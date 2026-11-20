# Ladder research 2: flame spread and flame-volume heat feedback (R2–R4)

2026-11-20. Research only; no repository file was edited. Tags: **V** read by me in the primary source, **S**
secondhand, **M** from memory (to verify), **D** derived by me. Derivations use ρ∞c_pT∞√g = 1,110 kW m^-5/2.

## 0. Headline

1. **Our flames can't be resolved on the gas grid.** A 1–2 kW stick or torch flame has D* = 0.06–0.08 m (D, FDS
   eq. 6.2), so D*/δx is 0.3–0.4 at 0.2 m and 1.2–1.6 at 0.05 m. FDS validation runs mostly sit at D*/δx ≈ 3–19,
   and FDS warns against taking any of them as an acceptable minimum (V, FDS 6.9.1 User's Guide §6.3.6 p. 42;
   Validation Guide (VG) Table 3.49).
2. **FDS isn't grid-converged on spread rate even with the flame resolved.**
   - **PMMA parallel panels:** the 5 mm grid peaks minutes before the 2 cm grid and the test (VG Fig. 14.40).
   - **UMD SBI PMMA:** 4, 2 and 1 cm all reach only about 100–190 kW against 285 kW measured at 190 s
     (VG Fig. 14.41).
   - **TN 2102 single crib:** the peak is about 800, 440 and 330 kW at 8, 4 and 2 cm, against about 390 kW
     measured (VG Fig. 14.22).
   - (Figures V; values D, read off the plots.) The class held every time; the rate didn't.
3. **The literature backs the hot-surface spike's diagnosis.**
   - Fine fuels "will not ignite solely from radiation even at … <∼80 kW·m−2"; flame and hot-gas contact ignites
     them (V, Finney et al. 2015, PNAS 112:9833, pp. 1, 3).
   - In wooden-dowel arrays, upward spread is convective and sideways spread radiative (V, Jiang et al. 2019,
     PCI 37:3767).
   - A flame that only leaks χ_r·q''_f into the bed misses the dominant path: the flame body touching fuel.
4. **The minimal cited model that fits D25 is a sub-grid flame object sized in metres.**
   - Height from a correlation; flux onto surfaces from a correlation in x/x_f (impingement in the flame, a tail
     above it, view-factor radiation outside).
   - Evaluated on fuel surfaces in metres and deposited by overlap.
   - It is cheap and grid-independent in geometry. **The risk is the flux→pyrolysis→flame-size loop near the spread
     threshold.**
5. **R4 has an oracle (NIST TN 2102 Test 13, a 56×56×46 cm crib), but not for the crate.** Nothing I found grades a
   2 kW torch on a 0.6 m crate of 20 mm slats, and real cribs are lit with far larger pilots.

## 1. R2: single-surface spread

### 1.1 Opposed flow (downward, lateral)

- **LIFT / ASTM E1321 (Quintiere & Harkleroad, NBSIR 84-2943):** V = Φ / [kρc (T_ig − T_s)²] for
  T_s,min < T_s < T_ig (V, restated as eq. 42 of DOT/FAA/CT-85/2 p. 21).
  - Φ comes from de Ris and Fernandez-Pello: Φ = V_a kρc (T_f − T_ig)² f(Damköhler) (V, NBSIR 84-2943 eq. 14,
    p. 20).
  - All three parameters are effective, "not fundamental" (V, p. 22).

Values (V, NBSIR 84-2943 Table 2, OCR of the scan):

| Material | T_ig (°C) | kρc ((kW/m²K)²s) | Φ (kW²/m³) | T_s,min (°C) |
|---|---|---|---|---|
| PMMA Type G, 12.7 mm | 378 | 1.02 | 14.43 | 90 |
| Douglas fir particle board, 12.7 mm | 382 | 0.94 | 12.75 | 210 |
| Plywood, plain, 12.7 mm | 390 | 0.54 | 12.91 | 120 |

- **The predictions (D).**
  - At T_s = 20 °C every row is below T_s,min: **no opposed-flow spread on cold thick wood or PMMA.**
  - Preheated plywood spreads at 1.2 mm/s at 250 °C and 3.0 mm/s at 300 °C; particle board at 0.8 and 2.0 mm/s.
  - A sharp, pre-registerable class result.
- **Thin fuels.** de Ris's thin-fuel formula (V ∝ k_g(T_f − T_ig)/[ρcτ(T_ig − T∞)], **M**) is why paper spreads
  downward and slabs don't. It needs τ, which the bed already carries.

### 1.2 Concurrent (upward) spread

- **Sibulkin & Kim:** V ≈ (q''_f)² δ_f / [kρc (T_ig − T_s)²], with δ_f the flame length beyond the pyrolysis zone
  (V, NBSIR 84-2943 eq. 15, p. 22). Everything then hangs on the flame height and the wall flux ahead of the front.
- **Flame height (V, DOT/FAA/CT-85/2, Quintiere, Harkleroad & Hasemi 1985, eq. 33 and p. 13).**
  - x_f = 4.65 [E'/(ρc_pT√g)]^{2/3} (Delichatsios); Hasemi's coefficient is 6.1. Tested for x_f of 0.3–1.4 m, with
    "considerable scatter".
  - In metres: 0.043–0.057·E'^{2/3}, so 5 kW/m gives about 0.13 m and 30 kW/m about 0.42 m (D).
- **Wall flux (V, the same report).**
  - In the flame, 10 to just under 30 kW/m², with "no universal maximum" (p. 19). Beyond the flame it falls as
    roughly x^-2.4 (p. 18).
  - The radiative share is estimated at ≥50% (p. 20).
- **Leventon (UMD PhD 2016, abstract V).** The flame flux is a function of burning rate alone. It predicts seven
  other polymers to 3.9 kW/m², "about 10–15% of peak", so the peaks are about 26–39 kW/m² (D).
  - Coupled to ThermaKin2D, it is the minimal "flame as a correlation" model.
- **Saito–Quintiere–Williams (1985) and Saito et al. (1987) on wood:** cited but not opened (**M**).

### 1.3 What a grid sim could carry

- **The model.** Each burning surface patch has an E' from its pyrolysis. Its flame is a sheet of height x_f(E')
  along the surface in the buoyant direction (tilted by the draught), putting q''(x/x_f) on the surface ahead.
  - Opposed spread emerges at the flame foot. No separate law is needed, and LIFT grades it.
  - It must live on surfaces in metres. Every lab specimen (5×20 cm PMMA, 3.2 mm dowels, 20 mm slats) is below
    the 0.4 m thin-feature rule, so sub-cell, as the D30 bed already is.
- **Grading data.**
  - LIFT Table 2 (V).
  - Wall-flame height and flux (DOT/FAA/CT-85/2; Leventon).
  - The FDS-validated PMMA upward sets, for class only.
  - Wood upward-spread numbers aren't in hand (Saito 1987; Mangs & Hostikka on birch, cited in VG §2.2.7: **S**).

## 2. R3: flame volumes onto other bodies

### 2.1 Radiation models

- **Point source:** q'' = χ_r Q/(4πr²). It is "accurate in the far-field" and conservative "within a few fire
  diameters" (V, NISTIR 6546 eq. 7, p. 2). CFAST uses it and states the same limit (V, CFAST 7.7.7 Tech Ref §1).
- **Solid flame:** q'' = F τ ε_f E_f, with view factor F onto a cylinder of the flame's height and width (V,
  NISTIR 6546 eq. 1).
- **Heskestad flame height:** L = 0.23 Q^{2/5} − 1.02 D (V, as applied in NISTIR 6546; 0.235 is the usual
  coefficient, **M**).
  - At D = 2 cm, 1 kW gives 0.21 m and 2 kW 0.29 m (D).
  - **Caveat:** it was fitted to pool and burner fires. Kilowatt stick flames and momentum-driven torches are
    extrapolations (fitted range not verified, **M**).
- **R3 is near-field.** The point source gives 9.5 kW/m² at 5 cm and 2.4 kW/m² at 10 cm for 1 kW, χ_r = 0.3 (D).
  - At those gaps the target sits in or beside the flame. Babrauskas: near the source convection adds 10–20%,
    "and in the immediate vicinity … can even dominate" (V, NBSIR 81-2271 p. 9).
  - The minimum is a solid flame with an impingement zone.

### 2.2 Item-to-item ignition

- **Babrauskas, "Will the second item ignite?"** (NBSIR 81-2271; FSJ 4:281). Furniture gave up to about 80 kW/m² at
  0.05 m. 40 kW/m² was never seen beyond 0.44 m, nor 20 kW/m² beyond 0.88 m (V, p. 27).
  - The burning item "does not act as a point source" near-field (V, p. 11).
  - Ignitability classes are 10, 20 and 40 kW/m² (V).
  - Its distance correlation is empirical, from furniture: an R3 sanity band at 0.5–1 m only.

### 2.3 Gap experiments, and kindling

- **Jiang, Zhao, Tang, Miller, Sun & Gollner 2019 (PCI 37:3767–3774): the best R3 oracle found.**
  - Birch dowels 3.2 mm in diameter and 31.8 mm long, at spacings of 0.75, 0.875 and 1.5 cm, lit from one dowel
    with a butane lighter (V, §3).
  - "For the 1.5 cm spacing, the gap was too large for horizontal flame spread"; vertical spread occurred at every
    spacing (V, abstract).
  - Their criterion is a race: burnout time t_b = 13.6 s against the neighbour's radiative ignition time
    t_i = 19.8 s at 1.5 cm (V, §4–5). **A class criterion with a margin, as the resolution rule wants.**
- **Finney et al. 2015:** 1.27 mm cardboard combs. Preheat radiation was "generally below ∼30 kW·m−2", too low
  within flame residence times of 2–35 s; flame contact did the igniting (V, pp. 3–5).
- **Vogel & Williams 1970, matchstick arrays:** the convective theory Jiang cites (**S**).
- **Firestarter beside a stick, and 20 mm stick beside stick: no cited experiment found.** Searched: firestarter,
  kindling, wax starter, stick spacing, item-to-item.
  - Jiang's dowels are thermally thin (δ_T ≈ 4.9 mm by their estimate), so they don't transfer to 20 mm sticks.
  - **R3 with 20 mm sticks has no oracle.**

## 3. R4: cribs

### 3.1 Correlations and regimes

- **Gross's two regimes (V, McAllister & Finney 2016, Fire Technol. 52:1035, pp. 1035–1036).**
  - Loosely packed: the rate is "governed by heat and mass transfer processes near the surfaces" and is
    "independent of the porosity".
  - Densely packed: it is "limited by availability of oxidizer within the fuel bed".
- **Heskestad.** Porosity φ = s^{1/2}b^{1/2}A_v/A_s (cm), and 10³R/(A_s b^{-1/2}) = 1 − exp(−50φ) (R in g/s,
  lengths in cm; V, eq. 2, "not explicitly given" by Heskestad). The transition is near φ ≈ 0.05 cm (**S**).
- **Wind.** 0.7 m/s changed the rate by +6.5% to +61.5% for 12.7 mm sticks and −37% to −61% for 6.4 mm sticks
  (V, abstract). Alley draughts matter at about ×2.
- **Not opened (M):** Block, Thomas, McCarter & Broido, and Delichatsios 1976 (C&F 27:267) on crib fire growth.
- **The crib data I could read measure burning rate, not spread.** Gross lit whole piles over heptane, and
  McAllister dunked cribs in alcohol (V).

### 3.2 The crate as a crib (D, assumptions stated)

- **The layout assumed:** 2 cm square sticks at volume fraction 0.25 (s = 3b = 6 cm), 30 layers in 0.6 m.
  A_v/A_s = 0.5625/30.
  - φ = √12 × 0.01875 = **0.065 cm**: just loosely packed, factor 0.96, surface-controlled.
- **Fully involved:** A_s (four faces) = 10.8 m², so R ≈ **73 g/s**, about 0.9–1.2 MW (12.4–16.7 MJ/kg); 32.4 kg
  burns in about 7 min.
  - The bed's σ = 25 m²/m³ counts two faces (bed.md), which halves this.
  - A slatted crate isn't a crib. This is what a fully involved crib at the crate's loading does, not whether a
    torch involves it.
- **The TN 2102 Test 13 cross-check is inconclusive.**
  - The crib: 39.4 kg, 3.8 cm sticks, peak about 390 kW (V, char_oxidation.md §2.1); ΔH = 16.7 MJ/kg (V, VG
    Table 3.27).
  - The fully ventilated Heskestad rate is 42–48 g/s, assuming 450–550 kg/m³ (**M**), i.e. 520–800 kW.
  - The measured/ideal ratio is therefore 0.5–0.75. Without the crib's layout I can't tell whether that is the
    porosity factor or an error.

### 3.3 Oracle

- **TN 2102 Test 13.**
  - Public HRR, already analysed in char_oxidation.md; residue 0.053 ± 0.034 (V, VG Table 3.27).
  - Ignited with acetone-soaked cotton rope plus crinkle paper (V, VG §3.59), 0.75 kg of it in Test 13 (V,
    char_oxidation.md).
- **The fair R4 test** reproduces that crib and pilot. The torch-lit crate is an ungraded prediction.

## 4. How fire codes represent sub-grid flames

| Approach | Flame | Grid-independent at 0.05–0.2 m? | Needs from us |
|---|---|---|---|
| **FDS LES** | Mixing-limited fast chemistry with rate set by τ_mix (V, Tech Ref §2.6.1). Where χ_r q''' > 10 kW/m³, emission is rescaled so the flame radiates χ_r of its HRR (V, eq. 6.10). Unresolved fuel area is fixed with `AREA_MULTIPLIER` (V, UG §9.1.2), a calibration | **No.** It needs δx ≈ 6–8 mm for our flames (D, D*/δx ≈ 10), and the rate still isn't converged (§0) | A full gas solver: infeasible for a game server |
| **FDS particle and boundary-fuel vegetation** (V, UG §17) | Fuel as particles or a porous layer; flame on the gas grid | Same limit. Its cribs at 2–8 cm differ 2.4× in peak | Our bed *is* the boundary-fuel model minus its gas-phase flame: that gap is our failure |
| **CFAST** | Prescribed-HRR objects ignited "at a prescribed time, temperature or heat flux"; point-source radiation; "does not predict fire growth" (V, Tech Ref §1–2) | Trivially | A target-ignition rule only |
| **Rothermel / FARSITE / level set** | Empirical rate of spread (R = I_Rξ(1+φ_w+φ_s)/(ρ_bεQ_ig), form **M**; INT-115 scope "a continuous stratum … contiguous to the ground", V). The level set uses "purely empirical rules" (V, UG §17) | Yes: the rate is an input | A rate per fuel. Breaks T18, and has no slab or crate fuel |
| **Lumped flame sheet or volume** (LIFT-based spread models; Leventon–Stoliarov) | Geometry and flux from correlations in E' and x/x_f | Yes, if evaluated in metres and deposited by overlap | Pyrolysis per patch (we have it), a flame object per burning cluster, and view factors |

Only the last row is grid-independent by construction, keeps spread an outcome of heat transfer (T18) and is
affordable.

## 5. Recommendation

### 5.1 Model and cost

- **R2: a flame-sheet object per burning surface patch.**
  - x_f(E') from Delichatsios or Hasemi; q''(x/x_f) from DOT/FAA/CT-85/2 or Leventon.
  - Cost: O(patches × the elements within about 2x_f), analytic.
  - Gaps: a cited *wood* wall-flame flux profile (particle board is in DOT/FAA/CT-85/2), and the in-flame flux onto
    char.
- **R3: the same object as a solid flame.**
  - Heskestad height (flagged out of range), an impingement zone at 10–30 kW/m², and view-factor radiation outside
    it, normalized to χ_r·Q.
  - Cost: view factors per flame–target pair, cacheable while static.
- **R4: the same objects inside the bed.**
  - Surfaces inside a flame get the in-flame flux. That is the crib heat feedback the hot-surface spike says the
    char layer needs.
  - Check the fully involved rate against Heskestad eq. 2 and the time history against TN 2102.
  - **Don't make the crib correlation the burning law.** It would replace heat transfer, which T18 forbids.

### 5.2 Risk

- **Geometry isn't the risk.** A flame in metres, deposited by overlap, gives each grid the same flux integral.
- **The loop is.** Flux → pyrolysis → E' → x_f → flux. Near threshold, a small grid-dependent pyrolysis error flips
  the class; Jiang's race (13.6 against 19.8 s) shows how thin the margin is.
  - Gate with CLAUDE.md's band and outcome margin, and choose scenarios away from the threshold.
- **Flame merging.** Neighbouring patches' flames merge, so E' must be clustered by connected burning area in
  metres, never by cell. No cited merging model was opened (**M**).
- **The bed.** In-flame flux onto statistically placed surfaces (σ, φ) needs a cited in-crib flux, and I found none
  to verify. McAllister mentions Tewarson & Pion's "ideal burning rate" (p. 1041) as a related bound.

### 5.3 Pre-registered pass criteria (suggested)

- **R2a, opposed flow.**
  - A 12.7 mm plywood slab at 20 °C has no sustained downward spread (LIFT T_s,min = 120 °C).
  - Preheated to 250 and 300 °C it spreads, at 1.2 and 3.0 mm/s within ×2.
  - Same class on all grids.
- **R2b, upward.**
  - A base-lit vertical PMMA or particle-board slab spreads upward and accelerates.
  - The flame height lies within 0.043–0.057·E'^{2/3}, and the wall flux peaks at 10–30 kW/m².
  - The rate isn't graded across grids (FDS fails that test).
- **R3, near field.**
  - Reproduce Jiang's class: sideways spread at 0.75 cm, none at 1.5 cm, upward at both. This needs a sub-cell
    discrete element.
  - Otherwise grade only the t_b-against-t_i race with the cited properties.
  - Firestarter-to-stick: class only, or new data.
- **R3, far field.** A 50–100 kW item's irradiance falls inside Babrauskas's envelope.
- **R4.**
  - A TN 2102 crib with its pilot burns to ≤10% residue (class).
  - Peak HRR within ×1.5 of 390 kW and time to peak within ±40% of 23 min, on all grids. FDS ranged 0.85–2× on
    peak.
  - The torch-lit crate is reported, not graded.

## 6. Thin evidence and disagreements

- **No data for 20 mm sticks at gaps or for firestarter-to-stick.** The dowels are thermally thin.
- **No opened numbers for upward spread on wood** (Saito 1987, Mangs & Hostikka: S/M).
- **The wall-flame flux form is disputed.** Quintiere et al. find "no universal maximum"; Leventon makes it a
  function of burning rate. Both give 10–40 kW/m².
- **Finney and Jiang don't conflict.** Finney has convection dominating for fine fuels; Jiang has radiation driving
  sideways spread. The direction relative to the flame decides.
- **Heskestad's flame height and the crib correlations are empirical.** Small or jet flames and slatted crates are
  outside their fitted range.
- **Not opened:** SFPE Handbook, Drysdale, Quintiere's *Fundamentals*, Delichatsios 1976, the FRN crib notes. Any
  value from them is M.

## Sources

FDS 6.9.1 User's Guide, Technical Reference and Validation Guide (github.com/firemodels/fds, release FDS-6.9.1);
CFAST 7.7.7 Technical Reference (github.com/firemodels/cfast); NBSIR 84-2943; DOT/FAA/CT-85/2
(rosap.ntl.bts.gov/view/dot/92629); NBSIR 81-2271; NISTIR 6546 (all nvlpubs.nist.gov Legacy IR); McAllister &
Finney 2016 (fs.usda.gov rmrs_2015_mcallister_s001.pdf); Finney et al. 2015 (Treesearch 48668); Jiang et al. 2019
(par.nsf.gov/servlets/purl/10089266); Leventon 2016 (drum.lib.umd.edu/handle/1903/18203, abstract); Rothermel
INT-115 (fs.usda.gov/rm/pubs_int/int_rp115.pdf); Gross 1962, J. Res. NBS 66C:99.
