"""Scenes are authored in metres and voxelized per rig.

Nothing is authored in cells. A scene is a list of primitives with a material and an optional name; the rig's cell
size decides how finely it is sampled. Imagination produces the same specs (``imagination.spec``), so an imagined
object is made of the same cells, burns and breaks like anything else, and needs no special case.

A cell belongs to a primitive when its centre lies inside it; later primitives overwrite earlier ones.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np

from maxim_overdrive.config import MaterialTable, RigProfile
from maxim_overdrive.world.grid import MaterialGrid


@dataclass(frozen=True)
class Box:
    min_m: tuple[float, float, float]
    max_m: tuple[float, float, float]
    material: str
    name: str | None = None
    kind: Literal["box"] = "box"

    def mask(self, grid: MaterialGrid) -> np.ndarray:
        x, y, z = grid.mesh()
        (x0, y0, z0), (x1, y1, z1) = self.min_m, self.max_m
        return (x >= x0) & (x < x1) & (y >= y0) & (y < y1) & (z >= z0) & (z < z1)

    @property
    def volume_m3(self) -> float:
        return float(np.prod(np.subtract(self.max_m, self.min_m)))


@dataclass(frozen=True)
class Cylinder:
    """Upright cylinder (axis along z)."""

    center_xy_m: tuple[float, float]
    radius_m: float
    z_m: tuple[float, float]
    material: str
    name: str | None = None
    kind: Literal["cylinder"] = "cylinder"

    def mask(self, grid: MaterialGrid) -> np.ndarray:
        x, y, z = grid.mesh()
        cx, cy = self.center_xy_m
        r2 = (x - cx) ** 2 + (y - cy) ** 2
        return (r2 < self.radius_m**2) & (z >= self.z_m[0]) & (z < self.z_m[1])

    @property
    def volume_m3(self) -> float:
        return float(np.pi * self.radius_m**2 * (self.z_m[1] - self.z_m[0]))


Primitive = Box | Cylinder


@dataclass(frozen=True)
class Scene:
    extent_m: tuple[float, float, float]
    primitives: tuple[Primitive, ...] = field(default_factory=tuple)
    ambient_c: float = 20.0

    def build(self, rig: RigProfile, materials: MaterialTable) -> MaterialGrid:
        for p in self.primitives:
            if p.material not in materials:
                raise ValueError(f"unknown material {p.material!r} in primitive {p.name or p.kind}")
        grid = MaterialGrid.empty(self.extent_m, rig, materials, ambient_c=self.ambient_c)
        for p in self.primitives:
            grid.paint(p.mask(grid), p.material, region=p.name)
        return grid

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Scene:
        prims: list[Primitive] = []
        for p in raw.get("primitives", []):
            kind = p.get("kind", "box")
            if kind == "box":
                prims.append(Box(tuple(p["min_m"]), tuple(p["max_m"]), p["material"], p.get("name")))
            elif kind == "cylinder":
                prims.append(
                    Cylinder(tuple(p["center_xy_m"]), float(p["radius_m"]), tuple(p["z_m"]), p["material"], p.get("name"))
                )
            else:
                raise ValueError(f"unknown primitive kind {kind!r}")
        return cls(tuple(raw["extent_m"]), tuple(prims), float(raw.get("ambient_c", 20.0)))
