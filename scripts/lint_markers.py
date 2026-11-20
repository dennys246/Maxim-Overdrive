"""Standards check 1: ``TEMPORARY(...)`` markers and ``pragma: no cover`` reasons (CLAUDE.md, "Fix root causes").

A marker is the one allowed exemption to the no-band-aid rule. Each must give a reason and cite a roadmap phase that
exists, is not done, and lists the marker's file in its section of docs/roadmap.md, so a band-aid can't outlive the
moment promised to remove it, and the roadmap shows every one that is open. A ``pragma: no cover`` must say why the
line can't be tested.

Markdown holds no band-aids, so it holds no markers or pragmas. A document that explains or reviews the rule quotes
their syntax in code (an inline span or a code block), and anything that renders as text is a finding. Documents are
parsed by markdown-it as CommonMark plus GitHub's tables, the way they render, rather than by a hand-written
approximation; raw HTML counts as text, and a fence left open at the end of a file is a finding.
"""

from __future__ import annotations

import re

from markdown_it import MarkdownIt
from markdown_it.token import Token

# Upper case always counts; any other case counts when it cites a phase, so "a temporary (two-turn) fire" in prose is
# not a marker but "temporary (phase2): ..." is.
TEMP_MARKER = re.compile(r"\b(?:TEMPORARY|(?i:temporary)(?=\s*\(\s*phase))\s*\(([^)]*)\)")
TEMP_TARGET = re.compile(r"^phase(\d+)(?:/[a-z0-9][a-z0-9_-]*)?$")
PRAGMA = re.compile(r"pragma:\s*no\s*cover", re.IGNORECASE)
PRAGMA_REASON = re.compile(r"pragma:\s*no\s*cover\s*(?:-+|:)\s*\S.{8,}", re.IGNORECASE)
PHASE_HEADING = re.compile(r"^## Phase (\d+):.*\((\w+)[^)]*\)\s*$")


# The lint and its tests write markers and pragmas as data. Documents need no entry: they quote them in code.
MARKER_EXEMPT = {"scripts/lint_standards.py", "scripts/lint_markers.py", "tests/test_lint_standards.py"}
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
