# PR 4a (`phase1/sim-replay`) delta round 3: the delta-2 fold, read from the tree

**Lenses:** Executor, Architecture, Wire integrity, Determinism and replay.

**Reviewed:** `git diff 82447d3 afda61c` and `git show -s afda61c`, both delta-2 reports, and fold.md's "Delta 2"
table. I set every status by reading the tree at `afda61c`.

**How it was run:** I used a copy of `afda61c` at `.../scratchpad/delta3/tree`. The interpreter was the worktree's
venv under `-I`, with the copy's `src` and root first on `sys.path`; `simcore.__file__` resolved into the copy.
- **Tests:** `test_simulation`, `test_ownership` and `test_sem_bridge` gave 147 passed.
- **Lint:** after a throwaway `git init` in the copy, `scripts/lint_standards.py` gave PASS with 0 findings.
- **Deletion proof:** I replaced `world.adopt()` with `pass`, and
  `test_a_world_another_simulation_owns_is_refused_so_time_has_one_owner` failed (1 failed). I then restored the file,
  checked it byte for byte against the worktree, and removed the copy's `.git` and caches. `diff -rq` against the
  worktree is clean.
- **Rewraps:** a whitespace-token diff (`token_diff.py`) between `82447d3` and `afda61c`.
- **pymaxim:** 1.3.3, read from the venv's site-packages.
- **Scripts:** in `_durable/sim_tick_review/delta3_scripts/`: `probe_adopt.py`, `probe_shared_grid.py`,
  `probe_sources_rollback.py` and `token_diff.py`.
- **Not run:** the full suite, the 0.05 m tier, mypy, import-linter and the gate.

## Counts

**New findings: 0 BLOCKER, 1 SHOULD-FIX, 6 NIT.**

**Statuses set (12 rows):** 10 fixed, 1 open (D2-S1 with Arch S5), 1 split (A N2 is fixed; Exec N2 is deferred).
- **Differs from the author:** the author's account implies D2-S1 is closed. I set it **open**.
- **Fixed with a caveat:** D2-N5 is fixed for every line it named, but the author's broader claim ("every line this
  branch added past 120 columns") is false by one line (D3-N5).
- **Fixed in part:** A N1 is fixed for `step`, but the module docstring still makes the old claim (D3-N3), and the new
  rollback comment claims more than the code delivers (D3-N2).

## New SHOULD-FIX

### D3-S1. `adopt` guards the `World` wrapper, not the state time owns. Two simulations can still step one grid
**Where:** `src/simcore/core/world.py::World.adopt`, `src/simcore/core/simulation.py::Simulation.__init__`;
`docs/design/sim_core.md` §2 ("a world has one simulation"; "One owner of time").

`adopt` sets a flag on the `World` object. The cell state, though, is the `MaterialGrid` (plus the sources), and
`World(grid, *, limits, sources)` accepts any grid, including one another simulation owns. D2-S1's scenario comes back
one layer down.

*Failure scenario (verified, `probe_shared_grid.py`):*
1. Build a simulation and run 3 ticks.
2. `w = world_of(first)`, then `Simulation(World(w.grid, limits=w.limits, sources=w.sources), config=T3)`. It is
   accepted at tick 1 and publishes frame 0 at `tick=0, time_us=0` of the stepped grid.
3. Step `first` 2 ticks and `second` 5 ticks. Both reach `(tick 6, frame tick 5)`, and `world_of(second).grid is
   w.grid`.

The grid now runs physics twice for one tick 5, and no window refuses it. The window's single ownership is one owner
at a time, not one owner across time. The only route to it is the same one D2-S1 used: a test or host holding a live
simulation's private state. So it is as reachable as the scenario that fold closed. PR 4b's loader is the first real
caller, and it builds a `World` from a grid.

The constructor still checks nothing about the world's state either. Round 1's Arch S5 asked that it refuse a grid that
isn't at construction, and D2-S1's second point was that the loader "needs a tick other than 0, which this signature
can't take". §2 now names `Simulation(world)` as "the save loader's (PR 4b)". Yet it always starts the clock at 1 and
publishes frame 0 at tick 0, and §3 (sim_core line 58) still says tick 0 "publishes the authored world". So the
contract promises the loader an interface that can't represent a loaded state.

*Fix (unverified):* put the single adoption on the grid, the store the window already owns (for example, the grid
refuses a second adopting `World`, or `World.__init__` adopts its grid). Either state in §2 that the save loader's
tick and frame-0 rule are PR 4b's to change, or drop the "save loader's" claim until PR 4b.

## New NIT

- **D3-N1. A construction that raises after `adopt` consumes the world.**
  `src/simcore/core/simulation.py::Simulation.__init__` calls `world.adopt()` before `Physics(world.grid, laws)`, which
  raises on a bad law tuple (`test_a_law_tuple_the_registry_disagrees_with_is_refused_at_construction`). The world is
  then left adopted with no simulation. *Scenario (verified, `probe_adopt.py`):* the first construction raises "a law
  tuple names each law once". A retry on the same world with the default laws is refused with "this world already has
  its simulation". `from_scene` discards its world, so the shipped path is unaffected today. A PR 4b loader that
  retries on the same world would hit it. *Fix (verified):* I moved `world.adopt()` to just before
  `physics.warm(...)`. `test_simulation.py` gave 56 passed, including the two-owner test, and the probe's retry was
  accepted. The file was restored afterwards.
- **D3-N2. The new rollback comment's "No key it reached can recur (field_version counts rollbacks)" is false for a
  sources-only tick.** `src/simcore/core/simulation.py::Simulation.step`, the `except` branch. A tick of fires and
  douses alone runs inside `CellStore.holding()`, which never calls `_roll_back`, so `_rollbacks` doesn't move.
  *Scenario (verified, `probe_sources_rollback.py`):* plant a raise in `SourceExposure.end_tick` on an ignite-only tick
  1. Before and after, `(_rollbacks, field_version("material"))` is `(0, (0, 2))`. Every key that tick reached is the
  current key, and it recurs on a retry. No cache is wrong, because no cell changed. But the comment's stated reason
  covers only cell windows, and a reader relying on it for a future cache keyed on sources would be misled.
- **D3-N3. The module docstring still makes the claim A N1 removed from `step`.** `src/simcore/core/simulation.py`
  line 5: "all in one window: a tick that raises changes nothing, its source exposure included". A raising publication
  leaves the tick committed. This is the same contradiction one screen up.
- **D3-N4. The D-S2 checklist row misstates the deposit churn's condition.** `docs/plans/checklists.md`, Step 5a,
  "Incremental cache rebuilds": "A fire re-lit every tick at a new radius counts `heat/deposit` 40 times against 10".
  Delta 2's NIT 2 measured a fire cycling through 5 radii and said the point is that a fire "re-lit at a shape the
  previous step already used ... rebuilds". A rebuild at a new radius is expected. The surprise is the rebuild at a
  radius already used. The row also drops "per 20 ticks" and the T3 tile at 0.1 m. A B5 reader would take the 4× as
  the expected case.
- **D3-N5. One branch-added prose line is still past 120 columns.**
  `docs/design/reviews/sim_tick/fold.md:70` ("- **(a) Revert to main's rule ...", 139 characters) was added in
  `8a8fecb` and is neither a table nor a heading. The commit and the D2-N5 row say "every line this branch added past
  120 columns (outside tables and headings) is rewrapped". The lines delta 2 named are all fixed. A character count of
  every added `.md` line since the merge base, outside `reviews/`, finds none past 120. The one other hit, in
  `tests/test_laws.py:462` (126, ending `# type: ignore`), is code that ruff allows.
- **D3-N6. The bridge test's name still states the rule D2-S2 corrected.**
  `tests/test_sem_bridge.py::test_the_membrane_steps_only_through_its_port_one_tick_per_call`. Its comment now says
  "each execute that reaches stage 2", but its name, which lesson 37 cites as evidence, still says "one tick per
  call". If it is renamed, lesson 37's citation has to change in the same commit.
- **D3-N7. §7's tightened cost line lost two qualifiers.** `docs/design/sim_core.md` §7, "**Cost** on the T3 tile".
  The PR 4a figures lost "measured". PR 3's "0.88–0.96× and 2.4×" lost their grids, so the reader has to infer the
  order (0.1 m, then 0.2 m) from the sentence before. No number changed and no contract was dropped. The rest of the
  §7 and §13 cuts keep every rule:
  - the cache keys;
  - "holds only what the current state needs", with construction, the windowed tick's end and the rollback as rebuild
    sites (now more precise: a quiet tick opens no window);
  - the bridge's one record per call that reaches stage 2, physics every `physics_every`-th such call, the unlogged
    records and the no-bar rule.

## Checked, not findings

- **The rewraps are word for word.** Token sequences are identical for CLAUDE.md (5,031 tokens).
  - `architecture.md` changed only "It" to "it".
  - The roadmap, the lessons, the checklist and fold.md changed only in the intended D2-N2, D2-N3, D2-N4, D-S2,
    `rho_cp`, PR 4b and Delta 2 text.
  - `lint_standards` passes, so no guard citation broke.
- **`ValueError`.** It is the type `Simulation` already uses for construction misuse (the law tuple). This is a
  programming error, not untrusted input, so `Refused` would be wrong.
- **The ownership scans.** `adopt` grants no capability, so it needn't be an `OWNED_CALLS` entry. The adapters and the
  protocol hold no `World` (capability passing, `PEEKS`), so they can't call it.
- **sim_core.md budget.** `wc -w` gives 3,770 at `bfb12f8`, 3,773 at `82447d3` and 3,770 at `afda61c`. The new §4
  line, `Simulation(world, *, config: SimConfig, laws=DEFAULT_LAWS)`, matches `__init__`'s parameters.
- **pymaxim 1.3.3.**
  - `cerebellum.py`'s docstring has "mirroring NAc but for sensory prediction instead of reward".
  - `tool_bridge.py`: line 584 is `reading = sensor.read()`, line 860 is the `if self._cerebellum is not None and
    entity_state:` guard, line 885 is `actual=entity_state`, and line 908 is `"entity_state": entity_state` in the
    tool's output.
  - NAc's measured credit comes from `_intero_before` and `_measured_credit_total` (lines 541–747).
  - Lesson 37 and the OD-A16 row now say this correctly.
- **The new test's bar.** `(first.tick, first.frames.latest.tick) == (6, 5)` holds the first simulation's ownership
  after the refusal, and the test fails with `adopt` deleted.
- **The PR 4b publication row and the `step` docstring** match `step`'s order: commit, then the clock, then the
  publish. They also match delta 2's NIT 1 scenario.

## Status table

| id | status | evidence |
|---|---|---|
| D2-S1, Arch S5 (reopened) | **open** | The verbatim scenario, `Simulation(world_of(sim))`, is refused, and the test is red with `adopt` deleted (run). The same two-owner state is reachable through a new `World` over the live grid (D3-S1, verified). The constructor still checks nothing about the grid's state. §2 names it the save loader's, but it can't take a loaded tick, and §3 still says frame 0 is "the authored world" (D3-S1). |
| D2-S2 | fixed | §13: "Each `execute` that reaches stage 2 submits one record ... every `physics_every`-th such call". The bridge test's comment matches. The test's name is still stale (D3-N6). |
| D2-S3 | fixed | 3,770 words by `wc -w`. The §7 and §13 cuts drop no contract (D3-N7 is wording only). |
| D2-N1 | fixed | `Deposit.keep`: "at `material`'s current version", matching `deposit.py:101`. |
| D2-N2 | fixed | Checked against 1.3.3 (above). Lesson 37 and OD-A16 say the forward model learns and the LLM reads it, and that it is not NAc credit. |
| D2-N3 | fixed | "the first destroying it and the second applying and destroying nothing". |
| D2-N4 | fixed | A bold "Added by step 5a PR 4a's review" paragraph, after D-B2's, before the superseded list. Token-identical apart from the lead and a colon. |
| D2-N5 | fixed | Every line delta 2 named is rewrapped and none of them is over 120. "It" is now "it". The author's "every line" claim misses `fold.md:70` (D3-N5). |
| A N1 | fixed | `step`'s docstring says a raising publication leaves the tick committed. The rollback comment drops "recur" but makes a new overclaim (D3-N2). The PR 4b checklist row exists. The module docstring still has the old claim (D3-N3). |
| A N2 | fixed | The D-S2 row gives 2.0–2.5×, about 8 ms per extra rebuild at 230,400 cells, and about 170 ms per strike tick at 5×10⁶ cells, as delta 2 measured, plus the 40 against 10. The churn's condition is misstated (D3-N4). |
| Exec N2 (reopened, `rho_cp`) | deferred | Reason: optimize only from a profile, and no B5 profile pass exists yet. Trigger: B5's profile pass. The Step 5a checklist row now holds it outside fold.md, as Exec N2's evidence asked. |
| A N3 | fixed | The marker reads "sees an instant effect: each call that reaches stage 2 is one tick". |
