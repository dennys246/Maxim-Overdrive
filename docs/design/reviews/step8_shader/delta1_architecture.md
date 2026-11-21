# Step 8 shader, delta 1: Architecture

Read: CLAUDE.md, `docs/code_review.md`, `client_rendering.md` §2, §5.3–§5.5, §6.5, §8 and §10 as staged, B5, B7 and B30, all five round-one reports, fold.md, and `git diff --cached ce06d7b`. Read-only. I ran no gate, Godot or Docker. Where I worked a geometric case by hand, I say so below. None of those cases was rendered.

## Fold status (architecture.md), set from the tree

| # | Status | Basis |
|---|---|---|
| A1 advisory too wide | **fixed** | `golden_measures.py::CUTAWAY_ADVISORY` is now four (sample, k) pairs. `test_only_the_measured_crate_pairs_are_advisory` fails a crate sample at any other yaw. §2 now states that the crate pairs are reported and left to the owner, so the design and the code agree. |
| A2 departures only in a commit message | **open (narrowed)** | AO: §5.5 now says 8-tap. Crate: §2. Black night and flame particles: B30. All fixed. But §10 still reads "None open", while fold.md lists six owner decisions open. That is the exact failure scenario of A2: the owner reads §10 and merges. The crack's 12 px floor is recorded only in fold.md and a shader comment; §5.4 now states something false (N2). |
| A3 composition in test support | **deferred (valid)** | B30 names it, with the trigger "step 8, with `main.tscn`'s scene tree". The call-order bug is fixed: `RenderStage::_update_pixel_metres` runs from both `aim` and `use_tier`. See N5 on the row's breadth. |
| A4 pops on the pavement | **open (narrowed)** | The reported positions are fixed. A strip of the pavement still pops, and both §2 and `cutaway.gd` claim no pops anywhere (N1). |
| A5 depth proof | **open, not verifiable** | fold.md says the `DEPTH = ndc.z` proof ran (591–902 px blobs) and is "recorded in the fold commit". That commit does not exist yet. Re-check the message when it lands. |
| A6 B7 and prepush | **fixed** | §6.5 now says prepush doesn't run the checks, and `--no-xvfb` prints that the goldens are not judged. The optional suggestion (cite `colour_alone_findings` in the CLAUDE.md Guard) was not taken. That is acceptable. |
| A7 uncoloured material draws black | **fixed** | `CellVolume::use_palette` takes the vocabulary, reports with `push_error` and draws magenta. Caveat: the test covers only the magenta fill for an id outside the vocabulary. Neither `push_error` branch (an id above 15, or no colour) is exercised, so the "report loudly" half is unproven. |
| NIT 8 vocabulary off the seam | **fixed** | `CellSnapshot.material_ids`, and `problems()` refuses an empty vocabulary. The rest of the seam is N4. |
| NIT 9 grid origin | **fixed** | FIELDS.md now has an origin row. |
| NIT 10 constants twice | **open (narrowed)** | The test holds the declarations `palette[16]` and `cut_ids[8]`. It does not hold `cutaway.gdshaderinc`'s loop bound `i < 8` or `lighting.gdshaderinc`'s `clamp(material, 0, 15)`. Scenario: `MAX_CUT` and `cut_ids` go to 16 and the test passes, but the shader reads only 8 ids. |
| NIT 11 game facts in the engine half | **open** | `cutaway.gd`'s docstring now carries more alley numbers (5.7 m, 1.2 m). fold.md does not mention this finding. |
| NIT 12 third copy of the geometry | **open** | Not addressed, and not mentioned in fold.md. |
| NIT 13 CLAUDE.md Layout | **fixed** | It now names `support/`, `fixtures/`, `golden_measures.py` and `client_fixtures.py`. |

fold.md silently drops NITs 11 and 12. An author's record that omits findings is the overstatement pattern O25 exists to catch. List them, even as "not folded".

### Deferrals made from the other reports

- **B5, client upload (14–46 ms for bricks, 98–166 ms for region bounds, against a 3 ms target): a real deferral, poorly wired.** It has numbers, a root cause, a fix (the server ships the brick mask and region bounds) and a trigger ("with step 7, before `show_snapshot` is wired to the stream"). Nothing calls `show_snapshot` per frame today, so there is no live harm. Two gaps:
  - Step 7's checklist (`docs/plans/checklists.md`, Step 7) has no item for it, and §4's channel list has no brick-mask entry. The step 7 author works from the checklist, so the trigger moment doesn't carry the work. Add a checklist line.
  - §8's table still says "B5, gated in CI" next to a 1.4–2.4 ms prediction. That is false now, and B5 contradicts it (see N3).
- **B30: a real deferral for the composition, a grab-bag for everything else.** The `main.tscn` trigger fits the composition, the black-night constraint and flame particles. It does not fit:
  - hatching unmeasured: a missing measured check, which belongs in B7;
  - no ANGLE/D3D11 compile: its trigger is the first Windows runner or export;
  - the perspective path never drawn: its trigger is whoever first uses perspective.

  Bundled in one row with one trigger, the row will be marked done when `main.tscn` lands, with three items still open. Split it, or give each item its own trigger inside the row.

## New findings

### SHOULD-FIX N1: "no pops anywhere" is still false on a strip of the pavement
`client/addons/engine/render/cutaway.gd::across_short_side`, its docstring, and §2 "No pops"

For wall_south (x 1.2–12, y 0–0.4) the rule computes q = (p.x, clamp(p.y, 0, 0.4)). While p.y ≥ 0.4, q − p = (0, 0.4 − p.y), so the cut depends only on f.y. That is correct for the whole alley and for the pavement north of y = 0.4.

On the pavement west of the wall's end, a body can stand at y < 0.4. With a 0.25 m radius against the domain edge, the strip is x 0.25–0.95, y 0.25–0.4. There q = p, so dot = 0, and the `< 0` test never cuts.

Worked by hand at the yaw whose forward is (−0.707, 0.707), with the camera to the south-east:
- At (0.9, 0.41) the wall is cut.
- At (0.9, 0.39) it is not. A sightline from the body's east half toward the camera enters the wall at x = 1.2, y ≈ 0.25, a few centimetres up a 4 m wall, so part of the body is hidden.
- A 10.8 m wall therefore appears and vanishes on a 2 cm step, with no tween.

wall_north at y 3.6–3.75 is the mirror case. The docstring's premise, "the player's distance across it, which a body never crosses", fails exactly off a wall's end, where the player can stand beside the wall's thickness. The pavement samples (y 0.65, 2.0, 3.35) and the unit sweep (y in {0.65, 2.0, 3.35}) never enter the strip.

Fix: decide by the plane of the wall's inner face: cut when the player is on the alley side of it and the camera is on the far side. That has no degenerate interior. The cheaper alternative is to state the exception in §2 and drop "anywhere". Add a sweep at y = 0.3 either way.

### SHOULD-FIX N2: the 12 px polygon floor is a design change, not a tier detail, and it opens a never-colour-alone hole
`client/addons/engine/render/crack.gdshaderinc::crack_spacing_m`; `client_rendering.md` §5.4

`spacing = cell_m · 2^ceil(log2(12 · pixel_m / cell_m))`. Taking pixel_m from `IsoCamera.pixel_metres`:

| Tier | View | px per 0.1 m cell | Voronoi spacing |
|---|---|---|---|
| rig and max | golden, 72 px/m | 7.2 | 0.2 m |
| laptop (scale 0.5) | golden | 3.6 | 0.4 m |
| every tier | the 12 m play zoom | fewer than at golden | at least 0.2 m |

A one-cell pattern needs a view under about 6 m. So this is not a laptop-only concession: at every shipped zoom and tier, §5.4's "each cell carries 3-D Voronoi edges" is no longer what is drawn. §5.4 is unedited and now false.

The consequence follows from `hit_normal` and `carve`; I reasoned it from the code and did not render it:
- Shape comes only from grooves, and from the lip bevel within about 2w of an edge.
- A cracked cell that no Voronoi edge crosses draws flat, darkened only: colour alone, which a CLAUDE.md standard forbids.
- At 0.4 m spacing most isolated 0.1 m cracked cells have no edge. At 0.2 m, many don't.
- `colour_alone_findings` measures over the large crate ramp and wall_north's 10×4×12 patch, so it cannot see this. A one- or two-cell chip from damage is a normal game state.

fold.md rightly lists this as owner decision 4. It still needs to be recorded in §5.4, which can be done word-neutrally by replacing "each cell carries" with the spacing rule, and the isolated-cell case needs a fix or a strict red gate. One option: guarantee an edge in every cracked cell, for instance by seeding a feature point at each cracked cell's centre at any octave.

Two lesser points:
- The pattern re-tiles at each octave of zoom, which is a pop by another name.
- Laptop and rig draw different patterns at the same view. That is acceptable as detail only if §6.3's agreement metric is stated to tolerate it.

### SHOULD-FIX N3: the design's owner-facing sections contradict the record
`client_rendering.md` §10 and §8

§10 says "None open" while six owner decisions are open (A2's residue). §8 says the upload meter is "B5, gated in CI" while B5 says it has no meter and is broken by 10–50×. Both can be fixed without adding words. For §10, replace its sentence with a pointer to fold.md's list. For §8, change the status cell to "no meter; broken as built (B5)". As written, the design document tells the owner the opposite of what the branch knows.

### NIT N4: the material seam checks presence, not its contract
`client/addons/engine/render/cell_snapshot.gd::problems`

FIELDS.md now promises "ids 0–15", but `problems()` refuses only an empty vocabulary. It does not refuse an out-of-range id, two names sharing one id (the last colour wins silently in `use_palette`), or a material-channel value missing from the vocabulary (it draws magenta with no report).

The 16-material cap is a client capacity limit. It lives only in a test fixture's notes and a shader array, not in §4.2 or §5.5. It will bite when `data/materials/` passes 15 solids. Record it, and refuse in `problems()`.

### NIT N5: the region-bounds cache is keyed on object identity
`client/tests/support/render_stage.gd::show_snapshot`

`if snap != _snapshot` recomputes the bounds only for a new object. Its comment invites a decoder that "keeps one snapshot per region map". Scenario: a decoder that updates one `CellSnapshot` in place when a `regions` message arrives keeps stale cut boxes, and the wrong wall is cut. Step 7 already plans `regions_version`. Key the cache on that, and carry the rule into B30's engine node.

### NIT N6: §2's test bullet lost its deletion proof and miscounts the advisory
`client_rendering.md` §2, "Test (step 8)"

- To stay within budget, "Proved by deletion: with the cut off, the yaws facing a wall fail" was cut. The design no longer requires the cut-away gate's proof, and fold.md doesn't say it was rerun with the new rule and the pavement samples. fold.md also gives no rendered result for the three new gated pavement samples. Executor should confirm that they ran and pass.
- "It hides 13% at two yaws" is really four (sample, yaw) pairs over three yaw steps (crate-south at k 1 and 2, crate-east at k 2 and 3).

### NIT N7: §5.3's formula uses an undefined T₀ and lost its tag
`client_rendering.md` §5.3 "Glow"

T₀ is the catalogue offset (`emission.gdshaderinc::glow_emission`'s `k0`), but §5.3 never says so. The `[engineering]` tag on a stylisation was dropped in the same edit.

## Checked, nothing found

- **The short-side rule elsewhere:**
  - The end wall (0.4 × 3.2) clamps x only. Its decision is y-independent, and its face is out of reach, so it is correct.
  - The crate isn't flagged, so the rule never applies to it.
  - Inside the alley, every side-wall decision is x-independent, which fixes A4's original scenario.
  - A square or near-square flagged region degenerates to the nearest-point rule, so it pops at corners, and the axis flips discontinuously at aspect ratio 1. No such region exists today. The plane-of-face fix in N1 also removes this. Otherwise §2 should say the rule assumes long, straight walls.
- **GoldenShot in `tests/support/`:** it parses the golden scene's argv, a test-only concern. B27 keeps `tests/*` out of exports, and nothing under `addons/` references it. Its "crate" requirement is a fixture fact, appropriately in tests.
- **Word budget:** `client_rendering.md` is 3,796 words by `wc -w`, against 3,800 at both 35a1702 and ce06d7b. It did not grow. The cost was N6's dropped sentence.
- **Server/client split:** the fold adds no write path. Cut and palette are uniforms only, and `ImageTexture3D.update` in place is visual only.
- **Engine/game boundary:** no new `res://game` or `res://tests` reference under `addons/` (grep).
- **Departures recorded outside a commit message:**
  - Cut rule: §2.
  - AO: §5.5.
  - Emission and the 920 °C correction: §5.3.
  - Black night: B30.
  - Flame particles: B30.
  - Crate advisory: §2.
  - Upload budget: B5.
  - Crack polygon floor: **fold.md only** (N2).
  - Owner decisions: **not in §10** (N3).
