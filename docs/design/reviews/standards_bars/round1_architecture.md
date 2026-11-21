# PR 21 (phase1/standards-bars) — Architecture lens

Diff: `git diff origin/main...7debd5c` (CLAUDE.md, docs/code_review.md, docs/standards_backlog.md,
tests/test_cross_tier.py). Read: whole CLAUDE.md, docs/code_review.md, standards_backlog.md, roadmap Phase 3,
docs/plans/checklists.md header, architecture.md Known gaps, every `xfail` in tests/, both commit messages.

Counts: BLOCKER 1, SHOULD-FIX 5, NIT 3.

## BLOCKER

**A1. CLAUDE.md::"Every bar is one of three kinds" — "Verification ... required now, never deferred" contradicts the
tree and three standing rules.** The rule defines verification as agreement with "a closed form, an oracle (FDS) or
another grid". Cross-grid agreement is therefore verification. The tree carries deferred cross-grid misses as strict
red gates plus Known gaps: `tests/test_act_validation.py::test_the_fiercest_allowed_fire_has_the_same_outcome_at_every_rig_on_every_turn`
and `::test_a_strike_breaches_a_thin_wall_the_same_at_every_rig`, and architecture.md's "coarsest rig lags" gap. The
standing rules "Known-broken behaviour gets a strict red gate", "Record known physics gaps ... with numbers" and the
`TEMPORARY(phaseN)` exemption all permit exactly that deferral. The new rule also gives the Known-gap route to
validation alone ("a miss ships as a Known gap").
Failure scenario: step 6's fire lands and its 0.2 m vs 0.1 m cross-tier test misses by a band-gated outcome. One
reader of the rule blocks the merge ("verification is never deferred"). Another applies the red-gate rule and ships an
xfail plus a Known gap. Both cite CLAUDE.md.
Fix (unverified): split the intent. "Verification is never a *future* bar (never deferred to Maxim or to a later
phase without a TEMPORARY marker or a Known gap with numbers and a strict red gate); its band never loosens." Or
state that the existing cross-tier xfails are verification debt, listed under the phase that clears them. Either way
the owner must decide which reading is meant; as worded the rule contradicts the tree.

## SHOULD-FIX

**A2. CLAUDE.md::"A future bar is tracked, never dropped" — the isolation evidence stops at the wrong boundary, so
our bridge's bugs can be deferred to Maxim.** "The world-side half (the stimulus at the receptor) passes, and the miss
is in Maxim's transduction." Between the world's field and Maxim's transduction sits our code:
`simcore/adapters/sem/bridge.py` builds the `SensorReading` values, and we choose how Maxim is driven (cadence,
which modulators, what time cues). "The receptor" can be read as the world's cells.
Failure scenario: an NPC fails to learn that a hot door hurts. The world-side test checks the temperature field at the
door and passes. The bridge clamps or normalizes the reading wrongly, or feeds it on the wrong clock. The author files
it as Maxim's transduction, xfails the gate naming a Maxim issue, and the bug sits in Phase 3 until Maxim "fixes" it.
Two further holes make it worse: (a) with `raises=AssertionError`, a future-bar gate whose own body asserts a
world-side precondition stays xfailed when *that* assertion fails, so the "world-side half passes" must be a separate,
non-xfail test, and the rule doesn't say so; (b) nothing requires showing that Maxim is driven as its briefs say
(the Bio-faithful lens's question), which is a precondition of blaming its transduction.
Fix (unverified): "evidence that isolates the cause: a separate passing test that the values handed to Maxim at the
membrane (the `SensorReading`s the bridge emits, on the clock the bridge uses) carry the stimulus, and a note that
Maxim is driven as its brief says. Without both it is our bug."

**A3. CLAUDE.md::"Every bar is one of three kinds" — scope and the derivation clause don't fit most of the repo's
bars.** "Every bar" with no scope covers determinism (bit-identical: no source uncertainty), trust-boundary limits,
the 95% diff-coverage floor, B5's 20% regression gate and closed-form tolerances. A closed form has no "spread"; its
tolerance comes from the discretization error at the grid spacing (e.g. the crater test's `rel=0.25`).
Failure scenario: a reviewer, holding the rule as written, files a BLOCKER on a new closed-form heat test because its
tolerance isn't "derived from a source's uncertainty", and the author invents a spread for an exact formula; or on a
determinism test that isn't any of the three kinds.
Fix (unverified): scope to "every numeric outcome bar on physics or NPC behaviour"; name the closed-form source as
"the scheme's error estimate at the spacing"; move "written before the measurement, shown able to fail" next to
"Prove a guard by deleting", which it duplicates (it already cites B10).

**A4. CLAUDE.md::"A design document holds the contract" — the partition is ambiguous and routes contract decisions
into a file that deletes itself.** The contract list includes "cadence" and "the interfaces between modules"; the
mechanism list includes "a refresh cap" and "a cost". A refresh cap is a cadence, and a cost is a B5 budget the client
and server both plan against. `docs/plans/checklists.md` is exempt from the word budget (O42), has no design-review
lens, and "each step's section is deleted when that step's PR merges", so the rationale for anything moved there is
lost, while design reviews are kept verbatim precisely "because they explain why the design is what it is".
Failure scenario: a design's server-to-client snapshot refresh cap is moved to the build checklist as "a test to
write". The builder picks 10 Hz; the client's interpolation, written from the design, assumes 20 Hz. No design reader
saw the number, and the checklist section that held it is deleted at merge.
Fix (unverified): the criterion is "does another module depend on this value?" If yes, it is contract and stays in
the design (a numeric value may be "to be measured at step N" there, with the test in the checklist); if no, it may
live only as a checklist test. The checklist item cites the design section it serves.

**A5. CLAUDE.md::"Review finds; it doesn't design" and docs/code_review.md::Design reviews — the stop rule lets open
BLOCKERs leave the design without the owner's overrule or a reviewer's status.** code_review.md keeps "A BLOCKER stops
the build until it is folded or overruled by the owner with a recorded reason", and O25 makes status a reviewer's.
The new text says that when a second paper round finds new blockers in folded text "the round stops and the author
proposes moving the rest into the build steps". It doesn't say who accepts the proposal, that contract blockers are
excluded, or that each moved finding gets a reviewer-set `deferred` with its trigger (the build step).
Failure scenario: round 2 finds a units mismatch between two sections the fold touched (a contract, by A4's own
list). The author invokes the stop rule, moves it to the step's checklist, and the build starts with the contract
blocker open and its fold table showing no status.
Fix (unverified): "only findings about mechanisms move; each is recorded `deferred` by a reviewer with the build step
as trigger; contract blockers still fold or are overruled by the owner; the owner accepts the move."

**A6. CLAUDE.md::"A design document holds the contract" — cites `docs/plans/long_term_features.md`, which is not on
this branch or origin/main.** It exists only on the SEM stimulus design branch (added in 5ff1b7c).
Failure scenario: this PR merges first; CLAUDE.md, which every session reads first, points at a missing file, and a
session that follows it either stalls or recreates a tracker that will collide with the SEM branch's on merge.
Fix (verified by `git ls-tree origin/main` and `git log --all -- docs/plans/long_term_features.md`): merge after the
branch that adds it, or drop the citation until then.

## NIT

**A7. docs/code_review.md::Design reviews vs CLAUDE.md — the same rule in two wordings and two homes.** CLAUDE.md
puts the stop rule under "Review finds"; code_review.md puts it under "The design holds the contract". CLAUDE.md says
"unverified unless they ran it"; code_review.md "verified, with the script it ran". Pick one home and quote it; two
copies drift (the fold tables' history, O25, is this exact failure).

**A8. docs/code_review.md::"A delta round on a design reviews the fold's diff, not the whole document."** Read
literally, it excludes Wire integrity's job (everything outside the hunks that reads a changed contract). A fold that
renames a quantity in §3 leaves §7 using the old name, and no delta reader looks. Add "and, for Wire integrity, every
section that reads a contract the diff changes" (unverified).

**A9. CLAUDE.md::"A future bar" guard — `test_red_gates_are_strict_and_warnings_are_errors` checks only the global
`xfail_strict = true`; a per-marker `strict=False` passes it.** Pre-existing, but the new rule now leans on it for
"(strict)". B34's AST extension should also refuse `strict=False`. Also: "the reason names the upstream issue" assumes
one is filed; Phase 3 items are usually drafts first (B15: "once filed, its Maxim issue"), so say "the Phase 3 item,
and its issue once filed", or authors will file early and skip "Search Maxim before proposing" (B22).

## Checked, no finding

- `raises=` rule (CLAUDE.md, tests/test_cross_tier.py): consistent with the other three strict gates, which already
  pass `raises=AssertionError`; B34 honestly records that the cited test doesn't yet check it.
- Each new rule ends in a Guard and a backlog row (B30-B34, all `open`); no rule is guarded by a document alone.
- Future-bar rule vs "Keep Maxim untouched" and "Push back on Maxim": compatible (all route to Phase 3); "Without that
  evidence it is our bug" is the right default, its gap is A2.
- Word budgets: CLAUDE.md 3,943 to 4,329 words, code_review.md 1,772 to 1,875; neither is under O22.
