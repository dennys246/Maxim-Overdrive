"""The vendor: a behaviour tree that decides, and nothing else (plan §3.5, VS2).

A behaviour tree is a fixed priority list of branches, each a condition and an action, evaluated every tick; the
first branch whose condition holds runs. It is the usual way games give an NPC readable, debuggable behaviour that
always does something sensible. This one, in priority order:

1. **flee** while the radiant flux on the vendor is over ``flee_flux_w_m2`` (2 kW/m^2 is painful within 45 s,
   ``fire_model.md`` §5): run to the safe spot by the alley's mouth;
2. **douse** a small fire (still growing, under ``small_fire_w``) within ``douse_range_m`` of the stall, while the
   extinguisher has a charge: walk to it and put it out from ``douse_reach_m``;
3. **warn** while any fire burns within ``warn_range_m``: stay put, facing it;
4. **comment** while the player is overheating within ``comment_range_m``: face them;
5. **idle**: go back to the stall and face the player.

It senses by oracle, on purpose (plan §3.5): it reads the fires, the flux and the player's core temperature
straight from the simulation, which lesson 24 rules out for real NPCs. ``decide`` returns a command for the vendor's
body and, when dousing, the fire to put out; the simulation applies both, the fire through the applier.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from slice_server.body import Body, Command
from slice_server.fire import Bounds, Point


@dataclass(frozen=True)
class NpcParams:
    stall_x: float
    stall_y: float
    safe_x: float
    safe_y: float
    effort: float
    flee_flux_w_m2: float
    douse_range_m: float
    douse_reach_m: float
    small_fire_w: float
    charges: int
    warn_range_m: float
    comment_range_m: float


@dataclass(frozen=True)
class SeenFire:
    region: str
    centroid: Point
    bounds: Bounds
    power_w: float


@dataclass(frozen=True)
class Perception:
    flux_w_m2: float
    fires: Sequence[SeenFire]  # the burning ones
    player_x: float
    player_y: float
    player_core_c: float
    player_warn_c: float
    charges: int


@dataclass(frozen=True)
class NpcDecision:
    state: str
    command: Command
    douse: str | None = None
    target: str | None = None  # the fire it is dousing or warning about, for its lines


def _toward(me: Body, x: float, y: float, effort: float, arrive_m: float = 0.15) -> Command:
    dx, dy = x - me.x, y - me.y
    dist = math.hypot(dx, dy)
    return Command() if dist <= arrive_m else Command(dx / dist, dy / dist, effort)


def _near(me: Body, bounds: Bounds) -> float:
    (x0, y0, _), (x1, y1, _) = bounds
    return math.hypot(min(max(me.x, x0), x1) - me.x, min(max(me.y, y0), y1) - me.y)


def decide(me: Body, seen: Perception, p: NpcParams) -> NpcDecision:
    if seen.flux_w_m2 > p.flee_flux_w_m2:
        return NpcDecision("flee", _toward(me, p.safe_x, p.safe_y, 1.0))
    douse = _douse(me, seen, p)
    if douse is not None:
        return douse
    near = [f for f in seen.fires if math.dist((me.x, me.y), f.centroid[:2]) <= p.warn_range_m]
    if near:
        return NpcDecision(
            "warn", Command(), target=min(near, key=lambda f: math.dist((me.x, me.y), f.centroid[:2])).region
        )
    if (
        seen.player_core_c >= seen.player_warn_c
        and math.hypot(seen.player_x - me.x, seen.player_y - me.y) <= p.comment_range_m
    ):
        return NpcDecision("comment", Command())
    return NpcDecision("idle", _toward(me, p.stall_x, p.stall_y, p.effort))


def _douse(me: Body, seen: Perception, p: NpcParams) -> NpcDecision | None:
    if seen.charges <= 0:
        return None
    small = [
        f for f in seen.fires
        if f.power_w <= p.small_fire_w and _near_stall(f, p) <= p.douse_range_m
    ]  # fmt: skip
    if not small:
        return None
    fire = min(small, key=lambda f: (_near(me, f.bounds), f.region))
    if _near(me, fire.bounds) <= p.douse_reach_m:
        return NpcDecision("douse", Command(), douse=fire.region, target=fire.region)
    (x0, y0, _), (x1, y1, _) = fire.bounds
    nx, ny = min(max(me.x, x0), x1), min(max(me.y, y0), y1)
    return NpcDecision("douse", _toward(me, nx, ny, p.effort, arrive_m=0.0), target=fire.region)


def _near_stall(fire: SeenFire, p: NpcParams) -> float:
    (x0, y0, _), (x1, y1, _) = fire.bounds
    return math.hypot(min(max(p.stall_x, x0), x1) - p.stall_x, min(max(p.stall_y, y0), y1) - p.stall_y)


def face(me: Body, x: float, y: float) -> None:
    """Turn the vendor to face a point (standing still, its yaw would otherwise keep its last heading)."""
    if math.hypot(x - me.x, y - me.y) > 1e-9:
        me.yaw = math.atan2(y - me.y, x - me.x)
