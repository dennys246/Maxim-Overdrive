"""The wire's JSON: the one strict decoder in front of stage 1, and the one encoder (boundaries §9.1, TB-1).

A client's text message is untrusted input. Before stage 1 types any field, this decoder has already refused, with
``bad_json``: text past ``max_bytes`` (counted before parsing); bytes that are not UTF-8; anything that is not JSON;
``NaN``, ``Infinity`` and ``-Infinity``, which Python's parser accepts by default; a number that overflows a float
(``1e400``); a key repeated in one object, which Python would resolve silently as last-wins; a string holding a lone
surrogate (``"\\ud800"``), which Python's parser accepts and no UTF-8 log or echo could write; and an integer of
magnitude 2⁵³ or more, because Godot parses every JSON number as a double, in which 2⁵³ + 1 is 2⁵³, so the pin sits
below both (boundaries §9.1, O59; ``client/tests/unit/test_json_ints.gd`` shows it); and containers nested past
``MAX_DEPTH``, a rule both readers apply, where the parser's own limit would differ between interpreters.

A float that holds a whole value (``5500.0``, ``1e3``) is still a float here; stage 1 refuses it where an integer is
expected (``not_int``), and ``true`` there too, since a bool is an int in Python (``checks.whole_number``).

The encoder writes what the server sends: compact, keys sorted, ASCII only, and integers only. The design keeps floats
off the server's JSON (DC-S9's integer columns; scales as integer rationals, DC-N5), and Godot's parser reads every
number as a double, so the client can tell ``5`` from ``5.0`` only by the text: it refuses any number written with
a point or an exponent, and this encoder never writes one.
"""

from __future__ import annotations

import json
import math
from collections.abc import Sequence

from simcore.core.refusals import RefusalCode, Refused

__all__ = ["JSON_INT_MAX", "MAX_DEPTH", "decode", "encode", "integers_only"]

JSON_INT_MAX = 2**53 - 1  # boundaries §9.1 (O59): the largest n for which a double tells n from n + 1
MAX_DEPTH = 32  # containers along the deepest path, so [] is 1; deeper than any message the protocol defines
_INT_DIGITS = len(str(JSON_INT_MAX)) + 1  # a sign and 16 digits; longer text is refused before int() reads it


def _refused(message: str) -> Refused:
    return Refused(message, code=RefusalCode.BAD_JSON)


def _constant(name: str) -> float:
    raise _refused(f"JSON has no {name}")  # NaN, Infinity, -Infinity: the names Python's parser would accept


def _integer(text: str) -> int:
    if len(text) > _INT_DIGITS or abs(value := int(text)) > JSON_INT_MAX:
        raise _refused(f"an integer of magnitude 2^53 or more ({len(text)} characters)")
    return value


def _real(text: str) -> float:
    value = float(text)
    if not math.isfinite(value):
        raise _refused(f"a number too large for a double ({len(text)} characters)")
    return value


def _object(pairs: Sequence[tuple[str, object]]) -> dict[str, object]:
    out = dict(pairs)
    if len(out) != len(pairs):
        raise _refused("a key repeated in one object")
    return out


def _check_value(value: object) -> None:
    """Every string in ``value``, keys included, is whole text, and no container nests past ``MAX_DEPTH``. Measured on
    the parsed value, iteratively: the parser's own limit is the interpreter's recursion limit, which differs between
    Python versions, so it can't be the rule both readers apply."""
    stack: list[tuple[object, int]] = [(value, 1)]
    while stack:
        item, depth = stack.pop()
        if isinstance(item, dict | list):
            if depth > MAX_DEPTH:
                raise _refused(f"containers nested past {MAX_DEPTH} levels")
            children = [*item.keys(), *item.values()] if isinstance(item, dict) else item
            stack.extend((child, depth + 1) for child in children)
        elif isinstance(item, str) and any(0xD800 <= ord(ch) <= 0xDFFF for ch in item):
            raise _refused("a string holding a lone surrogate")
        elif isinstance(item, str) and "\x00" in item:  # Godot can't hold U+0000 in a String (O63): never wire text
            raise _refused("a string holding U+0000")


def decode(data: str | bytes, *, max_bytes: int) -> object:
    """One JSON value from ``data``, or a Refused coded ``bad_json`` that says why without echoing the input."""
    size = len(data.encode("utf-8", "surrogatepass")) if isinstance(data, str) else len(data)
    if size > max_bytes:
        raise _refused(f"a message of {size} bytes, past the {max_bytes}-byte cap")
    if isinstance(data, bytes):
        try:
            data = data.decode("utf-8")
        except UnicodeDecodeError:
            raise _refused("bytes that are not UTF-8") from None
    try:
        value = json.loads(
            data, parse_constant=_constant, parse_int=_integer, parse_float=_real, object_pairs_hook=_object
        )
    except json.JSONDecodeError as exc:
        raise _refused(f"not JSON: {exc.msg} at character {exc.pos}") from None
    except RecursionError:  # nesting past the interpreter's own limit, which MAX_DEPTH sits far below
        raise _refused(f"containers nested past {MAX_DEPTH} levels") from None
    _check_value(value)
    return value


def integers_only(value: object, what: str) -> None:
    """Refuse a float anywhere in ``value`` (``not_int``): the server's JSON holds integers only (O62), so a reader of
    it applies this right after the version, before any schema, and refuses any number written with a point or an
    exponent with this one code, as the client's parser does (O63)."""
    stack: list[object] = [value]
    while stack:
        item = stack.pop()
        if isinstance(item, float):
            raise Refused(
                f"{what}: a number with a point or an exponent; it holds integers only", code=RefusalCode.NOT_INT
            )
        if isinstance(item, dict):
            stack.extend(item.values())
        elif isinstance(item, list):
            stack.extend(item)


def encode(value: object) -> str:
    """``value`` as the server's JSON text. A float, or an integer of magnitude 2⁵³ or more, is a programming error
    here, never sent: the client refuses the one and can't read the other exactly."""
    _check_numbers(value)
    return json.dumps(value, allow_nan=False, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _check_text(text: str) -> None:
    if "\x00" in text:
        raise ValueError("U+0000 can't go on the wire: the client's text can't hold it (O63)")
    if any(0xD800 <= ord(ch) <= 0xDFFF for ch in text):
        raise ValueError("a lone surrogate can't go on the wire: the decoder refuses it")


def _check_numbers(value: object) -> None:
    if isinstance(value, str):
        _check_text(value)
        return
    if isinstance(value, bool) or value is None:
        return
    if isinstance(value, float):
        raise ValueError("the server writes integers only; a float can't go on the wire")
    if isinstance(value, int):
        if abs(value) > JSON_INT_MAX:
            raise ValueError(f"an integer of magnitude 2^53 or more can't go on the wire: {value.bit_length()} bits")
        return
    if isinstance(value, dict):
        for item in (*value.keys(), *value.values()):
            _check_numbers(item)
        return
    if isinstance(value, list | tuple):
        for item in value:
            _check_numbers(item)
        return
    raise TypeError(f"a {type(value).__name__} can't go on the wire: JSON holds objects, arrays, text and integers")
