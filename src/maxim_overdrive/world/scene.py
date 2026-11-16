"""Scenes are authored in metres and voxelized per rig.

Nothing is authored in cells. A scene is a list of primitives with a material and an optional name; the rig's cell
size decides how finely it is sampled. Imagination produces the same specs (``imagination.spec``), so an imagined
object is made of the same cells, burns and breaks like anything else, and needs no special case.

A cell belongs to a primitive when its centre lies inside it; later primitives overwrite earlier ones.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

from maxim_overdrive.checks import finite_real, finite_vector
from maxim_overdrive.config import MaterialTable, RigProfile
from maxim_overdrive.world.grid import Bounds, Mask, MaterialGrid


def _check_labels(material: object, name: object) -> None:
    if not isinstance(material, str) or not material:
        raise ValueError(f"primitive {name!r} needs a material name, got {material!r}")
    if name is not None and (not isinstance(name, str) or not name):
        raise ValueError(f"a primitive's name must be a non-empty string, got {name!r}")


@dataclass(frozen=True)
class Box:
    min_m: tuple[float, float, float]
    max_m: tuple[float, float, float]
    material: str
    name: str | None = None
    kind: Literal["box"] = "box"

    def __post_init__(self) -> None:
        lo, hi = finite_vector(self.min_m, 3, "min_m"), finite_vector(self.max_m, 3, "max_m")
        if not all(a < b for a, b in zip(lo, hi, strict=True)):
            raise ValueError(f"box max_m must exceed min_m on every axis, got {lo} and {hi}")
        _check_labels(self.material, self.name)
        object.__setattr__(self, "min_m", lo)
        object.__setattr__(self, "max_m", hi)

    def mask(self, grid: MaterialGrid) -> Mask:
        x, y, z = grid.mesh()
        (x0, y0, z0), (x1, y1, z1) = self.min_m, self.max_m
        return (x >= x0) & (x < x1) & (y >= y0) & (y < y1) & (z >= z0) & (z < z1)

    @property
    def volume_m3(self) -> float:
        return math.prod(b - a for a, b in zip(self.min_m, self.max_m, strict=True))  # floats: inf, not a warning

    @property
    def bounds_m(self) -> Bounds:
        (x0, y0, z0), (x1, y1, z1) = self.min_m, self.max_m
        return (x0, y0, z0), (x1, y1, z1)


@dataclass(frozen=True)
class Cylinder:
    """Upright cylinder (axis along z)."""

    center_xy_m: tuple[float, float]
    radius_m: float
    z_m: tuple[float, float]
    material: str
    name: str | None = None
    kind: Literal["cylinder"] = "cylinder"

    def __post_init__(self) -> None:
        center = finite_vector(self.center_xy_m, 2, "center_xy_m")
        (radius,) = finite_vector((self.radius_m,), 1, "radius_m")
        z = finite_vector(self.z_m, 2, "z_m")
        if radius <= 0 or z[1] <= z[0]:
            raise ValueError(f"cylinder needs a positive radius and z_m[1] > z_m[0], got {radius} and {z}")
        _check_labels(self.material, self.name)
        object.__setattr__(self, "center_xy_m", center)
        object.__setattr__(self, "radius_m", radius)
        object.__setattr__(self, "z_m", z)

    def mask(self, grid: MaterialGrid) -> Mask:
        x, y, z = grid.mesh()
        cx, cy = self.center_xy_m
        r2 = (x - cx) ** 2 + (y - cy) ** 2
        return (r2 < self.radius_m**2) & (z >= self.z_m[0]) & (z < self.z_m[1])

    @property
    def volume_m3(self) -> float:
        return math.pi * self.radius_m * self.radius_m * (self.z_m[1] - self.z_m[0])  # r*r: ** raises on overflow

    @property
    def bounds_m(self) -> Bounds:
        (cx, cy), r, (z0, z1) = self.center_xy_m, self.radius_m, self.z_m
        return (cx - r, cy - r, z0), (cx + r, cy + r, z1)


Primitive = Box | Cylinder


# No ambient is hotter than a flame (wood's is about 2000 C); a scene's air at 1e300 C would overflow the first step.
MAX_AMBIENT_C = 3000.0


@dataclass(frozen=True)
class Scene:
    extent_m: tuple[float, float, float]
    primitives: tuple[Primitive, ...] = field(default_factory=tuple)
    ambient_c: float = 20.0

    def __post_init__(self) -> None:
        x, y, z = finite_vector(self.extent_m, 3, "a scene's extent_m")
        if min(x, y, z) <= 0:
            raise ValueError(f"a scene's extent_m must be positive on every axis, got {self.extent_m!r}")
        ambient = finite_real(self.ambient_c, "a scene's ambient_c")
        if not -273.15 < ambient <= MAX_AMBIENT_C:
            limit = f"above absolute zero and at most {MAX_AMBIENT_C:g} C"
            raise ValueError(f"a scene's ambient_c must be {limit}, got {self.ambient_c!r}")
        object.__setattr__(self, "extent_m", (x, y, z))
        object.__setattr__(self, "ambient_c", ambient)

    def build(self, rig: RigProfile, materials: MaterialTable) -> MaterialGrid:
        for p in self.primitives:
            if p.material not in materials:
                raise ValueError(f"unknown material {p.material!r} in primitive {p.name or p.kind}")
        grid = MaterialGrid.empty(self.extent_m, rig, materials, ambient_c=self.ambient_c)
        for p in self.primitives:
            grid.paint(p.mask(grid), p.material, region=p.name, bounds_m=p.bounds_m if p.name else None)
        return grid

    @classmethod
    def from_dict(cls, raw: object) -> Scene:
        """A scene from parsed YAML or JSON. Any malformed shape is a ValueError that says what was wrong."""
        if not isinstance(raw, Mapping):
            raise ValueError(f"a scene must be a mapping, got {type(raw).__name__}")
        listed = raw.get("primitives", [])
        if isinstance(listed, (str, bytes, Mapping)) or not isinstance(listed, Sequence):
            raise ValueError(f"primitives must be a list, got {type(listed).__name__}")
        prims: list[Primitive] = []
        for p in listed:
            if not isinstance(p, Mapping):
                raise ValueError(f"each primitive must be a mapping, got {p!r}")
            kind = p.get("kind", "box")
            if kind == "box":
                prims.append(Box(p["min_m"], p["max_m"], p["material"], p.get("name")))
            elif kind == "cylinder":
                prims.append(Cylinder(p["center_xy_m"], p["radius_m"], p["z_m"], p["material"], p.get("name")))
            else:
                raise ValueError(f"unknown primitive kind {kind!r}")
        return cls(tuple(raw["extent_m"]), tuple(prims), raw.get("ambient_c", 20.0))
