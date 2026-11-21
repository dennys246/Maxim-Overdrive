"""The verification rule (world_model §1.1): outcomes agree across grids, and converge from the coarse grid.

A scenario's outcome (an onset turn, an integrity) is not smooth in the spacing, so it gets no order of accuracy. What
it gets is agreement: how far apart the grids land, how far each is from the finest (the reference), and whether the
coarse grid's error is no smaller than the truth grid's. A test keeps its own tolerance on the spread, because "each
grid within tol of the reference" would let two grids sit 2 * tol apart (CLAUDE.md: no band loosens).

An agreement study is indexed by spacing alone. Its physics step is whatever the scenario takes at that spacing: until
step 5a's fixed physics step, ``World`` substeps at a floor that scales as 1 / dx**2, so these studies refine space and
time together, unlike ``converges``'s, which hold one of them fixed (E2). No ``Run`` is built for them, because a step
the study doesn't control would be a label, not a measurement.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Callable, Hashable, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Agreement:
    """One outcome across grids, coarse to fine. ``converging`` is None with fewer than three grids."""

    spacings: tuple[float, ...]
    values: tuple[float, ...]
    errors: tuple[float, ...]
    spread: float
    converging: bool | None


def agrees(observable: Callable[[float], float], spacings: Sequence[float], *, quantum: float = 0.0) -> Agreement:
    """Measure ``observable(dx_m)`` at each spacing, coarse to fine.

    ``errors`` are against the finest spacing. ``converging`` holds when each grid's error is no smaller than the next
    finer grid's, give or take ``quantum``, the outcome's resolution (a whole turn for an onset turn): within one
    quantum, two errors can't be told apart. With two grids there is no truth between them to judge.
    """
    spacings = _coarse_to_fine(spacings)
    if not (math.isfinite(quantum) and quantum >= 0):
        raise ValueError(f"quantum must be finite and non-negative, got {quantum!r}")
    values = tuple(float(observable(dx_m)) for dx_m in spacings)
    errors = tuple(abs(v - values[-1]) for v in values)
    converging = (
        None if len(spacings) < 3 else all(errors[i] + quantum >= errors[i + 1] for i in range(len(errors) - 2))
    )
    return Agreement(spacings, values, errors, max(values) - min(values), converging)


def same_class(outcome: Callable[[float], Hashable], spacings: Sequence[float]) -> bool:
    """Whether ``outcome(dx_m)`` gives one class at every spacing (the rule's "never the outcome class")."""
    return len({outcome(dx_m) for dx_m in _coarse_to_fine(spacings)}) == 1


def _coarse_to_fine(spacings: Sequence[float]) -> tuple[float, ...]:
    spacings = tuple(float(dx) for dx in spacings)
    if len(spacings) < 2:
        raise ValueError(f"agreement needs at least two grids, got {len(spacings)}")
    if any(not (math.isfinite(dx) and dx > 0) for dx in spacings):
        raise ValueError(f"spacings must be finite and positive, got {spacings}")
    if any(b >= a for a, b in itertools.pairwise(spacings)):
        raise ValueError(f"spacings must go from coarse to fine, got {spacings}")
    return spacings
