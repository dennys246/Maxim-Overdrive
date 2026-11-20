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
KEY = "compat-llvmpipe-mesa25.2.8-godot4.7.2"
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


def _main(tmp_path: Path, actual: np.ndarray, golden: np.ndarray | None, log: str = LOG) -> int:
    (tmp_path / "golden.log").write_text(log)
    _write(tmp_path / "out" / "frame.png", actual)
    if golden is not None:
        _write(tmp_path / "goldens" / KEY / "rig" / "frame.png", golden)
    args = ["--log", str(tmp_path / "golden.log"), "--actual", str(tmp_path / "out" / "frame.png")]
    args += ["--goldens", str(tmp_path / "goldens"), "--name", "rig/frame.png", "--diff", str(tmp_path / "diff.png")]
    code: int = gcmp.main(args)
    return code


def test_main_passes_a_matching_frame(tmp_path, capsys):
    assert _main(tmp_path, _flat((10, 20, 30)), _flat((10, 20, 30))) == 0
    assert capsys.readouterr().out == "golden_compare: PASS rig/frame.png\n"
    assert not (tmp_path / "diff.png").exists()


def test_main_fails_a_different_frame_and_writes_the_difference(tmp_path, capsys):
    golden = _flat((10, 20, 30), 100, 100)
    actual = golden.copy()
    actual[:20, :20] = (250, 250, 250)
    assert _main(tmp_path, actual, golden) == 1
    assert "px blob with ΔE > 10" in capsys.readouterr().err
    diff = np.asarray(Image.open(tmp_path / "diff.png"))
    assert diff[0, 0] == 255
    assert diff[50, 50] == 0


def test_main_refuses_when_there_is_no_golden_for_this_renderer(tmp_path, capsys):
    assert _main(tmp_path, _flat((1, 2, 3)), None) == 1
    assert f"no golden at {tmp_path / 'goldens' / KEY / 'rig' / 'frame.png'}" in capsys.readouterr().err


def test_main_refuses_another_renderer(tmp_path, capsys):
    assert _main(tmp_path, _flat((1, 2, 3)), _flat((1, 2, 3)), log=LOG.replace("256", "128")) == 1
    assert "128 bits" in capsys.readouterr().err


def test_the_committed_goldens_are_keyed_and_full_size():
    goldens = sorted(GOLDENS.rglob("*.png"))
    assert goldens, "step 2 ships one renderer golden (client_rendering.md §12)"
    for png in goldens:
        rel = png.relative_to(GOLDENS)
        assert re.fullmatch(r"compat-llvmpipe-mesa\d+\.\d+\.\d+-godot\d+\.\d+\.\d+", rel.parts[0]), rel
        assert gcmp.load_rgb(png).shape == (720, 1280, 3), rel
