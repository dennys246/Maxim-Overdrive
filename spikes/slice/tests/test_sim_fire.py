"""The fire and the body's heat through the real simulation and applier: what reaches the world, not only what the
fire module books."""

import dataclasses

import numpy as np
import pytest
from slice_server import config
from slice_server.body import Body, Command
from slice_server.intents import Kindle, Move
from slice_server.sim import Sim

from maxim_overdrive import data

# The vendor has no extinguisher charge here, so these tests watch the fire and the body, not the vendor dousing it.
_LOADED = config.load()
C = dataclasses.replace(
    _LOADED, npc=dataclasses.replace(_LOADED.npc, vendor=dataclasses.replace(_LOADED.npc.vendor, charges=0))
)
RHO_C = np.zeros(256)
for _id, _m in data.materials().by_id.items():
    RHO_C[_id] = _m.density_kg_m3 * _m.specific_heat_j_kgk


def _energy_j(sim: Sim) -> float:
    f = sim.frame
    return float((RHO_C[f.material] * np.asarray(f.temperature)).sum() * f.dx_m**3)


def _at_the_crate(cfg: config.SliceConfig = C) -> Sim:
    sim = Sim(cfg)
    sim.body = Body(5.4, 2.9, 0.4, yaw=0.0)  # 0.6 m from the crate's west face, facing it
    return sim


def test_the_cells_gain_exactly_the_energy_the_fire_releases() -> None:
    # Wire integrity: the fire's bookkeeping says what it released; this checks the world actually received it.
    sim = _at_the_crate()
    before = _energy_j(sim)
    sim.step([Kindle()])
    for _ in range(300):  # 30 s of t-squared growth: about 0.4 MJ
        sim.step([])
    released = sim.fire.fuels["crate"].released_j
    assert released > 3e5
    assert _energy_j(sim) - before == pytest.approx(released, rel=1e-6)


def test_a_burnt_out_object_leaves_no_fire_in_the_world() -> None:
    tiny = dataclasses.replace(C, fuel=dataclasses.replace(C.fuel, objects={**C.fuel.objects, "crate": 0.0001}))
    sim = _at_the_crate(tiny)
    sim.step([Kindle()])
    assert "fire:crate" in sim.world.sources
    events = []
    for _ in range(300):
        events += sim.step([])
    assert {"type": "event", "what": "burnt_out", "region": "crate"} in events
    assert "fire:crate" not in sim.world.sources
    # A burnt-out crate is no longer a target: there is nothing left in reach that burns.
    assert sim.step([Kindle()])[0]["error"] == "nothing that burns within reach"


def test_a_neighbour_that_ignites_gets_a_fire_in_the_world() -> None:
    sim = _at_the_crate()
    sim.step([Kindle()])
    sim.fire.fuels["pallet"].skin_c = C.fuel.materials["wood"].ignition_c + 5.0  # past ignition: lights this tick
    events = sim.step([])
    assert any(e["what"] == "ignited" and e["region"] == "pallet" for e in events)
    assert "fire:pallet" in sim.world.sources


def test_only_something_that_burns_is_kindled() -> None:
    sim = Sim(C)
    sim.body = Body(5.4, 2.0, 0.4, yaw=-np.pi / 2)  # facing the south wall, 1.6 m from it
    assert sim.step([Kindle()])[0]["ok"] is False
    assert not sim.world.sources


def test_a_tripped_body_runs_slow_without_overdrive() -> None:
    sim = Sim(C)
    sim.body = Body(2.0, 2.0, 0.4)
    sim.heat.tripped_s = 100.0
    core = sim.heat.core_c
    for _ in range(30):
        sim.step([Move(Command(1.0, 0.0, 1.0, overdrive=True))])
    assert sim.body.vx == pytest.approx(C.body.walk_speed_m_s * C.heat.tripped_speed_factor, rel=0.01)
    assert sim.heat.core_c <= core, "no Overdrive heat while tripped"


def test_the_state_carries_heat_fires_and_the_puddle() -> None:
    sim = _at_the_crate()
    sim.step([Kindle()])
    state = sim.state()
    assert state["heat"]["core_c"] == pytest.approx(C.heat.start_c, abs=0.5)
    assert state["heat"]["flux_w_m2"] > 0, "the burning crate radiates on the body"
    fires = {f["region"]: f for f in state["fires"]}
    assert fires["crate"]["burning"]
    assert not fires["pallet"]["burning"]
    assert len(state["puddle"]) == 4
