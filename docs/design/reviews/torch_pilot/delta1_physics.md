# Physics and resolution, delta round 2: `docs/design/torch_pilot.md` (fold over fcc6e55, uncommitted)

I read the folded design whole, along with numbers.md, fold1.md, the diffs to checklists.md and contracts.md, fire_solid §3.1, §4.3–§4.6 and world_model §3 and §5. I also read the footprint code in `src/simcore/core/scene.py`. I re-ran numbers.md's concrete march at 45 kW/m² to find the onset time (scratch file `/private/tmp/claude-501/march.py`).

## 1. Status table (my statuses, read from the tree)

| Id | Status | Evidence |
|---|---|---|
| P-B1 | fixed | §3 takes cell regions "by its authored footprint… never measured by its cells". Distances are f64 from `point_mm`/1000, so no dx term is left. The geometry it now relies on is underspecified: see P2-S1. |
| P-B2 | fixed | §0.6 and §9.4: none of the three gates is rewritten, and each stays strict until its mechanism is deleted (Q6). Beat 8 is a new gate, and deleting extinction turns it red (through beat 6 first). |
| P-B3 | fixed | §9.2 now has a written cross-grid bar, max(e_dt, one physics step). Its derivation is a new defect: P2-S2. |
| P-S1 | fixed | §4.2 keeps losses on before flash, as fire_solid §4.4 does. The §6 ceiling is min ε_r·50 kW/m². I checked that a torch at ε·q, absorbed whole, with the same losses, matches a cone at q absorbed at ε, before and after flash. 50 kW/m² is the highest flux both rungs grade, and FDS verifies PMMA at 50 (fire_solid §4.5, §4.6). What remains is in P2-S3 and P2-S4. |
| P-S2 | fixed | §4.2: "Absorbed whole at the surface node `[engineering]`". The ceiling is consistent with it. |
| P-S3 | fixed | §7 names the cold-gauge residual with h_c's 3.3 kW/m² (h_t is honestly uncited), m''_flash's validation gap, the energy that misses the slab (22% and 39%, which match numbers.md's 0.781 and 0.609), and the Q2 extrapolation. |
| P-S4 | fixed | §6: the length is content's, and r ≥ W/2 makes the burning area at least 0.01 m², R1's sample. §7 now says the gap is "reduced… not absent". |
| P-S5 | fixed | §9.2 has a margin rule covering flash, char and out. Its floor degenerates: P2-S5. |
| P-S6 | fixed | §5: E_p,t is written with `tick_us`/10⁶ and n_t over `physics_every`, holds are in world seconds, and the time study halves `tick_us`. |
| P-S7 | fixed | max(0.5 s, 3%) and the 2× margin are dropped, and B30 is raised as Q8. The replacement bars have their own defects: P2-S2 and P2-S6. |
| P-S8 | fixed | §9.4 now uses the times to 25, 50 and 75% of the final flaming area. |
| P-N1 | fixed | §7 gives concrete at the new ceiling: 208 K lossless (closed form) and "about 190 K" with losses (numbers.md: 187). The onset time it quotes is wrong: P2-N1. |
| P-N2 | fixed | The cap is gone from §5, and reflash is allowed only when piloted. Beat 3 now contradicts that: P2-S7. |
| P-N3 | fixed | §9.1 beat 4 is `[engineering]` alone. |
| P-N4 | fixed | §7 gives 14.3 kW/m² at the 45 kW/m² ceiling, and calls every rod `kindle` an extrapolation. |
| P-N5 | fixed | Beat 7 now reads "`t_flash` < `end_tick`, and `t_char` < `t_out`". Both clauses can fail. |
| P-N6 | fixed | §3 and §10: the catalogue refuses slab recipes ≤ 2 mm, as a fire_solid §5.1 edit. |
| P-N7 | fixed | numbers.md takes every figure over 40 offsets, and §6 and §7 quote ranges. |

## 2. Delta findings

No new blockers.

**P2-S1. A cell region's "authored footprint" is today a bounding box, and §3 doesn't say which geometry it measures.** `torch_pilot.md::§3`. CONTRACT (the target rule).
- What the code holds:
  - `scene.py::footprint_of` returns "their joint bounding box and volume-weighted centroid".
  - The exact CSG shape is world_model §5's future plan ("The fix is to make each region's authored shape exact").
- What the design leaves open:
  - §3 says "one fixed formula per kind" but names no kind for a cell region.
  - It cites `sim_core.md` §7 for the footprint quote. That sentence is in `world_model.md` §5 (line 126), and grep finds it nowhere in sim_core.
- Failure scenario 1, a cylinder:
  - Take a concrete cylinder pillar of r = 0.15 m.
  - A point 40 mm from its bounding box's corner is about 102 mm from the cylinder surface.
  - Measured on the box, it is `applied` to the pillar. Measured on the cylinder, it is `not_on_surface`.
- Failure scenario 2, a hollow box:
  - Put a fuel slab inside a hollow concrete box (a crate or oven). A point on the slab's top is "inside a candidate deeper than 50 mm" if the box counts as solid.
  - Whether that point is refused, or goes to the slab at distance 0, depends on an order between §3's clauses that the text doesn't give.
- Either way, two implementations both comply and disagree on the receipt class.
- Fix (unverified):
  - Name the geometry for each kind: box, cylinder, or CSG minus carved air.
  - State that the "inside deeper than 50 mm" test applies only when no candidate is within 50 mm.
  - Correct the citation.

**P2-S2. The cross-grid bar is taken from the time-step error, not from the spatial error it gates.** `torch_pilot.md::§9.2` ("Across grids… within max(e_dt, one physics step)"), and §7's red gate, which reuses "the §9.2 time bar". CONTRACT (a verification bar).
- The rule: CLAUDE.md requires a bar "derived from its source's error (a closed form's from the scheme's error at the spacing…)".
- The only dx path §9.2 names is the floor contact, a spatial coupling. e_dt measures the solid's first-order time error, which is a different source. Nothing ties the floor coupling's error at dx = 0.2 m to e_dt.
- Failure scenario:
  - `t_out` is about 2,000 s and set by the back face, which the floor backs (§7: "its back-face behaviour is a prediction").
  - The 0.2 m floor cell's mean temperature under the slab differs from the 0.05 m one, so `t_out` moves by tens of seconds.
  - e_dt is a few seconds, so the gate goes red.
  - "Fix the physics" then has no derived target. The pressure is to redefine the bar after measurement, which the same rule forbids.
- Fix (unverified):
  - Derive the cross-grid bar from the floor coupling's own error at each spacing, for example a closed-form or refined-floor reference for the contact.
  - Or prove the coupling dx-free and keep max(e_dt, step) only as the measurement's resolution.
- §7's red gate compares two different scenes (a plank against a slab), so it needs its own derivation as well.

**P2-S3. PMMA under the torch runs outside the verified configuration, and §7 doesn't say so.** `torch_pilot.md::§4.2, §6, §7`. CONTRACT (Known gaps).
- Where the configurations differ:
  - §4.2 absorbs the torch at the surface node.
  - The PMMA sets that FDS verifies and the cone grades absorb in depth (fire_solid §4.1: κ 2,620–3,421 m⁻¹, applied "on both sides").
  - The ceiling argument equates only total absorbed flux, not where it is absorbed.
- Fire_solid gives the size: surface absorption moves FDS's peak by −6.2% and +42 s at 50 kW/m² (§4.1). That is the size of a `kindle`-on-PMMA error, and no gap or bar records it.
- Separately, §6's "FDS verifies" 50 kW/m² is true for PMMA only. The §4.6 inputs are NIST-StMU-FSRI PMMA, so pine's ceiling rests on grading alone.
- Fix (unverified): add a §7 gap with the −6.2% / +42 s number, and qualify §6's basis per material.

**P2-S4. ε_r is ambiguous for pine, and one reading makes a data ceiling depend on a fitted parameter.** `torch_pilot.md::§6` ("min over shipped recipes of ε_r · 50 kW/m²"). CONTRACT (`actions.yaml`'s `max_flux_w_m2`).
- Pine has a fixed virgin ε and a fitted char ε (fire_solid §4.5: "Free: … pine … char ε"). §6 doesn't say which one ε_r means, or whether to take the minimum of both.
- If char counts, a refit of R1 moves `kindle`'s published ceiling, a versioned data value, through a fitted parameter. That breaks the claim that "Nothing is fitted to make the exit pass" in spirit.
- If only virgin counts, a pre-flash surface that has already charred (a slow low-flux heat-up) receives more than the cone-equivalent 50 kW/m².
- Fix (unverified): define ε_r as the minimum over the recipe's fixed ε values. Any char-surface excess then goes to §7 with its number.

**P2-S5. The margin rule has no floor, so a measured spread of zero gives a zero margin.** `torch_pilot.md::§9.2` ("held from its threshold by at least that threshold's spread"). CONTRACT (world_model §3's operating-point margin).
- Why a zero spread is likely: holds are whole coarsest ticks, and band edges and beat times are quantised to physics steps. So the spread of D's band edge across three grids and two steps can easily come out as 0.
- Failure scenario:
  - The spread is 0, so D is set exactly on the highest upper edge.
  - Across machines, where only the class is promised, a last-ulp difference flips flash against no-flash at D.
  - The same thing happens to "out before the cap" when `t_out`'s spread is 0.
- Fix (unverified): margin = max(spread, one quantum of the quantity: one coarsest tick for D, one physics step for times), stated now.

**P2-S6. The in-time check names two steps but needs three, and "≤" doesn't test first order.** `torch_pilot.md::§9.2` ("at `tick_us` and `tick_us`/2 … with |t(dt/2) − t(dt/4)| ≤ |t(dt) − t(dt/2)|"). CONTRACT for the bar's form; MECHANISM for the runs.
- Three steps are needed: the inequality needs a dt/4 run, which the text never schedules. The margin rule, and §0.6's controls, speak of "the two steps", and fire_solid §4.3 runs dt, dt/2 and dt/4.
- "≤" is not a convergence test:
  - It passes on equal differences, which is a stall, not convergence.
  - On step-quantised beat times it fails on noise. For example, t(dt) − t(dt/2) = 0 by quantisation, then t(dt/2) − t(dt/4) = 0.125 s goes red with no physics error.
- First order means a ratio of about 2. The rule is stated as "the first-order scheme converging", but the test can't show it.
- Build step 6.1b should carry the test: interpolate crossing times within the step (the beats' resolution), then check the ratio against a bound derived from the scheme.

**P2-S7. Beat 3 forbids a reflash that §5 allows.** `torch_pilot.md::§9.1` beat 3 ("each part flashes at most once") against §5 ("A part that goes out may flash again only when piloted"). CONTRACT (the exit's beat and the pilot condition).
- Why a reflash can happen in the exit: with Q2 adopted and a long hold, pine under a growing char layer can drop below m''_ext while the torch is still on. Fire_solid §4.4 records heater-on flame-outs at 2,050–2,301 s at 25 kW/m². The pilot then legitimately reflashes the part.
- So beat 3 goes red on physics that the design permits, and the easy way out is to shorten D.
- Fix (unverified): either assert at most one flash per pilot-free interval, or make the cap a model rule in §5. Choose one, not both.

**P2-S8. Superposing torch and flame flux after flash is an unnamed validation gap.** `torch_pilot.md::§4.2` ("pilors in key order, then the flame flux") and §7. CONTRACT (Known gaps).
- What the model does: after flash, while the pilot is live (beat 7 requires `t_flash` < `end_tick`), a part receives q''_t + q''_fl with convective loss off.
- Why that is unsupported:
  - Both are gauge fluxes from flames, and §4.2 calls q''_t mostly convective.
  - Two impinging flames on one surface share one boundary layer, so their convective gains don't add.
  - The cone's additivity is radiant heater plus flame, not flame plus flame.
- Effect: m'' during the hold is overstated, which moves `t_char` and possibly `t_out`. No gap records this.
- Fix (unverified): name it in §7, with its bound q''_t·A_ov·(end_tick − t_flash) of energy.

**P2-S9. The checklist dropped the §9.2 measurements.** `docs/plans/checklists.md` step 6, "Added by D-B2". MECHANISM (process).
- The fcc6e55 list had "the band in D at three grids and two steps (§9.2)". The folded list has no time study, no cross-grid study, no band or margin measurement, and no ledger-close test.
- §9.2 says "values at 6.1b", and §6 needs D and the cap set from those measurements. No build step now owns them.
- The list should go back to 6.1b, alongside the §6 ceiling refusal test and the E_p,t one-expression test (ledger and solve share it).

**P2-N1. §7's concrete onset time is the lossless figure, while the sentence is about the case with losses.** "It reaches concrete's 300 °C onset only past about 110 s."
- Lossless, a 280 K rise at 45 kW/m² takes 60·(280/208)² ≈ 109 s.
- With losses, numbers.md's march (ε 0.9, h 10) reaches 280 K at 150 s. It reads about 3% low, so the true time is about 140–150 s.
- Verified: I ran the march at dt 0.5 s. "Past 110 s" is a true lower bound, but it is the wrong number to quote.

**P2-N2. §6 says "All values are fixed and committed before the first exit run", but §9.2 sets D and the cap from measured runs of the exit scene.**
- That is ordering, not fitting.
- State it as: q''_t, r_t and the recipe are fixed first, and D and the cap follow from the 6.1b band measurement, then are frozen before step 8's exit.

**P2-N3. numbers.md says the with-loss rises "read about 3% low", but §7 quotes them as "about 190 K" without that correction.**
- The corrected value is about 193 K. The difference doesn't change the conclusion.

## Counts

Statuses: 18 fixed, 0 deferred, 0 rejected, 0 open. Three of the fixes are fixed only as stated, with their residuals filed as new findings: P-B3 (P2-S2), P-S5 (P2-S5) and P-S7 (P2-S2, P2-S6).

New findings: 0 BLOCKER, 9 SHOULD-FIX, 3 NIT.
- Contract: 8, namely S1, S2, S3, S4, S5, S6 (the bar's form), S7 and S8.
- Mechanism: S9 (step 6.1b) and S6's runs (step 6.1b).
- Nits: N1–N3 are wording and number fixes in §7 and §6.
- Fix verification: none of the proposed fixes is verified, except that P2-N1's arithmetic was run.
