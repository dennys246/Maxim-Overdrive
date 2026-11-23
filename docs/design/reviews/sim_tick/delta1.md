# PR 4a (`phase1/sim-replay`) delta round 1: the round-1 fold, read from the tree

Reviewed: the staged fold on c721850 (`git diff --cached`, plus `git show c721850`), main's merged client files
excluded. Every claim below was run on a copy of the working tree, with the worktree's venv interpreter under `-I` and
the copy's `src` and root first on `sys.path`. Scripts are in `_durable/sim_tick_review/delta1_scripts/`. Lenses: all
eight of round 1, on the diff.

**New findings: 0 BLOCKER, 3 SHOULD-FIX, 6 NIT.**
**Round-1 statuses: 22 fixed, 5 open (4 waiting on the owner's ruling, 1 wording), 1 deferred, 1 rejected (29).**

## New SHOULD-FIX

### D-S1. The warm after a rolled-back tick has no guard, and the fold and the commit message both say it has one
`src/simcore/core/simulation.py::Simulation.step` (the `except BaseException:` branch's `self._physics.warm(...)`);
`tests/test_simulation.py::test_a_retried_tick_counts_the_same_work_as_one_that_never_failed`.

The fold says: "deleting each `warm` call (construction, a tick's end, after a rollback) turns the counter or retry
tests red". The staged commit message (`fold1_msg.txt`) lists the same deletion proof. For the third call, that is
false. I deleted the rollback-branch warm and ran `test_simulation`, `test_laws`, `test_deposit`, `test_exposure`,
`test_heat` and `test_determinism`: **252 passed, 1 skipped**. The other two deletions do go red: construction's warm
fails the counter test, and the tick-end warm fails the counter test and the rolled-back test.

The retry test can't catch it because its retried tick strikes. A strike moves `material`'s version, so the clean
run rebuilds the faces, the weights and the bound on that tick too, and the counts match either way. The call
matters on a retried tick that changes no topology. `delta1_scripts/retry_quiet.py` makes heat raise once on physics
tick 10 with an empty batch, then retries:
- tree: `equal work: True`;
- rollback warm deleted: `equal work: False`, with `want () 0` against
  `got (('heat/deposit', 1), ('heat/face_conductances', 1)) 1`. The bits are equal in both.

So the mechanism behind SF-1's fix for an ordinary physics-tick failure works but is untested, and the charter's
"prove a guard by deleting what it guards" claim for it is wrong. Note: with the rollback count in every key, the
warm is not needed for correctness, only for the counters. Deleting both the warm and the count was not tried.

### D-S2. Warming at every windowed tick's end rebuilds heat's caches on every strike tick: 2.1× the CPU for a strike per tick, not disclosed
`src/simcore/core/simulation.py::Simulation._run` (`self._physics.warm(exposure.values())` inside the window).

The tick-end warm builds the face conductances, the deposit weights and every per-substep bound for the state the
tick ends in. On 336eee8 these were built on the next physics tick, which is the only reader. Every tick that
changes `material` now pays for a full rebuild, however many such ticks fall between two physics steps. This is the
interim port's normal pattern, because each `submit` is one tick, and it is PR 4b's for an agent that strikes on
consecutive ticks.

Measured (`delta1_scripts/tile_burst.py`): the T3 tile (12 × 4 × 4.8 m) at 0.1 m, crate lit, a 2e7 J strike on a new
point of the wall every tick for 20 ticks (4 physics steps), process time, min of 3:

| tree | face builds | 20 ticks |
|---|---|---|
| 336eee8 | 4 | 186 ms |
| fold | 20 | 399 ms |

On the small crate scene at 0.1 m (`burst.py`) it is the same 20 builds against 4. Bar 7's burn (no strikes) is
unaffected: 88.7–91.0 ms against 88.3–89.4 ms per 6 world s at 0.1 m (`bench_4a.py`, two runs each).

The trade is real, because building at the tick's end is what makes a retried tick and a loaded replay count alike.
But neither the fold nor the message names it, and B5 will read these counters. The fix is the author's or the
owner's design call: a documented cost, or a mechanism that keeps the counters a function of state without building
before a reader exists. I don't propose one.

### D-S3. The staged tree fails the gate's ruff step
`tests/_imports.py` line 110. Adding `"typing.ClassVar"` made the line 121 characters long. On the staged blob,
`ruff check --no-cache tests/_imports.py` reports `E501 Line too long (121 > 120)`. `# fmt: skip` stops the
formatter, not the lint. `scripts/prepush.sh` can't print PASS on this tree, so the fold isn't verified by the gate
yet. Format, mypy (`src scripts tests`, no issues) and import-linter (10 kept) are clean on my copy.

## New NIT

- **D-N1. `Physics.warm`'s narrowing is unguarded.** `src/simcore/core/physics.py::Physics.warm`
  (`with self._grid.reading(reads=law.reads)`). Replacing that line with an unnarrowed block leaves `test_laws` and
  `test_simulation` green (109 passed). `_Peeks` reads nothing in `warm` (its state is stateless), and the new test's
  `orchestrator.warm(())` raises only through the bound, which is narrowed separately. The test docstring says both
  run narrowed "at rest (construction's warm-up)". That holds for the bound, but nothing checks a law state's `warm`.
- **D-N2. Det N-5's reorder ships with no test.** `Simulation.step`. Putting `_publish` back before
  `self._clock.advance()` leaves `test_simulation`, `test_deposit`, `test_sem_bridge` and `test_ownership` green
  (159 passed). It is a behaviour change, so the testing rule wants a test. A planted raising `FrameFeed.publish`,
  then a retry, would make one.
- **D-N3. A rollback of a window `Simulation` didn't open moves every cache key with no re-warm, so the next tick
  counts rebuilds.** `grid.py::CellStore._roll_back` (`_rollbacks += 1`) together with
  `imagination.py::_voxelize`'s own window. Measured (`delta1_scripts/place_refused.py`): on a live simulation, a
  `place` refused inside its window (`TOO_SMALL`, a 5 cm box at 0.2 m, which is itself a spacing-dependent
  refusal) changes nothing in state. Yet physics tick 10 then reports `(('heat/deposit', 1),
  ('heat/face_conductances', 1)) 1` against `() 0` for a run that never tried. So "a function of state" holds only
  for rollbacks `Simulation` owns. `place` has no `src/` caller today and sits under its `TEMPORARY(phase1/sim-clock)`
  marker. *Trigger:* PR 4b, when `imagine` becomes stage 2 inside the tick's window and its refusals reach replay.
- **D-N4. Stale text the fold left.**
  - `docs/plans/checklists.md`, PR 4a's cache row: "per `topology_version`, each with the rollback eviction the
    deposit has". There is no eviction now, and the keys are `field_version`s. This is the "checklist" half of
    Arch N5.
  - `src/simcore/core/scene.py:48`: `# grid.MAX_LENGTH_M`, which is now `geometry.MAX_LENGTH_M`.
  - `tests/test_simulation.py:392`: "rolls back and forgets its caches". `forget` is gone.
  - CLAUDE.md's Layout doesn't list `geometry.py`.
  - sim_core §7: "rebuilt at each tick's end, at construction and after a rolled-back tick (owner, 2026-11-22,
    `reviews/sim_step/fold.md` S1)" attributes the fold's new mechanism to an older ruling about eviction. Only the
    key bullet is marked proposed.
  - sim_core line 197 still gives bar 7 at 0.2 m as "an estimate ... 0.75×", where 0.72–0.98× is now measured.
- **D-N5. The fold's reason for keeping §13's "a callable its test or host owns" is wrong.** It says `Port` is "a
  Protocol with one call". `bridge.py::Port` has a `limits` property and `submit`, which is exactly round 1's point.
- **D-N6. `tests/test_readme.py` takes 5.7 s** (`--durations`: 6,000 ticks at 0.1 m in a subprocess) and isn't marked
  `slow`. The rule is "mark anything over a few seconds `slow`". The spawn itself is right: an `ALLOWED_SPAWNS` "given"
  row, an explicit `env` built like `test_constructors.py`'s, `cwd=tmp_path`, and writes only under `tmp_path`.

## Round-1 statuses (read from the tree)

| Finding | Status | Evidence |
|---|---|---|
| Exec S1 (heat's eviction untested) | fixed | Deleting `_rollbacks += 1` turns 3 tests red: `test_no_version_a_rolled_back_window_reached_is_reached_again`, `test_a_bare_orchestrator_on_a_rolled_back_grid_serves_no_stale_cache` (real `HEAT`) and the deposit's PR 3 S1 test. The rollback test now uses the real `HEAT`. |
| Exec S2 (REGION_GONE flips with spacing) | fixed (owner's ruling, verified) | `_check_region` matches bfb12f8 line for line. My destruction schedule (`gone_bits.py`: the block struck to nothing, then struck, lit, doused and lit again) is bit-identical to bfb12f8 at 0.2 and 0.1 m, with identical outcome codes. The author's `compare.py` and `compare2.py` match too (0.2 m, 400 ticks). Putting the cell rule back turns the new test red at both spacings. The §5.1 and checklist rows are amended. |
| Exec S3 (`cells_copied` 2.75× low) | fixed | Counted in `CellStore._counted` where each copy is made. The test asserts (4+2+1+4) × cells, which matches round 1's instrumented 11. Not counting the revocation turns the counter test red. |
| Exec N1 (0.2 m bar-7 noise) | fixed | The range is recorded in fold.md, and the PR is to carry bar 7 (336eee8's message). My 0.1 m rerun is 88.7–91.0 ms, about where it was at 336eee8. The sim_core line 197 estimate is D-N4. |
| Exec N2 (`rho_cp` per substep) | deferred | Reason: optimise from a profile (B5). Trigger: B5's profile pass. Named in fold.md only. |
| Exec N3 (douse exemption not in §5.1) | fixed (moot) | The exemption went with the revert. A douse on a struck-out region succeeds (`gone_bits.py`, tick 3), as on main. |
| Exec N4 / Arch N5 / Det N-2 (§7 keys) | open (owner) | §7 is drafted and marked proposed, and it matches the code (`field_version("material")` for the faces and the weights). The checklist row is still stale (D-N4). |
| Arch S1 (`bound_reads`, `prepare` unenforced) | fixed | `CellStore.reading`. Unnarrowing the bound turns `[bound]` red, and unnarrowing prepare turns `[prepare]` red. Round 1's `h1.py` case now raises `UndeclaredRead`. `warm`'s narrowing is unguarded (D-N1). |
| Arch S2 (eviction at one call site) | fixed | The key's rollback count makes it the type's. A bare `Physics` on a rolled-back grid serves no stale faces, and the test goes red without the count. |
| Arch S3 / Det SF-1 (lazy caches; counters depend on history) | fixed | Construction warms at rest. My runs over 50 ticks with strikes, ignites and douses (`retry_long.py`): a second fresh run, a retry of the same strike, a retry after a failed crate strike and a retry of a quiet physics tick (25) all match the uninterrupted run's `WorkCounters` on every tick, and bit for bit. The after-rollback warm that the quiet retry depends on is unguarded (D-S1). |
| Arch S4 (README, spike on the retired API) | fixed | The README runs (`test_readme.py`, which passes and prints a ratio). `spikes/slice/README.md` pins bfb12f8 (owner). Its reason is plausible: the spike's body step reads the frame before stepping. |
| Arch S5 (unchecked built-world constructor) | fixed | `Simulation(world, *, config, laws)` builds `Physics(world.grid, laws)`, so round 1's two-grid case can't be built. |
| Arch S6 (§2 `source_exposure`) | open (owner) | §2 is drafted, marked proposed. |
| Arch N1 (stale names) | fixed | The contract name, boundaries §6.2 ("the deposit"), fire_solid's `_check_region` row (true again), and `on_close` deleted in c721850. |
| Arch N2 (`_run` tests `Strike`) | fixed | `edits_cells` `ClassVar`, excluded from `asdict` and the wire. Setting a strike's to False turns 13 tests red. |
| Arch N3 (`Physics.work` replaced) | fixed | `Physics.start_tick()` returns the tally. |
| Arch N4 (§13 "a callable"; roadmap line) | open | The roadmap line is fixed. §13 is left with an inaccurate reason (D-N5). |
| Arch N6 (fierce-fire units) | fixed | Labelled "in 6 s turns". The stray capital "It" remains. |
| Arch N7 (`place` publishes no frame) | fixed | Stated in its marker. |
| Arch N8 (`Simulation.step` no gate row) | rejected | The reason holds: the records are `LogRecord`'s gate rows, and the batch check has its own tests. |
| Arch N9 (`field_version` overclaims) | fixed | It now says the key may move when the values didn't, and that it can't recur after a rollback. True as built. |
| Det SF-2 (lesson 34/35) | fixed | Rewritten. `tool_bridge.py` at pymaxim 1.3.3 (in the venv): line 584 is `reading = sensor.read()` in the post-`execute` read-back, and line 885 is `actual=entity_state` in `observe_from_action`. Pointed at lesson 6 and OD-A16, whose row cites §35. (The call runs only with a cerebellum attached and a non-empty read-back, line 860. The lesson's claim holds whenever it runs.) |
| Det N-1 (construction writes don't move versions) | fixed | `_handed_open` is bumped at commit. Removing it turns the new test red. Only construction's window can hand anything writable outside a block (`Gate.may_write` with `writer=None`), so ticks never use it. |
| Det N-3 (lesson 23 cites a missing test) | fixed | `test_ownership.py:481` exists. |
| Det N-4 ("one tick per call") | fixed | The marker, `SteppingPort` and §35 say "reaches stage 2". |
| Det N-5 (commit before publication) | fixed | The clock advances before `_publish`. Untested (D-N2). |

## Not findings (checked)

- **Suite.** All of `tests/` on my copy: 2,877 passed, 25 skipped, 5 xfailed (strict). The 5 failures needed git (the
  copy had no `.git`). After `git init` in the copy they pass (382 passed across `test_lint_standards`,
  `test_tooling_config` and `test_validation`). The 0.05 m tier was not run.
- **Can a cache serve a state it wasn't built from?** I found no path. Versions move at revocation, at `_set_cells`
  and at construction's commit. Each rollback moves `_rollbacks`, which nothing restores. The overlaps key on
  geometry alone. No warm or bound runs inside a law's narrowed block (`Gate.narrow` refuses nesting). The commit's
  install moves no version on a tick, because `_handed_open` is empty outside construction. So the warm keys inside
  the window equal the committed keys.
- **`reading` at rest.** `_channel` and `regions` now gate reads when narrowed at rest. `solid` and `volume_m3` go
  through `material`. A state's `warm` that opened a window inside `reading` would reset the gate's narrowing
  (`Gate.open` sets `_narrowed = None`), but no state does, and laws don't open windows.
- **`SourceExposure.values()`.** It is sorted by key, stable for a key that is both closed and live, and holds what
  `power`'s own `keep` would hold on the next step. Deleting `keep`'s pruning turns 2 deposit tests red.
- **`cells_copied` scope.** Region-mask copies (`_take_cells`, `name_region`) aren't counted. They are masks, not
  fields, and a strike makes none. Worth naming when `imagine` joins the tick (4b).
- **The geometry split.** `grid.py` is at 449 lines (503 before the split, per the message). The split follows a
  responsibility: no state and no window. Every importer moved. Both forbidden lists name it, and
  `test_tooling_config` holds them.
- **`Simulation.__init__` warm with construction-time sources** (`test_exposure._run`): the warm runs at rest and is
  counted in no tick.
- **The README's spawn** follows the isolation rules (D-N6 covers only its duration).
