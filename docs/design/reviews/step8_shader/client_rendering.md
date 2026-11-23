# Step 8 shader: Client and rendering

Scope: `git diff 35a1702...HEAD` (c656c33, ce06d7b). I read the shader includes, the GDScript under `render/`, `render_stage.gd`, `golden.gd`, `cutaway_check.gd`, the tier, palette and cut-away resources, and §1–§8 of the design. I also:
- looked at all three committed goldens, with pixel crops and numpy scans;
- ported `find_hit`'s walk (entry axis, `walk_at`, `advance`, `skip_brick`, cut test; no carving) to float32 Python and compared it with a float64 reference DDA on the alley fixture, 30,000 rays at the golden camera with 2e-5 cell origin noise;
- ran headless Godot on a scratchpad copy of `client/` to check what the dummy renderer compiles and reports.

I edited nothing in the worktree and did not run the gate.

## Findings

### SHOULD-FIX: rig and max goldens record a hole in an uncracked wall
`client/addons/engine/render/traversal.gdshaderinc::skip_brick` / `cell_volume.gdshaderinc::find_hit` (cause not confirmed)

- **What:** pixel (543, 224) is pure (0, 0, 0) in both `rig/fire.png` and `max/fire.png`, and all 8 of its neighbours are (173 sum). It sits on wall_north's south face, well away from the crack patch, a box edge and the capsules.
- **Geometry:** unprojecting the pixel gives a ray that enters the top face at cell (67.4, 5.67, 48) and meets the wall face y = 36 at (37.05, 36, 12.01). Both y = 36 and z = 12 are brick boundaries, the double-boundary landing that the comment on `walk_at` names as the hard case.
- **Cause unknown:** the shader writes exactly 0 only when it discards: lit output is never 0, and the cell is uncracked. So the ray missed. My float32 port does not reproduce the miss (0 of 30,000 rays disagree with the reference), so the cause is something the port lacks: GPU float behaviour, `round`, or varying interpolation.
- **Why it matters:** the goldens now lock in a defect. On other GPUs the same walk will leak somewhere else, which shows as sparkle in play.
- **Fix:** add a debug "miss" pass that writes 1 where `find_hit` returns false inside the box, and assert it is empty over solid-backed pixels. Then find the leak, and re-record the goldens.

### SHOULD-FIX: on laptop the crack pattern turns into dark noise, and §6.4 runs only on rig
`client/addons/engine/render/crack.gdshaderinc::groove_half_width_m`; `scripts/golden_run.py::SHOTS`

- **The numbers:** laptop draws at render scale 0.5, so `pixel_m` = 10 m / 360 px = 0.0278 m. The floor is 0.75 px = 0.0208 m half-width, which is more than the largest metre term (0.02 m at c = 1). The Voronoi polygons are one cell (0.1 m ≈ 3.6 px) across, and each groove is about 4.2 cm of that.
- **Result:** in the laptop golden the crate and the wall_north patch read as near-uniform black speckle; I viewed the crops at 3×. The polygonal shape is gone, and crack severity has no shape signal at all: c from 0.25 to 1 draws identical grooves. Only the char darkening (colour) varies.
- **On rig:** the floor wins for c < 0.52 at the golden zoom, and for c < 0.62 at the default 12 m play zoom.
- **Rule:** CLAUDE.md says "cracks also change shape". §6.4's checks run only on `fire-rig*`, so nothing measures laptop.
- **Fix:** run the never-colour-alone checks per tier. Decide with the owner how the Voronoi spacing scales with pixel size: a feature lattice sized in pixels, or a cap on groove area.

### SHOULD-FIX: the 1.5 px groove floor is not met on foreshortened faces
`crack.gdshaderinc::groove_half_width_m`

- **What:** the floor is in metres per screen pixel, but a groove lies on a face that is foreshortened on screen.
- **Numbers:** top faces at 40° elevation compress by sin 40° = 0.64, so the narrowest on-screen groove is about 0.96 px. Vertical faces at yaw 45 compress by about 0.71, about 1.06 px.
- **Effect:** sub-1.5 px grooves shimmer under sub-pixel camera pans, which is the failure the floor exists to prevent.
- **Fix:** divide the floor by |n·d| for the hit face, using the face's normal and the ray. §5.4's worked numbers assume an unforeshortened face.

### SHOULD-FIX: carving has no depth bound, so grooves can see through solid cells, more often on low tiers
`crack.gdshaderinc::carve`, `cell_volume.gdshaderinc::find_hit`

- **What:** a cracked cell is declared empty when every point sample lands in a groove: 2 samples on laptop, 4 on rig, 8 on max. The ray then walks on. Voronoi boundaries are sheets that run through every cracked cell, so a ray nearly parallel to a sheet can pass the whole cracked thickness.
- **In the fixture:** the wall_north patch is cracked through its whole thickness (y 36–39) to the volume's north edge (ny = 40). Rays through it leave the volume and are discarded.
- **Evidence:** rig shows 3 pure-black pixels with bright neighbours in the patch and on the crate, and max shows 1.
- **Why it matters:** with a non-black background, or a body or mesh behind the wall, a c = 0.5 wall shows holes the server never reported, which misstates the world. Fewer substeps pass more cells, so the effect differs by tier.
- **Fix:** bound the groove depth in metres (for example a few × w, or `crack_substeps` cells). Treat a ray that passes all of it as hitting the fissure floor.

### SHOULD-FIX: a misspelt uniform name fails silently, and the unit tests cannot catch it
`client/addons/engine/render/cell_volume.gd::_param`, `client/tests/unit/render/test_cell_volume.gd`

- **Probe:** on 4.7.2 headless, `ShaderMaterial.get_shader_parameter("nope")` returns 3 after `set_shader_parameter("nope", 3)`. So `test_cell_volume`'s read-backs pass whatever the shader declares.
- **Scenario:** some defaults equal the fixture's values (`glow_scale_c` = 3.8235294, `glow_offset_c` = 525, `cell_m` = 0.1), so a typo there would pass the goldens too.
- **Fix is cheap:** `Shader.get_shader_uniform_list()` works headless. I printed all 20 uniforms for both variants, and today every `_param` name matches. A test should assert that each `_param` name is in that list.

### SHOULD-FIX: unknown material ids draw black or another material's colour, with no warning
`cell_volume.gd::use_palette`, `lighting.gdshaderinc::albedo_of`

- **What:** ids missing from the palette draw `Color.BLACK`, and ambient × 0 = 0, so the cells are invisible against the black background `RenderStage` now uses.
- **What:** ids ≥ 16 are clamped to `palette[15]` and drawn as that material.
- **Trigger:** step 7's vocabulary adds a material, or a palette name is misspelt. Solid cells silently vanish or show the wrong material. That is a quiet fallback, the swallow pattern the code rules ban.
- **Fix:** refuse, or `push_error`, when `ids` holds a name the palette lacks or an id ≥ PALETTE_SIZE. Use a loud debug colour, not black.

### SHOULD-FIX: no deletion proof was recorded for the depth formula
`cell_volume.gdshaderinc::fragment` (the DEPTH write)

c656c33 says "the depth swap needs the goldens: next commit". ce06d7b records no swap proof. §6.2 requires one ("swapping the depth formula fails the capsule golden"). The fixture does contain the half-buried body (actor 2's axis is on wall_north's face at y = 3.6 m), so the proof can be run. CLAUDE.md: "say so in the commit message".

### SHOULD-FIX: `MAX_STEPS` is sized for the alley only, and a larger snapshot truncates silently
`traversal.gdshaderinc::MAX_STEPS`

- **What:** 320 is justified by "nx + ny + nz = 208 cells of the alley".
- **What:** `CellSnapshot.problems()` accepts any shape. For a snapshot with nx + ny + nz > ~300 (a longer tile, or step 7 sending something else), grazing rays run out of steps, return false and discard, which shows as holes with no diagnostic.
- **Fix:** bound the loop by `cells.x + cells.y + cells.z` (a dynamic loop bound is legal in GLSL 3.30), or have `problems()` refuse shapes over the constant.

### SHOULD-FIX: hatching is never measured, and on laptop it aliases into a checkerboard
`lighting.gdshaderinc::hatch`

At render scale 0.5 the 0.12 m period on wall_north's exposed east face (where wall_end is cut) comes out as a checker dither, not stripes; I compared 4× crops of the laptop and rig goldens. Hatching is the cut-away's "shape, not colour" signal, but no check in `golden_measures.py` covers it, so it holds by luck. The fix is to floor the period in pixels, like the crack groove, and add a measure.

### NIT: the emission formula departs from §5.3 without being listed
`emission.gdshaderinc::glow_emission`

- **The departure:** the code computes 4((T/1773)⁴ − (T₀/1773)⁴). §5.3 says 4(T/1773)⁴. The comment explains the change, but the commit's "Departures" list omits it.
- **§5.3's claim doesn't hold:** "embers near 920 °C read bright yellow-orange; output above 1.0 drives glow". At 920 °C (g = 103) the code emits about (0.60, 0.20, 0.02): orange-red, below the 1.0 bloom threshold. Even §5.3's own formula gives 0.82 there.
- **Fix:** record the departure, and either retune GAIN or the hue, or correct §5.3's claim.

### NIT: edge pixels discard when `entry_axis` picks the wrong axis
`traversal.gdshaderinc::entry_axis`

- **Mechanism:** within about 1e-5 cells of a box edge whose neighbouring face is back-facing, `entry_axis` can pick that face's axis. `walk_at` then computes crossed = n (for example x = nx while moving +x), the cell is outside, and the pixel is discarded.
- **Also:** an origin clamped to exactly `cells` on a non-chosen axis floors to n and discards.
- **Impact:** only silhouette pixels, and the solids stop below the box top. A walls-to-the-edge tile would show it on the x = 0 and y = 0 faces.
- **Fix:** take the entry axis from the box face's normal (pass `NORMAL` in a varying), not from distances.

### NIT: `centre_godot` duplicates the node's position, so the placement assumptions are fragile
`cell_volume.gd::show_snapshot`, `cell_volume.gdshaderinc::vertex/fragment`

The shader assumes `MODEL_MATRIX` is a pure translation, and that `centre_godot` is the box's half-extent, which happens to equal `position`. Moving or rotating the node, or placing a tile at an offset (streaming), breaks both the ray origin and the depth with no error. Pass the half-extent explicitly, and document or assert that there is no rotation or scale.

### NIT: a texture read with implicit derivatives inside divergent control flow
`emission.gdshaderinc::glow_count`

`texture(glow_tex, …)` runs after `discard` and inside data-dependent branches, so per GLSL its derivatives are undefined. It is harmless today, because there are no mipmaps and both filters are linear. `textureLod(…, 0.0)` states the intent, and also avoids FXC gradient-in-flow warnings under ANGLE/D3D.

### NIT: the tonemapper choice has no recorded why
`render_stage.gd::_init`

`TONE_MAPPER_LINEAR` is set with no one-line why. Linear clips HDR emission at 1.0, so bloom is the only cue that something is brighter than white, and laptop has bloom off. The black-background workaround for Compatibility's per-path clear-colour mapping is documented. But it constrains the game's night look and hides an engine inconsistency, so the owner should see it as a decision, not a detail.

### NIT: the perspective ray path is never exercised
`cell_volume.gdshaderinc::fragment`

`dir = normalize(v_local − v_camera_local)` is the correct ray for a perspective camera, but every caller is orthographic, so nothing tests it.

## Checked, nothing found

**Feedback into the world.** `Cutaway`, `CellVolume` and `RenderStage` write only shader uniforms and the viewport. There are no sockets and no intents, and nothing returns a value to game code.

**Typing.** Every new `.gd` file declares types throughout. `project.godot` has every warning at 2 and `directory_rules={}`. The dummy renderer compiles shaders headless; I probed it with a broken shader and it prints "Shader compilation failed". `cell_volume.gd` preloads both variants, so the gate's load step catches shader compile errors.

**Snapshot channels, not art.** Geometry, region, crack, glow and burning all come from the channels, and albedo from a palette by material name. The fixed key light and night ambient are documented as a look (BF-N1).

**Traversal:**
- Axis choice and ties are standard.
- Brick jumps decide the crossed axis from the step sign, and the other axes' floor can only regress to a cell with t ≈ current t. That is a grazing visit, not a skip, and my port confirmed no cell skipped.
- Rays parallel to an axis get `inv` = FAR and are excluded from the jump.
- Partial bricks at the far edge exit correctly.
- Every `texelFetch` sits behind `inside()`, including the AO and hatch neighbour reads, through short-circuit `&&`.
- Loop bounds are constant (320, 16, 27, 8).

**Depth.** The Compatibility `ndc.z * 0.5 + 0.5` matches §5.3 and sits behind `CURRENT_RENDERER`. The hit point maps back into the model frame consistently with the ray origin.

**Orthographic ray.** The camera's −Z goes through `INV_VIEW_MATRIX[2]` into the local frame, with the origin at the rasterised box point. Correct.

**Voronoi.** The 3×3×3 search is enough for jitter in [0.15, 0.85]. The bisector distance's sign and `away` are right, and the fissure-wall normal faces the ray. The integer hash is portable.

**Linear glow sample.** `p − 0.5n` lands on the hit cell's centre plane, and clamp-to-edge applies at the volume's edges. Inside a groove the sample can fall in the next cell, a tier difference too small to matter.

**AO.** It treats out-of-volume cells as open. Its 8-tap layout is a documented departure from §5.5's 6-tap.

**Engine whys** are present for MeshInstance3D, BoxMesh, ShaderMaterial, ImageTexture3D, the R8/RG8 formats, the SubViewport, own_world_3d, the orthographic camera, Resource vs RefCounted, `unshaded`, `cull_back` and the `#define` variants.

**Driver risk, unverified.** No ANGLE/D3D11 compile has been run. The 320-step loop with 16 × 27 nested loops is the shape FXC sometimes tries to unroll. Worth one Windows ANGLE compile before step 8 closes.

Scratch work (emulator, crops): <scratchpad>/emu.py, <scratchpad>/crops.png, <scratchpad>/hatch.png.
