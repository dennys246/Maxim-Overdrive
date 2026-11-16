"""Damage: mechanical strikes and heat weakening, both per unit volume so they stay resolution-independent.

A strike deposits ``energy_j`` with a 3-D Gaussian profile of width ``sigma_m`` around a point. Each cell receives
the Gaussian's exact average over the cell (a product of error-function differences, one per axis), so coarse and
fine cells see the same energy density where the profile is smooth. A solid cell loses integrity by
``energy density / fracture_energy`` and becomes air when integrity reaches 0.

That gives a closed-form crater for a strike inside one material: the radius at which the energy density equals
the fracture energy,

    r* = sigma * sqrt(2 * ln(E / (f * (2*pi)^(3/2) * sigma^3)))

which tests/test_damage.py checks every rig against.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import ndimage
from scipy.special import ndtr

from maxim_overdrive.config import AIR_ID
from maxim_overdrive.world.checks import finite_real, finite_vector
from maxim_overdrive.world.grid import Field, MaterialGrid


@dataclass(frozen=True)
class StrikeResult:
    destroyed_cells: int
    destroyed_volume_m3: float
    absorbed_j: float


def _axis_fraction(grid: MaterialGrid, axis: int, center: float, sigma: float) -> Field:
    edges = np.arange(grid.shape[axis] + 1) * grid.dx
    cdf = ndtr((edges - center) / sigma)
    return np.diff(cdf)


def strike(grid: MaterialGrid, point_m: tuple[float, float, float], energy_j: float, sigma_m: float) -> StrikeResult:
    point_m = finite_vector(point_m, 3, "a strike's point_m")  # type: ignore[assignment]
    energy_j = finite_real(energy_j, "a strike's energy_j")
    sigma_m = finite_real(sigma_m, "a strike's sigma_m")
    if energy_j < 0 or sigma_m <= 0:
        raise ValueError(f"a strike needs non-negative energy and positive sigma, got {energy_j!r} J, {sigma_m!r} m")
    fx = _axis_fraction(grid, 0, point_m[0], sigma_m)[:, None, None]
    fy = _axis_fraction(grid, 1, point_m[1], sigma_m)[None, :, None]
    fz = _axis_fraction(grid, 2, point_m[2], sigma_m)[None, None, :]
    cell_energy = energy_j * fx * fy * fz  # J landing in each cell
    density = cell_energy / grid.cell_volume_m3
    solid = grid.solid
    fracture = grid.materials.fracture[grid.material]
    with np.errstate(divide="ignore", invalid="ignore"):
        loss = np.where(solid & (fracture > 0), density / fracture, 0.0)
    grid.integrity -= loss.astype(grid.integrity.dtype)
    gone = solid & (grid.integrity <= 0.0)
    n = grid.destroy(gone)
    absorbed = float(cell_energy[solid].sum())
    return StrikeResult(n, n * grid.cell_volume_m3, absorbed)


def analytic_crater_radius_m(energy_j: float, sigma_m: float, fracture_j_m3: float) -> float:
    """Radius inside which a strike destroys an infinite block of one material (0 if it destroys nothing)."""
    peak = energy_j / ((2 * math.pi) ** 1.5 * sigma_m**3)
    if peak <= fracture_j_m3:
        return 0.0
    return sigma_m * math.sqrt(2.0 * math.log(peak / fracture_j_m3))


def thermal_degrade(grid: MaterialGrid, dt: float) -> int:
    """Weaken cells hotter than their material's limit. Returns cells destroyed this step."""
    above = grid.materials.degrade_above[grid.material]
    excess = grid.temperature - above
    hot = grid.solid & (excess > 0)
    if not hot.any():
        return 0
    rate = grid.materials.degrade_rate[grid.material]
    grid.integrity[hot] -= (rate[hot] * dt * excess[hot] / 100.0).astype(grid.integrity.dtype)
    return grid.destroy(hot & (grid.integrity <= 0.0))


def region_integrity(grid: MaterialGrid, region: str) -> float:
    """Mean integrity over the region's original solid cells, destroyed cells counting 0."""
    mask = grid.regions[region] & (grid.original_material != AIR_ID)
    n = int(mask.sum())
    return float(grid.integrity[mask].clip(min=0.0).sum() / n) if n else 0.0


def region_breached(grid: MaterialGrid, region: str) -> bool:
    """True if destroyed cells form a hole through the region along its thinnest axis (a hole through a wall)."""
    orig = grid.regions[region] & (grid.original_material != AIR_ID)
    if not orig.any():
        return False
    idx = np.argwhere(orig)
    lo, hi = idx.min(axis=0), idx.max(axis=0)
    axis = int(np.argmin(hi - lo))
    holes = orig & (grid.material == AIR_ID)
    if not holes.any():
        return False
    labels, _ = ndimage.label(holes)  # holes is non-empty, so there is at least one component
    first = np.take(labels, lo[axis], axis=axis)
    last = np.take(labels, hi[axis], axis=axis)
    return bool(np.intersect1d(first[first > 0], last[last > 0]).size)
