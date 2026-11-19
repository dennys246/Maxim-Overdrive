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
5. Separation of concerns: in ``src/`` and ``scripts/``, no function body, module or class may outgrow the limits in
   ``[tool.maxim_overdrive.size_limits]``, and no ``noqa`` may silence the complexity rules. A function that doesn't
   fit is split by responsibility; the limit is a tripwire for a god function, not a target. The limits only tighten:
   none may rise above the base branch's.

Run: ``python scripts/lint_standards.py [--base REF]`` (exit 1 on any finding). scripts/prepush.sh runs it.
"""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

from markdown_it import MarkdownIt
from markdown_it.token import Token

ROOT = Path(__file__).resolve().parents[1]

# Upper case always counts; any other case counts when it cites a phase, so "a temporary (two-turn) fire" in prose is
# not a marker but "temporary (phase2): ..." is.
TEMP_MARKER = re.compile(r"\b(?:TEMPORARY|(?i:temporary)(?=\s*\(\s*phase))\s*\(([^)]*)\)")
TEMP_TARGET = re.compile(r"^phase(\d+)(?:/[a-z0-9][a-z0-9_-]*)?$")
PRAGMA = re.compile(r"pragma:\s*no\s*cover", re.IGNORECASE)
PRAGMA_REASON = re.compile(r"pragma:\s*no\s*cover\s*(?:-+|:)\s*\S.{8,}", re.IGNORECASE)
PHASE_HEADING = re.compile(r"^## Phase (\d+):.*\((\w+)[^)]*\)\s*$")
# Every rule in these sections must name its guard. Honesty comes first in CLAUDE.md, and the lint reads it too.
STANDARDS_HEADINGS = ("## First principle: brutal honesty", "## Engineering standards")
GUARD = re.compile(r"Guard:\s*(.+)$")
PATH_REF = re.compile(r"`([^`]+)`")
BACKLOG_REF = re.compile(r"\bB(\d+)\b")
BACKLOG_ROW = re.compile(r"^\|\s*B(\d+)\s*\|")
# A noqa that silences a complexity rule, a blanket noqa (which silences every rule), or a file-wide exemption in
# ruff's or flake8's spelling (ruff honours both). The scan is by line, so a string that spells one is flagged too.
COMPLEXITY_NOQA = re.compile(
    r"#\s*noqa:[^#\n]*\b(?:C90\d?|PLR091[1-5])\b|#\s*noqa(?!\s*:)|#\s*(?:ruff|flake8)\s*:\s*noqa", re.IGNORECASE
)
SIZE_SCOPE = ("src/", "scripts/")
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


LEAF_BLOCKS = ("inline", "fence", "code_block", "html_block")
DOC_FINDING = (
    "a document holds no band-aid markers or pragmas: quote one in a Markdown code span or code block, and defer a "
    "finding with no code to mark as a backlog row or a known gap"
)


def _inline_text(children: list[Token]) -> str:
    """The rendered text of an inline token: code spans are left out (a space keeps their neighbours apart), breaks
    render as newlines so a marker split across lines still matches, and image alt text counts."""
    text = []
    for child in children:
        if child.type == "code_inline":
            text.append(" ")
        elif child.type in ("softbreak", "hardbreak"):
            text.append("\n")
        elif child.type in ("text", "html_inline"):
            text.append(child.content)
        elif child.type == "image":
            text.append(_inline_text(child.children or []))
    return "".join(text)


def _line_count(text: str) -> int:
    """Lines in ``text``, split on ``\\n`` alone as CommonMark splits them; a last line needs no newline."""
    return text.count("\n") + (text != "" and not text.endswith("\n"))


def _markdown_problems(rel: str, text: str) -> list[str]:
    """Markers and pragmas in what a document renders as text, and fences that hide the rest of it.

    markdown-it decides what is code, so this holds no CommonMark rules of its own. A finding in rendered inline text
    is reported at the first line of its paragraph, heading or table row: the parser places blocks, not words. Raw
    HTML, and any source line no leaf block covers (a footnote or link definition, which CommonMark drops but GitHub
    shows), are checked line by line as written. Fenced and indented code are skipped.
    """
    src = text.replace("\r\n", "\n").replace("\r", "\n")
    raw = src.split("\n")
    # The last non-blank line; CommonMark counts only spaces and tabs as blank, not NBSP or a form feed.
    last = max((i for i, line in enumerate(raw) if line.strip(" \t")), default=-1)
    covered: set[int] = set()
    lines: set[int] = set()
    open_fences: list[int] = []
    for tok in MARKDOWN.parse(src):
        if tok.map is None or tok.type not in LEAF_BLOCKS:
            continue
        first, end = tok.map
        covered.update(range(first, end))
        if tok.type == "inline":
            rendered = _inline_text(tok.children or [])
            if TEMP_MARKER.search(rendered) or PRAGMA.search(rendered):
                lines.add(first + 1)
        elif tok.type == "html_block":
            lines.update(i + 1 for i in range(first, end) if TEMP_MARKER.search(raw[i]) or PRAGMA.search(raw[i]))
        elif tok.type == "fence" and end > last and _line_count(tok.content) == end - first - 1:
            # A fence that reaches the end of the document is open when its lines are the opener and its content
            # alone: a closed fence's lines also hold its closer. Its container's end (a blockquote or list item the
            # document's end closes) doesn't count as closing it: the rest is still shown as code.
            open_fences.append(first + 1)
    lines.update(
        i + 1 for i, line in enumerate(raw) if i not in covered and (TEMP_MARKER.search(line) or PRAGMA.search(line))
    )
    problems = [f"{rel}:{n}: {DOC_FINDING}" for n in sorted(lines)]
    problems += [f"{rel}:{n}: this code fence is never closed, so nothing after it is checked" for n in open_fences]
    return problems


def _pragma_problem(line: str, where: str) -> str | None:
    if PRAGMA.search(line) and not PRAGMA_REASON.search(line):
        return f"{where}: 'pragma: no cover' needs a reason: '# pragma: no cover - <why>'"
    return None


def _marker_problems(
    m: re.Match[str], line: str, where: str, rel: str, sections: dict[int, tuple[str, str]]
) -> list[str]:
    target = m.group(1).strip()
    rest = line[m.end() :]
    problems = []
    if not rest.lstrip().startswith(":") or len(rest.strip(" :")) < 10:
        problems.append(f"{where}: TEMPORARY({target}) needs ': <why, and what the real fix is>'")
    t = TEMP_TARGET.match(target)
    if not t:
        return [*problems, f"{where}: TEMPORARY({target}) must cite a roadmap phase, e.g. TEMPORARY(phase2)"]
    n = int(t.group(1))
    if n not in sections:
        return [*problems, f"{where}: TEMPORARY({target}) cites phase {n}, which docs/roadmap.md lacks"]
    status, body = sections[n]
    if status == "done":
        problems.append(f"{where}: TEMPORARY({target}): phase {n} is done, so this was due to be removed")
    if not re.search(rf"(?<![\w./-]){re.escape(rel)}(?![\w/-])", body):
        problems.append(f"{where}: TEMPORARY({target}): list {rel} under Phase {n} in docs/roadmap.md")
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
            if p := _pragma_problem(line, where):
                problems.append(p)
            for m in TEMP_MARKER.finditer(line):
                problems += _marker_problems(m, line, where, rel, sections)
    return problems


@dataclass(frozen=True)
class SizeLimits:
    function_lines: int
    module_lines: int
    public_methods: int


def size_limits(pyproject: str) -> tuple[SizeLimits | None, list[str]]:
    table = tomllib.loads(pyproject).get("tool", {}).get("maxim_overdrive", {}).get("size_limits")
    names = ("function_lines", "module_lines", "public_methods")
    if not isinstance(table, dict) or set(table) != set(names):
        return None, [f"pyproject.toml: [tool.maxim_overdrive.size_limits] must set exactly {', '.join(names)}"]
    if not all(type(table[n]) is int and table[n] > 0 for n in names):
        return None, ["pyproject.toml: every size limit must be a positive integer"]
    return SizeLimits(**{n: table[n] for n in names}), []


def check_size_ratchet(current: SizeLimits, base: str | None) -> list[str]:
    """The size limits only tighten: no limit may rise above the base branch's."""
    before, _ = size_limits(base) if base is not None else (None, [])
    if before is None:
        return []
    return [
        f"pyproject.toml: size limit {name} rose from {getattr(before, name)} to {getattr(current, name)}; "
        "limits only tighten"
        for name in ("function_lines", "module_lines", "public_methods")
        if getattr(current, name) > getattr(before, name)
    ]


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


def _body_lines(fn: ast.FunctionDef | ast.AsyncFunctionDef, lines: list[str]) -> int:
    """Lines of code in the body: the docstring, blank lines and comment-only lines don't count, so the limit never
    pushes anyone to delete an explanation. Approximate by design: a line inside a multi-line string that starts with
    ``#`` is skipped too."""
    first = fn.body[0]
    docstring = (
        isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str)
    )
    body = fn.body[1:] if docstring else fn.body
    if not body:
        return 0
    end = fn.end_lineno if fn.end_lineno is not None else body[-1].lineno
    return sum(1 for ln in lines[body[0].lineno - 1 : end] if ln.strip() and not ln.lstrip().startswith("#"))


def _tree_problems(rel: str, tree: ast.Module, lines: list[str], limits: SizeLimits) -> list[str]:
    """Function bodies and public methods. A class's public methods are the ``def``s in its own body, properties and
    each ``@overload`` stub included: they are all surface a caller can reach."""
    problems = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
            and (n := _body_lines(node, lines)) > limits.function_lines
        ):
            problems.append(
                f"{rel}:{node.lineno}: {node.name} has a {n}-line body (limit {limits.function_lines}); "
                "split it by responsibility"
            )
        if isinstance(node, ast.ClassDef):
            public = [
                m
                for m in node.body
                if isinstance(m, ast.FunctionDef | ast.AsyncFunctionDef) and not m.name.startswith("_")
            ]
            if len(public) > limits.public_methods:
                problems.append(
                    f"{rel}:{node.lineno}: class {node.name} has {len(public)} public methods "
                    f"(limit {limits.public_methods}); it is doing more than one job"
                )
    return problems


def check_sizes(files: dict[str, str], limits: SizeLimits) -> list[str]:
    """God-function tripwires over the code coverage measures (``src/`` and ``scripts/``)."""
    problems = []
    for rel, text in sorted(files.items()):
        if not (rel.endswith(".py") and rel.startswith(SIZE_SCOPE)):
            continue
        lines = text.splitlines()
        if len(lines) > limits.module_lines:
            problems.append(f"{rel}: {len(lines)} lines (limit {limits.module_lines}); split the module by concern")
        problems += [
            f"{rel}:{i}: a noqa may not silence the complexity rules; split the code instead"
            for i, ln in enumerate(lines, 1)
            if COMPLEXITY_NOQA.search(ln)
        ]
        try:
            tree = ast.parse(text, filename=rel)
        except SyntaxError as exc:  # reported as a finding: an unparseable file must not pass the size check unread
            problems.append(f"{rel}:{exc.lineno}: does not parse, so its sizes can't be checked: {exc.msg}")
            continue
        problems += _tree_problems(rel, tree, lines, limits)
    return problems


def standards_bullets(claude_md: str) -> tuple[list[tuple[int, str]], list[str]]:
    """Top-level bullets in every rule section, joined across continuation lines, plus the sections not found."""
    lines = claude_md.splitlines()
    bullets: list[tuple[int, str]] = []
    missing: list[str] = []
    for heading in STANDARDS_HEADINGS:
        start = next((i for i, ln in enumerate(lines) if ln.strip() == heading), None)
        if start is None:
            missing.append(heading)
            continue
        section: list[tuple[int, str]] = []
        for i in range(start + 1, len(lines)):
            ln = lines[i]
            if ln.startswith("## "):
                break
            if ln.startswith("- "):
                section.append((i + 1, ln))
            elif section and ln.startswith("  ") and ln.strip():
                section[-1] = (section[-1][0], section[-1][1] + " " + ln.strip())
        if not section:
            missing.append(heading)
        bullets.extend(section)
    return bullets, missing


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
    bullets, missing = standards_bullets(claude_md)
    problems += [f"CLAUDE.md: no '{heading}' section with rule bullets" for heading in missing]
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
    value = tomllib.loads(pyproject).get("tool", {}).get("coverage", {}).get("report", {}).get("fail_under")
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
        return None, [f"--base {base} is not a commit in this repository, so the coverage and size ratchets can't run"]
    show = ["git", "show", f"{base}:pyproject.toml"]
    out = subprocess.run(show, cwd=root, capture_output=True, text=True, check=False)
    return (out.stdout if out.returncode == 0 else None), []


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
    verdict = "FAIL" if problems else "PASS"
    print(
        f"lint_standards: {verdict} ({len(problems)} finding(s)); rules enforced by a check: {checked}, "
        f"held only by review (backlog): {review_only}"
    )
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
