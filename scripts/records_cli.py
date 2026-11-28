"""The ``records.py`` commands: ``index``, ``renumber``, ``migrate`` and ``migrate-branch`` (records_layout §5, §6, §8).

Each reads the working tree and writes into it; none commits. The base is the merge base with a freshly fetched
``origin/main`` (RL12), and ``renumber`` and ``migrate-branch`` refuse to run during an uncommitted merge.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

import records_branch
from lint_records import HAND_EDIT
from records import load_records
from records_git import Git
from records_index import edit_found, generate, generation, headers_of
from records_renumber import RenumberError, merged_commit, merged_own, parse_mapping, plan
from records_tree import ROOTS, tree_files, write


def known_generations(git: Git) -> list[dict[str, str]]:
    """What HEAD's, the base's and (during a merge) MERGE_HEAD's records generate: the text a generated file may
    hold without being a hand edit. The base is the merge base with ``origin/main`` as last fetched."""
    revs = ["HEAD"] if git.ok("rev-parse", "-q", "--verify", "HEAD") else []
    if revs and git.ok("rev-parse", "-q", "--verify", "origin/main"):
        revs.append(git.merge_base("origin/main"))
    revs += ["MERGE_HEAD"] if git.merging() else []
    return [generation(git.files_at(rev, ROOTS)) for rev in revs]


def index(root: Path, git: Git) -> int:
    """Regenerate every generated file from the records; refuse, writing nothing, when a generated file was edited
    other than by ``index`` (``records_index.edit_found``)."""
    files = tree_files(root)
    records, problems = load_records(files)
    out, missing = generate(records, headers_of(files))
    current = {p: (root / p).read_text(encoding="utf-8") for p in out if (root / p).is_file()}
    known = [out, *known_generations(git)]
    merging = git.merging()
    for path in sorted(current):
        if (edit := edit_found(path, current[path], known, merging=merging)) is not None:
            problems.append(f"{path} {edit}: {HAND_EDIT}")
    problems += missing
    if problems:
        for p in problems:
            print(f"records index: {p}", file=sys.stderr)
        print("records index: nothing was written", file=sys.stderr)
        return 1
    write(root, {p: t for p, t in out.items() if current.get(p) != t})
    print(f"records index: {len(out)} generated file(s), {len(records)} record(s)")
    return 0


def renumber(root: Path, git: Git, pairs: list[str], merged: str | None) -> int:
    if git.merging():
        print("records renumber: refused during an uncommitted merge; commit the merge first (RL12)", file=sys.stderr)
        return 1
    try:
        mapping = parse_mapping(pairs)
        files = {**git_tracked(git), **tree_files(root)}
        if merged:
            merge = merged_commit(git, merged)
            added, own = merged_own(git, merge, mapping)
            base_paths = {r.path for r in load_records(files)[0]} - added  # only that merge's records are its own
            writes, report = plan(files, base_paths, {}, mapping, own=own)
        else:
            base = git.fetch_base()
            base_paths = set(git.files_at(base, ROOTS))
            writes, report = plan(files, base_paths, git.hunks(base), mapping)
    except RenumberError as exc:
        print(f"records renumber: {exc}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:  # a fetch with no network, say: reported, nothing written
        print(f"records renumber: git {' '.join(exc.cmd[1:3])} failed: {exc.stderr.strip()}", file=sys.stderr)
        return 1
    write(root, writes)
    for old, new in report.renamed:
        print(f"renamed {old} -> {new}")
    print(f"rewrote {len(report.rewritten)} citation line(s) the branch added or changed")
    for line in report.listed:
        print(f"not rewritten (main's, or a hand-resolved line): {line}")
    print("a green check doesn't prove a listed citation moved: read each one")
    return index(root, git)


def git_tracked(git: Git) -> dict[str, str]:
    """Every tracked or untracked (not ignored) text file in the working tree, as the citations' rewrite reads
    them: an uncommitted file's citations are the branch's own lines too."""
    out = {}
    for rel in filter(None, git.run("ls-files", "-z", "-co", "--exclude-standard").split("\0")):
        path = git.root / rel
        if path.is_file():
            try:
                out[rel] = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:  # binary: no citations to rewrite
                continue
    return out


def main(argv: list[str], *, cwd: Path, env: Mapping[str, str]) -> int:
    """Run one command on the repository the caller is in (``cwd``'s top level), never the one this script lives
    in: a late branch runs ``origin/main``'s copy of the script. Git runs with ``env``, the command's own."""
    parser = argparse.ArgumentParser(prog="records.py", description="the shared records' commands")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("index", help="regenerate every generated file from the records")
    p = sub.add_parser("renumber", help="move this branch's records off colliding ids")
    p.add_argument("pairs", nargs="+", metavar="OLD=NEW")
    p.add_argument("--merged", metavar="PR", help="rename the record PR's merge added (a duplicate on main)")
    m = sub.add_parser("migrate", help="stage 1: today's four files into records")
    m.add_argument("--hand", required=True, help="the hand file: titles, aliases, kinds and steps (listed)")
    b = sub.add_parser("migrate-branch", help="a late branch's edits of the old files into records")
    b.add_argument("branch")
    b.add_argument("--into", required=True, help="the late branch's worktree, which receives the records")
    b.add_argument("--hand", required=True, help="the migration's hand file, as R3 committed it")
    args = parser.parse_args(argv)
    root = Path(Git(cwd, env).run("rev-parse", "--show-toplevel").strip())
    git = Git(root, env)
    if args.command == "index":
        return index(root, git)
    if args.command == "renumber":
        return renumber(root, git, args.pairs, args.merged)
    if args.command == "migrate":
        return records_branch.migrate_tree(root, git, Path(args.hand))
    into = Git(Path(args.into).resolve(), env)
    return records_branch.migrate_branch(into, args.branch, Path(args.hand).resolve())
