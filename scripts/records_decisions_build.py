"""Decision records built from today's logs (records_layout §8 stage 1), with the proof that statuses survive.

``build`` turns the logs into one record per decision and a ``_header.md`` per log. Each row's cells that the
fields don't render byte for byte (a slug id's ``D26``-to-``D28``, a non-ISO date, a status worded "restates realtime
decisions 1 to 4", a cross-listed decision's second wording) are kept in its ``legacy`` row, with the row's position.
Every derived status must mean what the original cell meant, or the build fails: a converter bug, never a listed
exception.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from records import DECISION, UNKNOWN, Record, file_name, plain, read_record, record_text, slugify
from records_decisions import (
    MigrationError,
    Row,
    group_rows,
    is_restatement,
    lead_title,
    meaning,
    numbered_id,
    primary,
    relations,
    slug_id,
    split_log,
    who_and_date,
)
from records_index import Relations, decision_row

ROOT = "docs/design/decisions/"
CELLS = ("id_cell", "ruling", "who_date", "owner_section", "status")


@dataclass(frozen=True)
class Hand:
    """What the migration is given by hand, each listed in its commit (§4, §8): titles for rows and gaps with no
    bold lead, the repository paths that restated names stand for, and Known gaps' kinds and steps."""

    titles: Mapping[str, str]
    aliases: Mapping[str, str]
    kinds: Mapping[str, str]
    closes_at: Mapping[str, str]


def row_keys(rows: list[Row]) -> dict[tuple[str, int], str]:
    """Each row's hand key, ``<log>:<id cell>``, with ``:<n>`` from the second row of one id cell in one log."""
    seen: dict[str, int] = {}
    out = {}
    for row in rows:
        key = f"{row.log}:{row.id_cell}"
        seen[key] = seen.get(key, 0) + 1
        out[(row.log, row.position)] = key if seen[key] == 1 else f"{key}:{seen[key]}"
    return out


def _title(row: Row, keys: Mapping[tuple[str, int], str], hand: Hand, listed: list[str]) -> str:
    lead = lead_title(row.ruling)
    if lead:
        return lead
    key = keys[(row.log, row.position)]
    if key not in hand.titles:
        raise MigrationError(f"decision row {key} has no bold lead and no hand title")
    listed.append(f"hand title: decision {key}: {hand.titles[key]}")
    return hand.titles[key]


Held = Mapping[str, Mapping[str, set[str]]]
External = Mapping[tuple[str, int], list[dict[str, str]]]


def _raw(group: list[Row], held: Held, external: External, title: str, hand: Hand) -> dict[str, object]:
    """The record's front matter, before legacy: every field from the primary row and the relations held by it."""
    source = primary(group)
    parsed = numbered_id(source.id_cell)
    ident, qualifier = parsed if parsed else (slug_id(source.id_cell, title), None)
    who, date = who_and_date(source.who_date)
    restated = meaning(source.status, hand.aliases).base
    if restated.startswith("restates ") and restated.removeprefix("restates ") not in hand.aliases.values():
        raise MigrationError(f"decisions/{source.log}.md: {restated!r} names no path the hand aliases give")
    mine = held.get(str(ident), {})
    raw: dict[str, object] = {
        "version": 1, "id": ident, "slug": slugify_for(ident, title), "title": title, "date": date, "who": who,
        "owner_section": source.owner_section or UNKNOWN,
        **{rel: sorted(mine.get(rel, ())) for rel in ("supersedes", "amends", "confirms", "corrects")},
        "amended_by_external": _externals(group, external),
        "also_in": sorted({r.log for r in group} - {sorted(r.log for r in group)[0]}),
        "restates": [restated.removeprefix("restates ")] if restated.startswith("restates ") else [],
    }  # fmt: skip
    if qualifier:
        raw["qualifier"] = qualifier
    return raw


def slugify_for(ident: object, title: str) -> str:
    """A numbered record's slug is its title's; a slug id is its own slug."""
    return str(ident) if not numbered_id(str(ident)) else slugify(title)


def _externals(group: list[Row], external: Mapping[tuple[str, int], list[dict[str, str]]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in sorted(group, key=lambda r: r.log):
        out += [e for e in external.get((row.log, row.position), []) if e not in out]
    return out


def _record(raw: Mapping[str, object], body: str, directory: str) -> Record:
    meta = DECISION.read(dict(raw), "a migrated decision")
    rel = f"{ROOT}{directory}/{file_name('decisions', meta['id'], str(meta['slug']))}"
    return Record("decisions", rel, meta, body)


def build(logs: Mapping[str, str], hand: Hand) -> tuple[dict[str, str], list[Record], list[str]]:
    """(each log's ``_header.md`` text by path, the decision records, the listing for the commit)."""
    heads, rows = {}, []
    for log in sorted(logs):
        head, found = split_log(log, logs[log])
        heads[f"{ROOT}{log}/_header.md"] = head
        rows += found
    keys = row_keys(rows)
    held, external = relations(rows)
    listed: list[str] = []
    groups = group_rows(rows)
    bare = []
    for group in groups:
        source = primary(group)
        raw = _raw(group, held, external, _title(source, keys, hand, listed), hand)
        bare.append(_record(raw, source.ruling + "\n", sorted(r.log for r in group)[0]))
    records = _with_legacy(groups, bare, hand)
    listed += _unknowns(records)
    listed += [f"hand alias: {name} restates {path}" for name, path in sorted(hand.aliases.items())]
    return heads, records, listed


def _with_legacy(groups: list[list[Row]], bare: list[Record], hand: Hand) -> list[Record]:
    """Each record with a legacy row per log it is listed in: its position, and each cell its fields don't render
    byte for byte. Then the proof: each derived status means what its original cell meant."""
    rel = Relations.of(bare)
    out = []
    for group, record in zip(groups, bare, strict=True):
        legacy_rows = []
        for row in sorted(group, key=lambda r: r.log):
            rendered = decision_row(record, row.log, rel)[2:-3].split(" | ")
            original = (row.id_cell, row.ruling, row.who_date, row.owner_section, row.status)
            _same_meaning(row, rendered[4], hand, restates_ok=is_restatement(row) and row is not primary(group))
            legacy = {"log": row.log, "position": row.position}
            legacy |= {c: o for c, o, r in zip(CELLS, original, rendered, strict=True) if o != r}
            legacy_rows.append(legacy)
        raw = {"version": 1, **_plain(record.meta), "legacy": {"rows": legacy_rows}}
        out.append(
            read_record(
                record.path, record_text(Record("decisions", record.path, DECISION.read(raw, record.path), record.body))
            )
        )
    return out


def _plain(meta: Mapping[str, object]) -> dict[str, object]:
    return {k: plain(v) for k, v in meta.items() if v is not None and k != "legacy"}


def _same_meaning(row: Row, derived: str, hand: Hand, *, restates_ok: bool) -> None:
    was, now = meaning(row.status, hand.aliases), meaning(derived, hand.aliases)
    if was == now or (restates_ok and was.parts == now.parts):
        return
    raise MigrationError(
        f"decisions/{row.log}.md row {row.position} ({row.id_cell}): status {row.status!r} derives as {derived!r}"
    )


def _unknowns(records: list[Record]) -> list[str]:
    return [f"unknown: {r.path}: {k}" for r in records for k, v in r.meta.items() if v == UNKNOWN]
