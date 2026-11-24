# Wire integrity, delta round 4: phase1/protocol (fold 87ff10e..5471454, merged at 0eba5e8)

**How I checked.** I ran `git archive 0eba5e8` into `<scratchpad>/delta4/wire/head`, and Python ran on that copy
(`simcore.__file__` resolves there). The worktree has uncommitted edits to `text.py` and `checklists.md`, so I
reviewed none of them. The merge 0eba5e8 adds exactly what #52 changed on main: diffing the two patches shows only
index hashes and hunk offsets apart. It changes none of this branch's wire code.

I reran the delta-2 and delta-3 probes (1,917) and added 58 new ones (`<scratchpad>/delta4/wire/extra4.py`). The new
ones are integers at 16 and 17 digits, at ±(2⁶³−1), at −2⁶³−1 and at 21 and 30 digits, each written three ways: as
`[n]`, as `{"protocol":n}` and as `{"session":n,"tick":n}`. They also include 7 float literals near the integer edges.

Python judged each probe with `strict_json.decode` and `value_tree`. Godot 4.7.2 judged the same bytes with
`WireJson.parse` and `FrameDecoder.decode`, through `godot_check.run_godot` with HOME inside scratch.

**Result.** 1,972 of 1,975 probes agree. The 3 that part are all NT-1. Every integer probe agrees, both signs, at and
past int64. The probe run printed no `ERROR:` line, only NT-2's 20 `WARNING: Exponent too high` lines.

**The gate's Godot step.** `godot_check.check` on the committed `client/` returns no findings, and the run ends
`client-tests: PASS 90 tests`. The log has no `ERROR:`, `SCRIPT ERROR` or `Parse Error`. Its only warnings are NT-2's
and the Cutaway warning.

**Python tests.** On the archive copy, `tests/test_wire*.py` and `tests/test_host.py` give 355 passed, 1 skipped.

## Fold table (delta-3 findings)

| # | Status | What I checked |
|---|---|---|
| B-1 | **fixed** | `wire_json.gd::_integer` counts digits (sign excluded) before `to_int` runs. The fixtures for 2⁶³, −2⁶³ and a 400-digit negative are refused on both sides. All 74 integer probes agree, and `to_int` prints no ERROR. Two mutations in scratch copies: (a) `_INT_DIGITS = 19` gives `client-tests: FAIL 2`, because `integer_at_2p63` and `negative_integer_at_2p63` are accepted; (b) the guard off (`_INT_DIGITS = 100000`) gives 5 "Godot printed an error" findings plus `FAIL 3`. I watched both go red. The comment is now correct. |
| SF-N | **fixed** | O68 is an author-marked row reading "awaiting the owner". §9.1 cites it, and the row states the alternative. |
| NT-1 | **open** | It is listed as open in the commit message, but it has no checklist or backlog row, so it isn't deferred. The 3 probes still part (Python accepts them, Godot gives `bad_json`). |
| NT-2 | **open** | Same as NT-1: no checklist or backlog row. The client tests still print `WARNING: Exponent too high`. The gate's scan ignores warnings, so the gate stays green. |

Counts: 2 fixed, 2 open, 0 deferred, 0 rejected.

## New findings in the fold

### SHOULD-FIX

**W4-S1. `scripts/wire_texts.py::_number_and_structure_edges`, `exact_halfway_past_the_largest_double`: the fold of
Client D3-SF2 adds a fixture that never reaches the tie it is named for.**

The fixture is `[2^1024 − 2^970]` written as a bare integer of 309 digits. Both readers refuse it on the integer path.
Python's reason is "an integer of magnitude 2^53 or more (309 characters)", and in Godot the new digit guard refuses
it. So `_double` and `_past_largest` never see it. The commit's claim, "inf on both sides, round to even", is not what
the fixture tests, and the comment in `wire_texts.py` repeats that claim.

Failure scenario: I changed `_past_largest`'s `>=` to `>` in a scratch copy, which rounds the tie to the largest
double instead of to inf. `godot_check.check` on that copy returns **no findings** (`PASS 90`). Yet the mutant
accepts `[H.0]`, `[He0]`, `[1.79…792e308]` (all the digits) and `[-H.0]` as finite, and Python refuses all four as
`bad_json`. That is 4 partings that the shipped fixtures can't see.

Verified fix: write the tie on the float path, for example `[<H>.0]` or `1.` followed by the digits and `e308`. On
the committed tree, Python and Godot agree on all 4 of those forms and on 2 values just below the tie (7 of 7). Under
the mutant 4 of them part, so a fixture in that form fails. The bare-integer fixture can stay, renamed for what it
is: an integer past int64.

### NIT

**W4-N1.** `_INT_DIGITS = 16` and the magnitude check are indistinguishable for any value from 16 to 18: 17- and
18-digit literals fit int64, so `absi > INT_MAX` refuses them anyway. No fixture pins 17 digits. That is harmless,
but the comment "INT_MAX's digit count" suggests the exact value matters.

## Checked, no finding

- **`close_code` removal.** Nothing in `client/` reads it any more. The remaining hits are Python's websockets
  attributes in tests.
- **Session and tick integers.** The `{"session":n,"tick":n}` probes at ±2⁶³, ±(2⁶³−1) and 30 digits all agree, so
  no −2⁶³ reaches `NetSession`.
- **The renamed fixture.** `just_past_the_halfway` (`1.79769313486231581e308`) is refused on both sides through the
  float path.
