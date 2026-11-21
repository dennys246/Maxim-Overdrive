# Step 8 shader: Architecture

Scope read: CLAUDE.md, `docs/code_review.md` (always-on lenses), `docs/design/client_rendering.md` §1, §2, §5–§8, §10–§12, `docs/design/tile_and_client.md` §1, `docs/plans/checklists.md` Step 8, `docs/standards_backlog.md` B6/B7/B19/B25, and all of `git diff 35a1702...HEAD`, including both commit messages. Read-only; I ran no gate, test or Godot.

## Findings

### SHOULD-FIX 1: the advisory exemption turns off the gate for all four yaws at two samples, not just the two pairs the crate hides
`scripts/golden_measures.py::cutaway_report` / `CUTAWAY_ADVISORY`

The exemption is keyed by sample name (`match["sample"] in CUTAWAY_ADVISORY`). That ungates all eight (sample, yaw) pairs of `crate-south` and `crate-east`, but by the commit's own account the crate hides the body at only two of them. This is a loosened tolerance, the charter's example of a band-aid.

Failure scenario: a change stops `wall_south` from being cut at yaw 45. A body at `crate-south` (6.3, 2.35), with wall_south between it and the south-east camera, is then fully hidden. `cutaway_report` files that as a note, `golden_run` prints "advisory" and the job passes.

Fix: exempt only the measured (sample, k) pairs and gate the rest. Better still, settle the §2 conflict on the metric itself: divide by a frame with only the *cut-flagged* regions removed, so the test measures what the cut leaves, not what the never-cut crate hides. That changes §2's metric, so it is the owner's call. Either way, §2's test text still says "≥ 95% … at the crate", so the design and the code disagree today (see 2).

### SHOULD-FIX 2: departures "for the owner" live only in a commit message; the design and the backlog still say otherwise
`docs/design/client_rendering.md` §2 test bullet, §5.5 table, §10; `docs/standards_backlog.md` B7

The commit lists departures "each for the owner", but only one reached a document: the §2 cut rule, amended in place at an unchanged 3,800 words (I checked). The rest:
- **AO:** §5.5 still says max uses `6-tap`; `client/game/tiers/max.tres` has `ao_taps = 8`. On the merits I agree: six taps have no symmetric layout on a square face, and the two extra reads cost almost nothing. Editing the table cell adds no words.
- **Crate samples:** §2 still requires ≥ 95% at the crate; the code reports those samples without gating them (finding 1).
- **Black background:** the per-buffer-path clear-colour behaviour of Godot 4.7.2 Compatibility is a measured engine fact. It is recorded only in a comment in `client/tests/support/render_stage.gd::NIGHT`. It is not a §9 probe, a §5.3 note or a backlog row.
- **Flame particles:** not built. `RenderTier.flame_particles` is a field nothing reads, and the tests check its value anyway.

§10 still says "None open". CLAUDE.md says a finding with no code to mark becomes a backlog row or a known gap, and forbids silent deferral. A commit message is neither.

Failure scenario: the owner reads §10 and B7, sees nothing open, and merges. The next author builds `main.tscn` with a non-black night sky, and the tiers disagree in play by ΔE 11 while every check passes (see 3).

### SHOULD-FIX 3: the render composition lives in test support, so the goldens test a stage, not the game
`client/tests/support/render_stage.gd::RenderStage`

`RenderStage` is where the renderer is actually put together:
- the Environment (linear tonemap, `glow_hdr_threshold` 1.0, the black background);
- the tier's `scaling_3d_scale` applied to the viewport;
- `pixel_m` derived from the viewport (`aim` reads `scaling_3d_scale`, so it silently depends on `use_tier` having run first);
- region bounds computed once;
- the Cutaway-to-CellVolume wiring.

Its docstring says it is "never used by the game". So when step 8 builds `client/game/main.tscn`, the game must re-derive all of this. Every golden, cut-away and tier-agreement number then describes the test stage's composition, not the shipped one. This is the "repeat the fix at each call site" shape, and the "a fix ships with a caller" rule is met only by tests.

Failure scenario: the game calls `use_tier` after `aim`, for example when the player switches tier at runtime. The laptop tier keeps the rig's `pixel_m`, so its grooves fall to 0.75 px and shimmer, breaking §5.4's 1.5 px floor. No test sees it.

Fix: move the composition into an engine node under `client/addons/engine/render/` that both `main.tscn` and the check scenes instantiate, and have it recompute `pixel_m` whenever the tier or the zoom changes. Or, at the least, add a backlog row naming this before `main.tscn` lands.

### SHOULD-FIX 4: "No pops" is false on the pavement, where the player spawns
`client/addons/engine/render/cutaway.gd::cut_regions`; §2 "No pops"; the commit's "never pops for a side wall"

The nearest-point rule is clearly better than the box-centre rule inside the alley. I checked it by hand: at (5.5, 2.925) and yaw 45, the centre rule gives dot = −0.16 and cuts wall_north, while the nearest point gives +0.48 and leaves it, as the commit says. The No-pops argument also holds for x in 1.2–11.6 m.

On the pavement (x 0–1.2 m, the spawn), the nearest point of a side wall is its end corner, and the sign then depends on where the player stands. For wall_south at yaw 315 (f = (0.707, 0.707)): at (0.5, 2.0) dot = 0.707·(0.7 − 1.6) < 0, so the wall is cut; at (1.1, 0.45) dot = 0.707·(0.1 − 0.05) > 0, so it is not. wall_north at yaw 225 is the mirror case. A 4 m wall therefore appears and vanishes while the player walks, with no camera tween, which contradicts "the flag flips only at tween start".

`client/tests/cutaway_check.gd::SAMPLES` and `test_cutaway.gd` have no pavement position, so nothing catches it. The fix is to state the exception in §2 and test it, or to decide side walls by the plane of their inner face.

### SHOULD-FIX 5: a deletion proof promised for "next commit" never appears
Commit c656c33, "the depth swap needs the goldens: next commit"; commit ce06d7b

ce06d7b records the goldens but says nothing about swapping the depth formula. §6.2 names that swap as the depth golden's deletion proof, and CLAUDE.md requires the proof in the commit message. The golden view does include actor 2, half inside wall_north, so the golden could carry the proof. But no one has shown that the depth write is what it protects.

Failure scenario: `DEPTH = ndc.z` lands on the Compatibility path, and actor 2's capsule draws over the wall. The golden may well catch it, but the branch claims nothing it has checked. Either run the proof and record it, or list it as open in B7.

### SHOULD-FIX 6: B7 omits that the measured checks run only in a non-required job that has never run
`docs/standards_backlog.md` B7; `scripts/golden_run.py::golden_job`; `scripts/prepush.sh`

The cut-away ≥ 95% check, the never-colour-alone checks and tier agreement run only inside the golden job. That job is not required in branch protection and has never run on GitHub. `golden_measures`' docstring says they "fail on the owner's Mac as they would in CI", but only if someone runs `golden_run.py --no-xvfb` by hand: `prepush.sh` never calls it. §6.5 says prepush runs the tier-agreement and greyscale checks when a GPU context exists. That isn't built, and B7's "Missing" list doesn't say so.

Failure scenario: a local push removes the carving. The gate passes, and the never-colour-alone rule's only check never runs until someone looks at CI. Add the missing prepush hook to B7's missing list. CLAUDE.md's colour-alone Guard could also cite `scripts/golden_measures.py::colour_alone_findings` now that it exists.

### SHOULD-FIX 7: a material without a palette entry draws black on a black background, silently
`client/addons/engine/render/cell_volume.gd::use_palette`, `material_palette.gd::by_id`, `lighting.gdshaderinc::albedo_of`

`by_id` skips names the palette lacks, `use_palette` fills those with `Color.BLACK`, and ids ≥ 16 are dropped or clamped to `palette[15]` in the shader. Neither `CellSnapshot.problems` nor `SnapshotFixture` checks that every material in the vocabulary has a colour and an id below `PALETTE_SIZE`. Lit black albedo stays black, and since the background is now black too (finding 2), that geometry becomes invisible. That is a quiet fallback, which CLAUDE.md counts as a swallow.

Failure scenario: someone adds `brick` to `data/materials/core.yaml` and authors a wall in it. The wall vanishes, except for its glow. All five materials have colours today, so this is latent. Refuse, or report loudly, when a material has no colour or an id is out of range.

### NIT 8: the seam's vocabularies are split
`cell_snapshot.gd::CellSnapshot` vs `snapshot_fixture.gd::material_ids`

`region_names` lives on `CellSnapshot`, but the material vocabulary lives on the test-only `SnapshotFixture`, and `RenderStage` reads it from there. Step 7's decoder must fill the seam plus something outside it. Put `material_ids` on `CellSnapshot`.

### NIT 9: FIELDS.md misses the grid-origin assumption
`client/tests/fixtures/snapshots/FIELDS.md`; `cell_volume.gd::show_snapshot`; `cutaway.gd::flagged_boxes`

The box position, the cut boxes and the actors' `pos_mm` all assume cell (0,0,0)'s corner sits at the world origin. FIELDS.md claims to name "every field it assumes" but doesn't list this one. That is harmless for one tile and wrong the moment a frame carries an offset.

### NIT 10: one constant written in two places
- `cutaway.gdshaderinc` hard-codes `cut_ids[8]` and the loop bound `8`, while `Cutaway.MAX_CUT` is 8.
- `lighting.gdshaderinc` has `palette[16]` and `clamp(…, 0, 15)`, while `CellVolume.PALETTE_SIZE` is 16.

If one side changes, they disagree silently. A `#define` in the include, with a unit test that compares it to the GDScript constant, would hold them together.

### NIT 11: game facts in the Apache engine half
- `cutaway.gd`'s docstring carries alley numbers (10.8 m, x = 5.7 m).
- `cutaway_regions.gd` says "never the crate".
- `iso_camera.gd` hard-codes 40° and 45° as engine constants, though §7.1 puts the camera rig in `game/`.

This is not a B25 violation (no `res://game` path, which I grepped for), but the boundary is getting blurry.

### NIT 12: the alley's geometry has a third copy
`scripts/client_fixtures.py::PRIMITIVES` restates tile §1.1's table. `--check` compares the fixtures only with the script's own copy. When `tests/fixtures/scenes/alley_box.yaml` lands, nothing makes the two converge. Add a note, or read that file when it exists.

### NIT 13: CLAUDE.md's Layout section is out of date
It doesn't mention `scripts/client_fixtures.py`, `scripts/golden_measures.py` or `client/tests/support/`.

## Checked, nothing found

- **Server/client split:** `Cutaway` and `CellVolume` write shader uniforms and nothing else. There is no network or intent path, and no picking yet.
- **Protocol seam:** nothing under `client/addons/` reads the fixture format or the unfrozen wire. The fixture reader sits under `tests/support/`, and `CellSnapshot` knows no wire fields.
- **Engine/game boundary (B25):** no `res://game/` or `res://tests/` reference under `client/addons/` (grep). Game data, `client/game/*.tres`, is reached only from tests and test support.
- **Engine whys:** present for the 3-D textures, the BoxMesh plus fragment shader (no compute on Compatibility), the `#define` glow variants, SubViewport, MeshInstance3D, orthographic projection, unshaded and cull_back, and `look_at` versus setting the basis.
- **Never colour alone:** the crack carves shape (Voronoi grooves at least 1.5 px), glow adds HDR brightness, and the cut is hatched. The masks come from the shader's own debug passes.
- **Shader includes, one concern each:** traversal, cutaway, crack, lighting (with AO and hatching), emission and debug are cleanly split. `cell_volume.gdshaderinc` orchestrates: the walk, the normal, the shade. Its `Hit` struct carries crack fields, which is acceptable for the orchestrator.
- **Silent swallows:** every `push_error` path reports. The cut-limit truncation warns. With three walls and `MAX_CUT` 8 it can't fire today.
- **Word budget:** `client_rendering.md` is 3,800 words before and after.
- **Size limits:** the Python in `scripts/` looks well within them. GDScript has no tripwire (B19 (3), already open).
- **B7 honesty about CR-B3:** the byte-identical result at 128 and 256 bits is stated plainly, as is goldens recorded under emulation.
- **The nearest-point cut rule:** correct on the merits inside the alley (I verified the yaw-45 case by hand), and recorded in §2 with the reason. The only exception is finding 4.
