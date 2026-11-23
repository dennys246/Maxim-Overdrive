# remote_gate, round 1: Executor and Wire integrity (2026-11-22)

The reader's hand-back on PR #53 at 32fff60, condensed and saved by the author. Statuses are unset until a reviewer
sets them after the fold. The reader ran six mutations against `tests/test_remote_gate.py`; all six survived (S1–S4,
N2). No BLOCKER.

## SHOULD-FIX

- **S1, the fast-forward test commits nothing between runs.** The second `main` call gates the same head, so deleting
  `git merge --ff-only` stays green (mutation survived).
- **S2, quoting is unguarded.** Replacing `shlex.join` with `" ".join` stays green: no argument carries a space or a
  shell character. The fake `ssh` runs the command with bash, while the real remote's login shell is zsh.
- **S3, `check_bundle` is only unit-tested.** Deleting its call in `gate_branch` stays green (mutation survived).
- **S4, `_env` and `env -i` are untested.** Dropping the `KEEP_ENV` filter, or `env -i` in the remote script, stays
  green (both mutations survived): nothing plants `GIT_DIR` or `MAXIM_OVERDRIVE_UNLOCKED`.
- **S5, failure handling.** The remote's stderr is dropped; `worktree add -b` leaves a remote branch behind, so a
  worktree removed by hand can never be re-added ("branch exists"); an ssh drop leaves the gate running, and the
  next run fast-forwards the worktree under it.
- **S6, the venv is never refreshed** (as Architecture S4).
- **S7, the fake remote is too forgiving.** The fake `scp` runs `mkdir -p` (the real one doesn't), the fake `ssh`
  inherits the caller's `PATH` and bash, so a script that needs Homebrew tools or bash 4 passes here and fails there.

## NIT

- **N1:** `bundle_name` collides (as Architecture S2).
- **N2:** `-b <branch>` versus `--detach` is untested (mutation survived); a rewritten branch's `+` refspec is too.
- **N3:** the shared-clone check should resolve the path on the remote (realpath), not compare strings here.
- **N4:** `--short=12` can print more than 12 characters when ambiguous; `PASS` takes exactly 12.
- **N5:** `constraints/py3.12.txt` is hard-coded whatever `--python` is.
- **N6:** `make_bundle` falls back to a whole bundle when the base is mistyped, hiding the mistake.
- **N7:** `tail -n 40` buffers to the end, so nothing streams; only worth a note.
