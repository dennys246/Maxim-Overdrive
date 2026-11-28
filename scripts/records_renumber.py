"""``records.py renumber``: the branch merged second moves its own records off a colliding id (records_layout §5).

One mapping is applied at once (``O12=O14 O13=O15``), so shifting a range can't collide with itself. The branch's
records with an old id are renamed and their front matter rewritten. Citations are rewritten only in lines the branch
added or changed against the base, the merge base with a freshly fetched ``origin/main`` (RL12); every citation of an
old id elsewhere is listed, not rewritten, because it names the other branch's record. A changed line whose hunk
replaced a line that already cited the old id may hold both branches' citations (a hand-resolved merge), so it is
listed too. Nothing is rewritten in a file a ``freeze.sha256`` lists or under ``docs/maxim_upstream/``, and a decision
or ``B`` id never under ``docs/design/reviews/``, whose finding ids share the shapes.

``--merged <PR>`` is for a duplicate both PRs merged: it renames the record that PR's merge commit added, and treats
the lines that merge added against its first parent as the branch's own, matched by their text.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from lint_ids import CITATION, frozen_files
from records import (
    BY_NAME,
    Record,
    family_of,
    file_name,
    load_records,
    read_meta,
    read_record,
    record_text,
    split_record,
)
from records_git import Git, Hunk
from records_index import MARKER

UPSTREAM = "docs/maxim_upstream/"
REVIEWS = "docs/design/reviews/"
_NUMBERED = re.compile(r"(?:[A-Z]+\d*-)?[A-Z]+\d+[a-z]?")


class RenumberError(ValueError):
    """A renumber that can't be done as asked; nothing has been written."""


def family_of_id(ident: str) -> str:
    """The family an id to renumber belongs to: a lesson number, a ``B`` row, or a numbered decision id."""
    if ident.isdigit():
        return "lessons"
    if re.fullmatch(r"B[1-9]\d*", ident):
        return "backlog"
    if _NUMBERED.fullmatch(ident):
        return "decisions"
    raise RenumberError(f"{ident} is not a lesson, backlog or numbered decision id; a slug id is never renumbered")


def parse_mapping(pairs: list[str]) -> dict[str, str]:
    """``old=new`` pairs as one mapping, each within one family, no old id twice and no old id as another's new."""
    mapping: dict[str, str] = {}
    for pair in pairs:
        old, sep, new = pair.partition("=")
        if not sep or not old or not new or old == new:
            raise RenumberError(f"{pair!r} is not old=new with two different ids")
        if family_of_id(old) != family_of_id(new):
            raise RenumberError(f"{old} and {new} are ids of different families")
        if old in mapping:
            raise RenumberError(f"{old} is mapped twice")
        if new in mapping.values():
            raise RenumberError(f"two ids are mapped to {new}")
        mapping[old] = new
    return mapping


@dataclass
class Report:
    renamed: list[tuple[str, str]] = field(default_factory=list)
    rewritten: list[str] = field(default_factory=list)
    listed: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Own:
    """Which lines are the branch's own: by number in the working tree, or by text for ``--merged``."""

    numbers: Mapping[str, frozenset[int]]
    texts: Mapping[str, frozenset[str]]
    unsafe: Mapping[str, frozenset[int]]  # changed lines whose hunk replaced a line that cited an old id
    unsafe_texts: Mapping[str, frozenset[str]] = field(default_factory=dict)  # the same, by text, for --merged

    def holds(self, rel: str, number: int, text: str) -> bool:
        if number in self.unsafe.get(rel, frozenset()) or text in self.unsafe_texts.get(rel, frozenset()):
            return False
        return number in self.numbers.get(rel, frozenset()) or text in self.texts.get(rel, frozenset())


def _cites(text: str, mapping: Mapping[str, str], rel: str) -> bool:
    return rewrite_line(text, mapping, rel) != text


def rewrite_line(text: str, mapping: Mapping[str, str], rel: str) -> str:
    """The line with every citation of an old id replaced by its new one, at once."""
    lessons = {o: n for o, n in mapping.items() if family_of_id(o) == "lessons"}
    tokens = {o: n for o, n in mapping.items() if family_of_id(o) != "lessons"}
    if tokens and not rel.startswith(REVIEWS):
        alternation = "|".join(re.escape(o) for o in sorted(tokens, key=len, reverse=True))
        text = re.sub(rf"(?<![\w-])({alternation})(?![\w-])", lambda m: tokens[m.group(1)], text)
    lesson_scope = (rel.startswith("docs/") and rel.endswith(".md")) or (
        rel.startswith("tests/") and rel.endswith(".py")
    )
    if lessons and lesson_scope:
        text = CITATION.sub(lambda m: re.sub(r"\d+", lambda d: lessons.get(d.group(0), d.group(0)), m.group(0)), text)
    return text


def own_lines(hunks: Mapping[str, list[Hunk]], mapping: Mapping[str, str]) -> Own:
    numbers = {rel: frozenset(n for h in hs for n in h.added) for rel, hs in hunks.items()}
    unsafe = {
        rel: frozenset(n for h in hs if any(_cites(r, mapping, rel) for r in h.removed) for n in h.added)
        for rel, hs in hunks.items()
    }
    return Own(numbers, {}, unsafe)


def _renamed(record: Record, text: str, new: str) -> Record:
    """The record moved to ``new``: its front matter as the citations' rewrite left it, with its id set to ``new``."""
    meta = {
        **read_meta(BY_NAME[record.family], record.path, text),
        "id": int(new) if record.family == "lessons" else new,
    }
    path = str(Path(record.path).parent / file_name(record.family, meta["id"], record.slug))
    return read_record(path, record_text(Record(record.family, path, meta, split_record(record.path, text)[1])))


def rename_records(records: list[Record], texts: Mapping[str, str], mapping: Mapping[str, str], own: set[str],
                   report: Report) -> dict[str, str | None]:  # fmt: skip
    """The writes that rename the branch's own records with an old id: new path to text, old path to None.
    ``texts`` are the record files after the citations' rewrite, which already moved their relations."""
    writes: dict[str, str | None] = {}
    taken = {r.path for r in records}
    for record in records:
        if record.id in mapping and record.path in own and family_of_id(record.id) == record.family:
            moved = _renamed(record, texts[record.path], mapping[record.id])
            if moved.path in taken:
                raise RenumberError(f"{moved.path} is another record already: choose a free id for {record.id}")
            writes[record.path] = None
            writes[moved.path] = record_text(moved)
            report.renamed.append((record.path, moved.path))
    mine = {r.id for r in records if r.path in own}
    report.listed += [
        f"{old}: no record of this branch has it, so none was renamed" for old in sorted(set(mapping) - mine)
    ]
    return writes


def rewrite_citations(files: Mapping[str, str], mapping: Mapping[str, str], own: Own, report: Report) -> dict[str, str]:
    """Each file with its own lines' citations rewritten; every other citation of an old id is listed."""
    skip = frozen_files(dict(files))
    writes = {}
    for rel in sorted(files):
        if rel in skip or rel.startswith(UPSTREAM) or files[rel].startswith(MARKER):
            continue  # a generated file is rebuilt from the renamed records by `index`, never rewritten here
        lines = files[rel].split("\n")
        changed = False
        for i, line in enumerate(lines):
            new = rewrite_line(line, mapping, rel)
            if new == line:
                continue
            if own.holds(rel, i + 1, line):
                lines[i], changed = new, True
                report.rewritten.append(f"{rel}:{i + 1}")
            else:
                report.listed.append(f"{rel}:{i + 1}: {line.strip()[:120]}")
        if changed:
            writes[rel] = "\n".join(lines)
    return writes


def plan(files: Mapping[str, str], base_paths: set[str], hunks: Mapping[str, list[Hunk]], mapping: Mapping[str, str],
         *, own: Own | None = None) -> tuple[dict[str, str | None], Report]:  # fmt: skip
    """Every write a renumber makes, and its report: records the base doesn't hold are the branch's own. The
    citations are rewritten first, all at once; then each own record takes its new id from the mapping."""
    report = Report()
    records, _ = load_records(files)
    own_records = {r.path for r in records if r.path not in base_paths}
    lines = own if own is not None else own_lines(hunks, mapping)
    rewritten = rewrite_citations(files, mapping, lines, report)
    texts = {**files, **rewritten}
    renames = rename_records(records, texts, mapping, own_records, report)
    return {**rewritten, **renames}, report


def merged_commit(git: Git, pr: str) -> str:
    """The merge commit of PR ``pr`` on ``origin/main``, or a RenumberError."""
    found = git.run("log", "--merges", "--format=%H", f"--grep=^Merge pull request #{pr} ", "origin/main").split()
    if len(found) != 1:
        raise RenumberError(f"origin/main has {len(found)} merge commits for PR #{pr}; expected one")
    return found[0]


def merged_own(git: Git, merge: str, mapping: Mapping[str, str]) -> tuple[set[str], Own]:
    """For ``--merged``: the record paths that merge added, and its added lines by text (main may have moved since,
    so line numbers would drift)."""
    hunks = git.hunks(f"{merge}^1", merge)
    texts, unsafe = {}, {}
    for rel, hs in hunks.items():
        lines = git.run("show", f"{merge}:{rel}").split("\n")
        texts[rel] = frozenset(lines[n - 1] for h in hs for n in h.added if n <= len(lines))
        replaced = [h for h in hs if any(_cites(r, mapping, rel) for r in h.removed)]  # a hand-resolved line
        unsafe[rel] = frozenset(lines[n - 1] for h in replaced for n in h.added if n <= len(lines))
    before = set(filter(None, git.run("ls-tree", "-r", "-z", "--name-only", f"{merge}^1").split("\0")))
    added = {rel for rel in hunks if rel not in before and family_of(rel) is not None}
    return added, Own({}, texts, {}, unsafe)
