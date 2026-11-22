"""Every input the world server refuses, it refuses loudly, and the error says what was wrong.

These are the edges of config, grid, scene, damage, heat and the SEM bridge. Each rejection is a promise to the
author of a data file or to a caller, so each is tested.
"""

from __future__ import annotations

import contextlib
import dataclasses
import math
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest
import yaml
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from maxim_overdrive import data
from simcore.adapters.loaders import DataPath, load_action_limits, load_materials, read_yaml
from simcore.adapters.sem import bridge
from simcore.core import damage, heat, physics
from simcore.core.applier import Applier
from simcore.core.grid import Footprint, MaterialGrid
from simcore.core.imagination import Budget, SpecRejected, place
from simcore.core.law import LawInputs
from simcore.core.limits import ACTION_LIMITS
from simcore.core.materials import MATERIAL, MATERIAL_TABLE, MaterialTable
from simcore.core.refusals import RefusalCode, Refused
from simcore.core.scene import Box, Cylinder, Scene, Spawn
from simcore.core.world import HeatSource, World
from simcore.protocol.tiers import RIG_PROFILE, RigProfile
from tests._gitutil import git

LIMITS = data.action_limits()
MATERIAL_REQUIRED = frozenset(f.name for f in MATERIAL.fields if f.required)
DATA = Path(__file__).resolve().parents[1] / "data"
SCENE_RAW = {"version": 1, "extent_m": [1, 1, 1], "spawns": []}
MATERIAL_OPTIONAL = frozenset(f.name for f in MATERIAL.fields if not f.required)

# -- config ---------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("dx_m", "message"),
    [
        (0.0, "dx_m must be positive"),
        (-0.1, "dx_m must be positive"),
        (math.nan, "dx_m must be a finite number"),
        (True, "dx_m must be a finite number"),
    ],
)
def test_a_grid_refuses_an_impossible_spacing(materials, dx_m, message):
    # Before resolution left the rig (D20), RigProfile refused these as cell_size_m; the grid holds the line now.
    with pytest.raises(ValueError, match=message):
        MaterialGrid.empty((1.0, 1.0, 1.0), materials, dx_m=dx_m)


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
    with pytest.raises(ValueError, match="id must be from 0 to 255"):
        MaterialTable(_table_with(materials, wood={"id": 256}))


# -- grid and scene -------------------------------------------------------------------------------------------------


def test_extents_must_be_whole_cells_at_every_rig(materials):
    with pytest.raises(ValueError, match="whole number"):
        MaterialGrid.empty((1.05, 1.0, 1.0), materials, dx_m=0.2)


def test_a_point_outside_the_grid_has_no_cell(dx_m, materials):
    g = MaterialGrid.empty((1.0, 1.0, 1.0), materials, dx_m=dx_m)
    assert g.cell_of((0.0, 0.0, 0.0)) == (0, 0, 0)
    for point in [(-0.01, 0.5, 0.5), (0.5, 1.0, 0.5), (0.5, 0.5, 7.0)]:
        with pytest.raises(ValueError, match="outside the grid"):
            g.cell_of(point)


def test_region_names_are_unique(dx_m, materials):
    g = MaterialGrid.empty((1.0, 1.0, 1.0), materials, dx_m=dx_m)
    x, _, _ = g.mesh()
    with g.writing(writer="construction"):
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


def test_a_scene_refuses_unknown_materials(dx_m, materials):
    scene = Scene((1.0, 1.0, 1.0), (Box((0, 0, 0), (0.4, 0.4, 0.4), "adamantium", "thing"),))
    with pytest.raises(ValueError, match="unknown material 'adamantium' in primitive 'thing'"):
        scene.build(materials, dx_m=dx_m)


@pytest.mark.parametrize("raw", [["not", "a", "scene"], "scene", None, 3])
def test_a_scene_must_be_a_mapping(raw):
    with pytest.raises(ValueError, match="scene must be a mapping"):
        Scene.from_dict(raw)


def test_a_scene_refuses_unknown_primitive_kinds():
    with pytest.raises(ValueError, match="unknown kind 'torus'"):
        Scene.from_dict({**SCENE_RAW, "primitives": [{"kind": "torus", "material": "wood"}]})


# -- heat, damage, world ----------------------------------------------------------------------------------------------


def test_no_time_means_no_substeps_and_no_change(dx_m, materials):
    g = MaterialGrid.empty((1.0, 1.0, 1.0), materials, dx_m=dx_m)
    with g.writing(writer="construction"):
        g.temperature[0, 0, 0] = 500.0
    before = g.temperature.copy()
    with g.writing(writer="construction"):
        assert heat.step(g, 0.0) == 0
        assert heat.step(g, -5.0) == 0
    assert np.array_equal(g.temperature, before)


@pytest.mark.parametrize(("energy_j", "sigma_m"), [(-1.0, 0.2), (1.0, 0.0), (1.0, -0.2)])
def test_a_strike_refuses_negative_energy_and_non_positive_width(dx_m, materials, energy_j, sigma_m):
    g = MaterialGrid.empty((1.0, 1.0, 1.0), materials, dx_m=dx_m)
    with pytest.raises(ValueError, match="non-negative"):
        physics.strike(g, (0.5, 0.5, 0.5), energy_j, sigma_m)


def test_a_region_with_no_solid_cells_cannot_be_breached(dx_m, materials):
    g = MaterialGrid.empty((1.0, 1.0, 1.0), materials, dx_m=dx_m)
    x, _, _ = g.mesh()
    with g.writing(writer="construction"):
        g.paint(
            np.broadcast_to(x < 0.5, g.shape),
            "air",
            region="doorway",
            footprint=Footprint(((0, 0, 0), (0.5, 1, 1)), (0.25, 0.5, 0.5)),
        )
    assert damage.region_breached(g, "doorway") is False


def test_a_world_with_no_fire_stays_at_ambient(dx_m, materials):
    w = World.from_scene(
        Scene((1.0, 1.0, 1.0), (Box((0, 0, 0), (0.4, 1, 1), "concrete", "wall"),)),
        materials,
        dx_m=dx_m,
        limits=LIMITS,
    )
    w.advance()
    assert np.allclose(w.grid.temperature, 20.0)
    assert w.turn == 1


def test_a_source_smaller_than_a_cell_still_delivers_its_full_power(dx_m, materials):
    # All air, so the fire has no solid to sit on. A source this small is no action's (the limits refuse it), so it
    # arrives the one other way, at construction.
    spark = HeatSource((0.5, 0.5, 0.5), radius_m=1e-4, power_w=100.0)
    w = World(Scene((1.0, 1.0, 1.0)).build(materials, dx_m=dx_m), limits=LIMITS, sources={"spark": spark})
    power = w._power_field()
    assert power is not None
    assert power.sum() == pytest.approx(100.0)
    assert power[w.grid.cell_of((0.5, 0.5, 0.5))] == pytest.approx(100.0)


# -- SEM bridge -------------------------------------------------------------------------------------------------------


def _world(dx_m, materials):
    return World.from_scene(
        Scene((2.0, 2.0, 2.0), (Box((0.8, 0, 0), (1.2, 2, 2), "concrete", "wall"),)),
        materials,
        dx_m=dx_m,
        limits=LIMITS,
    )


def test_sensors_and_modulators_refuse_unknown_names(dx_m, materials):
    w = _world(dx_m, materials)
    with pytest.raises(ValueError, match="unknown region quantity 'colour'"):
        bridge.RegionInstrument(w.frames, "wall", "colour")
    with pytest.raises(ValueError, match="no region 'door'"):
        bridge.RegionInstrument(w.frames, "door", "integrity")
    with pytest.raises(ValueError, match="no region 'door'"):
        bridge.StructureModulator(Applier(w), w.frames, "door")


def test_every_sensor_reports_its_schema_and_unit(dx_m, materials):
    w = _world(dx_m, materials)
    sensors, _ = bridge.region_parts(Applier(w), w.frames, "wall")
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


def test_a_region_that_lost_all_its_cells_reads_nan_and_cannot_burn(dx_m, materials):
    w = _world(dx_m, materials)
    sensors, mods = bridge.region_parts(Applier(w), w.frames, "wall")
    with w.grid.writing(writer="construction"):  # a later paint takes every cell
        w.grid.paint(w.grid.regions["wall"].cells, "air")
    assert math.isnan(sensors["temperature_max"].value())
    res = mods["structure"].execute("ignite", {"power_w": 1000.0})
    assert not res.success
    assert res.error == "region_gone"  # the closed vocabulary; the words stay in the applier's Outcome
    assert "fire:wall" not in w.sources


def test_an_imagined_object_over_its_mass_budget_is_refused(dx_m, materials):
    g = Scene((3.0, 3.0, 2.0)).build(materials, dx_m=dx_m)
    crate = {"name": "c", "primitives": [{"min_m": [0, 0, 0], "max_m": [0.6, 0.6, 0.6], "material": "wood"}]}
    with pytest.raises(SpecRejected, match="too heavy: 130 kg, the limit is 100 kg"):
        place(g, crate, (1.0, 1.0, 0.0), Budget(max_mass_kg=100.0))
    assert "c" not in g.regions


def test_the_game_data_is_found_installed_or_in_a_checkout_or_refused(tmp_path):
    here = tmp_path / "src" / "maxim_overdrive"
    here.mkdir(parents=True)
    with pytest.raises(FileNotFoundError, match=r"no game data .*: none of .*_data, .*data is a directory"):
        data.data_dir(here)
    (tmp_path / "data").mkdir()
    assert str(data.data_dir(here)) == str(tmp_path / "data")  # a checkout
    (here / "_data").mkdir()
    assert str(data.data_dir(here)) == str(here / "_data")  # installed wins
    assert str(data.data_dir()) == str(DATA)  # this checkout


def test_the_game_data_is_a_place_only_the_file_gates_open():
    """B29 (step 3b delta round 7, D7-N2): data_dir hands out no pathlib.Path, so game code can't read a data file
    past the strict YAML gate; it joins bare names, and the loaders open it."""
    where = data.data_dir() / "materials" / "core.yaml"
    assert isinstance(where, DataPath)
    for opener in ("read_text", "read_bytes", "open", "parent", "resolve", "__fspath__"):
        assert not hasattr(where, opener), opener
    with pytest.raises(TypeError):
        Path(where)  # type: ignore[arg-type]  # no __fspath__: the point
    assert load_materials(where).by_name.keys() == load_materials(DATA / "materials" / "core.yaml").by_name.keys()
    again = data.data_dir() / "materials" / "core.yaml"
    assert str(where) == str(again)  # handles compare by identity; their text names the place
    assert repr(where).startswith("DataPath(")


@pytest.mark.parametrize("name", ["..", ".", "a/b", "/etc", "", 7, "x\\y"])
def test_a_data_path_joins_bare_names_only(name):
    with pytest.raises(Refused) as caught:
        data.data_dir() / name
    assert caught.value.code is RefusalCode.BAD_NAME


def test_a_rig_profile_loads_by_path_and_the_game_finds_its_own_by_name(tmp_path):
    custom = tmp_path / "tiny.yaml"
    custom.write_text("version: 1\nname: tiny\n")
    assert RigProfile.load(custom) == RigProfile("tiny")
    assert data.rig_profile("rig").name == "rig"
    with pytest.raises(FileNotFoundError):
        data.rig_profile("no_such_rig")


@pytest.mark.parametrize("name", ["../../x", "rigs/rig", "/etc/passwd", "..", "", "rig.yaml", 7, "a b"])
def test_a_rig_name_with_a_separator_dots_or_an_absolute_path_is_refused(name):
    # delta round 4, Trust D4-N2: an operator's rig flag joined unchecked into a path read any reachable *.yaml.
    with pytest.raises(ValueError, match="a rig name is letters, digits"):
        data.rig_profile(name)


# -- every number in a data file is a finite real number, or the loader says which one isn't -------------------------


@pytest.mark.parametrize(
    ("ambient", "message"), [("nan", "finite number"), (".nan", "finite number"), (-300, "above -273.15")]
)
def test_a_scene_refuses_an_impossible_ambient_temperature(ambient, message):
    raw = yaml.safe_load(f"version: 1\nextent_m: [1, 1, 1]\nspawns: []\nambient_c: {ambient}\n")
    with pytest.raises(ValueError, match=message):
        Scene.from_dict(raw)


@pytest.mark.parametrize(
    ("extent", "message"),
    [
        ([True, 3, 2], "extent_m must be 3 finite numbers"),
        ([3, 3], "extent_m must be 3 numbers"),
        (["3", 3, 2], "extent_m must be 3 finite numbers"),
        ([math.nan, 3, 2], "extent_m must be 3 finite numbers"),
        ([0, 3, 2], "above 0 and within 1000 of 0 on every axis"),
        ([3, 3, 1e6], "above 0 and within 1000 of 0 on every axis"),
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
        with pytest.raises(ValueError, match=r"ambient_c must be above -273\.15 and at most 3000"):
            Scene((1.0, 1.0, 1.0), ambient_c=ambient)


def test_a_named_region_needs_its_authored_bounds(dx_m, materials):
    g = MaterialGrid.empty((1.0, 1.0, 1.0), materials, dx_m=dx_m)
    x, _, _ = g.mesh()
    with pytest.raises(ValueError, match="needs its authored footprint"):
        g.paint(np.broadcast_to(x < 0.5, g.shape), "wood", region="crate")
    assert "crate" not in g.regions
    assert (g.material == 0).all()  # refused before anything was painted
    with g.writing(writer="construction"):
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


def test_an_imagined_objects_size_budget_is_judged_the_same_at_every_rig(spacings, materials):
    # A 1.5 m slab whose faces sit off the 0.2 m grid: measured from cells it spans 1.6 m at laptop, and was refused
    # there only. Measured from its authored geometry it is 1.5 m at every rig.
    slab = {"name": "slab", "primitives": [{"min_m": [0, 0, 0], "max_m": [1.5, 0.3, 0.3], "material": "wood"}]}
    for dx_m in spacings:
        g = Scene((4.0, 3.0, 2.0)).build(materials, dx_m=dx_m)
        place(g, slab, (1.25, 1.0, 0.0), Budget(max_extent_m=1.5, max_mass_kg=1000.0))
        assert g.regions["slab"].footprint.bounds_m == ((1.25, 1.0, 0.0), (2.75, 1.3, 0.3)), dx_m


def test_a_multi_primitive_objects_footprint_covers_every_primitive(dx_m, materials):
    spec = {
        "name": "table",
        "primitives": [
            {"min_m": [0, 0, 0.6], "max_m": [1.0, 0.6, 0.7], "material": "wood"},  # the top
            {"kind": "cylinder", "center_xy_m": [0.1, 0.1], "radius_m": 0.05, "z_m": [0, 1.4], "material": "wood"},
        ],
    }
    g = Scene((3.0, 3.0, 2.0)).build(materials, dx_m=dx_m)
    place(g, spec, (1.0, 1.0, 0.0), Budget(max_extent_m=1.5, max_mass_kg=1000.0))
    footprint = g.regions["table"].footprint
    low, high = footprint.bounds_m
    assert low == (1.0, 1.0, 0.0)
    assert high == pytest.approx((2.0, 1.6, 1.4))
    with pytest.raises(SpecRejected, match=r"too large: 1\.40 m across"):  # the tallest axis, not the first
        place(g, {**spec, "name": "tall"}, (0.0, 0.0, 0.0), Budget(max_extent_m=1.2, max_mass_kg=1000.0))


def test_a_later_paint_takes_cells_from_earlier_regions_and_a_refused_paint_changes_nothing(dx_m, materials):
    g = MaterialGrid.empty((1.0, 1.0, 1.0), materials, dx_m=dx_m)
    x, _, _ = g.mesh()
    left = np.broadcast_to(x < 0.6, g.shape)
    with g.writing(writer="construction"):
        g.paint(left, "wood", region="left", footprint=Footprint(((0, 0, 0), (0.6, 1, 1)), (0.3, 0.5, 0.5)))
        g.paint(np.broadcast_to(x >= 0.4, g.shape), "concrete")  # unnamed, and it overlaps "left"
    assert not (g.regions["left"].cells & np.broadcast_to(x >= 0.4, g.shape)).any()
    before = g.material.copy()
    with pytest.raises(ValueError, match="already exists"):
        g.paint(np.ones(g.shape, dtype=bool), "steel", region="left", footprint=g.regions["left"].footprint)
    assert np.array_equal(g.material, before)  # refused before anything was painted


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
def test_a_later_solid_may_not_take_space_from_a_named_solid(dx_m, materials, primitives, ok):
    scene = Scene((3.0, 3.0, 2.0), primitives)
    if ok:
        scene.build(materials, dx_m=dx_m)
    else:
        with pytest.raises(ValueError, match="overlaps the named solid crate"):
            scene.build(materials, dx_m=dx_m)


def test_a_footprints_centroid_is_volume_weighted_and_a_cylinders_is_its_middle():
    from simcore.core.scene import footprint_of  # noqa: PLC0415

    big, small = Box((0, 0, 0), (3, 1, 1), "wood"), Box((3, 0, 0), (4, 1, 1), "wood")
    assert footprint_of([big, small]).centroid_m == pytest.approx((2.0, 0.5, 0.5))  # unweighted would be 2.25
    assert Cylinder((1.0, 2.0), 0.5, (0.4, 1.6), "wood").centroid_m == (1.0, 2.0, 1.0)


def test_thermal_degradation_follows_its_closed_form_at_every_rig(spacings, materials):
    # One step of the law: integrity falls by rate * dt * (T - limit) / 100 in every cell above the limit, whatever
    # the cell size. A rate that scaled with dx (a resolution-dependent law) fails here.
    wood = materials["wood"]
    assert wood.degrade_above_c is not None
    excess, dt = 150.0, 0.5
    for dx_m in spacings:
        g = Scene((1.0, 1.0, 1.0), (Box((0, 0, 0), (1, 1, 1), "wood", "block"),)).build(materials, dx_m=dx_m)
        with g.writing(writer="construction"):
            g.temperature[:] = wood.degrade_above_c + excess
            damage.THERMAL.step(g, dt, LawInputs())
        expected = 1.0 - wood.degrade_rate_per_s_per_100c * dt * excess / 100.0
        assert g.integrity == pytest.approx(np.full(g.shape, expected), rel=1e-6), dx_m


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
def test_the_overlap_rule_judges_every_axis(dx_m, materials, later, ok):
    scene = Scene((3.0, 3.0, 2.0), (Box((0, 0, 0), (1, 1, 1), "wood", "crate"), later))
    if ok:
        scene.build(materials, dx_m=dx_m)
    else:
        with pytest.raises(ValueError, match="overlaps the named solid crate"):
            scene.build(materials, dx_m=dx_m)


def test_a_later_solid_may_fill_an_earlier_named_air_region(dx_m, materials):
    room = Box((0, 0, 0), (2, 2, 1), "air", "room")
    Scene((3.0, 3.0, 2.0), (room, Box((0.5, 0.5, 0), (1, 1, 0.5), "wood", "crate"))).build(materials, dx_m=dx_m)


def test_an_imagined_object_may_not_sit_in_a_named_solids_footprint(dx_m, materials):
    wall = Box((1.0, 0.0, 0.0), (1.6, 3.0, 2.0), "concrete", "wall")
    doorway = Box((1.0, 1.0, 0.0), (1.6, 2.0, 2.0), "air", "doorway")
    g = Scene((3.0, 3.0, 2.0), (wall, doorway)).build(materials, dx_m=dx_m)
    box = {"name": "box", "primitives": [{"min_m": [0, 0, 0], "max_m": [0.4, 0.4, 0.4], "material": "wood"}]}
    with pytest.raises(SpecRejected, match="that space belongs to 'wall'"):
        place(g, box, (1.1, 1.3, 0.0))  # in the doorway's air, inside the wall's footprint
    place(g, box, (2.0, 1.3, 0.0))  # beside the wall is fine
    assert "box" in g.regions


def test_thermal_degradation_is_proportional_to_the_excess(spacings, materials):
    wood = materials["wood"]
    assert wood.degrade_above_c is not None
    for dx_m in spacings:
        g = Scene((1.0, 1.0, 1.0), (Box((0, 0, 0), (1, 1, 1), "wood", "block"),)).build(materials, dx_m=dx_m)
        x, _, _ = g.mesh()
        excess = np.where(np.broadcast_to(x < 0.5, g.shape), 150.0, 50.0)
        with g.writing(writer="construction"):
            g.temperature[:] = wood.degrade_above_c + excess
            damage.THERMAL.step(g, 0.5, LawInputs())
        expected = 1.0 - wood.degrade_rate_per_s_per_100c * 0.5 * excess / 100.0
        assert g.integrity == pytest.approx(expected, rel=1e-6), dx_m


@pytest.mark.parametrize("name", ["Crate", "CRATE", "crAte"])
def test_an_imagined_object_named_like_an_existing_region_is_refused_before_painting(dx_m, materials, name):
    g = Scene((3.0, 3.0, 2.0), (Box((0.2, 0.2, 0), (0.8, 0.8, 0.6), "wood", "crate"),)).build(materials, dx_m=dx_m)
    before = g.material.copy()
    box = {"name": name, "primitives": [{"min_m": [0, 0, 0], "max_m": [0.4, 0.4, 0.4], "material": "wood"}]}
    with pytest.raises(SpecRejected, match="something called 'crate' already exists"):
        place(g, box, (2.0, 2.0, 0.0))
    assert np.array_equal(g.material, before)  # refused, not half-applied


def test_name_region_itself_refuses_a_name_maxim_would_confuse(dx_m, materials):
    # Its callers check first; this is the second line, for any future caller that doesn't.
    g = Scene((3.0, 3.0, 2.0), (Box((0.2, 0.2, 0), (0.8, 0.8, 0.6), "wood", "crate"),)).build(materials, dx_m=dx_m)
    footprint = g.regions["crate"].footprint
    with pytest.raises(ValueError, match=r"region 'Crate' already exists \(as 'crate'\)"):
        g.name_region("Crate", g.regions["crate"].cells, footprint, solid=True)


def test_an_imagined_object_may_sit_in_a_named_air_room_but_no_primitive_may_enter_a_solids_footprint(dx_m, materials):
    room = Box((0.0, 0.0, 0.0), (3.0, 3.0, 2.0), "air", "room")
    crate = Cylinder((2.3, 2.3), 0.3, (0.0, 0.6), "wood", "crate")  # its box's corners are empty space
    g = Scene((3.0, 3.0, 2.0), (room, crate)).build(materials, dx_m=dx_m)
    box = {"name": "box", "primitives": [{"min_m": [0, 0, 0], "max_m": [0.4, 0.4, 0.4], "material": "wood"}]}
    place(g, box, (0.2, 0.2, 0.0))  # inside the air room is fine
    two = {
        "name": "two",
        "primitives": [
            {"min_m": [0, 0, 0], "max_m": [0.2, 0.2, 0.2], "material": "wood"},
            {"min_m": [1.0, 1.0, 0], "max_m": [1.08, 1.08, 0.2], "material": "wood"},  # in the box's empty corner
        ],
    }
    with pytest.raises(SpecRejected, match="that space belongs to 'crate'"):
        place(g, two, (1.0, 1.0, 0.0))


def test_paint_refuses_a_confusable_name_before_painting(dx_m, materials):
    g = MaterialGrid.empty((1.0, 1.0, 1.0), materials, dx_m=dx_m)
    x, _, _ = g.mesh()
    footprint = Footprint(((0, 0, 0), (0.5, 1, 1)), (0.25, 0.5, 0.5))
    with g.writing(writer="construction"):
        g.paint(np.broadcast_to(x < 0.5, g.shape), "wood", region="crate", footprint=footprint)
    before = g.material.copy()
    with pytest.raises(ValueError, match="already exists"):
        g.paint(np.ones(g.shape, dtype=bool), "steel", region="Crate", footprint=footprint)
    assert np.array_equal(g.material, before)


# -- closed schemas: every loader refuses a key it doesn't know, at every level (B12) ----------------------------------

RIG_FILE = "version: 1\nname: t\n"


@pytest.mark.parametrize(
    ("text", "message"),
    [
        (RIG_FILE + "cell_size_m: 0.1\n", r"unknown key\(s\) \['cell_size_m'\]"),  # physics left the rig (D20)
        (RIG_FILE + "name: u\n", "repeated key"),  # the second value would silently win
        ("- name: t\n", "rig profile .* must be a mapping"),
        ("name: [\n", "not valid YAML"),
    ],
)
def test_a_rig_file_refuses_unknown_and_repeated_keys(tmp_path, text, message):
    path = tmp_path / "t.yaml"
    path.write_text(text)
    with pytest.raises(ValueError, match=message):
        RigProfile.load(path)


def _material_file(tmp_path, edit):
    raw = yaml.safe_load((DATA / "materials" / "core.yaml").read_text())
    edit(raw)
    path = tmp_path / "core.yaml"
    path.write_text(yaml.safe_dump(raw))
    return path


def test_a_material_file_refuses_a_repeated_key(tmp_path):
    text = (DATA / "materials" / "core.yaml").read_text()
    path = tmp_path / "core.yaml"
    path.write_text(text.replace("  wood:\n", "  wood:\n    id: 99\n", 1))
    with pytest.raises(ValueError, match="repeated key"):
        load_materials(path)


BOX_RAW = {"kind": "box", "min_m": [0, 0, 0], "max_m": [0.5, 0.5, 0.5], "material": "wood", "name": "crate"}
CYLINDER_RAW = {"kind": "cylinder", "center_xy_m": [0.5, 0.5], "radius_m": 0.2, "z_m": [0, 1], "material": "wood"}


def test_a_scene_accepts_every_key_it_knows():
    spawn = {"name": "runner", "archetype": "human", "holding": "torch", "at_m": [0.5, 0.5, 0.0]}
    scene = Scene.from_dict({**SCENE_RAW, "primitives": [BOX_RAW, CYLINDER_RAW], "ambient_c": 25.0, "spawns": [spawn]})
    assert [p.kind for p in scene.primitives] == ["box", "cylinder"]
    assert scene.ambient_c == 25.0
    assert scene.spawns == (Spawn("runner", "human", (500, 500, 0), "torch"),)


@pytest.mark.parametrize(
    ("spec", "message"),
    [
        # A provenance or licence field the reader doesn't know must not vanish silently.
        ({"name": "crate", "primitives": [BOX_RAW], "licence": "cc-by"}, r"unknown key\(s\) \['licence'\]"),
        ({"name": "crate", "primitves": [BOX_RAW]}, r"unknown key\(s\) \['primitves'\]"),
        (
            {"name": "crate", "primitives": [{**BOX_RAW, "colour": "red"}]},
            r"malformed spec: primitives\[0\] \(box\): unknown",
        ),
    ],
)
def test_an_imagined_object_refuses_unknown_keys(dx_m, materials, spec, message):
    g = Scene((3.0, 3.0, 2.0)).build(materials, dx_m=dx_m)
    with pytest.raises(SpecRejected, match=message):
        place(g, spec, (1.0, 1.0, 0.0))
    assert not g.regions  # refused before anything was painted


@pytest.mark.parametrize("kind", [["box"], {}, 3, None])
def test_a_primitive_kind_that_is_not_a_name_is_refused_not_crashed_on(kind):
    with pytest.raises(ValueError, match="unknown kind"):
        Scene.from_dict({**SCENE_RAW, "primitives": [{**BOX_RAW, "kind": kind}]})


def test_a_rig_file_refuses_a_missing_key_by_name(tmp_path):
    path = tmp_path / "t.yaml"
    path.write_text("version: 1\n")
    with pytest.raises(ValueError, match=r"missing key\(s\) \['name'\]"):
        RigProfile.load(path)


def test_a_material_without_its_optional_degradation_keys_loads(tmp_path):
    def edit(raw):
        del raw["materials"]["wood"]["degrade_above_c"], raw["materials"]["wood"]["degrade_rate_per_s_per_100c"]

    table = load_materials(_material_file(tmp_path, edit))
    assert table["wood"].degrade_above_c is None
    assert table["wood"].degrade_rate_per_s_per_100c == 0.0


def test_the_material_schema_names_every_field_the_reader_fills():
    from simcore.core.materials import Material  # noqa: PLC0415

    assert {f.name for f in dataclasses.fields(Material)} - {"name"} == MATERIAL_REQUIRED | MATERIAL_OPTIONAL
    assert not MATERIAL_REQUIRED & MATERIAL_OPTIONAL


def test_every_optional_material_key_is_read_not_just_accepted(tmp_path):
    def edit(raw):
        raw["materials"]["wood"].update(degrade_above_c=123.5, degrade_rate_per_s_per_100c=0.0625)

    wood = load_materials(_material_file(tmp_path, edit))["wood"]
    assert (wood.degrade_above_c, wood.degrade_rate_per_s_per_100c) == (123.5, 0.0625)


def test_a_key_cannot_be_both_required_and_optional():
    from simcore.core.checks import known_keys  # noqa: PLC0415

    with pytest.raises(TypeError, match="both required and optional"):
        known_keys({}, "x", required={"a"}, optional={"a", "b"})


@pytest.mark.parametrize("load", [RigProfile.load, load_materials, load_action_limits])
def test_a_data_file_nested_too_deeply_is_refused_with_its_name(tmp_path, load):
    path = tmp_path / "deep.yaml"
    path.write_text("x: " + "[" * 5000 + "]" * 5000 + "\n")
    with pytest.raises(ValueError, match=r"deep\.yaml: nested too deeply"):
        load(path)


class _OddMapping(dict[str, object]):  # a Python caller's mapping with a key no YAML or JSON could produce
    def __iter__(self):
        yield ["unhashable"]


def test_an_imagined_object_with_an_unhashable_key_is_refused_not_crashed_on(dx_m, materials):
    g = Scene((3.0, 3.0, 2.0)).build(materials, dx_m=dx_m)
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
    # A refusal is expected for most inputs, and it is a coded one (WT-S1): a plain ValueError, a KeyError or a
    # TypeError fails the test.
    with contextlib.suppress(Refused):
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
    dx_m, materials, spec, origin
):
    # A named wall, so the occupied, namesake and footprint refusals are reachable too.
    g = Scene((3.0, 3.0, 2.0), (Box((0.0, 0.0, 0.0), (0.6, 3.0, 2.0), "concrete", "wall"),)).build(materials, dx_m=dx_m)
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
    (RigProfile.load, DATA / "rigs" / "rig.yaml"),
    (load_materials, DATA / "materials" / "core.yaml"),
    (load_action_limits, DATA / "world" / "actions.yaml"),
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
        with contextlib.suppress(Refused):  # coded, or the test fails
            load(file)


@settings(max_examples=150, deadline=None)
@given(raw=_json | st.dictionaries(st.text(max_size=20), _json, max_size=6), as_yaml=st.booleans(), text=st.text())
def test_every_data_loader_loads_or_refuses_any_file(tmp_path_factory, raw, as_yaml, text):
    path = tmp_path_factory.mktemp("fuzz") / "f.yaml"
    path.write_text(yaml.safe_dump(raw) if as_yaml else text)
    for load in (RigProfile.load, load_materials, load_action_limits):
        with contextlib.suppress(Refused):  # coded, or the test fails
            load(path)


# -- format versions: every data format names its version, and a reader refuses one it doesn't know (B21) --------------

ROOT = Path(__file__).resolve().parents[1]


# Rig format v1 (D20): 0 is the retired physics format, refused by version and never migrated.


def test_every_shipped_data_file_is_at_its_formats_current_version():

    # Each data directory has one reader and one format; a file in a directory no reader owns is an error, so a new
    # kind of data file can't ship without a version and a loader.
    readers: dict[str, tuple[Callable[[Path], object], int]] = {
        "rigs": (RigProfile.load, RIG_PROFILE.version),
        "materials": (load_materials, MATERIAL_TABLE.version),
        "world": (load_action_limits, ACTION_LIMITS.version),
    }
    # The files git tracks, not whatever is on disk: a Finder .DS_Store is not a data file.
    listed = git(ROOT, "ls-files", "data").stdout
    files = [ROOT / line for line in listed.splitlines()]
    assert files
    for path in files:
        kind = path.relative_to(DATA).parts[0]
        assert kind in readers, f"{path}: no reader owns data/{kind}/"
        load, version = readers[kind]
        assert path.suffix == ".yaml", path
        shipped = yaml.safe_load(path.read_text())["version"]
        assert type(shipped) is int, path  # False == 0, but false is not version 0
        assert shipped == version, path
        load(path)


@pytest.mark.parametrize(
    ("load", "fixture"),
    [(load_materials, "core.yaml"), (load_action_limits, "actions.yaml")],
)
def test_the_committed_v0_files_still_load(load, fixture):
    # Golden files at version 0. When a format moves on, its reader must still load these (a migration) or refuse
    # them loudly for their version; they are never rewritten to match. Loading must also read every value: today a
    # v0 file loads to exactly what the shipped file does, and after a bump this compares with what migration gives.
    golden = load(Path(__file__).parent / "fixtures" / "formats" / "v0" / fixture)
    shipped = load(
        {
            "core.yaml": DATA / "materials" / "core.yaml",
            "actions.yaml": DATA / "world" / "actions.yaml",
        }[fixture]
    )
    if isinstance(golden, MaterialTable):
        assert isinstance(shipped, MaterialTable)
        assert golden.by_name == shipped.by_name
    else:
        assert golden == shipped


def test_the_committed_v0_rig_file_is_refused_by_version_not_migrated():
    # Rig format v0 carried physics (cell_size_m, min_substeps_per_turn). Under D20 it is a dead format: its golden
    # stays committed, and the reader refuses it loudly for its version, saying what moved. The golden's own header
    # still names test_the_committed_v0_files_still_load: goldens are never edited, so this test is its holder now.
    with pytest.raises(ValueError, match=r"rig profile .* version must be 1, got 0: .*left the rig.*dx_m"):
        RigProfile.load(Path(__file__).parent / "fixtures" / "formats" / "v0" / "rig.yaml")


def test_the_committed_v1_rig_file_still_loads():
    golden = RigProfile.load(Path(__file__).parent / "fixtures" / "formats" / "v1" / "rig.yaml")
    assert golden == data.rig_profile("rig")


def _newer(text: str) -> str:
    """A file from a future version: its version bumped, and a field that version added."""
    for now in (1, 0):  # the rig format is at 1, the others at 0
        if f"version: {now}" in text:
            return text.replace(f"version: {now}", f"version: {now + 1}", 1) + "added_in_next: true\n"
    raise AssertionError("no version line")


@pytest.mark.parametrize(
    ("load", "source", "message"),
    [
        (RigProfile.load, DATA / "rigs" / "rig.yaml", "rig profile .* version must be 1, got 2"),
        (load_materials, DATA / "materials" / "core.yaml", "material table .* version must be 0, got 1"),
        (load_action_limits, DATA / "world" / "actions.yaml", "action limits .* version must be 0, got 1"),
    ],
)
def test_a_file_from_a_newer_format_is_refused_for_its_version_not_its_new_fields(tmp_path, load, source, message):
    path = tmp_path / source.name
    path.write_text(_newer(source.read_text()))
    with pytest.raises(ValueError, match=message):
        load(path)


def test_a_scene_from_a_newer_format_is_refused_for_its_version_not_its_new_fields():
    with pytest.raises(ValueError, match="scene version must be 1, got 2"):
        Scene.from_dict({**SCENE_RAW, "version": 2, "added_in_v2": True})


@pytest.mark.parametrize(
    ("listed", "message"),
    [
        ("box", "primitives must be a list"),
        ({"kind": "box"}, "primitives must be a list"),
        ([7], r"primitives\[0\] must be a mapping"),
        ([{"kind": ["box"]}], "unknown kind"),
        ([{"kind": "box", "material": "wood"}], "missing key"),
    ],
)
def test_primitives_from_data_refuses_every_malformed_list(listed, message):
    from simcore.core.scene import primitives_from_data  # noqa: PLC0415

    with pytest.raises(ValueError, match=message):
        primitives_from_data(listed)


def test_the_directory_gate_names_every_candidate_it_refused(tmp_path):
    from simcore.adapters.loaders import existing_directory  # noqa: PLC0415

    (tmp_path / "a_file").write_text("x")
    with pytest.raises(FileNotFoundError, match=r"thing: none of .*missing, .*a_file is a directory"):
        existing_directory(tmp_path, ["missing", "a_file"], "thing")
    found = existing_directory(tmp_path / "a" / "..", ["."], "thing")  # resolved: '..' is arithmetic the gate does
    assert isinstance(found, DataPath)  # never a pathlib.Path (step 3b(b) delta review, D1)
    assert str(found) == str(tmp_path.resolve())


def test_a_symlinked_package_finds_the_data_beside_the_real_package(tmp_path):
    # Delta round 6, Executor N-h. The intended behaviour: data is found beside the package's real location, so the
    # gate resolves the package before it joins a candidate; a symlinked data directory resolves too.
    from simcore.adapters.loaders import existing_directory  # noqa: PLC0415

    real = tmp_path / "checkout" / "src" / "maxim_overdrive"
    real.mkdir(parents=True)
    (tmp_path / "checkout" / "data").mkdir()
    link = tmp_path / "site" / "maxim_overdrive"
    link.parent.mkdir()
    link.symlink_to(real, target_is_directory=True)
    assert str(data.data_dir(link)) == str((tmp_path / "checkout" / "data").resolve())  # not site/../data
    data_link = tmp_path / "data_link"
    data_link.symlink_to(tmp_path / "checkout" / "data", target_is_directory=True)
    assert str(existing_directory(tmp_path, ["data_link"], "x")) == str((tmp_path / "checkout" / "data").resolve())


def test_a_data_file_is_a_regular_file_never_a_device_or_a_pipe(tmp_path):
    """Delta D3: /dev/zero (and a FIFO) report 0 bytes, so a stat-only budget passed and read_bytes never ended."""
    import os  # noqa: PLC0415

    to_zero = tmp_path / "zero.yaml"
    to_zero.symlink_to("/dev/zero")
    pipe = tmp_path / "pipe.yaml"
    os.mkfifo(pipe)
    import threading  # noqa: PLC0415

    def refused(path):
        with pytest.raises(Refused, match="not a regular file") as caught:
            read_yaml(path)
        return caught.value.code

    for path in (to_zero, pipe, tmp_path):
        # On a deadline: a FIFO opened without O_NONBLOCK blocks forever, which would stall the gate, not fail it
        # (delta round 4, R4-9).
        codes: list[RefusalCode] = []
        reader = threading.Thread(target=lambda p=path, out=codes: out.append(refused(p)), daemon=True)
        reader.start()
        reader.join(timeout=10)
        assert not reader.is_alive(), f"{path}: the gate blocked on it"
        assert codes == [RefusalCode.BAD_SHAPE]


# -- the file gate refuses what PyYAML's constructors can't build (step 3b(b) review, Trust T1-S1, Executor S2) ------


@pytest.mark.parametrize(
    "text",
    [
        "version: " + "9" * 5000 + "\n",  # int() past CPython's 4,300-digit limit
        "version: 2020-13-45\n",
        "version: 2001-02-29\n",
        "k: 2026-01-01 25:00:00\n",
        "k: !!int x\n",
        "k: !!float x\n",
        "k: !!timestamp x\n",
        "k: !!bool maybe\n",
    ],
)
def test_a_value_yaml_cannot_build_is_a_coded_refusal_that_names_the_file(tmp_path, text):
    path = tmp_path / "bad.yaml"
    path.write_text(text)
    with pytest.raises(Refused, match=r"bad\.yaml") as caught:
        read_yaml(path)
    assert caught.value.code is RefusalCode.BAD_SHAPE


def test_a_data_file_is_utf8_whatever_the_machines_locale(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_bytes(b"version: 0\nname: \xff\xfe\n")
    with pytest.raises(Refused, match="not UTF-8") as caught:
        read_yaml(path)
    assert caught.value.code is RefusalCode.BAD_SHAPE
    path.write_bytes("name: Zoë\n".encode())
    assert read_yaml(path) == {"name": "Zoë"}


def test_a_data_file_over_its_byte_budget_is_refused_before_it_is_read(tmp_path, monkeypatch):
    from simcore.adapters import loaders  # noqa: PLC0415

    path = tmp_path / "big.yaml"
    path.write_text("a: [1, 2, 3]\n")  # 13 bytes
    monkeypatch.setattr(loaders, "MAX_FILE_BYTES", 12)
    with pytest.raises(Refused, match="larger than 12 bytes") as caught:
        read_yaml(path)
    assert caught.value.code is RefusalCode.OVER_BUDGET
    monkeypatch.setattr(loaders, "MAX_FILE_BYTES", 13)
    assert read_yaml(path) == {"a": [1, 2, 3]}


# -- step 3b(b) delta round 2 folds ------------------------------------------------------------------------------


def test_a_data_path_holds_no_path_to_reach_past_the_gate():
    """Delta 2, N1: ``(data_dir() / 'core.yaml')._path.open()`` read a data file past the strict YAML gate."""
    where = data.data_dir() / "materials" / "core.yaml"
    with pytest.raises(AttributeError):
        where._path  # type: ignore[attr-defined]  # noqa: B018 - the point: there is no such attribute
    assert not hasattr(where, "__dict__")


def test_an_unreadable_data_file_is_a_coded_refusal(tmp_path):
    """Delta 2, N4's neighbour: a mode-000 file raised an uncoded PermissionError."""
    path = tmp_path / "locked.yaml"
    path.write_text("a: 1\n")
    path.chmod(0)
    try:
        with pytest.raises(Refused, match="can't be read") as caught:
            read_yaml(path)
        assert caught.value.code is RefusalCode.BAD_SHAPE
    finally:
        path.chmod(0o600)


def test_a_data_file_is_read_no_further_than_its_budget(tmp_path, monkeypatch):
    """Delta 2, N7: the refusal alone could not tell a bounded read from an unbounded one; the read's size can."""
    import os  # noqa: PLC0415

    from simcore.adapters import loaders  # noqa: PLC0415

    asked: list[int] = []
    real_fdopen = os.fdopen

    class Spy:
        def __init__(self, handle):
            self._handle = handle

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            self._handle.close()

        def read(self, n=-1):
            asked.append(n)
            return self._handle.read(n)

    monkeypatch.setattr(os, "fdopen", lambda fd, mode: Spy(real_fdopen(fd, mode)))  # the gate's own os.fdopen
    monkeypatch.setattr(loaders, "MAX_FILE_BYTES", 12)
    path = tmp_path / "big.yaml"
    path.write_text("a: " + "1" * 100 + "\n")
    with pytest.raises(Refused, match="larger than 12 bytes"):
        read_yaml(path)
    assert asked == [13]


def test_a_data_directory_candidate_is_relative_to_the_package():
    """Delta 2, N8: an absolute candidate replaced the base."""
    from simcore.adapters.loaders import existing_directory  # noqa: PLC0415

    with pytest.raises(TypeError, match="relative to the package"):
        existing_directory(DATA, ["/etc"], "x")


# -- step 3b(b) delta round 3 folds ------------------------------------------------------------------------------


def test_only_the_gate_makes_a_data_path_and_a_copy_is_the_same_place():
    """Round 3, R3-6: DataPath() and copy.copy(h) made handles with no path, which failed later with a bare KeyError."""
    import copy  # noqa: PLC0415

    with pytest.raises(TypeError, match="made by the file gate"):
        DataPath(object())
    where = data.data_dir() / "materials"
    assert copy.copy(where) is where
    assert copy.deepcopy(where) is where
    assert str(copy.deepcopy(where) / "core.yaml") == str(DATA / "materials" / "core.yaml")


def test_a_path_with_a_nul_is_a_coded_refusal(tmp_path):
    """Round 3, R3-10: an embedded NUL raised a bare ValueError from os.open."""
    with pytest.raises(Refused, match="not a file name") as caught:
        read_yaml(str(tmp_path / "a\x00b.yaml"))
    assert caught.value.code is RefusalCode.BAD_NAME
