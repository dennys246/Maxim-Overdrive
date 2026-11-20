"""The gate's Godot checks (B6; client_rendering.md §7.3, CR-B1): the client imports, every script loads, tests pass.

Godot's exit status is not a test result. Godot 4.7.2 exits 0 after a parse error, keeps running after a runtime error
in a script started with ``-s``, and ``load()`` returns a non-null script that cannot be instantiated when the
script fails to compile (measured; docs/design/research/godot_probes.md). So each call runs under an outer timeout,
and the check reads what Godot printed:

1. ``godot --version`` must be the pinned build (``ci/godot.env``).
2. A copy of the project, as a fresh checkout would have it, is imported (``--headless --import``), so ``class_name``
   resolves. The import must not create or change any file outside ``.godot/``: a script's ``.uid`` file is
   committed with it, and a project the editor would rewrite is not the project under review.
3. ``res://tests/load_all.gd`` loads every ``.gd`` file; each one that is null or cannot be instantiated is named.
4. ``res://tests/run.gd`` runs the client tests, and its last line must be ``client-tests: PASS <n> tests``.

Every step fails on a ``SCRIPT ERROR``, ``Parse Error`` or ``ERROR:`` line and on a timeout. Godot runs with ``HOME``
and the XDG directories inside the work directory, because it writes editor settings, caches and logs there.

Run: ``python scripts/godot_check.py [--project client] [--timeout 120]`` (exit 1 on any finding). Godot is ``$GODOT``,
else the macOS app, else ``godot`` on ``PATH``.
"""

from __future__ import annotations

import argparse
import filecmp
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PINS = ROOT / "ci" / "godot.env"
MACOS_APP = Path("/Applications/Godot.app/Contents/MacOS/Godot")
TIMEOUT_S = 120.0

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
ERROR_LINE = re.compile(r"SCRIPT ERROR|Parse Error|ERROR:")
SENTINEL = re.compile(r"^client-tests: PASS (\d+) tests$")
UNLOADABLE = "godot-check: unloadable "
LOADED = re.compile(r"^godot-check: loaded (\d+) scripts$")
IMPORT_CACHE = ".godot"


@dataclass(frozen=True)
class Run:
    """What one Godot call printed (stdout and stderr, interleaved, colour codes removed) and how it ended."""

    step: str
    lines: tuple[str, ...]
    returncode: int | None  # None: killed at the timeout
    timeout_s: float


def pinned_version(pins: str) -> str:
    found = re.search(r"^GODOT_VERSION=(\S+)$", pins, re.MULTILINE)
    if found is None:
        raise ValueError("ci/godot.env has no GODOT_VERSION line")
    return found.group(1)


def find_godot(env: Mapping[str, str], platform: str, which: Callable[[str], str | None] = shutil.which) -> str | None:
    if env.get("GODOT"):
        return env["GODOT"]
    if platform == "darwin" and MACOS_APP.is_file():
        return str(MACOS_APP)
    return which("godot")


def godot_env(home: Path) -> dict[str, str]:
    """This environment with Godot's per-user directories moved into ``home`` (macOS reads HOME; Linux, XDG first)."""
    xdg = {"XDG_DATA_HOME": ".local/share", "XDG_CONFIG_HOME": ".config", "XDG_CACHE_HOME": ".cache"}
    return {**os.environ, "HOME": str(home), **{k: str(home / v) for k, v in xdg.items()}}


def run_godot(godot: str, step: str, args: Sequence[str], *, home: Path, timeout_s: float) -> Run:
    home.mkdir(parents=True, exist_ok=True)
    cmd = [godot, *args]
    try:
        done = subprocess.run(
            cmd, env=godot_env(home), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout_s, check=False
        )
        out, code = done.stdout, done.returncode
    except subprocess.TimeoutExpired as e:
        out, code = e.output or b"", None
    lines = tuple(ANSI.sub("", line) for line in out.decode("utf-8", "replace").splitlines())
    return Run(step, lines, code, timeout_s)


def error_findings(run: Run) -> list[str]:
    found = [f"{run.step}: Godot printed an error: {line.strip()}" for line in run.lines if ERROR_LINE.search(line)]
    if run.returncode is None:
        found.append(f"{run.step}: timed out after {run.timeout_s:g} s (Godot keeps running after a script error)")
    return found


def sentinel_findings(run: Run) -> list[str]:
    last = next((line for line in reversed(run.lines) if line.strip()), "")
    passed = SENTINEL.match(last)
    if passed is None or int(passed.group(1)) == 0:
        return [f"{run.step}: the last line is {last!r}, not 'client-tests: PASS <n> tests'"]
    if run.returncode != 0:
        return [f"{run.step}: printed PASS but exited {run.returncode}"]
    return []


def load_findings(run: Run, expected: int) -> list[str]:
    bad = [line.removeprefix(UNLOADABLE) for line in run.lines if line.startswith(UNLOADABLE)]
    found = [f"{run.step}: {path} is null or cannot be instantiated" for path in bad]
    counts = [int(m.group(1)) for line in run.lines if (m := LOADED.match(line))]
    if counts != [expected]:
        found.append(f"{run.step}: expected 'godot-check: loaded {expected} scripts', got {counts or 'nothing'}")
    return found


def scripts_in(project: Path) -> list[str]:
    paths = (p for p in project.rglob("*.gd") if IMPORT_CACHE not in p.relative_to(project).parts)
    return sorted("res://" + p.relative_to(project).as_posix() for p in paths)


def copy_project(source: Path, dest: Path) -> Path:
    """The project as a fresh checkout has it: without the import cache."""
    shutil.copytree(source, dest, ignore=shutil.ignore_patterns(IMPORT_CACHE))
    return dest


def import_changes(source: Path, imported: Path) -> list[str]:
    """Files the import created or changed outside the import cache, relative to the project."""
    out = []
    for p in sorted(imported.rglob("*")):
        rel = p.relative_to(imported)
        if p.is_dir() or rel.parts[0] == IMPORT_CACHE:
            continue
        if not (source / rel).is_file():
            out.append(f"import: created {rel.as_posix()}; commit it (run the import in client/ once)")
        elif not filecmp.cmp(source / rel, p, shallow=False):
            out.append(f"import: rewrote {rel.as_posix()}; commit the editor's form of it")
    return out


def version_findings(godot: str, *, pins: str, home: Path, timeout_s: float) -> list[str]:
    run = run_godot(godot, "version", ["--headless", "--version"], home=home, timeout_s=timeout_s)
    want = pinned_version(pins)
    got = run.lines[-1].strip() if run.lines else ""
    return error_findings(run) + ([] if got == want else [f"version: Godot is {got!r}, the pin is {want}"])


def import_step(godot: str, source: Path, project: Path, *, home: Path, timeout_s: float) -> list[str]:
    run = run_godot(godot, "import", ["--headless", "--import", "--path", str(project)], home=home, timeout_s=timeout_s)
    return error_findings(run) + import_changes(source, project)


def load_step(godot: str, project: Path, *, home: Path, timeout_s: float) -> list[str]:
    paths = scripts_in(project)
    args = ["--headless", "--path", str(project), "-s", "res://tests/load_all.gd", "--", *paths]
    run = run_godot(godot, "load", args, home=home, timeout_s=timeout_s)
    return error_findings(run) + load_findings(run, len(paths))


def client_tests_step(godot: str, project: Path, *, home: Path, timeout_s: float) -> list[str]:
    args = ["--headless", "--path", str(project), "-s", "res://tests/run.gd"]
    run = run_godot(godot, "tests", args, home=home, timeout_s=timeout_s)
    return error_findings(run) + sentinel_findings(run)


def check(source: Path, *, godot: str, work: Path, pins: str, timeout_s: float = TIMEOUT_S) -> list[str]:
    """Every finding for the project at ``source``; ``work`` is an empty directory the check may fill."""
    home, project = work / "home", copy_project(source, work / "project")
    found = version_findings(godot, pins=pins, home=home, timeout_s=timeout_s)
    found += import_step(godot, source, project, home=home, timeout_s=timeout_s)
    found += load_step(godot, project, home=home, timeout_s=timeout_s)
    return found + client_tests_step(godot, project, home=home, timeout_s=timeout_s)


def main(argv: list[str] | None = None, *, work_parent: Path = ROOT / "build") -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--project", type=Path, default=ROOT / "client")
    parser.add_argument("--timeout", type=float, default=TIMEOUT_S, help="seconds per Godot call")
    args = parser.parse_args(argv)
    godot = find_godot(os.environ, sys.platform)
    if godot is None:
        print("godot_check: FAIL: no Godot; install 4.7.2 (ci/install_godot.sh) or set GODOT", file=sys.stderr)
        return 1
    work_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="godot-check-", dir=work_parent) as work:
        found = check(args.project, godot=godot, work=Path(work), pins=PINS.read_text(), timeout_s=args.timeout)
    for f in found:
        print(f"godot_check: {f}", file=sys.stderr)
    print(f"godot_check: {'FAIL' if found else 'PASS'} ({godot})")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
