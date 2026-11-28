"""Standards check 10: the shared records (``docs/design/records_layout.md`` §7).

``check_records`` refuses:

- a record ``records.read_record`` refuses, or whose file name disagrees with its ``id`` and ``slug``;
- a change §4 doesn't allow, compared with the base: a decision changed or deleted; a lesson deleted, or changed
  outside its body, title and section, or changed without a new ``amended`` entry, or with its trail cut; a backlog
  row deleted or changed outside its body, ``lands_with``, ``status`` and ``done_in``; any record's id or slug
  changed. Removing ``legacy`` alone is always allowed (R3's presentation commit), and so is a duplicate's rename
  while the base holds two records with that id and the branch leaves one (§5);
- once the base holds records (the migration has landed), an ``unknown`` in a record the base doesn't hold, and a
  ``legacy`` field written or changed;
- while the generator writes today's forms, a field that disagrees with the prose it duplicates (§4): a gap's
  ``gate`` that its body doesn't name, a backlog ``status`` its prose doesn't state;
- a lesson cited in a line added under ``docs/maxim_upstream/`` that the base doesn't hold (§5);
- a generated file that differs from its regeneration, naming what to edit, or ``migrate-branch`` when it holds an
  entry no record holds (§6, §8);
- a relation naming an unknown decision, path, section or external ruling, and a cycle among relations;
- a record over its family's word budget (§6, RL4).

The comparison is refused during an uncommitted merge, when the working tree holds ``main``'s incoming lines as if
they were the branch's (RL12).
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from lint_ids import cited_lessons, frozen_files
from lint_repo import tracked_text_files
from records import BY_NAME, UNKNOWN, Record, load_records, stated_status, words
from records_git import Git
from records_index import TODAYS_FORM, generate, generation, headers_of, stray_lines

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = "docs/maxim_upstream/"
# What the comparison reads at the base: the record directories, the lessons file and the upstream drafts.
BASE_PATHS = (
    "docs/lessons/",
    "docs/design/decisions/",
    "docs/known_gaps/",
    "docs/standards_backlog/",
    "docs/maxim_upstream/",
    "docs/lessons_maxim_in_games.md",
)
LESSON_CHANGES = {"body", "title", "section", "amended"}
BACKLOG_CHANGES = {"body", "lands_with", "status", "done_in"}
_SECTION_OF = re.compile(r"^(?P<path>\S+?)(?: §(?P<section>[\w.]+))?$")


@dataclass(frozen=True)
class Base:
    """What the comparison reads at the base: its files (records, generated files, upstream drafts, lessons)."""

    files: Mapping[str, str]


def _by_path(records: list[Record]) -> dict[str, Record]:
    return {r.path: r for r in records}


def _fields(record: Record) -> dict[str, object]:
    """A record's comparable content: its front matter without ``legacy``, and its body."""
    return {**{k: v for k, v in record.meta.items() if k != "legacy"}, "body": record.body}


def _changed(old: Record, new: Record) -> set[str]:
    before, after = _fields(old), _fields(new)
    return {k for k in before.keys() | after.keys() if before.get(k) != after.get(k)}


def _lesson_change(old: Record, new: Record, changed: set[str]) -> list[str]:
    if changed - LESSON_CHANGES:
        return [
            f"{new.path}: a lesson may change only its body, title and section, not {sorted(changed - LESSON_CHANGES)}"
        ]
    trail_old, trail_new = old.maps("amended"), new.maps("amended")
    if trail_new[: len(trail_old)] != trail_old:
        return [f"{new.path}: a lesson's amended trail only grows; the branch cut or rewrote it"]
    if changed - {"amended"} and len(trail_new) == len(trail_old):
        return [f"{new.path}: a lesson changed without a new amended entry (a date and a one-line why)"]
    return []


def _change_problems(old: Record, new: Record) -> list[str]:
    """What §4 refuses in one record changed since the base."""
    changed = _changed(old, new)
    if not changed:
        return []
    if new.family == "decisions":
        return [f"{new.path}: a decision never changes; a new ruling is a new record (records_layout §4)"]
    if new.family == "lessons":
        return _lesson_change(old, new, changed)
    if new.family == "backlog" and changed - BACKLOG_CHANGES:
        return [f"{new.path}: a backlog row may change only its body, lands_with, status and done_in"]
    return []


def _duplicate_fix(old: Record, base: list[Record], branch: list[Record]) -> bool:
    """The one rename allowed (§5): the base holds two records with this id in its family, and the branch one."""

    def count(records: list[Record]) -> int:
        return sum(1 for r in records if r.family == old.family and r.id == old.id)

    return count(base) == 2 and count(branch) == 1


def changes(base: list[Record], branch: list[Record]) -> list[str]:
    """Every change §4 refuses between the base's records and the branch's, and what the migration rules hold."""
    now, problems = _by_path(branch), []
    migrated = bool(base)
    for old in base:
        new = now.get(old.path)
        if new is None and old.family not in ("gaps",) and not _duplicate_fix(old, base, branch):
            problems.append(f"{old.path}: a {BY_NAME[old.family].format.name} is never deleted or renamed (§4)")
        elif new is not None:
            problems += _change_problems(old, new)
            if new.meta["legacy"] is not None and new.meta["legacy"] != old.meta["legacy"]:
                problems.append(f"{new.path}: only the migration writes legacy (§4)")
    was = {r.path for r in base}
    for new in branch:
        if migrated and new.path not in was:
            problems += [f"{new.path}: {k} is unknown, but only a migrated record may hold unknown" for k, v in
                         new.meta.items() if v == UNKNOWN]  # fmt: skip
            problems += [f"{new.path}: only the migration writes legacy (§4)"] if new.meta["legacy"] is not None else []
            if new.family == "decisions" and new.maps("amended_by_external"):
                problems.append(
                    f"{new.path}: only the migration writes amended_by_external; a later ruling is a record"
                )
    return problems


def prose_agrees(records: list[Record]) -> list[str]:
    """While the prose still duplicates a field (§4, "One owner per fact"), the two must agree."""
    if not TODAYS_FORM:
        return []
    problems = []
    for r in records:
        if r.family == "gaps":
            problems += _gap_prose(r)
        if r.family == "backlog":
            lands_with = None if r.meta["lands_with"] == UNKNOWN else str(r.meta["lands_with"])
            said, _ = stated_status(r.body.rstrip("\n"), lands_with)
            if UNKNOWN not in (said, r.meta["status"]) and r.meta["status"] != said:
                problems.append(f"{r.path}: status {r.meta['status']} but its prose says {said}")
    return problems


def _gap_prose(r: Record) -> list[str]:
    """A gap's ``gate`` and ``closes_at`` must each be named in its body, unless unknown or explained as absent."""
    out = []
    for name, absent in (("gate", "none"), ("closes_at", "unscheduled")):
        value = str(r.meta[name])
        if value != UNKNOWN and not value.startswith(absent) and value not in r.body:
            out.append(f"{r.path}: {name} {value} is not what its body names")
    return out


def _base_lessons(base: Base) -> set[int]:
    records, _ = load_records(base.files)
    ids = {int(r.id) for r in records if r.family == "lessons"}
    return ids or {
        int(n) for n in re.findall(r"^### (\d+)\.", base.files.get("docs/lessons_maxim_in_games.md", ""), re.M)
    }


def upstream_citations(files: Mapping[str, str], base: Base) -> list[str]:
    """A lesson may be cited under ``docs/maxim_upstream/`` only once it is on the base (§5)."""
    known, problems = _base_lessons(base), []
    for rel in sorted(files):
        if not (rel.startswith(UPSTREAM) and rel.endswith(".md")):
            continue
        before = {n for n, _ in cited_lessons(base.files.get(rel, ""))}
        for n, line in cited_lessons(files[rel]):
            if n not in before and n not in known:
                problems.append(f"{rel}:{line}: cites lesson {n}, which is not on the base; cite it once it merges")
    return problems


HAND_EDIT = (
    "which no record generates: a hand edit. Move it into its record or _header.md; a late branch's edit of the old "
    "files is moved by `scripts/records.py migrate-branch <branch> --into <its worktree> --hand <the migration's hand "
    "file>` (records_layout §8). Then run `scripts/records.py index`"
)


def generated(files: Mapping[str, str], records: list[Record], base: Mapping[str, str]) -> list[str]:
    """Every generated file must equal its regeneration. One that differs is stale (run ``index``) when every line
    comes from what the tree's or the base's records generate, and holds a hand edit otherwise
    (``records_index.stray_lines``, the one rule ``index`` refuses by too)."""
    out, problems = generate(records, headers_of(files))
    known = [out, generation(base)]
    for path, text in sorted(out.items()):
        have = files.get(path)
        if have is None:
            problems.append(f"{path} is missing: run `scripts/records.py index`")
        elif have != text:
            stray = stray_lines(path, have, known)
            how = f"it holds {stray[0]!r}, {HAND_EDIT}" if stray else "it is stale: run `scripts/records.py index`"
            problems.append(f"{path} differs from its regeneration: {how}")
    return problems


def _section_exists(text: str, section: str) -> bool:
    return re.search(rf"^#{{1,6}} {re.escape(section)}(?:[.\s]|$)", text, re.M) is not None


def _relation_targets(r: Record, ids: set[str], files: Mapping[str, str]) -> list[str]:
    problems = [
        f"{r.path}: {rel} names {t}, which no decision record holds"
        for rel in ("supersedes", "amends", "confirms", "corrects")
        for t in r.strings(rel)
        if t not in ids
    ]
    for entry in r.strings("restates"):
        m = _SECTION_OF.match(entry)
        if entry in ids:
            continue
        if m is None or m.group("path") not in files:
            problems.append(f"{r.path}: restates {entry}, which is neither a decision id nor a repository path")
        elif m.group("section") and not _section_exists(files[m.group("path")], m.group("section")):
            problems.append(f"{r.path}: restates {entry}, but {m.group('path')} has no section §{m.group('section')}")
    for e in r.maps("amended_by_external"):
        text = files.get(str(e["path"]))
        if text is None or not re.search(rf"^\| {re.escape(str(e['ruling']))} \|", text, re.M):
            problems.append(
                f"{r.path}: amended_by_external names ruling {e['ruling']} of {e['path']}, which doesn't exist"
            )
    return problems


def relations(records: list[Record], files: Mapping[str, str]) -> list[str]:
    """Every relation names something that exists, and no ruling reaches itself through them."""
    decisions = [r for r in records if r.family == "decisions"]
    ids = {r.id for r in decisions}
    problems = [p for r in decisions for p in _relation_targets(r, ids, files)]
    edges: dict[str, set[str]] = defaultdict(set)
    for r in decisions:
        for rel in ("supersedes", "amends", "confirms", "corrects", "restates"):
            edges[r.id] |= {t for t in r.strings(rel) if t in ids}
    return problems + [f"decision {c} reaches itself through its relations" for c in _cycles(edges)]


def _cycles(edges: Mapping[str, set[str]]) -> list[str]:
    """The ids on a cycle, each reported once: a node from which a walk returns to itself."""
    found = []
    for start in sorted(edges):
        seen, stack = set(), list(edges[start])
        while stack:
            node = stack.pop()
            if node == start:
                found.append(start)
                break
            if node not in seen:
                seen.add(node)
                stack.extend(edges.get(node, ()))
    return found


def budgets(records: list[Record]) -> list[str]:
    return [
        f"{r.path}: {words(r.body)} words; a {r.family[:-1] if r.family != 'backlog' else 'backlog row'} record's "
        f"budget is {BY_NAME[r.family].budget_words} (records_layout §6)"
        for r in records
        if words(r.body) > BY_NAME[r.family].budget_words
    ]


def check_records(files: Mapping[str, str], *, base: Base | None, merging: bool) -> list[str]:
    """Every finding over the tree's records, compared with ``base`` (None: nothing to compare yet)."""
    frozen = frozen_files(dict(files))
    live = {k: v for k, v in files.items() if k not in frozen}
    records, problems = load_records(live)
    base_files = base.files if base is not None else {}
    problems += prose_agrees(records) + generated(files, records, base_files) + relations(records, files)
    problems += budgets(records)
    if base is None:
        return problems
    if merging:
        return [
            *problems,
            "records: the change check refuses to run during an uncommitted merge: commit it first (RL12)",
        ]
    base_records, _ = load_records(base.files)
    return problems + changes(base_records, records) + upstream_citations(files, base)


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    """``python scripts/lint_records.py [--base REF]``: the check alone, against the merge base with REF (default
    ``origin/main``, as the gate's), exit 1 on any finding. The gate runs it through ``lint_standards.py``."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="origin/main", help="the ref whose merge base the changes are compared with")
    args = parser.parse_args(argv)
    git = Git(root, os.environ)  # the gate's own environment: it reads the repository it is run in
    files = tracked_text_files(root)
    if not git.ok("rev-parse", "--verify", "-q", f"{args.base}^{{commit}}"):
        print(f"lint_records: --base {args.base} is not a commit here; fetch it", file=sys.stderr)
        return 1
    base = Base(git.files_at(git.merge_base(args.base), BASE_PATHS))
    return report(check_records(files, base=base, merging=git.merging()))


def report(problems: list[str]) -> int:
    """Print the findings and the verdict; the exit code."""
    for p in problems:
        print(p, file=sys.stderr)
    print(f"lint_records: {'FAIL' if problems else 'PASS'} ({len(problems)} finding(s))")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
