"""The law tuple and its orchestrator (`docs/design/sim_core.md` §5, §5.1, §8): which laws run, in what order, at
what cadence, and Topology applying each law's world edits per batch. Not a law: it imports the laws, and no law
imports it.

The tuple is fixed: ``(damage.loads, heat, damage.thermal)``. Loads resolve per record, right after their record's
stage 2; heat then thermal damage run per substep, each substep's edits applied after the law that asked for them.

`Physics` is one simulation's orchestrator: the tuple, each law's state (its caches, built here at construction), the
stability bound's cache, and the work tally. The orchestrator holds every law's writer token
(`simcore.core.writers.claim`) and runs each law's step narrowed to it, reading only the law's declared ``reads``; a
law never narrows itself, and holds no token to narrow with.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from simcore.core import damage, heat, topology
from simcore.core.exposure import Exposure, Source
from simcore.core.fields import FIELDS, LAW_NAMES
from simcore.core.grid import MaterialGrid, Point
from simcore.core.law import STATELESS, Cadence, Changes, Law, LawInputs, LawState, Load, LoadEffect
from simcore.core.stepping import substep_loop
from simcore.core.work import Work
from simcore.core.writers import WriterToken, claim

DEFAULT_LAWS: tuple[Law, ...] = (damage.LOADS, heat.HEAT, damage.THERMAL)

# The cadences the orchestrator runs today. per_tick and per_physics_step laws join with 5b's body laws and 6.1's
# solid; a tuple holding one is refused rather than silently never run.
_RUN = (Cadence.PER_RECORD, Cadence.PER_SUBSTEP)

_TOKENS = {name: claim(name) for name in LAW_NAMES}
# A token goes to the registered law object itself, never to whatever carries its name (PR 2 delta, SF-1 and D1): an
# impostor named "damage.thermal" gets no token, so it writes nothing. A reordered tuple of the same objects still runs.
_REGISTERED: dict[str, Law] = {law.name: law for law in DEFAULT_LAWS}


def check_laws(laws: Sequence[Law]) -> None:
    """Refuse a law tuple the registry doesn't agree with: a repeated name, a law whose ``writes`` aren't exactly
    the fields the registry declares it a writer of, a bound that reads beyond ``reads``, or a cadence nothing runs
    yet. A programming error, never untrusted input."""
    names = [law.name for law in laws]
    if len(set(names)) != len(names):
        raise ValueError(f"a law tuple names each law once, got {names}")
    for law in laws:
        declared = {f.name for f in FIELDS if law.name in f.writers}
        if set(law.writes) != declared:
            message = f"{law.name} writes {sorted(law.writes)}, but the field registry declares {sorted(declared)}"
            raise ValueError(message)
        if not set(law.bound_reads) <= set(law.reads or ()):
            raise ValueError(f"{law.name}'s bound reads {sorted(law.bound_reads)}, beyond its reads")
        if law.cadence not in _RUN:
            raise ValueError(f"{law.name} runs {law.cadence.value}, a cadence nothing runs yet")


check_laws(DEFAULT_LAWS)


def run_law(grid: MaterialGrid, law: Law, dt_s: float, inputs: LawInputs, *, state: LawState) -> tuple[Changes, int]:
    """One law's one step, as itself, then its world edits applied by Topology as one batch, inside the window.
    Returns its changes and the cells Topology destroyed. Only the registered law object holds its token: anything
    else, a same-named impostor included, runs as no writer and writes nothing."""
    token = _TOKENS[law.name] if _REGISTERED.get(law.name) is law else None
    return _run_with(grid, law, token, dt_s, inputs, state=state)


def _run_as(grid: MaterialGrid, law: Law, dt_s: float, inputs: LawInputs) -> tuple[Changes, int]:
    """Run ``law`` holding the token its name registers: the tests' way to write a law's field the way a law does.
    The ownership scan holds this name to physics.py in ``src/``, so shipped code can't reach it."""
    return _run_with(grid, law, _TOKENS.get(law.name), dt_s, inputs, state=STATELESS)


def _run_with(
    grid: MaterialGrid, law: Law, token: WriterToken | None, dt_s: float, inputs: LawInputs, *, state: LawState
) -> tuple[Changes, int]:
    if law.reads is None:  # only Topology reads anything; a law declares what it reads (PR 2 delta, D1)
        raise ValueError(f"{law.name} declares no reads; a law names the fields it reads")
    with grid.as_writer(token, reads=law.reads):
        changes = law.step(grid, dt_s, inputs, state)
    return changes, topology.apply(grid, changes.requests) if changes.requests else 0  # no requests, no batch


class Physics:
    """One simulation's orchestrator: its law tuple, each law's state, the bound cache and the work tally."""

    def __init__(self, grid: MaterialGrid, laws: Sequence[Law] = DEFAULT_LAWS) -> None:
        check_laws(laws)
        self._grid, self._laws = grid, tuple(laws)
        self._states: dict[str, LawState] = {law.name: law.new_state(grid) for law in self._laws}
        self._bounds: dict[
            str, tuple[tuple[tuple[int, int], ...], float]
        ] = {}  # per law: its bound_reads' versions, the bound
        self.work = Work()

    def group(self, cadence: Cadence) -> tuple[Law, ...]:
        return tuple(law for law in self._laws if law.cadence is cadence)

    def start_tick(self) -> Work:
        """A fresh tally for the tick about to run: the orchestrator and the simulation add to it (§10)."""
        self.work = Work()
        return self.work

    def warm(self, sources: Sequence[Source]) -> None:
        """Bring every cache to the state: each law's state holds what ``sources`` need at the grid's versions, and
        each per-substep law's bound is known (sim_core.md §2, §7). Run at the end of each tick that opened a window,
        where its builds count in the tick's work, and at rest after construction and after a rollback, where they
        count in no tick: so a run, a retried tick and a replay from a loaded state count the same work."""
        for law in self._laws:
            with self._grid.reading(reads=law.reads):
                self._states[law.name].warm(self._grid, sources)
        self.bound(self.group(Cadence.PER_SUBSTEP))

    def resolve_loads(self, loads: Sequence[Load]) -> tuple[LoadEffect, ...]:
        """Resolve one record's loads, inside the window: the per-record laws in tuple order, each one's world edits
        applied by Topology as one batch. Returns each load's effect, in the order the loads came."""
        effects: list[LoadEffect] = []
        inputs = LawInputs(loads=tuple(loads))
        for law in self.group(Cadence.PER_RECORD):
            changes, destroyed = run_law(self._grid, law, 0.0, inputs, state=self._states[law.name])
            predicted = sum(e.destroyed_cells for e in changes.effects)
            if destroyed != predicted:  # the effects report what Topology did, so the two counts are one fact
                raise RuntimeError(
                    f"{law.name} reported {predicted} destroyed cells, but Topology destroyed {destroyed}"
                )
            effects.extend(changes.effects)
        return tuple(effects)

    def bound(self, group: Sequence[Law]) -> float:
        """The tightest stable step of ``group`` now, each law's bound cached on its ``bound_reads``' versions."""
        return min((self._law_bound(law) for law in group), default=math.inf)

    def _law_bound(self, law: Law) -> float:
        key = tuple(self._grid.field_version(name) for name in law.bound_reads)
        cached = self._bounds.get(law.name)
        if cached is not None and cached[0] == key:
            return cached[1]
        with self._grid.reading(reads=law.bound_reads):  # a bound that reads more would be served stale
            value = law.stable_dt(self._grid, self._states[law.name])
        self._bounds[law.name] = (key, value)
        self.work.stable_dt_evaluations += 1
        return value

    def run(self, seconds: float, *, refine: int, exposure: Exposure) -> int:
        """Advance the per-substep laws by ``seconds`` as one fixed physics step (sim_core.md §8; ``refine`` is
        ``SimConfig.substep_refine``), inside the window. Returns the substeps taken. It moves no clock.

        Each law's ``prepare`` runs on the first substep and after one whose batches edited the world (a destroyed
        cell is air, and a fire heats solids), when the stability bound is rechecked too (§5)."""
        if seconds <= 0:
            return 0
        group = self.group(Cadence.PER_SUBSTEP)
        inputs: dict[str, LawInputs] = {}

        def once(dt: float, refresh: bool) -> bool:
            if refresh:
                inputs.update({law.name: self._prepare(law, exposure) for law in group})
            before = self._grid.topology_version
            for law in group:
                run_law(self._grid, law, dt, inputs[law.name], state=self._states[law.name])
            return self._grid.topology_version != before  # an edit moves the bound and where sources deposit

        taken = substep_loop(seconds, refine, lambda: self.bound(group), once)
        self._count(group, taken)
        return taken

    def _prepare(self, law: Law, exposure: Exposure) -> LawInputs:
        with self._grid.reading(reads=law.reads):
            prepared = law.prepare(self._grid, self._states[law.name], exposure)
        self.work.power_field_builds += prepared.power_w is not None
        return prepared

    def _count(self, group: Sequence[Law], taken: int) -> None:
        self.work.physics_steps += 1
        for law in group:
            self.work.substeps[law.name] += taken
            self.work.cell_substeps[law.name] += taken * math.prod(self._grid.shape)

    def builds(self) -> dict[str, int]:
        """Every law cache's builds so far, as ``law/cache`` (§10): the tally reads the change over a tick."""
        return {f"{name}/{cache}": n for name, state in self._states.items() for cache, n in state.builds().items()}


def strike(grid: MaterialGrid, point_m: Point, energy_j: float, sigma_m: float) -> LoadEffect:
    """One strike resolved as a record's only load, inside the window, by a fresh orchestrator: the tests' way to
    strike a bare grid. Shipped strikes go through `Simulation.step`."""
    (effect,) = Physics(grid).resolve_loads((Load("strike", point_m, energy_j, sigma_m),))
    return effect
