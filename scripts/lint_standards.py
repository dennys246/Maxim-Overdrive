"""Mechanical checks for the engineering standards in CLAUDE.md.

1. ``TEMPORARY(...)`` markers, the one allowed exemption to the no-band-aid rule. Each must give a reason and cite a
   roadmap phase that exists, is not done, and lists the marker's file in its section of docs/roadmap.md. So a
   band-aid can't outlive the moment promised to remove it, and the roadmap shows every one that is open.
2. ``pragma: no cover`` must say why the line can't be tested.
   Markdown holds no band-aids, so it holds no markers or pragmas. A document that explains or reviews the rule
   quotes their syntax in code (an inline span or a code block), and anything that renders as text is a finding.
   Documents are parsed by markdown-it as CommonMark plus GitHub's tables, the way they render, rather than by a
   hand-written approximation; raw HTML counts as text, and a fence left open at the end of a file is a finding.
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
from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[1]

# Upper case always counts; any other case counts when it cites a phase, so "a temporary (two-turn) fire" in prose is
# not a marker but "temporary (phase2): ..." is.
TEMP_MARKER = re.compile(r"\b(?:TEMPORARY|(?i:temporary)(?=\s*\(\s*phase))\s*\(([^)]*)\)")
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

# The lint and its tests write markers and pragmas as data. Documents need no entry: they quote them in code.
MARKER_EXEMPT = {"scripts/lint_standards.py", "tests/test_lint_standards.py"}
# How GitHub renders the docs: CommonMark plus tables (cells are parsed one by one, so a span can't cross rows).
MARKDOWN = MarkdownIt("commonmark").enable(["table", "strikethrough"])


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


def markdown_prose(text: str) -> tuple[list[str], int | None]:
    """Each line's rendered text, with code left out, and the line of a fence left open at the end, if any.

    Inline text, link text and raw HTML (inline or a block) count; code spans, fenced and indented code don't.
    Lines are split as CommonMark splits them (``\\n``, ``\\r\\n`` or ``\\r``), so line numbers match the source.
    """
    src = text.replace("\r\n", "\n").replace("\r", "\n")
    raw = src.split("\n")
    lines = [""] * len(raw)
    open_fence = None
    for tok in MARKDOWN.parse(src):
        if tok.map is None:
            continue
        first, end = tok.map
        if tok.type == "html_block":
            for i in range(first, end):
                lines[i] += raw[i]
        elif tok.type == "fence":
            closer = raw[end - 1].strip()
            fence_char = tok.markup[0]
            closed = end - first >= 2 and len(closer) >= len(tok.markup) and closer == fence_char * len(closer)
            if not closed:
                open_fence = first + 1
        elif tok.type == "inline":
            line = first
            lines[line] += " "  # table cells share a line; one cell's text must not run into the next
            for child in tok.children or []:
                if child.type in ("softbreak", "hardbreak"):
                    line += 1
                elif child.type in ("text", "html_inline"):
                    lines[line] += child.content
    return lines, open_fence


def _markdown_problems(rel: str, text: str) -> list[str]:
    lines, open_fence = markdown_prose(text)
    problems = []
    for lineno, line in enumerate(lines, 1):
        if TEMP_MARKER.search(line) or PRAGMA.search(line):
            problems.append(
                f"{rel}:{lineno}: a document holds no band-aid markers or pragmas: quote one in `code`, and defer a "
                "finding with no code to mark as a backlog row or a known gap"
            )
    if open_fence is not None:
        problems.append(f"{rel}:{open_fence}: this code fence is never closed, so nothing after it is checked")
    return problems


def check_markers(files: dict[str, str], roadmap: str) -> list[str]:
    sections = phase_sections(roadmap)
    problems = []
    for rel, text in sorted(files.items()):
        if rel in MARKER_EXEMPT:
            continue
        if rel.endswith(".md"):
            problems += _markdown_problems(rel, text)
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
                if not re.search(rf"(?<![\w./-]){re.escape(rel)}(?![\w/-])", body):
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
    ids = [int(m.group(1)) for ln in backlog.splitlines() if (m := BACKLOG_ROW.match(ln))]
    rows = set(ids)
    # Branches add rows in parallel; a merge that keeps two rows with one id would let a guard cite the wrong row.
    problems = [
        f"docs/standards_backlog.md: backlog row B{b} is defined {ids.count(b)} times"
        for b in sorted(rows)
        if ids.count(b) > 1
    ]
    bullets = standards_bullets(claude_md)
    if not bullets:
        return [*problems, f"CLAUDE.md: no '{STANDARDS_HEADING}' section with rule bullets"], 0, 0
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


def base_pyproject(root: Path, base: str | None) -> tuple[str | None, list[str]]:
    """The base's pyproject.toml, or None when there is no base or the base has no pyproject. An unknown ref is a
    finding, not a skip: a typo must not quietly switch the ratchet off."""
    if base is None:
        return None, []
    verify = ["git", "rev-parse", "--verify", "-q", f"{base}^{{commit}}"]
    known = subprocess.run(verify, cwd=root, capture_output=True, check=False)
    if known.returncode != 0:
        return None, [f"--base {base} is not a commit in this repository, so the coverage ratchet can't run"]
    show = ["git", "show", f"{base}:pyproject.toml"]
    out = subprocess.run(show, cwd=root, capture_output=True, text=True, check=False)
    return (out.stdout if out.returncode == 0 else None), []


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", help="git ref whose coverage floor this branch may not go below")
    args = parser.parse_args(argv)

    backlog_path = root / "docs/standards_backlog.md"
    backlog = backlog_path.read_text() if backlog_path.exists() else ""
    problems = check_markers(tracked_text_files(root), (root / "docs/roadmap.md").read_text())
    guard_problems, checked, review_only = check_guards((root / "CLAUDE.md").read_text(), backlog, root)
    problems += guard_problems
    base_text, base_problems = base_pyproject(root, args.base)
    problems += base_problems
    problems += check_coverage_ratchet((root / "pyproject.toml").read_text(), base_text)
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
