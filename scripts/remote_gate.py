"""Gate branches on another machine (the Mac mini), the way ``scripts/prepush.sh`` gates them here.

For each run it prepares this session's own clone on the remote (cloning it if missing, and refusing it if it
resolves to the clone every session shares). For each branch it:
- bundles the branch's commits over a base (``origin/main`` by default; the whole branch when there are none);
- checks that the bundle's head is the local branch head;
- copies the bundle into the clone's ``.git/remote-gate/`` (one retry on a dropped connection);
- runs a bash script there on stdin, never through the remote's login shell (zsh read ``$b:r`` as a modifier once).

The remote script fetches the bundle (a rewritten branch is taken as rewritten), checks out a detached worktree per
branch, rebuilds its ``.venv`` whenever the lockfile for ``--python``'s version or ``pyproject.toml`` changed, and
runs the gate with an explicit environment. This script prints the remote's ``prepush: PASS <sha>`` line, after
checking that the remote gated the local head, or the failure lines, stderr included. It exits 1 on any refusal or
failure.

Nothing private is written here or printed: the host comes from ``--remote`` or ``OVERDRIVE_REMOTE`` (an ssh host or
config alias), and the repository is public. Every remote output passes a mask that replaces the host, the remote
home, user and temp directory. Remote paths are relative to the remote's home. The remote runs its commands under a
non-login shell, so ``--python`` should be an absolute path (Homebrew's ``bin`` isn't on that ``PATH``).

Run: ``python scripts/remote_gate.py --clone <session>-repo --python <abs python3.12> <branch> [<branch> ...]``
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED_CLONE = "overdrive-gate/repo"  # every session's clone on the mini: never fetched into
KEEP_ENV = frozenset({"PATH", "HOME", "USER", "LOGNAME", "LANG", "SSH_AUTH_SOCK"})  # no GIT_*, no proxy settings
PASS = re.compile(r"^prepush: PASS ([0-9a-f]{12,40}) ")  # scripts/prepush.sh's printf, held by a test
HEAD_LINE = re.compile(r"^remote-gate: HEAD ([0-9a-f]{40})$")
PRIVATE_LINE = re.compile(r"^remote-gate: PRIVATE (home|user|tmp) (.+)$")
BRANCH = re.compile(r"^[A-Za-z0-9._/-]+$")  # so "+" can flatten "/" without a collision
CLONE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*-repo$")  # one path component, never the shared "repo"
COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")  # no leading dot, so never ".."
REMOTE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._@-]*$")  # an ssh host or alias, never option-shaped

PRELUDE = r"""set -euo pipefail
printf 'remote-gate: PRIVATE home %s\n' "${HOME}"
printf 'remote-gate: PRIVATE user %s\n' "$(id -un)"
printf 'remote-gate: PRIVATE tmp %s\n' "${TMPDIR:-/tmp}"
for v in $(env | sed -n 's/^\(GIT_[A-Za-z0-9_]*\)=.*/\1/p'); do unset "${v}"; done
"""
PREPARE_SCRIPT = (
    PRELUDE
    + r"""clone="${HOME}/$1"; origin=$2; shared="${HOME}/$3"
if [ ! -d "${clone}/.git" ]; then mkdir -p "$(dirname "${clone}")"; git clone -q "${origin}" "${clone}"; fi
real=$(cd "${clone}" && pwd -P)
if [ -d "${shared}" ] && [ "${real}" = "$(cd "${shared}" && pwd -P)" ]; then
  echo "remote-gate: $1 resolves to the clone every session shares" >&2; exit 2
fi
mkdir -p "${clone}/.git/remote-gate"
"""
)
GATE_SCRIPT = (
    PRELUDE
    + r"""cd "${HOME}/$1"; branch=$2; name=$3; python=$5
case "$4" in /*) godot=$4 ;; *) godot="${HOME}/$4" ;; esac
trap '' HUP  # a dropped ssh leaves the gate running; the pid file below then refuses a second run until it ends
pidfile="${PWD}/.git/remote-gate/${name}.pid"
if [ -f "${pidfile}" ] && kill -0 "$(cat "${pidfile}")" 2>/dev/null; then
  echo "remote-gate: a gate for ${branch} is still running (pid $(cat "${pidfile}"))" >&2; exit 2
fi
echo "$$" > "${pidfile}"; trap 'rm -f "${pidfile}"' EXIT
git fetch -q origin
git fetch -q ".git/remote-gate/${name}.bundle" "+refs/heads/${branch}:refs/remotes/bundle/${name}"
wt=".worktrees/${name}"
if [ -d "${wt}" ]; then
  cur=$(git -C "${wt}" symbolic-ref -q --short HEAD || true)
  if [ -n "${cur}" ] && [ "${cur}" != "${branch}" ]; then
    echo "remote-gate: ${wt} is on ${cur}, not ${branch}" >&2; exit 2
  fi
  git -C "${wt}" checkout -q --detach "bundle/${name}"
else
  git worktree add -q --detach "${wt}" "bundle/${name}"
fi
cd "${wt}"
echo "remote-gate: HEAD $(git rev-parse HEAD)"
ver=$("${python}" -c 'import sys; print("%d.%d" % sys.version_info[:2])')
lock="constraints/py${ver}.txt"
if [ ! -f "${lock}" ]; then echo "remote-gate: no lockfile ${lock} for ${python}" >&2; exit 2; fi
stamp="${python} ${ver} $(cat "${lock}" pyproject.toml | git hash-object --stdin)"
if [ "$(cat .venv/remote-gate.stamp 2>/dev/null || true)" != "${stamp}" ]; then
  rm -rf .venv  # the stamp is written last, so an interrupted build is rebuilt next time
  "${python}" -m venv .venv
  if ! .venv/bin/pip -q install -c "${lock}" -e ".[dev,maxim]" > .venv/install.log 2>&1; then
    tail -n 20 .venv/install.log >&2; exit 4
  fi
  printf '%s\n' "${stamp}" > .venv/remote-gate.stamp
fi
set +e
env -i PATH="${PATH}" HOME="${HOME}" LANG="${LANG:-C}" GODOT="${godot}" bash scripts/prepush.sh 2>&1 | tail -n 40
status=${PIPESTATUS[0]}
exit "${status}"
"""
)


class GateRefused(Exception):
    """A branch that can't be gated, or whose gate failed: the message says which and why."""


@dataclass(frozen=True)
class Config:
    remote: str
    clone: str  # relative to the remote's home: <gate root>/<session>-repo
    godot: str
    python: str
    base: str
    origin: str
    repo: Path
    work: Path


@dataclass(frozen=True)
class Remote:
    """One ssh call's result: the raw stdout lines (for the HEAD and PASS lines) and the masked text to show."""

    lines: tuple[str, ...]
    errors: tuple[str, ...]  # stderr
    code: int
    private: tuple[tuple[str, str], ...]  # (value, label), longest value first

    def shown(self, text: str) -> str:
        for value, label in self.private:
            text = text.replace(value, label)
        return text

    def tail(self) -> str:
        return self.shown("\n".join([*self.lines[-20:], *self.errors[-20:]]))


def _env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k in KEEP_ENV}


def _run(cmd: list[str], *, cwd: Path | None = None, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, input=stdin, capture_output=True, text=True, env=_env(), check=False)


def flat_name(branch: str) -> str:
    """The branch as one path component; ``+`` is outside ``BRANCH``'s alphabet, so no two branches share a name."""
    return branch.replace("/", "+")


def check_branch(branch: str) -> None:
    parts = branch.split("/")
    if not BRANCH.match(branch) or branch.startswith("-") or any(p in ("", ".", "..") for p in parts):
        raise GateRefused(f"{branch!r} is not a branch name this script gates (letters, digits, . _ - and /)")


def clone_path(gate_root: str, clone: str) -> str:
    """This session's clone under the gate root, refused unless both are plain names and the clone isn't shared."""
    if not CLONE.match(clone):
        raise GateRefused(f"{clone!r} must be one name ending in -repo; the shared clone is never this session's own")
    if not all(COMPONENT.match(p) for p in gate_root.split("/")):
        raise GateRefused(f"{gate_root!r} must be a relative path of plain names")
    return f"{gate_root}/{clone}"


def local_head(repo: Path, branch: str) -> str:
    r = _run(["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}^{{commit}}"], cwd=repo)
    if r.returncode != 0:
        raise GateRefused(f"{branch} is not a local branch")
    return r.stdout.strip()


def make_bundle(repo: Path, branch: str, base: str, out: Path) -> None:
    if _run(["git", "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}"], cwd=repo).returncode != 0:
        raise GateRefused(f"the base {base} is not a commit here")
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


def ssh(cfg: Config, script: str, *args: str) -> Remote:
    """Run ``script`` under bash on the remote, with ``args``; its output is masked before anyone sees it."""
    r = _run(["ssh", "-o", "BatchMode=yes", "--", cfg.remote, shlex.join(["bash", "-s", "--", *args])], stdin=script)
    labels = {"home": "<home>", "user": "<user>", "tmp": "<tmp>"}
    private = {cfg.remote: "<remote>"}
    lines: list[str] = []
    for line in r.stdout.splitlines():
        if m := PRIVATE_LINE.match(line):
            private[m.group(2).rstrip("/")] = labels[m.group(1)]
        else:
            lines.append(line)
    ordered = tuple(sorted(((v, k) for v, k in private.items() if v), key=lambda p: -len(p[0])))
    remote = Remote(tuple(lines), tuple(r.stderr.splitlines()), r.returncode, ordered)
    if r.returncode != 0 and not any(HEAD_LINE.match(line) for line in lines):
        raise GateRefused(f"the remote refused (exit {r.returncode}):\n{remote.tail()}")
    return remote


def prepare(cfg: Config) -> None:
    ssh(cfg, PREPARE_SCRIPT, cfg.clone, cfg.origin, SHARED_CLONE)


def copy(cfg: Config, bundle: Path, dest: str) -> None:
    cmd = ["scp", "-q", "-o", "BatchMode=yes", "--", str(bundle), f"{cfg.remote}:{dest}"]
    if _run(cmd).returncode != 0 and _run(cmd).returncode != 0:  # one retry: connections drop
        raise GateRefused(f"could not copy the bundle for {bundle.stem} (twice)")


def verdict(remote: Remote, head: str) -> str:
    """The remote's PASS line, if it gated exactly ``head`` and passed; else GateRefused with the failure lines."""
    gated = [m.group(1) for line in remote.lines if (m := HEAD_LINE.match(line))]
    if gated != [head]:
        raise GateRefused(f"the remote gated {gated or 'nothing'}, not {head[:12]}:\n{remote.tail()}")
    passed = [line for line in remote.lines if (m := PASS.match(line)) and head.startswith(m.group(1))]
    if remote.code != 0 or not passed:
        raise GateRefused(f"the gate failed for {head[:12]} (exit {remote.code}):\n{remote.tail()}")
    return passed[-1]


def gate_branch(cfg: Config, branch: str) -> str:
    head = local_head(cfg.repo, branch)
    name = flat_name(branch)
    bundle = cfg.work / f"{name}.bundle"
    make_bundle(cfg.repo, branch, cfg.base, bundle)
    check_bundle(cfg.repo, bundle, branch, head)
    copy(cfg, bundle, f"{cfg.clone}/.git/remote-gate/{name}.bundle")
    return verdict(ssh(cfg, GATE_SCRIPT, cfg.clone, branch, name, cfg.godot, cfg.python), head)


def _origin_url(repo: Path) -> str:
    return _run(["git", "remote", "get-url", "origin"], cwd=repo).stdout.strip()


def config(argv: list[str]) -> tuple[Config, list[str]]:
    p = argparse.ArgumentParser(description="Gate branches on a remote machine.")
    p.add_argument("branches", nargs="+")
    p.add_argument("--remote", default=os.environ.get("OVERDRIVE_REMOTE", ""), help="ssh host or alias")
    p.add_argument("--clone", required=True, help="this session's own clone: one name ending in -repo")
    p.add_argument("--gate-root", default="overdrive-gate", help="where clones live, relative to the remote's home")
    p.add_argument("--godot", default="", help="the remote Godot binary (default: under the gate root)")
    p.add_argument("--python", default="python3.12", help="the remote Python for each .venv: give an absolute path")
    p.add_argument("--base", default="origin/main")
    p.add_argument("--repo", type=Path, default=ROOT)
    p.add_argument("--work", type=Path, default=ROOT / ".remote_gate", help="where bundles are made here")
    a = p.parse_args(argv)
    if not REMOTE.match(a.remote):
        raise GateRefused("no usable remote: pass --remote or set OVERDRIVE_REMOTE to an ssh host or alias")
    clone = clone_path(a.gate_root, a.clone)
    for branch in a.branches:
        check_branch(branch)
    godot = a.godot or f"{a.gate_root}/godot/Godot.app/Contents/MacOS/Godot"
    return Config(a.remote, clone, godot, a.python, a.base, _origin_url(a.repo), a.repo, a.work), a.branches


def main(argv: list[str] | None = None) -> int:
    try:
        cfg, branches = config(sys.argv[1:] if argv is None else argv)
        prepare(cfg)
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
