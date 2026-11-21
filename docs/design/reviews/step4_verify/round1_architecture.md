# Pre-push review, phase1/verify (step 4): Architecture lens

Reviewer: Architecture. Diff: `origin/main...3108b6e` (7 commits, 18 files). Read-only; nothing edited.

**Counts: BLOCKER 0, SHOULD-FIX 4, NIT 6.**

## What I checked

- CLAUDE.md, `docs/code_review.md`, `docs/design/boundaries.md` §2.2 (layer 8: `engine.host | engine.verify`, siblings),
  §3 (core defined by exclusion, `engine.verify` in the non-simulation list), line 649 (the game's gate runs
  `engine.verify`'s cross-tier suite), and `docs/design/verify_harness.md` in full.
- Every module of `src/simcore/verify/` (runs, convergence, bands, agreement, splitting, `__init__`).
- Layering: `pyproject.toml` layers contract (verify between game and protocol), the new forbidden contract
  `verify-measures-only`, `tests/_imports.py` allowlist (fail closed), `tests/test_tooling_config.py`
  (`test_every_child_of_the_engine_is_in_a_layer` covers the new child). The harness imports only `__future__`,
  `math`, `dataclasses`, `itertools`, `collections.abc`; the forbidden contract keeps it off core/adapters/protocol/maxim.
  The layer placement is consistent with boundaries layer 8 (above protocol; host will be a sibling). Sound.
- `heat.step`'s loop change and its two tests; `World.advance`, `heat.min_substeps` (to see what a turn's physics step
  really is).
- The ports in `tests/test_cross_tier.py`, `tests/test_act_validation.py`, and the order tests in `tests/test_heat.py`.
- Callers: `band_gate`, `same_class_under_refinement`, `Convergence.work`, `reference_converged` are read only in
  `tests/test_verify.py`.
- Size/one-job: every harness function is short and single-purpose; `converges` delegates the reference branch to
  `_against_reference` and run checking to `_ratios`. No god functions. `heat.step` grows to plan + replan + power
  refresh + hook; still within limits (see NIT 3).

## SHOULD-FIX

### S1. `tests/test_cross_tier.py::_grids`, `tests/test_act_validation.py` ports: `Run.dt_s` does not describe the run, so the harness's space-study guard is vacuous on the World scenarios

`Run`'s contract (verify_harness §3) is "spacing, physics step length, and how many steps", and `agrees`/`same_class`
refuse runs whose `dt_s` or `steps` differ (`agreement.py::_check_space_study`), the point being E2: refine space
at a fixed step. The ports pass `Run(dx_m, 6.0, turns)`: 6.0 is the *turn*, not the physics step. On the shipped path
`World.advance` calls `heat.step(..., min_substeps=heat.min_substeps(dx))`, and `min_substeps` is
`ceil(FLOOR_AREA_M2 / dx**2)`, so the physics step at 0.05 m is about 1/16 of the one at 0.2 m (more where stability
binds). Every "space study" in the ports changes space and time together, exactly what `_ratios` refuses in
`converges`, and `_check_space_study` passes because the field it checks is a label. `test_a_strike_breaches...`
passes `steps=1` for a strike that has no steps at all. The observables also ignore the run except `run.dx_m`
(`lambda run: runs[run.dx_m]` over precomputed dicts), so the harness never drives what it validates.

Failure scenario: step 6.1 adds a fire-solid scenario and, following this pattern (CLAUDE.md names these files as
"the patterns"), reads an order or a `converging` verdict off an `agrees` study whose grids silently differ in
physics step; a time-error cancellation like heat's old 3.23 passes as spatial convergence, and the type said
it couldn't. Also, when 5a's `Simulation` lands, nothing forces its scenario tests to feed `Run.dt_s` into the
simulation, because the current pattern establishes that it is ignored.

Fix (unverified): either make the World scenarios honest about what is held fixed (a `Run` field or a separate
scenario type carrying the turn length, with `dt_s` reserved for the physics step and the agreement check holding
the *turn* fixed), or have the contract say that `agrees` runs are labelled by turn until 5a, under a
`TEMPORARY(phase1/sim-clock)`-style marker listed in the roadmap, so 5a must make the observable consume `run`.
Not a BLOCKER because `agrees` reports no order and the tolerances are unchanged, so no gate passes today that
failed before.

### S2. `convergence.py::converges` / `_against_reference` disagree with the contract, and the only reference study ignores `reference_converged`

- verify_harness §4 says `reference_converged` "needs three runs". The code accepts three runs but can then never
  return True (`len(orders) >= 2` needs four); `tests/test_verify.py::test_three_runs_give_one_order_and_never_claim_a_converged_reference`
  pins that. The code is the defensible behaviour; the contract is wrong.
- The contract's signature is `converges(observable, runs, *, exact=None)`; the code adds a required-when-no-exact
  `order_tol`. The contract doesn't name it, though every caller without a closed form must pass it.
- With `exact`, `reference_converged` is `True`, a claim about a reference that doesn't exist. `Agreement.converging`
  uses `None` for "can't judge"; this type should too.
- `tests/test_heat.py::test_heat_is_first_order_in_time` passes `order_tol` and never asserts
  `study.reference_converged`. The required parameter's only output has no reader on the one shipped reference study.

Failure scenario: a SEM tissue-law time study (no closed form) is written from the contract with three runs, reads
`reference_converged is False` forever, and its author drops the assertion or "fixes" the harness. Or, from the heat
pattern, the author asserts per-order bars only and never learns the reference hadn't settled, the exact case the
spike asked the harness to catch.

Fix (unverified): correct §4 (four runs for a verdict; `order_tol` in the signature); make `reference_converged:
bool | None` with `None` under `exact`; assert it in the time test. Small.

### S3. `bands.py::band_gate` / `_flip`: bisection assumes monotonicity and hides a non-monotone outcome

`_flip` checks only the two ends, then bisects. A binary outcome that flips twice inside `xs` (true, false, true
across the range) returns one edge chosen by where the midpoints land, with no error. CLAUDE.md says binary outcomes
"keep a band near their threshold", and near a threshold on a coarse grid is exactly where aliasing makes an outcome
non-monotone in the control value (a fire's power crossing an ignition threshold cell by cell). The harness exists
so that "a band that wasn't found can't be gated" (its own docstring); a band found wrongly is gated silently.

Failure scenario: step 6.1 gates ignition vs. source power with `band_gate` at 0.2/0.1/0.05 m. At 0.2 m ignition holds
at 40 kW, fails at 45 kW (a cell-boundary effect) and holds again from 50 kW. Bisection lands on 50 kW, the band
looks tight, and the shipped operating point of 42 kW is declared clear of it while 0.2 m actually flips there.

Fix (unverified): either scan `xs` linearly (each probe is a full simulation, so this costs `len(xs)` runs instead
of `log2`), or keep bisection but say "monotone" in the contract as a precondition the test must establish and add a
cheap check: evaluate `xs[hi-1]` false and the values just above the edge (say two) true, and raise on a violation.
The second doesn't prove monotonicity but catches the common double flip near the edge. `band_gate` has no physics
caller in this step, so this can be settled before 6.1 uses it.

### S4. `convergence.py::Observable` and `runs.py::Work`: one observable shape for `converges`, another for everything else, and `Work` has no reader

`converges` requires `Callable[[Run], tuple[float, Work]]`; `agrees`, `same_class`, `band_gate` and
`same_class_under_refinement` take plain values. In `tests/test_heat.py::_gaussian` the test fabricates
`Work(taken, taken * g.temperature.size)` from the count it passed in. No engine counter supplies it and no test
outside `test_verify.py` reads `Convergence.work`. The contract cites world_v2's "exact performance counters", which
belong to the engine (5a's `Simulation`), not to the test.

Failure scenario: 5a's `Simulation` exposes real counters; every existing `converges` caller keeps hand-computing
`Work`, which can drift from what the engine counted (a replanned `heat.step` takes more substeps than planned:
`_gaussian` asserts `taken == substeps`, but a scenario observable won't), and the scenario harness functions can't
report work at all because their signature has nowhere to put it.

Fix (unverified): either drop `Work` from `converges` until a counter source and a reader exist (B5's budgets), or
make every harness function accept the same observable shape (value plus optional `Work`) so the vocabulary is one.
Prefer the first: "a fix ships with a caller".

## NIT

### N1. `tests/test_heat.py::_space_study`: the scalar `exact` doesn't fit a field closed form

The space study's observable returns the error norm and passes `exact=0.0`, so `values == errors`. Every field
closed form (fire solid's conduction, a tissue diffusion) will do the same. Consider letting an observable return an
error directly (`converges(..., exact=None)` plus an `errors_given=True` mode, or a separate `orders_of(errors)`)
so the API says what callers do. Unverified.

### N2. Contract §2 "Nothing in `src/` imports it" is unchecked

The layers contract puts `maxim_overdrive` above `simcore.verify`, so game code may import the harness and nothing
fails. boundaries line 649 wants the game's gate to run the harness, which is tests. If the claim is meant, a
forbidden contract `maxim_overdrive -> simcore.verify` holds it (unverified); otherwise drop the sentence.

### N3. `heat.py::step`: the replan path can reintroduce a sliver substep, and the function now plans as well as does

`planned = taken + math.ceil((seconds - elapsed) / dt)`: when the remainder is an integer multiple of the new bound
up to rounding from above, `ceil` adds one substep of about 1e-16 × dt. Harmless physically, and only on the
destruction path, but it is the same float-ceil pattern the comment above it forbids. Separately, the schedule
(plan, replan on tightening) is a decision and could be a small pure helper beside `stable_dt`, leaving `step` to
do. The loop fix itself is a genuine root-cause fix (count, don't compare a float sum), with a red-first test and a
replan test that shows the bound really tightened. Unverified.

### N4. `agreement.py::_check_space_study` compares `dt_s` with `!=`, `convergence.py::_ratios` with `_close`

Two notions of "the same step" in one package. A run built as `Run(dx, T / n, n)` against one built by
`refined_in_time` can differ in the last ulp and be refused by `agrees` while `converges` accepts it. Use `_close`
in both (move it to `runs.py`).

### N5. `runs.py::Run` requires `dx_m > 0` for every law

A SEM tissue law on a body compartment has no grid spacing; a time study of it must invent a `dx_m`. Fine for now
(the time study holds dx fixed), but say in the contract that a non-spatial law passes a fixed nominal spacing, or
give `Run` an optional spacing when the first such law lands.

### N6. Mechanism and measurement in the contract note

verify_harness.md §4 says `band_gate` works "by bisection" (mechanism; the contract is "each run's flip point over
`xs`", plus the monotone precondition if S3 keeps it). §4's "at heat's 86 s it gave orders of 3.23 and -0.33" and
"passing again at a quarter of the step" are heat's measurement and heat's test method, which belong in
`test_heat.py`'s docstring (already there) and not in the harness's contract. §5's heat bars are a test contract and
fine to keep.

## Fit for the next users

- **5a `Simulation`:** the callable boundary fits (no `World` in the harness, enforced). The risk is S1: the scenario
  pattern lets an observable ignore `run.dt_s`, and the move to `Simulation` will copy it unless the type or a marker
  forces otherwise. `same_class_under_refinement` fits splitting §6.4 once observables consume `run.dt_s`.
- **6.1 fire solid:** `agrees`/`same_class` fit scenario outcomes; `band_gate` fits ignition, subject to S3.
- **SEM tissue laws:** `converges` time studies fit (subject to S2 and N5); `agrees` is space-only and has no
  time-only analogue, which is fine until a tissue scenario needs one.

## Verdict

No BLOCKER. The layer placement, the forbidden contract and the allowlist are right and enforced; the heat loop fix
is a real root-cause fix with red-first tests; the order tests now refine space and time apart and say how their
bars were set. The four SHOULD-FIXes are about the vocabulary saying more than it checks (S1, S3) or less than it
does (S2, S4); each is small, and S1 and S3 should be settled before 5a and 6.1 copy the pattern.
