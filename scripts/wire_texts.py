"""The wire fixtures' text sets (``scripts/wire_fixtures.py`` writes them): JSON texts both readers judge alike, and the
client messages decode and stage 1 judge (``simcore.protocol.strict_json``, ``simcore.protocol.messages``).
"""

from __future__ import annotations

import json
from collections.abc import Mapping

from simcore.protocol.messages import MAX_MESSAGE_BYTES
from simcore.protocol.strict_json import MAX_DEPTH, decode

__all__ = ["Fixture", "client_messages", "json_texts", "value_tree"]

# name -> (bytes, outcome, code or "", extras for the manifest)
Fixture = tuple[bytes, str, str, Mapping[str, object]]
_OK, _NO = "accepted", "refused"


def json_texts() -> dict[str, Fixture]:
    nested = "[" * 5_000 + "]" * 5_000  # past Python's recursion limit (1,000) and Godot's depth limit
    return {
        "object": _judged(b'{"a":[1,-2,"x",true,null],"b":{},"c":"caf\xc3\xa9 \\u00e9","d":2.5}', _OK),
        "nan": (b'{"a":NaN}', "refused", "bad_json", {}),
        "infinity": (b'{"a":Infinity}', "refused", "bad_json", {}),
        "minus_infinity": (b'{"a":-Infinity}', "refused", "bad_json", {}),
        "overflow": (b'{"a":1e400}', "refused", "bad_json", {}),
        "repeated_key": (b'{"a":1,"a":2}', "refused", "bad_json", {}),
        "repeated_escaped_key": (b'{"a":1,"\\u0061":2}', "refused", "bad_json", {}),
        "nested_repeated_key": (b'{"a":[{"b":1,"b":1}]}', "refused", "bad_json", {}),
        "lone_surrogate": (b'{"a":["\\ud800"]}', "refused", "bad_json", {}),
        "deep_nesting": (nested.encode(), "refused", "bad_json", {}),
        "nesting_at_limit": _judged(("[" * MAX_DEPTH + "]" * MAX_DEPTH).encode(), _OK),
        "nesting_past_limit": (("[" * (MAX_DEPTH + 1) + "]" * (MAX_DEPTH + 1)).encode(), "refused", "bad_json", {}),
        "not_json": (b'{"a":', "refused", "bad_json", {}),
        "oversized": (b'{"a":"' + b"x" * 64 + b'"}', "refused", "bad_json", {"max_bytes": 64}),
        **_grammar_edges(),
    }


def _grammar_edges() -> dict[str, Fixture]:
    """RFC 8259's edges, where a parser written for the wire and Python's can part (O63): each judged alike, and each
    accepted one read to the same value (``value_tree``)."""
    texts = {**_string_edges(), **_number_and_structure_edges()}
    return {name: _judged(data, outcome) for name, (data, outcome) in texts.items()}


def _judged(data: bytes, outcome: str) -> Fixture:
    if outcome == _NO:
        return (data, outcome, "bad_json", {})
    return (data, outcome, "", {"value": value_tree(decode(data, max_bytes=len(data) + 1))})


def value_tree(value: object) -> object:
    """``value`` in a form no JSON reader can change: text as its code points, each object as its members sorted by
    key, and a float by its class only (finite), never its digits: the server's JSON holds no float (O62), so a
    reader classifies one, and Godot's to_float isn't correctly rounded (step 7 delta 2, W SF-1). Godot builds the
    same tree."""
    if isinstance(value, str):
        return {"s": [ord(ch) for ch in value]}
    if isinstance(value, bool) or value is None:
        return {"b": value}
    if isinstance(value, int):
        return {"i": value}
    if isinstance(value, float):
        return {"f": "finite"}  # the decoder refused every other class
    if isinstance(value, dict):
        return {"o": [[value_tree(k), value_tree(v)] for k, v in sorted(value.items())]}
    assert isinstance(value, list)
    return {"a": [value_tree(v) for v in value]}


def _string_edges() -> dict[str, tuple[bytes, str]]:
    ok, no = _OK, _NO
    return {
        "leading_zero": (b'{"a":007}', no),
        "trailing_comma_object": (b'{"a":1,}', no),
        "trailing_comma_array": (b"[1,2,]", no),
        "raw_tab_in_string": (b'{"a":"x\ty"}', no),
        "raw_newline_in_string": (b'{"a":"x\ny"}', no),
        "nul_after_value": (b'{"a":1}\x00', no),
        "nul_in_string": (b'{"a":"x\x00"}', no),
        "escaped_nul": (b'{"a":"x\\u0000"}', no),  # Godot can't hold U+0000 in a String, so neither side takes it
        "bom": (b'\xef\xbb\xbf{"a":1}', no),
        "float_1e20": (b'{"a":1e20}', ok),
        "float_whole_at_2p53": (b'{"a":9007199254740992.0}', ok),
        "float_largest_power": (b"[1e308]", ok),
        "float_past_double": (b"[1e309]", no),
        "raw_utf8": (b'{"a":"caf\xc3\xa9"}', ok),
        "truncated_utf8": (b'{"a":"\xc3"}', no),
        "overlong_utf8": (b'{"a":"\xc0\xaf"}', no),  # a lead byte no UTF-8 sequence uses
        "overlong_utf8_three_bytes": (b'{"a":"\xe0\x80\xaf"}', no),  # "/" in three bytes: valid lead, too small
        "overlong_utf8_four_bytes": (b'{"a":"\xf0\x80\x80\xaf"}', no),
        "utf8_surrogate": (b'{"a":"\xed\xa0\x80"}', no),
        "utf8_past_unicode": (b'{"a":"\xf4\x90\x80\x80"}', no),
        "surrogate_pair": (b'{"a":"\\ud83d\\ude00"}', ok),
        "lone_low_surrogate": (b'{"a":"\\udc00"}', no),
        "high_then_letter": (b'{"a":"\\ud83d\\u0041"}', no),
        "unknown_escape": (b'{"a":"\\x41"}', no),
        "short_unicode_escape": (b'{"a":"\\u12"}', no),
        "solidus_escape": (b'{"a":"\\/"}', ok),
        "raw_bom_in_key": (b'{"\xef\xbb\xbfa":1,"a":2}', ok),  # two keys: a decoder that drops a BOM sees one
        "escaped_bom_leading": (b'["\\ufeffx"]', ok),
        "nul_beside_replacement": (b'{"a\\u0000b":1,"a\\ufffdb":2}', no),  # refused for its U+0000, not a repeat
        "signed_unicode_escape_plus": (b'["\\u+041"]', no),
        "signed_unicode_escape_minus": (b'["\\u-041"]', no),
    }


def _number_and_structure_edges() -> dict[str, tuple[bytes, str]]:
    ok, no = _OK, _NO
    return {
        "minus_zero": (b"[-0]", ok),
        "exponent_past_u32": (b"[1e4294967296]", no),  # an exponent that wraps in a 32-bit reader
        "zero_with_a_huge_exponent": (b"[0e99999999999999999999]", ok),
        "long_fraction_and_exponent": (b"[0." + b"0" * 400 + b"1e400]", ok),  # 0.1
        "just_below_overflow": (b"[1.7976931348623157e308]", ok),
        "rounds_down_to_the_largest_double": (b"[1.7976931348623158e308]", ok),
        "rounds_up_past_the_largest_double": (b"[1.7976931348623159e308]", no),
        "just_past_the_halfway": (b"[1.79769313486231581e308]", no),  # to_float reads it as finite
        # 2^1024 - 2^970 written out: the tie between the largest double and 2^1024, which rounds to even (inf)
        "exact_halfway_past_the_largest_double": (
            b"[179769313486231580793728971405303415079934132710037826936173778980444968292764750946649017977587207096330286416692887910946555547851940402630657488671505820681908902000708383676273854845817711531764475730270069855571366959622842914819860834936475292719074168444365510704342711559699508093042880177904174497792]",
            no,
        ),
        "integer_past_u64": (b"[18446744073709551617]", no),  # 2^64 + 1: a reader that wraps reads 1
        "integer_at_2p63": (b"[9223372036854775808]", no),  # past int64: Godot's to_int reads -2^63, whose absi is too
        "negative_integer_at_2p63": (b"[-9223372036854775808]", no),
        "long_negative_integer": (b"[-" + b"9" * 400 + b"]", no),
        "smallest_normal_double": (b"[2.2250738585072014e-308]", ok),  # finite, though Godot reads its digits as 0
        "half_way_digits": (b"[970034019735371.5]", ok),
        "past_the_integers_as_a_float": (b"[9007199254740993.0]", ok),
        "exponent_without_digits": (b"[1e]", no),
        "fraction_without_digits": (b"[1.]", no),
        "leading_plus": (b"[+1]", no),
        "leading_point": (b"[.5]", no),
        "largest_negative": (b"[-9007199254740991]", ok),
        "negative_at_2p53": (b"[-9007199254740992]", no),
        "long_integer": (b"[" + b"1" * 30 + b"]", no),
        "scalar": (b"7", ok),
        "empty": (b"", no),
        "only_space": (b" \t\r\n", no),
        "two_values": (b"{} {}", no),
        "capital_true": (b"[True]", no),
        "short_null": (b"[nul]", no),
        "key_not_text": (b"{1:2}", no),
        "vertical_tab": (b"[1,\x0b2]", no),
    }


def _message(**fields: object) -> bytes:
    return json.dumps(fields, separators=(",", ":")).encode()


KINDLE: dict[str, object] = {"type": "kindle", "seq": 3, "point_mm": [5500, 2925, 400], "duration_ticks": 100}


def _accepted_messages() -> dict[str, Fixture]:
    ok: str = "accepted"
    kindle = KINDLE
    accepted: dict[str, Fixture] = {
        "hello": (_message(type="hello", protocol=0, token="Ab3_-x" * 7 + "z"), ok, "", {}),
        "hello_newer": (_message(type="hello", protocol=1, token="t0ken"), "refused", "bad_version", {}),
        "move": (_message(type="move", seq=1, dir=[1, 0]), ok, "", {}),
        "move_stop": (_message(type="move", seq=2, dir=None), ok, "", {}),
        "move_to": (_message(type="move_to", seq=2, target_mm=[8000, 3600]), ok, "", {}),
        "kindle": (_message(**kindle), ok, "", {}),
        "time_pause": (_message(type="time", seq=4, op="pause"), ok, "", {}),
        "time_set_scale": (_message(type="time", seq=5, op="set_scale", scale=10), ok, "", {}),
        "snapshot": (_message(type="snapshot", seq=6), ok, "", {}),
        "seq_largest": (_message(type="snapshot", seq=2**31 - 1), ok, "", {}),
    }
    return accepted


def _refused_messages() -> dict[str, tuple[bytes, str]]:
    kindle = KINDLE
    return {
        "duration_float": (_message(**{**kindle, "duration_ticks": 5500.0}), "not_int"),
        "duration_true": (_message(**{**kindle, "duration_ticks": True}), "not_int"),
        "duration_1e3": (_message(**kindle).replace(b'"duration_ticks":100', b'"duration_ticks":1e3'), "not_int"),
        "point_bool": (_message(**{**kindle, "point_mm": [1, True, 3]}), "not_int"),
        "seq_below_2p53": (_message(type="snapshot", seq=2**53 - 1), "out_of_range"),
        "seq_at_2p53": (_message(type="snapshot", seq=2**53), "bad_json"),
        "seq_past_2p53": (_message(type="snapshot", seq=2**53 + 1), "bad_json"),
        "seq_2p31": (_message(type="snapshot", seq=2**31), "out_of_range"),
        "seq_negative": (_message(type="snapshot", seq=-1), "out_of_range"),
        "unknown_type": (_message(type="vote", seq=1), "unknown_kind"),
        "no_type": (_message(seq=1), "unknown_kind"),
        "type_not_text": (_message(type=7, seq=1), "unknown_kind"),
        "client_actor": (_message(type="move", seq=1, dir=[1, 0], actor=2), "unknown_field"),
        "client_tick": (_message(type="move", seq=1, dir=[1, 0], tick=9), "unknown_field"),
        "client_observed_tick": (_message(type="snapshot", seq=1, observed_tick=9), "unknown_field"),
        "client_apply_us": (_message(**{**kindle, "apply_us": 0}), "unknown_field"),
        "client_role": (_message(type="hello", protocol=0, token="t0ken", role="host"), "unknown_field"),
        "missing_seq": (_message(type="snapshot"), "missing_field"),
        "dir_short": (_message(type="move", seq=1, dir=[1]), "bad_shape"),
        "dir_text": (_message(type="move", seq=1, dir="up"), "bad_shape"),
        "token_spaces": (_message(type="hello", protocol=0, token="a token"), "bad_shape"),
        "token_long": (_message(type="hello", protocol=0, token="t" * 65), "bad_shape"),
        "pause_with_scale": (_message(type="time", seq=4, op="pause", scale=2), "bad_shape"),
        "set_scale_without_scale": (_message(type="time", seq=4, op="set_scale"), "bad_shape"),
        "unknown_op": (_message(type="time", seq=4, op="rewind"), "unknown_kind"),
        "not_object": (b"[1,2]", "bad_shape"),
        "nan": (b'{"type":"time","seq":4,"op":"set_scale","scale":NaN}', "bad_json"),
        "overflow": (b'{"type":"time","seq":4,"op":"set_scale","scale":1e400}', "bad_json"),
        "repeated_key": (b'{"type":"snapshot","seq":1,"seq":2}', "bad_json"),
        "oversized": (_message(type="snapshot", seq=1, pad="x" * MAX_MESSAGE_BYTES), "bad_json"),
    }


def client_messages() -> dict[str, Fixture]:
    refused: dict[str, Fixture] = {k: (v, "refused", code, {}) for k, (v, code) in _refused_messages().items()}
    return {**_accepted_messages(), **refused}
