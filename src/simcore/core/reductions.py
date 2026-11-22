"""Region reductions observers read (sim_core.md §5.1: observers read; laws resolve): a region's integrity and whether
it is breached, over a grid at rest or a published frame. Not a law, so no law module holds them."""

from __future__ import annotations

import numpy as np
from scipy import ndimage

from simcore.core.grid import CellState
from simcore.core.materials import AIR_ID


def region_integrity(grid: CellState, region: str) -> float:
    """Mean integrity over the region's original solid cells, destroyed cells counting 0."""
    mask = grid.regions[region].cells & (grid.original_material != AIR_ID)
    n = int(mask.sum())
    return float(grid.integrity[mask].clip(min=0.0).sum() / n) if n else 0.0


def region_breached(grid: CellState, region: str) -> bool:
    """True if destroyed cells form a hole through the region along its thinnest axis (a hole through a wall)."""
    orig = grid.regions[region].cells & (grid.original_material != AIR_ID)
    if not orig.any():
        return False
    idx = np.argwhere(orig)
    lo, hi = idx.min(axis=0), idx.max(axis=0)
    axis = int(np.argmin(hi - lo))
    holes = orig & (grid.material == AIR_ID)
    if not holes.any():
        return False
    labels, _ = ndimage.label(holes)  # holes is non-empty, so there is at least one component
    first = np.take(labels, lo[axis], axis=axis)
    last = np.take(labels, hi[axis], axis=axis)
    return bool(np.intersect1d(first[first > 0], last[last > 0]).size)
