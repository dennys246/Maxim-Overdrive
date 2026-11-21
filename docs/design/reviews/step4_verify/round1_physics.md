# Pre-push review: Physics and resolution lens, phase1/verify at 3108b6e

Reviewer: independent, Physics and resolution lens. Diff: `origin/main...3108b6e`. All computations ran with the
worktree's `.venv` and live under `.worktrees/_durable/verify_review/work/` (scripts `orders.py`, `orders_dx.py`,
`bitid.py`, `loop2.py`, `real_sliver.py`; planted trees `old/`, `new/`, `mut1/`, `mut2/`, `fix/`). The worktree was
not edited.

**Counts: BLOCKER 0, SHOULD-FIX 4, NIT 3.**

## What holds

- **Order method.** `converges` computes p = ln(e_c/e_f)/ln r against a closed form, and Richardson
  p = ln(|v1−v2|/|v2−v3|)/ln r with one ratio otherwise. It refuses studies that refine both dx and dt, or neither
  (`_ratios`). This is E2 done correctly.
- **The space bar |p−2| ≤ (dx/σ_t)² is sound, and conservative.** Time-converged orders (128,000 substeps,
  dt = 0.028 s) are 1.915 and 1.983, so p−2 = −0.085 and −0.017. That shrinks about 5× per halving, which is the
  asymptotic dx² signature. Against bars of 0.218 and 0.054 that leaves 2.6× and 3.2× headroom. The coefficient 1 on
  (dx/σ_t)² is a fair "next term" scale.
- **heat.step on the shipped path is bit-identical.** I ran a crate-and-wall fire (120 kW, 150 turns) through
  `World.advance` with origin/main's `heat.py` and with the branch's. At 0.2 m and 0.1 m the SHA-256 of
  temperature + integrity + material is identical, and so are the substep totals (600, 2,400; 27 and 160 cells
  destroyed). The replan branch never fires on the shipped path today. The TEMPORARY floor gives dt = 1.5 / 0.375 /
  0.094 s, far below air's stability bound (about 275 s at 0.2 m, 17 s at 0.05 m), so destroyed cells turning into air
  never tighten stability below dt. The non-destruction path can't differ either: 64 substeps of 6 s accumulate about
  1e-13 s of rounding, below the old 1e-12 epsilon.
- **The replan test guards what it claims.** I planted two mutations: deleting `planned = taken + ...` (`mut1`) and
  deleting `dt = bound` (`mut2`). Each turns
  `test_a_step_replans_at_the_shorter_step_when_a_change_tightens_stability` red, and
  `test_a_step_takes_exactly_the_substeps_it_plans_however_many` stays green. Verified.
- **The time study is time-only and first order.** At 0.2 m, Richardson orders are 1.116, 1.060, 1.030, 1.015
  (k = 1…32). p−1 halves with dt, as explicit Euler should.

## SHOULD-FIX

### S1. `src/simcore/core/heat.py::step`: the replan path brings back the zero-length or sliver substep the commit fixes

The new comment says "never compare a running float sum", but the replan sets
`planned = taken + ceil((seconds - elapsed) / dt)` from exactly that running sum, and then steps at `dt = bound` with
the last step clipped by `min(dt, seconds - elapsed)`. When the remaining time is (to rounding) a whole number of
bounds, `ceil` adds one step, and the loop then runs a substep of dt = 0.0 (or about 1e-16 s). Each such substep also
makes an `on_substep` call and adds one to `taken` (and to `Work`).

- **Reproduced on the real function** (`real_sliver.py`). A 0.6 m wood cube at 0.2 m turns into steel after
  substep 1, with `seconds = 2·k·stable_dt(steel)` for k = 1…86. In 4 of the 87 cases there is a zero or sliver
  substep, and `taken ≠ 1 + k`.
- **The arithmetic model** (`loop2.py`, the same statements) gives 2,357 zero-dt substeps in 18,535 near-integer
  cases. None were negative; they are exactly 0.0.
- **Harm today:** none on the shipped path, because the replan never fires there (see above).
- **Harm after step 5a:** it bites once step 5a removes the substep floor. dt then sits at the stability bound, and
  destruction into air does tighten it. Work counters lose exactness: `Work` is meant to be an exact counter, and
  `same_class_under_refinement` and the 5a budgets read it.
- **Fix:** on a replan, split the remainder evenly: `remaining = seconds - elapsed; more = ceil(remaining / bound);
  dt = remaining / more; planned = taken + more`. **Verified** in `work/fix/`: zero sliver substeps across the 87
  cases, and both heat.step tests pass. The shipped-path hashes can't change, because the branch is unreachable
  there. Add a red-first case to the replan test, for example `seconds = 2·k·steel_dt` with k = 3, which hits the
  zero step in my sweep (check which k does on your machine).

### S2. `tests/test_heat.py::test_heat_is_first_order_in_time`: it computes `reference_converged` and ignores it, and the value is False

The test passes `order_tol = decay_rate * runs[-2].dt_s` but never asserts `study.reference_converged`. At
3108b6e that flag is **False**:

- The orders 1.116 and 1.060 differ by 0.056, against a tolerance of 0.043.
- At 0.1 m (k = 1…8) and 0.05 m it is also False.
- The cause is structural. p−1 = O(dt), so consecutive orders differ by about 0.65·λ₀·dt_coarse, which always
  exceeds λ₀·dt of the second-finest run (about 1.3× in every study I ran).

So the harness's one "has the reference converged" signal, which verify_harness §4 says such a study "must give",
reports non-convergence here, and the gate passes anyway. This is the "a check that cannot fail" family. The
tolerance line is dead code that looks like a guard.

- **Fix:** derive `order_tol` from the bar being asserted (orders within λ₀·dt of 1 can differ by up to
  λ₀·(dt_i + dt_{i+1})). `λ₀·runs[-3].dt_s` = 0.087 passes. Then `assert study.reference_converged`.
- **Alternative:** document in `Convergence` that `reference_converged` means "the orders' spread is below tol",
  which a first-order study can only meet with tol ≥ the order's own drift.
- **Unverified as code;** the numbers are verified (`orders.py time 1 2 4 8`).

### S3. `tests/test_heat.py::test_heat_is_first_order_in_time`: the docstring's physics for option (a) is wrong, though the bar is safe

The owner's ruling (a), |p−1| ≤ (α/σ₀²)·dt, passes with margin. But the stated reason ("the initial Gaussian's
decay rate, which generates most of the time error") isn't what the expansion gives. For explicit Euler on
u′ = Lu, (1+hL)ⁿ = exp(TL − (Th/2)L² + (Th²/3)L³ + …), all evaluated at u(T). At the Gaussian's peak
(width σ_T), C₂/C₁ = (α/σ_T²)·[10/3 − 8.75·αT/σ_T²], and the predicted Richardson deviation is

  p − 1 ≈ (3 / (4 ln 2))·(C₂/C₁)·dt ≈ 1.19·(α/σ_T²)·dt = 0.59·(α/σ₀²)·dt (here αT/σ_T² = 0.255).

Measured: (p−1)/((α/σ_T²)·dt) = 1.40 at 0.2 m, 1.24 at 0.1 m and 1.207 at 0.05 m, converging to the predicted 1.19
as the space discretisation resolves the pulse (σ₀/dx is only 1.5 at 0.2 m).

So the first-written σ_t bar was the right scale and simply lacked its O(1) coefficient of about 1.2. It was not
failing because σ_t was the wrong width. Option (a) happens to equal 2.04·(α/σ_T²), which gives 1.46× headroom at
0.2 m.

The ruling stands, since it is the owner's call. But the recorded rationale is false, and the next law to be
retrofitted will copy it. Replace it with the expansion and its coefficient. The derived bar,
|p−1| ≤ c·(α/σ_T²)·dt with c = (3 / (4 ln 2))·|10/3 − 8.75·αT/σ_T²|, needs a margin at 0.2 m (1.40 against 1.19), which
is a decision for the owner. Verified numerically (`orders_dx.py time {0.2, 0.1, 0.05}`).

### S4. `tests/test_heat.py::test_heat_is_second_order_in_space` and `docs/design/verify_harness.md` §4: the space study is only nearly time-converged, and its recorded numbers don't reproduce

- **Time-convergence.** At the test's step (8,000 substeps, 0.45 s) the orders are **1.918 and 1.997**. At ¼ of the
  step they are 1.915 and 1.986, and at 1/16 they are 1.915 and 1.983. Time error still moves the fine order by
  +0.015 (27% of its 0.054 bar), and it flips the sign of p−2 at the fine pair (true −0.017, measured −0.003).
- **"Passing again at a quarter of the step" doesn't show time-convergence.** It shows both steps clear a bar with
  3× headroom. A real check asserts that the orders at base and at 4×base agree within a small fraction of the bar
  (here they differ by 0.011), or extrapolates in time.
- **The docstring's "Measured 2026-11-21: orders 1.93 and 2.03" is false at 3108b6e.** The test's own `_space_study`
  gives 1.9183 and 1.9971 (I ran it).
- **"At the old test's step (stability at 0.05 m, 86 s) they were 3.23 and −0.33" doesn't reproduce either.**
  `stable_dt` at 0.05 m is 28.85 s, so 86 s is unstable there, and `_gaussian`'s `taken == substeps` assertion fails
  at 42 substeps. A shared 28.8 s step gives 2.20 and 4.90. The old test's mixed per-grid steps (4/21/125 substeps)
  give 3.13 and 3.68.
- The same "86 s … 3.23 and −0.33" appears in `docs/design/verify_harness.md` §4.
- `docs/architecture.md` gives "0.08%" for 0.05 m. The value is 0.0852% at the test's step (0.0863% time-converged),
  so 0.09% or 0.085%.

The conclusion (the old test passed by cancellation) is right: the mixed orders of 3.1–3.7 are impossible for the
scheme. But the evidence as recorded is wrong, and CLAUDE.md's first principle requires the numbers to be exact.
Fix: rerun the measurements, replace the numbers, and add the base-versus-4×base order-stability assertion.
**Unverified as code;** the numbers are verified (`orders.py space 1 4 16`, and direct `_space_study` calls).

## NIT

### N1. `src/simcore/verify/agreement.py::agrees`: `converging` is sign-blind, and quantization fools it, for outcomes like onset turns

The predicate is `errors[i] >= errors[i+1]`, on absolute errors against the finest grid. For integer outcomes
(verified with `agrees`):

- (90, 91, 90) at 0.2/0.1/0.05 m gives errors (0, 1) and converging=False. That is a red gate for a one-turn
  quantum, with the coarse grid exactly on the reference.
- (89, 91, 90) gives converging=True, even though the coarse and truth grids sit on opposite sides.
- (91, 90, 90) gives True.

Today's fire numbers (94, 92, 90) are well clear. But the moment a physics improvement brings the grids within a
turn, `test_fire_outcomes_agree_across_rigs` can go red because the physics improved. That is the opposite of what
the rule wants, and the path of least resistance would be to loosen it.

Suggested fix: let `agrees` take the outcome's quantum q (a turn = 1) and define
converging = e_coarse + q ≥ e_truth, or treat |e| ≤ q as converged; optionally also report the signs. I rate it a
NIT only because no current value is near the edge; if the owner wants the rule to hold for a playtest-tuned fire,
it is SHOULD-FIX. Unverified as a fix.

### N2. `tests/test_act_validation.py::test_the_fiercest_allowed_fire_...`: the `Run`s are labels, not the discretisation

`Run(dx_m, 6.0, 60)` claims 60 steps, while the observable reads turn `t`. It is harmless, because `agrees` only
checks that the step and count are shared, but a reader of the `Agreement` repr sees 60 steps for turn 3.
`test_a_strike_breaches_a_thin_wall_...` has the same issue with `Run(dx, 6.0, 1)` for a strike that runs no turn.

### N3. `band_gate`, `same_class_under_refinement` and `Convergence.reference_converged` have no physics caller on this branch

`same_class_under_refinement` is scheduled for 5a. `band_gate` is not used by the thin-wall breach (still a strict
red gate), where its margin assertion (tile §6.3 item 7) would matter most. This is for the Wire-integrity lens to
weigh; from the physics side, the only binary outcome in the diff (the breach) isn't banded yet.

## Other questions asked of this lens

- **Is the verification rule's wording consistent with world_model §1.1?** Yes, in substance. §1.1's quoted rule is
  "agree … within a gated tolerance". Its bullet adds "must converge from 0.2 m", and CLAUDE.md merges the two.
  CLAUDE.md keeps "a spacing may change precision, never the outcome class", which §1.1 says the old rule "becomes"
  rather than keeps. That is harmless (`same_class` still uses it), but strictly it is an addition to §1.1.
- **The fast tier's coverage.** It never compares truth with reference (0.2 against 0.1, `converging` None). Only
  `MAXIM_OVERDRIVE_ALL_TIERS` checks the rule itself. The prepush gate sets it, so this is acceptable.
- **The fire test's bar.** `onset.spread ≤ 0.1·min(values)` gates the spread across all grids, which is stricter
  than "the truth grid within tolerance of the reference". Fine.
- **Thresholds on cell means.** The diff adds none. `damage.thermal_degrade` (untouched) thresholds the cell-mean
  temperature (`excess > 0`), the root of the two strict red gates this branch ports. They stay strict, with their
  known-gap reasons, and the bars are unchanged. Nothing new.
- **Determinism.** The harness is pure, `Work` counts are ints, and the loop change is integer-counted. With S1 fixed,
  the counts are exact on every path.
