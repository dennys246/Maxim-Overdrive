"""The world as material cells: a structure of arrays, one value per cell.

Every cell holds a material id, an integrity in [0, 1] and a temperature in °C. Physics fields (heat today; sound,
light and gas later) and damage read and write these arrays in place. SEM entities for the environment are views
over sets of cells (``sem_env``); renderers read quantized copies (``world.snapshot``).

Cell ``(i, j, k)`` covers ``[i*dx, (i+1)*dx) x [j*dx, (j+1)*dx) x [k*dx, (k+1)*dx)`` in metres; z is up.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from maxim_overdrive.config import AIR_ID, MaterialTable, RigProfile


@dataclass
class MaterialGrid:
    dx: float
    shape: tuple[int, int, int]
    materials: MaterialTable
    material: np.ndarray = field(repr=False)
    original_material: np.ndarray = field(repr=False)
    integrity: np.ndarray = field(repr=False)
    temperature: np.ndarray = field(repr=False)
    regions: dict[str, np.ndarray] = field(default_factory=dict, repr=False)
    time_s: float = 0.0

    @classmethod
    def empty(
        cls,
        extent_m: tuple[float, float, float],
        rig: RigProfile,
        materials: MaterialTable,
        ambient_c: float = 20.0,
    ) -> MaterialGrid:
        dx = rig.cell_size_m
        shape = tuple(max(1, round(e / dx)) for e in extent_m)
        for e, n in zip(extent_m, shape, strict=True):
            if abs(n * dx - e) > 1e-6 * max(1.0, e):
                raise ValueError(
                    f"extent {e} m is not a whole number of {dx} m cells; author tile extents as multiples of the "
                    "coarsest rig's cell size so every rig covers the same space"
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

    def centers(self, axis: int) -> np.ndarray:
        """Cell-centre coordinates along one axis, in metres."""
        return (np.arange(self.shape[axis]) + 0.5) * self.dx

    def mesh(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
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

    def paint(self, mask: np.ndarray, material_name: str, region: str | None = None) -> None:
        """Fill the cells in ``mask`` with a material at full integrity; optionally name them as a region."""
        mid = self.materials[material_name].id
        self.material[mask] = mid
        self.original_material[mask] = mid
        self.integrity[mask] = 0.0 if mid == AIR_ID else 1.0
        if region is not None:
            if region in self.regions:
                raise ValueError(f"region {region!r} already exists")
            self.regions[region] = mask.copy()
        # A later paint takes cells from any earlier region.
        for name, other in self.regions.items():
            if name != region:
                np.logical_and(other, ~mask, out=other)

    def destroy(self, mask: np.ndarray) -> int:
        """Turn solid cells in ``mask`` to air. Returns how many cells were destroyed."""
        hit = mask & (self.material != AIR_ID)
        n = int(hit.sum())
        if n:
            self.material[hit] = AIR_ID
            self.integrity[hit] = 0.0
        return n

    # -- reading ------------------------------------------------------------

    @property
    def solid(self) -> np.ndarray:
        solid: np.ndarray = self.material != AIR_ID
        return solid

    def volume_m3(self, mask: np.ndarray | None = None) -> float:
        m = self.solid if mask is None else (mask & self.solid)
        return float(m.sum()) * self.cell_volume_m3
