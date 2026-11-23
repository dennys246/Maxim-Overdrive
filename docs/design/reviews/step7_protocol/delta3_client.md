# Client and rendering lens: delta round 3 (fold e97727d..a532695, merged at 87ff10e)

Method: I reviewed the committed tree, using `git archive 87ff10e` into `<scratchpad>/delta3/client/tree`. The merge
87ff10e touches no client, protocol or host file. Every Godot run went through `godot_check.run_godot` with HOME
under `<scratchpad>/delta3/client/`. The unit baseline is `client-tests: PASS 90 tests`. Each mutation ran on a fresh
copy (`<scratchpad>/delta3/client/mutate.py`, `sock.sh`). Probes are in `probe/` and `probe2/`.

## Fold table (delta-2 findings)

| # | Status | What I checked |
|---|---|---|
| S4(b) the 65th queued packet | **deferred, accepted** | It is listed in checklists.md step 7 with a trigger (step 8's live client). |
| N3 the two `index()` orders | **deferred, accepted** | It is listed with a trigger (step 8's decoder filling `CellSnapshot`). |
| N-N1 the parser's cost | **deferred, accepted** | B5 now records 0.7 ms per 1 KB header and 0.5 s for a hostile BOM text, and step 8's budget gate owns both. |
| N-N2 the client closes with 1000, not 1008 | **open** | The code is unchanged (`peer.close(1000, ...)`), and client_rendering §4.3 still names only the host's 1008. The fold neither records the choice nor changes it. |
| N-N3 the engine-fact test depends on timing | **open, now SHOULD-FIX (measured)** | It is unchanged and not deferred. On the unmutated tree, `test_godot_drops_the_error_that_arrives_with_the_close` failed 2 of 16 runs with `raw packets 1 reason bad_token`. So Godot 4.7.2 *does* sometimes hold the error text, and §4.3's "drops a text packet arriving with the close [ran]" is wrong as a fact. NetClient handles both orders, so the client is fine. But the gate goes red about 1 run in 8, and a gate that flakes gets rerun until it passes. A fix: assert that the reason is `bad_token` and that packets is 0 or 1, and correct §4.3 to say "may drop". |
| D2-SF1 non-string `type` | **fixed** | `kind is String and kind == "welcome"`, with a test for `5`, `true`, `[1]` and `{}`. When I reverted the check, the suite went red (4 failures, `SCRIPT ERROR: Invalid operands 'int' and 'String'`). |
| D2-SF2 the coded-reason rule had no test | **fixed** | `test_a_close_reason_that_is_no_code_is_not_taken_as_one`. When I reverted the rule to `not reason.is_empty()`, that test went red and the other 6 passed. |
| D2-N1 the cost of the BOM path | **deferred, accepted** | It is recorded in B5 (above). The code is unchanged. |
| D2-N2 `MAX_TEXT_BYTES` had no check | **fixed** | The manifest now carries `max_text_bytes`, and the client is held to it. When I set the cap to 256 KiB, the suite went red (`max_text_bytes: got 262144, want 65536`). |
| D2-N3 the socket wait spun | **fixed** | The helper now uses an `asyncio.Event` set in a `finally`. I read the code; I didn't mutate it (it is test plumbing). |

**Counts: fixed 4, deferred and accepted 4, open 2 (N-N2, N-N3), rejected 0.**

## New findings (the fold's diff)

### D3-SF1 (SHOULD-FIX). Removing the digit guard lets the client accept integers that the server refuses
`client/addons/engine/net/wire_json.gd::_integer`. The new comment says that `String.to_int` "clamps a longer literal
to the int64 range rather than wrapping it". On 4.7.2 that is false at both ends (measured in `probe/`):

| literal | `to_int` | `absi` | client | Python |
|---|---|---|---|---|
| `[9223372036854775808]` (2⁶³) | wraps to INT64_MIN, **with no engine error** | INT64_MIN (it overflows) | **accepted** as -2⁶³ | refused |
| `[-18446744073709551617]` | clamps to INT64_MIN | INT64_MIN | **accepted** | refused |
| `[-99999999999999999999999999]` | INT64_MIN | INT64_MIN | **accepted** | refused |
| `[18446744073709551617]` (the new fixture) | INT64_MAX | INT64_MAX | refused | refused |

`absi(INT64_MIN)` returns INT64_MIN, which is below `INT_MAX`, so the magnitude check passes it.

How it fails: a server message with `"tick": 9223372036854775808` reads as -2⁶³. The client reports `out_of_range`
where the grammar says `bad_json`, and a field with no range check would carry -2⁶³ into the game. The two readers
are supposed to judge the grammar's edges alike (boundaries §9.1), and here they don't. The fixture the fold added
covers only the positive clamp, which is the one case where the comment holds. Each over-range literal also prints
two `ERROR: Cannot represent ...` lines, so a hostile text can spam the log.

Proposed fix (**verified**): restore the digit guard, `text.length() - (1 if text.begins_with("-") else 0) > 16 or
absi(...)`. In `probe2/`, all three literals above then give `bad_json` with no engine error, and ±(2⁵³ − 1) is still
accepted. Add `[9223372036854775808]` and `[-18446744073709551617]` to both corpora. Then the guard can be told apart
by a test, which answers X-N1's reason for removing it.

### D3-SF2 (SHOULD-FIX). The fixture named for the exact halfway isn't the exact halfway
`scripts/wire_texts.py`, `exact_halfway_past_the_largest_double` = `1.79769313486231581e308`. The exact halfway is
2¹⁰²⁴ − 2⁹⁷⁰ = 1.797693134862315807937…e308 (309 digits), and this literal lies above it. When I changed
`_past_largest`'s `>=` to `>`, the suite stayed `PASS 90 tests`. So the round-half-to-even boundary that `_PAST_DOUBLE`'s
comment describes is unguarded, and the fixture's name claims a bar it doesn't hold.

How it fails: an edit to `>` makes the client read the exact halfway as the largest double (finite), while Python reads
inf (refused). The class differs, and the class is what the contract keeps (O62 and the fold's own SF-1 ruling).

Proposed fix (**verified**): add a fixture with the full 309-digit literal. In `probe2/` it is `bad_json` with `>=`
and accepted with `>`. Rename or drop the current fixture.

### NITs
- **D3-N1 `NetSession.close_code` has no reader and no test.** It is written in `NetClient.poll`, and nothing reads
  it. net_check prints only the refusal, so deleting the assignment turns nothing red. The old test line `closed -1`
  pinned the code; the new `closed` doesn't. Either print it in net_check and assert it (−1 for the TCP close, 1008
  for the prose close), or drop the field until a caller exists.
- **D3-N2** `_against` waits a literal `5.0` seconds, not `TIMEOUT_S`.

## Checked, no finding
- `WireFields.version` without `was_float`: the parser makes every non-integer literal a float, so `not value is int`
  covers it. `protocol_float` and `newer_protocol_with_float` still hold it.
- `test_a_reconnect_starts_a_fresh_session` connects to port 1 as a client and binds nothing, and it closes the peer.
- The merge 87ff10e changes no file in this lens.
