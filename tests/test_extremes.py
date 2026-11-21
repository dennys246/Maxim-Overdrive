"""Extreme numbers at the geometry gates: every one becomes a refusal before any arithmetic (step 3b review, B1).

A tile is at most ``MAX_EXTENT_M`` across, so a coordinate or radius beyond it is not a shape. The primitive
constructors refuse it, so ``place`` and ``Scene.build`` never square a 1e200 m radius (which raised OverflowError
through ``place``, an LLM-facing gate). The property tests count how far their examples reach, because a fuzzer
that never builds a primitive guards nothing (the measure-fuzz-reach rule).
"""

from __future__ import annotations

import contextlib
import math
from collections import Counter
from typing import Any

import numpy as np
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from maxim_overdrive import data
from simcore.core import scene as scene_module
from simcore.core.imagination import SpecRejected, place
from simcore.core.scene import MAX_EXTENT_M, Box, Cylinder, Scene

MATERIALS = data.materials()
HUGE = [1e300, -1e300, 1e200, 1.4e154, 1e20, 2 * MAX_EXTENT_M, -2 * MAX_EXTENT_M, 10**400, 10**20]
NON_FINITE = [math.inf, -math.inf, math.nan]


def _grid():
    return Scene((3.0, 3.0, 2.0), (Box((0.0, 0.0, 0.0), (0.6, 3.0, 2.0), "concrete", "wall"),)).build(
        MATERIALS, dx_m=0.2
    )


def _cylinder(**change: Any) -> dict[str, Any]:
    raw = {"kind": "cylinder", "center_xy_m": [1.5, 1.5], "radius_m": 0.3, "z_m": [0.0, 0.5], "material": "wood"}
    return {**raw, **change}


@pytest.mark.parametrize("value", HUGE + NON_FINITE, ids=repr)
@pytest.mark.parametrize("field", ["radius_m", "center_xy_m", "z_m"])
def test_an_extreme_cylinder_number_is_refused_by_place(field, value):
    # radius_m=1e200 raised OverflowError from Cylinder.mask before the fix.
    change = {"radius_m": value} if field == "radius_m" else {field: [value, 0.5]}
    g = _grid()
    before = g.material.copy()
    with pytest.raises(SpecRejected):
        place(g, {"name": "c", "primitives": [_cylinder(**change)]}, (0.0, 0.0, 0.0))
    assert np.array_equal(g.material, before)


@pytest.mark.parametrize("value", HUGE + NON_FINITE, ids=repr)
def test_an_extreme_box_corner_or_origin_is_refused_by_place(value):
    box = {"min_m": [0.0, 0.0, 0.0], "max_m": [value, 0.5, 0.5], "material": "wood"}
    with pytest.raises(SpecRejected):
        place(_grid(), {"name": "b", "primitives": [box]}, (1.0, 1.0, 0.0))
    small = {"min_m": [0.0, 0.0, 0.0], "max_m": [0.4, 0.4, 0.4], "material": "wood"}
    with pytest.raises(SpecRejected):
        place(_grid(), {"name": "b", "primitives": [small]}, (value, 1.0, 0.0))


@pytest.mark.parametrize("value", [*HUGE, *NON_FINITE, -0.0])
def test_the_primitive_constructors_refuse_a_number_that_is_no_shape(value):
    if value == 0.0:  # negative zero is a coordinate like any other, and a radius of it is refused
        Box((value, 0.0, 0.0), (1.0, 1.0, 1.0), "wood")
        with pytest.raises(ValueError, match="radius"):
            Cylinder((0.0, 0.0), value, (0.0, 1.0), "wood")
        return
    with pytest.raises(ValueError, match="max_m"):
        Box((0.0, 0.0, 0.0), (value, 1.0, 1.0), "wood")
    with pytest.raises(ValueError, match="radius"):
        Cylinder((0.0, 0.0), value, (0.0, 1.0), "wood")
    with pytest.raises(ValueError, match="center_xy_m"):
        Cylinder((value, 0.0), 0.5, (0.0, 1.0), "wood")


def test_an_extreme_authored_cylinder_is_refused_when_the_scene_is_read():
    raw = {"version": 0, "extent_m": [3.0, 3.0, 2.0], "primitives": [_cylinder(radius_m=1e200)]}
    with pytest.raises(ValueError, match="radius_m"):
        Scene.from_dict(raw)


# -- property tests over the whole number line, with their reach counted ----------------------------------------------

_any_number = (
    st.sampled_from([*HUGE, *NON_FINITE, -0.0, 0.0])
    | st.floats()
    | st.floats(-3.0, 3.0)
    | st.integers()
    | st.integers(-3, 3)
)
_triple = st.lists(_any_number, min_size=3, max_size=3)
_good_cylinder = {"kind": "cylinder", "center_xy_m": [1.5, 1.5], "radius_m": 0.3, "z_m": [0.0, 0.5], "material": "wood"}
_good_box = {"min_m": [1.2, 1.2, 0.0], "max_m": [1.6, 1.6, 0.4], "material": "steel"}


@st.composite
def _primitive(draw: st.DrawFn) -> dict[str, Any]:
    """A valid primitive with none, one or every number replaced by one from the whole number line, so examples
    reach both the constructor's refusals and, when they pass, the voxelizer."""
    raw: dict[str, Any] = dict(draw(st.sampled_from([_good_cylinder, _good_box])))
    numeric = [k for k in raw if k not in ("kind", "material")]
    for key in draw(st.sampled_from([[], *[[k] for k in numeric], numeric])):
        if isinstance(raw[key], list):
            raw[key] = [draw(_any_number) for _ in raw[key]]
        else:
            raw[key] = draw(_any_number)
    return raw


@pytest.fixture
def reach(monkeypatch):
    """Counts how far examples get: constructed primitives, and masks computed (the arithmetic B1 crashed in)."""
    counts: Counter[str] = Counter()
    for cls in (Box, Cylinder):
        post, mask = cls.__post_init__, cls.mask

        def counted_post(self, post=post):
            counts["constructed"] += counts["on"]
            post(self)
            counts["valid"] += counts["on"]

        def counted_mask(self, grid, mask=mask):
            counts["masked"] += counts["on"]
            return mask(self, grid)

        monkeypatch.setattr(cls, "__post_init__", counted_post)
        monkeypatch.setattr(cls, "mask", counted_mask)
    return counts


def test_an_imagined_object_with_any_numbers_is_placed_or_refused(reach):
    @settings(max_examples=400, deadline=None, derandomize=True, suppress_health_check=[HealthCheck.too_slow])
    @given(prims=st.lists(_primitive(), min_size=1, max_size=2), origin=st.just([0.0, 0.0, 0.0]) | _triple)
    def run(prims, origin):
        g = _grid()  # its own wall is not counted
        before = g.material.copy()
        reach["examples"] += 1
        reach["on"] = 1
        try:
            place(g, {"name": "thing", "primitives": prims}, origin)
        except SpecRejected:
            assert np.array_equal(g.material, before)
        finally:
            reach["on"] = 0

    run()
    # Measured reach (2026-11-20): every example builds a primitive; about half are valid shapes; masks are computed
    # for the ones that pass the analytic budgets. The floors keep the fuzzer from drifting back to junk.
    assert reach["constructed"] >= reach["examples"]
    assert reach["valid"] >= 0.2 * reach["examples"], reach
    assert reach["masked"] >= 0.02 * reach["examples"], reach


def test_a_scene_with_any_numbers_is_built_or_refused(reach):
    @settings(max_examples=300, deadline=None, derandomize=True, suppress_health_check=[HealthCheck.too_slow])
    @given(prims=st.lists(_primitive(), min_size=1, max_size=2))
    def run(prims):
        reach["examples"] += 1
        reach["on"] = 1
        with contextlib.suppress(ValueError):
            Scene.from_dict({"version": 0, "extent_m": [3.0, 3.0, 2.0], "primitives": prims}).build(MATERIALS, dx_m=0.2)
        reach["on"] = 0

    run()
    assert reach["constructed"] >= reach["examples"]
    assert reach["valid"] >= 0.2 * reach["examples"], reach
    assert reach["masked"] >= 0.1 * reach["examples"], reach


def test_reach_is_reported(reach, capsys):
    """Not a check: prints the reach of one run, for the fold's record (pytest -s)."""
    test_an_imagined_object_with_any_numbers_is_placed_or_refused(reach)
    with capsys.disabled():
        n = reach["examples"]
        print(f"\nreach: {dict(reach)}; valid {reach['valid'] / n:.0%}, masked {reach['masked'] / n:.0%} per example")
    assert scene_module.MAX_EXTENT_M == MAX_EXTENT_M
