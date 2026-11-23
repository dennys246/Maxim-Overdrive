"""M5, the burn diagnostic (plan.md §5), reported only: it measures known gaps, never the generator.

On the shipped path: ``place`` into a fresh world, ``Applier.apply(name, Ignite(100 kW, 0.3 m))``, then turns of
``World.advance`` at the world's default turn length. (a) a fire on air has no solid cell centre inside its sphere at
turn 0; (b) for the rest, the turn at which the sphere's solid fraction reaches zero, and the region's integrity at
turns 10, 20 and 30, censored from that turn on. Throwaway spike code.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from typing import Any

import numpy as np
import protocol

from maxim_overdrive.data import action_limits
from simcore.core import reductions
from simcore.core.applier import Applier
from simcore.core.imagination import place
from simcore.core.intents import Ignite
from simcore.core.world import World

POWER_W, RADIUS_M, TURNS, AT = 100e3, 0.3, 30, (10, 20, 30)
TURN_S = 6.0  # errata E4: turns of 6 s, pinned here so a changed World default can't move M5


def _solid_in_sphere(world: World, name: str) -> int:
    src = world.sources[f"fire:{name}"]
    x, y, z = world.grid.mesh()
    px, py, pz = src.point_m
    inside = (x - px) ** 2 + (y - py) ** 2 + (z - pz) ** 2 <= src.radius_m**2
    return int(np.count_nonzero(inside & world.grid.solid))


def burn(spec: dict[str, Any]) -> dict[str, Any]:
    world = World(protocol.empty_grid(), limits=action_limits())
    place(world.grid, spec, protocol.OFFSET_M)
    name = spec["name"]
    outcome = Applier(world).apply(name, Ignite(POWER_W, RADIUS_M))
    if not outcome.success:
        return {"ignited": False, "code": None if outcome.code is None else outcome.code.value}
    if _solid_in_sphere(world, name) == 0:
        return {"ignited": True, "fire_on_air": True}
    censor, integrity = None, {}
    for turn in range(1, TURNS + 1):
        world.advance(TURN_S)
        if censor is None and _solid_in_sphere(world, name) == 0:
            censor = turn
        if turn in AT:
            integrity[turn] = None if censor is not None else reductions.region_integrity(world.grid, name)
    return {"ignited": True, "fire_on_air": False, "solid_gone_turn": censor, "integrity": integrity}


def m5(samples: Sequence[Any]) -> dict[str, Any]:
    """Per (model, arm), over accepted specs: the fire-on-air fraction and the censored integrity means."""
    rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for s in samples:
        if s.verdict.klass == protocol.ACCEPTED and s.spec is not None:
            rows[f"{s.model}/{s.arm}"].append(burn(s.spec))
    out = {}
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
