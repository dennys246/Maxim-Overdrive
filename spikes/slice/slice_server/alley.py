"""The slice's alley: the tile spec's boxes (``tile_and_client.md`` §1), authored in metres.

The crate is plain wood here, not the tile spec's porous bed: the bed is step 6's, and the slice's fire is its own
fuel budget (plan §3.3). Week 2 adds the pallet stack beside the crate, close enough for the crate's fire to light
it by radiation, and the puddle: a patch of floor under a gap in the awning where rain keeps it wet. Week 3 adds the
glass and drywall.
"""

from __future__ import annotations

from simcore.core.scene import Box, Scene

EXTENT_M = (12.0, 4.0, 4.8)
FLOOR_TOP_M = 0.4
SPAWN_M = (0.6, 2.0)  # on the pavement at the alley's mouth (x 0-1.2 m)
# The pallet stack, on whole cells: a 0.4 m gap east of the crate. Its near face is 0.7 m from the crate's centroid,
# so the crate's fire at full burn puts about 17 kW/m^2 on it (the point-source law), above wood's critical flux for
# ignition of about 12 kW/m^2.
PALLET_MIN_M, PALLET_MAX_M = (7.0, 2.6, FLOOR_TOP_M), (7.6, 3.2, 1.0)
# The puddle, (x0, y0, x1, y1) in metres: by the south wall, between the mouth and the crate.
PUDDLE_XY = (3.0, 0.4, 4.4, 1.6)


def scene() -> Scene:
    return Scene(
        EXTENT_M,
        (
            Box((0.0, 0.0, 0.0), (12.0, 4.0, FLOOR_TOP_M), "concrete", "floor"),
            Box((1.2, 0.0, 0.4), (12.0, 0.4, 4.4), "concrete", "wall_south"),
            Box((1.2, 3.6, 0.4), (12.0, 4.0, 4.4), "concrete", "wall_north"),
            Box((11.6, 0.4, 0.4), (12.0, 3.6, 4.4), "concrete", "wall_end"),
            Box((6.0, 2.6, 0.4), (6.6, 3.2, 1.0), "wood", "crate"),
            Box(PALLET_MIN_M, PALLET_MAX_M, "wood", "pallet"),
            Box((9.0, 0.8, 0.4), (9.6, 1.4, 1.0), "wood", "crate_far"),
        ),
    )


def in_puddle(x: float, y: float) -> bool:
    x0, y0, x1, y1 = PUDDLE_XY
    return x0 <= x <= x1 and y0 <= y <= y1
