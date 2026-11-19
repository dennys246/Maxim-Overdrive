# Design review: tile and client (step 0d), Client and rendering lens

Reader: Client and rendering. Design: `docs/design/tile_and_client.md` at `f6afd66` (draft). Also read: CLAUDE.md,
`docs/code_review.md` (lens row, Design reviews), `docs/standards_backlog.md` B6/B7, `docs/architecture.md`
(Transport), `src/maxim_overdrive/world/world.py::snapshot`.

**Probes run** against `/Applications/Godot.app` 4.7.2.stable.official.ed1daf0bf on the owner's M2. They were
throwaway scripts in the session scratchpad, deleted afterwards and not committed:
1. `--doctool` API dump, checked for every class, method, member and constant the design names.
2. A project with the design's seven warnings at level Error, run with `--check-only` and `-s`, recording exit codes.
3. `--headless` viewport capture.
4. A windowed Compatibility render on `opengl3`: an `ImageTexture3D` at 120 × 40 × 48 in R8 and RH, `create` and
   `update` timed; a shader with `filter_nearest`/`filter_linear`, `repeat_disable` and `texelFetch`; `DEPTH`
   writes against cubes in front of and behind the written plane; unshaded `ALBEDO = 4.0` with `Environment` glow on
   and off; `scaling_3d_scale` 1.0 against 0.25.
5. `viewport_get_measured_render_time_gpu` over 120 frames, on Compatibility and on Forward+/Metal.

Each claim below is tagged **[ran]** or **[memory]**.

**Verified real in 4.7.2 [ran]:**
- `ImageTexture3D.create(format, w, h, d, use_mipmaps, Image[]) -> Error` and `update(Image[]) -> void`
- `Image.create_from_data` (static), `FORMAT_R8`, `FORMAT_RH`, `PackedByteArray.slice`
- `WebSocketPeer.inbound_buffer_size` (default 65,535), `max_queued_packets` (4,096), `handshake_headers`,
  `was_string_packet`, `connect_to_url`
- `Camera3D.PROJECTION_ORTHOGONAL` and `size`
- `Viewport.scaling_3d_scale`, which works in Compatibility: bilinear, 2 → 10 edge steps per row at 0.25
- `RenderingServer.viewport_set_measure_render_time` and `viewport_get_measured_render_time_gpu` exist
- `--fixed-fps`, `--write-movie`, `--check-only`
- All seven warning names in §9.2: `untyped_declaration`, `inferred_declaration`, `unsafe_property_access`,
  `unsafe_method_access`, `unsafe_cast`, `unsafe_call_argument`, `return_value_discarded`

Upload fits the budget: 48 slices take 85–260 µs; `update` takes 160–230 µs per channel. Unshaded output above 1.0
does drive Compatibility's glow, which settles §6.1's and §9.3's "to verify". `--headless` draws nothing: the dummy
texture storage makes `get_image()` return null.

Counts: 3 BLOCKER, 7 SHOULD-FIX, 7 NIT.

## BLOCKER

### CR-B1. The B6 gate cannot fail on exit codes: Godot exits 0 on parse errors and hangs on runtime errors

`tile_and_client.md::§9.2`; B6.
- **What I ran [ran]:** a script with an untyped `var` and the design's warnings set to Error.
  - `--check-only -s bad.gd` prints `SCRIPT ERROR: Parse Error … (Warning treated as error.)`, then
    `Failed to load script`, and **exits 0**. `-s bad.gd` without `--check-only` also exits 0.
  - A `class_name … extends RefCounted` file, checked the same way, also exits 0.
  - A `SceneTree` script that hits a runtime error (an out-of-bounds index) before `quit()` prints the error and
    **keeps running**. I killed it after 6 s.
  - `quit(3)` does exit 3, so an exit code is only trustworthy when the script got as far as calling `quit`.
- **Failure scenario:** the gate runs `godot --headless --check-only -s` over every script and the test runner
  through `-s`, then trusts `$?`. An untyped declaration lands and the gate prints PASS. A test that indexes past an
  array end hangs CI until the job timeout, with no failure named. This is a guard that cannot fail, which
  CLAUDE.md makes a BLOCKER.
- **Fix:**
  - The gate wraps each Godot call in a Python `subprocess.run(timeout=…)`. macOS has no `timeout(1)`; I checked.
  - It fails on any `SCRIPT ERROR`, `Parse Error` or `ERROR:` in the combined output.
  - It requires the runner's sentinel line (`client-tests: PASS <n> tests`) as the last line, and `run.gd` ends
    with `quit(0 if all passed else 1)`.
  - The parse check loads every `.gd` file and fails on any `load()` that returns null. A warning promoted to Error
    becomes a load failure, as I saw.
  - Prove it by deletion: commit one fixture of each kind (an untyped script, a runtime-error test, a failing
    assert) and watch the gate go red on each.
  - Record in §9.2 that Godot's exit status is not a test result.

### CR-B2. The client has no region identity, so "F on a region", the ID pass and the cut-away can't be built

`tile_and_client.md::§4.3`, `§6.1`, `§8.4`, `§3.2`.
- **The gap:** the client receives `material`, `crack`, `glow` and `temperature_c` (§5.1), plus a palette per
  material id. `crate` and `crate_control` are both `wood` (id 4), and the floor and walls are both `concrete`.
  - §4.3 sends `act {region, …}`, but a CPU DDA pick through the material bytes yields "wood at cell (i, j, k)",
    never `crate`.
  - §8.4 "renders region and actor ids as flat colours" with no region-id input.
  - The §8.3 ID-mask areas and the §3.2 player-visibility test depend on that pass.
- **Failure scenario:** step 8 reaches the exit action and the client cannot fill `region`. It ends up guessing
  "the nearest wood", which is the client deciding a region, forbidden by §4.4, or hard-coding `crate`. Every
  golden check that uses the ID mask is unimplementable.
- **Fix:** a `region` u8 channel in the frame, with `welcome` mapping index to name; 230 KB more, and it is also
  what §11's `bincount` uses. Or put each region's authored AABB in `welcome`, but that breaks once cells burn or
  imagined objects arrive. The pick returns (point, region index), and the server re-validates as already written.
  This is a Wire item for step 7 too.

### CR-B3. Goldens on CI have no specified way to get a rendering context

`tile_and_client.md::§8.1`, `§8.5`; B7.
- **What is settled [ran]:** `--headless` gives a null image. "Not `--headless`" is right but incomplete.
- **The gap [memory]:** Godot 4's Linux display servers are X11 and Wayland; there is no surfaceless/EGL offscreen
  mode. On a CI runner, Compatibility with llvmpipe needs a display server (Xvfb or a headless Wayland
  compositor) plus `LIBGL_ALWAYS_SOFTWARE=1`.
- **The second gap [memory]:** "llvmpipe, identical across runners" is only true for a pinned Mesa build.
  llvmpipe's JIT picks its vector width and FMA use from the host CPU, and GitHub's runner pool mixes Intel and
  AMD.
- **Failure scenario:** step 5 writes the golden job and it fails to open a window. Or it passes on one runner and
  shows ΔE noise on another, and the "fix" is a loosened tolerance.
- **Fix:**
  - §8.5 names the container image with its Mesa version pinned and `LP_NATIVE_VECTOR_WIDTH` fixed.
  - It names `xvfb-run -s "-screen 0 1280x720x24"` (or a chosen alternative) and
    `--rendering-driver opengl3 --rendering-method gl_compatibility --fixed-fps 60 --resolution 1280x720`.
  - The goldens path keys on the Mesa version (`<renderer>-<driver>-mesa<ver>`).
  - The golden scene asserts `get_image() != null`, because under the dummy renderer
    `get_current_rendering_method()` still reports `gl_compatibility` [ran]. Waiting a few frames is not enough:
    capture after `await RenderingServer.frame_post_draw` [memory].

## SHOULD-FIX

### CR-S1. The `DEPTH` formula is now known, and it differs by renderer

`tile_and_client.md::§6.1` (Depth).
- **What I measured [ran]:** in Compatibility, `DEPTH = clip.z / clip.w` (clip = `PROJECTION_MATRIX * VIEW_MATRIX
  * hit`) draws a cube behind the written plane in front of it. `1.0 - ndc` and `(1.0 - ndc) * 0.5` do the same.
  Only `DEPTH = ndc.z * 0.5 + 0.5` composites correctly.
- **The renderer macro [ran]:** `#if CURRENT_RENDERER == RENDERER_COMPATIBILITY` compiles and selects it.
- **Forward+ [memory]:** it wants plain `ndc.z` (reversed-Z). My Forward+/Metal readback came back black, so that
  is inconclusive.
- **Failure scenario:** the obvious Vulkan-style formula hides the player's capsule inside walls or draws it
  through them. No current golden sets an occluder deliberately in front of and behind the player, so nothing
  catches it.
- **Fix:** write the verified formula behind the macro, and add a renderer golden with a capsule half inside a
  wall (the probe's pattern).

### CR-S2. "About 40 steps typical" is not what the geometry gives; the raymarch cost is 2–3× higher

`tile_and_client.md::§6.1` (Cost).
- **Derivation:** a floor ray at 40° elevation and 45° yaw, d = (0.542, 0.542, −0.643), falls 4.4 m from the box
  top to the floor. That is t = 6.85 m, or 3.71 m in each of x and y. It crosses 37 + 37 + 44 = **118 cells**.
- **Where it applies:** without the cut no floor is visible at all (the wall's shadow is 3.37 m across the alley
  > 3.2 m). So every floor pixel the player sees is one of these long rays through cut cells. Wall tops and outer
  faces take 1–5 steps.
- **The honest estimate:** the golden view (crate-centred, cut region 4 m) is bimodal, and a mean of 60–80 is
  plausible: 55–75 M texel reads per frame, not 37 M. Each step also evaluates the three-part cut test.
- **Failure scenario:** the "laptop, integrated GPU ≤ 12 ms" budget is set from the low estimate and the first
  measurement blows it. Or the B5 "first measurement + 20%" bakes in a slow shader with no recourse named.
- **Fix:**
  - Restate the cost with the floor-ray figure.
  - Start rays at the top of the solid bounding box (z = 4.4 m), not the extent.
  - Name the standard remedy now: a coarse occupancy texture (an R8 at 4 × 4 × 4 bricks, 1/64 the size, uploaded
    with the frame) so empty bricks are skipped in one step. This is ordinary DDA empty-space skipping and still
    needs no compute shaders.

### CR-S3. The cut-away fails its own ≥ 95% visibility test at the crate, and hides distant fire

`tile_and_client.md::§3.2`.
- **The stump height:** stumps reach 1.1 m above the feet: cells whose bottom is ≤ 1.0 m are kept, and at 0.1 m
  that tops out at 1.1 m. The design's ignite position puts the body axis 0.7 m from the north wall's inner face.
  - With the camera on the north side, the sightline crosses the wall 0.7/sin 45° = 0.99 m out and rises 0.83 m by
    then.
  - Body points below about 0.27 m are therefore behind the stump: 15% of a 1.8 m body.
  - Along a wall (axis 0.25 m from the face) it is about 0.8 m, or 44%.
- **The "≥ 95% at all four yaws" test** fails at two yaws on day one, or gets loosened.
- **Distant fire:** cells more than 4 m from the player stay whole. From the spawn (5.4 m from the crate) with the
  camera on the north side, the uncut north wall beside the crate (0.4 m from it) hides the crate entirely. "Watch
  it burn" works only from within 4 m.
- **The denominator is undefined:** the test does not say visible relative to what.
- **Fix:**
  - Cut every wall cell whose outward normal faces the camera and that lies in the view frustum (walls-down, as
    the cited Sims mode does), not a 4 m disc.
  - Lower the stumps within about 1.5 m of the player (to 0.2 m), or define visibility as pixels of the player's
    ID mask with world geometry above the stump plane removed.
  - Test at sampled positions along both walls and at the crate, not only at G5.

### CR-S4. Cracks at `t_crack` are sub-pixel, so the greyscale test fails or drives tuning to the test

`tile_and_client.md::§6.2`, `§7.3`, `§8.4`.
- **Groove width:** at the golden view (10 m over 720 px, 72 px/m) a groove is 2 × 0.02 m × c wide. At c = 64/255
  (the `t_crack` threshold) that is **0.72 px** on rig and 0.36 px on laptop (scale 0.5).
- **Coverage:** G2 is taken when only ≥ 8 cells have reached that threshold. The crate is about 43 × 60 px, roughly
  2,500 px; 8 cells' faces are about 390 px, and grooves cover a fraction of those.
- **The mean shift (derived)** is about 2 L* against the required ≥ 8.
- **Failure scenario:** G2 fails, or the carve width is inflated until the test passes. Laptop cracks alias and
  flicker, and the tier-agreement area check disagrees.
- **Fix:**
  - Give fissure width a screen-space floor (≥ 1.5 px at the current zoom) as well as its metre scale.
  - Compute the §8.4 greyscale deltas over the pixels of the cracked cells only, which needs a cell-index debug
    pass like the ID pass.
  - Or take G2 at a crack state the physics reaches with margin, with the threshold measured first.

### CR-S5. The GPU-time meter reads 0.0 on the owner's Mac

`tile_and_client.md::§10`.
- **What I ran [ran]:** with `viewport_set_measure_render_time(root rid, true)`,
  `viewport_get_measured_render_time_gpu` returned `0.0` at frames 40, 80 and 120. This held on Compatibility
  (OpenGL 4.1 over Metal) and on Forward+/Metal; the CPU counterpart returned plausible values (0.06–0.21 ms).
  This may be my call pattern, but as written the two GPU budget rows can't be measured.
- **Fix:** step 2's probe either makes it read non-zero or replaces it. One option is `--gpu-profile`, which
  exists [ran]. Another is uncapped frame time with `--disable-vsync`, minimum of N, on a fixed scene. Until then,
  mark the GPU rows *unmeasured*, not B5.

### CR-S6. The CPU pick must apply the cut, or clicks land on invisible walls

`tile_and_client.md::§4.2`, `§6.1`.
- **Failure scenario:** "the same DDA on the CPU" says nothing about the cut-away or crack carving. A click on floor
  seen through a cut wall hits the cut wall cell first. `move_to` targets the wall, and the server snaps or answers
  `unreachable`.
- **Fix:** the pick lives in `dda.gd` and takes the same cut parameters (player position, forward, radius, height).
  A unit test asserts that the pick and a shader-equivalent reference agree on a grid of screen points. Cracks
  can be ignored for picking, which should be stated.

### CR-S7. The warning list is real but partial

`tile_and_client.md::§9.2`.
- **The default levels [ran]:** the 4.7.2 defaults leave `unsafe_void_return`, `narrowing_conversion`,
  `integer_division`, `unused_variable`, `shadowed_variable` and other typing-adjacent warnings at Warn (1).
- **Why it matters:** CLAUDE.md says "typed-GDScript warnings as errors", and a Warn never fails the gate (CR-B1).
  `return_value_discarded` at Error fires on `PackedByteArray.resize` and `Image.save_png` [ran]. The tempting
  `var _e: int = …` dodge is a silent swallow under the repo's own rule.
- **Fix:** set every warning to Error unless a listed reason says otherwise. Have a test read `project.godot`
  against that list. State that returned `Error` values are checked and reported, never bound to `_`.

## NIT

### CR-N1. The sampler hints are compile-time

`§5.4`, `§6.1`. `filter_nearest` and `filter_linear` are uniform hints [ran], so "glow filter per tier" needs two
uniforms or a `#define` variant, not a runtime switch. Use `texelFetch` with the DDA's integer cell index for
`material` and `crack` [ran, works in Compatibility]; that removes `round(r·255)` and boundary off-by-ones.

### CR-N2. The cut-away pops

`§3.2`. "No popping" is untrue. As the player moves 0.1 m, cells at the 4 m rim and the −0.3 m plane flip between
stump and full height. During the 0.25 s yaw tween, f sweeps and whole wall runs flip. Use the target yaw's f at
tween start; CR-S3's walls-down rule removes the rim.

### CR-N3. Camera-relative WASD during a tween and on focus loss

`§4.1`. The heading must be recomputed and re-sent when the yaw changes with a key held, using the target yaw (mid
tween the yaw is not 45° + k·90°). Send `move {heading: null}` on `NOTIFICATION_APPLICATION_FOCUS_OUT`; whether
Godot releases held keys on focus loss is [memory].

### CR-N4. Stefan–Boltzmann is not visible brightness

`§6.3`. T⁴ is total radiant power. Visible luminance from 800 K to 1,773 K rises by orders of magnitude more
[memory, Planck × V(λ)]. T⁴ is a fine `[engineering]` stylisation, but label it one rather than physics. Also state
the emission scale, since §8.4's "≥ 15 L*" is undefined without it.

### CR-N5. Interpolation is in ticks, not wall time

`§4.4`, `§5.3`. "One tick behind" at dial 0.25 is 400 ms of lag, and at 10× the actor throttle (30 Hz) spans 3.3
ticks. Specify the interpolation buffer in wall time (about 100 ms), keyed on world tick, and state latency per dial
setting.

### CR-N6. Some states are shown by colour only

`§4.3`, `§8.4`. The hovered or targeted region for `F` and a live pilot have no specified visual. Give each a shape
(an outline, a marker), not a tint. Material identity rests on palette hue alone; that is acceptable as identity,
but say so.

### CR-N7. Smaller items

- **First upload hitch:** the first `update` after `create` took 10.9 ms [ran]; warm it on `welcome`.
- **Buffer sizing:** 4 MiB of `inbound_buffer_size` holds three frames. A client stall (macOS throttling an
  occluded window, [memory]) then fails the session on backlog, which §5.2 would misreport as "oversize". Size it
  to one frame plus headroom and have the server send latest-wins only after the previous frame drained.
- **`class_name` cache:** a fresh CI checkout has no `.godot/`, so `-s run.gd` needs `--import` first to resolve
  `class_name` [memory].

**Verdict:** not ready to build. Fold CR-B1–B3 (gate exit codes, region identity, a CI rendering context) and
re-derive the raymarch cost and cut-away before step 2 code.
