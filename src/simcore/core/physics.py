"""The law tuple and its orchestrator (`docs/design/sim_core.md` §5, §5.1): which laws run, in what order, at what
cadence, and Topology applying each law's world edits per batch. Not a law: it imports the laws, and no law imports it.

The tuple is fixed: ``(damage.loads, heat, damage.thermal)``. Loads resolve per record, right after their record's
stage 2; heat then thermal damage run per substep, each substep's edits applied after the law that asked for them.
That is the order heat and damage ran in before the tuple (damage was heat's ``on_substep`` callback), so every
result is bit-identical to theirs.

The orchestrator holds every law's writer token (`simcore.core.writers.claim`) and runs each law's step narrowed to
it, reading only the law's declared ``reads``; a law never narrows itself, and holds no token to narrow with.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from simcore.core import damage, heat, topology
from simcore.core.fields import FIELDS, LAW_NAMES
from simcore.core.grid import Field, MaterialGrid, Point
from simcore.core.law import Cadence, Changes, Law, LawInputs, Load, LoadEffect
from simcore.core.stepping import substep_loop
from simcore.core.writers import WriterToken, claim

DEFAULT_LAWS: tuple[Law, ...] = (damage.LOADS, heat.HEAT, damage.THERMAL)

# The cadences the orchestrator runs today. per_tick and per_physics_step laws join with step 5a's PR 4 and later
# (with heat's prepare); a tuple holding one is refused rather than silently never run.
_RUN = (Cadence.PER_RECORD, Cadence.PER_SUBSTEP)

_TOKENS = {name: claim(name) for name in LAW_NAMES}
# A token goes to the registered law object itself, never to whatever carries its name (PR 2 delta, SF-1 and D1): an
# impostor named "damage.thermal" gets no token, so it writes nothing. A reordered tuple of the same objects still runs.
_REGISTERED: dict[str, Law] = {law.name: law for law in DEFAULT_LAWS}


def check_laws(laws: Sequence[Law]) -> None:
    """Refuse a law tuple the registry doesn't agree with: a repeated name, a law whose ``writes`` aren't exactly
    the fields the registry declares it a writer of, or a cadence nothing runs yet. A programming error, never
    untrusted input."""
    names = [law.name for law in laws]
    if len(set(names)) != len(names):
        raise ValueError(f"a law tuple names each law once, got {names}")
    for law in laws:
        declared = {f.name for f in FIELDS if law.name in f.writers}
        if set(law.writes) != declared:
            message = f"{law.name} writes {sorted(law.writes)}, but the field registry declares {sorted(declared)}"
            raise ValueError(message)
        if law.cadence not in _RUN:
            raise ValueError(f"{law.name} runs {law.cadence.value}, a cadence nothing runs yet")


check_laws(DEFAULT_LAWS)


def _group(laws: Sequence[Law], cadence: Cadence) -> tuple[Law, ...]:
    check_laws(laws)  # every tuple alike, the default too: no identity special case (PR 3 review, Architecture N5)
    return tuple(law for law in laws if law.cadence is cadence)


def run_law(grid: MaterialGrid, law: Law, dt_s: float, inputs: LawInputs) -> tuple[Changes, int]:
    """One law's one step, as itself, then its world edits applied by Topology as one batch, inside the window.
    Returns its changes and the cells Topology destroyed. Only the registered law object holds its token: anything
    else, a same-named impostor included, runs as no writer and writes nothing."""
    token = _TOKENS[law.name] if _REGISTERED.get(law.name) is law else None
    return _run_with(grid, law, token, dt_s, inputs)


def _run_as(grid: MaterialGrid, law: Law, dt_s: float, inputs: LawInputs) -> tuple[Changes, int]:
    """Run ``law`` holding the token its name registers: the tests' way to write a law's field the way a law does.
    The ownership scan holds this name to physics.py in ``src/``, so shipped code can't reach it."""
    return _run_with(grid, law, _TOKENS.get(law.name), dt_s, inputs)


def _run_with(
    grid: MaterialGrid, law: Law, token: WriterToken | None, dt_s: float, inputs: LawInputs
) -> tuple[Changes, int]:
    if law.reads is None:  # only Topology reads anything; a law declares what it reads (PR 2 delta, D1)
        raise ValueError(f"{law.name} declares no reads; a law names the fields it reads")
    with grid.as_writer(token, reads=law.reads):
        changes = law.step(grid, dt_s, inputs)
    return changes, topology.apply(grid, changes.requests) if changes.requests else 0  # no requests, no batch


def resolve_loads(
    grid: MaterialGrid, loads: Sequence[Load], laws: Sequence[Law] = DEFAULT_LAWS
) -> tuple[LoadEffect, ...]:
    """Resolve one record's loads, inside the window: the per-record laws in tuple order, each one's world edits
    applied by Topology as one batch. Returns each load's effect, in the order the loads came."""
    effects: list[LoadEffect] = []
    inputs = LawInputs(loads=tuple(loads))
    for law in _group(laws, Cadence.PER_RECORD):
        changes, destroyed = run_law(grid, law, 0.0, inputs)
        predicted = sum(e.destroyed_cells for e in changes.effects)
        if destroyed != predicted:  # the effects report what Topology did, so the two counts are one fact
            raise RuntimeError(f"{law.name} reported {predicted} destroyed cells, but Topology destroyed {destroyed}")
        effects.extend(changes.effects)
    return tuple(effects)


def run_physics(
    grid: MaterialGrid,
    seconds: float,
    *,
    refine: int,
    power: Callable[[], Field | None],
    laws: Sequence[Law] = DEFAULT_LAWS,
) -> int:
    """Advance the per-substep laws by ``seconds`` as one fixed physics step (sim_core.md §8; ``refine`` is
    ``SimConfig.substep_refine``), inside the window. Returns the substeps taken. It moves no clock: the caller
    that owns the interval moves time, in whole microseconds (sim_core.md §3).

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
            run_law(grid, law, dt, inputs)
        return grid.topology_version != before  # an edit moves the stability bound and where sources deposit

    return substep_loop(seconds, refine, bound, once)


def strike(grid: MaterialGrid, point_m: Point, energy_j: float, sigma_m: float) -> LoadEffect:
    """One strike resolved as a record's only load, inside the window: what the applier does for a strike action."""
    (effect,) = resolve_loads(grid, (Load("strike", point_m, energy_j, sigma_m),))
    return effect
