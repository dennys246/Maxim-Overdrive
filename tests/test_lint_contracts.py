"""scripts/lint_contracts.py: one owner per contract (B36).

Each rule is proven by planting what it forbids: a five-reason copy of a vocabulary in another design, a signature
restated in a plan, a missing, doubled or orphan marker, a fold table and a decision table inside a design. All must go
red, and the real tree must pass.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.test_lint_standards import _load

ROOT = Path(__file__).resolve().parents[1]
lint = _load("lint_contracts")

REGISTRY = """# Contracts

| Contract | Owner | Kind | Restates at |
|---|---|---|---|
| `outcomes.reasons` | `design/placement.md` §2.6 | vocabulary | 3 |
| `log.order` | `design/bounds.md` §6.2 | signature | 1 |
"""
PLACEMENT = """# Placement

## 2. The contract

### 2.6 Outcomes

<!-- contract: outcomes.reasons -->
| Reason | Meaning |
|---|---|
| `timeout` | the call ran out of time |
| `budget` | over budget |
| `parse` | unparseable |
| `reloaded` | the world reloaded |
| `unavailable` | no placement |

### 2.7 Health

A `timeout` here counts against health.
"""
BOUNDS = """# Bounds

## 6. Pipeline

### 6.2 The record

<!-- contract: log.order -->
One ordering key: `(apply_tick, kind_rank, seq)`.
"""


def files(**extra: str) -> dict[str, str]:
    base = {
        "docs/design/contracts.md": REGISTRY,
        "docs/design/placement.md": PLACEMENT,
        "docs/design/bounds.md": BOUNDS,
        "docs/plans/plan.md": "# Plan\n\nSee `design/placement.md` §2.6.\n",
    }
    return {**base, **extra}


def test_a_tree_with_one_owner_per_contract_passes() -> None:
    assert lint.check_contracts(files()) == []


def test_a_copied_vocabulary_in_another_design_fails() -> None:
    copy = "# Agents\n\n## 4. Late\n\nA thought fails as `timeout`, `budget`, `parse`, `reloaded` or `unavailable`.\n"
    problems = lint.check_contracts(files(**{"docs/design/agents.md": copy}))
    assert problems == [
        "docs/design/agents.md:5: restates outcomes.reasons (`timeout`, `budget`, `parse`, `reloaded`); "
        "link to docs/design/placement.md §2.6 instead"
    ]


@pytest.mark.parametrize(("named", "fails"), [(1, False), (2, False), (3, True)])
def test_three_members_in_one_block_restate_and_fewer_reference(named: int, fails: bool) -> None:
    spans = " and ".join(f"`{m}`" for m in ["timeout", "budget", "parse"][:named])
    plan = f"# Plan\n\nThe step handles {spans}.\n"
    assert bool(lint.check_contracts(files(**{"docs/plans/plan.md": plan}))) is fails


def test_members_spread_over_separate_blocks_are_references() -> None:
    plan = "# Plan\n\nOn `timeout` it retries.\n\nOn `budget` it stops.\n\nOn `parse` it logs.\n"
    assert lint.check_contracts(files(**{"docs/plans/plan.md": plan})) == []


def test_a_restated_signature_fails_anywhere_in_scope() -> None:
    roadmap = "# Roadmap\n\n- Order by `(apply_tick, kind_rank, seq)`.\n"
    problems = lint.check_contracts(files(**{"docs/roadmap.md": roadmap}))
    assert problems == [
        "docs/roadmap.md:3: restates log.order (`(apply_tick, kind_rank, seq)`); "
        "link to docs/design/bounds.md §6.2 instead"
    ]


@pytest.mark.parametrize(
    "rel",
    [
        "docs/design/reviews/round/executor.md",
        "docs/design/decisions/agents.md",
        "docs/design/research/notes.md",
        "docs/lessons_maxim_in_games.md",
    ],
)
def test_records_and_files_out_of_scope_may_quote_a_contract(rel: str) -> None:
    quote = "# Record\n\n`timeout`, `budget`, `parse`, `reloaded`, `unavailable`.\n"
    assert lint.check_contracts(files(**{rel: quote})) == []


def test_a_superseded_design_is_history_and_may_restate() -> None:
    old = "# Old\n\n> **Superseded 2026-11-16 by `new.md`.**\n\n`timeout`, `budget`, `parse`.\n"
    assert lint.check_contracts(files(**{"docs/design/old.md": old})) == []


def test_a_contract_without_its_marker_fails() -> None:
    unmarked = PLACEMENT.replace("<!-- contract: outcomes.reasons -->\n", "")
    problems = lint.check_contracts(files(**{"docs/design/placement.md": unmarked}))
    assert problems == [
        "outcomes.reasons: needs exactly one `<!-- contract: outcomes.reasons -->` marker, found at nowhere"
    ]


def test_a_contract_marked_twice_fails() -> None:
    twice = BOUNDS + "\n<!-- contract: outcomes.reasons -->\n`a`, `b`, `c`\n"
    problems = lint.check_contracts(files(**{"docs/design/bounds.md": twice}))
    assert any(p.startswith("outcomes.reasons: needs exactly one") for p in problems)


def test_a_marker_outside_its_section_fails() -> None:
    moved = PLACEMENT.replace(
        "### 2.7 Health\n", "### 2.7 Health\n\n<!-- contract: outcomes.reasons -->\n`x`, `y`, `z`\n"
    )
    moved = moved.replace("<!-- contract: outcomes.reasons -->\n| Reason", "| Reason", 1)
    problems = lint.check_contracts(files(**{"docs/design/placement.md": moved}))
    assert problems == [
        "outcomes.reasons: its marker (docs/design/placement.md:17) is not inside docs/design/placement.md §2.6"
    ]


def test_a_marker_with_no_row_fails() -> None:
    orphan = BOUNDS + "\n## 7. More\n\n<!-- contract: ghost -->\n`a`, `b`, `c`\n"
    problems = lint.check_contracts(files(**{"docs/design/bounds.md": orphan}))
    assert problems == ["docs/design/bounds.md:12: marker ghost has no row in docs/design/contracts.md"]


def test_a_marker_followed_by_a_heading_fails() -> None:
    bare = BOUNDS.replace("One ordering key: `(apply_tick, kind_rank, seq)`.\n", "#### 6.2.1 Next\n")
    problems = lint.check_contracts(files(**{"docs/design/bounds.md": bare}))
    assert problems == ["log.order: no defining block follows its marker (docs/design/bounds.md:7)"]


@pytest.mark.parametrize(
    ("row", "complaint"),
    [
        ("| `x` | design/a.md §1 | vocabulary | 3 |", "a row must read"),
        ("| `x` | `design/a.md` §1 | vocabulary |", "a row must read"),
        ("| `x` | `design/a.md` §1 | list | 3 |", "x's kind is 'list'"),
        (
            "| `outcomes.reasons` | `design/placement.md` §2.6 | vocabulary | 3 |",
            "outcomes.reasons is registered twice",
        ),
    ],
)
def test_a_malformed_registry_row_fails(row: str, complaint: str) -> None:
    problems = lint.check_contracts(files(**{"docs/design/contracts.md": REGISTRY + row + "\n"}))
    assert any(complaint in p for p in problems)


def test_a_missing_registry_fails() -> None:
    tree = files()
    del tree["docs/design/contracts.md"]
    assert "docs/design/contracts.md is missing: B36's contracts have no registry" in lint.check_contracts(tree)


def test_a_vocabulary_of_two_cannot_be_checked() -> None:
    two = PLACEMENT.replace(
        "| `parse` | unparseable |\n| `reloaded` | the world reloaded |\n| `unavailable` | no placement |\n", ""
    )
    problems = lint.check_contracts(files(**{"docs/design/placement.md": two}))
    assert problems == ["outcomes.reasons: a vocabulary needs at least 3 members to check, found ['timeout', 'budget']"]


def test_a_signature_block_without_a_code_span_fails() -> None:
    plain = BOUNDS.replace("One ordering key: `(apply_tick, kind_rank, seq)`.", "One ordering key.")
    assert lint.check_contracts(files(**{"docs/design/bounds.md": plain})) == [
        "log.order: its defining block holds no code span"
    ]


@pytest.mark.parametrize(
    ("block", "found"),
    [
        ("- `a`: one\n- `b`: two, see `x`\n- `c`: three\n", ["a", "b", "c"]),
        ("1. `a`: one\n2. `b`: two\n", ["a", "b"]),
        ("The kinds are `a`, `b` and `a` again.\n", ["a", "b"]),
        ("| K | M |\n|---|---|\n| `a`, `b` | uses `z` |\n", ["a", "b"]),
    ],
)
def test_members_are_the_heads_of_a_list_or_table_and_every_span_of_a_paragraph(block: str, found: list[str]) -> None:
    assert lint.members(lint.Block(0, tuple(block.splitlines())), "vocabulary") == found


def test_a_fenced_block_is_one_block_even_with_blank_lines() -> None:
    text = "```\n`a`\n\n`b`\n```\n\nafter\n"
    assert [b.start for b in lint.blocks(text)] == [0, 6]


@pytest.mark.parametrize(
    ("text", "complaint"),
    [
        ("# D\n\n## Fold table: the review\n\n| Id | Status |\n", "docs/design/d.md:3: a fold table belongs"),
        (
            "# D\n\n## 0. Decisions\n\n| # | Decision | Where |\n|---|---|---|\n| O1 | x | §1 |\n",
            "docs/design/d.md:5: a decision",
        ),
        ("# D\n\n| Id | Ruling (owner) |\n|---|---|\n| T1 | x |\n", "docs/design/d.md:3: a decision table"),
    ],
)
def test_a_fold_or_decision_table_inside_a_design_fails(text: str, complaint: str) -> None:
    problems = lint.check_contracts(files(**{"docs/design/d.md": text}))
    assert any(p.startswith(complaint) for p in problems)


def test_the_records_may_hold_decision_and_fold_tables() -> None:
    record = "# R\n\n| Id | Ruling | Who |\n|---|---|---|\n| O1 | x | owner |\n\n## Fold table\n"
    tree = files(**{"docs/design/decisions/d.md": record, "docs/design/reviews/r/fold.md": record})
    assert lint.check_contracts(tree) == []


def test_a_section_ends_at_the_next_heading_of_its_level() -> None:
    text = "# T\n## 2. A\n### 2.6 B\nx\n#### 2.6.1 C\ny\n### 2.7 D\n"
    assert lint.section_span(text, "2.6") == (2, 6)
    assert lint.section_span(text, "2") == (1, 8)  # to the end, past the last newline
    assert lint.section_span(text, "9") is None


def test_the_real_tree_passes() -> None:
    tree = {p.relative_to(ROOT).as_posix(): p.read_text() for p in sorted((ROOT / "docs").rglob("*.md"))}
    assert lint.check_contracts(tree) == []


SENTENCE = """# Placement

## 2. The contract

### 2.6 Outcomes

- **What the agent sees:** only replies.
<!-- contract: outcomes.reasons: budget timeout parse -->
- **One closed list of `thought_failed` reasons**, owned here: `budget`, `timeout`, `parse`. `call_timeout` is not one.
"""


def test_a_marker_can_name_members_a_sentence_holds() -> None:
    tree = files(**{"docs/design/placement.md": SENTENCE})
    assert lint.check_contracts(tree) == []
    copy = "# Agents\n\nIt fails as `budget`, `timeout` or `parse`.\n"
    assert lint.check_contracts({**tree, "docs/design/agents.md": copy}) == [
        "docs/design/agents.md:3: restates outcomes.reasons (`budget`, `timeout`, `parse`); "
        "link to docs/design/placement.md §2.6 instead"
    ]


def test_naming_the_list_and_another_outcome_is_not_a_restatement() -> None:
    tree = files(**{"docs/design/placement.md": SENTENCE})
    prose = "# Agents\n\nA `thought_failed` record, never a `call_timeout`, and `budget` is one reason.\n"
    assert lint.check_contracts({**tree, "docs/design/agents.md": prose}) == []


def test_a_marker_naming_a_member_its_block_lacks_fails() -> None:
    drift = SENTENCE.replace("parse -->", "parse reloaded -->")
    assert lint.check_contracts(files(**{"docs/design/placement.md": drift})) == [
        "outcomes.reasons: its marker names ['reloaded'], which its block doesn't hold as code spans"
    ]


def test_each_top_level_list_item_is_its_own_block() -> None:
    text = "- `a` one\n  `b` still one\n- `c` two\n1. `d` three\n\npara\n"
    assert [b.start for b in lint.blocks(text)] == [0, 2, 3, 5]


def test_members_in_neighbouring_list_items_are_references() -> None:
    plan = "# Plan\n\n- On `timeout` it retries.\n- On `budget` it stops.\n- On `parse` it logs.\n"
    assert lint.check_contracts(files(**{"docs/plans/plan.md": plan})) == []


def test_a_row_may_raise_how_many_members_restate_it() -> None:
    plan = "# Plan\n\nThe step handles `timeout`, `budget` and `parse`.\n"
    raised = REGISTRY.replace("| vocabulary | 3 |", "| vocabulary | 4 |")
    assert lint.check_contracts(files(**{"docs/plans/plan.md": plan, "docs/design/contracts.md": raised})) == []
    with_four = plan.replace("and `parse`", "`parse` and `reloaded`")
    assert lint.check_contracts(files(**{"docs/plans/plan.md": with_four, "docs/design/contracts.md": raised}))


def test_an_owner_block_may_name_another_contracts_members() -> None:
    ranks = (
        "\n<!-- contract: log.order -->\nRanks `(apply_tick, kind_rank, seq)`: `timeout`, `budget`, `parse` first.\n"
    )
    bounds = BOUNDS.replace(
        "\n<!-- contract: log.order -->\nOne ordering key: `(apply_tick, kind_rank, seq)`.\n", ranks
    )
    assert lint.check_contracts(files(**{"docs/design/bounds.md": bounds})) == []


def test_a_marked_list_defines_as_a_whole() -> None:
    listed = PLACEMENT.replace(
        "| Reason | Meaning |\n|---|---|\n| `timeout` | the call ran out of time |\n| `budget` | over budget |\n"
        "| `parse` | unparseable |\n| `reloaded` | the world reloaded |\n| `unavailable` | no placement |\n",
        "- `timeout`: late\n- `budget`: over\n- `parse`: bad\n",
    )
    assert lint.check_contracts(files(**{"docs/design/placement.md": listed})) == []
