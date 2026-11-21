# Solid spike: pre-registration (2026-11-20, committed before any spike code runs)

A throwaway prototype of `fire_solid.md` §4's 1D solid, verified against FDS and graded with the cone tests R0
(ignition) and R1 (burning). Code goes in `spikes/physics/solid/`, never imported by `src/`.

**No constant is tuned to pass, no criterion is loosened after the run, and none is reinterpreted after it.** Only
the fitter sets the free parameters, inside the bounds below, on fit data only.

Tags: **V** primary source read for this document; **M** memory; **D** derived here (FDS runs and data scripts in
`_durable/solid_spike/`, not committed).

## 0. The risks, stated first

1. **The published PMMA set misses the flame-free data.** FDS 6.11.1 on MaCFP's own inputs over-predicts NIST's
   50 kW/m² peak MLR by 7–15% (§9). A fitted flame flux q''_fl could absorb that; P0 separates the two.
2. **PMMA's graded peak is a back-face feature.** A 6 mm slab on insulation peaks when heat reaches its back, so
   fire_solid §4.5's own backing rule forbids an envelope across labs. PMMA is graded against one lab (DBI_Lund)
   and its three repeats, which is strict.
3. **One constant q''_fl may fail across fluxes** (fire_solid §4.5). The PMMA reverse fit tests it.

## 1. Questions

- **V:** does our solid reproduce FDS 6.11.1 on MaCFP's NIST-StMU-FSRI PMMA gasification inputs at 25 and 50 kW/m²,
  within fire_solid §4.6's tolerances, at a reference step and at the shipped 0.5 s?
- **P0:** on all 11 shipped gasification inputs, is our error against NIST's data no worse than FDS's?
- **P:** with MaCFP's published kinetics and thermal properties fixed and only §3's free parameters fitted, does the
  solid reproduce MaCFP's cone data at held-out fluxes?
  - **P1, black PMMA:** fit at 25 kW/m², grade at 50 and 65; then the reverse, fit at 65, grade at 25. Both must
    pass.
  - **P2, white pine, parallel grain:** fit at 30 and 60, grade at 25, 50 and 75.

## 2. Data, pinned

MaCFP `matl-db` at commit **`9986be8d285c70b51d59262468199a3e63e41fe0`** (2026-11-20), read with `gh api`. FDS
6.11.1 at `_tools/fds-6.11.1/bin/fds`, run under `env -i HOME="$PWD" PATH=/usr/bin:/bin OMP_NUM_THREADS=1`.

| Use | Files | Excluded |
|---|---|---|
| V | `PMMA/Validation_Results/NIST-StMU-FSRI/FDS_Input_Files/`: `…_25R1.fds` at `T_END=1500`; `…_R3.fds` as shipped | — |
| P0 | all 11 inputs there (25R1–R3 at `T_END=1500`; R3–R5, T1–T5 as shipped), each against its repeat in `PMMA/Validation_Data/NIST_Gasification_Apparatus/` | — |
| P1, per lab | `PMMA/Calibration_Data/DBI_Lund/DBI_Lund_Cone_{25,50,65}kW_{1,2,3}.csv`, the square samples | round samples (25 kW_4–6: another holder and area) |
| P1, t_ig envelope | every PMMA cone file at 25, 50, 65 | per test, MaCFP-2's outlier rule, ΔH_c = 23.5 ± 2.5 kJ/g (V, `Calibration_Data/README.md`). It removes HKPolyU, LCPP, ULSTER and UQ, UClan at 25 and one Edinburgh test |
| P2 | `Wood/Calibration_Data/*/*_Wood_Cone_*`, not perpendicular | MaCFP-4's own (V, `Scripts/MaCFP-4/Cone_analysis.py`): UMET; IMT 25 kW R2, R5; BUWfd 50 kW R1. Also FZJ 75 kW R1 for mass features (no mass), and BUWfd entirely: MaCFP's script has no area for it, and L1 §1.3 flagged its 2–4 s ignitions before this document |

- **Grain orientation is MaCFP-4's:** a file not named perpendicular is parallel. IMT's README calls its orientation
  "uncertain but consistent", so results name IMT separately.
- **Areas:** README values (MaCFP-4's `get_cone_area` for wood; PMMA: Edinburgh 0.095², TIFP 0.0084, UClan 0.0088,
  UDRI and UQ 0.00884, others 0.01).
- **Pine labs.** Fit: Aalto, FZJ, TUBS, UDRI at 30; Aalto, FZJ, UDRI, UQ at 60. Graded: FSRI, IMT at 25; FPL,
  FSRI, IMT at 50; FSRI, FZJ, IMT at 75. Aalto's 45 is a cross-check.

### 2.1 Features (data and model alike)

- **t_ig:** the first sample with Q'' ≥ 24 kW/m² (V, MaCFP-4's `df[df['HRR (kW/m2)'] >= 24].index[0]`). The
  model's Q'' is m''·ΔH_c,eff × flaming area ÷ sample area.
- **m''_10:** MaCFP-4's five-point central difference of mass per area, averaged over ±5 s. **m''_60:**
  (m(t − 30 s) − m(t + 30 s)) ÷ (60 s · A).
- **PMMA:** peak m''_10 over [t_ig, last Q'' ≥ 24]; its time; mass lost per area from t_ig to then.
- **Pine:** first peak, the largest m''_10 in [t_ig, t_ig + 200 s]; plateau, the mean m''_60 over
  [t_ig + 250, t_ig + 450 s]. The window ends at the first m''_60 < 2.7 g/m²s after the first peak.
- **ΔH_c,eff:** ∫Q'' dt ÷ mass lost over the window (PMMA: while flaming), averaged over fit tests.
- **m''_ext (pine):** the median m''_60 at the README flame-out times of fit-flux tests (Aalto and UQ report them).
  With none, 1.17 g/m²s, leak named (fire_solid §4.4).
- **Artefact rule,** written after seeing FPL 50 kW/m² R4's 71.6 g/m²s first peak (its lab's median is 13.5): a
  test whose peak exceeds twice its lab's median at that flux is excluded and listed.

### 2.2 Bands

- **Envelope:** [min, max] of lab means per feature and flux, each end widened by §5's V tolerance (3 s on times,
  2.5% on rates and masses), since no band can be finer than verification resolves.
- **Per-lab band:** [min, max] of that lab's tests, widened the same way.
- **Stage 0:** a data-only script computes every band and m''_ext by these rules. Its `bands.json` is committed and
  signed before any model code exists, and must reproduce these t_ig envelopes (D, lab means, s):

| | 25 | 30 (fit) | 50 | 60 (fit) | 65 | 75 |
|---|---|---|---|---|---|---|
| PMMA | 98.7–123.5 (6 labs) | — | DBI only, tests 24–27 | — | 12.0–25.9 (7 labs) | — |
| Pine | 70.3–118.3 | 31.0–51.7 | 13.7–23.3 | 8.8–20.0 | — | 3.7–7.7 |

  A difference is a stage-0 bug, disclosed.

## 3. The model under test

As fire_solid §4: delta-form backward Euler with one εσT⁴ linearisation; FDS's n-step Arrhenius with T_cut at
10⁻⁹ s⁻¹; the exact frozen-T update; regression at 1% of node thickness; flash at m''_flash and extinction at
m''_ext, refusing m''_ext ≥ m''_flash; convective loss off while flaming.

**In-depth absorption** is the two-flux model of FDS's Technical Reference Guide (`Solid_Chapter.tex`, "Radiation
Heat Transfer to Solids", tag FDS-6.11.1; V). The surface radiative term is zero, and the source is the divergence
of the forward and backward fluxes, with q''⁺(0) = q''_in + (1 − ε)q''⁻(0). The closures at layer interfaces and
the back face, and what FDS's `WALL TEMPERATURE` reports, are read from FDS-6.11.1's `wall.f90` and cited in the
code before it is written.

| | PMMA | White pine |
|---|---|---|
| **Fixed set** | `PMMA/Material_Properties/2023/MaCFP_PMMA_NIST-StMU.json`, from TGA, DSC, MCC and literature, no cone (V): two reactions plus 1% inert; k 0.20; c 2,130; ρ 1,177; ε 0.963; κ 2,620 m⁻¹ | `Wood/Material_Properties/Wood_UMD_FSRI-DM.json`: kinetics fitted to TGA only, the rest measured directly (V). CORIA is disqualified as cone-calibrated (V). **Fallback, named now:** `Wood_UCB-TDEP-1` |
| **Free (bounds)** | q''_fl [15, 30] kW/m² (L1 §6; cardboard 17.2–29.9, V via L1 §2.3); m''_flash [24/ΔH_c,eff, 2.5] g/m²s (upper M) | the same two; k_c [0.04, 0.30] W/mK (DM's LFA 0.037–0.046 at 673–873 K; UCB-CONST-1 up to 0.299; V7 11b); char ε [0.677, 0.833] (DM, V) |
| **Measured, not fitted** | ΔH_c,eff from DBI's fit tests (D: 24.7 at 25, 24.6 at 65 kJ/g) | ΔH_c,eff; m''_ext |
| **Geometry** | DBI's mean thickness per flux (6.08–6.25 mm, V) | 25.4 mm (MaCFP-4 nominal) |
| **Backing** | DBI's 2 × 13 mm Superwool SW Plus, ρ 64 (V); k from DBI's table, 0.034–0.041 W/mK at 25–70 °C (V), linear above (M); c 1,000 J/kgK (M); adiabatic beneath | adiabatic (no back-face feature is graded) |
| **Fit features** | 4: t_ig, peak, its time, mass lost | 6: t_ig, first peak, plateau, at 30 and 60 |

**The count:** 2 free parameters against 4 fit features (PMMA), 4 against 6 (pine). Fixing the kinetics answers
Physics S2's "about 10 against about 4". A fit that breaks the count doesn't run.

## 4. The fitter

- **Objective:** Σ ((model − band centre) ÷ band half-width)² over the fit features.
- **Method:** `scipy.optimize.differential_evolution`, defaults, `seed=0`, `polish=True`. **One graded run per
  material and direction** (three). Seeds 1–4 run too; their spread on graded features is reported, not graded.
- It never sees a graded flux. A value within 1% of a bound's width of that bound is a **flagged pass**, for the
  owner. q''_fl is flagged as fitted in every result.

## 5. Criteria (pass or miss, fixed now)

| # | Criterion | Pass when |
|---|---|---|
| V1 | FDS 25R1 at 1,500 s | peak m'' within 2.5%; times to m'' ≥ 1, ≥ 2.7 g/m²s and to half the peak within 3 s; front T at 300 s within 12 K; mass lost at 300 s within 2.5%. Peak time ungraded (within 1% over 797–984 s) |
| V2 | FDS R3 | V1's six, plus peak time within 8 s |
| V3 | Step | V1 and V2 pass at 0.01 s (the inputs' DT) **and** at 0.5 s |
| P0 | Gasification, 11 inputs | per feature and repeat (50: peak MLR, its time, time to 2.7 g/m²s, time to half the sample mass; back T: time to 100, 200, 300 °C where recorded): **A** inside the repeats' range widened by the V tolerance; **B** otherwise, if \|ours − data\| ≤ \|FDS − data\| + V tolerance; **C** otherwise. Pass: no C. A P1 pass leaning on a B is labelled "q''_fl may compensate a property-set error" |
| P1 | PMMA | forward: every DBI feature at 50 and 65 in its per-lab band, and t_ig at 65 in the envelope; reverse: the same at 25 |
| P2 | Pine | t_ig, first peak and plateau at 25, 50, 75 in the envelope |
| S1 | Pine sustains | in every graded run, min m'' over the data window ≥ 1.1·m''_ext |
| S2 | PMMA after flash | m''_10 never falls between flash and the data's peak time (fire_solid §4.4) |
| N1 | Step halving, every graded run | 0.5 and 0.25 s: same class, t_ig within max(0.5 s, 3%); 0.125 s: peak within 2.5% of 0.25 s |
| N2 | Node halving | same class; graded features within the V tolerances |
| N3 | Flashes | at most one per part, every run |
| N4 | The guard is live | with m''_ext above m''_flash, N1 or N3 goes red |
| N5 | Mass | Σ node mass + removed = initial to 10⁻⁹ relative, every step of every run |
| N6 | Energy ledger | every step, \|absorbed − Δstored − outputs\| ≤ 10⁻⁹ of cumulative absorbed; deleting any line turns it red |
| N7 | Closed forms (fire_solid §6 rows 1–4) | thick and thin t_ig, losses off, within 2%; erfc profile at 60 s within 1% of the surface rise; κ = 10⁹ m⁻¹ against surface absorption within 10⁻⁶; 200 steps at ambient change no bit; ambient rates exactly 0; an n = 0.5 node reaches exactly 0 |
| N8 | Determinism | a rerun gives a byte-identical `results.json` |
| N9 | Range ends | PMMA backing k held at 0.041 and as Kaowool PM's ramps (V, from the inputs), c 800 and 1,200; pine on 25.4 mm Kaowool PM. Reported; a class change is outcome 9 |

**17 criteria.** Also reported, ungraded: time to sustained flaming; the heater removed (no data: a prediction);
apparent L_g; the BUWfd and Aalto + FZJ-only variants; runtime.

## 6. What each outcome means (stated before results exist)

| # | Outcome | Meaning | For 6.1 and 6.2 |
|---|---|---|---|
| 1 | All pass | The solid is right; 2 (PMMA) or 4 (pine) cone constants reproduce held-out data | 6.1 builds as specified; 6.2 treats q''_fl as a fitted configuration constant |
| 2 | 1, with B features in P0 | The published set is off flame-free; q''_fl compensates | As 1, plus a Known gap with numbers; 6.2 doesn't reuse q''_fl outside cone geometry |
| 3 | P1 passes one direction only | A constant q''_fl fails across fluxes | 6.1's cone tests can't pass as specified; a cited q''_fl(q_ext) law, owner's ruling before 6.1; 6.2's flame feedback must depend on flux |
| 4 | P1 misses DBI's bands but lies in the all-lab envelope | Within between-lab scatter, not lab-specific | A miss; the owner decides whether per-lab is 6.1's bar |
| 5 | P1 passes, P2 misses | The char physics is short (k_c, char ε, no oxidation, density) | R1 pine to the owner; 6.2 can't design crib burning on this char; the char model (`char_oxidation.md`) first |
| 6 | P2 misses only on IMT | The orientation-uncertain lab drives it | Reported per lab; the owner rules on IMT |
| 7 | V misses at 0.01 s | A bug, or a model difference from FDS | P is not graded. Fixed, disclosed, all rerun; a surviving miss is a fire_solid §4 design question |
| 8 | V passes at 0.01 s, not at 0.5 s | The shipped step is too coarse | §4.3's fixed-substep fallback, to the owner; P graded at it; the cost goes to B5 |
| 9 | An N9 end flips a class | A band, not a margin | That property is verified before 6.1 builds |
| 10 | N1, N2 or N3 misses | Step, node or toggling dependence | The resolution rule is broken in the solid; 6.1 waits for the fix |
| 11 | N5, N6 or N8 misses | A bug | Fixed, all redone, disclosed; an owner item only if a class changes |
| 12 | m''_ext ≥ fitted m''_flash, or a fit at a bound | The hysteresis premise or a range fails | The owner decides; no bound moves |

## 7. What the spike is not

No flame objects, cells, crib, contact coupling or world limits; the cone tests are grid-free. **A lone surface going out when the heater is removed is expected** (L1 §2.3; fire_solid §8) and says
nothing about the crate. No char oxidation, moisture, perpendicular grain, 65 kW/m² or flame-path verification.

| Gap that biases the verdict | Toward |
|---|---|
| Adiabatic pine back (S1's window includes back-face heating) | a sustain pass |
| Bands widened by the V tolerance | a pass |
| Pine density fixed at the set's 360 kg/m³; the tests span about 325–455 (D) | unknown, per lab |
| No moisture | early t_ig |
| Constant-flux inputs; NIST's flux rises from 0.93 to 1.0 of nominal over 240 s (V, README) | P0 class B on early times |

## 8. Code and rules

- `spikes/physics/solid/`: kernels, cone harness, FDS driver, stage 0 and the fitter. Never imported by `src/`.
- **Kernels:** numpy, a hand-written Thomas solve, no BLAS; delta form; `np.where` for T_cut, never a gather;
  fixed-order reductions; no wall clock; no randomness but the fitter's seeds.
- **Committed beside the code:** `bands.json`, `results.json` (every criterion's numbers, fitted values, seed
  spread); here, `results.md` (one row per criterion, its §6 outcome).
- **Not committed:** FDS outputs and MaCFP data. A script regenerates them from the pinned commit and checks them
  against SHA-256s recorded in `results.json`.
- Deviations say whether they came before or after a run.

## 9. Reference values measured before code (D)

- FDS reproduces the fold's 25R1 (1,500 s) and R3 runs byte for byte. Both burn out to the 1% inert.
- Layout: 24 (25R1) or 23 (R3) PMMA cells of 0.27 mm, 53 Kaowool, 1 aluminium.
- **The back boundary is immaterial:** with `BACKING='INSULATED'` every V1 and V2 feature is unchanged; the aluminium
  back warms 2.2 K in 500 s. Ours is insulated.
- The shipped thickness counts the epoxy as PMMA (25R1: 6.59 mm against 6.26 measured). We run as shipped.

| P0's baseline | FDS as shipped | NIST data |
|---|---|---|
| 50: peak MLR, R3 / R4 / R5 (g/m²s) | 31.99 / 31.98 / 32.04 | 29.88 / 28.06 / 27.80 |
| 50: peak time (s) | 346 / 345.5 / 368 | 346 / 326 / 337 |
| 50: half the sample mass lost (s) | 250 / 244 / 262.5 | 226 / 223 / 239 |
| 50: half the peak reached (s) | 126 / 126 / 130 | 65 / 65 / 60 |
| 25 R1: back T at 100 / 200 / 300 °C (s) | 160.5 / 313.5 / 588 | 145 / 345 / 749 |
| 50 T3 / T4: back T at 100 °C (s) | 115.5 / 111.5 | 114 / 112 |

P0 should show B features: the property set's, if V passes.

## 10. Where fire_solid.md can't be followed as written

1. **Pine labs.** §4.5's "fitted on 30, 60 (Aalto, FZJ) … graded on 25, 50, 75 (FSRI)" and "held-out pine fluxes
   are FSRI's alone" are false at this commit: IMT has 25, 50, 75; FPL and BUWfd 50; FZJ 75; TUBS, UDRI, UQ 30 or
   60. All usable labs are fitted; the Aalto + FZJ fit is reported.
2. **§4.4's flame-out table** calls IMT parallel and uses IMT R2, which MaCFP-4 excludes. It stays a cross-check.
3. **PMMA's peak features are back-face features,** so §4.5's backing rule makes its grading per lab (§0).
4. **"PMMA at 50 has two labs":** ULSTER's ΔH_c is 31.7–33.2 kJ/g, outside MaCFP-2's rule; only DBI remains.
5. **Gasification at 25 kW/m²** has back temperatures only, and fire_solid set no tolerance; P0 defines one.
6. **"Several seeds"** against the brief's single run: seed 0 is graded, four more reported.
7. **The pine set's ε depends on heater flux and its κ is finite** (5×10⁴ m⁻¹), not opaque. Both are used as
   published: ε interpolated linearly in heater flux, κ through the two-flux path.
