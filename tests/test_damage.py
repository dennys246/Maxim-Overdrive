"""Strikes against the closed-form crater; breach and integrity read the same at every rig.

A strike writes the cells, so each test opens the grid's write window, as the applier does on the shipped path.
"""

import math

import pytest

from simcore.core import damage, physics, reductions
from simcore.core.scene import Box, Scene, constructing
from tests._cells import destroy

F_CONCRETE = 2.0e7


def test_crater_matches_closed_form(dx_m, materials):
    g = Scene((2.0, 2.0, 2.0), (Box((0, 0, 0), (2, 2, 2), "concrete"),)).build(materials, dx_m=dx_m)
    with g.writing(writer=None):
        res = physics.strike(g, (1.0, 1.0, 1.0), 3.7e7, 0.15)
    r = damage.analytic_crater_radius_m(3.7e7, 0.15, F_CONCRETE)
    assert res.destroyed_volume_m3 == pytest.approx(4 / 3 * math.pi * r**3, rel=0.10)


def test_strike_below_fracture_destroys_nothing(dx_m, materials):
    g = Scene((2.0, 2.0, 2.0), (Box((0, 0, 0), (2, 2, 2), "concrete"),)).build(materials, dx_m=dx_m)
    assert damage.analytic_crater_radius_m(1.0e6, 0.3, F_CONCRETE) == 0.0
    with g.writing(writer=None):
        assert physics.strike(g, (1.0, 1.0, 1.0), 1.0e6, 0.3).destroyed_cells == 0


@pytest.mark.parametrize(("energy", "breached"), [(6.3e7, True), (9.6e6, False)])
def test_breach_is_the_same_outcome_at_every_rig(spacings, materials, energy, breached):
    integrities = []
    for dx_m in spacings:
        g = Scene((2.0, 3.0, 2.4), (Box((0.8, 0, 0), (1.2, 3, 2.4), "concrete", "wall"),)).build(materials, dx_m=dx_m)
        with g.writing(writer=None):
            physics.strike(g, (0.8, 1.5, 1.2), energy, 0.3)  # on the wall's face
        assert reductions.region_breached(g, "wall") is breached, dx_m
        integrities.append(reductions.region_integrity(g, "wall"))
    assert max(integrities) - min(integrities) < 0.01  # the SEM integrity sensor reads the same at every rig


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="region_breached picks its axis from cell extents, so it can change with the spacing: a 0.6 x 0.6 x 0.55 m "
    "box at (0.5, 0.5, 0) tests x at 0.2 m (extents [2, 2, 2], ties to x) and z at 0.1 m ([5, 5, 4]), so a hole "
    "through its thinnest authored axis counts only at the finer rig (docs/architecture.md, Known gaps). The fix is "
    "world_model.md section 1's breach by remaining thickness in metres, at step 8a (phase1/fuel-surface).",
)
def test_a_hole_through_the_thinnest_authored_axis_is_a_breach_at_every_rig(spacings, materials):
    for dx_m in spacings:
        box = Box((0.5, 0.5, 0.0), (1.1, 1.1, 0.55), "wood", "box")  # thinnest authored axis: z
        g = Scene((2.0, 2.0, 2.0), (box,)).build(materials, dx_m=dx_m)
        x, y, _ = g.mesh()
        # A 0.2 m square column in metres, whose faces are cell faces at every spacing, so it holds whole cells.
        column = (x > 0.8) & (x < 1.0) & (y > 0.8) & (y < 1.0) & g.regions["box"].cells
        with constructing(g):
            if destroy(g, column) == 0:  # the precondition raises outside the gate's raises=, so it can't pass as red
                raise RuntimeError(f"no hole was made at {dx_m} m")
        assert reductions.region_breached(g, "box"), dx_m
