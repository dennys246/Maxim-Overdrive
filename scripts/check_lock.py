"""Fail if the running environment doesn't match this Python's lockfile (owner decision O32).

The gate runs on locked dependencies so a release upstream can't turn it red with no local change, and so replay
goldens are recorded and checked on one numerical stack. A lock nobody installs from protects nothing: this check
compares every pinned package in ``constraints/py<major>.<minor>.txt`` with what is installed, and refuses a missing
lockfile, a missing package or a different version. The scheduled drift job (``.github/workflows/drift.yml``) runs
unpinned on purpose and sets ``MAXIM_OVERDRIVE_UNLOCKED=1``.

Run: ``python scripts/check_lock.py`` (exit 1 on any finding).
"""

from __future__ import annotations

import os
import re
import sys
from collections.abc import Callable
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s;#]+)")


def lockfile(root: Path, version: tuple[int, int]) -> Path:
    return root / "constraints" / f"py{version[0]}.{version[1]}.txt"


def pins(text: str) -> dict[str, str]:
    """``name==version`` lines, names normalised as packaging does (PEP 503)."""
    out = {}
    for line in text.splitlines():
        m = PIN.match(line.strip())
        if m:
            out[re.sub(r"[-_.]+", "-", m.group(1)).lower()] = m.group(2)
    return out


def findings(text: str, installed: Callable[[str], str]) -> list[str]:
    out = []
    for name, want in sorted(pins(text).items()):
        try:
            have = installed(name)
        except metadata.PackageNotFoundError:
            out.append(f"{name} is locked at {want} but not installed")
            continue
        if have != want:
            out.append(f"{name} is {have}, locked at {want}")
    return out


def main(root: Path = ROOT, version: tuple[int, int] | None = None) -> int:
    if os.environ.get("MAXIM_OVERDRIVE_UNLOCKED") == "1":
        print("check_lock: SKIPPED (MAXIM_OVERDRIVE_UNLOCKED=1, the drift job)")
        return 0
    version = version or (sys.version_info.major, sys.version_info.minor)
    lock = lockfile(root, version)
    if not lock.is_file():
        found = f"no lockfile for Python {version[0]}.{version[1]} ({lock.name})"
        print(f"check_lock: {found}; use a Python that constraints/ has a lockfile for", file=sys.stderr)
        return 1
    problems = findings(lock.read_text(), metadata.version)
    for p in problems:
        print(f"check_lock: {p}", file=sys.stderr)
    if problems:
        print(
            f"check_lock: FAIL; reinstall with: pip install -c constraints/{lock.name} -e '.[dev,maxim]'",
            file=sys.stderr,
        )
        return 1
    print(f"check_lock: PASS ({lock.name})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
