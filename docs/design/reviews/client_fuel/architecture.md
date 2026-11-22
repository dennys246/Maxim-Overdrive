# Architecture review: phase1/client-fuel (step 8 fuel pass), round 1

**Scope read:** `git diff 69483d9` (commits 76f7570..d91df0f plus the working tree), the untracked files, `docs/design/client_objects.md` §0–§7, `client_rendering.md` §4.1 diff, `research/fuel_antialiasing.md`, `checklists.md` step 8 (index and working tree), `fire_solid.md` §5.6 (the state column), and `standards_backlog.md` B5/B42. I made no changes and ran no git writes. Most of the structure is sound:
- `FuelSnapshot` is the seam, and its `problems()` refuses unknown kinds.
- `FuelFixture` lives under `tests/`.
- Every transform goes through `IsoCamera.to_godot`, and the shaders use `axes.gdshaderinc`.
- The glow curve and key light are now one include each.
- Visuals come only from snapshot columns, and nothing feeds back to the server.

The findings are about docs that no longer match the code, bars changed without an owner ruling, and open items with no owner.

## Findings

### SHOULD-FIX A1: `docs/design/client_objects.md::§7.2` (Burn-through and Tier agreement rows): two accepted bars rewritten with no owner ruling cited
- **Burn-through.** Base 69483d9 required "live segments at the floor or wider". The tree now requires only that "every live segment farther than that radius from the run's ends draws". That drops the width half of the bar: one pixel now satisfies it (`golden_fuel.py::burn_through_findings` checks `.any()`).
- **Tier agreement.** "fuel ID mask per kind ... within 15%" becomes summed coverage per object, in a window widened by `AREA_WINDOW_PX = 2.0` on every tier.
- The per-object change is arguably stricter, and its reason is recorded (a pooled area hid the floor-deletion). But both are edits to a contract table the owner accepted on 2026-11-22. Neither the diff nor `reviews/client_objects/` cites a ruling. I grepped for "floor or wider", "per object" and "depth_prepass".

**Failure scenario:** a regression that draws every live segment one pixel wide (the 2 px floor lost on one segment kind) passes Burn-through. It is caught only if tier agreement or the golden happens to see it. Nobody decided to give up the width check.

**Fix (unverified):** put both rewrites to the owner and record the ruling. Or restore the width clause: the drawn width per live segment ≥ the floor, measured across the footprint strip.

### SHOULD-FIX A2: `client_objects.md::§4.1` ("That texture holds three RGBA8 texels...") no longer describes the code
- The design says texel 0 is "the row's three bytes and `state`", and that "`state` updates the RGBA8 texture's fourth byte".
- The code works differently (`fuel_pass.gd::_write_instance`, `fuel_object.gdshaderinc::instance_at`):
  - texel 0 holds the first row plus the **recipe palette slot**;
  - texel 1 holds `segment_count` plus the **object row**;
  - `state` travels in a separate per-frame `state_tex`.
- The behaviour the design asks for still holds: a burnout never triggers a rebuild. But the design now holds a false statement, where a reader would take the layout.
- The same section says "An unknown recipe or kind is reported and drawn magenta". `FuelSnapshot._vocabulary_problems` refuses an unknown kind, which is the right call (a new kind is a protocol bump, per client_rendering §4.1), so the design's "kind ... drawn magenta" is also stale.

**Fix (unverified):** update §4.1's texel list and the kind rule to what was built. Do it within the word budget (see A6).

### SHOULD-FIX A3: `fuel_pass.gd::_write_instance` / `use_palette`: an unknown or overflowing recipe is drawn in a real recipe's colour, not magenta
`_recipe_slots.get(id, PALETTE_SIZE - 1)` sends a missing id to slot 15. Slot 15 is magenta only while fewer than 16 recipes exist.

**Failure scenario:** with 16 or more recipes, `use_palette` reports "recipe X is past the shader's 16 colours". X's id is then missing from `_recipe_slots`, so X is drawn in recipe 16's real albedo. The docstring's "Those draw magenta" and §4.1's rule are both false here, and the only signal is a `push_error`.

**Fix (unverified):** reserve slot 15 for `UNCOLOURED`, so the shader holds 15 real recipes. Then test 15, 16 and 17 recipes.

### SHOULD-FIX A4: `fuel_flame.gdshader::vertex`: the burnt-out rule has two owners, and the flame path ignores it
- §4.3 says a burnt-out object (`state` 1) draws "without glow or flame".
- `fuel_object.gdshaderinc::fuel_colour` drops glow and burning when `state_tex` reads 1.
- The flame shader keys only on `ignited_tex[INSTANCE_ID]`. It never reads the object's state, and it can't, because a flame instance carries no object row.

**Failure scenario:** if fire_solid's burnout leaves `ignited_fraction` above 0 on the remaining char segments, a burnt-out stick keeps its flames while its surface goes dark. Nothing in `fire_solid.md` §5.6 that I found requires ignited to be zeroed at burnout. The `rod_spent` fixture has ignited 0, so no check catches this.

**Fix (unverified):** give the flame pass the object row per segment, for example a segment-to-object R16 row texture built on a rebuild, which is exact. Then apply one shared `burnt_out(row)` helper in the include, and add a fixture segment with state 1 and ignited above 0.

### SHOULD-FIX A5: open items deferred only in a research note, with no owner or trigger
`research/fuel_antialiasing.md` "What this leaves open" holds two decisions and one gap:
- **(1) The stability measure barely discriminates on the rig tier.** "A question for the owner", but it sits in no roadmap row, backlog row or checklist item.
- **(2) Slabs have no edge coverage.** §4.2 now says "Slab edges have none yet (that record's open item 2)". The design defers into a research note, which owns nothing.
- **(3) llvmpipe is unmeasured.** See A7.

A research document is not a deferral. The rules want a named step or a backlog row with a trigger, and decisions in front of the owner.

**Failure scenario:** step 8 closes with "§7.2's checks, each proved by deletion" ticked. Meanwhile slab edges crawl, and a rig-only AA regression passes, with no row that would ever reopen either.

**Fix:** put (1) to the owner before hand-off. Add (2) to step 8's checklist, citing §4.2, with "before the slab exit's goldens" as its trigger. Fold (3) per A7.

Related: `tests/test_golden_stability.py::test_a_hard_edged_line_crawls_well_beyond_the_ideal` asserts `> 1.5 * ideal`, below the 2.0 bar. So it passes while a hard-edged line passes the actual gate, and its name ("well beyond") claims what it doesn't test. The comment is honest. The name and the assertion should say "the rig tier alone does not catch this", or the test should assert against `BAR_RATIO` and be a strict xfail pending the owner's answer.

### SHOULD-FIX A6: `docs/design/client_objects.md`: an existing design document grew from 5,180 to 5,266 words
CLAUDE.md (O22, B24) says "an existing design document doesn't grow". `client_rendering.md` also grew, from 3,742 to 3,745.

The growth comes from §4.2's new AA and depth paragraph, §5.3's cost, and the two §7.2 rows. Part of §4.2's added text restates measurements the research record owns ("0.42 of rig's (0.91 after)"). That also brushes against one owner per contract: the numbers now live in two places.

**Fix:** keep the contract sentence in §4.2 ("rods: analytic edge coverage, one rendered pixel; fringes don't write depth") and link the numbers to the research record. Trim elsewhere until the document is net zero.

### SHOULD-FIX A7: `research/fuel_antialiasing.md` and `client_objects.md` header say "Not run under llvmpipe", but llvmpipe-keyed fuel goldens are in the tree
`client/tests/goldens/compat-llvmpipe-mesa25.2.8-...-godot4.7.2/{rig,laptop,max}/fuel.png` are untracked and timestamped 01:53. That is after the research record (01:41) and the last rod-shader edit (01:44). No render source is newer.

If they were drawn by `golden_run.py` in the CI image, that same run drew `stability_check.tscn` and judged the stick-stability bar under llvmpipe. Those numbers then exist and are unreported, and open item 3 is false. If they were not drawn in the image, a golden under the llvmpipe key isn't what it claims to be (T12).

I couldn't tell which from the tree: no run directory or log survives in the worktree.

**Fix:** state where the goldens came from in the hand-off and the commit. If llvmpipe ran, add its stability table (and the frame-time caveat) to the research record.

### SHOULD-FIX A8: `docs/plans/checklists.md` step 8 doesn't say what this branch leaves undone
The step 8 item still reads as one line covering everything, and the branch delivers part of it. Still to do:
- picking (§4.3);
- the Severity, Outlines and charred-face Crack checks, and the groove view (§7.2);
- Speckle extended to the fuel cold frame: `golden_measures.py::speckle_findings` still reads only `cold-{tier}.png`;
- the fuel B5 measurements (B5's owed rows exist but nothing is measured);
- C S7's head-on readout.

Two entries are stale:
- The "Deferred ... the Burning check run with flames off (S5)" entry is done: `golden_fuel.py::state_findings` uses the `-noflame` frame.
- §7.2 still says "Tier agreement on ID masks isn't built yet (B7). Fuel joins it as its own masks, per kind", which contradicts the new per-object row and `agreement_findings`.

§7.2's heading names `scripts/golden_measures.py`, but the fuel checks are in `golden_fuel.py` and `golden_stability.py`.

**Failure scenario:** the owner merges "the fuel pass" believing §7.2 is complete, when 3 of its 11 rows have no check.

**Fix:** split the step 8 item into done and remaining, drop S5 from the deferred list, and fix the two §7.2 sentences.

### SHOULD-FIX A9: `tools/fuel_aa/stability_frames.gd` can't reproduce the record it backs
- It loads `res://addons/engine/render/fuel_rod_edge.gdshader` for the "edge" mode, and that file no longer exists.
- Its header says "none" and "msaa" need the old shader from commit d91df0f.
- So none of the three columns of the research table can be rerun from the tree that cites them.
- It also builds its own snapshot (`_put`) and its own camera offsets, a second copy of the frame series that `client/tests/stability_check.gd` draws for the gate. The research numbers and the gate's numbers can drift apart unseen.

**Root cause:** the production shader already gives hard edges with `render_pixel_m = 0` ("0 until set, which draws hard edges"). MSAA is a viewport setting.

**Fix (unverified):** drive all three modes through the production `FuelPass`, using `use_pixel_metres(..., scale)` with the fade zeroed, plus `msaa_3d`. Reuse `stability_check.gd`'s frame loop (parameterised by mode) instead of a second copy, and read the `fuel_stick` fixture. Then `measure.py` can be dropped in favour of `golden_run.stability_findings`.

## NITs

- **N1 `fuel_pass.gd::_init`, the flames' `custom_aabb`.** It is a fixed 2 km cube centred at the origin. It disables culling, and it makes the flames' transparent sort key the world origin. That is a hidden special case, though a harmless one today. **Fix (unverified):** set it at `_rebuild` from the objects' bounds grown by `FLAME_HEIGHT_M`.
- **N2 `fuel_rod.gdshader` render_mode.** There is no one-line engine why in the code for `blend_mix, depth_draw_opaque, depth_prepass_alpha`. The why is only in the design, and the work is uncommitted, so it isn't in a commit either. One comment line would do: fringes blend, so only opaque coverage writes depth.
- **N3 `fuel_pass.gd::show_fuel`.** "must be drawable (its filler refused it otherwise)" is a precondition the type doesn't carry. An undrawable snapshot (for example a kind id outside the vocabulary) would silently draw as a slab via `_rebuild`'s `else`. Step 7's decoder will be the second filler. A checked handle, or calling `state_problems()` inside `show_fuel` (it's cheap), would push the invariant into the seam.
- **N4 duplication.** `_vector(snap, table, prefix, suffix, r)` exists three times: `FuelSnapshot`, `FuelGeometry`, `FuelFootprints`. The dtype map exists in `golden_fuel.NUMPY` and `fuel_fixtures.NUMPY`. A `FuelSnapshot.vector()` accessor would leave one copy. Footprints staying an independent projection is right for a test oracle; only the row decoding should be shared.
- **N5 `scripts/golden_run.py::stability_findings`.** It loads the stability frames and judges them inside the orchestrator. `golden_fuel.fuel_findings` and `gm.*_findings` own their own loading. Move it to `golden_stability.findings(dir)` so `golden_run` stays a list of named steps.
- **N6 `client/game/recipe_palette.tres`.** It is game data keyed by `pine_rod` and `pine_slab`, names that exist only in `scripts/fuel_fixtures.py::RECIPES`: no server recipe table exists yet. Either cite the fixture as the source of the names until step 7's recipes land, or keep the file under `client/tests/`.
- **N7 `fuel_pass.gd::instance_images` and `rebuilds`.** These are test-only state on an engine class. They are documented and small, so this is acceptable. Note it in case the class nears the 12-public-member line.
- **N8 `checklists.md`, the S7 measure "fixed 2026-11-22 before any renderer was measured".** This is pre-registration, and it exists only in the index (staged, uncommitted), with the measurements in the same uncommitted tree. Commit it on its own, ahead of the research record, so the history shows the order the claim depends on.

## Questions put to the owner, per the brief

- **Analytic edge coverage on rods only:** a build choice that owner ruling 3 allowed. The open slab half is A5.
- **`depth_prepass_alpha`:** a mechanism with its reason and numbers recorded. Not a contract change beyond §4.2's wording. A6 covers the wording, N2 the code why.
- **Per-object tier agreement:** a contract change (A1).
- **The stability bar's weakness on the rig tier:** honestly reported, but unowned (A5).

## Verdict
No BLOCKER. 9 SHOULD-FIX and 8 NIT.
- A1 and A5 need the owner before hand-off.
- A2, A6 and A8 are honesty fixes to the docs.
- A3 and A4 are real behaviour defects in the display rules (magenta, burnt-out), each needing a test.
- A7 must be answered from the run records.
