"""Topology: the one owner of world edits (`docs/design/sim_core.md` §5.1; `world_v2.md` §2.2's choke point).

Construction, `imagine`, the admin material edit and destruction never paint or destroy cells themselves: they make
requests, and `apply` carries out one batch of them as the `topology` writer, in the batch's key order, and the
grid bumps its `topology_version` once when the batch changed anything. A batch is one requester's one invocation: one
record's apply (its stage 2 and its loads), one law's one substep, or construction.

A request's key is its place in the batch: requesters emit their requests in a deterministic order, and no requester
in step 5a emits two that could race. Keyed requests (fuel tables' `pending` rows, `fire_solid.md` §1.4) bring their own
keys when they land.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from simcore.core.fields import CONSTRUCTION, TOPOLOGY
from simcore.core.grid import Footprint, Mask, MaterialGrid


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


def apply(grid: MaterialGrid, requests: Sequence[Request], *, writer: str = TOPOLOGY) -> int:
    """Carry out one batch of world-edit requests, in key order, inside the open window. Returns the cells destroyed.

    ``writer`` is Topology's own name except for construction, the one requester that authors state rather than
    editing it (sim_core.md §6's writers column). The batch is one ``as_writer`` block, so the grid bumps its
    ``topology_version`` once if the batch changed anything (``simcore.core.writers``)."""
    if writer not in (TOPOLOGY, CONSTRUCTION):
        raise ValueError(f"world edits are applied as Topology or construction, not {writer!r}")
    destroyed = 0
    with grid.as_writer(writer):
        for request in requests:
            if isinstance(request, Destroy):
                destroyed += grid.destroy(request.mask)
            elif isinstance(request, Paint):
                grid.paint(request.mask, request.material, region=request.region, footprint=request.footprint)
            else:
                grid.name_region(request.region, request.mask, request.footprint, solid=request.solid)
    return destroyed
