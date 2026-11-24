# Executor lens: phase1/fuel-leftovers (uncommitted, against 2586ed7)

Reviewer: Executor. Read the diff's hunks, the untracked fixtures and `owner_rulings.md`, and traced each from its
entry point: `RenderStage.aim` / `FuelPass.show_fuel` for the client, and `golden_run.measured_findings` →
`golden_fuel.fuel_findings` / `golden_stability.findings` for the checks.

## What I ran

- `.venv/bin/pytest -q -p no:cacheprovider tests/test_golden_fuel.py tests/test_golden_stability.py tests/test_fuel_fixtures.py --cov=scripts --cov-branch`:
  63 passed. `scripts/golden_fuel.py`, `scripts/golden_stability.py` and `scripts/fuel_fixtures.py` are at 100% line
  and branch coverage under these modules alone, so the changed Python lines are covered. `test_fuel_fixtures`'s
  `stale` loop iterates `FIXTURES`, so the committed `fuel_ramp_next.*` is held to the generator.
- `.venv/bin/python scripts/godot_check.py`: `godot_check: PASS`. The client unit tests pass on this tree.
- **`ideal_coverage` rewrite:** I compared the old 256-pass loop with the new edge-band version on 150 random
  axes (diagonal, axis-aligned, half-pixel-aligned; widths 0.3–8 px and whole widths). The largest absolute
  difference was **0**, so the claim that it is identical holds. The `EDGE_PX` reasoning is right too: the farthest
  sample sits 7.5/16·√2 ≈ 0.663 px from the pixel centre, which is under 0.707 px.
- **Area-bar margins:** `0.5·(srgb ratio − 1)` on the ideal line comes to 0.11 / 0.09–0.10 at 2 px, 0.05–0.07 at
  3 px and 0.02–0.03 at 8 px, while the linear ideal reads 0.996–1.003. The bar does separate linear coverage from
  sRGB-encoded coverage at the widths the stability scene draws.
- **Shader clamp (ruling 6):** I worked it through `glow_curve`. With the clamp deleted and t_c = +∞: k = ∞, level = ∞,
  span = clamp(∞) = 1, and the hue is GLOW_WHITE, whose components are all positive. The colour is therefore +∞ with
  no NaN (no 0·∞ term). At 6,000 °C the level is about 7·156 ≈ 1.1×10³, already far past 1. An 8-bit target
  saturates both to the same white. For −∞ the `t_c > START` branch skips the glow, so the clamp's lower side cannot
  show either. **The record in `owner_rulings.md` ruling 6, and the shader comment, are accurate as stated.**
- **Slab derivation in `fuel_fixtures.py::leaning`:** checked against `fuel_slab.gdshader`'s
  `growth = max(1, 2·floor_half / (t·max(sine, 0.25)))`. Face-on gives 27.8 / 0.25 = 111 mm; symmetric growth would
  bring the face (111 − 20)/2 = 45.6 mm forward, past the splinter's 2 + 13.9 = 15.9 mm. A flat plank at 40°
  elevation has sine 0.766 and grows 36.3 mm, a rise of 8.1 mm. The numbers are consistent. Also checked:
  `n × along`, with `along · n = 0`, makes the slab's face normal exactly `TOWARD_CAMERA`.
- **Deletion-proof table vs code:** the rig/max/laptop outcomes for the rod sort are consistent with the tiers. rig
  and max differ only in crack substeps, AO taps and particle count, so their fuel paths are identical. The fringe
  bar is `FRINGE_SHARE · core_gain`, so 7.3 means a core gain of 73 L*. I could not rerun the Linux golden (Docker
  is not allowed here), so the measured numbers themselves are the author's.

## Findings

### E-S1 SHOULD-FIX: `client/addons/engine/render/fuel_geometry.gd::back_to_front` sorts by centre, which misorders off-centre crossings, and the fixture can't see it

The docstring says centre depth "orders crossing rods by height under the iso camera". That holds only when the two
centres coincide horizontally, and the committed fixture is built that way: stick_cross's centre is (3.2, 1.85) and
log_cross's is (3.2, 1.85). In general the horizontal offset between the centres dominates.

Failure scenario, computed with the golden camera (yaw 45°, elevation 40°, view direction (−0.542, 0.542, −0.643)
world). Take the same stick, 0.5 m long and lying across the same log, shifted 0.1 m along y. Its centre is at
y = 1.95 and it still crosses the log, 5 mm above it. Its centre now sits 0.019 m *farther* along the view than the
log's. Shifted 0.2 m it sits 0.073 m farther. So the stick sorts first, the log's colour pass blends over the stick's
outer fade, and D1's overwrite returns. This happens at any crossing more than about 0.07 m from both centres, which
is the ordinary case in a pile.

The new check (`_fringe_findings`) and the unit test `test_rods_draw_back_to_front_for_the_camera` both use only the
coincident-centre pair, so neither can fail on this. `checklists.md` and `research/fuel_antialiasing.md` record
"D1's outer half" as built, with no mention of the limitation.

Fix: either state the limitation (centre sort, correct only where centres stack) wherever D1's outer half is claimed
and add a gap row, or change the key. That choice is design, not review. Unverified.

### E-S2 SHOULD-FIX: `client/tests/unit/render/test_fuel_pass.gd::test_a_turn_before_the_first_frame_builds_nothing` asserts "sorted from the start" with an instance count

The last check is `instance_count == 77` labelled "sorted from the start", but it does not test any order. Deleting
the sort from the rebuild path, so that `_place` calls `_upload(rods, …)` unsorted when `_forward` is already set,
leaves this test green.

The golden doesn't cover that path either. `golden.gd::_draw` calls `show_fuel` (the rebuild) *before* `aim`, so the
rebuild runs with `_forward` still zero, and the later shots in the same tier reuse the same snapshot as steady
frames. As far as I can trace, a rebuild with a view direction already set never runs under any check.

Failure scenario: on the shipped path, any structural change after the camera has turned (an object added or burnt
away) rebuilds the rods in row order, and they stay unsorted until the next turn. No check would see it.

Fix: assert `_rod_position(fuel, log_row) < _rod_position(fuel, stick)` after `show_fuel`, using a forward that
sorts the log first (for example the golden camera's, as in the sibling test) rather than `Vector3(0, −1, −1)`.
Unverified.

### E-S3 SHOULD-FIX: `client/addons/engine/render/fuel_pass.gd::_upload_rods` has no check that the transforms and the instance texture stay paired after a sort

`_rod_position` reads only the instance texture's object-row field. `test_back_to_front_…` checks
`permute_floats` in isolation. If `_upload_rods` passed `_rod_transforms` unpermuted alongside the permuted bytes
(or the reverse), every rod would draw at one object's transform with another object's segment rows, and every
Mac-side test would still pass. `test_rods_draw_back_to_front_for_the_camera` would pass for the
transforms-unpermuted variant. The other `test_fuel_pass` tests read `multimesh.buffer` only on unsorted passes.

The docstring's own invariant is "instance i still reads its own rows". Only the Linux golden could catch a break,
and only indirectly.

Fix: in the sorted test, check that for each instance i the transform's origin equals the geometry row's centre for
the object row encoded in instance i's texel. Unverified.

### E-S4 SHOULD-FIX: `scripts/golden_fuel.py::_fringe_findings` / `FRINGE_SHARE`: the deletion proof clears its bar by 0.8 L*, and on laptop the check cannot fail

The record is accurate: with the sort deleted, rig and max read 6.5 L* against a bar of 7.3, and laptop reads 13.6
against 4.2. That record has two consequences.

1. On laptop, the check's guard against the deletion it was written for cannot fail. That is a check that cannot
   fail on that tier, and it is listed only as checklist "Remaining" work. CLAUDE.md counts a check that cannot fail
   as a BLOCKER. I rate it SHOULD-FIX only because it is disclosed and rig/max still hold the mechanism. The owner
   should rule on it explicitly.
2. On rig/max, an unsorted frame passes if its fade band gains 0.8 L* or more. A Mesa/llvmpipe update, a change to
   the fade's width, or a change to the core gain (the bar is relative to it) could move that, and then the check
   guards the sort on no tier at all, with no signal: a passing check looks the same as before. The sorted reading
   is 32.6 L*, so 25 L* of the gap lies on the side of the bar where nothing can go wrong. The comment's own estimate
   ("the band averages a quarter of the stick's coverage") points to a share well above 0.1.

Re-deriving the bar is the author's job; this finding is the fragility, with its failure scenario.

### E-N1 NIT: "coverage measured linear on every tier" (`client_objects.md` §7.2, `checklists.md` step 8) — the area check runs on rig and laptop only

`stability_check.gd::TIERS` is `["rig", "laptop"]`, and `KEYS` matches it. max shares rig's fuel path (the same
scale, bloom and glow_linear), so the claim holds by inference, not by measurement. The text should say which.

### E-N2 NIT: `client/tests/golden.gd::_show_next`'s refusal branches have never been seen to fire

The three error returns (`fuel_usable`, refused, rebuild count changed) run only in the golden, and only on success.
The rebuild guard is the only thing that makes the update shot a test of the *in-place* upload. If a later change
made the next fixture differ in structure, the guard would have to fire, and nothing shows that it can. A one-off
proof would close this: change `objects_next` to alter a structural column, run `golden_run`, see the rebuild
message, and note it in the commit.

## Checked and fine

- `back_to_front`: farthest first (ascending −forward·c), ties keep row order through the float index (exact below
  2²⁴), and the keys are finite because `fuel_snapshot.gd` refuses non-finite geometry. The unit test would fail on a
  reversed sort.
- `use_view_direction` refuses zero and NaN and re-sorts only on a change. A refusal in `RenderStage.aim` is a
  `push_error`, and `golden_run` fails on `ERROR:` lines (`godot_check.error_findings`), so it is not swallowed.
- `_upload_rods` before the first frame, and with zero rods, handles both edge cases and the test covers them.
- `crossing_findings` loops over both pairs, and each pair's "no pixels" branch, the buried-splinter branch and the
  erased-fade branch are each driven by a test that goes red. `update_findings`'s stale-frame test goes red, and the
  next fixture's swapped hot/cold sets are disjoint.
- `area_findings`: the flicker test now expects two findings, which is correct (half the area), and the sRGB test goes
  red. `srgb` matches the standard transfer.
- The count updates (77/79 objects, 77 rods, 2 slabs, `first[size − 10]`, 27 shots) match the fixture and `SHOTS`.

## Summary

| Id | Severity | One line |
|---|---|---|
| E-S1 | SHOULD-FIX | Centre-depth sort misorders crossings off the centres (0.1 m is enough); the fixture's stacked centres hide it |
| E-S2 | SHOULD-FIX | "sorted from the start" asserts a count; a rebuild after a turn is unguarded by any check |
| E-S3 | SHOULD-FIX | No check that the transforms and the instance texture stay paired after the permute |
| E-S4 | SHOULD-FIX | The fringe deletion proof clears its bar by 0.8 L* on rig/max and cannot fail on laptop |
| E-N1 | NIT | "linear on every tier": the area check measures rig and laptop; max only by inference |
| E-N2 | NIT | `_show_next`'s rebuild guard has never been seen to fire |

The record of ruling 6 is accurate. The claim that the `ideal_coverage` rewrite is identical is verified (0
difference over 150 cases).
