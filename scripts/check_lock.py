"""Fail if the running environment doesn't match this Python's lockfile (owner decision O32).

The gate runs on locked dependencies so a release upstream can't turn it red with no local change, and so replay
goldens are recorded and checked on one numerical stack. A lock nobody installs from protects nothing: this check
compares ``constraints/py<major>.<minor>.txt`` with what is installed, both ways. It refuses a missing or empty
lockfile, a locked package that is missing or at another version, and an installed package the lock doesn't name
(a stale or hand-installed one would still be imported, or loaded as a pytest plugin).

Only the scheduled drift job (``.github/workflows/drift.yml``) runs unpinned. It sets ``MAXIM_OVERDRIVE_UNLOCKED=1``,
which is honoured only on GitHub Actions for a ``schedule`` or ``workflow_dispatch`` run; anywhere else it is refused.
``--report`` prints the differences and exits 0, so a red drift run says what moved.

Run: ``python scripts/check_lock.py [--report]`` (exit 1 on any finding).
"""

from __future__ import annotations

import os
import re
import sys
from collections.abc import Callable, Iterable, Mapping
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s;#]+)")
NOT_LOCKED = {"pip", "maxim-overdrive"}  # the installer, and the project itself (installed editable from the tree)
SKIP_EVENTS = {"schedule", "workflow_dispatch"}


def normalise(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()  # PEP 503


def lockfile(root: Path, version: tuple[int, int]) -> Path:
    return root / "constraints" / f"py{version[0]}.{version[1]}.txt"


def pins(text: str) -> dict[str, str]:
    """``name==version`` lines; comments, ``# via`` notes and blank lines are skipped."""
    return {normalise(m.group(1)): m.group(2) for line in text.splitlines() if (m := PIN.match(line.strip()))}


def findings(text: str, installed: Callable[[str], str], present: Iterable[str]) -> list[str]:
    """Differences between the lock and the environment: missing or other-version pins, and unlocked extras."""
    locked = pins(text)
    if not locked:
        return ["the lockfile pins nothing"]
    out = []
    for name, want in sorted(locked.items()):
        try:
            have = installed(name)
        except metadata.PackageNotFoundError:
            out.append(f"{name} is locked at {want} but not installed")
            continue
        if have != want:
            out.append(f"{name} is {have}, locked at {want}")
    extras = sorted({normalise(n) for n in present} - set(locked) - NOT_LOCKED)
    return out + [f"{name} is installed but not in the lock" for name in extras]


def skip_refusal(env: Mapping[str, str]) -> str | None:
    """None when the lock check may be skipped here; otherwise why the skip is refused."""
    if env.get("GITHUB_ACTIONS") == "true" and env.get("GITHUB_EVENT_NAME") in SKIP_EVENTS:
        return None
    return "MAXIM_OVERDRIVE_UNLOCKED=1 is only for the scheduled drift job on GitHub Actions"


def installed_names() -> list[str]:
    return [d.metadata["Name"] for d in metadata.distributions()]


def main(
    root: Path = ROOT,
    version: tuple[int, int] | None = None,
    argv: list[str] | None = None,
    *,
    env: Mapping[str, str],
) -> int:
    """The check; ``env`` is the environment it decides the skip from, passed and never read from the process.

    Only ``entry``, the command line, passes ``os.environ``. A caller that reads the process environment inherits
    whatever its runner set: the drift job sets ``MAXIM_OVERDRIVE_UNLOCKED`` for the whole gate, and the tests of this
    check that expected a refusal saw a skip instead (run 45238153656). Required and keyword-only, so forgetting it is
    a ``TypeError``, not a silent inheritance.
    """
    report = "--report" in (sys.argv[1:] if argv is None else argv)
    if env.get("MAXIM_OVERDRIVE_UNLOCKED") == "1" and not report:
        refusal = skip_refusal(env)
        print(f"check_lock: {refusal or 'SKIPPED (the drift job)'}", file=sys.stderr if refusal else sys.stdout)
        return 1 if refusal else 0
    version = version or (sys.version_info.major, sys.version_info.minor)
    lock = lockfile(root, version)
    if not lock.is_file():
        found = f"no lockfile for Python {version[0]}.{version[1]} ({lock.name})"
        print(f"check_lock: {found}; use a Python that constraints/ has a lockfile for", file=sys.stderr)
        return 0 if report else 1
    problems = findings(lock.read_text(), metadata.version, installed_names())
    for p in problems:
        print(f"check_lock: {p}", file=sys.stderr)
    if problems and not report:
        fix = f"pip install -c constraints/{lock.name} -e '.[dev,maxim]'"
        print(
            f"check_lock: FAIL; in this worktree's own venv only: pip uninstall what the lock doesn't name, then {fix}",
            file=sys.stderr,
        )
        return 1
    print(f"check_lock: {'REPORT' if report else 'PASS'} ({lock.name}, {len(problems)} difference(s))")
    return 0


def entry() -> int:
    """The command line: the one caller that hands ``main`` the process environment, where the drift job's skip is."""
    return main(env=os.environ)


if __name__ == "__main__":
    sys.exit(entry())
