# PR 4a (`phase1/sim-replay`) delta round 2, Executor, Determinism, Performance, Physics: the delta-1 fold, read from the tree

**Reviewed:** `git diff c721850 8a8fecb` (the round-1 and delta-1 fold, one commit), its message (`git show -s
8a8fecb`), and the merge `82447d3` only as far as the lesson renumbering and the OD-A16 citation. I read every
`fold.md` row in these four lenses, round 1 and delta 1, against the tree.

**How I ran things:** on my copy of `82447d3` (`scratchpad/delta2_a/tree`), with the sim-replay venv's interpreter
under `-I` and the copy's `src` and root first on `sys.path`. `simcore.__file__` resolves into the copy. Every
mutation goes through `delta2_scripts/a_mutate.py`, which applies one named string replacement, runs pytest
(`a_run.sh`) and restores the file, checked by sha256. Afterwards `diff -rq` showed `src` and `tests` identical to the
worktree. For timing I compared against `git archive 336eee8 src data` (`scratchpad/delta2_a/base336`). Scripts are
in `_durable/sim_tick_review/delta2_scripts/` (`a_run.sh`, `a_mutate.py`, `a_tile_burst.py`, `a_fire_burst.py`).

Unmutated copy: `test_simulation`, `test_laws`, `test_deposit`, `test_exposure`, `test_heat` and `test_determinism`
gave 255 passed, 1 skipped. `test_determinism`, `test_sem_bridge`, `test_ownership`, `test_imagination` and
`test_cross_tier` gave 276 passed, 2 skipped, 4 xfailed (strict). `ruff check` and `ruff format --check` are clean on
`src scripts tests`, and no line in `tests/_imports.py` is over 120 columns. I did not run the full suite or the 0.05 m
tier.

## Counts

**New findings: 0 BLOCKER, 0 SHOULD-FIX, 3 NIT.**

**Statuses set: 24 rows. 20 fixed, 3 deferred, 1 open.** The one that differs from the author's account, and from
delta 1, is Exec N2. Delta 1 read it as deferred. I set it **open**, because the deferral exists only in the fold
table: no checklist row, backlog row or B5 entry records it.

## Deletion proofs (all hold)

Each mutation was run against `test_simulation`, `test_laws`, `test_deposit` and `test_exposure`, and most also against
`test_heat` and `test_determinism`.

| Mechanism broken | Red tests |
|---|---|
| The warm in `Simulation.step`'s `except` branch (deleted) | `test_a_retried_tick_counts_the_same_work_as_one_that_never_failed[quiet]` only. The `[a strike]` case stays green, as D-S1 said it would. |
| `Physics.warm` without `reading(reads=law.reads)` | `test_a_law_state_warming_up_reads_only_what_its_law_declares` |
| `_publish` before `self._clock.advance()` | `test_a_publication_that_raises_leaves_the_tick_counted_so_no_retry_applies_it_twice` (at `assert sim.tick == 2`) |
| `self._rollbacks += 1` (deleted) | `test_no_version_a_rolled_back_window_reached_is_reached_again`, `test_a_bare_orchestrator_on_a_rolled_back_grid_serves_no_stale_cache`, `test_a_window_that_rolls_back_leaves_no_entry_a_later_state_could_reuse` (3, as claimed) |
| The revocation copy not `_counted` | `test_the_work_counters_hold_their_exact_values_and_repeat_on_a_rerun` |
| The `_handed_open` bump at commit (Det N-1) | `test_a_field_written_in_construction_s_window_moves_its_version` |
| The tick-end warm | the counter test and `test_a_rolled_back_tick_leaves_no_cache_a_later_state_reuses` |
| Construction's warm | the counter test |
| The rollback warm and the rollback count together | 5 tests, all bit or stale-cache tests. `[quiet]` passes: with the counts restored, the old cache is valid again. This confirms delta 1's remark that the warm matters only for the counters, given the count. |
| The cell-based gone rule restored | `test_a_strike_on_a_region_destroyed_earlier_in_the_tick_applies_and_destroys_nothing[0.2]` and `[0.1]` |
| A strike's `edits_cells = False` | 6 tests in `test_simulation` and `test_laws` |
| `Deposit.keep` without pruning | 2 deposit tests |

Every deletion claim in the commit message that falls in my lenses reproduced. I did not rerun the bound and prepare
narrowing proofs (Arch S1). Delta 1 ran them, and the code is unchanged since.

## New findings

### NIT 1. `Simulation.step`'s docstring still says a raising tick changes nothing, but a raising publication now leaves the tick committed, with no frame and no report
`src/simcore/core/simulation.py::Simulation.step`.

The docstring says: "A tick that raises later changes nothing either: the window rolls back ...". After Det N-5, a
`_publish` that raises comes after the commit and after `self._clock.advance()`. That tick's records are applied, the
clock has moved, no frame exists for that tick, and the caller gets no `TickReport` (so its `WorkCounters` are lost).
The shipped test shows exactly this: after the planted `MemoryError`, `sim.tick == 2` and `fire:crate` is in the
sources. The next sentence of the docstring describes the new order, so the text now contradicts itself.

**Failure scenario (PR 4b):** a host or log writer that appends a tick's batch to the intent log only when `step`
returns has to treat the exception as "nothing happened". It would then drop a tick that did commit, and a replay
from that log would diverge from the live state at that tick. The publication also breaks "one frame per tick with a
record" (`test_ownership.py::test_the_shipped_path_publishes_one_frame_per_tick_with_a_record_or_physics`). Only a
`MemoryError` in `CellFrame.of` can realistically cause it today, because `FrameFeed.publish`'s own checks can't fail
on this path.

**Fix:** correct the docstring now. The fuller fix belongs in PR 4b's log design and needs a trigger there: the log
records a tick before publication, or independently of it. Unverified.

### NIT 2. The D-S2 deferral row leaves out two costs a B5 reader will meet
`docs/plans/checklists.md`, the Step 5a row "Incremental cache rebuilds"; the mechanism is
`src/simcore/core/simulation.py::Simulation._run` (the tick-end `warm`) together with `deposit.py::Deposit.keep`.

1. **No max-profile figure.** I reproduced the row's measurement with `a_tile_burst.py`: T3 tile, 0.1 m, 230,400
   cells, a strike every tick for 20 ticks, three alternating pairs, load average about 30. The fold took 204–237 ms
   and 336eee8 took 91–115 ms, with 20 face builds against 4. That is a ratio of 2.0–2.5×, consistent with the row's
   "2×" at its low end. The extra 16 rebuilds cost about 8 ms each at 230,400 cells. Scaled linearly, that is about
   170 ms per strike tick at the max profile (5×10⁶ cells), which is the number B5's budget will be held against. The
   charter's Performance lens asks for the max-profile cost, and the row doesn't give it.
2. **Deposit churn on re-lit fires.** The warm that ends a physics tick keeps only the live source values, because
   `exposure.step` has consumed the closed ones. A fire re-lit at a shape the previous step already used therefore
   rebuilds its overlap and weights. `a_fire_burst.py` re-lights the crate's fire every tick for 20 ticks (T3 tile,
   0.1 m), cycling through 5 radii. It counts `heat/deposit` at 40 in the fold against 10 on 336eee8. The time is
   unchanged (34–39 ms against 36–37 ms), because the boxes are small. This follows from §7 ("holds only what the
   current state needs") and isn't a correctness defect. But it is a 4× change in a counter B5 reads, and neither
   the fold nor the row names it.

**Fix:** add both figures to the D-S2 row. Unverified as wording; the numbers are measured.

### NIT 3. Small text defects in the fold
- `docs/design/sim_core.md` grew from 3,770 words (c721850, and main) to 3,773 (8a8fecb). The rule is that an
  existing design document doesn't grow (O22, B24). Three words, but the rule has no allowance.
- `src/simcore/adapters/sem/bridge.py::StructureModulator.execute`'s marker: "sees an instant effect at once" says
  the same thing twice.

## Status table

| Row | Status | Evidence |
|---|---|---|
| Det SF-1, Arch S3 (lazy caches) | fixed | Deleting construction's warm or the tick-end warm turns the counter test red. Deleting the rollback warm turns `[quiet]` red. All three are wired on the shipped path (`Simulation.__init__`, `_run`, `step`). |
| Arch S2, Exec S1 (eviction at one call site) | fixed | Deleting `_rollbacks += 1` turns the 3 claimed tests red. `field_version` returns `(rollbacks, count)`, and every cache keys on it: `HeatState._faces`, `Physics._bounds`, `Deposit._weights`. |
| Arch S1 (declared reads) | fixed | `Physics.warm`, `bound` and `_prepare` all run under `CellStore.reading`. I proved the warm narrowing myself. The bound and prepare proofs are delta 1's, and that code is unchanged. |
| Exec S3 (`cells_copied`) | fixed | `_counted` is called at open, at views, at revocation and at commit. Uncounting the revocation turns the counter test red. The test asserts (4+2+1+4) × cells. |
| Exec S2 (`REGION_GONE`) | fixed (owner's ruling) | `_check_region` decides on `cells.any()`, authored geometry only. `destroy` never touches region masks (`grid.py::destroy`, `_set_cells`). The cell rule turns both spacings' tests red. The §5.1 and Step 6 checklist rows are present. |
| Det SF-2 (lesson) | fixed | Lesson 37 cites `tool_bridge.py:885` and :860. Roadmap OD-A16 cites §37. |
| Det N-1 (construction's versions) | fixed | The `_handed_open` bump is red when deleted. `Gate.may_write` is False for a `None` writer, so only construction's window fills `_handed_open`. |
| Det N-2, Exec N4 (§7 keys) | fixed (owner's ruling) | §7 line 180 keys on `field_version`, which counts rollbacks. The code matches. |
| Det N-3 (lesson 23) | fixed | Both tests the lesson cites exist (`test_sem_bridge.py`, `test_ownership.py`). |
| Det N-4 ("per call that reaches stage 2") | fixed | `bridge.py:193` and lesson 37 line 502. |
| Det N-5 (clock before publication) | fixed | The order is red when reversed. The docstring is now inaccurate (NIT 1). |
| Arch NIT (`_run` tests `Strike`) | fixed | `edits_cells` `ClassVar`. A strike's set to False turns 6 tests red. |
| Arch NIT (`Physics.work`) | fixed | `Physics.start_tick()`, used in `step`. |
| Exec N1 (bar 7 noise) | fixed | sim_core line 197: "0.32–0.35× at 0.1 m and 0.72–0.98× at 0.2 m". |
| Exec N2 (`rho_cp` per substep) | **open** | The deferral and its trigger ("B5's profile pass") appear only in `fold.md`. `grep rho_cp` finds nothing in `docs/plans`, `standards_backlog.md`, `sim_core.md` or `architecture.md`. CLAUDE.md requires a finding with no code to mark to be deferred as a backlog row. Add one, for example to B5's owed rows or to the Step 5a checklist, and it becomes deferred. |
| Exec N3 (douse exemption) | fixed (moot) | The exemption is gone with the revert (`applier.py` diff). |
| D-S1 (rollback warm untested) | fixed | `[quiet]` is red when the warm is deleted, and the only test that goes red. |
| D-S2 (tick-end rebuild cost) | deferred (owner's ruling) | Reason: no B5 budget exists yet. Trigger: B5's turn-time budget. The row sits under Step 5a in `checklists.md` (lines 248–251) with 363 against 183 ms and the bit-identical incremental fix. Reproduced at 2.0–2.5×. The row lacks the max-profile figure and the deposit churn (NIT 2). |
| D-S3 (ruff line length) | fixed | `ruff check` and `ruff format --check` are clean on `src scripts tests`. |
| D-N1 (warm narrowing) | fixed | Red when unnarrowed (see the proofs). |
| D-N2 (publication order) | fixed | Red when reversed. |
| D-N3 (refused `place` moves counters) | deferred | Reason: `place` opens its own window under its `TEMPORARY(phase1/sim-clock)` marker. Trigger: PR 4b, when `imagine` runs inside the step's window. The Step 5a checklist row is present. |
| D-N4 (stale text, my lenses' items) | fixed | The checklist cache row, `scene.py:48` (`geometry.MAX_LENGTH_M`), the retry test's comment (no `forget`; `grep forget` finds nothing in `src` or `test_simulation.py`), CLAUDE.md's layout (`geometry.py`), §7's attribution split (lines 188–189), and §7's bar 7 range. |
| D-N6 (`test_readme.py` 5.7 s) | fixed | `@pytest.mark.slow` and `skipif(not ALL_TIERS)` at lines 20–21. |

These rows are outside my lenses and I did not set them: Arch S4, S5, S6, Arch N1, N4 (D-N5), N6, N7, N8, N9, and
D-N's cerebellum note. Arch S5 is consistent with what I read: `Simulation.__init__` builds `Physics(world.grid,
laws)`.

## Checked, not findings

- **The geometry split** is verbatim. `geometry.py` holds the removed `grid.py` code byte for byte apart from imports,
  so it changes no physics.
- **A warm that raises.** `Deposit.keep` assigns its dicts at the end, and `HeatState.faces` assigns after building, so
  a warm that raises part-way leaves no half-built cache. In the `except` branch, a second raise from the warm keeps
  the first exception as its context.
- **Cache keys across the commit.** The tick-end warm runs inside the window, but its keys equal the committed ones:
  the commit's `install` bumps only `_handed_open`, which is empty on a tick. A commit that fails after the warm rolls
  back, moves `_rollbacks`, and the warm at rest rebuilds.
- **Bar 7 and other costs.** Bar 7's burn (no strikes) and fire-only ticks cost the same as on 336eee8 (NIT 2,
  item 2). The new `require_read` and `_counted` calls are O(1) per access.
