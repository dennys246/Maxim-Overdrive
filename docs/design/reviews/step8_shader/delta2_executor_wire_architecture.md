# Step 8 shader, delta 2: Executor, Wire integrity, Architecture

Scope: `git diff --cached ce06d7b` plus the three unstaged goldens.

**Ran:** pytest on test_golden_measures, test_golden_run, test_client_project and test_golden_compare (70 passed); the headless client runner on a mktemp copy (`PASS 34 tests`); two GDScript mutations and one Python mutation; `golden_measures.speckle` on the shipped goldens, ce06d7b's, and delta 1's defective goldens (kept in the delta-1 scratch directory). **Not run:** golden_run, cutaway_check, Docker. Cold frames aren't committed, so cold-frame speckle counts are the author's.

## Fold status (set from the tree)

### delta1_executor_wire.md

| Finding | Status | Evidence |
|---|---|---|
| B1 (walk holes locked into the goldens) | **fixed** | `skip_brick` now takes exact `advance` steps with no texture reads, and `walk_at` runs only at entry. Isolated black pixels on bright 8-neighbourhoods: rig 4 (ce06d7b) → 10 (delta 1) → 0 now; max 2 → 11 → 1. The one left in max, at (328, 634), sits on a three-way silhouette next to near-black night (3), not on a flat face, and is byte-identical in delta 1. `speckle` finds 51 in delta 1's rig and max fire goldens and 0 in the new ones. The debug miss pass round one asked for was not built; `speckle` stands in for it (see N1–N3). |
| S1 (in-place update untested) | **open (narrowed)** | The new test proves reuse and reallocation, not the update itself. Replacing `reuse.update(images)` with `pass` still leaves all 34 tests green (verified), which is exactly EW S1's scenario. Contents are covered only by the golden job: `SHOTS` draws fire, then cold, per tier through one stage, so a stale texture would make cold equal fire and fail colour-alone. That job is CI-only and not required (B7). The reason is real (the dummy renderer keeps no data), but there is no trigger. |
| S2 (goldens unstaged) | **open** | They are still unstaged and HEAD is ce06d7b. fold.md says "committed in their own commit": false at this state (N6). |
| N1 (summary line; the matching test judged nothing) | **fixed** | `--no-xvfb` prints "goldens not judged", and two tests pin it. The matching-frames test now runs with `XVFB=()` and asserts "3 goldens". |
| N2 (palette `push_error` paths untested) | **open** | The author rejected it: a test would print `ERROR:` and fail the scan. That is true of `push_error` itself, not of the decision. If `use_palette` returned its problems and the caller reported them, both branches could be tested (one function decides, the caller reports). The same applies to `use_pixel_metres`'s new refusal. |
| N3 (shader constants untied) | **fixed** | The test now checks `clamp(material, 0, 15)`, `i < 8; i++` and `const int BRICK = 4;` against the GDScript constants. Each string occurs exactly once in its file (grep). |
| N4 (bounds cache keyed by identity) | **deferred** | B30 (1) names it, with the trigger "`main.tscn`'s scene tree". |
| N5 (`rmtree` then `mkdir`) | **open (NIT)** | Named in fold.md as left open. |
| N6 (timing headroom) | **fixed** | Every call prints its wall time, and a test asserts the line. 32.3/32.0 s is the author's measurement. |

### delta1_architecture.md

| Finding | Status | Evidence |
|---|---|---|
| N1 (pavement strip pops) | **open** | The exception is now stated and pinned rather than fixed. Its stated rationale is false, and in the strip the body is hidden (new S1). |
| N2 (12 px floor; isolated cells and severity colour-only) | **deferred (incomplete)** | Named with a reason: owner decision 7, B7, and §5.4 states the spacing rule. CLAUDE.md asks known-broken behaviour for a strict red gate; none exists, not even an advisory print in `golden_run`. The trigger is the owner's decision. |
| N3 (§10 and §8 contradict the record) | **§8 fixed; §10 open** | §10 says "Six", but fold.md lists seven owner decisions (item 7 came in delta 1). |
| N4 (seam checks presence only) | **open (NIT)** | Named, not folded. |
| N5 (bounds cache) | **deferred** | B30 (1). |
| N6 (§2 counts; deletion proof dropped) | **count fixed; proof open** | §2 says four pairs. "Proved by deletion" is still gone. fold.md doesn't say the cut-off deletion run was repeated with the short-side rule and the pavement samples. |
| N7 (T₀; the `[engineering]` tag) | **T₀ fixed; tag open (NIT)** | T₀ is defined as the offset. (The code converts it to kelvin, which the formula's T_K/1773 needs; the text leaves that implicit.) The tag on the stylisation is still missing. |
| A2 residue (§10 "None open") | **open** | Same as N3: the count is wrong. |
| A5 (depth proof) | **open** | No fold commit exists, so nothing in the tree records the run. |
| NIT 10 | **fixed** | As EW N3. |
| NIT 11 (alley numbers in the engine docstring) | **rejected (reason holds)** | They are the rule's evidence. |
| NIT 12 / W N4 (third copy of the alley) | **deferred** | Trigger: `content/scenes/alley.yaml` exists. It is recorded only in fold.md, not in a backlog row. |
| B5 checklist line | **rejected (author's call, flagged to the owner)** | B5 carries the trigger. The checklist is the owner's plan. |
| B30 grab-bag | **fixed** | Four items, each with its own trigger. Hatching moved to B7. |

## New findings

### SHOULD-FIX

**S1. `client/addons/engine/render/cutaway.gd::across_short_side` and `test_cutaway.gd::test_a_side_walls_cut_never_depends_on_where_along_it_the_player_stands`: the wall-end exception is a §2 visibility failure, and the test pins it as correct.**
- **The defect:** the docstring and §2 justify the strip as "walking round a wall's end, where what occludes really does change". It doesn't change: the same wall occludes on both sides of the flip.
- **Worked by hand at step 0** (forward (−0.707, 0.707), camera to the south-east, 40° elevation; not rendered):
  - The body is at (0.9, 0.3) with radius 0.25.
  - A body column (x, y) is behind wall_south when y − (1.2 − x) ∈ [0, 0.4]. The ray rises only about 0.06–0.36 m before it reaches the 4 m wall.
  - That holds for the north-east half of the disc, x + y ≥ 1.2, through the full body height.
  - So about half the body's silhouette is hidden while the wall stays uncut: roughly 50% visible against §2's ≥ 95%.
  - At (0.9, 0.41) the wall is cut and the body is visible.
- **Failure scenario:** a player spawning on the pavement steps to y = 0.3 beside wall_south's end and half vanishes into it. `cutaway_check` has no sample in the strip (pavement-south is at y = 0.65), so nothing sees it, and the unit test asserts `not in_strip.has(SOUTH)`.
- **Fix:** when the player lies within the short side's span, so the short-side offset is zero, decide on the long axis instead: `q = p.clamp(box)`, the nearest point. At step 0 that gives (0.3, 0)·f = −0.21, so the wall is cut. The flips that remain cut a wall that no longer occludes, which is harmless. Add a `cutaway_check` sample at (0.9, 0.3) and pin the test to the cut. (A's plane-of-face rule doesn't cure it: y = 0.3 isn't on the alley side.)

**S2. `scripts/golden_measures.py::speckle`: the flatness guard, the part that prevents false positives, is unproven by its tests.**
- **Mutation:** with `flat & odd` changed to `odd`, all speckle tests pass (verified on a copy).
- **Why they can't see it:** the stripe and edge cases are symmetric, so the median already equals the centre.
- **What the mutation does on real frames:** it flags about 6,800 pixels on each shipped rig and max golden. So the mutation fails loudly in CI, never silently.
- **The gap:** the property the round asked about (no false positives on lines, hatching and AO edges) is what the guard holds, and no test pins it.
- **Fix:** add a one-pixel line, flagged without `flat` and not with it.

### NIT

**N1. `golden_measures.py::SPECKLE_TIERS`: laptop has no traversal guard at all.**
- The comment says a laptop defect is a 2 × 2 block. But `speckle` on delta 1's defective laptop golden finds 0 even on the phase-aligned half-resolution frame.
- At laptop, the one tier that draws differently, a walk defect is caught only by the ΔE golden, which passed the dotted goldens before.
- Say so in B7, or measure laptop properly.

**N2. `speckle` sees only one isolated pixel on a flat face:**
- two adjacent bad pixels, a 2 × 2 block, or a hole touching an edge or silhouette each give 0 (verified on synthetic frames);
- it never looks at the fire frames.

It is a narrow proxy for round one's miss pass. Neither §6 nor B7 lists it among the measured checks; only the module docstring does. Record it in B7's list.

**N3. Speckle numbers disagree:** the docstring says 47 per rig frame, fold.md 52 (cold), and I measure 51 (delta 1's fire goldens). Use one number and name its frame.

**N4. `cell_volume.gd::use_pixel_metres` refuses 0, negatives and NaN, but passes +inf.**
- `IsoCamera.pixel_metres` with a viewport height of 0 returns inf: the case CP N3 named.
- `crack_octave` then takes `ceili(inf)` and `pow(2, …)`, both undefined or inf, and `_octave` holds garbage until the next finite call recomputes.
- Small impact (a zero-height view draws nothing). Use `is_finite(metres) and metres > 0.0`.
- The refusal has no test, for the same `push_error` reason as EW N2.

**N5. `CellVolume.crack_octave`:**
- **Below 12 px inside the band:** hysteresis holds an octave until exact < n + 0.1, so polygons can shrink to 12 / 2^0.1 ≈ 11.2 px. That contradicts "at least 12 px" in `CRACK_MIN_POLYGON_PX`, crack.gdshaderinc and §5.4.
- **The octave outlives a cell size change:** `_octave` survives a `show_snapshot` with a different `cell_m`, where the octave index means a different spacing. Reset it when `cell_m` changes.
- **The first pick has no hysteresis:** a bare `ceil` at the 12 m view's exact = 1.0. Deterministic in double today (the ratio is exactly 2.0), but worth noting.
- **Test comment:** "exactly 2 octaves" means the 1–2 boundary.

**N6. fold.md "Delta 1" overstates in three places:**
- EW S2 says the goldens were "committed in their own commit". They are unstaged.
- "0 in every frame at every tier after": `speckle` does not run on laptop and reports 0 on the defective laptop frame too, so laptop's 0 is not evidence.
- "§10 points to the owner decisions": §10 says six, and the list has seven.

**N7. `client/tests/cutaway_check.gd` header:** it still says the check "requires >= 95% at every sample". Four pairs are advisory.

## Checked and found sound

- **Wiring:** `measured_findings` runs `speckle_findings` after colour-alone at every tier, and a test asserts it. The 12 `SHOTS` names match what both readers open. CI's `run.sh` passes no `--no-xvfb`.
- **Speckle can fail:** 51 findings on delta 1's goldens, 0 on the shipped ones, 2 on ce06d7b's rig (C S1's (224, 543) among them).
- **False positives:** silhouettes, lines, gradients and hatching put disagreeing pixels in the ring or keep the centre near the median. The shipped rig and max fire goldens (hatched stumps, AO, capsule edges, cracks) give 0. Thin features are at least 14 px at the golden view. The Mac `--no-xvfb` path is unmeasured.
- **Hysteresis:** with the band deleted, the octave test goes red ("holds 2 on the boundary: got 1"). `crack_spacing_m` is in the uniform-name test, and its value is asserted. The goldens' 10 m view sits 0.26 octaves from a boundary, so shot order doesn't matter.
- **The walk:** every outer iteration advances at least one exact cell, so `nx + ny + nz + 4` bounds it.
- **Shader-constant checks:** each asserted string occurs once, and both variants are covered.
- **Docs:** `client_rendering.md` is 3,798 words (≤ 3,800). §8 matches B5, §5.4 states the spacing rule, B7 carries the crack gaps and hatching, and B30 has a trigger per item.
