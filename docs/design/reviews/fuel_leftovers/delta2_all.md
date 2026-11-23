# Delta round 2, all lenses: phase1/fuel-leftovers (uncommitted, against 2586ed7)

Reviewer: Executor, Architecture, Wire integrity, Client rendering, Trust boundary, Performance (delta 2). Scope:
delta round 1's findings (AW-D*, ET-*, N-*, P-N3) and the "Delta round 1 folds" section of `fold.md`.

Ran:
- `.venv/bin/pytest -q -p no:cacheprovider tests/test_golden_fuel.py tests/test_fuel_fixtures.py`: 57 passed.
- `scripts/fuel_fixtures.py --check`: rc 0.
- `scripts/godot_check.py`, once: `godot_check: PASS`. This covers ET-N3's GDScript test.
- Mutation of ET-S1's guard, done with a pytest plugin in the scratchpad, worktree untouched. The plugin patches
  `golden_fuel._mean_y` after collection:
  - replaced by `_mean_l`: `test_the_fade_is_judged_in_linear_light` fails (1 failed, 32 passed)
  - replaced by luminance of unlinearised sRGB: the same test fails
- Checked the f16 bits in ET-N3's test by hand: 0x6DDD is 6,004 and 0xDC45 is −273.25.
- Word counts: `fuel_antialiasing.md` 1,124 (base 1,124); `client_objects.md` 5,166 (base 5,176). Both are within
  budget.
- Character-width scan of lines that are new against base.

Not run: the golden job (Docker). AW-D4's "second run passed" can't be verified from the tree.

## Status of delta round 1's findings (set from the tree)

| Finding | Status | Evidence |
|---|---|---|
| AW-D1 | **fixed in part**; the rest open as D2-1 | `fuel_fixtures.TEMPERATURE_CLIP_C` is the stand-in producer's copy. `test_every_fixture_temperature_is_inside_the_clip_and_the_clip_is_the_clients` holds each fixture inside it, both ends exact in f16, and both GDScript copies equal to it. `FuelSnapshot`'s comment is now true ("must apply; … not yet built"). Not done: the test the fix asked to name at the encoder's step. Step 7's checklist row (`checklists.md` "the fuel tables and fuel view") doesn't carry it, and §3.3's literal "[−273, 6000]" is a fourth copy that nothing reads |
| AW-D2 | **fixed** for the steady frame and the docstring; the insertion figure in the same bullet is stale (D2-2) | §4.1 says 1.80–1.83 ms, nearly all the loop, and 0.10 ms without it. `show_fuel`'s docstring names the loop and about 1.8 ms |
| AW-D3 | **fixed** | The checklist and `test_the_fade_is_not_judged_on_laptop`'s comment cite 0.258 against 0.233, matching the research note's table |
| AW-D4 | **fixed** (the record agrees; the run itself is unverifiable here) | `fold.md` line 31 and the research note both say a second run passed (27 shots, 6 goldens, cut-away, stick stability) |
| AW-D5 | **deferred** for the cost: B5's fuel row now names "the rods' third pass … its GPU cost unmeasured", triggered with B5's client rows. **Open** for the wording: §7.4 still says "both rod passes" (D2-5) | — |
| AW-D6 | **fixed** | The 179-column line is rewrapped. A new 122-column line appeared (D2-6) |
| ET-S1 | **fixed**, verified by deletion | `test_the_fade_is_judged_in_linear_light` turns red under both the L* swap and the unlinearised-sRGB swap. Arithmetic checked: (0.0452 − 0.0130) / (0.716 − 0.0130) = 0.046 |
| ET-N1 | **open** (NIT) | The fix asked that the suspected cause be marked unmeasured. `FADE_SHARE`'s comment says "the hot stick's bloom adds to the band", and the research note says "bloom puts the measured share above the model", both as fact. Only `fold.md` says "inferred, not separated by measurement". N-3 offered a competing cause (HDR saturation) that the record doesn't mention |
| ET-N2 | **fixed** in the code | `frame_problems`' docstring and the `FRAME_COLUMNS` comment both name the temperature check. The design's copy of the same sentence is still stale (D2-3) |
| ET-N3 | **fixed** | Rows 0, 5 and `rows − 1`, each with all five bit patterns. The Godot step passes |
| N-1 | **deferred** to step 8 for the mechanism and a touching-rod fixture (step 8's Remaining names it). The record of the gap understates it (D2-4) | — |
| N-2 | **fixed** (as AW-D2). Ruling 9 and B5 say "per snapshot (2 Hz)". The insertion residual is D2-2 | — |
| N-3 | **open** (NIT), as ET-N1 | — |
| N-4 | **fixed** | The Shipped row reads "core then fade". The long line is rewrapped |
| N-5 | **open** (NIT; left open by the author) | Nothing in the tree records fade-over-fade in instance order, and `client_objects.md` §4.2's "whatever the order" still reads as covering it |
| N-6 | **deferred** with AW-D5 (B5's fuel row). §2's "+0.24 ms object pass" row still doesn't say which pass configuration it measured (D2-5) | — |
| P-N3 | **deferred**, accepted | The reason holds: about 1.7 s per golden run. The trigger is recorded only in `fold.md`, which the next editor of `golden_stability.py` won't read. A clause in step 8's Remaining would make it findable |

No BLOCKER is open.

## New findings from the folds

### D2-1 SHOULD-FIX: the producer's clip test exists only as a GDScript comment; step 7's checklist doesn't carry it

`docs/plans/checklists.md` step 7 row ("the fuel tables and fuel view (`client_objects.md` §3, …)");
`client/addons/engine/render/fuel_snapshot.gd::TEMPERATURE_MIN_C` comment; `scripts/fuel_fixtures.py::TEMPERATURE_CLIP_C`.

- **Defect.** AW-D1's failure scenario is still reachable, and nothing scheduled guards it. The fold ties the stand-in
  producer, the decoder and the shader together. But the real encoder (step 7) lives in `src/`, which can't import
  `scripts/fuel_fixtures.py`, so none of today's tests can reach it. The only place that says the encoder must clip
  at exactly −273.0 (exact in f16, not −273.15) is a comment in a client file. CLAUDE.md sends a test that only
  running can check to its build step's checklist. Step 7's row lists the fuel tables and the fuel view without it.
  §3.3's "[−273, 6000]" is also read by nothing, so a step-7 author working from the design has no check against it.
- **Failure scenario.** Step 7 writes the encoder from §3.3 and `scene.py`'s absolute zero, clipping at −273.15.
  The client receives −273.25. `_temperature_problems` refuses the frame, and fuel freezes on its last good frame.
  Every test stays green, because the test that ties the copies covers only `scripts/`.
- **Fix direction (unverified).** One clause in step 7's row: the encoder's clip equals the decoder's, both ends exact
  in f16, with a test reading the GDScript constants. Or point that test at §3.3's row.

### D2-2 SHOULD-FIX: §4.1's insertion figure "check included, 14.1–14.5 ms" predates the temperature loop, which an insertion also runs

`docs/design/client_objects.md` §4.1 (line 187); `client/addons/engine/render/fuel_pass.gd::show_fuel`.

- **Defect.** `show_fuel` calls `frame_problems`, and through it `_temperature_problems`, before it compares
  structure. So every insertion pays the 1.5–1.8 ms loop as well. The fold changed the steady figure in this bullet
  and kept the insertion figure, still labelled "check included". N-2 measured the insertion in this tree at
  18.7–21.0 ms under load 9–14 (load inflates it). The base figure plus the measured check gives roughly 15.6–16.3 ms.
  Either way, 14.1–14.5 ms is not this tree's insertion. This is the same kind of defect as AW-D2: a shipped-path
  number in the design that the fold left false.
- **Failure scenario.** B5's fuel row, or step 8's budget work, takes 14.1–14.5 ms as the insertion baseline. Its
  first measurement then reads as an 11% or larger regression that no code change caused.
- **Fix direction (unverified).** Rerun `tools/fuel_aa/rebuild_time.gd` for the insertion, or state it as base plus
  the check. Swapping the number doesn't grow the design.

### D2-3 SHOULD-FIX: §3.2 still says the per-frame check holds only sizes and `state`, and its refusal list has no temperature refusal

`docs/design/client_objects.md` §3.2, lines 119–124 ("Every frame, the other columns are held to their row counts and
`state` to 0 or 1. … The decoder refuses on any of these:").

- **Defect.** This is ET-N2's sentence in the design, which is the contract owner. Ruling 9 added a wire-level
  refusal: a whole frame is refused if any segment is outside [−273, 6000], NaN or ±∞. That refusal is a rule the
  producer depends on. The ruling record says each ruling's effect is stated in the section it names, but ruling 9's
  effect appears in the design only as the "(ruling 9 …)" timing note in §4.1. §3.2's refusal list omits it, and
  §3.2's per-frame sentence contradicts it. §3.3's row says "clipped to" as the producer's duty, not that the client
  refuses.
- **Failure scenario.** Step 7 builds the encoder and its decode-rejection fixtures from §3.2's refusal list (step
  7's row: "Decode and stage-1 rejection fixtures"). It writes no out-of-clip fixture and treats the clip as cosmetic.
  That is D2-1's frozen-fuel case again, reached through the design rather than through the code.
- **Fix direction (unverified).** One clause in §3.2's per-frame sentence and one bullet in the refusal list, both
  citing ruling 9.

### D2-4 SHOULD-FIX: N-1's gap is recorded without its numbers and as "a gap", which misstates it; §4.2 still says "whatever the order"

Owner ruling 7 ("rods that touch keep a gap near the contact"); `fuel_rod_fringe.gdshader` header ("the rear rod's
depth hides part of the front fade"); `research/fuel_antialiasing.md` line 97–98; `checklists.md` step 8 Remaining;
`client_objects.md` §4.2 ("a front fade lands on a rear rod whatever the order").

- **Defect.** N-1's model found three effects for two touching 5 mm sticks:
  - 39–42% of the front stick's fade hidden;
  - 10% of the front core hidden;
  - the rear stick's fade drawn over the front stick's core on 16–22% of samples, deterministically. The fold's
    pass order makes this happen every time; before the fold it happened in half the instance orders.
  The record names only the first effect, gives no number, and in ruling 7 calls it "a gap", which it isn't: no
  pixel goes empty, the wrong rod's colour lands there. The most visible effect, rear fade on front core, isn't
  recorded anywhere outside the review. §4.2, the design's statement of the mechanism, isn't qualified at all.
  CLAUDE.md asks that known gaps carry their numbers. Here the numbers exist and weren't copied.
- **Failure scenario.** Step 8 builds the touching-rod fixture with "hides part of the front fade" as its expected
  defect. It measures fade loss and passes a rear-fade-over-core artefact as noise. Separately, a reader of §4.2
  takes crossings in a kindling pile as solved.
- **Fix direction (unverified).** Copy N-1's table rows, or a one-line summary with its percentages and "from a
  model", into the research note's N-1 sentence and step 8's Remaining. Reword ruling 7's clause and the shader
  header to name both effects (this is the author's record of the ruling, so the owner may want to see the wording).
  Qualify §4.2 with "unless the rods touch".

### D2-5 NIT: §7.4 "both rod passes" and §2's unlabelled "+0.24 ms" still describe the pre-fold rod

`client_objects.md` §7.4 line 379; §2 table, "The object pass at 2,000 instances … +0.24 ms". The rod now draws three
passes (`fuel_pass.gd::_init`: `rod` → `rod_core` → `rod_fade`). B5 owes the cost, but the design's wording is wrong
today. A reader re-measuring frame time "including both rod passes" would configure the wrong pass count. A word
swap fixes it ("all three rod passes"; "measured with two").

### D2-6 NIT: two new lines over 120 columns

- `client_objects.md:187`, 150 characters, from the AW-D2 fold.
- `research/fuel_antialiasing.md:98`, 122 characters, from the N-1 fold.

This is the same pattern as AW-D6 and N-4, reintroduced.

## Checked and fine

- `fade_half` is set only on `rod_fade`, and the priorities 0 → 1 → 2 → 3 are as the fringe header and §4.2 describe.
  The discard `(coverage < 0.5) != fade_half` puts each fragment in exactly one half.
- `frame_problems` still runs before any drawing on both paths. The NaN refusal still holds (`not (t >= lo and t <= hi)`).
- The GDScript test's lambda captures `row` per iteration. Its edge cases (−273.0 and 6,000 at row 5) pass and are
  exact in f16, as the Python test also asserts.
- `test_the_fade_bar_is_half_the_coverage_models_share` checks that 0.5 × (1/8)/(7/8) = 1/14.
- B5's new clauses carry their conditions (headless, editor build, M2, per snapshot at 2 Hz).
- No word budget is exceeded, and no design text was added beyond the swaps.

## Summary

| Id | Severity | One line |
|---|---|---|
| AW-D1 | fixed in part | The stand-in producer, decoder and shader are tied. The encoder's test is unscheduled (D2-1) |
| AW-D2, N-2 | fixed | The steady frame and docstring are true. The insertion is stale (D2-2) |
| AW-D3, AW-D4, AW-D6, ET-S1, ET-N2, ET-N3, N-4 | fixed | ET-S1 proved by two mutations. ET-N3 by the Godot step |
| AW-D5, N-6 | deferred (B5 fuel row) | Wording open (D2-5) |
| N-1 | deferred (step 8 Remaining) | The record understates it (D2-4) |
| P-N3 | deferred | Trigger recorded only in `fold.md` |
| ET-N1, N-3, N-5 | open (NIT) | Bloom stated as fact, unmeasured. Fade over fade unrecorded |
| D2-1 | SHOULD-FIX | The encoder's clip test (−273.0, exact in f16) is only a GDScript comment, not in step 7's checklist |
| D2-2 | SHOULD-FIX | §4.1's "insertion, check included, 14.1–14.5 ms" excludes the temperature loop the insertion now runs |
| D2-3 | SHOULD-FIX | §3.2 says per-frame columns are only size- and state-checked, and its refusal list lacks ruling 9's temperature refusal |
| D2-4 | SHOULD-FIX | N-1's gap is recorded as "a gap", with no numbers. Rear fade over front core goes unrecorded, and §4.2 is unqualified |
| D2-5 | NIT | §7.4 "both rod passes" and §2's +0.24 ms predate the third pass |
| D2-6 | NIT | Two new lines over 120 columns (client_objects:187, fuel_antialiasing:98) |
