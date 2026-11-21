"""Where a binary outcome flips, per grid (CLAUDE.md: binary outcomes keep a band near their threshold).

A test asserts that its operating point clears the band by its margin (``tile_and_client.md`` §6.3 item 7).
"""

from __future__ import annotations

import itertools
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from simcore.verify.runs import Run

Outcome = Callable[[Run, float], bool]


@dataclass(frozen=True)
class Band:
    """Each run's flip point (the first control value where the outcome holds), and their range."""

    edges: tuple[float, ...]
    low: float
    high: float


def band_gate(outcome: Outcome, xs: Sequence[float], runs: Sequence[Run]) -> Band:
    """Find each run's flip point over the ascending control values ``xs``.

    Every value is evaluated, not bisected: near a threshold on a coarse grid an outcome can flip more than once
    (true, false, true), and bisection would land on one edge and hide the others. The outcome must be false at
    ``xs[0]``, true at ``xs[-1]``, and flip exactly once between; anything else raises ``ValueError``, because a band
    that wasn't found, or isn't one band, can't be gated.
    """
    xs = tuple(float(x) for x in xs)
    if len(xs) < 2 or any(b <= a for a, b in itertools.pairwise(xs)):
        raise ValueError(f"xs must hold at least two strictly ascending values, got {xs}")
    if not runs:
        raise ValueError("a band needs at least one run")
    edges = tuple(_flip(outcome, xs, run) for run in runs)
    return Band(edges, min(edges), max(edges))


def _flip(outcome: Outcome, xs: tuple[float, ...], run: Run) -> float:
    held = [bool(outcome(run, x)) for x in xs]
    if held[0] or not held[-1]:
        raise ValueError(f"the outcome isn't bracketed by {xs[0]} (false) and {xs[-1]} (true) at {run}")
    first = held.index(True)
    if not all(held[first:]):
        raise ValueError(f"the outcome flips more than once over {xs} at {run}: {held}")
    return xs[first]
