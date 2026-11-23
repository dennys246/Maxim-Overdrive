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
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray
from wire_texts import Fixture, client_messages, json_texts

from simcore.protocol.catalogue import V0, Channel, catalogue_hash, describe
from simcore.protocol.frame_header import MAX_EXTENT, MAX_TABLES
from simcore.protocol.grammar import encode_cells

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
        np.arange(n, dtype="<u2").reshape(shape) * 257 + 1,  # region: 0x0001, 0x0102, ...: the two bytes differ, so
        # a reader that swaps them reads another id (a probe below), which RG8's upload of the low byte first needs
        np.linspace(0, 255, n).astype("<u1").reshape(shape),  # crack
        np.linspace(-40.0, 1200.0, n).astype("<f2").reshape(shape),  # temperature_c
    ]


def _cells(tick: int = 5, shape: tuple[int, int, int] = SHAPE, catalogue: Sequence[Channel] = V0) -> bytes:
    """The base frame: v0's channels, under the hash of ``catalogue``, the one its welcome announced."""
    channels = list(zip(V0, _arrays(shape), strict=True))
    return encode_cells(
        tick=tick, regions_version=1, cell_size_um=CELL_UM, origin_um=ORIGIN_UM, catalogue=catalogue, channels=channels
    )


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
    """Append an array carrying ``channel``; the frame's catalogue hash stays welcome's (O64)."""

    def edit(header: Header) -> None:
        arrays = _array_entries(header)
        offset = sum(int(a["size"]) for a in arrays)
        size = len(values)
        arrays.append({"channel": channel.description(), "of": of, "offset": offset, "size": size,
                       "uncompressed_size": size})  # fmt: skip

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

    return edit


SMOKE = Channel("smoke_kg_m3", "kg_per_m3", "f32", "raw", required=False)  # a unit this build has never heard of
SOOT = Channel("soot", "ratio", "u8", "raw", required=False)  # an optional channel a reader may know and a frame omit
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
                        catalogue=V0, channels=list(zip(V0, arrays, strict=True)))  # fmt: skip


ASYMMETRIC_CORNERS = [(z, y, x) for z in (0, 1) for y in (0, 2) for x in (0, 3)]
# the region ids at the same corners: index z*12 + y*4 + x in [2, 3, 4], each id's two bytes different
ASYMMETRIC_REGIONS = [
    {"channel": "region", "zyx": [z, y, x], "value": (z * 12 + y * 4 + x) * 257 + 1} for z, y, x in ASYMMETRIC_CORNERS
]
_SEEN = ("python", "godot")


def _goldens() -> dict[str, Fixture]:
    probes = [{"channel": "material", "zyx": list(c), "value": i + 1} for i, c in enumerate(ASYMMETRIC_CORNERS)]
    required = Channel("smoke_kg_m3", "kg_per_m3", "f32", "raw", required=True)
    return {
        "base": (_cells(), "accepted", "", {"probes": [{"channel": "region", "zyx": [1, 1, 1], "value": 7 * 257 + 1}]}),
        "asymmetric": (_asymmetric(), "accepted", "", {"shape": [2, 3, 4], "probes": [*probes, *ASYMMETRIC_REGIONS]}),
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
        "optional_channel_omitted": (  # the reader knows an optional channel this frame doesn't carry (O64)
            _cells(catalogue=[*V0, SOOT]),
            "accepted",
            "",
            {"catalogue": catalogue_hash(describe([*V0, SOOT])), "known_extra": [SOOT.description()]},
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
    return _repack(header, [payload[:start] + payload[start + size :]])


def _frame_edges() -> dict[str, Fixture]:
    """Where the two decoders could part (step 7 review, W-S1 to W-S8): each with the server's outcome and code."""
    header, payload = _split(_cells())
    text = json.dumps(header, separators=(",", ":"), sort_keys=True)
    digest = str(header["catalogue"])

    def swap(old: str, new: str) -> bytes:
        assert old in text, old
        return _raw(text.replace(old, new, 1), payload)

    many = [{"name": f"t{i}", "required": False, "rows": 0} for i in range(MAX_TABLES + 1)]
    return {
        "header_nul_padding": (_raw(text + "\x00\x00", payload), "refused", "bad_json", {}),
        "header_trailing_comma": (swap('"tick":5', '"tick":5,'), "refused", "bad_json", {}),
        "header_leading_zero": (swap('"tick":5', '"tick":05'), "refused", "bad_json", {}),
        "tick_1e20": (swap('"tick":5', '"tick":1e20'), "refused", "not_int", {}),
        "scale_float": (swap('"scale":[1,255]', '"scale":[1.0,255]'), "refused", "not_int", {}),
        "protocol_true": (_edited(_set("protocol", True)), "refused", "bad_version", {}),
        "protocol_negative": (_edited(_set("protocol", -1)), "refused", "bad_version", {}),
        "digest_trailing_newline": (swap(f'"{digest}"', f'"{digest}\\n"'), "refused", "bad_shape", {}),
        "optional_name_escaped_non_ascii": (  # an escape decodes to a non-ASCII name: refused by the name rule
            _edited(lambda h: _array_entries(h)[-1]["channel"].update(name="s\u00f6t"), _extra(SOOT, bytes(8))),
            "refused",
            "bad_identity_key",
            {},
        ),
        "name_with_colon": (_edited(_set_channel(0, "name", "mat:erial")), "refused", "bad_identity_key", {}),
        "too_many_tables": (_edited(_set("tables", many)), "refused", "over_budget", {}),
        "extent_past_u16": (_edited(_set("shape", [1, 1, MAX_EXTENT + 1])), "refused", "out_of_range", {}),
    }


def frames() -> dict[str, Fixture]:
    return {**_goldens(), **_pins(), **_header_json(), **_schema(), **_layout(), **_extension(), **_frame_edges()}


SETS: dict[str, tuple[Callable[[], dict[str, Fixture]], str, tuple[str, ...]]] = {
    "frames": (frames, "bin", _SEEN),
    "json": (json_texts, "json", _SEEN),
    "client": (client_messages, "json", ("python",)),
}


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
                entry.setdefault("catalogue", V0_HASH)  # what welcome announced: every frame carries it (O64)
            entries.append(entry)
        manifest[set_name] = {"readers": list(readers), "fixtures": entries}
    out["manifest.json"] = (json.dumps(manifest, indent=1, sort_keys=True) + "\n").encode()
    return out


def stale(directory: Path) -> list[str]:
    """The fixture files that differ from what this script makes, or are missing, or are left over. A hidden file (a
    Finder ``.DS_Store``) is the machine's, not a fixture, so it is never left over."""
    want = files()
    have = (
        {
            p.relative_to(directory).as_posix()
            for p in directory.rglob("*")
            if p.is_file() and not p.name.startswith(".")
        }
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
