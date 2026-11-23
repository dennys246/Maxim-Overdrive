"""Topology: the one owner of world edits (`docs/design/sim_core.md` §5.1; `world_v2.md` §2.2's choke point).

Construction, `imagine`, the admin material edit and destruction never paint or destroy cells themselves: they make
requests, and `apply` carries out one batch of them holding Topology's token, the only writer the cells accept an edit
from (`simcore.core.writers`). What a batch is, and the order its requests apply in, are §5.1's.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from simcore.core.fields import TOPOLOGY
from simcore.core.geometry import Mask
from simcore.core.grid import Footprint, MaterialGrid
from simcore.core.writers import claim

_TOPOLOGY = claim(TOPOLOGY)


@dataclass(frozen=True)
class Destroy:
    """Turn the solid cells in ``mask`` to air."""

    mask: Mask


@dataclass(frozen=True)
class Paint:
    """Fill ``mask`` with ``material`` at full integrity, optionally naming it as region ``region``."""

    mask: Mask
    material: str
    region: str | None = None
    footprint: Footprint | None = None


@dataclass(frozen=True)
class NameRegion:
    """Name the cells in ``mask`` as ``region``, without changing what they are made of."""

    region: str
    mask: Mask
    footprint: Footprint
    solid: bool


Request = Destroy | Paint | NameRegion


def apply(grid: MaterialGrid, requests: Iterable[Request]) -> int:
    """Carry out one batch of world-edit requests, in the order they come, inside the open window. Returns the cells
    destroyed. The batch is one block of Topology's, so the grid bumps ``topology_version`` once if it changed
    anything. ``requests`` may be a generator: each request is made as it is applied, so a batch never holds every
    request's mask at once (construction's hundreds of full-grid masks)."""
    destroyed = 0
    with grid.as_writer(_TOPOLOGY):
        for request in requests:
            if isinstance(request, Destroy):
                destroyed += grid.destroy(request.mask)
            elif isinstance(request, Paint):
                grid.paint(request.mask, request.material, region=request.region, footprint=request.footprint)
            else:
                grid.name_region(request.region, request.mask, request.footprint, solid=request.solid)
    return destroyed
