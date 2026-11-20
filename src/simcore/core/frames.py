"""Published frames: what observers read instead of the world (boundaries §4.2, B-10; §4.4, B-13).

A frame is an immutable sample of the cells, published when they change: after each write window closes, which is
after each intent application and each advance (and at construction). It holds the read-only owners of that moment.
No window writes an owner in place (``CellStore.writing`` swaps in new ones at exit), so a frame is a copy in effect,
without copying: a reading taken from it is the same however much later it is taken. A test holds that.

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

from simcore.core import damage
from simcore.core.checks import shown
from simcore.core.grid import Field, Mask, MaterialGrid, Region, WindowClosed
from simcore.core.materials import AIR_ID

# Each quantity a region reading may report, with its unit.
QUANTITIES: Mapping[str, str] = MappingProxyType(
    {"integrity": "ratio", "temperature_max": "celsius", "temperature_mean": "celsius", "breached": "bool"}
)


@dataclass(frozen=True)
class CellFrame:
    """The cells at one publication: read-only arrays that no window writes again, and the regions of that moment."""

    sequence: int  # how many frames this world published before this one
    time_s: float
    dx_m: float
    shape: tuple[int, int, int]
    material: npt.NDArray[np.uint8]
    original_material: npt.NDArray[np.uint8]
    integrity: npt.NDArray[np.float32]
    temperature: Field
    regions: Mapping[str, Region]

    def __post_init__(self) -> None:
        # Frozen means deep, of the type (step 3b review, Executor N6): a frame holds read-only arrays only.
        for name in ("material", "original_material", "integrity", "temperature"):
            if self.__dict__[name].flags.writeable:
                raise ValueError(f"a frame's {name} must be read-only (simcore.core.readonly.frozen)")

    @classmethod
    def of(cls, grid: MaterialGrid, sequence: int) -> CellFrame:
        """The grid as it is at rest, never inside a window, whose arrays the window goes on writing. The region
        table is copied: the grid's own view of it follows later windows."""
        if grid.is_writing:
            raise WindowClosed("a frame is published at rest, never while the write window is open")
        return cls(
            sequence,
            grid.time_s,
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
            return damage.region_integrity(self.cells, region)
        if quantity == "breached":
            return 1.0 if damage.region_breached(self.cells, region) else 0.0
        temps = self.cells.temperature[cells]
        if temps.size == 0:
            return float("nan")
        return float(np.max(temps) if quantity == "temperature_max" else np.mean(temps))

    def _region(self, region: str) -> Region:
        if not isinstance(region, str) or region not in self.cells.regions:
            raise KeyError(f"no region {shown(region)} in this world")
        return self.cells.regions[region]


class FrameView:
    """What an observer holds: the latest frame of one feed, and no way to publish one (step 3b review, Arch N3)."""

    def __init__(self, feed: FrameFeed) -> None:
        self._feed = feed

    @property
    def latest(self) -> Frame:
        return self._feed.latest


class FrameFeed:
    """The latest frame one world published. Only the world holds it; observers get a ``FrameView``."""

    def __init__(self, first: Frame) -> None:
        self._latest = first

    @property
    def latest(self) -> Frame:
        return self._latest

    def publish(self, frame: Frame) -> None:
        if frame.sequence != self._latest.sequence + 1:
            raise ValueError(f"frame {frame.sequence} does not follow frame {self._latest.sequence}")
        self._latest = frame
