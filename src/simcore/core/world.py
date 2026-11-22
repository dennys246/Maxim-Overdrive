"""The authoritative world: one grid, its heat sources, and a fixed-length turn.

Godot never simulates; it sends intents and draws snapshots (``simcore.protocol.encoding``). Cradles and experiments
run this same object headless, so the physics an NPC grows up in is the physics of the game.

The world changes only inside its write window (``World.writing``): the cells through the grid's window, the heat
sources as a private table nobody else holds. Two callers open it, ``advance`` and the intent applier
(``simcore.core.applier``); ``tests/test_ownership.py`` holds that list. Each window that closes publishes a frame
(``simcore.core.frames``), which is what observers read.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from types import MappingProxyType

from simcore.core import physics
from simcore.core.checks import finite_real, finite_vector
from simcore.core.deposit import Deposit
from simcore.core.exposure import Exposure, standing
from simcore.core.frames import CellFrame, Frame, FrameFeed, FrameView
from simcore.core.grid import Field, MaterialGrid
from simcore.core.law import Law
from simcore.core.limits import ActionLimits
from simcore.core.materials import MaterialTable
from simcore.core.refusals import RefusalCode, Refused
from simcore.core.scene import Scene


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
    """One grid, its heat sources, its turn count and the limits on what one action may ask of it."""

    def __init__(
        self,
        grid: MaterialGrid,
        turn_seconds: float = 6.0,
        *,
        limits: ActionLimits,
        sources: Mapping[str, HeatSource] | None = None,
    ) -> None:
        # limits is required, so a world can't run with no limits or two sets of them. sources is construction's
        # (boundaries §6.4): after it, only the applier changes them.
        self._grid, self._limits, self._turn = grid, limits, 0
        self._turn_seconds = finite_real(turn_seconds, "turn_seconds")
        if not self._turn_seconds > 0:
            raise ValueError(f"turn_seconds must be positive, got {turn_seconds!r}")
        self._sources: Mapping[str, HeatSource] = MappingProxyType(dict(sources or {}))
        self._deposit = Deposit(grid)
        self._feed = FrameFeed(Frame(CellFrame.of(grid, 0)))
        self._frames = FrameView(self._feed)
        grid.on_close(self._publish)

    @classmethod
    def from_scene(
        cls,
        scene: Scene,
        materials: MaterialTable,
        turn_seconds: float = 6.0,
        *,
        dx_m: float,
        limits: ActionLimits,
    ) -> World:
        """The scene voxelized at grid spacing ``dx_m``, the simulation's one truth (world_model D20)."""
        return cls(scene.build(materials, dx_m=dx_m), turn_seconds, limits=limits)

    @property
    def grid(self) -> MaterialGrid:
        return self._grid

    @property
    def limits(self) -> ActionLimits:
        return self._limits

    @property
    def turn_seconds(self) -> float:
        return self._turn_seconds

    @property
    def turn(self) -> int:
        return self._turn

    @property
    def sources(self) -> Mapping[str, HeatSource]:
        """The heat sources, read-only. The applier changes them, inside the write window."""
        return self._sources

    @property
    def frames(self) -> FrameView:
        """Where observers read this world: the latest published frame, and nothing that can publish one (§4.2)."""
        return self._frames

    def _publish(self) -> None:
        self._feed.publish(Frame(CellFrame.of(self._grid, self._feed.latest.sequence + 1)))

    @contextmanager
    def writing(self, *, cells: bool = True) -> Iterator[dict[str, HeatSource]]:
        """The write window (boundaries §4.1): a writable copy of the heat sources, a copy of which becomes the
        world's when the window closes, so the dict handed out never is the world's. With ``cells`` (the default) it is
        also the grid's window. ``cells=False`` holds the same single ownership (``CellStore.holding``) without copying
        a cell. Either way a frame is published when it closes, so every application has its after-frame; after a
        sources-only window it holds the same immutable owners, so it costs no copy.

        A window that raises in its body, or while the grid freezes its copies, changes nothing. The order on success
        is: the cells commit, the frame is published, then the sources commit; so if publishing itself raised, the
        cells would be committed and the sources not (no shipped path raises there)."""
        sources = dict(self._sources)
        if cells:
            with self._grid.writing(writer=None):  # each law, and Topology, narrow to their own names inside
                yield sources
        else:
            with self._grid.holding():
                yield sources
        self._sources = MappingProxyType(dict(sources))  # committed after the grid's window committed
        if not cells:
            self._publish()

    def _power_field(self, exposure: Exposure) -> Field | None:
        # TEMPORARY(phase1/sim-clock): the world holds its sources' deposit and heat consumes the power, while the
        # registry names heat as the sources' resolver (sim_core.md §6, §7): step 5a's PR 4, which moves the window
        # into Simulation.step, hands the sources to heat's prepare. The deposit is already sorted and cached (PR 3).
        return self._deposit.power(exposure.shares, exposure.of_ticks)

    def advance(
        self,
        seconds: float | None = None,
        *,
        refine: int = 1,
        exposure: Exposure | None = None,
        laws: Sequence[Law] = physics.DEFAULT_LAWS,
    ) -> int:
        """Run ``laws`` for one turn (or ``seconds``, a whole number of microseconds) as one fixed physics step, its
        substeps refined ``refine`` times (``SimConfig.substep_refine``), and move the clock by it. ``exposure`` is
        the step's source shares (``Simulation``'s ``source_exposure``, sim_core.md §3); without it, the sources
        standing now stand the whole step. Returns the substeps taken."""
        seconds = self._turn_seconds if seconds is None else seconds
        interval_us = round(seconds * 1_000_000)
        if interval_us / 1_000_000 != seconds or interval_us <= 0:  # time never stands still or runs backward
            raise ValueError(f"a physics step is a positive whole number of microseconds, got {seconds!r} s")
        step = Exposure(standing(self._sources, 1), 1) if exposure is None else exposure

        def power() -> Field | None:  # read on each refresh, inside the window
            return self._power_field(step)

        # TEMPORARY(phase1/sim-clock): World.advance owns the write window for the law tuple until Simulation.step owns
        # it (boundaries §4.1, 2c; sim_core.md §12): step 5a's PR 4 moves the window there, and this goes.
        with self.writing():
            taken = physics.run_physics(self._grid, seconds, refine=refine, power=power, laws=laws)
            self._grid.time_us += interval_us  # integer time, moved by the interval's owner (sim_core.md §3)
        self._turn += 1  # after the window, so a step that raises counts no turn
        return taken
