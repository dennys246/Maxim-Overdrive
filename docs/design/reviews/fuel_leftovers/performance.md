# Performance lens: phase1/fuel-leftovers (diff against 2586ed7, uncommitted tree)

Reviewer: Performance lens. Read: `fuel_pass.gd`, `fuel_geometry.gd` (diff and surrounding code), `render_stage.gd::aim`,
`iso_camera.gd`, `golden.gd::_show_next`, `golden_stability.py` (whole), the `golden_fuel.py` diff, `client_objects.md`
§7 budget table, `standards_backlog.md` B5.

## What I measured

All numbers come from this Mac (Apple M2, load average 9 to 12 while I ran them), so treat them as upper-side numbers.

**1. GDScript sort and permutes** (my bench: a copy of `back_to_front`, `permute_floats`, `permute_bytes`, run headless
under Godot 4.7.2 from the editor binary, 20 repetitions each, random transforms). The bench is in
`<scratchpad>/perf/gd/bench.gd`.

| Rods | `back_to_front` | `permute_floats` | `permute_bytes` | Total per sort |
|---|---|---|---|---|
| 100 | 48 µs | 39 µs | 42 µs | 0.13 ms |
| 2,000 (the world limit) | 856 µs | 638 µs | 618 µs | **2.1 ms** |
| 20,000 (not a limit for rods; scaling only) | 10.4 ms | 6.5 ms | 6.2 ms | 23 ms |

- I also timed a presized copy (resize the output, then a per-element loop) as an alternative to slice and
  `append_array`. It was 3x slower (1.95 ms against 0.64 ms at 2,000). The author's slice-and-append version is the
  faster of the two in GDScript, so I have no finding against it.
- The 2×10⁴ segments are never sorted. Only rod instances are, at most 2,000 of them. Flames are `blend_add`, which
  gives the same result in any order, so they need no sort.
- I did not measure the GPU side. I timed `multimesh.buffer`, `Image.create_from_data` and
  `ImageTexture.create_from_image` together at 6 µs for 2,000 rods, but the headless renderer is a dummy, so that
  number does not count. I did not measure llvmpipe or a real GPU, a release export template, or the laptop tier's CPU.

**2. `ideal_coverage`, old against new** (my script, which reimplements the old loop verbatim:
`<scratchpad>/perf/ic.py`).
- **Identical output.** On 1280x720 frames, at 30, 72 and 120 px/m with widths 2.0 and 2.4 and 8 offsets each, the
  largest difference between old and new was 0.0. A fuzz of 300 random axes, widths 0.3 to 6 px, on 200x120 frames
  found 0 pixels that differed. The author's claim of identical output holds.
- **Speed.** For 8 axes the old version took 171 to 527 ms and the new one 7 to 42 ms, which is 10 to 40 times faster.
- **Cost per key in `findings`.** At 120 px/m and 2.4 px wide, `stability` took 205 ms and the new `area_findings`
  took 281 ms. Over six keys, `area_findings` adds about 1.7 s to a stability run on this machine.
- `tests/test_golden_stability.py`: 16 tests passed in 14.5 s wall time. The slowest test call took 0.96 s, so most of
  the wall time is import and collection on a loaded machine. The new tests take 0.07 s.

## Cadence (read from the code, not measured)

- **Steady frames.** `show_fuel` does not rebuild on a steady frame, so it never calls `_upload_rods`. Neither a
  steady frame nor a state change such as a burnout sorts. The test asserts `rebuilds == 1` across a turn.
- **Rebuilds.** Each structural rebuild (the structure or the region map changes) now runs one sort when `_forward` is
  set. That adds about 2.1 ms at the limit to a rebuild.
- **Camera turns.** `use_view_direction` re-sorts only when the normalized forward vector changes beyond
  `is_equal_approx`. `RenderStage.aim` calls it on every aim, but a pan or zoom leaves the forward vector unchanged,
  so neither one re-sorts. `IsoCamera.place` snaps between four fixed yaws (`step_yaw`), so today a turn costs one
  sort.
- **Does the in-place upload stay in place after sorting?** Yes, by construction. The sort permutes only the rod
  transforms and the per-instance texture, and each instance keeps its `first` row and its object row. The four
  segment textures and `state_tex` are indexed by segment or object row and still go through `_row_texture`'s
  `texture.update` path. The sort never touches them. The golden's update pass (`golden.gd::_show_next`) runs after
  `aim` has sorted and checks `rebuilds` is unchanged, so on the shipped test stage it exercises "sorted, then
  steady" end to end.

## Findings

### P-S1 (SHOULD-FIX): the new per-turn CPU cost is unrecorded against any budget
`client/addons/engine/render/fuel_pass.gd::_upload_rods`, `fuel_geometry.gd::back_to_front`.

The branch adds a CPU step of about 2.1 ms at the world's 2,000-rod limit (M2, loaded, editor build). It runs on every
camera turn and every rebuild. Neither `client_objects.md`'s budget table nor B5's fuel-pass row names it. B5 lists
"the fuel pass's insertion, steady frame and frame time" as owed, but not the turn.

**Failure scenario.** The step-8 budget work sets frame and insertion budgets without knowing about this step. On the
laptop tier's slower CPU, 4 to 5 ms or more during a turn shows up as an unexplained hitch, or it is absorbed into an
unrelated budget. The standard says budgets are "measured, not guessed", and this is an unmeasured addition on the
shipped draw path.

**Fix (unverified as a doc edit).** Add the measured number, marked [ran], and its conditions to B5's owed fuel-pass
row, as "a camera turn, at 2,000 rods". The design document's word budget forbids growing `client_objects.md`, so B5
is the place.

### P-N1 (NIT): a turn allocates a fresh GPU texture where an in-place update fits
`fuel_pass.gd::_upload`.

On a turn the instance count is unchanged, so the instance texture keeps its size. `_upload` still calls
`ImageTexture.create_from_image`, which builds a new texture each time, plus a new `Image`. `_row_texture` already
shows the in-place pattern (`texture.update`).

The cost is one 3x2,000 RGBA8 texture created per turn, about 24 KB. That is small, and the GPU half is unmeasured
(headless). Each turn also makes about 4,000 small slice allocations, plus the output arrays growing by append, about
120 KB in all. Both are acceptable at one turn per keypress.

**Failure scenario.** This only matters if turns become frequent (see P-N2). I propose no fix now. I name it so
review knows the turn path does not update in place, unlike the segment path.

### P-N2 (NIT): an animated turn would re-sort on every frame
`fuel_pass.gd::use_view_direction`.

The re-sort trigger is any change of the forward vector past `is_equal_approx`, which is a tolerance of about 1e-5.
Today the camera snaps between four yaws, so this is fine. Iso games commonly ease a 90° turn over several frames.
If the camera ever eases this way, every frame of the animation runs a full sort, about 2.1 ms at the limit, plus a
texture creation. The doc comment says "never per frame", but that holds only because the camera snaps. Nothing in
the pass enforces it.

**Trigger.** The first time a camera turn is animated. A test pinning one sort per yaw step would catch it. I do not
prescribe a design.

### P-N3 (NIT): `area_findings` repeats work `stability` already did
`scripts/golden_stability.py::findings`, `area_findings`.

For each key, `area_findings` recomputes `ideal_coverage` for all 8 axes, and `bin_coverage` for both the encoded
ideal and the rendered frames. `stability` computed the same ideal and rendered bins moments earlier. `bin_coverage`
builds a full-frame `mgrid` over 1280x720 on every call, and that dominates. The cost is about 280 ms per key, or
about 1.7 s per run, on a loaded M2. It is harmless at this size.

**Failure scenario.** None today. The function costs more than the check needs, which matters only if keys or
resolution grow. Sharing the binned arrays would roughly halve it (unverified).

### Not findings (checked)
- The rewrite of `ideal_coverage` is correct and faster. I measured it bit-identical, as listed above.
- Holding `_rod_transforms` and `_rod_bytes` costs about 120 KB at the limit, a third copy beside the MultiMesh's own.
  That is negligible.
- Segment uploads are untouched by the sort, so the existing budget row of 95 to 161 µs still applies.
- The golden run adds one capture per tier for the update pass, plus a second frame upload. I did not measure the
  golden job's wall time on llvmpipe, and the brief forbids running Docker.

## Not measured (stated plainly)
- GPU cost of `multimesh.buffer` and the new instance texture on a turn, on llvmpipe or real hardware.
- Release export template speed. The GDScript VM is the same, but release builds skip some debug checks, so my
  numbers are probably pessimistic.
- The laptop tier's CPU.
- The extra golden-job time from the update pass.
- A whole-frame time during a turn.

## Fold status
Every finding above is **open**. I set none as fixed, since nothing was folded during this round.
