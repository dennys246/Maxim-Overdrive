# remote_gate, fold 1 (2026-11-22)

The author's account of how each round-1 finding was folded ([round1_arch_trust.md](round1_arch_trust.md), "AT";
[round1_exec_wire.md](round1_exec_wire.md), "EW"). These are the author's claims. A reviewer sets each status from
the tree in the delta round.

Each fix was mutation-checked. The fold reverted the fixed line and ran the named test, which went red; all 24
mutations were killed. One test was added after its first mutation survived (`remote_re`: the fake ssh's own `--`
check had masked it).

| Finding | Change | Test that kills its mutation |
|---|---|---|
| AT S1, EW N3 | `--clone` is one name matching `*-repo` under `--gate-root`, whose parts are plain names (no `..`, no absolute path). On the remote, the prepare step resolves the clone with `pwd -P` and refuses it if it is the shared `overdrive-gate/repo`. | `test_an_unsafe_clone_root_or_remote_is_refused_before_anything_runs`, `test_a_clone_that_resolves_to_the_shared_one_is_refused_on_the_remote` |
| AT S2, EW N1 | Bundles go to the session's own `<clone>/.git/remote-gate/`. Names flatten `/` to `+`, which branch names may not contain, so no two branches collide. | `test_a_branch_whose_name_has_a_slash_…` (worktree `phase1+x-y`) |
| AT S3, EW S5a | The remote's stderr is captured and shown in every refusal, through the same mask as stdout. | `test_a_worktree_on_another_branch_is_refused_and_its_message_reaches_stderr`, `test_a_connection_failure_shows_ssh_stderr_with_the_host_masked` |
| AT S4, EW S6, EW N5 | The venv is rebuilt whenever its stamp changes. The stamp is the Python path, its `X.Y` version and the git hash of `constraints/pyX.Y.txt` plus `pyproject.toml`. The lockfile is chosen by that version, and a missing one is refused. The stamp is written last, so an interrupted build is rebuilt next time. pip's log goes to `.venv/install.log`, and its tail is shown on failure. | `test_the_venv_is_rebuilt_…`, `test_a_failed_install_shows_its_log_…`, `test_a_python_with_no_lockfile_…` |
| AT N1 | Branches must match `[A-Za-z0-9._/-]+`, with no leading `-` and no empty, `.` or `..` part. `--remote` must be a plain host or alias. `ssh` and `scp` take `--` before the host. | `test_a_branch_name_outside_the_safe_alphabet_…`, `test_an_option_shaped_remote_is_refused_by_name_…`; the fakes refuse argv without `--` |
| AT N2 | The remote prints its home, user and `TMPDIR` as `PRIVATE` lines, which are never shown. Every shown line has them, and the host, replaced (`<home>`, `<user>`, `<tmp>`, `<remote>`), longest value first. | `test_a_failing_gate_exits_nonzero_and_masks_…` |
| AT N3 | `PASS` is held to `scripts/prepush.sh`'s clean `printf` by a test that renders it. The dirty-tree line must not match. | `test_the_pass_pattern_matches_the_line_prepush_prints_…` |
| AT N4 | The docstring, `--python`'s help and the CLAUDE.md line now ask for an absolute `--python`. | (docs) |
| EW S1, EW N2 | The worktree is added `--detach` and moved with `checkout --detach` to the bundle's ref, so a rewritten branch is gated as rewritten. No remote branch is created, which ends the sticky "branch exists" state. A worktree on another branch is refused. | `test_a_new_commit_and_a_rewritten_branch_…`, `test_a_worktree_removed_by_hand_is_added_again`, `test_a_worktree_on_another_branch_…` |
| EW S2 | The fake ssh runs the command under `/bin/zsh` (`/bin/sh` where there is none). `--godot` with a space reaches the gate whole. | `test_an_explicit_godot_with_a_space_…` (kills `" ".join`) |
| EW S3 | `check_bundle` is tested on the shipped path: a head that moved is refused before anything is copied. | `test_a_bundle_that_misses_the_local_head_…` |
| EW S4 | A planted local `GIT_DIR` (kills dropping `KEEP_ENV`). A planted remote `GIT_DIR`, which the remote prelude unsets. A planted remote `MAXIM_OVERDRIVE_UNLOCKED`, which the stub gate refuses (kills dropping `env -i`). | every passing test |
| EW S5c | `trap '' HUP` keeps a dropped session's gate under its shell. A pid file per branch refuses a second run while that pid lives, and is removed on exit. | `test_a_gate_still_running_for_the_branch_…` |
| EW S7 | The fake ssh empties the environment to `PATH=/usr/bin:/bin`. The fake scp makes no directories, so the prepare step creates them. | all |
| EW N4 | `PASS` takes a short sha of 12 to 40 characters that is a prefix of the head. | `test_the_verdict_…` |
| EW N6 | A base that isn't a commit is refused instead of silently bundling the whole branch. | `test_a_branch_with_nothing_over_the_base_…` |
| EW N7 | Not changed: `tail` buffers, so nothing streams. Python captures the output whole anyway. | — |

## Deviations and gaps (author)

- **The venv is not built in a temporary directory and renamed.** A venv's console scripts have their absolute
  path in their shebangs, so a renamed venv's `pytest` and `ruff` would point at the old name. The stamp, written
  last, makes the build atomic in effect instead.
- **The ssh-drop path is untested.** The fake can't drop a connection. The test covers only the pid-file refusal,
  not that `trap '' HUP` keeps the shell alive under a real `sshd`.
- **Migration on the mini.** `--clone` now takes `specgen-spike-repo`, not `overdrive-gate/specgen-spike-repo`.
  Worktrees made by 32fff60 (`phase1-…`, on branches) stay where they are. New runs make `phase1+…` worktrees and
  build their venvs once. The old bundles in `overdrive-gate/` are left for the owner to delete.
