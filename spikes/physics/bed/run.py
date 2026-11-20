"""Spike runner: one named run per process, results to results/<name>.json (spike, never in src/).

Usage: run.py NAME DX PILOT_TICKS [T_END] [key=value ...]
Every run records os.getloadavg() and wall/CPU time beside its numbers.
"""

from __future__ import annotations

import json
import math
import os
import sys
import time

import numpy as np
import sim
from constants import NOMINAL
from model import LEDGER_IN, LEDGER_OUT, LEDGER_STORE

HERE = os.path.dirname(os.path.abspath(__file__))


def parse(kv: list[str]):
    out = {}
    for a in kv:
        k, v = a.split("=")
        cur = getattr(NOMINAL, k)
        if isinstance(cur, bool):
            out[k] = v in ("1", "true", "True")
        elif isinstance(cur, (int, float)):
            out[k] = type(cur)(float(v))
        else:
            out[k] = v
    return out


def deletion_test(ledger: list[dict]) -> dict[str, float]:
    """Worst |residual| / cumulative release over all physics steps, with each line deleted."""
    res = {}
    for line in LEDGER_IN + LEDGER_OUT + LEDGER_STORE:
        worst = 0.0
        for row in ledger:
            r, rel = sim.residual(row, drop=line)
            if rel > 0:
                worst = max(worst, r / rel)
        res[line] = worst
    return res


def main() -> None:
    name, dx, ticks = sys.argv[1], float(sys.argv[2]), int(sys.argv[3])
    rest = sys.argv[4:]
    t_end = None
    if rest and "=" not in rest[0]:
        t_end = float(rest[0])
        rest = rest[1:]
    over = parse(rest)
    p = NOMINAL.with_(**over)
    load0 = os.getloadavg()
    w0, c0 = time.time(), time.process_time()
    r = sim.run(p, dx, ticks, t_end=t_end)
    wall, cpu = time.time() - w0, time.process_time() - c0
    o = sim.observables(r, p)
    o["ledger_deletion"] = deletion_test(r["ledger"])
    last = r["ledger"][-1]
    o["ledger_final_MJ"] = {k: v / 1e6 for k, v in last.items()}
    o.update(
        name=name,
        dx=dx,
        pilot_ticks=ticks,
        overrides=over,
        t_end=t_end,
        wall_s=wall,
        cpu_s=cpu,
        loadavg_start=load0,
        loadavg_end=os.getloadavg(),
        steps=len(r["ledger"]),
    )
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    with open(os.path.join(HERE, "results", f"{name}.json"), "w") as f:
        json.dump(o, f, indent=1, default=lambda x: None if isinstance(x, float) and math.isnan(x) else x)
    ts = {k: v for k, v in r.items() if isinstance(v, np.ndarray)}
    np.savez_compressed(os.path.join(HERE, "results", f"{name}.npz"), **ts)
    print(
        json.dumps(
            {
                k: o[k]
                for k in (
                    "name",
                    "t_ignite",
                    "t_crack",
                    "t_glow",
                    "t_gone",
                    "glow_longest_s",
                    "ember_peak_c",
                    "ember_mean_c",
                    "ledger_worst_rel",
                    "wall_s",
                )
            },
            default=str,
        )
    )


if __name__ == "__main__":
    main()
