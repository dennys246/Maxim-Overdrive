"""The SEM ``structure`` modulator is a trust boundary: an NPC's tool call, an LLM's output and (from Phase 1 step 2)
a client's ``act`` intent all reach the world through it. Every refusal leaves the world exactly as it was, and no
input, however malformed, crashes it or puts a non-finite number into the grid.

The bad values below are the probes the 2026-11-15 design review ran against the committed modulator
(docs/design/reviews/realtime_lanes_coop/trust_boundary.md TB-1, executor.md X7).
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from maxim_overdrive import Box, RigProfile, Scene, World
from maxim_overdrive.config import ActionLimits
from maxim_overdrive.sem_env.bridge import ActionRefused, Extinguish, Ignite, Strike, parse_action, region_parts
from maxim_overdrive.world import damage
from maxim_overdrive.world.world import HeatSource

SCENE = Scene((3.0, 3.0, 2.0), (Box((1.2, 1.2, 0), (1.8, 1.8, 0.6), "wood", "crate"),))


def _world(materials):
    return World.from_scene(SCENE, RigProfile.load("laptop"), materials)


def _structure(world, limits):
    _, mods = region_parts(world, "crate", limits=limits)
    return mods["structure"]


def _state(world):
    g = world.grid
    return (g.material.copy(), g.integrity.copy(), g.temperature.copy(), dict(world.sources))


def _unchanged(before, world):
    after = _state(world)
    return (
        all(np.array_equal(a, b, equal_nan=True) for a, b in zip(before[:3], after[:3], strict=True))
        and before[3] == after[3]
    )


BAD = [
    # ignite: power
    ("ignite", {"power_w": math.nan}, "power_w"),
    ("ignite", {"power_w": math.inf}, "power_w"),
    ("ignite", {"power_w": -1e9}, "power_w"),
    ("ignite", {"power_w": 1e300}, "power_w"),
    ("ignite", {"power_w": "inf"}, "power_w"),
    ("ignite", {"power_w": "500000"}, "power_w"),
    ("ignite", {"power_w": True}, "power_w"),
    ("ignite", {"power_w": 10**400}, "power_w"),
    ("ignite", {}, "power_w"),
    # ignite: radius
    ("ignite", {"power_w": 1000.0, "radius_m": -0.3}, "radius_m"),
    ("ignite", {"power_w": 1000.0, "radius_m": 0.0}, "radius_m"),
    ("ignite", {"power_w": 1000.0, "radius_m": math.nan}, "radius_m"),
    ("ignite", {"power_w": 1000.0, "radius_m": 50.0}, "radius_m"),
    ("ignite", {"power_w": 1000.0, "radius_m": None}, "radius_m"),
    ("ignite", {"power_w": 1000.0, "colour": "red"}, "colour"),
    # strike: energy
    ("strike", {"energy_j": math.nan}, "energy_j"),
    ("strike", {"energy_j": math.inf}, "energy_j"),
    ("strike", {"energy_j": "inf"}, "energy_j"),
    ("strike", {"energy_j": -5.0}, "energy_j"),
    ("strike", {"energy_j": 1e300}, "energy_j"),
    ("strike", {}, "energy_j"),
    # strike: width
    ("strike", {"energy_j": 1e5, "sigma_m": math.nan}, "sigma_m"),
    ("strike", {"energy_j": 1e5, "sigma_m": 0.0}, "sigma_m"),
    ("strike", {"energy_j": 1e5, "sigma_m": -0.1}, "sigma_m"),
    ("strike", {"energy_j": 1e5, "sigma_m": 100.0}, "sigma_m"),
    # strike: point
    ("strike", {"energy_j": 1e5, "point_m": [1.0]}, "point_m"),
    ("strike", {"energy_j": 1e5, "point_m": [1.0, 1.0]}, "point_m"),
    ("strike", {"energy_j": 1e5, "point_m": [math.nan, 1.0, 1.0]}, "point_m"),
    ("strike", {"energy_j": 1e5, "point_m": [True, 1.0, 1.0]}, "point_m"),
    ("strike", {"energy_j": 1e5, "point_m": "abc"}, "point_m"),
    ("strike", {"energy_j": 1e5, "point_m": [1, 2, 3, 4]}, "point_m"),
    ("strike", {"energy_j": 1e5, "force": 3}, "force"),
    # extinguish takes nothing
    ("extinguish", {"all": True}, "all"),
]


@pytest.mark.parametrize(("affordance", "params", "field"), BAD)
def test_bad_parameters_are_refused_by_name_and_leave_the_world_unchanged(materials, limits, affordance, params, field):
    w = _world(materials)
    w.sources["fire:crate"] = HeatSource((1.5, 1.5, 0.3), 0.3, 1000.0)  # so extinguish has something to put out
    before = _state(w)
    res = _structure(w, limits).execute(affordance, params)
    assert not res.success
    assert res.error is not None
    assert field in res.error
    assert _unchanged(before, w)


def test_params_must_be_a_mapping(materials, limits):
    w = _world(materials)
    before = _state(w)
    res = _structure(w, limits).execute("ignite", [("power_w", 1000.0)])
    assert not res.success
    assert res.error == "params must be a mapping of names to values"
    assert _unchanged(before, w)


@pytest.mark.parametrize(
    ("affordance", "params"),
    [
        ("ignite", {"power_w": 500_000}),  # an int, as an LLM's JSON gives it
        ("ignite", {"power_w": np.float32(60_000.0), "radius_m": np.float64(0.4)}),
        ("strike", {"energy_j": 200_000, "sigma_m": 0.2, "point_m": (1.5, 1.5, 0.3)}),
        ("strike", {"energy_j": 0.0}),  # a tap does nothing, and that's fine
    ],
)
def test_good_parameters_of_any_real_number_type_still_work(materials, limits, affordance, params):
    assert _structure(_world(materials), limits).execute(affordance, params).success


def test_the_limits_come_from_data_and_the_bounds_are_inclusive(materials, limits):
    w = _world(materials)
    s = _structure(w, limits)
    assert s.execute("ignite", {"power_w": limits.max_power_w, "radius_m": limits.max_radius_m}).success
    assert s.execute("strike", {"energy_j": limits.max_energy_j, "sigma_m": limits.max_sigma_m}).success
    too_much = limits.max_power_w * 1.01
    refused = s.execute("ignite", {"power_w": too_much})
    assert refused.error == f"power_w must be a finite number in [0, {limits.max_power_w:g}], got {too_much!r}"


# -- the physics entry points refuse what no caller should ever pass ------------------------------------------------


@pytest.mark.parametrize(
    ("point", "energy", "sigma"),
    [
        ((1.0, 1.0, 1.0), math.nan, 0.2),
        ((1.0, 1.0, 1.0), math.inf, 0.2),
        ((1.0, 1.0, 1.0), 1e5, math.nan),
        ((1.0, 1.0, 1.0), 1e5, math.inf),
        ((math.nan, 1.0, 1.0), 1e5, 0.2),
        ((1.0, 1.0), 1e5, 0.2),
    ],
)
def test_a_strike_refuses_non_finite_physics(materials, point, energy, sigma):
    w = _world(materials)
    with pytest.raises(ValueError, match="strike"):
        damage.strike(w.grid, point, energy, sigma)


@pytest.mark.parametrize(
    ("point", "radius", "power"),
    [
        ((1.0, 1.0, 1.0), 0.3, math.nan),
        ((1.0, 1.0, 1.0), 0.3, math.inf),
        ((1.0, 1.0, 1.0), 0.3, -1.0),
        ((1.0, 1.0, 1.0), 0.0, 1.0),
        ((1.0, 1.0, 1.0), -0.3, 1.0),
        ((1.0, 1.0, 1.0), math.nan, 1.0),
        ((math.inf, 1.0, 1.0), 0.3, 1.0),
        ((1.0, 1.0), 0.3, 1.0),
    ],
)
def test_a_heat_source_refuses_non_finite_or_negative_physics(point, radius, power):
    with pytest.raises(ValueError, match="heat source"):
        HeatSource(point, radius, power)


# -- no input crashes the modulator or poisons the grid ---------------------------------------------------------------

_values = st.one_of(
    st.floats(allow_nan=True, allow_infinity=True),
    st.integers(min_value=-(10**400), max_value=10**400),
    st.booleans(),
    st.none(),
    st.text(max_size=6),
    st.lists(st.one_of(st.floats(allow_nan=True, allow_infinity=True), st.integers(), st.booleans()), max_size=5),
)
_params = st.dictionaries(
    st.sampled_from(["power_w", "radius_m", "energy_j", "sigma_m", "point_m", "x"]), _values, max_size=4
)


@settings(derandomize=True, max_examples=300, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(affordance=st.sampled_from(["strike", "ignite", "extinguish", "teleport"]), params=_params)
def test_no_input_crashes_the_modulator_or_leaves_a_non_finite_cell(materials, limits, affordance, params):
    w = _world(materials)
    before = _state(w)
    res = _structure(w, limits).execute(affordance, params)
    if not res.success:
        assert _unchanged(before, w)
    w.advance()
    g = w.grid
    assert np.isfinite(g.temperature).all()
    assert np.isfinite(g.integrity).all()
    assert ((g.integrity >= 0) & (g.integrity <= 1)).all()
    assert (g.temperature > -273.15).all()


# -- the limits file is a loader, so every rejection path is tested -------------------------------------------------

GOOD_LIMITS = (
    "version: 0\nignite: {max_power_w: 1.0e+7, min_radius_m: 0.01, max_radius_m: 3.0}\n"
    "strike: {max_energy_j: 1.0e+9, min_sigma_m: 0.01, max_sigma_m: 2.0}\n"
)


def test_the_shipped_limits_load(limits):
    assert limits == ActionLimits.load()
    assert limits.max_power_w == 1.0e7


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("[1, 2]\n", "version must be 0"),
        (GOOD_LIMITS.replace("version: 0", "version: 1"), "version must be 0, got 1"),
        (GOOD_LIMITS + "teleport: {}\n", "expected sections"),
        (GOOD_LIMITS.replace("ignite: {", "ignite: {extra: 1, "), "ignite must have exactly"),
        (GOOD_LIMITS.replace("strike: {max_energy_j: 1.0e+9, ", "strike: {"), "strike must have exactly"),
        (GOOD_LIMITS.replace("1.0e+7", ".nan"), "max_power_w must be a positive finite number"),
        (GOOD_LIMITS.replace("1.0e+7", "-1"), "max_power_w must be a positive finite number"),
        (GOOD_LIMITS.replace("1.0e+7", "true"), "max_power_w must be a positive finite number"),
        (GOOD_LIMITS.replace("1.0e+7", "'big'"), "max_power_w must be a positive finite number"),
        # YAML 1.1 reads 1.0e7 (no exponent sign) as a string; the loader refuses it rather than guessing.
        (GOOD_LIMITS.replace("1.0e+7", "1.0e7"), "max_power_w must be a positive finite number, got '1.0e7'"),
        (GOOD_LIMITS.replace("max_radius_m: 3.0", "max_radius_m: 0.001"), "minimum must not exceed its maximum"),
        (GOOD_LIMITS.replace("max_sigma_m: 2.0", "max_sigma_m: 0.001"), "minimum must not exceed its maximum"),
    ],
)
def test_bad_limits_files_are_refused_loudly(tmp_path, text, message):
    path = tmp_path / "actions.yaml"
    path.write_text(text)
    with pytest.raises(ValueError, match=message):
        ActionLimits.load(path)


def test_parsing_reads_nothing_from_the_world(limits):
    # parse_action takes no world: the protocol layer can run it before the action reaches the simulation.
    assert parse_action("ignite", {"power_w": 5}, limits) == Ignite(5.0, 0.3)
    assert parse_action("strike", {"energy_j": 1, "point_m": [1, 2, 3]}, limits) == Strike(1.0, 0.15, (1.0, 2.0, 3.0))
    assert parse_action("extinguish", {}, limits) == Extinguish()
    with pytest.raises(ActionRefused, match="unknown affordance 7"):
        parse_action(7, {}, limits)
