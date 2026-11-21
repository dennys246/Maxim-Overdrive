import dataclasses
import math

import pytest
from slice_server import config, heat_debt
from slice_server.heat_debt import BodyHeat

P = config.load().heat


def _run(h: BodyHeat, seconds: float, p=P, **kw) -> BodyHeat:
    args = {"overdrive": False, "air_c": 20.0, "radiant_w_m2": 0.0, "in_puddle": False} | kw
    for _ in range(round(seconds / 0.1)):
        heat_debt.step(h, p, dt=0.1, **args)
    return h


def test_with_no_sources_the_node_relaxes_to_the_air_by_the_closed_form() -> None:
    # Explicit Euler on dT/dt = -hA/C (T - Ta) gives T_n = Ta + (T0 - Ta)(1 - hA dt / C)^n exactly.
    dry = dataclasses.replace(P, coolant_kg=0.0, coolant_refill_kg_s=0.0)
    h = _run(BodyHeat(60.0, 0.0), 30.0, dry)
    want = 20.0 + 40.0 * (1 - P.h_a_w_k * 0.1 / P.capacity_j_k) ** 300
    assert h.core_c == pytest.approx(want, rel=1e-12)


FIRE_1M = 0.3 * 357e3 / (4 * math.pi)  # a full crate fire (357 kW, 30% radiated) at 1 m: 8.5 kW/m^2


def _time_to_trip(limit_s: float = 900.0, **kw) -> float | None:
    h, t = heat_debt.start(P), 0.0
    while not h.tripped and t < limit_s:
        _run(h, 0.1, **kw)
        t += 0.1
    return t if h.tripped else None


# Tuning checks, not physics bars: they hold the ladder the body file promises, so a retune that breaks the shape of
# the loop (where you stand decides how long you can push) goes red.


def test_overdrive_in_still_air_runs_on_coolant_until_it_is_spent_then_trips() -> None:
    h = heat_debt.start(P)
    t = _time_to_trip(overdrive=True)
    assert t is not None
    assert 120 < t < 240, f"two to four minutes of Overdrive in still air (got {t:.0f} s)"
    _run(h, t, overdrive=True)
    assert h.coolant_kg < 0.2 * P.coolant_kg, "the coolant ran low first: that is the debt"


def test_where_you_stand_decides_how_long_you_can_push() -> None:
    still = _time_to_trip(overdrive=True)
    near_fire = _time_to_trip(radiant_w_m2=FIRE_1M)
    both = _time_to_trip(overdrive=True, radiant_w_m2=FIRE_1M)
    assert still is not None
    assert near_fire is not None
    assert both is not None
    assert both < 45
    assert both < near_fire < still
    assert _time_to_trip(overdrive=True, in_puddle=True) is None, "the puddle saves you"


def test_the_puddle_refills_coolant() -> None:
    h = BodyHeat(50.0, 0.0)
    _run(h, 2.0, in_puddle=True)
    assert h.coolant_kg > 0.3 * P.coolant_kg


def test_a_trip_holds_for_trip_s_after_the_core_cools_below_trip() -> None:
    h = BodyHeat(P.trip_c + 1, 0.0)
    _run(h, 0.1)
    assert h.tripped
    h.core_c = P.trip_c - 5.0  # cooled below the trip point
    _run(h, P.trip_s - 0.5)
    assert h.tripped
    _run(h, 1.0)
    assert not h.tripped


def test_a_burst_of_heat_past_the_trip_point_trips_at_once() -> None:
    # Executor N2: add_heat's trip branch had no test.
    h = BodyHeat(P.trip_c - 1.0, P.coolant_kg)
    heat_debt.add_heat(h, P, 2.0 * P.capacity_j_k)  # +2 K
    assert h.tripped
    assert h.tripped_s == P.trip_s
    cool = BodyHeat(40.0, P.coolant_kg)
    heat_debt.add_heat(cool, P, P.capacity_j_k)
    assert not cool.tripped
