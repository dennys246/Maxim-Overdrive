"""Mechanical checks for the engineering standards in CLAUDE.md.

1. ``TEMPORARY(...)`` markers, the one allowed exemption to the no-band-aid rule. Each must give a reason and cite a
   roadmap phase that exists, is not done, and lists the marker's file in its section of docs/roadmap.md. So a
   band-aid can't outlive the moment promised to remove it, and the roadmap shows every one that is open.
2. ``pragma: no cover`` must say why the line can't be tested.
3. Guard citations. Every rule bullet under CLAUDE.md's "Engineering standards" ends with ``Guard:`` and names files
   that exist (``path``, or ``path::symbol`` where the symbol appears as a whole word outside comments, and, in a
   ``.py`` file, as a definition) and/or backlog rows (``B7``) in docs/standards_backlog.md. A rule whose only
   guards are documents must also cite a backlog row: a document is not a check. The summary line counts the rules
   a check enforces and the rules held only by review, so neither number hides.
4. The coverage floor only ratchets: ``fail_under`` may not drop below the base branch's.

Run: ``python scripts/lint_standards.py [--base REF]`` (exit 1 on any finding). scripts/prepush.sh runs it.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

import tomli  # the stdlib's tomllib, from PyPI on every version: one code path, including Python 3.10

ROOT = Path(__file__).resolve().parents[1]

TEMP_MARKER = re.compile(r"\bTEMPORARY\s*\(([^)]*)\)", re.IGNORECASE)
TEMP_TARGET = re.compile(r"^phase(\d+)(?:/[a-z0-9][a-z0-9_-]*)?$")
PRAGMA = re.compile(r"pragma:\s*no\s*cover", re.IGNORECASE)
PRAGMA_REASON = re.compile(r"pragma:\s*no\s*cover\s*(?:-+|:)\s*\S.{8,}", re.IGNORECASE)
PHASE_HEADING = re.compile(r"^## Phase (\d+):.*\((\w+)[^)]*\)\s*$")
STANDARDS_HEADING = "## Engineering standards"
GUARD = re.compile(r"Guard:\s*(.+)$")
PATH_REF = re.compile(r"`([^`]+)`")
BACKLOG_REF = re.compile(r"\bB(\d+)\b")
BACKLOG_ROW = re.compile(r"^\|\s*B(\d+)\s*\|")
COMMENT_PREFIX = {".py": "#", ".toml": "#", ".sh": "#", ".yml": "#", ".yaml": "#", ".gitignore": "#", ".gd": "#"}

# Files that discuss markers and pragmas without being band-aids or exclusions.
MARKER_EXEMPT = {"scripts/lint_standards.py", "tests/test_lint_standards.py", "CLAUDE.md", "docs/code_review.md"}


def phase_sections(roadmap: str) -> dict[int, tuple[str, str]]:
    """Phase number -> (status word, section text) from the roadmap's ``## Phase N: ... (status)`` headings."""
    out: dict[int, tuple[str, str]] = {}
    current: int | None = None
    for line in roadmap.splitlines():
        m = PHASE_HEADING.match(line)
        if m:
            current = int(m.group(1))
            out[current] = (m.group(2).lower(), "")
        elif line.startswith("## "):
            current = None
        elif current is not None:
            status, text = out[current]
            out[current] = (status, text + line + "\n")
    return out


def check_markers(files: dict[str, str], roadmap: str) -> list[str]:
    sections = phase_sections(roadmap)
    problems = []
    for rel, text in sorted(files.items()):
        if rel in MARKER_EXEMPT:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            where = f"{rel}:{lineno}"
            if PRAGMA.search(line) and not PRAGMA_REASON.search(line):
                problems.append(f"{where}: 'pragma: no cover' needs a reason: '# pragma: no cover - <why>'")
            for m in TEMP_MARKER.finditer(line):
                target = m.group(1).strip()
                rest = line[m.end() :]
                if not rest.lstrip().startswith(":") or len(rest.strip(" :")) < 10:
                    problems.append(f"{where}: TEMPORARY({target}) needs ': <why, and what the real fix is>'")
                t = TEMP_TARGET.match(target)
                if not t:
                    problems.append(f"{where}: TEMPORARY({target}) must cite a roadmap phase, e.g. TEMPORARY(phase2)")
                    continue
                n = int(t.group(1))
                if n not in sections:
                    problems.append(f"{where}: TEMPORARY({target}) cites phase {n}, which docs/roadmap.md lacks")
                    continue
                status, body = sections[n]
                if status == "done":
                    problems.append(f"{where}: TEMPORARY({target}): phase {n} is done, so this was due to be removed")
                if rel not in body:
                    problems.append(f"{where}: TEMPORARY({target}): list {rel} under Phase {n} in docs/roadmap.md")
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


def _code_text(path: Path) -> str:
    """The file without comment lines or trailing comments, so a guard can't be satisfied by a remark about it."""
    prefix = COMMENT_PREFIX.get(path.suffix or path.name)
    lines = path.read_text().splitlines()
    if prefix is None:
        return "\n".join(lines)
    return "\n".join(re.split(rf"(?:^|\s){re.escape(prefix)}", ln, maxsplit=1)[0] for ln in lines)


def symbol_present(path: Path, symbol: str) -> bool:
    name = symbol.rsplit(".", maxsplit=1)[-1]
    text = _code_text(path)
    word = rf"(?<![\w-]){re.escape(name)}(?![\w-])"
    if path.suffix == ".py":
        return (
            re.search(rf"^\s*(?:def|class|async\s+def)\s+{re.escape(name)}\b|^\s*{re.escape(name)}\s*[:=]", text, re.M)
            is not None
        )
    return re.search(word, text) is not None


def _path_problem(root: Path, ref: str) -> str | None:
    path, _, symbol = ref.partition("::")
    target = root / path
    if not target.exists():
        return f"guard {path} does not exist"
    if symbol and not target.is_file():
        return f"guard {path} is a directory, so ::{symbol} can't be checked"
    if symbol and not symbol_present(target, symbol):
        return f"guard {path} has no {symbol} outside comments"
    return None


def check_guards(claude_md: str, backlog: str, root: Path) -> tuple[list[str], int, int]:
    """Findings, plus how many rules a check enforces and how many only review holds."""
    rows = {int(m.group(1)) for ln in backlog.splitlines() if (m := BACKLOG_ROW.match(ln))}
    bullets = standards_bullets(claude_md)
    if not bullets:
        return [f"CLAUDE.md: no '{STANDARDS_HEADING}' section with rule bullets"], 0, 0
    problems: list[str] = []
    checked = review_only = 0
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
            continue
        problems += [f"{where}: {p}" for ref in paths if (p := _path_problem(root, ref))]
        for b in refs:
            if b not in rows:
                problems.append(f"{where}: backlog row B{b} is not in docs/standards_backlog.md")
        checks = [p for p in paths if not p.partition("::")[0].startswith("docs/")]
        if checks:
            checked += 1
        else:
            review_only += 1
            if not refs:
                problems.append(f"{where}: only documents guard this rule; cite the backlog row that will check it")
    return problems, checked, review_only


def fail_under(pyproject: str) -> float | None:
    value = tomli.loads(pyproject).get("tool", {}).get("coverage", {}).get("report", {}).get("fail_under")
    return None if value is None else float(value)


def check_coverage_ratchet(current: str, base: str | None) -> list[str]:
    now = fail_under(current)
    if now is None:
        return ["pyproject.toml: [tool.coverage.report] fail_under is missing"]
    before = fail_under(base) if base is not None else None
    if before is not None and now < before:
        return [f"pyproject.toml: coverage fail_under fell from {before:g} to {now:g}; the floor only ratchets up"]
    return []


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


def base_pyproject(root: Path, base: str | None) -> str | None:
    if base is None:
        return None
    cmd = ["git", "show", f"{base}:pyproject.toml"]
    out = subprocess.run(cmd, cwd=root, capture_output=True, text=True, check=False)
    return out.stdout if out.returncode == 0 else None  # no pyproject at the base: nothing to ratchet against


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", help="git ref whose coverage floor this branch may not go below")
    args = parser.parse_args(argv)

    backlog_path = root / "docs/standards_backlog.md"
    backlog = backlog_path.read_text() if backlog_path.exists() else ""
    problems = check_markers(tracked_text_files(root), (root / "docs/roadmap.md").read_text())
    guard_problems, checked, review_only = check_guards((root / "CLAUDE.md").read_text(), backlog, root)
    problems += guard_problems
    problems += check_coverage_ratchet((root / "pyproject.toml").read_text(), base_pyproject(root, args.base))
    for p in problems:
        print(p, file=sys.stderr)
    verdict = "FAIL" if problems else "PASS"
    print(
        f"lint_standards: {verdict} ({len(problems)} finding(s)); rules enforced by a check: {checked}, "
        f"held only by review (backlog): {review_only}"
    )
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
