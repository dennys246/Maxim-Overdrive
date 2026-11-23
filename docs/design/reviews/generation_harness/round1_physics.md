# Generation harness plan, round 1: Physics and resolution (2026-11-22)

The reader's hand-back, condensed and saved by the author; statuses are unset (all open) until a reviewer sets them
after the fold. The reader reviewed §5 (U2, U3, U4, U10) and §7 H3 at 620b7a0, against:
- `world_model.md` §1.1 and §4, and `fire_solid.md` §5.4;
- `subcell_solids.md` §2 and §11, and `verify_harness.md`;
- `test_cross_tier.py` and `test_heat.py`.

Probes ran in the spike's venv, with the scripts in the session scratchpad.

## Probe results

**P1, placement-dependent refusal.** A 0.8 × 0.8 m wood slab at four z offsets:

| dx | t = 0.05 | t = 0.08 | t = 0.15 |
|---|---|---|---|
| 0.2 | too_small ×4 | too_small, ok at 2.50× volume, too_small, too_small | ok 1.33, ok 1.33, too_small, too_small |
| 0.1 | ok, 2.00× | ok, 1.25× | ok, 1.33× |
| 0.05 | ok, 1.00× | ok, 1.25× | ok, 1.00× |

**P2, accepted but not the authored object.** A table, a 1.0 × 0.6 m top 0.04 m thick on four 0.05 m legs, is
accepted at every grid. At **0.1 m, the truth grid, it has 0 top cells and 7 leg cells**, against 1 and 3 at 0.2 m
and 240 and 56 at 0.05 m. Its cell-volume ratios are 1.03, 0.23 and 1.19.

**P3, the spike's M5 fire shows no outcome to compare.** A 100 kW fire on a 0.6 m crate for 30 turns of 6 s leaves
integrity at 1.000 at every grid, with peaks of 198.9, 175.6 and 176.0 °C. `test_cross_tier` needs 150 turns at 60 kW
to reach onset.

**P4, time per spec.** 30 turns on the 4 m scene take 0.05 s at 0.2 m, 0.23 s at 0.1 m and 0.94 s at 0.05 m.

## BLOCKER

- **B1, U2 and U3: today they measure the engine's representation gap, not the spec.** Until `subcell_solids` S1,
  cells come from a cell-centre test: P1's offset-dependent refusals and 1.25–2.5× volumes. Most furniture fails U2
  for a Known gap D34 schedules, while P2 passes with no top at the truth grid. Fix (unverified):
  - U2 becomes a strict red gate on S1;
  - until then, record representation fidelity per part (cell volume over authored volume, per grid) without judging
    it;
  - the one spec verdict available today is "a part with no cells at the truth grid".
- **B2, U3: scenario, duration, bars and grids are unstated, and the obvious reading cannot fail.**
  - P3's 30-turn run passes every spec.
  - Longer runs meet the coarse grid's known 32% lag (a strict red gate), and binary outcomes need a band.
  - "Two grids" contradicts `world_model.md` §1.1, which compares 0.1 m against 0.05 m: P3's peaks differ 13% at
    0.2 m and agree to 0.2% between 0.1 and 0.05 m.

  Fix (unverified): per check, the scenario, turns and step, the grids (0.1 m against 0.05 m), the observable with a
  cited bar, and for binary classes a `band_gate` sweep and margin.
- **B3, U3: finiteness, temperature bounds and integrity range check the laws, so a failure can't be the spec's
  fault.** An engine NaN on one geometry class would be recorded as thousands of spec failures, bias the training data
  and never be filed. Fix (unverified): split the battery into engine properties (the corpus feeds property tests of
  the laws, and failures triage to engine Known gaps) and spec verdicts (placement, representation fidelity, fuel or
  not, support).
- **B4, §5 "Two rules" and H3: a test-suite red gate is conflated with a per-spec verdict.**
  - A per-spec "the ledger closes" has no value before the ledger exists.
  - `fire_solid.md` §5.4 is the fuel-object ledger, while cells have only `heat_energy_j`.
  - The tolerance is unnamed (`world_model.md` §4: 1e-12 relative per substep).

  Fix (unverified): records hold `not_run: waits_on=<step>`, consumers needing it refuse `not_run`, the suite holds one
  strict red gate per check, and each ledger is named with its tolerance.

## SHOULD-FIX

- **S1, U4:** "no fire lands on air" turns a measured Known gap into a spec verdict, since where the fire lands is the
  applier's rule. Fix: U4 judges only "ignites iff fuel", through `kindle`, red-gated until TP1; fire-on-air stays a
  diagnostic.
- **S2, U10:** a binary outcome with no margin. `subcell_solids` §2.3 already differs in class across 0.4 m until D22.
  Fix: cite that row and red-gate cell parts on D22.
- **S3, cost:** extrapolated from P4 (not measured past 30 turns):
  - 150 turns costs about 0.25 s at 0.2 m, 1.2 s at 0.1 m and 4.7 s at 0.05 m;
  - a five-power band sweep at 0.1 m and 0.05 m is about 30 s a spec;
  - 5,000 specs is about 40 core-hours, or about 10 h without the reference.

  Whether the 0.05 m reference runs per spec or on a sample is a contract choice for H0.

## NIT

- **N1:** "temperatures bounded" needs a bound and its source (e.g. `WOOD_FLAME_C`).
- **N2, U8:** name the grid (0.1 m), and that bit-identity holds per machine only.
