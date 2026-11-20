"""The four laws, each ``stable_dt(state) -> float`` and ``step(state, dt, ledger) -> None``.

Per bed cell the state is two-node: the skin (Ts, a 1 mm layer over the cell's fuel surface, tile 6b) and the bulk
(T: slat cores plus pore air). Ledger lines follow tile §5.4 (a diagnostic here; Q4 owns closure). Kernels are
elementwise numpy, slicing, fancy indexing, ``np.bincount``, pairwise ``np.sum`` and one SuperLU triangular solve:
no BLAS (``np.dot``/``matmul``/``einsum``/``@``), no ``np.power``.
"""

from __future__ import annotations

import numpy as np
from model import (
    SIGMA_SB,
    STABILITY_SAFETY,
    T_AMB,
    TICK_S,
    C,
    State,
    bed_capacity,
    cell_k,
    cell_rhoc,
    fourth,
    ignition_time_s,
    k_rad,
    skin_capacity,
)

Ledger = dict[str, float]


def _add(ledger: Ledger, line: str, joules: float) -> None:
    ledger[line] = ledger.get(line, 0.0) + joules


def _faces(k: np.ndarray):
    for axis in range(3):
        lo = [slice(None)] * 3
        hi = [slice(None)] * 3
        lo[axis] = slice(0, -1)
        hi[axis] = slice(1, None)
        a, b = k[tuple(lo)], k[tuple(hi)]
        yield tuple(lo), tuple(hi), 2.0 * a * b / (a + b)  # harmonic mean, as heat.py; k > 0 everywhere


class Conduction:
    """Diffusive transport, explicit: (1) the bulk field, heat.py's finite-volume scheme (harmonic-mean faces,
    insulated boundary); (2) re-radiation between the skins of neighbouring bed cells, Rosseland conductivity
    evaluated at the face's mean skin temperature (nonlinear: the bound tightens as the bed heats)."""

    name = "conduction"

    def stable_dt(self, s: State) -> float:
        k = cell_k(s)
        total = np.zeros_like(k)
        for lo, hi, kf in _faces(k):
            total[lo] += kf
            total[hi] += kf
        bulk = float(np.min(cell_rhoc(s) * s.dx**2 / total))
        g = self._skin_conductance(s)
        nb = s.Ts.size
        i, j = s.geo.skin_nbrs
        gsum = np.bincount(i, weights=g, minlength=nb) + np.bincount(j, weights=g, minlength=nb)
        cs = skin_capacity(s)
        act = gsum > 0
        skin = float(np.min(cs[act] / gsum[act])) if np.any(act) else np.inf
        return STABILITY_SAFETY * min(bulk, skin)

    @staticmethod
    def _skin_conductance(s: State) -> np.ndarray:
        """W/K across each interior bed face pair (face area dx², distance dx); zero unless both skins exist."""
        i, j = s.geo.skin_nbrs
        active = (s.mw + s.mc) > 0.0
        Tm = 0.5 * (s.Ts[i] + s.Ts[j])
        return np.where(active[i] & active[j], k_rad(Tm) * s.dx, 0.0)

    def step(self, s: State, dt: float, ledger: Ledger) -> None:
        k = cell_k(s)
        flux = np.zeros_like(k)
        for lo, hi, kf in _faces(k):
            q = kf * (s.T[hi] - s.T[lo])
            flux[lo] += q
            flux[hi] -= q
        g = self._skin_conductance(s)
        i, j = s.geo.skin_nbrs
        q = g * (s.Ts[j] - s.Ts[i]) * dt  # J from j into i
        nb = s.Ts.size
        dq = np.bincount(i, weights=q, minlength=nb) - np.bincount(j, weights=q, minlength=nb)
        cs = skin_capacity(s)
        s.Ts = np.where(cs > 0, s.Ts + dq / np.where(cs > 0, cs, 1.0), s.Ts)
        s.T += dt * flux / (cell_rhoc(s) * s.dx**2)


class Skin:
    """6b: each bed cell's skin exchanges with its slat cores through the conduction resistance of a quarter slat
    (k_wood / (δ/4) per m², a two-node slat), and the pilot's power lands on the skins behind the disc (tile §3.2)."""

    name = "skin"

    @staticmethod
    def _G(s: State) -> float:
        return C("k_wood") / (C("slat") / 4.0) * C("sigma_v") * s.geo.V  # W/K per cell, constant

    def stable_dt(self, s: State) -> float:
        cs = skin_capacity(s)
        act = cs > 0
        if not np.any(act):
            return np.inf
        rate = self._G(s) * (1.0 / cs[act] + 1.0 / bed_capacity(s)[act])  # monotone when rate·dt ≤ 1
        return float(STABILITY_SAFETY / np.max(rate))

    def step(self, s: State, dt: float, ledger: Ledger) -> None:
        cs = skin_capacity(s)
        act = cs > 0
        idx = s.geo.bed_flat
        Tb = s.T.flat[idx]
        Q = np.where(act, self._G(s) * (Tb - s.Ts) * dt, 0.0)  # J into the skin
        pilot = np.where(act, s.pilot_w * s.geo.pilot_frac * dt, 0.0)
        s.Ts = np.where(act, s.Ts + (Q + pilot) / np.where(act, cs, 1.0), Tb)
        s.T.flat[idx] = Tb - Q / bed_capacity(s)
        _add(ledger, "sources", float(np.sum(pilot)))


class PorousBed:
    """6c + 6d, the flux-threshold sources.

    Ignition (tile §5.2 6b, area overlap with a critical heat flux): a cell whose west face is at least half under
    the disc lights once the pilot (flux >= CHF) has run the thermally thick closed-form ignition time; a cell whose
    fuel receives a flame flux >= CHF lights; any cell whose skin reaches T_p with wood left lights too. The flame's
    feedback is tile §5.4's identity, q''_f x A_burning x dt, over the lit cells with wood; it is spread over the bed
    by the P1 solve (extinction sigma_v/4, so over ell, in metres) and lands on skins. Pyrolysis is a projection: a
    skin above T_p with wood behind it is put back to T_p and the excess gasifies volatiles at L_g (so
    m'' = q''_net / L_g, tile §5.2). Volatiles release ΔH_c; release minus the feedback is the plume.
    Char forms at χ per kg of wood and oxidises at the diffusion-limited 6d rate once a cell's wood is gone and its
    skin is >= T_p (a threshold this prototype assumes), heating the skin."""

    name = "bed"

    def stable_dt(self, s: State) -> float:
        # The projection is unconditionally stable and no source depends on temperature: no bound.
        return np.inf

    def step(self, s: State, dt: float, ledger: Ledger) -> None:
        self._ignite(s)
        flame = self._flame(s, dt, ledger)
        release = self._pyrolyse(s, ledger)
        _add(ledger, "plume_convective", release - flame)  # volatile release not fed back (signed per substep)
        self._oxidise_char(s, dt, ledger)

    @staticmethod
    def _ignite(s: State) -> None:
        q_pilot = C("pilot_power") / (np.pi * C("pilot_radius") ** 2)
        piloted = (q_pilot >= C("chf")) and (s.pilot_ticks * TICK_S >= ignition_time_s())
        new = (s.Ts >= C("T_p")) | ((s.geo.pilot_cover >= 0.5) & piloted)
        s.lit = s.lit | (new & (s.mw > 0.0))

    @staticmethod
    def _flame(s: State, dt: float, ledger: Ledger) -> float:
        src = np.where(s.lit & (s.mw > 0.0), C("q_f") * C("sigma_v") * s.geo.V * dt, 0.0)  # J
        total = float(np.sum(src))
        if total <= 0.0:
            return 0.0
        cs = skin_capacity(s)
        act = cs > 0  # only fuel absorbs: an emptied cell transmits (the factor keeps the bed's full extinction)
        absorbed = np.where(act, s.geo.p1_absorb * s.geo.p1.solve(src), 0.0)
        deposit = total * absorbed / float(np.sum(absorbed))
        s.Ts = np.where(act, s.Ts + deposit / np.where(act, cs, 1.0), s.Ts)
        # tile §5.2 6b: ignition by a critical heat flux, here the flame's flux on the cell's fuel surface
        s.lit = s.lit | (act & (s.mw > 0.0) & (deposit >= C("chf") * C("sigma_v") * s.geo.V * dt))
        _add(ledger, "flame_deposit", total)
        return total

    @staticmethod
    def _pyrolyse(s: State, ledger: Ledger) -> float:
        cs = skin_capacity(s)
        chi, Lg, Tp = C("chi_char"), C("L_g"), C("T_p")
        hot = (s.mw > 0.0) & (s.Ts > Tp)
        excess = np.where(hot, (s.Ts - Tp) * cs, 0.0)
        vol_avail = s.mw * (1.0 - chi)
        vol = np.minimum(excess / Lg, vol_avail)  # kg of volatiles
        all_gone = hot & (excess / Lg >= vol_avail)
        wood_used = np.where(all_gone, s.mw, vol / (1.0 - chi))
        s.Ts = np.where(hot, s.Ts - vol * Lg / np.where(cs > 0, cs, 1.0), s.Ts)
        Tb = s.T.flat[s.geo.bed_flat]
        cb_before = bed_capacity(s)
        s.mw = np.where(all_gone, 0.0, s.mw - wood_used)
        s.mc = s.mc + wood_used * chi
        removed = (cb_before - bed_capacity(s)) * (Tb - T_AMB)  # mass leaves the bulk at the bulk temperature
        s.burning = vol
        release = float(np.sum(vol * C("dHc")))
        _add(ledger, "combustion", release)
        _add(ledger, "gasification", float(np.sum(vol * Lg)))
        _add(ledger, "removed_with_mass", float(np.sum(removed)))
        return release

    @staticmethod
    def _oxidise_char(s: State, dt: float, ledger: Ledger) -> None:
        lit = (s.mw == 0.0) & (s.mc > 0.0) & (s.Ts >= C("T_p"))
        want = C("m_char_flux") * C("sigma_v") * s.geo.V * dt
        burn = np.where(lit, np.minimum(want, s.mc), 0.0)
        cs_before = skin_capacity(s)
        Tb = s.T.flat[s.geo.bed_flat]
        cb_before = bed_capacity(s)
        s.mc = np.where(lit & (want >= s.mc), 0.0, s.mc - burn)
        heat = burn * C("dH_char")
        Ts_new = np.where(cs_before > 0, s.Ts + heat / np.where(cs_before > 0, cs_before, 1.0), s.Ts)
        gone = (cs_before > 0) & (skin_capacity(s) == 0)  # fuel just ran out: the skin's heat goes with the mass
        removed = np.where(gone, cs_before * (Ts_new - T_AMB), 0.0) + (cb_before - bed_capacity(s)) * (Tb - T_AMB)
        s.Ts = np.where(gone, Tb, Ts_new)
        _add(ledger, "combustion", float(np.sum(heat)))
        _add(ledger, "removed_with_mass", float(np.sum(removed)))


class OpenAirLoss:
    """6a: the envelope loses h_c(Ts-Ta) + ε sigma (Ts⁴-Ta⁴) per m², spread over the ell-deep layer's skins."""

    name = "open_air"

    @staticmethod
    def _q(Ts: np.ndarray) -> np.ndarray:
        return C("h_c") * (Ts - T_AMB) + C("eps") * SIGMA_SB * (fourth(Ts) - T_AMB**4)

    def stable_dt(self, s: State) -> float:
        cs = skin_capacity(s)
        act = (cs > 0) & (s.geo.env_w > 0)
        if not np.any(act):
            return np.inf
        Ts = s.Ts[act]
        dq = C("h_c") + 4.0 * C("eps") * SIGMA_SB * Ts * Ts * Ts
        rate = dq * 1.8 * s.geo.env_w[act] / cs[act]
        return float(STABILITY_SAFETY / np.max(rate))

    def step(self, s: State, dt: float, ledger: Ledger) -> None:
        cs = skin_capacity(s)
        act = cs > 0
        loss = np.where(act, self._q(s.Ts) * 1.8 * s.geo.env_w * dt, 0.0)
        s.Ts = np.where(act, s.Ts - loss / np.where(act, cs, 1.0), s.Ts)
        _add(ledger, "open_air_loss", float(np.sum(loss)))


def stored_energy(s: State) -> float:
    bulk = float(np.sum(cell_rhoc(s) * (s.T - T_AMB))) * s.geo.V
    return bulk + float(np.sum(skin_capacity(s) * (s.Ts - T_AMB)))


FORWARD = (Conduction(), Skin(), PorousBed(), OpenAirLoss())
