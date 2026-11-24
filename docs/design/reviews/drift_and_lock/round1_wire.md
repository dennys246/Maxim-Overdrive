# Wire integrity review: `phase1/drift-and-lock` (`1ed9caa..38383fc`)

**Reviewer lens:** Wire integrity (`docs/code_review.md`). Read-only; experiments in `<scratchpad>/review_wire/`, on a
`git archive` copy of `38383fc` and a `git archive` of Maxim `1b2e60a9` (#1773), never in the worktree.

## Summary

0 BLOCKER, 4 SHOULD-FIX, 2 NIT.

The root fix for the drift job is wired correctly on every shipped path, as far as it goes:

- **Gate** (`scripts/prepush.sh:69`) runs `"$PY" scripts/check_lock.py` as a script, so it reaches
  `main(env=os.environ)`.
- **CI** (`test.yml`) installs with `-c constraints/py<ver>.txt`, never sets `MAXIM_OVERDRIVE_UNLOCKED`, and runs the
  same gate, so `env` holds no skip and the full check runs. `check_lock` passes in the worktree venv (0 differences),
  `pip check` is clean, and the two lockfiles are identical below their headers, with only `pymaxim` moving
  (1.3.3 to 1.3.4).
- **Drift job** (`drift.yml`) sets `MAXIM_OVERDRIVE_UNLOCKED=1` for the whole job. It runs `check_lock.py --report`,
  which returns before the skip logic, then the gate. In the gate, the script's `os.environ` holds
  `GITHUB_ACTIONS=true` and `GITHUB_EVENT_NAME` of `schedule` or `workflow_dispatch`, so the check skips. The tests
  now pass `env` explicitly, so they no longer inherit the skip.

I reproduced the job's mode locally with `GITHUB_ACTIONS=true GITHUB_EVENT_NAME=schedule|workflow_dispatch
MAXIM_OVERDRIVE_UNLOCKED=1`. `tests/test_check_lock.py` passed 23 of 23, and the new module gave 3 passed and 3
xfailed.

**Will the drift job go green on 1.3.4?** Expected yes, though only a dispatch confirms it. In run 45238153656 every
leg failed only on the two `test_check_lock` tests, and the coverage miss was entirely `scripts/check_lock.py`
(`Missing: 36, 79-96`, 16 statements, the non-skip half of `main`). Both are fixed in the job's mode. The newest
pymaxim on PyPI and GitHub is still 1.3.4 (`pip index versions pymaxim`, `gh release list`), so the three new gates
stay XFAIL there. Their bars don't depend on numpy, ruff or mypy versions. I did not re-measure `check_lock.py`'s
drift-mode coverage independently: coverage reported "no data" on my archived copy, which I didn't chase. On 1.3.5,
OD-I1 and OD-I3 turn XPASS(strict) and the job goes red, as the brief intends.

The defects are that the shipped skip path lost its only test (W1), and that the gates can go green or vanish
without the guarded mechanism being fixed (W2, W3). One roadmap claim is false as measured (W4).

## Findings

### W1: SHOULD-FIX, `scripts/check_lock.py::__main__` (entry point) / `tests/test_check_lock.py::test_only_the_scheduled_drift_job_may_skip`

**Defect.** Before this branch, `test_only_the_scheduled_drift_job_may_skip` set the process environment and called
`main()`, so it exercised the same path the gate uses: process environment, then the skip decision. Now every test
passes `env` directly, and the only code that joins `os.environ` to the skip, `sys.exit(main(env=os.environ))`, runs
under no test. It is also excluded from coverage (`exclude_also` has `if __name__ == .__main__.:`). The drift job's
skip on the shipped path now has no guard here.

**Failure scenario.** A later edit writes `main(env={})` there, or `main(env=dict(SOME_FILTERED_VIEW))`, or drops the
skip variable. CI stays green, the local gate stays green, and every test in `test_check_lock.py` stays green. The
next scheduled drift run fails at `check_lock` in all four legs, before any test runs, and files four public issues.
That is the same class of bug this branch fixes, moved one line.

**Evidence (verified).** In a `git archive` copy of `38383fc` I changed the entry point to `main(env={})`. Then
`GITHUB_ACTIONS=true GITHUB_EVENT_NAME=schedule MAXIM_OVERDRIVE_UNLOCKED=1 pytest tests/test_check_lock.py
tests/test_prepush.py` gave 33 passed. The mutant survives.

**Proposed fix (verified as a probe, not as a committed test).** Add one test that runs the script as `__main__` in
process with `runpy.run_path(<scripts/check_lock.py>, run_name="__main__")` under a monkeypatched environment. It
asserts `SystemExit(0)` in the drift job's mode and `SystemExit(1)` with only `MAXIM_OVERDRIVE_UNLOCKED=1`. It
spawns no process, so `ALLOWED_SPAWNS` is untouched. My probe script (`<scratchpad>/review_wire/entry_probe.py`)
gives exit 0 and exit 1 on the real script. On the `env={}` mutant it gives 1 where 0 was expected, so the test would
go red.

### W2: SHOULD-FIX, `tests/test_maxim_fixes_pending.py::_assert_a_pickled_embedding_file_is_refused`

**Defect.** At #1773 the gate flips because the loader refuses version 1 by number, before it reads any pickled
array, not because pickle is off. The fixed `EmbeddingStore.load` (Maxim `1b2e60a9`) opens the file with
`allow_pickle=False`, and then returns 0 on `version == 1` ("the old pickle-based format") without touching
`memory_ids`. A loader that renumbered the format but kept `allow_pickle=True` would pass this gate the same way. So
the gate holds the format number, not OD-I3's mechanism. "Prove a guard by deleting what it guards" fails: delete the
pickle fix and the gate stays green.

**Failure scenario.** A 1.3.5 that kept version 2 but reverted `allow_pickle` (a refactor, or a partial backport)
flips the gate. The fixing session removes it and closes OD-I3 as fixed. `AgentHome` (OD-A12) then makes a pickle
load reachable from saves.

**Evidence (verified).** I ran `<scratchpad>/review_wire/od_i3_probe.py`, which writes a version 1 and a version 2
file, each with object arrays:

| Loader | v1 loaded | v2 loaded |
|---|---|---|
| installed 1.3.4 | 1 | 0 |
| #1773's source | 0 | 0 |
| #1773's source with `allow_pickle=True` restored | 0 (gate passes) | 1 |

**Proposed fix (verified with the probe above).** Make the helper assert both: a version 1 file is refused, and a
version 2 file of object arrays (the fix's `_EMBEDDING_FILE_VERSION`) is refused. On 1.3.4 the version 1 file loads
1 entry, so the gate is red. On #1773 both are 0, so it passes. On the pickle-on mutant the version 2 file loads 1,
so it stays red. Its stand-in test needs the same two files.

### W3: SHOULD-FIX, `tests/test_maxim_fixes_pending.py` (module level, `pytest.importorskip` for `cost_tracker` and `semantic`)

**Defect.** Both Maxim modules are imported with module-level `importorskip`. If a pymaxim release moves or renames
either module, all six tests in the file are skipped and the gate prints no failure. That includes the three strict
red gates, their three proofs, and the OD-I6 gate, which needs neither module. CLAUDE.md forbids `skip` for
known-broken behaviour for this reason. The gate requires pymaxim anyway (`prepush.sh:42` refuses to run without
`import maxim`), so the skip guards against nothing on the shipped path.

**Failure scenario.** The drift job installs a pymaxim that moves `maxim.similarity.semantic`. The gates vanish, the
job goes green, and roadmap rows OD-I1, OD-I3 and OD-I6 still say a strict red gate holds them. This is the drift
job, the path that exists to show these gates flipping.

**Evidence (verified).** I put a shadow copy of the installed `maxim` on `PYTHONPATH` with
`similarity/semantic.py` removed. The module gave `1 skipped`. With plain imports
(`from maxim.models.language import cost_tracker`, `from maxim.similarity import semantic`), the same shadow gave
`1 error`, and the real 1.3.4 gave `3 passed, 3 xfailed`.

**Proposed fix (verified as above).** Use plain imports. Optionally, move the OD-I6 gate so it doesn't depend on
those imports.

### W4: SHOULD-FIX, `docs/roadmap.md` OD-I6 row

**Defect.** The row says the gate "fails on 1.3.4 and passes on #1773's source". It does not pass there. The gate
reads installed distribution metadata, which `PYTHONPATH` cannot replace. The commit message says so itself ("OD-I6
reads installed metadata, so only its stand-in … can show it"). A claim about what works must be measured on the
shipped path.

**Evidence (verified).** With Maxim `1b2e60a9`'s `src` first on `PYTHONPATH`, the module gives XPASS(strict) for
OD-I1 and OD-I3, and **XFAIL** for `test_pymaxim_admits_rich_14`. #1773's `pyproject.toml` does declare
`rich>=13.0.0,<16.0`, so the stand-in string is accurate.

**Proposed fix (unverified, text only).** For OD-I6, write "fails on 1.3.4. Its helper passes on #1773's declared
requirement (`rich>=13.0.0,<16.0`), a stand-in, because installed metadata can't be swapped from source".

### W5: NIT, `docs/roadmap.md` OD-I1, OD-I3, OD-I5, OD-I6 and OD-I7 rows

**Defect.** The brief says to close OD-I5 and OD-I7 "citing your PR". The rows cite the branch name
`phase1/drift-and-lock`. A branch is deleted after a merge, and a PR number stays resolvable.

**Trigger.** The PR is opened. Replace the branch with `#<n>` before hand-off.

### W6: NIT, `tests/test_maxim_fixes_pending.py` (`from packaging.requirements import Requirement`)

**Defect.** `packaging` is imported directly, but no extra in `pyproject.toml` declares it. It is locked only as a
transitive dependency ("via pytest"). Today it always resolves.

**Trigger.** A pytest release drops its `packaging` dependency. If that happens, the drift job's install would lack
the package, and the OD-I6 gate module would fail at collection. Declare `packaging` in `dev` if the owner wants
direct imports declared, as `idna` was for `src/`.

## Checked, no finding

- **`check_lock.main`'s callers.** The only callers in the repo are the script entry and `tests/test_check_lock.py`,
  and every test call passes `env`. `test_the_environment_is_a_required_keyword` holds the `TypeError`. Mypy
  strictness is unaffected: `Mapping[str, str]` accepts `os.environ`.
- **`--report` in the drift job.** It short-circuits before the skip, which is unchanged from main and correct.
  Checking the report runs before the skip variable matters is the gate's job.
- **The lockfiles against CI.** Both lockfiles are identical below their headers. No new pymaxim 1.3.4 requirement is
  missing from the lock (`check_lock` PASS, `pip check` clean), and the `rich` cap still holds `import-linter==2.6`.
- **OD-I1's gate.** The sites at #1773 read `now if now is not None else time.time()`, so the gate flips on the
  mechanism itself. The test's `CostTracker` writes only to `tmp_path` (the `state_path` is set explicitly). The
  stand-in models the fix as a clock that reads zero rather than an `is None` test. That is weaker, but the
  real-source XPASS covers it.
- **The module's collection in drift.** The default `tests/` collection picks it up, and `raises=AssertionError` is
  narrow. A missing `rich` requirement would raise `StopIteration` and fail loudly, which is correct.
