# PR 4a (`phase1/sim-replay`) delta round 4: the delta-3 fold, read from the tree

**Lenses:** Executor, Architecture, Wire integrity, Determinism and replay.

**Reviewed:** `git diff afda61c 3e61f70`, `git show -s 3e61f70`, `delta3.md`, and the "Delta 3" table in
`fold.md`. I set every status by reading the tree, not the table. I also checked the merge `94ca301` (origin/main
#48) with `git diff 3e61f70 94ca301 --stat`. Its 12 files don't overlap any file the branch changes since its merge
base with `53cd42c` (`comm -12` of the two name lists is empty).

**How it was run:** I used a copy of `94ca301` at `<scratchpad>/delta4/tree` (`diff -rq` against the worktree:
clean, apart from caches). The interpreter was the worktree's venv under `-I`, with the copy's `src` and root first
on `sys.path`, and `simcore.__file__` resolved into the copy.
- **Tests:** `test_simulation`, `test_ownership`, `test_sem_bridge`, `test_exposure` and `test_constructors` gave 218
  passed. `test_frames`, `test_act_validation`, `test_determinism`, `test_laws` and `test_validation` gave 508
  passed, 1 skipped, 3 xfailed and 1 failed. The failure is
  `test_every_shipped_data_file_is_at_its_formats_current_version`, which runs `git ls-files` and fails because the
  copy is not a repository. It is an artefact of the copy, not a finding.
- **Lint:** after a throwaway `git init` (removed afterwards), `scripts/lint_standards.py` gave PASS with 0 findings.
  Ruff check and format are clean on the changed Python files.
- **Mutations:** three, each restored and checked with `cmp` against the worktree. They are listed under D3-S1, D3-N1
  and D4-N1.
- **Scripts:** in `.worktrees/_durable/sim_tick_review/delta4_scripts/`: `run_tests.sh`, `mutate.py`,
  `mutate_after_physics.py`, `probe_routes.py`, `probe_warm_retry.py` and `probe_fork.py`.
- **Not run:** the full suite, the 0.05 m tier, mypy, import-linter and the gate.

## Counts

**New findings: 0 BLOCKER, 0 SHOULD-FIX, 4 NIT.**

**Statuses set (10 rows; the first row splits into three ids):** 9 fixed, 1 open (Arch S5).
- **Differs from the author:** the D3-S1 row folds D3-S1, D2-S1 and Arch S5 into one fix. D3-S1 and D2-S1 are fixed.
  Arch S5 is still **open**. Its ask was that the constructor refuse a grid that isn't at construction. The
  constructor still accepts a stepped state at tick 0 and publishes it as frame 0 (D4-N2). No marker or checklist row
  defers it.
- Every other row matches the fold's claim. Two carry caveats: D3-N1 (D4-N1) and D3-N4 (the spacing).

## New NIT

### D4-N1. The retry test pins only the law-tuple refusal, so moving the adoption above `warm` stays green
**Where:** `tests/test_simulation.py::test_a_construction_that_raised_leaves_the_cells_free_for_a_retry`;
`src/simcore/core/simulation.py::Simulation.__init__`.

The constructor's docstring says the cells are adopted "once everything that can refuse has run". Two things can
refuse after `Physics(...)`: the law-tuple check (inside `Physics`) and `physics.warm`, which refuses a source
outside the grid ("point (50.0, 50.0, 50.0) is outside the grid (3.0, 3.0, 2.0)"). The test only exercises the
first.

*Scenario (verified, `mutate_after_physics.py` and `probe_warm_retry.py`):* move `world.grid.adopt()` to the line
just after `Physics(world.grid, laws)`.
- `test_simulation.py` gives 57 passed. Nothing goes red.
- A construction whose world has a source outside the grid raises in `warm`. A retry on the same grid with a good
  `World` is then refused: "these cells already have their simulation".
- As shipped, the same retry is accepted at tick 1.

So the test can't tell the shipped order from a regression that breaks D3-N1's own scenario at the second refusal
site.

*Fix (unverified):* add a second case to the test, a world whose source lies outside the grid, then a retry on its
grid.

### D4-N2. Arch S5's residual has no tracking row, and §3's frame-0 rule disagrees with what the constructor accepts
**Where:** `src/simcore/core/simulation.py::Simulation.__init__`; `docs/design/sim_core.md` §2 ("Constructors") and
§3 ("Tick 0 is construction ... publishes the authored world"); `docs/plans/checklists.md` (the PR 4b rows).

§2 now says `Simulation(world)` "adopts a world's cells at tick 0 ... (the loader's tick is PR 4b's)". Delta 3's
fix asked that §2 say both the loader's tick and its frame-0 rule are PR 4b's. Only the tick is named. Nothing in
the constructor checks that the cells are at construction.

*Scenario (verified, `probe_fork.py`):*
1. Light the crate and run to tick 20 (max temperature 28.6 °C).
2. Build `MaterialGrid(g.dx, g.shape, g.materials, material=g.material, ...)` from the stepped grid's arrays.
3. Pass it to `Simulation(World(fork, ...), config=T3)`. It is accepted at tick 1, and frame 0 is published at
   `tick=0, time_us=0` with a maximum of 28.6 °C. That is not "the authored world" §3 promises.

The fork also carries no regions (the grid constructor takes none), so it isn't even a faithful fork. This is not
two owners of one cell store: `frozen` copies, and the fork's windows write only its own copies. It is Arch S5's
unrefused state. Today it is reachable only through public core constructors (tests). PR 4b's loader will be the
first real caller. The only marker that PR 4b owns it is a parenthetical in §2, and no Step 5a checklist row lists
"the loader's tick and frame 0, or a refusal of a non-construction grid" among PR 4b's items.

*Fix (unverified):* add a PR 4b checklist row naming the loaded tick and the frame-0 rule, citing §2 and §3. A
reviewer can then set Arch S5 to deferred with PR 4b's loader as its trigger. Alternatively, make §2 say the frame-0
rule is PR 4b's too. This is within the word budget only if something else is cut.

### D4-N3. A shallow copy of an unadopted grid gives two simulations that share the version table and the gate
**Where:** `src/simcore/core/grid.py::CellStore` (no `__copy__`), `CellStore.adopt`.

`copy.copy(grid)` copies the attribute dict, so the copy shares `_versions`, `_gate`, `_regions` and (until the
first window) `_channels` by reference, while `_adopted` is copied by value.

*Scenario (verified, `probe_routes.py`):*
1. Build a grid, then `g2 = copy.copy(g)`.
2. `Simulation(World(g, ...))` and `Simulation(World(g2, ...))` are both accepted.
3. After 5 ticks of the second, the first's `g.field_version("temperature")` has moved from `(0, 0)` to `(0, 1)`,
   though its cells never changed. The two grids' channels have already diverged.

The first simulation's caches then rebuild, and its work counters (§10) count a change made by another simulation.
So the counters depend on more than the first simulation's own records, which is a Determinism and replay concern
for any work-counter bar. Keys still only grow, so no cache serves stale data.

Copying an adopted grid is refused (the flag is copied). `copy.deepcopy` fails with
`TypeError: cannot pickle 'mappingproxy' object`, which is incidental, not a guard. No code in `src/`, `tests/` or
`scripts/` copies a grid today (searched: `copy.copy`, `deepcopy`, `__copy__`, `pickle`).

*Fix (unverified):* give `CellStore` `__copy__` and `__deepcopy__` that raise, as `loaders.DataPath` defines its own.

### D4-N4. `adopt` is a public call that no scan holds to `Simulation`
**Where:** `src/simcore/core/grid.py::CellStore.adopt`; `tests/test_ownership.py::OWNED_CALLS`.

Any core module can call `grid.adopt()`. A stray call makes every later `Simulation` over those cells refuse. That
failure is loud, not silent, so this is a NIT. `OWNED_CALLS` already holds `as_writer`, `claim` and `constructing`
to their owners, and the one-simulation rule is exactly that kind of rule.

*Scenario:* a PR 4b loader that adopts the grid it builds, "to be safe", before handing it to `Simulation(world)`
makes every load fail with "already have their simulation". Nothing would flag the call site.

*Fix (unverified):* add `"adopt": {"simcore/core/simulation.py"}` to `OWNED_CALLS`.

## Checked, not findings

- **Routes to two simulations over one cell store.**
  - The same `World` and a new `World` over the grid are both refused.
  - `copy.copy` of an adopted grid is refused.
  - `World` copies its sources into its own proxy, so a second `World` shares only the grid, which is adopted.
  - `Scene.build` and `MaterialGrid.empty` build a fresh grid each call. Neither has a cache.
  - The session fixtures in `conftest.py` are the material table and the limits, not grids.
  - `tests/_sim.py` and `tests/_cells.py` never construct a second `Simulation`. `_cells.heat_alone` and
    `physics.strike` run an orchestrator on a bare grid without a `Simulation`.
  - Subclassing `MaterialGrid` to override `adopt` would defeat it, but nothing does, and no guard could stop that
    inside the core.
- **Hidden test dependencies.** The only `Simulation(world)` calls in `tests/` are `test_exposure._run`, which builds
  a fresh world per call, and the two new tests. `test_laws._reference` builds its own grid and never wraps it. Every
  determinism rerun goes through `from_scene`, which builds a new grid each time. Nothing in `scripts/` builds a
  `Simulation`.
- **Adopted cells, other writers.** Adoption guards only the construction of another `Simulation`. Tests still open
  an adopted grid's window directly (`test_act_validation`, `test_frames`, `test_ownership`). In `src/`,
  `imagination._voxelize` opens the window under its `TEMPORARY(phase1/sim-clock)` marker, and `WINDOW_OWNERS` holds
  the openers. This predates the fold and is marked.
- **A refused construction leaves no trace.** A second construction over an adopted, stepped grid runs `Physics`,
  `CellFrame.of` and `warm` before `adopt` raises. The grid's digest, `_copied`, `_versions`, `_rollbacks` and
  `topology_version` were identical before and after (`probe_routes.py`). `warm`'s reads are narrowed under
  `reading()`, whose `finally` clears the narrowing. A `warm` that raises part-way leaves only that construction's
  `Physics` half-warmed, and that object is discarded. Delta 2 already checked that `Deposit.keep` and
  `HeatState.faces` assign at the end.
- **The ownership scans.** `adopt` grants no capability and opens no window, so the token, opener and peek scans
  don't apply. `test_ownership` passes (see D4-N4 on `OWNED_CALLS`).
- **Size limits.** `CellStore` has 11 public methods in its own body (including `adopt`), against a limit of 12, which
  is what `lint_sizes` counts. `MaterialGrid` has 7. `lint_standards` passes. `CellStore` is one method from the
  tripwire.
- **The rollback comment** in `Simulation.step` matches the code:
  - `_roll_back` moves `_rollbacks`, and `field_version` keys on `(rollbacks, count)`.
  - `holding()` moves no version.
  - The `except` branch re-warms at rest.
- **The docstrings.** The module docstring's "before the window commits" agrees with `step`'s docstring. The
  constructor's "a loaded tick is PR 4b's" and "once everything that can refuse has run" match the order of the code
  (but see D4-N1). The `adopt` docstring's "can publish it as frame 0" is accurate: a refused construction builds a
  frame 0 in its own feed but never publishes it.
- **sim_core.md.** It is 3,770 words by `wc -w` at both `afda61c` and `3e61f70`. §4's
  `Simulation(world, *, config: SimConfig, laws=DEFAULT_LAWS)  # a built world, adopted (§2)` matches `__init__`.
- **The §7 cost line** matches its sources:
  - The PR 4a figures, 0.32–0.35× at 0.1 m and 0.72–0.98× at 0.2 m, match `delta2_exec_det_perf_phys.md` (Exec N1
    row).
  - The PR 3 figures, 0.88–0.96× at 0.1 m and 2.4× at 0.2 m, match `reviews/sim_step/round1_det_perf.md` (lines
    41–42).
  - The line now pairs each figure with its grid by the order "at 0.1 and 0.2 m".
- **The churn row** matches delta 2's NIT 2: 20 ticks, 5 radii, `heat/deposit` 40 against 10, unchanged time, and
  the tick-end `warm` keeping only live values. It says "on the same tile" without the 0.1 m spacing, which the
  previous sentence gives. This is minor.
- **The renamed bridge test.** `git grep` finds the old name only in the verbatim reports (`delta2_arch_wire_trust_bio.md:55`
  and `delta3.md:99`). Lesson 37 cites the new name, and its line is within 120 columns. The old simulation test
  name survives only in `delta3.md` and in `fold.md`'s Delta 2 row, which is a historical record.
- **Line widths.** Every added line past 120 columns in this diff is a table row.

## Status table

| id | status | evidence |
|---|---|---|
| D3-S1 | fixed | `CellStore.adopt` holds the flag, and `World.adopt` is gone (`git grep`: no caller). The new test refuses both the same world and `World(world.grid, ...)`. With the adoption deleted (`mutate.py delete`): 1 failed, the two-owner test. §2 no longer calls the constructor the save loader's. |
| D2-S1 | fixed | The verbatim scenario and delta 3's new-`World` variant are both refused. `first` still reaches `(6, 5)` after the refusals. |
| Arch S5 | **open** | The constructor still checks nothing about the cells' state: a grid rebuilt from a stepped grid is accepted at tick 1 with a stepped frame 0 (`probe_fork.py`). §3 says frame 0 is the authored world. No marker or checklist row defers it, and §2 names only the tick as PR 4b's (D4-N2). |
| D3-N1 | fixed | `adopt` is the constructor's last line. With it moved before `Physics(...)` (`mutate.py first`): 1 failed, the retry test. Caveat D4-N1: with it after `Physics`, the test stays green and a `warm` refusal consumes the cells. |
| D3-N2 | fixed | The comment says a cell window's rollback is counted and a tick of fires alone moves none. This matches `_roll_back`, `field_version` and `holding`. |
| D3-N3 | fixed | Module docstring: "a tick that raises before the window commits changes nothing". |
| D3-N4 | fixed | "20 ticks, cycling through 5 radii ... a radius the previous step already used rebuilds", as delta 2's NIT 2 measured. The spacing is only implied. |
| D3-N5 | fixed | `fold.md:70`'s bullet is rewrapped, word for word, with every line within 120 columns. |
| D3-N6 | fixed | `test_the_membrane_steps_only_through_its_port_one_tick_per_call_that_reaches_stage_2`. Lesson 37 cites it. The old name appears only in verbatim reports. |
| D3-N7 | fixed | "measured" and "at 0.1 and 0.2 m" are back, and the numbers match their sources. 3,770 words at both commits. |
