# remote_gate, round 1: Architecture and Trust boundary (2026-11-22)

The reader's hand-back on PR #53 at 32fff60, condensed and saved by the author. Statuses are unset until a reviewer
sets them after the fold. No BLOCKER.

## SHOULD-FIX

- **S1, `scripts/remote_gate.py::refuse_shared_clone`: bypassable.** It compares the last two path parts with
  `overdrive-gate/repo`, so `overdrive-gate/x/../repo`, `./overdrive-gate/repo/`, an absolute path or a symlink on the
  remote all reach the shared clone and fetch into it, changing what every other session gates.
- **S2, `bundle_name` and the bundle destination: one shared namespace with collisions.** Bundles land in the gate
  root, which every session shares, and `/` becomes `-`, so `phase1/a-b` and `phase1-a/b` (or two sessions gating
  the same branch name) overwrite each other's bundle between the copy and the fetch.
- **S3, `gate_branch`: the remote's stderr is discarded.** A failing `git fetch`, `worktree add` or `pip install`
  (under `set -e`) exits nonzero with nothing shown but "the remote gated nothing".
- **S4, `REMOTE_SCRIPT`: the venv is never refreshed.** It is built once, when `.venv` is missing; a later lockfile
  or `pyproject.toml` change gates on the stale environment (the gate's lock check then refuses, with no route out),
  and a half-built venv from an interrupted install is kept forever.

## NIT

- **N1:** branch names and `--remote` reach `ssh`/`scp` argv with no `--`; an option-shaped value (`-oProxyCommand=…`)
  is read as an option.
- **N2:** only `$HOME` is masked; the remote user name and `TMPDIR` (which on macOS names a per-user folder) print.
- **N3:** `PASS` is not tied to `scripts/prepush.sh`'s `printf`; a change to the gate's line silently fails every run.
- **N4:** the remote command runs under a non-login zsh, so its `PATH` lacks Homebrew; `--python python3.12` fails
  there. Document an absolute `--python`.
