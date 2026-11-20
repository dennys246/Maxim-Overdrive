"""Print results/results.json as Markdown tables (for body.md). Run after run.py."""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = json.loads((HERE / "results" / "results.json").read_text())


def fmt_t(t, phase_s):
    if t is None or t == "None":
        return "never"
    return f"{t:.0f}" if t >= 10 else f"{t:.1f}"


def pain_cell(sk, phase_s):
    lo = sk["t_pain"]["43.0C"]
    hi = sk["t_pain"]["44.8C"]
    a, b = fmt_t(lo, phase_s), fmt_t(hi, phase_s)
    cell = a if a == b else f"{a}\N{EN DASH}{b}"
    return cell


def case_keys(rows: list[dict]) -> list[tuple]:
    """(phase, case, model) in first-seen order."""
    keys = []
    for r in rows:
        k = (r["phase"], r["case"], r["model"])
        if k not in keys:
            keys.append(k)
    return keys


def axis_row(rows: list[dict], d: float, k: tuple) -> dict:
    return next(x for x in rows if x["ref"] == "axis" and x["d"] == d and (x["phase"], x["case"], x["model"]) == k)


def print_flux(rows: list[dict], keys: list[tuple]) -> None:
    print("## Flux (kW/m^2 at the worst body height / body mean), distance from crate axis\n")
    print("| phase | case | model | 1 m | 2 m | 3 m |")
    print("|---|---|---|---|---|---|")
    for k in keys:
        cells = []
        for d in (1.0, 2.0, 3.0):
            r = axis_row(rows, d, k)
            cells.append(f"{r['q_max']:.1f} / {r['q_mean']:.1f}")
        print(f"| {k[0]} | {k[1]} | {k[2]} | " + " | ".join(cells) + " |")


def print_pain_rows(sub: list[dict], k: tuple) -> None:
    for cname in sub[0]["skin"]:
        cells = []
        for d in (1.0, 2.0, 3.0):
            r = next(x for x in sub if x["d"] == d)
            cells.append(pain_cell(r["skin"][cname], r["phase_s"]))
        r1 = next(x for x in sub if x["d"] == 1.0)
        b2 = r1["skin"][cname]["t_burn2"]
        print(f"| {k[0]} | {k[1]} | {k[2]} | {cname} | " + " | ".join(cells) + f" | {fmt_t(b2, r1['phase_s'])} |")


def print_pain(rows: list[dict], keys: list[tuple]) -> None:
    for ref in ("axis", "face"):
        print(f"\n## Time to pain, s (43.0\N{EN DASH}44.8 degC at 0.1 mm), distance from crate {ref}\n")
        print("| phase | case | model | clothing | 1 m | 2 m | 3 m | 2nd-degree burn at 1 m |")
        print("|---|---|---|---|---|---|---|---|")
        for k in keys:
            sub = [x for x in rows if x["ref"] == ref and (x["phase"], x["case"], x["model"]) == k]
            if not sub or not sub[0]["skin"]:
                continue
            print_pain_rows(sub, k)


def print_core(rows: list[dict], keys: list[tuple]) -> None:
    print("\n## Core (T5 lump), K/min gross / net of spec losses, c = 3470 (2980)\n")
    print("| phase | case | model | 1 m | 2 m | 3 m |")
    print("|---|---|---|---|---|---|")
    for k in keys:
        cells = []
        for d in (1.0, 2.0, 3.0):
            c = axis_row(rows, d, k)["core"]
            cells.append(
                f"{c['gross_K_per_min[c=3470]']:+.2f} ({c['gross_K_per_min[c=2980]']:+.2f}) / "
                f"{c['net_K_per_min[c=3470]']:+.2f}"
            )
        print(f"| {k[0]} | {k[1]} | {k[2]} | " + " | ".join(cells) + " |")


def main() -> None:
    rows = R["results"]["rows"]
    keys = case_keys(rows)
    print_flux(rows, keys)
    print_pain(rows, keys)
    print_core(rows, keys)
    print("\n## Validations\n")
    print(json.dumps(R["validations"], indent=1))
    print("\n", R["determinism"])


if __name__ == "__main__":
    main()
