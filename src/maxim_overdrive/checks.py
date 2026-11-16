"""Turning untrusted values into the finite floats physics needs, or refusing them with a reason.

Data files (rigs, materials, action limits, scenes), imagined specs and SEM actions (an NPC's tool call, an LLM's
output, a client's intent) all reach the world as loosely typed values. Each number becomes a float here or is
refused here, so nothing downstream sees NaN, an infinity, a bool posing as a number, or a string that ``float()``
would quietly accept. ``tests/test_validation.py`` and ``tests/test_act_validation.py`` hold every loader to it.
"""

from __future__ import annotations

import math
import numbers
from collections.abc import Sequence


def finite_real(value: object, what: str) -> float:
    """``value`` as one finite float, or a ValueError that names it. Numpy scalars count; bools and strings don't."""
    f = math.nan
    if not isinstance(value, bool) and isinstance(value, numbers.Real):
        try:
            f = float(value)
        except OverflowError:  # an int too big for a float, such as 10**400 from YAML or JSON
            f = math.nan
    if not math.isfinite(f):
        raise ValueError(f"{what} must be a finite number, got {value!r}")
    return f


def finite_vector(value: object, n: int, what: str) -> tuple[float, ...]:
    """``value`` as ``n`` finite floats, or a ValueError that names the field."""
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence) or len(value) != n:
        raise ValueError(f"{what} must be {n} numbers, got {value!r}")
    try:
        return tuple(finite_real(v, what) for v in value)
    except ValueError:
        raise ValueError(f"{what} must be {n} finite numbers, got {value!r}") from None
