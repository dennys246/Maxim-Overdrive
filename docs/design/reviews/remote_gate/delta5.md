# remote_gate delta 5 (Executor, Trust boundary), on b995f37 (2026-11-23)

The reader's hand-back, condensed and saved by the author. The reader tested the module at b995f37 from a scratch
copy, with made-up addresses only, and reran the author's mutations itself.

**S1 (`delta4.md`): fixed** (the reviewer's status). The probe grid was 8 addresses × 4 endings × 5 message shapes,
with no leak:
- the addresses: IPv4; compressed IPv6; three ending in `::`; IPv4-mapped; `::1`; zoned;
- the endings: none, `.`, `:` and `::`;
- the shapes: the four ssh messages plus a bare one at the end of a line.

What is dropped stays after the mask (`fd7a::1::` → `<address>::`). The extended test fails on the parent b714a24.
Each of fold5.md's three mutations turns it red. 48 tests pass.

**F1 (`delta3.md`): still fixed.** Every row is masked, and so are the bracketed forms (`[2001:db8::]:22`,
`[fe80::1%en0]:22`).

**Left unmasked, as required:** dotted versions, a 40-character sha, `test_x.py::test_y` (with and without a trailing
`::`), times, and the PASS line. A literal made only of separators can't mask (nothing parses, or nothing has a hex
digit).

**New findings:** none at any severity. N1 and N2 from `delta4.md` stand. Words made only of hex letters around `::`
(`dead::beef`, `cafe::`) are masked, as fold5.md says. They are valid literals, so this errs toward hiding.

**Round status:** every finding from round 1 through delta 4 is fixed, rejected or deferred with a trigger. The one
deferral is the lock left with no pid, with the trigger "the first `pid starting` refusal for a gate that isn't
running" (`delta3.md`).
