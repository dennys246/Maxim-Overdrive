"""Observation reads published frames (boundaries §4.2, B-10; §4.4, B-13).

A frame is published after each write window: each intent application and each advance. A reading taken from it is
an immutable sample: it does not change when the world moves on. Instruments hold a frame feed, never the world, and
nothing they report carries the grid spacing.
"""

from __future__ import annotations

import gc
import math

import pytest

from maxim_overdrive import data
from simcore.adapters.sem import bridge
from simcore.core import frames
from simcore.core.grid import MaterialGrid
from simcore.core.scene import Box, Scene
from simcore.core.world import World

LIMITS = data.action_limits()
MATERIALS = data.materials()
SCENE = Scene(
    (3.0, 3.0, 2.0),
    (Box((1.2, 1.2, 0), (1.8, 1.8, 0.6), "wood", "crate"), Box((0, 0, 0), (0.6, 3.0, 2.0), "concrete", "wall")),
)


def _world() -> World:
    return World.from_scene(SCENE, MATERIALS, dx_m=0.2, limits=LIMITS)


def _readings(frame: frames.Observation) -> dict[tuple[str, str], float]:
    return {(r, q): frame.reading(r, q) for r in frame.region_names for q in frames.QUANTITIES}


def test_a_reading_taken_at_one_frame_is_unchanged_after_the_world_moves_on():
    w = _world()
    _, crate = bridge.region_parts(w, "crate")
    assert crate["structure"].execute("ignite", {"power_w": 500_000.0, "radius_m": 0.3}).success
    frame = w.frames.latest
    before = _readings(frame)
    stamp = (frame.sequence, frame.time_s)
    for _ in range(3):
        w.advance()
    assert crate["structure"].execute("strike", {"energy_j": 4.0e7, "sigma_m": 0.3}).success
    assert _readings(frame) == before
    assert (frame.sequence, frame.time_s) == stamp
    later = _readings(w.frames.latest)
    assert later[("crate", "temperature_max")] > before[("crate", "temperature_max")]  # the world did move on
    assert later[("crate", "integrity")] < before[("crate", "integrity")]


def test_a_frame_is_stamped_with_the_time_it_was_published_at():
    w = _world()
    assert (w.frames.latest.sequence, w.frames.latest.time_s) == (0, 0.0)
    w.advance()
    assert (w.frames.latest.sequence, w.frames.latest.time_s) == (1, w.turn_seconds)


def test_a_frames_regions_do_not_follow_a_later_paint():
    w = _world()
    frame = w.frames.latest
    with w.grid.writing():
        w.grid.paint(w.grid.regions["crate"].cells, "air")
    assert frame.reading("crate", "integrity") == 1.0
    assert w.frames.latest.reading("crate", "integrity") == 0.0  # the paint published a frame of its own
    assert math.isnan(w.frames.latest.reading("crate", "temperature_mean"))


def _reachable(root: object, depth: int = 6) -> list[object]:
    seen, frontier, out = {id(root)}, [root], []
    for _ in range(depth):
        nxt = []
        for obj in frontier:
            for ref in gc.get_referents(obj):
                if id(ref) not in seen and not isinstance(ref, type):
                    seen.add(id(ref))
                    nxt.append(ref)
        out += nxt
        frontier = nxt
    return out


def test_an_instrument_and_a_modulator_hold_no_world_and_no_grid():
    w = _world()
    sensors, mods = bridge.region_parts(w, "crate")
    for part in [*sensors.values()]:
        assert not any(isinstance(o, (World, MaterialGrid)) for o in _reachable(part)), part
    # The modulator holds an applier, which holds the world (it is the write half); the membrane's own surface doesn't.
    assert {type(v).__name__ for v in vars(mods["structure"]).values()} == {"Applier", "str"}


def test_the_observation_protocol_offers_no_way_to_the_world():
    surface = {name for name in vars(frames.Observation) if not name.startswith("_")}
    assert surface == {"sequence", "time_s", "region_names", "is_solid", "reading"}
    assert not surface & {"advance", "sources", "grid", "cells", "writing"}
    assert {name for name in vars(frames.FrameSource) if not name.startswith("_")} == {"latest"}


def test_a_reading_refuses_an_unknown_quantity_or_region():
    frame = _world().frames.latest
    with pytest.raises(ValueError, match="unknown region quantity 'colour'"):
        frame.reading("crate", "colour")
    with pytest.raises(KeyError, match="no region 'door'"):
        frame.reading("door", "integrity")


def test_the_feed_publishes_frames_in_order_only():
    w = _world()
    feed = w.frames
    stale = feed.latest
    with pytest.raises(ValueError, match="does not follow"):
        feed.publish(stale)


def test_nothing_an_instrument_or_an_entity_reports_carries_the_cell_size():
    # BF-N4 (boundaries §4.4): the grid spacing is the simulation's, not something an observer can sense.
    w = _world()
    sensors, _ = bridge.region_parts(w, "crate")
    for s in sensors.values():
        assert s.read().extra == {}
        assert s.read().timestamp == w.frames.latest.time_s
    ent = bridge.to_maxim_entity(w, "crate")
    assert "cell_size_m" not in ent.metadata
