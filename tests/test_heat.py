"""Heat conduction against a closed-form solution, plus conservation and convergence."""

import numpy as np

from maxim_overdrive import Box, RigProfile, Scene
from maxim_overdrive.world import heat

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
    assert np.isfinite(g.temperature).all() and g.temperature.max() <= 1000.0 + 1e-6
