"""The accelerant spike's bed with burning surfaces and flame gas de-pinned from T_p (spike, never in src/).

Preregistration §1 (commit 1c58b75). What this changes in spikes/physics/accelerant/wetbed.py::WetBed:
  surface_mode=char   Iw's 1 mm skin is the char-surface temperature T_c: no pin at T_p; it loses
                      q''_k = k_c (T_c - T_f) / delta_c to the pyrolysis front, delta_c = max(m_c / rho_c, skin), and
                      m''_v = q''_k / L_g (§1.1). Every other term of the skin balance is the bed's.
  gas_cap=flame       gas leaving a flaming cell: min(T_fl, t_in + (1 - chi_r)(Q - fb) / (m c_p)); its buoyancy
                      temperature is the mean of inlet and outlet, as in non-flaming cells (§1.2).
  gas_cap=mccaffrey_z the cap is McCaffrey's three-region centre-line temperature at z / Q^(2/5) of the column (Mz).
  incell_contact      H2: a flaming cell's gas also exchanges with that cell's unlit and non-flaming parts (§1.3).
With surface_mode=pinned, gas_cap=tp and no contact every override calls the parent, so the parents' runs are
reproduced bit for bit (E4).
"""

from __future__ import annotations

import math

import numpy as np
from constants import SIGMA_SB
from hot_constants import HotParams, mccaffrey_dt
from wetbed import WetBed

PARTS = ("ui", "iw", "ic", "ia")


class HotBed(WetBed):
    p: HotParams

    def __post_init__(self) -> None:
        super().__post_init__()
        self.lit0 = float(self.A_iw.sum())  # area lit at t = 0 (scenarios F and B)
        self.gas_exit = (math.nan, math.nan)  # (flow-weighted mean, max) K of gas leaving flaming cells

    # ------------------------------------------------------------ char layer
    def delta_c(self) -> np.ndarray:
        """Char-layer thickness (m) of each cell's Iw, floored at the 1 mm skin."""
        return np.maximum(self.c_iw / self.p.rho_c, self.p.skin_m)

    def front_flux(self, t_c: np.ndarray) -> np.ndarray:
        """q''_k (W/m^2) from a char surface at t_c to the front at T_f; zero where the front has stalled or no
        wood is left."""
        p = self.p
        kc = p.k_char(0.5 * (t_c + p.t_f))
        on = (self.A_iw > 0) & (self.w_iw > 0) & (t_c > p.t_f)
        return np.where(on, kc * (t_c - p.t_f) / self.delta_c(), 0.0)

    def _step_iw(self, dt, gabs, *, q_gas_iw, q_ox_iw, r_c_iw, direct_w):
        """Bed._step_iw with the pin replaced by conduction to the front (§1.1)."""
        p = self.p
        if p.surface_mode == "pinned":
            return super()._step_iw(dt, gabs, q_gas_iw=q_gas_iw, q_ox_iw=q_ox_iw, r_c_iw=r_c_iw, direct_w=direct_w)
        T0 = self.T0
        fenv = self.f_env
        live = self.A_iw > 0
        cs = self.cap_n[0]
        t_old = self.Ts_iw
        direct = np.where(live, direct_w / np.maximum(self.A_iw, 1e-30), 0.0)
        qn = gabs - p.eps * SIGMA_SB * t_old**4 - q_gas_iw - fenv * p.h_env * (t_old - T0) + q_ox_iw + direct
        qk = self.front_flux(t_old)
        t_new = t_old + dt * (qn - qk) / cs
        removed = float((self.A_iw * qk).sum()) * dt  # the front's energy leaves with the volatiles
        pyr = qk / p.l_g / (1 - p.chi_char) * dt
        dw = np.minimum(self.w_iw, pyr)
        mv_eff = dw * (1 - p.chi_char) / dt
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

    def _substeps(self) -> int:
        n = super()._substeps()
        p = self.p
        live = self.A_iw > 0
        if p.surface_mode == "pinned" or not np.any(live):
            return n
        t = self.Ts_iw
        g = float(np.max(np.where(live, p.k_char(0.5 * (t + p.t_f)) / self.delta_c(), 0.0)))
        hr = 4 * p.eps * SIGMA_SB * float(np.max(np.where(live, t, 0.0))) ** 3
        lim = 0.9 * self.cap_n[0] / (g + hr + 120.0)
        return max(n // p.sub_mult, math.ceil(p.dt_phys / lim)) * p.sub_mult

    # ------------------------------------------------------------- draught
    def _cap_column(self, k: int, fl: np.ndarray, qdot: np.ndarray, col: dict) -> np.ndarray:
        """The flame-gas ceiling (K) of layer k: T_p, T_fl, or McCaffrey at the column's z / Q^(2/5) (Mz)."""
        p = self.p
        if p.gas_cap == "tp":
            return np.full(fl.shape, p.t_p)
        if p.gas_cap == "flame":
            return np.full(fl.shape, p.t_fl)
        col["z0"] = np.where(fl & np.isnan(col["z0"]), k * self.dx, col["z0"])
        col["q"] = col["q"] + np.where(fl, qdot[:, :, k], 0.0)
        z = (k + 1) * self.dx - col["z0"]
        x = np.where(fl & (col["q"] > 0), z / np.maximum(col["q"] / 1e3, 1e-30) ** 0.4, np.inf)
        return self.T0 + mccaffrey_dt(x, self.T0, p.mcc_c)

    def _contact(self, temps, k, *, fl, t_in2, h, cap, q_gas):
        """H2: gas leaving the flame zone of a flaming cell exchanges with that cell's unlit and non-flaming parts
        by the bed's exponential law. Returns (gas temperature leaving the cell, power gained by the gas)."""
        mask = {
            "ui": np.ones(fl.shape, dtype=bool),
            "ic": np.ones(fl.shape, dtype=bool),
            "iw": ~self.fl_iw[:, :, k],
            "ia": ~self.fl_ia[:, :, k],
        }
        area = {"ui": self.A_ui, "iw": self.A_iw, "ic": self.A_ic, "ia": self.A_ia}
        a_c = sum(np.where(mask[key], area[key][:, :, k], 0.0) for key in PARTS)
        num = sum(np.where(mask[key], area[key][:, :, k] * temps[key][:, :, k], 0.0) for key in PARTS)
        t_c = np.where(a_c > 0, num / np.maximum(a_c, 1e-30), t_in2)
        on = fl & (a_c > 0) & (cap > 0)
        ntu = np.where(cap > 0, h * a_c / np.maximum(cap, 1e-300), np.inf)
        t_out = np.where(on, t_c + (t_in2 - t_c) * np.exp(-ntu), t_in2)
        qsol = np.where(on, cap * (t_out - t_in2), 0.0)
        tgm = np.where(on, t_c - qsol / np.maximum(h * a_c, 1e-300), t_in2)
        for key in PARTS:
            q_gas[key][:, :, k] = np.where(on & mask[key], h * (temps[key][:, :, k] - tgm), q_gas[key][:, :, k])
        return t_out, float(qsol.sum())

    def _layer_o2_co(self, temps, k, *, fl, y, yco, mdot, qdot, h, rq):
        """Layer k's O2 use (flames by Huggett, char oxidation in non-flaming cells) and CO burning: the parent's
        expressions, moved here unchanged. Fills r_c and q_ox (rq); returns (CO heat, O2 left, CO fraction)."""
        p = self.p
        r_c, q_ox = rq
        o2_fl = np.where(fl, np.minimum(y * mdot, qdot[:, :, k] / p.huggett), 0.0)
        nf = ~fl
        areas = {"iw": self.A_iw[:, :, k] * (self.c_iw[:, :, k] > 0), "ic": self.A_ic[:, :, k]}
        co_prod, o2_char = self._char_oxidation(temps, k, h=h, y=y, mdot=mdot, nf=nf, areas=areas, r_c=r_c, q_ox=q_ox)
        y_new = y - np.where(mdot > 0, (o2_fl + o2_char) / np.maximum(mdot, 1e-300), 0.0)
        y_new = np.maximum(y_new, 0.0)
        co_av = yco * mdot + co_prod
        qco, y_new, co_av = self._burn_co(nf, co_av, y_new, mdot)
        return qco, y_new, np.where(mdot > 0, co_av / np.maximum(mdot, 1e-300), 0.0)

    def _draught(self, temps: dict[str, np.ndarray], qdot: np.ndarray, fb: np.ndarray):
        """WetBed._draught with the flame-gas ceiling of §1.2 and, in H2, the contact of §1.3. Non-flaming cells
        are computed with the parent's expressions unchanged."""
        p = self.p
        if p.gas_cap == "tp" and not p.incell_contact:
            return super()._draught(temps, qdot, fb)
        n = self.n
        s = (n, n, n)
        q_gas = {k: np.zeros(s) for k in PARTS}
        r_c = {k: np.zeros(s) for k in ("iw", "ic")}
        q_ox = {k: np.zeros(s) for k in ("iw", "ic")}
        tg = np.zeros(s)
        t_in = np.full((n, n), self.T0)
        y = np.full((n, n), p.y_o2)
        yco = np.zeros((n, n))
        mdot = self.Gcol * self.Af
        tot = [0.0, 0.0, 0.0]
        plume_avail = (1 - p.chi_r) * (qdot - fb)
        self._void_now = self._void()
        col = {"z0": np.full((n, n), np.nan), "q": np.zeros((n, n))}
        exit_acc = [0.0, 0.0, math.nan]  # flow x temperature, flow, max, of gas leaving flaming cells
        for k in range(n):
            fl = self.flaming[:, :, k]
            t_fl = np.maximum(t_in, self._cap_column(k, fl, qdot, col))
            need = mdot * p.cp_air * (t_fl - t_in)
            qfl = np.where(fl, np.minimum(need, plume_avail[:, :, k]), 0.0)
            tot[0] += float(qfl.sum())
            nf = ~fl
            a_s, t_s = self._layer_surface(temps, k, t_in)
            h = self._h_slat(mdot, t_in, t_s, k)
            qco, y_new, yco = self._layer_o2_co(
                temps, k, fl=fl, y=y, yco=yco, mdot=mdot, qdot=qdot, h=h, rq=(r_c, q_ox)
            )
            tot[1] += float(qco.sum())
            t_in2 = t_in + np.where(mdot > 0, (qco + qfl) / np.maximum(mdot * p.cp_air, 1e-300), 0.0)
            cap = mdot * p.cp_air
            ntu = np.where(cap > 0, h * a_s / np.maximum(cap, 1e-300), np.inf)
            t_out = np.where(nf & (a_s > 0), t_s + (t_in2 - t_s) * np.exp(-ntu), t_in2)
            qsol = np.where(nf & (a_s > 0) & (cap > 0), cap * (t_out - t_in2), 0.0)
            tot[2] += float(qsol.sum())
            tgm = np.where(a_s > 0, t_s - qsol / np.maximum(h * a_s, 1e-300), t_in2)
            for key in PARTS:
                q_gas[key][:, :, k] = np.where(nf & (cap > 0), h * (temps[key][:, :, k] - tgm), 0.0)
            t_exit = t_in2
            if p.incell_contact:
                t_exit, q_c = self._contact(temps, k, fl=fl, t_in2=t_in2, h=h, cap=cap, q_gas=q_gas)
                tot[2] += q_c
            # buoyancy: a flaming cell's gas at the mean of inlet and outlet; stagnant gas in a flame at the cap
            tg[:, :, k] = np.where(
                fl,
                np.where(mdot > 0, 0.5 * (t_in + t_exit), t_fl),
                np.where(cap > 0, 0.5 * (t_in2 + t_out), t_s),
            )
            _track_exit(exit_acc, fl & (mdot > 0), mdot, t_exit)
            t_in = np.where(fl, t_exit, t_out)
            y = y_new
        self.Tg = tg
        self.o2_supply = float((mdot * p.y_o2).sum())
        self.gas_exit = (exit_acc[0] / exit_acc[1] if exit_acc[1] > 0 else math.nan, exit_acc[2])
        self.Gcol = self._ergun(tg)
        return q_gas, r_c, q_ox, tot[0], tot[1], tot[2]


def _track_exit(acc: list[float], go: np.ndarray, mdot: np.ndarray, t_exit: np.ndarray) -> None:
    """Accumulate the flow-weighted and the peak temperature of gas leaving flaming cells (reported only)."""
    if np.any(go):
        acc[0] += float((mdot * t_exit)[go].sum())
        acc[1] += float(mdot[go].sum())
        acc[2] = float(np.nanmax([acc[2], float(t_exit[go].max())]))
