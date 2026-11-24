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

## Round 1

Reports, verbatim: `round1_executor.md`, `round1_architecture.md`, `round1_wire.md`, `round1_determinism.md`. Counts:
0 BLOCKER; SHOULD-FIX E1–E3, A1–A3, W1–W4; NIT E4–E6, A4–A6, W5, W6, D1, D2. Several findings name one defect from two
lenses, so they are folded once.

**Folds, as the author describes them.** The delta round reads the fold's diff and sets each status (O25).

| Findings | Fold |
|---|---|
| E1, W1 | `check_lock.entry`, the command line, is the one caller that passes `os.environ`; a test runs it under the drift job's environment and with the event removed. Changing `entry` to `main(env={})` turns that test red |
| E2, W2 | The OD-I3 bar is that nothing was unpickled: a value in `version` whose unpickling makes a directory, asserted absent. Red on 1.3.4, on 1.3.4 with only a version bump and on #1773 with `allow_pickle=True` restored; flips on #1773 |
| E3, W3, A2 | Only pymaxim's absence skips the module; the two submodules are imported plainly, so a moved module is a collection error (run with `semantic.py` renamed) |
| A1, W4, E4 | The OD-I1, OD-I3 and OD-I6 rows cite lesson 41 for the proof instead of restating it. Lesson 41 is rewritten: OD-I6 flips with a `dist-info` overlay carrying #1773's requirement (run), and the method is three setups |
| A3 | The OD-I7 row names `sem_stimuli.md` delta 1's stale "returns 1.0" for the region-modulator build step; the design is outside this step's files |
| E5 | The OD-I1 row says the gate holds one of five sites, and the release is read for all five before the row closes |
| D1 | The OD-I1 helper's docstring states the clock bound (later than 3,601 s after the epoch) |
| A6, E6, W5 | The rows get the PR's number once it exists, before hand-off |

**Left as they are, with their reviewers' triggers** (NITs, the author's call under O80; none is a rule waiting for a
check, so no backlog row):
- A4: `docs/design/inference_placement.md:22` still says the lock is pymaxim 1.3.3. Outside this step's files; trigger:
  that design's next edit, or the 1.3.5 lock move.
- A5: `check_lock.main` still falls back to `sys.argv` and `sys.version_info`. Harmless today; trigger: a caller that
  needs another argv or version without passing it.
- W6: the gates import `packaging`, locked only through pytest. Trigger: a pytest release that drops it.
- D2: the pickle stand-in patches `numpy.load` process-wide. Trigger: tests run in parallel in one process.

The B49–B51 reservations are unused; this step releases them.
