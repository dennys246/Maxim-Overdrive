"""Per-test cone features, by §2.1 of the pre-registration. Data only: no model, no fitting.

Units: time s, mass g, area m², Q'' kW/m², mass flux g/m²s, mass per area g/m², ΔH_c kJ/g.
"""

from __future__ import annotations

import math

import numpy as np
import pins
from tables import Array


def ignition_index(q: Array) -> int | None:
    """The first sample with Q'' >= 24 kW/m² (MaCFP-4: `df[df['HRR (kW/m2)'] >= 24].index[0]`); NaN never counts."""
    hits = np.flatnonzero(q >= pins.Q_IGN)
    return int(hits[0]) if hits.size else None


def last_flaming_index(q: Array) -> int:
    """The last sample with Q'' >= 24 kW/m² (the caller has checked one exists)."""
    return int(np.flatnonzero(q >= pins.Q_IGN)[-1])


def mlr10(t: Array, m: Array, area: float) -> Array:
    """m''_10: MaCFP-4's five-point central difference of mass per area, then its mean over samples within ±5 s.

    raw[i] = (m[i-2] - m[i+2]) / (t[i+2] - t[i-2]) / A; the mean skips NaN raw values (the first and last two, and
    any touching a missing mass), and is NaN where no raw value lies within the window.
    """
    n = t.size
    raw = np.full(n, math.nan)
    if n >= 5:
        raw[2:-2] = (m[:-4] - m[4:]) / (t[4:] - t[:-4]) / area
    out = np.full(n, math.nan)
    for i in range(n):
        lo = int(np.searchsorted(t, t[i] - pins.MLR10_HALF_WINDOW, side="left"))
        hi = int(np.searchsorted(t, t[i] + pins.MLR10_HALF_WINDOW, side="right"))
        w = raw[lo:hi]
        w = w[np.isfinite(w)]
        if w.size:
            out[i] = float(np.sum(w)) / w.size
    return out


def mlr60_at(t: Array, m: Array, area: float, at: Array) -> Array:
    """m''_60 = (m(t - 30) - m(t + 30)) / (60 A) at the times `at`, with mass linearly interpolated between finite
    samples; NaN where t - 30 or t + 30 falls outside the finite samples' span."""
    ok = np.isfinite(m)
    tf, mf = t[ok], m[ok]
    out = np.full(at.size, math.nan)
    if tf.size < 2:
        return out
    a, b = at - pins.MLR60_HALF_SPAN, at + pins.MLR60_HALF_SPAN
    inside = (a >= tf[0]) & (b <= tf[-1])
    out[inside] = (np.interp(a[inside], tf, mf) - np.interp(b[inside], tf, mf)) / (2 * pins.MLR60_HALF_SPAN * area)
    return out


def thr(t: Array, q: Array, i0: int, i1: int) -> float:
    """∫Q'' dt from sample i0 to i1 (trapezoid, kJ/m²), skipping any interval with a missing end."""
    dt = np.diff(t[i0 : i1 + 1])
    mid = 0.5 * (q[i0:i1] + q[i0 + 1 : i1 + 1])
    good = np.isfinite(mid)
    return float(np.sum(mid[good] * dt[good]))


def has_mass(m: Array) -> bool:
    """False for a file whose mass column is missing or never changes (no mass signal)."""
    f = m[np.isfinite(m)]
    return f.size >= 5 and float(np.max(f) - np.min(f)) > 0.0


def dhc(t: Array, q: Array, m: Array, area: float, *, span: tuple[int, int]) -> float:
    """ΔH_c,eff over samples i0..i1: ∫Q'' dt ÷ mass lost per area (kJ/g); NaN if no mass was lost or one end is NaN."""
    i0, i1 = span
    lost = (m[i0] - m[i1]) / area
    return thr(t, q, i0, i1) / lost if np.isfinite(lost) and lost > 0 else math.nan


def argmax_finite(values: Array, idx: Array) -> int | None:
    """The index in `idx` with the largest finite value (the first, on a tie); None if none is finite."""
    v = values[idx]
    ok = np.isfinite(v)
    if not np.any(ok):
        return None
    j = int(np.argmax(np.where(ok, v, -math.inf)))
    return int(idx[j])


def pmma_features(t: Array, m: Array, q: Array, area: float) -> dict[str, float | None]:
    """PMMA: t_ig; peak m''_10 over [t_ig, last Q'' >= 24]; its time; mass lost per area from t_ig to then; ΔH_c,eff
    while flaming. Mass features are None when the file has no mass signal."""
    ig = ignition_index(q)
    if ig is None:
        return {"t_ig": None}
    last = last_flaming_index(q)
    out: dict[str, float | None] = {"t_ig": float(t[ig]), "t_flame_end": float(t[last])}
    if not has_mass(m):
        return out
    md = mlr10(t, m, area)
    ip = argmax_finite(md, np.arange(ig, last + 1))
    if ip is None:
        return out
    out |= {
        "peak": float(md[ip]),
        "t_peak": float(t[ip]),
        "mass_lost": float((m[ig] - m[ip]) / area),
        "dhc": dhc(t, q, m, area, span=(ig, last)),
    }
    return out


def pine_window_end(t: Array, m60: Array, i_peak: int) -> int | None:
    """The first sample after the first peak with m''_60 < 2.7 g/m²s; None if the data never fall below it."""
    later = np.flatnonzero((np.arange(t.size) > i_peak) & (m60 < pins.PINE_WINDOW_END_MLR))
    return int(later[0]) if later.size else None


def pine_features(t: Array, m: Array, q: Array, area: float) -> dict[str, float | bool | None]:
    """Pine: t_ig; first peak (largest m''_10 in [t_ig, t_ig + 200 s]) and its time; the window's end (first m''_60
    < 2.7 after the first peak); the plateau (mean m''_60 over [t_ig + 250, t_ig + 450 s], cut at the window's end);
    ΔH_c,eff over [t_ig, window end]. Mass features are None when the file has no mass signal."""
    ig = ignition_index(q)
    if ig is None:
        return {"t_ig": None}
    t0 = float(t[ig])
    out: dict[str, float | bool | None] = {"t_ig": t0}
    if not has_mass(m):
        return out
    md = mlr10(t, m, area)
    m60 = mlr60_at(t, m, area, t)
    ip = argmax_finite(md, np.flatnonzero((t >= t0) & (t <= t0 + pins.PINE_FIRST_PEAK_SPAN)))
    if ip is None:
        return out
    iw = pine_window_end(t, m60, ip)
    t_end = float(t[iw]) if iw is not None else math.inf
    lo, hi = t0 + pins.PINE_PLATEAU[0], min(t0 + pins.PINE_PLATEAU[1], t_end)
    pl = m60[(t >= lo) & (t <= hi) & np.isfinite(m60)]
    uncut = m60[(t >= lo) & (t <= t0 + pins.PINE_PLATEAU[1]) & np.isfinite(m60)]
    i_last = iw if iw is not None else int(np.flatnonzero(np.isfinite(m))[-1])
    out |= {
        "first_peak": float(md[ip]),
        "t_first_peak": float(t[ip]),
        "window_end": float(t[iw]) if iw is not None else None,
        "plateau": float(np.sum(pl)) / pl.size if pl.size else None,
        "plateau_cut_by_window": bool(t_end < t0 + pins.PINE_PLATEAU[1]),
        "plateau_uncut_reported_only": float(np.sum(uncut)) / uncut.size if uncut.size else None,
        "dhc": dhc(t, q, m, area, span=(ig, i_last)),
    }
    return out
