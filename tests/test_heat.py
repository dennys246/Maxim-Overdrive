"""Heat conduction against a closed-form solution, plus conservation and convergence.

The laws write the cells only inside the grid's write window (boundaries §4.1), so each test opens it, as
``Simulation.step`` does on the shipped path.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
import pytest

from simcore.core import heat, physics, topology
from simcore.core.exposure import Exposure
from simcore.core.grid import MaterialGrid
from simcore.core.law import STATELESS, Cadence, Changes, LawInputs, LawState
from simcore.core.materials import AIR_ID
from simcore.core.scene import Box, Scene, constructing
from simcore.core.stepping import substep_loop
from simcore.verify import Run, converges
from tests._cells import NO_SOURCES, heat_alone, paint
from tests.conftest import ALL_TIERS

SIGMA0, T_S = 0.3, 3600.0


def _bar(dx_m, materials):
    g = Scene((4.0, 0.2, 0.2), (Box((0, 0, 0), (4, 0.2, 0.2), "steel"),)).build(materials, dx_m=dx_m)
    x = g.centers(0)[:, None, None]
    with constructing(g):
        g.temperature[:] = 20 + 100 * np.exp(-((x - 2) ** 2) / (2 * SIGMA0**2))
    return g, x


PHYSICS_STEP_S = 0.5  # T3's P (simcore.core.simulation.T3.physics_seconds): the shipped path's fixed physics step


def _spread(dx_m, materials, refine=1):
    """The bar after T_S of heat alone on the shipped path: fixed physics steps of P, each refined ``refine`` times."""
    g, x = _bar(dx_m, materials)
    with g.writing(writer=None):
        for _ in range(round(T_S / PHYSICS_STEP_S)):
            heat_alone(g, PHYSICS_STEP_S, refine)
    s2 = SIGMA0**2 + 2 * materials["steel"].diffusivity_m2_s * T_S
    exact = 20 + 100 * SIGMA0 / np.sqrt(s2) * np.exp(-((x - 2) ** 2) / (2 * s2))
    return g.temperature.copy(), exact


def _error(dx_m, materials):
    got, exact = _spread(dx_m, materials)
    return float(np.abs(got - exact).max() / (exact.max() - 20))


def test_at_the_fixed_step_heats_time_error_is_below_its_space_error(materials):
    """sim_core.md §11 bar 1 (verification): at P = 0.5 s and 0.1 m, the error the step length adds (P against P/8,
    the same spacing) is below the error the spacing leaves (P/8 against the closed form). If this failed, a measured
    accuracy floor would join the step rule as a truth constant (§8); it is the only thing that may."""
    coarse, exact = _spread(0.1, materials, refine=1)
    fine, _ = _spread(0.1, materials, refine=8)
    amplitude = exact.max() - 20
    time_error = float(np.abs(coarse - fine).max() / amplitude)
    space_error = float(np.abs(fine - exact).max() / amplitude)
    assert time_error < space_error, (time_error, space_error)


def test_gaussian_spreads_as_the_heat_equation_says(dx_m, materials):
    assert _error(dx_m, materials) < 0.02


def _gaussian(dx_m, materials, substeps):
    """The bar after T_S seconds in exactly ``substeps`` steps, each one fixed physics step of T_S / substeps: its
    closed-form error and its peak."""
    g, x = _bar(dx_m, materials)
    with g.writing(writer=None):
        taken = sum(heat_alone(g, T_S / substeps) for _ in range(substeps))
    if taken != substeps:  # a precondition: the study's step, not stability's, set the count
        raise RuntimeError(f"heat took {taken} substeps, not the study's {substeps}")
    s2 = SIGMA0**2 + 2 * materials["steel"].diffusivity_m2_s * T_S
    exact = 20 + 100 * SIGMA0 / np.sqrt(s2) * np.exp(-((x - 2) ** 2) / (2 * s2))
    return float(np.abs(g.temperature - exact).max() / (exact.max() - 20)), float(g.temperature.max())


def _sigma_t(materials):
    return float(np.sqrt(SIGMA0**2 + 2 * materials["steel"].diffusivity_m2_s * T_S))


def _space_study(materials, substeps):
    runs = [Run(dx_m, T_S / substeps, substeps) for dx_m in (0.2, 0.1, 0.05)]
    return converges(lambda run: _gaussian(run.dx_m, materials, run.steps)[0], runs, exact=0.0)


SPACE_BASE = 64  # the space study's step: 1/64 of stability at 0.05 m (0.45 s); 1/16 is not time-converged


@pytest.mark.slow
@pytest.mark.skipif(not ALL_TIERS, reason="slow: runs the 0.05 m grid; set MAXIM_OVERDRIVE_ALL_TIERS=1")
def test_heat_is_second_order_in_space(materials):
    """Finite volumes with harmonic-mean faces are second order in space (world_model E2: space refined alone).

    The bar, set before measuring (verify_harness §5): each observed order is 2 within the next truncation term's
    relative size, (dx_coarse / sigma_t)**2, sigma_t the Gaussian's width at T_S. The owner accepted it (2026-11-21,
    ruling (a)) though it is wider than the old test's one-sided "fine < coarse / 4" (order > 2), which measured
    cancelled space and time error, not space: the clean study's order at 0.2/0.1 m is 1.92.

    The step is shared by every grid and must be time-converged: a quarter of it moves each order by under a quarter
    of that order's bar (set after seeing Physics' review measure 0.011; owner accepted, 2026-11-21). Measured on this
    0.2 m-thick bar: orders 1.918 and 1.997 at 0.45 s, 1.915 and 1.986 at 0.1125 s; errors 1.286%, 0.340%, 0.085%.
    At 1.8 s (1/16 of stability) the fine order is 2.045, inside its bar but not time-converged. At the finest grid's
    stability step (28.85 s) the orders are 2.20 and 4.90, so stability alone is not enough.
    """
    finest = _bar(0.05, materials)[0]
    base = SPACE_BASE * math.ceil(T_S / heat.stable_dt(finest))
    studies = [_space_study(materials, substeps) for substeps in (base, 4 * base)]
    for study in studies:
        for p, run in zip(study.orders, study.runs, strict=False):
            assert abs(p - 2) <= (run.dx_m / _sigma_t(materials)) ** 2, study.orders
    # Time-converged: a quarter of the step moves each order by under a quarter of its bar.
    for p, q, run in zip(studies[0].orders, studies[1].orders, studies[0].runs, strict=False):
        assert abs(p - q) <= (run.dx_m / _sigma_t(materials)) ** 2 / 4, (studies[0].orders, studies[1].orders)


def test_heat_is_first_order_in_time(materials):
    """Explicit Euler is first order in time (world_model E2: time refined alone, at 0.2 m).

    The bar (owner ruling (i), 2026-11-21): each Richardson order is 1 within (alpha / sigma0**2) * dt_coarse. Its
    derivation: the explicit-Euler expansion predicts p - 1 = c * (alpha / sigma_T**2) * dt at the pulse's peak,
    c = (3 / (4 ln 2)) * |10/3 - 8.75 * alpha * T / sigma_T**2| = 1.19 here (Physics review, S3). The bar equals
    2.04 * (alpha / sigma_T**2) * dt: the leading term plus a margin for higher-order terms and the 0.2 m grid's
    coarse resolution of the pulse, whose measured coefficient is 1.36 and 1.40 for the two orders at 0.2 m (1.24 at
    0.1 m, 1.207 at 0.05 m).

    Corrected: this test first said the decay rate used sigma0 because "the initial curvature generates most of the
    time error". That was wrong; sigma_T is the right scale, and the first bar written (sigma_T, no coefficient) only
    lacked the coefficient. The owner ruled (a) on that wrong reason, then (i) on the derivation above. Measured
    2026-11-21: orders 1.116 and 1.060.

    The reference must also have settled: the two orders agree within the finer order's own bar, (alpha / sigma0**2)
    * dt at the second run (0.087 against a gap of 0.056, 0.65 of it). The owner first accepted the coarser order's
    bar (0.173); the delta review showed the finer one holds and guards more, so the bar was tightened. A tolerance
    at the second-finest step can't be met at any refinement: the gap is 1.3 times its bar.
    """
    dx_m = 0.2
    base = math.ceil(T_S / heat.stable_dt(_bar(dx_m, materials)[0]))
    runs = [Run(dx_m, T_S / (base * k), base * k) for k in (1, 2, 4, 8)]
    decay_rate = materials["steel"].diffusivity_m2_s / SIGMA0**2
    study = converges(
        lambda run: _gaussian(run.dx_m, materials, run.steps)[1], runs, order_tol=decay_rate * runs[1].dt_s
    )
    assert len(study.orders) == 2
    for p, run in zip(study.orders, study.runs, strict=False):
        assert abs(p - 1) <= decay_rate * run.dt_s, study.orders
    assert study.reference_converged, study.orders


def test_a_step_takes_exactly_the_substeps_it_plans_however_many(materials):
    """Red first: an end test of elapsed < seconds - 1e-12 on a running float sum took 8,001 substeps when asked for
    8,000 of 0.45 s, a sliver from rounding that grows with the count (found by step 4's space study)."""
    g, _ = _bar(0.2, materials)
    stability = math.ceil(T_S / heat.stable_dt(g))
    for refine in (4, 8_000):  # 8,000 is the red-first case's count; more adds time, not coverage
        with g.writing(writer=None):
            assert heat_alone(g, T_S, refine) == refine * stability


@dataclass(frozen=True)
class _EditOnce:
    """A per-substep test law that asks Topology for one world edit on its first substep and records every dt."""

    edit: Callable[[MaterialGrid], topology.Request]
    dts: list[float] = field(default_factory=list)
    name: str = "test.edit_once"
    version: int = 1
    cadence: Cadence = Cadence.PER_SUBSTEP
    reads: tuple[str, ...] = ()
    writes: tuple[str, ...] = ()
    bound_reads: tuple[str, ...] = ()

    def new_state(self, grid: MaterialGrid) -> LawState:
        return STATELESS

    def prepare(self, grid: MaterialGrid, state: LawState, exposure: Exposure) -> LawInputs:
        return LawInputs()

    def stable_dt(self, grid: MaterialGrid, state: LawState) -> float:
        return math.inf

    def step(self, grid: MaterialGrid, dt_s: float, inputs: LawInputs, state: LawState) -> Changes:
        self.dts.append(dt_s)
        return Changes((self.edit(grid),)) if len(self.dts) == 1 else Changes()


def _to_steel(grid: MaterialGrid) -> topology.Request:
    return topology.Paint(np.ones(grid.shape, dtype=bool), "steel")


def test_a_step_replans_at_the_shorter_step_when_a_change_tightens_stability(materials):
    """When a law's world edit makes stability need a shorter step (wood becoming steel, about 100x more
    diffusive), the rest of the call is replanned at the new bound instead of overrunning it."""
    g = MaterialGrid.empty((0.6, 0.6, 0.6), materials, dx_m=0.2)
    with constructing(g):
        paint(g, np.ones(g.shape, dtype=bool), "wood")
        g.temperature[:] = np.random.default_rng(1).uniform(0, 100, g.shape)
    seconds = 2 * heat.stable_dt(g)  # two planned substeps at wood's step
    law = _EditOnce(_to_steel)
    with g.writing(writer=None):
        taken = physics.Physics(g, (heat.HEAT, law)).run(seconds, refine=1, exposure=NO_SOURCES)
    turned = law.dts[:1]
    steel_dt = heat.stable_dt(g)
    assert steel_dt < turned[0]  # the change really tightened stability below the planned step
    assert taken == 1 + math.ceil((seconds - turned[0]) / steel_dt)
    assert np.isfinite(g.temperature).all()
    assert g.temperature.min() >= 0.0  # stable: no overshoot past the initial bounds
    assert g.temperature.max() <= 100.0


@pytest.mark.parametrize("k", [27, 43, 54, 86])
def test_a_replan_splits_the_rest_evenly_and_never_takes_a_zero_length_substep(materials, k):
    """Red first: replanning at dt = bound with ceil(remaining / bound) steps took a 0.0 s substep whenever the
    remainder was a whole number of bounds up to rounding. These k did on this machine (2026-11-21, Physics S1)."""
    g = MaterialGrid.empty((0.6, 0.6, 0.6), materials, dx_m=0.2)
    with constructing(g):
        paint(g, np.ones(g.shape, dtype=bool), "steel")
    steel_dt = heat.stable_dt(g)
    with constructing(g):
        paint(g, np.ones(g.shape, dtype=bool), "wood")
        g.temperature[:] = np.random.default_rng(1).uniform(0, 100, g.shape)
    law = _EditOnce(_to_steel)
    with g.writing(writer=None):
        physics.Physics(g, (heat.HEAT, law)).run(2 * k * steel_dt, refine=2, exposure=NO_SOURCES)
    rest = law.dts[1:]
    assert min(rest) == pytest.approx(max(rest), rel=1e-9)  # one even step, so no zero-length or sliver substep
    assert max(rest) <= steel_dt * (1 + 1e-12)  # an even split can exceed the bound by one ulp (Physics delta N-1)


def test_insulated_world_conserves_heat(dx_m, materials):
    g = Scene(
        (1.2, 1.2, 1.2), (Box((0, 0, 0), (1.2, 1.2, 0.6), "concrete"), Box((0, 0, 0.6), (1.2, 1.2, 1.2), "steel"))
    ).build(materials, dx_m=dx_m)
    with constructing(g):
        g.temperature[:] = np.random.default_rng(0).uniform(0, 500, g.shape)
    before = heat.heat_energy_j(g)
    with g.writing(writer=None):
        heat_alone(g, 3600.0)
    assert abs(heat.heat_energy_j(g) - before) / before < 1e-9


def test_step_never_exceeds_the_stability_bound(materials):
    dx_m = 0.2
    g = Scene((1.0, 1.0, 1.0), (Box((0, 0, 0), (1, 1, 1), "steel"),)).build(materials, dx_m=dx_m)
    with constructing(g):
        g.temperature[2, 2, 2] = 1000.0
    with g.writing(writer=None):
        n = heat_alone(g, 10 * 3600.0)
    assert n >= 10 * 3600.0 / heat.stable_dt(g)
    assert np.isfinite(g.temperature).all()
    assert np.max(g.temperature) <= 1000.0 + 1e-6


def test_a_cell_destroyed_mid_turn_gets_no_more_source_power(dx_m, materials, monkeypatch):
    """Closed form: one wood cell, constant power on solids, destroyed after the first substep.

    It gains exactly one substep's energy at wood's heat capacity. Depositing the turn's power into it after it has
    become air (1/1000 of wood's rho*cp) is what drove burning crates to tens of thousands of degrees. The power is
    heat's ``prepare``, patched to put ``p_w`` on solid cells, so the test holds that prepare reruns after an edit
    (sim_core.md §5): deleting the rerun leaves the first substep's power on the destroyed cell.
    """
    g = MaterialGrid.empty((dx_m,) * 3, materials, dx_m=dx_m)
    with constructing(g):
        paint(g, np.ones(g.shape, dtype=bool), "wood")
    p_w = 1000.0

    def prepare(self, grid, state, exposure):
        return LawInputs(power_w=p_w * grid.solid.astype(np.float64))

    monkeypatch.setattr(heat.HeatLaw, "prepare", prepare)
    law = _EditOnce(lambda grid: topology.Destroy(np.ones(grid.shape, dtype=bool)))
    rho_cp = materials["wood"].volumetric_heat_capacity
    with g.writing(writer=None):
        n = physics.Physics(g, (heat.HEAT, law)).run(6.0, refine=4, exposure=NO_SOURCES)
    assert n == 4
    assert (g.material == AIR_ID).all()  # the edit really landed after the first substep
    expected = 20.0 + p_w * 1.5 / (rho_cp * g.cell_volume_m3)
    assert g.temperature[0, 0, 0] == pytest.approx(expected, rel=1e-9)


@pytest.mark.parametrize("refine", [0, -1])
def test_the_fixed_step_refuses_a_refinement_below_one(refine):
    with pytest.raises(ValueError, match="refine must be at least 1"):
        substep_loop(1.0, refine, lambda: 1.0, lambda dt, refresh: False)


def test_the_fixed_step_is_refine_times_stabilitys_count():
    """sim_core.md §8: n = refine * max(1, ceil(P / bound)), dt = P / n, with no floor beyond refine."""
    seen: list[float] = []

    def record(dt: float, refresh: bool) -> bool:
        seen.append(dt)
        return False

    assert substep_loop(1.0, 3, lambda: 0.4, record) == 9
    assert seen == [1.0 / 9] * 9
    assert substep_loop(1.0, 1, lambda: 10.0, lambda dt, refresh: False) == 1  # a long bound: one substep, not a floor


def test_a_replan_takes_the_rest_from_counts_not_from_a_running_sum():
    """sim_core.md §8: the rest of a replanned step is ``(planned - taken) * dt``. On 0.5 s in 10 substeps, the 9th
    edits the world and the new bound is a tenth of the last substep: from counts the rest is exactly 10 substeps.
    From ``seconds - elapsed`` (nine float additions of 0.05 fall short of 0.45 by rounding) the rest divided by
    the bound is 10.000000000000009, whose ceiling is 11, so the step took 11 even substeps for the rest, 20 in all.
    Proved by planting that sum in ``substep_loop``: this went red (20 substeps) and every other test stayed green."""
    seconds, dt = 0.5, 0.5 / 10
    limit = (10 - 9) * dt / 10
    seen: list[float] = []

    def bound() -> float:
        return 0.055 if len(seen) < 9 else limit  # ceil(0.5 / 0.055) is 10 substeps of 0.05 s

    def once(step: float, refresh: bool) -> bool:
        seen.append(step)
        return len(seen) == 9  # the 9th substep edits the world, so the bound is rechecked

    assert substep_loop(seconds, 1, bound, once) == 9 + 10
    assert seen[:9] == [dt] * 9
    assert seen[9:] == [(10 - 9) * dt / 10] * 10


@pytest.mark.parametrize("refine", [1, 2, 4])
def test_a_replan_keeps_each_substep_within_the_bound_over_refine(refine):
    """sim_core.md §8: after an edit tightens the bound, every later substep is at most bound / refine, so a refined
    run stays a refinement of a stable step. PR 3 review N3: the trigger compared the bound with the refined dt, so a
    bound between the refined dt and the step refine divides replanned refine 1 but not refine 4, whose remaining
    substeps were then 1.7 times bound / 4. Proved by restoring ``limit < dt``: refine 2 and 4 went red."""
    bounds = iter([0.5, 0.3])  # a 1 s step at a 0.5 s bound; the first substep's edit tightens it to 0.3 s
    seen: list[float] = []

    def step_once(dt: float, refresh: bool) -> bool:
        seen.append(dt)
        return len(seen) == 1

    substep_loop(1.0, refine, lambda: next(bounds), step_once)
    assert all(dt <= 0.3 / refine for dt in seen[1:]), seen
