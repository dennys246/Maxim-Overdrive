"""Today's decision logs parsed into decision records (records_layout §8 stage 1), and what a status cell means.

A log is ``docs/design/decisions/<log>.md``: a hand-written head, then one five-column table (Id, Ruling, Who and
date, Owner section, Status). A row whose first cell is a single id (``O57``, ``D12, provisional``) is that id's
record; an id in two logs is one record, cross-listed (``also_in``). A row whose first cell is a range or list
(``D26``-to-``D28``, ``O23, O24, O31``) or no id (``—``, ``ruled 1``) is a record whose id is a slug (§5).

A status cell's relations are moved onto the ruling that holds them (``superseded by O6`` becomes O6's
``supersedes``), so a status is derived, never stored. ``meaning`` reads a cell into what it says, and the converter
refuses to finish unless every derived status means what its original cell meant: a cell it can't derive is a
converter bug, never a listed exception.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field

from records import UNKNOWN, slugify
from records_index import DECISION_HEAD

_ID_CELL = re.compile(r"^((?:[A-Z]+\d*-)?[A-Z]+\d+[a-z]?)(?:,\s*([a-z][a-z -]*)|\s+\(([a-z][a-z -]*)\))?$")
_WHO_DATE = re.compile(r"^(.+), (\d{4}-\d{2}-\d{2})$")
_LEAD = re.compile(r"^\*\*(.+?)\*\*")
_EXTERNAL = re.compile(r"^amended by ([a-z][a-z-]*) ruling (\S+)$")
_RELATION = re.compile(r"^(superseded|amended|confirmed|corrected) by ((?:[A-Z]+\d*-)?[A-Z]+\d+[a-z]?)$")
_ALSO_IN = re.compile(r"^also in `decisions/([a-z0-9_]+)\.md`$")
RELATION_OF = {"superseded": "supersedes", "amended": "amends", "confirmed": "confirms", "corrected": "corrects"}
TABLE_HEAD = DECISION_HEAD.split("\n", 1)[0]  # the table head the generator writes, its one owner


class MigrationError(ValueError):
    """The converter met a source it can't represent faithfully: a bug to fix, never an exception to list."""


@dataclass(frozen=True)
class Row:
    log: str
    position: int
    id_cell: str
    ruling: str
    who_date: str
    owner_section: str
    status: str


@dataclass(frozen=True)
class Meaning:
    """What a status cell says: its base (live, superseded, restates) and each relation it names."""

    base: str
    parts: frozenset[str] = field(default_factory=frozenset)


def split_log(log: str, text: str) -> tuple[str, list[Row]]:
    """A log's head (everything before its table) and its rows, or a MigrationError naming a row it can't split."""
    head, sep, table = text.partition(TABLE_HEAD + "\n")
    if not sep:
        raise MigrationError(f"decisions/{log}.md: no table headed {TABLE_HEAD}")
    lines = table.split("\n")
    if lines[0] != "|---|---|---|---|---|" or lines[-1] != "":
        raise MigrationError(f"decisions/{log}.md: the table's separator or its end is not today's form")
    rows = []
    for position, line in enumerate(lines[1:-1], start=1):
        cells = line[2:-2].split(" | ") if line.startswith("| ") and line.endswith(" |") else []
        if len(cells) != 5:
            raise MigrationError(f"decisions/{log}.md: row {position} is not five cells: {line[:80]}")
        rows.append(Row(log, position, *cells))
    return head, rows


def meaning(cell: str, aliases: Mapping[str, str]) -> Meaning:
    """The meaning of a status cell; ``aliases`` turn a restated name (``world_model §0``) into a repository path."""
    base, parts = "live", set()
    for part in cell.split("; "):
        if part == "live":
            continue
        if part.startswith("restates "):
            target = part.removeprefix("restates ")
            base = f"restates {aliases.get(target, target)}"
        elif part.startswith("superseded by "):
            base = part
        elif _EXTERNAL.match(part) or _RELATION.match(part) or _ALSO_IN.match(part):
            parts.add(part)
        else:
            raise MigrationError(f"a status says {part!r}, which the converter can't read")
    return Meaning(base, frozenset(parts))


def numbered_id(id_cell: str) -> tuple[str, str | None] | None:
    """(id, qualifier) for a cell that is a single id (``D12, provisional``), else None (a slug-id row)."""
    m = _ID_CELL.match(id_cell)
    return (m.group(1), m.group(2) or m.group(3)) if m else None


def who_and_date(cell: str) -> tuple[str, str]:
    """(who, date) from a "Who, date" cell; a date that isn't ISO is ``unknown``, and its cell stays in legacy."""
    m = _WHO_DATE.match(cell)
    if m:
        return m.group(1), m.group(2)
    return cell.split(",", 1)[0], UNKNOWN


def lead_title(ruling: str) -> str | None:
    """A ruling's bold lead sentence, without its closing colon or comma, or None when it has none."""
    m = _LEAD.match(ruling)
    return m.group(1).strip().rstrip(":,;").strip() if m else None


def slug_id(id_cell: str, title: str) -> str:
    """The slug id of a row with no single id: its cell's words (``D26`` to ``D28`` is ``d26-to-d28``), or its
    title's when the cell is empty or a dash."""
    if id_cell in ("—", ""):
        return slugify(title)
    return slugify(id_cell.replace("\u2013", " to "))


def is_restatement(row: Row) -> bool:
    return row.status.startswith("restates ")


def primary(rows: list[Row]) -> Row:
    """The row a cross-listed decision's fields come from: the first log's, unless that row restates another."""
    ordered = sorted(rows, key=lambda r: r.log)
    return next((r for r in ordered if not is_restatement(r)), ordered[0])


def group_rows(rows: list[Row]) -> list[list[Row]]:
    """One group per record: the rows of one numbered id across logs, and each slug-id row alone."""
    by_id: dict[str, list[Row]] = defaultdict(list)
    alone: list[list[Row]] = []
    for row in rows:
        parsed = numbered_id(row.id_cell)
        if parsed is None:
            alone.append([row])
        else:
            by_id[parsed[0]].append(row)
    for ident, group in by_id.items():
        if len({r.log for r in group}) != len(group):
            raise MigrationError(f"decision {ident} has two rows in one log: a duplicate to fix before migrating")
    return [*by_id.values(), *alone]


def relations(rows: list[Row]) -> tuple[dict[str, dict[str, set[str]]], dict[tuple[str, int], list[dict[str, str]]]]:
    """Every relation the status cells state, moved onto the ruling that holds it, and each row's external
    amendments.

    ``O2``'s "superseded by O6" becomes O6's ``supersedes: [O2]``; "amended by docs-contracts ruling 49" stays on
    the ruling it amends, as ``amended_by_external``, keyed here by the row (log, position) that says it."""
    held: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    external: dict[tuple[str, int], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        parsed = numbered_id(row.id_cell)
        for part in row.status.split("; "):
            m, e = _RELATION.match(part), _EXTERNAL.match(part)
            if m and parsed is None:
                raise MigrationError(f"decisions/{row.log}.md row {row.position}: a slug-id row is {part!r}")
            if m and parsed:
                held[m.group(2)][RELATION_OF[m.group(1)]].add(parsed[0])
            elif e:
                path = f"docs/design/reviews/{e.group(1).replace('-', '_')}/rulings.md"
                external[(row.log, row.position)].append({"path": path, "ruling": e.group(2)})
    return held, external
