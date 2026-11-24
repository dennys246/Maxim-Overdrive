"""Record M5's per-turn trajectory on the engine it was written against, the golden M5 checks itself to (errata E18).

Runs only on an engine with ``World.advance`` and the applier, ``c6d4f10``: from a ``git archive c6d4f10`` of the
repository, with this file copied in, run ``python -I spikes/specgen/m5_golden_recorder.py <out.json>`` from its root.
Each spec is ignited at 100 kW, 0.3 m; each row is the solid cells inside the fire's sphere and the region's integrity,
after the ignite (turn 0, integrity not read) and after each 6 s turn. Throwaway spike code.
"""

import json
import sys

sys.path[:0] = ["src", ".", "spikes/specgen"]
import burn  # noqa: E402
import numpy as np  # noqa: E402
import protocol  # noqa: E402

from maxim_overdrive.data import action_limits  # noqa: E402
from simcore.core import reductions  # noqa: E402
from simcore.core.applier import Applier  # noqa: E402
from simcore.core.imagination import place  # noqa: E402
from simcore.core.intents import Ignite  # noqa: E402
from simcore.core.world import World  # noqa: E402


def box(lo: list[int], hi: list[int]) -> dict[str, object]:
    return {"kind": "box", "min_cm": lo, "max_cm": hi, "material": "wood"}


def drum() -> dict[str, object]:
    return {"kind": "cylinder", "center_xy_cm": [30, 30], "radius_cm": 25, "z_cm": [0, 60], "material": "wood"}


SPECS = [
    {"intent": "golden", "name": "crate", "primitives": [box([0, 0, 0], [40, 40, 50])]},
    {"intent": "golden", "name": "stool", "primitives": [box([0, 0, 0], [40, 40, 40]), box([0, 0, 40], [40, 40, 50])]},
    {"intent": "golden", "name": "plank", "primitives": [box([0, 0, 0], [80, 20, 40])]},
    {"intent": "golden", "name": "drum", "primitives": [drum()]},
    # two legs 1 m apart: no solid cell centre inside the fire's sphere, M5's fire on air
    {"intent": "golden", "name": "legs", "primitives": [box([0, 0, 0], [20, 20, 40]), box([100, 0, 0], [120, 20, 40])]},
    # a small block, whose solid in the sphere burns out before turn 30
    {"intent": "golden", "name": "block", "primitives": [box([0, 0, 0], [20, 20, 20])]},
]


def solid_in_sphere(world: World, name: str) -> int:
    src = world.sources[f"fire:{name}"]
    x, y, z = world.grid.mesh()
    px, py, pz = src.point_m
    inside = (x - px) ** 2 + (y - py) ** 2 + (z - pz) ** 2 <= src.radius_m**2
    return int(np.count_nonzero(inside & world.grid.solid))


def record(raw: dict[str, object], arms: object) -> list[list[object]]:
    spec = protocol.convert(raw, arms)
    world = World(protocol.empty_grid(), limits=action_limits())
    place(world.grid, spec, protocol.OFFSET_M)
    assert Applier(world).apply(spec["name"], Ignite(burn.POWER_W, burn.RADIUS_M)).success
    rows: list[list[object]] = [[solid_in_sphere(world, spec["name"]), None]]
    for _ in range(burn.TURNS):
        world.advance(burn.TURN_S)
        rows.append([solid_in_sphere(world, spec["name"]), repr(reductions.region_integrity(world.grid, spec["name"]))])
    return rows


if __name__ == "__main__":
    arms = protocol.load_arms()
    out = {"engine": "c6d4f10", "specs": SPECS, "turns": {str(s["name"]): record(s, arms) for s in SPECS}}
    with open(sys.argv[1], "w") as f:
        json.dump(out, f, indent=1)
    print({k: (v[0][0], v[-1]) for k, v in out["turns"].items()})
