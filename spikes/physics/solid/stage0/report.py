"""Write bands.json (sorted keys, six significant digits, so a rerun is byte-identical) and bands.md (tables)."""

from __future__ import annotations

import json
import math
from typing import Any

import pins

# Choices the pre-registration leaves open, made here before the bands were read, and disclosed with them.
INTERPRETATIONS = (
    "m''_10: raw[i] = (m[i-2] - m[i+2]) / (t[i+2] - t[i-2]) / A (MaCFP-4's `Calculate_dm_dt`), then the mean of the "
    "finite raw values with |t_j - t_i| <= 5 s.",
    "m''_60: mass linearly interpolated at t - 30 and t + 30 s between finite samples; undefined within 30 s of "
    "either end of the record.",
    "PMMA mass lost: raw mass at the t_ig sample minus raw mass at the peak sample, over the area (g/m²).",
    "ΔH_c (PMMA, and MaCFP-2's outlier rule): trapezoidal ∫Q'' dt over [t_ig, last Q'' >= 24] over the raw mass "
    "lost between those samples. A test whose ΔH_c can't be computed (no mass signal) fails the rule.",
    "Pine window: from t_ig to the first sample after the first peak with m''_60 < 2.7 g/m²s; the plateau's "
    "[t_ig + 250, t_ig + 450 s] is cut at the window's end. With no such sample the window runs to the record's end.",
    "PMMA envelopes take every PMMA cone file at 25, 50 and 65 (DBI's round samples included, at their README "
    "area 0.00387 m²), minus MaCFP-2's outliers and §2.1's artefacts. Only t_ig's is graded (P1); the others are "
    "reported for §6 outcome 4.",
    "The artefact rule's lab median is over the lab's tests still in the set at that flux, the test itself included.",
    "Pine per-lab bands use the same tests as the envelopes. Pine ΔH_c,eff is the mean over the fit tests at 30 "
    "and 60 pooled (also given per flux).",
    "m''_ext: m''_60 at each README flame-out time, for the fit-flux tests of the labs that record one (Aalto 30 "
    "and 60, UQ 60); a flame-out within 30 s of the record's end has no m''_60 and is listed as such.",
    "P0: back T is the mean of the thermocouples reading at each sample; half the sample mass is half the mass "
    "file's first reading. Widening uses each feature's V tolerance (peak 2.5%, peak time 8 s, the other times "
    "3 s); the half-mass time and back-T crossings have no V row, so they take §2.2's 3 s on times.",
)


def _clean(x: Any) -> Any:
    """JSON-ready: floats to six significant digits (non-finite to null), tuples to lists, keys to strings."""
    if isinstance(x, bool) or x is None or isinstance(x, (int, str)):
        return x
    if isinstance(x, float):
        return float(f"{x:.6g}") if math.isfinite(x) else None
    if isinstance(x, dict):
        return {str(k): _clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    raise TypeError(f"unexpected {type(x)} in bands")


def to_json(doc: dict[str, Any]) -> str:
    return json.dumps(_clean(doc), sort_keys=True, indent=1, ensure_ascii=False, allow_nan=False) + "\n"


def fmt(x: Any, nd: int = 2) -> str:
    if x is None:
        return "—"
    if isinstance(x, bool):
        return "yes" if x else "**NO**"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    if isinstance(x, list):
        return ", ".join(fmt(v, nd) for v in x)
    return str(x)


def _band_row(label: str, b: dict[str, Any] | None, extra: str = "") -> str:
    if b is None:
        return f"| {label} | — | — | — |{extra}"
    n = b.get("n_labs", b.get("n"))
    return f"| {label} | {fmt(b['min'])} to {fmt(b['max'])} | {fmt(b['lo'])} to {fmt(b['hi'])} | {n} |{extra}"


def checks_md(checks: list[dict[str, Any]]) -> list[str]:
    out = [
        "## Pre-registered reference values",
        "",
        f"{sum(c['match'] for c in checks)} of {len(checks)} reproduced.",
        "",
        "| Check | Pre-registered | Computed | Reproduced |",
        "|---|---|---|---|",
    ]
    out += [f"| {c['check']} | {fmt(c['preregistered'])} | {fmt(c['computed'])} | {fmt(c['match'])} |" for c in checks]
    return [*out, ""]


def pmma_md(pmma: dict[str, Any]) -> list[str]:
    out = [
        "## PMMA",
        "",
        "Ranges are [min, max] before widening; bands are widened by 3 s on times and 2.5% on "
        "rates and masses. Units: s, g/m²s, g/m².",
        "",
        "### DBI_Lund per-lab bands (P1, square samples)",
        "",
        "| Flux, feature | Tests' range | Band | n |",
        "|---|---|---|---|",
    ]
    for flux, feats in pmma["per_lab"]["DBI_Lund"].items():
        out += [_band_row(f"{flux}: {f}", b) for f, b in feats.items()]
    out += [
        "",
        "### All-lab envelopes (t_ig graded in P1; the rest for outcome 4)",
        "",
        "| Flux, feature | Lab means' range | Band | Labs |",
        "|---|---|---|---|",
    ]
    for flux, feats in pmma["envelope"].items():
        out += [_band_row(f"{flux}: {f}", b) for f, b in feats.items()]
    out += [
        "",
        "### ΔH_c,eff, DBI square tests (kJ/g; the fit flux's is the measured constant)",
        "",
        "| Flux | Mean | n |",
        "|---|---|---|",
    ]
    out += [f"| {flux} | {fmt(v['mean'], 3)} | {v['n']} |" for flux, v in pmma["dhc_eff_dbi"].items() if v]
    return [*out, ""]


def pine_md(pine: dict[str, Any]) -> list[str]:
    out = [
        "## White pine, parallel grain",
        "",
        "### Envelopes (P2 graded at 25, 50, 75; fit at 30, 60)",
        "",
        "| Flux (role), feature | Lab means' range | Band | Labs |",
        "|---|---|---|---|",
    ]
    for flux, feats in pine["envelope"].items():
        out += [_band_row(f"{flux} ({feats['role']}): {f}", b) for f, b in feats.items() if f != "role"]
    out += ["", "### Per-lab bands", "", "| Flux, lab, feature | Tests' range | Band | n |", "|---|---|---|---|"]
    for flux, labs in pine["per_lab"].items():
        for lab, feats in labs.items():
            out += [_band_row(f"{flux}, {lab}: {f}", b) for f, b in feats.items()]
    d = pine["dhc_eff"]
    out += ["", "### ΔH_c,eff over the fit tests (kJ/g)", "", "| Set | Mean | n |", "|---|---|---|"]
    out += [f"| {k} | {fmt(v['mean'], 3)} | {v['n']} |" for k, v in d.items() if v]
    m = pine["m_ext"]
    out += [
        "",
        f"### m''_ext = {fmt(m['value'], 3)} g/m²s ({m['source']}, n = {m['n']})",
        "",
        "| Test | Flame-out (s) | m''_60 there (g/m²s) | Record ends (s) | m''_60 at end - 30 s (reported only) |",
        "|---|---|---|---|---|",
    ]
    out += [
        f"| {k} | {fmt(v['t_flameout'], 0)} | {fmt(v['m60'], 3)} | {fmt(v.get('t_record_end'), 0)} | "
        f"{fmt(v.get('m60_at_record_end_minus_30s_reported_only'), 3)} |"
        for k, v in m["tests"].items()
    ]
    off = pine["t_ig_envelope_artefact_rule_off_reported_only"]
    out += [
        "",
        "### t_ig envelope with the artefact rule lifted (reported only, not a band)",
        "",
        "| Flux | Lab means' range | Band | Labs |",
        "|---|---|---|---|",
    ]
    out += [_band_row(flux, b) for flux, b in off.items()]
    return [*out, ""]


def gas_md(gas: dict[str, Any]) -> list[str]:
    out = [
        "## P0: NIST gasification data",
        "",
        "| Repeat | " + " | ".join(pins.GASIF_TOL) + " |",
        "|---|" + "---|" * len(pins.GASIF_TOL),
    ]
    for rep, f in gas["repeats"].items():
        out.append(
            f"| {rep} | " + " | ".join(fmt(f.get(k), 2 if k == "peak_mlr" else 0) for k in pins.GASIF_TOL) + " |"
        )
    out += ["", "| Group, feature | Repeats' range | Band | n |", "|---|---|---|---|"]
    for group, feats in gas["ranges"].items():
        out += [_band_row(f"{group}: {f}", b) for f, b in feats.items()]
    return [*out, ""]


def exclusions_md(pmma: dict[str, Any], pine: dict[str, Any]) -> list[str]:
    out = ["## Exclusions", "", "| Test | Set | Reason |", "|---|---|---|"]
    for tests in (pmma["tests"], pine["tests"]):
        for name, t in tests.items():
            for scope, reasons in t["excluded"].items():
                if reasons != ["not the per-lab band's lab"]:
                    out += [f"| {name} | {scope} | {r} |" for r in reasons if r != "not the per-lab band's lab"]
    return [*out, ""]


def to_md(doc: dict[str, Any], notes: list[str]) -> str:
    out = [
        "# Solid spike, stage 0: feature bands from MaCFP data",
        "",
        f"Generated by `run.py` from MaCFP matl-db at `{pins.COMMIT}` ({len(doc['source']['files'])} files, "
        "SHA-256s in `bands.json`). Data only: no model, no fitting. Rules: "
        "`docs/design/research/solid_spike/preregistration.md` §2.",
        "",
        "Rerun: `<python> spikes/physics/solid/stage0/run.py` (numpy and the standard library; it fetches the pinned "
        "files once into the git-ignored `cache/`, verifying each against the commit's git blob SHA). "
        "`run.py --check` recomputes and fails unless both outputs are byte-identical. `run.py` exits 1 while any "
        "reference value below is not reproduced.",
        "",
    ]
    out += checks_md(doc["reference_checks"])
    out += ["## Findings and disclosures", "", *[f"- {n}" for n in notes], ""]
    out += [
        "## Interpretations (choices the pre-registration leaves open)",
        "",
        *[f"- {n}" for n in INTERPRETATIONS],
        "",
    ]
    out += pmma_md(doc["pmma"]) + pine_md(doc["pine"]) + gas_md(doc["gasification"])
    out += exclusions_md(doc["pmma"], doc["pine"])
    return "\n".join(out)
