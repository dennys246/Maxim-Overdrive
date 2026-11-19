"""Strikes against the closed-form crater; breach and integrity read the same at every rig."""

import math

import pytest

from maxim_overdrive import Box, Scene
from maxim_overdrive.world import damage

F_CONCRETE = 2.0e7


def test_crater_matches_closed_form(rig, materials):
    g = Scene((2.0, 2.0, 2.0), (Box((0, 0, 0), (2, 2, 2), "concrete"),)).build(rig, materials)
    res = damage.strike(g, (1.0, 1.0, 1.0), 3.7e7, 0.15)
    r = damage.analytic_crater_radius_m(3.7e7, 0.15, F_CONCRETE)
    assert res.destroyed_volume_m3 == pytest.approx(4 / 3 * math.pi * r**3, rel=0.10)


def test_strike_below_fracture_destroys_nothing(rig, materials):
    g = Scene((2.0, 2.0, 2.0), (Box((0, 0, 0), (2, 2, 2), "concrete"),)).build(rig, materials)
    assert damage.analytic_crater_radius_m(1.0e6, 0.3, F_CONCRETE) == 0.0
    assert damage.strike(g, (1.0, 1.0, 1.0), 1.0e6, 0.3).destroyed_cells == 0


@pytest.mark.parametrize(("energy", "breached"), [(6.3e7, True), (9.6e6, False)])
def test_breach_is_the_same_outcome_at_every_rig(rigs, materials, energy, breached):
    integrities = []
    for rig in rigs:
        g = Scene((2.0, 3.0, 2.4), (Box((0.8, 0, 0), (1.2, 3, 2.4), "concrete", "wall"),)).build(rig, materials)
        damage.strike(g, (0.8, 1.5, 1.2), energy, 0.3)  # on the wall's face
        assert damage.region_breached(g, "wall") is breached, rig.name
        integrities.append(damage.region_integrity(g, "wall"))
    assert max(integrities) - min(integrities) < 0.01  # the SEM integrity sensor reads the same at every rig
