# Hot-surface spike: pre-registration (2026-11-20, committed before any spike code runs)

This spike tests one hypothesis: that the physics spike (`../physics_spike/bed.md`) and the accelerant spike
(`../accelerant_spike/results.md`) failed to spread because of one simplification, not a missing mechanism. In
both, a burning surface is pinned at T_p (380 °C), and gas leaving a flaming cell is capped at T_p.

**The hypothesis is the coordinator's inference from those two results, not a finding.** It was formed after both
misses and after reading their diagnostics, so it carries a forking-paths risk. The guard is the usual one:

- every constant, range end, criterion and the meaning of each outcome is fixed here before code;
- **no constant is tuned, no criterion is loosened after the run, and none is reinterpreted after it.**

A negative result is as useful as a positive one.

The spike is throwaway, like its two parents. Its code goes in `spikes/physics/hot/`, subclassing
`spikes/physics/bed/model.py::Bed` and `spikes/physics/accelerant/wetbed.py::WetBed`, and is never imported by
`src/`. The bed's and the accelerant's code and committed results are not edited.

**Tags**, as in the accelerant pre-registration:
- **V:** verified on a page read for this pre-registration;
- **S:** secondhand (a snippet, an abstract, or quoted by another source);
- **M:** memory, to verify before the run (a row still M is reported as M);
- **D:** derived here (scratch, not committed).

## 0. The risk, stated first

Two hand calculations (D, scratch `calc.py`) point in opposite directions. Both are predictions, not criteria.

1. **De-pinning should strengthen the heat path to unlit fuel.**
   - A burning surface at 550–690 °C emits 2.5–4.7× what it does at 380 °C into the in-bed radiation field P1:
     εσT⁴ = 9.3 kW/m² at 380 °C against 30 kW/m² at 600 °C.
   - Draught gas leaving a flame at about 870 °C instead of 380 °C carries about 2.3× the sensible heat per kilogram
     into the cell above.
   - The accelerant spike's hottest unlit skin beside a flame reached only 108, 164 and 230 °C (0.2, 0.1 and
     0.05 m). The spike needed 230 °C for wet wood and needs 380 °C for dry wood.
2. **De-pinning may also put flames out.** With the cited char-layer balance (§1.1), take an interior burning face
   under (1 − χ_r)·q''_f = 17.5 kW/m², with its neighbours at 380 °C:
   - its pyrolysis flux falls below m''_crit = 3.7 g/m²s once its char is about 4 mm thick;
   - with neighbours at 600 °C, it falls below at about 6 mm.

   A half-slat's full char is 10 mm, so **the fully-lit scenario F, which passed 1a in `bed.md`, may now miss
   it.** The cause would be the char layer insulating the pyrolysis front. That is real physics: charring timber
   self-extinguishes without enough external heat. But the model doesn't have all of a crib's mutual heating, so a
   miss there would partly be the model's.

| Interior face, nominal k_c, ρ_c (D) | Char 1 mm | 2.5 mm | 5 mm | 10 mm |
|---|---|---|---|---|
| Neighbours at 380 °C: T_c, m'' | 438 °C, 7.7 g/m²s | 504 °C, 4.5 | 537 °C, 2.6 | 557 °C, 1.4 |
| Neighbours at 600 °C: T_c, m'' | 544 °C, 13.6 | 630 °C, 7.3 | 667 °C, 4.1 | 687 °C, 2.2 |
| Today's pin (any thickness) | 380 °C, 9.7 | 9.7 | 9.7 | 9.7 |

The criteria grade spread and sustain separately (§3), so the outcome can't be reported as just "better" or "worse".

## 1. The model change

The change has three parts: a char-layer surface balance on burning wood, a flame-gas temperature in the draught,
and one structural variant run beside them. Everything else stays as it is.

### 1.1 The char-layer surface balance (replaces 6c's pin on Iw)

This applies to Iw, the ignited-wood part of each cell (`bed/model.py::_step_iw`). Its 1 mm skin node,
`Ts_iw`, becomes the **char-surface temperature T_c**. It is no longer pinned at T_p. It is a sub-cell surface
quantity, per m² of fuel surface, as `char_oxidation.md` §5.1 item 1 recommends.

**The surface balance** (explicit, per substep, the skin's existing capacity C_s):

  C_s·dT_c/dt = q''_direct + εG/4 − εσT_c⁴ − q''_gas − f_env·h_env·(T_c − T₀) + q''_ox − q''_k

Every term except q''_k is today's, computed exactly as `_step_iw` computes it now:
- **q''_direct:** (1 − χ_r)·q''_f on flaming area, plus the pilot's share on lit faces under the disc;
- **εG/4:** absorbed P1 radiation;
- **q''_gas:** draught exchange, in non-flaming cells only (§1.3 changes that only in H2);
- **f_env·h_env:** convection from the envelope share;
- **q''_ox:** char oxidation, in non-flaming cells only, by the bed's existing law.

**The new term, conduction through the char to the pyrolysis front:**
- q''_k = k_c·(T_c − T_f)/δ_c when T_c > T_f, and 0 otherwise. The front stalls while the surface is cooler than
  it.
- δ_c = max(m_c/ρ_c, δ_s). Here m_c is the Iw char areal mass that already exists (`c_iw`), and δ_s = 1 mm is the
  tile spec's 6b skin, a numerical floor that stops the conductance diverging at ignition.
- k_c and ρ_c enter only as the product k_c·ρ_c/m_c, so one end of the group covers both (§1.4).

**Pyrolysis.** While wood remains (`w_iw > 0`), m''_v = q''_k/L_g. This replaces m''_v = excess over T_p / L_g:
- the volatile flux, char yield χ, flaming test (m''_v ≥ m''_crit) and release (m''_v·ΔH_c,eff) are today's;
- the energy q''_k leaves with the volatiles and is booked to `removed_with_mass`, as 6c's excess is now.

**What stays as in 6c, deliberately:**
- **No conduction into the virgin wood behind the front.** Iw keeps its lumped slab energy `e_iw`. All the flux
  reaching the front gasifies, as all of 6c's net flux does. (Gap, §5.)
- **Ignition is untouched.** Area joins Iw at T_p (380 °C) with its slab energy, by the existing reconstructed
  piloted rule (`_transfers`, `_merge_iw`). It mixes into the cell's T_c and m_c by area, as today.
- **Hand-over to char is untouched.** Iw → Ic when the wood is gone, at T_c (`_iw_to_ic` already hands over
  `Ts_iw`). That is the hand-over temperature `char_oxidation.md` says decides glow (§3, reported only).
- **Accelerant (K).** Ia, the ignited part still wet, is unchanged:
  - its wet nodes are capped at T_b, which is the liquid's physics, not the pin;
  - its dry surface node keeps 6c at T_p (at most 0.07 m² ever held Ia in the accelerant spike);
  - Ia → Iw keeps the accelerant code's rule (dry, and the surface node at T_p). After that, the char layer runs.

**Constants (new):**

| Constant | Value (ends run) | Source | Status |
|---|---|---|---|
| T_f, pyrolysis-front temperature | 300 °C (288; 380) | "The temperature at the base of the char layer is generally taken to be 300 °C or 550 °F (288 °C)": White & Dietenberger 2010, Wood Handbook FPL-GTR-190 ch. 18 (via `char_oxidation.md` §2.2). EC5's char line is the 300 °C isotherm (Cachim & Franssen 2009, Fire Mater. 33:129, §2). 380 °C = T_p is a modelling end that recovers today's front | V / V / end |
| k_c, char conductivity | 0.10 W/mK (0.07; EC5 apparent k(T)) | 0.10: Correa et al. 2023 Table 1 (via `char_oxidation.md`). EN 1995-1-2 Annex B, as tabulated by Cachim & Franssen 2009 Table II (PDF read): 0.070 at 350 °C, 0.077 at 400, 0.090 at 500, 0.176 at 600, 0.350 at 800, 1.500 at 1,200 °C. These are "apparent values … to take into account increased heat transfer due to shrinkage cracks above about 500 °C". The EC5 end interpolates linearly at the layer mean ½(T_c + T_f) | V (via) / V |
| ρ_c, char density | 150 kg/m³ (200) | χ·ρ_wood with no shrinkage (D, `char_oxidation.md` §5.1). End: EC5 density ratio 0.33 at 500 °C × 600 = 198 (D from the V table) | D |
| ε, char emissivity | 0.9 (0.85; 0.95) | as `bed.md` §2 | V / M range |
| C_s | 1,020 J/m²K (the existing skin: 600 × 1,700 × 1 mm) | Kept so nothing else changes. A 1 mm char skin would hold about 190 (150 × 1,260 × 1 mm, D). This affects transients only, not the steady T_c (§3, E3) | existing |

### 1.2 The flame-gas temperature (replaces the T_p cap in the draught)

**Today.** In a flaming cell, `_draught` heats the column's gas toward T_p:
- with what the cell's plume can give, q_fl = min(ṁc_p·(T_p − t_in), (1 − χ_r)(Q − fb));
- the rest of (1 − χ_r)(Q − fb) leaves as `plume_convective`;
- the cell's surfaces don't exchange with the gas;
- the buoyancy temperature is set to T_p.

**The change.** T_p in that cap becomes **T_fl, a cited time-mean flame temperature.** The gas leaving a flaming
cell is then:

  t_out = min(T_fl, t_in + (1 − χ_r)(Q − fb)/(ṁc_p))  (t_in ≥ T_fl passes unchanged)

**How it is tied to the cell's heat release.** The tie is the energy balance, not a dial. A weakly burning cell
can't heat its draught to T_fl, because its plume can't supply ṁc_p·ΔT. T_fl is only the ceiling: on a time
average, gas inside a flame is no hotter than the flame. This matches McCaffrey's central finding: "For the flame
region alone both V and ΔT are independent of fire size, Q. Fire size enters only in determining how high or long
this continuous flame region will be" (NBSIR 79-1910, p. 7, V).

**A height-resolved end (Mz)** uses McCaffrey's full three-region correlation as the cap, so the cap itself
depends on heat release and height:
- **The correlation:** 2gΔT/T₀ = (κ/C)²·(z/Q^(2/5))^(2η−1), C = 0.9.
  - Flame region: κ = 6.8, η = ½, for z/Q^(2/5) < 0.08 m/kW^(2/5).
  - Intermittent: κ = 1.9, η = 0, for 0.08–0.20.
  - Plume: κ = 1.1, η = −⅓, above 0.20.
- **Per column, at each flaming cell:**
  - Q is the summed lagged release (kW) of the flaming cells at or below it, from the lowest flaming cell in the
    column;
  - z is the height from that cell's bottom face to the top of this cell.
- Non-flaming cells are unchanged.

**The buoyancy temperature of a flaming cell** becomes ½(t_in + t_out), with t_out energy-limited, the same rule
non-flaming cells use. Today's code uses the cap whatever the energy. That overstated buoyancy little at 380 °C,
but at 873 °C it would drive the draught with heat the cell doesn't have. This is part of the change, disclosed,
and it is off in the zero-change mode (E4).

**Unchanged in the draught:**
- O₂ by Huggett, never limiting flaming;
- Ergun resistance;
- exchange in non-flaming cells (the hotter gas now heats the unlit fuel above);
- the CO path and the column march.

The same edit applies to `wetbed.py`'s `_draught` override (K).

**How both changes reach P1.** No P1 code changes:
- `_emission()` already weights each part's εσT⁴ by area, so a hotter T_c is emitted into P1 by itself;
- the χ_r·q''_f source and the export of χ_r(Q − fb) as `flame_radiative` are unchanged;
- gas radiation is not added to P1 (gap, §5).

**Constants (new):**

| Constant | Value (ends run) | Source | Status |
|---|---|---|---|
| T_fl | **873 °C** (520; 1,027) | McCaffrey 1979, NBSIR 79-1910, pp. 7–8 (scanned PDF read): the flame region at κ = 6.8, η = ½, C = 0.9 gives ΔT = T₀(κ/C)²/2g = 853 K at T₀ = 293 K (D). Babrauskas, "Temperatures in flames and fires" (doctorfire.com, page read): McCaffrey's continuous-flame temperatures "are constant and are slightly below 900 °C"; Cox & Chitty 900 °C; Ingason's rack-storage solid flame 870 °C; "for small flames (less than about 1 m base diameter), continuous flame region temperatures of around 900 °C should be expected" | V / D |
| T_fl, low end | 520 °C | Heskestad (1997, *Flame heights of fuel arrays with combustion in depth*, Fire Safety Science 5:427) takes a 500 °C rise as the flame tip, so about 520 °C (via Babrauskas, page read). The same page puts visible tips at 320–400 °C; those sit at or below T_p, which is today's model, so they aren't run separately | S |
| T_fl, high end | 1,027 °C | McCaffrey p. 5: his thermocouple error is "about 20% at T_gas = 1300 K … The thermocouple will be reading about 1000 K". So the true flame-region gas is about 1,300 K (D) | V / D |
| McCaffrey's three regions (Mz end) | above | NBSIR 79-1910 p. 8 (V). Five fire sizes; 14.4, 22 and 45 kW are V (pp. 8 and iv); fuel and burner size M | V |
| Crib interior gas (cross-check only) | about 650 °C at the crib top to a 900 °C peak | Mukunda et al. 2022, Combust. Theory Model., free-burning cribs (S, search snippet) | S |

**Two cautions about T_fl.** McCaffrey's flames are open pool flames over a 0.30 m burner (M), not flames inside
a porous bed with Ergun-limited flow. Applying them inside the bed is an analogy. The ends and Mz bracket it, but
they don't remove it (gap, §5).

### 1.3 The structural variant H2: flame gas touches the flaming cell's own unlit fuel

**H1** is §1.1 plus §1.2: exactly the coordinator's hypothesis. In H1, as today, a flaming cell's gas never
exchanges with that cell's unlit surfaces. That exclusion is part of what the hypothesis keeps. Its effect depends
on grid size: a 0.2 m flaming cell holds about 0.2 m² of unlit fuel the flame gas never touches.

**H2 is H1 plus that contact:**
- In a flaming cell, after the flame heats the gas (§1.2), the gas exchanges with the cell's Ui, unlit Up, Ic and
  unlit wet parts.
- It uses the existing exponential NTU law and `_h_slat`, as in a non-flaming cell, on those parts' area only.
- Flaming Iw and Ia are excluded, because their flame heat is already q''_f.
- It is booked to the same lines as the non-flaming exchange.

H2 is graded on the same criteria, as a separate arm. H1 alone decides the hypothesis. H2 tells step 6 what else
it would need if H1 misses (§4).

### 1.4 What stays exactly as in `bed/` and `accelerant/`

Every other line of physics:
- **The parts and ignition:** the four parts (Ui, Up, Iw, Ic) and Ia; their slab profiles; the ignition rule and
  thresholds (T_p, T_b), with the reconstructed sub-cell skin field and the piloted face-neighbour condition.
- **The flame:** q''_f and its split ((1 − χ_r) direct, χ_r into P1); ΔH_c,eff, L_g, χ, m''_crit, χ_r.
- **Radiation and the draught:** P1 and Marshak; Ergun, Churchill–Bernstein and Churchill–Chu; Huggett.
- **Char:** kinetics, Arthur's products, the CO path.
- **The rest:** the pilot (2 kW over r = 0.2 m), the envelope 6a, the adiabatic floor, the kerosene model, the
  ledger lines, the 0.5 s physics step and the substep bound. The bound gains the conduction term k_c/δ_c in the
  skin's stability limit, which only adds substeps.

**Constants and ranges** are `bed.md` §2's and the accelerant pre-registration §1's, unchanged. The code gets
three switches:
- `surface_mode`: `pinned` or `char`;
- `gas_cap`: `tp`, `flame` or `mccaffrey_z`;
- `incell_contact`: off or on.

With `pinned`, `tp` and off, the code paths are today's (E4).

## 2. Scenarios

**As in the parents:**
- the tile spec's crate: 0.6 m, φ = 0.25, σ = 25 m²/m³, 32.4 kg over 5.4 m²;
- grids of 0.2, 0.1 and 0.05 m, with 0.05 m the reference;
- 0.5 s physics steps, open air at 20 °C, an adiabatic floor.

**The cap.** Every new run has a 5,400 s cap, with `sim.py`'s existing stops: quiet, or fuel under 5%. The bed's S
and B runs stopped at 1,800 s only because nothing was burning. A spreading fire must be allowed to finish.
Zero-change runs (E4) keep their original settings.

| Scenario | Set-up | Graded |
|---|---|---|
| **S, bare** | The physics spike's S: 2 kW pilot for 600 s at `kindle`'s point, nominal constants | yes |
| **K, soaked** | The accelerant spike's nominal: kerosene 64 kg/m³ of wood, uniform, the same pilot for 600 s | yes |
| **F, fully lit** | The bed's F: all fuel flaming at t = 0 | 1a only (that the change doesn't break sustain) |
| **B, base-lit** | The bed's B: the bottom 0.1 m flaming at t = 0 | reported, not graded |

B is the classic crib test of upward, gas-driven spread: real cribs lit at the base burn through. It shows the gas
path alone more clearly than S.

**Arms:**
- **H1 (graded):** S, K and F at all three grids.
- **H2 (graded as a second arm):** S, K and F at all three grids.
- **Attribution (reported):** H1 with only the surface change, and H1 with only the gas change. S and K at all three
  grids.
- **B:** H1 and H2 at all three grids.

## 3. Criteria (thresholds fixed now)

**Definitions** reuse the accelerant spike's, so results compare directly. Areas are slat surface, out of 5.4 m².
- **λ(t):** the fraction that has ever flamed, on either fuel. **λ_max** is its final value.
- **λ_w(t):** the fraction whose wood has pyrolysed while flaming. In this model that means Iw flaming area, or Ia
  whose surface node runs 6c, as in `wetbed.py::wood_involved`.
- **Spread class:** none if λ_max < 0.10; partial if 0.10 ≤ λ_max < 0.90; spread if λ_max ≥ 0.90.
- **t_L95 (K):** the liquid inventory first at or below 5% of its initial mass.
- **Flame-out:** the start of the final interval with zero flaming area.
- **t_ignite:** flaming area first ≥ 0.1 m².
- **t_B:** λ_w first ≥ 0.90.

| # | Criterion | Pass when |
|---|---|---|
| **B1** | **Spread** (S, K) | λ_max ≥ 0.90 |
| **B2** | **Wood fully involved** | S: max λ_w ≥ 0.90. K: λ_w(t_L95) ≥ 0.90, as pre-registered for the accelerant (a missing t_L95 is a miss). The 10% allowance covers the outward envelope share (8%) |
| **C** | **Sustain** after the pilot and the kerosene (1a) (S, K) | Flame-out comes after the pilot's end (and, in K, after t_L95), and virgin wood at flame-out is ≤ 5% of 32.4 kg |
| **C_F** | **The change keeps F's 1a** | In F, virgin wood at flame-out ≤ 5%, as `bed.md` F passed (0.6% left). Flame-out is reported against the bed's 449 / 575 / 770 s |
| **D1** | **Grid class agreement** (resolution rule) | The classes of B1, B2, C and C_F are the same at 0.2, 0.1 and 0.05 m, and so is the three-way spread class |
| **D2** | **Convergence** | t_ignite, t_B, flame-out and (K) t_L95 pass the physics spike's 2a rule at tol = 15%: \|e₀.₁\| ≤ tol, and (\|e₀.₂\| ≥ \|e₀.₁\| or \|e₀.₁\| ≤ tol/4). λ_max and the final λ_w at 0.1 m are within 0.05 (absolute) of 0.05 m. A time missing on any grid is a miss |
| **D3** | **Observed order** | p > 0.5 for each D2 time, with Richardson's e₀.₁ reported. Expected to miss, as both parents did (0.5 s quantisation, unresolved radiative layer) |
| **E1** | **Ledger closure** | At every physics step, \|in − Δstored − out\| ≤ 1% of cumulative release, with the parents' lines. No line is added: the change moves energy between existing lines (`removed_with_mass`, `open_air_draught`, `plume_convective`, Δskins) |
| **E2** | **The changed lines matter** | Deleting each of `removed_with_mass`, `open_air_draught`, `plume_convective` and Δskins turns E1 red in at least one H1 run. A line under 1% of release that can't trip it is reported as a partial miss, as before |
| **E3** | **Closed forms of the new terms** | Four checks, below |
| **E4** | **Zero-change reproduction** | Two checks, below |
| **E5** | **Deterministic and splitting-robust** | A rerun of S and K H1 at 0.1 m is bit-identical. At 10× substeps (0.1 m), the classes of B1, B2 and C are unchanged |
| **G** | **Range ends** | At 0.1 m, each end in turn gives H1 the same classes of B1, B2 and C (S, K) and C_F (F) as nominal, and the same three-way spread class |

**E3, the closed forms of the new terms:**
1. **The steady surface balance.** One Iw element at fixed m_c (no char growth), fixed G, no draught and constant
   q''_direct, run to steady state at m_c = 0.05, 0.375, 0.75 and 1.5 kg/m². Its T_c must match the bisection root
   of the §1.1 balance to 0.5 K, and m''_v must match k_c(T_c − T_f)/(δ_c·L_g) to 0.1%. Checked against the §0
   table's rows to its printed precision.
2. **The front stalls.** At T_c ≤ T_f, m''_v = 0 exactly.
3. **The gas cap.** One flaming cell with prescribed Q, fb, ṁ and t_in must give t_out = min(T_fl,
   t_in + (1 − χ_r)(Q − fb)/(ṁc_p)) to 10⁻¹² relative, with both branches exercised.
4. **Mz.** For a column with prescribed releases, the cap must equal McCaffrey's ΔT at the cells' z/Q^(2/5), in
   each of the three regions.

**E4, zero-change reproduction:**
1. **With the new terms disabled** (`pinned`, `tp`, contact off), the hot-spike code must reproduce these committed
   digests bit for bit:
   - the bed: `S_nom_02` 462917f4…, `S_nom_01` 74465ca0…, `F_nom_02` 75f97068…, `F_nom_01` bcfc8eab… and
     `B_nom_01` 2baffcf1…;
   - the accelerant: `N_02` 93ac5d79… and `N_01` b382b46e….
2. **Pre-ignition identity.** With the new terms **on**, the state digest at each step before the first flaming
   area appears equals the parent's (the bed for S, the accelerant for K).

   The change acts only on Iw and on flaming cells, so a difference before ignition is a bug. In S this pins the
   disc's ignition at 415.5 s. In K it pins it at 47.5 s, though A's 90% coverage may move after first flame and is
   reported.

**The range ends for G**, at 0.1 m, in S, K and F (36 runs):
- k_c: 0.07, and EC5's apparent k(T);
- ρ_c: 200;
- T_f: 288 and 380;
- T_fl: 520 and 1,027, and Mz;
- ε: 0.85 and 0.95;
- q''_f: 15 and 35. This is the one existing end that flipped F in `bed.md`, and the flame flux on a hot surface is
  the term this change leans on.

**Reported, not graded:**
- **The probe.** The accelerant spike's hottest-unlit-skin-beside-a-flame (`probe.py`) at 180, 360, 480 and 600 s,
  against its 108 / 164 / 230 °C.
- **Spread.** The spread front's mean speed (m/s, from λ(t) and the area-equivalent radius), λ(t) and λ_w(t).
- **Release and energy.** Peak release and its time; the energy split (kerosene, wood, char).
- **The new temperatures.** The distribution of T_c on flaming Iw (interior, and the outward envelope share),
  against `char_oxidation.md`'s predicted 700–900 / 550–650 °C. The gas temperature leaving flaming cells, against
  the crib cross-check of 650–900 °C.
- **Attribution and B.** The attribution arms, and B.
- **Glow, as a side effect.** t_glow by the bed's sight-line `envelope_layer` (≥ 0.08 m² at ≥ 625 °C for 60 s),
  the ember peak and mean, and T_c at hand-over. Glow's own model is the char research's, not this spike's: a glow
  here is evidence about the hand-over temperature only.
- **O₂.** O₂ is never limiting in this model. **Any B1 pass is labelled "O₂-unverified"** if flaming O₂ demand
  exceeds the draught's supply for more than 10% of the flaming time before flame-out. The accelerant
  pre-registration had the same rule, and it matters more here, because a fully involved crate demands about
  0.18 kg/s of air at 540 kW (D, Huggett).

**Back on the T13 path** (the owner decides before step 6) if any of these happens on the 0.05 m reference:
- any H1 miss of B1, B2 or C in S or K;
- any D1 class difference;
- a C_F miss.

## 4. What each outcome means (stated before results exist)

The owner's T13 choice is between option 1 (a cited spread law, then rerun) and option 3 (change the exit). T17's
standing decision is option 2: the accelerant lights the crate. The verdict is read from **H1 nominal at the 0.05 m
reference, with D1**. The ends (G), H2 and the gaps (§5) qualify it.

| Outcome | What it means | What it rules out | What step 6 would build |
|---|---|---|---|
| **1. S and K spread, sustain, D1 holds, C_F passes** | The pin was the cause. Fire spreads by heat transfer once burning surfaces and flame gas carry their cited temperatures. **The "spread law" of option 1 is this de-pinning**, with no separate spread rule. That is T18's principle (spread only from heat transfer), now with a mechanism | That a dedicated spread-rate correlation is required | One change does two jobs: the char-layer surface (it is also 6d's hand-over temperature for glow) and T_fl in the draught. Keep P1, the piloted reconstructed ignition, the flux ignition with a band and the sub-cell envelope (physics-spike lessons). Step 6 must still validate it against crib data (time to peak, peak release, as NIST TN 2102 Test 13 in `char_oxidation.md` §2.1), because this spike grades class, not rate. **T17 returns to the owner:** if bare S spreads under the 2 kW torch, the accelerant is gameplay, not a necessity |
| **2. K spreads, S doesn't** (S lights its disc but stays under 0.90) | De-pinning is the spread mechanism; the torch alone is too weak to start it | — | As in 1, with T17's accelerant kept as the lighting route. The exit runs K |
| **3. Spread or sustain only on finer grids** (D1 fails) | The mechanism is enough but unresolved: spread depends on resolving the flame-to-neighbour distance (as the accelerant spike's 0.05 m creep did). The resolution rule is broken | That a per-cell version can ship | De-pinning plus a sub-cell flame-gas and radiation model sized in metres. **T13 stays open:** the owner is told the cost |
| **4. Partial spread** (0.10 ≤ λ_max < 0.90 on the reference) | De-pinning is part of the answer, not all of it | That the pin is the *only* cause | Look at H2. If H2 spreads, flame contact inside the flaming cell is the missing piece (outcome 6). If not, outcome 5 applies |
| **5. No spread** (λ_max < 0.10, as before) | **The hypothesis is false.** With cited char-surface and flame-gas temperatures, the existing paths (P1 and the draught) still can't carry a flame's heat to unburnt fuel fast enough | That the failure was one simplification. Option 1 is then the larger job: flames as volumes that reach neighbouring fuel (impingement, flame height across cells), or a cited crib spread correlation. That is new research, and option 3 becomes the realistic Phase 1 path | Nothing from H1 alone; the char layer is still needed for glow |
| **6. H1 misses, H2 spreads** | The missing mechanism is the flame gas touching unburnt fuel *in its own cell*, which H1 excluded. It is real (flames wrap slats) | That radiation and the inter-cell draught suffice | Flame contact is inherently sub-cell, so step 6 needs a flame-volume model sized in metres. Otherwise the outcome depends on cell size (a 0.2 m flaming cell holds far more unlit fuel). Expect D1 trouble in H2 too, and grade it |
| **7. Spread, but C or C_F misses** (surfaces self-extinguish as the char thickens, the §0 risk) | De-pinning trades sustain for spread. Without enough mutual heating, the char layer insulates the front below m''_crit | That de-pinning is a drop-in change to 6c | Research the flame's heat feedback onto charring surfaces in cribs (q''_f on hot char; the radiation of gas and soot inside the bed) and char k(T). Not tuned: the EC5 end is the one cited lever, and it is run |
| **8. A range end flips a class** | The outcome sits inside the cited ranges: a band, not a margin | — | Step 6's band gate (tile §6.3 item 7) carries it. The owner decides the risk. If T_fl's low end flips it, the flame-temperature analogy (§1.2) becomes the question to research |

**Whichever outcome:**
- **E failures are bugs.** They are fixed and all runs redone, disclosed, and an owner item only if a class
  changes.
- **D3** is recorded for step 4's harness.
- **Glow.** If glow appears in F or S, it is evidence for `char_oxidation.md`'s hand-over claim (§2.2). It is not a
  1b pass, which needs the char model.

**A pass leans on the gaps that bias toward a pass** (§5). `results.md` must say which ones it leans on; a pass
survives only the miss-biased ones.

## 5. Out of scope, and the gaps that bias the verdict

**Out of scope:**
- **Glow and burnout as criteria** (1b, 1c). They belong to the char-oxidation model (`char_oxidation.md`). Here
  they are reported only.
- **A dedicated spread law, a flame-volume or flame-height model, or impingement across cells.** Leaving them out
  is the test.
- **Evaporation below T_b, autoignition, liquid motion** (K). As in the accelerant spike.
- **The body (Q5), the SEM bridge, gasoline.**
- **Validating the spread *rate* or peak release against crib data.** That is step 6's; the values are reported
  here.

**Gaps that bias the verdict:**

| Gap | Biases spread (B) and sustain (C) toward |
|---|---|
| O₂ never limits flaming (label on any B1 pass, §3) | a pass |
| q''_f stays 25 kW/m² on a hot char surface (its convective part should fall as T_c rises) | a pass for T_c and spread; neutral for sustain |
| All the flux reaching the front gasifies; none conducts into virgin wood behind it (6c's lumping, kept) | a pass for sustain |
| T_fl from open pool flames applied inside a porous bed (McCaffrey's burner, not a crib) | unknown; bracketed by 520 / 1,027 and Mz |
| H1: flame gas never touches its own cell's unlit fuel (H2 lifts this) | a miss (H1) |
| No gas or soot radiation in P1 beyond χ_r·q''_f; χ_r(Q − fb) is exported, not returned to the bed | a miss |
| The char layer's heat capacity is ignored beyond the 1 mm skin node (C_s is wood's, not char's) | transients only: slower surface heating, toward a miss early |
| Iw is one lumped surface per cell: new ignitions average into T_c and m_c by area | unknown (a fresh ignition cools an old hot surface; an old char thickness throttles a new one) |
| Constant k_c at nominal; no cracking or radiative conductivity (the EC5 end carries them) | mixed: a higher k lowers T_c (less emission, a miss for spread) and raises m'' (a pass for sustain) |
| Ia's surface stays at T_b (wet) or pinned at T_p (dry) (K) | a miss (K) |
| Single T_b, no evaporation below it, no autoignition (K, inherited) | a miss (K) |
| Δh_c taken as complete, not effective (K, inherited) | a pass |
| No bed collapse; slat area held until burnt | unknown |
| Piloted ignition needs a flame in the cell or a face neighbour; no spontaneous ignition of hot unlit wood | a miss (small: autoignition of wood is well above T_p) |

## 6. What happens with the results

- **`results.md`** in this directory: one row per criterion, with its numbers, and the §4 outcome it lands in. It
  names the gaps that verdict leans on.
- **Deviations** are labelled as such, with the reason and the time they were made (before or after a run). Any
  structural fix found necessary while building is disclosed. No constant moves.
- **Verification before the run.** Every row still S or M is re-checked, and its final status reported. Specifically:
  - Heskestad 1997's 500 K tip criterion, from the paper;
  - McCaffrey's burner size and Q range, from Table 1;
  - Correa et al.'s k_c, from the paper rather than via `char_oxidation.md`;
  - Mukunda et al. 2022's crib temperatures.

  A changed value gets a deviation run at that value; the nominal stays as registered.
- **Runtime** is recorded per run, with the load average.
- **The code** stays in `spikes/physics/hot/` as a record.

## References

1. Babrauskas, V. Temperatures in flames and fires. doctorfire.com (page read 2026-11-20), citing McCaffrey 1979,
   Cox & Chitty 1982, Ingason 1994, Heskestad 1997.
2. Cachim, P.B., Franssen, J.-M. (2009). Comparison between the charring rate model and the conductive model of
   Eurocode 5. *Fire Mater.* 33:129–143 (postprint, ORBi), Table II and §2.2.
3. Correa, N., et al. (2023). *Fire Saf. J.* 104049, Table 1 (via `../char_oxidation.md`).
4. Heskestad, G. (1997). Flame heights of fuel arrays with combustion in depth. *Fire Safety Science* 5:427–438
   (S, via 1).
5. McCaffrey, B.J. (1979). Purely Buoyant Diffusion Flames: Some Experimental Results. NBSIR 79-1910, pp. 5–8.
6. Mukunda, H.S., et al. (2022). A novel predictive model for free burning wooden cribs. *Combust. Theory Model.*
   (S, snippet).
7. White, R.H., Dietenberger, M.A. (2010). Wood Handbook FPL-GTR-190, ch. 18 (via `../char_oxidation.md`).
8. The parents: `../physics_spike/preregistration.md`, `../physics_spike/bed.md`,
   `../accelerant_spike/preregistration.md`, `../accelerant_spike/results.md`, `../char_oxidation.md`.
