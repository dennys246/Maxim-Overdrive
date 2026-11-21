"""§2.2's bands: an envelope over lab means and a per-lab band over a lab's tests, each end widened by the V
tolerance (3 s on times, 2.5% on rates and masses)."""

from __future__ import annotations

import math
import statistics

import pins
from selection import Test


def widen(lo: float, hi: float, kind: str, tol: float | None = None) -> tuple[float, float]:
    """[lo, hi] widened by an absolute time tolerance or a relative one, each end outward."""
    if kind == "time":
        d = pins.TOL_TIME if tol is None else tol
        return lo - d, hi + d
    r = pins.TOL_REL if tol is None else tol
    return lo * (1 - r) if lo >= 0 else lo * (1 + r), hi * (1 + r) if hi >= 0 else hi * (1 - r)


def band(values: list[float], kind: str, tol: float | None = None) -> dict[str, object]:
    """{min, max, lo, hi, n}: the values' range and that range widened."""
    lo, hi = min(values), max(values)
    wlo, whi = widen(lo, hi, kind, tol)
    return {"min": lo, "max": hi, "lo": wlo, "hi": whi, "n": len(values)}


def _value(t: Test, feature: str) -> float:
    v = t.feats[feature]
    assert isinstance(v, float)
    return v


def lab_means(tests: list[Test], scope: str, flux: int, feature: str) -> dict[str, dict[str, object]]:
    """{lab: {mean, n, tests}} over the tests in `scope` at `flux` with a finite `feature`, labs sorted."""
    by_lab: dict[str, list[Test]] = {}
    for t in tests:
        if t.flux == flux and t.counts(scope, feature):
            by_lab.setdefault(t.lab, []).append(t)
    return {
        lab: {
            "mean": math.fsum(_value(t, feature) for t in group) / len(group),
            "n": len(group),
            "tests": sorted(t.name for t in group),
        }
        for lab, group in sorted(by_lab.items())
    }


def envelope(tests: list[Test], scope: str, flux: int, feature: str, kind: str) -> dict[str, object] | None:
    """[min, max] of lab means, widened; None if no lab has the feature at that flux."""
    labs = lab_means(tests, scope, flux, feature)
    if not labs:
        return None
    means = [float(v["mean"]) for v in labs.values()]  # type: ignore[arg-type]
    out = band(means, kind)
    out["n_labs"] = out.pop("n")
    out["labs"] = labs
    return out


def per_lab(tests: list[Test], scope: str, *, lab: str, flux: int, feature: str, kind: str) -> dict[str, object] | None:
    """[min, max] of one lab's tests, widened; None if it has none."""
    group = sorted(
        (t for t in tests if t.lab == lab and t.flux == flux and t.counts(scope, feature)), key=lambda t: t.name
    )
    if not group:
        return None
    out = band([_value(t, feature) for t in group], kind)
    out["tests"] = {t.name: _value(t, feature) for t in group}
    out["mean"] = math.fsum(_value(t, feature) for t in group) / len(group)
    return out


def mean_over(tests: list[Test], feature: str) -> dict[str, object] | None:
    """{mean, n, tests} of a feature over the given tests (finite values only)."""
    vals = {
        t.name: _value(t, feature)
        for t in sorted(tests, key=lambda t: t.name)
        if isinstance(t.feats.get(feature), float) and math.isfinite(_value(t, feature))
    }
    if not vals:
        return None
    return {"mean": math.fsum(vals.values()) / len(vals), "n": len(vals), "tests": vals}


def median(values: list[float]) -> float:
    return float(statistics.median(values))
