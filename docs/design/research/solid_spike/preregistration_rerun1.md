# Solid spike, rerun 1 of 2: pre-registration (2026-11-20, committed before any code changes)

This rerun follows the owner's ruling of 2026-11-20 (option A1, with the cutoff change approved) on the first run
(`preregistration.md`, 65ee7d6; `results.md`, 9575a44). The first run's governing outcome was 12, with 7, 9 and 10
also triggered. This is **rerun 1 of the two** that `fire_model.md` §10.2's time-box allows 6.1; an overrun triggers
its fallback exit (owner ruling 3).

**This rerun is informed by the first run's results.** So only the numerics may change (§1), each fix with its cited
basis. **No bound moves.** No criterion or threshold changes. The data, the bands, the fit/grade split, the fitter and
the flame flux q''_fl stay as registered (§3).

Tags as before: **V** primary source read for this document (location given); **M** memory; **D** derived here.

## 0. Predictions, stated first

1. **P1 reverse misses on t_ig at 25 kW/m², whatever the numerics do.** The forward fit put m''_flash on its floor
   (0.972 g/m²s) and still flashed at 151.5 s, against DBI's 97–109 s. t_ig is the flash time: the first Q'' ≥ 24
   kW/m², reached once m'' ≥ m''_flash ≥ 24 ÷ ΔH_c,eff. So ignition is decided before any flame exists, and no flame
   parameter can bring it earlier. §1's fixes leave PMMA's heating before flash almost unchanged: A doesn't touch
   PMMA, B passed for PMMA at 50 and 65 in the first run, and C delays it if anything.
2. **An open question for the owner, not tested here.** Verification against FDS on the gasification inputs passed
   (V1–V3). The solid therefore heats PMMA as FDS does with this set, and FDS also needs 162 s to reach 1 g/m²s at
   25 kW/m². The late ignition likely comes from one of two places:
   - the transfer of NIST-StMU's parameters from N₂ gasification to cone ignition in air (oxidation at the surface,
     the heater's spectrum against κ, the epoxy counted as PMMA);
   - the ignition criterion: a flash at m''_flash against MaCFP's first Q'' ≥ 24.

   P0 has no 25 kW/m² mass data to separate these.
3. **Outcome 1 is out of reach,** and no change in this rerun is meant to reach it. What the rerun can still decide:
   - whether pine's node dependence (N2) and N7 are fixed;
   - with the numerics sound, whether P2, S1 and the fits at bounds still fail. If they do, the failures belong to
     the model and its fixed sets, not to the discretisation.

## 1. What changes: the numerics

**A. Pine is opaque, by FDS's own rule** (fixes N7's κ row; the fix proposed for N2).
- **The rule:** FDS 6.11.1 turns on in-depth radiation for a wall only if one of its materials has κ < 4.9×10⁴ m⁻¹:
  `IF (MATERIAL(ONE_D%MATL_INDEX(NN))%KAPPA_S<4.9E4_EB) ONE_D%INTERNAL_RADIATION = .TRUE.` (V, `init.f90` line
  4265). Otherwise the wall absorbs and emits at its face temperature (`wall.f90` lines 2873–2876, 2914 and 2922).
  `read.f90` lines 9366–9371 refuse inputs inconsistent with the rule.
- **How I checked it:** I fetched `init.f90`, `wall.f90` and `read.f90` from `firemodels/fds` at tag FDS-6.11.1 (tag
  object `c6c06da5`, the one `spec.py` cites for the version we run), grepped every use of `INTERNAL_RADIATION`, and
  read the lines above. The flag is set nowhere else. Its default is false (`type.f90` line 259).
- **Pine:** every component of `Wood_UMD_FSRI-DM.json` has κ = 5×10⁴, so FDS would treat pine as opaque. The first
  pre-registration's §10.7 routed it through the two-flux model, a departure from FDS. That is where results §6 and
  D6 place N2's miss: a spurious black-node conductivity and emission at the node centre (a diagnosis, unverified).
- **In this rerun:** the rule is applied per part, as FDS applies it per wall. Pine, and pine on Kaowool (N9; Kaowool
  has FDS's default κ, 5×10⁴), use the kernel's existing surface-absorption mode (N7's reference). PMMA on Superwool
  keeps the two-flux model (PMMA's κ is 2,620), so V's PMMA path is unchanged by A.
- **A side effect:** the pine JSON's `Units` block gives absorption in m²/kg, while its field says 1/m (V). Either
  reading is ≥ 4.9×10⁴, so A makes the ambiguity immaterial.
- **N7's κ = 10⁹ row** runs as registered. It now passes through the dispatch rule, so it tests the rule, not the
  two-flux limit; this is disclosed. Also reported, ungraded: a two-flux run at κ = 4.8×10⁴ against surface
  absorption at 1, 2, 4 and 8 times the nodes (D6's gap, measured).

**B. If A isn't enough: the node count from a convergence probe that sees no data.**
- **The node count:** FDS's rule × r, with r set per material.
- **The probe:** before any fit, it runs the fit fluxes only (PMMA 25 and 65; pine 30 and 60), every free parameter at
  the midpoint of its registered bound, and r = 1, 2, 4, 8, 16, 32. It computes the fit features and the class, and
  compares them with no band.
- **r\*:** the smallest r ≤ 8 such that, at every probe flux, the class (ignited, flashes, extinctions) holds and
  every fit feature changes by no more than V's tolerances (3 s on times, 2.5% on rates and masses) from r to 2r *and*
  from 2r to 4r. The observed order, p = log₂(|f_r − f_2r| ÷ |f_2r − f_4r|), is reported per feature.
- **No r\* ≤ 8:** the numerics have failed for that material.
- **If A alone passes at r = 1, r\* = 1.** V stays at FDS's own layout (r = 1), as registered: it verifies like
  with like.

**C. The kinetics cutoff, raised to where the source's TGA shows conversion** (owner-approved 2026-11-20; fixes N7's
ambient-rate row).
- **The problem:** at the registered 10⁻⁹ s⁻¹, T_cut lies below 20 °C for PMMA reaction 1 and pine reactions 1 and 5
  (results D7).
- **The rule:** T_cut,i = max(T at 10⁻⁹ s⁻¹, T_on,i). T_on,i is the temperature at which reaction i alone, starting
  at 293.15 K and heated at its source's slowest calibration rate, reaches 10⁻³ conversion. The rates come from the
  pinned JSONs' `Calibration` blocks (V): NIST-StMU's kinetics were fitted to TGA at 10 K/min, DM's to TGA at 3, 10
  and 30 K/min, so 3 K/min.
- **Values** (D: an estimate from a scratch integration; the code recomputes them, and a difference over 1 K is
  disclosed):

| Reaction | PMMA 1 | PMMA 2 | Pine 1 | Pine 2 | Pine 3 | Pine 4 | Pine 5 |
|---|---|---|---|---|---|---|---|
| T_cut, registered (K) | 252 | 426 | 279 | 370 | 429 | 301 | 163 |
| T_on, rerun (K) | 349 | 532 | 372 | 459 | 517 | 425 | 311 |
| Rate at T_on (s⁻¹) | 1.3×10⁻⁵ | 1.3×10⁻⁵ | 3.6×10⁻⁶ | 4.0×10⁻⁶ | 4.1×10⁻⁶ | 2.5×10⁻⁶ | 3.6×10⁻⁶ |

- **Why it's not a fit:**
  - Its inputs are the published A and E and the source's own heating rate.
  - Its one constant, 10⁻³ conversion, is `[engineering]` and fixed here, before any run.
  - It sees no cone or gasification data and enters no objective.
  - Its basis is the source's domain: below the temperature where the TGA that set the kinetics records conversion,
    the extrapolated rate has no support.
- **What it costs:**
  - The step at the cutoff grows from 10⁻⁹ to at most 1.3×10⁻⁵ s⁻¹, and N1 tests it.
  - It changes PMMA's kinetics before flash, so V and P0 are regraded.
  - If V misses, C has failed. This rerun allows no further fix, so the numerics have failed.

## 2. Dropped: the flame-flux change

The ruling's first plan, the one this rerun replaces, would have swapped the constant q''_fl for a cited flame flux
that depends on burning rate. That change is dropped, for two reasons.

- **No primary source I read in full gives one at cone scale.**
  - **Leventon 2016,** UMD PhD, hdl 1903/18203 (V: §2.4–2.5 and ch. 3–4; SHA-256 `74f5f350…`). The flame is a
    vertical wall flame. Inside it the flux is constant: 40 kW/m² below 5 cm and 34 above (eq. 3), as
    h_flame(T_fl − T_surf) with h_flame = 0.0193 kW/m²K and T_fl = 2,363 K (eqs. 22–24). Burning rate sets only the
    flame height (eq. 11), so the abstract's "a function of burning rate alone" describes the flux's spatial
    profile. A 10 cm horizontal sample sits wholly under its flame, where the flux is constant.
  - **Tilles 2017,** UMD MS, hdl 1903/20029 (V: ch. 3–4, Table 4.4). Cone, centre and side gauges: centre 6.9 +
    27.1χ_r kW/m², side 37.3. No burning-rate term.
  - **McCoy 2021,** UMD PhD, hdl 1903/28335 (V: §3.5.3 and 3.6.1–3.6.2, Tables 7–9, pp. 52–67; SHA-256
    `4e439fea…`). The group's cone model for ThermaKin2Ds. Centre: 9.5 kW/m² + 3.7×10⁻³(2150 − T_s); side: 20.0×10⁻³(2150 −
    T_s); the centre is 29.2% of the area. McCoy assumes the flux doesn't depend on burning rate: the flame
    structure is "unchanged from low to higher irradiation", and blowing is neglected (p. 61).
- **The only fallback, a composite, breaks the registered range by construction.** Nordtest NT TR 540 (Hostikka &
  Axelsson 2003; V, all 41 pages; SHA-256 `586b46e6…`) tabulates CFD radiative flame flux against heat release rate
  per area, 6.5–14.5 kW/m² (Table 3).
  - It is methane, radiative only and unvalidated ("the validation of the heat flux predictions was not made", p. 5).
  - Adding McCoy's area-weighted convection (15.24 W/m²K to 2,150 K) gives a cold-gauge reading of 34.8–42.8 kW/m²
    (D), above the registered 30. Outcome 12 would trigger whatever the run showed.
- **The outcome:** q''_fl stays the constant fitted parameter, with its registered bounds of [15, 30] kW/m².

**The recorded gaps:**
- Not read: "Empirical model of flame heat feedback for simulation of cone calorimetry", Fire Saf. J. 2019
  (ScienceDirect S0379711218303035), which returned 403. A search summary credits it to McCoy, Tilles and
  Stoliarov; that credit is unverified.
- Also not read: Leventon, Korver & Stoliarov, Combust. Flame 179 (2017) 338–353; Rhodes & Quintiere 1996 (known only
  via Tilles); Hermouet et al. 2021 (paywalled).
- The sources disagree. McKinnon's cardboard flux rises from 17.2 to 29.9 kW/m² between 20 and 60 kW/m² of heater
  flux (V via L1 §2.3), while McCoy's thermoplastics don't change.
- McCoy's measured PMMA side flux (33.6 kW/m²) lies above the registered q''_fl range. That bears on outcome 12's
  bound question, which stays with the owner.

## 3. What doesn't change

- **The data:** MaCFP `matl-db` at `9986be8d285c70b51d59262468199a3e63e41fe0`; FDS 6.11.1 and its runs; the
  exclusions and areas.
- **Stage 0:** `bands.json` (03f7cc0), §2.1's features, §2.2's bands, ΔH_c,eff and m''_ext.
- **Every criterion and threshold:** V1–V3, P0, P1, P2, S1, S2 and N1–N9, with V's tolerances, the N tolerances and
  S1's 1.1. N2's second halving (§4) adds a condition and loosens none.
- **The fit/grade split:** PMMA 25 → 50, 65 and 65 → 25; pine 30, 60 → 25, 50, 75.
- **The fitter:** the objective; `differential_evolution` with its defaults, `seed=0` and `polish=True`; seeds 1–4
  reported; the no-feature penalty; the flag rule; the count (2 against 4, 4 against 6).
- **Every bound:** q''_fl [15, 30] kW/m²; m''_flash [24/ΔH_c,eff, 2.5] g/m²s; k_c [0.04, 0.30] W/mK; char ε [0.677,
  0.833].
- **The model otherwise:**
  - D1's H_r(T) and D2–D5 (the ruling on D1, results §9.3, is pending and outside this rerun);
  - the 0.5 s step; h = 13 W/m²K before flash and convection off while flaming;
  - the heater nominal; flash and extinction tested on step-end m''; the hysteresis refusal;
  - geometry, backings and run lengths.

## 4. Gates, in order

| Gate | Runs | Must pass |
|---|---|---|
| 1. Numerics, no fit, no data | N7's five parts; V1–V3 at 0.01 and 0.5 s (C changes PMMA); N5 and N6 on them; §1 B's probe | **N7, all five;** V1–V3; an r\* ≤ 8 per material |
| 2. Graded numerics | seed-0 fits at r\* (seeds 1–4 reported); graded runs at r\*, 2r\* and 4r\* | **N2 converged:** class unchanged and every graded feature within V's tolerances from r\* to 2r\* and from 2r\* to 4r\*, order reported. Also N1, N3, N4, N5, N6, N8 |
| 3. Validation | as registered | P0, P1, P2, S1, S2, N9; bound flags |

- **A failure of N7 or V stops both materials.** A failure of the probe or of gate 2 stops that material.
- **A stopped material** gets no validation verdict. Its graded features are recorded but compared with no band.
- **Regrading:** all 17 first-run criteria are regraded, and the first pre-registration's §6 table classifies gate
  3's results.
- **Results** go to `results_rerun1.md` and `results_rerun1.json`; the first run's files stay untouched.

## 5. Outcomes (stated before results exist)

| # | Outcome | Meaning | Next |
|---|---|---|---|
| R1 | N7 or V fails, or neither material passes gates 1–2 | A–C can't fix the numerics | **6.1 waits;** no validation verdict. The owner chooses: rerun 2 on the numerics, or the fallback exit |
| R2 | One material passes gates 1–2, the other doesn't | The fix holds for one | That material alone is graded; the other is as R1 |
| R3 | Gates 1–2 pass, and every validation criterion passes with no bound flag | §6 outcome 1 | 6.1 builds as specified. **Predicted unreachable** (§0.1) |
| R4 | Gates 1–2 pass, and P1 misses only on reverse t_ig at 25 | The predicted miss, before any flame | The owner rules on §0.2's question; then rerun 2 (the last) or the fallback exit |
| R5 | Gates 1–2 pass, and other validation misses remain | Model or fixed-set shortfalls on sound numerics; §6 outcomes 2–6 name which | The owner's call: rerun 2 or the fallback exit. Reported against the first run, criterion by criterion |
| R6 | Gates 1–2 pass, and a fit sits at a bound | §6 outcome 12 again | The owner decides; no bound moves |
| R7 | Gates 1–2 pass, and N9 flips a class | §6 outcome 9 | That property is verified before 6.1 builds |

R4–R7 can coexist; the first one listed governs.

## 6. Cost, and what isn't pre-registered

- **Cost (D, from the first run's timings):** a pine fit took about 300 s at 67 nodes. At r\* = 8, five seeds take
  about 3.5 h, and the probe and graded N2 at up to 32× the nodes add about 30 min. At r\* = 1 the rerun costs about
  what the first run did.
- **Not pre-registered:**
  - what rerun 2 would change;
  - D1's ruling;
  - §0.2's question;
  - PMMA's ill-conditioned flat-peak time (the first run's PMMA N2 miss at 25 kW/m²), which B either clears or fails
    and which isn't redefined;
  - any fix found after a run. A deviation is labelled before or after a run, as in the first.
- **The sources' PDFs** (handles and SHA-256 above) go to `_durable/solid_spike/` before the run.
