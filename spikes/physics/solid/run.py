"""The solid spike, end to end after the fits: every criterion's numbers into `results.json` (§8).

    <python> fds_driver.py      # FDS 6.11.1 on the 11 pinned inputs (out/fds/, not committed)
    ./launch_fits.sh            # the 16 fits (out/fit/, not committed; their numbers are copied into results.json)
    <python> run.py             # V, P0, N7, grading, N1-N4, N9, seeds -> results.json (+ timings.json)
    <python> run.py --check     # recompute and fail unless results.json is byte-identical (N8)

Single-threaded (OMP/OPENBLAS/VECLIB/MKL_NUM_THREADS=1), no clock or randomness in the kernels; CPU times and load
averages go to `timings.json`, which N8 does not compare.
"""

from __future__ import annotations

import json
import math
import os
import re
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
import numpy as np
import spec
import verify

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results.json"
TIMINGS = HERE / "timings.json"
LOG = HERE / "out" / "run.log"


def log(msg: str) -> None:
    line = f"[cpu {time.process_time():8.1f}s load {os.getloadavg()[0]:.2f}] {msg}"
    print(line, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def clean(o: Any) -> Any:
    """JSON-safe, deterministic: numpy scalars to float, NaN/inf to strings, tuples to lists."""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (bool, np.bool_)):
        return bool(o)
    if isinstance(o, (int, np.integer)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        f = float(o)
        return f if math.isfinite(f) else str(f)
    return o


def fds_h_r_check() -> dict[str, Any]:
    """Our H_R(T) for NIST-StMU against the table FDS printed in its .out for each reaction."""
    text = (fds_driver.case_dir("R3") / f"{fds_driver.chid('R3')}.out").read_text(encoding="utf-8")
    blocks = re.findall(r"H_R \(kJ/kg\) TMP_REF,\s+(\d+) K:\s+([-0-9.E+]+)\s+(\d+) K:\s+([-0-9.E+]+)\s+(\d+) K:\s+([-0-9.E+]+)", text)
    b = materials.pmma_from_fds(inputs.fds_case("R3"), fds_h_r=True)
    rows = []
    for r, blk in zip(b.reactions, blocks, strict=True):
        for i in range(3):
            t, v = float(blk[2 * i]), float(blk[2 * i + 1])
            ours = (r.h + r.h_slope * (t - r.t_ref)) / 1e3
            rows.append({"T_K": t, "fds_kJ_kg": v, "ours_kJ_kg": ours, "rel": ours / v - 1})
    return {"rows": rows, "max_abs_rel": max(abs(x["rel"]) for x in rows), "t_ref_K": [r.t_ref for r in b.reactions]}


def apparent_lg(peaks: dict[int, float]) -> float:
    """1 / slope of peak m'' (g/m²s) against heater flux (kW/m²): kJ/g."""
    q = np.array(sorted(peaks), dtype=float)
    m = np.array([peaks[k] for k in sorted(peaks)])
    return float(1.0 / np.polyfit(q, m, 1)[0])


def extras(pm: dict[str, Any], pi: dict[str, Any], refine_pmma: int = 1, refine_pine: int = 1) -> dict[str, Any]:
    """Ungraded (§5 "also reported"): sustained flaming, the heater removed, apparent L_g, the Aalto + FZJ fit. Rerun 1
    passes its r* per material for the heater-removed runs."""
    out: dict[str, Any] = {}
    x_pm = pm["pmma_forward"]["fit"]["x"]
    peaks = {25: pm["pmma_forward"]["fit_flux_features"]["peak"]} | {
        int(k): v["per_lab_DBI"]["peak"]["model"] for k, v in pm["pmma_forward"]["graded"].items()
    }
    data = {f: cone.BANDS["pmma"]["per_lab"]["DBI_Lund"][str(f)]["peak"]["mean"] for f in (25, 50, 65)}
    out["apparent_L_g_kJ_g"] = {"model_forward": apparent_lg(peaks), "DBI_data": apparent_lg(data), "model_peaks": peaks, "data_peaks": data}
    removed: dict[str, Any] = {}
    for after in (60.0, 300.0):
        b = materials.pmma_cone(50, fds_h_r=True, refine=refine_pmma)
        p = fit.pmma_params(x_pm)
        import harness

        s = harness.cone(b, flux=50e3, flame=harness.Flame(p.q_fl, p.m_flash, None, cone.PMMA_DHC[25]), dt=spec.DT_SHIPPED,
                         t_end=spec.PMMA_T_CAP[50], stop_after_burnout=True, heater_off_after_flash=after)
        removed[f"pmma_fwd_50_off_{after:.0f}s_after_flash"] = {"note": "PMMA has no m''_ext (unset): it cannot go out", "flashes": s.flashes}
        bp = materials.pine_cone(50, k_c=pi["fit"]["x"][2], eps_char=pi["fit"]["x"][3], refine=refine_pine)
        q = fit.pine_params(pi["fit"]["x"])
        sp = harness.cone(bp, flux=50e3, flame=harness.Flame(q.q_fl, q.m_flash, cone.PINE_M_EXT, cone.PINE_DHC), dt=spec.DT_SHIPPED,
                          t_end=after + 900.0, stop_after_burnout=False, heater_off_after_flash=after)
        fl = np.array(sp.flaming)
        t = np.array(sp.t)
        t_out = next((float(t[i]) for i in range(1, fl.size) if fl[i - 1] and not fl[i]), None)
        t_flash = next((float(t[i]) for i in range(fl.size) if fl[i]), None)
        removed[f"pine_50_off_{after:.0f}s_after_flash"] = {
            "t_flash": t_flash,
            "t_flameout": t_out,
            "seconds_after_heater_off": None if t_out is None or t_flash is None else t_out - (t_flash + after),
        }
    out["heater_removed_prediction"] = removed
    out["time_to_sustained_flaming"] = "equal to t_ig in every run (one flash per part, N3); pine extinctions after flash are in S1"
    out["pine_node_convergence_50kW"] = {}
    for r in (1, 2, 4, 8):
        _, f = cone.pine_run(50, fit.pine_params(pi["fit"]["x"]), refine=r)
        out["pine_node_convergence_50kW"][f"refine_{r}"] = {k: f.get(k) for k in cone.PINE_FEATURES}
    try:
        af = grade.pine_section(0, numerics=False, name="pine_aalto_fzj")
        out["pine_aalto_fzj_fit_reported"] = {"x": af["fit"]["x"], "objective": af["fit"]["objective"],
                                              "graded": {k: {f: r["model"] for f, r in v["envelope"].items()} | {"pass_full_envelope": v["pass"]}
                                                         for k, v in af["graded"].items()}}
    except FileNotFoundError:
        out["pine_aalto_fzj_fit_reported"] = "not run"
    out["buwfd_variant"] = "not run: stage 0 has no BUWfd band (MaCFP-4 gives no area for it; §2 excludes it entirely)"
    return out


def build() -> tuple[dict[str, Any], dict[str, Any]]:
    timings: dict[str, Any] = {}

    def timed(name: str, fn: Any, *a: Any, **k: Any) -> Any:
        t0, l0 = time.process_time(), os.getloadavg()[0]
        log(f"{name}: start")
        r = fn(*a, **k)
        timings[name] = {"cpu_s": time.process_time() - t0, "load_start": l0, "load_end": os.getloadavg()[0]}
        log(f"{name}: done ({timings[name]['cpu_s']:.1f} s)")
        return r

    src = inputs.fetch_all()
    materials.check_pmma_sets_agree()
    doc: dict[str, Any] = {
        "schema": "solid-spike-results/1",
        "preregistration": "docs/design/research/solid_spike/preregistration.md (65ee7d6)",
        "inputs_sha256": src,
        "fds": {c: fds_driver.hashes(c) for c in inputs.FDS_CASES},
    }
    doc["fds_h_r_check"] = timed("fds_h_r_check", fds_h_r_check)
    doc["N7"] = timed("N7", closed_form.all_n7)
    doc["V_as_registered"] = timed("V_registered", verify.v_all, fds_h_r=False)
    doc["V_after_fix"] = timed("V_fixed", verify.v_all, fds_h_r=True)
    doc["P0"] = {
        "graded_dt_0.5": timed("P0_0.5", verify.p0_all, 0.5, fds_h_r=True),
        "reported_dt_0.01": timed("P0_0.01", verify.p0_all, 0.01, fds_h_r=True),
        "reported_as_registered_dt_0.5": timed("P0_registered", verify.p0_all, 0.5, fds_h_r=False),
    }
    pm = timed("P1", grade.pmma_section, 0, numerics=True)
    pi = timed("P2", grade.pine_section, 0, numerics=True)
    doc["P1"] = pm
    doc["P2"] = pi
    doc["N4"] = timed("N4", grade.n4, pm["pmma_forward"]["fit"]["x"], pi["fit"]["x"])
    doc["N9"] = timed("N9", grade.n9, pm["pmma_forward"]["fit"]["x"], pm["pmma_reverse"]["fit"]["x"], pi["fit"]["x"], {**pm, "pine": pi})
    doc["seeds_1_4_reported"] = timed("seeds", grade.seed_spread, (1, 2, 3, 4))
    doc["extras_reported"] = timed("extras", extras, pm, pi)
    doc["P1_as_registered_constant_H_reported"] = timed("P1_constH", grade.pmma_const_h_reported)
    doc["N3_N5_N6_over_graded_runs"] = grade.LEDGER.summary()
    fits = {}
    for p in sorted((HERE / "out" / "fit").glob("*_s*.json")):
        r = json.loads(p.read_text(encoding="utf-8"))
        timings[f"fit:{p.stem}"] = r.pop("timing_reported_only")
        fits[p.stem] = r
    doc["fits"] = fits
    return clean(doc), timings


def to_json(doc: dict[str, Any]) -> str:
    return json.dumps(doc, indent=1, sort_keys=True, allow_nan=False) + "\n"


def main(argv: list[str]) -> int:
    spec.NUMERICS = "run1"  # the first run's model (65ee7d6, 9575a44); rerun 1 is rerun1.py
    doc, timings = build()
    text = to_json(doc)
    if "--check" in argv:
        same = RESULTS.read_text(encoding="utf-8") == text
        log(f"N8: rerun byte-identical: {same}")
        (HERE / "out" / "results_rerun.json").write_text(text, encoding="utf-8")
        return 0 if same else 1
    RESULTS.write_text(text, encoding="utf-8")
    timings["total_cpu_s_this_process"] = time.process_time()
    TIMINGS.write_text(json.dumps(clean(timings), indent=1, sort_keys=True) + "\n", encoding="utf-8")
    log("results.json written")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
