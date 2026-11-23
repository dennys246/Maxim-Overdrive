# remote_gate delta 4 (Executor, Trust boundary), on b714a24 (2026-11-23)

The reader's hand-back, condensed and saved by the author. Made-up addresses only; the reader ran probes against
copies of the module before and after the fold, and didn't rerun the author's mutations.

**F1: fixed** (the reviewer's status). Each shape F1 named is now masked:
- IPv4 before `.` and `:`;
- compressed IPv6 before `:`;
- IPv4-mapped IPv6, in all four ssh message shapes, where before the `::ffff:` prefix stayed visible;
- `fe80::1%en0.`.

Dotted versions, shas, `test_x.py::test_y`, times and the PASS line stay unmasked.

**S1 (SHOULD-FIX, a regression in b714a24), `_address`:** `rstrip(".:")` also strips a `::` that belongs to the
address, so `2001:db8::` becomes `2001:db8`, fails to parse, and is returned unmasked. A host at an address ending in
`::` leaks in all four shapes (`Connection to 2001:db8:: closed.`, `ssh: connect to host 1:: port 22`); the parent
commit masked both. `fd7a::: x` leaked before the fold and still does. *Fix (checked standalone, not in the module):*
strip one trailing separator at a time, longest literal first, and keep the first form that parses.

**N1 (NIT, older than the fold):** a zone's `%[\w.-]+` swallows a sentence's `.`, so `fe80::1%en0. closed` loses its
period; before a `:` the zone stays visible (`<address>%en0:`). No address shows either way.

**N2 (NIT):** the IPv4 mask now reaches `10.0.0.9.a` (`<address>.a`) and `10.0.0.9..`; never a version, sha or the
PASS line.
