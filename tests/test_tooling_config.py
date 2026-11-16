"""The settings CLAUDE.md's standards rely on are in force, not merely mentioned in pyproject.toml."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import tomli

ROOT = Path(__file__).resolve().parents[1]


def _config() -> dict[str, Any]:
    tool: dict[str, Any] = tomli.loads((ROOT / "pyproject.toml").read_text())["tool"]
    return tool


def test_the_no_silent_swallow_rules_are_selected_and_not_ignored():
    lint = _config()["ruff"]["lint"]
    selected, ignored = set(lint["select"]), set(lint.get("ignore", []))
    assert {"BLE", "S110"} <= selected
    assert not {"BLE", "BLE001", "S110"} & ignored
    for pattern, rules in lint.get("per-file-ignores", {}).items():
        assert pattern.startswith("tests/") or not {"BLE", "BLE001", "S110"} & set(rules), pattern


def test_red_gates_are_strict_and_warnings_are_errors():
    pytest_cfg = _config()["pytest"]["ini_options"]
    assert pytest_cfg["xfail_strict"] is True
    assert pytest_cfg["filterwarnings"] == ["error"]
    assert "--strict-markers" in pytest_cfg["addopts"]


def test_coverage_measures_branches_over_src_and_scripts():
    coverage = _config()["coverage"]
    assert coverage["run"]["branch"] is True
    assert set(coverage["run"]["source"]) == {"maxim_overdrive", "scripts"}
    assert "omit" not in coverage["run"]  # an omitted file is uncovered code that nobody sees


def test_mypy_is_strict():
    mypy = _config()["mypy"]
    assert mypy["strict"] is True
    assert set(mypy["files"]) == {"src", "tests", "scripts"}
    relaxed = [o for o in mypy.get("overrides", []) if "disallow_untyped_defs" in o]
    assert all(o["module"] == ["tests.*"] for o in relaxed)  # only test signatures may go unannotated


# Canaries one step past each cap, and one at the complexity cap that must stay quiet. Asking ruff itself, rather than
# reading pyproject.toml for keys that relax a rule, closes every way to relax one, including keys ruff adds later.
CANARY = (
    "def at_cap(x):\n" + "".join(f"    if x == {i}:\n        x += 1\n" for i in range(9)) + "    return x\n\n\n"
    "def complex_(x):\n" + "".join(f"    if x == {i}:\n        x += 1\n" for i in range(10)) + "    return x\n\n\n"
    "def returns(x):\n" + "".join(f"    if x == {i}:\n        return {i}\n" for i in range(6)) + "    return x\n\n\n"
    "def branches(x):\n" + "".join(f"    if x == {i}:\n        x += 1\n" for i in range(13)) + "    return x\n\n\n"
    "def statements(x):\n" + "".join(f"    x += {i}\n" for i in range(51)) + "    return x\n"
)
EXPECTED = {
    "complex_": {"C901"},
    "returns": {"PLR0911"},
    "branches": {"C901", "PLR0912"},
    "statements": {"PLR0915"},
}


def _ruff(*args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, "-m", "ruff", *args]
    return subprocess.run(cmd, cwd=ROOT, input=stdin, capture_output=True, text=True, check=False)


def _capped_hits(path: str) -> dict[str, set[str]]:
    """The complexity codes ruff reports on the canary, as if it were the file at ``path``, by canary function."""
    out = _ruff("check", "--force-exclude", "--output-format", "json", "--stdin-filename", path, "-", stdin=CANARY)
    starts = {ln.split("(")[0][4:]: i for i, ln in enumerate(CANARY.splitlines(), 1) if ln.startswith("def ")}
    by_line = {line: name for name, line in starts.items()}
    hits: dict[str, set[str]] = {name: set() for name in starts}
    for d in json.loads(out.stdout or "[]"):
        if d["code"] in {"C901", "PLR0911", "PLR0912", "PLR0915"} and d["location"]["row"] in by_line:
            hits[by_line[d["location"]["row"]]].add(d["code"])
    return hits


@pytest.mark.parametrize(
    "path", ["src/maxim_overdrive/world/canary.py", "src/maxim_overdrive/canary.py", "scripts/canary.py"]
)
def test_ruff_enforces_each_complexity_cap_at_its_threshold(path):
    hits = _capped_hits(path)
    assert hits.pop("at_cap") == set()  # complexity 10 is allowed: the cap is 10, not lower
    assert hits == EXPECTED


def test_tests_waive_only_the_statement_count():
    hits = _capped_hits("tests/test_canary.py")
    assert hits.pop("at_cap") == set()
    assert hits == {**EXPECTED, "statements": set()}


def test_ruff_lints_every_tracked_python_file():
    """An exclude anywhere (a key, a glob, an extended config) shows up as a tracked file ruff doesn't see."""
    shown = _ruff("check", "--show-files", "src", "tests", "scripts")
    assert shown.returncode == 0, shown.stderr
    seen = {str(Path(p).resolve().relative_to(ROOT)) for p in shown.stdout.split() if p.endswith(".py")}
    listed = subprocess.run(
        ["git", "ls-files", "src", "tests", "scripts"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    tracked = {f for f in listed.stdout.splitlines() if f.endswith(".py")}
    assert tracked - seen == set()


def test_no_nested_ruff_config_can_override_the_root_one():
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    assert not [f for f in tracked.splitlines() if Path(f).name in {"ruff.toml", ".ruff.toml"}]
    assert [f for f in tracked.splitlines() if Path(f).name == "pyproject.toml"] == ["pyproject.toml"]
