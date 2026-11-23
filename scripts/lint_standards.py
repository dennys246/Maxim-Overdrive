"""Mechanical checks for the engineering standards in CLAUDE.md, one module per check.

1. ``TEMPORARY(...)`` markers and ``pragma: no cover`` reasons: ``lint_markers.py``.
2. Guard citations: every standards rule names the check or backlog row that holds it: ``lint_guards.py``.
3. The coverage floor only ratchets: ``lint_coverage.py``.
4. Size tripwires and the size ratchet: ``lint_sizes.py``.
5. Untrusted input by source: input primitives only in input gates, unsafe decoders nowhere: ``lint_inputs.py``.
6. The gate registry: every entry point untrusted input can reach has a row: ``lint_gates.py``.
7. One owner per contract: no registered vocabulary or signature restated outside its owner, no fold or decision
   table inside a design: ``lint_contracts.py``.
8. No home directory in the tree, in any spelling: ``lint_paths.py``.
What they read from git comes from ``lint_repo.py``. This module runs them and says what the ratchets could not
compare.

Run: ``python scripts/lint_standards.py [--base REF]`` (exit 1 on any finding). scripts/prepush.sh runs it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lint_contracts import check_contracts
from lint_coverage import check_coverage_ratchet, fail_under
from lint_gates import check_gates
from lint_guards import check_guards
from lint_inputs import check_inputs
from lint_markers import check_markers
from lint_paths import check_paths
from lint_repo import base_pyproject, tracked_text_files
from lint_sizes import check_size_ratchet, check_sizes, size_limits

ROOT = Path(__file__).resolve().parents[1]


def ratchet_notes(base: str | None, base_text: str | None) -> list[str]:
    """What the ratchets could not compare, said aloud: a base with no pyproject.toml, no coverage floor or no size
    limits leaves that ratchet with nothing to hold, which must show rather than pass silently."""
    if base is None:
        return []
    if base_text is None:
        return [f"note: {base} has no pyproject.toml, so the coverage and size ratchets have nothing to compare yet"]
    notes = []
    if fail_under(base_text) is None:
        notes.append(f"note: {base} has no coverage floor, so the coverage ratchet has nothing to compare yet")
    if size_limits(base_text)[0] is None:
        notes.append(f"note: {base} has no valid size limits, so the size ratchet has nothing to compare yet")
    return notes


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", help="git ref whose coverage floor and size limits this branch may not loosen")
    args = parser.parse_args(argv)

    backlog_path = root / "docs/standards_backlog.md"
    backlog = backlog_path.read_text() if backlog_path.exists() else ""
    files = tracked_text_files(root)
    problems = check_markers(files, (root / "docs/roadmap.md").read_text())
    guard_problems, checked, review_only = check_guards((root / "CLAUDE.md").read_text(), backlog, root)
    problems += guard_problems
    problems += check_inputs(files)
    problems += check_paths(files)
    designs = any(rel.startswith("docs/design/") for rel in files)
    problems += check_contracts(files) if designs else []
    engine = any(rel.startswith("src/simcore/") for rel in files)
    problems += check_gates(files) if engine else []
    base_text, base_problems = base_pyproject(root, args.base)
    problems += base_problems
    pyproject = (root / "pyproject.toml").read_text()
    problems += check_coverage_ratchet(pyproject, base_text)
    limits, limit_problems = size_limits(pyproject)
    problems += limit_problems
    if limits is not None:
        problems += check_sizes(files, limits)
        problems += check_size_ratchet(limits, base_text)
    for p in problems:
        print(p, file=sys.stderr)
    for n in [] if base_problems else ratchet_notes(args.base, base_text):  # a bad ref is already a finding
        print(f"lint_standards: {n}")
    if not engine:
        print("lint_standards: note: no engine under src/simcore/, so the gate registry has nothing to hold")
    if not designs:
        print("lint_standards: note: no docs/design/, so the contracts check has nothing to hold")
    verdict = "FAIL" if problems else "PASS"
    print(
        f"lint_standards: {verdict} ({len(problems)} finding(s)); rules enforced by a check: {checked}, "
        f"held only by review (backlog): {review_only}"
    )
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
