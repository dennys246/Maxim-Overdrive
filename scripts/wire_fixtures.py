"""Protocol v0's golden wire fixtures, read by the Python decoders and by Godot's (world_v2 §8; boundaries §9.1).

Four sets, under ``client/tests/fixtures/wire/``, each listed in ``manifest.json`` with the outcome every reader of it
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
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
from wire_frames import (
    CELL_UM,
    EIGHT_F32,
    SHAPE,
    SMOKE,
    SOOT,
    ZONES,
    Header,
)
from wire_frames import (
    array_entries as _array_entries,
)
from wire_frames import (
    arrays as _arrays,
)
from wire_frames import (
    both as _both,
)
from wire_frames import (
    cells as _cells,
)
from wire_frames import (
    drop_array as _drop_array,
)
from wire_frames import (
    edited as _edited,
)
from wire_frames import (
    extra as _extra,
)
from wire_frames import (
    raw as _raw,
)
from wire_frames import (
    repack as _repack,
)
from wire_frames import (
    set_channel as _set_channel,
)
from wire_frames import (
    set_key as _set,
)
from wire_frames import (
    split as _split,
)
from wire_frames import (
    with_channel as _with_channel,
)
from wire_texts import Fixture, client_messages, json_texts

from simcore.core.checks import IDENTITY_KEY_CHARS
from simcore.protocol.catalogue import V0, Channel, catalogue_hash, describe
from simcore.protocol.frame_header import MAX_ARRAYS, MAX_EXTENT, MAX_GRIDS, MAX_TABLES
from simcore.protocol.grammar import MAX_HEADER_BYTES, encode_cells
from simcore.protocol.replies import MAX_TEXT_BYTES, welcome
from simcore.protocol.strict_json import JSON_INT_MAX, MAX_DEPTH, encode

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "client" / "tests" / "fixtures" / "wire"
FORMAT = "overdrive-wire-fixtures"
VERSION = 0
FRAME_CAP = 4 * 1024 * 1024  # the client's inbound buffer (client_rendering §4.3): the decoders' default cap
V0_HASH = catalogue_hash(describe(V0))


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
# temperature_c's f16 bits at two cells of the base frame: a reader that misreads the half-float format reads others
TEMPERATURE_BITS = [
    {"channel": "temperature_c", "zyx": list(zyx), "value": int(_arrays(SHAPE)[3][zyx].view("<u2")), "as": "bits"}
    for zyx in ((0, 0, 1), (1, 1, 1))
]
# the region ids at the same corners: index z*12 + y*4 + x in [2, 3, 4], each id's two bytes different
ASYMMETRIC_REGIONS = [
    {"channel": "region", "zyx": [z, y, x], "value": (z * 12 + y * 4 + x) * 257 + 1} for z, y, x in ASYMMETRIC_CORNERS
]
_SEEN = ("python", "godot")


def _goldens() -> dict[str, Fixture]:
    probes = [{"channel": "material", "zyx": list(c), "value": i + 1} for i, c in enumerate(ASYMMETRIC_CORNERS)]
    required = Channel("smoke_kg_m3", "kg_per_m3", "f32", "raw", required=True)
    return {
        "base": (
            _cells(),
            "accepted",
            "",
            {"probes": [{"channel": "region", "zyx": [1, 1, 1], "value": 7 * 257 + 1}, *TEMPERATURE_BITS]},
        ),
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
        "float_where_the_schema_answers_first": (swap('"kind":"full"', '"kind":1.5'), "refused", "not_int", {}),
        "scale_float": (swap('"scale":[1,255]', '"scale":[1.0,255]'), "refused", "not_int", {}),
        "protocol_true": (_edited(_set("protocol", True)), "refused", "bad_version", {}),
        "newer_protocol_with_float": (
            _raw(text.replace('"protocol":0', '"protocol":1', 1).replace('"tick":5', '"tick":5.0', 1), payload),
            "refused",
            "bad_version",
            {},
        ),
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


def _swap(old: str, new: str) -> bytes:
    """The base frame with ``old`` replaced in its header's text, the payload as it was."""
    header, payload = _split(_cells())
    text = json.dumps(header, separators=(",", ":"), sort_keys=True)
    assert old in text, old
    return _raw(text.replace(old, new, 1), payload)


def _limit_edges() -> dict[str, Fixture]:
    """Every header limit, at it and past it (delta review S8); the manifest's ``limits`` holds the client to them."""
    long_name = Channel("n" * 64, "ratio", "u8", "raw", required=False)
    too_long = _edited(lambda h: _array_entries(h)[-1]["channel"].update(name="n" * 65), _extra(SOOT, bytes(8)))
    grids = [dict(ZONES, name=f"z{i}") for i in range(MAX_GRIDS)]  # with cells, one past the cap
    many_arrays = _edited(lambda h: _array_entries(h).extend([dict(_array_entries(h)[0])] * (MAX_ARRAYS - 3)))
    return {
        "name_at_64_characters": (_extra(long_name, bytes(8)), "accepted", "", {"ignored": [f"channel:{'n' * 64}"]}),
        "name_past_64_characters": (too_long, "refused", "bad_identity_key", {}),
        "too_many_grids": (_edited(lambda h: h["grids"].extend(grids)), "refused", "over_budget", {}),
        "too_many_arrays": (many_arrays, "refused", "over_budget", {}),
        "header_past_cap": (_swap('"tick":5', '"tick":5' + " " * MAX_HEADER_BYTES), "refused", "bad_shape", {}),
    }


def _parity_edges() -> dict[str, Fixture]:
    """The delta round's parity holes (W-SF1, S4), and checks a later one used to hide (E-N3)."""
    swap = _swap
    raw_scale = _set_channel(0, "scale", [2, 1])
    return {
        "key_with_escaped_bom": (swap('"tick":', '"\\ufefftick":'), "refused", "unknown_field", {}),
        "kind_with_escaped_bom": (swap('"kind":"full"', '"kind":"\\ufefffull"'), "refused", "unknown_kind", {}),
        "grid_name_with_escaped_bom": (
            swap('"name":"cells"', '"name":"\\ufeffcells"'),
            "refused",
            "bad_identity_key",
            {},
        ),
        "raw_scale_and_unknown_dtype": (
            _edited(_both(raw_scale, _set_channel(1, "dtype", "u64"))),
            "refused",
            "unknown_kind",
            {},
        ),
        "raw_scale_and_bad_name": (
            _edited(_both(raw_scale, _set_channel(1, "name", "a:b"))),
            "refused",
            "bad_identity_key",
            {},
        ),
        "raw_scale_and_bad_of": (
            _edited(_both(raw_scale, lambda h: _array_entries(h)[2].update(of="a:b"))),
            "refused",
            "bad_identity_key",
            {},
        ),
        # checks a later one used to hide (delta review E-N3): each input breaks that rule alone
        "optional_raw_with_scale": (
            _edited(lambda h: _array_entries(h)[-1]["channel"].update(scale=[2, 1]), _extra(SOOT, bytes(8))),
            "refused",
            "bad_shape",
            {},
        ),
        "grid_shape_same_count": (_edited(lambda h: h["grids"][0].update(shape=[1, 2, 4])), "refused", "bad_shape", {}),
    }


def frames() -> dict[str, Fixture]:
    return {
        **_goldens(), **_pins(), **_header_json(), **_schema(), **_layout(), **_extension(), **_frame_edges(),
        **_parity_edges(), **_limit_edges(),
    }  # fmt: skip


LIMITS = {
    "max_grids": MAX_GRIDS, "max_tables": MAX_TABLES, "max_arrays": MAX_ARRAYS, "max_extent": MAX_EXTENT,
    "max_header_bytes": MAX_HEADER_BYTES, "max_name_chars": IDENTITY_KEY_CHARS, "max_depth": MAX_DEPTH,
    "int_max": JSON_INT_MAX, "max_text_bytes": MAX_TEXT_BYTES,
}  # fmt: skip


def server_messages() -> dict[str, Fixture]:
    """The server's own text messages, written by its encoder, as the client must read them (delta review W-N2)."""
    welcome_text = encode(welcome(session_id=1, role="guest", shape=SHAPE)).encode()
    return {"welcome": (welcome_text, "accepted", "", {})}


SETS: dict[str, tuple[Callable[[], dict[str, Fixture]], str, tuple[str, ...]]] = {
    "frames": (frames, "bin", _SEEN),
    "json": (json_texts, "json", _SEEN),
    "client": (client_messages, "json", ("python",)),
    "server": (server_messages, "json", ("godot",)),
}


def files() -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    manifest: dict[str, object] = {"format": FORMAT, "version": VERSION, "frame_cap": FRAME_CAP, "catalogue": V0_HASH}
    manifest["limits"] = LIMITS  # the client's constants are held to these (step 7 delta review S8)
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
