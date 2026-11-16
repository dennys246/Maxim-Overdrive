"""Determinism: the same scene, rig and actions give bit-identical state on the same machine.

Replays, saves, bug reports and Maxim cradles all depend on it (CLAUDE.md, "Determinism"). Across machines only the
outcome class is promised, as under the resolution rule.
"""

from __future__ import annotations

import ast
import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

from maxim_overdrive import Box, RigProfile, Scene, World
from maxim_overdrive.config import ActionLimits
from maxim_overdrive.sem_env.bridge import region_parts
from tests.conftest import FAST_TIERS

LIMITS = ActionLimits.load()

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "maxim_overdrive"

SCENE = Scene(
    (3.0, 3.0, 2.0),
    (Box((1.2, 1.2, 0), (1.8, 1.8, 0.6), "wood", "crate"), Box((0, 0, 0), (0.6, 3.0, 2.0), "concrete", "wall")),
)
TURNS = 30
FIRE_W = 500_000.0  # hot enough that the crate degrades and loses cells within TURNS, at every fast rig

# Determinism is a property of code paths, not of cell size: the fast tiers run the same code as max, and max would
# add about 50 s to every pre-push for no new path.
fast_rigs = pytest.mark.parametrize("rig_name", FAST_TIERS)


def run(rig_name: str) -> World:
    """Fire on the crate and a strike on the wall: heat, thermal degradation, thermal and mechanical destruction."""
    w = World.from_scene(SCENE, RigProfile.load(rig_name), limits=LIMITS)
    _, crate = region_parts(w, "crate")
    assert crate["structure"].execute("ignite", {"power_w": FIRE_W, "radius_m": 0.3}).success
    _, wall = region_parts(w, "wall")
    assert wall["structure"].execute("strike", {"energy_j": 2.0e7, "sigma_m": 0.2}).success
    for _ in range(TURNS):
        w.advance()
    return w


def digest(w: World) -> str:
    """Everything the next turn depends on: cells, regions (in insertion order), sources, clock."""
    h = hashlib.sha256()
    g = w.grid
    for arr in (g.material, g.original_material, g.integrity, g.temperature):
        h.update(arr.tobytes())
    for name, mask in g.regions.items():
        h.update(name.encode())
        h.update(mask.tobytes())
    for name, src in w.sources.items():
        h.update(f"{name}{src.point_m}{src.radius_m}{src.power_w}".encode())
    h.update(f"{g.time_s!r} {w.turn}".encode())
    return h.hexdigest()


@fast_rigs
def test_the_scenario_exercises_burning(rig_name):
    """Guard on the guard: if the fire stops reaching degradation, the determinism tests below test too little."""
    w = run(rig_name)
    sensors, _ = region_parts(w, "crate")
    assert sensors["integrity"].value() < 0.9  # thermal degradation ran
    original_crate = w.grid.regions["crate"] & (w.grid.original_material != 0)
    assert (original_crate & ~w.grid.solid).any()  # and destroyed crate cells


@fast_rigs
def test_two_runs_are_bit_identical(rig_name):
    assert digest(run(rig_name)) == digest(run(rig_name))


@fast_rigs
def test_runs_in_processes_with_different_hash_seeds_agree(rig_name):
    """Catches order that depends on PYTHONHASHSEED (iterating a set of names), which one process cannot see."""
    here = digest(run(rig_name))
    code = f"from tests.test_determinism import digest, run; print(digest(run({rig_name!r})))"
    # Seeds 0, 3 and 4 iterate a small set of strings in three different orders (1 and 2 happen to agree, so a test
    # on those two passed with a seed-dependent defect injected). The in-process run adds a fourth, random seed.
    for seed in ("0", "3", "4"):
        env = {**os.environ, "PYTHONHASHSEED": seed, "PYTHONPATH": f"{ROOT / 'src'}{os.pathsep}{ROOT}"}
        out = subprocess.run(
            [sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, check=True
        )
        assert out.stdout.strip() == here, f"PYTHONHASHSEED={seed}"


# -- the static half: no hidden sources of nondeterminism ------------------------------------------------------------

# Randomness, when it arrives, comes from one seeded numpy Generator owned by World; time comes from World.advance.
# The scan reads the syntax tree, so comments, strings, spacing, line breaks and aliases can't hide a call, and
# f-string expressions are checked on every Python version.
BANNED_MODULES = {
    "random": "the stdlib global RNG",
    "secrets": "OS entropy",
    "uuid": "OS entropy",
    "time": "the wall clock",
    "datetime": "the wall clock",
    "timeit": "the wall clock",
}
NUMPY_RANDOM_ALLOWED = {"default_rng", "Generator", "SeedSequence", "PCG64"}  # seeded construction only
SEEDED_CONSTRUCTORS = {"default_rng", "PCG64", "SeedSequence"}
# server/ is the transport: it may read the clock and OS entropy (connection timeouts, the per-launch token), and
# nothing it reads that way may reach the world (docs/standards_backlog.md B14). Everything else is simulation.
NOT_SIMULATION = {"server"}


def _dotted(node: ast.AST) -> str | None:
    """``np.random.rand`` for an attribute chain on a name, else None."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        return ".".join([node.id, *reversed(parts)])
    return None


def _import_findings(node: ast.Import | ast.ImportFrom) -> list[str]:
    modules = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
    out = [f"imports {m}: {BANNED_MODULES[m.split('.')[0]]}" for m in modules if m.split(".")[0] in BANNED_MODULES]
    numpy_random = any(m.startswith("numpy.random") for m in modules) or (
        isinstance(node, ast.ImportFrom) and node.module == "numpy" and any(a.name == "random" for a in node.names)
    )
    if numpy_random:
        out.append("imports numpy.random: use the World's Generator")
    return out


def _name_findings(dotted: str) -> list[str]:
    parts = dotted.split(".")
    out = []
    if parts[0] in BANNED_MODULES and len(parts) > 1:
        out.append(f"uses {dotted}: {BANNED_MODULES[parts[0]]}")
    if parts[0] in ("np", "numpy") and parts[1:2] == ["random"] and parts[2:3] and parts[2] not in NUMPY_RANDOM_ALLOWED:
        out.append(f"uses {dotted}: numpy's global RNG")
    if dotted in ("os.urandom", "date.today") or parts[-1] == "SystemRandom":
        out.append(f"uses {dotted}: OS entropy or the wall clock")
    return out


def _call_findings(node: ast.Call) -> list[str]:
    name = _dotted(node.func) or ""
    out = []
    if name == "hash":
        out.append("calls builtin hash (randomized per process by PYTHONHASHSEED)")
    if name.split(".")[-1] in SEEDED_CONSTRUCTORS and not node.args and not node.keywords:
        out.append(f"calls {name}() with no seed (seeded from OS entropy)")
    return out


def findings(path: Path, source: str) -> list[str]:
    tree = ast.parse(source)
    # Judge only the outermost attribute of a chain, so np.random.rand is one finding, not three.
    inner = {id(n.value) for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    out = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            hits = _import_findings(node)
        elif isinstance(node, (ast.Attribute, ast.Name)) and id(node) not in inner:
            hits = _name_findings(_dotted(node) or "")
        elif isinstance(node, ast.Call):
            hits = _call_findings(node)
        else:
            hits = []
        out += [f"{path}:{getattr(node, 'lineno', 0)}: {h}" for h in hits]
    return out


def scanned_files() -> list[Path]:
    files = [p for p in PACKAGE.rglob("*.py") if p.relative_to(PACKAGE).parts[0] not in NOT_SIMULATION]
    return sorted(files) + sorted((ROOT / "tests").rglob("*.py"))


def test_the_simulation_and_tests_have_no_hidden_sources_of_nondeterminism():
    hits = [f for p in scanned_files() for f in findings(p.relative_to(ROOT), p.read_text())]
    assert not hits, "\n".join(hits)


@pytest.mark.parametrize(
    "source",
    [
        "import random",
        "from random import choice",
        "import secrets",
        "import time as t",
        "from time import time",
        "from datetime import datetime as dt",
        "import timeit",
        "import uuid",
        "from numpy.random import rand",
        "from numpy import random",
        "import numpy.random",
        "x = np.random.rand(3)",
        "x = numpy.random.normal()",
        "x = (np.random\n.rand())",
        "x = np . random . rand()",
        "rng = np.random.default_rng()",
        "rng = np.random.Generator(np.random.PCG64())",
        "t = time.time()",
        "clock = time.time",
        "t = time.perf_counter_ns()",
        "time.sleep(0.1)",
        "d = datetime.now()",
        "d = date.today()",
        "k = hash(name)",
        "k = hash (name)",
        'msg = f"{hash(name)}"',
        "b = os.urandom(8)",
        "r = random_module.SystemRandom()",
    ],
)
def test_the_scan_catches(source):
    assert findings(Path("x.py"), source + "\n"), source


@pytest.mark.parametrize(
    "source",
    [
        "rng = np.random.default_rng(seed)",
        "rng = np.random.default_rng(seed=1)",
        "rng = np.random.Generator(np.random.PCG64(1234))",
        "# never call hash(x) or time.time() here",
        "msg = 'hash(x) and time.time() are banned'",
        'doc = f"{name}: uses np.random.rand"',
        "h = stable_hash(name)",
        "h = hashlib.sha256()",
        "t = world.time_s",
        "self.hash = value.hash(1)",
    ],
)
def test_the_scan_ignores(source):
    assert findings(Path("x.py"), source + "\n") == [], source


def test_a_chain_is_one_finding():
    assert len(findings(Path("x.py"), "x = np.random.rand(3)\n")) == 1
