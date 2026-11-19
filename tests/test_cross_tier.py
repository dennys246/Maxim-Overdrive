"""The resolution rule on a full turn loop: a fire on a crate, and on a concrete wall, at every rig."""

import numpy as np
import pytest

from maxim_overdrive import Box, RigProfile, Scene, World
from maxim_overdrive.sem_env.bridge import region_parts
from tests.conftest import FAST_TIERS

SCENE = Scene(
    (3.0, 3.0, 2.0),
    (Box((1.2, 1.2, 0), (1.8, 1.8, 0.6), "wood", "crate"), Box((0, 0, 0), (0.6, 3.0, 2.0), "concrete", "wall")),
)


def _burn(rig, materials, turns=150, power_w=60_000.0):
    w = World.from_scene(SCENE, rig, materials)
    crate_s, crate_m = region_parts(w, "crate")
    wall_s, wall_m = region_parts(w, "wall")
    assert crate_m["structure"].execute("ignite", {"power_w": power_w, "radius_m": 0.3}).success
    assert wall_m["structure"].execute("ignite", {"power_w": power_w, "radius_m": 0.3}).success
    onset = None
    for turn in range(turns):
        w.advance()
        if onset is None and crate_s["integrity"].value() < 0.9:
            onset = turn
    return onset, crate_s["integrity"].value(), wall_s["integrity"].value()


def test_fire_outcomes_agree_across_rigs(rigs, materials):
    runs = {rig.name: _burn(rig, materials) for rig in rigs}
    onsets = [r[0] for r in runs.values()]
    assert all(o is not None for o in onsets), runs  # the crate catches at every rig
    assert max(onsets) - min(onsets) <= 0.1 * min(onsets), runs  # and at about the same turn
    assert all(r[1] < 0.7 for r in runs.values()), runs  # it is badly burned everywhere
    assert all(r[2] > 0.99 for r in runs.values()), runs  # the concrete wall survives everywhere
    # Known gap (docs/architecture.md): late in a burn the coarsest rig lags, because a coarse cell degrades as one
    # block. Not gated yet.


def test_a_small_fire_changes_nothing_at_any_rig(rigs, materials):
    for rig in rigs:
        onset, crate, wall = _burn(rig, materials, turns=60, power_w=20_000.0)
        assert onset is None, rig.name
        assert crate > 0.99, rig.name
        assert wall > 0.99, rig.name


# Wood's adiabatic flame temperature is about 2000 C: no fire burning on wood may heat any cell past it. Before
# heat.step refreshed source power after destruction, this scenario peaked at 16,619 C (0.2 m) and 29,213 C (0.1 m).
WOOD_FLAME_C = 2000.0


def test_a_fierce_fire_never_heats_any_cell_past_the_flame_temperature(rigs, materials):
    for rig in rigs:
        w = World.from_scene(SCENE, rig, materials)
        crate_s, crate_m = region_parts(w, "crate")
        assert crate_m["structure"].execute("ignite", {"power_w": 500_000.0, "radius_m": 0.3}).success
        peak = 0.0
        for _ in range(30):
            w.advance()
            peak = max(peak, float(np.max(w.grid.temperature)))
        assert crate_s["integrity"].value() < 0.5, rig.name  # it really burned
        assert peak < WOOD_FLAME_C, (rig.name, peak)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Known gap (docs/architecture.md): fires don't consume fuel. Once no solid is left under a fire, "
        "World._power_field deposits its power into air (207,350 C at 0.2 m by turn 50). Fix before the Phase 1 "
        "crate scenario is gated; this gate then flips and must be removed."
    ),
)
def test_a_fire_that_has_burned_its_fuel_stops_heating(materials):
    for name in FAST_TIERS:
        w = World.from_scene(SCENE, RigProfile.load(name), materials)
        _, crate_m = region_parts(w, "crate")
        assert crate_m["structure"].execute("ignite", {"power_w": 500_000.0, "radius_m": 0.3}).success
        peak = 0.0
        for _ in range(60):
            w.advance()
            peak = max(peak, float(np.max(w.grid.temperature)))
        assert peak < WOOD_FLAME_C, (name, peak)
