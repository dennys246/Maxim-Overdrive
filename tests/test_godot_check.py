"""scripts/godot_check.py, the gate's Godot step (B6; client_rendering.md §7.3, CR-B1): its checks on Godot's output.

These run without Godot, on output shaped like what Godot 4.7.2 prints. tests/test_godot_gate_fixtures.py runs the
same checks against the real Godot on a fixture project per failure mode.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("godot_check", ROOT / "scripts" / "godot_check.py")
assert _spec is not None
assert _spec.loader is not None
gc = importlib.util.module_from_spec(_spec)
sys.modules["godot_check"] = gc
_spec.loader.exec_module(gc)

PINS = gc.PINS.read_text()


def _run(lines: list[str], code: int | None = 0, step: str = "tests") -> object:
    return gc.Run(step, tuple(lines), code, 9.0)


def test_the_pinned_version_is_read_from_ci_godot_env():
    assert gc.pinned_version(PINS) == "4.7.2.stable.official.ed1daf0bf"
    with pytest.raises(ValueError, match="GODOT_VERSION"):
        gc.pinned_version("GODOT_RELEASE_URL=x\n")


@pytest.mark.parametrize(
    "line",
    [
        'SCRIPT ERROR: Parse Error: Variable "x" has no static type. (Warning treated as error.)',
        'ERROR: Failed to load script "res://a.gd" with error "Parse error".',
        "   Parse Error: something",
        "SCRIPT ERROR: Invalid access to property or key 'x' on a base object of type 'Nil'.",
    ],
)
def test_any_error_line_is_a_finding(line):
    found = gc.error_findings(_run(["Godot Engine v4.7.2", line, "client-tests: PASS 3 tests"]))
    assert found == [f"tests: Godot printed an error: {line.strip()}"]


def test_a_timeout_is_a_finding_and_a_quiet_run_is_not():
    assert gc.error_findings(_run(["Godot Engine v4.7.2", "WARNING: something"])) == []
    assert gc.error_findings(_run([], code=None)) == [
        "tests: timed out after 9 s (Godot keeps running after a script error)"
    ]


@pytest.mark.parametrize(
    ("lines", "code", "finding"),
    [
        (["client-tests: PASS 4 tests"], 0, None),
        (["client-tests: PASS 4 tests", "", "  "], 0, None),
        (["client-tests: PASS 4 tests"], 1, "printed PASS but exited 1"),
        (["client-tests: PASS 4 tests"], None, "printed PASS but exited None"),
        (["client-tests: PASS 0 tests"], 0, "not 'client-tests: PASS <n> tests'"),
        (["client-tests: FAIL 1 of 4 tests"], 1, "not 'client-tests: PASS <n> tests'"),
        (["client-tests: PASS 4 tests", "WARNING: ObjectDB instances leaked at exit"], 0, "the last line is"),
        (["Godot Engine v4.7.2"], 0, "not 'client-tests: PASS <n> tests'"),
        ([], 0, "the last line is ''"),
    ],
)
def test_the_sentinel_must_be_the_last_line_and_the_run_must_exit_0(lines, code, finding):
    found = gc.sentinel_findings(_run(lines, code))
    assert found == [] if finding is None else (len(found) == 1 and finding in found[0])


def test_the_load_check_names_each_unloadable_script_and_wants_the_full_count():
    good = _run(["godot-check: loaded 2 scripts"], step="load")
    assert gc.load_findings(good, 2) == []
    bad = _run(["godot-check: unloadable res://a.gd", "godot-check: loaded 2 scripts"], step="load")
    assert gc.load_findings(bad, 2) == ["load: res://a.gd is null or cannot be instantiated"]
    assert gc.load_findings(good, 3) == ["load: expected 'godot-check: loaded 3 scripts', got [2]"]
    assert gc.load_findings(_run([], step="load"), 1) == ["load: expected 'godot-check: loaded 1 scripts', got nothing"]


def test_find_godot_prefers_the_environment_then_the_mac_app_then_the_path(tmp_path, monkeypatch):
    app = tmp_path / "Godot"
    monkeypatch.setattr(gc, "MACOS_APP", app)

    def which(name: str) -> str:
        return f"/on/path/{name}"

    assert gc.find_godot({"GODOT": "/x/godot"}, "darwin", which) == "/x/godot"
    assert gc.find_godot({}, "darwin", which) == "/on/path/godot"  # no app installed
    app.write_text("")
    assert gc.find_godot({"GODOT": ""}, "darwin", which) == str(app)
    assert gc.find_godot({}, "linux", which) == "/on/path/godot"
    assert gc.find_godot({}, "linux", lambda name: None) is None


def test_godot_runs_with_every_per_user_directory_inside_its_home(tmp_path):
    env = gc.godot_env(tmp_path)
    assert env["HOME"] == str(tmp_path)
    for key in ("XDG_DATA_HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME"):
        assert Path(env[key]).parent.parent == tmp_path or Path(env[key]).parent == tmp_path


def _project(tmp_path: Path) -> Path:
    src = tmp_path / "src"
    (src / "a").mkdir(parents=True)
    (src / ".godot" / "editor").mkdir(parents=True)
    (src / "a" / "x.gd").write_text("extends RefCounted\n")
    (src / "a" / "x.gd.uid").write_text("uid://abc\n")
    (src / ".godot" / "editor" / "cached.gd").write_text("")
    (src / "project.godot").write_text("config_version=5\n")
    return src


def test_the_copy_is_a_fresh_checkout_and_scripts_in_the_cache_are_not_listed(tmp_path):
    src = _project(tmp_path)
    assert gc.scripts_in(src) == ["res://a/x.gd"]
    copy = gc.copy_project(src, tmp_path / "copy")
    assert not (copy / ".godot").exists()
    assert (copy / "a" / "x.gd.uid").is_file()


def test_the_import_may_change_only_its_cache(tmp_path):
    src = _project(tmp_path)
    copy = gc.copy_project(src, tmp_path / "copy")
    (copy / ".godot").mkdir()
    (copy / ".godot" / "uid_cache.bin").write_bytes(b"\0")
    assert gc.import_changes(src, copy) == []
    (copy / "a" / "y.gd.uid").write_text("uid://new\n")
    (copy / "project.godot").write_text("config_version=5\n[rewritten]\n")
    assert gc.import_changes(src, copy) == [
        "import: created a/y.gd.uid; commit it (run the import in client/ once)",
        "import: rewrote project.godot; commit the editor's form of it",
    ]


def test_without_godot_the_gate_fails_and_says_how_to_get_it(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(gc, "find_godot", lambda env, platform: None)
    assert gc.main([], work_parent=tmp_path) == 1
    assert "install 4.7.2 (ci/install_godot.sh) or set GODOT" in capsys.readouterr().err


def test_the_gate_prints_every_finding_and_fails(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(gc, "find_godot", lambda env, platform: "/x/godot")
    monkeypatch.setattr(gc, "check", lambda source, **kw: ["load: res://a.gd is null or cannot be instantiated"])
    assert gc.main([], work_parent=tmp_path) == 1
    out = capsys.readouterr()
    assert "godot_check: load: res://a.gd is null or cannot be instantiated" in out.err
    assert out.out == "godot_check: FAIL (/x/godot)\n"
    assert list(tmp_path.iterdir()) == []


def test_a_non_zero_exit_is_a_finding_and_a_timeout_is_left_to_the_error_scan():
    assert gc.exit_findings(_run([], code=0)) == []
    assert gc.exit_findings(_run([], code=None)) == []
    assert gc.exit_findings(_run([], code=3, step="draw")) == ["draw: exited 3"]
