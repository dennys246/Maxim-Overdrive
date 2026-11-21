# Fire sub-steps 6.0–6.1: fuel objects, the solid and the cone tests (design, 2026-11-20)

**Scope** (owner, "B plus C", `reviews/fire_model/fold.md`). This is the build spec for two sub-steps:
- **6.0:** fuel objects, segments, coupling, occupancy and the formats;
- **6.1:** the 1D solid, graded by the cone tests R0 and R1.

It follows `fire_model.md` v2, the direction, wherever it doesn't say otherwise. Flames, crib physics, radiation
between objects, the client's drawing of objects and the NPC surface are out of scope (§7 says which document owns
each open finding). R0 and R1 need no flame object: a cone test prescribes the heater and the flame's flux.

**Two references, kept apart:**
- **Verification, our numerics against FDS.** FDS 6.11.1 (NIST) runs the same 1D cases with the same parameters,
  and our solver must reproduce its curves.
- **Validation, our physics against measurements.** MaCFP's multi-lab cone data (PMMA, white pine).

MaCFP ships FDS cone inputs for black PMMA (`matl-db/PMMA/Validation_Results/`, NIST-StMU-FSRI and Aalto sets); one
ran here in 13 s. Pine has fitted property sets but no FDS inputs, so we write those ourselves.

## 1. Fuel objects

### 1.1 Tables

All tables are column-major numpy arrays inside `CellStore`'s write window, named in the field registry (O34), and
sorted by their integer key. Rows are inserted and removed only in the per-step topology batch.

| Table | Key | Columns |
|---|---|---|
| `objects` | `object_id` u32 (from a persisted counter, never reused) | `recipe_id` u16 (resolved by name, §5), `region_id` u16, `kind` u8 (`rod`, `slab`), geometry f64 (origin, axis, length, radius or thickness, width), `state` u8 (live, burnt out), per-component inventories (kg) |
| `segments` | (`object_id`, `seg`) | geometry in metres (centre, normal, area); front position f64 in [0, 1] along the segment; per part (ignited, unignited): area f64, node offset into `nodes` |
| `nodes` | (`object_id`, `seg`, part, node) | T f64 (K); per-component density f64 (kg/m³ of the node's volume); node thickness f64 (m) |
| `coupling` | (cell index, `object_id`, `seg`) | overlap weight f64, rebuilt in the topology batch from geometry; CSR offsets per cell |

- **Segment size** is fixed in metres per recipe class (default 0.02 m along a rod or across a slab), never by cell.
  6.1 tests the size: halving it must keep R0's and R1's classes and graded times within tolerance (physics delta S).
- **Nodes** are sized in millimetres per recipe (FDS's rule: the first cell ≤ √(α·1 s), stretch 2 toward the core,
  V per L5 §1). They are allocated from authoring, so preheating before ignition is kept.
- **Inventories** are kg per object, held per node, never kg/m³ of a world cell.
- `bed` objects (the crate) come with 6.2/6.4, not here.

### 1.2 Representation is authored, never chosen by size

A recipe declares its representation: **fuel** recipes are always objects, **structural** recipes are always cells
(concrete, steel, glass, drywall, and wood *cells* such as a plank wall). An imagined or authored fuel recipe becomes
an object at every grid spacing, whatever its size (Wire N-B1). Structural wood cells keep today's thermal and
damage laws and no fire law; a burning wall is out of Phase 1, and the Known gap says so (Architecture D-S4).

### 1.3 Overlap and limits

- **No overlap.** A fuel object may not overlap another fuel object's volume, or a solid cell, beyond contact. The
  tolerance is 1 mm in metres; overlap is refused at authoring and at `imagine` (Wire N-B2). It may sit inside an
  owner's footprint where that footprint is air (cardboard in a crate).
- **World limits**, declared in a new `data/world/limits.yaml` and checked before allocation: objects, segments and nodes,
  plus surface area per world. Each `imagine` checks its own spec budget *and* the world's remaining limits, so
  repeated in-budget calls can't grow the tables without bound.
- **Saves** carry the object-id counter. Saved rows are validated like authored ones: the geometry ranges, the
  recipe's admitted kinds, overlap, and inventories ≥ 0 that sum to the recipe's mass. Size alone isn't enough.

## 2. Occupancy, regions and the consumers

**Occupancy.** `occupied(cell) = solid(cell) | holds_fuel(cell)`, where `holds_fuel` is true if any coupling row with
weight > 0 names the cell. **Region membership** is two sets: the cells whose u16 `region` channel names the region
(one owner per cell, unchanged), plus the objects whose `region_id` does. Each reduction joins the two explicitly.

Every consumer that asks "is something here", read at gates 396ae10 (Executor delta NS2), switches to an explicit
rule, each with a test:

| Consumer | Today | After |
|---|---|---|
| `grid.Region.solid` and `Region` construction | cells whose material isn't air | cells, plus a `fuel_objects` index |
| `applier._check_region`, `applier._on_region` | refuse an air region | refuse only a region with no solid cells and no objects |
| `bridge.StructureModulator.__init__`, `region_parts` | `cells.any()` on solid | the same join |
| `frames.CellFrame.reading` | region cell masks | adds object reductions for the quantities objects carry (`temperature_*` over segments' surface nodes) |
| `damage.py` (strike, breach, `region_integrity`) | cells only | **unchanged in 6.0:** fuel objects don't take strike or breach damage yet, a named gap owned by the 6.2 design (Architecture A-S4) |
| `scene._check_no_solid_overlaps`, `imagination`'s overlap rule | solid boxes | §1.3 |
| `encoding.snapshot` (`× solid` masks) | cells | cells unchanged; objects travel in their own table (§5.3) |

## 3. Coupling between objects and the grid

- **Conduction.** A segment touching a solid cell (the crate on the concrete floor) exchanges heat by contact
  conductance across the overlap area, with the cell's temperature. That keeps V_floor meaningful.
- **Convection and re-radiation** go to the surroundings at **ambient T∞ (the outside reservoir)**, never into air
  cells. This is a stated Phase 1 simplification, and it settles the gas-sink blocker for 6.0–6.1 (Physics P2-B1,
  Architecture D-B1, Executor NB1): heat entering air cells has no Phase 1 sink, so pooled air would heat fuel by an
  amount set by dx. The cost: hot gas doesn't preheat fuel above it. Delivering that heat is the plume's job, and the
  6.2 design owns it. The ledger books it as `open_air_object`.
- **This is where dx enters 6.0–6.1:** the coupling weights for contact, and the straddle test (§6). R0 and R1 are
  otherwise grid-free, so they are unit tests with a cross-grid straddle check. That is said, not hidden (Executor
  S11).
- **Frequency.** Objects couple once per physics step. R1 compares that against a run coupled at every heat
  substep; a class or a graded time outside tolerance fails 6.1. The high-area bed instability (DP D1-S3) belongs to
  6.2.

## 4. The solid (6.1)

### 4.1 Conduction and kinetics

- **Conduction:** 1D in depth per part, backward Euler in delta form, one linearisation of εσT⁴ at the front, and a
  hand-written Thomas solve with no BLAS. Properties may depend on temperature (k(T), c(T) as RAMPs, as MaCFP's sets
  do).
- **Kinetics:** both candidates are built:
  - **(a)** a threshold law, at T_p with an intrinsic L_g, exactly zero below T_p;
  - **(b)** n-step Arrhenius, as the MaCFP sets use (FDS's form r = A·ρ^n·e^(−E/RT)), with a written cutoff below
    which the rate is exactly zero.

  Each node updates exponentially at frozen T, and the sink comes from the mass consumed. R0 chooses between them
  on fit, held-out agreement and cost: work counters, and whether a cooled profile can be exactly quiescent (DP
  D1-S2).
- **Residue:** char at yield χ, or none (PMMA). Char oxidation is off in 6.1; the cone tests are graded in flaming
  and up to the heater's removal.
- **Back face:** the backing is specified per dataset (MaCFP's insulation layers, as in its FDS inputs).

### 4.2 Ignition, the flame's flux and extinction, for a lone surface in a cone

- **Pilot:** the cone's spark, present by definition. Unpiloted ignition is refused (fire_model §3.2).
- **Flash** (flame attachment) when the unignited part's mass flux reaches m''_flash.
- **While flaming,** the surface gets a prescribed flame flux q''_fl. In MaCFP practice this is about 15–30 kW/m² at
  cone scale (V, L1 §2.3), and its value comes from the fit (§4.3).
- **Extinction** when the flaming part's mass flux falls below m''_ext.
- **The two thresholds are fitted, not chosen, and both may land anywhere in their cited ranges:**
  - m''_flash in 1–2 g/m²s (MaCFP's t_ig definition: Q'' ≥ 24 kW/m²);
  - m''_ext in 2.7–8.3 g/m²s (V7 1).

  m''_ext above m''_flash is **not a contradiction:** a surface that flashes before it can sustain itself goes out.
  That is *flashing*, a real cone phenomenon at low flux. Sustained ignition is when m'' stays ≥ m''_ext with the
  flame's flux on. **t_ig is graded at the data's own definition** (Q'' ≥ 24 kW/m² sustained), not at the first
  flash, so the flash-out-reflash cycle (Executor NS1, Physics P2-B2) is a graded behaviour, not a defect.
- **The lab may have extinction without flashing.** Pine at 25 kW/m² sustains at about 3.8 g/m²s (MaCFP-4), which
  pins m''_ext ≤ 3.8 for that species. That is a constraint the fit must meet, not a knob.

### 4.3 Fitting, held out

| Material | Fitted on | Graded on (held out) |
|---|---|---|
| Black PMMA (MaCFP-2) | 25 kW/m² | 50 and 65 kW/m²; then the reverse: fit 65, grade 25 |
| White pine (MaCFP-4), parallel grain | 30 and 60 kW/m² | 25, 50 and 75 kW/m², and the heater removed at a pre-registered time |

- **Free parameters:**
  - the kinetics (or T_p and L_g);
  - k_c and char ε;
  - q''_fl, m''_flash and m''_ext, each within its cited range.
- **The fitter is pre-registered:** an objective on curve features, its bounds and its seed. It runs once per
  material, and the graded fluxes are never seen by it.
- **A fit that lands at a range's edge is reported as such.**
- **Where MaCFP publishes a property** (density, k, c, ε of the virgin material), it is used and not fitted.

## 5. Formats

### 5.1 Material data v1

| File | Version key | Loader (one gate, `adapters/loaders.py`) | In the log header |
|---|---|---|---|
| `data/materials/core.yaml` | `version: 1` | `load_materials` (structural; u8 ids stable; registered `materials_v0_to_v1`) | path and SHA-256, as today |
| `data/materials/chemistry.yaml` | `version: 1` | `load_chemistry`: components and species by name, with stable ids; reactions; refusals of fire_model §9.1 | path and SHA-256 |
| `content/recipes/*.yaml` (game content, planned in tile §1.3) | `version: 1` | `load_recipes`: representation (§1.2), components, admitted kinds, geometry ranges, segment class, node rule | path and SHA-256 of each file |
| `data/materials/variants.yaml` | `version: 1` | `load_variants`: per recipe, the knobs an imagined object may set | path and SHA-256 |

The cone fixtures (PMMA, pine and their backings) live under `tests/fixtures/fire/`, never in `content/`.

### 5.2 Scene v2 and spec v1

- **Scene v2** adds `fuel:` entries: recipe by name, `kind` (`rod` with any axis, or `slab`), metric geometry,
  region. It carries a registered migration from v1, and v1 scenes load unchanged with no fuel.
- **The imagined-object spec v1** names a recipe, a kind the recipe admits, geometry within its ranges, and closed
  variant keys. Out of range is refused, never clamped. Its budgets are checked against the world's remaining
  limits (§1.3).

### 5.3 Wire, save and digest

- **Snapshot:** an `objects` table and a `segments` table (world_model F2–F4: column-major, integer keys, no
  strings).

  | Column | Type | Unit, quantisation |
  |---|---|---|
  | `object_id` | u32 | — |
  | `recipe_id` | u16 | — |
  | `region_id` | u16 | — |
  | geometry | f32 | m, 1 mm |
  | `surface_temperature_c` | u8 | °C, display-quantised as `temperature_c` is |
  | `ignited_fraction` | u8 | 1/255 |

  The tables are budgeted per profile in B5. The cell channel `burning` stays reserved; it isn't given a new
  meaning (Wire WT-S6). Drawing these tables is the client design pass's job (§7). 6.1 is server-only.
- **Save and digest:** every table in §1.1 and the object-id counter. Cap events and retirement counters enter with
  the integrator that has them.
- **Ledger lines:**
  - Δ(nodes), the sensible energy;
  - Δ(component inventories) at reference enthalpies;
  - the cone heater's input, the prescribed flame flux's input and the spark's input, all on the input side;
  - `open_air_object` (§3);
  - conduction to cells;
  - the energy leaving with the gas products, at their temperature;
  - `removed_with_mass`.

## 6. Tests

| Test | What it proves | Can it fail? |
|---|---|---|
| Thick and thin t_ig closed forms (losses off, high flux) | the conduction solver | yes: a wrong ρc or node rule shifts t_ig |
| Constant-flux semi-infinite profile (erfc) at 60 s | node sizing | yes |
| Delta-form equilibrium: zero forcing at ambient for 200 steps | no drift | yes: the full form drifted on 200 of 200 (DP-S1) |
| **FDS verification:** our solver with MaCFP's NIST-StMU-FSRI PMMA parameters and FDS's boundary conditions, at 25, 50 and 65 kW/m², against FDS 6.11.1's burning rate and surface temperature | our numerics match a reference implementation | yes. The tolerance (e.g. peak MLR within 2%, its time within 5 s) is pre-registered after one FDS run at two node densities shows FDS's own discretisation spread |
| R0 and R1 held-out grading (§4.3) | the physics against data | yes |
| Segment size halved | segment-independence | yes |
| Straddle: one slab across a cell boundary at offsets dx/3 and 2dx/3, at 0.2, 0.1 and 0.05 m, on the concrete floor | coupling totals and the floor's heating agree across grids within tile §6.3's tolerance | yes, if coupling weights are cell-centred |
| Coupling closed form: a slab at fixed T on a semi-infinite solid cell block | the contact conductance | yes |
| Identity pattern: no fuel objects in a scene → today's digests bit for bit | 6.0 changes nothing else | yes |
| Save and load at every step of a cone run | the save is complete | yes |
| Loader, scene, spec and world-limit refusals, each one | the trust boundary | yes |
| Work counters for node solves per step | cost, deterministically | yes, on any increase |

## 7. The open findings and their owners

| Finding (delta round 1) | Owner |
|---|---|
| Gas sink (P2-B1, D-B1, NB1) | 6.0–6.1: §3, ambient; then **6.2**: the plume |
| Flash and extinction (NS1, P2-B2) | 6.1: §4.2; per-flame extinction in **6.2** |
| Imagined representation by size (WT N-B1) | §1.2 |
| Unbounded objects (WT N-B2) | §1.3 |
| Occupancy consumers (NS2), WT-B1 | §2 |
| Formats, versions, loaders, log header, id counter, row validation (WT new) | §5 |
| Ledger lines (WT-S7) | §5.3 |
| Segment size untested (physics delta) | §6 |
| Held radiation field, surface-to-surface cost, flame budget positivity, the contact law, merging, multi-rate spikes (D1-B1, D1-B2, physics deltas, D1-S1) | **6.2 design** |
| Sleep predicate (D1-S2) | 6.2 (6.1 runs everything awake) |
| Client can't draw objects; `crack`'s source (D-B2) | **a client design pass** (`client_rendering.md` revision) before step 8 |
| The red gates calling `ignite`, the `TEMPORARY` ceilings (A-S2, NS8: three gates) | **6.4**, with `kindle`'s new pilot |
| Held flame lifecycle (D-S7, WT-S5) | **before step 5** ships vocabulary v1: a note to the step 5 plan |
| `strike` and breach on objects (A-S4) | 6.2 design |
| Per-layer placement (A-S6) | below |
| The NPC surface, Maxim asks, lesson 24's wording (Bio NB1, NB2 and the rest) | **a separate NPC fire note**, ruled on its own; none of it blocks 6.0–6.1 |

**Placement** (A-S6):

| Code | Layer |
|---|---|
| Object, segment, node and coupling tables, the 1D solid, the kinetics | sealed core: `core/fuel.py`, `core/solid.py` |
| Loaders for chemistry, recipes and variants | `adapters/loaders.py` |
| The snapshot tables | `protocol/encoding.py` |
| The recipes | game `content/` |

The core keeps its banned-import list: no IO, no clock.

## 8. What 6.0–6.1 doesn't show

Whether fire spreads, sustains in a crib or glows. A lone slab that flames out when the heater goes is the expected
answer, and it passing says nothing about the crate. That question belongs to 6.2 onward, designed from what R0 and
R1 measure.
