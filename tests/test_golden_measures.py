"""scripts/golden_measures.py: the rendered checks that measure a property (client_rendering.md §2, §6.3, §6.4; B7).

Driven by synthetic frames whose answer is known, so each rule is shown to pass what it should and to fail what it
must: a body hidden behind a wall, a crack that only darkens (the carving deleted), glow with its emission zeroed,
and a tier that draws a different picture. The real frames are judged in the golden job (scripts/golden_run.py);
the deletion proofs on the real shader are in the branch's commit message.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from tests.test_golden_compare import gcmp

ROOT = Path(__file__).resolve().parents[1]
assert gcmp is not None
_spec = importlib.util.spec_from_file_location("golden_measures", ROOT / "scripts" / "golden_measures.py")
assert _spec is not None
assert _spec.loader is not None
gm = importlib.util.module_from_spec(_spec)
sys.modules["golden_measures"] = gm
_spec.loader.exec_module(gm)

H, W = 90, 160
RED = (255, 0, 0)


def _frame(rgb: tuple[int, int, int] = (0, 0, 0)) -> np.ndarray:
    return np.broadcast_to(np.array(rgb, dtype=np.uint8), (H, W, 3)).copy()


def _save(path: Path, rgb: np.ndarray) -> None:
    Image.fromarray(rgb).save(path)


def _body(rgb: np.ndarray, rows: slice) -> np.ndarray:
    rgb[rows, 70:90] = RED
    return rgb


def _pair(d: Path, sample: str, k: int, visible_rows: slice = slice(20, 60)) -> None:
    _save(d / f"cut-{sample}-k{k}-with.png", _body(_frame(), visible_rows))
    _save(d / f"cut-{sample}-k{k}-without.png", _body(_frame(), slice(20, 60)))


def _all_pairs(d: Path) -> None:
    for sample in gm.CUTAWAY_SAMPLES:
        for k in range(4):
            _pair(d, sample, k)


def test_every_expected_pair_with_the_body_visible_passes(tmp_path):
    _all_pairs(tmp_path)
    _pair(tmp_path, "south-2", 1, slice(21, 60))  # 39/40 = 97.5%
    assert gm.cutaway_findings(tmp_path) == []


def test_a_body_a_wall_hides_fails(tmp_path):
    _all_pairs(tmp_path)
    _pair(tmp_path, "north-4", 2, slice(20, 50))  # 30/40 = 75%: a wall left standing
    assert gm.cutaway_findings(tmp_path) == ["cutaway: cut-north-4-k2-with.png: 75.0% of the body visible, below 95%"]


def test_every_sample_is_gated_the_crate_ones_included(tmp_path):
    _all_pairs(tmp_path)
    _pair(tmp_path, "crate-east", 2, slice(20, 54))
    assert gm.cutaway_findings(tmp_path) == [
        "cutaway: cut-crate-east-k2-with.png: 85.0% of the body visible, below 95%"
    ]


def test_a_missing_extra_or_half_pair_fails(tmp_path):
    assert len(gm.cutaway_findings(tmp_path)) == 4 * len(gm.CUTAWAY_SAMPLES)
    _all_pairs(tmp_path)
    (tmp_path / "cut-end-k3-with.png").unlink()
    (tmp_path / "cut-end-k0-without.png").unlink()
    _pair(tmp_path, "stray", 1)
    found = gm.cutaway_findings(tmp_path)
    assert found == [
        "cutaway: no frames for end at step 3",
        "cutaway: frames for stray at step 1, which is not a sample",
        "cutaway: cut-end-k0-with.png has no -without.png beside it",
    ]


def test_a_body_that_never_draws_fails(tmp_path):
    _all_pairs(tmp_path)
    _save(tmp_path / "cut-end-k0-with.png", _frame())
    _save(tmp_path / "cut-end-k0-without.png", _frame())
    assert gm.cutaway_findings(tmp_path) == [
        "cutaway: cut-end-k0-with.png: the body draws no pixels even with the volume hidden"
    ]


def test_the_sample_list_is_the_scenes():
    source = (ROOT / "client" / "tests" / "cutaway_check.gd").read_text()
    block = source[source.index("const SAMPLES") : source.index("\n}\n", source.index("const SAMPLES"))]
    assert tuple(re.findall(r'"([a-z0-9.-]+)": Vector3', block)) == gm.CUTAWAY_SAMPLES


def test_body_pixels_count_only_the_id_colour():
    rgb = _frame((200, 200, 200))
    rgb[0, :10] = RED
    rgb[1, :10] = (200, 30, 30)  # filtered silhouette, still mostly red
    rgb[2, :10] = (255, 200, 0)  # glow: red is high but so is green
    assert gm.body_pixels(rgb) == 20


def _cracked(carve: bool) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """A cold block, the same block cracked (darkened, and grooved when ``carve``), and its crack mask."""
    cold = _frame((20, 20, 20))
    cold[20:70, 40:120] = (150, 120, 90)
    cracked = cold.copy()
    cracked[20:70, 40:120] = (110, 88, 66)  # char darkens
    if carve:
        cracked[20:70:6, 40:120] = (15, 12, 10)  # and fissures cross it
        cracked[20:70, 40:120:7] = (15, 12, 10)
    mask = np.zeros((H, W), dtype=np.bool_)
    mask[20:70, 40:120] = True
    return cold, cracked, mask


def test_a_crack_that_changes_shape_passes():
    assert gm.crack_findings(*_cracked(carve=True)) == []


def test_a_crack_that_only_darkens_fails_on_edges():
    found = gm.crack_findings(*_cracked(carve=False))
    assert len(found) == 1
    assert found[0].startswith("crack: edge density")


def test_a_crack_too_faint_to_see_fails_on_lightness():
    cold, _, mask = _cracked(carve=False)
    faint = cold.copy()
    faint[20:70:6, 40:120] = (147, 117, 87)
    assert any(f.startswith("crack: mean |ΔL*|") for f in gm.crack_findings(cold, faint, mask))


def test_an_empty_mask_fails_rather_than_passing_vacuously():
    cold, cracked, mask = _cracked(carve=True)
    assert gm.crack_findings(cold, cracked, ~np.ones_like(mask)) == ["crack: the crack mask marks no pixels"]
    assert gm.glow_findings(cold, cracked, ~np.ones_like(mask)) == ["glow: the glow mask marks no pixels"]


def test_glow_must_brighten():
    cold = _frame((60, 40, 30))
    mask = np.ones((H, W), dtype=np.bool_)
    assert gm.glow_findings(cold, _frame((255, 170, 60)), mask) == []
    hue_only = _frame((70, 30, 25))  # redder, not brighter: colour alone
    assert gm.glow_findings(cold, hue_only, mask)[0].startswith("glow: glowing cells are")


def test_tiers_that_differ_in_detail_agree_and_a_different_picture_does_not():
    rig = _frame((90, 90, 80))
    rig[30:60, 40:100] = (200, 120, 60)
    big = np.kron(rig, np.ones((2, 2, 1), dtype=np.uint8))  # 320 x 180, filtered back to 160 x 90
    detail = big.copy()
    detail[60:120:2, 80:200:2] = (180, 110, 55)  # every other pixel a little darker: detail, not a new picture
    assert gm.agreement_findings("laptop", detail, big) == []
    assert len(gm.agreement_findings("max", np.zeros_like(big), big)) == 2


def test_an_isolated_pixel_on_a_flat_face_is_speckle_and_texture_is_not():
    rgb = _frame((93, 90, 80))
    assert gm.speckle(rgb) == []
    rgb[40, 70] = (0, 0, 3)  # a floor top shaded as a side face
    rgb[60, 100] = (60, 58, 52)
    assert gm.speckle(rgb) == [(40, 70), (60, 100)]
    textured = _frame((93, 90, 80))
    for k in range(0, W, 8):
        textured[:, k : k + 3] = (40, 40, 40)  # hatching-like stripes: the neighbours disagree, nothing is flagged
    assert gm.speckle(textured) == []
    line = _frame((93, 90, 80))
    line[40, :] = (20, 20, 20)  # a one-pixel line (a groove's floor, an edge): its neighbours disagree, not speckle
    assert gm.speckle(line) == []
    edge = _frame((93, 90, 80))
    edge[:, 80:] = (20, 20, 20)  # a silhouette is not speckle
    assert gm.speckle(edge) == []


def test_speckle_is_judged_on_the_full_resolution_cold_frames(tmp_path):
    clean = _frame((93, 90, 80))
    for tier in gm.SPECKLE_TIERS:
        _save(tmp_path / f"cold-{tier}.png", clean)
    assert gm.speckle_findings(tmp_path) == []
    dotted = clean.copy()
    dotted[10, 10] = (0, 0, 0)
    _save(tmp_path / "cold-max.png", dotted)
    assert gm.speckle_findings(tmp_path) == ["max: speckle: 1 isolated pixel(s) on flat faces, first at [(10, 10)]"]


def test_the_box_filter_averages_blocks_and_refuses_an_uneven_frame():
    rgb = np.zeros((180, 320, 3), dtype=np.uint8)
    rgb[0, 0] = (255, 255, 255)
    small = gm.box_filter(rgb)
    assert small.shape == (90, 160, 3)
    assert small[0, 0].tolist() == [64, 64, 64]
    with pytest.raises(ValueError, match="doesn't divide"):
        gm.box_filter(np.zeros((100, 161, 3), dtype=np.uint8))


def test_colour_alone_reads_the_frames_golden_run_names(tmp_path):
    cold, cracked, mask = _cracked(carve=True)
    glow_mask = np.zeros((H, W), dtype=np.bool_)
    glow_mask[75:85, 10:30] = True
    cracked[75:85, 10:30] = (255, 200, 120)
    _save(tmp_path / "cold-max.png", cold)
    _save(tmp_path / "fire-max.png", cracked)
    _save(tmp_path / "fire-max-crack_mask.png", np.where(mask[..., None], 255, 0).astype(np.uint8).repeat(3, -1))
    _save(tmp_path / "fire-max-glow_mask.png", np.where(glow_mask[..., None], 255, 0).astype(np.uint8).repeat(3, -1))
    assert gm.colour_alone_findings(tmp_path, "max") == []
    _save(tmp_path / "fire-max.png", cold)
    assert gm.colour_alone_findings(tmp_path, "max")[0].startswith("max: crack:")
