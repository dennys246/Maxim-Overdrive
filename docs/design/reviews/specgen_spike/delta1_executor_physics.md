# Spec generator spike, delta 1: Executor, Physics and Determinism (2026-11-22)

This is a condensed record of the reviewer's hand-back message. The reviewer set each status, read from the tree,
and ran read-only scripts:
- an offset sweep over whole-centimetre faces at 0.2, 0.1 and 0.05 m;
- 30-turn burns at 0.1 m;
- reruns of both Known gaps.

## Fold status of round 1

**Executor.**

- **Fixed:** B1, B2, B3, S2 (on the spike side), S3 to S10, rejection 13, M2(c), M7's denominator and the best arm
  chosen after the fact.
- **Open:**
  - S1: thin parts lose their solid before turn 30 (N-S1).
  - The spacing for M1 (`TOO_SMALL` depends on it).

**Physics and Determinism.**

- **Fixed:** B1, B2, S1 to S6, S8 and N1 to N3.
  - On S2, the offset is verified off every centre at 0.2, 0.1 and 0.05 m, by 3, 3 and 2 mm, with no ties. A
    cylinder tie is impossible (the minimum |d − r| is about 0.7 µm).
- **Open:**
  - B3 on the code side: the Known gap is true but has no red gate or named step.
  - S7's sub-point: `world_model.md` §1.1 exempts fuel objects only as "fuel, never structure", so spec v1 can't carry
    load on a table leg.

## New defects

- **N-S1, SHOULD-FIX, plan §5 M5(b): thin parts are in the air runaway before turn 30.**
  - A 10 cm post has no solid in the sphere by turn 10: 13,343 °C at turn 10 and 151,178 °C at turn 30.
  - A 20 cm post loses its solid by turn 20.
  - Fix: record the turn when the sphere's solid fraction reaches zero, and censor M5(b) after it.
- **N-S2, SHOULD-FIX, plan §6 "Power": the Wilson intervals ignore clustering** (30 prompts × 4 samples). The
  half-width is ±0.14 at ρ = 0.5 and ±0.18 at ρ = 1, so "about 0.15 detectable" isn't derived. Use cluster intervals
  at the prompt level.
- **N-S3, SHOULD-FIX, plan §1: the table numbers are for (0.5, 0.5, 0).** At the spike's offset the table keeps
  0.032, 0.103 and 0.055 m³: its top reappears, inflated, at 0.1 m. So M3 samples a single sub-cell phase.
- **N-S4, SHOULD-FIX: neither new Known gap has a red gate or a named step.**
- **N-N1:** the bootstrap's level and method are unstated.
- **N-N2:** the paired draw may take impossible prompts, and which 4 samples are labelled is unsaid.
- **N-N3:** cylinders are safe from knife edges, but the plan doesn't say so.

## The author's folds after delta 1 (statuses here are the author's claims, unreviewed)

- **Two strict red gates, each proven to fail for its stated reason with `--runxfail`:**
  - `tests/test_damage.py::test_a_hole_through_the_thinnest_authored_axis_is_a_breach_at_every_rig`: it fails at
    0.2 m only (0.1 and 0.05 m see the breach).
  - `tests/test_imagination.py::test_an_object_partly_outside_the_world_is_refused`.

  The first draft of the breach gate selected no cells at 0.05 m, and its precondition raised `AssertionError`,
  which the strict gate would have counted as red. The mask is now a column whose faces are cell faces at every
  spacing, and the precondition raises `RuntimeError`.
- **The named steps:** the breach law at step 8a, which is the author's proposal for the owner to confirm, and
  `place`'s bounds at step 5a.
- **Plan folds:** N-S1, N-S2, N-S3, N-N1, N-N2 and N-N3; the spacing for M1; and S7's sub-point in D31 and plan §1.
- **The architecture delta's folds:** the docstring, O57's payload and the gateway, the lesson date and the roadmap
  trigger.

No further paper round was run. The next review is the freeze's review of the prompt and arm files, which also reads
these folds.
