"""The resolution rule on a full turn loop: a fire on a crate, and on a concrete wall, at every rig."""

from maxim_overdrive import Box, Scene, World
from maxim_overdrive.sem_env.bridge import region_parts

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
