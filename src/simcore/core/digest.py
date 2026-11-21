"""Content digests, stored versioned: ``sha256/c14n-1:<hex>`` (checklist step 3b; boundaries §6.3).

A digest names how it was made, its hash and its canonical serialisation, so a later change of either is a new
prefix that a reader refuses by name, never a hash that silently stops matching. "Hash" means SHA-256 over a
canonical serialisation (world_model §8). The log header (step 5a) records each content file's digest this way.

**c14n-1**, the canonical serialisation of a loaded value: JSON text with no whitespace, mapping keys (strings only)
sorted by code point, sequences as arrays, ``None``, ``True`` and ``False`` as ``null``, ``true`` and ``false``, an
int in decimal, a float by ``repr`` (the shortest text that reads back as the same float; non-finite floats are
refused, as JSON has none), and strings UTF-8 with only ``"``, ``\\`` and the C0 controls escaped. Anything else is a
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
    return '"' + "".join(_ESCAPES.get(ch, ch) for ch in value) + '"'


def canonical(value: object) -> str:
    """``value`` in c14n-1, or a TypeError for anything c14n-1 has no form for."""
    if value is None or isinstance(value, bool):
        return {None: "null", True: "true", False: "false"}[value]
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise TypeError(f"c14n-1 has no form for {value!r}")
        return repr(value)
    if isinstance(value, str):
        return _text(value)
    if isinstance(value, Mapping):
        if not all(isinstance(k, str) for k in value):
            raise TypeError("c14n-1 mapping keys are strings")
        return "{" + ",".join(f"{_text(k)}:{canonical(value[k])}" for k in sorted(value)) + "}"
    if isinstance(value, Sequence) and not isinstance(value, bytes | bytearray):
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
