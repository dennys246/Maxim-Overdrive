"""The strike resolver (sim_core.md §5.1: damage's resolvers, one module per load kind). Not a law: ``damage.loads``
applies what it returns. Per unit volume, so it stays resolution-independent.

A strike deposits ``energy_j`` with a 3-D Gaussian profile of width ``sigma_m`` around a point. Each cell receives
the Gaussian's exact average over the cell (a product of error-function differences, one per axis), so coarse and
fine cells see the same energy density where the profile is smooth. A solid cell loses integrity by
``energy density / fracture_energy`` and becomes air when integrity reaches 0.

That gives a closed-form crater for a strike inside one material: the radius at which the energy density equals
the fracture energy,

    r* = sigma * sqrt(2 * ln(E / (f * (2*pi)^(3/2) * sigma^3)))

which tests/test_damage.py checks at every grid spacing.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.special import ndtr

from simcore.core.geometry import Field
from simcore.core.grid import MaterialGrid
from simcore.core.law import Load


def _axis_fraction(grid: MaterialGrid, axis: int, center: float, sigma: float) -> Field:
    edges = np.arange(grid.shape[axis] + 1) * grid.dx
    cdf = ndtr((edges - center) / sigma)
    return np.diff(cdf)


def loss(grid: MaterialGrid, load: Load) -> tuple[Field, Field]:
    """A strike's energy in each cell (J) and the integrity each cell loses."""
    point_m, energy_j, sigma_m = load.point_m, load.energy_j, load.sigma_m  # finite and in range: Load checks
    fx = _axis_fraction(grid, 0, point_m[0], sigma_m)[:, None, None]
    fy = _axis_fraction(grid, 1, point_m[1], sigma_m)[None, :, None]
    fz = _axis_fraction(grid, 2, point_m[2], sigma_m)[None, None, :]
    cell_energy = energy_j * fx * fy * fz  # J landing in each cell
    density = cell_energy / grid.cell_volume_m3
    fracture = grid.materials.fracture[grid.material]
    with np.errstate(divide="ignore", invalid="ignore"):
        lost = np.where(grid.solid & (fracture > 0), density / fracture, 0.0)
    return cell_energy, lost


def analytic_crater_radius_m(energy_j: float, sigma_m: float, fracture_j_m3: float) -> float:
    """Radius inside which a strike destroys an infinite block of one material (0 if it destroys nothing)."""
    peak = energy_j / ((2 * math.pi) ** 1.5 * sigma_m**3)
    if peak <= fracture_j_m3:
        return 0.0
    return sigma_m * math.sqrt(2.0 * math.log(peak / fracture_j_m3))
