# Char oxidation: do the crate's embers glow and burn out? (step 6, first task; 2026-11-20)

This is the literature research T17 made step 6's first task. It answers one question: for the tile's crate (a
0.6 m cube of 20 mm softwood slats at fuel volume fraction φ = 0.25, 32.4 kg), after flaming, which char-oxidation
model, with what cited constants, predicts whether the char glows and burns out, and over what time.

**Tags:** **V** read in a primary source here; **S** secondhand (snippet, abstract, or quoted); **M** from memory,
to verify; **D** derived here (scratch script, not committed); **Meas** measured in a cited source. Untagged numbers
restate the spike or the tile spec.

## 0. The answer, first

1. **Real cribs of this size glow and burn down for tens of minutes after flaming.** NIST burned a 39 kg pine crib
   of almost the same size (56 × 56 × 46 cm, 38 mm sticks). After the flaming peak at 23 min, its heat release fell
   to a low-smoke tail of 100 to 220 kW that lasted at least 18 min. At 45 min a bright orange ember bed was raked,
   and at about 48 min it was quenched with 7% of the mass left (§2.1, Meas).
2. **The spike's "no glow" came from the hand-over temperature, not from the kinetics.** 6c pins the burning
   surface at T_p, so the char was born at 380 °C. In a real burning slat, T_p (about 300 °C) belongs to the
   pyrolysis front *under* the char layer. The char surface above it runs at about 550 to 900 °C during flaming
   (§2.2). Char handed over at those temperatures is at or above the spike's own self-heating threshold of
   590–676 °C, which was computed with the same Morvan & Dupuy kinetics.
3. **Two more mechanisms the spike lacked keep it hot:**
   - Interior char exchanges radiation with neighbours at about the same temperature. Its net radiative loss is
     near zero, as in a charcoal pile or Ohlemiller's U-channel (§2.3).
   - Char also oxidises during the late flaming phase (§2.4).
4. **The literature's kinetics disagree by about 300 K on where oxidation turns diffusion-limited:** about 350 °C
   with TGA kinetics used as zone-II rates, about 700 °C with the Morvan & Dupuy apparent surface rate (§1).
   - Firebrand studies that measured glowing-char temperatures (700–1,100 °C) found the diffusion-limited
     (Reynolds-analogy) model predicted them best (§1.4).
   - In fire conditions, char oxidation is mostly diffusion-controlled (Correa et al. 2023).
5. **Recommendation (§4):**
   - A char layer with its own surface temperature: the front is pinned at T_p, the surface is not.
   - Oxidation by O₂ film transfer in series with a cited kinetic rate.
   - Arthur's CO/CO₂ split, with CO burning in the bed as the other range end.
   - Off under an attached flame.
   - The spike's in-bed radiation kept.
6. **Prediction for this crate (§5):**
   - **Glow: yes, with a moderate margin.** The interior char runs 700–1,000 °C; the outermost faces run about
     500–710 °C (D).
   - **Ember phase: about 7 to 32 min** (D), consistent with NIST's tail of at least 18 min.
   - **t_gone ≈ 20–45 min** after ignition, inside the 5,400 s cap.
7. **The real risk has moved from glow to burnout's 5% threshold.**
   - Real free-burning ember piles leave unburnt char: NIST's cribs left 5.3 ± 3.4% even with raking.
   - The step-6 model has no ash layer, pile collapse or dying-ember extinction, so it will probably burn the char
     to under 5%. That would be partly for the wrong reason, and it must be recorded as a Known gap.

**Confidence:** high that real crates glow; moderate that the recommended model shows it (a band under the
pessimistic kinetic end); low on the ember duration (±2×).

## 1. Kinetics of char oxidation

### 1.1 The rate laws in use

The rate of char burning per m² of surface is limited by two resistances in series. One is film transport of O₂ to
the surface; the other is the chemistry, at the surface or inside the pores. With mass-transfer coefficient h_m and
a kinetic surface velocity k_s:

  ṁ''_O₂ = ρ_g Y_O₂,∞ / (1/k_s + 1/h_m),  ṁ''_C = ṁ''_O₂ / s,

where s is the O₂ mass per kg of carbon: 2.67 to CO₂, 1.33 to CO. Under the Chilton–Colburn analogy with Le = 1,
ρ_g h_m = h/c_p (M, standard). The three classic regimes:
- **Zone I:** kinetics, O₂ everywhere in the pores; the rate ∝ char mass.
- **Zone II:** pore diffusion and kinetics together; the apparent E is about half the intrinsic E.
- **Zone III:** film diffusion; the rate depends only weakly on T.

These regimes and the Damköhler number that switches between them are set out in **Correa, Cuevas, Fuentes,
Torero & Reszka (2023)** (V).

**Intrinsic vs apparent.** TGA kinetics are *intrinsic*. They are fitted on milligram samples at 2.5–10 K/min,
in Zone I by construction, as a volumetric rate ∝ char mass. A slat's char layer is millimetres thick, so applying
them to it overstates the rate unless pore diffusion (a Thiele modulus) is added. *Apparent* kinetics are fitted
on burning particles or beds, with transport folded into A and E. The ACS Omega review (Yang et al. 2026) finds
apparent E in Zone II "not approximately half" of Zone I, because the reaction order is not 1 (S). No single (A, E) pair carries between scales.

### 1.2 Cited constants

| Source | Form | E (kJ/mol) | A | O₂ order | Status |
|---|---|---|---|---|---|
| Morvan & Dupuy 2004, via Mankame & Shotorban 2021 Eq. 23 (the spike's choice) | surface: ṁ''_O₂ = ρ Y k_s, k_s = 430 e^(−9000/T) m/s | 74.8 (D from 9,000 K) | 430 m/s | 1 | V numbers / M form (spike) |
| Lin & Huang 2022, Table 1, reaction "co" (Gpyro, wood smouldering, GA-fitted to TGA) | volumetric, ∝ ρ_char Y_O₂ | 184 | 10^12.9 s⁻¹ | 1 (char order 1.27) | V (text extraction of the table) |
| Branca & Di Blasi 2003 (wood char, TGA) | volumetric | 183 or 229 (by pyrolysis severity) | not seen | not seen | S (abstract) |
| Correa et al. 2023, Table 1 (from Anca-Couce et al. 2012 and Kashiwagi & Nambu 1992, E raised 20 kJ/mol "for better fit") | volumetric | 150 | log A = 6.55 (as extracted; inconsistent with E = 150 and a TGA peak near 450 °C, so probably garbled) | 0.68 | V text, garbled table |
| Anca-Couce et al. 2012 (pine, TGA in 4.3–20.5% O₂) | volumetric | not seen | not seen | 0.68 (via Correa and the ACS review) | S |
| Kashiwagi & Nambu 1992 (cellulosic paper) | volumetric | not seen (Correa: their E + 20 = 150, so about 130) | not seen | 0.78 (via a review snippet) | S |
| Yang et al. 2026 review: wood chars, intrinsic | — | 114–142 | — | 0.5–0.68 | S |
| Same review: wood chars, apparent, Zone II | — | 38–121 | — | — | S |
| Evans & Emmons 1977, "Combustion of wood charcoal", Fire Research 1:57–66 | 1-D charcoal in an air stream | not read | not read | not read | citation V, content not read |

**Sources disagree** by orders of magnitude in rate at a given T, but put wood char's E at roughly 110–230 kJ/mol
intrinsic and 40–120 apparent; Morvan & Dupuy (75 kJ/mol) is apparent.

### 1.3 Where each law turns diffusion-limited, and the self-heating threshold

From the scratch script (D). Interior char loses only convectively, h(T − T₀), and has no net radiative loss
(§2.3). The O₂ film capacity is h·Y/c_p = 4.2 × 10⁻³ kg O₂/m²·s at h = 20 W/m²K. Char per m² of fuel surface is
1.5 kg (600 kg/m³ × 10 mm × 0.25); char density is 150 kg/m³.

| Kinetic law | Kinetic O₂ capacity at 380 °C / 650 °C (kg/m²·s) | Turns film-limited near | Self-heating threshold T* (h = 15–25) |
|---|---|---|---|
| Morvan & Dupuy, surface | 5.6 × 10⁻⁵ / 2.2 × 10⁻³ | about 700 °C | **590–676 °C** (Arthur), 556–614 °C (CO₂ only); reproduces the spike's `closed_forms.py` |
| Lin & Huang, Zone II (Thiele, D_eff = 0.25 D_O₂-air, M) | 1.7 × 10⁻³ / 0.27 | about 380 °C | **327–349 °C** |
| Lin & Huang, Zone I over the whole char (upper bound) | 1.1 × 10⁻² / 215 | below 380 °C | 318–328 °C |

**This is the crux, and the literature reports both ends.** The ACS Omega review gives wood char's kinetic-to-diffusion
transition as "about 400 °C or 700 °C" (S). With TGA-derived kinetics, the spike's char at 380 °C would self-heat and
glow. With Morvan & Dupuy it does not. The spike chose the slow end unknowingly.

**Which end does experiment favour?**
- **Lattimer, Bearinger, Wong & Hodges (2022)** compared six char-oxidation models against single-firebrand tests.
  The heat and mass transfer Reynolds-analogy model, which is film-limited, was best: temperature within 5%,
  diameter within 4%, mass-loss rate within 29% (S, abstract and snippet).
- **Banagiri, Meadows & Lattimer (2023)** use a kinetics-to-convection resistance ratio of 0.1 as the switch, with
  a minimum oxidation temperature of 550 °C (S).
- **Correa et al. (2023):** "for compartment fire conditions, char oxidation will mostly occur under
  diffusion-controlled conditions." Da exceeds 1 within about 25 s at external fluxes ≥ 40 kW/m², "even before
  glowing and before flaming ignition" (V).
- **Terrei et al. (2024)** (Fire Safety J.; 600+ vertical tests, 7 species): the onset of char oxidation sits
  between 380 and 400 °C surface temperature under external heating (V, abstract). That is the low end, not 600 °C.

**The weight of measured evidence favours film-limited oxidation above about 550 °C.** Below that, kinetics
matter, and their onset is reported near 380–400 °C.

### 1.4 Glowing char is measured at 700–1,100 °C, film-limited

**Zhu & Urban (2024)** (V) measured glowing firebrand accumulations of birch dowels (6.35 and 12.7 mm) by
colour-ratio pyrometry:
- Glowing surface temperatures were 700–1,100 °C, with a mean of 897 ± 67 °C in one case and up to 930 °C at 2.7 m/s.
- They define glowing as smouldering with surface temperatures "in excess of approximately 600 °C causing the fuel
  surface to incandesce."
- "Because the glowing combustion is rate limited by oxygen, the heat release correspondingly decreases along the
  flow direction."
- Their model is film-limited oxidation, with a Spalding number, ετ = 0.7 (char emissivity × ash transmissivity),
  and zero net exchange between neighbouring firebrands. It reproduces the trend.

Lattimer et al. (2022), as their ref. 28, is the source of that model. **This is a cited, validated, minimal model
of exactly what the crate needs.**

## 2. Why real cribs glow: what the spike's model misses

### 2.1 Measured: a crib of this size glows for 18+ min

**McGrattan (2020), NIST TN 2102, Test 13, "Single Wood Crib"** (V; the HRR CSV from NIST's Fire Calorimetry
Database was analysed here):
- **The crib:** pine, 56 × 56 × 46 cm, 3.8 cm square slats, about 39 kg (39.39 kg on the load cell), moisture
  under 5%.
- **Ignition:** 0.75 kg of crinkle paper under the first row of slats.
- **Ending:** "At approximately 48 min, the hot coals were spread out and raked into a water bath."

| Time (min) | HRR (kW) | Cumulative (MJ) | Hood CO/CO₂ | Smoke K (1/m) |
|---|---|---|---|---|
| 23 (peak) | 380–396 | ~300 | ~0 | 0.011 |
| 30 | 217 | 433 | 0.004 | 0.001 |
| 34 | 158 | 478 | 0.011 | 0.001 |
| 40 | 127 | 526 | 0.022 | 0.001 |
| 46 (embers stirred at 45.4) | 118 | 565 | 0.039 | 0.000 |
| 48 → quench | 102 | 577 | 0.042 | 0.001 |
| end | — | 597 | — | — |

(Meas, D: read off the CSV at 1 s resolution.)
- **The tail from 30 to 48 min released 144 MJ at a mean of 133 kW.** It was smoke-free, and the hood CO/CO₂ rose
  from 0.004 to 0.04: the signature of char oxidation, not flaming.
- **The event photograph at 45 min** shows a collapsed bed of bright orange glowing coals with a small residual
  flame.
- **Test 14 (two cribs) repeats the pattern** (D): 32→52 min, 264 MJ, so 132 MJ per crib, with CO/CO₂ up to 0.058.
- **The residue was 2.85 kg (7.2%) when quenched**, glowing and not burnt out.
- **Table 1 gives the crib residue yield as 0.053 ± 0.034,** and the text says that "in order to burn as much of
  the items as possible, it was necessary to mix up the residue with a pike hook until all of the combustible
  material had been consumed" (V).

**Energy cross-check (D, spike's memory values).** The crib forms 0.25 × 39.4 = 9.85 kg of char and
29.5 kg of volatiles.
- Volatiles: 29.5 kg × 12.4 MJ/kg = 366 MJ. Char burnt: (9.85 − 2.85) kg × 28.5 MJ/kg (char as about 87% C, M) =
  200 MJ. Total 566 MJ, against 597 MJ measured (−5%). The memory values χ = 0.25 and ΔH_c,eff = 12.4 MJ/kg are
  consistent with this crib.
- By 30 min, 433 MJ had been released. Volatiles can supply only 366 MJ, so about 70 MJ, about a third of the
  char burnt, oxidised before or during the end of flaming (§2.4). This assumes the volatiles were exhausted by
  30 min, which the low smoke supports but doesn't prove.

**Differences from our crate:** 38 mm sticks (slower flaming, thicker char), a paper base fire, and a stir and
quench at 45 and 48 min. The *existence* of a glowing tail of at least 18 min carries over; its *length* does not, exactly.

### 2.2 Mechanism 1 (decisive): the char surface is not at T_p

The spike's 6c pins each burning surface's 1 mm skin at T_p, and the char inherits that skin temperature at
hand-over (`model.py::_iw_to_ic`, `t_new = Ts_iw`). The literature puts T_p elsewhere:
- **The char front is about 300 °C.** "The temperature at the base of the char layer is generally taken to be
  300 °C or 550 °F (288 °C)" (White & Dietenberger 2010, Wood Handbook ch. 18, V). That is the pyrolysis front.
- **The ignition surface temperature is a different quantity:** "the average surface temperature at ignition
  increases from 347 °C at imposed heat flux of 36 kW m⁻² to 377 °C at imposed heat flux of 18 kW m⁻²" (same, V).
  It describes virgin wood at the moment of ignition, before a char layer exists.
- **The char surface during and after flaming is much hotter:**
  - **Lin & Huang (2022)** (V) report the steady wood surface temperature under irradiation, measured and
    modelled. A near-limit blue flame survives only for "T_s > T_B ≈ 700 °C at q''_e > q''_B ≈ 40 kW/m²". They
    restate their 2021 experiment: "the near-limit blue flame appeared only if the char surface temperature
    exceeded 700 °C."
  - **Terrei et al. (2024):** surface temperatures at auto-ignition were 450–700 °C (ignition within 2 min) and
    700–800 °C (ignition after 2 min) (V, abstract). A plateau of about 750 °C at 49 kW/m² and about 502 °C for
    flameless char oxidation at 12.4 kW/m² come from a snippet (S).
  - **Inside cribs,** gas temperatures are reported from about 650 °C at the crib top to a peak of 900 °C (S,
    search snippet of a free-burning crib paper, not opened). Interior char surfaces bathed in that gas sit near it.
  - **A closed-form bound (D).** An outward char face absorbing only q''_f = 25 kW/m² and re-radiating at
    ε = 0.9 balances at 563 °C. That is a lower bound for a face also lit by in-bed radiation.
  - **Conduction alone overshoots:** a 5 mm char layer (k ≈ 0.10 W/mK, Correa Table 1, V) carrying 25 kW/m²
    needs 1,250 K across it, so re-radiation limits the surface; either way it is hundreds of K above 300 °C.

**The hand-over temperature, therefore:** about 550–650 °C on outward faces and 700–900 °C in the interior (D, from
the rows above). The spike's T_p hand-over (380 °C) is 200–500 K too cold.

**Consequence.** Even with the spike's own pessimistic kinetics (T* = 590–676 °C), interior char handed over at
700–900 °C is above threshold and runs up to the film-limited branch. Outward-face char at 550–650 °C sits in the
band, which is why the glow *area* margin depends on in-bed radiation (§2.3). The spike's conclusion that "glow is
decided by kinetics on/off" was a consequence of the 380 °C hand-over. With a physical hand-over, kinetics decide
only the margin at the envelope and the end of the burnout.

### 2.3 Mechanism 2 (sustaining): radiative exchange inside the bed

- **A single slab can't sustain itself.** "A single flat slab of wood which is thermally thick … will not sustain
  smoldering combustion unless an external heat flux supplements the heat from wood char oxidation …
  greater than about 1 W/cm²" (Ohlemiller & Shaub 1988, NBSIR 88-3767, V).
- **Facing surfaces do.** Their self-sustaining geometry is a U-channel, in which "smoldering on each interior slab
  face provides the sustaining flux for the face opposite." Temperature profiles "pointed to a dominance of
  radiative transfer in the smolder propagation process at low air flow rates" (V; also Ohlemiller 1991, Fire
  Safety Science 3:565, S).
- **Firebrand piles show the same thing:**
  - Salehizadeh, Hakes & Gollner (2021) (V): "Larger firebrand piles produced higher temperatures at the center
    of the pile." A 4 g pile's centre "only reached approximately 400 °C" while large piles' inner sensors
    averaged 500–700 °C. The authors attribute the difference to re-radiation.
  - Zhu & Urban (2024) set the net exchange between neighbouring brands to zero (V).
  - Eissa, Mueller & Ghodrat (2026, FDS): front brands reach about 1,200 °C, middle about 1,000 °C, rear about
    700 °C (S, abstract).

**For the crate:**
- **The spike already has this mechanism:** its P1 radiation makes slat-to-slat exchange and envelope leakage
  one solve. Keep it.
- **The 6d closed form (D) needs no radiation term for interior char.** Interior char's only loss is convective,
  h(T − T₀), so its film-limited equilibrium is set by O₂ depletion along the draught and by P1 leakage to the
  envelope, not by its own εσT⁴. The adiabatic rise Y·ΔH_O₂/c_p is about 2,600 K for CO₂ and 1,460 K for CO.
- **An outward face is a different matter (D):**

| h (W/m²K) | CO₂ only | Arthur | Tognotti |
|---|---|---|---|
| 10 | 531 °C | 502 °C | 498 °C |
| 15 | 607 °C | 558 °C | 561 °C |
| 25 | 713 °C | 632 °C | 646 °C |

  These are for ε = 0.9; at ετ = 0.7 (ash) add 35–55 K. A bare outward face is *marginal* against 625 °C.
- **What an observer sees is the sight-line integral into the bed** over ℓ = 4/σ_v ≈ 0.16 m. This is what the
  spike's t_glow already computes, and it is how a charcoal pile looks: dark grey outer coals with orange depths.

### 2.4 Mechanism 3 (partial): oxidation during flaming

- **During attached flaming, O₂ doesn't reach the char.** Blowing pyrolysis gas and the flame sheet consume it.
  This is the standard assumption in integral char models (M; I didn't find a primary quote).
- **As the pyrolysis flux falls toward extinction,** about 4 g/m²·s (Lin & Huang 2022, citing Emberley et al.;
  the spike uses 3.7), flames become discrete. Lin & Huang (V): "as the discrete blue flame only partially
  covered the char surface, the oxygen molecules may diffuse into the cracked and porous char layer to maintain the
  char oxidation."
- **NIST's energy split (§2.1)** suggests about a third of the char was burnt by the end of flaming (D).
- **The spike oxidised char only in cells with no flame** (`_char_oxidation`, the `nf` mask), so it missed this.
  It matters for burnout timing, not the glow verdict.

### 2.5 Mechanism 4 (not modelled): the bed collapses

The NIST crib at 45 min is a heap, not a crib. Collapse compacts the char:
- more mutual radiation and less envelope area per mass, which favours glow;
- less draught (Ergun) and thicker ash, which slow burnout.

A Known gap for step 6.

### 2.6 Candidates evaluated

| Candidate | Verdict |
|---|---|
| Char already hot at hand-over | **Decisive.** 550–900 °C, not 380 °C |
| Radiative exchange inside the crib | **Sustaining.** It removes the interior's radiative loss; the spike has it (P1); keep it |
| Flame heat feedback oxidising char during flaming | **Partial.** About a third of the char by flame-out (D); timing only |
| The char layer's surface-to-depth temperature profile | The same physics as row 1: the front is at about 300 °C, the surface hundreds of K hotter |
| O₂ access once flames retreat | Real, but not limiting: once flames go, the film supplies 25–65 kW/m² of O₂-limited heat (D) |

## 3. The CO/CO₂ split at the char surface

**Arthur (1951),** Trans. Faraday Soc. 47:164–178, doi:10.1039/TF9514700164 (V citation; body not read):
- **The formula:** CO/CO₂ = 10^3.4 e^(−12,400 cal/mol / RT) = 2,512 e^(−6,240/T).
- **The exponent:** 12,400/1.987 = 6,240 K (D).
- **Prefactor and exponent** are consistent with ANSYS CFX's char model, "the constants are given by Gibb as AS =
  2500 and TS = 6240 K" (V), which attributes them to Gibb, not Arthur. So the formula is S, consistent across two
  secondary sources.
- **What it gives:** CO/CO₂ is 1.6 at 773 K (0.62 CO) and 4.9 at 1,000 K (0.83 CO).

**Tognotti, Longwell & Sarofim (1990),** Proc. Combust. Inst. 23:1207 (S, abstract and later validation):
- The surface CO₂/CO falls exponentially with a coefficient of about 3,100 K. It is below 0.1–0.2 at combustion
  temperatures.
- Gas-phase CO oxidation near the particle adds CO₂ at high char temperatures, sooner with water vapour present.
- The form CO₂/CO = 0.02 e^(3,070/T) is M.
- Shaddix & Geier judged the correlation credible only below about 1,250 K (S).
- Both correlations say **mostly CO at the surface above about 800 K.** Holzleithner et al. find the ratio also
  depends on local O₂ (S).

**What it does to the ember temperature.** Per kg of O₂, CO₂ releases 12.3 MJ and CO releases 6.9 MJ (D, from NIST
ΔfH).
- At the film limit, Arthur products give 64% of the CO₂-only surface heat (D).
- That lowers an outward face by 30–80 K (§2.3 table) and an interior ember by roughly 200 K (the spike measured
  938 → 738 °C mean).
- **Where the CO burns decides the heat.** Blue flames over charcoal are CO burning in the boundary layer (M, common
  observation). NIST's hood CO/CO₂ stayed at 0.02–0.06 through the tail (Meas): globally, almost all the CO
  became CO₂ before the hood. The hood can't say whether it burned inside the pile, returning heat to it, or in
  the plume above.

**Recommendation:** Arthur at the surface, with two ends: CO leaves the bed (pessimistic), CO burns in the bed's
hot gas (optimistic). The spec's CO₂-only 6d is the optimistic surface end; don't use it alone.

## 4. The pyrolysis temperature question

| Quantity | Value | Source | Status |
|---|---|---|---|
| Char-base (front) temperature | 300 °C (288 °C) | White & Dietenberger 2010, Wood Handbook ch. 18 | V |
| Piloted ignition surface temperature, various woods (SG 0.33–0.69, horizontal) | 347 °C at 36 kW/m² → 377 °C at 18 kW/m² | same | V |
| Piloted ignition, softwoods, for engineering | T_ig ≈ 627 K (354 °C) | Janssens 1991 PhD (Gent), via Correa et al. 2023 | S |
| Flaming softwoods | 349–364 °C; 300–310 °C at low flux | Babrauskas, "Ignition of Wood" slides (spike) | V (spike) |
| Lignin C–C cleavage; volatiles end | 370–400 °C; about 450 °C | Wood Handbook ch. 18 | V |
| Glowing ("afterglow") onset | "Above 450 °C, the remaining wood residue is an activated char that undergoes further degradation by being oxidized to CO₂, CO, and H₂O until only ashes remain" | Wood Handbook ch. 18 | V |
| Char oxidation onset under heating | 380–400 °C surface | Terrei et al. 2024 | V (abstract) |

**Answers:**
1. **The spec's 380 °C is not out of the literature** for an *ignition surface temperature*: Wood Handbook gives
   377 °C at 18 kW/m². It sits at the low-flux end; at the crate's flame fluxes (25 kW/m² plus) about 350–365 °C
   is better supported. The spike's range ends (300, 364) were reasonable.
2. **T_p is the wrong hand-over temperature for char,** whatever its value. It belongs to two places, never the
   char surface:
   - the virgin surface at ignition, where 350–380 °C is supported;
   - the pyrolysis front under the char, where about 300 °C is the char-line convention.
3. **A kinetics-based pyrolysis model isn't needed for the glow question.** Lin & Huang's 5-step Gpyro scheme
   (drying, hemicellulose, cellulose, lignin, char oxidation; E = 130/106/154/229/184 kJ/mol) is the cited option
   if step 6 later needs one. It is out of proportion for a 0.1 m cell. A fixed front temperature with an integral
   char layer is the standard engineering model (Wood Handbook's char line; Quintiere's integral models, M).

## 5. Recommendation for step 6's 6d, and the prediction

### 5.1 The minimal cited model

For each part of a bed cell's fuel surface, in the existing sub-cell surface layer (per m² of fuel surface, in
metres, never per cell):

1. **The char layer, during flaming (replaces "surface pinned at T_p"):**
   - **State:** char areal mass m_c (kg/m²), and a char-surface temperature T_c in a lumped surface node.
   - **Surface balance:** the flame flux q''_f, plus the absorbed in-bed radiation εG/4, minus εσT_c⁴, minus
     conduction through the char to the front, k_c(T_c − T_p,front)/δ_c with δ_c = m_c/ρ_c.
   - **Pyrolysis:** m'' = (conduction reaching the front − conduction into virgin wood)/L_g.
   - **Constants:**
     - T_p,front = 300 °C, Wood Handbook (V).
     - k_c = 0.10 W/mK, Correa Table 1 (V; radiative conductivity in the pores at high T, M, to research).
     - ρ_c = χ·ρ_wood with no shrinkage (D).
   - **What it buys:** the char is hot when flaming ends, from a cited energy balance, with no constant chosen for
     the outcome.
   - **Ignition stays on virgin wood** at T_ig ≈ 350–365 °C, by flux with a band (spike lesson 4).
2. **Oxidation (6d proper):**
   - **The law:** ṁ''_O₂ = Y_O₂,local / (1/(ρ_g k_s(T_c)) + c_p/h), the local h from the bed's existing
     convective correlation (Le = 1, Chilton–Colburn).
   - **Two cited kinetic ends, both run:**
     - (a) film-limited with a kinetic cut-off at 550 °C, Banagiri et al. 2023 (S) and the Lattimer et al. 2022
       method (S): the nominal end;
     - (b) Morvan & Dupuy k_s = 430 e^(−9000/T) m/s: the pessimistic end.
   - **Don't use** TGA volumetric kinetics (Lin & Huang, Branca & Di Blasi) on a whole char layer; they are
     Zone I rates and need a Thiele term (§1.3).
   - **When it's on:** off on surface area under an attached flame (m'' ≥ m''_crit); on as the pyrolysis flux
     falls below it.
   - **Products:** Arthur at the surface (S), with CO burning in the bed as the other end (§3).
   - **The ledger:** char heat at 28.5 MJ/kg (C → CO₂, × 0.87 carbon, M) or the Arthur blend.
3. **Radiation:** the spike's in-bed P1, unchanged. It is what sustains interior char.
4. **Burnout:** the char area is held until its mass is gone, as in the spike. There is no ash layer, collapse or
   dying-pile extinction; record all three as Known gaps with this file's NIST numbers.

**What this adds to step 6:** one surface temperature, one char-thickness state per surface part and one
flame-cover switch. Each needs a closed form (the T_c steady balance, the §2.3 ember temperature, the §1.3
threshold), plus a cross-tier test on t_glow and t_gone.

### 5.2 Prediction for the crate (order of magnitude, D)

| Quantity | Nominal (film-limited) | Pessimistic (Morvan & Dupuy) |
|---|---|---|
| Hand-over T_c, interior / outward | 700–900 / 550–650 °C | same |
| Interior char ignites? | yes (T* ≈ 330–350 °C or the 550 °C cut-off) | yes if T_c > 590–676 °C: interior yes, outward faces marginal |
| Interior ember T | 700–1,000 °C, limited by O₂ depletion and P1 leakage | same once lit |
| Outward bare face T | 500–710 °C (h 10–25, products) | lower, or out |
| Glow (≥ 0.08 m² of envelope at ≥ 625 °C, sight-line) | **PASS**, moderate margin | **probable PASS**; the margin rests on the sight-line seeing interior char within 0.16 m |
| Char oxidation power, 5.4 m² at the film limit | 90–350 kW (h 10–25; Arthur to CO₂) | lower, then film-limited once hot |
| Ember phase, 8.1 kg char at constant area | 420–1,890 s (7–32 min) | longer |
| t_gone, after accelerant ignition | flaming 450–770 s (spike F) + embers ≈ **20–45 min** | ≤ 60 min |
| Analogue | NIST 39 kg crib: ≥ 18 min tail at 100–220 kW, not finished at 48 min | — |

**Burnout timing is uncertain by about 2×:** shrinking area and a collapsed pile's weaker draught lengthen the
tail; oxidation during flaming shortens it.

**The 5,400 s cap is safe at every end** (D).

### 5.3 Pass/fail risks, plainly

1. **1b glow: low to moderate risk.**
   - Real crates of this size glow (Meas, NIST).
   - The recommended model should show it with no constant chosen for the outcome.
   - **The remaining risk is the outward faces.** A bare char face with full view of 20 °C surroundings
     film-limits at only 500–710 °C. If step 6's envelope observable weights the outer 1–2 cm heavily, the glowing
     area could fall short at the low-h, CO-escapes end.
   - Run that end.
2. **1c burnout to 5% within 5,400 s: moderate risk, and the honest physics is less favourable than the model.**
   - Real ember piles die with char left. NIST needed a pike hook to reach 5.3 ± 3.4%, and Test 13 still had 7.2%
     when quenched at 48 min.
   - Ash (about 0.3–0.5% of softwood, M) alone is under 5%. Unburnt char at the dying edge is not.
   - **The model probably passes 1c because it lacks the mechanisms that stop real piles:** ash blanketing,
     collapse and small-pile radiative loss.
   - **This must be recorded in Known gaps as "passes for a missing reason,"** and the owner should know that a
     real crate left alone may not reach 5% within 90 min.
3. **The spike's verdict is reversed,** but not by tuning:
   - the hand-over temperature changes from a misattributed constant (T_p) to a cited energy balance;
   - a cited film-limited model, validated on glowing char, becomes the nominal kinetic end.
   - **Disclosure:** this research followed the miss; both kinetic ends are fixed here, before any rerun, and the
     rerun reports both.
4. **The fallback (option 3) is not needed for glow** on present evidence. If the rerun misses 1b at the
   pessimistic end only, that is a band in the outcome. Report it as such, not as a pass.

## 6. What remains unverified

- **The Morvan & Dupuy rate form** (ρY·k_s, units of 430 m/s) is still only read via Mankame & Shotorban. The
  original isn't opened (spike status M form).
- **Lattimer et al. 2022 and Banagiri et al. 2023** were seen only as abstract and snippets. The best-model claim,
  its 5/4/29% errors and the 550 °C cut-off need the full texts.
- **Arthur 1951's body is unread.** The constants are consistent across ANSYS (attributed to Gibb) and the spike's
  snippet. Tognotti's form is M.
- **Branca & Di Blasi 2003** (J. Anal. Appl. Pyrolysis 67:207–219, venue M) and **Di Blasi 2009** (PECS
  35:121–140, doi:10.1016/j.pecs.2008.08.001, V citation) are unread for A and order. **Evans & Emmons 1977** and
  **Kashiwagi & Nambu 1992** are unread.
- **Snippet-only:** the crib gas temperatures (650–900 °C) and Terrei's 750 °C plateau. Bartlett, Hadden & Bisby
  2019 (doi:10.1007/s10694-018-0787-y) was blocked; read it for char-surface temperatures.
- **Correa Table 1's char-oxidation row** extracted garbled (log A = 6.55 is inconsistent with E = 150).
- **Babrauskas's Ignition Handbook** (2003) glowing-ignition chapter and **Rein's SFPE smouldering chapter** were
  not opened.
- **§5.2 is hand calculation at constant area;** the 0.1 m run of §5.1 is the test.

## 7. References

1. Arthur, J.R. (1951). Reactions between carbon and oxygen. *Trans. Faraday Soc.* 47:164–178.
   doi:10.1039/TF9514700164
2. ANSYS CFX-Solver Theory Guide v25.2, §6.3.5 Reactions (Gibb constants).
3. Banagiri, S., Meadows, J.W., Lattimer, B.Y. (2023). A computational fluid dynamics model to estimate local
   quantities in firebrand char oxidation. *J. Fire Sci.* doi:10.1177/07349041231195847
4. Branca, C., Di Blasi, C. (2003). Global kinetics of wood char devolatilization and combustion. *J. Anal. Appl.
   Pyrolysis* 67:207–219 (venue from memory).
5. Correa, N., Cuevas, J.I., Fuentes, A., Torero, J.L., Reszka, P. (2023). Understanding the effect of char
   oxidation on wood temperature profiles for varying heating and oxygen conditions. *Fire Saf. J.* 104049.
   doi:10.1016/j.firesaf.2023.104049 (accepted manuscript: discovery.ucl.ac.uk/10182076)
6. Di Blasi, C. (2009). Combustion and gasification rates of lignocellulosic chars. *Prog. Energy Combust. Sci.*
   35:121–140. doi:10.1016/j.pecs.2008.08.001
7. Eissa, O., Mueller, E.V., Ghodrat, M. (2026). Numerical simulation of firebrand pile burning behaviour under
   different cross-flows. *Int. J. Wildland Fire*. doi:10.1071/WF25202
8. Evans, D.D., Emmons, H.W. (1977). Combustion of wood charcoal. *Fire Research* 1:57–66.
9. Kashiwagi, T., Nambu, H. (1992). Global kinetic constants for thermal oxidative degradation of a cellulosic
   paper. *Combust. Flame* 88:345–368.
10. Lattimer, B.Y., Bearinger, E., Wong, S., Hodges, J.L. (2022). Evaluation of models and important parameters for
    firebrand burning. *Combust. Flame* 235:111619. doi:10.1016/j.combustflame.2021.111619
11. Lin, S., Huang, X. (2022). Extinction of wood fire: modeling smoldering and near-limit flame under irradiation.
    *Fire Technol.* doi:10.1007/s10694-022-01295-2 (preprint: ira.lib.polyu.edu.hk/bitstream/10397/108055)
12. Lin, S., Huang, X., Gao, J., Ji, J. (2021). Extinction of wood fire: a near-limit blue flame above hot
    smoldering surface. *Fire Technol.* doi:10.1007/s10694-021-01146-6
13. McGrattan, K. (2020). Heat Release Rates of Multiple Transient Combustibles. NIST TN 2102.
    doi:10.6028/NIST.TN.2102; Test 13 data: NIST Fire Calorimetry Database, `Test13_woodCrib_r1`
    (https://www.nist.gov/node/1674296)
14. Ohlemiller, T., Shaub, W. (1988). Products of Wood Smolder and Their Relation to Wood-Burning Stoves. NBSIR
    88-3767. https://nvlpubs.nist.gov/nistpubs/Legacy/IR/nbsir88-3767.pdf
15. Ohlemiller, T.J. (1991). Smoldering combustion propagation on solid wood. *Fire Safety Science* 3:565–574.
    doi:10.3801/IAFSS.FSS.3-565
16. Salehizadeh, H., Hakes, R.S.P., Gollner, M.J. (2021). Critical ignition conditions of wood by cylindrical
    firebrands. *Front. Mech. Eng.* 7:630324. doi:10.3389/fmech.2021.630324
17. Terrei, L., Flity, H., Ikhou, O., Trohel, G., Torero, J.L., et al. (2024). Effect of the wood species on the
    fire behavior in vertical orientation. *Fire Saf. J.* 104234. doi:10.1016/j.firesaf.2024.104234
18. Tognotti, L., Longwell, J.P., Sarofim, A.F. (1990). The products of the high temperature oxidation of a single
    char particle in an electrodynamic balance. *Proc. Combust. Inst.* 23:1207–1213 (title and pages from memory).
19. White, R.H., Dietenberger, M.A. (2010). Fire safety of wood construction. *Wood Handbook* (FPL-GTR-190),
    ch. 18. USDA Forest Products Laboratory.
20. Yang, J., Wu, X., Yang, L., Xu, J., Wu, S., Lai, M. (2026). Multiscale perspectives on char oxidation: reaction
    regimes, transport phenomena, and modeling challenges. *ACS Omega* 11(22):31831–31852.
    doi:10.1021/acsomega.5c13555
21. Zhu, L., Urban, J.L. (2024). Analyzing the ignition capabilities of glowing firebrand accumulations. *Proc.
    Combust. Inst.* doi:10.1016/j.proci.2024.105746
22. Morvan, D., Dupuy, J.L. (2004). Modeling the propagation of a wildfire through a Mediterranean shrub using a
    multiphase formulation. *Combust. Flame* 138:199–210 (title and pages from memory), via Mankame & Shotorban
    (2021), *Front. Mech. Eng.* 7:640979 (spike, V).
