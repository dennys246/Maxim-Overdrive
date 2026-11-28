"""The shared records, one file per record (``docs/design/records_layout.md``), and the command that keeps them.

This module owns the record format (§4): ``read_record`` is its one reader, and ``record_text`` its one writer.
A record file begins with a line that is exactly ``---``; its front matter ends at the next such line, and the rest
is the body, which may hold ``---`` lines of its own. The front matter is parsed by the loaders' strict YAML grammar
(``simcore.adapters.loaders.read_yaml_text``) and held to its family's ``Format`` (``simcore.core.schema``): unknown
keys, unknown versions, unquoted dates and unbuildable values are refused, by name.

Four families (§2, RL3), each in its own directory (§3):

- lessons, ``docs/lessons/<n>-<slug>.md``;
- decisions, ``docs/design/decisions/<design>/<id>-<slug>.md`` (``<slug>.md`` when the id is a slug, §5);
- Known gaps, ``docs/known_gaps/<slug>.md``, whose id is its slug;
- standards backlog rows, ``docs/standards_backlog/<id>-<slug>.md``.

Each directory also holds ``_header.md``, the hand-written head of its generated file (§6), which is not a record.

Run: ``python scripts/records.py index`` (regenerate every generated file), ``renumber <old>=<new> ...`` (§5),
``migrate`` and ``migrate-branch <branch>`` (§8).
"""

from __future__ import annotations

import datetime
import os
import re
import sys
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import yaml

from simcore.adapters.loaders import read_yaml_text
from simcore.core.checks import shown
from simcore.core.converters import Choice, Flag
from simcore.core.refusals import RefusalCode, Refused
from simcore.core.schema import Bad, Converter, Field, Format, ListOf, Nested, Schema, Whole

UNKNOWN = "unknown"  # what the migration writes where a source lacks a required value (§4)
SLUG_CHARS = 60
LINE_CHARS = 400  # a front-matter line: a title, a who, a gate's test id
_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_DAY = re.compile(r"\d{4}-\d{2}-\d{2}")
_NUMBERED_ID = re.compile(r"((?:[A-Z]+\d*-)?[A-Z]+)(\d+)([a-z]?)")
_BACKLOG_ID = re.compile(r"B[1-9]\d*")
FENCE = "---"
HEADER = "_header.md"

# The lessons file's section headings today, plus the section for lessons beyond Maxim (RL7), in the file's order.
LESSON_SECTIONS = (
    "World and physics",
    "Perception and the body",
    "Acting, refusals and learning",
    "Time",
    "Working with Maxim",
    "Game and general engineering",
)
GAP_KINDS = ("physics", "performance", "trust boundary")  # RL6
QUALIFIERS = ("provisional", "re-ruled")  # a ruling's standing beside its id today (§4): D12, PH2-S2
BACKLOG_STATUSES = ("open", "done in part", "done")


# -- converters: free text the schema module's name rules would refuse (titles hold code spans and punctuation) ------


# YAML's line breaks (a title "a\x85b" reads back as "a b"), NUL, and the table cell separator: a front-matter line
# is rendered into a Markdown table cell, so a | would split the cell.
_NOT_IN_A_LINE = "\n\r\x00\x85\u2028\u2029|"


@dataclass(frozen=True)
class Line:
    """One line of text: a str of 1 to ``max_chars`` characters, no line break, no outer spaces. ``allow_empty``
    is for a legacy cell, which keeps a source's empty cell as it was."""

    max_chars: int = LINE_CHARS
    allow_empty: bool = False

    def convert(self, value: object, what: str) -> str:
        shortest = 0 if self.allow_empty else 1
        ok = type(value) is str and shortest <= len(value) <= self.max_chars and value == value.strip()
        if not ok or any(c in str(value) for c in _NOT_IN_A_LINE):
            message = f"{what} must be one line of 1 to {self.max_chars} characters, no |, got {shown(value)}"
            raise Refused(message, code=RefusalCode.BAD_TEXT)
        return str(value)

    @property
    def bad(self) -> Bad:
        long = "x" * (self.max_chars + 1)
        empty = () if self.allow_empty else ("",)
        lines = ("a\nb", "a\x00b", "a\x85b", "a\u2028b", "a\u2029b", "a|b")
        return tuple((v, RefusalCode.BAD_TEXT) for v in (7, *empty, " x", *lines, long, ["x"]))


@dataclass(frozen=True)
class Slug:
    """Lowercase ASCII words joined by hyphens, at most ``SLUG_CHARS`` characters (§3)."""

    def convert(self, value: object, what: str) -> str:
        if type(value) is not str or len(value) > SLUG_CHARS or not _SLUG.fullmatch(value):
            message = (
                f"{what} must be lowercase ASCII words joined by hyphens, at most {SLUG_CHARS}, got {shown(value)}"
            )
            raise Refused(message, code=RefusalCode.BAD_NAME)
        return value

    @property
    def bad(self) -> Bad:
        return tuple((v, RefusalCode.BAD_NAME) for v in (7, "", "A-b", "a--b", "-a", "a_b", "é", "a" * 61))


@dataclass(frozen=True)
class Day:
    """A date written as the quoted string ``"YYYY-MM-DD"``; an unquoted date loads as a date object and is refused."""

    def convert(self, value: object, what: str) -> str:
        if type(value) is not str or not _DAY.fullmatch(value):
            message = f'{what} must be a quoted "YYYY-MM-DD" date, got {shown(value)}'
            raise Refused(message, code=RefusalCode.BAD_SHAPE)
        try:
            datetime.date.fromisoformat(value)
        except ValueError:
            raise Refused(f"{what}: {value} is not a calendar date", code=RefusalCode.BAD_SHAPE) from None
        return value

    @property
    def bad(self) -> Bad:
        dates = (7, "2026-11-1", "2026-02-30", datetime.date(2026, 11, 24), "2026-11-24x")
        return tuple((v, RefusalCode.BAD_SHAPE) for v in dates)


@dataclass(frozen=True)
class RecordId:
    """A family's id: a lesson number, a ``B`` number, a numbered decision id (``O7a``, ``PH2-S2``) or a slug."""

    family: str

    def convert(self, value: object, what: str) -> object:
        if self.family == "lessons":
            return Whole(1, 10**6).convert(value, what)
        if type(value) is str and _ID_SHAPES[self.family](value):
            return value
        raise Refused(f"{what} is not a {self.family} id, got {shown(value)}", code=RefusalCode.BAD_NAME)

    @property
    def bad(self) -> Bad:
        if self.family == "lessons":
            return Whole(1, 10**6).bad
        wrong = {"backlog": ("b1", "B0", "B1a"), "decisions": ("A_1", "O-1", "Ab"), "gaps": ("A-gap", "a_gap", "O1")}
        return tuple((v, RefusalCode.BAD_NAME) for v in (7, "", *wrong[self.family]))


@dataclass(frozen=True)
class LogName:
    """A decision log's name, as its file is named under ``docs/design/decisions/`` (``npcs_and_sem``)."""

    def convert(self, value: object, what: str) -> str:
        if type(value) is not str or len(value) > SLUG_CHARS or not _LOG.fullmatch(value):
            raise Refused(f"{what} must be a decision log's name, got {shown(value)}", code=RefusalCode.BAD_NAME)
        return value

    @property
    def bad(self) -> Bad:
        return tuple((v, RefusalCode.BAD_NAME) for v in (7, "", "Npcs", "a/b", "a.md"))


_LOG = re.compile(r"[a-z0-9]+(?:_[a-z0-9]+)*")
_ID_SHAPES = {
    "decisions": lambda v: bool(_NUMBERED_ID.fullmatch(v) or (len(v) <= SLUG_CHARS and _SLUG.fullmatch(v))),
    "gaps": lambda v: bool(len(v) <= SLUG_CHARS and _SLUG.fullmatch(v)),
    "backlog": lambda v: bool(_BACKLOG_ID.fullmatch(v)),
}


@dataclass(frozen=True)
class OrUnknown:
    """``inner``'s value, or the word ``unknown`` the migration writes where a source lacks the value (§4)."""

    inner: Converter

    def convert(self, value: object, what: str) -> object:
        return UNKNOWN if value == UNKNOWN and type(value) is str else self.inner.convert(value, what)

    @property
    def bad(self) -> Bad:
        return self.inner.bad


@dataclass(frozen=True)
class Strings:
    """A list of at most ``max_items`` values, each read by ``item``, counted before any is read."""

    item: Converter
    max_items: int = 64

    def convert(self, value: object, what: str) -> tuple[object, ...]:
        if not isinstance(value, list):
            raise Refused(f"{what} must be a list, got {type(value).__name__}", code=RefusalCode.BAD_SHAPE)
        if len(value) > self.max_items:
            raise Refused(f"{what} holds at most {self.max_items} items", code=RefusalCode.OVER_BUDGET)
        return tuple(self.item.convert(v, f"{what}[{i}]") for i, v in enumerate(value))

    @property
    def bad(self) -> Bad:
        return (({}, RefusalCode.BAD_SHAPE), ("x", RefusalCode.BAD_SHAPE), ([7], self.item.bad[0][1]))


# -- the four formats (§4), each at version 1 ----------------------------------------------------------------------

_LINE = Line()
RELATIONS = ("supersedes", "amends", "confirms", "corrects")  # held by the later ruling (§4)
_AMENDED = ListOf(Nested(Schema((Field("date", Day()), Field("why", _LINE)))), max_items=256)
_EXTERNAL = ListOf(Nested(Schema((Field("path", _LINE), Field("ruling", _LINE)))), max_items=16)
_LOG_ROW = Schema(
    (
        Field("log", LogName()),
        Field("position", Whole(1, 10**4)),
        *(Field(c, Line(allow_empty=True), required=False) for c in ("id_cell", "who_date", "owner_section", "status")),
        Field("ruling", Line(max_chars=8000, allow_empty=True), required=False),
    )
)


# TEMPORARY(phase1/records-build): each format's legacy field holds today's presentation facts for the migration's
# byte-for-byte proof (RL11); R3's presentation commit removes it from every record and every format (a version bump).
def _common(family: str, legacy: Schema) -> tuple[Field, ...]:
    return (
        Field("id", RecordId(family)),
        Field("slug", Slug()),
        Field("title", _LINE),
        Field("date", OrUnknown(Day())),
        Field("legacy", Nested(legacy), required=False),
    )


LESSON = Format(
    "lesson",
    1,
    Schema(
        (
            *_common("lessons", Schema((Field("heading_tail", _LINE, required=False),))),
            Field("section", OrUnknown(Choice(LESSON_SECTIONS))),
            Field("amended", _AMENDED),
        )
    ),
)
DECISION = Format(
    "decision",
    1,
    Schema(
        (
            *_common("decisions", Schema((Field("rows", ListOf(Nested(_LOG_ROW), max_items=16)),))),
            Field("who", OrUnknown(_LINE)),
            Field("owner_section", OrUnknown(_LINE)),
            *(Field(rel, Strings(RecordId("decisions")), required=False, default=()) for rel in RELATIONS),
            Field("amended_by_external", _EXTERNAL, required=False, default=()),
            Field("qualifier", Choice(QUALIFIERS), required=False),
            Field("also_in", Strings(LogName(), max_items=16), required=False, default=()),
            Field("restates", Strings(_LINE), required=False, default=()),
        )
    ),
)
GAP = Format(
    "known gap",
    1,
    Schema(
        (
            *_common("gaps", Schema((Field("position", Whole(1, 10**4)), Field("group", _LINE)))),
            Field("kind", OrUnknown(Choice(GAP_KINDS))),
            Field("gate", OrUnknown(_LINE)),  # a test id, or "none: <reason>"
            Field("closes_at", OrUnknown(_LINE)),  # a named step, or "unscheduled: <reason>"
        )
    ),
)
BACKLOG = Format(
    "backlog row",
    1,
    Schema(
        (
            *_common("backlog", Schema((Field("three_cells", Flag()),))),
            Field("rule", OrUnknown(_LINE)),
            Field("lands_with", OrUnknown(_LINE)),
            Field("status", OrUnknown(Choice(BACKLOG_STATUSES))),
            Field("done_in", OrUnknown(_LINE), required=False),
        )
    ),
)


@dataclass(frozen=True)
class Family:
    """A record family: where its records live, its format, and its per-record word budget (§6, RL4)."""

    name: str
    root: str
    format: Format
    budget_words: int
    per_log: bool = False  # decisions: one directory per log under the root


FAMILIES = (
    Family("lessons", "docs/lessons/", LESSON, 500),
    Family("decisions", "docs/design/decisions/", DECISION, 400, per_log=True),
    Family("gaps", "docs/known_gaps/", GAP, 400),
    Family("backlog", "docs/standards_backlog/", BACKLOG, 600),
)
BY_NAME = {f.name: f for f in FAMILIES}


@dataclass(frozen=True)
class Record:
    """One record: its family, its repository path, its front matter as its format read it, and its body."""

    family: str
    path: str
    meta: Mapping[str, object]
    body: str

    @property
    def id(self) -> str:
        return str(self.meta["id"])

    @property
    def slug(self) -> str:
        return str(self.meta["slug"])

    @property
    def title(self) -> str:
        return str(self.meta["title"])

    def strings(self, key: str) -> tuple[str, ...]:
        """A list field's values as text (a relation's ids, ``also_in``, ``restates``)."""
        value = self.meta[key]
        return tuple(str(v) for v in value) if isinstance(value, tuple) else ()

    def maps(self, key: str) -> tuple[Mapping[str, object], ...]:
        """A list-of-mappings field's entries (``amended``, ``amended_by_external``)."""
        value = self.meta[key]
        return tuple(v for v in value if isinstance(v, Mapping)) if isinstance(value, tuple) else ()

    @property
    def legacy(self) -> Mapping[str, object]:
        """The record's ``legacy`` fields, empty when it holds none."""
        value = self.meta["legacy"]
        return value if isinstance(value, Mapping) else {}

    @property
    def log(self) -> str:
        """A decision's log, the directory that holds it; empty for the other families."""
        return Path(self.path).parent.name if BY_NAME[self.family].per_log else ""


def family_of(rel: str) -> Family | None:
    """The family a repository path is a record of, or None (a generated file, a ``_header.md``, anything else)."""
    for family in FAMILIES:
        if not rel.startswith(family.root) or not rel.endswith(".md"):
            continue
        parts = rel[len(family.root) :].split("/")
        if len(parts) == (2 if family.per_log else 1) and parts[-1] != HEADER:
            return family
    return None


def file_name(family: str, ident: object, slug: str) -> str:
    """The file name a record with this id and slug must have (§3): a slug id names the file alone."""
    return f"{slug}.md" if str(ident) == slug else f"{ident}-{slug}.md"


def split_record(rel: str, text: str) -> tuple[str, str]:
    """(front matter, body): the front matter is between the first line, exactly ``---``, and the next such line."""
    lines = text.split("\n")
    if lines[0] != FENCE:
        raise Refused(f"{rel}: a record begins with a line that is exactly {FENCE}", code=RefusalCode.BAD_SHAPE)
    end = next((i for i in range(1, len(lines)) if lines[i] == FENCE), None)
    if end is None:
        raise Refused(f"{rel}: the front matter never ends (no second {FENCE} line)", code=RefusalCode.BAD_SHAPE)
    return "\n".join(lines[1:end]), "\n".join(lines[end + 1 :])


def read_meta(family: Family, rel: str, text: str) -> Mapping[str, object]:
    """A record file's front matter, held to its family's format; the file name is not judged here."""
    front, _ = split_record(rel, text)
    return family.format.read(read_yaml_text(front, rel), rel)


def read_record(rel: str, text: str) -> Record:
    """The record in ``text``, read from repository path ``rel``, or a Refused that names the file and the fault.

    The family comes from the path; the front matter is held to the family's format; the file name must equal the
    one its ``id`` and ``slug`` give, and a Known gap's id must be its slug."""
    family = family_of(rel)
    if family is None:
        raise Refused(f"{rel}: not in a record directory (records_layout §3)", code=RefusalCode.BAD_NAME)
    meta, body = read_meta(family, rel, text), split_record(rel, text)[1]
    if family.name == "gaps" and meta["id"] != meta["slug"]:
        raise Refused(f"{rel}: a Known gap's id is its slug", code=RefusalCode.BAD_NAME)
    want = file_name(family.name, meta["id"], str(meta["slug"]))
    if Path(rel).name != want:
        raise Refused(f"{rel}: its id and slug name the file {want}", code=RefusalCode.BAD_NAME)
    return Record(family.name, rel, meta, body)


def plain(value: object) -> object:
    """A read value as YAML can dump it: mappings to dicts without their absent (None) optional keys, tuples to
    lists."""
    if isinstance(value, Mapping):
        return {k: plain(v) for k, v in value.items() if v is not None}
    if isinstance(value, tuple | list):
        return [plain(v) for v in value]
    return value


def record_text(record: Record) -> str:
    """The file text of a record, the inverse of ``read_record``: fields in the format's order, an optional field
    left out when it holds its default, so a record reads back equal."""
    fields = BY_NAME[record.family].format.schema.fields
    front: dict[str, object] = {"version": BY_NAME[record.family].format.version}
    front |= {f.name: plain(record.meta[f.name]) for f in fields if f.required or record.meta[f.name] != f.default}
    dumped = yaml.safe_dump(front, sort_keys=False, allow_unicode=True, width=10**6, default_flow_style=False)
    return f"{FENCE}\n{dumped}{FENCE}\n{record.body}"


def slugify(title: str) -> str:
    """A slug from a title: lowercase ASCII words joined by hyphens, cut at a word to at most ``SLUG_CHARS``."""
    ascii_text = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode().lower()
    words = re.findall(r"[a-z0-9]+", ascii_text)
    out = ""
    for word in words:
        joined = f"{out}-{word}" if out else word
        if len(joined) > SLUG_CHARS:
            break
        out = joined
    if not out:
        raise Refused(f"no slug can be made from {shown(title)}: give one by hand", code=RefusalCode.BAD_NAME)
    return out


def id_key(ident: object) -> tuple[int, str, int, str]:
    """Id order (§5): by prefix, then number, then letter suffix; slug ids after the numbered ones, by slug."""
    if isinstance(ident, int) or str(ident).isdigit():  # a lesson's number, as an int or as Record.id's text
        return (0, "", int(str(ident)), "")
    m = _NUMBERED_ID.fullmatch(str(ident))
    return (0, m.group(1), int(m.group(2)), m.group(3)) if m else (1, str(ident), 0, "")


def load_records(files: Mapping[str, str]) -> tuple[list[Record], list[str]]:
    """Every record among ``files`` (repository path to text), and a finding for each one the reader refuses."""
    records: list[Record] = []
    problems: list[str] = []
    for rel in sorted(files):
        if family_of(rel) is None:
            continue
        try:
            records.append(read_record(rel, files[rel]))
        except Refused as exc:
            problems.append(f"{exc} (records_layout §4)")
    return records, problems


_DONE = re.compile(r"^\*\*(done in part|done)\*\*(.*)$", re.S)


def stated_status(check: str, lands_with: str | None) -> tuple[str, str | None]:
    """A backlog row's status as its prose states it, and where it was done, the one reading of that prose (§4,
    "One owner per fact"): the converter takes the field from it and lint_records holds the field to it.

    A cell (Lands with, then the check) opening with a bold **done in part** is done in part; with a bold **done**
    that is limited to a scope ("**done** for enumerations"), done in part too; with a bare bold **done**, done. Where
    is the first parenthesis after the mark, or the Lands-with cell when the mark opens the check. A Lands-with cell
    that opens with "open" is open. Anything else states nothing: ``unknown``."""
    for cell in (lands_with or "", check):
        m = _DONE.match(cell)
        if m is None:
            continue
        rest = m.group(2)
        status = "done in part" if m.group(1) == "done in part" or rest.startswith(" for ") else "done"
        where = re.match(r"[^(]*\(([^)]+)\)", rest)
        return status, where.group(1) if where else (lands_with if cell is check else None)
    if lands_with is not None and re.match(r"open\b", lands_with):
        return "open", None
    return UNKNOWN, None


def words(text: str) -> int:
    return len(text.split())


if __name__ == "__main__":
    import records_cli  # the commands import this module, so they load once it has

    # the caller's directory and environment: the commands work on the repository they are run in
    sys.exit(records_cli.main(sys.argv[1:], cwd=Path.cwd(), env=os.environ))
