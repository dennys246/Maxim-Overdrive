# Delta 1, Architecture + Wire integrity: `fa40450..6480408` (phase1/guest-text-rulings)

I read the fold diff, the tree at HEAD and the round-1 reports. Probes ran on 3.12.12; no suites, no edits.

## Round-1 fold status (set from the tree)

| Finding | Status | Evidence |
|---|---|---|
| Arch SF-1 / TW-N2 / E-S2 (name test can't fail) | **fixed** | The monkeypatched `NO_INK` test goes red if `visible_name` drops `_blank` (by reading). |
| Arch N-1 (tables docstring) | **fixed** | First line fixed; line 7 see N-2. |
| Arch N-2 (§5.3 phrasing, "one" selector) | **fixed** | "never three inkless in a row", "one selector". |
| Arch N-3 (reflow) | **fixed** | |
| Arch N-4 (measurement restated in a comment) | **fixed** | The new `MAX_MARKS` comment restates O71's UDHR count, the same pattern, a NIT. |
| TW-S1 (marks stack without limit) | **fixed in part; open** | The reported constructs are refused (`TALL_STACKS`, and the floated-mark case in `LONG_RUNS`), and O70 is corrected. The stated rule of four marks per character can still be stepped around (B-1 below). |
| TW-N1 / E-N1 (U+2422 and gap fillers) | **fixed** | O72. U+2422 alone passes, and the Bhaiksuki triple is in `PASSES`. |
| TW-N3 (index not asserted) | **fixed** | `test_a_long_run_is_named_at_the_character_that_overflows`. The stack tests assert `at 5`. |
| TW-N4 (row 7 lists O70) | **fixed** | O70 is out of row 7, and O69 stays because it confirms the wire rulings O67 and O68. |

## Findings

### B-1 (SHOULD-FIX, contract versus code) `src/simcore/core/text.py::_check_runs`: a joiner resets the mark count, so one character carries 11 or 12 marks, not 4

The mark check is called as `_past_cap_at(..., counted=_mark, skipped=_never)`. ZWNJ and ZWJ are not marks, so each one ends the stack. `_visible` calls a mark visible, so O61's rule that a joiner sits between visible characters lets a joiner stand between two marks. Measured:
`"x" + M4 + ZWJ + M4 + ZWJ + M4 + "b"` (M4 = `"\u0301\u0302\u0303\u0304"`) **passes**. NFC folds the first mark into `á`, which leaves 11 marks on one base. Repeating that segment three times also passes. A third joiner is refused as a blank run, so the trick caps at two joiners per base.

Failure scenario: O71 (owner, "at most four marks follow one character"), the §5.3 row ("nor five marks on one character") and the `player_text` docstring all state a rule the code doesn't enforce. The owner has now ruled twice on a record that overstates the gate.

**What it doesn't break, and this is my own correction of the obvious alarm:** the bit bound. A joiner is an inkless slot in the run, so its trailing marks fit inside O71's "95 per gap" count once 21 inkless characters become 23 (2 × (log2 23 + 43) ≈ 95). The "about 508" figure for "hi!" stands within rounding. The fault is the rule as written, not the channel's size. That is why I rate this SHOULD-FIX and not BLOCKER. A BLOCKER needs the shipped path, and `player_text` still has no caller.

**Fix (verified by probe, not by suite):** have the mark counter skip joiners: `skipped=lambda ch: ch in _JOINERS`, a named predicate. With that change the 11-mark case is refused at index 6, and all of these still pass: `क्‍ष` (KA, virama, ZWJ, SSA), Persian ZWNJ, the Burmese and Hebrew four-stacks, `x` with four marks, and the 👩‍❤️‍👨 ZWJ sequence. `_never` then has no caller and goes away. A `TALL_STACKS` case with a joiner should be added red-first.

The property test can't see this. `_assert_no_long_runs` counts "five marks in a row" on the raw string, which is the same blind spot as the code, so its oracle isn't independent even though `_PIECES` holds ZWJ and marks. Count marks per base in the oracle, skipping joiners.

### S-2 (SHOULD-FIX, record convention) `docs/design/decisions/boundaries.md::O70`: an owner ruling's text was rewritten, and author narrative now sits in an owner row

The record's header says "rulings are never edited; a new ruling is a new row", with no exception for unmerged rows. The edit removed the claim the owner actually ruled on and put in "The author told the owner this bounded the channel; it did not". That is the author speaking inside a row marked `owner, 2026-11-23`. O71 says the same thing ("O70 was ruled on the author's false claim"), so the correction now appears twice.

Failure scenario: a reader can't see what the owner was told when ruling O70, which O71 cites as its reason.

Fix (unverified, owner's call): restore O70 verbatim from `fa40450` with its status `live; amended by O71`, and let O71 carry the correction. If the owner prefers the edit because O70 never merged, mark the inserted sentence as the author's.

### N-1 (NIT) `docs/design/decisions/boundaries.md::O72` status `awaiting the owner`

The precedent is O67 and O68, author calls whose code shipped in the same fold. Their status column read `live`, and "awaiting the owner" lived in the ruling text. No other row in `decisions/` uses this status. O72's rule is already in force in the tree (`NO_INK`, the name test), so a status of "awaiting" misreports the tree. Fix: `live`. The text already says it awaits the owner.

### N-2 (NIT) `src/simcore/core/text_tables.py` module docstring, line 7

"`NO_INK` alone is kept by hand (O70)". O72 now owns how the list is kept, so cite O70 and O72, as the `NO_INK` comment does.

### N-3 (NIT) `docs/plans/checklists.md` step 7, hidden-channels item: O71's numbers restated

43, 95 and 508 now live in O71, in this item and in the commit. Once B-1 is fixed the numbers hold (see above), but any re-measurement has two places to edit. The checklist could cite O71 for the figures and keep only the trigger and what "tighter" needs.

### N-4 (NIT) `docs/design/reviews/guest_text_rulings/round1_{executor,wire_trust}.md`: evidence cited in scratchpad files not on the branch

The reports name `scratchpad/review/*.py` and `probe*.py`. No private details or usernames. But the probes aren't durable and aren't in the tree, so "measured" can't be re-run from the branch. Either say "probes not kept" or commit the few that the numbers depend on.

## Checked, no finding

- **Word budgets:** `boundaries.md` is 10,737 on origin/main and 10,735 at HEAD. `foundations_plan.md` is 2,491, under 2,500. `checklists.md` grew 12,189 → 12,213, which is exempt (O42). The reports are 966, 1,131 and 1,312, all under 3,000.
- **Stale text:** `9.8 bits`, `39 bits`, `_BLANK_WORDS`, `28 of them`, "29" and BLANK/FILLER name matching appear outside the reports only as O72's history and the test's reviewed-set comment.
- **"21 inkless":** confirmed (21 on 3.12.12). Passing marks after `a` come to 1,698 by my count against O71's 1,706. My count leaves out marks that compose under NFC. The bound is an upper bound either way.
- **`text.py` structure:** each function has one job. `_past_cap_at`'s docstring is accurate. `_blank`'s docstring is accurate, since the Mn entries in `NO_INK` (Khitan's filler and the joiners) are refused outright by `_refused_at`. The `player_text` docstring overstates the rule only through B-1. Sizes are well within limits.
- **Shipped path and wire:** `player_text` still has no caller in `src/` (recorded, `phase1/agents`). The refusal is `BAD_TEXT` with an unchanged spelling, and the host replies with code and field only, so the index never reaches the client. The client doesn't judge guest text (O63), so the wire fixtures need nothing.
