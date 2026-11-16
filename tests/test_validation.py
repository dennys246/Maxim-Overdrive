"""Every input the world server refuses, it refuses loudly, and the error says what was wrong.

These are the edges of config, grid, scene, damage, heat and the SEM bridge. Each rejection is a promise to the
author of a data file or to a caller, so each is tested.
"""

from __future__ import annotations

import dataclasses
import math

import numpy as np
import pytest
import yaml

from maxim_overdrive import Box, MaterialTable, RigProfile, Scene, World
from maxim_overdrive.config import ActionLimits, data_dir
from maxim_overdrive.imagination.spec import Budget, SpecRejected, place
from maxim_overdrive.sem_env import bridge
from maxim_overdrive.world import damage, heat
from maxim_overdrive.world.grid import Footprint, MaterialGrid
from maxim_overdrive.world.scene import Cylinder
from maxim_overdrive.world.world import HeatSource

LIMITS = ActionLimits.load()

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
    g.paint(
        np.broadcast_to(x < 0.5, g.shape),
        "wood",
        region="crate",
        footprint=Footprint(((0, 0, 0), (0.5, 1, 1)), (0.25, 0.5, 0.5)),
    )
    with pytest.raises(ValueError, match="already exists"):
        g.paint(
            np.broadcast_to(x >= 0.5, g.shape),
            "wood",
            region="crate",
            footprint=Footprint(((0.5, 0, 0), (1, 1, 1)), (0.25, 0.5, 0.5)),
        )


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
    g.paint(
        np.broadcast_to(x < 0.5, g.shape),
        "air",
        region="doorway",
        footprint=Footprint(((0, 0, 0), (0.5, 1, 1)), (0.25, 0.5, 0.5)),
    )
    assert damage.region_breached(g, "doorway") is False


def test_a_world_with_no_fire_stays_at_ambient(rig, materials):
    w = World.from_scene(
        Scene((1.0, 1.0, 1.0), (Box((0, 0, 0), (0.4, 1, 1), "concrete", "wall"),)),
        rig,
        materials,
        limits=LIMITS,
    )
    w.advance()
    assert np.allclose(w.grid.temperature, 20.0)
    assert w.turn == 1


def test_a_source_smaller_than_a_cell_still_delivers_its_full_power(rig, materials):
    w = World.from_scene(
        Scene((1.0, 1.0, 1.0)), rig, materials, limits=LIMITS
    )  # all air: the fire has no solid to sit on
    w.sources["spark"] = HeatSource((0.5, 0.5, 0.5), radius_m=1e-4, power_w=100.0)
    power = w._power_field()
    assert power is not None
    assert power.sum() == pytest.approx(100.0)
    assert power[w.grid.cell_of((0.5, 0.5, 0.5))] == pytest.approx(100.0)


# -- SEM bridge -------------------------------------------------------------------------------------------------------


def _world(rig, materials):
    return World.from_scene(
        Scene((2.0, 2.0, 2.0), (Box((0.8, 0, 0), (1.2, 2, 2), "concrete", "wall"),)),
        rig,
        materials,
        limits=LIMITS,
    )


def test_sensors_and_modulators_refuse_unknown_names(rig, materials):
    w = _world(rig, materials)
    with pytest.raises(ValueError, match="unknown region quantity 'colour'"):
        bridge.RegionSensor(w, "wall", "colour")
    with pytest.raises(KeyError, match="no region 'door'"):
        bridge.RegionSensor(w, "door", "integrity")
    with pytest.raises(KeyError, match="no region 'door'"):
        bridge.StructureModulator(w, "door")


def test_every_sensor_reports_its_schema_and_unit(rig, materials):
    sensors, _ = bridge.region_parts(_world(rig, materials), "wall")
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
    sensors, mods = bridge.region_parts(w, "wall")
    w.grid.regions["wall"].cells[:] = False  # a later paint took every cell
    assert math.isnan(sensors["temperature_max"].value())
    res = mods["structure"].execute("ignite", {"power_w": 1000.0})
    assert not res.success
    assert res.error == "the wall is gone"
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


# -- every number in a data file is a finite real number, or the loader says which one isn't -------------------------


@pytest.mark.parametrize(
    ("ambient", "message"), [("nan", "finite number"), (".nan", "finite number"), (-300, "absolute zero")]
)
def test_a_scene_refuses_an_impossible_ambient_temperature(ambient, message):
    raw = yaml.safe_load(f"extent_m: [1, 1, 1]\nprimitives: []\nambient_c: {ambient}\n")
    with pytest.raises(ValueError, match=message):
        Scene.from_dict(raw)


@pytest.mark.parametrize(
    ("field", "value"), [("cell_size_m", "'0.1'"), ("cell_size_m", ".inf"), ("full_res_radius_m", "true")]
)
def test_a_rig_file_refuses_a_value_that_is_not_a_finite_number(tmp_path, field, value):
    good = {"name": "t", "cell_size_m": "0.25", "min_substeps_per_turn": "2", "full_res_radius_m": "4.0"}
    good[field] = value
    path = tmp_path / "t.yaml"
    path.write_text("".join(f"{k}: {v}\n" for k, v in good.items()))
    with pytest.raises(ValueError, match=f"{field} must be a finite number"):
        RigProfile.load(path)


@pytest.mark.parametrize(
    "field", ["density_kg_m3", "specific_heat_j_kgk", "conductivity_w_mk", "fracture_energy_j_m3", "degrade_above_c"]
)
def test_a_material_file_refuses_a_value_that_is_not_a_finite_number(tmp_path, field):
    raw = yaml.safe_load((data_dir() / "materials" / "core.yaml").read_text())
    raw["materials"]["wood"][field] = "2.0e7"  # YAML 1.1 reads this as a string
    path = tmp_path / "core.yaml"
    path.write_text(yaml.safe_dump(raw))
    with pytest.raises(ValueError, match=f"wood.{field} must be a finite number"):
        MaterialTable.load(path)


@pytest.mark.parametrize(
    ("extent", "message"),
    [
        ([True, 3, 2], "extent_m must be 3 finite numbers"),
        ([3, 3], "extent_m must be 3 numbers"),
        (["3", 3, 2], "extent_m must be 3 finite numbers"),
        ([math.nan, 3, 2], "extent_m must be 3 finite numbers"),
        ([0, 3, 2], "between 0 and 1000 m on every axis"),
        ([3, 3, 1e6], "between 0 and 1000 m on every axis"),
    ],
)
def test_a_scene_refuses_an_impossible_extent(extent, message):
    with pytest.raises(ValueError, match=message):
        Scene(tuple(extent))


@pytest.mark.parametrize(("ambient", "ok"), [(-273.15, False), (-273.0, True), (3000.0, True), (3000.5, False)])
def test_a_scenes_ambient_bounds_are_exact(ambient, ok):
    if ok:
        given = int(ambient) if ambient.is_integer() else ambient  # an int becomes a float
        assert isinstance(Scene((1.0, 1.0, 1.0), ambient_c=given).ambient_c, float)
    else:
        with pytest.raises(ValueError, match="ambient_c must be above absolute zero"):
            Scene((1.0, 1.0, 1.0), ambient_c=ambient)


@pytest.mark.parametrize("value", ["2.9", "true", "'4'", ".inf"])
def test_a_rig_files_substep_count_must_be_a_whole_number(tmp_path, value):
    path = tmp_path / "t.yaml"
    path.write_text(f"name: t\ncell_size_m: 0.25\nmin_substeps_per_turn: {value}\nfull_res_radius_m: 4.0\n")
    with pytest.raises(ValueError, match="min_substeps_per_turn must be a whole number"):
        RigProfile.load(path)


@pytest.mark.parametrize(("field", "value"), [("id", True), ("id", 2.0), ("color_rgb", [1, 2, "3"])])
def test_a_material_files_whole_numbers_are_whole(tmp_path, field, value):
    raw = yaml.safe_load((data_dir() / "materials" / "core.yaml").read_text())
    raw["materials"]["wood"][field] = value
    path = tmp_path / "core.yaml"
    path.write_text(yaml.safe_dump(raw))
    with pytest.raises(ValueError, match=f"wood.{field} must be a whole number"):
        MaterialTable.load(path)


def test_a_material_files_degrade_rate_must_be_a_number(tmp_path):
    raw = yaml.safe_load((data_dir() / "materials" / "core.yaml").read_text())
    raw["materials"]["wood"]["degrade_rate_per_s_per_100c"] = "0.01"
    path = tmp_path / "core.yaml"
    path.write_text(yaml.safe_dump(raw))
    with pytest.raises(ValueError, match=r"wood\.degrade_rate_per_s_per_100c must be a finite number"):
        MaterialTable.load(path)


def test_a_named_region_needs_its_authored_bounds(rig, materials):
    g = MaterialGrid.empty((1.0, 1.0, 1.0), rig, materials)
    x, _, _ = g.mesh()
    with pytest.raises(ValueError, match="needs its authored footprint"):
        g.paint(np.broadcast_to(x < 0.5, g.shape), "wood", region="crate")
    assert "crate" not in g.regions
    assert (g.material == 0).all()  # refused before anything was painted
    g.paint(
        np.broadcast_to(x < 0.5, g.shape),
        "wood",
        region="crate",
        footprint=Footprint(((0, 0, 0), (0.5, 1, 1)), (0.25, 0.5, 0.5)),
    )
    with pytest.raises(ValueError, match="already exists"):
        g.name_region("crate", np.broadcast_to(x < 0.5, g.shape), Footprint(((0, 0, 0), (0.5, 1, 1)), (0.25, 0.5, 0.5)))
    assert Cylinder((0.5, 0.5), 0.2, (0.0, 1.0), "wood").bounds_m == ((0.3, 0.3, 0.0), (0.7, 0.7, 1.0))


def test_an_imagined_objects_size_budget_is_judged_the_same_at_every_rig(rigs, materials):
    # A 1.5 m slab whose faces sit off the 0.2 m grid: measured from cells it spans 1.6 m at laptop, and was refused
    # there only. Measured from its authored geometry it is 1.5 m at every rig.
    slab = {"name": "slab", "primitives": [{"min_m": [0, 0, 0], "max_m": [1.5, 0.3, 0.3], "material": "wood"}]}
    for rig in rigs:
        g = Scene((4.0, 3.0, 2.0)).build(rig, materials)
        place(g, slab, (1.25, 1.0, 0.0), Budget(max_extent_m=1.5, max_mass_kg=1000.0))
        assert g.regions["slab"].footprint.bounds_m == ((1.25, 1.0, 0.0), (2.75, 1.3, 0.3)), rig.name


def test_a_multi_primitive_objects_footprint_covers_every_primitive(rig, materials):
    spec = {
        "name": "table",
        "primitives": [
            {"min_m": [0, 0, 0.6], "max_m": [1.0, 0.6, 0.7], "material": "wood"},  # the top
            {"kind": "cylinder", "center_xy_m": [0.1, 0.1], "radius_m": 0.05, "z_m": [0, 1.4], "material": "wood"},
        ],
    }
    g = Scene((3.0, 3.0, 2.0)).build(rig, materials)
    place(g, spec, (1.0, 1.0, 0.0), Budget(max_extent_m=1.5, max_mass_kg=1000.0))
    footprint = g.regions["table"].footprint
    low, high = footprint.bounds_m
    assert low == (1.0, 1.0, 0.0)
    assert high == pytest.approx((2.0, 1.6, 1.4))
    with pytest.raises(SpecRejected, match=r"too large: 1\.40 m across"):  # the tallest axis, not the first
        place(g, {**spec, "name": "tall"}, (0.0, 0.0, 0.0), Budget(max_extent_m=1.2, max_mass_kg=1000.0))


def test_a_later_paint_takes_cells_from_earlier_regions_and_a_refused_paint_changes_nothing(rig, materials):
    g = MaterialGrid.empty((1.0, 1.0, 1.0), rig, materials)
    x, _, _ = g.mesh()
    left = np.broadcast_to(x < 0.6, g.shape)
    g.paint(left, "wood", region="left", footprint=Footprint(((0, 0, 0), (0.6, 1, 1)), (0.3, 0.5, 0.5)))
    g.paint(np.broadcast_to(x >= 0.4, g.shape), "concrete")  # unnamed, and it overlaps "left"
    assert not (g.regions["left"].cells & np.broadcast_to(x >= 0.4, g.shape)).any()
    before = g.material.copy()
    with pytest.raises(ValueError, match="already exists"):
        g.paint(np.ones(g.shape, dtype=bool), "steel", region="left", footprint=g.regions["left"].footprint)
    assert np.array_equal(g.material, before)  # refused before anything was painted


@pytest.mark.parametrize(("field", "value"), [("id", -1), ("color_rgb", [1e9, -5, 3]), ("color_rgb", [1, 2])])
def test_a_material_files_ids_and_colours_are_in_range(tmp_path, field, value):
    raw = yaml.safe_load((data_dir() / "materials" / "core.yaml").read_text())
    raw["materials"]["drywall"][field] = value
    path = tmp_path / "core.yaml"
    path.write_text(yaml.safe_dump(raw))
    with pytest.raises(ValueError, match=r"uint8|color_rgb"):
        MaterialTable.load(path)
