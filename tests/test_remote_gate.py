"""scripts/remote_gate.py: gate branches on another machine, against a fake remote under tmp_path (no network).

The fake ``ssh`` runs the command in a home directory under tmp_path with bash; the fake ``scp`` copies into it. The
"origin" is a local repository whose ``scripts/prepush.sh`` is a stub, so the tests check what the script does around
the gate (bundling, refs, worktrees, the PASS line, refusals), not the gate itself.
"""

from __future__ import annotations

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
PASSING = '#!/bin/bash\necho "godot=$GODOT"\necho "prepush: PASS $(git rev-parse --short=12 HEAD) (stub)"\n'
FAILING = '#!/bin/bash\necho "godot=$GODOT"\necho "FAILED tests/test_x.py::test_y"\nexit 3\n'


def _exe(path: Path, text: str) -> Path:
    path.write_text(text)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def _fakes(bin_dir: Path, home: Path, *, scp_fails: int = 0) -> None:
    bin_dir.mkdir()
    _exe(bin_dir / "ssh", f'#!/bin/bash\ncd "{home}" && HOME="{home}" exec bash -c "$4"\n')
    drops = home / ".drops"
    _exe(
        bin_dir / "scp",
        "#!/bin/bash\n"
        f'n=$(cat "{drops}" 2>/dev/null || echo 0)\n'
        f'if [ "$n" -lt {scp_fails} ]; then echo $((n+1)) > "{drops}"; exit 1; fi\n'
        f'dest="${{5#*:}}"; mkdir -p "{home}/$(dirname "$dest")"; cp "$4" "{home}/$dest"\n',
    )


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    origin, home = tmp_path / "origin", tmp_path / "home"
    home.mkdir()
    origin.mkdir()
    git(origin, "init", "-q", "-b", "main")
    (origin / "scripts").mkdir()
    _exe(origin / "scripts" / "prepush.sh", PASSING)
    git(origin, "add", "-A")
    git(origin, "commit", "-q", "-m", "base")
    git(tmp_path, "clone", "-q", str(origin), "local")
    local = tmp_path / "local"
    git(local, "checkout", "-q", "-b", BRANCH)
    (local / "work.txt").write_text("a change\n")
    git(local, "add", "-A")
    git(local, "commit", "-q", "-m", "work")
    _fakes(tmp_path / "bin", home)
    python = _exe(
        tmp_path / "fakepy",
        '#!/bin/bash\nmkdir -p "$3/bin"; printf "#!/bin/bash\\n" > "$3/bin/pip"\nchmod +x "$3/bin/pip"\n',
    )
    monkeypatch.setenv("PATH", f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("OVERDRIVE_REMOTE", HOST)
    return {"tmp": tmp_path, "origin": origin, "home": home, "local": local, "python": python, "work": tmp_path / "w"}


def _args(w: dict[str, Path], *branches: str) -> list[str]:
    return [
        "--clone",
        "gate/session-repo",
        "--repo",
        str(w["local"]),
        "--work",
        str(w["work"]),
        "--python",
        str(w["python"]),
        *branches,
    ]


def _private_value_anywhere(root: Path) -> list[Path]:
    return [p for p in root.rglob("*") if p.is_file() and HOST.encode() in p.read_bytes()]


def test_a_branch_whose_name_has_a_slash_is_gated_and_its_pass_line_printed(
    world: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    head = git(world["local"], "rev-parse", BRANCH).stdout.strip()
    assert rg.main(_args(world, BRANCH)) == 0
    out = capsys.readouterr()
    assert out.out.strip() == f"{BRANCH}: prepush: PASS {head[:12]} (stub)"
    worktree = world["home"] / "gate" / "session-repo" / ".worktrees" / "phase1-x-y"
    assert git(worktree, "rev-parse", "HEAD").stdout.strip() == head  # the ref survived the slash
    assert HOST not in out.out + out.err
    assert not _private_value_anywhere(world["tmp"])
    assert rg.main(_args(world, BRANCH)) == 0  # a second run fast-forwards the existing worktree


def test_a_failing_gate_exits_nonzero_and_masks_the_remote_home(
    world: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    _exe(world["local"] / "scripts" / "prepush.sh", FAILING)
    git(world["local"], "commit", "-q", "-am", "a failing gate")
    assert rg.main(_args(world, BRANCH)) == 1
    err = capsys.readouterr().err
    assert "FAILED tests/test_x.py::test_y" in err
    assert "(exit 3)" in err
    assert "godot=<home>/overdrive-gate/godot/Godot.app/Contents/MacOS/Godot" in err
    assert str(world["home"]) not in err
    assert HOST not in err


def test_the_clone_every_session_shares_is_refused_before_anything_runs(
    world: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    args = _args(world, BRANCH)
    args[1] = "overdrive-gate/repo"
    assert rg.main(args) == 1
    assert "every session shares" in capsys.readouterr().err
    assert not world["work"].exists()
    assert not (world["home"] / "overdrive-gate").exists()


def test_no_remote_is_refused(world: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OVERDRIVE_REMOTE")
    monkeypatch.setattr(sys, "argv", ["remote_gate.py", *_args(world, BRANCH)])
    assert rg.main() == 1


def test_a_stale_bundle_head_is_refused(world: dict[str, Path]) -> None:
    bundle = world["work"] / "b.bundle"
    rg.make_bundle(world["local"], BRANCH, "origin/main", bundle)
    head = rg.local_head(world["local"], BRANCH)
    rg.check_bundle(world["local"], bundle, BRANCH, head)
    (world["local"] / "work.txt").write_text("a later change\n")
    git(world["local"], "commit", "-q", "-am", "later")
    with pytest.raises(rg.GateRefused, match="not the local head"):
        rg.check_bundle(world["local"], bundle, BRANCH, rg.local_head(world["local"], BRANCH))


def test_a_branch_with_nothing_over_the_base_is_bundled_whole(world: dict[str, Path]) -> None:
    git(world["local"], "branch", "phase1/same", "origin/main")
    bundle = world["work"] / "same.bundle"
    rg.make_bundle(world["local"], "phase1/same", "origin/main", bundle)
    rg.check_bundle(world["local"], bundle, "phase1/same", rg.local_head(world["local"], "phase1/same"))
    with pytest.raises(rg.GateRefused, match="could not bundle"):
        rg.make_bundle(world["local"], "no-such-branch", "origin/main", world["work"] / "x.bundle")
    with pytest.raises(rg.GateRefused, match="not a local branch"):
        rg.local_head(world["local"], "no-such-branch")


def test_a_dropped_copy_is_retried_once_and_two_drops_refuse(
    world: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    (world["tmp"] / "bin" / "ssh").unlink()
    (world["tmp"] / "bin" / "scp").unlink()
    (world["tmp"] / "bin").rmdir()
    _fakes(world["tmp"] / "bin", world["home"], scp_fails=1)
    assert rg.main(_args(world, BRANCH)) == 0
    (world["home"] / ".drops").write_text("-5")  # five more drops: both attempts fail
    assert rg.main(_args(world, BRANCH)) == 1
    assert "twice" in capsys.readouterr().err


def test_the_verdict_takes_only_a_pass_for_the_head_the_remote_gated() -> None:
    head = "a" * 40
    good = f"remote-gate: HEAD {head}\nprepush: PASS {head[:12]} (base x)\n"
    assert rg.verdict(good, 0, head) == f"prepush: PASS {head[:12]} (base x)"
    with pytest.raises(rg.GateRefused, match="gated"):
        rg.verdict(good.replace(head, "b" * 40, 1), 0, head)  # the remote gated another commit
    with pytest.raises(rg.GateRefused, match="exit 1"):
        rg.verdict(good, 1, head)  # a PASS line with a failing exit
    with pytest.raises(rg.GateRefused, match="failed"):
        rg.verdict(f"remote-gate: HEAD {head}\nprepush: PASS {'b' * 12}\n", 0, head)  # a PASS for another sha


def test_the_script_carries_no_host_address_or_home_path() -> None:
    text = (ROOT / "scripts" / "remote_gate.py").read_text()
    assert not re.search(r"\b\d{1,3}(\.\d{1,3}){3}\b", text)  # no IP address
    assert "/Users/" not in text
    assert "/home/" not in text
    assert not re.search(r"[a-z0-9-]+\.(org|com|net|ts\.net|local)\b", text)  # no host name


def test_an_explicit_godot_is_passed_through(world: dict[str, Path], capsys: pytest.CaptureFixture[str]) -> None:
    _exe(world["local"] / "scripts" / "prepush.sh", FAILING)
    git(world["local"], "commit", "-q", "-am", "show godot")
    assert rg.main([*_args(world, BRANCH)[:-1], "--godot", "/opt/godot/Godot", BRANCH]) == 1
    assert "godot=/opt/godot/Godot" in capsys.readouterr().err
