# Delta round 2, Executor + Trust boundary: phase1/guest-text-rulings (6480408..656eac6)

Scope: the fold commit only. Every probe and mutation ran on a `git archive 656eac6` copy in `<scratchpad>/review/d2/c` on Python 3.12.12, with `pytest -o pythonpath=src`. The scripts are `auto.py` (the class oracle), `count.py` (the bound), `real.py` (real text) and `classes.py` (class sizes). I wrote nothing in the repo.

Baseline: `tests/test_text.py` has 98 passed.

## Verdict

No BLOCKER. The joiner fix is correct, and I found no real text that it now refuses. O73's automaton reproduces independently. Its weights do not: the bound it states is about 2.5 bits low. That is now the fourth understated bound in this series.

## Fold status of delta 1's findings (set by me from the 656eac6 tree)

| Finding | Status | Evidence |
|---|---|---|
| D1-S1 / B-1 (a joiner splits a stack) | **fixed** | `skipped=_joiner`. Mutating it back to never-skip turns 2 tests red: the new TALL_STACKS case and the property test (run). |
| D1-S2 (the 508 bound is exceeded) | **open** | O73 restates the bound and now counts the leading stack and the joiners. Its weights undercount, though (SF-1 below). |
| D1-S3 (cost of the cap) | **fixed** | O73 records the refusal of Tibetan Sanskrit stacks and of Hebrew with meteg plus an accent. I re-measured both: ཀྵྨྲྱཱུཾ is refused at 5, and U+05E9 05BC 05B8 05BD 05C1 05A5 is refused at 5. |
| D1-N1 (the oracle reads module constants) | **fixed** | The oracle now uses the literals 2 and 4. Setting `MAX_MARKS=1000` turns the property test red, and so does setting `MAX_BLANK_RUN=1000` (run). |
| D1-N2 (FE0E/FE0F count toward the stack) | **open** | Nothing in O71, O73, the tests or the checklist mentions it, and the commit message doesn't either. `"❤️"+M3` passes and `"❤️"+M4` is refused at 5 (run). It is harmless, but unrecorded. |
| S-2 (O70 was rewritten) | **fixed** | O70's text is byte-identical to `fa40450`. Only the status changed, to "amended by O71". |
| N-1 (O72's status) | **fixed** | The status is `live`, and the row is now confirmed by the owner. |
| N-2 (the text_tables docstring) | **fixed** | It cites O70, O71 and O72. |
| N-3 (numbers restated in the checklist) | **fixed** | The checklist cites O73. |
| N-4 (probes not on the branch) | **fixed** | The README says the probes were not kept and describes both measurements. |

## The joiner fix

**Real text.** All of these pass:
- Devanagari half-KSSA and eyelash ra;
- Bengali RA+ZWJ+virama+YA (ya-phala, the case where a mark follows a joiner);
- Sinhala śrī and yansaya, Malayalam's old chillu, Kannada, Tamil and Telugu conjuncts with nukta, and Khmer coeng+ZWJ;
- Persian ZWNJ after harakat, and Arabic shadda+fatha+ZWJ;
- pointed Hebrew (4 marks)+ZWJ+letter;
- KA+nukta+udātta+anudātta+ZWJ+virama, which is exactly 4 marks across the joiner;
- the couple, rainbow-flag and eye-in-bubble emoji ZWJ sequences.

In every real joiner use I know of, the character after the joiner is a base (a consonant or an emoji). The one exception is Bengali ya-phala, and there the joiner follows a base. A refusal therefore needs more than 4 marks summed across a joiner, which only constructed text has. One example is Arabic with 3 harakat+ZWJ+2 harakat, which I made up and know of no source for.

**More than four marks on one character.** I found no construct that does it:
- M4+ZWJ+M1 is refused;
- a leading M4+ZWJ+M4 is refused;
- a doubled joiner is refused by O61;
- a selector counts as a mark;
- a spacing mark (Mc) starts a new, visible base, which is correct;
- a space is a base, and O70 limits how many follow each other.

**What counting after NFC means.** O71 counts after NFC, so a precomposed base such as ǖ carries 4 further marks, 6 diacritics on screen. That is as ruled, not new.

## O73's automaton and numbers

**The automaton.** I wrote my own class oracle from the ruling text, not from the code. It checks O61's joiner context, the run of inkless characters and joiners (marks skipped, at most 2) and the stack of marks (joiners skipped, at most 4).

The first version disagreed with `player_text` on 152 strings. The reason is that a lone mark counts as ink (`_visible`), so a message made only of marks passes. This is behaviour from before the fold. O73's README doesn't say so, but its 87,380-string claim needs it.

Once I counted V or M as ink, my oracle agreed with `player_text` on all 87,380 class strings of length 1 to 8. The number matches O73's.

**One representative per class.** This is sound for marks, with one exception. I swapped representatives at random: four per class string over all class strings up to length 6, drawn from 6 letters, 9 marks (with a virama, a Tibetan subjoined vowel, a Hebrew point, an enclosing keycap, Thai, and U+0345), 4 inkless characters and both joiners. That found 0 disagreements.

The exception is the presentation selectors. FE0E and FE0F belong to a fifth class: a mark that is accepted only right after an emoji base. Put in as M they gave 1,185 disagreements. They are not in the 1,698, so leaving them out of the automaton is correct. They add at most 2 marks per emoji base to the weights.

Marks that compose under NFC don't change acceptance, because the automaton runs on the NFC output. They do change the weights (SF-1).

**The numbers.** With O73's own weights (1,698 marks, 19 inkless, 2 joiners) my DP gives "hi!" = 549.0 bits and 137.25 bits per further visible character. That is O73's figure exactly.

## Findings

### SHOULD-FIX SF-1. `decisions/boundaries.md::O73` and `reviews/guest_text_rulings/README.md`: "at most about 2^549" is not an upper bound

O73's weights are wrong in two ways.

**Inkless characters.** On 3.12.12, 21 characters pass between "h" and "i" and draw nothing: 17 Zs, U+2800, U+13441, U+13442 and U+1D159 (`classes.py`). Delta 1 counted 21 too. O73 uses 19.

**Marks.** 1,698 is the count of marks that are NFC-stable after "a". A mark that composes with "a" but not with the real base is a separate reading. On 3.12.12 the NFC-stable counts are:

| Position | Marks |
|---|---|
| after "h" | 1,706 |
| after "i" | 1,700 |
| after "!" | 1,714 |
| after a space | 1,714 |
| after an emoji base | 1,716 |
| at the start or after a joiner | up to 1,729, every mark that passes |

**The corrected bound.** With a sound weight of 1,729 marks and 21 inkless characters, "hi!" comes to **551.4 bits** and each further visible character adds **137.9**. Counting a selector after an emoji base gives 551.5. The bound O73 states is too low by about 2.4 bits. That matches D1-S2's estimate of about 552.

**Failure scenario.** The owner is asked to accept an "at most" that the text exceeds. O73 also says "counted exactly", which holds for the automaton but not for its weights. The error is small. It is still the fourth time in a row that this bound has come out low.

**Fix (verified by `count.py`; the wording is the author's).** State about 552 bits for "hi!" and about 138 per character. In the README, state the weights as 1,729 marks, 21 inkless and 2 joiners, as an upper bound. Also say that a mark alone counts as ink.

### NIT N-1. `boundaries.md::O73`: an author's call with no "awaiting the owner"

O67 and O68 set the precedent: an author's call says "awaiting the owner" in its text. O73 corrects the numbers of an owner ruling and is marked `author, 2026-11-23`, but nothing in it says that it awaits the owner.

Fix: add "awaiting the owner" to the text (unverified).

### NIT N-2. D1-N2 is still unrecorded

The selector-as-mark behaviour needs one clause in O73 (for example, "an emoji's selector is one of its four"), or a recorded rejection.

## Trust checks (no finding)

- The new refusal names a position and a count, never the text.
- It returns BAD_TEXT.
- `_joiner` is pure and linear.
- Dropping `unicodedata.name` from the core's allowlist matches the code: `text.py` no longer calls it.
