"""Run every Q3 configuration as a child process with an explicit environment and collect results/*.json.

    .venv/bin/python spikes/physics/splitting/experiments.py [--jobs 6]

Each run is `run.py` in its own process. Thread environments for 3b:
  t1:    OMP/OPENBLAS/VECLIB/MKL_NUM_THREADS = 1
  t8:    the same = 8
  unset: none of them set (the library default)
Every other run uses t1. Results land in spikes/physics/splitting/results/<name>.json; a result already present is
reused (delete it to rerun).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PY = str(ROOT / ".venv" / "bin" / "python")
RESULTS = HERE / "results"
THREAD_VARS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "MKL_NUM_THREADS")


def env_for(threads: str) -> dict[str, str]:
    env = {"PATH": "/usr/bin:/bin", "PYTHONHASHSEED": "0", "LC_ALL": "C"}
    if threads != "unset":
        env.update({v: threads for v in THREAD_VARS})
    return env


def configs() -> list[tuple[str, list[str], str]]:
    out = []
    for scen in ("pilot", "established"):
        for dx in ("0.2", "0.1", "0.05"):
            base = ["--dx", dx, "--scenario", scen]
            tag = f"{scen}_{dx}"
            out.append((f"{tag}_lie_fwd_t1", [*base, "--audit"], "1"))
            out.append((f"{tag}_lie_fwd_t1_rerun", [*base, "--audit"], "1"))
            out.append((f"{tag}_lie_fwd_t8", [*base, "--audit"], "8"))
            out.append((f"{tag}_lie_fwd_unset", [*base, "--audit"], "unset"))
            out.append((f"{tag}_strang_fwd", [*base, "--scheme", "strang", "--audit"], "1"))
            out.append((f"{tag}_lie_rev", [*base, "--order", "reverse", "--audit"], "1"))
            out.append((f"{tag}_strang_rev", [*base, "--scheme", "strang", "--order", "reverse", "--audit"], "1"))
            stop = ["--stop-after-gone"] if scen == "established" else []
            out.append((f"{tag}_lie_fwd_ref10", [*base, "--refine", "10", *stop], "1"))
            out.append((f"{tag}_strang_fwd_ref10", [*base, "--scheme", "strang", "--refine", "10", *stop], "1"))
            # added after the first batch showed a 3d outcome flip at 0.2 m: is it a splitting artifact?
            if dx != "0.05":
                out.append((f"{tag}_lie_rev_ref10", [*base, "--order", "reverse", "--refine", "10", *stop], "1"))
                out.append(
                    (
                        f"{tag}_strang_rev_ref10",
                        [*base, "--scheme", "strang", "--order", "reverse", "--refine", "10", *stop],
                        "1",
                    )
                )
    return out


def run_one(name: str, args: list[str], threads: str) -> str:
    dest = RESULTS / f"{name}.json"
    if dest.exists():
        return f"{name}: cached"
    proc = subprocess.run(
        [PY, str(HERE / "run.py"), *args], env=env_for(threads), cwd=ROOT, capture_output=True, text=True, check=False
    )
    if proc.returncode != 0:
        return f"{name}: FAILED\n{proc.stderr[-2000:]}"
    data = json.loads(proc.stdout)
    data["threads_env"] = threads
    dest.write_text(json.dumps(data, indent=1))
    return f"{name}: {data['wall_s']} s"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--jobs", type=int, default=6)
    p.add_argument("--only", default="")
    a = p.parse_args()
    RESULTS.mkdir(exist_ok=True)
    todo = [c for c in configs() if a.only in c[0]]
    # longest first (0.05 m references) so the pool drains evenly
    todo.sort(key=lambda c: ("0.05" not in c[0], "ref10" not in c[0]))
    with ThreadPoolExecutor(max_workers=a.jobs) as pool:
        for msg in pool.map(lambda c: run_one(*c), todo):
            print(msg, flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
