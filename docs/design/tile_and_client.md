# The tile and the client (design, step 0d, 2026-11-18)

**Status:** DRAFT, for a design review before code (Executor, Architecture, Wire integrity, Bio-faithful
integration, Client and rendering, Physics and resolution). Step 0d of `docs/plans/foundations_plan.md` §2; it feeds
steps 2 (Godot skeleton), 5 (clock), 6 (fuel), 7 (protocol v0) and 8 (the tile).

**Numbers** are *measured* (with source), *derived* (arithmetic shown), *from memory, to verify*, or `[engineering]`
(a choice, not physics). Godot API names not checked against 4.7.2 are *to verify*; step 2 probes each headless
before code depends on it.

**Corrections to the repo's text** (each lands with the PR that touches the file):
- `docs/architecture.md:20`, "The game is turn-based (classic Fallout)", is stale: superseded by real time with pause
  on a fixed tick (`origin/phase1/realtime-design:docs/design/realtime_lanes_coop.md`, decisions 1–4). Its Transport
  note that head-of-line blocking "is harmless for a turn-based game" is restated for real time in §5.3.
- `docs/roadmap.md` Phase 1 still lists the clinic (moved after the exit by D27) and an exit "at the laptop and rig
  profiles" (rendering tiers since D20). The comments in `data/rigs/*.yaml` still describe physics precision.

## 0. Decisions this document rests on

| Id | Decision | Owner, date | Source |
|---|---|---|---|
| T1 | **Camera: isometric 3/4,** fixed elevation, rotatable in 90° steps, zoom within limits; walls between camera and player get a cut-away rule | owner, 2026-11-18 | §3 |
| T2 | **Movement: click-to-move and WASD,** both reduced to validated intents through the one intent door, in canonical order, logged for replay; the client never moves the player authoritatively | owner, 2026-11-18 | §2, §4 |
| RT1–4 | Real time with pause on a fixed tick; a time dial; pause is a state, not a dial value; host-only time control behind `TimeAuthority` | owner, 2026-11-15 | realtime decisions 1–4, §2–§3 |
| D20 | One simulation truth at 0.1 m; rigs become rendering tiers only | owner, 2026-11-16 | world_model §0, §1 |
| D25 | Reconstruct, decide at the point, integrate; the client reads at its own level of detail, never "a cell" | owner, 2026-11-16 | world_model §0 |
| D26 | Tile first; exit: walk into the alley, set a crate on fire, watch it crack, glow and burn away by a fuel-mass law in open air; zones, combustion, CSG, phase change in Phase 2 | owner, 2026-11-17 | world_model §0 |
| D27, D28 | Clinic after the exit; grey-box heat-debt prototype after the tile | owner, 2026-11-17 | world_model §0 |
| O23 | Frames publish on change, not per tick | owner, 2026-11-17 | boundaries §0, §4.2 |

Nothing here redecides these. New proposals sit in their section; real choices are also in §12.

## 1. The alley in metres

### 1.1 Geometry

- **Extent 12.0 × 4.0 × 4.8 m** (x east along the alley, y north, z up): 60 × 20 × 24 cells at 0.2 m, whole on every
  axis, so `MaterialGrid.empty` accepts it at 0.2, 0.1 and 0.05 m.
- **A dead-end alley off a street.** x 0–1.2 m is pavement (the spawn); walls run from x = 1.2 m to the end wall.
  Clear width 3.2 m, walls 4.0 m tall `[engineering]`.
- **Every solid, and every air gap a test relies on, is ≥ 0.4 m** (two coarse cells).

| Name | Material | min_m | max_m |
|---|---|---|---|
| `floor` | concrete | (0, 0, 0) | (12.0, 4.0, 0.4) |
| `wall_south` | concrete | (1.2, 0, 0.4) | (12.0, 0.4, 4.4) |
| `wall_north` | concrete | (1.2, 3.6, 0.4) | (12.0, 4.0, 4.4) |
| `wall_end` | concrete | (11.6, 0.4, 0.4) | (12.0, 3.6, 4.4) |
| `crate` | wood | (6.0, 2.6, 0.4) | (6.6, 3.2, 1.0) |
| `crate_control` | wood | (9.0, 0.8, 0.4) | (9.6, 1.4, 1.0) |

- **The crate is the cross-tier crate,** a 0.6 m wood cube as in `tests/test_cross_tier.py::SCENE`, so the evidence
  measured on it (`docs/architecture.md`, Known gaps) carries over. It sits 0.4 m off the north wall.
- **`crate_control` is the negative control,** 2.68 m from the crate corner to corner (derived: √(2.4² + 1.2²)). It
  must stay intact (§7.3).
- **No bounding-box overlaps between named solids,** which `origin/phase1/act-validation`'s
  `scene._check_no_solid_overlaps` refuses: walls start on the floor's top face, the end wall sits between the sides.
- **No other props in Phase 1.** Sheet-metal props can't satisfy the thin-feature rule, and a solid steel block would
  be a false heat sink. Props come with the clinic (D27).
- **Material:** `wood` exists in `data/materials/core.yaml` (id 4) with thermal and degrade properties only, **no fuel
  properties** (heat of combustion, burn rate, char). Plan step 6 adds them in material table v1, with provenance.

### 1.2 Light and "open air"

- **No light field in Phase 1** (Phase 2). The shader's key light, ambient and bloom are rendering only, never sensed,
  never fed back. Ambient is low (night) so glow reads `[engineering]`. The sky's tint follows the world's time of day
  from the `tick` message, never the client's clock.
- **"Open air" (D26) means no O₂ limit, not an open heat boundary.** `heat.py` is insulated at the extent and has no
  convection or radiation (Known gaps), so the alley's open end and top lose no heat. The fuel law decides burn-out;
  the tile's air stays hot. Recorded as a Known gap with the tile's numbers.

### 1.3 Scene YAML

In `Scene.from_dict`'s format on `origin/phase1/act-validation` (closed keys `version`, `extent_m`, `primitives`,
`ambient_c`). The spawn is new, so this is **scene format v1**, with a v0 migration test.

```yaml
version: 1
extent_m: [12.0, 4.0, 4.8]
ambient_c: 15.0
spawns:   # new in v1: named points in metres, validated inside the extent and on free floor
  - {name: player, at_m: [0.6, 2.0, 0.4]}
primitives:
  - {kind: box, name: floor,         material: concrete, min_m: [0.0, 0.0, 0.0],   max_m: [12.0, 4.0, 0.4]}
  - {kind: box, name: wall_south,    material: concrete, min_m: [1.2, 0.0, 0.4],   max_m: [12.0, 0.4, 4.4]}
  - {kind: box, name: wall_north,    material: concrete, min_m: [1.2, 3.6, 0.4],   max_m: [12.0, 4.0, 4.4]}
  - {kind: box, name: wall_end,      material: concrete, min_m: [11.6, 0.4, 0.4], max_m: [12.0, 3.6, 4.4]}
  - {kind: box, name: crate,         material: wood,     min_m: [6.0, 2.6, 0.4],   max_m: [6.6, 3.2, 1.0]}
  - {kind: box, name: crate_control, material: wood,     min_m: [9.0, 0.8, 0.4],   max_m: [9.6, 1.4, 1.0]}
```

`data/scenes/alley.yaml`; its loader test checks 0.2 m alignment in integers, not floats (world_model §8, F13).

### 1.4 Size and memory (derived)

| Grid | Cells | At 100–125 B/cell (world_model §9) | Role |
|---|---|---|---|
| 0.2 m | 28,800 | 2.9–3.6 MB | verification |
| **0.1 m** | **120 × 40 × 48 = 230,400** | **23–29 MB** | **truth** |
| 0.05 m | 1,843,200 | 184–230 MB | reference |

Solid at 0.1 m: 59,312 cells (floor 19,200, sides 17,280 each, end 5,120, crates 216 each), 26%. The truth grid is
36% of the 640,000-cell synthetic tile whose cached heat substep measured 3.9 ms (world_model §9), so about 1.4 ms
here (derived estimate); step 5 measures it.

## 2. The player

### 2.1 The body

Nothing in the repo models a body or a position (checked: `world/`, `sem_env/`; the realtime design's `actors` is an
id allocator). Minimal proposal:
- **An actor, not cells.** The `Simulation` holds an actor table: `actor_id`, `pos_mm` (3 × int32), `held` heading
  (int8, −1 none), `path` (int32 waypoints). **Integer millimetres** `[engineering]`: exact, so replay needs no float
  care.
- **Collision volume:** an upright cylinder, radius 0.25 m, height 1.8 m `[engineering]` (shoulder half-width about
  0.2–0.25 m, *from memory, to verify*). Feet on the floor's top (z = 0.4 m); no gravity or steps in Phase 1.
- **Speed:** 1.4 m/s, a common preferred walking speed (*from memory, to verify*): 140 mm per 0.1 s tick. No running.
- **Not painted into cells:** the body doesn't block heat, burn or take damage. Standing in the fire is harmless, a
  Known gap until bodies have physics (Phase 4/5).
- **Data:** `data/world/player.yaml`, versioned, closed keys, strict loader like `ActionLimits.load`.

### 2.2 Movement on the server

- **Tick order** (realtime §2.1) gains one stage: apply records, **move bodies**, agents (no-op), physics on physics
  ticks, outputs.
- **Headings in integers:** h ∈ 0..7 is h × 45° counter-clockwise from +x; axis steps are 140 mm, diagonals (99, 99)
  mm (140/√2 = 98.99; 0.007% speed error, derived). The table is data.
- **Blocked** = the cylinder at the candidate position overlaps a solid truth cell in the band [feet + 0.05 m, feet +
  1.8 m], or leaves the extent less the radius; a disc–square test in integer mm. A reduction over the body's volume
  in metres, identical on every machine (D20) `[engineering]`.
- **Sliding:** full step, else its x part, else its y part, else stay. A step (140 mm) is shorter than the radius and
  walls are ≥ 0.4 m, so nothing tunnels (derived).
- **Burned-away cells become walkable;** `topology_version` (world_model §7) invalidates paths.

### 2.3 "Set a crate on fire" as an intent

**What exists** (`origin/phase1/act-validation:src/maxim_overdrive/sem_env/bridge.py`): `parse_action` over `strike
{energy_j, sigma_m, point_m}`, `ignite {power_w, radius_m}`, `extinguish {}`, with ceilings in `data/world/actions.yaml`
(ignite ≤ 500 kW, radius 0.3–3.0 m). `_ignite` places a `HeatSource` at the **region's centroid**, burning until
extinguished. The YAML says the ceilings are "not what a body can do"; world_model §8 retires `extinguish` for `douse`.

**What the tile needs instead:**
- **A point on the surface.** A centroid fire starts inside the crate. `ignite` gains `point_m`, validated as
  `strike`'s is: on the region's authored footprint, within 0.1 m of its surface `[engineering]`.
- **A pilot, not a fire.** After step 6 the fire belongs to the fuel law; the player supplies `ignite {point_m,
  power_w, duration_s}`, limited by `data/world/player.yaml` (narrower than the ceilings). Step 6 owns the pilot's
  physics (area-overlap deposit, world_model §3) and picks the tile's values **outside the band gate**: ≥ 2× the
  reference grid's minimum igniting pilot energy `[engineering]`.
- **Reach and rate:** the body's axis within 1.5 m of the point `[engineering]`; one live pilot per actor; ≤ 1 ignite
  per second per session (`data/server/`). No line-of-sight check yet (a Known gap; nothing thin to reach through).
- **One door:** stage-1 `engine.intents.parse_action`, the log, stage-2 against the world at apply (boundaries §6).
  Refusal codes: `out_of_reach`, `not_on_region`, `limit`, `not_finite`, `busy`.

This changes another branch's vocabulary: a Wire item for step 7, a Physics item for step 6 (§12 Q3).

## 3. Camera and occlusion (T1)

### 3.1 The camera

- **`Camera3D` with `projection = PROJECTION_ORTHOGONAL`.** Parallel projection keeps sizes constant with depth, which
  is what makes a 3/4 view read as a map. Engine why: a camera property, no custom matrix.
- **Elevation 40°** `[engineering]` (true isometric is 35.26°, arctan 1/√2). Steeper shows more floor between 4 m
  walls; a 4 m wall hides 4.8 m of floor behind it at 40° and 5.7 m at 35.26° (derived), more than the 3.2 m alley, so
  the cut-away is required at any angle in range.
- **Yaw 45° + k·90°,** Q/E, tweened over 0.25 s. **Zoom:** orthographic `size` (view height) 6–24 m, default 12 m,
  ×1.25 per wheel step `[engineering]`.
- **Follow:** a critically damped spring on the interpolated player, about 0.2 s. Camera 60 m back, clip 0.1–200 m.
- **Golden camera:** yaw 45°, elevation 40°, size 10 m, centred on the crate, 1280 × 720.

### 3.2 The cut-away rule

A fade still covers the player in colour, so this design cuts (as The Sims' walls-down mode does, *from memory*):
- **A cell is cut** when (a) it is on the camera's side of the player, dot(cell − player, f) < −0.3 m, f the camera's
  horizontal forward; (b) within 4.0 m of the player horizontally; (c) its bottom is > 1.0 m above the player's feet
  `[engineering]`.
- **Cut faces are hatched** (a shape, not a colour), so a cut never reads as burned-away wall. The 1.0 m stumps keep
  the layout legible.
- **Always on:** no occlusion test, no popping. **Visual only:** shader uniforms; the server's walls stay whole.
- **Tests:** golden G5 (§8); the player's ID-mask pixels (§8.4) ≥ 95% visible at all four yaws `[engineering]`.

## 4. Input to intents (T2)

### 4.1 WASD as a held direction

- **Camera-relative keys, world-frame wire.** The client resolves the keys and camera yaw to one of 8 world headings
  or none; with yaw at 45° + k·90° every combination lands exactly on one (derived).
- **Sent on change only:** `move {heading: 0..7 | null}`. The server holds it per actor and steps the body each tick.
  The log stores changes; replay reproduces every step. A per-tick stream would add records and make the client track
  the server's tick for nothing; TCP on localhost loses nothing, and a leave is a logged stop.
- **Validation:** integer in [0, 7] or null; ≤ 30 per second per session.
- **While paused,** a `move` applies at the next tick; press-and-release nets to nothing.

### 4.2 Click-to-move, pathed on the server

- **The client sends a target, never a path:** `move_to {target_mm: [x, y]}`, picked by a CPU DDA ray through the
  material bytes it holds (§6.1). The pick is re-validated.
- **Walk grid:** 2-D at 0.1 m, a cell free if the body centred there isn't blocked: a disc convolution of column
  occupancy, 4,800 nodes, rebuilt when `topology_version` changes.
- **A\*:** 8-connected, integer octile costs (10, 14), no corner cutting, ties broken by (f, h, j, i), ≤ 10,000
  expansions else `no_path`. A blocked target snaps to the nearest free node within 0.3 m, else `unreachable`. Paths
  are pruned by deterministic line of sight, walked at 1.4 m/s, arrival within 50 mm `[engineering]`.
- **Reply** `move_result {tick_applied, success, error, path_mm}`: the client draws the server's route. A `move`
  cancels a path; a new `move_to` replaces it; a topology change replans once, else the body stops with
  `path_blocked`. While paused, the path is planned at the next tick and walked on resume.

### 4.3 Controls

| Input | Message | Who |
|---|---|---|
| Space | `time {request: pause}` / `{request: resume}` | host; guests refused by `TimeAuthority` |
| `,` / `.` | `time {request: set_scale, scale}` over presets 0.25, 0.5, 1, 2, 5, 10, 20 from `data/server/` `[engineering]` | host |
| `F` on a region | `act {region, action: ignite, params: {point_m, power_w, duration_s}}` | any actor |
| Q, E, wheel | none (camera) | client |

The HUD shows requested and effective scale and **"dilated"** when effective < requested (realtime §3.1). It hides
time controls when `welcome.role` isn't host; the server refuses them regardless, tested in step 7 with the controls
forced visible.

### 4.4 What the client may and may not do

| May (visual only) | May not (feeds back) |
|---|---|
| Interpolate poses, one tick behind | Move the drawn body by its own collision |
| Animate walk and turn from interpolated velocity | Send positions, paths or waypoints |
| Tween camera; cut-away; bloom; flame particles | Send intents at frame rate or on a timer |
| Cross-fade `glow` between two frames | Decide reach, region or ignition |
| Pick a point and region (re-validated) | Put its own clock into anything it sends |

**No prediction in Phase 1** `[engineering]`. Latency (derived): 0–100 ms to the next tick (mean 50), plus 100 ms
interpolation, plus a 17 ms frame: about 170 ms mean, 220 ms worst. Fine for an iso walk, slow for action. §12 Q2.

### 4.5 Replay

Every `move`, `move_to`, `act` and `time` record gets `(tick, host_seq)` and goes into the intent log (realtime §4.2).
**Test:** the exit scenario run live through the socket, then replayed from its log with no client, gives
bit-identical actor tables and grids at every physics tick.

## 5. Snapshot channels to 3-D textures

### 5.1 Channels

From `world.snapshot()`; names are identities (world_model §8):

| Channel | dtype | Meaning | Godot `Image` format |
|---|---|---|---|
| `material` | u8 | id, 0 air | `FORMAT_R8`, nearest; id = round(r·255) |
| `crack` | u8 | round(255·(1 − integrity)) on solids | `FORMAT_R8` |
| `glow` | u8 | round(255·clip((T − 525)/975, 0, 1)) on solids | `FORMAT_R8` |
| `temperature_c` | f16 | T clipped to [−273, 6000] °C | `FORMAT_RH`, debug view only |

- **`snapshot()` today returns (x, y, z) arrays and a float `time_s`;** the wire is `[nz, ny, nx]`, x fastest, z-up,
  integer `tick` (realtime §7). The transpose lives in `engine.encoding` (boundaries), held by the asymmetric golden
  fixture.
- **Missing: where it burns.** Cells vanishing shows "burned away", not "burning". The tile needs **a `fire` channel
  from step 6:** u8 heat release per volume, with its linear scale in the frame header (§12 Q4).

### 5.2 Upload

- **One `ImageTexture3D` per channel,** made on `welcome` by `create(format, nx, ny, nz, false, images)` and refreshed
  by `update(images)`; `images` is `Array[Image]`, one `Image.create_from_data(nx, ny, false, format, bytes)` per
  z-slice from `PackedByteArray.slice`. Engine why: the built-in 3-D texture a shader samples as `sampler3D`;
  separate R8 textures avoid per-byte repacking in GDScript, which would cost more than the upload.
- **Whole-texture updates** in v0 (`research/states_of_matter/architecture.md` expects no partial update, *to
  verify*). Two `glow` textures (previous, current) for a 0.5 s cross-fade.
- **Axes in one place, the shader:** Godot (X, Y, Z) = server (x, z, −y); texture (u, v, w) = (x/nx, y/ny, z/nz).
- **`WebSocketPeer.inbound_buffer_size`** raised from its 64 KiB default (architecture.md, Transport) to 4 MiB
  `[engineering]`, `max_queued_packets` bounded; an oversize frame fails the session loudly, with a test.

### 5.3 Cadence and size

- **Cells on change** (O23): after each physics step (every 5 ticks) and each tick that applied an intent, at most
  `snapshot_hz` (2 Hz during fire, realtime §7), latest-wins.
- **Actors in the `tick` message,** throttled to ≤ 30 Hz `[engineering]`, under 40 B per actor. They are also a table
  in the published frame, so a Phase 4 perceiver reads bodies and cells from one frame.
- **Frame size at 0.1 m (derived):** 230,400 × 5 B = 1,152,000 B plus a < 2 KB header; 2.3 MB/s at 2 Hz;
  `temperature_c` is 40%. Compression off in v0 (reserved); 74% air suggests zstd pays (*to verify*).
- **Head-of-line blocking:** a `tick` queued behind a 1.15 MB frame waits on the order of a millisecond on localhost
  (*to verify*); the one-tick interpolation buffer absorbs it. Meter in §10.

### 5.4 Rendering tiers

Every tier uploads the same 0.1 m channels; tiers change drawing, never the world:

| Tier | `Viewport.scaling_3d_scale` | Crack substeps | Glow filter | Bloom | AO | Flame particles |
|---|---|---|---|---|---|---|
| laptop | 0.5 | 2 | nearest | off | off | 64 |
| rig | 1.0 | 4 | trilinear | on | 4-tap | 256 |
| max | 1.0 | 8 | trilinear | on | 6-tap | 1,024 |

All `[engineering]`, retuned after §10's first measurements. These fields go to rendering data under `engine.tiers`
(boundaries S1); `cell_size_m` and `min_substeps_per_turn` leave the tier files when D20 is enforced. "Same apart
from detail" is a test (§8.3).

## 6. The one shader

### 6.1 Recommendation: raymarch the cell volume

| Option | Per update | Verdict |
|---|---|---|
| Greedy meshing on the CPU | remeshing 230,400 cells in GDScript at 2 Hz, likely hundreds of ms (*to verify*), or a C++ GDExtension | no, for a newcomer team |
| Marching cubes | as above, or compute shaders; smooth surfaces also blur the cells cracks are drawn on | no |
| **Voxel raymarch (DDA), one fragment shader** | **an upload, nothing else** | **yes** |

- **How:** a `MeshInstance3D` with a `BoxMesh` the size of the extent and a `ShaderMaterial`. Per pixel of the box's
  front faces, the shader walks the ray cell by cell with Amanatides–Woo traversal (1987: always step to the nearest
  cell boundary) until it meets a solid, uncut cell; the crossed face gives the normal. Orthographic rays share one
  direction. Engine why: ordinary Godot, no compute pipeline or GDExtension; the textures are the whole state.
- **Cost (derived):** ≤ nx + ny + nz = 208 steps per ray, about 40 typical in the golden view: ~37 M texel reads per
  1280 × 720 frame plus crack substeps. Laptop renders a quarter of the pixels. Measured in §10.
- **Depth:** the shader writes `DEPTH` from the hit, so the player's `CapsuleMesh` composites in the same opaque pass
  (reversed-Z formula *to verify*).
- **Lighting in the shader** (`render_mode unshaded`): fixed key light, three-tone face shading (top brightest,
  classic iso), neighbour AO on tiers that have it, emission on top. No dynamic shadows in Phase 1. Whether unshaded
  output above 1.0 drives bloom under the chosen renderer is *to verify*.
- **Inputs:** `sampler3D` uniforms with `filter_nearest`, `repeat_disable` (*to verify*): material, crack, glow
  (previous and current), temperature (debug), later fire; a 256 × 1 palette from `welcome`'s `color_rgb` per id;
  `grid_shape`, `cell_size_m`, `glow_t`, `crack_substeps`, the cut-away's player position, forward, radius and height.
  The client's picking runs the same DDA on the CPU, ≤ 208 steps per click.

### 6.2 Crack changes shape and shading

- **Shape:** each cell carries a fixed fracture pattern, the edges of a 3-D Voronoi diagram seeded by an integer hash
  of the cell index (deterministic). Where `crack` = c > 0, points within 0.02 m × c of an edge are **empty**
  `[engineering]`. On a hit the shader marches `crack_substeps` into the cell; a ray in a fissure goes deeper, and
  one that leaves the cell resumes the DDA. Cracks are grooves with depth, visible in silhouette and in greyscale.
- **Shading:** fissure walls darken with depth, and the normal tilts towards the nearest edge, so light catches the
  lips. Char darkens albedo with c too, but the tests (§8.4) use luminance and edges, never hue.

### 6.3 Glow changes brightness

- **T from `glow`:** T = 525 + 975·g/255 °C (`snapshot()` inverted; 3.8 °C per step). 525 °C is `GLOW_START_C` in
  `world.py`, near the Draper point (798 K), where hot solids first glow visibly red; the repo cites no source, so
  *from memory, to verify* before material table v1.
- **Brightness ∝ (T_K/1773)⁴** (Stefan–Boltzmann, normalised at 1500 °C), with hue from dull red through orange to
  yellow-white. Bright and dim differ in greyscale (§8.4).
- **Flames** (with `fire`): emissive flicker on fire cells' exposed faces, plus `GPUParticles3D` seeded at fire cells;
  visual only, off in goldens.

### 6.4 What glow can show today

The Known gaps record peaks of 538 °C (0.2 m) and 613 °C (0.1 m) while the crate burns: `glow` 3 and 23 of 255
(derived), barely visible, because wood cells degrade away (from 250 °C) before they get hot. **"Watch it glow"
depends on step 6's surface law** giving char or embers above 525 °C over an area. If it doesn't, that is a physics
finding for step 6, never a reason to rescale `glow` in the shader. §7.3 gates the channel, not pixels.

## 7. The exit scenario, scripted

### 7.1 The clock

Tick 0.1 s (`tick_us` = 100,000), physics every 5 ticks (0.5 s), as realtime §2.2 proposes. This replaces the 6 s
"turn" and answers the plan's open "turn length" (plan §5, roadmap), for the owner to confirm (§12 Q1).

### 7.2 The script

`tests/scenarios/alley_exit.log`, in the intent-log format; ticks are apply ticks.

| Tick | Record | Expect |
|---|---|---|
| 0 | `join` host → actor 1 at (600, 2000, 400) mm | `welcome`, role host |
| 10 | `move {heading: 0}` | east at 140 mm/tick |
| 42 | `move {heading: null}` | at (5080, 2000) (derived: 600 + 32 × 140) |
| 50 | `move_to {target_mm: [5500, 2900]}` | a path; arrival by about tick 58 (993 mm at 140 mm/tick) |
| 70 | `act {region: crate, action: ignite, params: {point_m: [6.0, 2.9, 0.7], power_w: P, duration_s: D}}` | success: the west face, 0.5 m from the body's axis |
| 75 | `time {request: set_scale, scale: 10}` | granted |
| ≤ 36,000 | nothing | §7.3 |

- P and D come from step 6 (§2.3). The cap, 3,600 world seconds `[engineering]`, fails a crate not gone by then.
- **Refusal variants,** each asserting its code and an unchanged world digest: ignite from the spawn
  (`out_of_reach`), at `[6.0, 2.0, 0.7]` (`not_on_region`), P over the limit (`limit`), NaN (`not_finite`), `time`
  from a guest token (refused).

### 7.3 What must be observed

**Automated on the server's frames** (Python, unpaced `Simulation.step`, every physics tick):
1. **Arrival:** x ≥ 1.2 m by tick 40; within reach at tick 70.
2. **Crack:** `t_crack` = first tick with ≥ 8 crate cells at `crack` ≥ 64 (integrity ≤ 0.75).
3. **Glow:** `t_glow` = first tick with ≥ 8 crate surface cells at `glow` ≥ 26 (T ≥ 625 °C) `[engineering]`.
4. **Burned away:** `t_gone` = first tick with crate solid volume ≤ 5% of 0.216 m³, before the cap.
5. **The fire stops when the fuel is gone:** `tests/test_cross_tier.py::test_a_fire_that_has_burned_its_fuel_stops_heating`
   flips green and its strict red gate is removed (step 6). On the tile: from `t_gone`, `fire` is zero everywhere;
   no cell ever exceeds 2000 °C (`WOOD_FLAME_C`); from `t_gone` + 600 ticks the tile's maximum only falls.
6. **Order:** all three times exist, and `t_gone` > `t_glow`.
7. **Controls:** `crate_control` and walls keep integrity ≥ 0.99; the floor ≥ 0.95, since concrete degrades from
   300 °C under the crate (measured first, recorded with the threshold) `[engineering]`.
8. **Determinism:** two runs and the replay are bit-identical at every physics tick (§4.5).
9. **Convergence:** at 0.2 m and 0.05 m the outcome class matches (gone, stopped, controls intact) and `t_gone`
   agrees with the 0.05 m reference within the band gate (world_model §3). Thresholds come from measurement and are
   never loosened to pass.

**Automated on the client:** the goldens (§8).

**Human playtest** (owner, live at 1× then 10×): does walking feel responsive; is the player visible behind the south
wall at every yaw; does the crack read as a crack and the glow as heat; does burn-out read as fuel running out; does
the dial feel right. The verdict and the measured latency go in the PR.

## 8. Golden screenshots (B7)

### 8.1 Method

- **Not `--headless`:** it uses a dummy renderer that draws nothing (true of Godot 4.x as I know it; *to verify* in
  4.7.2). Goldens run the client with a real rendering context and `--fixed-fps 60` (*to verify*).
- **From recorded frames, not a live server.** The scenario writes frames at chosen ticks to
  `client/tests/goldens/frames/<tick>.bin` (wire format). `client/tests/golden.tscn` decodes one, sets the golden
  camera, turns off particles, animation and cross-fade, waits 3 frames and saves
  `get_viewport().get_texture().get_image()` as PNG. A render is a pure function of (frame, camera, tier).
- **Frames:** G1 tick 70 (cold, player at the crate), G2 `t_crack`, G3 `t_glow`, G4 `t_gone` + 100, G5 camera on the
  south side with `wall_south` between it and the player. Five per tier, 15 PNGs.
- **Renderer goldens** use fixed frame fixtures and catch shader regressions; **scenario goldens** are re-recorded
  deliberately when physics changes.

### 8.2 Tolerance

- **Metric:** per-pixel CIE76 ΔE in CIELAB, in numpy (no new dependency). Pass: mean ≤ 1.0, 99.5th percentile ≤ 4.0,
  and no 4-connected blob with ΔE > 10 over 64 pixels `[engineering]`. The blob rule catches a missing crack a mean
  would hide.
- **Proved by deletion:** renders with crack carving disabled, and with emission zeroed, must fail G2 and G3.

### 8.3 Same apart from detail

Box-filter each tier's frame to 160 × 90; laptop against rig must pass mean ΔE ≤ 3.0, 99th percentile ≤ 10, and the
ID-mask areas of the crate, glow region and player agree within 15% `[engineering]`.

### 8.4 Never colour alone, as a test

- **ID pass:** a debug uniform renders region and actor ids as flat colours, giving the crate's and player's pixels.
- **Greyscale:** in L* only, G2's crate pixels differ from G1's by ≥ 8 in mean with ≥ 2× G1's Sobel edge density;
  G3's glowing pixels are ≥ 15 L* brighter than G1's `[engineering]`.

### 8.5 Platforms and updates

- **Canonical goldens** render in CI on Linux with Mesa's software rasteriser (llvmpipe), identical across runners,
  stored as `client/tests/goldens/<renderer>-<driver>/<tier>/G<n>.png`.
- **The owner's Mac** compares against them and reports without gating; the tier-agreement and greyscale checks
  (one machine's frames against each other) gate everywhere.
- **Updates are deliberate:** `scripts/update_goldens.sh <reason>` re-renders, writes a diff image per golden and
  refuses a dirty tree; the commit carries reason and diffs. Tests never rewrite goldens.

## 9. Godot project shape

### 9.1 Scene tree (`client/scenes/main.tscn`)

```
Main (Node3D)                     main.gd: wires children, holds no game state
├── Net (Node)                    net_client.gd: WebSocketPeer, handshake, routing
├── World (Node3D)
│   ├── CellVolume (MeshInstance3D: BoxMesh + ShaderMaterial)   cell_volume.gd, cell_volume.gdshader
│   ├── Actors (Node3D) → Actor_<id> (MeshInstance3D: CapsuleMesh)   actor_view.gd: interpolation
│   ├── Path (MeshInstance3D: ImmediateMesh)                     the server's route
│   └── Flames (Node3D) → GPUParticles3D
├── CameraRig (Node3D, yaw) → Pitch (Node3D) → Camera3D (orthogonal)   camera_rig.gd
├── WorldEnvironment               background, bloom per tier
├── IntentInput (Node)             intent_input.gd: InputMap actions → messages
└── Hud (CanvasLayer) → Control    hud.gd: dial, pause, scales, "dilated", refusals
```

- **Engine whys:** `Node3D` is anything with a 3-D transform; `MeshInstance3D` draws one mesh with a material;
  `CanvasLayer` draws UI over the 3-D view; `WorldEnvironment` holds post-processing; `Net` is a plain child, not an
  autoload singleton, so dependencies show in the tree and tests can swap it.
- **Pure logic in `RefCounted` scripts** (`protocol/frame_decoder.gd`, `heading.gd`, `dda.gd`): Godot's
  reference-counted object with no tree, testable without a scene.

### 9.2 GDScript and tests

- **Fully typed;** warnings as Error in `project.godot`: `untyped_declaration`, `inferred_declaration`,
  `unsafe_property_access`, `unsafe_method_access`, `unsafe_cast`, `unsafe_call_argument`, `return_value_discarded`
  (names *to verify*). Engine why for GDScript over C#: no .NET toolchain, the editor's own language, headless parse
  checks with no build.
- **A minimal test runner** (`client/tests/run.gd`, `godot --headless -s`), not a third-party addon, so no licensed
  asset to list. It runs the decoder against `tests/fixtures/wire/` (B3), the heading table and the DDA, in the gate
  (step 2, B6).

### 9.3 Renderer

**Compatibility (OpenGL 3.3)** for Phase 1 `[engineering]`: the shader is unshaded, so Forward+ buys little, and
Compatibility runs on integrated GPUs and CI's llvmpipe, so goldens match what players run. Bloom support there is
*to verify*; if absent, a post-process pass on rig and max (§12 Q5).

### 9.4 Connecting

- **The server launches the client** and passes the per-launch token by environment variable (`OS.get_environment`)
  or a 0600 file, never argv (realtime §5).
- **`WebSocketPeer.connect_to_url("ws://127.0.0.1:<port>")`,** the literal address; `poll()` each `_process`; text
  packets are JSON, binary are frames (`was_string_packet()`).
- **No `Origin` header:** the server refuses any. architecture.md says `WebSocketPeer` sends none unless told,
  unconfirmed; step 2 proves it with a Python listener that fails on `Origin`, and the client never sets
  `handshake_headers`.
- **`hello {protocol: 0, token}` first.** The client refuses unknown protocol, `kind` or dtype loudly, and checks each
  frame header (shape as in `welcome`, sizes within offsets) before slicing.

## 10. Performance budgets

**Method** (plan §6): Python meters are CPU time (`time.process_time_ns`), minimum of N ≥ 20, never wall time on a
loaded machine. GDScript has no per-process CPU clock, so client meters are the minimum of N ≥ 50
`Time.get_ticks_usec()` intervals, which rejects interference, plus GPU time from
`RenderingServer.viewport_set_measure_render_time` / `viewport_get_measured_render_time_gpu` (*to verify*). Targets
become the first measurement + 20% (B5).

| Meter | Target | Gate |
|---|---|---|
| Frame bytes at 0.1 m | ≤ 1,154,048 B (1,152,000 + header) | exact |
| Frame encode, server CPU | ≤ 5 ms | B5 |
| Heat substep on the alley | ≈ 1.4 ms (§1.4) | B5 |
| Move bodies + replan, per tick | ≤ 0.5 ms | B5 |
| Client decode + upload | ≤ 6 ms | B5 |
| GPU frame, rig tier, golden view, owner's Mac | ≤ 8 ms | B5 |
| GPU frame, laptop tier, integrated GPU | ≤ 12 ms | B5 |
| `tick` delay behind a frame, p99 | ≤ 5 ms | B5 |
| Input to photon, WASD | ≤ 220 ms worst (§4.4) | reported |

An upload at 2 Hz may spend one frame's budget each half-second; p99 frame time is reported with it.

## 11. Bio-faithful note

Phase 1 has no NPCs; the tile must not block Phase 4's percepts, which are reductions of physical channels at the
perceiver, in metres (boundaries §4.4, npcs §7.1):
- **Everything an NPC could care about is a named region in metres.** "The crate is hot" becomes a surface
  temperature over the crate's visible area from where the NPC stands, not today's interior `temperature_max` (an
  instrument). The reductions are one `bincount` over `region_id` (23 ms at 0.05 m on the synthetic tile, world_model
  §9; less here).
- **The player is an actor in the world's frame,** so an NPC perceives the body and the ignite event from the same
  frame and log.
- **Nothing an NPC would see is client-only.** Light, smoke and sound are Phase 2 fields; the sky follows world time,
  so a later SCN entrained by world light shares the player's day.
- **Divergence named:** the player's body has no physics in Phase 1 (§2.1).

## 12. Open questions for the owner

1. **Turn length:** a 0.1 s tick with physics every 0.5 s, retiring the 6 s turn? *Recommend yes;* it unblocks step 5.
2. **Prediction for the player's own body:** none in Phase 1 (~170 ms mean latency), or visual-only from the start?
   *Recommend none,* measured in the playtest, added visual-only if walking feels sluggish.
3. **Ignite as a bounded pilot** (`point_m`, `power_w`, `duration_s`, reach 1.5 m) instead of a centroid fire that
   burns until put out? *Recommend yes,* values from step 6 outside the band gate.
4. **A `fire` channel from step 6** so flames can be drawn? *Recommend yes;* otherwise "burning" shows only as cells
   disappearing.
5. **Compatibility renderer** rather than Forward+ for Phase 1? *Recommend Compatibility,* matching CI's software
   goldens and integrated GPUs; revisit with Phase 2 light.
6. **Elevation 40°** rather than true isometric 35.26°? *Recommend 40°* for the narrow alley.

## 13. What this does not settle

- **Step 6:** the burn law, the pilot's physics and values, `fire`'s definition, whether glow reaches the §7.3
  threshold, and the three times.
- **Step 7:** `move`, `move_to`, `move_result` as message kinds with golden fixtures; the actor table in frames; the
  `tick` throttle; `ignite`'s new params.
- **Later in Phase 1:** the clinic and its doorway (D27); save v0 with the actor table (step 9); the heat-debt
  prototype (D28).
- **Phase 2:** light, sound, smoke, convection, open boundaries, zones; delta frames, zstd, partial uploads, dynamic
  shadows; refinement near fronts.
- **Phase 4/5:** bodies with physics, NPC percepts here, line of sight for reach. **Phase 5+ (O28):** co-op guests.
- **Not designed:** gamepad (a 16-heading vocabulary would be a versioned change), audio, menus, client-side saves.
