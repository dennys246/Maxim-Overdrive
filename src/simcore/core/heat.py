"""Heat conduction on the material grid: explicit finite volumes, insulated outer boundary.

    rho*cp * dT/dt = div(k grad T) + q

Each cell exchanges heat with its six neighbours through a face whose conductance is the harmonic mean of the two
cells' conductivities (the standard choice for a material interface: it keeps flux continuous across it). The outer
boundary is insulated (zero flux), so with no sources total heat energy is conserved exactly, up to rounding.

The step is explicit, so stability bounds its length. The shipped path runs ``HEAT``, this law, in the law tuple
(``simcore.core.physics``), whose fixed physics step takes as many substeps as stability needs, times the config's
``substep_refine`` (sim_core.md §8); there is no accuracy floor. Heat alone is the one-law tuple ``(HEAT,)`` through
the same orchestrator, so time has one mover.
Convection and radiation are not modelled yet: air here only conducts, which understates how fast a room heats.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from simcore.core.deposit import Deposit
from simcore.core.exposure import Exposure
from simcore.core.grid import Field, MaterialGrid
from simcore.core.law import Cadence, Changes, LawInputs, LawState
from simcore.core.readonly import frozen

STABILITY_SAFETY = 0.9
Faces = list[tuple[int, Field]]


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


def face_conductances(grid: MaterialGrid) -> Faces:
    """The grid's interior face conductances as it stands now: a function of ``material`` alone."""
    return _face_conductances(grid.materials.conductivity[grid.material])


def stable_dt(grid: MaterialGrid, faces: Faces | None = None) -> float:
    """Longest stable explicit step for the grid as it stands now, in seconds. ``faces`` are its face conductances,
    computed here when not given."""
    rho_cp = grid.materials.rho_cp[grid.material]
    total = np.zeros(grid.shape, dtype=np.float64)
    for axis, kf in face_conductances(grid) if faces is None else faces:
        lo = [slice(None)] * 3
        hi = [slice(None)] * 3
        lo[axis] = slice(0, -1)
        hi[axis] = slice(1, None)
        total[tuple(lo)] += kf
        total[tuple(hi)] += kf
    with np.errstate(divide="ignore"):
        limit = np.where(total > 0, rho_cp * grid.dx**2 / total, np.inf)
    return float(STABILITY_SAFETY * limit.min())


def substep(grid: MaterialGrid, dt: float, power_w: Field | None = None, faces: Faces | None = None) -> None:
    """Advance temperature by one explicit step of ``dt`` seconds. ``power_w`` is heat added per cell, in watts;
    ``faces`` the face conductances, computed here when not given."""
    rho_cp = grid.materials.rho_cp[grid.material]
    T = grid.temperature
    flux_sum = np.zeros(grid.shape, dtype=np.float64)  # W/m (divided by dx below)
    for axis, kf in face_conductances(grid) if faces is None else faces:
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


class HeatState:
    """Heat's caches for one grid (sim_core.md §7): the sources' deposit, and the face conductances per version of
    ``material``, the only field they read. Built at construction; a rolled-back window empties both."""

    def __init__(self, grid: MaterialGrid) -> None:
        self.deposit = Deposit(grid)
        self._faces: tuple[int, Faces] | None = None
        self._face_builds = 0

    def faces(self, grid: MaterialGrid) -> Faces:
        version = grid.field_version("material")
        if self._faces is None or self._faces[0] != version:
            self._faces = (version, [(axis, frozen(kf)) for axis, kf in face_conductances(grid)])
            self._face_builds += 1
        return self._faces[1]

    def forget(self) -> None:
        self.deposit.forget()
        self._faces = None

    def builds(self) -> dict[str, int]:
        return {"deposit": self.deposit.rebuilds, "face_conductances": self._face_builds}


@dataclass(frozen=True)
class HeatLaw:
    """Conduction plus the heat sources' power, as a per-substep law (sim_core.md §5): it resolves the sources and
    writes temperature, and nothing else. Its bound reads ``material`` alone, so the bound is cached per its
    version."""

    name: str = "heat"
    version: int = 1
    cadence: Cadence = Cadence.PER_SUBSTEP
    reads: tuple[str, ...] = ("material", "temperature")
    writes: tuple[str, ...] = ("temperature",)
    bound_reads: tuple[str, ...] = ("material",)

    def new_state(self, grid: MaterialGrid) -> HeatState:
        return HeatState(grid)

    def prepare(self, grid: MaterialGrid, state: LawState, exposure: Exposure) -> LawInputs:
        """The sources' power per cell over the step (heat resolves sources, sim_core.md §6)."""
        assert isinstance(state, HeatState)
        return LawInputs(power_w=state.deposit.power(exposure.shares, exposure.of_ticks))

    def stable_dt(self, grid: MaterialGrid, state: LawState) -> float:
        assert isinstance(state, HeatState)
        return stable_dt(grid, state.faces(grid))

    def step(self, grid: MaterialGrid, dt_s: float, inputs: LawInputs, state: LawState) -> Changes:
        assert isinstance(state, HeatState)
        substep(grid, dt_s, inputs.power_w, state.faces(grid))  # run as heat by the orchestrator (physics.run_law)
        return Changes()


HEAT = HeatLaw()


def heat_energy_j(grid: MaterialGrid, reference_c: float = 0.0) -> float:
    """Total heat content relative to ``reference_c``: sum of rho*cp*V*(T - ref)."""
    rho_cp = grid.materials.rho_cp[grid.material]
    return float((rho_cp * (grid.temperature - reference_c)).sum() * grid.cell_volume_m3)
