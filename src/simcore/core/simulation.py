"""The simulation (step 5a, `docs/design/sim_core.md`): an integer clock that runs one tick per `step`.

This is step 5a's first PR, the strangler wrap: `Simulation` drives today's `World` unchanged. A tick applies its
records through today's applier, in the log's key order, then runs physics on physics ticks through `World.advance`,
so heat, damage, the substep floor and the frame cadence are exactly as before. PRs 2-4 move those pieces inside:
the law list and registry, the fixed physics step, and the intent log with its per-tick digest.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from simcore.core.applier import Applier, Outcome
from simcore.core.frames import FrameView
from simcore.core.intents import AFFORDANCE_OF, Action
from simcore.core.limits import ActionLimits
from simcore.core.materials import MaterialTable
from simcore.core.scene import Scene
from simcore.core.world import World

# kind_rank for 5a's v0 log vocabulary (sim_core.md §14; boundaries.md §6.2 owns the table): every v0 world action
# (ignite, strike and its douse, spelled `extinguish` in today's intents) ranks 30.
WORLD_ACTION_RANK = 30


def _whole(value: object, name: str, *, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be a whole number of at least {minimum}, got {value!r}")
    return value


@dataclass(frozen=True)
class SimConfig:
    """The truth constants (tile_and_client.md §6.1, T3): a tick's length in world microseconds, and how many ticks
    one physics step covers. Integers, so nothing stores time as a float (sim_core.md §3)."""

    tick_us: int = 100_000
    physics_every: int = 5

    def __post_init__(self) -> None:
        _whole(self.tick_us, "tick_us", minimum=1)
        _whole(self.physics_every, "physics_every", minimum=1)

    @property
    def physics_seconds(self) -> float:
        """One physics step's length, derived for the laws' float arithmetic where it is needed, never stored."""
        return self.physics_every * self.tick_us / 1_000_000


T3 = SimConfig()


@dataclass(frozen=True)
class LogRecord:
    """One input record, carrying what `step` needs in 5a's first PR (boundaries.md §6.2's fields and key).

    The log's full record (schema_version, observed and issued ticks, typed params, the audit payload) and its file
    format are step 5a's PR 4; this is the subset `step` applies today: the typed action and the region it targets."""

    apply_tick: int
    apply_us: int
    actor_id: str
    seq: int
    target: str
    action: Action

    def __post_init__(self) -> None:
        _whole(self.apply_tick, "apply_tick", minimum=1)
        _whole(self.apply_us, "apply_us", minimum=0)
        _whole(self.seq, "seq", minimum=0)
        for name, value in (("actor_id", self.actor_id), ("target", self.target)):
            if not isinstance(value, str) or not value:
                raise ValueError(f"{name} must be a non-empty string, got {value!r}")
        if type(self.action) not in AFFORDANCE_OF:
            raise ValueError(f"action must be a typed action, got {type(self.action).__name__}")

    @property
    def kind(self) -> str:
        return AFFORDANCE_OF[type(self.action)]

    @property
    def kind_rank(self) -> int:
        return WORLD_ACTION_RANK

    @property
    def key(self) -> tuple[int, int, int, str, int]:
        """The log's one ordering key (boundaries.md §6.2)."""
        return (self.apply_tick, self.kind_rank, self.apply_us, self.actor_id, self.seq)


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
        """The strangler seam: wrap a world that construction already published as frame 0. Construction moves
        into `from_scene`, through the topology owner, in step 5a's PR 2 (sim_core.md §2)."""
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

    def step(self, records: Sequence[LogRecord]) -> TickReport:
        """Run one tick: apply its records in key order, then physics if it is a physics tick.

        The whole batch is checked before any of it applies, so a bad batch raises ``ValueError`` and changes
        nothing."""
        tick = self._clock.tick
        self._check_batch(tick, records)
        outcomes = tuple(self._applier.apply(r.target, r.action) for r in records)
        physics = tick % self._config.physics_every == 0
        substeps = self._world.advance(self._config.physics_seconds) if physics else 0
        self._clock.advance()
        return TickReport(tick, outcomes, physics, substeps)

    @staticmethod
    def _check_batch(tick: int, records: Sequence[LogRecord]) -> None:
        for r in records:
            if not isinstance(r, LogRecord):
                raise ValueError(f"step takes LogRecords, got {type(r).__name__}")
            if r.apply_tick != tick:
                raise ValueError(f"a record for tick {r.apply_tick} reached tick {tick}")
        keys = [r.key for r in records]
        if any(keys[i + 1] <= keys[i] for i in range(len(keys) - 1)):
            raise ValueError("records must be in strictly increasing key order (boundaries.md §6.2)")
