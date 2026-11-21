"""scripts/client_fixtures.py: the client's snapshot fixtures are the real alley, made by the engine's Scene, and
the committed files are exactly what the script makes, so a scene or format change can't leave them stale (§6.1,
EX-S13's staleness rule applied to the renderer's fixtures)."""

from __future__ import annotations

import gzip
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("client_fixtures", ROOT / "scripts" / "client_fixtures.py")
assert _spec is not None
assert _spec.loader is not None
cf = importlib.util.module_from_spec(_spec)
sys.modules["client_fixtures"] = cf
_spec.loader.exec_module(cf)


def test_the_committed_fixtures_are_what_the_script_makes():
    assert cf.stale(cf.OUT) == []
    assert cf.main(["--check"]) == 0


def test_a_changed_or_missing_fixture_is_stale(tmp_path, capsys):
    assert cf.main([], out=tmp_path) == 0
    assert cf.stale(tmp_path) == []
    (tmp_path / "alley_fire.bin.gz").write_bytes(b"x")
    (tmp_path / "alley_cold.json").unlink()
    assert sorted(cf.stale(tmp_path)) == ["alley_cold.json", "alley_fire.bin.gz"]
    assert cf.main(["--check"], out=tmp_path) == 1
    assert "alley_fire.bin.gz is stale" in capsys.readouterr().err


def _read(name: str) -> tuple[dict[str, object], bytes]:
    header = json.loads((cf.OUT / f"{name}.json").read_text())
    return header, gzip.decompress((cf.OUT / f"{name}.bin.gz").read_bytes())


def test_the_header_describes_the_data():
    header, data = _read("alley_fire")
    assert header["format"] == cf.FORMAT
    assert header["version"] == 0
    assert header["shape"] == [48, 40, 120]
    assert header["data_size"] == len(data) == 230400 * 6
    assert header["data_sha256"] == hashlib.sha256(data).hexdigest()
    assert header["data_gzip_sha256"] == hashlib.sha256((cf.OUT / "alley_fire.bin.gz").read_bytes()).hexdigest()
    assert header["regions"] == {"1": "floor", "2": "wall_south", "3": "wall_north", "4": "wall_end", "5": "crate",
                                 "6": "crate_far"}  # fmt: skip


def _channel(name: str, channel: str) -> np.ndarray:
    header, data = _read(name)
    spec = header["channels"][channel]  # type: ignore[index]
    dtype = "<u2" if spec["dtype"] == "u16" else "u1"
    raw = np.frombuffer(data[spec["offset"] : spec["offset"] + spec["size"]], dtype=dtype)
    return raw.reshape(48, 40, 120)  # [z, y, x]


def test_the_arrays_are_the_alley_with_x_fastest():
    material = _channel("alley_cold", "material")
    assert material[0, 0, 0] == 1
    assert material[5, 20, 5] == 0  # floor at the origin, air over the pavement
    assert material[6, 28, 62] == 4  # wood in the crate at x 6.2, y 2.8, z 0.6 m
    assert material[20, 2, 30] == 1
    assert material[20, 2, 5] == 0  # wall_south starts at x 1.2 m, not 0.5
    region = _channel("alley_cold", "region")
    assert region[6, 28, 62] == 5
    assert region[6, 10, 92] == 6


def test_the_fire_is_where_the_docstring_says_and_the_cold_alley_has_none():
    for channel in ("crack", "surface_glow", "burning"):
        assert not _channel("alley_cold", channel).any()
    crack, glow, burning = (_channel("alley_fire", c) for c in ("crack", "surface_glow", "burning"))
    assert crack[6, 28, 60] == 64
    assert crack[6, 28, 65] == 254  # the ramp over the crate
    assert glow[9, 10, 92] == round((1400 - 525) * 255 / 975)
    assert glow[4, 8, 92] == round((600 - 525) * 255 / 975)
    assert glow[6, 10, 92] == 0  # inside crate_far: not envelope
    assert burning[3, 24:30, 104:110].all()
    assert not burning[:, :, :100].any()
    assert not (glow.astype(bool) & burning.astype(bool)).any()  # flames apart from the glow mask
