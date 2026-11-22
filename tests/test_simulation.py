"""The simulation shell (step 5a PR 1, sim_core.md §2-§4): the integer clock, one tick per `step`, records applied in
key order through today's applier, and physics on physics ticks through today's `World.advance`.

The wrap changes nothing: a run through `Simulation.step` and the same calls made on a `World` directly give
bit-identical state (tests/test_determinism.py's digest). That comparison stays until step 5a's PR 3 drops the substep
floor, a deliberate break (sim_core.md §11). The direct path uses a literal 0.5 s, so a wrong derived interval in the
shell can't cancel out.
"""

from __future__ import annotations

from typing import cast

import numpy as np
import pytest

from simcore.core.applier import Applier
from simcore.core.intents import KIND_RANK, Extinguish, Ignite, LogRecord, Strike
from simcore.core.simulation import T3, SimConfig, Simulation
from simcore.core.world import World
from tests.conftest import FAST_SPACINGS
from tests.test_determinism import FIRE_W, LIMITS, MATERIALS, SCENE, digest

IGNITE = Ignite(power_w=FIRE_W, radius_m=0.3)
STRIKE = Strike(energy_j=2.0e7, sigma_m=0.2, point_m=None)
DOUSE = Extinguish()
KIND = {Ignite: "ignite", Strike: "strike", Extinguish: "douse"}
STEP_S = 0.5  # T3's physics step, written out so the direct path doesn't share the shell's derivation


def _record(params, *, tick=1, target="crate", us=0, actor=1, seq=0, kind=None):
    kind = KIND[type(params)] if kind is None else kind
    return LogRecord(apply_tick=tick, apply_us=us, actor_id=actor, seq=seq, kind=kind, target=target, params=params)


def _world(dx_m=0.2):
    return World.from_scene(SCENE, MATERIALS, dx_m=dx_m, limits=LIMITS)


def _sim(world=None, config=T3):
    return Simulation(world or _world(), config=config)


# --- SimConfig ---


def test_t3_is_a_tenth_of_a_second_tick_and_physics_every_half_second():
    assert (T3.tick_us, T3.physics_every, T3.physics_seconds) == (100_000, 5, STEP_S)


@pytest.mark.parametrize(
    ("field", "value"), [("tick_us", 0), ("tick_us", 1.5), ("physics_every", True), ("physics_every", -1)]
)
def test_a_config_refuses_anything_but_positive_whole_numbers(field, value):
    with pytest.raises(ValueError, match=field):
        SimConfig(**{field: value})


# --- LogRecord ---


def test_a_record_ranks_each_v0_world_action_from_the_closed_table_and_orders_by_the_logs_key():
    for params in (IGNITE, STRIKE, DOUSE):
        r = _record(params, tick=3, us=7, actor=9, seq=2)
        assert r.kind_rank == KIND_RANK[r.kind] == 30
        assert r.key == (3, 30, 7, 9, 2)


def test_a_records_rank_is_read_from_the_table_not_assumed(monkeypatch):
    # Every v0 kind ranks 30 today, so a constant would pass the test above; the rank must follow the table.
    from simcore.core import intents  # noqa: PLC0415 - patched in place for this test only

    monkeypatch.setattr(intents, "KIND_RANK", {**intents.KIND_RANK, "strike": 31})
    assert (_record(IGNITE).kind_rank, _record(STRIKE).kind_rank) == (30, 31)


def test_actor_ids_order_as_integers_not_as_text():
    # "10" < "9" as text; boundaries §6.2's keys are integers (D-N2).
    assert _record(IGNITE, actor=9).key < _record(IGNITE, actor=10).key


@pytest.mark.parametrize(
    ("changes", "match"),
    [
        ({"tick": 0}, "apply_tick"),
        ({"tick": True}, "apply_tick"),
        ({"us": -1}, "apply_us"),
        ({"us": 2**63}, "apply_us"),
        ({"seq": 1.0}, "seq"),
        ({"seq": 2**32}, "seq"),
        ({"actor": -1}, "actor_id"),
        ({"actor": 2**32}, "actor_id"),
        ({"actor": "npc"}, "actor_id"),
        ({"target": "a:b"}, "target"),
        ({"target": 3}, "target"),
        ({"kind": "pause"}, "unknown record kind"),
        ({"kind": 7}, "unknown record kind"),
        ({"kind": "strike"}, "params must be its typed action"),
    ],
)
def test_a_record_refuses_a_malformed_field(changes, match):
    with pytest.raises(ValueError, match=match):
        _record(IGNITE, **changes)


def test_a_record_refuses_anything_but_a_typed_action():
    with pytest.raises(ValueError, match="typed action"):
        _record({"power_w": 1.0}, kind="ignite")


# --- the clock and construction ---


def test_tick_0_is_construction_it_publishes_frame_0_and_runs_no_physics():
    world = _world()
    sim = _sim(world)
    assert sim.tick == 1  # the first step runs tick 1
    assert sim.frames.latest.sequence == 0
    assert (world.grid.time_s, world.turn) == (0.0, 0)


def test_the_seam_refuses_a_world_that_has_already_advanced():
    world = _world()
    world.advance(STEP_S)
    with pytest.raises(ValueError, match="never one that has advanced"):
        _sim(world)


def test_from_scene_builds_the_same_world_as_world_from_scene():
    sim = Simulation.from_scene(SCENE, MATERIALS, dx_m=0.2, config=T3, limits=LIMITS)
    direct = _world()
    assert np.array_equal(sim.frames.latest.cells.temperature, direct.frames.latest.cells.temperature)
    assert np.array_equal(sim.frames.latest.cells.material, direct.frames.latest.cells.material)
    assert sim.config is T3
    assert sim.frames.latest.sequence == 0


def test_physics_runs_on_every_physics_every_th_tick_and_never_before():
    world = _world()
    sim = _sim(world, SimConfig(tick_us=100_000, physics_every=3))
    reports = [sim.step([]) for _ in range(7)]
    assert [r.tick for r in reports] == [1, 2, 3, 4, 5, 6, 7]
    assert [r.physics for r in reports] == [False, False, True, False, False, True, False]
    assert all((r.substeps > 0) == r.physics for r in reports)
    assert world.grid.time_s == pytest.approx(2 * 0.3)
    assert sim.tick == 8


# --- step's batch ---


def test_a_tick_applies_its_records_in_key_order_and_reports_each_outcome():
    report = _sim().step([_record(IGNITE, seq=0), _record(STRIKE, target="wall", seq=1)])
    assert [o.affordance for o in report.outcomes] == ["ignite", "strike"]
    assert all(o.success for o in report.outcomes)


def test_a_generator_batch_loses_no_record():
    world = _world()
    report = _sim(world).step(r for r in [_record(IGNITE)])
    assert [o.affordance for o in report.outcomes] == ["ignite"]
    assert "fire:crate" in world.sources


def test_a_refused_action_is_an_outcome_not_an_error():
    report = _sim().step([_record(Ignite(power_w=10 * LIMITS.max_power_w, radius_m=0.3))])
    assert not report.outcomes[0].success
    assert report.outcomes[0].code is not None


@pytest.mark.parametrize(
    ("records", "match"),
    [
        ([_record(IGNITE), _record(IGNITE, tick=2, seq=1)], "for tick 2 reached tick 1"),
        ([_record(IGNITE, seq=1), _record(STRIKE, target="wall", seq=0)], "increasing key order"),
        ([_record(IGNITE, us=0), _record(STRIKE, target="wall", us=1)], r"repeats an \(actor_id, seq\)"),
        ([_record(IGNITE, us=T3.tick_us)], "not within a 100000 us tick"),
        ([object()], "LogRecords"),
    ],
)
def test_a_bad_batch_is_refused_whole_and_changes_nothing(records, match):
    world = _world()
    sim = _sim(world)
    before = (digest(world), sim.tick, sim.frames.latest.sequence)
    with pytest.raises(ValueError, match=match):
        sim.step(records)
    assert (digest(world), sim.tick, sim.frames.latest.sequence) == before


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Interim departure, named in simulation.py: frames still publish when a write window closes, carry no tick, "
    "and a refusal-only tick publishes none. sim_core.md §4 (cadence: tile_and_client.md §4) publishes one frame per "
    "tick, stamped with it; step 5a's PR 4 moves publication onto the record path, and this gate then flips.",
)
def test_a_refusal_only_tick_publishes_one_frame_stamped_with_its_tick():
    sim = _sim()
    report = sim.step([_record(Ignite(power_w=10 * LIMITS.max_power_w, radius_m=0.3))])
    if report.outcomes[0].success:  # a precondition: the record must be refused, or the gate tests nothing
        raise RuntimeError("the ignite was accepted: the gate can't reach its bar")
    assert sim.frames.latest.sequence == 1
    assert getattr(sim.frames.latest, "tick", None) == 1


# --- the wrap changes nothing ---

# Records by tick, on and off physics ticks (5 and 30 are physics ticks at T3): an ignite at tick 1, a strike on the
# crate at a physics tick, and a douse then a re-ignite in one physics tick. Physics before apply, records dropped on
# a physics tick, or records applied in reverse each change the digest (the review's plants).
SCHEDULE = {
    1: [_record(IGNITE, tick=1)],
    5: [_record(STRIKE, tick=5, seq=1)],
    30: [_record(DOUSE, tick=30, seq=2), _record(IGNITE, tick=30, us=1, seq=3)],
}


def _through_simulation(dx_m, ticks, schedule):
    world = _world(dx_m)
    sim = _sim(world)
    while sim.tick <= ticks:
        sim.step(schedule.get(sim.tick, []))
    return world


def _directly(dx_m, ticks, schedule):
    world = _world(dx_m)
    applier = Applier(world)
    for t in range(1, ticks + 1):
        for r in schedule.get(t, []):
            applier.apply(r.target, r.params)
        if t % 5 == 0:
            world.advance(STEP_S)
    return world


@pytest.mark.parametrize("dx_m", FAST_SPACINGS)
def test_a_run_through_simulation_is_bit_identical_to_the_same_calls_on_world(dx_m):
    wrapped, direct = _through_simulation(dx_m, 60, SCHEDULE), _directly(dx_m, 60, SCHEDULE)
    assert digest(wrapped) == digest(direct)
    assert wrapped.frames.latest.sequence == direct.frames.latest.sequence


def test_a_record_on_a_physics_tick_applies_before_that_ticks_physics():
    # physics_every - 1 empty ticks, then a physics tick carrying the ignite: the step must apply it, then run physics.
    schedule = {5: [_record(IGNITE, tick=5)]}
    sim_world = _world()
    sim = _sim(sim_world)
    reports = [sim.step(schedule.get(sim.tick, [])) for _ in range(5)]
    assert reports[-1].physics
    assert digest(sim_world) == digest(_directly(0.2, 5, schedule))


def test_an_ignite_then_a_douse_in_one_tick_leaves_no_fire():
    # Applied in key order, the douse comes second; applied in reverse, the fire would survive.
    world = _world()
    _sim(world).step([_record(IGNITE, us=0, seq=0), _record(DOUSE, us=1, seq=1)])
    assert world.sources == {}


def test_a_burning_run_through_simulation_is_bit_identical_to_the_same_calls_on_world():
    # Long enough that the fire degrades and destroys crate cells, so destruction mid-step is on the compared path.
    schedule = {1: [_record(IGNITE, tick=1), _record(STRIKE, tick=1, target="wall", seq=1)]}
    wrapped, direct = _through_simulation(0.2, 600, schedule), _directly(0.2, 600, schedule)
    assert (wrapped.grid.material != wrapped.grid.original_material).any()
    assert digest(wrapped) == digest(direct)


def test_a_record_and_a_config_store_plain_ints_so_the_key_serialises():
    # Wire delta: numpy integers passed validation unchanged, and json.dumps refuses them (PR 4's log needs it).
    import json  # noqa: PLC0415 - only this test needs it

    import numpy as np  # noqa: PLC0415

    record = _record(IGNITE, tick=np.int64(1), us=np.int64(0), actor=np.int64(7), seq=np.int64(0))
    assert all(type(v) is int for v in (record.apply_tick, record.apply_us, record.actor_id, record.seq))
    json.dumps(record.key)
    # cast: the test hands SimConfig the numpy integers its int annotations exclude, as a caller could.
    config = SimConfig(tick_us=cast(int, np.int64(100_000)), physics_every=cast(int, np.int64(5)))
    assert type(config.tick_us) is int
    assert type(config.physics_every) is int
