# Wire integrity (design form): `docs/design/torch_pilot.md` at fcc6e55

**Lint state.** I ran `scripts/lint_standards.py`, read-only. It reported `PASS (0 finding(s)); rules enforced by a check: 21, held only by review (backlog): 27`. The `pilot.fields` marker matches §2's table. Its restates-at count is 4, justified in `contracts.md` by `boundaries.md` §6.2's three shared names. That count lets tile §2.2's pilots row (which shares `actor_id` and `end_tick`) and any copy of up to three fields pass without the lint seeing them. None of the other contracts below are registered, so review alone holds them.

## Contract table

| Contract | Owner (after) | Producers before → after | Consumers before → after | What each consumer gets, before → after |
|---|---|---|---|---|
| Pilot record (`pilot.fields`) | torch_pilot §2 | none (tile §3.2's `pilot_live`, no record) → applier stage 2 | solid law; save (step 9, `fire_solid.md` §5.5's list); per-tick digest (`sim_core.md` §9); field registry (`sim_core.md` §6); pilots wire row; lifecycle (`region_gone`, leave) | nothing → a record whose `face`, `centre_um` rounding and cell-target region are undefined (W-B2). Not added to sim_core §9's member list or fire_solid §5.5's save list, and §10 omits both |
| Pilots wire row | tile §2.2 | `actor_id, region_id, end_tick` (10 B) → unchanged; `point_mm` is Q5 | GDScript decoder (`client_rendering.md` §4.1 `tick`); pilot marker (`client_rendering.md` §3.1, line 58); torch flame (§8); efference test (checklist 5b) | tile §3.1 and checklist 5b also require `cause = (actor_id, seq)` on the row, but §2 says "stays tile §2.2's" without `seq` (W-S2). No `region_id` source for a cell target (W-B2) |
| `kindle` stage-2 target | fire_model §5.4 (rule) plus torch_pilot §3 (evaluation, depth bound) | tile §3.2 (box, 50 mm, depth, "two candidates") → nearest surface, 1 mm tie, depth bound restored | applier, receipt's derived region, replay, NPC body modulator | split across two owners. §10 links tile to fire_model, which then holds no depth bound (W-S3) |
| Receipt (`intent_result`) | tile §3.3 | region → "derived region is the slab's" | client, sem_stimuli §6.2, digest member 5 ("effect values") | kindle's measured effect is never defined (W-N2) |
| Refusal codes | tile §3.4 | unchanged enum; `fuel_only_region` refuses kindle (Q1) | applier, exit variants (tile §6.2), refusals.py | no code for a point beyond 50 mm of every candidate, or on a burnt-out object (W-S6) |
| `actions.yaml` v1 | tile §3.2 (frozen) and torch_pilot §6/§10 | v0 in tree (`ignite`); tile's v1: `max_power_w`, `min_radius_m` = 0.2 → `max_flux_w_m2`, `min_radius_m` = 0.02 | stage 1, `ActionLimits`, `tests/test_act_validation.py::test_every_verification_grid_is_at_least_as_fine_as_the_smallest_action`, log header | two contradicting statements in the tree. No version number is named. No check site exists for the flux ceiling (W-S1). A test asserts `min_radius_m ≥ 0.2` (W-S4) |
| `content/items/torch.yaml` | tile §3.2 and torch_pilot §10 | file does not exist → `flux_w_m2`, `radius_m`, `max_duration_s`, `restrike_s` | stage 2 (`over_item_max`), pilot record, log header digest | "version bump" for a file that has never shipped, against fire_solid §5.1's "new formats start at version: 0" (W-S1) |
| `incident_absorbed` ledger line | fire_solid §5.4 | cone harness only → plus the torch | ledger test, exit gate §9.2 | listed in §10. Consistent |
| Fuel view (char share) | fire_solid §5.6 | unchanged | exit beat 4 | read by a test. fire_solid §5.6 says it is computed on the encoder's request, so the beat isn't "logged server state" (W-N3) |
| Exit beats (slab) | torch_pilot §9 (claimed) and tile §6 (D-S2, per fire_solid §7 and client_objects §7.3) | crate beats `t_crack`/`t_glow`/`t_gone` → `t_flash`/`t_char`/`t_out` | step 8's script, scenario goldens G1–G5 (client_objects §7.3) | two owners named in the tree; no mapping from G1–G5 to the new beats (W-S5) |
| Red gates (three `ignite` tests) | torch_pilot §9.4, tile §3.2, tile §6.4, roadmap | `ignite` → `kindle` rewrites | roadmap Phase 1 (flipping removes the `actions.yaml` band-aid) | one rewrite cannot fail (W-B1) |
| Work counters | sim_core §10 | unchanged → "unpiloted-crossing count … a work counter" | `TickReport`, bar 6, B5 | an outcome count enters a frozen work-only struct without an owner edit (W-N1) |
| Build-plan placement (6.1b) | torch_pilot §10, checklist step 6 | fire_model §10.2 (6.4), fire_solid §1.3/§2 ("6.4") | build order, the `TEMPORARY` sphere band-aid from 5b | stale "6.4" in three places (W-S7) |

## BLOCKER

**W-B1. One rewritten `ignite` gate keeps a bar the new target can't produce, so it flips without the mechanism.**
`docs/design/torch_pilot.md::§9.4`, the second bullet.

What is wrong: the bar of `tests/test_act_validation.py::test_the_fiercest_allowed_fire_has_the_same_outcome_at_every_rig_on_every_turn` (read at fcc6e55, lines 295–305) is `agrees(integrity_at(turn)).spread <= 0.1` on the crate, a wood *cell* region. The design says the gate is "rewritten with `kindle` at §6's ceiling … keeping its bar". There are two possible targets, and neither keeps it:
- A cell region: §4.4 makes a cell target deposit nothing. Integrity then stays 1.0 at every grid, and the gate passes trivially.
- A fuel slab: fire_solid §2 says objects take no damage, and `Frame.reading` refuses an object-only region. The bar has nothing to read, and the test either errors or is rewritten into something else.

The roadmap (Phase 1 bullet, lines 34–45) treats flipping this gate as the condition for removing the `actions.yaml` band-aid.

Failure scenario: 6.1b rewrites the test with `kindle` on the crate's region. It goes green because nothing is heated, the strict gate is removed, and the roadmap's precondition reads as met while the cross-grid divergence it guarded was never exercised. CLAUDE.md says a test that cannot fail is a BLOCKER.

Kind: contract (a claim the roadmap consumes).

Fix, unverified: state the rewritten gate's target and an observable the target actually produces (a slab beat, say), or record that the gate retires with `ignite` and say what replaces its cross-grid bar.

**W-B2. The pilot record is saved, digested and drives a wire row, but its bytes and two of its consumers are undefined.**
`docs/design/torch_pilot.md::§2`, `§3`, `§4.4`, `§10`.

What is wrong:
- **`face` u8 has no vocabulary.** Nothing says which integer is a slab's top face, its sides or underside, a rod's lateral surface or its ends, or a cell region's faces. Save goldens and the digest need the encoding.
- **`centre_um` (3 × i64) is called "exact … in whole micrometres" from "the authored integers".** Fuel geometry is f64 metres (fire_solid §1.1: "geometry f64 per kind"). F13's integer micrometres apply to cell edges and segment lengths only. A rod's nearest surface point is irrational. The rounding rule for a saved, digested value is unstated.
- **The null `object_id` 2³²−1** is a sentinel that fire_solid §1.1 doesn't reserve. Its counter rule ("at 2³² − 1 the next insertion is refused") doesn't say whether 2³²−1 itself is ever issued.
- **A cell-target record carries no region.** Nothing in it can produce tile §2.2's `region_id` on the pilots row, or test the "ends on `region_gone`" lifecycle.
- **"Saved and digested, in key order",** but sim_core §9's member list (registry fields, `sources`, `source_exposure`, regions, records) has no pilots member and no position for one. fire_solid §5.5's save list for step 9 doesn't include the record. §10 names neither edit. A new digest member changes every `tick_digest` line, so it is also an `intent_log` golden change, unless "an empty table adds no bytes" is stated for it as fire_solid §5.4 states for its tables. That isn't stated here.
- **No load-time validation is stated for a save** (the strictest gate, strangers' machines). Examples: `end_tick > apply_tick`; one live record per actor; the object live; flux and radius inside the ceiling. fire_solid §5.5 did this for its tables.

Failure scenario: step 9 builds save v0 from fire_solid §5.5's list and drops the pilot, which is N-S2's own scenario ("save mid-`kindle` and load: the pilot is gone"). Or two builders encode `face` differently, and the golden save and the replay digest disagree. Or a hand-edited save loads a record with `end_tick` < `apply_tick`.

Kind: contract (save, digest and wire bytes). N-S2 asked for exactly "its key, … its place in the save … the revised pilots table, codes, receipt field and item and limits formats with their versions". The key is answered; the rest is not.

Fix, unverified: define `face`'s enum and `centre_um`'s rounding, and reserve the sentinel in fire_solid §1.1's counter rule. Carry `region_id` in the record. Add the sim_core §9 member (or state that an empty table adds no bytes) and the fire_solid §5.5 save row, with load checks, to §10.

## SHOULD-FIX

**W-S1. `actions.yaml` v1 and `torch.yaml` have two owners that contradict each other, no version numbers, and no check site for the flux ceiling.**
`docs/design/torch_pilot.md::§6`, `§10`; `tile_and_client.md::§3.2`.

What is wrong:
- **Two owners disagree.** Tile §3.2 (frozen v3) defines v1 as `max_power_w`, `max_duration_s`, `min_radius_m` = 0.2, and the item as `power_w`, `radius_m` ≥ 0.2. Checklist step 5b ships that v1 with the sphere band-aid before 6.1b exists. torch_pilot §10 redefines both. So the tree states both shapes now, and §10 defers the move to Q6.
- **No version numbers.** "Each a version bump" names none. If 5b ships v1, 6.1b's file is v2, and the stage-1 code and the log header's recorded version must say so. `torch.yaml` doesn't exist yet, and fire_solid §5.1 says new formats start at `version: 0`, so "bump" is undefined for it.
- **No check site for the flux ceiling.** The client's `kindle` carries only `point_mm` and `duration_ticks` (tile §3.3), so stage 1 has no flux or radius to check against `max_flux_w_m2` and `min_radius_m`. The 65 kW/m² ceiling and the 0.02 m floor therefore bind the item file at load (a cross-file check like `FuelCatalogue`'s) or nowhere. The design names neither the site nor the refusal code, nor whether the check gets a gate-registry row.

Failure scenario: an item authored at 90 kW/m² loads, because nothing compares it with the ceiling. Every `kindle` then drives pine past its graded range, which §6's ceiling exists to prevent.

Kind: contract (format, operator surface).

**W-S2. §2 restates the pilots wire row in a version that drops tile §3.1's `cause`.**
`docs/design/torch_pilot.md::§2`, the bullet "The wire's pilots row stays tile §2.2's (`actor_id`, `region_id`, `end_tick`)".

What is wrong: tile §3.1 says "each bodies-part event and pilots row also carries it as `cause`", and checklist step 5b's test is "a `kindle`'s pilot row name[s] their intent". That needs `seq` on the row. Tile §2.2's 10 B row and this restatement both omit it.

Failure scenario: step 7 freezes the row at 10 B per this note. Checklist 5b's efference-copy test, or an NPC adapter mapping `cause` to `invocation`, can't identify which `kindle` a row belongs to.

Kind: contract (wire). Fix, unverified: link the row instead of restating it, and send the `seq` gap to tile §2.2's owner with Q5.

**W-S3. The target rule ends up split between two owners.**
`docs/design/torch_pilot.md::§3`, `§10`.

What is wrong: §3 says "The rule is fire_model §5.4's", then amends it:
- it restores the 50 mm depth bound (`not_on_surface`), which fire_model §5.4 dropped;
- it defines the candidate set;
- it adds the contact-line tie.

§10 turns tile §3.2's target sentence into a link to fire_model §5.4, but lists no fire_model edit. After §10, fire_model §5.4, the named owner, still has no depth bound, and the bound lives only here.

Failure scenario: 6.2's bed design follows fire_model §5.4 (the named owner) for porous fuel and omits the depth refusal. A `kindle` 0.3 m inside a crate then targets it.

Kind: contract. Fix, unverified: make one section the owner of the whole rule and have the other link to it.

**W-S4. A shipped test encodes the 0.2 m floor that §6 retires, and §10 forgets it.**
`docs/design/torch_pilot.md::§6` ("the 0.2 m radius floor retires"), `§10`.

What is wrong: `tests/test_act_validation.py::test_every_verification_grid_is_at_least_as_fine_as_the_smallest_action` asserts `LIMITS.min_radius_m >= COARSEST_M` (0.2), with the resolution-rule rationale. Setting `kindle`'s `min_radius_m` = 0.02 turns it red, unless someone loosens or deletes it.

Failure scenario: 6.1b ships `min_radius_m: 0.02`, the test fails, and the easy fix deletes it with no recorded reason. That is a guard removed without the "nothing here sees a cell" argument being checked.

Kind: consumer forgotten. Fix, unverified: list the test in §10 and the checklist, with what replaces it (for example, the footprint must be at least two strips across).

**W-S5. The slab beats' ownership (D-S2) is now claimed in two places, and the goldens aren't mapped.**
`docs/design/torch_pilot.md::§0` ("answers D-S2 for Phase 1") and `§9`; `fire_solid.md::§7` (row "The tile §6 revision, before step 8 | D-S2", unchanged); `client_objects.md::§7.3` ("Their owner is tile §6 (D-S2)").

What is wrong: neither citing section is in §10. client_objects §7.3 says G1–G5's names stay and their beats must be restated, but §9 defines `t_flash`/`t_char`/`t_out` without saying which golden each one feeds.

Failure scenario: step 8 follows client_objects §7.3 to tile §6, finds crate beats, and either builds goldens on beats the slab can't produce or re-derives the beats a second time.

Kind: contract. Fix, unverified: add both rows to §10 and give the G1–G5 ↔ beat mapping, or say that step 8 owns that mapping.

**W-S6. Refusal outcomes for two reachable cases are unstated.**
`docs/design/torch_pilot.md::§3`.

What is wrong:
- **A point farther than 50 mm from every candidate.** Tile §6.2's variant at (6000, 2000, 725) expects `not_on_surface`, but §3 names that code only for depth.
- **A point on a burnt-out object.** Candidates are "every live fuel object", but burnt-out rows stay (fire_solid §1.1), and §2's lifecycle ends on `region_gone`, which a burnt-out slab never triggers.

Failure scenario: a `kindle` on the burnt-out slab silently targets the floor's cell region beneath it. Per §4.4 that is `applied` with zero deposit, a receipt no player or NPC can tell apart from a success. The refusal codes are digested (sim_core §9 member 5), so the two producers' choices diverge in replay goldens.

Kind: contract (refusal vocabulary at stage 2).

**W-S7. Stale "6.4" placements survive, and §10 misses them.**
`fire_solid.md::§2` (table row "`kindle`'s target … 6.4 (Bio N1)"), `fire_solid.md::§1.3` ("`kindle` in 6.4"), `fire_model.md::§10.2` (the build plan has no 6.1b) and `§12` (line 474, "flipping the two fire red gates and retiring `actions.yaml`'s ceilings (proposed: in 6.4)"). Checklist 5b still says the sphere band-aid is "removed by step 6's skin".

What is wrong: §10 lists only fire_solid §2's Q1 exception, §5.4 and §7. The design never says that 6.1b deletes 5b's `TEMPORARY` sphere deposit, or that the roadmap's Phase 1 file list changes with it.

Failure scenario: 6.1b lands, the 5b marker stays listed against "step 6's skin", and the band-aid outlives the change that should remove it.

Kind: contract (build order, marker lint input). These edits are outside the one-link limit on fire_solid this branch keeps, so they belong in §10's list for after the rulings.

**W-S8. Checklist step 6 lists no format tests.**
`docs/plans/checklists.md`, step 6, "Added by D-B2".

What is wrong: the build tests listed omit:
- `actions.yaml` v1/v2's refusal of the old version;
- `torch.yaml`'s loader rejection paths and its gate-registry row;
- the pilot record's save round trip and golden fixture;
- the digest-member golden.

CLAUDE.md requires every rejection path and a registry row for loaders, and a round trip plus goldens for save formats.

Failure scenario: 6.1b passes its listed tests while `scripts/lint_gates.py` has no row for the item loader.

Kind: mechanism (build-step test list). It can be deferred to 6.1b with that trigger.

## NIT

**W-N1.** `torch_pilot.md::§5` and `§9.1`: the "unpiloted-crossing count" is an outcome count, but it goes into `WorkCounters`, which sim_core §10 defines as exact counts of work and which bar 6 holds to expected values. Name the owner edit, or report the count elsewhere. Kind: contract (`TickReport`).

**W-N2.** `torch_pilot.md::§9.1` beat 1: the receipt's "measured effect" for `kindle` (tile §3.3; digest member 5 "effect values") is never defined. Is it the region, the object or the deposit? Kind: contract.

**W-N3.** `torch_pilot.md::§9.1` beat 4 reads fire_solid §5.6's fuel view, which is presentation-only and computed on the encoder's request. That isn't "logged server state". Recompute it from the store in the test, or say that the test requests the view. Kind: mechanism.

**W-N4.** `torch_pilot.md::§2` vs tile §2.2: `end_tick` is u64 in the record and u32 on the wire, and nothing states the narrowing rule. Q5's `point_mm` is the client's point, not the footprint centre (`centre_um`), so §8's "with one, it aims at the footprint" is off by up to 50 mm. Kind: contract (wire).

**W-N5.** `torch_pilot.md::§9.1`: the script is "step 8's `tests/scenarios/` file, in tile §6.2's form, … the cap of tile §6.2". Tile §6.2's file `alley_exit.yaml` is the crate's (Phase 2) and versioned, and its 5,400 s cap is 2× the crate's estimate. The slab script's name, its version and its own cap are unstated. Kind: contract (script format).

**W-N6.** `torch_pilot.md::§8`: for a cell-target pilot the client is told to aim at "the target object's top face centre", but a cell region has no object. Kind: consumer gap.

**W-N7.** `torch_pilot.md::§1` restates fire_solid §4.4's cone case ("flash at m''_flash, a prescribed q''_fl …, at most one flash per part") in prose, a B36-style copy below any registered count. A link would do. Kind: one-owner hygiene.

**Checked and sound:**
- The `contracts.md` row and its count rationale.
- The fire_solid §7 one-row edit: the subcell-design worktree (ed2c9ae) leaves that line unchanged, so they don't conflict.
- The `kindle` record staying `target: null`, consistent with tile §3.2 and boundaries §6.2.
- `incident_absorbed`, listed in §10.
- The log header already digests items (boundaries §6.3).
- The refusal codes named in the design all exist in `src/simcore/core/refusals.py`.
- `wrong_target` exists in code and on the subcell branch (S0), as Q1 says.

Count: 2 BLOCKER, 8 SHOULD-FIX, 7 NIT.
