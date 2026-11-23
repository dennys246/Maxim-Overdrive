"""The intent applier: stage 2 of every action, and the only code that changes the world for one (boundaries §3, §6.4).

Stage 1 (``simcore.core.intents.parse_action``) made a typed action inside the limits without reading the world.
Here it is checked against the world as it is now (the region exists and is solid, it has cells left, a strike's
point is on it, something is burning) and then applied, inside the tick's write window, which `Simulation.step` opens
(sim_core.md §13): an ignite or a douse edits the window's sources, and a strike puts a `Load` in, which the per-record
laws resolve right after (§5.1). A refusal at either stage is an ``Outcome`` that changes nothing. Nothing outside the
simulation holds an applier: every input reaches the world as a record through `Simulation.step` (§4).

The reach and centroid checks are judged from authored footprints in metres, never from cells: a region's cells move
with the grid spacing, so a reach built from them would accept a strike at one spacing and refuse it at another.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from types import MappingProxyType

from simcore.core.checks import shown
from simcore.core.grid import Point
from simcore.core.intents import AFFORDANCE_OF, Action, ActionRefused, Ignite, Strike
from simcore.core.law import Load, LoadEffect
from simcore.core.refusals import RefusalCode, Refused, agent_text
from simcore.core.world import HeatSource, World


@dataclass(frozen=True)
class Outcome:
    """What applying one action did. ``params`` are the action's values as applied (finite, JSON-shaped). A refusal
    carries its ``code`` (and the schema ``field`` at fault, if one is), which is all an agent is told, and ``error``,
    the words, for logs and tests. ``effects`` are what its loads did (a strike's destroyed volume and absorbed
    energy): host-side effects in the tick's report, never a stimulus (sim_core.md §4)."""

    affordance: str
    params: Mapping[str, object]
    success: bool
    error: str | None = None
    effects: tuple[LoadEffect, ...] = ()
    code: RefusalCode | None = None
    field: str | None = None

    def __post_init__(self) -> None:
        if (self.code is None) != self.success:  # a refusal the agent can't be told is a programming error
            raise TypeError(f"an outcome carries a code exactly when it is refused: {self.success}, {self.code}")

    @property
    def agent_text(self) -> str | None:
        """The refusal in the closed vocabulary (boundaries §5.4), or None when the action was applied."""
        return None if self.code is None else agent_text(self.code, self.field)


def _refused(affordance: str, params: Mapping[str, object], exc: Refused) -> Outcome:
    return Outcome(affordance, params, False, str(exc), code=exc.code, field=exc.field)


Resolve = Callable[[Sequence[Load]], tuple[LoadEffect, ...]]


class Applier:
    """Applies typed actions to one world's regions, inside the tick's window (`Simulation.step`'s)."""

    def __init__(self, world: World) -> None:
        self._world = world

    def apply(self, region: str, action: Action, *, sources: dict[str, HeatSource], resolve: Resolve) -> Outcome:
        """Apply a typed action to ``region``: re-checked against this world's limits, then against the world now.
        ``sources`` is the open window's sources table, and ``resolve`` the per-record laws (sim_core.md §5.1)."""
        if type(action) not in AFFORDANCE_OF:
            raise TypeError(f"not an action: {type(action).__name__}")  # a programming error, not untrusted input
        affordance = AFFORDANCE_OF[type(action)]
        params = MappingProxyType({k: list(v) if isinstance(v, tuple) else v for k, v in asdict(action).items()})
        try:
            action.check(self._world.limits)
            self._check_region(region)
        except ActionRefused as exc:
            return _refused(affordance, params, exc)
        if isinstance(action, Strike):
            return self._strike(region, action, params, resolve)
        if isinstance(action, Ignite):
            return self._ignite(region, action, params, sources)
        return self._extinguish(region, params, sources)

    def _centroid_m(self, region: str) -> Point:
        """Where a fire or an aimless strike lands: the authored centroid, so it doesn't move with the grid spacing."""
        return self._world.grid.regions[region].footprint.centroid_m

    def _check_region(self, region: str) -> None:
        regions = self._world.grid.regions
        if not isinstance(region, str) or region not in regions:
            raise ActionRefused(f"there is no {shown(region)} in this world", code=RefusalCode.NO_REGION)
        if not regions[region].solid:  # a name in the table
            raise ActionRefused(f"the {region} is air: there is no structure to act on", code=RefusalCode.NOT_SOLID)
        # Gone: authored geometry (a later paint) took every cell. Not destruction: whether any cell survives a strike
        # depends on the grid spacing, so deciding on it would refuse at one spacing and accept at another (PR 4a
        # review, Exec S2; owner, 2026-11-22). A strike on a destroyed region applies and destroys nothing.
        if not regions[region].cells.any():
            raise ActionRefused(f"the {region} is gone", code=RefusalCode.REGION_GONE)

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

    def _strike(self, region: str, action: Strike, params: Mapping[str, object], resolve: Resolve) -> Outcome:
        point = action.point_m if action.point_m is not None else self._centroid_m(region)
        if not self._on_region(region, point, action.sigma_m):
            refusal = ActionRefused(f"point_m is not on the {region}", code=RefusalCode.NOT_ON_REGION, field="point_m")
            return _refused("strike", params, refusal)
        # The strike is a load: damage resolves it right after this stage 2, and Topology destroys (§5.1).
        effects = resolve((Load("strike", point, action.energy_j, action.sigma_m),))
        return Outcome("strike", params, True, effects=effects)

    def _ignite(
        self, region: str, action: Ignite, params: Mapping[str, object], sources: dict[str, HeatSource]
    ) -> Outcome:
        # A region carved hollow (a wall with a doorway through its middle) can have its centroid in air, so this fire
        # may heat only air: a known gap, held by a strict red gate. Refusing it here would mean deciding from the
        # region's cells, which move with the grid spacing; the fix is per-cell ownership with authored geometry
        # (design v2).
        sources[f"fire:{region}"] = HeatSource(self._centroid_m(region), action.radius_m, action.power_w)
        return Outcome("ignite", params, True)  # a fire changes no cell until the next physics step

    def _extinguish(self, region: str, params: Mapping[str, object], sources: dict[str, HeatSource]) -> Outcome:
        if f"fire:{region}" not in sources:  # the window's table: an earlier record this tick may have lit it
            refusal = ActionRefused(f"nothing is burning on the {region}", code=RefusalCode.NOT_BURNING)
            return _refused("extinguish", params, refusal)
        del sources[f"fire:{region}"]
        return Outcome("extinguish", params, True)
