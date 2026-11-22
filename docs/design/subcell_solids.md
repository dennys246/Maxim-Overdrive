# Sub-cell solids: the contract (design draft, 2026-11-22; D34, D35; not yet reviewed)

**Scope.** This document is the contract for solid parts thinner than the world's cells can hold: a steel sheet, a glass
pane, a table's 4 cm leg. It covers:
- how a part is represented;
- the one object store and its tables;
- ownership and overlap;
- coupling to cells, objects and zones;
- acts and laws on objects;
- load and support;
- what NPCs and the client receive;
- the formats.

Mechanisms that nothing else depends on go to §13's build checklist as tests to write.

**It depends on PR #42** (`phase6/specgen-spike`), which carries D31–D35 (`decisions/world_model.md`) and the research
survey, `research/subcell_solids/survey.md`. Neither is on `main` at 703b745, where this draft was written. Read the
survey's §0 (what docs-contracts ruling 72 forbids, and why) and §1 (the options) before this one. They are not
restated here.

**Owners this design leans on, and never restates:**
- fuel objects, their store, coupling and formats: `fire_solid.md` §1–§5;
- the flow, the law list and the field registry: `sim_core.md` §5, §5.1, §6;
- the reconstruction rule, ownership and determinism: `world_model.md` §3, §5, §6;
- the fuel objects' wire columns: `client_objects.md` §3 (PR #40, accepted 2026-11-22);
- stimuli and perception: `sem_stimuli.md`;
- the gates and the log header: `boundaries.md` §5.3, §5.4, §6.3.

## 0. The answer

1. **A part is an object when its thinnest dimension is under `object_threshold_m`,** a length in data, proposed as
   0.4 m. The rule is applied per authored primitive, in metres, before any cell is touched. The grid's spacing and the
   part's offset never enter it, so one spec gets one representation on every rig (D35 (1); §2).
2. **Objects keep their authored primitives,** boxes and upright cylinders in metres, with a lumped or 1-D thermal
   profile chosen by a Biot number computed from data (D35 (2); §3.3).
3. **One store holds every object.** `fire_solid.md`'s `FuelStore` becomes `ObjectStore`, and each row gains a `role`:
   `fuel`, `structure` or `inert` (D35 (3); §3).
4. **`too_small` stops depending on where a part lands.** A part is refused only for being thinner than
   `min_part_thickness_m`, in metres, under a new code; the old code retires (§11.3).
5. **Regions may mix cells and objects** (§4). Every act and reading is defined on objects, which replaces
   `fire_solid.md` §2's `fuel_only_region` before it ships (§7).
6. **Both conflicts the survey names are resolved:**
   - objects exchange heat with zone gas once zones land, and `fire_solid.md` §3.1's ambient rule is kept for Phase 1
     only (§5.2);
   - an object closes gap area between authored zones, counted in integers (§6).
7. **Load is solved on a member graph** of bearing contacts in metres. A member fails when its load exceeds its
   capacity, gated with a margin. D33's placement check reads the same graph (§8). Until D32's bodies exist, a lost
   support is a Known gap with a strict red gate, never silent.

## 1. What this rests on

The rulings this design implements are kept in `decisions/world_model.md`: D22 and D26 (rubble and zones are Phase 2),
D31 (load), D32 (bodies), D33 (placement support), D34 (the defect, with its measurements) and D35 (the owner's three
answers). Docs-contracts ruling 72 (`reviews/docs_contracts/rulings.md`; stated in `world_model.md` §1.1) is the rule
§12 revises; its reasons are survey §0's. Each section below cites the ruling it serves.

## 2. The representation rule

### 2.1 The rule

For each authored primitive p, from a scene or a spec, its **thinnest dimension** t(p) is:
- for a box, its smallest edge, `min(max_m − min_m)`;
- for an upright cylinder, `min(2 · radius_m, z_m[1] − z_m[0])`.

| Condition | Representation |
|---|---|
| p is a fuel recipe entry (`fire_solid.md` §5.2) | an object, role `fuel`, at every t (unchanged) |
| `t(p) < min_part_thickness_m` | refused, `part_too_thin` (§11.3) |
| `min_part_thickness_m ≤ t(p) < object_threshold_m` | an object, role `structure` or `inert` (§3.2) |
| `t(p) ≥ object_threshold_m` | cells, voxelized by volume overlap (§2.3) |

- **Both thresholds are in `data/world/limits.yaml`** (§11.1). Proposed values: `object_threshold_m = 0.4`, which is
  two cells of the 0.2 m coarsest verification grid (`world_model.md` §1.1's thin-feature bar), and
  `min_part_thickness_m = 0.001`, the contact tolerance (`fire_solid.md` §1.3).
- **The comparison runs on the authored float64 values,** exactly as written. It is never run on a quantity derived
  from a grid. A part exactly at the threshold becomes cells.
- **Per primitive, not per spec.** One spec can give cells and objects together: a 3 m × 0.5 m concrete plinth carrying
  a 2 cm steel rail. Both belong to the spec's one region (§4.3).
- **Never dx:** representation, refusal and mass are functions of the authored primitives and the data only. The
  red-first test of §13 holds every rig and every sub-cell offset to that.

### 2.2 What this makes objects

Most furniture, panes, doors, pipes, rails, sheet-metal enclosures and posts under 0.4 m become objects; walls, floors,
slabs and blocks at or above 0.4 m stay cells. A 0.39 m concrete block is an object, and a 0.4 m one is cells. That
step is the price of a rule independent of dx. Both representations must give the same outcome class for a block near
the threshold, so §13 includes a test across the threshold: blocks of 0.38, 0.40 and 0.42 m under one fire and one
load.

### 2.3 Cells from authored primitives

Primitives at or above the threshold are voxelized **by exact volume overlap,** never by cell centre. That is
CLAUDE.md's deposit rule, already required for fuel initialisation (`world_model.md` §3's S3 row). A cell's material is
assigned when the primitive's overlap fraction is at least ½. Mass is computed from authored volume, never from counted
cells. A part at least two coarse cells thick keeps a stable material assignment at every offset. The verification tests
measure the residual surface aliasing at 0.2 m and record it as a Known gap with its numbers.

## 3. One store

### 3.1 `ObjectStore`

`fire_solid.md` §1.1's `FuelStore` is renamed `ObjectStore`, with the same tables, keys, window, copy-on-first-write,
reduction order and id counter. Only the changes are listed here.

| Table | Change |
|---|---|
| `objects` | adds `role` u8 (`fuel` 0, `structure` 1, `inert` 2); `material_id` u8 for `structure` and `inert` (`recipe_id` stays for `fuel`; the unused column holds its sentinel, 0xFF or 0xFFFF); `kind` adds `box` (origin f64×3, extent f64×3) and `cylinder` (centre f64×2, radius f64, z0 f64, z1 f64); `integrity` f64 in [0, 1]; `support` u8 (`anchored` 0, `bearing` 1, `loose` 2, §8.3); `pose` f64×7 (translation, unit quaternion), **reserved for D32 and fixed at identity**; `state` adds `failed` and `removed` |
| `segments` | for `box` and `cylinder` objects, one row per face (6 for a box, 3 for a cylinder: bottom, top, side), with its area, outward normal and the node it exchanges through (§3.3) |
| `nodes` | for `structure` and `inert` objects, one profile per object across its thinnest dimension (§3.3) |
| `contact` | adds object-to-object rows, keyed (`object_a` < `object_b`, `face_a`, `face_b`), with their contact area; still derived |
| `members` | new, derived: the bearing graph of §8.1, rebuilt per topology batch; never saved |

- **`kind` and `role` are independent:**
  - a fuel `slab` is `kind` `slab`, role `fuel`;
  - a 4 cm wooden leg is `kind` `box`, role `structure`;
  - a glass vase is `kind` `cylinder`, role `inert`.
- **Geometry stays immutable** until D32's bodies, as `fire_solid.md` §1.1 has it for fuel. Damage changes `integrity`,
  `state` and node thicknesses, never `objects`' geometry columns.
- **One mass truth:** an object's mass is its authored volume times its material's density, minus what its nodes have
  lost (`fire_solid.md` §5.4's inventory and `removed_kg`). Overlapping parts of one spec are refused (§4.2), so a
  volume is never counted twice.
- **Limits are shared:** `fire_solid.md` §1.3's `objects`, `segments`, `nodes` and `contact` limits count every role.
  Their values are re-measured at build step S1 (§13), under B5, with structural objects included.

### 3.2 Role

- **`structure`:** a member of the bearing graph (§8.1). It carries load from what rests on it and has a capacity.
- **`inert`:** it has mass and imposes load on its supports, but it is never a member, so it carries nothing.
- **`fuel`:** as `fire_solid.md` defines it: it imposes load, carries none, and burns under its recipe.
- **How a scene or spec picks a role:**
  - a part under the threshold is `structure` unless it is authored `inert`;
  - a spec part sets it with the optional key `role` (§11.2);
  - a fuel entry is always `fuel`.
- **Burning is a matter of material, not role.** A structural object burns if its material names a recipe in
  `data/materials/mechanics.yaml`'s `burns_as` (§11.1), as wood does, which `fire_solid.md` §4 runs on its nodes.
  Steel, glass, concrete and drywall name none in v0. That is how a leg that burns and a leg that carries load are one
  object (D35 (3)).

### 3.3 The thermal profile, by Biot number

For a `structure` or `inert` object:
- **The Biot number** is Bi = h_ref · (t / 2) / k, with t the thinnest dimension (§2.1), k the material's
  conductivity (`core.yaml`) and `h_ref` from `mechanics.yaml` (§11.1). Every input is authored or data, so it is
  never dx.
- **If Bi < `lumped_biot_max`** (data, proposed 0.1), the profile is lumped: one node, and every face exchanges through
  it.
- **Otherwise it is 1-D across t,** between the two faces normal to the thinnest axis: nodes by `fire_solid.md` §1.2's
  node rule, the first face reading node 0 and the opposite face the last node. The other faces (the edges) exchange
  through the profile's mean. A cylinder whose thinnest dimension is its diameter is 1-D radially; one whose thinnest
  dimension is its height is 1-D axially.
- **Survey §1's reference cases fall as expected:** 1 cm steel is lumped, a 6 mm pane is 1-D (Bi ≈ 0.1–0.3), and a
  4 cm pine leg is 1-D (Bi ≈ 4). The values are re-derived from the data at build step S2.
- **The choice is fixed at insertion** and saved with the layout, as `fire_solid.md` §5.5 requires: the saved layout
  is the truth.

## 4. Ownership and overlap

### 4.1 Objects against cells

- **An object owns no cell.** `world_model.md` §5's rule stands: each cell has one owner, through `region_id`.
- **An object may not overlap any solid region's authored geometry by more than 1 mm,** judged in metres on the CSG
  of `world_model.md` §5, never on cells. This extends `fire_solid.md` §1.3's rule from fuel to every role.
- **A structural cell `place` may not overlap an object.**
- **An object that touches a cell face**, with separation ≤ 1 mm and an overlap over 1 mm along each face axis
  (`fire_solid.md` §1.3), gets a contact row. Cell edges are integer micrometres (F13).

### 4.2 Objects against objects

- **No two objects may overlap by more than 1 mm,** across specs and within one. This is a change for structural
  specs: v0 lets one spec's primitives overlap, counting the volume twice. Spec v1 refuses it as `parts_overlap`
  (§11.3). The spike measures v0 as frozen (`research/specgen_spike/plan.md`), and stage 2 is written against v1.
- **Touching objects get contact rows** by the same separation-and-overlap test, in metres, with no cells involved.

### 4.3 Regions

- **A region may own cells and objects together.** This replaces `fire_solid.md` §1.3's "cells only or objects only".
- **A spec's or scene entry's parts are one region,** whatever their representation.
- **`Region` keeps its authored footprint,** which is now the union of its cell CSG and its objects' primitives, and
  its centroid is the volume-weighted centroid of both.
- **A region is gone** when it has no live cell and no object in state `live` or `failed`.

## 5. Coupling

### 5.1 Contact

- **Object to cell:** `fire_solid.md` §3.2's skin coupling, unchanged, for every role.
- **Object to object:** per contact row, one antisymmetric transfer per physics step,
  q = A · (T_a − T_b) / (1/h_a + 1/h_contact + 1/h_b), where:
  - T_a and T_b are each face's exchange node (§3.3);
  - h_a and h_b are each node's conductance to its face;
  - `h_contact` is in `mechanics.yaml`, per material pair, defaulting to its `contact_default`.

  It runs as a Robin condition inside both objects' implicit solves, as `fire_solid.md` §3.2's scheme does, and it is
  written to the declared field `contact_exchange` (`sim_core.md` §5.1). No law calls another.
- **dx enters only through cell contact rows and the skin's far boundary,** as `fire_solid.md` §3.2 states.
  Object-to-object coupling is grid-free.

### 5.2 Gas: the first conflict

- **In Phase 1, `fire_solid.md` §3.1's ambient rule applies to every object, of every role.** Phase 1 has no zones
  (D26), so a steel sheet in a burning room never heats from the room's gas. That stays a Known gap, recorded with the
  §3.1 numbers and extended to structure.
- **Once zones land (Phase 2),** every exposed face of every object exchanges with the gas of the zone it faces, not
  with the ambient:
  - convection and radiation, in the same forms as §3.1's loss, with T∞ replaced by the zone's gas temperature;
  - booked as one antisymmetric transfer to that zone's energy, ledger line `object_to_zone`;
  - this revises §3.1's "permanent for Phase 1" to "until zones land" (§12).
- **Which zone a face faces:** for each face, the area over each zone's air cells, probed 1 mm outward along its normal.
  It is computed from integer-micrometre cell edges and the face's authored geometry, cached per `topology_version`, and
  summed in sorted zone order. A face over two zones splits its exchange by those areas.
- **"No law heats air cells" stays** (`fire_solid.md` §3.1's guard). Zone gas is not air cells (`world_model.md` §2).
- **Object-to-surface radiation** is owned by `fire_model.md` §3.3's surface exchange, and joins when that lands.

### 5.3 The ledger

New terms in `fire_solid.md` §5.4's equation:
- storage: Δ(object nodes), all roles;
- internal and net zero: `object_contact`;
- output: `object_to_zone`, from Phase 2.

Every term is one transfer, limited by what the donor holds and applied antisymmetrically, never clamped afterwards
(`world_model.md` §4).

## 6. Zone topology: the second conflict

- **Zones stay authored in metres,** and their volumes and gap areas stay integer counts (`world_model.md` §2, §6).
  Objects never relabel a zone.
- **A gap's open area** for each (zone pair, z-bin) is its face count times the face area, minus a **blocked area**:
  - the summed projected area, onto that gap's cell faces, of every live object lying within 1 mm of the gap plane;
  - held as an integer number of square micrometres;
  - computed from object geometry quantized to integer micrometres, which is the same quantization as cell edges
    (F13).
- **Cadence:** recomputed per topology batch, assembled in sorted order, and equal bit for bit to a full recompute,
  under the Hypothesis property of `world_model.md` §6.
- **A pane filling a window gives the gap zero open area.** When the pane breaches (§7.2), the next batch restores the
  open area. That is the pane's breach joining the zones (survey §4).

## 7. Acts and laws on objects

Each act on an object resolves in one law, per `sim_core.md` §5.1's rule of one resolver per input kind. Objects take no
outcome from the applier.

### 7.1 The acts

| Act | On an object | Resolver |
|---|---|---|
| `strike` | the point in metres must lie within 1 mm of a live object's surface; the `Load` decrements its `integrity` by the strike law's closed form on the object's material and section | `damage.objects` |
| `ignite` | allowed on an object whose material `burns_as` a recipe, or on a fuel object; refused otherwise with today's `not_solid` sense, under a new code `not_flammable` (§11.3) | heat, as for fuel |
| `douse` | as on cells, through the object's faces | heat |
| `kindle` | `fire_model.md` §2.2's metric nearest-surface query, over cells and objects | 6.4's |

`fire_solid.md` §2's `fuel_only_region` is never built. Every act above is defined on every role.

### 7.2 The laws

- **`thermal_degrade`:** an object's strength factor is `mechanics.yaml`'s temperature table, read at the profile's
  minimum-strength node, never at the mean. That is the "decide at the point" rule applied to a 1-D profile.
- **Breach:** a `structure` or `inert` object is breached when its remaining thickness along its thinnest axis, in
  metres, falls below `breach_ligament_m` (data). That is `world_model.md` §3's strength-and-breach row on the object.
- **Glass cracking:** a glass object cracks when the ΔT between its centre node and its edge nodes crosses
  `mechanics.yaml`'s `crack_delta_t_k`. A cracked pane is breached. This binary outcome is band-gated, with a margin in
  input flux (ruling 60; survey §4). Its validation scatter is a Known gap.
- **`crack`** on an object is 1 − `integrity`, the same meaning as the cell channel (`world_model.md` §8, F1).
- **Destruction:** at `integrity` 0 an object's `state` becomes `removed`. Its remaining mass goes to its zone's fines
  species, or in Phase 1 to the ledger's `removed_with_mass`, so mass is never deleted (`world_model.md` §2). Fracture
  into new objects is out of scope; per-object local voxels are D35 (2)'s later kind.

### 7.3 Readings

- **`frames.QUANTITIES`** (`integrity`, `temperature_max`, `temperature_mean`, `breached`) is defined on a region's
  matter, both cells and objects:
  - `integrity` and `temperature_mean` are volume-weighted over cells and objects;
  - `temperature_max` is the maximum over cells and object nodes;
  - `breached` holds if any of its cells' axes or any of its objects is breached.
- **A cell-only region's value is bit-identical to today's,** pinned by a test. Every region that exists before this
  design is cell-only or fuel-only, so no recorded value changes meaning. `fire_solid.md` §2's cell-only pin is revised
  to this one (§12). **This is an owner question** (§14, item 1), because F1 says a new meaning gets a new name.

## 8. Load

### 8.1 The member graph

- **Its vertices:**
  - every object in state `live` (all roles, each with its weight);
  - one **anchor** per cell region connected to the world's floor by `world_model.md` §6's anchor test.
- **Its edges are bearing contacts:** contact rows (§4) whose contact normal is within `bearing_angle_deg` (data,
  proposed 30°) of vertical, so they can pass a vertical load in compression. In v1 nothing else is a joint: there is
  no glue, tension or authored joint.
- **Members** are the `structure` vertices. `inert` and `fuel` vertices only carry their own weight into the graph.
- **The graph is derived,** rebuilt per topology batch and from the `objects` table in key order, and never saved.

### 8.2 Capacity and the solve

- **Capacity, per member,** from authored geometry in metres and `mechanics.yaml`, scaled by the strength factor of
  §7.2:
  - crushing σ_c · A;
  - Euler buckling π² · E · I / (K · L)², with K = 1 for v1 (pinned at both bearings);
  - bending, for a member carrying load between two bearings, σ = M · c / I against σ_t.

  A, I and c come from the member's section in metres, never from cells. D31's measured risk was a 6.25× error in A and
  39× in I for a 4 cm leg on 0.1 m cells.
- **The load split** comes from a linear-elastic solve over the graph, with axial stiffness E · A / L per member edge,
  in float64. Vertices and edges are ordered by key, and the factorization is deterministic, so one machine gives
  bit-identical results. That makes a statically indeterminate four-legged table determinate. The solver is chosen at
  build step S4 against the closed forms of §13.
- **Cadence:** `per_physics_step`, in `sim_core.md` §5's tuple after the thermal laws. It runs only when a topology
  batch or a member's strength factor changed since the last solve, keyed on those versions (`sim_core.md` §7).

### 8.3 Failure and the hand-off

- **A member fails** when its load exceeds its capacity. That binary outcome is band-gated with a margin (ruling 60). A
  failed member's `state` becomes `failed`, and every vertex that loses its last bearing path to an anchor gets
  `support` `loose`.
- **Until D32's bodies land,** a loose object stays where it is, with its `support` set to `loose` and an event
  `support_lost` in the tick report. That is a **Known gap with a strict red gate:** a table whose leg chars through
  under its load falls (D31's case), `xfail(strict=True, raises=AssertionError)`.
- **The hand-off when bodies land** is D32's design. Cells whose support fails are D22's rubble. This design reserves
  `pose` and `support` so neither needs a format change.

### 8.4 Placement support (D33)

A `place`, or a scene entry, is refused as `unsupported` (§11.3) when any of its parts would be `loose` in the graph
built with the placed parts included. That is judged on authored geometry in metres, before any write, with
`pending`'s objects counted (`fire_solid.md` §1.4). Whether an imagined object may anchor another stays with D32 (D33).

## 9. Sensors and NPCs

- **NPC sensors reduce over volumes in metres, across cells and objects alike,** under `sem_stimuli.md`'s rows and
  `boundaries.md` §4.4's rule that percepts come only through physical channels at the perceiver. No sensor names a
  cell or an object.
- **New object quantities** (a load, a contact force, a support state) are registered fields under `sim_core.md` §6.
  They are perceivable only when `sem_stimuli.md` §7.4's registry marks them, which is false by default.
- **What an NPC senses of weight, contact and motion** is owned by `sem_stimuli.md` §3's body: a contact force at its
  receptors when it pushes or lifts, never an object's mass as a number. Motion waits for D32.
- **The bridge's surface** (`region_parts`, the affordances) changes only through the NPC fire note's ruling, which
  `fire_solid.md` §7 names. This design adds no affordance.

## 10. The snapshot

`client_objects.md` §3 owns the object columns (PR #40). This design hands it requirements, as `fire_solid.md` §5.6 did:
- `objects`: `role` u8; `kind` `box` and `cylinder` with geometry as f32 metres; `integrity` u8 in 1/255; `support` u8;
  `pose` absent until D32.
- `segments` for structural faces: `surface_temperature_c` f16, clipped to [−273, 6000] as `temperature_c` is.
- **Never by colour alone:** crack severity by shape (`client_objects.md` §6), and glow with brightness
  (`client_objects.md` §5).
- **Every tier draws every live structural object,** since it is gameplay geometry. A tier may simplify edges and
  shading, never existence.

## 11. Formats

### 11.1 Data

| File | Change | Holds |
|---|---|---|
| `data/world/limits.yaml` | version bump, refusal test for the old version (repo-only data) | `object_threshold_m`, `min_part_thickness_m`, `lumped_biot_max`, `breach_ligament_m`, `bearing_angle_deg`; `fire_solid.md` §1.3's limits, re-measured |
| `data/materials/mechanics.yaml` | new, `version: 0`, loader `load_mechanics` in `adapters/loaders.py`, gate row | per solid material, by name: `sigma_c_pa`, `sigma_t_pa`, `e_pa`, a strength-factor table against temperature, `h_ref_w_m2k`, `burns_as` (a recipe name or null), for glass `crack_delta_t_k`; `h_contact` per material pair, with `contact_default` |

- **`core.yaml` doesn't change.** `FuelCatalogue` (`fire_solid.md` §5.1) gains `mechanics.yaml`'s cross-references:
  every material has a row, and `burns_as` names a known recipe. Each has a catalogue refusal and a test.
- **Every value enters tagged as V, S, M or D** (`fire_solid.md`'s tags), and no M value enters `data/` unverified
  (`world_model.md` §11).

### 11.2 Scene and spec

- **Scene:** the next scene version after the one on `main` when S1 lands. A primitive may carry `role: inert`, and
  the representation follows §2.1. Scenes are repo-only, so the old version gets a bump and a refusal test.
- **Structural spec v1:** `{spec_version: 1, name, primitives}`, where each primitive may carry `role` (`structure` or
  `inert`).
  - It is checked against `Budget`, §2.1, §4.2 and §8.4.
  - An unversioned spec is refused as `bad_version` once v1 ships. Nothing persisted v0, so no migration is needed.
  - `fire_solid.md` §5.2's fuel spec v1 and this structural spec v1 are one format, decided at S1 with its owner.
- **`imagine`** stays step 5's intent (`fire_solid.md` §5.2), with `pending` (`fire_solid.md` §1.4) covering every
  role.

### 11.3 Refusal codes

Codes are appended to `refusals.RefusalCode`, each tested at its gate:
- **Spec and scene:** `part_too_thin`, `parts_overlap`, `overlaps_object`, `unsupported`, `unknown_role`.
- **Acts:** `not_flammable`; `not_on_object`, for a strike point off every surface of an object-only region.
- **Loaders:** `bad_version` for `mechanics.yaml`; catalogue codes `missing_mechanics` and `dangling_reference`.

`too_small` retires: it stays in the enum, as append-only requires, and nothing produces it. Its meaning, "no cell
centre fell inside", is the defect D34 names, and F1 forbids giving the name a new meaning.

### 11.4 Digest, save and header

- **Digested:** every `ObjectStore` table except `contact` and `members`, which are derived, plus `pending` and the
  counter (`fire_solid.md` §5.4). Empty tables add no bytes, so 5a's replay goldens are unchanged without objects.
- **Save, handed to step 9** (`fire_solid.md` §5.5's list plus):
  - `role`, `material_id`, `integrity`, `support` and `pose`;
  - name maps for `material_id`, remapped by name;
  - on load, `members` and the load solve are recomputed and must equal the stored digest.
- **The log header** records `limits.yaml` and `mechanics.yaml` as `boundaries.md` §6.3 says.

## 12. Revisions this design requires (proposed, not applied here)

| Document | Edit |
|---|---|
| `world_model.md` §1.1, thin features | "fuel objects are exempt only as `rod`, `slab` or `bed` recipes" becomes "parts thinner than `object_threshold_m` are objects (`subcell_solids.md` §2); fuel recipes are objects at any thickness". Ruling 72 is superseded |
| CLAUDE.md, the thin-features line | the same, citing `world_model.md` §1.1 as its owner |
| `world_model.md` §2, §6 | gap areas subtract object-blocked area (§6 here) |
| `world_model.md` §5 | an object owns no cell; a region may own cells and objects |
| `fire_solid.md` §1.1 | `FuelStore` becomes `ObjectStore`; the columns of §3.1 here |
| `fire_solid.md` §1.3 | "structural materials are cells" becomes §2.1's rule; "a region is cells only or objects only" is withdrawn |
| `fire_solid.md` §2 | `fuel_only_region` withdrawn before it ships; acts per §7.1 here; the `QUANTITIES` pin per §7.3 |
| `fire_solid.md` §3.1 | "permanent for Phase 1" becomes "until zones land (`subcell_solids.md` §5.2)"; the Known gap extends to structure |
| `fire_solid.md` §5.3, §5.6 | the codes of §11.3; the requirements of §10 |
| `client_objects.md` §3 (PR #40) | `role`, the box and cylinder kinds, `integrity` and `support` columns |
| `sim_core.md` §5, §6 | the laws `objects.thermal`, `damage.objects` and `load` in the tuple; the `ObjectStore` tables in the registry |
| `imagination.py` docstring | "voxelized into the grid like any authored primitive" becomes §2.1's rule |
| `docs/architecture.md`, Known gaps | the rig-dependent fit gap (D34) closes when S1 passes its red-first test; §5.2's and §8.3's gaps are added when their steps land |

## 13. Build steps, and the tests each owes

Every step is its own branch and review round. Every physics law ships with a closed-form test and a cross-grid test.

| Step | Lands | Tests (survey §4 has their numbers) |
|---|---|---|
| **S1. Representation and store**, after `fire_solid.md` 6.0b | §2, §3.1–§3.2, §4, §11.2–§11.3; no new physics | **red first:** the footstool, aquarium and locker specs (`spikes/specgen/arms.yaml`) at N sub-cell offsets × 0.2, 0.1, 0.05 m: the same representation, refusal outcome and mass at every one; every §11.3 code at its gate; Hypothesis: representation is a function of the primitives and data only; overlap tests in metres |
| **S2. Thermal on objects** | §3.3, §5.1, §5.3 | a lumped steel sheet under constant flux, dT/dt = q″/(ρ·c·t), and convective decay (τ ≈ 1,570 s at h = 25); a sheet between two solids; the Biot choice on survey §1's cases; ledger closure; the threshold test of §2.2 under one fire |
| **S3. Acts, laws and readings** | §7 | strike and breach on objects in metres; glass cracking's band gate; `thermal_degrade` at the profile's weakest node; the `QUANTITIES` pin on cell-only regions; destruction's mass to fines |
| **S4. Load** | §8 | a column's crushing load; Euler buckling of a 1 m × 1 cm steel rod; a simply supported beam; a four-legged table's split; a pine leg charred at β under load (D31's fire coupling); D33's `unsupported`; the red gate of §8.3 |
| **S5. Zones** (with Phase 2's zones) | §5.2, §6 | zone coupling closed form; a pane separating two zones at every grid and offset, and its breach joining them; gap integers against a full recompute |
| **S6. Snapshot** | §10 | `client_objects.md` §7's goldens and measured checks for the new columns |

## 14. Open questions for the owner

1. **Readings over mixed regions (§7.3).** Extend `QUANTITIES`' meaning from a region's cells to its matter, keeping
   every cell-only value bit-identical, or name new quantities? The author recommends extending, because no region that
   exists before this design changes value. F1's rule is the argument against.
2. **A lost support until D32 (§8.3).** A loose object stays where it is, behind a strict red gate. Is that acceptable,
   or does load wait for bodies?
3. **Burning structure (§3.2).** Wood structure burns through `burns_as`, which needs a solid recipe for wood. Should
   it land with S2, or should structural wood stay non-burning until 6.2's flames?
4. **The threshold's value (§2.2).** At 0.4 m, a 0.39 m block is an object. Confirm the value, or raise it.
5. **Spec v1 refuses overlapping parts (§4.2).** That changes the generator's contract for stage 2. Confirm it.
