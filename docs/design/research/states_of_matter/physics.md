# States of matter as the world model: physics design

Research and design note for Maxim Overdrive, 2026-11-15. Read against `src/maxim_overdrive/world/{grid,heat,damage,world}.py`,
`docs/architecture.md` ("The resolution rule", "Known gaps") on `phase1/act-validation` at `56eed51`, plus
`signals/world_fields.md` and `signals/benchmarking.md`. No repo files were changed. Two throwaway probes were run
from the scratchpad (`phases/exp1d.py`, `phases/stefan.py`, `phases/run2.py`); their numbers are below.

## The short answer

1. **Put each phase where it can be rig-independent by construction.** Condensed matter (solids, and liquids that
   don't flow yet) lives in the rig's cells as **per-volume component masses plus enthalpy**. Gas lives **per room**
   (a well-mixed zone with a fixed species list), not per cell. Everything that crosses between the two crosses at
   **exposed faces, as fluxes per square metre**. Per-room quantities are integrals over cells, and per-area flux laws
   don't contain dx, so neither can change the outcome class when the rig changes. Free-surface liquid flow per cell
   (Noita and Dwarf Fortress cellular automata) is the one representation that *can't* be made rig-independent
   cheaply, so it is deferred. Liquids go per room first, as in Barotrauma.
2. **Switch the heat state from temperature to enthalpy (J/m³).** Temperature and phase fraction are then derived
   from enthalpy, and latent heat is exact. The explicit scheme keeps its stability bound: a phase plateau only adds
   heat capacity.
3. **Replace "cell-mean temperature over a threshold weakens integrity, and integrity 0 deletes the cell" with
   transitions that are linear in energy.** Mass leaves a cell at a rate set by the energy it receives (latent heat of
   melting, gasification or vaporization). Strength follows the remaining solid mass fraction, and a cell is removed
   only when its mass actually reaches zero. That is necessary for convergence but **not sufficient**: surface
   ignition is decided in a millimetre-thick heated skin that no rig resolves. It needs a sub-cell surface model
   whose depth is set in metres (FDS does this with a 1-D solid mesh that ignores the gas mesh).
4. **Combustion is per room, and oxygen is in it from day one.** Heat release is 13.1 MJ per kg of O2 consumed
   (Huggett 1980, verified), capped by the room's O2. Products are set by declared yields, with the atom balance
   closed exactly. **The sealed-room numbers change the exit test.** The 18 m³ crate scene holds about 4 kg of O2.
   Burning it down to a 15% O2 extinction limit releases about 15 MJ, which is about 1.2 kg of wood volatiles, out of a
   130 kg crate. **A sealed crate fire chars the surface and goes out within about 5 to 7 turns. It cannot "burn
   away".** The Phase 1 crate scene needs a ventilation boundary, and the fuel model needs a vent from the start.

## 0. Why the current fire diverges (diagnosis, with measurements)

The current model chains four steps: fixed power, spread over the solid cells inside a sphere, then integrity lost at
`rate·(T_cell − T_c)`, then the whole cell deleted at integrity 0, after which the power is renormalized over the
survivors. Three mechanisms break convergence.

**(a) Whole-cell deletion plus renormalization quantizes the fire's footprint and feeds the error back.** The
1-D probe (`run2.py`) puts a 3 MW/m² volumetric fire over x < R on a 0.6 m wood slab and reports mean slab integrity
at dx = 0.2 / 0.1 / 0.05 / 0.025 / 0.0125 m:

| model | R | 60 s | 90 s | 120 s |
|---|---|---|---|---|
| today's threshold + destroy | 0.25 m | 0.678 / 0.656 / 0.598 / 0.598 / 0.598 | **0.504 / 0.500 / 0.583** / 0.583 / 0.583 | **0.333 / 0.500 / 0.583** / 0.583 / 0.583 |
| enthalpy, energy-limited mass loss | 0.25 m | 0.887 / 0.878 / 0.852 / 0.852 / 0.852 | 0.791 / 0.739 / 0.713 / 0.713 / 0.713 | 0.652 / 0.600 / 0.583 / 0.583 / 0.583 |

The threshold model is **non-monotone in dx** (0.504 → 0.500 → 0.583 at 90 s), which is the same "oscillatory
convergence" that `benchmarking.md` found in the real crate's GCI. Its spread at 120 s is 0.25. The mass-loss model
converges monotonically with a spread of 0.07. The error that remains is first order and comes from the source's
edge cutting a coarse cell (fuel outside the sphere gets burned). It disappears once the source edge lies on a cell
boundary at every rig (R = 0.3: 0.652 / 0.600 / 0.600 / 0.600 / 0.601).

**(b) A cell-mean temperature can't see a surface skin.** Under a 50 kW/m² surface flux (`exp1d.py`), "ignite when
the first cell's mean T reaches 350 °C" gives these times:

| dx (m) | 0.2 | 0.1 | 0.05 | 0.025 | 0.0125 | 0.00625 | 0.003125 | closed form |
|---|---|---|---|---|---|---|---|---|
| t_ignition (s) | 1350 | 677 | 340 | 172 | 88 | 46 | 25 | **5.2** |

That is t ∝ dx: zeroth-order convergence over the whole game range. The closed form for a thermally thick solid is
t_ig = (π/4)·kρc·(T_ig − T₀)²/q″² (from memory, standard; it follows from the erfc surface solution). The heated
layer is √(αt) ≈ 1 mm for wood after 5 s. No game rig resolves it, and none ever will.

**(c) Thresholds turn a convergent field into a discontinuous outcome.** The cell average of a rate that is smooth in
T differs from the rate at the mean T by O(dx²·|∇T|²·r″) (Jensen), so it converges at second order. A kink, such as
`max(0, T − T_c)`, gives O(dx) error in the cells the front crosses. A step, such as "delete at integrity 0" or
"ignite when T > T_c", flips a volume of dx³ at once, and the time it flips is quantized by how long it takes to heat
the whole cell. Feedback then turns the local error into a global one: the renormalized power and the deleted cell's
lost heat (a known gap) both depend on which cells flipped.

**Is "rate-based mass loss driven by enthalpy" the standard way to converge?** For phase change, yes. The
fixed-grid enthalpy method (Voller; Alexiades and Solomon) is the textbook approach, and it makes the melted mass a
linear functional of the energy. For burning, fire codes do two things together. Pyrolysis is a rate law
(Arrhenius, or an ignition-temperature, energy-limited law), never a strength threshold. And the solid's heat
conduction runs on its own fine 1-D mesh normal to the surface, independent of the gas grid (FDS's solid phase). The
second part is what fixes (b), so this design adopts both.

## 1. Representation per phase

| Phase | Where it lives | State | Rig-independent? |
|---|---|---|---|
| **Solid** (and non-flowing liquid: molten steel, a melted plastic slump) | rig cells | `material` u8 (matrix material); **enthalpy H** f64 J/m³; **component densities** f32 kg/m³ for the components a material declares (wood: virgin, char, moisture; steel: one); `integrity` f32 = mechanical damage only | Converges (energy-linear). Exact for box-aligned geometry. First-order error only where a feature edge cuts a coarse cell, which is the existing thin-features rule. |
| **Exposed surface** (solid face next to a room's gas) | the faces of rig cells (derived mask), plus per-cell surface state for the fuel cells that have exposed faces | `skin` state per exposed fuel cell: absorbed energy and penetration depth (a heat-balance integral, 2×f32), `burning` bool | **By construction**, if area is measured in m², because the flux laws are per m². Caveat below. |
| **Gas** | **per room** (rooms = connected non-solid cells, labelled) | moles of a fixed species list: N2, O2, CO2, CO, H2O, FUEL (pyrolysate pseudo-species), SOOT (kg), plus 2–3 generic agent slots; room gas enthalpy; total pressure derived | **By construction.** Room volume is a cell count × dx³, which is exact for box-aligned rooms. |
| **Liquid pool** (water, oil, coolant, acid) | **per room** (Phase 2): volume per liquid species; level = V / floor area; pools on the floor | f64 per room per species, plus pool enthalpy | By construction. Barotrauma's "hulls and gaps" is the precedent (`world_fields.md`). |
| Liquid with a free surface per cell | deferred | fill fraction f32 per cell + velocity | **No.** Cellular automata (DF's 7 levels, Noita's falling sand, ONI's one element per cell) move "cells per step", so how far a flood runs depends on dx and dt. Doing it properly needs shallow water or VOF with a pressure solve. |
| Gas transport inside a room | deferred | a fixed-metre coarse gas grid (0.4 m, not the rig's dx) with an eddy diffusivity | By construction (fixed metres), at a cost of about 1/500 of per-cell at the max rig. |

Rules this representation forces:

- **No gas in cells.** Air cells stop being thermal state. Their displayed temperature is the room's (later the
  upper or lower layer of a CFAST-style two-zone room). That closes two known gaps by construction: "air only
  conducts" (heat now crosses faces into the room by a convective coefficient h) and "a fire dumps power into air
  cells" (there is nothing per-cell to dump into).
- **Measure exposed area in metres, and beware staircases.** For box-aligned surfaces, a count of exposed faces × dx²
  is exact at every rig. For a voxelized sphere or diagonal it is not: the staircase area tends to about 1.5× the true
  area as dx → 0 for a sphere (Manhattan-surface paradox; from memory). So either (i) keep fuel primitives
  box-aligned in Phase 1, which the crate already is, or (ii) estimate area per cell from the authored geometry, or
  from |∇φ_s|·V on the solid-fraction field. Record the choice as a known gap.
- **A cell is deleted only when its condensed mass is zero.** What remains (sensible heat, mass) is first moved into
  the room as products, so energy and mass close. The "destroying a cell removes its heat" known gap disappears.

## 2. Energy: the enthalpy method in `heat.py`

**State.** `H` replaces `temperature` in `MaterialGrid`, as J/m³ relative to T_ref = 0 °C. Per cell,
`H = Σ_i ρ_i·h_i(T, φ_i)`, summed over the condensed components i. For a component with a melt at T_m, latent heat L
and solid and liquid heat capacities c_s and c_l:

```
h(T) = c_s·T                          T < T_m
h    = c_s·T_m + φ·L                  T = T_m, φ ∈ [0, 1]   (the plateau)
h    = c_s·T_m + L + c_l·(T − T_m)    T > T_m
```

**Inversion** (T and φ from H) is closed form and branch-free in numpy for one meltable component per cell:
`H_s = ρc_s·T_m`, `φ = clip((H − H_s)/(ρL), 0, 1)`,
`T = where(H < H_s, H/ρc_s, where(φ < 1, T_m, T_m + (H − H_s − ρL)/ρc_l))`. Glass and polymers soften over a range,
so give them a **mushy band** [T_sol, T_liq] with φ linear in T across it. That makes H(T) piecewise linear and
strictly increasing, and it is the usual cure for staircasing. Mixed cells (wood: virgin + char + water) have one
meltable at most in Phase 1, and the other components add ρ_i·c_i to the sensible capacity.

**The scheme.** `H += dt·(div(k_face ∇T(H)) + q)`, with harmonic-mean faces as today. `k` becomes
`k(φ, components)`, the volume-fraction-weighted conductivity.

**Stability.** The explicit bound is `dt ≤ ρc_eff·dx²/Σk_faces`, where `c_eff = dH/dT`. On the plateau
dH/dT → ∞, which only *helps*. So the bound is the existing `stable_dt`, using the smallest sensible ρc and the
largest k each material can take in any phase. Precompute both per material. Then the bound doesn't change when
phases change, and `stable_dt` stops rebuilding every substep (the rebuild cost `world_fields.md` flagged). Two
cautions:

- An explicit enthalpy step can carry a cell straight across a whole plateau in one step if the step's dH > ρL.
  That conserves energy, but it smears the front. With game latents (steel ρL ≈ 2 GJ/m³) the stable dt never comes
  close, so this is a stated assumption with an assertion, not a sub-iteration.
- Mass loss also changes ρc. A cell that has lost most of its mass has a small ρc_eff and a tight dt. Floor the
  *conductive* coupling of nearly empty cells (k ∝ φ_s) rather than letting dt collapse. Equivalently, remove the
  cell below a small mass fraction ε, after transferring its contents. ε is a per-volume constant, not a cell count.

**Order of accuracy (measured, `stefan.py`).** One-phase Neumann problem, Ste = 0.5, explicit enthalpy method, melted
mass Σφ·dx against 2λ√(αt):

| dx | 0.1 | 0.05 | 0.025 | 0.0125 | 0.00625 | 0.003125 |
|---|---|---|---|---|---|---|
| error | 2.1e-3 | 8.6e-4 | 4.0e-4 | 5.6e-5 | 3.6e-5 | 1.6e-5 |
| observed p | | 1.26 | 1.11 | 2.84 | 0.63 | 1.19 |

That is first order *on average*, with the irregular steps that are characteristic of enthalpy methods ("staircase":
the front cell's temperature is pinned at T_m while the front crosses it; Tacke 1985 removes the oscillation in 1-D,
and refinement alone only reduces it). **The gate should therefore be an envelope, error ≤ C·dx, plus a
least-squares slope near 1 over four or more grids, not a tight pairwise p band.** Contrast heat's clean second
order.

## 3. Transitions

All of these are one mechanism: **energy above a component's transition enthalpy converts it at its latent heat.**
If the product is condensed, it stays in the cell (melt). If the product is gas, it leaves for the room, carrying its
sensible enthalpy with it (pyrolysis, evaporation, boiling, sublimation). One kernel and one conservation ledger
cover them all.

| Transition | Law | Where | Notes and data |
|---|---|---|---|
| Melting and solidification | enthalpy plateau (above) | cell | Steel: T_m ≈ 1500 °C, L ≈ 250–270 kJ/kg (from memory; iron is about 247 kJ/kg at 1538 °C). Phase 1: the melt stays in its cell (no flow). Known gap: molten metal doesn't drip. |
| Pyrolysis (solid fuel → FUEL gas + char) | **energy-limited at the surface** once the skin ignites: ṁ″ = q″_net / (L_g + c_s·(T_p − T_bulk)). **Volumetric** inside a cell whose bulk H passes the pyrolysis enthalpy (a thin item heated through), the same plateau form with L_g. Char yield χ_c stays as the char component. | exposed face; cell | This is FDS's simple "ignition temperature" solid model and Tewarson's ṁ″ = q″/L_g. Wood: T_p ≈ 300–350 °C, L_g ≈ 1.5–2 MJ/kg, char yield ≈ 0.2–0.25 (all from memory; verify against the SFPE Tewarson chapter). Arrhenius (dm/dt = −A·m·e^(−E/RT), with A and E from TGA) is FDS's full model. It is smooth in T, so its cell-mean bias is second order, but it is stiff and still needs the skin resolved. **Use energy-limited in Phase 1.** It is linear in energy and has a closed form (steady ablation). |
| Surface ignition | heat-balance-integral skin per exposed fuel cell: a quadratic or cubic profile of depth δ(t) driven by the net face flux. Ignite when T_surface ≥ T_ig. | exposed face | One ODE and 2 floats per exposed fuel cell. Reproduces t_ig = (π/4)kρcΔT²/q″² to a profile-dependent constant (about 10–15% for quadratic; from memory). **The test pins the constant against the erfc solution.** The alternative is a fixed-metre 1-D subgrid of 8–16 nodes per burning face (as FDS does), which costs more and is exact as N grows. |
| Gas-phase combustion | per room: burn FUEL at `min(supply, O2-limited)`, with an extinction ramp f(X_O2) = clip((X − X_lo)/(X_hi − X_lo), 0, 1). HRR = **13.1 MJ × kg O2 consumed**. | room | 13.1 MJ/kg O2: Huggett, *Fire and Materials* 4(2), 61–65, 1980, ±5% for conventional organic fuels (**verified**, NIST). Extinction limit: CFAST's lower oxygen limit is user-set. A developer post gives a default of **10%**, and its Technical Reference describes HRR falling off below **15%** (**conflicting; fix our own X_lo = 0.10, X_hi = 0.15 in data and cite both**). |
| Products | FUEL has a declared formula (wood pyrolysate ≈ CH₁.₇O₀.₇₂; **from memory**). CO and soot come from declared yields, and CO2 and H2O from the **atom balance**, so mass closes exactly. | room | Well-ventilated wood (Tewarson, SFPE; **from memory, not found online this session**): y_CO2 ≈ 1.27, y_CO ≈ 0.004, y_soot ≈ 0.015 kg/kg, ΔH_c,eff ≈ 12.4 MJ/kg. Measured effective heats for wood: 12–15 MJ/kg flaming at large scale (Babrauskas), about 16.5 MJ/kg dry, gross 18–19 (verified in secondary sources). Under-ventilated CO rises to about 0.1–0.2 kg/kg with the global equivalence ratio (Gottuk and Lattimer; the GER framework is verified, the 0.2 figure is from memory). Phase 1: constant yields. Phase 2: y_CO(GER). |
| Flame heat feedback | a **fixed incident flux per m²** q″_f onto burning faces (wood ≈ 25–35 kW/m²; from memory), taken out of the HRR before the rest goes to the room gas. Optionally, faces within a flame zone in metres (Heskestad flame height L_f = 0.235·Q^(2/5) − 1.02·D; from memory) receive it too, which is what makes flame spread emerge. | face | Gives HRR per unit area ≈ q″_f·ΔH_c/L_g ≈ 30e3 × 12.4/1.8 ≈ 200 kW/m², the right order for wood. **Don't feed back a fraction of the HRR**: that has loop gain χ·ΔH_c/L_eff > 1 and runs away. A fixed flux per area is what real burning saturates at. |
| Evaporation and condensation | ṁ″ = h_m·(ρ_v,sat(T_s) − ρ_v,room). The sign gives condensation on cold surfaces. ρ_v,sat from Antoine or Clausius–Clapeyron. | pool or face ↔ room | Water L_v = 2.257 MJ/kg at 100 °C. Also covers wood moisture (a latent sink before pyrolysis) and concrete dehydration. |
| Boiling | when T_s ≥ T_sat(p_room): energy-limited, ṁ = q_net / L_v | pool, cell | Exact closed form (below). |
| Sublimation | the same plateau with L_sub, product gas | cell | Only for props (dry ice: −78.5 °C, about 571 kJ/kg; from memory). Free once the kernel exists. |
| Extinguishing | water delivered as liquid mass onto faces: an energy sink of c_w·ΔT + L_v per kg, plus vapour to the room (which dilutes O2) | face | Rig-independent: mass per m² per second. |

**Structural consequences.** `integrity` keeps only mechanical damage (strikes). The structural reading becomes:

```
strength_cell = integrity × Σ_i (V_i/V_cell)·σ_i(T)/σ_ref        (σ_liquid = 0; char ≈ 0.1·virgin; from memory)
```

Here V_i/V_cell is each component's remaining volume fraction (mass / ρ_i), so **a burned or melted cell loses
strength in proportion to the mass it has lost, continuously.** σ(T) for steel follows a smooth reduction table:
Eurocode 3's k_y,θ is about 0.47 at 600 °C (from memory), so data, not code. `RegionSensor.integrity` becomes the
volume-weighted mean strength, a linear functional, so it converges. `breached` stays a connectivity test on cells
with strength below ½. It is still a threshold on a convergent field, so near its threshold it *will* flip between
rigs. The cure is the benchmarking note's outcome margin (gate a scenario only if its decisive value sits at least 2×
the cross-rig spread from the threshold), not a better kernel. Strikes already took that route with closed-form
outcome classes.

## 4. Conservation and budget closure

- **Species.** Track the mass of each condensed component per cell and moles of each gas species per room. Every
  process is a **transfer computed once, limited by what the donor holds, and applied antisymmetrically** to donor
  and receiver. Never clamp a stock after the update (SS13's negative moles came from unportioned sharing; clamping
  would create mass instead).
- **Elements.** Every reaction in `data/` is checked at load for an atom balance of C, H, O, N to 1e-12 (loader
  rejection test, B12), so species mass closes as long as elements do.
- **Energy.** Choose one reference. Sensible enthalpy is the state. Chemical energy enters as HRR = 13.1 MJ ×
  ΔO2 only. Latent heats are internal transfers. Keep a **per-substep ledger**: conduction (must sum to 0 to
  round-off), external sources, HRR, face convection (cell → room), the enthalpy carried by mass transfers, and vent
  outflow. The test is `ΔH_cells + ΔH_rooms = Σ sources − Σ boundary outflow`, to 1e-10 relative in float64, every
  substep and every rig, with Hypothesis over random scenes (B9). Keep component densities f32 only if the declared
  tolerance matches. **Keep H and room inventories in f64.**
- **Determinism.** Room labelling (`scipy.ndimage.label`) is deterministic. Per-room sums use `np.bincount` over
  room ids, which runs in a fixed order. No dict-order iteration over species: the list is fixed in data.

## 5. Benchmarks

| # | Benchmark | Closed form | Tests what | Order test? |
|---|---|---|---|---|
| B-1 | **One-phase Stefan / Neumann** (slab at T_m, wall at T_w) | X = 2λ√(αt), λ√π·e^(λ²)·erf λ = Ste | the enthalpy kernel, the plateau, latent bookkeeping | **Yes, space: first order (envelope).** Measured above. |
| B-2 | **Two-phase Neumann** (sub-cooled solid) | the same similarity form, with a two-erf transcendental (Alexiades and Solomon; from memory) | the sensible + latent coupling, different c_s and c_l | yes, first order |
| B-3 | Lumped block melted by constant power | t = m(c_s·ΔT + L)/P exactly | latent heat, energy ledger | no: L1 exactness, 1e-12 |
| B-4 | **Thermally thick ignition** under constant flux | t_ig = (π/4)kρcΔT²/q″² | the skin model | its own constant; **rig-independent by construction (same t at every dx)** |
| B-5 | **Steady planar ablation / regression** | v = q″/(ρ(L_g + cΔT)), cell emptied at dx/v | energy-limited pyrolysis, face hand-off as cells empty | exact at every rig for box geometry |
| B-6 | **Sealed-room O2 budget** (constant fuel supply) | m_O2(t) = m₀ − r·ṁ_f·t until the ramp, then exponential decay with rate r·ṁ_f/((X_hi − X_lo)·m_tot) | combustion, the ramp, yields, atom balance | **yes, time: first order** (explicit Euler). Use an exact exponential per room and it becomes L1 exact. |
| B-7 | Adiabatic sealed-room gas heating | ΔT = ∫HRR dt/(m·c_v); p from the ideal gas law | room enthalpy, pressure | exact |
| B-8 | **Ventilation-limited burning** (room with one doorway) | Kawagoe: ṁ_air ≈ 0.5·A√H kg/s, HRR_max ≈ 1.5 MW·A√H (from memory, classic) | the vent model, "burn away" | no (an outcome) |
| B-9 | Pool evaporation into a sealed room | m_v(t) = m_sat(1 − e^(−t/τ)), τ = V/(h_m·A) | evaporation and saturation | **yes, time** |
| B-10 | Boil-off | t_boil = m·c·ΔT/P, then dry at t_boil + m·L_v/P | the boiling branch | exact |
| B-11 | Draining tank / two rooms equalizing through a hole (Phase 2) | Torricelli t = (A/(C_d·a))·√(2h/g) | per-room liquid flow | yes, time |
| B-12 | Manufactured solution for a mushy-band H(T) | derived offline | variable k(φ), mushy inversion | **yes, second order** (smooth H(T)) |
| B-13 | Cross-tier crate (ventilated) | none, outcome class | everything together | GCI recorded, not gated |

The cheapest strong guard is **B-1 + B-3 + B-6 + the ledger**. B-4 and B-5 are the tests that prove the fix for
ignition divergence, because the same t_ig and v at every rig is the resolution rule made exact.

## 6. Cost at 5.12 M cells (the 16×10×4 m tile at 0.05 m)

| Item | Granularity | State | Per substep | Notes |
|---|---|---|---|---|
| Enthalpy conduction | cell | H f64 (replaces T: +0) | as today, plus one inversion (about 6 `where`/`clip` ops, +20–30%) | precomputing k and ρc per material removes today's rebuild of conductances per substep, which more than pays for it |
| Component densities | cell | 2–3 × f32 = 40–60 MB | only on the active mask (cells whose H is near a transition, or burning) | the mask is sparse: only cells in a fire zone |
| Exposed-face set | derived per topology change | ≈ area/dx²: 200 m² of fuel surface → 80 k faces at 0.05 m | skin ODE and fluxes on 80 k entries: negligible | recompute on cell deletion **inside the same substep** (the SS14 stale-airtightness lesson) |
| Room labels | cell, derived | u16, 10 MB | none; `ndimage.label` (≈0.1–0.2 s at 5 M) only on substeps that delete a cell or open a door | |
| Room gas, chemistry, vents | room | ~10 species × tens of rooms: bytes | microseconds; reductions via `bincount` over the active faces | can run per substep; nothing here sets dt |
| Liquids (Phase 2) | room | bytes | microseconds | |
| Snapshot | turn | adds uint8 channels: `phase` (liquid fraction), `char`, per-room tables | per turn | rooms ship as a table keyed by room id, not a grid |

**Per substep:** conduction, inversion, transitions, face fluxes, room chemistry (all coupled and cheap except
conduction). **Per event:** room labelling and the face set. **Per turn:** sensors, snapshot. Nothing here adds a
dx⁻⁵ transport field. Per-cell gas would (160 substeps × 8 species × 5 M cells at an eddy diffusivity of
0.01 m²/s, per `world_fields.md`), which is why it stays deferred.

Stability check of the new couplings at max (dt ≈ 6/64 ≈ 0.09 s): face convection, h/(ρc·dx) ≈ 10/(10⁶ × 0.05) ≈
2e-4 /s; room gas, h·A/(m·c) ≈ 0.03 /s; linearized radiation at 1000 K, 4σT³ ≈ 230 W/m²K, so about 0.7 /s on a room
(later). All are far below 1/dt.

## 7. What to build first, and what to defer

**Phase 1 fuel model, in order (each step ships its own tests):**

1. **Enthalpy state.** `H` replaces `temperature`. Materials gain `phase` data in `core.yaml` (T_m or a mushy band,
   L, c_l, k_l: null for none) and `components` (wood: virgin, char yield, moisture). **L1: with no transitions,
   the new scheme matches the old heat tests to 1e-12.** Then B-1, B-3, B-12. Precompute per-material ρc and k bounds.
   Decide this before save v0, because it changes the state variable of a saved field.
2. **Rooms and gas.** Label non-solid cells into rooms and give each room a fixed species inventory plus enthalpy.
   Air cells' T becomes the room's. Face convection carries heat between solids and the room. **Every room gets a
   vent from the start:** an opening to an ambient reservoir at constant pressure and composition (declared per
   scene in metres; Kawagoe inflow). Rooms are isobaric (expansion leaves through the vent), so there is no pressure
   solver. B-6, B-7, B-8 and the ledger.
3. **Pyrolysis, skin and combustion.** Energy-limited pyrolysis (surface and volumetric), the skin ignition model,
   room combustion at 13.1 MJ/kg O2 with the extinction ramp, atom-balanced products, and fixed-flux flame feedback.
   B-4, B-5, B-6. **The fire becomes the fuel's.** `ignite` becomes a *pilot* with a finite energy (J, or W for a
   capped duration) deposited by overlap. Sustained HRR comes only from pyrolysis. This removes the fuel gap by
   construction (no fuel, no HRR) and retires `test_a_fire_that_has_burned_its_fuel_stops_heating`, the
   500 kW / 0.3 m `TEMPORARY` envelope in `actions.yaml` and the `temperature_max` range gap.
4. **Strength by mass fraction.** `integrity` → strength = damage × remaining volume fraction × σ(T). Cells are
   deleted only at zero mass, after transferring their contents.
5. **Re-derive the crate scenario as ventilated,** with an outcome margin. The sealed version starves (about 1.2 kg
   of fuel burned) and becomes its own "fire goes out" test.

**Defer, and record as known gaps with numbers:**

- Per-cell liquids, a free surface and flow. Molten metal doesn't drip, and puddles are a surface layer later.
- A pressure solver and a velocity field. Rooms are isobaric with vents. Blast overpressure is an event.
- Per-cell or coarse-grid gas transport. Two-zone rooms (a CFAST-style smoke layer) come before any grid.
- Arrhenius multi-step pyrolysis, char oxidation (glowing combustion), y_CO(GER), and radiation between surfaces.
- Non-box fuel geometry (the staircase-area gap) until an area estimator exists.

## Sources

Verified this session:
- Huggett, "Estimation of Rate of Heat Release by Means of Oxygen Consumption Measurements", *Fire and Materials*
  4(2) 61–65, 1980; 13.1 MJ/kg O2, ±5%: https://firedoc.nist.gov/article/eXcyXYQBWEcjUZEYeI11 ,
  https://nvlpubs.nist.gov/nistpubs/sp958-lide/html/280-282.html ; Parker's use of E = 13.1 MJ/kg:
  https://nvlpubs.nist.gov/nistpubs/Legacy/IR/nbsir81-2427-1.pdf
- Enthalpy method, apparent heat capacity, source-term forms; Neumann one-phase solution and the λ equation (that page
  has a typo in its λ definition: use 2√(αt)): https://mbd.pages.rwth-aachen.de/courses/cmm/content/script/chapters/phase_change.html
- Staircase and oscillation in fixed-grid enthalpy methods; Tacke 1985's correction for explicit 1-D:
  https://arphymat.univ-rennes1.fr/publis/2009%20FVM%20Muhieddine%20et%20al.pdf ,
  https://diamhomes.ewi.tudelft.nl/~kvuik/papers/Bru06SV.pdf
- FDS Arrhenius pyrolysis with A and E from TGA, and reference-temperature inputs:
  https://firedynamics.github.io/LectureFireSimulation/content/modelling/09_pyrolysis/01_fundamentals.html ,
  https://fds-smv.blogspot.com/2009/09/pyrolysis-model-in-fds.html , https://arxiv.org/pdf/2303.17446
- CFAST oxygen-limited HRR and lower oxygen limit (10% default per a developer post; a decline below 15% per a
  Technical Reference discussion): https://groups.google.com/g/cfast/c/Qwr11g7LziQ ,
  https://gh.r-mj.com/firemodels/cfast/discussions/2214 ; CFAST technical reference:
  https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication1030.pdf
- CO yield vs global equivalence ratio (Gottuk and Lattimer framework):
  https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6431963/ ,
  https://www.tu-braunschweig.de/fileadmin/Redaktionsgruppen/Institute_Fakultaet_3/IBMB/FG_O/Bibliothek/Schriftreihen/Heft_198.pdf
- Effective heat of combustion of wood, 12–15 MJ/kg flaming (Babrauskas), 16.5 MJ/kg dry, gross 18–19:
  https://publications.iafss.org/publications/fss/3/547/view/fss_3-547.pdf (and the cone-calorimeter results linked
  from the same search)

From memory, to verify before anything goes into `data/` or `docs/`: the Tewarson SFPE wood yields (1.27 / 0.004 /
0.015, ΔH_c,eff 12.4 MJ/kg) and L_g, the wood pyrolysate formula, the thermally thick t_ig formula's constant and the
heat-balance-integral profile constants, Heskestad's flame height, Kawagoe's ventilation factor, steel T_m and L,
Eurocode 3 k_y,θ, dry-ice data, char strength, the voxel-sphere 1.5× area limit, wood q″_f, and the two-phase
Neumann transcendental. Game and engine precedents (Barotrauma, DF, Noita, ONI, SS13 and SS14, FDS, CFAST) are as
cited in `signals/world_fields.md`.
