"""E4(ii): with the new terms on, the state equals the parent's at every step before the first flaming area
(preregistration §3; spike, never in src/). The parent of S is the bed run through WetBed at zero loading, which the
accelerant spike showed is the bed bit for bit; the parent of K is WetBed itself.

Usage: identity.py   (PYTHONPATH=../bed:../accelerant); the output is results/identity.txt.
"""

from __future__ import annotations

import hashlib

import numpy as np
from acc_constants import NOMINAL as ACC
from hot_constants import NOMINAL as HOT
from hotbed import HotBed
from wetbed import WetBed

ARRAYS = ("Tu", "T_ic", "G", "c_ic", "Lu", "Lup", "Tia", "Lia", "A_ia", "A_iw", "Ts_iw", "c_iw", "Gcol", "Tup")


def digest(b: WetBed) -> str:
    h = hashlib.sha256()
    for name in ARRAYS:
        h.update(np.ascontiguousarray(getattr(b, name)).tobytes())
    return h.hexdigest()


def compare(label: str, loading: float, dx: float) -> str:
    parent = WetBed(ACC.with_(loading_wood=loading), dx, 6000)
    hot = HotBed(HOT.with_(loading_wood=loading), dx, 6000)
    steps = 0
    while not parent.flaming.any() and not hot.flaming.any() and steps < 3600:
        parent.physics_step()
        hot.physics_step()
        steps += 1
        if parent.flaming.any() or hot.flaming.any():
            break
        if digest(parent) != digest(hot):
            return f"{label} dx={dx}: MISS, states differ at t={hot.t:.1f} s before any flame"
    same = parent.flaming.any() and hot.flaming.any() and parent.t == hot.t
    return (
        f"{label} dx={dx}: {steps - 1} steps identical before the first flame; first flaming area in both at "
        f"t={hot.t:.1f} s  {'PASS' if same else 'MISS'}"
    )


def main() -> None:
    for label, loading in (("S", 0.0), ("K", 64.0)):
        for dx in (0.2, 0.1, 0.05):
            print(compare(label, loading, dx), flush=True)


if __name__ == "__main__":
    main()
