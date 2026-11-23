# Client and rendering lens: delta round 4 (fold 87ff10e..5471454, merged at 0eba5e8)

Method: I reviewed the committed tree, using `git archive 0eba5e8` into `<scratchpad>/delta4/client/tree`. The worktree
was clean. The merge 0eba5e8 changes no client, protocol, host or Godot-test file; it only touches
checklists/roadmap links to `docs/known_gaps.md`. Every Godot run went through `scripts/godot_check.py` in a copy, or
through `gc.run_godot` with HOME under `<scratchpad>/delta4/client/`. The baseline is `godot_check: PASS`, and
`tests/test_wire.py` gives 313 passed.

## Fold table (delta-3 findings)

| # | Status | What I checked |
|---|---|---|
| S4(b), N3, N-N1, D2-N1 | **deferred, accepted** (unchanged) | All are still listed in checklists.md step 7 or B5, each with its trigger. |
| N-N2 the client closes with 1000, not 1008 | **open** | The code is unchanged. The commit lists it as open, and it is in no checklist or backlog row. |
| N-N3 the engine-fact socket test was flaky | **fixed** | The test now accepts 0 or 1 raw packets and requires the reason `bad_token`. §4.3 and NetClient say "can/may drop". **Flake runs:** 60 sequential runs in one loop (`<scratchpad>/delta4/client/loop.py`) all gave 0 packets. 3 × 60 runs in parallel, under load, gave 178 with 0 and 2 with 1 packet, and every one had reason `bad_token`. None fell outside the accepted set and none had an error finding. The whole `tests/test_godot_net.py` module, run 12 times, passed all 7 tests each time. So the engine fact is real (the 1-packet case reproduces, at about 1%, under load), and the new assertion holds in every case seen. The test can still fail: it goes red if the reason stops arriving. It no longer flips on an engine upgrade that always holds the packet, and that is an acceptable loss. |
| D3-SF1 the digit guard was removed | **fixed** | `_integer` checks `digits > _INT_DIGITS` (16) before `to_int`. The new fixtures (2⁶³, −2⁶³, 400 nines) are refused on both sides, and test_wire passes. **Mutations:** a guard disabled (`digits > 100000`) gives `FAIL 3 failure(s)` plus five engine-ERROR findings. `_INT_DIGITS = 19` gives `FAIL 2 failure(s)` (the 2⁶³ pair). `_INT_DIGITS = 15` gives `FAIL 3`. `_INT_DIGITS = 17` passes, which is expected: 17 and 18 digits fit in int64, so `absi` still refuses them. That is no defect. |
| D3-SF2 the halfway fixture | **open** | See D4-SF1. The fold added the 309-digit literal, but as an **integer**. It goes through `_integer` (the digit guard), never the float path, so `_past_largest` is still unguarded. When I mutated `>=` to `>` in `_past_largest`, the result was still `godot_check: PASS`. |
| D3-N1 `close_code` had no reader | **fixed** | The field and its assignment are gone. A grep for `close_code` over client/ finds nothing. The test line now reads `session.end("closed")`. |
| D3-N2 `_against` waits a literal `5.0` | **open** | It is unchanged (`tests/test_godot_net.py:157`) and not mentioned in the commit. |

**Counts: fixed 3 (N-N3, D3-SF1, D3-N1), deferred and accepted 4, open 3 (N-N2, D3-SF2, D3-N2), rejected 0.**

## New findings (the fold's diff)

### D4-SF1 (SHOULD-FIX). The "exact halfway" fixture is an integer literal, so it never reaches the boundary it names
`client/tests/fixtures/wire/json/exact_halfway_past_the_largest_double.json` and `scripts/wire_texts.py`
(`exact_halfway_past_the_largest_double`). The literal `[1797…792]` (309 digits, no `.` and no `e`) is exactly
2¹⁰²⁴ − 2⁹⁷⁰; I checked this in Python. But a number with no `.` and no exponent is an integer to both decoders. Godot
refuses it in `_integer`, because it has more than 16 digits, and Python refuses it as an integer of 2⁵³ or more. Both
give `bad_json` without ever rounding a float. The comment ("the tie … which rounds to even (inf)") and the commit's
claim ("inf on both sides, round to even") describe a path this text does not take.

How it fails: someone edits `_past_largest`'s `>=` to `>`. The client then reads a float written at the exact halfway
as the largest double (finite), while Python reads inf and refuses it. Measured: with that mutation the gate stays
`PASS`. The two decoders disagree on a class, which is what O62/O68 promise to keep alike.

Proposed fix (**verified**): write the same digits as a float, `[1.797693134862315807937…174497792e308]` (one `.`
after the first digit, then `e308`). Python's `strict_json.decode` refuses it as `bad_json` (inf), and the same digits
ending `…1e308` decode to 1.7976931348623157e308. I put that text into the fixture file in two copies of the tree. With
`>`, the result was `client-tests: FAIL 1 failure(s) in 90 tests`; with `>=`, it was `godot_check: PASS`. Keep the
integer form too, under an integer name, if it is wanted.

### NITs
- **D4-N1** `wire_json.gd::_integer`'s comment says `to_int` "prints an engine ERROR on overflow and returns -2^63".
  That is only partly true. With `_INT_DIGITS = 19`, 2⁶³ and −2⁶³ reached `to_int`, and the run printed **no** engine
  ERROR. 2⁶³ wraps silently (as in delta 3), and −2⁶³ is exactly INT64_MIN, a valid int64. Only longer literals, such
  as 2⁶⁴ + 1 or 30 ones, print the ERROR. The commit's line "it prints an engine ERROR on a positive overflow, which
  the gate's error scan catches" is therefore not true of 2⁶³. Say "wraps (2⁶³) or clamps with an engine ERROR (longer
  literals)".

## Checked, no finding
- The merge 0eba5e8 changes nothing in this lens.
- `_INT_DIGITS = 16` is correct: every literal of up to 16 digits fits in int64, so `absi` is exact there, and leading
  zeros are refused upstream.
- `just_past_the_halfway` (the old literal) stays refused on both sides, and its name is now accurate.
