# Fire sub-steps 6.0–6.1: fuel objects, the solid and the cone tests (design, 2026-11-20, revised after review)

**Scope** (owner, "B plus C", `reviews/fire_model/fold.md`). The build spec for three pieces:
- **6.0a:** the data formats, their loaders and versions, and the field-registry entries;
- **6.0b:** fuel objects in their own store, contact coupling, insertion and the refusals;
- **6.1:** the 1D solid, verified against FDS and graded against cone data (R0 PMMA, R1 pine).

It follows `fire_model.md` v2 wherever it doesn't say otherwise. Flames, crib physics, radiation between objects,
acts and damage on objects, drawing objects and the NPC surface are out of scope (§7 names owners). A cone test
prescribes the heater and the flame's flux, so R0 and R1 need no flame object.

**Two references, kept apart:**
- **Verification:** our numerics against FDS 6.11.1 (NIST), on MaCFP's PMMA *gasification* inputs (§4.6).
- **Validation:** our physics against MaCFP's NIST gasification data and its multi-lab cone data (PMMA, white pine).

Tags: **V** primary source read, **S** secondhand, **M** memory (verify before it enters `data/`), **D** derived (our
scripts or FDS runs, under `_durable/fire_solid_review/scratch/`).

## 0. Landing order, and what exists today

Nothing 6.0 leans on is built at gates 396ae10:

| 6.0 needs | At 396ae10 | Comes from |
|---|---|---|
| Field registry | none | step 5a |
| Fixed physics step | a 6 s turn of 4, 16 or 64 heat substeps, `TEMPORARY(phase1/sim-clock)` | step 5a: 0.5 s (tile T3) |
| Intent log and header | none; no SHA-256 in `src/` | step 5a; field list in boundaries §6.3 |
| Digest | a test helper, `tests/test_determinism.py::digest`; no golden committed | step 5a's registry digest and replay goldens |
| Region ids | `CellStore._regions`, a dict of `Region` (mask, footprint, `solid`) | the u16 id array in world_model §10 row 4 (sim-clock = step 5a); the 5a checklist must add it |
| `topology_version`, refusal codes | none; `ActionRefused`, `SpecRejected` carry messages only | step 5a |
| The `imagine` intent | none; `imagination.place` has no caller in `src/` | step 5's applier, `place` as stage 2 (boundaries §5.3); no wire message in v0 (T16) |
| Save | none | step 9, save v0 |
| Table grammar | `encoding.snapshot` returns a dict of arrays | step 7 |

**The order:**
1. **6.0a lands on step 5a's line, after its field registry and before its log writer records the first golden.** It
   adds the data files, loaders, catalogue and registry entries for the fuel tables (declared reserved, as world_model
   reserves `loose`).
2. **6.0b lands after step 5b.** **6.1 follows 6.0b.**

**What the early landing buys:** the header's list of digested files is fixed before the first log, so no header
migration is needed. It doesn't prevent re-recording: any content change (6.1's fit) refuses older logs
(boundaries §6.3), by design.

**The plan's step 6 row** still reads "constants cited, never fitted … tile §6.3 passes at three grids". The commit
that accepts this design revises it and the 5a and 6 checklists (D-N5).

## 1. Fuel objects (6.0b)

### 1.1 The store and its tables

The tables live in a new **`FuelStore`**, not `CellStore`, whose body already has 10 of its 12 allowed public
members. A world-level window composes both stores: one owner, and a rollback across both. Each table is copied on its
**first write** in a window, not on entry, so a `strike` copies no node table. Copy plus freeze is about 1.2 ms for a
19 MB node table and 28 ms for 480 MB (D, DP FS-S5).

The tables are column-major numpy arrays, registered and sorted by integer key:

| Table | Key | Columns |
|---|---|---|
| `objects` | `object_id` u32 | `recipe_id` u16, `region_id` u16, `kind` u8 (`rod`, `slab`), geometry f64 per kind, `state` u8 (live, burnt out), `removed_kg` f64 |
| `segments` | (`object_id`, `seg`) | centre, normal, area; per part (unignited, ignited): area, `ignited`, node offset |
| `nodes` | (`object_id`, `seg`, part, node) | T f64 (K); per-component density f64 (kg/m³); thickness f64 (m) |
| `contact` | (cell, `object_id`, `seg`) | contact area f64 (m²); sorted COO, looked up by `searchsorted` |
| `pending` | `object_id` | accepted objects not yet inserted (§1.4) |

- **The object-id counter** is persisted. At 2³² − 1 the next insertion is refused (`object_ids_exhausted`), never
  wrapped.
- **Geometry per kind:** a `rod` is origin, unit axis, length and radius. A `slab` is origin, two unit edge axes,
  length, width and thickness. `bed` (6.2) adds its own columns.
- **Geometry is immutable in 6.0–6.1.** Regression changes node thickness only, and node thickness never feeds
  `contact`.
- **Node densities are the one mass truth.** An inventory is a `bincount` over nodes in key order, never stored.
  `removed_kg` (mass gone as gas) is stored, for `removed_with_mass`.
- **Burnt-out rows stay,** counted against the limits; removal is 6.2's.
- **`contact` is derived** (`derivation_version`, F15). It is rebuilt on an insertion and on a `topology_version`
  change (a destroyed floor cell drops its rows).
- **No per-cell CSR:** a row pointer costs 15.4 MB at the 1.92×10⁶-cell tile and 40 MB at 5×10⁶ (D, DP FS-S4).

### 1.2 Segments and nodes

- **A segment is a strip,** 0.02 m along a rod, or 0.02 m along a slab's length spanning its width, fixed in metres
  per recipe class. 200 m² of 0.5 m-wide slab is 4.8×10⁵ nodes as strips and 1.2×10⁷ as tiles: 14–25 against
  350–620 ms per step (D, DP FS-S6).
- **In 6.1 a segment flips whole at flash.** Its area and node profile move to the ignited part as a copy, so the
  front moves segment by segment. Partial transfer, with an enthalpy merge, is 6.2's (DP FS-S9). A zero-area part
  keeps its profile and is skipped; no flux is ever a mass rate over a vanishing area.
- **Nodes** are sized per recipe (first node ≤ √(α·1 s), FDS's rule, V; a stated stretch) and allocated at
  insertion, so preheating is kept.
- **Layout:** padded to the largest node count with decoupled identity rows, bit-identical to unpadded (D, DP probe
  f); the padded fraction is a work counter.

### 1.3 Representation, overlap, regions and limits

**Representation is authored.** Fuel recipes are objects at every spacing. Structural materials are cells (concrete,
steel, glass, drywall, and `wood` cells such as a plank wall). Wood cells keep today's thermal and damage laws and no
fire law; a burning wall is out of Phase 1, a Known gap (D-S4).

**Overlap is judged on authored geometry in metres, never on cells:**
- A fuel object may not overlap another fuel object, or any solid region's footprint, by more than 1 mm. That extends
  today's imagined rule (`imagination._within_world_rules` refuses overlap with a solid footprint). Containers
  (cardboard in the crate) come with 6.2's bed.
- A structural `place` may not overlap a fuel object. Today `_voxelize` tests `mask & grid.solid` only.
- An object partly outside the world is refused. Today's `place` catches only one entirely outside.

**Contact** between a segment face and a solid cell face needs a separation ≤ 1 mm and an overlap over 1 mm along
each face axis. Cell edges are integer micrometres (F13). By float edges, an object on [0.3, 0.5] m left a
5.55×10⁻¹⁷ m sliver at 0.1 and 0.05 m and none at 0.2 m (D, DP FS-S2). `holds_fuel` uses the same metric threshold.
It has no 6.0–6.1 consumer, so it is built with its first (6.2, or `kindle` in 6.4).

**Regions.** In 6.0–6.1 each fuel object names a new region (a scene's `region:` must not exist yet; a spec's
`name`, as today). A region is then cells only or objects only; mixing comes with 6.2.

**World limits** (`data/world/limits.yaml`) are checked before allocation by scene build and `place`:

| Limit | Value | Basis |
|---|---|---|
| Nodes, padded | 4.8×10⁵ | a 25 ms solid budget per 0.5 s step at 47–52 ns per Arrhenius node (D, DP FS-S6, load 2.2–2.6) |
| Segments | 2×10⁴ | nodes ÷ (12 nodes × 2 parts) |
| Fuel surface | 200 m² | 2×10⁴ strips of 0.02 × 0.5 m |
| Objects | 2,000 | `[engineering]` |
| Contact rows | per object, what it would need at 0.05 m | its geometry |

- **The contact bound is one number at every tier,** so a limit can't refuse at one spacing what it admits at another
  (Wire S10).
- **The values are provisional** until 6.1 measures the solid under B5. `imagination.Budget` keeps per-spec limits.

### 1.4 Insertion and `imagine` between steps

An `imagine` is applied in its own window, between physics steps:
- **An accepted object goes into `pending`.** Every check (overlap, limits, contact bound, region id) runs against
  the tables *plus* `pending`, in log order. Of two same-step `imagine`s that overlap or jointly pass a limit, one is
  refused.
- **The id is minted at acceptance** from the counter, which is in the window's rollback. A refusal consumes no id.
- **The batch drains `pending` in id order.** Ids only grow, so rows append and stay sorted.
- **`pending` is state:** digested, and a save requirement.
- **Scene build** inserts inside its construction window: a refusal on the third `fuel:` entry leaves the tables
  unchanged.

## 2. Occupancy, regions and the consumers

**Acts and readings stay on cells in 6.0–6.1.** An object-only region is refused by every act and reading with one
code, `fuel_only_region`, until 6.2 defines strike, fire and integrity on objects. `temperature_*` and the rest of
`frames.QUANTITIES` keep their cell-only meaning, pinned by a test. An object quantity, when needed, gets a new name
(F1) as a lab instrument under `tests/`, never in `QUANTITIES` or on an NPC builder (fire_model §5.5).

Each consumer that asks "is something here", read at 396ae10:

| Consumer | Today | 6.0–6.1 |
|---|---|---|
| `grid.Region.solid` | set once: at `paint` (`solid=mid != AIR_ID`), or `True` when imagined | unchanged |
| `applier._check_region` | refuses unknown, `not solid` ("is air"), `not cells.any()` ("is gone") | refuses `fuel_only_region` first |
| `applier._on_region` | strike-point ownership from footprints and others' `solid`; refuses nothing | unchanged; no fuel sits in a solid footprint |
| `World._power_field` | `frac * grid.solid`, falling back to air (Known gap) | unchanged; guarded (§3.1) |
| `bridge.region_parts`, `StructureModulator` | `frame.is_solid`; an instrument per `QUANTITIES` entry; `strike`, `ignite`, `extinguish` | `region_parts` refuses an object-only region; affordances pinned |
| `frames.Frame.reading` | cell reductions; `region_integrity` is 0.0 with no solid cells | refuses an object-only region, never 0.0 |
| `Frame.is_solid`, `Observation.is_solid`, `CellFrame.solid` | cells | unchanged |
| `damage.strike`, `region_integrity`, `region_breached`, `thermal_degrade` | `grid.solid` | unchanged; objects take no damage (6.2) |
| `grid.destroy` | solid cells become air | bumps `topology_version`, rebuilding `contact` |
| `scene._check_no_solid_overlaps`, `imagination._within_world_rules`, `_voxelize` | boxes, footprints, cells | plus §1.3's metric rules |
| `encoding.snapshot` | `* frame.solid` masks | unchanged; no objects on the wire (§5.6) |
| The digest (today's helper hashes `region.solid`) | cells, regions, sources, clock | plus `FuelStore`; empty tables add no bytes |
| `kindle`'s target (fire_model §2.2) | none | 6.4 (Bio N1), by a metric nearest-surface query |

## 3. Coupling between objects and the grid

### 3.1 The ambient rule, for Phase 1

**Every exposed object surface loses h_c(T_s − T∞) + εσ(T_s⁴ − T∞⁴) to the ambient reservoir:** tile 6a (§1.2,
§5.2) on object surfaces, booked as tile §5.4's `open_air_loss`. Nothing an object loses enters an air cell.
- **Why:** Phase 1 air has no advection, so heat put into it pools by an amount set by dx. `World._power_field`
  refuses air for the same reason. For a cone sample the rule is literally true.
- **It is permanent for Phase 1,** a Known gap rather than a `TEMPORARY` marker, recorded in `docs/architecture.md`
  in 6.0b's commit with its costs:
  - hot gas never preheats fuel: an object at 200 °C inside 200 °C cells still loses about 4.5 kW/m² (2.3 convective,
    2.2 radiative; D, Physics §4);
  - a fire-heated wall radiates nothing to an object;
  - an object boxed in by solid cells still loses to the outside.
- **The plume** leaves the open-topped alley (tile §1.2). Preheating from hot gas would be a new law 6.2 may design,
  not a stub it owes.
- **The guard:** a test sums each law's power into `material == AIR_ID` cells and requires zero, except
  `_power_field`'s fallback, whose Known gap has its strict red gate
  (`tests/test_cross_tier.py::test_a_fire_that_has_burned_its_fuel_stops_heating`). Sending an object's loss to its
  cells turns it red.

### 3.2 Contact conduction through a skin sized in metres

A segment touching a solid cell (a slab on the floor) exchanges heat with that face's **skin**, not the cell mean.
- **Why:** the cell mean gives a resistance of about (dx/2)/k: about 14·ΔT W/m² at 0.2 m and 56·ΔT at 0.05 m,
  against a closed form of 39·ΔT at 600 s (D, Physics S9).
- **The skin** is world_model §3's: a 1D profile into the face, 25 mm deep (half the finest cell, so it fits in
  every cell), held in world_model §8's face table. Its far node couples to the cell mean, and its energy above the
  mean is Δ(skins) (tile §5.4). 6.0b builds skins on contact faces only. Skins and 6a on every structural face stay
  with step 6 under the 6.2 design (A-S2, D-S3).
- **The scheme:** contact is a Robin condition inside both implicit solves (object and skin), with the other side's
  temperature frozen at the step's start; the cell side gets exactly the node's negated gain, as the same f64
  expression. Explicit exchange would sit at h_c·Δt/C_node ≈ 0.9 for PMMA's first node at 1,000 W/m²K (D, DP
  FS-S12).
- **Frequency:** the solid and contact run once per 0.5 s physics step, as a law in 5a's list before heat. §6 checks
  it on the floor scene, where something couples.

**dx enters 6.0–6.1 only** through contact rows, the skin's far boundary and the straddle test; the cone tests are
grid-free unit tests (Executor S11).

## 4. The solid (6.1)

### 4.1 Conduction and absorption

- **Conduction:** 1D in depth per part, backward Euler in delta form, one linearisation of εσT⁴ at the front, and a
  hand-written Thomas solve with no BLAS. The matrix is strictly diagonally dominant for positive k and c, so no
  conditioning bound is needed (Wire N-N1). k(T) and c(T) are RAMPs where a set has them; the PMMA sets here have
  constant k and c, and only their Kaowool backing has RAMPs (V).
- **In-depth absorption is implemented.** MaCFP's black PMMA sets absorb in depth (`ABSORPTION_COEFFICIENT` 2,620
  m⁻¹ NIST-StMU-FSRI, 3,421 Aalto; V). Surface absorption moves FDS's peak by −6.2% and +42 s at 50 kW/m² (D,
  Executor B2), an error that would land in q''_fl. We implement FDS's in-depth model as its Technical Reference
  Guide defines it (two-flux, M; read V before coding). It adds one source term per node, and κ → ∞ recovers surface
  absorption, which pine's opaque sets use.
- **Back face:** per dataset. The gasification inputs' Kaowool and aluminium are that apparatus's backing. Cone
  backings differ by lab: 25.4 mm Kaowool (NIST), 13 mm Superwool (DBI), vermiculite and a frame (UQ) (V).

### 4.2 Kinetics: published Arrhenius with a written cutoff

- **One rate law,** FDS's n-step Arrhenius, r = A·(ρ_s/ρ_s0)^n·ρ_s0·e^(−E/RT). The threshold law (a) is dropped:
  with published kinetics (§4.5) it has no source for T_p and L_g, and the cutoff gives the same quiescence.
- **The cutoff:** below T_cut, where A·e^(−E/RT_cut) = 10⁻⁹ s⁻¹ `[engineering]`, the rate is exactly zero. T_cut is
  written per reaction with its provenance, so a cooled profile is exactly quiescent. It is applied with `np.where`
  over the full array, never a gather.
- **The frozen-T update is exact for any n:** ρ_new = max(0, ρ^(1−n) − (1−n)kΔt)^(1/(1−n)), exactly 0 past the
  depletion time ρ^(1−n)/((1−n)k). The naive form gave 155 kg/m³ from 10⁻³, or NaN (D, DP FS-S1). The heat sink
  comes from the mass consumed.
- **Residue:** char at yield χ, or the set's inert fraction (NIST-StMU-FSRI's `PMMA3`, 0.01; V). Char oxidation is
  off, so windows end before it matters.

### 4.3 Regression and the time step

- **Regression:** a non-charring node's thickness scales with Σ(ρ_i/ρ_i,virgin). Below 1% of its initial thickness,
  the surface node's mass and enthalpy move, as exact sums, into the next node, which becomes the surface. FDS
  remeshes instead (M). Without a rule a fixed mesh pulses, about 40 s per 0.33 mm PMMA node at 10 g/m²s (D,
  Physics S8). The FDS runs go to burnout, so they exercise it.
- **The step:** once per 0.5 s physics step (T3), independent of dx and heat's substeps. FDS's peak moves 4.4%
  between DT 0.01 and 0.5 s (D, Physics §0) and our scheme is first order, so §6 runs dt, dt/2 and dt/4. If 0.5 s
  misses, the pre-registered fallback is a fixed substep count in seconds, reported to the owner; the tolerance is
  never widened.

### 4.4 Ignition, the flame's flux and extinction, in a cone

- **Pilot:** the cone's spark, present by definition; unpiloted ignition is refused (fire_model §3.2). It adds no
  energy, so it has no ledger line (Physics N3).
- **Flash:** a segment's unignited part attaches a flame when its per-m² mass flux reaches m''_flash.
- **While flaming,** the part gets a prescribed flame flux q''_fl, as a gauge would read it, and its convective loss
  is off: the flame sits on that surface (Physics S4). Re-radiation stays.
- **Extinction:** when the flaming part's mass flux falls below m''_ext.
- **Hysteresis:** the loader refuses m''_ext ≥ m''_flash. That is a pre-registered model choice (a flame, once
  attached, holds below the flux that lit it; M). The data agree for pine: first-crossing t_ig puts flash at ≥ 24
  kW/m² ÷ ΔH_c,eff ≈ 1.5–1.8 g/m²s (D, ΔH_c,eff 13.2–16.4 kJ/g), and heater-on flame-out at 0.8–1.3 (below).
- **No toggling.** After flash, q''_fl raises m'', so a new flame starts above m''_ext, and a reflash must climb the
  whole band. R0 and R1 count flashes per part and require at most one.
- **The exposing test** (§6): class and t_ig agree at dt and dt/2; it is proven by setting m''_ext above m''_flash.

**m''_ext comes from pine's own data,** not V7 1's 2.7–8.3 g/m²s CLT step-down band. At 25 kW/m², MaCFP-4's flames
persist to about 1 g/m²s (D, Executor S1, ±30 s mass differences over 0.01 m²):

| 25 kW/m², parallel | FSRI R1 | FSRI R2 | FSRI R3 | IMT R1 | IMT R2 |
|---|---|---|---|---|---|
| Recorded flame-out (s) | 2,280 | 2,132 | 2,050 | 2,301 | 2,178 |
| m'' there (g/m²s) | 0.93 | 1.17 | 0.78 | 1.33 | 1.17 |

- **25 kW/m² is graded, so these come second.** m''_ext is first measured the same way from the fit fluxes' recorded
  flame-outs (30, 60 kW/m²). The 25 kW/m² values check that it is one property of the species.
- **If the fit-flux tests record no flame-out,** the 25 kW/m² median (1.17) is used, and the result names that leak.
- **PMMA's window ends at its peak** (§4.5), so nothing sees m''_ext. It is held out of the fit and unset; the runs
  assert m'' never falls after flash inside the window.

### 4.5 Fitting, held out

**Fixed, not fitted:** kinetics, ΔH_r, k, c, ε and κ, from one MaCFP set calibrated without cone data.
- **PMMA:** NIST-StMU (TGA, DSC, MCC and literature; V, `MaCFP_PMMA_NIST-StMU.json`).
- **Pine:** one of `Wood/Material_Properties/`'s 12 sets (V), named before the fit. A cone-calibrated set
  disqualifies itself. If none qualifies, pine's kinetics join the free list; then the count rule must still hold, or
  R1 goes to the owner.

**Free:** PMMA q''_fl and m''_flash; pine q''_fl, m''_flash, k_c and char ε.
- **m''_flash** ranges from 24 kW/m² ÷ ΔH_c,eff (lower, flaming wouldn't register) to 2.5 g/m²s (M).
- **q''_fl is one fitted constant per material, flagged as fitted in every result.** Its 15–30 kW/m² range is L1 §6's
  recommendation; its only verified data are McKinnon's *cardboard*, 17.2 kW/m² at 20 and 29.9 at 60 (V via L1
  §2.3). It rises with the heater, so a constant may fail across fluxes, which PMMA's reverse fit tests.

| Material | Fitted on | Graded on (held out) | Graded features |
|---|---|---|---|
| Black PMMA, MaCFP-2 | 25 kW/m² | 50, 65; then the reverse (fit 65, grade 25). Both must pass | t_ig, peak m'', its time, mass lost at the data's peak time |
| White pine, MaCFP-4, parallel | 30, 60 (Aalto, FZJ) | 25, 50, 75 (FSRI) | t_ig, first-peak m'', plateau m'' |

- **More features than parameters:** PMMA 4 at its fit flux against 2, pine 6 against 4. A fit that breaks this
  doesn't run.
- **t_ig is MaCFP's: the first time Q'' reaches 24 kW/m²** (V: `Scripts/MaCFP-4/Cone_analysis.py`,
  `df[df['HRR (kW/m2)'] >= 24].index[0]`). The model's Q'' is m''·ΔH_c,eff over the flaming area per sample area,
  with ΔH_c,eff from the fit fluxes only. The time to sustained flaming is a second, ungraded number: FSRI pine R3 at
  25 kW/m² crosses 24 at 27 s and sustains from about 57 s (D).
- **Windows:** pine from 0 until the data's MLR first falls below 2.7 g/m²s (1,727–2,050 s at 25; D), after which
  char oxidation carries the HRR; pine is graded on MLR. PMMA from 0 to the data's peak time.
- **Sustain is gated with a margin:** min m'' over the window ≥ 1.1·m''_ext.
- **Back-face features** (PMMA's rise, pine's second peak) are graded per lab with its backing, or reported
  ungraded; never against an envelope mixing backings (Physics S6).
- **The fitter is pre-registered:** objective, bounds and several seeds, with the held-out spread reported. It never
  sees a graded flux, and nothing graded sets a bound but §4.4's named fallback. A fit at a range's edge is a
  flagged pass that goes to the owner.
- **The heater removed** has no MaCFP-4 data: a prediction, not graded.
- **Lab and flux are confounded:** held-out pine fluxes are FSRI's alone; PMMA at 50 kW/m² has two labs (DBI_Lund,
  ULSTER; V). Results are per lab.
- **First, flame-free:** the solid is validated against MaCFP's NIST gasification data (`PMMA/Validation_Data`, 25
  and 50 kW/m²; V), so its errors can't hide in q''_fl.

### 4.6 FDS verification, in the configuration we implement

- **The cases:** MaCFP's NIST-StMU-FSRI inputs are anaerobic gasification (`SOLID_PHASE_ONLY=T`, h = 13 W/m²K,
  constant flux) at 25 and 50 kW/m²; no input has a flame, and none is at 65 (V, Executor B1). We run them as
  shipped, with in-depth absorption on both sides. 65 kW/m² isn't verified, and neither is the flame path.
- **Same layout:** the inputs set `STRETCH_FACTOR=1`, and so does our solver here. FDS's default stretch 2 moves the
  50 kW/m² peak −2.8% and −11 s (D, Executor S9).
- **At 25 kW/m², `T_END` = 1,500 s:** the shipped 800 s ends before the peak, at about 890 s (D).
- **Tolerance from FDS's own spread,** about twice it, set before our solver runs. Each pair is the inputs' cells
  against `CELL_SIZE_FACTOR=0.5` (D; the 25 kW/m² pair is in `scratch/fold/`, the 50 pair is Executor's):

| Feature | Spread at 25 | Spread at 50 | Tolerance |
|---|---|---|---|
| Peak m'' | 10.03 → 9.92 g/m²s (1.1%) | 31.99 → 31.71 (0.9%) | 2.5% |
| Time to m'' ≥ 1, ≥ 2.7 g/m²s | 1.5 s, 1.5 s | 0.5 s, 1.0 s | 3 s |
| Time to half the peak | 352.5 → 354.0 s | 126.0 → 126.0 s | 3 s |
| Surface T at 300 s | 348.0 → 351.1 °C | 398.2 → 404.1 °C | 12 K |
| Mass lost at 300 s | 1.2% | 1.3% | 2.5% |
| Peak time | not graded: within 1% of peak over 797–984 s | 346.0 → 349.5 s | 8 s |

- **dt:** FDS runs at the inputs' 0.01 s, ours at a converged step; the shipped 0.5 s meets the same tolerance
  against that run.

## 5. Formats

### 5.1 Data files and loaders (6.0a)

All loaders are in `adapters/loaders.py`, the one input gate. New formats start at `version: 0`, as every format here
did.

| File | Format | Loader | Holds |
|---|---|---|---|
| `data/materials/core.yaml` | v0, unchanged | `load_materials` | today's fields; no bump, so `materials_v0_to_v1` is dropped (Wire S4) |
| `data/materials/chemistry.yaml` | v0 | `load_chemistry` | components and species by name with declared ids; Arrhenius reactions with T_cut; the RAMP schema; fire_model §9.1's per-file refusals |
| recipe files, one per recipe | v0 | `load_recipes` | a declared `id`, representation, components, admitted kinds, geometry ranges, segment class, node rule, and its `variants:` |
| `data/world/limits.yaml` | v0 | `load_world_limits` | §1.3's limits |

- **Variants live in their recipe file,** which deletes a cross-file reference.
- **One catalogue owns the cross-file references:** `FuelCatalogue`, a validating constructor over all loaded tables,
  all or nothing, with a gate row. It refuses, each with a test:
  - `dangling_reference`;
  - `name_in_two_namespaces` (a recipe named `wood`, a material; Wire N-S6);
  - `duplicate_id` (retired ids are listed, like 5a's retired verbs);
  - `variant_bounds` (min > max, non-finite, a default out of bounds);
  - `range_exceeds_limits`;
  - `joint_loading`, checked at every corner of the variant box: loadings past the void, inconsistent bulk density,
    retention caps (Wire N-S5).
- **Recipes load in sorted path order,** and ids come from the files, never glob order. The game's recipes arrive
  with `content/` at step 8. Engine tests use Apache fixtures under `tests/fixtures/fire/`, beside the cone fixtures.
- **The shipped-data test** keys readers by directory; 6.0a keys it by file, and an unowned file stays an error.
- **The log header** records each file by logical name (no path), its version and the SHA-256 of its canonical loaded
  value (boundaries §6.3), plus one digest over the sorted recipe set (Wire S7).
- **The FDS outputs and MaCFP data** committed as fixtures are listed with source and licence first (A-N6).

### 5.2 Scene and spec (6.0b)

- **Scene:** `SCENE_VERSION` is 0. Tile §1.3's planned v1 (step 3b part b, not coded) makes the crate `material:
  wood, bed: {...}` cells, which §1.3 forbids. Tile §1.3 drops `bed:` (done with the acceptance, 2026-11-20); 3b part b ships v1 without it.
- **`fuel:` entries** enter the scene version after the one on `main` when 6.0b lands: a recipe by name, an admitted
  `kind` (`rod` with a finite non-zero axis, or `slab`), metric geometry, a new region. Scenes are repo-only, so the
  older version gets a bump and a refusal test, not a migration (`checklists.md` 3b).
- **Spec v1:** `name`, recipe, admitted kind, geometry in range and closed variant keys; out of range is refused,
  never clamped; checked against `Budget` and the remaining limits with `pending` counted. Structural imagining keeps
  today's unversioned `{name, primitives}`, which nothing persisted, so no migration (Wire N-S6).
- **The caller** is step 5's `imagine` intent, reached in Phase 1 only through logged intents and tests (T16): a thin
  caller (A-S6, D-S11).

### 5.3 Refusal codes

Appended to 5a's list, each tested at its gate:
- **Acts and readings:** `fuel_only_region`.
- **Spec and scene:** `unknown_recipe`, `kind_not_admitted`, `geometry_out_of_range`, `bad_axis`,
  `unknown_variant`, `variant_out_of_range`, `joint_loading`, `overlaps_fuel`, `overlaps_solid`, `outside_world`,
  `region_exists`, `spec_budget`.
- **Limits:** `world_limit_objects`, `_segments`, `_nodes`, `_area`, `_contact`; `object_ids_exhausted`,
  `region_ids_exhausted`.
- **Loaders:** `version_unknown` per file, and §5.1's catalogue codes.

### 5.4 Digest and ledger

- **Digested:** every `FuelStore` table but `contact` (derived), with `pending` and the counter. Empty tables add no
  bytes.
- **Reductions** over objects or nodes are `bincount` or fixed-order sums over the full table in key order, never
  `np.sum` over a gathered subset (DP-S2: 56 of 200 mismatches).
- **Ledger,** in tile §5.4's equation:
  - storage: Δ(nodes) sensible, Δ(inventory) at reference enthalpies, Δ(skins);
  - input: `incident_absorbed`, which only the cone harness supplies in 6.1, its test ledger naming the heater and
    the prescribed flame;
  - output: `open_air_loss`, `contact_to_cells`, `pyrolysate_out` (gas products at their temperature),
    `removed_with_mass`.

  `combustion`, `plume_convective` and `flame_radiative` stay 6.2's.

### 5.5 Save requirements, handed to step 9's save v0

6.0–6.1 builds no save. Step 9 takes:
- a version, a loader (decoding in loaders, construction in the core), a gate row, a round trip and a golden;
- every `FuelStore` table but `contact`, plus `pending` and the counter; `contact` rebuilt on load, never read;
- name maps for `recipe_id` and `region_id`, remapped by name;
- offsets monotone, in bounds and matching the segments' parts; per-part node counts equal to the recipe's node rule
  for the saved geometry; thicknesses positive and summing; part areas summing; the counter above the largest id;
- **conservation, never "sums to the recipe's mass":** the initial mass, recomputed from geometry, recipe and
  variants, equals Σ(node mass) + `removed_kg` within 10⁻⁹ relative `[engineering]`, which 6.1 measures and
  tightens;
- a changed node rule: the saved layout is the truth; refuse or migrate, never re-derive silently.

Until then, §6 tests that **the digest after a rebuild from the tables equals the running digest.**

### 5.6 Snapshot requirements, for the client pass and step 7

6.0–6.1 sends no objects. The client design pass (before step 8) and step 7's grammar take:
- **`objects`:** `object_id` u32, `recipe_id` u16, `region_id` u16, `kind` u8, geometry per kind as f32 metres.
- **`segments`:** (`object_id`, `seg`); `surface_temperature_c` **f16** clipped to [−273, 6000] like `temperature_c`
  (a u8 clips every ignited surface at 255 °C); `ignited_fraction` u8 in 1/255.
- **Column-extensible tables,** so D-B2's char column needs no bump. `welcome` carries the recipe name↔id map. The
  budget per profile is B5's. `burning` stays reserved.
- These names supersede fire_model §9.2's `segment_glow` and `burning` (Bio N2).

## 6. Tests

| Test | What it proves | How it fails |
|---|---|---|
| Thick and thin t_ig closed forms (losses off); the erfc profile at 60 s | conduction, node sizing | a wrong ρc or node rule |
| Inert slab, κ finite, then κ → ∞ against surface absorption | in-depth absorption | a misplaced source |
| Delta-form equilibrium, 200 steps at ambient | no drift | the full form drifted 200 of 200 (DP-S1) |
| Ambient rates exactly zero; an n = 0.5 node depletes to exactly 0 | cutoff, positivity | the naive form's 155 kg/m³ or NaN |
| dt, dt/2, dt/4 on t_ig and peak m'' | the shipped step | error past §4.6's tolerance |
| Nodes halved, on R0's and R1's classes and times | node independence, regression | a node-scale threshold, pulsing |
| FDS verification (§4.6) | numerics against a reference | outside tolerance |
| NIST gasification validation | the solid without q''_fl | yes |
| **Flash at 0.5 s and 0.25 s steps:** same class, t_ig within max(0.5 s, 3%), ≤ 1 flash per part | no step-period toggling | proven with m''_ext > m''_flash |
| R0 and R1 held-out grading | physics against data | yes |
| **Non-uniform heater:** a 0.3 m slab under a linear 25 → 50 kW/m² heater, averaged exactly per segment; segments halved; times to 25, 50, 75% ignited area within max(1 s, 5%) | segment independence with a moving front | centre sampling, indexing, area transfer |
| Straddle: a slab across a cell boundary at dx/3 and 2dx/3, at 0.2, 0.1, 0.05 m, on concrete | contact area equal to 10⁻¹² relative; floor heat at 600 s within 5% of 0.05 m | cell-centred rows, slivers, a cell-mean law |
| Contact closed form, slab at fixed T on a concrete block, each dx | within 3% of 39·ΔT W/m² at 600 s | the cell-mean law, up to 4× off |
| **Coupling frequency:** a slab on the floor heated through contact, per 0.5 s step against fixed 0.05 s substeps | slab and floor-face T at 600 s within 1 K; floor gain = slab loss and > 10% of the slab's heat | deleting coupling fails the second clause |
| No law heats air cells | the ambient rule | an object's loss sent to cells |
| No fuel → 5a's replay goldens unchanged | identity | an empty table adding bytes |
| **Rebuild digest = running digest,** every step of a 0.1 m floor scene with a mid-run `imagine` and a burnout | the tables are the whole state | a missing column, `pending` or counter |
| Hypothesis: Σ node mass + `removed_kg` = initial; incremental `contact` = full rebuild | one mass truth; derived rows | yes |
| Two same-step `imagine`s, overlapping or jointly over a limit; a scene failing at its third entry | `pending`; all or nothing | yes |
| Every §5.3 code at its gate | the trust boundary | yes |
| `QUANTITIES` and affordances exactly today's; object-only regions refused | the instrument pin | proven by adding a quantity |
| Work counters at the world limits: node-steps (real, padded), `exp` calls, contact rows, topology events, bytes copied per window; B5 `process_time` second | cost | any increase |
| Offset and subset (D1-S9), CI matrix, 1 and N threads | position independence | `exp` tails on x86-64 |

## 7. Owners

This review's findings are in `reviews/fire_solid/fold.md`. Every delta-round-1 id (`reviews/fire_model/`):

| Owner | Findings |
|---|---|
| This design | P2-B1, D-B1, NB1 (§3.1); NS1, P2-B2 (§4.4); N-B1, N-B2 (§1.3, §1.4); NS2, WT-B1, N-S1 (§2); N-S4, D-S1 (§0, §5.1); N-S5, N-S6, N-N4, D-S11 (§5.1, §5.2); N-S3, D-N1 (§5.6); N-S7, D1-S4 (§1.1, §5.5); N-N1 (§4.1); P2-S3, D1-S9, NS6, NN6 (§6); P2-S2 (§3.2); NN4 (§4.5); D-S4 (§1.3); D-S6 (§1.1, below); D-N5 (§0); P2-N1 (§4.4, the cone's spark) |
| The 6.2 design | D1-B1, D1-B2, D1-S1, D1-S3, D1-S5–S8, D1-N1–N3, D-S10, P2-S1, P2-S4, P2-S5, P2-S7, P2-N2, P2-N3, NB2, NS3–NS5, NS7, NN1–NN3, N-N3, D-S8, D-S9 (with the owner), A-S4 (round 1); D1-S2 (6.1 runs awake); P2-S6 (also §3.1's Known gap); D-S3 (every structural face) |
| 6.4, with `kindle`'s pilot | A-S2, NS8, D-S5 (red gates, `TEMPORARY` ceilings); N-S2, N-N2, NN5 |
| fire_model's next revision, before the 6.2 design | D-N2, D-N3 (`douse` lands with 6.2's acts), D-N4, NN7 |
| The tile §6 revision, before 6.4 | D-S2 |
| The client design pass, before step 8 | D-B2 |
| A note to the step 5 plan, before vocabulary v1 | D-S7, WT-S5 |

**The NPC fire note** owns Bio delta-1 S2, S7, N3, NB1, NB2, NS1–NS5 and NN1–NN4. **Trigger:** ruled before step 5
ships vocabulary v1 and before any MP-* draft enters `docs/maxim_upstream/`. 6.0–6.1 doesn't block on it because the
bridge, `QUANTITIES` and the affordances stay untouched (§2), so NS3 isn't widened. The note decides the SEM read path
for segment temperature; fire_model §2.2's "SEM … read" is corrected in fire_model's next revision.

**Placement** (boundaries §2.2's layers; today's modules):

| Code | Layer | Module |
|---|---|---|
| Recipe, component, reaction and limit types; `FuelCatalogue` | 1 | `core/chemistry.py`; `WorldLimits` in `core/limits.py` |
| Rod and slab geometry; metric overlap and contact tests | 2 | `core/fuel_geometry.py` |
| `FuelStore`, tables, `pending`, window | 3 | `core/fuel.py` |
| The solid: conduction, absorption, kinetics, regression, flash, extinction | 4 | `core/solid.py` |
| Contact rows, skins, exchange | 4 | `core/coupling.py` |
| Scene `fuel:`; spec v1 | 5a | `core/scene.py`, `core/imagination.py` |
| `fuel_only_region`, insertion, the composed window | 6 | `core/applier.py`, `core/world.py` |
| Loaders | 7a | `adapters/loaders.py` |
| The cone harness (heater, prescribed q''_fl, spark) and its test ledger | — | `tests/fire/` |

The core keeps its banned imports: no IO, no clock.

## 8. What 6.0–6.1 doesn't show

Whether fire spreads, sustains in a crib or glows. A lone slab that flames out when the heater goes is the expected
answer, and it passing says nothing about the crate. That question belongs to 6.2 onward, designed from what R0 and
R1 measure.
