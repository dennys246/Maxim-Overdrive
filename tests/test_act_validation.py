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


@pytest.mark.parametrize(
    ("affordance", "params", "field"), BAD, ids=[f"{a}-{f}-{i}" for i, (a, _, f) in enumerate(BAD)]
)
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


def test_a_target_is_accepted_only_when_it_is_this_region():
    # Maxim's orchestrator-actor tool passes target=<Entity>, what the actor acts ON (the player by default). A
    # region's structure is only acted on directly, so another target is refused, never dropped: dropping it would
    # strike the crate when the call meant the wall.
    from maxim_overdrive.sem_env.bridge import to_maxim_entity  # noqa: PLC0415 - the gate installs pymaxim

    assert frozenset({"target"}) == MAXIM_CALL_KEYS
    scene = Scene(SCENE.extent_m, (*SCENE.primitives, Box((0, 0, 0), (0.6, 3, 2), "concrete", "wall")))
    w = World.from_scene(scene, RigProfile.load("laptop"), limits=LIMITS)
    crate, wall = to_maxim_entity(w, "crate"), to_maxim_entity(w, "wall")
    s = crate.modulators["structure"]
    for target in [None, crate, "crate", "Crate"]:  # case-insensitive, as Maxim's EntityMap resolves names
        assert s.execute("ignite", {"power_w": 1000.0, "target": target}).success, target
    before = _state(w)
    others: list[tuple[object, str]] = [(wall, "'wall'"), ("player", "'player'"), (object(), "<a object>")]
    for other, shown in others:
        res = s.execute("strike", {"energy_j": 1e5, "target": other})
        assert not res.success
        assert res.error is not None
        assert res.error == (
            f"the crate's structure is acted on directly, not on {shown}: name the crate as the target "
            "(or leave target out)"
        )
    assert _unchanged(before, w)


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
    w.grid.regions["crate"].cells[:] = False
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


WOOD_FLAME_C = 2000.0  # wood's adiabatic flame temperature: no fire on wood may heat a cell past it


def _burn_every_turn(rig, turns):
    w = World.from_scene(SCENE, rig, limits=LIMITS)
    s, m = region_parts(w, "crate")
    assert m["structure"].execute("ignite", {"power_w": LIMITS.max_power_w, "radius_m": LIMITS.min_radius_m}).success
    history = []
    for _ in range(turns):
        w.advance()
        history.append((s["integrity"].value(), float(np.max(w.grid.temperature))))
    return history


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="fires diverge across rigs mid-burn: at the allowed corner the crate's integrity differs by up to 0.19 "
    "between rigs at turn 22, and past about 30 turns the fuel gap heats air. Burning is a threshold on a cell's "
    "mean temperature, which lags in coarse cells (docs/architecture.md, Known gaps). The Phase 1 fuel model "
    "(a burn rate driven by heat content) is the fix; this gate then flips.",
)
def test_the_fiercest_allowed_fire_has_the_same_outcome_at_every_rig_on_every_turn(rigs):
    runs = {rig.name: _burn_every_turn(rig, 60) for rig in rigs}
    for turn in range(60):
        integrity = [h[turn][0] for h in runs.values()]
        assert max(integrity) - min(integrity) <= 0.1, (turn, runs)
        assert all(h[turn][1] <= WOOD_FLAME_C for h in runs.values()), (turn, runs)


CONCRETE_THRESHOLD_J = 2.0e7 * (2 * math.pi) ** 1.5 * 0.2**3  # where a 0.2 m strike's peak meets fracture


def _block_strike(rig, energy_j, thickness_m=1.8, x0=0.6):
    scene = Scene((3.0, 3.0, 2.0), (Box((x0, 0.2, 0), (x0 + thickness_m, 2.8, 1.8), "concrete", "block"),))
    w = World.from_scene(scene, rig, limits=LIMITS)
    sensors, mods = region_parts(w, "block")
    point = [x0 + thickness_m / 2, 1.5, 0.9]
    res = mods["structure"].execute("strike", {"energy_j": energy_j, "sigma_m": 0.2, "point_m": point})
    assert res.success
    return res.metadata["destroyed_volume_m3"], sensors["breached"].value()


def test_a_strike_below_the_fracture_threshold_destroys_nothing_at_any_rig(rigs):
    for rig in rigs:  # exact cell-average deposition makes this a guarantee, not a tolerance
        assert _block_strike(rig, 0.95 * CONCRETE_THRESHOLD_J)[0] == 0, rig.name


@pytest.mark.parametrize("multiple", [4.0, 5.0, 8.0, 12.0, 40.0, 390.0])
def test_a_crater_of_radius_at_least_a_third_of_a_metre_matches_the_closed_form_at_every_rig(rigs, multiple):
    energy = multiple * CONCRETE_THRESHOLD_J
    expected = 4 / 3 * math.pi * damage.analytic_crater_radius_m(energy, 0.2, 2.0e7) ** 3
    for rig in rigs:
        assert _block_strike(rig, energy)[0] == pytest.approx(expected, rel=0.25), rig.name


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="whether a strike breaches a thin wall flips across rigs near the threshold: a 0.4 m concrete wall "
    "struck at 1.5x the threshold is breached at rig and max but not laptop (docs/architecture.md, Known gaps). "
    "Craters narrower than two coarse cells are below what the coarse rig resolves.",
)
def test_a_strike_breaches_a_thin_wall_the_same_at_every_rig(rigs):
    # The wall's faces sit off the 0.2 m grid (x from 1.3 to 1.7 m), as most authored walls will.
    breached = {rig.name: _block_strike(rig, 1.5 * CONCRETE_THRESHOLD_J, 0.4, x0=1.3)[1] for rig in rigs}
    assert len(set(breached.values())) == 1, breached


def test_a_strike_at_any_face_of_a_region_off_the_coarse_grid_is_judged_the_same_at_every_rig(rigs):
    # The crate's faces sit between the 0.2 m cells, so its cells (and any reach built from them) move with the rig.
    lo, hi, sigma = (1.25, 1.25, 0.25), (1.75, 1.75, 0.85), LIMITS.default_sigma_m
    scene = Scene((3.0, 3.0, 2.0), (Box(lo, hi, "wood", "crate"),))
    middle = [(a + b) / 2 for a, b in zip(lo, hi, strict=True)]
    for rig in rigs:
        w = World.from_scene(scene, rig, limits=LIMITS)
        s = region_parts(w, "crate")[1]["structure"]
        for axis in range(3):
            for edge, outward in [(lo[axis] - sigma, -9.0), (hi[axis] + sigma, 9.0)]:
                at, past = list(middle), list(middle)
                at[axis], past[axis] = edge, math.nextafter(edge, outward)
                assert s.execute("strike", {"energy_j": 1e3, "point_m": at}).success, (rig.name, axis, edge)
                refused = s.execute("strike", {"energy_j": 1e3, "point_m": past})
                assert refused.error == "point_m is not on the crate", (rig.name, axis, edge)


def test_a_strike_past_a_regions_face_into_another_region_belongs_to_that_region(rigs):
    # A wall right against the crate: a strike just past the crate's face, within sigma, lands in the wall.
    crate = Box((1.2, 1.2, 0), (1.8, 1.8, 0.6), "wood", "crate")
    wall = Box((1.8, 0, 0), (2.4, 3, 2), "concrete", "wall")
    room = Box((0.6, 0.6, 0), (2.4, 2.4, 1.2), "air", "room")  # an air room never owns a point
    for rig in rigs:
        w = World.from_scene(Scene((3.0, 3.0, 2.0), (room, crate, wall)), rig, limits=LIMITS)
        parts = {r: region_parts(w, r)[1]["structure"] for r in ("crate", "wall")}
        before = _state(w)
        res = parts["crate"].execute("strike", {"energy_j": 1e7, "point_m": [1.85, 1.5, 0.3]})
        assert res.error == "point_m is not on the crate", rig.name
        assert _unchanged(before, w)
        assert parts["wall"].execute("strike", {"energy_j": 1e3, "point_m": [1.85, 1.5, 0.3]}).success
        assert (
            parts["crate"].execute("strike", {"energy_j": 1e3, "point_m": [1.15, 1.5, 0.3]}).success
        )  # inside the room
        res = parts["crate"].execute("strike", {"energy_j": 1e3, "point_m": [1.79, 1.5, 0.3]})
        assert res.success, rig.name  # within sigma of the wall, but on the crate's own footprint


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


# -- folds from PR 1's delta review -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "params",
    [
        {"energy_j": 1e3, "point_m": [10**5000, 0, 0]},  # nested: 3.10's reprlib crashed on it
        {"energy_j": 1e3, "point_m": (10**5000,)},
        {"energy_j": 1e3, "point_m": [[10**5000], 0, 0]},
        {"energy_j": 1e3, (10**5000,): 1},
        {"energy_j": "x" * 1_000_000},
    ],
    ids=["nested-int", "short-tuple-int", "deep-int", "int-key", "megabyte-string"],  # str(10**5000) would raise
)
def test_huge_or_hostile_values_anywhere_are_refused_with_a_short_message(params):
    res = _structure(_world()).execute("strike", params)
    assert not res.success
    assert res.error is not None
    assert len(res.error) < 200


@pytest.mark.parametrize(
    "affordance", [10**5000, "x" * 1_000_000, None, ("strike",)], ids=["huge-int", "megabyte", "none", "tuple"]
)
def test_a_hostile_affordance_name_is_refused_and_never_echoed_whole(affordance):
    res = _structure(_world()).execute(affordance, {})
    assert not res.success
    assert len(res.affordance) <= 80
    assert res.error is not None
    assert len(res.error) < 200


@pytest.mark.parametrize(
    ("build", "name"),
    [
        (lambda: Strike(10**400, 0.2, None), "energy_j"),
        (lambda: Strike("a", 0.2, None), "energy_j"),  # type: ignore[arg-type]
        (lambda: Strike(1.0, math.nan, None), "sigma_m"),
        (lambda: Strike(1.0, 0.2, (1.0, 2.0)), "point_m"),  # type: ignore[arg-type]
        (lambda: Strike(1.0, 0.2, (1.0, "2", 3.0)), "point_m"),  # type: ignore[arg-type]
        (lambda: Ignite(math.nan, 0.3), "power_w"),
        (lambda: Ignite(1.0, math.inf), "radius_m"),
    ],
)
def test_a_hand_built_action_with_bad_numbers_cannot_be_made(build, name):
    with pytest.raises(ActionRefused, match=f"^{name} must be"):
        build()


def test_apply_refuses_what_is_not_an_action_loudly():
    with pytest.raises(TypeError, match="not an action: object"):
        _structure(_world()).apply(object())


@pytest.mark.parametrize(
    ("action", "affordance"),
    [(Strike(1.0, 0.2, None), "strike"), (Ignite(1.0, 0.3), "ignite"), (Extinguish(), "extinguish")],
)
def test_apply_names_every_affordance_from_its_action(action, affordance):
    assert _structure(_world()).apply(action).affordance == affordance


def test_a_zero_limit_is_refused():
    with pytest.raises(ValueError, match="max_power_w must be positive"):
        ActionLimits(**{**vars(LIMITS), "max_power_w": 0.0})


@pytest.mark.parametrize(
    ("text", "message"),
    [
        (GOOD_LIMITS.replace("version: 0", "version: 0\n? [1, 2]\n: 3"), "a mapping key must be a plain value"),
    ],
)
def test_more_bad_limits_files_are_refused(tmp_path, text, message):
    path = tmp_path / "actions.yaml"
    path.write_text(text)
    with pytest.raises(ValueError, match=message):
        ActionLimits.load(path)


def test_yaml_merge_keys_still_work_in_the_limits_file(tmp_path):
    text = (
        "version: 0\n"
        "base: &base {max_power_w: 500000.0, min_radius_m: 0.3, max_radius_m: 3.0, default_radius_m: 0.3}\n"
        "ignite: {<<: *base}\n" + GOOD_LIMITS.split("\n")[2] + "\n"
    )
    path = tmp_path / "actions.yaml"
    path.write_text(text)
    with pytest.raises(ValueError, match="expected sections"):  # merged fine; "base" is then an unknown section
        ActionLimits.load(path)


def test_maxims_actor_tool_must_name_the_region_as_its_own_target():
    # In Maxim's OrchestratorActorTool the entity acts ON its target (default: the player). Overdrive's affordances
    # are done TO the region, so only target=<the region> is a coherent call (roadmap Phase 3 item 11 asks Maxim to
    # tell the two kinds of affordance apart).
    from maxim.embodiment.body import Embodiment  # noqa: PLC0415 - the gate installs pymaxim
    from maxim.embodiment.entity_map import EntityMap  # noqa: PLC0415
    from maxim.embodiment.sem import Entity  # noqa: PLC0415
    from maxim.simulation.tools import OrchestratorActorTool  # noqa: PLC0415

    from maxim_overdrive.sem_env.bridge import to_maxim_entity  # noqa: PLC0415

    w = World.from_scene(
        Scene(SCENE.extent_m, (*SCENE.primitives, Box((0, 0, 0), (0.6, 3, 2), "concrete", "wall"))),
        RigProfile.load("laptop"),
        limits=LIMITS,
    )
    npc = Entity("npc", "body")
    entities = EntityMap()
    entities.register_self(npc)
    entities.register_scene(to_maxim_entity(w, "crate"))
    entities.register_scene(to_maxim_entity(w, "wall"))
    actor = OrchestratorActorTool(embodiment=Embodiment(npc), entity_map=entities)
    ignite = {"entity": "crate", "affordance": "ignite", "params": {"power_w": 1000.0}}
    default = actor.run(**ignite)
    assert not default.success
    assert "name the crate as the target" in (default.error or "")
    assert w.sources == {}
    assert actor.run(**ignite, target="crate").success
    assert w.sources["fire:crate"].power_w == 1000.0
    assert not actor.run(entity="crate", affordance="strike", target="wall", params={"energy_j": 1e3}).success


@pytest.mark.parametrize(
    "target",
    [
        type("Sneaky", (str,), {"__eq__": lambda self, other: True, "__hash__": str.__hash__})("wall"),
        "x" * 1_000_000,
        10**5000,
    ],
    ids=["str-subclass", "megabyte-name", "huge-int"],
)
def test_a_hostile_target_is_refused_with_a_short_message(target):
    res = _structure(_world()).execute("ignite", {"power_w": 1.0, "target": target})
    assert not res.success
    assert res.error is not None
    assert len(res.error) < 300


def test_a_yaml_merge_key_can_be_overridden_but_a_written_key_cannot_repeat(tmp_path):
    base = "base: &b {max_power_w: 1.0, min_radius_m: 0.3, max_radius_m: 3.0, default_radius_m: 0.3}\n"
    strike = GOOD_LIMITS.split("\n")[2] + "\n"
    path = tmp_path / "actions.yaml"
    path.write_text("version: 0\n" + base + "ignite: {<<: *b, max_power_w: 500000.0}\n" + strike)
    with pytest.raises(ValueError, match="expected sections"):  # merged and overridden fine; "base" is unknown
        ActionLimits.load(path)
    path.write_text("version: 0\nignite: {<<: *b, max_power_w: 1.0, max_power_w: 2.0}\n".replace("*b", "{}"))
    with pytest.raises(ValueError, match="repeated key"):
        ActionLimits.load(path)


def test_a_fire_lands_on_the_authored_centroid_at_every_rig(rigs):
    # The crate's faces sit off the coarse grid, so the centroid of its cells moves with the rig; the fire mustn't.
    scene = Scene((3.0, 3.0, 2.0), (Box((1.25, 1.25, 0.25), (1.75, 1.75, 0.85), "wood", "crate"),))
    for rig in rigs:
        w = World.from_scene(scene, rig, limits=LIMITS)
        assert region_parts(w, "crate")[1]["structure"].execute("ignite", {"power_w": 1.0}).success
        assert w.sources["fire:crate"].point_m == (1.5, 1.5, 0.55), rig.name


def test_an_entity_whose_name_is_not_a_plain_string_is_refused():
    from maxim.embodiment.sem import Entity  # noqa: PLC0415 - the gate installs pymaxim

    sneaky = Entity("crate", "structure")
    object.__setattr__(
        sneaky, "name", type("Sneaky", (str,), {"__eq__": lambda s, o: True, "__hash__": str.__hash__})("crate")
    )
    res = _structure(_world()).execute("ignite", {"power_w": 1.0, "target": sneaky})
    assert not res.success


def test_a_merged_key_is_overridden_by_the_one_written_after_it(tmp_path):
    path = tmp_path / "actions.yaml"
    merged = "{max_power_w: 1.0, min_radius_m: 0.3, max_radius_m: 3.0, default_radius_m: 0.3}"
    path.write_text(f"version: 0\nignite: &i {merged}\n" + GOOD_LIMITS.split("\n")[2] + "\n")
    assert ActionLimits.load(path).max_power_w == 1.0
    raw = yaml.load(f"a: &a {merged}\nb: {{<<: *a, max_power_w: 500000.0}}\n", Loader=_strict_loader())
    assert raw["b"]["max_power_w"] == 500000.0  # the written key wins over the merged one


def _strict_loader():
    from maxim_overdrive.config import _StrictLoader  # noqa: PLC0415

    return _StrictLoader
