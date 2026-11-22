# Delta round: Client and rendering + Performance, phase1/fuel-leftovers (after round 1's folds)

Reviewer: Client and rendering and Performance lenses (round 1: `client_rendering.md` CR-*, `performance.md` P-*).
Read from the tree: `git diff 2586ed7` for `client/addons/engine/render/` (fuel_pass.gd, fuel_rod*.gdshader(inc),
fuel_object.gdshaderinc, fuel_snapshot.gd), `client/tests/golden.gd`, `client/tests/support/golden_shot.gd`, the
unit-test diffs, `scripts/fuel_fixtures.py`, `scripts/golden_fuel.py`, the doc diffs, `fold.md`, owner rulings 6–9.

Ran:
- `tools/fuel_aa/rebuild_time.gd` headless (Godot 4.7.2 editor build, M2, load average 9–14), on copies of `client/`
  in my scratchpad (this tree and `git archive 2586ed7`), HOME/XDG moved there. Nothing written in the worktree.
- A ray-cast model of the three rod passes (smooth cylinders, the shader's coverage rule and widened shell, the depth
  test as "nearest silhouette wins"):
  `<scratchpad>/delta_sim/cross.py`
  (the fixture's crossing, four yaws, rig and laptop) and `.../delta_sim/cases.py` (two touching 5 mm sticks; two
  touching 50 mm logs). It models geometry, not Godot. It was not checked against a render.
- No pytest, gate, Docker or golden run.

## Status of round 1 findings (set from the tree)

| Finding | Status | Evidence in the tree |
|---|---|---|
| CR-1 (centre sort wrong off centre; fixture crossed at both centres) | **fixed** | The sort is gone (`fuel_geometry.gd` matches base; no `back_to_front`/`permute_*` anywhere in `client/`). The colour draws core (priority 1) then fade (priority 2) for every rod, so the order no longer depends on instance or camera. The fixture's crossing moved to 0.15 m off the log's centre and 0.1 m off the stick's. In my model the four yaws give identical results. One limit the fold's wording overclaims is new finding N-1. |
| CR-2 (band twice the fade's reach; "a quarter" wrong; 0.8 L* margin) | **fixed** | The derivation now says band 1/8 and strip 7/8, which is right for a 1 px band with the fade's 0.5 px reach and a floored 2 px stick (rig and max render at scale 1). The bar is in linear Y (`_mean_y`), re-derived under owner ruling 8. Measured margin: deletion 0.021 against a bar of 0.071 (3.4×). The old margin was 0.8 L*. The premise of the model is off for this fixture: see N-3. |
| CR-3 (no caller of `use_view_direction`) | **fixed** (moot) | The function and the cached rod buffers are removed, and nothing needs the camera. |
| CR-4 (leaning-plank derivation) | **fixed** | `fuel_fixtures.py::leaning` gives 29.8 mm (rig, max), 43.7 mm (laptop) and the 1.9 mm laptop margin. I rechecked the arithmetic: the 2 mm lift, 13.9 mm floor, 13.9/27.8 mm render pixel, and (111 − 20)/2 = 45.6. All agree. |
| CR-5 (ruling 6's "8-bit target" mechanism) | **fixed** | Ruling 6 now states what was measured: llvmpipe, linear tonemapper, +∞ pixel-identical to 6,000 °C, other cases not measured. The shader comment is narrowed. `fuel_snapshot.gd`'s "can't be seen in an 8-bit frame" refers to the captured PNG, which is 8-bit, so it is accurate. |
| CR-6 (transform/instance-row pairing untested) | **fixed** (moot) | `_place` writes instance i from geometry row i, as on main. No permutation is left to pair. |
| CR-7 (animated turn re-sorts) | **fixed** (moot) | No sort. |
| P-S1 (per-turn sort cost unrecorded) | **fixed** (moot) | The sort is gone. The cost the fold adds instead is N-2. |
| P-N1 (texture recreated per turn) | **fixed** (moot) | No turn path. `_place` recreates the instance texture only on a rebuild, as on main. |
| P-N2 (animated turn re-sorts) | **fixed** (moot) | No sort. |
| P-N3 (`area_findings` recomputes `ideal_coverage`) | **open** | `golden_stability.py::area_findings` is unchanged. The author says open (NIT) but names no trigger, so this is not a deferral. It becomes "deferred" if a trigger is named, such as "when keys or resolution grow". |

## The core/fade split: what I checked, and what holds

- **Ordering in the transparent pass.** All four rod and flame materials blend (`blend_mix`/`ALPHA`, flames
  `blend_add`), so they all go to Compatibility's alpha list. That list sorts by `render_priority` first, then by
  depth. The chain `rod → rod_core → rod_fade` (two `next_pass` links on `material_override`) gives priorities 0, 1, 2,
  and flames 3. `test_a_rods_colour_core_then_fade_follow_its_depth_and_get_every_uniform` holds the chain, the shaders,
  `fade_half` and the priorities. No other client material sets `render_priority`. The one MultiMesh is one render
  element per pass, so instance order matters only inside a pass. This is unmeasured in source, but the author's
  deletion (0.396 → 0.021 on rig/max) shows the third pass draws, and draws after the cores, on llvmpipe.
- **Uniforms.** `_param` iterates over material names and `_param_on` over `KIND_MATERIALS["rod"]`, so
  `render_pixel_m`, `floor_half_m`, `instance_tex` and the rest reach both colour materials. `fade_half` is set once in
  `_init` and nothing resets it.
- **Exactly one half per fragment.** The depth pass discards `rod_coverage < 0.5`. The core discards `coverage <= 0 ||
  coverage < 0.5`. The fade discards `coverage <= 0 || coverage >= 0.5`. The comparison is the same and the
  `rod_coverage` code is the same, and core and fade are one shader. The widened shell is convex and drawn with
  `cull_back`, so each rod has one front fragment per pixel. A fragment therefore lands in the core or the fade, never
  both, and the core region is the depth silhouette. Residual risk: the depth pass is a different program, so a
  compiler could round a coverage at exactly 0.5 differently. That case is measure-zero, and it predates the fold.
- **The depth test each pass meets.** The depth pass writes the nearest widened shell (`depth_draw_always`). Core and
  fade are `depth_draw_never` and test against it. A rear rod's fade inside a front rod's silhouette is therefore
  hidden. A front fade outside its own silhouette passes over a rear rod's core wherever the front shell is nearer.
  That holds except where the shells interpenetrate (N-1).
- **Fade over fade.** Two fades overlap only outside both silhouettes. They draw in instance order at the same
  priority, so the rear's fade can land on the front's. The error is a_f·a_r·(C_f − C_r), at most 0.25·ΔC because both
  alphas are below 0.5. At a crossing it covers four sub-pixel corner patches. This is NIT N-5.
- **Flames after fades.** Priority 3 is above 2, and the flames still depth-test against the silhouettes, as on
  main. C-S2's concern is kept.

## New findings

### N-1 SHOULD-FIX: "a front fade lands on a rear rod at any crossing" is false for touching rods, whose widened shells interpenetrate; for two touching sticks, the rear stick's fade now always draws over the front stick's core

`client/addons/engine/render/fuel_rod.gdshaderinc::vertex` widens every rod's mesh to `drawn + render_pixel_m`, and the
depth pass writes that shell's depth. For rods that touch, the rear rod's shell reaches in front of the front rod
near the contact. A floored stick is drawn 2.8× its real 5 mm radius, and every rod gains one more rendered pixel.

Ray-cast results (fixture geometry, smooth cylinders, any of the four yaws, which agree):

| Case | Front fade over rear core, hidden by depth | Front core over rear, hidden | Rear fade drawn over front core |
|---|---|---|---|
| Fixture: 5 mm stick on 50 mm log, rig | 12% of band samples (9.5% of its coverage) | 0 | 0 |
| Same, laptop | 16% | 0.6% | 64 of 3,398 samples (1.9%) |
| Two touching 5 mm sticks, rig | 39% | 10% | 16% (423 of 2,653) |
| Same, laptop | 42% | 10% | 22% |
| Two touching 50 mm logs, rig and laptop | 0 | 0 | 0 |

Where a rear shell is nearer, the core-then-fade order now puts the rear rod's fade on the front rod's core every
time. With main's single pass, that happened only in half of the instance orders. So for crossing kindling (thin
sticks resting on thin sticks, the common case in a pile), the fold turns an order-dependent artefact into a
deterministic one. It also leaves 39% of the front fade hidden. The shell interpenetration itself predates the fold:
it is main's depth pass.

**Failure scenario.** A hot 5 mm stick resting across a cold 5 mm stick. Near the contact, the hot stick's edge is
notched (10% of its overlap hidden). The cold stick's fade blends over the hot core there, and 39% of the hot stick's
outer fade is missing. None of this is checked: the only rod crossing in the fixture is stick-on-log, where the loss is
about 10% and the 1/14 bar passes easily (0.396).

The record overstates this in four places:
- owner ruling 7 ("at any crossing, yaw and instance order")
- `client_objects.md` §4.2 ("whatever the order")
- `checklists.md` step 8 ("at any crossing")
- `fuel_rod_fringe.gdshader`'s header ("a front rod's fade always blends over a rod behind it")

**Fix (unverified, the author's call).** State the limit with its numbers as a known gap beside D1's inner half: the
outer fade holds only where the front shell stays nearer, which fails for touching rods within about one shell
thickness of contact. Add a touching stick-on-stick crossing to the fixture, so the limit is measured rather than
derived. A mechanism change belongs to step 8 and is not this review's to design. One direction would be depth from
the drawn rather than the widened surface.

The model's caveats: 12-sided facets change shell depth by up to 3.4% of the shell radius (about 0.9 mm on a
27.8 mm shell), small against interpenetrations of several mm. Real Godot depth precision is not modelled.

### N-2 SHOULD-FIX: the steady frame's design number is now 20× stale; the per-snapshot temperature check sits outside every client budget

`client/addons/engine/render/fuel_snapshot.gd::_temperature_problems` is a GDScript loop over every segment
(`decode_half` and two compares). It runs in `frame_problems`, which `FuelPass.show_fuel` calls on every snapshot,
steady frames included.

Measured with `tools/fuel_aa/rebuild_time.gd` at the world limits (2×10⁴ segments), headless editor build, this M2
under load 9–14, back to back:

| | steady frame, min | median |
|---|---|---|
| base 2586ed7 | 0.10 ms | 0.19 ms |
| this tree | 1.80–1.83 ms | 1.90–3.62 ms |

This agrees with the author's 1.5–1.8 ms for the check alone. The insertion grows too, from 14.1–14.5 ms (§4.1) to
18.7–21.0 ms here, though load inflates my numbers.

Where this sits against the budgets:
- **Cadence.** It runs once per cell-frame message (2 Hz, §4.1), not per rendered frame. Ruling 9 and B5 say "a frame",
  which reads as the 16.7 ms render frame. It costs about 11% of one 60 Hz frame every 30 frames, on the main thread.
- **No budget covers it.** `client_rendering.md` §8's 3 ms decode-and-upload budget covers the cell textures only, and
  is already broken (B5). The fuel pass has no budget of its own; B5's fuel row lists it as owed. Adding this to the
  cell decode on the same tick makes the hitch worse.
- **B5 records it,** which satisfies "measured, not guessed".

What is wrong in the tree:
- `client_objects.md` §4.1 still says "a steady frame 0.08–0.09 ms". This is a contract number another module's budget
  work will read, and it is now about 1.8 ms.
- `fuel_pass.gd::show_fuel`'s docstring still says a steady burn costs "a compare, a short check and its segment
  uploads". The check is now a full pass over every segment.
- The §2 table's measured costs do not include it.

**Failure scenario.** Step 8's budget work, or B5's fuel row, takes §4.1's 0.08 ms steady frame as the baseline, sets a
bar from it, and either fails at once or never sees the 1.8 ms.

**Fix (verified as measured above; the edits are unverified).**
- Replace §4.1's number with the measured one, marked [ran], with its conditions. The word count does not change.
- Correct the docstring.
- Say "per snapshot (2 Hz)" in ruling 9 and B5.

Whether 1.8 ms per snapshot is acceptable is the owner's call, which ruling 9 already made knowing the number. I don't
reopen it.

### N-3 NIT: the coverage model's 1/7 does not describe the measured fixture (0.396, 2.8× the model), and the record doesn't say why

`golden_fuel.py::FADE_SHARE`'s comment and `research/fuel_antialiasing.md` derive the bar as half of an intact share of
1/7 = 0.143. The measured intact share is 0.396, and the deletion leaves 0.021, so the fade itself contributes about
0.375. My hypothesis, unverified (I did not read the noflame frames): the 1,500 °C stick's HDR emission saturates. Its
core reads clipped white rather than 7/8 of its colour, and band pixels with coverage × emission ≥ 1 clip too, which
inflates the ratio.

Saturation only raises an intact share, so the bar stays a valid lower bound, and the deletion side (0.021 against
0.071) is what guards D1. Still, the model the bar is "derived from" is off by 2.8× on its own fixture, and a reader
re-deriving it later has no explanation. Bars are meant to be derived from their source's error, and "half" is a factor
the owner ruled (ruling 8), so I don't contest it.

**Fix (unverified).** One sentence in the research note: the model assumes an unsaturated stick, the fixture's
measures 0.396, and the deletion residual (0.021, bloom) is what the bar is placed against.

### N-4 NIT: the research note's "Shipped" row and one unwrapped line predate the fold

`docs/design/research/fuel_antialiasing.md`:
- The depth table's **Shipped** row still reads "then the colour blended over the whole ramp". Since ruling 7 that is
  two passes, core then fade, which the paragraph below it says.
- The line beginning "(coverage ≥ 0.5) draws before any rod's fade… The check, on rig and max (ruling 8): the fade
  band's linear gain over the log is" is about 160 columns, unwrapped against the file's 120.

**Failure scenario.** A reader of the table takes the shipped configuration to be one colour pass, which is the
configuration the deletion row measures as broken.

### N-5 NIT: fade over fade still draws in instance order

`fuel_pass.gd::_init`: both rods' fades share priority 2, so where the fades of two rods overlap, outside both
silhouettes, the later instance's fade lands on top. The error is a_f·a_r·(C_f − C_r), at most a quarter of the colour
difference. It covers sub-pixel corner patches at a crossing, and strips where parallel rods lie within a rendered
pixel of each other. It is deterministic, does not depend on the camera, and is small. Recording it keeps "whatever
the order" from being read as covering it.

### N-6 NIT (Performance): the third rod pass's GPU cost is unmeasured, and §2's "+0.24 ms object pass" predates it

Rods now rasterize their widened shell three times. Each time, the fragment runs `rod_coverage`: the instance-texture
fetch, the segment-row lookup and the `burnt_through` fetch. The fade pass then discards the core fragments. That
makes rod fragment work about 1.5× main's two passes. The `client_objects.md` §2 row ("The object pass at 2,000
instances … +0.24 ms") doesn't say which pass configuration it measured. B5 already owes the fuel pass's frame time,
so this needs no new row. It is a note that the number in §2 is not the shipped configuration's. I could not measure
it: the headless renderer is a dummy, and this Mac's frame-time tool reports a GPU meter of 0.

## Summary

- Statuses: CR-1 to CR-7 are fixed, three of them substantively (CR-1, CR-2, CR-4), one by narrowed wording (CR-5),
  and three moot by the sort's removal (CR-3, CR-6, CR-7). P-S1, P-N1 and P-N2 are fixed (moot). P-N3 is open.
- No BLOCKER. Two SHOULD-FIX:
  - N-1: touching rods' shells interpenetrate, so "any crossing" is false, and for touching sticks the rear fade now
    always lands on the front core.
  - N-2: §4.1's steady frame is now 1.8 ms against 0.08 ms on the page, and the cadence wording is ambiguous.
- Four NITs: N-3 to N-6.
