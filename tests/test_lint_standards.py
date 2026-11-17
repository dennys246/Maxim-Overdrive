"""scripts/lint_standards.py: the checks behind the no-band-aid exemption, guard citations and the coverage ratchet."""

from __future__ import annotations

import importlib.util
import subprocess
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
- Temporary: src/a.py clamps glow until HDR lands.
## Phase 2: Physics breadth (later; in parallel with Phase 3)
- Temporary: src/a.py and src/b.py.
## Standing rules
- src/c.py is mentioned here, outside any phase.
"""


def test_the_roadmap_phases_parse():
    sections = lint.phase_sections(ROADMAP)
    assert {n: status for n, (status, _) in sections.items()} == {0: "done", 1: "next", 2: "later"}
    assert "src/c.py" not in sections[2][1]  # a non-phase heading ends the section
    real = lint.phase_sections((ROOT / "docs/roadmap.md").read_text())
    assert real[0][0] == "done"
    assert real[1][0] == "next"


# -- TEMPORARY markers and pragmas ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "line",
    [
        "x = 1  # TEMPORARY(phase2): air only conducts; remove when convection lands",
        "# TEMPORARY(phase1/scene): crate hard-coded until the YAML loader exists",
        "// TEMPORARY(phase1): shader clamps glow until HDR tonemapping is set up",
        "if x:  # pragma: no cover - only reachable on Windows, which CI does not run",
        "# pragma: no cover: the branch needs a GPU that tests do not have",
    ],
)
def test_a_well_formed_marker_passes(line):
    assert lint.check_markers({"src/a.py": line}, ROADMAP) == []


@pytest.mark.parametrize(
    ("rel", "line", "complaint"),
    [
        ("src/a.py", "# TEMPORARY(soon): fix later please", "must cite a roadmap phase"),
        ("src/a.py", "# TEMPORARY(phase9): a phase that does not exist", "lacks"),
        ("src/a.py", "# TEMPORARY(phase0): a phase that is already done", "is done"),
        ("src/a.py", "# TEMPORARY(phase2)", "needs ': <why"),
        ("src/a.py", "# TEMPORARY(phase2): eh", "needs ': <why"),
        ("src/a.py", "# temporary (phase0): lower case and a space still count", "is done"),
        ("src/z.py", "# TEMPORARY(phase2): the roadmap does not list this file", "list src/z.py under Phase 2"),
        ("src/c.py", "# TEMPORARY(phase2): listed only outside the phase section", "list src/c.py under Phase 2"),
        ("src/a.py", "x  # pragma: no cover", "needs a reason"),
        ("src/a.py", "x  # pragma: no cover - meh", "needs a reason"),
        ("src/a.py", "# Temporary (phase0): mixed case still counts when it cites a phase", "is done"),
        ("a.py", "# TEMPORARY(phase2): listed only as part of a longer path, src/a.py", "list a.py under Phase 2"),
    ],
)
def test_a_bad_marker_is_reported(rel, line, complaint):
    problems = lint.check_markers({rel: line}, ROADMAP)
    assert any(complaint in p for p in problems), problems
    assert all(p.startswith(f"{rel}:1:") for p in problems)


def test_prose_about_temporary_things_is_not_a_marker():
    assert lint.check_markers({"docs/x.md": "A temporary (two-turn) fire, TEMPORARILY (sic) lit."}, ROADMAP) == []


def test_exempt_files_may_mention_markers():
    line = "# TEMPORARY(soon): x  # pragma: no cover"
    assert lint.check_markers({"tests/test_lint_standards.py": line, "scripts/lint_standards.py": line}, ROADMAP) == []


@pytest.mark.parametrize(
    "text",
    [
        "A review quotes `TEMPORARY(phaseN)` and `# pragma: no cover` as syntax.",
        "A double-backtick span ``TEMPORARY(phaseN) with a ` inside`` is code too.",
        "A span that wraps `TEMPORARY(phaseN):\n<why>` across a line is still one span.",
        "```python\nx = 1  # TEMPORARY(soon)\n# pragma: no cover\n```",
        "~~~~\n```\nTEMPORARY(soon) inside a longer fence a shorter one cannot close\n~~~~",
    ],
)
def test_markdown_code_is_a_quotation_not_a_marker(text):
    assert lint.check_markers({"docs/design/reviews/r.md": text}, ROADMAP) == []


@pytest.mark.parametrize(
    ("text", "line", "complaint"),
    [
        ("Prose: TEMPORARY(phaseN) with no code span.", 1, "must cite a roadmap phase"),
        ("```\nquoted\n```\nTEMPORARY(soon): after the fence closes, with a reason", 4, "must cite a roadmap phase"),
        ("An unclosed ` backtick\n\nTEMPORARY(soon): a blank line ends the paragraph`", 3, "must cite a roadmap phase"),
        ("x  pragma: no cover, in prose", 1, "needs a reason"),
    ],
)
def test_markdown_prose_is_still_checked(text, line, complaint):
    problems = lint.check_markers({"docs/x.md": text}, ROADMAP)
    assert any(complaint in p for p in problems), problems
    assert all(p.startswith(f"docs/x.md:{line}:") for p in problems), problems


def test_backticks_in_code_files_do_not_hide_a_marker():
    problems = lint.check_markers({"src/a.py": "s = '`'  # TEMPORARY(soon): x `y`"}, ROADMAP)
    assert any("must cite a roadmap phase" in p for p in problems), problems


def test_the_repository_documents_need_no_marker_exemption():
    assert not {rel for rel in lint.MARKER_EXEMPT if rel.endswith(".md")}
    files = lint.tracked_text_files(ROOT)
    docs = {rel: text for rel, text in files.items() if rel.endswith(".md")}
    assert lint.check_markers(docs, (ROOT / "docs/roadmap.md").read_text()) == []


# -- guard citations --------------------------------------------------------------------------------------------------

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
- **Rule eight.** Guard: `docs/code_review.md`
- **Rule nine.** Guard: `tests::anything`
- **Rule ten.** Guard: `pyproject.toml::markers`, `docs/code_review.md`
- **Rule eleven.** Guard: `scripts/lint_standards.py::re`

## Next section

- not a rule. No guard needed.
"""
BACKLOG = "| B1 | something |\n"


def test_guard_citations_are_checked():
    problems, checked, review_only = lint.check_guards(STANDARDS, BACKLOG, ROOT)
    text = "\n".join(problems)
    for ok in ("CLAUDE.md:5:", "CLAUDE.md:7:", "CLAUDE.md:15:"):  # rules one, two, ten
        assert ok not in text, text
    assert "CLAUDE.md:8: rule has no 'Guard:'" in text
    assert "CLAUDE.md:9: guard nope/missing.py does not exist" in text
    assert "CLAUDE.md:10: guard scripts/lint_standards.py has no no_such_symbol outside comments" in text
    assert "CLAUDE.md:11: backlog row B99" in text
    assert "CLAUDE.md:12: 'Guard:' names neither" in text
    assert "CLAUDE.md:13: only documents guard this rule" in text
    assert "CLAUDE.md:14: guard tests is a directory" in text
    assert "CLAUDE.md:16: guard scripts/lint_standards.py has no re outside comments" in text  # imported, not defined
    assert len(problems) == 8
    assert "not a rule" not in text
    # Rules one, two (a directory is a real guard), four, five, nine, ten, eleven cite non-document paths; six and
    # eight cite only a backlog row or a document. Three and seven never reach the count.
    assert (checked, review_only) == (7, 2)


def test_a_missing_standards_section_is_a_finding():
    assert lint.check_guards("# CLAUDE.md\n", BACKLOG, ROOT) == (
        ["CLAUDE.md: no '## Engineering standards' section with rule bullets"],
        0,
        0,
    )


def test_a_standards_section_at_the_end_of_the_file_is_read():
    problems, checked, _ = lint.check_guards("## Engineering standards\n\n- **R.** Guard: `tests`", BACKLOG, ROOT)
    assert (problems, checked) == ([], 1)


@pytest.mark.parametrize(
    ("name", "text", "symbol", "present"),
    [
        ("a.toml", 'select = ["BLE", "S110"]\n', "BLE", True),
        ("a.toml", '# BLE and S110 are the swallow rules\nselect = ["E"]\n', "BLE", False),
        ("a.toml", 'select = ["E"]  # BLE comes later\n', "BLE", False),
        ("a.toml", 'select = ["BLEX"]\n', "BLE", False),
        ("a.sh", '"$PY" -m diff_cover.diff_cover_tool x\n', "diff_cover", True),
        ("a.py", "def check(x):\n    pass\n", "check", True),
        ("a.py", "CHECKS: list[str] = []\n", "CHECKS", True),
        ("a.py", "x = check(1)\n", "check", False),
        ("a.py", "class Lint:\n    def run(self): ...\n", "Lint.run", True),
        (".gitignore", ".worktrees/\n", ".worktrees", True),
        ("notes.md", "the BLE rule\n", "BLE", True),
    ],
)
def test_symbols_are_whole_words_outside_comments(tmp_path, name, text, symbol, present):
    p = tmp_path / name
    p.write_text(text)
    assert lint.symbol_present(p, symbol) is present


# -- coverage ratchet -------------------------------------------------------------------------------------------------


def _pyproject(floor: float | None) -> str:
    return "[tool.coverage.report]\n" + ("" if floor is None else f"fail_under = {floor}\n")


@pytest.mark.parametrize(
    ("now", "base", "complaint"),
    [
        (100, 100, None),
        (100, 95, None),
        (95, None, None),
        (95, 100, "fell from 100 to 95"),
        (None, 100, "fail_under is missing"),
    ],
)
def test_the_coverage_floor_only_ratchets(now, base, complaint):
    problems = lint.check_coverage_ratchet(_pyproject(now), None if base is None else _pyproject(base))
    if complaint is None:
        assert problems == []
    else:
        assert len(problems) == 1
        assert complaint in problems[0]


def test_a_base_without_a_floor_has_nothing_to_ratchet_against():
    assert lint.check_coverage_ratchet(_pyproject(90), "[project]\nname = 'x'\n") == []


# -- the whole run, against a real repository -------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _commit(repo: Path, message: str) -> None:
    """A throwaway commit in a temp repo: a fixed identity, unsigned because it never leaves the test."""
    identity = ["-c", "user.email=t@example.com", "-c", "user.name=t", "-c", "commit.gpgsign=false"]
    _git(repo, *identity, "commit", "-qm", message)


@pytest.fixture
def repo(tmp_path):
    """A minimal repository that passes: CLAUDE.md, roadmap, backlog, pyproject, and a binary file."""
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/roadmap.md").write_text("## Phase 1: Tile (next)\n")
    (tmp_path / "docs/standards_backlog.md").write_text("| B1 | x |\n")
    (tmp_path / "CLAUDE.md").write_text("## Engineering standards\n\n- **R.** Guard: `pyproject.toml::fail_under`\n")
    (tmp_path / "pyproject.toml").write_text(_pyproject(100))
    (tmp_path / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n\xff\xfe\x00")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "-A")
    _commit(tmp_path, "x")
    return tmp_path


def test_main_passes_a_clean_repository_and_reports_the_counts(repo, capsys):
    assert lint.main(["--base", "HEAD"], root=repo) == 0
    assert (
        "PASS (0 finding(s)); rules enforced by a check: 1, held only by review (backlog): 0" in capsys.readouterr().out
    )


def test_main_fails_and_reports_each_finding(repo, capsys):
    (repo / "pyproject.toml").write_text(_pyproject(90))  # below the base's 100
    (repo / "hack.py").write_text("x = 1  # TEMPORARY(phase1): untracked files are scanned too\n")
    assert lint.main(["--base", "HEAD"], root=repo) == 1
    out = capsys.readouterr()
    assert "FAIL (2 finding(s))" in out.out
    assert "fell from 100 to 90" in out.err
    assert "list hack.py under Phase 1" in out.err


def test_main_without_a_base_or_backlog_still_runs(repo, capsys):
    (repo / "docs/standards_backlog.md").unlink()
    assert lint.main([], root=repo) == 0
    assert lint.base_pyproject(repo, None) == (None, [])


def test_an_unknown_base_is_a_finding_not_a_skip(repo, capsys):
    (repo / "pyproject.toml").write_text(_pyproject(10))
    assert lint.main(["--base", "mian"], root=repo) == 1
    assert "--base mian is not a commit" in capsys.readouterr().err


def test_a_base_with_no_pyproject_has_nothing_to_ratchet_against(repo):
    _git(repo, "rm", "-q", "pyproject.toml")
    _commit(repo, "y")
    assert lint.base_pyproject(repo, "HEAD") == (None, [])


def test_the_repository_itself_passes(capsys):
    assert lint.main([], root=ROOT) == 0, capsys.readouterr().err
