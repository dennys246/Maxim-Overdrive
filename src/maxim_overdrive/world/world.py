"""The authoritative world: one grid, its heat sources, and a fixed-length turn.

Godot (later) never simulates; it sends intents and draws snapshots. Cradles and experiments run this same object
headless, so the physics an NPC grows up in is the physics of the game.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from maxim_overdrive.checks import finite_real, finite_vector
from maxim_overdrive.config import ActionLimits, MaterialTable, RigProfile
from maxim_overdrive.world import damage, heat
from maxim_overdrive.world.grid import Field, MaterialGrid
from maxim_overdrive.world.scene import Scene


@dataclass(frozen=True)
class HeatSource:
    point_m: tuple[float, float, float]
    radius_m: float
    power_w: float

    def __post_init__(self) -> None:
        # Physical validity, whoever builds the source. Gameplay limits (how big a fire may be) belong to the action
        # that asks for it (config.ActionLimits, checked in sem_env.bridge).
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

    Weighting by overlap rather than by "centre inside" keeps a source's power density the same at every rig; with
    centre-inside, a 0.3 m fire at 0.2 m cells covered 35% more volume than the sphere and ran cooler.
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
    rig: RigProfile
    turn_seconds: float = 6.0
    sources: dict[str, HeatSource] = field(default_factory=dict)
    turn: int = 0
    # What one action may ask of this world. Required, so a world can't run with no limits or two sets of them.
    limits: ActionLimits = field(kw_only=True)

    @classmethod
    def from_scene(
        cls,
        scene: Scene,
        rig: RigProfile,
        materials: MaterialTable | None = None,
        turn_seconds: float = 6.0,
        *,
        limits: ActionLimits,
    ) -> World:
        materials = materials or MaterialTable.load()
        return cls(scene.build(rig, materials), rig, turn_seconds, limits=limits)

    def _power_field(self) -> Field | None:
        if not self.sources:
            return None
        power = np.zeros(self.grid.shape, dtype=np.float64)
        for src in self.sources.values():
            frac = sphere_overlap(self.grid, src.point_m, src.radius_m)
            # A fire heats the material it burns on. Air only conducts here (no convection yet), so power dumped
            # into air cells would sit there, and how much of it did would depend on the rig.
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
            min_substeps=self.rig.min_substeps_per_turn,
            power=self._power_field,
            on_substep=damage.thermal_degrade,
        )
        self.turn += 1
        return taken


# Glow starts near the Draper point (~525 °C), where hot solids first emit visible red light.
GLOW_START_C = 525.0
GLOW_FULL_C = 1500.0


def snapshot(grid: MaterialGrid) -> dict[str, object]:
    """Quantized per-cell state for a renderer: the arrays a client uploads as 3-D textures.

    ``crack`` (1 - integrity) and ``glow`` are ready shader inputs, so the finest physical state shows up directly as
    cracks, scorching and glowing metal without the renderer knowing any physics.
    """
    integrity = np.clip(grid.integrity, 0.0, 1.0)
    glow = np.clip((grid.temperature - GLOW_START_C) / (GLOW_FULL_C - GLOW_START_C), 0.0, 1.0) * grid.solid
    return {
        "shape": grid.shape,
        "cell_size_m": grid.dx,
        "time_s": grid.time_s,
        "material": grid.material.copy(),
        "crack": np.round((1.0 - integrity) * grid.solid * 255).astype(np.uint8),
        "glow": np.round(glow * 255).astype(np.uint8),
        "temperature_c": np.clip(grid.temperature, -273.0, 6000.0).astype(np.float16),
    }
