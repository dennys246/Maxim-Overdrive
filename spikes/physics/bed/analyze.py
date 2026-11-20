"""Read results/*.json and print the Q1, Q2, Q4 and determinism verdicts (spike)."""

from __future__ import annotations

import glob
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TOL = {"t_crack": 0.15, "t_glow": 0.15, "t_gone": 0.10}


def load() -> dict[str, dict]:
    out = {}
    for f in sorted(glob.glob(os.path.join(HERE, "results", "*.json"))):
        with open(f) as fh:
            d = json.load(fh)
        out[d["name"]] = d
    return out


def num(x) -> float:
    return math.nan if x is None else float(x)


def q1(d: dict) -> dict:
    wood_out = num(d["wood_at_flameout_frac"])
    a = math.isfinite(num(d["t_ignite"])) and d["ignited_60s_after_pilot"] and wood_out < 0.05
    b = d["glow_longest_s"] >= 60.0
    c = math.isfinite(num(d["t_gone"])) and num(d["t_gone"]) <= 5400.0
    return {"1a": a, "1b": b, "1c": c}


def q2(times: dict[float, float], key: str) -> dict:
    t2, t1, t05 = times[0.2], times[0.1], times[0.05]
    res = {"t0.2": t2, "t0.1": t1, "t0.05": t05}
    if not all(math.isfinite(v) for v in (t2, t1, t05)):
        res.update(verdict_2a="MISS (time missing on some grid)", verdict_2b="MISS (no order)")
        return res
    tol = TOL[key] * t05
    e1, e2 = t1 - t05, t2 - t05
    ok = abs(e1) <= tol and (abs(e2) >= abs(e1) or abs(e1) <= tol / 4)
    res.update(e01=e1, e02=e2, tol=tol, verdict_2a="PASS" if ok else "MISS")
    d21, d1h = t2 - t1, t1 - t05
    if d21 * d1h > 0 and d1h != 0:
        p = math.log2(d21 / d1h)
        texact = t05 - d1h / (2**p - 1) if p != 0 else math.nan
        res.update(p=p, e01_richardson=t1 - texact, verdict_2b="PASS" if p > 0.5 else "MISS")
    else:
        res.update(
            p=math.nan,
            e01_richardson=math.nan,
            verdict_2b="MISS (differences change sign or vanish: no observed order)",
        )
    return res


def main() -> None:
    R = load()
    print("== runs ==")
    for n, d in R.items():
        print(
            f"{n:16s} dx={d['dx']:.2f} ign={num(d['t_ignite']):8.1f} crack={num(d['t_crack']):8.1f} "
            f"glow={num(d['t_glow']):8.1f} glowrun={d['glow_longest_s']:6.1f} gone={num(d['t_gone']):8.1f} "
            f"flameout={num(d['t_flameout']):7.1f} woodout={num(d['wood_at_flameout_frac']):.3f} "
            f"fuel_end={d['fuel_end_frac']:.3f} Tlay={d['t_layer_max_c']:7.1f} emb_pk={num(d['ember_peak_c']):7.1f} "
            f"emb_mn={num(d['ember_mean_c']):6.1f} rel={d['release_total_MJ']:6.1f} "
            f"Q1={q1(d)} led={d['ledger_worst_rel']:.1e} wall={d['wall_s']:.0f}s cpu={d['cpu_s']:.0f}s "
            f"load={d['loadavg_start'][0]:.0f}->{d['loadavg_end'][0]:.0f}"
        )
    print("\n== Q2 ==")
    sets = {sc: {0.2: f"{sc}_02", 0.1: f"{sc}_01", 0.05: f"{sc}_005"} for sc in ("F_nom", "S_nom", "B_nom")}
    sets["F_diff"] = {0.2: "F_diff_02", 0.1: "F_diff", 0.05: "F_diff_005"}
    sets["F_spec6d"] = {0.2: "F_spec6d_02", 0.1: "F_spec6d", 0.05: "F_spec6d_005"}
    for scen, names in sets.items():
        g = {dx: R.get(nm) for dx, nm in names.items()}
        if any(v is None for v in g.values()):
            print(scen, "incomplete:", [k for k, v in g.items() if v is None])
            continue
        for key in ("t_crack", "t_glow", "t_gone", "t_crack_rec", "t_glow_bright", "t_ignite"):
            k2 = key if key in TOL else ("t_crack" if "crack" in key else "t_glow" if "glow" in key else "t_crack")
            print(scen, key, q2({dx: num(v[key]) for dx, v in g.items()}, k2))
    print("\n== Q4 ==")
    worst = max(d["ledger_worst_rel"] for d in R.values())
    print("worst closure over all runs and steps:", worst)
    for n, d in R.items():
        if n in ("F_nom_005", "S_nom_005", "F_diff_005", "F_spec6d_005", "F_diff", "F_spec6d"):
            print(n, {k: ("RED" if v > 0.01 else "green") + f" {v:.3g}" for k, v in d["ledger_deletion"].items()})
    print("\n== determinism ==")
    a, b = R.get("F_nom_01"), R.get("F_nom_01_rerun")
    if a and b:
        print(
            "F_nom_01 digest", a["digest"], "\nrerun   digest", b["digest"], "\nidentical:", a["digest"] == b["digest"]
        )


if __name__ == "__main__":
    main()
