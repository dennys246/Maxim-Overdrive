# Client and rendering, delta 1: phase1/client-fuel (step 8 fuel pass)

Scope: the working tree against my round-1 report (`docs/design/reviews/client_fuel/client_rendering.md`), the author's
fold record (`fold.md`, read as claims), `client_objects.md` §4–§5 and §7.2, and `research/fuel_antialiasing.md`. I
read the rod's two passes, the flame, slab and object includes, `FuelPass`, `FuelGeometry`, the `FuelSnapshot`
refusals I had raised, `scripts/golden_fuel.py` and the new fixture objects in `scripts/fuel_fixtures.py`.

What I ran, all outside the worktree:
- **Probes:** Godot 4.7.2 (opengl3, M2) on a copy of `client/` at
  `/private/tmp/claude-501/-Users-dennyschaedig-Scripts-Maxim-Overdrive/b7bf205d-729f-449a-b38d-e830de582329/scratchpad/delta_rendering/client/`,
  with HOME and XDG moved there.
  - `probe/cross.gd` draws the real `FuelPass` on `fuel_ramp` at the crossing, then swaps the two crossing rods' instance
    order.
  - `probe/slab.gd` switches the slab floor on and off with the cell floor drawn and hidden.
- **A full Mac golden run** (`scripts/golden_run.py --no-xvfb`, output in `delta_rendering/golden/`): PASS, 24 shots. I
  recomputed the new checks from its frames.

I modified nothing in the worktree.

## Fold status of my round-1 findings

| Finding | Status | Read from |
|---|---|---|
| SHOULD-FIX 1: crossing rods occlude by instance order | **fixed** (the occlusion) | `fuel_rod.gdshader` writes depth with no colour where coverage ≥ 0.5. `fuel_rod_fringe.gdshader` is its `next_pass`, with `depth_draw_never`. Silhouettes now occlude by depth on every tier, and the drawn width keeps the 2 px floor. Crossing recomputed from my Mac frames: rig 72.8, laptop 41.9, max 72.8 L* (bar 15). My probe gives an identical fuel-ID mask in both instance orders. The edge's anti-aliasing at a crossing still depends on order: new SHOULD-FIX D1 |
| SHOULD-FIX 2: flames against blended rods; ±1000 m box | **fixed** | `fuel_pass.gd::_init`: fringe priority 1, flames priority 2. `_fit_boxes`: the rod, slab and flame boxes come from the data. I verified the priority fix in round 1's standalone probe. I did not re-probe it on the real pass, because no fixture flame overlaps a rod core, so no check can see this (the fold says the same). Box margins: NIT D3 |
| SHOULD-FIX 3: flames ignore burnout and burn-through | **fixed** | `fuel_flame.gdshader::vertex` reads the object row from `segment_object_tex` (RF, exact) and collapses on `burnt_out(object_row) or burnt_through(INSTANCE_ID)`. The fixture now has `rod_spent` (state 1, 1,200 °C, ignited 1) and `rod_gap`. The burnout and dead-flame checks pass on my Mac frames. Their deletion numbers are the author's, not rerun by me |
| SHOULD-FIX 4: slab floor buries what rests on top | **fixed**, fixture **deferred** | `fuel_slab.gdshader::vertex` computes `VERTEX.y = 0.5 - (0.5 - VERTEX.y) * growth`, so the segmented face stays in place. That is the face flames rise from (`FuelGeometry.flame_buffer`'s `+ normal * T`). The stick-on-slab fixture is deferred in step 8's checklist (`docs/plans/checklists.md:323`; trigger: step 8's remaining items). The anchoring has a new cost of its own: NIT D2 |
| SHOULD-FIX 5: §4.1 texel layout stale | **fixed** | §4.1 now states the shipped layout (first row plus palette slot, count plus object row, ℓ's bits, `state` in its own R8 texture), matching `instance_at` and `_place` |
| NIT 1: `segment_count` 0; unchecked sizes | **fixed** | `FuelSnapshot._object_problems` refuses count 0. Rod length and radius must be finite and positive |
| NIT 2: normals right only for orthogonal bases | **fixed** | slab axes must be unit length and perpendicular (`square`, `_is_unit`). Rod bases are orthogonal by construction |
| NIT 3: rod ends have hard edges | **open** | "recorded here" is only `fold.md`, a review record. The research note's open items (slab edges, the rig's weakness, llvmpipe cost) and step 8's checklist don't mention rod ends. Add them beside slab edge coverage, with that item's trigger |
| NIT 4: culling boxes miss the widening | **fixed** | `_fit_boxes` grows the rod box by 3 px and the slab box by 8 px. The test reads the buffers. The margin is hard-coded: NIT D3 |
| NIT 5: magenta lost at 16 recipes | **fixed** | `UNCOLOURED_SLOT` is reserved, so at most 15 recipes. `use_palette` reports any recipe past that |
| NIT 6: burn colour in two includes | **fixed** | `flame_colour.gdshaderinc` is included by `emission.gdshaderinc` and `fuel_object.gdshaderinc`. The billboard's `FLAME_BASE`/`FLAME_TIP` are a separate look, not a copy |

## New findings

### SHOULD-FIX D1: where rods cross, the front rod's edge is still drawn by instance order and against the wrong background

**Location:** `client/addons/engine/render/fuel_rod_fringe.gdshader::fragment`, with `fuel_rod.gdshader`. The claim
to correct is in `docs/design/research/fuel_antialiasing.md` ("Depth" table, shipped row: "the ramp intact") and
`client_objects.md` §4.2.

**Mechanism.** Every depth pass draws first, then every colour pass in instance order, and no colour pass writes
depth. Take a front rod A crossing a rear rod B:

- **Outer half of A's ramp** (coverage 0 to 0.5, outside A's silhouette, inside B's): the depth there is B's.
  - If A's index is lower, A blends over the background first. Then B's colour pass passes its own depth at
    coverage 1 and overwrites A completely. A's outer fade is erased.
  - If A's index is higher, A blends over B, which is correct.
- **Inner half of A's ramp** (coverage 0.5 to 1, inside A's silhouette): the depth there is A's, so B never draws.
  A blends over whatever is behind both rods. That is a halo of background between A and B, in either order.

The include's header comment states only the inner-half cost, and the research note repeats it in one line. Neither
mentions that the outer half depends on order.

**Measured** (`probe/cross.gd`: `fuel_ramp`, golden scale 72 px/m, volume hidden, flames off):
- **Shaded, original order** (log later, so the case where A's index is lower):
  - Rig: 7 pixels differ from the swapped order, by up to 122/255. Example: (113, 48, 11), the bare log's colour,
    where the swapped order gives (184, 152, 133), the stick's fade over the log.
  - Laptop: 55 pixels differ, by up to 66/255.
  - That is the stick's outer fade erased in the committed fixture itself.
- **Fuel-ID mask, both orders identical:** inside the white log, the stick's edge shows a seam of 132–208/255 on rig
  and down to about 100/255 on laptop, where the answer is 255. That is the halo.
  - It also lowers `log_cross`'s summed-coverage area, which the per-object tier-agreement check reads.
  - It passes today: on my Mac frames `log_cross` is 224.7 on rig against 220.3 on laptop.

**Failure scenario.** A kindling pile at the laptop tier while the camera pans:
- Every crossing has a step of about 0.5·|rear − background| at the front rod's silhouette, which is the hard step
  at coverage 0.5.
- On half the crossings (whichever index order the server sent), the outer fade is also gone.
- The fold rejected the opaque-core design for exactly this step, which crawled at 2.55–2.62× against the 2.0× bar.
  Here it comes back at every crossing.
- The stability check measures one stick alone. The crossing check measures mean L* over 16 pixels with a hot stick
  on a cold log, so it passes either way.
- Nothing measures crawl in a pile, and the Phase 1 exit's subject is piles.
- The design and the research note say the ramp is intact, which is false at a crossing.

**Why SHOULD-FIX and not BLOCKER:** who occludes whom is now right. This is edge quality at about 1 output pixel, but
it is unmeasured and the documents overstate it.

**Fix (unverified):** the author decides between two options.
- **(a) Accept and record.** Correct the research note's "ramp intact" and §4.2's sentence. Record both halves of the
  cost with the numbers above as a known gap or backlog row. Add a crossing to the stability measure, with the bar
  fixed before measuring, so the cost is known rather than assumed.
- **(b) Fix the outer half.** Order the rods back to front per camera yaw at rebuild. The camera has only
  `IsoCamera.step_yaw`'s four yaws, so that is four index orders. It fixes the outer half wherever the order of
  centre depths matches the order at each pixel, which holds for most pairs of crossing sticks (my round-1 remark that
  crossings have "no consistent order" was too strong for two sticks). It leaves the inner halo, which needs
  order-independent transparency.

### NIT D2: the slab floor's growth is buried by whatever the slab rests on

**Location:** `client/addons/engine/render/fuel_slab.gdshader::vertex`.

Anchored at the segmented face, the growth extends away from it. For a slab lying on a surface, that is down into the
surface, behind its opaque cells.

**Measured** (`probe/slab.gd`, `slab_char` on the alley floor, fuel-ID coverage in an 80 px box):
- At 10 m: 904.2 with the slab floor on and 904.2 with it off, when the cell floor draws. With the cell floor hidden,
  941.2 against 904.2.
- At 24 m: 938.1 against 938.1 with the floor drawn; 984.9 against 958.9 with it hidden.

So the slab floor does nothing for a slab resting face-up on anything. Its thickness edge stays below 2 px (about 0.5 px
at 24 m).

This is harmless for a flat plank, whose silhouette is its face and not thin. But the mechanism is a no-op that no
check can see. The deferred stick-on-slab fixture tests the other direction (burial from above), not this one.

**Fix (unverified):** say in §4.2 or step 8's checklist that the floor applies only to an exposed thickness edge.
Alternatively, widen the slab's silhouette in view space, as the rod's coverage does, with depth from the true
surface. Slab edge coverage, the research note's open item 2, would need that machinery anyway.

### NIT D3: the culling-box margins are constants, not the shaders' own widening

**Location:** `client/addons/engine/render/fuel_pass.gd::_fit_boxes`.

- **Rod box.** It grows by 3 output px. The rod shader widens by `floor_half_m + render_pixel_m`, which is 1 px +
  1/scale px.
  - That fits the shipped scales of 0.5 and 1.
  - `RenderTier` accepts any scale in (0, 1]. At 0.33 the widening is 4 px, the box is 1 px short, and a floored stick
    at the frame edge pops.
  - Grow the box by `px + px / render_scale` instead, from the value `use_pixel_metres` already holds.
- **Flame box.** It grows by `FLAME_HEIGHT_M` plus half the widest flame.
  - In play (`flame_flicker` 1) a flame rises up to 1.2 × 0.2 = 0.24 m, against a reach of 0.22 m for the widest rod
    flame (0.04 m).
  - That matters only when every object is just off screen and a tip isn't, so it is negligible, but the box and the
    shader again state one quantity twice.

## Checked and sound

**Pass ordering:**
- Priorities: rod depth 0, rod colour 1, flames 2.
- The cell volume, slabs and bodies are opaque, and nothing else in `client/` sets a priority or blends.
- The transparent pass is therefore exactly: every rod's depth, then every rod's colour, then the flames.
- The fringe meets its own depth on the same front faces (`cull_back` in both passes) from textually identical vertex
  code. Silhouettes draw on both the M2 and llvmpipe, per the fold's Linux goldens and my Mac run.
- The FLAME_ID view stays correct: fringes draw black before the flames, and flames are depth-tested against
  silhouettes.

**Flame gate:**
- `segment_object_tex` is RF, built by `FuelGeometry.segment_objects` in segment-row order.
- Floats are exact to 2²⁴, and `INSTANCE_ID` is the segment row.
- `state_tex` and `thickness_tex` reach the flame material through `_param`.
- `ignited_tex` is R8, so it cannot carry inf or NaN.

**Temperature clamp:** an f16 inf clamps to 6,000 °C. A NaN fails `t_c > FUEL_GLOW_START_C` whatever `clamp`
returns, so it adds no glow.

**Flat varyings:** `v_instance` (ivec4) and `v_segment_m` are constant per instance, so the provoking vertex cannot
matter. The `segment_row` clamp still keeps caps on their own object.

**Slab anchoring geometry:** local +y is the segmented face, as in `slab_buffer`'s `normal * T`. Flames rise from that
face.

**New checks in `scripts/golden_fuel.py`:**
- **`crossing_findings`** can fail for the right reason: the log is later in instance order, so draw-order occlusion
  shows the log (the author measured 7.1–7.7 L*). It reads `stick ∩ log` against `log ∖ stick` on the no-flame
  frame, within the fuel mask. It is blind to D1.
- **`burnout_findings`** compares `rod_spent` against `rod_burnt`'s cold, live segments with char ≥ 0.9, flames off.
  A drop of the burnout branch adds glow (author: 84–96 L*). An absent rod fails on "no pixels".
- **`dead_flame_findings`:**
  - Its strips widen by 0.4 m in pixels.
  - No other ignited object lies within that reach in the fixture. `stick_cross` is hot but not ignited, and 0.4 m
    from `rod_spent`'s end.
  - So it can't false-alarm today, and it reads the flame-ID mask, which depth-tests against silhouettes.
- **All three pass on my Mac frames on every tier.**

**New fixture objects:**
- `stick_cross` rests on `log_cross`: its axis is 5 mm above the log's top, so they touch.
- `rod_gap`'s ignited run is exactly its burnt-through run, so a flame there can only come from an ungated shader.

## Not verified

- **Godot's vertex template:** whether it declares `invariant gl_Position`. The two rod passes rely on equal depth
  from two programs. That holds on the M2 and llvmpipe, but other drivers are not checked.
- **The real pass's flame priority:** no fixture overlaps a flame and a rod core. My evidence is round 1's standalone
  probe.
- **The fold's deletion runs** (burnout branch, flame gate, single-pass rods): not rerun.
- **The stability numbers** in the research note: not rerun. I didn't measure stability at a crossing; D1 is reasoned
  from the step I measured, not from a crawl measurement.
- **llvmpipe:** D1's and D2's pixels were measured only on the M2.
