# Client and rendering review: phase1/client-fuel (step 8 fuel pass), round 1

Scope: `git diff 69483d9` plus the untracked files. I read the shaders, FuelPass, FuelGeometry, FuelSnapshot validation, the golden and stability scenes, FuelFootprints, `scripts/golden_fuel.py`, `scripts/golden_stability.py` and the `golden_run.py` diff, and checked them against `client_objects.md` §4–§7 and `research/fuel_antialiasing.md`. I ran Godot 4.7.2 (opengl3, gl_compatibility, macOS) only on a copy of the client at `/private/tmp/claude-501/-Users-dennyschaedig-Scripts-Maxim-Overdrive/b7bf205d-729f-449a-b38d-e830de582329/scratchpad/rev_client/client/`. The probes are in its `probe/` folder: `probe.gd` (standalone blend, sort and encoding probes), `probe2.gd` (real FuelPass flames at four yaws), `probe3.gd` (real stick, floor on and off). I did not touch the worktree and did not run the gate.

## Summary

The client only draws. Nothing in FuelPass, FuelGeometry, FuelFootprints or the shaders feeds back to the server. Visuals come from snapshot columns. Glow, burning, char, burn-away and flames each change brightness or shape, not hue alone. The refactored cell includes compute exactly what they computed before (details at the end). The real problems are in how the rods blend:

- A thin rod's anti-aliased edge, or on the laptop tier the whole of a floored stick, writes no depth. Rods in a pile therefore occlude each other by MultiMesh instance order, not by depth.
- The flames' draw order against the blended rods depends on the transparent sort, which keys on an arbitrary box centre.

I reproduced both mechanisms in Godot. Neither fixture exercises them, so every gate check passes with the defects present.

## Findings

### SHOULD-FIX 1: on the laptop tier, floored rods occlude each other by instance order, not depth

**Location:** `client/addons/engine/render/fuel_rod.gdshader::fragment` (the coverage formula), with `render_mode … blend_mix, depth_draw_opaque, depth_prepass_alpha`.

**Defect:** only fragments at full alpha reach the depth prepass. I measured this: a fringe at alpha 0.9, 0.98 and 0.995 wrote no depth in Compatibility. The formula is `coverage = clamp((v_drawn_m - d)/fade + 0.5, 0, 1)`.
- At the 2 px floor on rig (drawn = 1 output px, fade = 1 px), coverage is 1 only for d ≤ 0.5 px. The depth-writing core is 1 px wide, half the floor.
- On laptop (fade = 2 output px), coverage is `1 - d/2px`. It reaches 1 only on the axis itself, so a floored stick writes essentially no depth at all.

In the transparent colour pass, a rod drawn later overwrites anything without depth, even when it lies behind. Each rod's core passes its own prepassed depth, and blending at alpha 1 replaces the pixel.

**Measured** (probe A in `probe.gd`: two instances of one MultiMesh, red in front, green behind):
- Front at index 0: the front's fringe over the back quad comes out pure green (0, 1, 0). The front edge is erased.
- Front at index 1: the same pixel blends correctly to (0.50, 0.50, 0).

**Failure scenario:**
- Laptop tier, a 20 mm stick lying across a 100 mm log behind it, with the log at a higher instance index. Inside the log's silhouette the stick is erased completely: it appears to pass behind the log.
- Rig tier, same scene: the stick's anti-aliased fringe is erased there, so it draws 1 px wide and hard-edged, below §4.2's 2 px floor.
- In kindling piles, the Phase 1 exit's subject, crossings are the norm.

**Why the gate misses it:**
- The stability check draws a lone stick.
- `fuel_ramp`'s pile is laid out so that "none touches another".
- The research note's pile result (laptop coverage 0.91 of rig's) measures area, not who occludes whom.

**Fix (unverified):** draw rods in two passes.
1. An alpha-tested core that writes depth, keeping coverage ≥ 0.5. That core is exactly the floor width.
2. A blended fringe pass with `depth_draw_never`, depth-tested against step 1.

Add a crossing-sticks fixture and an occlusion check to prove it. Sorting instances per yaw cannot fix this: crossing sticks have no consistent order.

### SHOULD-FIX 2: flames over a blended rod depend on the transparent sort, keyed on an arbitrary box centre

**Location:** `client/addons/engine/render/fuel_pass.gd::_init` (`flames.custom_aabb` = ±1000 m around the FuelPass origin; neither material sets `render_priority`).

**Defect:**
- Rods are `blend_mix`, so they are in the transparent pass, sorted against the flames.
- Godot sorts transparent instances by their AABB centre's depth. The flames' centre is Godot's origin, a corner of the world, not where the flames are.
- If the flames sort first, they add light, and then the rod's core (alpha 1, passing its own prepass depth, since flames write none) overwrites them.

**Measured** (probe B in `probe.gd`: an additive quad in front of an opaque-core `blend_mix` quad):
- Additive quad's box centre far behind the scene: the pixel is pure red (1, 0, 0). The flame is gone.
- Box centre nearer the camera: magenta (1, 0, 1), the correct additive result.
- Setting `render_priority = 1` on the additive material gives magenta in both cases. **Fix verified** in the standalone probe.

**Failure scenario:** at camera yaws where the world origin sorts behind the rods, the lower part of every flame that overlaps a rod vanishes. That covers a flame from a lower stick crossing a stick above it, a vertical rod's flame (its base point sits inside the rod), and the base of every flame. The behaviour changes as the camera turns.

**Why the gate misses it:** in `fuel_ramp` no flame overlaps a rod core. `probe2.gd` counts flame-mask pixels at all four yaws with priority 0, with priority 1 and with rods hidden: 116, 110, 117 and 108 px, identical across all three. The check structurally cannot see this defect.

**Fix:**
- Give the flame material a higher `render_priority` than the rods. That alone is verified, in the standalone probe.
- Also derive the flames' `custom_aabb` from the snapshot's bounds at rebuild, not a fixed ±1000 m: a world over 1 km would cull flames. That part is unverified.

### SHOULD-FIX 3: flames ignore burnout and burn-through

**Location:** `client/addons/engine/render/fuel_flame.gdshader::vertex`.

**Defect:**
- `fuel_object.gdshaderinc::fuel_colour` drops glow and the burning term when `state` is 1, which implies `ignited_fraction` can be nonzero at burnout. The flame shader reads only `ignited_tex`: it never reads `state_tex` or `thickness_tex`.
- §4.3 says a burnt-out object draws "without glow or flame".
- The client contradicts itself: either `ignited` is guaranteed 0 at burnout, and `fuel_colour`'s branch is dead and should go, or flames break §4.3.
- Likewise, a burnt-through segment (thickness 0) with `ignited` > 0 draws a flame floating over its gap.

**Why the gate misses it:** `rod_spent` has `ignited` 0, so no check covers it.

**Fix (unverified):** collapse the quad when the object is burnt out or the segment is burnt through. That needs the segment's object row, or a per-segment state lookup. Add a fixture segment with `state` 1 and `ignited` > 0.

### SHOULD-FIX 4: the slab floor thickens the box in world space, burying what rests on it

**Location:** `client/addons/engine/render/fuel_slab.gdshader::vertex` (`VERTEX.y *= max(1, 2*floor_half_m/(thickness*edge_sine))`).

**Defect:** the thickening grows the box symmetrically along its normal in world space, so the top face moves up by half the added thickness.

**Example** (derived from the shader, not rendered): the fixture's 20 mm plank at the golden elevation (40°, edge_sine 0.77) at 30 px/m.
- The floor is 2 px = 67 mm, so the factor is about 4.3.
- The world thickness becomes about 87 mm, and the top rises about 33 mm.

**Failure scenario:**
- A 10 mm stick lying on the plank is swallowed by the plank's depth.
- The plank's own flames rise from the true top (`FuelGeometry._slab_tops`), so their bases are buried by about 33 mm.
- Near face-on views (`MIN_EDGE_SINE` 0.25) the growth reaches 8 px-metres.

The floor is meant to change what the screen shows (§4.2), not the depth that other geometry is tested against. The rod widens in 3-D too, but symmetrically about its axis. I measured the rod case against the real floor (`probe3.gd`): coverage drops only 0.5–1.7% when the floor draws, so the rod is fine.

**Fix (unverified):** widen the slab's silhouette in view space, as the rod's coverage does, rather than growing the world box. Or at least anchor the growth at the segmented face's opposite side. Add a fixture with a stick resting on a plank.

### SHOULD-FIX 5: the design's per-instance texture contract no longer matches the code

**Location:** `docs/design/client_objects.md` §4.1 against `client/addons/engine/render/fuel_object.gdshaderinc::instance_at` and `fuel_pass.gd::_write_instance`.

**Defect:**
- §4.1 still says texel 0 holds "the row's three bytes and `state`", and that "`state` updates the RGBA8 texture's fourth byte and never triggers a rebuild".
- The code puts the palette slot in byte 3, adds the object row in texel 1, and uploads `state` as a separate per-object `state_tex` every frame.
- The diff edited other bullets in §4.1 but not these two, so the design (the contract's owner) now describes a texture the code does not build.

**Fix:** update §4.1 to the shipped layout, or change the code to match.

### NIT 1: `segment_count` 0 makes the shader's clamp undefined

**Location:** `fuel_snapshot.gd::_object_problems`, `fuel_object.gdshaderinc::segment_row`.

A count of 0 is accepted. In the shader, `clamp(k, 0, count - 1)` then has min > max, which GLSL ES leaves undefined. In practice it reads the previous object's last segment. Refuse count 0, or count·ℓ < L, at the reader.

Related: a rod's length and radius, and a slab's sizes, are checked `> 0` but not finite for rods, and a slab's two axes are not checked orthogonal. A skewed basis makes `normal` non-unit and the box sheared.

### NIT 2: `MODEL_NORMAL_MATRIX` is safe only because the bases are orthogonal

Whether Compatibility's MultiMesh path gives M or M⁻ᵀ, the result is the same direction here. The rod's side normals have equal x and z scale, the caps are single-axis, and the box faces are single-axis. That stops holding the moment NIT 1's skew gets through. Say so in a comment, or enforce orthogonality.

### NIT 3: rod ends and slab edges have hard edges

The rod mesh is widened only radially, so its flat ends are not anti-aliased. The stability check drops two end bins, so this is untested. Slab edges are the research note's open item 2. Both are recorded or harmless at the floor, but rod ends are not stated anywhere.

### NIT 4: culling boxes miss the vertex-shader widening

The rod and slab MultiMesh boxes come from the unwidened mesh. A floored stick whose axis sits just off-screen can pop by up to about 2 px at the frame edge.

### NIT 5: past 16 recipes, an extra recipe takes a real colour instead of magenta

**Location:** `fuel_pass.gd::_write_instance`.

An unknown slot defaults to `PALETTE_SIZE - 1`. With exactly 16 recipes, slot 15 is a real recipe's colour, so a 17th recipe draws in it instead of §4.1's magenta. It is reported, but drawn wrong.

### NIT 6: one colour constant lives in two includes

`BURN_COLOUR` (1.0, 0.42, 0.08) in `fuel_object.gdshaderinc` duplicates `FLAME_COLOUR` in `emission.gdshaderinc`. The cell and fuel burning colours can drift apart; `glow_curve` and `key_light` were deduplicated for exactly this reason.

## The measured checks: can each fail, and does it measure what it claims?

**Coverage encoding is sound.** With bloom off, as every mask pass has it, a 0.5-alpha white fringe over black reads 0.498 at scale 1.0 and 0.502 at scale 0.5 (probe C). PNG values are linear coverage on both paths, so `object_areas` and the stability sums are valid.

**Stick stability:**
- It can fail: hard edges score 5.8–6.1× on laptop.
- It does not discriminate on rig. Hard edges score 2.05× and 1.18× against a 2.0 bar, which the research note's open item 1 already records. A rig-only regression would pass.
- The bar of 2× is a round number, though it was fixed before measuring, per the checklist.
- It measures a lone stick with the volume hidden, so it says nothing about the floor's or a pile's occlusion (Findings 1 and 4).
- It ran on an M2, not under llvmpipe (open item 3). Confirm the Linux run's numbers are on record.

**Burn-through:** can fail (deletion "thickness ignored"). The "every live segment draws" half only asks for one pixel per segment, which is weak but consistent with the table.

**Burning, char and glow:** each compares segments within one object on the no-flame frame. They can fail and measure L*. Sound.

**Flame shape:**
- It can fail: no mask pixels, or the gain below 15 L*.
- "Above" is measured against the lowest point of the lit run's axis, not per segment, so a flame drawn under a tilted rod could still pass. All fixture rods are horizontal.
- It cannot see Finding 2 (no overlap in the fixture).

**Tier agreement:** per object, summed coverage with a 2 px window on every tier. Sound, and the per-object design is justified by its deletion note.

**Fixture coverage gap:** every rod lies along world x, and the one slab is horizontal. Tilted and vertical rods, slanted slabs (the `edge_sine` path), crossings and objects resting on objects are all undrawn. Findings 1–4 all live in that gap.

## Checked and clean

**Refactored cell includes:**
- `glow_curve(glow_offset_c + glow_scale_c*g, glow_offset_c, clamp(g/255))` is algebraically identical to the old inline code.
- `face_lit`, the key-light constants and `godot_to_world` / `world_to_godot` moved verbatim.
- Include order puts each definition before its use (axes before traversal, key_light before lighting, glow_curve before emission).
- I confirm the author's claim that the goldens should be unchanged, from the source. I did not rerun the Linux image.

**Shader mechanics:**
- No half-float custom data: indices travel as RGBA8 bytes through `texelFetch`.
- The f32 segment length is rebuilt with `uintBitsToFloat`.
- `surface_temperature_c` is RH because the wire column is f16.

**Segment lookup:**
- `v_s` is linear along the rings-0 cylinder, exact under the orthographic camera.
- The clamp keeps the caps on their own object.
- The discard is per fragment, and the depth prepass runs the same discard.

**Flame quads:**
- `POSITION` is written in the vertex shader, with `custom_aabb` set because the mesh box is meaningless.
- A collapsed instance rasterises nothing.
- `INSTANCE_ID` equals the segment row, consistent with `segment_tops`' object order, which FuelSnapshot enforces.

**Transforms:** FuelGeometry builds Godot-frame transforms through `IsoCamera.to_godot`, so the culling boxes are where the objects are, apart from NIT 4.

**GDScript and tier parity:**
- The GDScript is fully typed. The project's warnings-as-errors rejected my own untyped probe, so it is enforced.
- Tier parity holds: one output-pixel floor on all tiers, and a fade of one rendered pixel, which is equal area by construction.
- The rod floor against the real floor geometry: coverage falls by at most 1.7% (`probe3.gd`). Not a defect.

**Debug views:**
- Fuel-ID: cells drawn by OCCLUDER in black, fuel white, flames hidden.
- Flame-ID: fuel black but still occluding by depth, flames white and additive.
- Both draw with bloom off.

Fold status for each finding is open; per O25, a reviewer sets it.
