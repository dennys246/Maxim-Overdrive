"""What a law is (`docs/design/sim_core.md` §5): its name, version, cadence, the fields it reads and writes, and one
`step`. Not a law itself: the laws (`heat`, `damage`) import this, and no law imports another (§5.1, held by the
`laws-independent` import contract), so what two laws share lives here.

A law writes only as itself, and never narrows itself: the orchestrator runs `step` narrowed to the law's token
(`simcore.core.physics.run_law`), so the window refuses a read of a field outside `reads` and a write to a field the
registry doesn't list the law as a writer of (`simcore.core.fields`), and revokes the law's writable arrays when its
step ends. World edits are requests in `Changes`, which Topology applies per batch (`simcore.core.topology`).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from simcore.core.checks import finite_real, finite_vector
from simcore.core.grid import Field, MaterialGrid, Point
from simcore.core.topology import Request


class Cadence(StrEnum):
    """When a law runs (§5). The orchestrator runs the groups in this order; tuple order orders a law within one."""

    PER_RECORD = "per_record"
    PER_TICK = "per_tick"
    PER_PHYSICS_STEP = "per_physics_step"
    PER_SUBSTEP = "per_substep"


@dataclass(frozen=True)
class Load:
    """One mechanical load an input put into the world (§5.1): a strike's energy, width and point. Damage resolves
    every load kind; a later kind (ballistic, chemical) is a new ``kind`` with its resolver inside damage."""

    kind: str
    point_m: Point
    energy_j: float
    sigma_m: float

    def __post_init__(self) -> None:
        # Physical validity where a load is made, whoever makes it (the applier's limits are gameplay's, checked
        # earlier): a finite point, a finite non-negative energy and a finite positive width.
        object.__setattr__(self, "point_m", finite_vector(self.point_m, 3, f"a {self.kind}'s point_m"))
        energy_j = finite_real(self.energy_j, f"a {self.kind}'s energy_j")
        sigma_m = finite_real(self.sigma_m, f"a {self.kind}'s sigma_m")
        if energy_j < 0 or sigma_m <= 0:
            message = f"a {self.kind} needs non-negative energy and positive sigma, got {energy_j!r} J, {sigma_m!r} m"
            raise ValueError(message)
        object.__setattr__(self, "energy_j", energy_j)
        object.__setattr__(self, "sigma_m", sigma_m)


@dataclass(frozen=True)
class LoadEffect:
    """What one resolved load did, for its record's outcome."""

    destroyed_cells: int
    destroyed_volume_m3: float
    absorbed_j: float


@dataclass(frozen=True)
class LawInputs:
    """A step's inputs: the heat sources' power per cell (heat resolves sources), and the loads (damage resolves)."""

    power_w: Field | None = None
    loads: tuple[Load, ...] = ()


@dataclass(frozen=True)
class Changes:
    """What a law's step asks of the rest of the tick: world-edit requests for Topology, and per-load effects."""

    requests: tuple[Request, ...] = ()
    effects: tuple[LoadEffect, ...] = ()


class Law(Protocol):
    """A member of the declared law tuple (§5), whatever its cadence."""

    @property
    def name(self) -> str: ...

    @property
    def version(self) -> int: ...

    @property
    def cadence(self) -> Cadence: ...

    @property
    def reads(self) -> tuple[str, ...]: ...

    @property
    def writes(self) -> tuple[str, ...]: ...

    def stable_dt(self, grid: MaterialGrid) -> float:
        """The longest stable step for this law on the grid as it stands, in seconds; infinity if unconditional."""
        ...

    def step(self, grid: MaterialGrid, dt_s: float, inputs: LawInputs) -> Changes:
        """Advance this law by ``dt_s`` (or resolve its inputs, for a per-record law), inside the window."""
        ...
