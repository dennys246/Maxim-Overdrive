# Design review: world model (design v3, part 1), Physics and resolution lens

Reader: Physics and resolution. Design: `docs/design/world_model.md` at `66310f4` (draft). Folded review audited:
`reviews/world_v2/physics.md` (P1–P5, S1–S10, NITs). Code read: `.worktrees/act-validation` at `2f200b5`
(`world/damage.py`). Also read: CLAUDE.md, `docs/code_review.md` (Physics lens, Design reviews),
`docs/architecture.md` (Known gaps), `reviews/world_v2/determinism_lanes_performance.md` (S-3, performance),
`reviews/world_v2/executor.md` (E8), the committed probes.

One throwaway probe, run from the scratchpad in 0.3 s and not committed (rebuild from this description):
`strike_breach.py`, a Gaussian strike (σ = 0.15 m) centred on the face of a 0.4 m wall, using the shipped
`damage.strike` deposit (exact per-axis cell average). For each grid and three sub-cell offsets of the strike
point (0, ¼, ½ cell), it bisects the continuum crater radius R at which a through-hole first appears, by three
rules: (A) the shipped rule, destroy where the cell-mean density ≥ fracture, then a destroyed column connects the
faces; (C) S1's thickness rule fed by the shipped integrity, Σ max(1 − ρ_cell/f, 0)·dx per column ≤ 0; (B) damage
evaluated at points, remaining thickness averaged over each column's footprint. The continuum breaches at
R = 0.400 m. Energy ratios use E ∝ exp(R²/2σ²).

## Summary

The direction is right. One truth resolution removes the class of findings that came from machines simulating
different worlds, and the §3 table now applies the principle to most laws. But four things are wrong as written:
- **The verification rule (§1.1) is not yet a gate.** It names no tolerance and doesn't define "converge". It also
  loses three things the cross-rig rule exposed (B1).
- **§1.2 lets a machine's time budget coarsen the simulation.** That brings back machine-dependent physics, and makes
  the state depend on the wall clock (B2).
- **Strikes still decide at the cell mean in Phase 1.** S1's thickness rule doesn't fix that. At the truth
  resolution a 0.4 m wall breaches at 0.41–0.46× the strike energy the continuum needs (B3, measured).
- **"All destroyed mass goes to the zone's fines"** puts about 130 kg of concrete into a room holding 22 kg of air
  (B4).

The fold table also overstates: S8 is claimed folded in §8 and isn't there. Seven more rows are partial (table
below).

## BLOCKER

### B1. `world_model.md` §1.1, the verification rule: not gateable as written, and it hides what the cross-rig rule exposed

The rule says "the 0.1 m answer must lie within a stated tolerance of the 0.05 m reference, and must converge from
0.2 m". No tolerance is stated, "converge" isn't defined, and the rule has three holes.

1. **Agreement between two grids isn't correctness.**
   - *Pre-asymptotic plateaus:* P1's cell-mean wall exchange gives 104.2 / 104.2 / 84.7 MJ/m² at 0.2 / 0.1 /
     0.05 m, against a converged 48. The 0.2 → 0.1 step shows zero change, so any "converges from 0.2 m" check
     that looks for shrinking differences can't tell a plateau from convergence. A 25% tolerance against 0.05 m
     passes a law that is 2.2× wrong.
   - *Laws sized in metres can't be caught by the grid:* skins, ignited fractions and sub-box recession are
     dx-independent by construction. A convergence test over the grid passes them however wrong they are. v2's
     S6 said this of the ignition benchmark ("satisfied by any skin that ignores the cell").
   - A missing critical heat flux, or a wrong skin constant, is the same at 0.1 and 0.05 m.
2. **Offset variance at one resolution becomes invisible.** Under the cross-rig rule, a dependence on where a
   source sits relative to the grid showed up as rigs disagreeing. With one truth it is still what a player meets,
   but no test as written looks for it.
   - At 0.1 m, the v2 pilot lights the crate in 1.5 s centred on a face and 6.3 s on a corner (P2's table, rig
     column). That is a 4× spread between two positions 5 cm apart, at the truth resolution.
   - The area-overlap fix should remove it, but only an offset sweep would show that it did.
3. **The reference isn't a reference for a first-order law.** With p = 1, the error at 0.05 m is as large as the
   difference between 0.1 and 0.05 m. "Within a tolerance of 0.05 m" then bounds only half the truth's error.

**Fix: write the rule as three gates.**
- **(a) Every law has an absolute closed-form gate at 0.1 m.** CLAUDE.md's closed-form requirement stays, and it
  does the work for laws sized in metres.
- **(b) A three-grid gate on 0.2 / 0.1 / 0.05 m.** Compute the convergence ratio R = (f₀.₀₅ − f₀.₁)/(f₀.₁ − f₀.₂).
  - Require 0 < R < 1, and an observed order within about ±50% of the law's formal order. Otherwise the gate
    fails as non-asymptotic (Celik and Roache).
  - Gate |f₀.₁ − f_ext| / |f_ext| ≤ tol_q, with f_ext the Richardson extrapolation and Fs = 1.25.
  - For benchmarks, which are small 1-D or 2-D cases, add 0.025 m so the asymptotic claim is checked rather than
    assumed. Keep 0.05 m as the reference only for full-tile scenes.
- **(c) An offset sweep at 0.1 m.** Every benchmark with a source or a front runs at ≥ 3 sub-cell offsets (0, ¼,
  ½ cell), and the spread across offsets is gated too.

**An honest tolerance** is set per quantity, from what the outcome can bear, not from what passes. I'd propose:
- **5%** on continuous integrals: energy absorbed, mass remaining, burnout time, O₂ consumed.
- **The band gate** (S-1 below), in input units, for binary outcomes.

The probe shows (b) works. The strike-breach thresholds R* = 0.30 / 0.347 / 0.373 m give R ≈ 0.55, p ≈ 0.86 and
f_ext ≈ 0.405 m against a true 0.400. So the extrapolation recovers the continuum, and it flags the truth as 14% off
in R, which is 2.4× in energy.

### B2. §1.2 and D21: a machine's budget may coarsen the simulation, which reverses D20 and breaks determinism

D21 says "a machine's time budget may coarsen or sleep only regions where the outcome is provably unchanged". §1.2
says "as a law is verified resolution-independent by its convergence test, it earns budget freedom: the dial extends
law by law".
- **A convergence test proves agreement within a tolerance, not an unchanged outcome.** Near a binary threshold
  (B3's breach, the critical heat flux), coarsening flips the outcome. That is the class D20 removes.
- **A budget is wall-clock state.** The same scene and intents on the same machine, under different background
  load, would coarsen different regions and give different bits. That breaks "bit-identical on one machine" and
  replays. A replay on a slower machine diverges.
- **Sleeping is the only lever §1.2 states correctly,** because it changes nothing bit-for-bit.

**Fix:**
1. Resolution changes, if any, are decided from world state only, the same way refinement is.
2. The budget may only sleep (bit-identical) or dilate time.
3. Delete "earns budget freedom". If a coarser law is ever wanted, it is a deterministic world-state choice with its
   own band gate.

### B3. §3 and §7: strike damage still decides at the cell mean in Phase 1, and the breach-by-thickness fix doesn't reach it

`damage.strike` (shipped) subtracts ρ_cell/f from integrity and destroys a cell at integrity ≤ 0. That is a threshold
on the cell-mean energy density. §3 moves all of P4 to Phase 2, including P4's step 1 ("evaluate damage at points,
then integrate"), but strikes, craters and breach-by-strike are Phase 1. Measured (`strike_breach.py`, a 0.4 m wall,
continuum breach at R = 0.400 m):

| grid | shipped rule (A): R* (E / E_true) | S1's thickness on the shipped integrity (C) | damage at points, column-averaged thickness (B) |
|---|---|---|---|
| 0.2 m | 0.296–0.324 (0.20–0.29×) | 0.296–0.324 (0.20–0.29×) | 0.411–0.459 (1.22–3.11×) |
| **0.1 m (truth)** | **0.347–0.354 (0.42–0.46×)** | **0.347–0.353 (0.41–0.46×)** | 0.401–0.411 (1.02–1.23×) |
| 0.05 m (reference) | 0.374–0.376 (0.64–0.66×) | 0.373–0.375 (0.63–0.65×) | 0.400–0.401 (0.99–1.02×) |

Ranges are over offsets 0, ¼ and ½ cell.

**What the table shows.**
- At the truth resolution, the shipped strike breaches a 0.4 m wall with less than half the energy the continuum
  needs. Truth and reference disagree by 1.5× in energy.
- S1's rule changes nothing here, because it integrates an integrity that was already thresholded at the cell mean.
- Damage at points fixes the bias.
- The remaining 23% spread at offset 0 comes from averaging thickness over a column's footprint. Decide on the
  point-wise thickness instead: breached when the open area {(x, y) : remaining thickness ≤ t_min} ≥ A_min, both in
  metres. That composes S1 with §7's open-area rule, and it is exact for a sphere.

**There is a format consequence too.** `crack` = 1 − integrity is frozen by F1 ("a name is an identity"). If Phase
2 makes integrity a point-wise intact volume fraction, that is a meaning change. Define integrity's meaning now, as
the intact volume fraction from point-wise damage, and ship that meaning in Phase 1's strike.

**Fix:**
1. Phase 1's strike computes each cell's damaged volume fraction in closed form, as the measure of {x : ρ(x) ≥ f}
   (a sphere for one material, by per-axis overlap).
2. Breach is decided as above.
3. The crater test gates destroyed volume against (2/3)πR³ ∩ wall, with offsets.
4. Collapse stays Phase 2, but P4 asked for a known gap with the 7.5× number and a strict red gate until then. The
   document records neither (see S-7).

### B4. §2 and §7: "destroyed solid mass moves to the zone's fines species" puts a crater's mass into the room's gas

A strike with R = 0.3 m on a concrete wall destroys (2/3)π·0.3³ ≈ 0.057 m³, about 130 kg. The 3×3×2 m room holds
about 22 kg of air. As a gas species, those fines would:
- multiply the zone's mass and heat capacity about 7-fold (zone temperature, and every skin flux driven by it);
- enter X_O₂ if fractions are by mass, and so the extinction ramp;
- leave through vents with the Kawagoe outflow;
- if the destroyed cells' heat goes with them (architecture.md's gap "Destroying a cell removes its heat"), make
  the fines carry that energy into the gas.

This also contradicts P5's fix, which §7 cites: "fines are the declared mass fraction below a fixed size in metres
(for example 1 mm)".

**Fix:** a per-zone **debris pool**, inert and resting on the floor like the liquid pool in §2, with mass, enthalpy
and a fragment size in metres. It is not part of the gas mixture, and vents don't carry it.
- Only a declared aerosol fraction (a material property, *to be sourced*) enters the gas as fines.
- Phase 2's rubble then re-materialises the debris pool, and the ledger stays exact.
- The destroyed cells' enthalpy goes to the pool, which also closes that known gap.

## SHOULD-FIX

### S-1. §3, the band gate: as written it is a ratchet with no bound, and it compares only truth against reference

"Measure the width of the input range where the truth and the reference disagree, record it in Known gaps, and gate
that width" has four gaps.
- **No bound.** v2's S4 asked to gate the width at a declared fraction of the threshold (±10%). Gating the width you
  recorded only stops regressions, and it would accept P4's 7.5× once written down.
- **Two biased grids can agree.** Where a threshold has a closed form (the CHF, the crater radius, burn-through at
  0.40 m, the starvation O₂), the band must include it.
- **No offset sweep** (B1(c)). The player-visible band at one resolution is the spread over positions.
- **No procedure.** It doesn't say which input is controlling, the bisection tolerance, or the offsets.

**Proposed definition.** For each binary outcome O and its controlling input u (strike energy, pilot power and
offset, vent area, fuel mass):
1. Find u*_h by bisection to 0.5% of u*, at 0.1 m for at least three offsets, and at 0.05 m.
2. The band is [min, max] over every u*_h, together with u*_exact where one exists.
3. The gate is (max − min)/u*_ref ≤ the declared fraction (±10% to start).
4. A wider band is a strict `xfail` red gate, with its number in Known gaps.

**What this does to the B3 numbers.**
- The shipped strike fails it at 0.1 m. Its energy band is 0.41–0.46× the continuum's threshold, so it misses the
  true threshold entirely.
- The point-wise rule passes.

State the band in the input the player controls. Because E ∝ exp(R²/2σ²), 1.5% in R is about 10% in E at R/σ ≈ 2.7.

### S-2. §3, "goes out" isn't well defined, and v2's S9 fix wasn't taken

"Flames are extinguished when the zone's O₂ fraction falls to the extinction limit, with a ramp from 15% to 10%" has
five problems.
- **It never happens in finite time.** With a linear ramp f(X) = (X − 0.10)/0.05, O₂-limited burning gives
  dX/dt ∝ −f(X), an exponential approach to 10% (S9 said this). Under the stated rule, the sealed acceptance
  scene (§10, E1) never goes out.
- **"The extinction limit" is ambiguous.** The text names two (15% and 10%).
- **Flames out isn't burning out.** A hot sealed room keeps pyrolysing the crate through the skins after the
  flames stop. That is physical, but the solid's outcome then needs its own definition, and S5 asked B-6 to show
  pyrolysis stopping.
- **It has no meaning in a vented room** (steady state), or for fuel exhaustion.
- **"Burned away" is listed as a binary outcome, but not defined anywhere.**

**Fix:**
- "Out" is HRR below a declared W per m³ of zone for a declared time (S9's wording). Pyrolysis below a declared
  kg/(m²·s) on every face is a separate outcome, "smouldering out".
- "Burned away" is fuel mass below a declared fraction of the initial, in kg from the volume-overlap fuel field.
- All three go under the band gate.

### S-3. §3, skins on every exposed face: the energy store, edges, corners, recession and stability are unspecified

P1's fix said "the skin's energy is part of its cell's energy, never a second store". §3 doesn't carry that over,
and it doesn't say how skins behave in the cells where most of the crate's burning happens.
- **Edges and corners.** At 0.1 m with a 5 cm skin, a corner cell exposed on three faces holds three skin slabs of
  0.1 × 0.1 × 0.05 m: 1.5× the cell's volume. A cell exposed on two opposite faces is all skin. Define how
  overlapping skins share the cell's enthalpy, for example skin depth ≤ dx/2 with the overlap wedge counted once,
  and gate it with the crate's five-face heat-up.
  - The 1-D skin misses corner-accelerated heating: by superposition, a quarter-space heated on both faces reaches
    T_ig 4× sooner at the edge line. The affected width is √(α·t_ig), about 1–5 mm for wood. That is negligible for
    ignited area, but record it.
- **Recession.** P3's surface moves through the cell. The skin must recede with it, and when the sub-box empties,
  the skin must migrate to the newly exposed face of the next cell with its profile. §8's face table, keyed by
  (cell index, face), needs a defined migration rule before the grammar freezes, or each fuel PR invents one.
- **Stability.** A fixed-metre skin with 16 nodes over 5 cm has 3.1 mm nodes. Explicit stability needs
  dt ≤ dx²/2α: 0.41 s for steel (α ≈ 1.2×10⁻⁵ m²/s, *from memory*) and 0.04 s for copper, against a 0.5 s
  physics step. Specify an implicit tridiagonal skin solve, which is cheap per face.
- **Every face flux goes through the skin:** convection, radiation, flame feedback, and §8's new `douse` (water as
  a heat sink, evaporation). Say so.

### S-4. §3, pyrolysis: the fold changes S2's fix, and the new form is undefined and conflicts with sleeping

S2 asked for three things:
1. The face flux goes into the skin.
2. Gasification happens where the skin's surface reaches T_p, at L_g only.
3. "Volumetric" is triggered by a declared thermal thickness in metres.

§3 instead makes the volumetric branch "a rate on the reconstructed profile".
- **There is no reconstructed interior profile.** Skins exist only at faces, and P1 showed that a linear
  reconstruction across a coarse cell is 3× wrong.
- **An Arrhenius-type rate is positive at every temperature.** Every wood chunk then always changes, so it never
  sleeps (§1.2), and it adds a sub-ulp drift to the ledger.
- **It isn't needed in Phase 1.** Thin features are at least two cells (≥ 0.2 m), and wood's heated depth over an
  hour is 2√(αt) ≈ 4.6 cm (α = 1.5×10⁻⁷ m²/s). So no Phase 1 fuel is thermally thin.

**Fix:** take S2 as written. Drop the volumetric branch from Phase 1, refuse thermally thin fuel by the declared
thickness, and record thin fuel as a known gap.

### S-5. §3 against §9: sparks and torches stay volumetric, so they can't drive the skins

§9 keeps "the fire's sphere overlap … for sparks and torches". That is P2's problem 1: a volumetric deposit heats the
cell's interior, not the skin. So a torch ignites on the cell-mean clock that the skin was built to remove. It also
keeps the known gap "a source smaller than a cell heats one cell" (P/dx³).

**Fix:**
- Every heat source acting on a solid surface deposits by area overlap on exposed faces, in W/m².
- Volume deposit is kept only for genuinely in-depth sources.
- Add the surface clause to CLAUDE.md's deposit rule (v2 physics NIT 4).
- Add P2's minimum pilot size in metres.

### S-6. §1.1, thin features and alignment have no stated grid under one truth

- CLAUDE.md's "two cells of the coarsest rig" loses its referent. If 0.2 m stays a verification grid, a scene must
  be representable at 0.2 m for B1(b) to run, which means features ≥ 0.4 m thick and geometry aligned to 0.2 m.
  Otherwise the 0.2 m run is pre-asymptotic by construction, and the three-grid gate fails or means nothing.
- §3's "unaligned fuel geometry is refused" doesn't say aligned to which grid.
- State both. One choice: aligned to 0.2 m and ≥ 0.4 m for verification scenes, and ≥ 2 truth cells for play
  geometry, with dynamic thinness held by the integral rules (v2 physics NIT 3).

### S-7. The benchmark set is missing, so PR 3's harness has nothing named to verify

v2 had §3.4's minimum set, and the physics review added seven benchmarks. v3 lists neither. "v2 §2.1 stands" doesn't
cover §3.4. Name the Phase 1 set, each with its closed form, the grids, the offsets and a tolerance:
- wall heat uptake, convective and radiative (P1; pin the Carslaw–Jaeger form);
- the box burning on five faces (P3, replacing the slab);
- pilot translation invariance and the critical heat flux (P2, S6);
- the absolute t_ig against erfc (S6);
- planar burn-through as a thickness (S1);
- the strike breach of B3;
- the closed-form vent, HRR ≈ 1.5 MW·A√H (S7);
- the sealed room going out (S-2).

Plus the Phase 2 placeholders: the pillar's ligament (P4) and the repose cone (S10). The P4 known gap and red gate
belong here too, and so does the rule that the lab tile contains no pillar a player can cut until then.

### S-8. §7, the Phase 2 foundations: one field is missing, and one meaning isn't fixed

- **`fragment_m` isn't reserved.** P5's fix carries fragment size per volume on loose cells, and the snapshot
  carries it with `loose`. §7 says "fragment size is a length in metres" but reserves only `loose` and
  `packing_fraction`. Adding it later is the format change §7 exists to avoid.
- **Integrity's meaning** (B3): fix it now as the intact volume fraction.
- **A min cut of intact area is a capacity, not a support decision.** Phase 2 also needs demand: the mass above and,
  for eccentric damage, the moment. The foundation needed now is the per-face intact area. With integrity defined
  as a volume fraction, area fraction × dx² is derivable, so no extra field is needed if B3 is taken.
- **Settling via `packing_fraction`** as a partly filled top cell is adequate for S10's continuous column heights.

### S-9. §1.1, the performance case for 0.1 m misquotes its source

§1.1 says 0.05 m runs at "about 1.6× real time in a quiet room even after caching, and slower during a fire". The
source (DLP, performance) says "about 0.3 s per 0.5 s step, roughly 1.6× real time" (that is, 1.6× *faster* than
real time) and 0.55 s per step during a fire, about 0.9× real time.
- That estimate costs skins as one face pass (60 ms). With 16-node skins on about 200 k faces, the skins cost
  about one heat substep each (about 35 ms), so 0.05 m would be worse than DLP says.
- The conclusion (0.05 m has no headroom) probably survives, but state the numbers correctly. Open question 1
  rests on them.

### S-10. §3, two existing cell-mean laws are missing from the table

- `damage.thermal_degrade` (shipped) reduces integrity where the cell-mean temperature exceeds `degrade_above`: a
  threshold on the mean. With skins, the surface is hotter than the mean.
- The planned steel strength σ(T) (Eurocode 3 k_y,θ in §11) is non-linear in T.

Say which temperature each reads: the skin's surface temperature, or a through-thickness integral of k_y(T(x)) over
the skin plus the cell. Add both to the table.

### S-11. The fold table: S8 is claimed and not folded, and the physics NITs are missing

- **S8** is listed under "§8 (identity), Known gaps". §8 mentions neither breach holes as vents nor
  `temperature_max`, and the document records no known gap. That is the A-B1 pattern the table exists to prevent.
  Either fold it in §8 (define `temperature_max` as a reduction in metres; record breach venting as a known gap
  with S8's 0–0.16 m² quantization at 0.2 m, re-measured at 0.1 m), or list it under part 2.
- **The v2 physics NITs are missing from the table:** the enthalpy-form update, f32 progress and fuel mass, dynamic
  thinness, and the deposit surface clause. The table says it covers "every v2 finding within this part's scope".

## NIT

- **§3, fuel by volume overlap plus refusing unaligned fuel is redundant for boxes.** The sub-box state can represent
  an unaligned box exactly: initial recession = (1 − overlap) per axis, on the outer side. So unaligned boxes don't
  have to be refused, and the refusal can be kept for non-boxes only.
- **§4, the ledger.** "Changes close to 1e-12 of the tile's total energy" isn't a gate. State the bound per conserved
  quantity (energy, mass, O and C atoms), both tile-wide and per zone. A tile-wide relative bound of 0.1 J per
  substep is fine for catching a leak, but a per-zone ledger localises it.
- **§3, flame feedback.** S5's cap ("the min of the two") isn't stated.
- **§3, vents as a separate closed-form term.** S7 asked for directed flows inside L, which the implicit step handles.
  A separate explicit term needs a donor limit and a stated CFL. A 1 m³ cupboard with a 1.6 m² door exchanges
  about 40% of its mass per 0.5 s step. Say which form is used.
- **§1.2, sleeping.** The "uniform" criterion must cover every coupled state: zone values, skins, progress, fuel and
  rates, compared bit for bit. A room that has had a fire cools asymptotically and never sleeps again, so sleeping
  helps only untouched regions. Say so, so nobody counts on it for the dial.

## Fold table audit (physics rows)

| Finding | Cited | Verdict |
|---|---|---|
| P1 heat exchange | §3 | **Folded** in substance (skins on every exposed face, depth in metres). Missing: the skin-as-part-of-the-cell energy rule, the closed-form benchmark (S-3, S-7). |
| P2 ignition by area | §3 | **Partial.** Area overlap, ignited fractions and losses are in. Missing: the minimum pilot size, the translation-invariance and CHF benchmarks. §9 keeps volumetric sparks and torches (S-5). How the ignited fraction grows after the pilot is removed (spread within a face and to the next face) is undefined. |
| P3 sub-box recession | §3 | **Folded** in substance. Missing: the five-face box replacing the slab benchmark, the skin–recession coupling (S-3). |
| P4 collapse | §3, §7 (Phase 2) | **Partial.** Deferring collapse is the owner's call (D22). But step 1 (damage at points) is needed in Phase 1 (B3), and the requested known gap and red gate aren't recorded (S-7). |
| P5 fragments | §3, §7 | **Partial.** "Fragment size in metres" is stated. `fragment_m` isn't reserved (S-8), and the fines rule contradicts P5 (B4). |
| S1 breach by thickness | §3 | **Folded** for ablation. Ineffective for strikes until B3 is taken. |
| S2 pyrolysis | §3 | **Changed, not folded.** It replaces S2's thermal-thickness criterion with an undefined rate (S-4). "Sensible heat counted once" is in. |
| S3 fuel by overlap | §3 | **Folded.** The alignment grid is unstated (S-6). |
| S4 band gate | §3 | **Partial.** No bound, no offset sweep, no closed-form anchor, margin not in input units (S-1). |
| S5 flame feedback | §3 | **Mostly folded.** The cap and the "pyrolysis stops" benchmark are missing. |
| S6 skin constants, CHF | §3 (ignition row) | **Partial.** Losses and CHF are in. The absolute pin against erfc and moisture (model it, or declare dry fuel) are missing. |
| S7 zone operator | §3 | **Folded** for the operator and the per-gap transfers. The vent form is vague, and the B-8 closed-form vent and √H from z-binned gaps aren't named (NIT, S-7). |
| S8 holes as vents, `temperature_max` | §8, Known gaps | **Not folded** (S-11). |
| S9 "goes out" | §3 | **Partial.** The sealed-room numbers are reproduced correctly (1.07 kg at 15%, 2.0 kg at 10%). The definition doesn't terminate, and S9's own definition wasn't taken (S-2). |
| S10 settling | §3 (Phase 2) | **Folded** as a deferral. `packing_fraction` is adequate, and the repose cone benchmark is a Phase 2 item. |
| v2 physics NITs (enthalpy form, f32 progress, dynamic thinness, surface deposit clause) | absent | **Not listed** (S-11). |

## What I checked and found sound

- **D20's one truth as the root fix** for the cross-machine class. The principle and the choice of 0.1 m are
  defensible, subject to S-9's corrected numbers.
- **Sleeping quiet chunks as the only budget lever that touches physics.** An exactly uniform chunk and halo give
  zero fluxes, so on/off is bit-identical (with the NIT's criterion).
- **The §3 table's quoted evidence** matches the v2 review: P1 47.9 / 48.1 / 48.1; P3 0.370 at every grid; S1
  0.30 / 0.35 / 0.375 m; S3 0.38–1.13; S7 0.18% and 0.0.
- **The zone operator** (I + dt·L·V⁻¹), with antisymmetric per-gap transfers: conservative for any volumes, and
  matching DLP S-3's measured fix.
- **The sealed-room O₂ numbers:**
  - 3.95–3.96 kg and about 4.95 kg of O₂;
  - 1.07 kg of fuel to 15% and 2.0 kg to 10%;
  - the E1 point that a sealed gate passes under any burn law (5 kg of O₂ burns only about 2.5 kg of the 130 kg
    crate).
- **Breach by remaining thickness** for planar ablation. With sub-box recession it is exact, and composing it with
  §7's open area is right, once damage is evaluated at points (B3's probe: 0.99–1.02× at 0.05 m).
- **Mass never silently deleted** as a principle. Only its destination is wrong (B4).
- **The integer cell counts for zone volumes and gap areas** (§2, §6): exact and deterministic, and aligned zones are
  exact at every grid.
- **Flame feedback per m² scaled by the extinction factor and debited:** it bounds the loop gain and closes the
  ledger.
- **Float64 caches and a relative ledger bound** (§4): both are consistent with the measured magnitudes (a tile holds
  about 1e11 J, and pairwise summation error is about 1e-15 relative).
- **Phase 2's foundations** for settling (`packing_fraction` as a partly filled top cell), persisted cluster ids with
  a metric ordering key, and the topology choke point. All adequate.
