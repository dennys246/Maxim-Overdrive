"""The work counters (`docs/design/sim_core.md` §10): exact integers counting what a tick did, never wall time.

`Work` is the tally the orchestrator and the simulation add to while a tick runs; `WorkCounters` is its frozen
reading, one per `TickReport`. Because every cache and member digest is built eagerly (§2), a replay counts exactly
what the live run counted, so tests hold the counters to exact values, and B5's budgets read them.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass

Counts = tuple[tuple[str, int], ...]  # sorted by name, so equal work compares equal however it was tallied


def _sorted(counts: Mapping[str, int]) -> Counts:
    return tuple(sorted((name, n) for name, n in counts.items() if n))


@dataclass(frozen=True)
class WorkCounters:
    """One tick's work (§10). Per-law and per-cache counts are sorted ``(name, count)`` pairs, zero counts left out."""

    physics_steps: int = 0
    substeps: Counts = ()  # per law
    cell_substeps: Counts = ()  # per law: the cells its kernel iterates, times its substeps
    stable_dt_evaluations: int = 0
    windows_opened: int = 0  # cell windows
    cells_copied: int = 0  # field values the tick's window copied: at open, views, revocations and commit
    frames_published: int = 0
    power_field_builds: int = 0
    rebuilds: Counts = ()  # per cache


class Work:
    """The running tally for one tick. Only the simulation and its orchestrator add to it."""

    def __init__(self) -> None:
        self.physics_steps = 0
        self.substeps: Counter[str] = Counter()
        self.cell_substeps: Counter[str] = Counter()
        self.stable_dt_evaluations = 0
        self.windows_opened = 0
        self.cells_copied = 0
        self.frames_published = 0
        self.power_field_builds = 0
        self.rebuilds: Counter[str] = Counter()

    def reading(self) -> WorkCounters:
        return WorkCounters(
            self.physics_steps,
            _sorted(self.substeps),
            _sorted(self.cell_substeps),
            self.stable_dt_evaluations,
            self.windows_opened,
            self.cells_copied,
            self.frames_published,
            self.power_field_builds,
            _sorted(self.rebuilds),
        )
