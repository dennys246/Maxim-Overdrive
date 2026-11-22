"""The simulation (step 5a, `docs/design/sim_core.md`): an integer clock that runs one tick per `step`.

This is step 5a's strangler wrap: `Simulation` drives `World`. A tick applies its records through the applier, in
the log's key order, then runs physics on physics ticks through `World.advance`, which runs the law tuple
(`simcore.core.physics`, PR 2), so heat, damage and the substep floor are exactly as before. PRs 3-4 move the rest
inside: the fixed physics step, and the intent log with its per-tick digest.

Interim departures from sim_core.md, each named with the PR that ends it:
- the `Simulation(world, *, config)` seam beside `from_scene` (marked below; PR 4, when `Simulation` carries the
  per-tick digest the tests compare);
- frames are still published when a write window closes, so a tick with two records publishes two and a refusal-only
  tick publishes none, and frames carry no tick (§4's cadence, `tile_and_client.md` §4; PR 4, with the record path);
- the world's time is still `grid.time_s`, a float that `World.advance` accumulates (§2 retires it; PR 3, with the
  fixed physics step).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from simcore.core.applier import Applier, Outcome
from simcore.core.checks import whole_number
from simcore.core.frames import FrameView
from simcore.core.intents import LogRecord
from simcore.core.limits import ActionLimits
from simcore.core.materials import MaterialTable
from simcore.core.refusals import RefusalCode, Refused
from simcore.core.scene import Scene
from simcore.core.world import World


def _positive(value: object, what: str) -> int:
    n = whole_number(value, what)
    if n < 1:
        raise Refused(f"{what} must be at least 1, got {n}", code=RefusalCode.OUT_OF_RANGE)
    return n


@dataclass(frozen=True)
class SimConfig:
    """The truth constants (tile_and_client.md §6.1, T3): a tick's length in world microseconds, and how many ticks
    one physics step covers. Integers, so nothing stores time as a float (sim_core.md §3). §3's third constant,
    `substep_refine`, joins with the fixed physics step in step 5a's PR 3."""

    tick_us: int = 100_000
    physics_every: int = 5

    def __post_init__(self) -> None:
        object.__setattr__(self, "tick_us", _positive(self.tick_us, "tick_us"))  # stored as a plain int
        object.__setattr__(self, "physics_every", _positive(self.physics_every, "physics_every"))

    @property
    def physics_seconds(self) -> float:
        """One physics step's length, derived for the laws' float arithmetic where it is needed, never stored."""
        return self.physics_every * self.tick_us / 1_000_000


T3 = SimConfig()


@dataclass(frozen=True)
class TickReport:
    """What one tick did: its records' outcomes in key order, and whether physics ran and how many substeps it took.
    The per-tick digest and the work counters join in PR 4 (sim_core.md §4, §9, §10)."""

    tick: int
    outcomes: tuple[Outcome, ...]
    physics: bool
    substeps: int


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
    """The world's one owner of time. `step` runs exactly one tick (sim_core.md §4)."""

    def __init__(self, world: World, *, config: SimConfig) -> None:
        # TEMPORARY(phase1/sim-clock): this seam wraps a World the caller built and still holds, so the strangler
        # tests can compare digest(world) against direct World calls; sim_core.md §4's one constructor is from_scene.
        # Step 5a's PR 4 removes it, when Simulation carries the per-tick digest those tests compare instead.
        if world.turn != 0 or world.grid.time_s != 0.0:
            raise ValueError("Simulation wraps a world at construction (tick 0), never one that has advanced")
        self._world, self._config = world, config
        self._applier = Applier(world)
        self._clock = Clock()

    @classmethod
    def from_scene(
        cls, scene: Scene, materials: MaterialTable, *, dx_m: float, config: SimConfig, limits: ActionLimits
    ) -> Simulation:
        """The scene voxelized at ``dx_m``, published as frame 0. Tick 0 is construction: it runs no physics."""
        return cls(World.from_scene(scene, materials, dx_m=dx_m, limits=limits), config=config)

    @property
    def tick(self) -> int:
        """The tick the next `step` runs."""
        return self._clock.tick

    @property
    def config(self) -> SimConfig:
        return self._config

    @property
    def frames(self) -> FrameView:
        return self._world.frames

    def step(self, records: Iterable[LogRecord]) -> TickReport:
        """Run one tick: apply its records in key order, then physics if it is a physics tick.

        The batch is read once and checked whole before any of it applies, so a bad batch raises ``ValueError`` and
        changes nothing, and a one-shot iterable loses no record."""
        tick, batch = self._clock.tick, tuple(records)
        self._check_batch(tick, batch)
        outcomes = tuple(self._applier.apply(r.target, r.params) for r in batch)
        physics = tick % self._config.physics_every == 0
        substeps = self._world.advance(self._config.physics_seconds) if physics else 0
        self._clock.advance()
        return TickReport(tick, outcomes, physics, substeps)

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
