"""Mechanical checks for the engineering standards in CLAUDE.md.

1. ``TEMPORARY(...)`` markers, the one allowed exemption to the no-band-aid rule. Each must cite the roadmap phase
   that removes it (``TEMPORARY(phase2): ...`` or ``TEMPORARY(phase1/scene): ...``). The phase must exist in
   docs/roadmap.md and must not be done, so a band-aid can't outlive the moment that was promised to remove it.
2. Guard citations. Every rule bullet under CLAUDE.md's "Engineering standards" ends with ``Guard:`` and names either
   files that exist (``path`` or ``path::symbol``, with the symbol present in the file) or backlog rows (``B7``)
   that exist in docs/standards_backlog.md. A rule with no check is visible, not silent.

Run: ``python scripts/lint_standards.py`` (exit 1 on any finding). scripts/prepush.sh runs it.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TEMP_MARKER = re.compile(r"TEMPORARY\(([^)]*)\)")
TEMP_TARGET = re.compile(r"^phase(\d+)(?:/[a-z0-9][a-z0-9_-]*)?$")
PHASE_HEADING = re.compile(r"^## Phase (\d+):.*\((\w+)[^)]*\)\s*$")
STANDARDS_HEADING = "## Engineering standards"
GUARD = re.compile(r"Guard:\s*(.+)$")
PATH_REF = re.compile(r"`([^`]+)`")
BACKLOG_REF = re.compile(r"\bB(\d+)\b")
BACKLOG_ROW = re.compile(r"^\|\s*B(\d+)\s*\|")

# Files the marker check skips: this lint and its tests talk about markers without being band-aids.
MARKER_EXEMPT = {"scripts/lint_standards.py", "tests/test_lint_standards.py", "CLAUDE.md", "docs/code_review.md"}


def phases(roadmap: str) -> dict[int, str]:
    """Phase number -> status word ("done", "next", "later") from the roadmap's headings."""
    out: dict[int, str] = {}
    for line in roadmap.splitlines():
        m = PHASE_HEADING.match(line)
        if m:
            out[int(m.group(1))] = m.group(2).lower()
    return out


def check_temporary_markers(files: dict[str, str], roadmap: str) -> list[str]:
    known = phases(roadmap)
    problems = []
    for rel, text in sorted(files.items()):
        if rel in MARKER_EXEMPT:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for m in TEMP_MARKER.finditer(line):
                target = m.group(1).strip()
                where = f"{rel}:{lineno}"
                t = TEMP_TARGET.match(target)
                if not t:
                    problems.append(f"{where}: TEMPORARY({target}) must cite a roadmap phase, e.g. TEMPORARY(phase2)")
                    continue
                n = int(t.group(1))
                if n not in known:
                    problems.append(f"{where}: TEMPORARY({target}) cites phase {n}, which docs/roadmap.md lacks")
                elif known[n] == "done":
                    problems.append(f"{where}: TEMPORARY({target}): phase {n} is done, so this was due to be removed")
                if not line[m.end() :].lstrip().startswith(":") or len(line[m.end() :].strip(" :")) < 10:
                    problems.append(f"{where}: TEMPORARY({target}) needs ': <why, and what the real fix is>'")
    return problems


def standards_bullets(claude_md: str) -> list[tuple[int, str]]:
    """Top-level bullets in the Engineering standards section, joined across continuation lines."""
    lines = claude_md.splitlines()
    try:
        start = next(i for i, ln in enumerate(lines) if ln.strip() == STANDARDS_HEADING)
    except StopIteration:
        return []
    bullets: list[tuple[int, str]] = []
    for i in range(start + 1, len(lines)):
        ln = lines[i]
        if ln.startswith("## "):
            break
        if ln.startswith("- "):
            bullets.append((i + 1, ln))
        elif bullets and ln.startswith("  ") and ln.strip():
            bullets[-1] = (bullets[-1][0], bullets[-1][1] + " " + ln.strip())
    return bullets


def check_guards(claude_md: str, backlog: str, root: Path) -> list[str]:
    rows = {int(m.group(1)) for ln in backlog.splitlines() if (m := BACKLOG_ROW.match(ln))}
    bullets = standards_bullets(claude_md)
    if not bullets:
        return [f"CLAUDE.md: no '{STANDARDS_HEADING}' section with rule bullets"]
    problems = []
    for lineno, text in bullets:
        where = f"CLAUDE.md:{lineno}"
        g = GUARD.search(text)
        if not g:
            problems.append(f"{where}: rule has no 'Guard:' (cite a test, script or backlog row)")
            continue
        cited = g.group(1)
        paths = PATH_REF.findall(cited)
        refs = [int(b) for b in BACKLOG_REF.findall(PATH_REF.sub("", cited))]
        if not paths and not refs:
            problems.append(f"{where}: 'Guard:' names neither a `path` nor a backlog row")
        for ref in paths:
            path, _, symbol = ref.partition("::")
            target = root / path
            if not target.exists():
                problems.append(f"{where}: guard {path} does not exist")
            elif symbol and target.is_file() and symbol.split(".")[-1] not in target.read_text():
                problems.append(f"{where}: guard {path} has no symbol {symbol}")
        for b in refs:
            if b not in rows:
                problems.append(f"{where}: backlog row B{b} is not in docs/standards_backlog.md")
    return problems


def tracked_text_files(root: Path) -> dict[str, str]:
    cmd = ["git", "ls-files", "-co", "--exclude-standard"]
    out = subprocess.run(cmd, cwd=root, capture_output=True, text=True, check=True)
    files = {}
    for rel in out.stdout.splitlines():
        p = root / rel
        if p.is_file():
            try:
                files[rel] = p.read_text(encoding="utf-8")
            except UnicodeDecodeError:  # binary file: no markers to find
                continue
    return files


def main(root: Path = ROOT) -> int:
    roadmap = (root / "docs/roadmap.md").read_text()
    backlog_path = root / "docs/standards_backlog.md"
    backlog = backlog_path.read_text() if backlog_path.exists() else ""
    problems = check_temporary_markers(tracked_text_files(root), roadmap)
    problems += check_guards((root / "CLAUDE.md").read_text(), backlog, root)
    for p in problems:
        print(p, file=sys.stderr)
    print(f"lint_standards: {'FAIL' if problems else 'PASS'} ({len(problems)} finding(s))")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
