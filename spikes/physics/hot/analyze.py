"""Grade every hot-surface run against the preregistered criteria (§3) and print the tables results.md quotes.

Usage: analyze.py > results/analysis.txt   (reads results/*.json here and the parents' committed JSONs; spike).
"""

from __future__ import annotations

import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
GRIDS = ("02", "01", "005")
ENDS = ("kc07", "kcec5", "rhoc200", "tf288", "tf380", "tfl520", "tfl1027", "mz", "eps85", "eps95", "qf15", "qf35")
ZERO = {
    "Z_S_02": ("bed", "S_nom_02", "digest_bed"),
    "Z_S_01": ("bed", "S_nom_01", "digest_bed"),
    "Z_F_02": ("bed", "F_nom_02", "digest_bed"),
    "Z_F_01": ("bed", "F_nom_01", "digest_bed"),
    "Z_B_01": ("bed", "B_nom_01", "digest_bed"),
    "Z_N_02": ("accelerant", "N_02", "digest_wet"),
    "Z_N_01": ("accelerant", "N_01", "digest_wet"),
}


def load(name: str, where: str = RES) -> dict | None:
    path = os.path.join(where, f"{name}.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def num(x) -> float:
    return math.nan if x is None else float(x)


def fmt(x, nd: int = 1) -> str:
    x = num(x) if not isinstance(x, bool) else x
    if isinstance(x, bool):
        return "PASS" if x else "MISS"
    return "—" if not math.isfinite(x) else f"{x:.{nd}f}"


def classes(c: dict, scen: str) -> tuple:
    if scen == "F":
        return (c["C_F"], c["spread_class"])
    return (c["B1"], c["B2"], c["C"], c["spread_class"])


def rule_2a(t: dict[str, float]) -> tuple[bool, str]:
    """The physics spike's 2a rule at tol = 15 %; a time missing on any grid is a miss."""
    if not all(math.isfinite(t[g]) for g in GRIDS):
        return False, "missing on a grid"
    ref = t["005"]
    tol = 0.15 * abs(ref)
    e1, e2 = t["01"] - ref, t["02"] - ref
    ok = abs(e1) <= tol and (abs(e2) >= abs(e1) or abs(e1) <= tol / 4)
    return ok, f"e0.1={e1:+.1f} e0.2={e2:+.1f} tol={tol:.1f}"


def order(t: dict[str, float]) -> str:
    if not all(math.isfinite(t[g]) for g in GRIDS):
        return "p undefined (missing)"
    d1, d2 = t["02"] - t["01"], t["01"] - t["005"]
    if d2 == 0 or d1 == 0 or d1 / d2 <= 0:
        return f"p undefined (differences {d1:+.1f}, {d2:+.1f}): MISS"
    p = math.log2(d1 / d2)
    rich = t["01"] - (t["005"] - d2 / (2**p - 1)) if p != 0 else math.nan
    return f"p={p:.2f} Richardson e0.1={rich:+.1f}: {'PASS' if p > 0.5 else 'MISS'}"


def section_nominal(prefix: str, title: str) -> None:
    print(f"\n## {title}")
    print("scen grid | lam_max class | lam_w | B1 B2 C C_F | t_ign t_B t_L95 t_out | wood_out | peak kW | O2>sup | cpu")
    for scen in ("S", "K", "F", "B"):
        for g in GRIDS:
            name = f"{scen}{prefix}_{g}"
            r = load(name)
            if r is None:
                continue
            c, rep = r["criteria"], r["reported"]
            print(
                f"{scen} {g:>4} | {c['lambda_max']:.4f} {c['spread_class']:7} | {c['lambda_w_max']:.4f} | "
                f"{fmt(c['B1'])} {fmt(c['B2'])} {fmt(c['C'])} {fmt(c['C_F'])} | {fmt(c['t_ignite'])} "
                f"{fmt(c['t_B'])} {fmt(c['t_L95'])} {fmt(c['t_out'])} | {c['wood_at_out_frac']:.4f} | "
                f"{rep['peak_qdot_kW']:.1f} | {rep['o2_over_frac_flaming']:.3f} | {r['cpu_s']:.0f}"
            )


def section_d(prefix: str) -> None:
    print(f"\n## D1-D3, arm '{prefix or 'H1'}'")
    for scen in ("S", "K", "F"):
        runs = {g: load(f"{scen}{prefix}_{g}") for g in GRIDS}
        if any(v is None for v in runs.values()):
            continue
        cl = {g: classes(runs[g]["criteria"], scen) for g in GRIDS}
        same = len(set(cl.values())) == 1
        print(f"{scen} D1 classes {cl} -> {'PASS' if same else 'MISS'}")
        keys = ["t_ignite", "t_B", "t_out"] + (["t_L95"] if scen == "K" else [])
        if scen == "F":
            keys = ["t_out"]
        for key in keys:
            t = {g: num(runs[g]["criteria"][key]) for g in GRIDS}
            ok, how = rule_2a(t)
            print(f"  D2 {key}: {[fmt(t[g]) for g in GRIDS]} {how} -> {'PASS' if ok else 'MISS'}; D3 {order(t)}")
        for key in ("lambda_max", "lambda_w_max"):
            a, b = runs["01"]["criteria"][key], runs["005"]["criteria"][key]
            print(f"  D2 {key}: 0.1 {a:.4f} vs 0.05 {b:.4f} -> {'PASS' if abs(a - b) <= 0.05 else 'MISS'}")


def section_e() -> None:
    print("\n## E1, E2 (all non-zero-change runs)")
    worst, dele = 0.0, {}
    for f in sorted(os.listdir(RES)):
        if not f.endswith(".json") or f.startswith("Z_"):
            continue
        r = load(f[:-5])
        worst = max(worst, r["ledger"]["E1_worst_rel"])
        for k, v in r["ledger"]["E2_deletion"].items():
            if v > dele.get(k, (0.0, ""))[0]:
                dele[k] = (v, f[:-5])
    print(f"E1 worst |in - dstored - out| / release: {worst:.2e} -> {'PASS' if worst <= 0.01 else 'MISS'}")
    for k in ("removed_with_mass", "open_air_draught", "plume_convective", "d_skins"):
        v, n = dele.get(k, (0.0, ""))
        print(f"E2 delete {k}: worst {v:.4f} ({n}) -> {'RED' if v > 0.01 else 'green'}")


def section_e4() -> None:
    print("\n## E4 zero-change digests")
    for name, (parent, pname, key) in ZERO.items():
        r = load(name)
        ref = load(pname, os.path.join(HERE, "..", parent, "results"))
        if r is None or ref is None:
            print(f"{name}: missing")
            continue
        ok = r[key] == ref["digest"]
        print(f"{name} {r[key][:16]} vs {parent}/{pname} {ref['digest'][:16]} -> {'PASS' if ok else 'MISS'}")


def section_e5() -> None:
    print("\n## E5")
    for scen in ("S", "K"):
        a, b, c = load(f"{scen}_01"), load(f"{scen}_01_rerun"), load(f"{scen}_01_sub10")
        if a and b:
            print(
                f"{scen} rerun digest {a['digest'][:16]} vs {b['digest'][:16]} -> "
                f"{'PASS' if a['digest'] == b['digest'] else 'MISS'}"
            )
        if a and c:
            ca, cc = classes(a["criteria"], scen), classes(c["criteria"], scen)
            print(
                f"{scen} 10x substeps classes {cc} vs {ca} -> {'PASS' if ca == cc else 'MISS'}; "
                f"lam {c['criteria']['lambda_max']:.4f} vs {a['criteria']['lambda_max']:.4f}, "
                f"t_out {fmt(c['criteria']['t_out'])} vs {fmt(a['criteria']['t_out'])}"
            )


def section_g() -> None:
    print("\n## G range ends at 0.1 m")
    for scen in ("S", "K", "F"):
        nom = load(f"{scen}_01")
        if nom is None:
            continue
        cn = classes(nom["criteria"], scen)
        for e in ENDS:
            r = load(f"{scen}_{e}_01")
            if r is None:
                continue
            c = r["criteria"]
            ce = classes(c, scen)
            print(
                f"{scen} {e:8} classes {ce} lam {c['lambda_max']:.4f} t_out {fmt(c['t_out'])} "
                f"wood_out {c['wood_at_out_frac']:.4f} -> {'same' if ce == cn else 'FLIPS'}"
            )


def section_reported() -> None:
    print("\n## Reported (H1 and H2 nominal, B, deviation)")
    keys = (
        "tc_fl_mean_median",
        "tc_fl_env_median",
        "tc_fl_int_median",
        "tc_fl_max_peak",
        "gas_exit_mean_median",
        "gas_exit_max_peak",
        "t_glow",
        "glow_longest_s",
        "glow_area_max",
        "ember_peak_c",
        "E_wood_flaming_MJ",
        "E_accelerant_MJ",
        "E_char_MJ",
        "fuel_end_frac",
        "t_peak_qdot",
    )
    for f in sorted(os.listdir(RES)):
        if not f.endswith(".json") or f.startswith("Z_") or "_01_" in f:
            continue
        r = load(f[:-5])
        rep = r["reported"]
        vals = " ".join(f"{k}={fmt(rep.get(k), 1)}" for k in keys)
        print(f"{f[:-5]}: {vals} probe={rep.get('probe')}")
        print(f"   lambda_t={ {k: round(v, 4) for k, v in rep['lambda_t'].items()} }")


def main() -> None:
    section_nominal("", "H1 nominal")
    section_nominal("2", "H2 (in-cell contact)")
    section_nominal("dev817", "Deviation: T_fl = 817 C (McCaffrey Table 1)")
    section_nominal("surf", "Attribution: surface change only")
    section_nominal("gas", "Attribution: gas change only")
    for prefix in ("", "2", "dev817"):
        section_d(prefix)
    section_e()
    section_e4()
    section_e5()
    section_g()
    section_reported()


if __name__ == "__main__":
    main()
