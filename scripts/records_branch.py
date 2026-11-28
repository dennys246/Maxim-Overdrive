"""``records.py migrate`` and ``migrate-branch`` (records_layout §8).

``migrate`` runs stage 1 on the working tree: today's four files become records and ``_header.md`` files, and the
generated files are written in today's form, each equal to its original apart from the marker line.

``migrate-branch <branch>`` is for a branch that edited the old files after the migration landed. It reads the
branch's own commits' diff to the four old files against the base (the merge base with a freshly fetched
``origin/main``), so it works before the branch merges ``main`` and after a merge that went through cleanly. Both
sides of that diff are parsed by the converter, and each difference is mapped onto ``origin/main``'s records:

- an added lesson, decision row, gap or backlog row becomes a new record (``unknown`` where its source lacks a value,
  which the lint refuses in a new record, so the session fills it in before committing);
- an edit of an existing entry becomes a change §4 allows (a lesson body with an ``amended`` entry, a backlog
  status, a gap's body), and any other edit is refused by name; a deleted gap is a deleted record.

It writes ``origin/main``'s records with those changes, and the regenerated files, into the branch's worktree. It
commits nothing.
"""

from __future__ import annotations

import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from records import BY_NAME, Record, load_records, read_record, record_text
from records_decisions import MigrationError, split_log
from records_decisions_build import Hand, build
from records_git import Git
from records_index import BACKLOG_FILE, GAPS_FILE, LESSONS_FILE, MARKER, generate, headers_of
from records_migrate import DECISION_LOGS, backlog, gaps, lessons, migrate, read_hand
from records_tree import ROOTS, TODAY, tree_files, write

from simcore.adapters.loaders import read_yaml


def _hand(path: Path) -> Hand:
    return read_hand(read_yaml(path))


def old_files(files: Mapping[str, str]) -> dict[str, str]:
    """The four old files among ``files``, each without the marker line a generated copy begins with."""
    out = {}
    for rel, text in files.items():
        is_log = rel.startswith(DECISION_LOGS) and rel.endswith(".md") and "/" not in rel[len(DECISION_LOGS) :]
        if rel in TODAY or is_log:
            out[rel] = text.split("\n", 1)[1] if text.startswith(MARKER) else text
    return out


def migrate_tree(root: Path, git: Git, hand_path: Path) -> int:
    """Stage 1 on the working tree, which must hold no records yet."""
    del git  # the tree is read from disk; the signature matches the other commands
    if load_records(tree_files(root))[0]:
        print("records migrate: the tree already holds records; migrate runs once, from today's files", file=sys.stderr)
        return 1
    files = old_files(tree_files(root, (*TODAY, DECISION_LOGS)))
    try:
        result = migrate(files, _hand(hand_path))
    except (MigrationError, ValueError) as exc:  # a converter bug or a bad hand file: reported, nothing written
        print(f"records migrate: {exc}", file=sys.stderr)
        return 1
    out, problems = generate(result.records, {k.rsplit("/", 1)[0] + "/": v for k, v in result.headers.items()})
    write(root, {**{r.path: record_text(r) for r in result.records}, **result.headers, **out})
    for line in [*problems, *result.listed]:
        print(f"records migrate: listed: {line}")
    print(f"records migrate: {len(result.records)} record(s), {len(out)} generated file(s)")
    return 1 if problems else 0


@dataclass
class Changes:
    """What a late branch's diff maps onto main's records: records to write, paths to delete, refusals."""

    writes: dict[str, Record] = field(default_factory=dict)
    deletes: set[str] = field(default_factory=set)
    refused: list[str] = field(default_factory=list)


def _parsed(files: Mapping[str, str], hand: Hand) -> dict[tuple[str, str], Record]:
    """Each entry of the old files, keyed by family and id (a gap by its slug)."""
    out: dict[tuple[str, str], Record] = {}
    if LESSONS_FILE in files:
        out |= {("lessons", r.id): r for r in lessons(files[LESSONS_FILE])[1]}
    if GAPS_FILE in files:
        out |= {("gaps", r.id): r for r in gaps(files[GAPS_FILE], hand)[1]}
    if BACKLOG_FILE in files:
        out |= {("backlog", r.id): r for r in backlog(files[BACKLOG_FILE])[1]}
    logs = {rel[len(DECISION_LOGS) : -3]: t for rel, t in files.items() if rel.startswith(DECISION_LOGS)}
    if logs:
        out |= {("decisions", f"{r.log}/{r.id}"): r for r in build(logs, hand)[1]}
    return out


def _fresh(record: Record) -> Record:
    """A new record from a late branch's entry: no ``legacy``, which only the migration writes."""
    meta = {**record.meta, "legacy": None}
    return read_record(record.path, record_text(Record(record.family, record.path, meta, record.body)))


def _edited(
    key: tuple[str, str], old: Record, new: Record, *, mine: Record | None, when: str, branch: str
) -> Record | str:
    """Main's record with the branch's edit applied, or the reason §4 refuses it."""
    if mine is None:
        return f"{key[0]} {key[1]}: edited on the branch but not on main"
    family, before, after = key[0], dict(old.meta), dict(new.meta)
    moved = {k for k in before if k != "legacy" and before[k] != after[k]} | (
        {"body"} if old.body != new.body else set()
    )
    allowed = {"lessons": {"body", "title", "section", "slug"}, "backlog": {"body", "lands_with", "status", "done_in"},
               "gaps": {"body", "gate"}}.get(family, set())  # fmt: skip
    if family == "lessons":
        moved -= {"slug"} if before["title"] != after["title"] else set()
    if not moved <= allowed or "slug" in moved:
        return f"{family} {key[1]}: the branch changed {sorted(moved - allowed or moved)}, which §4 doesn't allow"
    raced = sorted(
        k for k in moved if (mine.body if k == "body" else mine.meta[k]) != (old.body if k == "body" else before[k])
    )
    if raced:
        return f"{family} {key[1]}: main changed {raced} since the branch's base too; move the branch's edit by hand"
    meta = {**mine.meta, **{k: after[k] for k in moved if k != "body"}}
    if family == "lessons":
        why = f"moved from {branch}'s edit of the lessons file by migrate-branch"
        meta["amended"] = (*mine.maps("amended"), {"date": when, "why": why})
    body = new.body if "body" in moved else mine.body
    return read_record(mine.path, record_text(Record(family, mine.path, meta, body)))


def map_changes(
    base: Mapping[str, str], head: Mapping[str, str], *, main: list[Record], hand: Hand, when: str, branch: str
) -> Changes:
    """The branch's diff of the old files, from ``base`` to ``head``, as changes to ``main``'s records."""
    before, after = _parsed(base, hand), _parsed(head, hand)
    by_key = {(r.family, f"{r.log}/{r.id}" if r.family == "decisions" else r.id): r for r in main}
    out = Changes()
    for key in sorted(after.keys() - before.keys()):
        out.writes[after[key].path] = _fresh(after[key])
    for key in sorted(before.keys() - after.keys()):
        if key[0] == "gaps" and key in by_key:
            out.deletes.add(by_key[key].path)
        else:
            out.refused.append(
                f"{key[0]} {key[1]}: deleted on the branch; a {BY_NAME[key[0]].format.name} is never deleted"
            )
    for key in sorted(before.keys() & after.keys()):
        old, new = before[key], after[key]
        if (old.meta, old.body) == (new.meta, new.body) or _same_but_legacy(old, new):
            continue
        if key[0] == "decisions":
            out.refused.append(f"decision {key[1]}: edited on the branch; a decision never changes")
            continue
        edited = _edited(key, old, new, mine=by_key.get(key), when=when, branch=branch)
        if isinstance(edited, str):
            out.refused.append(edited)
        else:
            out.writes[edited.path] = edited
    return out


def _same_but_legacy(old: Record, new: Record) -> bool:
    """Equal apart from ``legacy``, which records presentation the branch can't have meant to edit."""

    def content(r: Record) -> tuple[dict[str, object], str]:
        return {k: v for k, v in r.meta.items() if k != "legacy"}, r.body

    return content(old) == content(new)


def changed_heads(before: Mapping[str, str], after: Mapping[str, str], hand: Hand) -> list[str]:
    """The old files whose head (the text before their entries) the branch changed: a head is a ``_header.md`` now,
    which the branch's session edits by hand, so each is refused by name rather than dropped (§8)."""
    out = []
    for rel in sorted(before.keys() & after.keys()):
        if before[rel] != after[rel] and _head(rel, before[rel], hand) != _head(rel, after[rel], hand):
            out.append(f"{rel}: the branch changed its head; make that edit in its _header.md by hand")
    return out


def _head(rel: str, text: str, hand: Hand) -> str:
    if rel == LESSONS_FILE:
        return lessons(text)[0]
    if rel == GAPS_FILE:
        return gaps(text, hand)[0]
    if rel == BACKLOG_FILE:
        return backlog(text)[0]
    return split_log(rel[len(DECISION_LOGS) : -3], text)[0]


def _ready(git: Git, branch: str) -> str | None:
    """Why ``migrate-branch`` can't run in this worktree now, or None."""
    if git.run("symbolic-ref", "-q", "--short", "HEAD").strip() != branch:
        return f"--into must be {branch}'s worktree, with {branch} checked out"
    if git.merging():
        return "a merge is in progress: abort it (git merge --abort), run migrate-branch, commit, then merge main"
    if git.run("status", "--porcelain", "--", *TODAY, DECISION_LOGS, *ROOTS).strip():
        return "the old files or the record directories have uncommitted changes: commit or discard them first"
    return None


def _writes(git: Git, main_files: Mapping[str, str], changes: Changes) -> tuple[dict[str, str | None], list[str]]:
    """What to write: main's records and headers the worktree lacks (their bytes as main has them), the branch's
    changes, and the regenerated files. A record the worktree already holds is never overwritten unless it is one
    the branch's diff changed."""
    have = tree_files(git.root)
    mine, _ = load_records({p: t for p, t in have.items() if p in main_files or p not in TODAY})
    by_path = {r.path: r for r in load_records(main_files)[0]} | {r.path: r for r in mine}
    by_path |= changes.writes
    records = [r for p, r in sorted(by_path.items()) if p not in changes.deletes]
    out, problems = generate(records, headers_of({**main_files, **have}))
    writes: dict[str, str | None] = {p: t for p, t in main_files.items() if p not in have}
    writes |= {p: record_text(r) for p, r in changes.writes.items()} | dict.fromkeys(changes.deletes) | out
    return writes, problems


def migrate_branch(git: Git, branch: str, hand_path: Path) -> int:
    """Move ``branch``'s committed edits of the old files into records, written into its worktree ``git.root``.

    Run it from a checkout of ``origin/main`` (which has this script and the loaders it needs), with ``--into`` the
    late branch's worktree: §8's shape, so it works before the branch merges ``main``."""
    if (why := _ready(git, branch)) is not None:
        print(f"records migrate-branch: {why}", file=sys.stderr)
        return 1
    base = git.fetch_base()
    scope = (*TODAY, DECISION_LOGS)
    main_files = git.files_at("origin/main", ROOTS)
    when = git.run("log", "-1", "--format=%cs", branch).strip()
    try:
        hand = _hand(hand_path)
        before, after = old_files(git.files_at(base, scope)), old_files(git.files_at(branch, scope))
        changes = map_changes(before, after, main=load_records(main_files)[0], hand=hand, when=when, branch=branch)
        changes.refused += changed_heads(before, after, hand)
    except (MigrationError, ValueError) as exc:
        print(f"records migrate-branch: {exc}", file=sys.stderr)
        return 1
    for line in changes.refused:
        print(f"records migrate-branch: refused: {line}", file=sys.stderr)
    if changes.refused:
        return 1
    writes, problems = _writes(git, main_files, changes)
    write(git.root, writes)
    for line in [*(f"wrote {p}" for p in sorted(changes.writes)), *problems]:
        print(f"records migrate-branch: {line}")
    print("records migrate-branch: review the records (a new one may not hold unknown), then commit them")
    return 1 if problems else 0
