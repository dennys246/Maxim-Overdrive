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
    ],
)
def test_every_citation_spelling_of_a_missing_lesson_fails(text: str, missing: list[int]) -> None:
    files = {ids.LESSONS: LESSONS, "docs/x.md": text}
    problems = ids.check_lessons(files)
    assert [p.split("cites lesson ")[1].split(",")[0] for p in problems] == [str(n) for n in missing]
    assert problems[0].startswith("docs/x.md:1:") or problems[0].startswith("docs/x.md:")


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


def test_without_the_lessons_file_there_is_nothing_to_check() -> None:
    assert ids.check_lessons({"docs/x.md": "lesson 9"}) == []


def test_check_ids_reports_both_families() -> None:
    files = {
        ids.LESSONS: LESSONS,
        "docs/x.md": "lesson 9",
        "docs/design/decisions/a.md": _log("O9 | x | o | §1 | live", "O9 | y | o | §1 | live"),
    }
    assert len(ids.check_ids(files)) == 2


def test_the_real_tree_has_no_collision_and_no_dangling_citation() -> None:
    assert ids.check_ids(repo.tracked_text_files(ROOT)) == []
