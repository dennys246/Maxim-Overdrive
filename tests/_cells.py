"""Test-side authoring: world edits go through Topology, as every requester's do (sim_core.md §5.1).

Each helper is one batch of one request, applied inside the window the test opened (usually ``scene.constructing``).
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

from simcore.core import heat, physics, topology
from simcore.core.exposure import Exposure
from simcore.core.fields import FIELDS
from simcore.core.geometry import Mask
from simcore.core.grid import Footprint, MaterialGrid
from simcore.core.law import STATELESS, Cadence, Changes, LawInputs, LawState

NO_SOURCES = Exposure((), 1)


def paint(
    grid: MaterialGrid, mask: Mask, material: str, region: str | None = None, *, footprint: Footprint | None = None
) -> None:
    topology.apply(grid, [topology.Paint(mask, material, region, footprint)])


def name_region(grid: MaterialGrid, region: str, mask: Mask, footprint: Footprint, *, solid: bool) -> None:
    topology.apply(grid, [topology.NameRegion(region, mask, footprint, solid)])


def destroy(grid: MaterialGrid, mask: Mask) -> int:
    return topology.apply(grid, [topology.Destroy(mask)])


def heat_alone(grid: MaterialGrid, seconds: float, refine: int = 1, exposure: Exposure = NO_SOURCES) -> int:
    """Heat alone, the one-law tuple through an orchestrator of its own, inside the open window, as one fixed physics
    step of ``seconds`` refined ``refine`` times, the sources' shares ``exposure`` (none by default). Returns the
    substeps taken."""
    return physics.Physics(grid, (heat.HEAT,)).run(seconds, refine=refine, exposure=exposure)


@dataclass(frozen=True)
class _AsLaw:
    """A test law that runs ``body`` as its step, with the declared reads and writes of the law it is named for."""

    body: Callable[[MaterialGrid], object]
    name: str
    reads: tuple[str, ...]
    writes: tuple[str, ...]
    version: int = 1
    cadence: Cadence = Cadence.PER_SUBSTEP
    bound_reads: tuple[str, ...] = ()

    def new_state(self, grid: MaterialGrid) -> LawState:
        return STATELESS

    def prepare(self, grid: MaterialGrid, state: LawState, exposure: Exposure) -> LawInputs:
        return LawInputs()

    def stable_dt(self, grid: MaterialGrid, state: LawState) -> float:
        return math.inf

    def step(self, grid: MaterialGrid, dt_s: float, inputs: LawInputs, state: LawState) -> Changes:
        self.body(grid)
        return Changes()


def as_law(grid: MaterialGrid, body: Callable[[MaterialGrid], object], name: str = "heat") -> None:
    """Run ``body`` as the law ``name`` (heat by default), reading every field and writing what the registry declares
    for it, inside the open window: how a test writes a law's field the way a law does."""
    writes = tuple(f.name for f in FIELDS if name in f.writers)
    physics._run_as(grid, _AsLaw(body, name, tuple(f.name for f in FIELDS), writes), 0.0, LawInputs())
