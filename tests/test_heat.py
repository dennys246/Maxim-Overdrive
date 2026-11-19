"""Heat conduction against a closed-form solution, plus conservation and convergence."""

import numpy as np
import pytest

from maxim_overdrive import Box, RigProfile, Scene
from maxim_overdrive.config import AIR_ID
from maxim_overdrive.world import heat
from maxim_overdrive.world.grid import MaterialGrid

SIGMA0, T_S = 0.3, 3600.0


def _bar(rig, materials):
    g = Scene((4.0, 0.2, 0.2), (Box((0, 0, 0), (4, 0.2, 0.2), "steel"),)).build(rig, materials)
    x = g.centers(0)[:, None, None]
    g.temperature[:] = 20 + 100 * np.exp(-((x - 2) ** 2) / (2 * SIGMA0**2))
    return g, x


def _error(rig, materials):
    g, x = _bar(rig, materials)
    heat.step(g, T_S, rig.min_substeps_per_turn)
    s2 = SIGMA0**2 + 2 * materials["steel"].diffusivity_m2_s * T_S
    exact = 20 + 100 * SIGMA0 / np.sqrt(s2) * np.exp(-((x - 2) ** 2) / (2 * s2))
    return float(np.abs(g.temperature - exact).max() / (exact.max() - 20))


def test_gaussian_spreads_as_the_heat_equation_says(rig, materials):
    assert _error(rig, materials) < 0.02


def test_error_falls_with_resolution(materials):
    coarse, fine = (_error(RigProfile.load(t), materials) for t in ("laptop", "rig"))
    assert fine < coarse / 4  # second order in space: halving the cell should cut error about 4x


def test_insulated_world_conserves_heat(rig, materials):
    g = Scene(
        (1.2, 1.2, 1.2), (Box((0, 0, 0), (1.2, 1.2, 0.6), "concrete"), Box((0, 0, 0.6), (1.2, 1.2, 1.2), "steel"))
    ).build(rig, materials)
    g.temperature[:] = np.random.default_rng(0).uniform(0, 500, g.shape)
    before = heat.heat_energy_j(g)
    heat.step(g, 3600.0, rig.min_substeps_per_turn)
    assert abs(heat.heat_energy_j(g) - before) / before < 1e-9


def test_step_never_exceeds_the_stability_bound(materials):
    rig = RigProfile.load("laptop")
    g = Scene((1.0, 1.0, 1.0), (Box((0, 0, 0), (1, 1, 1), "steel"),)).build(rig, materials)
    g.temperature[2, 2, 2] = 1000.0
    n = heat.step(g, 10 * 3600.0, min_substeps=1)
    assert n >= 10 * 3600.0 / heat.stable_dt(g)
    assert np.isfinite(g.temperature).all()
    assert np.max(g.temperature) <= 1000.0 + 1e-6


def test_a_cell_destroyed_mid_turn_gets_no_more_source_power(rig, materials):
    """Closed form: one wood cell, constant power on solids, destroyed after the first substep.

    It gains exactly one substep's energy at wood's heat capacity. Depositing the turn's power into it after it has
    become air (1/1000 of wood's rho*cp) is what drove burning crates to tens of thousands of degrees.
    """
    g = MaterialGrid.empty((rig.cell_size_m,) * 3, rig, materials)
    g.paint(np.ones(g.shape, dtype=bool), "wood")
    p_w = 1000.0

    def power():
        return p_w * g.solid.astype(np.float64)

    def destroy_once(grid, dt):
        if (grid.material != AIR_ID).any():
            return grid.destroy(np.ones(grid.shape, dtype=bool))
        return 0

    rho_cp = materials["wood"].volumetric_heat_capacity
    n = heat.step(g, 6.0, min_substeps=4, power=power, on_substep=destroy_once)
    assert n == 4
    expected = 20.0 + p_w * 1.5 / (rho_cp * g.cell_volume_m3)
    assert g.temperature[0, 0, 0] == pytest.approx(expected, rel=1e-9)
