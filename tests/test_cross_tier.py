"""The verification rule on a full turn loop: a fire on a crate, and on a concrete wall, at every grid.

The truth grid (0.1 m) agrees with the reference (0.05 m, under MAXIM_OVERDRIVE_ALL_TIERS=1) and converges from the
coarse grid (0.2 m) (world_model §1.1), measured through ``simcore.verify`` (docs/design/verify_harness.md).

These scenarios refine space and time together: World substeps each turn at a floor that scales as 1 / dx**2, so the
physics step shrinks with the spacing. Agreement here is the shipped discretisation's, not space's alone; step 5a's
fixed physics step makes it space alone (its checklist). Heat's own studies (tests/test_heat.py) refine them apart.
"""

import numpy as np
import pytest

from maxim_overdrive import data
from simcore.adapters.sem.bridge import region_parts
from simcore.core.applier import Applier
from simcore.core.scene import Box, Scene
from simcore.core.world import World
from simcore.verify import agrees
from tests.conftest import FAST_SPACINGS

LIMITS = data.action_limits()
TURN = 1.0  # an onset is a whole turn: errors within one turn can't be told apart


SCENE = Scene(
    (3.0, 3.0, 2.0),
    (Box((1.2, 1.2, 0), (1.8, 1.8, 0.6), "wood", "crate"), Box((0, 0, 0), (0.6, 3.0, 2.0), "concrete", "wall")),
)


def _burn(dx_m, materials, turns=150, power_w=60_000.0):
    w = World.from_scene(SCENE, materials, dx_m=dx_m, limits=LIMITS)
    crate_s, crate_m = region_parts(Applier(w), w.frames, "crate")
    wall_s, wall_m = region_parts(Applier(w), w.frames, "wall")
    for mods in (crate_m, wall_m):  # preconditions raise RuntimeError, never a red gate's AssertionError
        if not mods["structure"].execute("ignite", {"power_w": power_w, "radius_m": 0.3}).success:
            raise RuntimeError("ignite refused: the test can't reach its bar")
    onset = None
    for turn in range(turns):
        w.advance()
        if onset is None and crate_s["integrity"].value() < 0.9:
            onset = turn
    return onset, crate_s["integrity"].value(), wall_s["integrity"].value()


def test_fire_outcomes_agree_across_rigs(spacings, materials):
    grids = sorted(spacings, reverse=True)
    runs = {dx_m: _burn(dx_m, materials) for dx_m in grids}
    assert all(r[0] is not None for r in runs.values()), runs  # the crate catches at every grid
    onset = agrees(lambda dx_m: runs[dx_m][0], grids, quantum=TURN)
    assert onset.spread <= 0.1 * min(onset.values), onset  # at about the same turn (the bar is unchanged)
    # Converges from coarse (all grids only). Measured 2026-11-21: onset 94, 92, 90 at 0.2, 0.1, 0.05 m.
    assert onset.converging is not False, onset
    assert all(r[1] < 0.7 for r in runs.values()), runs  # it is badly burned everywhere
    assert all(r[2] > 0.99 for r in runs.values()), runs  # the concrete wall survives everywhere
    # Known gap (docs/architecture.md): the coarsest rig lags in the burn; gated below.


BADLY_BURNED = 0.7  # the level test_fire_outcomes_agree_across_rigs asserts every rig reaches
TIME_TOL = 0.15  # tile_and_client.md §6.3 item 8: a crack-like time converges within 15% of the finer grid's


def _turn_below(dx_m, materials, level, turns=300, power_w=60_000.0):
    w = World.from_scene(SCENE, materials, dx_m=dx_m, limits=LIMITS)
    crate_s, crate_m = region_parts(Applier(w), w.frames, "crate")
    wall_m = region_parts(Applier(w), w.frames, "wall")[1]
    for mods in (crate_m, wall_m):
        if not mods["structure"].execute("ignite", {"power_w": power_w, "radius_m": 0.3}).success:
            raise RuntimeError("ignite refused: the gate can't reach its bar")
    for turn in range(turns):
        w.advance()
        if crate_s["integrity"].value() < level:
            return turn
    raise RuntimeError(f"the crate never fell below {level} in {turns} turns at {dx_m} m")


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "Known gap (docs/architecture.md): the coarsest rig lags in the burn, because a coarse cell degrades as one "
        "block. Measured 2026-11-21: the crate falls below 0.7 at turn 138 at 0.2 m against 104 at 0.1 m (33%, "
        "against tile §6.3's 15%); below 0.5 the lag is 152 against 135 (12.6%). The fix is the reconstructed burn "
        "rate (roadmap Phase 2, 'Close the known gap'); this gate then flips and must be removed."
    ),
)
def test_the_crate_is_badly_burned_at_the_same_turn_at_every_rig(materials):
    turn = agrees(lambda dx_m: _turn_below(dx_m, materials, BADLY_BURNED), sorted(FAST_SPACINGS, reverse=True))
    assert turn.errors[0] <= TIME_TOL * turn.values[-1], turn


def test_a_small_fire_changes_nothing_at_any_rig(spacings, materials):
    for dx_m in spacings:
        onset, crate, wall = _burn(dx_m, materials, turns=60, power_w=20_000.0)
        assert onset is None, dx_m
        assert crate > 0.99, dx_m
        assert wall > 0.99, dx_m


# Wood's adiabatic flame temperature is about 2000 C: no fire burning on wood may heat any cell past it. Before
# heat.step refreshed source power after destruction, this scenario peaked at 16,619 C (0.2 m) and 29,213 C (0.1 m).
WOOD_FLAME_C = 2000.0


def test_a_fierce_fire_never_heats_any_cell_past_the_flame_temperature(spacings, materials):
    for dx_m in spacings:
        w = World.from_scene(SCENE, materials, dx_m=dx_m, limits=LIMITS)
        crate_s, crate_m = region_parts(Applier(w), w.frames, "crate")
        assert crate_m["structure"].execute("ignite", {"power_w": 500_000.0, "radius_m": 0.3}).success
        peak = 0.0
        for _ in range(30):
            w.advance()
            peak = max(peak, float(np.max(w.grid.temperature)))
        assert crate_s["integrity"].value() < 0.5, dx_m  # it really burned
        assert peak < WOOD_FLAME_C, (dx_m, peak)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "Known gap (docs/architecture.md): fires don't consume fuel. Once no solid is left under a fire, "
        "World._power_field deposits its power into air (207,350 C at 0.2 m by turn 50). Fix before the Phase 1 "
        "crate scenario is gated; this gate then flips and must be removed."
    ),
)
def test_a_fire_that_has_burned_its_fuel_stops_heating(materials):
    for dx_m in FAST_SPACINGS:
        w = World.from_scene(SCENE, materials, dx_m=dx_m, limits=LIMITS)
        _, crate_m = region_parts(Applier(w), w.frames, "crate")
        # A precondition raises RuntimeError, not the gate's raises= type, so a refused ignite can't count as the miss.
        if not crate_m["structure"].execute("ignite", {"power_w": 500_000.0, "radius_m": 0.3}).success:
            raise RuntimeError("ignite refused: the gate can't reach its bar")
        peak = 0.0
        for _ in range(60):
            w.advance()
            peak = max(peak, float(np.max(w.grid.temperature)))
        assert peak < WOOD_FLAME_C, (dx_m, peak)
