"""P0's data features from NIST's gasification repeats (§5 P0; §9's "NIST data" column).

MLR files give m'' (g/m²s) directly; mass files give the sample's mass (g); temperature files give two or three back
thermocouples (K). Back T is the mean of the thermocouples reading at each sample (a choice the pre-registration
doesn't fix; disclosed in bands.md).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pins
from tables import Array, read_csv


def first_time_at_or_above(t: Array, v: Array, level: float) -> float | None:
    """The first sample time with v >= level (NaN never counts); None if it never gets there."""
    hits = np.flatnonzero(v >= level)
    return float(t[hits[0]]) if hits.size else None


def _checked(path: Path, units: tuple[str, ...]) -> tuple[Array, ...]:
    table = read_csv(path)
    if tuple(u.lower() for u in table.units[: len(units)]) != units:
        raise ValueError(f"{path}: units {table.units}, expected {units}")
    return table.columns


def mlr_features(path: Path) -> dict[str, float | None]:
    """Peak m'' and its first time; first times to m'' >= 1, >= 2.7 g/m²s and to half the peak."""
    t, mlr = _checked(path, ("s", "g/m2/s"))[:2]
    i = int(np.argmax(np.where(np.isfinite(mlr), mlr, -np.inf)))
    peak = float(mlr[i])
    return {
        "peak_mlr": peak,
        "t_peak": float(t[i]),
        "t_mlr_1": first_time_at_or_above(t, mlr, 1.0),
        "t_mlr_2.7": first_time_at_or_above(t, mlr, 2.7),
        "t_half_peak": first_time_at_or_above(t, mlr, 0.5 * peak),
    }


def mass_features(path: Path) -> dict[str, float | None]:
    """The first time the sample's mass is at most half its first reading, and that first reading."""
    t, m = _checked(path, ("s", "g"))[:2]
    m0 = float(m[0])
    hits = np.flatnonzero(m <= 0.5 * m0)
    return {"m0": m0, "t_half_mass": float(t[hits[0]]) if hits.size else None}


def back_temperature_features(path: Path) -> dict[str, float | None]:
    """First times the mean back thermocouple reaches 100, 200 and 300 °C (None where it never does)."""
    cols = read_csv(path).columns
    t, tcs = cols[0], np.vstack(cols[1:])
    ok = np.isfinite(tcs)
    count = ok.sum(axis=0)
    mean_k = np.where(count > 0, np.where(ok, tcs, 0.0).sum(axis=0) / np.maximum(count, 1), np.nan)
    mean_c = mean_k - pins.KELVIN
    out: dict[str, float | None] = {"t_end": float(t[-1]), "back_T_end_C": float(mean_c[-1])}
    for level in pins.BACK_T_CROSSINGS:
        out[f"t_back_{level:.0f}C"] = first_time_at_or_above(t, mean_c, level)
    return out
