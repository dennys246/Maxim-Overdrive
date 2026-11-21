# fire_solid.md (6.0–6.1), design review: Physics and resolution

Read on disk: `docs/design/fire_solid.md` (staged), `fire_model.md` v2, `code_review.md`, CLAUDE.md, L1 and V7, the
round-one and delta-1 physics reviews, and `src/simcore/core/heat.py` at gates. MaCFP `matl-db` was read at `master`
with `gh api` on 2026-11-20. FDS 6.11.1 runs are in `_durable/fire_solid_review/scratch/physics/` and the pine CSVs
in `_durable/fire_solid_review/data/`. Tags: **V** primary source read by me, **S** secondhand, **M** memory, **D**
derived (my scripts or FDS runs).

**Counts: 3 BLOCKER, 9 SHOULD-FIX, 4 NIT.**

## 0. What I measured

**MaCFP's PMMA FDS inputs are not cone inputs (V).** Every `.fds` under `PMMA/Validation_Results/` models the NIST
gasification apparatus: anaerobic N₂, `SOLID_PHASE_ONLY=T`, no flame, 25 and 50 kW/m² only.
- NIST-StMU-FSRI R3: h = 13 W/m²K; two reactions plus an inert fraction; `ABSORPTION_COEFFICIENT=2620`, which is
  in-depth absorption (FDS two-flux); behind the sample, Kaowool and an aluminium plate.
- Aalto-I: κ = 3,091.5 m⁻¹, h = 15.

No input exists at 65 kW/m² or with a flame. The NIST-StMU set is calibrated on TGA, DSC, MCC and literature (V,
`MaCFP_PMMA_NIST-StMU.json`), so it is independent of the cone data.

**FDS 6.11.1 runs of NIST-StMU (D).** "abs" is the input as shipped; "surf" deletes κ. The m'' columns are the first
times the burning rate reaches 1 and 2.7 g/m²s.

| Case | Peak m'' (g/m²s), time | m'' ≥ 1 (T_s) | m'' ≥ 2.7 | 1 → 2.7 |
|---|---|---|---|---|
| 25 abs / surf | still rising at 800 s | 162 s (310 °C) / 171 s (330 °C) | 246 / 266 s | **85 / 95 s** |
| 50 abs / surf | 32.0 at 346 s / 30.0 at 388 s | 20.5 / 19.0 s | 42.5 / 39.5 s | **22 / 21 s** |
| 65 abs / surf | 46.3 at 248 s / 43.9 at 281 s | 13.2 / 11.2 s | 20.4 / 20.8 s | **7 / 10 s** |
| 50 abs, `CELL_SIZE_FACTOR=0.5` | 31.7 at 350 s | 20.0 s | 41.5 s | |
| 50 abs, DT = 0.5 s | 33.4 at 350 s | 21.0 s | 43.0 s | |

The 25 kW/m² run took 12.9 s of wall time, which agrees with the design's "13 s".

**Pine at 25 kW/m², parallel grain (D, FSRI R1–R3 and IMT R1–R2):**
- **Plateau.** The 300 s mean MLR is 3.4–3.9 g/m²s; the 30 s minimum over t_ig + 250–450 s is **3.0–3.7**.
- **Late test.** From about 1,500–1,800 s after ignition, MLR is **0.7–1.6** while HRR stays at 22–39 kW/m². That is
  about 24–34 kJ/g, which is char oxidation, not flaming.
- **t_ig.** FSRI R3 first crosses 24 kW/m² at **27 s**, drops back to 6 kW/m² at 52 s and sustains from about 57 s.
  `Scripts/MaCFP-4/Cone_analysis.py` takes the *first* crossing (V: `df[df['HRR (kW/m2)'] >= 24].index[0]`).

**Other facts (V):**
- PMMA cone data at 50 kW/m² come from two labs (DBI_Lund, ULSTER).
- Cone backings differ by lab: 25.4 mm of Kaowool (NIST), 13 mm of Superwool (DBI), vermiculite with a retainer
  frame (UQ).

## 1. BLOCKERs

### B1. Flash and extinction toggle at the physics-step period, and the design calls it "flashing"
`fire_solid.md::§4.2` (thresholds; "not a contradiction")

The cited ranges are disjoint (m''_flash 1–2, m''_ext 2.7–8.3), so **every** flash starts below m''_ext. On the
heater alone m'' needs 85–95 s to climb from 1 to 2.7 g/m²s at 25 kW/m², 21 s at 50 and 7–10 s at 65 (D, §0). Adding
a 15–30 kW/m² flame flux makes 25 kW/m² look roughly like 50, so m'' stays below m''_ext for about 10–20 s.

*Failure scenario.* PMMA at 25 kW/m² with a 0.5 s step:
1. The part flashes at m'' = 1.
2. Next step it is still below 2.7, so it is extinguished.
3. It is still above m''_flash, so it reflashes the step after.

The flame flux runs at a duty cycle set by the unwritten order of checks within a step. Halve dt and the time to
sustained flaming changes. Near the sustain boundary (pine at 25, the heater-off case), so can the class.

Real flashing has a gas-phase timescale (the flammable layer burns off and must re-accumulate). This model has none,
so its cycle is numerical. This is delta-1 P2-B2(b) reopened: the fix asked for an induction time, and the design
relabelled the defect instead.

*Fix.*
- Exempt a flame created at flash from extinction for a cited induction time, fixed in seconds.
- Or decide sustain from the steady state the part reaches with q''_fl applied.
- Test it: run R0 at dt and dt/4 and require the same class and t_ig within tolerance. Make the test go red when the
  rule is deleted.

### B2. Two §6 checks can't fail in a cone test
`fire_solid.md::§1.1` segment size; `§3` "Frequency"; `§6` "Segment size halved"

- **Segment halving.** The cone's heater and flame fluxes are uniform, and 6.1 has no lateral conduction and no front
  motion, so every segment is identical. Halving the segment size changes only the summation order. A test that
  cannot fail is a BLOCKER under the charter.
- **Coupling frequency.** R1 is "grid-free" (§3) and its backing is layers inside the solid (§4.1), so no cell
  couples to the sample. The "once per step" and "every substep" runs are therefore identical. "Every heat substep"
  also names no run: the count is 4, 16 or 64 depending on dx (`heat.min_substeps`, V).

*Fix.* Move both checks to cases with a gradient they can see:
- segment size: a non-uniform flux map (the gasification apparatus ships `q25_hfmap.png`, V), or the straddle case;
- coupling frequency: the straddle test on the concrete floor at all three dx.

Or call them invariance checks and drop the claim that they test segment independence or lag.

### B3. The FDS verification as written compares different physics, and some of its cases don't exist
`fire_solid.md::` intro ("MaCFP ships FDS cone inputs"); `§6` FDS verification; `§4.1` conduction

§6 says it runs "at 25, 50 and 65 kW/m²" with "FDS's boundary conditions". The inputs that exist (§0, V) differ in
four ways:
- they model N₂ gasification at 25 and 50, with no 65;
- they have no flame, so §4.2 gets no verification;
- they absorb in depth (κ 2,620–3,092 m⁻¹, a penetration depth of 0.32–0.38 mm, about one first node);
- §4.1 has surface absorption only.

*Failure scenario (D).* A correct surface-absorption solver run with "MaCFP's NIST-StMU-FSRI parameters" differs from
FDS by:
- 33–42 s in peak time (against a 5 s tolerance);
- 6–7% in peak m'' (against 2%);
- 7–15% in the time to m'' ≥ 1.

So the test goes red for a physics choice nobody made. And because the tolerance is set "after one FDS run", the
likely outcome is that it gets set to fit.

*Fix.*
- Add Beer–Lambert in-depth absorption to §4.1 (or a one-flux simplification with its error measured against FDS).
  Otherwise, verify against an FDS case with κ deleted and say it is no longer MaCFP's case.
- State that 65 kW/m² is our edit of `EXTERNAL_FLUX`, and run with flash logic off.
- Add one FDS case whose `EXTERNAL_FLUX` steps up by q''_fl at a prescribed t_flash, against our solver forced to
  flash then, so the flame-flux path is verified.

FDS's own spread between node densities (0.9% on peak, 4 s on its time; D) supports the 2% and 5 s tolerance, but
only when run at the shipped dt (S7).

## 2. SHOULD-FIX

### S1. "Sustained" t_ig is not the data's own definition
`fire_solid.md::§4.2` ("the data's own definition (Q'' ≥ 24 kW/m² sustained)")

MaCFP's t_ig is the *first* crossing (V, §0; V7 2c). On FSRI pine R3 at 25 kW/m², the first crossing and sustained
flaming are 27 s and about 57 s (D). Grading the model at "sustained" against lab means taken at "first" biases
low-flux t_ig late, which is exactly where flashing happens.

*Fix.* Apply the data's rule to the model's Q'' = m''·ΔH_c,eff while flaming, and define Q'' during a flash. Report
the sustained time as a second, ungraded number.

### S2. More free parameters than features, and the design's own rule fixes the kinetics
`fire_solid.md::§4.3` "Free parameters"; "Where MaCFP publishes a property … it is used"

§4.3 never lists its graded features. Counting from fire_model §6.2:
- **PMMA** (two reactions plus an inert fraction, as MaCFP's sets do; V): A, E and ΔH_r per reaction plus a mass
  fraction make about 7. Add q''_fl, m''_flash and m''_ext and that is **about 10 parameters against about 4
  features** (t_ig, plateau, back-face peak and its time) from one curve.
- **Pine**: **12 or more against about 8**.

The fit then has a manifold of exact solutions, and the held-out prediction is wherever the seeded optimiser stops.
Two of the parameters are unidentifiable:
- m''_ext for PMMA: it burns to burnout, so no feature sees it, and the fit drifts to an edge;
- m''_flash for PMMA: first-crossing t_ig is m'' ≥ 0.98 at ΔH_c 24.4, which trades off against A and E.

MaCFP *publishes* kinetics and ΔH_r from TGA and DSC. Under the design's own rule, they are not free.

*Fix.*
- Take kinetics, ΔH_r, k, c, ε and κ from one named MaCFP set calibrated without cone data. NIST-StMU qualifies (V).
- Fit only q''_fl and m''_flash, plus k_c and char ε for pine. List every feature, and require fewer parameters than
  fitted features.
- Hold m''_ext out of the PMMA fit.
- Run several seeds and report the spread of the held-out predictions.
- Add MaCFP's NIST gasification data (V, `PMMA/Validation_Data`) as a flame-free validation of the solid alone, so
  its errors aren't absorbed into q''_fl.

### S3. A held-out flux constrains the fit
`fire_solid.md::§4.2` ("pins m''_ext ≤ 3.8"); `§4.3` ("never seen by it")

Pine at 25 kW/m² is held out, yet its MLR bounds m''_ext, and R1 then grades "sustained at 25".

Two more problems:
- **The bound.** 3.8 is a time mean, and the plateau's 30 s minimum is 3.0–3.7 (D), so the bound sits inside the
  data's own band. No outcome margin is given, which CLAUDE.md requires for binary outcomes.
- **The PMMA side.** If the "published" k, c and ε come from a cone-calibrated set, the held-out flux has already
  shaped them.

*Fix.*
- Take the bound from outside the graded set (V7 1's species band) or from the fit fluxes.
- Gate sustain on min m'' over the window ≥ 1.1·m''_ext.
- Name the property set and its calibration data.

### S4. q''_fl is a constant with a hidden convective loss, and its range is miscited
`fire_solid.md::§4.2` ("in MaCFP practice … 15–30 kW/m² (V, L1 §2.3)"); `§3`

**Miscited.** L1 §2.3's numbers are McKinnon's *cardboard*, not MaCFP. They also show the flame flux rising with the
external flux, from 17.2 kW/m² at 20 to 29.9 at 60 (V via L1). A constant fitted at 25 and graded at 65 (and the
reverse) is biased by about 1.7×, in opposite directions.

**Hidden loss.** The surface keeps losing h(T_s − T∞) to ambient air under its own flame: 4.4 kW/m² for PMMA at
630 K, 6.9 kW/m² for char at 823 K, at h = 13 (D). The fit then returns q''_fl minus that loss, which is not what
the cited range bounds. Since char heats up during the test, the bias drifts with time.

*Fix.*
- Turn off the convective loss while a part flames, and define q''_fl as a gauge would measure it.
- Cite the range from PMMA or wood data.
- Allow a cited linear law q''_fl(q''_ext), or report the forward-against-reverse PMMA disagreement.

### S5. No grading window, char oxidation is off, and HRR needs ΔH_c
`fire_solid.md::§4.1` "Residue"; `§4.3`

- **Window.** Pine's MLR at 25 kW/m² falls below 2.7 about 1,500–1,800 s after ignition, while the data keep
  Q'' ≥ 24 through glowing (D). With char oxidation off, the model goes out about 600 s early. Whether "sustained"
  passes therefore depends on a window the design doesn't define.
- **Oxidation.** The 30 kW/m² second peak (990–1,610 s after t_ig, L1) overlaps the start of oxidation.
- **ΔH_c.** Pine's ΔH_c,eff swings 13.2–16.4 kJ/g across fluxes (D, L1), a 24% swing, wider than the first-peak
  envelope (±19%). MaCFP's HOC includes glowing (V, script).

*Fix.* Pre-register each window, for example from t_ig until the data's MLR first falls below 2.7. Grade pine on MLR,
and derive HRR using ΔH_c from the fit fluxes only.

### S6. One backing graded against an envelope of several
`fire_solid.md::§4.1` "Back face" ("as in its FDS inputs")

The FDS inputs' layers (Kaowool plus aluminium) are the gasification apparatus's backing, not a cone backing. Cone
backings differ by lab (§0, V), and FZJ's pine shows no second peak (L1). Back-face features graded against a
min–max envelope that mixes backings are either trivially inside it or wrong for an untracked reason.

*Fix.* Grade the back-face features (PMMA's rise, pine's second peak) per lab with that lab's backing, or report them
ungraded. Correct the sentence.

### S7. The solid's time step is unspecified and untested
`fire_solid.md::§3` "Frequency"; `§4.1`; `§6`

The design never says the solid's dt. Today's world step is the 6 s turn, and step 5a's physics step is still
`TEMPORARY` (V, `heat.py`). Pine's t_ig at 75 kW/m² is 4–8 s (L1). Even at 0.5 s:
- FDS's own CN solver with substepping moves peak m'' by 4.5% (D), outside §6's 2%.
- Backward Euler plus frozen-T kinetics is first-order. The explicit sink moves a surface node about 8 K per step at
  65 kW/m², against an Arrhenius e-folding of about 21 K (D).
- If the solid substeps with the heat grid, its dt varies with dx.

*Fix.* Fix the solid's step in seconds, independent of dx and the turn. Add a dt, dt/2, dt/4 convergence test on
t_ig and peak m'', and run §6 at the shipped dt.

### S8. Law (a) thresholds a node mean, and PMMA has no regression rule
`fire_solid.md::§1.1` "Nodes"; `§4.1` (a)

- **Law (a).** It fires when a node's mean T reaches T_p. Across a 0.33 mm surface node under 25–65 kW/m², the
  gradient is tens of kelvin. That is CLAUDE.md's average-then-threshold at node scale, so t_ig depends on node size.
  §6's node checks (erfc, FDS at two densities) don't cover law (a).
- **Regression.** PMMA's nodes empty, and nodes are "allocated from authoring" with no rule for an empty one. On a
  fixed mesh, m'' pulses as each node is consumed. 0.33 mm ÷ (10 g/m²s ÷ 1,190 kg/m³) ≈ 40 s per node (D), the same
  order as the graded features.

*Fix.* Write the shrinking-node rule (FDS remeshes; M). Add node-halving checks on R0 and R1's classes and times for
both laws.

### S9. Contact to a cell's mean T depends on dx
`fire_solid.md::§3` "Conduction"; `§6` straddle and the closed form

The floor's thermal boundary layer is √(αt) ≈ 17–36 mm after 10 minutes (α 5–7×10⁻⁷ m²/s, M), thinner than any
cell. Exchanging with the cell mean gives a resistance of about (dx/2)/k (k = 1.4, M):
- about 14·ΔT W/m² at most at 0.2 m;
- about 56·ΔT at 0.05 m;
- against a closed form of 39·ΔT at 600 s.

That is about 4× across the grids (D), and it breaks CLAUDE.md's "reconstruct… surface model sized in metres". The
straddle test will catch it, but no law in the design can pass it.

*Fix.* Give each contact patch a 1D profile into the cell, sized in metres and coupled to the cell mean at its far
boundary. State the closed-form test's dx.

## 3. NITs

- **N1.** "Runs once per material" contradicts PMMA's forward and reverse fits. Say whether both must pass.
- **N2.** A fit at a range's edge is "reported" with no consequence. Make it a flagged pass or a fail.
- **N3.** A cone spark adds no energy to the sample, so the ledger's "spark's input" is zero or undefined.
- **N4.** m''_ext's 2.7–8.3 is from timber (V7 1), with no PMMA source. PMMA at 50 kW/m² is an envelope of two
  labs (V). Say both.

## 4. Answers to the brief, in short

- **Is the lone-surface model right and sufficient?** The structure is standard: 1D conduction with k(T) and c(T),
  Arrhenius kinetics, char and a back boundary. Five things are wrong or missing:
  - in-depth absorption for black PMMA (B3);
  - the convective loss under flame (S4);
  - the flash-to-sustain transient (B1);
  - PMMA regression (S8);
  - pine's late phase, which needs char oxidation (S5).

  Thresholding the part's area-mean m'' is right: in the cone it is the sample mean the lab measures, and in the
  world it is fixed in metres.
- **Is the held-out scheme honest?** The split is right, but:
  - it leaks through §4.2 (S3);
  - it is about 2.5× underdetermined (S2);
  - it misdefines t_ig (S1).

  It does not pass by construction, but with wide envelopes (PMMA t_ig at 65 is 12–29 s) and a degenerate fit, a pass
  would say little.
- **Ambient convection and re-radiation?** Acceptable for the cone before ignition: MaCFP's inputs use h = 13–15 to
  TMPA (V). That `SOLID_PHASE_ONLY` gas sits at TMPA is M. It is wrong under the flame (S4). In the world, an object
  can never be preheated by its surroundings: at 200 °C inside 200 °C cells it still loses about 4.5 kW/m²
  (2.3 convective + 2.2 radiative, D). Record that in Known gaps.
- **Is the FDS test meaningful?** Yes for conduction and kinetics, once it is redefined as matched gasification
  (B3). No for §4.2: no MaCFP input has a flame.
- **Does anything threshold a mean or depend on dx?**
  - the contact law (S9);
  - the solid's dt, if tied to the heat substeps (S7);
  - law (a) at node scale (S8);
  - the sustain bound taken from a time mean (S3).
