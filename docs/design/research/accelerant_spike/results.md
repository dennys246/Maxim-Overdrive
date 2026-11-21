# Accelerant spike: results (2026-11-20)

**This is the T13 failure path.** The torch lights the soaked crate's kerosene in 47.5 s on every grid (A passes),
but the fire never leaves the faces under the torch.
- **How little burns:** at most 1.3% of the slat surface ever lights (0.05 m grid), 99% of the kerosene is never
  burnt, and 99% of the wood is left when the flames go out. B1, B2 and C miss on all three grids and at every
  pre-registered range end.
- **The cause is the one the physics spike found, not the accelerant.** The bed's heat paths (in-bed radiation P1
  carrying χ_r·q''_f, and draught gas leaving a flame at T_p) can't raise the unlit wood next to a flame to 230 °C.
  It reaches 108 °C at 0.2 m, 164 °C at 0.1 m and 230 °C only at 0.05 m, after 600 s of burning.
- **So T18's claim fails in this model.** T18 said a soaked bed spreads "because its fuel is distributed"; here it
  doesn't. No constant was tuned, and no criterion moved.
- **The owner decides before step 6 is designed** (preregistration §4, "B1 misses"): a cited spread law (option 1 of
  `../physics_spike/physics_spike.md`), or a changed exit (option 3).

**Read this verdict with its caveat.** It leans on gaps that bias toward a miss (§4). And the 0.05 m reference has not
converged on how far the fire spreads: the lit fraction is 0.6%, 0.6%, 1.3% and 0.9% at 0.2, 0.1, 0.05 and an extra
0.025 m, not monotonic, but never near 90%. The miss is robust in class across all four grids, but this spike does not show that a real kerosene-soaked crate wouldn't spread. It shows
that **this model** can't make it spread.

Code: `spikes/physics/accelerant/`.
- `wetbed.py` subclasses `spikes/physics/bed/model.py::Bed`. The bed's code and results are untouched.
- `wetsim.py` and `acc_run.py` run and grade one scenario; `analyze.py` grades all of them; `closed_form.py` is E4(i);
  `probe.py` is the spread diagnostic.
- `results/*.json` and `analysis.txt` hold the numbers. The `*.npz` arrays aren't committed; the scripts regenerate them.

The criteria are `preregistration.md`'s (commit 40d79a6, SHA-256 b42a4627…), unchanged.

## Verdicts

| # | Criterion (threshold as pre-registered) | Result | Verdict |
|---|---|---|---|
| A | Kerosene flaming over ≥ 90% of the disc's faces before the pilot ends | t_A = 47.5 s at 0.2, 0.1 and 0.05 m. Closed-form expectation ~40 s; bare wood took 415 s | **PASS** |
| B1 | max λ ≥ 0.90 | λ_max = 0.0058, 0.0058, 0.0129 (0.2, 0.1, 0.05 m): 0.031, 0.031, 0.070 m² of 5.4 m² | **MISS** |
| B2 | λ_w(t_L95) ≥ 0.90 | t_L95 never occurs: 98.9–99.4% of the kerosene is still in the wood when the run ends. λ_w ≤ 0.0116 at every time | **MISS** |
| C | Flame-out after t_L95 and the pilot's end, virgin wood ≤ 5% | Flame-out at 558.5, 556.5 and 1,220 s with 99.4%, 99.4% and 98.9% of the wood left. No t_L95 | **MISS** |
| D1 | Class of A, B1, B2, C identical at all three grids | (PASS, MISS, MISS, MISS) on every grid | **PASS** |
| D2 | 2a rule at 15% on t_A, t_B, t_L95, flame-out; λ within 0.05 | t_A: 47.5 / 47.5 / 47.5, passes. t_B and t_L95 don't exist: missing, so a miss. Flame-out: 558.5 / 556.5 / 1,220 s, e₀.₁ = −663.5 s against tol 183 s, a miss. λ_max and λ_w differ by 0.007 and 0.006 at 0.1 m: pass | **MISS** |
| D3 | p > 0.5 for each D2 time | t_A: zero differences, so p is undefined (a miss by the rule as written; the time is grid-independent). Flame-out: differences +2.0 and −663.5 s, a sign change. t_B, t_L95: missing | **MISS** |
| E1 | Ledger closes to 1% at every step | Worst 2.0 × 10⁻¹³ of cumulative release over 24 runs (23 graded and 1 extra) | **PASS** |
| E2 | Each new line turns E1 red when deleted | `combustion_accelerant` 81% (Surf_01), liquid sensible heat 12% (N_01_rerun). `vapour_unburnt` 0.22% at most (Tb175_01): too small to trip 1% | **Partial MISS** |
| E3 | Liquid mass closes to 10⁻⁹ | Worst 3.9 × 10⁻¹⁶ | **PASS** |
| E4 | (i) T_b plateau = m_L·L_v/q'' to one substep; (ii) zero loading reproduces `bed.md` | (i) First measurement (substep count): worst error 1.54 substeps, a miss. Interpolated measurement (a deviation, added after the miss): 2.8 × 10⁻¹¹ substeps. (ii) S and F at 0.1 m, and F at 0.2 m, reproduce the bed's committed runs **bit for bit** (SHA-256 digests equal, e.g. F_nom_01 bcfc8eab…), with every printed observable equal | (i) **MISS as measured**, see §1 · (ii) **PASS** |
| E5 | Rerun bit-identical; 10× substeps keep the classes | Digest equal. At 10× substeps: same classes, t_A 47.5, λ 0.0058, flame-out 558.5 s (against 556.5) | **PASS** |
| F | Every end keeps nominal's classes | All 14 ends give (PASS, MISS, MISS, MISS), so the outcome is not a band inside the cited ranges. The largest spread is at T_b = 175 °C: λ = 0.036 | **PASS** |

**Back on the T13 path:** yes. B1, B2 and C miss at nominal on the 0.05 m reference (the pre-registered trigger).

## 1. What was built, and the deviations

The model is preregistration §1. A liquid mass sits per node of the 10-node half-slat on every profiled part (Ui, Up,
and the new Ia). Its heat capacity joins the node's. A wet node is capped at T_b, and the energy above it evaporates
liquid at L_v (`wetbed.py::evaporate`).
- **Ignition:** a wet area ignites at T_b by the bed's piloted rule and reconstruction. A dry area ignites at T_p as
  before.
- **Ia (ignited and still wet):** it flames while (m''_K·Δh_c,K + m''_w·ΔH_c,w) ≥ m''_crit·ΔH_c,w. Its dry surface node
  runs 6c above T_p.
- **Heat:** the flame's heat goes through the bed's own terms.
- **With zero loading every added term is an exact zero.** That is why E4(ii) reproduces the bed bit for bit.

**Deviations and interpretations, all disclosed:**
1. **E4(i)'s measurement.** The test as first written counted the substeps in which the node evaporated. Its two
   boundary substeps are only partly at T_b, so the count carries up to two substeps of quantisation, and it missed at
   1.54. An interpolated measurement was added after the miss: crossing time from the explicit update, drying time
   from the last substep's evaporated share. It gives 2.8 × 10⁻¹¹ substeps, so the kernel is exact. The miss is the
   first estimator's; it is reported as measured, and the second measurement is labelled a deviation.
2. **Ia → Iw.** The pre-registration says Ia "merges into Iw when it holds no liquid … as Ui → Iw does now". The bed's
   merge sets the skin to T_p, so merging a dry area still below T_p would give it a T_p skin for free. The code merges
   only when the area is dry **and** its surface node is pinned at T_p. This was decided before any run. In every
   graded run but one, every merge happened while flaming (λ_w equals its loose variant). The exception is Surf_01,
   where 0.0019 m² merged while not flaming (λ_w 0.0055 against 0.0058 loose). No class depends on it.
3. **Undefined t_L95.** B2 and C need t_L95, which never occurs because the unlit wood keeps its kerosene. Both are
   graded MISS, consistent with D2's "a time missing on any grid is a miss".
4. **Not modelled on Ia:** char oxidation. Ia's char is carried into Iw on merging. Glow is out of scope, and Ia
   holds at most 0.07 m².
5. **Glow layers not computed** (`envelope_layer`, brightness), to save CPU. Ember peak and mean are recorded and
   aren't interpreted (out of scope, preregistration §5).
6. **E2's liquid sensible-heat line** was added as a record-only field part-way through the queue. It is present in 7
   of the 23 graded runs, N_01_rerun included, which is identical in state to N_01. Evolution and digests are unaffected.
7. **One extra run, not pre-registered and not graded:** the 0.025 m grid (§3.4). It was added after seeing that λ
   grew from 0.1 m to 0.05 m.

**The m''_crit ends** change the wood's own extinction criterion as well as q''_crit, because the pre-registration
derives one from the other. The **loading transfer** from fuel oil by volume rather than mass (S densities 0.825
against 0.865) would give 59 kg/m³ of wood. That lies inside the 32–96 range already run at both ends, so no deviation
run was needed.

## 2. Constants after the verification pass

These are the pre-registration's M and S rows, rechecked before the runs. **No verified value differed from a
pre-registered one, so no deviation runs were required.**

| Constant | Pre-registered status | Final status |
|---|---|---|
| T_b range 175–325 °C, flash point | V/S (NIOSH from a snippet) | **V.** NIOSH Pocket Guide 0366 page read: BP 347–617 °F, FP 100–162 °F, SG 0.81 |
| Gasoline RVP 7–15 psi (justification only) | M | **S.** CARB document via search: winter 7–15 psig; EPA summer cap 9.0 psi |
| Gasoline flash point −43 °C (justification only) | M | M: not found |
| Kerosene thinner than No. 2 fuel oil | M | **S.** Penn State FSc 430 table: No. 1 at 31 SSU, SG 0.825; No. 2 at 35 SSU, SG 0.865 at 100 °F (publisher unnamed) |
| q''_crit energy form (Lyon & Quintiere 2007) | M | **M.** Citation confirmed (C&F 151:551); full text not reached |
| χ_r = 0.35 end | S | **S.** Hamins et al. 1991 abstract: 0.16–0.35 over eight fuels, which fuels unconfirmed |
| Wood cell-wall density 1,530 kg/m³ | S | S |
| Babrauskas m''∞, kβ, Δh_g (cross-checks only) | S | S: the primary wasn't opened |
| Drying-model form | M | M |

## 3. Results in detail

### 3.1 A: the accelerant lights

The wetted faces under the 15.9 kW/m² disc reach T_b and ignite at 47.5 s at every grid.
- **Against prediction:** the derived closed form was about 40 s; bare wood took 415 s in `bed.md`.
- **At the ends:** 25 s at T_b = 175 °C and 166 s at T_b = 325 °C, so A is sensitive to the boiling-point
  simplification but passes at both ends.
- **A 30 s ("brief") pilot, reported and not graded, lights nothing.** The faces are still below T_b when it ends,
  and the run goes quiet at 30.5 s. A hold of order a minute is needed, consistent with the tile spec's assumed 60 s.

### 3.2 B: why it doesn't spread

`results/probe.txt` gives the hottest unlit skin next to a flame (where the piloted rule allows ignition) during
600 s of burning:

| Grid | 180 s | 360 s | 480 s | 600 s | Lit area at 600 s |
|---|---|---|---|---|---|
| 0.2 m | 68 °C | 95 °C | 108 °C | — (out) | 0.031 m² |
| 0.1 m | 107 °C | 146 °C | 164 °C | — (out) | 0.031 m² |
| 0.05 m | 135 °C | 178 °C | 208 °C | 230 °C | 0.069 m² |

The burning disc is small: 0.031 m², about 5 kW mean release while flaming (peaks of 130 kW come from vapour
bursts, below). Its heat reaches the unlit wood only two ways:
- **P1:** χ_r·q''_f = 7.5 kW/m² of the flaming area, spread over the cell.
- **Draught gas heated to T_p:** about 1 g/s per column at 0.1 m.

The rest of the flame's radiation is exported as `flame_radiative` (0.70 MJ of the 2.6 MJ released at 0.1 m), and
nothing in the model returns it to the bed. This is the physics spike's root cause unchanged. **Lowering the ignition
threshold to T_b didn't bridge it:** the neighbours' temperature rise falls short of the 210 K needed by a factor of
2.4 (0.2 m) and 1.5 (0.1 m).

Only at 0.05 m do neighbours reach 230 °C. There a flame's P1 source and plume heat are shared with 1/8 of the unlit
surface that a 0.1 m cell holds, so the same flame heats it harder.
There the fire creeps from about 400 s, reaching 0.070 m² by flame-out at 1,220 s. That is why λ and the flame-out
time differ between 0.1 m and 0.05 m (§3.4).

**The vapour comes in bursts, a single-T_b artifact.** Each 1 mm node holds 0.064 kg/m² of kerosene, 16 kJ/m² of
latent heat, but needs 214 kJ/m² of sensible heat to reach T_b. So vapour arrives in bursts as each node reaches T_b,
and the Ia flame flickers: flaming in 874 of 3,574 steps at 0.1 m. The peak release of 130 kW (about 4 MW/m² of
flaming area, twice Babrauskas's large-pool rate) is a burst, not a sustained fire.

### 3.3 C: nothing is left to sustain

The lit disc burns its own wood through in 510–560 s at 0.2 and 0.1 m (wood left 99.42% = 1 − 0.031/5.4), then goes
out. C is the 1a criterion, so it is decided by B's failure, not by the wood fire's own balance. Scenario F already
showed that balance holds when the whole bed is lit (`bed.md` §3).

### 3.4 D: convergence, and the extra 0.025 m run

D1 passes: the class is the same at every grid. D2 and D3 miss:
- **t_A is grid-independent.** The disc is sampled at 1 mm whatever the cell size, so its differences are zero and p
  is undefined.
- **Flame-out is not converged.** It is 558.5, 556.5 and 1,220 s, because at 0.05 m the fire begins to creep. This is
  the physics spike's Q2 lesson again: the in-bed radiative layer (about 0.1 m) and here the flame-to-neighbour
  distance are unresolved at 0.2 and 0.1 m. The 0.05 m reference is not converged either.

**The extra 0.025 m run, not pre-registered and not graded:**
- A passes at 47.5 s; B1, B2 and C miss.
- λ_max = 0.0091 (0.049 m²), λ_w = 0.0083, flame-out at 814.5 s with 99.2% of the wood left.
- 0.82% of the kerosene burns; the ledger closes to 1.9 × 10⁻¹⁴.

So the lit fraction across 0.2 / 0.1 / 0.05 / 0.025 m is 0.0058 / 0.0058 / 0.0129 / 0.0091, and flame-out is 558.5 /
556.5 / 1,220 / 814.5 s. **Neither converges, and neither is monotonic.** Whether the fire creeps a few centimetres
depends on how the cell boundaries fall against the disc. But on every grid the class is the same, and the lit area
stays below 1.3%: two orders of magnitude short of B1's 90%. The spread extent near the flame is under-resolved; the
verdict is not.

### 3.5 E: the ledger and the checks

- **The ledger closes to 10⁻¹³, and the liquid's mass to 10⁻¹⁶.**
- **The closed form found nothing wrong with the kernel** once measured properly (§1, item 1).
- **E2 is a partial miss for the same reason as `bed.md`'s 4b:** `vapour_unburnt` carries at most 0.22% of release,
  because almost no unlit wet surface reaches T_b, and a 1% global tolerance can't see it.
- **The strongest check is E4(ii).** The extended model reproduces the bed's committed S and F runs bit for bit, so
  every added term really is inert at zero loading.

### 3.6 F and the reported quantities

**F.** No end changes a class. The largest effect is T_b = 175 °C: λ = 0.036, flame-out at 2,162 s, 97% of the wood
left. A soaked crate's outcome does not hinge on any cited range end; it hinges on the missing heat path.

| At 0.1 m, nominal | Value |
|---|---|
| Kerosene burnt / vented / left in the wood | 0.58% / 0.006% / 99.4% |
| Energy released: kerosene / wood volatiles / char | 0.86 / 1.75 / 0.0002 MJ (against 149 MJ of kerosene available) |
| Peak release (a vapour burst) | 129 kW |
| O₂ demand above draught supply | 0.03% of steps before the run ends, so **not** "O₂-unverified" |
| `t_crack` (≥ 0.08 m² of envelope ≥ 10% charred) | none at 0.2 or 0.1 m; 331.5 s at 0.05 m |

## 4. The gaps the verdict leans on (preregistration §5)

**The miss leans on all four gaps that bias toward a miss**, so it is not robust to them:
- **A single T_b with no evaporation below it.** Real kerosene's flash point is 38–72 °C (NIOSH). A neighbour at
  164 °C would be shedding vapour, and the flash point is far below the 230 °C this model demands. This gap probably
  matters most.
- **Gas leaving a flame at T_p (380 °C), not at flame temperature.** Real flames are hotter, and contact the wood above.
- **Autoignition (229 °C, CHRIS) not modelled.**
- **Ia's 6c skin conducting inward.**

**The gaps that bias toward a pass** (complete combustion, O₂ never limiting) can't rescue a fire that never spreads.

**What the verdict is robust to:**
- every cited range end (F);
- the substep count (E5);
- the grid class (D1).

**What it is not robust to:**
- the four model gaps above;
- an unresolved spread extent at fine grids (§3.4).

## 5. What it means for step 6, and the owner's decision

Per preregistration §4 ("A passes, B1 misses"): **T18's distributed-fuel claim fails under 6c's heat paths. T13: the
owner decides, before step 6, between a cited spread law (option 1) and changing the exit (option 3).** Loading
beyond the cited retention is not offered, and F shows it would not help: 96 kg/m³ gives λ = 0.0066.

**This spike's evidence, laid out for that decision:**
1. **The accelerant is not the missing piece; the spread law is.** With wood (`bed.md`) and with kerosene (here),
   every fire stays where it was lit, because nothing carries a flame's heat to unburnt fuel at the rate real flames
   do. The accelerant made ignition fast (47.5 s against 415 s) and changed nothing else. **Recommendation: option 1,
   researched as a flame-to-fuel heat-transfer law,** a flame-gas temperature and contact, or a cited spread rate for
   cribs and soaked porous beds. It should be a sub-cell law sized in metres, because §3.4 shows spread depending on
   the cell size.
2. **If option 1 is taken, the accelerant model also needs a cited evaporation-below-T_b law.** Vapour pressure from
   the distillation curve would replace the single T_b, before any rerun. That is the largest miss-biasing gap, and
   it makes the vapour supply bursty. Step 6 should not ship the single-T_b model.
3. **What step 6 can keep from this spike:**
   - the in-depth loading field and the evaporation kernel (exact against its closed form);
   - the energy and mass ledgers, which close to round-off;
   - the zero-loading identity test pattern, a strong regression guard;
   - the finding that a brief hold doesn't light a soaked crate (A needs about 50 s).
4. **SEM (T18) is unaffected:** the bridge still derives "soaked" from the loading field. But the claim that spread
   follows from labels-free physics has to wait for the spread law.

## 6. What this does not show

- That a real kerosene-soaked crate wouldn't burn. It would. §4's gaps are where this model departs from that.
- Glow or burnout. They are out of scope, and no char outputs are interpreted.
- Liquid motion, pooling or a poured (rather than soaked) crate. These are Phase 2.
- Behaviour at grids finer than 0.025 m.

## Runtime

23 graded runs plus 1 extra, at most 4 processes at once. Load averages were 35–61 at each run's start (in each JSON).

| Grid | CPU / wall per nominal run |
|---|---|
| 0.2 m | 5 s / 8 s |
| 0.1 m | 11 s / 18 s |
| 0.05 m | 60 s / 95 s |
| 0.1 m at 10× substeps | 85 s / 98 s |
| 0.025 m (extra) | 693 s / 752 s |

Range ends took 10–22 s of CPU each.
