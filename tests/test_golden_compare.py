"""scripts/golden_compare.py: the §6.2 tolerance, and goldens keyed by the renderer that drew them (B7, CR-B3)."""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("golden_compare", ROOT / "scripts" / "golden_compare.py")
assert _spec is not None
assert _spec.loader is not None
gcmp = importlib.util.module_from_spec(_spec)
sys.modules["golden_compare"] = gcmp
_spec.loader.exec_module(gcmp)

GOLDENS = ROOT / "client" / "tests" / "goldens"
LOG = (
    "Godot Engine v4.7.2.stable.official.ed1daf0bf - https://godotengine.org\n"
    "OpenGL API 4.5 (Core Profile) Mesa 25.2.8-0ubuntu0.24.04.4 - Compatibility - Using Device: Mesa - "
    "llvmpipe (LLVM 20.1.2, 256 bits)\n"
)
KEY = "compat-llvmpipe-mesa25.2.8-0ubuntu0.24.04.4-llvm20.1.2-godot4.7.2"
MAC_LOG = "Godot Engine v4.7.2.stable\nOpenGL API 4.1 Metal - 90.5 - Compatibility - Using Device: Apple - Apple M2\n"


def _flat(rgb: tuple[int, int, int], h: int = 90, w: int = 160) -> np.ndarray:
    return np.broadcast_to(np.array(rgb, dtype=np.uint8), (h, w, 3)).copy()


def test_lab_matches_known_values():
    lab = gcmp.srgb_to_lab(np.array([[[255, 255, 255], [0, 0, 0], [255, 0, 0], [128, 128, 128]]], dtype=np.uint8))
    np.testing.assert_allclose(lab[0, 0], [100.0, 0.0, 0.0], atol=0.01)
    np.testing.assert_allclose(lab[0, 1], [0.0, 0.0, 0.0], atol=0.01)
    np.testing.assert_allclose(lab[0, 2], [53.24, 80.09, 67.20], atol=0.05)  # CIE76 references for sRGB red
    np.testing.assert_allclose(lab[0, 3], [53.59, 0.0, 0.0], atol=0.05)


def test_identical_frames_pass_with_zero_difference():
    frame = _flat((90, 60, 30))
    verdict = gcmp.compare(frame, frame)
    assert (verdict.mean, verdict.p995, verdict.blob_px) == (0.0, 0.0, 0)
    assert verdict.findings() == []


def test_a_slight_shift_everywhere_passes_and_a_larger_one_fails_the_mean():
    base = _flat((100, 100, 100))
    assert gcmp.compare(_flat((101, 100, 100)), base).findings() == []
    found = gcmp.compare(_flat((106, 100, 100)), base).findings()  # ΔE 2.6 everywhere: under the percentile's 4
    assert len(found) == 1
    assert found[0].startswith("mean ΔE 2.5")


def test_scattered_large_differences_fail_the_percentile_but_not_the_blob_rule():
    golden = _flat((100, 100, 100))
    actual = golden.copy()
    actual[::8, ::8] = (160, 100, 100)  # 1 in 64 pixels, isolated
    found = gcmp.compare(actual, golden).findings()
    assert len(found) == 1
    assert found[0].startswith("99.5th percentile")


@pytest.mark.parametrize(("side", "fails"), [(8, False), (9, True)])
def test_a_blob_over_64_pixels_fails(side, fails):
    """A small object that moved: too small for the mean and the percentile to see, which is why the rule exists."""
    golden = _flat((100, 100, 100), 400, 400)
    actual = golden.copy()
    actual[10 : 10 + side, 10 : 10 + side] = (200, 60, 60)
    found = gcmp.compare(actual, golden).findings()
    assert [f.startswith(f"a {side * side} px blob") for f in found] == ([True] if fails else [])


def test_blobs_are_4_connected():
    """Diagonal neighbours are separate blobs: 4-connectivity, as §6.2 says, not 8."""
    mask = np.zeros((20, 20), dtype=bool)
    for i in range(20):
        mask[i, i] = True
    assert gcmp.largest_blob(mask) == 1
    mask[0, 1:6] = True  # joins (0, 0) to (0, 5), and (1, 1) below (0, 1)
    assert gcmp.largest_blob(mask) == 7
    assert gcmp.largest_blob(np.zeros((4, 4), dtype=bool)) == 0


def test_frames_of_different_sizes_are_refused():
    with pytest.raises(ValueError, match="the frame is"):
        gcmp.compare(_flat((0, 0, 0), 90, 160), _flat((0, 0, 0), 90, 161))


def test_the_key_comes_from_the_log():
    assert gcmp.golden_key(LOG) == KEY


@pytest.mark.parametrize(
    ("log", "why"),
    [
        (LOG.splitlines()[1], "no 'Godot Engine v<version>' line"),
        (LOG.replace("llvmpipe", "softpipe"), "no Compatibility renderer on Mesa llvmpipe"),
        (LOG.replace("Compatibility", "Forward+"), "no Compatibility renderer on Mesa llvmpipe"),
        (MAC_LOG, "no Compatibility renderer on Mesa llvmpipe"),
        (LOG.replace("256 bits", "128 bits"), "llvmpipe ran at 128 bits, not 256"),
    ],
)
def test_only_256_bit_llvmpipe_draws_goldens(log, why):
    with pytest.raises(ValueError, match=re.escape(why)):
        gcmp.golden_key(log)


def _write(path: Path, rgb: np.ndarray) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgb).save(path)
    return path


def _judge(tmp_path: Path, actual: np.ndarray, golden: np.ndarray | None, log: str = LOG) -> list[str]:
    frame = _write(tmp_path / "out" / "frame.png", actual)
    if golden is not None:
        _write(tmp_path / "goldens" / KEY / "renderer" / "frame.png", golden)
    found: list[str] = gcmp.judge(log, frame, tmp_path / "goldens", "renderer/frame.png", tmp_path / "diff.png")
    return found


def test_a_matching_frame_passes(tmp_path):
    assert _judge(tmp_path, _flat((10, 20, 30)), _flat((10, 20, 30))) == []
    assert not (tmp_path / "diff.png").exists()


def test_a_different_frame_fails_and_the_difference_is_written(tmp_path):
    golden = _flat((10, 20, 30), 100, 100)
    actual = golden.copy()
    actual[:20, :20] = (250, 250, 250)
    found = _judge(tmp_path, actual, golden)
    assert any("a 400 px blob with ΔE > 10" in f for f in found), found
    diff = np.asarray(Image.open(tmp_path / "diff.png"))
    assert diff[0, 0] == 255
    assert diff[50, 50] == 0


def test_no_diff_is_written_unless_asked(tmp_path):
    frame = _write(tmp_path / "f.png", _flat((250, 0, 0)))
    _write(tmp_path / "goldens" / KEY / "renderer" / "f.png", _flat((0, 0, 250)))
    assert gcmp.judge(LOG, frame, tmp_path / "goldens", "renderer/f.png")
    assert sorted(p.name for p in tmp_path.iterdir()) == ["f.png", "goldens"]


def test_a_frame_of_another_size_is_a_finding(tmp_path):
    found = _judge(tmp_path, _flat((1, 2, 3), 90, 160), _flat((1, 2, 3), 90, 161))
    assert len(found) == 1
    assert "the frame is" in found[0]


def test_there_must_be_a_golden_for_this_build(tmp_path):
    found = _judge(tmp_path, _flat((1, 2, 3)), None)
    assert found == [
        f"no golden at {tmp_path / 'goldens' / KEY / 'renderer' / 'frame.png'}: record one from this run's frame "
        "in a commit of its own (§6.5)"
    ]


def test_another_renderer_is_refused(tmp_path):
    assert _judge(tmp_path, _flat((1, 2, 3)), _flat((1, 2, 3)), log=LOG.replace("256", "128")) == [
        "llvmpipe ran at 128 bits, not 256 (LP_NATIVE_VECTOR_WIDTH)"
    ]


def test_a_new_llvm_or_mesa_revision_is_a_new_key():
    """S2C-S1: llvmpipe's pixels come from LLVM's JIT and the Ubuntu revision as well as from Mesa's version."""
    assert gcmp.golden_key(LOG.replace("LLVM 20.1.2", "LLVM 20.1.3")) != KEY
    assert gcmp.golden_key(LOG.replace("24.04.4", "24.04.5")) != KEY


def test_the_committed_goldens_are_keyed_and_full_size():
    goldens = sorted(GOLDENS.rglob("*.png"))
    assert goldens, "step 2 ships one renderer golden (client_rendering.md §12)"
    for png in goldens:
        rel = png.relative_to(GOLDENS)
        assert re.fullmatch(r"compat-llvmpipe-mesa\d+\.\d+\.\d+\S*-llvm\d+\.\d+\.\d+-godot\d+\.\d+\.\d+", rel.parts[0])
        assert gcmp.load_rgb(png).shape == (720, 1280, 3), rel
