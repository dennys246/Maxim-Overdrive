# The verification harness (step 4): the contract

**Status:** the contract for plan step 4 (`phase1/verify`), 2026-11-21. It holds only what other modules and tests
depend on (CLAUDE.md, "A design document holds the contract"). How each function computes its answer is the code's,
checked by its tests. Sources: `world_model.md` §1.1 and §10 row 3 (E2); `world_v2.md` row 2;
`boundaries.md` layer 8; `research/physics_spike/splitting.md` §6 and `physics_spike.md` (step 4's harness);
`research/hot_surface_spike/preregistration.md` D3.

## 1. What it is for

The truth grid is 0.1 m on every machine; 0.2 m and 0.05 m are verification grids (`world_model.md` §1.1). The
resolution rule becomes the verification rule: **the truth resolution's outcomes agree with the reference
resolution's, within a gated tolerance, and converge from the coarse grid.** The harness is how a test says that,
in one vocabulary, for every law.

## 2. Where it lives

- **`simcore.verify`** (`engine.verify`), in `boundaries.md` §2.2's layer order. It imports nothing from the engine:
  only `math`, `dataclasses`, `itertools` and `collections.abc`. A forbidden contract (`verify-measures-only`) keeps
  it off `simcore.core`,
  `simcore.adapters`, `simcore.protocol` and `maxim`. Nothing in `src/` imports it, tests do: the layers contract
  keeps the engine's lower layers off it, and `verify-ships-nowhere` keeps the game off it.
- **It never builds a `World`.** It receives observables as callables and never constructs state itself. A test
  supplies the state: a law on a grid, or, until step 5a's `Simulation` exists, a `World` scenario. When 5a lands,
  the scenario tests move to `Simulation`, and the harness doesn't change.

## 3. The types (frozen dataclasses)

| Type | Fields | Meaning |
|---|---|---|
| `Run` | `dx_m`, `dt_s`, `steps` | one discretisation of a convergence study: spacing, physics step, step count |
| `Convergence` | `runs`, `values`, `errors`, `orders`, `reference_converged` | what `converges` measured; the flag is None against a closed form |
| `Band` | `edges` (per run), `low`, `high` | where a binary outcome flips, per grid |
| `Agreement` | `spacings`, `values`, `errors`, `spread`, `converging` | one scenario outcome across grids |

`world_v2.md`'s exact performance counters belong to the engine: they arrive with step 5a's `Simulation`, which has a
counter to report, and its budgets (B5), which read them. Every observable returns a plain value.

## 4. The functions

- **`converges(observable, runs, *, exact=None, order_tol=None)` → `Convergence`.**
  - `observable(run)` returns the value.
  - With `exact`, the errors are against it (a closed form); `order_tol` is refused, since there is no reference.
  - Without, the finest run is the reference: errors are against it, and `order_tol` is required.
    `reference_converged` says whether the last two Richardson orders agree within it (the spike: "it must say when
    the reference itself hasn't converged"). A verdict needs two orders, so four runs; with three it is False.
  - `orders` holds the observed order between each consecutive pair, p = ln(e_coarse / e_fine) / ln(r), r the
    refinement ratio.
  - Space and time are refined separately (E2): a space study holds `dt_s` fixed across runs, and a time study holds
    `dx_m` fixed. A `runs` list that changes both raises `ValueError`.
  - A space study's shared step must be time-converged: a quarter of it moves each order by under a quarter of
    that order's bar. Stability at the finest grid isn't enough: for heat's bar (28.85 s at 0.05 m) it gave orders
    of 2.20 and 4.90.
- **`band_gate(outcome, xs, runs)` → `Band`.** `outcome(run, x)` is a binary outcome at control value `x`. The harness
  evaluates every `x`, finds each run's flip point, and refuses an outcome that flips more than once (a coarse grid
  can alias a threshold; bisection would hide it). It reports the band across grids. The test then asserts its
  operating point clears the band by its margin (`world_model.md` §3).
- **`agrees(observable, spacings)` → `Agreement`,** for a scenario outcome that isn't smooth in the
  spacing, so has no order. `observable(dx_m)` returns the outcome; spacings go coarse to fine. It reports the spread
  across grids, each grid's error against the finest, and `converging`: each coarser grid's error is no smaller than
  the next finer one's, with no allowance for the outcome's resolution. That is the
  rule's "converges from the coarse grid"; it is None with two grids. The test keeps its own bar on the spread: "each
  grid within tol of the reference" would let two grids sit 2 × tol apart.
- **`same_class(outcome, spacings)` → `bool`:** one outcome class at every spacing.
- **Agreement studies take spacings, not `Run`s.** A scenario's physics step is whatever `World` takes at that
  spacing. Since step 5a's fixed physics step it is the same at every spacing on shipped data, so these studies refine
  space alone, held time-converged by `sim_core.md` §11 bar 2b. A `dt_s` the study doesn't control would be a label,
  not a measurement.
- **`same_class_under_refinement(outcome, run, factors=(1, 10))` → `bool`.** The splitting test at fixed `dx_m`: the
  same outcome class at `steps` and `10 × steps` with `dt_s` divided to match (`splitting.md` §6.4). The
  reversed-order half needs a law list, so it lands with step 5a, stated as an item in 5a's checklist.

## 5. What the gates assert (the tests' contract)

- **Heat, retrofitted (E2):**
  - **Space order:** at a time-converged shared step (0.45 s), the closed-form error's observed order is 2, within
    (dx_coarse / σ_t)². The owner accepted that bar though it is wider than the old one-sided "fine < coarse / 4"
    (ruling (a), 2026-11-21). Measured: 1.918 and 1.997. It runs the 0.05 m grid, so it is slow-tier.
  - **Time order:** at 0.2 m, 1 within (α / σ₀²) · dt, the explicit-Euler expansion's leading term (≈ 1.19 · (α / σ_T²)
    · dt) plus a margin (owner ruling (i)); measured 1.116 and 1.060. The reference must have settled, within the
    coarser order's own bar.
  - These replace `test_error_falls_with_resolution`, whose "fine < coarse / 4" mixed both errors.
- **The cross-grid comparisons** in `tests/test_cross_tier.py` and `tests/test_act_validation.py` are restated
  through `agrees` and `same_class`. Tests that check an invariant at each grid in turn (a centroid, a refusal, a
  crater's closed form) already verify at every grid and stay as they are:
  - **The full tier (`MAXIM_OVERDRIVE_ALL_TIERS=1`):** 0.1 m within the gate's tolerance of 0.05 m, converging from
    0.2 m. Measured: the fire's onset at turns 94, 92 and 90.
  - **The fast tier:** 0.2 m against 0.1 m, which is the same check one level coarser.
  - **Tolerances are unchanged** in this step: no band loosens (CLAUDE.md). The strict red gates stay strict.
- **Determinism:** each harness function is pure given its callables, and a rerun gives identical results.

## 6. What this step changes outside the harness

- CLAUDE.md's resolution rule, `docs/architecture.md`'s statement of it, and the review charter's Physics lens gain
  the verification rule's wording (`world_model.md` §1.1).
- The substep floor in `heat.py` stayed until step 5a's PR 3 removed it (`sim_core.md` §8). Heat's studies pass
  explicit step counts, so they never depended on it; the scenario agreement studies did (§4).

## 7. Not in this step

- The reversed-order splitting test (step 5a, with the law list).
- Moving scenario tests from `World` to `Simulation`, and so to space alone (step 5a).
- The exact performance counters (step 5a, with B5's budgets).
- New physics. Only heat is retrofitted; damage is measured through the existing scenarios.
- `band_gate`'s first physics caller: the thin-wall breach gate, which asserts its band margin when the PR that fixes
  that Known gap lands (`docs/architecture.md`). Until then `band_gate` is tested on synthetic outcomes only.
