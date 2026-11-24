# remote_gate, delta round 3 on 6c4a87c (2026-11-22)

Reviewer: one reader, all lenses (Executor, Architecture, Wire integrity, Trust boundary). Scope: `git show 6c4a87c`;
a5f62f9 checked briefly. Statuses are the reviewer's, read from the tree. No BLOCKER.

Ran on a scratch copy of 6c4a87c (`rg-delta3`): `tests/test_remote_gate.py`, 47 passed. 21 mutations of
`scripts/remote_gate.py`, each run against the file's relevant tests: 19 killed, 2 survived (M4 and M19 below; neither
is one the commit claims). Every mutation the commit message claims was reproduced and killed. Mask probes called
`masked()` directly (it is the shipped path for ssh and scp stderr and the shown tail).

**Merge a5f62f9:** against main, only the branch's files and its `ALLOWED_SPAWNS` row; both rows kept. No finding.

## Statuses

| Finding | Status | Note |
|---|---|---|
| E-S1 resolved IP never masked | fixed; residue in F1 | dropping IPv4 (M1), the bracket form (M2), the hex rule (M3) and the bare zone (M5) are all killed. Port glued on (`a.b.c.d:22`), brackets (`[a.b.c.d]:22`, `[fe80::1%en0]:22`), IPv4-mapped (`::ffff:a.b.c.d`, bare and bracketed), `'alias,addr'` and `/48` are all masked. A literal followed by `.` or `:` is not (F1) |
| E-S2 nested clone refused after cloning | fixed | the clone-before-check mutation is killed (M6) by the new `nested/` emptiness assert. Probed: a dangling symlink at the gate root or at the clone passes the check but `mkdir -p`/`git clone` then fail, so the result is a refusal and nothing lands in the shared tree |
| E-S3 `ssh -G` user mask unguarded | fixed | `found.get("user")` replaced with `""` is killed (M20) |
| E-N1 ProxyJump / `Match exec` | fixed; residue in F3 | dropping the proxyjump read (M17), the jump user (M15) or the port strip (M16) is killed. The docstring now names `Match exec` |
| E-N2 scp resolved-host mask | fixed | scp masked by the alias only is killed on the `[gate-box]` case (M21) |
| E-N3 / D-N6 the lock race | fixed | the mkdir lock closes the race. The empty-pid rule (M7), the mutex (M8), the recheck (M9), the guarded second mkdir (M10), each `.recover` release (M11, M12, M13), `owner()`'s `\|\| true` (M18) and the trap (M14) are all killed. Traced the interleavings by hand: a fresh gate can take the lock only while it is absent, which happens only inside a recovery, and then the recoverer's second `mkdir` loses and it refuses. Neither shim test can pass if the winner's lock is removed |
| D-N3 remote half (open in delta 2) | fixed | by E-S2 |
| fold2.md correction | fixed | the two wrong claims are corrected in fold2.md, in the author's voice |

## The author's open item (a lock left with no pid)

**Status: deferred (reviewer's).** Reason: the lock fails closed and loudly. The refusal (`pid starting`) names the
directory to remove, and nothing removes a lock with no pid on its own. Trigger: the first `pid starting` refusal for a
gate that isn't running, or the next change to `GATE_SCRIPT`'s lock.

Two corrections to fold3.md's account:

- **"One shell builtin wide" is an understatement.** On the fast path the window runs from the `/bin/mkdir`
  process's syscall to the builtin `echo`'s write: one external process exits and bash reaps it. On the recovery path
  it also takes in `rmdir .recover`, a full fork and exec. The window is still milliseconds, and nothing on the remote
  writes during it, so a dropped ssh can't SIGPIPE it. Only a failed `echo` under `set -e`, or a kill, strands it.
- **There is a cheap root fix the account doesn't mention.** Take the lock with `ln -sn "$$" "${gatelock}"`. The link
  is created with the pid already inside it, atomically, and the owner is read back with `readlink`. That makes the
  empty-pid state impossible and drops the `starting` branch. Verified here on macOS: `ln -sn` fails with `File exists`
  on an existing link, dangling or not. Caveat (verified): `ln -s` onto an existing directory links inside it, so a leftover lock directory from this
  commit needs one `rm -rf`. Alternatively, move
  the final `rmdir .recover` after the pid write, which shrinks the recovery path's window back to the fast path's
  (unverified). Either fix is the author's call. The deferral is acceptable as it stands.

## New findings

**F1 SHOULD-FIX, `scripts/remote_gate.py::IPV4`/`IPV6`/`_address`: a literal followed by `.` or `:` is not masked.**

| Input | Output |
|---|---|
| `closed by 100.64.1.2.` | `closed by 100.64.1.2.` |
| `added fd7a::1.` | unchanged |
| `fd7a::1:` | unchanged |
| `::ffff:100.64.1.2.` | unchanged |
| `fd7a:115c:a1e0::1234...` | unchanged |

IPv4: the lookahead `(?![\w.])` rejects a sentence-ending period, and no other start position qualifies. IPv6: the bare
class includes `.` and `:`, so the greedy match takes the trailing punctuation, `IPv6Address` rejects it, and
`_address` returns the text unchanged. `re.sub` does not retry a shorter match once the callback declines.

Failure scenario: any ssh or remote line that ends a sentence with the peer's address (`… by <ip>.`, or a
`debug1:`-style line under a raised `LogLevel`) prints the tailnet address. This breaks the docstring's "every IPv4 and
IPv6 address literal" promise, the same class as E-S1.

Fix (unverified): in `_address`, strip trailing `.`/`:` from the candidate before parsing, and put the stripped
characters back; allow a single trailing `.` in IPv4's lookahead (`(?!\w|\.\w)`). Add the five rows above to
`test_the_address_masks_…`.

**F2 NIT, `tests/test_remote_gate.py::test_the_address_masks_leave_test_ids_times_and_versions_alone`: the IPv6
lookbehind's `.` and `:` are unguarded.** M4 (`(?<![\w.:])` changed to `(?<![\w])`) passes. The pinned cases fail to
parse either way. A case like `x:::1` or `a.::1` would pin it.

**F3 NIT, `scripts/remote_gate.py::_jumps`: two residues.**

- A bracketed IPv6 hop with a port (`[fd7a::1]:22`) keeps its port. `.strip("[]")` then yields `fd7a::1]:22`, a mask
  that never matches. The address pattern hides it anyway.
- A hop given as an alias is masked as the alias. Its own `HostName` isn't resolved, and the address pattern doesn't
  cover a name. The docstring's "ProxyJump hosts ssh resolves it to" overstates for that case. This matters only if
  a config with a jump.

**F4 NIT, `scripts/remote_gate.py::masked`: the address masks are over-broad on remote output.** A four-part version
(`numpy 2.1.3.4`, `pyobjc-core-10.3.1.1`) becomes `<address>`. So do hex-only words around `::` (`beef::cafe`, `a::b`,
`add::`), and an 8-group colon run. A zone after a colon-ended match is half-masked (`fe80::1%en0:` →
`<address>%en0:`; an interface name, not private).

None of these can mangle a commit sha or the PASS line:

- a sha has neither dots nor colons;
- `verdict` matches `HEAD`/`PASS` on raw lines;
- the returned PASS line is printed raw.

That last point is pre-existing: the PASS line is the one remote line no mask touches (sha, base, skipped list; none
private). Readability only, like D-N5.

**F5 NIT, `GATE_SCRIPT`:** the message reads "a gate for X is started just now" (the test pins it). fold3.md is dated
2026-11-23; the commit, 2026-11-22.

**M19 (survived, not a defect):** setting the EXIT trap before the pid write passes, and it would clean up the open
item's `set -e` case. It is a candidate fix.

**Not checked:** whether `100.64.1.2` in the tests is anyone's real address. I didn't read the ssh config, so as not to
bring private names into this transcript; the author should confirm. `fd7a:115c:a1e0::/48` is Tailscale's public prefix.
