# Fuel objects on the client (design D-B2, 2026-11-21, for review)

**Scope.** The client design pass that `fire_solid.md` §7 assigns to D-B2 ("the client design pass, before step 8";
D-B2's text is `reviews/fire_model/delta1_architecture.md`, with A-S7 in `reviews/fire_solid/architecture.md`). It
settles how the Godot client draws fire_solid's fuel objects and segments, what replaces the provisional
`surface_glow` and `burning` cell channels (B42), how crack severity shows by shape (B7, step 8 owner decision 7),
and what the measured checks and goldens become. It names every field the server sends for fuel, for step 7's
grammar.

**What this document owns** (one owner per contract, B36): the fuel tables on the wire (§3), the object pass's
contract (§4), the display rules for glow, burning and flames (§5), and the crack-severity rule for cells and objects
(§6). The cell channels stay `client_rendering.md` §4.2's, the frame grammar §4.1's and world_v2 §8's, the physics
of every quantity fire_solid's or 6.2's.

**Numbers** are *measured* ([ran]: Godot 4.7.2.stable.official.ed1daf0bf, Compatibility, the owner's M2), *derived*,
or `[engineering]`. The probe is `tools/godot_probes/probe_fuel_objects.gd`; it has not run under llvmpipe.

## 0. The answers

1. **The cell channels lose `surface_glow` and `burning`.** Fuel state travels in fuel tables. Structural glow is
   drawn from `temperature_c`, which the frame already carries. `burning` stays a reserved name, unsent (§3.5, §5.1).
2. **Segment state reaches the GPU as data textures, and objects draw in a second pass of instanced meshes.** One
   `MultiMesh` per geometry kind, one instance per object, rebuilt only when the object set changes. Each segment
   column uploads as it arrives, with no GDScript loop, and the shaders read it by row (§4).
3. **Glow changes brightness, burning adds brightness, flames add shape.** A flame is a volume drawn from the server's
   flame table, so the fire's silhouette changes, not only its colour (§5).
4. **Crack severity shows by edge density.** The pattern only gains edges as severity rises, and every cracked cell
   shows a groove. On fuel, char severity draws as cracks only where a face is wide enough to hold them; thinner
   fuel shows char by darkening and burn-through by gaps (§6, owner question 1).
5. **The checks** gain severity, isolated-cell, burn-through, stick-stability and flame-shape measures. The scenario
   goldens keep tile §6.3's beats (§7).

## 1. What this rests on (read at main 2e67af2)

| Source | What it fixes here |
|---|---|
| `fire_solid.md` §1.1–§1.2 | the `objects` and `segments` tables, kinds `rod` and `slab`, immutable geometry, 0.02 m strip segments, two parts per segment, node thickness regression, `state` live or burnt out |
| `fire_solid.md` §1.3 | world limits: 2,000 objects, 2×10⁴ segments; no fuel inside a solid footprint |
| `fire_solid.md` §2, §5.6 | acts and `QUANTITIES` stay on cells; the column list this document takes over; `burning` reserved; names superseding fire_model §9.2's |
| `fire_model.md` §2.1, §4.1, §7, §9.2 | `bed` arrives in 6.2; flames are stateless per cluster, keyed by the minimum member key, sized by the server; the exit's starter, sticks and crate |
| `client_rendering.md` §1, §3.1, §4, §5, §6, §8 | the camera and zoom; what the client may do; the frame and channels; the raymarch, glow curve and crack pattern; goldens and checks; budgets |
| `tile_and_client.md` §6.3 | the observed beats `t_crack`, `t_glow`, `t_gone` that G2–G4 key on |
| `world_model.md` §8 (F1–F4), `world_v2.md` §8 | a name is a meaning; tables column-major with integer keys and no strings; required and optional; what bumps what |
| `boundaries.md` §8.3 | display quantization is presentation only and lives in the protocol layer |
| `standards_backlog.md` B5, B7, B40, B42 | the upload budget broken by GDScript loops; the crack gaps; unbuilt flames; the provisional channels |
| `reviews/step8_shader/fold.md` decisions 4, 5, 7, 9 | polygons ~12 px; glow gain 7; severity by polygon density with an edge in every cracked cell; the fire channels conflict |
| `reviews/docs_contracts/rulings.md` rows 10, 79 | deferred to this pass; `crack` keeps one meaning |

## 2. What the client has to live with

| Fact | Value | Basis |
|---|---|---|
| Zoom | 30–120 px/m (720 px over 24–6 m); the golden view 72 px/m | derived, `client_rendering.md` §1 |
| A cell at 0.1 m | 7.2 px at the golden view | derived |
| R3's sticks, 7.5–15 mm | 0.23–1.8 px across the zoom range; 0.54–1.08 px at the golden view | derived, `fire_model.md` §5.4 |
| A segment, 0.02 m | 0.6–2.4 px along its object | derived |
| A 20 mm rod, no anti-aliasing | drawn 1–3 px wide; coverage along it varies by 38% (a 0.2 m rod: 4.8%) | [ran] |
| The same with 4× MSAA, and with MSAA plus a 2 px floor | 27%, 23% | [ran] |
| Building 2,000 / 2×10⁴ instances in GDScript | 0.46–0.57 ms / 4.4–5.8 ms | [ran], minimum of 50, two runs |
| Uploading 2×10⁴ segment rows (one RH and one RGBA8 texture) | 45–54 µs | [ran], minimum of 50, two runs |
| MultiMesh custom data; `texelFetch` of R8 and RH 2-D textures in vertex and fragment; RH 3-D linear filtering (0.502 at a 0/1000 midpoint) | all work on Compatibility | [ran] |
| What the probe did not measure | shimmer under camera motion (one static frame), llvmpipe, frame time | — |

Three consequences:
- **The raymarch can't draw fuel.** Objects sit in air cells, and the walk passes through them (D-B2).
  Voxelising them into channels would make their look depend on dx, which fire_model §0.3 forbids. Ray-testing
  objects in the raymarch would need per-cell object lists, which fire_solid §1.1 rejected (15.4–40 MB).
- **Thin fuel is narrower than a pixel at every zoom.** A stick is drawn by a pixel-width rule, not by its true size.
- **No in-world fire exists before 6.4.** A segment flashes only with a pilot, and the only in-world pilot is
  `kindle` (6.4). Flames exist from 6.2, and step 8 follows 6.4 (fire_model §10.2), so step 8 draws all of it.

## 3. The fuel tables (the wire contract)

### 3.1 Form

- **The tables travel in the cell frame**, beside its grids and channels, as world_v2 §8 and `client_rendering.md`
  §4.1 describe: column-major, an integer key, no strings (F2–F4). Each column has its dtype, its unit from the
  closed vocabulary and, for integer encodings, `scale_num` and `scale_den`, in the catalogue `welcome` sends.
- **Every fuel table is `required`.** A client that can't draw fuel refuses the frame loudly rather than draw a world
  without its fire. `objects`, `segments`, `rods` and `slabs` join the registry with 6.0b; `flames` with 6.2; each
  addition bumps the registry version, not the protocol (world_v2 §8).
- **Columns can be added** without a bump to the tables' meaning (fire_solid §5.6): an unknown optional column is
  ignored.
- **`welcome`** carries the recipe name↔id map and the object-kind vocabulary (`rod` 0, `slab` 1; `bed` is 6.2's).
- **A frame is sent** when the cells' version or any fuel table changes, at most `snapshot_hz`. A warm object changes
  every 0.5 s physics step, so fuel cooling after a fire keeps the 2 Hz cadence.
- **Presentation only** (boundaries §8.3). The core publishes the per-segment reductions of §3.3 on the frame, in f64,
  as `bincount` reductions in key order (fire_solid §5.4). The protocol layer quantizes them. Whether SEM ever reads
  the frame's fuel view is the NPC fire note's decision (fire_solid §7); `QUANTITIES` is untouched.

### 3.2 `objects`, `rods`, `slabs`

**`objects`**, keyed by `object_id`, rows sorted by it:

| Column | dtype | Unit | Meaning |
|---|---|---|---|
| `object_id` | u32 | 1 | key, never reused (fire_solid §1.1) |
| `recipe_id` | u16 | 1 | id in `welcome`'s recipe map |
| `region_id` | u16 | 1 | the object's region (fire_solid §1.3), the same ids as the `region` channel |
| `kind` | u8 | 1 | id in `welcome`'s kind vocabulary |
| `state` | u8 | 1 | 0 live, 1 burnt out (fire_solid §1.1) |
| `segment_count` | u16 | 1 | its rows in `segments` |
| `segment_length_m` | f32 | m | ℓ: segment k spans [kℓ, min((k+1)ℓ, L)) from the origin along the axis (rod) or length axis (slab), L the length |

**`rods`**, keyed by `object_id`, one row per rod: `origin_{x,y,z}_m` (the axis's start, from which segments count),
`axis_{x,y,z}` (unit, dimensionless), `length_m`, `radius_m`, all f32 in world metres.

**`slabs`**, keyed by `object_id`: `origin_{x,y,z}_m` (a corner), `length_axis_{x,y,z}`, `width_axis_{x,y,z}`,
`length_m`, `width_m`, `thickness_m`, all f32. The segmented face is fire_solid's to state (question F2 in §9).

Per-kind geometry tables rather than one table of positional columns: each column then has one meaning (F1), and a
new kind (6.2's `bed`) is a new table and a new mesh, never a reinterpretation of old columns.

**Checks the decoder runs**, refusing the frame on any: kinds, recipes and regions known; Σ `segment_count` equals
the `segments` rows; each object's geometry row present in exactly its kind's table; finite geometry, positive
lengths, unit axes within 10⁻⁶ `[engineering]`; `segments`' key column equal to the one the objects imply.

### 3.3 `segments`

Keyed by (`object_id`, `seg`), rows sorted by key, one object's segments contiguous in `seg` order:

| Column | dtype | Unit | Encoding | Meaning (the core's reduction over the segment's parts p with area a_p > 0) |
|---|---|---|---|---|
| `object_id` | u32 | 1 | — | key |
| `seg` | u16 | 1 | — | key |
| `surface_temperature_c` | f16 | °C | clipped to [−273, 6000] | the radiance-equivalent surface temperature (Σ a_p T_p⁴ / Σ a_p)^¼, in kelvin, of each part's surface node, then in °C |
| `ignited_fraction` | u8 | 1 | 1/255 | the ignited part's area ÷ the segment's area |
| `thickness_fraction` | u8 | 1 | 1/255 | Σ_p a_p·(its nodes' thickness) ÷ (the segment's area × its initial thickness); 0 when burnt through |
| `char_fraction` | u8 | 1 | 1/255 | residue mass (char, or the set's inert fraction; fire_solid §4.2) ÷ the segment's solid mass |

- **Why radiance-equivalent and not the area mean.** Glow goes as T⁴. When a segment is part-ignited, the mean
  temperature of its parts glows dimmer than the parts do. CLAUDE.md's rule applies: evaluate the law per part, then
  integrate. In 6.1 a segment flips whole, so one part has area and the column is that part's temperature.
- **u8 for fractions:** 1/255 resolves a front moving over one segment in 255 steps, below a pixel at every zoom.
  The rounding is to nearest.
- **The previous `burning`** (the burning fraction of a cell's fuel surface) is `ignited_fraction`'s job now, per
  segment. The name `burning` stays reserved (fire_solid §5.6).

### 3.4 `flames` (with 6.2)

Keyed by the cluster's minimum member key (`object_id` u32, `seg` u16; fire_model §4.1). The client needs:
`base_min_{x,y,z}_m` and `base_max_{x,y,z}_m`, the axis-aligned box of the member segments; `height_m`, the flame's
height above the box's top; `heat_release_kw`. All f32. 6.2's design owns each quantity's physics and may add
columns; the client draws what these four give (§5.3). Flames are derived (F15), so the table is never saved.

### 3.5 Cell channels after this pass

`client_rendering.md` §4.2 keeps `material`, `region`, `crack` (1 − integrity only; docs-contracts row 79) and
`temperature_c`, and loses `surface_glow` and `burning`. Frame bytes (derived): 6 B × 230,400 cells = 1,382,400 B,
plus the fuel tables:

| Table | Bytes per row | At the limits |
|---|---|---|
| `objects` | 16 | 32,000 B (2,000) |
| `rods` or `slabs` | 36 or 52 | ≤ 104,000 B |
| `segments` | 11 | 220,000 B (2×10⁴) |
| `flames` | 38 | ≤ 760,000 B if every segment were its own cluster; 6.2 bounds the count |

At the limits, before flames, a frame is 1,738,400 B plus headers, below today's 1,843,200 B and the 3.5 MiB cap. B5 gates the
bytes per profile.

## 4. The object pass

### 4.1 Instanced meshes, data textures

- **One `MultiMeshInstance3D` per kind**, under a `Fuel` node beside `CellVolume`. Each object is one instance: a
  unit cylinder or box carried by a transform built from its geometry row. Engine why: a MultiMesh draws every
  instance in one draw call, with per-instance data. A node per object would mean 2,000 nodes and 2,000 draw calls.
- **Per-instance custom data** carries the object's first segment row and its segment count, both whole numbers in
  floats, exact below 2²⁴.
- **The rebuild is rare.** The client compares the `objects`, `rods` and `slabs` bytes with the last frame's, a
  native compare, and rebuilds instances only when they differ (0.46–0.57 ms at 2,000 objects [ran]). Geometry is
  immutable (fire_solid §1.1), so this happens on insertion and on burnout.
- **Segment state uploads every frame without a loop.** Each segment column becomes a 2-D texture 256 texels wide,
  with row i at (i mod 256, i div 256), padded with a resize: RH for `surface_temperature_c`, R8 for each u8. The
  bytes go from the frame to `Image.create_from_data` unchanged: 45–54 µs at 2×10⁴ rows [ran]. One instance per
  segment would cost 4.4–5.8 ms a frame in GDScript [ran], more than `client_rendering.md` §8's whole 3 ms budget, which B5 records as already
  broken by two other GDScript loops.
- **Shaders read by row:** the vertex shader reads `thickness_fraction` (shape, §4.2), and the fragment shader reads
  temperature, ignition and char. A fragment's segment is k = ⌊s/ℓ⌋, with s its distance along the axis.
- **Depth:** an ordinary depth test against the raymarch's written `DEPTH` (`client_rendering.md` §5.3), as bodies
  already do. **Cut-away:** objects are never cut; fuel never sits in a wall (fire_solid §1.3).
- **Colour by recipe:** albedo comes from client data keyed by recipe name, as materials are; an unknown recipe or kind
  is reported and drawn magenta, as an unknown material is.

### 4.2 Shape: burn-away and the pixel floor

- **Burn-away is shape.** A segment's drawn radius (rod) or thickness (slab) is its initial value ×
  `thickness_fraction`. At 0 the segment draws nothing, so a burnt-through stick shows a gap. In the probe, ten
  burnt segments of fifty left 9 of 56 pixel steps empty [ran].
- **The floor:** a segment with `thickness_fraction` > 0 is never drawn narrower than **2 output pixels**, at every
  tier. On the laptop tier (render scale 0.5) that is one rendered pixel. One
  floor in output pixels keeps the tiers' ID-mask areas comparable (`client_rendering.md` §6.3). A floor in rendered
  pixels would draw sticks twice as wide on the laptop.
- **Anti-aliasing is part of the contract,** because the floor alone doesn't remove the staircase: 38% → 38% (floor),
  27% (4× MSAA), 23% (both) [ran]. The check is §7's stability measure. MSAA or analytic edge coverage is the build's
  choice (owner question 3).
- **What the floor costs:** below the floor, apparent width carries no information. A 7.5 mm stick and a 15 mm stick
  look the same at the golden view. Their state shows through brightness (§5), gaps (above) and darkening (§6.3).

### 4.3 Picking and interaction

- **`F` on a fuel surface** (`client_rendering.md` §3): the pick also tests objects, analytically against the drawn
  (floored) geometry, at most 2,000 tests. It returns the point on the true surface nearest the hit, in mm. The
  server re-validates (6.4's metric nearest-surface query, fire_solid §2). On a stick narrower than 2 px, the drawn
  floor is what makes it clickable.
- **The hover outline** is drawn on the object's region (`region_id`), as for cells.
- **Interpolation** (`client_rendering.md` §3.1): cross-fading `surface_temperature_c` and `temperature_c` between
  frames is visual only. Geometry never interpolates.

## 5. Glow, burning and flames: never by colour alone

### 5.1 Structural glow from `temperature_c`

- **The structural glow input is the cell mean.** `surface_glow` was specified as the face's envelope-layer skin
  temperature, but nothing computes that: skins exist only on contact faces until 6.2's design (fire_solid §3.2).
  Today's encoder sends the cell mean under the name `glow`, so `temperature_c` is the same quantity under its true
  name.
- **The glow curve is unchanged** (`client_rendering.md` §5.3: gain 7, start 525 °C, hue dull red to yellow-white).
  Its start and span become client constants, since an f16 in °C needs no catalogue rational.
- **Known gap:** a face being heated is hotter than its cell's mean, so structural glow comes on late and dim, by an
  amount set by the 0.1 m channel grid. It goes in `docs/architecture.md`'s Known gaps with the build. If 6.2 puts
  skins on every structural face, the face temperature comes as a new channel with its own name (F1), not as
  `surface_glow`.

### 5.2 Fuel surfaces

- **Glow** uses the same curve on `surface_temperature_c`. Emission is HDR, and above 1.0 it drives bloom. Glow
  changes brightness, which `client_rendering.md` §6.4's L* check measures. The laptop tier's flat white band above
  about 1,230 °C stays (B7).
- **Burning:** `ignited_fraction` adds an emissive flame-lit term on the surface, scaled by the fraction, so a
  flaming surface is brighter than a merely hot one. That is brightness, not hue.

### 5.3 Flames

- **A flame is a volume**, drawn from its `flames` row: the base box and a height above it. It is a camera-facing
  stack, or a mesh whose silhouette tapers with height. Engine why: a flame is gas, with no surface for the raymarch
  or the fuel meshes to hit, so it is drawn as an emissive volume over them, blended additively, after opaque
  geometry. Flicker and particles are visual only (`client_rendering.md` §3.1), off in goldens. Particles stay a tier
  detail on top (`client_rendering.md` §5.5, B40 (2)).
- **Never by colour alone:** a flame adds pixels where nothing was drawn (shape) and brightness over them.
- **Without a flame table** there is no flame shape. If fire_model §7's fallback stops the exit below 6.2, burning
  shows by brightness only, and §7's flame-shape check can't run. That is a recorded risk, not a gap this design
  can close.

## 6. Crack severity by shape

### 6.1 The rule (cells' `crack`, segments' `char_fraction`)

This replaces the severity half of `client_rendering.md` §5.4 and implements step 8 owner decision 7:
1. **Monotone:** at every tier, edge density per unit of drawn cracked area rises strictly with severity, from 0.25 to
   1.0.
2. **Additive:** a groove drawn at severity c is drawn at every c′ > c on the same point. The pattern only gains
   edges as damage grows, and it never swims.
3. **No silent cracked cell:** every cracked cell's visible face shows at least one groove pixel, isolated or not.
4. **The floors hold:** grooves at least 1.5 px wide; the finest polygons at about 12 px (decision 4). Milder
   severities draw coarser octaves of the same pattern.

Mechanism, for step 8's checklist: nested Voronoi octaves, each switched on above a severity, plus a fissure through
each cracked cell's face wherever no octave edge crosses it. Tests prove the mechanism (§7); this document fixes only
the four properties.

### 6.2 Why severity can't stay in groove width

At the golden view, on a face square to the ray, the metre term's half-width is 0.02 m × c × 72 px/m = 1.44c px, so
the 0.75 px floor decides every groove below c ≈ 0.52 (derived); on slanted faces the floor is divided by the cosine
and decides more. B7 measured c = 0.25–0.96 drawing the same grooves on rig walls, and none on the laptop. Density changes at every zoom; width can't.

### 6.3 Char on fuel

- **Faces at least 12 px across** (a slab's top, 6.2's bed) carry the rule above, with `char_fraction` as severity.
  The pattern is fixed in the object's own coordinates.
- **Narrower fuel** (every stick, at every zoom) can't hold a 12 px polygon. Its char shows as darkening, a luminance
  change measured in L*, and its burn-away as gaps (§4.2). That satisfies "never colour alone" through brightness and
  shape, but it isn't a crack. Owner question 1.

## 7. Checks and goldens

### 7.1 Renderer goldens (hand-built fixtures)

- **A fuel fixture:** rods of 10, 50 and 100 mm and a slab. Segments carry a temperature ramp to 1,500 °C, an ignited
  run, `thickness_fraction` from 1 to 0 (a burnt-through run) and a char ramp. With 6.2, add one flame row.
- **A crack-severity fixture:** four blocks at c = 0.25, 0.5, 0.75 and 1.0, plus isolated single cracked cells at
  each.
- The fire fixture's hand-placed `surface_glow` and `burning` are replaced by the fuel fixture's tables, and its
  structural glow by `temperature_c`.

### 7.2 Measured checks (`scripts/golden_measures.py`, each proved by deletion)

| Check | Bar | Deletion that must fail it |
|---|---|---|
| Glow (kept), mask from both passes' debug views | ≥ 15 L* brighter | zero the emission |
| Crack (kept), cracked cells and charred faces ≥ 12 px | mean \|ΔL*\| ≥ 8 and ≥ 2× edge density | carving off, darkening kept |
| **Severity** | edge density strictly rising over the four blocks, each step ≥ 1.25× `[engineering]` | one octave for every severity |
| **Isolated cells** | every isolated cracked cell has ≥ 1 groove pixel, from a groove debug pass | the per-cell fissure removed |
| **Burn-through** | zero object-ID pixels over the burnt run; live runs at least the floor wide | `thickness_fraction` ignored |
| **Stick stability** | coverage along each stick varies ≤ 25% `[engineering]` (0.23 measured with MSAA and the floor, 0.38 without, [ran]) | AA off |
| **Flame shape** (6.2) | flame-ID pixels above the fuel > 0, and ≥ 15 L* over them | flames off, emission kept |
| Tier agreement (§6.3, kept) | the ID-mask areas now include fuel, within 15% | floor in rendered pixels |
| Speckle (kept) | extended to the fuel fixture's cold frame | — |

The stick-stability bar was chosen after the probe measured 0.23, so it is a ceiling to hold, not a prediction. A
build that can't meet it reports the measured value to the owner. Glow, crack, severity, isolated-cell, burn-through,
stability and flame-shape checks each read masks from the shaders' debug passes, so they measure exactly the pixels a
state reaches.

### 7.3 Scenario goldens

G1–G5 keep their names and tile §6.3's beats (`t_crack`, `t_glow`, `t_gone`). The tile §6 revision before 6.4 (D-S2)
restates those beats on objects; the client's requirement is only that each beat is computed from logged server
state, never from pixels.

### 7.4 Budgets (`client_rendering.md` §8)

The decode-and-upload row gains the segment textures (45–54 µs at the limits [ran]); the instance rebuild is a reported
row (0.46–0.57 ms per change [ran]); frame time at the golden view includes the object pass with its anti-aliasing. If MSAA
is chosen, every golden is re-recorded in its own commit (`client_rendering.md` §6.5) and its llvmpipe cost is measured first.

## 8. What changes elsewhere (in this branch, on acceptance)

| Document | Change |
|---|---|
| `client_rendering.md` | §4.2: the rows of §3.5 and its frame bytes; §4.1: the send rule's fuel clause; §3.1: the cross-fade row names `surface_temperature_c` and `temperature_c`; §5.1: the bed bullet becomes a link here; §5.3: glow's input and flames link to §5; §5.4: severity links to §6; §7.1: the `Fuel` node; §12: the rows of §9. Net words ≤ 0 |
| `fire_solid.md` | §5.6 becomes a link to §3; §7's D-B2 row names this document |
| `tile_and_client.md` | §5.5's bed meaning of `crack` is dropped (docs-contracts row 79) |
| `client/tests/fixtures/snapshots/FIELDS.md` | `surface_glow` and `burning` rows deleted; fuel tables listed as step 7's to confirm |
| `docs/standards_backlog.md` | B42 closed by this design, its build items moved to step 8's checklist; B7's crack gaps name §6; B5 gains the fuel bytes |
| `docs/design/contracts.md` (after #37) | the fuel tables registered, with markers in §3.2–§3.4 |
| `docs/lessons_maxim_in_games.md` | the entry below |

**Lesson.** A sub-grid simulation forces a second render path. When the server represents something below its grid
(fuel in metres, not cells), every consumer has to follow the representation, and the renderer is one of them. The
shader branch built on a cell channel for fuel because it read the client design and not the fire build spec. That
is B42, and the cause was a contract with two owners.

## 9. Requirements by step

| Step | Requirement |
|---|---|
| 6.0b | The frame publishes the fuel view: geometry and the four §3.3 reductions per segment, in f64, in key order. **Questions for fire_solid's owner:** F1, does the last segment take the remainder, as §3.2 assumes? F2, which slab face carries the segments? F3, is a rod's origin its axis's start? |
| 7 | The grammar's tables and catalogue entries (§3), `welcome`'s kind vocabulary, `required` on every fuel table, and the decoder checks of §3.2. Fixtures: a frame with fuel, a burnt-out object, an unknown kind (refused), a missing geometry row (refused), a segment-count mismatch (refused) |
| 6.2 | The `flames` table's quantities (§3.4); `bed` as a kind, with its geometry table and its segment rule |
| 8 | §4–§7: the pass, textures, floor and anti-aliasing, picking, the fixtures, the checks with their deletion proofs, budgets, the glow Known gap, the re-recorded goldens |

## 10. Owner questions

1. **Thin fuel shows char by darkening and burn-away by gaps, not by cracks** (§6.3). No stick reaches the 12 px a
   polygon needs at any zoom. *Recommended: accept.* The alternative is a crack drawn below its own floors, which is
   speckle.
2. **Structural glow from the cell mean until face skins exist** (§5.1), a Known gap. *Recommended: accept.* No
   face temperature exists to send.
3. **How sticks are anti-aliased** (§4.2). MSAA is one line of setup, but it re-records every golden and its
   llvmpipe cost is unmeasured. Analytic edge coverage in the object shader touches nothing else, but it blends, so
   draw order matters. *Recommended: prototype both at step 8 and choose by the stability check and frame time.*

## 11. Not settled here

How a flame looks beyond its shape and brightness; a bed's slats; where within a segment its ignited part lies;
delta frames; any NPC read of fuel (the NPC fire note).
