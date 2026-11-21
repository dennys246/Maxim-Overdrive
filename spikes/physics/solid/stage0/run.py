"""Stage 0 of the solid spike: MaCFP's raw cone and gasification data -> the pre-registered feature bands.

    <python> spikes/physics/solid/stage0/run.py          # fetch (once) into cache/, compute, write, check
    <python> spikes/physics/solid/stage0/run.py --check  # recompute and fail unless bands.json/.md are unchanged

Writes `bands.json` and `bands.md` beside this file. Single-threaded and deterministic: no clock, no randomness.
Exits 1 if any pre-registered reference value is not reproduced (the outputs are still written: a mismatch is
reported, never adjusted), or, with --check, if a rerun would change either file.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path
from typing import Any

import compute
import fetch
import pins
import reference
import report
import selection

HERE = Path(__file__).resolve().parent


def build() -> tuple[dict[str, Any], list[str]]:
    """Every band, its source hashes and the reference checks; plus the data findings for bands.md."""
    files = fetch.fetch_all()
    cone = sorted(p for p in files if p.lower().endswith(".csv"))
    pmma_tests = selection.load_pmma([p for p in cone if p.startswith(pins.PMMA_CONE_DIR)])
    pine_tests = selection.load_pine([p for p in cone if p.startswith(pins.WOOD_CONE_DIR)])
    readmes = {p: fetch.cache_path(p).read_text(encoding="utf-8") for p in pins.READMES}
    doc: dict[str, Any] = {
        "schema": "solid-spike-stage0/1",
        "source": {"repo": pins.REPO, "commit": pins.COMMIT, "files": files},
        "rules": {
            "q_ign_kw_m2": pins.Q_IGN,
            "tol_time_s": pins.TOL_TIME,
            "tol_rel": pins.TOL_REL,
            "dhc_rule_kj_g": list(pins.DHC_RULE),
            "artefact_factor": pins.ARTEFACT_FACTOR,
            "unit_errata": {f"{k[0]} column {k[1]}": v[2] for k, v in pins.UNIT_ERRATA.items()},
            "interpretations": list(report.INTERPRETATIONS),
        },
        "pmma": compute.pmma_section(pmma_tests),
        "pine": compute.pine_section(pine_tests, readmes),
        "gasification": compute.gasification_section(),
    }
    doc = json.loads(report.to_json(doc))  # checks and tables read the rounded values bands.json carries
    doc["reference_checks"] = reference.all_checks(doc["pmma"], doc["pine"], doc["gasification"])
    return doc, findings(doc)


def findings(doc: dict[str, Any]) -> list[str]:
    """Mismatches first, then what the data show that a reader of the bands must know."""
    notes = [
        f"**MISMATCH:** {c['check']}: pre-registered {report.fmt(c['preregistered'])}, computed "
        f"{report.fmt(c['computed'])} (difference {report.fmt(c['difference'])}). Reported, not adjusted. {c['note']}"
        for c in doc["reference_checks"]
        if not c["match"]
    ]
    for (stem, col), (_, label, why) in pins.UNIT_ERRATA.items():
        notes.append(f"{stem} labels column {col} [{label}]; read as kW/m²: {why}.")
    for name, t in doc["pine"]["tests"].items():
        f = t["features"]
        if f.get("plateau_cut_by_window"):
            notes.append(
                f"{name}: the window ends at {report.fmt(f['window_end'], 0)} s (t_ig {report.fmt(f['t_ig'], 0)}"
                f" s), cutting the plateau window; plateau {report.fmt(f['plateau'])} as the rule gives it, "
                f"{report.fmt(f['plateau_uncut_reported_only'])} uncut (reported only, not a band)."
            )
        elif f.get("first_peak") is not None and f.get("window_end") is None:
            notes.append(
                f"{name}: m''_60 never falls below 2.7 g/m²s after the first peak; its window runs to the record's end."
            )
    notes += outlying_lab_means(doc)
    return notes + m_ext_notes(doc["pine"]["m_ext"]) + gasif_notes(doc["gasification"])


def gasif_notes(gas: dict[str, Any]) -> list[str]:
    """P0 grades back-T crossings "where recorded": name the repeats whose record ends before a crossing."""
    short = [
        f"{k} (ends {report.fmt(v['t_end'], 0)} s at {report.fmt(v['back_T_end_C'], 0)} °C)"
        for k, v in gas["repeats"].items()
        if "t_end" in v and v.get("t_back_300C") is None
    ]
    return [
        f"P0 back T: these records end before 300 °C, so their later crossings are not recorded: {', '.join(short)}."
    ]


def m_ext_notes(m: dict[str, Any]) -> list[str]:
    """Why m''_ext has the value it has, when any fit-flux flame-out gives no m''_60."""
    missing = {k: v for k, v in m["tests"].items() if v["m60"] is None}
    if not missing:
        return []
    gaps = [v["t_record_end"] - v["t_flameout"] for v in missing.values() if v.get("t_record_end") is not None]
    last = [
        v["m60_at_record_end_minus_30s_reported_only"]
        for v in missing.values()
        if v.get("m60_at_record_end_minus_30s_reported_only") is not None
    ]
    head = (
        f"**m''_ext falls back to {report.fmt(m['value'])} g/m²s, the leak §2.1 names:** "
        if m["n"] == 0
        else f"m''_ext is the median of {m['n']} tests; "
    )
    return [
        head + f"{len(missing)} fit-flux tests have no m''_60 at their README flame-out because their records "
        f"end within 30 s of it ({report.fmt(-min(gaps), 0)} s before to {report.fmt(max(gaps), 0)} s after; m''_60 "
        "needs 30 s after). Reported "
        f"only: m''_60 30 s before each record's end is {report.fmt(min(last))}-{report.fmt(max(last))} g/m²s."
    ]


def outlying_lab_means(doc: dict[str, Any]) -> list[str]:
    """Lab means more than twice the median lab mean: the artefact rule can't see them (it compares a test with its
    own lab), so they are flagged here, not excluded."""
    notes = []
    for mat in ("pmma", "pine"):
        for flux, feats in doc[mat]["envelope"].items():
            for feat, env in feats.items():
                if not isinstance(env, dict) or env["n_labs"] < 3:
                    continue
                med = statistics.median(v["mean"] for v in env["labs"].values())
                notes += [
                    f"{mat} {flux} kW/m² {feat}: {lab}'s mean {report.fmt(v['mean'])} (n = {v['n']}) is over "
                    f"twice the labs' median {report.fmt(med)}; it sets the envelope's end and no rule removes it."
                    for lab, v in env["labs"].items()
                    if v["mean"] > pins.ARTEFACT_FACTOR * med
                ]
    return notes


def main(argv: list[str]) -> int:
    doc, notes = build()
    text_json, text_md = report.to_json(doc), report.to_md(doc, notes)
    out_json, out_md = HERE / "bands.json", HERE / "bands.md"
    if "--check" in argv:
        same = out_json.read_text(encoding="utf-8") == text_json and out_md.read_text(encoding="utf-8") == text_md
        print("rerun byte-identical" if same else "rerun DIFFERS from the committed outputs")
        return 0 if same else 1
    out_json.write_text(text_json, encoding="utf-8")
    out_md.write_text(text_md, encoding="utf-8")
    bad = [c for c in doc["reference_checks"] if not c["match"]]
    for c in doc["reference_checks"]:
        print(
            f"{'ok      ' if c['match'] else 'MISMATCH'}  {c['check']}: pre-registered "
            f"{report.fmt(c['preregistered'])}, computed {report.fmt(c['computed'])}"
        )
    print(f"{len(doc['reference_checks']) - len(bad)}/{len(doc['reference_checks'])} reference values reproduced")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
