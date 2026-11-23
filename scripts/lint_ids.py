"""Record ids no two branches may share, and lesson citations that must resolve.

Parallel sessions add decisions and lessons on their own branches, and the owner merges them on GitHub. Two branches
can take the same next number and both pass their own gate. This check catches the collision on the first gate that
sees both, with a message that says who renumbers.

**Decisions.** Every table row in ``docs/design/decisions/*.md`` whose first cell is a single id is a record:
``O57``, ``D34``, ``T1``, ``TP1``, ``OA3``, ``O7a``, ``PH2-S2``. Backticks and bold around the id are ignored, and a
trailing qualifier is allowed (``D12, provisional``, ``O58 (provisional)``), so a decorated cell can't dodge the
check. A family is an id **prefix across every decision log**. ``D`` is used by two designs (``sem_stimuli`` D1-D15
and ``world_model`` D20 onward), and their numbers don't overlap today; holding the prefix unique keeps a bare
citation like "D3" unambiguous. An id may appear in two logs only when the decision is cross-listed: each row's status
cell names the other log as ``also in `decisions/<log>.md```. Anything else is a collision. First cells that aren't a
single id are not records and are skipped: ranges and lists that restate other rows (en-dash ranges such as
``D26``-to-``D28`` or ``RT1``-to-``4``, and lists such as ``O23, O24, O31``) and unnumbered rulings (``ruled 1``,
``the split``, ``—``).

**Phase 3 items.** Every table row of ``docs/roadmap.md`` whose first cell is an ``OD-<letters><n>`` id
(``OD-I13``) is an item, and each id is defined once.

Citations of decisions and items are not resolved: Maxim's own decision ids (``D53``) and frozen pre-registrations
use the same shapes, so a bare ``D36`` can't be told apart from one of ours. A renumber's citations are the author's
to move, and a green check doesn't say the renumber is complete: a missed citation still resolves to the other
branch's record.

**Lessons.** Headings ``### N.`` in ``docs/lessons_maxim_in_games.md`` must be unique. A citation of a lesson number
with no heading fails. The spellings read: ``lesson N``, ``Lesson N``, ``lessons N and N``, ``lessons N, N and N``,
en-dash ranges ``lessons N``-to-``N`` and ``lessons N to N`` (both ends), ``lesson §N``, and the file name followed
by ``§N``, ``N``, ``::N`` or ``§N, §N``. A four-digit number after a separator ends the list, so
``lesson 24, 2026-11-20`` cites lesson 24 only. They are read in ``docs/**/*.md`` and in the ``reason=`` strings of
``tests/*.py``. Files listed in any ``freeze.sha256`` are skipped: they can never be edited, so a renumber must leave
them alone. Without the lessons file, any citation is a finding: a moved or renamed file must not turn the check off.

The backlog's B-ids are not checked here: ``lint_guards`` already refuses a backlog row defined twice, and one rule
has one owner.
"""

from __future__ import annotations

import ast
import posixpath
import re
from collections import defaultdict
from pathlib import PurePosixPath

DECISIONS = "docs/design/decisions/"
LESSONS = "docs/lessons_maxim_in_games.md"
ROADMAP = "docs/roadmap.md"
_ID_CELL = re.compile(r"^((?:[A-Z]+\d*-)?[A-Z]+)(\d+)([a-z]?)(?:,\s*[a-z][a-z -]*|\s+\([a-z][a-z -]*\))?$")
_DECORATION = re.compile(r"[`*]")
_ROADMAP_ID = re.compile(r"^(OD-[A-Z]+\d+[a-z]?)$")
_ROW = re.compile(r"^\|\s*([^|]+?)\s*\|")
_ALSO_IN = re.compile(r"also in `decisions/([a-z_]+\.md)`")
_HEADING = re.compile(r"^### (\d+)\.", re.M)
_GAP = r"(?:[ \t]+|[ \t]*\n[ \t]*)"  # whitespace that never crosses a blank line
_SEP_GAP = r"[ \t]*(?:\n[ \t]*)?"  # the same, but possibly none, after a list separator (an en-dash range)
_CITE = re.compile(
    rf"\b[Ll]essons?{_GAP}(?:§[ \t]*)?(\d+(?:[ \t]*(?:,|and|\u2013|-|to){_SEP_GAP}(?!\d{{4}})(?:§[ \t]*)?\d+)*)"
    rf"|lessons_maxim_in_games\.md`?(?:::|[ \t]*§?[ \t]*)(\d+(?:[ \t]*(?:,|and|\u2013){_SEP_GAP}§[ \t]*\d+)*)"
)


def _decision_rows(files: dict[str, str]) -> dict[str, list[tuple[str, int, str]]]:
    """Each record id with where it is defined: (log, line, status cell)."""
    rows: dict[str, list[tuple[str, int, str]]] = defaultdict(list)
    for rel in sorted(files):
        if not (rel.startswith(DECISIONS) and rel.endswith(".md")):
            continue
        for number, line in enumerate(files[rel].splitlines(), start=1):
            m = _ROW.match(line)
            if m is None:
                continue
            cell = _ID_CELL.match(_DECORATION.sub("", m.group(1)).strip())
            if cell is None:
                continue
            ident = f"{cell.group(1)}{cell.group(2)}{cell.group(3)}"
            status = line.rstrip().rstrip("|").rsplit("|", 1)[-1]
            rows[ident].append((PurePosixPath(rel).name, number, status))
    return rows


def _cross_listed(defs: list[tuple[str, int, str]]) -> bool:
    """Two definitions in two logs, each naming the other as ``also in``."""
    if len(defs) != 2 or defs[0][0] == defs[1][0]:
        return False
    (log_a, _, status_a), (log_b, _, status_b) = defs
    return log_b in _ALSO_IN.findall(status_a) and log_a in _ALSO_IN.findall(status_b)


def check_decisions(files: dict[str, str]) -> list[str]:
    problems = []
    for ident, defs in sorted(_decision_rows(files).items()):
        if len(defs) > 1 and not _cross_listed(defs):
            where = ", ".join(f"{DECISIONS}{log}:{line}" for log, line, _ in defs)
            problems.append(
                f"decision id {ident} is defined {len(defs)} times ({where}): two branches took the same id; the one "
                "merged second renumbers its own decision and its own citations, or a cross-listed decision says "
                "'also in `decisions/<log>.md`' in both rows"
            )
    return problems


def check_roadmap_ids(files: dict[str, str]) -> list[str]:
    """Phase 3 items (``OD-I13``) are numbered in parallel by branches too: each is one row of the roadmap."""
    seen: dict[str, list[int]] = defaultdict(list)
    for number, line in enumerate(files.get(ROADMAP, "").splitlines(), start=1):
        m = _ROW.match(line)
        cell = _ROADMAP_ID.match(_DECORATION.sub("", m.group(1)).strip()) if m else None
        if cell is not None:
            seen[cell.group(1)].append(number)
    return [
        f"{ROADMAP}: item {ident} is defined {len(lines)} times (lines {', '.join(map(str, lines))}): two branches "
        "took the same id; the one merged second renumbers its own item and its own citations"
        for ident, lines in sorted(seen.items())
        if len(lines) > 1
    ]


def _cited(text: str) -> list[tuple[int, int]]:
    """(lesson number, line) for every citation in the text; a range cites both ends."""
    out: list[tuple[int, int]] = []
    for m in _CITE.finditer(text):
        line = text.count("\n", 0, m.start()) + 1
        numbers = m.group(1) or m.group(2)
        out.extend((int(n), line) for n in re.findall(r"\d+", numbers))
    return out


def _reason_strings(source: str) -> list[tuple[str, int]]:
    """The constant ``reason=`` strings of a test module, with their lines."""
    tree = ast.parse(source)  # a syntax error fails the lint loudly, as ruff and pytest also report it
    out: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.keyword)
            and node.arg == "reason"
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            out.append((node.value.value, node.value.lineno))
    return out


def frozen_files(files: dict[str, str]) -> set[str]:
    """Every file a ``freeze.sha256`` manifest lists, as a repository path."""
    frozen: set[str] = set()
    for rel, text in files.items():
        if PurePosixPath(rel).name != "freeze.sha256":
            continue
        base = PurePosixPath(rel).parent
        for line in text.splitlines():
            parts = line.split()
            if len(parts) == 2 and not line.startswith("#") and ":" not in parts[1]:
                frozen.add(posixpath.normpath(str(base / parts[1])))
    return frozen


def _citations(files: dict[str, str]) -> list[tuple[int, str, int]]:
    """(lesson, file, line) for every citation in scope."""
    frozen = frozen_files(files)
    out: list[tuple[int, str, int]] = []
    for rel in sorted(files):
        if rel in frozen:
            continue
        if rel.startswith("docs/") and rel.endswith(".md"):
            out.extend((n, rel, line) for n, line in _cited(files[rel]))
        elif rel.startswith("tests/") and rel.endswith(".py"):
            for text, start in _reason_strings(files[rel]):
                out.extend((n, rel, start + line - 1) for n, line in _cited(text))
    return out


def check_lessons(files: dict[str, str]) -> list[str]:
    if LESSONS not in files:
        cited = _citations(files)
        if not cited:
            return []  # a tree with no lessons and no citation of one (a fixture) has nothing to hold
        n, rel, line = cited[0]
        return [f"{LESSONS} is missing, but {len(cited)} citation(s) cite it, first {rel}:{line} (lesson {n})"]
    headings = [int(n) for n in _HEADING.findall(files[LESSONS])]
    problems = [
        f"{LESSONS}: two branches took lesson {n}: the one merged second renumbers its own lesson and its own citations"
        for n in sorted({n for n in headings if headings.count(n) > 1})
    ]
    known = set(headings)
    for n, rel, line in _citations(files):
        if n not in known:
            problems.append(
                f"{rel}:{line}: cites lesson {n}, which {LESSONS} doesn't have: cite an existing lesson, or add the "
                "lesson in the same branch"
            )
    return problems


def check_ids(files: dict[str, str]) -> list[str]:
    """Every finding: decision and roadmap ids taken twice, lessons numbered twice, and citations that don't resolve."""
    return check_decisions(files) + check_roadmap_ids(files) + check_lessons(files)
