# Delta round 1: Executor and Determinism lenses, phase1/sim-shell at c9c0370

Reviewer: independent, read-only. Diff read: `git diff 90dc9b2..c9c0370` (simulation.py, intents.py, test_simulation.py,
the marker wording in world.py/applier.py/imagination.py, roadmap, lint_gates, _imports). Plants ran in a `git archive`
copy at `.worktrees/_durable/sim_shell_review/delta1_plant/` (`plant.py` there; `simcore.__file__` confirmed to resolve
to the copy). The worktree was not edited.

**Counts: 0 BLOCKER, 1 SHOULD-FIX, 3 NIT (new). Round 1: 13 fixed, 1 rejected, 1 deferred, 1 split fixed/deferred.**

## Status of round-1 findings (set by this reviewer, from the tree)

| Lens | Id | Status | Evidence |
|---|---|---|---|
| Exec | S1 | **fixed**, verified | plants A and C each fail 3 tests (below) |
| Exec | S2 | **fixed**, verified | `step` reads `tuple(records)`; plant E fails `test_a_generator_batch_loses_no_record` |
| Exec | S3 | **fixed**, verified | `TEMPORARY(phase1/sim-clock)` on `Simulation.__init__`, roadmap bullet names `simulation.py`; `lint_standards.py` PASS |
| Exec | N1 | **fixed**, verified | `_check_batch` refuses `apply_us >= tick_us` (plant F fails 1); `actor_id` is an int; `target` passes `identity_key` |
| Exec | N2 | **fixed**, verified | `_directly` uses literal `STEP_S`; plant I (`physics_seconds + 1e-6`) now fails 6, including all three bit-identity tests |
| Exec | N3 | **fixed** | module docstring lists the three departures; `SimConfig` names `substep_refine` |
| Exec | N4 | **rejected** (no action needed) | an observation, not a defect; the docstring says the shell has no shipped caller yet |
| Exec | N5 | **fixed** | the three markers and the roadmap bullet say "until `Simulation.step` owns the window" and name PR 2 / PR 4 |
| Det | B1 | **fixed**, verified | `SCHEDULE` (ticks 1, 5, 30) at 0.2 and 0.1 m plus two targeted tests; plants A, B, C each fail 3 |
| Det | S1 | **fixed**, verified | as Exec S2 |
| Det | S2 | (a) and in-batch (b) **fixed**, verified; cross-tick (b) **deferred** | plants F and G each fail their parametrized case. Deferral accepted: uniqueness across ticks needs the log's history, which is PR 4's reader. Trigger: PR 4. But see new S1: it is recorded only in fold.md |
| Det | N1 | **fixed** | docstring names `grid.time_s` as a departure ended by PR 3 |
| Det | N2 | **fixed**, verified | seam refuses `turn != 0` or `time_s != 0`; plant H fails 1. Residual: new N1 |
| Det | N3 | **deferred** | a half-done tick on an exception matters once the window moves into `step`; today only programming errors raise. Trigger: PR 3. Recorded only in fold.md (new S1) |
| Det | N4 | **fixed** (partial residual) | the SCHEDULE bit-identity test compares `frames.latest.sequence`; `from_scene` compares temperature and material. Residual: new N3 |

## Plants (copy only; each run is the full `tests/test_simulation.py`, baseline 40 passed, 1 xfailed)

| Plant in `Simulation.step` / `_check_batch` | Result |
|---|---|
| none | 40 passed, 1 xfailed |
| A: physics before apply | 3 failed: bit-identity [0.2], [0.1], `test_a_record_on_a_physics_tick_applies_before_that_ticks_physics` |
| C: drop records on a physics tick | 3 failed: the same three |
| B: apply in reverse, outcomes reversed back | 3 failed: bit-identity [0.2], [0.1], `test_an_ignite_then_a_douse_in_one_tick_leaves_no_fire` |
| D: drop every record | 8 failed (the strict xfail turns into an error, as it should) |
| E: batch read without `tuple()` | 1 failed (generator test) |
| F: no `apply_us` bound | 1 failed |
| G: no duplicate-id check | 1 failed |
| H: no advanced-world check on the seam | 1 failed |
| I: `physics_seconds + 1e-6` | 6 failed, all three bit-identity tests among them |

The fold's claim that the first three plants left the suite green before the fold and now fail is true. Its
correction to 553abca ("4 tests, not 3" for plant I) matched the old suite; with the literal `STEP_S` the count is now
6.

## Bit-identity with direct World use

Holds. On c9c0370: `tests/test_simulation.py` 40 passed, 1 xfailed (the strict frame-cadence gate);
`test_determinism.py`, `test_tooling_config.py`, `test_input_allowlist.py` 207 passed. The three bit-identity tests
(SCHEDULE at 0.2 and 0.1 m over 60 ticks; a 600-tick burn that destroys crate cells) compare the full digest; the
direct path issues the same applier calls in the same order and `advance(0.5)` on `t % 5 == 0`, with no value shared
with the shell. The shell still has no clock, RNG or `hash()`; the key order is total (strictly increasing keys, and
now a unique `(actor_id, seq)` per batch).

## New findings

### SHOULD-FIX

**S1. `docs/design/reviews/sim_shell/fold.md` (Det S2 cross-tick, Det N3): the deferrals live only in a review
file.** CLAUDE.md: "A finding with no code to mark is deferred as a backlog row or a known gap instead." Neither
deferral appears in `docs/roadmap.md`, `docs/standards_backlog.md`, `sim_core.md` or a code marker (grep for
`(actor_id, seq)`, "half", "exception" in those files: only boundaries §6.1's definition). Failure scenario: PR 4's
author builds the log reader from sim_core.md and the roadmap, never opens `reviews/sim_shell/`, and a replayed log
that repeats `(actor 7, seq 3)` on ticks 10 and 40 is accepted, so two receipts share one id; likewise PR 3 moves the
window into `step` and a retried tick double-applies its records. Fix (unverified): one roadmap line under step 5a's
PR 4 and PR 3 scopes, or a backlog row each, naming the check and its trigger. (Architecture N1/N4 and Wire N5 have
the same shape; not my lenses, flagged for their reviewers.)

### NIT

**N1. `simulation.py::Simulation.__init__`: the seam accepts a world that has been written but not advanced.** Probe:
`Applier(w).apply("crate", IGNITE)` then `Simulation(w, config=T3)` is accepted, with frame sequence 1 and a fire
already burning. That input never passed through a record, so it is outside the log a replay would hold. Harmless for
the strangler tests that exist, but the check's stated purpose is "a world at construction (tick 0)"; adding
`world.frames.latest.sequence != 0` makes it say what it means. Unverified.

**N2. `intents.py::LogRecord.__post_init__`: `_bounded`'s normalized `int` is discarded, so the record keeps the
caller's integer type.** Probe: `actor_id=np.int64(3)` gives `key == (1, 30, 0, np.int64(3), 0)`. Ordering and the
duplicate check still work (numpy ints compare and hash as Python ints), so determinism is not broken today, but PR 4's
writer and any digest over keys will meet numpy scalars (`json` refuses `np.int64`; `repr` differs). Store the
normalized value (`object.__setattr__`) or refuse non-`int` exactly. Unverified.

**N3. `tests/test_simulation.py::test_a_burning_run_through_simulation_is_bit_identical_to_the_same_calls_on_world`
and `test_from_scene_builds_the_same_world_as_world_from_scene`:** the burn test doesn't compare
`frames.latest.sequence`, and the `from_scene` test compares two channels instead of `digest()` (regions, integrity
and sources not covered). Each is one line; Det N4 asked for both. Unverified.

## Fixes verified vs unverified

Verified by plant in the copy: Exec S1, S2, N1, N2; Det B1, S1, S2 (a, in-batch b), N2; S3 by `lint_standards.py`
PASS. Read only, not planted: Exec N3, N5; Det N1, N4. The three new NITs' fixes and new S1's fix are unverified.
