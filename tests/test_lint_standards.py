"""scripts/lint_standards.py: the checks behind the no-band-aid exemption, guard citations and the coverage ratchet."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from tests._gitutil import git

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
    assert lint.check_markers({"CLAUDE.md": "# TEMPORARY(soon): x  # pragma: no cover"}, ROADMAP) == []


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

## First principle: brutal honesty

- **Honest rule.** Guard: B1
- **Unguarded honest rule.** Nothing checks it.
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
    assert "CLAUDE.md:25: rule has no 'Guard:'" in text  # the honesty section is read like the standards
    assert len(problems) == 9
    assert "not a rule" not in text
    # Rules one, two (a directory is a real guard), four, five, nine, ten, eleven cite non-document paths; six,
    # eight and the honest rule cite only a backlog row or a document. Three, seven and the unguarded honest rule
    # never reach the count.
    assert (checked, review_only) == (7, 3)


HONESTY = "## First principle: brutal honesty\n\n- **H.** Guard: B1\n\n"


def test_a_missing_rule_section_is_a_finding():
    assert lint.check_guards("# CLAUDE.md\n", BACKLOG, ROOT) == (
        [
            "CLAUDE.md: no '## First principle: brutal honesty' section with rule bullets",
            "CLAUDE.md: no '## Engineering standards' section with rule bullets",
        ],
        0,
        0,
    )


def test_a_rule_section_with_no_bullets_is_a_finding():
    problems, _, _ = lint.check_guards(HONESTY + "## Engineering standards\n\nprose only\n", BACKLOG, ROOT)
    assert problems == ["CLAUDE.md: no '## Engineering standards' section with rule bullets"]


def test_a_standards_section_at_the_end_of_the_file_is_read():
    claude_md = HONESTY + "## Engineering standards\n\n- **R.** Guard: `tests`"
    problems, checked, _ = lint.check_guards(claude_md, BACKLOG, ROOT)
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


LIMITS = "[tool.maxim_overdrive.size_limits]\nfunction_lines = 40\nmodule_lines = 500\npublic_methods = 12\n"


def _pyproject(floor: float | None, limits: str = LIMITS) -> str:
    return "[tool.coverage.report]\n" + ("" if floor is None else f"fail_under = {floor}\n") + limits


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
    git(repo, *args)


def _commit(repo: Path, message: str) -> None:
    """A throwaway commit in a temp repo (tests/_gitutil.py: a fixed identity, unsigned, no inherited git state)."""
    git(repo, "commit", "-qm", message)


@pytest.fixture
def repo(tmp_path):
    """A minimal repository that passes: CLAUDE.md, roadmap, backlog, pyproject, and a binary file."""
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/roadmap.md").write_text("## Phase 1: Tile (next)\n")
    (tmp_path / "docs/standards_backlog.md").write_text("| B1 | x |\n")
    (tmp_path / "CLAUDE.md").write_text(
        "## First principle: brutal honesty\n\n- **H.** Guard: `pyproject.toml`\n\n"
        "## Engineering standards\n\n- **R.** Guard: `pyproject.toml::fail_under`\n"
    )
    (tmp_path / "pyproject.toml").write_text(_pyproject(100))
    (tmp_path / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n\xff\xfe\x00")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "-A")
    _commit(tmp_path, "x")
    return tmp_path


def test_main_passes_a_clean_repository_and_reports_the_counts(repo, capsys):
    assert lint.main(["--base", "HEAD"], root=repo) == 0
    assert (
        "PASS (0 finding(s)); rules enforced by a check: 2, held only by review (backlog): 0" in capsys.readouterr().out
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


# -- Separation of concerns: size and complexity tripwires -------------------------------------------------------------

SMALL = lint.SizeLimits(function_lines=4, module_lines=20, public_methods=2)


def _function(name: str, body_lines: int, docstring: bool = False) -> str:
    doc = '    """A docstring\n    over two lines."""\n' if docstring else ""
    return f"def {name}():\n" + doc + "".join(f"    x{i} = {i}\n" for i in range(body_lines))


def test_the_real_limits_load_and_match_the_standard():
    limits, problems = lint.size_limits((ROOT / "pyproject.toml").read_text())
    assert problems == []
    assert limits == lint.SizeLimits(function_lines=40, module_lines=500, public_methods=12)


@pytest.mark.parametrize(
    "table",
    [
        "",  # missing
        "[tool.maxim_overdrive.size_limits]\nfunction_lines = 40\nmodule_lines = 500\n",  # one missing
        LIMITS + "class_lines = 9\n",  # an unknown key would be a limit nobody enforces
        LIMITS.replace("40", "0"),
        LIMITS.replace("40", "40.5"),
        LIMITS.replace("40", "true"),
    ],
)
def test_a_missing_or_malformed_limits_table_is_a_finding(table):
    limits, problems = lint.size_limits(_pyproject(100, limits=table))
    assert limits is None
    assert len(problems) == 1


def test_code_within_the_limits_passes():
    code = _function("f", 4) + _function("g", 4, docstring=True)
    assert lint.check_sizes({"src/a.py": code}, SMALL) == []


def test_a_long_function_is_found_and_the_docstring_does_not_count():
    problems = lint.check_sizes({"src/a.py": _function("long", 5)}, SMALL)
    assert problems == ["src/a.py:1: long has a 5-line body (limit 4); split it by responsibility"]


def test_a_nested_function_counts_towards_its_parent_and_is_checked_itself():
    inner = "".join("    " + ln + "\n" for ln in _function("inner", 5).splitlines())
    problems = lint.check_sizes({"scripts/a.py": "def outer():\n" + inner}, SMALL)
    assert any("outer has a 6-line body" in p for p in problems)
    assert any("inner has a 5-line body" in p for p in problems)


def test_a_long_module_is_found():
    problems = lint.check_sizes({"src/a.py": "x = 1\n" * 21}, SMALL)
    assert problems == ["src/a.py: 21 lines (limit 20); split the module by concern"]


def test_a_class_with_too_many_public_methods_is_found_and_private_ones_do_not_count():
    methods = "".join(f"    def m{i}(self): pass\n" for i in range(3))
    private = "".join(f"    def _p{i}(self): pass\n" for i in range(5))
    problems = lint.check_sizes({"src/a.py": "class God:\n" + methods + private}, SMALL)
    assert problems == ["src/a.py:1: class God has 3 public methods (limit 2); it is doing more than one job"]
    assert (
        lint.check_sizes({"src/a.py": "class Fine:\n" + methods[: methods.index("    def m2")] + private}, SMALL) == []
    )


@pytest.mark.parametrize(
    "line",
    [
        "def f():  # noqa: C901",
        "def f():  # noqa: PLR0912",
        "def f():  # noqa: E501, PLR0915",
        "def f():  # NOQA:C90",
        "def f():  # noqa",  # a blanket noqa silences every rule, these included
        "# ruff: noqa",
        "# ruff: noqa: C901",
        "# flake8: noqa",  # ruff honours it as a file-wide exemption
    ],
)
def test_a_noqa_may_not_silence_the_complexity_rules(line):
    problems = lint.check_sizes({"src/a.py": line + "\n"}, SMALL)
    assert any("a noqa may not silence the complexity rules" in p for p in problems)


def test_a_noqa_for_another_rule_is_allowed():
    assert lint.check_sizes({"src/a.py": "import os  # noqa: F401\n"}, SMALL) == []


def test_the_limits_apply_to_src_and_scripts_only():
    long = _function("long", 9) + "# noqa: C901\n"
    files = {"tests/test_a.py": long, "docs/a.md": long, "src/a.txt": long, "tools/a.py": long}
    assert lint.check_sizes(files, SMALL) == []


def test_an_unparseable_file_is_a_finding_not_a_pass():
    problems = lint.check_sizes({"src/a.py": "def f(:\n"}, SMALL)
    assert len(problems) == 1
    assert "does not parse" in problems[0]


def test_main_reports_a_god_function(repo, capsys):
    (repo / "src").mkdir()
    (repo / "src/god.py").write_text(_function("god", 41))
    assert lint.main([], root=repo) == 1
    assert "god has a 41-line body (limit 40)" in capsys.readouterr().err


def test_main_reports_a_malformed_limits_table(repo, capsys):
    (repo / "pyproject.toml").write_text(_pyproject(100, limits=""))
    assert lint.main([], root=repo) == 1
    assert "size_limits] must set exactly" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("base", "complaint"),
    [
        (None, None),
        (_pyproject(100), None),
        (_pyproject(100, limits=LIMITS.replace("40", "60")), None),  # tightening is fine
        (_pyproject(100, limits=LIMITS.replace("40", "30")), "function_lines rose from 30 to 40"),
        (_pyproject(100, limits=LIMITS.replace("500", "400")), "module_lines rose from 400 to 500"),
        (_pyproject(100, limits=LIMITS.replace("12", "10")), "public_methods rose from 10 to 12"),
        (_pyproject(100, limits=""), None),  # a base from before the limits existed
    ],
)
def test_the_size_limits_only_tighten(base, complaint):
    current = lint.SizeLimits(function_lines=40, module_lines=500, public_methods=12)
    problems = lint.check_size_ratchet(current, base)
    assert problems == [] if complaint is None else [p for p in problems if complaint in p] == problems != []


def test_main_refuses_a_loosened_limit(repo, capsys):
    (repo / "pyproject.toml").write_text(_pyproject(100, limits=LIMITS.replace("40", "80")))
    assert lint.main(["--base", "HEAD"], root=repo) == 1
    assert "function_lines rose from 40 to 80" in capsys.readouterr().err


def test_comments_and_blank_lines_do_not_count_towards_a_body():
    code = (
        "def f():\n    # why the first step\n    a = 1\n\n"
        "    # why the second\n    b = 2\n    c = 3\n    return a + b + c\n"
    )
    assert lint.check_sizes({"src/a.py": code}, SMALL) == []
    assert lint.check_sizes({"src/a.py": code.replace("    return", "    d = 4\n    return")}, SMALL) != []


def test_a_body_that_is_only_a_docstring_counts_as_empty():
    code = 'def f():\n    """One\n    two\n    three\n    four\n    five."""\n'
    assert lint.check_sizes({"src/a.py": code}, SMALL) == []


def test_async_functions_and_methods_are_checked():
    body = "".join(f"    x{i} = {i}\n" for i in range(5))
    problems = lint.check_sizes({"src/a.py": "async def f():\n" + body}, SMALL)
    assert problems == ["src/a.py:1: f has a 5-line body (limit 4); split it by responsibility"]
    methods = "".join(f"    async def m{i}(self): pass\n" for i in range(3))
    assert any("3 public methods" in p for p in lint.check_sizes({"src/a.py": "class C:\n" + methods}, SMALL))


@pytest.mark.parametrize(
    ("base", "base_text", "expected"),
    [
        (None, None, []),
        ("main", None, ["coverage and size ratchets have nothing to compare"]),
        ("main", "[tool.coverage.report]\n", ["no coverage floor", "no valid size limits"]),
        ("main", _pyproject(100, limits=""), ["no valid size limits"]),
        ("main", _pyproject(100), []),
    ],
)
def test_a_ratchet_with_nothing_to_compare_says_so(base, base_text, expected):
    notes = lint.ratchet_notes(base, base_text)
    assert len(notes) == len(expected)
    assert all(e in n for e, n in zip(expected, notes, strict=True))


def test_main_prints_the_ratchet_notes(repo, capsys):
    _git(repo, "checkout", "-q", "--orphan", "bare")
    _git(repo, "rm", "-q", "-r", "--cached", "pyproject.toml")
    _commit(repo, "a base with no pyproject")
    _git(repo, "add", "-A")
    assert lint.main(["--base", "bare"], root=repo) == 0
    assert "bare has no pyproject.toml" in capsys.readouterr().out
