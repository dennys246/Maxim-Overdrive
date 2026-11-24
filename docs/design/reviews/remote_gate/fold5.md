# remote_gate delta 4, fold (2026-11-23)

The author's claims; statuses are the reviewer's to set (O25). Findings are in `delta4.md`.

| Finding | Change | Author's claim |
|---|---|---|
| S1 (SHOULD-FIX): b714a24 stopped masking an address ending in `::` | `_address` drops one trailing `.` or `:` at a time, longest first, and masks the first form that parses (`_is_ipv6`); what it dropped stays after `<address>` | the test now covers `2001:db8:: closed.`, `fd7a::: x` and `1:: port 22`, and was red before the change. Three mutations each turn it red: trying only the fully stripped form, never stripping, and accepting any form. 48 tests pass. `beef::` is masked again, as it was before b714a24 (a valid literal; fails safe) |
| N1, N2 (NITs) | none | neither shows an address; left for the next change to the masks |
