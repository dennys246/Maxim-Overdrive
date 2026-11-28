"""scripts/lint_ids.py: record ids two branches may not share, and lesson citations that must resolve."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_load("records")  # lint_ids reads the record files through it
ids = _load("lint_ids")
repo = _load("lint_repo")

HEAD = "| Id | Decision | Who, date | Owner section | Status |\n|---|---|---|---|---|\n"
LESSONS = "# Lessons\n\n### 1. One (2026-11-01)\n\nText.\n\n### 2. Two (2026-11-02)\n\nText.\n"


def _log(*rows: str) -> str:
    return HEAD + "".join(f"| {r} |\n" for r in rows)


def test_one_id_in_two_logs_is_a_collision() -> None:
    files = {
        "docs/design/decisions/a.md": _log("O9 | x | owner | §1 | live"),
        "docs/design/decisions/b.md": _log("O9 | y | owner | §2 | live"),
    }
    problems = ids.check_decisions(files)
    assert len(problems) == 1
    assert "O9 is defined 2 times" in problems[0]
    assert "merged second renumbers" in problems[0]


def test_one_id_twice_in_one_log_is_a_collision() -> None:
    files = {"docs/design/decisions/a.md": _log("D4 | x | owner | §1 | live", "D4 | y | owner | §1 | live")}
    assert len(ids.check_decisions(files)) == 1


def test_a_decision_cross_listed_both_ways_is_one_record() -> None:
    files = {
        "docs/design/decisions/a.md": _log("O3 | x | owner | §1 | live; also in `decisions/b.md`"),
        "docs/design/decisions/b.md": _log("O3 | x | owner | §1 | live; also in `decisions/a.md`"),
    }
    assert ids.check_decisions(files) == []


def test_a_one_sided_cross_listing_is_still_a_collision() -> None:
    files = {
        "docs/design/decisions/a.md": _log("O3 | x | owner | §1 | live; also in `decisions/b.md`"),
        "docs/design/decisions/b.md": _log("O3 | y | owner | §1 | live"),
    }
    assert len(ids.check_decisions(files)) == 1


def test_a_cross_listing_within_one_log_is_still_a_collision() -> None:
    row = "O3 | x | owner | §1 | live; also in `decisions/a.md`"
    assert len(ids.check_decisions({"docs/design/decisions/a.md": _log(row, row)})) == 1


def test_a_prefix_is_one_family_across_designs() -> None:
    files = {
        "docs/design/decisions/sem.md": _log("D21 | x | owner | §1 | live"),
        "docs/design/decisions/world.md": _log("D21 | y | owner | §1 | live"),
    }
    assert len(ids.check_decisions(files)) == 1


def test_restating_rows_and_unnumbered_rulings_are_not_records() -> None:
    files = {
        "docs/design/decisions/a.md": _log(
            "D26 | x | owner | §1 | live",
            "D26\u2013D28 | restated | owner | §1 | restates a",
            "O23, O24, O31 | restated | owner | §1 | restates b",
            "ruled 1 | x | owner | §1 | live",
            "— | x | owner | §1 | live",
        )
    }
    assert ids.check_decisions(files) == []


def test_a_qualified_id_cell_counts_as_its_id() -> None:
    files = {
        "docs/design/decisions/a.md": _log("D12, provisional | x | owner | §1 | live", "D12 | y | owner | §1 | live")
    }
    assert len(ids.check_decisions(files)) == 1


@pytest.mark.parametrize("cell", ["`O9`", "**O9**", "O9 (provisional)", "O9,provisional", "**`O9`**, provisional"])
def test_a_decorated_id_cell_is_still_its_id(cell: str) -> None:
    files = {
        "docs/design/decisions/a.md": _log(f"{cell} | x | owner | §1 | live"),
        "docs/design/decisions/b.md": _log("O9 | y | owner | §1 | live"),
    }
    assert len(ids.check_decisions(files)) == 1


def test_a_hyphenated_id_is_a_record_of_its_own_family() -> None:
    files = {
        "docs/design/decisions/a.md": _log("PH2-S2, re-ruled | x | owner | §1 | live"),
        "docs/design/decisions/b.md": _log("PH2-S2 | y | owner | §1 | live", "S2 | z | owner | §1 | live"),
    }
    problems = ids.check_decisions(files)
    assert len(problems) == 1
    assert "PH2-S2 is defined 2 times" in problems[0]


def test_also_in_counts_only_in_the_status_cell() -> None:
    files = {
        "docs/design/decisions/a.md": _log("O3 | see also in `decisions/b.md` | owner | §1 | live"),
        "docs/design/decisions/b.md": _log("O3 | see also in `decisions/a.md` | owner | §1 | live"),
    }
    assert len(ids.check_decisions(files)) == 1


def test_three_definitions_are_a_collision_even_when_cross_listed() -> None:
    row_a = "O3 | x | owner | §1 | live; also in `decisions/b.md`"
    files = {
        "docs/design/decisions/a.md": _log(row_a),
        "docs/design/decisions/b.md": _log("O3 | x | owner | §1 | live; also in `decisions/a.md`"),
        "docs/design/decisions/c.md": _log("O3 | x | owner | §1 | live; also in `decisions/a.md`"),
    }
    problems = ids.check_decisions(files)
    assert len(problems) == 1
    assert "defined 3 times" in problems[0]


def test_a_roadmap_item_taken_twice_fails() -> None:
    roadmap = "| Id | Item |\n|---|---|\n| OD-I13 | a |\n| `OD-I13` | b |\n| OD-I14 | c |\n| OD-A13 | d |\n"
    assert ids.check_roadmap_ids({ids.ROADMAP: roadmap}) == [
        f"{ids.ROADMAP}: item OD-I13 is defined 2 times (lines 3, 4): two branches took the same id; the one merged "
        "second renumbers its own item and its own citations"
    ]


def test_a_roadmap_cell_that_only_mentions_an_item_is_not_an_item() -> None:
    roadmap = "| Id | Item |\n|---|---|\n| OD-I13 | a |\n| see OD-I13 | b |\n| OD-I13, OD-I14 | c |\nOD-I13 prose\n"
    assert ids.check_roadmap_ids({ids.ROADMAP: roadmap}) == []
    assert ids.check_roadmap_ids({}) == []


def test_files_outside_the_decision_logs_are_not_read() -> None:
    assert ids.check_decisions({"docs/design/other.md": _log("O9 | x | o | §1 | live", "O9 | y | o | §1 | live")}) == []


def test_two_lessons_with_one_number_fail() -> None:
    files = {ids.LESSONS: LESSONS + "\n### 2. Another two (2026-11-03)\n"}
    problems = ids.check_lessons(files)
    assert problems == [
        f"{ids.LESSONS}: two branches took lesson 2: the one merged second renumbers its own lesson "
        "and its own citations"
    ]


@pytest.mark.parametrize(
    ("text", "missing"),
    [
        ("see lesson 7", [7]),
        ("Lesson 7 says", [7]),
        ("lessons 1 and 7", [7]),
        ("lessons 1, 2 and 7", [7]),
        ("lessons 1\u20137", [7]),
        ("lessons 1 to 7", [7]),
        ("lesson §7", [7]),
        ("lessons 1 and §7", [7]),
        ("`lessons_maxim_in_games.md` §7", [7]),
        ("lessons_maxim_in_games.md §7", [7]),
        ("lesson\n7", [7]),
        ("`lessons_maxim_in_games.md` 7", [7]),
        ("`lessons_maxim_in_games.md::7`", [7]),
        ("`lessons_maxim_in_games.md` §1, §7", [7]),
        ("lessons_maxim_in_games.md §1 and §7", [7]),
    ],
)
def test_every_citation_spelling_of_a_missing_lesson_fails(text: str, missing: list[int]) -> None:
    files = {ids.LESSONS: LESSONS, "docs/x.md": text}
    problems = ids.check_lessons(files)
    assert [p.split("cites lesson ")[1].split(",")[0] for p in problems] == [str(n) for n in missing]
    assert problems[0].startswith("docs/x.md:1:")


def test_a_finding_names_the_line_of_its_citation() -> None:
    problems = ids.check_lessons({ids.LESSONS: LESSONS, "docs/x.md": "a\nb\nsee lesson 7\n"})
    assert [p.split(" cites")[0] for p in problems] == ["docs/x.md:3:"]


@pytest.mark.parametrize("text", ["lesson 1, 2026-11-20", "lesson 2 to 2026", "lessons 1 and 2, 12345 cells"])
def test_a_four_digit_number_after_a_separator_ends_the_list(text: str) -> None:
    assert ids.check_lessons({ids.LESSONS: LESSONS, "docs/x.md": text}) == []


def test_a_citation_never_crosses_a_blank_line() -> None:
    assert ids.check_lessons({ids.LESSONS: LESSONS, "docs/x.md": "the lessons\n\n7 of them"}) == []


def test_citations_of_existing_lessons_pass() -> None:
    assert ids.check_lessons({ids.LESSONS: LESSONS, "docs/x.md": "lesson 1, lessons 1 and 2, lesson §2"}) == []


def test_a_test_reason_string_is_read_and_other_strings_are_not() -> None:
    source = (
        "import pytest\n\n\n"
        '@pytest.mark.xfail(strict=True, raises=AssertionError, reason="lesson 9 says")\n'
        "def test_a() -> None:\n"
        '    note = "lesson 8"\n'
        '    pytest.raises(ValueError, match="lesson 7")\n'
    )
    problems = ids.check_lessons({ids.LESSONS: LESSONS, "tests/test_a.py": source})
    assert len(problems) == 1
    assert "cites lesson 9" in problems[0]
    assert "tests/test_a.py:4:" in problems[0]


def test_a_test_with_a_syntax_error_fails_loudly() -> None:
    with pytest.raises(SyntaxError):
        ids.check_lessons({ids.LESSONS: LESSONS, "tests/test_a.py": "def (:\n"})


def test_frozen_files_are_never_read() -> None:
    manifest = "# frozen\nabc123  arms.yaml\ndef456  weights:S:repo@rev:file.gguf\n"
    files = {
        ids.LESSONS: LESSONS,
        "spikes/x/freeze.sha256": manifest,
        "docs/frozen.md": "lesson 9",
        "spikes/x/arms.yaml": "lesson 9",
    }
    assert ids.frozen_files(files) == {"spikes/x/arms.yaml"}
    assert len(ids.check_lessons(files)) == 1  # the docs file still counts
    files["spikes/x/freeze.sha256"] = manifest + "0  ../../docs/frozen.md\n"
    assert "docs/frozen.md" in ids.frozen_files(files)
    assert ids.check_lessons(files) == []  # frozen, so its citation is never read


def test_a_markdown_file_outside_docs_is_not_read() -> None:
    assert ids.check_lessons({ids.LESSONS: LESSONS, "spikes/notes.md": "lesson 9"}) == []


def test_without_the_lessons_file_a_citation_is_a_finding() -> None:
    problems = ids.check_lessons({"docs/a.md": "nothing", "docs/x.md": "x\nlesson 9 and lesson 4"})
    assert problems == [f"{ids.LESSONS} is missing, but 2 citation(s) cite it, first docs/x.md:2 (lesson 9)"]


def test_a_tree_with_no_lessons_and_no_citation_has_nothing_to_check() -> None:
    assert ids.check_lessons({"docs/x.md": "no citation here"}) == []


def test_check_ids_reports_every_family() -> None:
    files = {
        ids.LESSONS: LESSONS,
        ids.ROADMAP: "| OD-I1 | a |\n| OD-I1 | b |\n",
        "docs/x.md": "lesson 9",
        "docs/design/decisions/a.md": _log("O9 | x | o | §1 | live", "O9 | y | o | §1 | live"),
    }
    assert len(ids.check_ids(files)) == 3


def test_the_real_tree_has_no_collision_and_no_dangling_citation() -> None:
    assert ids.check_ids(repo.tracked_text_files(ROOT)) == []
