"""The settings CLAUDE.md's standards rely on are in force, not merely mentioned in pyproject.toml."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

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


CAPPED = ("C901", "PLR0911", "PLR0912", "PLR0915")


def _relaxes(entry: str) -> bool:
    """Ruff matches rule selectors by prefix, so "C", "PLR09" and "ALL" each relax every capped rule."""
    return entry == "ALL" or any(code.startswith(entry) for code in CAPPED)


def test_the_complexity_rules_are_selected_and_not_relaxed():
    ruff = _config()["ruff"]
    lint = ruff["lint"]
    assert {"C90", "PL"} <= set(lint["select"])
    assert lint["mccabe"]["max-complexity"] == 10
    for table in (ruff, lint):
        for key in ("ignore", "extend-ignore"):
            assert not [e for e in table.get(key, []) if _relaxes(e)], key
        for key in ("per-file-ignores", "extend-per-file-ignores"):
            for pattern, rules in table.get(key, {}).items():
                relaxed = {r for r in rules if _relaxes(r)}
                # tests may waive the statement count; nothing else, and nowhere else
                assert relaxed <= {"PLR0915"}, (key, pattern)
                assert not relaxed or pattern.startswith("tests/"), (key, pattern)
    for key in ("exclude", "extend-exclude"):
        assert not [e for e in ruff.get(key, []) if e.startswith(("src", "scripts", "*", "/", "."))], key
    for key in ("max-branches", "max-returns", "max-statements"):
        assert key not in lint.get("pylint", {})  # ruff's defaults (12 branches, 6 returns, 50 statements) hold


def test_no_nested_ruff_config_can_override_the_root_one():
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    assert not [f for f in tracked.splitlines() if Path(f).name in {"ruff.toml", ".ruff.toml"}]
    assert [f for f in tracked.splitlines() if Path(f).name == "pyproject.toml"] == ["pyproject.toml"]
