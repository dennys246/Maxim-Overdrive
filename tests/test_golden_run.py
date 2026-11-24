"""scripts/golden_run.py, the golden job's procedure: import, draw under a display, judge (B7; S2A-S1, S2E-S1).

A real run needs Xvfb and llvmpipe, which exist only in the golden image (ci/godot-golden/), so these tests drive the
procedure with a stand-in Godot: a script that answers ``--import`` by marking the project it imported, and draws by
copying a frame, printing what the real Godot prints, and a parse error when the project it draws was never imported
(S2D-S2), as the real Godot does for a ``class_name``. They prove the procedure's decisions, and that it reuses the
gate's scans: an error line, a non-zero exit, a missing frame and a timeout all fail the job, whatever the frame looks
like.
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
from tests.test_golden_fuel import gf  # registers golden_fuel and its imports, which golden_run imports
from tests.test_golden_measures import gm
from tests.test_golden_stability import gs  # registers golden_stability

ROOT = Path(__file__).resolve().parents[1]
assert gc is not None
assert gcmp is not None
assert gm is not None
assert gf is not None
assert gs is not None
_spec = importlib.util.spec_from_file_location("golden_run", ROOT / "scripts" / "golden_run.py")
assert _spec is not None
assert _spec.loader is not None
gr = importlib.util.module_from_spec(_spec)
sys.modules["golden_run"] = gr
_spec.loader.exec_module(gr)

FAKE_GODOT = f"""#!{sys.executable}
import os, shutil, sys
mode = os.environ["FAKE_GODOT_MODE"]
project = sys.argv[sys.argv.index("--path") + 1]
mark = os.path.join(project, ".godot", "imported.mark")
if "--import" in sys.argv:
    os.makedirs(os.path.dirname(mark), exist_ok=True)
    open(mark, "w").close()
    sys.exit(0)
print({LOG!r}, end="")
if not os.path.exists(mark):  # as the real Godot fails on a class_name in a project never imported
    print('SCRIPT ERROR: Parse Error: Identifier "EnginePin" not declared in the current scope.')
user = sys.argv[sys.argv.index("--") + 1:]
outs = [a.removeprefix("--shot=").split(":", 3)[3] for a in user if a.startswith("--shot=")]
yaws = [x.removeprefix("--yaw=") for x in user if x.startswith("--yaw=")]
for a in user:
    if a.startswith("--out=") and yaws:  # the cut-away scene: one pair at the yaw step it was given
        d, k = a.removeprefix("--out="), yaws[0]
        outs += [os.path.join(d, f"cut-end-k{{k}}-with.png"), os.path.join(d, f"cut-end-k{{k}}-without.png")]
    elif a.startswith("--out="):  # the stability scene: one frame stands in for its 32
        outs.append(os.path.join(a.removeprefix("--out="), "stab-rig-72-0.png"))
if any(not os.path.isabs(o) for o in outs):
    print("ERROR: Can't save PNG at a relative path")  # the real Godot reads it against the project
    sys.exit(1)
if mode == "error":
    print("SCRIPT ERROR: something broke")
if mode == "hang":
    while True:
        pass
for o in outs:
    if mode != "no-frame":
        shutil.copy(os.environ["FAKE_GODOT_FRAME"], o)
    if mode != "no-footprints" and os.path.basename(o).startswith("fuel-"):  # golden.gd writes one per fuel shot
        open(o[:-4] + ".segments.json", "w").write("[]")
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
    """A stand-in Godot, a golden per tier for the build its log names, a frame it will draw, and the measured checks
    recorded instead of run (they are tested on real-shaped frames in tests/test_golden_measures.py)."""
    rgb = np.zeros((72, 128, 3), dtype=np.uint8)
    rgb[10:20, 10:20] = (200, 120, 40)
    goldens = tmp_path / "goldens"
    for tier in gr.TIERS:
        (goldens / KEY / tier).mkdir(parents=True)
        Image.fromarray(rgb).save(goldens / KEY / tier / "fire.png")
        Image.fromarray(rgb).save(goldens / KEY / tier / "fuel.png")
    Image.fromarray(rgb).save(tmp_path / "frame.png")
    monkeypatch.setattr(gr, "GOLDENS", goldens)
    measured: list[Path] = []

    def record(out: Path, cut: Path) -> list[str]:
        measured.append(cut)
        return []

    monkeypatch.setattr(gr, "measured_findings", record)
    monkeypatch.setenv("FAKE_GODOT_FRAME", str(tmp_path / "frame.png"))
    monkeypatch.setenv("FAKE_GODOT_MODE", "ok")
    return _executable(tmp_path / "godot", FAKE_GODOT), measured


def _main(tmp_path: Path, godot: str, *extra: str) -> int:
    code: int = gr.main(["--godot", godot, "--out", str(tmp_path / "out"), "--no-xvfb", *extra], work_parent=tmp_path)
    return code


def test_matching_frames_pass_every_shot_is_drawn_and_the_logs_are_kept(setup, tmp_path, monkeypatch, capsys):
    godot, measured = setup
    monkeypatch.setattr(gr, "XVFB", ())  # judged as on the CI image, with no X server to wrap Godot in
    code = gr.main(["--godot", godot, "--out", str(tmp_path / "out")], work_parent=tmp_path)
    assert code == 0, capsys.readouterr().err
    printed = capsys.readouterr().out
    assert printed.endswith("golden_run: PASS (27 shots, 6 goldens, cut-away, stick stability)\n")
    assert printed.count("res://tests/cutaway_check.tscn took") == 4
    assert printed.count("res://tests/golden.tscn took") == 3  # one call per tier
    out = tmp_path / "out"
    assert sorted(p.name for p in out.glob("*.png")) == sorted(name for name, *_ in gr.SHOTS)
    assert "llvmpipe (LLVM 20.1.2, 256 bits)" in (out / "golden.log").read_text()
    for k in range(4):  # one call per yaw step
        assert (out / f"cutaway-k{k}.log").is_file()
        assert (out / "cutaway" / f"cut-end-k{k}-with.png").is_file()
    assert measured == [out / "cutaway"]
    assert not list(out.glob("*.diff.png"))


@pytest.mark.parametrize(
    "case",
    [
        ("error", "Godot printed an error: SCRIPT ERROR: something broke"),
        ("exit-2", "exited 2"),
        ("no-frame", "draw: no frame at"),
        ("no-footprints", "draw: no footprints beside"),
    ],
)
def test_a_draw_that_errs_exits_badly_or_writes_nothing_fails_and_judges_nothing(
    setup, tmp_path, monkeypatch, capsys, case
):
    godot, measured = setup
    mode, finding = case
    monkeypatch.setenv("FAKE_GODOT_MODE", mode)
    assert _main(tmp_path, godot) == 1
    assert finding in capsys.readouterr().err
    assert measured == []


def test_a_hang_is_ended_by_the_timeout(setup, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FAKE_GODOT_MODE", "hang")
    assert _main(tmp_path, setup[0], "--timeout", "2") == 1
    assert "timed out after 2 s" in capsys.readouterr().err


def test_a_frame_that_differs_from_its_golden_fails_per_tier_and_its_difference_is_written(
    setup, tmp_path, monkeypatch, capsys
):
    other = np.full((72, 128, 3), 255, dtype=np.uint8)
    Image.fromarray(other).save(tmp_path / "other.png")
    monkeypatch.setenv("FAKE_GODOT_FRAME", str(tmp_path / "other.png"))
    monkeypatch.setattr(gr, "XVFB", ())  # judged as on the CI image, with no X server to wrap Godot in
    assert gr.main(["--godot", setup[0], "--out", str(tmp_path / "out")], work_parent=tmp_path) == 1
    err = capsys.readouterr().err
    for tier in gr.TIERS:
        assert f"{tier}/fire.png: mean ΔE" in err
        assert (tmp_path / "out" / f"fire-{tier}.diff.png").is_file()


def test_every_measured_finding_fails_the_job(tmp_path, monkeypatch):
    monkeypatch.setattr(gm, "cutaway_findings", lambda cut: ["cutaway: hidden"])
    monkeypatch.setattr(gm, "colour_alone_findings", lambda out, tier: [f"{tier}: glow: dim"] if tier == "max" else [])
    monkeypatch.setattr(gm, "agreement_findings", lambda name, tier, rig: [f"tiers: {name}"])
    monkeypatch.setattr(gm, "speckle_findings", lambda out: ["rig: speckle"])
    monkeypatch.setattr(gf, "fuel_findings", lambda out: ["burning (rig): dim"])
    monkeypatch.setattr(gs, "findings", lambda frames: ["stick stability (laptop-30): crawls"])
    for tier in gr.TIERS:
        Image.fromarray(np.zeros((90, 160, 3), dtype=np.uint8)).save(tmp_path / f"fire-{tier}.png")
    assert gr.measured_findings(tmp_path, tmp_path) == [
        "cutaway: hidden",
        "max: glow: dim",
        "rig: speckle",
        "burning (rig): dim",
        "stick stability (laptop-30): crawls",
        "tiers: laptop",
        "tiers: max",
    ]


def test_a_failed_import_draws_nothing(setup, tmp_path, monkeypatch, capsys):
    godot = setup[0]
    monkeypatch.setattr(gr, "CLIENT", tmp_path / "client")
    (tmp_path / "client").mkdir()
    monkeypatch.setattr(gc, "import_changes", lambda source, imported: ["import: created x.gd.uid"])
    assert _main(tmp_path, godot) == 1
    assert "import: created x.gd.uid" in capsys.readouterr().err
    assert not (tmp_path / "out" / "golden.log").exists()


def test_off_the_ci_image_the_goldens_are_not_judged_and_stale_cut_frames_are_cleared(
    setup, tmp_path, monkeypatch, capsys
):
    godot, measured = setup
    other = np.full((72, 128, 3), 255, dtype=np.uint8)  # would fail every golden
    Image.fromarray(other).save(tmp_path / "other.png")
    monkeypatch.setenv("FAKE_GODOT_FRAME", str(tmp_path / "other.png"))
    stale = tmp_path / "out" / "cutaway" / "cut-old-k0-with.png"
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"x")
    assert _main(tmp_path, godot) == 0  # --no-xvfb
    printed = capsys.readouterr().out
    assert "goldens not judged" in printed
    assert printed.endswith("golden_run: PASS (27 shots, goldens not judged, cut-away, stick stability)\n")
    assert measured == [tmp_path / "out" / "cutaway"]
    assert not stale.exists()


def test_by_default_godot_draws_under_xvfb(setup, tmp_path, monkeypatch, capsys):
    mark = tmp_path / "wrapper-args"
    monkeypatch.setenv("FAKE_WRAPPER_MARK", str(mark))
    wrapper = _executable(tmp_path / "xvfb-run", WRAPPER)
    monkeypatch.setattr(gr, "XVFB", (wrapper, "-a", "-s", "-screen 0 1280x720x24"))
    assert gr.main(["--godot", setup[0], "--out", str(tmp_path / "out")], work_parent=tmp_path) == 0
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
    assert gr.main(["--godot", setup[0], "--out", "out", "--no-xvfb"], work_parent=tmp_path) == 0, (
        capsys.readouterr().err
    )
    assert (tmp_path / "out" / "fire-rig.png").is_file()
