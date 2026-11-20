"""scripts/golden_run.py, the golden job's procedure: import, draw under a display, judge (B7; S2A-S1, S2E-S1).

A real run needs Xvfb and llvmpipe, which exist only in the golden image (ci/godot-golden/), so these tests drive the
procedure with a stand-in Godot: a script that answers ``--import`` and draws by copying a frame, printing what the
real Godot prints. They prove the procedure's decisions, and that it reuses the gate's scans: an error line, a
non-zero exit, a missing frame and a timeout all fail the job, whatever the frame looks like.
"""

from __future__ import annotations

import importlib.util
import os
import stat
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from tests.test_godot_check import gc  # registers godot_check, which golden_run imports
from tests.test_golden_compare import KEY, LOG, gcmp

ROOT = Path(__file__).resolve().parents[1]
assert gc is not None
assert gcmp is not None
_spec = importlib.util.spec_from_file_location("golden_run", ROOT / "scripts" / "golden_run.py")
assert _spec is not None
assert _spec.loader is not None
gr = importlib.util.module_from_spec(_spec)
sys.modules["golden_run"] = gr
_spec.loader.exec_module(gr)

FAKE_GODOT = f"""#!{sys.executable}
import os, shutil, sys
mode = os.environ["FAKE_GODOT_MODE"]
if "--import" in sys.argv:
    sys.exit(0)
print({LOG!r}, end="")
out = next(a for a in sys.argv if a.startswith("--out=")).removeprefix("--out=")
if not os.path.isabs(out):
    print("ERROR: Can't save PNG at path: " + out)  # the real Godot reads it against the project
    sys.exit(1)
if mode == "error":
    print("SCRIPT ERROR: something broke")
if mode == "hang":
    while True:
        pass
if mode != "no-frame":
    shutil.copy(os.environ["FAKE_GODOT_FRAME"], out)
sys.exit(2 if mode == "exit-2" else 0)
"""
WRAPPER = f"""#!{sys.executable}
import os, sys
open(os.environ["FAKE_WRAPPER_MARK"], "w").write(" ".join(sys.argv[1:4]))
os.execv(sys.argv[4], sys.argv[4:])
"""


def _executable(path: Path, source: str) -> str:
    path.write_text(source)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return str(path)


@pytest.fixture
def setup(tmp_path, monkeypatch):
    """A stand-in Godot, a golden for the build its log names, and a frame it will draw."""
    rgb = np.zeros((72, 128, 3), dtype=np.uint8)
    rgb[10:20, 10:20] = (200, 120, 40)
    goldens = tmp_path / "goldens"
    (goldens / KEY / "renderer").mkdir(parents=True)
    Image.fromarray(rgb).save(goldens / KEY / "renderer" / "boxes.png")
    Image.fromarray(rgb).save(tmp_path / "frame.png")
    monkeypatch.setattr(gr, "GOLDENS", goldens)
    monkeypatch.setenv("FAKE_GODOT_FRAME", str(tmp_path / "frame.png"))
    monkeypatch.setenv("FAKE_GODOT_MODE", "ok")
    return _executable(tmp_path / "godot", FAKE_GODOT)


def _main(tmp_path: Path, godot: str, *extra: str) -> int:
    code: int = gr.main(["--godot", godot, "--out", str(tmp_path / "out"), "--no-xvfb", *extra], work_parent=tmp_path)
    return code


def test_a_matching_frame_passes_and_its_log_is_kept(setup, tmp_path, capsys):
    assert _main(tmp_path, setup) == 0, capsys.readouterr().err
    assert capsys.readouterr().out.endswith("golden_run: PASS (1 scene(s))\n")
    assert "llvmpipe (LLVM 20.1.2, 256 bits)" in (tmp_path / "out" / "renderer-boxes.log").read_text()
    assert not (tmp_path / "out" / "renderer-boxes.diff.png").exists()


@pytest.mark.parametrize(
    "case",
    [
        ("error", "Godot printed an error: SCRIPT ERROR: something broke"),
        ("exit-2", "exited 2"),
        ("no-frame", "no frame at"),
    ],
)
def test_a_draw_that_errs_exits_badly_or_writes_nothing_fails_whatever_the_frame(
    setup, tmp_path, monkeypatch, capsys, case
):
    mode, finding = case
    monkeypatch.setenv("FAKE_GODOT_MODE", mode)
    assert _main(tmp_path, setup) == 1
    assert finding in capsys.readouterr().err


def test_a_hang_is_ended_by_the_timeout(setup, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FAKE_GODOT_MODE", "hang")
    assert _main(tmp_path, setup, "--timeout", "2") == 1
    assert "timed out after 2 s" in capsys.readouterr().err


def test_a_frame_that_differs_fails_and_its_difference_is_written(setup, tmp_path, monkeypatch, capsys):
    other = np.full((72, 128, 3), 255, dtype=np.uint8)
    Image.fromarray(other).save(tmp_path / "other.png")
    monkeypatch.setenv("FAKE_GODOT_FRAME", str(tmp_path / "other.png"))
    assert _main(tmp_path, setup) == 1
    assert "mean ΔE" in capsys.readouterr().err
    assert (tmp_path / "out" / "renderer-boxes.diff.png").is_file()


def test_a_failed_import_draws_nothing(setup, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(gr, "CLIENT", tmp_path / "client")
    (tmp_path / "client").mkdir()
    monkeypatch.setattr(gc, "import_changes", lambda source, imported: ["import: created x.gd.uid"])
    assert _main(tmp_path, setup) == 1
    assert "import: created x.gd.uid" in capsys.readouterr().err
    assert not (tmp_path / "out" / "renderer-boxes.log").exists()


def test_by_default_godot_draws_under_xvfb(setup, tmp_path, monkeypatch, capsys):
    mark = tmp_path / "wrapper-args"
    monkeypatch.setenv("FAKE_WRAPPER_MARK", str(mark))
    wrapper = _executable(tmp_path / "xvfb-run", WRAPPER)
    monkeypatch.setattr(gr, "XVFB", (wrapper, "-a", "-s", "-screen 0 1280x720x24"))
    assert gr.main(["--godot", setup, "--out", str(tmp_path / "out")], work_parent=tmp_path) == 0
    assert mark.read_text() == "-a -s -screen 0 1280x720x24"
    assert gr.XVFB != ()
    capsys.readouterr()


def test_the_real_wrapper_is_xvfb_at_the_golden_resolution():
    assert gr.XVFB == ("xvfb-run", "-a", "-s", "-screen 0 1280x720x24")
    assert " ".join(gr.DRAW) == (
        "--audio-driver Dummy --rendering-driver opengl3 --rendering-method gl_compatibility --fixed-fps 60 "
        "--resolution 1280x720"
    )


def test_without_godot_the_job_fails(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(gc, "find_godot", lambda env, platform: None)
    monkeypatch.delenv("GODOT", raising=False)
    assert gr.main(["--out", str(tmp_path / "out")], work_parent=tmp_path) == 1
    assert "no Godot" in capsys.readouterr().err
    assert os.environ.get("GODOT") is None


def test_a_relative_out_directory_reaches_godot_as_an_absolute_path(setup, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert gr.main(["--godot", setup, "--out", "out", "--no-xvfb"], work_parent=tmp_path) == 0, capsys.readouterr().err
    assert (tmp_path / "out" / "renderer-boxes.png").is_file()
