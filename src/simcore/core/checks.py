"""Turning untrusted values into the finite floats physics needs, or refusing them with a reason.

Data files (rigs, materials, action limits, scenes), imagined specs and SEM actions (an NPC's tool call, an LLM's
output, a client's intent) all reach the world as loosely typed values. Each number becomes a float here or is
refused here, so nothing downstream sees NaN, an infinity, a bool posing as a number, or a string that ``float()``
would quietly accept. Each mapping is held to the keys its reader knows (``known_keys``), so a misspelt key is
refused rather than silently ignored. Every value a refusal echoes goes through ``shown``, which bounds it.
``tests/test_validation.py`` and ``tests/test_act_validation.py`` hold every loader to it.
"""

from __future__ import annotations

import math
import numbers
import reprlib
from collections.abc import Collection, Mapping, Sequence


class _BoundedRepr(reprlib.Repr):
    """reprlib that echoes only plain values by value, so an echo is the same text in every run.

    Strings, numbers, bools, None and lists, tuples, sets and dicts of them print as reprlib prints them. Anything else
    prints as its type name (``<a Thing>``), never its repr, which may carry a memory address that differs between runs
    (step 3b review, Architecture S4). A set prints sorted by each element's echo, never in iteration order, which
    PYTHONHASHSEED decides for str and bytes. An int too long to convert to text (past 4300 digits) is shown by its
    size.
    """

    def repr_int(self, x: int, level: int) -> str:
        if x.bit_length() > 128:
            return f"<an integer of about {int(x.bit_length() * 0.30103)} digits>"
        return repr(x)

    def repr_bool(self, x: bool, level: int) -> str:
        return repr(x)

    def repr_NoneType(self, x: None, level: int) -> str:  # reprlib dispatches on the type's name
        return "None"

    def repr_float(self, x: float, level: int) -> str:
        return repr(x)

    def repr_instance(self, x: object, level: int) -> str:
        return f"<a {type(x).__name__}>"

    def _sorted_set(self, x: set[object] | frozenset[object], level: int, left: str, right: str) -> str:
        if not x:
            return f"{type(x).__name__}()"
        items = sorted(self.repr1(e, level - 1) for e in x)
        shown_items = items[: self.maxset] + (["..."] if len(items) > self.maxset else [])
        return f"{left}{', '.join(shown_items)}{right}"

    def repr_set(self, x: set[object], level: int) -> str:
        return self._sorted_set(x, level, "{", "}")

    def repr_frozenset(self, x: frozenset[object], level: int) -> str:
        return self._sorted_set(x, level, "frozenset({", "})")


_SHOW = _BoundedRepr()
_SHOW.maxstring = _SHOW.maxother = 40


def shown(value: object) -> str:
    """A bounded, run-independent repr for an error message (boundaries §5.4, bounded echo), so a huge or hostile
    value can't flood or crash the reply, and a replayed refusal has the same bytes. It bounds length only; it doesn't
    scrub."""
    if type(value) not in _PLAIN_TYPES:  # a subclass of one (a numpy float, a str subclass) has a repr of its own
        return _SHOW.repr_instance(value, 0)
    return _SHOW.repr(value)


# The types reprlib prints by value.
_PLAIN_TYPES = (str, int, float, bool, type(None), list, tuple, set, frozenset, dict)


def entity_key(name: str) -> str:
    """A name as Maxim's EntityMap resolves it: stripped, lower-cased, spaces as underscores (boundaries §2.2: the
    name rule sits in layer 0, so the membrane's gate half can apply it without reaching the cells)."""
    return name.strip().lower().replace(" ", "_")


def finite_real(value: object, what: str) -> float:
    """``value`` as one finite float, or a ValueError that names it. Numpy scalars count; bools and strings don't."""
    f = math.nan
    if not isinstance(value, bool) and isinstance(value, numbers.Real):
        try:
            f = float(value)
        except OverflowError:  # an int too big for a float, such as 10**400 from YAML or JSON
            f = math.nan
    if not math.isfinite(f):
        raise ValueError(f"{what} must be a finite number, got {shown(value)}")
    return f


def whole_number(value: object, what: str) -> int:
    """``value`` as an int, or a ValueError that names it. Only integers count: not bools, floats such as 2.9 (which
    ``int()`` would quietly truncate to 2) or numeric strings."""
    if isinstance(value, bool) or not isinstance(value, numbers.Integral):
        raise ValueError(f"{what} must be a whole number, got {shown(value)}")
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
    both = sorted(set(required) & set(optional))
    if both:  # a reader's own schema contradicting itself is a programming error, not bad input
        raise TypeError(f"{what}: {both} can't be both required and optional")
    if not isinstance(raw, Mapping):
        raise ValueError(f"{what} must be a mapping, got {type(raw).__name__}")
    keys = list(raw)
    names = {k for k in keys if isinstance(k, str)}
    unknown = sorted(shown(k) for k in keys if not isinstance(k, str) or (k not in required and k not in optional))
    if unknown:
        listed = ", ".join(unknown[:8]) + (f" and {len(unknown) - 8} more" if len(unknown) > 8 else "")
        raise ValueError(f"{what}: unknown key(s) [{listed}]; it takes {sorted({*required, *optional})}")
    missing = sorted(k for k in required if k not in names)
    if missing:
        raise ValueError(f"{what}: missing key(s) {missing}")
    return raw


def format_version(raw: object, expected: int, what: str) -> Mapping[str, object]:
    """``raw`` as a mapping whose ``version`` is exactly ``expected``, or a ValueError that names what it found.

    Checked before the keys, so a file from a newer format is refused for its version, not for the fields it added.
    Only an int counts: ``true`` and ``0.0`` are not version 0, and a file with no version is refused, not assumed.
    """
    if not isinstance(raw, Mapping):
        raise ValueError(f"{what} must be a mapping, got {type(raw).__name__}")
    version = raw.get("version")
    if type(version) is not int or version != expected:
        raise ValueError(f"{what} version must be {expected}, got {shown(version)}")
    return raw


def _has_length(value: Sequence[object], n: int) -> bool:
    try:
        return len(value) == n
    except OverflowError:  # a sequence too long to count, such as range(10**20); no JSON value is
        return False


def finite_vector(value: object, n: int, what: str) -> tuple[float, ...]:
    """``value`` as ``n`` finite floats, or a ValueError that names the field."""
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence) or not _has_length(value, n):
        raise ValueError(f"{what} must be {n} numbers, got {shown(value)}")
    try:
        return tuple(finite_real(v, what) for v in value)
    except ValueError:
        raise ValueError(f"{what} must be {n} finite numbers, got {shown(value)}") from None
