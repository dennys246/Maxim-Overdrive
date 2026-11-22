# Trust boundary lens: phase1/fuel-leftovers (git diff 2586ed7 plus the untracked files)

Reader: Trust boundary. Scope: every new input-taking function (`fuel_pass.gd::use_view_direction`, `_upload_rods`,
`_upload`; `fuel_geometry.gd::back_to_front`, `permute_floats`, `permute_bytes`), what snapshot data reaches them,
validate-then-mutate, hostile snapshots (huge counts, non-finite values, a refused frame between good ones) against
the sort and the in-place upload, and the record of the temperature clamp (owner ruling 6) against TB-S4.

Probes run: Godot 4.7.2 headless scripts in my scratchpad (`tb_probe/probe.gd`, `probe2.gd`, HOME and XDG moved
into the scratchpad), testing Vector3 overflow, `normalized()`, and `PackedVector2Array.sort()` with NaN keys. I did
not run the gate, pytest or `godot_check.py`.

## Findings

### TB-S1 SHOULD-FIX: ruling 6's record overstates why the clamp can't be checked, and leaves out TB-S4's checkable option

**Location:** `docs/design/reviews/client_objects/owner_rulings.md` (ruling 6), `docs/plans/checklists.md` step 8,
and `client/addons/engine/render/fuel_object.gdshaderinc` (the comment above `FUEL_MIN_C`).

**Defect.** The record says Compatibility's 8-bit target saturates +inf and 6,000 °C to the same white, "so no frame
can see the clamp", and that only "a renderer with an HDR target makes it checkable". It names one measurement
(+inf, llvmpipe, bloom on) but generalises well beyond it, in four ways:

1. **The tonemapper.** The golden stage sets `Environment.TONE_MAPPER_LINEAR` (`render_stage.gd:39`). With linear
   tonemapping, inf passes straight to the unorm write and clamps to 1.0. Reinhard, Filmic and ACES are rational
   functions of the colour, so an infinite input gives inf/inf, which is NaN. That happens before the 8-bit write,
   so it doesn't saturate, and a NaN pixel is written as whatever the driver chooses (usually black). So on this
   same renderer the clamp is visible as soon as any non-linear tonemapper is used. That case could be checked
   today, without an HDR renderer. (Inferred from the tonemap formulas; not rendered.)
2. **NaN was never tried.** An f16 NaN gets through `frame_problems` too, because it checks only the column's
   length. `clamp(NaN, lo, hi)` is implementation-defined in GLSL. On a driver whose `max(NaN, lo)` returns NaN and
   whose `min(NaN, hi)` returns `hi`, a NaN segment draws at 6,000 °C. Without the clamp it draws cold, because every
   comparison with NaN is false. So the clamp can change what a NaN segment looks like, and nothing has measured it.
   TB delta1 already says "not rendered".
3. **One driver.** "No frame can see it" was measured on llvmpipe only. The shipped renderer is `gl_compatibility`
   on every platform (`project.godot:70-72`), on real GPU drivers.
4. **The record leaves out TB-S4's second fix.** TB-S4 offered two fixes: clamp in `fuel_colour`, or "refuse
   non-finite values in the per-frame check" (2×10⁴ halves). The second runs in GDScript, so a unit test in
   `test_fuel_snapshot.gd` can guard it like every other rejection path, with no rendering. Ruling 6 frames the
   choice as "keep the clamp unchecked" or "wait for an HDR renderer". The record doesn't show that the checkable
   option was put to the owner. Today `segments.surface_temperature_c` is the only per-frame column whose values
   aren't validated client-side. The other per-frame columns are u8, and `state` is range-checked. This charter's
   lens asks for every rejection path to be tested, aiming at 100% branch coverage.

**Failure scenario.** A later shader edit drops the clamp, or a new tonemapper lands (say, Filmic for the art pass).
A server bug sends f16 inf or NaN for one segment. That object then draws black or white-hot, and no gate goes red.
A reader of ruling 6 has been told this can't happen until an HDR renderer arrives, so nobody writes the check.

**Also: there is no trigger.** "A renderer with an HDR target makes it checkable" is not listed under step 8's
"Remaining", and has no backlog row. So the deferral has no point at which it gets picked up again.

**Fix (unverified; review doesn't design).** Correct the record and the shader comment so the claim covers only
what was measured: +inf, linear tonemap, llvmpipe. Put TB-S4's per-frame refusal option back in front of the owner,
or record that it was considered. Give the deferral a named trigger.

### TB-N1 NIT: `use_view_direction` accepts a finite vector it then treats as "no direction"

**Location:** `client/addons/engine/render/fuel_pass.gd::use_view_direction`.

**Defect (verified by probe, Godot 4.7.2).** Take `Vector3(1e30, -1e30, 1e30)`:
- `is_finite()` is true, and `length()` is `inf` (the f32 square overflows), so `inf > 0.0` passes the guard.
- `normalized()` then returns `(0, 0, 0)`.
- The function returns `""` (accepted) and sets `_forward = Vector3.ZERO`, which `_upload_rods` treats as "row
  order".

So it accepts a direction its docstring says it refuses, and silently un-sorts the rods.

**Failure scenario.** Low in practice: today the only caller is `RenderStage.aim`, which passes
`-camera.transform.basis.z`, a unit vector. A future caller that passes an unnormalised look vector built from
world coordinates (a free camera, a replayed camera path) could hit it. The rods would then draw unsorted, with no
error.

**Fix (verified predicate, not the edited function).** Refuse when `not forward.normalized().is_normalized()`. In
the probe, this refuses the overflow case and accepts `(0, -0.7, -0.7)`, `(1e19, 1e19, 0)` and `(1e-20, 0, 0)`. Add
the overflow vector to the test's `bad` list.

### TB-N2 NIT: the update pass's missing-`_next` path isn't tested

**Location:** `client/tests/golden.gd::_show_next`, `client/tests/unit/render/test_golden_shot.gd`.

**Defect.** A `shaded_update` shot whose fuel fixture has no `_next` file fails loudly through `fuel_usable`, which
I checked by reading the code. But no test covers that branch, or the "the next frame rebuilt the fuel pass"
branch. This is test-harness input rather than a shipped trust boundary, which is why it's a NIT.

**Failure scenario.** A refactor makes `_show_next` skip the rebuild comparison. A `_next` fixture that changes the
structure would then capture a rebuild, and the in-place upload check would pass without ever exercising the
in-place path. The author's deletion proof (upload skipped: −45.8 / −71.5 L*) covers the upload itself, not this
guard.

## Checked, no finding

- **Validate-then-mutate in `use_view_direction`.** The refusal returns before `_forward` or any upload changes. The
  zero and NaN paths are tested (`test_rods_draw_back_to_front_for_the_camera`). +inf goes through the same
  `is_finite` branch as NaN.
- **A refused frame between good frames.** `show_fuel` still runs `frame_problems`, and on a rebuild `problems`,
  before any mutation. `_rod_transforms` and `_rod_bytes` change only inside `_rebuild` → `_place`. So a turn after
  a refused frame re-sorts the last good rods, and draws nothing from the refused frame.
- **A turn before the first frame.** `_upload_rods` returns while `_rod_bytes` is empty. Tested
  (`test_a_turn_before_the_first_frame_builds_nothing`), and the first rebuild sorts with the stored direction.
- **Huge counts.** Row counts are capped at `MAX_OBJECTS = 2000` and `MAX_SEGMENTS = 20000` (`_shape_problems`)
  before any rebuild. `back_to_front` stores the row index as a float32 `Vector2.y`, which is exact only below
  2^24, so the cap keeps the permutation exact by a wide margin. If the cap is ever raised past 16,777,216, the
  index round trip breaks (indices merge, `slice` past the end returns an empty array, and the buffer comes up
  short). Worth knowing; it isn't reachable today.
- **Non-finite sort keys from finite input.** Origins and lengths are validated as finite, but the extent check is
  deferred (TB2-S2). A rod at origin 3e38 with length 3e38 overflows its centre to inf (probe:
  `Vector3(3e38,0,0)+Vector3(2e38,0,0) = inf`), and a dot product with the view direction can give inf or NaN. The
  probe sorted 40 keys, a third of them NaN: no error, no crash, and the result was still a permutation (all 40
  indices kept). So hostile geometry draws misordered rods, not corrupt instances. That is covered by the existing
  TB2-S2 deferral.
- **The permutation keeps instances matched to their data.** The instance texture is permuted with the transforms,
  and each instance carries its own object row and first segment row (`_place`). So `state_tex`, the segment
  textures (row-indexed) and the FUEL_ID view stay correct. Flames are indexed by segment row (`fuel_flame.gdshader`,
  `INSTANCE_ID`) and are not permuted. That is correct.
- **The in-place upload (`_row_texture`) on a steady frame.** This branch doesn't change it. Per-frame column
  lengths are checked against the row counts on every frame, so a steady frame can't shrink or grow a texture.
  The height and format check before `texture.update` holds.
- **An OOM in `_place`.** It now sets `instance_count` before the resize failure returns, and no longer sets the
  buffer. That leaves zeroed transforms and a stale instance texture. The pre-branch code left a stale texture too.
  This only happens if allocating 2000 × 12 bytes fails, so it isn't a finding.
- **Python tooling** (`area_ratio`, `area_findings`, `update_findings`, `ideal_coverage`). Empty or degenerate
  inputs give NaN, and `abs(NaN - 1) <= margin` is false, so they fail closed with a finding. `srgb` is fed only
  coverage values in [0, 1].

## Summary table

| Id | Severity | Status | Location |
|---|---|---|---|
| TB-S1 | SHOULD-FIX | open | `owner_rulings.md` ruling 6, `checklists.md` step 8, `fuel_object.gdshaderinc` comment |
| TB-N1 | NIT | open | `fuel_pass.gd::use_view_direction` |
| TB-N2 | NIT | open | `client/tests/golden.gd::_show_next`, `test_golden_shot.gd` |
