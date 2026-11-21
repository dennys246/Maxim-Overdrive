"""The splitting test at a fixed spacing: refining time never changes the outcome class (physics spike, splitting §6.4).

The reversed-order half needs step 5a's law list, so it lands there.
"""

from __future__ import annotations

from collections.abc import Callable, Hashable, Sequence

from simcore.verify.runs import Run


def same_class_under_refinement(outcome: Callable[[Run], Hashable], run: Run, factors: Sequence[int] = (1, 10)) -> bool:
    """Whether ``outcome`` gives one class at ``run`` refined in time by each of ``factors``."""
    if not factors or any(isinstance(f, bool) or not isinstance(f, int) or f < 1 for f in factors):
        raise ValueError(f"factors must be whole numbers of at least 1, got {factors!r}")
    classes = {outcome(run.refined_in_time(f)) for f in factors}
    return len(classes) == 1
