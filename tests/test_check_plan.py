"""scripts/check_plan.py: the plan must carry every decision, Phase 3 id and open question, within its word budget."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("check_plan", ROOT / "scripts" / "check_plan.py")
assert _spec is not None
assert _spec.loader is not None
check = importlib.util.module_from_spec(_spec)
sys.modules["check_plan"] = check
_spec.loader.exec_module(check)

SOURCES = {
    "docs/design/boundaries.md": (
        "| O1 | one repo |\n\n## 12. Open questions\n\n1. Name?\n2. Two PRs?\n\n## 13. Not settled\n"
    ),
    "docs/design/world_model.md": "- **D20.** One truth.\n\n## 12. Open questions for the owner\n\n1. 0.1 m?\n",
    "docs/design/npcs_and_sem.md": "| O11a | floor |\n\n### 12.1 For the owner\n\n1. **Guests.**\n\n### 12.2 Div\n",
    "docs/roadmap.md": "| OD-A1 | decay |\n\n## Open questions\n\n- Turn length?\n- Copyright?\n",
    "docs/design/tile_and_client.md": "| T1 | camera |\n\n## 9. Open questions\n\n1. Tick?\n\n## 10. Not\n",
    "docs/design/client_rendering.md": "| T2 | moves |\n\n## 10. Open questions for the owner\n\n1. Renderer?\n",
    "docs/design/decisions/boundaries.md": "| O3 | substrate | owner, 2026-11-16 | — | live |\n",
    "docs/design/decisions/npcs_and_sem.md": "| O12 | speed | owner, 2026-11-16 | §4.2 | live |\n",
    "docs/design/decisions/world_model.md": "| D21 | resolution | owner, 2026-11-16 | — | live |\n",
    "docs/design/decisions/tile_and_client.md": "| T3 | tick | owner, 2026-11-18 | §6.1 | live |\n",
    "docs/design/decisions/client_rendering.md": "| T8 | renderer | owner, 2026-11-18 | §7.4 | live |\n",
}
PLAN = """O1, O3, O11a, O12, D20, D21, T1, T2, T3, T8 and OD-A1.

### Open: boundaries §12
1. Name.
2. Two PRs.

### Open: world_model §12
1. 0.1 m.

### Open: npcs_and_sem §12.1
1. Guests.

### Open: tile §9
1. Tick.

### Open: client §10
1. Renderer.

### Open: roadmap
1. Turn length.
2. Copyright.
"""


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    for rel, text in {**SOURCES, check.PLAN: PLAN}.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(text)
    return tmp_path


def test_a_complete_plan_passes(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert check.main(repo) == 0
    assert "PASS (0 finding(s))" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("drop", "complaint"),
    [
        ("O1, ", "O1 is in the sources"),
        ("O3, ", "O3 is in the sources"),
        ("O12, ", "O12 is in the sources"),
        ("D21, ", "D21 is in the sources"),
        ("T3, ", "T3 is in the sources"),
        ("T8 and", "T8 is in the sources"),
        ("O11a, ", "O11a is in the sources"),
        ("D20, ", "D20 is in the sources"),
        ("T1, ", "T1 is in the sources"),
        ("T2, ", "T2 is in the sources"),
        ("### Open: tile §9\n1. Tick.\n", "tile §9 question 1"),
        ("### Open: client §10\n1. Renderer.\n", "client §10 question 1"),
        (" and OD-A1", "OD-A1 is in the sources"),
        ("2. Two PRs.\n", "boundaries §12 question 2"),
        ("1. 0.1 m.\n", "world_model §12 question 1"),
        ("### Open: npcs_and_sem §12.1\n1. Guests.\n", "npcs_and_sem §12.1 question 1"),
        ("2. Copyright.\n", "roadmap question 2"),
    ],
)
def test_a_plan_missing_anything_fails(
    repo: Path, capsys: pytest.CaptureFixture[str], drop: str, complaint: str
) -> None:
    plan = repo / check.PLAN
    assert drop in plan.read_text()
    plan.write_text(plan.read_text().replace(drop, "", 1))
    assert check.main(repo) == 1
    assert complaint in capsys.readouterr().err


def test_a_question_listed_under_another_source_does_not_count(repo: Path) -> None:
    plan = repo / check.PLAN
    plan.write_text(
        plan.read_text()
        .replace("### Open: world_model §12\n1. 0.1 m.\n", "")
        .replace("2. Copyright.", "2. Copyright.\n3. 0.1 m.")
    )
    assert "world_model §12 question 1 is not in the plan" in check.findings(repo)


def test_a_source_without_its_question_section_is_a_finding(repo: Path) -> None:
    (repo / "docs/roadmap.md").write_text("| OD-A1 | decay |\n")
    assert "docs/roadmap.md has no '## Open questions' section" in check.findings(repo)


def test_a_plan_over_its_word_budget_fails(repo: Path) -> None:
    plan = repo / check.PLAN
    plan.write_text(plan.read_text() + " word" * check.WORD_BUDGET)
    assert any("its budget is 2500" in f for f in check.findings(repo))


def test_a_section_ends_at_the_next_heading_of_its_level() -> None:
    text = "## 12. Open\n1. a\n### 12.1 sub\n2. b\n## 13. Next\n3. c\n"
    assert check.section(text, "## 12. Open") == "\n1. a\n### 12.1 sub\n2. b\n"
    assert check.section(text, "### 12.1") == "\n2. b\n"
    assert check.section(text, "## 99") is None


def test_the_real_plan_passes() -> None:
    assert check.findings() == []


def test_the_required_ids_never_shrink() -> None:
    """A decision table that moves, or a source dropped, must not quietly stop the plan from being held to its ids."""
    recorded = (ROOT / "tests/fixtures/check_plan/required_ids.txt").read_text().splitlines()
    floor = {line for line in recorded if line and not line.startswith("#")}
    sources = {s: (ROOT / s).read_text() for s in check.ID_SOURCES}
    required = {f.split()[0] for f in check.missing_ids("", sources)}
    assert floor - required == set()
