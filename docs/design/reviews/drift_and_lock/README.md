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
| A6, E6, W5 | The rows get the PR's number once it exists, before hand-off. Done after the delta round: #73 |

**Left as they are, with their reviewers' triggers** (NITs, the author's call under O80; none is a rule waiting for a
check, so no backlog row):
- A4: `docs/design/inference_placement.md:22` still says the lock is pymaxim 1.3.3. Outside this step's files; trigger:
  that design's next edit, or the 1.3.5 lock move.
- A5: `check_lock.main` still falls back to `sys.argv` and `sys.version_info`. Harmless today; trigger: a caller that
  needs another argv or version without passing it.
- W6: the gates import `packaging`, locked only through pytest. Trigger: a pytest release that drops it.
- D2: the pickle stand-in patches `numpy.load` process-wide. Trigger: tests run in parallel in one process.

The B49–B51 reservations are unused; this step releases them.

## Delta round (the last, under the stop rule)

Reports, verbatim: `delta_executor.md`, `delta_architecture.md`, `delta_wire.md`. They read `38383fc..d1c105b`.
Reviewer-set statuses of round 1: E1–E5, D1, A1–A3, W1–W4 fixed; E6, W5 deferred to the PR's opening (A6 open, the
same item); D2, A4, A5, W6 deferred with the triggers above. No BLOCKER. New: Architecture N1 (SHOULD-FIX), Executor
N1 (SHOULD-FIX, the same defect as Wire N2), and NITs Architecture N2, N3, Executor N2 (the same as Wire N1), Wire N3.

**Folds after the delta round, as the author describes them.** No round reads them (stop rule); each was run as stated.

| Findings | Fold |
|---|---|
| Executor N1, Wire N2 | The OD-I3 gate also records every `allow_pickle` the loader asks `numpy.load` for (each read made with pickle off) and judges both records after `load` returns. Red on 1.3.4 with an early return on a missing key, and on #1773 with pickle on and its version read from another key; still flips on #1773. The stand-in is a store that opens the file with pickle off |
| Architecture N1 | Lesson 41 records OD-I1's three setups again; run: it flips on #1773 and stays red with only `get_totals`'s `or time.time()` put back |
| Architecture N2 | The OD-I7 row points at `sem_stimuli.md` §3.3 and Phase 4's first-body build |
| Architecture N3, Wire N3 | The module docstring names `prepush.sh`'s import check, which holds on the locked gate and the drift job alike |
| Executor N2, Wire N1 | A test loads `check_lock.py` as `__main__` (the module's own `exec_module` loader; `runpy`, as proposed, is a code runner the standards lint refuses, boundaries §5.2) and expects exit 0 in the drift job's mode and 1 without the event. Changing the block to `main(env={})` turns it red |
