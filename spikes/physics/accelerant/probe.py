"""Diagnostic (not graded): how hot do the unlit surfaces next to the flames get? Prints every 60 s for 600 s.

Usage: probe.py DX   (PYTHONPATH must include ../bed). Quoted in results.md §3 (spike, never in src/).
"""

from __future__ import annotations

import sys

from acc_constants import NOMINAL
from wetbed import WetBed


def main() -> None:
    dx = float(sys.argv[1]) if len(sys.argv) > 1 else 0.2
    b = WetBed(NOMINAL, dx, 6000)
    for step in range(1200):
        b.physics_step()
        if step % 120 == 119:
            cand = b._flame_neighbourhood() & (b.A_ui > 0)
            tu = b.Tu[..., 0] - 273.15
            print(
                f"t={b.t:6.1f} s  flaming cells {int(b.flaming.sum()):3d}  lit {float(b.lit_cum.sum()):.4f} m2  "
                f"hottest unlit skin next to a flame {float(tu[cand].max()) if cand.any() else float('nan'):6.1f} C  "
                f"(needs {NOMINAL.t_b_c:.0f} C)  draught {float(b.Gcol.sum() * b.Af) * 1e3:5.1f} g/s"
            )


if __name__ == "__main__":
    main()
