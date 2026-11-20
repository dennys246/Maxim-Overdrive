# 5. Numerics, resolution, determinism and cost for the fire ladder

Lens: numerics, resolution, determinism, cost. Tags: **V** I read it in a primary source, **S** secondhand,
**M** from memory, **D** I derived or measured it (script named). Scratch scripts, downloads and logs are in
`ladder_research/numerics_scratch/`. Sources read: FDS at commit `5458d6e` (`Source/wall.f90`, `func.f90`, `read.f90`,
the Technical Reference and User's Guide `.tex`), Gpyro at `6d369dd` (`documentation/gpyro_technical_reference.pdf`),
and Stoliarov & Lyon's ThermaKin paper (IAFSS 9, 2009, pp. 1141–1152). Load averages for every timing are given
beside it.

## 0. Correction first: K2_005's diagnosis is wrong

`hot_surface_spike/results.md` §3.2 says the run probably stalled because the char-layer limit
0.9·C/(k_c/δ_c + h_r + 120) "grows the substep count without bound as δ_c thins". **The code refutes this, and a
reproduction finds a different cause.**

- **The char term is bounded (V, code).** `HotBed.delta_c()` returns `max(c_iw/rho_c, skin_m)`, so δ_c ≥ 1 mm.
  With C = 600·1700·0.001 = 1,020 J/m²K, the limit gives **1 substep** for every δ_c at k_c = 0.10, and **2** at the
  worst floored case (EC5 k = 1.5 W/mK at 1,200 °C). Without the floor, the count would still only be 6 at 10 µm and
  55 at 1 µm (**D**, `cost_kernels.py`). That is linear growth, and it can't produce a 200× slowdown.
- **What happened (D, `k2_probe*.py` on a copy of the spike code, load 2.8–4.6):**
  1. At 0.1 m, K2 never needs more than 1 substep (10,800 steps).
  2. At 0.05 m, the smallest δ_c in the run is 8.3 mm, far above the floor.
  3. From t ≈ 523 s, cell (0,3,4) on the pilot face holds an accelerant area A_ia of 1.4×10⁻²⁰ to 1.5×10⁻¹⁹ m². It
     grows in steps of 1.355×10⁻²⁰ = 2⁻⁶⁶, so it is floating-point residue from the Ui→Ia area transfers.
  4. `WetBed._pilot_split` sends the whole of the cell's φ pilot share (8.96 W) to Ia whenever `A_ia > 0`.
     `_step_ia` then divides it by the area (`direct_w / max(A_ia, 1e-30)`), which gives **6×10¹⁹ W/m²**.
  5. While the sliver held liquid, boiling and the T_p pin hid this. Once it dried (t = 528.5 s), the skin jumped to
     **2.9×10¹⁶ K** in one step.
  6. `WetBed._substeps` uses the area-blind T³ of the hottest live Ia node. It returned **n = 2.8×10³⁹**: in effect an
     endless loop, with NaNs after it.
- **The lesson is general, and it's worse than the hypothesis.** Three defects compound:
  - an absolute power is divided by an area that can be a rounding residue;
  - a sub-part with no physical size still counts as "live";
  - the substep count is derived from state, with no upper bound (as in `splitting.md` §6 rule 3, which also has no
    cap).
- **H2 did not cause it.** It only changed the trajectory enough to create the sliver; the bug is in the accelerant
  parent. A results.md correction is the owner's call. Logs: `probe_K2_005_live.txt`,
  `probe2_K2_005.txt`, `probe3_K2_005.txt`.

## 1. In-depth conduction with pyrolysis and char in FDS, Gpyro and ThermaKin

**FDS (V, `wall.f90`, `func.f90`, `read.f90`, User's Guide §"Solid Phase Numerical Gridding Issues")**
- **Integrator.** Each surface cell solves 1D conduction in the normal direction with **Crank–Nicolson** (the
  `-0.5*DT_BC_SUB*K*RDXN*RDX/RHO_C` coefficients) and a hand-written **Thomas algorithm**.
- **Front boundary.** Radiation is linearised about the old surface temperature: 3εσT⁴ on the right-hand side and
  2εσT³ in the diagonal. So the stiff T⁴ term is implicit to first order, without iteration.
- **Bounded substeps.** The solid step is split only when a trial explicit ΔT exceeds `DELTA_TMP_MAX` (default
  25 °C). The split is **capped at `TIME_STEP_FACTOR` = 10** (`DT_BC_SUB = DT_BC/MIN(NINT(TIME_STEP_FACTOR*
  WALL_INCREMENT), MAX(1,NINT(TMP_RATIO))))`). FDS buys bounded cost by accepting lower accuracy at the cap, which
  CN's unconditional stability makes safe. An optional Fourier check (`CHECK_FO`) is off by default.
- **Grid.** The first cell is ≤ `CELL_SIZE_FACTOR`·√(α·1 s), with default factor 1 and stretch 2 toward mid-depth.
  Cell count is capped by `N_LAYER_CELLS_MAX` = 999 (`GET_N_LAYER_CELLS`). For wood (α ≈ 1.2×10⁻⁷ m²/s) the first
  cell is about 0.35 mm, giving roughly 10–12 cells across a 20 mm slat (**D**).
- **Densities** update explicitly (`RHO = MAX(0, RHO - DT*RHO_DOT)`). Cells scale by the density ratio
  (shrink/swell).
- **Remeshing.** A layer is remeshed when:
  - a cell vanishes;
  - a cell's size changes by more than `REMESH_RATIO` (0.25) since the last remesh;
  - the layer thins by more than 1.5× its smallest cell.
- **Layer removal.** A layer is removed outright below `MINIMUM_LAYER_THICKNESS` (1×10⁻⁶ m, or 0.1× the specified
  thickness if smaller) or `MINIMUM_LAYER_MASS_FRACTION` (1×10⁻¹²). Its mass is reported as lost.
- **Emission correction.** The radiation chapter bounds an emission correction to [0.1, 100] so that flaming cells
  radiate χ_r·q̇‴ (V, `Radiation_Chapter.tex` §"Correction of the Emission Source Term"). This is FDS's own admission
  that σT⁴ of an under-resolved cell mean is wrong.

**Gpyro (V, Technical Reference §4.1, §6.1–6.3)**
- **Integrator.** Fully implicit finite volume with a TDMA. Nonlinearity is handled by **outer iterations to a
  tolerance** (relative for species, absolute otherwise), with optional static under-relaxation applied only when
  convergence fails.
- **Grid.** Cells are Lagrangian in condensed mass: Δz shrinks or swells to conserve mass. For charring with no
  shrinkage, Δz stays fixed (§4.2).
- **Positivity.** Source terms are split into production and destruction parts, and destruction is made implicit:
  φ = (φ° + Δt·S⁺)/(1 + Δt·S⁻/φ). This is **Patankar's** trick. It keeps masses non-negative without a clamp, and
  the guide says it was "critical for ensuring a stable solution".

**ThermaKin (V, IAFSS 9 paper pp. 1145–1149)**
- **Integrator.** **Crank–Nicolson**, with the rate function linearised by a first-order Taylor expansion (one
  linearisation, no Newton loop). The result is a block-tridiagonal system, solved by LU "with iterative improvement".
- **Step and element size are user-fixed.** The verification problem converged at 1×10⁻⁵–1×10⁻⁴ m elements and a
  0.01–0.1 s step. It **diverged** at Δt = 2 s with 1×10⁻⁵ m elements, and at 20 s with 1×10⁻⁴ m.
- **Element merging or minimum thickness:** not described in this paper (unknown).

**What is bounded-cost and deterministic:**
- A fixed-structure implicit solve: CN or backward Euler, Thomas with a fixed node count, **one** linearisation of
  T⁴ and Arrhenius, no tolerance loop.
- FDS-style capped substeps are bounded too. Gpyro's converge-to-tolerance loop is not: its cost is data-dependent,
  though it is deterministic on one machine.
- Remeshing is deterministic if its triggers are integer or threshold tests computed in metres, but it is branchy
  and changes array shapes. For charring wood, the Gpyro choice (Δz fixed, properties change) avoids remeshing
  except where char oxidation regresses the surface.

## 2. Stiff source terms at a fixed 0.5 s step

| Approach | Cost per tick | Determinism risk | Failure mode |
|---|---|---|---|
| Explicit, with state-derived substeps (spikes today) | unbounded (§0) | none on one machine; n depends on state | spiral: one bad cell sets n for the grid |
| Explicit plus clamp | bounded | branchy, but deterministic | clamps hide energy errors and create the asymptotic-threshold artefacts in `splitting.md` §6 |
| Linearised implicit (FDS, ThermaKin) | bounded, fixed | none if elementwise | CN rings when Δt·α/Δx² ≫ 1 (below) |
| Newton to a tolerance (Gpyro) | data-dependent | bits change with the tolerance; iteration counts vary per cell | slow cells, cost spikes |
| Exponential / analytic at frozen T | bounded, 1 `exp` per node | `np.exp` may differ across CPUs (SIMD libm): allowed, since only one-machine bit identity is required | first order in T(t) |
| Patankar–Euler | bounded | none | first order, under-predicts the rate |

**Measured (D, `stiff_tests.py`, load ≈ 2.6):**
- **CN ringing.**
  - Setup: wood under a 50 kW/m² step, dt = 0.5 s, 30 stretched nodes, first node 9.3 µm thick
    (Δt·α/Δx₀² = 681).
  - θ = 0.5: the surface **cooled on 10 of 19 steps** under constant heating.
  - θ = 0.55 and θ = 1: 0 of 19.
  - Consequence: with nodes set in metres and Δt fixed, use backward Euler or θ ≈ 0.55. Alternatively, keep Δx₀ at
    √(α·Δt) or more, i.e. 0.24 mm at 0.5 s.
- **Arrhenius.**
  - Setup: illustrative wood kinetics, A = 10⁸ s⁻¹ and E = 125 kJ/mol, with T rising 10 K/s.
  - Remaining fraction at 25 s, against an exact 0.5108: frozen-T exponential at T_mid 0.5110, explicit 0.5276,
    Patankar 0.4950.
  - k·Δt is only 0.34 here, so explicit is still stable. Above about 850 K, k·Δt > 1 for these kinetics (**D**), and
    explicit overshoots and needs its clamp.

**Splitting (V, `splitting.md`).** Lie with a fixed law order. Exact per-law updates make Lie safe at a large Δt.

**Real-time practice:**
- Fixed dt plus an accumulator, and **a clamp on steps per frame** so the game slows down instead of spiralling
  (V, Fiedler, "Fix Your Timestep!").
- Rigid-body solvers use **fixed iteration counts chosen offline**, not convergence tests, and prefer substeps to
  iterations (V, Catto, Solver2D 2024).
- Maxim's analogue: a fixed or capped n per physics step, fixed linearisations, and dilating world time (D21) when
  the cap binds. **Never an uncapped loop.**

## 3. Grid independence of sub-cell flames, fronts and char

- **FDS (V, User's Guide §"Grid resolution").**
  - FDS judges plume resolution by D*/δx, with D* = (Q̇/(ρ∞c_pT∞√g))^(2/5).
  - The current guide now says taking any tabulated value "as an 'acceptable' minimum is inappropriate". The often
    quoted 4–16 range is **S/M**; I didn't find it in this guide revision.
  - FDS doesn't make flames grid-independent. It *requires* resolving them, then patches the radiative part
    (χ_r correction).
- **Our evidence that grid-scale structure breaks convergence:**
  - **Bed.** `bed.md` §4: flaming duration 449 → 575 → 770 s with growing differences. The stated cause is the P1
    radiative boundary layer, 1/√(3βκ) ≈ 0.10 m, which is unresolved at the coarse grid.
  - **Hot surface.** `hot_surface_spike` F: flame-out converges (p = 1.87) once the surface law is controlled by a
    char layer sized in metres.
  - Both match world_model §3: sub-cell models sized in metres converge, and cell-sized ones don't.
- **Fronts.**
  - A char layer or pyrolysis front kept as a per-surface 1D state in metres, here δ_c or a node grid, is independent
    of the voxel grid by construction. Only its coupling area (face area, sub-box recession) touches dx.
  - Level-set fronts (**M**) are heavier and unneeded if each face carries an ignited-area fraction.
- **Flame-volume risks when the volume spans cells:**
  1. Emission deposited into grid cells (P1 or DOM) inherits the unresolved near-field. That is the bed.md failure.
  2. Partial-cell overlap decided by cell centres gives stair-step jumps in flux as the flame grows.
  3. A binary "flame touches this face", decided by cells, flips between grids.
  4. Feedback: Q̇ sets flame height, which sets irradiance, which sets burning area, which sets Q̇. Any grid error in
     area amplifies around this loop.
- **Remedy:**
  - The flame is a solid shape in metres (height from Q̇, e.g. Heskestad, set by the flame-model research).
  - Its surface emissive power is fixed so that the total radiated power is χ_r·Q̇ exactly.
  - Irradiance is evaluated at quadrature points on each receiving face, fixed in metres, not per cell, and
    integrated over the face.
  - Contact is a geometric overlap fraction.
- **Cross-tier test for the flame volume:**
  - (a) **Decoupled.** A prescribed Q̇ over a burner, and a target face at several distances. Compare the absorbed
    power on the target with an analytic cylinder-to-element view factor at 0.2 / 0.1 / 0.05 m. Gate the relative
    error and the order p.
  - (b) **Conservation.** Radiated power = χ_r·Q̇ to round-off on every grid.
  - (c) **Coupled (R3).** Sweep the separation between two bodies. Measure the band of separations where grids
    disagree on "second body ignites", and gate its width (S4 band gate). Report t_ignite's Richardson p, and require
    p > 0.5 with the differences shrinking.
  - (d) The same test with the flame base straddling a cell boundary, offset by dx/3 and 2dx/3. This catches
    cell-centre decisions.

## 4. Cost at our scale

**Measured (D, `cost_kernels.py`, numpy single-threaded, `OMP/OPENBLAS/VECLIB/MKL_NUM_THREADS=1`, load
2.57 → 2.61):**

| Kernel | Size | Best time |
|---|---|---|
| 1D CN step, Thomas vectorised over surfaces | N = 20 nodes × M = 1,000 | 0.22 ms |
| | 20 × 10,000 | 1.65 ms |
| | 20 × 100,000 | 15.6 ms |
| | 40 × 100,000 | 30.2 ms (≈ 7.5–8.5 ns per node) |
| Flame point to face irradiance, unoccluded | 256 points × 10,000 faces | 59 ms (≈ 23 ns per pair) |
| | 1,024 × 10,000 | 230 ms |
| Occlusion by fixed-step voxel sampling | 100,000 rays × 32 samples | 87 ms (≈ 27 ns per sample) |

**Checks:**
- Bit-identical on repeat: **True**.
- A subset of surfaces solved alone gives **the same bits** as inside the batch. So sleeping or waking surfaces
  can't change results.
- Accuracy against the semi-infinite constant-flux closed form at 60 s, comparing at node 0's centre:
  - 20 stretched nodes (1.15): +0.34%;
  - 40 uniform 1 mm nodes: +0.007%;
  - 10 uniform 4 mm nodes: +3.7%.
  - Backward Euler and CN agree within 0.1% at Δt = 0.5 s.

**At our scale (D):**
- **Crate, 0.6 m at 0.05 m.**
  - Outer surface 2.16 m², i.e. 864 faces. With 20 nodes that is about **0.2 ms** per solve.
  - A crib's internal slat area may be 10× that: about 2 ms.
- **Tile, 16×10×4 m at 0.1 m (640k cells).**
  - Even 200 m² of exposed fuel at 0.01 m² per face is 20,000 surfaces. At 20 nodes that is **about 3.3 ms** per
    solve.
  - The cached heat substep costs 3.9 ms (world_model §9, V). The in-depth solve is about one heat substep, once per
    physics step if it is unconditionally stable.
  - Memory: 20 nodes × 8 B × 3 arrays × 20,000 surfaces ≈ 10 MB.
- **Flame radiation is the cost risk, not conduction.**
  - All pairs at fine sampling is 59–230 ms per evaluation, plus occlusion. At 2.6 M pairs × 32 samples, occlusion
    alone is about 2.2 s, which is infeasible every step.
  - Bounded alternatives:
    - (i) a few emitters per flame, using analytic solid-cylinder view factors (≈ 1 pair per face per flame);
    - (ii) receiver patches sized in metres (e.g. 0.2 m), not faces, with a deterministic per-face split by area;
    - (iii) a visibility cache keyed on topology version, recomputed in the per-physics-step topology batch
      (world_model §6), or when a flame's bounding box changes bin.
  - With (i)–(iii), 10 flames × 20,000 faces ≈ 200k pairs: about 5 ms unoccluded, and occlusion amortised.
- **The 0.68–0.74 s `advance(0.5)` figure at 1.9×10⁶ cells** from the brief: I couldn't find it in
  `docs/architecture.md` at 124ad83, nor on `origin/main` (unverified). If it holds, the server is already over real
  time, and anything here must come with a cost-regression gate.

## 5. Recommendations for R0–R4

**Integrators:**
- In-depth conduction:
  - backward Euler, or θ = 0.55 with nodes guaranteeing Δt·α/Δx₀² ≤ ~1;
  - one linearisation of εσT⁴ at the front (FDS form);
  - a hand-written elementwise Thomas solve vectorised over surfaces, with no BLAS or LAPACK (the
    `splitting.md` §7 hazard);
  - one solve per substep, or once per physics step if the coupling allows.
- Pyrolysis and char oxidation per node: an exponential update at frozen T. The energy sink is computed from the
  mass actually consumed, so the ledger closes exactly. Patankar is the fallback where several sinks compete.
- **Every remaining explicit law** gets a stability bound with a **hard cap** on n, e.g. 16. When n would exceed it:
  - in tests, fail loudly with the offending cell;
  - in play, dilate world time (D21) and report it.
  - Never loop unbounded.
- **Area hygiene** (from §0):
  - route absolute powers by area share (W × A_part/ΣA), never W/A_part;
  - retire sub-parts below an area in metres, e.g. (1 mm)², merging their energy;
  - stability estimates count only parts above that area.

**Data layout:**
- Structure-of-arrays (N_nodes, M_surfaces) with surfaces contiguous.
- Surfaces sorted by an integer key (cell index, face), in a deterministic order.
- Surfaces are added and removed once per physics step in the topology batch.
- Fixed N per material class, on a grid defined in metres.
- No remeshing for charring wood (Gpyro's fixed Δz). Surface regression from char oxidation drops whole nodes by
  thickness in metres.

**Tests by rung:**
- **R0 ignition:**
  - closed forms: semi-infinite erfc profile, and t_ig = (π/4)kρc(T_ig − T₀)²/q″² for thermally thick solids (**M**,
    to verify);
  - band gate on ignition versus incident flux across 0.2 / 0.1 / 0.05 m;
  - subset-independence bits;
  - a CN ringing test, i.e. no surface cooling under constant heating.
- **R1 burning:**
  - char depth against a charring-rate closed form (EC5 β₀, **M**, to verify);
  - energy ledger to round-off;
  - flame-out time with Richardson p > 0.5 and shrinking differences (the bed.md failure as a regression);
  - an n-cap test that feeds a sliver area and requires a bounded n and a finite T.
- **R2 single-surface spread:**
  - spread rate converging across grids;
  - front offset tests at dx/3 and 2dx/3;
  - the reversed law tuple giving the same outcome class (`splitting.md` §6.4).
- **R3 two bodies:** §3 tests (a)–(d).
- **R4 crib:**
  - a cost-regression gate, ms per physics step at the 0.1 m tile with the crib burning, against a budget recorded
    in Known gaps;
  - a peak-memory gate;
  - a determinism replay across processes with different hash seeds;
  - CI thread counts 1/2/8 for any solver kept (`splitting.md` §7).

**Uncertain:**
- The 20,000-surface figure is an order-of-magnitude assumption, not measured from a scene.
- The flame-model shapes and χ_r come from other research tracks.
- I haven't tested whether a lumped δ_c char model and a full node grid give the same R1 outcome class. That should
  be measured before choosing between them.
