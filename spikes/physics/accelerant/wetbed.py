"""The bed spike's porous crate carrying an in-depth kerosene loading (spike, never imported by src/).

Preregistration §1 (commit 40d79a6). What this adds to spikes/physics/bed/model.py::Bed:
  liquid   kg/m^2 per slab node on every profiled part (Ui, Up, Ia); its heat capacity joins the node's.
  drying   a wet node is capped at T_b; the energy above it evaporates liquid at L_v (`evaporate`), and the vapour
           reaches the surface at once.
  Ia       ignited and still wet: keeps the 10-node profile, flames while its fuel heat-release flux is at least
           q''_crit = m''_crit * dH_c,wood (or the mass form), runs 6c on its surface node once that node is dry and
           reaches T_p, and merges into Iw when it holds no liquid and its surface is pinned at T_p.
  ignition a wetted area ignites at T_b (dry areas at T_p, unchanged), by the bed's piloted rule and reconstruction.
With zero loading every added term is an exact zero, so the bed's state evolves bit for bit (E4(ii)).
"""

from __future__ import annotations

import numpy as np
from acc_constants import AccParams
from constants import SIGMA_SB
from model import LEDGER_IN, LEDGER_OUT, Bed

DRY = 1e-9  # kg/m^2: an area holding no more liquid than this is dry (preregistration §1)
ACC_IN = (*LEDGER_IN, "combustion_accelerant")
ACC_OUT = (*LEDGER_OUT, "vapour_unburnt")


def evaporate(
    t_new: np.ndarray, liq: np.ndarray, cap_w: np.ndarray, *, t_b: float, l_v: float, c_l: float, t0: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Cap wet nodes at T_b; the energy above that level evaporates liquid at L_v.

    t_new are temperatures after an explicit update made with capacity cap_w + liq*c_l (J/m^2 K). The vapour
    carries L_v + c_l (T_b - T0) per kg. Returns (temperatures, liquid left, kg/m^2 evaporated).
    """
    cap = cap_w + liq * c_l
    ex = np.where((liq > 0) & (t_new > t_b), cap * (t_new - t_b), 0.0)
    dm = np.minimum(ex / l_v, liq)
    liq_new = liq - dm
    u = cap * (t_new - t0) - dm * (l_v + c_l * (t_b - t0))
    t = np.where(dm > 0, t0 + u / (cap_w + liq_new * c_l), t_new)
    return t, liq_new, dm


def initial_profile(p: AccParams, dxs: np.ndarray) -> np.ndarray:
    """Liquid per node (kg/m^2) for the authored loading: uniform by node thickness, or filled from the face."""
    total = p.liquid_per_area
    if p.distribution == "uniform":
        return total * dxs / dxs.sum()
    cap = p.void_wood * dxs * p.rho_l
    filled = np.minimum(np.maximum(total - (np.cumsum(cap) - cap), 0.0), cap)
    if filled.sum() < total * (1 - 1e-12):
        raise ValueError("loading exceeds the half-slat's void cap")
    return filled


class WetBed(Bed):
    p: AccParams

    # ---------------------------------------------------------------- setup
    def _init_parts(self, s: tuple[int, int, int], a_cell: float) -> None:
        super()._init_parts(s, a_cell)
        p = self.p
        prof = initial_profile(p, self.dxs)
        self.Lu = np.broadcast_to(prof, (*s, p.n_slab)).copy()
        self.Lup = np.where(self.A_up[..., None] > 0, self.Lu, 0.0)
        self.A_ia = np.zeros(s)
        self.Tia = np.full((*s, p.n_slab), self.T0)
        self.Lia = np.zeros((*s, p.n_slab))
        self.w_ia = np.zeros(s)
        self.c_ia = np.zeros(s)
        self.mk_ia = np.zeros(s)
        self.mw_ia = np.zeros(s)
        self.fl_ia = np.zeros(s, dtype=bool)
        self.fl_iw = np.zeros(s, dtype=bool)
        self.lit_cum = np.zeros(s)  # area ever ignited, any fuel
        self.wood_cum = np.zeros(s)  # area entered wood pyrolysis while flaming
        self.wood_unfl = np.zeros(s)  # Ia -> Iw merges made while not flaming (reported, the loose lambda_w)
        self.up_to_ia = np.zeros(s)  # disc area that ignited on kerosene
        self.liq0 = self.liquid_mass()
        self.burnt_kg = 0.0
        self.vented_kg = 0.0
        self.qdot_last = 0.0

    def __post_init__(self) -> None:
        super().__post_init__()
        self.ledger["combustion_accelerant"] = 0.0
        self.ledger["vapour_unburnt"] = 0.0
        self.fl_iw = self.flaming.copy()  # the F scenario sets bed flaming at t = 0

    # ------------------------------------------------------------- measures
    def liquid_mass(self) -> float:
        return float(
            (self.A_ui * self.Lu.sum(-1)).sum()
            + (self.A_up * self.Lup.sum(-1)).sum()
            + (self.A_ia * self.Lia.sum(-1)).sum()
        )

    def _cell_fuel(self) -> np.ndarray:
        return super()._cell_fuel() + self.A_ia * (self.w_ia + self.c_ia)

    def _cell_wood(self) -> np.ndarray:
        return super()._cell_wood() + self.A_ia * self.w_ia

    def _liquid_heat(self) -> float:
        c_l = self.p.c_l
        return float(
            (self.A_ui * ((self.Lu * c_l) * (self.Tu - self.T0)).sum(-1)).sum()
            + (self.A_up * ((self.Lup * c_l) * (self.Tup - self.T0)).sum(-1)).sum()
            + (self.A_ia * ((self.Lia * c_l) * (self.Tia - self.T0)).sum(-1)).sum()
        )

    def energies(self) -> tuple[float, float]:
        cells, skins = super().energies()
        if not hasattr(self, "A_ia"):
            return cells, skins
        dt_a = self.Tia - self.T0
        skins = skins + float((self.A_ia * self.cap_n[0] * dt_a[..., 0]).sum())
        cells = cells + float((self.A_ia * (dt_a[..., 1:] @ self.cap_n[1:])).sum()) + self._liquid_heat()
        return cells, skins

    def _a_tot(self) -> np.ndarray:
        return super()._a_tot() + self.A_ia

    def surf_T(self) -> np.ndarray:
        a = self._a_tot()
        num = (
            self.A_ui * self.Tu[..., 0] + self.A_iw * self.Ts_iw + self.A_ic * self.T_ic + self.A_ia * self.Tia[..., 0]
        )
        return np.where(a > 0, num / np.maximum(a, 1e-30), self.T0)

    def _emission(self) -> np.ndarray:
        sb = SIGMA_SB
        a_tot = self._a_tot()
        t_ui = self.Tu[..., 0]
        eb_num = sb * (
            self.A_ui * t_ui**4
            + self.A_iw * self.Ts_iw**4
            + self.A_ic * self.T_ic**4
            + self.A_ia * self.Tia[..., 0] ** 4
        )
        return np.where(a_tot > 0, eb_num / np.maximum(a_tot, 1e-30), sb * self.T0**4)

    def _void(self) -> np.ndarray:
        p = self.p
        solid = ((self.A_ui + self.A_up) * p.w0 + self.A_iw * self.w_iw + self.A_ia * self.w_ia) / p.rho_wood + (
            self.A_iw * self.c_iw + self.A_ic * self.c_ic + self.A_ia * self.c_ia
        ) / (p.chi_char * p.rho_wood)
        return np.clip(1.0 - solid / self.V, 0.05, 1.0)

    def _layer_surface(self, temps, k, t_in):
        a_ui = self.A_ui[:, :, k]
        a_s = a_ui + self.A_iw[:, :, k] + self.A_ic[:, :, k] + self.A_ia[:, :, k]
        t_s = np.where(
            a_s > 0,
            (
                a_ui * temps["ui"][:, :, k]
                + self.A_iw[:, :, k] * temps["iw"][:, :, k]
                + self.A_ic[:, :, k] * temps["ic"][:, :, k]
                + self.A_ia[:, :, k] * temps["ia"][:, :, k]
            )
            / np.maximum(a_s, 1e-30),
            t_in,
        )
        return a_s, t_s

    # ------------------------------------------------------------- draught
    def _draught(self, temps: dict[str, np.ndarray], qdot: np.ndarray, fb: np.ndarray):
        """The bed's column march, with the Ia surfaces exchanging heat with non-flaming gas like the other parts.
        Copied from model.py::Bed._draught; the only change is the part list ("ia" added)."""
        p = self.p
        n = self.n
        s = (n, n, n)
        q_gas = {k: np.zeros(s) for k in ("ui", "iw", "ic", "ia")}
        r_c = {k: np.zeros(s) for k in ("iw", "ic")}
        q_ox = {k: np.zeros(s) for k in ("iw", "ic")}
        tg = np.zeros(s)
        t_in = np.full((n, n), self.T0)
        y = np.full((n, n), p.y_o2)
        yco = np.zeros((n, n))
        mdot = self.Gcol * self.Af
        tot = [0.0, 0.0, 0.0]  # flame-gas heating, CO burning, solid exchange
        plume_avail = (1 - p.chi_r) * (qdot - fb)
        self._void_now = self._void()
        for k in range(n):
            fl = self.flaming[:, :, k]
            t_fl = np.maximum(t_in, p.t_p)
            need = mdot * p.cp_air * (t_fl - t_in)
            qfl = np.where(fl, np.minimum(need, plume_avail[:, :, k]), 0.0)
            tot[0] += float(qfl.sum())
            o2_fl = np.where(fl, np.minimum(y * mdot, qdot[:, :, k] / p.huggett), 0.0)
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
            tot[1] += float(qco.sum())
            yco = np.where(mdot > 0, co_av / np.maximum(mdot, 1e-300), 0.0)
            t_in2 = t_in + np.where(mdot > 0, (qco + qfl) / np.maximum(mdot * p.cp_air, 1e-300), 0.0)
            cap = mdot * p.cp_air
            ntu = np.where(cap > 0, h * a_s / np.maximum(cap, 1e-300), np.inf)
            t_out = np.where(nf & (a_s > 0), t_s + (t_in2 - t_s) * np.exp(-ntu), t_in2)
            qsol = np.where(nf & (a_s > 0) & (cap > 0), cap * (t_out - t_in2), 0.0)
            tot[2] += float(qsol.sum())
            tgm = np.where(a_s > 0, t_s - qsol / np.maximum(h * a_s, 1e-300), t_in2)
            for key in ("ui", "iw", "ic", "ia"):
                q_gas[key][:, :, k] = np.where(nf & (cap > 0), h * (temps[key][:, :, k] - tgm), 0.0)
            tg[:, :, k] = np.where(fl, t_fl, np.where(cap > 0, 0.5 * (t_in2 + t_out), t_s))
            t_in = np.where(fl, np.where(mdot > 0, t_in + qfl / np.maximum(mdot * p.cp_air, 1e-300), t_in), t_out)
            y = y_new
        self.Tg = tg
        self.o2_supply = float((mdot * p.y_o2).sum())
        self.Gcol = self._ergun(tg)
        return q_gas, r_c, q_ox, tot[0], tot[1], tot[2]

    # ---------------------------------------------------------------- step
    def _substeps(self) -> int:
        nsub = super()._substeps()
        if np.any(self.A_ia > 0):
            p = self.p
            t_a = float(np.max(np.where(self.A_ia[..., None] > 0, self.Tia, 0.0)))
            hr = 4 * p.eps * SIGMA_SB * t_a**3
            lim = 0.9 * self.cap_n[0] / (self.K[0] + hr + 120.0)
            nsub = max(nsub, int(np.ceil(p.dt_phys / lim)))
        return nsub * self.p.sub_mult

    def _substep(self, dt: float, frac: float) -> None:
        p = self.p
        q_pil = p.pilot_w / (np.pi * p.pilot_r_m**2) * frac
        fs = self._flame_sources()
        eb = self._emission()
        pil_iw, pil_ia, ein, p_gap = self._pilot_split(q_pil)
        rad_net_out = self._solve_p1(eb, fs["src"], ein)
        gabs = p.eps * self.G / 4.0
        temps = {"ui": self.Tu[..., 0], "iw": self.Ts_iw, "ic": self.T_ic, "ia": self.Tia[..., 0]}
        q_gas, r_c, q_ox, q_fl, q_co, q_sol = self._draught(
            temps, fs["qdot_prev"], np.minimum(fs["fb"], fs["qdot_prev"])
        )
        conv_env = self._step_ui(dt, gabs, q_gas["ui"])
        p_up, up_6a = self._step_up(dt, q_pil)
        removed, conv_iw, mv_eff = self._step_iw(
            dt, gabs, q_gas_iw=q_gas["iw"], q_ox_iw=q_ox["iw"], r_c_iw=r_c["iw"], direct_w=fs["fb_direct"] + pil_iw
        )
        conv_env += conv_iw
        removed_ic, conv_ic = self._step_ic(dt, gabs, q_gas_ic=q_gas["ic"], q_ox_ic=q_ox["ic"], r_c_ic=r_c["ic"])
        conv_env += conv_ic
        removed += removed_ic
        ia = self._step_ia(dt, gabs, q_gas_ia=q_gas["ia"], direct_w=fs["fb_direct_ia"] + pil_ia, a_fl_ia=fs["a_fl_ia"])
        conv_env += ia["conv"]
        removed += ia["removed"]
        L = self.ledger
        L["sources"] += (p_up + p_gap + float(pil_iw.sum()) + float(pil_ia.sum())) * dt
        qdot = mv_eff * p.dh_vol * fs["a_fl"]
        L["combustion_flaming"] += (float(qdot.sum()) + ia["q_wood"]) * dt
        L["combustion_char"] += (
            float((self.A_iw * q_ox["iw"]).sum()) + float((self.A_ic * q_ox["ic"]).sum()) + q_co
        ) * dt
        L["combustion_accelerant"] += ia["q_acc"] * dt
        net = float((qdot + ia["qdot"] - fs["fb"]).sum())
        L["flame_radiative"] += (p.chi_r * net - float(fs["fl_bed"].sum())) * dt
        L["plume_convective"] += ((1 - p.chi_r) * net - q_fl) * dt
        L["open_air_rad"] += (rad_net_out + p_gap) * dt
        L["open_air_conv"] += conv_env * dt
        L["open_air_pilotface"] += up_6a * dt
        L["open_air_draught"] += (q_fl + q_co + q_sol) * dt
        L["removed_with_mass"] += removed
        self.qdot_last = float(fs["qdot_prev"].sum())
        removed2, new_iw, new_ia = self._transfers(frac)
        L["removed_with_mass"] += removed2
        self.fl_iw = (self.A_iw > 0) & ((self.mvol >= p.m_crit) | new_iw)
        self.fl_ia = (self.A_ia > 0) & (self._ia_flames() | new_ia)
        self.flaming = self.fl_iw | self.fl_ia

    def _ia_flames(self) -> np.ndarray:
        """Preregistration §1: the fuel heat-release flux reaches q''_crit (or, the mass-form end, the mass flux)."""
        p = self.p
        if p.crit_form == "mass":
            return (self.mk_ia + self.mw_ia) >= p.m_crit
        return (self.mk_ia * p.dh_k + self.mw_ia * p.dh_vol) >= p.m_crit * p.dh_vol

    def _flame_sources(self) -> dict[str, np.ndarray]:
        """As the bed's, with flaming Ia surfaces adding their release and taking the same feedback law."""
        p = self.p
        a_fl = np.where(self.fl_iw, self.A_iw, 0.0)
        a_fl_ia = np.where(self.fl_ia, self.A_ia, 0.0)
        qdot_prev = self.mvol * p.dh_vol * a_fl + (self.mk_ia * p.dh_k + self.mw_ia * p.dh_vol) * a_fl_ia
        fb_iw = p.q_f * a_fl
        fb = fb_iw + p.q_f * a_fl_ia
        rad_share = 1.0 if p.feedback_mode == "p1" else p.chi_r
        src = rad_share * fb / self.V
        fl_bed = p.chi_r * np.maximum(qdot_prev - fb, 0.0) if p.flame_in_bed else np.zeros_like(fb)
        src = src + fl_bed / self.V
        return {
            "a_fl": a_fl,
            "a_fl_ia": a_fl_ia,
            "qdot_prev": qdot_prev,
            "fb": fb,
            "src": src,
            "fl_bed": fl_bed,
            "fb_direct": (1 - rad_share) * fb_iw,
            "fb_direct_ia": (1 - rad_share) * (p.q_f * a_fl_ia),
        }

    def _pilot_split(self, q_pil: float):
        """Where the pilot lands: Up while unlit, then the cell's Ia, then its Iw; else into the gaps."""
        p = self.p
        n = self.n
        up_live = self.A_up[0] > 0
        to_ia = ~up_live & (self.A_ia[0] > 0)
        to_iw = ~up_live & ~to_ia & (self.A_iw[0] > 0)
        gap = q_pil * self.overlap / self.Af * np.where(up_live | to_ia | to_iw, 1 - p.phi, 1.0)
        pil_iw = np.zeros((n, n, n))
        pil_iw[0] = np.where(to_iw, q_pil * p.phi * self.overlap, 0.0)
        pil_ia = np.zeros((n, n, n))
        pil_ia[0] = np.where(to_ia, q_pil * p.phi * self.overlap, 0.0)
        ein = {k: np.full(c.shape, SIGMA_SB * self.T0**4) for k, c in self.bfaces.items()}
        ein["x-"] = ein["x-"] + gap
        return pil_iw, pil_ia, ein, float((gap * self.Af).sum())

    def _vent(self, area: np.ndarray, dm: np.ndarray) -> None:
        """Vapour from a surface that is not flaming leaves unburnt with its latent and sensible heat."""
        p = self.p
        mass = float((area * dm.sum(-1)).sum())
        if mass > 0:
            self.vented_kg += mass
            self.ledger["vapour_unburnt"] += mass * (p.l_v + p.c_l * (p.t_b - self.T0))

    def _vent_residual(self, da: np.ndarray, liq: np.ndarray, temp: np.ndarray) -> None:
        """Liquid at or below DRY on an area leaving its part: vented, with its sensible heat."""
        mass = float((da * liq.sum(-1)).sum())
        if mass > 0:
            self.vented_kg += mass
            self.ledger["vapour_unburnt"] += float((da * (liq * self.p.c_l * (temp - self.T0)).sum(-1)).sum())

    def _dry(self, t_new: np.ndarray, liq: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        p = self.p
        return evaporate(t_new, liq, self.cap_n, t_b=p.t_b, l_v=p.l_v, c_l=p.c_l, t0=self.T0)

    def _step_ui(self, dt: float, gabs: np.ndarray, q_gas_ui: np.ndarray) -> float:
        p = self.p
        T0 = self.T0
        tu = self.Tu
        f0 = gabs - p.eps * SIGMA_SB * tu[..., 0] ** 4 - q_gas_ui - self.f_env * p.h_env * (tu[..., 0] - T0)
        cond = self.K * (tu[..., :-1] - tu[..., 1:])
        dq = np.zeros_like(tu)
        dq[..., 0] = f0
        dq[..., :-1] -= cond
        dq[..., 1:] += cond
        conv_env = float((self.A_ui * self.f_env * p.h_env * (tu[..., 0] - T0)).sum())
        self.Tu = tu + dt * dq / (self.cap_n + self.Lu * p.c_l)
        if np.any(self.Lu > 0):
            self.Tu, self.Lu, dm = self._dry(self.Tu, self.Lu)
            self._vent(self.A_ui, dm)
        return conv_env

    def _step_up(self, dt: float, q_pil: float) -> tuple[float, float]:
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
        self.Tup = tp + dt * dqp / (self.cap_n + self.Lup * p.c_l)
        if np.any(self.Lup > 0):
            self.Tup, self.Lup, dm = self._dry(self.Tup, self.Lup)
            self._vent(self.A_up, dm)
        return float((self.A_up * q_front).sum()), float((self.A_up * loss_up).sum())

    def _step_ia(self, dt: float, gabs: np.ndarray, *, q_gas_ia, direct_w, a_fl_ia) -> dict:
        """Ia: profiled like Ui, wet nodes dried at T_b, 6c on a dry surface node above T_p.
        Vapour from a surface that flamed this substep burns; otherwise it is vented."""
        p = self.p
        T0 = self.T0
        out: dict = {"removed": 0.0, "conv": 0.0, "q_wood": 0.0, "q_acc": 0.0, "qdot": np.zeros_like(self.A_ia)}
        live = self.A_ia > 0
        if not np.any(live):
            return out
        t = self.Tia
        ts = t[..., 0]
        direct = np.where(live, direct_w / np.maximum(self.A_ia, 1e-30), 0.0)
        f0 = gabs - p.eps * SIGMA_SB * ts**4 - q_gas_ia - self.f_env * p.h_env * (ts - T0) + direct
        cond = self.K * (t[..., :-1] - t[..., 1:])
        dq = np.zeros_like(t)
        dq[..., 0] = f0
        dq[..., :-1] -= cond
        dq[..., 1:] += cond
        t_new, liq, dm = self._dry(t + dt * dq / (self.cap_n + self.Lia * p.c_l), self.Lia)
        t_new, mv_eff, excess = self._ia_pyrolysis(t_new, liq, dt)
        mk = dm.sum(-1) / dt
        burns = a_fl_ia > 0
        m_cell = self.A_ia * dm.sum(-1)
        h_vap = p.l_v + p.c_l * (p.t_b - T0)
        self.burnt_kg += float(np.where(burns, m_cell, 0.0).sum())
        self.vented_kg += float(np.where(burns, 0.0, m_cell).sum())
        self.ledger["vapour_unburnt"] += float(np.where(burns, 0.0, m_cell).sum()) * h_vap
        out["removed"] = float((self.A_ia * excess).sum()) + float(np.where(burns, m_cell, 0.0).sum()) * h_vap
        out["conv"] = float((self.A_ia * self.f_env * p.h_env * (ts - T0)).sum())
        out["q_acc"] = float((mk * p.dh_k * a_fl_ia).sum())
        out["q_wood"] = float((mv_eff * p.dh_vol * a_fl_ia).sum())
        out["qdot"] = (mk * p.dh_k + mv_eff * p.dh_vol) * a_fl_ia
        self.Tia = np.where(live[..., None], t_new, T0)
        self.Lia = np.where(live[..., None], liq, 0.0)
        self.mk_ia = np.where(live, mk, 0.0)
        self.mw_ia = np.where(live, mv_eff, 0.0)
        return out

    def _ia_pyrolysis(self, t_new: np.ndarray, liq: np.ndarray, dt: float):
        """6c on Ia's surface node once it is dry: pinned at T_p, the excess gasifies wood at L_g.
        Returns (temperatures, volatile flux kg/m^2 s, gasification enthalpy J/m^2)."""
        p = self.p
        s0 = t_new[..., 0]
        can = (self.A_ia > 0) & (liq[..., 0] <= 0) & (self.w_ia > 0) & (s0 > p.t_p)
        excess = np.where(can, self.cap_n[0] * (s0 - p.t_p), 0.0)
        t_new = t_new.copy()
        t_new[..., 0] = np.where(can, p.t_p, s0)
        pyr = excess / p.l_g / (1 - p.chi_char)
        dw = np.minimum(self.w_ia, pyr)
        self.w_ia = self.w_ia - dw
        self.c_ia = self.c_ia + p.chi_char * dw
        return t_new, dw * (1 - p.chi_char) / dt, excess

    # ------------------------------------------------------------ transfers
    def _transfers(self, frac: float):
        nb = self._flame_neighbourhood()
        new_iw = np.zeros(self.A_iw.shape, dtype=bool)
        new_ia = np.zeros(self.A_iw.shape, dtype=bool)
        self._ignite_up(frac, nb, new_iw, new_ia)
        self._ignite_ui(nb, new_iw, new_ia)
        self._ia_to_iw(new_iw)
        removed = self._burn_down()
        return removed, new_iw, new_ia

    def _ignite_up(self, frac: float, nb: np.ndarray, new_iw: np.ndarray, new_ia: np.ndarray) -> None:
        """Up ignites with the pilot on or a flame adjacent: wet at T_b into Ia, dry at T_p into Iw (the bed's rule)."""
        p = self.p
        wet = self.Lup.sum(-1) > DRY
        ign = (self.A_up > 0) & (self.Tup[..., 0] >= np.where(wet, p.t_b, p.t_p)) & ((frac > 0) | nb)
        dry_ign = ign & ~wet
        if np.any(dry_ign):
            da = np.where(dry_ign, self.A_up, 0.0)
            e_slab = (self.Tup - self.T0) @ self.cap_n - self.cap_n[0] * (p.t_p - self.T0)
            self._vent_residual(da, self.Lup, self.Tup)
            self._merge_iw(da, p.w0, 0.0, e_slab)
            self.A_up = self.A_up - da
            new_iw |= dry_ign
            self.lit_cum += da
            self.wood_cum += da
        wet_ign = ign & wet
        if np.any(wet_ign):
            da = np.where(wet_ign, self.A_up, 0.0)
            self._merge_ia(da, self.Tup, self.Lup, p.w0)
            self.A_up = self.A_up - da
            self.Lup = np.where(wet_ign[..., None], 0.0, self.Lup)
            new_ia |= wet_ign
            self.lit_cum += da
            self.up_to_ia += da

    def _ignite_ui(self, nb: np.ndarray, new_iw: np.ndarray, new_ia: np.ndarray) -> None:
        """Ui ignites by the reconstructed sub-cell skin, at T_b where wet (into Ia), at T_p where dry (into Iw)."""
        p = self.p
        wet = self.Lu.sum(-1) > DRY
        e_slab = (self.Tu - self.T0) @ self.cap_n - self.cap_n[0] * (p.t_p - self.T0)
        frac_hot = self._hot_fraction_at(np.where(wet, p.t_b, p.t_p))
        target = frac_hot * self.A_ui0
        already = self.A_ui0 - self.A_ui
        da = np.where(nb, np.clip(target - already, 0.0, self.A_ui), 0.0)
        if not np.any(da > 0):
            return
        da_dry = np.where(wet, 0.0, da)
        da_wet = np.where(wet, da, 0.0)
        if np.any(da_dry > 0):
            self._vent_residual(da_dry, self.Lu, self.Tu)
            self._merge_iw(da_dry, p.w0, 0.0, e_slab)
            new_iw |= da_dry > 0
            self.wood_cum += da_dry
        if np.any(da_wet > 0):
            self._merge_ia(da_wet, self.Tu, self.Lu, p.w0)
            new_ia |= da_wet > 0
        self.A_ui = self.A_ui - da
        self.lit_cum += da

    def _ia_to_iw(self, new_iw: np.ndarray) -> None:
        """Ia holding no liquid, its surface pinned at T_p under 6c, becomes Iw with its slab energy."""
        p = self.p
        done = (self.A_ia > 0) & (self.Lia.sum(-1) <= DRY) & (self.Tia[..., 0] >= p.t_p)
        if not np.any(done):
            return
        da = np.where(done, self.A_ia, 0.0)
        self._vent_residual(da, self.Lia, self.Tia)
        e_slab = (self.Tia - self.T0) @ self.cap_n - self.cap_n[0] * (p.t_p - self.T0)
        self._merge_iw(da, np.where(done, self.w_ia, 0.0), np.where(done, self.c_ia, 0.0), e_slab)
        flamed = done & self.fl_ia
        new_iw |= flamed
        self.wood_cum += np.where(flamed, da, 0.0)
        self.wood_unfl += np.where(done & ~self.fl_ia, da, 0.0)
        keep = ~done
        self.A_ia = np.where(keep, self.A_ia, 0.0)
        self.Tia = np.where(keep[..., None], self.Tia, self.T0)
        self.Lia = np.where(keep[..., None], self.Lia, 0.0)
        for name in ("w_ia", "c_ia", "mk_ia", "mw_ia"):
            setattr(self, name, np.where(keep, getattr(self, name), 0.0))
        self.fl_ia = self.fl_ia & keep

    def _burn_down(self) -> float:
        """The bed's Iw -> Ic and Ic burn-out moves, unchanged (model.py::Bed._transfers)."""
        T0 = self.T0
        removed = 0.0
        done = (self.A_iw > 0) & (self.w_iw <= 1e-9)
        if np.any(done):
            removed += self._iw_to_ic(done)
        gone = (self.A_ic > 0) & (self.c_ic <= 1e-4)
        if np.any(gone):
            removed += float((np.where(gone, self.A_ic * self._cic() * (self.T_ic - T0), 0.0)).sum())
            self.A_ic = np.where(gone, 0.0, self.A_ic)
            self.c_ic = np.where(gone, 0.0, self.c_ic)
            self.T_ic = np.where(gone, T0, self.T_ic)
        return removed

    def _merge_ia(self, da: np.ndarray, t_prof: np.ndarray, l_prof: np.ndarray, w_add: float) -> None:
        """Add area da (profile t_prof, l_prof) to the cell's Ia, conserving energy and liquid."""
        c_l = self.p.c_l
        T0 = self.T0
        a_new = self.A_ia + da
        safe = np.maximum(a_new, 1e-30)[..., None]
        u = self.A_ia[..., None] * (self.cap_n + self.Lia * c_l) * (self.Tia - T0) + da[..., None] * (
            self.cap_n + l_prof * c_l
        ) * (t_prof - T0)
        liq = (self.A_ia[..., None] * self.Lia + da[..., None] * l_prof) / safe
        live = a_new[..., None] > 0
        self.Tia = np.where(live, T0 + u / (safe * (self.cap_n + liq * c_l)), T0)
        self.Lia = np.where(live, liq, 0.0)
        self.w_ia = np.where(a_new > 0, (self.A_ia * self.w_ia + da * w_add) / safe[..., 0], 0.0)
        self.c_ia = np.where(a_new > 0, (self.A_ia * self.c_ia) / safe[..., 0], 0.0)
        self.A_ia = a_new

    def _hot_fraction_at(self, thresh: np.ndarray) -> np.ndarray:
        """model.py::Bed._hot_fraction with a per-cell threshold (T_b where wet, T_p where dry)."""
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
        frac = (tu >= thresh).astype(float)
        reach = 0.5 * self.dx * (np.abs(grads[0]) + np.abs(grads[1]) + np.abs(grads[2]))
        cand = (self.A_ui > 0) & (tu + reach >= thresh) & (tu - reach < thresh)
        if np.any(cand):
            g0, g1, g2 = grads[0][cand], grads[1][cand], grads[2][cand]
            off = g0[:, None] * ox.ravel() + g1[:, None] * oy.ravel() + g2[:, None] * oz.ravel()
            frac[cand] = ((tu[cand][:, None] + off) >= thresh[cand][:, None]).mean(axis=-1)
        return frac

    # ---------------------------------------------------------- observables
    def wood_involved(self) -> float:
        """Area whose surface has reached T_p while flaming: entries into Iw while flaming, plus flaming Ia whose
        dry surface node is pyrolysing at T_p."""
        pyr = (self.A_ia > 0) & self.fl_ia & (self.Tia[..., 0] >= self.p.t_p)
        return float(self.wood_cum.sum()) + float(np.where(pyr, self.A_ia, 0.0).sum())
