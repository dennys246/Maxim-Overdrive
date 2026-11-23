# remote_gate, delta round 1 on de5979a (2026-11-22)

Reviewer: one reader, all lenses (Executor, Architecture, Wire integrity, Trust boundary). Scope: `git show de5979a`
over 32fff60. Statuses below are the reviewer's, read from the tree. No BLOCKER.

Ran: `tests/test_remote_gate.py` + `tests/test_isolation.py` on a scratch copy of de5979a, 104 passed. Twenty
mutations of `scripts/remote_gate.py`, `test_remote_gate.py` each: 15 killed, 5 survived (listed under the findings;
two of them are equivalent mutations). Re-ran the author's `shlex.join` -> `" ".join` mutation: killed by
`test_an_explicit_godot_with_a_space_reaches_the_gate_whole`.

## Statuses

| Finding | Status | Note |
|---|---|---|
| AT S1, EW N3 | fixed | `CLONE`/`COMPONENT` refuse paths; remote `pwd -P` check, mutation `pwd -P`->`pwd` killed. Residue: D-N3 |
| AT S2, EW N1 | fixed | per-clone `.git/remote-gate/`, `/`->`+` is injective over `BRANCH` |
| AT S3 | fixed | ssh stderr reaches every ssh refusal; scp stderr is still dropped (D-N4). The fix opens D-S1 |
| AT S4, EW S6, EW N5 | fixed | stamp written last; lockfile by version (mutation killed). Two parts unguarded: D-N1 |
| AT N1 | fixed | `--` on ssh and scp, `BRANCH`/`REMOTE` validated; mutations killed |
| AT N2 | open | the user mask is in the code but no test guards it (D-S2) |
| AT N3 | fixed | `test_the_pass_pattern_…` renders prepush.sh's printf |
| AT N4 | fixed | docstring, `--python` help, CLAUDE.md line |
| EW S1 | fixed | new commit and `--amend` both gated at the new head |
| EW S2 | fixed | fake runs zsh; `" ".join` killed (re-run here) |
| EW S3 | fixed | shipped-path test; asserts no bundle copied |
| EW S4 | fixed | planted local and remote `GIT_DIR`, remote `MAXIM_OVERDRIVE_UNLOCKED`; the GIT_* unset mutation killed |
| EW S5a | fixed | as AT S3 |
| EW S5b | fixed | `--detach` ends "branch exists"; a dir deleted with `rm -rf` still can't be re-added (D-N2) |
| EW S5c | fixed (second-run half); deferred (drop half) | pid file guarded (mutation killed). The drop path: deferred, reason the fake can't drop a connection, trigger the first dropped run on the mini or any change to how the session is started (pty, `-tt`). See D-S3 on the `trap '' HUP` rationale |
| EW S7 | fixed | fake: `env -i PATH=/usr/bin:/bin`, zsh, scp makes no dirs |
| EW N2 | fixed | `test_a_worktree_removed_by_hand_is_added_again` kills a return to `-b`. Removing `--detach` alone is an equivalent mutation (a `refs/remotes` ref checks out detached anyway): survived, not a defect |
| EW N4 | fixed | 12-40 prefix; `{12}` mutation killed |
| EW N6 | fixed | mistyped base refused; mutation killed |
| EW N7 | rejected | agreed with the author: output is captured whole, nothing would stream |

**Deviation 1 (venv stamped last, not built and renamed): sound.** Console-script shebangs and `pyvenv.cfg` hold the
absolute path, so a rename breaks the venv; `rm -rf` then build then stamp gives the same all-or-nothing property, and
the pid file stops a second run from deleting a venv in use. **Deviation 2 (drop path untested): acceptable as a
deferral**, but its stated mechanism is doubtful (D-S3).

## New findings

**D-S1 SHOULD-FIX, `scripts/remote_gate.py::ssh` (mask): the real host name leaks through ssh's own stderr when
`--remote` is an alias.** The mask replaces only `cfg.remote`. With `--remote mini` and a `HostName` in
`~/.ssh/config`, ssh's own messages name the resolved host, not the alias (`ssh: connect to host <HostName> port 22:
...`, `Warning: Permanently added '<HostName>' ...`). Before the fold stderr was discarded, so this is new: a timeout
on the tailnet prints the private host into the terminal and the session transcript, from which it can be pasted into
a review or PR. The docstring promises "nothing private is printed". The test uses the host itself as `--remote`, so it
can't see this. Fix (unverified): also mask `hostname` (and `user`) from `ssh -G <remote>`, and add a fake whose
alias differs from the host it prints.

**D-S2 SHOULD-FIX, `tests/test_remote_gate.py::test_a_failing_gate_exits_nonzero_and_masks_…`: the user mask is
unguarded.** Deleting the `PRIVATE user` printf from `PRELUDE` stays green (35 passed). The user name appears only
inside the home and tmp paths, which are masked first, so `getpass.getuser() not in err` can't fail. fold1.md names
this test as AT N2's killer: the fold table overstates. Needs a stub that prints the user outside those paths (for
example `id -un`).

**D-S3 SHOULD-FIX (claim, not code), `GATE_SCRIPT` `trap '' HUP` and fold1/commit message.** The command runs with no
pty (`ssh host 'bash -s'`), and sshd sends no SIGHUP to a non-pty session when the connection drops; the shell lives
on because nothing it runs writes to the dead channel (prepush's output goes to `tail`, which dies of SIGPIPE only at
the end). The trap is probably inert, and "keeps a dropped session's gate under its shell" is unverified. The
mutation removing it survives. Either drop the claim (and the trap) or prove it on the mini; record which. Related,
pre-existing but worth folding with it: `bash -s` reads its script from stdin one byte at a time (checked here:
`printf 'cat\necho hi\n' | bash -s` prints `echo hi`), so any child of the gate that reads stdin swallows the rest of
the script. Run the gate's commands with `</dev/null`.

**D-N1 NIT, `GATE_SCRIPT` (venv): two stamp parts are unguarded.** Replacing `rm -rf .venv` with a no-op survives
(the fake venv has no packages to go stale), and so does dropping `${python}` from the stamp (no test switches
interpreter at one version).

**D-N2 NIT, `GATE_SCRIPT` (worktree): a worktree deleted with `rm -rf` is still not re-added.** Checked here: `git
worktree add` then fails with "is a missing but already registered worktree". The test removes it with `git worktree
remove`, which deregisters it. A `git worktree prune` in the session's own clone before `add` would fix it
(unverified in the script).

**D-N3 NIT, `clone_path` / `PREPARE_SCRIPT`: a clone nested in the shared clone passes.** `--gate-root
overdrive-gate/repo --clone x-repo` is accepted; `pwd -P` equality doesn't match, and the session clones into the
shared clone's working tree, leaving an untracked directory there that every session's gate then sees.

**D-N4 NIT, `copy`: scp's stderr is dropped**, so "could not copy (twice)" has no cause, unlike every ssh refusal
the fold now explains. If it is shown, it needs the D-S1 mask.

**D-N5 NIT, `Remote.shown`: over-masking.** A short alias or user name (`mini`, `dev`, `test`) is replaced wherever
it appears, so failure lines can read `<user>s/<user>_x.py`. Readability only.

**D-N6 NIT, `GATE_SCRIPT` pid file: check-then-write isn't atomic**, so two runs of one branch from one session
started together can both pass the check. Same-session only.
