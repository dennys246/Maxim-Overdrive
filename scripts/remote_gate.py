"""Gate branches on another machine (the Mac mini), the way ``scripts/prepush.sh`` gates them here.

For each branch it:
- bundles the branch's commits over a base (``origin/main`` by default; the whole branch when there are none);
- checks that the bundle's head is the local branch head;
- copies the bundle to the remote (one retry on a dropped connection);
- runs a bash script there on stdin, never through the remote's login shell (zsh read ``$b:r`` as a modifier once).

The remote script fetches the bundle into this session's own clone, adds or fast-forwards a worktree per branch with
its own ``.venv`` from ``constraints/py3.12.txt``, and runs the gate with an explicit environment. This script prints
the remote's ``prepush: PASS <sha>`` line, after checking that the remote gated the local head, or the failure lines
with the remote's home directory masked. It exits 1 on any refusal or failure.

The host is never written here: it comes from ``--remote`` or ``OVERDRIVE_REMOTE`` (an ssh host or config alias), and
the repository is public. Remote paths are relative to the remote's home. The shared ``overdrive-gate/repo`` clone
belongs to every session, so it is refused: fetching a branch into it changes what other sessions gate.

Run: ``python scripts/remote_gate.py --clone overdrive-gate/<session>-repo <branch> [<branch> ...]``
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
SHARED_CLONE = ("overdrive-gate", "repo")  # every session's clone on the mini: never fetched into
KEEP_ENV = frozenset({"PATH", "HOME", "USER", "LOGNAME", "LANG", "SSH_AUTH_SOCK"})  # no GIT_*, no proxy settings
PASS = re.compile(r"^prepush: PASS ([0-9a-f]{12})\b")
HEAD_LINE = re.compile(r"^remote-gate: HEAD ([0-9a-f]{40})$")
REMOTE_SCRIPT = r"""set -euo pipefail
abs() { case "$1" in /*) printf '%s' "$1" ;; *) printf '%s/%s' "$HOME" "$1" ;; esac; }
clone=$(abs "$1"); origin=$2; bundle=$(abs "$3"); branch=$4; name=$5; godot=$(abs "$6"); python=$7
mask() { sed -u -e "s#${HOME}#<home>#g"; }
if [ ! -d "${clone}/.git" ]; then git clone -q "${origin}" "${clone}"; fi
cd "${clone}"
git fetch -q origin
git fetch -q "${bundle}" "+refs/heads/${branch}:refs/remotes/bundle/${name}"
if [ ! -d ".worktrees/${name}" ]; then git worktree add -q ".worktrees/${name}" -b "${branch}" "bundle/${name}"; fi
cd ".worktrees/${name}"
git merge -q --ff-only "bundle/${name}"
echo "remote-gate: HEAD $(git rev-parse HEAD)"
if [ ! -d .venv ]; then
  "${python}" -m venv .venv
  .venv/bin/pip -q install -c constraints/py3.12.txt -e ".[dev,maxim]" > /dev/null
fi
set +e
env -i PATH="${PATH}" HOME="${HOME}" LANG="${LANG:-C}" GODOT="${godot}" bash scripts/prepush.sh 2>&1 | mask | tail -n 40
status=${PIPESTATUS[0]}
exit "${status}"
"""


class GateRefused(Exception):
    """A branch that can't be gated, or whose gate failed: the message says which and why."""


@dataclass(frozen=True)
class Config:
    remote: str
    clone: str
    gate_root: str
    godot: str
    python: str
    base: str
    origin: str
    repo: Path
    work: Path


def _env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k in KEEP_ENV}


def _run(cmd: list[str], *, cwd: Path | None = None, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, input=stdin, capture_output=True, text=True, env=_env(), check=False)


def refuse_shared_clone(clone: str) -> None:
    if PurePosixPath(clone).parts[-2:] == SHARED_CLONE:
        raise GateRefused(f"{clone} is the clone every session shares; name this session's own")


def bundle_name(branch: str) -> str:
    return branch.replace("/", "-")


def local_head(repo: Path, branch: str) -> str:
    r = _run(["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}^{{commit}}"], cwd=repo)
    if r.returncode != 0:
        raise GateRefused(f"{branch} is not a local branch")
    return r.stdout.strip()


def make_bundle(repo: Path, branch: str, base: str, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    if _run(["git", "bundle", "create", str(out), f"{base}..{branch}"], cwd=repo).returncode == 0:
        return
    whole = _run(["git", "bundle", "create", str(out), branch], cwd=repo)  # no commits over the base
    if whole.returncode != 0:
        raise GateRefused(f"could not bundle {branch}: {whole.stderr.strip()}")


def check_bundle(repo: Path, bundle: Path, branch: str, head: str) -> None:
    r = _run(["git", "bundle", "list-heads", str(bundle), f"refs/heads/{branch}"], cwd=repo)
    heads = r.stdout.split()[:1]
    if heads != [head]:
        raise GateRefused(f"the bundle for {branch} holds {heads or 'nothing'}, not the local head {head[:12]}")


def copy(remote: str, bundle: Path, dest: str) -> None:
    cmd = ["scp", "-q", "-o", "BatchMode=yes", str(bundle), f"{remote}:{dest}"]
    if _run(cmd).returncode != 0 and _run(cmd).returncode != 0:  # one retry: connections drop
        raise GateRefused(f"could not copy the bundle for {bundle.stem} (twice)")


def verdict(stdout: str, code: int, head: str) -> str:
    """The remote's PASS line, if it gated exactly ``head`` and passed; else GateRefused with the failure lines."""
    lines = stdout.splitlines()
    gated = [m.group(1) for line in lines if (m := HEAD_LINE.match(line))]
    if gated != [head]:
        raise GateRefused(f"the remote gated {gated or 'nothing'}, not {head[:12]}:\n" + "\n".join(lines[-20:]))
    passed = [line for line in lines if (m := PASS.match(line)) and m.group(1) == head[:12]]
    if code != 0 or not passed:
        raise GateRefused(f"the gate failed for {head[:12]} (exit {code}):\n" + "\n".join(lines[-20:]))
    return passed[-1]


def gate_branch(cfg: Config, branch: str) -> str:
    head = local_head(cfg.repo, branch)
    name = bundle_name(branch)
    bundle = cfg.work / f"{name}.bundle"
    make_bundle(cfg.repo, branch, cfg.base, bundle)
    check_bundle(cfg.repo, bundle, branch, head)
    dest = f"{cfg.gate_root}/{name}.bundle"
    copy(cfg.remote, bundle, dest)
    remote_cmd = shlex.join(["bash", "-s", "--", cfg.clone, cfg.origin, dest, branch, name, cfg.godot, cfg.python])
    r = _run(["ssh", "-o", "BatchMode=yes", cfg.remote, remote_cmd], stdin=REMOTE_SCRIPT)
    return verdict(r.stdout, r.returncode, head)


def _origin_url(repo: Path) -> str:
    return _run(["git", "remote", "get-url", "origin"], cwd=repo).stdout.strip()


def config(argv: list[str]) -> tuple[Config, list[str]]:
    p = argparse.ArgumentParser(description="Gate branches on a remote machine.")
    p.add_argument("branches", nargs="+")
    p.add_argument("--remote", default=os.environ.get("OVERDRIVE_REMOTE", ""), help="ssh host or alias")
    p.add_argument("--clone", required=True, help="this session's own clone, relative to the remote's home")
    p.add_argument("--gate-root", default="overdrive-gate", help="where bundles go, relative to the remote's home")
    p.add_argument("--godot", default="", help="the remote Godot binary (default: under the gate root)")
    p.add_argument("--python", default="python3.12", help="the remote Python that makes each worktree's .venv")
    p.add_argument("--base", default="origin/main")
    p.add_argument("--repo", type=Path, default=ROOT)
    p.add_argument("--work", type=Path, default=ROOT / ".remote_gate", help="where bundles are made here")
    a = p.parse_args(argv)
    if not a.remote:
        raise GateRefused("no remote: pass --remote or set OVERDRIVE_REMOTE")
    refuse_shared_clone(a.clone)
    godot = a.godot or f"{a.gate_root}/godot/Godot.app/Contents/MacOS/Godot"
    cfg = Config(a.remote, a.clone, a.gate_root, godot, a.python, a.base, _origin_url(a.repo), a.repo, a.work)
    return cfg, a.branches


def main(argv: list[str] | None = None) -> int:
    try:
        cfg, branches = config(sys.argv[1:] if argv is None else argv)
    except GateRefused as exc:
        print(f"remote_gate: {exc}", file=sys.stderr)
        return 1
    failed = 0
    for branch in branches:
        try:
            print(f"{branch}: {gate_branch(cfg, branch)}")
        except GateRefused as exc:
            print(f"{branch}: REFUSED: {exc}", file=sys.stderr)
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
