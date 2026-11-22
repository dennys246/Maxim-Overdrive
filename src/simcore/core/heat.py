"""Heat conduction on the material grid: explicit finite volumes, insulated outer boundary.

    rho*cp * dT/dt = div(k grad T) + q

Each cell exchanges heat with its six neighbours through a face whose conductance is the harmonic mean of the two
cells' conductivities (the standard choice for a material interface: it keeps flux continuous across it). The outer
boundary is insulated (zero flux), so with no sources total heat energy is conserved exactly, up to rounding.

The step is explicit, so stability bounds its length. The shipped path runs ``HEAT``, this law, in the law tuple
(``simcore.core.physics``), which takes as many substeps as stability needs and never fewer than its caller's floor;
``World`` passes ``min_substeps(dx)``, a per-call floor set by the grid spacing. ``step`` runs heat alone.
Convection and radiation are not modelled yet: air here only conducts, which understates how fast a room heats.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from simcore.core.grid import Field, MaterialGrid
from simcore.core.law import Cadence, Changes, LawInputs
from simcore.core.stepping import substep_loop

STABILITY_SAFETY = 0.9

# TEMPORARY(phase1/sim-clock): a per-call substep floor kept from the retired rig profiles for bit-identity
# (2026-11-19, plan step 3a); the real fix is step 5a's fixed physics step with an accuracy floor per step length.
# min_substeps(dx) = FLOOR_AREA_M2 / dx^2 gives 4, 16 and 64 substeps at 0.2, 0.1 and 0.05 m, the rigs' old
# min_substeps_per_turn, so results are bit-identical to theirs (digests compared by hand in 3a; the per-turn counts
# are pinned by tests/test_determinism.py::TURN_SUBSTEPS). It is
# not the stability bound, and it is an accuracy floor only at the 6 s turn: it applies per call, whatever the call's
# length, so advance(0.5) at 0.05 m takes 64 substeps of 7.8 ms and advance(600) 64 of 9.4 s. On every 6 s turn the
# floor, not stability, decides the count; dropping it changes every digest, a behaviour change owed to step 5a.
FLOOR_AREA_M2 = 0.16
# The rule is the smallest whole number of substeps at or above FLOOR_AREA_M2 / dx^2, so a substep is never longer
# than 37.5 s * dx^2 / m^2 at the 6 s turn. It gives the rigs' numbers at their spacings (the quotients are
# 3.9999999999999996, 15.999999999999996 and 63.99999999999999, which ceil takes to 4, 16 and 64), and it differs
# from the round() first used here at spacings nothing runs at: at 0.16 m the quotient is 6.25, which round() gave 6
# and this gives 7. Ceiling, not rounding, because a floor that is a bound must not round down.


def min_substeps(dx_m: float) -> int:
    """The fewest substeps one ``step`` call takes at grid spacing ``dx_m`` (at least 1)."""
    return max(1, math.ceil(FLOOR_AREA_M2 / dx_m**2))


def _face_conductances(k: Field) -> list[tuple[int, Field]]:
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


def substep(grid: MaterialGrid, dt: float, power_w: Field | None = None) -> None:
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


@dataclass(frozen=True)
class HeatLaw:
    """Conduction plus the heat sources' power, as a per-substep law (sim_core.md §5): it resolves the sources and
    writes temperature, and nothing else."""

    name: str = "heat"
    version: int = 1
    cadence: Cadence = Cadence.PER_SUBSTEP
    reads: tuple[str, ...] = ("material", "temperature")
    writes: tuple[str, ...] = ("temperature",)

    def stable_dt(self, grid: MaterialGrid) -> float:
        return stable_dt(grid)

    def step(self, grid: MaterialGrid, dt_s: float, inputs: LawInputs) -> Changes:
        with grid.as_writer(self.name):
            substep(grid, dt_s, inputs.power_w)
        return Changes()


HEAT = HeatLaw()


def step(
    grid: MaterialGrid, seconds: float, min_substeps: int = 1, power: Callable[[], Field | None] | None = None
) -> int:
    """Advance heat alone by ``seconds``, inside the window. Returns the number of substeps taken.

    For heat's own closed-form and convergence studies; the shipped path runs every law through
    ``simcore.core.physics.run_physics``, with the same loop (``simcore.core.stepping``). Heat alone changes no cell,
    so the source power ``power()`` (W per cell, or None) is read once."""
    if seconds <= 0:
        return 0
    inputs = LawInputs(power_w=power() if power is not None else None)

    def once(dt: float, _refresh: bool) -> bool:
        HEAT.step(grid, dt, inputs)
        return False

    taken = substep_loop(seconds, min_substeps, lambda: stable_dt(grid), once)
    grid.time_s += seconds
    return taken


def heat_energy_j(grid: MaterialGrid, reference_c: float = 0.0) -> float:
    """Total heat content relative to ``reference_c``: sum of rho*cp*V*(T - ref)."""
    rho_cp = grid.materials.rho_cp[grid.material]
    return float((rho_cp * (grid.temperature - reference_c)).sum() * grid.cell_volume_m3)
