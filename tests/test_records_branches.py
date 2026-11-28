"""Records under concurrent branches (``docs/design/records_layout.md`` §5, §6, §8; §9 R1, R2).

Git repositories are made in ``tmp_path``, with an ``origin`` that is a local bare repository, and every git call runs
with ``tests/_gitutil.py``'s isolated environment, so nothing reaches a repository named in the session's.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pytest

from tests._gitutil import git, isolated_env
from tests._records import (
    HEADERS,
    backlog_row,
    branch,
    build,
    cli,
    decision,
    gap,
    index,
    lesson,
    lint_ids,
    records,
    renumber,
    rgit,
    rtree,
    tree,
)
from tests._records import _load as _load_script
from tests._records import migrate as rmigrate

# -- repositories ---------------------------------------------------------------------------------------------------


def _write(root: Path, files: Mapping[str, str | None]) -> None:
    for rel, text in files.items():
        path = root / rel
        if text is None:
            path.unlink()
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)


def _commit(root: Path, files: Mapping[str, str | None], message: str) -> None:
    _write(root, files)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)


def _repo(tmp_path: Path, files: dict[str, str]) -> tuple[Path, Path]:
    """(origin, a clone on main) with ``files`` as main's first commit."""
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    work = tmp_path / "work"
    git(tmp_path, "init", "-q", "-b", "main", str(work))
    git(work, "remote", "add", "origin", str(origin))
    _commit(work, files, "base")
    git(work, "push", "-q", "origin", "main")
    return origin, work


def _clone(tmp_path: Path, origin: Path, name: str) -> Path:
    other = tmp_path / name
    git(tmp_path, "clone", "-q", str(origin), str(other))
    return other


def _git(root: Path):
    return rgit.Git(root, isolated_env())


def _regenerate(root: Path) -> None:
    assert cli.index(root, _git(root)) == 0


def _files(root: Path) -> dict[str, str]:
    out = rtree.tree_files(
        root, (*rtree.ROOTS, *rtree.TODAY, "docs/generated/", "docs/notes.md", "docs/design/decisions/")
    )
    return {k: v for k, v in out.items()}


# -- the generated index is the detector (§5, RL9) -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("mine", "theirs", "duplicate"),
    [(("O2", "a"), ("O3", "b"), False), (("O2", "a"), ("O2", "b"), True)],
)
def test_two_branches_adding_to_one_family_conflict_in_its_index(tmp_path, mine, theirs, duplicate):
    _, work = _repo(tmp_path, tree(decision("O1", "one")))
    git(work, "checkout", "-q", "-b", "theirs")
    _commit(work, dict([decision(*theirs)]), "theirs")
    _regenerate(work)
    _commit(work, {}, "theirs: index")
    git(work, "checkout", "-q", "main")
    git(work, "checkout", "-q", "-b", "mine")
    _commit(work, dict([decision(*mine)]), "mine")
    _regenerate(work)
    _commit(work, {}, "mine: index")
    merged = git(work, "merge", "-q", "theirs", check=False)
    assert merged.returncode != 0
    assert "docs/generated/decisions_index.md" in git(work, "diff", "--name-only", "--diff-filter=U").stdout
    _regenerate(work)  # the conflict is resolved by the command, never by hand
    found = lint_ids.check_ids(_files(work))
    assert any(f"decisions id {mine[0]} is held by 2 records" in p for p in found) == duplicate


def test_one_id_with_one_slug_on_two_branches_is_an_add_add_conflict(tmp_path):
    _, work = _repo(tmp_path, tree(decision("O1", "one")))
    rel, text = decision("O2", "same")
    git(work, "checkout", "-q", "-b", "theirs")
    _commit(work, {rel: text.replace("Its text.", "Theirs.")}, "theirs")
    git(work, "checkout", "-q", "main")
    git(work, "checkout", "-q", "-b", "mine")
    _commit(work, {rel: text}, "mine")
    assert git(work, "merge", "-q", "theirs", check=False).returncode != 0
    assert rel in git(work, "diff", "--name-only", "--diff-filter=U").stdout


def test_index_refuses_a_generated_file_holding_an_entry_no_record_holds(tmp_path, capsys):
    _, work = _repo(tmp_path, tree(decision("O1", "one")))
    log = work / "docs/design/decisions/alpha.md"
    log.write_text(log.read_text() + "| O9 | **Hand-made.** | owner, 2026-11-20 | — | live |\n")
    before = log.read_text()
    assert cli.index(work, _git(work)) == 1
    assert (
        "holds '| O9 | **Hand-made.** | owner, 2026-11-20 | — | live |', which no record generates"
        in capsys.readouterr().err
    )
    assert log.read_text() == before  # nothing was written


def test_index_refuses_an_edit_inside_an_existing_entry(tmp_path, capsys):
    _, work = _repo(tmp_path, tree(lesson(1, "one", body="The first.\n")))
    path = work / "docs/lessons_maxim_in_games.md"
    _commit(
        work, {"docs/lessons_maxim_in_games.md": path.read_text().replace("The first.", "The first, amended.")}, "edit"
    )
    assert cli.index(work, _git(work)) == 1
    assert "holds 'The first, amended.', which no record generates" in capsys.readouterr().err
    assert "The first, amended." in path.read_text()  # nothing was discarded


def test_index_regenerates_after_a_committed_record_change(tmp_path):
    _, work = _repo(tmp_path, tree(gap("a-gap"), gap("b-gap"), lesson(1, "one")))
    git(work, "fetch", "-q", "origin")
    rel, text = lesson(1, "one", title="Uno")
    _commit(work, {"docs/known_gaps/a-gap.md": None, rel: text}, "delete a gap, retitle a lesson; no index")
    _regenerate(work)
    assert "### 1. Uno" in (work / "docs/lessons_maxim_in_games.md").read_text()


def test_index_regenerates_after_a_gap_is_deleted(tmp_path):
    _, work = _repo(tmp_path, tree(gap("a-gap"), gap("b-gap")))
    (work / "docs/known_gaps/a-gap.md").unlink()
    _regenerate(work)
    assert "A gap" in (work / "docs/known_gaps.md").read_text()
    assert (work / "docs/known_gaps.md").read_text().count("\n- ") == 1


# -- renumber's choices, on a planned tree (§5) ----------------------------------------------------------------------


def _own(*hunks: tuple[str, tuple[str, ...], tuple[int, ...]]) -> dict[str, list[object]]:
    out: dict[str, list[object]] = {}
    for rel, removed, added in hunks:
        out.setdefault(rel, []).append(rgit.Hunk(removed, added))
    return out


def _plan(files: dict[str, str], base: set[str], hunks: dict[str, list[object]], *pairs: str):
    return renumber.plan(files, base, hunks, renumber.parse_mapping(list(pairs)))


def test_renumber_rewrites_the_branchs_own_citation_and_lists_mains():
    mine_rel, mine = decision("O5", "mine")
    files = {mine_rel: mine, "docs/notes.md": "Main cites O5.\nThe branch cites O5.\n"}
    hunks = _own((mine_rel, (), tuple(range(1, 12))), ("docs/notes.md", (), (2,)))
    writes, report = _plan(files, set(), hunks, "O5=O6")
    assert writes["docs/notes.md"] == "Main cites O5.\nThe branch cites O6.\n"
    assert report.listed == ["docs/notes.md:1: Main cites O5."]
    assert writes[mine_rel] is None
    assert (
        records.read_record(
            "docs/design/decisions/alpha/O6-mine.md", writes["docs/design/decisions/alpha/O6-mine.md"]
        ).id
        == "O6"
    )


def test_a_hand_resolved_line_holding_both_citations_is_listed_not_rewritten():
    files = {"docs/notes.md": "Shared, O5 main and O5 branch.\n"}
    hunks = _own(("docs/notes.md", ("Shared, O5 main.",), (1,)))
    writes, report = _plan(files, set(), hunks, "O5=O6")
    assert writes == {}
    assert "docs/notes.md:1: Shared, O5 main and O5 branch." in report.listed


def test_renumber_never_rewrites_a_frozen_file_an_upstream_draft_or_a_review_finding():
    files = {
        "docs/frozen/a.md": "Cites O5.\n",
        "docs/frozen/freeze.sha256": "0" * 64 + "  a.md\n",
        "docs/maxim_upstream/x.md": "Cites O5 and lesson 44.\n",
        "docs/design/reviews/r/x.md": "Finding O5: a defect.\n",
    }
    hunks = _own(*((rel, (), (1,)) for rel in files))
    writes, report = _plan(files, set(), hunks, "O5=O6", "44=45")
    assert writes == {}
    assert report.rewritten == []


def test_renumber_still_renames_the_branchs_record_when_mains_of_that_number_is_cited_upstream():
    mine_rel, mine = lesson(44, "mine")
    main_rel, main = lesson(44, "theirs")
    files = {
        mine_rel: mine,
        main_rel: main,
        "docs/maxim_upstream/x.md": "As lesson 44 shows.\n",
        "docs/a.md": "See lesson 44.\n",
    }
    hunks = _own((mine_rel, (), tuple(range(1, 12))), ("docs/a.md", (), (1,)))
    writes, _report = _plan(files, {main_rel}, hunks, "44=45")
    assert writes[mine_rel] is None
    assert "docs/lessons/45-mine.md" in writes
    assert writes["docs/a.md"] == "See lesson 45.\n"
    assert "docs/maxim_upstream/x.md" not in writes
    assert main_rel not in writes


def test_a_range_mapping_applies_at_once():
    files = {"docs/a.md": "O5 then O6.\n"}
    writes, _ = _plan(files, set(), _own(("docs/a.md", (), (1,))), "O5=O6", "O6=O7")
    assert writes["docs/a.md"] == "O6 then O7.\n"


def test_a_decision_id_is_rewritten_only_as_a_whole_token():
    files = {"docs/a.md": "O5, PH2-O5, O55, O5a and `O5`.\n"}
    writes, _ = _plan(files, set(), _own(("docs/a.md", (), (1,))), "O5=O6")
    assert writes["docs/a.md"] == "O6, PH2-O5, O55, O5a and `O6`.\n"


@pytest.mark.parametrize("pairs", [["O5"], ["O5=O5"], ["O5=6"], ["O5=O6", "O5=O7"], ["a-slug=b-slug"]])
def test_a_mapping_that_cant_be_done_is_refused(pairs):
    with pytest.raises(renumber.RenumberError):
        renumber.parse_mapping(pairs)


def test_a_relation_to_a_renumbered_id_moves_with_it():
    a_rel, a = decision("O5", "mine")
    b_rel, b = decision("O7", "later", amends=["O5"])
    hunks = _own((a_rel, (), tuple(range(1, 12))), (b_rel, (), tuple(range(1, 14))))
    writes, _ = _plan({a_rel: a, b_rel: b}, set(), hunks, "O5=O6")
    assert records.read_record(b_rel, writes[b_rel]).strings("amends") == ("O6",)


# -- renumber in a repository: the base is a freshly fetched origin/main (RL12) -------------------------------------


def _collision(tmp_path: Path) -> tuple[Path, Path]:
    """Main and a branch that both took O5; the branch has merged main, and local main is stale."""
    origin, work = _repo(tmp_path, tree(decision("O1", "one"), ("docs/notes.md", "Intro.\n")))
    git(work, "checkout", "-q", "-b", "phase1/mine")
    _commit(work, dict([decision("O5", "mine")]) | {"docs/notes.md": "Intro.\nThe branch cites O5.\n"}, "mine")
    other = _clone(tmp_path, origin, "other")
    _commit(other, dict([decision("O5", "theirs")]) | {"docs/notes.md": "Main cites O5.\nIntro.\n"}, "theirs")
    _regenerate(other)
    _commit(other, {}, "theirs: index")
    git(other, "push", "-q", "origin", "main")
    git(work, "fetch", "-q", "origin")
    merged = git(work, "merge", "-q", "--no-edit", "origin/main", check=False)
    if merged.returncode != 0:  # the generated files conflict, as they should: the command resolves them
        _regenerate(work)
        git(work, "add", "-A")
        git(work, "commit", "-q", "--no-edit")
    return origin, work


def test_renumber_in_a_repository_with_a_stale_local_main(tmp_path, capsys):
    _, work = _collision(tmp_path)
    assert git(work, "rev-parse", "main").stdout != git(work, "rev-parse", "origin/main").stdout  # local main is stale
    assert cli.renumber(work, _git(work), ["O5=O6"], None) == 0
    assert (work / "docs/notes.md").read_text() == "Main cites O5.\nIntro.\nThe branch cites O6.\n"
    assert (work / "docs/design/decisions/alpha/O6-mine.md").is_file()
    assert (work / "docs/design/decisions/alpha/O5-theirs.md").is_file()
    assert "docs/notes.md:1: Main cites O5." in capsys.readouterr().out
    assert lint_ids.check_ids(_files(work)) == []


def test_renumber_refuses_during_an_uncommitted_merge(tmp_path, capsys):
    origin, work = _repo(tmp_path, tree(decision("O1", "one")))
    git(work, "checkout", "-q", "-b", "phase1/mine")
    _commit(work, {"docs/a.md": "Mine.\n"}, "mine")
    other = _clone(tmp_path, origin, "other")
    _commit(other, {"docs/b.md": "Theirs.\n"}, "theirs")
    git(other, "push", "-q", "origin", "main")
    git(work, "fetch", "-q", "origin")
    git(work, "merge", "-q", "--no-commit", "--no-ff", "origin/main")
    assert cli.renumber(work, _git(work), ["O1=O2"], None) == 1
    assert "refused during an uncommitted merge" in capsys.readouterr().err


def test_renumber_merged_renames_that_prs_record_and_rewrites_its_merges_lines(tmp_path):
    _origin, work = _repo(tmp_path, tree(decision("O1", "one"), ("docs/notes.md", "Intro.\n")))
    for n, (slug, note) in enumerate((("first", "docs/a.md"), ("second", "docs/b.md")), start=1):
        git(work, "checkout", "-q", "-b", f"phase1/{slug}", "main")
        _commit(work, dict([decision("O5", slug)]) | {note: f"The {slug} cites O5.\n"}, slug)
        git(work, "checkout", "-q", "main")
        git(work, "merge", "-q", "--no-ff", "-m", f"Merge pull request #{n} from x/{slug}", f"phase1/{slug}")
    _regenerate(work)
    _commit(work, {}, "index")
    git(work, "push", "-q", "origin", "main")
    git(work, "checkout", "-q", "-b", "phase1/fix-duplicate")
    assert cli.renumber(work, _git(work), ["O5=O6"], "2") == 0
    assert (work / "docs/design/decisions/alpha/O6-second.md").is_file()
    assert (work / "docs/design/decisions/alpha/O5-first.md").is_file()
    assert (work / "docs/b.md").read_text() == "The second cites O6.\n"
    assert (work / "docs/a.md").read_text() == "The first cites O5.\n"
    assert lint_ids.check_ids(_files(work)) == []


# -- migrate-branch (§8, §9 R2) ------------------------------------------------------------------------------------

OLD_LESSONS = (
    "# Lessons\n\nThe head.\n\n## World and physics\n\n### 1. One (2026-11-16)\n\nThe first.\n\n"
    "### 2. Two (2026-11-17)\n\nThe second.\n"
)
OLD_LOG = (
    "# Decisions of `alpha.md`\n\n| Id | Ruling | Who, date | Owner section | Status |\n|---|---|---|---|---|\n"
    "| O1 | **One.** It is ruled. | owner, 2026-11-16 | §1 | live |\n"
)
OLD_GAPS = "# Known gaps\n\nThe head.\n\n**Known gaps:**\n- **A gap.** It is measured.\n"
OLD_BACKLOG = (
    "# Backlog\n\nThe head.\n\n| ID | Rule it enforces | The check | Lands with |\n|---|---|---|---|\n"
    "| B1 | A rule | The check. | open |\n"
)
OLD = {
    "docs/lessons_maxim_in_games.md": OLD_LESSONS,
    "docs/design/decisions/alpha.md": OLD_LOG,
    "docs/known_gaps.md": OLD_GAPS,
    "docs/standards_backlog.md": OLD_BACKLOG,
}
LATE_EDITS = {
    "docs/lessons_maxim_in_games.md": OLD_LESSONS.replace("The first.", "The first, corrected.")
    + "\n### 44. Forty-four (2026-11-25)\n\nThe late lesson.\n",
    "docs/design/decisions/alpha.md": OLD_LOG
    + "| D38 | **Regions.** A late ruling. | owner, 2026-11-25 | §2 | live |\n",
    "docs/standards_backlog.md": OLD_BACKLOG.replace("| The check. | open |", "| **done** (step 4). | open |"),
}


def _hand(tmp_path: Path) -> Path:
    path = tmp_path / "hand.yaml"
    path.write_text("version: 1\n")
    return path


def _migrated_main(tmp_path: Path) -> tuple[Path, Path]:
    """Main before the migration, a late branch made from it that edits the old files, then main migrated."""
    origin, work = _repo(tmp_path, OLD)
    git(work, "checkout", "-q", "-b", "phase1/late")
    _commit(work, LATE_EDITS, "late edits")
    other = _clone(tmp_path, origin, "other")
    assert branch.migrate_tree(other, _git(other), _hand(tmp_path)) == 0
    _commit(other, {}, "migrate")
    git(other, "push", "-q", "origin", "main")
    return origin, work


WHY = "moved from phase1/late's edit of the lessons file by migrate-branch"


def _assert_migrated(work: Path) -> None:
    files = _files(work)
    recs, problems = records.load_records(files)
    assert problems == []
    by_id = {(r.family, r.id): r for r in recs}
    assert by_id[("lessons", "44")].body == "The late lesson.\n"
    assert by_id[("lessons", "44")].meta["legacy"] is None
    assert by_id[("lessons", "1")].body == "The first, corrected.\n"
    assert [dict(e) for e in by_id[("lessons", "1")].maps("amended")] == [
        {"date": by_id[("lessons", "1")].maps("amended")[0]["date"], "why": WHY}
    ]  # fmt: skip
    assert by_id[("decisions", "D38")].title == "Regions."
    assert by_id[("backlog", "B1")].meta["status"] == "done"
    out, _ = index.generate(recs, index.headers_of(files))
    assert all(files[p] == t for p, t in out.items())


def test_migrate_branch_before_the_branch_merges_main(tmp_path):
    _, work = _migrated_main(tmp_path)
    assert branch.migrate_branch(_git(work), "phase1/late", _hand(tmp_path)) == 0
    _assert_migrated(work)


def test_migrate_branch_runs_from_a_main_checkout_into_the_late_branchs_worktree(tmp_path):
    """The shipped shape (§8): the late branch has no records.py yet, so main's checkout runs it, --into the branch."""
    origin, work = _migrated_main(tmp_path)
    main_checkout = _clone(tmp_path, origin, "main-checkout")
    argv = ["migrate-branch", "phase1/late", "--into", str(work), "--hand", str(_hand(tmp_path))]
    assert cli.main(argv, cwd=main_checkout, env=isolated_env()) == 0
    _assert_migrated(work)
    assert git(main_checkout, "status", "--porcelain").stdout == ""  # nothing was written where it ran


def test_migrate_branch_refuses_an_uncommitted_edit_or_a_changed_head(tmp_path, capsys):
    _, work = _migrated_main(tmp_path)
    lessons = work / "docs/lessons_maxim_in_games.md"
    lessons.write_text(lessons.read_text() + "\n### 46. Uncommitted (2026-11-26)\n\nText.\n")
    assert branch.migrate_branch(_git(work), "phase1/late", _hand(tmp_path)) == 1
    assert "uncommitted changes" in capsys.readouterr().err
    git(work, "checkout", "--", "docs/lessons_maxim_in_games.md")
    _commit(
        work,
        {"docs/standards_backlog.md": LATE_EDITS["docs/standards_backlog.md"].replace("The head.", "Edited.")},
        "head",
    )
    assert branch.migrate_branch(_git(work), "phase1/late", _hand(tmp_path)) == 1
    assert "docs/standards_backlog.md: the branch changed its head" in capsys.readouterr().err


def test_migrate_branch_keeps_a_record_the_branch_already_holds(tmp_path):
    _, work = _migrated_main(tmp_path)
    git(work, "fetch", "-q", "origin")
    git(work, "merge", "-q", "--no-edit", "origin/main")
    rel = next(p for p in (work / "docs/lessons").glob("2-*.md")).relative_to(work).as_posix()
    amended = (work / rel).read_text().replace("amended: []", "amended:\n- date: '2026-11-26'\n  why: mine")
    _commit(work, {rel: amended.replace("The second.", "The second, mine.")}, "amend lesson 2 the new way")
    assert branch.migrate_branch(_git(work), "phase1/late", _hand(tmp_path)) == 0
    assert "The second, mine." in (work / rel).read_text()
    assert "The second, mine." in (work / "docs/lessons_maxim_in_games.md").read_text()


def test_migrate_branch_after_a_clean_merge_of_main(tmp_path):
    _, work = _migrated_main(tmp_path)
    git(work, "fetch", "-q", "origin")
    git(work, "merge", "-q", "--no-edit", "origin/main")  # the marker line is the only line main changed near them
    assert branch.migrate_branch(_git(work), "phase1/late", _hand(tmp_path)) == 0
    _assert_migrated(work)


def test_migrate_branch_refuses_an_edit_section_4_doesnt_allow_by_name(tmp_path, capsys):
    origin, work = _repo(tmp_path, OLD)
    git(work, "checkout", "-q", "-b", "phase1/late")
    _commit(
        work, {"docs/design/decisions/alpha.md": OLD_LOG.replace("It is ruled.", "It is reworded.")}, "edit a ruling"
    )
    other = _clone(tmp_path, origin, "other")
    assert branch.migrate_tree(other, _git(other), _hand(tmp_path)) == 0
    _commit(other, {}, "migrate")
    git(other, "push", "-q", "origin", "main")
    assert branch.migrate_branch(_git(work), "phase1/late", _hand(tmp_path)) == 1
    assert "refused: decision alpha/O1: edited on the branch; a decision never changes" in capsys.readouterr().err


def test_migrate_branch_runs_only_in_the_branchs_worktree(tmp_path, capsys):
    _, work = _migrated_main(tmp_path)
    git(work, "checkout", "-q", "main")
    assert branch.migrate_branch(_git(work), "phase1/late", _hand(tmp_path)) == 1
    assert "--into must be phase1/late's worktree" in capsys.readouterr().err


def test_migrate_runs_once(tmp_path, capsys):
    _, work = _repo(tmp_path, OLD)
    assert branch.migrate_tree(work, _git(work), _hand(tmp_path)) == 0
    assert (work / "docs/lessons_maxim_in_games.md").read_text().split("\n", 1)[1] == OLD_LESSONS
    assert branch.migrate_tree(work, _git(work), _hand(tmp_path)) == 1
    assert "already holds records" in capsys.readouterr().err


def test_the_headers_fixture_matches_the_families():
    roots = {f.root for f in records.FAMILIES}
    assert {k.rsplit("/", 2)[0] + "/" if "decisions/" in k else k.rsplit("/", 1)[0] + "/" for k in HEADERS} == roots


# -- the command line, and the remaining refusals -------------------------------------------------------------------


def test_the_command_line_dispatches_each_command(tmp_path, capsys):
    _, work = _repo(tmp_path, OLD)
    env = isolated_env()
    hand = str(_hand(tmp_path))
    assert cli.main(["migrate", "--hand", hand], cwd=work / "docs", env=env) == 0  # from a subdirectory too
    assert cli.main(["index"], cwd=work, env=env) == 0
    assert "generated file(s)" in capsys.readouterr().out
    assert cli.main(["renumber", "O1"], cwd=work, env=env) == 1
    assert "is not old=new" in capsys.readouterr().err
    assert cli.main(["migrate-branch", "phase1/late", "--into", str(work), "--hand", hand], cwd=work, env=env) == 1


def test_index_refuses_records_whose_family_has_no_header(tmp_path, capsys):
    files = tree(decision("O1", "one"))
    del files["docs/design/decisions/alpha/_header.md"]
    _, work = _repo(tmp_path, files)
    assert cli.index(work, _git(work)) == 1
    assert "is a decision's log but has no _header.md" in capsys.readouterr().err


def test_migrate_reports_a_converter_failure_and_writes_nothing(tmp_path, capsys):
    _, work = _repo(tmp_path, OLD | {"docs/standards_backlog.md": "# Backlog\n"})
    assert branch.migrate_tree(work, _git(work), _hand(tmp_path)) == 1
    assert "no table headed" in capsys.readouterr().err
    assert not (work / "docs/lessons").exists()


def _mapped(base: dict[str, str], head: dict[str, str]):
    main = rmigrate.migrate(base, build.Hand({}, {}, {}, {})).records
    return branch.map_changes(base, head, main=main, hand=build.Hand({}, {}, {}, {}), when="2026-11-26", branch="b")


def test_migrate_branch_maps_a_deleted_gap_and_refuses_a_deleted_lesson():
    gone = OLD | {"docs/known_gaps.md": "# Known gaps\n\nThe head.\n\n**Known gaps:**\n"}
    assert _mapped(OLD, gone).deletes == {"docs/known_gaps/a-gap.md"}  # the branch closed its only gap
    two = OLD | {"docs/known_gaps.md": OLD_GAPS + "- **B gap.** Also measured.\n"}
    changes = _mapped(two, OLD)
    assert changes.deletes == {"docs/known_gaps/b-gap.md"}
    changes = _mapped(
        OLD, OLD | {"docs/lessons_maxim_in_games.md": OLD_LESSONS.split("### 2.", maxsplit=1)[0].rstrip("\n") + "\n"}
    )
    assert changes.refused == ["lessons 2: deleted on the branch; a lesson is never deleted"]


def test_migrate_branch_refuses_a_lesson_edit_section_4_doesnt_allow():
    edited = OLD | {"docs/lessons_maxim_in_games.md": OLD_LESSONS.replace("(2026-11-16)", "(2026-11-18)")}
    changes = _mapped(OLD, edited)
    assert changes.refused == ["lessons 1: the branch changed ['date'], which §4 doesn't allow"]


def test_migrate_branch_maps_a_retitled_lesson_without_moving_its_slug():
    edited = OLD | {"docs/lessons_maxim_in_games.md": OLD_LESSONS.replace("### 1. One (", "### 1. Uno (")}
    (record,) = _mapped(OLD, edited).writes.values()
    assert (record.title, record.slug) == ("Uno", "one")


def test_hunks_name_removed_lines_and_count_an_untracked_file_as_all_added(tmp_path):
    _, work = _repo(tmp_path, {"docs/a.md": "one\n-- two\nthree\n"})
    (work / "docs/a.md").write_text("one\nTWO\nthree\nfour\n")
    (work / "docs/new.md").write_text("x\ny\n")
    hunks = _git(work).hunks("HEAD")
    assert hunks["docs/a.md"] == [rgit.Hunk(("-- two",), (2,)), rgit.Hunk((), (4,))]
    assert hunks["docs/new.md"] == [rgit.Hunk((), (1, 2, 3))]


# -- round 1's folds ---------------------------------------------------------------------------------------------------


def test_two_branches_adding_backlog_rows_conflict_in_its_table_and_the_duplicate_is_caught(tmp_path):
    guards = _load_script("lint_guards")
    _, work = _repo(tmp_path, tree(backlog_row(1, "one")))
    git(work, "checkout", "-q", "-b", "theirs")
    _commit(work, dict([backlog_row(2, "theirs", body="Their check.\n")]), "theirs")
    _regenerate(work)
    _commit(work, {}, "theirs: index")
    git(work, "checkout", "-q", "main")
    git(work, "checkout", "-q", "-b", "mine")
    _commit(work, dict([backlog_row(2, "mine", body="My check.\n")]), "mine")
    _regenerate(work)
    _commit(work, {}, "mine: index")
    assert git(work, "merge", "-q", "theirs", check=False).returncode != 0
    assert "docs/standards_backlog.md" in git(work, "diff", "--name-only", "--diff-filter=U").stdout
    _regenerate(work)
    ids, _ = guards.backlog_numbers("", work)
    assert sorted(ids) == [1, 2, 2]


def test_index_allows_a_line_heads_records_generate_and_nothing_else_does(tmp_path):
    """The HEAD allowance, with bodies that differ, so the deleted gap's line is generated by HEAD alone."""
    _, work = _repo(tmp_path, tree(gap("a-gap", body="**A gap.** One; step 8 closes it.\n"), gap("b-gap")))
    (work / "docs/known_gaps/a-gap.md").unlink()
    _regenerate(work)
    assert "One; step 8" not in (work / "docs/known_gaps.md").read_text()


def test_migrate_branch_refuses_an_edit_main_also_made_since_the_base(tmp_path, capsys):
    origin, work = _migrated_main(tmp_path)
    other = _clone(tmp_path, origin, "amend")
    rel = next(p for p in (other / "docs/lessons").glob("1-*.md")).relative_to(other).as_posix()
    amended = (other / rel).read_text().replace("The first.", "The first, as main corrected it.")
    amended = amended.replace("amended: []", "amended:\n- date: '2026-11-26'\n  why: main's fix")
    _commit(other, {rel: amended}, "main amends lesson 1")
    _regenerate(other)
    _commit(other, {}, "index")
    git(other, "push", "-q", "origin", "main")
    assert branch.migrate_branch(_git(work), "phase1/late", _hand(tmp_path)) == 1
    assert "refused: lessons 1: main changed ['body'] since the branch's base too" in capsys.readouterr().err


def test_migrate_branch_maps_a_row_inserted_mid_log_without_refusing_the_rows_after_it():
    log = OLD_LOG + "| O2 | **Two.** It is ruled too. | owner, 2026-11-16 | §2 | live |\n"
    base = OLD | {"docs/design/decisions/alpha.md": log}
    row = "| O1a | **One and a bit.** Late. | owner, 2026-11-25 | §1 | live |\n"
    head = base | {"docs/design/decisions/alpha.md": log.replace("| O2 |", row + "| O2 |")}
    changes = _mapped(base, head)
    assert changes.refused == []
    assert [r.id for r in changes.writes.values()] == ["O1a"]


def test_hunks_read_names_with_spaces_and_non_ascii_whatever_the_config(tmp_path):
    _, work = _repo(tmp_path, {"docs/caf\u00e9 notes.md": "one\n"})
    git(work, "config", "diff.noprefix", "true")
    (work / "docs/caf\u00e9 notes.md").write_text("one\ntwo\n")
    (work / "docs/a.png").write_bytes(b"\x89PNG\xff\xfe")
    assert _git(work).hunks("HEAD") == {"docs/caf\u00e9 notes.md": [rgit.Hunk((), (2,))]}


def test_renumber_rewrites_an_untracked_files_citation(tmp_path):
    _, work = _repo(tmp_path, tree(decision("O1", "one")))
    git(work, "checkout", "-q", "-b", "phase1/mine")
    _write(work, dict([decision("O5", "mine")]) | {"docs/plans/x.md": "Cites O5.\n"})
    assert cli.renumber(work, _git(work), ["O5=O6"], None) == 0
    assert (work / "docs/plans/x.md").read_text() == "Cites O6.\n"


def test_renumber_refuses_two_ids_to_one_and_a_rename_onto_a_record():
    with pytest.raises(renumber.RenumberError, match="two ids are mapped to O7"):
        renumber.parse_mapping(["O5=O7", "O6=O7"])
    mine_rel, mine = decision("O5", "x")
    main_rel, main = decision("O6", "x", body="**Keep me.**\n")
    with pytest.raises(renumber.RenumberError, match="is another record already"):
        _plan({mine_rel: mine, main_rel: main}, {main_rel}, _own((mine_rel, (), tuple(range(1, 12)))), "O5=O6")


def test_renumber_refuses_cleanly_when_git_fails(tmp_path, capsys):
    _, work = _repo(tmp_path, tree(decision("O1", "one")))
    git(work, "remote", "set-url", "origin", str(tmp_path / "nowhere.git"))
    assert cli.renumber(work, _git(work), ["O1=O2"], None) == 1
    assert "records renumber: git fetch -q failed" in capsys.readouterr().err


def test_renumber_merged_lists_a_hand_resolved_line_holding_both_citations(tmp_path):
    _origin, work = _repo(tmp_path, tree(decision("O1", "one"), ("docs/notes.md", "Shared.\n")))
    git(work, "checkout", "-q", "-b", "phase1/first")
    _commit(work, dict([decision("O5", "first")]) | {"docs/notes.md": "Shared, O5 first.\n"}, "first")
    git(work, "checkout", "-q", "main")
    git(work, "merge", "-q", "--no-ff", "-m", "Merge pull request #1 from x/first", "phase1/first")
    git(work, "checkout", "-q", "-b", "phase1/second", "main~1")
    _commit(work, dict([decision("O5", "second")]) | {"docs/notes.md": "Shared, O5 second.\n"}, "second")
    git(work, "merge", "-q", "main", check=False)  # the second PR's session resolves the line by hand
    _write(work, {"docs/notes.md": "Shared, O5 first and O5 second.\n"})
    _regenerate(work)
    git(work, "add", "-A")
    git(work, "commit", "-q", "--no-edit")
    git(work, "checkout", "-q", "main")
    git(work, "merge", "-q", "--no-ff", "-m", "Merge pull request #2 from x/second", "phase1/second")
    git(work, "push", "-q", "origin", "main")
    git(work, "checkout", "-q", "-b", "phase1/fix-duplicate")
    named = git(work, "log", "--merges", "--first-parent", "--format=%s", "-1", "--diff-filter=A", "--",
                "docs/design/decisions/alpha/O5-second.md").stdout  # fmt: skip
    assert named.startswith("Merge pull request #2 ")  # the command lint_ids' message gives names the PR
    assert cli.renumber(work, _git(work), ["O5=O6"], "2") == 0
    assert (work / "docs/notes.md").read_text() == "Shared, O5 first and O5 second.\n"  # listed, not rewritten
    assert (work / "docs/design/decisions/alpha/O6-second.md").is_file()


def test_renumber_renames_only_the_family_an_id_belongs_to():
    d_rel, d = decision("B5", "a-decision-shaped-like-a-row")
    b_rel, b = backlog_row(5, "a-row")
    hunks = _own((d_rel, (), tuple(range(1, 12))), (b_rel, (), tuple(range(1, 12))))
    writes, report = _plan({d_rel: d, b_rel: b}, set(), hunks, "B5=B6")
    assert report.renamed == [(b_rel, "docs/standards_backlog/B6-a-row.md")]
    assert d_rel not in writes or writes[d_rel] is not None


# -- the remaining branches --------------------------------------------------------------------------------------------


def test_migrate_branch_reads_only_the_old_files_a_side_holds():
    base = {"docs/lessons_maxim_in_games.md": OLD_LESSONS}
    head = {"docs/lessons_maxim_in_games.md": OLD_LESSONS + "\n### 44. Late (2026-11-25)\n\nIt.\n"}
    changes = branch.map_changes(base, head, main=[], hand=build.Hand({}, {}, {}, {}), when="2026-11-26", branch="b")
    assert [r.id for r in changes.writes.values()] == ["44"]
    assert branch.map_changes({}, {}, main=[], hand=build.Hand({}, {}, {}, {}), when="x", branch="b").writes == {}


def test_migrate_branch_refuses_an_edit_of_an_entry_main_no_longer_holds():
    base = {"docs/standards_backlog.md": OLD_BACKLOG}
    head = {"docs/standards_backlog.md": OLD_BACKLOG.replace("| The check. |", "| A new check. |")}
    changes = branch.map_changes(base, head, main=[], hand=build.Hand({}, {}, {}, {}), when="x", branch="b")
    assert changes.refused == ["backlog B1: edited on the branch but not on main"]


def test_migrate_branch_refuses_a_changed_gaps_head():
    head = OLD | {"docs/known_gaps.md": OLD_GAPS.replace("The head.", "A new head.")}
    assert branch.changed_heads(OLD, head, build.Hand({}, {}, {}, {})) == [
        "docs/known_gaps.md: the branch changed its head; make that edit in its _header.md by hand"
    ]


def test_migrate_branch_refuses_during_a_merge(tmp_path, capsys):
    _origin, work = _migrated_main(tmp_path)
    git(work, "fetch", "-q", "origin")
    git(work, "merge", "-q", "--no-commit", "--no-ff", "origin/main", check=False)
    assert branch.migrate_branch(_git(work), "phase1/late", _hand(tmp_path)) == 1
    assert "a merge is in progress: abort it" in capsys.readouterr().err


def test_migrate_branch_reports_an_entry_the_converter_cant_read(tmp_path, capsys):
    origin, work = _repo(tmp_path, OLD)
    git(work, "checkout", "-q", "-b", "phase1/late")
    _commit(work, {"docs/known_gaps.md": OLD_GAPS + "- A gap with no bold lead.\n"}, "a lead-less gap")
    other = _clone(tmp_path, origin, "other")
    assert branch.migrate_tree(other, _git(other), _hand(tmp_path)) == 0
    _commit(other, {}, "migrate")
    git(other, "push", "-q", "origin", "main")
    assert branch.migrate_branch(_git(work), "phase1/late", _hand(tmp_path)) == 1
    assert "has no bold lead and no hand title" in capsys.readouterr().err


def test_index_in_a_repository_with_no_origin_main(tmp_path):
    _, work = _repo(tmp_path, tree(decision("O1", "one")))
    git(work, "remote", "remove", "origin")
    _regenerate(work)


def test_renumber_reads_past_a_deleted_file_and_a_binary_one(tmp_path):
    _, work = _repo(tmp_path, tree(decision("O1", "one"), ("docs/gone.md", "x\n")))
    git(work, "checkout", "-q", "-b", "phase1/mine")
    (work / "docs/gone.md").unlink()
    (work / "docs/a.png").write_bytes(b"\x89PNG\xff\xfe")
    _write(work, dict([decision("O5", "mine")]))
    assert cli.renumber(work, _git(work), ["O5=O6"], None) == 0
    assert (work / "docs/design/decisions/alpha/O6-mine.md").is_file()


def test_renumber_merged_refuses_a_pr_with_no_merge_commit(tmp_path, capsys):
    _, work = _repo(tmp_path, tree(decision("O1", "one")))
    git(work, "fetch", "-q", "origin")
    assert cli.renumber(work, _git(work), ["O1=O2"], "9") == 1
    assert "origin/main has 0 merge commits for PR #9" in capsys.readouterr().err


def test_files_at_reads_markdown_blobs_only(tmp_path):
    _, work = _repo(tmp_path, {"docs/a.md": "a\n", "docs/b.png": "png\n"})
    assert _git(work).files_at("HEAD", ("docs/",)) == {"docs/a.md": "a\n"}
