"""The values the pre-registration recorded before any code (§2.2's t_ig table, §2's exclusion list, §2.1's FPL
artefact, §3's ΔH_c,eff, §9's NIST data, §10.4's ULSTER ΔH_c), compared with what stage 0 computes.

Each is matched at the precision it was written with (half a unit in its last digit). A mismatch is reported, never
adjusted: §2.2 says "a difference is a stage-0 bug, disclosed", and the pre-registration is not edited.
"""

from __future__ import annotations

import math
from typing import Any

# §2.2's t_ig table (lab means, s): material, flux -> (lo, hi, decimals, labs or None).
TIG_ENVELOPES: dict[tuple[str, int], tuple[float, float, int, int | None]] = {
    ("pmma", 25): (98.7, 123.5, 1, 6),
    ("pmma", 65): (12.0, 25.9, 1, 7),
    ("pine", 25): (70.3, 118.3, 1, None),
    ("pine", 30): (31.0, 51.7, 1, None),
    ("pine", 50): (13.7, 23.3, 1, None),
    ("pine", 60): (8.8, 20.0, 1, None),
    ("pine", 75): (3.7, 7.7, 1, None),
}
# §9, "NIST data" column: repeat key -> {feature: value}, written to the whole unit.
NIST_DATA: dict[str, dict[str, float]] = {
    "q50_Mass_R3": {"peak_mlr": 29.88, "t_peak": 346, "t_half_mass": 226, "t_half_peak": 65},
    "q50_Mass_R4": {"peak_mlr": 28.06, "t_peak": 326, "t_half_mass": 223, "t_half_peak": 65},
    "q50_Mass_R5": {"peak_mlr": 27.80, "t_peak": 337, "t_half_mass": 239, "t_half_peak": 60},
    "q25_Temp_R1": {"t_back_100C": 145, "t_back_200C": 345, "t_back_300C": 749},
    "q50_Temp_R3": {"t_back_100C": 114},
    "q50_Temp_R4": {"t_back_100C": 112},
}
# §2's P1 envelope row: MaCFP-2's rule "removes HKPolyU, LCPP, ULSTER and UQ, UClan at 25 and one Edinburgh test".
DHC_REMOVED_LABS = ("HKPolyU", "LCPP", "ULSTER", "UQ")
DHC_REMOVED_UCLAN_FLUX = 25
DHC_REMOVED_EDINBURGH = 1


# Why each known mismatch arises, found by reading the data after the run (stage 0 reports; it never adjusts).
EXPLANATIONS = {
    "pine t_ig envelope at 50 kW/m² (s)": (
        "§2.1's artefact rule, written after this table, removes FPL R4 from every feature. FPL's t_ig mean is 13.80 s "
        "without R4 and 13.67 s with it, so the recorded 13.7 predates the rule; with the rule lifted stage 0 gives "
        "the recorded envelope (`t_ig_envelope_artefact_rule_off_reported_only`). The band follows the rule as written."
    ),
    "ΔH_c rule removes one Edinburgh test": (
        "Edinburgh_Cone_25kW_1's ΔH_c over its flaming window is 26.27 kJ/g, outside 21-26 (the derivation script "
        "behind the pre-registration printed the same 26.27); 65kW_4 has no usable mass signal (peak m''_10 -0.63). "
        "Dropping 25kW_1 moves Edinburgh's 25 kW/m² t_ig mean from 108.0 to 105.5 s; neither is an end of the "
        "envelope (TIFP 98.7, GIDAZE+ 123.5), so the graded band is the same either way."
    ),
    "FPL 50 kW/m² lab median first peak (g/m²s)": (
        "FPL's six first peaks are 11.58, 13.41, 13.61, 15.10, 15.11 and 71.64 g/m²s: median 14.35, or 13.61 "
        "without R4. 13.5 is neither. R4 is excluded either way (71.6 > 2 x 14.35)."
    ),
    "ULSTER ΔH_c at 50 (kJ/g)": (
        "The maximum is 33.147 (ULSTER_Cone_50kW_1), which rounds to 33.1; the derivation script printed 33.15, and "
        "33.2 is that rounded again. ULSTER is outside 21-26 and removed either way."
    ),
}


def _half_unit(decimals: int) -> float:
    return 0.5 * 10.0 ** (-decimals) + 1e-9


def _row(check: str, recorded: object, computed: object, match: bool, diff: object = None) -> dict[str, Any]:
    return {
        "check": check,
        "preregistered": recorded,
        "computed": computed,
        "match": match,
        "difference": diff,
        "note": None if match else EXPLANATIONS.get(check, "unexplained: a stage-0 bug until shown otherwise"),
    }


def tig_envelopes(pmma: dict[str, Any], pine: dict[str, Any]) -> list[dict[str, Any]]:
    """§2.2's t_ig envelopes (unwidened min and max of lab means) and, for PMMA, the lab counts."""
    rows = []
    for (mat, flux), (lo, hi, dec, labs) in TIG_ENVELOPES.items():
        env = (pmma if mat == "pmma" else pine)["envelope"][str(flux)]["t_ig"]
        got_lo, got_hi = env["min"], env["max"]
        ok = abs(got_lo - lo) <= _half_unit(dec) and abs(got_hi - hi) <= _half_unit(dec)
        rows.append(
            _row(f"{mat} t_ig envelope at {flux} kW/m² (s)", [lo, hi], [got_lo, got_hi], ok, [got_lo - lo, got_hi - hi])
        )
        if labs is not None:
            rows.append(_row(f"{mat} t_ig envelope at {flux} kW/m²: labs", labs, env["n_labs"], env["n_labs"] == labs))
    return rows


def pmma_50(pmma: dict[str, Any]) -> list[dict[str, Any]]:
    """§2.2: PMMA at 50 is "DBI only, tests 24-27"."""
    env = pmma["envelope"]["50"]["t_ig"]
    labs = sorted(env["labs"])
    tests = [v["features"]["t_ig"] for k, v in pmma["tests"].items() if k in env["labs"]["DBI_Lund"]["tests"]]
    rng = [round(min(tests)), round(max(tests))]
    return [
        _row("pmma t_ig envelope at 50 kW/m²: labs", ["DBI_Lund"], labs, labs == ["DBI_Lund"]),
        _row("pmma t_ig at 50 kW/m²: DBI test range (s)", [24, 27], rng, rng == [24, 27]),
    ]


def dhc_removals(pmma: dict[str, Any]) -> list[dict[str, Any]]:
    """§2: which tests MaCFP-2's ΔH_c rule removes from the envelope."""
    removed = sorted(
        k for k, v in pmma["tests"].items() if any("MaCFP-2" in r for r in v["excluded"].get("envelope", []))
    )
    by_lab: dict[str, list[str]] = {}
    for k in removed:
        by_lab.setdefault(pmma["tests"][k]["lab"], []).append(k)
    rows = []
    for lab in DHC_REMOVED_LABS:
        all_lab = sorted(k for k, v in pmma["tests"].items() if v["lab"] == lab)
        rows.append(
            _row(
                f"ΔH_c rule removes every {lab} test",
                len(all_lab),
                len(by_lab.get(lab, [])),
                by_lab.get(lab, []) == all_lab,
            )
        )
    uclan = by_lab.get("UClan", [])
    want = [k for k, v in pmma["tests"].items() if v["lab"] == "UClan" and v["flux"] == DHC_REMOVED_UCLAN_FLUX]
    rows.append(_row("ΔH_c rule removes UClan at 25 only", sorted(want), uclan, uclan == sorted(want)))
    edi = by_lab.get("Edinburgh", [])
    rows.append(
        _row(
            "ΔH_c rule removes one Edinburgh test",
            DHC_REMOVED_EDINBURGH,
            edi,
            len(edi) == DHC_REMOVED_EDINBURGH,
            len(edi) - DHC_REMOVED_EDINBURGH,
        )
    )
    others = sorted(set(by_lab) - {*DHC_REMOVED_LABS, "UClan", "Edinburgh"})
    rows.append(_row("ΔH_c rule removes no other lab", [], others, not others))
    return rows


def scalars(pmma: dict[str, Any], pine: dict[str, Any]) -> list[dict[str, Any]]:
    """§3's ΔH_c,eff (DBI fit tests), §2.1's FPL artefact numbers and §10.4's ULSTER ΔH_c range."""
    rows = []
    for flux, want in ((25, 24.7), (65, 24.6)):
        got = pmma["dhc_eff_dbi"][str(flux)]["mean"]
        rows.append(
            _row(
                f"pmma ΔH_c,eff, DBI fit tests at {flux} (kJ/g)",
                want,
                got,
                abs(got - want) <= _half_unit(1),
                got - want,
            )
        )
    fpl = pine["tests"]["FPL_Wood_Cone_50kW_hor_R4"]["features"]["first_peak"]
    rows.append(_row("FPL 50 kW/m² R4 first peak (g/m²s)", 71.6, fpl, abs(fpl - 71.6) <= _half_unit(1), fpl - 71.6))
    peaks = sorted(
        v["features"]["first_peak"]
        for k, v in pine["tests"].items()
        if v["lab"] == "FPL" and v["flux"] == 50 and v["features"].get("first_peak") is not None
    )
    med = peaks[len(peaks) // 2] if len(peaks) % 2 else 0.5 * (peaks[len(peaks) // 2 - 1] + peaks[len(peaks) // 2])
    rows.append(
        _row("FPL 50 kW/m² lab median first peak (g/m²s)", 13.5, med, abs(med - 13.5) <= _half_unit(1), med - 13.5)
    )
    ul = [v["features"]["dhc"] for v in pmma["tests"].values() if v["lab"] == "ULSTER" and v["flux"] == 50]
    got_rng = [min(ul), max(ul)]
    ok = abs(got_rng[0] - 31.7) <= _half_unit(1) and abs(got_rng[1] - 33.2) <= _half_unit(1)
    rows.append(_row("ULSTER ΔH_c at 50 (kJ/g)", [31.7, 33.2], got_rng, ok, [got_rng[0] - 31.7, got_rng[1] - 33.2]))
    return rows


def nist(gas: dict[str, Any]) -> list[dict[str, Any]]:
    """§9's NIST data column."""
    rows = []
    for rep, feats in NIST_DATA.items():
        for feat, want in feats.items():
            got = gas["repeats"][rep][feat]
            dec = 2 if feat == "peak_mlr" else 0
            ok = got is not None and abs(got - want) <= _half_unit(dec)
            rows.append(_row(f"NIST {rep} {feat}", want, got, ok, None if got is None else got - want))
    return rows


def all_checks(pmma: dict[str, Any], pine: dict[str, Any], gas: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [*tig_envelopes(pmma, pine), *pmma_50(pmma), *dhc_removals(pmma), *scalars(pmma, pine), *nist(gas)]
    for r in rows:
        d = r["difference"]
        if isinstance(d, float) and not math.isfinite(d):
            r["difference"] = None
    return rows
