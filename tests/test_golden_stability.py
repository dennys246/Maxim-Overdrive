"""scripts/golden_stability.py: the stick-stability measure judges a renderer against an ideal line at the same
geometry, passes the ideal itself, fails a hard-edged line, and bins and drops ends as step 8's checklist fixes."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from PIL import Image

from tests.test_golden_compare import gcmp

assert gcmp is not None  # registered as golden_compare, which golden_stability imports

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("golden_stability", ROOT / "scripts" / "golden_stability.py")
assert _spec is not None
assert _spec.loader is not None
gs = importlib.util.module_from_spec(_spec)
sys.modules["golden_stability"] = gs
_spec.loader.exec_module(gs)

SHAPE = (120, 200)
WIDTH = 2.0  # the 2 px floor


def _axes(steps: int = 8) -> list[Any]:
    """A stick at about 33 degrees (the golden camera's projected angle), moved k/8 px on both screen axes."""
    return [gs.Axis(20.0 + k / steps, 30.0 + k / steps, 180.0 + k / steps, 90.0 + k / steps) for k in range(steps)]


def test_the_ideal_line_meets_its_own_bar():
    axes = _axes()
    frames = [gs.ideal_coverage(SHAPE, a, WIDTH) for a in axes]
    rendered, ideal = gs.stability(frames, axes, WIDTH)
    assert rendered == pytest.approx(ideal)
    assert gs.passes(rendered, ideal)


@pytest.mark.parametrize("width", [1.0, 1.44, 2.0, 2.5])
def test_a_hard_edged_line_crawls_beyond_the_ideal_but_only_near_the_bar(width):
    # Centre sampling, no anti-aliasing: each pixel is in or out, so coverage per bin jumps as the stick moves.
    # Measured 1.9-2.1x the ideal at these widths, about the bar itself: at full resolution the check alone does not
    # catch anti-aliasing switched off (the rig tier's hard-edged rods measured 1.16-2.12x); the laptop tier's
    # 5.8-5.9x does. The owner's question (fuel_antialiasing.md item 1); this test states the weakness, not a bar.
    axes = _axes()
    frames = [(gs.ideal_coverage(SHAPE, a, width) >= 0.5).astype(np.float64) for a in axes]
    rendered, ideal = gs.stability(frames, axes, width)
    assert 1.5 * ideal < rendered < 2.5 * ideal


def test_the_ideal_covers_the_stick_area():
    axis = gs.Axis(10.5, 10.5, 110.5, 10.5)
    cover = gs.ideal_coverage(SHAPE, axis, WIDTH)
    assert cover.sum() == pytest.approx(100.0 * WIDTH, rel=0.01)
    assert cover.max() == pytest.approx(1.0)


def test_bins_are_four_pixels_along_the_axis_with_two_dropped_at_each_end():
    axis = gs.Axis(10.0, 50.0, 50.0, 50.0)  # 40 px: ten bins, six kept
    cover = gs.ideal_coverage(SHAPE, axis, WIDTH)
    bins = gs.bin_coverage(cover, axis, WIDTH)
    assert len(bins) == 40 // int(gs.BIN_PX) - 2 * gs.END_BINS
    assert bins == pytest.approx(np.full(len(bins), gs.BIN_PX * WIDTH), rel=0.02)


def test_the_spread_is_max_minus_min_over_the_mean_at_the_95th_percentile():
    same = [np.array([1.0, 2.0, 4.0])] * 3
    assert gs.spread_statistic(same) == 0.0
    varied = [np.array([1.0, 2.0]), np.array([3.0, 2.0])]
    # bin 0: (3 - 1) / 2 = 1; bin 1: 0. The 95th percentile of [1, 0] is 0.95.
    assert gs.spread_statistic(varied) == pytest.approx(0.95)


def test_an_empty_bin_never_divides_by_zero():
    assert gs.spread_statistic([np.array([0.0, 1.0]), np.array([0.0, 1.0])]) == 0.0


def test_the_bar_is_twice_the_ideal():
    assert gs.passes(0.2, 0.1)
    assert not gs.passes(0.2001, 0.1)


def _stability_frames(directory: Path, *, flicker: bool, keys: tuple[str, ...] = gs.KEYS) -> None:
    """stability_check.tscn's output: for each tier and zoom, 8 frames of a 2 px stick moved k/8 px, ideal, or
    flickering on laptop-30 (drawn at alternate offsets only, the crawl at its worst)."""
    shape, width = (120, 200), 2.0
    ends = [[20.0 + k / 8, 30.0 + k / 8, 180.0 + k / 8, 90.0 + k / 8] for k in range(gs.OFFSETS)]
    for key in keys:
        for k, e in enumerate(ends):
            cover = gs.ideal_coverage(shape, gs.Axis(*e), width)
            if flicker and key == "laptop-30":
                cover = cover * (k % 2)
            grey = np.round(cover * 255).astype(np.uint8)
            Image.fromarray(np.stack([grey] * 3, axis=-1)).save(directory / f"stab-{key}-{k}.png")
    meta = {key: {"ends": ends, "drawn_px": width} for key in keys}
    (directory / "stability.json").write_text(json.dumps(meta))


def test_the_stability_check_passes_an_ideal_stick_and_fails_a_flickering_one(tmp_path):
    _stability_frames(tmp_path, flicker=False)
    assert gs.findings(tmp_path) == []
    _stability_frames(tmp_path, flicker=True)
    found = gs.findings(tmp_path)
    assert len(found) == 1
    assert found[0].startswith("stick stability (laptop-30): ")


def test_a_stability_record_that_is_missing_partial_or_short_is_a_finding(tmp_path):
    assert gs.findings(tmp_path) == [f"stick stability: no {tmp_path / 'stability.json'}"]
    _stability_frames(tmp_path, flicker=False, keys=("laptop-30",))
    assert gs.findings(tmp_path)[0].startswith("stick stability: measured ['laptop-30'], not")
    (tmp_path / "stability.json").write_text("{}")
    assert gs.findings(tmp_path)[0].startswith("stick stability: measured [], not")  # nothing measured
    _stability_frames(tmp_path, flicker=False)
    (tmp_path / "stab-rig-30-3.png").unlink()
    assert gs.findings(tmp_path) == ["stick stability (rig-30): 8 offsets, missing ['stab-rig-30-3.png']"]


def test_a_failing_stick_with_an_ideal_of_zero_is_reported_not_divided(tmp_path, monkeypatch):
    _stability_frames(tmp_path, flicker=False)
    monkeypatch.setattr(gs, "stability", lambda images, axes, width: (0.5, 0.0))
    found = gs.findings(tmp_path)
    assert len(found) == 4
    assert all("against an ideal of 0" in f for f in found)


def test_the_stability_keys_are_what_the_scene_draws():
    source = (ROOT / "client" / "tests" / "stability_check.gd").read_text()
    tiers = source.split('const TIERS: Array[String] = ["')[1].split('"]')[0].split('", "')
    zooms = source.split("const PX_PER_M: Array[float] = [")[1].split("]")[0].split(", ")
    offsets = int(source.split("const OFFSETS: int = ")[1].split()[0])
    assert tuple(sorted(f"{t}-{int(float(z))}" for t in tiers for z in zooms)) == gs.KEYS
    assert offsets == gs.OFFSETS
