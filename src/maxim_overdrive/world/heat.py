"""Heat conduction on the material grid: explicit finite volumes, insulated outer boundary.

    rho*cp * dT/dt = div(k grad T) + q

Each cell exchanges heat with its six neighbours through a face whose conductance is the harmonic mean of the two
cells' conductivities (the standard choice for a material interface: it keeps flux continuous across it). The outer
boundary is insulated (zero flux), so with no sources total heat energy is conserved exactly, up to rounding.

The step is explicit, so stability bounds its length. ``step`` takes as many substeps as stability needs and never
fewer than the rig asks for: a coarse rig gets cheaper, never unstable. Convection and radiation are not modelled
yet: air here only conducts, which understates how fast a room heats.
"""

from __future__ import annotations

import math
from collections.abc import Callable

import numpy as np

from maxim_overdrive.world.grid import MaterialGrid

STABILITY_SAFETY = 0.9


def _face_conductances(k: np.ndarray) -> list[tuple[int, np.ndarray]]:
    """Harmonic-mean conductivity on the interior faces along each axis."""
    out = []
    for axis in range(3):
        a = np.take(k, np.arange(k.shape[axis] - 1), axis=axis)
        b = np.take(k, np.arange(1, k.shape[axis]), axis=axis)
        denom = a + b
        with np.errstate(divide="ignore", invalid="ignore"):
            kf = np.where(denom > 0, 2.0 * a * b / denom, 0.0)
        out.append((axis, kf))
    return out


def stable_dt(grid: MaterialGrid) -> float:
    """Longest stable explicit step for the grid as it stands now, in seconds."""
    k = grid.materials.conductivity[grid.material]
    rho_cp = grid.materials.rho_cp[grid.material]
    total = np.zeros(grid.shape, dtype=np.float64)
    for axis, kf in _face_conductances(k):
        lo = [slice(None)] * 3
        hi = [slice(None)] * 3
        lo[axis] = slice(0, -1)
        hi[axis] = slice(1, None)
        total[tuple(lo)] += kf
        total[tuple(hi)] += kf
    with np.errstate(divide="ignore"):
        limit = np.where(total > 0, rho_cp * grid.dx**2 / total, np.inf)
    return float(STABILITY_SAFETY * limit.min())


def substep(grid: MaterialGrid, dt: float, power_w: np.ndarray | None = None) -> None:
    """Advance temperature by one explicit step of ``dt`` seconds. ``power_w`` is heat added per cell, in watts."""
    k = grid.materials.conductivity[grid.material]
    rho_cp = grid.materials.rho_cp[grid.material]
    T = grid.temperature
    flux_sum = np.zeros(grid.shape, dtype=np.float64)  # W/m (divided by dx below)
    for axis, kf in _face_conductances(k):
        lo = [slice(None)] * 3
        hi = [slice(None)] * 3
        lo[axis] = slice(0, -1)
        hi[axis] = slice(1, None)
        q = kf * (T[tuple(hi)] - T[tuple(lo)])  # flux from hi into lo, per unit area times dx
        flux_sum[tuple(lo)] += q
        flux_sum[tuple(hi)] -= q
    dT = dt * flux_sum / (rho_cp * grid.dx**2)
    if power_w is not None:
        dT += dt * power_w / (rho_cp * grid.cell_volume_m3)
    T += dT


def step(
    grid: MaterialGrid,
    seconds: float,
    min_substeps: int = 1,
    power_w: np.ndarray | None = None,
    on_substep: Callable[[MaterialGrid, float], int] | None = None,
) -> int:
    """Advance heat by ``seconds``. Returns the number of substeps taken.

    ``on_substep(grid, dt)`` runs after each substep (damage uses it to weaken hot cells) and returns how many cells
    it destroyed. Destroyed cells change the stability bound, so it is recomputed only after a substep that
    destroyed something.
    """
    if seconds <= 0:
        return 0
    n = max(min_substeps, math.ceil(seconds / stable_dt(grid)))
    dt = seconds / n
    taken = 0
    elapsed = 0.0
    changed = False
    while elapsed < seconds - 1e-12:
        if changed:
            dt = min(dt, stable_dt(grid))
        dt = min(dt, seconds - elapsed)
        substep(grid, dt, power_w)
        changed = bool(on_substep(grid, dt)) if on_substep is not None else False
        elapsed += dt
        taken += 1
    grid.time_s += seconds
    return taken


def heat_energy_j(grid: MaterialGrid, reference_c: float = 0.0) -> float:
    """Total heat content relative to ``reference_c``: sum of rho*cp*V*(T - ref)."""
    rho_cp = grid.materials.rho_cp[grid.material]
    return float((rho_cp * (grid.temperature - reference_c)).sum() * grid.cell_volume_m3)
