"""Imagined objects pass the world's rules, then become ordinary cells."""

import pytest

from maxim_overdrive import Box, Scene
from maxim_overdrive.imagination.spec import Budget, SpecRejected, place
from maxim_overdrive.world import damage

CRATE = {"name": "imagined_crate", "primitives": [{"kind": "box", "min_m": [0, 0, 0], "max_m": [0.6, 0.6, 0.6], "material": "wood"}]}


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
        ({**CRATE, "primitives": [{**CRATE["primitives"][0], "material": "unobtainium"}]}, (1.2, 1.2, 0), "not a material"),
        (CRATE, (0.0, 0.0, 0.0), "occupied"),
        ({**CRATE, "primitives": [{**CRATE["primitives"][0], "max_m": [2.0, 2.0, 2.0], "material": "steel"}]}, (0.8, 0.8, 0), "too"),
        ({"name": "nothing", "primitives": []}, (1.2, 1.2, 0), "at least one"),
    ],
)
def test_the_world_refuses_impossible_objects(rig, materials, spec, origin, reason):
    g = _grid(rig, materials)
    before = g.material.copy()
    with pytest.raises(SpecRejected, match=reason):
        place(g, spec, origin, Budget(max_mass_kg=500, max_extent_m=1.5))
    assert (g.material == before).all()
