"""scripts/fuel_fixtures.py: the client's fuel fixture carries client_objects.md §3's tables column for column, follows
fire_solid §1.2's segment rule, starts every visible object past half-float exactness, and the committed files are
exactly what the script makes (the staleness rule the cell fixtures follow)."""

from __future__ import annotations

import gzip
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

import numpy as np
import pytest

from simcore.protocol import encoding as wire_encoding

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("fuel_fixtures", ROOT / "scripts" / "fuel_fixtures.py")
assert _spec is not None
assert _spec.loader is not None
ff = importlib.util.module_from_spec(_spec)
sys.modules["fuel_fixtures"] = ff
_spec.loader.exec_module(ff)


def test_the_committed_fixture_is_what_the_script_makes():
    assert not ff.stale(ff.OUT)
    assert ff.main(["--check"]) == 0


def test_a_changed_or_missing_fixture_is_stale(tmp_path, capsys):
    assert ff.main([], out=tmp_path) == 0
    assert not ff.stale(tmp_path)
    (tmp_path / f"{ff.NAME}.bin.gz").write_bytes(gzip.compress(b"x", mtime=0))
    assert ff.stale(tmp_path) == [ff.NAME]
    assert ff.main(["--check"], out=tmp_path) == 1
    assert "is stale" in capsys.readouterr().err
    (tmp_path / f"{ff.NAME}.json").unlink()
    assert ff.stale(tmp_path)


def test_another_zlib_compressing_the_same_columns_is_current(tmp_path):
    assert ff.main([], out=tmp_path) == 0
    data = tmp_path / f"{ff.NAME}.bin.gz"
    other = gzip.compress(gzip.decompress(data.read_bytes()), compresslevel=1, mtime=0)
    data.write_bytes(other)
    header = json.loads((tmp_path / f"{ff.NAME}.json").read_text())
    header["data_gzip_sha256"] = hashlib.sha256(other).hexdigest()
    (tmp_path / f"{ff.NAME}.json").write_text(json.dumps(header, indent=1, sort_keys=True) + "\n")
    assert not ff.stale(tmp_path)


@pytest.mark.parametrize(("length_m", "count"), [(0.14, 7), (0.28, 14), (0.56, 28), (1.12, 56), (0.6, 30), (0.03, 2)])
def test_segments_count_by_fire_solids_integer_rule(length_m, count):
    # A plain f64 ceiling of 0.14 / 0.02 gives 8: these are the lengths it miscounts (delta 1, five lenses B1).
    assert ff.segment_count(length_m) == count


def test_every_table_carries_client_objects_columns_with_their_dtypes_and_encodings():
    header, blob = ff.content()
    assert set(header["tables"]) == set(ff.TABLES)
    for table, spec in ff.TABLES.items():
        got = header["tables"][table]
        assert list(got["columns"]) == list(spec)
        for column, (dtype, unit, encoding) in spec.items():
            entry = got["columns"][column]
            assert (entry["dtype"], entry["unit"], entry["encoding"]) == (dtype, unit, encoding)
            assert entry["size"] == got["rows"] * np.dtype(ff.NUMPY[dtype]).itemsize
            assert ("scale_den" in entry) == (encoding == ff.LINEAR)
    assert header["data_size"] == len(blob)


def _column(header, blob, table, column):
    entry = header["tables"][table]["columns"][column]
    raw = blob[entry["offset"] : entry["offset"] + entry["size"]]
    return np.frombuffer(raw, dtype=ff.NUMPY[entry["dtype"]])


def test_every_visible_object_starts_past_half_float_exactness():
    header, blob = ff.content()
    counts = _column(header, blob, "objects", "segment_count").astype(int)
    first_rows = np.concatenate([[0], np.cumsum(counts)[:-1]])
    visible = len(ff.visible())
    assert (first_rows[-visible:] > ff.HALF_EXACT_ROWS).all()
    assert counts.sum() == header["tables"]["segments"]["rows"]


def test_segment_keys_run_object_by_object_from_zero():
    header, blob = ff.content()
    counts = _column(header, blob, "objects", "segment_count").astype(int)
    oids = _column(header, blob, "objects", "object_id").astype(int)
    assert (_column(header, blob, "segments", "object_id") == np.repeat(oids, counts)).all()
    assert (_column(header, blob, "segments", "seg") == np.concatenate([np.arange(n) for n in counts])).all()


def test_the_ramps_reach_the_states_the_checks_read():
    header, blob = ff.content()
    thickness = _column(header, blob, "segments", "thickness_fraction")
    ignited = _column(header, blob, "segments", "ignited_fraction")
    char = _column(header, blob, "segments", "char_fraction")
    temperature = _column(header, blob, "segments", "surface_temperature_c").astype(float)
    # rod_burnt's run of ten segments, and rod_gap's four, which report ignition with no surface left
    assert (thickness == 0).sum() == 14
    # rod_lit's ten, rod_gap's four burnt-through ones and all twenty of rod_spent's (burnt out, still reporting it)
    assert (ignited == 255).sum() == 34
    assert set(np.unique(ignited)) == {0, 255}
    assert char.max() == 255
    assert temperature.max() == pytest.approx(1500.0, abs=1.0)
    assert (_column(header, blob, "objects", "state") == 1).sum() == 1


def test_fuel_regions_follow_the_alleys_and_are_each_named():
    header, _ = ff.content()
    ids = sorted(int(i) for i in header["regions"])
    assert ids[0] == ff.alley_region_count() + 1
    assert ids == list(range(ids[0], ids[0] + len(ids)))


def test_linear_columns_round_to_the_nearest_255th_and_clip():
    raw = ff.column_bytes([0.0, 0.5, 1.0, 1.7, -0.2], "u8", ff.LINEAR)
    assert list(raw) == [0, 128, 255, 255, 0]


def test_the_stick_fixture_is_the_stability_measures_stick():
    header, blob = ff.content(ff.STICK)
    assert header["tables"]["objects"]["rows"] == 1
    entry = header["tables"]["rods"]["columns"]["radius_m"]
    radius = np.frombuffer(blob[entry["offset"] : entry["offset"] + entry["size"]], dtype="<f4")
    assert radius.tolist() == [pytest.approx(0.01)]
    assert header["tables"]["segments"]["rows"] == 50


def test_the_recipe_palette_colours_every_recipe_the_fixture_names():
    # Review N4: the vocabulary is in the fixture script and in the client's palette, and nothing else ties them; a
    # recipe without a colour draws magenta and only push_errors at golden time.
    palette = (ROOT / "client" / "game" / "recipe_palette.tres").read_text()
    coloured = set(re.findall(r'^"([a-z_]+)": Color\(', palette, flags=re.MULTILINE))
    assert coloured == set(ff.RECIPES)


def test_the_fuel_glow_starts_and_spans_as_the_cells_glow():
    # Review N5: the fuel shader's glow constants copy the encoder's until step 7 deletes the encoder's (client_objects
    # §5.1); until then a hot wall and a hot stick at one temperature must glow alike.
    shader = (ROOT / "client" / "addons" / "engine" / "render" / "fuel_object.gdshaderinc").read_text()
    start_match = re.search(r"const float FUEL_GLOW_START_C = ([\d.]+);", shader)
    span_match = re.search(r"const float FUEL_GLOW_SPAN_C = ([\d.]+);", shader)
    assert start_match
    assert span_match
    start, span = float(start_match.group(1)), float(span_match.group(1))
    assert (start, start + span) == (wire_encoding.GLOW_START_C, wire_encoding.GLOW_FULL_C)
