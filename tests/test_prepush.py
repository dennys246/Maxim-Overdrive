"""scripts/prepush.sh refuses to run on main or from the main checkout, because other agents may be at work.

Each test copies the gate into a fresh repository and runs it there, through tests/_gitutil.py, so neither the gate
nor the fixture can reach any other repository. The refusal comes before every other precondition, so a run that gets
past it fails later on the missing Python instead, which is how a pass is recognised here.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from tests._gitutil import git, isolated_env

ROOT = Path(__file__).resolve().parents[1]
PAST_THE_REFUSAL = "no Python at"


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A repository with the gate committed on main, and a linked worktree on a phase branch."""
    main = tmp_path / "repo"
    (main / "scripts").mkdir(parents=True)
    shutil.copy(ROOT / "scripts" / "prepush.sh", main / "scripts" / "prepush.sh")
    git(main, "init", "-q", "-b", "main")
    git(main, "add", "-A")
    git(main, "commit", "-q", "-m", "x")
    git(main, "worktree", "add", "-q", str(main / ".worktrees" / "step"), "-b", "phase1/step")
    return main


def _gate(cwd: Path, python: str | None = None, **env: str) -> subprocess.CompletedProcess[str]:
    clean = {k: v for k, v in isolated_env().items() if k not in {"CI", "GITHUB_ACTIONS", "PYTHON", "BASE"}}
    clean |= {"PYTHON": python or str(cwd / "no-such-python"), **env}
    cmd = ["bash", "scripts/prepush.sh"]
    return subprocess.run(cmd, cwd=cwd, env=clean, capture_output=True, text=True, check=False)


def test_the_gate_refuses_main(repo: Path) -> None:
    out = _gate(repo)
    assert out.returncode == 1
    assert "HEAD is on main" in out.stderr


def test_the_gate_refuses_another_branch_in_the_main_checkout(repo: Path) -> None:
    git(repo, "checkout", "-q", "-b", "phase1/other")
    out = _gate(repo)
    assert out.returncode == 1
    assert "this is the main checkout" in out.stderr


def test_the_gate_runs_in_a_worktree_on_a_phase_branch(repo: Path) -> None:
    out = _gate(repo / ".worktrees" / "step")
    assert PAST_THE_REFUSAL in out.stderr
    assert "main checkout" not in out.stderr


def test_github_actions_is_exempt_because_its_clone_is_fresh(repo: Path) -> None:
    assert PAST_THE_REFUSAL in _gate(repo, GITHUB_ACTIONS="true").stderr


@pytest.mark.parametrize("ci", ["true", "1", "false"])
def test_a_ci_variable_alone_is_not_an_exemption(repo: Path, ci: str) -> None:
    assert "HEAD is on main" in _gate(repo, CI=ci).stderr


def test_a_shared_venv_is_never_offered_an_install(repo: Path, tmp_path: Path) -> None:
    """A venv outside the worktree is shared: installing into it would re-point every session's editable install."""
    shared = tmp_path / "shared-venv" / "bin" / "python"
    shared.parent.mkdir(parents=True)
    shared.symlink_to(shutil.which("false") or "/usr/bin/false")
    out = _gate(repo / ".worktrees" / "step", python=str(shared))
    assert "don't install into it" in out.stderr
    assert "pip install -e" not in out.stderr.split("make this worktree its own venv")[0]


def test_the_tests_cannot_reach_a_repository_named_in_the_environment(tmp_path: Path, monkeypatch) -> None:
    """A hook or `git rebase -x` exports GIT_DIR; the fixture's commits must still land only in its own repo."""
    victim = tmp_path / "victim"
    victim.mkdir()
    git(victim, "init", "-q", "-b", "main")
    (victim / "wip.txt").write_text("another session's work in progress\n")
    monkeypatch.setenv("GIT_DIR", str(victim / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(victim))
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    git(elsewhere, "init", "-q", "-b", "main")
    (elsewhere / "f").write_text("x\n")
    git(elsewhere, "add", "-A")
    git(elsewhere, "commit", "-q", "-m", "x")
    monkeypatch.delenv("GIT_DIR")
    monkeypatch.delenv("GIT_WORK_TREE")
    assert git(victim, "rev-parse", "--verify", "-q", "HEAD", check=False).returncode != 0  # still no commits
    assert git(victim, "status", "--porcelain").stdout == "?? wip.txt\n"
