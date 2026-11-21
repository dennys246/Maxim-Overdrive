# Solid spike: results (2026-11-20)

Pre-registration: `preregistration.md` (65ee7d6). Stage 0's bands: `spikes/physics/solid/stage0/bands.json` (03f7cc0).
Code and numbers: `spikes/physics/solid/` (`results.json` holds every value below; `timings.json` the CPU times).

## The verdict, first

**The solid's numerics hold up; the cone predictions don't.** V passes, but only after a fix made after the first V run
(outcome 7, below). Every one of the five fits lands on a bound of its range. Held-out, P1 misses in both directions and
P2 misses at every flux. Pine's features also depend on the node size well beyond the tolerance (N2). The governing
outcome is **12** (fits at bounds), with **7** (V fixed and everything rerun), **10** (N2 misses) and **9** (an N9 range
end flips a class) also triggered. The free parameters can't make up for what is missing in the fixed property sets and
the model, and 6.1 can't build its cone tests as specified.

| # | Verdict | The numbers |
|---|---|---|
| V1 | **pass** (after fix D1) | 25R1: peak 9.84 vs FDS 10.03 g/m²s (−1.9%); t(≥1) +1.5 s; t(≥2.7) +1.5 s; t(½ peak) −1.5 s; front T(300 s) +1.2 K; mass(300 s) −0.5%. As registered: **miss**, t(½ peak) −4.5 s |
| V2 | **pass** (after D1) | R3: peak 31.51 vs 31.99 (−1.5%); t(½ peak) −1.5 s; front T +7.9 K; mass(300 s) −1.5%; peak time +5 s. As registered: **miss**, peak −8.0%, t(½ peak) −8.5 s, mass −5.8% |
| V3 | **pass** (after D1) | V1 and V2 pass at 0.01 s and at 0.5 s; the largest change between the two steps is 0.5 s on a crossing time |
| P0 | **miss** | 8 A, 12 B, **1 C**: R5's peak time, 377.5 s against data 337 and FDS 368. The C is 1.5 s beyond the B allowance |
| P1 | **miss** | forward: peak at 50 and 65 is 17–27% above DBI's band, peak time 9–18 s early, t_ig at 50 outside the envelope; reverse: t_ig at 25 is 200.5 s against DBI's 97–109 |
| P2 | **miss** | at 25 kW/m² the model never ignites; at 50 and 75 the first peak is 10–32% high and the plateau 11–14% low; only t_ig at 75 is in band |
| S1 | **miss** | 25: no ignition; 50 and 75: the model goes out (min m'' 0.48 and 0.86 g/m²s against the 1.29 needed) before the data window ends |
| S2 | **miss** | forward 50 and 65: the model peaks and burns out before DBI's peak time (m''_10 falls by 1.8 g/m²s); reverse 25 passes |
| N1 | **pass** | t_ig moves ≤ 0.5 s between 0.5 and 0.25 s; the 0.125 s peak is within 0.1% of 0.25 s. Pine 25 is vacuous: no step ignites |
| N2 | **miss** | pine 50 and 75: first peak −17%, plateau −11%, and the extinction disappears when nodes are halved; PMMA reverse 25: peak time +4.5 s |
| N3 | **pass** | at most 1 flash per part in all 94 graded and numerics runs |
| N4 | **pass** | with m''_ext = 1.5·m''_flash: PMMA 3 and 4 flashes, pine 5 and 10 flashes (at 0.5 and 0.25 s), so N3 and N1 both go red |
| N5 | **pass** | worst mass error 5.4×10⁻¹⁵ of the initial mass, every step of every run |
| N6 | **pass** | worst energy residual 8.1×10⁻¹⁶ of cumulative absorbed; deleting a line gives ≥ 2.7×10⁻⁵ (reaction), 1.3×10⁻³ (convection), 6.7×10⁻³ (re-radiation), 1.0 (absorbed) |
| N7 | **miss** (2 of 5 parts) | thick t_ig +0.001%, thin −0.003%, erfc 0.10%, the inert slab changes no bit in 200 steps, the n = 0.5 node depletes to exactly 0: pass. κ = 10⁹ against surface absorption: **−2.9%**. Ambient rates: **not 0** for PMMA's reaction 1 and pine's reactions 1 and 5 |
| N8 | **pass** | `run.py --check` in a fresh process with another hash seed: `results.json` byte-identical; the PMMA seed-0 fits rerun byte-identical |
| N9 | **class flips** | pine on 25.4 mm Kaowool PM keeps burning at 50 and 75 (no extinction), so the class changes. PMMA's four backing ends change no class |

Total CPU (single-threaded): FDS 120 s; the 18 fits 2,584 s (plus 144 s for the two N8 fit reruns); the pipeline 172–175 s per
pass, three passes. About 3,400 s in all.
Load average 2.4–6.0 during the runs, with per-run values in `timings.json`.

## 1. Deviations, labelled

**D1 (after a run; outcome 7).** As registered (H_r constant at the set's value), V missed at 0.01 s (table above).
I diagnosed it from FDS's own output before changing anything. FDS 6.11.1 defaults `ADJUST_H` on (read.f90
7700–7820), which makes the heat of reaction depend on temperature: H_r(T) = H_r + (c_p,gas − c_s)(T − T_ref). The
inputs' gas, `SPEC ID='MMA', FORMULA='C5H8O'`, has no thermodynamic data, so FDS gives it c_p = (R/MW)·γ/(γ−1) with
γ = 1.4, which is 0.346 kJ/kgK (data.f90 `THERMO_TABLE_GAS`). The slope is therefore −1.78 kJ/kgK. T_ref is FDS's
5 K/min TGA peak (`GET_TMP_REF`): 452.95 K and 627.84 K. At PMMA's 670 K surface, reaction 2's heat is 842 kJ/kg, not
914. I implemented exactly that, with no free number in it. It reproduces the H_r table FDS prints in its `.out`
to 0.03% (`fds_h_r_check`), V then passes, and everything downstream was rerun on the fixed model. Two cautions follow:
- The slope comes from an FDS default for an undefined gas, not from MaCFP's property set. Real MMA vapour has a
  c_p of about 1.5–2 kJ/kgK, which would give a slope several times smaller. **The model that matches FDS is therefore
  less faithful to PMMA than the one registered.** For transparency, P1 was also fitted and graded on the registered
  constant-H model (reported only, `P1_as_registered_constant_H_reported`). It misses the same way: forward peaks at
  52.6 and 65.5 g/m²s, reverse t_ig at 25 is 212.5 s.
- Pine keeps a constant H. Its set gives no gas c_p, and no FDS input exists for pine.

**D2 (before any run).** The pine chain's kinetics are exact per reaction at frozen T. Each solid product is added
immediately, so it can react in the same step. That is first order in dt across a chain. §3's "exact frozen-T update"
is written for one reactant.

**D3 (before any run).** The front's reflection q⁺(0) = q_in + (1−ε)q⁻(0) is solved exactly at frozen T. FDS lags it
one substep.

**D4 (before any run).** The two-flux source is explicit at the old T (as in FDS), plus an implicit
nearest-neighbour linearisation of its σT⁴ terms. Without that, black pine char nodes would be explicitly unstable at
0.5 s. The pair terms are antisymmetric, so the ledger closes exactly.

**D5 (before any run).** Regression also merges a surface node that holds no reactive mass. NIST-StMU's inert is
exactly 1%, so a depleted node sits on the 1% threshold, and the strict "< 1%" test would be decided by rounding. N7
found a bug in my first version of this rule: it merged inert-from-start nodes. That was fixed before any recorded run.
It could not affect V, because every PMMA node starts reactive.

**D6 and D7 (N7, reported as misses, not reinterpreted).**
- No two-flux scheme with uniform-temperature nodes has surface absorption as its κ → ∞ limit. Adjacent black nodes
  still exchange σ(T_i⁴ − T_j⁴), and node 0 emits at its centre's temperature, not the face's.
- With the pre-registered cutoff (10⁻⁹ s⁻¹), T_cut lies below 20 °C for these low-E reactions: 252 K (PMMA 1), 279 K
  and 163 K (pine 1 and 5). The rates at 20 °C are 1.1×10⁻⁷, 4.8×10⁻⁹ and 2.1×10⁻⁶ s⁻¹ (pine 5 acts on an
  intermediate that is zero at ambient).

**Choices the pre-registration leaves open (all made before any run).**
- Cone h = 13 W/m²K, the inputs' value. Ambient and initial T 20 °C.
- q''_fl is incident radiation, absorbed with ε through the two-flux path.
- Flash and extinction are tested on the step's m'' at step ends.
- The class for N1 and N2 is (ignited, flashes, extinctions).
- P0 is graded at 0.5 s, the step P uses; 0.01 s gives the same counts.
- A run without a fit feature scores 10⁶.
- Superwool's k above 70 °C extends the table's least-squares slope.
- Pine ε is held at the table's ends outside 10–60 kW/m².
- Node counts follow FDS's rule (24/23 PMMA and 53 Kaowool in V; 22–23 PMMA, 2 × 18 Superwool and 67 pine in the
  cones).
- Model features are computed with stage 0's own functions on the model's step-end series.
- The fit's parameter units are kW/m², g/m²s, W/mK and ε.
- The BUWfd variant was not run: stage 0 has no BUWfd band.

## 2. V: our solid against FDS 6.11.1

FDS ran on the 11 pinned inputs, reproducing the earlier runs byte for byte (25R1 and R3 compared). Our solver was
read at FDS's device times. After D1, every V row passes at both steps.

Margins after D1:
- **V1:** front T +1.2 K of 12; t(½ peak) −1.5 s of 3.
- **V2:** front T +7.9 K of 12; peak −1.5% of 2.5%.

The 7.9 K is the thinnest margin. FDS's own surface T at 50 kW/m² moves +5.9 K when its cells are halved (fire_solid
§4.6), so the gap is about the size of FDS's own grid sensitivity. 25R1's ungraded peak time is 936 s against FDS's
889.5, on the flat plateau the pre-registration expected. Our back temperature follows FDS's `TSB1` to within 0–7.5 s
on every crossing. That confirms that FDS reads its depth device from the last PMMA cell.

## 3. P0: against NIST's gasification data

The solid as fixed by D1, at 0.5 s:

| Feature (repeats) | Class | Ours / FDS / data |
|---|---|---|
| back T 100 °C (25R1, 25R2) | B, B | 159.0 / 160.5 / 145; 163.5 / 163.5 / 145 |
| back T 100 °C (25R3, T3, T4) | A, A, A | 145.5 / 147 / 133; 115.5 / 115.5 / 114; 111.5 / 111.5 / 112 |
| back T 200, 300 °C (25R1, 25R2) | B ×4 | 313.5 vs data 345; 594 vs 749; 321 vs 344; 609 vs 743 (FDS within 7.5 s of ours) |
| peak m'' (R3–R5) | B ×3 | 31.5 / 32.0 / 27.8–29.9 |
| peak time (R3, R4; R5) | A, A; **C** | 351, 350.5 vs 346, 326; R5 377.5 / 368 / 337 |
| t(m'' ≥ 2.7) (R3–R5) | A ×3 | 43 / 42.5 / 37–41 |
| t(½ sample mass) (R3–R5) | B ×3 | 259.5, 259, 276 vs 226, 223, 239 |

The property set is off flame-free, as §0's risk 1 predicted. It over-predicts the 50 kW/m² peak by 5–13% and reaches
half mass 33–37 s late. At 25 kW/m² the back heats too fast early and too slowly late (300 °C at about 600 s against
749). Our solver tracks FDS on all of this; the one C is a 9.5 s solver difference on R5's flat peak. The registered
constant-H model scores 11 A, 6 B, 4 C: its lower peak happens to land in the data's range, but its half-mass times are
worse.

## 4. P1: black PMMA, DBI_Lund

| Fit | q''_fl (kW/m²) | m''_flash (g/m²s) | Objective | At a bound |
|---|---|---|---|---|
| forward (fit 25), seed 0 | 18.86 | 0.974 | 80.7 | m''_flash at its lower end (0.972) |
| reverse (fit 65), seed 0 | **15.00** | 1.809 | 38.0 | q''_fl at its lower end |

**Forward.** At the fit flux the model's t_ig is 151.5 s against DBI's 97–109. No free parameter can move it, because
m''_flash is already at its floor and q''_fl acts only after the flash. So the fit trades t_ig against the peak.

Held-out (model / DBI band):

| Feature | 50 kW/m² | 65 kW/m² |
|---|---|---|
| t_ig (s) | 21 / 21–30, in; envelope 22.7–28.7, out | 13.5 / 13–20, in; envelope 9–28.9, in |
| peak (g/m²s) | 57.7 / 42.0–49.4, out | 73.0 / 52.6–57.5, out |
| peak time (s) | 217.5 / 226–240, out | 171.5 / 189–200, out |
| mass lost (g/m²) | 6,583 / 6,193–6,803, in | 6,565 / 6,327–6,730, in |

**Reverse.** At 25 kW/m², t_ig is 200.5 s (band 97–109) and the peak time 488.5 s (band 379–406); the peak and mass lost
are in band.

**The cause is upstream of the fit.** With the published set the solid takes about 150–200 s to reach a flaming mass
flux at 25 kW/m². FDS does too: 162 s to 1 g/m²s in 25R1. The cone data ignite at about 100 s. At 50–65 kW/m² the model
ignites on time but burns too fast: its apparent L_g is 0.99 kJ/g against DBI's 1.50 (slopes of peak m'' against
flux).

- **Outcome 4:** at 65 the forward run lies inside the all-lab envelope on every feature; at 50 (DBI is the envelope)
  it doesn't.
- **Outcome 3** does not apply: neither direction passes.
- **Seeds 1–4:** forward q''_fl 18.60–18.86 and m''_flash 0.972–0.974, with graded peaks within 0.3 g/m²s of each
  other. Reverse q''_fl is 15.00 every time, m''_flash 2.15–2.29, and t_ig at 25 is 213–218 s. Every seed misses
  identically.

## 5. P2: white pine, parallel grain

**Fit, seeds 0–4.** q''_fl 20.22 kW/m², m''_flash 2.44–2.49 g/m²s, k_c **0.300** (upper bound), char ε **0.833** (upper
bound), objective 11.70 for every seed. The Aalto + FZJ-only fit (reported) lands at the same bounds, objective 19.4.

At the fit fluxes the model ignites early and its plateau is low:

| Fit flux | t_ig (model / envelope centre) | plateau (model / envelope) |
|---|---|---|
| 30 kW/m² | 25 / 41 s | 3.93 / 4.21–5.02 |
| 60 kW/m² | 6 / 14 s | 5.18 / 5.82–7.33 |

The fitter pushes char conductivity and emissivity to their limits to raise the plateau, and can't.

Held-out (model / envelope):

| Feature | 25 kW/m² | 50 kW/m² | 75 kW/m² |
|---|---|---|---|
| t_ig (s) | none / 67–121 | 8.0 / 10.8–26.3, out | 4.0 / 0.7–10.7, in |
| first peak (g/m²s) | — | 18.66 / 12.09–14.11, out | 23.66 / 16.61–21.53, out |
| plateau (g/m²s) | — | 4.82 / 5.61–6.39, out | 5.66 / 6.33–7.66, out |

At 25 kW/m² the fitted m''_flash (2.49) is never reached.

**Outcome 6** does not apply: every miss persists with IMT removed from the envelope. **Outcome 5** (P1 passes, P2
misses) does not strictly apply either, because P1 also misses. Its diagnosis still fits pine: a char model short of
oxidation, moisture and density variation, and a black-node two-flux that is badly under-resolved (§6).

**S1.** 25 kW/m² is not independent (m''_ext is the 25 kW/m² fallback leak, as stage 0 flagged). At 50 and 75 the
model's m'' falls below m''_ext = 1.17 at 1,313 and 1,092 s. That is before the data windows end (1,401 and 1,132 s),
so the flame goes out. The adiabatic back biases toward a sustain pass (§7 of the pre-registration), and the model
still fails.

**m''_ext against m''_flash:** 1.17 < 2.49, so the hysteresis premise holds and that half of outcome 12 is not
triggered.

## 6. N: numerics

**N1** (step) passes everywhere it can be evaluated. At 0.5 against 0.25 s, t_ig differs by 0.25–0.5 s against a
tolerance of ≥ 0.5 s; the 0.125 s peak is within 0.1% of 0.25 s. 0.5 s is an adequate step for this solid, so outcome 8
is not triggered.

**N2** (nodes) fails for pine, and the failure is structural. Pine at 50 kW/m² with nodes halved repeatedly:

| Nodes | 67 | 134 | 268 | 536 |
|---|---|---|---|---|
| First peak (g/m²s) | 18.66 | 15.46 | 13.92 | 13.12 |
| Plateau (g/m²s) | 4.82 | 4.30 | 4.02 | 3.87 |

That is first-order convergence toward about 12.3 and 3.7. The likely cause, a diagnosis I have not verified: with
κ = 5×10⁴ m⁻¹ each 0.38 mm node is optically black (2κdx = 38). Two things then scale with dx: a black-body exchange
between neighbours, which acts as a spurious conductivity of 4σT³·dx (0.06 W/mK at 900 K, against k_c = 0.3), and
emission from the node centre rather than the face. FDS's default cell rule is simply too coarse for an opaque two-flux
material. The pine fit was done at this resolution, so its bound-hitting values partly absorb the discretisation error.

PMMA passes N2 at 50 and 65 (≤ 1.3%, ≤ 1.5 s). At reverse 25 the peak time moves 4.5 s against a 3 s tolerance. The
cause is the flat peak plateau again (V1's peak time is ungraded for the same reason). Nonetheless it is a miss.

**N3–N6** pass. N4 proves the guard: with the hysteresis inverted, PMMA toggles 3 and 4 times and pine 5 and 10, at
0.5 and 0.25 s respectively.

**N7** misses on D6 and D7. Both are flaws in what was registered (the κ → ∞ test can't pass with any node-uniform
two-flux scheme, and the cutoff is below ambient for these sets), not kernel bugs. The conduction closed forms pass by
orders of magnitude.

**N9.** PMMA's backing ends (k 0.041, Kaowool PM's k ramp, c 800 and 1,200) move graded features by ≤ 1% and flip no
band membership. Pine on 25.4 mm Kaowool PM loses its extinction at 50 and 75 kW/m², so the class flips. Pine's sustain
is a band, not a margin (outcome 9).

**Ungraded.**
- *Heater removed* (pine at 50, the prediction asked for): flame-out 10.5 s after the heater goes off at
  flash + 60 s, and 32.5 s after at flash + 300 s. As expected for a lone surface (pre-registration §7).
- *Time to sustained flaming* equals t_ig in every run.
- *Runtime:* 0.1 ms per step at 80 nodes; a PMMA cone run takes 0.13 s, a pine graded run 0.6 s.

## 7. What this shows and doesn't

**Shows:**
- The kernel solves what it claims to. It matches FDS on FDS's own inputs once FDS's temperature-dependent H_r is
  included. It conserves mass and energy to 10⁻¹⁵, is step-converged at 0.5 s, and its guards are live.
- The registered fixed property sets plus two or four cone constants do not reproduce held-out cone data for either
  material. The failures are not marginal: a 2× ignition delay for PMMA at 25 kW/m², and no pine ignition at
  25 kW/m².
- For pine, the black two-flux at FDS's default node size is not node-converged.

**Doesn't show:**
- Whether a different constant (not tested) or a flux-dependent q''_fl would pass. Outcome 12 hands that to the owner.
- Whether NIST-StMU's late ignition at 25 kW/m² comes from κ, from the cone's heater spectrum, or from the set. P0 has
  no 25 kW/m² mass data to separate these.
- Anything about flames, cells, cribs, contact or world limits (pre-registration §7). 65 kW/m² and the flame path
  remain unverified against FDS.
- That D1 is physically right. It matches FDS, which uses a defaulted gas c_p.

## 8. N8: determinism

The PMMA seed-0 fits were rerun in separate processes and are byte-identical. `run.py --check` recomputes everything
from the fits in a fresh process with another `PYTHONHASHSEED` and compares `results.json` byte for byte. The pine fit
was not rerun (its 5 seeds already agree to 10⁻⁴ in q''_fl). The check passed: `results.json` is byte-identical
(`out/run.log`).

## 9. What it means for 6.1 and the 6.2 design

1. **6.1 cannot build as specified.** Outcomes 12 and 10 both block it. The owner rules on the bounds; no bound moved
   here.
2. **Pine needs node convergence before any fit means anything.** That is a resolution-rule failure (outcome 10). The
   fix is in the solid's discretisation, in one of two ways:
   - treat κ ≥ 5×10⁴ as opaque, with a face temperature and FDS's own surface absorption (which FDS does, at its
     4.9×10⁴ threshold, and which the pre-registration's §10.7 declined);
   - refine the first millimetre.
   This should be decided before 6.1, and the pine fit redone after it.
3. **D1 needs an owner ruling:**
   - adopt FDS's H_r(T) (matches the verification reference, physically doubtful);
   - keep constant H and re-verify against an FDS run with `ADJUST_H=F` (not run here);
   - give the gas a measured c_p.
   The first keeps V; the other two need a new V run.
4. **For 6.2:**
   - q''_fl can't be treated as a fitted configuration constant: the reverse fit sits on its floor, the forward fit
     overshoots held-out peaks, and the apparent L_g is a third low.
   - Flame feedback must depend on something, likely flux or the sample, and the set's flame-free errors (P0) must be
     fixed first or they land in q''_fl.
   - The 25 kW/m² PMMA ignition gap (2×) is the most important single number for any world fire that starts from a
     weak exposure.
5. **Known gaps to record in `docs/architecture.md`:**
   - pine's node dependence (first peak 18.7 → 13.1 g/m²s across 8× refinement);
   - PMMA's 25 kW/m² t_ig (151–212 s against about 100);
   - T_cut below ambient for low-E reactions.
