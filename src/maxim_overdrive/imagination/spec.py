"""Imagined objects enter the world as specs, never as free-form assets.

An LLM (Maxim's ImaginationDesigner, later) proposes an object as primitives made of known materials, in metres,
relative to the object's origin. Before anything exists, the spec must pass the world's rules: every material is in
the table, the object fits its size limit and its mass budget, and the space it would occupy is free. A passed spec
is voxelized into the grid like any authored primitive, so an imagined crate burns and breaks like a real one.

Rendering assets (meshes, textures, sounds) are derived from the same spec and the material table, not generated
separately; see docs/architecture.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from maxim_overdrive.world.grid import MaterialGrid
from maxim_overdrive.world.scene import Box, Cylinder, Primitive, Scene


@dataclass(frozen=True)
class Budget:
    max_mass_kg: float = 500.0
    max_extent_m: float = 3.0


class SpecRejected(ValueError):
    """The world refused an imagined object. The message says why, for the agent and the player."""


def _offset(p: Primitive, o: tuple[float, float, float]) -> Primitive:
    if isinstance(p, Box):
        return Box(tuple(a + b for a, b in zip(p.min_m, o)), tuple(a + b for a, b in zip(p.max_m, o)), p.material)  # type: ignore[arg-type]
    return Cylinder(
        (p.center_xy_m[0] + o[0], p.center_xy_m[1] + o[1]), p.radius_m, (p.z_m[0] + o[2], p.z_m[1] + o[2]), p.material
    )


def place(grid: MaterialGrid, spec: dict[str, Any], origin_m: tuple[float, float, float], budget: Budget = Budget()) -> float:
    """Validate an imagined object and voxelize it as a new region. Returns its mass in kg.

    Raises ``SpecRejected`` with a reason if any rule fails; the grid is unchanged in that case.
    """
    name = spec.get("name")
    if not name or not isinstance(name, str):
        raise SpecRejected("an imagined object needs a name")
    if name in grid.regions:
        raise SpecRejected(f"something called {name!r} already exists")
    try:
        prims = Scene.from_dict({"extent_m": grid.extent_m, "primitives": spec.get("primitives", [])}).primitives
    except (KeyError, TypeError, ValueError) as exc:
        raise SpecRejected(f"malformed spec: {exc}") from exc
    if not prims:
        raise SpecRejected("an imagined object needs at least one primitive")
    for p in prims:
        if p.material not in grid.materials:
            raise SpecRejected(f"{p.material!r} is not a material this world knows")
        if p.material == "air":
            raise SpecRejected("objects cannot be made of air")
    placed = [_offset(p, origin_m) for p in prims]

    masks = [p.mask(grid) for p in placed]
    union = np.logical_or.reduce(masks)
    if not union.any():
        raise SpecRejected("the object is smaller than one cell at this resolution, or outside the world")
    idx = np.argwhere(union)
    size = (idx.max(axis=0) - idx.min(axis=0) + 1) * grid.dx
    if size.max() > budget.max_extent_m + 1e-9:
        raise SpecRejected(f"too large: {size.max():.2f} m across, the limit is {budget.max_extent_m} m")
    if (union & grid.solid).any():
        raise SpecRejected("that space is occupied")
    # Mass from the authored geometry, so the budget does not depend on the rig.
    mass = sum(p.volume_m3 * grid.materials[p.material].density_kg_m3 for p in placed)
    if mass > budget.max_mass_kg:
        raise SpecRejected(f"too heavy: {mass:.0f} kg, the limit is {budget.max_mass_kg:.0f} kg")

    for p, m in zip(placed, masks):
        grid.paint(m, p.material)
    grid.regions[name] = union.copy()
    return float(mass)
