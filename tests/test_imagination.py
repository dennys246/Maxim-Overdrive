"""Imagined objects pass the world's rules, then become ordinary cells."""

from typing import Any

import numpy as np
import pytest

from simcore.core import damage
from simcore.core.imagination import Budget, SpecRejected, place
from simcore.core.scene import Box, Scene

CRATE: dict[str, Any] = {
    "name": "imagined_crate",
    "primitives": [{"kind": "box", "min_m": [0, 0, 0], "max_m": [0.6, 0.6, 0.6], "material": "wood"}],
}


def _grid(dx_m, materials):
    return Scene((3.0, 3.0, 2.0), (Box((0, 0, 0), (0.6, 3.0, 2.0), "concrete", "wall"),)).build(materials, dx_m=dx_m)


def test_an_imagined_crate_is_destructible_like_any_other(dx_m, materials):
    g = _grid(dx_m, materials)
    mass = place(g, CRATE, (1.2, 1.2, 0.0))
    assert mass == pytest.approx(0.216 * 600)  # from authored geometry, the same at every rig
    assert g.volume_m3(g.regions["imagined_crate"].cells) == pytest.approx(0.216, rel=1e-6)
    with g.writing():
        damage.strike(g, (1.5, 1.5, 0.3), 5.0e6, 0.3)
    assert damage.region_integrity(g, "imagined_crate") < 1.0


@pytest.mark.parametrize(
    ("spec", "origin", "reason"),
    [
        (
            {**CRATE, "primitives": [{**CRATE["primitives"][0], "material": "unobtainium"}]},
            (1.2, 1.2, 0),
            "not a material",
        ),
        (CRATE, (0.0, 0.0, 0.0), "belongs to 'wall'"),  # judged from footprints before any cell is read
        (
            {**CRATE, "primitives": [{**CRATE["primitives"][0], "max_m": [2.0, 2.0, 2.0], "material": "steel"}]},
            (0.8, 0.8, 0),
            "too",
        ),
        ({"name": "nothing", "primitives": []}, (1.2, 1.2, 0), "at least one"),
        ({**CRATE, "name": ""}, (1.2, 1.2, 0), "needs a name"),
        ({**CRATE, "name": 7}, (1.2, 1.2, 0), "needs a name"),
        ({**CRATE, "name": " box"}, (1.2, 1.2, 0), "no outer spaces"),
        ({**CRATE, "name": "box "}, (1.2, 1.2, 0), "no outer spaces"),
        ({**CRATE, "name": "  "}, (1.2, 1.2, 0), "no outer spaces"),
        ({**CRATE, "name": "\tbox"}, (1.2, 1.2, 0), "no outer spaces"),
        ({**CRATE, "name": "wall"}, (1.2, 1.2, 0), "already exists"),
        (
            {**CRATE, "primitives": [{"kind": "box", "min_m": [0, 0, 0], "material": "wood"}]},
            (1.2, 1.2, 0),
            "malformed",
        ),
        ({**CRATE, "primitives": [{"kind": "torus", "material": "wood"}]}, (1.2, 1.2, 0), "malformed"),
        ({**CRATE, "primitives": [{**CRATE["primitives"][0], "material": "air"}]}, (1.2, 1.2, 0), "air"),
        (
            {**CRATE, "primitives": [{**CRATE["primitives"][0], "max_m": [0.01, 0.01, 0.01]}]},
            (1.21, 1.21, 0.01),
            "smaller than one cell",
        ),
        (CRATE, (10.0, 10.0, 0.0), "smaller than one cell|outside"),
        (
            {**CRATE, "primitives": [{**CRATE["primitives"][0], "min_m": [0, 0, 0, 0]}]},
            (1.2, 1.2, 0),
            "malformed",
        ),  # 4 numbers
        (
            {**CRATE, "primitives": [{**CRATE["primitives"][0], "min_m": [0, 0]}]},
            (1.2, 1.2, 0),
            "malformed",
        ),  # 2 numbers
        (
            {**CRATE, "primitives": [{**CRATE["primitives"][0], "min_m": [0, 0, "a"]}]},
            (1.2, 1.2, 0),
            "malformed",
        ),  # "a"
        (
            {**CRATE, "primitives": [{**CRATE["primitives"][0], "min_m": [0, 0, float("nan")]}]},
            (1.2, 1.2, 0),
            "malformed",
        ),  # nan
        (
            {**CRATE, "primitives": [{**CRATE["primitives"][0], "min_m": [0, True, 0]}]},
            (1.2, 1.2, 0),
            "malformed",
        ),  # True
        ({**CRATE, "primitives": [{**CRATE["primitives"][0], "min_m": "000"}]}, (1.2, 1.2, 0), "malformed"),  # 000
        (
            {**CRATE, "primitives": [{**CRATE["primitives"][0], "min_m": [0.6, 0, 0]}]},
            (1.2, 1.2, 0),
            "malformed",
        ),  # exceed
        (
            {**CRATE, "primitives": [{**CRATE["primitives"][0], "material": 7}]},
            (1.2, 1.2, 0),
            "malformed",
        ),  # material name
        (
            {
                **CRATE,
                "primitives": [
                    {"kind": "cylinder", "center_xy_m": [0, 0], "radius_m": -0.2, "z_m": [0, 1], "material": "wood"}
                ],
            },
            (1.2, 1.2, 0),
            "malformed.*radius_m must be above 0",
        ),
        # Shapes an LLM can produce that are not numbers, lists or mappings where they should be.
        ({**CRATE, "primitives": [{**CRATE["primitives"][0], "min_m": [0, 0, 10**400]}]}, (1.2, 1.2, 0), "malformed"),
        (
            {
                **CRATE,
                "primitives": [
                    {"kind": "cylinder", "center_xy_m": [0, 0], "radius_m": 10**400, "z_m": [0, 1], "material": "wood"}
                ],
            },
            (1.2, 1.2, 0),
            "malformed",
        ),
        ({**CRATE, "primitives": "box"}, (1.2, 1.2, 0), "malformed.*must be a list"),
        ({**CRATE, "primitives": {"a": 1}}, (1.2, 1.2, 0), "malformed.*must be a list"),
        ({**CRATE, "primitives": ["box"]}, (1.2, 1.2, 0), "malformed.*must be a mapping"),
        ({**CRATE, "primitives": [{**CRATE["primitives"][0], "name": ["x"]}]}, (1.2, 1.2, 0), "malformed.*name"),
        (CRATE, (float("nan"), 0.0, 0.0), "malformed.*origin_m"),
        (CRATE, (float("inf"), 0.0, 0.0), "malformed.*origin_m"),
        (CRATE, (1e308, 0.0, 0.0), "malformed"),  # adding the offset collapses the box
        (CRATE, (1.2, 1.2), "malformed.*origin_m"),
        (CRATE, "abc", "malformed.*origin_m"),
        (["not", "a", "spec"], (1.2, 1.2, 0), "must be a mapping"),
        (
            {**CRATE, "primitives": [{**CRATE["primitives"][0], "max_m": [1e308, 1e308, 1e308]}]},
            (1.2, 1.2, 0),
            "too large|too heavy|within 1000 of 0",
        ),
    ],
)
def test_the_world_refuses_impossible_objects(dx_m, materials, spec, origin, reason):
    g = _grid(dx_m, materials)
    before = g.material.copy()
    with pytest.raises(SpecRejected, match=reason):
        place(g, spec, origin, Budget(max_mass_kg=500, max_extent_m=1.5))
    assert (g.material == before).all()


def test_an_imagined_cylinder_lands_where_it_was_placed(dx_m, materials):
    g = _grid(dx_m, materials)
    barrel = {
        "name": "barrel",
        "primitives": [
            {"kind": "cylinder", "center_xy_m": [0.0, 0.0], "radius_m": 0.3, "z_m": [0.0, 0.8], "material": "wood"}
        ],
    }
    mass = place(g, barrel, (2.0, 2.0, 0.0))
    assert mass == pytest.approx(np.pi * 0.3**2 * 0.8 * g.materials["wood"].density_kg_m3)
    idx = np.argwhere(g.regions["barrel"].cells)
    centre_m = (idx.mean(axis=0) + 0.5) * g.dx
    assert centre_m[:2] == pytest.approx([2.0, 2.0], abs=g.dx / 2)  # offset by the origin, not left at (0, 0)


def test_numpy_scalars_are_numbers(dx_m, materials):
    g = _grid(dx_m, materials)
    crate = {**CRATE, "primitives": [{**CRATE["primitives"][0], "max_m": [np.int64(1), np.float64(0.6), 0.6]}]}
    assert place(g, crate, (np.float32(1.2), 1.2, 0)) == pytest.approx(0.36 * 600)


def test_a_space_an_unnamed_solid_fills_is_occupied_and_refusing_it_changes_nothing(dx_m, materials):
    # No footprint claims an unnamed solid, so only the cells can say the space is taken: this refusal comes from
    # inside the write window, which rolls back the primitives already painted.
    slab = Box((1.0, 1.0, 0.0), (2.0, 2.0, 0.4), "concrete")
    g = Scene((3.0, 3.0, 2.0), (slab,)).build(materials, dx_m=dx_m)
    before = g.material.copy()
    above = {"min_m": [0, 0, 1.0], "max_m": [0.4, 0.4, 1.4], "material": "concrete"}  # free: painted first
    two = {"name": "two", "primitives": [above, CRATE["primitives"][0]]}  # the crate's cells are the slab's
    with pytest.raises(SpecRejected, match="occupied"):
        place(g, two, (1.2, 1.2, 0.0))
    assert np.array_equal(g.material, before)
    assert "two" not in g.regions
