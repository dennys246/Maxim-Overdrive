"""Protocol v0's wire, read by the server's decoders: the golden fixtures, the frame grammar's extension rule, the
strict JSON pins and stage 1 (client_rendering §4.1; world_v2 §8; boundaries §9.1; tile §3.3, §3.4).

``client/tests/unit/net/`` holds Godot's decoders to the same manifest, so the two sides reach one outcome per
fixture.
"""

from __future__ import annotations

import contextlib
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from simcore.core.refusals import RefusalCode, Refused
from simcore.core.schema import Format, Tagged
from simcore.protocol import registry
from simcore.protocol.catalogue import UNITS, V0, Channel, catalogue_hash, describe
from simcore.protocol.frame_header import HEADER, Array, Grid, Header, Table, read_header
from simcore.protocol.grammar import CELL_GRID, DecodedFrame, decode_frame, encode_cells, pack
from simcore.protocol.messages import CLIENT_MESSAGES, Hello, Kindle, Move, MoveTo, Snapshot, Time, read_message
from simcore.protocol.strict_json import JSON_INT_MAX, MAX_DEPTH, decode, encode, integers_only
from tests.conftest import ALL_TIERS

ROOT = Path(__file__).resolve().parents[1]
WIRE = ROOT / "client" / "tests" / "fixtures" / "wire"
ARTIFACT = ROOT / "docs" / "generated" / "protocol.md"
MANIFEST: dict[str, Any] = json.loads((WIRE / "manifest.json").read_text())


def _load(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_load("wire_texts")  # before wire_fixtures, which imports these two by name
_load("wire_frames")
wf = _load("wire_fixtures")

V0_HASH = catalogue_hash(describe(V0))


def _entries(set_name: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = MANIFEST[set_name]["fixtures"]
    return entries


def _read_frame(entry: dict[str, Any]) -> Any:
    data = (WIRE / entry["file"]).read_bytes()
    known = [*V0, *(Channel(**{**d, "scale": tuple(d["scale"]), "offset": tuple(d["offset"])})
                    for d in entry.get("known_extra", []))]  # fmt: skip
    return decode_frame(data, known=known, catalogue=entry["catalogue"], max_bytes=entry.get("max_bytes", wf.FRAME_CAP))


def _outcome(read: Any, entry: dict[str, Any]) -> tuple[str, str]:
    try:
        read(entry)
    except Refused as refused:
        return "refused", refused.code.value
    return "accepted", ""


READERS = {
    "frames": _read_frame,
    "json": lambda e: decode((WIRE / e["file"]).read_bytes(), max_bytes=e.get("max_bytes", 1 << 20)),
    "client": lambda e: read_message((WIRE / e["file"]).read_bytes()),
}


@pytest.mark.parametrize(
    ("set_name", "entry"),
    [(s, e) for s in READERS for e in _entries(s)],
    ids=lambda v: v["file"] if isinstance(v, dict) else v,
)
def test_every_fixture_reaches_the_outcome_its_manifest_names(set_name, entry):
    assert _outcome(READERS[set_name], entry) == (entry["outcome"], entry["code"])


def test_the_committed_fixtures_are_what_the_script_makes():
    # Regenerate with: .venv/bin/python scripts/wire_fixtures.py
    assert wf.stale(WIRE) == []


def test_the_generator_reports_a_changed_a_missing_and_a_left_over_file(tmp_path):
    assert wf.main([], out=tmp_path) == 0
    assert wf.main(["--check"], out=tmp_path) == 0
    (tmp_path / "frames" / "base.bin").write_bytes(b"x")
    (tmp_path / "json" / "nan.json").unlink()
    (tmp_path / "frames" / "extra.bin").write_bytes(b"")
    (tmp_path / "frames" / ".DS_Store").write_bytes(b"\x00")  # the machine's, not a fixture
    assert wf.stale(tmp_path) == ["frames/base.bin", "frames/extra.bin", "json/nan.json"]
    assert wf.main(["--check"], out=tmp_path) == 1


def test_the_six_goldens_come_first_and_cover_what_world_v2_names():
    names = [Path(e["file"]).stem for e in _entries("frames")[:6]]
    assert names == [
        "base", "asymmetric", "unknown_optional_channel", "unknown_optional_grid_and_table",
        "unknown_required_channel", "newer_protocol",
    ]  # fmt: skip


def test_both_readers_are_named_for_the_shared_sets_and_only_the_server_for_client_messages():
    assert {s: MANIFEST[s]["readers"] for s in READERS} == {
        "frames": ["python", "godot"], "json": ["python", "godot"], "client": ["python"]
    }  # fmt: skip


@pytest.mark.parametrize(
    "entry", [e for e in _entries("frames") if e["outcome"] == "accepted"], ids=lambda e: e["file"]
)
def test_an_accepted_frame_reads_its_probes_its_ignored_names_and_its_tick(entry):
    frame = _read_frame(entry)
    assert list(frame.ignored) == entry.get("ignored", [])
    assert frame.shape == tuple(entry.get("shape", [2, 2, 2]))
    assert frame.tick == entry.get("tick", 5)
    for probe in entry.get("probes", []):
        value = frame.channels[probe["channel"]][tuple(probe["zyx"])]
        read = int(np.asarray(value).view("<u2")) if probe.get("as") == "bits" else int(value)  # an f16's bits
        assert read == probe["value"]
    assert set(frame.channels) == {c.name for c in V0}
    assert not any(a.flags.writeable for a in frame.channels.values())  # views of the frame's bytes, read-only


def test_the_asymmetric_frame_puts_x_fastest_and_states_its_origin():
    frame = _read_frame(next(e for e in _entries("frames") if e["file"] == "frames/asymmetric.bin"))
    flat = frame.channels["material"].reshape(-1)
    assert flat[3] == 2  # [z=0, y=0, x=3]: x varies fastest on the wire
    assert flat[4 * 2] == 3  # [z=0, y=2, x=0]
    assert flat[12] == 5  # [z=1, y=0, x=0]
    assert (frame.cell_size_um, frame.origin_um) == (200_000, (-1000, 2000, 400))


def test_a_frame_needs_its_cell_grid_and_the_reader_s_catalogue():
    data = wf._cells()
    with pytest.raises(Refused) as refused:
        decode_frame(data, known=V0, catalogue=catalogue_hash([]), max_bytes=wf.FRAME_CAP)
    assert (refused.value.code, refused.value.field) == (RefusalCode.BAD_VERSION, "catalogue")


_values = st.integers(0, 255)


@settings(max_examples=60, deadline=None)
@given(
    shape=st.tuples(st.integers(1, 4), st.integers(1, 4), st.integers(1, 4)),
    seed=st.integers(0, 2**32 - 1),
    tick=st.integers(0, JSON_INT_MAX),
)
def test_a_frame_round_trips_every_channel_bit_for_bit(shape, seed, tick):
    rng = np.random.default_rng(seed)
    arrays = [
        rng.integers(0, 256, shape).astype("<u1"),
        rng.integers(0, 2**16, shape).astype("<u2"),
        rng.integers(0, 256, shape).astype("<u1"),
        rng.uniform(-273, 6000, shape).astype("<f2"),
    ]
    data = encode_cells(tick=tick, regions_version=3, cell_size_um=50_000, origin_um=(1, -2, 3), catalogue=V0,
                        channels=list(zip(V0, arrays, strict=True)))  # fmt: skip
    frame = decode_frame(data, known=V0, catalogue=V0_HASH, max_bytes=len(data))
    assert (frame.tick, frame.regions_version) == (tick, 3)
    for channel, values in zip(V0, arrays, strict=True):
        assert frame.channels[channel.name].tobytes() == values.tobytes()


@settings(max_examples=300, deadline=None)
@given(data=st.binary(max_size=600))
def test_the_frame_decoder_refuses_any_bytes_with_a_code_and_never_crashes(data):
    with contextlib.suppress(Refused):  # a refusal is a reading; anything else escaping fails the test
        decode_frame(data, known=V0, catalogue=V0_HASH, max_bytes=wf.FRAME_CAP)


@pytest.mark.slow
@pytest.mark.skipif(not ALL_TIERS, reason="slow: 5,400 frames; set MAXIM_OVERDRIVE_ALL_TIERS=1 (the gate does)")
def test_every_one_byte_change_to_a_frame_is_read_or_refused_and_the_sweep_reaches_every_check():
    # Exhaustive, not sampled: every byte of the base frame set to five values (5,400 frames). The reach is asserted
    # so the sweep can't quietly stop exercising a check (measured 2026-11-22: every code below, and 254 accepted).
    base = wf._cells()
    seen: set[str] = set()
    for at in range(len(base)):
        for byte in (0x00, 0x20, 0x7F, 0xFF, base[at] ^ 1):
            data = bytearray(base)
            data[at] = byte
            try:
                decode_frame(bytes(data), known=V0, catalogue=V0_HASH, max_bytes=wf.FRAME_CAP)
            except Refused as refused:  # a refusal is a reading; anything else escaping fails the test
                seen.add(refused.code.value)
            else:
                seen.add("accepted")
    assert seen >= {
        "accepted",
        "bad_json",
        "bad_shape",
        "bad_version",
        "unknown_field",
        "unknown_kind",
        "missing_field",
    }


def test_the_encoder_refuses_an_array_that_is_not_its_channel_s():
    wrong = [np.zeros((2, 2, 2), "<u2"), *[np.zeros((2, 2, 2), "<u1")] * 3]
    with pytest.raises(TypeError, match="channel material"):
        encode_cells(tick=0, regions_version=0, cell_size_um=1, origin_um=(0, 0, 0), catalogue=V0,
                     channels=list(zip(V0, wrong, strict=True)))  # fmt: skip


def test_pack_writes_the_header_length_little_endian():
    data = pack({"a": 1}, [b"\x01\x02"])
    assert data == (7).to_bytes(4, "little") + b'{"a":1}' + b"\x01\x02"


def test_the_one_cell_grid_is_named_cells():
    assert CELL_GRID == "cells"


def test_a_header_reads_to_typed_values_with_each_array_s_channel_a_catalogue_channel():
    header, _ = wf._split(wf._optional_grid_and_table())
    read = read_header(header)
    assert isinstance(read, Header)
    assert [type(g) for g in read.grids] == [Grid, Grid]
    assert read.tables == (Table("flames", required=False, rows=3),)
    assert all(isinstance(a, Array) and isinstance(a.channel, Channel) for a in read.arrays)
    assert read.arrays[0].channel.description() == V0[0].description()
    assert isinstance(_read_frame(_entries("frames")[0]), DecodedFrame)


# --- the catalogue -------------------------------------------------------------------------------------------------


def test_v0_s_channels_are_client_rendering_s_four_with_units_from_the_vocabulary():
    assert [c.name for c in V0] == ["material", "region", "crack", "temperature_c"]
    assert [c.dtype for c in V0] == ["u8", "u16", "u8", "f16"]
    assert {c.unit for c in V0} <= set(UNITS)
    assert all(c.required for c in V0)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"encoding": "raw", "scale": (2, 1)},
        {"encoding": "raw", "offset": (1, 1)},
        {"encoding": "linear", "scale": (1, 0)},
        {"encoding": "linear", "offset": (0, -1)},
    ],
)
def test_a_malformed_channel_is_refused_with_a_code(kwargs):
    with pytest.raises(Refused) as refused:
        Channel("c", "id", "u8", required=True, **kwargs)
    assert refused.value.code is RefusalCode.BAD_SHAPE


def test_the_protocol_artifact_is_what_the_registry_renders():
    # Regenerate with: PYTHONPATH=src python -c 'from simcore.protocol.registry import render; print(render(), end="")'
    assert ARTIFACT.read_bytes() == registry.render().encode()


# --- strict JSON ----------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("value", [2**53 - 1, -(2**53 - 1), 0])
def test_an_integer_inside_the_pin_round_trips(value):
    assert decode(encode({"n": value}), max_bytes=100) == {"n": value}


@pytest.mark.parametrize("bad", [2**53, -(2**53), 2**53 + 1, 5500.0, 0.5, math.nan, math.inf])
def test_the_encoder_writes_integers_within_the_pin_only(bad):
    with pytest.raises(ValueError, match=r"2\^53|integers only"):
        encode({"a": [bad]})


def test_the_encoder_writes_compact_sorted_ascii():
    assert encode({"b": 1, "a": "é", "c": [True, None]}) == '{"a":"\\u00e9","b":1,"c":[true,null]}'


def test_the_size_cap_counts_bytes_before_parsing():
    with pytest.raises(Refused, match="past the 3-byte cap"):
        decode('"é"', max_bytes=3)  # three characters, four bytes
    assert decode('"é"', max_bytes=4) == "é"


def test_bytes_that_are_not_utf8_are_refused():
    with pytest.raises(Refused, match="not UTF-8") as refused:
        decode(b'"\xff"', max_bytes=10)
    assert refused.value.code is RefusalCode.BAD_JSON


def test_the_depth_limit_counts_containers_and_holds_inside_objects():
    assert decode("[" * MAX_DEPTH + "]" * MAX_DEPTH, max_bytes=1 << 10)
    deep_in_object = '{"a":' * MAX_DEPTH + "[]" + "}" * MAX_DEPTH
    with pytest.raises(Refused, match="nested past"):
        decode(deep_in_object, max_bytes=1 << 10)


def test_nesting_past_the_interpreter_s_own_limit_is_the_same_refusal():
    with pytest.raises(Refused, match="nested past") as refused:
        decode("[" * 200_000 + "]" * 200_000, max_bytes=1 << 20)
    assert refused.value.code is RefusalCode.BAD_JSON


@settings(max_examples=150, deadline=None)
@given(st.text(max_size=200))
def test_the_decoder_refuses_any_text_with_bad_json_or_reads_it(text):
    codes = set()
    try:
        decode(text, max_bytes=1 << 12)
    except Refused as refused:  # the decoder's one code; anything but a Refused escaping fails the test
        codes.add(refused.code)
    assert codes <= {RefusalCode.BAD_JSON}


# U+0000 and lone surrogates are never wire text (O63; the decoder refuses both, and so does the encoder)
_WIRE_TEXT = st.text(st.characters(exclude_characters="\x00", exclude_categories=["Cs"]), max_size=8)
_JSON_LEAVES = st.none() | st.booleans() | st.integers(-JSON_INT_MAX, JSON_INT_MAX) | _WIRE_TEXT


@settings(max_examples=80, deadline=None)
@given(
    st.recursive(
        _JSON_LEAVES,
        lambda c: st.lists(c, max_size=3) | st.dictionaries(_WIRE_TEXT, c, max_size=3),
        max_leaves=12,
    )
)
def test_what_the_encoder_writes_the_decoder_reads_back(value):
    text = encode(value)
    assert decode(text, max_bytes=1 << 16) == json.loads(text)


# --- client messages: decode and stage 1 ---------------------------------------------------------------------------

SAMPLES: dict[str, dict[str, object]] = {
    "hello": {"type": "hello", "protocol": 0, "token": "t0ken"},
    "move": {"type": "move", "seq": 1, "dir": [1, 0]},
    "move_to": {"type": "move_to", "seq": 1, "target_mm": [1, 2]},
    "kindle": {"type": "kindle", "seq": 1, "point_mm": [1, 2, 3], "duration_ticks": 40},
    "time": {"type": "time", "seq": 1, "op": "set_scale", "scale": 2.5},
    "snapshot": {"type": "snapshot", "seq": 1},
}


def test_every_message_type_has_a_sample():
    assert set(SAMPLES) == set(CLIENT_MESSAGES.schemas)


def _past_json(value: object) -> bool:
    """A value the decoder refuses before stage 1 sees it: a non-finite float, or an integer past the pin."""
    if isinstance(value, list | tuple):
        return any(_past_json(v) for v in value)
    if isinstance(value, float):
        return not math.isfinite(value)
    return isinstance(value, int) and not isinstance(value, bool) and abs(value) > JSON_INT_MAX


def _walk() -> list[tuple[str, str, object, RefusalCode]]:
    """Each field of each message, fed each value its converter must refuse, and the code it must refuse it with:
    the converter's, or ``bad_json`` where the value can't pass the decoder at all."""
    cases = []
    for kind, schema in CLIENT_MESSAGES.schemas.items():
        for field in schema.fields:
            for bad, code in field.convert.bad:
                if not (field.nullable and bad is None):
                    version_first = kind == "hello" and field.name == "protocol"  # read first (_check_protocol)
                    want = RefusalCode.BAD_VERSION if version_first else code
                    cases.append((kind, field.name, bad, RefusalCode.BAD_JSON if _past_json(bad) else want))
    return cases


@pytest.mark.parametrize(("kind", "name", "bad", "code"), _walk())
def test_every_field_refuses_each_value_its_converter_lists(kind, name, bad, code):
    message = {**SAMPLES[kind], name: bad}
    with pytest.raises(Refused) as refused:
        read_message(json.dumps(message))
    assert refused.value.code is code


@pytest.mark.parametrize("kind", SAMPLES)
def test_every_message_refuses_an_unknown_and_a_missing_field(kind):
    with pytest.raises(Refused) as unknown:
        read_message(json.dumps({**SAMPLES[kind], "issued_tick": 1}))
    assert unknown.value.code is RefusalCode.UNKNOWN_FIELD
    required = [f.name for f in CLIENT_MESSAGES.schemas[kind].fields if f.required]
    for name in required:
        with pytest.raises(Refused) as missing:
            read_message(json.dumps({k: v for k, v in SAMPLES[kind].items() if k != name}))
        version_first = kind == "hello" and name == "protocol"  # a hello with no version is refused for it
        assert missing.value.code is (RefusalCode.BAD_VERSION if version_first else RefusalCode.MISSING_FIELD)


def test_each_message_reads_to_its_type():
    assert read_message(json.dumps(SAMPLES["snapshot"])) == Snapshot(seq=1)
    assert read_message(json.dumps(SAMPLES["kindle"])) == Kindle(seq=1, point_mm=(1, 2, 3), duration_ticks=40)
    assert read_message(json.dumps(SAMPLES["time"])) == Time(seq=1, op="set_scale", scale=2.5)
    assert read_message('{"type":"move","seq":3,"dir":null}') == Move(seq=3, dir=None)
    assert read_message(json.dumps(SAMPLES["move_to"])) == MoveTo(seq=1, target_mm=(1, 2))


def test_a_hello_s_repr_never_shows_its_token():
    hello = read_message(json.dumps(SAMPLES["hello"]))
    assert isinstance(hello, Hello)
    assert hello.token == "t0ken"
    assert "t0ken" not in repr(hello)
    assert "t0ken" not in str(hello)


def test_a_bad_token_s_refusal_never_echoes_it():
    with pytest.raises(Refused) as refused:
        read_message(json.dumps({**SAMPLES["hello"], "token": "secret value"}))
    assert "secret" not in str(refused.value)


@pytest.mark.parametrize("op", ["pause", "resume"])
def test_pause_and_resume_take_no_scale_and_set_scale_needs_one(op):
    assert read_message(json.dumps({"type": "time", "seq": 1, "op": op})) == Time(seq=1, op=op, scale=None)
    with pytest.raises(Refused) as refused:
        read_message(json.dumps({"type": "time", "seq": 1, "op": op, "scale": 1.0}))
    assert (refused.value.code, refused.value.field) == (RefusalCode.BAD_SHAPE, "scale")


def test_the_wire_schemas_may_name_ticks_and_content_formats_may_not():
    # The rule is content's (Format's): a wire schema carries the simulation's ticks, a data file never does
    assert {"tick", "duration_ticks"} <= {f.name for s in (HEADER, CLIENT_MESSAGES.schemas["kindle"]) for f in s.fields}
    with pytest.raises(TypeError, match="never ticks"):
        Format("doc", 1, CLIENT_MESSAGES.schemas["kindle"])


def test_the_messages_are_one_tagged_reader_keyed_by_type():
    assert isinstance(CLIENT_MESSAGES, Tagged)
    assert CLIENT_MESSAGES.tag == "type"


def test_the_server_s_json_holds_integers_only_at_any_depth():
    # O62: a reader of the server's JSON refuses a float wherever it sits, after the version (strict_json.integers_only)
    integers_only({"a": [1, {"b": -2}], "c": "5.0", "d": True, "e": None}, "doc")
    for value in ({"a": 5.0}, {"a": [1, [2.5]]}, {"a": {"b": {"c": 1e20}}}, [0.0]):
        with pytest.raises(Refused) as refused:
            integers_only(value, "doc")
        assert refused.value.code is RefusalCode.NOT_INT


def test_the_encoder_refuses_what_json_can_t_hold_and_a_long_integer_is_refused_before_it_is_read():
    for value in ({1, 2}, object(), b"bytes"):
        with pytest.raises(TypeError, match="can't go on the wire"):
            encode({"a": value})
    for nul in ({"a": "x\x00"}, {"a\x00": 1}):
        with pytest.raises(ValueError, match="U\\+0000"):
            encode(nul)
    with pytest.raises(ValueError, match="lone surrogate"):
        encode({"\ud800": 1})
    with pytest.raises(Refused) as refused:  # 10,000 digits: refused by length, never handed to int()
        decode("[" + "9" * 10_000 + "]", max_bytes=20_000)
    assert refused.value.code is RefusalCode.BAD_JSON


_JSON_VALUES = st.recursive(
    st.none() | st.booleans() | st.integers(-(2**60), 2**60) | st.floats(allow_nan=False) | st.text(max_size=12),
    lambda inner: st.lists(inner, max_size=4) | st.dictionaries(st.text(max_size=6), inner, max_size=4),
    max_leaves=12,
)


@settings(max_examples=400, deadline=None)
@given(kind=st.sampled_from(sorted(SAMPLES)), data=st.data())
def test_stage_1_never_crashes_on_a_real_message_with_one_field_changed(kind, data):
    # Past decode (review T-S2): a valid message of each type with one field replaced, added or dropped, so the
    # examples reach the schema and the message builders, not only the JSON parser. A refusal carries a code.
    message = dict(SAMPLES[kind])
    key = data.draw(st.sampled_from([*message, "extra"]), label="key")
    if data.draw(st.booleans(), label="drop") and key in message and key != "type":
        del message[key]
    else:
        message[key] = data.draw(_JSON_VALUES, label="value")
    codes: list[RefusalCode] = []
    try:
        read = read_message(json.dumps(message))
    except Refused as refused:  # a refusal carries a code; any other exception escaping fails the test
        codes.append(refused.code)
    if not codes:
        assert type(read).__name__.lower().replace("_", "") == str(message["type"]).replace("_", "")
