"""Published frames: what observers read instead of the world (boundaries §4.2, B-10; §4.4, B-13).

A frame is an immutable sample of the cells at the end of one tick, stamped with that tick: `Simulation` publishes
frame 0 at construction and one at the end of each tick that applied a record or ran physics (sim_core.md §4,
`tile_and_client.md` §4), whether or not it changed a cell. It holds the
read-only owners of that moment. No window writes an owner in place (``CellStore.writing`` swaps in new ones at exit),
so a frame is a copy in effect, without copying: a reading taken from it is the same however much later it is taken.
A test holds that.

Observers type against ``Observation``, which has no ``advance``, no ``sources`` and no ``grid``, so mypy refuses a
peek at the world behind it. Readings are reductions over a region's cells, so they read the same at every grid
spacing; nothing here reports a cell size.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Protocol

import numpy as np
import numpy.typing as npt

from simcore.core import reductions
from simcore.core.checks import shown
from simcore.core.geometry import Field, Mask
from simcore.core.grid import MaterialGrid, Region
from simcore.core.materials import AIR_ID
from simcore.core.writers import WindowClosed

# Each quantity a region reading may report, with its unit.
QUANTITIES: Mapping[str, str] = MappingProxyType(
    {"integrity": "ratio", "temperature_max": "celsius", "temperature_mean": "celsius", "breached": "bool"}
)


@dataclass(frozen=True)
class CellFrame:
    """The cells at one publication: read-only arrays that no window writes again, and the regions of that moment."""

    sequence: int  # how many frames this world published before this one
    tick: int  # the tick it was published at the end of; 0 is construction
    time_us: int  # the tick's end in whole world microseconds: seconds are derived, never stored (sim_core.md §3)
    dx_m: float
    shape: tuple[int, int, int]
    material: npt.NDArray[np.uint8]
    original_material: npt.NDArray[np.uint8]
    integrity: npt.NDArray[np.float32]
    temperature: Field
    regions: Mapping[str, Region]

    def __post_init__(self) -> None:
        # Frozen means deep, of the type (step 3b review, Executor N6): a frame holds read-only arrays only.
        arrays: dict[str, npt.NDArray[np.generic]] = {
            "material": self.material,
            "original_material": self.original_material,
            "integrity": self.integrity,
            "temperature": self.temperature,
        }
        for name, array in arrays.items():
            if array.flags.writeable:
                raise ValueError(f"a frame's {name} must be read-only (simcore.core.readonly.frozen)")

    @property
    def time_s(self) -> float:
        return self.time_us / 1_000_000

    @classmethod
    def of(cls, grid: MaterialGrid, sequence: int, *, tick: int, time_us: int) -> CellFrame:
        """The grid as it is at rest, never inside a window, whose arrays the window goes on writing. The region
        table is copied: the grid's own view of it follows later windows."""
        if grid.is_writing:
            raise WindowClosed("a frame is published at rest, never while the write window is open")
        return cls(
            sequence,
            tick,
            time_us,
            grid.dx,
            grid.shape,
            grid.material,
            grid.original_material,
            grid.integrity,
            grid.temperature,
            MappingProxyType(dict(grid.regions)),
        )

    @property
    def solid(self) -> Mask:
        solid: Mask = self.material != AIR_ID
        return solid


class Observation(Protocol):
    """What a percept or an instrument may read: one published frame. No ``advance``, ``sources`` or ``grid``."""

    @property
    def sequence(self) -> int: ...

    @property
    def tick(self) -> int: ...

    @property
    def time_s(self) -> float: ...

    @property
    def region_names(self) -> tuple[str, ...]: ...

    def is_solid(self, region: str) -> bool: ...

    def reading(self, region: str, quantity: str) -> float: ...


class FrameSource(Protocol):
    """Where an observer gets the latest frame: a feed, never the world."""

    @property
    def latest(self) -> Observation: ...


@dataclass(frozen=True)
class Frame:
    """One published frame: region readings computed from its cells on demand (an ``Observation``)."""

    cells: CellFrame

    @property
    def sequence(self) -> int:
        return self.cells.sequence

    @property
    def tick(self) -> int:
        return self.cells.tick

    @property
    def time_s(self) -> float:
        return self.cells.time_s

    @property
    def region_names(self) -> tuple[str, ...]:
        return tuple(self.cells.regions)

    def is_solid(self, region: str) -> bool:
        return self._region(region).solid

    def reading(self, region: str, quantity: str) -> float:
        """One quantity of ``QUANTITIES`` over one region's cells, as of this frame."""
        if not isinstance(quantity, str) or quantity not in QUANTITIES:
            raise ValueError(f"unknown region quantity {shown(quantity)}")
        cells = self._region(region).cells
        if quantity == "integrity":
            return reductions.region_integrity(self.cells, region)
        if quantity == "breached":
            return 1.0 if reductions.region_breached(self.cells, region) else 0.0
        temps = self.cells.temperature[cells]
        if temps.size == 0:
            return float("nan")
        return float(np.max(temps) if quantity == "temperature_max" else np.mean(temps))

    def _region(self, region: str) -> Region:
        if not isinstance(region, str) or region not in self.cells.regions:  # one exception type (§5.4)
            raise ValueError(f"no region {shown(region)} in this world")
        return self.cells.regions[region]


class FrameView:
    """What an observer holds: the latest frame of one feed, and no way to publish one (step 3b review, Arch N3)."""

    def __init__(self, feed: FrameFeed) -> None:
        self._feed = feed

    @property
    def latest(self) -> Frame:
        return self._feed.latest


class FrameFeed:
    """The latest frame one simulation published. Only the simulation holds it; observers get a ``FrameView``."""

    def __init__(self, first: Frame) -> None:
        self._latest = first

    @property
    def latest(self) -> Frame:
        return self._latest

    def publish(self, frame: Frame) -> None:
        if frame.sequence != self._latest.sequence + 1:
            raise ValueError(f"frame {frame.sequence} does not follow frame {self._latest.sequence}")
        if frame.tick <= self._latest.tick:  # one frame per tick at most, in tick order (sim_core.md §4)
            raise ValueError(f"a frame for tick {frame.tick} can't follow tick {self._latest.tick}'s")
        self._latest = frame
