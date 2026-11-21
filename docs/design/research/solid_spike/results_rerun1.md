# Solid spike, rerun 1 of 2: results (2026-11-20)

Pre-registration: `preregistration_rerun1.md` (de2290d), and `preregistration.md` (65ee7d6) for everything it leaves
unchanged. Bands: `stage0/bands.json` (03f7cc0). Numbers: `spikes/physics/solid/results_rerun1.json`; CPU and load:
`timings_rerun1.json`. Code: `rerun1.py` (the gates in order) plus the three fixes in `materials.py`, `kernel.py`,
`closed_form.py` and `spec.py`. The first run's `results.md`, `results.json` and `timings.json` are untouched.

## The verdict, first

**The numerics are now sound. The cone predictions still miss.** Gates 1 and 2 pass for both materials: N7 passes
five of five, V1–V3 pass, the probe finds r\* = 2 (PMMA) and r\* = 4 (pine), and N2 converges at r\*, 2r\* and 4r\*.
So both materials were graded. In gate 3, P0, P1, P2, S1 and S2 all miss, and every seed-0 fit sits on a bound.
N9 flips no class.

**The governing outcome is R5,** with R6 also triggered. The model or its fixed sets fall short, and the numerics
are sound. R4, the predicted miss, did not trigger on its own terms: the reverse t_ig at 25 kW/m² misses as §0.1
predicted (222 s against DBI's 97–109), but P1 forward also misses, so P1's miss isn't "only" that one.

**What the rerun settles.** With pine opaque by FDS's rule and its nodes converged, pine's first peak at 50 kW/m²
drops into the envelope, S1 passes at 50 and 75, and N9's flip is gone. But the plateau is now 31% below the data,
with q''_fl, k_c and char ε all on their upper bounds. PMMA moves by ≤ 1%, and every PMMA miss of the first run
remains.

| # | Verdict | The numbers (first run in brackets where it differs) |
|---|---|---|
| V1 | **pass** | 25R1: peak −1.8%; t(≥1) +1.5 s; t(≥2.7) +1.5 s; t(½ peak) −1.5 s; front T(300) +1.2 K; mass(300) −0.7% (−0.5%) at 0.01 s; −0.85% at 0.5 s |
| V2 | **pass** | R3: peak −1.5%; t(½ peak) −1.5 / −1.0 s; front T(300) +7.9 / +8.0 K; mass(300) −1.6%; peak time +5 s |
| V3 | **pass** | V1 and V2 at 0.01 and 0.5 s |
| P0 | **miss** | 8 A, 12 B, **1 C** (R5's peak time 377.5 s against FDS 368 and data 337), identical in class to the first run |
| P1 | **miss** | forward: peak 58.4 / 73.9 g/m²s against DBI's 42.0–49.4 / 52.6–57.5; peak time 218.5 / 172.5 s, early; t_ig at 50 is 20.5 s, outside DBI's 21–30 (first run: 21, in) and the envelope. Reverse: t_ig at 25 is 222 s (200.5) against 97–109; peak time 504.5 s against 379–406 |
| P2 | **miss** | 25: no ignition; 50: first peak 13.29 **in** (18.66 out), plateau 3.88 out (4.82), t_ig 7.0 out; 75: first peak 15.69 out, low (23.66, high), plateau 4.41 out (5.66), t_ig 3.5 in |
| S1 | **miss** | 25: no ignition; 50 and 75: **pass** (min m'' 1.98 and 3.31 against 1.29 needed; first run: both went out) |
| S2 | **miss** | forward 50 and 65: m''_10 falls by 1.81 and 1.45 g/m²s before DBI's peak time; reverse 25 passes |
| N1 | **pass** | t_ig moves ≤ 0.5 s between 0.5 and 0.25 s; the 0.125 s peak is within 0.93% of 0.25 s. Pine 25 is vacuous (no step ignites) |
| N2 | **pass** (miss) | at r\*, 2r\*, 4r\*: every graded feature within V's tolerances, class unchanged (table below) |
| N3 | **pass** | at most 1 flash per part in every graded, numerics and probe run |
| N4 | **pass** | m''_ext = 1.5·m''_flash: PMMA 3 and 4 flashes, pine 2 and 2 flashes (0.5 and 0.25 s); N3 red for both, N1's class red for PMMA |
| N5 | **pass** | worst 8.0×10⁻¹⁵ of the initial mass |
| N6 | **pass** | worst 3.0×10⁻¹⁴ of cumulative absorbed; deleting any line gives ≥ 6.6×10⁻⁶ |
| N7 | **pass** (2 of 5 missed) | all five parts pass; the κ row passes through the dispatch rule (disclosed in the pre-registration) |
| N8 | **pass** | `rerun1.py --check` in a fresh process (PYTHONHASHSEED 12345 against 0): `results_rerun1.json` byte-identical; the PMMA seed-0 fits rerun identical |
| N9 | **no flip** (flip) | pine on Kaowool PM keeps its class at 50 and 75; PMMA's four backing ends flip nothing |

**CPU (single-threaded):** 16 fits 7,949 s (four at once, load 1.9–6.9); N8's fit reruns 178 s; gate 1 alone 33 s;
the pipeline 178 s per pass, two passes. About 8,500 s. FDS was not rerun: gate 1 checks that its 11 runs hash to
`results.json`'s values.

## 1. Deviations, labelled

**RD1 (during the fits, before any graded run; no number affected). The rerun's fits overwrote the first run's fit
files.** `launch_fits_rerun1.sh` didn't set `SOLID_FIT_OUT`, so the 16 rerun fits wrote to `out/fit/`, the first run's
git-ignored fit directory, and replaced its 16 JSON files there. Its logs were untouched. That breaks the rule to keep
the first run's outputs intact. I found it when the launcher's N8 comparison failed.
- **The fix:** I moved the rerun's files to `out_rerun1/fit/`, which I identified by their `"numerics": "rerun1"` field.
  I rebuilt the first run's files from the committed `results.json` (`fits`) and `timings.json` (`fit:*`), which
  hold every field.
- **The check:** re-grading the first run in its own mode (`spec.NUMERICS = "run1"`) from the rebuilt files reproduces
  its P1 and P2 rows exactly.
- **The guard:** `fit.py` refuses a rerun fit aimed at `out/fit/` (run, and seen to refuse); the launcher exports
  `SOLID_FIT_OUT`.

**RD2 (before any run): the first run stays reproducible.** The fixes sit behind `spec.NUMERICS`, which defaults to
"rerun1", and `run.py` sets "run1". In run1 mode the modified code reproduces the first run's N7 values (two report
keys were added), and its P1 and P2 graded rows exactly. `grade.n4` and `grade.n9` were split per material, so a
stopped material could be left out; their output is unchanged.

**Readings and choices fixed in code before any run:**
- **R4 and R5.** R4 means "P1's only miss is the reverse t_ig at 25". R5 means any other validation miss in P0, P1,
  P2, S1 or S2.
- **Comparisons.** In the probe and in N2, a rate or mass is compared relative to the coarser run, as the first run's
  N2 did. A feature that is absent at every resolution passes.
- **V and P0 run at r = 1**, FDS's layout, so both compare like with like.
- **T_on** is computed from the pinned JSONs' A, E, n and `Calibration` rates: 10 K/min for NIST-StMU, and 3 K/min for
  DM (the slowest of 3, 10 and 30). Every value is within 0.5 K of the registered estimate, and none differs by more
  than 1 K. Trapezoid rule at 10⁻³ K.
- **Timings** go to `timings_rerun1.json`, committed beside the first run's `timings.json`.

**Vacuous rows, as the first run's code defines them (disclosed, not reinterpreted).** Pine at 25 kW/m² ignites at
no r and no step, so its N1 and N2 rows pass as "same class, no features". Pine's N4 goes red through N3 alone.

**Open:** the pre-registration's §6 asks for the sources' PDFs to go to `_durable/solid_spike/` before the run. They
are not there, and I did not fetch them. They back §2's dropped flame-flux change, not any number here.

## 2. Gate 1: numerics, no fit, no data

### N7, all five parts

The conduction closed forms are unchanged (thick +0.001%, thin −0.003%, erfc 0.10%). **κ = 10⁹ passes with error
0:** the part now goes through FDS's rule, so the row tests the dispatch, not the two-flux limit (§1 A). **Ambient
rates are exactly 0** for every reaction, and 200 ambient steps change no bit, even with both sets' kinetics on. The
n = 0.5 node depletes to exactly 0.

**§1 C's cutoffs, as the code computes them:**

| Reaction | PMMA 1 | PMMA 2 | Pine 1 | Pine 2 | Pine 3 | Pine 4 | Pine 5 |
|---|---|---|---|---|---|---|---|
| T_cut at 10⁻⁹ s⁻¹ (K) | 252.2 | 425.8 | 279.1 | 370.2 | 428.6 | 300.5 | 163.1 |
| T_on = T_cut, rerun (K) | 349.4 | 531.5 | 372.1 | 458.9 | 517.1 | 424.6 | 311.1 |
| Rate at T_cut (s⁻¹) | 1.27×10⁻⁵ | 1.25×10⁻⁵ | 3.57×10⁻⁶ | 3.98×10⁻⁶ | 4.08×10⁻⁶ | 2.45×10⁻⁶ | 3.60×10⁻⁶ |

**§1 A's dispatch:** pine, and pine on Kaowool PM, use surface absorption. PMMA on Superwool and the gasification
inputs use the two-flux model, because PMMA's κ is 2,620 m⁻¹.

**Reported, ungraded: D6's gap.** Two-flux at κ = 4.8×10⁴, against surface absorption on N7's slab, face T at 120 s:

| Nodes (× FDS's rule) | 1 | 2 | 4 | 8 |
|---|---|---|---|---|
| Face error, share of the rise | −2.95% | −1.52% | −0.79% | −0.42% |
| Largest node error | 2.79% | 1.59% | 0.97% | 0.64% |

The error halves with each halving of the nodes: a first-order discretisation error of black two-flux nodes, which
measures the first run's D6 diagnosis rather than assuming it.

### V1–V3 with fix C

C changes PMMA's kinetics below 349 K and 532 K. V moves by at most 0.18% (25R1's mass lost at 300 s) and keeps every
margin (V table above). The tightest margin is still V2's front T, +7.95 K of 12. N5 and N6 on the V runs: mass
8.0×10⁻¹⁵, energy 1.8×10⁻¹⁶, every ledger line needed. The H_r(T) check against FDS's `.out` holds to 0.03%.

### §1 B's probe

Fit fluxes, every free parameter at its bound's midpoint. The class is (ignited, 1 flash, 0 extinctions) at every r.

| | r = 1 | 2 | 4 | 8 | 16 | 32 |
|---|---|---|---|---|---|---|
| PMMA 25: t_peak (s) | 432.5 | 436.0 | 438.5 | 439.5 | 440.0 | 440.5 |
| PMMA 25: mass lost (g/m²) | 6,277 | 6,351 | 6,407 | 6,432 | 6,431 | 6,446 |
| PMMA 65: peak (g/m²s) | 76.74 | 77.53 | 78.02 | 78.27 | 78.41 | 78.47 |
| Pine 30: t_ig (s) | **32.0** | 56.5 | 56.5 | 55.0 | 54.0 | 54.0 |
| Pine 60: first peak (g/m²s) | 14.54 | 13.67 | 13.20 | 13.22 | 13.22 | 13.23 |

- **PMMA, r\* = 2.** r = 1 fails on PMMA 25's peak time, which moves 3.5 s from r = 1 to 2. From 2 to 4 and from 4 to 8,
  every feature stays within tolerance at both fluxes.
- **Pine, r\* = 4.** r = 1 fails: at 30 kW/m², t_ig jumps 24.5 s when the nodes are halved, and the first peak at 60
  falls 6%. r = 2 fails: the first peak at 60 falls 3.5% from 2 to 4. From 4 to 8 to 16 every feature agrees, to
  1.5 s and 0.9%.
- **Observed order** p = log₂(|f_r − f_2r| ÷ |f_2r − f_4r|) at r\*: PMMA's peak 0.87 and 0.92 (25, 65 kW/m²), mass
  lost 1.19 and 1.27; pine's first peak 0.86 and 1.06 (30, 60), plateau 1.17 and 0.95. t_ig's is mostly undefined,
  being quantised at the 0.5 s step. All are in `gate1.probe.*.checks`.

**A alone was not enough for pine:** at FDS's 67 nodes (0.38 mm), one halving still moves ignition 24.5 s.

**Gate 1 passes for both materials.**

## 3. Gate 2: graded numerics

**The seed-0 fits at r\*.**

| Fit | q''_fl (kW/m²) | m''_flash (g/m²s) | k_c (W/mK) | char ε | Objective | At a bound |
|---|---|---|---|---|---|---|
| PMMA forward (fit 25) | 19.01 | 0.9724 | — | — | 86.2 (80.7) | m''_flash at its floor (24/ΔH_c,eff = 0.972) |
| PMMA reverse (fit 65) | **15.00** | 2.378 | — | — | 40.2 (38.0) | q''_fl at its floor |
| Pine (fit 30, 60) | **30.00** | 1.922 | **0.300** | **0.833** | 23.2 (11.7) | q''_fl, k_c and char ε all at their upper bounds |

Pine's objective doubled, and its q''_fl moved from 20.2 to the bound of 30: the first run's coarse nodes had been
doing part of the fit's work.

**N2 at r\*, 2r\*, 4r\*** (graded fluxes, 0.5 s):

| Run | Feature | r\* | 2r\* | 4r\* | Observed p |
|---|---|---|---|---|---|
| PMMA fwd 50 | peak (g/m²s) | 58.37 | 58.70 | 58.88 | 0.84 |
| | t_peak (s) | 218.5 | 219.5 | 220.0 | 1.0 |
| PMMA fwd 65 | peak | 73.93 | 74.39 | 74.64 | 0.86 |
| PMMA rev 25 | t_ig (s) | 222.0 | 222.5 | 222.5 | undefined |
| | t_peak (s) | 504.5 | 507.0 | 508.5 | 0.74 |
| Pine 50 | first peak | 13.292 | 13.299 | 13.304 | 0.58 |
| | plateau | 3.8823 | 3.8823 | 3.8823 | 1.79 |
| Pine 75 | first peak | 15.688 | 15.691 | 15.710 | −2.5 |

- **Every change is within V's tolerances.** The largest are 2.5 s on PMMA reverse's peak time (of 3) and 0.77% on
  PMMA forward's mass lost (of 2.5%).
- **On the orders:** PMMA's peak converges below first order (p ≈ 0.85), to a limit about 0.5–1 g/m²s above r\*'s,
  far less than its 18–28% miss. Pine 75's negative orders come from changes of 10⁻⁴ relative: noise.
- **The first run's PMMA reverse-25 N2 miss** (peak time, +4.5 s on one halving at r = 1) is cleared at r\* = 2, as §6
  of the pre-registration allowed B to do.

N1, N3, N4, N5 and N6 pass for both materials (table above). **Gate 2 passes for both.** N8 also passes.

## 4. Gate 3: validation, regraded

### P0

The rows match the first run's to within 10⁻⁴ s or g/m²s, and the classes are identical: 8 A, 12 B, 1 C. The C is R5's peak time
at 50 kW/m²: 377.5 s for us, against FDS's 368 and the data's 337. That is 1.5 s beyond the B allowance. C's cutoffs
don't touch the 50 kW/m² peak. **Miss.** Every B is still a property-set error the solid shares with FDS: the peak is
5–13% high, half mass comes 33–37 s late, and at 25 kW/m² the back face heats early and late.

### P1 (DBI_Lund), at r\* = 2

| Feature | fwd 50 (model / band) | fwd 65 | rev 25 |
|---|---|---|---|
| t_ig (s) | 20.5 / 21–30, **out**; envelope 22.7–28.7, out | 13.0 / 13–20, in; envelope 9–28.9, in | **222.0** / 97–109, out; envelope 95.7–126.5, out |
| peak (g/m²s) | 58.37 / 42.0–49.4, out | 73.93 / 52.6–57.5, out | 28.88 / 26.3–29.7, in |
| peak time (s) | 218.5 / 226–240, out | 172.5 / 189–200, out | 504.5 / 379–406, out |
| mass lost (g/m²) | 6,651 / 6,193–6,803, in | 6,646 / 6,327–6,730, in | 6,216 / 5,628–6,310, in |

- **Forward:** m''_flash on its floor still flashes at 152.5 s at the fit flux. At 50 and 65 the model burns too
  fast: apparent L_g 0.97 kJ/g against DBI's 1.50.
- **Reverse:** t_ig at 25 is 222 s, so §0.1's prediction holds; the numerics moved it 21.5 s later, as §0.1 allowed
  C might.
- **Outcome 4:** at 65, forward lies in the all-lab envelope on every feature; at 50, it doesn't.
- **Seeds 1–4** miss identically: forward q''_fl 18.82–19.75 with m''_flash on its floor; reverse q''_fl 15.00 every
  time, t_ig at 25 between 210.5 and 220.5 s.

**Miss.** S2 also misses: forward 50 and 65 peak and decay before DBI's peak time.

### P2 (envelope), at r\* = 4

| Feature | 25 | 50 | 75 |
|---|---|---|---|
| t_ig (s) | none / 67–121 | 7.0 / 10.8–26.3, out (early) | 3.5 / 0.7–10.7, in |
| first peak (g/m²s) | — | 13.29 / 12.09–14.11, **in** | 15.69 / 16.61–21.53, out (low) |
| plateau (g/m²s) | — | 3.88 / 5.61–6.39, out (−31%) | 4.41 / 6.33–7.66, out (−30%) |

- **At the fit fluxes** the plateau is already low: 3.31 at 30 kW/m² (4.21–5.02) and 4.11 at 60 (5.82–7.33).
- **At 25 kW/m², m''_flash (1.92) is never reached.**
- **Outcome 6** doesn't apply: every miss persists with IMT removed from the envelope.
- **Seeds 1–4:** the same three bounds, objective 23.19 every time.
- **The Aalto + FZJ fit** (reported) lands on the same bounds.

**Miss.**

**The first run against the rerun.** The first run's first peak was 10–32% high and its plateau 11–14% low. Now the
first peak is right or slightly low, and the plateau is 30% low. Part of the first run's high first peak was the
spurious black-node conductivity. With it gone, the converged model's char layer insulates the virgin wood too well,
even at the largest char conductivity (0.30) and emissivity (0.833) the bounds allow.

### S1, N9, bound flags

- **S1 misses only at 25 kW/m²,** where the model never ignites (and m''_ext is the fallback leak, not independent of
  25). At 50 and 75 the model now sustains through the data window. As registered, any graded run failing S1 is a
  miss.
- **N9:** no class flips. Pine on 25.4 mm Kaowool PM changes its plateau by less than 0.03% at 50 and 75. Under fix A
  the adiabatic back no longer matters within the data window. The first run's flip came from the under-resolved
  two-flux, not from a real backing sensitivity. PMMA's four backing ends move graded features by ≤ 1% and flip
  nothing.
- **Bound flags:** every graded fit has at least one parameter flagged.
  - PMMA forward: m''_flash at its lower end.
  - PMMA reverse: q''_fl at its lower end.
  - Pine: q''_fl, k_c and char ε at their upper ends.
  - m''_ext (1.17) is below m''_flash (1.92), so the hysteresis premise holds.

**Ungraded:** with the heater removed at flash + 60 s and + 300 s, pine at 50 goes out 12 s and 41 s later.
Sustained flaming equals t_ig everywhere. A pine graded run takes about 0.5 s at 268 nodes, a PMMA run about 0.2 s
at 116.

## 5. Outcomes

**Rerun outcomes (§5):** R1 no; R2 no (both graded); R3 no; R4 no; **R5 yes (governs)**; **R6 yes**; R7 no.

**The first pre-registration's §6, on gate 3:** **12 applies** (every fit at a bound). 4 applies partly (65 forward
lies in the all-lab envelope, 50 doesn't). 5 doesn't strictly apply (P1 also misses), but its diagnosis fits pine.
1–3 and 6–11 don't apply: there are misses throughout, neither P1 direction passes, the misses persist without IMT,
V passes at both steps, nothing flips, and N1–N3, N5, N6 and N8 pass.

**Against the first run, criterion by criterion:**
- **Flipped to pass:** N2, N7 and S1's 50 and 75 runs.
- **Flipped away:** N9's flip.
- **Moved the other way:** P1 forward's t_ig at 50 moved out of DBI's band by 0.5 s (21.0 → 20.5 s).
- **Unchanged:** every other verdict.

## 6. What it means

1. **The resolution rule now holds in the solid.** Outcome 10 is cleared, with two numbers for 6.1's design:
   - pine needs 4× FDS's default cells (0.095 mm) and PMMA 2× (0.14 mm);
   - convergence is about first order, so 6.1's verification grid can't be FDS's default for opaque charring
     materials.

   §4.3's node rule in `fire_solid.md` should cite this.
2. **The remaining failures belong to the model and its fixed sets, not the discretisation.** That was the question
   §0.3 said this rerun could decide.
   - **PMMA:** ignition at 25 kW/m² comes about 2× late (§0.2's open question for the owner, unchanged), and the burn
     is about 50% too fast at 50–65 kW/m² (apparent L_g 0.97 against 1.50). P0 shows the same set over-predicting the
     flame-free peak by 5–13%. No q''_fl in [15, 30] fixes both directions.
   - **Pine:** converged, the DM set's char under-delivers the plateau by 30% even at k_c 0.30 and ε 0.833. That points
     at the char model (oxidation, moisture, density), as outcome 5's diagnosis says, not at the bounds' position
     alone.
3. **For the owner (R5 and R6):** rerun 2 (the last under §10.2's time-box) or the fallback exit; no bound moved.
   Numerics have nothing left to fix, so a rerun 2 would change the model or the fixed sets (the char physics,
   §0.2's ignition question, D1's pending H_r(T) ruling), each needing its own pre-registration, with a narrow line
   between "informed by two runs" and "fitting the data". Five bounds hit across three fits, all toward more heat
   feedback for pine and less for PMMA's reverse, is worth weighing before choosing rerun 2 over the fallback.
4. **Known gaps to record in `docs/architecture.md`:**
   - the resolution numbers above;
   - pine's plateau −30% at converged numerics;
   - PMMA's 25 kW/m² t_ig, 222 s against about 100.

## 7. The owner's ruling (2026-11-20): the fallback exit

The owner took `fire_model.md` §7's fallback, and fire stays a long-term feature (`docs/plans/long_term_features.md`).

- **Phase 1's fire exit is the highest rung that passes honestly:** the lone-surface solid, verified against FDS and
  node-converged, ignited by the torch, burning, charring and flaming out. It is verified, not validated: its
  validation misses (§4, §6.2) ship as Known gaps in `docs/architecture.md` with 6.1's code, with the numbers above.
- **The crate moves to Phase 2,** with 6.2–6.4 (the flame object, two bodies, the crib).
- **Rerun 2 stays banked,** unspent, until §0.2's pre-ignition question has a cited answer (a cone-in-air parameter
  set, or an ignition criterion from the literature). It then gets its own pre-registration.
- **Open for 6.1's design:** whether the slab exit flips the burnout red gate
  (`tests/test_cross_tier.py::test_a_fire_that_has_burned_its_fuel_stops_heating`), which the plan put at 6.4.
