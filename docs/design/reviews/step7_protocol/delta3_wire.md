# Wire integrity, delta round 3: phase1/protocol (fold e97727d..a532695, merged at 87ff10e)

**How I checked.** `git archive 87ff10e` went to `<scratchpad>/delta3/wire/head`, and Python ran on that copy
(`simcore.__file__` resolves there). The merge 87ff10e changes only `docs/` files from #51 and #54. It touches none of
this branch's code. I reran delta-2's 1,817 probes, and added 100 new ones (`<scratchpad>/delta3/wire/extra.py`):
22 integer edges, each as `[n]` and as `{"protocol":n}`, plus 28 float literals around the new fixtures. Python judged
each probe with `strict_json.decode`, and `value_tree` came from the committed tree. Godot 4.7.2 judged the same bytes
with `WireJson.parse` and `FrameDecoder.decode`. My probe's `_tree` matches the committed `test_wire_fixtures.gd`, and
Godot ran only through `godot_check.run_godot` / `check` with HOME in scratch.

**Result:** 1,906 of 1,917 probes agree. 11 part: 3 are NT-1 (still open), and **8 are a regression that the fold
introduced (B-1)**.

## Fold table (delta-2 findings)

| # | Status | What I checked |
|---|---|---|
| SF-1 | **fixed** (contract narrowed; see SF-N) | `value_tree` and `_tree` compare a float by its class. §9.1 reads "a float by its class", and `_double`'s comment no longer claims Python's value. The three literals are fixtures (`half_way_digits`, `past_the_integers_as_a_float`, `smallest_normal_double`), and both readers accept each as finite. Every float probe now agrees in outcome and in class, except NT-1's. I didn't mutate this, because the class comparison is trivially true for any finite value. |
| NT-1 | **open** | It is not in the commit message, and it has no checklist or backlog row. `_double` still caps a 7-digit exponent at ±100000, and its docstring doesn't state the bound. `sat_digits_then_neg_exp` and `[1`+999,990 zeros+`e-1000000]` still part (Python accepts them, Godot gives `bad_json`). |
| NT-2 | **open** | It is not mentioned. The client test run still prints `WARNING: Exponent too high`. |

Counts: 1 fixed, 2 open, 0 deferred, 0 rejected.

## New findings in the fold

### BLOCKER

**B-1. `wire_json.gd::_integer`: removing the `_INT_DIGITS` guard (X-N1) rests on a false premise. As a result the
gate's Godot step fails on the committed tree, and the client accepts integers that the server refuses.**
The new comment says that `String.to_int` "clamps a longer literal to the int64 range". It doesn't clamp. Measured
on 4.7.2:
- **The gate.** For a positive overflow, `to_int` prints `ERROR: Cannot represent … as a 64-bit signed integer`.
  The new `integer_past_u64` fixture and the existing `long_integer` fixture both trigger it, so `res://tests/run.gd`
  prints two `ERROR:` lines. `godot_check.ERROR_LINE` matches them. I ran `godot_check.check` on the committed
  `client/`, and it returned
  `tests: Godot printed an error: ERROR: Cannot represent 18446744073709551617 …` and the same for `111…1` (30 digits).
  So `scripts/prepush.sh` can't print PASS for a532695 or 87ff10e. The author's "redone, it was green" mutation
  checked the sentinel line, not the gate. The guard was in fact distinguishable.
- **Parity.** In some cases `to_int` returns INT64_MIN, and `absi(INT64_MIN)` is still INT64_MIN, which is negative
  and so passes `> INT_MAX`. Godot **accepts** each of these as the int −9223372036854775808, where Python refuses
  them with `bad_json`:
  - `9223372036854775808` (2⁶³), which is positive;
  - `-9223372036854775808`;
  - `-18446744073709551617`;
  - `-` followed by 400 nines.

  These are 8 probes, counting the `[n]` and `{"protocol":n}` forms. That breaks §9.1's "judged alike, code". A
  hostile local server (or a corrupted text) can now hand `NetSession` a `session` or `tick` of −2⁶³ that passes the
  integer pin.
- **Test gap.** No fixture holds 2⁶³ or −2⁶³, so the client tests stay at `PASS 90` while the parity is broken.

Verified fix: I restored the guard in a scratch copy (`digits > 16 or …`, short-circuiting before `to_int`). The
result was 0 `ERROR:` lines, `client-tests: PASS 90 tests`, and every integer probe agreeing (1,914 of 1,917; the
3 left are NT-1). Add fixtures `[9223372036854775808]` and `[-9223372036854775808]`, both refused, and correct the
comment.

### SHOULD-FIX

**SF-N. The float-by-class narrowing is a contract change made by the author, with no decision row. O67 got one for
the analogous U+0000 call.** The commit says that dropping float values from the parity contract is "the author's
call, flagged to the owner". The only place that flag exists is the commit message. `decisions/boundaries.md` has no
row for it, so it isn't on the owner's queue. Failure scenario: the owner rules for a correctly rounded conversion,
or reads §9.1 as the owner's own wording. Either way nothing records that O63's "code and value" was narrowed or who
narrowed it. A later reviewer then treats it as settled. Fix: add an author-marked row, like O67, and cite it from
§9.1.

### Checked, no finding

- **Reply cap.** `replies.text` measures `len(str)`, and `encode` uses `ensure_ascii=True`, so characters are bytes.
  For example, 30,000 `é` encode to 180,019 bytes and are refused.
- **The cap's boundary.** The server refuses `> 65536`, and `WireJson.parse` refuses `> max_bytes`, so exactly
  65,536 bytes passes on both sides.
- **Send sites.** All four `send` sites in `server.py` go through `text`. The welcome at shape 400³ is 658 bytes.
- **Limits.** The manifest's `max_text_bytes` (65536) is compared with `NetSession.MAX_TEXT_BYTES` in
  `test_the_client_s_limits_are_the_server_s`, and the key-count check covers it.
- **Oversize replies.** An oversized reply raises `ValueError` out of the handler. websockets logs it and closes with
  1011, and the session's `finally` still runs. That is loud, as stated.
- **New fixtures.** All 5 reach their manifest outcomes on both sides. `exact_halfway_past_the_largest_double` is
  refused by both.
- **`WireFields.version`** without `was_float`: a float literal is a GDScript float, and both forms of the
  `{"protocol":<float>}` probes agree.
- **Tests.** `tests/test_host.py` passes (42) and `tests/test_wire*.py` passes (309, 1 skipped).
