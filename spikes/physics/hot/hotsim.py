"""Run one hot-surface scenario; record the preregistered observables and the ledger every physics step (spike).

The loop, the ledger rows, the digests and the quiet rule are wetsim's; this adds the records the hot-surface
preregistration (§3) reports: T_c on flaming Iw, the gas leaving flaming cells, the hottest unlit skin beside a
flame, and the sight-line glow area every GLOW_EVERY steps.
"""

from __future__ import annotations

import hashlib
import math

import numpy as np
import wetsim
from hot_constants import HotParams
from hotbed import HotBed

GLOW_C = 625.0
GLOW_AREA = 0.08
GLOW_EVERY = 10  # physics steps (5 s): the envelope layer is costly; disclosed in results.md
EXTRA_KEYS = (
    "tc_fl_mean",
    "tc_fl_max",
    "tc_fl_env",
    "tc_fl_int",
    "gas_exit_mean",
    "gas_exit_max",
    "hot_unlit_nb",
    "glow_area",
)


def _tc_stats(bed: HotBed) -> tuple[float, float, float, float]:
    """Area-weighted T_c (C) of flaming Iw: all, max, cells on the envelope, interior cells."""
    a = np.where(bed.fl_iw, bed.A_iw, 0.0)
    tot = float(a.sum())
    if tot <= 0:
        return (math.nan,) * 4
    t = bed.Ts_iw - 273.15
    env = bed.n_env > 0
    ae, ai = float(a[env].sum()), float(a[~env].sum())
    return (
        float((a * t).sum() / tot),
        float(t[a > 0].max()),
        float((a * t)[env].sum() / ae) if ae > 0 else math.nan,
        float((a * t)[~env].sum() / ai) if ai > 0 else math.nan,
    )


def record_extra(bed: HotBed, rec: dict[str, list], step: int) -> None:
    for key, v in zip(EXTRA_KEYS[:4], _tc_stats(bed), strict=True):
        rec[key].append(v)
    rec["gas_exit_mean"].append(bed.gas_exit[0] - 273.15)
    rec["gas_exit_max"].append(bed.gas_exit[1] - 273.15)
    cand = bed._flame_neighbourhood() & (bed.A_ui > 0)
    rec["hot_unlit_nb"].append(float(bed.Tu[..., 0][cand].max()) - 273.15 if cand.any() else math.nan)
    if step % GLOW_EVERY == GLOW_EVERY - 1:
        lay = bed.envelope_layer()
        rec["glow_area"].append(sum(bed.sample_area(v, GLOW_C + 273.15) for v in lay.values()))
    else:
        rec["glow_area"].append(math.nan)


def hash_hot(h, bed: HotBed) -> None:
    for a in (bed.Tu, bed.T_ic, bed.G, bed.c_ic, bed.Lu, bed.Tia, bed.Lia, bed.A_ia, bed.A_iw, bed.Ts_iw, bed.c_iw):
        h.update(np.ascontiguousarray(a).tobytes())


def run(p: HotParams, dx: float, pilot_ticks: int, *, t_end: float | None = None, extras: bool = True) -> dict:
    bed = HotBed(p, dx, pilot_ticks)
    t_end = p.cap_s if t_end is None else t_end
    keys = wetsim.RECORD_KEYS + (EXTRA_KEYS if extras else ())
    rec: dict[str, list] = {k: [] for k in keys}
    ledger_hist: list[dict[str, float]] = []
    hb, hw, hh = hashlib.sha256(), hashlib.sha256(), hashlib.sha256()
    gone_after = None
    for step in range(round(t_end / p.dt_phys)):
        bed.physics_step()
        ledger_hist.append(wetsim.ledger_rows(bed))
        wetsim.record(bed, rec)
        if extras:
            record_extra(bed, rec, step)
        wetsim.hash_bed(hb, bed)
        wetsim.hash_wet(hw, bed)
        hash_hot(hh, bed)
        if wetsim.is_quiet(bed) and bed.t > p.dt_phys * 10:
            break
        if bed.fuel_mass() < 0.05 * bed.m0:
            gone_after = step if gone_after is None else gone_after
            if step - gone_after > 600:
                break
    out: dict = {k: np.array(v, dtype=float) for k, v in rec.items()}
    out.update(
        ledger=ledger_hist,
        m0=bed.m0,
        wood0=bed.wood0,
        liq0=bed.liq0,
        lit0=bed.lit0,
        area=float(bed.A_ui0.sum() + bed.A_up0.sum()),  # A_ui0 still holds the area lit at t = 0
        disc=float(bed.A_up0.sum()),
        digest_bed=hb.hexdigest(),
        digest_wet=hw.hexdigest(),
        digest=hh.hexdigest(),
        pilot_end=pilot_ticks * 0.1,
        n=bed.n,
    )
    return out


def first_time(t: np.ndarray, cond: np.ndarray) -> float:
    idx = np.nonzero(cond)[0]
    return float(t[idx[0]]) if idx.size else math.nan


def criteria(r: dict) -> dict:
    """B1, B2, C (S, K) and C_F (F) exactly as preregistered §3; lambda counts area lit at t = 0 (F, B)."""
    t = r["t"]
    pe = r["pilot_end"]
    soaked = r["liq0"] > 0
    o: dict = {}
    lam = (r["lit"] + r["lit0"]) / r["area"]
    lam_w = np.maximum.accumulate(r["wood_inv"] + r["lit0"]) / r["area"]
    o["lambda_max"] = float(lam.max())
    o["spread_class"] = "spread" if o["lambda_max"] >= 0.90 else "partial" if o["lambda_max"] >= 0.10 else "none"
    o["B1"] = o["lambda_max"] >= 0.90
    o["lambda_w_max"] = float(lam_w.max())
    o["t_L95"] = first_time(t, r["liquid"] <= 0.05 * r["liq0"]) if soaked else math.nan
    if soaked:
        i95 = np.searchsorted(t, o["t_L95"]) if math.isfinite(o["t_L95"]) else t.size - 1
        o["lambda_w_tL95"] = float(lam_w[min(i95, t.size - 1)])
        o["B2"] = math.isfinite(o["t_L95"]) and o["lambda_w_tL95"] >= 0.90
    else:
        o["B2"] = o["lambda_w_max"] >= 0.90
    o["t_B"] = first_time(t, lam_w >= 0.90)
    o["t_out"], i_out = wetsim.flame_out(t, r["a_flaming"])
    o["wood_at_out_frac"] = float(r["wood"][i_out] / r["wood0"]) if i_out >= 0 else float(r["wood"][-1] / r["wood0"])
    after = math.isfinite(o["t_out"]) and o["t_out"] > pe
    if soaked:
        after = after and math.isfinite(o["t_L95"]) and o["t_out"] > o["t_L95"]
    o["C"] = bool(after and o["wood_at_out_frac"] <= 0.05)
    o["C_F"] = bool(math.isfinite(o["t_out"]) and o["wood_at_out_frac"] <= 0.05)
    o["t_ignite"] = first_time(t, r["a_flaming"] >= 0.1)
    o["t_A"] = first_time(t, (r["a_disc"] >= 0.9 * r["disc"]) & (t <= pe)) if soaked else math.nan
    return o


def reported(r: dict, crit: dict) -> dict:
    """The §3 reported quantities (not graded)."""
    t = r["t"]
    last = r["ledger"][-1]
    o: dict = {}
    o["E_accelerant_MJ"] = last["combustion_accelerant"] / 1e6
    o["E_wood_flaming_MJ"] = last["combustion_flaming"] / 1e6
    o["E_char_MJ"] = last["combustion_char"] / 1e6
    o["peak_qdot_kW"] = float(r["qdot"].max()) / 1e3
    o["t_peak_qdot"] = float(t[int(np.argmax(r["qdot"]))])
    o["peak_flaming_area"] = float(r["a_flaming"].max())
    end = crit["t_out"] if math.isfinite(crit["t_out"]) else t[-1] + 1.0
    fl = (r["a_flaming"] > 0) & (t < end)
    over = (r["o2_demand"] > r["o2_supply"]) & fl
    o["o2_over_frac_flaming"] = float(over.sum() / max(fl.sum(), 1))
    o["o2_unverified"] = bool(crit["B1"] and o["o2_over_frac_flaming"] > 0.10)
    o["burnt_frac"] = float(r["burnt"][-1] / r["liq0"]) if r["liq0"] > 0 else math.nan
    o["vented_frac"] = float(r["vented"][-1] / r["liq0"]) if r["liq0"] > 0 else math.nan
    o["fuel_end_frac"] = float(r["fuel"][-1] / r["m0"])
    em = r["ember_max"]
    o["ember_peak_c"] = float(np.nanmax(em)) if np.any(np.isfinite(em)) else math.nan
    if "tc_fl_mean" in r:
        for key in ("tc_fl_mean", "tc_fl_env", "tc_fl_int", "gas_exit_mean"):
            v = r[key]
            o[key + "_median"] = float(np.nanmedian(v)) if np.any(np.isfinite(v)) else math.nan
        for key in ("tc_fl_max", "gas_exit_max"):
            v = r[key]
            o[key + "_peak"] = float(np.nanmax(v)) if np.any(np.isfinite(v)) else math.nan
        o["probe"] = {
            f"{s}": (float(r["hot_unlit_nb"][i]) if (i := int(np.searchsorted(t, s))) < t.size else None)
            for s in (180, 360, 480, 600)
        }
        g = r["glow_area"]
        gt = t[np.isfinite(g)]
        gv = g[np.isfinite(g)]
        on = gv >= GLOW_AREA
        o["t_glow"] = float(gt[on][0]) if on.any() else math.nan
        best = cur = 0
        for c in on:
            cur = cur + 1 if c else 0
            best = max(best, cur)
        o["glow_longest_s"] = best * GLOW_EVERY * 0.5
        o["glow_area_max"] = float(gv.max()) if gv.size else math.nan
    # lambda(t) at 60 s intervals, for the record
    lam = (r["lit"] + r["lit0"]) / r["area"]
    o["lambda_t"] = {f"{s}": float(lam[min(int(np.searchsorted(t, s)), t.size - 1)]) for s in range(0, 5401, 300)}
    return o
