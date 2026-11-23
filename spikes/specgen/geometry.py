"""Authored-shape metrics for the spec generator spike (plan.md §5, M2 and M7). Throwaway spike code.

Every geometric predicate is judged in whole micrometres on the spec's own frame (before the scene offset), so a face
authored to touch another is a touch whatever float its centimetres became: in floats 0.23 - 0.12 is
0.11000000000000001, so a float comparison with an 0.11 m radius would miss that tangent.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from simcore.core.digest import digest
from simcore.core.scene import Box, Cylinder, Primitive

THIN_M = 0.4  # plan §5 M2: the thin-feature rule's 0.4 m


def um(value_m: float) -> int:
    return round(value_m * 1_000_000)


@dataclass(frozen=True)
class Shape:
    """A primitive in whole micrometres: a box's bounds, or an upright cylinder's centre, radius and z range."""

    box: tuple[tuple[int, int, int], tuple[int, int, int]] | None
    cyl: tuple[int, int, int, int, int] | None  # cx, cy, r, z0, z1

    @property
    def z(self) -> tuple[int, int]:
        if self.box is not None:
            return self.box[0][2], self.box[1][2]
        assert self.cyl is not None
        return self.cyl[3], self.cyl[4]


def shape(p: Primitive) -> Shape:
    if isinstance(p, Box):
        lo = (um(p.min_m[0]), um(p.min_m[1]), um(p.min_m[2]))
        hi = (um(p.max_m[0]), um(p.max_m[1]), um(p.max_m[2]))
        return Shape((lo, hi), None)
    assert isinstance(p, Cylinder)
    c = p.center_xy_m
    return Shape(None, (um(c[0]), um(c[1]), um(p.radius_m), um(p.z_m[0]), um(p.z_m[1])))


def _overlap(a0: int, a1: int, b0: int, b1: int) -> bool:
    return a0 <= b1 and b0 <= a1  # closed intervals: touching counts


def _box_cyl(box: tuple[tuple[int, int, int], tuple[int, int, int]], cyl: tuple[int, int, int, int, int]) -> bool:
    (x0, y0, _), (x1, y1, _) = box
    cx, cy, r, _, _ = cyl
    nx, ny = min(max(cx, x0), x1), min(max(cy, y0), y1)
    return (cx - nx) ** 2 + (cy - ny) ** 2 <= r * r


def touches(a: Shape, b: Shape) -> bool:
    """Touching or overlapping, judged exactly in integers."""
    if not _overlap(*a.z, *b.z):
        return False
    if a.box is not None and b.box is not None:
        return all(_overlap(a.box[0][i], a.box[1][i], b.box[0][i], b.box[1][i]) for i in range(2))
    if a.cyl is not None and b.cyl is not None:
        return (a.cyl[0] - b.cyl[0]) ** 2 + (a.cyl[1] - b.cyl[1]) ** 2 <= (a.cyl[2] + b.cyl[2]) ** 2
    box, cyl = (a.box, b.cyl) if a.box is not None else (b.box, a.cyl)
    assert box is not None
    assert cyl is not None
    return _box_cyl(box, cyl)


def components(prims: Sequence[Primitive]) -> int:
    """M2 (c): connected components of the contact graph, with the floor (z = 0) as one more node."""
    shapes = [shape(p) for p in prims]
    parent = list(range(len(shapes) + 1))  # the last node is the floor

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def join(i: int, j: int) -> None:
        parent[find(i)] = find(j)

    floor = len(shapes)
    for i, s in enumerate(shapes):
        if s.z[0] == 0:
            join(i, floor)
        for j in range(i + 1, len(shapes)):
            if touches(s, shapes[j]):
                join(i, j)
    return len({find(i) for i in range(len(shapes) + 1)})


def smallest_side_m(p: Primitive) -> float:
    if isinstance(p, Box):
        return min(h - lo for lo, h in zip(p.min_m, p.max_m, strict=True))
    assert isinstance(p, Cylinder)
    return min(2 * p.radius_m, p.z_m[1] - p.z_m[0])


def thin_fraction(prims: Sequence[Primitive]) -> float:
    """M2's report: the fraction of authored volume in primitives whose smallest side is under 0.4 m."""
    total = sum(p.volume_m3 for p in prims)
    thin = sum(p.volume_m3 for p in prims if smallest_side_m(p) < THIN_M)
    return thin / total if total > 0 else 0.0


def spec_id(spec: Mapping[str, Any]) -> str:
    """ip_and_licensing.md §6 item 1: the content is every accepted key except `name`, today `primitives`, with each
    primitive's own optional `name` left out too."""
    prims = [{k: v for k, v in p.items() if k != "name"} for p in spec.get("primitives", []) if isinstance(p, dict)]
    return digest({"primitives": prims})


def raster(prims: Sequence[Primitive]) -> np.ndarray[Any, np.dtype[np.bool_]]:
    """M7's 1 cm analysis raster, after the spec's minimum is moved to the origin. A cell is in a primitive when its
    centre is, judged in integer half-centimetres."""
    shapes = [shape(p) for p in prims]
    cm = [_cm(s) for s in shapes]
    lo = [min(c[0][i] for c in cm) for i in range(3)]
    hi = [max(c[1][i] for c in cm) for i in range(3)]
    grid = np.zeros(tuple(max(1, h - lo_) for lo_, h in zip(lo, hi, strict=True)), dtype=np.bool_)
    for s, (b0, b1) in zip(shapes, cm, strict=True):
        sl = tuple(slice(b0[i] - lo[i], b1[i] - lo[i]) for i in range(3))
        if s.box is not None:
            grid[sl] = True
        else:
            grid[sl] |= _disc(s, b0, b1)
    return grid


def _cm(s: Shape) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    def c(v: int, up: bool) -> int:
        return -(-v // 10_000) if up else v // 10_000

    if s.box is not None:
        lo, hi = s.box
        return (c(lo[0], False), c(lo[1], False), c(lo[2], False)), (c(hi[0], True), c(hi[1], True), c(hi[2], True))
    assert s.cyl is not None
    cx, cy, r, z0, z1 = s.cyl
    return (c(cx - r, False), c(cy - r, False), c(z0, False)), (c(cx + r, True), c(cy + r, True), c(z1, True))


def _disc(s: Shape, b0: tuple[int, int, int], b1: tuple[int, int, int]) -> np.ndarray[Any, np.dtype[np.bool_]]:
    assert s.cyl is not None
    cx, cy, r, _, _ = s.cyl
    i = np.arange(b0[0], b1[0], dtype=np.int64)[:, None]
    j = np.arange(b0[1], b1[1], dtype=np.int64)[None, :]
    # A cell's centre in micrometres is 10,000 * index + 5,000; compare squared distances exactly in int64.
    inside = (i * 10_000 + 5_000 - cx) ** 2 + (j * 10_000 + 5_000 - cy) ** 2 <= r * r
    return np.broadcast_to(inside[:, :, None], (b1[0] - b0[0], b1[1] - b0[1], b1[2] - b0[2]))


def iou(a: np.ndarray[Any, np.dtype[np.bool_]], b: np.ndarray[Any, np.dtype[np.bool_]]) -> float:
    shape_ = tuple(max(x, y) for x, y in zip(a.shape, b.shape, strict=True))
    pa = np.zeros(shape_, dtype=np.bool_)
    pb = np.zeros(shape_, dtype=np.bool_)
    pa[tuple(slice(0, n) for n in a.shape)] = a
    pb[tuple(slice(0, n) for n in b.shape)] = b
    union = int(np.count_nonzero(pa | pb))
    return int(np.count_nonzero(pa & pb)) / union if union else 1.0


def vendi(rasters: Sequence[np.ndarray[Any, np.dtype[np.bool_]]]) -> tuple[float, float]:
    """M7: the Vendi score at orders 0.5 and infinity, with volume IoU as the kernel."""
    n = len(rasters)
    k = np.ones((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            k[i, j] = k[j, i] = iou(rasters[i], rasters[j])
    lam = np.clip(np.linalg.eigvalsh(k / n), 0.0, None)
    half = float(np.sum(np.sqrt(lam)) ** 2)  # exp(log(sum lam^q) / (1 - q)) at q = 0.5
    return half, float(1.0 / lam.max())
