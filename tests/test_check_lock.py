"""scripts/check_lock.py: the gate refuses an environment that doesn't match this Python's lockfile (O32)."""

from __future__ import annotations

import importlib.util
import sys
from importlib import metadata
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("check_lock", ROOT / "scripts" / "check_lock.py")
assert _spec is not None
assert _spec.loader is not None
check = importlib.util.module_from_spec(_spec)
sys.modules["check_lock"] = check
_spec.loader.exec_module(check)

LOCK = "# header\nnumpy==2.5.5\n    # via maxim-overdrive\nPyYAML==6.0.3 ; python_version >= '3'\nTypes_PyYAML==6.0.1\n"


def _installed(versions: dict[str, str]):
    def lookup(name: str) -> str:
        if name not in versions:
            raise metadata.PackageNotFoundError(name)
        return versions[name]

    return lookup


def test_pins_normalise_names_and_skip_comments_and_markers() -> None:
    assert check.pins(LOCK) == {"numpy": "2.5.5", "pyyaml": "6.0.3", "types-pyyaml": "6.0.1"}


def test_a_matching_environment_has_no_findings() -> None:
    env = {"numpy": "2.5.5", "pyyaml": "6.0.3", "types-pyyaml": "6.0.1"}
    assert check.findings(LOCK, _installed(env)) == []


def test_a_different_or_missing_package_is_a_finding() -> None:
    found = check.findings(LOCK, _installed({"numpy": "2.6.0", "pyyaml": "6.0.3"}))
    assert found == ["numpy is 2.6.0, locked at 2.5.5", "types-pyyaml is locked at 6.0.1 but not installed"]


def test_a_python_without_a_lockfile_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert check.main(tmp_path, (3, 11)) == 1
    assert "no lockfile for Python 3.11" in capsys.readouterr().err


def test_main_compares_the_lock_with_what_is_installed(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "constraints").mkdir()
    lock = tmp_path / "constraints" / "py3.12.txt"
    lock.write_text(f"pyyaml=={metadata.version('pyyaml')}\n")
    assert check.main(tmp_path, (3, 12)) == 0
    lock.write_text("pyyaml==0.0.1\n")
    assert check.main(tmp_path, (3, 12)) == 1
    assert "pyyaml is" in capsys.readouterr().err


def test_the_drift_job_is_the_only_way_to_skip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAXIM_OVERDRIVE_UNLOCKED", "1")
    assert check.main(tmp_path, (3, 11)) == 0
    drift = yaml.safe_load((ROOT / ".github" / "workflows" / "drift.yml").read_text())
    assert drift["jobs"]["drift"]["env"]["MAXIM_OVERDRIVE_UNLOCKED"] == "1"
    gate = yaml.safe_load((ROOT / ".github" / "workflows" / "test.yml").read_text())
    assert "MAXIM_OVERDRIVE_UNLOCKED" not in str(gate)


def test_every_ci_python_has_a_lockfile_and_ci_installs_from_it() -> None:
    gate = yaml.safe_load((ROOT / ".github" / "workflows" / "test.yml").read_text())
    job = gate["jobs"]["prepush"]
    versions = job["strategy"]["matrix"]["python-version"]
    assert versions
    assert all((ROOT / "constraints" / f"py{v}.txt").is_file() for v in versions)
    install = next(s["run"] for s in job["steps"] if s.get("name") == "Install")
    assert "-c constraints/py${{ matrix.python-version }}.txt" in install


def test_the_drift_job_runs_on_a_schedule_and_unpinned() -> None:
    drift = yaml.safe_load((ROOT / ".github" / "workflows" / "drift.yml").read_text())
    assert drift[True]["schedule"]  # PyYAML reads the bare key `on` as True
    install = next(s["run"] for s in drift["jobs"]["drift"]["steps"] if s.get("name") == "Install, unpinned")
    assert "-c " not in install
