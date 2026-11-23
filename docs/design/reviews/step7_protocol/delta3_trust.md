# Trust boundary, delta round 3: phase1/protocol (e97727d ... a532695, merged at 87ff10e)

Lens: Trust boundary. I reviewed the committed tree at 87ff10e, unpacked with `git archive` into
`<scratchpad>/delta3/trust/wt`. `git diff a532695 87ff10e -- src client tests scripts` touches none of this branch's
protocol, text or client files. Probes are in `<scratchpad>/delta3/trust/`: `edges.py` (new guest-text cases), and I
reran delta 2's `sweep.py` (every code point named BLANK or FILLER, plus the hidden-run constructs). Godot ran only
through the test module's `run_godot`, with `--basetemp` (and so HOME) inside the scratch directory.

Counts: fold table **4 fixed, 1 deferred (accepted), 3 open, 0 rejected**. New: **0 BLOCKER, 1 SHOULD-FIX, 3 NIT.**

## Fold table (status read from the tree)

| Id | Status | What I checked |
|---|---|---|
| N-S1 blank rule too wide | **fixed** | `_refused_at` refuses a blank only when it is `Mn`. Sweep: braille text, `"a ␢ b"`, `"word꣹"` and the Po gap fillers inside a word are accepted. `"⠀"`, `"\U00016fe4"`, `"\U00013441"`, `"x‍⠀y"`, `"a𓑁‍𓑁b"` and a run of 50 Khitan fillers are still refused. All four hidden-run constructs except U+1D159 are refused at caps of 500 and 200. Mutation (back to `_blank(ch)`): the two new PASSES cases go **red**. One gap: the `Mn` clause itself has no test (new T3-S1). |
| N-S2 close-reason check untested | **fixed** | `test_a_close_reason_that_is_no_code_is_not_taken_as_one` exists. Mutation in the scratch copy (`var coded: bool = not reason.is_empty()`) with `MAXIM_OVERDRIVE_GODOT=1`: **1 failed, 6 passed**, and the failure is that test. On the unmutated copy, 7 passed. |
| N-N1 dead `not _blank` in `_visible` | **fixed** (now live) | Removing the clause turns three `HIDDEN` cases **red** (the braille blank alone, blanks and spaces, the hieroglyph blank). The author also dropped `_visible`'s default-ignorable clause. That is safe: each such character is refused at its own index first, and the case `a‍͏b` is still refused. |
| N-N2 U+1D159 residual | **deferred, accepted** | `checklists.md` step 7 lists it with a reason and a trigger (the first guest text an NPC reads, when a rendering test can measure ink). |
| N-N3 code shape vs `test_refusals` | **open** | Not addressed, and not mentioned in the commit. `CODE` is still `^[a-z][a-z_]{0,31}\z` with no shared fixture tying it to `RefusalCode`. A code-shaped hostile reason is still taken verbatim. |
| D-N5 fuzz reach unasserted | **open** | The commit lists it as open. `tests/test_wire.py` still asserts no reach for the message property test. |
| D-N6 `bad_version` field | **open** | The commit lists it as open. `_check_protocol` is unchanged. |

## New findings

### T3-S1 (SHOULD-FIX). The zero-width-blank refusal has no test that can fail
`src/simcore/core/text.py::_refused_at` (`zero_width_blank`)

The only character this clause refuses on its own is U+16FE4 KHITAN SMALL SCRIPT FILLER (the one blank of category Mn).
The two Khitan cases in `HIDDEN` are caught by other rules: the filler alone is caught by "draws nothing", and the
filler beside a joiner is caught by the joiner rule. Mutation `zero_width_blank = False`: `tests/test_text.py` gives
**61 passed**. On that mutant, `player_text("a" + "\U00016fe4"*498 + "b", ..., max_chars=500)` is **accepted**:
498 zero-width marks stacked on one letter, a count that shows nothing on screen. This is the D-B1 attack class that
delta 1 rated a BLOCKER, and the fold's new clause is its only guard.

Failure scenario: a later simplification (say, "blanks are like spaces now", so the clause is dropped), or a wrong
category string, passes the gate, and guest speech can again carry an invisible run to an NPC's prompt.

Fix (**verified**): add `("a\U00016fe4b", "a zero-width filler mark inside a word")` to `HIDDEN`. With the mutant it
goes **red** (1 failed, 61 passed). With the committed code it passes (62 passed).

### NITs
- **T3-N1** `net_client.gd::poll`, `net_session.gd::close_code`: `close_code` is written but no code or test reads
  it. The origin test lost its `-1` assertion, and no test now checks a close code the client recorded. Architecture
  N-6 moved the code there "apart", but that field has no reader and no guard. Either assert it in
  `test_a_close_reason_that_is_no_code_is_not_taken_as_one` (1008) or drop it until step 8 needs it.
- **T3-N2** `text.py`, a pre-existing gap the fold widens slightly. Spacing blanks now join the Zs spaces (thin, hair,
  en, em, ideographic and the rest) as characters that draw nothing, and are allowed between visible ones. Choosing
  among them carries bits: `"hi"` + 200 characters alternating U+2009 and U+200A + `"!"` is accepted, and so are the
  braille-blank/space and braille-blank/hieroglyph-blank versions (`edges.py`). This is O65's "a run of them can carry
  hidden bits" by a different route. No checklist row, Known gap or backlog row records it. Record it with the U+1D159
  residual, under the same trigger.
- **T3-N3** `text.py::_visible`: a blank that draws a glyph (U+2422 BLANK SYMBOL, U+A8F9 and the other Po gap fillers)
  is refused when it stands alone ("draws nothing"), and a joiner before one is refused (`"क‍꣹"`). This rarely
  matters, but the docstring says these characters "keep working". It holds only inside other text.

## Checked, no finding
- **`replies.text` cap:** `encode` is `ensure_ascii`, so counting characters is counting bytes. The server refuses a
  reply only past 64 KiB, and the client's `parse` refuses only past the same cap (`>`), so the two agree at the
  boundary. The `ValueError` names only the reply's type and its size, never its content.
- **`type` not a String:** the client unit test covers 5, true, [1] and {}. Comparing `kind is String` first is right.
- **`session.end` keeps the first refusal**, so a peer's close reason can't overwrite an error the client already
  recorded.
