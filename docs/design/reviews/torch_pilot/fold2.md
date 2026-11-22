# Round 2 (delta) and its fold: `torch_pilot.md` (2026-11-22)

**The delta round** reviewed round 1's fold, uncommitted over fcc6e55 because GPG signing was waiting on the owner.
It used the same six lenses (`delta1_<lens>.md`). Each reviewer set the status of its own round-1 findings from the
tree, and reviewed the fold's diff.

## Statuses set by the reviewers (round 1's findings)

| Lens | fixed | deferred | rejected | open |
|---|---|---|---|---|
| Executor | 18 | 1 (E-S10, to 6.1b) | 0 | 0 |
| Physics | 18 | 0 | 0 | 0 |
| Architecture | 11 | 0 | 1 (A-N3, by its own reviewer: §10 is a change list, not a decision table) | 1 (A-B1, through A2-B1) |
| Wire integrity | 16 | 0 | 0 | 1 (W-S7: checklist 5b's "removed by step 6's skin") |
| Determinism | 8 | 0 | 0 | 2 (D-B1 narrowed to the cell-target `region_gone` cut; D-N1: no sim_core §12 link) |
| Bio-faithful | 7 | 0 | 0 | 0 |

The rows are taken from the reports' status tables. A-B1, W-S7, D-B1 and D-N1 were open when round 2 ended. The
second fold below claims fixes for them, and **no reviewer has read those fixes**.

## The stop (`docs/code_review.md`, "When the rounds stop")

Round 2 found new blockers in text the first fold added:
- **D2-B1:** "halve `tick_us`" contradicts the formats it relies on, which are written in ticks.
- **A2-B1:** Q6's deletion at 5b contradicts 5b's own sphere `kindle`, and a fourth `ignite` gate was missing.

Both are contract defects, so they fold. By the charter the paper rounds stop here, and **the author proposes that
stop to the owner**. Mechanism findings move to the build steps their reviewers named, recorded below.
- **Deferred by reviewers, with their triggers, now in `docs/plans/checklists.md`:**
  - to 6.1b: E-S10, E2-S2, E2-S3, E2-S4, P2-S9, D2-S4, D2-N2, E2-N5, A2-N1 (moot after the fold below), A2-N2 and W2-S5's
    timing (moot after the fold);
  - to step 8: E2-S4's G1–G5 mapping;
  - to Phase 4's body design: B2-N2's measurement.
- **Not yet given a status by a reviewer:** every contract fix below. A two-reader status check, as in PR #27's
  practice, would set them. The owner decides whether to run it.

## Round 2's contract findings, as folded (author's claims)

| Id | Change |
|---|---|
| D2-B1, W2-S4, E2-S1, P2-S6, W2-N4 | §5: the solid refines by `tick_us` alone, at dt, dt/2 and dt/4. The script states seconds (`hold_s`), and its loader converts them. The runs start in reach, so no movement enters. §9.1 states the departure from tile §6.2's form. Beat times are interpolated. §9.2 says it checks convergence, and that the scheme's order is fire_solid §6's |
| A2-B1, E2-S7 | §0.6, §9.4, Q6: at 5b, the four gates' precondition moves to the sphere `kindle`. At 6.1b the sphere deposit, `HeatSource`, `sources` and `_power_field` go, and the gates close by deletion. The crate gate is named. Structure's cross-rig claim is retired as a Known gap with 6.2's trigger |
| D-B1 residue, A2-N1, W2-S5 | §2: only `leave` cuts a pilot; `region_gone` no longer ends one (it is fruitless anyway), and tile §3.2's clause is dropped (§10) |
| D2-S1 | §2: removed at the first physics step at a tick ≥ end − 1, or at the cut when nothing is left to integrate |
| D2-S2, W2-S2, D-N1 | §2, §10: an empty member still hashes, so 6.1b is a recorded break under sim_core §12; its position is sim_core §9's edit |
| D2-S3, D2-N1 | §3: one tie phrasing ("less than 1 mm farther than the nearest"); `centre_m` is the nearest point on the resolved face |
| E2-S6, W2-S1 | §2: `target` is renamed `target_kind`; `contracts.md`'s count is back to 4, with the three-name rationale |
| P2-S1, W2-S3, W2-N3 | §2, §3: a cell region is measured by its authored primitives (CSG when it lands), never `footprint_of`'s box. Its face is 255. The rule's order is stated. The citation is world_model §5 |
| P2-S2 | §9.2: across grids within max(e_dt, s_floor), where s_floor is the floor contact's verified 3% carried to each beat |
| P2-S3, P2-S8 | §6, §7: FDS verification is PMMA's only; PMMA's surface-absorption error and the torch-plus-flame superposition are gaps |
| P2-S4 | §6, §7: ε_r is the least fixed ε; a surface charred before flash is a gap |
| P2-S5 | §9.2: margin = max(spread, one quantum) |
| P2-S7, E2-S5 | §9.1: reflashes are counted, not forbidden; beat 7 reads "the pilot's last covered physics step" |
| A2-S1, W-S7 | §10: tile §3.2's red-gate sentence, lifecycle clause and `max_power_w`; the roadmap's "must flip" sentences and Phase 0 claim; checklist 5b; `architecture.md` |
| A2-S2 | Q1: S0's conflicting rewrite stated, with subcell §7.1's row and §4.3's "gone" |
| B2-S1 | `docs/roadmap.md` OD-A16 row: the torch-pilot evidence and the draft's slow-effects paragraph flagged; checklist 6.1b records both delays |
| B2-N1 | §12, lesson 35: both paths past a call, the eligibility trace and the anchor tier |
| B2-N2 | §6: the NPC holds stay outside every shipped recipe's band; `torch.yaml` gains them in Phase 4 with a bump |
| W2-N1 | Q5: 30 B |
| W2-N2 | Q5: the narrowing refusal is step 7's freeze to name |
| W2-N5 | §6: a 6.1b test holds `actions.yaml`'s ceiling to its formula |
| W2-N6 | §2: "live" is by interval, so at most one live record per actor; load refuses two live ones |
| E2-N1 | §10: the dangling §4.4 reference replaced |
| E2-N2, P2-N1, P2-N3 | §7: the onset at about 140 s with losses (numbers.md's march); 187 K is quoted as reading 3% low |
| E2-N3 | §6: "a disc centred on the slab's centreline" |
| E2-N4 | §6, Q3: the floor converts as the ceiling does, ε_r · 25 kW/m² |
| P2-N2 | §6: the torch's values are fixed first; D and the cap follow from the band runs |

**Numbers checked by the author during this fold:** the onset time, from numbers.md's corrected march at 45 kW/m²
(284 °C at 120 s, 310 °C at 150 s). Nothing else was rerun.
