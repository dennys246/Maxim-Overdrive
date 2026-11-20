"""A Pennes three-layer skin (Torvi & Dale 1994 properties), optionally under one fabric layer and an air gap.

Vertex-centred finite volumes on a 1-D column, x = 0 at the skin surface, nodes exactly on the layer interfaces so
the pain receptor (0.1 mm, the epidermis-dermis interface) is a node. Backward Euler, with every non-linear
radiation term written as a conductance evaluated at the previous step (semi-implicit, unconditionally stable for
the linear part). Deterministic: no randomness, fixed operation order, numpy/scipy banded solve.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import constants as C
import numpy as np
from scipy.linalg import solve_banded

K0 = 273.15


@dataclass(frozen=True)
class Grid:
    x: np.ndarray  # node depths, m (x[0] = 0 surface, x[-1] = base)
    cap: np.ndarray  # J/m^2K per node
    perf: np.ndarray  # W/m^2K per node (perfusion coefficient G rho_b c_b times the node's depth)
    met: np.ndarray  # W/m^2 per node
    cond: np.ndarray  # W/m^2K between node i and i+1
    i_receptor: int


def make_grid(n_epi: int = 20, n_derm: int = 40, n_sub: int = 50) -> Grid:
    counts = (n_epi, n_derm, n_sub)
    xs = [0.0]
    seg_props = []
    for (_name, thick, k, rc, g, qm), n in zip(C.SKIN_LAYERS, counts, strict=True):
        dx = thick / n
        for _ in range(n):
            xs.append(xs[-1] + dx)
            seg_props.append((dx, k, rc, g, qm))
    x = np.array(xs)
    nn = len(x)
    cap, perf, met = np.zeros(nn), np.zeros(nn), np.zeros(nn)
    cond = np.zeros(nn - 1)
    for j, (dx, k, rc, g, qm) in enumerate(seg_props):
        for i in (j, j + 1):
            cap[i] += rc * dx / 2.0
            perf[i] += g * C.RHO_C_BLOOD * dx / 2.0
            met[i] += qm * dx / 2.0
        cond[j] = k / dx
    i_rec = int(np.argmin(np.abs(x - C.PAIN_DEPTH_M)))
    assert abs(x[i_rec] - C.PAIN_DEPTH_M) < 1e-12
    return Grid(x, cap, perf, met, cond, i_rec)


def rad_conductance(eps: float, t1_k: float, t2_k: float) -> float:
    """eps sigma (T1^4 - T2^4) = G (T1 - T2) with G = eps sigma (T1^2 + T2^2)(T1 + T2)."""
    return eps * C.SIGMA * (t1_k * t1_k + t2_k * t2_k) * (t1_k + t2_k)


@dataclass(frozen=True)
class Clothing:
    areal_mass: float  # kg/m^2
    gap: float  # m


class Column:
    """Unknowns: [T_fabric (if clothed), T_0 .. T_{N-1}]; T_N (base) held at core temperature or no-flux."""

    def __init__(
        self, grid: Grid, clothing: Clothing | None, base_fixed: bool = True, surface_override: float | None = None
    ) -> None:
        self.g = grid
        self.cl = clothing
        self.base_fixed = base_fixed
        self.surface_override = surface_override  # Jasinski validation: a fixed absorbed flux, no losses
        self.off = 1 if clothing else 0
        n_skin = len(grid.x) - (1 if base_fixed else 0)
        self.n = n_skin + self.off

    def _static(self):
        """Conduction, perfusion and metabolism: the parts of the system that never change."""
        g, off, n = self.g, self.off, self.n
        n_skin = n - off
        diag, upper, lower, rhs = np.zeros(n), np.zeros(n), np.zeros(n), np.zeros(n)
        diag[off:] += g.perf[:n_skin]
        rhs[off:] += g.perf[:n_skin] * (C.T_BLOOD_C + K0) + g.met[:n_skin]
        for i in range(n_skin):
            r = i + off
            if i + 1 < len(g.x):
                c = g.cond[i]
                diag[r] += c
                if i + 1 < n_skin:
                    upper[r] = -c
                    lower[r + 1] = -c
                    diag[r + 1] += c
                else:  # the neighbour is the fixed base node
                    rhs[r] += c * (C.T_CORE_C + K0)
        cap = np.concatenate(([self.cl.areal_mass * C.CLOTH_C] if self.cl else [], g.cap[:n_skin]))
        return diag, upper, lower, rhs, cap

    def _assemble(self, temps: np.ndarray, q_inc_w: float, dt: float | None):
        """Return (ab, rhs) for  (C/dt + K) T_new = C/dt T_old + b ; dt None gives the steady system."""
        if not hasattr(self, "_st"):
            self._st = self._static()
        d0, u0, l0, r0, cap = self._st
        off, n = self.off, self.n
        ta = C.T_AMB_C + K0
        diag, upper, lower, rhs = d0.copy(), u0.copy(), l0.copy(), r0.copy()
        ts = temps[off]
        if self.surface_override is not None:
            rhs[off] += self.surface_override
        elif self.cl is None:
            g_out = C.H_SKIN_AIR + rad_conductance(C.BODY_EPS, ts, ta)
            diag[off] += g_out
            rhs[off] += g_out * ta + C.BODY_EPS * q_inc_w
        else:
            tf = temps[0]
            eps_eff = 1.0 / (1.0 / C.CLOTH_EPS + 1.0 / C.BODY_EPS - 1.0)
            g_gap = C.K_AIR / self.cl.gap + rad_conductance(eps_eff, tf, ts)
            g_out = C.H_CLOTH_AIR + rad_conductance(C.CLOTH_EPS, tf, ta)
            diag[0] += g_gap + g_out
            rhs[0] += g_out * ta + C.CLOTH_ALPHA * q_inc_w
            upper[0] = -g_gap
            lower[1] = -g_gap
            diag[1] += g_gap
        if dt is not None:
            diag += cap / dt
            rhs += cap / dt * temps
        ab = np.zeros((3, n))
        ab[0, 1:] = upper[:-1]
        ab[1] = diag
        ab[2, :-1] = lower[1:]
        return ab, rhs

    def steady(self, q_inc_w: float, iters: int = 60) -> np.ndarray:
        temps = np.full(self.n, C.T_CORE_C + K0 - 3.0)
        for _ in range(iters):
            ab, rhs = self._assemble(temps, q_inc_w, None)
            temps = solve_banded((1, 1), ab, rhs)
        return temps

    def step(self, temps: np.ndarray, q_inc_w: float, dt: float) -> np.ndarray:
        ab, rhs = self._assemble(temps, q_inc_w, dt)
        return solve_banded((1, 1), ab, rhs)

    def receptor(self, temps: np.ndarray) -> float:
        return float(temps[self.g.i_receptor + self.off]) - K0


def henriques_rate(t_k: float) -> float:
    if t_k < C.HENRIQUES_T_ON_K:
        return 0.0
    return C.HENRIQUES_P * math.exp(-C.HENRIQUES_DE_R / t_k)


@dataclass(frozen=True)
class Exposure:
    t_pain: dict  # threshold name -> seconds or None
    t_burn1: float | None  # Henriques Ib = 0.53
    t_burn2: float | None  # Ib = 1
    steady_receptor_c: float
    initial_receptor_c: float
    initial_surface_c: float


def expose(grid: Grid, clothing: Clothing | None, q_inc_kw: float, t_max: float, dt: float = 0.01) -> Exposure:
    """Skin starts at its no-fire steady state; the flux steps on at t = 0 (the fire's peak) and stays."""
    col = Column(grid, clothing)
    temps = col.steady(0.0)
    t_rec0 = col.receptor(temps)
    t_surf0 = float(temps[col.off]) - K0
    q_w = q_inc_kw * 1000.0
    t_ss = col.receptor(col.steady(q_w))
    pending = {k: v for k, v in C.PAIN_T_C.items() if t_ss >= v}
    t_pain: dict = {k: None for k in C.PAIN_T_C}
    burn_possible = t_ss + K0 > C.HENRIQUES_T_ON_K
    t_b1 = t_b2 = None
    ib = 0.0
    t = 0.0
    prev = t_rec0
    n_steps = round(t_max / dt)
    for k in range(1, n_steps + 1):
        if not pending and (not burn_possible or t_b2 is not None):
            break
        temps = col.step(temps, q_w, dt)
        t = k * dt
        cur = col.receptor(temps)
        for name in list(pending):
            thr = pending[name]
            if cur >= thr:
                t_pain[name] = t - dt + dt * (thr - prev) / (cur - prev)
                del pending[name]
        ib += henriques_rate(cur + K0) * dt
        if t_b1 is None and ib >= 0.53:
            t_b1 = t
        if t_b2 is None and ib >= 1.0:
            t_b2 = t
        prev = cur
    return Exposure(t_pain, t_b1, t_b2, t_ss, t_rec0, t_surf0)


def jasinski_check(dt: float = 0.01) -> tuple[float | None, float | None]:
    """Reproduce Jasinski (2003) example 1: 6,500 W/m^2 absorbed for 18 s, quadratic initial profile 32.5 -> 37 degC,
    no-flux base. Published: first-degree 16.25 s, second-degree 17.8 s."""
    grid = make_grid()
    col = Column(grid, None, base_fixed=False, surface_override=6500.0)
    depth = grid.x[-1]
    temps = 37.0 + K0 - 4.5 * (1.0 - grid.x / depth) ** 2
    ib, t1, t2 = 0.0, None, None
    for k in range(1, round(18.0 / dt) + 1):
        temps = col.step(temps, 0.0, dt)
        ib += henriques_rate(col.receptor(temps) + K0) * dt
        if t1 is None and ib >= 0.53:
            t1 = k * dt
        if t2 is None and ib >= 1.0:
            t2 = k * dt
    return t1, t2
