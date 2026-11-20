"""The intent applier: stage 2 of every action, and the only code that changes the world for one (boundaries §3, §6.4).

Stage 1 (``simcore.core.intents.parse_action``) made a typed action inside the limits without reading the world.
Here it is checked against the world as it is now (the region exists and is solid, it has cells left, a strike's
point is on it, something is burning) and then applied inside the world's write window. A refusal at either stage is
an ``Outcome`` that changes nothing. The SEM membrane (``simcore.adapters.sem``) is a gate in front of this. It holds an
``Applier``, which exposes only ``limits`` and ``apply``, and a frame view; what keeps it to those is the import
contracts plus ``tests/test_ownership.py``'s scans for reaching world state by attribute and through re-exports.

The reach and centroid checks are judged from authored footprints in metres, never from cells: a region's cells move
with the grid spacing, so a reach built from them would accept a strike at one spacing and refuse it at another.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from types import MappingProxyType

from simcore.core import damage
from simcore.core.checks import shown
from simcore.core.grid import Point
from simcore.core.intents import AFFORDANCE_OF, Action, ActionRefused, Ignite, Strike
from simcore.core.limits import ActionLimits
from simcore.core.world import HeatSource, World


@dataclass(frozen=True)
class Outcome:
    """What applying one action did. ``params`` are the action's values as applied (finite, JSON-shaped)."""

    affordance: str
    params: Mapping[str, object]
    success: bool
    error: str | None = None
    metadata: Mapping[str, float] = field(default_factory=lambda: MappingProxyType({}))


class Applier:
    """Applies typed actions to one world's regions. It is the write half the SEM bridge used to hold."""

    def __init__(self, world: World) -> None:
        self._world = world

    @property
    def limits(self) -> ActionLimits:
        return self._world.limits

    def apply(self, region: str, action: Action) -> Outcome:
        """Apply a typed action to ``region``: re-checked against this world's limits, then against the world now."""
        if type(action) not in AFFORDANCE_OF:
            raise TypeError(f"not an action: {type(action).__name__}")  # a programming error, not untrusted input
        affordance = AFFORDANCE_OF[type(action)]
        params = MappingProxyType({k: list(v) if isinstance(v, tuple) else v for k, v in asdict(action).items()})
        try:
            action.check(self._world.limits)
            self._check_region(region)
        except ActionRefused as exc:
            return Outcome(affordance, params, False, str(exc))
        # TEMPORARY(phase1/sim-clock): the applier opens the world's write window itself, synchronously, until
        # Simulation.step exists (boundaries §4.1, 2c); there the step owns the window and applies intents in order.
        if isinstance(action, Strike):
            return self._strike(region, action, params)
        if isinstance(action, Ignite):
            return self._ignite(region, action, params)
        return self._extinguish(region, params)

    def _centroid_m(self, region: str) -> Point:
        """Where a fire or an aimless strike lands: the authored centroid, so it doesn't move with the grid spacing."""
        return self._world.grid.regions[region].footprint.centroid_m

    def _check_region(self, region: str) -> None:
        regions = self._world.grid.regions
        if not isinstance(region, str) or region not in regions:
            raise ActionRefused(f"there is no {shown(region)} in this world")
        if not regions[region].solid:
            raise ActionRefused(f"the {region} is air: there is no structure to act on")  # a name in the table
        if not regions[region].cells.any():
            raise ActionRefused(f"the {region} is gone")

    def _on_region(self, region: str, point: Point, sigma_m: float) -> bool:
        """Whether a strike at ``point`` is a strike on ``region``, judged from authored footprints in metres.

        Reach is the region's footprint plus the strike's width, except that a point outside this footprint but
        inside another solid region's belongs to that region: a strike just past the crate's face, into the wall
        beside it, is a strike on the wall. Solids can't overlap (``scene._check_no_solid_overlaps``), and air
        regions such as rooms never own a point.
        """
        regions = self._world.grid.regions

        def inside(name: str, margin: float) -> bool:
            lo, hi = regions[name].footprint.bounds_m
            return all(a - margin <= p <= b + margin for a, p, b in zip(lo, point, hi, strict=True))

        if not inside(region, sigma_m):
            return False
        others = (r for r, other in regions.items() if r != region and other.solid)
        return inside(region, 0.0) or not any(inside(r, 0.0) for r in others)

    def _strike(self, region: str, action: Strike, params: Mapping[str, object]) -> Outcome:
        point = action.point_m if action.point_m is not None else self._centroid_m(region)
        if not self._on_region(region, point, action.sigma_m):
            return Outcome("strike", params, False, f"point_m is not on the {region}")
        with self._world.writing():
            res = damage.strike(self._world.grid, point, action.energy_j, action.sigma_m)
        meta = {"destroyed_volume_m3": res.destroyed_volume_m3, "absorbed_j": res.absorbed_j}
        return Outcome("strike", params, True, metadata=MappingProxyType(meta))

    def _ignite(self, region: str, action: Ignite, params: Mapping[str, object]) -> Outcome:
        # A region carved hollow (a wall with a doorway through its middle) can have its centroid in air, so this fire
        # may heat only air: a known gap, held by a strict red gate. Refusing it here would mean deciding from the
        # region's cells, which move with the grid spacing; the fix is per-cell ownership with authored geometry
        # (design v2).
        source = HeatSource(self._centroid_m(region), action.radius_m, action.power_w)
        with self._world.writing(cells=False) as sources:  # a fire changes no cell until the next advance
            sources[f"fire:{region}"] = source
        return Outcome("ignite", params, True)

    def _extinguish(self, region: str, params: Mapping[str, object]) -> Outcome:
        if f"fire:{region}" not in self._world.sources:
            return Outcome("extinguish", params, False, f"nothing is burning on the {region}")
        with self._world.writing(cells=False) as sources:
            del sources[f"fire:{region}"]
        return Outcome("extinguish", params, True)
