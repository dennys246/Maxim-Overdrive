# remote_gate, fold 2: the delta round on de5979a (2026-11-23)

This records the author's claims, not statuses; a reviewer sets those from the tree. The findings are in `delta1.md`.
The branch merged `origin/main` first (40f0b27), then folded the round below.

| Finding | Change (author's claim) |
|---|---|
| D-S1 ssh names the resolved host | `ssh_masks` reads `hostname` and `user` from `ssh -G <remote>`, which connects to nothing, and every ssh and scp message goes through those masks along with the alias. If `ssh -G` fails, the run is refused with the alias masked. Tests: the fake resolves the alias `gate-box` to the stand-in host, and a refused connection prints both; the test runs with the host and with the alias, and asserts neither appears. |
| D-S2 the user mask is unguarded | Kept, and now tested. A remote message can name the user outside any path (for example git's or ssh's own messages), so the mask is needed. The failing stub prints `ran as $(id -un), alone`, and the test asserts `ran as <user>, alone`. The fake's `ssh -G` reports a different user, so only the `PRIVATE user` line can hide the real one. |
| D-S3 `trap '' HUP` is inert | The trap is removed, and so is the claim that it helps. The docstring now says plainly that a dropped connection is not survived: the gate may run on until it next writes, and the pid file refuses a second gate of that branch meanwhile. Deferred: surviving a drop (`nohup` and a log read back). Trigger: a run on the mini actually lost to a drop. |
| D-S3 (related) `bash -s` and stdin | `_script` wraps each remote script's body in one function, which bash reads whole before running it. The function is called with `</dev/null`, so no child can read the rest of the script. Test: a fake Python whose venv step runs `cat > /dev/null`. |
| D-N1 two stamp parts unguarded | Test: a file planted in the venv is gone after a lock change. A second interpreter at the same version triggers a fourth install. |
| D-N2 a worktree deleted by hand | `git worktree prune` (in the session's own clone) runs before `worktree add`. Test: `shutil.rmtree` of the worktree, then the branch is gated again. |
| D-N3 a clone inside the shared clone | Checked here too: `clone_path` refuses a path under `overdrive-gate/repo/`. On the remote, `PREPARE_SCRIPT` refuses a clone whose real path is the shared clone or lies inside it (a `case` on the prefix replaces the equality test). Tests: the gate-root `overdrive-gate/repo` is refused locally, and a symlinked gate root that lands inside the shared working tree is refused remotely. |
| D-N4 scp's stderr dropped | The second failure's stderr is shown through the same masks. Test: the fake scp's drop prints the stand-in host, and the test asserts `(twice): lost connection to <remote>`. |
| D-N5 over-masking | Skipped. It only affects readability: a short alias or user can be replaced inside unrelated words. |
| D-N6 the pid file isn't atomic | A stale pid file is removed, then the new one is written under `noclobber`; the loser of a simultaneous start is refused. A window is left: two runs can both remove the same stale file before either writes. No test exercises the noclobber refusal, because two runs can't be made to start at the same moment without a race in the test. |

Mutation check: one mutation per change, run against `tests/test_remote_gate.py`. Eleven were killed, among them the removal of the function wrapper. Two survived:

- **Dropping `</dev/null`:** an equivalent mutation. Once the wrapper has made bash read the whole script, stdin is already at end of file, so the redirect is defence in depth, not the guard.
- **Dropping noclobber:** untested, as the table says.
