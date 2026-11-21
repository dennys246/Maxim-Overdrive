"""The client's snapshot fixtures: cell state the renderer draws without a live server (client_rendering.md §6.1).

Protocol v0 (step 7) isn't frozen, so these are **not** wire frames. They carry the channels the renderer reads, in a
plain container a client test loader reads (``client/tests/support/snapshot_fixture.gd``), and every field they
assume is named in ``client/tests/fixtures/snapshots/FIELDS.md`` for step 7 to confirm or change.

The geometry is the real alley (tile_and_client.md §1.1), built by the engine's own ``Scene`` at the 0.1 m truth, so
material and region cells are what the server holds. The fire channels are hand-placed, as §6.1's renderer goldens
are: a crack ramp over the crate and a patch of ``wall_north``, a glow ramp over ``crate_far``'s envelope, and
flames on a floor patch of their own. They exercise the shader; they are not a physical fire.

Arrays are ``[nz, ny, nx]`` in C order, x fastest, so one z-slice is one Godot ``Image`` row by row. The engine's grid
is indexed ``[x, y, z]``; this transposes it, as step 7's encoder will have to.

Run: ``python scripts/client_fixtures.py`` writes them; ``--check`` exits 1 when a committed file differs.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from maxim_overdrive.data import materials
from simcore.core.grid import MaterialGrid
from simcore.core.scene import SCENE_VERSION, Scene

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "client" / "tests" / "fixtures" / "snapshots"
FORMAT = "overdrive-client-snapshot-fixture"
VERSION = 0
CELL_M = 0.1
# surface_glow's calibration as client_rendering.md §4.2 gives it: T = 525 °C + (975/255) °C per count.
GLOW_OFFSET_C, GLOW_SCALE_NUM, GLOW_SCALE_DEN = 525, 975, 255
CHANNELS = (("material", "u8"), ("region", "u16"), ("crack", "u8"), ("surface_glow", "u8"), ("burning", "u8"))

PRIMITIVES: tuple[dict[str, object], ...] = tuple(
    {"kind": "box", "name": name, "material": material, "min_m": lo, "max_m": hi}
    for name, material, lo, hi in (
        ("floor", "concrete", [0.0, 0.0, 0.0], [12.0, 4.0, 0.4]),
        ("wall_south", "concrete", [1.2, 0.0, 0.4], [12.0, 0.4, 4.4]),
        ("wall_north", "concrete", [1.2, 3.6, 0.4], [12.0, 4.0, 4.4]),
        ("wall_end", "concrete", [11.6, 0.4, 0.4], [12.0, 3.6, 4.4]),
        ("crate", "wood", [6.0, 2.6, 0.4], [6.6, 3.2, 1.0]),
        ("crate_far", "wood", [9.0, 0.8, 0.4], [9.6, 1.4, 1.0]),
    )
)
ALLEY = {"version": SCENE_VERSION, "extent_m": [12.0, 4.0, 4.8], "ambient_c": 15.0, "primitives": list(PRIMITIVES)}
# The player where the exit script kindles the crate (tile §6.2, tick 57), and a second body whose axis sits on
# wall_north's face, half inside it: the depth golden (§5.3, CR-S1). Feet on the floor's top, 0.4 m.
ACTORS = ({"id": 1, "pos_mm": [5500, 2925, 400]}, {"id": 2, "pos_mm": [8000, 3600, 400]})

U8 = NDArray[np.uint8]


def alley() -> tuple[MaterialGrid, dict[str, int]]:
    """The alley at the 0.1 m truth, and region ids 1, 2, ... in authoring order (0: no region)."""
    grid = Scene.from_dict(ALLEY).build(materials(), dx_m=CELL_M)
    ids = {str(p["name"]): i + 1 for i, p in enumerate(PRIMITIVES)}
    return grid, ids


def wire_order(a: NDArray[np.generic]) -> NDArray[np.generic]:
    """``[x, y, z]`` (the grid) to ``[z, y, x]`` in C order (the fixture), so x is fastest."""
    return np.ascontiguousarray(np.transpose(a, (2, 1, 0)))


def region_cells(grid: MaterialGrid, ids: dict[str, int]) -> NDArray[np.uint16]:
    region = np.zeros(grid.shape, dtype=np.uint16)
    for name, rid in ids.items():
        region[grid.regions[name].cells] = rid
    return region


def exposed(solid: NDArray[np.bool_]) -> NDArray[np.bool_]:
    """Solid cells with an air face-neighbour, the domain's edge counting as closed."""
    padded = np.pad(solid, 1, constant_values=True)
    open_face = np.zeros(solid.shape, dtype=np.bool_)
    for axis in range(3):
        for shift in (-1, 1):
            open_face |= ~np.roll(padded, shift, axis=axis)[1:-1, 1:-1, 1:-1]
    out: NDArray[np.bool_] = solid & open_face
    return out


def fire_channels(grid: MaterialGrid) -> tuple[U8, U8, U8]:
    """crack, surface_glow and burning, in grid order ``[x, y, z]``."""
    crack, glow, burning = (np.zeros(grid.shape, dtype=np.uint8) for _ in range(3))
    crate = grid.regions["crate"].cells
    x = np.arange(grid.shape[0])[:, None, None]
    # A ramp from c = 64/255 (0.25) at the crate's west column to 254/255 at its east one, 38 counts per column.
    crack[crate] = np.broadcast_to(np.clip(64 + (x - 60) * 38, 64, 255), grid.shape)[crate]
    crack[70:80, 36:40, 4:16] = 128  # wall_north, x 7.0-8.0 m, its whole thickness, z 0.4-1.6 m: c = 0.5
    far = grid.regions["crate_far"].cells & exposed(grid.material != 0)
    z = np.arange(grid.shape[2])[None, None, :]
    # The envelope from 600 °C at its foot to 1,400 °C at its top: g = (T - 525) * 255 / 975.
    temp_c = 600 + (z - 4) * (800 / 5)
    glow[far] = np.broadcast_to(np.round((temp_c - GLOW_OFFSET_C) * GLOW_SCALE_DEN / GLOW_SCALE_NUM), grid.shape)[far]
    # Flames on a floor patch of their own (x 10.4-11.0, y 2.4-3.0, the floor's top layer), away from the crack and
    # glow masks: on crate_far they lit the glow mask by themselves, and the glow check passed with glow off.
    burning[104:110, 24:30, 3] = 191
    return crack, glow, burning


def arrays(*, fire: bool) -> tuple[dict[str, NDArray[np.generic]], dict[str, int], tuple[int, int, int]]:
    grid, ids = alley()
    zeros = np.zeros(grid.shape, dtype=np.uint8)
    crack, glow, burning = fire_channels(grid) if fire else (zeros, zeros, zeros)
    raw: dict[str, NDArray[np.generic]] = {"material": grid.material, "region": region_cells(grid, ids)}
    raw |= {"crack": crack, "surface_glow": glow, "burning": burning}
    nx, ny, nz = grid.shape
    return {name: wire_order(a) for name, a in raw.items()}, ids, (nz, ny, nx)


def encode(name: str, *, fire: bool) -> tuple[str, bytes]:
    """The fixture's JSON header and its gzip-compressed arrays."""
    data, ids, shape = arrays(fire=fire)
    blob, channels = bytearray(), {}
    for channel, dtype in CHANNELS:
        raw = data[channel].astype("<u2" if dtype == "u16" else "u1").tobytes()
        channels[channel] = {"dtype": dtype, "offset": len(blob), "size": len(raw)}
        blob += raw
    header = {
        "format": FORMAT,
        "version": VERSION,
        "shape": list(shape),
        "cell_m": CELL_M,
        "materials": {name: m.id for name, m in materials().by_name.items()},
        "regions": {str(rid): region for region, rid in ids.items()},
        "glow": {"offset_c": GLOW_OFFSET_C, "scale_num": GLOW_SCALE_NUM, "scale_den": GLOW_SCALE_DEN},
        "channels": channels,
        "actors": list(ACTORS),
        "data": f"{name}.bin.gz",
        "data_size": len(blob),
        "data_sha256": hashlib.sha256(blob).hexdigest(),
    }
    compressed = gzip.compress(bytes(blob), mtime=0)
    header["data_gzip_sha256"] = hashlib.sha256(compressed).hexdigest()
    return json.dumps(header, indent=1, sort_keys=True) + "\n", compressed


FIXTURES = {"alley_cold": False, "alley_fire": True}


def files() -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    for name, fire in FIXTURES.items():
        header, blob = encode(name, fire=fire)
        out[f"{name}.json"], out[f"{name}.bin.gz"] = header.encode(), blob
    return out


def stale(directory: Path) -> list[str]:
    """The fixture files that are missing from ``directory`` or differ from what this script makes."""
    return [name for name, content in files().items() if not (directory / name).is_file()
            or (directory / name).read_bytes() != content]  # fmt: skip


def main(argv: list[str] | None = None, *, out: Path = OUT) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="exit 1 when a committed fixture differs")
    args = parser.parse_args(argv)
    if args.check:
        found = stale(out)
        for name in found:
            print(f"client_fixtures: {name} is stale; rerun scripts/client_fixtures.py", file=sys.stderr)
        return 1 if found else 0
    out.mkdir(parents=True, exist_ok=True)
    for name, content in files().items():
        (out / name).write_bytes(content)
    print(f"client_fixtures: wrote {len(FIXTURES)} fixtures to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
