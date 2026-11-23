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

from simcore.core.checks import MAXIM_TARGET_ALIASES, entity_key, finite_real, shown
from simcore.core.geometry import Field, GridGeometry, Mask, whole_micrometres
from simcore.core.materials import AIR_ID, MaterialTable
from simcore.core.readonly import frozen
from simcore.core.refusals import RefusalCode, Refused
from simcore.core.schema import Text
from simcore.core.window import WindowOwner
from simcore.core.writers import Gate, WindowClosed, WriterToken

# The one rule for a region's name, whoever names it (a scene file, an imagined object, code): printable, bounded,
# and never a name Maxim resolves to the agent itself (step 3b(b) delta review, D-S1, D-S2).
REGION_NAME = Text(reserved=tuple(MAXIM_TARGET_ALIASES))

# Topology's fields: never handed out writable, so they change only through its edits, which count its batches.
_EDITED_ONLY = frozenset({"material", "original_material"})


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


# What a cell window's rollback restores: the channels, the region table, the clock and the topology version.
_Saved = tuple[dict[str, npt.NDArray[np.generic]], dict[str, "Region"], dict[str, int], int]


class CellStore(WindowOwner[_Saved]):
    """The cells' owner: which arrays exist, and the one window in which they may be written (boundaries §4.1).

    At rest every channel, every region mask and the region table are read-only. A window (``writing``, whose
    lifecycle is `simcore.core.window`'s) holds fresh writable copies as the channels while it is open, and at exit
    swaps in read-only copies of them as the new owners, so a write through a handle kept past the window lands in
    memory the world no longer reads. The region table works the same way: a window that paints holds writable masks
    of its own, narrowed in place, and freezes each once at exit.

    Inside the window the gate (`simcore.core.writers.Gate`) decides access. A writable array goes only to a declared
    writer, and never for `material` or `original_material`, which change only through Topology's edits; anyone else
    gets a view that can't be made writable. A narrowed block's writable arrays are revoked when it ends: the store
    keeps a copy and drops the array it handed out, so a handle kept past its block writes nowhere the world reads.
    """

    def __init__(
        self,
        *,
        material: npt.NDArray[np.uint8],
        original_material: npt.NDArray[np.uint8],
        integrity: npt.NDArray[np.float32],
        temperature: Field,
    ) -> None:
        WindowOwner.__init__(self)
        self._gate = Gate()
        self._topology_version = 0
        self._edited = False  # Topology's open block has painted, named or destroyed something
        self._handed: set[str] = set()  # fields handed out writable in the open narrowed block
        self._views: dict[str, npt.NDArray[np.generic]] = {}  # in the window: each field's frozen read-only copy
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
        # How many times each field may have changed: a cache keyed on a law's bound_reads reads these (sim_core.md
        # §7). Bumped for each block or window a field was handed writable in, and for each edit that changed it.
        self._versions: dict[str, int] = dict.fromkeys(self._channels, 0)
        self._handed_open: set[str] = set()  # handed writable outside a narrowed block (construction's window)
        self._rollbacks = 0  # never restored: a version from a rolled-back window can't be reached again
        self._copied = 0  # field values copied, a work counter (sim_core.md §10); never restored
        self._adopted = False  # a simulation owns these cells: the one owner of their time (sim_core.md §2)

    def adopt(self) -> None:
        """Hands the cells to their one simulation, the one owner of their time (sim_core.md §2). A second adoption
        raises, so no second simulation, over this grid in any world, can publish it as frame 0 or step it."""
        if self._adopted:
            raise ValueError("these cells already have their simulation (sim_core.md §2)")
        self._adopted = True

    def _channel(self, name: str) -> npt.NDArray[np.generic]:
        """The field's array: writable inside the window only for a writer the registry declares for it, and for
        anyone else a frozen copy, whose memory is immutable bytes that reach no writable array, so an undeclared write
        raises and the copy can't be unlocked (sim_core.md §5.1). The copy is made once per change of the field: a
        writer's revocation and Topology's edits drop it. A narrowed block reads only what its writer declares."""
        arr = self._channels[name]
        if self._open or self._gate.narrowed:
            self._gate.require_read(name)  # a narrowed reader reads only what it declares, in a window or at rest
        if not self._open:
            return arr  # frozen: nothing can make it writable (readonly.frozen)
        if name not in _EDITED_ONLY and self._gate.may_write(name):
            (self._handed if self._gate.narrowed else self._handed_open).add(name)
            return arr
        view = self._views.get(name)
        if view is None:
            view = self._views[name] = self._counted(frozen(arr))
        return view

    @property
    def cells_copied(self) -> int:
        """How many field values the windows have copied so far: at open, at commit, for read-only views and for
        revoked writable arrays (sim_core.md §10). A tick's count is the change over it."""
        return self._copied

    def _counted(self, arr: npt.NDArray[np.generic]) -> npt.NDArray[np.generic]:
        self._copied += arr.size
        return arr

    def field_version(self, name: str) -> tuple[int, int]:
        """A key that moves whenever ``name``'s values may have changed (it may move when they didn't): the grid's
        rollbacks, which never go back, and a count a rollback restores. So no key a rolled-back window reached is
        ever reached again, and a cache keyed on these, whoever owns it, can't serve a state it wasn't built from."""
        if name == "regions":  # the table moves only in Topology's batches, which bump the topology version
            return self._rollbacks, self._topology_version
        return self._rollbacks, self._versions[name]

    @property
    def topology_version(self) -> int:
        """How many of Topology's batches have changed the cells or the region table (sim_core.md §5.1, §7)."""
        return self._topology_version

    @contextmanager
    def reading(self, *, reads: tuple[str, ...]) -> Iterator[None]:
        """Narrow to a reader that writes nothing and reads only ``reads``, in a window or at rest: a law's bound,
        prepare and cache warm-up read what the law declares and nothing else (sim_core.md §5)."""
        with self._gate.narrow(None, reads):  # no writer: nothing is handed out writable, so nothing to revoke
            yield

    @contextmanager
    def as_writer(self, writer: WriterToken | None, *, reads: tuple[str, ...] | None = None) -> Iterator[None]:
        """Narrow the open window to ``writer``'s token for the block (``simcore.core.writers``): the orchestrator
        around each law's step, and Topology around each batch. A batch that changed anything bumps
        ``topology_version`` once, even if it then raised: its edits are in the window's cells until the window rolls
        back, which restores the version too. The block's writable arrays are revoked at its end."""
        self._require_window("a narrowed writer")
        with self._gate.narrow(writer, reads):
            self._edited = False
            try:
                yield
            finally:
                self._topology_version += self._edited
                self._edited = False
                for name in self._handed:
                    self._channels[name] = self._counted(self._channels[name].copy())
                    self._views.pop(name, None)
                    self._versions[name] += 1
                self._handed.clear()

    def _require_window(self, what: str) -> None:
        if not self._open:
            raise WindowClosed(f"{what} changes only inside the write window (boundaries §4.1)")

    @property
    def material(self) -> npt.NDArray[np.uint8]:
        return self._channel("material")  # type: ignore[return-value]

    @property
    def original_material(self) -> npt.NDArray[np.uint8]:
        return self._channel("original_material")  # type: ignore[return-value]

    @property
    def integrity(self) -> npt.NDArray[np.float32]:
        return self._channel("integrity")  # type: ignore[return-value]

    @property
    def temperature(self) -> Field:
        return self._channel("temperature")  # type: ignore[return-value]

    @property
    def regions(self) -> Mapping[str, Region]:
        if self._open or self._gate.narrowed:
            self._gate.require_read("regions")
        return MappingProxyType(self._region_table())

    def _window_table(self) -> tuple[dict[str, Mask], dict[str, tuple[Footprint, bool]]]:
        """This window's changed region masks (writable, narrowed in place) and every region's footprint and
        solidity in table order, set up at the first paint or naming in the window."""
        if self._masks is None:
            self._masks = {}
            self._meta = {n: (r.footprint, r.solid) for n, r in self._regions.items()}
        return self._masks, self._meta

    def _take_cells(self, mask: Mask) -> bool:
        """A later paint takes cells from any earlier region; returns whether it took any. Only a region it actually
        takes cells from is copied and later refrozen, and only the box the mask covers is read (step 3b review,
        Trust S5)."""
        self._window_table()
        assert self._masks is not None
        box = _bounding_box(mask)
        if box is None:
            return False
        keep, took = ~mask[box], False
        for name in self._meta:
            cells = self._masks[name] if name in self._masks else self._regions[name].cells
            if np.all(cells[box] <= keep):  # it holds no cell the paint takes
                continue
            if name not in self._masks:
                self._masks[name] = cells.copy()
            np.logical_and(self._masks[name][box], keep, out=self._masks[name][box])
            took = True
        return took

    def _region_table(self) -> dict[str, Region]:
        if self._masks is None:
            return self._regions
        masks = self._masks
        return {n: Region(masks[n], *m) if n in masks else self._regions[n] for n, m in self._meta.items()}

    # -- the window (its lifecycle is WindowOwner's) --------------------------------------------------------------

    def _open_window(self, writer: WriterToken | None) -> _Saved:
        self._gate.open(writer)
        saved = (self._channels, self._regions, dict(self._versions), self._topology_version)
        self._channels = {name: self._counted(arr.copy()) for name, arr in self._channels.items()}
        self._masks = None
        self._views.clear()
        return saved

    def _prepare_commit(self) -> Callable[[], None]:
        channels = {name: self._counted(frozen(arr)) for name, arr in self._channels.items()}
        table = self._region_table()

        def install() -> None:
            self._channels, self._regions = channels, table
            for name in self._handed_open:
                self._versions[name] += 1

        return install

    def _roll_back(self, saved: _Saved) -> None:
        self._channels, self._regions, self._versions, self._topology_version = saved
        self._rollbacks += 1

    def _close_window(self) -> None:
        self._masks, self._views, self._handed_open = None, {}, set()
        self._gate.close()


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
        dx_um = whole_micrometres(dx, "dx_m")
        cells = []
        for e in extent_m:
            n, rest = divmod(whole_micrometres(e, "extent_m"), dx_um)
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
            raise Refused(f"region {shown(region)} already exists", code=RefusalCode.NAME_TAKEN)
        if region is not None and footprint is None:
            raise Refused(
                f"region {shown(region)} needs its authored footprint in metres", code=RefusalCode.MISSING_FIELD
            )
        self._require_edit("a paint", "material", "original_material", "integrity", "regions")
        mid = self.materials[material_name].id
        values = (("material", mid), ("original_material", mid), ("integrity", float(mid != AIR_ID)))
        if self._set_cells(mask, values) | self._take_cells(mask):  # both run: `|`, not `or`
            self._edited = True
        if region is not None:
            assert footprint is not None
            self.name_region(region, mask, footprint, solid=mid != AIR_ID)

    def name_region(self, region: str, mask: Mask, footprint: Footprint, *, solid: bool) -> None:
        """Name the cells in ``mask`` as a region with its footprint, without changing what they are made of.

        Names must differ under Maxim's name normalisation (``entity_key``), because Maxim resolves an NPC's
        "crate" to whichever entity normalises to it: two regions "Crate" and "crate" would let a call aimed at one
        burn the other.
        """
        REGION_NAME.convert(region, "a region's name")
        clash = next((r for r in self._region_names() if entity_key(r) == entity_key(region)), None)
        if clash is not None:
            message = f"region {shown(region)} already exists" + ("" if clash == region else f" (as {shown(clash)})")
            raise Refused(message, code=RefusalCode.NAME_TAKEN)
        self._require_edit("a region", "regions")
        self._window_table()
        assert self._masks is not None
        self._masks[region] = np.array(mask, dtype=np.bool_)  # broadcast or not, a mask of its own
        self._meta[region] = (footprint, solid)
        self._edited = True

    def _region_names(self) -> Iterator[str]:
        return iter(self._meta if self._masks is not None else self._regions)

    def destroy(self, mask: Mask) -> int:
        """Turn solid cells in ``mask`` to air. Returns how many cells were destroyed. Topology's (sim_core.md §5.1)."""
        self._require_edit("a destruction", "material", "integrity")
        hit = mask & (self._channels["material"] != AIR_ID)
        n = int(hit.sum())
        if n:
            self._set_cells(hit, (("material", AIR_ID), ("integrity", 0.0)))
            self._edited = True
        return n

    def _set_cells(self, mask: Mask, values: tuple[tuple[str, float], ...]) -> bool:
        """Set each field's cells in ``mask`` to its value, in place, and drop the fields' read-only copies. Returns
        whether any value changed: a batch moves ``topology_version`` only if it changed a value (sim_core.md §5.1)."""
        changed = False
        for name, value in values:
            differs = bool((self._channels[name][mask] != value).any())
            self._channels[name][mask] = value  # in place, through the owner's dict: the writer scan sees it
            self._views.pop(name, None)
            self._versions[name] += differs
            changed = changed or differs
        return changed

    def _require_edit(self, what: str, *fields: str) -> None:
        self._require_window(what)
        self._gate.require_editor(what)
        for field in fields:
            self._gate.require_writer(field)

    # -- reading ------------------------------------------------------------

    @property
    def solid(self) -> Mask:
        solid: Mask = self.material != AIR_ID
        return solid

    def volume_m3(self, mask: Mask | None = None) -> float:
        m = self.solid if mask is None else (mask & self.solid)
        return float(m.sum()) * self.cell_volume_m3
