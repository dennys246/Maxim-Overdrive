# Performance review: phase1/client-fuel, delta 1 (round 1 → fold)

Reader: Performance lens. Tree: the worktree as it stood on 2026-11-22 around 03:00. HEAD is d91df0f, and the fold is
uncommitted in the working tree. I read the fold record `docs/design/reviews/client_fuel/fold.md` as claims, not
statuses. I measured on a copy of `client/` in
`<scratchpad>/delta_performance/client/`:
- Godot 4.7.2 on the M2, with HOME and XDG under that directory.
- GDScript warnings demoted to warnings in the copy only.
- Benches in `client/bench/`: `bench.gd` (mine), `author_bench.gd` (a copy of the author's `scratchpad/bench/bench_fuel.gd`) and `frame_time.gd` (the committed tool plus two env knobs and an `onepass` mode).

Load average was 8.4–10.9 on 8 cores throughout, so absolute times are inflated. Where it matters I ran the author's
bench and mine back to back under the same load. I wrote nothing in the worktree.

## Status of my round-1 findings (set by me, from the tree and my reruns)

| ID | Status | Evidence |
|---|---|---|
| P-B1 rebuild 52–71 ms | **fixed** | Columns are decoded once (`FuelSnapshot.floats`, `FuelGeometry.Rods/Slabs`), and each MultiMesh gets one `buffer` assignment. Insertion through `show_fuel` at the limits (headless) is 15.5–16.5 ms min/median on my fixture and 15.8–16.5 ms on the author's, run back to back under load 9. Earlier runs on the author's bench gave 14.5–15.2 ms under load 10.8. That is consistent with the cited 13.8–14.2 ms once load is allowed for. The cited figure is now the shipped path's, in §4.1, §7.4 and B5. |
| P-S1 `problems()` 29–41 ms | **fixed** | 3.6–4.6 ms on my fixture, with 0, 200 or 500 slabs (the author cites 3.4–3.5 ms). The value sets are built once, and `kind_name` is no longer called per row. |
| P-S2 trigger concatenation | **fixed** | `structure()` takes 14–15 µs. Comparing it against a separately built, equal snapshot (step 7's case: new arrays, same bytes) takes 11 µs. A steady `show_fuel` on an equal copy takes 0.107–0.119 ms, and 0.102–0.111 ms with new per-frame values (author: 0.09–0.10 ms). `rebuilds` stayed at 1 in every run. The row counts are in the structure (`#rows`), which closes the caveat I raised. |
| P-S3 `frame_time.gd` broken | **fixed** | The committed tool parses and runs against the shipped pass. I only added knobs; its own code paths are unchanged. The research note's shipped table cites it, with modes `off`, `noflame` and `shipped`. |
| P-N1 `use_palette` always rebuilds | **fixed** | Resending the same palette and then a frame leaves `rebuilds` at 1 and costs 0.108–0.120 ms. |
| P-N2 per-instance fetches in fragment | **fixed** | The instance fields are fetched in `vertex()` as flat varyings. Per-fragment fetches are now 1 in the rod's depth pass and 5 in the rod's colour pass and the slab, down from 8. The slab's `discard` (early-z) part stands, but it is intrinsic to dropping burnt-through segments per pixel, so I don't pursue it. |
| P-N3 `_mean_l` Lab over the frame | **fixed** | `golden_fuel.fuel_findings` on `scratchpad/docker_confirm` (the fold's frames, which pass) takes 0.94 s on the Mac host, down from 7.8–8.6 s. What remains is `strip` (0.34 s) and the PNG decode (0.21 s). |
| P-N4 §4.1 stale layout | **fixed** | §4.1 now states the shipped texels and `state` as its own texture, matching `fuel_pass.gd::_place` and `fuel_object.gdshaderinc::instance_at`. |

## What the fold added: measurements

**Insertion at the world limits, headless.** These are my fixture's numbers: 2,000 rods with varied axes, a third of
them near vertical (so `rod_buffer`'s `EAST` branch runs, which round 1 never exercised), 10 segments each. Min /
median of 7 runs, under load 9–10.

| Part | Time |
|---|---|
| `show_fuel` insertion (check + rebuild + uploads) | 15.5–17.0 / 16.4–20.1 ms |
| `problems()` | 3.7–4.0 / 3.8–4.2 ms |
| `FuelGeometry.flame_buffer` (2×10⁴ segments) | 6.0–6.4 / 6.3–8.0 ms |
| `FuelGeometry.rod_buffer` (2,000) | 3.5–3.6 / 3.8–4.3 ms |
| `FuelGeometry.slab_buffer` (500 slabs) | 1.07 / 1.18 ms |
| `FuelGeometry.bounds` (2,000 rods) | 0.87–0.88 / 0.88–0.94 ms |
| `FuelGeometry.segment_objects` | 0.38 / 0.39 ms |
| `FuelGeometry.widest_flame_m` | 0.09 ms |
| `geometry_rows("rod")` | 0.12 ms (called 6 times per insertion, check included) |
| `first_rows()` | 0.08 ms (called twice) |

**Per frame.** `frame_problems()` takes 0.050–0.055 ms, half the steady frame. It is a GDScript loop over 2,000 state
bytes. The new `segment_object_tex` (RF, 80 KB) uploads only on a rebuild.

**Frame time, windowed.** Settings: opengl3 Compatibility, 1280×720, `--disable-vsync`. Each figure is the min /
median of 300 intervals after 30 warm-up frames, over two interleaved runs per mode. `onepass` is the shipped pass
with the rods' material set to the colour pass alone (no depth pass), with flames on. It is a probe, not a shippable
mode, since it reintroduces C-S1.

| Mode | Golden view (10 m, 72 px/m, 10 mm sticks) | Close (6 m, 120 px/m, 50 mm rods overlapping) |
|---|---|---|
| Off (pass hidden) | 3.90–3.93 / 4.41–4.45 ms | 5.37–5.41 / 5.84–6.09 ms |
| No flames | 3.96–4.04 / 4.46–4.55 ms | 5.60–5.63 / 5.85–6.14 ms |
| One pass, flames | 4.02–4.11 / 4.49–4.50 ms | 5.63–5.65 / 5.95–6.14 ms |
| Shipped (two passes, flames) | 4.11–4.20 / 4.57–4.66 ms | 5.73–5.78 / 6.14–6.17 ms |

At the golden view the shipped pass adds +0.18–0.30 ms min over hidden, which matches the author's +0.15–0.3 ms. The
second rod pass costs about 0.0–0.18 ms there. In a fill-heavy close view the pass adds +0.32–0.41 ms, and the second
pass about 0.08–0.12 ms. On the M2 the two-pass rod is cheap.

**Golden job wall time, from the author's `docker_fold.log`.** Each call took 8.2–13.5 s of the 120 s limit.
`golden_stability.findings` on `docker_confirm/stability` took 1.23 s.

## New findings

No BLOCKER or SHOULD-FIX. Three NITs.

### PD-N1 NIT: §7.4's frame-time figure is the design probe's, not the shipped pass's

**Where:** `docs/design/client_objects.md` §7.4 ("+0.24 ms at the limits, M2") and the §2 row it echoes ("1 ring,
golden view … +0.24 ms", citing the design review's `performance.md` P-S3).

**Defect.** The budget section states the cost of a single-pass rod probe. That probe predates the two-pass rods and
the per-object flames. The shipped measurement lives in `research/fuel_antialiasing.md` ("Frame time") and in B5:
+0.15–0.3 ms on `tools/fuel_aa/frame_time.gd`. My rerun gives +0.18–0.30 ms min. So one quantity has two numbers in
two places, and the one in the budget section is off the shipped path. That is the same defect class P-B1 had for the
rebuild, though here the numbers happen to agree.

**Failure scenario.** Step 7 seeds B5's frame-time baseline from §7.4 and gets the probe's number and conditions. Or
a later shader change re-records the research note, and §7.4 silently goes stale.

**Fix (unverified, doc-only).** Have §7.4 cite the research note's shipped table instead of restating a number. This
is "one owner per contract", and it doesn't grow the document.

### PD-N2 NIT: the frame-time tool sees only a low-fill view, so a fill regression in the two rod passes can't show

**Where:** `tools/fuel_aa/frame_time.gd::_setup` (a fixed 10 m view and 10 mm sticks).

**Defect.** At the golden view every rod is floored to about 2 px, so the rod passes cover almost nothing. The fold
doubled the rod fragment work, and the depth pass is a blended draw at alpha 0: each covered fragment does a
framebuffer read-modify-write that changes nothing. Both costs scale with covered pixels, and the tool's only view has
almost none. My close-view variant shows the pass's cost rising to +0.32–0.41 ms on the M2. That is still cheap, but
the committed record can't see it. Under llvmpipe the blending is CPU time and remains unmeasured; the record says
so.

**Failure scenario.** A later change makes the colour pass's fragment heavier, or makes the depth pass cover the
whole widened rod. At the golden view the rerun shows noise. At 120 px/m with thick logs the frame cost moves, and
nobody measured it.

**Fix (verified that it runs; not proposed as the bar).** Add a close-zoom, thick-rod mode. My scratch patch
(`FT_SIZE`, `FT_RADIUS` env knobs) runs and gives the column above.

### PD-N3 NIT: the rods' culling box has no margin at render scale 0.5, and too little below it

**Where:** `client/addons/engine/render/fuel_pass.gd::_fit_boxes` (rods grow by `3.0 * px`), against `fuel_rod.gdshaderinc::vertex`.

**Defect.** The vertex shader widens a rod by `max(r, px) + px / render_scale − r`, which is at most
`px · (1 + 1/scale)`. At scale 1.0 that is 2 px, and at the laptop's 0.5 it is exactly 3 px, so there is no margin.
`RenderTier` accepts any scale in (0, 1], and `use_pixel_metres` accepts any positive scale. At scale 0.4 the widening
is 3.5 px against a 3 px box.

**Failure scenario.** A future tier at scale 0.33 culls a rod whose fringe is on screen at the viewport edge. The rod
pops in about 1 px late as the camera pans. This is small, and a rendering-lens overlap: I found it by reading, not
running.

**Fix (unverified).** Grow the box by `px · (1 + 1/scale)` from the scale `use_pixel_metres` already receives. This
is C-S2's box. Alternatively, refuse a scale below 0.5 where tiers are validated.

## Checked and found adequate

- **`structure()` compare.** Comparing natively against separately built arrays costs 11 µs for about 220 KB of
  structural bytes. Same-object versus copy makes no difference that matters.
- **`FuelGeometry.bounds`, `widest_flame_m`, `segment_objects` and `_fit_boxes`.** All are under 1 ms per insertion,
  and nothing runs per frame.
- **The flame shader's vertex work.** Four `texelFetch`es per vertex across 8×10⁴ vertices: flames cost 0.0–0.1 ms
  over no flames at the golden view. The data-sized culling box replaces the ±1000 m box, which can only help.
- **The per-frame `_param` calls** set each texture on four materials even when it was updated in place. This is
  inside the 0.10–0.12 ms steady frame.
- **`golden_fuel`'s new checks** (crossing, burnout, dead flames, agreement per object) run within the 0.94 s above.
- **Insertion is still about one 60 Hz frame at the limits** (14–16 ms). This is not a new defect. The design calls it
  "a reported row", and B5 records it with no meter and no bar, so nothing would catch a regression. That gap is B5's,
  owed at step 7.

  Where the rest goes:
  - `flame_buffer` is about 40% of the insertion. It is a GDScript per-segment loop.
  - `problems()` is about 25%.
  - `geometry_rows` runs six times per insertion. Hoisting it would save under 1 ms, so I don't pursue it.

## Not verified

- Frame cost under llvmpipe, and the laptop tier's frame time on real hardware.
- Whether `onepass` and the shipped pass draw the same pixels. `onepass` is a cost probe only.
- The author's absolute 13.8–14.2 ms figure at low load. Under load 9–11 I get 14.5–16.5 ms on their own bench, and
  my fixture matches theirs back to back.
- Behaviour above the world limits, which are now refused.
