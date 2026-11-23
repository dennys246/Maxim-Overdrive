# Executor lens: phase1/guest-text-rulings (fa40450)

Scope: `src/simcore/core/text.py`, `src/simcore/core/text_tables.py` and `tests/test_text.py` in `git diff origin/main...HEAD`, plus the numbers in O70 and the commit message. Probes live in `scratchpad/review/` (`measure.py`, `probe.py`, `marks.py`, `reach.py`, `mutate.sh`). Mutations ran on a copy of `src/`, selected with `pytest -o pythonpath=<copy>`. `git status` is clean.

## Verdict

For runs of spaces and blanks, the code does what O70 says. The cap counts on the NFC text. A space, a named blank, a gap filler, U+1D159 and a joiner all count as part of a run. The refusal names where the run starts and never echoes the text. The reported index is correct at the start, in the middle and at the end, and after an emoji with its selector. I found no input where spaces or blanks get past the cap: NFC folds U+2000 and U+2001 to U+2002 and U+2003, and the run is counted after that fold, so those cases are refused too.

The claim around the cap is wrong, though. O70 and the checklist say the channel is "bounded", and it is not, because combining marks are not counted at all. That finding comes first below.

## Numbers remeasured (all confirmed)

| Claim | Measured |
|---|---|
| 29 characters that draw nothing on Python 3.12 | 29 on 3.12.12 (Unicode 15.0), and the same 29 on 3.14.6 (Unicode 16.0) |
| About 9.8 bits per gap | log2(1 + 29 + 29²) = 9.77 |
| About 39 bits on "hi!" | 4 gaps × 9.77 = 39.07 |
| Guards proven by breaking them | Cap at 1000 or 3: 7 tests red. `NO_INK` removed: 3 red. My reset-on-U+0020 mutant turned 4 red. The commit's figure of 6 matches a reset on `isspace()`, which is plausible and not a finding. |

The 29 are a slight overestimate, which errs on the safe side. The set includes ZWNJ and ZWJ, which can never sit inside a run, because a joiner needs a visible character on each side. It also includes characters that do draw (see N1). Counted exactly, the bound is about 9.57 bits for an inner gap.

## Findings

### SHOULD-FIX E-S1. `text.py::_long_blank_run_at` / `_visible`: combining marks reset the run and are never capped, so "bounded, not closed" is false

`_visible` returns True for every Mn character that is not a named blank. Each mark therefore resets the run, and any number of marks may stack on one base character.

What I measured on 3.12:
- `"a" + "  ́" * 50 + "b"` passes: 50 two-space gaps, each followed by an acute accent sitting on a space.
- `"h" + "្" * 200 + "i"` passes. That is 200 KHMER SIGN COENG, an invisible stacker that has no glyph of its own.
- `"្"` and `"᩠"` (Tai Tham sakot) both have ccc 9, so NFC keeps their order. That makes a 1-bit-per-character channel of invisible stackers.
- 506 marks of ccc 230 pass unchanged after a Latin letter: 8.98 bits per mark.
- `"hi" + 496 of those marks + "!"` passes `player_text(..., max_chars=500)` and carries roughly 4,400 bits. That is more than the 2,390 bits O70 was written to stop.

Failure scenario: a guest hides an instruction for the NPC's LLM in a stack of marks. A human reading the line sees a smudge on one letter, or nothing at all, depending on the font.

`docs/plans/checklists.md`'s residual list names "one variation selector or joiner beside a visible character" and leaves mark stacking out. The same gap was already on `main` before this commit. What this commit adds is the "bounded" claim.

Two possible fixes, both unverified: a cap on non-starters per base character (UAX #15's Stream-Safe Text Format uses 30, and a tighter cap is an owner ruling), or at minimum rewording O70, §5.3 and the checklist to "inkless runs bounded; combining-mark stacking open" with these numbers. Which one to take is the owner's ruling, not mine.

### SHOULD-FIX E-S2. `tests/test_text.py::test_the_null_notehead_is_no_name_either` cannot fail on what it claims to guard

IDNA already refuses U+1D159: `idna.check_label("crate\U0001d159")` raises "Codepoint U+1D159 ... not allowed". With `NO_INK` deleted the test stays green, which is why the commit counts only 3 red cases and not 4.

The commit message says U+1D159 is "refused in names" as an effect of O70, but `NO_INK` adds nothing to name refusal. Failure scenario: a future `NO_INK` entry that IDNA allows (as it allows the hieroglyph blanks) would be judged by this test pattern, and that pattern does not exercise `_blank` in names.

Fix, unverified: either drop the test and the claim, or test `_blank` in names with a code point IDNA allows. One way is a test that puts a temporary IDNA-valid entry in `NO_INK` with monkeypatch.

### NIT E-N1. `text.py::_blank`: characters named BLANK or FILLER that draw are counted as inkless

U+2422 BLANK SYMBOL (␢) and the gap fillers (U+A8F9, U+10AF6, U+1144E, U+11945, U+11C44, U+11C45, U+11F48, all Po) have glyphs. Even so:
- `"␢"` alone is refused with "draws nothing", although the PASSES comment calls it "the BLANK SYMBOL, which draws".
- `"a␢␢␢b"` is refused as a run.
- Three Bhaiksuki gap fillers in a row are refused. That is real manuscript usage, so this is an over-refusal.

The alone-refusal predates this commit. The run refusal is new. This is also why "29 inkless" really means "29 that `_visible` calls inkless". Fix: state it in O70, or match names by word ("BLANK" but not "BLANK SYMBOL"). Unverified.

### NIT E-N2. `tests/test_text.py::test_whatever_passes_is_nfc_within_its_cap_and_holds_no_lone_format_character`: the new run assertion never fires

With `MAX_BLANK_RUN = 1000` the property test stayed green. In 300 examples, 43 inputs held a run of three or more, but each was refused for some other reason (a control or format character), so no passing output ever held a run. The explicit `LONG_RUNS` cases are what guard the cap.

Fix, unverified: a strategy built from visible characters plus the 29 inkless ones, with its reach counted (the memory note "Measure fuzz reach").

### NIT E-N3. Trailing and repeated spaces are refused, not trimmed

`"hi   "` is refused with BAD_TEXT. This follows the ruling, but no shipped caller exists yet. `grep` finds no `player_text` call in `src/` outside its definition and no speech path in `client/`, so whatever the client does with a typed trailing space or an aligned column is still undecided.

Record it for the `speak` step: either the client trims, or the guest gets told why a message bounced.

## Not findings (checked)

- NFC folding of spaces.
- Joiners next to blanks: refused by O61 before the run check.
- U+FE0F counted as drawn after an emoji.
- Refusal order: the category check comes first, then the run check, then the draws-nothing check, all BAD_TEXT.
- The `NO_INK` table shape test.
- Branch coverage of `_long_blank_run_at`: both returns run.
