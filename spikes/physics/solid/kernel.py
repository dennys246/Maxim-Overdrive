"""The 1D solid of fire_solid §4, as the pre-registration's §3 fixes it (spike; never imported by src/).

One part: layers of nodes in depth, front face at node 0. Per step of length dt, in this order:

1. **Kinetics at frozen T.** FDS's n-step Arrhenius (wall.f90 PYROLYSIS, `REACTION_RATE = A*RHO_S**N_S*EXP(-E/(R0*T))`),
   zero below T_cut (A·exp(-E/RT_cut) = 1e-9 1/s) by `np.where` over the whole array. Each reaction's reactant is
   updated exactly at frozen T: n = 1 by exp(-k dt); otherwise y_new = max(0, y^(1-n) - (1-n)k dt)^(1/(1-n)) on
   y = m/m_0 (fire_solid §4.2). Reactions are applied in list order and a solid product is added at once, so in a
   chain (pine) a product can react later in the same step: exact per reaction, first order in dt across a chain
   (disclosed). The heat sink is the mass consumed times H (J/kg of reactant, + endothermic).
2. **Properties at the old T, post-kinetics masses** (FDS's component averages, wall.f90 POINT_LOOP3 and
   func.f90 GET_EMISSIVITY): volume fractions X = (m/rho)/sum(m/rho); k and kappa volume-weighted; heat capacity
   sum(m c); front emissivity volume-weighted over node 0. A shrinking (non-charring) layer's node thickness scales
   with sum(m/rho) (fire_solid §4.3); a charring layer's stays fixed.
3. **In-depth radiation, the two-flux model** (FDS Technical Reference Guide, "Radiation Heat Transfer to
   Solids"; discretised as wall.f90 lines 2262-2290): per node TWO_DX_KAPPA = 2·kappa·dx, and the flux leaving a
   node is (R_in + 2κdx·σT⁴)/(1 + 2κdx), inwards then outwards over every node of every layer. Back face insulated
   (wall.f90 `CASE(INSULATED)`: EMISSIVITY_BACK = 0, so the inward flux reflects fully). Front closure
   q⁺(0) = q_in + (1 - ε)q⁻(0): FDS lags q⁻(0) one substep (`Q_RAD_OUT_OLD`); here it is solved exactly at the
   step's frozen T (the sweep is linear in q⁺(0)). Everything is written relative to the surroundings' blackbody
   σT_r⁴, which is an exact solution of the two-flux equations, so a slab at ambient gets exactly zero source.
   With in-depth radiation the front face's own radiative term is zero and only convection acts there (wall.f90
   line 2867 `ONE_D%INTERNAL_RADIATION` branch).
4. **Conduction, backward Euler in delta form,** one tridiagonal solve by a hand-written Thomas algorithm. Face
   conductance between nodes is the series resistance dx_i/2k_i + dx_j/2k_j (wall.f90's harmonic K_S with DX_WGT).
   The radiation source is linearised once: its nearest-neighbour Jacobian (black-node exchange between adjacent
   nodes, w_i = (1-τ_i)(1-τ_j) on Δ(σT⁴), plus node 0's escape through the front) is implicit, the rest explicit at
   the old T. The pair terms are antisymmetric, so energy is booked exactly. The surface-absorption mode (κ → ∞
   reference, N7) instead linearises εσT_F⁴ once at the front face.
5. **Regression** (fire_solid §4.3): a shrinking layer's surface node below 1% of its initial thickness, or holding
   no reactive mass, moves its mass and enthalpy into the next node of its layer (disclosed: at NIST-StMU's 1% inert
   fraction a fully depleted node sits exactly at 1%, so the strict test alone would be decided by rounding).

The ledger (N6) books, per step in J/m², absorbed radiation, re-radiation out, convection in, the reaction sink and
the stored change; mass (N5) is node masses plus gas removed. No clock, no randomness, no BLAS.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import numpy.typing as npt
import spec

Array = npt.NDArray[np.float64]


@dataclass(frozen=True)
class Component:
    """One condensed-phase material: true density, c(T) and k(T) tables (K; constant outside), ε, κ."""

    name: str
    rho: float
    c_t: tuple[float, ...]
    c_v: tuple[float, ...]
    k_t: tuple[float, ...]
    k_v: tuple[float, ...]
    eps: float
    kappa: float


@dataclass(frozen=True)
class Reaction:
    """reactant -> nu·product (solid) + (1 - nu)·gas; rate A·exp(-E/RT) on (m/m0)^n; H in J/kg of reactant."""

    reactant: int
    product: int | None
    nu: float
    a: float
    e: float
    n: float
    h: float
    h_slope: float = 0.0  # J/kgK: dH/dT (FDS ADJUST_H, read.f90 7790-7820), 0 = constant H
    t_ref: float = 0.0  # K: where H holds
    t_on: float = 0.0  # K: rerun 1 §1 C's TGA onset (materials.onset_temperature); 0 = the registered cutoff alone

    @property
    def t_cut_k(self) -> float:
        """Where A·exp(-E/RT) = K_CUT; inf if A itself is at or below K_CUT (never active then)."""
        if self.a <= spec.K_CUT:
            return math.inf
        return self.e / (spec.R_GAS * math.log(self.a / spec.K_CUT))

    @property
    def t_cut(self) -> float:
        """The rate is exactly 0 below this: max(T at K_CUT, t_on) (rerun 1 §1 C; t_on = 0 gives the first run's)."""
        return max(self.t_cut_k, self.t_on)


@dataclass(frozen=True)
class Layer:
    """A layer: thickness (m), node count, initial bulk density (kg/m³), mass fraction per component, shrinks?"""

    thickness: float
    n_nodes: int
    rho_bulk: float
    fractions: tuple[float, ...]
    shrinks: bool


@dataclass
class Ledger:
    """Per-step energy lines (J/m²) and the running checks."""

    absorbed: float = 0.0
    out_rad: float = 0.0
    conv_in: float = 0.0
    reaction: float = 0.0
    stored: float = 0.0
    cum_absorbed: float = 0.0
    worst_energy: float = 0.0  # max |residual| / cumulative absorbed over steps
    worst_mass: float = 0.0  # max |mass error| / initial over steps
    lines_needed: dict[str, float] = field(default_factory=dict)  # per line: max |residual without it| / cum

    def check(self) -> float:
        return self.absorbed - self.out_rad + self.conv_in - self.reaction - self.stored


def _interp_all(t: Array, tabs_t: list[Array], tabs_v: list[Array]) -> Array:
    """Each component's table at every node's T: shape (n_comp, n)."""
    return np.vstack([np.interp(t, tt, vv) for tt, vv in zip(tabs_t, tabs_v, strict=True)])


def thomas(lo: list[float], di: list[float], up: list[float], rhs: list[float]) -> list[float]:
    """Solve the tridiagonal system lo[i]x[i-1] + di[i]x[i] + up[i]x[i+1] = rhs[i] (lo[0], up[-1] unused)."""
    n = len(di)
    cp = [0.0] * n
    dp = [0.0] * n
    beta = di[0]
    cp[0] = up[0] / beta
    dp[0] = rhs[0] / beta
    for i in range(1, n):
        li = lo[i]
        beta = di[i] - li * cp[i - 1]
        cp[i] = up[i] / beta
        dp[i] = (rhs[i] - li * dp[i - 1]) / beta
    x = [0.0] * n
    x[n - 1] = dp[n - 1]
    for i in range(n - 2, -1, -1):
        x[i] = dp[i] - cp[i] * x[i + 1]
    return x


def sweep(r0: float, e: list[float], tau: list[float]) -> tuple[list[float], float]:
    """Two-flux sweep (wall.f90 2277-2290) in primed form: inwards from q⁺(0)' = r0, full reflection at the insulated
    back, outwards. Returns each node's net absorbed flux (W/m²) and q⁻(0)'."""
    n = len(e)
    net = [0.0] * n
    r = r0
    for i in range(n):
        ti = tau[i]
        rn = ti * r + (1.0 - ti) * e[i]
        net[i] = r - rn
        r = rn
    b = r
    for i in range(n - 1, -1, -1):
        ti = tau[i]
        bn = ti * b + (1.0 - ti) * e[i]
        net[i] += b - bn
        b = bn
    return net, b


class Solid:
    """One part's nodes and their state. Build once per run; `step` advances it by dt."""

    def __init__(
        self,
        comps: list[Component],
        reactions: list[Reaction],
        layers: list[Layer],
        t0: float,
        *,
        surface_absorption: bool = False,
        emission: bool = True,
    ) -> None:
        self.comps = comps
        self.reactions = reactions
        self.surface_absorption = surface_absorption
        self.emission = emission  # False only for N7's losses-off closed forms (surface mode)
        nc = len(comps)
        cols: list[Array] = []
        dx0: list[float] = []
        lay: list[int] = []
        for li, L in enumerate(layers):
            if len(L.fractions) != nc:
                raise ValueError("a layer needs one mass fraction per component")
            d = L.thickness / L.n_nodes
            for _ in range(L.n_nodes):
                cols.append(np.array([f * L.rho_bulk * d for f in L.fractions]))
                dx0.append(d)
                lay.append(li)
        self.m: Array = np.array(cols).T.copy()  # (nc, n) kg/m²
        self.m0: Array = self.m.copy()  # per-node initial masses (for n != 1 kinetics)
        self.ref: Array = np.array(dx0)  # each node's reference (initial) thickness
        self.layer: npt.NDArray[np.int64] = np.array(lay, dtype=np.int64)
        self.shrinks = np.array([layers[i].shrinks for i in lay], dtype=bool)
        self.rho = np.array([c.rho for c in comps])
        self.vol0: Array = (self.m / self.rho[:, None]).sum(axis=0)
        self.eps_c = np.array([c.eps for c in comps])
        self.kap_c = np.array([c.kappa for c in comps])
        self.ct = [np.array(c.c_t) for c in comps]
        self.cv = [np.array(c.c_v) for c in comps]
        self.kt = [np.array(c.k_t) for c in comps]
        self.kv = [np.array(c.k_v) for c in comps]
        self.reactive = np.zeros(nc, dtype=bool)
        for r in reactions:
            self.reactive[r.reactant] = True
        self.t_cut = [r.t_cut for r in reactions]
        self.T: Array = np.full(self.m.shape[1], float(t0))
        self.t_face = float(t0)
        self.removed = 0.0  # kg/m² of gas released
        self.initial_mass = float(self.m.sum())
        self.merges = 0
        self.ledger = Ledger()

    # ----- geometry and properties -----
    def thickness(self) -> Array:
        """Node thicknesses (m): shrinking layers scale with sum(m/rho); charring and inert layers keep theirs."""
        vol = (self.m / self.rho[:, None]).sum(axis=0)
        return np.where(self.shrinks, self.ref * (vol / self.vol0), self.ref)

    def _props(self) -> tuple[Array, Array, Array, Array, float]:
        vol = self.m / self.rho[:, None]
        volsum = vol.sum(axis=0)
        x = vol / volsum
        dx = np.where(self.shrinks, self.ref * (volsum / self.vol0), self.ref)
        kk = (x * _interp_all(self.T, self.kt, self.kv)).sum(axis=0)
        cap = (self.m * _interp_all(self.T, self.ct, self.cv)).sum(axis=0)
        kap = (x * self.kap_c[:, None]).sum(axis=0)
        eps0 = float((x[:, 0] * self.eps_c).sum())
        return dx, kk, cap, kap, eps0

    # ----- 1. kinetics -----
    def _kinetics(self, dt: float) -> tuple[Array, Array]:
        n = self.m.shape[1]
        gas = np.zeros(n)
        heat = np.zeros(n)
        temp = self.T
        for r, tc in zip(self.reactions, self.t_cut, strict=True):
            k = np.where(temp >= tc, r.a * np.exp(-r.e / (spec.R_GAS * temp)), 0.0)
            mr = self.m[r.reactant]
            if r.n == 1.0:
                dm = mr * -np.expm1(-k * dt)
            else:
                m0 = self.m0[r.reactant]
                y = np.divide(mr, m0, out=np.zeros(n), where=m0 > 0)
                p = 1.0 - r.n
                inner = np.maximum(0.0, y**p - p * k * dt)
                ynew = np.where(k > 0, inner ** (1.0 / p), y)
                dm = np.where(k > 0, mr - ynew * m0, 0.0)
            self.m[r.reactant] = mr - dm
            if r.product is not None:
                self.m[r.product] = self.m[r.product] + r.nu * dm
                gas += (1.0 - r.nu) * dm
            else:
                gas += dm
            heat += dm * (r.h + r.h_slope * (temp - r.t_ref)) if r.h_slope != 0.0 else dm * r.h
        return gas, heat

    # ----- 3. radiation -----
    def _two_flux(self, dx: Array, kap: Array, eps0: float, q_in: float, t_r: float) -> tuple[list[float], float, list[float]]:
        """Net absorbed radiation per node (W/m², primed form), q⁻(0)' and each node's τ."""
        tau = (1.0 / (1.0 + 2.0 * kap * dx)).tolist()
        e = (spec.SIGMA * (self.T**4 - t_r**4)).tolist()
        q_prime = eps0 * q_in  # ε·(incident - σT_r⁴); incident's ambient part is σT_r⁴
        net_a, b_a = sweep(0.0, e, tau)
        b = 1.0
        for ti in tau:
            b *= ti * ti
        r0 = (q_prime + (1.0 - eps0) * b_a) / (1.0 - (1.0 - eps0) * b)
        if r0 == 0.0:
            return net_a, b_a, tau
        net, b0 = sweep(r0, e, tau)
        return net, b0, tau

    # ----- the step -----
    def step(self, dt: float, q_ext: float, h: float, t_gas: float, t_r: float) -> float:
        """Advance by dt under incident flux q_ext (W/m², beyond the surroundings' σT_r⁴), convection h to gas at
        t_gas. Returns the gas released this step (kg/m²)."""
        gas, heat = self._kinetics(dt)
        self.removed += float(gas.sum())
        dx, kk, cap, kap, eps0 = self._props()
        n = dx.size
        temp = self.T
        g_face = 1.0 / (dx[:-1] / (2.0 * kk[:-1]) + dx[1:] / (2.0 * kk[1:]))  # W/m²K between i and i+1
        kf = 2.0 * kk[0] / dx[0]
        diag = cap / dt
        lo = np.zeros(n)
        up = np.zeros(n)
        rhs = -heat / dt
        rhs[:-1] += g_face * (temp[1:] - temp[:-1])
        rhs[1:] += g_face * (temp[:-1] - temp[1:])
        diag[:-1] += g_face
        diag[1:] += g_face
        lo[1:] -= g_face
        up[:-1] -= g_face
        abs_in = q_ext + spec.SIGMA * t_r**4
        if self.surface_absorption:
            fo = self.t_face
            em = 1.0 if self.emission else 0.0
            lin = 4.0 * eps0 * spec.SIGMA * fo**3 * em
            den = kf + lin + h
            d_old = (eps0 * q_ext - em * eps0 * spec.SIGMA * (fo**4 - t_r**4) - lin * (temp[0] - fo) + h * (t_gas - temp[0])) / den
            bcoef = kf * (lin + h) / den
            rhs[0] += kf * d_old
            diag[0] += bcoef
            esc = 0.0
        else:
            net, b0, tau = self._two_flux(dx, kap, eps0, q_ext, t_r)
            gdr = 4.0 * spec.SIGMA * temp**3
            ta = np.array(tau)
            w = (1.0 - ta[:-1]) * (1.0 - ta[1:])
            diag[:-1] += w * gdr[:-1]
            diag[1:] += w * gdr[1:]
            lo[1:] -= w * gdr[:-1]
            up[:-1] -= w * gdr[1:]
            esc = eps0 * (1.0 - tau[0]) * float(gdr[0])
            diag[0] += esc
            rhs += np.array(net)
            h_eff = h * kf / (kf + h) if h > 0 else 0.0
            diag[0] += h_eff
            rhs[0] += h_eff * (t_gas - temp[0])
        dtemp = np.array(thomas(lo.tolist(), diag.tolist(), up.tolist(), rhs.tolist()))
        new_t = temp + dtemp
        # ledger (J/m²)
        L = self.ledger
        L.absorbed = eps0 * abs_in * dt
        L.reaction = float(heat.sum())
        L.stored = float((cap * dtemp).sum())
        if self.surface_absorption:
            d_new = d_old - dtemp[0] * (lin + h) / den
            tf_new = float(new_t[0] + d_new)
            L.out_rad = (em * eps0 * spec.SIGMA * fo**4 + lin * (tf_new - fo) + (1.0 - em) * eps0 * spec.SIGMA * t_r**4) * dt
            L.conv_in = h * (t_gas - tf_new) * dt
            self.t_face = tf_new
        else:
            L.out_rad = (eps0 * (b0 + spec.SIGMA * t_r**4) + esc * float(dtemp[0])) * dt
            L.conv_in = h_eff * (t_gas - float(new_t[0])) * dt
            self.t_face = float((kf * new_t[0] + h * t_gas) / (kf + h)) if h > 0 else float(new_t[0])
        self.T = new_t
        self._check(L)
        self._regress()
        return float(gas.sum())

    def _check(self, L: Ledger) -> None:
        L.cum_absorbed += L.absorbed
        scale = L.cum_absorbed if L.cum_absorbed > 0 else 1.0
        res = L.check()
        L.worst_energy = max(L.worst_energy, abs(res) / scale)
        for name in ("absorbed", "out_rad", "conv_in", "reaction"):
            without = res - (getattr(L, name) * (-1.0 if name in ("out_rad", "reaction") else 1.0))
            L.lines_needed[name] = max(L.lines_needed.get(name, 0.0), abs(without) / scale)
        merr = abs(float(self.m.sum()) + self.removed - self.initial_mass) / self.initial_mass
        L.worst_mass = max(L.worst_mass, merr)

    # ----- 5. regression -----
    def _regress(self) -> None:
        while self.shrinks[0] and self.m.shape[1] > 1 and self.layer[1] == self.layer[0]:
            vol = float((self.m[:, 0] / self.rho).sum())
            frac = vol / float(self.vol0[0])
            depleted = float(self.m0[self.reactive, 0].sum()) > 0.0 and float(self.m[self.reactive, 0].sum()) == 0.0
            if frac >= spec.REGRESS_FRACTION and not depleted:
                return
            c0 = float((self.m[:, 0] * np.array([np.interp(self.T[0], t, v) for t, v in zip(self.ct, self.cv, strict=True)])).sum())
            c1 = float((self.m[:, 1] * np.array([np.interp(self.T[1], t, v) for t, v in zip(self.ct, self.cv, strict=True)])).sum())
            self.T[1] = (c0 * self.T[0] + c1 * self.T[1]) / (c0 + c1)
            self.m[:, 1] += self.m[:, 0]
            self.m0[:, 1] += self.m0[:, 0]
            self.ref[1] += self.ref[0]
            self.vol0[1] += self.vol0[0]
            keep = slice(1, None)
            self.m = self.m[:, keep].copy()
            self.m0 = self.m0[:, keep].copy()
            self.ref = self.ref[keep].copy()
            self.vol0 = self.vol0[keep].copy()
            self.layer = self.layer[keep].copy()
            self.shrinks = self.shrinks[keep].copy()
            self.T = self.T[keep].copy()
            self.merges += 1

    # ----- outputs -----
    def layer_mass(self, layer: int) -> float:
        """kg/m² still in a layer."""
        return float(self.m[:, self.layer == layer].sum())

    def reactive_mass(self) -> float:
        return float(self.m[self.reactive].sum())

    def last_node_t(self, layer: int) -> float:
        """T of the deepest node of a layer: FDS's INSIDE WALL TEMPERATURE at a layer's back face picks the cell whose
        back boundary is at that depth (dump.f90 lines 8938-8943, `IF (DEPTH<=ONE_D%X(II2)) I_DEPTH = II2`)."""
        idx = np.flatnonzero(self.layer == layer)
        return float(self.T[idx[-1]])
