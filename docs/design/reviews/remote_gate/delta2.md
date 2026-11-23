# remote_gate, delta round 2 on 5317781 (2026-11-22)

Reviewer: one reader, all lenses (Executor, Architecture, Wire integrity, Trust boundary). Scope: `git show 5317781`
(40f0b27 is origin/main only). Statuses are the reviewer's, read from the tree. No BLOCKER.

Ran on a scratch copy of 5317781 (`rg-delta2`): `tests/test_remote_gate.py`, 41 passed. Seventeen mutations of
`scripts/remote_gate.py`, the file's tests each: 13 killed, 4 survived (M1, M3, M6, M18 below). Two probe tests in a
second copy (`rg-delta2-probe`): the nested-clone pollution and the unmasked IP, both confirmed.

## Statuses

| Finding | Status | Note |
|---|---|---|
| D-S1 resolved host leaks | fixed (hostname); residue in E-S1, E-N1, E-N2 | dropping the hostname mask, and reverting `ssh()` to the alias-only mask, are both killed by the `[gate-box]` case |
| D-S2 user mask unguarded | fixed | dropping the `PRIVATE user` printf is killed (`ran as <user>, alone`) |
| D-S3 `trap '' HUP` | fixed | trap and claim removed; docstring states the drop isn't survived. Deferral accepted: reason (no survival mechanism yet), trigger (a mini run lost to a drop) |
| D-S3 (related) `bash -s` stdin | fixed | removing the wrapper (keeping the redirect) is killed by `test_a_child_that_reads_stdin…`. **Author's equivalence claim: agreed.** bash parses `main() {…}` whole, then reads the last line to its newline before running it; the script ends there, Python closes ssh's stdin, so a child reading stdin gets EOF. `</dev/null` is defence in depth; M1 survives as an equivalent mutation, not a defect |
| D-N1 stamp parts | fixed | `rm -rf .venv` and `${python}` mutations both killed |
| D-N2 worktree deleted by hand | fixed | dropping `git worktree prune` killed |
| D-N3 nested clone | open (remote half) | local `clone_path` check killed (M9) and the remote `case` killed (M10), but the remote refuses only *after* cloning into the shared working tree: E-S2 |
| D-N4 scp stderr | fixed; one part unguarded (E-N2) | unmasked scp stderr is killed |
| D-N5 over-masking | rejected (reviewer agrees) | readability only; note the hostname and `-G` user masks widen it (a MagicDNS short name like `mini` masks inside `mini-gate`) |
| D-N6 pid file not atomic | open | E-N3: the race is not closed, and the "can't be tested deterministically" claim is wrong |

## New findings

**E-S1 SHOULD-FIX, `scripts/remote_gate.py::ssh_masks`: the resolved IP address is never masked.** ssh's most common
failure lines name the peer's address, not its name: `Connection closed by <ip> port 22`, `Connection reset by <ip>
port 22`, `kex_exchange_identification: …` followed by the address line, and with `CheckHostIP` the known-hosts warning
adds `'<host>,<ip>'`. `ssh -G` reports only `hostname`, so for a Tailscale node the 100.x address (or the
`fd7a:115c:a1e0::/48` IPv6 one) reaches the terminal and transcript. Probe: a fake ssh printing `Connection closed by
100.101.102.103 port 22` after resolving the alias; the refusal printed the address verbatim. Severity: a tailnet
address is less identifying than the name, but the docstring promises "nothing private is printed", and the address is
reachable from inside the tailnet. An IPv6 `HostName` is masked only if ssh prints it in the same spelling as the
config (ssh prints the resolved, compressed form, so `fd7a:0:…:1` in the config won't match `fd7a::1`). Fix
(unverified): mask every IPv4 and IPv6 literal in ssh and scp stderr by pattern, rather than chasing resolved
addresses. Regex metacharacters are not an issue: `masked` uses `str.replace`.

**E-S2 SHOULD-FIX, `PREPARE_SCRIPT` (the remote `case`): a nested clone is refused only after it has been cloned into
the shared working tree.** The script runs `git clone` first and checks `pwd -P` second. With `gate -> overdrive-gate/repo/nested`,
the probe left `overdrive-gate/repo/nested/session-repo` (a full clone) in place after the refusal. This is exactly
the failure D-N3 described ("an untracked directory there that every session's gate then sees"): the refusal message is
new, the pollution isn't fixed. `test_a_clone_that_resolves_inside_the_shared_one…` asserts the exit code and the
message, never that the shared tree is unchanged, so it can't see this. Fix (unverified): `mkdir -p` the parent,
resolve the parent with `pwd -P`, refuse before `git clone`; assert `not (shared/"nested"/"session-repo").exists()`.

**E-S3 SHOULD-FIX, `tests/test_remote_gate.py` (D-S1's tests): the `ssh -G` user mask is unguarded (M6 survives).**
Replacing `found.get("user", "")` with `""` passes all 41. The likeliest failure under `BatchMode=yes` is
`<user>@<host>: Permission denied (publickey).`, printed before the `PRIVATE` lines exist, so only the `-G` user mask
hides it (the probe shows it does, today). No test prints the user in ssh's own stderr. The commit message's list of
killed mutations doesn't claim this one, so no overstatement, but D-S1's fold names "host and user". Fix: make the
refused-connection fake print `remote-user@{HOST}: Permission denied` and assert `<user>@<remote>`.

**E-N1 NIT, `ssh_masks`: a ProxyJump or ProxyCommand host is not masked.** `ssh -G` prints `proxyjump`, but only
`hostname` and `user` are read; messages like `ssh: Could not resolve hostname <jump>` or `channel 0: open failed`
name the jump host (and its own `HostName` would need a second `-G`). Only matters if the owner's config uses one; not
checked here (reading `~/.ssh/config` would put the private name in this transcript). Also, "connects to nothing" is
true of `-G` but a `Match exec` block in the config still runs its command; the docstring could say so.

**E-N2 NIT, `tests/test_remote_gate.py::test_a_dropped_copy_is_retried_once_and_two_drops_refuse`: scp's resolved-host
mask is unguarded (M18 survives).** Masking scp's stderr with only `(cfg.remote, "<remote>")` passes, because the test
runs with `--remote` equal to `HOST`. Parametrize it over `HOST` and `ALIAS` as the ssh test is.

**E-N3 NIT, `GATE_SCRIPT` pid file (D-N6): the race is not closed, and the guard is testable.** The `rm -f` runs
unconditionally after the liveness check, so with A and B starting together, B's `rm` can delete the pid file A has
just written, and both run; noclobber refuses B only when A writes in the microseconds between B's `rm` and B's write.
fold2.md's "the loser of a simultaneous start is refused" overstates; the window is barely narrower than before. The
"no deterministic test" claim is also wrong: a test fake ssh that puts a shim `rm` first on `PATH` (writing a live
pid after removing the file) makes the refusal deterministic, and M3 (dropping noclobber) would then be killed. Real
fix (unverified): take the lock with an atomic create that is never preceded by a blind remove (`mkdir` lock dir, or
`noclobber` write first and replace a stale file only by `mv` of a fresh temp after re-checking). Same-session only,
so a NIT; deferring it with that trigger is acceptable if recorded honestly.

**Checked, no finding:** longest-first ordering holds when the hostname contains the user or the alias (M7 killed);
labels can be re-masked only into `<<remote>>`-style noise, never a leak; masking happens after `HEAD`/`PASS` matching,
so a mask that is a hex substring can't break `verdict`; the `case` pattern quotes the shared path, so glob characters in it are literal, and a failing `cd` there fails closed;
`set -e`, `exit` and the `EXIT` trap behave the same inside `main` as at top level.
