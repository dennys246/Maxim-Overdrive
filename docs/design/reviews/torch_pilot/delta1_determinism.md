# Determinism and replay, delta round 2 (torch_pilot.md, working tree over fcc6e55)

What I read: `git diff fcc6e55 -- docs/`, all of the folded torch_pilot.md, fold1.md's D rows, the step 6 and step 9 checklist diffs, and contracts.md. I checked them against these sources at the tree: sim_core §3 (clock, `source_exposure`), §8 (`substep_refine`), §9 (digest framing), §11 bar 2b; tile §2.2, §2.3, §3.2, §6.2; fire_solid §4.3 and the §6 rows; `src/simcore/core/simulation.py::SimConfig`. I also checked that no digest code exists yet (`simulation.py:20`: digest and save "come with the log (PR 4)"), and that no `kindle` code or replay golden exists in src/ or tests/. I ran nothing beyond grep and reading. Every proposed fix below is unverified.

## 1. Status table (round 1, determinism)

| Id | Status | Evidence |
|---|---|---|
| D-B1 | **open** (narrowed) | §2 "The lifecycle, in tick order" fixes scenarios 1, 2, 3 and 5: live by interval, a cut sets `end_tick` in step 1, removal comes after the covering physics step in the `source_exposure` clear slot, and fuel objects are never `region_gone`. Scenario 4 stays open for **cell targets**: "the applier sets `end_tick` … in that tick's step 1" has no meaning for a region destroyed in step 6 (physics), and no intent carries that event to the applier. The new removal rule also has a hole (D2-S1). |
| D-S1 | fixed | §2 adds "a new member" of sim_core §9, and §10 gives sim_core §6, §9 rows (appender, remover, resolver, digest member); step 9 has the save row. The "empty adds no bytes" claim the fold added is wrong; see D2-S2. |
| D-S2 | fixed | §2 `centre_m` is 3 × f64; §3 "Distances": f64, one formula per kind, nearest point unrounded. No integer field is left to round. |
| D-S3 | fixed | §3 "Faces" gives a precedence rule (segmented face first, else the lowest `face`), and the checklist has edge and corner cases. The rule breaks `centre_m`; see D2-S3. |
| D-S4 | fixed | §5 writes E_p,t in `tick_us` and `physics_every` as one named expression that the ledger books, with the solve deriving its flux from it. The substep question goes away because the solid runs once per physics step (fire_solid §4.3) and the study halves `tick_us`. That choice brings new contract defects (D2-B1). |
| D-S5 | fixed | §4.3: per pilot, scalar `math`, one call shape at apply and on load, a cache keyed by record values and evicted on removal and rollback. §9.3 runs with a second pilot. |
| D-S6 | fixed | §4.2: "pilots in key order, then the flame flux". The convective-off share is gone (losses stay on). Checklist: two pilots, both orders. |
| D-S7 | fixed | §3 Candidates: "as of the start of stage 2 (`pending` is excluded …)". Checklist case present. |
| D-N1 | **open** | fold1 says "a log break is a recorded change under sim_core §12 (not restated)". Nothing in torch_pilot.md links sim_core §12, and §10 has no sim_core §12 row: grep finds no `sim_core.md` §12 in the file. §0.2 speaks only of saved records. Linking is not restating. One line in §10 or §0.2 would close it. |
| D-N2 | fixed | checklists.md step 9: "The pilot records (`torch_pilot.md` §2): load refusals, a round trip at a mid-pilot tick, and a golden." |

## 2. Delta findings

**D2-B1. The time study's "halve `tick_us`" contradicts the formats it depends on: `duration_ticks`, scripts keyed on apply ticks, and per-tick movement.**
`docs/design/torch_pilot.md::§5` ("Holds are stated in world seconds … the time study halves `tick_us` at a fixed `physics_every`, and every input's schedule refines with it"), `§9.2` ("at `tick_us` and `tick_us`/2"). **Contract defect.** These are what the claim runs into:
- the wire's and the log's `kindle` field is `duration_ticks` (tile §3.2 table, line 228);
- tile §6.2's scenario form is "a versioned script of inputs at apply ticks";
- tile §2.3 states walk speed as 140 mm per tick;
- sim_core §3 calls `tick_us` a truth constant, T3's, hashed into the log header;
- sim_core §8 and §11 bar 2b refine time through `substep_refine`, which fire_solid §4.3 says doesn't reach the solid ("independent of … heat's substeps").

So no input schedule "refines with it" unless something converts it, and §10 routes no edit to tile §3.2, tile §6.2, or sim_core §3, §8 and §11.

Failure scenario: `slab_exit.yaml` holds `apply_tick: 10, duration_ticks: 50`. At `tick_us`/2, the logged record is identical, so the kindle lands at world 0.5 s instead of 1.0 s and holds 2.5 s instead of 5 s. t_flash then moves by the input change rather than the scheme's error. §9.2's |t(dt) − t(dt/2)| measures the script, and the margin rule ("D lies above the band's highest upper edge by that spread") is set from a spurious spread.

There is a second problem in the same text: §9.2 lists runs at `tick_us` and `tick_us`/2 only, yet its convergence test needs t(dt/4) too. fire_solid §6 runs dt, dt/2 and dt/4. The gate's run set is undefined as written, and the step 6 checklist dropped "two steps" altogether.

Proposed fix (unverified): one owner states how time is refined for the solid: a `SimConfig` knob, or `tick_us` with a rule that converts the script and `duration_ticks` from seconds. §10 routes the owner's edit, and §9.2 lists all three steps.

**D2-S1. "Removed after the first physics step whose interval holds `end_tick` − 1" never fires for a cut whose last covered tick was already integrated.**
`§2` lifecycle, "Removed". Contract: it decides which records sit in the digest and the save.

Failure scenario: apply at 70, `leave` at L = 121, so `end_tick` = 121 and `end_tick` − 1 = 120. The physics step at tick 120 (interval (115, 120]) ran in tick 120's step 6, before the cut. Read literally, the condition "the current interval holds `end_tick` − 1" fails at tick 125 and at every later step, so the record is never removed. This hits every cut with L ≡ 1 (mod `physics_every`), and every cut with L ≤ the last completed physics tick, such as a `region_gone` processed late.

Consequences:
- The record lingers in the digest and the save forever.
- If the wire's pilots table is built from the records present, it shows a dead pilot.
- Load accepts it, because the refusal is "two *live* records".
- An implementation that reads the rule as "the first physics step at a tick ≥ `end_tick` − 1" removes it at 125. The two readings give different digests from tick 125 on.

The checklist's lifecycle cases ("`end_tick` on and off a physics tick, `leave` mid-interval") don't name this phase.

Proposed fix (unverified): "removed in the clear slot of the first physics step at tick ≥ `end_tick` − 1, or at once when `end_tick` − 1 ≤ the last completed physics tick". Add L ≡ 1 (mod 5) to the 6.1b lifecycle tests.

**D2-S2. "An empty table adds no bytes, so logs without a `kindle` keep their goldens" is false under sim_core §9's framing.**
`§2` "Saved and digested". **Contract defect** in the digest, which sim_core owns.
- sim_core §9 writes, for every member, its name, `dtype.str`, ndim, shape and 32-byte member digest into the tick digest. That holds for an empty member too; `source_exposure`'s empty segments are still a member.
- Adding a `pilots` member therefore changes every tick digest, and §9 has no "omit when empty" rule.
- torch_pilot doesn't own §9, and §10's sim_core §9 row says only "its digest member".

Failure scenario: a golden recorded at 6.1 is replayed at 6.1b with no `kindle`. Every tick digest differs. Either the golden is regenerated with no recorded break, which sim_core §12 forbids, or the builder adds an omit-when-empty special case to make this sentence true. That case would then apply to no other member.

Proposed fix (unverified): delete the claim and route a sim_core §12 recorded break at 6.1b (this also closes D-N1). Or have sim_core §9 adopt an omit-empty rule for all members, as its own edit.

**D2-S3. The face precedence makes `centre_m` lie off the chosen face's plane, and the design doesn't say which point is saved.**
`§3` "Faces" against "The nearest point becomes `centre_m` unrounded", and `§4.1` ("centred on `centre_m`, in the plane of the target's `face`"). **Contract defect:** `centre_m` is saved and digested, it is Q5's wire centre, and the overlap reads it.

Failure scenario: a slab with its top at z = h and a side at x = 0, and a point at (−0.5 mm, y, h − 0.5 mm).
- The nearest point is on the side face, at (0, y, h − 0.5 mm), 0.5 mm away.
- The top face is 0.707 mm away, within 1 mm, so `face` becomes 0 (top).
- `centre_m` is then a point 0.5 mm below the plane the disc lies in.
- One implementation saves the global nearest point and projects it in the overlap. Another saves the nearest point on the resolved face, (0, y, h).
- The two save different bytes. A rebuild across a refactor changes the digest.

"Within 1 mm of each other" is also pairwise, and so non-transitive: A–B and B–C within 1 mm while A–C are not. The rule should read "within 1 mm of the minimum". It uses "within" here and "under 1 mm" for candidates, which disagree at exactly 1 mm (D2-N1).

Proposed fix (unverified): "`centre_m` is the nearest point on the resolved face", stated once.

Mechanism note for 6.1b: §9.4's "ignore `face`" control must kindle a side point more than 1 mm from the top edge. Otherwise the precedence lights it legitimately, and the control is red for the wrong reason.

**D2-S4. The overlap cache's key leaves out geometry it reads.**
`§4.3` "A cache keyed by the record's values". sim_core §7 requires a key over the values a cache reads. The overlap also reads the object's authored geometry and its segment layout (strip ℓ, rod band). For a cell target it reads the region's footprint, keyed only through `region_id`. Today 6.1 never edits object geometry after acceptance, so on the shipped path this is latent. **Mechanism.**

Failure scenario: the sub-cell design (§3, "objects of every role join") or a 6.2 remesh changes a row's segments while a pilot is live. A cache hit serves stale A_ov, and a load rebuild computes the new one, so the running digest and the rebuild diverge.

6.1b test: build with the object's geometry digest in the key, or assert that object geometry is immutable while it is referenced.

**D2-S5. A `region_gone` cut on a cell target has no tick-order site.** (This is D-B1's residue, kept under D-B1 and not counted twice.)

**D2-N1.** §3 uses "under 1 mm" for candidates and "within 1 mm" for faces, so the two disagree at exactly 1.000 mm. On one machine this is deterministic, but it is an f64 equality on the boundary. **Contract**, cosmetic.

**D2-N2.** The step 6 checklist dropped round 1's "a save at a mid-pilot tick … bit-identical" from 6.1b and moved it to step 9. That's acceptable, because §2 says the 6.1b stand-in is the rebuild-from-tables digest. But the D-B1 phase cases (a save between `end_tick` and removal, and a save at L ≡ 1 mod 5) are named nowhere. **Mechanism**: step 9's round trip should carry them.

## Counts

Statuses: fixed 7 (D-S1 through D-S7, D-N2 is 7 with D-S1..D-S7 minus none; listed: D-S1, D-S2, D-S3, D-S4, D-S5, D-S6, D-S7, D-N2 = 8), open 2 (D-B1 narrowed to cell-target `region_gone`; D-N1), deferred 0, rejected 0. **Totals: 8 fixed, 2 open.**

New findings: 1 BLOCKER (D2-B1), 4 SHOULD-FIX (D2-S1, D2-S2, D2-S3, D2-S4; D2-S5 is D-B1's residue and not counted), 2 NIT (D2-N1, D2-N2).

By kind: contract 5 (D2-B1, D2-S1, D2-S2, D2-S3, D2-N1); mechanism 2 (D2-S4, which goes to 6.1b; D2-N2, which goes to step 9).

The charter's stopping condition applies: this second paper round found a new contract blocker (D2-B1) in text the fold added. Contract blockers still fold or the owner overrules them. Only D2-S4 and D2-N2 may move to build steps.
