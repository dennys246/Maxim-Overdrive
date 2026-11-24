# Delta round 1, Executor + Trust boundary: phase1/guest-text-rulings (fa40450..6480408)

Scope: the fold commit only. Every probe and mutation ran on a `git archive 6480408` copy in `scratchpad/review/d1/c`, with `pytest -o pythonpath=<copy>`. Scripts are `d1/p1.py`, `p2.py`, `p3.py`, `reach.py`, `udhr.py`, `names.py` and `mutc.sh`. I wrote nothing in the repo.

**Tree note:** while I was reviewing, the worktree got uncommitted edits that are not mine (`text.py` `_never` became `_joiner`, a new TALL_STACKS case, and changes to O70, O72 and the checklist). Two early mutations accidentally ran against that WIP and were thrown away; everything below was rerun on the commit. `git status` is dirty only with that author WIP.

## Verdict

No BLOCKER. The fold closes what round 1 found. I remeasured the UDHR basis and it holds: 535 files, stack heights {1: 71,685, 2: 5,549, 3: 349, 4: 1}, and the one stack of four is in `udhr_mya`. Every mutation count in the commit message reproduces.

Two defects are new in the fold:
- the joiners let a stack get past the cap;
- O71's "at most about 508 bits" is not an upper bound.

There is also an over-refusal that O71 doesn't record.

## Round-1 fold status (set by me from the 6480408 tree)

| Finding | Status | Evidence |
|---|---|---|
| E-S1 / TW-S1 | **fixed** | `MAX_MARKS`, marks skipped in the blank run, five joiners in `NO_INK`, O70 corrected. `"h"+"្"*200+"i"` and `"a"+"  ́"*150+"b"` are both refused. The restated bound has its own errors (D1-S2). |
| E-S2 / TW-N2 / Arch SF-1 | **fixed** | `test_a_listed_character_is_no_name_either`. Deleting `visible_name`'s `_blank` line turns it red (run). |
| E-N1 / TW-N1 | **fixed** | ␢ alone, `a␢␢␢b` and three Bhaiksuki fillers all pass. The 16 BLANK/FILLER names are identical on 3.12 (15.0) and 3.14 (16.0), checked. No formerly matched character that draws nothing gets through: the hieroglyph blanks and the Khitan filler are in `NO_INK`, and the Hangul fillers are default-ignorable. Names still refuse all 16 (probed). O72 was the author's call at this commit. |
| E-N2 | **fixed** | In 300 examples on the commit: 34 refused by the stack rule, 57 by the run rule. See D1-N1 for a gap in its oracle. |
| E-N3 | **open** | Trailing and double spaces are still refused, not trimmed. No row records this for the `speak` step, and the commit message doesn't mention it. |
| TW-N3 | **fixed** | Positions are asserted. Making `_past_cap_at` return `i - 1` turns 8 tests red (run). |
| TW-N4 | **fixed** | Row 7 no longer lists O70. |
| Arch N-1, N-2, N-3, N-4 | **fixed** | Docstring line, §5.3 wording ("never three inkless in a row", "one selector"), reflow, and the `MAX_BLANK_RUN` comment now cites O70. |

## New findings

### SHOULD-FIX D1-S1. `text.py::_check_runs` (stack count, `skipped=_never`): a ZWJ or ZWNJ between marks splits a stack, so one glyph carries 12 marks

`_drawn_at` and `_visible` treat a mark as visible, so a joiner between two marks passes O61's joiner rule. The joiner is not a mark, so it resets the stack counter. The blank-run counter allows two joiners in a row, because marks are skipped there.

Measured on 3.12:
- `"h"+M4+ZWJ+M4+ZWNJ+M4+"i"+…` passes, with 12 marks per visible letter (`M4` = U+0301..0304).
- `"x́‍̂"` passes.
- Three joiners are refused as a run.

Failure scenario: O71's sentence "at most four marks follow one character" is false as a guest sees the text. All 12 marks render on one letter, and the joiner choices add a bit each.

The bound arithmetic is nearly untouched, because the joiners act as gap characters (D1-S2). The fix is the WIP's `skipped=_joiner` together with its test case. That is **unverified at this commit**, and the next delta should check it. Check also whether any real Indic sequence puts a joiner between two marks: a virama followed by ZWJ and a vowel sign would be refused under that fix.

### SHOULD-FIX D1-S2. `decisions/boundaries.md` O71 and the checklist row: "'hi!' hides at most about 508 bits" is exceeded

Two sites are left out of the bound.

- **A stack with no base at the start of the text.** `M4+"hi!"` passes, and so does `M4+" "+M4+" "+M4+"hi!"`. That adds a fifth stack of about 43 bits.
- **The joiners.** The bound uses 21 inkless characters, but a joiner flanked by marks is a 22nd and 23rd gap character (D1-S1).

My counts:
- Marks that pass after "a": 1,729 (1,698 leave NFC unchanged). I cannot reproduce 1,706.
- With A = 1,729 and 21 inkless characters, O71's own formula gives 508.4, so the arithmetic is right.
- Adding the leading stack and 23 gap characters gives **about 552 bits** (551.5 with A = 1,706).

This is the third revision of the same claim, and every one of them was too low. The owner rules on these numbers. The fix is to restate the bound (about 552, or about 509 once the leading stack and joiner-split stacks are refused) or to refuse a mark at position 0. Either is unverified; which one is the owner's call. The WIP's fix for D1-S1 removes the joiner term but not the leading stack.

### SHOULD-FIX D1-S3. `text.py::MAX_MARKS` / O71: the UDHR basis is modern prose, and the cap refuses real liturgical and transliterated text that O71 doesn't record

Refused on 3.12 (code points chosen by me):
- Tibetan Sanskrit stacks, where subjoined consonants are Mn on one base:
  - `ཀྵྨྲྱཱུཾ` U+0F40 0FB5 0FA8 0FB2 0FB1 0F71 0F74 0F7E: 7 marks.
  - `ཀཱརྟྶྣྱཱ`, with 5 marks on ར.
  - The Kalachakra monogram (ཧ with ྐ ྵ ྨ ླ ྭ ྲ ྱ ཾ) is far taller. Tibetan mantra and dhāraṇī text writes such stacks routinely.
- Hebrew with a dagesh, a shin dot, a vowel, meteg and an accent (U+05E9 05BC 05B8 05BD 05C1 05A5). The fold's own TALL_STACKS case is this shape. **Unverified** that the Leningrad Codex has a 5-mark letter; measure a cantillated Tanakh (OSHB/WLC).
- A constructed Vedic syllable with candrabindu, anudātta, svarita and U+1CD1. Its reality is **unverified**.

Passes: Thai, decomposed Vietnamese (NFC composes it), Yoruba, the IPA cases I built (up to 5 code points, at most 4 marks after NFC), the Quranic `وَٱلَّٰٓـِٔى` (exactly 4 on lam), a Samaveda syllable with svara digits, and NFC-expanding exclusions (U+0F73, U+0F75, U+0958).

Failure scenario: a Tibetan-speaking guest types a mantra and gets BAD_TEXT. O71 says the number was "measured" and never says what it costs. The fix is to name the over-refusal in O71 or the checklist with these examples, or to measure a liturgical corpus before the owner confirms 4. Both are unverified.

### NIT D1-N1. `tests/test_text.py::_assert_no_long_runs`: the property test's oracle reads `MAX_MARKS` and `MAX_BLANK_RUN` from the module under test

With `MAX_MARKS = 1000` on the commit tree, `test_whatever_passes_holds_no_long_run_and_no_tall_stack` stays green, even though 52 of its 300 outputs then held stacks of five or more (`d1/reach.py`). Only TALL_STACKS catches the number. The property guards the counting logic, not the cap. The fix is to use literals 2 and 4 in the oracle. Unverified.

### NIT D1-N2. `text.py::MAX_MARKS`: U+FE0E and U+FE0F are Mn, so they count toward the stack

`"❤️"+M4` is refused at 5: an emoji with a presentation selector carries only three marks. This is harmless, and the O71 text could say so. A spacing mark (Mc) resets the count. That is correct, because an Mc draws a spacing glyph (`"क"+("ा"+M4)*90` passes as 90 visible characters).

## Mutation claims (rerun on 6480408)

| Claim | Measured |
|---|---|
| `MAX_MARKS` 1000: 5 red | 5 (the TALL_STACKS cases only) |
| `MAX_MARKS` 3: Burmese, Hebrew and four-mark cases red as well | 8, which is 5 + those 3 |
| Marks ending a blank run: 3 red, property test among them | 3: property, floated marks, position `hi a ́ ́ b` |
| Joiners unlisted: 6 red | 6 |
| Name matching restored: 3 red | 3 |

Baseline: 97 passed.

## Trust checks (no finding)

- The new refusals echo no text: they name only a position and a count.
- Both are BAD_TEXT.
- The new code is pure and linear.
