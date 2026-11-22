"""Test-side authoring: world edits go through Topology, as every requester's do (sim_core.md §5.1).

Each helper is one batch of one request, applied inside the window the test opened (usually ``scene.constructing``).
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

from simcore.core import heat, physics, topology
from simcore.core.fields import FIELDS
from simcore.core.grid import Field, Footprint, Mask, MaterialGrid
from simcore.core.law import Cadence, Changes, LawInputs


def paint(
    grid: MaterialGrid, mask: Mask, material: str, region: str | None = None, *, footprint: Footprint | None = None
) -> None:
    topology.apply(grid, [topology.Paint(mask, material, region, footprint)])


def name_region(grid: MaterialGrid, region: str, mask: Mask, footprint: Footprint, *, solid: bool) -> None:
    topology.apply(grid, [topology.NameRegion(region, mask, footprint, solid)])


def destroy(grid: MaterialGrid, mask: Mask) -> int:
    return topology.apply(grid, [topology.Destroy(mask)])


def heat_alone(
    grid: MaterialGrid, seconds: float, refine: int = 1, power: Callable[[], Field | None] | None = None
) -> int:
    """Heat alone, the one-law tuple through the orchestrator, inside the open window, as one fixed physics step of
    ``seconds`` refined ``refine`` times. Returns the substeps taken."""
    return physics.run_physics(grid, seconds, refine=refine, power=power or (lambda: None), laws=(heat.HEAT,))


@dataclass(frozen=True)
class _AsLaw:
    """A test law that runs ``body`` as its step, with the declared reads and writes of the law it is named for."""

    body: Callable[[MaterialGrid], object]
    name: str
    reads: tuple[str, ...]
    writes: tuple[str, ...]
    version: int = 1
    cadence: Cadence = Cadence.PER_SUBSTEP

    def stable_dt(self, grid: MaterialGrid) -> float:
        return math.inf

    def step(self, grid: MaterialGrid, dt_s: float, inputs: LawInputs) -> Changes:
        self.body(grid)
        return Changes()


def as_law(grid: MaterialGrid, body: Callable[[MaterialGrid], object], name: str = "heat") -> None:
    """Run ``body`` as the law ``name`` (heat by default), reading every field and writing what the registry declares
    for it, inside the open window: how a test writes a law's field the way a law does."""
    writes = tuple(f.name for f in FIELDS if name in f.writers)
    physics._run_as(grid, _AsLaw(body, name, tuple(f.name for f in FIELDS), writes), 0.0, LawInputs())
