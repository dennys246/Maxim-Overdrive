"""The simulation (step 5a, `docs/design/sim_core.md`): an integer clock that runs one tick per `step`.

`Simulation` is the world's one owner of time and of the write window. A tick applies its records in the log's key
order, each record's loads resolved right after its stage 2, then runs physics on physics ticks, all in one window:
a tick that raises changes nothing, its source exposure included. It publishes one frame at the tick's end when the
tick applied a record or ran physics, stamped with the tick (§4).

Still to come in step 5a, each named with the PR that ends it: the per-tick digest, the intent log, its header with
the law tuple, and replay (PR 4b, §9, §14); `imagine` as an intent kind (PR 4b, §13).
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from simcore.core.applier import Applier, Outcome
from simcore.core.checks import whole_number
from simcore.core.exposure import SourceExposure
from simcore.core.fields import FIELDS
from simcore.core.frames import CellFrame, Frame, FrameFeed, FrameView
from simcore.core.intents import LogRecord, Strike
from simcore.core.law import Law
from simcore.core.limits import ActionLimits
from simcore.core.materials import MaterialTable
from simcore.core.physics import DEFAULT_LAWS, Physics
from simcore.core.refusals import RefusalCode, Refused
from simcore.core.scene import Scene
from simcore.core.work import Work, WorkCounters
from simcore.core.world import World

_CELL_FIELDS = sum(f.container == "cells" for f in FIELDS)  # what a cell window copies per cell


def _positive(value: object, what: str) -> int:
    n = whole_number(value, what)
    if n < 1:
        raise Refused(f"{what} must be at least 1, got {n}", code=RefusalCode.OUT_OF_RANGE)
    return n


@dataclass(frozen=True)
class SimConfig:
    """The truth constants (tile_and_client.md §6.1, T3; sim_core.md §3): a tick's length in world microseconds, how
    many ticks one physics step covers, and `substep_refine`, the factor the fixed physics step multiplies its
    stability count by (§8; 1 in shipped play, raised by tests to refine time on the shipped path). Integers, so
    nothing stores time as a float."""

    tick_us: int = 100_000
    physics_every: int = 5
    substep_refine: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "tick_us", _positive(self.tick_us, "tick_us"))  # stored as a plain int
        object.__setattr__(self, "physics_every", _positive(self.physics_every, "physics_every"))
        object.__setattr__(self, "substep_refine", _positive(self.substep_refine, "substep_refine"))

    @property
    def physics_seconds(self) -> float:
        """One physics step's length, derived for the laws' float arithmetic where it is needed, never stored."""
        return self.physics_every * self.tick_us / 1_000_000


T3 = SimConfig()


@dataclass(frozen=True)
class TickReport:
    """What one tick did (sim_core.md §4): its records' outcomes in key order (each with its loads' effects), whether
    physics ran, its substeps, and the work counters (§10). Host-side: never a stimulus. The per-tick digest joins
    in PR 4b (§9)."""

    tick: int
    outcomes: tuple[Outcome, ...]
    physics: bool
    substeps: int
    work: WorkCounters


class Clock:
    """The integer tick (sim_core.md §2, §3). Only `Simulation.step` moves it."""

    def __init__(self) -> None:
        self._tick = 1  # tick 0 is construction; the first step runs tick 1

    @property
    def tick(self) -> int:
        return self._tick

    def advance(self) -> None:
        self._tick += 1


class Simulation:
    """The world's one owner of time and of its write window. `step` runs exactly one tick (sim_core.md §4)."""

    def __init__(self, world: World, physics: Physics, *, config: SimConfig) -> None:
        # Private: `from_scene` is the one constructor (§2). The parts are built there, at rest.
        self._world, self._physics, self._config = world, physics, config
        self._applier = Applier(world)
        self._clock = Clock()
        self._exposure = SourceExposure(world.sources, tick=self._clock.tick)  # construction's stand from tick 1
        self._feed = FrameFeed(Frame(CellFrame.of(world.grid, 0, tick=0, time_us=0)))
        self._frames = FrameView(self._feed)
        world.grid.on_roll_back(physics.forget)  # a rolled-back tick leaves no cache a later state could reuse

    @classmethod
    def from_scene(
        cls,
        scene: Scene,
        materials: MaterialTable,
        *,
        dx_m: float,
        config: SimConfig,
        limits: ActionLimits,
        laws: Sequence[Law] = DEFAULT_LAWS,
    ) -> Simulation:
        """The scene voxelized at ``dx_m``, published as frame 0. Tick 0 is construction: it runs no physics.
        ``laws`` is the law tuple (§5), the default in shipped play; the splitting bar runs it reversed (§11 bar 3).
        Every law's caches are built here, eagerly (§2)."""
        grid = scene.build(materials, dx_m=dx_m)
        return cls(World(grid, limits=limits), Physics(grid, laws), config=config)

    @property
    def tick(self) -> int:
        """The tick the next `step` runs."""
        return self._clock.tick

    @property
    def config(self) -> SimConfig:
        return self._config

    @property
    def limits(self) -> ActionLimits:
        """What one action may ask (stage 1 parses against these)."""
        return self._world.limits

    @property
    def frames(self) -> FrameView:
        """The latest published frame (§4), and no way to publish one."""
        return self._frames

    def step(self, records: Iterable[LogRecord]) -> TickReport:
        """Run one tick: apply its records in key order, then physics if it is a physics tick, in one window.

        The batch is read once and checked whole before any of it applies, so a bad batch raises ``ValueError`` and
        changes nothing, and a one-shot iterable loses no record. A tick that raises later changes nothing either: the
        window rolls back, and the clock, the exposure and the frames move only after it commits."""
        tick, batch = self._clock.tick, tuple(records)
        self._check_batch(tick, batch)
        physics = tick % self._config.physics_every == 0
        self._physics.work = work = Work()
        before = self._physics.builds()
        if batch or physics:
            outcomes, substeps = self._run(tick, batch, physics=physics, work=work)
            self._publish(tick, work)
        else:  # a quiet tick: no window, no frame (tile_and_client.md §4)
            outcomes, substeps = (), 0
        after = self._physics.builds()
        work.rebuilds.update({name: n - before.get(name, 0) for name, n in after.items()})
        self._clock.advance()
        return TickReport(tick, outcomes, physics, substeps, work.reading())

    def _run(
        self, tick: int, batch: tuple[LogRecord, ...], *, physics: bool, work: Work
    ) -> tuple[tuple[Outcome, ...], int]:
        """The tick's window: the apply phase, the tick's exposure, then the physics step on a physics tick. A strike
        or physics needs the cells; a tick of fires and douses alone holds the window without copying a cell."""
        exposure, substeps = self._exposure.copy(), 0
        cells = physics or any(isinstance(r.params, Strike) for r in batch)
        with self._world.writing(cells=cells) as sources:
            if cells:
                work.windows_opened += 1
                work.cells_copied += math.prod(self._world.grid.shape) * _CELL_FIELDS
            resolve = self._physics.resolve_loads
            outcomes = tuple(self._applier.apply(r.target, r.params, sources=sources, resolve=resolve) for r in batch)
            exposure.end_tick(tick, sources)
            if physics:
                substeps = self._physics.run(
                    self._config.physics_seconds, refine=self._config.substep_refine, exposure=exposure.step(tick)
                )
        self._exposure = exposure  # only once the window committed
        return outcomes, substeps

    def _publish(self, tick: int, work: Work) -> None:
        sequence = self._feed.latest.sequence + 1
        self._feed.publish(
            Frame(CellFrame.of(self._world.grid, sequence, tick=tick, time_us=tick * self._config.tick_us))
        )
        work.frames_published += 1

    def _check_batch(self, tick: int, batch: tuple[object, ...]) -> None:
        records = []
        for r in batch:
            if not isinstance(r, LogRecord):
                raise ValueError(f"step takes LogRecords, got {type(r).__name__}")
            if r.apply_tick != tick:
                raise ValueError(f"a record for tick {r.apply_tick} reached tick {tick}")
            if r.apply_us >= self._config.tick_us:
                raise ValueError(f"apply_us {r.apply_us} is not within a {self._config.tick_us} us tick")
            records.append(r)
        ids = [(r.actor_id, r.seq) for r in records]
        if len(set(ids)) != len(ids):
            raise ValueError("a batch repeats an (actor_id, seq), the intent id receipts carry (boundaries.md §6.1)")
        keys = [r.key for r in records]
        if any(keys[i + 1] <= keys[i] for i in range(len(keys) - 1)):
            raise ValueError("records must be in strictly increasing key order (boundaries.md §6.2)")
