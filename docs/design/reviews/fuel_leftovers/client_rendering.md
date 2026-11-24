# Client and rendering lens: phase1/fuel-leftovers (git diff 2586ed7 + untracked)

Read: `fuel_pass.gd`, `fuel_geometry.gd`, `fuel_rod*.gdshader(inc)`, `fuel_slab.gdshader`, `fuel_object.gdshaderinc`,
`glow_curve.gdshaderinc`, `iso_camera.gd`, `render_stage.gd`, `golden.gd`, `golden_shot.gd`, `fuel_footprints.gd`, the
unit-test diffs, `scripts/fuel_fixtures.py`, `scripts/golden_fuel.py`, `scripts/golden_stability.py`, `golden_run.py`,
and the doc diffs plus `owner_rulings.md`. Ran: one Python snippet for the sort-flip distance (below). Did not run
Godot, pytest or Docker.

## Findings

### CR-1 SHOULD-FIX: sorting by centre gets off-centre crossings wrong, and the fixture crosses at both centres

`fuel_geometry.gd::back_to_front` sorts each rod by `forward · centre`. Under the 40° iso camera, a stick lying
0.055 m above a log's axis (the fixture's geometry) sorts in front only while its centre sits within
`0.055 · sin40 / (cos40/√2) = 0.065 m` of the log's centre along the camera's horizontal view. Measured with a snippet
at yaw 45: offset 0 to 0.065 m along the stick's axis, the stick sorts nearer; 0.07 m and beyond, it sorts **farther**
and draws first, so the log's colour pass overwrites its outer fade outside the stick's silhouette. That is exactly
the D1 defect the branch says it fixed.

The failure scenario: a 0.5 m stick lying across a 0.5 m log a quarter of the way along either one (offset 0.125 m). It
fails at two of the four yaws (the sign of the offset along the view flips with the 180° step), so the defect shows or
hides as the player turns the camera. In a real pile most crossings sit off centre.

`fuel_fixtures.py::visible` puts `stick_cross` (centre (3.2, 1.85)) and `log_cross` (centre (3.2, 1.85)) at the same
plan point, the one geometry a centre sort always gets right. So `crossing_findings`/`_fringe_findings` cannot see
this limit. The docs overstate it: the docstring's "orders crossing rods by height under the iso camera",
`research/fuel_antialiasing.md`'s "Sorted since phase1/fuel-leftovers: rods draw back to front", and checklist step 8's
"D1's outer half". The correct statement is: the outer half is fixed only for crossings within about 6.5 cm of both
centres along the view (a per-object key can't order overlapping long objects in general).

What fixing it takes is the author's call, and needs an owner decision on whether the centre sort is acceptable with
the limit recorded. Possible directions, unverified: a fixture crossing moved off centre, which the current code
should fail at one of the yaws; and a different key or per-pair ordering.

### CR-2 SHOULD-FIX: the fringe band is twice the fade's reach, and the bar's "a quarter" is wrong. That leaves the rig/max deletion 0.8 L* from passing

`golden_fuel.py::_fringe_findings` widens the stick's strip by `SPECKLE_TIERS[tier]` output pixels, one **rendered**
pixel. But `fuel_rod.gdshaderinc::rod_coverage` is `clamp((drawn − d)/fade + 0.5)` with `fade` = one rendered pixel,
which is 0.5 at the drawn edge and reaches 0 at **half** a rendered pixel past it. So the outer half of the band has no
designed coverage, and the band's mean coverage is about 1/8, not the "quarter" the `FRINGE_SHARE` comment derives the
bar from. That dilution halves the sorted signal while leaving any sort-independent residual untouched.

The deleted (unsorted) case should put pure log colour in the band, yet it reads 6.5 L* on rig/max. My hypothesis,
unverified: the residual is the hot stick's bloom halo (bloom is on for rig/max and off for laptop), which adds to the
band and not to `bare` (log pixels far from the stick).

The failure scenario: any bloom retune (`GLOW_GAIN`, the WorldEnvironment glow intensity), or a fixture move that puts
`bare` nearer the stick, shifts the residual by about 1 L*, and the unsorted deletion passes on rig/max too. The guard
would then hold D1 on no tier.

Fix, unverified: make the band match the fade's reach (drawn to drawn + 0.5 rendered px), and correct the derivation
comment. Since the bar was "written before measuring", re-deriving it is the owner's ruling (CLAUDE.md, B30).

### CR-3 SHOULD-FIX: a host that never calls `use_view_direction` gets row order silently

`fuel_pass.gd::_upload_rods` falls back to row order when `_forward == Vector3.ZERO`, with no report. Today the only
caller is `client/tests/support/render_stage.gd::aim`. No shipped scene instantiates `FuelPass` yet, so the first game
host (or `stability_check.gd`, if it ever draws crossings without going through `aim`) can forget the call. It would
then draw the D1 defect while every unit test stays green.

This is the "push invariants into types" and "a handler that quietly returns a fallback" pattern. The contract lives
only in a doc comment. Fix, unverified: refuse to draw (or `push_error` on the first rebuild) until a direction is set,
or take the camera as a required collaborator.

### CR-4 NIT: the leaning-plank derivation understates the rod's drawn depth, and the laptop margin is 1.9 mm, not about 30

`fuel_fixtures.py::leaning`'s docstring says symmetric growth covers "the splinter's drawn top at 2 + 13.9 = 15.9 mm".
The vertex shader scales `VERTEX.xz` by `(drawn + render_pixel_m)/radius` in **every** local xz direction, so the
cylinder is widened toward the camera as well. The depth-pass front surface on the axis therefore sits at
2 + 13.9 + 13.9 = 29.8 mm on rig/max, and at 2 + 13.9 + 27.8 = 43.7 mm on laptop (render_pixel_m = 1/(72·0.5) m). That
is against the symmetric face's 45.6 mm. A 12-sided facet trims it by about 3%.

The deletion still buries the splinter on every tier, which matches the author's measurement. But the laptop margin
is 1.9 mm (0.14 output px), and a later change to the rod's fade width or to `MIN_EDGE_SINE` could make the laptop
check blind with no one noticing. Worth stating the real numbers. The rest of the derivation checks out: the 0.25 floor
face-on, growth 5.56 to 111 mm, the flat plank's 0.766 sine and 8 mm rise, `TOWARD_CAMERA` against
`IsoCamera.place` at yaw 45, and `across = n × along` being unit and making `along × across = n`.

### CR-5 NIT: ruling 6's mechanism ("8-bit target") contradicts the codebase's own glow comment

`fuel_object.gdshaderinc` (the `FUEL_MAX_C` comment), `owner_rulings.md` ruling 6 and checklist step 8 say
Compatibility's "8-bit target saturates" +∞ and 6,000 °C to one white. But `glow_curve.gdshaderinc` says the bloom halo
"keeps growing with the HDR value", and `emission.gdshaderinc` and `render_tier.gd` say bloom spreads emission above
1.0. Both can't be literally true.

What the measurement supports is narrower: the target's range caps below 6,000 °C's emission (about 1,100 by the
curve: 7·((6273/1773)^4 − k0^4)), so the two are indistinguishable. The ruling's outcome (keep the clamp, unchecked)
and the measurement ("could not fail, removed") are recorded accurately. Only the stated mechanism is suspect: I did
not verify Compatibility's 3D buffer format in 4.7.2. Fix: state the measured fact ("saturates below 6,000 °C's
emission") rather than a format. The record is otherwise accurate: the clamp has no other consumer, NaN isn't
reachable through `clamp`'s path anyway (the wire's f16 can carry ±∞ and the snapshot validator doesn't check
temperatures for finiteness), and Compatibility is the only renderer in `project.godot`, so "a renderer with an HDR
target" names a future change, not the shipped path.

### CR-6 NIT: nothing holds the transform and instance-texture permutations to the same order

`test_rods_draw_back_to_front_for_the_camera` checks the instance-texture row order. `test_back_to_front_orders_*`
checks `permute_floats` on a synthetic buffer. No unit test checks that, after `_upload_rods`, instance i's transform
origin belongs to the object whose row sits in texture row i. A regression that permuted one and not the other would
draw every rod's segment state on another rod's geometry. Probably the goldens would catch it, but only on Linux CI.
Fix, unverified: in the sort test, compare `rods.multimesh.get_instance_transform(i).origin` with the stick's and the
log's expected centres.

### CR-7 NIT: an animated camera turn would re-sort every frame

`use_view_direction` re-sorts on any change beyond `is_equal_approx`. Today the camera steps 90° at a time. If the
turn is ever interpolated, every frame of it costs a GDScript sort plus `append_array(slice)` over up to 2,000 rods,
and a new MultiMesh buffer and instance texture (unmeasured). The "never per frame" doc comment would then be false.
Record this as a B5 row when the camera animation lands. No action needed now.

## Checked and clean

- **Sort direction and ties.** Key `−forward·origin` ascending is farthest first. Origins are read at buffer
  offsets 3/7/11, which is correct for TRANSFORM_3D row-major with `FLOATS = 12`. Ties keep row order (Vector2 sorts
  by x then y; the float32 index is exact below 2^24). The camera is orthographic, so a pan never needs a re-sort, and
  the direction-only trigger is right.
- **Re-sort triggers.** A rebuild while the camera stays put sorts with the stored `_forward`. A steady frame touches
  only the row textures, which the permuted instance texel's `first`/`row` fields still address, so the sort survives
  updates. A turn before the first frame builds nothing (tested). An empty rod set uploads nothing.
- **MultiMesh buffer.** `_upload` reads `instance_count`, which `_place` set first. The buffer is assigned only for
  n > 0, and the instance image is sized `maxi(n,1)` to match `bytes`.
- **Render priorities.** The rod depth pass at 0, the colour at 1 and the flames at 2 are unchanged. Instance order
  matters only within the colour pass, since the depth pass draws invisible. Slabs are opaque, so the splinter
  needs no sort.
- **`fuel_slab.gdshader`.** Face-anchored growth is consistent with the fixture derivation. The culling box grows by
  `SLAB_MAX_GROWTH_PX`.
- **The update golden.** `_show_next` captures, then shows the next frame, and refuses it if it rebuilt. The next
  fixture keeps the structure, so `_row_texture` takes the `texture.update` path. `shaded_update` is flame-free and
  requires a fuel fixture, and it is added to `golden_run.SHOTS` for every tier.
- **`ideal_coverage`.** `EDGE_PX` (half the diagonal) is the correct bound for a square pixel against both the side
  and the cap lines. The sample axes are broadcast correctly. `area_ratio`'s "linear ⇒ 1" holds for a ramp symmetric
  about the drawn edge, including after a bilinear upscale.
- **Typed GDScript.** Every new variable, loop variable and return is typed.
- **Not by colour alone.** The update and crossing checks read glow brightness (L*), not hue.
