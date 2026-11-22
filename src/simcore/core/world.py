"""The world's cell state (`docs/design/sim_core.md` §2): one grid, its heat sources, and the limits on what one
action may ask of it.

Godot never simulates; it sends intents and draws snapshots (``simcore.protocol.encoding``). Cradles and experiments
run the same `Simulation` headless, so the physics an NPC grows up in is the physics of the game.

The world changes only inside its write window (``World.writing``): the cells through the grid's window, the heat
sources as a private table nobody else holds. One caller opens it, `Simulation.step`, once per tick that needs it;
``tests/test_ownership.py`` holds that. Time, construction and publication are the simulation's.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from types import MappingProxyType

from simcore.core.checks import finite_real, finite_vector
from simcore.core.grid import MaterialGrid
from simcore.core.limits import ActionLimits
from simcore.core.refusals import RefusalCode, Refused


@dataclass(frozen=True)
class HeatSource:
    point_m: tuple[float, float, float]
    radius_m: float
    power_w: float

    def __post_init__(self) -> None:
        # Physical validity, whoever builds the source. Gameplay limits (how big a fire may be) belong to the action
        # that asks for it (simcore.core.limits.ActionLimits, checked by simcore.core.intents).
        object.__setattr__(self, "point_m", finite_vector(self.point_m, 3, "a heat source's point_m"))
        radius = finite_real(self.radius_m, "a heat source's radius_m")
        power = finite_real(self.power_w, "a heat source's power_w")
        if radius <= 0 or power < 0:
            raise Refused(
                f"a heat source needs a positive radius and non-negative power, got {radius!r} m, {power!r} W",
                code=RefusalCode.OUT_OF_RANGE,
            )
        object.__setattr__(self, "radius_m", radius)
        object.__setattr__(self, "power_w", power)


class World:
    """One grid, its heat sources and the limits on what one action may ask of it."""

    def __init__(
        self, grid: MaterialGrid, *, limits: ActionLimits, sources: Mapping[str, HeatSource] | None = None
    ) -> None:
        # limits is required, so a world can't run with no limits or two sets of them. sources is construction's
        # (boundaries §6.4): after it, only the applier changes them.
        self._grid, self._limits = grid, limits
        self._sources: Mapping[str, HeatSource] = MappingProxyType(dict(sources or {}))
        self._adopted = False

    def adopt(self) -> None:
        """Hands the world to its one simulation, the one owner of its time (sim_core.md §2). A second adoption
        raises, so a world another simulation has stepped can't be published again as frame 0, or stepped twice."""
        if self._adopted:
            raise ValueError("this world already has its simulation (sim_core.md §2)")
        self._adopted = True

    @property
    def grid(self) -> MaterialGrid:
        return self._grid

    @property
    def limits(self) -> ActionLimits:
        return self._limits

    @property
    def sources(self) -> Mapping[str, HeatSource]:
        """The heat sources, read-only. The applier changes them, inside the write window."""
        return self._sources

    @contextmanager
    def writing(self, *, cells: bool) -> Iterator[dict[str, HeatSource]]:
        """The write window (boundaries §4.1): a writable copy of the heat sources, a copy of which becomes the
        world's when the window closes, so the dict handed out never is the world's. With ``cells`` it is also the
        grid's window. Without, it holds the same single ownership (``CellStore.holding``) without copying a cell:
        a tick whose records change only sources.

        A window that raises in its body, or while the grid freezes its copies, changes nothing: the sources commit
        only after the cells committed."""
        sources = dict(self._sources)
        if cells:
            with self._grid.writing(writer=None):  # each law, and Topology, narrow to their own names inside
                yield sources
        else:
            with self._grid.holding():
                yield sources
        self._sources = MappingProxyType(dict(sources))
