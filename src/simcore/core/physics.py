"""The law tuple and its orchestrator (`docs/design/sim_core.md` §5, §5.1): which laws run, in what order, at what
cadence, and Topology applying each law's world edits per batch. Not a law: it imports the laws, and no law imports it.

The tuple is fixed: ``(damage.loads, heat, damage.thermal)``. Loads resolve per record, right after their record's
stage 2; heat then thermal damage run per substep, each substep's edits applied after the law that asked for them.
That is the order heat and damage ran in before the tuple (damage was heat's ``on_substep`` callback), so every
result is bit-identical to theirs.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from simcore.core import damage, heat, topology
from simcore.core.fields import writers_of
from simcore.core.grid import Field, MaterialGrid, Point
from simcore.core.law import Cadence, Law, LawInputs, Load, LoadEffect
from simcore.core.stepping import substep_loop

DEFAULT_LAWS: tuple[Law, ...] = (damage.LOADS, heat.HEAT, damage.THERMAL)

# The cadences the orchestrator runs today. per_tick and per_physics_step laws join with step 5a's PR 3 and later
# (the fixed physics step); a tuple holding one is refused rather than silently never run.
_RUN = (Cadence.PER_RECORD, Cadence.PER_SUBSTEP)


def check_laws(laws: Sequence[Law]) -> None:
    """Refuse a law tuple the registry doesn't agree with: a repeated name, a write the registry doesn't declare for
    the law, or a cadence nothing runs yet. A programming error, never untrusted input."""
    names = [law.name for law in laws]
    if len(set(names)) != len(names):
        raise ValueError(f"a law tuple names each law once, got {names}")
    for law in laws:
        undeclared = [f for f in law.writes if law.name not in writers_of(f)]
        if undeclared:
            raise ValueError(f"{law.name} writes {undeclared}, which the field registry doesn't declare for it")
        if law.cadence not in _RUN:
            raise ValueError(f"{law.name} runs {law.cadence.value}, a cadence nothing runs yet")


def _group(laws: Sequence[Law], cadence: Cadence) -> tuple[Law, ...]:
    check_laws(laws)
    return tuple(law for law in laws if law.cadence is cadence)


def resolve_loads(
    grid: MaterialGrid, loads: Sequence[Load], laws: Sequence[Law] = DEFAULT_LAWS
) -> tuple[LoadEffect, ...]:
    """Resolve one record's loads, inside the window: the per-record laws in tuple order, each one's world edits
    applied by Topology as one batch. Returns each load's effect, in the order the loads came."""
    effects: list[LoadEffect] = []
    inputs = LawInputs(loads=tuple(loads))
    for law in _group(laws, Cadence.PER_RECORD):
        changes = law.step(grid, 0.0, inputs)
        topology.apply(grid, changes.requests)
        effects.extend(changes.effects)
    return tuple(effects)


def run_physics(
    grid: MaterialGrid,
    seconds: float,
    *,
    min_substeps: int,
    power: Callable[[], Field | None],
    laws: Sequence[Law] = DEFAULT_LAWS,
) -> int:
    """Advance the per-substep laws by ``seconds``, inside the window. Returns the substeps taken.

    ``power()`` is the sources' power per cell, recomputed on the first substep and after one whose batches edited
    the world (a destroyed cell is air, and a fire heats solids), when the stability bound, the tuple's tightest, is
    rechecked too. Before the tuple, the trigger was "damage destroyed a cell", the only edit a substep makes today."""
    if seconds <= 0:
        return 0
    group = _group(laws, Cadence.PER_SUBSTEP)
    inputs = LawInputs()

    def bound() -> float:
        return min(law.stable_dt(grid) for law in group)

    def once(dt: float, refresh: bool) -> bool:
        nonlocal inputs
        if refresh:
            inputs = LawInputs(power_w=power())
        before = grid.topology_version
        for law in group:
            topology.apply(grid, law.step(grid, dt, inputs).requests)
        return grid.topology_version != before  # an edit moves the stability bound and where sources deposit

    taken = substep_loop(seconds, min_substeps, bound, once)
    grid.time_s += seconds
    return taken


def strike(grid: MaterialGrid, point_m: Point, energy_j: float, sigma_m: float) -> LoadEffect:
    """One strike resolved as a record's only load, inside the window: what the applier does for a strike action."""
    (effect,) = resolve_loads(grid, (Load("strike", point_m, energy_j, sigma_m),))
    return effect
