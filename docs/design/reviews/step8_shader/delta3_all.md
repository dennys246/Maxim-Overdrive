# Step 8 shader, delta 3: all lenses

Lenses: Executor, Wire integrity, Architecture, Client and rendering. Diff: `git diff d934e6d 9215696`, plus 1358725
(goldens). Statuses are set from the tree at 1358725.

**Ran:** the headless client runner on a mktemp copy (`PASS 37 tests`); pytest on test_golden_measures and
test_golden_run (30 passed); `golden_measures` on the author's llvmpipe cut-away run (`scratchpad/ci9/cutaway`) and
on delta 1's defective laptop frame. I also built a Python port of `cut_regions` with an occlusion model
(`scratchpad/d3/occl.py`): a capsule ray-cast towards the 40° camera against the §1.1 boxes, with the stump at
0.4–0.7 m (0.1 m fixture). It gives 96.5% where the render measures 96.4%. **Not run:** the gate, Docker, windowed
Godot.

**Headline:** no BLOCKER. The sightline rule is right in plan: its reach, its slab test and its sampling. Over a
0.1 m sweep of the whole alley at all four yaws (12,000 placements, modelled), no wall the rule leaves standing hides
anything that matters: the lowest ratio is set by stumps, not by uncut walls. There are two gaps. In an unsampled
corner the stumps alone take the ratio below 95%. And the hysteresis has no caller.

## Fold status (set from the tree)

### delta2_executor_wire_architecture.md

| Finding | Status | Evidence |
|---|---|---|
| S1 (the short-side strip hides half the body) | **fixed** | Replaced by the sightline rule. The strip samples are gated, and the unit test now asserts the cut at (0.9, 0.3) and (0.9, 3.7). Modelled: 100% at both strip samples at every yaw, and wall_south is cut at step 0. |
| S2 (speckle's flatness guard unproven) | **fixed** | The one-pixel line test. Derived: with `flat & odd` changed to `odd`, the line's pixels (ring median = background, centre 183 below it) are flagged, so the new assertion fails. |
| N1 (laptop has no traversal guard) | **fixed** | Laptop is scanned on a 2×2 box-down. Measured: 6 dots on delta 1's defective laptop frame (`d1/new_laptop.png`), and 0 on ci9's cold and fire frames and on the committed golden. Only the even parity is scanned; the odd parity finds 0 even on the defective frame. That is right for a 2× upscale, but it is not stated. |
| N2 (speckle sees one isolated pixel only; not in §6 or B7) | **open** | Neither B7 nor §6 mentions speckle (grep). |
| N3 (speckle numbers disagree) | **fixed** | The docstring and fold.md both say 52 per cold frame and 47 in the fire golden, each named. |
| N4 (`use_pixel_metres` passes +inf) | **fixed** | `is_finite` is checked, and the test covers 0, −1, INF and NAN. |
| N5 (octave below 12 px; survives a cell_m change; test comment) | **fixed in part** | The reset on a new `cell_m` and the 11.2 px band are in the docstring. Still open (NIT): §5.4 still says "≥ 12 px polygons", and the test comment still says "exactly 2 octaves". |
| N6 (fold.md overstatements) | **fixed** | The goldens are committed (d934e6d, 1358725). Laptop's 0 is now evidence (see N1). |
| N7 (`cutaway_check` header) | **fixed** | Every pair is gated, so "requires ≥ 95% at every sample" is now true. |
| delta-1 EW S1 (in-place update untested) | **open** | Unchanged. fold.md names it as not folded, with no trigger. |
| delta-1 EW N2 (palette `push_error` untested) | **fixed** | Problems are returned; both branches and every refusal are tested. `RenderStage` is the only caller, and it reports each problem. |
| delta-1 A N2 (no red gate for colour-only severity) | **deferred (author's status, owner decision 7)** | Decision 7 schedules a branch. Still no strict red gate or advisory print. |
| delta-1 A N6 (deletion proof dropped) | **fixed** | §2 says "Proved by deletion". 9215696's message gives 56 of 68 failing with no cut (author-measured; consistent with `proof-cut3.log`'s 0% pairs). |
| delta-1 A N7 (`[engineering]` tag) | **fixed** | The tag is in §5.3. |
| delta-1 A5 (depth proof) | **fixed** | Recorded in 37b24be's message. |
| delta-1 N5, N8, P carve, P reads | **open** | Named in fold.md as not folded. |

### delta2_client_performance.md

| Finding | Status | Evidence |
|---|---|---|
| N9 (`walk_at` floors at t = 0) | **fixed, NIT residue open** | `ceil − 1` is used on negatively stepping axes, so the comment's "can never place the walk on the wrong side" now holds. Still uncorrected: the asked-for `skip_brick` comment ("at most 3 * BRICK cells", which is 3·BRICK − 2). There is no test; the shader has none headless, and the golden camera had 0 such cases. |
| N10 (unset spacing carves a recess; `pixel_m` default) | **fixed, untested** | `carves()` gates carving on spacing > 0, and `pixel_m` defaults to 0. `hatch` and the groove width both tolerate 0 (derived). The asked-for test, that a fresh volume's cracked cell draws its face, does not exist. |
| N11 (speckle misses laptop, fire and cut frames) | **fixed in part** | Laptop is fixed (see EWA N1). The 136 cut frames and the fire frames are still unscanned, so the widest set of ray directions (four yaws) still has no speckle check. |
| N12 (§10 "Six") | **fixed, but see new N4** | §10 now says "None"; one decision is still pending. |
| N4 (severity by shape) | **deferred (author's status, owner decision 7)** | Trigger: the scheduled branch. |
| N5, N6, N8 | **open** | Named in fold.md. |

## New findings

### SHOULD-FIX

**S1. `client/tests/cutaway_check.gd::SAMPLES`: in an alley corner the stumps alone hide more than 5%, and no sample stands there.**
- **Mechanism:** each cut wall keeps a 0.3 m stump (0.4–0.7 m). A body touching one wall loses 50 of 1,384 px to it: 96.4% measured, 96.5% modelled.
- **The corner:** a body in a corner touches two cut walls. At (11.35, 0.65), step 0, wall_south and wall_end are both cut, and the model gives **93.8%** (likewise at (11.35, 3.35), step 1). That would fail the 95% gate.
- **Why nothing sees it:** the `end` sample is at y = 2.0, and no sample stands in a corner. The sweep's lowest placements are exactly these two corners.
- **Failure scenario:** the gate passes while a §2 claim ("the stump hides at most the feet's edge"; ≥ 95% everywhere) is false at a spot a player reaches by walking to the dead end.
- **Fix:** add two corner samples. If they fail as modelled, the owner decides between a lower stump in corners, a stump height tied to the body's distance from the face, or a §2 exception. Do not loosen the threshold.

**S2. `client/addons/engine/render/cutaway.gd::cut_regions(held = PackedInt32Array())`: the anti-flicker hold has no caller, and its default makes forgetting it silent.**
- **What claims it:** §2 ("a cut wall holds 0.25 m longer"), the class docstring and the commit claim the hold as behaviour.
- **What calls it:** the only callers, `RenderStage.cut_for`, `golden.gd` and `cutaway_check.gd`, pass no `held`. Only `test_cutaway.gd` threads it.
- **Statelessness is honest for the checks:** a hold only adds cuts, and a cut wall's stump lies inside the wall, so visibility can only rise. The stateless gate is therefore a lower bound.
- **It is not honest for the claim:** CLAUDE.md's "A fix ships with a caller" means this is capability, not shipped behaviour. "Push invariants into types" means a default `held` turns a forgotten argument into silent flicker rather than an error.
- **Fix:** make `held` required, with the checks passing `PackedInt32Array()` explicitly and saying why. Mark §2's hold "built, wired with `main.tscn`" with B30's trigger.

**S3. `scripts/golden_measures.py::_pair_finding`, with the new reference: nothing checks the reference frame itself.**
- **Before:** the reference ("volume hidden") never depended on the cut machinery.
- **Now:** it is `RenderStage.cut_all`, a cut through the same uniforms, so a defect in the cut path can move both frames.
- **Failure scenario:** a shader change makes `region_is_cut` honour only `cut_ids[0]`, or a game caller passes more than `MAX_CUT` flagged regions (`use_cut` truncates silently).
  - The reference then keeps a wall that the "with" frame cut, and ratios go above 1.
  - A ratio above 1 is never a finding.
  - Only a pair where a wall hides the whole body still fails, through the zero-pixel path.
  - Measured today: every pair has with ≤ without. The maximum is 1.000, and the crate pairs are 1200/1200.
- **Fix:** flag a ratio above 1 + 1/without, and fail `cut_all` when there are more than `MAX_CUT` flagged regions. A cheap anchor would also help: one "volume hidden" frame per yaw at a crate-free sample, required to equal its reference.

### NIT

**N1. `cutaway.gd` docstring:** "Three sightlines spread across the body's width" is wrong. It is `ceili(0.6 / 0.15) + 1` = 5 lines, and 9 when held.

**N2. `cutaway.gd::_shadows`: walls cut that hide nothing.**
- **Measured on the model:** 160 of 12,000 placements have a cut wall whose restoration hides no body pixel.
- **Where:** all of them are on the 0.05 m margin band. Examples: wall_end along the step-0 diagonal from (8.25, 3.35) to (9.85, 1.75), and wall_south's far end from (9.45–9.85, 3.35–2.95).
- **Cost:** only scenery; the end wall pops there as the body crosses the band. Recording it is enough.

**N3. `cutaway.gd`: the hold is lateral only.**
- `HOLD_M` widens the sightline band but not `reach`, so a body moving along its sightline across the reach limit has no hysteresis.
- In the alley the reach never binds before a lateral edge (derived for every wall and yaw), so the flaw is latent until content has a wall farther than 4.8 m from a walkable spot.

**N4. `docs/design/client_rendering.md` §10, "None: step 8's seven were decided":** fold.md's decision 5, the ember gain, is "pending the owner's look at a sweep". So one question is open, and §10 overstates.

**N5. `RenderStage.cut_all`, the `-INF` stump:**
- It works on llvmpipe and Metal: `x > -inf + 1e-4` is true.
- But GLSL ES 3.00 doesn't require infinities, and the Compatibility renderer targets it.
- A finite value below every cell, such as −1.0 m, says the same without relying on IEEE behaviour in a uniform.

**N6. Cut-away runtime.**
- ci9 (this rule, 68 pairs, emulated amd64) took 80.6 s of `cutaway_check`'s 120 s timeout, and `golden.tscn` 59.4 s.
- ci7 and ci8 measured 32.0 and 38.6 s, so 8 more pairs don't explain the jump; the machine was probably loaded.
- Delta 2's "under 60 s" no longer holds as measured. Remeasure idle, or split the call before CI's slower runner meets the timeout.


## Checked, nothing found

- **Reach:** (top − feet)/tan 40° is the distance at which a sightline from the feet clears the box. The head (1.8 m) clears at 3.1 m, so between 3.1 and 4.77 m a wall hides only the lower body, and cutting it is right.
  - Starting at the axis, not the near edge, costs at most a sliver of the near foot (derived).
- **Slab test and sampling:** `sightline_meets` is correct for a start inside, a box behind, parallel rays and reach ≤ 0, with seven unit cases. Lines ≤ 0.15 m apart can't miss a 0.4 m wall.
- **Uncut occlusion:** over the sweep, no placement falls below 95% from a wall left standing. The minimum, 93.8%, is the stumps (S1). Mid-alley the result doesn't change with x at any yaw.
- **Flicker:** a ±2 cm jitter flips the bare rule at 156 of the sampled placements. With `held` threaded through, it changes at most once (sampled; derived, since 2 cm can't cross the 0.25 m band).
- **API returns:** `RenderStage`, the only non-test caller of `use_palette` and `use_pixel_metres`, pushes every problem.
- **`walk_at`:** `mix(floor, ceil − 1, down)` is sound; the entry axis is still overwritten by `crossed`.
- **Docs:** `client_rendering.md` is 3,769 words (≤ 3,800).
