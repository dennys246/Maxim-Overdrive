# Derived numbers for `torch_pilot.md` (D)

Run with the worktree's `.venv/bin/python` (numpy from `constraints/py3.12.txt`), 2026-11-22. Strips are 0.02 m
(`fire_solid.md` §1.2); the disc is centred on the slab's centreline; overlap per strip by 2×10⁵-point trapezoid
integration of min(chord, W). Concrete from `data/materials/core.yaml` (k 1.7, ρ 2400, c 880).

```python
"""Derived numbers for the torch-pilot note (D). Disc of radius r centred on a slab's centreline, width W,
strips of length l along the slab. Exact areas by fine 1-D integration of the chord (closed form check)."""
import math
import numpy as np

def chord_cover(y, r, W):
    # covered width of a strip line at offset y along the slab length: min(chord, W)
    c = 2*np.sqrt(np.clip(r*r - y*y, 0, None))
    return np.minimum(c, W)

def strip_stats(r, W, l=0.02, n=200000):
    edges = np.arange(-math.ceil(r/l)*l, math.ceil(r/l)*l + l/2, l)
    full_e, tot_e, worst_central = 0.0, 0.0, None
    rows = []
    for a, b in zip(edges[:-1], edges[1:]):
        y = np.linspace(a, b, n)
        cov = np.trapezoid(chord_cover(y, r, W), y)  # overlap area of the strip
        f = cov / (l*W)
        rows.append((a, b, f, cov))
        tot_e += cov
        if f > 1 - 1e-9:
            full_e += cov
    fc = max(r_[2] for r_ in rows)
    return full_e/tot_e, fc, rows

for W, r in [(0.1, 0.05), (0.1, 0.1), (0.1, 0.2), (0.5, 0.05), (0.5, 0.2), (0.3, 0.1)]:
    frac, fmax, rows = strip_stats(r, W)
    print(f"W={W} r={r}: energy in fully covered strips {frac:.3f}; max strip coverage {fmax:.3f}")

# cold-face bound: semi-infinite concrete under constant q for t: dT_s = 2 q sqrt(t) / sqrt(pi k rho c)
k, rho, c = 1.7, 2400, 880
for q in (25e3, 75e3):
    for t in (30, 60):
        print(f"concrete face rise at {q/1e3:.0f} kW/m2, {t} s: {2*q*math.sqrt(t)/math.sqrt(math.pi*k*rho*c):.0f} K")
# a 0.1 m cell's mean rise from the same energy over one 0.1 x 0.1 face
for q in (75e3,):
    E = q*0.01*60
    print(f"cell-mean rise, 0.1 m concrete cell, {q/1e3:.0f} kW/m2 over its 0.01 m2 face for 60 s: {E/(rho*c*1e-3):.1f} K")
# rod circumferential dilution: projected width 2R over circumference 2 pi R
print("rod: share of ring heated by a footprint wider than the rod:", 1/math.pi)
```

Output:

```
W=0.1 r=0.05: energy in fully covered strips 0.000; max strip coverage 0.973
W=0.1 r=0.1: energy in fully covered strips 0.836; max strip coverage 1.000
W=0.1 r=0.2: energy in fully covered strips 0.910; max strip coverage 1.000
W=0.5 r=0.05: energy in fully covered strips 0.000; max strip coverage 0.195
W=0.5 r=0.2: energy in fully covered strips 0.000; max strip coverage 0.799
W=0.3 r=0.1: energy in fully covered strips 0.000; max strip coverage 0.662
concrete face rise at 25 kW/m2, 30 s: 82 K
concrete face rise at 25 kW/m2, 60 s: 115 K
concrete face rise at 75 kW/m2, 30 s: 245 K
concrete face rise at 75 kW/m2, 60 s: 346 K
cell-mean rise, 0.1 m concrete cell, 75 kW/m2 over its 0.01 m2 face for 60 s: 21.3 K
rod: share of ring heated by a footprint wider than the rod: 0.3183098861837907
```
