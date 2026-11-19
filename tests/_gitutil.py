"""The one way tests run git: in an environment that can only touch the repository a test names.

A session's environment can point git somewhere else: a hook or `git rebase -x` exports ``GIT_DIR``,
``GIT_WORK_TREE`` and ``GIT_INDEX_FILE``, and the user's global config can add hooks or signing. A test that inherits
them commits into another session's repository instead of its own temp one. So every test's git call drops every
``GIT_*`` variable, ignores global and system config, and supplies its own identity. tests/test_isolation.py fails on
any test that runs git another way.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

IDENTITY = ("-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false")


def isolated_env(**extra: str) -> dict[str, str]:
    """The current environment without any ``GIT_*`` variable, and with no global or system git config."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env |= {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", **extra}
    return env


def git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run git in ``cwd`` only. Commits are unsigned on purpose: these repositories never leave the test."""
    return subprocess.run(
        ["git", *IDENTITY, *args], cwd=cwd, env=isolated_env(), capture_output=True, text=True, check=check
    )
