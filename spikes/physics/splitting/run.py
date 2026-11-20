"""One run of the Q3 prototype: the Q1 scenario (pilot at tick 70 for 120 s) to the 5,400 s cap.

    .venv/bin/python spikes/physics/splitting/run.py --dx 0.1 --scheme lie --order forward [--refine 10] [--audit]

Prints one JSON object: observables, bound checks, substep statistics, the ledger and a running hash of every state
array at every physics step (3b). Observables (tile §6.3 mapping, see splitting.md):
  t_glow: first physics tick with >= 0.08 m² of envelope face whose envelope-layer skin, the radiometric mean
          (sum w Ts⁴)^(1/4) over the ell-deep column behind the face, is >= 625 °C.
  t_gone: first physics tick with wood + char <= 5% of the initial 32.4 kg (tile §5.5).
  t_ignite: first physics tick with >= 0.1 m² of fuel surface releasing volatiles (tile §6.3 item 2's area).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from laws import FORWARD, stored_energy
from model import CAP_TICKS, T_MAX_BOUND, T_MIN_BOUND, C, fourth, initial_state, prepare
from scheduler import Stats, check_bounds, physics_step

GLOW_K = 625.0 + 273.15
GLOW_AREA = 0.08
IGNITE_AREA = 0.1


def glow_area(s) -> float:
    g = s.geo
    act = ((s.mw + s.mc) > 0).astype(np.float64)
    w = g.face_w * act[g.face_cell]
    num = np.bincount(g.face_ids, weights=w * fourth(s.Ts[g.face_cell]), minlength=g.n_faces)
    den = np.bincount(g.face_ids, weights=w, minlength=g.n_faces)
    hot = (den > 0) & (num >= GLOW_K**4 * den)
    return float(np.count_nonzero(hot)) * g.face_area


def run(dx: float, *, scheme: str, order: str, refine: int, audit: bool, stop_after_gone: bool, scenario: str) -> dict:
    geo = prepare(dx)
    s = initial_state(geo)
    if scenario == "established":  # tile §5.3's design point: the whole bed flaming from t = 0 (no constant changes)
        s.lit[:] = True
    laws = FORWARD if order == "forward" else tuple(reversed(FORWARD))
    ledger: dict[str, float] = {}
    stats = Stats()
    h = hashlib.blake2b(digest_size=16)
    fuel0 = float(np.sum(s.mw))
    e0 = stored_energy(s)
    out: dict = {
        "scenario": scenario,
        "dx": dx,
        "scheme": scheme,
        "order": [law.name for law in laws],
        "refine": refine,
        "t_ignite": None,
        "t_glow": None,
        "t_gone": None,
        "bound_failures": [],
        "fuel0_kg": fuel0,
    }
    peak_ts, worst_close, glow_run, best_glow_run = 0.0, 0.0, 0, 0
    t0 = time.perf_counter()
    while s.tick < CAP_TICKS:
        physics_step(laws, s, ledger, scheme=scheme, refine=refine, stats=stats, audit=audit)
        for a in s.hashed_arrays():
            h.update(np.ascontiguousarray(a).tobytes())
        bad = check_bounds(s, T_MIN_BOUND, T_MAX_BOUND)
        if bad and len(out["bound_failures"]) < 5:
            out["bound_failures"].append({"tick": s.tick, "what": bad})
        peak_ts = max(peak_ts, float(np.max(s.Ts)))
        burning_area = float(np.count_nonzero(s.burning > 0)) * C("sigma_v") * geo.V
        if out["t_ignite"] is None and burning_area >= IGNITE_AREA:
            out["t_ignite"] = s.tick
        ga = glow_area(s)
        glow_run = glow_run + 1 if ga >= GLOW_AREA else 0
        best_glow_run = max(best_glow_run, glow_run)
        if out["t_glow"] is None and ga >= GLOW_AREA:
            out["t_glow"] = s.tick
        fuel = float(np.sum(s.mw) + np.sum(s.mc))
        if out["t_gone"] is None and fuel <= 0.05 * fuel0:
            out["t_gone"] = s.tick
        released = ledger.get("combustion", 0.0)
        if released > 0:
            ins = ledger.get("sources", 0.0) + released
            outs = sum(
                ledger.get(k, 0.0) for k in ("plume_convective", "open_air_loss", "removed_with_mass", "gasification")
            )
            worst_close = max(worst_close, abs(ins - (stored_energy(s) - e0) - outs) / released)
        if stop_after_gone and out["t_gone"] is not None:
            break
    out.update(
        {
            "end_tick": s.tick,
            "wall_s": round(time.perf_counter() - t0, 2),
            "hash": h.hexdigest(),
            "peak_skin_c": peak_ts - 273.15,
            "max_T_c": float(np.max(s.T)) - 273.15,
            "longest_glow_s": best_glow_run * 0.5,
            "fuel_end_kg": float(np.sum(s.mw) + np.sum(s.mc)),
            "substeps_hist": {str(k): v for k, v in sorted(stats.substeps_hist.items())},
            "limiter": stats.limiter,
            "audit_violations": stats.audit_violations,
            "worst_audit_ratio": stats.worst_audit_ratio,
            "ledger_worst_rel_closure": worst_close,
            "ledger": ledger,
        }
    )
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dx", type=float, required=True)
    p.add_argument("--scheme", choices=["lie", "strang"], default="lie")
    p.add_argument("--order", choices=["forward", "reverse"], default="forward")
    p.add_argument("--refine", type=int, default=1)
    p.add_argument("--audit", action="store_true")
    p.add_argument("--stop-after-gone", action="store_true")
    p.add_argument("--scenario", choices=["pilot", "established"], default="pilot")
    a = p.parse_args()
    print(
        json.dumps(
            run(
                a.dx,
                scheme=a.scheme,
                order=a.order,
                refine=a.refine,
                audit=a.audit,
                stop_after_gone=a.stop_after_gone,
                scenario=a.scenario,
            )
        )
    )


if __name__ == "__main__":
    main()
