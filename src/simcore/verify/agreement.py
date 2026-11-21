"""The verification rule (world_model §1.1): outcomes agree across grids, and converge from the coarse grid.

A scenario's outcome (an onset turn, an integrity) is not smooth in the spacing, so it gets no order of accuracy. What
it gets is agreement: how far apart the grids land, how far each is from the finest (the reference), and whether the
coarse grid's error is no smaller than the truth grid's. A test keeps its own tolerance on the spread, because "each
grid within tol of the reference" would let two grids sit 2 * tol apart (CLAUDE.md: no band loosens).
"""

from __future__ import annotations

import itertools
from collections.abc import Callable, Hashable, Sequence
from dataclasses import dataclass

from simcore.verify.runs import Run


@dataclass(frozen=True)
class Agreement:
    """One outcome across grids, coarse to fine. ``converging`` is None with fewer than three grids."""

    runs: tuple[Run, ...]
    values: tuple[float, ...]
    errors: tuple[float, ...]
    spread: float
    converging: bool | None


def agrees(observable: Callable[[Run], float], runs: Sequence[Run]) -> Agreement:
    """Measure ``observable`` at each grid of a space study (one step, spacings coarse to fine).

    ``errors`` are against the finest run. ``converging`` holds when each grid's error is no smaller than the next
    finer grid's, the rule's "converges from the coarse grid"; with two grids there is no truth between them to judge.
    """
    runs = tuple(runs)
    _check_space_study(runs)
    values = tuple(float(observable(run)) for run in runs)
    errors = tuple(abs(v - values[-1]) for v in values)
    converging = None if len(runs) < 3 else all(errors[i] >= errors[i + 1] for i in range(len(errors) - 2))
    return Agreement(runs, values, errors, max(values) - min(values), converging)


def same_class(outcome: Callable[[Run], Hashable], runs: Sequence[Run]) -> bool:
    """Whether ``outcome`` gives one class at every grid of a space study (the resolution rule's outcome class)."""
    runs = tuple(runs)
    _check_space_study(runs)
    return len({outcome(run) for run in runs}) == 1


def _check_space_study(runs: tuple[Run, ...]) -> None:
    if len(runs) < 2:
        raise ValueError(f"agreement needs at least two grids, got {len(runs)}")
    if any(run.dt_s != runs[0].dt_s or run.steps != runs[0].steps for run in runs):
        raise ValueError("an agreement study holds the step and the step count, and changes only the spacing")
    if any(b.dx_m >= a.dx_m for a, b in itertools.pairwise(runs)):
        raise ValueError("grids must go from coarse to fine")
