"""Validation lives in constructors, frozen means deep, budgets come before allocation, echo is bounded.

Boundaries §5.1: holding an instance is proof it is valid, so each type refuses an invalid value whoever builds it.
§5.4: a gate checks its budgets before it allocates, and every value it echoes goes through ``checks.shown``.
"""

from __future__ import annotations

import dataclasses
import math
from typing import Any

import numpy as np
import pytest

from maxim_overdrive import data
from simcore.core.applier import Applier
from simcore.core.checks import finite_real, finite_vector, format_version, known_keys, shown, whole_number
from simcore.core.imagination import Budget, SpecRejected, place
from simcore.core.intents import Extinguish, Ignite, Strike
from simcore.core.materials import MaterialTable
from simcore.core.scene import Box, Scene
from simcore.core.world import World
from simcore.protocol.tiers import RigProfile

LIMITS = data.action_limits()
MATERIALS = data.materials()
WOOD = MATERIALS["wood"]


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"density_kg_m3": 0.0}, "density_kg_m3 must be positive"),  # it divides: rho*cp
        ({"specific_heat_j_kgk": -1.0}, "specific_heat_j_kgk must be positive"),
        ({"conductivity_w_mk": -0.1}, "conductivity_w_mk must be non-negative"),
        ({"fracture_energy_j_m3": -1.0}, "fracture_energy_j_m3 must be non-negative"),
        ({"degrade_rate_per_s_per_100c": -1.0}, "degrade_rate_per_s_per_100c must be non-negative"),
        ({"density_kg_m3": math.nan}, "density_kg_m3 must be a finite number"),
        ({"degrade_above_c": math.inf}, "degrade_above_c must be a finite number"),
        ({"id": 256}, r"id must fit in uint8 \(0 to 255\), got 256"),
        ({"id": -1}, "id must fit in uint8"),
        ({"id": 1.5}, "id must be a whole number"),
        ({"name": ""}, "a material needs a name"),
        ({"color_rgb": (0, 0, 256)}, "color_rgb must be three values from 0 to 255"),
        ({"color_rgb": (0, 0)}, "color_rgb must be three values from 0 to 255"),
        ({"color_rgb": "red"}, "color_rgb must be three values from 0 to 255"),
    ],
)
def test_a_material_refuses_what_no_physics_can_use(change, message):
    with pytest.raises(ValueError, match=message):
        dataclasses.replace(WOOD, **change)


def test_a_material_table_holds_materials_by_their_own_names():
    with pytest.raises(ValueError, match="'oak' must be a Material of that name"):
        MaterialTable({**MATERIALS.by_name, "oak": WOOD})
    with pytest.raises(ValueError, match="must be a Material"):
        MaterialTable({**MATERIALS.by_name, "x": object()})  # type: ignore[dict-item]


def test_a_built_material_is_normalized_to_plain_values():
    m = dataclasses.replace(WOOD, id=np.int64(4), density_kg_m3=np.float32(600), color_rgb=[1, 2, 3])  # type: ignore[arg-type]
    assert (type(m.id), type(m.density_kg_m3), m.color_rgb) == (int, float, (1, 2, 3))


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"max_mass_kg": math.nan}, "max_mass_kg must be a finite number"),  # nan once removed the mass limit
        ({"max_mass_kg": 0.0}, "max_mass_kg must be positive"),
        ({"max_extent_m": -1.0}, "max_extent_m must be positive"),
        ({"max_primitives": 0}, "max_primitives must be at least 1"),
        ({"max_primitives": 2.5}, "max_primitives must be a whole number"),
        ({"max_name_chars": True}, "max_name_chars must be a whole number"),
    ],
)
def test_a_budget_refuses_a_limit_that_is_no_limit(kwargs, message):
    with pytest.raises(ValueError, match=message):
        Budget(**kwargs)


@pytest.mark.parametrize("name", ["", "   ", 7, None])
def test_a_rig_profile_needs_a_name(name):
    with pytest.raises(ValueError, match="a rig profile needs a name"):
        RigProfile(name)


def _grid():
    return Scene((3.0, 3.0, 2.0)).build(MATERIALS, dx_m=0.2)


def test_too_many_primitives_are_refused_before_any_is_built_or_voxelized():
    g = _grid()
    prim: dict[str, Any] = {"min_m": [0, 0, 0], "max_m": [0.01, 0.01, 0.01], "material": "wood"}
    spec = {"name": "dust", "primitives": [prim] * 1000}  # 1,000 one-centimetre boxes: once ~5 GB at max
    with pytest.raises(SpecRejected, match="too many primitives: 1000, the limit is 32"):
        place(g, spec, (1.0, 1.0, 0.0))
    assert "dust" not in g.regions
    assert place(g, {**spec, "primitives": [{**prim, "max_m": [0.2, 0.2, 0.2]}] * 32}, (1.0, 1.0, 0.0)) > 0


def test_a_name_past_its_budget_is_refused_and_never_echoed_whole():
    with pytest.raises(SpecRejected, match="name is at most 64 characters") as exc:
        place(_grid(), {"name": "x" * 10_000, "primitives": []}, (1.0, 1.0, 0.0))
    assert len(str(exc.value)) < 200


HOSTILE: list[object] = ["x" * 100_000, 10**5000, [1] * 100_000, {"k" * 1000: 1}]


@pytest.mark.parametrize("value", HOSTILE, ids=["long-str", "huge-int", "long-list", "long-key"])
def test_every_check_echoes_a_hostile_value_bounded(value):
    calls = [
        lambda: finite_real(value, "v"),
        lambda: finite_vector(value, 3, "v"),
        lambda: format_version({"version": value}, 0, "v"),
    ]
    if not isinstance(value, int):  # a huge int is a whole number, rightly
        calls.append(lambda: whole_number(value, "v"))
    for call in calls:
        with pytest.raises(ValueError, match=r"^v ") as exc:
            call()
        assert len(str(exc.value)) < 200


def test_unknown_keys_are_listed_bounded_however_many_there_are():
    with pytest.raises(ValueError, match="unknown key") as exc:
        known_keys({f"k{i}": 1 for i in range(100_000)}, "thing", required=())
    assert len(str(exc.value)) < 300
    assert "and 99992 more" in str(exc.value)
    with pytest.raises(ValueError, match=r"unknown key\(s\) \[<an integer of about"):
        known_keys({10**5000: 1}, "thing", required=())


def test_shown_bounds_length_and_survives_an_int_too_long_to_print():
    assert len(shown("x" * 10_000)) < 50
    assert shown(10**5000).startswith("<an integer of about 50")
    assert shown(12345) == "12345"


def test_a_world_needs_a_positive_finite_turn():
    grid = _grid()
    for bad in (0.0, -6.0, math.nan):
        with pytest.raises(ValueError, match="turn_seconds"):
            World(grid, bad, limits=LIMITS)


# -- stage 2: the applier's world checks ------------------------------------------------------------------------------


def _world():
    room = Box((0.0, 0.0, 0.0), (1.0, 3.0, 2.0), "air", "room")
    crate = Box((1.2, 1.2, 0), (1.8, 1.8, 0.6), "wood", "crate")
    return World.from_scene(Scene((3.0, 3.0, 2.0), (room, crate)), MATERIALS, dx_m=0.2, limits=LIMITS)


@pytest.mark.parametrize(
    ("region", "message"),
    [("door", "there is no door in this world"), ("room", "the room is air: there is no structure to act on")],
)
def test_the_applier_refuses_a_region_it_cannot_act_on_and_changes_nothing(region, message):
    w = _world()
    frame = w.frames.latest
    for action in (Strike(1.0, 0.2, None), Ignite(1.0, 0.3)):
        out = Applier(w).apply(region, action)
        assert (out.success, out.error) == (False, message)
    assert w.frames.latest is frame
    assert dict(w.sources) == {}


def test_an_outcome_reports_the_applied_values_and_is_read_only():
    out = Applier(_world()).apply("crate", Strike(1e3, 0.2, (1.5, 1.5, 0.3)))
    assert out.success
    assert dict(out.params) == {"energy_j": 1e3, "sigma_m": 0.2, "point_m": [1.5, 1.5, 0.3]}
    assert set(out.metadata) == {"destroyed_volume_m3", "absorbed_j"}
    with pytest.raises(TypeError):
        out.metadata["x"] = 1.0  # type: ignore[index]


def test_extinguish_puts_out_the_fire_it_names_and_publishes_the_change():
    w = _world()
    applier = Applier(w)
    assert applier.apply("crate", Ignite(1000.0, 0.3)).success
    lit = w.frames.latest.sequence
    out = applier.apply("crate", Extinguish())
    assert (out.success, out.error, dict(w.sources)) == (True, None, {})
    assert w.frames.latest.sequence == lit + 1
    again = applier.apply("crate", Extinguish())
    assert (again.success, again.error) == (False, "nothing is burning on the crate")


def test_the_material_table_is_read_only_by_id_too():
    assert MATERIALS.by_id[WOOD.id] is WOOD
    with pytest.raises(TypeError):
        MATERIALS.by_id[99] = WOOD  # type: ignore[index]
