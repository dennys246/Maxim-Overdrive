# Executor review: phase1/client-fuel, delta 1 (round 1 → fold)

## The tree moved while I was reviewing it

The author kept folding during this round. Between 03:04 and 03:07 on 2026-11-22, these files changed under me:
- `fuel_pass.gd`, `fuel_snapshot.gd`, `test_fuel_pass.gd`, `test_fuel_snapshot.gd`
- `tools/fuel_aa/rebuild_time.gd`, `client_objects.md`, `checklists.md`

The changes cite "TB2-B1", "TB2-S1" and "TB2-S3", which look like the trust-boundary delta reviewer's findings.

I reviewed two snapshots:
- **Fold tree.** The fold as handed, copied at the start under `scratchpad/delta_executor/repo/`. New findings E2-S1 and E2-S2 are from this tree.
- **03:07 tree.** A copy under `scratchpad/delta_executor/client/` and `bench/`. I reran on it whatever touched the changed files.

Where the 03:07 edit already fixes a finding, I say so and say what I ran. The next delta should confirm that on the committed tree.

**Something I wrote by accident.** Once, I imported `scripts/golden_compare.py` with the worktree's `scripts/` as the working directory. That rewrote `.pyc` files in `scripts/__pycache__/`, which is gitignored. Nothing else in the worktree was written.

## Status of my round-1 findings

| Finding | Status | What I read or ran |
|---|---|---|
| S1 (burnt-out branch and `state_tex` unguarded) | **fixed** | `rod_spent` is now at 1,200 °C reporting ignition, and `golden_fuel.burnout_findings` reads it. I deleted the `if (burnt_out(...))` block in `fuel_object.gdshaderinc` and ran `golden_run.py --no-xvfb` on a scratch repo copy: burnout fails on every tier (laptop 84.0 L*, rig 96.2, max 96.2). The fold's 84–96 reproduces. |
| S2 (flames ignore burnout and burn-through) | **fixed** | `fuel_flame.gdshader` collapses a dead flame, looking up the object row through `segment_object_tex`. Deletions, each red on every tier: (1) `dead = false` gives 243–322 px. (2) The burnout half alone gives 243–280 px at `rod_spent`. (3) The burn-through half alone gives 112–125 px at `rod_gap`. (4) `object_row = 0` gives 243–280 px. The fold's numbers reproduce. Attribution is imprecise (E2-N1). |
| S3 (`segment_count` 0 accepted) | **fixed** | `_object_problems` refuses it. Deleting the refusal turns `test_an_object_with_no_segments_is_refused` red: the only remaining problem is the key mismatch, not "no segments". |
| S4 (no magenta past slot 15; byte 3 unasserted) | **fixed** (as raised) | Slot 15 is reserved. Four deletions, each red: (1) byte 3's write (headless, 2 failures); (2) the fallback slot set to 14 (got 14, want 15); (3) the past-palette bound moved to `PALETTE_SIZE` (2 failures); (4) the 17-recipe test. The shader's read of the slot is still unguarded (E2-N2). |
| S5 (§4.1 texel layout stale; rebuild cost unmeasured) | **fixed** | §4.1 lines 182–184 now state the layout the code builds, with `state` as its own texture. I ran `tools/fuel_aa/rebuild_time.gd` (03:07 tree, M2, headless, twice): insertion min 14.26/14.36 ms, median 14.49/14.54 ms. The doc's "14.1–14.5 ms" holds within the run spread. The fold record's "13.8–14.2 ms" does not match the doc (E2-N4). |
| N1 (stability check weak on rig) | **deferred** (owner's question; trigger: the owner's ruling) | Recorded as item 1 in `fuel_antialiasing.md`. `test_a_hard_edged_line_crawls_beyond_the_ideal_but_only_near_the_bar` now states the weakness rather than a bar. Rerun with hard edges in `fuel_rod_fringe.gdshader`: rig-30 1.16 (passes), rig-72 2.12, laptop-72 5.78, laptop-30 5.90. Same as round 1. |
| N2 (in-place upload has no pixel gate) | **deferred** (trigger: step 8's checklist item, `checklists.md` l. 325–326, "a two-frame golden for the in-place segment upload") | Still true. I replaced `texture.update(image); return texture` with `return texture` on the 03:07 tree, and all 74 client tests pass. The trigger sits inside this same step, so it has to land before step 8 closes. |
| N3 (`stability_findings` passes `{}`, crashes, divides by zero) | **fixed** | `golden_stability.findings` requires `KEYS` and `OFFSETS`. A missing record or frame is a finding, and an ideal of 0 is reported rather than divided by. The tests cover missing, partial, short and ideal-0. Small residue: an entry without `ends` or `drawn_px` raises `KeyError` (NIT, not filed separately). |
| N4 (instance encoding limits unchecked) | **fixed** | `MAX_OBJECTS` 2,000 and `MAX_SEGMENTS` 20,000 are checked in `_shape_problems` before any size is multiplied, and tested at limit + 1 and at −1. |

## New findings

### E2-S1 SHOULD-FIX: a refused frame still rebuilt (fold tree); fixed in the 03:07 tree
**Location:** `client/addons/engine/render/fuel_pass.gd::show_fuel` (fold tree).

**Defect.** `show_fuel` ran `problems()` and then `_rebuild(snap)`, and only afterwards `frame_problems()`. A frame whose structure changed and passed the structural check, but carried a state above 1, was refused only after the rebuild. New transforms and instance textures were then drawn with the previous frame's segment and state textures. That breaks the docstring ("a refused frame draws nothing new") and CLAUDE.md's "never a half-applied change".

**Reproduced.** My probe (`delta_executor/client/tests/probe/probe_half.gd`) changed rod 0's radius and set `state[0] = 7`. The result was `["object row 0 has state 7…"]` with `rebuilds` going from 1 to 2.

**Failure scenario.** An insertion arrives in the same message as a corrupt state byte. If segment rows were added, the old textures are too short: fragments past them read 0, which counts as burnt through, so whole objects vanish until the next good frame.

**Status in the 03:07 tree.** `frame_problems()` now runs first. `test_a_refused_frame_with_a_good_structure_draws_nothing_new` covers it ("an insertion refused per frame rebuilds nothing"). Moving the check back by deletion turns 4 checks red. Verified on the 03:07 copy.

### E2-S2 SHOULD-FIX: the pass-level per-frame refusal was unguarded (fold tree); fixed in the 03:07 tree
**Location:** `client/tests/unit/render/test_fuel_pass.gd::test_a_refused_frame_draws_nothing_new` (fold tree).

**Defect.** The test's second half restores rod 0's radius to 0.005. The fixture's radius is 0.01 (I printed it), so the structure changed. The short `ignited_fraction` column was therefore caught by `problems()`'s shape check, never by the per-frame check the test names.

**Proof.** In the fold tree I turned `show_fuel`'s `if not frame.is_empty(): return frame` into `if false and …`. All 72 client tests passed.

**Failure scenario.** A refactor drops the per-frame check from `show_fuel`. A frame with a short or invalid per-frame column then uploads a short texture, or a state of 2, with no gate going red.

**Status in the 03:07 tree.** The same deletion turns `test_a_refused_frame_with_a_good_structure_draws_nothing_new` red (4 failures). Verified on the 03:07 copy.

### E2-S3 SHOULD-FIX: TB-S4's temperature clamp has no guard
**Location:** `client/addons/engine/render/fuel_object.gdshaderinc::fuel_colour` (`clamp(..., FUEL_MIN_C, FUEL_MAX_C)`).

**Defect.** The fold lists TB-S4 as folded, but no fixture segment holds an f16 ±inf or a value past 6,000 °C. I deleted the clamp and ran `golden_run.py --no-xvfb`: PASS. Against the base frames, every tier's fuel frame differs by mean ΔE 0.0, so the CI goldens can't see the deletion either.

**Failure scenario.** The clamp is lost in a shader edit. A server sends f16 inf for a segment, which §3.3's clip should prevent but which a client must survive. `glow_curve` gets inf, the HDR output goes to inf or NaN, and bloom smears or blacks out the frame. No gate notices.

**Fix (unverified).** Put one f16 inf segment, and one at 1e4, in a fixture region the glow check reads. Then check that the segment reads no brighter than one at 6,000 °C and that no NaN or black pixel appears.

### E2-N1 NIT: the dead-flame check names the wrong object
**Location:** `scripts/golden_fuel.py::dead_flame_findings` with `FLAME_REACH_M = 0.4`.

**Defect.** `rod_spent` (y = 1.6) and `rod_gap` (y = 2.0) are 0.4 m apart. Each one's window, widened by 0.4 m, therefore takes in the other rod's flames. Measured:
- Deleting only the burnout half reports 131–157 px "at `rod_gap`".
- Deleting only the burn-through half reports 34–42 px "at `rod_spent`".

The gate still goes red, but the findings point at both mechanisms when only one broke.

**Failure scenario.** A regression in the burn-through half reports dead flames at `rod_spent`, and the debugger looks at burnout first. Any future ignited object within 0.4 m of either rod would also false-positive.

**Fix (unverified).** Move the two rods apart by more than twice the reach, or attribute each flame pixel to its nearest object.

### E2-N2 NIT: nothing guards the shader's read of the palette slot
**Location:** `fuel_object.gdshaderinc::fuel_colour` (`recipe_colours[clamp(inst.recipe, 0, 15)]`) and `instance_at` (`inst.recipe = byte_of(a.a)`).

**Defect.** I replaced the lookup with `recipe_colours[0]` and ran `golden_run.py --no-xvfb`: PASS. Against the base frames with `golden_compare.compare`, the fuel frames differ by mean ΔE 0.004, p99.5 0, largest blob 0 px. That is far inside the golden tolerance (mean 1.0; blobs 64 px at ΔE 10), so CI's goldens would pass it too. The reason is that `pine_rod` and `pine_slab` are nearly the same colour, and only one small slab carries `pine_slab`. The fold's tests now hold the CPU half: byte 3 is asserted and slot 15 is magenta.

**Failure scenario.** A shader edit reads the wrong channel, or reads slot 15 for every object. Every fuel object then draws one recipe's colour, or all of them draw magenta, and nothing goes red.

**Fix (unverified).** A fixture recipe whose colour stands far from the others, plus a colour check on its pixels.

### E2-N3 NIT: the flames' culling box ignores flicker
**Location:** `fuel_pass.gd::_fit_boxes` (`reach = FLAME_HEIGHT_M + …`) and `fuel_flame.gdshader::vertex` (`height_m = flame_height_m * sqrt(ignited) * (1 + flame_flicker * 0.2 * sin(...))`).

**Defect.** In play (`use_flicker(1.0)`), a flame reaches 1.2 × `FLAME_HEIGHT_M`, 0.04 m past the box. `use_flicker` also takes any amount without bounds. `test_culling_boxes_hold_what_the_shaders_draw` uses the unflickered height, so it can't see this.

**Failure scenario.** The box sits just below the bottom of the view while a flickering tip rises above the box's top face into view. The tip is culled, a pop at the screen edge. It is cosmetic, but it is exactly what C-S2's fold set out to rule out. Still present in the 03:07 tree.

### E2-N4 NIT: the fold record's claims trail the tree
**Location:** `docs/design/reviews/client_fuel/fold.md`.
- It says the insertion takes 13.8–14.2 ms on `bench_fuel.gd` (a scratch probe). §4.1 says 14.1–14.5 ms on `tools/fuel_aa/rebuild_time.gd`, and I measured 14.26–14.54 ms.
- It says "Client tests: 72 pass". That held in the fold tree; the 03:07 tree has 74.
- It says `client_objects.md` has "5,179 words against 5,180". `wc -w` gives 5,180 now (base 69483d9: 5,180), and `client_rendering.md` 3,740 against 3,742. Both are within budget; only the first number is off by one.

**Failure scenario.** The hand-off note quotes the fold record's numbers, and they don't reproduce.

## What I checked and found sound
- **Client tests.** 72 pass on the fold tree and 74 on the 03:07 tree (headless, a scratch copy, HOME and XDG redirected).
- **Python suites.** `tests/test_golden_fuel.py`, `test_golden_stability.py`, `test_golden_run.py` and `test_fuel_fixtures.py`: 68 passed.
- **Mac golden run.** `golden_run.py --no-xvfb` from a scratch repo copy: PASS (24 shots, cut-away).
- **Stability on Mac.** rig-72 1.10, rig-30 0.99, laptop-72 1.20, laptop-30 0.78, drawn width 2.0 px. These match the research doc's Mac numbers. I did not rerun llvmpipe.
- **C-S1, the two-pass rods.** With the depth pass discarding every fragment, the crossing check fails on every tier: laptop 7.1 L*, rig 7.7, max 7.7. The fold's 7.1–7.7 reproduces.
- **Culling boxes.** Removing the flame height from the box's reach turns `test_culling_boxes_hold_what_the_shaders_draw` red. `FuelGeometry.bounds` is tested against a turned box's corners. On the fold tree, the rod box's fixed `3.0 * px` equalled px·(1 + 1/0.5) exactly at the laptop tier's 0.5 scale. The 03:07 tree derives it from the render scale.
- **Slab growth.** Anchoring at the segmented face is bounded by `SLAB_MAX_GROWTH_PX` (2 px / 0.25 = 8 px). Deleting the anchor changes no measured check (blob 2–4 px): there is no stick-on-slab fixture yet, as the checklist (l. 323) records.
- **Structural refusals.** Each one in `test_every_structural_check_refuses` names its row. Sizes are refused at 0, −0.02, NaN and ∞ in every size column. Shared and out-of-range vocabulary ids, rising `object_id`s and perpendicular slab axes each have a case.
- **The flame-to-segment map.** `FuelGeometry.segment_objects` matches the order `flame_buffer` places flames in, and the test checks each object's first segment and the last row.
- **The palette rebuild.** Changing only a palette slot rebuilds; the same palette again doesn't (`test_only_a_structural_change_rebuilds`).

## What I did not verify
- llvmpipe anything: the CI goldens, §7.2's checks under llvmpipe, and the stability numbers 1.08/0.98/1.20/0.78.
- The coverage channel's encoding per tier (W-S5), which the fold also marks open.
- The flames' render priority against the rods' colour pass. No check sees it, and I didn't probe it.
- A1, the two §7.2 bars rewritten without a ruling: the owner's.
- The 03:07 tree beyond the deletions named above. It was still changing (`checklists.md` at 03:07:04), so the next delta has to review the committed diff.
