"""The verification rule on the shipped path: a fire on a crate, and on a concrete wall, at every grid.

The truth grid (0.1 m) agrees with the reference (0.05 m, under MAXIM_OVERDRIVE_ALL_TIERS=1) and converges from the
coarse grid (0.2 m) (world_model §1.1), measured through ``simcore.verify`` (docs/design/verify_harness.md).

Since step 5a's PR 4a these scenarios run through ``Simulation.step`` at T3's fixed 0.5 s physics step (sim_core.md
§8, §11 bar 2), with their actions as records; the 6 s turn is gone, so each time is world seconds, restated from the
turns it was measured in (a turn was 6 s). On shipped data each physics step is one substep at every spacing, so the
scenarios refine space alone; bar 2b below holds them time-converged at the shipped refine. Heat's own studies
(tests/test_heat.py) refine space and time apart.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pytest

from maxim_overdrive import data
from simcore.adapters.sem.bridge import region_parts
from simcore.core import physics
from simcore.core.grid import MaterialGrid
from simcore.core.intents import Ignite
from simcore.core.law import STATELESS, Cadence, Changes, LawInputs
from simcore.core.scene import Box, Scene
from simcore.core.simulation import SimConfig
from simcore.verify import Run, agrees, same_class_under_refinement
from tests._sim import SteppingPort, make, physics_steps, record, world_of
from tests.conftest import FAST_SPACINGS, TIERED_FAST_SPACINGS, TIERED_SPACINGS

LIMITS = data.action_limits()
STEP_S = 0.5  # T3's physics step (SimConfig.physics_seconds), written out for the restated times


SCENE = Scene(
    (3.0, 3.0, 2.0),
    (Box((1.2, 1.2, 0), (1.8, 1.8, 0.6), "wood", "crate"), Box((0, 0, 0), (0.6, 3.0, 2.0), "concrete", "wall")),
)


def _lit(dx_m, materials, targets, power_w, *, refine=1, laws=physics.DEFAULT_LAWS):
    """A simulation with a fire of ``power_w`` lit on each target at tick 1, as records."""
    sim = make(SCENE, materials, dx_m=dx_m, limits=LIMITS, config=SimConfig(substep_refine=refine), laws=laws)
    ignite = Ignite(power_w=power_w, radius_m=0.3)
    report = sim.step([record(ignite, target, tick=1, seq=n) for n, target in enumerate(targets)])
    if not all(o.success for o in report.outcomes):  # preconditions raise RuntimeError, never a gate's AssertionError
        raise RuntimeError("ignite refused: the test can't reach its bar")
    return sim


def _integrity(sim, region):
    return region_parts(SteppingPort(sim), sim.frames, region)[0]["integrity"].value()  # reads the frame only


def _burn(dx_m, materials, seconds=900.0, power_w=60_000.0, *, refine=1, laws=physics.DEFAULT_LAWS, levels=()):
    """Fires on the crate and the wall: when the crate first reads under 0.9 (its onset), the crate's and the wall's
    integrity at ``seconds``, and when the crate first reads under each of ``levels`` (searched to 1800 s, the 300
    turns the burn-time scenarios ran). Times are world seconds at the physics step's end, or None."""
    sim = _lit(dx_m, materials, ("crate", "wall"), power_w, refine=refine, laws=laws)
    onset, below, at = None, dict.fromkeys(levels), None
    limit_s = max(seconds, 1800.0 if levels else seconds)
    for k in range(1, round(limit_s / STEP_S) + 1):
        (report,) = physics_steps(sim, 1)
        if k == 1 and report.substeps != refine:  # a precondition: on shipped data one step is refine substeps
            raise RuntimeError(f"a step at refine {refine} took {report.substeps} substeps: the bar can't be reached")
        crate, time_s = _integrity(sim, "crate"), k * STEP_S
        onset = time_s if onset is None and crate < 0.9 else onset
        below.update({lv: time_s for lv, t in below.items() if t is None and crate < lv})
        if k == round(seconds / STEP_S):
            at = (crate, _integrity(sim, "wall"))
        if at is not None and all(t is not None for t in below.values()):
            break
    for lv, t in below.items():
        if t is None:
            raise RuntimeError(f"the crate never fell below {lv} in {limit_s} s at {dx_m} m")
    assert at is not None
    return onset, at[0], at[1], below


def test_fire_outcomes_agree_across_rigs(spacings, materials):
    grids = sorted(spacings, reverse=True)
    runs = {dx_m: _burn(dx_m, materials) for dx_m in grids}
    assert all(r[0] is not None for r in runs.values()), runs  # the crate catches at every grid
    onset = agrees(lambda dx_m: runs[dx_m][0], grids)
    assert onset.spread <= 0.1 * min(onset.values), onset  # at about the same time (the bar is unchanged)
    # Converges from coarse (all grids only). Measured 2026-11-21 in 6 s turns: onset 94, 92, 90 at 0.2, 0.1, 0.05 m.
    assert onset.converging is not False, onset
    assert all(r[1] < 0.7 for r in runs.values()), runs  # it is badly burned everywhere
    assert all(r[2] > 0.99 for r in runs.values()), runs  # the concrete wall survives everywhere
    # Known gap (docs/known_gaps.md): the coarsest rig lags in the burn; gated below.


BADLY_BURNED = 0.7  # the level test_fire_outcomes_agree_across_rigs asserts every rig reaches
TIME_TOL = 0.15  # tile_and_client.md §6.3 item 8: a crack-like time converges within 15% of the finer grid's


def _time_below(dx_m, materials, level, *, refine=1):
    return _burn(dx_m, materials, refine=refine, levels=(level,))[3][level]


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "Known gap (docs/known_gaps.md): the coarsest rig lags in the burn, because a coarse cell degrades as one "
        "block. Measured 2026-11-22 through Simulation.step at the 0.5 s step: the crate falls below 0.7 at 830 s at "
        "0.2 m against 629.5 s at 0.1 m (31.9%, against tile §6.3's 15%); below 0.5 the lag is 916.5 s against 811 s "
        "(13.0%). In 6 s turns it was turn 137 against 104. The fix is the reconstructed burn rate (roadmap Phase 2, "
        "'Close the known gap'); this gate then flips and must be removed."
    ),
)
def test_the_crate_is_badly_burned_at_the_same_time_at_every_rig(materials):
    when = agrees(lambda dx_m: _time_below(dx_m, materials, BADLY_BURNED), sorted(FAST_SPACINGS, reverse=True))
    assert when.errors[0] <= TIME_TOL * when.values[-1], when


def test_a_small_fire_changes_nothing_at_any_rig(spacings, materials):
    for dx_m in spacings:
        onset, crate, wall, _ = _burn(dx_m, materials, seconds=360.0, power_w=20_000.0)
        assert onset is None, dx_m
        assert crate > 0.99, dx_m
        assert wall > 0.99, dx_m


# Wood's adiabatic flame temperature is about 2000 C: no fire burning on wood may heat any cell past it. Before
# heat.step refreshed source power after destruction, this scenario peaked at 16,619 C (0.2 m) and 29,213 C (0.1 m).
WOOD_FLAME_C = 2000.0


def _peak(sim, seconds):
    """The hottest any cell got over ``seconds``, read from each physics step's frame."""
    peak = 0.0
    for _ in range(round(seconds / STEP_S)):
        physics_steps(sim, 1)
        peak = max(peak, float(np.max(sim.frames.latest.cells.temperature)))
    return peak


def _fierce(dx_m, materials, refine=1):
    """A 500 kW fire on the crate for 180 s (30 turns): the hottest any cell got, and the crate's integrity at the
    end."""
    sim = _lit(dx_m, materials, ("crate",), 500_000.0, refine=refine)
    return _peak(sim, 180.0), _integrity(sim, "crate")


def test_a_fierce_fire_never_heats_any_cell_past_the_flame_temperature(spacings, materials):
    for dx_m in spacings:
        peak, crate = _fierce(dx_m, materials)
        assert crate < 0.5, dx_m  # it really burned
        assert peak < WOOD_FLAME_C, (dx_m, peak)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "Known gap (docs/known_gaps.md): fires don't consume fuel. Once no solid is left under a fire, the deposit "
        "puts its power into air. Measured 2026-11-22 through Simulation.step: a cell passes 2000 C at 243 s at 0.2 m "
        "and 201.5 s at 0.1 m, and peaks at 423,810 C and 578,046 C by 360 s (in 6 s turns: 207,350 C at 0.2 m by "
        "turn 50). Fix before the Phase 1 crate scenario is gated; this gate then flips and must be removed."
    ),
)
def test_a_fire_that_has_burned_its_fuel_stops_heating(materials):
    for dx_m in FAST_SPACINGS:
        sim = _lit(dx_m, materials, ("crate",), 500_000.0)  # a refused ignite raises RuntimeError, not the gate's type
        peak = _peak(sim, 360.0)  # 60 turns
        assert peak < WOOD_FLAME_C, (dx_m, peak)


def _observables(dx_m, materials, refine):
    """Each passing scenario's observables in this module, measured at ``refine`` (the precondition that refine
    really refines is _burn's: the first step's substeps)."""
    onset, crate, wall, below = _burn(dx_m, materials, refine=refine, levels=(BADLY_BURNED, 0.5))
    small_onset, small_crate, small_wall, _ = _burn(dx_m, materials, 360.0, 20_000.0, refine=refine)
    peak, _ = _fierce(dx_m, materials, refine)
    return {
        "onset": onset,
        "crate": crate,
        "wall": wall,
        "badly_burned": below[BADLY_BURNED],
        "half_burned": below[0.5],
        "peak": peak,
        "small_onset": small_onset,
        "small_crate": small_crate,
        "small_wall": small_wall,
    }


@pytest.mark.parametrize("dx_m", TIERED_SPACINGS)
def test_each_scenario_observable_is_time_converged_at_the_shipped_refine(dx_m, materials):
    """sim_core.md §11 bar 2b (verification; source verify_harness.md §4): between substep_refine 1, shipped, and 4,
    each observable moves by under a quarter of its bar, so these scenarios measure space alone. The bars are the
    tests' own: onset agrees to 10% of itself, the burn times to TIME_TOL of themselves, and the thresholds (crate
    under 0.7, wall over 0.99, peak under WOOD_FLAME_C, the small fire's crate and wall over 0.99) by their margin at
    refine 4; the small fire never catches at either. Measured 2026-11-22 at T3's 0.5 s step, refine 1 against 4, in
    world seconds: at 0.2 m onset 569 and 569, crate 0.5502 and 0.5507 (a quarter of the margin is 0.037), burn times
    830 and 830.5, 916.5 both, peak 542.4 and 543.5 C; at 0.1 m onset 555 and 555.5, crate 0.3704 both, 629.5 both,
    811 and 811.5, peak 659.6 and 659.3 C; the small fire's crate and wall 1.0 at both grids. Until PR 4a these
    scenarios took 6 s turns, twelve times T3's step.

    What it covers (PR 3 review S3): this module's passing scenarios. Its two strict red gates (the coarse rig's lag,
    a fire past its fuel) and test_act_validation's fiercest allowed fire fail their own bars at refine 4, so they
    have no margin to hold a quarter of; they join when their gates flip (docs/plans/checklists.md). The strike
    scenarios resolve in the apply phase and run no substep, so refine can't move them."""
    shipped, refined = _observables(dx_m, materials, 1), _observables(dx_m, materials, 4)
    assert shipped["small_onset"] is None, shipped  # a class bar: the small fire never catches
    assert refined["small_onset"] is None, refined
    assert shipped["onset"] is not None, shipped  # the crate catches, so its onset has a bar
    assert refined["onset"] is not None, refined
    bars = {
        "onset": 0.1 * refined["onset"],
        "crate": BADLY_BURNED - refined["crate"],
        "wall": refined["wall"] - 0.99,
        "badly_burned": TIME_TOL * refined["badly_burned"],
        "half_burned": TIME_TOL * refined["half_burned"],
        "peak": WOOD_FLAME_C - refined["peak"],
        "small_crate": refined["small_crate"] - 0.99,
        "small_wall": refined["small_wall"] - 0.99,
    }
    assert all(bar > 0 for bar in bars.values()), bars  # each threshold really holds at refine 4
    moved = {name: abs(shipped[name] - refined[name]) for name in bars}
    assert all(moved[name] < bars[name] / 4 for name in bars), (moved, bars)


def _reversed_within_cadence(laws):
    """The tuple with each cadence group's laws in reverse order (sim_core.md §11 bar 3); groups keep their places."""
    groups = {c: [law for law in laws if law.cadence is c] for c in Cadence}
    return tuple(groups[law.cadence].pop() for law in laws)


def _burn_class(dx_m, materials, laws, steps):
    """The burn's outcome class (splitting.md §6 rule 4) at a refine read from the run: whether the crate caught,
    whether it is badly burned, and whether the wall survives, after ``steps`` physics steps."""

    def outcome(run: Run):
        onset, crate, wall, _ = _burn(dx_m, materials, steps * STEP_S, refine=run.steps // steps, laws=laws)
        return onset is not None, crate < BADLY_BURNED, wall > 0.99

    return outcome, Run(dx_m, STEP_S, steps)


def _orders(laws):
    return tuple(laws), _reversed_within_cadence(laws)


def _orders_agree(dx_m, materials, laws, steps):
    """Bar 3's first half: the forward tuple and the tuple reversed within each cadence group give one outcome class."""
    classes = set()
    for order in _orders(laws):
        outcome, run = _burn_class(dx_m, materials, order, steps)
        classes.add(outcome(run))
    return len(classes) == 1


def _each_order_refines(dx_m, materials, laws, steps):
    """Bar 3's second half: each order keeps its class under substep_refine 1 and 4."""
    for order in _orders(laws):
        outcome, run = _burn_class(dx_m, materials, order, steps)
        if not same_class_under_refinement(outcome, run, factors=(1, 4)):
            return False
    return True


def _splitting_holds(dx_m, materials, laws, steps=1800):
    """Bar 3: both halves, over the burn's 900 s by default."""
    return _each_order_refines(dx_m, materials, laws, steps) and _orders_agree(dx_m, materials, laws, steps)


@pytest.mark.parametrize("dx_m", TIERED_FAST_SPACINGS)
def test_the_law_tuple_reversed_within_each_cadence_gives_the_same_outcome(dx_m, materials):
    """sim_core.md §11 bar 3 (verification; source splitting.md §6 rule 4), on the burn scenario, through
    Simulation.step. The reversed tuple is (damage.loads, damage.thermal, heat): loads alone in its group, thermal
    damage before heat in the substep."""
    reversed_tuple = _reversed_within_cadence(physics.DEFAULT_LAWS)
    assert [law.name for law in reversed_tuple] == ["damage.loads", "damage.thermal", "heat"]
    assert _splitting_holds(dx_m, materials, physics.DEFAULT_LAWS)


@dataclass(frozen=True)
class _Plant:
    """One of the planted order-sensitive pair: a source, or a clamp that decides at a threshold. ``act`` is its step;
    it holds the name and the declared reads and writes of the law whose token the plant borrows."""

    name: str
    reads: tuple[str, ...]
    writes: tuple[str, ...]
    act: Callable[[MaterialGrid, float], object]
    version: int = 1
    cadence: Cadence = Cadence.PER_SUBSTEP
    bound_reads: tuple[str, ...] = ()

    def new_state(self, grid):
        return STATELESS

    def prepare(self, grid, state, exposure):
        return LawInputs()

    def stable_dt(self, grid, state):
        return math.inf

    def step(self, grid, dt_s: float, inputs: LawInputs, state) -> Changes:
        self.act(grid, dt_s)
        return Changes()


def _pair(source, clamp):
    """A planted pair under the real laws' tokens, so they write what heat and damage.thermal may."""
    return (
        _Plant("damage.loads", ("material",), ("integrity",), lambda grid, dt_s: None, cadence=Cadence.PER_RECORD),
        _Plant("heat", ("temperature", "integrity"), ("temperature",), source),
        _Plant("damage.thermal", ("temperature", "integrity"), ("integrity",), clamp),
    )


def _both_halves_fail(crate):
    """A source and a clamp. Forward, the clamp reads the source's heat and breaks the crate within the step;
    reversed, it reads the step's start, so at substep_refine 1 the crate survives the step and at 4 it breaks (the
    clamp's last substep reads three quarters of the heat)."""

    def source(grid, dt_s):
        grid.temperature[crate] += 1000.0 * dt_s / STEP_S

    def clamp(grid, dt_s):
        grid.integrity[grid.temperature > 500.0] = 0.0

    return _pair(source, clamp)


def _order_alone_fails(crate):
    """Order-sensitive, stable under refinement: the source holds the crate at 1000 C, and the clamp decides once per
    run, on its first substep (each plant run is one physics step, a fresh grid). Forward it reads the source's heat
    and breaks the crate; reversed it reads the step's start and never breaks it, at every refine."""
    decided: list[MaterialGrid] = []

    def source(grid, dt_s):
        grid.temperature[crate] = 1000.0

    def clamp(grid, dt_s):
        if any(g is grid for g in decided):
            return  # this run's one physics step has decided already
        decided.append(grid)
        grid.integrity[grid.temperature > 500.0] = 0.0

    return _pair(source, clamp)


def _refinement_alone_fails(crate):
    """Order-consistent, sensitive to refinement: the source does nothing, and the clamp breaks the crate only on a
    substep shorter than half the physics step, so both orders agree at each refine and both change class between 1
    and 4."""

    def clamp(grid, dt_s):
        if dt_s < STEP_S / 2:
            grid.integrity[crate] = 0.0

    return _pair(lambda grid, dt_s: None, clamp)


@pytest.mark.parametrize(
    ("plant", "orders_agree", "each_refines"),
    [(_both_halves_fail, False, False), (_order_alone_fails, False, True), (_refinement_alone_fails, True, False)],
)
def test_the_splitting_bar_fails_on_each_half_alone(materials, monkeypatch, plant, orders_agree, each_refines):
    """Proof that bar 3 can fail, and that each half can fail without the other (PR 3 review S2): the order plant
    turns the bar red with the refinement half deleted, and the refinement plant with the order half deleted."""
    crate = world_of(make(SCENE, materials, dx_m=0.2, limits=LIMITS)).grid.regions["crate"].cells
    pair = plant(crate)
    for law in pair:
        monkeypatch.setitem(physics._REGISTERED, law.name, law)
    assert _orders_agree(0.2, materials, pair, steps=1) is orders_agree
    assert _each_order_refines(0.2, materials, pair, steps=1) is each_refines
    assert not _splitting_holds(0.2, materials, pair, steps=1)
