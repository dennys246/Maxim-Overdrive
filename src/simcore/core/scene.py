"""Scenes are authored in metres and voxelized at a grid spacing.

Nothing is authored in cells. A scene is a list of primitives with a material and an optional name; the grid spacing
decides how finely it is sampled. Imagination produces the same specs (``simcore.core.imagination``), so an imagined
object is made of the same cells, burns and breaks like anything else, and needs no special case.

A cell belongs to a primitive when its centre lies inside it; later primitives overwrite earlier ones.

The scene file is format ``SCENE`` (v1: world_model F13's strict reader plus the bodies' ``spawns``, tile §1.3). Its
fields are declared once, below, and read by ``simcore.core.schema``; the primitives' constructors run the same rules.
"""

from __future__ import annotations

import math
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Literal

from simcore.core import topology
from simcore.core.checks import MAXIM_TARGET_ALIASES, entity_key, shown
from simcore.core.fields import CONSTRUCTION
from simcore.core.grid import (
    MAX_LENGTH_M,
    REGION_NAME,
    Bounds,
    Footprint,
    Mask,
    MaterialGrid,
    Point,
    whole_micrometres,
)
from simcore.core.materials import MaterialTable
from simcore.core.refusals import RefusalCode, Refused
from simcore.core.schema import Field, Format, Identity, ListOf, Nested, Real, Schema, Tagged, Text, Vector, Whole
from simcore.core.writers import claim

_CONSTRUCTION = claim(CONSTRUCTION)


@contextmanager
def constructing(grid: MaterialGrid) -> Iterator[None]:
    """Construction's write window on a grid nothing has run on yet (boundaries §4.1, §6.4): it writes the authored
    temperature and integrity directly, and asks Topology (``topology.apply``) for every paint and name, like any
    requester. Scene building is its shipped caller; tests author grids through it. Only construction opens one."""
    with grid.writing(writer=_CONSTRUCTION):
        yield


# Validity bounds, not tunables: no ambient is hotter than a flame (wood's is about 2000 C), and a scene's air at
# 1e300 C would overflow the first step. A tile is tens of metres. The extent bound only refuses absurd numbers: a
# real cell-count budget comes with the memory budget planned for design v2. Coordinates are bounded before any
# arithmetic: squaring a 1e200 m radius overflowed a float inside the voxelizer (step 3b review, B1).
MAX_AMBIENT_C = 3000.0
MAX_EXTENT_M = MAX_LENGTH_M  # grid.MAX_LENGTH_M: one bound for every length a scene or a grid takes
MAX_PRIMITIVES = 4096  # a list's length is counted before any primitive is built (boundaries §5.4)
MAX_SPAWNS = 64
_COORD3, _COORD2 = Vector(3, MAX_EXTENT_M), Vector(2, MAX_EXTENT_M)
# A primitive's name is a region name, which Maxim strips when it resolves one, so " crate" would answer to "crate".
_LABELS = (Field("material", Text()), Field("name", REGION_NAME, required=False, nullable=True))
BOX = Schema((Field("min_m", _COORD3), Field("max_m", _COORD3), *_LABELS))
CYLINDER = Schema(
    (
        Field("center_xy_m", _COORD2),
        Field("radius_m", Real(lo=0.0, lo_open=True, hi=MAX_EXTENT_M)),
        Field("z_m", _COORD2),
        *_LABELS,
    )
)
PRIMITIVE = Tagged("kind", "box", {"box": BOX, "cylinder": CYLINDER})


def _check_volume(p: Box | Cylinder) -> None:
    """A shape with no volume has no footprint centroid: a 1e-300 m radius underflows to 0 m³ (step 3b(b) review,
    Wire S4)."""
    if not p.volume_m3 > 0:
        raise Refused(f"a {p.kind}'s volume must be above 0 m³, got {p.volume_m3!r}", code=RefusalCode.TOO_SMALL)


@dataclass(frozen=True)
class Box:
    min_m: tuple[float, float, float]
    max_m: tuple[float, float, float]
    material: str
    name: str | None = None
    kind: Literal["box"] = "box"

    def __post_init__(self) -> None:
        v = BOX.check({"min_m": self.min_m, "max_m": self.max_m, "material": self.material, "name": self.name}, "box")
        lo, hi = v["min_m"], v["max_m"]
        if not all(a < b for a, b in zip(lo, hi, strict=True)):  # type: ignore[call-overload]  # two Vectors
            raise Refused(
                f"box max_m must exceed min_m on every axis, got {lo} and {hi}", code=RefusalCode.OUT_OF_RANGE
            )
        object.__setattr__(self, "min_m", lo)
        object.__setattr__(self, "max_m", hi)
        _check_volume(self)

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
        given = {"center_xy_m": self.center_xy_m, "radius_m": self.radius_m, "z_m": self.z_m}
        v = CYLINDER.check({**given, "material": self.material, "name": self.name}, "cylinder")
        z: tuple[float, float] = v["z_m"]  # type: ignore[assignment]  # a Vector of 2
        if z[1] <= z[0]:
            raise Refused(f"cylinder needs z_m[1] > z_m[0], got {z}", code=RefusalCode.OUT_OF_RANGE)
        for name in given:
            object.__setattr__(self, name, v[name])
        _check_volume(self)

    def mask(self, grid: MaterialGrid) -> Mask:
        x, y, z = grid.mesh()
        cx, cy = self.center_xy_m
        r2 = (x - cx) ** 2 + (y - cy) ** 2
        # radius_m**2 goes through libm pow, the platform-dependent form; r*r is one correctly rounded multiply, the
        # same everywhere. It stays **2 only to match fa27d5f's behaviour: at r = 0.28284271247461895 m on the 0.2 m
        # grid this macOS pow gives 20 cells and r*r 24 (the 1 km bound already rules out the overflow). The real fix
        # is voxelizing by volume overlap, with no knife edge (docs/standards_backlog.md, B28).
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
                raise Refused(
                    f"primitive {later.name or later.kind} overlaps the named solid {earlier.name}: named objects "
                    "can't share space with a later solid (air may carve into them)",
                    code=RefusalCode.SPACE_TAKEN,
                )


def footprint_of(primitives: Sequence[Primitive]) -> Footprint:
    """The authored footprint of one or more primitives: their joint bounding box and volume-weighted centroid.

    Overlaps between primitives are counted twice in the centroid's weights; authored objects rarely overlap."""
    lo = tuple(min(p.bounds_m[0][i] for p in primitives) for i in range(3))
    hi = tuple(max(p.bounds_m[1][i] for p in primitives) for i in range(3))
    total = sum(p.volume_m3 for p in primitives)
    c = tuple(sum(p.volume_m3 * p.centroid_m[i] for p in primitives) / total for i in range(3))
    return Footprint(((lo[0], lo[1], lo[2]), (hi[0], hi[1], hi[2])), (c[0], c[1], c[2]))


def _primitive(doc: Mapping[str, object]) -> Primitive:
    v: Mapping[str, Any] = doc
    if v["kind"] == "box":
        return Box(v["min_m"], v["max_m"], v["material"], v["name"])
    return Cylinder(v["center_xy_m"], v["radius_m"], v["z_m"], v["material"], v["name"])


PRIMITIVES = ListOf(PRIMITIVE, MAX_PRIMITIVES)


def primitives_from_data(listed: object) -> tuple[Primitive, ...]:
    """Primitives from a parsed list of mappings, each held to its kind's schema, or a Refused that says what was
    wrong. Shared by scene files and imagined specs: a spec is not a scene file, so it has no scene version."""
    return tuple(_primitive(doc) for doc in PRIMITIVES.convert(listed, "primitives"))


MM_PER_M = 1000
MAX_EXTENT_MM = round(MAX_EXTENT_M * MM_PER_M)


def to_mm(value_m: float) -> int:
    """A length in metres as whole millimetres, so positions are compared in integers (F13). Rounded to the nearest,
    and an exact tie to the even millimetre: Python's ``round`` on the float product (0.0025 m is 2 mm, 0.0035 m is
    4). Any other reader of a scene (a client tool) must round the same way, or refuse a position off the millimetre."""
    return round(value_m * MM_PER_M)


ALIGNMENT_M = 0.2  # the coarsest verification grid's cell (CLAUDE.md, the resolution rule): every extent's quantum
ALIGNMENT_UM = round(ALIGNMENT_M * 1_000_000)


# A spawn names a body by an identity key: save v0 maps each body to its persistent body_key (tile §2.1), so a ":"
# would make Maxim's per-agent stream seeds ambiguous (checks.identity_key).
SPAWN = Schema(
    (
        Field("name", Identity()),
        Field("archetype", Identity()),
        Field("at_m", _COORD3),
        Field("holding", Identity(), required=False, nullable=True),
    )
)
_ON_GRID_MM = Whole(-MAX_EXTENT_MM, MAX_EXTENT_MM)


@dataclass(frozen=True)
class Spawn:
    """Where a body enters the world: its identity key, its archetype, what it holds, at whole millimetres (tile §1.3).

    The scene's format checks syntax and extent only; clearance is checked when the body is made and at ``join``
    (step 5b), and ``join`` refuses an archetype with no spawn (AR-S9)."""

    name: str
    archetype: str
    at_mm: tuple[int, int, int]
    holding: str | None = None

    def __post_init__(self) -> None:
        f = SPAWN.by_name
        object.__setattr__(self, "name", f["name"].read(self.name, "spawn"))
        object.__setattr__(self, "archetype", f["archetype"].read(self.archetype, "spawn"))
        object.__setattr__(self, "holding", f["holding"].read(self.holding, "spawn"))
        at = self.at_mm
        if isinstance(at, (str, bytes)) or not isinstance(at, Sequence) or len(at) != 3:
            raise Refused(f"spawn.at_mm must be three whole numbers, got {shown(at)}", code=RefusalCode.BAD_SHAPE)
        object.__setattr__(self, "at_mm", tuple(_ON_GRID_MM.convert(c, "spawn.at_mm") for c in at))

    @classmethod
    def from_document(cls, doc: Mapping[str, Any]) -> Spawn:
        x, y, z = doc["at_m"]
        return cls(doc["name"], doc["archetype"], (to_mm(x), to_mm(y), to_mm(z)), doc["holding"])


_V0_REFUSED = (
    "scene files are repo-only, so an old version is refused, never migrated (step 3b): add its spawns and set "
    "version 1"
)
_LATER = "zones, vents and gaps arrive with a later scene version in Phase 2 (world_model F13)"
SCENE = Format(
    "scene",
    1,
    Schema(
        (
            Field("extent_m", Vector(3, MAX_EXTENT_M, positive=True)),
            Field("ambient_c", Real(lo=-273.15, lo_open=True, hi=MAX_AMBIENT_C), required=False, default=20.0),
            Field("primitives", PRIMITIVES, required=False, default=()),
            Field("spawns", ListOf(Nested(SPAWN), MAX_SPAWNS)),
        ),
        reserved={"zones": _LATER, "vents": _LATER, "gaps": _LATER},
    ),
    refused={0: _V0_REFUSED},
)


@dataclass(frozen=True)
class Scene:
    extent_m: tuple[float, float, float]
    primitives: tuple[Primitive, ...] = field(default_factory=tuple)
    ambient_c: float = 20.0
    spawns: tuple[Spawn, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        own = SCENE.schema.by_name
        object.__setattr__(self, "extent_m", own["extent_m"].read(self.extent_m, "scene"))
        object.__setattr__(self, "ambient_c", own["ambient_c"].read(self.ambient_c, "scene"))
        object.__setattr__(self, "primitives", tuple(self.primitives))
        object.__setattr__(self, "spawns", tuple(self.spawns))
        self._check_alignment()
        self._check_spawns()

    def _check_alignment(self) -> None:
        """Every extent is a whole number of ``ALIGNMENT_M`` cells, so a scene that builds at one verification grid
        builds at all of them (the resolution rule; world_model WT-5, WT-11). Judged in whole micrometres (F13)."""
        for e in self.extent_m:
            if whole_micrometres(e, "a scene's extent_m") % ALIGNMENT_UM:
                raise Refused(
                    f"a scene's extent_m must be whole multiples of {ALIGNMENT_M:g} m (the coarsest verification "
                    f"grid's cell), got {shown(self.extent_m)}",
                    code=RefusalCode.OUT_OF_RANGE,
                    field="extent_m",
                )

    def _check_spawns(self) -> None:
        """Each spawn is a ``Spawn`` inside the extent, compared in whole millimetres (F13), with a name that Maxim
        can't confuse: unique under its name rule (``checks.entity_key``), not a region's name, and not one of the
        target aliases Maxim resolves to the calling agent's own body (step 3b(b) review, Bio-faithful S3)."""
        if len(self.spawns) > MAX_SPAWNS:
            raise Refused(f"a scene holds at most {MAX_SPAWNS} spawns", code=RefusalCode.OVER_BUDGET)
        extent_mm = [to_mm(e) for e in self.extent_m]
        seen = {entity_key(p.name) for p in self.primitives if p.name}
        for spawn in self.spawns:
            if not isinstance(spawn, Spawn):
                raise Refused(f"a scene's spawns must be Spawns, got {shown(spawn)}", code=RefusalCode.BAD_SHAPE)
            key = entity_key(spawn.name)
            if key in MAXIM_TARGET_ALIASES:
                message = f"spawn {shown(spawn.name)} is a name Maxim resolves to the calling agent itself"
                raise Refused(message, code=RefusalCode.BAD_IDENTITY_KEY, field="name")
            if key in seen:
                message = f"spawn {shown(spawn.name)} shares its name with another spawn or a region"
                raise Refused(message, code=RefusalCode.NAME_TAKEN, field="name")
            seen.add(key)
            if not all(0 <= c <= e for c, e in zip(spawn.at_mm, extent_mm, strict=True)):
                raise Refused(
                    f"spawn {spawn.name} at {spawn.at_mm} mm lies outside the scene's {extent_mm} mm",
                    code=RefusalCode.OUTSIDE_EXTENT,
                )

    def build(self, materials: MaterialTable, *, dx_m: float) -> MaterialGrid:
        for p in self.primitives:
            if p.material not in materials:
                raise Refused(
                    f"unknown material {shown(p.material)} in primitive {shown(p.name or p.kind)}",
                    code=RefusalCode.UNKNOWN_MATERIAL,
                )
        _check_no_solid_overlaps(self.primitives)
        grid = MaterialGrid.empty(self.extent_m, materials, dx_m=dx_m, ambient_c=self.ambient_c)
        requests = (  # a generator: each primitive's mask is made as Topology paints it, never all at once
            topology.Paint(p.mask(grid), p.material, region=p.name, footprint=footprint_of([p]) if p.name else None)
            for p in self.primitives
        )
        with constructing(grid):
            topology.apply(grid, requests)
        return grid

    @classmethod
    def from_dict(cls, raw: object) -> Scene:
        """A scene from parsed YAML or JSON, at ``SCENE``'s version. Any malformed shape is a Refused (a ValueError)
        that says what was wrong."""
        doc: Mapping[str, Any] = SCENE.read(raw, "scene")
        prims = tuple(_primitive(p) for p in doc["primitives"])
        spawns = tuple(Spawn.from_document(s) for s in doc["spawns"])
        return cls(doc["extent_m"], prims, doc["ambient_c"], spawns)
