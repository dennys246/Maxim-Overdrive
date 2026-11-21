"""§4's fitter: scipy's differential_evolution with its defaults, `polish=True`, one graded seed (0) and four reported.

Objective: Σ ((model - band centre) / band half-width)² over the fit features at the fit flux(es) only; a feature
the run doesn't produce (no ignition, no plateau) scores FIT_NO_IGNITION_PENALTY (disclosed choice). Parameters are
in kW/m², g/m²s, W/mK and ε (the units only matter to the polish step's finite differences).

    <python> fit.py pmma_forward 0     # PMMA fit at 25 kW/m², seed 0 -> out/fit/pmma_forward_s0.json
    <python> fit.py pmma_reverse 3
    <python> fit.py pine 0
    <python> fit.py pine_aalto_fzj 0   # reported only: the envelope from Aalto and FZJ alone
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import cone
import numpy as np
import numpy.typing as npt
import spec
from scipy.optimize import differential_evolution

HERE = Path(__file__).resolve().parent
OUT = Path(os.environ.get("SOLID_FIT_OUT", str(HERE / "out" / "fit")))  # N8 reruns write elsewhere


def band(lo: float, hi: float) -> tuple[float, float]:
    return 0.5 * (lo + hi), 0.5 * (hi - lo)


def pmma_targets(fit_flux: int) -> dict[str, tuple[float, float]]:
    b = cone.BANDS["pmma"]["per_lab"]["DBI_Lund"][str(fit_flux)]
    return {f: band(b[f]["lo"], b[f]["hi"]) for f in cone.PMMA_FEATURES}


def pine_targets(labs: tuple[str, ...] | None = None) -> dict[tuple[int, str], tuple[float, float]]:
    out: dict[tuple[int, str], tuple[float, float]] = {}
    for flux in spec.PINE_FIT_FLUXES:
        env = cone.BANDS["pine"]["envelope"][str(flux)]
        for f in cone.PINE_FEATURES:
            if labs is None:
                out[(flux, f)] = band(env[f]["lo"], env[f]["hi"])
            else:
                means = [env[f]["labs"][lab]["mean"] for lab in labs if lab in env[f]["labs"]]
                tol = spec.TOL_TIME if f == "t_ig" else None
                lo, hi = min(means), max(means)
                lo, hi = (lo - tol, hi + tol) if tol is not None else (lo * (1 - spec.TOL_REL), hi * (1 + spec.TOL_REL))
                out[(flux, f)] = band(lo, hi)
    return out


def score(value: Any, target: tuple[float, float]) -> float:
    if value is None or not np.isfinite(value):
        return spec.FIT_NO_IGNITION_PENALTY
    c, h = target
    return float(((value - c) / h) ** 2)


def pmma_bounds(fit_flux: int) -> list[tuple[float, float]]:
    lo_flash = spec.Q_IGN / (cone.PMMA_DHC[fit_flux] / 1e6)  # g/m²s: 24 kW/m² ÷ ΔH_c,eff (kJ/g)
    return [(spec.QFL_BOUNDS[0] / 1e3, spec.QFL_BOUNDS[1] / 1e3), (lo_flash, spec.MFLASH_UPPER * 1e3)]


def pine_bounds() -> list[tuple[float, float]]:
    lo_flash = spec.Q_IGN / (cone.PINE_DHC / 1e6)
    return [
        (spec.QFL_BOUNDS[0] / 1e3, spec.QFL_BOUNDS[1] / 1e3),
        (lo_flash, spec.MFLASH_UPPER * 1e3),
        spec.KC_BOUNDS,
        spec.EPS_CHAR_BOUNDS,
    ]


def pmma_params(x: npt.ArrayLike) -> cone.PmmaParams:
    v = np.asarray(x, dtype=float)
    return cone.PmmaParams(float(v[0]) * 1e3, float(v[1]) * 1e-3)


def pine_params(x: npt.ArrayLike) -> cone.PineParams:
    v = np.asarray(x, dtype=float)
    return cone.PineParams(float(v[0]) * 1e3, float(v[1]) * 1e-3, float(v[2]), float(v[3]))


class PmmaObjective:
    def __init__(self, fit_flux: int, fds_h_r: bool = True) -> None:
        self.fit_flux = fit_flux
        self.fds_h_r = fds_h_r
        self.targets = pmma_targets(fit_flux)
        self.calls = 0

    def __call__(self, x: npt.ArrayLike) -> float:
        self.calls += 1
        _, f = cone.pmma_run(self.fit_flux, pmma_params(x), fit_flux=self.fit_flux, fds_h_r=self.fds_h_r)
        return sum(score(f.get(k), t) for k, t in self.targets.items())


class PineObjective:
    def __init__(self, labs: tuple[str, ...] | None = None) -> None:
        self.targets = pine_targets(labs)
        self.calls = 0

    def __call__(self, x: npt.ArrayLike) -> float:
        self.calls += 1
        p = pine_params(x)
        total = 0.0
        for flux in spec.PINE_FIT_FLUXES:
            _, f = cone.pine_run(flux, p, t_end=spec.PINE_FIT_T_CAP)
            total += sum(score(f.get(k), t) for (fl, k), t in self.targets.items() if fl == flux)
        return total


def flags(x: npt.ArrayLike, bounds: list[tuple[float, float]]) -> list[dict[str, Any]]:
    v = np.asarray(x, dtype=float)
    out = []
    for i, (lo, hi) in enumerate(bounds):
        w = hi - lo
        out.append(
            {
                "value": float(v[i]),
                "bounds": [lo, hi],
                "at_lower": bool(v[i] - lo <= spec.FLAG_FRACTION * w),
                "at_upper": bool(hi - v[i] <= spec.FLAG_FRACTION * w),
            }
        )
    return out


def run_fit(name: str, seed: int) -> dict[str, Any]:
    if name == "pmma_forward":
        obj: Any = PmmaObjective(25)
        bounds = pmma_bounds(25)
        names = ["q_fl_kW_m2", "m_flash_g_m2s"]
    elif name == "pmma_reverse":
        obj = PmmaObjective(65)
        bounds = pmma_bounds(65)
        names = ["q_fl_kW_m2", "m_flash_g_m2s"]
    elif name in ("pmma_forward_constH", "pmma_reverse_constH"):  # reported only: the model before V's fix
        ff = 25 if name.startswith("pmma_forward") else 65
        obj = PmmaObjective(ff, fds_h_r=False)
        bounds = pmma_bounds(ff)
        names = ["q_fl_kW_m2", "m_flash_g_m2s"]
    elif name in ("pine", "pine_aalto_fzj"):
        obj = PineObjective(("Aalto", "FZJ") if name == "pine_aalto_fzj" else None)
        bounds = pine_bounds()
        names = ["q_fl_kW_m2", "m_flash_g_m2s", "k_c_W_mK", "eps_char"]
    else:
        raise ValueError(name)
    if len(obj.targets) <= len(bounds):
        raise ValueError("refused: the fit has no more features than parameters (§3's count)")
    t0 = time.process_time()
    load0 = os.getloadavg()
    gen = [0]

    def progress(intermediate_result: Any) -> None:  # logging only; never stops the search
        gen[0] += 1
        print(f"  gen {gen[0]} f={intermediate_result.fun:.6g} x={list(intermediate_result.x)} calls={obj.calls} "
              f"cpu={time.process_time() - t0:.0f}s load={os.getloadavg()[0]:.2f}", flush=True)

    res = differential_evolution(obj, bounds, seed=seed, polish=True, callback=progress)
    cpu = time.process_time() - t0
    return {
        "fit": name,
        "seed": seed,
        "x": [float(v) for v in res.x],
        "names": names,
        "objective": float(res.fun),
        "nfev": int(res.nfev),
        "nit": int(res.nit),
        "success": bool(res.success),
        "message": str(res.message),
        "flags": flags(res.x, bounds),
        "n_features": len(obj.targets),
        "n_params": len(bounds),
        "timing_reported_only": {"cpu_s": cpu, "load_avg_start": list(load0), "load_avg_end": list(os.getloadavg())},
    }


def main(argv: list[str]) -> int:
    name, seed = argv[0], int(argv[1])
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"fit {name} seed {seed}: start (load {os.getloadavg()[0]:.2f})", flush=True)
    r = run_fit(name, seed)
    (OUT / f"{name}_s{seed}.json").write_text(json.dumps(r, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"fit {name} seed {seed}: done x={r['x']} f={r['objective']:.4g} nfev={r['nfev']} cpu={r['timing_reported_only']['cpu_s']:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
