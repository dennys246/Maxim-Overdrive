"""The record format, its checks and the migration's round trip (``docs/design/records_layout.md`` §4 to §8, §9 R1, R2).

Each refusal has its own test, and each was proven by deleting the check it names (the commit says which). The round
trip runs over a committed copy of today's four files (``tests/fixtures/records/today/``, at ``a5cf4bd``).
"""

from __future__ import annotations

import ast
import locale
from pathlib import Path
from typing import Any

import pytest
import yaml
from hypothesis import given
from hypothesis import strategies as st

from simcore.adapters.loaders import MAX_FILE_BYTES, read_yaml, read_yaml_text
from simcore.core.refusals import RefusalCode, Refused
from tests._records import (
    ROOT,
    backlog_row,
    decision,
    front,
    gap,
    index,
    lesson,
    lint,
    lint_ids,
    migrate,
    records,
    tree,
)
from tests._records import _load as _load_script

TODAY = ROOT / "tests/fixtures/records/today"
HAND = ROOT / "tests/fixtures/records/hand.yaml"


def _base(files: dict[str, str]) -> Any:
    return lint.Base(files)


def _check(files: dict[str, str], base: dict[str, str] | None = None, *, merging: bool = False) -> list[str]:
    found: list[str] = lint.check_records(files, base=None if base is None else _base(base), merging=merging)
    return found


# -- the loaders' text-level entry point (§4, §7) -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "code"),
    [
        ("a: [1\n", RefusalCode.BAD_SHAPE),
        ("a: 1\na: 2\n", RefusalCode.DUPLICATE_KEY),
        ("a: !!int x\n", RefusalCode.BAD_SHAPE),
        ("a: 2026-02-30\n", RefusalCode.BAD_SHAPE),
        ("[" * 5000, RefusalCode.OVER_BUDGET),
    ],
)
def test_read_yaml_text_refuses_what_the_file_gate_refuses(text, code):
    with pytest.raises(Refused, match=r"^front matter: ") as caught:
        read_yaml_text(text, "front matter")
    assert caught.value.code == code


def test_read_yaml_text_refuses_text_that_is_not_a_str_or_is_too_large():
    with pytest.raises(Refused) as caught:
        read_yaml_text(b"a: 1", "x")  # type: ignore[arg-type]
    assert caught.value.code == RefusalCode.BAD_SHAPE
    with pytest.raises(Refused) as caught:
        read_yaml_text("a" * (MAX_FILE_BYTES + 1), "x")
    assert caught.value.code == RefusalCode.OVER_BUDGET


def test_read_yaml_reads_through_the_text_entry_point_and_names_the_file(tmp_path):
    path = tmp_path / "x.yaml"
    path.write_text("a: 1\na: 2\n")
    with pytest.raises(Refused, match=r"x\.yaml: repeated key"):
        read_yaml(path)
    assert read_yaml_text("a: 1\n", "x") == {"a": 1}


# -- read_record: the one reader (§3, §4) --------------------------------------------------------------------------


def test_a_body_holding_dashes_reads_back_whole():
    rel, text = lesson(3, "conserve", body="Before.\n---\nAfter.\n---\n")
    assert records.read_record(rel, text).body == "Before.\n---\nAfter.\n---\n"


@pytest.mark.parametrize(
    ("change", "match"),
    [
        (lambda t: t.replace("'2026-11-20'", "2026-11-20"), "quoted"),
        (lambda t: t.replace("version: 1", "version: 2"), "version must be 1"),
        (lambda t: t.replace("version: 1", "version: 1\nflavour: x"), "flavour"),
        (lambda t: t.replace("version: 1", "version: 1\nversion: 1"), "repeated key"),
        (lambda t: "\n" + t, "begins with a line"),
        (lambda t: t.replace("---\nText", "Text"), "never ends"),
        (lambda t: t.replace("slug: conserve", "slug: other"), "name the file"),
    ],
)
def test_the_reader_refuses_a_malformed_record(change, match):
    rel, text = lesson(3, "conserve")
    with pytest.raises(Refused, match=match):
        records.read_record(rel, change(text))


def test_a_gap_whose_id_is_not_its_slug_is_refused():
    rel, text = gap("a-gap")
    with pytest.raises(Refused, match="id is its slug"):
        records.read_record("docs/known_gaps/a-gap.md", text.replace("id: a-gap", "id: other-gap"))
    assert records.read_record(rel, text).id == "a-gap"


def test_a_slug_id_makes_a_valid_file_name():
    rel, text = decision("d26-to-d28", "d26-to-d28", log="tile_and_client", restates=["CLAUDE.md"])
    assert rel == "docs/design/decisions/tile_and_client/d26-to-d28.md"
    assert records.read_record(rel, text).log == "tile_and_client"


def test_a_path_outside_the_record_directories_is_not_a_record():
    for rel in ("docs/lessons/_header.md", "docs/design/decisions/alpha.md", "docs/lessons/x/1-a.md", "docs/a.md"):
        assert records.family_of(rel) is None
        with pytest.raises(Refused, match="not in a record directory"):
            records.read_record(rel, "")


def _valid(family: str) -> tuple[str, str]:
    return {"lessons": lesson(3, "conserve"), "decisions": decision("O1", "one"), "gaps": gap("a-gap"),
            "backlog": backlog_row(1, "a-rule")}[family]  # fmt: skip


@pytest.mark.parametrize("family", [f.name for f in records.FAMILIES])
def test_every_field_refuses_each_value_its_converter_lists(family):
    rel, text = _valid(family)
    head, _body = records.split_record(rel, text)
    doc = yaml.safe_load(head)
    fmt = records.BY_NAME[family].format
    tried = 0
    for f in fmt.schema.fields:
        for bad, _code in f.convert.bad:
            if f.name == "legacy":
                continue
            raw = {**doc, f.name: bad}
            with pytest.raises(Refused):
                fmt.read(raw, rel)
            tried += 1
    assert tried >= 3 * len(fmt.schema.fields) - 6  # every field but legacy contributes refusals


@given(
    title=st.text(st.characters(codec="utf-8", exclude_categories=("Cs", "Cc", "Zl", "Zp")), min_size=1, max_size=80)
    .map(str.strip)
    .filter(lambda t: bool(t) and not set(t) & set(records._NOT_IN_A_LINE)),
    body=st.text(max_size=300),
)  # fmt: skip
def test_record_text_is_the_readers_inverse(title, body):
    rel, text = lesson(7, "seven", body=body, title=title)
    record = records.read_record(rel, text)
    assert records.read_record(rel, records.record_text(record)) == record


# -- generated files (§6) --------------------------------------------------------------------------------------------


def _sample() -> dict[str, str]:
    return tree(
        lesson(1, "one"),
        lesson(2, "two", section="Time"),
        decision("O1", "one"),
        decision("O2", "two", supersedes=["O1"]),
        decision("O3", "three", also_in=["beta"]),
        gap("a-gap"),
        backlog_row(1, "a-rule"),
    )


def test_status_is_derived_from_the_later_ruling():
    files = _sample()
    assert (
        "| O1 | **A ruling.** Its text. | owner, 2026-11-20 | §1 | superseded by O2 |"
        in files["docs/design/decisions/alpha.md"]
    )
    assert (
        "| O3 | **A ruling.** Its text. | owner, 2026-11-20 | §1 | live; also in `decisions/beta.md` |"
        in files["docs/design/decisions/alpha.md"]
    )
    assert (
        "| O3 | **A ruling.** Its text. | owner, 2026-11-20 | §1 | live; also in `decisions/alpha.md` |"
        in files["docs/design/decisions/beta.md"]
    )
    assert files["docs/generated/decisions_index.md"].startswith("<!-- Generated by `scripts/records.py index`")


def test_generation_is_byte_identical_in_other_locales():
    first = _sample()
    was = locale.setlocale(locale.LC_ALL)  # the process's locale, restored whatever happens: open() reads by it
    try:
        for name in ("C", "C.UTF-8", "en_US.UTF-8", "de_DE.UTF-8", "tr_TR.UTF-8"):
            try:
                locale.setlocale(locale.LC_ALL, name)
            except locale.Error:  # not installed on this machine; the others still run
                continue
            assert _sample() == first
    finally:
        locale.setlocale(locale.LC_ALL, was)


GENERATORS = ("records.py", "records_index.py")
# What generation may never read (§6): a clock, a locale, the environment, the process. Time zones are covered by
# construction: nothing here can read one (the tests may not touch the clock either, test_determinism).
FORBIDDEN = ("import time", "from time", "datetime.now", "datetime.today", "date.today", "import locale",
             "from locale", "os.environ", "getenv", "platform", "getpid")  # fmt: skip


def test_generation_reads_no_clock_locale_or_environment():
    for name in GENERATORS:
        source = (ROOT / "scripts" / name).read_text(encoding="utf-8")
        tree = ast.parse(source)
        body = "\n".join(
            ast.get_source_segment(source, node) or ""
            for node in tree.body
            if not (isinstance(node, ast.If) and "__main__" in (ast.get_source_segment(source, node.test) or ""))
        )  # the command line's entry point hands the environment to git, never to generation
        assert [f for f in FORBIDDEN if f in body] == [], name


def test_an_edit_inside_an_existing_entry_is_a_hand_edit_not_a_stale_file():
    files = _sample()
    files["docs/standards_backlog.md"] = files["docs/standards_backlog.md"].replace("The check.", "Edited.")
    (finding,) = _check(files)
    assert "it holds '| B1 | A rule | Edited. | open |', which no record generates: a hand edit" in finding


def test_a_generated_file_that_is_only_stale_says_to_run_index():
    files = _sample()
    rel, text = backlog_row(1, "a-rule", body="A new check.\n")
    assert _check({**files, rel: text}, files) == [  # the old line is the base's: stale, not a hand edit
        "docs/standards_backlog.md differs from its regeneration: it is stale: run `scripts/records.py index`"
    ]


def test_a_line_the_base_generated_is_stale_not_a_hand_edit():
    base = _sample()
    branch = {k: v for k, v in base.items() if k != "docs/known_gaps/a-gap.md"}  # a deleted gap, not regenerated
    (finding,) = _check(branch, base)
    assert finding.endswith("it is stale: run `scripts/records.py index`")


def test_a_generated_file_holding_an_entry_no_record_holds_names_migrate_branch():
    files = _sample()
    files["docs/design/decisions/alpha.md"] += "| O9 | **Hand-made.** | owner, 2026-11-20 | — | live |\n"
    (finding,) = _check(files)
    assert "'| O9 | **Hand-made.** | owner, 2026-11-20 | — | live |', which no record generates" in finding
    assert "migrate-branch <branch> --into" in finding


def test_a_missing_generated_file_is_a_finding():
    files = _sample()
    del files["docs/known_gaps.md"]
    assert _check(files) == ["docs/known_gaps.md is missing: run `scripts/records.py index`"]


def test_records_with_no_header_are_a_finding():
    files = tree(lesson(1, "one"), generated=False)
    del files["docs/lessons/_header.md"]
    assert any("holds records but no _header.md" in p for p in _check(files))


# -- changes against the base (§4, §5) -----------------------------------------------------------------------------


def _changed(item: tuple[str, str], new_text: str) -> tuple[dict[str, str], dict[str, str]]:
    base = tree(item, lesson(9, "nine"))
    return base, tree((item[0], new_text), lesson(9, "nine"))


@pytest.mark.parametrize(
    ("item", "edit", "match"),
    [
        (decision("O1", "one"), lambda t: t.replace("Its text.", "New text."), "a decision never changes"),
        (lesson(1, "one"), lambda t: t.replace("Text.", "New."), "without a new amended entry"),
        (lesson(1, "one"), lambda t: t.replace("'2026-11-20'\nsection", "'2026-11-21'\nsection"), "only its body"),
        (backlog_row(1, "a-rule"), lambda t: t.replace("rule: A rule", "rule: Another"), "only its body, lands_with"),
    ],
)
def test_a_change_section_4_doesnt_allow_is_refused(item, edit, match):
    base, branch = _changed(item, edit(item[1]))
    assert any(match in p for p in _check(branch, base)), _check(branch, base)


def test_a_lesson_change_with_a_new_amended_entry_is_allowed_and_its_trail_only_grows():
    rel, old = lesson(1, "one", amended=({"date": "2026-11-21", "why": "a fix"},))
    new = old.replace("Text.", "New.").replace("why: a fix", "why: a fix\n- date: '2026-11-22'\n  why: reworded")
    base, branch = _changed((rel, old), new)
    assert _check(branch, base) == []
    cut = new.replace("- date: '2026-11-21'\n  why: a fix\n", "")
    base, branch = _changed((rel, old), cut)
    assert any("only grows" in p for p in _check(branch, base))


D = "**done in part** (x)."  # the prose the new status must agree with


def test_allowed_changes_pass():
    for item, edit in (
        (backlog_row(1, "a"), lambda t: t.replace("status: open", "status: done in part").replace("The check.", D)),
        (gap("a-gap"), lambda t: t.replace("It is measured.", "It is measured again.")),
    ):  # fmt: skip
        base, branch = _changed(item, edit(item[1]))
        assert _check(branch, base) == []


@pytest.mark.parametrize("item", [decision("O1", "one"), lesson(1, "one"), backlog_row(1, "a-rule")])
def test_a_record_other_than_a_gap_is_never_deleted(item):
    base = tree(item, lesson(9, "nine"))
    assert any("is never deleted" in p for p in _check(tree(lesson(9, "nine")), base))


def test_a_gap_may_be_deleted():
    base = tree(gap("a-gap"), lesson(9, "nine"))
    assert _check(tree(lesson(9, "nine")), base) == []


def test_unknown_and_legacy_are_the_migrations_alone():
    base = tree(lesson(9, "nine"))
    assert _check(tree(lesson(9, "nine"), lesson(10, "ten", date="unknown")), {}) == []  # at the migration
    found = _check(tree(lesson(9, "nine"), lesson(10, "ten", date="unknown")), base)
    assert any("date is unknown, but only a migrated record may hold unknown" in p for p in found)
    found = _check(tree(lesson(9, "nine"), lesson(10, "ten", legacy={"heading_tail": ", x"})), base)
    assert any("only the migration writes legacy" in p for p in found)


def test_removing_legacy_is_allowed_even_from_a_decision():
    rel, text = decision("O1", "one", legacy={"rows": [{"log": "alpha", "position": 1}]})
    base = tree((rel, text))
    assert _check(tree(decision("O1", "one")), base) == []


def test_a_duplicates_rename_is_allowed_only_while_the_base_holds_two():
    two = tree(decision("O1", "one"), decision("O1", "uno", log="beta"))
    renamed = tree(decision("O1", "one"), decision("O2", "uno", log="beta"))
    assert not any("never deleted" in p for p in _check(renamed, two))
    one = tree(decision("O1", "one"))
    assert any("never deleted" in p for p in _check(tree(decision("O2", "one")), one))


def test_the_change_check_refuses_during_an_uncommitted_merge():
    files = _sample()
    assert _check(files, files, merging=True)[-1].startswith("records: the change check refuses to run during")


# -- one owner per fact (§4) ---------------------------------------------------------------------------------------


def test_a_field_that_disagrees_with_the_prose_it_duplicates_is_refused():
    gate = "tests/test_x.py::test_y"
    files = tree(gap("a-gap", gate=gate, body=f"**A gap.** Red gate: `{gate}`; step 8 closes it.\n"))
    assert _check(files) == []
    files = tree(gap("a-gap", gate=gate))
    assert any(f"gate {gate} is not what its body names" in p for p in _check(files))
    files = tree(gap("a-gap", closes_at="step 9"))
    assert any("closes_at step 9 is not what its body names" in p for p in _check(files))
    files = tree(backlog_row(1, "a-rule", status="done"))
    assert any("status done but its prose says open" in p for p in _check(files))


@pytest.mark.parametrize(
    ("check", "lands_with", "stated"),
    [
        ("The check.", "open", ("open", None)),
        ("The check.", "open; trigger: x", ("open", None)),
        ("The check.", "**done** (first green run at x)", ("done", "first green run at x")),
        ("The check.", "**done in part** (`a`): more", ("done in part", "`a`")),
        ("**done** for enumerations (phase1/b): still review's", "`phase1/b`", ("done in part", "phase1/b")),
        ("**done**: all of it.", "`phase1/c`", ("done", "`phase1/c`")),
        ("The check.", "Phase 1 step 5a", ("unknown", None)),
        ("(1) done; (2) open.", None, ("unknown", None)),
    ],
)
def test_a_backlog_rows_prose_states_its_status_one_way(check, lands_with, stated):
    assert records.stated_status(check, lands_with) == stated


# -- citations under docs/maxim_upstream/ (§5) -------------------------------------------------------------------------


def test_an_upstream_draft_may_cite_only_a_lesson_on_the_base():
    base = tree(lesson(9, "nine"), ("docs/maxim_upstream/a.md", "See lesson 9.\n"))
    branch = tree(lesson(9, "nine"), lesson(10, "ten"), ("docs/maxim_upstream/a.md", "See lesson 9 and lesson 10.\n"))
    (finding,) = _check(branch, base)
    assert finding.startswith("docs/maxim_upstream/a.md:1: cites lesson 10, which is not on the base")


# -- relations (§4, §7) ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("over", "match"),
    [
        ({"amends": ["O9"]}, "amends names O9, which no decision record holds"),
        ({"restates": ["docs/nowhere.md"]}, "neither a decision id nor a repository path"),
        ({"restates": ["docs/a.md §4"]}, "has no section §4"),
        ({"amended_by_external": [{"path": "docs/a.md", "ruling": "7"}]}, "ruling 7 of docs/a.md, which doesn't exist"),
    ],
)
def test_a_relation_naming_nothing_is_refused(over, match):
    files = tree(decision("O1", "one", **over), ("docs/a.md", "# A\n\n## 3. Three\n\n| 6 | x |\n"))
    assert any(match in p for p in _check(files)), _check(files)


def test_relations_naming_what_exists_pass():
    over: dict[str, Any] = {
        "amends": ["O2"],
        "restates": ["docs/a.md §3"],
        "amended_by_external": [{"path": "docs/a.md", "ruling": "6"}],
    }
    files = tree(
        decision("O1", "one", **over), decision("O2", "two"), ("docs/a.md", "# A\n\n## 3. Three\n\n| 6 | x |\n")
    )
    assert _check(files) == []


def test_a_cycle_among_relations_is_refused():
    files = tree(decision("O1", "one", amends=["O2"]), decision("O2", "two", supersedes=["O1"]))
    assert "decision O1 reaches itself through its relations" in _check(files)


def test_a_record_over_its_familys_budget_is_refused():
    files = tree(lesson(1, "one", body="word " * 501 + "\n"))
    assert any("501 words; a lesson record's budget is 500" in p for p in _check(files))


# -- ids and citations, read from the records (§5, §7) ----------------------------------------------------------------


def test_two_records_with_one_id_are_a_duplicate_naming_both():
    files = tree(decision("O1", "one"), decision("O1", "uno", log="beta"), lesson(4, "a"), lesson(4, "b"))
    found = lint_ids.check_ids(files)
    assert any(
        "decisions id O1 is held by 2 records" in p and "beta/O1-uno.md" in p and "renumber O1=" in p for p in found
    )
    assert any("lessons id 4 is held by 2 records" in p for p in found)


def test_slug_ids_repeat_across_logs_without_a_duplicate():
    files = tree(decision("the-split", "the-split"), decision("the-split", "the-split", log="beta"))
    assert lint_ids.check_decisions(files) == []


SPELLINGS = (
    "lesson 3", "Lesson 3", "lessons 3 and 4", "lessons 3, 4 and 5", "lessons 3\u20135", "lessons 3 to 5",
    "lesson §3", "`lessons_maxim_in_games.md` §3", "lessons_maxim_in_games.md::3", "lessons_maxim_in_games.md §3, §4",
)  # fmt: skip


@pytest.mark.parametrize("spelling", SPELLINGS)
def test_lesson_citations_in_every_spelling_resolve_against_the_records(spelling):
    lessons = [lesson(n, f"l{n}") for n in (3, 4, 5)]
    assert lint_ids.check_lessons(tree(*lessons, ("docs/a.md", f"As {spelling} says.\n"))) == []
    missing = tree(*lessons[1:], lesson(6, "l6"), ("docs/a.md", f"As {spelling} says.\n"))
    assert any("cites lesson 3, which no lesson has" in p for p in lint_ids.check_lessons(missing))


def test_a_tests_reason_string_cites_against_the_records_too():
    marker = '@pytest.mark.xfail(strict=True, reason="lesson 8", raises=AssertionError)'
    test = f"import pytest\n\n{marker}\ndef test_x():\n    pass\n"
    assert any("cites lesson 8" in p for p in lint_ids.check_lessons(tree(lesson(3, "l3"), ("tests/test_x.py", test))))


def test_lint_guards_reads_backlog_ids_from_the_records(tmp_path):
    guards = _load_script("lint_guards")
    for rel, text in (backlog_row(1, "a"), backlog_row(1, "b"), backlog_row(2, "c")):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(text)
    ids, source = guards.backlog_numbers("| B7 | table |\n", tmp_path)
    assert (sorted(ids), source) == ([1, 1, 2], "docs/standards_backlog/")
    problems, _, _ = guards.check_guards("## Engineering standards\n\n- **A rule.** Guard: B2\n", "", tmp_path)
    assert any(
        "B1 is defined 2 times: the branch merged second runs `scripts/records.py renumber B1=" in p for p in problems
    )


# -- stage 1 of the migration, on a copy of today's four files (§8, §9 R2) ------------------------------------------


def _today() -> dict[str, str]:
    return {p.relative_to(TODAY).as_posix(): p.read_text(encoding="utf-8") for p in sorted(TODAY.rglob("*.md"))}


def _migrated() -> Any:
    return migrate.migrate(_today(), migrate.read_hand(read_yaml(HAND)))


def test_the_migration_round_trips_todays_four_files_byte_for_byte():
    today, result = _today(), _migrated()
    texts = {r.path: records.record_text(r) for r in result.records}
    reread, problems = records.load_records(texts)
    assert problems == []
    assert reread == sorted(result.records, key=lambda r: r.path)
    headers = {k.rsplit("/", 1)[0] + "/": v for k, v in result.headers.items()}
    out, missing = index.generate(reread, headers)
    assert missing == []
    for path, original in today.items():
        marker, rest = out[path].split("\n", 1)
        assert marker.startswith("<!-- Generated by `scripts/records.py index`")
        assert rest == original, path
    assert set(out) - set(today) == {"docs/generated/decisions_index.md"}


def test_the_migrated_tree_passes_every_record_check():
    result = _migrated()
    files = {r.path: records.record_text(r) for r in result.records} | result.headers
    names = ("CLAUDE.md", "docs/design/reviews/docs_contracts/rulings.md")
    repo = {p: (ROOT / p).read_text(encoding="utf-8") for p in names}
    repo |= {p.relative_to(ROOT).as_posix(): p.read_text(encoding="utf-8") for p in (ROOT / "docs/design").glob("*.md")}
    recs, _ = records.load_records(files)
    files |= index.generate(recs, index.headers_of(files))[0] | repo
    assert _check(files) == []
    assert lint_ids.check_decisions(files) == []


def test_the_budgets_are_each_familys_longest_record_rounded_up_to_the_next_hundred():
    result = _migrated()
    for family in records.FAMILIES:
        longest = max(records.words(r.body) for r in result.records if r.family == family.name)
        assert family.budget_words == (longest // 100 + 1) * 100, (family.name, longest)


def test_front_matter_dates_are_quoted_strings():
    result = _migrated()
    text = records.record_text(next(r for r in result.records if r.family == "lessons"))
    assert "date: '2026-11-16'" in text
    assert front(date="2026-11-16").count("'2026-11-16'") == 1


# -- the remaining refusals and the command lines ----------------------------------------------------------------------


def test_a_list_field_over_its_count_and_a_title_with_no_slug_are_refused():
    rel, text = decision("O1", "one", amends=[f"O{n}" for n in range(2, 70)])
    with pytest.raises(Refused, match="holds at most 64 items"):
        records.read_record(rel, text)
    with pytest.raises(Refused, match="no slug can be made"):
        records.slugify("§ — ¶")


def test_a_refused_record_is_a_finding_not_a_crash():
    rel, text = lesson(1, "one")
    files = tree(generated=False) | {rel: text.replace("'2026-11-20'", "2026-11-20")}
    found, problems = records.load_records(files)
    assert found == []
    assert problems[0].startswith("docs/lessons/1-one.md.date must be a quoted")


def test_prose_saying_done_in_part_agrees_only_with_that_status():
    body = "**done in part** (step 4).\n"
    assert _check(tree(backlog_row(1, "a", status="done in part", body=body))) == []
    assert any("prose says done in part" in p for p in _check(tree(backlog_row(1, "a", status="done", body=body))))


def test_without_lesson_records_the_base_lessons_come_from_its_lessons_file():
    base = {"docs/lessons_maxim_in_games.md": "### 3. Three (2026-11-01)\n", "docs/maxim_upstream/a.md": ""}
    branch = tree(lesson(3, "three"), ("docs/maxim_upstream/a.md", "As lesson 3 says.\n"))
    assert _check(branch, base) == []


def test_a_restatement_of_a_decision_id_names_it():
    files = tree(decision("O1", "one"), decision("o1-again", "o1-again", restates=["O1"]))
    assert _check(files) == []


def test_a_cycle_through_a_third_ruling_is_found_once_per_member():
    files = tree(
        decision("O1", "one", amends=["O2"]),
        decision("O2", "two", amends=["O3"]),
        decision("O3", "three", amends=["O1", "O2"]),
    )
    cycles = [p for p in _check(files) if "reaches itself" in p]
    assert cycles == [f"decision O{n} reaches itself through its relations" for n in (1, 2, 3)]


def test_lint_records_runs_alone_on_this_repository():
    assert lint.main(["--base", "HEAD"], ROOT) == 0
    assert lint.main(["--base", "no-such-ref"], ROOT) == 1


# -- round 1's folds: each refusal it named, now with a test that fails without it ------------------------------------


def test_rewriting_an_existing_records_legacy_is_refused():
    rel, text = decision("O1", "one", legacy={"rows": [{"log": "alpha", "position": 1}]})
    base = tree((rel, text), lesson(9, "nine"))
    moved = text.replace("position: 1", "position: 2")
    assert any("only the migration writes legacy" in p for p in _check(tree((rel, moved), lesson(9, "nine")), base))


def test_a_duplicate_fix_must_leave_one_record():
    two = tree(decision("O1", "one"), decision("O1", "uno", log="beta"))
    assert sum("never deleted" in p for p in _check(tree(), two)) == 2


def test_amended_by_external_is_the_migrations_alone():
    rulings = ("docs/r/rulings.md", "| 41 | x |\n")
    base = tree(lesson(9, "nine"), rulings)
    added = decision("O2", "two", amended_by_external=[{"path": "docs/r/rulings.md", "ruling": "41"}])
    found = _check(tree(lesson(9, "nine"), added, rulings), base)
    assert any("only the migration writes amended_by_external" in p for p in found)


def test_an_upstream_citation_already_on_the_base_is_not_a_new_one():
    base = tree(lesson(9, "nine"), ("docs/maxim_upstream/a.md", "As lesson 12 shows.\n"))
    branch = tree(lesson(9, "nine"), ("docs/maxim_upstream/a.md", "As lesson 12 shows.\nMore.\n"))
    assert _check(branch, base) == []


@pytest.mark.parametrize("bad", ["a\x85b", "a\u2028b", "a|b"])
def test_a_title_holding_a_yaml_line_break_or_a_cell_separator_is_refused(bad):
    rel, text = lesson(7, "seven")
    raw = {**yaml.safe_load(records.split_record(rel, text)[0]), "title": bad}  # YAML itself folds \x85 on load
    with pytest.raises(Refused, match="one line"):
        records.LESSON.read(raw, rel)


def test_a_qualifier_is_one_of_todays_standings():
    rel, text = decision("D12", "d12", qualifier="superseded")
    with pytest.raises(Refused, match="must be one of"):
        records.read_record(rel, text)


def test_the_fixtures_equal_the_files_they_copy():
    for path in Path(TODAY).rglob("*.md"):
        rel = path.relative_to(TODAY).as_posix()
        assert path.read_bytes() == (ROOT / rel).read_bytes(), f"{rel} changed on main: recopy the fixtures"
    copied = {p.relative_to(TODAY).as_posix() for p in TODAY.rglob("*.md")}
    logs = {p.relative_to(ROOT).as_posix() for p in (ROOT / "docs/design/decisions").glob("*.md")}
    assert logs <= copied, "a decision log was added on main: copy it into the fixtures"


# -- the remaining branches --------------------------------------------------------------------------------------------


def test_prose_agreement_stops_once_the_generator_leaves_todays_form(monkeypatch):
    monkeypatch.setattr(lint, "TODAYS_FORM", False)
    assert lint.prose_agrees(records.load_records(tree(backlog_row(1, "a", status="done"), generated=False))[0]) == []


def test_a_diamond_of_relations_is_no_cycle():
    files = tree(
        decision("O1", "one", amends=["O2", "O3"]),
        decision("O2", "two", amends=["O4"]),
        decision("O3", "three", amends=["O4"]),
        decision("O4", "four"),
    )
    assert _check(files) == []


def test_the_report_prints_each_finding_and_the_verdict(capsys):
    assert lint.report(["a finding"]) == 1
    assert lint.report([]) == 0
    out = capsys.readouterr()
    assert out.err == "a finding\n"
    assert out.out == "lint_records: FAIL (1 finding(s))\nlint_records: PASS (0 finding(s))\n"


def test_a_header_outside_a_family_directory_is_not_a_family_header():
    assert index.headers_of({"docs/other/_header.md": "x", "docs/lessons/_header.md": "y"}) == {"docs/lessons/": "y"}
