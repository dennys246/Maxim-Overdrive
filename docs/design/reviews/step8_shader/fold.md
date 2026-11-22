# Step 8 shader fold: author's record

**The author's record, not a fold-status table** (O25: reviewers set statuses from the tree). Backlog rows B30 and B31 in the review reports are now B40 and B41: main took B30-B39 first. Round one ran at
ce06d7b: `executor.md`, `architecture.md`, `wire_integrity.md`, `client_rendering.md`, `performance.md`. No
BLOCKERs were raised. Ids: E Executor, A Architecture, W Wire integrity, C Client and rendering, P Performance.

## Shader

| Finding | Change | Proof |
|---|---|---|
| C S1 (black pixel at (543, 224)) | **Superseded in delta 1: this fix added 47 dots per frame.** An instrumented llvmpipe build showed the ray cycling between two bricks on two boundaries until out of steps; the jump was patched. | — |
| E S1 (`groove_t0` never reset) | Reset whenever the walk leaves the material (an empty brick or an undrawn cell). | Goldens re-recorded; the dark fringe term is gone by construction. |
| C (grooves see through solid cells) | Grooves end at `GROOVE_MAX_DEPTH_M` (0.05 m); a ray that reaches it hits the fissure floor, shaded as a face darkened by depth. | — |
| C (1.5 px floor not met on slanted faces) | The pixel floor is divided by the face's cosine with the ray (floored at 0.25). | — |
| C (laptop crack becomes speckle) | Voronoi spacing is one cell, or a power-of-two multiple of it so a polygon spans at least 12 px; it changes only at whole octaves of zoom. Never colour alone now runs at every tier. | Carving deleted (darkening kept): crack fails at laptop, rig and max (|ΔL*| 4.7–4.9, edge ratio < 1). |
| C (`MAX_STEPS` sized for the alley), P NIT | The loop bound is `nx + ny + nz + 4` from the `cells` uniform. | — |
| C (hatching aliases on laptop) | The period is at least 8 px. Hatching is still unmeasured: B40. | — |
| C NIT (entry axis from distances) | Taken from the box face's normal through a varying. | — |
| C NIT (`texture()` in divergent flow) | `textureLod(…, 0.0)`. | — |
| P NIT (8-tap AO reads 5 zero-weight taps) | Only the near-side neighbours are read: 2 edge taps, plus 1 corner at 8. The image is the same by construction. | — |
| W S2, C (uniform names can't be checked; defaults equal the fixture's) | A test holds every name `CellVolume` sets to `Shader.get_shader_uniform_list()` for both variants, and the palette and cut-list sizes to the GDScript constants. `cells`, `cell_m` and the glow calibration default to sentinels that draw nothing. | `cell_m` renamed in `cell_volume.gd`: the test goes red for both variants. |

## Client code

| Finding | Change | Proof |
|---|---|---|
| A 4, W S1, E N7 (nearest-point cut pops on the pavement) | The rule clamps only across a region's short side, so a side wall's decision depends only on the player's distance across it. §2 amended in place (word count kept). Three pavement samples join the rendered check; the unit test sweeps x from 0.3 m. | The nearest-point rule restored: the unit test goes red at exactly the pavement positions. |
| A 7, W S5, C (unknown materials draw black) | `use_palette` takes the vocabulary, reports a solid material without a colour or an id over 15, and draws it magenta. | Tested: an uncoloured id reads magenta. |
| A NIT 8, W S4 (vocabulary off the seam) | `material_ids` is on `CellSnapshot`, and `problems()` refuses a snapshot without it. | Tested. |
| A 3 (pixel footprint depends on call order) | `RenderStage` recomputes `pixel_m` from both `aim` and `use_tier`. The composition still lives in test support: B40. | — |
| E S4 (golden scene refusals untested) | Shot parsing and drawability checks moved to `tests/support/golden_shot.gd`, each refusal tested headless; a fixture without a crate region is refused. The cut-away scene's own refusals stay untested (it takes one argument). | `test_golden_shot.gd`. |
| E N5 | Duplicate actor ids refused. | Tested. |
| E N6, A NIT 10 | `BRICK_SHIFT` is the one constant. The shader's `8` and `16` are held by the uniform test. | — |
| P (new GPU textures every snapshot) | `ImageTexture3D.update` in place when format and shape match. | — |
| P (bricks 14–46 ms, region bounds 98–166 ms) | Not fixed in GDScript: a 2× tweak is still 4× over budget. Deferred to B5 with the numbers; the fix is the server shipping the brick mask and region bounds in protocol v0, before step 7 wires `show_snapshot` to the stream. | — |

## Checks and tooling

| Finding | Change | Proof |
|---|---|---|
| A 1, E S2, W S3 (advisory too wide; pair count unchecked) | Advisory is exactly four (sample, yaw) pairs; a missing, extra or half pair is a finding; the Python sample list is held to the scene's by a test; `out/cutaway` is cleared each run. | Tests: a crate sample below 95% at a non-advisory yaw fails; missing and stray pairs fail. |
| W S6 (Mac exit status meaningless; §6.5 claimed prepush runs the checks) | `--no-xvfb` skips the golden comparison with a printed line; §6.5 corrected in place. | Tested. |
| P NIT (runtime unrecorded) | Each Godot call prints its wall time. Measured under emulation: 50.7 s and 64.7 s of 120 s. | — |
| W N1, N2 | The gate fixture passes a `--shot`; the uid test globs `.gdshaderinc`. | — |
| A 5, E S3, W S8, C (depth proof promised, not given) | It was run after ce06d7b's commit message was written: the golden image with `DEPTH = ndc.z` fails all three goldens (591–902 px blobs above ΔE 10), and passes restored. Recorded in the fold commit. | As stated. |

## Rejected, with reason

- **W S7 (no prepush step compiles a shader).** Measured: a syntax error appended to `lighting.gdshaderinc` fails
  `scripts/godot_check.py` with `SHADER ERROR … Shader compilation failed`, because the client tests load
  `CellVolume`, which preloads both variants.

## Docs

§2 (rule, test), §5.3 (emission formula; the 920 °C claim, which was false), §5.5 (8-tap) and §6.5 edited in place:
`client_rendering.md` is 3,796 words, under its 3,800. FIELDS.md gains the grid origin, the missing `region`
channel and `glow`'s different quantity. B5, B7 and a new B40 (the composition in test support, the black-night
constraint, unbuilt flame particles, unmeasured hatching, no ANGLE compile, the untested perspective path). CLAUDE.md's
Layout names the new files.

## Owner decisions (decided 2026-11-21: "go with your recommendations"; outcomes set by the author)

1. **The cut-away rule:** the owner accepted the short-side rule, which delta 2 then showed wrong off a wall's end
   (wall_south uncut while hiding half the body at (0.9, 0.3)). Built instead: the occlusion test itself, sightlines
   in plan from across the body's width towards the camera, cut when one meets the box before climbing over it,
   with a 0.25 m hold against flicker. §2 amended. This is the recommendation's own fallback ("line of sight
   later"), brought forward because its premise failed.
2. **The crate and the 95%:** the test's reference frame now removes only the flagged walls, so the never-cut crate
   counts on both sides; the advisory pairs are gone and every pair is gated. A see-through body silhouette is a
   later feature, not scheduled.
3. **AO at 8 taps:** accepted; §5.5 says so.
4. **Crack polygons at least 12 px:** accepted (in a 0.1-octave hold, down to about 11.2 px); §5.4 says "~12 px, held".
5. **Ember gain:** the owner chose 7 from a sweep of 4, 7 and 10. The author described it as keeping the hottest
   faces' gradation; delta 4 showed it clips about 1,230-1,400 °C to white (top fifth, against a tenth at 4). A soft
   knee and two tonemappers were measured and rejected (the knee killed the bloom); the owner kept plain gain 7, the
   bloom halo carrying heat beyond white, the laptop tier's flat band recorded in B7.
6. **Black night:** accepted; B40. Whether the clear-colour behaviour is an engine bug is to be settled before step 8
   closes, and nothing filed without the owner's go (B41).
7. **Crack severity by shape:** scheduled as its own branch after this one: severity drives polygon density, every
   cracked cell is guaranteed an edge, and a mild-against-severe edge-density check holds it. B7 names it.
8. **Stump height (delta 3):** 0.2 m, not §2's 0.3 m: two stumps in a dead-end corner hid 6.5% of the body
   (93.5% measured, failing the gate); at 0.2 m the corner measures 98.7% and a wall 99.3%.

## Delta 1 (at the staged fold over ce06d7b)

Reports: `delta1_executor_wire.md`, `delta1_architecture.md`, `delta1_client_performance.md`. One BLOCKER, raised by
two readers independently.

| Finding | Change | Proof |
|---|---|---|
| EW B1, CP N1 (the walk fix shaded floor tops as side faces along brick edges: 47 dots per rig and max frame, recorded in the goldens) | The third patch to re-entering the cell grid from a float position after a brick jump. It is removed, not patched: in an empty brick the walk now takes its exact cell steps with no texture reads until it leaves the brick. Nothing after the entry face is derived from a position. | Speckle in the llvmpipe frames: 52 per cold rig and max frame before, 0 in every frame at every tier after. The two Godot calls got faster: 50.7/64.7 s to 32.3/32.0 s (emulated). |
| (the guard both readers asked for) | `golden_measures.speckle_findings`: on the cold rig and max frames, no pixel may stand apart from eight agreeing neighbours. | It counts 52 in the defective run's cold frames and 0 now. Unit-tested on a dot, stripes and an edge. The golden ΔE judge alone passed the dotted goldens. |
| CP N2 (the nudge read a neighbouring cell) | Gone with the nudge. | — |
| EW S1, CP N7 (in-place texture update untested) | A test: a second same-shape snapshot reuses the texture objects; a new shape allocates new ones. It cannot see contents, because the dummy renderer keeps none; the golden job's alternating fire and cold shots through one volume covers contents. | — |
| EW S2 (goldens unstaged) | Re-recorded from the clean run and committed in their own commit. | — |
| CP N3 (the octave sits on a boundary at the default zoom) | The octave is chosen in GDScript (`CellVolume.crack_octave`) with 0.1-octave hysteresis and passed as `crack_spacing_m`; a non-positive pixel size is refused. | Hysteresis deleted: the boundary test goes red (CPU picks octave 1 there, where float32 picked 2). |
| A N1 (pavement strip) | Not "no pops anywhere": off a wall's end, level with its thickness, the cut flips, because that is walking round the end. Stated in `cutaway.gd` and §2, and pinned by a test. | — |
| A N3 | §10 points to the owner decisions here; §8 says the upload has no meter and is broken (B5). | — |
| A N2, CP N4 (severity and isolated cells) | Recorded, not fixed: owner decision 7, B7, and §5.4's pattern line, which now states the spacing rule. | — |
| A N6, N7 | §2 counts four (sample, yaw) pairs; §5.3 defines T₀. | — |
| EW N1 | The summary says "goldens not judged" under `--no-xvfb`; the matching-frames test judges goldens. | — |
| EW N3, A NIT 10 | The shader's palette clamp, cut loop bound and brick size are now held to the GDScript constants by the uniform test. | — |
| A (B40 a grab-bag) | Split: each item has its own trigger; unmeasured hatching moved to B7. | — |

**Not folded, with reasons:**
- A NIT 11 (alley numbers in `cutaway.gd`'s docstring): they are the evidence for the rule, kept deliberately.
- A NIT 12, W N4 (a third copy of the alley's boxes): it remains until `content/scenes/alley.yaml` exists, then the
  generator reads it.
- EW N2 (the palette's two `push_error` paths untested): a test that triggers one prints `ERROR:`, which fails the gate's scan.
- A N4 (the seam checks presence, not ids or duplicates), A N5 / EW N4 (bounds cache by identity: in B40 (1)),
  EW N5 (`rmtree` then `mkdir`), CP N5 (the fissure floor's axis), CP N6 (depth-bound gaps at silhouettes), CP N8
  (hatch phase moves with zoom), P NITs (carve hoisting, redundant reads): NITs, left open, named here.
- Step 7's checklist line for shipping the brick mask: B5 carries the trigger. The checklist is the owner's plan.

## Delta 2 (at 37b24be and d934e6d)

Reports: `delta2_executor_wire_architecture.md`, `delta2_client_performance.md`. No BLOCKER. The client lens
emulated the new walk against an exact reference: no skipped cell, no wrong axis, no loop, at the golden camera and
over 200 random grids.

| Finding | Change | Proof |
|---|---|---|
| EWA S1 (the short-side rule hides half the body off a wall's end) | Replaced by the sightline rule (decision 1), with hysteresis; two pavement-strip samples join the rendered check. | All 68 pairs pass on the Mac, the lowest 96.4% (the stump); with the rule cutting nothing, 56 fail. Unit: the strip, the pavement, a walk out of a wall's shadow changing once. |
| (decision 2) | The reference frame removes every flagged wall, keeping the crate; `cutaway_findings` gates all pairs. | As above: the crate samples pass. |
| EWA S2 (speckle's flat guard untested) | A one-pixel line test. | — |
| CP N11, EWA NIT (speckle skips laptop) | Laptop judged on its frame averaged 2 × 2. | It finds 6 in delta 1's defective laptop frame, 0 now. |
| EWA N2 (palette errors untested) | `use_palette` and `use_pixel_metres` return their problems; `RenderStage` reports them. Both palette branches and the pixel refusals (0, negative, inf, NaN) are tested. | — |
| EWA NITs (octave survives a cell_m change; "≥ 12 px") | The hold resets on a new spacing; the docstring states the 11.2 px band. | — |
| CP N9 (entry cell on a negatively stepping axis) | `ceil − 1` there. | — |
| CP N10 (unset spacing carves a recess; `pixel_m` default plausible) | No carving until the spacing is set; `pixel_m` defaults to 0. | — |
| CP N12, EWA (§10 "Six"; §5.3 tag; §2's deletion sentence) | §10 records the decisions; the tag and the sentence are back. `client_rendering.md` is 3,769 words. | — |
| EWA (fold.md overstatements) | The goldens commit now exists (d934e6d); speckle counts are given per source: 52 per cold rig/max frame in the defective run, 47 in its fire golden (a stricter flatness test). | — |

Not folded: EW S1's remainder (texture contents are unreadable headless; the golden job covers them); the round-one
performance NITs; CP N5, N6, N8.

## Delta 3 (at 9215696 and 1358725)

Report: `delta3_all.md`. No BLOCKER; the sightline rule modelled over 12,000 placements leaves no wall standing that
hides more than 5%.

| Finding | Change | Proof |
|---|---|---|
| S1 (stumps alone fail in a corner) | Two corner samples added; measured 93.5% at both. The owner chose a 0.2 m stump (decision 8). | Corners 98.7%, walls 99.3% (Mac). |
| S2 (the hold has no caller; a default hides that) | `held` is required; the stateless check stage passes an empty array and says why (a hold only adds cuts, so the stateless frame is a lower bound). Wiring the hold into play is B40 (1). | A call without it fails to compile. |
| S3 (nothing checks the reference frame) | A ratio above 1 + 1/without is a finding; `cut_all` reports more flagged walls than the shader can cut. | Tested on a reference that kept a wall. |
| N1, N5 | The docstring counts 5 (9) sightlines; the reference stump is −1.0 m, not −inf. | — |
| N4 (§10 overstated while the gain was pending) | The gain is decided; §10 now holds. | — |
| EWA N5 residue, N2 | The octave test's comment; B7 names the speckle check. | — |

Not folded: N2 (walls cut on a 0.05 m margin band that hide nothing: scenery only), N3 (the hold widens sideways,
not in reach: latent in the alley), N6 (runtime: ci9's 80.6 s came from a loaded machine; remeasured in the final
run below), CP N10's fresh-volume test, delta-1 EW S1.

## Delta 4 (at 9e3731b and 8c28afc)

Report: `delta4_all.md`. No BLOCKER. `prepush: PASS 8c28afc5a93f`.

| Finding | Change |
|---|---|
| SHOULD-FIX (gain 7's comment: "without flattening the hottest faces") | False, and corrected first in the hand-off. Measured alternatives (decision 5); plain gain 7 kept by the owner; the comment, §5.3 and B7 now say what it does. |
| N1 (§2 stump sentence) | The derivation and the measurement are separate clauses, each tagged. |
| N2, S2 residue (the hold stated as shipped) | §2 says built, wired with `main.tscn`; B40 (1) names it. |
| N4 (corner samples undocumented) | The scene's header says why they exist. |
| N6, D2 N5 residue (§5.4 "≥ 12 px") | §5.4 says "~12 px, held". |
| (owner) the Godot clear colour | B41, with its steps and trigger. |

Not folded, named: N3 (`cut_all`'s overflow report can't run with three walls), N5 (`golden_compare` reads the first
renderer line of the joined log; every call uses the same renderer), P1 (runtime under load: the split calls ran
25-76 s at a load of 80-150; no idle baseline), and the earlier not-folded set. This fold changes a comment and docs
only: no code path, no pixel.
