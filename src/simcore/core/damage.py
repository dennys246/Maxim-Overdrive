"""Damage: mechanical strikes and heat weakening, both per unit volume so they stay resolution-independent.

Two laws (sim_core.md §5): ``LOADS`` resolves a record's loads (a strike today), and ``THERMAL`` weakens hot cells
each substep. Neither destroys a cell itself: each asks Topology (``simcore.core.topology``) to.

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
from dataclasses import dataclass

import numpy as np
from scipy import ndimage
from scipy.special import ndtr

from simcore.core.grid import CellState, Field, MaterialGrid
from simcore.core.law import Cadence, Changes, LawInputs, Load, LoadEffect
from simcore.core.materials import AIR_ID
from simcore.core.topology import Destroy, Request


def _axis_fraction(grid: MaterialGrid, axis: int, center: float, sigma: float) -> Field:
    edges = np.arange(grid.shape[axis] + 1) * grid.dx
    cdf = ndtr((edges - center) / sigma)
    return np.diff(cdf)


def _strike_loss(grid: MaterialGrid, load: Load) -> tuple[Field, Field]:
    """A strike's energy in each cell (J) and the integrity each cell loses."""
    point_m, energy_j, sigma_m = load.point_m, load.energy_j, load.sigma_m  # finite and in range: Load checks
    fx = _axis_fraction(grid, 0, point_m[0], sigma_m)[:, None, None]
    fy = _axis_fraction(grid, 1, point_m[1], sigma_m)[None, :, None]
    fz = _axis_fraction(grid, 2, point_m[2], sigma_m)[None, None, :]
    cell_energy = energy_j * fx * fy * fz  # J landing in each cell
    density = cell_energy / grid.cell_volume_m3
    fracture = grid.materials.fracture[grid.material]
    with np.errstate(divide="ignore", invalid="ignore"):
        loss = np.where(grid.solid & (fracture > 0), density / fracture, 0.0)
    return cell_energy, loss


@dataclass(frozen=True)
class LoadsLaw:
    """Damage's per-record resolver (sim_core.md §5.1): every mechanical load a record put in, in order. It writes
    integrity and asks Topology to destroy what broke; one resolver per input kind, so every load kind lands here."""

    name: str = "damage.loads"
    version: int = 1
    cadence: Cadence = Cadence.PER_RECORD
    reads: tuple[str, ...] = ("material", "integrity")
    writes: tuple[str, ...] = ("integrity",)

    def stable_dt(self, grid: MaterialGrid) -> float:
        return math.inf

    def step(self, grid: MaterialGrid, dt_s: float, inputs: LawInputs) -> Changes:
        requests: list[Request] = []
        effects: list[LoadEffect] = []
        slated = np.zeros(grid.shape, dtype=np.bool_)  # broken by an earlier load of this batch: counted once
        with grid.as_writer(self.name):
            for load in inputs.loads:
                if load.kind != "strike":
                    raise ValueError(f"damage resolves no {load.kind!r} load yet")  # a programming error
                cell_energy, loss = _strike_loss(grid, load)
                solid = grid.solid
                integrity = grid.integrity  # the window's writable array (an attribute can't be assigned: §4.1)
                integrity -= loss.astype(integrity.dtype)
                gone = solid & (grid.integrity <= 0.0) & ~slated
                slated |= gone
                n = int(gone.sum())  # Topology destroys exactly these: every one is solid now
                requests.append(Destroy(gone))
                effects.append(LoadEffect(n, n * grid.cell_volume_m3, float(cell_energy[solid].sum())))
        return Changes(tuple(requests), tuple(effects))


LOADS = LoadsLaw()


def analytic_crater_radius_m(energy_j: float, sigma_m: float, fracture_j_m3: float) -> float:
    """Radius inside which a strike destroys an infinite block of one material (0 if it destroys nothing)."""
    peak = energy_j / ((2 * math.pi) ** 1.5 * sigma_m**3)
    if peak <= fracture_j_m3:
        return 0.0
    return sigma_m * math.sqrt(2.0 * math.log(peak / fracture_j_m3))


@dataclass(frozen=True)
class ThermalLaw:
    """Heat weakening, per substep: cells hotter than their material's limit lose integrity, and Topology destroys
    the ones that reach 0. It reads temperature, which heat writes earlier in the same substep (the tuple's order)."""

    name: str = "damage.thermal"
    version: int = 1
    cadence: Cadence = Cadence.PER_SUBSTEP
    reads: tuple[str, ...] = ("material", "integrity", "temperature")
    writes: tuple[str, ...] = ("integrity",)

    def stable_dt(self, grid: MaterialGrid) -> float:
        return math.inf

    def step(self, grid: MaterialGrid, dt_s: float, inputs: LawInputs) -> Changes:
        above = grid.materials.degrade_above[grid.material]
        excess = grid.temperature - above
        hot = grid.solid & (excess > 0)
        if not hot.any():
            return Changes()
        rate = grid.materials.degrade_rate[grid.material]
        with grid.as_writer(self.name):
            grid.integrity[hot] -= (rate[hot] * dt_s * excess[hot] / 100.0).astype(grid.integrity.dtype)
        gone = hot & (grid.integrity <= 0.0)
        return Changes((Destroy(gone),)) if gone.any() else Changes()


THERMAL = ThermalLaw()


def region_integrity(grid: CellState, region: str) -> float:
    """Mean integrity over the region's original solid cells, destroyed cells counting 0."""
    mask = grid.regions[region].cells & (grid.original_material != AIR_ID)
    n = int(mask.sum())
    return float(grid.integrity[mask].clip(min=0.0).sum() / n) if n else 0.0


def region_breached(grid: CellState, region: str) -> bool:
    """True if destroyed cells form a hole through the region along its thinnest axis (a hole through a wall)."""
    orig = grid.regions[region].cells & (grid.original_material != AIR_ID)
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
