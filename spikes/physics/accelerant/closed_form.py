"""E4(i): one wet node, adiabatic behind, under a constant flux q'': its T_b plateau lasts m_L L_v / q''
to within one substep (preregistration §3). Uses the model's own kernel, wetbed.evaporate (spike, never in src/)."""

from __future__ import annotations

import numpy as np
from acc_constants import NOMINAL as p
from wetbed import evaporate


def plateau(q: float, m_l: float, dt: float) -> tuple[float, float]:
    """Integrate one node from ambient; return (time spent with liquid at T_b, closed form m_L L_v / q)."""
    cap_w = np.array([p.rho_wood * p.c_wood * p.skin_m])
    t = np.array([p.t_amb])
    liq = np.array([m_l])
    t_wet = 0.0
    e_in = 0.0
    for _ in range(int(1e7)):
        t_new = t + dt * q / (cap_w + liq * p.c_l)
        e_in += q * dt
        t, liq, dm = evaporate(t_new, liq, cap_w, t_b=p.t_b, l_v=p.l_v, c_l=p.c_l, t0=p.t_amb)
        if dm[0] > 0:
            t_wet += dt
        if liq[0] <= 0:
            break
    return t_wet, m_l * p.l_v / q


def plateau_interpolated(q: float, m_l: float, dt: float) -> float:
    """Added after the substep-count measurement missed (a disclosed deviation): the plateau from the instant the
    node reaches T_b (interpolated in its crossing substep) to the instant it dries (the share of the last substep's
    energy that evaporated liquid)."""
    cap_w = np.array([p.rho_wood * p.c_wood * p.skin_m])
    t = np.array([p.t_amb])
    liq = np.array([m_l])
    clock = 0.0
    start = None
    for _ in range(int(1e7)):
        t_new = t + dt * q / (cap_w + liq * p.c_l)
        if start is None and t_new[0] > p.t_b:
            start = clock + dt * (p.t_b - t[0]) / (t_new[0] - t[0])
        t, liq, dm = evaporate(t_new, liq, cap_w, t_b=p.t_b, l_v=p.l_v, c_l=p.c_l, t0=p.t_amb)
        if liq[0] <= 0:
            return clock + dt * dm[0] * p.l_v / (q * dt) - (start or 0.0)
        clock += dt
    return float("nan")


def main() -> None:
    worst = 0.0
    for q in (5e3, 15.9e3, 40e3):
        for m_l in (0.064, 0.488):
            for dt in (0.05, 0.5 / 7):
                got, want = plateau(q, m_l, dt)
                ok = abs(got - want) <= dt
                worst = max(worst, abs(got - want) / dt)
                print(
                    f"q={q / 1e3:5.1f} kW/m2 m_L={m_l:.3f} dt={dt:.4f}: plateau {got:8.3f} s, "
                    f"closed form {want:8.3f} s, {'PASS' if ok else 'MISS'}"
                )
    print(
        f"E4(i) first measurement (substep count): worst |error| / dt = {worst:.3f} "
        f"({'PASS' if worst <= 1 else 'MISS'})"
    )
    worst_i = 0.0
    for q in (5e3, 15.9e3, 40e3):
        for m_l in (0.064, 0.488):
            for dt in (0.05, 0.5 / 7):
                worst_i = max(worst_i, abs(plateau_interpolated(q, m_l, dt) - m_l * p.l_v / q) / dt)
    print(f"E4(i) interpolated (deviation, added after the miss): worst |error| / dt = {worst_i:.2e}")


if __name__ == "__main__":
    main()
