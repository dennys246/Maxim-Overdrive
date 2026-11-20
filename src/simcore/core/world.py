"""The authoritative world: one grid, its heat sources, and a fixed-length turn.

Godot never simulates; it sends intents and draws snapshots (``simcore.protocol.encoding``). Cradles and experiments
run this same object headless, so the physics an NPC grows up in is the physics of the game.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from simcore.core import damage, heat
from simcore.core.checks import finite_real, finite_vector
from simcore.core.grid import Field, MaterialGrid
from simcore.core.limits import ActionLimits
from simcore.core.materials import MaterialTable
from simcore.core.scene import Scene


@dataclass(frozen=True)
class HeatSource:
    point_m: tuple[float, float, float]
    radius_m: float
    power_w: float

    def __post_init__(self) -> None:
        # Physical validity, whoever builds the source. Gameplay limits (how big a fire may be) belong to the action
        # that asks for it (simcore.core.limits.ActionLimits, checked in simcore.adapters.sem.bridge).
        object.__setattr__(self, "point_m", finite_vector(self.point_m, 3, "a heat source's point_m"))
        radius = finite_real(self.radius_m, "a heat source's radius_m")
        power = finite_real(self.power_w, "a heat source's power_w")
        if radius <= 0 or power < 0:
            raise ValueError(
                f"a heat source needs a positive radius and non-negative power, got {radius!r} m, {power!r} W"
            )
        object.__setattr__(self, "radius_m", radius)
        object.__setattr__(self, "power_w", power)


def sphere_overlap(
    grid: MaterialGrid, center_m: tuple[float, float, float], radius_m: float, samples: int = 4
) -> Field:
    """Fraction of each cell inside a sphere, estimated on a samples^3 sub-grid per cell.

    Weighting by overlap rather than by "centre inside" keeps a source's power density the same at every grid spacing;
    with centre-inside, a 0.3 m fire at 0.2 m cells covered 35% more volume than the sphere and ran cooler.
    """
    offs = (np.arange(samples) + 0.5) / samples * grid.dx
    frac = np.zeros(grid.shape, dtype=np.float64)
    base = [np.arange(n) * grid.dx for n in grid.shape]
    cx, cy, cz = center_m
    for ox in offs:
        dx2 = ((base[0] + ox - cx) ** 2)[:, None, None]
        for oy in offs:
            dy2 = ((base[1] + oy - cy) ** 2)[None, :, None]
            for oz in offs:
                dz2 = ((base[2] + oz - cz) ** 2)[None, None, :]
                frac += (dx2 + dy2 + dz2) <= radius_m**2
    return frac / samples**3


@dataclass
class World:
    grid: MaterialGrid
    turn_seconds: float = 6.0
    sources: dict[str, HeatSource] = field(default_factory=dict)
    turn: int = 0
    # What one action may ask of this world. Required, so a world can't run with no limits or two sets of them.
    limits: ActionLimits = field(kw_only=True)

    @classmethod
    def from_scene(
        cls,
        scene: Scene,
        materials: MaterialTable,
        turn_seconds: float = 6.0,
        *,
        dx_m: float,
        limits: ActionLimits,
    ) -> World:
        """The scene voxelized at grid spacing ``dx_m``, the simulation's one truth (world_model D20)."""
        return cls(scene.build(materials, dx_m=dx_m), turn_seconds, limits=limits)

    def _power_field(self) -> Field | None:
        if not self.sources:
            return None
        power = np.zeros(self.grid.shape, dtype=np.float64)
        for src in self.sources.values():
            frac = sphere_overlap(self.grid, src.point_m, src.radius_m)
            # A fire heats the material it burns on. Air only conducts here (no convection yet), so power dumped
            # into air cells would sit there, and how much of it did would depend on the grid spacing.
            on_solid = frac * self.grid.solid
            weights = on_solid if on_solid.sum() > 0 else frac
            if weights.sum() == 0:  # a source smaller than a cell heats the cell it sits in
                weights = np.zeros(self.grid.shape)
                weights[self.grid.cell_of(src.point_m)] = 1.0
            power += src.power_w * weights / weights.sum()
        return power

    def advance(self, seconds: float | None = None) -> int:
        """Run physics for one turn (or ``seconds``). Returns heat substeps taken."""
        seconds = self.turn_seconds if seconds is None else seconds
        taken = heat.step(
            self.grid,
            seconds,
            min_substeps=heat.min_substeps(self.grid.dx),
            power=self._power_field,
            on_substep=damage.thermal_degrade,
        )
        self.turn += 1
        return taken
