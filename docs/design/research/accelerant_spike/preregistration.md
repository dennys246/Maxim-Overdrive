# Accelerant spike: pre-registration (2026-11-20, committed before any spike code runs)

This is T17's required Q1 rerun with a cited accelerant loading, in T18's form: a per-cell pore-loading field that
spreads fire only by heat transfer. It is throwaway, like the physics spike (`../physics_spike/preregistration.md`):
code in `spikes/physics/accelerant/`, extending `spikes/physics/bed/`, never imported by `src/`.

**No constant is tuned to make a criterion pass, no criterion is loosened after the run, and none is reinterpreted
after it.** The authored loading is a scenario value, fixed here from a cited retention, and never moved to rescue a
result.

**The risk, stated first.** The physics spike traced the failure to 6c giving flame heat no path to unburnt fuel
except χ_r·q''_f through P1 (`bed.md` §3). This spike adds **no spread law**, because T18 says a soaked bed spreads
"because its fuel is distributed". The accelerant lowers the ignition threshold from T_p (380 °C) to the liquid's
boiling range (about 230 °C). But heat still reaches unlit fuel only through P1 and the draught gas, so lateral and
downward spread may stay too weak. If they do, this is the T13 failure path again.

## 1. The accelerant

**Primary: kerosene.**
- **It keeps Phase 1's no-motion assumption true.** Its Reid vapour pressure is 0.1 psia (CHRIS), so negligible
  liquid evaporates before `kindle` at tick 70. Gasoline (about 7–15 psia, memory) would need the pre-ignition
  evaporation that T18 defers to Phase 2.
- **It makes question A a real test.** Its flash point, ≥ 38 °C, is above ambient, so the pilot must heat the wetted
  wood. Gasoline's, about −43 °C (memory), would make A trivial.
- **It is plausible in the world:** common lamp and heating fuel.

**How the loading burns: an in-depth liquid, dried like moisture.**
- **Storage.** Each slat part with a depth profile (Ui, Up, and the new Ia) carries a liquid mass per node, m_L,j
  (kg/m² of surface), on the existing 10-node half-slat. Each node's heat capacity gains m_L,j·c_L.
- **Evaporation.** A wet node can't exceed T_b. The energy that would lift it above T_b evaporates liquid at L_v,
  and the vapour reaches the surface at once. This is the thermal drying model used for moisture in pyrolysis
  codes (memory, form only).
- **Ignition.** A wetted unlit area ignites where its reconstructed sub-cell surface (`model.py::_hot_fraction`)
  reaches T_b, with the pilot on it or a flame in the cell or a face neighbour. This is the existing piloted rule,
  with T_b in place of T_p for wet surfaces.
- **Flaming.** A surface flames while its fuel heat-release flux, m''_K·Δh_c,K + m''_w·ΔH_c,w, is at least
  q''_crit = m''_crit·ΔH_c,w. That is the bed's cited extinction flux in energy form (derived; the energy form is
  Lyon & Quintiere 2007, from memory). For kerosene alone it is 1.06 g/m²s. Vapour from a surface that isn't flaming
  is vented unburnt.
- **The new part Ia (ignited and still wet).** Ia keeps its profile and flames on vapour. If its surface node dries
  and reaches T_p, 6c runs on that node: the excess over T_p gasifies wood at L_g, and both fuels count toward
  flaming. When it holds no liquid (≤ 10⁻⁹ kg/m²), it merges into Iw with its slab energy, as Ui → Iw does now.
  **6c on dry Iw is unchanged.**
- **Where the heat goes: the existing terms.** Burning vapour releases Δh_c,K and is booked like wood volatiles:
  - q''_f per m² of flaming surface, with (1 − χ_r) of it directly onto the surface and χ_r into P1;
  - of the rest of the release, χ_r goes to `flame_radiative` and the remainder to `plume_convective`;
  - O₂ use by Huggett;
  - gas leaving a flaming cell at T_p.

  6a, 6b, P1, the draught and char are as in `bed.md`.
- **q''_f is one flame law for wet and dry surfaces,** keeping its range of 15–35 kW/m² (nominal 25). A cross-check
  from kerosene pans, m''·Δh_g (derived), lands inside the range or just below its 15 end, so the range is kept, not
  re-chosen:
  - 35 g/m²s at D = 0.69 m gives 23–26 kW/m²;
  - 20 g/m²s at D = 0.34 m gives 13–15 kW/m².

**Constants.** V = verified on a page read for this pre-registration; S = secondhand or a snippet; M = memory, to
verify before the run (a row still M is reported as M); D = derived.

| Constant | Value (ends run) | Source | Status |
|---|---|---|---|
| Flash point | ≥ 38 °C | USCG CHRIS "Kerosene" (KRS, NOAA, 1999) §4.1 | V |
| T_b | 230 °C (175; 325) | CHRIS §9.3: 200–260 °C; NIOSH Pocket Guide 347–617 °F (snippet) | V / S |
| L_v | 250 kJ/kg | CHRIS §9.12 | V |
| c_L | 2.36 kJ/kgK, mean over 20–230 °C | CHRIS §9.21 (0.469 Btu/lb°F at 70 °F, +0.0005/°F), extrapolated above 210 °F | V / D |
| ρ_L | 800 kg/m³ | CHRIS §9.7 (Babrauskas: 820, S) | V |
| Δh_c,K | 43.1 MJ/kg | CHRIS §9.13 (Babrauskas: 43.2, S) | V |
| Reid vapour pressure; autoignition | 0.1 psia; 229 °C (not modelled) | CHRIS §9.19, §4.7 | V |
| Pan rates (cross-check) | 1 mm: 8.9, 10.4; 20 mm: 20, 35 g/m²s (D 0.34, 0.69 m) | Mealy, Benfer & Gottuk 2011, Fire Saf. Sci. 10:945, Table 3 (PDF read) | V |
| m''∞, kβ (cross-check) | 39 (36–42) g/m²s, 3.5 (2.7–4.3) m⁻¹ | Babrauskas 1983, Fire Technol. 19:251, as quoted by Mealy et al. 2011 | S |
| Δh_g (cross-check) | 670 kJ/kg; c_L·ΔT + L_v = 746 (D) | Babrauskas 1983 table row (snippet) | S |
| q''_crit | 45.9 kW/m² (31.0; 48.7; mass form) | m''_crit 3.7 (2.5; 3.93) g/m²s × 12.4 MJ/kg, `bed.md` §2 | D / M |
| χ_r, every flame | 0.30 (0.27; 0.33; 0.35) | NIST TN 2327 (wood); 0.35 the top of Hamins et al. 1991 (eight fuels, kerosene unconfirmed) | V / S |
| Wood void fraction | 0.61 (cell wall 1,530 kg/m³) | ASTM D2395 ≈ 1.53, FPL ≈ 1.54 (snippets) | S |
| Wood, char, gas | as `bed.md` §2 | `bed.md` | as there |

## 2. The scenario

- **As in the physics spike:**
  - the tile spec's crate (0.6 m, φ = 0.25, σ = 25 m²/m³, 32.4 kg of wood over 5.4 m²);
  - the 2 kW pilot over r = 0.2 m at `kindle`'s point (face x−, y = z = 0.325 m), on the 0.031 m² of outward slat
    faces under the disc;
  - grids of 0.2, 0.1 and 0.05 m, with 0.05 m as the reference;
  - 0.5 s physics steps, a 5,400 s cap, open air at 20 °C, and an adiabatic bottom.
- **Pilot duration.** D = 600 s, graded, as before. A 30 s ("brief") hold is run and reported, not graded.
- **The loading is a cold soak.** Pine posts soaked 24–48 h in a No. 2 fuel-oil solution retained **32–96 kg of
  solution per m³ of wood**, with the sapwood "well penetrated". Source: Wood Handbook FPL-GTR-190 ch. 15, Lebow
  2010, "Cold Soaking and Steeping" (PDF read; V).
  - **Nominal: 64 kg/m³ of wood,** the midpoint. That is 16 kg/m³ of bed and 0.64 kg/m² of surface: **3.46 kg
    (4.3 L) in the crate**, 149 MJ against the wood's 567 MJ (derived).
  - **Ends: 32 and 96** (1.73 and 5.18 kg).
  - **The transfer to kerosene is an analogy (M):** kerosene is thinner than No. 2 fuel oil (memory), so its uptake
    should be no smaller. The retention is applied kilogram for kilogram.
- **Distribution.** Nominal: uniform through the half-slat, as the source's sapwood was well penetrated.
  - **End: saturated from the surface.** The same mass fills nodes from the face inward, each to the void cap (0.61 ×
    1 mm × 800 = 0.49 kg/m² per node).
  - **This end stands for a brief douse,** whose transverse penetration is "usually less than a millimeter"
    (FPL-GTR-190 ch. 15, "Brief Dipping", V).
- **T18's porosity cap, read now.** It is read as the wood's internal void fraction × ρ_L = 488 kg/m³ of wood (122
  kg/m³ of bed). The nominal loading is 13% of it.
  - Liquid in the bed's air voids (1 − φ) is free liquid that drains: pooling, which is Phase 2.
  - Step 6's field definition should state this reading. **Flagged for the owner.**
- **Authored at t = 0,** uniform, at 20 °C, never moving.

**Closed-form expectation (derived; not a criterion):** a wetted face reaches T_b under the pilot in about 40 s
(π/4·kρc_eff·ΔT²/q''_net²; bare wood took 415 s). Its surface liquid then lasts seconds, so vapour must come from depth.

## 3. Questions and pass criteria

**Definitions** (areas are slat surface, out of 5.4 m²):
- **λ(t):** the fraction that has ever flamed, on either fuel.
- **λ_w(t):** the fraction whose surface has reached T_p while flaming (wood pyrolysing under 6c).
- **t_L95:** the first time the liquid inventory falls to 5% of its initial mass, by burning or venting.
- **Flame-out:** the start of the final interval with zero flaming area.

| # | Criterion | Pass when |
|---|---|---|
| A | The accelerant ignites under the pilot | Kerosene-fed flaming covers ≥ 90% of the area under the disc before the pilot ends. `t_A` is reported against the tile spec's assumed 60 s, not graded |
| B1 | The accelerant fire spreads through the crate | max λ ≥ 0.90 |
| B2 | The wood becomes fully involved | λ_w(t_L95) ≥ 0.90. The 10% allowance covers the outward envelope share (φ × 1.8 m² = 0.45 m², 8%), which loses heat to the room. `t_B` (first λ_w ≥ 0.90) is reported |
| C | The wood fire sustains after the accelerant (1a as pre-registered) | Flame-out comes after both t_L95 and the pilot's end, and virgin wood at flame-out is ≤ 5% of 32.4 kg |
| D1 | The class is grid-independent | The class of A, B1, B2 and C is the same at all three grids (the resolution rule) |
| D2 | Values converge | t_A, t_B, t_L95 and flame-out pass the physics spike's 2a rule at tol = 15%; max λ and λ_w(t_L95) at 0.1 m are within 0.05 (absolute) of the reference. A time missing on any grid is a miss |
| D3 | Observed order | p > 0.5 for each D2 time, with Richardson's e₀.₁ reported. Expected hard: the earlier 2b missed everywhere on 0.5 s quantisation |
| E1 | The ledger closes | At every physics step, \|in − Δstored − out\| ≤ 1% of cumulative release. The new lines are `combustion_accelerant`, `vapour_unburnt` (the vented vapour's latent and sensible heat; its chemical energy is never booked as release) and the liquid's sensible heat in Δcells |
| E2 | The new lines matter | Deleting each new line turns E1 red in at least one run |
| E3 | The liquid mass closes | initial = burnt + vented + remaining, to 10⁻⁹ relative, at every step |
| E4 | Closed forms | (i) One wet node, adiabatic behind, under a constant flux q'': its T_b plateau lasts m_L·L_v/q'' to within one substep. (ii) With zero loading, the model reproduces `bed.md`'s S and F nominal 0.1 m rows to their printed precision |
| E5 | Deterministic and splitting-robust | A rerun is bit-identical, and at 10× the substeps (0.1 m) the classes of A–C are unchanged |
| F | The class holds at the range ends | At 0.1 m, each end in turn gives the same classes of A, B1, B2 and C as nominal. The ends: loading 32 and 96; surface-saturated distribution; T_b 175 and 325; q''_crit 31.0, 48.7 and the mass form; χ_r 0.27, 0.33 and 0.35; q''_f 15 and 35; all feedback into P1. **Expected miss:** `bed.md`'s scenario F already missed 1a at q''_f = 15 and with all-P1 feedback. A miss there is reported, not explained away |

**Also reported:** the energy split between kerosene and wood, the fraction of kerosene vented unburnt, the peak
heat release, `t_crack`, and λ(t) and λ_w(t) at each grid. O₂ is never limiting in this model, so O₂ demand is
compared with the draught's supply; a demand above it for more than 10% of the time before t_L95 labels B
"O₂-unverified".

**Back on the T13 failure path:** any miss of A, B1, B2 or C at nominal on the 0.05 m reference, or a D1 class
difference.

## 4. Failure paths

Results go in `results.md` here, one row per criterion with its numbers.

- **A misses.** That contradicts ordinary experience, so the model is suspected first (the single T_b, or q''_crit
  on vapour from depth). A structural fix is disclosed as a deviation; no constant moves. If A still misses, the owner
  decides the igniter.
- **B1 misses.** The accelerant burns near the pilot only, so T18's distributed-fuel claim fails under 6c's heat
  paths. **T13:** the owner decides, before step 6, between a cited spread law (option 1 in `physics_spike.md`) and
  changing the exit (option 3). Loading beyond the cited retention is not offered.
- **B1 passes, B2 misses.** The kerosene burns off before the wood reaches T_p. **T13.** The options are more
  loading (only with a new retention citation), a spread or preheat law, or option 3.
- **C misses.** This is `bed.md`'s 1a miss on a new premise. **T13:** step 6 can't be designed on 6c as written.
- **D1 or D2 misses while A–C pass at the reference.** The resolution rule is broken. Step 6 needs `bed.md` §7.4's
  sub-cell envelope model before any exit run counts, and the owner is told.
- **D3 alone:** recorded for step 4's harness. **E:** a bug, fixed and all runs redone, disclosed; an owner item only
  if a class changes.
- **F misses.** The outcome sits inside the cited ranges, so it is a band, not a margin. Step 6's band gate (tile
  §6.3 item 7) must carry it. If a loading end flips the outcome, the soaked crate depends on a scenario choice,
  which is the owner's to make.

## 5. Out of scope, and the gaps carried

- **Glow and burnout (1b, 1c).** The char-oxidation model decides them, not the lighting (`bed.md` §3). That model
  is step 6's first research task under T17. Char outputs are recorded here but neither graded nor interpreted.
- **Liquid motion** (wicking, drainage, pooling, pre-ignition evaporation, the `soak` modulator). This is Phase 2
  under T18. A poured crate, the player's real action, needs a douse retention this spike lacks; the
  surface-saturated end only brackets it.
- **A spread law or a flame-gas temperature.** Not added: testing T18 without them is the point.
- **Gasoline, the body (Q5) and the SEM bridge's labels.**

**Gaps that bias the verdict:**

| Gap | Biases B and C toward |
|---|---|
| A single T_b with no evaporation below it, though the flash point is 38 °C | a miss |
| Autoignition at 229 °C not modelled | a miss |
| Gas leaving a flaming cell at T_p, not at flame temperature | a miss |
| Ia's 6c node conducts inward, where Iw's lumped skin doesn't | a miss |
| Δh_c,K taken as complete, not effective | a pass |
| O₂ never limiting | a pass |
| No resistance to vapour transport | a pass early, a miss later |
| The liquid's effect on wood conductivity ignored | unknown |

`results.md` names the gaps each verdict leans on: a pass survives the miss-biased gaps, not the pass-biased ones.
