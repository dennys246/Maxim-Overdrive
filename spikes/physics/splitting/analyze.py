"""Score Q3's criteria from results/*.json. Asserts 3b's bit-identity (the preregistration's determinism rule).

.venv/bin/python spikes/physics/splitting/analyze.py
"""

from __future__ import annotations

import json
from pathlib import Path

RESULTS = Path(__file__).resolve().parent / "results"
GRIDS = ("0.2", "0.1", "0.05")
SCENARIOS = ("pilot", "established")


def load(name: str) -> dict | None:
    p = RESULTS / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def rel(a: int | None, b: int | None) -> float | None:
    if a is None or b is None:
        return None
    return (a - b) / b


def fmt(x: float | None) -> str:
    return "undefined" if x is None else f"{100 * x:+.2f}%"


def secs(t: int | None) -> str:
    return "none" if t is None else f"{t / 10:.1f}"


def within_5pct(eg: float | None, eo: float | None) -> bool:
    return eg is not None and eo is not None and abs(eg) <= 0.05 and abs(eo) <= 0.05


def section_3a(lines: list[str]) -> bool:
    ok = True
    lines.append("## 3a stability")
    for scen in SCENARIOS:
        for g in GRIDS:
            for kind in ("lie_fwd_t1", "strang_fwd", "lie_rev", "strang_rev", "lie_fwd_ref10", "strang_fwd_ref10"):
                r = load(f"{scen}_{g}_{kind}")
                if r is None:
                    lines.append(f"- MISSING {scen}_{g}_{kind}")
                    ok = False
                    continue
                bad = r["bound_failures"]
                ok &= not bad
                lines.append(
                    f"- {scen} {g} {kind}: bounds {bad if bad else 'ok'}; audit violations "
                    f"{r.get('audit_violations')}, worst dt/bound {r.get('worst_audit_ratio', 0):.3f}; "
                    f"peak skin {r['peak_skin_c']:.0f} C; substeps {r['substeps_hist']}; "
                    f"ledger closure {r['ledger_worst_rel_closure']:.1e}; wall {r['wall_s']} s"
                )
    return ok


def section_3b(lines: list[str]) -> bool:
    ok = True
    lines.append("\n## 3b determinism")
    for scen in SCENARIOS:
        for g in GRIDS:
            hs = {k: (load(f"{scen}_{g}_lie_fwd_{k}") or {}).get("hash") for k in ("t1", "t1_rerun", "t8", "unset")}
            same = None not in hs.values() and len(set(hs.values())) == 1
            ok &= same
            lines.append(f"- {scen} {g}: {'IDENTICAL' if same else 'DIFFER'} {hs}")
    return ok


def common_reference_line(scen: str, g: str) -> str | None:
    s_ref = load(f"{scen}_{g}_strang_fwd_ref10")
    lie = load(f"{scen}_{g}_lie_fwd_t1")
    lref = load(f"{scen}_{g}_lie_fwd_ref10")
    if not (s_ref and lie and lref):
        return None
    return (
        "  - vs Strang x10 as the common reference: Lie base t_glow "
        f"{fmt(rel(lie['t_glow'], s_ref['t_glow']))}, "
        f"t_gone {fmt(rel(lie['t_gone'], s_ref['t_gone']))}; Lie x10 t_glow "
        f"{fmt(rel(lref['t_glow'], s_ref['t_glow']))}, t_gone {fmt(rel(lref['t_gone'], s_ref['t_gone']))}"
    )


def section_3c(lines: list[str]) -> bool:
    ok = True
    lines.append("\n## 3c splitting error (base vs 10x substeps, same scheme) and Lie vs Strang")
    for scen in SCENARIOS:
        for g in GRIDS:
            for scheme in ("lie", "strang"):
                b, r = (
                    load(f"{scen}_{g}_{scheme}_fwd" + ("_t1" if scheme == "lie" else "")),
                    load(f"{scen}_{g}_{scheme}_fwd_ref10"),
                )
                if b is None or r is None:
                    lines.append(f"- MISSING {scen} {g} {scheme}")
                    ok = False
                    continue
                eg, eo = rel(b["t_glow"], r["t_glow"]), rel(b["t_gone"], r["t_gone"])
                passed = within_5pct(eg, eo)
                if scheme == "lie":
                    ok &= passed
                lines.append(
                    f"- {scen} {g} {scheme}: t_glow {secs(b['t_glow'])} vs ref {secs(r['t_glow'])} "
                    f"({fmt(eg)}); t_gone {secs(b['t_gone'])} vs ref {secs(r['t_gone'])} ({fmt(eo)}); "
                    f"t_ignite {secs(b['t_ignite'])} vs {secs(r['t_ignite'])} -> "
                    f"{'PASS' if passed else 'MISS'}"
                )
            common = common_reference_line(scen, g)
            if common is not None:
                lines.append(common)
    return ok


def section_3d(lines: list[str]) -> bool:
    ok = True
    lines.append("\n## 3d order sensitivity (reverse vs forward)")
    for scen in SCENARIOS:
        for g in GRIDS:
            for scheme, fwd in (("lie", "lie_fwd_t1"), ("strang", "strang_fwd")):
                f, rv = load(f"{scen}_{g}_{fwd}"), load(f"{scen}_{g}_{scheme}_rev")
                if f is None or rv is None:
                    lines.append(f"- MISSING {scen} {g} {scheme}")
                    continue
                eg, eo = rel(rv["t_glow"], f["t_glow"]), rel(rv["t_gone"], f["t_gone"])
                passed = within_5pct(eg, eo)
                if scheme == "lie":
                    ok &= passed
                lines.append(
                    f"- {scen} {g} {scheme}: t_glow {secs(f['t_glow'])} -> {secs(rv['t_glow'])} ({fmt(eg)}); "
                    f"t_gone {secs(f['t_gone'])} -> {secs(rv['t_gone'])} ({fmt(eo)}); peak skin "
                    f"{f['peak_skin_c']:.0f} -> {rv['peak_skin_c']:.0f} C -> {'PASS' if passed else 'MISS'}"
                )
    return ok


def section_3d_followup(lines: list[str]) -> None:
    lines.append("\n## 3d follow-up: reversed order against its own 10x reference (is the flip a splitting artifact?)")
    for scen in SCENARIOS:
        for g in ("0.2", "0.1"):
            for scheme, base in (("lie", "lie_rev"), ("strang", "strang_rev")):
                b, r = load(f"{scen}_{g}_{base}"), load(f"{scen}_{g}_{scheme}_rev_ref10")
                if b is None or r is None:
                    continue
                lines.append(
                    f"- {scen} {g} {scheme} reverse: released {b['ledger'].get('combustion', 0) / 1e6:.0f} MJ "
                    f"vs x10 {r['ledger'].get('combustion', 0) / 1e6:.0f} MJ; fuel left {b['fuel_end_kg']:.2f} vs "
                    f"{r['fuel_end_kg']:.2f} kg; t_glow {fmt(rel(b['t_glow'], r['t_glow']))}; "
                    f"t_gone {fmt(rel(b['t_gone'], r['t_gone']))}"
                )


def main() -> None:
    lines: list[str] = []
    ok3a = section_3a(lines)
    ok3b = section_3b(lines)
    ok3c = section_3c(lines)
    ok3d = section_3d(lines)
    section_3d_followup(lines)
    lines.append(
        f"\nSUMMARY 3a {'PASS' if ok3a else 'MISS'}, 3b {'PASS' if ok3b else 'MISS'}, "
        f"3c(Lie) {'PASS' if ok3c else 'MISS'}, 3d(Lie) {'PASS' if ok3d else 'MISS'}"
    )
    text = "\n".join(lines)
    print(text)
    (RESULTS / "summary.md").write_text(text + "\n")
    assert ok3b, "3b: runs that must be bit-identical are not"


if __name__ == "__main__":
    main()
