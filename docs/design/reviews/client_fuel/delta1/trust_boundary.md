# Trust boundary review: phase1/client-fuel, delta 1

Reader: Trust boundary lens. Tree: the worktree as it stood on 2026-11-22, HEAD d91df0f plus the uncommitted fold. Inputs: my round-1 report, the author's `fold.md` (read as claims), client_objects §3.2–§3.3 and fire_solid §1.1–§1.3.

**Method.** I read `fuel_snapshot.gd`, `fuel_pass.gd`, `fuel_geometry.gd`, `fuel_object.gdshaderinc` and the flame and rod shaders' fetches, plus both test files. I then copied `client/` to `$D/delta_trust/client`, with HOME and XDG moved there, imported it, and ran it under Godot 4.7.2 headless. The unmodified copy prints `client-tests: PASS 72 tests`. In the copy I ran:

- `probe.gd`, a probe script outside `tests/`;
- ten one-line deletions;
- two candidate fixes.

Nothing in the worktree or its git state was touched.

**Summary.** All three round-1 BLOCKERs are fixed, and the seam's own refusals are each proved by deletion. Two new BLOCKERs are on the pass side:

- a frame refused by the per-frame check has already been rebuilt, and its flames then read past the segment textures;
- the test that names the per-frame path never reaches it.

Counts: **2 BLOCKER, 3 SHOULD-FIX, 3 NIT**.

## Round-1 statuses (reviewer-set, read from the tree)

| ID | Status | Evidence |
|---|---|---|
| TB-B1 | fixed | One rule decides an object's table: `geometry_rows(kind)` (keyed on `kind_ids[kind]`), which `_place`, `flame_buffer` and `_geometry_problems` all call. Shared or out-of-range ids are refused (`_vocabulary_problems`). Deleting `if seen.has(id)` turns `test_vocabularies_with_shared_or_out_of_range_ids_are_refused` red (2 failures). `kind_name` survives as dead code (TB2-N1). |
| TB-B2 | fixed | `sizes.is_finite()` on rods. Deleting it gives 4 failures in `test_every_structural_check_refuses`. |
| TB-B3 | fixed | `counts.decode_u16(i*2) == 0` is refused. Deleting it turns `test_an_object_with_no_segments_is_refused` red. |
| TB-S1 | fixed (code) | `frame_problems()` holds the five per-frame columns to their sizes and `state` to 0 or 1. Deleting the size compare gives 5 failures, and deleting the state check 1, both in `test_fuel_snapshot.gd`. Its call site in `show_fuel` is unguarded and misordered: TB2-B1 and TB2-B2. |
| TB-S2 | fixed, with one residual | Defect 1: the comparison is now against the last *drawn* `_structure`, which a refusal does not update. Defect 2: `FuelPass.show_fuel` owns both the comparison and the check. Defect 3: `structure()` carries `#rows`, `#kinds` and `#recipes`, and the region map is compared too. §3.2's wording is fixed. Residual: the stored structure shares the snapshot's arrays (TB2-S1). |
| TB-S3 | fixed | `_shape_problems` refuses rows outside 0..2,000 (objects, rods, slabs) or 0..2×10⁴ (segments) before any multiplication. Deleting the limit turns `test_row_counts_past_the_world_limits_or_missing_are_refused` red (2). Under these limits, the drawing side's encodings hold: first row ≤ 20,000 < 2²⁴, object row ≤ 2,000 < 2¹⁶, instance texture height ≤ 2,000 ≤ 2,048, segment textures ≤ 79 rows. The limits are a hand copy (TB2-N2). |
| TB-S4 | fixed | `fuel_colour` clamps `t_c` to [−273, 6000] before the glow. NaN stays implementation-defined through `clamp`, but every comparison with it is false, so it adds no glow (not rendered). |
| TB-S5 | fixed | Every path I listed now has a case: the missing or negative row count, segment length over {0, −0.02, NaN, ∞}, rod length and radius and slab length and width over the same four values, slab origin ∞, axis NaN, length axis off unit, and the other kind's table through a kind edit. Untested but covered by the same expression: thickness NaN or ∞, rod origin ∞. I accept those. |
| TB-N1 | fixed | `use_palette` clears `_structure` only when the slots change. `test_only_a_structural_change_rebuilds` calls it twice. |
| TB-N2 | fixed | Slot 15 is reserved for magenta. `_recipe_slots.get(…, UNCOLOURED_SLOT)` is used, and `test_a_recipe_past_the_palette_draws_magenta_never_a_real_colour` reads byte 3. |
| TB-N3 | fixed | `object_id`s must strictly rise. Deleting the check turns `test_every_structural_check_refuses` red. |
| TB-N4 | rejected (author's reason accepted) | `FuelFixture` is test support. It reads only committed fixtures, and no shipped path takes untrusted bytes through it. Step 7's decoder is the shipped gate and will need its own refusal suite. |

## New findings

### TB2-B1 (BLOCKER): `fuel_pass.gd::show_fuel` rebuilds before the per-frame check, so a refused frame draws new geometry, and its new flames read past the segment textures

- **Defect:** in `show_fuel`, a changed structure runs `problems()`, then `_rebuild(snap)`, and sets `_structure`. Only after that does it run `frame_problems()`, which can refuse.
  - `problems()` does not check `state` values (only `frame_problems` does), so a structurally valid frame with `state = 2` gets through it.
  - The frame is rebuilt and recorded as drawn, then refused, and the segment and state textures keep the previous frame's sizes.
  - This contradicts §3.2's "A refused frame draws nothing new" and the method's own doc comment.
- **Failure scenario, a geometry change (run, `probe.gd::_half_applied`):**
  - The fixture is drawn, then rod 0's radius changes to 0.05 and `state[3] = 2`.
  - `show_fuel` returns `["object row 3 has state 2; …"]`, yet `rebuilds` goes 1→2 and `_structure` holds the refused radius.
  - The refused geometry is what is drawn.
- **Failure scenario, an insertion (run):**
  - 600 segments are added to the last object, with keys correct, and `state[0] = 2`.
  - The frame is refused, but `flames.instance_count` goes 2335→2935 and `segment_object_tex` is rebuilt for 2,935 rows.
  - `temperature_tex` and the other segment textures stay at 10 rows of 256, where 12 are needed.
  - Flames 2,560–2,934 call `texelFetch(ignited_tex, row_at(INSTANCE_ID))` at y = 10 and 11, outside the texture. GLES3 leaves that undefined. On a frame step 7 refuses for a transient reason this is one wrong frame. If the server keeps sending the bad state, the rebuild does not repeat but the OOB reads continue every frame.
- **Fix (verified):** run `frame_problems()` before `_rebuild`, keeping the `changed` flag:
  ```
  var changed: bool = structure != _structure or region_names != _regions
  if changed: (problems → return if any)
  frame_problems → return if any
  if changed: _rebuild; _structure = structure.duplicate(true); _regions = …
  ```
  With this change in the copy, both scenarios are refused with `rebuilds` staying at 1 and flames at 2335, and the suite prints PASS 72. Add a pass-level test: a valid structural change plus a bad state, asserting `rebuilds` and `flames.multimesh.instance_count` are unchanged.

### TB2-B2 (BLOCKER): `test_fuel_pass.gd::test_a_refused_frame_draws_nothing_new` cannot fail for the per-frame path it names

- **Defect:** the test's second half restores rod 0's radius to `0.005`, but the fixture's radius is 0.01 (the probe read 0.00999999977648 from the accepted structure).
  - So the structure still differs, and the short `segments.ignited_fraction` is refused by `_shape_problems` inside `problems()`. Its message also begins with `segments.ignited_fraction`, so the assertion passes.
  - The per-frame branch of `show_fuel` is never reached.
- **Deletion run:** I replaced `var frame: Array[String] = snap.frame_problems()` in `show_fuel` with `[]`. The whole suite still prints `client-tests: PASS 72 tests`.
  - The shipped path's per-frame check, the fold's answer to TB-S1, is unguarded.
  - The fold's "a refused frame draws nothing new (tested)" holds only for the structural half.
- **Fix (unverified):** restore the radius from the fixture's own bytes (keep the original `PackedByteArray`), so the second frame differs only in a frame column. Assert `rebuilds` is unchanged as well as the refusal. Then delete the call again and watch the test go red.

### TB2-S1 (SHOULD-FIX, deferrable to step 7): `fuel_snapshot.gd::structure` stores the snapshot's own arrays, so an in-place edit of a structural column is never rechecked

- **Defect:** `structure()` puts `columns[key]` into the dictionary ("shared, not copied"), and `show_fuel` keeps that dictionary as `_structure`. Godot 4 packed arrays held in a Variant are shared references.
  - Run (`probe.gd::_in_place`): `var r = snap.columns["rods.radius_m"]; r.encode_float(0, INF)` changes the snapshot itself.
  - A direct `snap.columns["rods.radius_m"].encode_float(0, INF)` also changes `_structure`'s copy, which then reads `inf`.
  - The next `show_fuel` then compares equal and returns `[]`, with no recheck and no rebuild, while `problems()` on the same snapshot says `rod row 0 has bad geometry … radius inf`.
- **Failure scenario:** step 7's decoder reuses one `FuelSnapshot` and decodes into its existing arrays, an ordinary allocation-saving pattern.
  - Every structural change then goes unchecked and undrawn: the last instances stay while new segment state uploads against them.
  - If it changes `segment_count` without changing the row counts, a misdistributed count is drawn on stale instances.
  - Today's only producer, the fixture reader, builds new arrays, which is why no test sees this.
- **Fix (verified):** store `structure.duplicate(true)` on acceptance. It copies about 0.3 MB at the limits, only on a rebuild. In the copy, the in-place INF is refused, and the suite prints PASS 72. Alternatively, state in `FuelSnapshot`'s contract that a shown snapshot's arrays are never mutated. That is weaker, because nothing checks it.
- **Deferral:** acceptable only with step 7's decoder as the named trigger. The verified fix is one line and could fold now.

### TB2-S2 (SHOULD-FIX): finite but huge geometry passes §3.2's checks and makes the culling boxes infinite

- **Defect:** §3.2's geometry checks are finiteness, sign, unit axes and squareness. Nothing bounds magnitude or position, but fire_solid §1.3 refuses "an object partly outside the world", so such a row is malformed by contract and the client still accepts it.
- **Failure scenario (run, `probe.gd::_huge`):**
  - With rod 0's radius and origin_x at 1e30, `show_fuel` returns `[]`. The rod box becomes ±1e30, and that one rod covers the screen.
  - At 3e38, `FuelGeometry.bounds`'s reach overflows f32. The results are `rods.custom_aabb` S = (3e38, inf, inf) and `flames.custom_aabb` P = (−inf, −inf, −inf), S = (inf, inf, inf).
  - P + S is then NaN, so frustum tests on the flames' box are undefined: every flame can be culled, or none. I did not render this.
- **Fix (unverified):** refuse geometry whose extent leaves the world box by more than fire_solid's 1 mm. The world box comes from welcome or the cell snapshot's extent. A cheaper interim, if the world box is not on hand at this seam, is to bound every coordinate and size by the tile's largest extent. This is a §3.2 contract addition, so it needs the design's owner.

### TB2-S3 (SHOULD-FIX): `fuel_pass.gd::use_palette` applies new colours before the frame is checked, so a refused frame recolours the last good one

- **Defect:** `use_palette` sets `recipe_colours` immediately and clears `_structure`. If the following `show_fuel` refuses, the old instances keep their old slot bytes, but the palette's slots now belong to the new ordering.
- **Failure scenario (run, `probe.gd::_palette`):**
  - Draw with `{pine_rod: 1, pine_slab: 2}` coloured red and green.
  - Then send the same mapping in the other order (`{pine_slab: 2, pine_rod: 1}`) with a refused frame (rod radius NaN).
  - `recipe_colours` becomes `[green, red, …]` while every rod's slot byte is still 0, so the last good frame's rods draw in the slab's colour.
  - This lasts as long as frames keep being refused.
  - A welcome that only reorders the recipe map, with no id changed, also forces a full rebuild. That is cheap, but it is a needless structural change.
- **Fix (unverified):** keep the computed palette pending and apply it inside `show_fuel` only once the frame is accepted. Alternatively, have `show_fuel` take the palette, so the pass applies a frame's whole state or none of it. Assigning slots by sorted id, not dictionary order, removes the reorder rebuild.

## NIT

- **TB2-N1:** `fuel_snapshot.gd::kind_name` no longer has a caller outside its test. Its doc says it is "the one rule the checks and the drawing both use", which is false: `geometry_rows` is that rule. Delete it, or correct the doc.
- **TB2-N2:** `fuel_snapshot.gd::MAX_OBJECTS` and `MAX_SEGMENTS` are hand copies of `data/world/limits.yaml`, which fire_solid §1.3 calls provisional until 6.1 measures. A raised server limit makes the client refuse valid frames. That failure is loud, but nothing ties the two values together, and nothing ties them to the drawing side's 2,048-row instance texture either. This is one-owner territory (B36): step 7's welcome or a contract test should carry the values.
- **TB2-N3:** `test_fuel_snapshot.gd::_refused` matches a substring such as `"rod row 0"`, which any rod geometry problem satisfies. The deletions I ran all still went red, so it holds today. A case can still pass on a different check than the one it names, as TB2-B2 shows on the pass side. Matching the column's value in the message, for example `"radius inf"`, would pin each case to its check.

## Checked and sound

- The check order is `_shape_problems` first, short-circuiting, then limits before any multiplication. Every row walk is bounded by checked row counts, and `_segment_key_problems` allocates only `rows["segments"]` ≤ 2×10⁴.
- Ten deletions went red: zero count, shared id, world limits, sorted ids, state, rod finiteness, slab perpendicularity, frame sizes, and the two seam checks above. Each was in `fuel_snapshot.gd`, run against the full suite.
- `geometry_rows` with a kind the vocabulary lacks uses id −1, matching no row, and `_geometry_problems` then requires that kind's table to be empty.
- u32 ids at or above 2³¹ are compared as int32 on both sides in `_geometry_problems`, which is consistent, and as int64 in the sort check.
- Empty tables: `instance_count` 0 with a one-row zero texture, and `segment_objects` empty, padded to one row.
- Shader indices: `segment_row`'s clamp is now sound, since count ≥ 1. A subnormal ℓ gives `int(floor(inf))`, which is undefined, but the clamp keeps it on the object's own rows. `recipe` is clamped to 0..15, and the RF segment-object texture is exact far past 2,000.
- The design's choice not to recount segments from geometry (§3.2) means a count that disagrees with L draws the wrong segment along the rod but stays on its own object. That is a recorded decision, not a seam defect.

## Not verified

- I did not render the GLES3 out-of-bounds reads (TB2-B1) or the infinite and NaN culling boxes (TB2-S2), so their visual effect is inferred from the GLSL and Godot behaviour.
- I did not render NaN through `clamp`.
- I did not run the golden or Python suites, and did not measure the cost of `duplicate(true)` beyond its size estimate.
- I read neither step 7's decoder (it doesn't exist yet) nor the welcome vocabulary format.

Probe: `<scratchpad>/delta_trust/client/probe.gd`.
