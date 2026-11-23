"""M5, the burn diagnostic (plan.md §5), reported only: it measures known gaps, never the generator.

On the shipped path: ``place`` into a fresh world, an ignite record (100 kW, 0.3 m) on its first tick, then turns of
6 s through ``Simulation.step`` (errata E4, E18). (a) a fire on air has no solid cell centre inside its sphere at
turn 0; (b) for the rest, the turn at which the sphere's solid fraction reaches zero, and the region's integrity at
turns 10, 20 and 30, censored from that turn on. Throwaway spike code.
"""

from __future__ import annotations

import json
import subprocess
from collections import defaultdict
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import protocol

from maxim_overdrive.data import action_limits
from simcore.core import reductions
from simcore.core.imagination import place
from simcore.core.intents import Ignite, LogRecord
from simcore.core.simulation import SimConfig, Simulation
from simcore.core.world import World

POWER_W, RADIUS_M, TURNS, AT = 100e3, 0.3, 30, (10, 20, 30)
TURN_S = 6.0  # errata E4: turns of 6 s, pinned here so a changed default can't move M5
# Errata E18: a 1 s tick with physics every sixth, so a turn is one 6 s physics step, as World.advance(6.0) was,
# bit for bit; the ignite applies on tick 1, before any physics, where the old apply stood.
TICKS_PER_TURN = 6
CONFIG = SimConfig(tick_us=int(TURN_S * 1e6) // TICKS_PER_TURN, physics_every=TICKS_PER_TURN)
# M5's engine check (errata E18): six specs' trajectories recorded on c6d4f10 by m5_golden_recorder.py
GOLDEN = Path(__file__).parent / "m5_golden_c6d4f10.json"


def solid_in_sphere(world: World, name: str) -> int:
    src = world.sources[f"fire:{name}"]
    x, y, z = world.grid.mesh()
    px, py, pz = src.point_m
    inside = (x - px) ** 2 + (y - py) ** 2 + (z - pz) ** 2 <= src.radius_m**2
    return int(np.count_nonzero(inside & world.grid.solid))


def lit(spec: dict[str, Any]) -> tuple[Simulation, World, Any]:
    """The spec placed in a fresh world and the ignite applied on tick 1: the simulation, its world, the outcome."""
    world = World(protocol.empty_grid(), limits=action_limits())
    place(world.grid, spec, protocol.OFFSET_M)
    sim = Simulation(world, config=CONFIG)
    fire = Ignite(POWER_W, RADIUS_M)
    record = LogRecord(apply_tick=1, apply_us=0, actor_id=1, seq=0, kind="ignite", target=spec["name"], params=fire)
    (outcome,) = sim.step([record]).outcomes
    return sim, world, outcome


def turns(sim: Simulation, world: World, name: str) -> Iterator[tuple[int, float]]:
    """After each 6 s turn: the solid cells inside the fire's sphere and the region's integrity."""
    for _ in range(TURNS):
        while True:
            report = sim.step([])
            if report.physics:
                break
        yield solid_in_sphere(world, name), reductions.region_integrity(world.grid, name)


def trajectory(spec: dict[str, Any]) -> list[list[Any]]:
    """The golden's rows for an accepted spec: solid cells in the sphere and integrity, after the ignite (turn 0,
    integrity not read) and after each turn."""
    sim, world, outcome = lit(spec)
    if not outcome.success:
        raise RuntimeError(f"the golden's {spec['name']} was refused at ignite: {outcome.error}")
    rows: list[list[Any]] = [[solid_in_sphere(world, spec["name"]), None]]
    return rows + [[solid, repr(value)] for solid, value in turns(sim, world, spec["name"])]


def check_engine(golden_path: Path = GOLDEN) -> str:
    """Refuse to score unless this engine burns the golden's specs exactly as the engine M5 was written against
    (errata E18), so a later physics change stops M5 loudly instead of moving its numbers. Returns that engine."""
    golden = json.loads(golden_path.read_text())
    arms = protocol.load_arms()
    for raw in golden["specs"]:
        spec = protocol.convert(raw, arms)
        if trajectory(spec) != golden["turns"][spec["name"]]:
            raise RuntimeError(
                f"M5 refuses to score: {spec['name']} no longer burns as it did on {golden['engine']} (errata E18)"
            )
    return str(golden["engine"])


def _src_tree() -> str:
    out = subprocess.run(
        ["git", "-C", str(protocol.ROOT), "rev-parse", "HEAD:src"], check=True, capture_output=True, text=True
    )
    return out.stdout.strip()


def burn(spec: dict[str, Any]) -> dict[str, Any]:
    sim, world, outcome = lit(spec)
    name = spec["name"]
    if not outcome.success:
        return {"ignited": False, "code": None if outcome.code is None else outcome.code.value}
    if solid_in_sphere(world, name) == 0:
        return {"ignited": True, "fire_on_air": True}
    censor, integrity = None, {}
    for turn, (solid, value) in enumerate(turns(sim, world, name), start=1):
        if censor is None and solid == 0:
            censor = turn
        if turn in AT:
            integrity[turn] = None if censor is not None else value
    return {"ignited": True, "fire_on_air": False, "solid_gone_turn": censor, "integrity": integrity}


def m5(samples: Sequence[Any]) -> dict[str, Any]:
    """Per (model, arm), over accepted specs: the fire-on-air fraction and the censored integrity means, with the
    engine they burned on (errata E18)."""
    engine = {"matches": check_engine(), "src_tree": _src_tree()}  # before any burn (errata E18)
    rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for s in samples:
        if s.verdict.klass == protocol.ACCEPTED and s.spec is not None:
            rows[f"{s.model}/{s.arm}"].append(burn(s.spec))
    out: dict[str, Any] = {"engine": engine}  # cells are keyed "model/arm", so this key can't collide
    for key, rs in sorted(rows.items()):
        lit = [r for r in rs if r.get("ignited")]
        solid = [r for r in lit if not r["fire_on_air"]]
        out[key] = {
            "n": len(rs),
            "fire_on_air": sum(r["fire_on_air"] for r in lit) / len(lit) if lit else None,
            "solid_gone_turns": [r["solid_gone_turn"] for r in solid],
            "integrity_mean": {t: _mean([r["integrity"][t] for r in solid]) for t in AT},
        }
    return out


def _mean(values: list[float | None]) -> dict[str, Any]:
    kept = [v for v in values if v is not None]
    return {
        "mean": float(np.mean(kept)) if kept else None,
        "uncensored": len(kept),
        "censored": len(values) - len(kept),
    }
