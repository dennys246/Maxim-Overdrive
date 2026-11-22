# Wire integrity, delta round 2: `docs/design/torch_pilot.md` (working tree over fcc6e55)

**Lint state.** I ran `.venv/bin/python scripts/lint_standards.py` read-only. It printed `PASS (0 finding(s)); rules enforced by a check: 21, held only by review (backlog): 27`. The `pilot.fields` marker matches §2's table. Its count went from 4 to 5, and the justification for the new count is wrong (W2-S1).

A caveat that applies to the whole status table: §10's cross-document edits wait on Q9. So the tree still holds the old copies of the contracts this design now owns:
- tile §3.2's target sentence ("two candidates is `ambiguous_point`"), its `max_power_w` / `min_radius_m` 0.2, and its P × 0.1 s deposit;
- fire_model §5.4's flame-object pilot;
- checklist 5b's "removed by step 6's skin".

I mark a finding fixed when the design text is right and §10 names the edit. Until Q9's edits land, CLAUDE.md's rule that a contract has one owner is broken across the tree.

## Contract table (contracts the fold changed)

| Contract | Owner | Producers → consumers | State after the fold |
|---|---|---|---|
| `pilot.fields` | §2 | applier stage 2 → solid law, save (step 9), digest, wire row, `Simulation` removal | `target` u8 has a different meaning from `intent_record.target` (W2-S1). `face` covers boxes only (W2-S3). Digest position not defined (W2-S2) |
| Target rule (whole) | §3 | geometry query → applier, receipt, replay, the sub-cell `strike` | coherent here. Tile §3.2 and fire_model §5.4 stay stale until Q9 |
| Clock expression E_p,t | §5 | solid law → ledger `incident_absorbed`, the solve | matches `SimConfig.tick_us` and `physics_every` (simulation.py:60–61). The script's hold unit conflicts (W2-S4) |
| `actions.yaml` | §10 row → `data/world/` | stage 1 → `ActionLimits`, log header | tree is still v0 `ignite`. "A bump over 5b's v1" implies v2 without saying so. The ceiling's derivation is unchecked (W2-N5) |
| `content/items/torch.yaml` v0 | §10 | item loader (checked against the ceiling at load, gate row) → stage 2, pilot record | consistent |
| Pilots wire row Q5 | tile §2.2 (Q5 proposes) | encoder → GDScript decoder, flame (§8), efference test | the byte count is wrong (W2-N1). No refusal code for the u32 narrowing (W2-N2). Membership is not defined (W2-N6) |
| Exit script | §9.1 (`tests/scenarios/slab_exit.yaml` v0) | step 8 → goldens G1–G5 (step 8 maps them) | hold in seconds versus tile §6.2's `duration_ticks` (W2-S4) |
| Digest member | §2 → sim_core §9 (§10 row) | `Simulation` → replay check, goldens | "empty adds no bytes" contradicts §9's scheme. Its anchor `sources` is deleted by Q6 (W2-S2) |

## Status of round-1 findings (read from the tree)

| Id | Status | Evidence |
|---|---|---|
| W-B1 | fixed | §9.4: no gate is rewritten. Each stays strict until its mechanism is deleted (Q6). Beat 8 carries the burned-fuel meaning, with a deletion proof |
| W-B2 | fixed, except the digest bullet, reopened as W2-S2 | §2: `face` enum, `centre_m` f64 unrounded, `target` kind in place of the sentinel, `region_id`, load refusals; §10 fire_solid §5.5 row; checklist step 9 |
| W-S1 | fixed | §10: `actions.yaml` bump with a refusal test; `torch.yaml` v0; the ceiling checked at item load with a gate row. The version number is implied, not stated (NIT-level) |
| W-S2 | fixed (pending Q5) | §2 no longer restates the row; §10 tile §2.2 row; Q5 adds `seq` |
| W-S3 | fixed (pending Q9) | the preamble and §3 own the rule whole; §10 makes fire_model §5.4 and tile §3.2 links |
| W-S4 | fixed (pending Q9) | §10 `tests/test_act_validation.py` row |
| W-S5 | fixed (pending Q9) | the preamble takes D-S2 for Phase 1; §10 client_objects §7.3 row: "step 8 maps G1–G5" |
| W-S6 | fixed | §3: beyond 50 mm is `not_on_surface`; burnt-out rows are candidates; the receipt names the target, so a fruitless `applied` can be told apart |
| W-S7 | open | §10 covers fire_model §10.2/§12, fire_solid §1.3/§2, the roadmap and tile §3.2. `docs/plans/checklists.md` step 5b line 269 ("removed by step 6's skin") is unchanged and is not in §10's checklist row (steps 6 and 9 only) |
| W-S8 | fixed | checklist step 6, "the format and load refusals, with gate rows"; step 9 save row |
| W-N1 | fixed | §5: lab instrument under `tests/`, not `WorkCounters` |
| W-N2 | fixed | §3: effect value = derived target (kind, object, region) |
| W-N3 | fixed | §9.1: residue share from the store by fire_solid §5.6's definition |
| W-N4 | fixed (pending Q5) | Q5: centre on the row; `end_tick` narrowing by refusal |
| W-N5 | fixed | §9.1: `slab_exit.yaml` v0; cap from §9.2 (but see W2-S4) |
| W-N6 | fixed | §8: aim at the footprint centre if carried, else along the facing |
| W-N7 | fixed | §1: links only |

## Delta findings

### SHOULD-FIX

**W2-S1. `pilot.fields.target` reuses an intent-record field name with a different type and meaning, and `contracts.md` justifies the count with a false claim.**
Location: `torch_pilot.md::§2` and `contracts.md` (the `pilot.fields` (4) rationale).

What is wrong: `boundaries.md` §6.2's `intent_record.fields` defines `target` as "a stable id (a region name or persisted entity id)". It is null for `kindle` (§3 says so). §2's `target` is a u8 kind enum (0 object, 1 cell region). `contracts.md` raises the restates-at count to 5 on the grounds that the pilot record "shares" `target` because it "records its target". It doesn't: the two are different fields that happen to share a name. The raised count also lets one real restatement of a pilot field pass the lint unseen.

Failure scenario: step 9's save loader, or a replay tool, joins pilot records to intent records by shared field names (the stated reason for the shared key). It then compares u8 0/1 against null or a region name and either refuses valid saves or carries the wrong value across.

Kind: contract. Fix, unverified: rename it (`target_kind`) and restore the count to 4 with the three-name rationale.

**W2-S2. The digest member's position is undefined, its "no bytes when empty" claim contradicts sim_core §9's scheme, and its anchors are things Q6 deletes.**
Location: `torch_pilot.md::§2` ("Saved and digested … as an input beside `sources` … an empty table adds no bytes") and "Removed … in the slot where `source_exposure` is cleared".

What is wrong:
- **Position.** sim_core §9 fixes the members in a numbered order. "Beside `sources`" doesn't say whether the new member goes before or after member 2, and the order is part of the hash.
- **"No bytes".** §9 hashes, per member, "its name, its numpy `dtype.str`, its ndim, its shape and its 32-byte member digest". An empty member still contributes all of those. "Adds no bytes" holds only if an empty member is omitted, and §9 has no such rule. fire_solid §5.4's table makes the same claim, so the gap is shared; neither design states the omission rule.
- **Anchors.** Q6 recommends deleting `sources` and `source_exposure` at 5b. That would remove both the digest anchor and the removal slot this section is defined against.

Failure scenario: 6.1b implements §9 as written. Every existing `tick_digest` golden changes on a log with no `kindle`, contradicting "logs without a `kindle` keep their goldens". Alternatively, two builders place the member differently and replay digests diverge.

Kind: contract (digest bytes; sim_core §9's owner edit). Fix, unverified: state a member index independent of `sources`, and add an "omitted when empty" rule to §10's sim_core §9 row, or concede a golden change.

**W2-S3. The `face` enum covers box cell regions only, but a region's authored footprint is a CSG.**
Location: `torch_pilot.md::§2` (cell region "0–5 at −x … +z") and `§3` ("one fixed formula per kind").

What is wrong: world_model §5 (cited wrongly as sim_core §7, see W2-N3) says a region's authored geometry is "its solid primitives minus the air carved into them, held as a small CSG". A point on a carved interior face, or on a union of two primitives, has no `face` value and no distance formula "per kind". The `face` byte is saved, digested and load-refused ("whose `face` isn't in its kind's enum").

Failure scenario: a `kindle` 10 mm from a doorway carved into a wall region. The applier either computes the face of the uncarved box (wrong) or has no value to write. The save then holds a byte that load later refuses, or that a second builder encodes differently.

Kind: contract (saved byte). Fix, unverified: define a cell region's `face` as the primitive and face index of the CSG term, or restrict cell targets to box regions with a refusal code.

**W2-S4. The exit script states its hold in seconds while claiming tile §6.2's form, which carries ticks.**
Location: `torch_pilot.md::§9.1` ("in tile §6.2's form … a hold of D seconds") and `§5` ("Holds are stated in world seconds … converted to ticks by `tick_us`").

What is wrong: tile §3.3's `kindle` and tile §6.2's script rows carry `duration_ticks` (tile line 381: `duration_ticks: D`). §9.2's time study halves `tick_us`. A script in tile §6.2's form keeps D as a tick count, so the hold halves in world seconds. The design names no site where seconds become ticks (script loader? harness?).

Failure scenario: the dt/2 run of the time study holds the torch half as long, lands on the other side of the flash band, and the class disagrees across steps. The disagreement is then read as non-convergence of the solid.

Kind: contract (script format). Fix, unverified: give `slab_exit.yaml` a `hold_s` field converted at script load, and say that this departs from tile §6.2's form.

**W2-S5. The load rule `end_tick ≤ apply_tick` refuses a state the lifecycle can produce.**
Location: `torch_pilot.md::§2`, "Cut short … on `region_gone` … sets `end_tick` to the ending event's tick, in that tick's step 1" against "Load refuses a record whose `end_tick` ≤ `apply_tick`".

What is wrong: a cell region destroyed in the same tick τ the `kindle` applied gives `end_tick` = τ = `apply_tick`. Destruction comes from physics (step 6) or a topology batch, not step 1, so "that tick's step 1" has already passed. The record stays present until removal, so a save at τ writes a record that load refuses.

Failure scenario: a save taken at the tick a kindled wall region is destroyed fails to load on every machine.

Kind: the load rule is contract. When `region_gone` is observed and the cut applied is mechanism: test it in 6.1b's lifecycle cases ("`end_tick` on and off a physics tick"), adding the same-tick destruction case.

### NIT

**W2-N1.** `§11 Q5`: 10 B + `object_id` 4 + centre 3 × i32 12 + `seq` 4 = 30 B, not "32 B against 10". Kind: contract (wire budget, step 7). Verified by arithmetic from tile §2.2's dtypes.

**W2-N2.** `§11 Q5`: "`end_tick` narrows to u32 by refusal past 2³² − 1" names no refusal code. `refusal.codes` (tile line 246) has none for it, and the codes are append-only and digested. Kind: contract.

**W2-N3.** `§3` cites "`sim_core.md` §7: '`Region` keeps its authored footprint'". The quote lives in `world_model.md` §5 (line 126) and `world_v2.md`, not sim_core. Verified with grep. Kind: link hygiene.

**W2-N4.** `§9.2` names two steps ("`tick_us` and `tick_us`/2") but its convergence test |t(dt/2) − t(dt/4)| ≤ |t(dt) − t(dt/2)| needs three. Kind: mechanism, for 6.1b's band test.

**W2-N5.** `§6`: the ceiling is "min over shipped recipes of ε_r · 50 kW/m²", but it ships as a number in `actions.yaml`. No check holds the two equal when a recipe is added. Kind: mechanism, for a 6.1b test that recomputes the ceiling from the committed recipe set.

**W2-N6.** `§2` lets an ended record stay present until removal, so a second `kindle` "at `end_tick`" can make two records exist for one actor. Nobody says whether the wire's pilots table lists present or live records, and §8's flame draws "while a pilots row is live". Kind: contract (wire table membership, step 7).

## Counts

Statuses (17): fixed 16 (of which 1 fixed except one bullet reopened as W2-S2, and 6 pending Q5 or Q9), open 1 (W-S7), deferred 0, rejected 0.

New findings: BLOCKER 0, SHOULD-FIX 5, NIT 6.
- Contract: 8 (W2-S1, W2-S2, W2-S3, W2-S4, W2-N1, W2-N2, W2-N3, W2-N6). W2-S5's load rule is the contract part of a split finding.
- Mechanism: 2 (W2-N4 and W2-N5, both to 6.1b). W2-S5's timing goes to 6.1b's lifecycle cases.
