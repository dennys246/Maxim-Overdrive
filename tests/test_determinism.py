"""Determinism: the same scene, rig and actions give bit-identical state on the same machine.

Replays, saves, bug reports and Maxim cradles all depend on it (CLAUDE.md, "Determinism"). Across machines only the
outcome class is promised, as under the resolution rule.
"""

from __future__ import annotations

import hashlib
import io
import os
import re
import subprocess
import sys
import tokenize
from pathlib import Path

import pytest

from maxim_overdrive import Box, RigProfile, Scene, World
from maxim_overdrive.sem_env.bridge import region_parts
from tests.conftest import FAST_TIERS

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
    w = World.from_scene(SCENE, RigProfile.load(rig_name))
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
FORBIDDEN = {
    r"\bimport\s+(?:random|secrets)\b|\bfrom\s+(?:random|secrets)\s+import\b": "the stdlib RNG or OS entropy",
    r"\bimport\s+numpy\.random\b|\bfrom\s+numpy\.random\s+import\b|\bfrom\s+numpy\s+import\b.*\brandom\b": (
        "a numpy.random import outside the np namespace (use the World's Generator)"
    ),
    r"\b(?:np|numpy)\.random\.(?!default_rng\b|Generator\b|SeedSequence\b|PCG64\b)\w+": "numpy's global RNG",
    r"\bdefault_rng\(\s*\)|\bPCG64\(\s*\)|\bSeedSequence\(\s*\)": "an unseeded generator (seeded from OS entropy)",
    r"\btime\.(?:time|monotonic|perf_counter|process_time|thread_time)(?:_ns)?\(|\btime\.sleep\(": "the wall clock",
    r"\bfrom\s+time\s+import\b|\bperf_counter(?:_ns)?\(": "the wall clock",
    r"\b(?:datetime|date)\.(?:now|utcnow|today)\(": "the wall clock",
    r"(?<![\w.])hash\(": "builtin hash (randomized per process by PYTHONHASHSEED)",
    r"\bos\.urandom\(|\buuid\.uuid[14]\(|\bSystemRandom\b": "OS entropy",
}
# server/ is the transport: it may read the clock and OS entropy (connection timeouts, the per-launch token), and
# nothing it reads that way may reach the world. Everything else in the package is simulation.
NOT_SIMULATION = {"server"}


def code_only(source: str) -> list[tuple[int, str]]:
    """Each line's code with comments and string contents removed, so prose about ``hash(`` is not a finding."""
    lines: dict[int, list[str]] = {}
    skip = {tokenize.COMMENT, tokenize.STRING, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT}
    skip |= {getattr(tokenize, n) for n in ("FSTRING_MIDDLE", "TSTRING_MIDDLE") if hasattr(tokenize, n)}
    prev_end: tuple[int, int] | None = None
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type in skip or tok.type == tokenize.ENDMARKER:
            prev_end = None
            continue
        row = tok.start[0]
        sep = " " if prev_end and (prev_end[0] != row or prev_end[1] != tok.start[1]) else ""
        lines.setdefault(row, []).append(sep + tok.string)
        prev_end = tok.end
    return [(row, "".join(parts)) for row, parts in sorted(lines.items())]


def findings(path: Path, source: str) -> list[str]:
    out = []
    for lineno, line in code_only(source):
        for pattern, why in FORBIDDEN.items():
            if re.search(pattern, line):
                out.append(f"{path}:{lineno}: {why}: {line.strip()}")
    return out


def scanned_files() -> list[Path]:
    files = [p for p in PACKAGE.rglob("*.py") if p.relative_to(PACKAGE).parts[0] not in NOT_SIMULATION]
    return sorted(files) + sorted((ROOT / "tests").rglob("*.py"))


def test_the_simulation_and_tests_have_no_hidden_sources_of_nondeterminism():
    hits = [f for p in scanned_files() for f in findings(p.relative_to(ROOT), p.read_text())]
    assert not hits, "\n".join(hits)


@pytest.mark.parametrize(
    "line",
    [
        "import random",
        "from random import choice",
        "import secrets",
        "from numpy.random import rand",
        "from numpy import random",
        "import numpy.random",
        "x = np.random.rand(3)",
        "x = numpy.random.normal()",
        "rng = np.random.default_rng()",
        "rng = np.random.Generator(np.random.PCG64())",
        "t = time.time()",
        "t = time.time_ns()",
        "t = time.perf_counter_ns()",
        "t = time.process_time()",
        "time.sleep(0.1)",
        "from time import time",
        "d = datetime.now()",
        "d = date.today()",
        "k = hash(name)",
        "b = os.urandom(8)",
        "u = uuid.uuid4()",
        "r = random_module.SystemRandom()",
    ],
)
def test_the_scan_catches(line):
    assert findings(Path("x.py"), line + "\n"), line


@pytest.mark.parametrize(
    "line",
    [
        "rng = np.random.default_rng(seed)",
        "rng = np.random.Generator(np.random.PCG64(1234))",
        "# never call hash(x) or time.time() here",
        "msg = 'hash(x) and time.time() are banned'",
        'doc = f"{name}: uses np.random.rand"',
        "h = stable_hash(name)",
        "h = hashlib.sha256()",
        "t = world.time_s",
    ],
)
def test_the_scan_ignores(line):
    assert findings(Path("x.py"), line + "\n") == [], line
