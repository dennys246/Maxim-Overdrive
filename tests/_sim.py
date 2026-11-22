"""Driving a `Simulation` in tests: records, ticks, the bridge's port, and a look at the cell state behind it.

Everything reaches the world as a record through `Simulation.step` (sim_core.md §4). These helpers only build records
and step; they never apply anything themselves. `world_of` reads the simulation's private world, which only tests may
do (ruff's SLF001 refuses it in `src/` and `scripts/`).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence

from simcore.core.applier import Outcome
from simcore.core.intents import RECORD_KIND_OF, Action, LogRecord
from simcore.core.law import Law
from simcore.core.limits import ActionLimits
from simcore.core.materials import MaterialTable
from simcore.core.physics import DEFAULT_LAWS
from simcore.core.scene import Scene
from simcore.core.simulation import T3, SimConfig, Simulation, TickReport
from simcore.core.world import World


def make(
    scene: Scene,
    materials: MaterialTable,
    *,
    dx_m: float,
    limits: ActionLimits,
    config: SimConfig = T3,
    laws: Sequence[Law] = DEFAULT_LAWS,
) -> Simulation:
    return Simulation.from_scene(scene, materials, dx_m=dx_m, config=config, limits=limits, laws=laws)


def record(action: Action, target: str, *, tick: int, seq: int = 0, actor: int = 1, us: int = 0) -> LogRecord:
    return LogRecord(
        apply_tick=tick,
        apply_us=us,
        actor_id=actor,
        seq=seq,
        kind=RECORD_KIND_OF[type(action)],
        target=target,
        params=action,
    )


def act(sim: Simulation, target: str, action: Action, *, actor: int = 1) -> Outcome:
    """Apply one action as this tick's only record, and return its outcome. The tick runs physics if it is due."""
    (outcome,) = sim.step([record(action, target, tick=sim.tick, actor=actor)]).outcomes
    return outcome


def ticks(sim: Simulation, n: int) -> list[TickReport]:
    """Run ``n`` ticks with no records."""
    return [sim.step(()) for _ in range(n)]


def physics_steps(sim: Simulation, n: int) -> list[TickReport]:
    """Run until ``n`` more physics steps have run, with no records; returns the physics ticks' reports."""
    reports: list[TickReport] = []
    while len(reports) < n:
        report = sim.step(())
        if report.physics:
            reports.append(report)
    return reports


def seconds(sim: Simulation, s: float) -> list[TickReport]:
    """Run ``s`` world seconds (a whole number of ticks) with no records."""
    n, rest = divmod(round(s * 1_000_000), sim.config.tick_us)
    if rest:
        raise ValueError(f"{s} s is not a whole number of {sim.config.tick_us} us ticks")
    return ticks(sim, n)


def until(sim: Simulation, done: Callable[[Simulation], bool], *, limit_s: float) -> float | None:
    """Run physics steps until ``done(sim)`` holds after one; returns the world seconds that took, or None."""
    for _ in range(round(limit_s / sim.config.physics_seconds)):
        physics_steps(sim, 1)
        if done(sim):
            return sim.frames.latest.time_s
    return None


def world_of(sim: Simulation) -> World:
    """The cell state behind ``sim``: tests read it to digest state; nothing writes it outside `step`."""
    world: World = sim._world
    return world


class SteppingPort:
    """The bridge's submit-and-step port (sim_core.md §13), owned by the test: each ``submit`` is one record and one
    tick, so a bridge-driven run advances one tick per call that reaches stage 2 and can't be replayed. No outcome
    bar is measured through it."""

    def __init__(self, sim: Simulation, *, actor: int = 1) -> None:
        self._sim, self._actor, self._seq = sim, actor, 0

    @property
    def limits(self) -> ActionLimits:
        return self._sim.limits

    def submit(self, region: str, action: Action) -> Outcome:
        self._seq += 1
        rec = record(action, region, tick=self._sim.tick, seq=self._seq, actor=self._actor)
        (outcome,) = self._sim.step([rec]).outcomes
        return outcome


def steps(sim: Simulation, records_by_tick: dict[int, Iterable[LogRecord]], until_tick: int) -> list[TickReport]:
    """Run to ``until_tick`` inclusive, applying each tick's records."""
    return [sim.step(tuple(records_by_tick.get(sim.tick, ()))) for _ in range(until_tick - sim.tick + 1)]
