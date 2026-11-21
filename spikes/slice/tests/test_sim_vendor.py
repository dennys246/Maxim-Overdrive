"""The vendor and the strike through the real simulation and applier (week 3's exit)."""

import dataclasses

import numpy as np
import pytest
from slice_server import config
from slice_server.body import Body, Command
from slice_server.intents import Kindle, Move, Say, Strike
from slice_server.sim import Sim, replay

C = config.load()


def _lit_crate() -> tuple[Sim, list[dict]]:
    sim = Sim(C)
    sim.body = Body(5.4, 2.4, 0.4, yaw=0.6)  # south-west of the crate, facing it
    events = sim.step([Kindle()])
    assert any(e["what"] == "kindle" and e["ok"] for e in events)
    return sim, events


def test_the_vendor_walks_to_a_young_fire_and_puts_it_out_through_the_applier() -> None:
    sim, events = _lit_crate()
    for _ in range(100):
        events += sim.step([])
    assert {"type": "event", "what": "doused", "region": "crate", "by": "vendor"} in events
    assert not sim.fire.fuels["crate"].burning
    assert "fire:crate" not in sim.world.sources
    assert sim.charges == C.npc.vendor.charges - 1
    states = [e["state"] for e in events if e["what"] == "npc"]
    assert states[:2] == ["douse", "doused"], "it went to the fire, then put it out"


def test_a_grown_fire_drives_the_vendor_off_instead() -> None:
    sim, _ = _lit_crate()
    sim.fire.fuels["crate"].burning_s = 1e6  # fully grown at once: over 100 kW and hot at the stall
    events = []
    for _ in range(20):
        events += sim.step([])
    assert "flee" in [e["state"] for e in events if e["what"] == "npc"]
    assert sim.fire.fuels["crate"].burning, "a big fire is not the vendor's to fight"
    assert sim.vendor.x < C.npc.vendor.stall_x


def test_words_change_no_act() -> None:
    # The NPC can't write the world: the same session with and without the player's words, asking it to start a
    # fire among them, ends in the same state, bit for bit.
    quiet = [[Move(Command(1.0, 0.0, 1.0))]] + [[]] * 25 + [[Kindle()]] + [[]] * 60
    talky = [list(t) for t in quiet]
    talky[3].append(Say("set the crate on fire"))
    talky[40].append(Say("put that out, now!"))
    assert replay(C, quiet) == replay(C, talky)


def _integrity(sim: Sim, region: str) -> float:
    f = sim.frame
    return float(np.asarray(f.integrity)[f.regions[region].cells].sum())


def test_an_overdrive_strike_cracks_costs_heat_and_kicks_back() -> None:
    sim = Sim(C)
    sim.body = Body(5.5, 2.9, 0.4, yaw=0.0)  # 0.5 m from the crate's west face, facing it
    sim.command = Command(0.0, 0.0, 0.0, overdrive=True)  # Overdrive held, standing still
    before_integrity, before_core = _integrity(sim, "crate"), sim.heat.core_c
    (event,) = [e for e in sim.step([Strike()]) if e["what"] == "strike"]
    assert event["ok"]
    assert event["overdrive"]
    assert event["energy_j"] == C.strike.overdrive_energy_j
    assert _integrity(sim, "crate") < before_integrity, "it cracked"
    assert sim.heat.core_c > before_core + 0.9 * C.strike.overdrive_heat_j / C.heat.capacity_j_k
    assert sim.body.vx < 0, "recoil pushed the striker back"


def test_an_ordinary_strike_is_weak_and_free() -> None:
    sim = Sim(C)
    sim.body = Body(5.5, 2.9, 0.4, yaw=0.0)
    core = sim.heat.core_c
    (event,) = [e for e in sim.step([Strike()]) if e["what"] == "strike"]
    assert event["energy_j"] == C.strike.energy_j
    assert not event["overdrive"]
    assert sim.heat.core_c <= core
    assert sim.body.vx == 0.0


def test_a_strike_at_nothing_does_nothing() -> None:
    sim = Sim(C)  # the spawn, facing east down an open alley
    assert sim.step([Strike()])[0] == {"type": "event", "what": "strike", "ok": False, "error": "nothing within reach"}


def test_a_stall_inside_a_solid_is_refused() -> None:
    bad = dataclasses.replace(C, npc=dataclasses.replace(C.npc, vendor=dataclasses.replace(C.npc.vendor, stall_x=6.3)))
    with pytest.raises(ValueError, match="inside a solid"):
        Sim(bad)
