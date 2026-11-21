"""N7: the closed forms of fire_solid §6 rows 1-4, on the kernel as the graded runs use it (0.5 s, FDS's node rule).

1. Thick and thin t_ig, losses off (surface absorption, no emission, no convection), within 2%:
   thick t = (π kρc / 4)(ΔT/q)², thin t = ρcLΔT/q. The erfc profile at 60 s within 1% of the surface rise.
2. κ = 1e9 1/m (two-flux) against the surface-absorption mode, within 1e-6 (relative, surface T rise and node T).
3. 200 steps at ambient change no bit (inert slab and backing, two-flux, h = 13): every node T and mass identical.
4. Ambient rates exactly 0 for the published sets at 20 °C; an n = 0.5 node depletes to exactly 0.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import spec
from kernel import Component, Layer, Reaction, Solid
from materials import fds_cells, pine_cone, pmma_cone

DT = spec.DT_SHIPPED
T0 = 293.15
PM = dict(rho=1177.0, c=2130.0, k=0.20)  # NIST-StMU's thermal properties, inert


def _inert(kappa: float, eps: float = 1.0) -> Component:
    return Component("inert", PM["rho"], (300.0,), (PM["c"],), (300.0,), (PM["k"],), eps, kappa)


def _run(solid: Solid, q: float, t_end: float, h: float = 0.0) -> list[tuple[float, float]]:
    out = [(0.0, solid.t_face)]
    for i in range(1, round(t_end / DT) + 1):
        solid.step(DT, q, h, T0, T0)
        out.append((i * DT, solid.t_face))
    return out


def _cross(hist: list[tuple[float, float]], level: float) -> float:
    """Time the face first reaches `level`, linear between step ends."""
    for (t0, a), (t1, b) in zip(hist, hist[1:], strict=False):
        if b >= level > a:
            return t0 + (level - a) / (b - a) * (t1 - t0)
    return math.nan


def thick_and_thin() -> dict[str, Any]:
    q, d_t = 50e3, 300.0
    alpha = PM["k"] / (PM["rho"] * PM["c"])
    # thick: 25 mm is semi-infinite over the ~14 s (penetration 4·sqrt(αt) ≈ 4 mm)
    L = 0.025
    n = fds_cells(L, alpha)
    s = Solid([_inert(spec.KAPPA_DEFAULT)], [], [Layer(L, n, PM["rho"], (1.0,), False)], T0, surface_absorption=True, emission=False)
    hist = _run(s, q, 40.0)
    t_thick = math.pi * PM["k"] * PM["rho"] * PM["c"] / 4.0 * (d_t / q) ** 2
    got_thick = _cross(hist, T0 + d_t)
    # erfc profile at 60 s, same slab, node centres
    s = Solid([_inert(spec.KAPPA_DEFAULT)], [], [Layer(L, n, PM["rho"], (1.0,), False)], T0, surface_absorption=True, emission=False)
    _run(s, q, 60.0)
    x = (np.arange(n) + 0.5) * (L / n)
    t = 60.0
    r = math.sqrt(alpha * t)
    exact = 2 * q / PM["k"] * r / math.sqrt(math.pi) * np.exp(-(x**2) / (4 * alpha * t)) - q * x / PM["k"] * np.array(
        [math.erfc(v / (2 * r)) for v in x]
    )
    surf_rise = 2 * q / PM["k"] * r / math.sqrt(math.pi)
    prof_err = float(np.max(np.abs((s.T - T0) - exact)) / surf_rise)
    # thin: 0.5 mm, k raised to 1e3 so the slab is uniform (Bi ~ 0)
    Lt = 0.0005
    thin = Component("thin", PM["rho"], (300.0,), (PM["c"],), (300.0,), (1e3,), 1.0, spec.KAPPA_DEFAULT)
    s = Solid([thin], [], [Layer(Lt, 4, PM["rho"], (1.0,), False)], T0, surface_absorption=True, emission=False)
    hist = _run(s, q, 30.0)
    t_thin = PM["rho"] * PM["c"] * Lt * d_t / q
    got_thin = _cross(hist, T0 + d_t)
    return {
        "thick": {"closed_form_s": t_thick, "model_s": got_thick, "rel_err": got_thick / t_thick - 1, "nodes": n},
        "thin": {"closed_form_s": t_thin, "model_s": got_thin, "rel_err": got_thin / t_thin - 1},
        "erfc_60s_max_err_over_surface_rise": prof_err,
        "pass": abs(got_thick / t_thick - 1) <= 0.02 and abs(got_thin / t_thin - 1) <= 0.02 and prof_err <= 0.01,
    }


def kappa_limit() -> dict[str, Any]:
    """Inert NIST-StMU-like slab (ε 0.963, h 13), 50 kW/m² for 120 s: κ = 1e9 two-flux against surface absorption."""
    L = 0.00659
    n = fds_cells(L, PM["k"] / (PM["rho"] * PM["c"]))
    res = {}
    for name, sa, kap in (("surface", True, spec.KAPPA_DEFAULT), ("kappa_1e9", False, 1e9), ("kappa_2620", False, 2620.0)):
        s = Solid([_inert(kap, 0.963)], [], [Layer(L, n, PM["rho"], (1.0,), False)], T0, surface_absorption=sa)
        hist = _run(s, 50e3, 120.0, h=13.0)
        res[name] = {"face_T_120": hist[-1][1], "node_T": s.T.copy()}
    ref, lim = res["surface"], res["kappa_1e9"]
    rise = ref["face_T_120"] - T0
    face_err = (lim["face_T_120"] - ref["face_T_120"]) / rise
    node_err = float(np.max(np.abs(lim["node_T"] - ref["node_T"])) / rise)
    return {
        "face_T_120_K": {k: v["face_T_120"] for k, v in res.items()},
        "face_rel_err": face_err,
        "node_max_rel_err": node_err,
        "pass": abs(face_err) <= 1e-6 and node_err <= 1e-6,
    }


def ambient_bits() -> dict[str, Any]:
    """Inert PMMA on Superwool, two-flux, h 13, no heater: 200 steps must change no bit. With each published set's
    kinetics on, reported: their ambient rates are not zero (see `ambient_rates`)."""
    out: dict[str, Any] = {}
    b = pmma_cone(25, fds_h_r=True)
    inert = Solid(b.comps, [], b.layers, T0)
    t_before, m_before = inert.T.tobytes(), inert.m.tobytes()
    for _ in range(200):
        inert.step(DT, 0.0, 13.0, T0, T0)
    out["inert_unchanged"] = inert.T.tobytes() == t_before and inert.m.tobytes() == m_before
    for name, bb in (("pmma_set", b), ("pine_set", pine_cone(25, k_c=0.1, eps_char=0.75))):
        s = Solid(bb.comps, bb.reactions, bb.layers, T0)
        tb, mb = s.T.tobytes(), s.m.tobytes()
        for _ in range(200):
            s.step(DT, 0.0, 13.0, T0, T0)
        out[f"{name}_unchanged_reported"] = s.T.tobytes() == tb and s.m.tobytes() == mb
        out[f"{name}_max_dT_K"] = float(np.max(np.abs(s.T - T0)))
    out["pass"] = out["inert_unchanged"]
    return out


def ambient_rates() -> dict[str, Any]:
    """Each published reaction's rate and T_cut at 20 °C."""
    rows = []
    for name, bb in (("pmma", pmma_cone(25, fds_h_r=True)), ("pine", pine_cone(25, k_c=0.1, eps_char=0.75))):
        for i, r in enumerate(bb.reactions):
            k = r.a * math.exp(-r.e / (spec.R_GAS * T0)) if T0 >= r.t_cut else 0.0
            rows.append({"set": name, "reaction": i + 1, "t_cut_K": r.t_cut, "rate_at_20C_per_s": k})
    return {"rows": rows, "pass": all(r["rate_at_20C_per_s"] == 0.0 for r in rows)}


def half_order() -> dict[str, Any]:
    """One node, n = 0.5, held at 700 K: the exact update reaches exactly 0 at its depletion time and stays there."""
    comp = Component("x", 1000.0, (300.0,), (1000.0,), (300.0,), (0.2,), 0.9, spec.KAPPA_DEFAULT)
    r = Reaction(0, None, 0.0, 1e10, 1.5e5, 0.5, 0.0)
    s = Solid([comp], [r], [Layer(0.001, 1, 1000.0, (1.0,), False)], 700.0)
    k = r.a * math.exp(-r.e / (spec.R_GAS * 700.0))
    t_dep = 1.0 / ((1 - 0.5) * k)  # y^(1-n)/((1-n)k) with y = 1
    steps = math.ceil(t_dep / DT) + 4
    vals = []
    for _ in range(steps):
        s.T[:] = 700.0
        s._kinetics(DT)
        vals.append(float(s.m[0, 0]))
    first_zero = next((i for i, v in enumerate(vals) if v == 0.0), None)
    return {
        "depletion_time_s": t_dep,
        "first_exact_zero_step_end_s": None if first_zero is None else (first_zero + 1) * DT,
        "min_mass": min(vals),
        "pass": first_zero is not None and all(v == 0.0 for v in vals[first_zero:]) and min(vals) >= 0.0,
    }


def all_n7() -> dict[str, Any]:
    out = {
        "thick_thin_erfc": thick_and_thin(),
        "kappa_limit": kappa_limit(),
        "ambient_bits": ambient_bits(),
        "ambient_rates": ambient_rates(),
        "half_order": half_order(),
    }
    out["pass"] = all(v["pass"] for v in out.values())
    return out
