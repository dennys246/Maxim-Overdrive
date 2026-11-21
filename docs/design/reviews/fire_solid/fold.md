# Fold: `fire_solid.md` design review, round 1 (2026-11-20)

The six reports are kept verbatim beside this file. Each row gives the finding, where the revision answers it, and
its status. **Reviewers set the statuses** (O25); every row starts `open`. Prefixes: EX Executor, A Architecture, WT
Wire and trust, P Physics, FS Determinism and performance, BF Bio-faithful.

Counts: 16 BLOCKER, 55 SHOULD-FIX, 27 NIT. The revision is 5,989 words by `wc -w`.

**The author's eight decisions were followed.** Where the evidence changed one in detail:
- **Decision 4.** `core.yaml`'s fields don't change, so it stays at v0 with no migration. The new files start at
  `version: 0`, as every format here did. "Material data v1" names the split, not a version number. Variants moved
  into their recipe files, which removes a cross-file reference; there is no `variants.yaml`.
- **Decision 6.** m''_ext is taken first from the *fit* fluxes' recorded flame-outs. The 25 kW/m² values
  (Executor S1) are a cross-check, and the fallback if the fit fluxes record none, with the leak named. Reason:
  25 kW/m² is a graded flux, and the SHOULD-FIX "no held-out data for bounds" applies.
- **Decision 7.** In-depth absorption is implemented, not FDS switched to surface absorption. Surface absorption
  moves FDS's peak by −6.2% and +42 s at 50 kW/m² (D, EX-B2), and that error would land in q''_fl during
  validation.
- **The threshold law (a) is dropped.** This follows from fixing MaCFP's published kinetics: (a) would need fitted
  T_p and L_g.

**New measurement (D).** FDS 6.11.1, NIST-StMU-FSRI at 25 kW/m², `T_END=1500`, with `CELL_SIZE_FACTOR=0.5`
against the inputs' cells. Run in `_durable/fire_solid_review/scratch/fold/n25_fine/`; features in
`scratch/fold/features.txt`:
- peak 10.03 → 9.92 g/m²s, at 889.5 → 919.5 s;
- the peak is within 1% of its value over 797–984 s, so peak time isn't graded at 25;
- time to half the peak 352.5 → 354.0 s;
- surface temperature at 300 s 348.0 → 351.1 °C.

## Executor

| Finding | Where answered | Status |
|---|---|---|
| EX-B1 PMMA inputs are gasification, no 65 | intro; §4.6 (gasification at 25 and 50; 65 and the flame path not verified) | open |
| EX-B2 FDS gate can't pass without in-depth absorption | §4.1 (in-depth absorption implemented); §4.6 | open |
| EX-B3 coupling-frequency check can't fail in R1 | §3.2 Frequency; §6 coupling frequency on the floor scene, with a guard clause | open |
| EX-B4 segment halving can't fail | §1.2 (flip whole, front moves by segment); §6 non-uniform heater | open |
| EX-B5 `_power_field` missed; object-only regions send power to air | §2 (`fuel_only_region`; `_power_field` row); §3.1 guard | open |
| EX-S1 pine m''_ext band contradicted by data | §4.4 (m''_ext from pine's flame-outs, about 1 g/m²s) | open |
| EX-S2 heater removal has no data | §4.5 (a prediction, not graded) | open |
| EX-S3 "sustained" has no window | §4.5 (MaCFP's first crossing graded; sustained reported, ungraded) | open |
| EX-S4 save validator refuses mid-burn saves | §1.1 (one mass truth); §5.5 (conservation) | open |
| EX-S5 "today's" facilities don't exist | §0 table; §5.1 (no migration, canonical digest); §5.2 (scene v0) | open |
| EX-S6 `surface_temperature_c` u8 clips | §5.6 (f16) | open |
| EX-S7 consumer table misdescribed and incomplete; integrity 0.0 | §2 table, rewritten from the code | open |
| EX-S8 borrowed tolerances | §6 (each tolerance stated) | open |
| EX-S9 tolerance within FDS's spread; node layout; T_END | §4.6 (same layout, `T_END` 1,500 s, tolerance from the measured spread) | open |
| EX-N1 RAMPs not in the PMMA sets | §4.1 | open |
| EX-N2 inert residue in NIST-StMU-FSRI | §4.2 Residue | open |
| EX-N3 FDS's (ρ/ρ0)^n normalisation | §4.2 | open |
| EX-N4 L1 §2.3 is cardboard | §4.5 (q''_fl) | open |
| EX-N5 lab and flux confounded; plan row says "never fitted" | §4.5 (results per lab); §0 (plan row revised on acceptance) | open |

## Architecture

| Finding | Where answered | Status |
|---|---|---|
| A-B1 object-only regions pass act and entity gates | §2 (acts, readings and `region_parts` refuse `fuel_only_region`) | open |
| A-B2 build order can't be executed | §0 (dependency table; 6.0a with 5a, 6.0b after 5b; plan row) | open |
| A-S1 ambient rule mis-framed, unguarded, under-costed | §3.1 (tile 6a, Phase 1 rule, Known gap with three costs, plume corrected, guard test) | open |
| A-S2 cell 6a and skin lost owner; contact to cell mean | §3.2 (contact through a metric skin); §7 (every face under 6.2) | open |
| A-S3 `CellStore` god object, copies every table | §1.1 (`FuelStore`, composed window, copy on first write) | open |
| A-S4 placement table too coarse | §7 Placement (per layer; harness in `tests/fire/`) | open |
| A-S5 delta-round ids unowned | §7 (every delta-1 id) | open |
| A-S6 spec v1 and limits with no caller | §5.2 (the `imagine` intent is the caller; thin, said so) | open |
| A-S7 snapshot frozen with no consumer; u8 | §5.6 (requirements for the client pass and step 7; f16; extensible) | open |
| A-S8 save rules, mass truth, dropped name map | §1.1; §5.1 (declared ids); §5.5 (name maps, `contact` rebuilt) | open |
| A-S9 front position frozen early | §1.1 (no front column); §1.2 (flip whole; partial transfer is 6.2's) | open |
| A-S10 material v1 freezes before R0's choice | §4.2 (one rate law, Arrhenius; RAMP schema in §5.1) | open |
| A-N1 no header "as today" | §0; §5.1 | open |
| A-N2 no migration registry | §5.1 (no migration needed); §5.2 (bump and refusal) | open |
| A-N3 R0's loser deleted | §4.2 (law (a) not built) | open |
| A-N4 frequency check belongs to the floor scene | §6 | open |
| A-N5 geometry per kind | §1.1 | open |
| A-N6 fixtures' source and licence | §5.1 | open |

## Wire and trust

| Finding | Where answered | Status |
|---|---|---|
| WT-B1 occupancy table incomplete; receipts lie | §2 | open |
| WT-B2 save has no format; rule contradicts its test | §5.5 (requirements on step 9); §6 (rebuild digest) | open |
| WT-B3 material v1 breaks the landing order | §0 | open |
| WT-S1 `region_id` doesn't exist; region rule; exhaustion | §0; §1.3 Regions; §5.3 `region_ids_exhausted` | open |
| WT-S2 checks race their own batch | §1.4 (`pending`); §6 | open |
| WT-S3 recipe id stability | §5.1 (declared ids, sorted loading, retired list); §5.5, §5.6 (name maps) | open |
| WT-S4 no owner for cross-file references | §5.1 (`FuelCatalogue`; variants in recipe files; no migration) | open |
| WT-S5 `limits.yaml` has no version or loader; directory test | §5.1 (v0, `load_world_limits`, per-file readers) | open |
| WT-S6 scene and spec version chain | §5.2 (tile §1.3 drops `bed:`; bump and refusal; structural spec unchanged) | open |
| WT-S7 header contradicts boundaries §6.3 | §5.1 (logical names, canonical digests, recipe-set digest) | open |
| WT-S8 all-or-nothing doesn't reach the tables | §1.1 (composed window); §1.4 Scene build; §6 | open |
| WT-S9 snapshot columns incomplete | §5.6 | open |
| WT-S10 coupling rows unbudgeted, scale with dx | §1.3 (contact rows only, bound at 0.05 m) | open |
| WT-S11 refusals not named; overlap judged on cells | §5.3; §1.3 (metric overlap, `outside_world`) | open |
| WT-N1 no committed golden; empty tables | §5.4; §6 (5a's goldens) | open |
| WT-N2 `CellFrame.reading` doesn't exist | §2 (`Frame.reading`) | open |
| WT-N3 `content/` arrives at step 8 | §5.1 (Apache fixtures until then) | open |
| WT-N4 ledger line unnamed; tile's lines | §5.4 Ledger | open |
| WT-N5 `_on_region` refuses nothing | §2 | open |

## Physics

| Finding | Where answered | Status |
|---|---|---|
| P-B1 flash and extinction toggle | §4.4 (hysteresis required, data-based m''_ext, ≤ 1 flash, dt-halving test) | open |
| P-B2 segment halving and frequency checks can't fail | §6 (non-uniform heater; floor scene) | open |
| P-B3 FDS verification compares different physics | §4.1; §4.6. The stepped-flux flame case is not adopted: no 6.1 gate | open |
| P-S1 sustained t_ig isn't the data's definition | §4.5 | open |
| P-S2 more parameters than features | §4.5 (published kinetics fixed; count rule; seeds; gasification validation) | open |
| P-S3 held-out flux constrains the fit | §4.4 (fit fluxes first, named fallback); §4.5 (margin 1.1·m''_ext) | open |
| P-S4 q''_fl's hidden convective loss, miscitation | §4.4 (convection off while flaming); §4.5 (citation corrected, flagged) | open |
| P-S5 no window; char oxidation off; ΔH_c | §4.5 (windows, MLR grading, ΔH_c from fit fluxes) | open |
| P-S6 one backing against several | §4.1; §4.5 (per lab, or ungraded) | open |
| P-S7 solid's dt unspecified | §4.3 (0.5 s, dt convergence, fallback); §4.6 | open |
| P-S8 law (a) at node mean; PMMA regression | §4.2 (law (a) dropped); §4.3 (regression rule); §6 node halving | open |
| P-S9 contact to cell mean depends on dx | §3.2 (skin); §6 closed form | open |
| P-N1 "once per material" against forward and reverse | §4.5 (both must pass) | open |
| P-N2 edge fit has no consequence | §4.5 (flagged pass, to the owner) | open |
| P-N3 spark has no energy | §4.4 | open |
| P-N4 m''_ext band is timber; PMMA envelope | §4.4 (band dropped; PMMA unset); §4.5 (two labs) | open |

## Determinism and performance

| Finding | Where answered | Status |
|---|---|---|
| FS-B1 save validation; two mass truths | §1.1; §5.5 | open |
| FS-B2 mid-step `imagine` undefined | §1.4 (option (b), as decided) | open |
| FS-S1 n ≠ 1 update makes mass | §4.2; §6 | open |
| FS-S2 `holds_fuel` by float rounding | §1.3 (contact and occupancy by metric thresholds, integer edges); §6 straddle | open |
| FS-S3 coupling rebuild trigger; derived table saved | §1.1; §5.5 | open |
| FS-S4 CSR offsets O(cells) | §1.1 (sorted COO) | open |
| FS-S5 window copies tables twice | §1.1 (copy on first write) | open |
| FS-S6 no cost row; strips vs tiles | §1.2 (strips); §1.3 (limits from the budget) | open |
| FS-S7 work counter counts a constant | §6 (counters at the world limits) | open |
| FS-S8 ragged layout, offsets on load | §1.2 Layout; §5.5 | open |
| FS-S9 area transfer mixes profiles | §1.2 (flip whole in 6.1; zero-area rule) | open |
| FS-S10 every-step save test where nothing exists | §6 (rebuild digest on a floor scene with an `imagine` and a burnout); §5.5 | open |
| FS-S11 offset test missing | §4.2 (`np.where`); §6 | open |
| FS-S12 contact scheme | §3.2 (Robin, implicit, one expression) | open |
| FS-N1 persisted ids, name maps | §0; §5.5 | open |
| FS-N2 counter edges; burnt-out rows | §1.1 | open |
| FS-N3 empty tables in the digest | §5.4 | open |
| FS-N4 reductions by `bincount` | §5.4 | open |

## Bio-faithful

| Finding | Where answered | Status |
|---|---|---|
| BF-B1 `temperature_*` widened under the same name | §2 (cell-only, pinned; object quantities get new names, lab-only) | open |
| BF-S1 `structure` on object-only regions | §2 (`region_parts` refuses; affordances pinned) | open |
| BF-S2 integrity 0.0 | §2 (`Frame.reading` refuses, never 0.0) | open |
| BF-S3 NPC note has no trigger; ids unlisted | §7 (trigger; ids listed; bridge untouched) | open |
| BF-S4 reduction weighting | §2 (no object reduction in 6.0–6.1) | open |
| BF-N1 `kindle`'s target lost | §2 last row; §7 | open |
| BF-N2 snapshot names diverge from fire_model | §5.6 | open |
| BF-N3 pin the instrument set | §6 | open |

## Not folded

- **P-B3's third fix** (an FDS case whose flux steps up by q''_fl at a forced flash): left as an option. The flame
  path has no FDS gate in 6.1; it is said in §4.6.
- **The plan's step 6 row, the 5a checklist's region-id item and tile §1.3's `bed:`** are edits to other documents.
  This revision names them and their moments (§0, §5.2) but doesn't make them.
