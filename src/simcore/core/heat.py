"""Heat conduction on the material grid: explicit finite volumes, insulated outer boundary.

    rho*cp * dT/dt = div(k grad T) + q

Each cell exchanges heat with its six neighbours through a face whose conductance is the harmonic mean of the two
cells' conductivities (the standard choice for a material interface: it keeps flux continuous across it). The outer
boundary is insulated (zero flux), so with no sources total heat energy is conserved exactly, up to rounding.

The step is explicit, so stability bounds its length. ``step`` takes as many substeps as stability needs and never
fewer than its caller's floor; ``World`` passes ``min_substeps(dx)``, a per-call floor set by the grid spacing.
Convection and radiation are not modelled yet: air here only conducts, which understates how fast a room heats.
"""

from __future__ import annotations

import math
from collections.abc import Callable

import numpy as np

from simcore.core.grid import Field, MaterialGrid

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


def step(
    grid: MaterialGrid,
    seconds: float,
    min_substeps: int = 1,
    power: Callable[[], Field | None] | None = None,
    on_substep: Callable[[MaterialGrid, float], int] | None = None,
) -> int:
    """Advance heat by ``seconds``. Returns the number of substeps taken.

    ``power()`` gives the source power per cell in watts (or None). ``on_substep(grid, dt)`` runs after each substep
    (damage uses it to weaken hot cells) and returns how many cells it destroyed. Destroyed cells change both the
    stability bound and where sources deposit (a fire heats solids, and a destroyed cell is air), so both are
    recomputed after a substep that destroyed something, and only then.
    """
    if seconds <= 0:
        return 0
    n = max(min_substeps, math.ceil(seconds / stable_dt(grid)))
    dt = seconds / n
    taken = 0
    elapsed = 0.0
    changed = False
    power_w = power() if power is not None else None
    while elapsed < seconds - 1e-12:
        if changed:
            dt = min(dt, stable_dt(grid))
            power_w = power() if power is not None else None
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
