"""Protocol v0's golden wire fixtures, read by the Python decoders and by Godot's (world_v2 §8; boundaries §9.1).

Three sets, under ``client/tests/fixtures/wire/``, each listed in ``manifest.json`` with the outcome every reader of it
must reach (accepted, or refused with a code), so the two sides are held to one list:

- ``frames/``: cell frames (``simcore.protocol.grammar``; ``client/addons/engine/net/frame_decoder.gd``). The six
  goldens world_v2 §8 names come first: a base frame, an asymmetric grid, an unknown optional channel (ignored), an
  unknown optional grid and table (ignored), an unknown required channel (refused) and a newer protocol (refused).
  The rest each break one rule, so any reader that checks every rule refuses it with the same code in any order, and
  the integer pins sit in a header's ``tick``: 2⁵³ - 1 accepted, 2⁵³ and 2⁵³ + 1 refused (O59).
- ``json/``: texts both JSON readers judge alike (``simcore.protocol.strict_json``; ``wire_json.gd``).
- ``client/``: client messages through decode and stage 1 (``simcore.protocol.messages``), the server's alone.

The fixtures are small and uncompressed, so their bytes are the same on every machine, and ``--check`` compares them
byte for byte. Run: ``python scripts/wire_fixtures.py`` writes them; ``--check`` exits 1 when a committed file differs.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from simcore.protocol.catalogue import V0, Channel, catalogue_hash, describe
from simcore.protocol.grammar import encode_cells
from simcore.protocol.messages import MAX_MESSAGE_BYTES
from simcore.protocol.strict_json import MAX_DEPTH

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "client" / "tests" / "fixtures" / "wire"
FORMAT = "overdrive-wire-fixtures"
VERSION = 0
FRAME_CAP = 4 * 1024 * 1024  # the client's inbound buffer (client_rendering §4.3): the decoders' default cap
V0_HASH = catalogue_hash(describe(V0))
SHAPE = (2, 2, 2)
CELL_UM, ORIGIN_UM = 200_000, (0, 0, 0)

Header = dict[str, Any]  # the encoder's own header, as json.loads reads it back


def _arrays(shape: tuple[int, int, int]) -> list[NDArray[np.generic]]:
    n = int(np.prod(shape))
    return [
        (np.arange(n) % 4).astype("<u1").reshape(shape),  # material: air, then three solids
        np.arange(n, dtype="<u2").reshape(shape) * 257,  # region: both bytes differ, so RG8's byte order shows
        np.linspace(0, 255, n).astype("<u1").reshape(shape),  # crack
        np.linspace(-40.0, 1200.0, n).astype("<f2").reshape(shape),  # temperature_c
    ]


def _cells(tick: int = 5, shape: tuple[int, int, int] = SHAPE) -> bytes:
    channels = list(zip(V0, _arrays(shape), strict=True))
    return encode_cells(tick=tick, regions_version=1, cell_size_um=CELL_UM, origin_um=ORIGIN_UM, channels=channels)


def _split(frame: bytes) -> tuple[Header, bytes]:
    n = int.from_bytes(frame[:4], "little")
    header: Header = json.loads(frame[4 : 4 + n])
    return header, frame[4 + n :]


def _repack(header: Header, payload: list[bytes]) -> bytes:
    """A frame from a header the server's encoder would refuse to write (a float, a missing field): plain JSON."""
    return _raw(json.dumps(header, separators=(",", ":"), sort_keys=True), b"".join(payload))


def _edited(edit: Callable[[Header], None], frame: bytes | None = None) -> bytes:
    """The base frame with its header changed by ``edit``, the payload as it was."""
    header, payload = _split(frame or _cells())
    edit(header)
    return _repack(header, [payload])


def _raw(header_text: str, payload: bytes = b"") -> bytes:
    data = header_text.encode("utf-8", "surrogatepass")
    return len(data).to_bytes(4, "little") + data + payload


def _array_entries(header: Header) -> list[dict[str, Any]]:
    arrays: list[dict[str, Any]] = header["arrays"]
    return arrays


def _with_channel(channel: Channel, values: bytes, of: str = "cells") -> Callable[[Header], None]:
    """Append an array carrying ``channel`` (and rehash the catalogue over every channel the frame carries)."""

    def edit(header: Header) -> None:
        arrays = _array_entries(header)
        offset = sum(int(a["size"]) for a in arrays)
        size = len(values)
        arrays.append({"channel": channel.description(), "of": of, "offset": offset, "size": size,
                       "uncompressed_size": size})  # fmt: skip
        header["catalogue"] = catalogue_hash([a["channel"] for a in arrays])

    return edit


def _extra(channel: Channel, values: bytes, of: str = "cells", grid: Header | None = None) -> bytes:
    header, payload = _split(_cells())
    if grid is not None:
        header["grids"].append(grid)
    _with_channel(channel, values, of)(header)
    return _repack(header, [payload, values])


def _set(key: str, value: object) -> Callable[[Header], None]:
    return lambda h: h.__setitem__(key, value)


def _set_channel(i: int, key: str, value: object) -> Callable[[Header], None]:
    def edit(h: Header) -> None:
        _array_entries(h)[i]["channel"][key] = value
        h["catalogue"] = catalogue_hash([a["channel"] for a in _array_entries(h)])

    return edit


SMOKE = Channel("smoke_kg_m3", "kg_per_m3", "f32", "raw", required=False)  # a unit this build has never heard of
EIGHT_F32 = np.arange(8, dtype="<f4").tobytes()
ZONES = {"name": "zones", "required": False, "shape": [1, 1, 2], "cell_size_um": 400_000, "origin_um": [0, 0, 0]}


def _optional_grid_and_table() -> bytes:
    header, payload = _split(_cells())
    header["grids"].append(ZONES)
    header["tables"].append({"name": "flames", "required": False, "rows": 3})
    zone = Channel("zone_gas_c", "celsius", "f32", "raw", required=True)  # required, but on an ignored grid
    height = Channel("flame_height_m", "m", "f32", "raw", required=True)
    _with_channel(zone, np.zeros(2, "<f4").tobytes(), "zones")(header)
    _with_channel(height, np.zeros(3, "<f4").tobytes(), "flames")(header)
    return _repack(header, [payload, np.zeros(2, "<f4").tobytes(), np.zeros(3, "<f4").tobytes()])


def _asymmetric() -> bytes:
    """[nz, ny, nx] = [2, 3, 4], a different material at each corner, so a reader that swaps axes reads wrong ids."""
    shape = (2, 3, 4)
    arrays = _arrays(shape)
    material = np.zeros(shape, "<u1")
    for i, (z, y, x) in enumerate(ASYMMETRIC_CORNERS):
        material[z, y, x] = i + 1
    arrays[0] = material
    return encode_cells(tick=5, regions_version=1, cell_size_um=CELL_UM, origin_um=(-1000, 2000, 400),
                        channels=list(zip(V0, arrays, strict=True)))  # fmt: skip


ASYMMETRIC_CORNERS = [(z, y, x) for z in (0, 1) for y in (0, 2) for x in (0, 3)]
_SEEN = ("python", "godot")

# name -> (bytes, outcome, code or "", extras for the manifest)
Fixture = tuple[bytes, str, str, Mapping[str, object]]


def _goldens() -> dict[str, Fixture]:
    probes = [{"channel": "material", "zyx": list(c), "value": i + 1} for i, c in enumerate(ASYMMETRIC_CORNERS)]
    required = Channel("smoke_kg_m3", "kg_per_m3", "f32", "raw", required=True)
    return {
        "base": (_cells(), "accepted", "", {"probes": [{"channel": "region", "zyx": [1, 1, 1], "value": 7 * 257}]}),
        "asymmetric": (_asymmetric(), "accepted", "", {"shape": [2, 3, 4], "probes": probes}),
        "unknown_optional_channel": (_extra(SMOKE, EIGHT_F32), "accepted", "", {"ignored": ["channel:smoke_kg_m3"]}),
        "unknown_optional_grid_and_table": (
            _optional_grid_and_table(),
            "accepted",
            "",
            {"ignored": ["grid:zones", "table:flames"]},
        ),
        "unknown_required_channel": (_extra(required, EIGHT_F32), "refused", "unknown_field", {}),
        "newer_protocol": (_edited(_set("protocol", 1)), "refused", "bad_version", {}),
    }


def _tick(text: bytes) -> bytes:
    """The base frame with its tick's text replaced: the header length is unchanged only when the text is, so the
    frame is re-packed around it."""
    header, payload = _split(_cells())
    body = json.dumps(header, separators=(",", ":"), sort_keys=True).encode().replace(b'"tick":5', b'"tick":' + text)
    return len(body).to_bytes(4, "little") + body + payload


def _ascii_only() -> bytes:
    header, payload = _split(_cells())
    text = json.dumps(header, separators=(",", ":"), sort_keys=True, ensure_ascii=False)
    return _raw(text.replace('"kind":"full"', '"kind":"f\u00fcll"'), payload)  # a u-umlaut, as UTF-8


def _pins() -> dict[str, Fixture]:
    return {
        "tick_below_2p53": (_tick(b"9007199254740991"), "accepted", "", {"tick": 2**53 - 1}),
        "tick_at_2p53": (_tick(b"9007199254740992"), "refused", "bad_json", {}),
        "tick_past_2p53": (_tick(b"9007199254740993"), "refused", "bad_json", {}),
        "tick_float": (_tick(b"5.0"), "refused", "not_int", {}),
        "tick_true": (_tick(b"true"), "refused", "not_int", {}),
        "tick_1e3": (_tick(b"1e3"), "refused", "not_int", {}),
    }


def _header_json() -> dict[str, Fixture]:
    base = _cells()
    header, payload = _split(base)
    text = json.dumps(header, separators=(",", ":"), sort_keys=True)
    return {
        "header_not_json": (_raw(text[:-1], payload), "refused", "bad_json", {}),
        "header_nan": (_raw(text.replace('"tick":5', '"tick":NaN'), payload), "refused", "bad_json", {}),
        "header_overflow": (_raw(text.replace('"tick":5', '"tick":1e400'), payload), "refused", "bad_json", {}),
        "header_repeated_key": (
            _raw(text.replace('"tick":5', '"tick":5,"tick":6'), payload),
            "refused",
            "bad_json",
            {},
        ),
        "header_repeated_escaped_key": (
            _raw(text.replace('"tick":5', '"tick":5,"\\u0074ick":6'), payload),
            "refused",
            "bad_json",
            {},
        ),
        "header_lone_surrogate": (
            _raw(text.replace('"kind":"full"', '"kind":"\\ud800"'), payload),
            "refused",
            "bad_json",
            {},
        ),
        "header_not_object": (_raw("[]", payload), "refused", "bad_shape", {}),
        "header_not_ascii": (_ascii_only(), "refused", "bad_json", {}),
        "header_length_past_end": (len(base).to_bytes(4, "little") + base[4:], "refused", "bad_shape", {}),
        "too_short": (b"\x01\x00\x00", "refused", "bad_shape", {}),
        "oversized": (base, "refused", "bad_shape", {"max_bytes": len(base) - 1}),
    }


def _schema() -> dict[str, Fixture]:
    def drop(key: str) -> Callable[[Header], None]:
        def edit(h: Header) -> None:
            del h[key]

        return edit

    return {
        "protocol_missing": (_edited(drop("protocol")), "refused", "bad_version", {}),
        "protocol_float": (_edited(_set("protocol", 0.0)), "refused", "bad_version", {}),
        "unknown_header_key": (_edited(_set("tick_rate", 20)), "refused", "unknown_field", {}),
        "missing_header_key": (_edited(drop("regions_version")), "refused", "missing_field", {}),
        "delta_kind": (_edited(_set("kind", "delta")), "refused", "unknown_kind", {}),
        "zstd_compression": (_edited(_set("compression", "zstd")), "refused", "unknown_kind", {}),
        "unknown_dtype": (_edited(_set_channel(0, "dtype", "u64")), "refused", "unknown_kind", {}),
        "unknown_encoding": (_edited(_set_channel(2, "encoding", "log")), "refused", "unknown_kind", {}),
        "required_not_bool": (_edited(_set_channel(0, "required", 1)), "refused", "bad_shape", {}),
        "raw_with_scale": (_edited(_set_channel(0, "scale", [2, 1])), "refused", "bad_shape", {}),
        "zero_denominator": (_edited(_set_channel(2, "scale", [1, 0])), "refused", "bad_shape", {}),
    }


def _layout() -> dict[str, Fixture]:
    def arrays(edit: Callable[[list[dict[str, Any]]], None]) -> Callable[[Header], None]:
        return lambda h: edit(_array_entries(h))

    def grids(edit: Callable[[list[dict[str, Any]]], None]) -> Callable[[Header], None]:
        return lambda h: edit(h["grids"])

    base = _cells()
    return {
        "short_array": (
            _edited(arrays(lambda a: a[3].update(size=14, uncompressed_size=14))),
            "refused",
            "bad_shape",
            {},
        ),
        "trailing_bytes": (base + b"\x00", "refused", "bad_shape", {}),
        "array_of_nowhere": (_edited(arrays(lambda a: a[0].update(of="zones"))), "refused", "bad_shape", {}),
        "no_cells_grid": (_edited(grids(lambda g: g[0].update(name="world"))), "refused", "missing_field", {}),
        "grid_shape_differs": (_edited(grids(lambda g: g[0].update(shape=[2, 2, 1]))), "refused", "bad_shape", {}),
        "two_grids_one_name": (_edited(grids(lambda g: g.append(dict(g[0])))), "refused", "bad_shape", {}),
        "duplicate_channel": (_extra(V0[0], bytes(8)), "refused", "bad_shape", {}),
    }


def _extension() -> dict[str, Fixture]:
    other_unit = Channel("crack", "m", "u8", "linear", required=True, scale=(1, 255))
    required_grid = {**ZONES, "required": True}
    no_region = _drop_array(_cells(), 1)
    return {
        "missing_required_channel": (no_region, "refused", "missing_field", {}),
        "known_channel_other_unit": (_edited(_set_channel(2, "unit", "m")), "refused", "bad_shape", {}),
        "unknown_required_grid": (
            _extra(Channel("zone_gas_c", "celsius", "f32", "raw", required=False), bytes(8), "zones", required_grid),
            "refused",
            "unknown_field",
            {},
        ),
        "unknown_required_table": (
            _edited(lambda h: h["tables"].append({"name": "flames", "required": True, "rows": 0})),
            "refused",
            "unknown_field",
            {},
        ),
        "catalogue_mismatch": (
            _edited(_set("catalogue", catalogue_hash([other_unit.description()]))),
            "refused",
            "bad_version",
            {"catalogue": V0_HASH},
        ),
    }


def _drop_array(frame: bytes, i: int) -> bytes:
    """``frame`` without its array ``i``: later offsets moved down, so only the channel is missing."""
    header, payload = _split(frame)
    arrays = _array_entries(header)
    dropped = arrays.pop(i)
    start, size = int(dropped["offset"]), int(dropped["size"])
    for a in arrays[i:]:
        a["offset"] = int(a["offset"]) - size
    header["catalogue"] = catalogue_hash([a["channel"] for a in arrays])
    return _repack(header, [payload[:start] + payload[start + size :]])


def frames() -> dict[str, Fixture]:
    return {**_goldens(), **_pins(), **_header_json(), **_schema(), **_layout(), **_extension()}


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
    }


def _message(**fields: object) -> bytes:
    return json.dumps(fields, separators=(",", ":")).encode()


KINDLE: dict[str, object] = {"type": "kindle", "seq": 3, "point_mm": [5500, 2925, 400], "duration_ticks": 100}


def _accepted_messages() -> dict[str, Fixture]:
    ok: str = "accepted"
    kindle = KINDLE
    accepted: dict[str, Fixture] = {
        "hello": (_message(type="hello", protocol=0, token="Ab3_-x" * 7 + "z"), ok, "", {}),
        "hello_newer": (_message(type="hello", protocol=1, token="t0ken"), ok, "", {}),  # the session refuses it
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
    refused = {k: (v, "refused", code, {}) for k, (v, code) in _refused_messages().items()}
    return {**_accepted_messages(), **refused}


SETS: dict[str, tuple[Callable[[], dict[str, Fixture]], str, tuple[str, ...]]] = {
    "frames": (frames, "bin", _SEEN),
    "json": (json_texts, "json", _SEEN),
    "client": (client_messages, "json", ("python",)),
}


def _announced(data: bytes) -> str:
    """The catalogue hash a ``welcome`` would have announced for this frame: the one its header states, when the
    header can be read at all, and v0's otherwise."""
    try:
        header = json.loads(data[4 : 4 + int.from_bytes(data[:4], "little")])
    except ValueError:  # a header made to be unreadable; the reader refuses it before any hash is compared
        return V0_HASH
    stated: object = header.get("catalogue") if isinstance(header, dict) else None
    return stated if isinstance(stated, str) else V0_HASH


def files() -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    manifest: dict[str, object] = {"format": FORMAT, "version": VERSION, "frame_cap": FRAME_CAP, "catalogue": V0_HASH}
    for set_name, (build, suffix, readers) in SETS.items():
        entries = []
        for name, (data, outcome, code, extras) in build().items():
            path = f"{set_name}/{name}.{suffix}"
            out[path] = data
            entry = {"file": path, "outcome": outcome, "code": code, **extras}
            if set_name == "frames":
                entry.setdefault("catalogue", _announced(data))
            entries.append(entry)
        manifest[set_name] = {"readers": list(readers), "fixtures": entries}
    out["manifest.json"] = (json.dumps(manifest, indent=1, sort_keys=True) + "\n").encode()
    return out


def stale(directory: Path) -> list[str]:
    """The fixture files that differ from what this script makes, or are missing, or are left over."""
    want = files()
    have = (
        {p.relative_to(directory).as_posix() for p in directory.rglob("*") if p.is_file()}
        if directory.exists()
        else set()
    )
    differ = [n for n, data in want.items() if n not in have or (directory / n).read_bytes() != data]
    return sorted(differ + sorted(have - set(want)))


def main(argv: list[str] | None = None, *, out: Path = OUT) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if a committed fixture differs")
    args = parser.parse_args(argv)
    if args.check:
        bad = stale(out)
        for name in bad:
            print(f"wire_fixtures: stale {name}", file=sys.stderr)
        return 1 if bad else 0
    for name, data in files().items():
        (out / name).parent.mkdir(parents=True, exist_ok=True)
        (out / name).write_bytes(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
