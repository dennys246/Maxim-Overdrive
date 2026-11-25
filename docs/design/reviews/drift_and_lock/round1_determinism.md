# Determinism and replay review: `phase1/drift-and-lock` (`1ed9caa..38383fc`)

Lens: Determinism and replay (`docs/code_review.md`). Reviewer: independent reader, read-only, round 1.

## Summary

**0 BLOCKER, 0 SHOULD-FIX, 2 NIT.** The only pin that moved in either lockfile is `pymaxim` 1.3.3 to 1.3.4. A
fresh compile reproduces both files exactly, apart from the hand-written header. pymaxim's core requirements did not
change between the two tags, and its import does not reach the simulation, the replay fixtures or the digest
fixtures. Importing the new test module's Maxim modules changes no process-wide numerical state. The new gates
add no RNG, no order dependence and no writes outside `tmp_path`. The one way they touch the wall clock is
inside Maxim, on purpose (D1). I did not run the replay goldens or digests. The full gate running in the worktree
is the replay check, and this review does not stand in for it.

## What I checked, and how

1. **Did any other pin move? Do both files resolve one stack?**
   - `git diff 1ed9caa..38383fc -- constraints/` shows one line per file, `pymaxim==1.3.3` to `==1.3.4`.
   - `diff constraints/py3.12.txt constraints/py3.14.txt` differs only in the two header lines that name the
     Python version. The stack is the same in both files, `# via` lines included.
   - I copied `pyproject.toml` and `src/simcore/__init__.py` to `<scratchpad>/review_det/proj`. From there I ran
     `uv pip compile pyproject.toml --extra dev --extra maxim --python-version {3.12,3.14} --no-header -o <copy of
     the committed lock>`, which uses the existing pins as preferences. For both Pythons the output equals the
     committed file except the three header lines `--no-header` drops. Nothing else would move on a regeneration
     today.
   - Installed versus lock: no distribution in `.venv` differs from its lock pin. `pip check` reports no broken
     requirements, and `scripts/check_lock.py` prints `PASS (py3.12.txt, 0 difference(s))`.
   - pymaxim 1.3.4's requirements without extras are numpy, scipy, pyyaml, json-repair, httpx, idna, rich and
     filelock, and every locked version satisfies them. In Maxim's clone, `git diff v1.3.3 v1.3.4 --
     pyproject.toml` changes only optional extras (`console` gains pydantic, `tts` gains sounddevice, `comms`
     gains python-multipart). This repo's `[maxim]` extra installs none of them, so the core dependency set is the
     same in both releases.

2. **Can anything in 1.3.3 to 1.3.4 reach the simulation or the replay and digest fixtures?**
   - In `src/`, the only `import maxim` is `src/simcore/adapters/sem/bridge.py`. The import contracts in
     `pyproject.toml` hold it there:
     - `maxim-through-adapters` protects `maxim`, with `simcore.adapters.sem` the only allowed importer.
     - The sealed core bans `maxim`.
     - The game's contract forbids `maxim`.
   - Nothing outside `simcore/adapters/sem` imports the bridge (grep).
   - The fixture generators (`scripts/client_fixtures.py`, `fuel_fixtures.py`, `golden_fuel.py`,
     `wire_fixtures.py`) import no `maxim`. A Maxim change cannot enter a replay or digest fixture through code.
   - The other route is shared numerical libraries, and numpy and scipy did not move (point 1).
   - `src/maxim/embodiment/sem.py` is unchanged between the tags. That is the source of the frozen types the
     bridge and `_compat.py` mirror. `tests/test_sem_compat.py` passes on 1.3.4.
   - The one new import-time code in `maxim/__init__.py` (1.3.4) is `_self_engage_offline()`. It does nothing
     unless `MAXIM_OFFLINE` is set, and nothing in this repo sets it (grep over `*.py`, `*.sh`, `*.yml` and
     `*.toml`).

3. **Do imports leak process-wide state into simulation tests in the same pytest process?**
   - In a probe run with `-I`, I recorded process-wide state before and after importing
     `maxim.models.language.cost_tracker`, `maxim.similarity.semantic` and `maxim.embodiment.sem`. These are the
     modules the new test module imports at collection.
   - Unchanged after the imports: `os.environ` (so BLAS and OpenMP thread variables are untouched), `np.geterr()`,
     `np.get_printoptions()`, the numpy global RNG state, `warnings.filters`, and the root logger's level and
     handlers.
   - No torch, transformers, sentence-transformers, threadpoolctl or numba module was loaded (82 new modules, none
     of those).

4. **Do the new tests add nondeterminism?** (`tests/test_maxim_fixes_pending.py`)
   - RNG: none.
   - Order: the lock has no xdist or randomly plugin, and `addopts` adds none. The module's six tests each use
     their own `tmp_path`, and the two monkeypatches are undone at teardown.
   - Filesystem:
     - `CostTrackerConfig(state_path=tmp_path/...)` is set explicitly, so `resolve_user_state` (the home-directory
       default) is never reached.
     - The persist goes through `atomic_write_text`, which writes its temp file beside `path`, inside `tmp_path`.
     - `np.savez` and `EmbeddingStore.load` both use `tmp_path`.
     - `tests/test_isolation.py` passes (74 tests).
   - Clock: see D1.
   - The static determinism scan, `test_the_simulation_and_tests_have_no_hidden_sources_of_nondeterminism`, passes
     with the new module included (it scans all of `tests/`).
   - Repeat runs: `tests/test_maxim_fixes_pending.py tests/test_check_lock.py tests/test_sem_compat.py` gave
     33 passed and 3 xfailed. A second run of the gate module alone gave exactly 3 `XFAIL` lines.

5. **`check_lock` change (`aee5ca1`).** The skip is now decided only from an `env` mapping, which is required and
   keyword-only. This removes an environment-dependent outcome in the tests (the drift job's variable leaking in),
   so it makes the suite more deterministic across runners, not less. `test_the_check_never_reads_the_process_environment`
   pins that down.

## Findings

### D1 — NIT — `tests/test_maxim_fixes_pending.py::_assert_a_world_time_of_zero_is_a_time`

**Defect.** The test reads no clock itself, as the brief requires. But the expected failure works only because
Maxim reads the wall clock:
- `get_totals(now=0.0)` becomes `time.time()` in 1.3.4, which is exactly the bug being gated.
- On the same path, `record` calls `_maybe_persist`, which reads `time.time()`. Since `now - 0.0 >= 10` holds for
  any real clock, it writes `cost_state.json` into `tmp_path`.
- The constructor reads `time.time()` for the month key.

The outcome is clock-independent for any wall clock past 3,601 s after the epoch: the hourly window then prunes the
t = 1 s cost and the result is 0.0. The xfail is therefore deterministic in practice. Still, this is a test whose
code path reads the wall clock, the static scan cannot see that (the reads are in site-packages), and the rule says
"no wall clock".

**Failure scenario.** None reachable on a real machine. A sandbox or CI image that freezes `time.time()` near the
epoch (some time-faking test harnesses start at 0) would make 1.3.4 honour the window by accident. The gate would
XPASS and turn strict-red while the defect is still there.

**Proposed fix (unverified).** No code change needed. Optionally add one sentence to the docstring saying the
expected failure needs a wall clock later than 3,601 s, so a future reader of the "no wall clock" rule sees that the
dependency is known and bounded.

### D2 — NIT — `tests/test_maxim_fixes_pending.py::test_the_pickle_gate_passes_once_pickle_is_off`

**Defect.** `monkeypatch.setattr(semantic.np, "load", without_pickle)` patches `numpy.load` for the whole process,
not a name local to Maxim's module (`semantic.np` is the `numpy` module object). It is safe today: monkeypatch
restores it at teardown, and the suite runs serially in one thread with no xdist.

**Failure scenario.** If the suite ever runs tests in threads, or a fixture in the same test loads an `.npz` or
`.npy` with pickle on, that load sees the stand-in. One possible victim is a future golden that loads committed
arrays. Not reachable on this branch.

**Proposed fix (unverified).** None needed now. If parallelism arrives, patch through a narrower seam, or note the
global patch in the docstring. Recorded so the trigger ("tests run concurrently") is visible.

## Not reviewed by this lens

- Whether the replay goldens and digests are bit-identical on 1.3.4. The running full gate checks that, and its
  `prepush: PASS <sha>` is the evidence. Point 2 above is why I expect no movement: no Maxim code on any fixture
  path, and an unchanged numerical stack.
- The OD-I5 and OD-I7 roadmap closures, and the gates' fidelity to #1773 (Executor and Wire integrity lenses).
