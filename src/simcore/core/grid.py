"""The world as material cells: a structure of arrays, one value per cell.

Every cell holds a material id, an integrity in [0, 1] and a temperature in °C. Physics fields (heat today; sound,
light and gas later) and damage read and write these arrays in place. SEM entities for the environment are views
over sets of cells (``simcore.adapters.sem``); renderers read quantized copies (``simcore.protocol.encoding``).

Cell ``(i, j, k)`` covers ``[i*dx, (i+1)*dx) x [j*dx, (j+1)*dx) x [k*dx, (k+1)*dx)`` in metres; z is up.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import numpy.typing as npt

from simcore.core.checks import finite_real
from simcore.core.materials import AIR_ID, MaterialTable

# Array types for the grid's fields. Typing the element type (not bare np.ndarray) is what strict mypy needs on every
# supported numpy: older stubs give ndarray no default type parameters.
Mask = npt.NDArray[np.bool_]
Field = npt.NDArray[np.float64]
# A region's authored extent in metres, (min corner, max corner). It is kept beside the region's cells because the
# cells depend on the grid spacing and the authored bounds don't, so anything that asks "is this point on the region?"
# gets the same answer at every spacing.
Bounds = tuple[tuple[float, float, float], tuple[float, float, float]]
Point = tuple[float, float, float]


def entity_key(name: str) -> str:
    """A name as Maxim's EntityMap resolves it: stripped, lower-cased, spaces as underscores."""
    return name.strip().lower().replace(" ", "_")


@dataclass(frozen=True)
class Footprint:
    """A region's authored shape in metres: its bounding box and its volume-weighted centroid."""

    bounds_m: Bounds
    centroid_m: Point


@dataclass(frozen=True)
class Region:
    """A named part of the world. ``cells`` move with the grid spacing (and lose cells to later paints);
    ``footprint``, the authored shape, doesn't, so "where is it" and "is this point on it" get the same answer at
    every spacing."""

    cells: Mask
    footprint: Footprint
    solid: bool  # made of a solid material when named; air regions (rooms, doorways) never own a strike point


@dataclass
class MaterialGrid:
    dx: float
    shape: tuple[int, int, int]
    materials: MaterialTable
    material: npt.NDArray[np.uint8] = field(repr=False)
    original_material: npt.NDArray[np.uint8] = field(repr=False)
    integrity: npt.NDArray[np.float32] = field(repr=False)
    temperature: Field = field(repr=False)
    regions: dict[str, Region] = field(default_factory=dict, repr=False)
    time_s: float = 0.0

    @classmethod
    def empty(
        cls,
        extent_m: tuple[float, float, float],
        materials: MaterialTable,
        *,
        dx_m: float,
        ambient_c: float = 20.0,
    ) -> MaterialGrid:
        """An all-air grid over ``extent_m`` in cells of edge ``dx_m``, the simulation's truth resolution (D20)."""
        dx = finite_real(dx_m, "dx_m")
        if not dx > 0:  # the check RigProfile made on cell_size_m before resolution left the rig
            raise ValueError(f"dx_m must be positive, got {dx_m}")
        shape = tuple(max(1, int(np.rint(e / dx))) for e in extent_m)  # int: numpy 1.x round() keeps float64
        for e, n in zip(extent_m, shape, strict=True):
            if abs(n * dx - e) > 1e-6 * max(1.0, e):
                raise ValueError(
                    f"extent {e} m is not a whole number of {dx} m cells; author tile extents as multiples of the "
                    "coarsest grid's cell size so every grid spacing covers the same space"
                )
        return cls(
            dx=dx,
            shape=shape,  # type: ignore[arg-type]
            materials=materials,
            material=np.zeros(shape, dtype=np.uint8),
            original_material=np.zeros(shape, dtype=np.uint8),
            integrity=np.zeros(shape, dtype=np.float32),
            temperature=np.full(shape, ambient_c, dtype=np.float64),
        )

    # -- geometry -----------------------------------------------------------

    @property
    def cell_volume_m3(self) -> float:
        return self.dx**3

    @property
    def extent_m(self) -> tuple[float, float, float]:
        return tuple(n * self.dx for n in self.shape)  # type: ignore[return-value]

    def centers(self, axis: int) -> Field:
        """Cell-centre coordinates along one axis, in metres."""
        return (np.arange(self.shape[axis], dtype=np.float64) + 0.5) * self.dx

    def mesh(self) -> tuple[Field, Field, Field]:
        """Broadcastable cell-centre coordinates (x[:, None, None], y[None, :, None], z[None, None, :])."""
        x = self.centers(0)[:, None, None]
        y = self.centers(1)[None, :, None]
        z = self.centers(2)[None, None, :]
        return x, y, z

    def cell_of(self, point_m: tuple[float, float, float]) -> tuple[int, int, int]:
        idx = tuple(int(np.floor(p / self.dx)) for p in point_m)
        for i, n in zip(idx, self.shape, strict=True):
            if not 0 <= i < n:
                raise ValueError(f"point {point_m} is outside the grid {self.extent_m}")
        return idx  # type: ignore[return-value]

    # -- writing ------------------------------------------------------------

    def paint(
        self, mask: Mask, material_name: str, region: str | None = None, *, footprint: Footprint | None = None
    ) -> None:
        """Fill the cells in ``mask`` with a material at full integrity; optionally name them as a region.

        A named region needs its ``footprint``, its authored shape in metres (see ``Region``).
        """
        if region is not None and any(entity_key(r) == entity_key(region) for r in self.regions):
            raise ValueError(f"region {region!r} already exists")
        if region is not None and footprint is None:
            raise ValueError(f"region {region!r} needs its authored footprint in metres")
        mid = self.materials[material_name].id
        self.material[mask] = mid
        self.original_material[mask] = mid
        self.integrity[mask] = 0.0 if mid == AIR_ID else 1.0
        # A later paint takes cells from any earlier region.
        for other in self.regions.values():
            np.logical_and(other.cells, ~mask, out=other.cells)
        if region is not None:
            assert footprint is not None
            self.name_region(region, mask, footprint, solid=mid != AIR_ID)

    def name_region(self, region: str, mask: Mask, footprint: Footprint, *, solid: bool) -> None:
        """Name the cells in ``mask`` as a region with its footprint, without changing what they are made of.

        Names must differ under Maxim's name normalisation (``entity_key``), because Maxim resolves an NPC's
        "crate" to whichever entity normalises to it: two regions "Crate" and "crate" would let a call aimed at one
        burn the other.
        """
        clash = next((r for r in self.regions if entity_key(r) == entity_key(region)), None)
        if clash is not None:
            raise ValueError(f"region {region!r} already exists" + ("" if clash == region else f" (as {clash!r})"))
        self.regions[region] = Region(mask.copy(), footprint, solid)

    def destroy(self, mask: Mask) -> int:
        """Turn solid cells in ``mask`` to air. Returns how many cells were destroyed."""
        hit = mask & (self.material != AIR_ID)
        n = int(hit.sum())
        if n:
            self.material[hit] = AIR_ID
            self.integrity[hit] = 0.0
        return n

    # -- reading ------------------------------------------------------------

    @property
    def solid(self) -> Mask:
        solid: Mask = self.material != AIR_ID
        return solid

    def volume_m3(self, mask: Mask | None = None) -> float:
        m = self.solid if mask is None else (mask & self.solid)
        return float(m.sum()) * self.cell_volume_m3
