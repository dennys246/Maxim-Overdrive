# Delta round 1: Physics and resolution lens, phase1/verify at 6a2a0ec

Reviewer: independent, Physics and resolution lens. Diff: `3108b6e..6a2a0ec`. The worktree was not edited. Scripts
and planted trees are in `.worktrees/_durable/verify_review/delta1/`:
- `new/` is the tree at 6a2a0ec;
- `revert/` is the same tree with 3108b6e's `heat.py`;
- `sweep.py` sweeps the replan, `space.py` runs the space study at three steps, and `digest_*.txt` hold the
  shipped-path hashes.

**Counts: round 1 is 6 fixed, 1 open. New findings: BLOCKER 0, SHOULD-FIX 1, NIT 3.**

## Status of round-1 findings (set from the tree)

| # | Finding | Status | Evidence |
|---|---|---|---|
| S1 | The replan leaves a zero-length or sliver substep | **fixed** | See "S1" below |
| S2 | `reference_converged` is computed, ignored, and False | **fixed** | It is now asserted and passes. The rationale for its tolerance is wrong: see new S-1 |
| S3 | The time bar's rationale is false | **fixed** | See "S3" below |
| S4 | The space study isn't time-converged, and its numbers don't reproduce | **fixed** | See "S4" below |
| N1 | `agrees.converging` is fooled by quantization | **fixed** | `quantum=` was added, and the fire onset passes `quantum=TURN`. `(90, 91, 90)` is now converging at q = 1, and `(90, 92, 90)` is not (`test_errors_within_the_outcomes_quantum_cant_be_told_apart`). It is still sign-blind, which I accept |
| N2 | `Run`s used as labels in the scenario studies | **fixed** | Agreement studies take spacings. The design doc, the agreement module's docstring and `test_cross_tier.py` say why |
| N3 | `band_gate` and `same_class_under_refinement` have no physics caller | **open** | `same_class_under_refinement` is now scheduled (`docs/plans/checklists.md`, step 5a). `band_gate` still has no caller and no recorded trigger. The thin-wall breach, its natural caller, is still a strict red gate without a band margin. Missing: a checklist row naming the step that wires `band_gate` to the breach gate |

### S1: the replan's even split

- **Red first, verified.** With 3108b6e's `heat.py`, all four cases of
  `test_a_replan_splits_the_rest_evenly_and_never_takes_a_zero_length_substep` (k = 27, 43, 54, 86) fail. With
  the fold's `heat.py` they pass.
- **Sweep, verified.** `sweep.py` ran 696 cases: k = 1…86, and remainders at 0, ±1e-15, ±1e-12, 0.3, 0.5 and
  0.999 of a bound. The fold gives 0 slivers and 0 uneven splits, and the step sum matches `seconds` to 3.8e-15
  relative. The old code gives 272 slivers and 375 uneven splits.
- **Shipped path, verified bit-identical.** I reran the round-1 digest scenario (crate and wall, ignite plus
  strike, 60 turns) at 0.2 m and 0.1 m with each `heat.py`. The SHA-256 and the substep totals are identical
  (`624f6b…`, 240 substeps; `6b312a…`, 960 substeps), and they match round 1's. The branch is still unreachable
  under the substep floor.

### S3: the time bar's rationale

- The docstring now gives the explicit-Euler expansion: c = (3 / (4 ln 2))·|10/3 − 8.75·αT/σ_T²| = 1.19.
- It states the bar as 2.04·(α/σ_T²)·dt, which is the leading term plus a margin. It corrects the earlier reason
  first and records rulings (a) and then (i).
- I rechecked the Richardson algebra: p − 1 ≈ (3 / (4 ln 2))·(C₂/C₁)·h, with h the coarsest step of the triple.
  The test's `zip(orders, runs)` pairs each order with exactly that step. Correct.

### S4: the space study's time-convergence

- **Reproduced at 6a2a0ec** (`space.py`, the test's own `_space_study`):

  | Step (multiple of 0.05 m stability) | dt | Orders |
  |---|---|---|
  | 1/16 | 1.8 s | 1.9298, **2.0447** |
  | 1/64 | 0.45 s | 1.9183, 1.9971 |
  | 1/256 | 0.1125 s | 1.9154, 1.9855 |

  Errors at the test's step are 1.2857%, 0.3402% and 0.0852%. Every number in the docstring, in
  `verify_harness.md` §4 and §5, and in `architecture.md` matches.
- **The time-convergence assertion is real.** At the fine pair, the base-versus-quarter shift is 0.0116 against a
  tolerance of 0.0136.
- **"Time-converged" means a defined criterion, not zero time error.** For first-order time contamination, a shift
  of at most bar/4 bounds the residual at the base step to about bar/3. The measured residual is 1.997 against
  round 1's 1.983 at 1/1024: 0.014, or 26% of the 0.054 bar. That is disclosed well enough, and the owner accepted
  the bar.
- **Margin.** The shift uses 85% of its tolerance. The margin is small, but the value is deterministic.

## New findings

### S-1 (SHOULD-FIX). `tests/test_heat.py::test_heat_is_first_order_in_time`: the settle tolerance's stated justification is false, and a tighter derived tolerance exists

The docstring says: "A tolerance at the finer runs' step can't be met at any refinement, since consecutive orders
differ by about 0.65 of that step's bar."

Measured: λ₀·dt is 0.1733, 0.0867 and 0.0433 at runs 0, 1 and 2. The orders differ by 0.056, so:
- **At runs[1], the gap is 0.646 of the bar.** That is the 0.65 the docstring quotes, and a tolerance there *is*
  met, with 1.55× headroom.
- **At runs[2], the gap is 1.29 of the bar.** That is the one that "can't be met" (my round-1 S2 point).

So the number and the claim come from different steps. The sentence was used to justify the widest option,
λ₀·runs[0].dt = 0.173.

**Failure scenario.** At 0.173 the settle check is almost implied by the two order bars (|p₀ − 1| ≤ 0.173 and
|p₁ − 1| ≤ 0.087). It goes red only when the orders straddle 1 by more than 0.173, for example 1.10 and 0.92.
An order that drifts upward instead of halving, for example 1.12 and then 1.08, passes it. That is a reference
that hasn't settled, so the flag barely guards what §4 says it must.

**Fix.** Use the finer order's own bar, λ₀·runs[1].dt = 0.087. That is "within the order's own bar", derived the
same way, and the measured gap is 0.65 of it. Correct the sentence to "about 1.3× the bar at the second-finest
step (0.65 at the finer order's coarse step)".

**Status of the fix:** the numbers are verified (the script output is above). The code change is unverified: I
didn't run the test with 0.087, but 0.056 ≤ 0.087 follows from the measured orders. The owner accepted the current
bar, so this is the owner's call. The false sentence must be corrected either way.

### N-1 (NIT). `src/simcore/core/heat.py::step` and `tests/test_heat.py::test_a_replan_splits_…`: "no more than the new bound" holds only to one ulp

`remaining / ceil(remaining / bound)` can exceed `bound` by one ulp when the quotient rounds down to a whole
number. In `sweep.py` this happened in 19 of 696 cases, by at most 2.2e-16 relative. Physically it is harmless,
because `stable_dt` already applies `STABILITY_SAFETY`.

**Failure scenario.** The test asserts `max(rest) <= steel_dt` exactly. It holds at the four chosen k only by
luck, so a future k added to the list can go red on a 1-ulp overshoot that isn't a defect.

**Fix.** Assert `<= steel_dt * (1 + 1e-12)`, or reword the comment as "at most the bound, to rounding".
Unverified.

### N-2 (NIT). `docs/roadmap.md` (design rules) and `docs/architecture.md` ("The verification rule"): the old rule's text under the new rule's name

The roadmap now reads "**The verification rule:** a grid changes precision, never the outcome class". World_model
§1.1 says that rule *becomes* "the truth resolution's outcomes agree with the reference resolution's, within a
gated tolerance". The roadmap line therefore names the replaced statement and omits the tolerance and the
convergence that §1.1 adds. `architecture.md`'s "Outcome classes never differ" does the same, though it does quote
§1.1 directly above that line.

**Failure scenario.** A reader of the roadmap's rule list gets the strict-class rule. Binary outcomes near a
threshold can't keep it, which CLAUDE.md's band rule concedes, so the reader can't tell which rule a band-gated
test is held to.

**Fix.** Quote §1.1's sentence in the roadmap, and keep "never the outcome class" only as the band-gated corollary,
as CLAUDE.md does. Unverified as text.

### N-3 (NIT). `tests/test_heat.py::test_heat_is_second_order_in_space`: the fast tier now has no space-order gate

The test is now `slow` and skipped without `MAXIM_OVERDRIVE_ALL_TIERS`. Plain `pytest` therefore checks heat's
time order but not its space order. Prepush sets the tier, so the gate is intact. The cost: a local run can't see
a space-order regression.

**Fix.** Add a fast 0.4 / 0.2 / 0.1 m study, or a single 0.2 / 0.1 m order checked against the coarse bar.
Unverified.

Also wording: `verify_harness.md` §4 says "for heat's bar (28.85 s at 0.05 m)". "Bar" is used for tolerances
throughout, so "the steel bar's stability step" would read unambiguously.

## The questions asked of this lens

- **Are the bars and derivations correct?** Yes for the space bar and the time order bar: the expansion's
  coefficient is rechecked. The settle tolerance is not: see S-1.
- **Is the space study time-converged?** Yes, to the stated criterion. The residual is 26% of the fine bar, and it
  is disclosed.
- **Is the even split correct and bit-identical on the shipped path?** Yes: verified red-first, by the 696-case
  sweep, and by identical hashes. One-ulp caveat: N-1.
- **Do the scenario studies say they co-refine space and time until 5a?** Yes. `test_cross_tier.py`'s module
  docstring, the agreement module's docstring, `verify_harness.md` §4 and §6, CLAUDE.md and the 5a checklist row
  all say so. The stated mechanism is right: the floor scales as 1/dx².
- **Does the wording match world_model §1.1?** CLAUDE.md, `architecture.md`'s quote and the charter's Physics lens
  do. The roadmap's rule list does not: see N-2.
