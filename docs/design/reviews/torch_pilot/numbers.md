# Derived numbers for `torch_pilot.md` (D)

Run with the worktree's `.venv/bin/python` (numpy from `constraints/py3.12.txt`), 2026-11-22.

**Round 1 corrected the draft's numbers** (`round1_executor.md` E-S3, E-S4, E-N4; `round1_physics.md` P-N1, P-N7):
- The draft quoted coverage with the disc centred on a strip edge. Its "84%" was the share of the on-slab energy, not
  of the footprint's.
- Its 346 K concrete rise was at 75 kW/m², not the ceiling.
- Its docstring promised a closed-form check that it didn't contain.

This version does the following:
- It takes each figure over 40 centre offsets within a strip.
- It checks the closed form against quadrature.
- It adds the share of the footprint's energy that misses the slab.
- It adds a 1-D implicit march with re-radiation and convection (ε 0.9, h_c 10 W/m²K; both M).

**The march's first fix** (author, during the fold): its linearised surface loss dropped a +h·T₀ term, which
overstated losses. With that fixed, the lossless march gives 290 K against the closed form's 300 K at 65 kW/m² for
60 s. So the with-loss values below read about 3% low, a first-order surface-node error.

```python
"""Derived numbers for torch_pilot.md, round-1 fold (D). A disc of radius r on a slab of width W, centred on the
slab's centreline, its centre at offset o along the length within one 0.02 m strip (o over 41 points of [0, l)).
Per strip: overlap area by the closed form of min(chord, W) integrated over the strip, checked against fine
trapezoid quadrature. Concrete face: closed form, and a 1-D implicit march with re-radiation and convection."""
import math
import numpy as np

L_SEG = 0.02

def chord_integral(a, b, r, w):
    """Exact integral over y in [a, b] of min(2 sqrt(r^2 - y^2), w), zero outside |y| < r."""
    def F(y):  # antiderivative of 2 sqrt(r^2 - y^2)
        y = max(-r, min(r, y))
        return y * math.sqrt(max(r * r - y * y, 0.0)) + r * r * math.asin(y / r)
    yc = math.sqrt(max(r * r - (w / 2) ** 2, 0.0)) if w < 2 * r else 0.0  # |y| < yc: chord exceeds w
    total = 0.0
    for lo, hi, flat in ((-r, -yc, False), (-yc, yc, True), (yc, r, False)):
        x0, x1 = max(a, lo), min(b, hi)
        if x1 > x0:
            total += w * (x1 - x0) if flat else F(x1) - F(x0)
    return total

def strips(r, w, o):
    n = math.ceil(r / L_SEG) + 2
    edges = [o + k * L_SEG for k in range(-n, n + 1)]
    return [(chord_integral(a, b, r, w), a, b) for a, b in zip(edges[:-1], edges[1:])]

def quad(a, b, r, w, n=20001):
    y = np.linspace(a, b, n)
    return float(np.trapezoid(np.minimum(2 * np.sqrt(np.clip(r * r - y * y, 0, None)), w), y))

worst = max(abs(chord_integral(a, b, 0.07, 0.1) - quad(a, b, 0.07, 0.1)) for _, a, b in strips(0.07, 0.1, 0.0037))
print(f"closed form against quadrature, worst strip: {worst:.2e} m2")
for w, r in [(0.1, 0.05), (0.1, 0.075), (0.1, 0.1), (0.5, 0.05), (0.5, 0.2), (0.3, 0.1)]:
    fmax, on_slab, fbar = [], [], []
    for o in np.linspace(0, L_SEG, 41)[:-1]:
        s = strips(r, w, o)
        areas = np.array([x[0] for x in s])
        f = areas / (L_SEG * w)
        fmax.append(f.max())
        on_slab.append(areas.sum() / (math.pi * r * r))
        fbar.append((areas * f).sum() / areas.sum())
    print(f"W={w} r={r}: most-covered strip f {min(fmax):.3f}-{max(fmax):.3f}; disc energy on the slab "
          f"{min(on_slab):.3f}; energy-weighted mean f {min(fbar):.3f}-{max(fbar):.3f}")

k, rho, c = 1.7, 2400.0, 880.0
def face_rise(q, t, eps=0.9, h=10.0, t0=293.15, dx=5e-4, depth=0.1, dt=0.05):
    n = int(depth / dx); T = np.full(n, t0); a = k * dt / (rho * c * dx * dx)
    for _ in range(int(round(t / dt))):
        Ts = T[0]; g = 4 * eps * 5.670374419e-8 * Ts ** 3 + h  # linearised surface loss
        A = np.zeros((n, n)); bvec = T.copy()
        for i in range(n):
            A[i, i] = 1 + 2 * a
            if i > 0: A[i, i - 1] = -a
            if i < n - 1: A[i, i + 1] = -a
        A[0, 0] = 1 + a + g * dt / (rho * c * dx); A[0, 1] = -a
        loss0 = eps * 5.670374419e-8 * (Ts ** 4 - t0 ** 4) + h * (Ts - t0) - g * (Ts - t0)
        bvec[0] += (q - loss0 + g * t0) * dt / (rho * c * dx)
        A[-1, -1] = 1 + a
        T = np.linalg.solve(A, bvec)
    return T[0] - t0
for q in (45e3, 50e3, 65e3):
    for t in (30.0, 60.0):
        cf = 2 * q * math.sqrt(t) / math.sqrt(math.pi * k * rho * c)
        print(f"concrete face at {q/1e3:.0f} kW/m2, {t:.0f} s: closed form {cf:.0f} K; with losses (eps 0.9, h 10; M) {face_rise(q, t):.0f} K")
print(f"cell mean, 0.1 m cell, 45 kW/m2 on its 0.01 m2 face for 60 s: {45e3*0.01*60/(rho*c*1e-3):.1f} K")
print(f"convective loss at 350 C surface, h_c 10 (M): {10*(350-20)/1e3:.1f} kW/m2")
print(f"rod ring share: {1/math.pi:.3f}; at ceiling 45 kW/m2: {45/math.pi:.1f} kW/m2 ring mean")
```

Output:

```
closed form against quadrature, worst strip: 1.55e-10 m2
W=0.1 r=0.05: most-covered strip f 0.973-0.993; disc energy on the slab 1.000; energy-weighted mean f 0.818-0.830
W=0.1 r=0.075: most-covered strip f 1.000-1.000; disc energy on the slab 0.781; energy-weighted mean f 0.925-0.941
W=0.1 r=0.1: most-covered strip f 1.000-1.000; disc energy on the slab 0.609; energy-weighted mean f 0.954-0.964
W=0.5 r=0.05: most-covered strip f 0.195-0.199; disc energy on the slab 1.000; energy-weighted mean f 0.164-0.166
W=0.5 r=0.2: most-covered strip f 0.799-0.800; disc energy on the slab 1.000; energy-weighted mean f 0.677-0.678
W=0.3 r=0.1: most-covered strip f 0.662-0.666; disc energy on the slab 1.000; energy-weighted mean f 0.560-0.562
concrete face at 45 kW/m2, 30 s: closed form 147 K; with losses (eps 0.9, h 10; M) 134 K
concrete face at 45 kW/m2, 60 s: closed form 208 K; with losses (eps 0.9, h 10; M) 187 K
concrete face at 50 kW/m2, 30 s: closed form 163 K; with losses (eps 0.9, h 10; M) 149 K
concrete face at 50 kW/m2, 60 s: closed form 231 K; with losses (eps 0.9, h 10; M) 207 K
concrete face at 65 kW/m2, 30 s: closed form 212 K; with losses (eps 0.9, h 10; M) 193 K
concrete face at 65 kW/m2, 60 s: closed form 300 K; with losses (eps 0.9, h 10; M) 267 K
cell mean, 0.1 m cell, 45 kW/m2 on its 0.01 m2 face for 60 s: 12.8 K
convective loss at 350 C surface, h_c 10 (M): 3.3 kW/m2
rod ring share: 0.318; at ceiling 45 kW/m2: 14.3 kW/m2 ring mean
```

The lossless march against the closed form, and the with-loss rises at 30 and 60 s:

```
no-loss march vs closed form at 65/60: 290 300
45.0 [134, 187]
50.0 [149, 207]
65.0 [193, 267]
```

**Round 2's onset time** (`delta1_executor.md` E2-N2, `delta1_physics.md` P2-N1): the march above at 45 kW/m², scaled
×300/290 for its surface-node error, gives surface temperatures of 253, 284, 310 and 332 °C at 90, 120, 150 and 180
s. So concrete's 300 °C onset falls at about 140 s with losses, against about 110 s from the lossless closed form.
