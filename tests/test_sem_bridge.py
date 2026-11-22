"""Environment regions speak Maxim's SEM protocols."""

import pytest

from maxim_overdrive import data
from simcore.adapters.sem import bridge
from simcore.core.applier import Outcome
from simcore.core.intents import Action
from simcore.core.scene import Box, Scene
from tests._sim import SteppingPort, make

LIMITS = data.action_limits()


def _sim(dx_m, materials):
    return make(
        Scene((2.0, 3.0, 2.4), (Box((0.8, 0, 0), (1.2, 3, 2.4), "concrete", "wall"),)),
        materials,
        dx_m=dx_m,
        limits=LIMITS,
    )


class _Recording(SteppingPort):
    """The test's port, keeping each outcome the tick reported."""

    def __init__(self, sim):
        super().__init__(sim)
        self.outcomes: list[Outcome] = []

    def submit(self, region: str, action: Action) -> Outcome:
        self.outcomes.append(super().submit(region, action))
        return self.outcomes[-1]


def test_strike_moves_the_integrity_sensor(dx_m, materials):
    sim = _sim(dx_m, materials)
    port = _Recording(sim)
    sensors, mods = bridge.region_parts(port, sim.frames, "wall")
    assert sensors["integrity"].read().value == pytest.approx(1.0)
    res = mods["structure"].execute("strike", {"energy_j": 6.3e7, "sigma_m": 0.3, "point_m": [0.8, 1.5, 1.2]})
    assert res.success
    # The destroyed volume and absorbed energy are host-side effects in the tick's report, never in what the agent
    # is handed (sim_core.md §4, §13).
    assert "destroyed_volume_m3" not in res.metadata
    assert "absorbed_j" not in res.metadata
    assert port.outcomes[-1].effects[0].destroyed_volume_m3 > 0
    assert sensors["integrity"].read().value < 1.0
    assert sensors["breached"].read().value == 1.0


def test_the_membrane_steps_only_through_its_port_one_tick_per_call(materials):
    # sim_core.md §13's interim rule: execute submits one record and the port runs one tick for it, so the caller
    # sees the effect at once and world time moves one tick per call. The port is the test's; the membrane never
    # holds the simulation.
    sim = _sim(0.2, materials)
    port: bridge.Port = SteppingPort(sim)
    _, mods = bridge.region_parts(port, sim.frames, "wall")
    assert mods["structure"].execute("ignite", {"power_w": 1000.0}).success
    assert (sim.tick, sim.frames.latest.tick) == (2, 1)
    assert not mods["structure"].execute("ignite", {"power_w": -1.0}).success  # stage 1 refuses: no record, no tick
    assert sim.tick == 2
    assert port.limits is sim.limits


def test_bad_actions_fail_cleanly(dx_m, materials):
    sim = _sim(dx_m, materials)
    _, mods = bridge.region_parts(SteppingPort(sim), sim.frames, "wall")
    assert not mods["structure"].execute("extinguish", {}).success  # nothing burning
    assert not mods["structure"].execute("strike", {}).success  # missing energy
    assert not mods["structure"].execute("teleport", {}).success


def test_regions_are_real_maxim_entities(dx_m, materials):
    sem = pytest.importorskip("maxim.embodiment.sem")
    Modulator, Sensor = sem.Modulator, sem.Sensor
    sim = _sim(dx_m, materials)
    ent = bridge.to_maxim_entity(SteppingPort(sim), sim.frames, "wall")
    assert all(isinstance(s, Sensor) for s in ent.sensors.values())
    assert all(isinstance(m, Modulator) for m in ent.modulators.values())
    readings = ent.read_all_sensors()
    assert set(readings) == {"integrity", "temperature_max", "temperature_mean", "breached"}
    assert "strike" in ent.modulators["structure"].affordances
    # A wire value from a fixed vocabulary, never a module path, so a later move can't change it silently (W10).
    assert ent.metadata["source"] == "overdrive_world"
