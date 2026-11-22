# Executor delta review 1: phase1/verify (3108b6e..6a2a0ec)

Reviewer lens: Executor. The worktree was read only. Every plant ran in copies made with `git archive 6a2a0ec`, under
`.worktrees/_durable/verify_review/d1*`, with `PYTHONPATH` pointed at the copy. I did not run the full ALL_TIERS suite.

**Counts: 0 BLOCKER, 1 SHOULD-FIX, 2 NIT (new). Round 1: 6 fixed, 1 open (part of S4).**

## Status of round-1 findings (set from the tree)

| # | Finding | Status | Evidence |
|---|---|---|---|
| S1 | Time test computes `reference_converged` and ignores it; the tolerance can't be met | **fixed** | The test now asserts `study.reference_converged`, with `order_tol = λ·dt` at `runs[0]`. Measured: orders 1.11559 and 1.05969, gap 0.0559, tol 0.1733, True. Plant: tol back at `runs[-2]` (0.0433) makes the test fail. The tolerance is post-measurement; the owner's acceptance is recorded. |
| S2 | The "86 s" figures and the space orders don't reproduce | **fixed** | Reproduced every new number: stable_dt at 0.05 m is 28.84875 s (125 substeps), orders (2.198, 4.898); at 1/16, fine order 2.0447; at 1/64, (1.918, 1.997), errors 1.286/0.340/0.085%. architecture.md's 1.29/0.34/0.085% matches. Time coefficient: c = 1.1935, and λ₀/λ_T = 2.040 as stated. |
| S3 | `agrees.spread` untested beyond monotone values | **fixed** | `test_the_spread_is_the_full_range_whatever_the_order_of_the_values` uses (100, 110, 104) and (90, 100). Both `values[0] - values[-1]` and `abs(first - last)` fail it (by arithmetic: -4 or 4 against 10, and -10). |
| S4 | Space test 203 s in the default tier; exact-substeps test 20 s, unmarked | **fixed in part; open for the second test** | The space test is now `slow` and skipped without ALL_TIERS. It passes alone at the 0.05 m tier: 272 s wall, with 4 processes running. I couldn't check the commit's "64 s" under that load. `test_a_step_takes_exactly_the_substeps_it_plans_however_many` is still unmarked and took **30.5 s** in the fast tier (most of `test_heat.py`'s 36 s). Its 20,000-substep case adds nothing to the red-first case, which is the 8,000 one. |
| N1 | Contract §4 signature and run count out of date | **fixed** | §4 now gives `order_tol` in the signature and says "four runs; with three it is False". |
| N2 | `converges` ignores `order_tol` when `exact` is given | **fixed** | It now raises, tested by `test_a_closed_form_study_refuses_an_order_tolerance_it_would_ignore`. `reference_converged` is None against a closed form. |
| N3 | Replan rounding could take a sliver or 0 s substep | **fixed** | The rest is now split evenly (`dt = remaining / more`). Red first holds: with 3108b6e's `heat.py` the new parametrized test fails 4 of 4, `assert 0.0 == 461.58…` (a 0 s substep). The test isn't tied to its k values: the old code's tail step is a sliver for almost any k, so it fails on more than the four. |

## Other fold claims I re-ran

| Claim | Result |
|---|---|
| `SPACE_BASE = 16` fails the time-converged check | **Holds**: `0.0477 <= 0.0136` fails at 0.1 m (2.0447 against 1.9971) |
| Shipped-path digests bit-identical after the replan change | **Holds**: same digests at 0.2 and 0.1 m, old against new. But this scenario takes 4 or 16 substeps every turn, so it may never reach the replan branch. That makes this evidence weak, not a defect. |
| `simcore.verify` at 100% branch coverage | **Holds**: 151 statements, 46 branches, 0 missed, 57 tests |
| `band_gate` refuses a double flip | Test present. I didn't plant it myself. |
| `test_heat.py` plus `test_verify.py` in the fast tier | 72 passed, 1 skipped (35.7 s) |

## New findings

### SHOULD-FIX D1. `docs/design/verify_harness.md` §5 and `src/simcore/verify/agreement.py::agrees`: the onset gate was loosened, and the contract still says "Tolerances are unchanged"

`test_fire_outcomes_agree_across_rigs` now calls `agrees(..., quantum=TURN)`. That changes `converging` from
`errors[i] >= errors[i+1]` to `errors[i] + 1 >= errors[i+1]`, so the truth grid may now sit one turn further from the
reference than the coarse grid and still count as converging. `test_errors_within_the_outcomes_quantum_cant_be_told_apart`
shows the effect: (90, 91, 90) was False before the fold and is True now.

- **The contract still says the opposite.** §5 keeps "**Tolerances are unchanged** in this step: no band loosens
  (CLAUDE.md)". That sentence is now false.
- **No ruling covers it.** CLAUDE.md requires the owner's ruling to re-derive a bar wider, and to write a bar before
  measuring. The three rulings recorded in `tests/test_heat.py` don't cover this one, and the commit gives only the
  reason ("an onset is a whole turn").
- **Today it changes nothing.** The measured onsets are 94, 92 and 90, errors 4, 2 and 0, which pass at quantum 0.
  With two grids in the fast tier, `converging` is None either way.
- **Failure scenario:** a regression that leaves onsets at (90, 91, 90) passes the full-tier gate, and the gate's
  record says no band loosened.
- **Fix (unverified):** get the owner's ruling and record it beside the call and in §5. Or drop the quantum from the
  onset gate until a measurement needs it.

### NIT D2. `tests/test_heat.py::test_heat_is_first_order_in_time` docstring: the "0.65" explanation contradicts itself

The docstring says a tolerance at the finer runs' step "can't be met at any refinement, since consecutive orders
differ by about 0.65 of that step's bar". Measured:

- gap / (λ₀ · dt at `runs[1]`) = **0.645**. A gap 0.65 of a bar does meet that bar.
- The tolerance that can't be met is the old one at `runs[-2]`, where gap / tol = **1.29**.

So the number is right for one step and the reasoning is stated for another. Separately, "measured coefficient 1.40
at 0.2 m" is the second order's (1.405). The first order's is 1.36.

**Fix (verified by arithmetic above):** say "about 1.3 times the bar at `runs[-2]`", and name which order the 1.40 is.

### NIT D3. `tests/test_heat.py::test_heat_is_second_order_in_space`: the time-converged margin at 0.1 m is thin

At base 64, a quarter step moves the fine order by 0.0109, against a bar of 0.0136 (80% of it). The bar was set after
seeing 0.011 (disclosed, owner accepted). This isn't a defect.

**Failure scenario:** a harmless change to the bar geometry or the materials table flips the test red, and it gets
read as a physics regression. Worth knowing before the next materials-data change. No fix proposed.

## Not checked

- The commit's fast-tier count (1569 passed, 22 skipped, 5 xfailed), and ruff, mypy and the import contracts:
  outside this lens. I didn't plant the `verify-ships-nowhere` violations.
- The space test's 64 s wall time: my run was under 4× concurrent load.
