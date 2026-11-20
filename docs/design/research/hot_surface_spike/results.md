# Hot-surface spike: results (2026-11-20)

**Outcome 5 of the pre-registration's §4: the hypothesis is false.** It also carries a second miss the
pre-registration made a T13 trigger: de-pinning breaks sustain in the fully lit crate (C_F).

**Spread.** Burning surfaces got their cited char-surface temperature (they burn at 530–550 °C instead of 380 °C),
and flame gas got its cited ceiling (873 °C). Neither crate spread:
- the bare crate S lights only the 0.031 m² under the torch, λ_max = 0.0058 on every grid;
- the soaked crate K reaches λ_max = 0.0174 at 0.05 m, against 0.0129 in the accelerant spike;
- the in-cell contact arm H2 doesn't change that (S 0.0058; K 0.0058 / 0.0179, and K at 0.05 m did not complete, §3.2);
- no range end changes any class.

**Sustain.** The fully lit crate F, which passed 1a in `bed.md` (0.6% of the wood left), now goes out at
522 / 478 / 466 s with **33 / 39 / 40% of its wood unburnt**. The char layer insulates the pyrolysis front below the
flaming limit, as §0 warned.

**Back on the T13 path:** yes, on three counts:
- B1, B2 and C miss in S and K at nominal on the 0.05 m reference;
- C_F misses;
- D1 passes (every class is the same on every grid), so this is not a resolution artifact.

**What it means (§4, outcome 5).** The two spikes' failure was not one simplification:
- **The gas half was inert.** With the cap lifted, the gas leaving a small fire's cell is limited by that cell's own
  heat release. The S disc's exit gas never got above 295 °C, so the cap never bound.
- **The surface half made the small fires weaker, not stronger.** The S disc's flames now die 7 s after the torch
  stops, instead of at 1,042 s.

Option 1 is now the larger research job: a cited model of flames as volumes that heat neighbouring fuel and feed
heat back onto charring surfaces in a crib. Option 3 is the realistic Phase 1 path. Section 6 sets out what this
does and doesn't show.

The code is in `spikes/physics/hot/`:
- `hotbed.py` subclasses `accelerant/wetbed.py::WetBed`. The parents' code and committed results are untouched.
- `hotsim.py` and `hot_run.py` run one scenario. `analyze.py` grades every run (`results/analysis.txt`).
- `closed_form.py` is E3, and `identity.py` is E4(ii).
- `results/*.json`, `closed_form.txt` and `identity.txt` are committed beside the code. The `*.npz` arrays are
  ignored and regenerated.

The criteria are `preregistration.md`'s (commit 1c58b75, SHA-256 7a18a130…d236), unchanged.

## Verdicts

H1 nominal; 0.2 / 0.1 / 0.05 m.

| # | Criterion (threshold as registered) | Result | Verdict |
|---|---|---|---|
| B1 | S, K: λ_max ≥ 0.90 | S 0.0058 / 0.0058 / 0.0058. K 0.0058 / 0.0058 / 0.0174. Spread class "none" (< 0.10) everywhere | **MISS** |
| B2 | S: max λ_w ≥ 0.90. K: λ_w(t_L95) ≥ 0.90 | S λ_w 0.0058 on all grids. K: t_L95 never occurs (≥ 98.7% of the kerosene stays in the wood); λ_w ≤ 0.0119 | **MISS** |
| C | Flame-out after the pilot (and t_L95), virgin wood ≤ 5% | S: flame-out 607.0 s on every grid, wood left 99.8%. K: 497.0 / 498.0 / 1,055.0 s, wood left 99.5 / 99.5 / 99.2%; no t_L95 | **MISS** |
| C_F | F: virgin wood at flame-out ≤ 5% | Flame-out 522.5 / 478.5 / 466.5 s with 32.8 / 38.7 / 40.5% of the wood left. `bed.md` F: 449 / 575 / 770 s, 0.6% left | **MISS** |
| D1 | Classes of B1, B2, C, C_F and the spread class equal on all grids | S (MISS, MISS, MISS, none), K the same, F (C_F MISS, spread), on every grid. The 817 °C deviation also agrees on every grid; H2 agrees on every grid it completed (K2 at 0.05 m did not complete, §3.2) | **PASS** |
| D2 | 2a rule at 15% on t_ignite, t_B, flame-out, t_L95; λ_max, λ_w at 0.1 m within 0.05 of 0.05 m | t_ignite and t_B don't exist (flaming never reaches 0.1 m² in S or K), so they are a miss as registered. S flame-out 607 / 607 / 607 passes. K flame-out 497 / 498 / 1,055: e₀.₁ = −557 s against tol 158, a miss. λ and λ_w pass (largest gap 0.012, K) | **MISS** |
| D3 | p > 0.5 for each D2 time | S flame-out: zero differences, p undefined. K flame-out: p = −9.1. Others missing. (F flame-out, not a D2 time for F: p = 1.87, Richardson e₀.₁ = +16.5 s, the first observed order that passes in three spikes) | **MISS** |
| E1 | Ledger closes to 1% of release at every step | Worst 2.2 × 10⁻¹³ over all 84 non-zero-change runs | **PASS** |
| E2 | Deleting `removed_with_mass`, `open_air_draught`, `plume_convective`, Δskins each turns E1 red in ≥ 1 H1 run | Nominal 0.1 m: 5.6–14%, 33–51%, 0.1% (S) to 38% (F), and 21–93% of release. All four red | **PASS** |
| E3 | Four closed forms | (i) Steady T_c and m'' equal the bisection roots at all 8 points to the printed 0.01 K and 0.001 g/m²s (tolerances 0.5 K, 0.1%); they reproduce the §0 table. (ii) The front flux is exactly 0 at T_c ≤ T_f. (iii) Gas exit equals the closed form to 10⁻¹² relative on both branches. (iv) The Mz cap equals McCaffrey's ΔT in all three regions (6 points) | **PASS** |
| E4 | (i) Disabled terms reproduce 7 committed digests; (ii) identical state before the first flame | (i) Every digest equal: bed S_nom_02 462917f4…, S_nom_01 74465ca0…, F_nom_02 75f97068…, F_nom_01 bcfc8eab…, B_nom_01 2baffcf1…; accelerant N_02 93ac5d79…, N_01 b382b46e…. (ii) S: 830 identical steps on every grid, first flame at 415.5 s in both. K: 94 identical steps, first flame at 47.5 s in both | **PASS** |
| E5 | Rerun bit-identical; 10× substeps keeps classes (S, K at 0.1 m) | Digests equal (S b46620a1…, K 1be5af54…). 10×: same classes; λ unchanged; flame-out 607.0 / 607.0 s (S), 499.0 / 498.0 s (K) | **PASS** |
| G | Each of 12 ends keeps nominal's classes (S, K, F at 0.1 m) | All 36 runs keep their classes. Three ends change the *mechanism* (§3.4) | **PASS** |

**Reported, for the T13 reading:**
- H2 never spreads in any run that completed; K2 at 0.05 m did not complete (§3.2).
- The O₂ label applies to no B1 pass, because none exists. F's flaming O₂ demand exceeds the draught's supply for
  29–30% of its flaming time, so F's own result is O₂-unverified in that sense.
- Glow appears in F as a side effect (§3.5).

## 1. What was built, and the deviations

The model is preregistration §1, with no constant moved:
- **The char layer.** Iw's skin carries T_c, loses k_c(T_c − T_f)/δ_c to the front, and gasifies that flux at L_g
  (`hotbed.py::_step_iw`).
- **The flame gas.** A flaming cell's gas is heated toward T_fl within its plume budget (`_draught`, with
  `_cap_column` for Mz). Its buoyancy temperature is the mean of inlet and outlet.
- **H2.** `_contact` adds the exchange between a flaming cell's gas and its own unlit and non-flaming parts.

With the switches off, every override calls the parent (E4(i)).

**§6 verification, before any graded run.** Each S or M row was rechecked:

| Row | Registered | Found | Final |
|---|---|---|---|
| Heskestad's tip criterion | S (via Babrauskas) | Heskestad 1997 (FSS 5:427, PDF read): "the mean flame height of pool fires … corresponds to a temperature rise on the plume axis of 500 K" | **V**, unchanged |
| McCaffrey's burner and Q | M | Natural gas, 0.30 m square porous refractory burner (p. 3); Q = 14.4, 21.7, 33.0, 44.9, 57.5 kW (Table 1) | **V** |
| McCaffrey's flame-region ΔT | D: 853 K from κ = 6.8, C = 0.9 | **Table 1 measured 791–807 °C, weighted average 797 °C.** The registered 853 K uses the text's rounded C = 0.9; Table 1's average C is 0.936 | **Changed value** → deviation run at 817 °C (below) |
| Correa's k_c | V via `char_oxidation.md` | The UCL manuscript is behind a Cloudflare check, so it was not re-read. Corroborated by Lin & Huang 2022 Table 2 (PDF read): char k = 0.05 W/mK at 250 kg/m³, so k·ρ = 12.5, inside the registered group range 10.5–15 | V (via), unchanged |
| Mukunda 2022 crib temperatures | S | Paper read. It quotes Fons et al.: "about 650 °C at the top of the crib and increased to a peak of 900 °C in about a distance equal to the bed height". These are **above** the crib, not inside it | V citation / S measurement |
| White & Dietenberger's 300 °C char base | V via | Re-read in FPL-GTR-190 ch. 18 (PDF) | V |

**Deviations and decisions, all disclosed:**
1. **The T_fl = 817 °C deviation runs.** They were registered nominal = 873 °C, and §6 required a deviation run at a
   changed value. Run before grading: S, K and F on all three grids.
   - **S:** identical digest to nominal on every grid.
   - **K:** λ_max 0.0171 against 0.0174 at 0.05 m.
   - **F:** identical digest at 0.1 m.
   - No class changes. Graded results are nominal.
2. **H2 excludes Up, the outward faces under the disc** (decided while building, before any run). Up never exchanges
   with the draught anywhere in the bed. Adding it only in flaming cells would have created a new heat path. Up is
   0.031 m².
3. **A flaming cell with no draught flow** (only at t = 0, before Ergun has a buoyancy to act on) gets its buoyancy
   temperature at the cap. Otherwise a flaming column could never start a draught. Decided while building, before any
   run.
4. **Glow is sampled every 10 physics steps (5 s),** for CPU. So t_glow and the longest glow run have 5 s resolution.
5. **B's λ counts the base lit at t = 0.** Its "partial" class (0.1667) is exactly that layer, 1/6 of the area, with
   no spread beyond it.
6. **A restart.** The first launch was stopped after its first four 0.05 m runs, because ruff required a refactor of
   `_draught` (statement count) and `_contact` (positional arguments). No noqa and no config change.
   - Those outputs were deleted, and all 92 runs were redone on the final code.
   - The refactor was verified three ways: E3 and E4(ii) rerun; an H2 smoke run; and S_005 and K_005 reproduce the
     pre-refactor runs' λ_max and wood fraction to every printed digit (0.005817764173314432, 0.9981476015086241;
     0.017387677320466928, 0.992179837816866).
7. **E3(iv)** at first covered only McCaffrey's flame and intermittent regions. A second column covering the plume
   region was added before the queue ran.
8. **F under three ends has no flame-out time** (k_c 0.07, EC5 k(T), T_f 380 °C), because no flame survives the first
   physics step. C_F is graded MISS (no finite flame-out with ≤ 5% wood); the wood left is 99.6–99.99%.

## 2. Constants after verification

As registered (`hot_constants.py::PROVENANCE`), with the §1 table's changes. No value used in a graded run differs
from a registered one.

## 3. Results in detail

### 3.1 S and K: why nothing spreads

**The char layer makes the small fire weaker, not hotter where it matters.** In S, the disc ignites at 415.5 s, as
in the bed (E4(ii)). Its flaming surface then runs at T_c 531 / 542 / 546 °C (median; peak 578–594 °C), the low end
of `char_oxidation.md`'s predicted 550–650 °C for outward faces.

But the front flux k_c(T_c − T_f)/δ_c falls as the char grows. Once the pilot stops (600 s), m'' drops below
m''_crit within 7 s, so flame-out comes at 607.0 s on every grid. Under the bed's pin it came at 1,042 s.

The disc releases about 4 kW at peak, against 5.5–6.0 kW with the pin (the "gas only" arm). The hottest unlit skin
beside a flame:

| Grid | 480 s | 600 s | Needs |
|---|---|---|---|
| S, 0.2 / 0.1 / 0.05 m | 99 / 152 / 184 °C | 125 / 187 / 222 °C | 380 °C (T_p) |
| K, 0.2 / 0.1 / 0.05 m | 109 / 164 / 270 °C | — / — / 310 °C | 230 °C (T_b) |
| K, accelerant spike | 108 / 164 / 208 °C | — / — / 230 °C | 230 °C |

**K at 0.2 and 0.1 m is the accelerant spike to the degree.** Its probe is identical at 180, 360 and 480 s, and so
is its λ_max (0.0058). Two things explain it:
- K's flaming area is the wet part Ia. That part is unchanged by design (§1.1), and its vapour-fed flame is not a
  char surface.
- K's Iw only flames in the substep it merges from Ia, at T_p. The flaming-Iw T_c median is 380.0 °C (peak 400 °C
  at 0.05 m).

At 0.05 m the hotter neighbours (310 °C by 600 s) let the fire creep to 0.094 m² (λ 0.0174, against 0.0129). That is
still 50× short of B1.

**The gas half is inert because the energy balance binds, not the cap.**
- **The exit gas in S** has a flow-weighted median of 50 / 84 / 120 °C and a peak of 123 / 295 / 551 °C. It never
  reaches even the 520 °C end at 0.1 m, so S's digest is the same at T_fl = 520, 817, 873 and 1,027 °C.
- **Why.** The disc's convective budget, (1 − χ_r)(Q − fb), is a few hundred watts spread over each column's
  draught.
- **The registered tie to heat release was the binding term.** Lifting the ceiling from 380 °C to 873 °C had no
  effect on a small fire's plume.
- **In K** the cap binds only in the kerosene bursts (exit peak 873 °C), which last a few steps.

**Attribution (reported).**

| Arm, λ_max at 0.2 / 0.1 / 0.05 m | S | K | S flame-out (0.1 m) |
|---|---|---|---|
| H1 (both changes) | 0.0058 / 0.0058 / 0.0058 | 0.0058 / 0.0058 / 0.0174 | 607.0 s |
| Surface change only | the same | 0.0058 / 0.0058 / 0.0129 | 607.0 s |
| Gas change only | the same | 0.0058 / 0.0058 / 0.0176 | 1,045.0 s |
| Neither (the parents) | the same | 0.0058 / 0.0058 / 0.0129 | 1,045.0 s |

The surface change shortens S's fire. The gas change does nothing in S, and adds the 0.05 m creep in K.

### 3.2 H2: flame gas touching its own cell

H2 changes the state wherever a flaming cell holds unlit fuel (different digests), but no class:

| H2 | 0.2 m | 0.1 m | 0.05 m |
|---|---|---|---|
| S: λ_max, flame-out | 0.0058, 607.0 s | 0.0058, 607.0 s | 0.0058, 607.0 s |
| K: λ_max, flame-out | 0.0058, 497.0 s | 0.0179, 626.5 s | did not complete |
| F: wood at flame-out | 32.8% | 38.7% | 40.5% |
| B: λ_max (base only), flame-out | 0.1663, 309.5 s | 0.1667, 357.0 s | 0.1667, 337.0 s |

The probe in S2 at 0.1 m reads 152 / 165 °C at 480 / 600 s, which is *lower* than H1's 187 °C at 600 s. The gas
gives its heat to the flaming cell's own unlit fuel, which leaves less for the cell above, and none of it reaches
380 °C. **So outcome 6 (H1 misses, H2 spreads) does not occur in any completed run.**

**K2_005 did not complete.** H2 in the soaked crate at 0.05 m was stopped by the owner's decision after 217 min 44 s
of CPU (every other run took 3–86 s), with no result written. It doesn't decide the hypothesis, since H1 alone
does (preregistration §1.3), but it leaves outcome 6 unchecked at the reference grid for K: at 0.1 m K2 reached
λ_max 0.0179, class none.

**Why it stalled (corrected 2026-11-20; the first version of this section blamed the char layer, wrongly).** The step
6 numerics review reran a copy and logged the substep count (`.worktrees/_durable/ladder_research/numerics_scratch/`,
not committed). The char layer was never thinner than 8.3 mm, and its term asked for 1–2 substeps. From t ≈ 523 s one
pilot-face cell kept a wetted area `A_ia` of 1.5 × 10⁻¹⁹ m², floating-point residue. `wetbed.py::_pilot_split` counts
any `A_ia > 0` as live and sends it the cell's whole pilot share (8.96 W), and `_step_ia` divides that power by
`A_ia`: 6 × 10¹⁹ W/m². When the sliver dried at 528.5 s its node reached 2.9 × 10¹⁶ K, and the explicit stability
limit returned 2.8 × 10³⁹ substeps. The fault is three things together: power divided by a part's area, a part with no
physical size counted as live, and no cap on substeps. The bug is in the accelerant spike's `WetBed`, so every run
with an accelerant loading carries it. The completed runs' ledgers close, but whether a sliver arose in them wasn't
checked. The energy involved is at most one cell's pilot share, about 9 W of the torch's 2 kW. For step 6: route power
by area share, never divide by a part's area, give every part a minimum size in metres, and cap every substep count.

### 3.3 F: the char layer stops a fully lit crate

Lit everywhere at t = 0, F releases 650–675 kW at 44 s. That is about 20% above `bed.md`'s ≈ 540 kW, because the
fresh surfaces run hot before char forms. As the char thickens, the front flux falls:
- the median flaming T_c is 704 / 646 / 608 °C on envelope cells and 801 / 749 / 716 °C in the interior (inside
  `char_oxidation.md`'s predicted 550–650 and 700–900 °C);
- surface after surface drops below m''_crit;
- the bed goes out at 466–522 s with 33–40% of its wood unburnt, against 0.6% in `bed.md`.

This is §0's prediction: with neighbours at 600 °C, an interior face's m'' falls below 3.7 g/m²s at about 6 mm of
char, before the 10 mm half-slat is consumed.

**The flaming duration converges:** 522.5 / 478.5 / 466.5 s, p = 1.87. That is the first observed order above 0.5 in
three spikes, where `bed.md`'s pinned F diverged (449 / 575 / 770 s). The insulating char makes burning
surface-controlled, not dependent on the unresolved radiative layer.

**F's O₂ demand** exceeds the draught's supply for 29–30% of its flaming time. O₂ never limits in this model, so F's
burning rate is O₂-unverified. A real limit would make the miss worse.

### 3.4 The range ends

| End (0.1 m) | S: λ, flame-out | K: λ, flame-out | F: wood at flame-out |
|---|---|---|---|
| nominal | 0.0058, 607.0 s | 0.0058, 498.0 s | 38.7% |
| k_c 0.07 / EC5 k(T) | 0.0058, **416.0 s** | 0.0058, 498.0 s | **99.6% / 99.6%, out in the first step** |
| ρ_c 200 | 0.0058, 611.5 s | 0.0058, 498.0 s | 19.3% |
| T_f 288 / 380 | 0.0058, 608.0 / **416.0 s** | 0.0058, 498.0 s | 36.8% / **99.99%, out in the first step** |
| T_fl 520 / 1,027 / Mz | 0.0058, 607.0 s | 0.0058, 498.0 s | 38.7 / 38.7 / 38.9% |
| ε 0.85 / 0.95 | 0.0058, 605.0 / 611.5 s | 0.0058, 496.0 / 499.5 s | 38.1 / 39.1% |
| q''_f 15 / 35 | 0.0058, 604.0 / 613.5 s | 0.0058 / 0.0073, 499.5 / 739.0 s | 69.6 / 21.0% |

No end flips a class, so G passes. **But three ends put every fresh flame out at once:** k_c 0.07, EC5's k(T)
(0.075 W/mK at the 340 °C layer mean), and T_f = 380 °C.
- **Why.** A freshly lit area joins Iw at T_p = 380 °C with the 1 mm char floor. Its first front flux is
  k_c(T_p − T_f)/1 mm. That gives 8.0 kW/m² and m'' = 4.4 g/m²s at nominal, just above m''_crit = 3.7. At k_c = 0.07 it
  gives 3.1 g/m²s, and at T_f = T_p it gives zero.
- **So in this model, whether a fresh surface flames at all sits within 20% of the threshold.** The quantity setting
  it is the 1 mm floor δ_s, a numerical choice. That is the "band near a binary threshold" CLAUDE.md warns of, and
  step 6 would need a cited char-free start (a char layer growing from zero, with its own transient) to remove it.
- Even the most favourable ends (ρ_c 200, q''_f 35) leave 19–21% of F's wood unburnt.

### 3.5 Glow as a side effect (reported, not graded)

In F, the sight-line envelope layer reaches ≥ 625 °C over ≥ 0.08 m²:
- from 115 / 120 / 120 s;
- for 410 / 360 / 345 s;
- over a peak area of 1.6–1.8 m², almost all of the 1.8 m² envelope.

**This is glow from burning surfaces, not embers.** No Ic char ever forms, because no part's wood is ever used up
(`ember_peak` is undefined). It supports `char_oxidation.md` §2.2's claim that a char surface during flaming sits at
550–900 °C, and that a hand-over from it would start embers hot. But in this model the wood never burns through, so
the hand-over doesn't happen. S, K and B show no glow.

### 3.6 Runtime

- **Runs:** 92, at most 4 processes at once, single-threaded BLAS. Load averages at run start were 5.9–18.4 (each
  run's JSON).
- **CPU:** 1,403 s over 91 runs, 3–86 s each. The 92nd, K2_005, was stopped at 13,064 s without a result (§3.2).
- **Typical:** 0.2 m 3–10 s, 0.1 m 7–17 s, 0.05 m 25–64 s.
- **Checks:** `closed_form.py` 4 s and `identity.py` 10 s.

## 4. The gaps the verdict leans on

**The no-spread verdict (B1, B2, C)** leans on the gaps that bias toward a miss:
- **No gas or soot radiation in P1 beyond χ_r·q''_f, and χ_r(Q − fb) exported.** This is now the most likely missing
  path. With both temperature pins lifted, the in-bed heat paths still can't carry a small flame's heat to its
  neighbours. Real flames are volumes that radiate onto nearby fuel and wrap it.
- **Ia pinned at T_b, single T_b, and no autoignition (K).** Inherited from the accelerant spike. They are why the
  soaked crate is barely changed.
- **The flame-gas analogy from pool fires.** This proved irrelevant: the cap never bound in S.

It is robust to H1's exclusion of in-cell contact, because H2 tested it and nothing changed, except for K at 0.05 m,
which did not complete (§3.2).

**The C_F verdict** (and, through the same mechanism, C in S) leans on:
- **q''_f fixed at 25 kW/m² on a hot surface,** with no flame-volume feedback in a crib. This is the decisive
  simplification. A real burning crib's interior surfaces receive flame and soot radiation from all sides; the bed
  model gives each surface only its own 25 kW/m² plus P1. Under that, the char layer starves the front.
- **The fresh-surface start at T_p with a 1 mm floor** (§3.4): a numerical choice sitting near a threshold.
- **Iw as one lumped surface per cell,** and **constant k_c** (the EC5 end only makes it worse).
- **Robust to:** O₂ never limiting and all front flux gasifying. Both favour burning, and F still misses.

**What it is robust to:**
- every cited range end (G);
- the grid (D1);
- the substep (E5);
- the 817 °C correction to T_fl;
- the in-cell contact variant.

## 5. What it means for the owner's T13 decision

The pre-registration's §4, applied as written:

1. **Outcome 5: the hypothesis is false.** Lifting the T_p pin from burning surfaces and flame gas doesn't spread
   fire through the crate, bare or soaked.
   - **The flame gas.** It is limited by the cell's heat release, not by the cap.
   - **The char surface.** It is hotter but self-insulating, and makes small fires shorter.
   - **What this rules out:** that the failure was one simplification. Option 1 is the larger job: a cited model of
     flames as volumes reaching neighbouring fuel (impingement, flame height and radiation across cells), or a cited
     crib spread correlation. **Option 3 (change the exit) becomes the realistic Phase 1 path.** The accelerant
     (option 2, T17) doesn't rescue spread either, as the accelerant spike already showed.
2. **The C_F miss: the de-pinned surface isn't a drop-in change to 6c.**
   - With a char layer and only q''_f = 25 kW/m² of feedback, a fully lit crate leaves a third of its wood. Real cribs
     burn out (NIST TN 2102: about 5% residue).
   - Step 6 needs a cited crib heat-feedback model before a char layer can be adopted: flame and soot radiation onto
     charring surfaces inside the crib, and char k(T).
   - **This also touches T17's char research.** Its recommended char layer (`char_oxidation.md` §5.1) is exactly
     this model. On its own it delivers hot surfaces (glow in F, 3.5) but stops the burning.
   - Step 6 can't take §5.1 without the feedback term. That is now a research question for the char model, not a
     detail.
3. **What step 6 can keep:**
   - the char-layer kernel (exact against its closed form);
   - the energy-limited flame-gas term, which costs nothing and is the physically right tie;
   - the identity-before-ignition test pattern (E4(ii)), a strong regression guard;
   - the finding that a surface-controlled burning law converges in flaming time (F: p = 1.87) where the pinned one
     didn't.

## 6. What this does not show

- **That a real crate wouldn't spread or burn out.** It would. Section 4's gaps are where the model departs from it.
- **Whether a flame-volume model would spread it.** That is the next research question, not tested here.
- **Glow or burnout as criteria.** They are out of scope; §3.5 is reported only.
- **Liquid motion, a poured crate, or grids finer than 0.05 m.**
