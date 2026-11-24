# Physics and resolution: `docs/design/torch_pilot.md` at fcc6e55

I read the design and numbers.md. I checked them against fire_solid §1–§7, fire_model §3.2/§4.1/§4.3/§5.4/§6.1, tile §3.2/§6, world_model §1.1/§3, verify_harness §4, sim_core §3/§11, `src/simcore/core/scene.py`, `simulation.py`, `world.py`, `applier.py`, `data/` and the three `ignite` red gates in `tests/`. I re-derived the arithmetic by hand from numbers.md's formulas.

## Blockers

**P-B1. The target rule brings in a dx path the design doesn't name, so the target's class can change with the grid.** `docs/design/torch_pilot.md::§3` (also §0.4, §9.2). Contract.
- §3 makes every solid cell region a candidate "by its cells' faces". Cell faces depend on dx:
  - `scene.py` voxelizes primitives by cell centre (line 7).
  - Only the scene *extent* has to be aligned to 0.2 m (`_check_alignment`). Boxes and cylinders don't.
- The repo already records this failure mode. The hollow-region red gate's reason (`tests/test_act_validation.py:829-831`) says "Deciding from the region's cells would move with the grid spacing".
- tile §3.2 used the *authored box surface*. The design changes that without saying so, and §9.2 then claims floor contact is "the only place dx enters".
- Failure scenario: a concrete pillar authored at x ∈ [1.05, 1.35] m.
  - At 0.2 m its cells span [1.0, 1.4] (centres 1.1 and 1.3 are inside); at 0.05 m they span [1.05, 1.35].
  - A `kindle` at x = 0.99 is 10 mm from the pillar's voxel face at 0.2 m, so it is `applied` to a cell target. At 0.05 m it is 60 mm away, so it is `not_on_surface`.
  - Put a fuel slab 20 mm from that point: at 0.2 m the pillar wins and nothing ignites, while at 0.05 m the slab is the target and ignites. The outcome class differs across grids.
- Fix (unverified): take candidates from authored geometry, meaning primitives or region footprints in micrometres, as tile §3.2 did.

**P-B2. All three `ignite` red gates are "flipped" by moving them onto paths that cannot fail. One of them drops the guard on a gap that is still in the code.** `torch_pilot.md::§9.4`. Contract (verification gates and Known gaps).
- **`test_a_fire_that_has_burned_its_fuel_stops_heating`**
  - What it measures (`tests/test_cross_tier.py:142`): `World._power_field` putting `HeatSource` power into air.
  - The torch is not a `HeatSource` (§0.1), and nothing it does enters an air cell (fire_solid §3.1). Rewritten on the slab with `kindle`, the test therefore passes whether or not the gap exists.
  - The gap still exists. `sources` is still an input that heat resolves (`sim_core.md` §5.1, §6). `World._power_field` and `HeatSource` are still in `src/simcore/core/world.py`.
  - fire_solid §3.1 names this exact gate as the strict red gate for `_power_field`'s fallback. Removing it, as §9.4 says to, leaves that Known gap with no gate.
- **`test_the_fiercest_allowed_fire_…`**
  - Its bar is `agrees(integrity).spread <= 0.1` plus the peak cell temperature.
  - On a fuel target, `region_integrity` is refused for an object-only region (fire_solid §2), so the test can't measure its bar.
  - On a cell target, §4.4 deposits nothing, so integrity stays 1.0 and the spread is 0. That version cannot fail.
- **The hollow-region gate:** its replacement ("`kindle` on a hollow cell region heats no air") also cannot fail, because §4.4 deposits nothing on a cell target.
- Failure scenario: the PR goes green with three gates "flipped", while `_power_field` can still pour 207,350 °C into air from any remaining source producer.
- Fix (unverified): keep the burned-fuel gate strict until `sources` or the fallback is retired by name. Write any rewrite against a bar that a deletion can turn red.

**P-B3. The cross-grid time gate has no bar.** `torch_pilot.md::§9.2` ("agree by `verify_harness.md` §4's `agrees`"). Contract.
- `agrees` only reports a spread, per-grid errors and `converging`. verify_harness §4 says: "The test keeps its own bar on the spread."
- §9.2 gives no tolerance for `t_flash`, `t_char` or `t_out`. tile §6.3 item 8, which this replaces for the slab, had 15% and 10% against 0.05 m.
- Failure scenario: `t_out` sits at 1,200 s at 0.05 m and 1,900 s at 0.2 m, converging monotonically. The gate passes because only class and monotonicity are checked.
- A bar written now must be derived from its source's error and written before measurement (CLAUDE.md, the three kinds of bar). None is written.

## Should-fix

**P-S1. Before flash, the torch is not "the cone heater made local", so the 65 kW/m² ceiling's derivation doesn't hold.** `torch_pilot.md::§0.1, §4.2, §6`. Contract (the `actions.yaml` ceiling).
- How the graded runs differ from the torch:
  - fire_solid §4.4 keeps convective loss *on* until flash. The torch turns it off on its share from the first tick.
  - The cone heater is radiant. The torch is mostly convective (M), and its absorptivity is unstated (P-S2).
- So a torch at gauge flux q delivers more net flux than a cone heater at q, by about h_c(T_s − T∞), plus (1 − ε)·q if the cone's heater is absorbed at ε.
- Numbers (derived, illustrative, from tile §5.1's h_c = 10 and ε = 0.9, both M): near ignition at about 350 °C the convective term is 3.3 kW/m², and the absorptivity term is 6.5 kW/m² at 65. A 65 kW/m² torch therefore acts like a cone heater of about 75 kW/m².
- That is past PMMA's highest graded flux (65). Both are past the FDS-verified range (25 and 50; fire_solid §4.6: "65 kW/m² isn't verified, and neither is the flame path").
- Failure scenario: a PMMA `kindle` at the ceiling runs outside the regime that was graded, while §6 claims it doesn't.

**P-S2. The torch's absorptivity is unstated.** `torch_pilot.md::§4.2, §5`. Contract.
- "Absorbed at the surface node" doesn't say whether the energy is q''_t·A or ε·q''_t·A.
- fire_solid §5.4's `incident_absorbed`, the ledger close in §9.2, and every beat time depend on that choice.
- Pine's char ε is a *fitted* free parameter (fire_solid §4.5). If the deposit is ε-weighted, the fit silently changes the torch after char forms.
- Failure scenario: the solver and the ledger implementations make different choices. The ledger still closes, because both sides use "the same f64 expression", but `t_flash` is about 10% off from what the design intends.

**P-S3. The Known gaps are incomplete, and one has no numbers.** `torch_pilot.md::§7`. Contract (CLAUDE.md: Known gaps come with numbers).
- **The cold-gauge overstatement is given without a number.** A lower bound exists from the repo's own h_c: ≥ 3.3 kW/m² at T_s = 350 °C, more under an impinging flame. That is 5–13% of the 25–65 range, unstated.
- **Missing: a validation gap on the ignition criterion.** m''_flash is fitted to cone t_ig, under a spark pilot and a radiant heater (fire_solid §4.5). Applying it to flame-impingement piloting, where the pilot flame sits in the volatile stream, is an extrapolation. It should be named as a validation gap.
- **Missing: the energy that misses the slab.** §6 requires r_t ≥ W, which forces overhang. At r_t = W = 0.1 m, the disc's area is 0.0314 m², while its overlap with a long slab is ≤ 2r_t·W = 0.02 m². So at least 36% of the torch's energy is discarded beside the slab: it never heats the floor or the slab's edge.
- **Missing, if Q2 is adopted:** q''_fl is a cone-fitted constant applied to every flaming part in the world.

**P-S4. The exit slab's length and burning area are not specified, and "stays clear of the strip gap" is overstated.** `torch_pilot.md::§6, §7`. Contract (the exit scene).
- The width of 0.1 m is justified by R1's 0.01 m² sample, because m''_ext depends on sample size (fire_model §4.3).
- But in Phase 1 nothing spreads (§5: only piloted parts flash). The burning area is therefore the set of strips under the disc, about 2r_t × W ≥ 0.02 m² for r_t ≥ W, unless the slab is 0.1 m long. No length is given.
- Separately, at W = r_t, 16% of the footprint's energy lands in partly covered end strips (numbers.md: 0.836 in fully covered strips). Those strips flash on a strip mean, so the exit still contains the averaging-then-thresholding error. §7's "the exit stays clear of it" is not true.

**P-S5. Not every binary outcome in the exit is band-gated.** `torch_pilot.md::§9.2`. Contract.
- Only flash, controlled by D, is band-gated.
- "Flames out before the cap" is binary, and world_model §3 names "goes out" as an outcome that must be band-gated. "Char reached" (≥ 0.1) is binary too.
- With Q2 adopted, q''_fl can keep flaming going for a long time. Pine with the heater on flames out at 2,050–2,301 s at 25 kW/m² (fire_solid §4.4). So `t_out` against the 5,400 s cap is not obviously far from its threshold.
- Failure scenario: flame-out flips at one grid or step, and no band records it.

**P-S6. The time-refinement path is not named, and the energy formula hard-codes the tick.** `torch_pilot.md::§5, §9.2`. Contract for the formula; mechanism for the study.
- §9.2 requires the beats "at dt and dt/2" and the band at 0.5 and 0.25 s steps.
- `substep_refine`, which sim_core bar 2b relies on, doesn't refine the solid: it runs "independent of dx and heat's substeps" (fire_solid §4.3). A 0.25 s step therefore needs a different `SimConfig` (`tick_us` or `physics_every`; `simulation.py:60-61`), and the design doesn't say which.
- §5's energy is "q''_t · A_ov,p · 0.1 s · n_t". With `tick_us` = 50,000 that delivers twice the energy, and a D given in ticks halves the hold.
- Fix (unverified): write the formula with `tick_us`, and state D in world seconds converted to ticks.

**P-S7. New bars are not derived from their sources.** `torch_pilot.md::§9.2` (in time), §6 and §9.2 (the 2× band margin).
- fire_solid §6's max(0.5 s, 3%) was set for t_ig in a grid-free cone unit test. Here it is extended to `t_char` and `t_out`. At a `t_out` of about 2,000 s, 3% allows a 60 s difference, and nothing derives that from the first-order scheme's error at 0.5 s.
- The 2× margin is tile's `[engineering]` round number reused. Neither number is derived, and neither is listed in B30.

**P-S8. The strip-halving control can't see the error it is meant to guard.** `torch_pilot.md::§9.4`. Mechanism (a build-step test).
- The control fails on "a different class, or `t_flash` past max(0.5 s, 3%)".
- `t_flash` is set by the central, fully covered strips, which halving doesn't change. The partly covered strips, where segment size matters, never enter `t_flash`.
- Failure scenario: a bug in the area transfer of partly covered strips passes the control.
- fire_solid §6's non-uniform-heater test already shows the right observable: times to 25, 50 and 75% ignited area.

## Nits

**P-N1. §7's "346 K of face rise at the ceiling" uses 75 kW/m²; the ceiling is 65.** At 65 kW/m² for 60 s the rise is 2·65,000·√60 / √(π·1.7·2400·880) ≈ 300 K. Verified (arithmetic from numbers.md's formula and `data/materials/core.yaml`). It is still past the 300 °C onset, but only barely.

**P-N2. §5 cites "the one-flash cap" as fire_solid §4.4's.** fire_solid has no cap mechanism. It only says R0 and R1 "count flashes per part and require at most one" (a test). The design also leaves open what happens when a piloted part goes out *under* a long hold, which is plausible on pine given the heater-on flame-outs above.

**P-N3. §9.1 beat 4's 0.1 is labelled "as tile §6.3 item 3's 10%", but the quantity is different.**
- tile §6.3 means 10% of the fuel charred. fire_solid §5.6's residue share is residue mass ÷ remaining solid mass.
- With an illustrative char yield of 0.2 (unverified for the chosen set), a share of 0.1 corresponds to about 36% of the virgin material converted, depth-averaged, which also depends on slab thickness.
- The `[engineering]` tag is honest; the "as tile's 10%" label is misleading.

**P-N4. Every rod `kindle` is an extrapolation, and §7 should say so.** The ring mean is at most q''_t/π, which is 20.7 kW/m² at the ceiling. That is below every graded flux.

**P-N5. §9.1 beat 7's "`end_tick` ≤ `t_out`" can't fail.** Beat 6 defines `t_out` as a step after `end_tick`, so the clause is true by definition.

**P-N6. §3's "which every `slab` recipe's geometry range does" asserts something about files that don't exist.** No recipe file exists at fcc6e55: `data/` holds only materials, rigs and world. The thickness > 1 mm condition needs a catalogue refusal, owned by fire_solid §5.1, rather than a claim about data that hasn't been written.

**P-N7. numbers.md computes the 0.836 and 0.973 figures with the disc centred on a strip boundary.** The fully covered share depends on where the centre sits within a strip, so it should be reported as a range over offsets.

**Checked and found sound:** the closed form for the concrete face rise and the 21.3 K cell mean; the 0.195 and 0.973 coverages and the 1/π rod share; the deposit having no dx term (exact area overlap, energy prorated by tick); pairing re-radiation with convection off under the gauge convention; the hysteresis guard m''_ext < m''_flash; the ledger booking under `incident_absorbed`.

Count: 3 BLOCKER, 8 SHOULD-FIX, 7 NIT.
