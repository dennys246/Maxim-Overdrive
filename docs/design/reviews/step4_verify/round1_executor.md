# Executor review: phase1/verify (origin/main 814dea9 ... 3108b6e)

Reviewer lens: Executor. Worktree read only; every plant ran in copies under
`.worktrees/_durable/verify_review/` (`old/` = the branch with origin/main's `heat.py`, `plant/` = the branch, `p2/` = planted
copies, each restored after use). I did not run `MAXIM_OVERDRIVE_ALL_TIERS` or any 0.05 m scenario.

**Counts: 0 BLOCKER, 4 SHOULD-FIX, 3 NIT.**

## What I checked, and what held

| Claim (where) | What I ran | Result |
|---|---|---|
| Red first: the old loop takes 8,001 substeps for 8,000 (29af1d8) | `test_a_step_takes_exactly_the_substeps_it_plans_however_many` against origin/main's `heat.py` | **Holds**: `assert 8001 == 8000` |
| Shipped path is bit-identical (29af1d8) | `tests.test_determinism.SCENE`, 500 kW fire plus strike, 60 turns, digest at 0.2 m and 0.1 m, old `heat.py` against new | **Holds**: digests identical (`624f6bff…`, `6b312a64…`), 4 and 16 substeps every turn |
| Deleting the replan fails on `2 == 1 + 89` (e97bb05) | replaced the `planned = …` line with `pass` | **Holds**: `assert 2 == (1 + 89)` |
| Inverting the order formula fails 3 tests; dropping the mixed-study refusal fails 2 (cb368a1) | the same plants in `convergence.py` | **Holds**: 3 failed and 2 failed. Also planted: swapping the study axis fails 14 tests |
| 100% branch coverage of `simcore.verify` | `pytest tests/test_verify.py --cov=simcore.verify --cov-branch` | **Holds**: 157 statements, 44 branches, 0 missed (49 tests now; 41 at cb368a1) |
| A first-order space error fails the space test (29af1d8) | flux times `(1 + grid.dx)` in `substep` | **Holds**: orders 0.64 and 0.85, fails at `1.357 <= 0.218` |
| `+ 0.01` per step pulls the time order to 0.65 and fails (29af1d8) | `T += dT + 0.01` | **Holds**: orders (0.996, 0.649), fails |
| Time orders 1.116 and 1.060; the sigma_t bar gave 0.085 and 0.042 (test docstring) | the time study, printed | **Holds**: 1.11559, 1.05969; α/σ_t² × 1200 s = 0.085 |
| The space step is time-converged ("passes again at a quarter of the step") | errors at 8,000 and 32,000 substeps | **Holds**: 1.2857/0.3402/0.0852% against 1.2865/0.3410/0.0861% |
| Fire onset 94 and 92 turns at 0.2 and 0.1 m (05a7c76) | `tests.test_cross_tier._burn` at both | **Holds**: 94 and 92. The 90 at 0.05 m was not run (outside my brief) |
| The old architecture numbers came from mixed steps | old `_error` at each grid | **Holds**: 0.99%, 0.114%, 0.0089% (orders 3.13 and 3.68) |
| The ported gates keep their bars | read the diffs | **Holds**: the onset bar is `spread <= 0.1 * min`, as before; integrity spread `<= 0.1`; thin wall `same_class` has the old `len(set) == 1` semantics; badly-burned `errors[0] <= TIME_TOL * values[-1]` is the old `abs(coarse - fine) <= TIME_TOL * fine` (FAST_SPACINGS in both). The xfail gates keep `strict=True, raises=AssertionError` |
| The harness imports nothing from the engine | read the contract in `pyproject.toml`, `tests/_imports.py`, the imports in `src/simcore/verify/` | **Holds** |
| `heat.py` comment: the shortfall is "about 1e-9 s" at 8,000 × 0.45 s | summed in Python | 4.8e-10 s; fair |
| Fast-tier results of the new tests | `pytest tests/test_verify.py tests/test_heat.py` | **61 passed** (374 s wall) |

## SHOULD-FIX

### S1. `tests/test_heat.py::test_heat_is_first_order_in_time`: the reference check is computed with a tolerance that can't be met, then thrown away

The test passes `order_tol=decay_rate * runs[-2].dt_s` to `converges`, and the harness's docstring says such a study
"must give" a converged reference. The test never asserts `study.reference_converged`. Measured, it is **False**: the
last two orders differ by 1.1156 - 1.0597 = 0.0559, and the tolerance is 0.0433.

It never becomes True however far you refine, so the tolerance can't be met at any step:

| step multipliers k | orders | order_tol | converged |
|---|---|---|---|
| 1, 2, 4, 8 | 1.1156, 1.0597 | 0.0433 | False |
| 1 … 16 | 1.1156, 1.0597, 1.0299 | 0.0217 | False |
| 4, 8, 16, 32 | 1.0299, 1.0149 | 0.0108 | False |

The order's excess over 1 halves with each halving of dt (about 0.67·λdt), so the gap between successive orders is
about 0.33·λ·dt_i. The tolerance is λ·dt at `runs[-2]`, which is dt_i / 4, so it is 0.25·λ·dt_i. That's a fixed ratio
of 1.3, missed at every refinement.

**Failure scenario:** the contract (verify_harness §4) says the reference study "must say when the reference itself
hasn't converged". Here it does say so, and nobody listens. A change that leaves the 4-run study far from its
asymptotic regime still passes, as long as each order stays inside its own (wide) bar. Today's own measurement
already sits in that state.

**Fix (unverified as an edit, verified by arithmetic on the measured orders):** derive `order_tol` the way the bar is
derived, from the coarse step of the pair being compared: λ·dt at `runs[-4]`, which is 0.173 here, against a gap of
0.056. Then assert `reference_converged`. Because the bar is written after measuring, this is the owner's call
(CLAUDE.md, the bar rule). Otherwise, drop `order_tol` from the call so the test doesn't look like it checks
something it doesn't.

### S2. The "86 s" figures and the space-order numbers don't reproduce

These appear in the `test_heat_is_second_order_in_space` docstring, in `docs/design/verify_harness.md` §4 ("at heat's
86 s it gave orders of 3.23 and -0.33") and in commit 29af1d8:

- **"Stability at 0.05 m, 86 s" is false for this bar.** At 0.05 m the bar is 4 cells across, and `heat.stable_dt`
  gives **28.85 s** (125 substeps). 86 s is the 1-D bound, dx²/(2α)·0.9 = 86.5 s.
  - At 42 substeps (86 s), `heat.step` takes 125 substeps at 0.05 m anyway. `_gaussian` would then fail its
    `taken == substeps` assert, so the study as written can't run at 86 s.
  - Called directly, I get orders **3.23 and 3.69**, not 3.23 and -0.33.
  - At the real finest-grid stability step (125 substeps), the orders are **2.20 and 4.90**.
  - The qualitative point still stands: 4.90 fails the bar, so stability at the finest grid isn't enough. But the
    printed numbers and the 86 s have no reproduction path.
- **The claimed orders were "1.93 and 2.03"; I measure 1.918 and 1.997** at the test's step (and 1.915 and 1.986 at the
  quarter step). This is one machine and one deterministic code path, so this isn't noise: the recorded numbers come
  from some other configuration. The test still passes (margins of 0.08 against 0.218, and 0.003 against 0.054). Still,
  "Measured 2026-11-21" plus a number nobody can reproduce is a false record.
- **Failure scenario:** a later reader uses 86 s as "the finest stable step" for another study, or tries to reproduce
  -0.33 while chasing a regression, and wastes the effort. These numbers are also the evidence behind a contract
  sentence.

**Fix (verified, by what I ran above):** replace the numbers with 28.85 s, (2.20, 4.90) at the finest stability step,
and (1.92, 2.00) for the study. Or state exactly what configuration produced the old numbers.

### S3. `src/simcore/verify/agreement.py::agrees`: `spread` is untested beyond monotone values

`spread` is the only quantity the ported cross-grid gates assert (onset, fiercest fire). I planted
`spread = values[0] - values[-1]` (no max/min, no abs), and **all 49 tests in `test_verify.py` still pass**. The only
spread test uses 110, 104, 100, which is monotone and decreasing. In the fast tier there are two grids, so no
scenario test can tell the difference either.

**Failure scenario:** a refactor to "first minus last" passes the suite. A scenario whose coarse onset is earlier than
the fine one then gets a negative spread and passes any bar. A non-monotone case (100, 110, 104) understates the
spread by 6.

**Fix (unverified):** add a case with values that aren't monotone and increase coarse to fine, for example
{0.2: 100, 0.1: 110, 0.05: 104}, expecting spread 10.

### S4. `tests/test_heat.py::test_heat_is_second_order_in_space` costs 203 s wall in the default tier, unmarked

Measured with `--durations`: **203 s** for the space test and **20 s** for
`test_a_step_takes_exactly_the_substeps_it_plans_however_many`. Neither is marked `slow`.

- The machine was loaded: the run's CPU time was only 19 s for all four new tests. Even so, the space test runs
  3 grids × (8,000 + 32,000) substeps.
- CLAUDE.md says "Mark anything over a few seconds `slow` and gate it behind a tier variable."
- The rule can't be followed as written today: the existing fire scenarios aren't marked either (the 0.1 m `_burn`
  takes 81 s), and the only `slow` user is the Godot fixtures. So this is partly a standing gap, but this diff adds
  the largest single new cost to `pytest`'s default tier.
- The 64× base looks oversized. The errors at 8,000 and 32,000 substeps agree to about 6e-4 relative, so a smaller
  base would likely pass the quarter-step rerun. That is unverified and is the author's to measure.

**Failure scenario:** "run the module you touched first" for heat now takes minutes.

## NIT

- **N1. `docs/design/verify_harness.md` §4 doesn't match `converges` on two points.**
  - The listed signature is `converges(observable, runs, *, exact=None)`. It omits `order_tol`, which is required
    when `exact` is None.
  - It says a reference study "needs three runs". With three runs, `reference_converged` is always False, because
    `settled` needs two orders. `test_three_runs_give_one_order_and_never_claim_a_converged_reference` pins that.
  - An author following the contract would write a three-run study that can never pass.
- **N2. `convergence.py::converges` silently ignores `order_tol` when `exact` is given.** A caller who passes both
  thinks the reference is being checked, and gets a hard-coded `reference_converged=True`. Raising on the pair would
  make the misuse loud. Unverified.
- **N3. `heat.py::step` replan rounding (unverified, not reproduced).**
  - `planned = taken + math.ceil((seconds - elapsed) / dt)` can round up by one when the remainder is an exact
    multiple of `bound`. That reintroduces a sliver substep (or, in principle, a remainder of about 0 or slightly
    below 0, passed to `substep` and `on_substep`), the same class of bug this branch fixes, only on the replan path.
  - It is harmless to stability. I found no case on the shipped path: the digests above are unchanged, and that
    scenario does destroy cells.
  - Also: `docs/architecture.md` gives "1.28% / 0.34% / 0.08%" for errors I measure as 1.286, 0.340 and 0.0852%.
    Those are truncated, not rounded (0.09%).

## Not checked

- The 0.05 m onset of 90 turns and the full-tier `converging` value: they need the 0.05 m fire scenario.
- The commit's "164 passed, 5 xfailed" fast-tier count for `test_cross_tier` and `test_act_validation`: I ran only
  the onset measurement from them.
- The architecture.md word-count claim.
