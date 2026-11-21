"""Assemble every band, envelope and measured constant the pre-registration's criteria need."""

from __future__ import annotations

import math

import bands
import features
import fetch
import gasif
import numpy as np
import pins
import selection
import tables
from selection import Test


def test_rows(tests: list[Test]) -> dict[str, dict[str, object]]:
    """Every test's lab, flux, area, features and exclusions, by name."""
    return {
        t.name: {
            "lab": t.lab,
            "flux": t.flux,
            "area_m2": t.area,
            "path": t.path,
            "features": t.feats,
            "excluded": {k: sorted(v) for k, v in sorted(t.excluded.items())},
        }
        for t in sorted(tests, key=lambda t: t.name)
    }


def artefact_sensitivity(tests: list[Test], fluxes: list[int]) -> dict[str, object]:
    """The t_ig envelope with the artefact rule lifted, at each flux where it removed a test (reported only)."""
    hit = sorted({t.flux for t in tests if any(r.startswith("artefact") for v in t.excluded.values() for r in v)})
    relaxed = selection.without_artefact_rule(tests)
    return {str(f): bands.envelope(relaxed, "envelope", f, "t_ig", "time") for f in fluxes if f in hit}


def pmma_section(tests: list[Test]) -> dict[str, object]:
    """PMMA: DBI's per-lab bands and the all-lab envelopes (t_ig graded; the rest for §6 outcome 4), every flux,
    and ΔH_c,eff from DBI's square tests at each flux (the fit flux's is the measured constant)."""
    per_lab: dict[str, object] = {}
    env: dict[str, object] = {}
    dhc: dict[str, object] = {}
    for flux in pins.PMMA_FLUXES:
        key = str(flux)
        per_lab[key] = {
            f: bands.per_lab(tests, "per_lab", lab=pins.PMMA_FIT_LAB, flux=flux, feature=f, kind=k)
            for f, k in pins.PMMA_FEATURES.items()
        }
        env[key] = {f: bands.envelope(tests, "envelope", flux, f, k) for f, k in pins.PMMA_FEATURES.items()}
        dhc[key] = bands.mean_over([t for t in tests if t.flux == flux and t.counts("per_lab", "dhc")], "dhc")
    return {
        "per_lab": {pins.PMMA_FIT_LAB: per_lab},
        "envelope": env,
        "dhc_eff_dbi": dhc,
        "t_ig_envelope_artefact_rule_off_reported_only": artefact_sensitivity(tests, list(pins.PMMA_FLUXES)),
        "tests": test_rows(tests),
    }


def pine_section(tests: list[Test], readmes: dict[str, str]) -> dict[str, object]:
    """Pine: envelopes and per-lab bands at every listed flux, ΔH_c,eff over the fit tests and m''_ext."""
    env: dict[str, object] = {}
    per_lab: dict[str, object] = {}
    for flux, labs in sorted(pins.PINE_LABS.items()):
        key = str(flux)
        env[key] = {"role": pins.PINE_ROLE[flux]} | {
            f: bands.envelope(tests, "envelope", flux, f, k) for f, k in pins.PINE_FEATURES.items()
        }
        per_lab[key] = {
            lab: {
                f: bands.per_lab(tests, "envelope", lab=lab, flux=flux, feature=f, kind=k)
                for f, k in pins.PINE_FEATURES.items()
            }
            for lab in labs
        }
    fit = [t for t in tests if t.flux in pins.PINE_FIT_FLUXES and t.counts("envelope", "dhc")]
    dhc = {"pooled_fit_tests": bands.mean_over(fit, "dhc")} | {
        str(f): bands.mean_over([t for t in fit if t.flux == f], "dhc") for f in pins.PINE_FIT_FLUXES
    }
    return {
        "envelope": env,
        "per_lab": per_lab,
        "dhc_eff": dhc,
        "m_ext": m_ext(tests, readmes),
        "t_ig_envelope_artefact_rule_off_reported_only": artefact_sensitivity(tests, sorted(pins.PINE_LABS)),
        "tests": test_rows(tests),
    }


def m_ext(tests: list[Test], readmes: dict[str, str]) -> dict[str, object]:
    """§2.1: the median m''_60 at the README flame-out times of the fit-flux tests (Aalto and UQ)."""
    times: dict[str, float] = {}
    for path in sorted(pins.FLAMEOUT_READMES.values()):
        times |= tables.flameout_times(readmes[path])
    at: dict[str, object] = {}
    for t in sorted(tests, key=lambda t: t.name):
        if t.flux not in pins.PINE_FIT_FLUXES or not t.counts("envelope", "t_ig") or t.lab not in pins.FLAMEOUT_READMES:
            continue
        tfo = times.get(t.name)
        if tfo is None:
            at[t.name] = {"t_flameout": None, "m60": None}
            continue
        tt, m, _ = tables.cone_columns(fetch.cache_path(t.path))
        t_last = float(tt[-1]) - pins.MLR60_HALF_SPAN
        v, v_last = (float(x) for x in features.mlr60_at(tt, m, t.area, np.array([tfo, t_last])))
        at[t.name] = {
            "t_flameout": tfo,
            "m60": v if math.isfinite(v) else None,
            "t_record_end": float(tt[-1]),
            "m60_at_record_end_minus_30s_reported_only": v_last if math.isfinite(v_last) else None,
        }
    vals = [float(r["m60"]) for r in at.values() if isinstance(r, dict) and r["m60"] is not None]  # type: ignore[arg-type]
    if vals:
        return {"value": bands.median(vals), "source": "median of fit-flux flame-outs", "n": len(vals), "tests": at}
    return {
        "value": pins.M_EXT_FALLBACK,
        "source": "fallback (leak: 25 kW/m² median, fire_solid §4.4)",
        "n": 0,
        "tests": at,
    }


def gasification_section() -> dict[str, object]:
    """P0's NIST data per repeat, and each flux's repeat range widened by the feature's V tolerance."""
    base = pins.GASIF_DIR + "MaCFP-PMMA_Gasification_q{q}_{kind}_{r}.csv"
    reps: dict[str, dict[str, float | None]] = {}
    for q, r in pins.GASIF_MLR:
        reps[f"q{q}_Mass_{r}"] = gasif.mlr_features(
            fetch.cache_path(base.format(q=q, kind="MLR", r=r))
        ) | gasif.mass_features(fetch.cache_path(base.format(q=q, kind="Mass", r=r)))
    for q, r in pins.GASIF_TEMP:
        reps[f"q{q}_Temp_{r}"] = gasif.back_temperature_features(fetch.cache_path(base.format(q=q, kind="Temp", r=r)))
    ranges: dict[str, object] = {}
    for group in ("q50_Mass", "q25_Temp", "q50_Temp"):
        rows = [v for k, v in sorted(reps.items()) if k.startswith(group + "_")]
        ranges[group] = {}
        for feat, (kind, tol) in sorted(pins.GASIF_TOL.items()):
            vals = [float(v[feat]) for v in rows if v.get(feat) is not None]  # type: ignore[arg-type]
            if vals:
                ranges[group][feat] = bands.band(vals, kind, tol) | {"of_repeats": len(rows)}  # type: ignore[index]
    return {"repeats": reps, "ranges": ranges}
