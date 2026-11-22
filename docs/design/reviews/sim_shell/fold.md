# Fold of step 5a PR 1's review (`phase1/sim-shell`)

Four readers reviewed 553abca: Executor, Architecture, Wire integrity and Determinism (1 BLOCKER, 17 SHOULD-FIX, 18
NIT). Their reports are kept verbatim beside this file. Every status below is **open (for the reviewer)**: a reviewer
sets it from the tree (O25). The branch first merges `main`, including #37, which moved `kind_rank` to
`boundaries.md` §6.2.

**Verified by plants** (scratch copies, each restored): physics before apply, records dropped on a physics tick,
records applied in reverse, the batch read without materialising, the duplicate-id check removed, the `apply_us`
bound removed, the seam's advanced-world check removed, a constant `kind_rank`, an open rank table, and an unchecked
`actor_id`. Each now fails at least one test in `tests/test_simulation.py`; before this fold, the first three left
the suite green.

**Correction to 553abca's message:** the stretched-interval plant (`physics_seconds + 1e-6`) failed 4 tests, not 3.

## Determinism

| Id | What changed | Status |
|---|---|---|
| B1 | `SCHEDULE` puts records on ticks 1, 5 and 30 (5 and 30 are physics ticks), including a douse then a re-ignite in one physics tick; the bit-identity test runs it at 0.2 and 0.1 m and compares frame sequence too. `test_a_record_on_a_physics_tick_applies_before_that_ticks_physics` and `test_an_ignite_then_a_douse_in_one_tick_leaves_no_fire` added. The three plants fail | open (for the reviewer) |
| S1 | `step` reads the batch once with `tuple(records)` and takes any `Iterable`; `test_a_generator_batch_loses_no_record` | open (for the reviewer) |
| S2 | `_check_batch` refuses `apply_us >= tick_us` and a repeated `(actor_id, seq)` within a batch; the record bounds `apply_us` below 2⁶³. The cross-tick uniqueness of `(actor_id, seq)` belongs to the log's reader: **proposed: deferred**, trigger step 5a's PR 4 | open (for the reviewer) |
| N1 | Named in `simulation.py`'s docstring as an interim departure: `grid.time_s` is retired in PR 3, with the fixed step | open (for the reviewer) |
| N2 | The seam refuses a world whose `turn` or `grid.time_s` isn't 0; `test_the_seam_refuses_a_world_that_has_already_advanced` | open (for the reviewer) |
| N3 | No change: a half-done tick on an exception is PR 3's, when the window moves into the step. **Proposed: deferred**, trigger PR 3 | open (for the reviewer) |
| N4 | The bit-identity test compares `frames.latest.sequence`; the `from_scene` test compares temperature as well as material | open (for the reviewer) |

## Executor

| Id | What changed | Status |
|---|---|---|
| S1 | As Determinism B1: `test_a_record_on_a_physics_tick_applies_before_that_ticks_physics` steps four empty ticks, then a physics tick carrying an ignite | open (for the reviewer) |
| S2 | As Determinism S1 | open (for the reviewer) |
| S3 | `Simulation.__init__` carries `TEMPORARY(phase1/sim-clock)`, naming PR 4 as the removal; the roadmap's write-window bullet lists `simulation.py`. The removal moment is PR 4, not PR 2 (Architecture S3) | open (for the reviewer) |
| N1 | As Determinism S2; `actor_id` is an integer (Wire S1), and `target` passes `checks.identity_key` | open (for the reviewer) |
| N2 | `_directly` uses a literal `STEP_S = 0.5`, so a wrong derived interval in the shell can't cancel out | open (for the reviewer) |
| N3 | The module docstring lists all three interim departures together, and `SimConfig`'s docstring names `substep_refine` (PR 3) | open (for the reviewer) |
| N4 | No change: the shell has no shipped caller until PRs 2–4 put the host on it, as the module docstring says | open (for the reviewer) |
| N5 | The markers in `world.py`, `applier.py` and `imagination.py` and the roadmap bullet now say "until `Simulation.step` owns the window" and name the PR that moves each | open (for the reviewer) |

## Architecture

| Id | What changed | Status |
|---|---|---|
| S1 | `LogRecord`, `KIND_RANK` and `RECORD_KIND_OF` move to `simcore.core.intents` (layer 5b), which the membrane and the protocol may import; `simulation` stays forbidden to the membrane | open (for the reviewer) |
| S2 | The record takes §6.2's names: `kind` is a field and `params` the typed payload, checked to match its kind. The remaining §6.2 fields join in PR 4 as fields, with their payload kinds, so the type widens rather than renames | open (for the reviewer) |
| S3 | As Executor S3 | open (for the reviewer) |
| S4 | `SimConfig` uses `checks.whole_number`; the record bounds its integers with `whole_number` and `RefusalCode.OUT_OF_RANGE`; `target` passes `identity_key`. `actor_id` is an integer, not an identity key, because §6.2's ordering keys are integers (Wire S1) | open (for the reviewer) |
| S5 | As Executor N5 | open (for the reviewer) |
| N1 | No change: outcomes stay in key order, positionally; the receipt id joins with PR 4's record. **Proposed: deferred**, trigger PR 4 | open (for the reviewer) |
| N2 | `RECORD_KIND_OF` spells `Extinguish`'s record kind `douse`, the v0 log's word | open (for the reviewer) |
| N3 | As Wire S4 | open (for the reviewer) |
| N4 | No change: a validated `TickBatch` type is PR 4's, with the log reader that builds batches. **Proposed: deferred**, trigger PR 4 | open (for the reviewer) |

## Wire integrity

| Id | What changed | Status |
|---|---|---|
| S1 | `actor_id` is an `int` from 0 to 2³² − 1; `test_actor_ids_order_as_integers_not_as_text` | open (for the reviewer) |
| S2 | `KIND_RANK` is a closed table of the kinds a record can carry today, with values from `boundaries.md` §6.2; an unlisted kind is refused. `test_a_records_rank_is_read_from_the_table_not_assumed` kills the constant-rank plant | open (for the reviewer) |
| S3 | As Determinism S2; `seq` is bounded below 2³² | open (for the reviewer) |
| S4 | The frame-cadence departure is named in `simulation.py`'s docstring, with a strict red gate, `test_a_refusal_only_tick_publishes_one_frame_stamped_with_its_tick` (`raises=AssertionError`; its precondition raises `RuntimeError`). It flips in PR 4 | open (for the reviewer) |
| S5 | **For the owner, not folded:** `tile_and_client.md` §6.2's exit script joins the host at tick 0, while `sim_core.md` §3 makes tick 0 construction and `LogRecord` refuses `apply_tick` 0. One of them has to give | open (for the owner) |
| S6 | CLAUDE.md's layout lists `simulation.py`, and `intents.py` now says it holds the log record | open (for the reviewer) |
| S7 | `boundaries.md` §2.2 lists `simulation` as built under `engine.sim`, and drops `Simulation` from "Not built" | open (for the reviewer) |
| N1 | As Architecture N2 | open (for the reviewer) |
| N2 | As Executor N3 | open (for the reviewer) |
| N3 | The rank comment cites only `boundaries.md` §6.2, the owner | open (for the reviewer) |
| N4 | `pyproject.toml`'s membrane comment names the simulation among what the membrane gives up | open (for the reviewer) |
| N5 | No change in this PR: CLAUDE.md's "only `World.advance` moves time" and "Time comes from `World.advance`" are rewritten with PR 2, which moves the laws' window into the step. **Proposed: deferred**, trigger PR 2 | open (for the reviewer) |

## Also changed

- The core's external names allow `collections.abc.Iterable` (`tests/_imports.py`), for `step`'s parameter.
- The gate registry lists `LogRecord` (meets, `tests/test_simulation.py`), `LogRecord.key` and
  `LogRecord.kind_rank` (no input), since `intents.py` is a gate module.
