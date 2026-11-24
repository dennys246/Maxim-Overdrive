"""Run FDS 6.11.1 on the 11 pinned gasification inputs and read its device outputs (V, P0).

    <python> fds_driver.py            # run every case not already complete (out/fds/<case>/), log as it goes
    <python> fds_driver.py --force    # rerun all

Each input is copied byte for byte from the verified cache, except the 25 kW/m² inputs' `T_END=800`, which §2 sets to
1500 (the shipped 800 s ends before the peak). FDS runs in its own directory under the git-ignored `out/fds/`, with
`env -i HOME=$PWD PATH=/usr/bin:/bin OMP_NUM_THREADS=1`. Nothing it writes is committed; `results.json` records the
SHA-256 of each input as run and of each device file.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

import inputs
import numpy as np
import numpy.typing as npt

HERE = Path(__file__).resolve().parent
# The FDS 6.11.1 binary (the repo keeps it in .worktrees/_tools): $FDS, else `fds` on the caller's PATH, resolved here
# because run() gives FDS a minimal PATH.
FDS = Path(os.environ.get("FDS") or shutil.which("fds") or "fds")
OUT = HERE / "out" / "fds"
LONG_25 = 1500.0

Array = npt.NDArray[np.float64]


def input_text(case: str) -> str:
    text = inputs.fds_path(case).read_text(encoding="utf-8")
    if case.startswith("25"):
        old = "&TIME T_END=800,DT=0.01/"
        if text.count(old) != 1:
            raise ValueError(f"{case}: expected exactly one {old!r}")
        text = text.replace(old, f"&TIME T_END={LONG_25:.0f},DT=0.01/")
    return text


def case_dir(case: str) -> Path:
    return OUT / case


def chid(case: str) -> str:
    return f"macfp_black_pmma_nist_stmu_fsri_{case}"


def is_complete(case: str) -> bool:
    out = case_dir(case) / f"{chid(case)}.out"
    return out.exists() and "STOP: FDS completed successfully" in out.read_text(encoding="utf-8", errors="replace")


def run(case: str) -> None:
    d = case_dir(case)
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{chid(case)}.fds").write_text(input_text(case), encoding="utf-8")
    env = {"HOME": str(d), "PATH": "/usr/bin:/bin", "OMP_NUM_THREADS": "1"}
    with open(d / "run.log", "w", encoding="utf-8") as log:
        subprocess.run([str(FDS), f"{chid(case)}.fds"], cwd=d, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    if not is_complete(case):
        raise RuntimeError(f"FDS did not complete {case}")


def devc(case: str) -> dict[str, Array]:
    """The device file as {column: values}; columns as the inputs name them."""
    path = case_dir(case) / f"{chid(case)}_devc.csv"
    lines = path.read_text(encoding="utf-8").splitlines()
    names = [n.strip() for n in lines[1].split(",")]
    data = np.array([[float(x) for x in ln.split(",")] for ln in lines[2:] if ln.strip()])
    return {n: data[:, i] for i, n in enumerate(names)}


def hashes(case: str) -> dict[str, str]:
    d = case_dir(case)
    return {
        "input_as_run": hashlib.sha256(input_text(case).encode("utf-8")).hexdigest(),
        "devc": hashlib.sha256((d / f"{chid(case)}_devc.csv").read_bytes()).hexdigest(),
    }


def main(argv: list[str]) -> int:
    inputs.fetch_all()
    force = "--force" in argv
    for case in inputs.FDS_CASES:
        if force or not is_complete(case):
            print(f"fds: {case} running (load {os.getloadavg()[0]:.2f})", flush=True)
            run(case)
        print(f"fds: {case} complete {hashes(case)['devc'][:12]}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
