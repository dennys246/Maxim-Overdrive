"""The simulation (step 5a, `docs/design/sim_core.md`): an integer clock that runs one tick per `step`.

This is step 5a's strangler wrap: `Simulation` drives `World`. A tick applies its records through the applier, in
the log's key order, then runs physics on physics ticks through `World.advance`, which runs the law tuple
(`simcore.core.physics`) as one fixed physics step (§8, PR 3: no substep floor, `substep_refine` in the config).
PR 4 moves the rest inside: the intent log with its per-tick digest.

Interim departures from sim_core.md, each named with the PR that ends it:
- the `Simulation(world, *, config)` seam beside `from_scene` (marked below; PR 4, when `Simulation` carries the
  per-tick digest the tests compare);
- frames are still published when a write window closes, so a tick with two records publishes two and a refusal-only
  tick publishes none, and frames carry no tick (§4's cadence, `tile_and_client.md` §4; PR 4, with the record path);
- the world's time is `grid.time_us`, whole microseconds `World.advance` moves by each physics step's interval, so
  between physics ticks it reads the last physics tick's time; frames, the snapshot and the SEM bridge read
  `time_s`, derived from it (§3: never a stored float). Time read from the tick itself comes with frames that carry
  their tick (PR 4);
- `World._power_field` holds the sources' deposit (sorted and cached, `simcore.core.deposit`), not heat's `prepare`
  (§6, §7; marked; PR 4), and no law has `bound_reads` or `prepare` yet (§5; PR 4);
- `source_exposure` (§3, `simcore.core.exposure`) is held here, beside the world rather than in its window, and isn't
  digested or saved yet: the per-tick digest (§9 member 3) and the save come with the log (PR 4);
- a physics step that raises leaves that tick's records applied and its exposure cleared (no one window over the tick
  yet; PR 4);
- a strike still calls the orchestrator from the applier rather than appending a `Load` for the tick (§5.1; marked in
  the applier; PR 4), and the log header doesn't yet record the law tuple (§5; PR 4, with the log).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from simcore.core.applier import Applier, Outcome
from simcore.core.checks import whole_number
from simcore.core.exposure import SourceExposure
from simcore.core.frames import FrameView
from simcore.core.intents import LogRecord
from simcore.core.law import Law
from simcore.core.limits import ActionLimits
from simcore.core.materials import MaterialTable
from simcore.core.physics import DEFAULT_LAWS, check_laws
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

    def __init__(self, world: World, *, config: SimConfig, laws: Sequence[Law] = DEFAULT_LAWS) -> None:
        # TEMPORARY(phase1/sim-clock): this seam wraps a World the caller built and still holds, so the strangler
        # tests can compare digest(world) against direct World calls; sim_core.md §4's one constructor is from_scene.
        # Step 5a's PR 4 removes it, when Simulation carries the per-tick digest those tests compare instead.
        if world.turn != 0 or world.grid.time_s != 0.0:
            raise ValueError("Simulation wraps a world at construction (tick 0), never one that has advanced")
        check_laws(laws)  # refused at construction, not at the first physics tick
        self._world, self._config, self._laws = world, config, tuple(laws)
        self._applier = Applier(world)
        self._clock = Clock()
        self._exposure = SourceExposure(world.sources, tick=self._clock.tick)  # construction's stand from tick 1

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
        ``laws`` is the law tuple (§5), the default in shipped play; the splitting bar runs it reversed (§11 bar 3)."""
        return cls(World.from_scene(scene, materials, dx_m=dx_m, limits=limits), config=config, laws=laws)

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
        self._exposure.end_tick(tick, self._world.sources)
        physics = tick % self._config.physics_every == 0
        substeps = self._physics(tick) if physics else 0
        self._clock.advance()
        return TickReport(tick, outcomes, physics, substeps)

    def _physics(self, tick: int) -> int:
        """The physics step ending at ``tick``: each source value delivers the ticks it stood (§3)."""
        config, exposure = self._config, self._exposure.step(tick)
        seconds, refine = config.physics_seconds, config.substep_refine
        return self._world.advance(seconds, refine=refine, exposure=exposure, laws=self._laws)

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
