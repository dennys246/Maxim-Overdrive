"""What a body can reach: the nearest of some boxes within a distance, in front of it (kindle, strike, the vendor).

In front means within 60 degrees of the body's facing (cos 60 = 0.5), judged in the x-y plane from the body's axis
to the box's nearest point; touching a box counts as in front.
"""

from __future__ import annotations

import math
from collections.abc import Iterable

from slice_server.body import Body
from slice_server.fire import Bounds


def distance_in_front(body: Body, bounds: Bounds, reach_m: float) -> float | None:
    """The distance to ``bounds`` if it is within ``reach_m`` and in front of ``body``, else None."""
    (x0, y0, _), (x1, y1, _) = bounds
    nx, ny = min(max(body.x, x0), x1), min(max(body.y, y0), y1)
    dist = math.hypot(nx - body.x, ny - body.y)
    if dist > reach_m:
        return None
    ahead = dist < 1e-9 or (nx - body.x) * math.cos(body.yaw) + (ny - body.y) * math.sin(body.yaw) >= 0.5 * dist
    return dist if ahead else None


def nearest_in_front(body: Body, boxes: Iterable[tuple[str, Bounds]], reach_m: float) -> str | None:
    """The name of the nearest box in front of ``body`` within ``reach_m``; ties go to the first name in order."""
    best: tuple[float, str] | None = None
    for name, bounds in sorted(boxes):
        dist = distance_in_front(body, bounds, reach_m)
        if dist is not None and (best is None or dist < best[0]):
            best = (dist, name)
    return None if best is None else best[1]
