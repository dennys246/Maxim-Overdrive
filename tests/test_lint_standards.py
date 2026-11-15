"""scripts/lint_standards.py: the checks behind the no-band-aid exemption and the guard citations."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("lint_standards", ROOT / "scripts" / "lint_standards.py")
assert _spec is not None
assert _spec.loader is not None
lint = importlib.util.module_from_spec(_spec)
sys.modules["lint_standards"] = lint
_spec.loader.exec_module(lint)

ROADMAP = """\
## Phase 0: Foundations (done)
## Phase 1: The first visible tile (next)
## Phase 2: Physics breadth (later; in parallel with Phase 3)
"""


def test_the_roadmap_phases_parse():
    assert lint.phases(ROADMAP) == {0: "done", 1: "next", 2: "later"}
    assert lint.phases((ROOT / "docs/roadmap.md").read_text())[0] == "done"


@pytest.mark.parametrize(
    "line",
    [
        "x = 1  # TEMPORARY(phase2): air only conducts; remove when convection lands",
        "# TEMPORARY(phase1/scene): crate hard-coded until the YAML loader exists",
        "// TEMPORARY(phase1): shader clamps glow until HDR tonemapping is set up",
    ],
)
def test_a_well_formed_marker_passes(line):
    assert lint.check_temporary_markers({"src/a.py": line}, ROADMAP) == []


@pytest.mark.parametrize(
    ("line", "complaint"),
    [
        ("# TEMPORARY(soon): fix later please", "must cite a roadmap phase"),
        ("# TEMPORARY(phase9): a phase that does not exist", "lacks"),
        ("# TEMPORARY(phase0): a phase that is already done", "is done"),
        ("# TEMPORARY(phase2)", "needs ': <why"),
        ("# TEMPORARY(phase2): eh", "needs ': <why"),
    ],
)
def test_a_bad_marker_is_reported(line, complaint):
    problems = lint.check_temporary_markers({"src/a.py": line}, ROADMAP)
    assert len(problems) >= 1
    assert any(complaint in p for p in problems), problems
    assert problems[0].startswith("src/a.py:1:")


def test_exempt_files_may_mention_markers():
    assert lint.check_temporary_markers({"CLAUDE.md": "# TEMPORARY(soon): x"}, ROADMAP) == []


STANDARDS = """\
# CLAUDE.md

## Engineering standards

- **Rule one.** Text that wraps
  onto a second line. Guard: `scripts/lint_standards.py::check_guards`
- **Rule two.** Guard: B1, `tests`
- **Rule three.** No guard at all.
- **Rule four.** Guard: `nope/missing.py`
- **Rule five.** Guard: `scripts/lint_standards.py::no_such_symbol`
- **Rule six.** Guard: B99
- **Rule seven.** Guard: someone remembers

## Next section

- not a rule. No guard needed.
"""
BACKLOG = "| B1 | something |\n"


def test_guard_citations_are_checked():
    problems = lint.check_guards(STANDARDS, BACKLOG, ROOT)
    text = "\n".join(problems)
    assert "CLAUDE.md:5" not in text  # rule one: wrapped bullet, real file and symbol
    assert "CLAUDE.md:7" not in text  # rule two: real backlog row and real directory
    assert "CLAUDE.md:8: rule has no 'Guard:'" in text
    assert "CLAUDE.md:9: guard nope/missing.py does not exist" in text
    assert "CLAUDE.md:10: guard scripts/lint_standards.py has no symbol no_such_symbol" in text
    assert "CLAUDE.md:11: backlog row B99" in text
    assert "CLAUDE.md:12: 'Guard:' names neither" in text
    assert len(problems) == 5
    assert "not a rule" not in text


def test_a_missing_standards_section_is_a_finding():
    assert lint.check_guards("# CLAUDE.md\n", BACKLOG, ROOT) == [
        "CLAUDE.md: no '## Engineering standards' section with rule bullets"
    ]


def test_the_repository_itself_passes(capsys):
    assert lint.main(ROOT) == 0, capsys.readouterr().err
