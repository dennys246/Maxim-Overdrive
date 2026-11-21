"""One deterministic tick of the slice: intents, then bodies, then physics (the tile spec's tick order).

No clock and no IO here: ``Sim.step`` takes the tick's intents and advances exactly ``tick_s`` of simulated time, so
the same intents give the same state, which is what replay checks (``replay``). The server paces it to the wall
clock from outside.
"""

from __future__ import annotations

import hashlib
import math
import struct
from collections.abc import Iterable, Sequence
from dataclasses import astuple

import numpy as np

from maxim_overdrive import data
from simcore.core.applier import Applier
from simcore.core.frames import CellFrame
from simcore.core.intents import Ignite
from simcore.core.world import World
from simcore.protocol.encoding import snapshot
from slice_server import alley
from slice_server.body import Body, Cells, Command, check_no_tunnelling, step
from slice_server.config import SliceConfig
from slice_server.intents import Intent, Kindle, Move
from slice_server.wire import pack_cells

NOT_KINDLED = ("floor",)  # the ground is never the target in front of you
# The slice's heat channel, display only: 20 C is 0 and 500 C is 255. Glow starts near 525 C, and a 60 kW kindle
# takes minutes to bring any crate cell there (the energy goes into the bulk: there is no surface skin until fire's
# rung 6b), so this channel is what shows a fire warming its fuel before anything glows.
HEAT_LOW_C, HEAT_HIGH_C = 20.0, 500.0


class Sim:
    def __init__(self, config: SliceConfig, *, dx_m: float = 0.2, tick_s: float = 0.1) -> None:
        check_no_tunnelling(config.body, tick_s, dx_m)
        self.config, self.tick_s, self.tick = config, tick_s, 0
        self.world = World.from_scene(alley.scene(), data.materials(), dx_m=dx_m, limits=data.action_limits())
        self._applier = Applier(self.world)  # the only way the slice changes the world
        self.body = Body(*alley.SPAWN_M, feet_z=alley.FLOOR_TOP_M)
        self.command = Command()

    @property
    def frame(self) -> CellFrame:
        return self.world.frames.latest.cells

    def step(self, intents: Sequence[Intent]) -> list[dict[str, object]]:
        """One tick. Returns the events it caused, for the client and the session log."""
        events: list[dict[str, object]] = []
        for intent in intents:
            if isinstance(intent, Move):
                self.command = intent.command
            elif isinstance(intent, Kindle):
                events.append(self._kindle())
        frame = self.frame
        step(self.body, self.command, Cells(frame.solid, frame.dx_m), self.config.body, self.tick_s)
        self.world.advance(self.tick_s)
        self.tick += 1
        return events

    def _target(self) -> str | None:
        """The nearest named solid within reach of the body's axis, and not behind it."""
        b, reach = self.body, self.config.kindle.reach_m
        best: tuple[float, str] | None = None
        for name, region in sorted(self.frame.regions.items()):
            if not region.solid or name in NOT_KINDLED or not region.cells.any():
                continue
            (x0, y0, _), (x1, y1, _) = region.footprint.bounds_m
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
            return {"type": "event", "what": "kindle", "ok": False, "error": "nothing to light within reach"}
        k = self.config.kindle
        outcome = self._applier.apply(target, Ignite(k.power_w, k.radius_m))
        return {"type": "event", "what": "kindle", "region": target, "ok": outcome.success, "error": outcome.error}

    def state(self) -> dict[str, object]:
        """The tick's message to the client: the body and the cells, quantized for display."""
        snap = snapshot(self.frame)
        heat = np.clip((np.asarray(self.frame.temperature) - HEAT_LOW_C) / (HEAT_HIGH_C - HEAT_LOW_C), 0.0, 1.0)
        snap["heat"] = np.round(heat * 255).astype(np.uint8)
        burning = sorted(name.removeprefix("fire:") for name in self.world.sources if name.startswith("fire:"))
        b = self.body
        return {
            "type": "state",
            "tick": self.tick,
            "time_s": self.frame.time_s,
            "body": {"pos": [b.x, b.y, b.feet_z], "vel": [b.vx, b.vy], "yaw": b.yaw, "work_j": b.work_j},
            "burning": [{"region": r, "at": list(self.frame.regions[r].footprint.centroid_m)} for r in burning],
            "cells": {name: pack_cells(snap[name]) for name in ("material", "crack", "glow", "heat")},
        }

    def digest(self) -> str:
        """Every bit of state that replay must reproduce: the cells and the body."""
        f, h = self.frame, hashlib.sha256()
        for array in (f.material, f.integrity, f.temperature):
            h.update(array.tobytes())
        h.update(struct.pack(f"<{len(astuple(self.body))}d", *astuple(self.body)))
        h.update(struct.pack("<qd", self.tick, f.time_s))
        return h.hexdigest()


def replay(config: SliceConfig, ticks: Iterable[Sequence[Intent]], *, dx_m: float = 0.2) -> str:
    """Rerun a session from its intents, one sequence per tick, and return the final digest."""
    sim = Sim(config, dx_m=dx_m)
    for intents in ticks:
        sim.step(intents)
    return sim.digest()
