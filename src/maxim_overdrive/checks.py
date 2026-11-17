"""Turning untrusted values into the finite floats physics needs, or refusing them with a reason.

Data files (rigs, materials, action limits, scenes), imagined specs and SEM actions (an NPC's tool call, an LLM's
output, a client's intent) all reach the world as loosely typed values. Each number becomes a float here or is
refused here, so nothing downstream sees NaN, an infinity, a bool posing as a number, or a string that ``float()``
would quietly accept. Each mapping is held to the keys its reader knows (``known_keys``), so a misspelt key is
refused rather than silently ignored. ``tests/test_validation.py`` and ``tests/test_act_validation.py`` hold every
loader to it.
"""

from __future__ import annotations

import math
import numbers
from collections.abc import Collection, Mapping, Sequence


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


def whole_number(value: object, what: str) -> int:
    """``value`` as an int, or a ValueError that names it. Only integers count: not bools, floats such as 2.9 (which
    ``int()`` would quietly truncate to 2) or numeric strings."""
    if isinstance(value, bool) or not isinstance(value, numbers.Integral):
        raise ValueError(f"{what} must be a whole number, got {value!r}")
    return int(value)


def known_keys(
    raw: object, what: str, *, required: Collection[str], optional: Collection[str] = ()
) -> Mapping[str, object]:
    """``raw`` as a mapping that has every ``required`` key and no key outside ``required`` and ``optional``, or a
    ValueError that names the keys at fault.

    A closed schema, held from both sides: a key the reader doesn't know is refused, never ignored, so a typo such as
    ``degrade_above`` for ``degrade_above_c`` can't silently change what the world does; and a missing key is named,
    never left to surface as a bare KeyError. A key that isn't a string is unknown (nothing is hashed that might not
    be hashable). A new field is added to its reader's sets and to the format's version, not slipped in.
    """
    if not isinstance(raw, Mapping):
        raise ValueError(f"{what} must be a mapping, got {type(raw).__name__}")
    keys = list(raw)
    names = {k for k in keys if isinstance(k, str)}
    unknown = sorted(str(k) for k in keys if not isinstance(k, str) or (k not in required and k not in optional))
    if unknown:
        raise ValueError(f"{what}: unknown key(s) {unknown}; it takes {sorted({*required, *optional})}")
    missing = sorted(k for k in required if k not in names)
    if missing:
        raise ValueError(f"{what}: missing key(s) {missing}")
    return raw


def finite_vector(value: object, n: int, what: str) -> tuple[float, ...]:
    """``value`` as ``n`` finite floats, or a ValueError that names the field."""
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence) or len(value) != n:
        raise ValueError(f"{what} must be {n} numbers, got {value!r}")
    try:
        return tuple(finite_real(v, what) for v in value)
    except ValueError:
        raise ValueError(f"{what} must be {n} finite numbers, got {value!r}") from None
