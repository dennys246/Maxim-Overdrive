# remote_gate, fold 3: delta round 2 on 5317781 (2026-11-23)

This file records the author's claims, not statuses; a reviewer sets those from the tree. The findings are in
`delta2.md`.

| Finding | Change (author's claim) |
|---|---|
| E-S1 the resolved IP is never masked | `masked` replaces every IPv4 and IPv6 literal with `<address>` after the named masks. IPv6 is matched bracketed (`[fe80::1%en0]:22`) or bare and standing alone. A bare match must parse as an IPv6 address and hold a hex digit, so `::`, `test_x.py::add_case` and `12:34:56` stay as written. A resolved address from `ssh -G` is covered by both the value mask and the pattern. Test: the refused connection prints `Connection closed by 100.64.1.2 port 22`, a compressed IPv6 address with a zone and a bracketed full one. The output shows `<address>`, and none of the values appears. A unit test pins what must not be masked. |
| E-S2 a nested clone is refused only after cloning | `PREPARE_SCRIPT` resolves the deepest existing part of the clone's path (`pwd -P`, then the missing components appended) and refuses before any `mkdir` or `git clone`. The local half (`clone_path`) is unchanged. Test: after the refusal, the shared tree's `nested/` directory is empty. |
| E-S3 the `ssh -G` user mask is unguarded | The refused connection also prints `remote-user@<host>: Permission denied (publickey).`, and the test asserts `<user>@<remote>: Permission denied` with no `remote-user` anywhere. |
| E-N3 / D-N6 the pid-file race | Replaced by a `mkdir` lock directory holding the owner's pid. A lock whose pid is empty (just made) or alive is refused. A dead owner's lock is recovered under a second `mkdir` (`.lock.recover`), so only one gate recovers it. The recoverer checks that the pid is still the dead one, removes the lock, and takes it with `mkdir`. If that `mkdir` loses, it releases `.recover` and refuses. It never removes a lock whose pid changed. Tests: live, starting and dead locks; a recovery in progress; and the race at both steps, made deterministic by planting `mkdir` or `rm` first on the fake remote's `PATH` (a live gate takes the lock at that moment). The winner's lock stays intact, and `.recover` is released. fold2.md's two wrong claims are corrected there. |
| E-N1 ProxyJump hosts are not masked | `ssh_masks` reads `proxyjump` and masks each hop's host (`<jump>`) and user (`<user>`); `none` is no jump. Test: two hops, one with a user and a port. |
| E-N1 `Match exec` | Documented in the docstring: `ssh -G` opens no connection, but a `Match exec` block still runs its command. |
| E-N2 scp's resolved-host mask is unguarded | The dropped-copy test runs with the host and with the alias. With the alias, only the resolved-host mask hides scp's message. |

## What the lock still can't do

A gate that dies between making the lock and writing its pid leaves a lock with no pid. Every later gate refuses it
("pid starting") and names the directory to remove; it is never removed by itself. A recoverer that dies holding
`.recover` leaves the same kind of named refusal. Both are loud, need a hand to clear, and are left as they are: the
window is one shell builtin wide.
