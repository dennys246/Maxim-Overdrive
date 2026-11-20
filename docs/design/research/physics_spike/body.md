# Physics spike Q5: what a body near the fire feels (2026-11-19)

Code: `spikes/physics/body/` (`run.py` computes and writes `results/results.json`; `report.py` prints the tables).
The fire is parametrised from `tile_and_client.md` §5, not taken from the concurrent Q1 fire model, so Q5 doesn't
depend on Q1's outcome. Anything Q1 measures (heat release, ember temperature) replaces the matching row here.

**Verdicts.** **5a: reported** (§5). **5b: MISS.** At 1 m in the flaming peak, bare skin reaches pain in 1.0–4.7 s
under every flux model and at both ends of the heat release, below the 10 s floor. At 2 m the pre-registered point
source is inside the window (10–14 s at 777 kW, 35–46 s at 402 kW); the Shokri-Beyler upper end falls below it
(4.8–9.3 s). Per the pre-registration, this goes to D28's design note
(§7). It is not a physics failure.

## 1. The fire, parametrised

| Quantity | Value | Source |
|---|---|---|
| Flaming heat release Q̇ | 777 kW (q″_f = 25) and 402 kW (q″_f = 15), both run | tile spec §5.3, derived from constants that are *from memory* |
| Flaming duration | 390 s and 750 s | tile spec §5.3 |
| Radiative fraction χ_r | 0.30 | tile spec §5.1, *from memory*. NUREG-1805 ch. 5 gives 0.15–0.60 across fuels (verified). Point-source flux is linear in χ_r |
| Equivalent diameter D | 0.677 m (circle with the 0.6 m crate's footprint) | NUREG-1805 eq 5-3, verified |
| Flame height H_f | 0.235 Q̇^0.4 − 1.02 D = **2.68 m** (777 kW), **1.90 m** (402 kW) | Heskestad (1995) via NUREG-1805 eq 5-8, verified |
| Ember surfaces | the crate's face toward the body (0.36 m²) plus its top, at **550 °C** and **920 °C**, ε = 0.9 | tile spec §5.3 derives both ends (bare char face, envelope ember); ε from §5.1, *from memory* |
| Ember duration, release | 1,750 s at ~150 kW | tile spec §5.3, derived |

I treat "the fire's peak" as the start of the flaming plateau: the flux steps on at t = 0 against skin at its
no-fire steady state and stays at that value. The real fire ramps up over ~60 s, so a body already standing there
gets a gentler start. An ember-phase run uses the same step.

**Ember energy check (this spike, derived).** At 920 °C, a char face emits 103 kW/m². Over the whole 1.8 m²
envelope that is 186 kW, more than the ~150 kW the embers release. So 920 °C across every face can't be sustained,
and the 920 °C rows are an upper bound. 550 °C emits 23 kW/m², 42 kW over the envelope, which is consistent.

## 2. Flux models and their disagreement

**Geometry.** "d m from the crate" means from the crate's vertical axis. That is the convention behind the tile
spec's 18.5 kW/m² at 1 m and NUREG's L (cylinder centre to target). §4 also reports distances from the crate's face
(axis + 0.3 m). The target is a vertical element on the body's front, facing the axis, sampled every
0.05 m from 0.05 to 1.80 m. Pain uses the **hottest height** (pain starts at the hottest spot first). The core uses
the **mean over the body's height** times the 0.5 m² projected area.

- **Point source** (T14): q″ = χ_r Q̇ cos θ / (4πR²), with the source at the flame's mid-height (NUREG-1805 eq 5-1,
  after Drysdale; the cosine is Modak's form). Verified.
- **Solid flame:** a vertical cylinder of diameter D and height H_f, with q″ = E·F. F is the vertical-element view
  factor from NUREG-1805 eq 5-12 to 5-14 (Beyler, SFPE Handbook), verified. It agrees with an independent midpoint
  quadrature over the cylinder's visible surface to 5×10⁻⁶. E is run at two ends:
  - **E = χ_r Q̇ / A_flame** (38.5 kW/m² at 777 kW, 27.4 at 402 kW, derived): the solid flame that radiates exactly
    the point source's power. This is the lower end.
  - **E = 58·10^(−0.00823 D) = 57.3 kW/m²**: Shokri & Beyler (1989) via NUREG eq 5-6, verified. It was fitted to
    sooty pool fires, so for a wood crib it is the upper end.
- **Ember faces:** the exact view factor (a closed-form superposition for the front face, checked by quadrature to
  10⁻⁶, plus quadrature for the top) against a far-field "point" form, E·A·cos θ₁ cos θ₂ / (πR²) per face.

**Incident flux, kW/m², at the hottest height / averaged over the body (from the axis):**

| Phase | Case | Model | 1 m | 2 m | 3 m |
|---|---|---|---|---|---|
| flaming | 777 kW | point | 18.5 / 12.7 | 4.6 / 4.0 | 2.1 / 1.9 |
| flaming | 777 kW | solid, E = χ_rQ̇/A | 12.4 / 11.3 | 4.7 / 4.3 | 2.4 / 2.2 |
| flaming | 777 kW | solid, Shokri-Beyler | 18.4 / 16.8 | 7.1 / 6.4 | 3.5 / 3.3 |
| flaming | 402 kW | point | 9.6 / 7.1 | 2.4 / 2.2 | 1.1 / 1.0 |
| flaming | 402 kW | solid, E = χ_rQ̇/A | 8.3 / 7.3 | 2.7 / 2.5 | 1.3 / 1.2 |
| flaming | 402 kW | solid, Shokri-Beyler | 17.3 / 15.2 | 5.7 / 5.2 | 2.7 / 2.5 |
| ember | 550 °C | point / view factor | 5.4 / 4.3 | 0.9 / 0.9 | 0.4 / 0.4 |
| ember | 920 °C | point / view factor | 24.1 / 19.4 | 4.1 / 3.9 | 1.6 / 1.6 |

(The ember rows give peak flux for both models.)

**Disagreement.**
- **For an energy-consistent flame, the point source overestimates near the fire and slightly underestimates far
  from it.** At 777 kW: 1.5× at 1 m (18.5 against 12.4), equal at 2 m, 0.88× at 3 m. A cylinder radiates more
  sideways than an isotropic point, and the point's 1/R² diverges close in.
- **The choice of E outweighs the choice of model:** Shokri-Beyler gives 1.5–2.1× the energy-consistent E.
- **FPH-N3's "~7–10 kW/m² at 1 m, so the spec is ~2× high" doesn't reproduce from the axis.** With the exact
  cylinder F, F at 1 m is 0.32 (FPH-N3 assumed 0.2–0.3), and E ranges 38–57. That gives 12–18 kW/m², so the spec's
  18.5 is at most 1.5× high. FPH-N3's figure matches distances measured from the crate's face: 11 kW/m² by point
  source, 8–12 by solid flame at 1.3 m from the axis.
- **The embers' far-field form is 1.25× high at 1 m and exact by 2 m.**

## 3. The skin and core models

**Skin: a 1-D Pennes bioheat column,** with three layers and the properties from Torvi & Dale (1994) as tabulated in
Jasiński (2003) (verified):

| Layer | Thickness | k (W/m·K) | ρc (J/m³·K) | Perfusion | Metabolic heat |
|---|---|---|---|---|---|
| epidermis | 0.1 mm | 0.235 | 4.31×10⁶ | none | none |
| dermis | 2 mm | 0.445 | 3.96×10⁶ | 0.00125 s⁻¹ | 245 W/m³ |
| subcutaneous | 10 mm | 0.185 | 2.67×10⁶ | 0.00125 s⁻¹ | 245 W/m³ |

- **Blood** ρc 4.00×10⁶ J/m³·K at 37 °C; the base held at 37 °C. **Surface:** h = 8 W/m²·K (same source) plus
  radiation to 20 °C; skin ε and absorptance 0.95 (the tile spec's).
- **Numerics:** vertex-centred finite volumes with nodes on the layer interfaces, backward Euler at dt = 0.01 s, and
  radiation as a conductance lagged one step. Halving dt changes time to pain by ≤ 0.05%; doubling the grid, by
  ≤ 0.08%.
- **Initial state:** the no-fire steady state. That puts the surface at 32.4 °C bare and 34.7–35.2 °C clothed.
- **Pain** is a temperature at the receptor depth, 0.1 mm, the epidermis–dermis interface:
  **44.8 °C** (Buettner 1951, J. Appl. Physiol. 3:703; value verified from the abstract, author from memory) and
  **43.0 °C** (EN ISO 9886, the low end of Havenith & Daanen's 43–45 °C, both via IFV/Heus 2016, verified).
- **Burn:** the Henriques integral at the basal layer (P = 1.43×10⁷² s⁻¹ above 317 K, ΔE/R = 55,000 K, same
  source). Second degree is Ω = 1.
- **Clothing:** one cotton layer (c = 1,340 J/kg·K, Engineering ToolBox), absorptance and emissivity 0.9 (*from
  memory*), over an air gap that conducts (k_air/δ) and radiates to the skin. The outer face loses h = 10 W/m²·K plus
  radiation. Two cases bracket the range:
  - **light:** a 120 g/m² shirt over a 6.4 mm gap. The gap is the ASTM F1939 spacer, *from memory*.
  - **heavy:** a 220 g/m² shirt over a 25 mm gap. The gap is Lu et al. (2013), fit protective clothing. Shirt
    weights are from Printful's 119–220 g/m² range.

**Validation (none of it fitted):**

| Check | Published | This model |
|---|---|---|
| Jasiński (2003) example 1: 6.5 kW/m² absorbed for 18 s, first-degree burn | 16.25 s | 17.1 s (+5%) |
| the same example, second-degree burn | 17.8 s | not reached in 18 s (the model is slower) |
| Bare skin, 4.0 kW/m² to pain (Hoschke 1981, via IFV 2016) | 15 s | 13.5–18.1 s |
| Bare skin, 6.3 kW/m² (API 521 example, secondary source) | 8 s | 5.8–7.8 s |
| Bare skin, 9.45 kW/m² ("≈ 6 s, escape only", API RP 521 1997, secondary) | ~6 s | 2.9–3.8 s |
| Clothed, time to 43 °C, RadMan manikin, operator clothing (IFV 2016 Table V), 3.0 kW/m² | 33–88 s | 85–107 s |
| the same, 4.6 kW/m² | 20–58 s | 42–53 s |
| the same, 6.3 kW/m² | 18–68 s | 25–33 s |
| the same, 10 kW/m² | 13–20 s | 13–18 s |

The model sits in the anchors' range: 5% slow on Jasiński's case, slow on the clothed 3 kW/m² case. The 9.45 kW/m²
"6 s" is escape guidance, not a measured pain time.

**Core:** the T5 lump, 70 kg, with c at **3,470** (conventional) and **2,980 J/kg·K** (Xu, Rioux & Castellani 2022,
*Temperature*, PMC10274559, verified).
Gross rate 0.95·q̄·0.5 m²/(m·c); net subtracts the spec's losses at 37 °C in 20 °C air (convection over 1.9 m² plus
radiation, 514 W). No metabolism, as in the spec (~100 W at rest, *from memory*, would offset a fifth of that).

## 4. Results

Time to pain, in seconds, in the form t(43.0 °C)–t(44.8 °C). "Never" means the steady receptor temperature stays
below the threshold, or the threshold isn't reached within the phase. Flaming runs end at 390 s (777 kW) or 750 s
(402 kW); ember runs end at 1,750 s.

| Phase | Case | Model | Clothing | 1 m | 2 m | 3 m | 2nd-degree burn, 1 m |
|---|---|---|---|---|---|---|---|
| flaming | 777 kW | point | bare | 1.0–1.2 | 10–14 | 45–60 | 4.4 |
| | | | light–heavy | 5.9–10 | 41–70 | 166–327 | 18–22 |
| flaming | 777 kW | solid, χ_rQ̇/A | bare | 1.8–2.4 | 9.8–13 | 36–47 | 8.3 |
| | | | light–heavy | 9.5–16 | 40–67 | 129–242 | 32–38 |
| flaming | 777 kW | solid, Shokri-Beyler | bare | 1.0–1.3 | 4.8–6.3 | 17–23 | 4.5 |
| | | | light–heavy | 5.9–10 | 21–36 | 65–113 | 18–22 |
| flaming | 402 kW | point | bare | 2.8–3.7 | 35–46 | 154–215 | 13 |
| | | | light–heavy | 13–23 | 125–233 | never | 46–55 |
| flaming | 402 kW | solid, χ_rQ̇/A | bare | 3.6–4.7 | 27–36 | 109–148 | 16 |
| | | | light–heavy | 16–28 | 99–178 | 498–never | 56–67 |
| flaming | 402 kW | solid, Shokri-Beyler | bare | 1.1–1.4 | 7.0–9.3 | 29–38 | 4.9 |
| | | | light–heavy | 6.4–11 | 29–50 | 105–190 | 20–24 |
| ember | 550 °C | view factor (point) | bare | 12–16 (7.8–10) | 233–348 (213–312) | never | 44 (31) |
| | | | light–heavy | 46–78 (32–55) | never | never | 146–176 |
| ember | 920 °C (upper bound) | view factor (point) | bare | 0.9–1.2 (0.7–0.9) | 14–19 (13–17) | 72–96 (70–93) | 4.2 (3.0) |
| | | | light–heavy | 5.6–9.6 (4.5–7.7) | 54–93 (51–87) | 279–719 | 17–21 |

**Core warming rate, K/min, gross at c = 3,470 (and at 2,980) / net of the spec's losses:**

| Phase | Model | 1 m | 2 m | 3 m |
|---|---|---|---|---|
| flaming 777 kW | point | +1.49 (+1.74) / +1.36 | +0.47 (+0.55) / +0.35 | +0.23 (+0.26) / +0.10 |
| flaming 777 kW | solid, Shokri-Beyler | +1.97 (+2.30) / +1.85 | +0.75 (+0.87) / +0.62 | +0.38 (+0.45) / +0.26 |
| flaming 402 kW | point | +0.84 (+0.97) / +0.71 | +0.26 (+0.30) / +0.13 | +0.12 (+0.14) / −0.01 |
| ember 550 °C | view factor | +0.30 (+0.35) / +0.17 | +0.09 (+0.10) / −0.04 | +0.04 (+0.05) / −0.09 |

The core rates here are lower than the spec's §2.1 figure (+2.3 K/min at 1 m). The spec multiplies the peak flux
by the whole 0.5 m² at absorptance 1; this spike uses the flux averaged over the body's height at absorptance 0.95.

**Measured from the crate's face** (axis + 0.3 m), bare skin in the flaming phase: 1.6–4.1 s at 1 m and 7.2–23 s
at 2 m (777 kW); 2.0–9.4 s and 11–76 s (402 kW). The window moves out by about 0.3 m and 1 m still misses (full
table: `report.py`).

## 5. Criterion 5a, reported

- **Time from the fire's peak to pain**, bare skin, 777 kW, at 1 / 2 / 3 m from the axis:
  - point source: **1.0–1.2 / 10–14 / 45–60 s**;
  - energy-consistent solid flame: **1.8–2.4 / 9.8–13 / 36–47 s**;
  - Shokri-Beyler: **1.0–1.3 / 4.8–6.3 / 17–23 s**.
  - At 402 kW: 2–3× longer at 1 m and about 3.5× longer at 2–3 m under the point and energy-consistent models;
    Shokri-Beyler barely changes, because its E doesn't depend on Q̇.
  - Clothing multiplies the time by about 5–9 at 1 m and 3.5–5.5 at 3 m.
- **Core warming rate:** +1.3 to +2.3 K/min gross at 1 m in the flaming peak, +0.26 to +0.87 at 2 m, +0.12 to +0.45
  at 3 m. Net of the spec's no-metabolism losses, the body cools beyond about 3 m in the 402 kW case and beyond 2 m
  from 550 °C embers.

## 6. Criterion 5b: MISS

The window is 10–120 s at 1–2 m.

- **1 m: misses fast in every flaming configuration** for bare skin: 1.0–4.7 s (both heat-release ends, all three
  flux models). The pre-registered model (point source plus view-factor surfaces) gives 1.0–1.2 s at 777 kW.
- **2 m: inside the window** for the pre-registered point source: 10–14 s at 777 kW, 35–46 s at 402 kW. Shokri-
  Beyler at 777 kW falls just below it (4.8–6.3 s).
- **Embers:** at 920 °C, 1 m misses fast (≤ 1.2 s). At 550 °C, 1 m is in the window (12–16 s view factor, 7.8–10 s
  point) and 2 m misses slow (213–348 s).

The window exists in the 1–2 m band, but not across it. No constant was moved to look for a pass.

## 7. What D28's design note should take from this

1. **The skin, not the core, is the clock.**
   - Pain arrives in 1–60 s while the T5 lump moves 0.03–0.25 K. A core-only heat debt would be fire-blind on the
     timescale that matters, and its 1–2 K/min reads as "nothing happens for minutes".
   - This confirms FPH-N4. D28 needs a skin node, a 1-D column like this one or a calibrated two-node fit, and the
     tile spec's §2.1 receptor volumes need a caller.
2. **The interesting band is about 2–3 m in the flaming peak for bare skin, and about 1–2 m clothed.**
   - Bare skin at 2 m: 10–46 s (pre-registered model).
   - Clothed at 1 m: 6–28 s. Clothed at 2 m: 40–233 s.
   - 1 m bare is a 1–5 s "don't stand here", which is useful as a hard edge, not a trade-off.
   - The window moves with fire size: the 402 kW end lengthens each distance's time 2–3.5×. A design keyed to
     distances should key to flux instead, about 2–6 kW/m² for bare skin (pain in 10–120 s), so it carries over to
     other fires.
3. **Clothing is the biggest single lever after distance:** 3.5–9× at the same flux, and it is a real player choice.
   It makes "dress for the burning bay" a mechanic with physical grounding.
4. **Pain-to-burn margin is short.** A bare second-degree burn follows pain by about 3–4× the pain time (4.4 s
   against 1.0–1.2 s at 1 m; 44 s against 12–16 s at 550 °C embers). A heat-debt meter that waits for pain leaves little
   room before injury.
5. **The ember phase is the longer game.** At 550 °C, 1 m is a 12–16 s window and 2 m is comfortable warmth. That
   phase lasts ~30 minutes against the flames' 6–12, so most of the fire's life is a gentle gradient.
6. **The fire model's own uncertainty (E, χ_r, Q̇) moves the window by about ±0.5 m.** D28 shouldn't tune its feel
   to a decimal until step 6 measures Q̇ and the ember temperature (Q1).

## 8. What the model doesn't capture

- **The fire:** no ramp-up (a step at the peak); no flame flicker or tilt from wind; no attenuation by smoke or air
  (minor at 1–3 m). The flame is a cylinder of uniform E. The ember crate keeps its 0.6 m shape; a collapsed pile
  would be lower and smaller, so the ember fluxes are high. The 920 °C case exceeds the ember release (§1).
- **No convective plume heating.** That is right for a body beside an open fire in still air (DPH-S4), wrong
  downwind.
- **The skin:** 1-D (no lateral conduction or curvature); no vasodilation, sweating or pain adaptation (the
  threshold drifts 44.9 → 43.8 °C in long exposures, *Adaptation of thermal pain*, 1962). So times over ~60 s at
  < 2 kW/m² are least reliable: real skin defends itself, and "never" is likelier than shown.
- **Clothing:** the fabric is opaque (thin cotton transmits some infrared, which would make clothed times shorter).
  There is no moisture and no ignition or char of the fabric, and the gap has no natural convection.
- **The core:** the T5 lump has no metabolism, no sweating, no clothing effect on what it absorbs, and no
  distribution of heat between core and shell.
- **Pain at the hottest height** is the right event for "it hurts". A meter that averages the body would be slower.

## 9. Provenance gaps (could not verify)

- **χ_r = 0.3 for wood.** Only the cross-fuel range 0.15–0.60 was verified.
- **The Q̇ and duration chain** from tile spec §5.1 (all *from memory*).
- **Char ε = 0.9.**
- **Fabric α = ε = 0.9 and k_air** (*from memory*).
- **The 6.4 mm ASTM spacer** (*from memory*).
- **The body's h = 10 W/m²·K, 1.9 m², 0.5 m² projected and ε = 0.95** (the spec's, *from memory*).
- **Buettner as the 1951 paper's author** (the values were verified, the attribution is from memory).
- **The two API 521 time points** (secondary blog, not the standard).
- **The Torvi & Dale values** were verified only through Jasiński (2003), not the original paper.

## Determinism

`run.py` computes all results and validations twice in one process and asserts that the SHA-256 of the two JSON
payloads match. **Two runs, bit-identical:** `5b91a983…e76` (full hash in `results/results.json`).
