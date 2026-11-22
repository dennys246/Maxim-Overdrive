"""The verification rule on a full turn loop: a fire on a crate, and on a concrete wall, at every grid.

The truth grid (0.1 m) agrees with the reference (0.05 m, under MAXIM_OVERDRIVE_ALL_TIERS=1) and converges from the
coarse grid (0.2 m) (world_model §1.1), measured through ``simcore.verify`` (docs/design/verify_harness.md).

Since step 5a's PR 3 there is no substep floor: each 6 s turn is one fixed physics step at stability's count, the same
at every spacing on shipped data, so these scenarios refine space alone; bar 2b below holds them time-converged at the
shipped refine. They still step World.advance's 6 s turn; moving them to Simulation's 0.5 s step is PR 4's. Heat's
own studies (tests/test_heat.py) refine space and time apart.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pytest

from maxim_overdrive import data
from simcore.adapters.sem.bridge import region_parts
from simcore.core import physics
from simcore.core.applier import Applier
from simcore.core.grid import MaterialGrid
from simcore.core.law import Cadence, Changes, LawInputs
from simcore.core.scene import Box, Scene
from simcore.core.world import World
from simcore.verify import Run, agrees, same_class_under_refinement
from tests.conftest import ALL_SPACINGS, FAST_SPACINGS

LIMITS = data.action_limits()


SCENE = Scene(
    (3.0, 3.0, 2.0),
    (Box((1.2, 1.2, 0), (1.8, 1.8, 0.6), "wood", "crate"), Box((0, 0, 0), (0.6, 3.0, 2.0), "concrete", "wall")),
)


def _burn(dx_m, materials, turns=150, power_w=60_000.0, *, refine=1, laws=physics.DEFAULT_LAWS):
    w = World.from_scene(SCENE, materials, dx_m=dx_m, limits=LIMITS)
    crate_s, crate_m = region_parts(Applier(w), w.frames, "crate")
    wall_s, wall_m = region_parts(Applier(w), w.frames, "wall")
    for mods in (crate_m, wall_m):  # preconditions raise RuntimeError, never a red gate's AssertionError
        if not mods["structure"].execute("ignite", {"power_w": power_w, "radius_m": 0.3}).success:
            raise RuntimeError("ignite refused: the test can't reach its bar")
    onset = None
    for turn in range(turns):
        w.advance(refine=refine, laws=laws)
        if onset is None and crate_s["integrity"].value() < 0.9:
            onset = turn
    return onset, crate_s["integrity"].value(), wall_s["integrity"].value()


def test_fire_outcomes_agree_across_rigs(spacings, materials):
    grids = sorted(spacings, reverse=True)
    runs = {dx_m: _burn(dx_m, materials) for dx_m in grids}
    assert all(r[0] is not None for r in runs.values()), runs  # the crate catches at every grid
    onset = agrees(lambda dx_m: runs[dx_m][0], grids)
    assert onset.spread <= 0.1 * min(onset.values), onset  # at about the same turn (the bar is unchanged)
    # Converges from coarse (all grids only). Measured 2026-11-21: onset 94, 92, 90 at 0.2, 0.1, 0.05 m.
    assert onset.converging is not False, onset
    assert all(r[1] < 0.7 for r in runs.values()), runs  # it is badly burned everywhere
    assert all(r[2] > 0.99 for r in runs.values()), runs  # the concrete wall survives everywhere
    # Known gap (docs/architecture.md): the coarsest rig lags in the burn; gated below.


BADLY_BURNED = 0.7  # the level test_fire_outcomes_agree_across_rigs asserts every rig reaches
TIME_TOL = 0.15  # tile_and_client.md §6.3 item 8: a crack-like time converges within 15% of the finer grid's


def _turn_below(dx_m, materials, level, *, turns=300, power_w=60_000.0, refine=1):
    w = World.from_scene(SCENE, materials, dx_m=dx_m, limits=LIMITS)
    crate_s, crate_m = region_parts(Applier(w), w.frames, "crate")
    wall_m = region_parts(Applier(w), w.frames, "wall")[1]
    for mods in (crate_m, wall_m):
        if not mods["structure"].execute("ignite", {"power_w": power_w, "radius_m": 0.3}).success:
            raise RuntimeError("ignite refused: the gate can't reach its bar")
    for turn in range(turns):
        w.advance(refine=refine)
        if crate_s["integrity"].value() < level:
            return turn
    raise RuntimeError(f"the crate never fell below {level} in {turns} turns at {dx_m} m")


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "Known gap (docs/architecture.md): the coarsest rig lags in the burn, because a coarse cell degrades as one "
        "block. Measured 2026-11-22, one substep per 6 s turn: the crate falls below 0.7 at turn 137 at 0.2 m against "
        "104 at 0.1 m (32%, against tile §6.3's 15%); below 0.5 the lag is 152 against 134 (13.4%). The fix is the "
        "reconstructed burn rate (roadmap Phase 2, 'Close the known gap'); this gate then flips and must be removed."
    ),
)
def test_the_crate_is_badly_burned_at_the_same_turn_at_every_rig(materials):
    turn = agrees(lambda dx_m: _turn_below(dx_m, materials, BADLY_BURNED), sorted(FAST_SPACINGS, reverse=True))
    assert turn.errors[0] <= TIME_TOL * turn.values[-1], turn


def test_a_small_fire_changes_nothing_at_any_rig(spacings, materials):
    for dx_m in spacings:
        onset, crate, wall = _burn(dx_m, materials, turns=60, power_w=20_000.0)
        assert onset is None, dx_m
        assert crate > 0.99, dx_m
        assert wall > 0.99, dx_m


# Wood's adiabatic flame temperature is about 2000 C: no fire burning on wood may heat any cell past it. Before
# heat.step refreshed source power after destruction, this scenario peaked at 16,619 C (0.2 m) and 29,213 C (0.1 m).
WOOD_FLAME_C = 2000.0


def _fierce(dx_m, materials, refine=1):
    """A 500 kW fire on the crate for 30 turns: the hottest any cell got, and the crate's integrity at the end."""
    w = World.from_scene(SCENE, materials, dx_m=dx_m, limits=LIMITS)
    crate_s, crate_m = region_parts(Applier(w), w.frames, "crate")
    if not crate_m["structure"].execute("ignite", {"power_w": 500_000.0, "radius_m": 0.3}).success:
        raise RuntimeError("ignite refused: the test can't reach its bar")
    peak = 0.0
    for _ in range(30):
        w.advance(refine=refine)
        peak = max(peak, float(np.max(w.grid.temperature)))
    return peak, crate_s["integrity"].value()


def test_a_fierce_fire_never_heats_any_cell_past_the_flame_temperature(spacings, materials):
    for dx_m in spacings:
        peak, crate = _fierce(dx_m, materials)
        assert crate < 0.5, dx_m  # it really burned
        assert peak < WOOD_FLAME_C, (dx_m, peak)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "Known gap (docs/architecture.md): fires don't consume fuel. Once no solid is left under a fire, "
        "World._power_field deposits its power into air (207,350 C at 0.2 m by turn 50). Fix before the Phase 1 "
        "crate scenario is gated; this gate then flips and must be removed."
    ),
)
def test_a_fire_that_has_burned_its_fuel_stops_heating(materials):
    for dx_m in FAST_SPACINGS:
        w = World.from_scene(SCENE, materials, dx_m=dx_m, limits=LIMITS)
        _, crate_m = region_parts(Applier(w), w.frames, "crate")
        # A precondition raises RuntimeError, not the gate's raises= type, so a refused ignite can't count as the miss.
        if not crate_m["structure"].execute("ignite", {"power_w": 500_000.0, "radius_m": 0.3}).success:
            raise RuntimeError("ignite refused: the gate can't reach its bar")
        peak = 0.0
        for _ in range(60):
            w.advance()
            peak = max(peak, float(np.max(w.grid.temperature)))
        assert peak < WOOD_FLAME_C, (dx_m, peak)


def _observables(dx_m, materials, refine):
    """Each passing scenario's observables in this module, measured at ``refine``."""
    taken = World.from_scene(SCENE, materials, dx_m=dx_m, limits=LIMITS).advance(refine=refine)
    if taken != refine:  # a precondition: on shipped data one 6 s turn is one substep, so refine really refines it
        raise RuntimeError(f"a turn at refine {refine} took {taken} substeps: the gate can't reach its bar")
    onset, crate, wall = _burn(dx_m, materials, refine=refine)
    small_onset, small_crate, small_wall = _burn(dx_m, materials, turns=60, power_w=20_000.0, refine=refine)
    peak, _ = _fierce(dx_m, materials, refine)
    return {
        "onset": onset,
        "crate": crate,
        "wall": wall,
        "badly_burned": _turn_below(dx_m, materials, BADLY_BURNED, refine=refine),
        "half_burned": _turn_below(dx_m, materials, 0.5, refine=refine),
        "peak": peak,
        "small_onset": small_onset,
        "small_crate": small_crate,
        "small_wall": small_wall,
    }


@pytest.mark.parametrize("dx_m", ALL_SPACINGS)
def test_each_scenario_observable_is_time_converged_at_the_shipped_refine(dx_m, materials):
    """sim_core.md §11 bar 2b (verification; source verify_harness.md §4): between substep_refine 1, shipped, and 4,
    each observable moves by under a quarter of its bar, so these scenarios measure space alone. The bars are the
    tests' own: onset agrees to 10% of itself, the burn times to TIME_TOL of themselves, and the thresholds (crate
    under 0.7, wall over 0.99, peak under WOOD_FLAME_C, the small fire's crate and wall over 0.99) by their margin at
    refine 4; the small fire never catches at either. Measured 2026-11-22, refine 1 against 4: at 0.2 m onset 94 and
    94, crate 0.539 and 0.548 (a quarter of the margin is 0.038), burn times 137 and 138, 152 and 152, peak 536 and
    542 C; at 0.1 m onset 92 and 92, crate 0.370 both, 104 and 104, 134 and 135, peak 670 and 650 C; at 0.05 m onset
    89 and 90, crate 0.381 and 0.382, 101 both, 121 and 122, peak 1039 and 1025 C; the small fire's crate and wall
    1.0 at every grid. These scenarios still take 6 s turns, so this holds at P = 6 s, twelve times T3's step.

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


def _burn_class(dx_m, materials, laws, turns):
    """The burn's outcome class (splitting.md §6 rule 4) at a refine read from the run: whether the crate caught,
    whether it is badly burned, and whether the wall survives."""

    def outcome(run: Run):
        onset, crate, wall = _burn(dx_m, materials, turns=turns, refine=run.steps // turns, laws=laws)
        return onset is not None, crate < BADLY_BURNED, wall > 0.99

    return outcome, Run(dx_m, 6.0, turns)


def _orders(laws):
    return tuple(laws), _reversed_within_cadence(laws)


def _orders_agree(dx_m, materials, laws, turns):
    """Bar 3's first half: the forward tuple and the tuple reversed within each cadence group give one outcome class."""
    classes = set()
    for order in _orders(laws):
        outcome, run = _burn_class(dx_m, materials, order, turns)
        classes.add(outcome(run))
    return len(classes) == 1


def _each_order_refines(dx_m, materials, laws, turns):
    """Bar 3's second half: each order keeps its class under substep_refine 1 and 4."""
    for order in _orders(laws):
        outcome, run = _burn_class(dx_m, materials, order, turns)
        if not same_class_under_refinement(outcome, run, factors=(1, 4)):
            return False
    return True


def _splitting_holds(dx_m, materials, laws, turns=150):
    """Bar 3: both halves."""
    return _each_order_refines(dx_m, materials, laws, turns) and _orders_agree(dx_m, materials, laws, turns)


@pytest.mark.parametrize("dx_m", FAST_SPACINGS)
def test_the_law_tuple_reversed_within_each_cadence_gives_the_same_outcome(dx_m, materials):
    """sim_core.md §11 bar 3 (verification; source splitting.md §6 rule 4), on the burn scenario. The reversed tuple
    is (damage.loads, damage.thermal, heat): loads alone in its group, thermal damage before heat in the substep."""
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

    def stable_dt(self, grid):
        return math.inf

    def step(self, grid, dt_s: float, inputs: LawInputs) -> Changes:
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
    """A source and a clamp. Forward, the clamp reads the source's heat and breaks the crate within the turn;
    reversed, it reads the turn's start, so at substep_refine 1 the crate survives the turn and at 4 it breaks (the
    clamp's last substep reads three quarters of the heat). Measured: forward (0, 0.0, 1.0) at both refines,
    reversed (None, 1.0) at 1 and (0, 0.0) at 4."""

    def source(grid, dt_s):
        grid.temperature[crate] += 1000.0 * dt_s / 6.0

    def clamp(grid, dt_s):
        grid.integrity[grid.temperature > 500.0] = 0.0

    return _pair(source, clamp)


def _order_alone_fails(crate):
    """Order-sensitive, stable under refinement: the source holds the crate at 1000 C, and the clamp decides once per
    physics step, on its first substep. Forward it reads the source's heat and breaks the crate; reversed it reads the
    turn's start and never breaks it, at every refine."""
    decided: list[tuple[MaterialGrid, int]] = []

    def source(grid, dt_s):
        grid.temperature[crate] = 1000.0

    def clamp(grid, dt_s):
        if decided and decided[-1][0] is grid and decided[-1][1] == grid.time_us:
            return  # this physics step has decided already (its time moves only after its last substep)
        decided.append((grid, grid.time_us))
        grid.integrity[grid.temperature > 500.0] = 0.0

    return _pair(source, clamp)


def _refinement_alone_fails(crate):
    """Order-consistent, sensitive to refinement: the source does nothing, and the clamp breaks the crate only on a
    substep shorter than half the turn, so both orders agree at each refine and both change class between 1 and 4."""

    def clamp(grid, dt_s):
        if dt_s < 3.0:
            grid.integrity[crate] = 0.0

    return _pair(lambda grid, dt_s: None, clamp)


@pytest.mark.parametrize(
    ("plant", "orders_agree", "each_refines"),
    [(_both_halves_fail, False, False), (_order_alone_fails, False, True), (_refinement_alone_fails, True, False)],
)
def test_the_splitting_bar_fails_on_each_half_alone(materials, monkeypatch, plant, orders_agree, each_refines):
    """Proof that bar 3 can fail, and that each half can fail without the other (PR 3 review S2): the order plant
    turns the bar red with the refinement half deleted, and the refinement plant with the order half deleted."""
    crate = World.from_scene(SCENE, materials, dx_m=0.2, limits=LIMITS).grid.regions["crate"].cells
    pair = plant(crate)
    for law in pair:
        monkeypatch.setitem(physics._REGISTERED, law.name, law)
    assert _orders_agree(0.2, materials, pair, turns=1) is orders_agree
    assert _each_order_refines(0.2, materials, pair, turns=1) is each_refines
    assert not _splitting_holds(0.2, materials, pair, turns=1)
