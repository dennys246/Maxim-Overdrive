"""Content digests, stored versioned: ``sha256/c14n-1:<hex>`` (checklist step 3b; boundaries §6.3).

A digest names how it was made, its hash and its canonical serialisation, so a later change of either is a new
prefix that a reader refuses by name, never a hash that silently stops matching. "Hash" means SHA-256 over a
canonical serialisation (world_model §8). The log header (step 5a) records each content file's digest this way.

**c14n-1**, the canonical serialisation of a loaded value: JSON text with no whitespace, mapping keys (strings only)
sorted by code point, sequences as arrays, ``None``, ``True`` and ``False`` as ``null``, ``true`` and ``false``, an
int in decimal (at most 600 digits), a float by ``repr`` (the shortest text that reads back as the same float; -0.0 as
0.0; non-finite floats are refused, as JSON has none), and strings UTF-8 with only ``"``, ``\\`` and the C0 controls
escaped (a lone surrogate is refused). Types are exact: a numpy scalar, a bool posing as an int, or a str subclass is
refused, so a value's text never depends on which library computed it. It is canonical per type, not per value:
``1``, ``1.0`` and ``True`` are three texts, which is right only because every reader types its fields (``Real`` a
float, ``Whole`` an int); step 5a's log header, the first caller, digests readers' typed output only. Anything else is a
programming error, not input: a digest is taken of a value a reader has already built.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Mapping, Sequence

from simcore.core.refusals import RefusalCode, Refused

SCHEME = "sha256/c14n-1"
_DIGEST = re.compile(r"(?P<scheme>[a-z0-9]+/[a-z0-9]+-[0-9]+):(?P<hex>[0-9a-f]{64})")
_ESCAPES = {'"': '\\"', "\\": "\\\\"} | {chr(c): f"\\u{c:04x}" for c in range(0x20)}


def _text(value: str) -> str:
    if any(0xD800 <= ord(ch) <= 0xDFFF for ch in value):  # a lone surrogate has no UTF-8 form
        raise TypeError("c14n-1 has no form for a lone surrogate")
    return '"' + "".join(_ESCAPES.get(ch, ch) for ch in value) + '"'


# Below CPython's lowest int-to-text limit (640, the least PYTHONINTMAXSTRDIGITS accepts; 4,300 by default), so every
# process gives one an int's text or refuses it the same way (delta review, D5). Every Whole field is far smaller.
_MAX_INT_DIGITS = 600


def _scalar(value: object) -> str | None:
    """A scalar's c14n-1 text, or None if ``value`` is not one. Exact types only: a numpy float is a float subclass
    whose repr is ``np.float64(1.5)``, and a bool is an int subclass, so neither may take the int or float branch."""
    if value is None:
        return "null"
    if isinstance(value, bool) and type(value) is bool:
        return "true" if value else "false"
    if isinstance(value, int) and type(value) is int:
        if abs(value) >= 10**_MAX_INT_DIGITS:
            raise TypeError("c14n-1 has no form for an int this long")
        return str(value)
    if isinstance(value, float) and type(value) is float:
        if not math.isfinite(value):
            raise TypeError(f"c14n-1 has no form for {value!r}")
        return repr(value + 0.0)  # + 0.0 turns -0.0 into 0.0: equal floats, one text
    if isinstance(value, str) and type(value) is str:
        return _text(value)
    return None


def canonical(value: object) -> str:
    """``value`` in c14n-1, or a TypeError for anything c14n-1 has no form for."""
    text = _scalar(value)
    if text is not None:
        return text
    if isinstance(value, Mapping):
        if not all(type(k) is str for k in value):
            raise TypeError("c14n-1 mapping keys are strings")
        return "{" + ",".join(f"{_text(k)}:{canonical(value[k])}" for k in sorted(value)) + "}"
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return "[" + ",".join(canonical(v) for v in value) + "]"
    raise TypeError(f"c14n-1 has no form for a {type(value).__name__}")


def digest(value: object) -> str:
    """The versioned digest of ``value``: ``sha256/c14n-1:`` and the SHA-256 of its c14n-1 text, in hex."""
    return f"{SCHEME}:{hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()}"


def check_digest(stored: object, what: str) -> str:
    """A stored digest, held to the one scheme this reader knows, or a Refused: a digest made another way is refused
    by its scheme (``bad_version``), and one that is not a digest at all by its shape (``bad_shape``)."""
    match = _DIGEST.fullmatch(stored) if isinstance(stored, str) else None
    if match is None:
        raise Refused(f"{what} must be a digest such as {SCHEME}:<64 hex>", code=RefusalCode.BAD_SHAPE)
    if match["scheme"] != SCHEME:
        raise Refused(f"{what} is a {match['scheme']} digest; this reader knows {SCHEME}", code=RefusalCode.BAD_VERSION)
    return stored  # type: ignore[return-value]  # fullmatch proved it is a str
