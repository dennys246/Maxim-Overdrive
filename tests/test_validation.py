"""Every input the world server refuses, it refuses loudly, and the error says what was wrong.

These are the edges of config, grid, scene, damage, heat and the SEM bridge. Each rejection is a promise to the
author of a data file or to a caller, so each is tested.
"""

from __future__ import annotations

import dataclasses
import math

import numpy as np
import pytest

from maxim_overdrive import Box, MaterialTable, RigProfile, Scene, World
from maxim_overdrive.config import ActionLimits
from maxim_overdrive.imagination.spec import Budget, SpecRejected, place
from maxim_overdrive.sem_env import bridge
from maxim_overdrive.world import damage, heat
from maxim_overdrive.world.grid import MaterialGrid
from maxim_overdrive.world.world import HeatSource

# -- config ---------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"cell_size_m": 0.0}, "cell_size_m must be positive"),
        ({"cell_size_m": -0.1}, "cell_size_m must be positive"),
        ({"cell_size_m": math.nan}, "cell_size_m must be positive"),
        ({"min_substeps_per_turn": 0}, "at least 1"),
    ],
)
def test_a_rig_profile_refuses_impossible_values(changes, message):
    good = RigProfile.load("laptop")
    with pytest.raises(ValueError, match=message):
        dataclasses.replace(good, **changes)


def _table_with(materials, **changes_by_name):
    mats = dict(materials.by_name)
    for name, changes in changes_by_name.items():
        mats[name] = dataclasses.replace(mats[name], **changes)
    return mats


def test_the_material_table_refuses_duplicate_ids(materials):
    mats = _table_with(materials, wood={"id": materials["concrete"].id})
    with pytest.raises(ValueError, match="unique"):
        MaterialTable(mats)


def test_the_material_table_requires_air_at_id_zero(materials):
    mats = dict(materials.by_name)
    del mats["air"]
    with pytest.raises(ValueError, match="'air' with id 0"):
        MaterialTable(mats)


def test_material_ids_must_fit_a_byte(materials):
    with pytest.raises(ValueError, match="uint8"):
        MaterialTable(_table_with(materials, wood={"id": 256}))


# -- grid and scene -------------------------------------------------------------------------------------------------


def test_extents_must_be_whole_cells_at_every_rig(materials):
    with pytest.raises(ValueError, match="whole number"):
        MaterialGrid.empty((1.05, 1.0, 1.0), RigProfile.load("laptop"), materials)


def test_a_point_outside_the_grid_has_no_cell(rig, materials):
    g = MaterialGrid.empty((1.0, 1.0, 1.0), rig, materials)
    assert g.cell_of((0.0, 0.0, 0.0)) == (0, 0, 0)
    for point in [(-0.01, 0.5, 0.5), (0.5, 1.0, 0.5), (0.5, 0.5, 7.0)]:
        with pytest.raises(ValueError, match="outside the grid"):
            g.cell_of(point)


def test_region_names_are_unique(rig, materials):
    g = MaterialGrid.empty((1.0, 1.0, 1.0), rig, materials)
    x, _, _ = g.mesh()
    g.paint(np.broadcast_to(x < 0.5, g.shape), "wood", region="crate")
    with pytest.raises(ValueError, match="already exists"):
        g.paint(np.broadcast_to(x >= 0.5, g.shape), "wood", region="crate")


def test_a_scene_refuses_unknown_materials(rig, materials):
    scene = Scene((1.0, 1.0, 1.0), (Box((0, 0, 0), (0.4, 0.4, 0.4), "adamantium", "thing"),))
    with pytest.raises(ValueError, match="unknown material 'adamantium' in primitive thing"):
        scene.build(rig, materials)


@pytest.mark.parametrize("raw", [["not", "a", "scene"], "scene", None, 3])
def test_a_scene_must_be_a_mapping(raw):
    with pytest.raises(ValueError, match="a scene must be a mapping"):
        Scene.from_dict(raw)


def test_a_scene_refuses_unknown_primitive_kinds():
    with pytest.raises(ValueError, match="unknown primitive kind 'torus'"):
        Scene.from_dict({"extent_m": [1, 1, 1], "primitives": [{"kind": "torus", "material": "wood"}]})


# -- heat, damage, world ----------------------------------------------------------------------------------------------


def test_no_time_means_no_substeps_and_no_change(rig, materials):
    g = MaterialGrid.empty((1.0, 1.0, 1.0), rig, materials)
    g.temperature[0, 0, 0] = 500.0
    before = g.temperature.copy()
    assert heat.step(g, 0.0) == 0
    assert heat.step(g, -5.0) == 0
    assert np.array_equal(g.temperature, before)


@pytest.mark.parametrize(("energy_j", "sigma_m"), [(-1.0, 0.2), (1.0, 0.0), (1.0, -0.2)])
def test_a_strike_refuses_negative_energy_and_non_positive_width(rig, materials, energy_j, sigma_m):
    g = MaterialGrid.empty((1.0, 1.0, 1.0), rig, materials)
    with pytest.raises(ValueError, match="non-negative"):
        damage.strike(g, (0.5, 0.5, 0.5), energy_j, sigma_m)


def test_a_region_with_no_solid_cells_cannot_be_breached(rig, materials):
    g = MaterialGrid.empty((1.0, 1.0, 1.0), rig, materials)
    x, _, _ = g.mesh()
    g.paint(np.broadcast_to(x < 0.5, g.shape), "air", region="doorway")
    assert damage.region_breached(g, "doorway") is False


def test_a_world_with_no_fire_stays_at_ambient(rig, materials):
    w = World.from_scene(Scene((1.0, 1.0, 1.0), (Box((0, 0, 0), (0.4, 1, 1), "concrete", "wall"),)), rig, materials)
    w.advance()
    assert np.allclose(w.grid.temperature, 20.0)
    assert w.turn == 1


def test_a_source_smaller_than_a_cell_still_delivers_its_full_power(rig, materials):
    w = World.from_scene(Scene((1.0, 1.0, 1.0)), rig, materials)  # all air: the fire has no solid to sit on
    w.sources["spark"] = HeatSource((0.5, 0.5, 0.5), radius_m=1e-4, power_w=100.0)
    power = w._power_field()
    assert power is not None
    assert power.sum() == pytest.approx(100.0)
    assert power[w.grid.cell_of((0.5, 0.5, 0.5))] == pytest.approx(100.0)


# -- SEM bridge -------------------------------------------------------------------------------------------------------


def _world(rig, materials):
    return World.from_scene(
        Scene((2.0, 2.0, 2.0), (Box((0.8, 0, 0), (1.2, 2, 2), "concrete", "wall"),)), rig, materials
    )


def test_sensors_and_modulators_refuse_unknown_names(rig, materials):
    w = _world(rig, materials)
    with pytest.raises(ValueError, match="unknown region quantity 'colour'"):
        bridge.RegionSensor(w, "wall", "colour")
    with pytest.raises(KeyError, match="no region 'door'"):
        bridge.RegionSensor(w, "door", "integrity")
    with pytest.raises(KeyError, match="no region 'door'"):
        bridge.StructureModulator(w, "door", limits=ActionLimits.load())


def test_every_sensor_reports_its_schema_and_unit(rig, materials):
    sensors, _ = bridge.region_parts(_world(rig, materials), "wall", limits=ActionLimits.load())
    assert sensors["integrity"].reading_schema == {"type": "float", "range": [0.0, 1.0]}
    assert sensors["breached"].reading_schema == {"type": "float", "range": [0.0, 1.0]}
    assert sensors["temperature_max"].reading_schema == {"type": "float", "range": [-273.0, 6000.0]}
    assert {s.name: s.unit for s in sensors.values()} == {
        "integrity": "ratio",
        "temperature_max": "celsius",
        "temperature_mean": "celsius",
        "breached": "bool",
    }
    assert sensors["temperature_mean"].value() == pytest.approx(20.0)


def test_a_region_that_lost_all_its_cells_reads_nan_and_cannot_burn(rig, materials):
    w = _world(rig, materials)
    sensors, mods = bridge.region_parts(w, "wall", limits=ActionLimits.load())
    w.grid.regions["wall"][:] = False  # a later paint took every cell
    assert math.isnan(sensors["temperature_max"].value())
    res = mods["structure"].execute("ignite", {"power_w": 1000.0})
    assert not res.success
    assert res.error == "ValueError: region 'wall' has no cells"
    assert "fire:wall" not in w.sources


def test_an_imagined_object_over_its_mass_budget_is_refused(rig, materials):
    g = Scene((3.0, 3.0, 2.0)).build(rig, materials)
    crate = {"name": "c", "primitives": [{"min_m": [0, 0, 0], "max_m": [0.6, 0.6, 0.6], "material": "wood"}]}
    with pytest.raises(SpecRejected, match="too heavy: 130 kg, the limit is 100 kg"):
        place(g, crate, (1.0, 1.0, 0.0), Budget(max_mass_kg=100.0))
    assert "c" not in g.regions


def test_a_rig_loads_by_name_or_by_path(tmp_path):
    custom = tmp_path / "tiny.yaml"
    custom.write_text("name: tiny\ncell_size_m: 0.25\nmin_substeps_per_turn: 2\nfull_res_radius_m: 4.0\n")
    assert RigProfile.load(custom) == RigProfile("tiny", 0.25, 2, 4.0)
    assert RigProfile.load("rig").cell_size_m == 0.1
    with pytest.raises(FileNotFoundError):
        RigProfile.load("no_such_rig")
