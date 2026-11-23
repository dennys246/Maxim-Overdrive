# Architecture lens: fa40450 (phase1/guest-text-rulings)

Reader: Architecture. I read CLAUDE.md, the whole diff (`git diff origin/main...HEAD`), `text.py`, `text_tables.py`, the
decisions record's header, and grepped the tree (excluding `.venv`, `.worktrees`) for `awaiting the owner`, `2,390`,
`1D159`, `NO_INK`, `_blank`, `player_text`, `visible_name`, "draws nothing" and "hidden bits". I ran small probes with the
worktree's `.venv` and no test suites.

**No BLOCKERs.**

## What holds

- **Word budget (O22/O66):** `boundaries.md` is 10,737 words on origin/main and 10,737 at HEAD (`wc -w`). The §5.3
  addition is paid for in the same row and by the §9.1 cut ("a float by its class" became "floats by class").
  `foundations_plan.md` went from 2,490 to 2,492 words, under the plan's 2,500 cap with 8 words to spare.
  `checklists.md` is exempt (O42) and shrank anyway (12,200 to 12,189).
- **Decision-record convention:** the ruling text of O65, O67 and O68 is untouched. O67 and O68 still say "awaiting the
  owner" in their bodies, which is correct for a record whose rulings are never edited. Only their status columns
  changed (`live; confirmed by O69`, `live; amended by O70`). O69 and O70 are new rows with the owner, the date and an
  owner section. O70 says "Amends O65", and O65's status column matches it.
- **One owner per contract:** O70 owns the rule, and §5.3 (the owner section O70 names) states it in brief and cites it.
  Row 7 in `foundations_plan.md` and the checklist items link to it. The code cites O70 at `MAX_BLANK_RUN` and `NO_INK`.
- **Nothing stale:** "awaiting the owner" is left only in O67's and O68's frozen ruling text and in historical review
  reports. The other hits, `world_model.md:230` and `docs_contracts.md:3`, are unrelated to this change. "2,390" now
  appears only as the old measurement, and "28 of them" is gone from the plans. `npcs_and_sem.md` §6.6 (line 824)
  describes the gate without restating the run rule, so it isn't stale.
- **`_blank` shared with `visible_name` changes no name:** U+1D159 is category `So`, and `idna.check_label` already
  refuses it. A probe gave `InvalidCodepoint` for `crate\U0001d159`, so `visible_name` returned False before this
  commit too. Leaving that out of the record is correct, because nothing changes. This is also the reason for SF-1
  below.
- **Size:** `text.py` is 161 lines. `player_text` and `_long_blank_run_at` are well under the 40-line limit.
- **Selectors:** I checked that U+FE0F (category `Mn`) counts as ink in `_visible`. A probe passed `"Love ❤️  you"` and
  `"❤️‍🔥"`, so a heart followed by two spaces isn't refused. The test's own `_draws` agrees.

## Findings

### SF-1 (SHOULD-FIX) `tests/test_text.py::test_the_null_notehead_is_no_name_either` cannot fail if `NO_INK` is removed

The test claims to guard the `_blank` sharing: that `NO_INK` reaches the name rule. IDNA2008 already refuses U+1D159,
because it is `So` (`idna.check_label('crate\U0001d159')` raised `InvalidCodepoint` in my probe). Delete `NO_INK`, or
drop `_within(NO_INK, ch)` from `_blank`, and this test stays green.

**Failure scenario:** a later refactor splits `_blank` into a guest version and a name version and forgets `NO_INK` on
the name side. This test still passes, and nobody sees the gap until a listed character IDNA allows reaches a name.

**Fix (unverified):** either delete the test, since IDNA owns names and O70 says nothing about names, or keep it with a
comment that IDNA refuses the character on its own, and that it pins the outcome rather than the mechanism. A test
that does guard the mechanism would need a listed character that IDNA allows, and no such character exists today. The
CLAUDE.md rule "Prove a guard by deleting what it guards" applies, and the commit message should say which guard was
proven red. That check is the Executor's.

### N-1 (NIT) `src/simcore/core/text_tables.py` (module docstring): `NO_INK` is a hand-kept list in a module described as generated property tables

The first line still reads "Unicode property tables guest text needs and `unicodedata` lacks", and the body says
"Generated once from Unicode 16.0's ...". The one added sentence ("`NO_INK` alone is kept by hand") is accurate.
Meanwhile the other hand-kept "draws nothing" rule, `_BLANK_WORDS`, lives in `text.py`, so the hand rule is now split
across two modules.

**Failure scenario:** someone regenerating the tables for a Unicode upgrade rewrites the file from the published data
and drops `NO_INK`. No generator script exists in `scripts/` today, so the risk is low. If it happened, the property
test's `within(NO_INK, 0x1D159)` would catch it.

**Fix (unverified):** either move `NO_INK` next to `_BLANK_WORDS` in `text.py`, or fix the docstring's first line, for
example "Unicode tables ...: two generated, one hand-kept".

### N-2 (NIT) `docs/design/boundaries.md` §5.3, the guest-text row: two phrasing problems from the budget cut

- **"no run of three characters without" is hard to parse.** The reader has to supply "ink" from "some ink" before it.
- **"one presentation selector" became "a selector".** That drops O65's "one", although the cell cites O65 for it.
  Both rulings still hold the full rule, so this is precision, not a contract change.

**Fix (unverified):** "some ink, never three inkless in a row", and keep "one selector after an emoji base". This is
roughly word-neutral, and must be re-counted against 10,737.

### N-3 (NIT) `src/simcore/core/text.py::_blank`: a docstring reflow left a short line

The line reads "The name rule's own test, shared. In", and "guest text ..." continues on the next line. Reflow it.

### N-4 (NIT) `src/simcore/core/text.py::MAX_BLANK_RUN`: the comment restates O70's measurement

The comment repeats "about 4.8 bits a character ... about 2,390 bits", so the number now appears in O70, the
checklist, this comment and a test id. Citing O70 would be enough, and when someone re-measures, one place changes.
This is rationale rather than contract, so it is only a NIT.

## Summary

There is no BLOCKER. SF-1 is a guard test that can't fail on the mechanism it is named for. The rest are wording and
placement NITs. The budget, the record convention and the single owner of the rule all hold.
