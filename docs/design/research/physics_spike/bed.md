# Physics spike: the porous-bed crate fire (Q1, Q2, Q4)

Code: `spikes/physics/bed/` (`model.py`, `sim.py`, `run.py`, `analyze.py`, `closed_forms.py`; raw results in
`results/`). Throwaway; never imported by `src/`. The criteria are `preregistration.md`'s, unchanged.

**Headline.**
- **With cited constants, the tile spec's pilot does not light the crate.** A 2 kW, 600 s torch lights the 0.031 m²
  of slat faces under its disc. They burn out by about 1,040 s with 99.4% of the wood unburnt, at every grid and
  every range end. **Q1 and Q2 miss.**
- **The fully involved bed (the premise of spec §5.3) sustains flaming (1a).**
- **Its embers glow only if char oxidation has no kinetics.** With a cited surface rate, the char is born at
  T_p = 380 °C, below its 590–676 °C self-heating threshold, and goes out with 25% of the fuel left. With spec 6d's
  diffusion limit, the embers glow at a mean of 740–940 °C and burn out in 900–1,200 s.
- **The ledger closes to 2e-14,** and runs are bit-identical.

## 1. The model

- **Grid:** the 0.6 m crate as n³ cells (n = 3 / 6 / 12), full 3-D (the pilot is off-centre). The envelope is the
  five air-facing faces (1.8 m²); the floor face is adiabatic, which favours sustain.
- **Fuel:** φ = 0.25 and σ = 25 m²/m³, so 32.4 kg over 5.4 m², 6 kg per m² of surface. Each cell holds four parts by
  area:
  - **Ui, unburnt slats:** a 10-node half-slat conduction profile; node 0 is 6b's 1 mm skin.
  - **Up, outward faces under the pilot disc:** area φ × disc overlap, by 1 mm metric sampling. Pilot on the front,
    6a loss to 20 °C.
  - **Iw, ignited with wood:** a 1 mm skin pinned at T_p, with the excess gasifying at **m'' = q''_net/L_g** (6c).
    It flames while m'' ≥ m''_crit; a piloted ignition attaches a flame; char forms at χ.
  - **Ic, char:** a lumped temperature, oxidised (6d).
- **In-bed radiation (FPH-B1):** P1 for the incident radiation G.
  - Extinction a_v/4 (random elements), absorption ε·a_v/4, Marshak conditions on the envelope.
  - Surfaces absorb εG/4 and emit εσT⁴, so slat-to-slat exchange and envelope leakage come from one solve, with
    depth in metres.
- **Flame:** q''_f per m² of flaming surface.
  - The share (1 − χ_r) goes onto that surface; the share χ_r goes into P1, reaching neighbours.
  - Of the rest of the release, χ_r becomes `flame_radiative` and the remainder `plume_convective`.
- **Draught and O₂ (FPH-B1):** a buoyant column flow through Ergun's packed-bed resistance (plus a 1.5-head
  entrance/exit loss).
  - Gas–surface exchange is an exact exponential per cell, with h from Churchill–Bernstein or Churchill–Chu.
  - O₂ is consumed by flames (Huggett) and by char, and caps char oxidation.
  - Gas leaving a flaming cell is at T_p.
- **Char (6d, FPH-B2):** O₂ flux Y/[1/(ρk_s) + c_p/h], kinetics in series with mass transfer (Chilton–Colburn),
  k_s = 430·e^(−9000/T) m/s.
  - **Surface product: Arthur's CO/CO₂ = 2500·e^(−6240/T),** so mostly CO above about 800 K (9.2 vs 32.8 MJ/kg C).
    Chosen from the literature before any run.
  - The CO leaves; the other end, CO burning in-bed, was run.
- **6a:** P1 leakage, plus h_env on the outward share φ of envelope surfaces, plus the draught's exit enthalpy.
- **Ignition (FPH-B3):** the unburnt area ignites where a reconstructed skin field exceeds T_p. The field is the
  cell's skin plus a minmod gradient of the neighbours' surface temperatures, sampled at 6³ points. Only piloted: a
  flame in the cell or in a face neighbour.
- **Observables (§6.3):**
  - **t_glow:** ≥ 0.08 m² of envelope at ≥ 625 °C. The envelope-layer temperature is a sight-line integral (weight
    β·e^(−∫β), in metres) of the reconstructed surface temperature, sampled at 1 cm on each face. The P1 brightness
    temperature is reported too.
  - **t_crack:** ≥ 0.08 m² of envelope over cells ≥ 10% charred, the spec's cell rule, plus a 1 cm reconstructed
    variant.
  - **t_gone:** fuel below 1.62 kg. **t_ignite:** flaming ≥ 0.1 m².
- **Time:** 0.5 s physics steps, with substeps from the explicit stability bound.

**Disclosed corrections made during the spike.**
1. **Feedback delivery.** It first went all into P1, which spread a lit patch's own flame over the whole cell and
   starved it. It now follows 6c's wording ("deposits q''_f per m² of burning surface"). All-P1 is kept as a
   sensitivity. No constant changed.
2. **A J/g-for-J/kg units bug in the char heats** (1,000× low) was found by a closed-form check, not by the ledger.
   All runs were redone.
3. **A pilot-share leak (4.0% at T_p 300)** was found by the ledger and fixed.
4. **The "flame inside the bed" bound was dropped.** Returning χ_r of the whole release to the bed runs away (the
   bed flashes over in about 30 s), because χ_r·ΔH_c = 3.7 MJ/kg exceeds L_g = 1.8 MJ/kg. Any law returning more
   than **L_g/(χ_r·ΔH_c) = 48%** of the flame's radiation to the fuel is unstable.

## 2. Constants

V = verified on a page read in this spike; S = secondhand; M = memory, unverified; E = tile-spec content value.
| Constant | Value (ends run) | Source | Status |
|---|---|---|---|
| φ, b, σ, ρ_wood | 0.25, 20 mm, 25 m²/m³, 600 kg/m³ | tile spec §1.1, T15 | E |
| Pilot | 2 kW over r = 0.2 m (15.9 kW/m²), D = 600 s | tile spec §3.2 ("of order 2 kW", memory) | E/M |
| c_wood | 1,700 J/kgK (1,236; 2,630) | Wood Handbook FPL-GTR-190 Eq. 4-16a, at 293 / 413 / 653 K | V |
| k_wood | 0.12 W/mK (0.106; 0.15) | FPL-GTR-190 ch. 4 (0.106–0.116 oven-dry); 0.15 tile spec | V / M |
| T_p | 380 °C (300; 364) | Babrauskas, "Ignition of Wood" slides: 300–310 °C low flux, 349–364 °C flaming softwoods; 380 tile spec | V range / M |
| L_g | 1.8 MJ/kg | Tewarson, SFPE Handbook (Douglas fir 1.81); not found online | **M** |
| χ (char yield) | 0.25 (0.20; 0.30) | Baker 1983, FPL: ~25% | V / M range |
| ΔH_c,eff volatiles | 12.4 MJ/kg | tile spec / world_model §11; not found | **M** |
| q''_f | 25 kW/m² (15; 35) | Spearpoint & Quintiere; Tewarson & Pion 23.8 (snippets) | **S** |
| m''_crit | 3.7 g/m²s (2.5; 3.93) | Emberley et al. 2017, FSJ 91:327 (PDF read); 3.93 Arnórsson 2020 (snippet); 2.5 Bamford 1946 via review | V / S |
| χ_r | 0.30 (0.27; 0.33) | Johnsson et al., NIST TN 2327 | V |
| Huggett | 13.1 MJ/kg O₂ | Huggett 1980 via NIST SP 958 | V |
| ε | 0.9 (0.85; 0.95) | char 0.9, Chem. Eng. Trans. 94 (2022) | V / M range |
| h_env | 10 W/m²K (5) | tile spec; FPH: 5–10 on a 0.6 m face | M |
| c_char | 1,260 J/kgK | Huang & Rein via Jayasuriya 2022 Table 2 | V |
| Char kinetics | k_s = 430·e^(−9000/T) m/s (end: none, diffusion-limited) | Mankame & Shotorban 2021 Eq. 23, citing Morvan & Dupuy 2004; ρY_O₂ surface form memory | V numbers / M form |
| CO/CO₂ | 2500·e^(−6240/T) (end: CO₂ only) | Arthur 1951, Trans. Faraday Soc. 47:164; exponent consistent with a Utah snippet; prefactor and range unverified | **S/M** |
| CO in-bed burning | off (end: on) | modelling end | — |
| ΔH: C→CO₂, C→CO, CO→CO₂ | 32.8, 9.20, 10.1 MJ/kg | NIST WebBook ΔfH | V |
| Char as pure carbon | — | char ~85–90% C; overstates char heat ~10% | M |
| Ergun 150, 1.75; Churchill–Bernstein | — | Ergun 1952; Churchill & Bernstein 1977 (via Wikipedia) | V form |
| Churchill–Chu; Sutherland μ, k | — | snippets; White via COMSOL docs | S / V |
| c_p air, Pr, minor loss K | 1,100, 0.70, 1.5 | memory | M |
| β = a_v/4; P1 + Marshak | — | Cauchy; Modest (not opened) | M |

## 3. Q1: does the bed sustain and glow?

**S, the pre-registered scenario** (2 kW, 600 s pilot; nominal constants):

| | 0.2 m | 0.1 m | 0.05 m |
|---|---|---|---|
| Slat faces under the disc reach T_p | 415.5 s | 415.5 s | 415.5 s |
| Peak flaming area | 0.031 m² | 0.031 m² | 0.031 m² |
| t_ignite (flaming ≥ 0.1 m²) | never | never | never |
| Flame-out, wood left | 1,042 s, 99.4% | 1,045 s, 99.4% | 1,024 s, 99.4% |
| t_crack / t_glow / t_gone | — / — / — | — / — / — | 564 s / — / — |

**1a MISS, 1b MISS, 1c MISS at every grid.** No band in D exists: a 1,800 s pilot (0.1 m) gives the same
0.031 m² and the same 99.4%. Every range end run on S at 0.1 m (T_p 300, q''_f 35, k 0.106, c 1,236, ε 0.95,
h_env 5, m''_crit 2.5, all-P1 feedback) also misses all three. T_p = 300 °C lights the faces at 98 s instead of
415 s, but they still do not light the bed.

**Why:** the pilot's 15.9 kW/m² is only 3.4 kW/m² above the 12.5 kW/m² a bare face loses at T_p (so 415 s, not the
spec's 60 s; the no-loss closed form gives 49 s). Once lit, the faces' flames heat only themselves. The 6c law
gives no route by which a flame heats *unburnt* fuel above T_p, apart from χ_r·q''_f through P1. Burning surfaces
are pinned at T_p, and gas leaving a flaming cell is at T_p. **The bed cannot spread fire to itself.**
- **The base-lit crib (B,** bottom 0.1 m flaming at t = 0) shows the same thing. It burns its lit layer only:
  flame-out 573 / 567 / 723 s with 83% of the wood left (1a MISS).
- **This is FPH-B3's missing spread law,** made concrete.

**F, fully involved at t = 0** (tile spec §5.3's premise), nominal, 0.05 m reference:

| | 0.2 m | 0.1 m | 0.05 m |
|---|---|---|---|
| Flame-out | 449 s | 575 s | 770 s |
| Wood left at flame-out (1a) | 0.6% PASS | 0.6% PASS | 0.6% PASS |
| Peak fuel-loss rate | 0.0605 kg/s | 0.0589 | 0.0583 (≈ 540 kW flaming) |
| t_crack | 38.0 s | 41.5 s | 45.5 s |
| Glow ≥ 0.08 m² at ≥ 625 °C (1b) | never: MISS | MISS | MISS |
| Fuel at the end (1c) | 25.4%: MISS | 25.4%: MISS | 25.4%: MISS |
| Ember peak / mean | 380 / 40 °C | 380 / 36 °C | 380 / 31 °C |

- **The char is born at T_p,** because 6c pins the burning surface at T_p, and 380 °C is far below the char's
  self-heating threshold. With the cited kinetics, oxidation gives 0.66 kW/m² at 380 °C. It balances the draught
  loss only above **590 °C (h = 15) to 676 °C (h = 25)** (`closed_forms.py`).
- **So the embers cool to ambient** and 8.2 kg of char is left (the run stops when nothing can change).
- **The ember peak equals T_p in every kinetic run.**

**F under each range end** (0.1 m; times in s):

| End | 1a | 1b (longest glow) | 1c (t_gone) | Ember peak / mean |
|---|---|---|---|---|
| nominal | PASS | MISS (0) | MISS | 380 / 36 |
| q''_f 15 / 35 | **MISS** (6.1% left) / PASS | MISS / MISS | MISS / MISS | 380 / 36–41 |
| T_p 300 / 364 | PASS / PASS | MISS / MISS | MISS / MISS | 300 / 38; 364 / 37 |
| χ 0.20 / 0.30 | PASS / PASS | MISS / MISS | MISS / MISS | 380 / 31–42 |
| ε 0.85 / 0.95; h_env 5 | PASS | MISS | MISS | 380 / 36–37 |
| m''_crit 2.5 / 3.93; χ_r 0.27 / 0.33 | PASS | MISS | MISS | 380 / 36 |
| k 0.106 / 0.15; c 1,236 / 2,630 | PASS | MISS | MISS | 380 / 31–41 |
| CO₂ only (with kinetics) | PASS | MISS | MISS | 380 / 36 |
| CO burns in the bed | PASS | MISS | MISS | 380 / 36 |
| feedback all into P1 | **MISS** (24% left) | MISS | MISS | 474 / 40 |
| **no kinetics** (Arthur products) | PASS | **PASS (811 s)** | **PASS (918.5)** | 913 / 738 |
| **no kinetics + CO₂ (spec 6d)** | PASS | **PASS (1,105 s)** | **PASS (1,202)** | 1,144 / 939 |

The glow and burn-out outcome is decided by one modelling choice: **whether char oxidation has kinetics**. Once
kinetics are present, the CO/CO₂ choice does not matter, because the char never reaches a temperature where the
product matters. Without kinetics, Arthur's CO lowers the embers by about 200 K and t_gone by 280 s relative to
CO₂, as FPH-B2 predicted.

## 4. Q2: convergence

The rule is applied exactly as pre-registered. tol = 15% (crack, glow) or 10% (gone) of the 0.05 m value.
p = log₂((t₀.₂ − t₀.₁)/(t₀.₁ − t₀.₀₅)). The Richardson e₀.₁ is t₀.₁ − [t₀.₀₅ − (t₀.₁ − t₀.₀₅)/(2^p − 1)].

| Scenario, time | 0.2 / 0.1 / 0.05 | e₀.₁ (tol) | 2a | p | Richardson e₀.₁ | 2b |
|---|---|---|---|---|---|---|
| S: t_crack, t_glow, t_gone | —, 564 / —, — | — | **MISS** | — | — | **MISS** |
| F nominal: t_crack | 38.0 / 41.5 / 45.5 | −4.0 (6.8) | PASS | −0.19 | +28 | **MISS** |
| F nominal: t_glow, t_gone | none on any grid | — | **MISS** | — | — | **MISS** |
| F no kinetics: t_glow | 395.0 / 408.0 / 399.0 | +9.0 (59.9) | PASS | sign change | — | **MISS** |
| F no kinetics: t_gone | 908.0 / 918.5 / 904.0 | +14.5 (90.4) | PASS | sign change | — | **MISS** |
| F spec 6d: t_glow | 388.5 / 398.0 / 385.5 | +12.5 (57.8) | PASS | sign change | — | **MISS** |
| F spec 6d: t_gone | 1,196.5 / 1,202.0 / 1,207.0 | −5.0 (120.7) | PASS | 0.14 | −55 | **MISS** |

- **2a passes wherever the times exist; 2b misses everywhere.** The errors are small (1–3%) but not in the
  asymptotic range. They change sign, or p < 0.5, so a Richardson estimate is meaningless (−55 s against a measured
  −5 s).
- **Two causes are visible:**
  - **The 0.5 s step and threshold crossings quantise the times** at the size of the differences (DPH-S5's noise
    floor).
  - **The envelope's radiative boundary layer is unresolved.** Its P1 diffusion length is 1/√(3βκ) ≈ 0.10 m, one
    coarse cell at most. So the *flaming duration* does not converge: 449 → 575 → 770 s, with growing differences.
    t_gone converges anyway only because char burn-out dominates it.
- **The reconstructed crack area and the P1 brightness glow behave the same way.**

## 5. Q4: the ledger

- **4a PASS.** |in − Δstored − out| ≤ 1.9e-14 of cumulative release at every physics step of all 45 final runs.
  The lines are tile spec §5.4's: sources, combustion (flaming, char), plume_convective, flame_radiative,
  open_air_loss (radiation, convection, the pilot face's 6a, the draught exit), removed_with_mass, bodies, Δcells,
  Δskins. **Closure is exact by construction, so 4a alone proves little.**
  - It found one real leak during the spike, and that leak was fixed. The pilot's share on lit slats was booked but
    not deposited once they burnt to char: 4.0% at T_p 300, 0.62% at h_env 5.
  - It missed a 1,000× units error in the char heat, because the error was booked consistently.
- **4b is a partial MISS.**

| Line deleted | S (0.05 m) | F spec 6d (0.05 m) |
|---|---|---|
| sources | RED (100%) | green (0, none) |
| combustion_flaming | RED (59%) | RED (100%) |
| combustion_char | green (0.005%) | RED (46%) |
| plume_convective | RED (4.6%) | RED (57%) |
| flame_radiative | RED (13.5%) | RED (24%) |
| open_air_rad | RED (11.7%) | RED (31%) |
| open_air_conv | RED (3.0%) | green (0.74%) |
| open_air_pilotface | RED (14.8%) | green (0, none) |
| open_air_draught | RED (42%) | RED (20%) |
| removed_with_mass | RED (10.8%) | RED (14%) |
| bodies | green (identically 0) | green (identically 0) |
| Δcells | RED (57%) | RED (3.1%) |
| Δskins | RED (96%) | green (0.59%) |

- **Every line except `bodies` goes red in at least one scenario.** `bodies` cannot go red here: this spike has no
  body (Q5's spike owns it).
- **No single scenario turns every line red.** A global tolerance of 1% of cumulative release cannot see a line
  that carries less than 1% (Δskins 0.6% and envelope convection 0.7% in F).

**Determinism: PASS.** F_nom_01 run twice gives the identical SHA-256 over the per-step G, slab, char-mass and char-T
arrays (bcfc8eab…). Thread-count invariance is Q3's.

**Runtime.** 45 final runs took 127 min wall and 12 min CPU. The machine's 8 cores ran at load 61–152
(`os.getloadavg()` per run is in each JSON), so wall ≈ 10 × CPU. Fully involved, CPU / wall: 0.05 m 40 s / 596 s;
0.1 m 17 s / 211 s; 0.2 m 11 s / 109 s.

## 6. What the model does not capture

- **Flame-gas convection to unburnt fuel** (upward and concurrent spread). Gas leaving flames is held at T_p for want
  of a cited flame-gas temperature. This is the omission most likely to change S and B: real cribs lit at the base
  burn through.
- **A char-layer surface hotter than T_p during flaming.** 6c's single surface temperature makes the embers start
  at 380 °C, and that alone decides 1b and 1c under kinetics.
- **The rest:**
  - O₂ reaching envelope char by diffusion, without the draught.
  - The plume's extra draught above the bed.
  - Slat orientation (β = a_v/4 is isotropic, FPH-S3).
  - Bed collapse and changing char area (area held until burnt).
  - Ash, moisture, and the floor's heat sink (the bottom is adiabatic).
  - Autoignition.
  - Ventilation limits on flaming (O₂ used, never limiting).
  - P1 accuracy in the optically thin, burnt-out cells.
- **Grid coverage.** Q2 used the nominal and two no-kinetics sets; the range ends ran at 0.1 m only.

## 7. What step 6's design note should take from this

1. **The exit fails on 1a now, before glow is even reached.** Under the pre-registered failure path (T13) this goes
   to the owner before step 6 is designed. Neither the 2 kW torch nor a lit base layer spreads fire through a bed
   whose only flame law is 6c's q''_f on burning surfaces.
   - **Step 6 needs a cited spread law** (FPH-B3), or a flame-to-unburnt-fuel heat path: a flame-gas temperature,
     or a radiative return to the bed.
   - **That return is bounded.** A share above L_g/(χ_r·ΔH_c) ≈ 48% of the flame's radiation is unstable.
2. **The glow verdict hangs on char kinetics, not on any constant in §5.1.**
   - With a cited surface rate (Morvan & Dupuy form): no glow, 25% of the fuel left.
   - With §5.2's diffusion-limited 6d: glow at 740–940 °C and t_gone ≈ 900–1,200 s.
   - The note must cite a char surface temperature at the end of flaming (or a two-temperature char model). That
     temperature decides whether kinetics ever matter. It may not pick kinetics on/off by outcome.
3. **The ledger interface works,** but 4b needs per-line tests (DPH-S2's independent deposit test, or a closed form
   per line), not only global closure. Units belong in closed-form tests: the 1,000× error passed 4a.
4. **Convergence:** add a 2b check, as FPH-S5 asked. Resolve the envelope's radiative boundary layer (about 0.1 m)
   with a sub-cell envelope model sized in metres, or the flaming duration will not converge. Expect time
   quantisation at the 0.5 s step to dominate small errors.
5. **Constants that matter and are unverified:** L_g (M), ΔH_c,eff (M), q''_f (S only), Arthur's prefactor (S/M),
   and the kinetics' functional form (M). T_p = 380 °C sits above the verified softwood range (349–364 °C).
