"""One deterministic tick of the slice: intents, then bodies, then fire, then physics (the tile spec's tick order).

No clock and no IO here: ``Sim.step`` takes the tick's intents and runs exactly one tick of the engine's
``Simulation``, so the same intents give the same state, which is what replay checks (``replay``). The server paces it
to the wall clock from outside. The fire and the body's heat only decide; every change to the world is a record the
tick hands to ``Simulation.step``, which applies them through the applier in one write window, then runs physics.
"""

from __future__ import annotations

import hashlib
import math
import struct
from collections.abc import Iterable, Sequence
from dataclasses import astuple, replace

import numpy as np

from maxim_overdrive import data
from simcore.core.applier import Outcome
from simcore.core.frames import CellFrame
from simcore.core.intents import RECORD_KIND_OF, Action, Extinguish, Ignite, LogRecord
from simcore.core.intents import Strike as StrikeAction
from simcore.core.scene import Box
from simcore.core.simulation import SimConfig, Simulation
from simcore.core.world import World
from slice_server import alley, heat_debt, npc
from slice_server.body import Body, Cells, Command, blocked, check_no_tunnelling, impulse, step
from slice_server.config import NPC_STATES, SliceConfig
from slice_server.fire import Decision, Fire, FuelMaterial, Point, fuels_from, nearest_point
from slice_server.intents import Intent, Kindle, Move, Say, Strike
from slice_server.reach import nearest_in_front

CHEST_M = 1.0  # where on the body radiation and air temperature are read, above the feet
# The records' actors, in the order a tick applies them (the log's key orders by actor after kind and apply_us): the
# player's strike, as an intent, comes before the fire's changes, as it did when strikes applied on arrival.
PLAYER, FIRE = 1, 2
TICK_US = 100_000


class Sim:
    def __init__(self, config: SliceConfig, *, dx_m: float = 0.2, tick_s: float = 0.1) -> None:
        if round(tick_s * 1_000_000) != TICK_US:
            raise ValueError(f"the slice runs the engine's {TICK_US} us tick, not {tick_s} s")
        check_no_tunnelling(config.body, tick_s, dx_m)
        self.config, self.tick_s, self.tick = config, tick_s, 0
        scene, table = alley.scene(), data.materials()
        self.world = World(scene.build(table, dx_m=dx_m), limits=data.action_limits())  # kept to read its sources
        # Physics every tick, not the engine's default of every fifth: the slice's fire and heat were tuned on a
        # 0.1 s step, and a playtest has to feel the cadence it is tuned on (the plan's week 4).
        self._engine = Simulation(self.world, config=SimConfig(tick_us=TICK_US, physics_every=1))
        self._pending: list[tuple[int, str, Action]] = []  # this tick's records: actor, target, action
        self._seq = {PLAYER: 0, FIRE: 0}
        self.body = Body(*alley.SPAWN_M, feet_z=alley.FLOOR_TOP_M)
        self.command = Command()
        self.heat = heat_debt.start(config.heat)
        self.fire = Fire(config.fuel.fire, _fuels(config, scene.primitives, table))
        self._check_fits_the_limits()
        v = config.npc.vendor
        self.vendor = Body(v.stall_x, v.stall_y, feet_z=alley.FLOOR_TOP_M, yaw=math.pi)
        self.vendor_state, self.charges = "idle", v.charges
        if blocked(
            Cells(self.frame.solid, self.frame.dx_m), self.vendor.x, self.vendor.y, self.vendor.feet_z, config.body
        ):
            raise ValueError(f"the vendor's stall ({v.stall_x}, {v.stall_y}) is inside a solid")

    def _check_fits_the_limits(self) -> None:
        limits, radius = self.world.limits, self.config.fuel.fire.source_radius_m
        if not limits.min_radius_m <= radius <= limits.max_radius_m:
            raise ValueError(f"fire.source_radius_m {radius} is outside the action limits")
        for fuel in self.fire.fuels.values():
            if fuel.peak_power_w() > limits.max_power_w:
                raise ValueError(f"the {fuel.name} would burn at {fuel.peak_power_w():.0f} W, over the action limits")
        st = self.config.strike
        if not limits.min_sigma_m <= st.sigma_m <= limits.max_sigma_m:
            raise ValueError(f"strike.sigma_m {st.sigma_m} is outside the action limits")
        if max(st.energy_j, st.overdrive_energy_j) > limits.max_energy_j:
            raise ValueError(f"a strike's energy is over the action limits' {limits.max_energy_j:.0f} J")

    @property
    def frame(self) -> CellFrame:
        return self._engine.frames.latest.cells

    def step(self, intents: Sequence[Intent]) -> list[dict[str, object]]:
        """One tick. Returns the events it caused, for the client and the session log."""
        events = [e for intent in intents if (e := self._take(intent)) is not None]
        frame = self.frame
        command = self._effective(self.command)
        cells = Cells(frame.solid, frame.dx_m)
        step(self.body, command, cells, self.config.body, self.tick_s)
        events += self._vendor_step(cells)
        self._heat_body(command)
        decisions, fire_events = self.fire.step(self.tick_s)
        for decision in decisions:
            self._apply(decision)
        events += fire_events + self._after_fire(fire_events)
        self._run_engine_tick(events)
        self.tick += 1
        return events

    def _submit(self, actor: int, target: str, action: Action) -> None:
        self._pending.append((actor, target, action))

    def _run_engine_tick(self, events: list[dict[str, object]]) -> None:
        """Hand the tick's records to the engine, which applies them and runs physics in one window, and check each
        was applied: reach and powers were checked against the limits before submitting, so a refusal is a bug."""
        records = []
        for actor, target, action in self._pending:
            self._seq[actor] += 1
            kind = RECORD_KIND_OF[type(action)]
            records.append(LogRecord(self._engine.tick, 0, actor, self._seq[actor], kind, target, action))
        self._pending = []
        report = self._engine.step(records)
        for record, outcome in zip(records, report.outcomes, strict=True):
            if not outcome.success:
                raise RuntimeError(f"the applier refused the {record.kind} on the {record.target}: {outcome.error}")
        strikes = iter(o for r, o in zip(records, report.outcomes, strict=True) if r.kind == "strike")
        for event in events:
            if event["what"] == "strike" and event["ok"]:
                event["destroyed_m3"] = _destroyed_m3(next(strikes))

    def _take(self, intent: Intent) -> dict[str, object] | None:
        if isinstance(intent, Move):
            self.command = intent.command
            return None
        if isinstance(intent, Kindle):
            return self._kindle()
        if isinstance(intent, Strike):
            return self._strike()
        if isinstance(intent, Say):
            return None  # words reach the vendor's voice on the server, never the simulation
        raise TypeError(f"not an intent: {type(intent).__name__}")  # a programming error: intents are parsed first

    def _effective(self, command: Command) -> Command:
        """A tripped body has no Overdrive and runs slow."""
        if not self.heat.tripped:
            return command
        return replace(command, effort=command.effort * self.config.heat.tripped_speed_factor, overdrive=False)

    def _chest(self) -> Point:
        return (self.body.x, self.body.y, self.body.feet_z + CHEST_M)

    def _heat_body(self, command: Command) -> None:
        heat_debt.step(
            self.heat,
            self.config.heat,
            overdrive=command.overdrive and command.effort > 0,
            air_c=air_mean_c(self.frame, self._chest(), self.config.heat.sense_radius_m),
            radiant_w_m2=self.fire.flux_at(self._chest()),
            in_puddle=alley.in_puddle(self.body.x, self.body.y),
            dt=self.tick_s,
        )

    def _apply(self, decision: Decision) -> None:
        if decision.out:
            action: Ignite | Extinguish = Extinguish()
        else:
            # The cells get the convective share only: the radiated share (radiant_fraction) leaves the flame,
            # some of it reaching skins and bodies (fire.flux_at), the rest exported unreceived, as the tile spec
            # books flame radiation. Without the debit, radiation would add energy on top of the world's.
            fire = self.config.fuel.fire
            action = Ignite(decision.power_w * (1.0 - fire.radiant_fraction), fire.source_radius_m)
        self._submit(FIRE, decision.region, action)  # powers were checked against the limits at start

    def _kindle(self) -> dict[str, object]:
        burnable = ((n, f.bounds) for n, f in self.fire.fuels.items() if not f.burnt_out)
        target = nearest_in_front(self.body, burnable, self.config.kindle.reach_m)
        if target is None:
            return {"type": "event", "what": "kindle", "ok": False, "error": "nothing that burns within reach"}
        why_not = self.fire.kindle(target)
        return {"type": "event", "what": "kindle", "region": target, "ok": why_not is None, "error": why_not}

    def _strike(self) -> dict[str, object]:
        """Hit the nearest named solid in front: cracks where it lands; in Overdrive, harder, with heat and recoil."""
        s, b = self.config.strike, self.body
        solids = (
            (n, r.footprint.bounds_m)
            for n, r in self.frame.regions.items()
            if r.solid and n != "floor" and r.cells.any()
        )
        target = nearest_in_front(b, solids, s.reach_m)
        if target is None:
            return {"type": "event", "what": "strike", "ok": False, "error": "nothing within reach"}
        overdrive = self._effective(self.command).overdrive
        point = nearest_point(self.frame.regions[target].footprint.bounds_m, self._chest())
        energy = s.overdrive_energy_j if overdrive else s.energy_j
        self._submit(PLAYER, target, StrikeAction(energy, s.sigma_m, point))  # applied at the tick's end
        if overdrive:
            heat_debt.add_heat(self.heat, self.config.heat, s.overdrive_heat_j)
            impulse(b, -math.cos(b.yaw) * s.recoil_ns, -math.sin(b.yaw) * s.recoil_ns, self.config.body)
        return {"type": "event", "what": "strike", "region": target, "ok": True, "overdrive": overdrive,
                "energy_j": energy, "destroyed_m3": 0.0}  # fmt: skip  # filled in once the engine applies it

    def _vendor_step(self, cells: Cells) -> list[dict[str, object]]:
        """Perceive (by oracle), decide, move, and douse through the fire and the applier."""
        v, b = self.vendor, self.body
        burning = [
            npc.SeenFire(f.name, f.centroid, f.bounds, f.power_w()) for f in self.fire.fuels.values() if f.burning
        ]
        seen = npc.Perception(
            self.fire.flux_at((v.x, v.y, v.feet_z + CHEST_M)), burning, b.x, b.y, self.heat.core_c,
            self.config.heat.warn_c, self.charges,
        )  # fmt: skip
        decision = npc.decide(v, seen, self.config.npc.vendor)
        step(v, decision.command, cells, self.config.body, self.tick_s)
        if decision.command.effort == 0.0:
            npc.face(v, *self._facing_point(decision, b))
        if decision.douse is not None:
            self.fire.douse(decision.douse)  # an ask: the fire commits it in its step, beside the world's change
        return self._vendor_becomes(decision.state, decision.target)

    def _vendor_becomes(self, state: str, target: str | None) -> list[dict[str, object]]:
        """A change of the vendor's state, as a structured event: the server's voice turns it into words."""
        if state == self.vendor_state:
            return []
        self.vendor_state = state
        return [{"type": "event", "what": "npc", "state": state, "target": target, "player_core_c": self.heat.core_c}]

    def _after_fire(self, fire_events: list[dict[str, object]]) -> list[dict[str, object]]:
        """A douse the fire committed spends the vendor's charge (only the vendor douses)."""
        events = []
        for event in fire_events:
            if event["what"] == "doused":
                self.charges -= 1
                event["by"] = "vendor"
                events += self._vendor_becomes("doused", str(event["region"]))
        return events

    def _facing_point(self, decision: npc.NpcDecision, player: Body) -> tuple[float, float]:
        if decision.target is not None:
            c = self.fire.fuels[decision.target].centroid
            return c[0], c[1]
        return player.x, player.y

    def overdrive_on(self) -> bool:
        """Whether Overdrive is actually on this tick: held, moving, and not tripped."""
        return self._effective(self.command).overdrive and self.command.effort > 0

    def chest(self) -> Point:
        return self._chest()

    def digest(self) -> str:
        """Every bit of state that replay must reproduce, and that later ticks depend on: cells, body, command, heat,
        the vendor, the fires (their growth clocks included) and the world's heat sources."""
        f, h = self.frame, hashlib.sha256()
        for array in (f.material, f.integrity, f.temperature):
            h.update(array.tobytes())
        numbers = [
            *astuple(self.body),
            *astuple(self.command),
            *astuple(self.heat),
            *astuple(self.vendor),
            self.charges,
        ]
        numbers.append(NPC_STATES.index(self.vendor_state))
        for fuel in self.fire.fuels.values():
            numbers += [fuel.fuel_kg, fuel.skin_c, fuel.released_j, fuel.burning, fuel.burnt_out, fuel.burning_s]
        numbers += [src.power_w for _, src in sorted(self.world.sources.items())]
        h.update(struct.pack(f"<{len(numbers)}d", *(float(n) for n in numbers)))
        h.update(struct.pack("<qd", self.tick, f.time_s))
        return h.hexdigest()


def _destroyed_m3(outcome: Outcome) -> float:
    return float(sum(e.destroyed_volume_m3 for e in outcome.effects))


def _fuels(config: SliceConfig, primitives: Sequence[object], table: object) -> dict:
    """The fire's fuels: the fuel file's numbers with each material's density and heat capacity from the world."""
    boxes = {p.name: (p.material, p.bounds_m) for p in primitives if isinstance(p, Box) and p.name}
    materials = {}
    for name, entry in config.fuel.materials.items():
        m = table[name]  # type: ignore[index]
        materials[name] = FuelMaterial(
            entry.releasable_energy_j_kg, entry.ignition_c, entry.burn_rate_kg_s_m2,
            m.density_kg_m3, m.density_kg_m3 * m.specific_heat_j_kgk,
        )  # fmt: skip
    fire = config.fuel.fire
    return fuels_from(
        boxes,
        config.fuel.objects,
        materials,
        floor_z=alley.FLOOR_TOP_M,
        ambient_c=fire.ambient_c,
        growth_s=fire.growth_s,
    )


def air_mean_c(frame: CellFrame, centre: Point, radius_m: float) -> float:
    """The mean temperature of the air cells within ``radius_m`` of ``centre``: a reduction over a volume in metres.
    Cells are weighted by whether their centre is inside, which is coarse for a 1 m sphere of 0.2 m cells, and
    accepted in this lane: no outcome is decided from it, only a heat flow."""
    dx, (nx, ny, nz) = frame.dx_m, frame.shape
    lo = [max(0, math.floor((c - radius_m) / dx)) for c in centre]
    hi = [min(n, math.ceil((c + radius_m) / dx)) for c, n in zip(centre, (nx, ny, nz), strict=True)]
    ii, jj, kk = (np.arange(a, b) for a, b in zip(lo, hi, strict=True))
    x, y, z = ((ii + 0.5) * dx)[:, None, None], ((jj + 0.5) * dx)[None, :, None], ((kk + 0.5) * dx)[None, None, :]
    inside = (x - centre[0]) ** 2 + (y - centre[1]) ** 2 + (z - centre[2]) ** 2 <= radius_m**2
    window = np.s_[lo[0] : hi[0], lo[1] : hi[1], lo[2] : hi[2]]
    air = inside & (frame.material[window] == 0)
    if not air.any():  # a body's chest is always in air; no air here means the body is inside a solid, a bug
        raise RuntimeError(f"no air within {radius_m} m of {centre}")
    return float(np.asarray(frame.temperature)[window][air].mean())


def replay(config: SliceConfig, ticks: Iterable[Sequence[Intent]], *, dx_m: float = 0.2) -> str:
    """Rerun a session from its intents, one sequence per tick, and return the final digest."""
    sim = Sim(config, dx_m=dx_m)
    for intents in ticks:
        sim.step(intents)
    return sim.digest()
