# Spec generator spike, round 1: Physics and resolution, Determinism and replay (2026-11-22)

This is a condensed record of the reviewer's hand-back message. The reviewer ran a throwaway script outside the repo
that follows plan §5 M5 exactly, using the worktree's `.venv`. The author reproduced the table's voxelization
(0.032 m³ at 0.2 m and 0.007 m³ at 0.1 m, against 0.0455 m³ authored).

## BLOCKER

- **B1, plan §5 M5: the burn protocol mostly runs inside known gaps.**
  - **Fire on air.** A generated-style table (a 1.2 × 0.8 × 0.04 m top and 0.05 m legs) has no solid within its
    centroid's 0.3 m sphere at either spacing. Air reaches 242,527 °C at turn 60 at 0.2 m and 247,451 °C at 0.1 m.
    Its integrity stays 1.000 and it never breaches, so M5b scores it as agreement.
  - **"Scaled by power" is wrong.** The heating rate is P over the solid volume in the sphere, and the fallback to
    air is all-or-nothing.
  - **No signal on solid objects.** The 0.6 m crate at 100 kW reads 1.000 and 0.999 at turns 20 and 40, then 0.831
    against 0.874 at turn 60, with no breach.
- **B2, plan §5 M5(b): the 0.1 band has no threshold to sit on.** `region_breached` is topological, and the band is a
  round number.
- **B3, `damage.py::region_breached`: the axis is chosen from cells, so it flips with the spacing.** A
  0.6 × 0.6 × 0.55 m box picks x at 0.2 m and z at 0.1 m (verified). For furniture, "breached" is arbitrary.

## SHOULD-FIX

- **S1, plan §5 M3 and M5, the composite and §6 rule 2:** 0.2 against 0.1 m isn't the verification rule's check,
  since 0.1 m is the truth grid. Rewarding cross-grid agreement would train stage 2 on simcore's known gaps.
- **S2, plan §5 M1: the offset (0.5, 0.5, 0) puts faces on cell centres** (knife edges).
  - A 0.05 m leg is a full 0.2 m column at 0.2 m and zero cells at 0.1 m.
  - The table's top vanishes at both spacings, and `place` still accepts it.
- **S3, plan §5 M2 and M5:** v0 furniture can't meet the thin-feature rule, and the thin-volume measure isn't
  defined for unions.
- **S4, plan §5 M2(c):** "every pair separated" doesn't detect floating parts; that needs contact-graph
  connectivity.
- **S5, plan §5 M7:** an IoU kernel at 0.2 m doesn't absorb jitter. 0.29 against 0.31 m wide is 1 cell against 2.
- **S6, plan §7: the determinism claim is incomplete.**
  - The judge is a model call.
  - The bootstrap needs a seed.
  - "Scoring twice" in one process misses hash order.
  - The record lacks the simcore commit, the lock hash, the data digests, the scene, the offset and the arms hash.
  - Cross-machine scope is unstated (B28's `pow`, BLAS).
- **S7, `decisions/world_model.md::D31`: wrong premise and example.**
  - D22 already plans collapse by a min cut.
  - The slab-on-legs table really stands: about 0.5 MPa against 30–50 MPa crushing strength, and about 100 kN for
    Euler buckling.
  - The named closed forms miss buckling, bending stress and a statically indeterminate case.
  - Capacity quantization flips classes.
  - Furniture-scale members conflict with §1.1.
- **S8, `decisions/world_model.md::D33`:** "loose" is unsettled against D32's bodies, and the check must be in
  metres.

## NIT

- **N1:** a check run only "on events" misses gradual weakening by fire.
- **N2:** hosted seeds aren't honoured.
- **N3:** the spacing for M5(a) is unstated.
