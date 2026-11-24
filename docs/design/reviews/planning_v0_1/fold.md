# Fold of round 1 (`phase1/planning`)

Round 1 read `41036dc..bf2b638` and the five briefs, with three lenses: Architecture (A1–A15), Executor (E1–E19)
and Wire integrity (W1–W15). That makes 2 BLOCKERs, 32 SHOULD-FIXes and 15 NITs. The stop rule is `README.md`'s.
This fold is one commit after `bf2b638`, and the delta round reads only its diff. **The status column is the delta
reviewers' to set (O25); the author's "what changed" column is a claim for them to check against the tree.**

**Owner rulings taken for this fold (2026-11-23), each recorded in `decisions/boundaries.md`:**
- A1/E11: the parallel steps take reserved ids (O79 part 3), and 1a's rulings go in a log of their own, which also
  answers A2.
- A10: NITs stay in the record (O80).
- A11/W7: the briefs are committed at `docs/plans/next_steps/` and own their exit tests (O79 part 4).
- A6: the owner starts the next planning session when step 5 merges (O79 part 5).
- The ids clash: reserving a lesson number in prose tripped `lint_ids`, which my recommendation had not checked. My
  own text now reads "lesson number N". The two round-1 reports mark their four hypothetical spans as `lesson [N]`,
  each with a recorder's note (the owner's ruling).

| Finding | What changed (author) | Status (delta reviewers) |
|---|---|---|
| A1, E11 | O79 part 3 reserves ids per parallel step. Briefs 1a, 2 and 3 name their ids, and the shared rule says to take only those and release unused ones. The roadmap's records bullet no longer says "touch no record family" | |
| A2 | 1a records its rulings in `decisions/records_layout.md` (ids `RL…`), which `check_plan.ID_SOURCES` doesn't read. **Not folded:** A2's second half. Brief 3 may still touch the plan's §3 only within its budget, which has one word of headroom, so a new OD id there means cutting words | |
| A3 | O79 part 2: step 2 owns OD-I1, I3, I5, I6 and I7 until it merges; brief 3 excludes them, and brief 2 names them | |
| A4 | The OD-I10, OD-A4 (#1769), OD-A7 (#1305) and OD-A12 rows are cut to issue, release and lock. "1.3.5 at the earliest" is gone from OD-I1, I3 and I6 | |
| A5, E10 | O79 numbers the steps as the roadmap table does (1a, 2, 3, 4, 5, 6). Row 5a's trigger reads "step 6 of the next steps (O79): after step 5" | |
| A6 | "Planning" is defined as the session the owner starts when step 5 merges (O79 part 5), in the status table's lead and in row 6 | |
| A7 | O79 part 1: no recurring trigger runs while step 4 is open. Briefs 2 and 3 say so | |
| A8 | O78: the upstream lane starts the 1.3.5 repeat when it reconciles at the release. The red job is the second signal. Brief 2's trigger says the same | |
| A9 | B48's trigger is now "the upstream lane's second run", at the next tag or Maxim release | |
| A10 | O80; `README.md`'s stop rule is amended with its ruling; every brief's shared rule follows O80 | |
| A11, W7 | Briefs moved to `docs/plans/next_steps/`, and the `_durable` copies were deleted. The roadmap's table links them and holds no exit-test summary | |
| A12 | Brief 1a: the Known gap owns the open channel and cites O73. Brief 4 adds `checklists.md` step 7's two items to its files and says the same | |
| E1, W4 | Brief 2: no decorator-spelling grep; `strict=True` and `raises=AssertionError` are counted separately, ids are matched as `OD-I1([^0-9]|$)`, and the XFAIL count is 3 | |
| E2, W10 | Brief 2's red proof and exit test run in the job's mode (`GITHUB_ACTIONS=true GITHUB_EVENT_NAME=schedule`). Lesson 40 states the mode, and the local refusal path | |
| E3 | Brief 2: dispatch after a local PASS, with the owner's go-ahead for push and dispatch together, and any issues a red run opens listed for the owner | |
| E4 | Brief 2: a drift run that is red for an outside cause stops the step and goes to the owner, who must accept each failure | |
| E5 | Brief 2's files include `docs/design/reviews/drift_and_lock/` | |
| E7 | Brief 1a: AskUserQuestion calls of at most four questions | |
| E8 | Brief 1a: reinstall the records-layout venv after the merge. The shared rule: reinstall when a merge changes `constraints/` | |
| E9, W3 | Brief 3's exit test checks OD-H6, OD-A20, "perceived-time port", "machinery clock" and M72 are named, and that `setprofile` appears only under a superseded heading. It fails on today's draft (run 2026-11-23) | |
| E12 | O79 part 4 and the shared rule: a session ends at hand-off, and the owner resumes it or starts a fresh one to re-merge `main`. The roadmap agrees | |
| E13, W9 | Brief 5: three `replay MATCHES the recorded end` lines (`metrics.py:244`), and a coverage line carrying two percentages | |
| E14 | Brief 5: a section on more than one session, and the push or branch bundle the mini needs | |
| W1 | Brief 1a's exit test reads the delta reports' statuses and accepts `C1, W1` rows and bold statuses. Checked on samples: `C1`, `W1` and `A-B1` pass, `A-B2` (open) and a missing id fail | |
| W2 | Brief 1a fixes one citation form, `records_layout §10 Qn` or `records_layout added Q6`/`Q7`, which the exit test greps | |
| W5 | Brief 2 takes the dispatched run's id and runs `gh run watch --exit-status` | |
| W6 | O78 and the OD-I5 row: v1.3.4 carries OD-I5's fix (Maxim's v1.3.4 release notes, Security). Brief 2 closes that row too | |
| W8 | Brief 4 counts open PRs other than `phase1/records-build`, and requires 0 | |

**NITs (O80):** recorded with no change: A13, A14, E15, E16, E17, E18, E19, W11, W12, W14 and W15. Changed
anyway by other folds: A15 (E8's reinstall rule), E6 (W6's fold says "citing your PR") and W13 (O79's rewrite
names the roadmap's old trigger instead of the wind-down plan).
