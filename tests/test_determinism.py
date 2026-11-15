"""Determinism: the same scene, rig and actions give bit-identical state on the same machine.

Replays, saves, bug reports and Maxim cradles all depend on it (CLAUDE.md, "Determinism"). Across machines only the
outcome class is promised, as under the resolution rule.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from maxim_overdrive import Box, Scene, World
from maxim_overdrive.sem_env.bridge import region_parts

SCENE = Scene(
    (3.0, 3.0, 2.0),
    (Box((1.2, 1.2, 0), (1.8, 1.8, 0.6), "wood", "crate"), Box((0, 0, 0), (0.6, 3.0, 2.0), "concrete", "wall")),
)


def _run(rig, materials, turns: int = 20) -> World:
    w = World.from_scene(SCENE, rig, materials)
    _, mods = region_parts(w, "crate")
    assert mods["structure"].execute("ignite", {"power_w": 60_000.0, "radius_m": 0.3}).success
    _, wall = region_parts(w, "wall")
    assert wall["structure"].execute("strike", {"energy_j": 2.0e7, "sigma_m": 0.2}).success
    for _ in range(turns):
        w.advance()
    return w


def test_two_runs_are_bit_identical(rig, materials):
    a, b = _run(rig, materials), _run(rig, materials)
    for name in ("material", "integrity", "temperature"):
        assert np.array_equal(getattr(a.grid, name), getattr(b.grid, name)), name
    assert a.grid.time_s == b.grid.time_s
    assert a.turn == b.turn


# Sources of nondeterminism the world server must not use. Randomness, when it arrives, goes through a seeded
# numpy Generator the World owns; time comes from World.advance, never the wall clock.
FORBIDDEN = {
    r"\bimport random\b|\bfrom random import\b": "the stdlib global RNG",
    r"np\.random\.(?!default_rng\b|Generator\b|SeedSequence\b)\w+": "numpy's global RNG",
    r"\btime\.time\(|\btime\.monotonic\(|\bperf_counter\(": "the wall clock",
    r"\bdatetime\.(?:now|utcnow|today)\(": "the wall clock",
    r"\bhash\(": "builtin hash (randomized per process by PYTHONHASHSEED)",
    r"\bos\.urandom\(|\buuid\.uuid[14]\(": "OS entropy",
}
SIMULATION_ROOTS = ["world", "sem_env", "imagination"]


def test_the_simulation_has_no_hidden_sources_of_nondeterminism():
    pkg = Path(__file__).resolve().parents[1] / "src" / "maxim_overdrive"
    hits = []
    for root in SIMULATION_ROOTS:
        for path in sorted((pkg / root).rglob("*.py")):
            for lineno, line in enumerate(path.read_text().splitlines(), 1):
                for pattern, why in FORBIDDEN.items():
                    if re.search(pattern, line):
                        hits.append(f"{path.relative_to(pkg)}:{lineno}: {why}: {line.strip()}")
    assert not hits, "\n".join(hits)
