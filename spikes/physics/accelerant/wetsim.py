"""Run one soaked-bed scenario; record the preregistered observables and the ledger every physics step (spike)."""

from __future__ import annotations

import hashlib
import math

import numpy as np
from acc_constants import AccParams
from wetbed import ACC_IN, ACC_OUT, WetBed

CRACK_AREA = 0.08
STORE = ("d_cells", "d_skins")
RECORD_KEYS = (
    "t",
    "a_flaming",
    "a_flaming_iw",
    "a_disc",
    "lit",
    "wood_inv",
    "wood_unfl",
    "liquid",
    "burnt",
    "vented",
    "wood",
    "fuel",
    "crack_cell",
    "qdot",
    "o2_demand",
    "o2_supply",
    "ember_max",
    "ember_mean",
    "ember_area",
)


def ledger_rows(bed: WetBed) -> dict[str, float]:
    cells, skins = bed.energies()
    row = dict(bed.ledger)
    row["d_cells"] = cells - bed.E0_cells
    row["d_skins"] = skins - bed.E0_skins
    row["d_liquid"] = bed._liquid_heat()  # informational: the liquid's sensible heat, already inside d_cells
    return row


def residual(row: dict[str, float], drop: str | None = None) -> tuple[float, float]:
    """(|in - d_stored - out|, cumulative release), with one line optionally deleted."""
    ins = sum(row[k] for k in ACC_IN if k != drop)
    outs = sum(row[k] for k in ACC_OUT if k != drop)
    store = sum(row[k] for k in STORE if k != drop) - (row.get("d_liquid", 0.0) if drop == "liquid_sensible" else 0.0)
    released = sum(row[k] for k in ACC_IN)
    return abs(ins - store - outs), released


def record(bed: WetBed, rec: dict[str, list]) -> None:
    a_ic = bed.A_ic
    ea = float(a_ic.sum())
    cr = bed.crack_patches()
    rec["t"].append(bed.t)
    rec["a_flaming"].append(
        float(np.where(bed.fl_iw, bed.A_iw, 0.0).sum()) + float(np.where(bed.fl_ia, bed.A_ia, 0.0).sum())
    )
    rec["a_flaming_iw"].append(float(np.where(bed.fl_iw, bed.A_iw, 0.0).sum()))
    rec["a_disc"].append(float(np.where(bed.fl_ia, bed.up_to_ia, 0.0).sum()))
    rec["lit"].append(float(bed.lit_cum.sum()))
    rec["wood_inv"].append(bed.wood_involved())
    rec["wood_unfl"].append(float(bed.wood_unfl.sum()))
    rec["liquid"].append(bed.liquid_mass())
    rec["burnt"].append(bed.burnt_kg)
    rec["vented"].append(bed.vented_kg)
    rec["wood"].append(bed.wood_mass())
    rec["fuel"].append(bed.fuel_mass())
    rec["crack_cell"].append(sum(float((v >= 0.1).sum()) * bed.Af for v in cr.values()))
    rec["qdot"].append(bed.qdot_last)
    rec["o2_demand"].append(bed.qdot_last / bed.p.huggett)
    rec["o2_supply"].append(getattr(bed, "o2_supply", 0.0))
    rec["ember_max"].append(float(np.where(a_ic > 0, bed.T_ic, 0).max()) - 273.15 if ea > 0 else math.nan)
    rec["ember_mean"].append(float((a_ic * bed.T_ic).sum() / ea) - 273.15 if ea > 0 else math.nan)
    rec["ember_area"].append(ea)


def hash_bed(h, bed: WetBed) -> None:
    """The bed spike's digest (sim.py::hash_state): E4(ii) compares it with bed's committed runs."""
    for a in (bed.Tu, bed.T_ic, bed.G, bed.c_ic):
        h.update(np.ascontiguousarray(a).tobytes())


def hash_wet(h, bed: WetBed) -> None:
    for a in (bed.Tu, bed.T_ic, bed.G, bed.c_ic, bed.Lu, bed.Lup, bed.Tia, bed.Lia, bed.A_ia, bed.A_iw):
        h.update(np.ascontiguousarray(a).tobytes())


def is_quiet(bed: WetBed) -> bool:
    """Pilot off, no flame, every surface within 30 K of ambient (the bed's rule, Ia included)."""
    hot = max(float(bed.Tu[..., 0].max()), float(bed.Ts_iw.max()), float(bed.T_ic.max()), float(bed.Tia.max()))
    return bed.pilot_fraction() == 0 and not bed.flaming.any() and hot < bed.T0 + 30.0


def run(p: AccParams, dx: float, pilot_ticks: int, *, t_end: float | None = None) -> dict:
    bed = WetBed(p, dx, pilot_ticks)
    t_end = p.cap_s if t_end is None else t_end
    rec: dict[str, list] = {k: [] for k in RECORD_KEYS}
    ledger_hist: list[dict[str, float]] = []
    hb, hw = hashlib.sha256(), hashlib.sha256()
    gone_after = None
    for step in range(round(t_end / p.dt_phys)):
        bed.physics_step()
        ledger_hist.append(ledger_rows(bed))
        record(bed, rec)
        hash_bed(hb, bed)
        hash_wet(hw, bed)
        if is_quiet(bed) and bed.t > p.dt_phys * 10:
            break
        if bed.fuel_mass() < 0.05 * bed.m0:
            gone_after = step if gone_after is None else gone_after
            if step - gone_after > 600:
                break
    out: dict = {k: np.array(v) for k, v in rec.items()}
    out.update(
        ledger=ledger_hist,
        m0=bed.m0,
        wood0=bed.wood0,
        liq0=bed.liq0,
        area=float(bed.A_ui0.sum() + bed.A_up0.sum()),
        disc=float(bed.A_up0.sum()),
        digest_bed=hb.hexdigest(),
        digest=hw.hexdigest(),
        pilot_end=pilot_ticks * 0.1,
        n=bed.n,
    )
    return out


def first_time(t: np.ndarray, cond: np.ndarray) -> float:
    idx = np.nonzero(cond)[0]
    return float(t[idx[0]]) if idx.size else math.nan


def flame_out(t: np.ndarray, a: np.ndarray) -> tuple[float, int]:
    """Start of the final interval with zero flaming area (preregistration §3); NaN if still flaming at the end."""
    on = np.nonzero(a > 0)[0]
    if on.size == 0:
        return math.nan, -1
    last = int(on[-1])
    return (float(t[last + 1]), last + 1) if last + 1 < t.size else (math.nan, -1)


def criteria(r: dict) -> dict:
    """A, B1, B2, C and the reported quantities, exactly as preregistered."""
    t = r["t"]
    pe = r["pilot_end"]
    o: dict = {}
    o["t_A"] = first_time(t, (r["a_disc"] >= 0.9 * r["disc"]) & (t <= pe))
    o["A"] = math.isfinite(o["t_A"])
    lam = r["lit"] / r["area"]
    lam_w = np.maximum.accumulate(r["wood_inv"]) / r["area"]
    lam_w_loose = np.maximum.accumulate(r["wood_inv"] + r["wood_unfl"]) / r["area"]
    o["lambda_max"] = float(lam.max())
    o["B1"] = o["lambda_max"] >= 0.90
    o["t_L95"] = first_time(t, r["liquid"] <= 0.05 * r["liq0"]) if r["liq0"] > 0 else math.nan
    i95 = np.searchsorted(t, o["t_L95"]) if math.isfinite(o["t_L95"]) else t.size - 1
    o["lambda_w_tL95"] = float(lam_w[min(i95, t.size - 1)])
    o["lambda_w_loose_tL95"] = float(lam_w_loose[min(i95, t.size - 1)])
    o["lambda_w_max"] = float(lam_w.max())
    o["B2"] = math.isfinite(o["t_L95"]) and o["lambda_w_tL95"] >= 0.90
    o["t_B"] = first_time(t, lam_w >= 0.90)
    o["t_out"], i_out = flame_out(t, r["a_flaming"])
    o["wood_at_out_frac"] = float(r["wood"][i_out] / r["wood0"]) if i_out >= 0 else float(r["wood"][-1] / r["wood0"])
    o["C"] = bool(
        math.isfinite(o["t_out"])
        and math.isfinite(o["t_L95"])
        and o["t_out"] > o["t_L95"]
        and o["t_out"] > pe
        and o["wood_at_out_frac"] <= 0.05
    )
    o["t_ignite_01"] = first_time(t, r["a_flaming"] >= 0.1)
    i60 = np.searchsorted(t, pe + 60.0)
    o["ignited_60s_after_pilot"] = bool(i60 < t.size and r["a_flaming"][i60] >= 0.1)
    o["t_crack"] = first_time(t, r["crack_cell"] >= CRACK_AREA)
    return o


def reported(r: dict) -> dict:
    """Energy split, venting, peak release, O2 check, char outputs (recorded, not graded)."""
    t = r["t"]
    last = r["ledger"][-1]
    o: dict = {}
    o["E_accelerant_MJ"] = last["combustion_accelerant"] / 1e6
    o["E_wood_flaming_MJ"] = last["combustion_flaming"] / 1e6
    o["E_char_MJ"] = last["combustion_char"] / 1e6
    o["vented_frac"] = float(r["vented"][-1] / r["liq0"]) if r["liq0"] > 0 else math.nan
    o["burnt_frac"] = float(r["burnt"][-1] / r["liq0"]) if r["liq0"] > 0 else math.nan
    o["peak_qdot_kW"] = float(r["qdot"].max()) / 1e3
    o["peak_flaming_area"] = float(r["a_flaming"].max())
    t95 = first_time(t, r["liquid"] <= 0.05 * r["liq0"]) if r["liq0"] > 0 else math.nan
    pre = t <= (t95 if math.isfinite(t95) else t[-1])
    over = (r["o2_demand"] > r["o2_supply"]) & pre
    o["o2_over_frac_before_tL95"] = float(over.sum() / max(pre.sum(), 1))
    o["o2_unverified"] = o["o2_over_frac_before_tL95"] > 0.10
    o["o2_demand_peak_gs"] = float(r["o2_demand"].max()) * 1e3
    o["o2_supply_at_peak_gs"] = float(r["o2_supply"][int(np.argmax(r["o2_demand"]))]) * 1e3
    em = r["ember_max"]
    o["ember_peak_c"] = float(np.nanmax(em)) if np.any(np.isfinite(em)) else math.nan
    o["fuel_end_frac"] = float(r["fuel"][-1] / r["m0"])
    return o


def bed_compatible(r: dict) -> dict:
    """The bed spike's observables (sim.py::observables) for E4(ii)."""
    t = r["t"]
    pe = r["pilot_end"]
    after = t > pe
    fl = r["a_flaming_iw"][after]
    idx = np.nonzero(fl <= 0)[0]
    o: dict = {"t_ignite": first_time(t, r["a_flaming_iw"] >= 0.1)}
    o["t_flameout"] = float(t[after][idx[0]]) if idx.size else math.nan
    o["wood_at_flameout_frac"] = (
        float(r["wood"][after][idx[0]] / r["wood0"]) if idx.size else float(r["wood"][-1] / r["wood0"])
    )
    o["peak_flaming_area"] = float(r["a_flaming_iw"].max())
    o["t_crack"] = first_time(t, r["crack_cell"] >= CRACK_AREA)
    o["fuel_end_frac"] = float(r["fuel"][-1] / r["m0"])
    o["digest"] = r["digest_bed"]
    return o


def ledger_checks(r: dict) -> dict:
    """E1 worst closure, E2 deletion per line, E3 liquid mass closure."""
    worst = 0.0
    for row in r["ledger"]:
        res, rel = residual(row)
        if rel > 0:
            worst = max(worst, res / rel)
    dele = {}
    for line in (*ACC_IN, *ACC_OUT, *STORE, "liquid_sensible"):
        w = 0.0
        for row in r["ledger"]:
            res, rel = residual(row, drop=line)
            if rel > 0:
                w = max(w, res / rel)
        dele[line] = w
    if r["liq0"] > 0:
        mass = np.abs(r["liq0"] - (r["liquid"] + r["burnt"] + r["vented"])) / r["liq0"]
        liq_worst = float(mass.max())
    else:
        liq_worst = 0.0
    return {"E1_worst_rel": worst, "E2_deletion": dele, "E3_liquid_worst_rel": liq_worst}
