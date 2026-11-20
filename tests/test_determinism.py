"""Determinism: the same scene, grid spacing and actions give bit-identical state on the same machine.

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

from maxim_overdrive import data
from simcore.adapters.sem.bridge import region_parts
from simcore.core.scene import Box, Scene
from simcore.core.world import World
from tests.conftest import FAST_SPACINGS

LIMITS = data.action_limits()
MATERIALS = data.materials()

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

SCENE = Scene(
    (3.0, 3.0, 2.0),
    (Box((1.2, 1.2, 0), (1.8, 1.8, 0.6), "wood", "crate"), Box((0, 0, 0), (0.6, 3.0, 2.0), "concrete", "wall")),
)
TURNS = 30
FIRE_W = 500_000.0  # hot enough that the crate degrades and loses cells within TURNS, at every fast grid spacing

# Determinism is a property of code paths, not of cell size: the fast tiers run the same code as max, and max would
# add about 50 s to every pre-push for no new path.
fast_spacings = pytest.mark.parametrize("dx_m", FAST_SPACINGS)


def run(dx_m: float) -> World:
    """Fire on the crate and a strike on the wall: heat, thermal degradation, thermal and mechanical destruction."""
    w = World.from_scene(SCENE, MATERIALS, dx_m=dx_m, limits=LIMITS)
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
    for name, region in g.regions.items():
        mask = region.cells
        h.update(name.encode())
        h.update(mask.tobytes())
        h.update(f"{region.footprint}{region.solid}".encode())  # where fires land and what a strike reaches
    for name, src in w.sources.items():
        h.update(f"{name}{src.point_m}{src.radius_m}{src.power_w}".encode())
    h.update(f"{g.time_s!r} {w.turn}".encode())
    return h.hexdigest()


@fast_spacings
def test_the_scenario_exercises_burning(dx_m):
    """Guard on the guard: if the fire stops reaching degradation, the determinism tests below test too little."""
    w = run(dx_m)
    sensors, _ = region_parts(w, "crate")
    assert sensors["integrity"].value() < 0.9  # thermal degradation ran
    original_crate = w.grid.regions["crate"].cells & (w.grid.original_material != 0)
    assert (original_crate & ~w.grid.solid).any()  # and destroyed crate cells


# The substeps each 6 s turn takes on the shipped path, as the retired rigs set them (laptop, rig). The digests were
# shown bit-identical across the move by hand (step 3a's hand-off); a golden digest isn't committed, because only the
# outcome class is promised across machines and CI runs on another one. This pins the one number that set them.
TURN_SUBSTEPS = {0.2: 4, 0.1: 16, 0.05: 64}


@fast_spacings
def test_each_turn_takes_the_substeps_the_rigs_took(dx_m):
    w = World.from_scene(SCENE, MATERIALS, dx_m=dx_m, limits=LIMITS)
    _, crate = region_parts(w, "crate")
    assert crate["structure"].execute("ignite", {"power_w": FIRE_W, "radius_m": 0.3}).success
    assert [w.advance() for _ in range(3)] == [TURN_SUBSTEPS[dx_m]] * 3


@fast_spacings
def test_two_runs_are_bit_identical(dx_m):
    assert digest(run(dx_m)) == digest(run(dx_m))


@fast_spacings
def test_runs_in_processes_with_different_hash_seeds_agree(dx_m):
    """Catches order that depends on PYTHONHASHSEED (iterating a set of names), which one process cannot see."""
    here = digest(run(dx_m))
    code = f"from tests.test_determinism import digest, run; print(digest(run({dx_m!r})))"
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
# The sealed core's banned list (boundaries §3), the one list both checks read: pyproject.toml's sealed-core import
# contract must equal it (tests/test_tooling_config.py), and the core's own scan below refuses the same imports. It
# extends BANNED_MODULES, which holds everywhere, with what only the core gives up: the OS, file IO, logging,
# concurrency, the network, ctypes and Maxim.
SEALED_CORE_BANNED = frozenset(BANNED_MODULES) | {
    "zoneinfo",
    "os", "importlib", "sys", "platform", "locale", "signal", "gc", "weakref", "ctypes",
    "pathlib", "io", "yaml", "json", "tempfile", "shutil", "glob", "pickle", "marshal", "shelve", "dbm", "sqlite3",
    "mmap", "logging", "builtins", "codecs", "fileinput", "linecache", "tokenize", "zipfile", "tarfile", "gzip",
    "bz2", "lzma",
    "threading", "_thread", "asyncio", "concurrent", "multiprocessing", "subprocess", "queue", "sched",
    "socket", "select", "selectors", "ssl", "http", "urllib", "websockets",
    "maxim",
}  # fmt: skip
# What imports can't show (§3): builtins that read files, import by name or run text as code, named in any way (a
# call, an alias such as ``f = open``, ``getattr(builtins, ...)`` or ``__builtins__``); and numpy's and scipy's file
# IO, since the core imports both. The core uses none of them.
CORE_BANNED_BUILTINS = {"open", "__import__", "exec", "eval", "input", "compile", "getattr", "__builtins__"}
NUMPY_FILE_IO = {"load", "save", "savez", "savez_compressed", "fromfile", "memmap", "loadtxt", "savetxt", "genfromtxt"}
NUMPY_NAMES = {"np", "numpy"}
CORE = "simcore/core"
NUMPY_RANDOM_ALLOWED = {"default_rng", "Generator", "SeedSequence", "PCG64"}  # seeded construction only
SEEDED_CONSTRUCTORS = {"default_rng", "PCG64", "SeedSequence"}
# Package-qualified directories under src/ that may read the clock or OS entropy because nothing they read reaches the
# world: the transport, when it lands (simcore/host, docs/standards_backlog.md B14). None exists yet, so every package
# under src/ is scanned.
NOT_SIMULATION: set[str] = set()
# Non-vacuity: the scan must reach the turn loop and the laws, wherever a move puts them (boundaries §11.2, W14).
MUST_SCAN = {"simcore/core/world.py", "simcore/core/heat.py", "simcore/core/damage.py"}


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


def _simulated(path: Path) -> bool:
    rel = path.relative_to(SRC).as_posix()
    return not any(rel == d or rel.startswith(d + "/") for d in NOT_SIMULATION)


def scanned_files() -> list[Path]:
    files = [p for p in SRC.rglob("*.py") if _simulated(p)]
    return sorted(files) + sorted((ROOT / "tests").rglob("*.py"))


def _core_imports(node: ast.AST) -> list[str]:
    """What an import statement brings in, as dotted names; ``from numpy import load`` gives ``numpy.load``."""
    if isinstance(node, ast.Import):
        return [a.name for a in node.names]
    if isinstance(node, ast.ImportFrom) and node.level == 0:
        return [node.module or "", *(f"{node.module}.{a.name}" for a in node.names)]
    return []


def _core_file_io(node: ast.AST) -> str | None:
    """A banned builtin named anywhere, numpy's file IO (``np.load``, ``arr.tofile``) or ``scipy.io``."""
    if isinstance(node, ast.Name) and node.id in CORE_BANNED_BUILTINS:
        return f"names builtin {node.id}"
    if isinstance(node, ast.Attribute):
        dotted = _dotted(node) or ""
        parts = dotted.split(".")
        if node.attr == "tofile" or (parts[0] in NUMPY_NAMES and parts[-1] in NUMPY_FILE_IO):
            return f"uses {dotted or node.attr}: file IO"
        if parts[:2] == ["scipy", "io"]:
            return f"uses {dotted}: file IO"
        if parts[0] == "builtins":  # builtins.open, reached without an import through a module that holds it
            return f"uses {dotted}"
    return None


def core_findings(path: Path, source: str) -> list[str]:
    """The sealed core's own scan: no import from SEALED_CORE_BANNED, no banned builtin and no array file IO."""
    out = []
    for node in ast.walk(ast.parse(source)):
        line = getattr(node, "lineno", 0)
        for m in _core_imports(node):
            parts = m.split(".")
            if parts[0] in SEALED_CORE_BANNED or parts[:2] == ["scipy", "io"]:
                out.append(f"{path}:{line}: the core imports {m}")
            elif parts[0] == "numpy" and parts[-1] in NUMPY_FILE_IO:
                out.append(f"{path}:{line}: the core imports {m}: file IO")
        if (hit := _core_file_io(node)) is not None:
            out.append(f"{path}:{line}: the core {hit}")
    return out


def test_the_simulation_and_tests_have_no_hidden_sources_of_nondeterminism():
    scanned = scanned_files()
    assert {p.relative_to(SRC).as_posix() for p in scanned if p.is_relative_to(SRC)} >= MUST_SCAN
    hits = [f for p in scanned for f in findings(p.relative_to(ROOT), p.read_text())]
    core = sorted((SRC / CORE).rglob("*.py"))
    assert {p.relative_to(SRC).as_posix() for p in core} >= MUST_SCAN
    hits += [f for p in core for f in core_findings(p.relative_to(ROOT), p.read_text())]
    assert not hits, "\n".join(hits)


@pytest.mark.parametrize(
    "source",
    [
        "import os",
        "from pathlib import Path",
        "import logging.handlers",
        "import tempfile",
        "import maxim.embodiment",
        "from _thread import start_new_thread",
        "f = open('x')",
        "m = __import__('os')",
        "exec('x = 1')",
        "y = eval('1')",
        "s = input()",
        "import builtins",
        "import codecs",
        "import zipfile, gzip",
        "f = open",
        "f = __builtins__['open']",
        "e = getattr(builtins, 'exec')",
        "builtins.open('x')",
        "a = np.load('z.npy')",
        "np.save('z', a)",
        "a = numpy.fromfile('w')",
        "a = np.memmap('m')",
        "a = np.loadtxt('t')",
        "np.savetxt('t', a)",
        "a = np.genfromtxt('t')",
        "np.savez('z', a=a)",
        "arr.tofile('w')",
        "from numpy import load",
        "from scipy import io",
        "import scipy.io",
        "m = scipy.io.loadmat('m')",
    ],
)
def test_the_core_scan_catches(source):
    assert core_findings(Path("x.py"), source + "\n"), source


@pytest.mark.parametrize(
    "source",
    [
        "import math",
        "from . import heat",
        "from simcore.core.grid import MaterialGrid",
        "x = grid.open(1)",
        "# open('x')",
        "a = np.take(k, idx)",
        "from scipy.special import ndtr",
        "from numpy import typing",
        "x = self.load",
    ],
)
def test_the_core_scan_ignores(source):
    assert core_findings(Path("x.py"), source + "\n") == [], source


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
