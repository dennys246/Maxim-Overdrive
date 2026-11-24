## Wire integrity: fold status of round 2 at 94e85fe (read from the tree, not from fold2.md)

I ran `.venv/bin/python scripts/lint_standards.py` read-only. It printed `PASS (0 finding(s)); rules enforced by a check: 21, held only by review (backlog): 27`. I wrote nothing in the tree.

### Status table

| Id | Status | Evidence |
|---|---|---|
| W-S7 | fixed | `docs/plans/checklists.md` step 5b, line 269, now reads "removed by 6.1b. The four `ignite` red gates' precondition moves to it here (`torch_pilot.md` §9.4)". The text "step 6's skin" is gone from every document in scope (grep). |
| W2-S1 | fixed | §2's marker and table now say `target_kind` (u8), so the name no longer collides with `intent_record.target`. `contracts.md` sets `pilot.fields` to restate at 6, and its rationale is now true: tile §2.2's pilots row shares 5 names (`actor_id`, `seq`, `region_id`, `object_id`, `end_tick`) and the intent record shares 3. fold2 says the count went "back to 4"; it did at 8a912ba, then 94e85fe raised it to 6 with this rationale. Note that threshold 6 of 11 members means any copy of 5 pilot fields passes the lint unseen. That trade is stated and justified, so it is not a defect. |
| W2-S2 | fixed, with a residue (W3-S1) | §2: "at a position sim_core's edit assigns. An empty member still hashes its name, dtype and shape … a recorded break under `sim_core.md` §12". sim_core §9 now lists "6. pilots (`torch_pilot.md` §2)", so the position is defined and the "no bytes" claim is gone. The anchor is no longer `sources`. But sim_core §9 still holds `sources` and `source_exposure` as members 2 and 3, which TP6 deletes at 6.1b (W3-S1). |
| W2-S3 | fixed | §2's face enum gives 255 to a cell region, which takes no deposit (§4.1). §3 measures a cell region "by its authored solid primitives, minus carved air once world_model §5's CSG lands", never by cells or by `footprint_of`'s box. The load refusal ("face isn't in its kind's enum") now has a value for every kind. |
| W2-S4 | fixed | §9.1: `slab_exit.yaml` "departs from tile §6.2's form in one way: apply times and holds are in seconds (`hold_s`), which its loader converts to ticks by `tick_us`". §5 names the loader as the place where seconds become ticks. The rounding rule from seconds to ticks is not stated, but §9.2's margin of one coarsest tick on D absorbs it, so it is not a contract defect. |
| W2-S5 | fixed | §2: only `leave` cuts a pilot; `region_gone` no longer does. Tile §3.2's lifecycle reads "ends on expiry or on leave". A `kindle` and a `leave` in the same tick give end = apply. That record is removed "at the cut itself when every covered tick has already been integrated", which is vacuously true when it covers no ticks, so the load refusal can't meet it. The 6.1b lifecycle cases in the checklist do not list this same-tick case. That is a test to add, not a contract defect. |
| W2-N1 | fixed | Tile §2.2: 4+4+2+4+12+4 = 30 B, "30 B each" (TP5). |
| W2-N2 | open | The record's `end_tick` is u64 (§2), and tile §2.2's wire column is u32. No document states the narrowing rule or its refusal code: `refusal.codes` (tile line 243) is unchanged, and neither checklist step 7 nor tile §2.2 mentions it. fold2's "step 7's freeze to name" exists only in fold2, and the old Q5 sentence went with §11. This is a contract finding, so the author can't defer it. TP5's "frozen in step 7" freezes the columns, not this rule. |
| W2-N3 | fixed | §3 cites "world_model §5's CSG". sim_core §7 is no longer cited for the footprint. |
| W2-N4 | fixed | §9.2 runs three steps, "`tick_us`, ½ and ¼ (0.5, 0.25 and 0.125 s steps)", with the three-step test. |
| W2-N5 | deferred, to 6.1b (mechanism: a test that the shipped number equals its formula) | §6 Basis: "a 6.1b test holds `actions.yaml`'s number to it". Checklist 6.1b, lines 304–305: "`actions.yaml`'s ceiling equal to §6's formula over the committed sets". |
| W2-N6 | open (half fixed) | The live rule is fixed: §2 defines live by interval, "at most one live", and load refuses two live records. Wire membership is still unstated: tile §2.2 says only "showing `torch_pilot.md` §2's records". Records stay present after `end_tick` until removal, but §8 draws the flame "while a pilots row is live". So nothing says whether an ended-but-present record is a row, and the client can't tell without reading `end_tick` against the frame tick. Either is fine, but tile §2.2 must state which, before step 7 freezes the format. |

### New contract findings (from the ruling commit's cross-document edits)

**W3-S1 (SHOULD-FIX). TP6 deletes `sources`, `source_exposure` and `HeatSource` at 6.1b, but their owner, sim_core, still holds them as live contract, and §10 doesn't list the edit.**
- **Where:** `torch_pilot.md` §9.4 and TP6 say that at 6.1b "the sphere deposit … goes, and with it `HeatSource`, `sources` and `_power_field`". Their owner text is unchanged:
  - sim_core §1's table (line 29) lists `sources` and `source_exposure` as cell state;
  - sim_core §3 (line 64) makes `source_exposure` an input;
  - sim_core §6 (line 168) declares both inputs, with heat as their resolver;
  - sim_core §9 (lines 225–226) makes them digest members 2 and 3;
  - the code registry has `fields.py::InputSpec("sources", …)`;
  - checklist 5a PR 4 (line 234) adds `source_exposure` as member 3.
- **§10's gap:** its sim_core row says only "the pilot input and its resolver; its digest member". The 6.1b checklist names no such deletion.
- **What else loses its subject:** passing tests that drive heat sources, not only the four red gates. `tests/test_cross_tier.py` lines 44, 76, 117 and 147, and `tests/test_determinism.py` lines 48 and 67, run fire through `ignite`. The same goes for the closed-form tests in `test_exposure.py` and `test_deposit.py`. Nothing names their fate. The cross-tier and closed-form heat-source tests are the patterns CLAUDE.md cites.
- **Failure scenario:** 6.1b's builder reads sim_core §9, still with 6 members including `sources`, against torch_pilot §9.4, which deletes it. Two documents now own the digest's membership and the input set. Either `sources` is kept as a dead, always-empty member, and the "recorded break" in §2 understates what changes. Or it is deleted with no owner edit, and every tick-digest golden and save-v0 layout breaks a second time, unrecorded.
- **Fix (unverified):** add sim_core §1/§3/§6/§9's retirement of `sources` and `source_exposure` to §10's sim_core row, and make it one break at 6.1b. Add to the 6.1b checklist the deletion, or the rehoming, of the cross-tier, determinism and closed-form heat-source tests.

**W3-N1 (NIT). `client_objects.md` line 45 still names `fire_model.md` §5.4 as the source of "`kindle`'s 50 mm nearest-surface rule and `ambiguous_point`".** fire_model §5.4 now only links to `torch_pilot.md` §3, so a reader is sent to a stale owner. The lint can't catch this: it is a row naming a source, not a copy. Link hygiene: point the row at `torch_pilot.md` §3.

**W3-N2 (NIT). Tile §2.2's `centre_mm` (3 × i32) has no rule for converting from the record's f64 `centre_m`** (round, truncate, or the general display quantization in `encoding.py`). It is visual only (§8), but the wire's golden fixtures freeze its bytes at step 7. Fold it with W2-N2's narrowing rule into one encoding sentence in tile §2.2.

### Other checks, clean
- **Tile §3.2:**
  - the target sentence, the deposit "P × 0.1 s" and "when its region is gone" are gone;
  - `max_power_w` and the 0.2 m floor are scoped to the "sphere-era" v1, with 6.1b's fields linked to §6;
  - the red-gate sentence links §9.4.
- **The intent.kinds marker:** its new `not: … torch_pilot.md` matches the span added to the block, and the lint passes.
- **fire_solid:**
  - §2 excepts `kindle` (TP1);
  - §4.4 moves q''_fl into the solid law (TP2), which matches §9.4's "apply q''_fl" control;
  - §5.4 adds the torch as a supplier of `incident_absorbed`;
  - §5.5 adds pilots to the save list;
  - §7's D-S2 row links §9.
- **fire_model:** §5.4 links the target rule and puts the flame-object pilot in Phase 2; §10.2 is updated.
- **Grep for stale copies:** `max_power_w`, "two candidates", "P × 0.1", "region is gone", "rewritten to use" and "step 6's skin" each appear only where they are scoped or retired. Tile §6's 15.9 kW/m² is the Phase 2 crate's.

### Counts
- **Statuses (13):** fixed 9 (W-S7, W2-S1, W2-S2 with its residue, W2-S3, W2-S4, W2-S5, W2-N1, W2-N3, W2-N4), deferred 1 (W2-N5, to 6.1b), rejected 0, open 3 (W2-N2, W2-N6, and W2-S2's residue as W3-S1). Counted by Id: fixed 10, deferred 1, open 2.
- **New findings:** BLOCKER 0, SHOULD-FIX 1 (W3-S1), NIT 2 (W3-N1, W3-N2).
- **What this means for the hand-off:** W2-N2 and W2-N6 are contract items that fold2 claims fixed or deferred. They are not fixed in the tree.
