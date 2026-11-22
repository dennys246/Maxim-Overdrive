# Sub-cell solids: the contract (design, 2026-11-22; D34–D37; round 1 and delta 1 folded)

**Scope.** The contract for solid parts thinner than cells can hold: a steel sheet, a pane, a 4 cm
leg. Mechanisms nothing else depends on go to §13's build steps as tests to write.

**It depends on PR #42** (D31–D35 and `research/subcell_solids/survey.md`). D36 and D37 record the owner's rulings
on the review (`reviews/subcell_solids/`).

**Owners it leans on, never restates:** `fire_solid.md` §1–§5 (fuel objects); `sim_core.md` §4–§7 (flow, laws,
Topology, registry); `world_model.md` §2–§6; `client_objects.md` §3 (wire); `sem_stimuli.md`; `tile_and_client.md`
§3.4 (codes); `boundaries.md` §5.3, §5.4, §6.3.

## 1. Landing order

- **S0 lands before `fire_solid.md` 6.0a:** a text revision of its §1.3, §2, §5.2, §5.3 and §7 (§12), so no code
  ships that would need withdrawing from the append-only enum (D36 (4), D37 (2)). This branch carries it.
- **S1–S6 follow 6.0b** (§13) on the Phase 2 line, each its own branch and review.

## 2. The representation rule

### 2.1 Geometry in whole micrometres

Every metric decision here is made on integers.
- **The domain:** every coordinate and radius must satisfy |v| ≤ `coordinate_limit_um` / 10⁶ m before it is
  quantized, or the part is refused `out_of_range`. So no quantum overflows int64.
- **The quantum:** q(v) = rint(v · 10⁶), int64 micrometres, F13's cell-edge quantum. Each coordinate and each radius
  is quantized once; everything after is integer arithmetic. A box edge is q(hi) − q(lo); a cylinder's diameter is
  2·q(r) and its height q(z₁) − q(z₀).
- **Specs are judged in their own frame,** before `imagination._offset` adds the origin. A placed point is
  q(origin) + q(local), never q(origin + local). A scene's primitives are judged on their authored values.
- **Every threshold is held in integer micrometres** in data (§11.1), and `scene`, `place`, the scorer and any client
  tool share this one rule.

### 2.2 The rule

For each authored primitive p, its thinnest dimension t(p) is the smallest of its edges for a box, or the smaller of
its diameter and height for an upright cylinder, in µm:

| Condition | Representation |
|---|---|
| p is a fuel entry (`fire_solid.md` §5.2) | an object, role `fuel`, at every t |
| p is `air` (a scene's carve) | cells, always |
| t(p) < `min_part_thickness_um` | refused, `out_of_range`, naming the part's index |
| `min_part_thickness_um` ≤ t(p) < `object_threshold_um` | an object, role `structure` or `inert` (§3.2) |
| t(p) ≥ `object_threshold_um` | cells (§2.4) |

- **Values:**
  - `object_threshold_um` = 400,000 (proposed). That is two cells of the 0.2 m coarsest verification grid,
    `world_model.md` §1.1's thin-feature bar, and the loader refuses a smaller value.
  - `min_part_thickness_um` = 3,000 (D37 (1)), above twice `contact_tolerance_um` (1,000), so no part can lie inside
    another within the tolerance. A 1 mm sheet is refused.
- **Per primitive, not per spec.** One spec can give cells and objects together, in one region (§4.3).
- **The shipped alley's walls and floor sit exactly on the threshold** and stay cells. Any change to the quantum is
  therefore a representation change, and S1 tests it.

### 2.3 Outcomes on both sides of the threshold

A 0.39 m part is an object and a 0.40 m part is cells. Where their laws give a different outcome class, the
difference is a Known gap with its numbers and a strict red gate, closed in a named step:

| Law | Object (< 0.4 m) | Cells (≥ 0.4 m) | Until |
|---|---|---|---|
| Heat | tile profiles (§3.3) | cell conduction, with §2.4's aliasing | same class; §2.4's gap |
| Strike | `integrity` falls by the sphere's share; no hole (§7.1) | the sphere's cells are destroyed: a hole | D35 (2)'s fracture kind |
| Gap blocking after a strike | the part still blocks until `breached` (§6) | a holed wall joins the zones | D35 (2)'s fracture kind |
| Breach | ligament in metres (§7.2) | `region_breached` (Known gap: axis from cell extents) | step 8a |
| Burning wood | burns from 6.2 (§3.2) | never (`fire_solid.md` D-S4) | the 6.2 design's wood cells |
| Load capacity | crushes, buckles, bends (§8.2) | rigid; no capacity | D22's cell capacity |
| Body contact | `sem_stimuli.md` §7.1 (§5.1) | cell faces exchange nothing in v1 | `sem_stimuli.md` §2.3's face row |
| Gap blocking, intact | projection (§6) | face count | same class |
| Readings | lab names only (§7.3) | `QUANTITIES` | the NPC fire note's ruling on objects |
| Acts, S1 to S3 | an act but `kindle` (`torch_pilot.md` §3, TP1) reaches a region's cell parts only; a strike meeting none destroys nothing, accepted | as today | S3 |

S1–S4 each owe the cross-threshold test for their rows: parts of 0.38, 0.40 and 0.42 m, at three grids and several
offsets (§13). A same-class row is a passing test, and every other row is a red gate whose reason names its "Until".
No row ever changes a refusal code.

### 2.4 Cells from authored primitives

- **A cell takes a primitive's material when the primitive covers at least half of it,** with the overlap computed
  exactly on integer µm. A tie at exactly ½ assigns the cell. This replaces the cell-centre rule (`scene.py`), so it
  is a digest break, recorded under `sim_core.md` §12 with a bump of F15's `derivation_version`.
- **Mass is the authored volume's,** never the counted cells'.
- **The residual is a Known gap:** a 0.4 m box becomes 0.4 to 0.6 m of cells by grid and offset, so heat capacity
  can reach 1.5× and crossing time 2.25×. It closes with B28's material fraction per cell.

## 3. One store

### 3.1 `ObjectStore`

`fire_solid.md` §1.1's `FuelStore` is renamed `ObjectStore`. The window, copy-on-first-write, key order, `pending` and
the counter are unchanged. Only the changes are listed here:

| Table | Change |
|---|---|
| `objects` | adds:<br>- `role` u8: `fuel` 0, `structure` 1, `inert` 2;<br>- `material_id` u8 for `structure` and `inert`, with the sentinel 0xFF for `fuel`; `recipe_id` takes 0xFFFF for `structure` and `inert`;<br>- `integrity` f64 in [0, 1];<br>- `breached` u8, 0 or 1;<br>- `support` u8: `attached` 0, `loose` 1, `unstable` 2 (§8.3);<br>- `pose` f64×7: (tx, ty, tz, qw, qx, qy, qz), qw ≥ 0, zeros +0.0. It is fixed at identity until D32.<br><br>`state` numbers `live` 0, `burnt_out` 1, `failed` 2, `removed` 3. Kinds stay `rod` and `slab`: an upright cylinder is a rod with axis z, and a box is a slab with axis-aligned edges and its thinnest edge as thickness |
| `tiles` | new, for `structure` and `inert` objects. Keyed (`object_id`, `tile`). A slab's tile is a through-thickness column under a patch of its two largest faces, cut at `tile_m` per material (§11.1) along length then width; a rod's is an axial and angular patch. The last tile along an axis takes the remainder. Glass first cuts its edge band as a ring of tiles exactly `edge_band_um` wide. The remaining faces are boundary conditions of the edge tiles. Each row holds the patch's area, centre and outward normals |
| `nodes` | for structure and inert tiles: one profile per tile across the thickness (§3.3) |
| `contact` | object-to-cell rows as `fire_solid.md` has them, extended to every role. Its derivation is §4.1's |
| `object_contact` | new, derived. Keyed (`object_a` < `object_b`, `tile_a`, `tile_b`), with the patch's polygon in µm and its area |
| `region_geometry` | new. Keyed (`region_id`, `primitive`): each cell part's authored primitive in µm, written at insertion |
| `craters` | new. Keyed (`region_id`, `seq`): each strike or rubble removal's metric volume against a cell region, as a µm sphere (centre, radius), appended by the act's resolver |
| `region_support` | new. Keyed `region_id`: `support` (§3.1's numbers) of an unanchored cell region in the statics graph |

- **Fuel keeps its `segments`** (strips, `fire_solid.md` §1.2); a structural face is `tiles`, so no row has two
  meanings.
- **Geometry stays immutable** until D32. Damage changes `integrity`, node thicknesses, `craters` and the state
  columns, never authored geometry.
- **One mass truth:** authored volume times density, minus node losses (`fire_solid.md` §5.4) and crater volumes.
  Overlap and containment are refused (§4.2); the only volume counted twice lies within `contact_tolerance_um` of a
  touching face, at most tolerance × patch area per contact.
- **Ids are minted** in part order within a spec, and in entry order at scene build.
- **Limits are per role:** fuel's are `fire_solid.md` §1.3's; structure and inert get their own object, tile and node
  limits; a global `object_contact` limit is added. All are counted with `pending` before acceptance and refused with
  `world_limit_objects`, `world_limit_nodes`, `world_limit_contact`, and the new `world_limit_tiles` and
  `world_limit_object_contact` (§11.3).

### 3.2 Role

- **`structure`:** a member of the statics graph (§8) with a capacity (§8.2); it can fail.
- **`inert` and `fuel`:** rigid vertices that pass load to what they rest on and are never checked for capacity, so
  they never fail. A sheet resting on a fuel crate is attached through it, and the crate carries its load. `fuel`
  also burns (`fire_solid.md` §4).
- **On a cell part,** cells are rigid with no capacity until D22, so a role there changes nothing until then; D22
  gives `inert` cells none. Every floor-connected cell region is an anchor whatever its role (§8.1).
- **How a role is set:** a part takes `structure` unless authored `inert`. `fuel` comes only from a fuel entry (§11.2).
- **Burning is by material, from the 6.2 design** (D36 (7)). A structure or inert object whose material names a recipe
  in `mechanics.yaml`'s `burns_as` burns under `fire_solid.md` §4 from 6.2. Until then no structural object burns, and
  wood cells never do (§2.3).

### 3.3 Tiles and the thermal profile

- **Tiles give lateral resolution.** A 3 m rail heated at one end is hot at that end, and neighbouring tiles of one
  object exchange heat by in-plane conduction.
- **Biot number:** Bi = h_ref · L_c / k. Here L_c is the tile's volume over its exposed area (r/2 for a rod), and k is
  the conductivity in `core.yaml`. `h_ref` is the material's exposure coefficient: convection plus radiation
  linearized at `t_ref_k`, both in `mechanics.yaml` with their source cited.
- **The profile:** a tile with Bi < `lumped_biot_max` is lumped, with one node, and 1/h_node = 0 in contact. Otherwise
  it is 1-D across the thickness, by `fire_solid.md` §1.2's node rule, with radial metrics for a rod.
- **Glass has an edge band** of width `edge_band_um`, which §7.2's crack criterion reads against the interior.
- **Fixed at insertion and saved,** as `fire_solid.md` §5.5 requires: the saved layout is the truth.

## 4. Ownership and overlap

### 4.1 Objects against cells

- **An object owns no cell** (`world_model.md` §5).
- **A cell region's present geometry** is its `region_geometry` minus its `craters`, in µm. It is grid-free, and it
  is what every rule below reads, never cell faces.
- **Overlap and contact are judged against present geometry.** An object may not overlap it by more than
  `contact_tolerance_um`, and it touches it when the separation is ≤ the tolerance and the overlap exceeds it along
  each face axis. A crater under a bearing removes the contact in the batch that records it (§7.4), and an
  `imagine` into a blasted gap sees the gap.
- **A contact's exchange lands on the live cells under the patch,** weighted by area, each through its skin. A patch
  with no live cell under it carries no exchange, so no law heats air cells.
- **The fuel rule moves with it** (§12, S0).

### 4.2 Objects against objects, and within a spec

- **Overlap is measured exactly per pair of kinds,** in integer µm: box against box by axis intersections, box against
  cylinder by the disc's distance to the rectangle, and cylinder against cylinder by centre distance squared.
  - **Across specs and with existing objects:** an overlap beyond the tolerance, or containment, is `space_taken`,
    the same code cells give.
  - **Within one spec:** it is `parts_overlap`. This changes v0, which let a spec's parts overlap and counted the
    volume twice (D36 (7)).
- **Touching objects get `object_contact` rows** by the same test.

### 4.3 Regions and insertion

- **A region may own cells and objects.** A spec's or scene entry's parts are one region, with the union of its parts
  as its footprint.
- **The whole region enters at the drain** (`fire_solid.md` §1.4). Its cell parts' paint requests, its
  `region_geometry` and its objects are applied in one Topology batch, so no step sees half an object. Cell parts'
  occupancy is judged in µm on present geometry, never on `mask & grid.solid`.
- **A region is gone** when it has no live cell and no object in state `live` or `failed`. `applier._check_region`
  follows this rule (§12).

## 5. Coupling

### 5.1 Contact

- **Object to cell:** `fire_solid.md` §3.2's skin coupling, for every role, on §4.1's patches.
- **Object to object, one coupled solve:** the solid law (`fire_solid.md` §4, extended to every role's nodes)
  assembles each contact island, a connected set of touching objects, into one implicit system. The conductance
  1/(1/h_a + 1/h_contact + 1/h_b) is the coupling term. Each transfer is booked once, as ±H·A·(T_a − T_b)·Δt at the
  end-of-step temperatures, so it is antisymmetric and stable at any capacity ratio. Islands run in order of their
  smallest `object_id`.
- **Body to object:** owned by `sem_stimuli.md` §7.1. At contact onset a body reads the touched tile's surface node
  into its carried sub-mesh, and from then on writes §7.1's exchange field, which the solid law reads and resets like
  `contact_exchange`; §3.3's profile never sets the skin's contact temperature. Object tiles are `radiant_emitters`
  rows when §7.1's irradiance lands, keyed with the tile in place of the primitive (§12).
- **dx enters only through cell contact rows and the skin's far boundary.**

### 5.2 Gas: the first conflict

- **Phase 1:** `fire_solid.md` §3.1's ambient rule applies to every role. It is a Known gap extended to structure,
  with §3.1's numbers, and it must close (S5) before any NPC contact row reads an object.
- **When zones land (Phase 2):** each exposed tile exchanges with the gas of the zone it faces: convection, and
  radiation with the gas emissivity `epsilon_gas` (data). It is booked as one antisymmetric transfer to the zone
  (`object_to_zone`). This revises §3.1's "permanent for Phase 1" to "until zones land" (§12).
- **The zone a tile faces** is the authored zone volume containing the point `contact_tolerance_um` outward from its
  centre, judged in µm on authored zones, never on cells.
- **"No law heats air cells" stays:** zone gas is not air cells.

### 5.3 The ledger

These are new terms in `fire_solid.md` §5.4's equation:
- storage: Δ(object nodes) for every role;
- internal and net zero: `object_contact`;
- output, from Phase 2: `object_to_zone`.

Every term is one transfer, limited by what the donor holds and never clamped afterwards.

## 6. Zone topology: the second conflict

- **An opening is the authored interface between two zones' volumes,** in µm. Neither the zones nor the opening is
  relabelled by objects.
- **An object blocks an opening** when it spans the opening's plane within `contact_tolerance_um`, is in state `live`
  or `failed`, and is not `breached`.
- **Blocked area is the union of the blocking objects' projections, clipped to the opening.** A disc projects as the
  regular polygon of `disc_sides` (data) whose vertices are rounded to µm, so no transcendental function is
  evaluated. The union is computed in exact rational arithmetic on those vertices and floored once to whole µm². The
  open fraction is (opening − blocked) ÷ opening, applied to `world_model.md` §6's integer gap area by integer floor
  division. It never goes negative, and nothing is clamped.
- **Cadence:** recomputed in each Topology batch that changes a blocking object (§7.4), and equal bit for bit to a
  full recompute.

## 7. Acts, laws and readings

### 7.1 Acts

Each act resolves in one law (`sim_core.md` §5.1). Objects take no outcome from the applier.

| Act | On an object | Resolver |
|---|---|---|
| `strike` | **The target:** the region's footprint plus σ, as `applier._on_region` judges cells today, with the footprint the union of its cell and object parts; off it, `not_on_region`. Within it, the part struck is the nearest by `torch_pilot.md` §3's shared ranked query; ties break on the smallest distance in µm, then a cell part before an object, then the smallest `object_id`.<br>**The effect:** the strike's metric damage sphere (`damage.strike`) is intersected with the part. On cells it destroys cells and appends a `craters` row; on a `structure` or `inert` object `integrity` falls by the destroyed share. A fuel object takes no strike until 6.2's design, so fuel's `state` stays 0 or 1 | a resolver module in `damage.loads`'s declared tuple, `per_record` |
| `kindle` | `torch_pilot.md` §3's target rule, which owns it (TP1). A target that can't burn behaves as a non-burning cell surface does | 6.1b's |
| `douse` | as on cells, through the object's tiles | `fire_model.md`'s next revision |

`ignite` is retired by vocabulary v1 (`tile_and_client.md` §3.2) and has no row. Until S3 defines these rows, §2.3's
interim row applies.

### 7.2 Laws on objects

- **Strength, integrated over the section.** A member's capacity integrates its material's strength factor
  σ(T(x))/σ(T₀) over the remaining section of each tile row it bears through, and E(T) enters I for buckling. A
  minimum-node read is used only for local events such as breach.
- **Breach:** a tile is breached when its remaining thickness falls below `breach_ligament_um`, and the object is then
  `breached`. `breach_ligament_um` < `min_part_thickness_um`, checked by `MaterialCatalogue` against the loaded
  limits (§11.1), so nothing is breached at insertion.
- **Glass cracking:** a pane cracks, and is `breached`, when max over interior tiles of (T_tile − T̄_band) ≥
  `crack_delta_t_k`. This is an in-plane ΔT, the criterion of Pagni and Joshi and of Keski-Rahkonen. The binary
  outcome is band-gated with a margin in input flux (ruling 60), and its validation scatter is a Known gap. Any
  material with `crack_delta_t_k` cracks; no code keys on a material's name.
- **Destruction:** at `integrity` 0 a `structure` or `inert` object becomes `removed`. Its remaining mass goes to its
  zone's fines species, or in Phase 1 to `removed_with_mass`. Fracture into new objects is out of scope (D35 (2)'s
  later kind).

### 7.3 Readings

- **`frames.QUANTITIES` keeps its cell meaning,** pinned by test. A mixed region reduces over its cells only.
- **An object-only region is refused by `Frame.reading` and `region_parts`,** as `fire_solid.md` §2 has it for
  fuel: never 0.0 and never NaN. A region that becomes object-only during play is refused from that step, and an
  already-built `RegionInstrument` reports it as unavailable, never raising into Maxim (§13). So the bridge's
  surface, `QUANTITIES` and the affordances are unchanged (D36 (2)).
- **Object readings get new names on a lab surface,** under `tests/` or a lab builder, never in `QUANTITIES` or on an
  NPC builder. They reduce over cells by flat index, then objects by key, by `bincount`.

### 7.4 State changes are Topology requests

Object and region state transitions are keyed-table requests applied by `Topology` (`sim_core.md` §5.1). They are:
- `state` (`burnt_out`, `failed`, `removed`);
- `breached`;
- `support`, on objects and in `region_support`;
- a `craters` row.

Each batch that applies one bumps `topology_version`, so `contact`, `object_contact`, zone faces, blocked area and the
statics graph rebuild in the step the change happens. A request is emitted only when it changes a value. They come
from:
- the solid law: burnt out, breached, cracked;
- `damage.loads`: removed, craters;
- statics: failed, support.

`Topology` is the only writer of those columns, and `damage.loads` is the only writer of an object's `integrity`
after insertion.

## 8. Statics

### 8.1 The graph

- **Vertices** are every live object of every role, and every cell region not anchored. Each is a rigid body with
  three degrees of freedom: a vertical translation and tilts about x and y.
- **A failed member leaves the solve.** Its bearing contacts are removed from the graph, so it neither carries nor
  loads anything, and its capacity is never checked again. It holds in place under §8.3's D32 gap.
- **Anchors** are the domain floor (the plane z = 0) and every cell region connected to it. Connection is judged by
  §4.1's contact test on present geometry, never through cells. Each connected component has its own anchor, keyed by
  its `region_id` and its smallest `region_geometry` key; a split region gets two anchors.
- **Bearing contacts carry load.** A bearing contact is a contact whose normal is within `bearing_angle_deg` of
  vertical. Its points are the vertices of its patch polygon in µm. Each point is a compression-only spring whose
  stiffness is the series axial stiffness of the two parts, E·A/L each, with the patch area shared among the points.
  A point whose separation is within `contact_tolerance_um` starts at zero gap.
- **Islands are built from bearing contacts only.** A vertex linked to the anchored set only by side contacts stays
  outside the solve and keeps `attached` (D36 (1)). Its weight reaches no support: side contacts carrying no load is
  a Known gap until joints exist.
- **Cell regions enter as loads and supports.** An unanchored cell region resting on objects is a vertex with its
  present geometry's weight, and its outcome is held in `region_support`. An anchored cell region is a support.
- **Derived,** rebuilt in each batch that changes topology, from the tables in key order, and never saved.

### 8.2 The solve

- **Per island:** each connected set of vertices that touches an anchor through bearing contacts is one SPD system,
  solved by a direct Cholesky factorization in float64. Degrees of freedom are ordered by vertex key, then
  (w, θx, θy). Islands are ordered by their smallest key, so an unrelated object can't change a table's split.
- **Compression only, by an active set:** solve with every bearing point active; deactivate every point in tension at
  once; reactivate any inactive point whose gap closes; repeat until nothing changes or `statics_max_iterations` is
  reached. The iterations are counted as work (`sim_core.md` §10).
- **Capacity per `structure` member,** the strength-integrated section of §7.2 against these modes:
  - crushing;
  - Euler buckling π²·E·I/(K·L)², with K = `buckling_k` (data, 2.0 in v1: no joint restrains the upper bearing
    laterally);
  - bending between bearings, at their positions in metres.
- **Undefined results are defined outcomes.** If the system is singular, any result is non-finite, or the iteration
  cap is reached, every non-anchor vertex of that island gets `support` `unstable`. It is never an exception inside the
  step.
- **Cadence and key:** statics is a law, `per_physics_step`, after the solid law. Its key is the write ticks of every
  field it reads: node temperature and thickness, density, `integrity`, the state columns, `craters` and
  `topology_version`. It reruns when any of them moves. Per-member loads are derived, recomputed on load and never
  digested. The outcomes `state` and `support` are digested.
- **The solver's identity,** with the BLAS and its thread count, is part of the law's version and the log header.

### 8.3 Failure, and what waits for D32

- **A member fails** when its load exceeds its capacity, band-gated with a margin (ruling 60). Every member over
  capacity fails at once, leaves the solve (§8.1), and the island is re-solved, repeating until none fails, within the
  step and counted as work. So a table whose legs fail one by one cascades in that step.
- **A vertex with no contact path to an anchor becomes `loose`.** This is the only meaning "loose" has before D32
  (D33, D36 (1)).
- **Until D32,** loose, unstable and failed parts hold in place. That is a Known gap with a strict red gate: a table
  whose leg chars through under load falls (D31's case). It is tagged ANALOG with D32 as the step that earns it. No
  NPC perception or learning bar may depend on it (D36 (7)). `support_lost` is a host-side log record, never a
  `StimulusEvent` or text an NPC can read.
- **Hand-off:** D32's design takes loose, unstable and failed parts. D22 reads `region_support` to find the cells
  whose support failed.

### 8.4 Placement (D33)

- **A spec's own parts must connect.** In the spec's own frame, the base is every part whose lowest point lies within
  `contact_tolerance_um` of the spec's lowest point. A part with no contact path to the base is `parts_disconnected`,
  a spec fault.
- **The placement must attach.** In the world, with `pending` counted, a part with no contact path to an anchor is
  `unsupported`, a world outcome. There is no snapping: a base placed 3 mm above anything doesn't touch.
- Stability is judged after acceptance (§8.3).

## 9. Sensors and NPCs

- **NPC sensors reduce over volumes in metres** under `sem_stimuli.md`'s rows and `boundaries.md` §4.4. No sensor
  names a cell or an object.
- **The bridge is unchanged** (§7.3). The NPC fire note's trigger moves ahead of the first step that makes an
  object-only region reachable by an NPC act: S3, which defines acts on objects, because `fire_solid.md` §7's premise
  (the bridge untouched) holds only until then.
- **Never perceivable,** in the class of material ids (`sem_stimuli.md` §7.4):
  - `support`, `role`, `material_id` and `breached`;
  - capacities and object `integrity`;
  - the statics graph, `region_support` and `craters`.

  Only a force or a temperature at a receptor's site may be perceivable.
- **Stage-2 refusals go through `sem_stimuli.md` §6.2's receipts.** Every target-dependent refusal this design
  produces does: `space_taken` on objects and `unsupported`. T11's sweep gains material and support categories (§12).
- **Weight, contact force and motion have no row yet:** a future `sem_stimuli.md` row at receptor sites, frozen with
  D32's or the body-support design, triggered by the first act or state that puts a body's weight on an object or lets
  it push or lift one. Until then it is a named perception gap. Maxim's side binds through M11, a question to GL3's
  `mechano_proprio`.

## 10. The snapshot

`client_objects.md` §3 owns the wire. This design hands it requirements in that document's grammar:
- **Fuel's tables are unchanged:** `objects`, `rods`, `slabs` and `segments`, with `state` 0 or 1. Structural objects
  never appear in them.
- **A new required table, `structures`:** keyed `object_id`, with:
  - `region_id`, and `material_id` (in `welcome`'s material map);
  - `role`, `kind`, `state` (§3.1's numbers), `breached` and `support`;
  - `integrity` (u8, linear 1/255).

  Its geometry goes in new required tables `structure_rods` and `structure_slabs`, in the fuel tables' column forms.
- **A new required table, `tiles`,** keyed (`object_id`, `tile`), with `surface_temperature_c` as f16, clipped as
  `segments` is. Each `structures` row carries its tile counts along length and width, so the client never recounts
  the tiling.
- **The protocol bumps** for the new required tables (`client_objects.md` §3.1). Frame bytes and the join cap are
  re-derived at S6 with structure's limits.
- **The presentation view:** `fire_solid.md` §5.6's `FuelFrame` becomes `ObjectFrame` (`objects_version`), with the
  same site, cadence and leak rule: presentation only.
- **Never by colour alone;** every tier draws every live structural object.

## 11. Formats

### 11.1 Data

| File | Holds |
|---|---|
| `data/world/limits.yaml` (6.0a's v0, bumped at S1) | **Thresholds:** `object_threshold_um`, `min_part_thickness_um`, `contact_tolerance_um`, `coordinate_limit_um` (proposed 10⁸, 100 m).<br>**Limits:** the per-role object, tile and node limits; `object_contact`; statics' `statics_max_iterations` and its island size.<br>**Cross-checks:** 2·tolerance < minimum < threshold, and threshold ≥ 400,000 |
| `data/materials/mechanics.yaml` (new, v0, `load_mechanics`, gate row) | **Per solid material, by name:** `sigma_c_pa`, `sigma_t_pa`, `e_pa`, a strength-factor table, `tile_m`, `h_ref` inputs and `t_ref_k`, `lumped_biot_max`, `breach_ligament_um`, `bearing_angle_deg`, `buckling_k`, `burns_as`, and optionally `crack_delta_t_k` with `edge_band_um`.<br>**`h_contact`,** keyed by the sorted pair `a\|b`.<br>**Global:** `contact_default`, `disc_sides`, `epsilon_gas` |

- **The loader refuses:**
  - any non-finite or non-positive physical value;
  - a strength-factor table whose temperatures don't strictly increase, or whose factors lie outside [0, 1];
  - `bearing_angle_deg` outside (0, 90);
  - a repeated pair as `duplicate_key`, and a pair not in sorted order as `bad_key`.

  Each refusal has its test and gate row.
- **`fire_solid.md` §5.1 owns the data-file list.** It gains `mechanics.yaml`, its header digest and the shipped-data
  test's key (§12). `FuelCatalogue` becomes `MaterialCatalogue`. It checks that every material has a row, that
  `burns_as` names a known recipe, and the cross-file rule `breach_ligament_um` < `min_part_thickness_um`.
- **Values enter tagged V, S, M or D,** and no M value enters `data/` unverified.

### 11.2 Scene and spec

- **One tagged spec format, v1, shared with fuel:** `{version: 1, name, parts}`. The discriminator is the `recipe`
  key:
  - with it, a part is a fuel entry, as `fire_solid.md` §5.2 defines it;
  - without it, a structural part, `{kind: box | cylinder, geometry, material, role?}`.

  A `kind` its form doesn't admit is `kind_not_admitted`, checked before any other key, as is `role: fuel` on a
  structural part. `version` is `Format`'s key (`schema.read_version`). It is settled in S0, before 6.0b ships a
  different v1.
- **v0 is defined explicitly:** an unversioned `{name, primitives}`, the one spec form `Format` reads without a version
  key, as a named exception in `schema.py` (§12). It migrates to v1 with every primitive a structural part and no
  role. The migration never changes geometry, so a v0 spec whose parts overlap is refused under v1's rules. The
  spike's committed specs stay readable. Stage 1 is scored under v0, as frozen, and v1 scoring is stage 2's (§12).
- **`SpecId`** (`ip_and_licensing.md` §6.1) hashes the migrated v1 form, so `version` and `role` join the hash.
- **Scene:** the next version after `main`'s when S1 lands. A primitive may carry `role: inert`. Scenes are
  repo-only, so the old version gets a bump and a refusal test.

### 11.3 Refusal codes

One set of codes serves fuel and structure (D36 (4)):

| Code | New? | Class | Where |
|---|---|---|---|
| `out_of_range` | no | spec fault | a coordinate beyond `coordinate_limit_um`, a part under the minimum thickness, a zero volume, an unknown role value, or fuel geometry out of range |
| `parts_overlap` | yes | spec fault | two of one spec's parts overlap, or one contains another |
| `parts_disconnected` | yes | spec fault | a part with no contact path to the spec's base (§8.4) |
| `kind_not_admitted` | 6.0b's | spec fault | a kind its form doesn't admit, or `role: fuel` on a structural part |
| `space_taken` | no | world outcome | overlap with any existing cells or objects, fuel included |
| `unsupported` | yes | world outcome | no contact path to an anchor at the placement (§8.4) |
| `outside_extent` | no | world outcome | a part outside the world, from `place` and the scorer |
| `not_on_region` | no | world outcome | a strike point off the region's footprint plus σ |
| `world_limit_tiles`, `world_limit_object_contact` | yes | world outcome | §3.1's new limits |
| `missing_mechanics` | yes | loader | a solid material without a `mechanics.yaml` row |
| `bad_key` | yes | loader | an `h_contact` pair not in sorted order |

- **The classes are what a generator may be fed:** spec faults, with the part's index (a number the world writes);
  never world outcomes (D36 (3)). The class column belongs with `tile_and_client.md` §3.4 (§12).
- **A code is a function of authored geometry, the spec and the world in metres,** never of representation: it reads
  the same for a 0.39 m part and a 0.41 m part.
- **`too_small` is produced by nothing.** Its producers are recoded: the cell-centre test disappears with §2.4,
  `scene._check_volume`'s zero volume becomes `out_of_range`, and `_voxelize`'s outside-the-world branch becomes
  `outside_extent`. An `imagine` refused as `too_small` before S1 and accepted after it is a replay break, recorded at
  S1.

### 11.4 Digest, save and header

- **Digested:** every `ObjectStore` table but `contact` and `object_contact` (derived), with `region_geometry`,
  `craters` and `region_support`, plus `pending` and the counter. The new members change every tick's digest even
  when they are empty, because the digest hashes each member's name and shape (`sim_core.md` §9). That is a break,
  recorded at S1, with the new tables placed after fuel's in the registry's order.
- **Save, handed to step 9,** is `fire_solid.md` §5.5's list plus:
  - the new columns, `tiles`, `region_geometry`, `craters` and `region_support`;
  - name maps for `material_id`, `recipe_id` and `region_id`.

  The reader refuses any of these:
  - a `pose` other than identity before D32;
  - an enum value outside its numbers;
  - an `integrity` that is non-finite or outside [0, 1];
  - a saved `support` that differs from statics recomputed from the saved `state`. `state` is history, checked only
    for its enum values.
- **The log header** records `limits.yaml`, `mechanics.yaml` and the statics solver's identity (§8.2).

## 12. Revisions this design requires

S0's rows are applied on this branch (D37 (2)); the rest are proposed for their steps.

| Document | Edit |
|---|---|
| **S0, applied:** `fire_solid.md` §1.3 | representation is §2.2's rule; contact and overlap against present geometry in µm (§4.1); regions may mix; per-role limits |
| **S0, applied:** `fire_solid.md` §2 and §7 | acts reach a region's cell parts only until S3 (§2.3), so `fuel_only_region` never ships; readings and `region_parts` keep refusing object-only regions |
| **S0, applied:** `fire_solid.md` §5.2, §5.3 | one tagged spec v1 (§11.2); `overlaps_fuel` becomes `space_taken`; `geometry_out_of_range` becomes `out_of_range`; `fuel_only_region` is dropped |
| `fire_solid.md` §1.1, §1.2, §3.1, §4, §5.1, §5.4–§5.6 | `ObjectStore` and §3.1's tables; §3.1's "until zones land" (§5.2); the solid law over every role and object islands (§5.1); `mechanics.yaml`, `MaterialCatalogue`, the digest and save lists, `ObjectFrame` |
| `world_model.md` §1.1, and CLAUDE.md's thin-features line | thin parts are objects (§2); ruling 72 is superseded |
| `world_model.md` §2, §5, §6 | solids live in cells and objects; an object owns no cell; present geometry; gap areas take §6's open fraction |
| `sim_core.md` §4 | `support_lost` is a host-side log record, not a `TickReport` field |
| `sim_core.md` §5, §5.1 | the statics law; `damage.loads`'s object resolver; §7.4's request kinds, and which bump `topology_version` |
| `sim_core.md` §9, §12 | the new digest members and their place; the breaks of §2.4, §11.3 and §11.4 |
| `schema.py` (`Format`) | spec v0 as the one named format read without a version key (§11.2) |
| `applier.py` (`_check_region`, `_on_region`) | §4.3's "gone"; the footprint as the union of cell and object parts (§7.1) |
| `tile_and_client.md` §3.4 | the new codes, and a class column (spec fault or world outcome) |
| `sem_stimuli.md` §6.2, §7.4, §2.2 | T11's material and support categories; the never-perceivable list (§9); the future contact-force row and its trigger |
| `sem_stimuli.md` §7.1 | object contact read at onset into the carried sub-mesh; `radiant_emitters` keyed by tile for objects (§5.1) |
| `client_rendering.md` §4.1 | `welcome` carries the material map (§10) |
| `fire_model.md`, its next revision | `douse` over objects (§7.1) |
| `torch_pilot.md` §2 (TP1) | after S1, a pilot's target follows §3.1's states and §4.3's "gone" |
| `client_objects.md` §3 | §10's tables, the protocol bump, and the re-derived bytes and join cap |
| `ip_and_licensing.md` §6.1; `imagination.py` (`SPEC_KEYS`, docstring); `scene.py` docstring | v1 and the migration; §2's rule; §2.4's voxelization |
| `docs/architecture.md`, Known gaps | §2.3's rows; §2.4's aliasing; side contacts; §5.2's ambient gap; §8.3's hold-in-place gap |
| The spec generator spike's stage 2 design | what v1 replaces: the instruction "may touch or overlap" becomes "may touch"; M2's connectivity becomes §8.4's; the scene places at z = 0; the A3 loop feeds back spec faults only |

## 13. Build steps

Every physics law ships with a closed-form test and a cross-grid test (§2.3's scenarios at three grids and several
offsets). Each step's tests to write are in `docs/plans/checklists.md`, "Sub-cell solids", including the
mechanism findings delta 1 moved there under B33 (`reviews/subcell_solids/fold2.md`).

| Step | Lands |
|---|---|
| **S0, before 6.0a** | §12's S0 rows |
| **S1. Representation, store, ownership** | §2, §3.1–§3.2, §4, §7.4, §11 |
| **S2. Thermal** | §3.3, §5.1, §5.3 |
| **S3. Acts, laws, readings** | §7 |
| **S4. Statics** | §8 |
| **S5. Zones, with Phase 2's zones** | §5.2, §6 |
| **S6. Snapshot** | §10 |
