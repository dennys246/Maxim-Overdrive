"""The substep loop: how one interval is cut into stable explicit substeps (`docs/design/sim_core.md` §8).

Shared by `heat.step` (heat alone, for its closed-form and convergence studies) and the physics orchestrator (every
per-substep law in the tuple), so there is one loop. Not a law: laws don't import each other, and this is no law.
"""

from __future__ import annotations

import math
from collections.abc import Callable


def substep_loop(
    seconds: float, min_substeps: int, bound: Callable[[], float], step_once: Callable[[float, bool], bool]
) -> int:
    """Run ``step_once(dt, refresh)`` over ``seconds`` (positive); returns the substeps taken.

    ``bound()`` is the longest stable substep now. ``refresh`` is True on the first substep and after one that
    changed the cells (``step_once`` returned True), which is when sources must be recomputed and the bound rechecked.

    Count substeps; never compare a running float sum with an absolute epsilon. The sum of n steps of seconds / n
    misses seconds by rounding that grows with n (about 1e-9 s at 8,000 steps of 0.45 s), and an end test of
    elapsed < seconds - 1e-12 took one extra sliver of a substep (step 4's space study found it).
    """
    n = max(min_substeps, math.ceil(seconds / bound()))
    dt = seconds / n
    planned, taken, elapsed, changed = n, 0, 0.0, False
    while taken < planned:
        if changed:
            limit = bound()
            if limit < dt:  # destruction tightened stability: split the rest evenly at the new bound, to rounding
                remaining = seconds - elapsed
                more = math.ceil(remaining / limit)
                dt = remaining / more  # not dt = limit: a remainder of a whole number of bounds would leave a 0 s step
                planned = taken + more
        dt = min(dt, seconds - elapsed)
        changed = step_once(dt, taken == 0 or changed)
        elapsed += dt
        taken += 1
    return taken
