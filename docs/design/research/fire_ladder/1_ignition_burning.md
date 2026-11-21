# Ladder research 1: ignition (R0) and burning (R1) of solid fuels (2026-11-20)

Tags: **V** read by me in the primary source (location given). **S** secondhand. **M** memory, to verify. **D**
derived by me. The D cone numbers come from my scripts (session scratchpad `scripts/cone.py`, `wood2.py`, `hoc.py`),
run on the MaCFP `matl-db` CSVs at `master` on 2026-11-20.

## 0. The findings that matter most

1. **Open multi-lab cone data with raw time series exists for two of the four materials.**
   - MaCFP-2 black cast PMMA: 11 labs at 25 kW/m², 10 at 65.
   - MaCFP-4 Eastern White Pine: 10 labs, 91 tests, 25–75 kW/m², both grain orientations. Its summary is
     final as of 16 Sept 2026.
   - Both are at `github.com/MaCFP/matl-db`. Grade R0/R1 against these first.
2. **The literature's own between-lab spread is large,** wider than the spikes' 15% rule:
   - PMMA t_ig at 25 kW/m²: lab means 76–148 s.
   - Pine first-peak HRR at 50 kW/m²: lab means 161–235 kW/m².
3. **An isolated wood slab is supposed to go out without external flux.**
   - Emberley et al. 2017 (FSJ, CLT paper, "Small Scale Test Results", V): radiata pine self-extinguishes
     below **45 ± 1 kW/m²** external, at **3.7 ± 0.2 g/m²s**.
   - The hot-surface spike's crate F went out with 33–40% of its wood left. That may be correct single-surface
     physics. The closed form in §2.3 agrees.
   - R1 can decide it.
4. **The ignition criterion's headline number is disputed.**
   - MaCFP uses Q̇″ ≥ 24 kW/m², citing Lyon & Quintiere 2007 (V, MaCFP-4 §Time to Ignition).
   - Plathner's 2020 Lund thesis quotes the same paper's average as **66 ± 17 kW/m²** (V, §3.1.2.1).
   - McKinnon used **15** (range 10–20) for cardboard (V, MS thesis 2012, §3.2).
   - I couldn't open Lyon & Quintiere (paywalled).
5. **I found no measured burning data for wax/sawdust fire starters.** Paraffin itself is well characterised.

## 1. Ignition (R0)

### 1.1 The models

- **Thick:** t_ig ≈ (π/4)kρc((T_ig − T∞)/q″)².
  - With losses: t_ig^(−1/2) ≈ C(q″_ext − q″_cr).
  - V: MaCFP-4 Experimental Summary §Critical Heat Flux, citing Quintiere 2006.
  - √(kρc)·ΔT is the thermal response parameter (TRP).
- **Thin:** t_ig = ρcδ(T_ig − T∞)/q″_net, used when the penetration depth exceeds the thickness.
  - The condition is S, from Lyon 1999 (DOT/FAA/AR-99/56) eq. 5. The equation is an unreadable image, so its
    form is M.
- **Critical flux:** q″_cr = εσ(T_ig⁴ − T∞⁴) + h(T_ig − T∞) (V, Lyon 1999 p. 5).
- **Critical mass flux.** The flame attaches, or dies, when m″ crosses m″_cr (Bamford, Crank & Malan 1946).
  - Q̇″_cr = m″_cr·ΔH_c is roughly fuel-independent, per Tewarson and Lyon & Quintiere (V, Plathner §3.1.2.1).
    It fails below ΔH_c ≈ 10 kJ/g (V, Plathner §6.1).
  - m″_cr depends on the setup (V, Plathner §3.3): sample size (PMMA 19.2 g/m²s at 1 cm, 2.0 for larger
    samples), flow, O₂ and flux.
- **Integral model for wood:** Spearpoint & Quintiere 2001 (FSJ 36). It fits kρc and T_ig per species and grain
  and works above about 20 kW/m² (S, abstract). Wood ignited at about 10 kW/m², probably through char oxidation
  (V, that MaCFP-4 cites it for this).
- **Wood specifics** (Babrauskas 2002, JFPE 12:163, S abstract):
  - piloted ignition at 300–365 °C;
  - about 250 °C, glowing first, at the lowest fluxes.
  - Review CHF 12 ± 2 kW/m² (S).
  - Autoignition flux about 25–35 kW/m² (**M**).

### 1.2 Which criterion for a game

Every criterion lives in a near-surface profile about 1 mm deep. No world grid of 0.05–0.2 m resolves that.
FDS (M), Gpyro (M) and ThermaKin all solve a **separate 1D solid model per surface** on its own fine mesh.
ThermaKin's flame boundary condition is triggered by m″_cr (V, McKinnon §3.2). This is CLAUDE.md's "surface model
sized in metres": the 1D mesh is set per material in millimetres, never by the world cell.

- **T_ig:** the simplest, and what the spikes used.
  - It isn't a constant: it rises with flux. Lyon 1999 p. 4 (V) calls it "approximately equal to the peak mass
    loss temperature" under transient heating, which makes it kinetic.
  - It is sensitive to how the 1D mesh resolves the surface gradient.
- **m″_cr: the most defensible.**
  - It integrates over the pyrolysis zone.
  - The same law gives extinction, so R0 and R1 share it.
  - It works for any material with kinetics and ΔH_c.
  - Cost: it needs Arrhenius pyrolysis, and the value is setup-dependent.
- **Recommendation:** one-step Arrhenius pyrolysis in a per-surface 1D model. Piloted ignition at
  m″ ≥ Q̇″_cr/ΔH_c,eff, with Q̇″_cr a cited range (15–24 kW/m² in cone practice; 66 ± 17 disputed).
  - t_ig is then an output to grade.
  - The thick and thin formulas become closed-form tests: high flux, losses off.
  - Autoignition (no pilot) needs its own criterion. That is open.

### 1.3 Datasets

**PMMA (MaCFP-2).** Evonik ACRYLITE cast black 9H01 GT, 100 × 100 × 6 mm (V, MaCFP 2021 Report Part I §1.1).
t_ig at Q̇″ ≥ 24 kW/m² (V, Table 3.5):

| Flux | t_ig, lab means |
|---|---|
| 25 kW/m² | 76–148 s (median 112) |
| 50 kW/m² | 26 and 36 s (2 labs, D) |
| 65 kW/m² | 12–29 s (one flagged set excluded) |

- A t_ig^(−1/2) fit to these medians crosses zero at about **−7 kW/m²** (D).
- The reason: the slab isn't cleanly thick, since 4√(αt) ≈ 4√(0.11 mm²/s × 112 s) ≈ 14 mm against 6 mm (D). It
  also absorbs in depth (V, Linteris NIST TN 1929 abstract).
- Grade t_ig, never an extrapolated CHF.

**White pine (MaCFP-4).** Kiln-dried Pinus strobus from one grove, 25 mm thick, nominal volume 254 cm³ (V, §2).
Parallel grain, lab-mean t_ig (D):

| Flux (kW/m²) | 25 | 30 | 50 | 60 | 75 |
|---|---|---|---|---|---|
| Labs | 2 | 6 | 4 | 6 | 3 |
| t_ig (s) | 70, 190 | 30–52 | 14–23 (BUWfd 3*) | 7–20 (BUWfd 2*) | 4–8 |

\* BUWfd's 2–4 s is implausible: probably a time-zero convention I didn't check.

MaCFP-4 itself (V, §Critical Heat Flux):
- the lab spread is largest at 25 kW/m²;
- perpendicular grain ignites later;
- several labs' extrapolated CHFs come out **negative**, so it calls CHF "not … reliable".

**Cardboard.** McKinnon 2012 (UMD MS thesis, Table 3-1, V; one lab, ±2σ of the mean):
- double-wall corrugated, 7.4 mm, 174 kg/m³ overall; 0.64 mm liners at about 520 kg/m³ (V, §2.1).

| Flux (kW/m²) | 20 | 40 | 60 | 80 |
|---|---|---|---|---|
| t_ig (s) | 56.2 ± 3.4 | 14.2 ± 1.8 | 7.3 ± 0.6 | 5.8 ± 0.6 |
| Peak HRR (kW/m²) | 241 ± 16 | 309 ± 10 | 347 ± 19 | 369 ± 16 |

- Its ThermaKin model predicts t_ig within 2 s (S, C&F 2013 abstract).
- It is layered, not a thin sheet. I found no open single-sheet paper dataset.

## 2. Burning (R1)

### 2.1 Non-charring (PMMA)

**Steady burning:** m″ = q″_net/L_g, with q″_net = q″_ext + q″_flame − q″_cr (V, Lyon 1999 eq. 9).
- L_g = **1.6 kJ/g** from the m″-against-q″ slope (V, Table 4 p. 30, with components). Rhodes reports 2.8 for
  black PMMA (S).
- Linteris (V, TN 1929 abstract): cone-slope "effective" L_g reaches up to 1.3× the true input, depending on the
  model. **L_g is model-dependent.**

**The cone shape** (D, lab means, HKPoly excluded as a 2× outlier):
- **25 kW/m²:** a plateau of 350–570 kW/m², then a back-face rise to 482–719 kW/m² at 230–340 s after ignition.
- **65 kW/m²:** peak 993–1,473 kW/m².
- ΔH_c,eff 24–25 kJ/g (V, Table 3.6).
- The rise needs finite thickness and an insulated back.

### 2.2 Charring wood: the curve

MaCFP-4 (V, §Heat Release Rate): rapid rise; a decrease to a lower, relatively steady value; a second rise as the
back heats; a smouldering tail. Parallel grain (D):

| Flux | Labs / tests | First peak (kW/m², lab means) | Plateau, 250–450 s after t_ig | Second peak (kW/m²), time after t_ig | ΔH_c,eff (kJ/g) | Plateau MLR (g/m²s) |
|---|---|---|---|---|---|---|
| 30 | 6 / 17 | 126–211 | 42–88 | 61–136 at 990–1,610 s | 13.2 | 4.4 |
| 50 | 4 / 15 | 161–235 | 64–100 | 102–170 at 1,020–1,290 s | 16.4 | 5.5 |
| 60 | 6 / 19 | 156–265 | 64–142 | 79–152 | 14.8 | 6.6 |

- **FZJ's runs show no late second peak.** The second peak belongs to the backing, not the wood. MaCFP-4 lists
  backing and holder as key factors (V, Calibration_Data README). R1 must specify the backing.
- **Wood's cone "L_g" is apparent, not intrinsic.**
  - The plateau MLR (25: 3.7, 30: 4.4, 45: 5.9, 50: 5.5, 60: 6.6, 75: 7.2 g/m²s) rises at 0.069 g/m²s per
    kW/m², an apparent **14.6 kJ/g** (D, least squares on lab medians, transient plateau).
  - The intrinsic values are about 1–3: cellulose 2.6 kJ/g of solid (V, Lyon 1999 Table 5); wood 1.8 (M,
    Tewarson).
  - The gap is char insulation plus re-radiation. A model with an intrinsic L_g must *produce* about 10–15 kJ/g
    apparent. That is an R1 check.

### 2.3 The minimal model, and what the spikes lacked

**Per surface, 1D in metres:**
1. finite-slab conduction with a specified back boundary;
2. a pyrolysis front (one-step Arrhenius; the spikes' pinned T_p is a coarser stand-in) at an intrinsic L_g,
   leaving char at χ;
3. a char layer with ρ_c, c_c and k_c(T);
4. a surface balance: q″_ext + q″_fl = εσ(T_s⁴ − T∞⁴) + h(T_s − T∞) + conduction inward (+ char oxidation);
5. ignition and extinction at m″_cr.

This is Spearpoint & Quintiere's 2000 integral model (C&F 123:308, S). FDS, Gpyro and ThermaKin do more (MaCFP-4's
UMD_FSRI set has 14 components, V), but a game needs only items 1–5.

**Closed form (D).** A char surface at 550 °C (823 K) with ε = 0.9 re-radiates
0.9 × 5.67e-8 × (823⁴ − 293⁴) ≈ **23 kW/m²**.
- With the spikes' q″_fl = 25 kW/m² and no external flux, about 2 kW/m² is left to conduct inward.
- That is at most about 1.1 g/m²s at 1.8 kJ/g, below m″_cr = 3.7. **The flame goes out.**
- Emberley measured the same thing: extinction below 45 ± 1 kW/m² external (V). Reports range over 30–45 (S,
  2021 review), 24–57 across species (S), and spruce 43.6 ± 4.7 (S, Arnórsson).
- The cone flame's own flux onto a 0.1 m sample is modest: cardboard's mean was 17.2 kW/m² at 20 kW/m² external
  and 29.9 at 60, modelled as 30 (V, McKinnon §3.1.3).

**So no single R1 ingredient is obviously missing.**
- The bed spike pinned T_p and had no item 4, so it burned too well.
- The hot spike added items 3 and 4 and went out, as an isolated slab should.

**What R1 decides.** Run the same surface model as a cone test and require two things:
1. t_ig, first peak, plateau and second peak at 30, 50 and 60 kW/m² within the MaCFP-4 envelope;
2. extinction when the external flux steps below the 24–57 kW/m² band, at m″ ≈ 3.5–4 g/m²s.

If both pass, the crate failure is crib **feedback geometry**, an R3/R4 matter (neighbour and flame-volume
radiation replacing the cone heater). If not, the char model is wrong.

**One parameter to watch: k_c.**
- The hot spike used 0.10 W/mK; the MaCFP-4 UCB fit uses **0.15–0.30** (V, `Wood_UCB-CONST-1.json`).
- These are effective values that include radiation across pores. Too low a k_c starves the front.

## 3. Wax, fire starters, melting

**Paraffin** (V, Hamins, Bundy & Dillon 2005, JFPE 15:265, Table 1, a compilation of cited sources):
- melting point 48–68 °C; L_f 0.147–0.163 kJ/g;
- c 2.60 (solid) and 2.98 (liquid) kJ/kgK; k 0.23 W/mK; ρ 865–913 kg/m³;
- flash point 204–271 °C, fire point 238–263 °C, boiling 350–430 °C;
- net ΔH_c 43.1 MJ/kg.

Measured in the same paper (V):
- cone ΔH_c,eff 43.8 ± 0.7 kJ/g;
- **peak HRR 800–4,150 kW/m²** for 8 mm wax discs at 10–40 kW/m², a pool fire;
- candle mass loss rate 0.105 g/min, about **77 W** (D). Steady burning takes 12–15 min.

**The mechanism:**
- **A candle:** its flame melts a pool, and the wick lifts liquid by capillarity to the flame. The rate is set by
  the wick (39 mm² burning area, V), not the pool.
- **A bare wax block:** melts, pools and burns as a pool fire at roughly 4–20× wood's HRR per area (D).
- **A sawdust/wax starter:** the matrix is the wick. Capillarity holds the molten wax in the pores, and it burns
  from a fixed surface; the cellulose then chars.
  - This is the accelerant spike's soaked-wood case with a fusion step added.
  - **No published HRR, duration or ignition data found.** Only composition notes: "fire starters contain 50% or
    more paraffin" (S, cotton.org firelog paper); patent US 8,007,550.

**Minimal physics:**
- a latent heat of fusion in the 1D solid model;
- a retention rule: wax is held where a porous matrix holds it, and drains to a pool otherwise;
- the accelerant spike's evaporating-liquid law.

**For cells and pools.** Melting is the first case where a solid cell's mass must *leave* as liquid. It needs:
- a cited drainage criterion (none found);
- mass-conserving transfer to the pool system;
- a pool's burning area equal to its footprint, while a wicked liquid burns on the matrix surface.

Without melting, a wax block burns like wood (an order of magnitude off); with free drainage, a starter empties.

## 4. The property set

Configuration inputs, **not** material properties: q″_fl (depends on size and geometry), h, and the backing.

| Property (unit) | PMMA (black cast) | Softwood (white pine) | Cardboard (double-wall) | Paraffin | Kind |
|---|---|---|---|---|---|
| ρ (kg/m³) | 1,190 **M** | ≈380 (V UCB fit; D 315–480 from masses). Spikes: 600 | 174; liner 520 (V) | 865–913 (V) | measured |
| k (W/mK) | 0.21 (V, MaCFP T3.7) | 0.10–0.12 ⊥ (V UCB; Wood Handbook) | inverse-fitted (McKinnon §4.2) | 0.23 (V) | measured, or fitted |
| c (J/kgK) | ρc ≈ 1.9 MJ/m³K (D: k/α, α 0.10–0.12 mm²/s, V T3.8) | 1,236 at 293 K to 2,630 at 653 K (V, Wood Handbook) | DSC (McKinnon §4) | 2,604 / 2,981 (V) | measured |
| ε | 0.85–0.95 **M** | virgin 0.6–0.85; char 0.80 (V, UCB fit) | 0.95 tested (V) | — | measured or fitted |
| Kinetics | E ≈ 160 kJ/mol (V, Lyon T5) | multi-step fits only | multi-step (McKinnon 2013) | n/a | **fitted** |
| T_ig (°C) | ~300–330 **M**; TGA peak 398 (V, Lyon T2) | 300–365 piloted; ~250 glowing (S) | — | fire point 238–263 (V) | flux-dependent |
| m″_cr, ignition (g/m²s) | 2.0; plastics 1.9–3.2 (V, Plathner §3.3) | plywood 2.0–3.8 (V, Plathner) | ≈1.0 (D: 15 ÷ 14.5) | — | setup-dependent |
| m″, extinction (g/m²s) | — | 3.7 ± 0.2 (V, Emberley) | — | — | measured |
| ΔH_c,eff (kJ/g) | 24–25 (V) | 13–16.5 (D) | 13.2–14.8 flaming (V) | 43.8 (V) | measured |
| L_g intrinsic (kJ/g) | 1.6 (V); 2.8 (S) | 1.8 **M**; cellulose 2.6 (V) | DSC (McKinnon) | L_f 0.15–0.16 (V); L_v not found | **effective; model-dependent** |
| χ, char yield | ≈0 (V, Lyon T2: 2%) | 0.25 (V, Baker via spikes) | TGA | 0 | condition-dependent |
| k_c (W/mK) | — | 0.15–0.30 (V, fit); 0.10 in the spike | fitted | — | **fitted** |
| T_melt (°C) | — | — | — | 48–68 (V) | measured |

**The fitted rows (kinetics, L_g, k_c, char ε) must be re-fitted by our own model to the R1 data,** never copied:
- MaCFP lists 13+ different property sets for the one PMMA;
- Linteris shows the dependence directly, up to 1.3× on L_g.

## 5. What to grade against

The datasets are §1.3 and §2 (R0: t_ig; R1: the curve features), plus Emberley's extinction.

**The tolerance the literature achieves:**
- **Within a lab:** ASTM E1354-23 repeatability, as quoted by MaCFP-4 (V; the ASTM text itself is S):
  r = 4.1 + 0.125·t_ig s, and 1.23 + 0.050·ΔH_c kJ/g. That's ±18 s at 112 s.
  - Only 46% of MaCFP-4 wood series met it for t_ig, and 44% for ΔH_c (V).
- **Between labs:**
  - PMMA t_ig at 25 kW/m²: ±32% about the median (D).
  - Pine first peak at 50 kW/m²: ±19% (D).
  - Pine ranges are about twice PMMA's (V).
- **The proposal:**
  - Pass when the model lies inside the min-to-max envelope of lab means, per feature and per flux.
  - Grade features, not pointwise curves. Time zero and baselines differ between labs (V, MaCFP-4 on the Rouen
    resubmission).

## 6. Recommendations

**(a) A model per rung:**
- **R0:** a per-surface 1D model with finite thickness, its back boundary, re-radiation and convection, and
  one-step Arrhenius pyrolysis. Ignition at m″ ≥ Q̇″_cr/ΔH_c,eff.
  - Closed-form tests: the thick and thin t_ig formulas.
  - Basis: Lyon 1999; MaCFP-4; Plathner 2020; McKinnon 2012.
- **R1:** R0 plus the char layer, q″_fl as an input (about 15–30 kW/m² at cone scale) and extinction at m″_cr.
  - Order: PMMA, then pine, then cardboard, then the flux step-down extinction test.
  - Basis: Spearpoint & Quintiere 2000; Emberley 2017.
- **Wax/starter:** off R0/R1 until data exists. Then it is the accelerant law plus fusion plus retention.

**(b) The property table:** §4.

**(c) Open questions:**
1. **Q̇″_cr, 24 or 66 ± 17?** Read Lyon & Quintiere 2007 (C&F 151:551) and Dietenberger, Hasburgh & Yedinak 2021
   (library access).
2. **Unpiloted ignition of wood** (radiant ignition of a neighbour): Babrauskas's *Ignition Handbook*, not read.
3. **Fire starters:** a pre-registered bench measurement (mass against time on a scale), or the firelog/CPSC
   literature.
4. **My MaCFP-4 reductions against the repo's generated tables** (`Cone_Values.tex`,
   `Cone_MaCFP2_Range_Comparison.tex`): reconcile before pre-registering.
5. **The BUWfd time zero and FZJ's missing second peak:** read their READMEs.
6. **Our wood:** 600 kg/m³ against the pine's 380. Make the scene match the species graded against.
7. **A single-sheet paper dataset** for a true thermally thin case.
8. **The M rows:** PMMA ρ, ε and T_ig; wood L_g; the thin formula's form; the autoignition flux (Tewarson, SFPE
   Handbook).
