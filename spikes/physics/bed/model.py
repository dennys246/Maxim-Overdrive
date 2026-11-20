"""Porous-bed crate fire: a throwaway 3-D cell model (spike, never imported by src/).

Grid: the 0.6 m crate at dx = 0.2 / 0.1 / 0.05 m, n^3 cells, indices [i(x), j(y), k(z up)].
Envelope = the five faces adjacent to air (x-, x+, y-, y+, z+); the bottom sits on the floor and is
adiabatic for radiation and conduction (a stated assumption).

Each cell holds fuel surface in four parts (areas in m^2, per-area state):
  Ui  unburnt interior slats: 1-D half-slat conduction profile (node 0 = the 1 mm skin), sees the
      in-bed radiation field G and the draught gas.
  Up  unburnt outward-facing slat faces under the pilot's disc (area phi * disc overlap): 1-D
      profile, front face takes the pilot flux and loses 6a to 20 C surroundings.
  Iw  ignited, wood remaining: surface at T_p while pyrolysing with m'' = q''_net / L_g (tile spec
      6c); quasi-steady surface below T_p when q''_net < 0; flaming while m'' >= m''_crit.
  Ic  char only: lumped char temperature, oxidised by O2 (kinetics in series with mass transfer).
In-bed radiation: P1 with extinction beta = a_v/4, absorption eps*a_v/4, Marshak boundary at the
envelope. Flame feedback q''_f per m^2 of flaming surface is a volumetric P1 source in the cell.
Draught: per (i,j) column, a buoyancy-driven Ergun flow upward; gas exchanges heat with surfaces
(exponential per cell), carries O2 (consumed by char and flames, Huggett) and CO.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from constants import SIGMA_SB, Params

G_GRAV = 9.81
R_AIR = 287.05
P_ATM = 101325.0
DH_CO2 = 393.51e3 / 12.011e-3  # J/kg C (393.51 kJ/mol over 12.011 g/mol)
DH_CO = 110.53e3 / 12.011e-3  # J/kg C
DH_CO_GAS = (393.51e3 - 110.53e3) / 28.010e-3  # J/kg CO
LEDGER_IN = ("sources", "combustion_flaming", "combustion_char")
LEDGER_OUT = (
    "plume_convective",
    "flame_radiative",
    "open_air_rad",
    "open_air_conv",
    "open_air_pilotface",
    "open_air_draught",
    "removed_with_mass",
    "bodies",
)
LEDGER_STORE = ("d_cells", "d_skins")


def mu_air(t: np.ndarray) -> np.ndarray:
    return 1.716e-5 * (t / 273.0) ** 1.5 * (273.0 + 111.0) / (t + 111.0)


def k_air(t: np.ndarray) -> np.ndarray:
    return 0.0241 * (t / 273.0) ** 1.5 * (273.0 + 194.0) / (t + 194.0)


def rho_air(t: np.ndarray) -> np.ndarray:
    return P_ATM / (R_AIR * t)


def f_co(p: Params, t: np.ndarray) -> np.ndarray:
    """Molar-to-mass split of surface carbon to CO (fraction of carbon atoms going to CO)."""
    if p.product == "co2":
        return np.zeros_like(t)
    r = 2500.0 * np.exp(-6240.0 / np.maximum(t, 300.0))  # CO/CO2 molar (Arthur 1951)
    return r / (1.0 + r)


@dataclass
class Bed:
    p: Params
    dx: float
    pilot_ticks: int
    n: int = 0
    t: float = 0.0
    step_no: int = 0
    ledger: dict[str, float] = field(default_factory=dict)

    # ---------------------------------------------------------------- setup
    def __post_init__(self) -> None:
        p = self.p
        self.n = round(p.box_m / self.dx)
        n = self.n
        s = (n, n, n)
        self.V = self.dx**3
        self.Af = self.dx**2
        self.T0 = p.t_amb
        self._init_slab()
        a_cell = p.sigma_v * self.V
        self._init_envelope(s, a_cell)
        self._init_parts(s, a_cell)
        self.ledger = {k: 0.0 for k in LEDGER_IN + LEDGER_OUT}
        self.m0 = self.fuel_mass()
        self.wood0 = self.wood_mass()
        self.cell_fuel0 = self._cell_fuel()
        self.E0_cells, self.E0_skins = self.energies()
        self._lu_key = b""
        self._lu = None
        self._build_geometry()
        self._build_face_sampling()
        if self.p.ignite_base_m > 0:
            self._ignite_base(self.p.ignite_base_m)
        self.E0_cells, self.E0_skins = self.energies()

    def _init_slab(self) -> None:
        """Slab nodes over the half slat."""
        p = self.p
        half = p.slat_b_m / 2.0
        rest = (half - p.skin_m) / (p.n_slab - 1)
        self.dxs = np.array([p.skin_m] + [rest] * (p.n_slab - 1))
        self.cap_n = p.rho_wood * p.c_wood * self.dxs  # J/m^2 K per node
        mid = 0.5 * (self.dxs[:-1] + self.dxs[1:])
        self.K = p.k_wood / mid

    def _init_envelope(self, s: tuple[int, int, int], a_cell: float) -> None:
        """Envelope faces per cell, and the outward share of each part's area."""
        self.n_env = np.zeros(s)
        self.n_env[0, :, :] += 1
        self.n_env[-1, :, :] += 1
        self.n_env[:, 0, :] += 1
        self.n_env[:, -1, :] += 1
        self.n_env[:, :, -1] += 1
        self.f_env = self.p.phi * self.n_env * self.Af / a_cell

    def _init_parts(self, s: tuple[int, int, int], a_cell: float) -> None:
        """The four fuel-surface parts at ambient, the pilot's overlap, and the radiation and draught fields."""
        p = self.p
        n = self.n
        # pilot overlap on x- face patches (j,k)
        self.overlap = self._disc_overlap()
        self.A_up = np.zeros(s)
        self.A_up[0] = p.phi * self.overlap
        self.A_up0 = self.A_up.copy()
        self.A_ui = a_cell - self.A_up
        self.A_ui0 = self.A_ui.copy()
        self.Tu = np.full((*s, p.n_slab), self.T0)
        self.Tup = np.full((*s, p.n_slab), self.T0)
        self.A_iw = np.zeros(s)
        self.w_iw = np.zeros(s)
        self.c_iw = np.zeros(s)
        self.e_iw = np.zeros(s)
        self.Ts_iw = np.full(s, self.T0)
        self.A_ic = np.zeros(s)
        self.c_ic = np.zeros(s)
        self.T_ic = np.full(s, self.T0)
        self.mvol = np.zeros(s)
        self.flaming = np.zeros(s, dtype=bool)
        self.Tg = np.full(s, self.T0)
        self.Gcol = np.zeros((n, n))
        self.G = np.full(s, 4 * SIGMA_SB * self.T0**4)
        self.lastG = self.G.copy()
        self.q_out_face = {}  # for brightness

    def _ignite_base(self, depth: float) -> None:
        """Conditional scenario: fuel surface in z < depth (by volume overlap) starts flaming."""
        n = self.n
        z0 = np.arange(n) * self.dx
        ov = np.clip((depth - z0) / self.dx, 0.0, 1.0)  # fraction of each layer below depth
        da = self.A_ui * ov[None, None, :]
        skin_tp = self.cap_n[0] * (self.p.t_p - self.T0)
        e_add = (self.Tu - self.T0) @ self.cap_n - skin_tp
        self._merge_iw(da, self.p.w0, 0.0, e_add)
        self.A_ui = self.A_ui - da
        self.flaming = self.A_iw > 0  # the ledger's baseline E0 is taken after this state is set

    def _disc_overlap(self) -> np.ndarray:
        p = self.p
        n = self.n
        res = 600  # 1 mm sampling of the 0.6 m face, fixed in metres
        c = (np.arange(res) + 0.5) * (p.box_m / res)
        yy, zz = np.meshgrid(c, c, indexing="ij")
        inside = (yy - p.pilot_centre_yz_m[0]) ** 2 + (zz - p.pilot_centre_yz_m[1]) ** 2 <= p.pilot_r_m**2
        m = res // n
        cnt = inside.reshape(n, m, n, m).sum(axis=(1, 3)).astype(float)
        return cnt / cnt.sum() * math.pi * p.pilot_r_m**2

    def _build_geometry(self) -> None:
        n = self.n
        idx = np.arange(n**3).reshape(n, n, n)
        self.idx = idx
        pairs = []
        for ax in range(3):
            a = [slice(None)] * 3
            b = [slice(None)] * 3
            a[ax] = slice(0, n - 1)
            b[ax] = slice(1, n)
            pairs.append((idx[tuple(a)].ravel(), idx[tuple(b)].ravel()))
        self.pairs_p = np.concatenate([q[0] for q in pairs])
        self.pairs_q = np.concatenate([q[1] for q in pairs])
        # boundary faces: (cell index array, face name)
        self.bfaces = {
            "x-": idx[0, :, :],
            "x+": idx[-1, :, :],
            "y-": idx[:, 0, :],
            "y+": idx[:, -1, :],
            "z+": idx[:, :, -1],
        }

    def _build_face_sampling(self) -> None:
        """Bilinear interpolation from face-patch centres to a 1 cm sample grid (metric)."""
        p = self.p
        n = self.n
        m = round(p.box_m / p.face_sample_m)
        xs = (np.arange(m) + 0.5) * p.face_sample_m
        cpos = (np.arange(n) + 0.5) * self.dx
        f = np.clip((xs - cpos[0]) / self.dx, 0, n - 1 - 1e-12)
        i0 = np.floor(f).astype(int)
        w1 = f - i0
        i1 = np.minimum(i0 + 1, n - 1)
        W = np.zeros((m, n))
        W[np.arange(m), i0] += 1 - w1
        W[np.arange(m), i1] += w1
        self.W1 = W  # 1-D interp matrix
        self.sample_da = p.face_sample_m**2
        # depth quadrature along inward normal (1 mm, to the far side)
        self.sq = (np.arange(round(p.box_m / 0.002)) + 0.5) * 0.002
        L = np.zeros((self.sq.size, n))
        fz = (self.sq - cpos[0]) / self.dx
        for q, fv in enumerate(fz):
            if fv <= 0:  # extrapolate from the first two centres
                if n > 1:
                    L[q, 0] = 1 - fv
                    L[q, 1] = fv
                else:
                    L[q, 0] = 1
            elif fv >= n - 1:
                L[q, n - 1] = 1
            else:
                j = int(fv)
                L[q, j] = 1 - (fv - j)
                L[q, j + 1] = fv - j
        self.Lprof = L
        self.cell_of_s = np.minimum((self.sq / self.dx).astype(int), n - 1)

    # ------------------------------------------------------------- measures
    def _cell_fuel(self) -> np.ndarray:
        w0 = self.p.w0
        return (self.A_ui + self.A_up) * w0 + self.A_iw * (self.w_iw + self.c_iw) + self.A_ic * self.c_ic

    def fuel_mass(self) -> float:
        return float(self._cell_fuel().sum())

    def _cell_wood(self) -> np.ndarray:
        return (self.A_ui + self.A_up) * self.p.w0 + self.A_iw * self.w_iw

    def wood_mass(self) -> float:
        return float(self._cell_wood().sum())

    def energies(self) -> tuple[float, float]:
        dT_u = self.Tu - self.T0
        dT_p = self.Tup - self.T0
        skins = float(
            (self.A_ui * self.cap_n[0] * dT_u[..., 0]).sum()
            + (self.A_up * self.cap_n[0] * dT_p[..., 0]).sum()
            + (self.A_iw * self.cap_n[0] * (self.Ts_iw - self.T0)).sum()
        )
        cells = float(
            (self.A_ui * (dT_u[..., 1:] @ self.cap_n[1:])).sum()
            + (self.A_up * (dT_p[..., 1:] @ self.cap_n[1:])).sum()
            + (self.A_iw * self.e_iw).sum()
            + (self.A_ic * self._cic() * (self.T_ic - self.T0)).sum()
        )
        return cells, skins

    def _cic(self) -> np.ndarray:
        return np.maximum(self.c_ic, self.p.char_floor) * self.p.c_char

    def _a_tot(self) -> np.ndarray:
        return self.A_ui + self.A_iw + self.A_ic

    def surf_T(self) -> np.ndarray:
        """Area-weighted surface temperature of the interior parts of each cell (T_amb if empty)."""
        a = self._a_tot()
        num = self.A_ui * self.Tu[..., 0] + self.A_iw * self.Ts_iw + self.A_ic * self.T_ic
        return np.where(a > 0, num / np.maximum(a, 1e-30), self.T0)

    # ------------------------------------------------------------------ P1
    def _p1_matrix(self, av: np.ndarray):
        key = av.tobytes()
        if key == self._lu_key and self._lu is not None:
            return self._lu
        p = self.p
        n3 = self.n**3
        beta = np.maximum(av / 4.0, 0.05).ravel()
        kap = (p.eps * av / 4.0).ravel()
        gam = 1.0 / (3.0 * beta)
        cpq = self.Af / (self.dx / (2 * gam[self.pairs_p]) + self.dx / (2 * gam[self.pairs_q]))
        diag = kap * self.V
        diag = diag + np.bincount(self.pairs_p, cpq, n3) + np.bincount(self.pairs_q, cpq, n3)
        self.cb = {}
        for name, cells in self.bfaces.items():
            c = self.Af / (self.dx / (2 * gam[cells.ravel()]) + 2.0)
            self.cb[name] = c.reshape(cells.shape)
            diag = diag + np.bincount(cells.ravel(), c, n3)
        rows = np.concatenate([np.arange(n3), self.pairs_p, self.pairs_q])
        cols = np.concatenate([np.arange(n3), self.pairs_q, self.pairs_p])
        vals = np.concatenate([diag, -cpq, -cpq])
        M = sp.csc_matrix((vals, (rows, cols)), shape=(n3, n3))
        self._lu = spla.splu(M)
        self._lu_key = key
        self._kap = kap
        return self._lu

    def _solve_p1(self, eb: np.ndarray, src: np.ndarray, ein: dict[str, np.ndarray]) -> float:
        """Solve for G; return the net radiative power leaving through the envelope (W)."""
        av = self._a_tot() / self.V
        lu = self._p1_matrix(av)
        n3 = self.n**3
        rhs = self._kap * self.V * 4.0 * eb.ravel() + src.ravel() * self.V
        for name, cells in self.bfaces.items():
            rhs = rhs + np.bincount(cells.ravel(), (self.cb[name] * 4.0 * ein[name]).ravel(), n3)
        G = lu.solve(rhs)
        self.G = G.reshape(self.n, self.n, self.n)
        out = 0.0
        self.q_out_face = {}
        for name, cells in self.bfaces.items():
            q = self.cb[name] * (G[cells] - 4.0 * ein[name])
            self.q_out_face[name] = q / self.Af
            out += float(q.sum())
        return out

    # ------------------------------------------------------------- draught
    def _draught(self, temps: dict[str, np.ndarray], qdot: np.ndarray, fb: np.ndarray):
        """March each column upward. Returns per-part gas loss (W/m^2), O2-limited char carbon
        rates (kg/m^2 s) per part, and energy rates for the ledger."""
        p = self.p
        n = self.n
        s = (n, n, n)
        q_gas = {k: np.zeros(s) for k in ("ui", "iw", "ic")}
        r_c = {k: np.zeros(s) for k in ("iw", "ic")}
        q_ox = {k: np.zeros(s) for k in ("iw", "ic")}
        tg = np.zeros(s)
        t_in = np.full((n, n), self.T0)
        y = np.full((n, n), p.y_o2)
        yco = np.zeros((n, n))
        mdot = self.Gcol * self.Af
        q_fl_tot = 0.0
        q_co_tot = 0.0
        q_solid_tot = 0.0
        plume_avail = (1 - p.chi_r) * (qdot - fb)
        self._void_now = self._void()
        for k in range(n):
            fl = self.flaming[:, :, k]
            # --- flaming cells: gas heated to T_p from the plume; O2 by Huggett
            t_fl = np.maximum(t_in, p.t_p)
            need = mdot * p.cp_air * (t_fl - t_in)
            qfl = np.where(fl, np.minimum(need, plume_avail[:, :, k]), 0.0)
            q_fl_tot += float(qfl.sum())
            o2_fl = np.where(fl, np.minimum(y * mdot, qdot[:, :, k] / p.huggett), 0.0)
            # --- non-flaming: char oxidation, O2-limited
            nf = ~fl
            areas = {"iw": self.A_iw[:, :, k] * (self.c_iw[:, :, k] > 0), "ic": self.A_ic[:, :, k]}
            a_s, t_s = self._layer_surface(temps, k, t_in)
            h = self._h_slat(mdot, t_in, t_s, k)
            co_prod, o2_char = self._char_oxidation(
                temps, k, h=h, y=y, mdot=mdot, nf=nf, areas=areas, r_c=r_c, q_ox=q_ox
            )
            y_new = y - np.where(mdot > 0, (o2_fl + o2_char) / np.maximum(mdot, 1e-300), 0.0)
            y_new = np.maximum(y_new, 0.0)
            co_av = yco * mdot + co_prod
            qco, y_new, co_av = self._burn_co(nf, co_av, y_new, mdot)
            q_co_tot += float(qco.sum())
            yco = np.where(mdot > 0, co_av / np.maximum(mdot, 1e-300), 0.0)
            t_in2 = t_in + np.where(mdot > 0, (qco + qfl) / np.maximum(mdot * p.cp_air, 1e-300), 0.0)
            # --- exchange in non-flaming cells (exponential in each cell)
            cap = mdot * p.cp_air
            ntu = np.where(cap > 0, h * a_s / np.maximum(cap, 1e-300), np.inf)
            t_out = np.where(nf & (a_s > 0), t_s + (t_in2 - t_s) * np.exp(-ntu), t_in2)
            qsol = np.where(nf & (a_s > 0) & (cap > 0), cap * (t_out - t_in2), 0.0)
            q_solid_tot += float(qsol.sum())
            tgm = np.where(a_s > 0, t_s - qsol / np.maximum(h * a_s, 1e-300), t_in2)
            for key, tt in (("ui", temps["ui"]), ("iw", temps["iw"]), ("ic", temps["ic"])):
                q_gas[key][:, :, k] = np.where(nf & (cap > 0), h * (tt[:, :, k] - tgm), 0.0)
            # buoyancy temperature: flame zone at T_p; stagnant gas takes the surface temperature
            tg[:, :, k] = np.where(fl, t_fl, np.where(cap > 0, 0.5 * (t_in2 + t_out), t_s))
            t_in = np.where(fl, np.where(mdot > 0, t_in + qfl / np.maximum(mdot * p.cp_air, 1e-300), t_in), t_out)
            y = y_new
        self.Tg = tg
        exit_h = float((mdot * p.cp_air * (t_in - self.T0)).sum())
        self._exit_check = exit_h - (q_fl_tot + q_co_tot + q_solid_tot)
        self.Gcol = self._ergun(tg)
        return q_gas, r_c, q_ox, q_fl_tot, q_co_tot, q_solid_tot

    def _layer_surface(self, temps, k, t_in):
        """Layer k's interior surface area per cell and its area-weighted temperature (t_in where empty)."""
        a_ui = self.A_ui[:, :, k]
        a_s = a_ui + self.A_iw[:, :, k] + self.A_ic[:, :, k]
        t_s = np.where(
            a_s > 0,
            (
                a_ui * temps["ui"][:, :, k]
                + self.A_iw[:, :, k] * temps["iw"][:, :, k]
                + self.A_ic[:, :, k] * temps["ic"][:, :, k]
            )
            / np.maximum(a_s, 1e-30),
            t_in,
        )
        return a_s, t_s

    def _burn_co(self, nf, co_av, y_new, mdot):
        """CO burning in the bed's non-flaming cells, O2-limited: returns (heat, O2 left, CO left)."""
        n = self.n
        qco = np.zeros((n, n))
        if self.p.co_burns_in_bed:
            burn = np.where(nf, np.minimum(co_av, y_new * mdot * 28.010 / 16.0), 0.0)
            qco = burn * DH_CO_GAS
            y_new = y_new - np.where(mdot > 0, burn * 16.0 / 28.010 / np.maximum(mdot, 1e-300), 0.0)
            co_av = co_av - burn
        return qco, y_new, co_av

    def _char_oxidation(self, temps, k, *, h, y, mdot, nf, areas, r_c, q_ox):
        """One layer's O2-limited char oxidation: fills r_c and q_ox at layer k; returns (CO made, O2 used)."""
        p = self.p
        n = self.n
        flux = {}
        demand = np.zeros((n, n))
        for key in ("iw", "ic"):
            ts = temps[key][:, :, k]
            if p.kinetics:
                ks = p.ks_a * np.exp(-p.ks_ta / ts)
                res = 1.0 / np.maximum(rho_air(ts) * ks, 1e-300) + p.cp_air / np.maximum(h, 1e-12)
            else:
                res = p.cp_air / np.maximum(h, 1e-12)
            flux[key] = np.where(nf & (areas[key] > 0), y / res, 0.0)
            demand += flux[key] * areas[key]
        supply = y * mdot
        scale = np.where(demand > supply, supply / np.maximum(demand, 1e-300), 1.0)
        co_prod = np.zeros((n, n))
        o2_char = np.zeros((n, n))
        for key in ("iw", "ic"):
            ts = temps[key][:, :, k]
            fo2 = flux[key] * scale
            fc = f_co(p, ts)
            s_o2 = (32.0 / 12.011) * (1 - fc) + (16.0 / 12.011) * fc
            rc = fo2 / s_o2
            r_c[key][:, :, k] = rc
            q_ox[key][:, :, k] = rc * (DH_CO2 * (1 - fc) + DH_CO * fc)
            co_prod += rc * fc * (28.010 / 12.011) * areas[key]
            o2_char += fo2 * areas[key]
        return co_prod, o2_char

    def _h_slat(self, mdot, t_in, t_s, k):
        p = self.p
        d = p.slat_b_m
        tf = 0.5 * (t_in + t_s)
        rho = rho_air(tf)
        nu = mu_air(tf) / rho
        void = self._void_now[:, :, k]
        u = np.where(mdot > 0, mdot / self.Af / rho / np.maximum(void, 0.05), 0.0)
        re = u * d / nu
        pr = p.pr
        nu_f = (
            0.3
            + 0.62
            * np.sqrt(re)
            * pr ** (1 / 3)
            / (1 + (0.4 / pr) ** (2 / 3)) ** 0.25
            * (1 + (re / 282000.0) ** 0.625) ** 0.8
        )
        alpha = nu / pr
        ra = G_GRAV * np.abs(t_s - t_in) / tf * d**3 / (nu * alpha)
        nu_n = (0.60 + 0.387 * ra ** (1 / 6) / (1 + (0.559 / pr) ** (9 / 16)) ** (8 / 27)) ** 2
        return k_air(tf) / d * np.maximum(nu_f, nu_n)

    def _void(self) -> np.ndarray:
        p = self.p
        solid = ((self.A_ui + self.A_up) * p.w0 + self.A_iw * self.w_iw) / p.rho_wood + (
            self.A_iw * self.c_iw + self.A_ic * self.c_ic
        ) / (p.chi_char * p.rho_wood)
        return np.clip(1.0 - solid / self.V, 0.05, 1.0)

    def _ergun(self, tg: np.ndarray) -> np.ndarray:
        p = self.p
        H = p.box_m
        tbar = tg.mean(axis=2)
        rho_g = rho_air(tbar)
        dp = G_GRAV * H * (rho_air(np.array(self.T0)) - rho_g)
        av = (self._a_tot() / self.V).mean(axis=2)
        eps = self._void_now.mean(axis=2)
        mu = mu_air(tbar)
        a_e = 150.0 * mu * av**2 / (36.0 * eps**3)
        b_e = 1.75 * rho_g * av / (6.0 * eps**3)
        qa = H * b_e + 0.5 * p.k_minor * rho_g
        qb = H * a_e
        u = np.where(dp > 0, (-qb + np.sqrt(qb**2 + 4 * qa * np.maximum(dp, 0))) / (2 * qa), 0.0)
        return rho_g * u

    # ---------------------------------------------------------------- step
    def pilot_fraction(self) -> float:
        """Share of this physics step's 5 ticks that the pilot covers (ticks [0, D))."""
        first = self.step_no * 5
        on = max(0, min(self.pilot_ticks, first + 5) - first)
        return on / 5.0

    def physics_step(self) -> None:
        p = self.p
        frac = self.pilot_fraction()
        nsub = self._substeps()
        dt = p.dt_phys / nsub
        for _ in range(nsub):
            self._substep(dt, frac)
        self.t += p.dt_phys
        self.step_no += 1

    def _substeps(self) -> int:
        p = self.p
        hmax = 120.0  # bound on slat h used only for the stability estimate
        t_u = max(float(np.max(self.Tu[..., 0])), float(np.max(self.Ts_iw)))
        hr = 4 * p.eps * SIGMA_SB * t_u**3
        lim_skin = self.cap_n[0] / (self.K[0] + hr + hmax)
        lim_int = np.min(self.cap_n[1:-1] / (self.K[:-1] + self.K[1:])) if p.n_slab > 2 else 1e9
        dts = [lim_skin, lim_int]
        if np.any(self.A_ic > 0):
            tic = np.max(np.where(self.A_ic > 0, self.T_ic, 0))
            c = np.min(np.where(self.A_ic > 0, self._cic(), np.inf))
            dts.append(c / (4 * p.eps * SIGMA_SB * tic**3 + hmax))
        dt = 0.9 * min(dts)
        return max(1, math.ceil(p.dt_phys / dt))

    def _substep(self, dt: float, frac: float) -> None:
        p = self.p
        q_pil = p.pilot_w / (math.pi * p.pilot_r_m**2) * frac
        a_fl, qdot_prev, fb, src, fl_bed, fb_direct = self._flame_sources()
        eb = self._emission()
        pil_iw, ein, p_gap = self._pilot_split(q_pil)
        rad_net_out = self._solve_p1(eb, src, ein)
        gabs = p.eps * self.G / 4.0
        # --- draught
        temps = {"ui": self.Tu[..., 0], "iw": self.Ts_iw, "ic": self.T_ic}
        q_gas, r_c, q_ox, q_fl, q_co, q_sol = self._draught(temps, qdot_prev, np.minimum(fb, qdot_prev))
        conv_env = self._step_ui(dt, gabs, q_gas["ui"])
        p_up, up_6a = self._step_up(dt, q_pil)
        removed, conv_iw, mv_eff = self._step_iw(
            dt, gabs, q_gas_iw=q_gas["iw"], q_ox_iw=q_ox["iw"], r_c_iw=r_c["iw"], direct_w=fb_direct + pil_iw
        )
        conv_env += conv_iw
        removed_ic, conv_ic = self._step_ic(dt, gabs, q_gas_ic=q_gas["ic"], q_ox_ic=q_ox["ic"], r_c_ic=r_c["ic"])
        conv_env += conv_ic
        removed += removed_ic
        # ---------------- ledger lines for this substep (fluxes as applied above)
        L = self.ledger
        p_pil_iw = float(pil_iw.sum())
        L["sources"] += (p_up + p_gap + p_pil_iw) * dt
        qdot = mv_eff * p.dh_vol * a_fl  # release from this substep's pyrolysis
        L["combustion_flaming"] += float(qdot.sum()) * dt
        L["combustion_char"] += (
            float((self.A_iw * q_ox["iw"]).sum()) + float((self.A_ic * q_ox["ic"]).sum()) + q_co
        ) * dt
        L["flame_radiative"] += (p.chi_r * float((qdot - fb).sum()) - float(fl_bed.sum())) * dt
        L["plume_convective"] += ((1 - p.chi_r) * float((qdot - fb).sum()) - q_fl) * dt
        L["open_air_rad"] += (rad_net_out + p_gap) * dt
        L["open_air_conv"] += conv_env * dt
        L["open_air_pilotface"] += up_6a * dt
        L["open_air_draught"] += (q_fl + q_co + q_sol) * dt
        L["removed_with_mass"] += removed
        # ---------------- area moves (energy-conserving; mass-carried energy booked)
        removed2, new_ign = self._transfers(frac)
        L["removed_with_mass"] += removed2
        # flaming while m'' >= m''_crit; a piloted ignition attaches a flame for one substep
        self.flaming = (self.A_iw > 0) & ((self.mvol >= p.m_crit) | new_ign)

    def _flame_sources(self):
        """Flames from the previous substep's state: (flaming area, lagged release, feedback, P1 source,
        in-bed flame emission, feedback delivered straight onto the flaming surface)."""
        p = self.p
        n = self.n
        s = (n, n, n)
        fl = self.flaming
        a_fl = np.where(fl, self.A_iw, 0.0)
        qdot_prev = self.mvol * p.dh_vol * a_fl  # lagged: used only by the draught (O2, plume gas)
        fb = p.q_f * a_fl
        # feedback delivery: "attached" share straight onto the flaming surface (tile spec 6c),
        # radiative share chi_r into the in-bed field P1 (reaches neighbours). feedback_mode
        # "p1" sends it all to P1 (the first, rejected-as-unfaithful variant, kept as a sensitivity)
        rad_share = 1.0 if p.feedback_mode == "p1" else p.chi_r
        src = rad_share * fb / self.V
        # flame_in_bed: the flame's radiant output chi_r (Q - feedback) is emitted inside the bed
        # (other bounding end from the spec-literal export); lagged one substep, remainder exported
        fl_bed = p.chi_r * np.maximum(qdot_prev - fb, 0.0) if p.flame_in_bed else np.zeros(s)
        src = src + fl_bed / self.V
        fb_direct = (1 - rad_share) * fb  # W per cell
        return a_fl, qdot_prev, fb, src, fl_bed, fb_direct

    def _emission(self) -> np.ndarray:
        """Area-weighted black-body emissive power of each cell's interior surfaces (ambient if empty)."""
        sb = SIGMA_SB
        a_tot = self._a_tot()
        t_ui = self.Tu[..., 0]
        eb_num = sb * (self.A_ui * t_ui**4 + self.A_iw * self.Ts_iw**4 + self.A_ic * self.T_ic**4)
        return np.where(a_tot > 0, eb_num / np.maximum(a_tot, 1e-30), sb * self.T0**4)

    def _pilot_split(self, q_pil: float):
        """Where the pilot's flux lands: (W per cell onto Iw, incoming boundary
        radiation per face, gap power)."""
        p = self.p
        n = self.n
        sb = SIGMA_SB
        up_live = self.A_up[0] > 0
        # the phi share falls on the outward slat faces under the disc: Up while unlit, then the
        # cell's Iw; once no Iw is left there it passes into the bed through the gaps with the rest
        iw_live = self.A_iw[0] > 0
        to_iw = ~up_live & iw_live
        gap = q_pil * self.overlap / self.Af * np.where(up_live | to_iw, 1 - p.phi, 1.0)
        pil_iw = np.zeros((n, n, n))
        pil_iw[0] = np.where(to_iw, q_pil * p.phi * self.overlap, 0.0)  # W per cell
        ein = {k: np.full(c.shape, sb * self.T0**4) for k, c in self.bfaces.items()}
        ein["x-"] = ein["x-"] + gap
        p_gap = float((gap * self.Af).sum())
        return pil_iw, ein, p_gap

    def _step_ui(self, dt: float, gabs: np.ndarray, q_gas_ui: np.ndarray) -> float:
        """Ui slab; returns its convective envelope loss (W)."""
        p = self.p
        T0 = self.T0
        fenv = self.f_env
        tu = self.Tu
        f0 = gabs - p.eps * SIGMA_SB * tu[..., 0] ** 4 - q_gas_ui - fenv * p.h_env * (tu[..., 0] - T0)
        cond = self.K * (tu[..., :-1] - tu[..., 1:])
        dq = np.zeros_like(tu)
        dq[..., 0] = f0
        dq[..., :-1] -= cond
        dq[..., 1:] += cond
        conv_env = float((self.A_ui * fenv * p.h_env * (tu[..., 0] - T0)).sum())
        self.Tu = tu + dt * dq / self.cap_n
        return conv_env

    def _step_up(self, dt: float, q_pil: float) -> tuple[float, float]:
        """Up slab (outward faces under the disc); returns (pilot power absorbed, 6a loss to the room)."""
        p = self.p
        T0 = self.T0
        n = self.n
        tp = self.Tup
        q_front = np.zeros((n, n, n))
        q_front[0] = q_pil
        loss_up = p.eps * SIGMA_SB * (tp[..., 0] ** 4 - T0**4) + p.h_env * (tp[..., 0] - T0)
        condp = self.K * (tp[..., :-1] - tp[..., 1:])
        dqp = np.zeros_like(tp)
        dqp[..., 0] = q_front - loss_up
        dqp[..., :-1] -= condp
        dqp[..., 1:] += condp
        self.Tup = tp + dt * dqp / self.cap_n
        p_up = float((self.A_up * q_front).sum())
        up_6a = float((self.A_up * loss_up).sum())
        return p_up, up_6a

    def _step_iw(self, dt, gabs, *, q_gas_iw, q_ox_iw, r_c_iw, direct_w):
        """Iw: explicit 1 mm skin (tile spec 6b); pinned at T_p while wood remains, the excess over T_p
        gasifies: m'' = q''_net / L_g (6c). Returns (energy removed with mass, convective envelope loss,
        volatile mass flux)."""
        p = self.p
        T0 = self.T0
        fenv = self.f_env
        removed = 0.0
        live = self.A_iw > 0
        cs = self.cap_n[0]
        t_old = self.Ts_iw
        direct = np.where(live, direct_w / np.maximum(self.A_iw, 1e-30), 0.0)
        qn = gabs - p.eps * SIGMA_SB * t_old**4 - q_gas_iw - fenv * p.h_env * (t_old - T0) + q_ox_iw + direct
        t_new = t_old + dt * qn / cs
        can_pyr = live & (self.w_iw > 0)
        excess = np.where(can_pyr & (t_new > p.t_p), cs * (t_new - p.t_p), 0.0)  # J/m^2
        t_new = np.where(excess > 0, p.t_p, t_new)
        mv = excess / p.l_g / dt
        pyr = mv / (1 - p.chi_char) * dt
        dw = np.minimum(self.w_iw, pyr)
        mv_eff = dw * (1 - p.chi_char) / dt
        removed += float((self.A_iw * excess).sum())  # gasification enthalpy leaves with volatiles
        dcox = np.minimum(r_c_iw * dt, self.c_iw + p.chi_char * dw)
        m_old = self.w_iw + self.c_iw
        w_new = self.w_iw - dw
        c_new = self.c_iw + p.chi_char * dw - dcox
        m_new = w_new + c_new
        e_new = np.where(m_old > 0, self.e_iw * m_new / np.maximum(m_old, 1e-30), 0.0)
        removed += float((self.A_iw * (self.e_iw - e_new)).sum())
        conv = float((self.A_iw * fenv * p.h_env * (t_old - T0)).sum())
        self.w_iw = np.where(live, w_new, 0.0)
        self.c_iw = np.where(live, c_new, 0.0)
        self.e_iw = np.where(live, e_new, 0.0)
        self.Ts_iw = np.where(live, t_new, T0)
        self.mvol = np.where(live, mv_eff, 0.0)
        return removed, conv, mv_eff

    def _step_ic(self, dt, gabs, *, q_gas_ic, q_ox_ic, r_c_ic) -> tuple[float, float]:
        """Ic: lumped char; returns (energy removed with burnt char, convective envelope loss)."""
        p = self.p
        T0 = self.T0
        tic = self.T_ic
        cap_old = self._cic()
        f_ic = gabs - p.eps * SIGMA_SB * tic**4 - q_gas_ic - self.f_env * p.h_env * (tic - T0) + q_ox_ic
        live_c = self.A_ic > 0
        tic_new = np.where(live_c, tic + dt * f_ic / cap_old, T0)
        conv = float((self.A_ic * self.f_env * p.h_env * (tic - T0)).sum())
        dc = np.minimum(r_c_ic * dt, self.c_ic)
        self.c_ic = np.where(live_c, self.c_ic - dc, 0.0)
        cap_new = self._cic()
        removed = float((self.A_ic * (cap_old - cap_new) * (tic_new - T0)).sum())
        self.T_ic = tic_new
        return removed, conv

    def _transfers(self, frac: float) -> float:
        p = self.p
        T0 = self.T0
        removed = 0.0
        new_ign = np.zeros(self.A_iw.shape, dtype=bool)
        skin_tp = self.cap_n[0] * (p.t_p - T0)
        e_slab_u = (self.Tu - T0) @ self.cap_n - skin_tp
        e_slab_p = (self.Tup - T0) @ self.cap_n - skin_tp
        nb = self._flame_neighbourhood()
        # Up -> Iw: skin at T_p with the pilot on or a flame adjacent
        up_ign = (self.A_up > 0) & (self.Tup[..., 0] >= p.t_p) & ((frac > 0) | nb)
        if np.any(up_ign):
            da = np.where(up_ign, self.A_up, 0.0)
            self._merge_iw(da, p.w0, 0.0, e_slab_p)
            self.A_up = self.A_up - da
            new_ign |= up_ign
        # Ui -> Iw by the reconstructed sub-cell skin profile
        frac_hot = self._hot_fraction()
        target = frac_hot * self.A_ui0
        already = self.A_ui0 - self.A_ui
        da = np.where(nb, np.clip(target - already, 0.0, self.A_ui), 0.0)
        if np.any(da > 0):
            self._merge_iw(da, p.w0, 0.0, e_slab_u)
            self.A_ui = self.A_ui - da
            new_ign |= da > 0
        # Iw -> Ic when the wood is gone
        done = (self.A_iw > 0) & (self.w_iw <= 1e-9)
        if np.any(done):
            removed += self._iw_to_ic(done)
        # Ic burn-out
        gone = (self.A_ic > 0) & (self.c_ic <= 1e-4)
        if np.any(gone):
            removed += float((np.where(gone, self.A_ic * self._cic() * (self.T_ic - T0), 0.0)).sum())
            self.A_ic = np.where(gone, 0.0, self.A_ic)
            self.c_ic = np.where(gone, 0.0, self.c_ic)
            self.T_ic = np.where(gone, T0, self.T_ic)
        return removed, new_ign

    def _flame_neighbourhood(self) -> np.ndarray:
        """Piloted condition: flame in the cell or a face neighbour."""
        fl = self.flaming | (self.mvol >= self.p.m_crit) & (self.A_iw > 0)
        nb = fl.copy()
        nb[1:] |= fl[:-1]
        nb[:-1] |= fl[1:]
        nb[:, 1:] |= fl[:, :-1]
        nb[:, :-1] |= fl[:, 1:]
        nb[:, :, 1:] |= fl[:, :, :-1]
        nb[:, :, :-1] |= fl[:, :, 1:]
        return nb

    def _iw_to_ic(self, done: np.ndarray) -> float:
        """Move the Iw area whose wood is gone into Ic, energy-conserving; returns the energy removed with mass."""
        p = self.p
        T0 = self.T0
        a = np.where(done, self.A_iw, 0.0)
        c = np.where(done, self.c_iw, 0.0)
        t_new = np.where(done, self.Ts_iw, T0)
        e_char = a * np.maximum(c, p.char_floor) * p.c_char * (t_new - T0)
        e_skin = a * self.cap_n[0] * (t_new - T0)
        removed = float((a * self.e_iw + e_skin - e_char).sum())
        e_ic = self.A_ic * self._cic() * (self.T_ic - T0) + e_char
        a_new = self.A_ic + a
        c_mix = np.where(a_new > 0, (self.A_ic * self.c_ic + a * c) / np.maximum(a_new, 1e-30), 0.0)
        self.A_ic = a_new
        self.c_ic = c_mix
        cap = np.maximum(c_mix, p.char_floor) * p.c_char
        self.T_ic = np.where(a_new > 0, T0 + e_ic / np.maximum(a_new * cap, 1e-30), T0)
        self.A_iw = np.where(done, 0.0, self.A_iw)
        self.w_iw = np.where(done, 0.0, self.w_iw)
        self.c_iw = np.where(done, 0.0, self.c_iw)
        self.e_iw = np.where(done, 0.0, self.e_iw)
        self.mvol = np.where(done, 0.0, self.mvol)
        self.Ts_iw = np.where(done, T0, self.Ts_iw)
        return removed

    def _merge_iw(self, da: np.ndarray, w_add: float, c_add: float, e_add: np.ndarray) -> None:
        a_new = self.A_iw + da
        safe = np.maximum(a_new, 1e-30)
        self.w_iw = np.where(a_new > 0, (self.A_iw * self.w_iw + da * w_add) / safe, 0.0)
        self.c_iw = np.where(a_new > 0, (self.A_iw * self.c_iw + da * c_add) / safe, 0.0)
        self.e_iw = np.where(a_new > 0, (self.A_iw * self.e_iw + da * e_add) / safe, 0.0)
        self.Ts_iw = np.where(a_new > 0, (self.A_iw * self.Ts_iw + da * self.p.t_p) / safe, self.T0)
        self.A_iw = a_new

    def _hot_fraction(self) -> np.ndarray:
        """Fraction of each cell where the linearly reconstructed unburnt skin is >= T_p.
        Gradient: minmod of one-sided differences of the cell surface-temperature field."""
        p = self.p
        ts = self.surf_T()
        tu = self.Tu[..., 0]
        grads = []
        for ax in range(3):
            d_plus = np.zeros_like(ts)
            d_minus = np.zeros_like(ts)
            sl_a = [slice(None)] * 3
            sl_b = [slice(None)] * 3
            sl_a[ax] = slice(0, -1)
            sl_b[ax] = slice(1, None)
            diff = (ts[tuple(sl_b)] - ts[tuple(sl_a)]) / self.dx
            d_plus[tuple(sl_a)] = diff
            d_minus[tuple(sl_b)] = diff
            mm = np.where(d_plus * d_minus > 0, np.sign(d_plus) * np.minimum(np.abs(d_plus), np.abs(d_minus)), 0.0)
            # at the box edge use the one-sided difference
            edge_lo = [slice(None)] * 3
            edge_hi = [slice(None)] * 3
            edge_lo[ax] = 0
            edge_hi[ax] = -1
            mm[tuple(edge_lo)] = d_plus[tuple(edge_lo)]
            mm[tuple(edge_hi)] = d_minus[tuple(edge_hi)]
            grads.append(mm)
        m = p.m_sub
        o = ((np.arange(m) + 0.5) / m - 0.5) * self.dx
        ox, oy, oz = np.meshgrid(o, o, o, indexing="ij")
        frac = (tu >= p.t_p).astype(float)
        reach = 0.5 * self.dx * (np.abs(grads[0]) + np.abs(grads[1]) + np.abs(grads[2]))
        cand = (self.A_ui > 0) & (tu + reach >= p.t_p) & (tu - reach < p.t_p)
        if np.any(cand):
            g0, g1, g2 = grads[0][cand], grads[1][cand], grads[2][cand]
            off = g0[:, None] * ox.ravel() + g1[:, None] * oy.ravel() + g2[:, None] * oz.ravel()
            frac[cand] = ((tu[cand][:, None] + off) >= p.t_p).mean(axis=-1)
        return frac

    # ---------------------------------------------------------- observables
    def envelope_layer(self) -> dict[str, np.ndarray]:
        """Per envelope face: the sight-line-weighted envelope-layer surface temperature on face
        patches (weight beta*exp(-int beta), in metres), sampled bilinearly on a 1 cm grid."""
        ts = self.surf_T()
        beta = np.maximum(self._a_tot() / self.V / 4.0, 1e-6)
        ds = 0.002
        out = {}
        lines = {
            "x-": (ts, beta),
            "x+": (ts[::-1], beta[::-1]),
            "y-": (ts.transpose(1, 0, 2), beta.transpose(1, 0, 2)),
            "y+": (ts.transpose(1, 0, 2)[::-1], beta.transpose(1, 0, 2)[::-1]),
            "z+": (ts.transpose(2, 0, 1)[::-1], beta.transpose(2, 0, 1)[::-1]),
        }
        key = beta.tobytes()
        if key != getattr(self, "_lay_key", None):
            self._lay_w = {}
            for name, (_, bl) in lines.items():
                bq = np.moveaxis(bl[self.cell_of_s], 0, -1)  # (a, b, Q)
                tau = np.cumsum(bq, axis=-1) * ds - 0.5 * bq * ds
                w = bq * np.exp(-tau) * ds
                w = w / np.maximum(w.sum(-1, keepdims=True), 1e-30)
                self._lay_w[name] = w @ self.Lprof  # (a, b, n): linear in the line's cell values
            self._lay_key = key
        for name, (tl, _) in lines.items():
            out[name] = np.maximum(np.einsum("abm,mab->ab", self._lay_w[name], tl), self.T0)
        return out

    def sample_area(self, patch: np.ndarray, thresh: float) -> float:
        vals = self.W1 @ patch @ self.W1.T
        return float((vals >= thresh).sum()) * self.sample_da

    def brightness(self) -> dict[str, np.ndarray]:
        sb = SIGMA_SB
        out = {}
        for name, q in self.q_out_face.items():
            qplus = sb * self.T0**4 + q
            out[name] = (np.maximum(qplus, 0) / sb) ** 0.25
        return out

    def crack_patches(self) -> dict[str, np.ndarray]:
        frac = 1.0 - self._cell_wood() / np.maximum(self.cell_fuel0, 1e-30)
        return {"x-": frac[0], "x+": frac[-1], "y-": frac[:, 0], "y+": frac[:, -1], "z+": frac[:, :, -1]}
