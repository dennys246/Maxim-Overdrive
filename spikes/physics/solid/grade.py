"""P1, P2, S1, S2, N1-N4 and N9 on the fitted parameters (§5); seed 0 graded, seeds 1-4 reported.

A "graded run" is a held-out flux of a graded fit: PMMA forward (fit 25) at 50 and 65, PMMA reverse (fit 65) at 25,
pine (fit 30, 60) at 25, 50 and 75. N1, N2 and N3 run on every one of them; N5 and N6 are read from every run here.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import cone
import fit
import harness
import spec

HERE = Path(__file__).resolve().parent
FIT_DIR = HERE / "out" / "fit"  # rerun 1 points this at out_rerun1/fit (rerun1.py)
# Rerun 1 §1 B: each material's node multiplier r* for every run here that doesn't name its own `refine`. The first
# run's value is 1 (FDS's rule); rerun1.py sets r* from the convergence probe before any graded run.
REFINE = {"pmma": 1, "pine": 1}
PMMA_GRADED = {"pmma_forward": (25, (50, 65)), "pmma_reverse": (65, (25,))}
TIME_FEATURES = {"t_ig", "t_peak"}


def load_fit(name: str, seed: int) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads((FIT_DIR / f"{name}_s{seed}.json").read_text(encoding="utf-8"))
    return loaded


def in_band(value: Any, b: dict[str, Any]) -> bool:
    return value is not None and math.isfinite(float(value)) and b["lo"] <= float(value) <= b["hi"]


def _num(v: Any) -> float | None:
    return None if v is None else float(v)


class Ledger:
    """N3, N5 and N6 over every run graded here."""

    def __init__(self) -> None:
        self.runs = 0
        self.max_flashes = 0
        self.worst_mass = 0.0
        self.worst_energy = 0.0
        self.min_line_needed: dict[str, float] = {}

    def add(self, s: harness.Series) -> harness.Series:
        self.runs += 1
        self.max_flashes = max(self.max_flashes, s.flashes)
        self.worst_mass = max(self.worst_mass, s.worst_mass)
        self.worst_energy = max(self.worst_energy, s.worst_energy)
        for k, v in s.lines_needed.items():
            self.min_line_needed[k] = min(self.min_line_needed.get(k, math.inf), v)
        return s

    def summary(self) -> dict[str, Any]:
        return {
            "runs": self.runs,
            "N3_max_flashes_per_part": self.max_flashes,
            "N3_pass": self.max_flashes <= 1,
            "N5_worst_relative_mass_error": self.worst_mass,
            "N5_pass": self.worst_mass <= spec.N5_TOL,
            "N6_worst_relative_energy_residual": self.worst_energy,
            "N6_pass": self.worst_energy <= spec.N6_TOL,
            "N6_residual_with_each_line_deleted_min_over_runs": self.min_line_needed,
            "N6_every_line_needed": all(v > spec.N6_TOL for v in self.min_line_needed.values()),
        }


LEDGER = Ledger()


# ----- PMMA -----
def pmma_eval(name: str, x: list[float], flux: int, *, record: bool = True, **kw: Any) -> tuple[harness.Series, dict[str, Any]]:
    fit_flux = PMMA_GRADED[name][0]
    kw.setdefault("refine", REFINE["pmma"])
    s, f = cone.pmma_run(flux, fit.pmma_params(x), fit_flux=fit_flux, **kw)
    if record:
        LEDGER.add(s)
    return s, f


def pmma_grade_flux(name: str, x: list[float], flux: int) -> dict[str, Any]:
    s, f = pmma_eval(name, x, flux)
    per_lab = cone.BANDS["pmma"]["per_lab"]["DBI_Lund"][str(flux)]
    env = cone.BANDS["pmma"]["envelope"][str(flux)]
    rows = {k: {"model": _num(f.get(k)), "band": [per_lab[k]["lo"], per_lab[k]["hi"]], "in": in_band(f.get(k), per_lab[k])} for k in cone.PMMA_FEATURES}
    env_rows = {k: {"model": _num(f.get(k)), "band": [env[k]["lo"], env[k]["hi"]], "in": in_band(f.get(k), env[k])} for k in cone.PMMA_FEATURES}
    t_flash = f.get("t_ig")
    s2 = cone.mlr10_falls(s, float(t_flash), cone.pmma_data_peak_time(flux)) if t_flash is not None else {"falls": None}
    graded_ok = all(r["in"] for r in rows.values()) and env_rows["t_ig"]["in"]
    return {
        "flux": flux,
        "per_lab_DBI": rows,
        "envelope_t_ig_graded": env_rows["t_ig"],
        "envelope_reported_for_outcome_4": env_rows,
        "pass": graded_ok,
        "S2": s2 | {"window": [t_flash, cone.pmma_data_peak_time(flux)]},
        "class": cone.run_class(s, f),
    }


def pmma_n1_n2(name: str, x: list[float], flux: int, base: dict[str, Any]) -> dict[str, Any]:
    runs = {dt: pmma_eval(name, x, flux, dt=dt) for dt in spec.N1_STEPS}
    f5, f25, f125 = (runs[d][1] for d in spec.N1_STEPS)
    c5, c25 = (cone.run_class(*runs[d]) for d in spec.N1_STEPS[:2])
    n1 = _n1(c5, c25, f5.get("t_ig"), f25.get("t_ig"), f25.get("peak"), f125.get("peak"))
    s2r, f2r = pmma_eval(name, x, flux, refine=2)
    n2 = _n2(base["class"], cone.run_class(s2r, f2r), f5, f2r, cone.PMMA_FEATURES)
    return {"N1": n1, "N2": n2}


def _n1(c5: dict[str, Any], c25: dict[str, Any], t5: Any, t25: Any, p25: Any, p125: Any) -> dict[str, Any]:
    out: dict[str, Any] = {"class_0.5": c5, "class_0.25": c25, "t_ig_0.5": _num(t5), "t_ig_0.25": _num(t25)}
    same = c5 == c25
    if t5 is None or t25 is None:
        tig_ok = t5 is None and t25 is None
        tol = None
    else:
        tol = max(spec.N1_TIG_ABS, spec.N1_TIG_REL * float(t25))
        tig_ok = abs(float(t5) - float(t25)) <= tol
    vacuous = t5 is None and t25 is None and p25 is None and p125 is None  # no step ignites: nothing to compare
    peak_ok = vacuous or (p25 is not None and p125 is not None and abs(float(p125) / float(p25) - 1) <= spec.N1_PEAK_REL)
    out["vacuous_no_ignition_at_any_step"] = vacuous
    out |= {
        "t_ig_tol": tol,
        "peak_0.25": _num(p25),
        "peak_0.125": _num(p125),
        "peak_rel_diff": None if (p25 is None or p125 is None) else float(p125) / float(p25) - 1,
        "pass": bool(same and tig_ok and peak_ok),
    }
    return out


def _n2(c1: dict[str, Any], c2: dict[str, Any], f1: dict[str, Any], f2: dict[str, Any], feats: tuple[str, ...]) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    ok = c1 == c2
    for k in feats:
        a, b = f1.get(k), f2.get(k)
        if a is None or b is None:
            rows[k] = {"base": _num(a), "halved": _num(b), "pass": a is None and b is None}
        elif k in TIME_FEATURES:
            rows[k] = {"base": float(a), "halved": float(b), "diff": float(b) - float(a), "pass": abs(float(b) - float(a)) <= spec.TOL_TIME}
        else:
            rows[k] = {"base": float(a), "halved": float(b), "rel": float(b) / float(a) - 1, "pass": abs(float(b) / float(a) - 1) <= spec.TOL_REL}
        ok = ok and rows[k]["pass"]
    return {"class_base": c1, "class_halved": c2, "rows": rows, "pass": bool(ok)}


def pmma_section(seed: int, *, numerics: bool) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, (_, graded) in PMMA_GRADED.items():
        fr = load_fit(name, seed)
        x = fr["x"]
        g = {str(fl): pmma_grade_flux(name, x, fl) for fl in graded}
        fit_flux = PMMA_GRADED[name][0]
        sf, ff = pmma_eval(name, x, fit_flux)
        entry: dict[str, Any] = {
            "fit": {k: v for k, v in fr.items() if k != "timing_reported_only"},
            "fit_flux_features": {k: _num(ff.get(k)) for k in cone.PMMA_FEATURES},
            "graded": g,
            "pass": all(v["pass"] for v in g.values()),
        }
        if numerics:
            entry["numerics"] = {fl: pmma_n1_n2(name, x, int(fl), g[fl]) for fl in g}
        out[name] = entry
    return out


# ----- pine -----
def pine_eval(x: list[float], flux: int, *, record: bool = True, **kw: Any) -> tuple[harness.Series, dict[str, Any]]:
    kw.setdefault("refine", REFINE["pine"])
    s, f = cone.pine_run(flux, fit.pine_params(x), **kw)
    if record:
        LEDGER.add(s)
    return s, f


def pine_graded_run(x: list[float], flux: int, *, record: bool = True, **kw: Any) -> tuple[harness.Series, dict[str, Any]]:
    t_end = cone.pine_data_window_end(flux) + 30.0
    return pine_eval(x, flux, t_end=t_end, stop_after_flash=None, record=record, **kw)


def envelope_without(flux: int, feat: str, drop: str) -> dict[str, float] | None:
    """The envelope at a flux with one lab's mean left out (outcome 6), widened as §2.2 does."""
    labs = cone.BANDS["pine"]["envelope"][str(flux)][feat]["labs"]
    means = [v["mean"] for k, v in sorted(labs.items()) if k != drop]
    if not means:
        return None
    lo, hi = min(means), max(means)
    if feat == "t_ig":
        return {"lo": lo - spec.TOL_TIME, "hi": hi + spec.TOL_TIME}
    return {"lo": lo * (1 - spec.TOL_REL), "hi": hi * (1 + spec.TOL_REL)}


def pine_grade_flux(x: list[float], flux: int) -> dict[str, Any]:
    s, f = pine_graded_run(x, flux)
    env = cone.BANDS["pine"]["envelope"][str(flux)]
    rows = {}
    for k in cone.PINE_FEATURES:
        nb = envelope_without(flux, k, "IMT")
        rows[k] = {
            "model": _num(f.get(k)),
            "band": [env[k]["lo"], env[k]["hi"]],
            "in": in_band(f.get(k), env[k]),
            "lab_means": {lab: v["mean"] for lab, v in sorted(env[k]["labs"].items())},
            "in_without_IMT_reported": None if nb is None else in_band(f.get(k), nb),
        }
    w_end = cone.pine_data_window_end(flux)
    t_ig = f.get("t_ig")
    mmin = cone.min_mdot_after(s, float(t_ig), w_end) if t_ig is not None else math.nan
    s1_need = spec.S1_MARGIN * cone.PINE_M_EXT * 1e3
    return {
        "flux": flux,
        "envelope": rows,
        "pass": all(r["in"] for r in rows.values()),
        "S1": {
            "window": [_num(t_ig), w_end],
            "min_mdot_g_m2s": mmin,
            "needed_g_m2s": s1_need,
            "pass": bool(math.isfinite(mmin) and mmin >= s1_need),
            "extinctions": s.extinctions,
            "not_independent_at_25": flux == 25,
        },
        "model_window_end": _num(f.get("window_end")),
        "class": cone.run_class(s, f),
    }


def pine_n1_n2(x: list[float], flux: int, base: dict[str, Any]) -> dict[str, Any]:
    runs = {dt: pine_graded_run(x, flux, dt=dt) for dt in spec.N1_STEPS}
    f5, f25, f125 = (runs[d][1] for d in spec.N1_STEPS)
    c5, c25 = (cone.run_class(*runs[d]) for d in spec.N1_STEPS[:2])
    n1 = _n1(c5, c25, f5.get("t_ig"), f25.get("t_ig"), f25.get("first_peak"), f125.get("first_peak"))
    s2r, f2r = pine_graded_run(x, flux, refine=2)
    n2 = _n2(base["class"], cone.run_class(s2r, f2r), f5, f2r, cone.PINE_FEATURES)
    return {"N1": n1, "N2": n2}


def pine_section(seed: int, *, numerics: bool, name: str = "pine") -> dict[str, Any]:
    fr = load_fit(name, seed)
    x = fr["x"]
    g = {str(fl): pine_grade_flux(x, fl) for fl in spec.PINE_GRADED_FLUXES}
    fit_feats = {}
    for fl in spec.PINE_FIT_FLUXES:
        _, ff = pine_eval(x, fl, t_end=spec.PINE_FIT_T_CAP)
        fit_feats[str(fl)] = {k: _num(ff.get(k)) for k in cone.PINE_FEATURES}
    m_flash = fr["x"][1] * 1e-3
    out: dict[str, Any] = {
        "fit": {k: v for k, v in fr.items() if k != "timing_reported_only"},
        "fit_flux_features": fit_feats,
        "graded": g,
        "pass": all(v["pass"] for v in g.values()),
        "S1_pass": all(v["S1"]["pass"] for v in g.values()),
        "outcome_12_m_ext_ge_m_flash": cone.PINE_M_EXT >= m_flash,
    }
    if numerics:
        out["numerics"] = {fl: pine_n1_n2(x, int(fl), g[fl]) for fl in g}
    return out


# ----- N4 and N9 -----
def n4(pmma_x: list[float], pine_x: list[float]) -> dict[str, Any]:
    """m''_ext set to 1.5 x the fitted m''_flash (the loader would refuse it): N1 or N3 must go red."""
    out: dict[str, Any] = {"pmma_forward_50": n4_pmma(pmma_x), "pine_50": n4_pine(pine_x)}
    out["pass"] = all(v["red"] for v in out.values() if isinstance(v, dict))
    return out


def n4_pmma(pmma_x: list[float]) -> dict[str, Any]:
    mf = pmma_x[1] * 1e-3
    runs = {dt: pmma_eval("pmma_forward", pmma_x, 50, dt=dt, m_ext=1.5 * mf, allow_inverted=True, record=False) for dt in spec.N1_STEPS[:2]}
    return _n4_row(runs)


def n4_pine(pine_x: list[float]) -> dict[str, Any]:
    mf = pine_x[1] * 1e-3
    runs = {dt: pine_graded_run(pine_x, 50, dt=dt, m_ext=1.5 * mf, allow_inverted=True, record=False) for dt in spec.N1_STEPS[:2]}
    return _n4_row(runs)


def _n4_row(runs: dict[float, tuple[harness.Series, dict[str, Any]]]) -> dict[str, Any]:
    flashes = {str(dt): r[0].flashes for dt, r in runs.items()}
    c = {str(dt): cone.run_class(*r) for dt, r in runs.items()}
    t = [runs[d][1].get("t_ig") for d in spec.N1_STEPS[:2]]
    n3_red = max(flashes.values()) > 1
    n1_red = c[str(spec.N1_STEPS[0])] != c[str(spec.N1_STEPS[1])]
    return {"flashes": flashes, "classes": c, "t_ig": t, "N3_red": n3_red, "N1_class_red": n1_red, "red": n3_red or n1_red}


N9_VARIANTS: dict[str, dict[str, Any]] = {
    "k_0.041": {"backing_k": spec.N9_BACKING_K_CONST},
    "k_kaowool_ramp": {"backing_k_ramp": "kaowool"},
    "c_800": {"backing_c": spec.N9_BACKING_C[0]},
    "c_1200": {"backing_c": spec.N9_BACKING_C[1]},
}


def n9(pmma_fwd: list[float], pmma_rev: list[float], pine_x: list[float], base: dict[str, Any]) -> dict[str, Any]:
    """Range ends, fitted parameters held: PMMA backing k 0.041 / Kaowool PM's k ramp / c 800 / c 1,200; pine on 25.4 mm
    Kaowool PM. A graded feature changing in/out of its band, or the run class changing, is a class flip (outcome 9)."""
    a, b = n9_pmma(pmma_fwd, pmma_rev, base), n9_pine(pine_x, base)
    flips = a["flips"] + b["flips"]
    return {"rows": a["rows"] | b["rows"], "flips": flips, "outcome_9": bool(flips)}


def n9_pmma(pmma_fwd: list[float], pmma_rev: list[float], base: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    flips = []
    for name, x in (("pmma_forward", pmma_fwd), ("pmma_reverse", pmma_rev)):
        for fl in PMMA_GRADED[name][1]:
            ref = base[name]["graded"][str(fl)]
            for vn, kw in N9_VARIANTS.items():
                s, f = pmma_eval(name, x, fl, **kw)
                per_lab = cone.BANDS["pmma"]["per_lab"]["DBI_Lund"][str(fl)]
                ins = {k: in_band(f.get(k), per_lab[k]) for k in cone.PMMA_FEATURES}
                flip = any(ins[k] != ref["per_lab_DBI"][k]["in"] for k in ins) or cone.run_class(s, f) != ref["class"]
                out[f"{name}:{fl}:{vn}"] = {"features": {k: _num(f.get(k)) for k in cone.PMMA_FEATURES}, "in_band": ins, "flip": flip}
                if flip:
                    flips.append(f"{name}:{fl}:{vn}")
    return {"rows": out, "flips": flips, "outcome_9": bool(flips)}


def n9_pine(pine_x: list[float], base: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    flips = []
    for fl in spec.PINE_GRADED_FLUXES:
        ref = base["pine"]["graded"][str(fl)]
        s, f = pine_graded_run(pine_x, fl, backing="kaowool")
        env = cone.BANDS["pine"]["envelope"][str(fl)]
        ins = {k: in_band(f.get(k), env[k]) for k in cone.PINE_FEATURES}
        flip = any(ins[k] != ref["envelope"][k]["in"] for k in ins) or cone.run_class(s, f) != ref["class"]
        out[f"pine:{fl}:kaowool"] = {"features": {k: _num(f.get(k)) for k in cone.PINE_FEATURES}, "in_band": ins, "flip": flip}
        if flip:
            flips.append(f"pine:{fl}:kaowool")
    return {"rows": out, "flips": flips, "outcome_9": bool(flips)}


def seed_spread(seeds: tuple[int, ...]) -> dict[str, Any]:
    """Seeds 1-4: fitted values and graded features (reported, not graded)."""
    out: dict[str, Any] = {}
    for sd in seeds:
        p = pmma_section(sd, numerics=False)
        q = pine_section(sd, numerics=False)
        out[str(sd)] = {
            name: {
                "x": p[name]["fit"]["x"],
                "objective": p[name]["fit"]["objective"],
                "graded": {fl: {k: r["model"] for k, r in g["per_lab_DBI"].items()} | {"pass": g["pass"]} for fl, g in p[name]["graded"].items()},
            }
            for name in PMMA_GRADED
        } | {
            "pine": {
                "x": q["fit"]["x"],
                "objective": q["fit"]["objective"],
                "graded": {fl: {k: r["model"] for k, r in g["envelope"].items()} | {"pass": g["pass"]} for fl, g in q["graded"].items()},
            }
        }
    return out


def pmma_const_h_reported() -> dict[str, Any]:
    """Reported only: the PMMA fits and held-out features with the model as registered (constant H, before V's fix)."""
    out: dict[str, Any] = {}
    for name, base in (("pmma_forward_constH", "pmma_forward"), ("pmma_reverse_constH", "pmma_reverse")):
        fr = load_fit(name, 0)
        fit_flux, graded = PMMA_GRADED[base]
        rows = {}
        for fl in graded:
            s, f = cone.pmma_run(fl, fit.pmma_params(fr["x"]), fit_flux=fit_flux, fds_h_r=False)
            per_lab = cone.BANDS["pmma"]["per_lab"]["DBI_Lund"][str(fl)]
            env = cone.BANDS["pmma"]["envelope"][str(fl)]
            ins = {k: in_band(f.get(k), per_lab[k]) for k in cone.PMMA_FEATURES}
            rows[str(fl)] = {"features": {k: _num(f.get(k)) for k in cone.PMMA_FEATURES}, "in_DBI_band": ins,
                             "t_ig_in_envelope": in_band(f.get("t_ig"), env["t_ig"]),
                             "would_pass": all(ins.values()) and in_band(f.get("t_ig"), env["t_ig"])}
        out[name] = {"x": fr["x"], "objective": fr["objective"], "flags": fr["flags"], "graded": rows}
    return out
