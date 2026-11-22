"""scripts/lint_contracts.py: one owner per contract (B36).

Each rule is proven by planting what it forbids: a copy of a vocabulary in a sentence, a table or one member per
bullet; a signature restated in a plan; a marker that drifted from its text either way; a missing, doubled, misplaced
or orphan marker; a fold table, a decision table and a list of rulings inside a design. All must go red, and the real
tree must pass.
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

- **What the agent sees:** only replies.
<!-- contract: outcomes.reasons: budget timeout parse reloaded unavailable | not: thought_failed call_timeout -->
- **One closed list of `thought_failed` reasons:** `budget`, `timeout`, `parse`, `reloaded`, `unavailable`.
  `call_timeout` is an attempt outcome, not a reason.
- **Retries** are new attempts.

### 2.7 Health

A `timeout` here counts against health.
"""
BOUNDS = """# Bounds

## 6. Pipeline

### 6.2 The record

<!-- contract: log.order: (apply_tick, kind_rank, seq) -->
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


def check(**extra: str) -> list[str]:
    problems: list[str] = lint.check_contracts(files(**extra))
    return problems


def test_a_tree_with_one_owner_per_contract_passes() -> None:
    assert check() == []


def test_a_copy_in_a_sentence_fails() -> None:
    copy = "# Agents\n\n## 4. Late\n\nA thought fails as `timeout`, `budget`, `parse`, `reloaded` or `unavailable`.\n"
    assert check(**{"docs/design/agents.md": copy}) == [
        "docs/design/agents.md:5: restates outcomes.reasons (`budget`, `timeout`, `parse`, `reloaded`); "
        "link to docs/design/placement.md §2.6 instead"
    ]


def test_a_copy_one_member_per_bullet_fails() -> None:
    copy = "# Agents\n\nThe reasons:\n\n- `budget`: over\n- `timeout`: late\n- `parse`: bad\n"
    assert check(**{"docs/design/agents.md": copy}) == [
        "docs/design/agents.md:5: restates outcomes.reasons (`budget`, `timeout`, `parse`); "
        "link to docs/design/placement.md §2.6 instead"
    ]


def test_a_copy_spread_over_table_rows_fails() -> None:
    copy = "# Agents\n\n| Reason | Then |\n|---|---|\n| `budget` | stop |\n| `timeout` | retry |\n| `parse` | log |\n"
    assert len(check(**{"docs/design/agents.md": copy})) == 1


@pytest.mark.parametrize(("named", "fails"), [(1, False), (2, False), (3, True)])
def test_the_rows_count_of_members_in_one_block_restates_and_fewer_references(named: int, fails: bool) -> None:
    spans = " and ".join(f"`{m}`" for m in ["timeout", "budget", "parse"][:named])
    assert bool(check(**{"docs/plans/plan.md": f"# Plan\n\nThe step handles {spans}.\n"})) is fails


def test_members_in_separate_paragraphs_are_references() -> None:
    plan = "# Plan\n\nOn `timeout` it retries.\n\nOn `budget` it stops.\n\nOn `parse` it logs.\n"
    assert check(**{"docs/plans/plan.md": plan}) == []


def test_a_row_may_raise_its_count() -> None:
    plan = "# Plan\n\nThe step handles `timeout`, `budget` and `parse`.\n"
    raised = REGISTRY.replace("| vocabulary | 3 |", "| vocabulary | 4 |")
    assert check(**{"docs/plans/plan.md": plan, "docs/design/contracts.md": raised}) == []
    four = plan.replace("and `parse`", "`parse` and `reloaded`")
    assert check(**{"docs/plans/plan.md": four, "docs/design/contracts.md": raised})


def test_a_copy_in_the_same_list_as_the_owner_item_fails() -> None:
    beside = PLACEMENT.replace("- **Retries** are new attempts.", "- **Retries** on `budget`, `timeout` or `parse`.")
    assert check(**{"docs/design/placement.md": beside}) == [
        "docs/design/placement.md:9: restates outcomes.reasons (`budget`, `timeout`, `parse`); "
        "link to docs/design/placement.md §2.6 instead"
    ]


def test_another_contracts_owner_block_is_still_checked() -> None:
    ranked = BOUNDS.replace(
        "One ordering key: `(apply_tick, kind_rank, seq)`.",
        "Key `(apply_tick, kind_rank, seq)`; `budget`, `timeout`, `parse`.",
    )
    assert len(check(**{"docs/design/bounds.md": ranked})) == 1


def test_a_restated_signature_fails_anywhere_in_scope() -> None:
    roadmap = "# Roadmap\n\n- Order by `(apply_tick, kind_rank, seq)`.\n"
    assert check(**{"docs/roadmap.md": roadmap}) == [
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
    assert check(**{rel: "# Record\n\n`timeout`, `budget`, `parse`, `reloaded`, `unavailable`.\n"}) == []


def test_a_design_with_a_superseded_banner_is_history() -> None:
    old = "# Old\n\n> **Superseded 2026-11-16 by `new.md`.**\n\n## 1. Body\n\n`timeout`, `budget`, `parse`.\n"
    assert check(**{"docs/design/old.md": old}) == []


def test_a_superseded_note_inside_a_section_does_not_exempt_the_design() -> None:
    live = "# Live\n\n## 1. Body\n\n> **Superseded in part:** §1.2.\n\n`timeout`, `budget`, `parse`.\n"
    assert len(check(**{"docs/design/live.md": live})) == 1


def test_a_marker_naming_a_member_its_block_lacks_fails() -> None:
    drift = PLACEMENT.replace("unavailable | not:", "unavailable model_error | not:")
    assert check(**{"docs/design/placement.md": drift}) == [
        "outcomes.reasons: its marker names ['model_error'], which its block doesn't hold as code spans"
    ]


def test_a_member_the_text_gains_without_the_marker_fails() -> None:
    gained = PLACEMENT.replace("`unavailable`.\n", "`unavailable`, `model_error`.\n")
    assert check(**{"docs/design/placement.md": gained}) == [
        "outcomes.reasons: its block holds ['model_error'], which its marker neither names nor excludes"
    ]


def test_a_tables_member_positions_are_its_first_column() -> None:
    table = PLACEMENT.replace(
        "- **One closed list of `thought_failed` reasons:** `budget`, `timeout`, `parse`, `reloaded`, `unavailable`.\n"
        "  `call_timeout` is an attempt outcome, not a reason.\n",
        "| Reason | Then |\n|---|---|\n| `budget` | stop, see `call_timeout` |\n| `timeout` | retry |\n"
        "| `parse` | log |\n| `reloaded` | end |\n| `unavailable` | wait |\n",
    ).replace(" | not: thought_failed call_timeout", "")
    assert check(**{"docs/design/placement.md": table}) == []


def test_a_backticked_exclusion_may_hold_spaces() -> None:
    spaced = PLACEMENT.replace("not: thought_failed call_timeout", "not: thought_failed `(a, b)` call_timeout").replace(
        "is an attempt outcome", "is `(a, b)`'s outcome"
    )
    assert check(**{"docs/design/placement.md": spaced}) == []


def test_a_contract_without_its_marker_fails() -> None:
    unmarked = "\n".join(ln for ln in PLACEMENT.split("\n") if not ln.startswith("<!-- contract:"))
    assert check(**{"docs/design/placement.md": unmarked}) == [
        "outcomes.reasons: needs exactly one `<!-- contract: outcomes.reasons -->` marker, found at nowhere"
    ]


def test_a_contract_marked_twice_fails() -> None:
    twice = BOUNDS + "\n<!-- contract: outcomes.reasons: a b c -->\n`a`, `b`, `c`\n"
    assert any(p.startswith("outcomes.reasons: needs exactly one") for p in check(**{"docs/design/bounds.md": twice}))


def test_a_marker_in_fenced_code_is_quotation() -> None:
    quoted = BOUNDS + "\n```\n<!-- contract: ghost: a b c -->\n```\n"
    assert check(**{"docs/design/bounds.md": quoted}) == []


def test_a_marker_outside_its_section_fails() -> None:
    lines = PLACEMENT.split("\n")
    marker = next(ln for ln in lines if ln.startswith("<!-- contract:"))
    moved = "\n".join(ln for ln in lines if ln != marker) + f"\n{marker}\n`budget`\n"
    assert check(**{"docs/design/placement.md": moved})[0].startswith(
        "outcomes.reasons: its marker (docs/design/placement.md:16) is not inside docs/design/placement.md §2.6"
    )


def test_a_marker_with_no_row_fails() -> None:
    orphan = BOUNDS + "\n## 7. More\n\n<!-- contract: ghost: a b c -->\n`a`, `b`, `c`\n"
    assert check(**{"docs/design/bounds.md": orphan}) == [
        "docs/design/bounds.md:12: marker ghost has no row in docs/design/contracts.md"
    ]


def test_a_marker_followed_by_a_heading_fails() -> None:
    bare = BOUNDS.replace("One ordering key: `(apply_tick, kind_rank, seq)`.\n", "#### 6.2.1 Next\n")
    assert check(**{"docs/design/bounds.md": bare}) == [
        "log.order: no defining block follows its marker (docs/design/bounds.md:7)"
    ]


def test_a_marker_that_names_nothing_fails() -> None:
    empty = BOUNDS.replace("<!-- contract: log.order: (apply_tick, kind_rank, seq) -->", "<!-- contract: log.order -->")
    assert check(**{"docs/design/bounds.md": empty}) == ["log.order: its marker names no members"]


def test_a_vocabulary_of_two_cannot_be_checked() -> None:
    two = PLACEMENT.replace("budget timeout parse reloaded unavailable |", "budget timeout |").replace(
        ", `parse`, `reloaded`, `unavailable`.", "."
    )
    assert check(**{"docs/design/placement.md": two}) == [
        "outcomes.reasons: a vocabulary needs at least 3 members to check, found ['budget', 'timeout']"
    ]


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
    assert any(complaint in p for p in check(**{"docs/design/contracts.md": REGISTRY + row + "\n"}))


def test_a_missing_registry_fails() -> None:
    tree = files()
    del tree["docs/design/contracts.md"]
    assert "docs/design/contracts.md is missing: B36's contracts have no registry" in lint.check_contracts(tree)


@pytest.mark.parametrize(
    ("text", "complaint"),
    [
        ("# D\n\n## Fold table: the review\n\n| Id | Status |\n", "docs/design/d.md:3: a fold table belongs"),
        ("# D\n\n## 0. Decisions\n\n| # | Decision | Where |\n|---|---|---|\n| O1 | x | §1 |\n", "docs/design/d.md:5:"),
        ("# D\n\n| Id | Ruling (owner) |\n|---|---|\n| T1 | x |\n", "docs/design/d.md:3: a decision table"),
        ("# D\n\n## 0. Decisions\n\n- **D20. One truth.** Rigs are tiers.\n", "docs/design/d.md:5: a list of rulings"),
        (
            "# D\n\n## 10. Decisions\n\n**Ruled 2026-11-20:** **D1** the port.\n",
            "docs/design/d.md:5: a list of rulings",
        ),
    ],
)
def test_a_fold_table_decision_table_or_list_of_rulings_inside_a_design_fails(text: str, complaint: str) -> None:
    assert any(p.startswith(complaint) for p in check(**{"docs/design/d.md": text}))


def test_open_questions_are_not_rulings() -> None:
    assert check(**{"docs/design/d.md": "# D\n\n## 11. Open\n\n- **Q1.** The skin point count.\n"}) == []


def test_the_records_may_hold_decision_and_fold_tables() -> None:
    record = (
        "# R\n\n| Id | Ruling | Who |\n|---|---|---|\n| O1 | x | owner |\n\n- **D20. One truth.**\n\n## Fold table\n"
    )
    assert check(**{"docs/design/decisions/d.md": record, "docs/design/reviews/r/fold.md": record}) == []


def test_a_section_ends_at_the_next_heading_of_its_level_and_numbers_match_whole() -> None:
    text = "# T\n## 2. A\n### 2.6 B\nx\n#### 2.6.1 C\ny\n### 2.7 D\n"
    assert lint.section_span(text, "2.6") == (2, 6)
    assert lint.section_span(text, "2") == (1, 8)  # to the end, past the last newline
    assert lint.section_span("# T\n### 2.6 B\n", "2") is None
    assert lint.section_span(text, "9") is None


def test_the_last_block_counts_without_a_trailing_newline() -> None:
    assert lint.blocks("# T\n\nlast `a`") == [lint.Block(0, ("# T",)), lint.Block(2, ("last `a`",))]


def test_a_fenced_block_is_one_block_even_with_blank_lines() -> None:
    assert [b.start for b in lint.blocks("```\n`a`\n\n`b`\n```\n\nafter\n")] == [0, 6]


def test_the_real_tree_passes() -> None:
    tree = {p.relative_to(ROOT).as_posix(): p.read_text() for p in sorted((ROOT / "docs").rglob("*.md"))}
    assert lint.check_contracts(tree) == []


@pytest.mark.parametrize(
    ("marker", "complaint"),
    [
        ("not: thought_failed call_timeout ghost", "its marker excludes ['ghost'], which its block doesn't hold"),
        ("not: thought_failed call_timeout budget", "its marker both names and excludes ['budget']"),
        ("but: thought_failed call_timeout", "its marker reads 'but:' after '|'; only 'not:' may follow it"),
    ],
)
def test_an_exclusion_is_checked_too(marker: str, complaint: str) -> None:
    bad = PLACEMENT.replace("not: thought_failed call_timeout", marker)
    assert check(**{"docs/design/placement.md": bad}) == [f"outcomes.reasons: {complaint}"]


def test_a_tables_header_row_is_not_a_member_position() -> None:
    table = PLACEMENT.replace(
        "- **One closed list of `thought_failed` reasons:** `budget`, `timeout`, `parse`, `reloaded`, `unavailable`.\n"
        "  `call_timeout` is an attempt outcome, not a reason.\n",
        "| `thought_failed` reason | Then |\n|---|---|\n| `budget` | stop |\n| `timeout` | retry |\n"
        "| `parse` | log |\n| `reloaded` | end |\n| `unavailable` | wait |\n",
    ).replace(" | not: thought_failed call_timeout", "")
    assert check(**{"docs/design/placement.md": table}) == []


def test_the_registry_is_out_of_scope() -> None:
    listed = REGISTRY + "\nThe reasons `budget`, `timeout` and `parse` are one example.\n"
    assert check(**{"docs/design/contracts.md": listed}) == []


def test_a_numbered_list_of_rulings_inside_a_design_fails() -> None:
    text = "# D\n\n## 0. Decisions\n\n1. **O3.** The substrate runs outside.\n"
    assert check(**{"docs/design/d.md": text}) == [
        "docs/design/d.md:5: a list of rulings belongs in docs/design/decisions/"
    ]


def test_a_design_without_sections_is_exempt_only_by_a_banner_in_its_lead() -> None:
    late = "# Old\n\nLead.\n\nMore.\n\nBody `timeout`, `budget`, `parse`.\n\n> **Superseded by `x.md`.**\n"
    assert len(check(**{"docs/design/old.md": late})) == 1
    early = "# Old\n\n> **Superseded by `x.md`.**\n\nBody `timeout`, `budget`, `parse`.\n"
    assert check(**{"docs/design/old.md": early}) == []


def test_mentions_scattered_through_a_list_are_references() -> None:
    plan = "# Plan\n\n- On `timeout` it retries.\n- Later, `budget` stops it.\n- Logs show `parse`.\n"
    assert check(**{"docs/plans/plan.md": plan}) == []


def test_a_list_whose_items_lead_with_members_restates() -> None:
    plan = "# Plan\n\n- **`budget`**: over\n- `timeout`, late\n- `parse` is bad\n"
    assert check(**{"docs/plans/plan.md": plan}) == [
        "docs/plans/plan.md:3: restates outcomes.reasons (`budget`, `timeout`, `parse`); "
        "link to docs/design/placement.md §2.6 instead"
    ]


def test_one_list_item_holding_the_count_restates() -> None:
    plan = "# Plan\n\n- First.\n- The reasons are `budget`, `timeout` and `parse`.\n"
    assert len(check(**{"docs/plans/plan.md": plan})) == 1


@pytest.mark.parametrize("count", ["0"])
def test_a_registry_count_below_one_fails(count: str) -> None:
    low = REGISTRY.replace("| vocabulary | 3 |", f"| vocabulary | {count} |")
    assert any("restates at" in p and "at least 1" in p for p in check(**{"docs/design/contracts.md": low}))


def test_a_partial_banner_in_the_lead_does_not_exempt_the_design() -> None:
    part = (
        "# Live\n\n> **Superseded in part (2026-11-16).** §4.1 only.\n\n## 1. Body\n\n`timeout`, `budget`, `parse`.\n"
    )
    assert len(check(**{"docs/design/live.md": part})) == 1


@pytest.mark.parametrize(
    "text",
    [
        "# D\n\n## 10. Decisions\n\n- **Ruled 2026-11-20:** **D1** the port.\n",
        "# D\n\n## 0. Decisions\n\n**D20. One truth.** Rigs are tiers.\n",
    ],
)
def test_a_bulleted_or_bare_ruling_inside_a_design_fails(text: str) -> None:
    assert any("a list of rulings" in p for p in check(**{"docs/design/d.md": text}))


def test_the_lead_of_a_design_without_sections_is_its_first_three_paragraphs() -> None:
    third = "# Old\n\nOne.\n\n> **Superseded by `x.md`.**\n\nBody `timeout`, `budget`, `parse`.\n"
    assert check(**{"docs/design/old.md": third}) == []
    fourth = third.replace("One.\n\n", "One.\n\nTwo.\n\n")
    assert len(check(**{"docs/design/old.md": fourth})) == 1


def test_an_exclusion_outside_a_tables_first_column_is_stale() -> None:
    table = PLACEMENT.replace(
        "- **One closed list of `thought_failed` reasons:** `budget`, `timeout`, `parse`, `reloaded`, `unavailable`.\n"
        "  `call_timeout` is an attempt outcome, not a reason.\n",
        "| Reason | Then |\n|---|---|\n| `budget` | stop, see `call_timeout` |\n| `timeout` | retry |\n"
        "| `parse` | log |\n| `reloaded` | end |\n| `unavailable` | wait |\n",
    ).replace("not: thought_failed call_timeout", "not: call_timeout")
    assert check(**{"docs/design/placement.md": table}) == [
        "outcomes.reasons: its marker excludes ['call_timeout'], which its block doesn't hold"
    ]


def test_a_bare_bar_in_a_marker_says_so() -> None:
    bare = PLACEMENT.replace(" | not: thought_failed call_timeout", " |")
    assert "outcomes.reasons: its marker has a '|' with nothing after it" in check(**{"docs/design/placement.md": bare})
