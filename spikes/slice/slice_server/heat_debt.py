"""Overdrive as heat debt (plan §3.4, ``world_v2.md`` §10): one lumped thermal node for a body's cyberware.

A lumped node is one temperature and one heat capacity standing for a whole part: it holds heat, and every flow in
or out is a power in watts. The cyberware's node:

- gains ``overdrive_w`` while Overdrive is on, and the radiation it absorbs from fires;
- loses heat by convection to the air around the body, ``hA (T - T_air)``, where ``T_air`` is a reduction over a
  sphere of air in metres (a consumer reads at its own scale, never one cell);
- loses heat by boiling coolant, at ``latent_j_kg`` per kilogram, once it is above ``boil_c``, as fast as
  ``evap_max_kg_s`` allows and only while coolant remains. That is the debt: Overdrive runs on coolant, and coolant
  runs out. In the puddle (rain under the awning gap) coolant refills fast.

Above ``warn_c`` the HUD warns; at ``trip_c`` Overdrive cuts out and the body runs at ``tripped_speed_factor`` for
``trip_s``. Explicit Euler is enough here: the node's fastest rate, ``hA / C``, is about 0.003 per second, so a
0.1 s step is far inside stability.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HeatParams:
    capacity_j_k: float
    start_c: float
    overdrive_w: float
    h_a_w_k: float
    radiant_area_m2: float
    coolant_kg: float
    coolant_refill_kg_s: float
    puddle_refill_kg_s: float
    boil_c: float
    evap_max_kg_s: float
    latent_j_kg: float
    warn_c: float
    trip_c: float
    trip_s: float
    tripped_speed_factor: float
    sense_radius_m: float


@dataclass
class BodyHeat:
    core_c: float
    coolant_kg: float
    tripped_s: float = 0.0

    @property
    def tripped(self) -> bool:
        return self.tripped_s > 0.0


def start(p: HeatParams) -> BodyHeat:
    return BodyHeat(p.start_c, p.coolant_kg)


def step(
    h: BodyHeat,
    p: HeatParams,
    *,
    overdrive: bool,
    air_c: float,
    radiant_w_m2: float,
    in_puddle: bool,
    dt: float,
) -> None:
    """Advance the cyberware node one tick. ``overdrive`` is whether Overdrive is actually on (held, moving, and not
    tripped): the caller decides that, this function only books its heat."""
    heat_in = (p.overdrive_w if overdrive else 0.0) + radiant_w_m2 * p.radiant_area_m2
    convected = p.h_a_w_k * (h.core_c - air_c)
    evaporated = min(p.evap_max_kg_s, h.coolant_kg / dt) if h.core_c > p.boil_c else 0.0
    h.core_c += (heat_in - convected - evaporated * p.latent_j_kg) / p.capacity_j_k * dt
    refill = p.puddle_refill_kg_s if in_puddle else p.coolant_refill_kg_s
    h.coolant_kg = min(p.coolant_kg, h.coolant_kg - evaporated * dt + refill * dt)
    h.tripped_s = p.trip_s if h.core_c >= p.trip_c else max(0.0, h.tripped_s - dt)
