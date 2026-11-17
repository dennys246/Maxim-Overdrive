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
from types import MappingProxyType
from typing import Literal

from maxim_overdrive.checks import finite_real, finite_vector, known_keys
from maxim_overdrive.config import MaterialTable, RigProfile
from maxim_overdrive.world.grid import Bounds, Footprint, Mask, MaterialGrid, Point


def _check_labels(material: object, name: object) -> None:
    if not isinstance(material, str) or not material:
        raise ValueError(f"primitive {name!r} needs a material name, got {material!r}")
    if name is not None and (not isinstance(name, str) or not name.strip() or name != name.strip()):
        # Maxim strips the names it resolves, so " crate" would answer to "crate" and "  " to nothing.
        raise ValueError(f"a primitive's name must be a non-empty string with no outer spaces, got {name!r}")


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

    @property
    def centroid_m(self) -> Point:
        (x0, y0, z0), (x1, y1, z1) = self.min_m, self.max_m
        return ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)


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

    @property
    def centroid_m(self) -> Point:
        (cx, cy), (z0, z1) = self.center_xy_m, self.z_m
        return (cx, cy, (z0 + z1) / 2)


Primitive = Box | Cylinder


def boxes_overlap(a: Bounds, b: Bounds) -> bool:
    return all(a[0][i] < b[1][i] and b[0][i] < a[1][i] for i in range(3))


def _check_no_solid_overlaps(primitives: Sequence[Primitive]) -> None:
    """A later solid primitive may not take space from an earlier named solid one.

    A named region's footprint (its authored shape in metres) says where it is and what a strike on it reaches. If a
    later solid primitive painted over part of it, the footprint would cover cells the region no longer owns, so a
    fire on the crate would heat the wall and a strike on the crate would break it. Air may still carve into a named
    solid (a doorway in a wall). Overlap is judged on bounding boxes, so a cylinder's corners count; the region id
    array planned for design v2 makes ownership per cell instead.
    """
    for i, later in enumerate(primitives):
        if later.material == "air":
            continue
        for earlier in primitives[:i]:
            if earlier.name and earlier.material != "air" and boxes_overlap(earlier.bounds_m, later.bounds_m):
                raise ValueError(
                    f"primitive {later.name or later.kind} overlaps the named solid {earlier.name}: named objects "
                    "can't share space with a later solid (air may carve into them)"
                )


def footprint_of(primitives: Sequence[Primitive]) -> Footprint:
    """The authored footprint of one or more primitives: their joint bounding box and volume-weighted centroid.

    Overlaps between primitives are counted twice in the centroid's weights; authored objects rarely overlap."""
    lo = tuple(min(p.bounds_m[0][i] for p in primitives) for i in range(3))
    hi = tuple(max(p.bounds_m[1][i] for p in primitives) for i in range(3))
    total = sum(p.volume_m3 for p in primitives)
    c = tuple(sum(p.volume_m3 * p.centroid_m[i] for p in primitives) / total for i in range(3))
    return Footprint(((lo[0], lo[1], lo[2]), (hi[0], hi[1], hi[2])), (c[0], c[1], c[2]))


# Validity bounds, not tunables: no ambient is hotter than a flame (wood's is about 2000 C), and a scene's air at
# 1e300 C would overflow the first step. A tile is tens of metres. The extent bound only refuses absurd numbers: a
# real per-rig cell-count budget comes with the memory budget planned for design v2.
MAX_AMBIENT_C = 3000.0
MAX_EXTENT_M = 1000.0


# The keys each primitive kind requires when a scene is written as data (Scene.from_dict); "kind" and "name" are
# optional for both. Read-only, so no caller can widen a schema at run time.
PRIMITIVE_KEYS: Mapping[str, frozenset[str]] = MappingProxyType(
    {
        "box": frozenset({"min_m", "max_m", "material"}),
        "cylinder": frozenset({"center_xy_m", "radius_m", "z_m", "material"}),
    }
)


@dataclass(frozen=True)
class Scene:
    extent_m: tuple[float, float, float]
    primitives: tuple[Primitive, ...] = field(default_factory=tuple)
    ambient_c: float = 20.0

    def __post_init__(self) -> None:
        x, y, z = finite_vector(self.extent_m, 3, "a scene's extent_m")
        if not (min(x, y, z) > 0 and max(x, y, z) <= MAX_EXTENT_M):
            raise ValueError(
                f"a scene's extent_m must be between 0 and {MAX_EXTENT_M:g} m on every axis, got {self.extent_m!r}"
            )
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
        _check_no_solid_overlaps(self.primitives)
        grid = MaterialGrid.empty(self.extent_m, rig, materials, ambient_c=self.ambient_c)
        for p in self.primitives:
            grid.paint(p.mask(grid), p.material, region=p.name, footprint=footprint_of([p]) if p.name else None)
        return grid

    @classmethod
    def from_dict(cls, raw: object) -> Scene:
        """A scene from parsed YAML or JSON. Any malformed shape is a ValueError that says what was wrong."""
        if not isinstance(raw, Mapping):
            raise ValueError(f"a scene must be a mapping, got {type(raw).__name__}")
        known_keys(raw, "scene", required={"extent_m"}, optional={"primitives", "ambient_c"})
        listed = raw.get("primitives", [])
        if isinstance(listed, (str, bytes, Mapping)) or not isinstance(listed, Sequence):
            raise ValueError(f"primitives must be a list, got {type(listed).__name__}")
        prims: list[Primitive] = []
        for p in listed:
            if not isinstance(p, Mapping):
                raise ValueError(f"each primitive must be a mapping, got {p!r}")
            kind = p.get("kind", "box")
            if not isinstance(kind, str) or kind not in PRIMITIVE_KEYS:  # a list or a mapping isn't hashed
                raise ValueError(f"unknown primitive kind {kind!r}")
            known_keys(p, f"{kind} primitive", required=PRIMITIVE_KEYS[kind], optional={"kind", "name"})
            if kind == "box":
                prims.append(Box(p["min_m"], p["max_m"], p["material"], p.get("name")))
            else:
                prims.append(Cylinder(p["center_xy_m"], p["radius_m"], p["z_m"], p["material"], p.get("name")))
        e = finite_vector(raw["extent_m"], 3, "extent_m")
        return cls((e[0], e[1], e[2]), tuple(prims), raw.get("ambient_c", 20.0))
