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
from dataclasses import dataclass
from typing import Any, SupportsFloat

import numpy as np

from maxim_overdrive.checks import finite_vector, known_keys
from maxim_overdrive.world.grid import MaterialGrid, entity_key
from maxim_overdrive.world.scene import Box, Cylinder, Primitive, boxes_overlap, footprint_of, primitives_from_data


@dataclass(frozen=True)
class Budget:
    max_mass_kg: float = 500.0
    max_extent_m: float = 3.0


class SpecRejected(ValueError):
    """The world refused an imagined object. The message says why, for the agent and the player."""


def _offset(p: Primitive, o: tuple[float, float, float]) -> Primitive:
    if isinstance(p, Box):
        (x0, y0, z0), (x1, y1, z1) = p.min_m, p.max_m
        return Box((x0 + o[0], y0 + o[1], z0 + o[2]), (x1 + o[0], y1 + o[1], z1 + o[2]), p.material)
    return Cylinder(
        (p.center_xy_m[0] + o[0], p.center_xy_m[1] + o[1]), p.radius_m, (p.z_m[0] + o[2], p.z_m[1] + o[2]), p.material
    )


# The keys an imagined object may carry; each is checked by _read itself, with its own refusal ("needs a name", "at
# least one primitive"). A new one (a description, provenance, a licence) is added here and to the content its id
# hashes, as one list (the IP note on phase1/realtime-design, docs/design/ip_and_licensing.md section 6).
SPEC_KEYS = frozenset({"name", "primitives"})


def _read(grid: MaterialGrid, spec: object, origin_m: object) -> tuple[str, list[Primitive]]:
    """The spec's name and its primitives placed at ``origin_m``, or SpecRejected. Nothing here touches the grid."""
    if not isinstance(spec, Mapping):
        raise SpecRejected(f"an imagined object must be a mapping, got {type(spec).__name__}")
    try:
        known_keys(spec, "an imagined object", required=(), optional=SPEC_KEYS)
    except ValueError as exc:  # reported as the refusal
        raise SpecRejected(str(exc)) from exc
    name = spec.get("name")
    if not name or not isinstance(name, str) or not name.strip() or name != name.strip():
        raise SpecRejected("an imagined object needs a name, with no outer spaces")
    clash = next((r for r in grid.regions if entity_key(r) == entity_key(name)), None)
    if clash is not None:  # by Maxim's name rule, checked before anything is painted
        raise SpecRejected(f"something called {clash!r} already exists")
    try:
        origin = finite_vector(origin_m, 3, "origin_m")
        prims = primitives_from_data(spec.get("primitives", []))
        placed = [_offset(p, (origin[0], origin[1], origin[2])) for p in prims]  # offsetting re-validates
    except (KeyError, TypeError, ValueError) as exc:
        raise SpecRejected(f"malformed spec: {exc}") from exc
    if not prims:
        raise SpecRejected("an imagined object needs at least one primitive")
    for p in prims:
        if p.material not in grid.materials:
            raise SpecRejected(f"{p.material!r} is not a material this world knows")
        if p.material == "air":
            raise SpecRejected("objects cannot be made of air")
    return name, placed


def place(
    grid: MaterialGrid, spec: Mapping[str, Any], origin_m: Sequence[SupportsFloat], budget: Budget = Budget()
) -> float:
    """Validate an imagined object and voxelize it as a new region. Returns its mass in kg.

    Raises ``SpecRejected`` with a reason if any rule fails; the grid is unchanged in that case. ``spec`` and
    ``origin_m`` usually come from an LLM, so every malformed shape is a rejection, never another exception.
    """
    name, placed = _read(grid, spec, origin_m)

    masks = [p.mask(grid) for p in placed]
    union = np.any(np.stack(masks), axis=0)
    if not union.any():
        raise SpecRejected("the object is smaller than one cell at this resolution, or outside the world")
    # Size from the authored geometry, like mass, so whether an object is too large doesn't depend on the rig.
    footprint = footprint_of(placed)
    (x0, y0, z0), (x1, y1, z1) = footprint.bounds_m
    across_m = max(x1 - x0, y1 - y0, z1 - z0)
    if across_m > budget.max_extent_m + 1e-9:
        raise SpecRejected(f"too large: {across_m:.2f} m across, the limit is {budget.max_extent_m} m")
    if (union & grid.solid).any():
        raise SpecRejected("that space is occupied")
    # The same boundary as authored scenes (scene._check_no_solid_overlaps): an imagined object may not sit inside a
    # named solid's footprint, even in air carved into it, or a strike on that solid could break the new object.
    for other, region in grid.regions.items():
        if region.solid and any(boxes_overlap(region.footprint.bounds_m, p.bounds_m) for p in placed):
            raise SpecRejected(f"that space belongs to {other}")
    # Mass from the authored geometry, so the budget does not depend on the rig.
    mass = sum(p.volume_m3 * grid.materials[p.material].density_kg_m3 for p in placed)
    if mass > budget.max_mass_kg:
        raise SpecRejected(f"too heavy: {mass:.0f} kg, the limit is {budget.max_mass_kg:.0f} kg")

    for p, m in zip(placed, masks, strict=True):
        grid.paint(m, p.material)
    grid.name_region(name, union, footprint, solid=True)  # imagined objects are never air (see _read)
    return float(mass)
