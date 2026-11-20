"""What the standards lint reads from git: the tracked text files, and the base branch's pyproject.toml."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _git_env() -> dict[str, str]:
    """The gate's own environment, on purpose: these git calls read the repository the gate is run in."""
    return dict(os.environ)


def tracked_text_files(root: Path) -> dict[str, str]:
    cmd = ["git", "ls-files", "-co", "--exclude-standard"]
    out = subprocess.run(cmd, cwd=root, env=_git_env(), capture_output=True, text=True, check=True)
    files = {}
    for rel in out.stdout.splitlines():
        p = root / rel
        if p.is_file():
            try:
                files[rel] = p.read_text(encoding="utf-8")
            except UnicodeDecodeError:  # binary file: no markers to find
                continue
    return files


def base_pyproject(root: Path, base: str | None) -> tuple[str | None, list[str]]:
    """The base's pyproject.toml, or None when there is no base or the base has no pyproject. An unknown ref is a
    finding, not a skip: a typo must not quietly switch the ratchet off."""
    if base is None:
        return None, []
    verify = ["git", "rev-parse", "--verify", "-q", f"{base}^{{commit}}"]
    known = subprocess.run(verify, cwd=root, env=_git_env(), capture_output=True, check=False)
    if known.returncode != 0:
        return None, [f"--base {base} is not a commit in this repository, so the coverage and size ratchets can't run"]
    show = ["git", "show", f"{base}:pyproject.toml"]
    out = subprocess.run(show, cwd=root, env=_git_env(), capture_output=True, text=True, check=False)
    return (out.stdout if out.returncode == 0 else None), []
