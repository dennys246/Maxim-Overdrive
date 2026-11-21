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

- **`simcore.verify`**, `boundaries.md`'s layer 8 (`engine.verify`). It imports only `simcore.core` and numpy. A
  layers entry puts it under `maxim_overdrive` and above `simcore.protocol`, and a forbidden contract keeps it off
  `simcore.adapters`, `simcore.protocol` and `maxim`. Nothing in `src/` imports it; tests do.
- **It never builds a `World`.** It receives observables as callables and never constructs state itself. A test
  supplies the state: a law on a grid, or, until step 5a's `Simulation` exists, a `World` scenario. When 5a lands,
  the scenario tests move to `Simulation`, and the harness doesn't change.

## 3. The types (frozen dataclasses)

| Type | Fields | Meaning |
|---|---|---|
| `Run` | `dx_m`, `dt_s`, `steps` | one discretisation: spacing, physics step length, and how many steps |
| `Work` | `substeps`, `cell_substeps` | exact counters for one run, deterministic, never wall time (`world_v2.md`'s "exact performance counters") |
| `Convergence` | `runs`, `values`, `errors`, `orders`, `reference_converged`, `work` | what `converges` measured |
| `Band` | `edges` (per run), `low`, `high` | where a binary outcome flips, per grid |

## 4. The functions

- **`converges(observable, runs, *, exact=None)` → `Convergence`.**
  - `observable(run)` returns the value and its `Work`.
  - With `exact`, the errors are against it (a closed form).
  - Without, the finest run is the reference: errors are against it, and `reference_converged` says whether the
    observed order between the two finest pairs is stable. It needs three runs (the spike: "it must say when the
    reference itself hasn't converged").
  - `orders` holds the observed order between each consecutive pair, p = ln(e_coarse / e_fine) / ln(r), r the
    refinement ratio.
  - Space and time are refined separately (E2): a space study holds `dt_s` fixed across runs, and a time study holds
    `dx_m` fixed. A `runs` list that changes both raises `ValueError`.
- **`band_gate(outcome, xs, runs)` → `Band`.** `outcome(run, x)` is a binary outcome at control value `x`. The harness
  finds each run's flip point by bisection over `xs` and reports the band across grids. The test then asserts its
  operating point clears the band by its margin (`tile_and_client.md` §6.3 item 7).
- **`same_class_under_refinement(outcome, run, factors=(1, 10))` → `bool`.** The splitting test at fixed `dx_m`: the
  same outcome class at `steps` and `10 × steps` with `dt_s` divided to match (`splitting.md` §6.4). The
  reversed-order half needs a law list, so it lands with step 5a, stated as an item in 5a's checklist.

## 5. What the gates assert (the tests' contract)

- **Heat, retrofitted (E2):**
  - **Space order:** at a fixed `dt_s` stable at the finest grid, the observed order of the closed-form error is 2,
    within the next truncation term's relative size at that spacing.
  - **Time order:** at fixed `dx_m`, it is 1 (explicit Euler).
  - These replace `test_error_falls_with_resolution`, whose "fine < coarse / 4" mixed both errors.
- **The cross-tier tests**, `tests/test_cross_tier.py` and the cross-grid tests in `tests/test_act_validation.py`,
  are restated through `converges`, `band_gate` and `same_class_under_refinement`:
  - **The full tier (`MAXIM_OVERDRIVE_ALL_TIERS=1`):** 0.1 m within the gate's tolerance of 0.05 m, converging from
    0.2 m.
  - **The fast tier:** 0.2 m against 0.1 m, which is the same check one level coarser.
  - **Tolerances are unchanged** in this step: no band loosens (CLAUDE.md). The strict red gates stay strict.
- **Determinism:** each harness function is pure given its callables; `Work` counts are integers, and a rerun gives
  identical results.

## 6. What this step changes outside the harness

- CLAUDE.md's resolution rule, `docs/architecture.md`'s statement of it, and the review charter's Physics lens gain
  the verification rule's wording (`world_model.md` §1.1).
- The substep floor in `heat.py` stays: it is step 5a's to remove (its `TEMPORARY` marker). The harness passes
  explicit step counts, so its studies don't depend on the floor.

## 7. Not in this step

- The reversed-order splitting test (step 5a, with the law list).
- Moving scenario tests from `World` to `Simulation` (step 5a).
- New physics. Only heat is retrofitted; damage is measured through the existing scenarios.
