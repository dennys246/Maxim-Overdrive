"""``damage.thermal``, heat weakening per substep (sim_core.md §5): cells hotter than their material's limit lose
integrity, per unit volume and time, and Topology destroys the ones that reach 0."""

from __future__ import annotations

import math
from dataclasses import dataclass

from simcore.core.grid import MaterialGrid
from simcore.core.law import Cadence, Changes, LawInputs
from simcore.core.topology import Destroy


@dataclass(frozen=True)
class ThermalLaw:
    """It reads temperature, which heat writes earlier in the same substep (the tuple's order)."""

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
        grid.integrity[hot] -= (rate[hot] * dt_s * excess[hot] / 100.0).astype(grid.integrity.dtype)
        gone = hot & (grid.integrity <= 0.0)
        return Changes((Destroy(gone),)) if gone.any() else Changes()


THERMAL = ThermalLaw()
