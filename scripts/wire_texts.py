"""The wire fixtures' text sets (``scripts/wire_fixtures.py`` writes them): JSON texts both readers judge alike, and the
client messages decode and stage 1 judge (``simcore.protocol.strict_json``, ``simcore.protocol.messages``).
"""

from __future__ import annotations

import json
from collections.abc import Mapping

from simcore.protocol.messages import MAX_MESSAGE_BYTES
from simcore.protocol.strict_json import MAX_DEPTH

__all__ = ["Fixture", "client_messages", "json_texts"]

# name -> (bytes, outcome, code or "", extras for the manifest)
Fixture = tuple[bytes, str, str, Mapping[str, object]]


def json_texts() -> dict[str, Fixture]:
    nested = "[" * 5_000 + "]" * 5_000  # past Python's recursion limit (1,000) and Godot's depth limit
    return {
        "object": (b'{"a":[1,-2,"x",true,null],"b":{}}', "accepted", "", {}),
        "nan": (b'{"a":NaN}', "refused", "bad_json", {}),
        "infinity": (b'{"a":Infinity}', "refused", "bad_json", {}),
        "minus_infinity": (b'{"a":-Infinity}', "refused", "bad_json", {}),
        "overflow": (b'{"a":1e400}', "refused", "bad_json", {}),
        "repeated_key": (b'{"a":1,"a":2}', "refused", "bad_json", {}),
        "repeated_escaped_key": (b'{"a":1,"\\u0061":2}', "refused", "bad_json", {}),
        "nested_repeated_key": (b'{"a":[{"b":1,"b":1}]}', "refused", "bad_json", {}),
        "lone_surrogate": (b'{"a":["\\ud800"]}', "refused", "bad_json", {}),
        "deep_nesting": (nested.encode(), "refused", "bad_json", {}),
        "nesting_at_limit": (("[" * MAX_DEPTH + "]" * MAX_DEPTH).encode(), "accepted", "", {}),
        "nesting_past_limit": (("[" * (MAX_DEPTH + 1) + "]" * (MAX_DEPTH + 1)).encode(), "refused", "bad_json", {}),
        "not_json": (b'{"a":', "refused", "bad_json", {}),
        "oversized": (b'{"a":"' + b"x" * 64 + b'"}', "refused", "bad_json", {"max_bytes": 64}),
        **_grammar_edges(),
    }


_OK, _NO = "accepted", "refused"


def _grammar_edges() -> dict[str, Fixture]:
    """RFC 8259's edges, where a parser written for the wire and Python's can part (O63): each judged alike."""
    texts = {**_string_edges(), **_number_and_structure_edges()}
    return {name: (data, outcome, "" if outcome == _OK else "bad_json", {}) for name, (data, outcome) in texts.items()}


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
        "escaped_nul": (b'{"a":"x\\u0000"}', ok),
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
    }


def _number_and_structure_edges() -> dict[str, tuple[bytes, str]]:
    ok, no = _OK, _NO
    return {
        "minus_zero": (b"[-0]", ok),
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
