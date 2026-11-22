"""`source_exposure` against its closed form (sim_core.md §3): a source's energy in a physics step is the power of the
value standing at the end of each of the step's ticks, times ``tick_us``, summed over the ticks.

Measured on the shipped path, `Simulation.step`, as the heat the world gained: an insulated concrete slab under a fire
too small to degrade it, so conduction conserves heat (`tests/test_heat.py`) and the gain is the deposit.
"""

from __future__ import annotations

import pytest

from simcore.core import heat
from simcore.core.exposure import Share, SourceExposure
from simcore.core.intents import Extinguish, Ignite, LogRecord
from simcore.core.scene import Box, Scene
from simcore.core.simulation import T3, Simulation
from simcore.core.world import HeatSource, World
from tests.test_determinism import LIMITS, MATERIALS

SLAB = Scene((2.0, 2.0, 1.0), (Box((0.6, 0.6, 0.0), (1.4, 1.4, 0.6), "concrete", "slab"),))
P1, P2 = 1_000.0, 3_000.0
TICK_S = T3.tick_us / 1_000_000
REL = 1e-9  # heat's conservation holds to 1e-9 over an hour (tests/test_heat.py); this is half a second


def _fire(power_w: float, tick: int, seq: int) -> LogRecord:
    params = Ignite(power_w=power_w, radius_m=0.3)
    return LogRecord(apply_tick=tick, apply_us=0, actor_id=1, seq=seq, kind="ignite", target="slab", params=params)


def _douse(tick: int, seq: int) -> LogRecord:
    return LogRecord(apply_tick=tick, apply_us=0, actor_id=1, seq=seq, kind="douse", target="slab", params=Extinguish())


def _run(schedule: dict[int, list[LogRecord]], ticks: int, world: World | None = None) -> tuple[Simulation, float]:
    """Run ``ticks`` ticks of ``schedule``; returns the simulation and the heat its world gained, in joules."""
    world = world or World.from_scene(SLAB, MATERIALS, dx_m=0.2, limits=LIMITS)
    before = heat.heat_energy_j(world.grid, 20.0)
    sim = Simulation(world, config=T3)
    while sim.tick <= ticks:
        sim.step(schedule.get(sim.tick, []))
    return sim, heat.heat_energy_j(world.grid, 20.0) - before


@pytest.mark.parametrize("k", [1, 2, 3, 4, 5])
def test_a_source_on_for_k_ticks_delivers_k_ticks_of_its_power(k):
    # Lit at tick 6 - k, it stands at the end of ticks 6 - k to 5: k of the step's five.
    _, gained = _run({6 - k: [_fire(P1, 6 - k, 0)]}, 5)
    assert gained == pytest.approx(k * TICK_S * P1, rel=REL)


def test_an_ignite_at_tick_66_and_one_at_tick_69_differ_by_their_ticks():
    # The step ending at tick 70 covers ticks 66 to 70. Before source_exposure both delivered the whole step.
    _, early = _run({66: [_fire(P1, 66, 0)]}, 70)
    _, late = _run({69: [_fire(P1, 69, 0)]}, 70)
    assert early == pytest.approx(5 * TICK_S * P1, rel=REL)
    assert late == pytest.approx(2 * TICK_S * P1, rel=REL)


def test_a_fire_lit_and_doused_between_physics_ticks_delivers_the_ticks_it_stood():
    # Lit at 2, doused at 4: it stood at the end of ticks 2 and 3. Before source_exposure it delivered nothing.
    _, gained = _run({2: [_fire(P1, 2, 0)], 4: [_douse(4, 1)]}, 5)
    assert gained == pytest.approx(2 * TICK_S * P1, rel=REL)


def test_a_douse_then_a_re_ignite_at_a_new_power_each_tick_at_their_own_value():
    # P1 at the end of ticks 1 and 2, nothing at 3, P2 at 4 and 5; the doused value is the step's closed segment.
    schedule = {1: [_fire(P1, 1, 0)], 3: [_douse(3, 1)], 4: [_fire(P2, 4, 2)]}
    sim, _ = _run(schedule, 4)
    (segment,) = sim._exposure.closed
    assert (segment.key, segment.source.power_w, segment.ticks) == ("fire:slab", P1, 2)
    _, gained = _run(schedule, 5)
    assert gained == pytest.approx(TICK_S * (2 * P1 + 2 * P2), rel=REL)


def test_a_replacement_under_the_same_key_splits_the_step_between_the_values():
    # Re-ignited at P2 at tick 3 with no douse: P1 stood at the end of ticks 1 and 2, P2 at 3, 4 and 5.
    _, gained = _run({1: [_fire(P1, 1, 0)], 3: [_fire(P2, 3, 1)]}, 5)
    assert gained == pytest.approx(TICK_S * (2 * P1 + 3 * P2), rel=REL)


def test_the_physics_step_clears_the_closed_segments_and_a_value_replaced_at_a_steps_first_tick_has_none():
    # P1 stood the whole first step; replaced at tick 6, it stood at the end of none of the second step's ticks.
    schedule = {1: [_fire(P1, 1, 0)], 3: [_fire(P2, 3, 1)], 6: [_fire(P1, 6, 2)]}
    sim, _ = _run(schedule, 6)
    assert sim._exposure.closed == ()  # the first step's segment was cleared, and tick 6 closed none
    _, gained = _run(schedule, 10)
    assert gained == pytest.approx(TICK_S * (2 * P1 + 3 * P2 + 5 * P1), rel=REL)


def test_constructions_sources_stand_from_tick_1():
    world = World(SLAB.build(MATERIALS, dx_m=0.2), limits=LIMITS, sources={"fire:slab": _source(P1)})
    _, gained = _run({}, 5, world)
    assert gained == pytest.approx(5 * TICK_S * P1, rel=REL)


def _source(power_w: float) -> HeatSource:
    return HeatSource((1.0, 1.0, 0.3), 0.3, power_w)


def test_a_steps_shares_are_sorted_by_key_then_tick():
    # Unit level: two keys, one replaced twice, in the order they changed; the step lists a's values in tick order.
    exposure = SourceExposure({"b": _source(P1)}, tick=1)
    exposure.end_tick(1, {"b": _source(P1), "a": _source(P1)})
    exposure.end_tick(2, {"b": _source(P2), "a": _source(P2)})
    exposure.end_tick(3, {"b": _source(P2), "a": _source(P1)})
    step = exposure.step(3)
    assert step.of_ticks == 3
    assert step.shares == (
        Share("a", _source(P1), 1),
        Share("a", _source(P2), 1),
        Share("a", _source(P1), 1),
        Share("b", _source(P1), 1),
        Share("b", _source(P2), 2),
    )


def test_a_value_standing_on_delivers_each_step_only_that_steps_ticks():
    # Lit at tick 1, it stands through ticks 1 to 10: five ticks to each of two steps, not ten to the second.
    _, gained = _run({1: [_fire(P1, 1, 0)]}, 10)
    assert gained == pytest.approx(10 * TICK_S * P1, rel=REL)
