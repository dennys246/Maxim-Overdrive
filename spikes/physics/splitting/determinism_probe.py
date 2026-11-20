"""Which numpy/scipy operations change bits when the BLAS/OpenMP thread count changes? (3b hazard survey)

    .venv/bin/python spikes/physics/splitting/determinism_probe.py

Runs the same probe in child processes under thread counts 1, 2, 8 and unset (explicit env each), and reports, per
operation, whether the result hash differs across them. Also reports, in-process, layout-dependent reductions:
np.sum over the same values in a contiguous vs a strided view, and np.sum vs a different association order.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PY = str(ROOT / ".venv" / "bin" / "python")
THREAD_VARS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "MKL_NUM_THREADS")


def _h(a) -> str:
    return hashlib.blake2b(np.ascontiguousarray(a).tobytes(), digest_size=8).hexdigest()


def probe() -> dict[str, str]:
    rng = np.random.Generator(np.random.PCG64(12345))
    A = rng.standard_normal((1500, 1500))
    B = rng.standard_normal((1500, 1500))
    x = rng.standard_normal(1500)
    v = rng.standard_normal(4_000_000)
    out = {
        "matmul (A @ B)": _h(A @ B),
        "matvec (A @ x)": _h(A @ x),
        "np.dot(v, v)": _h(np.dot(v, v)),
        "np.einsum optimize=True": _h(np.einsum("ij,jk->ik", A[:300, :300], B[:300, :300], optimize=True)),
        "np.linalg.solve": _h(np.linalg.solve(A, x)),
        "np.sum(v)": _h(np.sum(v)),
        "np.cumsum(v)": _h(np.cumsum(v)),
        "elementwise exp/mul": _h(np.exp(v * 1e-3) * v),
        "np.power(v, 4)": _h(np.power(np.abs(v), 4)),
        "np.bincount weights": _h(np.bincount(rng.integers(0, 1000, v.size), weights=v, minlength=1000)),
    }
    n = 60
    L = sp.diags([-1.0, 2.5, -1.0], [-1, 0, 1], shape=(n, n), format="csc")
    L = (sp.kron(sp.eye(n), L) + sp.kron(L, sp.eye(n))).tocsc()
    b = rng.standard_normal(n * n)
    out["scipy splu solve"] = _h(spla.splu(L).solve(b))
    out["scipy spsolve"] = _h(spla.spsolve(L, b))
    out["scipy cg"] = _h(spla.cg(L, b, rtol=1e-10)[0])
    return out


def layout_checks() -> dict[str, bool]:
    rng = np.random.Generator(np.random.PCG64(7))
    base = rng.standard_normal((200, 200, 200))
    t = np.ascontiguousarray(base.transpose(2, 1, 0))  # same values, different memory order
    return {
        "np.sum C-order == np.sum of transposed copy": bool(np.sum(base) == np.sum(t)),
        "np.sum(contiguous) == np.sum(strided view of the same values)": bool(
            np.sum(base[:, :, ::2].copy()) == np.sum(base[:, :, ::2])
        ),
        "np.sum(x) == sequential python sum(x)": bool(np.sum(base[0, 0]) == sum(base[0, 0].tolist())),
        "x.sum(axis=0).sum() == x.sum()": bool(base.sum(axis=0).sum() == base.sum()),
    }


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--child":
        print(json.dumps(probe()))
        return
    runs = {}
    for threads in ("1", "2", "8", "unset"):
        env = {"PATH": "/usr/bin:/bin", "PYTHONHASHSEED": "0"}
        if threads != "unset":
            env.update({v: threads for v in THREAD_VARS})
        proc = subprocess.run([PY, __file__, "--child"], env=env, cwd=ROOT, capture_output=True, text=True, check=True)
        runs[threads] = json.loads(proc.stdout)
    ops = runs["1"].keys()
    report = {op: {t: runs[t][op] for t in runs} for op in ops}
    differs = {op: len(set(h.values())) > 1 for op, h in report.items()}
    result = {"thread_sensitive": differs, "hashes": report, "layout": layout_checks()}
    print(json.dumps(result, indent=1))
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "determinism_probe.json").write_text(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
