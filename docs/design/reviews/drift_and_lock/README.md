# Review of step 2 after `v0.1.0` (`phase1/drift-and-lock`)

**Scope.** The branch's diff against `origin/main` at `1ed9caa`: `scripts/check_lock.py`, `tests/test_check_lock.py`,
both lockfiles, `tests/test_maxim_fixes_pending.py`, the OD-I1, OD-I3, OD-I5, OD-I6 and OD-I7 rows of
`docs/roadmap.md`, and lesson 41. The brief is `docs/plans/next_steps/2_drift_and_lock.md`.

**Lenses:** Executor, Architecture, Wire integrity, and Determinism and replay (the lock moves the stack the replay
goldens are recorded on), per `docs/code_review.md`. One round, run in parallel by independent readers.

**The stop rule** (written before the round, as the brief requires):
- A BLOCKER or a SHOULD-FIX is folded.
- If a fold changes text or code, one delta round reads only that fold's diff, and no round follows it. A BLOCKER the
  delta round finds goes to the owner for a ruling, not to another round.
- A NIT is the author's call (O80): fixed or not, it is recorded with its reviewer's trigger, and becomes a backlog row
  only if it is a rule waiting for a check.
- The reviewers, not the author, set each finding's status (O25). Their reports are recorded verbatim beside this
  file.
