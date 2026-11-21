# Executor lens: `docs/design/fire_model.md` (branch `phase1/fire-design`, 54358fd)

Lens: are the design's claims about the code, data, tests and numbers true, and can each proposed test fail?
Code read at `gates` 396ae10 (`grid.py`, `frames.py`, `bridge.py`, `imagination.py`, `damage.py`) and at this
branch (`bridge.py`, `materials.py`, `data/materials/core.yaml`). Tags: **V** read it, **M** from memory.

**Counts: 1 BLOCKER, 13 SHOULD-FIX, 10 NIT.**

## BLOCKER

**B1. The R2.5 conservation check cannot fail.** `fire_model.md::§6 R2.5` and `§4.1 Flux onto surfaces`.
- *Claim:* the pass is "radiated power = χ_r·Q to round-off"; §4.1 sets "surface emissive power so the total radiated
  power is χ_r·Q exactly" (from L5 §3 (b)).
- *True:* if SEP = χ_r·Q / A_flame, then SEP × A_flame = χ_r·Q by algebra. The test only re-multiplies the number
  it divided.
- *Failure scenario:* the view-factor code has a sign error, or drops the flame's top disc, so the receivers absorb
  60% of what they should. The check still passes to round-off. Only the "absorbed power within a gated error" half
  of R2.5 can catch it.
- *Fix:* define conservation independently. Enclose the flame in a closed shell of receiver patches. The sum of
  their view-factor-computed absorbed power (ε = 1) must equal χ_r·Q, and the summation and reciprocity rules must
  hold per patch. Prove it by deletion: drop one face of the cylinder and watch the check go red.

## SHOULD-FIX

**S1. One m''_cr can't serve both ignition and extinction at the cited numbers.** `§3 item 5` ("so R0 and R1
share one law").
- *Claim:* ignition and extinction both use one critical mass flux.
- *True:*
  - R0's own data define t_ig as Q'' ≥ 24 kW/m² (V7 2c, 12). That is about 1 g/m²s, the flash point (V7 12).
  - The extinction numbers the note cites are 2.7–8.3 g/m²s (V7 1), and L1 §2.3 asks for extinction at about
    3.5–4 g/m²s.
  - V7 12 says the 24 and 66 kW/m² criteria are two different events, flash and fire point.
- *Failure scenario:* set m''_cr = 3.7 and R0's t_ig comes late against the 24 kW/m² definition. Set it to 1 and
  R1's slab burns on below the extinction band. Either R0 or R1 fails for a reason that is designed in.
- *Fix:* state two thresholds (with hysteresis), or say which rung's definition gives way.

**S2. The apparent-L_g check is circular and has no band.** `§3 "Two checks"` and `§6 R1` ("apparent L_g ≈ 15
kJ/g produced, not input").
- *Claim:* a correct char model must *produce* about 15 kJ/g.
- *True:*
  - §3 re-fits kinetics, L_g, k_c and char ε "by our model to R1's data". R1's data are MaCFP-4's curves at 30, 50
    and 60 kW/m².
  - The apparent L_g is the slope of plateau MLR against flux over that same dataset (L1 §2.2: 0.069 g/m²s per
    kW/m², hence 14.6; V7 11a: 0.064, hence 15.7).
  - So a fit that passes R1's plateau envelope reproduces the slope by construction.
  - The band is also inconsistent: L1 asks for "about 10–15 kJ/g", but V7's own fit, 15.7, lies outside it.
- *Failure scenario:* a char model with the wrong structure, fitted to the plateaus at three fluxes, still passes
  "≈ 15". The check adds nothing to the envelope check.
- *Fix:* hold out data. Fit at 30 and 60 kW/m², then predict the slope from the 25, 45 and 75 kW/m² plateaus. State
  a numeric band.

**S3. R2(a)'s oracle is a material not on the ladder, and "no spread cold" is an inference, not a measurement.**
`§6 R2`.
- *True:*
  - The 1.2 and 3.0 mm/s rates are for 1.27 cm plywood (V7 6), but §6 "Materials" lists PMMA, white pine and
    cardboard only.
  - "No opposed spread cold" is inferred from LIFT's T_s,min of 90–120 °C. V7 6 quotes the report's own warning
    that, because of the apparatus limits, "values of T_s,min < 80 °C could apply to much lower temperatures".
  - (M) Downward, opposed-flow spread over thick PMMA at room temperature in normal air is a classic measured result
    (Fernandez-Pello and Williams, of order 0.05 mm/s). If that holds, "no spread cold" is false for PMMA.
- *Failure scenario:* a correct model spreads slowly down cold PMMA and fails R2(a), which pressures tuning toward
  a wrong answer.
- *Fix:* verify the cold-PMMA case from a primary source, grade on a ladder material, or add plywood to the material
  table.

**S4. R4's oracle doesn't match what R4 would simulate.** `§6 R4`.
- *True:*
  - **Residue:** TN 2102 Test 13's "hot coals were spread out and raked into a water bath" at about 48 min (V7 3).
    The 5.3 ± 3.4% residue (7.2% for Test 13 alone) is a quenched remainder, not burnout.
  - **The pilot is not modelled:** "acetone-soaked cotton rope plus crinkle paper", 0.75 kg (L2 §3.3). Acetone,
    cotton and paper aren't in §9's components, so "with its own pilot" can't be built from the table as proposed.
  - **The geometry is not known:** L2 §3.2 says "without the crib's layout I can't tell". Only the outer dimensions
    and 3.8 cm sticks are verified.
  - **The time to peak is unverified:** "±40%" of 23 min (L2 §5) was not checked by V7, and the note doesn't state
    the 23 min.
- *Failure scenario:* the model burns to 2% at 90 min and is compared with a residue raked out at 48 min. The
  residue gate can pass or fail for the wrong reason.
- *Fix:* read the residue at 48 min, give the stick count and spacing from TN 2102, add the pilot's materials or
  substitute a cited equivalent energy, and verify the 23 min.

**S5. The note grades rates across grids while saying it never does.** `§0 item 5` ("graded on outcome class,
never rate"), `§6` intro, `R2 (a)` ("within ×2"), `R4` ("peak within ×1.5 and time to peak within ±40% on every
grid").
- *Failure scenario:* R4 fails at 0.2 m on peak rate while its class agrees on every grid. Is that a fail? The note
  says both.
- *Fix:* pick one rule and state it per rung.

**S6. "Reductions are `bincount` by region, as today" is false.** `§2.1`.
- *True:* there is no `region_id` array or `bincount` in `gates/src/simcore`. Regions are per-region boolean masks
  (`grid.py::Region.cells`), and readings are computed on demand per region
  (`frames.py::Frame.reading`: `self.cells.temperature[cells]`, max or mean). `bincount` is world_model §5 and §9's
  plan, not today's code.
- *Failure scenario:* a builder assumes element rows join an existing `bincount` path. None exists, so the element
  reduction is new code with no test pattern to follow.
- *Fix:* say "planned (world_model §5, §9)".

**S7. §10 "Decisions this revises" misses existing code and decisions that contradict the design.** `§10`, `§5.5`.
- **The bridge's region sensors.** `gates/.../bridge.py` exposes `temperature_max`, `temperature_mean`, `integrity`
  and `breached` (`frames.py::QUANTITIES`) over a whole region's cells, from anywhere. That is "an omniscient region
  instrument", which §5.5 forbids, and `breached` is a whole-entity boolean. §10 lists only `ignite` and
  `extinguish`.
- **T4's `kindle` deposit.** The deposit is "the footprint disc by face-area overlap onto the bed's skin (6b)", with
  `min_radius_m` = 0.2 (tile spec §3.2). The note replaces 6b, so `kindle` has no defined deposit. A 0.2 m minimum
  footprint also conflicts with a starter flame whose D* is 0.06–0.08 m.
- **T14.** "The flame radiates into bodies by a point source in Phase 1; into walls in Phase 2." §4.1 adds
  view-factor radiation onto surfaces in Phase 1.
- **`imagination.place`** paints primitives into cells and refuses an object "smaller than one cell at this
  resolution" (`imagination.py::_voxelize`). That is a resolution-dependent refusal, and it can't create elements.
  §9 changes what an imagined object is, but §10 doesn't list `place`.
- **T13.** Step 6 was to carry "a short design note under the Physics lens" with "no more paper rounds". This note
  supersedes that and should say so.
- *Failure scenario:* the build follows §10 as the change list and ships with the region sensors and a `kindle`
  that deposits onto a skin that no longer exists.

**S8. The cost citation isn't where the note says it is.** `§8.3`.
- *Claim:* "`advance(0.5)` ≈ 0.7 s at 1.92 × 10⁶ cells, `docs/architecture.md` Known gaps".
- *True:* neither this branch's nor `origin/main`'s `docs/architecture.md` has the line (searched `0.7 s`, `1.92`,
  `advance(0.5)`). It exists only on `gates` (`docs/architecture.md:129`, step 3b). L5 §4 flagged exactly this, and
  the note didn't fix it.
- That figure is also for a 40×8×6 m tile, while §8.3's table is for 16×10×4 m (640k cells).
- *Fix:* cite the `gates` branch and name the tile.

**S9. The wall-flame correlation is extrapolated, unflagged, and R2(b) grades against it.** `§4.1 Geometry`,
`§6 R2 (b)`.
- *True:*
  - Delichatsios and Hasemi are "tested for x_f of 0.3–1.4 m" (L2 §1.2).
  - x_f = (0.0436–0.0572)·Q'^(2/3) (D, consistent with L2's 0.043–0.057). A 1 kW flame on a 0.1 m-wide slab
    (Q' = 10 kW/m) gives x_f ≈ 0.20–0.27 m (D).
  - Ladder flames sit below the tested range, yet only Heskestad is flagged as an extrapolation.
- *Fix:* flag it, and grade R2(b)'s height only where the correlation was tested, or report it.

**S10. The n-cap test, as worded, can't go red.** `§6 "Each rung's tests"`, `§8.1`, `§8.2`.
- *Claim:* an n-cap test "feeds a sliver area and requires a bounded n and a finite T".
- *True:*
  - With the cap, n is bounded by construction. §8.2 also retires any part below (1 mm)² before the stability
    estimate, so a sliver never reaches the cap at all.
  - The test passes whether or not area hygiene (§8.2) works.
- *Failure scenario:* power is routed as W/A_part again (the K2_005 bug). The cap clips n at 16, T stays finite only
  because of the retirement, and the test is green.
- *Fix:* feed slivers both below and just above the retirement size. Assert the cap is *not* hit and the energy is
  conserved. Prove it by deleting the area-share routing and watching the test go red.

**S11. The cross-grid gates may be near-vacuous, and the design doesn't say where dx enters.** `§0 item 3`,
`§4.1`, `§6`.
- *True:*
  - Elements, patches and flames are "grid-independent by construction".
  - In Phase 1 the convective heat goes to "the outside reservoir", not to the gas cells.
  - What remains grid-dependent is the one-element-per-cell split of a straddling object (§2.1) and any coupling
    between an element and its host cell's temperature. The note never defines that coupling.
- *Failure scenario:* every "class across grids" gate (R2.5, R3, the exit) passes trivially, because the grid never
  touches the fire. Meanwhile the real dx coupling (element to cell conduction, which drives crack and integrity) is
  ungraded.
- *Fix:* name, per rung, which dx-dependent path the cross-grid gate exercises, and define the element-to-cell heat
  exchange with its closed form.

**S12. FDS's `REFERENCE_TEMPERATURE` is not a threshold law** (M, to verify in the FDS User's Guide). `§3`.
- *Claim:* "L3 recommends a threshold (T_p, L_g) by default, as FDS allows through `REFERENCE_TEMPERATURE` (V)".
- *True (M):* FDS uses `REFERENCE_TEMPERATURE` (with `REFERENCE_RATE` and `HEATING_RATE`) to *derive A and E* for its
  Arrhenius reaction. L3 itself says it "may stand in for A and E" (L3, FDS section). It is not precedent for a
  threshold law. FDS's threshold-like option is an ignition temperature with a prescribed burning rate.
- *Fix:* drop the precedent, or cite the right FDS feature.

**S13. §0.1's headline overstates Finney and Jiang, against V7.** `§0 item 1`, `§1` row "Flames heat fuel ahead by
contact".
- *Claim:* "Real fire spreads mostly by the flame *touching* fuel ahead of it", and in Jiang "upward spread is by
  contact".
- *True:*
  - V7 4 scopes Finney to fine particles of roughly 1 mm or less in wildland beds, "not a general rule for thick
    fuels".
  - V7 5: Jiang says "convection-based", not "flame contact". L2 §2 adds that Jiang's dowels are thermally thin and
    "don't transfer to 20 mm sticks".
  - The note says it follows V7 where they conflict, but this is the design's first premise.
- *Fix:* restate §0.1 with its scope. The case for flame objects survives on the spikes' own evidence.

## NIT

- **N1** `§2.2`, `§10`: "the per-cell `latent` scalar" is not a field. No `latent` exists in `src/` on either branch.
  The thing replaced is world_model §0 and §4's *planned* heat state. Say so.
- **N2** `§1` "Char handed over at 550–900 °C glows": `char_oxidation.md` says interior char at 700–900 °C glows,
  while outward faces at 550–650 °C are "marginal" under the pessimistic kinetics (lines 206–210, 382).
- **N3** `§2.2` "the accelerant spike's verified kernel": E4(i) was a "MISS as measured" and passes only under a
  post-registration deviation (`accelerant_spike/results.md` E4).
- **N4** `§5.2` "pain at ~45 s": the source row reads "Severe Pain", and the same NOAA page's default is "pain within
  60 seconds" (V7 8). "3–6×" is 2.8–5.8 over L6's four rows: fine, but say "severe".
- **N5** `§4.1` Heskestad 0.235 tagged V: L2's V source has 0.23, with "0.235 is the usual" (L2 §2.1).
- **N6** `§1` "Flames here are smaller than a cell": §0.2 gives 1.6 cells at 0.05 m.
- **N7** `§1` rows citing the accelerant and hot-surface runs: the sliver bug is in `WetBed`, so every
  accelerant-loaded run carries it, and "whether a sliver arose in them wasn't checked" (`hot_surface_spike/results.md`
  §3.2). K2_005 left outcome 6 unchecked at 0.05 m. The energy bound (about 9 W) makes this small; say it.
- **N8** `§0 item 6`, `§5.4`, `§11.4`: `ignite` was already retired by T4 and `extinguish` by world_model §8 (F7).
  Cite them; what's new is only the bridge affordance's demotion.
- **N9** `§3`, `R1` extinction "in the cited band" (24–57 kW/m²): the band spans species. The graded species' own
  value isn't in hand. V7 point 1 also notes that MaCFP-4 pine at 25 kW/m² keeps burning at about 3.8 g/m²s, so the
  pass band for white pine is effectively undefined until R1 "pins" it. Say where that number comes from.
- **N10** `§8.3` "~5 ms for 10 flames × 20,000 faces": this is 200k pairs × the measured 23 ns *point-to-face* cost.
  An analytic cylinder view factor per pair costs more and wasn't measured.

## Checked and found true

- **Code (`gates` 396ae10):**
  - `CellStore.__init__` hand-names four channels (material, original_material, integrity, temperature), and
    `frames.py::CellFrame` repeats them (fields and `__post_init__`). The §10 row is accurate.
  - `MaterialGrid.destroy` sets cells to air with no transfer.
  - `bridge.py` exposes `structure.ignite(power_w, radius_m)` and `structure.extinguish()`, on this branch too.
- **Data:** `core.yaml` wood density is 600 kg/m³; L1 gives pine about 380. T18's cap, 1 − 600/1530 = 0.61, matches.
- **Decisions:**
  - world_model: D26 defers pyrolysis and phase change, D29 and D30 define 6a–6d, §2 has positionless pools, §5 one
    owner per cell, §8 the (cell, face) table, §10 row 11 save v0 after the lanes.
  - Tile spec: T4's item power, T18's text ("spreads because its fuel is distributed", "no general solid mixtures",
    derived labels).
  - `states_of_matter/sem.md` N2.
  - CLAUDE.md's thin-features rule: 2 × 0.2 = 0.4 m.
- **Spikes:**
  - Physics: Q1 at all grids and ends; the 1,000× units bug caught by a closed form; bed flaming 449 → 575 → 770 s.
  - Accelerant: λ_max 0.0129 at 0.05 m.
  - Hot surface: outcome 5; C_F with 32.8–40.5% left; F p = 1.87 (differences 44 and 12 s give log₂ 3.67 = 1.87);
    the K2_005 sliver diagnosis; k_c 0.10.
- **V7 items, matched:**
  - 1: 24–57, 45 ± 1 and 2.7–8.3, with the paper correctly identified.
  - 2: 76–148 s and the outlier flag; 161–235 kW/m² over 4 labs.
  - 3: 798/437/334 against 485/392/389 kW and 396 ± 18 kW.
  - 5: the 13.6 and 19.8 s marked unverified.
  - 6: the derived velocities.
  - 9e: D*/dx of 1 to 118.
  - 11: k_c of 0.08–0.30.
  - 12: flash against fire point.
- **Derived numbers recomputed:**
  - D* is 0.0605 and 0.080 m at 1 and 2 kW, so 0.3–1.6 cells.
  - 0.9σ(823⁴ − 293⁴) = 23.0 kW/m².
  - 2.56×10⁶ pairs × 23 ns = 59 ms.
  - 20 × 20,000 nodes × 8 ns ≈ 3.3 ms.
  - The wall-flame coefficients 4.65 and 6.1 convert to 0.0436 and 0.0572.
- **L5:** "CN cooled on 10 of 19 steps" (θ = 0.5; 0 of 19 at 0.55 and 1); bit-identity and subset independence (for
  L5's scratch kernel, not the design's model).
- **L6 and L6b:** the NOAA rows; the MP-1 and MP-2 order and the GL2b and GL3 status (L6b §5).
- **Word budget:** 5,187 words, under the 6,000 for a new design.
- **Tests that can fail:** R0's "no surface cooling" and its thick and thin closed forms; subset independence; the
  load-time atom balance; R3(a)'s class; R2(b)'s "accelerates".
