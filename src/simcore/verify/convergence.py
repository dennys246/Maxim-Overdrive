"""Observed order of accuracy, with space and time refined separately (world_model E2).

A study refines one thing: the grid spacing at a fixed step (space), or the step at a fixed spacing (time). Mixing
the two lets their errors cancel, which is how heat's old order test showed an order of 3.2 its scheme can't reach.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from simcore.verify.runs import Run, Work

Observable = Callable[[Run], tuple[float, Work]]
_SAME = 1e-9  # relative: two floats this close are the same step, spacing, time or ratio


@dataclass(frozen=True)
class Convergence:
    """What ``converges`` measured, coarse to fine."""

    runs: tuple[Run, ...]
    values: tuple[float, ...]
    errors: tuple[float, ...]
    orders: tuple[float, ...]
    reference_converged: bool
    work: tuple[Work, ...]


def converges(
    observable: Observable, runs: Sequence[Run], *, exact: float | None = None, order_tol: float | None = None
) -> Convergence:
    """Measure ``observable`` over ``runs``, coarse to fine, and the observed order between them.

    With ``exact`` (a closed form), errors are against it and each order is ln(e_coarse / e_fine) / ln(r). Without
    it, the orders come from successive differences (Richardson: ln(|v1 - v2| / |v2 - v3|) / ln(r), which needs a
    constant ratio), errors are against the finest run, and ``reference_converged`` says whether the last two orders
    agree within ``order_tol``, which such a study must give.
    """
    runs = tuple(runs)
    ratios = _ratios(runs)
    measured = [observable(run) for run in runs]
    values = tuple(float(value) for value, _ in measured)
    work = tuple(w for _, w in measured)
    if exact is not None:
        errors = tuple(abs(v - exact) for v in values)
        orders = tuple(_order(errors[i], errors[i + 1], ratios[i]) for i in range(len(ratios)))
        return Convergence(runs, values, errors, orders, True, work)
    return _against_reference(runs, values, work, ratios, order_tol)


def _against_reference(
    runs: tuple[Run, ...],
    values: tuple[float, ...],
    work: tuple[Work, ...],
    ratios: list[float],
    order_tol: float | None,
) -> Convergence:
    if order_tol is None or not (math.isfinite(order_tol) and order_tol > 0):
        raise ValueError(f"a study without a closed form needs a positive order_tol, got {order_tol!r}")
    if len(runs) < 3:
        raise ValueError(f"a study without a closed form needs at least three runs, got {len(runs)}")
    if any(not _close(r, ratios[0]) for r in ratios):
        raise ValueError(f"Richardson orders need one refinement ratio, got {ratios}")
    diffs = [abs(values[i] - values[i + 1]) for i in range(len(values) - 1)]
    orders = tuple(_order(diffs[i], diffs[i + 1], ratios[0]) for i in range(len(diffs) - 1))
    errors = tuple(abs(v - values[-1]) for v in values)
    settled = len(orders) >= 2 and abs(orders[-1] - orders[-2]) <= order_tol
    return Convergence(runs, values, errors, orders, settled, work)


def _ratios(runs: tuple[Run, ...]) -> list[float]:
    """The refinement ratio between each consecutive pair, after checking the runs form one study."""
    if len(runs) < 2:
        raise ValueError(f"a convergence study needs at least two runs, got {len(runs)}")
    if any(not _close(run.seconds, runs[0].seconds) for run in runs):
        raise ValueError("every run in a study must cover the same simulated time")
    same_dt = all(_close(run.dt_s, runs[0].dt_s) for run in runs)
    same_dx = all(_close(run.dx_m, runs[0].dx_m) for run in runs)
    if same_dt == same_dx:
        raise ValueError("a study refines space at a fixed step or time at a fixed spacing, not both or neither")
    sizes = [run.dx_m if same_dt else run.dt_s for run in runs]
    ratios = [sizes[i] / sizes[i + 1] for i in range(len(sizes) - 1)]
    if any(r <= 1 + _SAME for r in ratios):
        raise ValueError(f"runs must go from coarse to fine, got ratios {ratios}")
    return ratios


def _order(coarse: float, fine: float, ratio: float) -> float:
    """ln(coarse / fine) / ln(ratio); an exact fine answer is infinitely accurate, an exact coarse one is not."""
    if fine == 0:
        return math.inf if coarse > 0 else math.nan
    if coarse == 0:
        return -math.inf
    return math.log(coarse / fine) / math.log(ratio)


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= _SAME * max(abs(a), abs(b))
