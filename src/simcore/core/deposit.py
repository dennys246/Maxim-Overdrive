"""Where a heat source's power lands: its sphere's overlap with the cells, and the per-source caches (sim_core.md §7).

A fire heats the material it burns on, so a source's weights are its overlap with solid cells, normalised to one; a
source over air only falls back to its whole overlap, and one smaller than a cell to the cell it sits in. Air only
conducts here (no convection yet), so power dumped into air cells would sit there, and how much of it did would
depend on the grid spacing.

The overlap is computed over the source's bounding box padded by one cell. It is bit-identical to the whole-grid
computation because every overlap value is a multiple of 1/64 (the 4^3 sub-sample), so the sums are exact in any order
(`reviews/sim_core/fold.md`); `tests/test_deposit.py` holds it to the whole-grid reference. Sources accumulate in
sorted-key order (`boundaries.md` §6.2), so the power field doesn't depend on the order sources were added.

Not a law: laws don't import each other, and this is the sources' resolver that heat's power reads.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from simcore.core.exposure import Point, Share, Source
from simcore.core.grid import Field, MaterialGrid
from simcore.core.readonly import frozen

Box = tuple[slice, slice, slice]
Weights = tuple[Box, Field, float]  # a source's box, its unnormalised weights there, and their sum
SAMPLES = 4  # per cell per axis: overlap values are multiples of 1 / SAMPLES**3, which keeps the box exact


def bounding_box(grid: MaterialGrid, center_m: Point, radius_m: float) -> Box:
    """The cells a sphere can touch, padded by one cell on each side against rounding, clipped to the grid."""
    out = []
    for c, n in zip(center_m, grid.shape, strict=True):
        lo = max(0, int(np.floor((c - radius_m) / grid.dx)) - 1)  # floored as MaterialGrid.cell_of floors
        hi = min(n, int(np.floor((c + radius_m) / grid.dx)) + 2)
        out.append(slice(lo, max(lo, hi)))
    return out[0], out[1], out[2]


def sphere_overlap(grid: MaterialGrid, center_m: Point, radius_m: float, box: Box | None = None) -> Field:
    """Fraction of each cell in ``box`` (default the whole grid) inside a sphere, on a SAMPLES^3 sub-grid per cell.

    Weighting by overlap rather than by "centre inside" keeps a source's power density the same at every grid spacing;
    with centre-inside, a 0.3 m fire at 0.2 m cells covered 35% more volume than the sphere and ran cooler.
    """
    box = box or (slice(0, grid.shape[0]), slice(0, grid.shape[1]), slice(0, grid.shape[2]))
    offs = (np.arange(SAMPLES) + 0.5) / SAMPLES * grid.dx
    base = [np.arange(s.start, s.stop) * grid.dx for s in box]  # global indices, so each cell's samples are the same
    frac = np.zeros(tuple(len(b) for b in base), dtype=np.float64)
    cx, cy, cz = center_m
    for ox in offs:
        dx2 = ((base[0] + ox - cx) ** 2)[:, None, None]
        for oy in offs:
            dy2 = ((base[1] + oy - cy) ** 2)[None, :, None]
            for oz in offs:
                dz2 = ((base[2] + oz - cz) ** 2)[None, None, :]
                frac += (dx2 + dy2 + dz2) <= radius_m**2
    return frac / SAMPLES**3


class Deposit:
    """The sources' power per cell, with sim_core.md §7's caches: each source's overlap per ``(point_m, radius_m)``
    (the grid's spacing and shape are fixed), and its solid-weighted weights and their sum per ``(point_m, radius_m,
    topology_version)``. Each call keeps only the entries the current sources need, and a window that rolls back
    empties them through `forget` (it restores ``topology_version``, so a later edit could reach a version an entry
    already names): the caches' contents are a function of state."""

    def __init__(self, grid: MaterialGrid) -> None:
        self._grid = grid
        self._overlaps: dict[tuple[Point, float], tuple[Box, Field]] = {}
        self._weights: dict[tuple[Point, float, int], Weights] = {}
        self.rebuilds = 0  # overlaps and weights built, a work counter (sim_core.md §10)

    def forget(self) -> None:
        """Drop every entry: the owner's rollback listener calls this (heat's state, sim_core.md §7)."""
        self._overlaps, self._weights = {}, {}

    def power(self, shares: Sequence[Share], of_ticks: int) -> Field | None:
        """The step's mean power per cell in watts: each share's power times the fraction ``ticks / of_ticks`` of the
        step it stood, so a share delivers ``power * ticks * tick_us`` over the step (sim_core.md §3). The ticks are
        counted in integers; the fraction is the energy rule's one float, so a share of 2 in 5 holds only to rounding
        (PR 3 review, Performance N2). Accumulated in the order given, which the caller sorts by key and then tick;
        None when there are no shares."""
        if not shares:
            self.forget()
            return None
        power = np.zeros(self._grid.shape, dtype=np.float64)
        overlaps: dict[tuple[Point, float], tuple[Box, Field]] = {}
        weights: dict[tuple[Point, float, int], Weights] = {}
        version = self._grid.topology_version
        for share in shares:
            src, ticks = share.source, share.ticks
            shape = (src.point_m, src.radius_m)
            overlaps[shape] = overlaps.get(shape) or self._overlaps.get(shape) or self._overlap(src)
            wkey = (src.point_m, src.radius_m, version)
            weights[wkey] = weights.get(wkey) or self._weights.get(wkey) or self._normalised(src, overlaps[shape])
            box, w, total = weights[wkey]
            # This order of operations, so the field is the reference's bits: a share that stood the whole step has
            # the fraction 1.0 exactly, and multiplying by it changes no bit.
            power[box] += src.power_w * (ticks / of_ticks) * w / total
        self._overlaps, self._weights = overlaps, weights
        return power

    def _overlap(self, src: Source) -> tuple[Box, Field]:
        self.rebuilds += 1
        box = bounding_box(self._grid, src.point_m, src.radius_m)  # cached entries are frozen: every hit shares them
        return box, frozen(sphere_overlap(self._grid, src.point_m, src.radius_m, box))

    def _normalised(self, src: Source, overlap: tuple[Box, Field]) -> Weights:
        self.rebuilds += 1
        box, frac = overlap
        on_solid = frac * self._grid.solid[box]
        weights = on_solid if on_solid.sum() > 0 else frac
        if weights.sum() == 0:  # a source smaller than a cell heats the cell it sits in
            weights = np.zeros(frac.shape)
            cell = self._grid.cell_of(src.point_m)
            weights[tuple(i - s.start for i, s in zip(cell, box, strict=True))] = 1.0
        return box, frozen(weights), float(weights.sum())
