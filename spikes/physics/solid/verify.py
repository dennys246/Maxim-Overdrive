"""V1-V3 (our solid against FDS 6.11.1) and P0 (both against NIST's gasification data), §5.

Both solvers' outputs are compared at FDS's device times: ours is interpolated linearly from its step ends onto
them, so every first-crossing time is read the same way (the first device sample at or above the level, stage 0's
`gasif` rule). FDS: m'' is `BURNING RATE` (BR1), front T `WALL TEMPERATURE` (TW1, the face, wall.f90's
TMP_F = (ghost + node 1)/2), the sample mass the PMMA components' `SURFACE DENSITY` (SD_11..13), back T `INSIDE WALL
TEMPERATURE` at the PMMA/Kaowool depth (TSB1). Ours: the same quantities from the kernel (back T is the last PMMA
node's T, the cell FDS picks at that depth).
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

import fds_driver
import harness
import inputs
import materials
import numpy as np
import numpy.typing as npt
import spec

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE / "stage0"))
Array = npt.NDArray[np.float64]
BANDS = json.loads((HERE / "stage0" / "bands.json").read_text(encoding="utf-8"))

V_CASES = {"V1": ("25R1", fds_driver.LONG_25), "V2": ("R3", None)}
P0_MLR = {"R3": "q50_Mass_R3", "R4": "q50_Mass_R4", "R5": "q50_Mass_R5"}
P0_TEMP = {
    "25R1": "q25_Temp_R1",
    "25R2": "q25_Temp_R2",
    "25R3": "q25_Temp_R3",
    "T1": "q50_Temp_R1",
    "T2": "q50_Temp_R2",
    "T3": "q50_Temp_R3",
    "T4": "q50_Temp_R4",
    "T5": "q50_Temp_R5",
}


def first_at_or_above(t: Array, v: Array, level: float) -> float | None:
    hits = np.flatnonzero(v >= level)
    return float(t[hits[0]]) if hits.size else None


def fds_series(case: str) -> dict[str, Array]:
    d = fds_driver.devc(case)
    sd = d["SD_11"] + d["SD_12"] + d["SD_13"]
    return {
        "t": d["Time"],
        "mdot": d["BR1"] * 1000.0,
        "mass": sd * 1000.0,
        "t_front": d["TW1"] + spec.KELVIN,
        "t_back": d["TSB1"] + spec.KELVIN,
    }


def our_series(case: str, dt: float, *, fds_h_r: bool, refine: int = 1) -> tuple[dict[str, Array], harness.Series]:
    c = inputs.fds_case(case)
    t_end = fds_driver.LONG_25 if case.startswith("25") else c["t_end"]
    b = materials.pmma_from_fds(c, fds_h_r=fds_h_r, refine=refine)
    s = harness.gasification(b, flux=c["flux_w"], h=c["h"], t_amb=c["tmpa_k"], dt=dt, t_end=t_end)
    a = s.arrays()
    tf = fds_series(case)["t"]
    return {k: (np.interp(tf, a["t"], v) if k != "t" else tf) for k, v in a.items() if k != "q"}, s


def v_features(x: dict[str, Array]) -> dict[str, float | None]:
    t, m = x["t"], x["mdot"]
    i = int(np.argmax(m))
    peak = float(m[i])
    j300 = int(np.argmin(np.abs(t - 300.0)))
    return {
        "peak": peak,
        "t_peak": float(t[i]),
        "t_mdot_1": first_at_or_above(t, m, 1.0),
        "t_mdot_2.7": first_at_or_above(t, m, 2.7),
        "t_half_peak": first_at_or_above(t, m, 0.5 * peak),
        "front_T_300": float(x["t_front"][j300]),
        "mass_lost_300": float(x["mass"][0] - x["mass"][j300]),
        "t_sample_300": float(t[j300]),
    }


V_TOL = {
    "peak": ("rel", spec.TOL_REL),
    "t_mdot_1": ("abs", spec.TOL_TIME),
    "t_mdot_2.7": ("abs", spec.TOL_TIME),
    "t_half_peak": ("abs", spec.TOL_TIME),
    "front_T_300": ("abs", spec.TOL_FRONT_T),
    "mass_lost_300": ("rel", spec.TOL_REL),
}


def compare(ours: dict[str, float | None], fds: dict[str, float | None], with_peak_time: bool) -> dict[str, Any]:
    tol = dict(V_TOL) | ({"t_peak": ("abs", spec.TOL_PEAK_TIME)} if with_peak_time else {})
    rows: dict[str, Any] = {}
    for k, (kind, tv) in tol.items():
        a, b = ours[k], fds[k]
        if a is None or b is None:
            rows[k] = {"ours": a, "fds": b, "pass": False}
            continue
        err = (a - b) / b if kind == "rel" else a - b
        rows[k] = {"ours": a, "fds": b, "error": err, "tolerance": tv, "kind": kind, "pass": bool(abs(err) <= tv)}
    if not with_peak_time:
        rows["t_peak_ungraded"] = {"ours": ours["t_peak"], "fds": fds["t_peak"]}
    return {"rows": rows, "pass": all(r["pass"] for r in rows.values() if "pass" in r)}


def v_all(*, fds_h_r: bool) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for crit, (case, _) in V_CASES.items():
        f = v_features(fds_series(case))
        out[crit] = {"case": case, "fds": f}
        for dt in spec.V_STEPS:
            x, s = our_series(case, dt, fds_h_r=fds_h_r)
            out[crit][f"dt_{dt}"] = compare(v_features(x), f, with_peak_time=crit == "V2") | {
                "N5_worst_mass": s.worst_mass,
                "N6_worst_energy": s.worst_energy,
                "N6_lines_needed": s.lines_needed,
                "merges": s.merges,
                "steps": s.steps,
            }
    v3 = all(out[c][f"dt_{dt}"]["pass"] for c in V_CASES for dt in spec.V_STEPS)
    out["V1"]["pass"] = all(out["V1"][f"dt_{dt}"]["pass"] for dt in spec.V_STEPS)
    out["V2"]["pass"] = all(out["V2"][f"dt_{dt}"]["pass"] for dt in spec.V_STEPS)
    out["V3"] = {
        "pass": v3,
        "at_0.01": all(out[c]["dt_0.01"]["pass"] for c in V_CASES),
        "at_0.5": all(out[c]["dt_0.5"]["pass"] for c in V_CASES),
    }
    return out


# ----- P0 -----
def gasif_mlr_features(x: dict[str, Array]) -> dict[str, float | None]:
    t, m = x["t"], x["mdot"]
    i = int(np.argmax(m))
    half = x["mass"][0] * 0.5
    hits = np.flatnonzero(x["mass"] <= half)
    return {
        "peak_mlr": float(m[i]),
        "t_peak": float(t[i]),
        "t_mlr_2.7": first_at_or_above(t, m, 2.7),
        "t_half_mass": float(t[hits[0]]) if hits.size else None,
    }


def gasif_temp_features(x: dict[str, Array]) -> dict[str, float | None]:
    tc = x["t_back"] - spec.KELVIN
    return {f"t_back_{lv:.0f}C": first_at_or_above(x["t"], tc, lv) for lv in (100.0, 200.0, 300.0)}


P0_TOL = {
    "peak_mlr": ("rel", spec.TOL_REL),
    "t_peak": ("abs", spec.TOL_PEAK_TIME),
    "t_mlr_2.7": ("abs", spec.TOL_TIME),
    "t_half_mass": ("abs", spec.TOL_TIME),
    "t_back_100C": ("abs", spec.TOL_TIME),
    "t_back_200C": ("abs", spec.TOL_TIME),
    "t_back_300C": ("abs", spec.TOL_TIME),
}


def classify(feat: str, ours: float | None, fds: float | None, data: float, group: str) -> dict[str, Any]:
    """§5 P0: A inside the repeats' widened range; B if |ours - data| <= |FDS - data| + tolerance; else C."""
    rng = BANDS["gasification"]["ranges"][group][feat]
    kind, tv = P0_TOL[feat]
    row: dict[str, Any] = {"ours": ours, "fds": fds, "data": data, "range": [rng["lo"], rng["hi"]]}
    if ours is None:
        return row | {"class": "C", "why": "ours never reaches it"}
    if rng["lo"] <= ours <= rng["hi"]:
        return row | {"class": "A"}
    tol = tv * abs(data) if kind == "rel" else tv
    fds_err = abs(fds - data) if fds is not None else math.inf
    if abs(ours - data) <= fds_err + tol:
        return row | {"class": "B", "ours_err": abs(ours - data), "fds_err": fds_err, "tol": tol}
    return row | {"class": "C", "ours_err": abs(ours - data), "fds_err": fds_err, "tol": tol}


def p0_all(dt: float, *, fds_h_r: bool) -> dict[str, Any]:
    reps = BANDS["gasification"]["repeats"]
    rows: dict[str, Any] = {}
    for case in inputs.FDS_CASES:
        x, _ = our_series(case, dt, fds_h_r=fds_h_r)
        f = fds_series(case)
        if case in P0_MLR:
            key = P0_MLR[case]
            o, fd = gasif_mlr_features(x), gasif_mlr_features(f)
            for feat in ("peak_mlr", "t_peak", "t_mlr_2.7", "t_half_mass"):
                rows[f"{case}:{feat}"] = classify(feat, o[feat], fd[feat], float(reps[key][feat]), "q50_Mass") | {"repeat": key}
        if case in P0_TEMP:
            key = P0_TEMP[case]
            group = "q25_Temp" if case.startswith("25") else "q50_Temp"
            o, fd = gasif_temp_features(x), gasif_temp_features(f)
            for feat in ("t_back_100C", "t_back_200C", "t_back_300C"):
                d = reps[key].get(feat)
                if d is None:
                    continue
                rows[f"{case}:{feat}"] = classify(feat, o[feat], fd[feat], float(d), group) | {"repeat": key}
    counts = {c: sum(1 for r in rows.values() if r["class"] == c) for c in "ABC"}
    return {"dt": dt, "rows": rows, "counts": counts, "pass": counts["C"] == 0}
