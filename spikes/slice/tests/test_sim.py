import dataclasses
import itertools

import numpy as np
import pytest
from slice_server import config
from slice_server.body import Body, Command
from slice_server.intents import Kindle, Move, Strike
from slice_server.sim import FIRE, Sim, replay
from slice_server.view import client_state

from simcore.core.intents import Ignite

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
    assert "fire:crate" in sim.sources
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
    assert not sim.sources


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


# The port onto the engine's Simulation (step 5a): the slice runs its tick, with physics on every tick.


def test_the_slice_runs_only_the_engines_tick() -> None:
    with pytest.raises(ValueError, match="100000 us tick"):
        Sim(C, tick_s=0.05)


def test_physics_runs_on_every_tick_not_the_engines_default_fifth() -> None:
    # Sim.digest is complete only at one tick per physics step (sim.py, ENGINE). At the engine's default of every
    # fifth (or any cadence above one), the burning crate's temperature would hold still between physics ticks.
    sim = Sim(C)
    sim.body = Body(5.4, 2.9, 0.4, yaw=0.0)
    sim.step([Kindle()])
    for _ in range(20):  # let the fire grow past nothing (t^2 from zero)
        sim.step([])
    temperatures = []
    for _ in range(5):
        sim.step([])
        temperatures.append(_crate_hottest(sim))
    assert all(b > a for a, b in itertools.pairwise(temperatures)), "heat moved on every tick"


def test_a_ticks_records_reach_the_engine_in_the_logs_key_order(monkeypatch: pytest.MonkeyPatch) -> None:
    # Executor S1: the slice built records in program order (player strikes, then the fire's), which is the key order
    # only while every kind ranks 30. With a strike ranked after an ignite, a relight-and-strike tick must still apply.
    from simcore.core import intents as engine_intents  # noqa: PLC0415 - the rank table this test patches

    ranks = {**engine_intents.KIND_RANK, "strike": 40}
    monkeypatch.setattr(engine_intents, "KIND_RANK", ranks)
    sim = Sim(C)
    sim.body = Body(5.5, 2.9, 0.4, yaw=0.0)
    events = sim.step([Kindle(), Strike()])  # one ignite record from the fire and one strike record from the player
    assert {e["what"] for e in events if e.get("ok")} >= {"kindle", "strike"}
    assert "fire:crate" in sim.sources


def test_a_refused_record_is_a_bug_and_says_so() -> None:
    # Executor N1: reach and powers are checked before submitting, so the engine refusing a record means the slice is
    # wrong; the tick says which record, instead of carrying on.
    sim = Sim(C)
    sim._submit(FIRE, "no_such_region", Ignite(1000.0, C.fuel.fire.source_radius_m))
    with pytest.raises(RuntimeError, match="refused the ignite on the no_such_region"):
        sim.step([])
