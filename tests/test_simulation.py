"""The simulation shell (step 5a PR 1, sim_core.md §2-§4): the integer clock, one tick per `step`, records applied in
key order through today's applier, and physics on physics ticks through today's `World.advance`.

The wrap changes nothing: a run through `Simulation.step` and the same calls made on a `World` directly give
bit-identical state (tests/test_determinism.py's digest). That comparison stays until step 5a's PR 3 drops the substep
floor, a deliberate break (sim_core.md §12).
"""

from __future__ import annotations

import numpy as np
import pytest

from simcore.core.applier import Applier
from simcore.core.intents import Extinguish, Ignite, Strike
from simcore.core.simulation import T3, WORLD_ACTION_RANK, LogRecord, SimConfig, Simulation
from simcore.core.world import World
from tests.conftest import FAST_SPACINGS
from tests.test_determinism import FIRE_W, LIMITS, MATERIALS, SCENE, digest

IGNITE = Ignite(power_w=FIRE_W, radius_m=0.3)
STRIKE = Strike(energy_j=2.0e7, sigma_m=0.2, point_m=None)


def _record(action, *, tick=1, target="crate", us=0, actor="host", seq=0):
    return LogRecord(apply_tick=tick, apply_us=us, actor_id=actor, seq=seq, target=target, action=action)


def _sim(world=None, config=T3):
    return Simulation(world or World.from_scene(SCENE, MATERIALS, dx_m=0.2, limits=LIMITS), config=config)


# --- SimConfig ---


def test_t3_is_a_tenth_of_a_second_tick_and_physics_every_half_second():
    assert (T3.tick_us, T3.physics_every, T3.physics_seconds) == (100_000, 5, 0.5)


@pytest.mark.parametrize(
    ("field", "value"), [("tick_us", 0), ("tick_us", 1.5), ("physics_every", True), ("physics_every", -1)]
)
def test_a_config_refuses_anything_but_positive_whole_numbers(field, value):
    with pytest.raises(ValueError, match=field):
        SimConfig(**{field: value})


# --- LogRecord ---


def test_a_record_ranks_every_v0_world_action_together_and_orders_by_the_logs_key():
    for action, kind in ((IGNITE, "ignite"), (STRIKE, "strike"), (Extinguish(), "extinguish")):
        r = _record(action, tick=3, us=7, actor="npc", seq=2)
        assert (r.kind, r.kind_rank, r.key) == (kind, WORLD_ACTION_RANK, (3, WORLD_ACTION_RANK, 7, "npc", 2))


@pytest.mark.parametrize(
    ("changes", "match"),
    [
        ({"tick": 0}, "apply_tick"),
        ({"tick": True}, "apply_tick"),
        ({"us": -1}, "apply_us"),
        ({"seq": 1.0}, "seq"),
        ({"actor": ""}, "actor_id"),
        ({"target": 3}, "target"),
    ],
)
def test_a_record_refuses_a_malformed_field(changes, match):
    with pytest.raises(ValueError, match=match):
        _record(IGNITE, **changes)


def test_a_record_refuses_anything_but_a_typed_action():
    with pytest.raises(ValueError, match="typed action"):
        _record({"power_w": 1.0})


# --- the clock and construction ---


def test_tick_0_is_construction_it_publishes_frame_0_and_runs_no_physics():
    world = World.from_scene(SCENE, MATERIALS, dx_m=0.2, limits=LIMITS)
    sim = _sim(world)
    assert sim.tick == 1  # the first step runs tick 1
    assert sim.frames.latest.sequence == 0
    assert (world.grid.time_s, world.turn) == (0.0, 0)


def test_from_scene_builds_the_same_world_as_world_from_scene():
    sim = Simulation.from_scene(SCENE, MATERIALS, dx_m=0.2, config=T3, limits=LIMITS)
    direct = World.from_scene(SCENE, MATERIALS, dx_m=0.2, limits=LIMITS)
    assert np.array_equal(sim.frames.latest.cells.material, direct.frames.latest.cells.material)
    assert sim.config is T3
    assert sim.frames.latest.sequence == 0


def test_physics_runs_on_every_physics_every_th_tick_and_never_before():
    world = World.from_scene(SCENE, MATERIALS, dx_m=0.2, limits=LIMITS)
    sim = _sim(world, SimConfig(tick_us=100_000, physics_every=3))
    reports = [sim.step([]) for _ in range(7)]
    assert [r.tick for r in reports] == [1, 2, 3, 4, 5, 6, 7]
    assert [r.physics for r in reports] == [False, False, True, False, False, True, False]
    assert all((r.substeps > 0) == r.physics for r in reports)
    assert world.grid.time_s == pytest.approx(2 * 0.3)
    assert sim.tick == 8


# --- step's batch ---


def test_a_tick_applies_its_records_in_key_order_and_reports_each_outcome():
    sim = _sim()
    report = sim.step([_record(IGNITE, seq=0), _record(STRIKE, target="wall", seq=1)])
    assert [o.affordance for o in report.outcomes] == ["ignite", "strike"]
    assert all(o.success for o in report.outcomes)


def test_a_refused_action_is_an_outcome_not_an_error():
    report = _sim().step([_record(Ignite(power_w=10 * LIMITS.max_power_w, radius_m=0.3))])
    assert not report.outcomes[0].success
    assert report.outcomes[0].code is not None


@pytest.mark.parametrize(
    ("records", "match"),
    [
        ([_record(IGNITE, tick=2)], "for tick 2 reached tick 1"),
        ([_record(IGNITE, seq=1), _record(STRIKE, target="wall", seq=0)], "increasing key order"),
        ([_record(IGNITE, seq=0), _record(STRIKE, target="wall", seq=0)], "increasing key order"),
        ([object()], "LogRecords"),
    ],
)
def test_a_bad_batch_is_refused_whole_and_changes_nothing(records, match):
    world = World.from_scene(SCENE, MATERIALS, dx_m=0.2, limits=LIMITS)
    sim = _sim(world)
    before = (digest(world), sim.tick, sim.frames.latest.sequence)
    with pytest.raises(ValueError, match=match):
        sim.step([_record(IGNITE), *records] if match == "for tick 2 reached tick 1" else records)
    assert (digest(world), sim.tick, sim.frames.latest.sequence) == before


# --- the wrap changes nothing ---


def _through_simulation(dx_m, physics_steps):
    world = World.from_scene(SCENE, MATERIALS, dx_m=dx_m, limits=LIMITS)
    sim = _sim(world)
    sim.step([_record(IGNITE, seq=0), _record(STRIKE, target="wall", seq=1)])
    while sim.tick <= physics_steps * T3.physics_every:
        sim.step([])
    return world


def _directly(dx_m, physics_steps):
    world = World.from_scene(SCENE, MATERIALS, dx_m=dx_m, limits=LIMITS)
    applier = Applier(world)
    assert applier.apply("crate", IGNITE).success
    assert applier.apply("wall", STRIKE).success
    for _ in range(physics_steps):
        world.advance(T3.physics_seconds)
    return world


@pytest.mark.parametrize("dx_m", FAST_SPACINGS)
def test_a_run_through_simulation_is_bit_identical_to_the_same_calls_on_world(dx_m):
    wrapped, direct = _through_simulation(dx_m, 12), _directly(dx_m, 12)
    assert digest(wrapped) == digest(direct)


def test_a_burning_run_through_simulation_is_bit_identical_to_the_same_calls_on_world():
    # Long enough that the fire degrades and destroys crate cells, so destruction mid-step is on the compared path.
    wrapped, direct = _through_simulation(0.2, 120), _directly(0.2, 120)
    assert (wrapped.grid.material != wrapped.grid.original_material).any()
    assert digest(wrapped) == digest(direct)
