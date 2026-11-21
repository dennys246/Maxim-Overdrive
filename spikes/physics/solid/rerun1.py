"""Rerun 1 of the solid spike: numerics only (`preregistration_rerun1.md`, de2290d), its gates in their order.

    <python> rerun1.py gate1       # gate 1 alone (N7, V1-V3 with N5/N6 on them, §1 B's probe) -> out_rerun1/gate1.json
    ./launch_fits_rerun1.sh        # the fits at each material's r* (out_rerun1/fit/), only for materials past gate 1
    <python> rerun1.py             # gates 1-3 -> results_rerun1.json (+ timings_rerun1.json, not compared by N8)
    <python> rerun1.py --check     # N8: recompute in a fresh process; fail unless results_rerun1.json is byte-identical

The numerics are spec.NUMERICS = "rerun1": §1 A (opacity by FDS's rule, per part) and §1 C (onset cutoffs), applied by
the builders in materials.py; §1 B's r* comes from `probe` and goes to grade.REFINE before any graded run. Everything
else (data, bands, fitter, bounds, features, criteria) is the first run's code, unchanged.

Gate logic (§4): a failure of N7 or V stops both materials; a probe failure (no r* <= 8) or a gate-2 failure stops that
material. A stopped material's graded features are recorded with no band (`features_only`). Outcomes R1-R7 (§5) are
computed by `outcomes`; its reading of R4 and R5 is written there, before any run.
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any

import closed_form
import cone
import fds_driver
import fit
import grade
import inputs
import materials
import run
import spec
import verify

HERE = Path(__file__).resolve().parent
OUT = HERE / "out_rerun1"
RESULTS = HERE / "results_rerun1.json"
TIMINGS = HERE / "timings_rerun1.json"
GATE1 = OUT / "gate1.json"
LOG = OUT / "run.log"
FIRST_RUN = HERE / "results.json"
MATERIALS = ("pmma", "pine")
TIMINGS_ACC: dict[str, Any] = {}


def log(msg: str) -> None:
    line = f"[cpu {time.process_time():8.1f}s load {os.getloadavg()[0]:.2f}] {msg}"
    print(line, flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def timed(name: str, fn: Any, *a: Any, **k: Any) -> Any:
    t0, l0 = time.process_time(), os.getloadavg()[0]
    log(f"{name}: start")
    r = fn(*a, **k)
    TIMINGS_ACC[name] = {"cpu_s": time.process_time() - t0, "load_start": l0, "load_end": os.getloadavg()[0]}
    log(f"{name}: done ({TIMINGS_ACC[name]['cpu_s']:.1f} s)")
    return r


# ----- gate 1 -----
def n5_n6_v(v: dict[str, Any]) -> dict[str, Any]:
    """N5 and N6 over the V runs (both cases, both steps)."""
    rows = [v[c][f"dt_{dt}"] for c in verify.V_CASES for dt in spec.V_STEPS]
    worst_m = max(r["N5_worst_mass"] for r in rows)
    worst_e = max(r["N6_worst_energy"] for r in rows)
    need = {k: min(r["N6_lines_needed"][k] for r in rows) for k in rows[0]["N6_lines_needed"]}
    return {
        "N5_worst_relative_mass_error": worst_m,
        "N5_pass": worst_m <= spec.N5_TOL,
        "N6_worst_relative_energy_residual": worst_e,
        "N6_pass": worst_e <= spec.N6_TOL,
        "N6_residual_with_each_line_deleted_min": need,
        "N6_every_line_needed": all(x > spec.N6_TOL for x in need.values()),
    }


def onsets() -> dict[str, Any]:
    """§1 C's T_cut per reaction as the code computes it, against the registered estimates (> 1 K is disclosed)."""
    out: dict[str, Any] = {}
    for mat, b in (("pmma", materials.pmma_cone(25, fds_h_r=True)), ("pine", materials.pine_cone(25, k_c=0.1, eps_char=0.75))):
        rate = materials.kinetics_rate(materials.pmma_json() if mat == "pmma" else materials.pine_json())
        rows = []
        for r, reg in zip(b.reactions, spec.T_ON_REGISTERED[mat], strict=True):
            rows.append({"t_cut_at_K_CUT_K": r.t_cut_k, "t_on_K": r.t_on, "t_cut_K": r.t_cut,
                         "rate_at_t_cut_per_s": r.a * math.exp(-r.e / (spec.R_GAS * r.t_cut)),
                         "registered_estimate_K": reg, "differs_by_more_than_1K": abs(r.t_on - reg) > 1.0})
        out[mat] = {"tga_rate_K_min": rate, "reactions": rows, "surface_absorption": b.surface_absorption}
    out["pine_on_kaowool_surface_absorption"] = materials.pine_cone(25, k_c=0.1, eps_char=0.75, backing="kaowool").surface_absorption
    out["gasification_inputs_surface_absorption"] = materials.pmma_from_fds(inputs.fds_case("R3"), fds_h_r=True).surface_absorption
    return out


def _mid(bounds: list[tuple[float, float]]) -> list[float]:
    return [0.5 * (lo + hi) for lo, hi in bounds]


def probe_runs(mat: str) -> dict[str, Any]:
    """§1 B: the fit fluxes only, every free parameter at its bound's midpoint, r = 1 ... 32; features and class."""
    out: dict[str, Any] = {}
    fluxes = (25, 65) if mat == "pmma" else spec.PINE_FIT_FLUXES
    for flux in fluxes:
        if mat == "pmma":
            x = _mid(fit.pmma_bounds(flux))
            feats_names = cone.PMMA_FEATURES
        else:
            x = _mid(fit.pine_bounds())
            feats_names = cone.PINE_FEATURES
        rows: dict[str, Any] = {"x_midpoints": x}
        for r in spec.PROBE_REFINE:
            if mat == "pmma":
                s, f = cone.pmma_run(flux, fit.pmma_params(x), fit_flux=flux, refine=r)
            else:
                s, f = cone.pine_run(flux, fit.pine_params(x), t_end=spec.PINE_FIT_T_CAP, refine=r)
            PROBE_LEDGER.add(s)
            rows[str(r)] = {"features": {k: grade._num(f.get(k)) for k in feats_names}, "class": cone.run_class(s, f)}
            log(f"  probe {mat} {flux} r={r}: {rows[str(r)]}")
        out[str(flux)] = rows
    return out


def observed_order(f1: Any, f2: Any, f4: Any) -> Any:
    """p = log2(|f_r - f_2r| / |f_2r - f_4r|); a string when undefined."""
    if f1 is None or f2 is None or f4 is None:
        return "undefined: a feature is missing"
    num, den = abs(float(f1) - float(f2)), abs(float(f2) - float(f4))
    if den == 0.0:
        return "undefined: f_2r == f_4r" if num else "undefined: all three equal"
    if num == 0.0:
        return "undefined: f_r == f_2r"
    return math.log2(num / den)


def r_star(probe: dict[str, Any], feats: tuple[str, ...]) -> dict[str, Any]:
    """The smallest r <= R_STAR_MAX with, at every probe flux, the class unchanged and every fit feature within V's
    tolerances from r to 2r and from 2r to 4r (grade._n2's comparison: 3 s on times, 2.5% relative on the rest)."""
    checks: dict[str, Any] = {}
    chosen = None
    for r in spec.PROBE_REFINE:
        if r > spec.R_STAR_MAX or 4 * r > spec.PROBE_REFINE[-1]:
            break
        per_flux = {}
        for flux, rows in probe.items():
            a, b, c = rows[str(r)], rows[str(2 * r)], rows[str(4 * r)]
            ab = grade._n2(a["class"], b["class"], a["features"], b["features"], feats)
            bc = grade._n2(b["class"], c["class"], b["features"], c["features"], feats)
            per_flux[flux] = {"r_to_2r": ab, "2r_to_4r": bc,
                              "order": {k: observed_order(a["features"][k], b["features"][k], c["features"][k]) for k in feats},
                              "pass": ab["pass"] and bc["pass"]}
        ok = all(v["pass"] for v in per_flux.values())
        checks[str(r)] = {"per_flux": per_flux, "pass": ok}
        if ok and chosen is None:
            chosen = r
    return {"checks": checks, "r_star": chosen, "pass": chosen is not None}


def fds_unchanged() -> dict[str, Any]:
    """The FDS runs are the first run's: input-as-run and device-file SHA-256s equal to results.json's."""
    first = json.loads(FIRST_RUN.read_text(encoding="utf-8"))["fds"]
    now = {c: fds_driver.hashes(c) for c in inputs.FDS_CASES}
    return {"hashes": now, "equal_to_first_run": now == first}


def gate1() -> dict[str, Any]:
    g: dict[str, Any] = {"onsets": timed("onsets", onsets)}
    g["fds"] = fds_unchanged()
    g["fds_h_r_check"] = timed("fds_h_r_check", run.fds_h_r_check)
    g["N7"] = timed("N7", closed_form.all_n7)
    g["N7_kappa_48e3_reported"] = timed("N7_kappa_48e3", closed_form.kappa_48e3_reported)
    g["V"] = timed("V", verify.v_all, fds_h_r=True)
    g["V_N5_N6"] = n5_n6_v(g["V"])
    g["probe"] = {}
    for mat, feats in (("pmma", cone.PMMA_FEATURES), ("pine", cone.PINE_FEATURES)):
        runs = timed(f"probe_{mat}", probe_runs, mat)
        g["probe"][mat] = {"runs": runs} | r_star(runs, feats)
    g["probe_N3_N5_N6"] = PROBE_LEDGER.summary()
    v_ok = g["V"]["V1"]["pass"] and g["V"]["V2"]["pass"] and g["V"]["V3"]["pass"]
    both = g["N7"]["pass"] and v_ok and g["V_N5_N6"]["N5_pass"] and g["V_N5_N6"]["N6_pass"] and g["fds"]["equal_to_first_run"]
    g["N7_and_V_pass"] = bool(both)
    g["pass"] = {m: bool(both and g["probe"][m]["pass"]) for m in MATERIALS}
    g["r_star"] = {m: g["probe"][m]["r_star"] for m in MATERIALS}
    return g


PROBE_LEDGER = grade.Ledger()


# ----- gate 2 -----
def n2_three(c: list[dict[str, Any]], f: list[dict[str, Any]], feats: tuple[str, ...]) -> dict[str, Any]:
    """§4 gate 2's N2: class and features from r* to 2r* and from 2r* to 4r*, with the observed order."""
    ab = grade._n2(c[0], c[1], f[0], f[1], feats)
    bc = grade._n2(c[1], c[2], f[1], f[2], feats)
    order = {k: observed_order(f[0].get(k), f[1].get(k), f[2].get(k)) for k in feats}
    return {"r_to_2r": ab, "2r_to_4r": bc, "order": order, "pass": bool(ab["pass"] and bc["pass"])}


def pmma_numerics(name: str, x: list[float], flux: int, r: int) -> dict[str, Any]:
    runs = {dt: grade.pmma_eval(name, x, flux, dt=dt) for dt in spec.N1_STEPS}
    f5, f25, f125 = (runs[d][1] for d in spec.N1_STEPS)
    c5, c25 = (cone.run_class(*runs[d]) for d in spec.N1_STEPS[:2])
    n1 = grade._n1(c5, c25, f5.get("t_ig"), f25.get("t_ig"), f25.get("peak"), f125.get("peak"))
    rr = [runs[spec.N1_STEPS[0]]] + [grade.pmma_eval(name, x, flux, refine=m * r) for m in (2, 4)]
    n2 = n2_three([cone.run_class(*q) for q in rr], [q[1] for q in rr], cone.PMMA_FEATURES)
    n2["features_by_refine"] = {str(m * r): {k: grade._num(q[1].get(k)) for k in cone.PMMA_FEATURES} for m, q in zip((1, 2, 4), rr, strict=True)}
    return {"N1": n1, "N2": n2}


def pine_numerics(x: list[float], flux: int, r: int) -> dict[str, Any]:
    runs = {dt: grade.pine_graded_run(x, flux, dt=dt) for dt in spec.N1_STEPS}
    f5, f25, f125 = (runs[d][1] for d in spec.N1_STEPS)
    c5, c25 = (cone.run_class(*runs[d]) for d in spec.N1_STEPS[:2])
    n1 = grade._n1(c5, c25, f5.get("t_ig"), f25.get("t_ig"), f25.get("first_peak"), f125.get("first_peak"))
    rr = [runs[spec.N1_STEPS[0]]] + [grade.pine_graded_run(x, flux, refine=m * r) for m in (2, 4)]
    n2 = n2_three([cone.run_class(*q) for q in rr], [q[1] for q in rr], cone.PINE_FEATURES)
    n2["features_by_refine"] = {str(m * r): {k: grade._num(q[1].get(k)) for k in cone.PINE_FEATURES} for m, q in zip((1, 2, 4), rr, strict=True)}
    return {"N1": n1, "N2": n2}


def gate2_pmma(r: int) -> dict[str, Any]:
    grade.LEDGER = grade.Ledger()
    sec = timed("pmma_section", grade.pmma_section, 0, numerics=False)
    num = {}
    for name, (_, graded) in grade.PMMA_GRADED.items():
        for fl in graded:
            num[f"{name}:{fl}"] = timed(f"pmma_numerics_{name}_{fl}", pmma_numerics, name, sec[name]["fit"]["x"], fl, r)
    n4 = timed("N4_pmma", grade.n4_pmma, sec["pmma_forward"]["fit"]["x"])
    return _gate2(sec, num, n4)


def gate2_pine(r: int) -> dict[str, Any]:
    grade.LEDGER = grade.Ledger()
    sec = timed("pine_section", grade.pine_section, 0, numerics=False)
    num = {str(fl): timed(f"pine_numerics_{fl}", pine_numerics, sec["fit"]["x"], fl, r) for fl in spec.PINE_GRADED_FLUXES}
    n4 = timed("N4_pine", grade.n4_pine, sec["fit"]["x"])
    return _gate2(sec, num, n4)


def _gate2(sec: dict[str, Any], num: dict[str, Any], n4: dict[str, Any]) -> dict[str, Any]:
    led = grade.LEDGER.summary()
    crit = {
        "N1": all(v["N1"]["pass"] for v in num.values()),
        "N2": all(v["N2"]["pass"] for v in num.values()),
        "N3": led["N3_pass"],
        "N4": n4["red"],
        "N5": led["N5_pass"],
        "N6": led["N6_pass"] and led["N6_every_line_needed"],
    }
    return {"section": sec, "numerics": num, "N4": n4, "N3_N5_N6": led, "criteria": crit,
            "pass_without_N8": all(crit.values()), "N8": "graded by `rerun1.py --check` (results_rerun1.md)"}


def features_only(mat: str, sec: dict[str, Any]) -> dict[str, Any]:
    """A stopped material (§4): its graded features, compared with no band."""
    if mat == "pmma":
        return {f"{n}:{fl}": {k: r["model"] for k, r in g["per_lab_DBI"].items()} for n in grade.PMMA_GRADED for fl, g in sec[n]["graded"].items()}
    return {fl: {k: r["model"] for k, r in g["envelope"].items()} for fl, g in sec["graded"].items()}


# ----- gate 3 -----
def gate3_pmma(g2: dict[str, Any]) -> dict[str, Any]:
    sec = g2["section"]
    p0 = {"graded_dt_0.5": timed("P0_0.5", verify.p0_all, 0.5, fds_h_r=True),
          "reported_dt_0.01": timed("P0_0.01", verify.p0_all, 0.01, fds_h_r=True)}
    s2 = {f"{n}:{fl}": g["S2"] for n in grade.PMMA_GRADED for fl, g in sec[n]["graded"].items()}
    n9 = timed("N9_pmma", grade.n9_pmma, sec["pmma_forward"]["fit"]["x"], sec["pmma_reverse"]["fit"]["x"], sec)
    flags = {n: sec[n]["fit"]["flags"] for n in grade.PMMA_GRADED}
    return {
        "P0": p0,
        "P1": {"forward_pass": sec["pmma_forward"]["pass"], "reverse_pass": sec["pmma_reverse"]["pass"],
               "pass": sec["pmma_forward"]["pass"] and sec["pmma_reverse"]["pass"]},
        "S2": {"rows": s2, "pass": all(v["falls"] is False for v in s2.values())},
        "N9": n9,
        "bound_flags": flags,
        "any_fit_at_bound": any(f["at_lower"] or f["at_upper"] for v in flags.values() for f in v),
    }


def gate3_pine(g2: dict[str, Any]) -> dict[str, Any]:
    sec = g2["section"]
    n9 = timed("N9_pine", grade.n9_pine, sec["fit"]["x"], {"pine": sec})
    flags = sec["fit"]["flags"]
    return {
        "P2": {"pass": sec["pass"]},
        "S1": {"pass": sec["S1_pass"], "rows": {fl: g["S1"] for fl, g in sec["graded"].items()}},
        "N9": n9,
        "bound_flags": flags,
        "any_fit_at_bound": any(f["at_lower"] or f["at_upper"] for f in flags),
        "outcome_12_m_ext_ge_m_flash": sec["outcome_12_m_ext_ge_m_flash"],
    }


def seeds_reported(mat: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for sd in (1, 2, 3, 4):
        if mat == "pmma":
            p = grade.pmma_section(sd, numerics=False)
            out[str(sd)] = {n: {"x": p[n]["fit"]["x"], "objective": p[n]["fit"]["objective"], "pass": p[n]["pass"]}
                            for n in grade.PMMA_GRADED} | {"graded": features_only("pmma", p)}
        else:
            q = grade.pine_section(sd, numerics=False)
            out[str(sd)] = {"x": q["fit"]["x"], "objective": q["fit"]["objective"], "pass": q["pass"], "graded": features_only("pine", q)}
    return out


# ----- outcomes (§5) -----
def outcomes(g1: dict[str, Any], status: dict[str, str], g3: dict[str, Any]) -> dict[str, Any]:
    """§5's R1-R7. Reading fixed before any run (disclosed): R4 is "P1's only miss is the reverse t_ig at 25 kW/m²";
    R5 is "any validation miss besides that one" (P0, the rest of P1, P2, S1, S2). Validation is P0, P1, P2, S1, S2;
    N9 is R7's and the bound flags R6's. With one material through gates 1-2 (R2), R3-R7 are evaluated on it alone."""
    passing = [m for m in MATERIALS if status[m] == "graded"]
    if not g1["N7_and_V_pass"] or not passing:
        return {"governing": "R1", "triggered": ["R1"], "graded_materials": passing}
    trig: list[str] = ["R2"] if len(passing) == 1 else []
    misses: list[str] = []
    p1_only_rev_tig = False
    if "pmma" in passing:
        p = g3["pmma"]
        misses += [k for k, ok in (("P0", p["P0"]["graded_dt_0.5"]["pass"]), ("S2", p["S2"]["pass"])) if not ok]
        rev = g3["pmma_section"]["pmma_reverse"]["graded"]["25"]
        rev_misses = [k for k, r in rev["per_lab_DBI"].items() if not r["in"]] + ([] if rev["envelope_t_ig_graded"]["in"] else ["t_ig_envelope"])
        fwd_ok = p["P1"]["forward_pass"]
        p1_only_rev_tig = fwd_ok and bool(rev_misses) and set(rev_misses) <= {"t_ig", "t_ig_envelope"}
        if not p["P1"]["pass"] and not p1_only_rev_tig:
            misses.append("P1")
    if "pine" in passing:
        q = g3["pine"]
        misses += [k for k, ok in (("P2", q["P2"]["pass"]), ("S1", q["S1"]["pass"])) if not ok]
    at_bound = any(g3[m]["any_fit_at_bound"] for m in passing) or ("pine" in passing and g3["pine"]["outcome_12_m_ext_ge_m_flash"])
    n9_flip = any(g3[m]["N9"]["outcome_9"] for m in passing)
    if not misses and not p1_only_rev_tig and not at_bound and not n9_flip:
        trig.append("R3")
    if p1_only_rev_tig:
        trig.append("R4")
    if misses:
        trig.append("R5")
    if at_bound:
        trig.append("R6")
    if n9_flip:
        trig.append("R7")
    gov = trig[0] if trig else "none"
    if gov == "R2" and len(trig) > 1:
        gov = f"R2 (graded material: {trig[1]})"
    return {"governing": gov, "triggered": trig, "graded_materials": passing, "validation_misses": misses,
            "P1_only_reverse_t_ig_25": p1_only_rev_tig}


# ----- the pipeline -----
def build() -> dict[str, Any]:
    src = inputs.fetch_all()
    materials.check_pmma_sets_agree()
    doc: dict[str, Any] = {
        "schema": "solid-spike-results-rerun1/1",
        "preregistration": "docs/design/research/solid_spike/preregistration_rerun1.md (de2290d); preregistration.md (65ee7d6)",
        "numerics": spec.NUMERICS,
        "inputs_sha256": src,
    }
    g1 = gate1()
    doc["gate1"] = g1
    status: dict[str, str] = {}
    g2: dict[str, Any] = {}
    for m in MATERIALS:
        if not g1["pass"][m]:
            status[m] = "stopped at gate 1"
            continue
        grade.REFINE[m] = int(g1["r_star"][m])
        g2[m] = gate2_pmma(grade.REFINE[m]) if m == "pmma" else gate2_pine(grade.REFINE[m])
        status[m] = "graded" if g2[m]["pass_without_N8"] else "stopped at gate 2"
    doc["gate2"] = {m: {k: v for k, v in g2[m].items() if k != "section"} | {"fits": _fit_summary(m, g2[m]["section"])} for m in g2}
    g3: dict[str, Any] = {}
    for m in g2:
        if status[m] != "graded":
            doc["gate2"][m]["graded_features_no_band"] = features_only(m, g2[m]["section"])
            continue
        g3[m] = gate3_pmma(g2[m]) if m == "pmma" else gate3_pine(g2[m])
        g3[f"{m}_section"] = g2[m]["section"]
        g3[f"{m}_seeds_1_4_reported"] = timed(f"seeds_{m}", seeds_reported, m)
    if status.get("pmma") == "graded" and status.get("pine") == "graded":
        g3["extras_reported"] = timed("extras", run.extras, g3["pmma_section"], g3["pine_section"], grade.REFINE["pmma"], grade.REFINE["pine"])
    doc["gate3"] = g3
    doc["status"] = status
    doc["refine"] = dict(grade.REFINE)
    doc["outcome"] = outcomes(g1, status, g3)
    fits = {}
    for p in sorted((OUT / "fit").glob("*_s*.json")):
        r = json.loads(p.read_text(encoding="utf-8"))
        TIMINGS_ACC[f"fit:{p.stem}"] = r.pop("timing_reported_only")
        fits[p.stem] = r
    doc["fits"] = fits
    return run.clean(doc)


def _fit_summary(mat: str, sec: dict[str, Any]) -> dict[str, Any]:
    if mat == "pmma":
        return {n: {"x": sec[n]["fit"]["x"], "objective": sec[n]["fit"]["objective"], "refine": sec[n]["fit"].get("refine"),
                    "fit_flux_features": sec[n]["fit_flux_features"]} for n in grade.PMMA_GRADED}
    return {"x": sec["fit"]["x"], "objective": sec["fit"]["objective"], "refine": sec["fit"].get("refine"),
            "fit_flux_features": sec["fit_flux_features"]}


def main(argv: list[str]) -> int:
    if spec.NUMERICS != "rerun1":
        raise RuntimeError("rerun1.py runs rerun 1's numerics only")
    grade.FIT_DIR = OUT / "fit"
    if argv[:1] == ["gate1"]:
        inputs.fetch_all()
        g = run.clean(gate1())
        GATE1.write_text(run.to_json(g), encoding="utf-8")
        log(f"gate1 written: N7_and_V {g['N7_and_V_pass']} pass {g['pass']} r* {g['r_star']}")
        return 0
    doc = build()
    text = run.to_json(doc)
    if "--check" in argv:
        (OUT / "results_rerun1_check.json").write_text(text, encoding="utf-8")
        same = RESULTS.read_text(encoding="utf-8") == text
        log(f"N8: rerun byte-identical: {same}")
        return 0 if same else 1
    RESULTS.write_text(text, encoding="utf-8")
    TIMINGS_ACC["total_cpu_s_this_process"] = time.process_time()
    TIMINGS.write_text(json.dumps(run.clean(TIMINGS_ACC), indent=1, sort_keys=True) + "\n", encoding="utf-8")
    log(f"results_rerun1.json written: outcome {doc['outcome']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
