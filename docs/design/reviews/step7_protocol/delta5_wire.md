# Wire integrity, delta round 5: phase1/protocol (fold 0eba5e8..70d8834, merged at 5e43010)

**How I checked.** `git archive 5e43010` into `<scratchpad>/delta5/wire/head`; Python ran on that copy
(`simcore.__file__` and `wire_texts.__file__` resolve there). The worktree was clean. The merge 5e43010 adds only the
id-check files from #55 (`scripts/lint_ids.py`, its tests, `CLAUDE.md`, review notes); it changes none of this
branch's wire code.

I reran the 1,975 probes of rounds 2 to 4 and added 11,412 (`<scratchpad>/delta5/wire/extra5.py`): every lead byte
0x80 to 0xFF, alone, before ASCII, truncated at the buffer's end, and followed by one, two and three continuation
bytes from {80, 8F, 90, 9F, A0, BF} x {80, BF} x {80, BF}, as a string value and as a key; plus 19 forms of the
halfway tie 2^1024 − 2^970 (`.0`, `.00`, `e0`, `E+0`, `1.<digits>e308`, `0.<digits>e309`, negated, trailing-zero
trimmed, just above, and just below by one unit). Python judged with `strict_json.decode` and `value_tree`; Godot
4.7.2 with `WireJson.parse` and `FrameDecoder.decode`, through `godot_check.run_godot` with HOME in scratch.

**Result.** 13,384 of 13,387 agree. The 3 that part are NT-1's, as before. All 11,394 UTF-8 probes agree (552
accepted, 10,842 `bad_json`), so the if/elif rewrite of `_utf8_sequence` reads every lead byte as the ternary did;
by reading, GDScript's ternary is right-associative, so the two are the same function. Every halfway form agrees:
the tie and above are refused, the values below are finite. The probe run printed no `ERROR:`, only NT-2's 20
`WARNING: Exponent too high`.

**The gate's Godot step.** `godot_check.check` (import, load, client tests and the error scan) on the committed
`client/` returns no findings. **Python:** `tests/test_wire*.py` and `tests/test_host.py` on the archive give 356
passed, 1 skipped.

## Fold table (delta-4 findings)

| # | Status | What I checked |
|---|---|---|
| W4-S1 | **fixed** | Both halfway fixtures are now floats (`<H>.0` and `1.<H>e308`), refused on both sides, and `test_the_committed_fixtures_are_what_the_script_makes` holds them to `wire_texts.py`. Mutant `_past_largest` `>=` → `>` in a scratch copy: `godot_check.check` gives `client-tests: FAIL 2 failure(s) in 90 tests`, and 11 of my halfway probes part under it. I watched it go red. |
| W4-N1 | **fixed** | `_INT_DIGITS`'s comment now says 18 would do too. |
| NT-1 | **deferred, accepted** | A row in `docs/plans/checklists.md` step 7 ("Open NITs from the review rounds") names it, with the reason (past every shipped cap) and a trigger (this step's `intent_result`). The trigger is a batch trigger, not one tied to float parsing, but the case is unreachable under the caps, so I accept it. |
| NT-2 | **deferred, accepted** | Same row; the warning is still printed and the error scan still ignores warnings. |

Counts: 2 fixed, 2 deferred (accepted), 0 rejected, 0 open.

## New findings in the fold

### SHOULD-FIX

**W5-S1. `client/addons/engine/net/wire_json.gd::_utf8_sequence`: the fold rewrote the lead-byte table, and no shipped
fixture pins three of its four branches.** The only raw UTF-8 a shipped JSON fixture accepts is two-byte `C3 A9`
(`raw_utf8.json`); the refused ones are overlong, surrogate, past U+10FFFF and truncated. Nothing accepts a raw
three-byte character other than the BOM, nothing accepts any raw four-byte character, and nothing feeds a lead byte
no sequence uses (80 to BF, F5 to FF).

Failure scenario, measured: three mutants of the rewritten lines, each run through `godot_check.check`, return **no
findings** (`PASS 90`):
- m3, `0xF0` → `0xF1`: every raw U+10000 to U+3FFFF (all emoji) refused by the client, accepted by Python (32
  probes part);
- m4, `0xDF` → `0xDE`: U+07C0 to U+07FF refused (6 part);
- m5, the default `length = 0` → `2`: a stray continuation byte or an F5 to FF lead reads as a two-byte character,
  so `{"a":"\xbf\xbf"}` and `{"a":"\xf5\x80\x80\x80"}` are accepted by the client and refused by Python (2,850 part).

m5 is the one that matters: the comment the fold added ("a lead byte no sequence uses ... stays 0") states the guard
that keeps the client's reader from accepting bytes the server's reader refuses (O63), and no test fails when it goes.
(The range edges `C2` and `F4` are masked by the overlong and past-U+10FFFF checks below, so those mutants are
equivalent and need no fixture.)

Verified fix: 8 JSON fixtures, `{"a":"\x80"}`, `{"a":"\xbf\xbf"}`, `{"a":"\xf5\x80\x80\x80"}`, `{"a":"\xff"}`
(refused) and `{"a":"\xdf\xbf"}`, `{"a":"\xe2\x82\xac"}`, `{"a":"\xf0\x9f\x98\x80"}`, `{"a":"\xf4\x8f\xbf\xbf"}`
(accepted), added to a scratch copy's `json/` and manifest with Python's outcome and value tree
(`<scratchpad>/delta5/wire/addfx.py`). The committed client with them: no findings. m3 and m4: `FAIL 2`; m5:
`FAIL 1`. In the tree they belong in `scripts/wire_texts.py::_string_edges`, since the fixture test regenerates from
there.

### NIT

None.

## Checked, no finding

- **The tie rule's `>=`** has exactly one shipped guard pair now, and both forms (`.0` and the exponent) reach it.
- **`_integer`'s new comment** matches Godot 4.7.2: my integer probes at 2^63 print no ERROR, and above it the digit
  guard refuses before `to_int`, so none prints.
- **`test_net_session.gd` and `net_client.gd`** changes are line wraps only; the moved `integer_*` fixtures keep
  their outcomes in the manifest.
- **A probe-harness note:** on this Mac's case-insensitive file system my `h_e0` and `h_E0` probe files collided; I
  renamed one and reran, and both agree. The shipped fixture names have no case-only pair.
