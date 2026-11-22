import dataclasses

import numpy as np
import pytest
from slice_server import config
from slice_server.body import Body, Command
from slice_server.intents import Kindle, Move
from slice_server.sim import Sim, replay
from slice_server.view import client_state

_LOADED = config.load()
C = dataclasses.replace(  # no extinguisher charge: these tests watch the player and the fire, not the vendor
    _LOADED, npc=dataclasses.replace(_LOADED.npc, vendor=dataclasses.replace(_LOADED.npc.vendor, charges=0))
)


def _crate_hottest(sim: Sim) -> float:
    f = sim.frame
    return float(np.asarray(f.temperature)[f.regions["crate"].cells].max())


def test_kindling_in_front_of_the_crate_lights_it_through_the_applier() -> None:
    sim = Sim(C)
    sim.body = Body(5.4, 2.9, 0.4, yaw=0.0)  # 0.6 m from the crate's west face, facing it
    before = _crate_hottest(sim)
    events = [e for e in sim.step([Kindle()]) if e["what"] == "kindle"]  # the vendor may react in the same tick
    assert events == [{"type": "event", "what": "kindle", "region": "crate", "ok": True, "error": None}]
    assert "fire:crate" in sim.world.sources
    for _ in range(50):
        sim.step([])
    # The fire grows as t^2 over 90 s, so after 5 s it has released little: the crate warms, but barely.
    assert _crate_hottest(sim) > before
    state = client_state(sim)
    (burning,) = state["burning"]
    assert burning["region"] == "crate"
    assert burning["at"] == pytest.approx([6.3, 2.9, 0.7])


def test_kindling_with_nothing_in_reach_changes_nothing() -> None:
    sim = Sim(C)  # at the spawn, 1.7 m from the nearest wall corner
    events = sim.step([Kindle()])
    assert events[0]["ok"] is False
    assert not sim.world.sources


def test_a_target_behind_the_body_is_not_lit() -> None:
    sim = Sim(C)
    sim.body = Body(5.4, 2.9, 0.4, yaw=np.pi)  # facing away from the crate
    assert sim.step([Kindle()])[0]["ok"] is False


def _script(turn: float) -> list[list]:
    east = Move(Command(1.0, 0.0, 1.0))
    veer = Move(Command(0.0, turn, 1.0, overdrive=True))
    return [[east]] + [[]] * 30 + [[veer]] + [[]] * 10 + [[Kindle()]] + [[]] * 5


def test_replay_is_bit_identical_and_can_tell_two_sessions_apart() -> None:
    assert replay(C, _script(1.0)) == replay(C, _script(1.0))
    assert replay(C, _script(1.0)) != replay(C, _script(-1.0))


def test_the_body_walks_into_the_alley_from_the_spawn() -> None:
    sim = Sim(C)
    for _ in range(20):
        sim.step([Move(Command(1.0, 0.0, 1.0))])
    assert sim.body.x > 2.5
    state = client_state(sim)
    assert state["tick"] == 20
    assert set(state["cells"]) == {"material", "crack", "glow", "heat"}
    assert state["burning"] == []
