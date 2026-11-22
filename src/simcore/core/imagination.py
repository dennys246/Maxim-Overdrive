"""Imagined objects enter the world as specs, never as free-form assets.

An LLM (Maxim's ImaginationDesigner, later) proposes an object as primitives made of known materials, in metres,
relative to the object's origin. Before anything exists, the spec must pass the world's rules: every material is in
the table, the object fits its size limit and its mass budget, and the space it would occupy is free. A passed spec
is voxelized into the grid like any authored primitive, so an imagined crate burns and breaks like a real one.

Rendering assets (meshes, textures, sounds) are derived from the same spec and the material table, not generated
separately; see docs/architecture.md.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any, SupportsFloat

import numpy as np

from simcore.core.checks import entity_key, finite_vector, known_keys, shown
from simcore.core.grid import REGION_NAME, Footprint, MaterialGrid
from simcore.core.refusals import RefusalCode, Refused
from simcore.core.scene import Box, Cylinder, Primitive, boxes_overlap, footprint_of, primitives_from_data
from simcore.core.schema import Field, Real, Schema, Whole

# Budget(max_mass_kg=nan) once built, and removed the mass limit; so each limit is held to its rule (boundaries §5.1).
_BUDGET = Schema(
    (
        Field("max_mass_kg", Real(lo=0.0, lo_open=True)),
        Field("max_extent_m", Real(lo=0.0, lo_open=True)),
        Field("max_primitives", Whole(1, 4096)),  # at most a scene's (scene.MAX_PRIMITIVES)
        Field("max_name_chars", Whole(1, 1024)),
    )
)


@dataclass(frozen=True)
class Budget:
    """What one imagined object may cost. Every limit is checked before a cell is allocated (boundaries §5.4)."""

    max_mass_kg: float = 500.0
    max_extent_m: float = 3.0
    max_primitives: int = 32  # each primitive costs a full-grid mask to voxelize, one at a time
    max_name_chars: int = 64

    def __post_init__(self) -> None:
        # Validating constructor (boundaries §5.1): Budget(max_mass_kg=nan) once built, and removed the mass limit.
        for name, value in _BUDGET.check(asdict(self), "budget").items():
            object.__setattr__(self, name, value)


class SpecRejected(Refused):
    """The world refused an imagined object. Its code is what an agent is told; the message says why, in words, for
    logs, tests and the player's own view."""


def _offset(p: Primitive, o: tuple[float, float, float]) -> Primitive:
    if isinstance(p, Box):
        (x0, y0, z0), (x1, y1, z1) = p.min_m, p.max_m
        return Box((x0 + o[0], y0 + o[1], z0 + o[2]), (x1 + o[0], y1 + o[1], z1 + o[2]), p.material)
    return Cylinder(
        (p.center_xy_m[0] + o[0], p.center_xy_m[1] + o[1]), p.radius_m, (p.z_m[0] + o[2], p.z_m[1] + o[2]), p.material
    )


# The keys an imagined object may carry; each is checked by _read itself, with its own refusal ("needs a name", "at
# least one primitive"). A new one (a description, provenance, a licence) is added here and to the content its id
# hashes, as one list (docs/design/ip_and_licensing.md, section 6).
SPEC_KEYS = frozenset({"name", "primitives"})


def _within_budget(spec: Mapping[object, object], budget: Budget) -> None:
    """The counts and lengths a spec may carry, checked before any primitive is built or any cell is allocated."""
    name, listed = spec.get("name"), spec.get("primitives", [])
    if isinstance(name, str) and len(name) > budget.max_name_chars:
        message = f"an imagined object's name is at most {budget.max_name_chars} characters"
        raise SpecRejected(message, code=RefusalCode.OVER_BUDGET, field="name")
    if isinstance(listed, Sequence) and len(listed) > budget.max_primitives:
        message = f"too many primitives: {len(listed)}, the limit is {budget.max_primitives}"
        raise SpecRejected(message, code=RefusalCode.OVER_BUDGET, field="primitives")


def _read(grid: MaterialGrid, spec: object, origin_m: object, budget: Budget) -> tuple[str, list[Primitive]]:
    """The spec's name and its primitives placed at ``origin_m``, or SpecRejected. Nothing here touches the grid."""
    if not isinstance(spec, Mapping):
        message = f"an imagined object must be a mapping, got {type(spec).__name__}"
        raise SpecRejected(message, code=RefusalCode.BAD_SHAPE)
    try:
        known_keys(spec, "an imagined object", required=(), optional=SPEC_KEYS)
    except Refused as exc:  # reported as the refusal, with its code
        raise SpecRejected(str(exc), code=exc.code, field=exc.field) from exc
    _within_budget(spec, budget)
    try:  # a region's one name rule (grid.REGION_NAME): an LLM's name is the most hostile one there is
        name = REGION_NAME.convert(spec.get("name"), "an imagined object's name")
    except Refused as exc:
        raise SpecRejected(str(exc), code=exc.code) from exc
    clash = next((r for r in grid.regions if entity_key(r) == entity_key(name)), None)
    if clash is not None:  # by Maxim's name rule, checked before anything is painted
        raise SpecRejected(f"something called {shown(clash)} already exists", code=RefusalCode.NAME_TAKEN)
    try:
        origin = finite_vector(origin_m, 3, "origin_m")
        prims = primitives_from_data(spec.get("primitives", []))
        placed = [_offset(p, (origin[0], origin[1], origin[2])) for p in prims]  # offsetting re-validates
    except Refused as exc:  # every malformed shape is coded where it is found (schema, checks, constructors)
        raise SpecRejected(f"malformed spec: {exc}", code=exc.code, field=exc.field) from exc
    if not prims:
        raise SpecRejected("an imagined object needs at least one primitive", code=RefusalCode.MISSING_FIELD)
    for p in prims:
        if p.material not in grid.materials:
            message = f"{shown(p.material)} is not a material this world knows"
            raise SpecRejected(message, code=RefusalCode.UNKNOWN_MATERIAL)
        if p.material == "air":
            raise SpecRejected("objects cannot be made of air", code=RefusalCode.NOT_SOLID)
    return name, placed


def _within_world_rules(grid: MaterialGrid, placed: list[Primitive], budget: Budget) -> tuple[Footprint, float]:
    """The footprint and mass of the placed primitives, or SpecRejected, judged from authored geometry alone: no cell
    is allocated, and the answer is the same at every grid spacing (boundaries §5.4: budgets before allocation)."""
    footprint = footprint_of(placed)
    (x0, y0, z0), (x1, y1, z1) = footprint.bounds_m
    across_m = max(x1 - x0, y1 - y0, z1 - z0)
    if across_m > budget.max_extent_m + 1e-9:
        message = f"too large: {across_m:.2f} m across, the limit is {budget.max_extent_m:g} m"
        raise SpecRejected(message, code=RefusalCode.OVER_BUDGET)
    # The same boundary as authored scenes (scene._check_no_solid_overlaps): an imagined object may not sit inside a
    # named solid's footprint, even in air carved into it, or a strike on that solid could break the new object.
    for other, region in grid.regions.items():
        if region.solid and any(boxes_overlap(region.footprint.bounds_m, p.bounds_m) for p in placed):
            raise SpecRejected(f"that space belongs to {shown(other)}", code=RefusalCode.SPACE_TAKEN)
    mass = sum(p.volume_m3 * grid.materials[p.material].density_kg_m3 for p in placed)
    if mass > budget.max_mass_kg:
        message = f"too heavy: {mass:.0f} kg, the limit is {budget.max_mass_kg:g} kg"
        raise SpecRejected(message, code=RefusalCode.OVER_BUDGET)
    return footprint, mass


def _voxelize(grid: MaterialGrid, name: str, placed: list[Primitive], footprint: Footprint) -> None:
    """Paint the primitives and name them, one mask per primitive, each computed once. A refusal raised here (the
    space is occupied, or the object covers no cell) rolls the window back whole."""
    solid = grid.solid  # before anything is painted: overlap among the object's own primitives is allowed
    union = np.zeros(grid.shape, dtype=np.bool_)
    # TEMPORARY(phase1/sim-clock): place opens the write window itself because the imagine intent kind doesn't exist
    # yet (boundaries §5.3, §6.4); step 5a's intent log is where every input joins one pipeline, and there place
    # becomes the applier's stage 2 of an imagine intent, inside Simulation.step's window.
    with grid.writing():
        for p in placed:
            mask = p.mask(grid)
            if (mask & solid).any():
                raise SpecRejected("that space is occupied", code=RefusalCode.SPACE_TAKEN)
            union |= mask
            grid.paint(mask, p.material)
        if not union.any():
            message = "the object is smaller than one cell at this resolution, or outside the world"
            raise SpecRejected(message, code=RefusalCode.TOO_SMALL)
        grid.name_region(name, union, footprint, solid=True)  # imagined objects are never air (see _read)


def place(
    grid: MaterialGrid, spec: Mapping[str, Any], origin_m: Sequence[SupportsFloat], budget: Budget = Budget()
) -> float:
    """Validate an imagined object and voxelize it as a new region. Returns its mass in kg.

    Raises ``SpecRejected`` with a reason if any rule fails; the grid is unchanged in that case. ``spec`` and
    ``origin_m`` usually come from an LLM, so every malformed shape is a rejection, never another exception. Every
    budget is checked before a cell is allocated: counts and names first (``_within_budget``), then extent, ownership
    and mass from the authored geometry; only occupancy needs the cells.
    """
    name, placed = _read(grid, spec, origin_m, budget)
    footprint, mass = _within_world_rules(grid, placed, budget)
    _voxelize(grid, name, placed, footprint)
    return float(mass)
