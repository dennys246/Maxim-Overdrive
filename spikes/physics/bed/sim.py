"""Run one bed scenario, record observables and the ledger at every physics step (spike)."""

from __future__ import annotations

import hashlib
import math

import numpy as np
from constants import Params
from model import LEDGER_IN, LEDGER_OUT, Bed

GLOW_C = 625.0
GLOW_AREA = 0.08
CRACK_AREA = 0.08


def ledger_rows(bed: Bed) -> dict[str, float]:
    cells, skins = bed.energies()
    row = dict(bed.ledger)
    row["d_cells"] = cells - bed.E0_cells
    row["d_skins"] = skins - bed.E0_skins
    return row


def residual(row: dict[str, float], drop: str | None = None) -> tuple[float, float]:
    """Return (|in - d_stored - out|, cumulative release) with one line optionally deleted."""
    ins = sum(row[k] for k in LEDGER_IN if k != drop)
    outs = sum(row[k] for k in LEDGER_OUT if k != drop)
    store = sum(row[k] for k in ("d_cells", "d_skins") if k != drop)
    released = row["sources"] + row["combustion_flaming"] + row["combustion_char"]
    return abs(ins - store - outs), released


RECORD_KEYS = (
    "t",
    "a_flaming",
    "a_ignited",
    "fuel",
    "wood",
    "glow_area",
    "glow_area_bright",
    "t_layer_max",
    "crack_cell",
    "crack_rec",
    "ember_max",
    "ember_mean",
    "ember_area",
    "draught_kgs",
    "y_o2_top_min",
)


def record(bed: Bed, rec: dict[str, list]) -> None:
    """Append this physics step's observable inputs to rec."""
    lay = bed.envelope_layer()
    bri = bed.brightness()
    cr = bed.crack_patches()
    ga = sum(bed.sample_area(v, GLOW_C + 273.15) for v in lay.values())
    gb = sum(bed.sample_area(v, GLOW_C + 273.15) for v in bri.values())
    cc = sum(float((v >= 0.1).sum()) * bed.Af for v in cr.values())
    crr = sum(bed.sample_area(v, 0.1) for v in cr.values())
    a_ic = bed.A_ic
    ea = float(a_ic.sum())
    rec["t"].append(bed.t)
    rec["a_flaming"].append(float(np.where(bed.flaming, bed.A_iw, 0).sum()))
    rec["a_ignited"].append(float((bed.A_iw + bed.A_ic).sum()))
    rec["fuel"].append(bed.fuel_mass())
    rec["wood"].append(bed.wood_mass())
    rec["glow_area"].append(ga)
    rec["glow_area_bright"].append(gb)
    rec["t_layer_max"].append(max(float(v.max()) for v in lay.values()) - 273.15)
    rec["crack_cell"].append(cc)
    rec["crack_rec"].append(crr)
    rec["ember_max"].append(float(np.where(a_ic > 0, bed.T_ic, 0).max()) - 273.15 if ea > 0 else math.nan)
    rec["ember_mean"].append(float((a_ic * bed.T_ic).sum() / ea) - 273.15 if ea > 0 else math.nan)
    rec["ember_area"].append(ea)
    rec["draught_kgs"].append(float(bed.Gcol.sum() * bed.Af))
    rec["y_o2_top_min"].append(0.0)


def hash_state(h, bed: Bed) -> None:
    h.update(np.ascontiguousarray(bed.Tu).tobytes())
    h.update(np.ascontiguousarray(bed.T_ic).tobytes())
    h.update(np.ascontiguousarray(bed.G).tobytes())
    h.update(np.ascontiguousarray(bed.c_ic).tobytes())


def is_quiet(bed: Bed) -> bool:
    """Pilot off, no flame, and every surface within 30 K of ambient."""
    return (
        bed.pilot_fraction() == 0
        and not bed.flaming.any()
        and max(float(bed.Tu[..., 0].max()), float(bed.Ts_iw.max()), float(bed.T_ic.max())) < bed.T0 + 30.0
    )


def run(
    p: Params,
    dx: float,
    pilot_ticks: int,
    *,
    t_end: float | None = None,
    record_every: int = 1,
    stop_when_gone: bool = True,
) -> dict:
    bed = Bed(p, dx, pilot_ticks)
    t_end = p.cap_s if t_end is None else t_end
    nsteps = round(t_end / p.dt_phys)
    rec: dict[str, list] = {k: [] for k in RECORD_KEYS}
    ledger_hist: list[dict[str, float]] = []
    h = hashlib.sha256()
    gone_after = None
    for step in range(nsteps):
        bed.physics_step()
        row = ledger_rows(bed)
        ledger_hist.append(row)
        if step % record_every:
            continue
        record(bed, rec)
        hash_state(h, bed)
        if is_quiet(bed) and bed.t > p.dt_phys * 10:
            break  # nothing left that can change an observable
        if stop_when_gone and bed.fuel_mass() < 0.05 * bed.m0:
            if gone_after is None:
                gone_after = step
            elif step - gone_after > 600:  # keep 300 s after t_gone for the record
                break
    out = {k: np.array(v) for k, v in rec.items()}
    out["ledger"] = ledger_hist
    out["m0"] = bed.m0
    out["wood0"] = bed.wood0
    out["digest"] = h.hexdigest()
    out["pilot_end"] = pilot_ticks * 0.1
    out["n"] = bed.n
    return out


def first_time(t: np.ndarray, cond: np.ndarray) -> float:
    idx = np.nonzero(cond)[0]
    return float(t[idx[0]]) if idx.size else math.nan


def longest_run(t: np.ndarray, cond: np.ndarray, dt: float) -> float:
    best = cur = 0
    for c in cond:
        cur = cur + 1 if c else 0
        best = max(best, cur)
    return best * dt


def observables(r: dict, p: Params) -> dict:
    t = r["t"]
    dt = float(t[1] - t[0]) if t.size > 1 else p.dt_phys
    pe = r["pilot_end"]
    out = {}
    out["t_ignite"] = first_time(t, r["a_flaming"] >= 0.1)
    i60 = np.searchsorted(t, pe + 60.0)
    out["ignited_60s_after_pilot"] = bool(i60 < t.size and r["a_flaming"][i60] >= 0.1)
    out["t_crack"] = first_time(t, r["crack_cell"] >= CRACK_AREA)
    out["t_crack_rec"] = first_time(t, r["crack_rec"] >= CRACK_AREA)
    out["t_glow"] = first_time(t, r["glow_area"] >= GLOW_AREA)
    out["t_glow_bright"] = first_time(t, r["glow_area_bright"] >= GLOW_AREA)
    out["glow_longest_s"] = longest_run(t, r["glow_area"] >= GLOW_AREA, dt)
    out["glow_bright_longest_s"] = longest_run(t, r["glow_area_bright"] >= GLOW_AREA, dt)
    out["glow_area_max"] = float(r["glow_area"].max())
    out["t_layer_max_c"] = float(r["t_layer_max"].max())
    out["t_gone"] = first_time(t, r["fuel"] < 0.05 * r["m0"])
    after = t > pe
    fl_after = r["a_flaming"][after]
    tt = t[after]
    out_idx = np.nonzero(fl_after <= 0)[0]
    if out_idx.size:
        out["t_flameout"] = float(tt[out_idx[0]])
        out["wood_at_flameout_frac"] = float(r["wood"][after][out_idx[0]] / r["wood0"])
    else:
        out["t_flameout"] = math.nan
        out["wood_at_flameout_frac"] = float(r["wood"][-1] / r["wood0"])
    out["peak_flaming_area"] = float(r["a_flaming"].max())
    em = r["ember_max"]
    out["ember_peak_c"] = float(np.nanmax(em)) if np.any(np.isfinite(em)) else math.nan
    # mean ember temperature over the ember phase (flaming area < 0.1 m^2, char present)
    ph = (
        (r["a_flaming"] < 0.1)
        & (r["ember_area"] > 0)
        & (t > (out["t_ignite"] if math.isfinite(out["t_ignite"]) else 0))
    )
    if np.any(ph):
        w = r["ember_area"][ph]
        out["ember_mean_c"] = float((r["ember_mean"][ph] * w).sum() / w.sum())
    else:
        out["ember_mean_c"] = math.nan
    out["fuel_end_frac"] = float(r["fuel"][-1] / r["m0"])
    out["draught_max_kgs"] = float(r["draught_kgs"].max())
    out["digest"] = r["digest"]
    # ledger 4a
    worst = 0.0
    for row in r["ledger"]:
        res, rel = residual(row)
        if rel > 0:
            worst = max(worst, res / rel)
    out["ledger_worst_rel"] = worst
    out["release_total_MJ"] = (r["ledger"][-1]["combustion_flaming"] + r["ledger"][-1]["combustion_char"]) / 1e6
    return out
