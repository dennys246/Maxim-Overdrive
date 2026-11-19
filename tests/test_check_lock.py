"""scripts/check_lock.py: the gate refuses an environment that doesn't match this Python's lockfile (O32)."""

from __future__ import annotations

import importlib.util
import re
import sys
import tomllib
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


ENV = {"numpy": "2.5.5", "pyyaml": "6.0.3", "types-pyyaml": "6.0.1"}
PRESENT = ["numpy", "PyYAML", "types_PyYAML", "pip", "maxim_overdrive"]


def test_a_matching_environment_has_no_findings() -> None:
    assert check.findings(LOCK, _installed(ENV), PRESENT) == []


def test_a_different_or_missing_package_is_a_finding() -> None:
    found = check.findings(LOCK, _installed({"numpy": "2.6.0", "pyyaml": "6.0.3"}), PRESENT[:2])
    assert found == ["numpy is 2.6.0, locked at 2.5.5", "types-pyyaml is locked at 6.0.1 but not installed"]


def test_an_installed_package_the_lock_does_not_name_is_a_finding() -> None:
    """A stale tomli or a hand-installed pytest plugin would still be imported (LK-S2)."""
    found = check.findings(LOCK, _installed(ENV), [*PRESENT, "tomli", "pytest-randomly"])
    assert found == ["pytest-randomly is installed but not in the lock", "tomli is installed but not in the lock"]


def test_an_empty_lockfile_is_a_finding() -> None:
    assert check.findings("# only comments\n", _installed(ENV), PRESENT) == ["the lockfile pins nothing"]


def test_a_python_without_a_lockfile_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert check.main(tmp_path, (3, 11), argv=[]) == 1
    assert "no lockfile for Python 3.11" in capsys.readouterr().err


def test_main_compares_the_lock_with_what_is_installed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(check, "installed_names", lambda: ["PyYAML", "pip"])
    (tmp_path / "constraints").mkdir()
    lock = tmp_path / "constraints" / "py3.12.txt"
    lock.write_text(f"pyyaml=={metadata.version('pyyaml')}\n")
    assert check.main(tmp_path, (3, 12), argv=[]) == 0
    lock.write_text("pyyaml==0.0.1\n")
    assert check.main(tmp_path, (3, 12), argv=[]) == 1
    assert "pyyaml is" in capsys.readouterr().err
    assert check.main(tmp_path, (3, 12), argv=["--report"]) == 0  # the drift job's report never fails the run


@pytest.mark.parametrize(
    ("env", "allowed"),
    [
        ({"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "schedule"}, True),
        ({"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "workflow_dispatch"}, True),
        ({"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "push"}, False),
        ({"GITHUB_EVENT_NAME": "schedule"}, False),
        ({}, False),
    ],
)
def test_only_the_scheduled_drift_job_may_skip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, env: dict[str, str], allowed: bool
) -> None:
    """A developer setting MAXIM_OVERDRIVE_UNLOCKED=1 gets a refusal, not a clean PASS (LK-S1)."""
    for k in ("GITHUB_ACTIONS", "GITHUB_EVENT_NAME"):
        monkeypatch.delenv(k, raising=False)
    for k, v in {**env, "MAXIM_OVERDRIVE_UNLOCKED": "1"}.items():
        monkeypatch.setenv(k, v)
    assert check.main(tmp_path, (3, 11), argv=[]) == (0 if allowed else 1)


def test_the_drift_job_sets_the_skip_and_ci_does_not() -> None:
    drift = yaml.safe_load((ROOT / ".github" / "workflows" / "drift.yml").read_text())
    assert drift["jobs"]["drift"]["env"]["MAXIM_OVERDRIVE_UNLOCKED"] == "1"
    gate = yaml.safe_load((ROOT / ".github" / "workflows" / "test.yml").read_text())
    assert "MAXIM_OVERDRIVE_UNLOCKED" not in str(gate)


def test_the_gate_checks_the_lock_before_any_tool_runs() -> None:
    """Deleting the step from prepush.sh must turn something red (LK-S3)."""
    gate = (ROOT / "scripts" / "prepush.sh").read_text()
    assert '"$PY" scripts/check_lock.py' in gate
    assert gate.index('"$PY" scripts/check_lock.py') < gate.index('step "ruff lint"')


@pytest.mark.parametrize("lock", sorted((ROOT / "constraints").glob("py*.txt")), ids=lambda p: p.name)
def test_every_requirement_in_pyproject_is_locked(lock: Path) -> None:
    """A dependency added to pyproject without regenerating the lock fails here (LK-S2)."""
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    wanted = list(project["dependencies"]) + [r for extra in project["optional-dependencies"].values() for r in extra]
    names = {check.normalise(re.split(r"[\s<>=!~;\[]", r, maxsplit=1)[0]) for r in wanted}
    assert names - set(check.pins(lock.read_text())) == set()


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


def test_installed_names_lists_this_environment() -> None:
    names = {check.normalise(n) for n in check.installed_names()}
    assert {"pyyaml", "numpy", "pytest"} <= names
