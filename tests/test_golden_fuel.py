"""scripts/golden_fuel.py: the fuel checks (client_objects.md §7.2) pass frames built to meet them and fail frames built
to miss them, on synthetic frames and footprints, so each check's logic is proved apart from Godot."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from tests.test_fuel_fixtures import ff
from tests.test_golden_measures import gm

ROOT = Path(__file__).resolve().parents[1]
assert ff is not None
assert gm is not None  # both registered under their module names, which golden_fuel imports
_spec = importlib.util.spec_from_file_location("golden_fuel", ROOT / "scripts" / "golden_fuel.py")
assert _spec is not None
assert _spec.loader is not None
gf = importlib.util.module_from_spec(_spec)
sys.modules["golden_fuel"] = gf
_spec.loader.exec_module(gf)

SHAPE = (120, 200)
SEG = gf.segments()
GREY, BRIGHT, DARK = (90, 90, 90), (220, 220, 220), (30, 30, 30)


def _footprints() -> np.ndarray:
    """Every segment row off-screen (zero length, which a strip skips), except the regions a test lays out."""
    return np.zeros((len(SEG.region), 5), dtype=np.float64)


def _lay(foot: np.ndarray, region: str, y: float, half: float = 2.0) -> None:
    """``region``'s segments end to end along screen row ``y``, 2 px each, from x = 10."""
    for k, r in enumerate(SEG.rows(region)):
        foot[r] = [10 + 2 * k, y, 12 + 2 * k, y, half]


def _paint(img: np.ndarray, foot: np.ndarray, rows: np.ndarray, colour: tuple[int, int, int]) -> None:
    img[gf.strip(SHAPE, foot[rows])] = colour


def _save(directory: Path, name: str, img: np.ndarray, foot: np.ndarray) -> None:
    Image.fromarray(img).save(directory / f"{name}.png")
    (directory / f"{name}.segments.json").write_text(json.dumps(foot.tolist()))


def _frames(
    directory: Path, tier: str, *, burning: bool = True, burnt_hole: bool = True, flames: bool = True,
    spent_glows: bool = False, stick_hidden: bool = False,
) -> None:  # fmt: skip
    """One tier's four fuel frames: everything laid out passes unless a flag removes what a check needs."""
    foot = _footprints()
    for region, y in (
        ("rod_lit", 20), ("rod_burnt", 40), ("slab_char", 60), ("stick_glow", 80), ("rod_spent", 96), ("rod_gap", 110),
    ):  # fmt: skip
        _lay(foot, region, y)
    _lay(foot, "log_cross", 70, half=4.0)  # beside slab_char's row, its middle crossed by the stick
    for k, r in enumerate(SEG.rows("stick_cross")):
        foot[r] = [40, 62 + 0.6 * k, 40, 62.6 + 0.6 * k, 1.0]
    mask = np.zeros((*SHAPE, 3), dtype=np.uint8)
    shaded = np.zeros((*SHAPE, 3), dtype=np.uint8)
    every = np.flatnonzero(foot[:, 2] != foot[:, 0])
    keep = every if not burnt_hole else np.setdiff1d(every, SEG.rows("rod_burnt", SEG.thickness == 0))
    _paint(mask, foot, keep, (255, 255, 255))
    _paint(shaded, foot, keep, GREY)
    if burning:
        _paint(shaded, foot, SEG.rows("rod_lit", SEG.ignited == 255), BRIGHT)
    for region in ("rod_burnt", "slab_char"):
        _paint(shaded, foot, SEG.rows(region, (SEG.char >= 128) & (SEG.thickness == 255)), DARK)
    _paint(shaded, foot, SEG.rows("stick_glow", SEG.temperature_c >= gf.HOT_C), BRIGHT)
    _paint(shaded, foot, SEG.rows("rod_spent"), BRIGHT if spent_glows else DARK)
    _paint(shaded, foot, SEG.rows("log_cross"), DARK)
    if not stick_hidden:
        _paint(shaded, foot, SEG.rows("stick_cross"), BRIGHT)
    flame = np.zeros((*SHAPE, 3), dtype=np.uint8)
    with_flames = shaded.copy()
    if flames:
        flame[2:16, 30:50] = 255  # above rod_lit's row 20
        with_flames[2:16, 30:50] = BRIGHT
    _save(directory, f"fuel-{tier}-noflame", shaded, foot)
    _save(directory, f"fuel-{tier}", with_flames, foot)
    _save(directory, f"fuel-{tier}-fuel_mask", mask, foot)
    _save(directory, f"fuel-{tier}-flame_mask", flame, foot)


def test_frames_built_to_pass_pass_every_check(tmp_path):
    for tier in ("laptop", "rig", "max"):
        _frames(tmp_path, tier)
    assert gf.fuel_findings(tmp_path) == []


def test_burning_with_no_added_brightness_is_found(tmp_path):
    _frames(tmp_path, "rig", burning=False)
    assert any(f.startswith("burning (rig)") for f in gf.state_findings(tmp_path, "rig", SEG))


def test_char_and_glow_without_contrast_are_found(tmp_path):
    _frames(tmp_path, "rig")
    png = tmp_path / "fuel-rig-noflame.png"
    flat = np.asarray(Image.open(png)).copy()
    flat[flat.any(axis=2)] = GREY
    Image.fromarray(flat).save(png)
    found = gf.state_findings(tmp_path, "rig", SEG)
    assert any(f.startswith("char on rod_burnt") for f in found)
    assert any(f.startswith("char on slab_char") for f in found)
    assert any(f.startswith("glow on fuel") for f in found)


def test_fuel_drawn_inside_the_burnt_run_is_found(tmp_path):
    _frames(tmp_path, "rig", burnt_hole=False)
    assert any("inside the burnt run" in f for f in gf.burn_through_findings(tmp_path, "rig", SEG))


def test_a_live_run_drawn_narrower_than_its_width_is_found(tmp_path):
    _frames(tmp_path, "rig")
    assert not any("draws" in f and "px, not" in f for f in gf.burn_through_findings(tmp_path, "rig", SEG))
    mask_png = tmp_path / "fuel-rig-fuel_mask.png"
    mask = np.asarray(Image.open(mask_png)).copy()
    foot = gf.footprints(mask_png)
    live = SEG.rows("rod_burnt", SEG.thickness > 0)
    mask[gf.strip(SHAPE, foot[live])] = 0
    thin = foot[live].copy()
    thin[:, 4] = 0.5  # a 1 px line where 4 px are drawn
    mask[gf.strip(SHAPE, thin)] = 255
    Image.fromarray(mask).save(mask_png)
    found = gf.burn_through_findings(tmp_path, "rig", SEG)
    assert any(f.startswith("burn-through (rig): live run") and "px, not 4.00" in f for f in found)


def test_no_clear_live_run_has_no_width_to_measure():
    assert gf._width_findings("rig", np.zeros(SHAPE), _footprints(), []) == []


def test_a_live_segment_that_draws_nothing_is_found_away_from_the_run(tmp_path):
    _frames(tmp_path, "rig")
    mask_png = tmp_path / "fuel-rig-fuel_mask.png"
    mask = np.asarray(Image.open(mask_png)).copy()
    foot = gf.footprints(mask_png)
    first_live = SEG.rows("rod_burnt", SEG.thickness > 0)[0]
    mask[gf.strip(SHAPE, foot[[first_live]])] = 0
    Image.fromarray(mask).save(mask_png)
    assert any("draw nothing" in f for f in gf.burn_through_findings(tmp_path, "rig", SEG))


def test_missing_or_misplaced_flames_are_found(tmp_path):
    _frames(tmp_path, "rig", flames=False)
    assert gf.flame_findings(tmp_path, "rig", SEG) == ["flame shape (rig): the flame mask marks no pixels"]
    _frames(tmp_path, "rig")
    flame_png = tmp_path / "fuel-rig-flame_mask.png"
    low = np.zeros((*SHAPE, 3), dtype=np.uint8)
    low[100:115, 30:50] = 255  # below the fuel
    Image.fromarray(low).save(flame_png)
    assert any("above the fuel" in f for f in gf.flame_findings(tmp_path, "rig", SEG))


def test_a_flame_that_adds_no_light_is_found(tmp_path):
    _frames(tmp_path, "rig")
    Image.open(tmp_path / "fuel-rig-noflame.png").save(tmp_path / "fuel-rig.png")
    assert any("L* over the flames" in f for f in gf.flame_findings(tmp_path, "rig", SEG))


def test_a_tier_whose_rods_cover_a_different_area_is_found(tmp_path):
    for tier in ("laptop", "rig", "max"):
        _frames(tmp_path, tier)
    png = tmp_path / "fuel-laptop-fuel_mask.png"
    mask = np.asarray(Image.open(png)).copy()
    mask[:, ::2] = 0  # half the rods' coverage gone
    Image.fromarray(mask).save(png)
    assert any(f.startswith("fuel tier agreement: rod_lit at laptop") for f in gf.agreement_findings(tmp_path, SEG))


def test_a_strip_covers_its_pixels_and_shrinks_at_both_ends():
    row = np.array([[10.0, 10.0, 20.0, 10.0, 1.0]])
    assert int(gf.strip(SHAPE, row).sum()) == 20
    assert int(gf.strip(SHAPE, row, shrink_px=2.0).sum()) == 12
    assert not gf.strip(SHAPE, row, shrink_px=5.0).any()
    assert not gf.strip(SHAPE, np.array([[-50.0, -50.0, -40.0, -50.0, 1.0]])).any()  # wholly off-screen


def test_a_segment_near_a_point_is_near_and_one_far_is_far():
    row = np.array([10.0, 10.0, 12.0, 10.0, 2.0])
    assert gf._distance(row, np.array([[13.0, 10.0]])) == pytest.approx(1.0)
    assert gf._distance(row, np.array([[50.0, 50.0], [12.0, 14.0]])) == pytest.approx(4.0)


def test_the_fixtures_regions_carry_the_states_the_checks_read():
    assert len(SEG.rows("rod_lit", SEG.ignited == 255)) == 10
    assert len(SEG.rows("rod_burnt", SEG.thickness == 0)) == 10
    assert len(SEG.rows("stick_glow", SEG.temperature_c >= gf.HOT_C)) > 0
    spent = SEG.rows("rod_spent")
    assert (SEG.ignited[spent] == 255).all()  # would flame
    assert (SEG.temperature_c[spent] >= gf.HOT_C).all()  # and glow
    gap = SEG.rows("rod_gap")
    assert (SEG.ignited[gap] > 0).tolist() == (SEG.thickness[gap] == 0).tolist()  # only its burnt run reports flame
    assert len(SEG.rows("rod_gap", SEG.ignited > 0)) == 4
    assert len(SEG.rows("rod_burnt", SEG.char >= gf.CHARRED)) > 0  # the burnout check's cold reference


def test_a_burnt_out_object_that_glows_is_found(tmp_path):
    _frames(tmp_path, "rig")
    assert gf.burnout_findings(tmp_path, "rig", SEG) == []
    _frames(tmp_path, "rig", spent_glows=True)
    assert any(f.startswith("burnout (rig): rod_spent glows") for f in gf.burnout_findings(tmp_path, "rig", SEG))
    Image.fromarray(np.zeros((*SHAPE, 3), dtype=np.uint8)).save(tmp_path / "fuel-rig-fuel_mask.png")
    assert gf.burnout_findings(tmp_path, "rig", SEG) == ["burnout (rig): no pixels to compare (0 and 0)"]


@pytest.mark.parametrize(("region", "y"), [("rod_spent", 96), ("rod_gap", 110)])
def test_a_flame_from_a_dead_object_or_segment_is_found(tmp_path, region, y):
    _frames(tmp_path, "rig")
    assert gf.dead_flame_findings(tmp_path, "rig", SEG) == []
    png = tmp_path / "fuel-rig-flame_mask.png"
    flame = np.asarray(Image.open(png)).copy()
    flame[y - 6 : y - 1, 14:20] = 255  # a tongue just above the object
    Image.fromarray(flame).save(png)
    found = gf.dead_flame_findings(tmp_path, "rig", SEG)
    assert any(f.startswith("dead flames (rig):") and f.endswith(region) for f in found)


def test_a_body_drawn_over_fuel_counts_no_fuel_area(tmp_path):
    _frames(tmp_path, "rig")
    png = tmp_path / "fuel-rig-fuel_mask.png"
    before = gf.object_areas(tmp_path, "rig", SEG)["rod_lit"]
    mask = np.asarray(Image.open(png)).copy()
    mask[15:26, 60:80] = (255, 0, 0)  # a body's ID colour, beside rod_lit's strips
    Image.fromarray(mask).save(png)
    assert gf.object_areas(tmp_path, "rig", SEG)["rod_lit"] <= before


def test_a_stick_hidden_by_a_log_behind_it_is_found(tmp_path):
    _frames(tmp_path, "rig")
    assert gf.crossing_findings(tmp_path, "rig", SEG) == []
    _frames(tmp_path, "rig", stick_hidden=True)
    found = gf.crossing_findings(tmp_path, "rig", SEG)
    assert any(f.startswith("crossing (rig): the stick over the log") for f in found)
    Image.fromarray(np.zeros((*SHAPE, 3), dtype=np.uint8)).save(tmp_path / "fuel-rig-fuel_mask.png")
    assert gf.crossing_findings(tmp_path, "rig", SEG) == ["crossing (rig): no pixels to compare (0 and 0)"]


def _copy_fixture(directory: Path, edit) -> Path:
    header = json.loads(gf.FIXTURE.read_text())
    edit(header)
    (directory / header["data"]).write_bytes((gf.FIXTURE.parent / header["data"]).read_bytes())
    out: Path = directory / gf.FIXTURE.name
    out.write_text(json.dumps(header))
    return out


@pytest.mark.parametrize(
    ("key", "value", "says"),
    [("format", "other", "not overdrive"), ("version", 1, "v1"), ("data_sha256", "0" * 64, "digest"),
     ("data_size", 1, "digest")],
)  # fmt: skip
def test_the_fixture_reader_refuses_what_it_does_not_know(tmp_path, key, value, says):
    path = _copy_fixture(tmp_path, lambda h: h.__setitem__(key, value))
    with pytest.raises(ValueError, match=says):
        gf.segments(path)
    assert len(gf.segments(_copy_fixture(tmp_path, lambda h: None)).region) == len(SEG.region)


def test_the_reader_knows_the_writers_format_and_the_drawn_fixture():
    assert (gf.FORMAT, gf.VERSION) == (ff.FORMAT, ff.VERSION)
    assert gf.FIXTURE_NAME in ff.FIXTURES
    source = (ROOT / "client" / "addons" / "engine" / "render" / "fuel_pass.gd").read_text()
    height = float(source.split("const FLAME_HEIGHT_M: float = ")[1].split()[0])
    assert pytest.approx(2.0 * height) == gf.FLAME_REACH_M


def test_a_comparison_with_nothing_drawn_says_so(tmp_path):
    _frames(tmp_path, "rig")
    Image.fromarray(np.zeros((*SHAPE, 3), dtype=np.uint8)).save(tmp_path / "fuel-rig-fuel_mask.png")
    found = gf.state_findings(tmp_path, "rig", SEG)
    assert found
    assert all("no pixels to compare (0 and 0)" in f for f in found)
