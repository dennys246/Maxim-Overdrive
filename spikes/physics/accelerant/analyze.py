"""Grade every preregistered criterion from results/*.json and print the tables results.md quotes (spike)."""

from __future__ import annotations

import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
CLASSES = ("A", "B1", "B2", "C")
TIMES = ("t_A", "t_B", "t_L95", "t_out")
ENDS = (
    "L32_01",
    "L96_01",
    "Surf_01",
    "Tb175_01",
    "Tb325_01",
    "Qc25_01",
    "Qc393_01",
    "Qmass_01",
    "Chir27_01",
    "Chir33_01",
    "Chir35_01",
    "Qf15_01",
    "Qf35_01",
    "P1_01",
)


def load(name: str) -> dict:
    with open(os.path.join(RES, f"{name}.json")) as f:
        return json.load(f)


def verdict(ok: bool) -> str:
    return "PASS" if ok else "MISS"


def fmt(x) -> str:
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "none"
    return f"{x:.4g}" if isinstance(x, float) else str(x)


def classes(r: dict) -> tuple[bool, ...]:
    return tuple(bool(r["criteria"][k]) for k in CLASSES)


def conv_2a(v02, v01, v005) -> tuple[bool, str]:
    vals = (v02, v01, v005)
    if any(v is None or not math.isfinite(v) for v in vals):
        return False, "missing on a grid"
    tol = 0.15 * abs(v005)
    e01, e02 = v01 - v005, v02 - v005
    ok = abs(e01) <= tol and (abs(e02) >= abs(e01) or abs(e01) <= tol / 4)
    return ok, f"e0.1 = {e01:+.4g} (tol {tol:.4g}), e0.2 = {e02:+.4g}"


def order_p(v02, v01, v005) -> tuple[bool, str]:
    if any(v is None or not math.isfinite(v) for v in (v02, v01, v005)):
        return False, "missing on a grid"
    d1, d2 = v02 - v01, v01 - v005
    if d2 == 0 or d1 / d2 <= 0:
        return False, f"differences {d1:+.4g}, {d2:+.4g}: sign change or zero"
    p = math.log2(d1 / d2)
    rich = v01 - (v005 - d2 / (2**p - 1)) if p != 0 else math.nan
    return p > 0.5, f"p = {p:.3f}, Richardson e0.1 = {rich:+.4g} against measured {d2:+.4g}"


def grids() -> None:
    rs = {g: load(f"N_{g}") for g in ("02", "01", "005")}
    print("## Nominal at each grid")
    for g, r in rs.items():
        c = r["criteria"]
        print(
            f"{g}: " + ", ".join(f"{k} {verdict(c[k])}" for k in CLASSES),
            "|",
            ", ".join(
                f"{k} {fmt(c[k])}"
                for k in ("t_A", "lambda_max", "t_L95", "lambda_w_tL95", "lambda_w_max", "t_B", "t_out")
            ),
            f"| wood at flame-out {c['wood_at_out_frac']:.4f} | cpu {r['cpu_s']:.0f} s wall {r['wall_s']:.0f} s",
        )
    same = len({classes(r) for r in rs.values()}) == 1
    print(f"D1 class identical across grids: {verdict(same)}")
    print("D2 / D3:")
    for k in TIMES:
        v = [rs[g]["criteria"][k] for g in ("02", "01", "005")]
        ok, txt = conv_2a(*v)
        ok3, txt3 = order_p(*v)
        print(f"  {k}: {fmt(v[0])} / {fmt(v[1])} / {fmt(v[2])}: 2a {verdict(ok)} ({txt}); p {verdict(ok3)} ({txt3})")
    for k in ("lambda_max", "lambda_w_tL95"):
        d = abs(rs["01"]["criteria"][k] - rs["005"]["criteria"][k])
        print(f"  {k} at 0.1 vs 0.05: |diff| = {d:.2e}: {verdict(d <= 0.05)}")


def ledger() -> None:
    names = sorted(f[:-5] for f in os.listdir(RES) if f.endswith(".json"))
    worst = max(load(n)["ledger"]["E1_worst_rel"] for n in names)
    liq = max(load(n)["ledger"]["E3_liquid_worst_rel"] for n in names)
    print(f"## E1 worst closure over {len(names)} runs: {worst:.2e} ({verdict(worst <= 0.01)})")
    print(f"## E3 liquid mass worst: {liq:.2e} ({verdict(liq <= 1e-9)})")
    lines = ("combustion_accelerant", "vapour_unburnt", "liquid_sensible")
    for line in lines:
        best = max(
            ((load(n)["ledger"]["E2_deletion"].get(line, 0.0), n) for n in names),
            key=lambda x: x[0],
        )
        print(f"E2 delete {line}: largest residual {best[0]:.3g} ({best[1]}): {verdict(best[0] > 0.01)}")


def determinism() -> None:
    a, b, s = load("N_01"), load("N_01_rerun"), load("N_01_sub10")
    print(f"## E5 rerun bit-identical: {verdict(a['digest'] == b['digest'])}")
    print(f"E5 10x substeps classes {classes(s)} vs {classes(a)}: {verdict(classes(s) == classes(a))}")
    print("   10x:", {k: fmt(s["criteria"][k]) for k in ("t_A", "lambda_max", "t_out", "wood_at_out_frac")})


def ends() -> None:
    nom = classes(load("N_01"))
    print("## F: range ends at 0.1 m")
    allok = True
    for n in ENDS:
        r = load(n)
        c = r["criteria"]
        ok = classes(r) == nom
        allok &= ok
        print(
            f"{n}: {verdict(ok)} classes {classes(r)} | t_A {fmt(c['t_A'])} lambda_max {c['lambda_max']:.4f} "
            f"t_out {fmt(c['t_out'])} wood {c['wood_at_out_frac']:.4f} | peak {r['reported']['peak_qdot_kW']:.0f} kW"
        )
    print(f"F overall: {verdict(allok)}")


def main() -> None:
    grids()
    ledger()
    determinism()
    ends()


if __name__ == "__main__":
    main()
