# Wire integrity + Trust boundary: phase1/guest-text-rulings (fa40450, O70)

Scope: `git diff origin/main...HEAD`. Ran `.venv/bin/pytest -q tests/test_text.py` (75 passed, Python 3.12.12) and
three probes, kept in the scratchpad (probe.py, probe2.py, probe3.py). The tree is unchanged.

## Summary

The run cap works as written. A run of three or more non-combining characters that draw nothing is refused, U+1D159
is refused alone and in runs, the refusal never echoes the text, and the new paths are tested. **But O70's record
claims the channel is now bounded ("a gap holds at most about 9.8 bits"; the checklist adds "'hi!' hides at most
about 39 bits"), and that claim is false.** Combining marks count as "drawn", so they are never counted in a run, and
any number of them can stack on one visible base. One SHOULD-FIX follows from that. No BLOCKER. On the wire side
nothing changes: `player_text` still has no caller on the shipped path (true on main too, and recorded).

## Findings

### TW-S1 (SHOULD-FIX). `src/simcore/core/text.py::_long_blank_run_at` / `_visible`: stacked combining marks carry unbounded hidden bits per visible character, so O70's "bounded" claim is false

`_visible` returns True for every Mn or Me character that isn't Default_Ignorable or named BLANK/FILLER. So a
combining mark resets the run counter, and nothing caps how many marks follow one base. Measured on 3.12:

- Five Mn "joiner" marks pass in any run length and in practice draw nothing after a Latin base: U+2D7F TIFINAGH
  CONSONANT JOINER, U+1107F BRAHMI NUMBER JOINER, U+11A47 ZANABAZAR SQUARE SUBJOINER, U+11A99 SOYOMBO SUBJOINER,
  U+11F42 KAWI CONJOINER. They have no property and no BLANK or FILLER name, which is the same class as U+1D159.
  `"hi" + 495 of them + "!"` passes at max_chars=500, about **1,149 bits**. My name filter found these five; the
  real set is probably larger. Whether they draw nothing depends on the font and was not measured.
- Any mark: 814 Mn characters of combining class 0 that NFC leaves unchanged pass after `"a"`. `"h" + 497 of them +
  "i!"` passes (NFC length 500), about **4,805 bits** under three visible characters. That is twice the 2,390 bits
  O70 was ruled to close. These marks do draw ink, but as an unreadable smear on one letter, and the LLM reads every
  code point.
- The cap can be stepped around: `"a" + "  ́" * 150 + "b"` passes. Two spaces plus a mark floated on a space
  makes each segment about 9.8 + 9.7 bits.

Failure scenario: at `phase1/agents`, a guest's `speak` passes the gate, and its text reaches an NPC prompt carrying
kilobits of instructions under a few visible characters. Meanwhile `decisions/boundaries.md` O70 and the
`checklists.md` step 7 row tell the owner the channel is bounded at about 9.8 bits a gap. The owner ruled on a false
premise. That makes this a contract-record error, not just a mechanism gap.

Fix, **unverified**, and it needs the owner, since it is a rule the rulings don't hold. (a) Correct O70's text and
the checklist row now: the cap bounds runs of spacing and blank base characters only, and combining marks stay open,
with the numbers above. (b) A cap on marks per base character. UAX #15's Stream-Safe Text Format caps non-starters at
30, but class-0 marks escape that, so the rule has to count Mn and Me regardless of combining class. (c) Add the
measured invisible joiner marks to `NO_INK`, where `_refused_at`'s `zero_width_blank` clause would then refuse them
outright as Mn blanks.

### TW-N1 (NIT). `src/simcore/core/text.py::_blank` + `tests/test_text.py::PASSES`: U+2422 BLANK SYMBOL draws ink but now counts toward a run

`_blank` matches "BLANK" in the name, so ␢ is treated as drawing nothing, and `"a␢␢␢b"` is now refused (measured).
The PASSES comment, `"␢ x"  # the BLANK SYMBOL, which draws`, contradicts the code. That case passes only
because of the `x`. ␢ also inflates the "29 that draw nothing" count O70 cites: my count of gap characters is 31,
which is 29 blanks plus ZWNJ and ZWJ, and one of the 29 is ␢. The record's 9.8-bit figure still holds: log2(1 + 31 +
29²) = 9.77. Fix (unverified): exclude U+2422 by code point, or match only whole-name blanks. Low impact. Real text
rarely holds three of them.

### TW-N2 (NIT). `tests/test_text.py::test_the_null_notehead_is_no_name_either` doesn't guard what its name implies

`idna.check_label("crate\U0001d159")` already refuses the name (measured: "Codepoint U+1D159 ... not allowed"), so
deleting `NO_INK` from `_blank` leaves this test green. The test can still fail on other breakage, so it isn't a
test that cannot fail. It just doesn't prove that `NO_INK` reaches names. Either drop it or retitle it as a
regression pin on IDNA.

### TW-N3 (NIT). `tests/test_text.py::test_a_run_of_more_than_two_characters_that_draw_nothing_is_refused`: the reported position isn't asserted

`run_at = i - MAX_BLANK_RUN` is never checked, so an off-by-one (reporting `i`, or `i - 3`) stays green. A guest
correcting a refused message relies on that index. Add `match="at 1"` for `"a   b"`. Unverified.

### TW-N4 (NIT). `docs/plans/foundations_plan.md` step 7 row lists O69 and O70 under "shared fixtures"

No wire fixture or client code carries O70. `client/tests/fixtures/wire/` and `scripts/wire_fixtures.py` are
untouched, and the client never handles guest text. The row reads as though both decoders implement it. Wording
only.

## Wire integrity checks (no finding)

- **Callers:** `grep player_text src scripts` finds only its definition and a comment in `refusals.py`. No
  `speak` message exists in `protocol/messages.py`. `checklists.md` (around line 406) records that `player_text`
  runs only under tests until the shipped path lands, and the step 8 agents row names `phase1/agents` as the first
  caller. The behaviour isn't live, which is consistent with what's recorded. "A fix ships with a caller" is met
  only by that recorded deferral.
- **Gate registry:** `scripts/lint_gates.py` lists `text.py::player_text` and `visible_name` as `meets` with
  `tests/test_text.py`. The new rejection path is in that module.
- **Refusal code:** the new refusal uses `RefusalCode.BAD_TEXT` (`"bad_text"`, in `test_refusals.py`'s spelling
  list). The host replies with `error(refused.code, refused.field)` (`host/server.py:137`), so the message, with its
  index, never reaches the client, and no guest text is echoed either way. The client has no `bad_text` handling,
  and needs none until a guest-text message exists.
- **Client and fixtures:** O63 keeps Unicode tables out of the client, and the client doesn't judge guest text, so
  the Godot side has nothing to agree with yet.

## Trust boundary checks (no finding)

- **Echo:** `player_text("secret   x", ...)` gives `'speech holds a run of more than 2 characters that draw nothing
  at 6'`. The existing `test_a_refusal_never_echoes_the_text` covers the shape.
- **Rejection paths tested:** the run refusal (LONG_RUNS: start, end, middle, braille, U+1D159, the 496-character
  attack), U+1D159 alone and with a space (HIDDEN), and runs of two passing (PASSES). The "draws nothing" branch is
  still reachable, through all-blank text of at most two characters (`"\U0001d159"`). By reading, setting
  `MAX_BLANK_RUN` to 3 turns `"a   b"` red, setting it to 1 turns `"Done.  Next"` red, and dropping `NO_INK` turns
  both U+1D159 cases red. I didn't run those mutants. The Hypothesis property now asserts no run of three, and its
  `_draws` is a superset-safe independent reading.
- **Crash and determinism:** the new code is pure. `unicodedata.name(ch, "")` takes a default, and lone surrogates
  are refused earlier. The worst case measured about 2.1 ms per 500-character call. The `_blank` name test depends
  on the interpreter's Unicode names, the same dependency as before; the 3.12/3.14 split is already recorded for Cn.

## Surviving channels, quantified (Python 3.12, max_chars=500)

| Channel | Bits | Status |
|---|---|---|
| Gap of 0 to 2 blanks between visible characters | about 9.8 per gap | bounded, as O70 says |
| Joiner or selector beside a visible character | 1 to 2 per visible character | open, recorded |
| Invisible Mn joiners stacked on one base | about 2.3 per mark, unbounded (1,149 in "hi…!") | **open, unrecorded (TW-S1)** |
| Any class-0 Mn stacked on one base | about 9.7 per mark, unbounded (4,805 in "h…i!") | **open, unrecorded (TW-S1)** |
