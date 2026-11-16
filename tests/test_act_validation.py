"""The SEM ``structure`` modulator is a trust boundary: an NPC's tool call, an LLM's output and (from Phase 1 step 2)
a client's ``act`` intent will all reach the world through it. Every refusal leaves the world exactly as it was, and
no input, however malformed, crashes it or puts a non-finite or out-of-range number into the grid.

The bad values below began as the probes the 2026-11-15 design review ran against the committed modulator
(docs/design/reviews/realtime_lanes_coop/trust_boundary.md TB-1, executor.md X7), plus those PR 1's own review found.
"""

from __future__ import annotations

import json
import math
from decimal import Decimal
from fractions import Fraction

import numpy as np
import pytest
import yaml
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from maxim_overdrive import Box, RigProfile, Scene, World
from maxim_overdrive.config import ActionLimits, data_dir
from maxim_overdrive.sem_env.bridge import (
    MAXIM_CALL_KEYS,
    ActionRefused,
    Extinguish,
    Ignite,
    Strike,
    parse_action,
    region_parts,
)
from maxim_overdrive.world import damage
from maxim_overdrive.world.world import HeatSource
from tests.conftest import FAST_TIERS

LIMITS = ActionLimits.load()
SCENE = Scene((3.0, 3.0, 2.0), (Box((1.2, 1.2, 0), (1.8, 1.8, 0.6), "wood", "crate"),))


def _world(rig="laptop"):
    return World.from_scene(SCENE, RigProfile.load(rig), limits=LIMITS)


def _structure(world):
    return region_parts(world, "crate")[1]["structure"]


def _state(world):
    g = world.grid
    return (g.material.copy(), g.integrity.copy(), g.temperature.copy(), dict(world.sources))


def _unchanged(before, world):
    after = _state(world)
    same_cells = all(np.array_equal(a, b, equal_nan=True) for a, b in zip(before[:3], after[:3], strict=True))
    return same_cells and before[3] == after[3]


BAD = [
    # ignite: power
    ("ignite", {"power_w": math.nan}, "power_w"),
    ("ignite", {"power_w": math.inf}, "power_w"),
    ("ignite", {"power_w": -1e9}, "power_w"),
    ("ignite", {"power_w": 1e300}, "power_w"),
    ("ignite", {"power_w": "inf"}, "power_w"),
    ("ignite", {"power_w": "500000"}, "power_w"),  # numeric strings are refused, never guessed
    ("ignite", {"power_w": True}, "power_w"),
    ("ignite", {"power_w": 10**400}, "power_w"),
    ("ignite", {"power_w": 10**5000}, "power_w"),  # too long for int-to-str: the message must not crash
    ("ignite", {"power_w": Decimal("1000")}, "power_w"),
    ("ignite", {"power_w": 1000 + 0j}, "power_w"),
    ("ignite", {"power_w": np.array([1000.0])}, "power_w"),
    ("ignite", {}, "power_w"),
    # ignite: radius
    ("ignite", {"power_w": 1000.0, "radius_m": -0.3}, "radius_m"),
    ("ignite", {"power_w": 1000.0, "radius_m": -0.0}, "radius_m"),
    ("ignite", {"power_w": 1000.0, "radius_m": 0.0}, "radius_m"),
    ("ignite", {"power_w": 1000.0, "radius_m": 0.1}, "radius_m"),  # below the minimum: a sub-cell fire
    ("ignite", {"power_w": 1000.0, "radius_m": math.nan}, "radius_m"),
    ("ignite", {"power_w": 1000.0, "radius_m": 50.0}, "radius_m"),
    ("ignite", {"power_w": 1000.0, "colour": "red"}, "colour"),
    ("ignite", {"power_w": 1000.0, 7: 1}, "7"),
    ("ignite", {"power_w": 1000.0, 10**5000: 1}, "digits"),
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
    ("strike", {"energy_j": 1e5, "sigma_m": 0.1}, "sigma_m"),  # below the minimum: a sub-cell crater
    ("strike", {"energy_j": 1e5, "sigma_m": -0.1}, "sigma_m"),
    ("strike", {"energy_j": 1e5, "sigma_m": 100.0}, "sigma_m"),
    # strike: point
    ("strike", {"energy_j": 1e5, "point_m": [1.0]}, "point_m"),
    ("strike", {"energy_j": 1e5, "point_m": []}, "point_m"),  # empty is not "omitted"
    ("strike", {"energy_j": 1e5, "point_m": [1.0, 1.0]}, "point_m"),
    ("strike", {"energy_j": 1e5, "point_m": [math.nan, 1.0, 1.0]}, "point_m"),
    ("strike", {"energy_j": 1e5, "point_m": [True, 1.0, 1.0]}, "point_m"),
    ("strike", {"energy_j": 1e5, "point_m": "abc"}, "point_m"),
    ("strike", {"energy_j": 1e5, "point_m": [1, 2, 3, 4]}, "point_m"),
    ("strike", {"energy_j": 1e5, "point_m": [[1.0], 1.0, 1.0]}, "point_m"),
    ("strike", {"energy_j": 1e5, "point_m": [0.0, 0.0, 8.98846567431158e307]}, "point_m"),  # overflowed before
    ("strike", {"energy_j": 1e5, "point_m": [0.2, 0.2, 0.2]}, "point_m"),  # in the world, but not on the crate
    ("strike", {"energy_j": 1e5, "force": 3}, "force"),
    # extinguish takes nothing; the affordance must exist
    ("extinguish", {"all": True}, "all"),
    ("teleport", {}, "teleport"),
]


@pytest.mark.parametrize(("affordance", "params", "field"), BAD)
def test_bad_parameters_are_refused_by_name_and_leave_the_world_unchanged(affordance, params, field):
    w = _world()
    w.sources["fire:crate"] = HeatSource((1.5, 1.5, 0.3), 0.3, 1000.0)  # so extinguish has something to put out
    before = _state(w)
    res = _structure(w).execute(affordance, params)
    assert not res.success
    assert res.error is not None
    assert field in res.error
    assert len(res.error) < 200  # a hostile value never floods the reply
    json.dumps(res.params, allow_nan=False)  # a refusal never echoes a non-finite value back
    assert _unchanged(before, w)


@pytest.mark.parametrize("params", [None, "power_w=1000", [("power_w", 1000.0)], 7])
def test_params_must_be_a_mapping(params):
    w = _world()
    before = _state(w)
    res = _structure(w).execute("ignite", params)
    assert not res.success
    assert res.error == "params must be a mapping of names to values"
    assert _unchanged(before, w)


@pytest.mark.parametrize(
    ("affordance", "params"),
    [
        ("ignite", {"power_w": 500_000}),  # an int, as an LLM's JSON gives it
        ("ignite", {"power_w": np.float32(60_000.0), "radius_m": np.float64(0.4)}),
        ("ignite", {"power_w": Fraction(1000, 3), "radius_m": None}),  # None means "use the default"
        ("strike", {"energy_j": 200_000, "sigma_m": 0.2, "point_m": (1.5, 1.5, 0.3)}),
        ("strike", {"energy_j": np.int64(1000), "point_m": [1.5, 1.5, 0.3]}),
        ("strike", {"energy_j": 0.0}),  # a tap does nothing, and that's fine
    ],
)
def test_good_parameters_of_any_real_number_type_still_work(affordance, params):
    res = _structure(_world()).execute(affordance, params)
    assert res.success, res.error


def test_maxims_call_keys_are_accepted_and_dropped():
    # Maxim's orchestrator-actor tool always passes target=<Entity>, the entity this modulator belongs to.
    assert frozenset({"target"}) == MAXIM_CALL_KEYS
    w = _world()
    assert _structure(w).execute("ignite", {"power_w": 1000.0, "target": object()}).success
    assert w.sources["fire:crate"].power_w == 1000.0


def test_both_ends_of_every_limit_are_allowed_and_one_step_past_them_is_not():
    s = _structure(_world())
    lim = LIMITS
    assert s.execute("ignite", {"power_w": lim.max_power_w, "radius_m": lim.max_radius_m}).success
    assert s.execute("ignite", {"power_w": 0.0, "radius_m": lim.min_radius_m}).success
    assert s.execute("strike", {"energy_j": lim.max_energy_j, "sigma_m": lim.max_sigma_m}).success
    assert s.execute("strike", {"energy_j": 0.0, "sigma_m": lim.min_sigma_m}).success
    for affordance, params, name in [
        ("ignite", {"power_w": math.nextafter(lim.max_power_w, math.inf)}, "power_w"),
        ("ignite", {"power_w": 1.0, "radius_m": math.nextafter(lim.min_radius_m, 0)}, "radius_m"),
        ("ignite", {"power_w": 1.0, "radius_m": math.nextafter(lim.max_radius_m, math.inf)}, "radius_m"),
        ("strike", {"energy_j": math.nextafter(lim.max_energy_j, math.inf)}, "energy_j"),
        ("strike", {"energy_j": 1.0, "sigma_m": math.nextafter(lim.min_sigma_m, 0)}, "sigma_m"),
        ("strike", {"energy_j": 1.0, "sigma_m": math.nextafter(lim.max_sigma_m, math.inf)}, "sigma_m"),
    ]:
        res = s.execute(affordance, params)
        assert not res.success
        assert res.error is not None
        assert res.error.startswith(f"{name} must be between")


def test_omitted_parameters_take_their_defaults_from_the_limits():
    w = _world()
    s = _structure(w)
    assert s.execute("ignite", {"power_w": 10.0}).success
    assert w.sources["fire:crate"].radius_m == LIMITS.default_radius_m
    assert parse_action("strike", {"energy_j": 1.0}, LIMITS) == Strike(1.0, LIMITS.default_sigma_m, None)
    schema = s.affordances
    assert schema["ignite"].params["radius_m"] == (float, LIMITS.default_radius_m)
    assert schema["strike"].params["sigma_m"] == (float, LIMITS.default_sigma_m)
    assert f"{LIMITS.max_power_w:g} W" in schema["ignite"].description  # the agent can read the bounds


def test_apply_rechecks_an_action_built_without_parsing():
    w = _world()
    s = _structure(w)
    before = _state(w)
    for action, name in [(Ignite(1e30, 0.3), "power_w"), (Strike(1e300, 0.2, None), "energy_j")]:
        res = s.apply(action)
        assert not res.success
        assert res.error is not None
        assert res.error.startswith(f"{name} must be between")
    assert _unchanged(before, w)


def test_apply_names_the_affordance_from_the_action_and_reports_the_parsed_values():
    w = _world()
    res = _structure(w).apply(parse_action("strike", {"energy_j": 1e3, "point_m": [1.5, 1.5, 0.3]}, LIMITS))
    assert res.success
    assert res.affordance == "strike"
    assert res.params == {"energy_j": 1e3, "sigma_m": LIMITS.default_sigma_m, "point_m": [1.5, 1.5, 0.3]}


def test_a_region_that_is_gone_refuses_in_words_the_agent_can_use():
    w = _world()
    s = _structure(w)
    w.grid.regions["crate"][:] = False
    for affordance, params in [("ignite", {"power_w": 1.0}), ("strike", {"energy_j": 1.0}), ("extinguish", {})]:
        res = s.execute(affordance, params)
        assert not res.success
        assert res.error == "the crate is gone"
    with pytest.raises(ValueError, match="region 'crate' has no cells"):
        s.centroid_m()  # a direct caller gets the physics answer, not a guess


def test_extinguishing_nothing_is_refused_in_words():
    res = _structure(_world()).execute("extinguish", {})
    assert not res.success
    assert res.error == "nothing is burning on the crate"


def test_every_shipped_rig_is_at_least_as_fine_as_the_smallest_action():
    # The resolution rule: an action smaller than a coarse cell lands in one cell at that rig and spreads at a finer
    # one, so its outcome would depend on the rig.
    coarsest = max(RigProfile.load(p.stem).cell_size_m for p in (data_dir() / "rigs").glob("*.yaml"))
    assert LIMITS.min_radius_m >= coarsest
    assert LIMITS.min_sigma_m >= coarsest


def _ignite_and_burn(rig, turns=40):
    w = _world(rig)
    s, m = region_parts(w, "crate")
    assert m["structure"].execute("ignite", {"power_w": LIMITS.max_power_w, "radius_m": LIMITS.min_radius_m}).success
    onset = None
    for turn in range(turns):
        w.advance()
        if onset is None and s["integrity"].value() < 0.9:
            onset = turn
    return onset, s["integrity"].value()


def test_the_fiercest_allowed_fire_has_the_same_outcome_at_every_rig():
    runs = {rig: _ignite_and_burn(rig) for rig in FAST_TIERS}
    onsets = [o for o, _ in runs.values()]
    assert all(o is not None for o in onsets), runs
    assert max(onsets) - min(onsets) <= max(1, 0.1 * min(onsets)), runs
    assert all(integrity < 0.7 for _, integrity in runs.values()), runs


@pytest.mark.parametrize("energy_j", [1e7, 3e7, 1e8, LIMITS.max_energy_j])
def test_the_narrowest_allowed_strike_makes_the_same_crater_at_every_rig(energy_j):
    scene = Scene((3.0, 3.0, 2.0), (Box((0.6, 0.6, 0), (2.4, 2.4, 1.8), "concrete", "block"),))
    expected = 4 / 3 * math.pi * damage.analytic_crater_radius_m(energy_j, LIMITS.min_sigma_m, 2.0e7) ** 3
    for rig in FAST_TIERS:
        w = World.from_scene(scene, RigProfile.load(rig), limits=LIMITS)
        res = region_parts(w, "block")[1]["structure"].execute(
            "strike", {"energy_j": energy_j, "sigma_m": LIMITS.min_sigma_m}
        )
        assert res.success
        assert res.metadata["destroyed_volume_m3"] == pytest.approx(expected, rel=0.25), rig


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
def test_a_strike_refuses_non_finite_physics(point, energy, sigma):
    with pytest.raises(ValueError, match="strike"):
        damage.strike(_world().grid, point, energy, sigma)


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


# -- through Maxim's own tool layer, the path an NPC's tool call will take --------------------------------------------


def test_an_npc_tool_call_through_maxim_is_refused_or_applied_the_same_way():
    from maxim.embodiment.tool_bridge import generate_tools_for_entity  # noqa: PLC0415 - the gate installs pymaxim
    from maxim.tools.registry import ToolRegistry  # noqa: PLC0415

    from maxim_overdrive.sem_env.bridge import to_maxim_entity  # noqa: PLC0415

    w = _world()
    tools = generate_tools_for_entity(to_maxim_entity(w, "crate"), ToolRegistry())
    ignite = next(t for t in tools if t.name == "crate_ignite")
    refused = ignite.execute(power_w=math.nan)
    assert not refused.success
    assert refused.error == "power_w must be a finite number, got nan"
    assert w.sources == {}
    assert ignite.execute(power_w=1000).success
    assert w.sources["fire:crate"].power_w == 1000.0


# -- no input crashes the modulator or poisons the grid ---------------------------------------------------------------

_reals = st.one_of(
    st.floats(allow_nan=True, allow_infinity=True),
    st.floats(min_value=-1.0, max_value=4.0),  # near the world's extent, so point_m sometimes lands on the crate
    st.integers(min_value=-(10**400), max_value=10**400),
    st.fractions(),
    st.decimals(allow_nan=True),
    st.complex_numbers(),
    st.builds(np.float32, st.floats(width=32)),
    st.builds(np.int64, st.integers(min_value=-(2**63), max_value=2**63 - 1)),
    st.sampled_from([np.bool_(True), np.float64(np.nan), -0.0]),
)
_values = st.one_of(
    _reals,
    st.booleans(),
    st.none(),
    st.text(max_size=6),
    st.lists(_reals, max_size=5),
    st.tuples(_reals, _reals, _reals),
    st.lists(st.lists(_reals, max_size=3), max_size=3),
)
_keys = st.one_of(
    st.sampled_from(["power_w", "radius_m", "energy_j", "sigma_m", "point_m", "target", "x"]),
    st.integers(),
    st.none(),
)
_params = st.one_of(st.dictionaries(_keys, _values, max_size=4), st.none(), st.lists(_values, max_size=2))


@pytest.mark.parametrize("rig", FAST_TIERS)
@settings(derandomize=True, max_examples=250, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(affordance=st.sampled_from(["strike", "ignite", "extinguish", "teleport", 3]), params=_params)
def test_no_input_crashes_the_modulator_or_leaves_a_bad_cell(rig, affordance, params):
    w = _world(rig)
    before = _state(w)
    res = _structure(w).execute(affordance, params)  # must not raise
    if not res.success:
        assert _unchanged(before, w)
    for source in w.sources.values():  # whatever was accepted is inside the limits
        assert 0 <= source.power_w <= LIMITS.max_power_w
        assert LIMITS.min_radius_m <= source.radius_m <= LIMITS.max_radius_m
    for _ in range(3):
        w.advance()
    g = w.grid
    assert np.isfinite(g.temperature).all()
    assert np.isfinite(g.integrity).all()
    assert ((g.integrity >= 0) & (g.integrity <= 1)).all()
    assert (g.temperature > -273.15).all()


# -- the limits file is a loader, so every rejection path is tested -------------------------------------------------

GOOD_LIMITS = (
    "version: 0\n"
    "ignite: {max_power_w: 500000.0, min_radius_m: 0.3, max_radius_m: 3.0, default_radius_m: 0.3}\n"
    "strike: {max_energy_j: 1.0e+9, min_sigma_m: 0.2, max_sigma_m: 2.0, default_sigma_m: 0.2}\n"
)


def test_the_shipped_limits_load_as_floats():
    assert ActionLimits.load() == LIMITS
    assert all(isinstance(v, float) for v in vars(LIMITS).values())
    assert isinstance(ActionLimits(**{**vars(LIMITS), "max_power_w": 7}).max_power_w, float)


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("[1, 2]\n", "version must be 0"),
        ("", "version must be 0, got None"),
        (GOOD_LIMITS.replace("version: 0", "version: 1"), "version must be 0, got 1"),
        (GOOD_LIMITS.replace("version: 0", "version: false"), "version must be 0, got False"),
        (GOOD_LIMITS.replace("version: 0", "version: 0.0"), "version must be 0, got 0.0"),
        (GOOD_LIMITS + "teleport: {}\n", "expected sections"),
        ("version: 0\n" + GOOD_LIMITS.split("\n")[1] + "\n", "expected sections"),
        (GOOD_LIMITS.replace("ignite: {", "ignite: {extra: 1, "), "ignite must have exactly"),
        (GOOD_LIMITS.replace("strike: {max_energy_j: 1.0e+9, ", "strike: {"), "strike must have exactly"),
        ("version: 0\nignite: [1, 2]\n" + GOOD_LIMITS.split("\n")[2] + "\n", "ignite must have exactly"),
        ("version: 0\nignite: {max_power_w: [1\n", "not valid YAML"),
        (GOOD_LIMITS.replace("500000.0", ".nan"), "max_power_w must be a finite number"),
        (GOOD_LIMITS.replace("500000.0", "-1"), "max_power_w must be positive"),
        (GOOD_LIMITS.replace("500000.0", "true"), "max_power_w must be a finite number"),
        (GOOD_LIMITS.replace("500000.0", "'big'"), "max_power_w must be a finite number"),
        (GOOD_LIMITS.replace("500000.0", "1" + "0" * 400), "max_power_w must be a finite number"),
        # YAML 1.1 reads 5.0e5 (no exponent sign) as a string; the loader refuses it rather than guessing.
        (GOOD_LIMITS.replace("500000.0", "5.0e5"), "max_power_w must be a finite number, got '5.0e5'"),
        (GOOD_LIMITS.replace("max_radius_m: 3.0", "max_radius_m: 0.25"), "default_radius_m must lie between"),
        (GOOD_LIMITS.replace("default_radius_m: 0.3", "default_radius_m: 9.0"), "default_radius_m must lie between"),
        (GOOD_LIMITS.replace("default_sigma_m: 0.2", "default_sigma_m: 0.1"), "default_sigma_m must lie between"),
        (GOOD_LIMITS.replace("max_power_w: 500000.0", "max_power_w: 1.0, max_power_w: 2.0"), "repeated key"),
    ],
)
def test_bad_limits_files_are_refused_loudly(tmp_path, text, message):
    path = tmp_path / "actions.yaml"
    path.write_text(text)
    with pytest.raises(ValueError, match=message):
        ActionLimits.load(path)


def test_parsing_reads_nothing_from_the_world():
    # parse_action takes no world: the protocol layer can run it before the action reaches the simulation.
    assert parse_action("ignite", {"power_w": 5}, LIMITS) == Ignite(5.0, LIMITS.default_radius_m)
    assert parse_action("strike", {"energy_j": 1, "point_m": [1, 2, 3]}, LIMITS) == Strike(
        1.0, LIMITS.default_sigma_m, (1.0, 2.0, 3.0)
    )
    assert parse_action("extinguish", {}, LIMITS) == Extinguish()
    with pytest.raises(ActionRefused, match="unknown affordance 7"):
        parse_action(7, {}, LIMITS)


def test_no_data_file_writes_a_number_as_a_string():
    # YAML 1.1 reads 1.0e7 (no exponent sign) as the string "1.0e7". The loaders refuse numeric strings, so a data
    # file written that way fails loudly; this test names the file and the key instead.
    found = []

    def walk(value, path):
        if isinstance(value, dict):
            for k, v in value.items():
                walk(v, [*path, str(k)])
        elif isinstance(value, list):
            for i, v in enumerate(value):
                walk(v, [*path, str(i)])
        elif isinstance(value, str):
            try:
                float(value)
            except ValueError:
                return
            found.append(".".join(path))

    for path in sorted(data_dir().rglob("*.yaml")):
        walk(yaml.safe_load(path.read_text()), [path.name])
    assert found == []
