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
# The stick-stability measure's stick (step 8's checklist): one 20 mm rod 1 m long, alone.
STICK = "fuel_stick"
FORMAT = "overdrive-client-fuel-fixture"
VERSION = 0
ALLEY_SCENE = ROOT / "tests" / "fixtures" / "scenes" / "alley_box.yaml"
SEGMENT_M = 0.02
FLOOR_TOP_M = 0.4
KINDS = {"rod": 0, "slab": 1}
RECIPES = {"pine_rod": 1, "pine_slab": 2}
# Rows past which half-float instance data loses whole numbers (client_objects.md §2).
HALF_EXACT_ROWS = 2048
# client_objects.md §3.3's clip of surface_temperature_c, which a producer applies and the client refuses outside of:
# the fixtures stand in for the server's fuel encoder (step 7) until it exists.
TEMPERATURE_CLIP_C = (-273.0, 6000.0)

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


Vec = tuple[float, float, float]


def rod(
    region: str, origin: Vec, length_m: float, radius_m: float, *, state: int = 0, along_y: bool = False,
    axis: Vec | None = None,
) -> Fuel:  # fmt: skip
    """A rod from ``origin`` along world x (or y, or ``axis``), its axis at ``origin``'s height."""
    geometry = dict(zip(("origin_x_m", "origin_y_m", "origin_z_m"), origin, strict=True))
    axis = axis or ((0.0, 1.0, 0.0) if along_y else (1.0, 0.0, 0.0))
    geometry |= dict(zip(("axis_x", "axis_y", "axis_z"), axis, strict=True))
    geometry |= {"length_m": length_m, "radius_m": radius_m}
    segments = [Segment() for _ in range(segment_count(length_m))]
    return Fuel("rod", "pine_rod", region, geometry, state=state, segments=segments)


def slab(
    region: str, origin: Vec, length_m: float, width_m: float, thickness_m: float, *,
    axes: tuple[Vec, Vec] = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
) -> Fuel:  # fmt: skip
    """A slab from its corner ``origin``, length along ``axes[0]`` and width along ``axes[1]`` (by default world x and
    y, on the floor), so its segmented face (fire_solid §1.1), at thickness along their cross product, is the top."""
    geometry = dict(zip(("origin_x_m", "origin_y_m", "origin_z_m"), origin, strict=True))
    geometry |= dict(zip(("length_axis_x", "length_axis_y", "length_axis_z"), axes[0], strict=True))
    geometry |= dict(zip(("width_axis_x", "width_axis_y", "width_axis_z"), axes[1], strict=True))
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
    # Burnt out while its char is still hot and reporting ignition: §4.3 draws it with no glow and no flame, so the
    # burnout branch changes pixels (review S1, S2) and the burnout check can see it deleted.
    spent = rod("rod_spent", (2.4, 1.6, FLOOR_TOP_M + 0.03), 0.4, 0.03, state=1)
    for s in spent.segments:
        s.char, s.temperature_c, s.ignited = 1.0, 1200.0, 1.0
    # Cold and live, but its burnt-through run reports ignition: a flame there would rise from no surface (§4.3).
    gap = rod("rod_gap", (2.4, 2.0, FLOOR_TOP_M + 0.03), 0.4, 0.03)
    for k, s in enumerate(gap.segments):
        if 8 <= k < 12:
            s.thickness, s.ignited = 0.0, 1.0
    # A hot thin stick lying across a cold log, the log later in instance order: where they cross the stick, in front,
    # must show (review C-S1: a floored stick wrote no depth, and a rod drawn after it overwrote it).
    # It crosses 0.15 m from the log's centre and 0.1 m from the stick's: a sort by centre would put the stick behind
    # the log once their centres part by about 0.065 m along the view (review A1, CR-1, E-S1).
    cross = rod("stick_cross", (3.05, 1.5, FLOOR_TOP_M + 0.1 + 0.005), 0.5, 0.005, along_y=True)
    for s in cross.segments:
        s.temperature_c = 1500.0
    log = rod("log_cross", (2.95, 1.85, FLOOR_TOP_M + 0.05), 0.5, 0.05)
    return [hot, burnt, lit, plank, spent, gap, cross, log, *leaning()]


# The golden camera's direction back toward the viewer (client iso_camera.gd: yaw 45 deg, elevation 40 deg), so a
# slab can face it: cos 40 / sqrt 2 across x and -y, sin 40 up.
TOWARD_CAMERA: Vec = (0.5416752204197017, -0.5416752204197017, 0.6427876096865393)


def leaning() -> list[Fuel]:
    """A 20 mm plank leaning 50 deg to face the golden camera, a hot splinter resting across its face: the slab floor
    must not bury it (review C-S4). Face-on, the edge sine is fuel_slab.gdshader's floor, 0.25, so at 72 px/m the 2 px
    floor grows the plank to 27.8 / 0.25 = 111 mm. Grown symmetrically, its face would come 45.6 mm toward the camera
    and cover the splinter, whose mesh, widened by the floor and one rendered pixel, reaches 2 + 13.9 + 13.9 = 29.8 mm
    off the face on rig and max and 2 + 13.9 + 27.8 = 43.7 mm on laptop, a 1.9 mm margin there (derived; review CR-4;
    the measured deletion is caught on every tier). Seen from 40 deg, a flat plank's sine is 0.77 and the rise 8 mm,
    under any floored rod's 13.9 mm half-width: that view can't see the deletion."""
    along: Vec = (0.7071067811865476, 0.7071067811865476, 0.0)
    n = TOWARD_CAMERA
    across: Vec = (-n[2] * along[1], n[2] * along[0], n[0] * along[1] - n[1] * along[0])  # n x along, along level
    plank = slab("slab_leaning", (3.0, 2.5, FLOOR_TOP_M), 0.3, 0.2, 0.02, axes=(along, across))
    lift = 0.02 + 0.002  # the plank's thickness and the splinter's radius, along the face's normal
    start = tuple(o + across[i] * 0.1 + along[i] * 0.02 + n[i] * lift for i, o in enumerate((3.0, 2.5, FLOOR_TOP_M)))
    resting = rod("stick_on_slab", (start[0], start[1], start[2]), 0.26, 0.002, axis=along)
    for s in resting.segments:
        s.temperature_c = 1500.0
    return [plank, resting]


def objects() -> list[Fuel]:
    return padding() + visible()


def objects_next() -> list[Fuel]:
    """fuel_ramp's next frame: the same structure, stick_glow's ramp reversed. Drawn after fuel_ramp, it reaches the
    client as a steady frame (no rebuild), so the glow check on it holds the in-place segment upload (review E-N2)."""
    fuel = objects()
    hot = next(f for f in fuel if f.region == "stick_glow")
    for s, t in zip(hot.segments, reversed([s.temperature_c for s in hot.segments]), strict=True):
        s.temperature_c = t
    return fuel


def stick() -> list[Fuel]:
    return [rod("stick", (4.5, 2.0, FLOOR_TOP_M + 0.01), 1.0, 0.01)]


NEXT = f"{NAME}_next"
FIXTURES = {NAME: objects, NEXT: objects_next, STICK: stick}


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


def content(name: str = NAME) -> tuple[dict[str, object], bytes]:
    """The fixture's header, without the compressed file's digest, and its columns end to end."""
    fuel = FIXTURES[name]()
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
        "data": f"{name}.bin.gz",
        "data_size": len(blob),
        "data_sha256": hashlib.sha256(blob).hexdigest(),
    }
    return header, bytes(blob)


def files() -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    for name in FIXTURES:
        header, blob = content(name)
        compressed = gzip.compress(blob, mtime=0)
        header["data_gzip_sha256"] = hashlib.sha256(compressed).hexdigest()
        out[f"{name}.json"] = (json.dumps(header, indent=1, sort_keys=True) + "\n").encode()
        out[f"{name}.bin.gz"] = compressed
    return out


def stale(directory: Path) -> list[str]:
    """The fixtures in ``directory`` whose content differs from what this script makes (zlib builds differ in
    bytes, so the check is the header, the compressed file's own digest, and the arrays it inflates to)."""
    found = []
    for name in FIXTURES:
        header_path, data_path = directory / f"{name}.json", directory / f"{name}.bin.gz"
        if not (header_path.is_file() and data_path.is_file()):
            found.append(name)
            continue
        want, raw = content(name)
        got = json.loads(header_path.read_text())
        compressed = data_path.read_bytes()
        digest = got.pop("data_gzip_sha256", None)
        if got != want or digest != hashlib.sha256(compressed).hexdigest() or gzip.decompress(compressed) != raw:
            found.append(name)
    return found


def main(argv: list[str] | None = None, *, out: Path = OUT) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--check", action="store_true", help="exit 1 when the committed fixture differs")
    args = parser.parse_args(argv)
    if args.check:
        found = stale(out)
        for name in found:
            print(f"fuel_fixtures: {name} is stale; rerun scripts/fuel_fixtures.py", file=sys.stderr)
        return 1 if found else 0
    out.mkdir(parents=True, exist_ok=True)
    for name, body in files().items():
        (out / name).write_bytes(body)
    print(f"fuel_fixtures: wrote {len(FIXTURES)} fixtures to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
