# Step 8 shader, delta 4: all lenses

Lenses: Executor, Wire integrity, Architecture, Client and rendering, Performance. Diff: `git diff 1358725 9e3731b`
(8c28afc re-records goldens). Statuses are set from the tree at 8c28afc.

**Ran:** the headless client runner on a mktemp copy (`PASS 37 tests`, 0 error lines). pytest on test_golden_measures
and test_golden_run (31 passed). `golden_measures.cutaway_findings` on the author's llvmpipe run at 9e3731b
(`scratchpad/ci12/cutaway`, 152 frames): no findings. The corners measure 98.7% (k0 south, k1 north), 99.3% or 100%
elsewhere, and the maximum ratio is 1.000. **Not run:** the gate, Docker, windowed Godot.

**Headline:** no BLOCKER. The stump, the required `held` and the split calls do what the commit says. Two problems remain. The reason the code gives for the gain-7 decision is false by derivation and by
measurement (S1). And S2's doc half was not folded.

## Fold status (set from the tree)

### delta3_all.md, new findings

| Finding | Status | Evidence |
|---|---|---|
| S1 (corner stumps) | **fixed** | The `corner-south` and `corner-north` samples are in both lists, and `test_golden_measures` holds the lists together. llvmpipe (ci12) gives 98.7% at the worst corner pair, which agrees with the author's Mac. The 0.3 m deletion proof is the author's; not rerun. |
| S2 (hold has no caller; default hides it) | **fixed in part** | `held` is required, and all four call sites pass it. RenderStage's comment gives the lower-bound argument. Still open: §2 still states "a cut wall holds 0.25 m longer" as shipped behaviour, and B30 (1) says "cut wiring" but never names the hold (grep). The fold row's "Wiring the hold into play is B30 (1)" is therefore an inference, not text. |
| S3 (reference frame unchecked) | **fixed** | The `ratio > 1 + 1/without` branch comes before the minimum check, and a test covers it (133.3%). Derived: with the branch deleted, 133% passes the 95% floor, so the test goes red. The `cut_all` overflow `push_error` becomes an `error_findings` line, which makes the run fail; it is untested (N3 below). |
| N1 (sightline count) | **fixed** | The docstring says 5, or 9 while held. |
| N2 (walls cut that hide nothing) | **rejected (author's), accepted** | Scenery only. Recording it was the whole ask, and fold.md records it. |
| N3 (hold is lateral only) | **open** | fold.md gives a reason ("latent in the alley") but no trigger. Suggested trigger: the first content with a wall more than 4.8 m from a walkable spot. |
| N4 (§10 overstated) | **fixed** | Decision 5 is now made (gain 7), so §10's "None" holds. |
| N5 (`-INF` stump) | **fixed** | The value is -1.0. Derived: the shader compares `float(c.z+1)*cell_m`, which is at least `cell_m > 0`, so any negative value cuts every cell whatever the world origin. |
| N6 (cut-away runtime) | **fixed in part** | The calls are split. ci12 shows golden calls of 54.8, 54.5 and 25.0 s and cut-away calls of 47.6 to 76.3 s against a 120 s limit; the worst call uses 64% of it. The asked-for idle remeasure was not done: every number was taken at load 80 to 150 (P1 below). |

### delta3_all.md, carried rows

| Finding | Status | Evidence |
|---|---|---|
| D2 EWA N2 (speckle not in §6 or B7) | **fixed** | B7 now names `speckle_findings`. |
| D2 EWA N5 residue | **fixed in part** | The test comment is corrected. §5.4 still says "≥ 12 px polygons" with no hold band, and grep finds no "11.2" in client_rendering.md. Owner decision 4's "§5.4 says so" is therefore false. |
| D2 CP N9 residue (`skip_brick` "at most 3 * BRICK cells") | **open** | Unchanged at traversal.gdshaderinc:148. |
| D2 CP N10 (fresh-volume test) | **open** | fold.md names it as not folded; there is no trigger. |
| D2 CP N11 (speckle misses fire and cut frames) | **open in part** | Unchanged. |
| D1 EW S1 (in-place update untested) | **open** | Unchanged, with no trigger. |
| D1 A N2 and D2 CP N4 (severity by shape) | **deferred (author's status, owner decision 7)** | The trigger is the scheduled branch. |
| D1 N5, N8, P carve, P reads; D2 CP N5, N6, N8 | **open** | Named as not folded. |
| All other rows delta 3 marked fixed | **still fixed** | This diff doesn't touch them. |

## New findings

### SHOULD-FIX

**S1. `client/addons/engine/render/emission.gdshaderinc::GLOW_GAIN`: the rationale "blooms without flattening the hottest faces to white" is false.**
- **Derived:** the linear tonemapper clips each channel at 1.0. With the fixture's calibration (525 °C + 975/255 °C per count), the blue channel alone is `0.62·s·level` in the top half of the span.
  - At gain 7, all three channels exceed 1.0 from about **1,230 °C** upwards. At 1,400 °C the levels are R 5.3, G 4.6, B 3.3.
  - At gain 4 the clip started at about 1,330 °C.
  - The envelope runs from 600 to 1,400 °C, so gain 7 widens the flat-white band from roughly the top 9% of the envelope's temperature range to the top 21%.
- **Measured:** the committed rig `fire.png` has **1,358** pixels with every channel ≥ 250, against 1,089 at 1358725 (+25%). Some of them may be bloom halo, but the face clip itself is arithmetic.
- **Failure scenario:** the owner's decision record (code comment and fold.md decision 5) says the hottest faces keep their gradation, but faces from 1,230 to 1,400 °C draw identical white. Glow is the brightness half of "never colour alone", and brightness carries no signal across that band.
- **Fix:** correct the comment to state the clip temperature, and let the owner confirm 7 knowing it. A real fix, such as a soft knee or a per-channel shoulder before the clip, is a decision, not a fold.
- **Related (NIT):** §5.3's "near 920 °C … bloom" holds only narrowly. Emission alone gives R = 1.05 at 920 °C and 0.95 at 900 °C, so the crossing sits at about 910 °C. Bloom at the envelope's foot depends on the lit colour added on top. State the crossing temperature rather than "near 920".

### NIT

**N1. `docs/design/client_rendering.md` §2, the stump sentence.**
- "rises 0.30 m by the face (derived), so even two stumps, in a corner, hide 1.3%" joins a derivation to a measurement with "so", and the 1.3% has no tag. The 0.30 m rise is the axis sightline; the 1.3% is the near foot's edge, which touches the face.
- Tag it with where it was measured: Mac, and llvmpipe at ci12 (both 98.7%).

**N2. §2's "a cut wall holds 0.25 m longer"** (S2's residue, above). Mark it as built but unwired, and name the hold in B30 (1).

**N3. `client/tests/support/render_stage.gd::cut_all`: the overflow report is untested.** No fixture has more than `MAX_CUT` walls (the alley has 3), so the branch never runs. `error_findings` would catch it, but nothing proves the branch fires. Move it with the composition when B30 (1) lands.

**N4. `client/tests/cutaway_check.gd::SAMPLES` header** still lists side walls, the end wall, the crate, pavement and strips, but not the corners or why they exist (two stumps meeting).

**N5. `scripts/golden_compare.py`: the joined `golden.log` names one build for three processes.** `next(...)` reads only the laptop call's renderer line. The binary is the same, so the risk is near zero. To close it, assert that every call names the same renderer.

**P1. The split's cost has not been measured on an idle machine.** Under load, the golden scene went from 59.4 s (one call, ci9) to 134.3 s (three calls, ci12), and the cut-away from 80.6 s to 251.6 s. Each call pays Godot start-up, shader compile and fixture load again. Record one idle run's per-call times as CI's baseline.

**N6. owner decision 4 in fold.md** says §5.4 states the 11.2 px band; it doesn't (see carried EWA N5).

## Checked, nothing found

- **STUMP_M = 0.2:** `stump_top_m(0.4)` = 0.6, unit-tested. The float32 sum 0.4 + 0.2 rounds to 0.6f, and `> stump + 1e-4` keeps the 0.4 to 0.6 m cell.
- **`held` required:** all four call sites pass it (`render_stage.gd:88`, `test_cutaway.gd:19, 75, 87, 107`).
- **`--yaw`:** a value outside "0" to "3", or none, fails with usage. `measured_findings` requires all 4 × 19 pairs, so a skipped call is caught.
- **`draw_all` split:** each tier draws its own shots, a failed call doesn't stop the later ones, and the stale-frame `rmtree` still runs first.
- **Fake Godot:** a missing `--yaw` makes the fake raise, so the test fails loudly. It asserts 3 golden calls, 4 cut-away calls and the k0 to k3 frames.
- **Ratio-above-1:** the one-pixel slack is right for 1,384 px bodies. The measured maximum is 1.000.
- **Word count:** client_rendering.md is 3,765 by `wc -w` (at most 3,800), down from 3,769.
