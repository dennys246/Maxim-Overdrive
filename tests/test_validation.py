"""Every input the world server refuses, it refuses loudly, and the error says what was wrong.

These are the edges of config, grid, scene, damage, heat and the SEM bridge. Each rejection is a promise to the
author of a data file or to a caller, so each is tested.
"""

from __future__ import annotations

import contextlib
import dataclasses
import math

import numpy as np
import pytest
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

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
        g.name_region(
            "crate",
            np.broadcast_to(x < 0.5, g.shape),
            Footprint(((0, 0, 0), (0.5, 1, 1)), (0.25, 0.5, 0.5)),
            solid=True,
        )
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


@pytest.mark.parametrize(
    ("field", "value"), [("id", -1), ("color_rgb", [256, 5, 3]), ("color_rgb", [1, -5, 3]), ("color_rgb", [1, 2])]
)
def test_a_material_files_ids_and_colours_are_in_range(tmp_path, field, value):
    raw = yaml.safe_load((data_dir() / "materials" / "core.yaml").read_text())
    raw["materials"]["drywall"][field] = value
    path = tmp_path / "core.yaml"
    path.write_text(yaml.safe_dump(raw))
    with pytest.raises(ValueError, match=r"uint8|color_rgb"):
        MaterialTable.load(path)


@pytest.mark.parametrize(
    ("primitives", "ok"),
    [
        ((Box((0, 0, 0), (1, 1, 1), "wood", "crate"), Box((0.5, 0, 0), (1.5, 1, 1), "concrete", "wall")), False),
        ((Box((0, 0, 0), (1, 1, 1), "wood", "crate"), Box((0.5, 0, 0), (1.5, 1, 1), "concrete")), False),
        ((Box((0, 0, 0), (1, 1, 1), "concrete", "wall"), Box((0.4, 0, 0), (0.6, 1, 0.8), "air", "doorway")), True),
        ((Box((0, 0, 0), (2, 2, 0.2), "concrete"), Box((0.5, 0.5, 0), (1, 1, 0.6), "wood", "crate")), True),
        ((Box((0, 0, 0), (1, 1, 1), "wood", "crate"), Box((1, 0, 0), (2, 1, 1), "concrete", "wall")), True),  # touching
    ],
    ids=["named-over-named", "unnamed-over-named", "air-carves-named", "named-over-unnamed", "touching"],
)
def test_a_later_solid_may_not_take_space_from_a_named_solid(rig, materials, primitives, ok):
    scene = Scene((3.0, 3.0, 2.0), primitives)
    if ok:
        scene.build(rig, materials)
    else:
        with pytest.raises(ValueError, match="overlaps the named solid crate"):
            scene.build(rig, materials)


def test_a_footprints_centroid_is_volume_weighted_and_a_cylinders_is_its_middle():
    from maxim_overdrive.world.scene import footprint_of  # noqa: PLC0415

    big, small = Box((0, 0, 0), (3, 1, 1), "wood"), Box((3, 0, 0), (4, 1, 1), "wood")
    assert footprint_of([big, small]).centroid_m == pytest.approx((2.0, 0.5, 0.5))  # unweighted would be 2.25
    assert Cylinder((1.0, 2.0), 0.5, (0.4, 1.6), "wood").centroid_m == (1.0, 2.0, 1.0)


def test_thermal_degradation_follows_its_closed_form_at_every_rig(rigs, materials):
    # One step of the law: integrity falls by rate * dt * (T - limit) / 100 in every cell above the limit, whatever
    # the cell size. A rate that scaled with dx (a resolution-dependent law) fails here.
    wood = materials["wood"]
    assert wood.degrade_above_c is not None
    excess, dt = 150.0, 0.5
    for rig in rigs:
        g = Scene((1.0, 1.0, 1.0), (Box((0, 0, 0), (1, 1, 1), "wood", "block"),)).build(rig, materials)
        g.temperature[:] = wood.degrade_above_c + excess
        damage.thermal_degrade(g, dt)
        expected = 1.0 - wood.degrade_rate_per_s_per_100c * dt * excess / 100.0
        assert g.integrity == pytest.approx(np.full(g.shape, expected), rel=1e-6), rig.name


@pytest.mark.parametrize(
    ("later", "ok"),
    [
        (Box((0, 0.5, 0), (1, 1.5, 1), "concrete"), False),  # overlaps on y
        (Box((0, 0, 0.5), (1, 1, 1.5), "concrete"), False),  # overlaps on z
        (Box((0, 1, 0), (1, 2, 1), "concrete"), True),  # side by side on y
        (Box((0, 0, 1), (1, 1, 2), "concrete"), True),  # stacked on z
        (Cylinder((1.45, 1.45), 0.5, (0, 1), "concrete"), False),  # box corners overlap, the body doesn't: refused
    ],
    ids=["y", "z", "beside-y", "stacked-z", "cylinder-corner"],
)
def test_the_overlap_rule_judges_every_axis(rig, materials, later, ok):
    scene = Scene((3.0, 3.0, 2.0), (Box((0, 0, 0), (1, 1, 1), "wood", "crate"), later))
    if ok:
        scene.build(rig, materials)
    else:
        with pytest.raises(ValueError, match="overlaps the named solid crate"):
            scene.build(rig, materials)


def test_a_later_solid_may_fill_an_earlier_named_air_region(rig, materials):
    room = Box((0, 0, 0), (2, 2, 1), "air", "room")
    Scene((3.0, 3.0, 2.0), (room, Box((0.5, 0.5, 0), (1, 1, 0.5), "wood", "crate"))).build(rig, materials)


def test_an_imagined_object_may_not_sit_in_a_named_solids_footprint(rig, materials):
    wall = Box((1.0, 0.0, 0.0), (1.6, 3.0, 2.0), "concrete", "wall")
    doorway = Box((1.0, 1.0, 0.0), (1.6, 2.0, 2.0), "air", "doorway")
    g = Scene((3.0, 3.0, 2.0), (wall, doorway)).build(rig, materials)
    box = {"name": "box", "primitives": [{"min_m": [0, 0, 0], "max_m": [0.4, 0.4, 0.4], "material": "wood"}]}
    with pytest.raises(SpecRejected, match="that space belongs to wall"):
        place(g, box, (1.1, 1.3, 0.0))  # in the doorway's air, inside the wall's footprint
    place(g, box, (2.0, 1.3, 0.0))  # beside the wall is fine
    assert "box" in g.regions


def test_thermal_degradation_is_proportional_to_the_excess(rigs, materials):
    wood = materials["wood"]
    assert wood.degrade_above_c is not None
    for rig in rigs:
        g = Scene((1.0, 1.0, 1.0), (Box((0, 0, 0), (1, 1, 1), "wood", "block"),)).build(rig, materials)
        x, _, _ = g.mesh()
        excess = np.where(np.broadcast_to(x < 0.5, g.shape), 150.0, 50.0)
        g.temperature[:] = wood.degrade_above_c + excess
        damage.thermal_degrade(g, 0.5)
        expected = 1.0 - wood.degrade_rate_per_s_per_100c * 0.5 * excess / 100.0
        assert g.integrity == pytest.approx(expected, rel=1e-6), rig.name


@pytest.mark.parametrize("name", ["Crate", "CRATE", "crAte"])
def test_an_imagined_object_named_like_an_existing_region_is_refused_before_painting(rig, materials, name):
    g = Scene((3.0, 3.0, 2.0), (Box((0.2, 0.2, 0), (0.8, 0.8, 0.6), "wood", "crate"),)).build(rig, materials)
    before = g.material.copy()
    box = {"name": name, "primitives": [{"min_m": [0, 0, 0], "max_m": [0.4, 0.4, 0.4], "material": "wood"}]}
    with pytest.raises(SpecRejected, match="something called 'crate' already exists"):
        place(g, box, (2.0, 2.0, 0.0))
    assert np.array_equal(g.material, before)  # refused, not half-applied


def test_name_region_itself_refuses_a_name_maxim_would_confuse(rig, materials):
    # Its callers check first; this is the second line, for any future caller that doesn't.
    g = Scene((3.0, 3.0, 2.0), (Box((0.2, 0.2, 0), (0.8, 0.8, 0.6), "wood", "crate"),)).build(rig, materials)
    footprint = g.regions["crate"].footprint
    with pytest.raises(ValueError, match=r"region 'Crate' already exists \(as 'crate'\)"):
        g.name_region("Crate", g.regions["crate"].cells, footprint, solid=True)


def test_an_imagined_object_may_sit_in_a_named_air_room_but_no_primitive_may_enter_a_solids_footprint(rig, materials):
    room = Box((0.0, 0.0, 0.0), (3.0, 3.0, 2.0), "air", "room")
    crate = Cylinder((2.3, 2.3), 0.3, (0.0, 0.6), "wood", "crate")  # its box's corners are empty space
    g = Scene((3.0, 3.0, 2.0), (room, crate)).build(rig, materials)
    box = {"name": "box", "primitives": [{"min_m": [0, 0, 0], "max_m": [0.4, 0.4, 0.4], "material": "wood"}]}
    place(g, box, (0.2, 0.2, 0.0))  # inside the air room is fine
    two = {
        "name": "two",
        "primitives": [
            {"min_m": [0, 0, 0], "max_m": [0.2, 0.2, 0.2], "material": "wood"},
            {"min_m": [1.0, 1.0, 0], "max_m": [1.08, 1.08, 0.2], "material": "wood"},  # in the box's empty corner
        ],
    }
    with pytest.raises(SpecRejected, match="that space belongs to crate"):
        place(g, two, (1.0, 1.0, 0.0))


def test_paint_refuses_a_confusable_name_before_painting(rig, materials):
    g = MaterialGrid.empty((1.0, 1.0, 1.0), rig, materials)
    x, _, _ = g.mesh()
    footprint = Footprint(((0, 0, 0), (0.5, 1, 1)), (0.25, 0.5, 0.5))
    g.paint(np.broadcast_to(x < 0.5, g.shape), "wood", region="crate", footprint=footprint)
    before = g.material.copy()
    with pytest.raises(ValueError, match="already exists"):
        g.paint(np.ones(g.shape, dtype=bool), "steel", region="Crate", footprint=footprint)
    assert np.array_equal(g.material, before)


# -- closed schemas: every loader refuses a key it doesn't know, at every level (B12) ----------------------------------

RIG_FILE = "name: t\ncell_size_m: 0.25\nmin_substeps_per_turn: 2\nfull_res_radius_m: 4.0\n"


@pytest.mark.parametrize(
    ("text", "message"),
    [
        (RIG_FILE + "cell_size: 0.5\n", r"unknown key\(s\) \['cell_size'\]"),  # a misspelt cell_size_m
        (RIG_FILE + "cell_size_m: 0.5\n", "repeated key"),  # the second value would silently win
        ("- name: t\n", "rig profile .* must be a mapping"),
        ("cell_size_m: [\n", "not valid YAML"),
    ],
)
def test_a_rig_file_refuses_unknown_and_repeated_keys(tmp_path, text, message):
    path = tmp_path / "t.yaml"
    path.write_text(text)
    with pytest.raises(ValueError, match=message):
        RigProfile.load(path)


def _material_file(tmp_path, edit):
    raw = yaml.safe_load((data_dir() / "materials" / "core.yaml").read_text())
    edit(raw)
    path = tmp_path / "core.yaml"
    path.write_text(yaml.safe_dump(raw))
    return path


@pytest.mark.parametrize(
    ("edit", "message"),
    [
        (lambda raw: raw.update(materails={}), r"material table: unknown key\(s\) \['materails'\]"),
        # A misspelt degrade_above_c: without the refusal, wood would silently never degrade.
        (lambda raw: raw["materials"]["wood"].update(degrade_above=250.0), r"material wood: unknown key\(s\)"),
        (lambda raw: raw["materials"].update(steel=[1, 2]), "material steel must be a mapping"),
        (lambda raw: raw.update(materials=[1]), "materials must be a mapping"),
    ],
)
def test_a_material_file_refuses_unknown_keys_at_every_level(tmp_path, edit, message):
    with pytest.raises(ValueError, match=message):
        MaterialTable.load(_material_file(tmp_path, edit))


def test_a_material_file_refuses_a_repeated_key(tmp_path):
    text = (data_dir() / "materials" / "core.yaml").read_text()
    path = tmp_path / "core.yaml"
    path.write_text(text.replace("  wood:\n", "  wood:\n    id: 99\n", 1))
    with pytest.raises(ValueError, match="repeated key"):
        MaterialTable.load(path)


BOX_RAW = {"kind": "box", "min_m": [0, 0, 0], "max_m": [0.5, 0.5, 0.5], "material": "wood", "name": "crate"}
CYLINDER_RAW = {"kind": "cylinder", "center_xy_m": [0.5, 0.5], "radius_m": 0.2, "z_m": [0, 1], "material": "wood"}


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ({"extent_m": [1, 1, 1], "primitives": [], "ambient": 30.0}, r"scene: unknown key\(s\) \['ambient'\]"),
        ({"extent_m": [1, 1, 1], "primitives": [{**BOX_RAW, "colour": "red"}]}, r"box primitive: unknown key"),
        ({"extent_m": [1, 1, 1], "primitives": [{**CYLINDER_RAW, "radius": 1}]}, r"cylinder primitive: unknown key"),
        ({"extent_m": [1, 1, 1], "primitives": [{**BOX_RAW, "radius_m": 0.2}]}, r"box primitive: unknown key"),
    ],
)
def test_a_scene_refuses_unknown_keys_at_every_level(raw, message):
    with pytest.raises(ValueError, match=message):
        Scene.from_dict(raw)


def test_a_scene_accepts_every_key_it_knows():
    scene = Scene.from_dict({"extent_m": [1, 1, 1], "primitives": [BOX_RAW, CYLINDER_RAW], "ambient_c": 25.0})
    assert [p.kind for p in scene.primitives] == ["box", "cylinder"]
    assert scene.ambient_c == 25.0


@pytest.mark.parametrize(
    ("spec", "message"),
    [
        # A provenance or licence field the reader doesn't know must not vanish silently.
        ({"name": "crate", "primitives": [BOX_RAW], "licence": "cc-by"}, r"unknown key\(s\) \['licence'\]"),
        ({"name": "crate", "primitves": [BOX_RAW]}, r"unknown key\(s\) \['primitves'\]"),
        ({"name": "crate", "primitives": [{**BOX_RAW, "colour": "red"}]}, "malformed spec: box primitive: unknown"),
    ],
)
def test_an_imagined_object_refuses_unknown_keys(rig, materials, spec, message):
    g = Scene((3.0, 3.0, 2.0)).build(rig, materials)
    with pytest.raises(SpecRejected, match=message):
        place(g, spec, (1.0, 1.0, 0.0))
    assert not g.regions  # refused before anything was painted


@pytest.mark.parametrize("value", [5, "red", [1, 2], {"r": 1}])
def test_a_material_colour_must_be_three_whole_numbers(tmp_path, value):
    path = _material_file(tmp_path, lambda raw: raw["materials"]["wood"].update(color_rgb=value))
    with pytest.raises(ValueError, match=r"wood\.color_rgb must be three whole numbers"):
        MaterialTable.load(path)


# -- closed schemas, the other half: required keys, and shapes that must not crash -------------------------------------


@pytest.mark.parametrize("kind", [["box"], {}, 3, None])
def test_a_primitive_kind_that_is_not_a_name_is_refused_not_crashed_on(kind):
    with pytest.raises(ValueError, match="unknown primitive kind"):
        Scene.from_dict({"extent_m": [1, 1, 1], "primitives": [{**BOX_RAW, "kind": kind}]})


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ({"primitives": []}, r"scene: missing key\(s\) \['extent_m'\]"),
        (
            {"extent_m": [1, 1, 1], "primitives": [{"kind": "box", "max_m": [1, 1, 1], "material": "wood"}]},
            r"box primitive: missing key\(s\) \['min_m'\]",
        ),
        (
            {"extent_m": [1, 1, 1], "primitives": [{k: v for k, v in CYLINDER_RAW.items() if k != "radius_m"}]},
            r"cylinder primitive: missing key\(s\) \['radius_m'\]",
        ),
        ({"extent_m": 5}, "extent_m must be 3 numbers"),
    ],
)
def test_a_scene_refuses_a_missing_key_by_name(raw, message):
    with pytest.raises(ValueError, match=message):
        Scene.from_dict(raw)


def test_a_rig_file_refuses_a_missing_key_by_name(tmp_path):
    path = tmp_path / "t.yaml"
    path.write_text("name: t\ncell_size_m: 0.25\n")
    with pytest.raises(ValueError, match=r"missing key\(s\) \['full_res_radius_m', 'min_substeps_per_turn'\]"):
        RigProfile.load(path)


@pytest.mark.parametrize(("text", "message"), [("name: [1]\n", "name must be a string"), ("name: 7\n", "name must be")])
def test_a_rig_name_must_be_a_string(tmp_path, text, message):
    path = tmp_path / "t.yaml"
    path.write_text(RIG_FILE.replace("name: t\n", text))
    with pytest.raises(ValueError, match=message):
        RigProfile.load(path)


@pytest.mark.parametrize(
    ("edit", "message"),
    [
        (lambda raw: raw["materials"]["wood"].pop("id"), r"material wood: missing key\(s\) \['id'\]"),
        (lambda raw: raw["materials"].update({5: raw["materials"]["wood"]}), "material names must be strings"),
    ],
)
def test_a_material_file_refuses_a_missing_key_and_a_name_that_is_not_a_string(tmp_path, edit, message):
    with pytest.raises(ValueError, match=message):
        MaterialTable.load(_material_file(tmp_path, edit))


def test_a_material_without_its_optional_degradation_keys_loads(tmp_path):
    def edit(raw):
        del raw["materials"]["wood"]["degrade_above_c"], raw["materials"]["wood"]["degrade_rate_per_s_per_100c"]

    table = MaterialTable.load(_material_file(tmp_path, edit))
    assert table["wood"].degrade_above_c is None
    assert table["wood"].degrade_rate_per_s_per_100c == 0.0


def test_the_material_schema_names_every_field_the_reader_fills():
    from maxim_overdrive.config import MATERIAL_OPTIONAL, MATERIAL_REQUIRED, Material  # noqa: PLC0415

    assert {f.name for f in dataclasses.fields(Material)} - {"name"} == MATERIAL_REQUIRED | MATERIAL_OPTIONAL


class _OddMapping(dict[str, object]):  # a Python caller's mapping with a key no YAML or JSON could produce
    def __iter__(self):
        yield ["unhashable"]


def test_an_imagined_object_with_an_unhashable_key_is_refused_not_crashed_on(rig, materials):
    g = Scene((3.0, 3.0, 2.0)).build(rig, materials)
    with pytest.raises(SpecRejected, match="unknown key"):
        place(g, _OddMapping(name="crate", primitives=[BOX_RAW]), (1.0, 1.0, 0.0))


_json = st.recursive(
    st.none() | st.booleans() | st.integers() | st.floats() | st.text(max_size=8),
    lambda inner: st.lists(inner, max_size=4) | st.dictionaries(st.text(max_size=12), inner, max_size=5),
    max_leaves=20,
)
_scene_like = st.fixed_dictionaries(
    {},
    optional={
        "extent_m": _json,
        "ambient_c": _json,
        "primitives": st.lists(
            st.fixed_dictionaries(
                {},
                optional={
                    k: _json
                    for k in ("kind", "min_m", "max_m", "material", "name", "center_xy_m", "radius_m", "z_m", "colour")
                },
            ),
            max_size=3,
        )
        | _json,
        "bogus": _json,
    },
)


@settings(max_examples=300, deadline=None)
@given(raw=_scene_like | _json)
def test_a_scene_built_from_any_json_is_built_or_refused_never_crashed_on(raw):
    with contextlib.suppress(ValueError):  # a refusal is expected for most inputs; anything else fails the test
        Scene.from_dict(raw)
