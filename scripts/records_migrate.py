"""Stage 1 of the migration (records_layout §8, RL11): today's four files parsed into records, losing nothing.

``migrate`` reads the lessons file, every decision log, the Known gaps file and the standards backlog, and returns the
records and the ``_header.md`` of each family directory. Regenerating today's forms from them (``records_index``)
reproduces each original byte for byte, apart from the marker line. Every presentation fact no other field holds goes
into ``legacy``; a value the source lacks is ``unknown``; a title the source lacks comes from the hand file. Each of
those is listed, for the migration commit to carry. Nothing is invented.
"""

from __future__ import annotations

import itertools
import re
from collections.abc import Mapping
from dataclasses import dataclass

from records import BACKLOG, GAP, LESSON, UNKNOWN, Line, Record, file_name, slugify, stated_status
from records_decisions import MigrationError
from records_decisions_build import Hand, build
from records_index import BACKLOG_FILE, BACKLOG_HEAD, GAPS_FILE, LESSONS_FILE

from simcore.core.schema import Field, Format, ListOf, Nested, Schema

DECISION_LOGS = "docs/design/decisions/"
_LESSON_HEADING = re.compile(r"^### (\d+)\. (.*) \((\d{4}-\d{2}-\d{2})(.*)\)$")
_SECTION = re.compile(r"^## (.+)$")
_GAP_LEAD = re.compile(r"^\*\*(.+?)\*\*")
_RED_GATE = re.compile(r"red gate[^`]{0,80}`(tests/[^`\s]+::[^`\s]+)`", re.S | re.I)
GAP_KEY_CHARS = 40  # a gap's hand key: the first characters of its bullet

_PAIRS = ListOf(Nested(Schema((Field("key", Line(max_chars=200)), Field("value", Line())))), max_items=512)
HAND = Format(
    "records migration hand file",
    1,
    Schema(
        tuple(Field(name, _PAIRS, required=False, default=()) for name in ("titles", "aliases", "kinds", "closes_at"))
    ),
)


def read_hand(raw: object) -> Hand:
    """The hand file, read by its format, as a ``Hand``; a key given twice is refused by name."""
    doc = HAND.read(raw, "the migration's hand file")
    out: dict[str, dict[str, str]] = {}
    for name in ("titles", "aliases", "kinds", "closes_at"):
        entries = doc[name]
        pairs = (
            [(str(p["key"]), str(p["value"])) for p in entries if isinstance(p, Mapping)]
            if isinstance(entries, tuple)
            else []
        )
        keys = [k for k, _ in pairs]
        if len(set(keys)) != len(keys):
            raise MigrationError(f"the hand file's {name} names a key twice")
        out[name] = dict(pairs)
    return Hand(out["titles"], out["aliases"], out["kinds"], out["closes_at"])


@dataclass(frozen=True)
class Migration:
    """What stage 1 produces: the records, each family directory's ``_header.md`` by path, and the listing."""

    records: list[Record]
    headers: dict[str, str]
    listed: list[str]


def _record(fmt: Format, family: str, root: str, raw: dict[str, object], body: str) -> Record:
    meta = fmt.read({"version": 1, **raw}, f"a migrated {fmt.name}")
    return Record(family, f"{root}{file_name(family, meta['id'], str(meta['slug']))}", meta, body)


def lessons(text: str) -> tuple[str, list[Record]]:
    """The lessons file's head and its lessons: each heading's number, title and date, its section, and its body."""
    lines = text.split("\n")
    first = next(i for i, line in enumerate(lines) if _SECTION.match(line))
    head, section, out = "\n".join(lines[:first]) + "\n", "", []
    starts = [i for i, line in enumerate(lines) if line.startswith("## ") or line.startswith("### ")] + [len(lines)]
    for start, end in itertools.pairwise(starts):
        if (m := _SECTION.match(lines[start])) and not lines[start].startswith("###"):
            section = m.group(1)
            continue
        h = _LESSON_HEADING.match(lines[start])
        if h is None:
            raise MigrationError(f"{LESSONS_FILE}:{start + 1}: a lesson heading without its date: {lines[start]}")
        body = "\n".join(lines[start + 1 : end]).strip("\n") + "\n"
        raw: dict[str, object] = {"id": int(h.group(1)), "slug": slugify(h.group(2)), "title": h.group(2)}
        raw |= {"date": h.group(3), "section": section, "amended": []}
        if h.group(4):
            raw["legacy"] = {"heading_tail": h.group(4)}
        out.append(_record(LESSON, "lessons", "docs/lessons/", raw, body))
    return head, out


def _bullets(lines: list[str]) -> list[tuple[str | None, list[str]]]:
    """(group line, the bullet's lines without their marks) for each bullet, in order."""
    out: list[tuple[str | None, list[str]]] = []
    group = None
    for number, line in enumerate(lines, start=1):
        if line.startswith("- "):
            out.append((group, [line[2:]]))
        elif line.startswith("  ") and out and line.strip():
            out[-1][1].append(line[2:])
        elif line.startswith("**") and line.endswith("**"):
            group = line
        elif line:
            raise MigrationError(f"{GAPS_FILE}: line {number} of its list is not a bullet or a group: {line[:60]}")
    return out


def gaps(text: str, hand: Hand) -> tuple[str, list[Record], list[str]]:
    """The Known gaps file's head and its gaps: a title from the bold lead or the hand file, the red gate when the
    prose names one, the kind and the closing step only from the hand file, and the bullet's group and position."""
    lines = text.split("\n")
    first = next(i for i, line in enumerate(lines) if line.startswith("**") and line.endswith("**"))
    head, out, listed = "\n".join(lines[:first]) + "\n", [], []
    for position, (group, body_lines) in enumerate(_bullets(lines[first:]), start=1):
        body = "\n".join(body_lines) + "\n"
        key = body[:GAP_KEY_CHARS]
        lead = _GAP_LEAD.match(body)
        title = lead.group(1).strip().rstrip(",:;").strip() if lead else hand.titles.get(f"gap:{key}")
        if title is None:
            raise MigrationError(f"the gap beginning {key!r} has no bold lead and no hand title")
        if lead is None:
            listed.append(f"hand title: gap {key!r}: {title}")
        gate = _RED_GATE.search(body)
        slug = slugify(title)
        raw: dict[str, object] = {"id": slug, "slug": slug, "title": title, "date": UNKNOWN}
        raw |= {"kind": hand.kinds.get(slug, UNKNOWN), "gate": gate.group(1) if gate else UNKNOWN}
        listed += [
            f"hand {name}: gap {slug}: {given[slug]}"
            for name, given in (("kind", hand.kinds), ("closes_at", hand.closes_at))
            if slug in given
        ]
        raw |= {"closes_at": hand.closes_at.get(slug, UNKNOWN), "legacy": {"position": position, "group": group}}
        out.append(_record(GAP, "gaps", "docs/known_gaps/", raw, body))
    return head, out, listed


def backlog(text: str) -> tuple[str, list[Record]]:
    """The backlog's head and its rows: id, rule, check and lands-with cells, and the status its prose states."""
    head, sep, table = text.partition(BACKLOG_HEAD)
    if not sep:
        raise MigrationError(f"{BACKLOG_FILE}: no table headed as today's")
    out = []
    for line in table.split("\n")[:-1]:
        cells = line[2:-2].split(" | ")
        if not (line.startswith("| B") and line.endswith(" |") and len(cells) in (3, 4)):
            raise MigrationError(f"{BACKLOG_FILE}: a row that is not three or four cells: {line[:60]}")
        ident, rule, check = cells[:3]
        lands_with = cells[3] if len(cells) == 4 else None
        status, done_in = stated_status(check, lands_with)
        raw: dict[str, object] = {"id": ident, "slug": slugify(rule), "title": rule, "date": UNKNOWN, "rule": rule}
        raw |= {"lands_with": lands_with or UNKNOWN, "status": status}
        if done_in:
            raw["done_in"] = done_in
        if len(cells) == 3:
            raw["legacy"] = {"three_cells": True}
        out.append(_record(BACKLOG, "backlog", "docs/standards_backlog/", raw, check + "\n"))
    return head, out


def migrate(files: Mapping[str, str], hand: Hand) -> Migration:
    """Today's four files, as records and headers, with the listing of every hand title and unknown field."""
    logs = {
        rel[len(DECISION_LOGS) : -3]: text
        for rel, text in files.items()
        if rel.startswith(DECISION_LOGS) and rel.endswith(".md") and "/" not in rel[len(DECISION_LOGS) :]
    }
    lesson_head, lesson_records = lessons(files[LESSONS_FILE])
    gap_head, gap_records, gap_listed = gaps(files[GAPS_FILE], hand)
    backlog_head, backlog_records = backlog(files[BACKLOG_FILE])
    decision_heads, decision_records, decision_listed = build(logs, hand)
    records = [*lesson_records, *decision_records, *gap_records, *backlog_records]
    headers = {
        "docs/lessons/_header.md": lesson_head,
        "docs/known_gaps/_header.md": gap_head,
        "docs/standards_backlog/_header.md": backlog_head,
        **decision_heads,
    }
    unknown = [
        f"unknown: {r.path}: {k}" for r in records if r.family != "decisions" for k, v in r.meta.items() if v == UNKNOWN
    ]
    return Migration(records, headers, [*decision_listed, *gap_listed, *unknown])
