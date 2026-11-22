# Sub-cell solids: the contract (design, 2026-11-22; D34–D36; round 1 folded)

**Scope.** The contract for solid parts thinner than the world's cells can hold: a steel sheet, a glass pane, a
table's 4 cm leg. Mechanisms nothing else depends on go to §13's build steps as tests to write.

**It depends on PR #42** (`phase6/specgen-spike`), which carries D31–D35 (`decisions/world_model.md`) and the survey
`research/subcell_solids/survey.md`. Read the survey's §0 and §1 first; they aren't restated here. D36 records the
owner's rulings on round 1 (`reviews/subcell_solids/`).

**Owners it leans on, never restates:** `fire_solid.md` §1–§5 (fuel objects); `sim_core.md` §5–§7 (flow, laws,
Topology, registry); `world_model.md` §2–§6; `client_objects.md` §3 (wire); `sem_stimuli.md`; `tile_and_client.md`
§3.4 (codes); `boundaries.md` §5.3, §5.4, §6.3.

## 0. The answer

1. A part is an object when its thinnest dimension, in whole micrometres on the spec's own coordinates, is under
   `object_threshold_um` (D35 (1); §2).
2. Objects keep analytic geometry in metres, as the kinds `slab` and `rod`, with tiled faces and per-tile profiles
   chosen by Biot number (D35 (2); §3).
3. One store, `ObjectStore`, holds every object, each with a `role` (D35 (3); §3).
4. NPC quantities stay on cells, and refusal codes never reveal the representation (D36 (2), (3); §7.3, §11.3).
5. Load is statics: rigid parts, compression-only bearing contacts, a deterministic active set (D36 (5); §8).
6. Where the two representations differ in outcome, the difference is a strict red gate and a Known gap, closed in a
   named step (D36 (6); §2.3).

## 1. Landing order

- **S0 lands before `fire_solid.md` 6.0a:** a text revision of its §1.3, §2, §5.2 and §5.3 (§12), so no code ships
  that would need withdrawing from the append-only enum (D36 (4)).
- **S1–S6 follow 6.0b** (§13), each its own branch and review round, on the Phase 2 line. Read against merged PRs
  #40, #44, #45 and #46.

## 2. The representation rule

### 2.1 Geometry in whole micrometres

Every metric decision here (thickness, overlap, contact, support, gap blocking, thresholds) is made on integers.
- **The quantum:** q(v) = rint(v · 10⁶), int64 micrometres, F13's cell-edge quantum.
- **Specs are judged in their own frame,** before `imagination._offset` adds the origin. A scene's primitives are
  judged on their authored values.
- **Every threshold is held in integer micrometres** in data (§11.1).
- **Why:** in float64, `4.0 − 3.6` is `0.3999999999999999`, so the alley's north wall would be an object and its
  south wall cells. In integers both are 400,000 µm, as is every 40 cm centimetre edge (A-B1, Physics B1, T-B1).

### 2.2 The rule

For each authored primitive p, its thinnest dimension t(p) is the smallest of its edges for a box, or
min(2·r, z₁ − z₀) for an upright cylinder, in µm:

| Condition | Representation |
|---|---|
| p is a fuel entry (`fire_solid.md` §5.2) | an object, role `fuel`, at every t |
| p is `air` (a scene's carve) | cells, always |
| t(p) < `min_part_thickness_um` | refused, `out_of_range`, naming the part's index |
| `min_part_thickness_um` ≤ t(p) < `object_threshold_um` | an object, role `structure` or `inert` (§3.2) |
| t(p) ≥ `object_threshold_um` | cells (§2.4) |

- **Proposed values:**
  - `object_threshold_um` = 400,000. That is two cells of the 0.2 m coarsest verification grid, `world_model.md`
    §1.1's thin-feature bar, and the loader refuses a smaller value.
  - `min_part_thickness_um` = 3,000, which must exceed twice `contact_tolerance_um` (1,000). Then no part can lie
    inside another within the tolerance (Physics S2, Trust T-S2).
- **Per primitive, not per spec.** One spec can give cells and objects together, in one region (§4.3).
- **The shipped alley's walls and floor sit exactly on the threshold** and stay cells. Any change to the quantum is
  therefore a representation change, and S1 tests it.

### 2.3 Outcomes on both sides of the threshold

A 0.39 m part is an object and a 0.40 m part is cells. Where their laws give a different outcome class, the
difference is a Known gap with its numbers and a strict red gate, closed in a named step:

| Law | Object (< 0.4 m) | Cells (≥ 0.4 m) | Until |
|---|---|---|---|
| Heat | tile profiles (§3.3) | cell conduction, with §2.4's aliasing | same class; §2.4's gap |
| Strike | the metric sphere's share of the part (§7.1) | the same sphere on cells | same class |
| Breach | ligament in metres (§7.2) | `region_breached` (Known gap: axis from cell extents) | step 8a |
| Burning wood | burns from 6.2 (§3.2) | never (`fire_solid.md` D-S4) | the 6.2 design's wood cells |
| Load capacity | crushes, buckles, bends (§8.2) | rigid; no capacity | D22's cell capacity |
| Body contact | `sem_stimuli.md` §7.1 (§5.1) | cell faces exchange nothing in v1 | `sem_stimuli.md` §2.3's face row |
| Gap blocking | projection (§6) | face count | same class |

S1–S4 each owe the cross-threshold test for their rows: parts of 0.38, 0.40 and 0.42 m, at three grids and several
offsets (§13). A same-class row is a passing test, and every other row is a red gate whose reason names the step in
its "Until" column.

### 2.4 Cells from authored primitives

- **A cell takes a primitive's material when the primitive covers at least half of it,** with the overlap computed
  exactly on integer µm. A tie at exactly ½ assigns the cell. This replaces the cell-centre rule (`scene.py`), so it
  is a digest break, recorded under `sim_core.md` §12 with a bump of F15's `derivation_version`.
- **Mass is the authored volume's,** never the counted cells'.
- **The residual is a Known gap with its numbers.** A 0.4 m box becomes 0.4 or 0.6 m of cells at 0.2 m, 0.4 or 0.5 m
  at 0.1 m, and 0.4 or 0.45 m at 0.05 m. Heat capacity can therefore reach 1.5× the authored value, and the time for
  heat to cross can reach 2.25× (Physics S1, Architecture A-S5). It closes with B28's material fraction per cell.

## 3. One store

### 3.1 `ObjectStore`

`fire_solid.md` §1.1's `FuelStore` is renamed `ObjectStore`. The window, copy-on-first-write, key order, `pending` and
the counter are unchanged. Only the changes are listed here:

| Table | Change |
|---|---|
| `objects` | adds:<br>- `role` u8: `fuel` 0, `structure` 1, `inert` 2;<br>- `material_id` u8 for `structure` and `inert`, with the sentinel 0xFF for `fuel`;<br>- `integrity` f64 in [0, 1];<br>- `breached` u8, 0 or 1;<br>- `support` u8: `attached` 0, `loose` 1, `unstable` 2 (§8.3);<br>- `pose` f64×7: (tx, ty, tz, qw, qx, qy, qz), qw ≥ 0, zeros +0.0. It is fixed at identity until D32.<br><br>`state` numbers `live` 0, `burnt_out` 1, `failed` 2, `removed` 3. Kinds stay `rod` and `slab`: an upright cylinder is a rod with axis z, and a box is a slab with axis-aligned edges and its thinnest edge as thickness |
| `tiles` | new, for `structure` and `inert` objects. Keyed (`object_id`, `tile`): each face is cut into tiles of `tile_m` per material (§11.1), numbered in (face, length, width) order, with the area, centre and outward normal of each |
| `nodes` | for structure and inert tiles: one profile per tile across the thickness (§3.3) |
| `contact` | object-to-cell rows as `fire_solid.md` has them, extended to every role. Its derivation is §4.1's |
| `object_contact` | new, derived. Keyed (`object_a` < `object_b`, `tile_a`, `tile_b`), with the patch's polygon in µm and its area |

- **Fuel keeps its `segments`** (strips, `fire_solid.md` §1.2); a structural face is `tiles`, so no row has two
  meanings (Wire S1, A-S2).
- **Geometry stays immutable** until D32. Damage changes `integrity`, node thicknesses and the state columns, never
  geometry.
- **One mass truth:** authored volume times density, minus node losses (`fire_solid.md` §5.4). Overlap and
  containment are refused (§4.2), so no volume counts twice.
- **Ids are minted** in part order within a spec, and in entry order at scene build.
- **Limits are per role:**
  - fuel's are `fire_solid.md` §1.3's;
  - structure and inert get their own object, tile and node limits;
  - a global `object_contact` limit is added;
  - all are counted with `pending` before acceptance and refused with the `world_limit_*` family (§11.3).

  So thin structure can't exhaust fire's budget (Trust T-S5).

### 3.2 Role

- **`structure`:** a member of the statics graph (§8). It carries load and has a capacity.
- **`inert`:** it has weight and loads its supports, but it carries nothing. On a cell part, `inert` means the cells
  are a load and never a support.
- **`fuel`:** `fire_solid.md`'s. It loads its supports and carries nothing.
- **How a role is set:** a part takes `structure` unless authored `inert`. `fuel` comes only from a fuel entry, and
  `role: fuel` on a structural part is `kind_not_admitted`.
- **Burning is by material, from the 6.2 design** (D36 (7)). A structure or inert object whose material names a recipe
  in `mechanics.yaml`'s `burns_as` burns under `fire_solid.md` §4 from 6.2. Until then no structural object burns, and
  wood cells never do (§2.3).

### 3.3 Tiles and the thermal profile

- **Tiles give lateral resolution.** A 3 m rail heated at one end is hot at that end, and neighbouring tiles of one
  object exchange heat by in-plane conduction (Physics B2, Architecture A-B7).
- **Biot number:** Bi = h_ref · L_c / k. Here L_c is the tile's volume over its exposed area (r/2 for a rod), and k is
  the conductivity in `core.yaml`. `h_ref` is the material's exposure coefficient: convection plus radiation
  linearized at `t_ref_k`, both in `mechanics.yaml` with their source cited (Physics S3, N1).
- **The profile:** a tile with Bi < `lumped_biot_max` is lumped, with one node, and 1/h_node = 0 in contact (Physics
  N2). Otherwise it is 1-D across the thickness, by `fire_solid.md` §1.2's node rule, with radial metrics for a rod.
- **Glass has an edge band.** Tiles within `edge_band_um` of a pane's perimeter form its band, and §7.2's crack
  criterion reads the band against the interior (Physics B4).
- **Fixed at insertion and saved,** as `fire_solid.md` §5.5 requires: the saved layout is the truth.

## 4. Ownership and overlap

### 4.1 Objects against cells

- **An object owns no cell** (`world_model.md` §5).
- **Overlap and contact are judged against a cell region's authored geometry** (its primitives, in µm), never against
  cell faces. An object may not overlap it by more than `contact_tolerance_um`, and it touches it when the separation
  is ≤ the tolerance and the overlap exceeds it along each face axis.
- **A contact's exchange lands on the cells under the authored patch,** weighted by area, each through its skin.
- **Why:** a cell face lies up to dx/2 from the authored surface, so by cell faces a rail on a plinth was attached at
  one grid and loose at another (Physics B7). The fuel rule moves with it (§12, S0).

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
- **The whole region enters at the drain** (`fire_solid.md` §1.4). Its cell parts' paint requests and its objects are
  applied in one Topology batch, so no step sees half an object (Trust T-S7). Cell parts' occupancy is judged in µm on
  authored geometry, never on `mask & grid.solid`.
- **A region is gone** when it has no live cell and no object in state `live` or `failed`.

## 5. Coupling

### 5.1 Contact

- **Object to cell:** `fire_solid.md` §3.2's skin coupling, for every role, on §4.1's patches.
- **Object to object, one coupled solve:** the solid law (`fire_solid.md` §4, extended to every role's nodes)
  assembles each contact island, a connected set of touching objects, into one implicit system. The conductance
  1/(1/h_a + 1/h_contact + 1/h_b) is the coupling term. Each transfer is booked once, as ±H·A·(T_a − T_b)·Δt at the
  end-of-step temperatures, so it is antisymmetric and stable at any capacity ratio. Islands run in order of their
  smallest `object_id` (Physics B5: a frozen-partner Robin scheme created 95% at a 120× capacity ratio).
- **Body to object:** owned by `sem_stimuli.md` §7.1. A body reads the touched tile's surface node and writes §7.1's
  exchange field, which the solid law reads and resets like `contact_exchange`; §3.3's profile never sets the skin's
  contact temperature. Object tiles are `radiant_emitters` rows when §7.1's irradiance lands (Bio S4).
- **dx enters only through cell contact rows and the skin's far boundary.**

### 5.2 Gas: the first conflict

- **Phase 1:** `fire_solid.md` §3.1's ambient rule applies to every role. It is a Known gap extended to structure,
  with §3.1's numbers. A steel door in a burning room stays cool to the touch, a false regularity, so the gap must
  close (S5) before any NPC contact row reads an object (Bio N1).
- **When zones land (Phase 2):** each exposed tile exchanges with the gas of the zone it faces: convection, and
  radiation with the gas emissivity `epsilon_gas` (data; Physics S7). It is booked as one antisymmetric transfer to
  the zone (`object_to_zone`). This revises §3.1's "permanent for Phase 1" to "until zones land" (§12).
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
- **Blocked area is the union of the blocking objects' projections, clipped to the opening,** as exact integer µm²
  (int64). A disc projects as the regular polygon of `disc_sides` (data) whose vertices are rounded to µm, so no
  transcendental function is evaluated. The open fraction is (opening − blocked) ÷ opening, applied to `world_model.md`
  §6's integer gap area by integer floor division. It never goes negative, and nothing is clamped (Physics S8,
  Architecture A-S9, Determinism D-S5, Trust T-N2).
- **Cadence:** recomputed in each Topology batch that changes a blocking object (§7.4), and equal bit for bit to a
  full recompute.

## 7. Acts, laws and readings

### 7.1 Acts

Each act resolves in one law (`sim_core.md` §5.1). Objects take no outcome from the applier.

| Act | On an object | Resolver |
|---|---|---|
| `strike` | **The target:** the point must lie within `contact_tolerance_um` of a surface. Ties break on the smallest distance in µm, then a cell face before an object, then the smallest `object_id`.<br>**The effect:** the strike's metric damage sphere (`damage.strike`) is intersected with the part, and `integrity` falls by the destroyed share. A point off every surface is today's `not_on_surface` | a resolver module in `damage.loads`'s declared tuple, `per_record` (Architecture A-B5) |
| `kindle` | `fire_model.md` §2.2's metric nearest-surface query over cells and objects. A target that can't burn behaves as a non-burning cell surface does, with no new code | 6.4's |
| `douse` | as on cells, through the object's tiles | `fire_model.md`'s next revision (D-N3) |

`ignite` is retired by vocabulary v1 (`tile_and_client.md` §3.2) and has no row (Architecture A-B6).

### 7.2 Laws on objects

- **Strength, integrated over the section.** A member's capacity integrates its material's strength factor
  σ(T(x))/σ(T₀) over the remaining section of each tile row it bears through, and E(T) enters I for buckling. A
  minimum-node read is used only for local events such as breach (Physics B3).
- **Breach:** a tile is breached when its remaining thickness falls below `breach_ligament_um`, and the object is then
  `breached`. The loader requires `breach_ligament_um` < `min_part_thickness_um`, so nothing is breached at insertion
  (Trust T-S3).
- **Glass cracking:** a pane cracks, and is `breached`, when max over interior tiles of (T_tile − T̄_band) ≥
  `crack_delta_t_k`. This is an in-plane ΔT, the criterion of Pagni and Joshi and of Keski-Rahkonen. The binary
  outcome is band-gated with a margin in input flux (ruling 60), and its validation scatter is a Known gap. Any
  material with `crack_delta_t_k` cracks; no code keys on a material's name.
- **Destruction:** at `integrity` 0 an object becomes `removed`. Its remaining mass goes to its zone's fines species,
  or in Phase 1 to `removed_with_mass`. Fracture into new objects is out of scope (D35 (2)'s later kind).

### 7.3 Readings

- **`frames.QUANTITIES` keeps its cell meaning,** pinned by test. A mixed region reduces over its cells only.
- **An object-only region is refused by `Frame.reading` and `region_parts`,** as `fire_solid.md` §2 has it for
  fuel: never 0.0 and never NaN. So the bridge's surface, `QUANTITIES` and the affordances are unchanged (D36 (2);
  Bio B1, Wire B2). An NPC can't reach an object-only region through the bridge until the NPC fire note rules on
  objects (§9).
- **Object readings get new names on a lab surface,** under `tests/` or a lab builder, never in `QUANTITIES` or on an
  NPC builder. Examples are `object_integrity` and `object_temperature_max`. They reduce over cells by flat index,
  then objects by key, by `bincount`.

### 7.4 State changes are Topology requests

Object state transitions are keyed-table requests applied by `Topology` (`sim_core.md` §5.1). They are:
- `state` (`burnt_out`, `failed`, `removed`);
- `breached`;
- `support`.

Each batch that applies one bumps `topology_version`, so `contact`, `object_contact`, zone faces, blocked area and the
statics graph rebuild in the step the change happens (Architecture A-B4, Determinism D-B3, Wire S2). The requests are
emitted by:
- the solid law: burnt out, breached, cracked;
- `damage.loads`: removed;
- statics: failed, support.

`Topology` is the only writer of those columns, and `damage.loads` is the only writer of an object's `integrity`
after insertion.

## 8. Statics

### 8.1 The graph

- **Vertices** are every live or failed object of every role, and every cell region not anchored. Each is a rigid
  body with three degrees of freedom: a vertical translation and tilts about x and y.
- **Anchors** are the domain floor (the plane z = 0) and every cell region whose cells connect to it through cells.
  Each connected component has its own anchor, keyed by its `region_id` and its lowest flat cell index. That key only
  orders, so a split region gets two anchors (Trust T-B2, Determinism D-N3).
- **Bearing contacts carry load.** A bearing contact is a contact whose normal is within `bearing_angle_deg` of
  vertical. Its points are the vertices of its patch polygon in µm. Each point is a compression-only spring whose
  stiffness is the series axial stiffness of the two parts, E·A/L each, with the patch area shared among the points.
- **Side contacts attach but carry nothing** (D36 (1)). A part is attached if any contact, on any face, links it to
  the anchored set. Load passes only through bearing contacts. Side contacts carrying no load is a Known gap until
  joints exist.
- **Cell regions enter as loads and supports.** An unanchored cell region resting on objects is a vertex with its
  authored weight. An anchored cell region is a support (Architecture A-B3).
- **Derived,** rebuilt in each batch that changes topology, from the tables in key order, and never saved.

### 8.2 The solve

- **Per island:** each connected set of vertices that touches an anchor is one SPD system, solved by a direct
  Cholesky factorization in float64. Degrees of freedom are ordered by vertex key, then (w, θx, θy). Islands are
  ordered by their smallest key, so an unrelated object can't change a table's split (Determinism D-S1).
- **Compression only, by an active set:**
  1. Solve with every bearing point active.
  2. Deactivate every point in tension at once.
  3. Reactivate any inactive point whose gap closes.
  4. Repeat until neither step 2 nor step 3 changes anything, or `statics_max_iterations` is reached.

  The iterations are counted as work (`sim_core.md` §10). For a load over one leg of a four-legged table, this gives
  the correct lift-off, where a scalar model split the load 0.25 to each leg (Physics B6).
- **Capacity per member,** the strength-integrated section of §7.2 against these modes:
  - crushing;
  - Euler buckling π²·E·I/(K·L)², with K = `buckling_k` (data, 2.0 in v1: no joint restrains the upper bearing
    laterally; Physics S5);
  - bending between bearings, at their positions in metres.
- **Undefined results are defined outcomes.** If the system is singular (a part with no stable support), any result
  is non-finite, or the iteration cap is reached, every non-anchor vertex of that island gets `support` `unstable`. It
  is never an exception inside the step (Trust T-B4).
- **Cadence and key:** statics is a law, `per_physics_step`, after the solid law. Its key is the write ticks of every
  field it reads: node temperature and thickness, density, `integrity`, the state columns and `topology_version`. It
  reruns when any of them moves (Determinism D-B2, Physics S6). Per-member loads are derived, recomputed on load and
  never digested. The outcomes `state` and `support` are digested.
- **The solver's identity,** with the BLAS and its thread count, is part of the law's version and the log header.

### 8.3 Failure, and what waits for D32

- **A member fails** when its load exceeds its capacity, band-gated with a margin (ruling 60). Every member over
  capacity fails at once, then the island is re-solved, repeating until none fails, within the step and counted as
  work (Determinism D-S2).
- **A vertex with no contact path to an anchor becomes `loose`.** This is the only meaning "loose" has before D32
  (D33, D36 (1)).
- **Until D32,** loose and unstable parts hold in place. That is a Known gap with a strict red gate: a table whose leg
  chars through under load falls (D31's case). It is tagged ANALOG with D32 as the step that earns it. No NPC
  perception or learning bar may depend on it (D36 (7); Bio N2). `support_lost` is recorded in the `TickReport`'s lab
  section and the log, never as a `StimulusEvent` or in text an NPC can read (Bio S3).
- **Hand-off:** D32's design takes loose and unstable parts. Cells whose support fails are D22's rubble.

### 8.4 Placement (D33)

- **A spec's own parts must connect.** In the spec's own frame, with its z = 0 plane as the floor, a part with no
  contact path to the base is `parts_disconnected`, a spec fault.
- **The placement must attach.** In the world, with `pending` counted, a part with no contact path to an anchor is
  `unsupported`, a world outcome. There is no snapping: a base placed 3 mm above anything doesn't touch (Trust T-B2).
- Stability is judged after acceptance (§8.3).

## 9. Sensors and NPCs

- **NPC sensors reduce over volumes in metres** under `sem_stimuli.md`'s rows and `boundaries.md` §4.4. No sensor
  names a cell or an object.
- **The bridge is unchanged** (§7.3). The NPC fire note's trigger moves ahead of the first step that makes an
  object-only region reachable by an NPC act. That is S3, because `fire_solid.md` §7's premise (the bridge untouched)
  holds only until then (Bio B1).
- **Never perceivable,** in the class of material ids (`sem_stimuli.md` §7.4):
  - `support`, `role`, `material_id` and `breached`;
  - capacities and object `integrity`;
  - the statics graph and its outputs.

  Only a force or a temperature at a receptor's site may be perceivable (Bio S3).
- **Stage-2 refusals go through `sem_stimuli.md` §6.2's receipts.** Every target-dependent refusal this design
  produces does: `space_taken` on objects, `unsupported`, and `not_on_surface`. T11's sweep gains material and support
  categories (§12; Bio S1).
- **Weight, contact force and motion have no row yet:** a future `sem_stimuli.md` row at receptor sites, frozen with
  D32's or the body-support design, triggered by the first act or state that puts a body's weight on an object or lets
  it push or lift one. Until then it is a named perception gap. Maxim's side binds through M11, a question to GL3's
  `mechano_proprio` (Bio S2; Maxim `origin/main` b98954f7, `docs/plans/grounding.md`).

## 10. The snapshot

`client_objects.md` §3 owns the wire. This design hands it requirements in that document's grammar (Wire B1,
Architecture A-S2):
- **Fuel's tables are unchanged:** `objects`, `rods`, `slabs` and `segments`, with `state` 0 or 1. Structural objects
  never appear in them.
- **A new required table, `structures`:** keyed `object_id`, with:
  - `region_id`, and `material_id` (in `welcome`'s material map);
  - `role`, `kind`, `state` (§3.1's numbers), `breached` and `support`;
  - `integrity` (u8, linear 1/255).

  Its geometry goes in new required tables `structure_rods` and `structure_slabs`, in the fuel tables' column forms.
- **A new required table, `tiles`,** keyed (`object_id`, `tile`), with `surface_temperature_c` as f16, clipped as
  `segments` is. `welcome` carries each material's `tile_m`.
- **The protocol bumps** for the new required tables (`client_objects.md` §3.1). Frame bytes and the join cap are
  re-derived at S6 with structure's limits.
- **The presentation view:** `fire_solid.md` §5.6's `FuelFrame` becomes `ObjectFrame` (`objects_version`), with the
  same site, cadence and leak rule: presentation only.
- **Never by colour alone,** and every tier draws every live structural object, since it is gameplay geometry.

## 11. Formats

### 11.1 Data

| File | Holds |
|---|---|
| `data/world/limits.yaml` (6.0a's v0, bumped at S1) | **Thresholds:** `object_threshold_um`, `min_part_thickness_um`, `contact_tolerance_um`.<br>**Limits:** the per-role object, tile and node limits; `object_contact`; statics' `statics_max_iterations` and its island size.<br>**Cross-checks:** 2·tolerance < minimum < threshold, and threshold ≥ 400,000 |
| `data/materials/mechanics.yaml` (new, v0, `load_mechanics`, gate row) | **Per solid material, by name:** `sigma_c_pa`, `sigma_t_pa`, `e_pa`, a strength-factor table, `tile_m`, `h_ref` inputs and `t_ref_k`, `lumped_biot_max`, `breach_ligament_um`, `bearing_angle_deg`, `buckling_k`, `burns_as`, and optionally `crack_delta_t_k` with `edge_band_um`.<br>**`h_contact`,** keyed by the sorted pair `a\|b`.<br>**Global:** `contact_default`, `disc_sides`, `epsilon_gas` |

- **The loader refuses:**
  - any non-finite or non-positive physical value;
  - a strength-factor table whose temperatures don't strictly increase, or whose factors lie outside [0, 1];
  - `bearing_angle_deg` outside (0, 90);
  - a reversed or repeated pair, as `duplicate_key`.

  Each refusal has its test and gate row (Trust T-S3, T-S4; Wire S8).
- **`fire_solid.md` §5.1 owns the data-file list.** It gains `mechanics.yaml`, its header digest and the shipped-data
  test's key (§12). `FuelCatalogue` becomes `MaterialCatalogue` and checks that every material has a row and that
  `burns_as` names a known recipe.
- **Values enter tagged V, S, M or D,** and no M value enters `data/` unverified.

### 11.2 Scene and spec

- **One tagged spec format, v1, shared with fuel:** `{version: 1, name, parts}`. Each part is either:
  - a structural part, `{kind: box | cylinder, geometry, material, role?}`;
  - or a fuel entry, as `fire_solid.md` §5.2 defines it.

  `version` is `Format`'s key (`schema.read_version`). It is settled in S0, before 6.0b ships a different v1 (Wire S6,
  Architecture A-B8, Trust T-S8).
- **v0 migrates.** An unversioned `{name, primitives}` reads as v1 with every primitive a structural part and no role.
  The migration never changes geometry, so a v0 spec whose parts overlap is refused under v1's rules. The spike's
  committed specs stay readable. Stage 1 is scored under v0, as frozen, and v1 scoring is stage 2's (§12).
- **`SpecId`** (`ip_and_licensing.md` §6.1) hashes the migrated v1 form, so `version` and `role` join the hash.
- **Scene:** the next version after `main`'s when S1 lands. A primitive may carry `role: inert`. Scenes are
  repo-only, so the old version gets a bump and a refusal test.

### 11.3 Refusal codes

| Code | New? | Class | Where |
|---|---|---|---|
| `out_of_range` | no | spec fault | a part under the minimum thickness, a zero volume, or an unknown role value |
| `parts_overlap` | yes | spec fault | two of one spec's parts overlap, or one contains another |
| `parts_disconnected` | yes | spec fault | a part with no contact path to the spec's base (§8.4) |
| `kind_not_admitted` | 6.0b's | spec fault | `role: fuel` on a structural part |
| `space_taken` | no | world outcome | overlap with any existing cells or objects |
| `unsupported` | yes | world outcome | no contact path to an anchor at the placement (§8.4) |
| `outside_extent` | no | world outcome | a part outside the world, from `place` and the scorer |
| `not_on_surface` | no | world outcome | a strike point off every surface |
| `missing_mechanics` | yes | loader | a solid material without a `mechanics.yaml` row |

- **The classes are what a generator may be fed:** spec faults, with the part's index (a number the world writes);
  never world outcomes (D36 (3)). The class column belongs with `tile_and_client.md` §3.4 (§12).
- **A code is a function of authored geometry, the spec and the world in metres,** never of representation: it reads
  the same for a 0.39 m part and a 0.41 m part.
- **`too_small` is produced by nothing.** Its two producers are recoded: the cell-centre test disappears with §2.4,
  and `scene._check_volume`'s zero volume becomes `out_of_range`. An `imagine` refused as `too_small` before S1 and
  accepted after it is a replay break, recorded at S1 (Wire S3, Trust T-S6).

### 11.4 Digest, save and header

- **Digested:** every `ObjectStore` table but `contact` and `object_contact` (derived), plus `pending` and the counter.
  The new members change every tick's digest even when they are empty, because the digest hashes each member's name
  and shape (`sim_core.md` §9). That is a break, recorded at S1, with the new tables placed after fuel's in name order
  (Wire S5, Determinism D-N2).
- **Save, handed to step 9,** is `fire_solid.md` §5.5's list plus:
  - the new columns and `tiles`;
  - name maps for `material_id`, `recipe_id` and `region_id`.

  The reader refuses any of these (Trust T-N3, Wire N2):
  - a `pose` other than identity before D32;
  - an enum value outside its numbers;
  - an `integrity` that is non-finite or outside [0, 1];
  - a saved `support` or `state` that differs from the recomputed statics.
- **The log header** records `limits.yaml`, `mechanics.yaml` and the statics solver's identity (§8.2).

## 12. Revisions this design requires (proposed, not applied here)

| Document | Edit |
|---|---|
| **S0, before 6.0a:** `fire_solid.md` §1.3 | contact and overlap against authored geometry in µm (§4.1); "structural materials are cells" becomes §2.2's rule; regions may mix; per-role limits |
| **S0:** `fire_solid.md` §2 | object-only acts are refused with the existing `wrong_target` until S3 defines them, so `fuel_only_region` never ships; readings and `region_parts` keep refusing object-only regions |
| **S0:** `fire_solid.md` §5.2, §5.3 | one tagged spec v1 (§11.2); `overlaps_fuel` becomes `space_taken`; `fuel_only_region` is dropped |
| `fire_solid.md` §1.1, §1.2 | `ObjectStore`; §3.1's columns; structural `tiles` beside fuel's strips |
| `fire_solid.md` §3.1 | "permanent for Phase 1" becomes "until zones land" (§5.2); the Known gap extends to structure |
| `fire_solid.md` §4 | the solid law covers every role's nodes and object-to-object islands (§5.1) |
| `fire_solid.md` §5.1, §5.4–§5.6 | `mechanics.yaml` and `MaterialCatalogue`; the digest and save lists; `ObjectFrame` |
| `fire_solid.md` §7 | acts on objects and structural faces move from "the 6.2 design" to this design |
| `world_model.md` §1.1, and CLAUDE.md's thin-features line | thin parts are objects (§2); ruling 72 is superseded |
| `world_model.md` §2, §5, §6 | solids live in cells and objects; an object owns no cell; gap areas take §6's open fraction |
| `sim_core.md` §5, §5.1 | the statics law; `damage.loads`'s object resolver; §7.4's request kinds, and which bump `topology_version` |
| `sim_core.md` §9, §12 | the new digest members and their place; the breaks of §2.4, §11.3 and §11.4 |
| `tile_and_client.md` §3.4 | the new codes, and a class column (spec fault or world outcome) |
| `sem_stimuli.md` §6.2, §7.4, §2.2 | T11's material and support categories; the never-perceivable list (§9); the future contact-force row and its trigger |
| `fire_model.md`, its next revision | `douse` and `kindle` over objects (§7.1) |
| `client_objects.md` §3 | §10's tables, the protocol bump, and the re-derived bytes and join cap |
| `ip_and_licensing.md` §6.1; `imagination.py` (`SPEC_KEYS`, docstring); `scene.py` docstring | v1 and the migration; §2's rule; §2.4's voxelization |
| `docs/architecture.md`, Known gaps | §2.3's rows; §2.4's aliasing; side contacts; §5.2's ambient gap; §8.3's hold-in-place gap |
| The spec generator spike's stage 2 design | what v1 replaces (Trust T-N4): the instruction "may touch or overlap" becomes "may touch"; M2's connectivity becomes §8.4's; the scene places at z = 0; the A3 loop feeds back spec faults only |

## 13. Build steps, and the tests each owes

Every physics law ships with a closed-form test and a cross-grid test (§2.3's scenarios at three grids and several
offsets).

| Step | Lands | Tests |
|---|---|---|
| **S0**, before 6.0a | §12's S0 rows | the contracts lint; `fire_solid.md`'s tests unchanged |
| **S1. Representation, store, ownership** | §2, §3.1–§3.2, §4, §7.4, §11 | **red first:** the footstool, aquarium and locker specs at N sub-cell offsets and N origins × 0.2, 0.1 and 0.05 m: the same representation, codes and mass everywhere. Hypothesis: representation is a function of primitives and data, with parts exactly at each threshold; any spec and origin places or raises `SpecRejected` with an enum code, leaving the tables, `pending` and cells unchanged (Trust T-S10, B9). Every §11.3 code at its gate; the loader's cross-checks; the alley's walls stay cells |
| **S2. Thermal** | §3.3, §5.1, §5.3 | **closed forms with their boundary conditions stated:** a lumped sheet exchanging on all faces (τ ≈ 770 s at h = 25, Physics S9) and under constant flux; a rail heated at one end against 1-D lateral conduction; an island's coupled solve conserving energy at a 120× capacity ratio. The Biot choice on survey §1's cases. §2.3's heat row across the threshold. **Deferred:** Physics S4's square section against a two-sided char closed form; a miss is a Known gap with its numbers, and its fix (orthogonal profiles) changes the node limit |
| **S3. Acts, laws, readings** | §7 | strike's sphere share against cells' at the threshold; breach by ligament; glass cracking's band gate on the in-plane closed form; the `QUANTITIES` pin; object-only refusals in `Frame.reading` and `region_parts`; the never-perceivable list |
| **S4. Statics** | §8 | crushing; Euler buckling of a 1 m × 1 cm steel rod with `buckling_k`; a simply supported beam; the eccentric table's lift-off; a pine leg charred at β under load (D31); bit-identity per island against the island alone (Determinism D-S1); `unstable` on a singular island, never an exception; §8.4's codes; §8.3's red gate; a B5 budget for re-solves during a fire (Trust T-S5) |
| **S5. Zones**, with Phase 2's zones | §5.2, §6 | zone coupling's closed form; a pane at an authored interface blocking at every grid and offset, and its breach joining the zones in that step; the union against a full recompute; a double-glazed unit's blocked area ≤ the opening |
| **S6. Snapshot** | §10 | `client_objects.md` §7's goldens and measured checks for the new tables |

## 14. Open questions for the owner

1. **The minimum part thickness rises to 3 mm** (§2.2), so a 1 mm steel sheet is refused. The rule needs the
   minimum above twice the 1 mm contact tolerance. Confirm, or lower the tolerance instead.
2. **S0 edits another session's design** (`fire_solid.md`) before its step 6.0a. Who carries it: this branch, or that
   line's next branch?
