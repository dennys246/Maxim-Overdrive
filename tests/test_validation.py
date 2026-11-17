"""Every input the world server refuses, it refuses loudly, and the error says what was wrong.

These are the edges of config, grid, scene, damage, heat and the SEM bridge. Each rejection is a promise to the
author of a data file or to a caller, so each is tested.
"""

from __future__ import annotations

import contextlib
import dataclasses
import math
import subprocess
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest
import yaml
from hypothesis import HealthCheck, given, settings
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
        Scene.from_dict({"version": 0, "extent_m": [1, 1, 1], "primitives": [{"kind": "torus", "material": "wood"}]})


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
    custom.write_text("version: 0\nname: tiny\ncell_size_m: 0.25\nmin_substeps_per_turn: 2\nfull_res_radius_m: 4.0\n")
    assert RigProfile.load(custom) == RigProfile("tiny", 0.25, 2, 4.0)
    assert RigProfile.load("rig").cell_size_m == 0.1
    with pytest.raises(FileNotFoundError):
        RigProfile.load("no_such_rig")


# -- every number in a data file is a finite real number, or the loader says which one isn't -------------------------


@pytest.mark.parametrize(
    ("ambient", "message"), [("nan", "finite number"), (".nan", "finite number"), (-300, "absolute zero")]
)
def test_a_scene_refuses_an_impossible_ambient_temperature(ambient, message):
    raw = yaml.safe_load(f"version: 0\nextent_m: [1, 1, 1]\nprimitives: []\nambient_c: {ambient}\n")
    with pytest.raises(ValueError, match=message):
        Scene.from_dict(raw)


@pytest.mark.parametrize(
    ("field", "value"), [("cell_size_m", "'0.1'"), ("cell_size_m", ".inf"), ("full_res_radius_m", "true")]
)
def test_a_rig_file_refuses_a_value_that_is_not_a_finite_number(tmp_path, field, value):
    good = {
        "version": "0",
        "name": "t",
        "cell_size_m": "0.25",
        "min_substeps_per_turn": "2",
        "full_res_radius_m": "4.0",
    }
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
    path.write_text(f"version: 0\nname: t\ncell_size_m: 0.25\nmin_substeps_per_turn: {value}\nfull_res_radius_m: 4.0\n")
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

RIG_FILE = "version: 0\nname: t\ncell_size_m: 0.25\nmin_substeps_per_turn: 2\nfull_res_radius_m: 4.0\n"


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
        (lambda raw: raw.update(materails={}), r"material table .*: unknown key\(s\) \['materails'\]"),
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
        (
            {"version": 0, "extent_m": [1, 1, 1], "primitives": [], "ambient": 30.0},
            r"scene: unknown key\(s\) \['ambient'\]",
        ),
        (
            {"version": 0, "extent_m": [1, 1, 1], "primitives": [{**BOX_RAW, "colour": "red"}]},
            r"box primitive: unknown key",
        ),
        (
            {"version": 0, "extent_m": [1, 1, 1], "primitives": [{**CYLINDER_RAW, "radius": 1}]},
            r"cylinder primitive: unknown key",
        ),
        (
            {"version": 0, "extent_m": [1, 1, 1], "primitives": [{**BOX_RAW, "radius_m": 0.2}]},
            r"box primitive: unknown key",
        ),
    ],
)
def test_a_scene_refuses_unknown_keys_at_every_level(raw, message):
    with pytest.raises(ValueError, match=message):
        Scene.from_dict(raw)


def test_a_scene_accepts_every_key_it_knows():
    scene = Scene.from_dict(
        {"version": 0, "extent_m": [1, 1, 1], "primitives": [BOX_RAW, CYLINDER_RAW], "ambient_c": 25.0}
    )
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
        Scene.from_dict({"version": 0, "extent_m": [1, 1, 1], "primitives": [{**BOX_RAW, "kind": kind}]})


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ({"version": 0, "primitives": []}, r"scene: missing key\(s\) \['extent_m'\]"),
        (
            {
                "version": 0,
                "extent_m": [1, 1, 1],
                "primitives": [{"kind": "box", "max_m": [1, 1, 1], "material": "wood"}],
            },
            r"box primitive: missing key\(s\) \['min_m'\]",
        ),
        (
            {
                "version": 0,
                "extent_m": [1, 1, 1],
                "primitives": [{k: v for k, v in CYLINDER_RAW.items() if k != "radius_m"}],
            },
            r"cylinder primitive: missing key\(s\) \['radius_m'\]",
        ),
        ({"version": 0, "extent_m": 5}, "extent_m must be 3 numbers"),
    ],
)
def test_a_scene_refuses_a_missing_key_by_name(raw, message):
    with pytest.raises(ValueError, match=message):
        Scene.from_dict(raw)


def test_a_rig_file_refuses_a_missing_key_by_name(tmp_path):
    path = tmp_path / "t.yaml"
    path.write_text("version: 0\nname: t\ncell_size_m: 0.25\n")
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
    assert not MATERIAL_REQUIRED & MATERIAL_OPTIONAL


@pytest.mark.parametrize("key", sorted(__import__("maxim_overdrive.config").config.MATERIAL_REQUIRED))
def test_every_required_material_key_is_named_when_missing(tmp_path, key):
    path = _material_file(tmp_path, lambda raw: raw["materials"]["wood"].pop(key))
    with pytest.raises(ValueError, match=rf"material wood: missing key\(s\) \['{key}'\]"):
        MaterialTable.load(path)


def test_every_optional_material_key_is_read_not_just_accepted(tmp_path):
    def edit(raw):
        raw["materials"]["wood"].update(degrade_above_c=123.5, degrade_rate_per_s_per_100c=0.0625)

    wood = MaterialTable.load(_material_file(tmp_path, edit))["wood"]
    assert (wood.degrade_above_c, wood.degrade_rate_per_s_per_100c) == (123.5, 0.0625)


def test_a_key_cannot_be_both_required_and_optional():
    from maxim_overdrive.checks import known_keys  # noqa: PLC0415

    with pytest.raises(TypeError, match="both required and optional"):
        known_keys({}, "x", required={"a"}, optional={"a", "b"})


@pytest.mark.parametrize("load", [RigProfile.load, MaterialTable.load, ActionLimits.load])
def test_a_data_file_nested_too_deeply_is_refused_with_its_name(tmp_path, load):
    path = tmp_path / "deep.yaml"
    path.write_text("x: " + "[" * 5000 + "]" * 5000 + "\n")
    with pytest.raises(ValueError, match=r"deep\.yaml: nested too deeply"):
        load(path)


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
# Well-formed values, so the search reaches the checks behind each field, mixed with malformed ones. A strategy that
# is mostly junk is refused at its first key and never builds a primitive (a review counted 0 in 300).
_number = st.floats(-5, 5) | st.integers(-5, 5)
_low = st.lists(st.floats(0.0, 1.0), min_size=3, max_size=3)
_high = st.lists(st.floats(1.1, 2.0), min_size=3, max_size=3)
_material = st.sampled_from(["wood", "steel", "concrete", "air", "unobtainium"])
_good_box = st.fixed_dictionaries(
    {"min_m": _low, "max_m": _high, "material": _material},
    optional={"kind": st.just("box"), "name": st.text(min_size=1, max_size=6)},
)
_good_cylinder = st.fixed_dictionaries(
    {
        "kind": st.just("cylinder"),
        "center_xy_m": st.lists(st.floats(1.0, 2.0), min_size=2, max_size=2),
        "radius_m": st.floats(0.1, 0.9),
        "z_m": st.lists(st.floats(0.0, 0.9), min_size=2, max_size=2).map(sorted),
        "material": _material,
    },
    optional={"name": st.text(min_size=1, max_size=6)},
)
_bad_primitive = st.fixed_dictionaries(
    {"kind": st.sampled_from(["box", "cylinder"]) | _json},
    optional={k: _number | _json for k in ("min_m", "max_m", "material", "center_xy_m", "radius_m", "z_m", "x")},
)
_primitive = _good_box | _good_cylinder | _bad_primitive | _json
_built_scene = st.fixed_dictionaries(  # always reaches Box and Cylinder, and their own checks
    {
        "version": st.just(0),
        "extent_m": st.just([3.0, 3.0, 2.0]),
        "primitives": st.lists(_good_box | _good_cylinder, min_size=1, max_size=3),
    },
    optional={"ambient_c": _number},
)
_scene_like = (
    _built_scene
    | st.fixed_dictionaries(
        {
            "version": st.just(0),
            "extent_m": st.just([3.0, 3.0, 2.0]) | st.lists(_number, min_size=3, max_size=3) | _json,
        },
        optional={"ambient_c": _number | _json, "primitives": st.lists(_primitive, max_size=3) | _json},
    )
    | st.dictionaries(st.text(max_size=12), _json, max_size=4)
)


@settings(max_examples=300, deadline=None)
@given(raw=_scene_like | _json)
def test_a_scene_built_from_any_json_is_built_or_refused_never_crashed_on(raw):
    with contextlib.suppress(ValueError):  # a refusal is expected for most inputs; anything else fails the test
        Scene.from_dict(raw)


_spec_like = st.fixed_dictionaries(
    {
        "name": st.text(min_size=1, max_size=8),
        "primitives": st.lists(_good_box | _good_cylinder, min_size=1, max_size=2),
    },
) | st.fixed_dictionaries(
    {"name": st.text(min_size=1, max_size=8) | _json, "primitives": st.lists(_primitive, max_size=3) | _json},
    optional={"licence": _json},
)


@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(spec=_spec_like | _json, origin=st.lists(st.floats(0, 3), min_size=3, max_size=3) | _json)
def test_an_imagined_object_from_any_json_is_placed_or_refused_and_a_refusal_changes_nothing(
    rig, materials, spec, origin
):
    # A named wall, so the occupied, namesake and footprint refusals are reachable too.
    g = Scene((3.0, 3.0, 2.0), (Box((0.0, 0.0, 0.0), (0.6, 3.0, 2.0), "concrete", "wall"),)).build(rig, materials)
    before, regions = g.material.copy(), set(g.regions)
    try:
        mass = place(g, spec, origin)
    except SpecRejected:
        assert np.array_equal(g.material, before)
        assert set(g.regions) == regions
    else:
        assert mass > 0
        assert set(g.regions) == regions | {spec["name"]}


def _mutation_paths(doc: object, prefix: tuple[object, ...] = ()) -> list[tuple[object, ...]]:
    """Every key path into a parsed data file's mappings, the file itself first."""
    paths = [prefix]
    if isinstance(doc, dict):
        for k, v in doc.items():
            paths += _mutation_paths(v, (*prefix, k))
    return paths


_DATA_FILES: list[tuple[Callable[[Path], object], Path]] = [
    (RigProfile.load, data_dir() / "rigs" / "rig.yaml"),
    (MaterialTable.load, data_dir() / "materials" / "core.yaml"),
    (ActionLimits.load, data_dir() / "world" / "actions.yaml"),
]


@settings(max_examples=200, deadline=None)
@given(data=st.data())
def test_every_data_loader_loads_or_refuses_one_change_to_its_real_file(tmp_path_factory, data):
    # One change to a real file reaches every check behind the first: number checks, each material, __post_init__.
    for load, source in _DATA_FILES:
        doc = yaml.safe_load(source.read_text())
        path = data.draw(st.sampled_from(_mutation_paths(doc)[1:]))
        parent = doc
        for key in path[:-1]:
            parent = parent[key]
        change = data.draw(st.sampled_from(["replace", "delete", "add"]))
        if change == "replace":
            parent[path[-1]] = data.draw(_json | _number)
        elif change == "delete":
            del parent[path[-1]]
        else:
            parent[data.draw(st.text(min_size=1, max_size=12))] = data.draw(_json)
        file = tmp_path_factory.mktemp("mutated") / source.name
        file.write_text(yaml.safe_dump(doc))
        with contextlib.suppress(ValueError):
            load(file)


@settings(max_examples=150, deadline=None)
@given(raw=_json | st.dictionaries(st.text(max_size=20), _json, max_size=6), as_yaml=st.booleans(), text=st.text())
def test_every_data_loader_loads_or_refuses_any_file(tmp_path_factory, raw, as_yaml, text):
    path = tmp_path_factory.mktemp("fuzz") / "f.yaml"
    path.write_text(yaml.safe_dump(raw) if as_yaml else text)
    for load in (RigProfile.load, MaterialTable.load, ActionLimits.load):
        with contextlib.suppress(ValueError):
            load(path)


# -- format versions: every data format names its version, and a reader refuses one it doesn't know (B21) --------------

ROOT = Path(__file__).resolve().parents[1]
BAD_VERSIONS = [("1", "got 1"), ("true", "got True"), ("0.0", "got 0.0"), ("'0'", "got '0'"), ("~", "got None")]


@pytest.mark.parametrize(("value", "shown"), BAD_VERSIONS)
def test_a_rig_file_refuses_a_version_it_does_not_know(tmp_path, value, shown):
    path = tmp_path / "t.yaml"
    path.write_text(RIG_FILE.replace("version: 0\n", f"version: {value}\n"))
    with pytest.raises(ValueError, match=f"rig profile .* version must be 0, {shown}"):
        RigProfile.load(path)


def test_a_rig_file_without_a_version_is_refused(tmp_path):
    path = tmp_path / "t.yaml"
    path.write_text(RIG_FILE.replace("version: 0\n", ""))
    with pytest.raises(ValueError, match="version must be 0, got None"):
        RigProfile.load(path)


@pytest.mark.parametrize("value", [1, True, 0.0, "0", None])
def test_a_material_file_refuses_a_version_it_does_not_know(tmp_path, value):
    path = _material_file(tmp_path, lambda raw: raw.update(version=value))
    with pytest.raises(ValueError, match=f"material table .* version must be 0, got {value!r}"):
        MaterialTable.load(path)


@pytest.mark.parametrize("value", [1, True, 0.0, "0", None])
def test_a_scene_refuses_a_version_it_does_not_know(value):
    with pytest.raises(ValueError, match=f"scene version must be 0, got {value!r}"):
        Scene.from_dict({"version": value, "extent_m": [1, 1, 1]})


def test_every_shipped_data_file_is_at_its_formats_current_version():
    from maxim_overdrive.config import ACTION_LIMITS_VERSION, MATERIAL_TABLE_VERSION, RIG_PROFILE_VERSION  # noqa: PLC0415

    # Each data directory has one reader and one format; a file in a directory no reader owns is an error, so a new
    # kind of data file can't ship without a version and a loader.
    readers: dict[str, tuple[Callable[[Path], object], int]] = {
        "rigs": (RigProfile.load, RIG_PROFILE_VERSION),
        "materials": (MaterialTable.load, MATERIAL_TABLE_VERSION),
        "world": (ActionLimits.load, ACTION_LIMITS_VERSION),
    }
    # The files git tracks, not whatever is on disk: a Finder .DS_Store is not a data file.
    listed = subprocess.run(["git", "ls-files", "data"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    files = [ROOT / line for line in listed.splitlines()]
    assert files
    for path in files:
        kind = path.relative_to(data_dir()).parts[0]
        assert kind in readers, f"{path}: no reader owns data/{kind}/"
        load, version = readers[kind]
        assert path.suffix == ".yaml", path
        shipped = yaml.safe_load(path.read_text())["version"]
        assert type(shipped) is int, path  # False == 0, but false is not version 0
        assert shipped == version, path
        load(path)


@pytest.mark.parametrize(
    ("load", "fixture"),
    [(RigProfile.load, "rig.yaml"), (MaterialTable.load, "core.yaml"), (ActionLimits.load, "actions.yaml")],
)
def test_the_committed_v0_files_still_load(load, fixture):
    # Golden files at version 0. When a format moves on, its reader must still load these (a migration) or refuse
    # them loudly for their version; they are never rewritten to match. Loading must also read every value: today a
    # v0 file loads to exactly what the shipped file does, and after a bump this compares with what migration gives.
    golden = load(Path(__file__).parent / "fixtures" / "formats" / "v0" / fixture)
    shipped = load(
        {
            "rig.yaml": data_dir() / "rigs" / "rig.yaml",
            "core.yaml": data_dir() / "materials" / "core.yaml",
            "actions.yaml": data_dir() / "world" / "actions.yaml",
        }[fixture]
    )
    if isinstance(golden, MaterialTable):
        assert isinstance(shipped, MaterialTable)
        assert golden.by_name == shipped.by_name
    else:
        assert golden == shipped


def _newer(text: str) -> str:
    """A file from a future version: its version bumped, and a field that version added."""
    return text.replace("version: 0", "version: 1", 1) + "added_in_v1: true\n"


@pytest.mark.parametrize(
    ("load", "source", "message"),
    [
        (RigProfile.load, data_dir() / "rigs" / "rig.yaml", "rig profile .* version must be 0, got 1"),
        (MaterialTable.load, data_dir() / "materials" / "core.yaml", "material table .* version must be 0, got 1"),
        (ActionLimits.load, data_dir() / "world" / "actions.yaml", "action limits version must be 0, got 1"),
    ],
)
def test_a_file_from_a_newer_format_is_refused_for_its_version_not_its_new_fields(tmp_path, load, source, message):
    path = tmp_path / source.name
    path.write_text(_newer(source.read_text()))
    with pytest.raises(ValueError, match=message):
        load(path)


def test_a_scene_from_a_newer_format_is_refused_for_its_version_not_its_new_fields():
    with pytest.raises(ValueError, match="scene version must be 0, got 1"):
        Scene.from_dict({"version": 1, "extent_m": [1, 1, 1], "added_in_v1": True})
