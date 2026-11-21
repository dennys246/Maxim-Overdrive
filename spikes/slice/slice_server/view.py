"""The tick's message to the client: what the simulation's state looks like on the wire (display only).

Kept out of ``sim``: the simulation decides and is replayed bit for bit; this module only reads it, quantizes cells
for display and packs them for the wire, so a change to the client message never touches the deterministic core.
"""

from __future__ import annotations

import numpy as np

from simcore.protocol.encoding import snapshot
from slice_server import alley
from slice_server.sim import Sim
from slice_server.wire import pack_cells

# The slice's heat channel, display only: 20 C is 0 and 500 C is 255. Glow starts near 525 C and the energy of a
# fire goes into the bulk (there is no surface skin in the world until fire's rung 6b), so this channel is what
# shows a fire warming its fuel before anything glows.
HEAT_LOW_C, HEAT_HIGH_C = 20.0, 500.0


def client_state(sim: Sim) -> dict[str, object]:
    """The body, its heat, the fires, the vendor and the cells, for the client to draw."""
    frame = sim.frame
    snap = snapshot(frame)
    heat = np.clip((np.asarray(frame.temperature) - HEAT_LOW_C) / (HEAT_HIGH_C - HEAT_LOW_C), 0.0, 1.0)
    snap["heat"] = np.round(heat * 255).astype(np.uint8)
    b, h, p, v = sim.body, sim.heat, sim.config.heat, sim.vendor
    return {
        "type": "state",
        "tick": sim.tick,
        "time_s": frame.time_s,
        "body": {"pos": [b.x, b.y, b.feet_z], "vel": [b.vx, b.vy], "yaw": b.yaw, "work_j": b.work_j},
        "heat": {
            "core_c": h.core_c,
            "start_c": p.start_c,
            "coolant": h.coolant_kg / p.coolant_kg,
            "warn_c": p.warn_c,
            "trip_c": p.trip_c,
            "tripped": h.tripped,
            "overdrive": sim.overdrive_on(),
            "flux_w_m2": sim.fire.flux_at(sim.chest()),
            "in_puddle": alley.in_puddle(b.x, b.y),
        },
        "burning": [{"region": f.name, "at": list(f.centroid)} for f in sim.fire.fuels.values() if f.burning],
        "fires": [
            {
                "region": f.name,
                "fuel": f.fuel_kg / f.fuel0_kg,
                "skin_c": f.skin_c,
                "burning": f.burning,
                "burnt_out": f.burnt_out,
            }
            for f in sim.fire.fuels.values()
        ],
        "puddle": list(alley.PUDDLE_XY),
        "vendor": {"pos": [v.x, v.y, v.feet_z], "yaw": v.yaw, "state": sim.vendor_state, "charges": sim.charges},
        "cells": {name: pack_cells(snap[name]) for name in ("material", "crack", "glow", "heat")},
    }
