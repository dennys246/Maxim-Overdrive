"""The gate's Godot checks against the real Godot: one fixture project per failure mode (B6, CR-B1).

Godot's exit status says nothing about a parse error or a runtime error, so every check in scripts/godot_check.py
reads what Godot printed. Each check is proved here by a fixture project in tmp_path whose defect that check names: a
parse error, a warning promoted to an error (in res://addons too), a runtime error the runner survives, a runtime
error before quit (a hang), a hang with no error, a missing sentinel, a failing assertion, a null load, a script
committed without its ``.uid``, and another engine version. Deleting a check turns its test red.

These tests run Godot, so they are ``slow`` (the import alone takes about eight seconds, so it runs once per session
and the fixtures that don't test it start from a copy of its result). They run with ``MAXIM_OVERDRIVE_ALL_TIERS=1``,
which the gate sets, and then a missing Godot fails them instead of skipping. Godot only ever runs through
``godot_check.run_godot``, with HOME and the XDG directories inside tmp_path.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import pytest

from tests.test_godot_check import PINS, gc

CLIENT = Path(__file__).resolve().parents[1] / "client"
FAST_TIMEOUT_S = 60.0  # for a fixture that should finish; a hang gets the shorter limit below
HANG_TIMEOUT_S = 5.0

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        not os.environ.get("MAXIM_OVERDRIVE_ALL_TIERS"), reason="slow: runs Godot; set MAXIM_OVERDRIVE_ALL_TIERS=1"
    ),
]


@pytest.fixture(scope="session")
def godot() -> str:
    found: str | None = gc.find_godot(os.environ, sys.platform)
    if found is None:
        pytest.fail("no Godot: install 4.7.2 (ci/install_godot.sh) or set GODOT; the gate needs it (B6)")
    return found


@pytest.fixture(scope="session")
def imported(godot, tmp_path_factory) -> Path:
    """The client, imported once, as every fixture that doesn't test the import starts from it."""
    work = tmp_path_factory.mktemp("imported")
    project = Path(gc.copy_project(CLIENT, work / "client"))
    assert gc.import_step(godot, CLIENT, project, home=work / "home", timeout_s=FAST_TIMEOUT_S) == []
    return project


@pytest.fixture
def project(imported, tmp_path) -> Path:
    return Path(shutil.copytree(imported, tmp_path / "client"))


def _add(project: Path, rel: str, source: str) -> None:
    path = project / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source)
    Path(f"{path}.uid").write_text("uid://bmaximfixture\n")  # so only the defect under test is new


def _load(godot: str, project: Path, tmp_path: Path) -> list[str]:
    found: list[str] = gc.load_step(godot, project, home=tmp_path / "home", timeout_s=FAST_TIMEOUT_S)
    return found


def _tests(godot: str, project: Path, tmp_path: Path, timeout_s: float = FAST_TIMEOUT_S) -> list[str]:
    found: list[str] = gc.client_tests_step(godot, project, home=tmp_path / "home", timeout_s=timeout_s)
    return found


def test_the_clean_client_passes_the_whole_gate(godot, tmp_path, capsys):
    """The full path a push takes: version, a fresh import, every script loaded, the client tests."""
    assert gc.main(["--project", str(CLIENT)], work_parent=tmp_path) == 0, capsys.readouterr().err
    assert "godot_check: PASS" in capsys.readouterr().out
    assert list(tmp_path.iterdir()) == []  # the work directory is removed


@pytest.mark.parametrize(
    "case",
    [
        ("addons/engine/broken.gd", "extends RefCounted\n\nfunc f( -> void:\n\tpass\n", "Parse Error: Expected"),
        ("game/broken.gd", "extends RefCounted\n\nfunc f( -> void:\n\tpass\n", "Parse Error: Expected"),
        ("addons/engine/untyped.gd", "extends RefCounted\n\nvar x = 1\n", "has no static type"),
        ("game/untyped.gd", "extends RefCounted\n\nvar x = 1\n", "has no static type"),
    ],
    ids=["parse-error-in-addons", "parse-error-in-game", "warning-as-error-in-addons", "warning-as-error-in-game"],
)
def test_a_script_that_does_not_compile_is_named_by_the_load_check(godot, project, tmp_path, case):
    """Godot prints the error and exits 0; load() returns a script that can't be instantiated, not null."""
    rel, source, message = case
    _add(project, rel, source)
    found = _load(godot, project, tmp_path)
    assert f"load: res://{rel} is null or cannot be instantiated" in found
    assert any("Godot printed an error" in f and message in f for f in found), found


def test_addons_are_exempt_from_warnings_unless_project_godot_says_otherwise(godot, project, tmp_path):
    """Godot 4.7.2 exempts res://addons by default, where the engine half lives; deleting the setting is the proof."""
    settings = project / "project.godot"
    settings.write_text(settings.read_text().replace("gdscript/warnings/directory_rules={}\n", ""))
    _add(project, "addons/engine/untyped.gd", "extends RefCounted\n\nvar x = 1\n")
    found = _load(godot, project, tmp_path)
    assert not any("untyped.gd" in f for f in found), found


def test_a_null_load_is_named(godot, project, tmp_path):
    args = ["--headless", "--path", str(project), "-s", "res://tests/load_all.gd", "--", "res://missing.gd"]
    run = gc.run_godot(godot, "load", args, home=tmp_path / "home", timeout_s=FAST_TIMEOUT_S)
    assert gc.load_findings(run, 1) == ["load: res://missing.gd is null or cannot be instantiated"]


def test_a_runtime_error_in_a_test_is_caught_though_the_runner_says_pass(godot, project, tmp_path):
    """The error aborts only its test method; the runner carries on and prints PASS, so only the scan sees it."""
    _add(project, "tests/unit/test_runtime_error.gd", RUNTIME_ERROR_TEST)
    found = _tests(godot, project, tmp_path)
    assert found
    assert all("Godot printed an error" in f for f in found), found
    assert any("Out of bounds get index '3'" in f for f in found), found


RUNTIME_ERROR_TEST = """extends RefCounted


func test_reads_past_the_end(t: TestContext) -> void:
\tvar a: Array[int] = [1, 2, 3]
\tvar i: int = a.size()
\tt.check(a[i] == 0, "unreachable")
"""


def test_a_runtime_error_before_quit_hangs_and_the_timeout_ends_it(godot, project, tmp_path):
    """CR-B1's case: an -s script errors before quit(), and Godot prints the error and keeps running."""
    runner = project / "tests" / "run.gd"
    error_first = "\tvar none: Array[int] = []\n\tprint(none[0])\n\tvar t: TestContext"
    runner.write_text(runner.read_text().replace("\tvar t: TestContext", error_first, 1))
    found = _tests(godot, project, tmp_path, timeout_s=HANG_TIMEOUT_S)
    assert any("timed out after 5 s" in f for f in found), found
    assert any("Out of bounds get index '0'" in f for f in found), found


def test_a_hang_with_no_error_is_ended_by_the_timeout(godot, project, tmp_path):
    _add(project, "tests/unit/test_hang.gd", HANG_TEST)
    found = _tests(godot, project, tmp_path, timeout_s=HANG_TIMEOUT_S)
    assert any("timed out after 5 s" in f for f in found), found
    assert not any("Godot printed an error" in f for f in found), found


HANG_TEST = """extends RefCounted


func test_never_returns(t: TestContext) -> void:
\tvar n: int = 0
\twhile n >= 0:
\t\tn = (n + 1) % 1000
\tt.check(false, "unreachable")
"""


def test_a_runner_that_never_prints_the_sentinel_fails_though_godot_exits_0(godot, project, tmp_path):
    runner = project / "tests" / "run.gd"
    runner.write_text(runner.read_text().replace("\tprint(t.summary())\n", ""))
    found = _tests(godot, project, tmp_path)
    assert len(found) == 1, found
    assert "not 'client-tests: PASS <n> tests'" in found[0]


def test_a_failing_assertion_fails_the_run(godot, project, tmp_path):
    failing = 'extends RefCounted\n\n\nfunc test_fails(t: TestContext) -> void:\n\tt.check_eq(1 + 1, 3, "sum")\n'
    _add(project, "tests/unit/test_fails.gd", failing)
    found = _tests(godot, project, tmp_path)
    assert len(found) == 1, found
    assert "'client-tests: FAIL 1 of" in found[0]


def test_a_script_committed_without_its_uid_is_named_by_the_import(godot, tmp_path):
    source = gc.copy_project(CLIENT, tmp_path / "source")
    (source / "game" / "extra.gd").write_text("extends RefCounted\n")
    project = gc.copy_project(source, tmp_path / "project")
    found = gc.import_step(godot, source, project, home=tmp_path / "home", timeout_s=FAST_TIMEOUT_S)
    assert found == ["import: created game/extra.gd.uid; commit it (run the import in client/ once)"]


def test_another_godot_version_is_refused(godot, tmp_path):
    assert gc.version_findings(godot, pins=PINS, home=tmp_path / "home", timeout_s=FAST_TIMEOUT_S) == []
    other = PINS.replace("GODOT_VERSION=4.7.2.", "GODOT_VERSION=4.7.3.")
    found = gc.version_findings(godot, pins=other, home=tmp_path / "home", timeout_s=FAST_TIMEOUT_S)
    assert found == ["version: Godot is '4.7.2.stable.official.ed1daf0bf', the pin is 4.7.3.stable.official.ed1daf0bf"]


def test_godot_keeps_its_per_user_files_in_the_home_it_is_given(godot, project, tmp_path):
    """Godot writes a log, editor settings and caches per user; they land in tmp_path, not the real home."""
    home = tmp_path / "home"
    assert _tests(godot, project, tmp_path) == []
    assert list(home.rglob("godot.log")), "the run's log should be inside the given home"
