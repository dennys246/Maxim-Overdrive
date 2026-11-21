"""The world as material cells: a structure of arrays, one value per cell.

Every cell holds a material id, an integrity in [0, 1] and a temperature in °C. Physics fields (heat today; sound,
light and gas later) and damage write these arrays in place, inside the write window (``CellStore.writing``), and
nowhere else: at rest every array is read-only, and nothing can make it writable again (boundaries §4.1). Observers
read published frames (``simcore.core.frames``), never the grid.

Cell ``(i, j, k)`` covers ``[i*dx, (i+1)*dx) x [j*dx, (j+1)*dx) x [k*dx, (k+1)*dx)`` in metres; z is up.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from types import MappingProxyType
from typing import Protocol

import numpy as np
import numpy.typing as npt

from simcore.core.checks import entity_key, finite_real
from simcore.core.materials import AIR_ID, MaterialTable
from simcore.core.readonly import frozen
from simcore.core.refusals import RefusalCode, Refused

UM_PER_M = 1_000_000


def _whole_micrometres(length_m: float, what: str) -> int:
    """A length as whole micrometres, or a Refused: cell edges are integer micrometres (F13, fire_solid §1.3)."""
    um = round(length_m * UM_PER_M)
    if abs(length_m * UM_PER_M - um) > 1e-3:  # a nanometre: float noise on a whole micrometre, never a real length
        raise Refused(f"{what} {length_m} m is not a whole number of micrometres", code=RefusalCode.OUT_OF_RANGE)
    return um


# Array types for the grid's fields. Typing the element type (not bare np.ndarray) is what strict mypy needs on every
# supported numpy: older stubs give ndarray no default type parameters.
Mask = npt.NDArray[np.bool_]
Field = npt.NDArray[np.float64]
# A region's authored extent in metres, (min corner, max corner). It is kept beside the region's cells because the
# cells depend on the grid spacing and the authored bounds don't, so anything that asks "is this point on the region?"
# gets the same answer at every spacing.
Bounds = tuple[tuple[float, float, float], tuple[float, float, float]]
Point = tuple[float, float, float]


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

    def __post_init__(self) -> None:
        # Frozen means deep (boundaries §5.1): the mask is a read-only copy, so no holder can repaint the region.
        object.__setattr__(self, "cells", frozen(np.asarray(self.cells, dtype=np.bool_)))


class CellState(Protocol):
    """What a reduction over a region reads: a grid at rest, or a published frame (``simcore.core.frames``)."""

    @property
    def material(self) -> npt.NDArray[np.uint8]: ...

    @property
    def original_material(self) -> npt.NDArray[np.uint8]: ...

    @property
    def integrity(self) -> npt.NDArray[np.float32]: ...

    @property
    def regions(self) -> Mapping[str, Region]: ...


def _bounding_box(mask: Mask) -> tuple[slice, slice, slice] | None:
    """The smallest box of cells holding every True cell of ``mask``, or None when it has none."""
    spans = []
    for axis in range(3):
        hits = np.flatnonzero(mask.any(axis=tuple(a for a in range(3) if a != axis)))
        if hits.size == 0:
            return None
        spans.append(slice(int(hits[0]), int(hits[-1]) + 1))
    return spans[0], spans[1], spans[2]


class GridGeometry:
    """Where the cells are: the spacing and the shape, and the coordinates that follow from them."""

    def __init__(self, dx: float, shape: tuple[int, int, int]) -> None:
        self._dx, self._shape = dx, shape

    @property
    def dx(self) -> float:
        return self._dx

    @property
    def shape(self) -> tuple[int, int, int]:
        return self._shape

    @property
    def cell_volume_m3(self) -> float:
        return self._dx**3

    @property
    def extent_m(self) -> tuple[float, float, float]:
        return tuple(n * self._dx for n in self._shape)  # type: ignore[return-value]

    def centers(self, axis: int) -> Field:
        """Cell-centre coordinates along one axis, in metres."""
        return (np.arange(self._shape[axis], dtype=np.float64) + 0.5) * self._dx

    def mesh(self) -> tuple[Field, Field, Field]:
        """Broadcastable cell-centre coordinates (x[:, None, None], y[None, :, None], z[None, None, :])."""
        x = self.centers(0)[:, None, None]
        y = self.centers(1)[None, :, None]
        z = self.centers(2)[None, None, :]
        return x, y, z

    def cell_of(self, point_m: tuple[float, float, float]) -> tuple[int, int, int]:
        idx = tuple(int(np.floor(p / self._dx)) for p in point_m)
        for i, n in zip(idx, self._shape, strict=True):
            if not 0 <= i < n:
                raise ValueError(f"point {point_m} is outside the grid {self.extent_m}")
        return idx  # type: ignore[return-value]


class WindowClosed(RuntimeError):
    """A write was attempted outside the write window: a programming error, never untrusted input."""


class CellStore:
    """The cells' owner: which arrays exist, and the one window in which they may be written (boundaries §4.1).

    At rest every channel, every region mask and the region table are read-only. ``writing()`` hands out fresh
    writable copies as the channels for the length of the window, and at exit swaps in read-only copies of them as the
    new owners, so no writable handle, and no view of one unlocked inside the window, outlives it: a write through any
    of them after exit lands in memory the world no longer reads. The region table works the same way: a window that
    paints holds writable masks of its own, narrowed in place, and freezes each once at exit. Everything new is built
    before anything is committed, so a window that raises, in its body or while it closes, is rolled back whole.
    """

    def __init__(
        self,
        *,
        material: npt.NDArray[np.uint8],
        original_material: npt.NDArray[np.uint8],
        integrity: npt.NDArray[np.float32],
        temperature: Field,
    ) -> None:
        self._channels: dict[str, npt.NDArray[np.generic]] = {
            "material": frozen(material),
            "original_material": frozen(original_material),
            "integrity": frozen(integrity),
            "temperature": frozen(temperature),
        }
        self._regions: dict[str, Region] = {}
        # Inside a window that paints: each region's writable mask, and its footprint and solidity, in table order.
        self._masks: dict[str, Mask] | None = None
        self._meta: dict[str, tuple[Footprint, bool]] = {}
        self._time_s = 0.0
        self._open = False
        self._held = False  # the world's sources-only window: the same one owner as the cells' window
        self._on_close: list[Callable[[], None]] = []

    @property
    def material(self) -> npt.NDArray[np.uint8]:
        return self._channels["material"]  # type: ignore[return-value]

    @property
    def original_material(self) -> npt.NDArray[np.uint8]:
        return self._channels["original_material"]  # type: ignore[return-value]

    @property
    def integrity(self) -> npt.NDArray[np.float32]:
        return self._channels["integrity"]  # type: ignore[return-value]

    @property
    def temperature(self) -> Field:
        return self._channels["temperature"]  # type: ignore[return-value]

    @property
    def regions(self) -> Mapping[str, Region]:
        return MappingProxyType(self._region_table())

    @property
    def time_s(self) -> float:
        return self._time_s

    @time_s.setter
    def time_s(self, value: float) -> None:
        self._require_window("the clock")
        self._time_s = value

    @property
    def is_writing(self) -> bool:
        """Whether the write window is open now."""
        return self._open

    def on_close(self, callback: Callable[[], None]) -> None:
        """Call ``callback`` after each window that closes without raising, whether or not it changed anything (the
        world publishes a frame there)."""
        self._on_close.append(callback)

    def _require_window(self, what: str) -> None:
        if not self._open:
            raise WindowClosed(f"{what} changes only inside the write window (boundaries §4.1)")

    def _window_table(self) -> tuple[dict[str, Mask], dict[str, tuple[Footprint, bool]]]:
        """This window's changed region masks (writable, narrowed in place) and every region's footprint and
        solidity in table order, set up at the first paint or naming in the window."""
        if self._masks is None:
            self._masks = {}
            self._meta = {n: (r.footprint, r.solid) for n, r in self._regions.items()}
        return self._masks, self._meta

    def _take_cells(self, mask: Mask) -> None:
        """A later paint takes cells from any earlier region. Only a region it actually takes cells from is copied
        and later refrozen, and only the box the mask covers is read (step 3b review, Trust S5)."""
        self._window_table()
        assert self._masks is not None
        box = _bounding_box(mask)
        if box is None:
            return
        keep = ~mask[box]
        for name in self._meta:
            if name in self._masks:
                np.logical_and(self._masks[name][box], keep, out=self._masks[name][box])
            elif not np.all(self._regions[name].cells[box] <= keep):  # it holds a cell the paint takes
                self._masks[name] = self._regions[name].cells.copy()
                np.logical_and(self._masks[name][box], keep, out=self._masks[name][box])

    def _region_table(self) -> dict[str, Region]:
        if self._masks is None:
            return self._regions
        masks = self._masks
        return {n: Region(masks[n], *m) if n in masks else self._regions[n] for n, m in self._meta.items()}

    def _refuse_a_second_owner(self) -> None:
        if self._open or self._held:
            raise WindowClosed("the write window is already open: it has one owner at a time")

    @contextmanager
    def holding(self) -> Iterator[None]:
        """The window's ownership without the cells: held by the world's sources-only window, so neither window
        opens while the other is open (step 3b delta review, Executor S-a). Copies nothing, publishes nothing."""
        self._refuse_a_second_owner()
        self._held = True
        try:
            yield
        finally:
            self._held = False

    @contextmanager
    def writing(self) -> Iterator[None]:
        """The write window. One owner at a time: a window opened inside another, or inside ``holding``, is
        refused."""
        self._refuse_a_second_owner()
        owners, regions, time_s = self._channels, self._regions, self._time_s
        self._channels, self._masks, self._open = {name: arr.copy() for name, arr in owners.items()}, None, True
        try:
            yield
            channels = {name: frozen(arr) for name, arr in self._channels.items()}  # built before anything commits
            table = self._region_table()
        except BaseException:
            self._channels, self._regions, self._time_s = owners, regions, time_s
            raise
        else:
            self._channels, self._regions = channels, table
        finally:
            self._masks, self._open = None, False
        for callback in self._on_close:
            callback()


class MaterialGrid(GridGeometry, CellStore):
    """Cells of one material table over a box in metres: painting, named regions and destruction."""

    def __init__(
        self,
        dx: float,
        shape: tuple[int, int, int],
        materials: MaterialTable,
        *,
        material: npt.NDArray[np.uint8],
        original_material: npt.NDArray[np.uint8],
        integrity: npt.NDArray[np.float32],
        temperature: Field,
    ) -> None:
        GridGeometry.__init__(self, dx, shape)
        CellStore.__init__(
            self, material=material, original_material=original_material, integrity=integrity, temperature=temperature
        )
        self._materials = materials

    @property
    def materials(self) -> MaterialTable:
        return self._materials

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
            raise Refused(f"dx_m must be positive, got {dx_m}", code=RefusalCode.OUT_OF_RANGE, field="dx_m")
        # Grid alignment is checked in integers (world_model F13): 0.6 / 0.2 is 2.9999999999999996 in floats, so a
        # float test needs a tolerance that some extent always falls across. Whole micrometres have no such edge.
        dx_um = _whole_micrometres(dx, "dx_m")
        cells = []
        for e in extent_m:
            n, rest = divmod(_whole_micrometres(e, "extent_m"), dx_um)
            if rest or n < 1:
                raise Refused(
                    f"extent {e} m is not a whole number of {dx} m cells; author tile extents as multiples of the "
                    "coarsest grid's cell size so every grid spacing covers the same space",
                    code=RefusalCode.OUT_OF_RANGE,
                    field="extent_m",
                )
            cells.append(n)
        shape = (cells[0], cells[1], cells[2])
        return cls(
            dx,
            shape,
            materials,
            material=np.zeros(shape, dtype=np.uint8),
            original_material=np.zeros(shape, dtype=np.uint8),
            integrity=np.zeros(shape, dtype=np.float32),
            temperature=np.full(shape, ambient_c, dtype=np.float64),
        )

    # -- writing (inside the window) ----------------------------------------

    def paint(
        self, mask: Mask, material_name: str, region: str | None = None, *, footprint: Footprint | None = None
    ) -> None:
        """Fill the cells in ``mask`` with a material at full integrity; optionally name them as a region.

        A named region needs its ``footprint``, its authored shape in metres (see ``Region``).
        """
        if region is not None and any(entity_key(r) == entity_key(region) for r in self._region_names()):
            raise Refused(f"region {region!r} already exists", code=RefusalCode.NAME_TAKEN)
        if region is not None and footprint is None:
            raise ValueError(f"region {region!r} needs its authored footprint in metres")
        self._require_window("a paint")
        mid = self.materials[material_name].id
        self.material[mask] = mid
        self.original_material[mask] = mid
        self.integrity[mask] = 0.0 if mid == AIR_ID else 1.0
        self._take_cells(mask)
        if region is not None:
            assert footprint is not None
            self.name_region(region, mask, footprint, solid=mid != AIR_ID)

    def name_region(self, region: str, mask: Mask, footprint: Footprint, *, solid: bool) -> None:
        """Name the cells in ``mask`` as a region with its footprint, without changing what they are made of.

        Names must differ under Maxim's name normalisation (``entity_key``), because Maxim resolves an NPC's
        "crate" to whichever entity normalises to it: two regions "Crate" and "crate" would let a call aimed at one
        burn the other.
        """
        clash = next((r for r in self._region_names() if entity_key(r) == entity_key(region)), None)
        if clash is not None:
            message = f"region {region!r} already exists" + ("" if clash == region else f" (as {clash!r})")
            raise Refused(message, code=RefusalCode.NAME_TAKEN)
        self._require_window("a region")
        self._window_table()
        assert self._masks is not None
        self._masks[region] = np.array(mask, dtype=np.bool_)  # broadcast or not, a mask of its own
        self._meta[region] = (footprint, solid)

    def _region_names(self) -> Iterator[str]:
        return iter(self._meta if self._masks is not None else self._regions)

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
