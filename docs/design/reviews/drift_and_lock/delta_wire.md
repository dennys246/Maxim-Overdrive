# Wire integrity, delta round: `phase1/drift-and-lock` (`38383fc..d1c105b`)

**Reviewer lens:** Wire integrity (`docs/code_review.md`). This round read only the fold's diff. Every experiment ran on
`git archive` copies of `d1c105b`, or with overlays of the installed pymaxim 1.3.4 and of Maxim `1b2e60a9` (#1773) put
first on `PYTHONPATH`. All of those sat in a scratch directory outside the worktree, and none touched the worktree.
One exception, disclosed: a targeted `mypy` on the three changed files may have refreshed the worktree's ignored
`.mypy_cache`.

## Status of the round-1 findings (set by this reader, from the tree)

| Id | Status | Basis |
|---|---|---|
| W1 | **fixed** | `prepush.sh:69` runs `scripts/check_lock.py` as a script. `drift.yml` runs that gate under `MAXIM_OVERDRIVE_UNLOCKED=1`, so it reaches `__main__` and then `entry()`, which calls `main(env=os.environ)`. The new test calls `entry()` under the drift job's environment and again with the event removed. With `entry` mutated to `main(env={})`, it gave 1 failed, 23 passed. A residual sits on the `__main__` line itself (N1 below) |
| W2 | **fixed** | Probe rerun (table below). The gate is red on 1.3.4, red on 1.3.4 with only a version bump, red on #1773 with `allow_pickle=True` restored, and XPASS(strict) on #1773. A narrower residual remains (N2) |
| W3 | **fixed** | With an overlay that removes `similarity/semantic.py` the module gives `1 error during collection`. Removing `models/language/cost_tracker.py` gives the same. Only `importorskip("maxim")` still skips, and `prepush.sh:42` refuses to run without `maxim` |
| W4 | **fixed** | The OD-I1, OD-I3 and OD-I6 rows no longer claim that the gates pass on #1773's source; they cite lesson 41. Lesson 41's new claim holds: a copy of `pymaxim-1.3.4.dist-info` whose line reads `Requires-Dist: rich<16.0,>=13.0.0` gives XPASS(strict) for `test_pymaxim_admits_rich_14`. With #1773's `src` overlaid and the metadata left alone, that gate stays XFAIL, as the lesson now says |
| W5 | **deferred** (status set by the reader; the author's fold says the same) | No PR exists yet (`gh pr list --head phase1/drift-and-lock --state all` is empty). `docs/roadmap.md` still names the branch 6 times. **Trigger:** the PR opens. The PR number must replace the branch name before hand-off |
| W6 | **deferred** | Left by the author under O80. `packaging` is still locked only through pytest (`constraints/py3.12.txt:67`, `packaging==26.3`). The trigger is unchanged: a pytest release that drops `packaging` |

### W2 probe, rerun against the new gate

Each row overlays `maxim/similarity/semantic.py` on the installed package and runs
`test_the_embedding_store_refuses_a_pickled_file` and `test_the_pickle_gate_passes_once_pickle_is_off`:

| Loader | Gate | Stand-in proof |
|---|---|---|
| installed 1.3.4 | XFAIL (red, as intended) | pass |
| 1.3.4 that also accepts version 2, pickle on ("version bump only") | XFAIL | pass |
| #1773 (`1b2e60a9`) | XPASS(strict) (flips; logs "Object arrays cannot be loaded when allow_pickle=False") | pass |
| #1773 with `allow_pickle=True` restored | XFAIL (the round-1 mutant now stays red) | pass |
| #1773 with pickle on, reading its version from a key other than `version` | **XPASS(strict)** | n/a |

The last row is a new mutant, and it is N2.

With the whole of #1773's `src/maxim` overlaid, the module gives XPASS(strict) for OD-I1 and OD-I3 and XFAIL for
OD-I6. That matches lesson 41.

## The drift job's path (GITHUB_ACTIONS=true, MAXIM_OVERDRIVE_UNLOCKED=1)

- `tests/test_check_lock.py` and `tests/test_maxim_fixes_pending.py` together gave 27 passed, 3 xfailed under each
  of `GITHUB_EVENT_NAME=schedule` and `workflow_dispatch`. The default environment gave the same.
- Run as a script, `scripts/check_lock.py` gave `SKIPPED (the drift job)` and exit 0 in the drift job's mode. With
  only `MAXIM_OVERDRIVE_UNLOCKED=1` it gave the refusal and exit 1, and with `--report` it gave `REPORT` and exit 0.
- The new test mutates the process environment only through `monkeypatch`. On the drift job that environment already
  holds all three variables, and `delenv("GITHUB_EVENT_NAME")` still works, so the test is correct in both
  environments.
- A moved Maxim module now turns the drift job red at collection, which files the issue. That is the intended loud
  failure, not a regression.
- `tests/test_isolation.py`: 74 passed. `_Unpickled.__reduce__` refers to `os.mkdir` under `tmp_path`, which is not
  a spawn. `ruff` and `mypy` are clean on the three changed source files.

## New findings

0 BLOCKER, 0 SHOULD-FIX, 3 NIT.

### N1: NIT, `scripts/check_lock.py::__main__` (`sys.exit(entry())`)

**Defect.** The test guards `entry`, but the shipped path enters through the `if __name__ == "__main__":` line, which
is in coverage's `exclude_also` and runs under no test. Replacing that line with `sys.exit(main(env={}))` bypasses
`entry` and recreates W1.

**Failure scenario.** An edit "simplifies" the line to call `main` directly with a literal environment. All tests pass,
and the next scheduled drift run fails `check_lock` in all four legs and files four issues.

**Evidence (verified).** In a `git archive` copy of `d1c105b` with that line mutated, `tests/test_check_lock.py` gave
24 passed. The `entry` mutant, by contrast, is caught.

**Why only a NIT.** The defect has moved from a call with an argument to a call that forwards nothing, which is a much
smaller and more visible edit surface. The round-1 proposal would close it: `runpy.run_path(..., run_name="__main__")`
asserting `SystemExit(0)` and `SystemExit(1)`. That proposal was verified as a probe in round 1. **Trigger:** any
edit to the `__main__` block.

### N2: NIT, `tests/test_maxim_fixes_pending.py::_assert_a_pickled_embedding_file_is_refused`, and lesson 41's "the field every loader reads first"

**Defect.** The pickled value sits only in `version`. The gate therefore proves that pickle is off only for a loader
that reads `version` before it refuses. Suppose a release's loader re-keys its format field (say `format`), keeps
pickle on, and refuses this file as version 0 before reading any pickled field. The gate then flips green with the
mechanism unfixed. Lesson 41 says `version` is "the field every loader reads first", which is true of 1.3.4 and #1773
but not in general.

**Failure scenario.** A 1.3.5 rewrites the loader in that way. OD-I3 XPASSes, the lock-moving session removes the gate
and closes the row, and OD-A12 inherits a live pickle load.

**Evidence (verified).** That mutant, built on #1773 with pickle on and the version read from `format`, gave
XPASS(strict).

**Why only a NIT.** No file the gate writes can cover format keys it doesn't know. Pickling every field would not help
either: the mutant reads no field at all. The residual risk is real only if the format is re-keyed, and the
lock-moving session has to read the release anyway (the OD-I1 row already requires that for the clock sites).
**Proposed text fix (unverified).** Add a clause to the OD-I3 row like OD-I1's: "before the row closes, read the
release's `EmbeddingStore.load` for `allow_pickle`". In lesson 41, change "every loader" to "1.3.4's and #1773's
loaders". **Trigger:** the 1.3.5 lock move.

### N3: NIT, `tests/test_maxim_fixes_pending.py` module docstring

**Defect.** The docstring says "the gate always has it (`check_lock` refuses an environment without it)". On the drift
job `check_lock` is skipped, so `check_lock` is not what guarantees pymaxim there. What does is `prepush.sh:42`
(`import maxim` must succeed), together with the `[maxim]` extra in the install step.

**Failure scenario.** None today; both guarantees hold. The risk is that someone later relies on the stated reason on
the one job where it is false.

**Trigger:** the next edit to the module. Cite `prepush.sh`'s import check instead.

## Summary

All six round-1 Wire findings are closed or tracked: W1 to W4 are fixed as measured, and W5 and W6 are deferred with
triggers. W5 must still be done before hand-off. The fold introduced no BLOCKER or SHOULD-FIX. The three NITs are
residual edges of W1 and W2 plus one docstring reason. Under the stop rule they are the author's call, and none is a
rule waiting for a check.
