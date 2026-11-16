"""Environment regions speak Maxim's SEM protocols."""

import pytest

from maxim_overdrive import Box, Scene, World
from maxim_overdrive.config import ActionLimits
from maxim_overdrive.sem_env import bridge


def _world(rig, materials):
    return World.from_scene(
        Scene((2.0, 3.0, 2.4), (Box((0.8, 0, 0), (1.2, 3, 2.4), "concrete", "wall"),)), rig, materials
    )


def test_strike_moves_the_integrity_sensor(rig, materials):
    w = _world(rig, materials)
    sensors, mods = bridge.region_parts(w, "wall", limits=ActionLimits.load())
    assert sensors["integrity"].read().value == pytest.approx(1.0)
    res = mods["structure"].execute("strike", {"energy_j": 6.3e7, "sigma_m": 0.3, "point_m": [0.8, 1.5, 1.2]})
    assert res.success
    assert res.metadata["destroyed_volume_m3"] > 0
    assert sensors["integrity"].read().value < 1.0
    assert sensors["breached"].read().value == 1.0


def test_bad_actions_fail_cleanly(rig, materials):
    _, mods = bridge.region_parts(_world(rig, materials), "wall", limits=ActionLimits.load())
    assert not mods["structure"].execute("extinguish", {}).success  # nothing burning
    assert not mods["structure"].execute("strike", {}).success  # missing energy
    assert not mods["structure"].execute("teleport", {}).success


def test_regions_are_real_maxim_entities(rig, materials):
    sem = pytest.importorskip("maxim.embodiment.sem")
    Modulator, Sensor = sem.Modulator, sem.Sensor
    ent = bridge.to_maxim_entity(_world(rig, materials), "wall", limits=ActionLimits.load())
    assert all(isinstance(s, Sensor) for s in ent.sensors.values())
    assert all(isinstance(m, Modulator) for m in ent.modulators.values())
    readings = ent.read_all_sensors()
    assert set(readings) == {"integrity", "temperature_max", "temperature_mean", "breached"}
    assert "strike" in ent.modulators["structure"].affordances
