"""Hot-surface spike runner: one named run per process, results to results/<name>.json (spike, never in src/).

Usage: hot_run.py NAME DX PILOT_TICKS [T_END] [key=value ...]   (PYTHONPATH must include ../bed:../accelerant)
Every run records os.getloadavg() and wall/CPU time beside its numbers.
"""

from __future__ import annotations

import json
import math
import os
import sys
import time

import hotsim
import numpy as np
import wetsim
from hot_constants import NOMINAL

HERE = os.path.dirname(os.path.abspath(__file__))


def parse(kv: list[str]) -> dict:
    out: dict = {}
    for a in kv:
        k, v = a.split("=")
        cur = getattr(NOMINAL, k)
        if isinstance(cur, bool):
            out[k] = v in ("1", "true", "True")
        elif isinstance(cur, int):
            out[k] = int(v)
        elif isinstance(cur, float):
            out[k] = float(v)
        else:
            out[k] = v
    return out


def main() -> None:
    name, dx, ticks = sys.argv[1], float(sys.argv[2]), int(sys.argv[3])
    rest = sys.argv[4:]
    t_end = None
    if rest and "=" not in rest[0]:
        t_end = float(rest[0])
        rest = rest[1:]
    over = parse(rest)
    p = NOMINAL.with_(**over)
    zero = p.surface_mode == "pinned" and p.gas_cap == "tp" and not p.incell_contact
    load0 = os.getloadavg()
    w0, c0 = time.time(), time.process_time()
    r = hotsim.run(p, dx, ticks, t_end=t_end, extras=not zero)
    wall, cpu = time.time() - w0, time.process_time() - c0
    o: dict = {"name": name, "dx": dx, "pilot_ticks": ticks, "overrides": over, "t_end": t_end}
    o["criteria"] = hotsim.criteria(r)
    o["reported"] = hotsim.reported(r, o["criteria"])
    o["ledger"] = wetsim.ledger_checks(r)
    o["ledger_final_MJ"] = {k: v / 1e6 for k, v in r["ledger"][-1].items()}
    o.update(
        digest=r["digest"],
        digest_bed=r["digest_bed"],
        digest_wet=r["digest_wet"],
        liq0_kg=r["liq0"],
        steps=len(r["ledger"]),
        wall_s=wall,
        cpu_s=cpu,
        loadavg_start=load0,
        loadavg_end=os.getloadavg(),
    )
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    with open(os.path.join(HERE, "results", f"{name}.json"), "w") as f:
        json.dump(o, f, indent=1, default=lambda x: None if isinstance(x, float) and math.isnan(x) else x)
    arrays = {k: v for k, v in r.items() if isinstance(v, np.ndarray)}
    np.savez_compressed(os.path.join(HERE, "results", f"{name}.npz"), **arrays)
    c = o["criteria"]
    keys = ("lambda_max", "spread_class", "B1", "B2", "C", "C_F", "t_ignite", "t_out", "wood_at_out_frac")
    print(json.dumps({"name": name, **{k: c[k] for k in keys}, "cpu_s": cpu, "wall_s": wall}, default=str))


if __name__ == "__main__":
    main()
