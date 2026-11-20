"""`simcore.protocol.encoding.snapshot`: what the client draws from, each channel against its defining formula."""

from __future__ import annotations

import numpy as np
import pytest

from maxim_overdrive import data
from simcore.core.scene import Box, Scene
from simcore.core.world import World
from simcore.protocol.encoding import GLOW_FULL_C, GLOW_START_C, snapshot

LIMITS = data.action_limits()


def _grid(dx_m, materials):
    return World.from_scene(
        Scene((2.0, 2.0, 2.0), (Box((0.8, 0, 0), (1.2, 2, 2), "concrete", "wall"),)),
        materials,
        dx_m=dx_m,
        limits=LIMITS,
    ).grid


def test_snapshot_shapes_dtypes_and_metadata(dx_m, materials):
    g = _grid(dx_m, materials)
    s = snapshot(g)
    assert s["shape"] == g.shape
    assert s["cell_size_m"] == g.dx
    assert s["time_s"] == g.time_s
    for key, dtype in [("material", np.uint8), ("crack", np.uint8), ("glow", np.uint8), ("temperature_c", np.float16)]:
        arr = s[key]
        assert isinstance(arr, np.ndarray)
        assert arr.shape == g.shape, key
        assert arr.dtype == dtype, key


def test_an_intact_cold_world_has_no_crack_and_no_glow(dx_m, materials):
    s = snapshot(_grid(dx_m, materials))
    assert not np.asarray(s["crack"]).any()  # air has integrity 0 but is not "cracked"
    assert not np.asarray(s["glow"]).any()


def test_crack_is_one_minus_integrity_on_solids(dx_m, materials):
    g = _grid(dx_m, materials)
    wall = g.regions["wall"].cells
    g.integrity[wall] = 0.5
    crack = np.asarray(snapshot(g)["crack"])
    assert (crack[wall] == 128).all()  # round(0.5 * 255) under numpy's round-half-even
    assert (crack[~g.solid] == 0).all()


def test_glow_starts_at_the_draper_point():
    assert GLOW_START_C == 525.0  # where hot solids first glow visibly red
    assert GLOW_FULL_C == 1500.0


@pytest.mark.parametrize(
    ("temp_c", "expected"),
    [
        (GLOW_START_C - 1.0, 0),
        (GLOW_START_C, 0),
        (GLOW_START_C + 0.25 * (GLOW_FULL_C - GLOW_START_C), 64),  # linear: a smoothstep would give 40
        ((GLOW_START_C + GLOW_FULL_C) / 2, 128),
        (GLOW_START_C + 0.75 * (GLOW_FULL_C - GLOW_START_C), 191),
        (GLOW_FULL_C, 255),
        (GLOW_FULL_C + 1000.0, 255),
    ],
)
def test_glow_ramps_from_the_draper_point_on_solids_only(dx_m, materials, temp_c, expected):
    g = _grid(dx_m, materials)
    g.temperature[:] = temp_c
    glow = np.asarray(snapshot(g)["glow"])
    assert (glow[g.solid] == expected).all()
    assert (glow[~g.solid] == 0).all()  # hot air does not glow


def test_temperature_is_clamped_to_the_float16_range_it_promises(dx_m, materials):
    g = _grid(dx_m, materials)
    g.temperature[:] = 1.0e9
    t = np.asarray(snapshot(g)["temperature_c"])
    assert np.isfinite(t).all()
    assert t.max() == pytest.approx(6000.0, rel=1e-3)
    g.temperature[:] = -1.0e9
    t = np.asarray(snapshot(g)["temperature_c"])
    assert t.min() == pytest.approx(-273.0, rel=1e-3)


def test_snapshot_arrays_do_not_alias_the_grid(dx_m, materials):
    g = _grid(dx_m, materials)
    s = snapshot(g)
    np.asarray(s["material"])[:] = 99
    assert (g.material != 99).all()
