# The tile: client and rendering (design, step 0d, v3, 2026-11-18)

**Status:** v3, frozen (owner T13, 2026-11-18); the final physics review's FPH-B1 to B3 are step 6 requirements (`docs/plans/checklists.md`). Split from v1 of `tile_and_client.md` (f6afd66) after
its six-lens review, accepted as O31; delta-reviewed with it (`docs/design/reviews/tile_v1/`, fold status in
`fold.md`). This document is the wire as the client reads it and the Godot side; the world side is
`tile_and_client.md`, cited as "world §n".

**Numbers** are *measured*, *derived*, *from memory, to verify*, or `[engineering]`. **[ran]** marks Godot 4.7.2 facts
measured on the owner's M2 (4.7.2.stable.official.ed1daf0bf), by the tile review (`reviews/tile_v1/`) or step 2's
probes (`research/godot_probes.md`).

## 0. Decisions this document rests on

This document's decisions (10 rulings) are kept as records, with their dates, owner sections and status, in `decisions/client_rendering.md`.

## 1. The camera (T1, T10)

- **`Camera3D` with `projection = PROJECTION_ORTHOGONAL`** [ran]. Parallel projection keeps sizes constant with depth.
  Engine why: it's a camera property, so no custom matrix is needed.
- **Elevation 40°.** A 4 m wall hides 4.8 m of floor behind it, more than the 3.2 m alley (derived), so the cut-away
  is needed.
- **Yaw 45° + k·90°,** on Q and E, tweened over 0.25 s.
- **Zoom:** orthographic `size` from 6 to 24 m, default 12 m, ×1.25 per wheel step `[engineering]`.
- **Follow:** a critically damped spring of about 0.2 s. The camera sits 60 m back, with clipping at 0.1–200 m.
- **Golden camera:** yaw 45°, size 10 m, centred on the crate, at 1280 × 720, which gives 72 px/m (derived).

## 2. The cut-away (T11; CR-S3, CR-N2)

- **Which regions:** walls, as named in client data (`client/game/cutaway.tres`, keyed by region name; DC-N4).
- **When:** a flagged region is cut when its authored box centre lies on the camera's side of the player:
  dot(c − p, f) < 0, where f is the camera's horizontal forward at the **target** yaw.
- **Stumps:** cut regions keep a 0.3 m stump, the cells whose top is ≤ feet + 0.3 m. With the body's axis 0.25 m from
  a wall face, the sightline at 40° rises 0.30 m by the face (0.25/sin 45° × tan 40°, derived). So the stump hides at
  most the feet's edge.
- **Hatching:** cut faces are hatched, a shape rather than a colour, so a cut wall never reads as burned away.
- **Never cut:** the crate and other non-wall regions, so the fire stays visible from anywhere.
- **No pops:** a side wall's centre line is never crossed, and the flag flips only at tween start. The end wall's
  centre (x = 11.8 m) is out of the body's reach.
- **Visual only:** uniforms, never fed back.
- **Test (step 8):** the player's ID-mask pixels with world geometry drawn, divided by the same with the cell volume
  hidden, must be **≥ 95%** (v1's and CR-S3's threshold; `fold.md` Check 2b). It is checked at sampled positions along
  both walls and at the crate, at all four yaws. Proved by deletion: with the cut off, the yaws facing a wall fail.

## 3. Input to intents (T2; world §3.3 has the messages)

| Input | Sends |
|---|---|
| W, A, S, D | `move {seq, dir}` on change, one of 8 vectors ((1000, 0), (1000, 1000), …), camera-relative on screen, world-frame on the wire; stage 1 canonicalises (T7) |
| Left click on floor | `move_to {seq, target_mm}` from the pick (§5.6); the route is drawn from `path_mm` |
| F on a fuel surface | `kindle {seq, point_mm, duration_ticks}`; no region (the server derives it) |
| Space; `,` and `.` | `time {pause \| resume}`; `time {set_scale}`, over presets 0.25–50 (client UI; the server checks only its range) |
| Q, E, wheel | none: camera only |

- **Integers on the wire:** values are cast with `int()` before `JSON.stringify`, which writes a float as `5500.0`
  (WT-S11) [ran].
- **Rotation with a key held** re-sends `dir` computed at the target yaw. **Focus loss** sends `move {dir: null}` on
  `NOTIFICATION_APPLICATION_FOCUS_OUT` (CR-N3).
- **Host-only controls:** the time controls are hidden for a non-host role; the server refuses them anyway.
- **The HUD** shows the requested and effective scale, and "dilated" when they differ.
- **Targeting is shown by shape:** an outline on the hovered fuel region, a marker on a live pilot (CR-N6).

### 3.1 What the client may and may not do (T9)

| May (visual only) | May not (feeds back) |
|---|---|
| Interpolate poses; animate from `facing` and motion | Move the drawn body by its own collision |
| Tween the camera; cut-away; bloom; flames | Send positions, paths, waypoints, a region or an actor |
| Cross-fade `surface_glow` between frames | Send intents at frame rate or on a timer |
| Pick a point (the server re-validates it) | Put its own clock into anything it sends |

- **Interpolation buffer:** 100 ms of wall time, keyed on world tick, one received sample behind (CR-N5, WT-N4).
- **Latency at 1× (derived):** 0–100 ms to the next tick, plus the 100 ms buffer, plus a 17 ms frame: about 170 ms
  mean and 220 ms worst. Measured in the playtest.

## 4. The wire, as the client reads it (client protocol layer)

### 4.1 Server → client messages

| Message | Carries |
|---|---|
| `welcome` | `session`, `role`, the world config, `shape`, the channel catalogue, the region map, 1-based archetype and item lists, `regions_version`, the time state |
| `regions` | new region-map entries and the new `regions_version`, sent before the first frame that uses them (DC-B1) |
| `tick` | JSON with integer columns only (DC-S9): `tick`, scales, paused; the actor and pilots tables (world §2.2); events since the last delivery; `path_mm` for each actor whose `path_version` changed |
| cell frame (binary) | `[u32 header length][JSON header][arrays]`, little-endian; the header has `protocol`, `kind`, `tick`, `shape: [nz, ny, nx]`, `regions_version`, the catalogue hash, and per array name, dtype, offset and size |
| `intent_result`, `time_decision`, `error` | world §3.3, §3.4 |

- **The catalogue** gives each channel's `unit` (from the closed vocabulary), `dtype`, and `scale` and `offset` as
  integer rationals (`scale_num` / `scale_den`), so 975/255 needs no float format (DC-N5).
- **The catalogue hash** uses boundaries §6.3's one canonicaliser, in the core's checks. The region map is outside the
  hash, so `imagine` doesn't churn it.
- **The decoder refuses** a frame whose `regions_version` is ahead of its map, or whose hash differs from `welcome`'s.
- **JSON numbers read back as floats** [ran]: integers from `tick` or a frame header are cast with `int()`; one over
  2^53 is refused.
- **Events accumulate per session** until delivered, bounded at 256 `[engineering]`. An overflow forces a resync: the
  server sends a full `tick` state and the client requests `snapshot`. State tables carry everything an event
  announces, so a skipped tick at 20× loses nothing (DC-S4).
- **Cell frames** go only on cells' version change, at most `snapshot_hz`, plus a `snapshot` reply after `welcome`
  and after a reconnect (WT-S6).

### 4.2 Channels

| Channel | dtype | Meaning (world §5) | Godot upload |
|---|---|---|---|
| `material` | u8 | material id | `FORMAT_R8` |
| `region` | u16 | `region_id` itself, never reused (world_model §5, F10; DC-B1) | `FORMAT_RG8`; id = r + 256·g via `texelFetch` |
| `crack` | u8 | 1 − integrity; a bed cell's charred-or-burned fraction | `FORMAT_R8` |
| `surface_glow` | u8 | the envelope-layer skin temperature of the cell's exposed faces, offset 525 °C, scale 975/255 °C | `FORMAT_R8` |
| `burning` | u8 | the burning fraction of the cell's fuel surface | `FORMAT_R8` |
| `temperature_c` | f16 | cell-mean temperature, a debug view kept by choice (WT-N8) | `FORMAT_RH` |

- **Frame size (derived):** 230,400 × 8 B = **1,843,200 B** plus the header. The gate is Σ(dtype bytes) × cells plus
  a header bound, taken from the registry.
- **Fixtures** (step 7) cover non-default scales, a frame after an `imagine` (a new region), and an asymmetric
  fixture for the axes.

### 4.3 Buffers and the transport

- **`inbound_buffer_size` = 4 MiB,** set before `connect_to_url` (the default is 65,535 [ran]).
- **`max_queued_packets` = 64** (the default is 4,096 [ran]).
- **The server's side:**
  - it refuses at `join` a shape whose frame exceeds a `data/server/` client cap of 3.5 MiB;
  - it sends a new frame only after the previous one has drained;
  - it keeps inbound `max_size` at 64 KiB, with a test for the 1009 close (TB-7, WT-S12).
- **Head-of-line blocking:** a `tick` queued behind a 1.84 MB frame waits on the order of a millisecond on localhost
  (*to measure*). The 100 ms buffer absorbs it.

## 5. The one shader

### 5.1 Raymarch the cell volume

| Option | Per update | Verdict |
|---|---|---|
| Greedy meshing in GDScript | remeshing 230,400 cells at 2 Hz, likely hundreds of ms (*to verify*), or a C++ GDExtension | no |
| Marching cubes | the same, or compute shaders; smooth surfaces blur the cells the cracks are drawn on | no |
| **Voxel raymarch (DDA), one fragment shader** | **an upload** | **yes** |

- **Geometry:** a `MeshInstance3D` with a `BoxMesh` over the solids' bounding box (top at z = 4.4 m) and a
  `ShaderMaterial`.
- **Traversal:** Amanatides–Woo (1987) steps cell by cell to the nearest boundary, until it reaches a solid, uncut
  cell. The crossed face gives the normal. Cells are read with `texelFetch` at the integer index [ran].
- **One concern per `.gdshaderinc` include** (AR-N2): traversal, cut-away, crack, lighting, emission, and the ID and
  cell-index debug passes.
- **A fuel-bed cell** draws as solid while it has fuel left. Its burning is shown through `burning` and
  `surface_glow`, not as a see-through slat pattern, a Phase 1 simplification.

### 5.2 Cost (CR-S2)

- **A floor ray** from z = 4.4 m at 40° elevation and 45° yaw crosses 34 + 34 + 40 = **108 cells** (derived: 4.0/0.643
  = 6.22 m, 3.37 m in each of x and y). A mean of 60–80 steps across the golden view gives 55–75 M texel reads per
  frame.
- **Empty-space skipping:** an R8 occupancy texture of 4 × 4 × 4-cell bricks (30 × 10 × 12 = 3,600 B), the seventh
  upload per frame. The cut test runs only inside occupied bricks.
- **The laptop tier** renders at `scaling_3d_scale` 0.5 [ran].

### 5.3 Depth, lighting, glow, flames

- **Depth (Compatibility):** `DEPTH = ndc.z * 0.5 + 0.5`, with ndc = clip.xyz / clip.w and clip = `PROJECTION_MATRIX *
  VIEW_MATRIX * hit` [ran]. It sits behind `#if CURRENT_RENDERER == RENDERER_COMPATIBILITY` [ran]. A renderer golden
  has a capsule half inside a wall (CR-S1).
- **Lighting** (`render_mode unshaded`): a fixed key light, three-tone face shading, neighbour AO, a fixed night
  ambient. No dynamic shadows.
- **Glow:** T = offset + scale·g, both from the catalogue. Emission = 4.0 × (T_K/1773)⁴ in HDR `[engineering]`, a
  **stylisation**: T⁴ is total radiance, not visible radiance (PH-N2, CR-N4). Hue goes dull red → orange →
  yellow-white. Ember envelopes near 920 °C (world §5.3) read bright yellow-orange. Output above 1.0 drives glow
  [ran].
- **Flames from `burning`:** emissive flicker plus `GPUParticles3D` at burning cells. Visual only, and off in goldens.

### 5.4 Crack changes shape (EX-S10, CR-S4)

- **The pattern:** each cell carries 3-D Voronoi edges from an integer hash of its index. With c = `crack` in [0, 1],
  points within w = max(0.02 m × c, the metres that 0.75 px spans at the current zoom) of an edge are empty when
  c > 0, so a groove is never narrower than 1.5 px `[engineering]`. The march goes `crack_substeps` into the cell.
  Fissure walls darken with depth, and the normal tilts towards the edge.
- **Worked numbers (derived):** at 72 px/m, c = 0.25 gives 0.72 px from the metre term, so the floor applies. At
  c = 1 the groove is 2.9 px.
- **Testing:** char darkens the albedo too, so the tests (§6.4) measure luminance and edges over cracked cells only.
  The deletion proof disables carving with the darkening kept.

### 5.5 Tiers (client data, AR-S7)

A typed `Resource` in `client/game/tiers/`:

| Tier | `scaling_3d_scale` | Crack substeps | Glow sampler | Bloom | AO | Flame particles |
|---|---|---|---|---|---|---|
| laptop | 0.5 | 2 | nearest | off | off | 64 |
| rig | 1.0 | 4 | linear | on | 4-tap | 256 |
| max | 1.0 | 8 | linear | on | 6-tap | 1,024 |

Filters are compile-time hints [ran], so the glow sampler is a `#define` variant (CR-N1, EX-N3).

### 5.6 Picking (CR-S6)

- `dda.gd` runs the same traversal on the CPU over `material` and `region`, with the same cut parameters, at most 208
  steps per click. Cracks are ignored.
- It returns a point in mm on the hit face, which the server re-validates.
- A unit test checks that the pick agrees with a shader-equivalent reference on a grid of screen points.

## 6. Golden screenshots (B7)

### 6.1 Method

- **From frame fixtures, never a live server.** `client/tests/golden.tscn`:
  - sets the golden camera;
  - turns off particles, animation and cross-fade;
  - refuses a headless display, where `frame_post_draw` never fires [ran];
  - captures after the first `await RenderingServer.frame_post_draw` [ran] and asserts `get_image() != null`;
  - saves the PNG.
- **Frame files are B3 wire fixtures** (WT-N6).
- **Renderer goldens** are hand-built frames: an asymmetric fixture, a cracked block, a glowing block, and a capsule
  half inside a wall.
- **Scenario goldens:**
  - G1 at tick 70, cold;
  - G2 when the charred area reaches 4× world §6.3's threshold;
  - G3 at `t_glow` + 60 s;
  - G4 at `t_gone` + 10 s;
  - G5 at tick 70 from the south, with `wall_south` cut.

  That is five per tier.
- **Staleness** (EX-S13): only `scripts/update_goldens.sh` (to be written) writes frame files. A `slow` test compares
  the regenerated digests with the committed ones.

### 6.2 Tolerance

- **Pass criteria:** CIE76 ΔE, computed in numpy. Mean ≤ 1.0, 99.5th percentile ≤ 4.0, and no 4-connected blob over
  64 px with ΔE > 10 `[engineering]`.
- **Deletion proofs:** disabling the carving fails G2; zeroing the emission fails G3; swapping the depth formula fails
  the capsule golden.

### 6.3 Same apart from detail

Each tier's frame is box-filtered to 160 × 90, then laptop and max are each compared against rig:
- mean ΔE ≤ 3.0;
- 99th percentile ≤ 10;
- ID-mask areas (crate, glowing region, player) within 15% `[engineering]`.

### 6.4 Never colour alone

- **Debug passes:** region and actor ids, from the `region` channel and the actor table, and a cell-index pass for
  cracked cells.
- **G2 against G1,** in L* over cracked cells only: a mean difference ≥ 8, and ≥ 2× the Sobel edge density.
- **G3 against G1:** the glowing pixels are ≥ 15 L* brighter `[engineering]`.

### 6.5 CI and machines (T12; CR-B3, EX-B3)

- **A required Linux CI job,** added in step 2 with one renderer golden. It runs in `ci/godot-golden/Dockerfile`:
  - the base image pinned by digest;
  - packages pinned by version from a dated Ubuntu snapshot (the archive drops old versions);
  - Godot 4.7.2 checked by SHA-256;
  - `LIBGL_ALWAYS_SOFTWARE=1`, `GALLIUM_DRIVER=llvmpipe`, and `LP_NATIVE_VECTOR_WIDTH=256` (llvmpipe's name reports it [ran]).
- **`scripts/golden_run.py`** imports, then runs, with the gate's timeout and scans: `xvfb-run -s "-screen 0 1280x720x24" godot --rendering-driver opengl3 --rendering-method
  gl_compatibility --fixed-fps 60 --resolution 1280x720 --path client res://tests/golden.tscn`. Linux has no
  surfaceless mode.
- **Golden paths** are `client/tests/goldens/compat-llvmpipe-mesa<package>-llvm<v>-godot<v>/<tier>/`, keyed from the
  run's log. A new build regenerates them in a commit of its own.
- **The Mac is advisory:** `prepush` runs the B6 gate, plus the tier-agreement and greyscale checks when a GPU
  context exists. B7 passes only when the CI job is green.
- **Updates go through** `scripts/update_goldens.sh <reason>`: it refuses a dirty tree, renders in the CI image, and
  writes a diff image for each golden.

## 7. The Godot project

### 7.1 Tree (boundaries §2.1)

```
client/addons/engine/            engine client half (Apache-2.0)
  protocol/frame_decoder.gd      RefCounted: header checks, catalogue, regions, slicing
  protocol/net_client.gd         WebSocketPeer, hello, routing
  render/cell_volume.gd          textures, uniforms
  render/cell_volume.gdshader    + render/*.gdshaderinc
  render/dda.gd                  RefCounted: the pick
client/game/                     this game (rights reserved)
  main.tscn                      Main (Node3D)
    ├── Net (Node)
    ├── World (Node3D) → CellVolume (MeshInstance3D: BoxMesh + ShaderMaterial), Actors → Actor_<id>
    │     (MeshInstance3D: CapsuleMesh), Path (MeshInstance3D: ImmediateMesh), Flames → GPUParticles3D
    ├── CameraRig (Node3D, yaw) → Pitch (Node3D) → Camera3D
    ├── WorldEnvironment
    ├── IntentInput (Node)
    └── Hud (CanvasLayer) → Control
  tiers/, cutaway.tres           client data
client/tests/                    runner, unit tests, goldens
```

**Engine whys:**
- `Node3D` is anything with a 3-D transform.
- `MeshInstance3D` draws one mesh.
- `CanvasLayer` draws UI over the 3-D view.
- `WorldEnvironment` holds post-processing.
- `Net` is a plain child rather than an autoload, so dependencies show in the tree.
- `RefCounted` scripts hold logic that can be tested without a scene.

### 7.2 GDScript

- **Every warning is set to Error** unless `client/WARNINGS.md` lists a reason, and a test reads `project.godot`
  (CR-S7). The 4.7.2 defaults leave `unsafe_void_return`, `narrowing_conversion`, `integer_division`,
  `unused_variable` and `shadowed_variable` at Warn, and exempt `res://addons` (the engine half), so
  `directory_rules` is `{}` [ran].
- **Returned `Error` values are checked and reported,** never bound to `_`. `return_value_discarded` fires on
  `PackedByteArray.resize` and `Image.save_png` [ran].
- **GDScript over C#:** no .NET toolchain, and parse checks need no build.

### 7.3 The B6 gate (CR-B1)

`scripts/godot_check.py`, run by `prepush`:
- imports a fresh copy first, so `class_name` resolves [ran], and fails if the import creates or rewrites a file;
- wraps each call in `subprocess.run(timeout=120)`;
- fails on `SCRIPT ERROR`, `Parse Error` or `ERROR:`;
- loads every `.gd` and fails on one that is null or not instantiable: a broken script loads non-null [ran];
- runs `client/tests/run.gd`, which awaits each test and fails one that checks nothing, and requires
  `client-tests: PASS <n> tests` as the last line and exit 0.

Fixture projects in `tmp_path`, never under `client/` (`tests/test_godot_gate_fixtures.py`), prove each check by
deletion. Godot's exit status is never trusted alone.

### 7.4 Renderer (T8)

**Compatibility (OpenGL 3.3).**
- The shader is unshaded, so Forward+ buys little.
- Compatibility runs on integrated GPUs and on CI's llvmpipe.
- Its glow works with unshaded HDR output [ran].
- Windows may draw through ANGLE (`fallback_to_angle`); that is still Compatibility.

### 7.5 Connecting

- **The token** arrives by environment variable (`OS.get_environment`) or a 0600 file, never argv (realtime §5).
- **The connection** is `WebSocketPeer.connect_to_url("ws://127.0.0.1:<port>")` [ran], polled each `_process`.
  `was_string_packet()` separates JSON from frames [ran].
- **No `Origin` header:** `handshake_headers` is never set. A Python listener test fails if the header appears.
- **The order** is `hello`, then `welcome`, then `snapshot`. Anything unknown is refused loudly, with the reason shown.

## 8. Client budgets (EX-S12, CR-S5)

Client meters take the minimum of N ≥ 50 `Time.get_ticks_usec()` intervals, and every meter must read > 0.

| Meter | Target | Status |
|---|---|---|
| Decode + upload, all seven textures (six channels, `region` at 2 B/cell, bricks) | ≤ 3 ms (1.4–2.4 ms from 173–294 µs per channel-equivalent [ran]) | B5, gated in CI |
| First upload | warmed on `welcome` (the first `update` took 10.9 ms [ran]) | test |
| Frame time, rig and laptop tiers, golden view | ≤ 16.7 ms with `--disable-vsync` | reported, as the uncapped minimum frame interval: the GPU meter reads 0 [ran] |
| `tick` delay behind a frame | ≤ 5 ms | reported |
| Input to photon | ≤ 220 ms worst | playtest |

## 9. Probe list (step 2; EX-S14)

| Item | Probe | Context | If it fails |
|---|---|---|---|
| No `Origin` | Python listener | headless | refuse at the server regardless |
| Integers from `JSON.stringify` | `int(5500)` → `5500` | headless | encode by hand |
| `FORMAT_RG8` and `texelFetch` for u16 ids | upload, read back | windowed | two R8 textures |
| `frame_post_draw` capture | the golden scene under Xvfb | CI image | wait N frames, assert non-null |
| llvmpipe with a fixed vector width | one golden on two runner CPU types | CI image | one runner class |
| GPU time | `--gpu-profile`, the GPU meter (both read 0 [ran]), uncapped frame time | windowed | rows stay "reported" |
| Keys on focus loss | key held, focus out | windowed | the client's own stop covers it |
| `class_name` on a fresh checkout | `--import`, then `-s run.gd` | headless | commit the import cache |
| Partial texture update | one slice changed | windowed | whole-texture (cheap) |

Results: `research/godot_probes.md`; an upgrade reruns `tools/godot_probes/`. The two-CPU row stays open (CR-B3).

## 10. Open questions for the owner

None open. v2's five were answered as recommended (T8–T12).

## 11. What this does not settle

- Forward+ and dynamic shadows, which wait for Phase 2 light.
- Delta frames, zstd and partial uploads.
- Drawing the bed's slats.
- Gamepad, audio, menus and client-side saves.

## 12. Requirements by plan step

| Requirement | Step |
|---|---|
| `client/` skeleton; `project.godot` (renderer, warnings, its test); `godot_check.py` and its fixtures; the CI golden job, its image and one renderer golden; §9's probes | 2 |
| The decoder against wire fixtures (scales, hash, `regions`, a post-`imagine` frame, header refusals); `tick` encoding; event accumulation and resync; `net_client.gd`; JSON integer reads (§4.1); buffers and the server's caps; the `Origin` test | 7 |
| The shader and its includes, bricks, depth golden, crack and glow, picking, cut-away and its 95% test, input mapping, HUD, tiers, the scenario goldens, staleness digests, `update_goldens.sh`, budgets | 8 |
