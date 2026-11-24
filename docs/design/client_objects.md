# Fuel objects on the client (design D-B2, 2026-11-21; accepted by the owner, 2026-11-22)

**Scope.** The client design pass that `fire_solid.md` §7 assigns to D-B2 ("the client design pass, before step 8";
D-B2's text is `reviews/fire_model/delta1_architecture.md`, with A-S7 in `reviews/fire_solid/architecture.md`). It
settles how the Godot client draws fire_solid's fuel objects and segments, what replaces the provisional
`surface_glow` and `burning` cell channels (B42), how crack severity shows by shape (B7, step 8 owner decision 7),
and what the measured checks and goldens become. It names every fuel field the server sends, for step 7's grammar.
Round 1's reports and the fold record are in `reviews/client_objects/`.

**What this document owns** (one owner per contract, B36): the fuel tables' wire columns (§3), the object pass's
contract (§4), the display rules for glow, burning and flames (§5), and the crack-severity rule for cells and objects
(§6). It links to the rest:
- the cell channels, the frame grammar, the send rule and the join cap: `client_rendering.md` §4;
- what each fuel quantity means, the fuel view the core publishes and its leak rule: `fire_solid.md` §5.6;
- the exit's observed beats: `tile_and_client.md` §6.3;
- the build items: `docs/plans/checklists.md` steps 7 and 8.

**Numbers** are *measured* ([ran]: Godot 4.7.2.stable.official.ed1daf0bf, Compatibility, the owner's M2), *derived*,
or `[engineering]`. The probe is `tools/godot_probes/probe_fuel_objects.gd`. The reviewers' variants of it are cited
by report. Under llvmpipe only the goldens and §7.2's checks ran.

## 0. The answers

1. **The cell channels lose `surface_glow` and `burning`.** Fuel state travels in fuel tables. Structural glow is
   drawn from `temperature_c` on solid cells only. `burning` stays a reserved name, unsent (§5.1).
2. **Objects draw in a second pass of instanced meshes, and segment state reaches the GPU as data textures.** There
   is one `MultiMesh` per geometry kind and one instance per object. The fragment shader looks up its own segment,
   and the textures upload as the bytes arrive (§4).
3. **Glow and burning change brightness, and flames add shape.** In Phase 1 the client draws a flame over each
   flaming segment, a visual effect driven by `ignited_fraction`. When Phase 2's flame object arrives, the server's
   flame table sizes it (§5).
4. **Crack severity shows as edge density, and edges only accumulate.** Isolated cracked cells and the edges of a
   cracked region show their outline. On fuel, char shows as cracks only on faces wide enough to hold them, and as
   darkening elsewhere (§6, owner rulings 1 and 2).
5. **The checks** gain burning, char, severity, isolated-cell, burn-through, stick-stability and flame-shape measures.
   The scenario goldens need their beats restated for the slab exit (§7, owner ruling 4).

## 1. What this rests on (read at main 98e2342, after #37)

| Source | What it fixes here |
|---|---|
| `docs/roadmap.md` Phase 1 exit and Phase 2 bullets; `research/solid_spike/results_rerun1.md` §7 | **the exit is the torch-lit slab** ("char, burn and flame out"); 6.2–6.4, the flame object and the crate are Phase 2 (owner, 2026-11-20) |
| `fire_solid.md` §1.1–§1.3 | the `objects` and `segments` tables; kinds `rod` and `slab`; immutable geometry; 0.02 m strip segments, two parts each; `state` live or burnt out; limits of 2,000 objects and 2×10⁴ segments; no fuel inside a solid footprint |
| `fire_solid.md` §2, §4.2, §5.6 | acts and `QUANTITIES` stay on cells; residue (char, or the inert fraction); the snapshot requirements this pass settles |
| `fire_model.md` §2.1, §4.1; `torch_pilot.md` §3 | `bed` and flames as later kinds and tables; the flame key; `kindle`'s 50 mm nearest-surface rule and `ambiguous_point` |
| `client_rendering.md` §1, §3, §4, §5, §6, §8 | camera and zoom; input; the frame, channels, bump rules and caps; the raymarch, glow curve and crack pattern; goldens and checks; budgets |
| `tile_and_client.md` §6.3 | the observed beats G2–G4 key on |
| `world_model.md` §8 (F1–F4, F15) | a name is a meaning; tables column-major with integer keys; non-default-scale fixtures |
| `sem_stimuli.md` §2.2–§2.3, §7.4; `boundaries.md` §4.4 | what an NPC may read: registered perceivable fields, never a presentation view |
| `standards_backlog.md` B5, B7, B40, B42; `reviews/step8_shader/fold.md` decisions 4, 5, 7, 9; `reviews/docs_contracts/rulings.md` rows 10, 79 | the budgets, the crack gaps, the decisions this builds on, and the two rows deferred to this pass |

## 2. What the client has to live with

| Fact | Value | Basis |
|---|---|---|
| Zoom | 30–120 px/m (720 px over 24–6 m); the golden view 72 px/m | derived, `client_rendering.md` §1 |
| A cell at 0.1 m; a segment, 0.02 m | 7.2 px at the golden view; 0.6–2.4 px along its object | derived |
| A 20 mm stick or slab edge (the exit's sticks, D-B2); a 3.2 mm dowel (R3a) | 0.6–2.4 px (1.44 at the golden view); 0.10–0.38 px | derived; `research/fire_ladder/2_flame_spread.md` |
| A slab top face, to hold 12 px polygons at the golden view | ≥ 0.17 m across | derived |
| MultiMesh custom data on Compatibility | **half float: whole numbers exact only to 2,048** | [ran], two reviewers independently (`reviews/client_objects/executor.md` E-B1, `client_rendering.md` B1) |
| `texelFetch` of R8 and RH 2-D textures; RH 3-D linear filtering | works (0.502 at a 0/1000 midpoint) | [ran] |
| The design's upload: one RH and three R8 textures, 2×10⁴ rows | 95–161 µs | [ran], `performance.md` P-N1, `executor.md` E-N2 |
| The object pass at 2,000 instances, 1 ring, golden view (two rod passes) | +0.24 ms (+0.6 ms with 4× MSAA) | [ran], `performance.md` P-S3 |
| A burnt segment drawn by a per-fragment lookup and discard | 0 px; live neighbours at full width, at any ring count | [ran], `client_rendering.md` S1 |
| Not measured | llvmpipe frame time | — |

Three consequences:
- **The raymarch can't draw fuel.** Objects sit in air cells, and the walk passes through them. Voxelising them into
  channels would make their look depend on dx (fire_model §0.3). Ray-testing them in the raymarch would need a
  per-cell object index, which costs what fire_solid §1.1's rejected per-cell CSR does (15.4–40 MB).
- **Thin fuel is drawn by a pixel rule, not its true size**, below about 2 px: every stick edge at most zooms.
- **Phase 1 has no flame object.** The slab flashes, flames and goes out in the solid model (fire_solid §4.4), so
  the only flame state on the wire is `ignited_fraction`.

## 3. The fuel tables (the wire columns)

### 3.1 Form

- **The tables travel in the cell frame,** in the grammar `client_rendering.md` §4.1 owns: column-major, an integer
  key, no strings. Each array is named `<table>.<column>`, so the five `object_id` keys are distinct.
- **dtypes:** u8, u16, u32, f16 and f32. Step 7's v0 dtype list must include u32 and f32, since `client_rendering.md` §4.1 makes a new
  dtype a protocol bump.
- **Encodings,** from the closed list step 7's registry names: `raw` for keys, ids and floats; `linear` for u8
  fractions, scale 1/255, offset 0.
- **Units,** from the closed unit vocabulary step 7's registry lists: `id`, `celsius`, `m`, `ratio`.
- **Every column below is `required`,** and so is every table. A client that can't draw fuel refuses the frame rather
  than draw a world without its fire. Unknown optional columns are ignored.
- **Versioning** is `client_rendering.md` §4.1's: a required table or a new object kind bumps the protocol, and an
  optional table, as Phase 2's `flames` will be (§3.4), bumps only the registry.
- **`welcome`** carries the recipe name↔id map and the object-kind vocabulary (`client_rendering.md` §4.1's `welcome` row). The kind ids
  are the vocabulary's; this document names only the kinds (`rod`, `slab`).
- **The quantities' meanings are `fire_solid.md` §5.6's.** The core publishes them in f64 in a fuel view that is
  never an NPC's percept. This document fixes only their wire form.

### 3.2 `objects`, `rods`, `slabs`

**`objects`**, rows sorted by `object_id`:

<!-- contract: fuel.objects.columns: object_id recipe_id region_id kind state segment_count segment_length_m -->
| Column | dtype | Unit | Encoding | Meaning |
|---|---|---|---|---|
| `object_id` | u32 | id | raw | key, never reused (fire_solid §1.1) |
| `recipe_id` | u16 | id | raw | id in `welcome`'s recipe map |
| `region_id` | u16 | id | raw | the object's region, the same ids as the `region` channel |
| `kind` | u8 | id | raw | id in `welcome`'s kind vocabulary |
| `state` | u8 | id | raw | 0 live, 1 burnt out |
| `segment_count` | u16 | id | raw | its rows in `segments` |
| `segment_length_m` | f32 | m | raw | ℓ: segment k spans [kℓ, min((k+1)ℓ, L)) from the origin along the axis (rod) or length axis (slab), with L the length |

**`rods`**, keyed by `object_id`, one row per rod: `origin_{x,y,z}_m` (the axis's start, where segment 0 begins),
`axis_{x,y,z}` (unit, `ratio`), `length_m`, `radius_m`. All are f32 in world metres, in the server's frame. The
span and the origin are fire_solid §1.1–§1.2's.

**`slabs`**, keyed by `object_id`: `origin_{x,y,z}_m` (a corner), `length_axis_{x,y,z}`, `width_axis_{x,y,z}`,
`length_m`, `width_m`, `thickness_m`, all f32. The segmented face is fire_solid §1.1's.

A table per kind, not one of positional columns, keeps each column's meaning (F1): a new kind is a new table and mesh.

**The decoder's checks** run when the structure differs from the last frame drawn: every `objects` column but `state`,
the geometry tables, `segments`' keys, the row counts, the vocabularies and the region map. In a steady burn: insertions
only. Every frame, the other columns are held to their row counts, `state` to 0 or 1 and `surface_temperature_c`
to §3.3's clip (ruling 9). A refused frame draws nothing new. The decoder refuses on any of these:
- row counts past fire_solid §1.3's limits; a kind or recipe id shared or outside its dtype;
- an unknown kind, recipe or region; `object_id`s not strictly rising;
- a `segment_count` of 0, Σ `segment_count` ≠ the `segments` rows, or key bytes ≠ the keys the objects imply;
- a geometry row missing, or present in another kind's table;
- non-finite geometry, a non-positive size, an axis off unit or slab axes off square by more than 10⁻⁶ `[engineering]`;
- from step 7, geometry outside the world: the cell snapshot's extent (fire_solid §1.3);
- a surface temperature NaN, infinite or outside §3.3's clip.

The client never recounts segments from geometry. `segment_count` is the server's, its rule fire_solid §1.2's. A recount from f32 columns disagrees with any rule for some lengths: 42 of 1,981 at an absolute tolerance
(`delta1_wire_integrity.md` N1). The key check catches a misdistributed count, and §4.1's clamp keeps every fragment on
its own object.

### 3.3 `segments`

Keyed by (`object_id`, `seg`), sorted, with one object's segments contiguous in `seg` order:

<!-- contract: fuel.segments.columns: object_id seg surface_temperature_c ignited_fraction thickness_fraction char_fraction -->
| Column | dtype | Unit | Encoding | Quantity (fire_solid §5.6 defines it) |
|---|---|---|---|---|
| `object_id` | u32 | id | raw | key |
| `seg` | u16 | id | raw | key |
| `surface_temperature_c` | f16 | celsius | raw, clipped to [−273, 6000] | the segment's radiance-equivalent surface temperature |
| `ignited_fraction` | u8 | ratio | linear 1/255 | the ignited part's share of the segment's area |
| `thickness_fraction` | u8 | ratio | linear 1/255 | remaining thickness ÷ initial; 0 when burnt through |
| `char_fraction` | u8 | ratio | linear 1/255 | residue's share of the segment's remaining solid mass; 0 when none remains |

- **The radiance-equivalent temperature** is exact for glow only while one part has area, as in 6.1.
- **u8 fractions** resolve a change of 1/255, below a pixel at every zoom. Rounding is to nearest.
- **`burning`**, the old per-cell burning fraction, is `ignited_fraction`'s job now, per segment. The name stays
  reserved.

### 3.4 Phase 2's `flames` table

The flame object is Phase 2's (6.2), so step 7's v0 carries no `flames` table. When it comes, it is optional, and a
client without it keeps drawing §5.3's Phase 1 flames. The client needs at least these columns: the key (fire_model
§4.1's minimum member key), the flame's base box and its height and width in metres, and its heat release. 6.2's
design owns the columns; this document is their consumer. The join cap then counts it too (`client_rendering.md`
§4.3).

### 3.5 Frame bytes

Six bytes per cell remain (`client_rendering.md` §4.2), and the fuel tables add these per row: `objects` 16, `rods`
36, `slabs` 52 and `segments` 11.

At the world limits the tables add 356,000 B. At the tile (230,400 cells) a frame is then 1,738,400 B plus headers.
The join cap counts the tables at the limits (`client_rendering.md` §4.3), which admits up to 552,336 cells under 3.5 MiB (derived,
`performance.md` P-S4). The header bound grows with the registry's column count (P-N2).

## 4. The object pass

### 4.1 Instanced meshes, data textures

- **One `MultiMeshInstance3D` per kind,** under a `Fuel` node beside `CellVolume`. Each object is one instance: a
  low-poly unit cylinder or box, with its transform built from the object's geometry row.
  - Engine why: a MultiMesh draws every instance in one draw call. A node per object would be 2,000 nodes and 2,000
    draw calls.
  - Transforms are built through `IsoCamera.to_godot`, the one mapping (`client_rendering.md` §4.1), so the
    MultiMesh's culling box is in Godot's frame where the objects are.
- **No index travels in custom data.** On Compatibility custom data is half float (§2), so an object's first segment
  row is read from a per-instance texture indexed by `INSTANCE_ID`.
  - That texture holds three RGBA8 texels per instance, all exact: the first row's three bytes and the recipe's palette
    slot (slot 15 is magenta, never a recipe's); `segment_count` and the object's row; ℓ's f32 bits.
  - `state` is its own R8 texture by object row, so a burnout never rebuilds.
- **The rebuild is rare:** only when §3.2's structure changes, so on insertion only. At the limits (M2, headless,
  `tools/fuel_aa/rebuild_time.gd`): an insertion, check included, 14.1–14.5 ms before ruling 9's temperature loop
  (18.7–21.0 ms after, loaded); a steady frame 1.80–1.83 ms, nearly all that loop (0.10 ms without it).
- **Segment state uploads on every cell-frame message (2 Hz), itself without a loop.** Each segment column becomes a 2-D
  texture 256 texels wide, with row i at (i mod 256, i div 256), padded by a resize: RH for `surface_temperature_c`,
  R8 for each u8 column.
  - The bytes go to `Image.create_from_data` unchanged: 95–161 µs at the limits (§2).
  - One instance per segment would cost 4.4–6.9 ms in GDScript (§2's probe and its reruns), more than
    `client_rendering.md` §8's whole 3 ms budget, which B5 already records as broken.
- **Each fragment finds its own segment:** k = clamp(⌊s/ℓ⌋, 0, `segment_count` − 1), with s the fragment's distance
  along the axis, carried in a smooth varying. The clamp keeps an end cap at s = L on its own object.
- **Depth, cut-away and colour:**
  - Depth: an ordinary depth test against the raymarch's written `DEPTH`, as bodies already do.
  - Cut-away: objects are never cut, because fuel never sits in a wall (fire_solid §1.3).
  - Colour: albedo comes from client data keyed by recipe name. A recipe without a colour, or past the palette, is
    reported and drawn magenta.

### 4.2 Shape: burn-away and the pixel floor

- **Burn-away is shape, at segment granularity.** A segment with `thickness_fraction` 0 draws no pixel within its
  axial span, and its live neighbours draw at full width up to their boundary.
  - Drawn thickness is monotone in `thickness_fraction`.
  - Pine chars rather than regresses (fire_solid §4.3), so in the Phase 1 exit this mostly shows at burnout.
  - It is decided per fragment. A per-vertex lookup tapers across shared rings and loses segments that hold no vertex
    (`client_rendering.md` S1, `executor.md` E-S3).
- **The floor:** a live segment is never drawn narrower than **2 output pixels** across its silhouette at any tier.
  - On the laptop tier (render scale 0.5) that is one rendered pixel.
  - It needs an output-pixel quantity beside `pixel_m`, which is per rendered pixel.
  - On a slanted slab it applies to the projected thickness, not the world thickness.
  - One floor in output pixels keeps the tiers' fuel ID masks comparable (§7.2).
- **What the floor costs:** below it, apparent width carries no information. An edge or stick narrower than 2 px
  shows its state through brightness (§5), gaps (above) and darkening (§6.3).
- **Anti-aliasing is part of the contract:** a stick's drawn coverage must be stable along its length and under
  sub-pixel camera motion, by §7.2's measure. Rods use analytic edge coverage, one rendered pixel wide (owner ruling 3,
  measured in `research/fuel_antialiasing.md`): it holds the bar on every tier, where MSAA fails the laptop tier.
  Slab edges have none yet (that record's open item 2). Rods draw depth alone over the silhouette (coverage ≥ 0.5),
  then every rod's colour core, then every rod's fade, blended by coverage: crossing sticks occlude by depth on every
  tier, and a front fade lands on a rear rod in any order unless rods touch or fades overlap (ruling 7).

### 4.3 Picking and interaction

- **`F` on a fuel surface** (`client_rendering.md` §3) sends the raw hit point, in mm, on the drawn surface.
  - The pick tests objects analytically against the drawn, floored geometry, and the burnt gaps aren't hittable.
  - The nearer of the cell hit and the object hit wins.
  - It never snaps to an object. Target derivation, `ambiguous_point` included, stays the server's shared validator's
    (fire_model §5.4), so a player's `kindle` and an NPC's are the same act.
  - The floor offsets a hit by at most 1 output pixel, 33 mm at 30 px/m. That is inside the server's 50 mm
    nearest-surface reach (derived).
- **The hover outline** is drawn on the object's region (`region_id`).
- **Interpolation** (`client_rendering.md` §3.1): a cross-fade of `surface_temperature_c` and `temperature_c` is
  visual only, and skipped on a frame whose key bytes changed. Geometry never interpolates.
- **A burnt-out object** (`state` 1) draws its remaining segments, which are char, without glow or flame.

## 5. Glow, burning and flames: never by colour alone

### 5.1 Structural glow from `temperature_c`

- **The input is the cell mean, on solid cells only.** `surface_glow` was meant to be the face's skin temperature,
  which nothing computes (skins exist only on contact faces, fire_solid §3.2). Today's encoder sends the masked cell
  mean as `glow`.
  - The client masks `temperature_c` by `material` ≠ air.
  - Its linear filter blends only solid neighbours.
  - So hot air never lights a wall's edge, as today's mask guarantees.
- **The glow curve is unchanged** (`client_rendering.md` §5.3: gain 7, start 525 °C). Its start becomes a client
  constant, and `encoding.GLOW_START_C`, `GLOW_FULL_C` and the `glow` key are deleted with step 7's encoder.
- **Known gap:** a face being heated is hotter than its cell's mean, so structural glow comes on late and dim.
  - Steady bound: the mean lags the face by up to q·(dx/2)/k, 29 K per kW/m² for the shipped concrete (k = 1.7
    W/m·K) in a 0.1 m cell: hundreds of kelvin at fire fluxes, so a bound, not a correction. A transient lag is less.
  - It is in `docs/known_gaps.md` (owner, 2026-11-22); today's encoder already has it.
  - A face-temperature input would come from world_model §8's face table under its own name, if Phase 2 builds skins
    on every structural face.

### 5.2 Fuel surfaces

- **Glow:** the same curve, on `surface_temperature_c`. Emission is HDR and drives bloom above 1.0, so glow changes
  brightness. The laptop tier's flat white band above about 1,230 °C stays (B7).
- **Burning:** `ignited_fraction` adds an emissive flame-lit term scaled by the fraction, so a flaming surface is
  brighter than a hot one at the same temperature. That is brightness, not hue (checked in §7.2).
- **Char:** `char_fraction` darkens the albedo, a luminance change (checked in §7.2), and drives cracks where a face
  can hold them (§6.3).

### 5.3 Flames

- **Phase 1: a client-drawn flame over each flaming segment.** It is an additive, camera-facing volume rising from
  the segment, its intensity scaled by `ignited_fraction`, at a stylised height `[engineering]` (0.1–0.3 m, the range
  fire_model §4.1 gives starter flames). It is a purely visual effect from a snapshot column (CLAUDE.md, "may add
  purely visual effects"), drawn after opaque geometry. Goldens draw it with flicker off, so §7.2 can measure it.
  - Engine why: a flame is gas with no surface for either pass to hit, so it is drawn as an emissive volume over them.
- **Phase 2:** the `flames` table (§3.4) sizes each flame, replacing the stylised height.
- **Never by colour alone:** a flame adds pixels where nothing was drawn (shape), and brightness over them.
- **Cost:** one quad per segment row, collapsed to zero area unless its segment flames, so only flaming segments
  cost fill. A burnt-out object or a burnt-through segment raises none. The flame pass is a frame-time row
  (§7.4); Phase 2's design states a cluster bound against it (`performance.md` P-S6).

### 5.4 What the player sees that no NPC senses

The player sees four cues that no stimulus row carries:
- burning brightness from the solid model's ignition latch;
- char darkening from a residue fraction;
- the Phase 1 flame, drawn from `ignited_fraction`;
- the torch's flame (`torch_pilot.md` §8).

An NPC's future sight row is radiance from surface temperatures only (`sem_stimuli.md` §2.2). So a cold charred
stick, or a just-ignited one, looks the same to an NPC as unburnt wood at that temperature. These are named
divergences, OPEN against OD-C8 (`docs/roadmap.md`). The NPC fire note decides whether sight needs an albedo or flame
channel. Until then, a perception bar about "seeing the fire burn" must cite this section, so a miss isn't read as
Maxim's.

## 6. Crack severity by shape

### 6.1 The rule (cells' `crack`, segments' `char_fraction`)

This replaces the severity half of `client_rendering.md` §5.4 and carries out step 8 owner decision 7:
1. **Monotone:** drawn edge density per unit of cracked area never falls as severity rises. It rises by at least one
   step in each of the bands (0, ¼], (¼, ½], (½, ¾] and (¾, 1], at every tier.
2. **Additive within a cell:** a pattern edge drawn at a cell's severity c is drawn at every c′ > c. The pattern only
   gains edges as the cell's damage grows, and never swims.
3. **Outlines:** a cell with c ≥ 1/8 `[engineering]` shows a groove along each face edge it shares with a cell below
   1/8, so an isolated cracked cell is always visible. Outlines follow the cracked region's edge as damage spreads:
   the crack front moving, not swimming. Below 1/8, damage shows by darkening alone, so scattered slight damage draws
   no grid.
4. **The floors hold** (`client_rendering.md` §5.4, decision 4). Milder severities draw coarser octaves of one
   pattern.

Rule 3 is narrower than decision 7's "every cracked cell is guaranteed an edge". At the golden view a cell is
7.2 px, so an edge in every cell of a region would draw polygons of about 7 px, which breaks decision 4. In the
reviewer's estimate it would also make mild damage the densest (`client_rendering.md` S3). Decisions 4 and 7
conflict at cell pitch; rule 3 is the recommendation in owner ruling 2.

### 6.2 Why severity can't stay in groove width

Under the shader branch's width law, at the golden view, on a face square to the ray, the metre term's half-width is 0.02 m × c × 72 px/m = 1.44c px. So
the 0.75 px floor decides every groove below c ≈ 0.52 (derived). On slanted faces the floor is divided by the cosine
and decides more. B7 measured c = 0.25–0.96 drawing the same grooves on rig walls, and none on the laptop.

### 6.3 Char on fuel

- **Faces at least 12 px across** carry §6.1, with `char_fraction` as severity and the pattern in object coordinates:
  a slab's top face at the golden view when it is ≥ 0.17 m wide.
- **Narrower faces** (stick and slab edges, and small faces at low zoom) can't hold a 12 px polygon. Their char shows
  as darkening, and their burn-away as gaps. Both are measured (§7.2), but neither is a crack (owner ruling 1).

## 7. Checks and goldens

### 7.1 Renderer goldens (hand-built fixtures)

- **A fuel fixture,** whose segments are numbered past 2,048 rows before its visible objects:
  - rods of radius 10, 50 and 100 mm, and a slab with a top face ≥ 0.17 m;
  - segments with a temperature ramp to 1,500 °C;
  - ignited runs at 600 °C, below the laptop's white band;
  - a run with `thickness_fraction` 0, a char ramp, a burnt-out object still hot and ignited, an ignited burnt-through
    run, and a hot stick across a cold log.
- **A crack-severity fixture:** one block per band of §6.1, plus isolated cracked cells in each.
- **The fire fixture:**
  - its hand-placed `surface_glow` and `burning` give way to the fuel fixture's tables;
  - its structural glow is drawn from masked `temperature_c`;
  - its `crack` is written at a non-default scale, so a decoder that hard-codes 1/255 fails (world_model §8, F7).

### 7.2 Measured checks (`scripts/golden_measures.py`, `golden_fuel.py`, `golden_stability.py`; each proved by deletion)

| Check | Bar | Deletion that must fail it |
|---|---|---|
| Glow (kept), mask from both passes' debug views | ≥ 15 L* brighter | zero the emission |
| **Burning**, flames off | ignited segments ≥ 15 L* brighter than unignited ones at the same temperature, at every tier `[engineering, as glow]` | drop the ignited term |
| **Char darkening** | charred segments ≥ 8 L* darker than uncharred ones at the same temperature `[engineering, as crack]` | ignore `char_fraction` |
| Crack (kept), cracked cells and charred faces ≥ 12 px | mean \|ΔL*\| ≥ 8 and ≥ 2× edge density | carving off, darkening kept |
| **Severity** | edge density rises by at least one step per band, at every tier | one octave for every severity |
| **Outlines** | every isolated cracked cell has groove pixels on each of its exposed edges | outlines removed |
| **Burn-through** | zero fuel-ID pixels inside the burnt run's axial footprint, shrunk at each end by its projected radius; every live segment farther than that radius from the run's ends draws, each run of them at its drawn width less 1 px | thickness ignored; rods narrowed |
| **Stick stability** | the per-bin coverage spread, under 8 sub-pixel camera offsets, within a margin of an ideal anti-aliased line; its area within half sRGB's excess of the drawn width | anti-aliasing off; coverage gamma-encoded |
| **Flame shape** | flame-ID pixels above the flaming segments > 0, and ≥ 15 L* over them | flames off, emission kept |
| **Burnout** | burnt out: < 15 L* above cold char, flames off; no flame-ID pixel near it or a burnt-through run | ignore `state`; ungate flames |
| **Crossing** | a stick over a log drawn later, and one resting on a plank that faces the camera, ≥ 15 L* above what is under it; on rig and max, the stick's outer fade over the log ≥ 1/14 of its gain, in linear light (ruling 8) | depth from the blended pass alone; core and fade in one pass; symmetric slab growth |
| **Update** | a steady frame's new segment state shows (glow, ≥ 15 L*) | in-place upload skipped |
| Tier agreement | each object's fuel-ID area, as summed coverage within one laptop pixel of the drawn edge, within 15% of rig's | floor in rendered pixels |
| Speckle (kept) | extended to the fuel fixture's cold frame | an isolated-pixel defect planted in the fixture |

- **The stability measure** integrates coverage over axial bins 4 px wide and compares each bin across sub-pixel
  camera offsets: crawl under motion.
- **Its margin** comes from an ideal line's spread over the same offsets, computed in numpy at exact coverage. The
  parameters and zooms are step 8's checklist's, fixed before measuring.
- The masks come from the shaders' debug passes: a fuel-ID view, a flame-ID view and a groove view. Their coverage is
  linear (measured on rig and laptop), so summed coverage is area.

### 7.3 Scenario goldens

G1–G5's names stay. Their beats (tile §6.3: `t_crack`, `t_glow`, `t_gone`) are written for the Phase 2 crate. They
read bed cells and an envelope skin that the slab exit doesn't have. For the torch-lit
slab the beats are `torch_pilot.md` §9's, on logged server state, and step 8 maps G1–G5 onto them.

### 7.4 Budgets (`client_rendering.md` §8)

- **Decode-and-upload** gains a steady fuel frame, and the **rebuild** is a reported row: both measured in §4.1.
- **Frame time** at the golden view includes the object pass, the rod passes and the flames
  (`research/fuel_antialiasing.md`).
- **Server side:** the fuel view's reductions get a B5 row: a stand-in measured 13.3 ms at the limits on a loaded
  machine (`performance.md` P-S5). Computed on the encoder's request and cached (fire_solid §5.6), they cost at most
  one reduction per frame sent, outside the solid's 25 ms step, and nothing in headless runs.

## 8. What this pass changes elsewhere

| Document | Change |
|---|---|
| `client_rendering.md` | §4.1: the `welcome` row's kind vocabulary, the send rule's fuel version; §4.2: the channel rows and frame bytes; §4.3: the join cap counts the fuel tables; §3.1, §5.1, §5.3–§5.6, §6.1–§6.4, §8, §12: links here |
| `fire_solid.md` | §5.6: the fuel view's quantities, site, cadence and leak rule; §7: the D-B2 row, D-S2's trigger, the view's placement |
| `fire_model.md` §9.2; `tile_and_client.md` §5.5 | the superseded `segment_glow`, `burning` and bed `crack` meanings become links (docs-contracts row 79) |
| `docs/plans/checklists.md` steps 6–8; `foundations_plan.md` rows 7–8 | the build items and fire_solid's questions; step 7 after 6.0b; step 8 sized |
| `client/tests/fixtures/snapshots/FIELDS.md` | the retired rows and the glow calibration go; the fuel tables listed |
| `docs/standards_backlog.md` | B42 stays open until step 7's decoder deletes the provisional reads; B7 names §6; B5 gains the fuel rows; B40 (2) names the flame pass |
| `docs/architecture.md`, `docs/roadmap.md` | the `glow` channel's mentions link to the owners |
| `docs/design/contracts.md` | the snapshot channels and the fuel tables' columns registered |
| `docs/lessons_maxim_in_games.md` | lesson 34 |

## 9. Owner rulings

The five rulings of 2026-11-22, numbered as cited here and in the code ("owner ruling 3"), are recorded in
`reviews/client_objects/owner_rulings.md`; each one's effect is stated in the section it names.

## 10. Not settled here

| Item | Owner, trigger |
|---|---|
| A flame's look beyond shape and brightness; a bed's slats; where a segment's ignited part lies | the 6.2 design (Phase 2) |
| Delta frames | world_v2's reserved `kind: delta`, unscheduled |
| Any NPC read of fuel; sight parity (§5.4) | the NPC fire note, before vocabulary v1 (fire_solid §7) |
