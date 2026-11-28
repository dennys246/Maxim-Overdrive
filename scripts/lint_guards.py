"""Standards check 3: guard citations (CLAUDE.md, "Engineering standards").

Every rule bullet under CLAUDE.md's "Engineering standards" (and its first principle) ends with ``Guard:`` and names
files that exist (``path``, or ``path::symbol`` where the symbol appears as a whole word outside comments, and, in a
``.py`` file, as a definition) and/or backlog rows (``B7``) in docs/standards_backlog.md. A rule whose only guards are
documents must also cite a backlog row: a document is not a check. The counts returned say how many rules a check
enforces and how many only review holds, so neither number hides.
"""

from __future__ import annotations

import re
from pathlib import Path

from records import BY_NAME, load_records

# Every rule in these sections must name its guard. Honesty comes first in CLAUDE.md, and the lint reads it too.
STANDARDS_HEADINGS = ("## First principle: brutal honesty", "## Engineering standards")
GUARD = re.compile(r"Guard:\s*(.+)$")
PATH_REF = re.compile(r"`([^`]+)`")
BACKLOG_REF = re.compile(r"\bB(\d+)\b")
BACKLOG_ROW = re.compile(r"^\|\s*B(\d+)\s*\|")
COMMENT_PREFIX = {".py": "#", ".toml": "#", ".sh": "#", ".yml": "#", ".yaml": "#", ".gitignore": "#", ".gd": "#"}


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


def backlog_numbers(backlog: str, root: Path) -> tuple[list[int], str]:
    """Every backlog row's number, from the records under ``docs/standards_backlog/`` when it holds any, and where
    they were read. A record the reader refuses is lint_records' finding."""
    directory = root / BY_NAME["backlog"].root
    texts = {
        f"{BY_NAME['backlog'].root}{p.name}": p.read_text(encoding="utf-8") for p in sorted(directory.glob("*.md"))
    }
    records = load_records(texts)[0] if directory.is_dir() else []
    if records:
        return [int(r.id[1:]) for r in records], BY_NAME["backlog"].root
    # TEMPORARY(phase1/records-build): the backlog is a hand-written table until R3's migration commit makes it
    # generated from its records; R3 removes this table reading.
    return [int(m.group(1)) for ln in backlog.splitlines() if (m := BACKLOG_ROW.match(ln))], "docs/standards_backlog.md"


def check_guards(claude_md: str, backlog: str, root: Path) -> tuple[list[str], int, int]:
    """Findings, plus how many rules a check enforces and how many only review holds."""
    ids, source = backlog_numbers(backlog, root)
    rows = set(ids)
    # Branches add rows in parallel; a merge that keeps two rows with one id would let a guard cite the wrong row.
    problems = [
        f"{source}: backlog row B{b} is defined {ids.count(b)} times"
        + (
            f": the branch merged second runs `scripts/records.py renumber B{b}=<next free id>`"
            if source.endswith("/")
            else ""
        )
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
