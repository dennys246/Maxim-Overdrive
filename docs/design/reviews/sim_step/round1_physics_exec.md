# Step 5a PR 3 review: Physics and resolution + Executor

Reviewer: independent, lenses Physics and resolution, and Executor. Tree: the unstaged changes in `.worktrees/sim-laws` on HEAD 3b4c493, plus the untracked `deposit.py`, `exposure.py`, `test_deposit.py` and `test_exposure.py`. Nothing in the worktree was edited. The plants ran from scratch scripts in the session scratchpad (`rev/`).

**Counts: 0 BLOCKER, 3 SHOULD-FIX, 6 NIT.**

## What I ran

- `pytest` on test_exposure, test_deposit, test_simulation, test_laws, test_heat and test_determinism: 229 passed, 1 skipped, 1 xfailed (8.8 s). test_cross_tier: 8 passed, 2 xfailed (4.0 s). ruff, ruff format, mypy (on the four touched core modules) and `lint_standards`: all clean.
- Every number in the commit message that a test or a script could reach. I re-measured them all and each matched (see "Claims" below).
- Plants: the deposit cache across a rollback (S1), the two halves of bar 3 (S2), a first-order dt error against bar 2b, the exposure guards, the replan arithmetic, and the new whole-grid `sphere_overlap` against HEAD's.

## SHOULD-FIX

**S1 `src/simcore/core/deposit.py::Deposit.power`: the weights cache is keyed on `topology_version`, and a rollback reuses version numbers.**
- `CellStore._roll_back` restores `_topology_version`, but the Deposit's cache keeps whatever it built inside the window that rolled back.
- The failure sequence:
  1. A physics step destroys cell A. The version becomes v+1, and `power()` caches weights for that topology.
  2. The step then raises. The window rolls back to version v. `simulation.py` documents this path as "a physics step that raises".
  3. Before the next physics step, a strike or a `place` edits cell B, which moves the version to v+1 again.
  4. The next step's first `power()` hits the stale v+1 entry, so the fire deposits as if A were gone.
- Demonstrated in `rev/plant_cache.py`: after a rollback and a different edit, `Deposit.power` differs from the reference by up to 74.8 W in a cell.
- This breaks §7's rule that "a cache's contents are a function of state". Once PR 4 builds the cache eagerly on load, it also becomes a replay divergence.
- Fix, unverified: clear the Deposit's caches whenever the world's window rolls back (for example a rollback hook on the grid), or key the cache on an epoch that is never reused. The conductance cache §7 plans for PR 4 has the same hazard.
- Add a test that rolls back and then edits differently.

**S2 `tests/test_cross_tier.py::test_the_splitting_bar_fails_on_an_order_sensitive_pair`: the plant can't show that either half of bar 3 can fail on its own.**
- Bar 3 has two checks: the two orders give one class, and each order passes `same_class_under_refinement`.
- The planted pair fails both at once. Forward it gives (0, 0.0, 1.0) at refine 1 and 4. Reversed it gives (None, 1.0) at refine 1 and (0, 0.0) at refine 4.
- In `rev/bar3.py`, `_splitting_holds` with the refinement half deleted still returns False, and so does it with the order half deleted. Neither deletion turns the test red. That breaks "prove a guard by deleting what it guards".
- Fix, unverified: add two plants.
  - One that is order-sensitive but stable under refinement, for example a clamp whose threshold the source crosses only in the forward order, with its count independent of the substeps.
  - One that is order-consistent but sensitive to refinement.

  Then show each one going red with its half deleted.

**S3 `tests/test_cross_tier.py::_observables` and `test_each_scenario_observable_is_time_converged_at_the_shipped_refine`: bar 2b covers fewer scenarios than the claim.**
- The test and the commit say "each scenario observable". The gate covers six observables of three scenarios: the burn, the two burn times and the fierce fire.
- Not covered:
  - `test_a_small_fire_changes_nothing_at_any_rig`, whose outcome is a threshold;
  - `test_a_fire_that_has_burned_its_fuel_stops_heating`;
  - every scenario in `test_act_validation.py`, which the commit counts under bar 2;
  - the 0.05 m grid under `MAXIM_OVERDRIVE_ALL_TIERS` (parametrized on `FAST_SPACINGS` only).
- Failure scenario: the fiercest allowed fire in act_validation could flip class between refine 1 and 4, and no gate would see it.
- A missing onset (`None`) at refine 4 raises `TypeError` in the bars dict, not an assertion with the bar.
- Fix: extend `_observables`, or narrow the claim and record the rest as a deferred row.
- Plant I ran (verified): with thermal damage's dt multiplied by (1 + dt/3), a first-order error, the gate goes red at 0.2 m on the movement check and at 0.1 m on the precondition (the peak exceeds the flame temperature). So the gate can fail.

## NIT

- **N1 `world.py::World.advance`** accepts a step of zero or negative length and moves time backward. `advance(-1.0)` left `time_us = -1_000_000` with `turn = 1`. Before this PR, `run_physics` returned before moving the clock. Only `Simulation` calls it, with a positive step, and PR 4 retires it, but "refuses a step that isn't a whole number of microseconds" should refuse ≤ 0 too.
- **N2 `simulation.py::Simulation._physics`** passes the interval through a round trip: integer microseconds to float `physics_seconds` to `round(seconds * 1e6)` in `World.advance`. It is safe today, because both sides divide by 1e6. But §3 says "in integers": pass `interval_us`. Also, `World.advance` doesn't check that `exposure.of_ticks * tick_us` equals the interval, so a mismatched caller would scale the energy silently.
- **N3 `stepping.py::substep_loop`:** the replan trigger `limit < dt` compares against the refined dt. Take refine 4 and a tightening that lands between the refined dt and the unrefined one. The refine-4 run doesn't replan, so its remainder is no longer 4× the new stability count, while the refine-1 run does replan. The refine-1-against-4 study then isn't a factor of 4 after an edit. §8 says this is unreachable on shipped data; record it, or trigger the replan on the bound.
- **N4 `test_laws.py::_reference_advance` and `test_deposit.py::_reference_power`** call the new `World._power_field` and `deposit.sphere_overlap`, so neither is a frozen pre-PR-3 reference for the deposit. I checked the new whole-grid `sphere_overlap` against HEAD's over 120 random spheres at 0.2, 0.1 and 0.05 m (`rev/cmp.py`): 0 mismatches, so there is no bug. But nothing in the tree pins it. Freeze HEAD's `sphere_overlap` in the test.
- **N5 Stale docs:**
  - `docs/architecture.md` (Known gaps) still says crate "0.55 at 0.2 m". The gate's 6 s turn now gives 0.539; P = 0.5 s gives 0.550.
  - `docs/design/fire_solid.md:26` still describes today's step as 4, 16 or 64 substeps under a `TEMPORARY` marker.
- **N6 `test_heat.py::test_a_replan_takes_the_rest_from_counts_not_from_a_running_sum`:** the docstring says the planted sum "took 11 and one sliver". It takes 11 even substeps: 0.5 − Σ9·0.05 over the bound is 10.000000000000009, and the ceiling gives 11, for 20 in all. There is no sliver.

## Checklist

- **The fixed-step rule:** `n = refine·max(1, ceil(P/bound))` and `dt = P/n`, as in §8. `refine < 1` is refused both in `SimConfig` and in `substep_loop`.
- **The replan:** the rest comes from counts. `(planned − taken)·dt` is verified: 0.05/0.005 = 10.0 exactly, while the running sum gives 10.000000000000009, which takes 11. The `min(dt, seconds − elapsed)` clip is gone, correctly.
- **The floor's removal is complete:** `min_substeps`, `FLOOR_AREA_M2`, the marker, the roadmap row and `TURN_SUBSTEPS` are all gone from `src/` and `tests/`. Only the test's `_retired_floor` reference and the doc mentions remain (N5).
- **The digest break is the intended one:**
  - With refine equal to the floor's count, the tuple matches the reference byte for byte every turn, through a fire and a strike that destroy cells. The tests are green, and I reproduced it at 0.2 and 0.1 m.
  - At refine 1 a 6 s turn takes 1 substep, and the state differs from the reference.
  - This holds because stability's count is 1 at the 6 s turn (bounds 240, 60 and 15 s), so refine × 1 equals the floor's count. The reference shares the new deposit (N4).
- **`source_exposure` against §3:**
  - Live share = T − max(since, start) + 1; closed share = t − max(since, start). Both are right for mid-interval ignite, douse and replace, and for values carried over from an earlier step.
  - A step with no changes gives `ticks/of_ticks` = 5/5 = 1.0 exactly, so the wrap test keeps its bits. It does, because SCHEDULE's tick-30 douse and re-ignite set an equal value, which stays live.
  - Plants matched the commit: dropping the `ticks > 0` guard turns only the first-tick test red, and dropping the clip on live values turns the standing-on test red.
- **The deposit's box:**
  - The padding is right. A sample counts only when i·dx ≤ c + r and i > (c − r)/dx − 1, and one cell on each side covers rounding.
  - The fallback cell is inside the box, because `cell_of` refuses points outside the grid.
  - It is bit-exact, since overlap values are multiples of 1/64. The 200-example Hypothesis test is green.
  - Each per-share term `p·(k/n)·w/total` with k = n is the old `p·w/sum` bit for bit.
  - The cache keys are right for a re-ignite, a new radius and a version bump, apart from S1.
- **Integer time:** time is stored in integer microseconds and only derived as seconds. It moves inside the window and rolls back with it. 3 × 0.1 s reads 0.3. A non-integral time is refused (`Refused` is a ValueError).
- **Bars:**
  - Bar 1 (verification, at 0.1 m, P against P/8): 1.1456e-5 against 3.4117e-3, and at 0.2 m 1.0205e-5 against 1.2866e-2. Both verified. The commit records its proof that the bar can fail, at P = 400 s; I didn't re-run it.
  - Bar 2b is verification, with verify_harness §4 as its source. It can fail (my plant), but its scope is short of the claim (S3).
  - Bar 3 is verification, with splitting §6 rule 4 as its source. The forward and reversed orders give one class at both spacings. Its can-fail proof doesn't separate its two halves (S2).
- **The late-burn gate:**
  - At the 6 s turn, one substep: 137/104 below 0.7 and 152/134 below 0.5.
  - At P = 0.5 s: 138/104 and 152/135.
  - Both verified. The gate stays strict-red (XFAIL), and its reason states the numbers of the path the gate runs.
- **Nothing moved or loosened:**
  - Onset is 94/92 as before. Heat's closed-form tests are green with unchanged bars, and the conservation test is still held to 1e-9.
  - The time assert went from approx to exact, which is tighter.
  - No band was widened. The xfail reason's numbers are re-measurements, not a looser bar.

## Claims in pr3_msg.txt

- **Verified:**
  - bar 1's numbers and its ratio of about 300;
  - every bar 2b number at both spacings;
  - the P = 0.5 s numbers: crate 0.5502 and 0.5507, and 138/104 and 152/135;
  - the 137/104 and 152/134 late-burn numbers;
  - onset 94 and 92;
  - bar 3's three-part class, the same for both orders (bar 3 is green);
  - the deposit and exposure behaviour, and the deletion proofs for the guard, the clip and the replan arithmetic;
  - "sorted accumulation breaks only with three or more sources" (with two, 0 + a + b = 0 + b + a exactly);
  - the 0.3 s claim.
- **Overstated:**
  - "each scenario observable" (S3);
  - "a planted pair … is caught" as the proof that bar 3 can fail (S2: caught, but either half alone would also catch it);
  - "the pre-tuple, pre-PR-3 reference" and "the frozen PR 2 reference's bits" (N4: both use the new deposit or `sphere_overlap`; I found them equal by measurement).
- **Unverified, not re-run:**
  - the bar 2 claim at P = 0.5 s for every act-validation scenario and every red gate. There is no committed reproduction for it;
  - "no shipped test has three overlapping sources";
  - the planted-floor and box-padding deletion counts (5, 10 and 11).
