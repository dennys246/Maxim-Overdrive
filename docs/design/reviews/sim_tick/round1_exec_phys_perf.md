# PR 4a round 1: Executor, Physics and resolution, Performance

Diff reviewed: `git diff bfb12f8 336eee8` (commit 336eee8). Every run below used `git archive` copies of 336eee8 and
bfb12f8 in a scratch directory, with the worktree's interpreter (`-I`, the copy's `src` first on `sys.path`, checked
by printing `simcore.__file__`). Nothing in the worktree was edited. Note: during the review the worktree's HEAD moved
to c721850 and has uncommitted edits to `physics.py`, `heat.py`, `grid.py`, `simulation.py` and others (the author's).
This report covers 336eee8 only. The probe scripts are in `round1_scripts/` next to this file.

**Counts: BLOCKER 0, SHOULD-FIX 3, NIT 4.**

## SHOULD-FIX

### S1. No test holds heat's caches to forgetting on a rolled-back tick. Delete that, and state silently diverges
`src/simcore/core/heat.py::HeatState.forget`, `src/simcore/core/physics.py::Physics.forget`,
`tests/test_simulation.py::test_a_rolled_back_tick_leaves_no_cache_a_later_state_reuses`

The rollback test swaps `_Raises`, a stateless law, in for heat. It then asserts `_states["heat"] is STATELESS`, so
heat's face-conductance cache and its deposit never exist in the test. Only `_bounds == {}` is checked.
`tests/test_deposit.py` (around line 155) says "tests/test_simulation.py holds that", meaning the wiring from
`Physics.forget` to the deposit. That claim is false.

- Mutation A: in `HeatState.forget`, replace `self._faces = None` with `pass`. `tests/test_simulation.py`,
  `test_laws.py`, `test_deposit.py`, `test_heat.py` and `test_determinism.py` give **230 passed, 1 skipped**.
- Mutation B: in `Physics.forget`, replace `state.forget()` with `pass`. The rollback, forget, cache and deposit
  tests in `test_simulation`, `test_deposit` and `test_laws` all pass (18 of 18).
- Failure scenario, run as `round1_scripts/stale.py`:
  1. Heat runs at the real `HEAT`, with a `damage.thermal`-named law that raises once.
  2. Tick 5 strikes point A and runs physics. Heat rebuilds its faces at `material` version v+1. Then the law
     raises, and rollback restores version v.
  3. A later tick strikes point B, which also lands on version v+1.
  4. On 336eee8 the temperatures equal those of a run that never failed (`True`). Under either mutation they differ
     (`False`): heat runs on the conductances of a crater that doesn't exist.

The commit lists "no cache eviction on a rolled-back tick" among its deletion proofs, but that proof covers only the
bound cache. The cost is small: the rollback test needs the real `HEAT` (put the planted raise in `damage.thermal`),
and should assert that heat's `faces` and the deposit's entries are empty after the rollback, or compare bits
against a run that never failed, as `stale.py` does. That fix is unverified as a test. The scenario itself is
verified.

### S2. `REGION_GONE` now decides an agent-visible refusal from cells, and the decision flips with grid spacing
`src/simcore/core/applier.py::Applier._check_region`

"Gone" is now `not (regions[region].cells & grid.solid).any()`, a binary decided on whether any cell survives, with
no margin. Destruction (strike or thermal) removes cells in spacing-dependent amounts, so the same record sequence
can be refused at one spacing and accepted at another.

Measured (`round1_scripts/gone2.py`) on a 1.2 m wood cube aligned to the 0.2 m grid, struck repeatedly at the
centroid with `energy_j = 2e7` and `sigma_m = 2.0`: the first refusal is strike **29 at 0.2 m, but strike 30 at
0.1 m and 0.05 m**. So strike 29 returns `region_gone` to the agent at the coarse grid and succeeds at the truth
grid. Other sizes and energies tie (for example 0.4 m and 0.8 m at 2e7 J; every size at 5e7, 1e8 and 2e8 J).

Before this commit, gone could only come from a later paint, which is construction and authored geometry aligned to
the 0.2 m grid. This commit makes it depend on destruction. The verification rule (world_model §1.1, CLAUDE.md:
"binary outcomes keep a band near their threshold… gated with an outcome margin") asks for either a margin-gated
test or a Known gap with these numbers. The commit has neither. The applier's own docstring explains why reach must
not be judged from cells ("would accept a strike at one spacing and refuse it at another"). That reasoning applies
here too, and the refusal code is what the agent is told.

The definition of gone (cells, volume in metres, or an outcome band) is a design call for the owner. I don't propose
one.

### S3. `WorkCounters.cells_copied` is computed from a formula and undercounts actual cell copies by about 2.75×
`src/simcore/core/simulation.py::Simulation._run` (`work.cells_copied += prod(shape) * _CELL_FIELDS`)

The counter adds 4 fields × cells once, when a cell window opens. It is not counted where copies happen. On one
physics tick at 0.1 m on the T3 tile (n = 1), `round1_scripts/copies.py` counted these full-grid copies in
`grid.py`:
- 5 `ndarray.copy` calls: 4 when the window opens, plus 1 revocation copy (temperature, after heat's narrowed
  block);
- 6 `frozen()` calls, which copy through `tobytes`: 4 when the window commits, plus 2 read-only views (material, and
  temperature after its revocation).

That is **11 full-field copies, about 10.3 MB, against the 4 fields (921,600 cell-fields) the counter reports**.
cProfile over 600 ticks agrees: 720 `tobytes` and 600 `copy` calls, about 12% of tick time at 0.1 m (with
profiler overhead). sim_core §10 names this counter "cells they copied", and B5's budgets will read it, so a budget
would be set against about a third of the real copying, and growth in revocation copies (each extra substep or law)
would be invisible to it.

The test `test_the_work_counters_hold_their_exact_values…` asserts `4 * cells`. That is the same formula restated,
so it can't catch the drift. This is not a regression in copying: bfb12f8's window machinery copies the same way.
The defect is that the counter claims an exact count it doesn't make.

## NIT

- **N1. Bar 7 at 0.2 m isn't reproducible from this bench**
  (`_durable/sim-replay/bench_4a.py`, 8 repetitions of about 15 ms). Five runs of 4a against PR 2 at 0.2 m gave
  12.6/17.4, 16.1/17.6, 13.6/17.5, and mid-burn (warmed to 600 s) 16.8/17.6, 17.0/17.1 and 16.1/16.5 ms. The ratio
  ranges from 0.72 to 0.98. The commit's 8.2 against 10.7 (0.77×) sits inside that noise.
  - At 0.1 m the gated half holds robustly. Early in the burn: PR 2 276.7 ms, bfb12f8 268.7 ms, 4a 88.4 ms (0.32×).
    Mid-burn at 600 s, after onset: 284.8 against 99.8 ms (0.35×). The author's 0.35× matches.
  - Method check: the bench times seconds 6 to 12 after ignition, the caches' best case. I re-measured mid-burn
    because of that. `round1_scripts/midburn.py` shows that on this tile at 0.2 m only one face rebuild happens
    between 60 and 1200 s, so the caches keep hitting during the burn. The method isn't flattering at 0.1 m.
  - Record the 0.2 m figure from more repetitions or a longer window.
- **N2.** `heat.py::substep` and `stable_dt` recompute `rho_cp = materials.rho_cp[grid.material]` (an O(cells)
  gather) on every substep. It is a function of `material` alone and could sit with the faces in the same
  version-keyed cache. Its cost is unmeasured and probably small next to `substep`'s 23 ms per call under the
  profiler (unverified).
- **N3. The douse exemption is a refusal contract the agent depends on, but it lives only in the applier's comment
  and one test** (`applier.py::Applier.apply`, `gone_ok=burning`). sim_core §5.1, which owns `REGION_GONE`'s
  meaning, doesn't state it. Under the one-owner rule, §5.1 should carry it. The behaviour itself is right: a
  struck-out crate's fire must stay doused-able, and `NO_REGION` and `NOT_SOLID` still apply.
- **N4. The cache keys differ from the design text.** sim_core §7 keys face conductances, and heat's bound, "per
  `topology_version`". The code keys both on `field_version("material")`. The code's key is finer, and I checked it
  is sound: `material` is in `_EDITED_ONLY`, so it is never handed writable and is bumped only by a changed
  `_set_cells`. But the contract and the code now say different things. One of them should change.

## Not findings (checked)

- **Bit identity apart from the `REGION_GONE` change: reproduced independently.**
  - My own schedule (`round1_scripts/ident.py`) on the determinism scene, 1800 ticks: ignite and strike at tick 1;
    a wall strike at 7; douse and ignite on physics tick 30; ignite and douse at 31; then strike 95, douse 200,
    ignite 201, strike 202, strike and ignite 400, douse 555.
  - The digest of the four channels, the region masks and the sources is equal between bfb12f8 and 336eee8: at
    0.2 m `d5c424ce16d5732c` for both, at 0.1 m `4db72b0a2980f8e1` for both.
  - My first schedule re-ignited the crate at tick 201 and diverged only there. The crate had burned to nothing
    under 500 kW, and 4a refuses that ignite `region_gone`, the intended change, as the commit says of its own first
    schedule.
- **Suite on 336eee8.** The 12 touched test modules: 700 passed, 5 xfailed (strict), 4 skipped (the tier). One
  failure, `test_validation.py::test_every_shipped_data_file…`, comes from my archive copy having no `.git` (`git
  ls-files` exit 128). It is not a code failure.
- **Mutations that go red, as claimed.**
  - Dropping `& grid.solid` from the gone check turns 2 tests red: the second strike, and the douse.
  - Forcing `gone_ok=False` turns the douse test red.
  - `World.writing` always copying cells, and `Simulation._run` always passing `cells=True`, each turn
    `test_ownership.py::test_a_window_that_changes_only_the_sources_copies_no_cells_but_still_publishes_a_frame` red.
- **Bars restated without loosening.**
  - Bar 2b's `bars` dict and its `< bar / 4` test are byte-identical to bfb12f8's. `TIME_TOL`, the 10% onset
    spread, `BADLY_BURNED`, the 0.99 wall and small-fire bars, and `WOOD_FLAME_C` are unchanged.
  - Times are now resolved to 0.5 s instead of 6 s, which is stricter, not looser.
  - The red gates stay strict with `raises=AssertionError`, and their preconditions raise `RuntimeError`.
  - Bar 3's plant test still asserts `not _splitting_holds` and each half alone. `_refinement_alone_fails`'s
    threshold moved from 3.0 to `STEP_S / 2`, the same half of the physics step.
- **Rollback mechanics.**
  - `_open_window` saves a copy of `_versions` and `_roll_back` restores it.
  - `on_roll_back(physics.forget)` is registered once per `Simulation`.
  - The exposure is worked on `copy()` and installed only after the `with` exits.
  - The clock and frames move only after `_run` returns.
  - A raising tick returns no report, so the `rebuilds` diff never reads a half tick.
- **Deposit keys.** `(point, radius)` for the overlap, plus `topology_version` for the weights, as §7 specifies.
  `forget` is wired through `HeatState.forget` (but see S1: nothing tests the wiring).
- **Quiet ticks** open no window, copy nothing and publish nothing, and cost only `Work()` plus two `builds()` dicts.
  A ticks-only tick (fires and douses) uses `holding()`, which copies no cell.
- **Frames.** `FrameFeed.publish` refuses a tick that isn't after the latest. `time_us = tick * tick_us` is an
  integer, and seconds are derived.
- **Bridge.** `SteppingPort` steps one tick per submit, and the cross-tier and act-validation outcome bars read
  frames or go through `act`/`record`, never the bridge (§13).
- **Not run:** the 0.05 m tier (`MAXIM_OVERDRIVE_ALL_TIERS`), so the commit's "0.05 m passes" is unverified by me,
  and the full `scripts/prepush.sh`.
