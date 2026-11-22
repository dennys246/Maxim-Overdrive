"""The client's fuel fixture: fuel tables the object pass draws without a live server (client_objects.md §7.1).

Steps 6.0b and 7 (the fuel store, its view and the protocol) aren't built, so this is **not** a wire frame. It carries
`client_objects.md` §3's tables column for column (names, dtypes, units, encodings), in the same plain container as the
cell fixtures (``scripts/client_fixtures.py``), read by ``client/tests/support/fuel_fixture.gd`` into the
``FuelSnapshot`` seam step 7's decoder will fill.

The objects are hand-placed on the alley's floor, as the renderer goldens are (client_rendering.md §6.1). They exercise
§7.2's checks; they are not a physical fire. Before the visible objects come enough small rods to put every visible
object's first segment row past 2,048, where half-float instance data stops being exact (client_objects.md §2).

Run: ``python scripts/fuel_fixtures.py`` writes it; ``--check`` exits 1 when the committed files differ.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from simcore.adapters.loaders import read_yaml
from simcore.core.scene import Scene

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "client" / "tests" / "fixtures" / "fuel"
NAME = "fuel_ramp"
FORMAT = "overdrive-client-fuel-fixture"
VERSION = 0
ALLEY_SCENE = ROOT / "tests" / "fixtures" / "scenes" / "alley_box.yaml"
SEGMENT_M = 0.02
FLOOR_TOP_M = 0.4
KINDS = {"rod": 0, "slab": 1}
RECIPES = {"pine_rod": 1, "pine_slab": 2}
# Rows past which half-float instance data loses whole numbers (client_objects.md §2).
HALF_EXACT_ROWS = 2048

# client_objects.md §3.2 and §3.3: column -> (dtype, unit, encoding).
RAW, LINEAR = "raw", "linear"
TABLES: dict[str, dict[str, tuple[str, str, str]]] = {
    "objects": {
        "object_id": ("u32", "id", RAW),
        "recipe_id": ("u16", "id", RAW),
        "region_id": ("u16", "id", RAW),
        "kind": ("u8", "id", RAW),
        "state": ("u8", "id", RAW),
        "segment_count": ("u16", "id", RAW),
        "segment_length_m": ("f32", "m", RAW),
    },
    "rods": {
        "object_id": ("u32", "id", RAW),
        **{f"origin_{a}_m": ("f32", "m", RAW) for a in "xyz"},
        **{f"axis_{a}": ("f32", "ratio", RAW) for a in "xyz"},
        "length_m": ("f32", "m", RAW),
        "radius_m": ("f32", "m", RAW),
    },
    "slabs": {
        "object_id": ("u32", "id", RAW),
        **{f"origin_{a}_m": ("f32", "m", RAW) for a in "xyz"},
        **{f"length_axis_{a}": ("f32", "ratio", RAW) for a in "xyz"},
        **{f"width_axis_{a}": ("f32", "ratio", RAW) for a in "xyz"},
        "length_m": ("f32", "m", RAW),
        "width_m": ("f32", "m", RAW),
        "thickness_m": ("f32", "m", RAW),
    },
    "segments": {
        "object_id": ("u32", "id", RAW),
        "seg": ("u16", "id", RAW),
        "surface_temperature_c": ("f16", "celsius", RAW),
        "ignited_fraction": ("u8", "ratio", LINEAR),
        "thickness_fraction": ("u8", "ratio", LINEAR),
        "char_fraction": ("u8", "ratio", LINEAR),
    },
}
NUMPY = {"u8": "<u1", "u16": "<u2", "u32": "<u4", "f16": "<f2", "f32": "<f4"}


@dataclass
class Segment:
    temperature_c: float = 20.0
    ignited: float = 0.0
    thickness: float = 1.0
    char: float = 0.0


@dataclass
class Fuel:
    """One fuel object: its geometry row (per kind) and its segments' state, as client_objects.md §3 carries them."""

    kind: str
    recipe: str
    region: str
    geometry: dict[str, float]
    state: int = 0
    segments: list[Segment] = field(default_factory=list)


def segment_count(length_m: float) -> int:
    """fire_solid.md §1.2's rule: the ceiling of length / segment length on whole micrometres, in integers."""
    length_um, segment_um = round(length_m * 1e6), round(SEGMENT_M * 1e6)
    return -(-length_um // segment_um)


def rod(region: str, origin: tuple[float, float, float], length_m: float, radius_m: float, *, state: int = 0) -> Fuel:
    """A rod lying on the floor along world x, its axis at ``origin``'s height."""
    geometry = dict(zip(("origin_x_m", "origin_y_m", "origin_z_m"), origin, strict=True))
    geometry |= {"axis_x": 1.0, "axis_y": 0.0, "axis_z": 0.0, "length_m": length_m, "radius_m": radius_m}
    segments = [Segment() for _ in range(segment_count(length_m))]
    return Fuel("rod", "pine_rod", region, geometry, state=state, segments=segments)


def slab(region: str, origin: tuple[float, float, float], length_m: float, width_m: float, thickness_m: float) -> Fuel:
    """A slab on the floor, length along world x, width along y, so its segmented face (fire_solid §1.1) is the top."""
    geometry = dict(zip(("origin_x_m", "origin_y_m", "origin_z_m"), origin, strict=True))
    geometry |= {"length_axis_x": 1.0, "length_axis_y": 0.0, "length_axis_z": 0.0}
    geometry |= {"width_axis_x": 0.0, "width_axis_y": 1.0, "width_axis_z": 0.0}
    geometry |= {"length_m": length_m, "width_m": width_m, "thickness_m": thickness_m}
    return Fuel("slab", "pine_slab", region, geometry, segments=[Segment() for _ in range(segment_count(length_m))])


def padding() -> list[Fuel]:
    """Small cold rods in the alley's open west end, enough that every later object starts past row 2,048. Three
    columns of 0.6 m rods, 0.05 m apart and 0.04 m between rows, so none touches another (fire_solid §1.3)."""
    out: list[Fuel] = []
    rows = 0
    while rows <= HALF_EXACT_ROWS:
        i = len(out)
        origin = (1.4 + 0.65 * (i % 3), 0.5 + 0.04 * (i // 3), FLOOR_TOP_M + 0.01)
        out.append(rod("kindling_pile", origin, 0.6, 0.01))
        rows += len(out[-1].segments)
    return out


def visible() -> list[Fuel]:
    """The objects §7.2's checks read: each ramp on its own object, at the golden view."""
    hot = rod("stick_glow", (3.6, 1.4, FLOOR_TOP_M + 0.01), 1.0, 0.01)
    for k, s in enumerate(hot.segments):
        s.temperature_c = 20.0 + (1500.0 - 20.0) * k / (len(hot.segments) - 1)
    burnt = rod("rod_burnt", (3.6, 1.8, FLOOR_TOP_M + 0.05), 1.0, 0.05)
    for k, s in enumerate(burnt.segments):
        s.thickness, s.char = (0.0, 0.0) if 20 <= k < 30 else (1.0, k / (len(burnt.segments) - 1))
    lit = rod("rod_lit", (3.6, 2.3, FLOOR_TOP_M + 0.1), 1.0, 0.1)
    for k, s in enumerate(lit.segments):
        s.temperature_c, s.ignited = 600.0, (1.0 if 10 <= k < 20 else 0.0)
    plank = slab("slab_char", (2.4, 2.4, FLOOR_TOP_M), 0.5, 0.3, 0.02)
    for k, s in enumerate(plank.segments):
        s.char = k / (len(plank.segments) - 1)
    spent = rod("rod_spent", (2.4, 1.6, FLOOR_TOP_M + 0.03), 0.4, 0.03, state=1)
    for s in spent.segments:
        s.char = 1.0
    return [hot, burnt, lit, plank, spent]


def objects() -> list[Fuel]:
    return padding() + visible()


def alley_region_count() -> int:
    """The cell fixtures number the alley's regions 1, 2, ... in authoring order; fuel regions come after them."""
    scene = Scene.from_dict(read_yaml(ALLEY_SCENE))
    return sum(1 for p in scene.primitives if p.name)


def region_ids(fuel: list[Fuel]) -> dict[str, int]:
    """Each fuel region's id, after the alley's, in first-use order (fire_solid §1.3: each object names a region)."""
    out: dict[str, int] = {}
    for f in fuel:
        out.setdefault(f.region, alley_region_count() + 1 + len(out))
    return out


def columns(fuel: list[Fuel]) -> dict[str, dict[str, list[float]]]:
    """Every table's columns as plain lists, in key order (client_objects.md §3)."""
    regions = region_ids(fuel)
    tables: dict[str, dict[str, list[float]]] = {t: {c: [] for c in TABLES[t]} for t in TABLES}
    for oid, f in enumerate(fuel, start=1):
        row: dict[str, float] = {
            "object_id": oid,
            "recipe_id": RECIPES[f.recipe],
            "region_id": regions[f.region],
            "kind": KINDS[f.kind],
        }
        row |= {"state": f.state, "segment_count": len(f.segments), "segment_length_m": SEGMENT_M}
        for c in TABLES["objects"]:
            tables["objects"][c].append(row[c])
        geometry = tables["rods" if f.kind == "rod" else "slabs"]
        for c in geometry:
            geometry[c].append(oid if c == "object_id" else f.geometry[c])
        for k, s in enumerate(f.segments):
            seg: dict[str, float] = {"object_id": oid, "seg": k, "surface_temperature_c": s.temperature_c}
            seg |= {"ignited_fraction": s.ignited, "thickness_fraction": s.thickness, "char_fraction": s.char}
            for c in TABLES["segments"]:
                tables["segments"][c].append(seg[c])
    return tables


def column_bytes(values: list[float], dtype: str, encoding: str) -> bytes:
    """One column's little-endian bytes: raw as is, linear u8 fractions rounded to the nearest 1/255."""
    array = np.asarray(values, dtype=np.float64)
    if encoding == LINEAR:
        array = np.rint(np.clip(array, 0.0, 1.0) * 255.0)
    return array.astype(NUMPY[dtype]).tobytes()


def content() -> tuple[dict[str, object], bytes]:
    """The fixture's header, without the compressed file's digest, and its columns end to end."""
    fuel = objects()
    data, blob, tables = columns(fuel), bytearray(), {}
    for table, spec in TABLES.items():
        cols = {}
        for column, (dtype, unit, encoding) in spec.items():
            raw = column_bytes(data[table][column], dtype, encoding)
            entry = {"dtype": dtype, "unit": unit, "encoding": encoding, "offset": len(blob), "size": len(raw)}
            cols[column] = entry | ({"scale_num": 1, "scale_den": 255} if encoding == LINEAR else {})
            blob += raw
        tables[table] = {"rows": len(data[table]["object_id"]), "columns": cols}
    header = {
        "format": FORMAT,
        "version": VERSION,
        "kinds": KINDS,
        "recipes": RECIPES,
        "regions": {str(rid): name for name, rid in region_ids(fuel).items()},
        "tables": tables,
        "data": f"{NAME}.bin.gz",
        "data_size": len(blob),
        "data_sha256": hashlib.sha256(blob).hexdigest(),
    }
    return header, bytes(blob)


def files() -> dict[str, bytes]:
    header, blob = content()
    compressed = gzip.compress(blob, mtime=0)
    header["data_gzip_sha256"] = hashlib.sha256(compressed).hexdigest()
    return {
        f"{NAME}.json": (json.dumps(header, indent=1, sort_keys=True) + "\n").encode(),
        f"{NAME}.bin.gz": compressed,
    }


def stale(directory: Path) -> bool:
    """Whether the committed fixture differs in content from what this script makes (zlib builds differ in bytes,
    so the check is the header, the compressed file's own digest, and the arrays it inflates to)."""
    header_path, data_path = directory / f"{NAME}.json", directory / f"{NAME}.bin.gz"
    if not (header_path.is_file() and data_path.is_file()):
        return True
    want, raw = content()
    got = json.loads(header_path.read_text())
    compressed = data_path.read_bytes()
    digest = got.pop("data_gzip_sha256", None)
    return got != want or digest != hashlib.sha256(compressed).hexdigest() or gzip.decompress(compressed) != raw


def main(argv: list[str] | None = None, *, out: Path = OUT) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--check", action="store_true", help="exit 1 when the committed fixture differs")
    args = parser.parse_args(argv)
    if args.check:
        if stale(out):
            print(f"fuel_fixtures: {NAME} is stale; rerun scripts/fuel_fixtures.py", file=sys.stderr)
            return 1
        return 0
    out.mkdir(parents=True, exist_ok=True)
    for name, body in files().items():
        (out / name).write_bytes(body)
    print(f"fuel_fixtures: wrote {NAME} to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
