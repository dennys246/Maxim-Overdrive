"""The substep loop: how one interval is cut into stable explicit substeps (`docs/design/sim_core.md` §8).

The physics orchestrator runs every per-substep law in the tuple through it (`simcore.core.physics.run_physics`; heat
alone is the one-law tuple), so there is one loop. Not a law: laws don't import each other, and this is no law.
"""

from __future__ import annotations

import math
from collections.abc import Callable


def substep_loop(
    seconds: float, refine: int, bound: Callable[[], float], step_once: Callable[[float, bool], bool]
) -> int:
    """Run ``step_once(dt, refresh)`` over ``seconds`` (positive) as the fixed physics step; returns the substeps taken.

    The rule is sim_core.md §8's: ``n = refine * max(1, ceil(seconds / bound()))``, ``dt = seconds / n``. ``refine``
    (``SimConfig.substep_refine``, 1 in shipped play) refines time on the shipped path; there is no floor beyond it.
    ``bound()`` is the longest stable substep now. ``refresh`` is True on the first substep and after one that
    changed the cells (``step_once`` returned True), which is when sources must be recomputed and the bound rechecked.

    Count substeps; never compare a running float sum with an absolute epsilon. A replan computes what remains from
    counts, ``(planned - taken) * dt`` (§8), not from ``seconds - elapsed``: the sum of n steps of seconds / n misses
    seconds by rounding that grows with n, and an end test on it once took one extra sliver of a substep.
    """
    if refine < 1:
        raise ValueError(f"refine must be at least 1, got {refine!r}")
    n = refine * max(1, math.ceil(seconds / bound()))
    dt = seconds / n
    planned, taken, changed = n, 0, False
    while taken < planned:
        if changed:
            limit = bound()
            # Destruction tightened stability past the step refine divides: split the rest evenly at the new bound,
            # refined, so a refined run stays a refinement of a stable step (PR 3 review N3; refine 1 is unchanged).
            if limit < dt * refine:
                remaining = (planned - taken) * dt
                more = refine * math.ceil(remaining / limit)
                dt = remaining / more  # not dt = limit: a remainder of a whole number of bounds would leave a 0 s step
                planned = taken + more
        changed = step_once(dt, taken == 0 or changed)
        taken += 1
    return taken
