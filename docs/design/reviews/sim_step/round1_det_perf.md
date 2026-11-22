# Step 5a PR 3 pre-push review: Determinism and Performance lenses

**Under review:** unstaged working-tree changes in `.worktrees/sim-laws` on PR 2's staged fold (HEAD 3b4c493),
including the untracked `src/simcore/core/deposit.py`, `exposure.py` and their tests. Nothing in the worktree was
edited.

**Method:** I made two copies outside the worktree. `pr2/` is the index, from `git checkout-index -a --prefix`. `pr3/`
is the working tree, copied with `cp -R`. Each copy ran with `PYTHONPATH=<copy>/src:<copy>` on the worktree's
`.venv`. Scripts are in `scripts/` beside this file: `bench.py` and `bench_tile.py` (step cost), `parts.py` (cost by
component), `prof.py` (cProfile), `burn_hits.py` (cache hit rate, cached against uncached bits, hash seeds) and
`rollback_plant.py`. Timings are medians, with the minimum where given, on this Mac. The T3 tile is
`reviews/sim_core`'s, from `perf_scripts/measure.py::tile`: 12 × 4 × 4.8 m, one 60 kW fire on the crate.

**Counts:** 0 BLOCKER, 2 SHOULD-FIX, 3 NIT.

## Performance: measured

Cost of 6 world seconds on the T3 tile:

| Path | 0.2 m | 0.1 m |
|---|---|---|
| PR 2 `World.advance(6.0)` (bar 7's "today": 4 / 16 substeps) | 6.9–7.1 ms | 118–128 ms |
| PR 2 `Simulation`, 60 ticks (the floor applied per 0.5 s call: 48 / 192 substeps) | 85.5 ms | 1,340 ms |
| PR 3 `Simulation`, 60 ticks (12 substeps), deposit cache on | 16.3 ms | 112–113 ms |
| PR 3 `Simulation`, 60 ticks, deposit cache cleared on every call | 25–32 ms (noisy) | 118–138 ms |
| PR 3 `World.advance(6.0)` (1 substep) | 1.4 ms | 9.4–10.4 ms |

- **Dropping the floor works.** On the shipped `Simulation` path at the 0.1 m truth grid, PR 3 is about 12× cheaper
  than PR 2: 113 ms against 1,340 ms per 6 world seconds. At 0.2 m it is about 5× cheaper. Quiet ticks are
  negligible: 12 physics steps of about 9.4 ms account for the whole 113 ms.
- **The deposit cache's hit rate is 99.6–99.8% and it saves little.** Over a 900 s two-fire burn through
  `Simulation`, with destruction:
  - at 0.2 m, 8 weight rebuilds and 2 overlap builds in 1,800 calls;
  - at 0.1 m, 16 weight rebuilds and 2 overlap builds in 1,800 calls.

  The rebuilds come from the topology bumps, 4 and 8 of them. A cached `Deposit.power` costs 0.02 ms. The uncached
  path costs about 0.5 ms per step at 0.1 m on the tile, roughly 5% of a step, because the bounding-box overlap already
  made the rebuild cheap.
- **Cached and uncached runs are bit-identical on the shipped path.** The burn's final temperature, integrity and
  material hash matched (0.2 m `8d5d931a…`, 0.1 m `4def691c…`). Verified.
- **The predicted cached figure of about 0.7× is not reached at 0.1 m: 0.88–0.96× today's `advance(6.0)`.** At 0.2 m
  the cost is **2.4×**, against the 1.4–1.6× that §7 records as the expected cost. A physics step at 0.1 m breaks down
  as:

  | Component | ms | Share of step |
  |---|---|---|
  | Whole step | 10.2 | 100% |
  | `heat.stable_dt` | 4.3 | 42% |
  | `_face_conductances` inside `substep` | 2.5 | 24% |
  | `damage.thermal` | about 0.5 | — |

  At 0.2 m the step is 1.33 ms, of which `stable_dt` is 0.55 and the conductances 0.35. The design's 0.7× assumed
  that the power field *and the stability bound* were cached (`perf_scripts/step_shape.py`: `cached = 12 * (s +
  dg)`). PR 3 ships only the deposit cache. The §7 cache that matters is face conductances and `stable_dt` per
  `topology_version`, and it isn't in PR 3: the checklist ties `stable_dt`'s cache to `bound_reads`, PR 4's. Those two
  caches would take the step to about 3.5 ms at 0.1 m, roughly 0.35× today, and to about 0.43 ms at 0.2 m, roughly
  0.75×. That is an estimate from the measured components, not a measurement of an implementation.
- **The 2.6× / 4.2× uncached slowdown predicted in design review does not occur.** At `n` = 1 the fixed step runs 12
  substeps per 6 s, not PR 2's 16 per call. Even with the deposit cache cleared, PR 3 at 0.1 m costs 1.0–1.1× today.
  It is "closed" by the floor's removal and the bounding box, not by the caches.

## SHOULD-FIX

### S1. `deposit.py::Deposit.power`: a rolled-back window leaves a weight entry keyed on a `topology_version` that a different later state reuses, and the next call returns the wrong power

**What's wrong.** §7 says "a cache's key is the values its result reads". The weights read `grid.solid[box]`, and
`topology_version` stands in for it. But `CellStore._roll_back` restores `_topology_version` with the cells, so a
version number does not name one state. If a window edits the cells (version v → v+1), calls `power()` and then
raises, the cache keeps `(p, r, v+1)` for the rolled-back cells. If a different edit then moves the version to v+1
again before the next `power()` call, that call hits the stale entry.

**Failure scenario, planted (`rollback_plant.py`, verified):**
1. Destroy cell A inside a window.
2. Call `power()`.
3. Raise, so the window rolls back. The version is back at v.
4. Destroy a different cell B, which takes the version to v+1.
5. Call `power()`.

The result is not equal to a fresh `Deposit`'s: the largest difference is 74.8 W. It puts 66 W into cell B, which is
now air, and misses cell A's neighbours.

**How the shipped path reaches it.** `run_physics` refreshes power after a substep that edited the world, when
`n` > 1: `substep_refine` above 1, or a replan. If a later substep raises, the window rolls back. `Simulation`'s
docstring treats continuing after a raised physics step as a supported state ("leaves that tick's records applied").
After that, a strike record in the next tick bumps the version before physics runs.

**Why it matters beyond PR 3.** PR 4's conductance and `stable_dt` caches per `topology_version` inherit the same
hole. A stale `stable_dt` there would be an unstable step with no error.

**Fix (unverified).** Two options:
- clear or roll back the deposit's caches when the window rolls back, through a grid hook beside `on_close`;
- key the caches on a generation counter that a rollback never restores.

Either way, add the plant above as a test that is red today.

### S2. §7 and §11 bar 7: the recorded expected cost is false at PR 3, and no measurement is recorded

**What's wrong.** §7 states "5a costs 1.4–1.6× today at 0.2 m, an expected cost that bar 7 records". PR 3 measures
2.4× (above). At 0.1 m, PR 3 passes bar 7's gate only narrowly, at 0.88–0.96×, which is inside run-to-run noise
(today's median spread alone is 118–128 ms). PR 3 is the PR that changes the step's cost, yet the diff records no
bar 7 measurement, no B5 row, and no note that the 0.7× and 1.4–1.6× figures depend on the `stable_dt` and
conductance caches still to land.

**Failure scenario.** PR 4 adds the digest, about 1.7 ms per writing tick at 0.1 m (§9), which is about 20 ms per 6 s
on physics ticks alone. That turns 0.96× into about 1.1×, and bar 7 fails at 0.1 m unless the conductance and
`stable_dt` caches land in the same PR. Meanwhile any B5 baseline taken at 0.2 m starts from an unexplained 2.4×.

**Fix (measured, as above).** Record these numbers in the hand-off or B5 now, with `scripts/bench_tile.py` as the
method, and state that the cached targets need the per-`topology_version` conductance and `stable_dt` caches. Then
land those caches no later than the digest in PR 4.

## NIT

- **N1. `simulation.py::Simulation._physics` and `world.py::World.advance`: integer time passes through a float.**
  `SimConfig` holds whole microseconds, but `_physics` passes `physics_seconds`, a float. `advance` then rebuilds
  `interval_us = round(seconds * 1e6)` and checks the round trip. It is exact for every config `SimConfig` can hold
  below about 2⁵³ µs, so nothing diverges today. Still, §3's "nothing stores time as a float" is kept by a check, not
  by the types. Passing `interval_us` and deriving seconds once for the laws would remove both the round trip and the
  `ValueError` path.
- **N2. `deposit.py::Deposit.power`: the per-share energy is `power * (ticks / of_ticks) * P`, not `k · tick_us ·
  power` "in integers" (§3).** It is deterministic: one expression, in sorted order. But `2/5` is inexact, so the
  closed form holds only to rounding, which is why `test_exposure.py` uses `approx`. Either reword §3 ("counted in
  integer ticks") or say in the docstring that the fraction is the only float.
- **N3. `deposit.py::Deposit`: cached arrays are writable.** `_overlaps` and `_weights` hold plain numpy arrays, and
  the `weights = ... else frac` fallback aliases the overlap. Nothing mutates them today, but one future in-place op
  (`w /= total`) would poison every later hit silently. Wrapping them with `simcore.core.readonly.frozen` makes that
  loud. The cost is nil, since they are built at most once per topology bump.

## Determinism: checked and sound

- **Sorted-key source sum.** `standing` sorts keys. `SourceExposure.step` and `closed` sort by key with a stable
  sort; closed segments are appended in tick order and come before live ones per key, and a key can close only one
  value per tick. Dict insertion order in `_live` reaches no result. The three-source test, with its order made
  visible, guards it. Over a 900 s burn at 0.2 m, the final state was identical under `PYTHONHASHSEED` 0, 1 and 12345
  (verified).
- **Cache keys.** Overlaps are keyed `(point_m, radius_m)`. The grid's dx and shape are fixed per `Deposit`, and
  ±0.0 hash and compute alike. Weights are keyed `(point_m, radius_m, topology_version)`. Power is not in the weights,
  correctly. The key misses only the rollback case (S1). Each call evicts down to the current shares, so the
  contents are a function of state except after S1's rollback.
- **Integer time.** `CellStore._time_us` is an int, set through `whole_number`, saved and restored with the window,
  and `time_s` is derived by division. Time moves outside the narrowed writer. Nothing in the laws reads it.
- **Exposure is cleared per physics step.** `step()` empties `_closed` and moves `_start` before `advance`. A raise
  then loses that step's exposure, as documented, so the documented interim is honest. Tick counting is correct:
  - closed `tick − max(since, start)`;
  - live `+1`;
  - a value replaced at the step's first tick contributes 0;
  - construction stands from tick 1.

  Exposure is not yet a digest member or saved: lesson 33 and the docstring name that for PR 4, so bar 4 can't see an
  exposure divergence until then.
- **Float accumulation.** Box-sliced `+=` adds in the same order as the whole-grid reference, and the sums of
  multiples of 1/64 are exact. Cached and uncached runs are bit-identical over a full burn with destruction.
- **The `substep_loop` replan** computes the remainder from counts. The removed `min(dt, seconds − elapsed)` leaves
  no running sum.
