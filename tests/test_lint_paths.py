"""scripts/lint_paths.py: no home directory in the tree (CLAUDE.md, "No personal details in the tree"; B44).

Each spelling is proven by planting it and watching the check refuse it. The samples are joined at run time, because
this file is itself in the tree the check scans: a literal sample would be a finding against it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests._gitutil import git
from tests.test_lint_standards import _load

ROOT = Path(__file__).resolve().parents[1]
paths = _load("lint_paths")
repo_files = _load("lint_repo")

NAME = "alice"
ROOTS = ("/Users/", "/home/", "C:\\Users\\", "-Users-", "-home-")
# Review F2, AW-S4: case, escaped and forward separators, URL encoding, a doubled slash.
SPELLINGS = (
    *ROOTS,
    "/users/",
    "/USERS/",
    "c:\\users\\",
    "C:\\\\Users\\\\",
    "C:/Users/",
    "%2FUsers%2F",
    "%2fhome%2f",
    "//Users//",
    "file:///Users/",
    "/mnt/c/Users/",  # WSL: the anchor must not hide a drive's home (fold 1)
    "-users-",
)


@pytest.mark.parametrize("root", SPELLINGS)
def test_every_spelling_of_a_home_directory_is_refused(root):
    line = f"ran it in `{root}{NAME}{'-repo/x' if root.startswith('-') else '/x'}` first"
    assert len(paths.check_paths({"docs/r.md": f"intro\n{line}\n"})) == 1


@pytest.mark.parametrize("root", ["/Users/", "/home/", "-Users-"])
def test_a_public_accounts_name_with_more_after_it_is_someone_else(root):
    # Review F5: runner-x is another account, not GitHub's runner; the dash form can't tell, so it names a project.
    found = paths.check_paths({"a.md": f"{root}runner-{NAME}/x"})
    assert len(found) == (0 if root.startswith("-") else 1)


def test_a_session_scratchpad_path_is_refused():
    # The form the go-public scrub missed: Claude Code's project directory, its slashes encoded as dashes.
    shared = "/private/tmp/claude-501/"  # shared-path-ok: text the check reads, never a path anything writes
    scratch = shared + "-Users-" + NAME + "-Scripts-Repo/0f/scratchpad/probe.gd"
    assert paths.check_paths({"docs/r.md": scratch})


@pytest.mark.parametrize(
    "line",
    [
        "`<home>/Scripts/repo` and `<scratchpad>/probe.gd`",
        "an elided `/Users/…` or `/Users/.../repo/src` names nobody",
        "`~/.config` and `~/.ssh` are anyone's",
        "GitHub's `/Users/runner/hostedtoolcache` and `/home/runner/work`",
        "macOS's `/Users/Shared/`",
        "a runner in `-Users-runner-work-`",
        # a directory inside a path, and prose (review AW-N2)
        "DeepMind Lab's `docs/users/observations.md` and github.com/users/x",
        "the Power-Users-guide for a multi-home-setup",
        "a placeholder after a public account: `/Users/runner-<name>/x`",
    ],
)
def test_placeholders_elisions_and_public_accounts_pass(line):
    assert paths.check_paths({"docs/r.md": line}) == []


def test_a_finding_names_the_line_but_never_the_name():
    found = paths.check_paths({"b.md": "ok\n", "a.md": f"ok\n{ROOTS[0]}{NAME}/x and {ROOTS[1]}{NAME}/y\n"})
    assert len(found) == 1  # one finding per line, however many paths it holds
    assert found[0].startswith("a.md:2: a path under someone's home directory")
    assert NAME not in found[0]  # CI's logs are public


def test_a_public_account_beside_a_private_one_is_still_a_finding():
    assert paths.check_paths({"a.md": f"/Users/runner/x then {ROOTS[0]}{NAME}/y"})


def test_the_repository_holds_no_home_directory():
    assert paths.check_paths(repo_files.tracked_text_files(ROOT)) == []


def test_a_file_whose_own_path_is_under_a_home_is_refused():
    # Review F3: a copied scratchpad folder names its owner in the path, whatever the file holds.
    found = paths.check_paths({f"docs/-Users-{NAME}-Repo/r.md": "fine\n"})
    assert len(found) == 1
    assert found[0].startswith("docs/-Users-<name>-Repo/r.md: its path is under someone's home directory")
    assert NAME not in found[0]  # the path is printed masked: CI's logs are public


def test_files_with_non_ascii_names_are_read(tmp_path):
    # Review F3: git quotes a non-ASCII name unless asked not to, and the lister skipped the file without a word.
    git(tmp_path, "init", "-q")
    (tmp_path / "café.md").write_text("x\n")
    assert repo_files.tracked_text_files(tmp_path) == {"café.md": "x\n"}
