"""The slice's alley: the tile spec's boxes (``tile_and_client.md`` §1), authored in metres.

The crate is plain wood here, not the tile spec's porous bed: the bed is step 6's, and the slice's fire is its own
fuel budget (plan §3.3, week 2). Week 2 adds the pallet beside the crate; week 3 the glass and drywall.
"""

from __future__ import annotations

from simcore.core.scene import Box, Scene

EXTENT_M = (12.0, 4.0, 4.8)
FLOOR_TOP_M = 0.4
SPAWN_M = (0.6, 2.0)  # on the pavement at the alley's mouth (x 0-1.2 m)


def scene() -> Scene:
    return Scene(
        EXTENT_M,
        (
            Box((0.0, 0.0, 0.0), (12.0, 4.0, FLOOR_TOP_M), "concrete", "floor"),
            Box((1.2, 0.0, 0.4), (12.0, 0.4, 4.4), "concrete", "wall_south"),
            Box((1.2, 3.6, 0.4), (12.0, 4.0, 4.4), "concrete", "wall_north"),
            Box((11.6, 0.4, 0.4), (12.0, 3.6, 4.4), "concrete", "wall_end"),
            Box((6.0, 2.6, 0.4), (6.6, 3.2, 1.0), "wood", "crate"),
            Box((9.0, 0.8, 0.4), (9.6, 1.4, 1.0), "wood", "crate_far"),
        ),
    )
