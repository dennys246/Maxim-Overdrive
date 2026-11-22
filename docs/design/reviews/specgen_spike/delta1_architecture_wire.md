# Spec generator spike, delta 1: Architecture, Wire integrity and Bio-faithful (2026-11-22)

This is a condensed record of the reviewer's hand-back message. The reviewer set each status, read from the tree.

## Fold status of round 1

| Finding | Status | Evidence |
|---|---|---|
| B1 provenance terms | fixed | They are gone from O57, lesson 32, the plan and the tracker. `sources.md` explains them only, checked against `sem.py:458-461` |
| B2 D32 pointer | fixed | D32 cites `gameplay.md`, "Drop as scope creep" (lines 217 and 225) |
| S1 §5.3 cell | fixed | It reads "world-side generator (O57)", and the word count is unchanged at 10,747 |
| S2 trust and replay | fixed, but opens SF-1 | |
| S3 citations | fixed | `README.md:28`, `experiments/README.md:7`, and `substrate_plan.md:766` as archived history, all verified |
| S4 the Maxim question | deferred | No ask exists yet. Trigger: Phase 6's design starts (O57) |
| S5 index rows | fixed | `check_plan` passes |
| S6 O56's owner | fixed | "—" |
| S7 §6 precedence | fixed | |
| N1 to N4 | fixed | |
| N5 tracker leans to design | rejected | A list of what is open is the tracker's job |
| N6 lesson date | open | |

## New defects

- **BLOCKER, `src/simcore/core/imagination.py` docstring.**
  - Line 3 is 130 characters, so ruff E501 fails the gate (verified).
  - `decisions/boundaries.md` resolves from nowhere in `src/`, and it points at a record, not the owner.
  - Fix: cite `docs/design/boundaries.md` §5.3 and rewrap.
- **SHOULD-FIX SF-1, O57 against `boundaries.md:117`, `:448` and §5.3: two owners for the `imagine` payload.**
  - `boundaries.md` already fixes that the intent carries a typed spec, and "never only the request" lets request
    text enter the log against `:444`.
  - Failure scenario: step 5a reads O57 as reopening the payload.
  - Fix: O57 says the contract stands, and a change would amend `boundaries.md`.
- **SHOULD-FIX SF-2, `architecture.md`'s two new Known gaps have no red gate and no named fixing step.** The
  breach-axis flip is a verification miss.
- **NIT-1:** `architecture.md` grew by about 200 words, in Known gaps, which CLAUDE.md requires. Owner to confirm in
  the hand-off.
- **NIT-2:** the Phase 6 trigger for the Maxim questions lives only in a decision row. Add it to roadmap Phase 6 or
  the tracker.
- **NIT-3:** O57 doesn't say whether the generator's calls go through the inference gateway.
- **NIT-4:** `foundations_plan.md` is at exactly 2,500 words.
