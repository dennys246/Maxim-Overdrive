"""Heat conduction against a closed-form solution, plus conservation and convergence.

The laws write the cells only inside the grid's write window (boundaries §4.1), so each test opens it, as
``World.advance`` does on the shipped path.
"""

import math

import numpy as np
import pytest

from simcore.core import heat
from simcore.core.grid import MaterialGrid
from simcore.core.materials import AIR_ID
from simcore.core.scene import Box, Scene
from simcore.verify import Run, Work, converges

SIGMA0, T_S = 0.3, 3600.0


def _bar(dx_m, materials):
    g = Scene((4.0, 0.2, 0.2), (Box((0, 0, 0), (4, 0.2, 0.2), "steel"),)).build(materials, dx_m=dx_m)
    x = g.centers(0)[:, None, None]
    with g.writing():
        g.temperature[:] = 20 + 100 * np.exp(-((x - 2) ** 2) / (2 * SIGMA0**2))
    return g, x


def _error(dx_m, materials):
    g, x = _bar(dx_m, materials)
    with g.writing():
        heat.step(g, T_S, heat.min_substeps(dx_m))
    s2 = SIGMA0**2 + 2 * materials["steel"].diffusivity_m2_s * T_S
    exact = 20 + 100 * SIGMA0 / np.sqrt(s2) * np.exp(-((x - 2) ** 2) / (2 * s2))
    return float(np.abs(g.temperature - exact).max() / (exact.max() - 20))


def test_gaussian_spreads_as_the_heat_equation_says(dx_m, materials):
    assert _error(dx_m, materials) < 0.02


def _gaussian(dx_m, materials, substeps):
    """The bar after T_S seconds in exactly ``substeps`` steps: its closed-form error, its peak, and the work."""
    g, x = _bar(dx_m, materials)
    with g.writing():
        taken = heat.step(g, T_S, substeps)
    assert taken == substeps  # the study's step, not stability's or the floor's, set the count
    s2 = SIGMA0**2 + 2 * materials["steel"].diffusivity_m2_s * T_S
    exact = 20 + 100 * SIGMA0 / np.sqrt(s2) * np.exp(-((x - 2) ** 2) / (2 * s2))
    error = float(np.abs(g.temperature - exact).max() / (exact.max() - 20))
    return error, float(g.temperature.max()), Work(taken, taken * g.temperature.size)


def _sigma_t(materials):
    return float(np.sqrt(SIGMA0**2 + 2 * materials["steel"].diffusivity_m2_s * T_S))


def _space_study(materials, substeps):
    runs = [Run(dx_m, T_S / substeps, substeps) for dx_m in (0.2, 0.1, 0.05)]

    def error(run):
        e, _, work = _gaussian(run.dx_m, materials, run.steps)
        return e, work

    return converges(error, runs, exact=0.0)


def test_heat_is_second_order_in_space(materials):
    """Finite volumes with harmonic-mean faces are second order in space (world_model E2: space refined alone).

    The bar, set before measuring (verify_harness §5): each observed order is 2 within the next truncation term's
    relative size, (dx_coarse / sigma_t)**2, sigma_t the Gaussian's width at T_S. The step is shared by every grid and
    small enough that time error doesn't enter, which the study shows by passing again at a quarter of the step.
    Measured 2026-11-21: orders 1.93 and 2.03. At the old test's step (stability at 0.05 m, 86 s) they were 3.23 and
    -0.33: time error swamped the fine grids, and the old "fine < coarse / 4" passed by cancellation.
    """
    finest = _bar(0.05, materials)[0]
    base = 64 * math.ceil(T_S / heat.stable_dt(finest))
    for substeps in (base, 4 * base):
        study = _space_study(materials, substeps)
        for p, run in zip(study.orders, study.runs, strict=False):
            assert abs(p - 2) <= (run.dx_m / _sigma_t(materials)) ** 2, (substeps, study.orders)


def test_heat_is_first_order_in_time(materials):
    """Explicit Euler is first order in time (world_model E2: time refined alone, at 0.2 m).

    The bar (owner ruling (a), 2026-11-21): each Richardson order is 1 within lambda * dt_coarse, lambda =
    alpha / sigma0**2, the initial Gaussian's decay rate, which generates most of the time error. Disclosed: this
    decay rate was chosen after measuring. The bar written first used sigma_t, the width at T_S, and both orders
    (1.116, 1.060) missed it (tolerances 0.085, 0.042); the owner ruled the sigma0 derivation correct.
    """
    dx_m = 0.2
    base = math.ceil(T_S / heat.stable_dt(_bar(dx_m, materials)[0]))
    runs = [Run(dx_m, T_S / (base * k), base * k) for k in (1, 2, 4, 8)]
    decay_rate = materials["steel"].diffusivity_m2_s / SIGMA0**2

    def peak(run):
        _, value, work = _gaussian(run.dx_m, materials, run.steps)
        return value, work

    study = converges(peak, runs, order_tol=decay_rate * runs[-2].dt_s)
    assert len(study.orders) == 2
    for p, run in zip(study.orders, study.runs, strict=False):
        assert abs(p - 1) <= decay_rate * run.dt_s, study.orders


def test_a_step_takes_exactly_the_substeps_it_plans_however_many(materials):
    """Red first: an end test of elapsed < seconds - 1e-12 on a running float sum took 8,001 substeps when asked for
    8,000 of 0.45 s, a sliver from rounding that grows with the count (found by step 4's space study)."""
    g, _ = _bar(0.2, materials)
    for substeps in (4, 8_000, 20_000):
        with g.writing():
            assert heat.step(g, T_S, substeps) == substeps


def test_a_step_replans_at_the_shorter_step_when_a_change_tightens_stability(materials):
    """When on_substep changes cells so stability needs a shorter step (wood becoming steel, about 100x more
    diffusive), the rest of the call is replanned at the new bound instead of overrunning it."""
    g = MaterialGrid.empty((0.6, 0.6, 0.6), materials, dx_m=0.2)
    with g.writing():
        g.paint(np.ones(g.shape, dtype=bool), "wood")
        g.temperature[:] = np.random.default_rng(1).uniform(0, 100, g.shape)
    seconds = 2 * heat.stable_dt(g)  # two planned substeps at wood's step
    turned: list[float] = []

    def to_steel(grid, dt):
        if turned:
            return 0
        turned.append(dt)
        grid.paint(np.ones(grid.shape, dtype=bool), "steel")
        return 1

    with g.writing():
        taken = heat.step(g, seconds, 2, on_substep=to_steel)
    steel_dt = heat.stable_dt(g)
    assert steel_dt < turned[0]  # the change really tightened stability below the planned step
    assert taken == 1 + math.ceil((seconds - turned[0]) / steel_dt)
    assert np.isfinite(g.temperature).all()
    assert g.temperature.min() >= 0.0  # stable: no overshoot past the initial bounds
    assert g.temperature.max() <= 100.0


def test_insulated_world_conserves_heat(dx_m, materials):
    g = Scene(
        (1.2, 1.2, 1.2), (Box((0, 0, 0), (1.2, 1.2, 0.6), "concrete"), Box((0, 0, 0.6), (1.2, 1.2, 1.2), "steel"))
    ).build(materials, dx_m=dx_m)
    with g.writing():
        g.temperature[:] = np.random.default_rng(0).uniform(0, 500, g.shape)
    before = heat.heat_energy_j(g)
    with g.writing():
        heat.step(g, 3600.0, heat.min_substeps(dx_m))
    assert abs(heat.heat_energy_j(g) - before) / before < 1e-9


def test_step_never_exceeds_the_stability_bound(materials):
    dx_m = 0.2
    g = Scene((1.0, 1.0, 1.0), (Box((0, 0, 0), (1, 1, 1), "steel"),)).build(materials, dx_m=dx_m)
    with g.writing():
        g.temperature[2, 2, 2] = 1000.0
    with g.writing():
        n = heat.step(g, 10 * 3600.0, min_substeps=1)
    assert n >= 10 * 3600.0 / heat.stable_dt(g)
    assert np.isfinite(g.temperature).all()
    assert np.max(g.temperature) <= 1000.0 + 1e-6


def test_a_cell_destroyed_mid_turn_gets_no_more_source_power(dx_m, materials):
    """Closed form: one wood cell, constant power on solids, destroyed after the first substep.

    It gains exactly one substep's energy at wood's heat capacity. Depositing the turn's power into it after it has
    become air (1/1000 of wood's rho*cp) is what drove burning crates to tens of thousands of degrees.
    """
    g = MaterialGrid.empty((dx_m,) * 3, materials, dx_m=dx_m)
    with g.writing():
        g.paint(np.ones(g.shape, dtype=bool), "wood")
    p_w = 1000.0

    def power():
        return p_w * g.solid.astype(np.float64)

    def destroy_once(grid, dt):
        if (grid.material != AIR_ID).any():
            return grid.destroy(np.ones(grid.shape, dtype=bool))
        return 0

    rho_cp = materials["wood"].volumetric_heat_capacity
    with g.writing():
        n = heat.step(g, 6.0, min_substeps=4, power=power, on_substep=destroy_once)
    assert n == 4
    expected = 20.0 + p_w * 1.5 / (rho_cp * g.cell_volume_m3)
    assert g.temperature[0, 0, 0] == pytest.approx(expected, rel=1e-9)


def test_the_substep_floor_follows_the_grid_spacing_as_the_rig_profiles_did():
    """Resolution left the rig (D20) without changing a result: the floor at today's spacings is exactly what the
    retired rig profiles carried (laptop 4, rig 16, max 64), and it grows as 1/dx^2, never below one substep."""
    assert [heat.min_substeps(dx) for dx in (0.2, 0.1, 0.05)] == [4, 16, 64]
    assert heat.min_substeps(0.16) == 7  # 6.25 rounds up: the floor is a bound, never rounded down
    assert heat.min_substeps(0.4) == 1
    assert heat.min_substeps(10.0) == 1
