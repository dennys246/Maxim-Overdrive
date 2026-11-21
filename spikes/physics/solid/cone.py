"""Cone runs and their features (§2.1, data and model alike), for the fitter and the grading.

The features are stage 0's own functions (`stage0/features.py`) applied to the model's series at its step ends:
mass per area in g/m² with area 1, Q'' in kW/m². t_ig is the first step end with Q'' >= 24 kW/m².
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import harness
import materials
import numpy as np
import spec

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE / "stage0"))
import features as stage0_features  # noqa: E402

BANDS: dict[str, Any] = json.loads((HERE / "stage0" / "bands.json").read_text(encoding="utf-8"))
PMMA_DHC = {25: BANDS["pmma"]["dhc_eff_dbi"]["25"]["mean"] * 1e6, 65: BANDS["pmma"]["dhc_eff_dbi"]["65"]["mean"] * 1e6}
PINE_DHC = BANDS["pine"]["dhc_eff"]["pooled_fit_tests"]["mean"] * 1e6  # J/kg
PINE_M_EXT = BANDS["pine"]["m_ext"]["value"] * 1e-3  # kg/m²s
PMMA_FEATURES = ("t_ig", "peak", "t_peak", "mass_lost")
PINE_FEATURES = ("t_ig", "first_peak", "plateau")


@dataclass(frozen=True)
class PmmaParams:
    q_fl: float  # W/m²
    m_flash: float  # kg/m²s


@dataclass(frozen=True)
class PineParams:
    q_fl: float
    m_flash: float
    k_c: float
    eps_char: float


def pmma_run(
    flux: int,
    p: PmmaParams,
    *,
    fit_flux: int,
    dt: float = spec.DT_SHIPPED,
    refine: int = 1,
    m_ext: float | None = None,
    allow_inverted: bool = False,
    fds_h_r: bool = True,
    **backing: Any,
) -> tuple[harness.Series, dict[str, Any]]:
    """DBI's square sample at `flux` with ΔH_c,eff from the fit flux's DBI tests (§3). fds_h_r=False is the model as
    registered (constant H), reported only after V's fix."""
    b = materials.pmma_cone(flux, refine=refine, fds_h_r=fds_h_r, **backing)
    fl = harness.Flame(p.q_fl, p.m_flash, m_ext, PMMA_DHC[fit_flux], allow_inverted)
    s = harness.cone(b, flux=flux * 1e3, flame=fl, dt=dt, t_end=spec.PMMA_T_CAP[flux], stop_after_burnout=True)
    a = s.arrays()
    f = stage0_features.pmma_features(a["t"], a["mass"], a["q"], 1.0)
    return s, dict(f)


def pine_run(
    flux: int,
    p: PineParams,
    *,
    dt: float = spec.DT_SHIPPED,
    refine: int = 1,
    t_end: float | None = None,
    stop_after_flash: float | None = spec.PINE_FIT_AFTER_TIG,
    m_ext: float | None = PINE_M_EXT,
    allow_inverted: bool = False,
    backing: str = "adiabatic",
) -> tuple[harness.Series, dict[str, Any]]:
    b = materials.pine_cone(flux, k_c=p.k_c, eps_char=p.eps_char, refine=refine, backing=backing)
    fl = harness.Flame(p.q_fl, p.m_flash, m_ext, PINE_DHC, allow_inverted)
    s = harness.cone(
        b,
        flux=flux * 1e3,
        flame=fl,
        dt=dt,
        t_end=t_end if t_end is not None else spec.PINE_T_CAP,
        stop_after_burnout=False,
        stop_at=stop_after_flash,
    )
    a = s.arrays()
    f = stage0_features.pine_features(a["t"], a["mass"], a["q"], 1.0)
    return s, dict(f)


def run_class(s: harness.Series, feats: dict[str, Any]) -> dict[str, Any]:
    """The outcome class the resolution rule protects (CHOICE, disclosed): ignited?, flashes, extinctions."""
    return {"ignited": feats.get("t_ig") is not None, "flashes": s.flashes, "extinctions": s.extinctions}


def pine_data_window_end(flux: int) -> float:
    """Mean window end (first m''_60 < 2.7 after the first peak) over the graded tests at a flux (s)."""
    labs = BANDS["pine"]["envelope"][str(flux)]["t_ig"]["labs"]
    vals: list[float] = []
    for lab in sorted(labs):
        for name in labs[lab]["tests"]:
            we = BANDS["pine"]["tests"][name]["features"].get("window_end")
            if we is not None:
                vals.append(float(we))
    return float(sum(vals) / len(vals))


def pmma_data_peak_time(flux: int) -> float:
    return float(BANDS["pmma"]["per_lab"]["DBI_Lund"][str(flux)]["t_peak"]["mean"])


def min_mdot_after(s: harness.Series, t0: float, t1: float) -> float:
    """S1: the smallest m'' (g/m²s) at step ends in [t0, t1]."""
    t = np.array(s.t)
    m = np.array(s.mdot)
    sel = (t >= t0) & (t <= t1)
    return float(m[sel].min()) if sel.any() else math.nan


def mlr10_falls(s: harness.Series, t0: float, t1: float) -> dict[str, Any]:
    """S2: does the model's m''_10 decrease anywhere between flash (t0) and the data's peak time (t1)?"""
    a = s.arrays()
    md = stage0_features.mlr10(a["t"], a["mass"], 1.0)
    sel = (a["t"] >= t0) & (a["t"] <= t1) & np.isfinite(md)
    v = md[sel]
    drops = np.diff(v)
    worst = float(drops.min()) if drops.size else 0.0
    return {"falls": bool(worst < 0.0), "largest_fall_g_m2s": -worst if worst < 0 else 0.0, "samples": int(v.size)}
