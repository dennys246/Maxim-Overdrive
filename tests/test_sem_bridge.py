"""Environment regions speak Maxim's SEM protocols."""

import pytest

from maxim_overdrive import data
from simcore.adapters.sem import bridge
from simcore.core.scene import Box, Scene
from simcore.core.world import World

LIMITS = data.action_limits()


def _world(dx_m, materials):
    return World.from_scene(
        Scene((2.0, 3.0, 2.4), (Box((0.8, 0, 0), (1.2, 3, 2.4), "concrete", "wall"),)),
        materials,
        dx_m=dx_m,
        limits=LIMITS,
    )


def test_strike_moves_the_integrity_sensor(dx_m, materials):
    w = _world(dx_m, materials)
    sensors, mods = bridge.region_parts(w, "wall")
    assert sensors["integrity"].read().value == pytest.approx(1.0)
    res = mods["structure"].execute("strike", {"energy_j": 6.3e7, "sigma_m": 0.3, "point_m": [0.8, 1.5, 1.2]})
    assert res.success
    assert res.metadata["destroyed_volume_m3"] > 0
    assert sensors["integrity"].read().value < 1.0
    assert sensors["breached"].read().value == 1.0


def test_bad_actions_fail_cleanly(dx_m, materials):
    _, mods = bridge.region_parts(_world(dx_m, materials), "wall")
    assert not mods["structure"].execute("extinguish", {}).success  # nothing burning
    assert not mods["structure"].execute("strike", {}).success  # missing energy
    assert not mods["structure"].execute("teleport", {}).success


def test_regions_are_real_maxim_entities(dx_m, materials):
    sem = pytest.importorskip("maxim.embodiment.sem")
    Modulator, Sensor = sem.Modulator, sem.Sensor
    ent = bridge.to_maxim_entity(_world(dx_m, materials), "wall")
    assert all(isinstance(s, Sensor) for s in ent.sensors.values())
    assert all(isinstance(m, Modulator) for m in ent.modulators.values())
    readings = ent.read_all_sensors()
    assert set(readings) == {"integrity", "temperature_max", "temperature_mean", "breached"}
    assert "strike" in ent.modulators["structure"].affordances
    # A wire value from a fixed vocabulary, never a module path, so a later move can't change it silently (W10).
    assert ent.metadata["source"] == "overdrive_world"
