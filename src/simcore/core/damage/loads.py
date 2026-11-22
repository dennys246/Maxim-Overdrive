"""``damage.loads``, the per-record law (sim_core.md §5.1): it resolves every mechanical load a record put in, in the
order they came, through the resolver its kind declares, applies the integrity each returns, and asks Topology to
destroy what broke. Every load kind resolves here, and nowhere else."""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

from simcore.core.damage.strike import loss as strike_loss
from simcore.core.exposure import Exposure
from simcore.core.geometry import Field, Mask
from simcore.core.grid import MaterialGrid
from simcore.core.law import STATELESS, Cadence, Changes, LawInputs, LawState, Load, LoadEffect
from simcore.core.topology import Destroy, Request

Resolver = Callable[[MaterialGrid, Load], tuple[Field, Field]]  # (energy per cell in J, integrity lost per cell)

# The declared resolvers, one per load kind (§5.1). A new kind (ballistic, chemical) is a module and a row here.
RESOLVERS: tuple[tuple[str, Resolver], ...] = (("strike", strike_loss),)
_BY_KIND = dict(RESOLVERS)


@dataclass(frozen=True)
class LoadsLaw:
    """Damage's per-record resolver: it writes integrity and asks Topology to destroy what broke."""

    name: str = "damage.loads"
    version: int = 1
    cadence: Cadence = Cadence.PER_RECORD
    reads: tuple[str, ...] = ("material", "integrity")
    writes: tuple[str, ...] = ("integrity",)
    bound_reads: tuple[str, ...] = ()  # unconditionally stable

    def new_state(self, grid: MaterialGrid) -> LawState:
        return STATELESS

    def prepare(self, grid: MaterialGrid, state: LawState, exposure: Exposure) -> LawInputs:
        return LawInputs()

    def stable_dt(self, grid: MaterialGrid, state: LawState) -> float:
        return math.inf

    def step(self, grid: MaterialGrid, dt_s: float, inputs: LawInputs, state: LawState) -> Changes:
        requests: list[Request] = []
        effects: list[LoadEffect] = []
        slated: Mask | None = None  # broken by an earlier load of this batch: counted once
        for load in inputs.loads:
            resolve = _BY_KIND.get(load.kind)
            if resolve is None:
                raise ValueError(f"damage resolves no {load.kind!r} load yet")  # a programming error
            cell_energy, loss = resolve(grid, load)
            solid = grid.solid
            integrity = grid.integrity  # the block's writable array (an attribute can't be assigned: §4.1)
            integrity -= loss.astype(integrity.dtype)
            gone = solid & (grid.integrity <= 0.0)
            if slated is not None:
                gone &= ~slated
            slated = gone if slated is None else slated | gone
            n = int(gone.sum())  # Topology destroys exactly these: every one is solid now
            requests.append(Destroy(gone))
            effects.append(LoadEffect(n, n * grid.cell_volume_m3, float(cell_energy[solid].sum())))
        return Changes(tuple(requests), tuple(effects))


LOADS = LoadsLaw()
