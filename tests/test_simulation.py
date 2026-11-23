"""The simulation (step 5a, sim_core.md §2-§4, §10): the integer clock, one tick per `step` in one write window,
records applied in key order with each one's loads resolved right after it, physics on physics ticks, one frame per
tick that applied a record or ran physics, and the work counters.

PR 4a's move of the window into `step` kept every cell's bits: the determinism scenario's digest of the cells, the
regions and the sources at the end matched PR 3's `World.advance` path on main, measured once and recorded in the
commit (the old path no longer exists to compare against in a test).
"""

from __future__ import annotations

import contextlib
import copy
from typing import cast

import numpy as np
import pytest

from simcore.core import heat, physics
from simcore.core.intents import KIND_RANK, Extinguish, Ignite, LogRecord, Strike
from simcore.core.law import STATELESS, LawInputs
from simcore.core.scene import Box, Scene
from simcore.core.simulation import T3, SimConfig, Simulation
from simcore.core.world import HeatSource, World
from tests._sim import physics_steps, ticks, world_of
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


def _sim(dx_m=0.2, config=T3, **kwargs):
    return Simulation.from_scene(SCENE, MATERIALS, dx_m=dx_m, config=config, limits=LIMITS, **kwargs)


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
    sim = _sim()
    assert sim.tick == 1  # the first step runs tick 1
    frame = sim.frames.latest
    assert (frame.sequence, frame.tick, frame.time_s) == (0, 0, 0.0)
    assert sim.config is T3


def test_physics_runs_on_every_physics_every_th_tick_and_never_before():
    sim = _sim(config=SimConfig(tick_us=100_000, physics_every=3))
    reports = ticks(sim, 7)
    assert [r.tick for r in reports] == [1, 2, 3, 4, 5, 6, 7]
    assert [r.physics for r in reports] == [False, False, True, False, False, True, False]
    assert all((r.substeps > 0) == r.physics for r in reports)
    assert (sim.frames.latest.tick, sim.frames.latest.time_s) == (6, 0.6)
    assert sim.tick == 8


def test_time_is_whole_microseconds_and_seconds_are_derived_never_summed():
    # sim_core.md §3: three ticks of 0.1 s are 300,000 us, read as 0.3 s; a float sum would read
    # 0.30000000000000004 (0.1 + 0.1 + 0.1), the drift that grows with every step of a long session.
    sim = _sim(config=SimConfig(tick_us=100_000, physics_every=1))
    ticks(sim, 3)
    assert 0.1 + 0.1 + 0.1 != 0.3  # a precondition: the float sum really drifts
    assert (sim.frames.latest.cells.time_us, sim.frames.latest.time_s) == (300_000, 0.3)


def test_cells_another_simulation_owns_are_refused_in_any_world_so_time_has_one_owner():
    # Delta 2 D2-S1: a second simulation over a stepped world published frame 0 at tick 0, and both stepped it. Delta 3
    # D3-S1: a new World over the same grid did it too, so the cells, not the World, carry the adoption.
    first = _sim()
    ticks(first, 3)
    world = world_of(first)
    for again in (world, World(world.grid, limits=world.limits, sources=world.sources)):
        with pytest.raises(ValueError, match="already have their simulation"):
            Simulation(again, config=T3)
    ticks(first, 2)  # the world's own simulation still owns it: its tick 5 runs physics and publishes
    assert (first.tick, first.frames.latest.tick) == (6, 5)


@pytest.mark.parametrize(
    ("laws", "sources", "match"),
    [
        ((*physics.DEFAULT_LAWS, physics.DEFAULT_LAWS[1]), {}, "names each law once"),  # refused building Physics
        (physics.DEFAULT_LAWS, {"fire:x": HeatSource((50.0, 50.0, 50.0), 0.3, 1e3)}, "outside the grid"),  # in warm
    ],
    ids=["law-tuple", "warm"],
)
def test_a_construction_that_raised_leaves_the_cells_free_for_a_retry(laws, sources, match):
    # Delta 3 D3-N1 and delta 4 D4-N1: adopting before every refusal had run left the cells owned by no simulation.
    grid = SCENE.build(MATERIALS, dx_m=0.2)
    with pytest.raises(ValueError, match=match):
        Simulation(World(grid, limits=LIMITS, sources=sources), config=T3, laws=laws)
    assert Simulation(World(grid, limits=LIMITS), config=T3).tick == 1


def test_cells_are_never_copied_so_no_two_simulations_share_their_versions():
    # Delta 4 D4-N3: a copy shared the versions and the gate, so a second simulation moved the first one's keys.
    grid = SCENE.build(MATERIALS, dx_m=0.2)
    for copier in (copy.copy, copy.deepcopy):
        with pytest.raises(TypeError, match="cells are not copied"):
            copier(grid)


def test_a_law_tuple_the_registry_disagrees_with_is_refused_at_construction():
    laws = (*physics.DEFAULT_LAWS, physics.DEFAULT_LAWS[1])
    with pytest.raises(ValueError, match="names each law once"):
        _sim(laws=laws)


# --- step's batch ---


def test_a_tick_applies_its_records_in_key_order_and_reports_each_outcome():
    report = _sim().step([_record(IGNITE, seq=0), _record(STRIKE, target="wall", seq=1)])
    assert [o.affordance for o in report.outcomes] == ["ignite", "strike"]
    assert all(o.success for o in report.outcomes)


def test_a_generator_batch_loses_no_record():
    sim = _sim()
    report = sim.step(r for r in [_record(IGNITE)])
    assert [o.affordance for o in report.outcomes] == ["ignite"]
    assert "fire:crate" in world_of(sim).sources


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
        ([_record(IGNITE), object()], "LogRecords"),  # a valid record before the bad one changes nothing either
    ],
)
def test_a_bad_batch_is_refused_whole_and_changes_nothing(records, match):
    sim = _sim()
    before = (digest(sim), sim.tick, sim.frames.latest.sequence)
    with pytest.raises(ValueError, match=match):
        sim.step(records)
    assert (digest(sim), sim.tick, sim.frames.latest.sequence) == before


# --- frames: one per tick that applied a record or ran physics (sim_core.md §4, tile_and_client.md §4) ---


def test_a_refusal_only_tick_publishes_one_frame_stamped_with_its_tick():
    sim = _sim()
    report = sim.step([_record(Ignite(power_w=10 * LIMITS.max_power_w, radius_m=0.3))])
    if report.outcomes[0].success:  # a precondition: the record must be refused, or the test tests nothing
        raise RuntimeError("the ignite was accepted: the test can't reach its bar")
    assert (sim.frames.latest.sequence, sim.frames.latest.tick) == (1, 1)
    assert report.work.frames_published == 1


def test_a_quiet_tick_publishes_nothing_and_opens_no_window():
    sim = _sim()
    report = sim.step([])
    assert not report.physics
    assert sim.frames.latest.sequence == 0
    assert (report.work.frames_published, report.work.windows_opened, report.work.cells_copied) == (0, 0, 0)


def test_a_tick_with_two_records_and_physics_publishes_one_frame():
    sim = _sim()
    ticks(sim, 4)
    report = sim.step([_record(IGNITE, tick=5, seq=0), _record(STRIKE, tick=5, target="wall", seq=1)])
    assert report.physics
    assert (sim.frames.latest.sequence, sim.frames.latest.tick, report.work.frames_published) == (1, 5, 1)
    assert report.work.windows_opened == 1  # the apply phase and physics share the tick's one window


def test_a_tick_of_fires_alone_copies_no_cell():
    report = _sim().step([_record(IGNITE)])
    assert (report.work.windows_opened, report.work.cells_copied, report.work.frames_published) == (0, 0, 1)


# --- one window per tick: a tick that raises changes nothing ---


class _Raises:
    """A per-substep law that raises on its first step: the tick's physics fails after its records applied."""

    name = "heat"  # registered as heat, so check_laws's registry check passes; it never gets heat's token
    version = 1
    cadence = physics.DEFAULT_LAWS[1].cadence
    reads = ("material", "temperature")
    writes = ("temperature",)
    bound_reads = ()

    def new_state(self, grid):
        return STATELESS

    def prepare(self, grid, state, exposure):
        return LawInputs()

    def stable_dt(self, grid, state):
        return float("inf")

    def step(self, grid, dt_s, inputs, state):
        raise RuntimeError("planted")


def test_a_tick_whose_physics_raises_leaves_no_half_applied_state():
    # sim_core.md §4 and the checklist's PR 4a row: records applied, then physics raising, roll back together, and
    # the clock, the frames and source_exposure don't move. A run after the failure matches one that never tried.
    laws = (physics.DEFAULT_LAWS[0], _Raises(), physics.DEFAULT_LAWS[2])
    sim = _sim(laws=laws)
    ticks(sim, 4)
    before = (digest(sim), sim.tick, sim.frames.latest.sequence)
    exposure = sim._exposure.closed, dict(sim._exposure._live)
    with pytest.raises(RuntimeError, match="planted"):
        sim.step([_record(IGNITE, tick=5), _record(STRIKE, tick=5, target="wall", seq=1)])
    assert (digest(sim), sim.tick, sim.frames.latest.sequence) == before
    assert (sim._exposure.closed, dict(sim._exposure._live)) == exposure
    assert "fire:crate" not in world_of(sim).sources


def test_a_rolled_back_tick_leaves_no_cache_a_later_state_reuses():
    # PR 3's S1, now for every law cache through Simulation: a strike on the crate at a physics tick whose heat raises
    # rolls back, restoring topology_version; a different strike (on the wall) then reaches the same version. The
    # run must equal one that only struck the wall, bit for bit and in its counted work: nothing the failed tick
    # built at that version is reused.
    def lit():
        sim = _sim()
        sim.step([_record(IGNITE)])
        ticks(sim, 3)
        return sim

    clean = lit()
    want = clean.step([_record(STRIKE, tick=5, target="wall")])
    failing = lit()
    with pytest.raises(RuntimeError, match="planted"), _raising_heat_once():
        failing.step([_record(STRIKE, tick=5, target="crate")])
    got = failing.step([_record(STRIKE, tick=5, target="wall")])
    assert world_of(failing).grid.topology_version == world_of(clean).grid.topology_version
    assert digest(failing) == digest(clean)
    assert got.work == want.work


# --- strikes resolve on their own tick (sim_core.md §5.1) ---


def test_a_strike_resolves_on_its_tick_its_crater_in_that_frame_its_effect_in_that_report():
    sim = _sim()
    solid_before = sim.frames.latest.cells.solid.sum()
    report = sim.step([_record(Strike(energy_j=LIMITS.max_energy_j, sigma_m=0.2, point_m=None))])
    (effect,) = report.outcomes[0].effects
    assert effect.destroyed_cells > 0
    assert sim.frames.latest.tick == 1
    assert solid_before - sim.frames.latest.cells.solid.sum() == effect.destroyed_cells


BLOCK = Scene((3.0, 3.0, 2.0), (Box((1.2, 1.2, 0), (1.6, 1.6, 0.4), "wood", "block"),))
BIG = Strike(energy_j=LIMITS.max_energy_j, sigma_m=LIMITS.max_sigma_m, point_m=None)


@pytest.mark.parametrize("dx_m", FAST_SPACINGS)
def test_a_strike_on_a_region_destroyed_earlier_in_the_tick_applies_and_destroys_nothing(dx_m):
    # sim_core.md §5.1 (owner, 2026-11-22): the next record's stage 2 sees the crater, but "gone" is authored geometry
    # only, never destruction, whose survivors depend on the grid spacing (PR 4a review, Exec S2: a cell rule flipped
    # between strike 29 at 0.2 m and 30 at 0.1 m). So the second strike is accepted at every spacing, with nothing
    # left to hit.
    sim = Simulation.from_scene(BLOCK, MATERIALS, dx_m=dx_m, config=T3, limits=LIMITS)
    first, second = sim.step([_record(BIG, target="block", seq=0), _record(BIG, target="block", seq=1)]).outcomes
    if not first.effects[0].destroyed_cells or sim.frames.latest.cells.solid.any():  # a precondition
        raise RuntimeError("the first strike left the block standing: the test can't reach its bar")
    assert second.success
    assert second.effects[0].destroyed_cells == 0


def test_topology_version_rises_once_per_strike_that_changes_the_world():
    sim = _sim()
    grid = world_of(sim).grid
    v0 = grid.topology_version
    tiny = Strike(energy_j=1.0, sigma_m=0.2, point_m=None)
    sim.step([_record(STRIKE, seq=0), _record(tiny, seq=1), _record(STRIKE, target="wall", seq=2)])
    assert grid.topology_version == v0 + 2


# --- records and physics in one tick ---


def test_a_record_on_a_physics_tick_applies_before_that_ticks_physics():
    # physics_every - 1 empty ticks, then a physics tick carrying the ignite: the step applies it, then runs physics,
    # where the fire stood at the end of one of the step's five ticks (sim_core.md §3), so it delivers a fifth of its
    # power over the step: bit for bit a fifth-power fire standing the whole step from tick 1.
    late = _sim()
    ticks(late, 4)
    assert late.step([_record(IGNITE, tick=5)]).physics
    early = _sim()
    early.step([_record(Ignite(power_w=FIRE_W / 5, radius_m=0.3), tick=1)])
    ticks(early, 4)
    assert FIRE_W * (1 / 5) == FIRE_W / 5  # a precondition: the two fractions are one float
    assert _temperatures(late) == _temperatures(early)
    whole = _sim()
    whole.step([_record(IGNITE, tick=1)])
    ticks(whole, 4)
    assert _temperatures(late) != _temperatures(whole)  # physics before apply would make late a whole-step fire


def _temperatures(sim):
    return world_of(sim).grid.temperature.tobytes()


def test_an_ignite_then_a_douse_in_one_tick_leaves_no_fire():
    # Applied in key order, the douse comes second; applied in reverse, the fire would survive.
    sim = _sim()
    sim.step([_record(IGNITE, us=0, seq=0), _record(DOUSE, us=1, seq=1)])
    assert world_of(sim).sources == {}


# --- the work counters (sim_core.md §10) ---


@pytest.mark.parametrize("n", [5, 23, 60])
def test_physics_steps_are_the_ticks_over_physics_every(n):
    sim = _sim()
    reports = ticks(sim, n)
    assert sum(r.work.physics_steps for r in reports) == n // T3.physics_every


def test_the_work_counters_hold_their_exact_values_and_repeat_on_a_rerun():
    def run():
        sim = _sim()
        lit = sim.step([_record(IGNITE)]).work
        return lit, [r.work for r in physics_steps(sim, 3)]

    lit, first = run()
    cells = 15 * 15 * 10  # the 3 x 3 x 2 m scene at 0.2 m
    # Construction builds every cache at rest and counts it in no tick (sim_core.md §2). The ignite's tick ends by
    # bringing the caches to its state: the new fire's overlap and weights, nothing else (no topology change).
    assert (lit.physics_steps, lit.stable_dt_evaluations, lit.rebuilds) == (0, 0, (("heat/deposit", 2),))
    assert (lit.windows_opened, lit.cells_copied, lit.frames_published) == (0, 0, 1)
    step = first[0]
    assert step.physics_steps == 1
    assert step.substeps == (("damage.thermal", 1), ("heat", 1))
    assert step.cell_substeps == (("damage.thermal", cells), ("heat", cells))
    # Every copy the window made, counted where it is made (PR 4a review, Performance S3): the four fields at open and
    # again at commit, read-only views of material and temperature for the laws that read them without writing, and
    # heat's temperature revoked when its block ends. Eleven fields' worth, not the four a formula assumed.
    assert (step.windows_opened, step.cells_copied, step.frames_published) == (1, (4 + 2 + 1 + 4) * cells, 1)
    assert step.power_field_builds == 1
    # Every cache was ready: the physics steps rebuild nothing and evaluate no bound while the topology stands.
    assert all((w.stable_dt_evaluations, w.rebuilds) == (0, ()) for w in first)
    assert run() == (lit, first)


@pytest.mark.parametrize("records", [[_record(STRIKE, tick=10)], []], ids=["a strike", "quiet"])
def test_a_retried_tick_counts_the_same_work_as_one_that_never_failed(records):
    # PR 4a review, Determinism SF-1: a tick that raises rolls back, and its caches no longer match the restored state
    # (their keys moved with the rolled-back window); they are rebuilt at rest for it, so the retry counts what an
    # uninterrupted run counts at that tick. The same eager build lets PR 4b's replay from a loaded state count the
    # live run's work (sim_core.md §2, §10). The quiet physics tick is the case that needs the rebuild: a strike's
    # retry rebuilds the same caches in both runs (delta 1, D-S1). Proven by deleting the rebuild after a raise.
    def to_tick(sim, last):
        sim.step([_record(IGNITE)])
        ticks(sim, last + 1 - sim.tick)

    clean = _sim()
    to_tick(clean, 9)
    want = clean.step(records).work
    failing = _sim()
    to_tick(failing, 9)
    with pytest.raises(RuntimeError, match="planted"), _raising_heat_once():
        failing.step(records)
    assert failing.step(records).work == want
    assert digest(failing) == digest(clean)


def test_a_publication_that_raises_leaves_the_tick_counted_so_no_retry_applies_it_twice(monkeypatch):
    # PR 4a review, Determinism N-5: the window commits, then the clock moves, then the frame is published. If
    # publication raised before the clock moved, a caller retrying the tick would apply its records twice. Proven by
    # advancing the clock after publication: the next tick's record is refused as the wrong tick.
    sim = _sim()
    real = sim._feed.publish

    def fails_once(frame):
        monkeypatch.setattr(sim._feed, "publish", real)
        raise MemoryError("planted")

    monkeypatch.setattr(sim._feed, "publish", fails_once)
    with pytest.raises(MemoryError, match="planted"):
        sim.step([_record(IGNITE, tick=1)])
    assert sim.tick == 2
    assert "fire:crate" in world_of(sim).sources
    with pytest.raises(ValueError, match="for tick 1 reached tick 2"):
        sim.step([_record(IGNITE, tick=1, seq=1)])
    assert sim.step([_record(DOUSE, tick=2)]).outcomes[0].success


@contextlib.contextmanager
def _raising_heat_once():
    real = heat.HeatLaw.step

    def raising(self, grid, dt_s, inputs, state):
        raise RuntimeError("planted")

    heat.HeatLaw.step = raising  # type: ignore[method-assign]
    try:
        yield
    finally:
        heat.HeatLaw.step = real  # type: ignore[method-assign]


def test_a_record_and_a_config_store_plain_ints_so_the_key_serialises():
    # Wire delta: numpy integers passed validation unchanged, and json.dumps refuses them (PR 4b's log needs it).
    import json  # noqa: PLC0415 - only this test needs it

    record = _record(IGNITE, tick=np.int64(1), us=np.int64(0), actor=np.int64(7), seq=np.int64(0))
    assert all(type(v) is int for v in (record.apply_tick, record.apply_us, record.actor_id, record.seq))
    json.dumps(record.key)
    # cast: the test hands SimConfig the numpy integers its int annotations exclude, as a caller could.
    config = SimConfig(tick_us=cast(int, np.int64(100_000)), physics_every=cast(int, np.int64(5)))
    assert type(config.tick_us) is int
    assert type(config.physics_every) is int
