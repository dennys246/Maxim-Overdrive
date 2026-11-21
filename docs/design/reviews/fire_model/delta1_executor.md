# Executor lens, delta round 1: `docs/design/fire_model.md` v2 (staged on `phase1/fire-design`, over 08310d1)

Read: v2 on disk, round 1's `executor.md`, `fold.md`; `gates` 396ae10 (core, bridge, `actions.yaml`, the red-gate
tests, architecture, world_model, tile spec); this branch's research and round-1 reviews; Maxim `origin/main`
437ec7b1 (unfetched). Tags: **V**
read it, **D** derived here, **M** from memory.

**Counts. Status: 21 fixed, 3 open, 0 deferred, 0 rejected. New: 2 BLOCKER, 8 SHOULD-FIX, 7 NIT.**

## 1. Status of the round-1 Executor findings

| Finding | Status | Reason (read from the tree) |
|---|---|---|
| B1 R2.5 conservation can't fail | fixed | §6.2 R2.5 now has an independent closed-shell sum, and deleting a face is the proof. Its "to round-off" tolerance is new trouble (NS4). |
| S1 one m''_cr | fixed | §3.2 has two events: flash at the data's t_ig rule and extinction per flame (§4.3). The two thresholds are now inverted (NS1). |
| S2 apparent L_g circular | fixed | §6.2 R1 reports it and doesn't grade it. Grading is on held-out fluxes. |
| S3 R2a oracle | fixed | The plywood speeds are gone, and the cold-PMMA dataset is "to find" (M, flagged in §12). The new front law raises its own problem (NS3). |
| S4 R4 oracle mismatch | **open** | Residue at 48 min and the prescribed pilot Q are done. But "stick layout from TN 2102" cites a source that doesn't have it: physics S6 says "TN 2102 doesn't give it", L2 §3.2 says the same, and v2's own §12 lists it as "not in hand". §2.1's "about 100" sticks comes from an assumed density (M, physics S1: 89–122) and is untagged. More in NS7. |
| S5 rates graded while saying never | fixed | §0 item 5 no longer says "never rate", and §6.1 states one rule. That rule's citation is wrong (NS6). |
| S6 "bincount as today" | fixed | §8.2 now states it as a rule, and "as today" is gone from that line. |
| S7 §10 omissions | fixed | §10.1 rows now cover the bridge's region sensors, T4's deposit and 0.2 m radius, T14, `imagination.place` and T13. |
| S8 cost citation | fixed | `gates:docs/architecture.md:129` reads "`advance(0.5)` takes 0.7 s of CPU at 1.92×10⁶ cells (a 40×8×6 m tile at 0.1 m)" (V). §8.3 matches it. |
| S9 wall-flame extrapolation | fixed | §4.1 flags runs on kindling and starter flames as extrapolation. R2b grades front position, not height. |
| S10 n-cap test | fixed | §8.2's hygiene test uses slivers below and above the floor, asserts "cap not hit" and energy conserved, and is proved by deletion. |
| S11 cross-grid gates near-vacuous | **open** | §2.2 defines the coupling, and §6.1 states the rule "every gate names its dx path". But no rung in §6.2 actually names one (R0, R1, R2a, R2b, R3a and R4 are silent), and the coupling still has no closed-form test, which CLAUDE.md requires for new physics. The Q_gas path the coupling relies on doesn't exist (NB1). |
| S12 `REFERENCE_TEMPERATURE` | fixed | Precedent withdrawn (§3.1). |
| S13 §0.1 overstated | fixed | §0.1 is scoped to fine particles and thin dowels, and says the case "rests on our spikes". |
| N1 `latent` | fixed | §10.1: "the planned per-cell latent state". |
| N2 char glow temperatures | fixed | The row is dropped. §3.3's 700–900 °C interior claim matches `char_oxidation.md` §0 item 3 (V). |
| N3 accelerant "verified kernel" | fixed | The phrase is gone (grep). |
| N4 "severe pain" | fixed | §5.2 says "severe pain" and 2.8–5.8×. |
| N5 Heskestad 0.235 | fixed | No longer quoted. |
| N6 "smaller than a cell" | **open** | §0 item 2's heading still says "Our flames are smaller than the cells", and the next line gives 0.3–1.6 cells. At 0.05 m it is false. |
| N7 sliver scope | fixed | §1 says every accelerant run carries it, bounds it at ≤ ~9 W and says the completed runs weren't checked. |
| N8 retirements already taken | fixed | §5.4 cites T4 and F7 (tile §3.2 confirms both, V). |
| N9 pine extinction band | fixed | R1 now has "sustained at 25 kW/m² (~3.8 g/m²s)", which matches V7's conclusion 1. The criterion it adds needs its own fix (NN5). |
| N10 VF cost | fixed | §8.3's 40 ns and 31 ms match `determinism_performance.md` §DP-S5 ("39–41 ns", "31 ms at 4"; V). |

## 2. New findings on v2

### BLOCKER

**NB1. Q_gas has no exit: 6a is not a loss from air cells, so the flame's convective power stays in the cells.**
`fire_model.md::§4.2 "Gas"`, `§2.2 "Heat between an object and the grid"`, `§9.2` ledger ("open-air loss (6a)").
- *Claim:* "Phase 1 has no gas in cells (world_model §2), so [Q_gas] reaches the outside reservoir through those cells'
  open-air loss (6a), on the ledger."
- *True (V):*
  - Tile §5.2 defines 6a as a loss on *exposed solid faces*: "each exposed face loses h_c(T_s − T_amb) + εσ(T_s⁴ −
    T_amb⁴) from its skin".
  - Tile §1.2 gives the convective plume its own exit: "the flame's convective plume leaves the open-topped alley".
    It never passes through the cells.
  - `gates/heat.py` has no loss term at all, only conduction substeps. Air cells only conduct, and air conducts
    "almost nothing" (tile §1.2).
  - world_model §2's "no gas in cells" says there is no gas state there. It doesn't say air cells shed heat.
- *Failure scenario:* a 1 kW starter flame with χ_r ≈ 0.3 (M) deposits ~0.7 kW into the air cells it overlaps. A
  flame volume of ~0.01 m³ holds ~12 J/K of air (D), so those cells warm at roughly 60 K/s and never stop.
  - §2.2's convection h(T_s − T_cell) and its "radiation at the overlapped cells' temperature" then *heat* every
    segment in those cells. This is the 207,350 °C air of `test_a_fire_that_has_burned_its_fuel_stops_heating`'s
    known gap, reborn.
  - The alternative is that the builder adds a loss from air cells to make it work. That is an unreviewed new law,
    and its coefficient sets every fire's outcome.
  - This touches ~70% of every flame's power and every cross-grid gate that rides the coupling.
- *Fix:* route Q_gas straight to the outside reservoir, as tile §1.2 does. Say which cells, if any, the plume heats.
  If cells are to receive it, design and cite the air-cell loss as a law, with its closed-form test and its ledger
  line.

**NB2. R4's "not flamed out at ~2.5 g/m²s" is decided by a free parameter, so it can't fail honestly.**
`§4.3`, `§6.2 R4`, `§12` ("Uncited: … per-flame extinction").
- *Claim:* m''_ext,flame is "cited per setup", and R4's check "is what grades it".
- *True:*
  - There is no citation for a crib setup, and none for the MaCFP pine cone either. V7 1's 2.7–8.3 g/m²s is a
    species band from one rig, and Plathner (S) is a size trend with no law given.
  - §4.3's rule ("mass flux averaged over its burning area") gives the crib cluster the same area-mean as physics S1's
    2.3–3.1 g/m²s (D).
- *Failure scenario:*
  - If R4's "setup" value is the cone's (3.7, or anything ≥ 2.7), R4 flames out by construction. That is physics S1's
    original BLOCKER, unchanged: only the averaging moved from patch to cluster.
  - If the builder picks the setup value for the crib, any value below 2.3 passes. The gate then tests the choice, not
    the model.
  - Either way the ladder's only check of per-flame extinction is vacuous. A test that cannot fail is a BLOCKER
    (CLAUDE.md).
- *Fix:* pre-register one rule for m''_ext,flame before R1: a cited scaling in cluster size or anchoring, or the cone
  value plus a stated anchoring mechanism. Apply it unchanged at R1 and R4, with no per-rung value. Until a scaling is
  cited, say R4's flaming criterion is a prediction.

### SHOULD-FIX

**NS1. The flash and extinction thresholds are inverted, so a fresh flame goes out in the step it lights.** `§3.2`
"Two events, with hysteresis"; `§4.3`.
- *True:* flash is at 1.0 g/m²s (PMMA) or 1.6 (pine) (D). The extinction values the note cites are 2.7–8.3 (V7 1),
  and R1's sustained pine burns at ~3.8. Hysteresis needs the flame to persist below the value that lit it. Here it
  must exceed a value *higher* than the one that lit it.
- *Failure scenario:* a lone pine slab at 25 kW/m² flashes at 1.6 g/m²s, and its one-segment cluster is checked
  against m''_ext > 1.6.
  - The flame dies in the same or the next step. With no flame there is no contact flux, so the mass flux can't climb
    on flame feedback. The flame flickers or never sustains.
  - R0's t_ig passes, because first flash is recorded, while R1's "sustained at 25" fails for a reason that is
    designed in.
- *Fix:* define the transition: when extinction is first evaluated after flash (a cited dwell, or after the flame's
  own feedback has been applied for one step), and state the ordering in the step.

**NS2. §2.2's consumer list misreads what the consumers check, and misses others.** `§2.2 "Occupancy"`.
- *True (V, `gates`):*
  - `applier._check_region`, `StructureModulator.__init__` and `region_parts` don't read cell occupancy. They read
    the region-level flag `Region.solid` (set once at naming from the material, `grid.py:351`), and `_check_region`
    also refuses `not regions[region].cells.any()` as "the {region} is gone".
  - Consumers of `grid.solid` or `AIR_ID` that are not listed:
    - `damage.py:54` (strike);
    - `damage.py:78` (heat damage only where solid);
    - `damage.py:88–101` (region integrity and `breached`);
    - `scene._check_no_solid_overlaps` (which v2's scene v2 must relax);
    - `applier._on_region` (a point inside another solid footprint belongs to that region; fuel inside the crate's
      footprint makes this ambiguous);
    - `frames.CellFrame.reading`, which reduces over `region.cells`.
- *Failure scenario:* an authored stick narrower than a cell, its own region, paints no cells.
  - `_check_region` refuses any act on it as "gone".
  - A lab `RegionInstrument("temperature_max")` calls `max` over an empty mask and raises.
  - A strike on the crate's footprint can't reach its cardboard objects.
  - The builder switches "occupancy" in the five named places and these still break.
- *Fix:* list every consumer above, split "region solidity" from "cell occupancy", define a fuel-only region's
  `solid` and "gone", and give each a test.

**NS3. R2a's front law needs LIFT's Φ and a T_ig, which pull against R2a's oracle and against §3.2's flash rule.**
`§3.2` "The front moves by a law", `§6.2 R2a`.
- *True (V, L2 and V7 6):*
  - The only cited Φ for PMMA is NBSIR 84-2943 Table 2: Type G, T_ig 378 °C, T_s,min 90 °C, Φ/kρc 14; Polycast,
    T_ig 278 °C, T_s,min 120 °C, Φ/kρc 8.
  - LIFT's model gives no spread below T_s,min.
  - At T_s = 20 °C the formula gives 0.11 mm/s (Type G) or 0.12 mm/s (Polycast) (D), about 2× the M value R2a grades
    against.
- *Failure scenario:*
  - If T_s,min is honoured, cold PMMA doesn't spread and R2a fails by design. That is v1's S3, back again.
  - If it isn't, the law runs outside its source's tested range, unflagged.
  - Either way the front speed depends on a T_ig while flash is decided by m''_flash. A part can flash where the front
    law says the surface is below T_ig, or the reverse.
  - The two PMMAs' T_ig differ by 100 K, so the grade depends on which PMMA is used.
- *Fix:* name the PMMA and its Φ source, and say whether T_s,min applies. Flag the cold case as an extrapolation of
  LIFT. Make T_ig in the front law consistent with m''_flash, or say which one wins.

**NS4. R2.5's "to round-off" can't be met with quadrature, so it forces a normalisation.** `§6.2 R2.5`, `§4.4
"Emission"`.
- *True:* §4.4 evaluates the analytic cylinder view factor at "receiver quadrature points". The shell's summed
  absorbed power then carries quadrature error of order the points' spacing over the distance, far above round-off.
- *Failure scenario:* the correct code fails R2.5. The builder rescales the shell's sum to χ_r·Q. The deletion proof
  then also passes, because the rescale hides the missing face, and B1 is back.
- Reciprocity "per patch" checks a patch-to-flame direction the model never computes, so it guards test code only.
- *Fix:* gate the shell sum's error falling with quadrature refinement (order stated), or integrate per patch
  exactly. Forbid normalisation in the text.

**NS5. Q_gas can go negative: contact convection isn't bounded by the budget it's partitioned from.** `§4.2`.
- *True:* Q_contact,conv = Σ h(d,u)(T_f − T_s)·A over segments inside the flame. That is computed bottom-up, and
  nothing caps it at (1 − χ_r)Q. "No term is added on top" is a claim with no mechanism behind it.
- *Failure scenario:*
  - A 1 kW starter flame engulfs 0.1 m² of cold stick surface, at h ≈ 50 W/m²K and ΔT ≈ 900 K (M). That makes
    Q_contact,conv ≈ 4.5 kW against ~0.7 kW available (D).
  - Q_gas = −3.8 kW: the cells are debited or energy is created.
  - The closed-shell ledger test (§6.2, "Tests at every rung") uses a known-receiver setup and won't see it.
- *Fix:* state the rule when demand exceeds supply. For example, the flame's T_f falls until the contact sum fits, as
  a law with a cited basis, not a clamp. Add a test where the engulfed area is large.

**NS6. Tile §6.3 is cited for a rate tolerance it doesn't have, and the exit's observables are left on retired
containers.** `§6.1`, `§10.1` "tile §6.3 item 8 | kept".
- *True (V, tile §6.3):*
  - Item 8's tolerances (15% for `t_crack` and `t_glow`, 10% for `t_gone`) are for **times** only. No rate tolerance
    exists.
  - Items 2–5 define ignited, crack, glow and gone on "bed and face state", "cells with ≥ 10% of their fuel charred"
    and the "envelope-layer skin". v2 removes all three.
- *Failure scenario:* R1's peak HRR and R4's peak rate have no cross-grid tolerance to meet. §7's exit (via 6.4) has
  no defined `t_crack` or `t_glow`, so item 8 grades undefined times.
- *Fix:* give rates their own tolerance, or say they are graded only against data. Add §6.3 items 2–5 to §10.1 and
  redefine them on segments and objects, in metres.

**NS7. R4's remaining oracle problems.** `§6.2 R4`.
- *Ember tail and peak time:* the "≥ 18 min" tail and the 23 min peak both come from the same HRR CSV, which
  `char_oxidation.md` §2.1 read at 1 s (V/Meas).
  - v2 grades the tail but holds the peak time back "until verified". The basis is the same either way.
  - The tail's start is undefined in the model: is it flaming end, or HRR < 220 kW?
- *Pilot:* "a prescribed Q from Test 13's early curve" adds the crib's own early burning to the pilot's. The pilot's
  identity is also inconsistent: `char_oxidation.md` has 0.75 kg of crinkle paper, while L2 §3.3 has acetone-soaked
  rope plus paper.
- *Failure scenario:* the double-counted early Q brings the peak forward. A tail measured from a different event
  passes or fails by definition.
- *Fix:* define the tail as the CSV defines it, grade the peak time from the same CSV or neither, and derive the
  pilot's Q from its own mass and ΔH_c.

**NS8. Three fire red gates, not two. Retiring `ignite` turns one of them red as an error.** `§12` last bullet, §5.4.
- *True (V, `gates`):* the fire gates are `test_act_validation.py:285`, `test_cross_tier.py:80` and
  `test_act_validation.py:815::test_a_fire_on_a_region_carved_hollow_heats_the_region_not_air` (strict,
  `raises=AssertionError`). The last one is about `ignite` landing at a hollow region's centroid. Architecture's A-S2
  missed it too.
- *Failure scenario:* §5.4 drops `ignite` from `parse_action`. That gate then raises `ActionRefused`, not
  `AssertionError`, so the strict xfail reports a failure and the suite goes red for a reason no plan names.
- *Fix:* name all three, and say when each is flipped, rewritten against `kindle`, or retired as moot (the centroid
  rule goes with `ignite`).

### NIT

- **NN1** `§3.1`: "Arrhenius removes 18 ulp per step even at 20 °C" holds only for the illustrative kinetics DP-S1
  used (A = 10⁸ s⁻¹, E = 125 kJ/mol). At the same A, any E ≳ 134 kJ/mol rounds to zero change at 20 °C (D). The
  cutoff criterion still stands; scope the number.
- **NN2** `§1` row 5 and `§0` item 4: "below the lone-surface value". 2.3–3.1 g/m²s overlaps the band's low end (2.7)
  and rests on an assumed density of 400–550 kg/m³ (M). Say "at or below Emberley's 3.7", and tag it.
- **NN3** `§3.2`: "the flame's footprint (§4.2)": §4.2 defines none.
- **NN4** `§6.2 R1`: "no sustained flaming once the heater is removed" has no MaCFP-4 data or time window: a
  prediction.
- **NN5** `§5.4`: the target rule changes T4's ("two candidates is `ambiguous_point`", any two within 50 mm) to
  nearest with a 1 mm tie. §10.1's T4 row lists only the deposit and the radius.
- **NN6** `§8.1`: the coupling-lag check "against a run that couples every substep" has no tolerance, so it can't
  fail as written.
- **NN7** `wc -w` gives exactly 6,000, the cap. Folding the open items needs cuts first.

## 3. Checked and found true

- **Code (`gates` 396ae10):**
  - `bridge.py` exposes `strike(energy_j, …)`, `ignite` ("it burns until extinguished") and `extinguish`.
    `RegionInstrument` serves `QUANTITIES` = integrity, temperature_max, temperature_mean, breached.
  - `parse_action` is the parse path inside `StructureModulator.execute`.
  - `imagination._voxelize` refuses with "smaller than one cell at this resolution".
  - `heat.min_substeps` gives 4, 16 and 64 at 0.2, 0.1 and 0.05 m, so the §8.1 ~16×/~64× coupling cost holds.
  - `actions.yaml` carries `TEMPORARY(phase1)` ceilings.
  - `encoding.snapshot` masks glow and crack by `frame.solid`.
- **Decisions and numbers:** T4 and F7 (tile §3.2); `core.yaml`'s six materials; DP-S1 and DP-S2's counts; §8.3's
  costs (DP-S5); physics S1 and S6's numbers; V7 2b's fluxes, so R0's hold-outs exist; L1's 12–29 s at 65 kW/m².
- **Maxim** (`origin/main`, unfetched): `bodies/base_humanoid.yaml` has `health: derived`, and `spec.py::_check_c5_direct_health`
  refuses a direct `health` sensor. §5.1's claim holds.
