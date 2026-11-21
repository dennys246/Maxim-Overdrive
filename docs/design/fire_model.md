# Fire model: design v2 for review (2026-11-20)

**Status: the direction, not the build spec** (owner, 2026-11-20, "B plus C", `reviews/fire_model/fold.md`). Delta
round 1 left 12 new blockers; sub-steps 6.0–6.1 get their own design, and flames are designed after R0–R1 run.

**Sources:** `docs/design/research/fire_ladder/` (L1–L6b; V7 wins over them). Tags: **V** primary,
**S** secondhand, **M** memory, **D** derived.

## 0. The answer

1. **Three spikes failed for one reason: the flame had no body.** Under law 6c a burning surface heats only itself;
   unburnt fuel sees only a radiative leak. For fine fuels, hot-gas contact rather than radiation ignites (Finney 2015,
   particles ≲ 1 mm; Jiang 2019, thin dowels; scoped by V7 4–5). The case rests on our spikes; the literature is
   consistent with it, not proof of it at 20 mm.
2. **Our flames are smaller than the cells.** A 1–2 kW flame has D* of 0.06–0.08 m (D), 0.3–1.6 cells across our
   grids. Resolving it would need millimetre gas cells: a CFD project (L2 §4, L4 §4).
3. **So fuel and flames become sub-grid objects with geometry in metres**, coupled to the cells by overlap (§2–§4).
   Their representation never depends on the grid; what does depend on dx is the coupling, which the cross-grid
   tests exercise (§6.1).
4. **Lone surfaces go out; cribs don't.** One timber surface self-extinguishes below an external flux of 24–57 kW/m²
   depending on species (V7 1). NIST's crib burns at its peak at an area-mean 2.3–3.1 g/m²s (D, physics review S1),
   below the lone-surface value, because its surfaces heat each other and its flames are anchored elsewhere. So
   extinction belongs to the flame, and surfaces exchange radiation (§3.3, §4.3). The hot-surface crate F going out
   was most likely an artefact of the per-patch law, not physics.
5. **We validate bottom up**, one mechanism per rung, fitted on some data and graded on held-out data (§6).
6. **NPCs sense physical stimuli at their receptors, never verdicts** (§5); nothing here is an NPC lesson until Phase 4
   measures one against the LLM's prior.
7. **The Phase 1 exit becomes "light a built fire"** (§7): an authored fire starter, kindling and a crate with
   cardboard; the player kindles the starter.

## 1. What the evidence established

| Finding | Evidence | Consequence |
|---|---|---|
| A torch lights only the slat faces it heats | physics spike Q1, every grid and range end | law 6c can't carry the exit |
| Kerosene in the pores doesn't spread it | accelerant spike, λ_max 0.0129 | T18's "spreads because its fuel is distributed" was wrong in that model |
| Hotter surfaces and an uncapped gas don't spread it | hot-surface spike, outcome 5 | the temperature pins weren't the cause |
| A lone char surface with only its own flame's flux goes out | closed form: 0.9σ(823⁴ − 293⁴) = 23 kW/m² against 25 (D); V7 1 | correct for one isolated surface only |
| NIST's crib sustains below the lone-surface extinction flux | TN 2102 Test 13 (V), area-mean 2.3–3.1 g/m²s (D) | extinction per flame; surface-to-surface exchange |
| K2_005's stall: a 10⁻¹⁹ m² sliver divided into a power | probe log (D), code read | area hygiene and local substeps (§8) |

The sliver bug is in the accelerant spike's `WetBed`, so every accelerant run carries it (≤ ~9 W of 2 kW; completed
runs unchecked for slivers).

## 2. Fuel: objects, segments and inventories

### 2.1 Containers

| Container | Key and rows | Holds |
|---|---|---|
| **Cell** (dense) | as today | structural owner material, region, temperature, integrity |
| **Fuel object** | persisted object id (u32), sorted | recipe (by name), region id, geometry in metres (`rod`: a cylinder with any axis; `slab`; `bed`: an authored porous box with φ and σ), component inventories in kg |
| **Segment** | (object id, segment index), sorted | a piece of the object's surface of fixed size in metres per recipe class (along the object's length or area, never by cell). It holds two **parts**, ignited and unignited, each with its own 1D in-depth profile, plus the front position between them (§3.2) |
| **Coupling row** | (cell index, object id, segment), sorted, CSR | the overlap weights of a segment in the cells it touches, recomputed in the topology batch |

- **Any number of objects per cell.** A 0.2 m cell can hold the crate's bed, its cardboard, a stick and the starter.
  Capacity never depends on dx.
- **A bed is a bed on every grid, and a stick is a stick.** The representation is authored, never chosen by dx. R3's
  dowels and R4's crib sticks are discrete rods at every spacing (about 100 for TN 2102's crib).
- **Inventories are kg per object and segment**, never kg/m³ of a cell.

### 2.2 Occupancy, regions and coupling

- **Occupancy** becomes `solid | holds_fuel` (from the coupling rows). Each consumer switches, with a test:
  `applier._check_region`, `StructureModulator.__init__`, `region_parts`, `snapshot`'s `× solid` masks,
  `imagination`'s overlap rule and `kindle`'s target derivation (§5.4).
- **Region membership** is cells ∪ objects (each object carries its region id).
- **Heat between an object and the grid** happens only through the coupling rows:
  - convection h(T_s − T_cell) with each overlapped cell, by overlap weight;
  - contact conduction into any solid cell the object touches (the crate on the concrete floor), which keeps the
    floor-damage control V_floor meaningful;
  - radiation to the surroundings, at the overlapped cells' temperature for an exposed segment, or by exchange with
    other segments (§3.3).

  This is where dx enters, so the cross-grid tests are aimed at it (§6.1). A segment's convective and contact power
  is deposited into cells by overlap weight, and the ledger books it on both sides.
- **Cells keep one temperature.** An air cell holding a burning stick reads the air; the stick's temperature lives
  on its segments, which glow, SEM and the client read (§9.2).

### 2.3 Transitions are inventory moves

| Transition | Move | Note |
|---|---|---|
| virgin → char + volatiles | reaction on `virgin`: residue char at yield χ, the rest to the pyrolysate | char thickness is derived from char mass |
| char → CO/CO₂ + ash | heterogeneous reaction, **off under flame cover** (`char_oxidation.md` §0.5) | glow, embers and burnout; ash stays as an inert inventory |
| PMMA → MMA vapour | no residue; the segment's thickness shrinks | PMMA is amorphous and gasifies; it doesn't drip (Joseph 2015, V) |
| moisture → vapour | evaporation at T_b | |
| paraffin solid ↔ liquid | latent move at T_m with L_f (Hamins 2005, V) | the T18 loading, split by phase; cap = void fraction × ρ_L, joint across all loadings |
| liquid → vapour | evaporation, then flames on vapour | the accelerant law |
| burnt out | combustible inventories below a per-object ε in kg | the residue goes to fines through a transfer, never through `MaterialGrid.destroy` |

**Dripping is deferred** as a known gap. Pools have no position (world_model §2), and drips can either extinguish or
spread a fire (Joseph 2015, V). A recipe whose melt would exceed its retention cap is refused at authoring.

**Phase 1 gas products** go to the outside reservoir as one ledger line per species name. Per-species zone state
stays in Phase 2 (D26); the loader's atom and energy closure checks run anyway (§9.1).

## 3. The solid

### 3.1 One 1D profile per part

Each segment's ignited and unignited parts carry a 1D profile in depth, with nodes sized in millimetres per recipe
and allocated from authoring, so preheating before ignition is kept (DP-S7). Each profile has:
- finite-slab conduction with the object's own back boundary (a rod's centre line; a slab's far face);
- pyrolysis at an intrinsic L_g, leaving char at χ;
- a char layer with ρ_c, c_c and k_c(T);
- a surface balance: absorbed flux = εσ(T_s⁴ − T_env⁴) + h(T_s − T_env) + conduction inward (+ char oxidation when
  not under flame).

**The rate law is R0's choice, graded on fit and cost.** The choice is between a threshold (pyrolysis at T_p with
L_g, exactly zero below T_p) and one-step Arrhenius with a written cutoff below which the rate is exactly zero.
Without that cutoff, Arrhenius removes 18 ulp per step even at 20 °C, so no fuel could ever sleep (DP-S1). FDS's
`REFERENCE_TEMPERATURE` derives Arrhenius A and E; it is not precedent for a threshold law (Executor S12, M).

### 3.2 Ignition, the front and the pilot

- **Two events, with hysteresis.**
  - **Flash** (flame attachment): the unignited part's mass flux reaches m''_flash, defined as the data define t_ig
    (MaCFP: Q'' ≥ 24 kW/m², about 1.0 g/m²s for PMMA and 1.6 for pine, D).
  - **Extinction** is decided per flame (§4.3), not per part.
- **A pilot is required.** A part ignites only inside a flame object's volume, within a cited distance of one, or in
  gas above an autoignition temperature. Autoignition isn't cited yet, so unpiloted ignition is refused and recorded
  as a gap.
- **The front moves by a law, never by a patch mean.** The ignited/unignited boundary in each segment advances at a
  speed set by the heat delivered just ahead of it, evaluated at the front in metres: the flame's footprint (§4.2)
  for concurrent spread. For opposed spread (downward, lateral), de Ris and Fernandez-Pello's form
  V = Φ/[kρc(T_ig − T_s)²] applies (V, NBSIR 84-2943 eq. 14), with Φ a cited material parameter. Because the front is
  a position, it doesn't jump by dx; a segment's size changes only the profiles' bookkeeping.

### 3.3 Surface-to-surface radiation

Segments exchange radiation with the segments they see (view factors in metres, from geometry). Interior char facing
char at 700–900 °C loses almost nothing net, which is how a crib's embers stay hot (`char_oxidation.md` §0.3). Law
6c's in-bed P1 is dropped, but for an authored `bed` object (not R3 or R4) it stays the bed's internal exchange. The
cost is in §8.3.

**Oxygen and the draught.** In-bed O₂ limits and Ergun draught are dropped with 6c. That is the gap R4 leans on
hardest: TN 2102's crib is probably porosity-limited (Heskestad factor 0.32–0.87, D, physics S6), which could put
our peak up to ~1.8× high. Before R4 is pre-registered, its porosity regime is computed from the crib's real stick
layout. If it is oxidiser-limited, an O₂ supply term per bed volume comes first.

## 4. Flames

### 4.1 One flame per cluster, recomputed each physics step

- **Clustering.** Burning segments group into clusters by distance in metres between their geometry, with a smooth
  merge weight across a distance band instead of a yes/no threshold. No cited merging model has been read (Thomas;
  Delichatsios: still to read), so the band is pre-registered and R3's gap sweep gates it (§6.2).
- **A cluster's id is its minimum member key.** Flames are **stateless**: recomputed from segments each physics step,
  so no flame state is saved and there is no identity to renumber.
- **Heat release.** Q = Σ pyrolysis mass flux × ΔH_c,eff over the cluster. The flame is fed only by its fuel.
- **Geometry.** Height and width are continuous functions of the cluster's Q and its geometry: a wall flame
  (Delichatsios and Hasemi, tested for x_f of 0.3–1.4 m) blending into a free flame (Heskestad, 7 < Q^(2/5)/D < 700,
  S) by the cluster's aspect, never by a switch. Kindling and starter flames (0.1–0.3 m) sit below the wall
  correlation's tested range, so every run on them is reported as an **extrapolation**. Phase 1 air is still: no
  tilt.

### 4.2 One heat budget per flame

Each cluster's Q is partitioned. No term is added on top:

Q = Q_contact,conv + Q_contact,rad + Q_rad,view + Q_rad,escape + Q_gas

- **Radiation:** Q_contact,rad + Q_rad,view + Q_rad,escape = χ_r·Q, with χ_r cited per fuel and flame scale (still
  to cite: L2 §5 leaves it open).
- **Gas:** Q_gas = (1 − χ_r)·Q − Q_contact,conv, which goes to the overlapped cells' gas by overlap. Phase 1 has no
  gas in cells (world_model §2), so it reaches the outside reservoir through those cells' open-air loss (6a), on the
  ledger.
- **Contact:** a segment inside the flame volume gets contact flux only, with no view-factor term on top. On thin
  elements contact is h(d, u)·(T_f − T_s), sized by diameter (h rising roughly as d^(−1/2), physics S8), plus the
  flame's radiation. The wall value of 10–30 kW/m² is used only for wall geometry.
- **A burning segment's own flame flux is its cluster's contact flux**: not a second source, as v1's q''_f was.

### 4.3 Extinction belongs to the flame

A cluster's flame persists while its fuel's mass flux, averaged over its burning area, stays above m''_ext,flame.
That value is cited per setup, since m''_cr changes with sample size (Plathner: 19.2 against 2.0 g/m²s, S). A
segment below the lone-surface value inside a sustained cluster keeps feeding it. A lone surface whose cluster is
just itself reduces to the cone case, and R1 grades that case. There is no cited per-cluster extinction model; R4's
check that "a fully involved TN 2102 crib doesn't flame out at about 2.5 g/m²s" is what grades it.

### 4.4 Radiation to receivers

Receivers are segments, solid cell faces and body regions. This revises T14, which had bodies only, by point source,
in Phase 1.

- **Emission.** Each flame is one emitter: an analytic solid-cylinder (or sheet) view factor to each receiver's
  quadrature points, which are fixed in metres.
- **Occlusion** is per (flame, receiving object or face group), sampled coarsely in metres. It is a pure function of
  the current geometry.
- **Multi-rate** (owner ruling 1). The radiation field is recomputed every N physics steps on a fixed schedule (N
  pre-registered, measured at R2.5). Between recomputes, the held field is **state**, in the save and the digest, so
  save/load at any step reproduces a continuous run.
- **A distance cutoff, if any, is a law in metres** in every mode, its dropped power booked; never a sleep shortcut.

## 5. What NPCs perceive and do

### 5.1 The split

The world computes the stimulus at the receptor. Maxim transduces it (L6b §3). The world also owns tissue: skin
conduction and damage are physics of the body's matter (Bio S4).

| Quantity | World | Maxim |
|---|---|---|
| Heat on skin | tissue temperature at each receptor depth the body declares; incident flux and contact stay internal (`sem_stimuli.md`) | warm and cool receptors (adapting); nociceptors (sensitising) |
| Tissue damage | a Henriques integral into the part's `integrity` | Maxim's `apply_damage`; humanoids lack `drive:health`, so no fear yet |
| Airway, smell, sound | concentrations and transients at the receptor (Phase 2) | chemical, olfactory and auditory receptors |
| Sight | luminance, angular size and flicker of **whatever is in view**, after line of sight: a lamp excites it too | the percept |

Two leak tests:
1. Could an instrument at that spot measure it with no nervous system? Then it is the world's.
2. Is it transduction (a threshold, gain, adaptation, latency)? Then it is the receptor's.

Tissue properties (skin k, ρc, Henriques constants) are world physics. Core temperature has one owner: world-written
with `drift_rate: 0`, or Maxim-drifted.

**Body shape.** On Maxim's humanoid bodies `health` is derived: `world_set_axis` can't write it, and a direct
`health` sensor is refused (Bio S1, `base_humanoid.yaml`, `spec.py` C5). So per-part burns need `world_set_axis` for
sub-sensors (OD-C10, world_v2 P4), or a flat body with that divergence named. Until GL2b, an NPC learns fire only
from injury, never from the pain that comes first.

**Divergences (Maxim's intents):**
- the root-sensor skin stopgap: **ANALOG**;
- generic in-view luminance: **ANALOG**, a stand-in for vision until OD-C8;
- credit for `kindle`'s delayed ignition: **OPEN** until OD-A16;
- the fractions (burning, charred, soaked, melting) stay **lab instruments** until a percept channel exists
  (OD-C8). They never reach an NPC through a region instrument.

### 5.2 Why radiation matters to the agents

On bare skin, severe pain comes at about 45 s and a second-degree burn at 187 s at 2 kW/m²; at 10 kW/m², 5 s and
14 s (NOAA ALOHA from FEMA, V7 8). Pain leads damage by 2.8–5.8×. Without flame radiation that warning window is
zero.

### 5.3 What changes from T18

- **"Flammable" and "porous" are not sensors.** No receptor delivers them. T18 specified them on paper only, and none
  exists in `src/`. Material identity reaches an NPC as a noun through sight.
- **Fractions, not booleans** (`states_of_matter/sem.md` N2 over T18).
- **Kept from T18:** physics owns the mechanism; nothing spreads by an SEM rule.

### 5.4 Acts

- **One fire act for everyone: `kindle`** (tile T4, which already retired `ignite`; F7 retired `extinguish`). It
  applies a held item's flame at a point.
  - **Target derivation:** the fuel object or solid whose surface is nearest the point within 50 mm, with a tie
    within 1 mm refused as `ambiguous_point` (R3's sticks at 0.75–1.5 cm separate by more than that).
  - **The torch's pilot is a flame object** with a prescribed Q at the point, heating by §4 like any flame. That
    replaces the sphere deposit and the 0.2 m minimum radius.
  - The vocabulary is v1 amended before step 5 ships it.
- **No NPC fire acts in Phase 1**, since there are no NPCs. `light`, `apply`, `carry`, `drop` and `place` come with
  item entities and NPC bodies (Phase 4), as the same `kindle` intent from a body, sharing its validators and log.
- **The bridge gets two builders.**
  - The **NPC builder** exposes no `ignite`, `extinguish`, `strike(energy_j)` or `RegionInstrument`. A golden test
    pins its tool surface, and `strike` becomes a body act with a held thing.
  - The **lab builder** lives in tests only.
  - `ignite` and `extinguish` leave `parse_action`, and a test refuses both through `execute`.
- **A fruitless act succeeds as an act.** `requires` names only sensors the body exposes (holding, reach), never an
  outcome. Fire acts carry no `target_effect` or `self_effect`, and a test refuses one that does.

### 5.5 What the bridge must never do

Decide an outcome; expose flammability, flash point, ΔH_c or φ; threshold an entity mean into a learned boolean;
refuse a fruitless act or describe its outcome (today's `ignite` description, "it burns until extinguished",
breaks this); give an NPC an omniscient region instrument (today's `temperature_*` and `breached`); write a second
heat path into the body.

## 6. The validation ladder

### 6.1 Grading rules

- **Across grids (owner ruling 2): the tile spec's rule stands.** Classes agree on every grid, and graded times and
  rates at 0.1 m lie within tile §6.3's tolerances (10–15%) of the 0.05 m reference, converging from 0.2 m. Nothing
  is loosened.
- **Against data:** curve features within the envelope of lab means, fitted on some fluxes and graded on held-out
  ones.
- **Every cross-grid gate names the dx path it exercises:**
  - segment–cell coupling;
  - flame-to-cell deposit;
  - the straddle test: an object placed across cell boundaries, offset by dx/3 and 2dx/3.

  A gate that no grid-dependent path touches is a unit test, not a cross-grid test.
- **Moisture is pinned per rung**, its effect on t_ig graded at R0. **Legibility checks** start when the client draws
  fire (step 8); passed rungs are rerun then.

### 6.2 Rungs

| Rung | Setup | Graded against | Pass |
|---|---|---|---|
| **R0 ignition** | one slab under fixed flux; PMMA, then white pine | MaCFP-2 PMMA (t_ig lab means 76–148 s at 25 kW/m², the 76 s lab flagged; 12–29 s at 65); MaCFP-4 pine (25–75 kW/m²) | fit at 30 and 60 kW/m², grade t_ig at 25, 50 and 75 inside the envelope; PMMA fitted at 25, graded at 65, and the reverse; thick and thin closed forms; the rate-law choice (§3.1) |
| **R1 burning** | that slab burning, then the heater removed | MaCFP-4 pine at 30–60 kW/m² (first peak 161–235 kW/m² at 50, 4 labs), backing specified | first peak, plateau and second peak in the envelope on held-out fluxes; sustained at 25 kW/m², as MaCFP-4 measures (about 3.8 g/m²s); no sustained flaming once the heater is removed. The apparent L_g (about 15 kJ/g, D) is reported, not graded |
| **R2a opposed spread** | PMMA lit at one edge, downward | a measured downward-spread dataset for cold PMMA, to find (Fernandez-Pello and Williams, of order 0.05 mm/s, M) | the front advances at the measured rate within its scatter; same class and time tolerance across grids |
| **R2b upward spread** | a base-lit vertical PMMA slab | a measured upward-spread dataset (FDS-validated PMMA panels, or Leventon), to name before pre-registration | pyrolysis-front position against time and its acceleration, which the correlations don't fix |
| **R2.5 flame object** (verification) | prescribed Q; receivers at distances; the base offset by dx/3 and 2dx/3 | analytic view factors | a closed shell of receivers absorbs χ_r·Q to round-off, with reciprocity per patch, and goes red when one cylinder face is deleted; absorbed power within a gated error on every grid; counted as a unit test, not physics |
| **R3a dowels** | Jiang's birch dowel arrays | Jiang 2019 (V7 5) | sideways spread at 0.75 cm, none at 1.5 cm, upward at both; a gap sweep whose band of disagreement between grids is gated |
| **R3b, R3c** | the starter beside a stick; stick beside stick | **no dataset** | class only, reported as predictions |
| **R4 crib** | TN 2102 Test 13, pilot as a prescribed Q from Test 13's early curve, stick layout from TN 2102 | 396 ± 18 kW peak; residue 5.3 ± 3.4% after raking at about 48 min (V7 3) | not flamed out at about 2.5 g/m²s; peak within ×1.5; residue graded at 48 min; ember tail ≥ 18 min; time to peak graded only once verified from the source |

LIFT's plywood speeds (V7 6) and Jiang's unverified timings (V7 5) are not used as criteria.

**Tests at every rung:**
- the identity pattern: a new term at zero reproduces the old digests bit for bit;
- sleep on against sleep off, with identical bits;
- save and load at every step of a fire run, matching one continuous run;
- the hygiene test (§8.2);
- a closed-shell ledger test for one cluster over known receivers;
- deterministic work counters (§8.3).

## 7. The Phase 1 exit

**The player lights a built fire.** The scene authors a wax-and-sawdust starter under three or four sticks leaned
on a crate packed with cardboard; the player kindles the starter with the torch.

- **R3b, R3c and R4 cover the beats.** Two of them have no oracle, so the exit is a prediction that passes its class
  and cross-grid gates plus the human playtest.
- **The starter has no published burning data** (L1 §3). It is modelled from paraffin's cited properties (Hamins
  2005) plus retention, and checked by a pre-registered bench measurement (mass against time), or stays a
  prediction.
- **Fallback** (owner ruling 3): if R0–R2.5 overrun their time-box (§10.2), or R3 fails, the exit is the highest rung
  that passes honestly, such as a burning slab that flames out and glows, and the crate moves to Phase 2. The owner
  decides when that trigger fires.
- **Not claimed:** any NPC lesson. Phase 1 has no NPCs, and a Phase 4 NPC that avoids fire may only be showing the
  LLM's prior. Fire learning is measured substrate-side or with a counter-prior (Maxim's Exp 38), under game-native
  pressure (L6 §5).

**Scene v2** carries fuel objects:
- a recipe by name;
- `rod` with any axis, `slab` and `bed`;
- placement inside an owner's footprint, which the overlap rule now allows for fuel objects only;
- a registered migration from v1, with tests.

## 8. Numerics and cost

### 8.1 Integrators and caps

- **Stiff laws are implicit.**
  - In-depth conduction uses backward Euler in **delta form** (solve for ΔT with the explicit residual on the right).
    At exact equilibrium the full form changed bits on 200 of 200 steps and the delta form on 0 (DP-S1).
  - The front linearises εσT⁴ once, as FDS does.
  - A hand-written Thomas solve, no BLAS.
  - Pyrolysis and oxidation: exponential update at frozen T, sink from the mass consumed.
- **Any law left explicit substeps locally, per part.** One sliver can't set n for the grid.
- **Cap events.** A part that would exceed its local cap (per law) steps implicitly instead. This is a **cap event**,
  counted in the digest and the tick status, and identical in play and test. Graded scenarios require zero cap
  events, and one test forces one and checks rerun and replay bits.
- **World time never shortens.** Dilation is the host's business, measured outside `World` (boundaries).
- **Coupling frequency.** The solids couple to the grid once per physics step, not every heat substep (which would
  cost ~16× at 0.1 m and ~64× at 0.05 m). The lag is checked against a run that couples every substep, at R0 and R1.

### 8.2 Hygiene and determinism

- **Power is routed by area share, never divided by a part's area.**
- **Retiring a part below its floor merges it** into its sibling, conserving area, every inventory, energy and the
  latch, by a written rule. An ignited part folds into the segment's front position and never vanishes.
- **The hygiene test** feeds slivers below and just above the floor, asserts the cap isn't hit and that energy is
  conserved, and goes red when area-share routing is deleted. A floor sweep at ×0.1 and ×10 keeps the class.
- **All tables are sorted by integer keys.** Rows are inserted and removed only in the per-step topology batch.
- **Reductions** are `bincount` or fixed-order sums over full tables, never `np.sum` over a subset (56 of 200 differed).
- **Sleep:** compact-support laws only, at bitwise equilibrium with zero forcing.
- **Randomness**, if any, is counter-based by (cluster id, tick).

### 8.3 Cost (D, measured by L5 and the review)

| Kernel | Measured | At 20,000 segment parts |
|---|---|---|
| Full 1D step (k(T), c(T), kinetics, sink, front, Thomas) | 21–23 ns per node | 9.3 ms per physics step at 20 nodes; 22 ms at 52,000 parts |
| Flame → receiver view factor, analytic cylinder | ~40 ns per (flame, quadrature point) | 31 ms for 10 flames at 4 points |
| Occlusion by voxel march | ~9 ns per sample | 243 ms uncoarsened (800,000 rays × 32 samples) |
| Clustering | | 10 ms |

- **What owner ruling 1 buys.** One emitter per cluster, coarse occlusion per object or face group, and recomputing
  every N steps divide the radiation cost by roughly N × (the coarsening factor).
- **Flame count is the crux:** TN 2102's cluster count is computed before R2.5.
- **A fire budget is written before R2.5**, for example "fire kernels ≤ X ms per physics step at the 1.92 × 10⁶-cell
  tile with the crate at peak". It is recorded in Known gaps. The server is already at about 0.7 s per 0.5 s step on
  that tile (gates `docs/architecture.md`, a 40×8×6 m tile).
- **The primary gate is deterministic work counters:** node solves, view-factor pairs, ray samples, cluster edges
  and cap events per step. B5's `process_time` gate is secondary.

## 9. Formats

### 9.1 The material data, split by owner

| Part | Owner, file | Holds |
|---|---|---|
| Structural materials | engine, `data/materials/core.yaml` v1 | today's concrete, steel, glass, drywall and wood cells with their fields; u8 ids stable |
| Chemistry | engine, `data/materials/chemistry.yaml` | species and components keyed **by name** with stable integer ids (world_model F8); every reacting component has a formula or elemental mass fractions; reactions; transitions |
| Recipes | game content | components, void fraction, bulk density, admitted geometry kinds and ranges |
| Variants | read by `imagination` | the only knobs an imagined object may set, per recipe, bounded and cited |

- **Validation materials** (PMMA, birch, TN 2102's pine) are test fixtures.
- **v0 fixtures** migrate through a registered `materials_v0_to_v1`.
- **Landing order.** Material data v1 and the object tables land before step 5's first log writer, so no replay
  golden is recorded on v0.

**The loader refuses**, each with a test, and every refusal raises the gate's one exception type (a `LinAlgError`
from the Hess solve is caught and re-raised):
- **yields** that don't sum to 1 within 1e-12 by `math.fsum` in key-sorted order, tested in both orders;
- **recipe fractions** that don't sum to 1;
- **dangling references** (reactant, yield, `consumes`, a variant's recipe or key), and one name in two namespaces;
- **bad kinetics:** A ≤ 0, E < 0, or n < 0;
- **bad densities:** void outside [0, 1), a density ≤ 0, or a bulk density inconsistent with the components;
- **loadings** whose joint volume exceeds the void;
- **atom balance** that doesn't close, a solved formula with a negative count, or two unknown formulas in one
  reaction;
- **a Hess cycle** that doesn't close, or is ill-conditioned beyond a stated bound;
- **a reaction or transition cycle** with net heat;
- **a threshold** without its closed provenance key.

### 9.2 Wire, save, digest and ledger

- **Snapshot.** Fuel objects and segments travel as a table (world_model F2–F4: column-major, integer keys, no
  strings), and so do flames (the client sizes its flame mesh from the server's height). Channels whose meaning
  changes get new names (F1):
  - `segment_glow`, the segments' surface temperature;
  - `burning`, the ignited area fraction.

  Godot decoder fixtures accompany both. These enter the protocol v0 grammar before step 7 freezes it.
- **Save and digest** carry everything that is state:
  - object and segment rows with their profiles and node counts (budget checked before allocation, F14);
  - inventories, front positions and latches;
  - the held radiation field;
  - cap and retirement counters;
  - a recipe name map;
  - the material-data hash in the header (refuse or migrate).

  Flames are derived, with a `derivation_version` (F15).
- **The imagined-object spec is versioned (v1).** It names a recipe, a geometry kind the recipe admits, metric
  geometry within the recipe's ranges, and closed variant keys. Out of range is refused, never clamped.
  - **Budgets before allocation:** objects, segments, nodes and surface area per spec.
  - `imagination.place` creates fuel objects for sub-cell geometry, instead of refusing objects "smaller than one
    cell".
- **Ledger lines:** Δ(segment profiles);
  Δ(object inventories) as chemical energy at reference enthalpies (no separate "combustion" input); fusion and
  evaporation; the flame partition (§4.2), each term on both sides; the coupling exchange; open-air loss (6a); the
  fines transfer; radiation dropped by any cutoff.

  Tile §5.4's `Δ(skins)` and `flame_radiative.unreceived` are replaced.

## 10. Scope and revisions

### 10.1 Decisions and documents this revises

| Revised | How |
|---|---|
| world_model §5 (one material per cell), §8 (the (cell, face) table, the save), §0/§4 (the planned per-cell latent state) | fuel objects and segments beside one structural owner per cell; phase-split inventories |
| world_model D23, D26, D29, D30 | laws 6b–6d replaced; pyrolysis and fusion enter Phase 1; the lab returns as the ladder's rigs; 6a kept |
| CLAUDE.md thin-features rule; `architecture.md` "How the rule is kept"; `code_review.md`'s Physics question; the imagination Known gap | the rule holds for resolved cells; fuel objects are exempt only as `rod`, `slab` or `bed` recipes of fuel, never structure (a plank wall stays cells) |
| tile T4 (`kindle`'s deposit and 0.2 m radius), T5 (one lumped body), T13 (no more paper rounds), T14 (radiation by point source to bodies only), T17 (accelerant ignition) | §5.4, §5.1, this note, §4.4, §7 |
| tile §5.1–§5.4 (q''_f, T_p, L_g, the ledger lines) | §3, §4.2, §9.2 |
| tile §5.3's pre-registered failure path | it fired (the three spikes); this design and §11 are its ruling, not a rescue |
| tile §6.3 item 8 | kept (owner ruling 2) |
| tile §11; `foundations_plan` step 6 ("Done when", Phase 2 deferrals); the roadmap's Phase 1 exit and Phase 2 bullets; D28's timing | §10.2 |
| T18 (labels), lesson 22, `states_of_matter/sem.md` N3's verb list | §5.3, §5.4, lesson 24 |
| world_v2 §7 (burn pain and Wire-4 review deferred to Phase 4's body design) | MP-2a and MP-1(i) are asked earlier (§11) |
| the bridge's NPC surface (`ignite`, `extinguish`, `strike`, region instruments) | §5.4 |
| `imagination.place`, scene v1, the spec, snapshot channels, the protocol grammar, the material table format | §7, §9 |
| O34's field registry (plan step 5a) | the object, segment and coupling tables join it: one registry, not a second one |

### 10.2 The build plan

| Sub-step | PR content | Before |
|---|---|---|
| 6.0 formats | material data v1 and migration; scene v2; the object, segment and coupling tables in the registry; snapshot and grammar entries | step 5's log writer and step 7's grammar freeze |
| 6.1 solid | §3 with R0 and R1 | — |
| 6.2 flame | §4 with R2.5, R2a and R2b; the fire budget | — |
| 6.3 two bodies | R3a–c | — |
| 6.4 crib and exit | R4 and §7's scene | step 8 |

- **The time-box (owner ruling 3) covers 6.1 and 6.2.** Each gets at most two pre-registration reruns. Overrunning
  triggers §7's fallback.
- **Size:** unknown beyond five PRs and their delta rounds; D28's prototype waits for 6.4 or the fallback.

## 11. Decisions

**Ruled (owner, 2026-11-20):**
1. **Cost model:** one flame per cluster with analytic view factors and coarse occlusion, plus multi-rate radiation
   on a fixed schedule; honest dilation is the fallback.
2. **Cross-grid grading keeps tile §6.3's tolerances.**
3. **Step 6 becomes the ladder,** with a time-box on R0–R2.5 and the fallback exit.

**Open, recommended as written:**

4. Adopt §2–§4.
5. Revise world_model §5 and the thin-features rule as in §10.1.
6. Phase-split inventories before save v0.
7. Revise T18's labels and the NPC surface (§5.3, §5.4).
8. Defer dripping.
9. The exit of §7.
10. **The Maxim asks.** Each needs a roadmap row under Phase 3, a draft in `docs/maxim_upstream/`, and reuses
    existing ids:

| Ask | Kind |
|---|---|
| MP-2a: nociceptor thresholds in physical units on a variant body | a question to GL2b(ii)'s calibration |
| MP-2b: two fibre classes, with the slow band (41–46 °C) feeding a learner | a pushback against GL1 review N4 ("one threshold for both fibre classes") and TR18 (`affective_slow` has no learner), with the skin model's time in 41–46 °C under the ladder's fluxes as evidence |
| MP-1(i): local burn fear | a variant `NACConfig.cluster_fear_failure_modes`, no default change, citing Exp 60's `drive:oxygen` precedent |
| MP-1(ii): fear carried by hivemind | edit the default and re-run T1-13 to T1-15; Phase 5's rumour mechanism |
| MP-5 | is world_v2 P4 / OD-C10: `world_set_axis` for sub-sensors; a prerequisite of per-part burns |
| MP-4 | is world_v2 P3 / OD-A16: delayed credit |
| MP-3, MP-6 | the proximity plan's amendment and receptor adaptation, later (L6b §5) |

## 12. Open questions and risks

- Uncited: flame merging, per-flame extinction, autoignition (refused until cited).
- Not in hand: R2a/R2b datasets, TN 2102's stick layout, its O₂ regime.
- The flux → pyrolysis → Q → height loop near threshold: binary outcomes keep CLAUDE.md's band and margin.
- Cost scales with flame count, unmeasured; x86 SIMD subset independence untested (CI offset test at 1 and N
  threads).
- The client may draw flourish (flicker, smoke) no NPC senses: a named asymmetry.
- **Not yet designed** (`fold.md`): the per-layer placement of the new code; `strike` and breach on fuel objects; a
  held flame's lifecycle; flipping the two fire red gates and retiring `actions.yaml`'s ceilings (proposed: in 6.4).
