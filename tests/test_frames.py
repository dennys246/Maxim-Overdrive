"""Observation reads published frames (boundaries §4.2, B-10; §4.4, B-13).

A frame is published at the end of each tick that applied a record or ran physics, stamped with that tick, and frame 0
at construction (sim_core.md §4). A reading taken from it is an immutable sample: it does not change when the world
moves on. Instruments hold a frame feed, never the world, and
nothing they report carries the grid spacing.
"""

from __future__ import annotations

import dataclasses
import gc
import math

import pytest

from maxim_overdrive import data
from simcore.adapters.sem import bridge
from simcore.core import frames
from simcore.core.grid import MaterialGrid
from simcore.core.scene import Box, Scene, constructing
from simcore.core.simulation import Simulation
from simcore.core.world import World
from tests._cells import paint
from tests._sim import SteppingPort, make, physics_steps, world_of

LIMITS = data.action_limits()
MATERIALS = data.materials()
SCENE = Scene(
    (3.0, 3.0, 2.0),
    (Box((1.2, 1.2, 0), (1.8, 1.8, 0.6), "wood", "crate"), Box((0, 0, 0), (0.6, 3.0, 2.0), "concrete", "wall")),
)


def _sim() -> Simulation:
    return make(SCENE, MATERIALS, dx_m=0.2, limits=LIMITS)


def _readings(frame: frames.Observation) -> dict[tuple[str, str], float]:
    return {(r, q): frame.reading(r, q) for r in frame.region_names for q in frames.QUANTITIES}


def test_a_reading_taken_at_one_frame_is_unchanged_after_the_world_moves_on():
    sim = _sim()
    _, crate = bridge.region_parts(SteppingPort(sim), sim.frames, "crate")
    assert crate["structure"].execute("ignite", {"power_w": 500_000.0, "radius_m": 0.3}).success
    frame = sim.frames.latest
    before = _readings(frame)
    stamp = (frame.sequence, frame.tick, frame.time_s)
    physics_steps(sim, 36)  # the three 6 s turns this ran before PR 4a
    assert crate["structure"].execute("strike", {"energy_j": 4.0e7, "sigma_m": 0.3}).success
    assert _readings(frame) == before
    assert (frame.sequence, frame.tick, frame.time_s) == stamp
    later = _readings(sim.frames.latest)
    assert later[("crate", "temperature_max")] > before[("crate", "temperature_max")]  # the world did move on
    assert later[("crate", "integrity")] < before[("crate", "integrity")]


def test_a_frame_is_stamped_with_the_tick_and_the_time_it_was_published_at():
    sim = _sim()
    assert (sim.frames.latest.sequence, sim.frames.latest.tick, sim.frames.latest.time_s) == (0, 0, 0.0)
    physics_steps(sim, 1)  # ticks 1-4 are quiet and publish nothing; tick 5 runs physics and publishes
    assert (sim.frames.latest.sequence, sim.frames.latest.tick, sim.frames.latest.time_s) == (1, 5, 0.5)


def test_a_frames_regions_do_not_follow_a_later_paint():
    sim = _sim()
    grid = world_of(sim).grid
    frame = sim.frames.latest
    with constructing(grid):
        paint(grid, grid.regions["crate"].cells, "air")
    assert sim.frames.latest is frame  # only a tick publishes (sim_core.md §4)
    assert frame.reading("crate", "integrity") == 1.0
    physics_steps(sim, 1)
    assert sim.frames.latest.reading("crate", "integrity") == 0.0  # the next tick's frame shows the paint
    assert math.isnan(sim.frames.latest.reading("crate", "temperature_mean"))


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
    sim = _sim()
    sensors, mods = bridge.region_parts(SteppingPort(sim), sim.frames, "crate")
    for part in [*sensors.values()]:
        assert not any(isinstance(o, (Simulation, World, MaterialGrid)) for o in _reachable(part)), part
    # The modulator holds a port, which its test or host owns (it is the write half, sim_core.md §13); the
    # membrane's own surface holds no simulation, world or grid.
    assert {type(v).__name__ for v in vars(mods["structure"]).values()} == {"SteppingPort", "str"}


def test_the_observation_protocol_offers_no_way_to_the_world():
    surface = {name for name in vars(frames.Observation) if not name.startswith("_")}
    assert surface == {"sequence", "tick", "time_s", "region_names", "is_solid", "reading"}
    assert not surface & {"advance", "sources", "grid", "cells", "writing"}
    assert {name for name in vars(frames.FrameSource) if not name.startswith("_")} == {"latest"}


def test_a_reading_refuses_an_unknown_quantity_or_region():
    frame = _sim().frames.latest
    with pytest.raises(ValueError, match="unknown region quantity 'colour'"):
        frame.reading("crate", "colour")
    with pytest.raises(ValueError, match="no region 'door'"):  # delta review, Trust D-N6: one exception type
        frame.reading("door", "integrity")


def test_the_feed_publishes_frames_in_order_only():
    first = _sim().frames.latest
    feed = frames.FrameFeed(first)
    with pytest.raises(ValueError, match="does not follow"):
        feed.publish(first)
    # One frame per tick at most, in tick order (sim_core.md §4): the next sequence stamped with no later tick is
    # refused, and a later tick is accepted.
    with pytest.raises(ValueError, match="can't follow tick 0"):
        feed.publish(frames.Frame(dataclasses.replace(first.cells, sequence=1)))
    feed.publish(frames.Frame(dataclasses.replace(first.cells, sequence=1, tick=1, time_us=100_000)))
    assert feed.latest.tick == 1


def test_nothing_an_instrument_or_an_entity_reports_carries_the_cell_size():
    # BF-N4 (boundaries §4.4): the grid spacing is the simulation's, not something an observer can sense.
    sim = _sim()
    sensors, _ = bridge.region_parts(SteppingPort(sim), sim.frames, "crate")
    for s in sensors.values():
        assert s.read().extra == {}
        assert s.read().timestamp == sim.frames.latest.time_s
    ent = bridge.to_maxim_entity(SteppingPort(sim), sim.frames, "crate")
    assert "cell_size_m" not in ent.metadata


def test_a_frame_refuses_writable_arrays_and_a_grid_whose_window_is_open():
    # Step 3b review, Executor N6 and Architecture N2: frozen means deep, of the type, not only of CellFrame.of.
    import numpy as np  # noqa: PLC0415

    from simcore.core.writers import WindowClosed  # noqa: PLC0415

    sim = _sim()
    grid = world_of(sim).grid
    cells = sim.frames.latest.cells
    with pytest.raises(ValueError, match="read-only"):
        dataclasses.replace(cells, temperature=np.zeros(cells.shape))
    with constructing(grid), pytest.raises(WindowClosed, match="open"):
        frames.CellFrame.of(grid, 1, tick=1, time_us=100_000)


def test_the_feed_an_observer_holds_cannot_publish():
    # Step 3b review, Architecture N3: a forged frame with time_s=1e9 was accepted through the membrane's feed.
    sim = _sim()
    assert not hasattr(sim.frames, "publish")
    assert {n for n in dir(sim.frames) if not n.startswith("_")} == {"latest"}


@pytest.mark.parametrize("bad", [["integrity"], {"q": 1}, 7])
def test_an_unhashable_or_odd_quantity_or_region_is_a_value_error(bad):
    sim = _sim()
    with pytest.raises(ValueError, match="unknown region quantity"):
        sim.frames.latest.reading("crate", bad)
    with pytest.raises(ValueError, match="unknown region quantity"):
        bridge.RegionInstrument(sim.frames, "crate", bad)
    with pytest.raises(ValueError, match="no region"):
        bridge.RegionInstrument(sim.frames, bad, "integrity")
