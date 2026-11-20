"""Q3 splitting prototype: the crate region, its state, and four operator-split laws.

Throwaway spike code (preregistration.md): never imported by src/. Every law has the architecture review's shape
(docs/design/reviews/flexibility/architecture.md #1, #5): ``prepare`` runs once (static geometry, weights), and
``stable_dt(state)`` / ``step(state, dt, ledger)`` are array-only kernels over plain numpy arrays.

Units are SI and kelvin throughout. Constants are tile_and_client.md §5.1 values (tagged there *from memory*; Q1
owns their verification). Nothing here is tuned: see CONSTANTS for each one's provenance.

Domain: a 1.0 m cube, insulated outside (as heat.py). z 0-0.2 m concrete floor; the 0.6 m crate bed on it at
x, y 0.2-0.8, z 0.2-0.8; air elsewhere. Bed envelope = top + four sides = 1.8 m² (tile §5.3).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

SIGMA_SB = 5.670374419e-8  # W/m²K⁴, CODATA 2018
T_AMB = 293.15  # 20 °C open air (preregistration rules)

# value, units, source, verified?
CONSTANTS = {
    "phi": (0.25, "-", "tile §1.1 / T15", "design value"),
    "sigma_v": (25.0, "m²/m³", "tile §1.1 (2φ/δ, δ = 20 mm)", "derived"),
    "rho_wood": (600.0, "kg/m³", "data/materials/core.yaml wood", "textbook, from memory"),
    "c_wood": (1700.0, "J/kgK", "data/materials/core.yaml wood", "textbook, from memory"),
    "k_wood": (0.15, "W/mK", "data/materials/core.yaml wood", "textbook, from memory"),
    "rho_air": (1.2, "kg/m³", "data/materials/core.yaml air", "textbook"),
    "c_air": (1005.0, "J/kgK", "data/materials/core.yaml air", "textbook"),
    "k_air": (0.026, "W/mK", "data/materials/core.yaml air", "textbook"),
    "rho_conc": (2400.0, "kg/m³", "data/materials/core.yaml concrete", "textbook, from memory"),
    "c_conc": (880.0, "J/kgK", "data/materials/core.yaml concrete", "textbook, from memory"),
    "k_conc": (1.7, "W/mK", "data/materials/core.yaml concrete", "textbook, from memory"),
    "dHc": (12.4e6, "J/kg volatiles", "tile §5.1", "from memory"),
    "chi_char": (0.25, "-", "tile §5.1", "from memory"),
    "dH_char": (32.8e6, "J/kg char", "tile §5.1 (CO2)", "from memory"),
    "L_g": (1.8e6, "J/kg volatiles", "tile §5.1", "from memory"),
    "T_p": (380.0 + 273.15, "K", "tile §5.1", "from memory"),
    "q_f": (25.0e3, "W/m² burning fuel surface", "tile §5.1 (range 15-35)", "from memory"),
    "eps": (0.9, "-", "tile §5.1", "from memory"),
    "h_c": (10.0, "W/m²K", "tile §5.1", "from memory"),
    "skin_depth": (0.001, "m", "tile §5.2 6b", "[engineering]"),
    "ell": (0.16, "m", "tile §5.2 6a, 4/sigma_v", "derived"),
    "m_char_flux": (0.86e-3, "kg/m²s", "tile §5.2 6d", "derived"),
    "pilot_power": (2000.0, "W", "tile §3.2 torch", "from memory"),
    "pilot_radius": (0.2, "m", "tile §3.2 torch", "from memory"),
    "chf": (12.0e3, "W/m²", "tile §5.1 critical heat flux", "from memory"),
    "slat": (0.020, "m", "tile T15 slat thickness", "design value"),
}


def C(name: str) -> float:
    return float(CONSTANTS[name][0])


STABILITY_SAFETY = 0.9  # as heat.py
PHYSICS_TICKS = 5  # T3: physics every 5 ticks of 0.1 s
TICK_S = 0.1
PILOT_START_TICK = 70  # tile §6.2
PILOT_TICKS = 1200  # 120 s: an assumption of this spike (tile leaves D to step 6's band), 2x the tile's ~60 s ignite
CAP_TICKS = 54_000  # tile §6.2 cap, 5,400 s

# Physical bounds for 3a, fixed before any run: nothing in the model is colder than ambient, and nothing can be
# hotter than an adiabatic wood-volatile flame (~2,300 K is above any wood flame's adiabatic temperature).
T_MIN_BOUND = T_AMB - 0.5
T_MAX_BOUND = 2300.0

AIR, CONC, BED = 0, 1, 2
BED_LO = np.array([0.2, 0.2, 0.2])
BED_HI = np.array([0.8, 0.8, 0.8])
EXTENT = 1.0
ENVELOPE_AREA = 1.8  # top + 4 sides of 0.36 m²


@dataclass
class State:
    """Everything a law reads or writes. Fields 'T', 'Ts', 'mw', 'mc' are the evolving state (hashed for 3b)."""

    dx: float
    T: np.ndarray  # bulk cell temperature, shape (n, n, n)
    Ts: np.ndarray  # skin temperature per bed cell, shape (nb,)
    mw: np.ndarray  # virgin wood per bed cell, kg
    mc: np.ndarray  # char per bed cell, kg
    tick: int = 0
    geo: Geometry = field(repr=False, default=None)  # type: ignore[assignment]
    pilot_w: float = 0.0  # pilot power for the current physics step, W (scheduler sets it)
    burning: np.ndarray | None = None  # per bed cell: volatiles released in the last bed substep (kg)
    lit: np.ndarray | None = None  # per bed cell: flaming latch (bool)
    pilot_ticks: int = 0  # ticks of pilot exposure so far (integer: no float time accumulation)

    def hashed_arrays(self) -> tuple[np.ndarray, ...]:
        return (self.T, self.Ts, self.mw, self.mc, self.lit)


@dataclass
class Geometry:
    """Static, prepared once per grid (the architecture review's ``prepare``)."""

    n: int
    dx: float
    V: float
    mat: np.ndarray  # (n, n, n) int8
    bed_flat: np.ndarray  # flat indices of bed cells
    env_w: np.ndarray  # (nb,) envelope area share: loss of cell i = q''(Ts_i) * A_env * env_w_i
    pilot_frac: np.ndarray  # (nb,) share of the pilot's power each bed cell's skin receives
    pilot_cover: np.ndarray  # (nb,) fraction of the cell's west face under the disc (0 off the face layer)
    face_ids: np.ndarray  # glow observable: (face, bed cell, weight) triplets
    face_cell: np.ndarray
    face_w: np.ndarray
    n_faces: int
    face_area: float
    p1: object  # scipy SuperLU factor of the bed's P1 (screened Poisson) operator for flame radiation
    p1_absorb: np.ndarray  # (nb,) beta * V: absorbed power per unit G
    skin_nbrs: tuple  # (i, j) bed-cell index pairs across interior bed faces, for in-bed radiation between skins
    k_static: np.ndarray  # (n, n, n) conductivity of cores, air and concrete (no radiative term)
    rhoc_static: np.ndarray  # (n, n, n) heat capacity per volume for non-bed cells (bed cells overwritten)


def _overlap_1d(a0: np.ndarray, a1: np.ndarray, b0: float, b1: float) -> np.ndarray:
    return np.clip(np.minimum(a1, b1) - np.maximum(a0, b0), 0.0, None)


def _layer_fraction(lo: np.ndarray, hi: np.ndarray, sub: int = 16) -> np.ndarray:
    """Fraction of each bed cell's volume within ell of an exposed face (5 faces), by sub-sampling.

    Exact as sub grows.
    """
    ell = C("ell")
    s = (np.arange(sub) + 0.5) / sub
    out = np.zeros(lo.shape[0])
    for i in range(lo.shape[0]):
        xs = lo[i, 0] + s * (hi[i, 0] - lo[i, 0])
        ys = lo[i, 1] + s * (hi[i, 1] - lo[i, 1])
        zs = lo[i, 2] + s * (hi[i, 2] - lo[i, 2])
        X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
        d = np.minimum.reduce([X - BED_LO[0], BED_HI[0] - X, Y - BED_LO[1], BED_HI[1] - Y, BED_HI[2] - Z])
        out[i] = np.count_nonzero(d < ell) / sub**3
    return out


def _disc_fraction(y0: np.ndarray, y1: np.ndarray, z0: np.ndarray, z1: np.ndarray, sub: int = 64) -> np.ndarray:
    """Area of the pilot disc (on the west face) inside each [y0,y1]x[z0,z1] footprint, by sub-sampling."""
    cy, cz, r = 0.525, 0.525, C("pilot_radius")  # tile §6.2 point (6000, 2925, 725) mm in local metres
    s = (np.arange(sub) + 0.5) / sub
    out = np.zeros(y0.shape[0])
    for i in range(y0.shape[0]):
        Y, Z = np.meshgrid(y0[i] + s * (y1[i] - y0[i]), z0[i] + s * (z1[i] - z0[i]), indexing="ij")
        inside = (Y - cy) ** 2 + (Z - cz) ** 2 <= r * r
        out[i] = np.count_nonzero(inside) / sub**2 * (y1[i] - y0[i]) * (z1[i] - z0[i])
    return out


def prepare(dx: float) -> Geometry:
    n = round(EXTENT / dx)
    c = (np.arange(n) + 0.5) * dx
    X, Y, Z = np.meshgrid(c, c, c, indexing="ij")
    mat = np.zeros((n, n, n), dtype=np.int8)
    mat[Z < 0.2] = CONC
    inbed = (BED_LO[0] < X) & (BED_HI[0] > X) & (BED_LO[1] < Y) & (BED_HI[1] > Y) & (BED_LO[2] < Z) & (BED_HI[2] > Z)
    mat[inbed] = BED
    bed_flat = np.flatnonzero(mat.ravel() == BED)
    ix, iy, iz = np.unravel_index(bed_flat, mat.shape)
    lo = np.stack([ix, iy, iz], axis=1) * dx
    hi = lo + dx
    V = dx**3

    layer = _layer_fraction(lo, hi)
    env_w = layer * V / float(np.sum(layer * V))

    # tile §3.2: the disc lands by face-area overlap on the skin behind the west face (the first bed cell)
    xdepth = (np.abs(lo[:, 0] - BED_LO[0]) < 0.5 * dx).astype(np.float64)
    disc = _disc_fraction(lo[:, 1], hi[:, 1], lo[:, 2], hi[:, 2])
    pilot_frac = xdepth * disc / float(np.sum(xdepth * disc))  # sums to 1: the pilot's energy is exact
    pilot_cover = xdepth * disc / (dx * dx)

    face_ids, face_cell, face_w, nf = _envelope_faces(ix, iy, iz, dx)
    p1, nbrs = _p1_operator(mat, bed_flat, dx)

    k_static = np.where(mat == CONC, C("k_conc"), C("k_air"))
    k_static = np.where(mat == BED, C("phi") * C("k_wood") + (1 - C("phi")) * C("k_air"), k_static)
    rhoc_static = np.where(mat == CONC, C("rho_conc") * C("c_conc"), C("rho_air") * C("c_air"))
    return Geometry(
        n,
        dx,
        V,
        mat,
        bed_flat,
        env_w,
        pilot_frac,
        pilot_cover,
        face_ids,
        face_cell,
        face_w,
        nf,
        dx * dx,
        p1,
        np.full(bed_flat.size, C("sigma_v") / 4.0 * V),
        nbrs,
        k_static.astype(np.float64),
        rhoc_static.astype(np.float64),
    )


def _envelope_faces(ix, iy, iz, dx):
    """Each exposed bed face, and the bed cells in the ell-deep column behind it with depth-overlap weights."""
    ell = C("ell")
    index = {(int(a), int(b), int(c)): k for k, (a, b, c) in enumerate(zip(ix, iy, iz, strict=True))}
    nb_lo = np.round(BED_LO / dx).astype(int)
    nb_hi = np.round(BED_HI / dx).astype(int) - 1
    faces, cells, weights = [], [], []
    nf = 0
    # (axis, side): side -1 = low face, +1 = high face; bottom (axis 2, low) sits on concrete, so not envelope
    for axis, side in [(0, -1), (0, 1), (1, -1), (1, 1), (2, 1)]:
        for key in zip(ix, iy, iz, strict=True):
            edge = nb_lo[axis] if side < 0 else nb_hi[axis]
            if key[axis] != edge:
                continue
            for depth in range(nb_hi[axis] - nb_lo[axis] + 1):
                cell = list(key)
                cell[axis] = edge - side * depth
                d0, d1 = depth * dx, (depth + 1) * dx
                w = max(0.0, min(d1, ell) - d0) / ell
                if w <= 0:
                    break
                faces.append(nf)
                cells.append(index[tuple(cell)])
                weights.append(w)
            nf += 1
    return np.array(faces), np.array(cells), np.array(weights), nf


def _p1_operator(mat: np.ndarray, bed_flat: np.ndarray, dx: float):
    """Flame radiation in the bed by the P1 (diffusion) approximation with extinction beta = sigma_v/4 (tile 6a):
        beta V G_j + sum_faces D dx (G_j - G_k) = s_j,  D = 1/(3 beta),
    and G = 0 half a cell outside the bed (radiation leaving the bed is not returned). Factorised once (SuperLU:
    single-threaded, so the solve is deterministic). Also returns the interior bed-face neighbour pairs."""
    beta = C("sigma_v") / 4.0
    D = 1.0 / (3.0 * beta)
    nb = bed_flat.size
    where = -np.ones(mat.size, dtype=np.int64)
    where[bed_flat] = np.arange(nb)
    where = where.reshape(mat.shape)
    diag = np.full(nb, beta * dx**3)
    rows, cols, vals = [], [], []
    pi, pj = [], []
    n = mat.shape[0]
    for axis in range(3):
        for sgn in (-1, 1):
            shifted = np.full(mat.shape, -1, dtype=np.int64)
            src = [slice(None)] * 3
            dst = [slice(None)] * 3
            if sgn > 0:
                src[axis], dst[axis] = slice(1, None), slice(0, -1)
            else:
                src[axis], dst[axis] = slice(0, -1), slice(1, None)
            shifted[tuple(dst)] = where[tuple(src)]
            me = where.ravel()
            nbr = shifted.ravel()
            ok = me >= 0
            inner = ok & (nbr >= 0)
            outer = ok & (nbr < 0)
            diag[me[inner]] += D * dx
            rows.append(me[inner])
            cols.append(nbr[inner])
            vals.append(np.full(int(inner.sum()), -D * dx))
            diag[me[outer]] += 2.0 * D * dx
            if sgn > 0:
                pi.append(me[inner])
                pj.append(nbr[inner])
    del n
    rows.append(np.arange(nb))
    cols.append(np.arange(nb))
    vals.append(diag)
    A = sp.csc_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(nb, nb))
    return spla.splu(A), (np.concatenate(pi), np.concatenate(pj))


def initial_state(geo: Geometry) -> State:
    nb = geo.bed_flat.size
    wood0 = C("phi") * C("rho_wood") * geo.V
    T = np.full((geo.n,) * 3, T_AMB)
    return State(
        dx=geo.dx,
        T=T,
        Ts=np.full(nb, T_AMB),
        mw=np.full(nb, wood0),
        mc=np.zeros(nb),
        geo=geo,
        burning=np.zeros(nb),
        lit=np.zeros(nb, dtype=bool),
    )


def ignition_time_s() -> float:
    """Thermally thick piloted ignition under a constant flux (tile §5.3's closed form):
    t_ig = (π/4) k rho c (T_p - T_amb)² / q''², with q'' the pilot's flux over its disc."""
    q = C("pilot_power") / (np.pi * C("pilot_radius") ** 2)
    krc = C("k_wood") * C("rho_wood") * C("c_wood")
    return float(np.pi / 4.0 * krc * (C("T_p") - T_AMB) ** 2 / (q * q))


# ----------------------------------------------------------------------------------------------------------------
# Shared kernels


def fuel_active(s: State) -> np.ndarray:
    return (s.mw + s.mc) > 0.0


def skin_capacity(s: State) -> np.ndarray:
    """J/K per bed cell: a 1 mm layer over the cell's fuel surface; zero once the cell's fuel is gone."""
    full = C("rho_wood") * C("c_wood") * C("skin_depth") * C("sigma_v") * s.geo.V
    return np.where(fuel_active(s), full, 0.0)


def bed_capacity(s: State) -> np.ndarray:
    """J/K per bed cell, bulk: remaining solid plus the pore air."""
    return (s.mw + s.mc) * C("c_wood") + C("rho_air") * C("c_air") * (1 - C("phi")) * s.geo.V


def cell_rhoc(s: State) -> np.ndarray:
    rhoc = s.geo.rhoc_static.copy()
    rhoc.flat[s.geo.bed_flat] = bed_capacity(s) / s.geo.V
    return rhoc


def fourth(x: np.ndarray) -> np.ndarray:
    """x**4 by two multiplies: avoids np.power's version-dependent fast paths (a determinism hazard, splitting.md)."""
    x2 = x * x
    return x2 * x2


def cell_k(s: State) -> np.ndarray:
    """Bulk conductivity: cores and pore air in a bed cell, air once its fuel is gone, else static."""
    k = s.geo.k_static.copy()
    k.flat[s.geo.bed_flat] = np.where(fuel_active(s), k.flat[s.geo.bed_flat], C("k_air"))
    return k


def k_rad(Ts: np.ndarray) -> np.ndarray:
    """Rosseland radiative conductivity of the slat array, 16 sigma T³/(3β), β = sigma_v/4.

    Re-radiation between skins.
    """
    return 16.0 * SIGMA_SB * Ts * Ts * Ts / (3.0 * C("sigma_v") / 4.0)
