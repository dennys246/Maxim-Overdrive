# remote_gate delta 3, fold (2026-11-23)

The author's claims; statuses are the reviewer's to set (O25). Findings are in `delta3.md`.

| Finding | Change | Author's claim |
|---|---|---|
| F1 (SHOULD-FIX): an address followed by `.` or `:` leaks | `IPV4`'s lookahead lets a `.` follow unless a digit comes after it; `_address` strips a bare, zoneless IPv6 match's trailing `.` and `:` before validating and puts them back after `<address>` | `test_an_address_ending_a_sentence_or_a_field_is_still_masked`: red before the change. Three mutations each turn it red: the old lookahead, no strip, and a lookahead that also masks dotted versions |
| Open item: a lock with no pid | none | deferred by the reviewer, with the trigger "the first `pid starting` refusal for a gate that isn't running"; the `ln -sn` root fix is noted there |
| F2 to F5 (NITs) | none | left for the trigger above or the next change to the masks; F4's over-masking never touches a sha or the PASS line (the reviewer's check) |

The test address `100.64.1.2` in `delta3.md` and in the tests is a stand-in, checked against the mini's real address
without printing either.
