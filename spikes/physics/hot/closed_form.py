"""E3: closed forms of the two new terms, on the model's own code (preregistration §3; spike, never in src/).

(i)   The steady surface balance: one interior Iw cell at fixed char mass, fixed G, no draught, constant flame flux,
      stepped by HotBed._step_iw to steady state. T_c must equal the bisection root of
      (1 - chi_r) q''_f + eps sigma T_n^4 - eps sigma T_c^4 - k_c (T_c - T_f) / delta_c = 0 to 0.5 K, and the volatile
      flux k_c (T_c - T_f) / (delta_c L_g) to 0.1 %. The §0 table's rows are printed beside it.
(ii)  The front stalls: at T_c <= T_f the volatile flux is exactly zero.
(iii) The gas cap: one flaming cell with prescribed Q, fb, m and t_in leaves at min(T_fl, t_in + (1 - chi_r)(Q - fb)
      / (m c_p)) to 1e-12 relative, on both branches.
(iv)  Mz: the cap of a column with prescribed releases equals McCaffrey's dT in each of his three regions.
Usage: closed_form.py   (PYTHONPATH=../bed:../accelerant); the output is results/closed_form.txt.
"""

from __future__ import annotations

import numpy as np
from constants import SIGMA_SB
from hot_constants import NOMINAL
from hotbed import HotBed

P = NOMINAL.with_(loading_wood=0.0, ignite_base_m=0.6)
C = (1, 1, 1)  # the interior cell of the 0.2 m grid


def bisect(f, lo: float, hi: float) -> float:
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if f(lo) * f(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


def steady(m_c: float, t_n: float) -> tuple[float, float, float, float]:
    """(model T_c, closed-form T_c, model m'', closed-form m'') for char mass m_c, neighbours at t_n (K)."""
    p = P
    b = HotBed(p, 0.2, 0)
    g = np.zeros_like(b.G)
    g[C] = 4 * SIGMA_SB * t_n**4
    gabs = p.eps * g / 4.0
    zero = np.zeros_like(g)
    direct = np.where(b.A_iw > 0, (1 - p.chi_r) * p.q_f * b.A_iw, 0.0)
    for _ in range(200000):
        b.c_iw[C] = m_c
        b.w_iw[C] = 5.0
        t_prev = b.Ts_iw[C]
        b._step_iw(0.01, gabs, q_gas_iw=zero, q_ox_iw=zero, r_c_iw=zero, direct_w=direct)
        if abs(b.Ts_iw[C] - t_prev) < 1e-12:
            break
    kc, tf = p.k_c, p.t_f
    d = max(m_c / p.rho_c, p.skin_m)
    q_in = (1 - p.chi_r) * p.q_f + p.eps * SIGMA_SB * t_n**4
    t_cf = bisect(lambda t: q_in - p.eps * SIGMA_SB * t**4 - kc / d * (t - tf), 300.0, 3000.0)
    return float(b.Ts_iw[C]), t_cf, float(b.mvol[C]), kc * (t_cf - tf) / (d * p.l_g)


def stall() -> float:
    b = HotBed(P, 0.2, 0)
    t = np.full_like(b.Ts_iw, P.t_f)
    t[0, 0, 0] = P.t_f - 1.0
    return float(np.abs(b.front_flux(t)).max())


def gas_cap(q_w: float, mdot: float) -> tuple[float, float]:
    """(model exit temperature, closed form) for one flaming cell at the bottom of its column."""
    p = P
    b = HotBed(p.with_(ignite_base_m=0.0), 0.2, 0)
    cell = (1, 1, 0)
    b.A_iw[cell] = 0.05
    b.w_iw[cell] = 5.0
    b.flaming[cell] = True
    b.fl_iw[cell] = True
    b.Gcol[:] = 0.0
    b.Gcol[1, 1] = mdot / b.Af
    qdot = np.zeros_like(b.G)
    qdot[cell] = q_w
    fb = np.zeros_like(b.G)
    fb[cell] = p.q_f * b.A_iw[cell]
    temps = {k: np.full_like(b.G, b.T0) for k in ("ui", "iw", "ic", "ia")}
    b._draught(temps, qdot, np.minimum(fb, qdot))
    want = min(p.t_fl, b.T0 + (1 - p.chi_r) * (q_w - fb[cell]) / (mdot * p.cp_air))
    return b.gas_exit[0], want


def mz() -> list[tuple[float, float, float]]:
    """(x, model cap - T0, hand-computed dT) for two columns of three flaming cells: all three regions."""
    p = P.with_(gas_cap="mccaffrey_z")
    b = HotBed(p.with_(ignite_base_m=0.0), 0.2, 0)
    fl = np.ones((b.n, b.n), dtype=bool)
    qdot = np.zeros_like(b.G)
    qdot[..., 0], qdot[..., 1], qdot[..., 2] = 20e3, 0.5e3, 0.5e3  # W: column (0, 0) flame and intermittent
    qdot[2, 2, :] = 0.3e3  # column (2, 2): the plume region
    col = {"z0": np.full((b.n, b.n), np.nan), "q": np.zeros((b.n, b.n))}
    t0, g = b.T0, 9.81
    out = []
    caps = [b._cap_column(k, fl, qdot, col) for k in range(b.n)]
    for ij in ((0, 0), (2, 2)):
        qc = 0.0
        for k in range(b.n):
            qc += qdot[ij][k] / 1e3
            out.append(_mcc_case((k + 1) * 0.2 / qc**0.4, caps[k][ij] - t0, t0, g))
    return out


def _mcc_case(x: float, got: float, t0: float, g: float) -> tuple[float, float, float]:
    """McCaffrey's dT at x written out by hand, region by region, beside the model's."""
    if x < 0.08:
        want = t0 * (6.8 / 0.9) ** 2 / (2 * g)
    elif x < 0.20:
        want = t0 * (1.9 / 0.9) ** 2 / (2 * g) / x
    else:
        want = t0 * (1.1 / 0.9) ** 2 / (2 * g) * x ** (-5.0 / 3.0)
    return x, got, want


def main() -> None:
    ok = True
    print("(i) steady surface balance, interior cell, (1 - chi_r) q''_f = 17.5 kW/m2, nominal k_c and rho_c")
    for m_c in (0.05, 0.375, 0.75, 1.5):
        for t_n_c in (380.0, 600.0):
            tm, tc, mm, mc = steady(m_c, t_n_c + 273.15)
            good = abs(tm - tc) <= 0.5 and abs(mm - mc) <= 1e-3 * mc
            ok &= good
            print(
                f"  m_c={m_c:5.3f} T_n={t_n_c:4.0f} C: T_c model {tm - 273.15:7.2f} closed {tc - 273.15:7.2f} C; "
                f"m'' model {mm * 1e3:6.3f} closed {mc * 1e3:6.3f} g/m2s  {'PASS' if good else 'MISS'}"
            )
    s = stall()
    ok &= s == 0.0
    print(f"(ii) front flux at T_c = T_f - 1 K and at T_f: max {s:.1e} W/m2  {'PASS' if s == 0.0 else 'MISS'}")
    for q_w, mdot, label in ((3e3, 2e-3, "energy-limited"), (200e3, 2e-3, "capped at T_fl")):
        got, want = gas_cap(q_w, mdot)
        good = abs(got - want) <= 1e-12 * want
        ok &= good
        print(f"(iii) {label}: exit {got:.12f} K, closed form {want:.12f} K  {'PASS' if good else 'MISS'}")
    for x, got, want in mz():
        good = abs(got - want) <= 1e-9 * want
        ok &= good
        print(f"(iv) Mz x={x:.4f} m/kW^0.4: cap - T0 {got:.6f} K, McCaffrey {want:.6f} K  {'PASS' if good else 'MISS'}")
    print(f"E3: {'PASS' if ok else 'MISS'}")


if __name__ == "__main__":
    main()
