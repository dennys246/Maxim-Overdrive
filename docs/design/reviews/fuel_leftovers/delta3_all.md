# Delta round 3, all lenses: phase1/fuel-leftovers (staged, uncommitted, against 2586ed7)

Reviewer: Executor, Architecture, Wire integrity, Client rendering, Trust boundary, Performance (delta 3). Scope:
`delta2_all.md`'s D2-1 to D2-6, the open ET-N1, N-3, N-5, P-N3's trigger, and `fold.md`'s "Delta round 2 folds".

Ran:
- `.venv/bin/pytest -q -p no:cacheprovider tests/test_golden_fuel.py tests/test_fuel_fixtures.py`: 57 passed.
- `scripts/lint_standards.py`: PASS (0 findings).
- f16 rounding (numpy): −273.15 → −273.25, −273.0 → −273.0, 6000.0 → 6000.0. The step-7 row's claim holds.
- Word counts: `fuel_antialiasing.md` 1,123 (budget 1,124); `client_objects.md` 5,176 (budget 5,176). Both within.
- Column scan of every added non-table prose line in the five changed docs.

Not run: Godot, the golden job. The delta-2 folds touch only docs and one Python comment, so no render changed.

## Status (set from the tree)

| Finding | Status | Evidence |
|---|---|---|
| D2-1 | **fixed** | `checklists.md` step 7 (`phase1/protocol`) row: the encoder clips to exactly [−273.0, 6000.0], names −273.15 → −273.25 as refused, and asks for a test against `FuelSnapshot`'s constants. Placed in the right step |
| D2-2 | **fixed** | §4.1: "14.1–14.5 ms before ruling 9's temperature loop (18.7–21.0 ms after, loaded)". No longer false. The only after-figure is a loaded one (D3-3) |
| D2-3 | **fixed** in the per-frame sentence | §3.2 line 122–123: `surface_temperature_c` held to §3.3's clip (ruling 9), every frame. The refusal list still has no bullet for it (D3-4, NIT) |
| D2-4 | **fixed** where it mattered; residue in two places (D3-1) | Step 8's Remaining carries 39%, 10%, 16–22%, "a geometry model, not a render". Ruling 7 names both effects, "from a model", and points to step 8. §4.2: "unless rods touch (ruling 7)". Not done: the research note's N-1 sentence and the fringe shader header, both named in D2-4's fix direction |
| D2-5 | **fixed** in the design | §2 row "(two rod passes)"; §7.4 "the rod passes". `fuel_rod.gdshaderinc` line 1 still says "the rod's two passes" (D3-2) |
| D2-6 | **fixed** | `client_objects.md:187–188` and `fuel_antialiasing.md:97–99` wrap at ≤120. No new prose line from these folds is over 120 |
| ET-N1 | **fixed** as asked (cause marked unmeasured) | `FADE_SHARE`'s comment: "probably the hot stick's bloom; not separated by measurement". The note: "probably from bloom" |
| N-3 | **open** (NIT), see D3-5 | The competing cause (core saturation) is not recorded, and the tree's own deletion number argues against bloom |
| N-5 | **deferred** to step 8 | Step 8's Remaining: "fade over fade in instance order (N-5, at most 0.25 of the colour difference)". Trigger: step 8's own work. §4.2 and ruling 7 still say "in any order" / "at any … instance order" without excluding it (NIT, folded into D3-1's fix) |
| P-N3 | **deferred**, trigger now findable | Step 8's Remaining: "1.7 s a run; when the golden job's time gets a B5 row" |

No BLOCKER is open. No SHOULD-FIX is open.

## New findings from the folds

### D3-1 NIT: the N-1 record is still one-effect in the two places a step-8 author reads first

`docs/design/research/fuel_antialiasing.md` lines 97–99 ("near a contact depth hides part of the front fade");
`client/addons/engine/render/fuel_rod_fringe.gdshader` header lines 5–6 (same wording).

- **Defect.** D2-4 asked that both name both effects. The fold fixed ruling 7, §4.2 and step 8, not these. The most
  visible effect, the rear fade drawn over the front core, appears in neither. The shader header is the file a
  step-8 author edits to fix touching rods.
- **Failure scenario.** Reading only the shader, the author fixes the depth occlusion of the front fade (for example,
  by shrinking the depth silhouette near contacts) and leaves the rear-fade-over-core artefact, which step 8's
  checklist names but the code comment doesn't.
- **Fix direction (unverified).** In the header: "…hides part of the front fade, and the rear fade draws over the
  front core (numbers: checklists.md step 8)". In the note, a pointer to step 8 rather than numbers, to stay inside
  the 1,124-word budget. Separately, add "(fade over fade excepted, N-5)" to §4.2's "in any order" or ruling 7's
  "instance order". That keeps N-5's own reason for being recorded: "whatever the order" shouldn't read as covering it.

### D3-2 NIT: `fuel_rod.gdshaderinc` still says "the rod's two passes"

`client/addons/engine/render/fuel_rod.gdshaderinc` line 1 ("what the rod's two passes share") and line 8 ("Two
passes, because…"). The rod draws three (`fuel_pass.gd::_init`: `rod` → `rod_core` → `rod_fade`). The branch edited
lines 11–14 of the same comment for ruling 7. Line 8 still holds as "depth vs colour", but line 1 is a count, and it is
wrong. This is D2-5's defect class, in code. A one-word swap ("three passes", or "the depth and colour passes").

### D3-3 NIT: §4.1's only post-ruling-9 insertion figure was measured under load

`docs/design/client_objects.md` §4.1, line 188: "(18.7–21.0 ms after, loaded)".

- **Defect.** Every other number in the bullet was measured unloaded. D2-2 estimated the unloaded insertion at about
  15.6–16.3 ms (base plus the loop). The label is honest, so the text is not false. But the shipped path's insertion
  now has no unloaded figure, and B5's fuel row reads §4.1 as its source.
- **Failure scenario.** B5's first unloaded run measures about 16 ms. Against 18.7–21.0 it reads as a 15–25%
  improvement, which hides a real regression of up to that size in the same commit.
- **Fix direction (unverified).** Rerun `tools/fuel_aa/rebuild_time.gd` unloaded and swap the number in, or record it
  as B5's to measure. Either can wait for B5's fuel row, so it is deferrable with that trigger.

### D3-4 NIT: §3.2's refusal list still doesn't list the temperature refusal

`client_objects.md` §3.2, lines 123–129. The per-frame sentence now holds `surface_temperature_c` to the clip, but the
list that follows ("The decoder refuses on any of these:") is structural only. NaN and ±∞ are implied by "the clip",
never stated. Step 7's row ("Decode and stage-1 rejection fixtures") plus the new D2-1 clause make a missing fixture
unlikely, so this is a NIT. It is the second half of D2-3's fix direction. A bullet would cost about 12 words, and the
design has 0 to spare, so the bullet needs an equal cut elsewhere.

### D3-5 NIT (N-3, ET-N1's second half): "probably bloom" is contradicted by the record's own deletion number

`scripts/golden_fuel.py::FADE_SHARE` comment (line 285); `research/fuel_antialiasing.md` line 89.

- **Defect.** With the fade pass deleted, the hot core still blooms, and the band's share is 0.021. So bloom from the
  core accounts for about 0.02 of the 0.396, not the roughly 0.25 excess over the model's 1/7. The fade's own
  emission is too dim to bloom much. Core saturation compressing `core_gain` (N-3's hypothesis) fits the numbers
  better, and the record doesn't mention it. Neither cause was measured. "Probably" isn't false, but the tree's own
  data argues against the cause it prefers.
- **Failure scenario.** Step 8's fresh laptop derivation (laptop has bloom off) assumes the rig's excess is bloom and
  expects laptop's intact share near the model. It is not (0.258, with the upscale smear), and the author attributes
  the gap to the wrong mechanism. The bar is a floor either way, so no check is weakened.
- **Fix direction (unverified).** "Above the model; cause unmeasured: core saturation or bloom. Bloom from the core
  alone adds 0.021 (deletion)." That is a swap of about the same word count.

## Checked and fine

- D2-1's clause is in step 7 (`phase1/protocol`), not step 8. Its f16 claims are exact (above).
- §3.2's wording matches the code: `frame_problems` runs `_temperature_problems` every frame.
- B5's fuel clauses name the insertion, the steady frame, frame time and "the rods' third pass … GPU cost unmeasured".
- §9 moving to `owner_rulings.md` keeps the ruling numbers that code and docs cite ("owner ruling 3"). Ruling 7's
  rewording is the author's record of an owner ruling, so the owner may want to see it.
- The P-N3 trigger names a real future event (B5's golden-job row).
- `owner_rulings.md` has one 122-column line (ruling 6, "clamp deleted, +∞ °C…"). It comes from an earlier fold,
  outside this round's scope, and is noted only for completeness.

## Summary

| Id | Severity / status | One line |
|---|---|---|
| D2-1, D2-2, D2-5, D2-6, ET-N1 | fixed | Encoder clip in step 7; insertion figure true; pass counts in the design; wraps |
| D2-3 | fixed (sentence) | Refusal list bullet missing (D3-4) |
| D2-4 | fixed (ruling 7, §4.2, step 8) | Note and shader header still one-effect (D3-1) |
| N-5, P-N3 | deferred to step 8 | Both in step 8's Remaining. P-N3's trigger is B5's golden-job row |
| N-3 | open (NIT) | See D3-5 |
| D3-1 | NIT | Shader header and research note name only the fade loss for touching rods |
| D3-2 | NIT | `fuel_rod.gdshaderinc:1` "two passes"; the rod draws three |
| D3-3 | NIT | The only post-loop insertion figure is loaded (18.7–21.0 ms) |
| D3-4 | NIT | §3.2's refusal list lacks the temperature/NaN refusal |
| D3-5 | NIT | "Probably bloom" against a 0.021 deletion residual. Saturation is unrecorded |

These are paper rounds on wording. Every new finding is a NIT. Under the charter's stop rule, round 4 isn't warranted
unless code changes.
