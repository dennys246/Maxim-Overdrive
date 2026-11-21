"""One deterministic tick of the slice: intents, then bodies, then fire, then physics (the tile spec's tick order).

No clock and no IO here: ``Sim.step`` takes the tick's intents and advances exactly ``tick_s`` of simulated time, so
the same intents give the same state, which is what replay checks (``replay``). The server paces it to the wall
clock from outside. Every change to the world goes through the applier; the fire and the body's heat only decide.
"""

from __future__ import annotations

import hashlib
import math
import struct
from collections.abc import Iterable, Sequence
from dataclasses import astuple, replace

import numpy as np

from maxim_overdrive import data
from simcore.core.applier import Applier
from simcore.core.frames import CellFrame
from simcore.core.intents import Extinguish, Ignite
from simcore.core.scene import Box
from simcore.core.world import World
from simcore.protocol.encoding import snapshot
from slice_server import alley, heat_debt
from slice_server.body import Body, Cells, Command, check_no_tunnelling, step
from slice_server.config import SliceConfig
from slice_server.fire import Decision, Fire, FuelMaterial, Point, fuels_from
from slice_server.intents import Intent, Kindle, Move
from slice_server.wire import pack_cells

# The slice's heat channel, display only: 20 C is 0 and 500 C is 255. Glow starts near 525 C and the energy of a
# fire goes into the bulk (there is no surface skin in the world until fire's rung 6b), so this channel is what
# shows a fire warming its fuel before anything glows.
HEAT_LOW_C, HEAT_HIGH_C = 20.0, 500.0
CHEST_M = 1.0  # where on the body radiation and air temperature are read, above the feet


class Sim:
    def __init__(self, config: SliceConfig, *, dx_m: float = 0.2, tick_s: float = 0.1) -> None:
        check_no_tunnelling(config.body, tick_s, dx_m)
        self.config, self.tick_s, self.tick = config, tick_s, 0
        scene, table = alley.scene(), data.materials()
        self.world = World.from_scene(scene, table, dx_m=dx_m, limits=data.action_limits())
        self._applier = Applier(self.world)  # the only way the slice changes the world
        self.body = Body(*alley.SPAWN_M, feet_z=alley.FLOOR_TOP_M)
        self.command = Command()
        self.heat = heat_debt.start(config.heat)
        self.fire = Fire(config.fuel.fire, _fuels(config, scene.primitives, table))
        self._check_fire_fits_the_limits()

    def _check_fire_fits_the_limits(self) -> None:
        limits, radius = self.world.limits, self.config.fuel.fire.source_radius_m
        if not limits.min_radius_m <= radius <= limits.max_radius_m:
            raise ValueError(f"fire.source_radius_m {radius} is outside the action limits")
        for fuel in self.fire.fuels.values():
            if fuel.peak_power_w() > limits.max_power_w:
                raise ValueError(f"the {fuel.name} would burn at {fuel.peak_power_w():.0f} W, over the action limits")

    @property
    def frame(self) -> CellFrame:
        return self.world.frames.latest.cells

    def step(self, intents: Sequence[Intent]) -> list[dict[str, object]]:
        """One tick. Returns the events it caused, for the client and the session log."""
        events = [e for intent in intents if (e := self._take(intent)) is not None]
        frame = self.frame
        command = self._effective(self.command)
        step(self.body, command, Cells(frame.solid, frame.dx_m), self.config.body, self.tick_s)
        self._heat_body(command)
        decisions, fire_events = self.fire.step(self.tick_s)
        for decision in decisions:
            self._apply(decision)
        self.world.advance(self.tick_s)
        self.tick += 1
        return events + fire_events

    def _take(self, intent: Intent) -> dict[str, object] | None:
        if isinstance(intent, Move):
            self.command = intent.command
            return None
        if isinstance(intent, Kindle):
            return self._kindle()
        raise TypeError(f"not an intent: {type(intent).__name__}")  # a programming error: intents are parsed first

    def _effective(self, command: Command) -> Command:
        """A tripped body has no Overdrive and runs slow."""
        if not self.heat.tripped:
            return command
        return replace(command, effort=command.effort * self.config.heat.tripped_speed_factor, overdrive=False)

    def _chest(self) -> Point:
        return (self.body.x, self.body.y, self.body.feet_z + CHEST_M)

    def _heat_body(self, command: Command) -> None:
        heat_debt.step(
            self.heat,
            self.config.heat,
            overdrive=command.overdrive and command.effort > 0,
            air_c=air_mean_c(self.frame, self._chest(), self.config.heat.sense_radius_m),
            radiant_w_m2=self.fire.flux_at(self._chest()),
            in_puddle=alley.in_puddle(self.body.x, self.body.y),
            dt=self.tick_s,
        )

    def _apply(self, decision: Decision) -> None:
        if decision.power_w > 0:
            action: Ignite | Extinguish = Ignite(decision.power_w, self.config.fuel.fire.source_radius_m)
        else:
            action = Extinguish()
        outcome = self._applier.apply(decision.region, action)
        if not outcome.success:  # the powers were checked against the limits at start: this is a bug, say so
            raise RuntimeError(f"the applier refused the fire's {decision}: {outcome.error}")

    def _target(self) -> str | None:
        """The nearest object that can still burn, within reach of the body's axis and in front of it."""
        b, reach = self.body, self.config.kindle.reach_m
        best: tuple[float, str] | None = None
        for name, fuel in sorted(self.fire.fuels.items()):
            if fuel.burnt_out:
                continue
            (x0, y0, _), (x1, y1, _) = fuel.bounds
            nx, ny = min(max(b.x, x0), x1), min(max(b.y, y0), y1)
            dist = math.hypot(nx - b.x, ny - b.y)
            # In front means within 60 degrees of the facing (cos 60 = 0.5); touching it counts as in front.
            ahead = dist < 1e-9 or (nx - b.x) * math.cos(b.yaw) + (ny - b.y) * math.sin(b.yaw) >= 0.5 * dist
            if dist <= reach and ahead and (best is None or dist < best[0]):
                best = (dist, name)
        return None if best is None else best[1]

    def _kindle(self) -> dict[str, object]:
        target = self._target()
        if target is None:
            return {"type": "event", "what": "kindle", "ok": False, "error": "nothing that burns within reach"}
        why_not = self.fire.kindle(target)
        return {"type": "event", "what": "kindle", "region": target, "ok": why_not is None, "error": why_not}

    def state(self) -> dict[str, object]:
        """The tick's message to the client: the body, its heat, the fires and the cells, quantized for display."""
        snap = snapshot(self.frame)
        heat = np.clip((np.asarray(self.frame.temperature) - HEAT_LOW_C) / (HEAT_HIGH_C - HEAT_LOW_C), 0.0, 1.0)
        snap["heat"] = np.round(heat * 255).astype(np.uint8)
        b, h, p = self.body, self.heat, self.config.heat
        return {
            "type": "state",
            "tick": self.tick,
            "time_s": self.frame.time_s,
            "body": {"pos": [b.x, b.y, b.feet_z], "vel": [b.vx, b.vy], "yaw": b.yaw, "work_j": b.work_j},
            "heat": {
                "core_c": h.core_c,
                "coolant": h.coolant_kg / p.coolant_kg,
                "warn_c": p.warn_c,
                "trip_c": p.trip_c,
                "tripped": h.tripped,
                "overdrive": self._effective(self.command).overdrive and self.command.effort > 0,
                "flux_w_m2": self.fire.flux_at(self._chest()),
                "in_puddle": alley.in_puddle(b.x, b.y),
            },
            "burning": [{"region": f.name, "at": list(f.centroid)} for f in self.fire.fuels.values() if f.burning],
            "fires": [
                {
                    "region": f.name,
                    "fuel": f.fuel_kg / f.fuel0_kg,
                    "skin_c": f.skin_c,
                    "burning": f.burning,
                    "burnt_out": f.burnt_out,
                }
                for f in self.fire.fuels.values()
            ],
            "puddle": list(alley.PUDDLE_XY),
            "cells": {name: pack_cells(snap[name]) for name in ("material", "crack", "glow", "heat")},
        }

    def digest(self) -> str:
        """Every bit of state that replay must reproduce: cells, body, command, heat and fires."""
        f, h = self.frame, hashlib.sha256()
        for array in (f.material, f.integrity, f.temperature):
            h.update(array.tobytes())
        numbers = [*astuple(self.body), *astuple(self.command), *astuple(self.heat)]
        for fuel in self.fire.fuels.values():
            numbers += [fuel.fuel_kg, fuel.skin_c, fuel.released_j, fuel.burning, fuel.burnt_out]
        h.update(struct.pack(f"<{len(numbers)}d", *(float(n) for n in numbers)))
        h.update(struct.pack("<qd", self.tick, f.time_s))
        return h.hexdigest()


def _fuels(config: SliceConfig, primitives: Sequence[object], table: object) -> dict:
    """The fire's fuels: the fuel file's numbers with each material's density and heat capacity from the world."""
    boxes = {p.name: (p.material, p.bounds_m) for p in primitives if isinstance(p, Box) and p.name}
    materials = {}
    for name, entry in config.fuel.materials.items():
        m = table[name]  # type: ignore[index]
        materials[name] = FuelMaterial(
            entry.releasable_energy_j_kg, entry.ignition_c, entry.burn_rate_kg_s_m2,
            m.density_kg_m3, m.density_kg_m3 * m.specific_heat_j_kgk,
        )  # fmt: skip
    return fuels_from(
        boxes, config.fuel.objects, materials, floor_z=alley.FLOOR_TOP_M, ambient_c=config.fuel.fire.ambient_c
    )


def air_mean_c(frame: CellFrame, centre: Point, radius_m: float) -> float:
    """The mean temperature of the air cells within ``radius_m`` of ``centre``: a reduction over a volume in metres.
    Cells are weighted by whether their centre is inside, which is coarse for a 1 m sphere of 0.2 m cells, and
    accepted in this lane: no outcome is decided from it, only a heat flow."""
    dx, (nx, ny, nz) = frame.dx_m, frame.shape
    lo = [max(0, math.floor((c - radius_m) / dx)) for c in centre]
    hi = [min(n, math.ceil((c + radius_m) / dx)) for c, n in zip(centre, (nx, ny, nz), strict=True)]
    ii, jj, kk = (np.arange(a, b) for a, b in zip(lo, hi, strict=True))
    x, y, z = ((ii + 0.5) * dx)[:, None, None], ((jj + 0.5) * dx)[None, :, None], ((kk + 0.5) * dx)[None, None, :]
    inside = (x - centre[0]) ** 2 + (y - centre[1]) ** 2 + (z - centre[2]) ** 2 <= radius_m**2
    window = np.s_[lo[0] : hi[0], lo[1] : hi[1], lo[2] : hi[2]]
    air = inside & (frame.material[window] == 0)
    if not air.any():  # a body's chest is always in air; no air here means the body is inside a solid, a bug
        raise RuntimeError(f"no air within {radius_m} m of {centre}")
    return float(np.asarray(frame.temperature)[window][air].mean())


def replay(config: SliceConfig, ticks: Iterable[Sequence[Intent]], *, dx_m: float = 0.2) -> str:
    """Rerun a session from its intents, one sequence per tick, and return the final digest."""
    sim = Sim(config, dx_m=dx_m)
    for intents in ticks:
        sim.step(intents)
    return sim.digest()
