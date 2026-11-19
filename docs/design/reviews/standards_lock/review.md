# Review: O32 lock every dependency, O33 Python 3.12+ (uncommitted, phase1/standards)

Lenses: Executor, Architecture, Wire integrity (docs/code_review.md). Counts: 0 BLOCKER, 4 SHOULD-FIX, 5 NIT.

## What was checked

- `uv pip compile` regenerated both lockfiles byte-identical (3.12, 3.14); a linux x86_64 resolve gives the same pins;
  `--only-binary :all:` resolves for manylinux_2_28 x86_64 and macOS arm64 on both Pythons, so CI's
  `pip install -c constraints/py<v>.txt -e '.[dev,maxim]'` has wheels and no markers to trip on (`--universal` would
  add only `colorama ; sys_platform == 'win32'`, irrelevant to the matrix).
- `.venv` (3.14.6): `check_lock.py` PASS; installed but not locked: `pip`, `maxim-overdrive`, `tomli` (stale).
- `pytest -q tests/test_check_lock.py tests/test_tooling_config.py`: 18 passed.
- `lint_standards.py --base main`: PASS, 0 findings; the new rule's Guard cites existing tests.
- No `tomli`, `py310` or `3.10` left in tracked text.

## SHOULD-FIX

**LK-S1 `scripts/check_lock.py::main`: anyone can switch the lock check off, and the gate still prints a clean PASS.**
Scenario: an agent whose venv drifted runs `MAXIM_OVERDRIVE_UNLOCKED=1 scripts/prepush.sh`. check_lock prints
SKIPPED inside a minute of output, and the gate ends with `prepush: PASS <sha>`, which clears a hand-off.
`test_the_drift_job_is_the_only_way_to_skip` checks only that test.yml lacks the string, so its name claims more
than it tests. Fix: honour the variable only when `GITHUB_ACTIONS=true` and `GITHUB_EVENT_NAME` is `schedule` or
`workflow_dispatch`, otherwise fail with "the lock may be skipped only in the drift job". Have prepush.sh add
`(lock check skipped)` to `SKIPPED` so the PASS line says so. Add a test that sets the variable without those
and expects exit 1.

**LK-S2 `scripts/check_lock.py::findings`: the check runs in one direction only, so an empty or partial lock passes.**
It walks the lock's pins, so `pins == {}` is a PASS. Confirmed: an empty `constraints/py3.14.txt` gives exit 0.
The same applies to a lock regenerated without `--extra maxim`, and to a dependency added to pyproject.toml
without regenerating: the new package installs unpinned and nobody sees it. Extra installed distributions are
also invisible. A stale `tomli` sits in the local venv today. An auto-loading pytest plugin (`pytest-randomly`,
`pytest-xdist`) installed by hand would change test behaviour and the check would still pass.
`test_every_ci_python_has_a_lockfile_and_ci_installs_from_it` checks only that the file exists. Fix: (a) fail when
`pins` is empty; (b) compare `metadata.distributions()` the other way as well, allowing only `pip` and the
project; (c) a test that every requirement name in `[project].dependencies` and the `dev`/`maxim` extras appears
in each lockfile.

**LK-S3 `tests/` (no test): nothing fails if prepush.sh stops calling check_lock.** The Guard cites the script and
two workflow tests. Deleting the `step "dependencies match the lockfile"` lines from `scripts/prepush.sh` leaves
every test green, and the shipped path loses the mechanism. Fix: a test in `tests/test_prepush.py` or
`tests/test_check_lock.py` asserting that prepush.sh runs `scripts/check_lock.py`, and runs it before the first
`ruff` step. A text check on the script is enough.

**LK-S4 `.github/workflows/drift.yml`: a red run doesn't say what drifted, and the lockfile header says it does.**
The header of `constraints/py3.1x.txt` says the drift job "shows what a regeneration would change". The job sets
`MAXIM_OVERDRIVE_UNLOCKED`, so check_lock prints SKIPPED and nothing lists the versions. Someone triaging a red
Monday run cannot tell a pymaxim type change from a numpy golden shift without reproducing it. Also, scheduled
runs only notify the account that last changed the cron line (repo is private, so no 60-day auto-disable). That
is the owner only if the owner's account pushes the file to main. Fix: add a step before Gate that always runs and
prints the difference against the lock, for example check_lock in a report-only mode, or `pip freeze` diffed
against the lock. In CLAUDE.md's rule, say who is notified, or open an issue on failure
(`gh issue create` in an `if: failure()` step).

## NIT

**LK-N1 `scripts/check_lock.py::findings`: versions are compared as strings.** `1.0` and `1.0.0` would be reported
as different, though pip treats them as equal. Use `packaging.version.Version`: packaging is already locked and
reachable through pytest.

**LK-N2 `scripts/check_lock.py::PIN`: environment markers are dropped, not evaluated.** A future
`foo==1 ; sys_platform == 'win32'` pin would show as "not installed" on Linux and macOS. No lock has markers
today. Evaluate them with `packaging.markers.Marker`, or say in the docstring that the locks are platform-resolved
and must have none. The test name "skip ... markers" reads as "evaluate".

**LK-N3 `scripts/check_lock.py::main`: the FAIL hint leaves out the shared-venv warning.** Its
`pip install -c ... -e` hint is printed even when `$PY` is a venv shared with another worktree (CLAUDE.md
suggests `PYTHON=<venv>/bin/python`). In that case the install re-points the editable install for every
session, which prepush.sh's precondition warns against. Either move the hint into prepush.sh, which already
tells the two cases apart, or print both variants.

**LK-N4 `scripts/prepush.sh` precondition hint:** `constraints/py<major.minor>.txt` is a placeholder. The script has
`$PY`, so it can print the real path with
`$("$PY" -c 'import sys;print(f"{sys.version_info[0]}.{sys.version_info[1]}")')`.

**LK-N5 `CLAUDE.md`/`README.md`: the commands use 3.12 while the working venv is 3.14.6.** That is fine, but
following CLAUDE.md in a fresh worktree gives a different interpreter from the one the existing `.venv` and its
goldens use. Say which Python goldens are recorded on ("the locked stack" does not include the interpreter), or
record them on both.
