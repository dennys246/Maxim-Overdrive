"""scripts/remote_gate.py: gate branches on another machine, against a fake remote under tmp_path (no network).

The fake remote is strict where the real one is: ``ssh`` runs the command under zsh (the mini's login shell; ``sh``
where there is none) with an emptied environment and ``PATH=/usr/bin:/bin``, plus a planted ``GIT_DIR`` and
``MAXIM_OVERDRIVE_UNLOCKED`` the script must not let through; ``scp`` never makes directories; both insist on ``--``
before the host. The "origin" is a local repository whose ``scripts/prepush.sh`` is a stub, so the tests check what
the script does around the gate (bundling, refs, worktrees, venvs, masks, the PASS line, refusals), not the gate.
"""

from __future__ import annotations

import getpass
import importlib.util
import os
import re
import stat
import sys
from pathlib import Path

import pytest

from tests._gitutil import git

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("remote_gate", ROOT / "scripts" / "remote_gate.py")
assert _spec is not None
assert _spec.loader is not None
rg = importlib.util.module_from_spec(_spec)
sys.modules["remote_gate"] = rg
_spec.loader.exec_module(rg)

HOST = "secret-host.invalid"  # stands for the private host: it must reach no file and no output
BRANCH = "phase1/x-y"
WT = "phase1+x-y"
LEAK_CHECK = 'if [ -n "${GIT_DIR:-}${MAXIM_OVERDRIVE_UNLOCKED:-}" ]; then echo "leaked into the gate"; exit 5; fi\n'
PASSING = (
    "#!/bin/bash\n" + LEAK_CHECK + 'echo "godot=$GODOT"\necho "on stderr" >&2\n'
    "printf '\\nprepush: PASS %s (base %s)%s\\n' \"$(git rev-parse --short=12 HEAD)\" stub ''\n"
)
FAILING = '#!/bin/bash\necho "godot=$GODOT tmp=$TMPDIR_SEEN"\necho "FAILED tests/test_x.py::test_y"\nexit 3\n'
PYTHON = (  # the remote Python: reports its version, makes a venv whose pip counts its installs
    "#!/bin/bash\n"
    'if [ "$1" = -c ]; then echo "${FAKE_PY_VERSION:-3.12}"; exit 0; fi\n'
    'mkdir -p "$3/bin"\n'
    'printf \'#!/bin/bash\\necho x >> "$HOME/pip-installs"\\n'
    '[ ! -f "$HOME/pip-fails" ] || { rm "$HOME/pip-fails"; echo pip broke; exit 1; }\\n\' > "$3/bin/pip"\n'
    'chmod +x "$3/bin/pip"\n'
)


def _exe(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def _fakes(bin_dir: Path, home: Path, *, scp_fails: int = 0) -> None:
    shell = "/bin/zsh" if Path("/bin/zsh").exists() else "/bin/sh"
    plant = f"GIT_DIR=/nonexistent MAXIM_OVERDRIVE_UNLOCKED=1 TMPDIR={home.parent / 'remote-tmp'}/"
    _exe(
        bin_dir / "ssh",
        f'#!/bin/bash\n[ "$3" = -- ] && [ "$4" = "{HOST}" ] || {{ echo "ssh: bad argv for $4" >&2; exit 255; }}\n'
        f'cd "{home}" && exec /usr/bin/env -i PATH=/usr/bin:/bin HOME="{home}" {plant} {shell} -c "$5"\n',
    )
    drops = home / ".drops"
    _exe(
        bin_dir / "scp",
        '#!/bin/bash\n[ "$4" = -- ] || exit 1\n'
        f'n=$(cat "{drops}" 2>/dev/null || echo 0)\n'
        f'if [ "$n" -lt {scp_fails} ]; then echo $((n+1)) > "{drops}"; exit 1; fi\n'
        f'[ "${{6%%:*}}" = "{HOST}" ] || exit 1\n'
        f'dest="{home}/${{6#*:}}"; [ -d "$(dirname "$dest")" ] || {{ echo "scp: no directory" >&2; exit 1; }}\n'
        'cp "$5" "$dest"\n',
    )


def _commit(repo: Path, path: str, text: str, message: str, *extra: str) -> None:
    (repo / path).parent.mkdir(parents=True, exist_ok=True)
    (repo / path).write_text(text)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", *extra, "-m", message)


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    origin, home = tmp_path / "origin", tmp_path / "home"
    home.mkdir()
    (tmp_path / "remote-tmp").mkdir()
    origin.mkdir()
    git(origin, "init", "-q", "-b", "main")
    _exe(origin / "scripts" / "prepush.sh", PASSING)
    (origin / "constraints").mkdir()
    (origin / "constraints" / "py3.12.txt").write_text("numpy==1\n")
    _commit(origin, "pyproject.toml", "[project]\n", "base")
    git(tmp_path, "clone", "-q", str(origin), "local")
    local = tmp_path / "local"
    git(local, "checkout", "-q", "-b", BRANCH)
    _commit(local, "work.txt", "a change\n", "work")
    _fakes(tmp_path / "bin", home)
    python = _exe(tmp_path / "fakepy", PYTHON)
    monkeypatch.setenv("PATH", f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("OVERDRIVE_REMOTE", HOST)
    monkeypatch.setenv("GIT_DIR", "/nonexistent")  # the script's own git calls must not inherit it
    return {"tmp": tmp_path, "origin": origin, "home": home, "local": local, "python": python, "work": tmp_path / "w"}


def _args(w: dict[str, Path], *branches: str, clone: str = "session-repo") -> list[str]:
    paths = ["--repo", str(w["local"]), "--work", str(w["work"]), "--python", str(w["python"])]
    return ["--clone", clone, "--gate-root", "gate", *paths, *branches]


def _clone(w: dict[str, Path]) -> Path:
    return w["home"] / "gate" / "session-repo"


def _head(w: dict[str, Path]) -> str:
    return git(w["local"], "rev-parse", BRANCH).stdout.strip()


def _private_value_anywhere(w: dict[str, Path]) -> list[Path]:
    """Files holding the host, outside the fake ssh and scp (which must name it to check their argv)."""
    roots = [w["home"], w["local"], w["origin"], w["work"]]
    return [p for r in roots for p in r.rglob("*") if p.is_file() and HOST.encode() in p.read_bytes()]


def test_a_branch_whose_name_has_a_slash_is_gated_detached_and_its_pass_line_printed(
    world: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    assert rg.main(_args(world, BRANCH)) == 0
    out = capsys.readouterr()
    assert out.out.strip() == f"{BRANCH}: prepush: PASS {_head(world)[:12]} (base stub)"
    worktree = _clone(world) / ".worktrees" / WT
    assert git(worktree, "rev-parse", "HEAD").stdout.strip() == _head(world)
    assert git(worktree, "symbolic-ref", "-q", "HEAD", check=False).returncode != 0  # detached: no remote branch
    assert git(_clone(world), "branch", "--list", BRANCH).stdout == ""
    assert HOST not in out.out + out.err
    assert not _private_value_anywhere(world)


def test_a_new_commit_and_a_rewritten_branch_are_each_gated_at_their_new_head(world: dict[str, Path]) -> None:
    assert rg.main(_args(world, BRANCH)) == 0
    _commit(world["local"], "work.txt", "more\n", "more")
    assert rg.main(_args(world, BRANCH)) == 0  # the worktree moved to the new head (verdict checks the HEAD line)
    _commit(world["local"], "work.txt", "rewritten\n", "rewritten", "--amend")
    assert rg.main(_args(world, BRANCH)) == 0  # a non-fast-forward: the "+" refspec takes it
    assert git(_clone(world) / ".worktrees" / WT, "rev-parse", "HEAD").stdout.strip() == _head(world)


def test_a_worktree_removed_by_hand_is_added_again(world: dict[str, Path]) -> None:
    assert rg.main(_args(world, BRANCH)) == 0
    git(_clone(world), "worktree", "remove", "--force", f".worktrees/{WT}")
    assert rg.main(_args(world, BRANCH)) == 0  # with `-b`, the branch left behind would refuse this


def test_a_worktree_on_another_branch_is_refused_and_its_message_reaches_stderr(
    world: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    assert rg.main(_args(world, BRANCH)) == 0
    git(_clone(world) / ".worktrees" / WT, "checkout", "-q", "-b", "someone-else")
    assert rg.main(_args(world, BRANCH)) == 1
    err = capsys.readouterr().err
    assert f".worktrees/{WT} is on someone-else, not {BRANCH}" in err


def test_a_failing_gate_exits_nonzero_and_masks_the_remote_home_user_temp_and_host(
    world: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    stub = FAILING.replace("$TMPDIR_SEEN", str(world["tmp"] / "remote-tmp"))  # the gate's env has no TMPDIR
    _commit(world["local"], "scripts/prepush.sh", stub, "a failing gate")
    assert rg.main(_args(world, BRANCH)) == 1
    err = capsys.readouterr().err
    assert "FAILED tests/test_x.py::test_y" in err
    assert "(exit 3)" in err
    assert "godot=<home>/gate/godot/Godot.app/Contents/MacOS/Godot tmp=<tmp>" in err
    assert str(world["home"]) not in err
    assert getpass.getuser() not in err
    assert HOST not in err


def test_a_connection_failure_shows_ssh_stderr_with_the_host_masked(
    world: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    _exe(world["tmp"] / "bin" / "ssh", f'#!/bin/bash\necho "ssh: connect to host {HOST}: refused" >&2\nexit 255\n')
    assert rg.main(_args(world, BRANCH)) == 1
    err = capsys.readouterr().err
    assert "ssh: connect to host <remote>: refused" in err
    assert HOST not in err


@pytest.mark.parametrize(
    ("flag", "value"),
    [
        ("--clone", "repo"),
        ("--clone", "../overdrive-gate/repo"),
        ("--clone", "overdrive-gate/x-repo"),
        ("--clone", "-repo"),
        ("--gate-root", "gate/.."),
        ("--gate-root", "/abs"),
        ("--remote", "-oProxyCommand=touch pwned"),
        ("--remote", ""),
    ],
)
def test_an_unsafe_clone_root_or_remote_is_refused_before_anything_runs(
    world: dict[str, Path], flag: str, value: str
) -> None:
    assert rg.main([*_args(world, BRANCH), f"{flag}={value}"]) == 1
    assert not world["work"].exists()
    assert list(world["home"].iterdir()) == []


@pytest.mark.parametrize("branch", ["-x", "a/../b", "a//b", "phase1/$(touch pwned)", "a+b", "a b"])
def test_a_branch_name_outside_the_safe_alphabet_is_refused_before_anything_runs(
    world: dict[str, Path], branch: str
) -> None:
    assert rg.main(_args(world, "--", branch)) == 1  # "--": argparse would read "-x" as an option
    assert list(world["home"].iterdir()) == []


def test_a_clone_that_resolves_to_the_shared_one_is_refused_on_the_remote(
    world: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    shared = world["home"] / "overdrive-gate" / "repo"
    git(world["tmp"], "clone", "-q", str(world["origin"]), str(shared))
    (world["home"] / "gate").mkdir()
    (world["home"] / "gate" / "session-repo").symlink_to(shared)
    assert rg.main(_args(world, BRANCH)) == 1
    assert "resolves to the clone every session shares" in capsys.readouterr().err
    assert not (shared / ".git" / "remote-gate").exists()


def test_an_option_shaped_remote_is_refused_by_name_not_only_by_ssh(world: dict[str, Path]) -> None:
    with pytest.raises(rg.GateRefused, match="no usable remote"):
        rg.config([*_args(world, BRANCH), "--remote=-oProxyCommand=touch pwned"])


def test_no_remote_is_refused(world: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OVERDRIVE_REMOTE")
    monkeypatch.setattr(sys, "argv", ["remote_gate.py", *_args(world, BRANCH)])
    assert rg.main() == 1


def test_a_bundle_that_misses_the_local_head_is_refused_before_it_is_copied(
    world: dict[str, Path], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(rg, "local_head", lambda repo, branch: "f" * 40)  # the branch moved after it was read
    assert rg.main(_args(world, BRANCH)) == 1
    assert "not the local head ffffffffffff" in capsys.readouterr().err
    assert not list((_clone(world) / ".git" / "remote-gate").glob("*.bundle"))


def test_a_stale_bundle_head_is_refused(world: dict[str, Path]) -> None:
    bundle = world["work"] / "b.bundle"
    rg.make_bundle(world["local"], BRANCH, "origin/main", bundle)
    rg.check_bundle(world["local"], bundle, BRANCH, rg.local_head(world["local"], BRANCH))
    _commit(world["local"], "work.txt", "a later change\n", "later")
    with pytest.raises(rg.GateRefused, match="not the local head"):
        rg.check_bundle(world["local"], bundle, BRANCH, rg.local_head(world["local"], BRANCH))


def test_a_branch_with_nothing_over_the_base_is_bundled_whole_and_a_mistyped_base_refused(
    world: dict[str, Path],
) -> None:
    git(world["local"], "branch", "phase1/same", "origin/main")
    bundle = world["work"] / "same.bundle"
    rg.make_bundle(world["local"], "phase1/same", "origin/main", bundle)
    rg.check_bundle(world["local"], bundle, "phase1/same", rg.local_head(world["local"], "phase1/same"))
    with pytest.raises(rg.GateRefused, match="could not bundle"):
        rg.make_bundle(world["local"], "no-such-branch", "origin/main", world["work"] / "x.bundle")
    with pytest.raises(rg.GateRefused, match="not a local branch"):
        rg.local_head(world["local"], "no-such-branch")
    with pytest.raises(rg.GateRefused, match="base origin/mian is not a commit"):
        rg.make_bundle(world["local"], BRANCH, "origin/mian", world["work"] / "y.bundle")


def test_a_dropped_copy_is_retried_once_and_two_drops_refuse(
    world: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    _fakes(world["tmp"] / "bin", world["home"], scp_fails=1)
    assert rg.main(_args(world, BRANCH)) == 0
    (world["home"] / ".drops").write_text("-5")  # five more drops: both attempts fail
    assert rg.main(_args(world, BRANCH)) == 1
    assert "twice" in capsys.readouterr().err


def test_the_venv_is_rebuilt_when_the_lock_or_pyproject_changes_and_only_then(world: dict[str, Path]) -> None:
    installs = world["home"] / "pip-installs"
    assert rg.main(_args(world, BRANCH)) == 0
    assert rg.main(_args(world, BRANCH)) == 0
    assert len(installs.read_text().split()) == 1
    _commit(world["local"], "pyproject.toml", "[project]\nname = 'x'\n", "pyproject")
    assert rg.main(_args(world, BRANCH)) == 0
    _commit(world["local"], "constraints/py3.12.txt", "numpy==2\n", "lock")
    assert rg.main(_args(world, BRANCH)) == 0
    assert len(installs.read_text().split()) == 3


def test_a_failed_install_shows_its_log_and_is_rebuilt_next_time(
    world: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    (world["home"] / "pip-fails").write_text("")
    assert rg.main(_args(world, BRANCH)) == 1
    err = capsys.readouterr().err
    assert "pip broke" in err
    assert "(exit 4)" in err
    assert rg.main(_args(world, BRANCH)) == 0  # no stamp was written, so the half-built venv was rebuilt
    assert len((world["home"] / "pip-installs").read_text().split()) == 2


def test_a_python_with_no_lockfile_for_its_version_is_refused(
    world: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    _exe(world["python"], PYTHON.replace("${FAKE_PY_VERSION:-3.12}", "3.99"))
    assert rg.main(_args(world, BRANCH)) == 1
    assert "no lockfile constraints/py3.99.txt" in capsys.readouterr().err


def test_a_gate_still_running_for_the_branch_refuses_a_second_and_a_stale_pid_does_not(
    world: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    assert rg.main(_args(world, BRANCH)) == 0
    pidfile = _clone(world) / ".git" / "remote-gate" / f"{WT}.pid"
    assert not pidfile.exists()  # removed on exit
    pidfile.write_text(f"{os.getpid()}\n")  # a live process
    assert rg.main(_args(world, BRANCH)) == 1
    assert f"a gate for {BRANCH} is still running" in capsys.readouterr().err
    pidfile.write_text("2147483646\n")  # no such process
    assert rg.main(_args(world, BRANCH)) == 0


def test_the_verdict_takes_only_a_pass_for_the_head_the_remote_gated() -> None:
    head = "a" * 40

    def remote(text: str, code: int = 0) -> object:
        return rg.Remote(tuple(text.splitlines()), (), code, ())

    good = f"remote-gate: HEAD {head}\nprepush: PASS {head[:12]} (base x)\n"
    assert rg.verdict(remote(good), head) == f"prepush: PASS {head[:12]} (base x)"
    assert rg.verdict(remote(good.replace(f"PASS {head[:12]}", f"PASS {head[:14]}")), head)  # a longer short sha
    with pytest.raises(rg.GateRefused, match="gated"):
        rg.verdict(remote(good.replace(head, "b" * 40, 1)), head)  # the remote gated another commit
    with pytest.raises(rg.GateRefused, match="exit 1"):
        rg.verdict(remote(good, 1), head)  # a PASS line with a failing exit
    with pytest.raises(rg.GateRefused, match="failed"):
        rg.verdict(remote(f"remote-gate: HEAD {head}\nprepush: PASS {'b' * 12} (base x)\n"), head)


def test_the_pass_pattern_matches_the_line_prepush_prints_and_not_its_dirty_line() -> None:
    text = (ROOT / "scripts" / "prepush.sh").read_text()
    formats = re.findall(r"printf '\\nprepush: PASS ([^']*)\\n'", text)
    clean = [f for f in formats if f.startswith("%s")]
    dirty = [f for f in formats if not f.startswith("%s")]
    assert len(clean) == 1, formats
    assert len(dirty) == 1, formats
    assert rg.PASS.match("prepush: PASS " + clean[0] % ("0123456789ab", "origin/main", ""))
    assert not rg.PASS.match("prepush: PASS " + dirty[0].replace("%s", "0123456789ab"))


def test_the_script_carries_no_host_address_or_home_path() -> None:
    text = (ROOT / "scripts" / "remote_gate.py").read_text()
    assert not re.search(r"\b\d{1,3}(\.\d{1,3}){3}\b", text)  # no IP address
    assert "/Users/" not in text
    assert "/home/" not in text
    assert not re.search(r"[a-z0-9-]+\.(org|com|net|ts\.net|local)\b", text)  # no host name


def test_an_explicit_godot_with_a_space_reaches_the_gate_whole(
    world: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    _commit(world["local"], "scripts/prepush.sh", FAILING, "show godot")
    assert rg.main([*_args(world, BRANCH)[:-1], "--godot", "/opt/my godot/Godot", BRANCH]) == 1
    assert "godot=/opt/my godot/Godot " in capsys.readouterr().err
