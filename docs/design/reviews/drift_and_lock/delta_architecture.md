# Architecture lens, delta round: `phase1/drift-and-lock`, `38383fc..d1c105b`

| Finding | Status (reviewer-set, O25) | Read from the tree |
|---|---|---|
| A1 | fixed | The OD-I6 row no longer claims a run "on #1773's source". It cites lesson 41, and lesson 41 now records a real proof: a `dist-info` overlay carrying #1773's `Requires-Dist`. The OD-I3 row also cites the lesson, and the lesson covers OD-I3. The same citation in the OD-I1 row is now false (N1). |
| A2 | fixed | Only `pytest.importorskip("maxim")` remains; the two submodules go through `importlib.import_module`. I ran a copy of the module with `semantic` renamed to `semantic_moved`: `1 error during collection`, interrupted, not a skip. |
| A3 | fixed | The OD-I7 row now says the design still describes the silent 1.0 and names `DamageRefused`. The design itself is untouched, as the brief requires. Its pointer is imprecise (N2). |
| A4 | deferred | Reason: `inference_placement.md` is outside the brief's files. Trigger: that design's next edit, or the 1.3.5 lock move (README). Line 22 still says "The locked release is pymaxim 1.3.3". |
| A5 | deferred | Reason: harmless today, every test passes `argv`. Trigger: a caller that needs another argv or version (README). `check_lock.main` still falls back to `sys.argv` and `sys.version_info`. |
| A6 | open | No PR exists yet (`gh pr list --head phase1/drift-and-lock` returns `[]`). The rows still cite the branch. The README promises `#<n>` before hand-off, and that edit is not in the tree. |

**New findings:** 0 BLOCKER, 1 SHOULD-FIX, 2 NIT.

## What I ran

- I read `git diff 38383fc..d1c105b` in full, the round-1 reports, the README fold table and stop rule, and the brief.
- **Scope.** The diff touches:
  - the review directory;
  - lesson 41 only;
  - the OD-I1, OD-I3, OD-I6 and OD-I7 rows only;
  - `scripts/check_lock.py`, where the root fix is;
  - `tests/test_check_lock.py`;
  - the gate module.

  All of it is on the brief's list. No workflow, conftest or design edits.
- **Word budgets.** Review reports run 1,215 to 1,760 words each, and the README is 595, all under 3,000. Lesson 41 is in the lessons log, not a design document, so the no-growth rule doesn't apply.
- **Targeted tests.** `pytest -rx tests/test_maxim_fixes_pending.py tests/test_check_lock.py`: 27 passed, 3 xfailed. Each XFAIL reason names its OD id and Maxim issue.
- **The OD-I3 gate's logic, checked against both loaders.**
  - Installed 1.3.4: `semantic.py:662` calls `np.load(path, allow_pickle=True)`, and `:664` reads `version` first. The pickled `version` therefore runs `os.mkdir` and the marker appears, so the gate is red.
  - #1773 (`git show 1b2e60a9:src/maxim/similarity/semantic.py`): `:677` loads with `allow_pickle=False` and `:678` reads `version`. That raises before anything is unpickled, the broad `except` at `:708` returns 0, and no marker appears, so the gate flips.
  - The lesson says #1773 refuses version 1 by its number before reading a pickled field (`:679-689`). That is correct, so the old gate did track the format, not the pickle.
  - I did not re-run the overlay setups myself.
- **The OD-I1 claim.** I grepped lesson 41 for what it says about OD-I1, and found it at line 575 only.

## New findings

### N1. SHOULD-FIX: `docs/roadmap.md::OD-I1` cites lesson 41 for a flip proof that lesson 41 no longer contains

**Defect.** The fold replaced each row's "passes on #1773's source" with "lesson 41 records how it was proved to flip". That is true for OD-I3 and OD-I6, not for OD-I1:

- The rewritten lesson names OD-I1 once ("holds OD-I1, OD-I3 and OD-I6 red on pymaxim 1.3.4").
- It describes flips only for the OD-I3 gate (both versions) and the OD-I6 overlay.
- The old lesson's evidence for OD-I1 ("OD-I1 and OD-I3 went `XPASS(strict)`" on #1773's `src/maxim`) was deleted in the rewrite.
- The only remaining record of OD-I1 flipping is the commit message ("all three gates XPASS(strict)").
- The lesson's own consequence asks for three setups per gate. For OD-I1 it shows none, including the third: #1773 with only `or time.time()` restored at `get_totals`.

So the row points to a source that doesn't hold the fact, and the fact itself now lives only in git history. This is the kind of claim A1 was raised against, moved one row up.

**Failure scenario.** At 1.3.5 the repeat session reads the OD-I1 row, opens lesson 41 to check that the gate was proved to flip, and finds nothing about OD-I1. It either:

- trusts the gate unproved. This matters because the gate holds one of five sites (E5), and a release that fixes `get_totals` but not the salience sites flips it anyway; or
- re-derives the proof from scratch.

Under the lesson's own rule, a gate whose flip isn't recorded is "a guess about upstream behaviour".

**Fix (unverified).** Restore one sentence to lesson 41: OD-I1's gate went `XPASS(strict)` with #1773's source overlaid, plus the third setup if it was run. Or reword the OD-I1 row to say only what is recorded. This is a text fold. Under the README's stop rule, no further round follows.

### N2. NIT: `docs/roadmap.md::OD-I7` points at "`sem_stimuli.md` delta 1" for text that lives in §3.3

**Defect.** The new clause says "`sem_stimuli.md` delta 1 still describes the silent 1.0". "Delta 1" is the design's review round (`docs/design/reviews/sem_stimuli/delta1/`), where SF-2 came from, not a section of the design. The stale sentence is at `sem_stimuli.md:134`, §3.3 "Phase 4's first body".

There is also no "region-modulator build step" in the roadmap or the plans: `grep -rln region.modulator docs` finds only review files. The closest addressee is the sem_stimuli checklist's first-body item, which the final Bio-faithful review cites for SF-2.

**Scenario.** The Phase 4 first-body session greps the design for "delta 1" and finds nothing. Grepping for "returns 1.0" does find it, which is why this is a NIT.

**Fix (unverified).** "`sem_stimuli.md` §3.3 still describes the silent 1.0; Phase 4's first-body build reads it against `DamageRefused`."

### N3. NIT: `tests/test_maxim_fixes_pending.py` (module docstring) gives the wrong reason pymaxim is always present

**Defect.** "The gate always has it (`check_lock` refuses an environment without it)". In the drift job, the one run where these gates are expected to flip, `check_lock` is skipped (`MAXIM_OVERDRIVE_UNLOCKED: "1"`). What guarantees pymaxim there is the job's `pip install --upgrade -e '.[dev,maxim]'` (`drift.yml:35`). The behaviour is right. Only the stated reason is wrong for that job.

**Scenario.** A later edit drops `maxim` from the drift job's extras, believing `check_lock` guards it. The module then skips quietly in exactly the run that should flip the gates.

**Fix (unverified).** Name both guarantees: "`check_lock` on the locked gate; the drift job installs the `maxim` extra".

## Facts in two places

- The proofs are now stated in the README fold table, in lesson 41 and in the commit message. The fold table is a review record, which is where the charter puts such tables, so this is acceptable. The single source the rows cite is lesson 41, and N1 is the gap there.
- The clock bound lives only in the docstring.
- The OD-I1 row's "one of five sites" is new and stated once.

## Stop-rule note

N1 is a SHOULD-FIX on text, not a BLOCKER. Under the README it folds without another round. A6 remains open until the PR number is in the rows.
