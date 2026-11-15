"""Imagined objects pass the world's rules, then become ordinary cells."""

from typing import Any

import numpy as np
import pytest

from maxim_overdrive import Box, Scene
from maxim_overdrive.imagination.spec import Budget, SpecRejected, place
from maxim_overdrive.world import damage

CRATE: dict[str, Any] = {
    "name": "imagined_crate",
    "primitives": [{"kind": "box", "min_m": [0, 0, 0], "max_m": [0.6, 0.6, 0.6], "material": "wood"}],
}


def _grid(rig, materials):
    return Scene((3.0, 3.0, 2.0), (Box((0, 0, 0), (0.6, 3.0, 2.0), "concrete", "wall"),)).build(rig, materials)


def test_an_imagined_crate_is_destructible_like_any_other(rig, materials):
    g = _grid(rig, materials)
    mass = place(g, CRATE, (1.2, 1.2, 0.0))
    assert mass == pytest.approx(0.216 * 600)  # from authored geometry, the same at every rig
    assert g.volume_m3(g.regions["imagined_crate"]) == pytest.approx(0.216, rel=1e-6)
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
        (CRATE, (0.0, 0.0, 0.0), "occupied"),
        (
            {**CRATE, "primitives": [{**CRATE["primitives"][0], "max_m": [2.0, 2.0, 2.0], "material": "steel"}]},
            (0.8, 0.8, 0),
            "too",
        ),
        ({"name": "nothing", "primitives": []}, (1.2, 1.2, 0), "at least one"),
        ({**CRATE, "name": ""}, (1.2, 1.2, 0), "needs a name"),
        ({**CRATE, "name": 7}, (1.2, 1.2, 0), "needs a name"),
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
            "malformed.*positive radius",
        ),
    ],
)
def test_the_world_refuses_impossible_objects(rig, materials, spec, origin, reason):
    g = _grid(rig, materials)
    before = g.material.copy()
    with pytest.raises(SpecRejected, match=reason):
        place(g, spec, origin, Budget(max_mass_kg=500, max_extent_m=1.5))
    assert (g.material == before).all()


def test_an_imagined_cylinder_lands_where_it_was_placed(rig, materials):
    g = _grid(rig, materials)
    barrel = {
        "name": "barrel",
        "primitives": [
            {"kind": "cylinder", "center_xy_m": [0.0, 0.0], "radius_m": 0.3, "z_m": [0.0, 0.8], "material": "wood"}
        ],
    }
    mass = place(g, barrel, (2.0, 2.0, 0.0))
    assert mass == pytest.approx(np.pi * 0.3**2 * 0.8 * g.materials["wood"].density_kg_m3)
    idx = np.argwhere(g.regions["barrel"])
    centre_m = (idx.mean(axis=0) + 0.5) * g.dx
    assert centre_m[:2] == pytest.approx([2.0, 2.0], abs=g.dx / 2)  # offset by the origin, not left at (0, 0)
