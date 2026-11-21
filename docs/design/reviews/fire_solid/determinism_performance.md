# Fire sub-steps 6.0–6.1 design review: Determinism, replay and Performance

Reviewed: `docs/design/fire_solid.md` as staged on disk in `.worktrees/fire-design`, against CLAUDE.md,
`docs/code_review.md`, `world_model.md` §6, §8 and §9, `reviews/fire_model/determinism_performance.md` and
`delta1_determinism_performance.md`, `research/fire_ladder/5_numerics.md`, and the code at `gates` 396ae10
(`core/grid.py::CellStore.writing`, `tests/test_determinism.py::digest`).

**Measurements** (D): `scratch/fs_probes.py`, output `scratch/fs_out.txt`. numpy 2.5.5, scipy 1.18.1, Python 3.14.6,
arm64, thread variables at 1, `process_time`, best of 3, **load 2.2–2.6**.

**Counts:** 2 BLOCKER, 12 SHOULD-FIX, 4 NIT.

**Inherited:** D1-S4 still open (S3), D1-S9 still open (S11); D1-S3's shape recurs for contact (S12).

---

## BLOCKER

### FS-B1. Save validation refuses every save after the first gram burns, and inventories have two sources of truth

**Location:** `fire_solid.md::§1.3` ("inventories ≥ 0 that sum to the recipe's mass"), `§1.1` (`objects`: "per-component
inventories (kg)"; `nodes`: "per-component density"; "Inventories are kg per object, held per node"), `§5.3`, `§6`
("Save and load at every step of a cone run").

1. **The validation rule is wrong.** Once pyrolysis starts, the inventories sum to the recipe's mass minus what left
   as gas. So a save taken at any step after flash fails load validation. The design's own every-step save test goes
   red at the first step with mass loss, or someone loosens the rule to "≤", which no longer checks anything.
2. **Two copies of one quantity.** Mass lives both as a per-object kg column and as node density × node volume. These
   are not the same bits. In probe (d), an inventory decremented by each step's consumed mass differed from
   Σρ·dz·A recomputed from the nodes on **306 of 400 steps**. The design doesn't say which copy is authoritative,
   which one the digest hashes, or which one a load recomputes. If a load rebuilds one from the other, the reloaded
   run diverges from the continuous one at the next step that reads it.

**Fix.**
- Node densities are the only stored mass. A per-object inventory is a reduction (`bincount` over nodes in key
  order), never state. Alternatively, store it and never re-derive it, but say so.
- Add a per-object cumulative `removed_kg` (f64, saved and digested), which the `removed_with_mass` ledger line
  already implies.
- Validation becomes: each density ≥ 0, removed ≥ 0, and Σ(node mass) + removed equals the recipe mass within a
  stated relative tolerance. The tolerance is needed because the two sums are taken in different orders.
- The every-step save test then covers flaming steps.

### FS-B2. "Inserted only in the topology batch" leaves an object imagined mid-step in an undefined state

**Location:** `fire_solid.md::§1.1` ("Rows are inserted and removed only in the per-step topology batch"), `§1.3`
(overlap and world limits checked at `imagine`), `§5.3` (object-id counter).

`imagine` is an intent applied in its own write window (`imagination.place`; `applier.py`), between physics steps.
The batch runs inside `advance`. So between acceptance and the batch, the object is pending, and the design never
defines that state:

- **Checks against stale tables.** Two `imagine` intents in one step both check overlap and the remaining world
  limits against tables that hold neither of them. Both pass, and both are told they succeeded. The batch then
  inserts two overlapping objects, or pushes the tables past the limits. That defeats §1.3, the fix for WT N-B2. If
  instead the batch re-checks and refuses one, an intent already reported as success is undone.
- **The id moment.** Is the id taken at acceptance, in log order, or at the batch? If at the batch, in what order?
  Does a refused or rolled-back `imagine` consume an id? `CellStore.writing` rolls the channels back on a raise.
  Does the counter roll back with them?
- **Saves and frames.** A save before the batch loses the pending object unless the queue is saved; the frame after
  the intent shows nothing.

**Fix.** Ids are minted in order and never reused, so an object's rows always go at the end of `objects`,
`segments` and `nodes`, which keeps them sorted. Two ways out:
- (a) Insert in the intent's own write window, with the counter in the window's rollback, and rebuild coupling there.
- (b) Keep the batch, but make the pending queue saved and digested state. Checks then run against the tables plus
  the queue in log order, and the id is minted at acceptance.

(a) is simpler. Test two same-step `imagine` intents that overlap each other.

---

## SHOULD-FIX

### FS-S1. The frozen-T exact update for reaction order n ≠ 1 creates mass or returns NaN

**Location:** `fire_solid.md::§4.1` (kinetics (b), r = A·ρⁿ·e^(−E/RT); "Each node updates exponentially at frozen T").

Exponential only for n = 1; otherwise ρ_new = (ρ^(1−n) − (1−n)kΔt)^(1/(1−n)). Probe (e) uses n = 0.5,
kΔt = 25 and ρ = 10⁻³ kg/m³. The base goes negative, squaring makes it positive, and **ρ_new = 155 kg/m³: mass
appears**. Where 1/(1−n) isn't an integer, the result is NaN. MaCFP's n-step sets carry orders other than 1 for some
reactions. Fitted kinetics may too, since "the kinetics" are free parameters (§4.3).

**Fix.**
Write the depletion time t* = ρ^(1−n)/((1−n)k) into the law (Δt ≥ t* gives ρ = 0 exactly), or refuse such n in
`load_chemistry`; test that an n < 1 node depletes to exactly 0.

### FS-S2. `holds_fuel` is decided by float rounding, and that decision depends on dx

**Location:** `fire_solid.md::§2` ("`holds_fuel` is true if any coupling row with weight > 0 names the cell"), `§1.3`
(1 mm contact tolerance), `§1.1` (coupling "overlap weight").

Take an object spanning [0.3, 0.5] m. Put cell edges at k·dx and compute the overlap as min(hi) − max(lo). Probe (c)
gives **a 5.55×10⁻¹⁷ m sliver in the cell below the object at 0.1 m and at 0.05 m, and none at 0.2 m**, because
3 × 0.1 ≠ 0.3 in floats. That cell "holds fuel", so it is occupied:
- `_check_region` stops refusing it;
- `StructureModulator` counts it;
- the region's object join changes.

An outcome class depends on dx through rounding: F13's `0.6 / 0.2` trap again.

The coupling column also mixes two meanings:
- **Volume overlap** with air cells, which drives occupancy.
- **Contact area** with solid cells, which drives conduction. §1.3 forbids volume overlap with solid cells, so the
  overlap weight there is 0 by construction.

**Fix.**
- Cell edges in integers (millimetres, or index × dx in integer units), as F13 does.
- Two row kinds, or two columns, with their units: volume overlap (m³) and contact area (m²).
- Contact defined by the 1 mm tolerance in metres, not by a positive float.
- `holds_fuel` by a volume threshold in metres (e.g. ≥ 1 mm × face area), stated as a law.
- Test: the §6 straddle test also asserts the set of occupied cells at offsets that land exactly on an edge.

### FS-S3. Coupling rows: the rebuild trigger is still unstated, and the save carries a derived table it must not trust (D1-S4 open)

**Location:** `fire_solid.md::§1.1` (coupling "rebuilt in the topology batch from geometry"), `§5.3` ("every table
in §1.1").

"Rebuilt in the topology batch" doesn't say every step or on an event. Whether geometry can change in 6.0–6.1 is also
unsaid. `nodes` carries a node thickness, so the solid can shrink (PMMA regresses), but nothing says whether
`objects.geometry` follows it.
If geometry follows and rows rebuild only on events, they go stale and a load that rebuilds them diverges. If rows
come from the save, a hostile save sets conduction weights directly (F5, F14: derived state is recomputed and
compared, never trusted).

**Fix.**
- State that geometry is immutable in 6.0–6.1, and that node thickness never feeds the coupling.
- Rebuild on insertion and removal only.
- Declare the table derived, with a `derivation_version`. The loader rebuilds it and refuses a mismatch (or it isn't
  saved at all, only digested).
- Add world_model §6's Hypothesis property: incremental rows equal a full rebuild, bit for bit.

### FS-S4. CSR offsets per cell are O(cells) state for a few hundred rows

**Location:** `fire_solid.md::§1.1` ("CSR offsets per cell"), `§2` (`holds_fuel`).

A full CSR row pointer has n_cells + 1 int64 entries (probe (b)):

| Grid | Offsets memory | Build |
|---|---|---|
| 1.92×10⁶-cell tile | **15.4 MB** | 4.7 ms |
| 5×10⁶ cells (max profile) | **40 MB** | 11.5 ms |

Sorted COO holds 20,000 rows in 160 kB. Every rebuild, save, digest and window copy pays the O(cells) price.

**Fix.** Use sorted COO with `searchsorted` for per-cell lookup. `holds_fuel` becomes `np.unique` of the volume rows'
cells, not a per-cell mask. If a per-cell mask is needed for a consumer, build it in the frame, at rest.

### FS-S5. Putting the fuel tables in `CellStore`'s write window copies them twice per window

**Location:** `fire_solid.md::§1.1` ("inside `CellStore`'s write window"); code: `gates` 396ae10
`grid.py::CellStore.writing`. On entry it runs `{name: arr.copy() for name, arr in owners.items()}`, and on exit
`frozen(arr)` for each channel.

Each window copies every channel. Windows open per intent (`applier`, `place`) and per `advance`. Probe (b) measured
copy plus freeze for node tables at 5 f64 per node:

| Node count | Table size | Time per window |
|---|---|---|
| 4.8×10⁵ | 19 MB | 1.2 ms |
| 1.2×10⁶ | 48 MB | 2.5 ms |
| 1.2×10⁷ | 480 MB | **28 ms** |

At 1.2×10⁷ nodes that is also 0.96 GB of transients for the memory budget. A `strike` pays it all.

**Fix.**
Copy per table on first write (only the solid and the batch write `nodes`), or keep the tables out of the per-intent
window under their own single-owner rule; measure and budget it.

### FS-S6. No cost row, no limit numbers, and a slab's segment shape that moves cost 25×

**Location:** `fire_solid.md::§1.1` ("default 0.02 m along a rod or across a slab"), `§1.3` (`limits.yaml`, no
numbers), `§6` (no cost figure).

Probe (a): a full backward-Euler step with RAMP k(T) and c(T), a linearised front, kinetics and a `bincount` ledger,
12 nodes, 3 components:

| Kinetics | ns per node |
|---|---|
| Threshold | **26–29** |
| 3-reaction Arrhenius (`where` + `exp` over all nodes) | **47–52** (1.8×) |

"Across a slab" can mean two things:
- **Strips** 0.02 m wide spanning the slab. The front is 1D ("position in [0, 1] along the segment"), which suggests
  this reading.
- **0.02 m tiles.**

At 12 nodes and two parts per segment, 200 m² of slab 0.5 m wide gives:

| Shape | Nodes | Per step, threshold / Arrhenius | Node table |
|---|---|---|---|
| Strips | 4.8×10⁵ | 14 / 25 ms | 19 MB |
| Tiles | 1.2×10⁷ | **350 / 620 ms** | **480 MB** |


**Fix.**
- State the slab segment shape.
- Write a fire-solid budget in ms per physics step at the 1.92×10⁶-cell tile and at the max profile.
- Derive `limits.yaml`'s numbers from that budget and the measured ns/node, and record them in Known gaps.
- Add the kinetics' cost to R0's choice as a number, not as "work counters".

### FS-S7. The work-counter gate counts a constant on a one-slab run

**Location:** `fire_solid.md::§6` ("Work counters for node solves per step … yes, on any increase"), `§4.1` (cost as
an R0 criterion).

All awake in 6.1 (§7), node solves per step = node count: a function of authoring. It can't see the 1.8× between
the laws (FS-S6), padding, rebuilds or copies, and on a ~12-node cone run it guards nothing at scale.

**Fix.**
- Per-step maximum counters: node-steps (real and padded), `exp` calls, coupling rows built, topology events, bytes
  copied per window.
- Run them on a scene at the world limits, not on a cone.
- Keep B5's `process_time` as the secondary gate.

### FS-S8. The ragged node layout has no solver layout and no save rule

**Location:** `fire_solid.md::§1.1` (`nodes` keyed (object, seg, part, node); "node offset into `nodes`"; node
thickness per node), `§5.3`.

Node count varies with thickness and recipe. A Thomas solve vectorised over parts needs one N.

**Layout.** The design picks none of:
- padding to N_max;
- grouping by N;
- a per-part Python loop, which at 10⁴–10⁵ parts is orders slower.

Probe (f): padding with decoupled identity rows (a = c = 0 at the joint) is **bit-identical** to the unpadded solve,
so padding is safe for bits, but cost scales with N_max over N_mean. Grouping by N puts a part in a batch decided by
state, so it needs D1-S9's offset test.

**Save.** Offsets are untrusted input (F14). The loader must check that:
- offsets are monotone;
- they agree with the segments' parts;
- each part's count equals what the recipe's node rule gives for its saved geometry, with thicknesses positive and
  summing to the part's thickness;

and refuse otherwise. If a recipe's node rule changes between builds (its SHA-256 in the header differs), the saved
layout is the truth: either refuse, or carry a registered migration. Never re-derive it silently.

**Fix.** Choose the layout and record the padded fraction as a counter. Add the loader checks above, each with its
refusal test.

### FS-S9. Moving area between the ignited and unignited parts mixes two profiles, by no stated rule

**Location:** `fire_solid.md::§1.1` (segment front position; per-part area and nodes), `§4.2` (flash, extinction).

When the front moves, area passes between parts with their own profiles, by no stated rule. Once the ignited part
has regressed the layouts differ, so a node-wise merge is undefined, and area-weighted T doesn't conserve energy
under c(T).

Zero-area parts also need a rule. A flash threshold on "the unignited part's mass flux" must come from the per-m²
profile, never from a mass rate divided by a vanishing part area (K2_005's class, 5_numerics §5 "area hygiene").

**Fix.**
- For 6.1, state whether the front moves at all. In the cone, a part may flip whole at flash.
- If it moves, merge by enthalpy on a common layout, from the previous step's state, at most one boundary per step
  (D1-S7).
- A part at zero area keeps its profile and is skipped by a written rule.

### FS-S10. The every-step save test runs where nothing it must prove exists

**Location:** `fire_solid.md::§6` ("Save and load at every step of a cone run"), `§3` (R0 and R1 are grid-free).

A cone run has no cells, coupling, region join, insertion or burnout, so the test passes with the coupling table, counter and region join entirely missing from the save. No save writer
exists at `gates` 396ae10, and save v0 freezes only after the content-identity review (roadmap). The design doesn't
say which writer 6.0 uses.

**Fix.**
Add an every-step save test at 0.1 m (slab on the floor, a mid-run `imagine`, one burnout), and name the writer or
say it waits on save v0.

### FS-S11. Insertion makes position-independence load-bearing now, and the offset test is still missing (D1-S9)

**Location:** `fire_solid.md::§6` (no offset test), `§1.1` (sorted tables), `§4.1` (Arrhenius cutoff).

Each insertion, removal or gathered cutoff shifts later rows' array offsets, so a part's `exp` runs at a different
SIMD body or tail position after an unrelated `imagine`. Probe (g): 0 of 7 shifts changed bits
on arm64. The golden CI is x86-64, and that is untested.

**Fix.**
- Add the offset and subset test to §6, on the CI matrix at 1 and N threads.
- Implement the cutoff with `np.where` over the full array, or say that the gather is covered by that test.

### FS-S12. Contact coupling once per physics step has no scheme, and an explicit one sits near its limit

**Location:** `fire_solid.md::§3` ("Conduction … by contact conductance … with the cell's temperature";
"Frequency").

The surface node is sized to √(α·1 s). For PMMA that is about 0.33 mm, and ρc ≈ 1.7×10⁶ J/m³K gives C_node ≈
560 J/m²K (D). Applied explicitly at Δt = 0.5 s, the ratio is h_c·Δt/C_node ≈ **0.9 at h_c = 1,000 W/m²K**, and
contact conductances run from hundreds to thousands. That is on the edge of oscillation on the fuel side, and past it
for higher h_c or thinner first nodes. On the cell side the ratio is small (about 5×10⁻³ at 0.05 m).

Unstated: its place in 5a's law list, how the cell's share spreads over heat's 16–64 substeps, and that one
expression books both sides.

**Fix.**
- The contact term is a Robin condition inside the implicit 1D solve, with the cell's T frozen at the step's start.
- The cell receives exactly the node's negated gain, using the same f64 expression, deposited at a stated point in
  the law order.
- The R1 per-substep comparison then measures lag, not stability.

---

## NIT

### FS-N1. `region_id` and `recipe_id` must be persisted ids, with name maps in the save

**Location:** `fire_solid.md::§1.1`, `§2`.

Regions are a dict in insertion order today (`CellStore._regions`); a u16 indexing it shifts. Say that both ids are persisted (5a's region id array), and that the
save carries name → id maps, refused on mismatch.

### FS-N2. The object-id counter's edges

**Location:** `fire_solid.md::§1.1`, `§1.3`.

- At 2³² − 1, refuse; never wrap.
- Say whether burnt-out rows stay (`state` = burnt out) and count against the world limits. If they stay, the tables
  only grow; if they go, removal needs FS-B2's rule.

### FS-N3. The identity test needs a definition of how empty tables enter the digest

**Location:** `fire_solid.md::§6` (identity pattern), `§5.3`.

Today's digest is a test helper over cells, regions, sources and the clock (`tests/test_determinism.py::digest`).
Either empty tables contribute no bytes, or the identity compares the pre-6.0 fields only. Say which, or "bit for
bit" can't be tested.

### FS-N4. Reductions over objects: restate DP-S2's rule

**Location:** `fire_solid.md::§2` (`temperature_*` over surface nodes), `§5.3` (ledger lines).

Every reduction over objects or nodes (ledger lines, frame readings, the region join) is a `bincount` or a
fixed-order sum over the full table in key order, never `np.sum` over a gathered subset (round 1 measured 56 of 200
mismatches).

---

## What is sound

Persisted u32 ids (insertion is an append); integer-key order; profiles from authoring; delta-form backward Euler
with a hand-written Thomas; exactly-zero kinetics as an R0 criterion; convection to ambient; the R1 lag check.
