# Architecture review: client_objects.md (D-B2), round 1, at 51c9660

Lens: Architecture. I read `docs/design/client_objects.md` in full and the probe's header, and checked the design against `fire_solid.md` (§0, §1, §3.2, §4.4, §5.4–§8), `fire_model.md` (§6.2, §7, §9.2, §10), `client_rendering.md` (§4–§9), `tile_and_client.md` (§3.2, §5.5, §6.3), `world_v2.md` §8, `boundaries.md` §8.3, the backlog rows B5, B7, B26, B36, B40 and B42, `reviews/step8_shader/fold.md` (owner decisions), D-B2 and A-S7 as written, `docs/roadmap.md` Phase 1, `docs/plans/foundations_plan.md` rows 6–8, `docs/plans/checklists.md` steps 6–8, `src/simcore/protocol/encoding.py`, `client/addons/engine/render/emission.gdshaderinc`, and PR #37's `rulings.md` (read-only). I ran nothing in the repository except reads, plus one throwaway Python calculation (A-N1).

Summary: **1 BLOCKER, 6 SHOULD-FIX, 3 NIT.** The object-pass contract itself is sound and in the right layer: geometry plus per-segment state on the wire, a second instanced pass, shape by burn-away and edge density, and the server staying authoritative. The defects are in three places:
- the phase plan the design assumes, which is not the one in force;
- who owns what it asks of other steps;
- stale copies its change list leaves behind.

## BLOCKER

### A-B1. The design is scoped to a Phase 1 that no longer exists. The ruled exit, the fallback D-B2 named, is treated as a hypothetical risk, and the scenario beats are deferred to a trigger that never fires in Phase 1.

**Location:** `client_objects.md::§2` (third consequence), `§5.3` ("Without a flame table"), `§7.2` (Flame shape row), `§7.3`, `§9` (6.2 row).

**Defect.**
- §2 says "No in-world fire exists before 6.4 … step 8 follows 6.4 (fire_model §10.2), so step 8 draws all of it." The plan in force says otherwise:
  - `docs/roadmap.md:56`: the Phase 1 exit is the fire fallback (owner, 2026-11-20), "light a slab with the torch, and watch it char, burn and flame out".
  - `roadmap.md:71`: the crate and rungs 6.2–6.4 (flame object, two bodies, crib) moved to Phase 2.
  - `foundations_plan.md` row 6: "6.2–6.4 long term (fallback, 2026-11-20)".
  - PR #37 `rulings.md` row 59: "The Phase 1 exit is the torch-lit slab."
  - fire_model §10.2's ordering, which the design cites, is the superseded plan.
- So:
  1. **§5.3 calls the ruled exit a "recorded risk".** It says "If fire_model §7's fallback stops the exit below 6.2, burning shows by brightness only … a recorded risk, not a gap this design can close." The fallback is not an "if"; it is the decision. D-B2 explicitly demanded the fallback be covered: "The fallback exit, 'a burning slab that flames out and glows', still needs it." The design answers it in one conditional sentence.
  2. **The flame-shape check never runs in Phase 1.** Neither do the `flames` table (§3.4) or the 6.2 rows of §9. Nothing says that the Phase 1 exit's "flame out" therefore has no flame shape at all.
  3. **The scenario beats have no owner with a live trigger.** §7.3 hands G2–G4's beats to "the tile §6 revision before 6.4 (D-S2)". 6.4 is Phase 2. The current beats can't be computed on the new representation:
     - tile §6.3 item 3 defines `t_crack` over "cells with ≥ 10% of their fuel charred", but fuel is no longer in cells;
     - item 4 defines `t_glow` on the "envelope-layer skin", which §5.1 itself says nothing computes.
  4. **By the design's own premises, the Phase 1 exit has no in-world ignition.** §2 says "the only in-world pilot is `kindle` (6.4)". (Strictly, `kindle` the intent lands with vocabulary v1 at step 5, tile §3.2. Its fuel pilot is fire_model §5.4's flame object, which is 6.2.) With 6.2–6.4 in Phase 2, nothing lights the slab in the world in Phase 1. That may be an upstream hole rather than this design's to fix, but the design states the facts that expose it and doesn't raise it (CLAUDE.md, "Raise a problem the moment you see it").

**Failure scenario.** Step 8 is built to this design. At the exit:
- the flame-shape check can't run;
- G2–G4 have no defined beats, and their owner (D-S2) is waiting for 6.4, a Phase 2 step;
- the scripted exit has no path from the torch to a flaming slab.

Phase 1 can't close, and no document names who decides. This is D-B2's own failure scenario ("nobody has sized"), one step later.

**Fix (unverified).** Restate §2, §5.3, §7 and §9 against the fallback exit. Name an owner and a Phase 1 trigger for the exit's beats. State as a finding for the owner how the torch lights the slab in Phase 1.

## SHOULD-FIX

### A-S1. A 6.0b requirement lives only in a client document. It silently reverses A-S7's fold and has no caller until step 7.

**Location:** `client_objects.md::§3.1` ("Presentation only"), `§3.2`/`§3.3` (the reductions' definitions), `§8` (fire_solid row), `§9` (6.0b row).

**Defect.**
- §9 requires that at 6.0b "the frame publishes the fuel view … in f64", and §3.1 has the tables "join the registry with 6.0b".
- `fire_solid.md` §5.6, the 6.0b build spec, says "6.0–6.1 sends no objects". That was its answer to A-S7, whose fourth bullet reads "'6.1 is server-only', so nothing needs snapshot tables in 6.0" and whose fix was "Take the snapshot out of 6.0".
- This design puts frame publication back into 6.0b without saying it reverses a folded finding.
- §8's fire_solid row only turns §5.6 into a link and renames the §7 row. It adds nothing to fire_solid §0's landing order, its §7 placement table (no `frames.py` row) or its §6 tests (the cost of 2×10⁴ reductions per step, and B5's work counters), and nothing to `checklists.md`.
- Questions F1–F3 to fire_solid's owner are recorded only in §9 of this document, although §3.2's segment-span formula depends on their answers.
- The reductions are defined here, in the "Meaning" column of §3.3 (radiance-equivalent T, Σ a_p·thickness, residue ÷ solid mass). The header assigns "the physics of every quantity" to fire_solid or 6.2. Each column's meaning therefore has two owners (F1, "a name is a meaning"). When 6.2's partial transfer changes parts and nodes, this client document has to change as well.
- The radiance weighting is a presentation choice made because glow goes as T⁴, yet it is computed in the core. boundaries §8.3 moves presentation out of the core.

**Failure scenario.** The 6.0b builder works from fire_solid, as its §0 tells them to, and ships no frame publication. Or they ship it with no consumer until step 7 ("A fix ships with a caller"). This is the B42 mechanism this design's own §8 lesson describes: a build that read one document while the contract lived in another.

**Fix (unverified).** Put frame publication in the step that first consumes it (step 7), or record the change in fire_solid §0/§7 and the checklist, saying it reverses A-S7. State the reductions' physical meaning in fire_solid, with this document owning only the wire columns. Record F1–F3 in fire_solid.

### A-S2. §8's change list leaves stale copies of contracts this design revises.

**Location:** `client_objects.md::§8`, `§3.1`, `§3.5`, `§4.3`, `§7`.

**Defect.** The design changes these, and §8 doesn't list them:
- `client_rendering.md`:
  - §5.6, picking: the object test and the floored geometry (§4.3 here). §5.6 still says `dda.gd` only.
  - §5.5, the tier table's flame-particle column.
  - §6.1, the renderer goldens list (fuel and severity fixtures).
  - §6.3, the ID-mask areas (which now include fuel).
  - §6.4, the never-colour-alone checks ("over cracked cells" only).
  - §8, budgets: §7.4 here adds rows.
  - §9's probe list, and `research/godot_probes.md`, which has 0 mentions of fuel. B26's upgrade procedure compares probe reruns with that file, so the new probe has no baseline.
- `docs/plans/checklists.md` step 7 still lists "`surface_glow` and `burning`", and step 8 still lists "one crack-and-glow shader".
- `foundations_plan.md` row 8 still says "one crack-and-glow shader".

Within the design:
- §3.5 restates `client_rendering.md` §4.2's channel list and frame bytes, while §8 also writes them into §4.2.
- §3.1's send rule is stated here and also becomes §4.1's "fuel clause".

Each is a contract in two places (CLAUDE.md "One owner per contract", B36).

**Failure scenario.** Step 7, working from its checklist, freezes `surface_glow` and `burning` into protocol v0. Or step 8 measures G3 against §6.4's cell-only masks and misses the fuel pass.

**Fix (unverified).** Complete §8. Make §3.5 and §3.1's send rule links, or make them the owners and turn client_rendering's copies into links.

### A-S3. §5.1's "the same quantity under its true name" is false, and its Known gap has no numbers.

**Location:** `client_objects.md::§5.1`.

**Defect.**
- **The masking.** `encoding.py:26` is `glow = clip((T − 525)/(1500 − 525)) × frame.solid`, so air cells send 0. `temperature_c` is unmasked: air cells carry their own temperature.
- **Why that matters on the rig tier.** The linear glow sampler (`emission.gdshaderinc::glow_count`) samples "at the cell's centre plane … blends across the face with the neighbouring cells". Lateral neighbours at a face's edge include air cells. Today they read 0. On `temperature_c` they read the air's temperature.
- **Consequence.** Switching inputs changes what draws: hot air beside a wall's edge (a `kindle` deposit, contact heating) brightens the edge. The text says nothing changes.
- **The Known gap.** It says structural glow "comes on late and dim, by an amount set by the 0.1 m channel grid" and defers the number to "with the build". CLAUDE.md requires Known gaps "with numbers". fire_solid §3.2 already gives the cell-mean resistance against the skin (about 14·ΔT and 56·ΔT W/m² against a closed form of 39·ΔT), which a bound could start from.
- **The constants.** The glow start and span move to "client constants", but `encoding.GLOW_START_C` and `GLOW_FULL_C` are not said to be deleted, so they risk becoming a second copy of the same constants.

**Failure scenario.** The rig tier's golden edges brighten where air is hot and the laptop tier's (nearest filter) don't. Tier agreement (§6.3) then moves for a reason the design says can't exist.

### A-S4. B42 is closed at design acceptance, while the shipped client still reads the provisional channels.

**Location:** `client_objects.md::§8` (standards_backlog row).

**Defect.**
- B42's trigger is "before step 8 closes".
- The code still reads `surface_glow` and `burning` as live channels (`cell_volume.gd:17`, `cell_snapshot.gd:16`, `emission.gdshaderinc:14,67`), and the encoder sends neither.
- Closing the row on design acceptance removes the only guard row for "visuals come from snapshot channels" while the gap is still in the tree. A checklist item is not a backlog row that `lint_standards` counts.

**Failure scenario.** Step 8 slips. The client keeps drawing hand-placed channels that no server sends, and the backlog shows no open gap.

### A-S5. Burning has no check that a deletion fails in Phase 1.

**Location:** `client_objects.md::§5.2` (Burning), `§7.2`.

**Defect.**
- "Burning" is shown only by `ignited_fraction`'s emissive term, as brightness.
- §7.2 has a glow check and a flame-shape check (6.2), but no row that fails when the ignited term is deleted.
- Under the fallback exit (A-B1), flame shape never runs. Deleting the term leaves only `surface_temperature_c` glow, and the glow check passes on that.
- The exit's "burn" beat is therefore kept by no measured check, only by attention (CLAUDE.md, "Prove a guard by deleting what it guards").

**Failure scenario.** A refactor drops the ignited term. Every Phase 1 golden check stays green, and a flaming slab draws as a merely hot one.

### A-S6. D-B2's sizing and plan half is unanswered.

**Location:** `client_objects.md::§8`, `§9`. D-B2 reads: "None of this is in §10.1, in §10.2's PR list, or in the size."

**Defect.**
- The design lists requirements by step but gives no size for step 8's object pass. It needs:
  - a second render path;
  - textures;
  - the AA choice, whose candidate MSAA re-records every golden;
  - picking;
  - five new checks with deletion proofs.
- It also touches neither fire_model §10.2's PR list nor the plan's row 8.
- D-B2's failure scenario was exactly that "nobody has sized" the redesign.

**Failure scenario.** Step 8 is scheduled as "one crack-and-glow shader" (plan row 8) and overruns with no recorded estimate.

## NIT

### A-N1. The radiance-equivalent temperature applies CLAUDE.md's rule only to a pure T⁴ law, not to the shader's law.

**Location:** `client_objects.md::§3.3` ("Why radiance-equivalent").

**Defect.** The shader's law is 7·((T/1773)⁴ − (T₀/1773)⁴), clipped at 0, with a hue ramp in T. That is not a pure T⁴ law, so the radiance-equivalent temperature is not "evaluate the law per part, then integrate". Take a segment half at 1,000 °C and half at 20 °C:
- the radiance-equivalent is 798 °C, which emits 0.646;
- the per-part mean is 0.787;
- so the segment draws 18% dim (*verified*: a three-line Python calculation of the shader formula).

It is exact in 6.1, where a segment flips whole. The text should say it is exact only there.

### A-N2. §3.1 attributes to world_v2 §8 a versioning rule that world_v2 §8 doesn't state.

**Location:** `client_objects.md::§3.1`.

**Defect.** §3.1 says each table "addition bumps the registry version, not the protocol (world_v2 §8)". world_v2 §8 says that only of an *optional* channel. These tables are all `required`, so adding one (flames) makes every old reader refuse every frame. Adding kind `bed` likewise fails the "kinds known" check. Either the rule's owner states the extension to required tables, or the claim is wrong. Wire integrity owns the substance.

### A-N3. §11's "Not settled here" items mostly lack an owner and a trigger.

**Location:** `client_objects.md::§11`.

**Defect.** Only "any NPC read of fuel" names one (the NPC fire note). Flame appearance, a bed's slats, where the ignited part lies within a segment, and delta frames have none. The first three are presumably 6.2's design. Say so. Delta frames are world_v2's reserved `kind: delta`, with no trigger.

## Checked and found sound

- **Server authority.** Picking returns a point that the server re-validates; interpolation is visual only, and geometry never interpolates (§4.3). Flicker and particles are visual only and off in goldens.
- **Visuals from snapshot channels.** The object pass draws only from wire tables. Albedo by recipe comes from client data keyed by name, as materials do, with magenta for unknowns.
- **Root cause, not a band-aid.** The design rejects voxelising fuel into channels (that would make the look depend on dx) and per-cell object lists (15.4–40 MB) with reasons. The second pass is the root fix D-B2 asked for.
- **Never colour alone.** Crack severity moves from width to edge density, with the derivation in §6.2 matching B7's measurement. Burn-away shows as gaps and char as luminance on thin fuel. Owner question 1 is raised honestly, not hidden.
- **A-S7's defects are fixed.** Surface temperature is f16; there is a char column (`char_fraction`); the tables are column-extensible.
- **Docs-contracts rows.** Row 79 (`crack` keeps one meaning) is applied (§3.5; §8's tile row). Row 10 is answered.
- **Layers on the client.** A `Fuel` node beside `CellVolume`; MultiMesh with data textures; the B5 costs are measured, not guessed.
- **Word budget.** 4,368 words, under 6,000. client_rendering is pledged net ≤ 0 (now 3,774 words).
- **Owner questions.** Each has a recommendation. Q3 (the AA choice) is deferred to step 8 with a deciding measure.
