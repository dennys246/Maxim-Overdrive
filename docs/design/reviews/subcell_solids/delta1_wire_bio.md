# Sub-cell solids design, delta 1: Wire integrity and Bio-faithful integration (2026-11-22)

The reader's report as handed back, saved by the author. The reader set every status below, read from the tree at
ed2c9ae.

**What the reader read:**
- the design end to end;
- the linked sections: `fire_solid.md` §1.1, §2, §5.3–§5.6 and §7; `client_objects.md` §3; `client_rendering.md`
  §4.1; `sim_core.md` §4, §5.1, §7 and §9; `sem_stimuli.md` §2.3, §6.2, §7.1 and §7.4; `tile_and_client.md` §3.2–§3.4
  and §6.2;
- the code behind them: `refusals.py`, `applier.py`, `bridge.py`, `imagination.py`, `schema.py` and `grid.py`.

Maxim `origin/main` is still b98954f7 after a fetch.

**Verdict:** no new contract BLOCKER (B33). All three round-1 Wire BLOCKERs and the Bio BLOCKER are fixed. Seven new
SHOULD-FIXes and eight NITs. NS1, NS2, NS3, NS6 and NS7 are small contract folds; NS4 and NS5 could move to S1 and S6
as build-step tests if the owner accepts.

## Boundary table (changed contracts only)

| Value | Owner | Status |
|---|---|---|
| t(p) and every µm decision (int64 µm, q = rint(v·10⁶)) | §2.1, from F13 (`grid.whole_micrometres`) | spec frame OK; the world-frame composition is unstated (N1) |
| `objects`: `role`, `material_id`, `integrity`, `breached`, `support`, `pose`, `state` 0–3 | §3.1, extending fire_solid §1.1 | matches; `recipe_id` for structural rows unstated (N7) |
| `tiles` (store) | §3.1, §3.3 | the emitter key doesn't match (N5) |
| `object_contact` (µm polygon) | §3.1 | OK |
| object state requests and `topology_version` | sim_core §5.1 (§12 row) | OK |
| wire `structures`, `structure_rods`, `structure_slabs`, `tiles` | client_objects §3 (§12 row) | the tile mapping needs a recount (NS2); fuel `state` can reach 3 (NS3); nothing reaches the wire before S6 (NS4) |
| `welcome`: material map plus `tile_m` | client_rendering §4.1 | no §12 row (N8) |
| `ObjectFrame` / `objects_version` (presentation only) | fire_solid §5.6 (§12 row) | OK |
| `QUANTITIES`, `Frame.reading`, `region_parts` | fire_solid §2 | a region that becomes object-only mid-life is unhandled (NS5) |
| refusal codes (§11.3) | `refusals.py`, tile §3.4 (§12 row) | all reused codes exist; `not_on_surface` on strike is wrong (NS1); `wrong_target` gets a new meaning (NS7) |
| spec v1 and its v0 migration (`version` key) | §11.2, `schema.read_version` | `read_version` refuses an unversioned spec (NS6) |
| `limits.yaml`, `mechanics.yaml` (µm, SI; pair key `a\|b`) | fire_solid §5.1 (§12 row) | OK; small `duplicate_key` issue (N6) |
| per-tick digest | sim_core §9 | break recorded; "name order" should be registry order (N6) |
| `support_lost` | "the `TickReport`'s lab section" | no such section exists (N4) |
| body to object contact | sem_stimuli §7.1 | ambiguous against the carried sub-mesh (N5) |

## Status of round-1 findings

**Wire integrity**

| Id | Status |
|---|---|
| B1 | fixed: separate structural tables, numbered `state`, `material_id`, protocol bump. Bytes and the join cap deferred to S6 (trigger: S6 lands with structure's limits) |
| B2 | fixed for regions born object-only; NS5 covers regions that become so |
| B3 | fixed; N1 is a residue |
| S1, S2, S5, S8, N1–N5 | fixed |
| S3 | fixed: `imagination.py:155`'s outside branch goes to `outside_extent` |
| S4 | open: "S0 before 6.0a" exists only in this unmerged design; `foundations_plan.md` row 6 still has 6.0a depending only on 5a, and §14 item 2 is unanswered. Trigger: the owner's §14.2 ruling plus an S0 dependency in that row |
| S6 | open in part: the `version` key and SpecId fixed; the v0 migration contradicts `read_version` (NS6) |
| S7 | open: `ignite` fixed; strike refusals and reach still differ by representation (NS1) |
| S9 | fixed; a few rows still missing (N8) |

**Bio-faithful integration**

| Id | Status |
|---|---|
| B1 | fixed: `QUANTITIES` and the bridge unchanged, object readings on the lab surface, the NPC fire note first |
| S1 | fixed: stage-2 codes become `accepted`; T11 gains categories |
| S2, N1, N2 | fixed |
| S3 | fixed; N4 is a residue |
| S4 | fixed; N5 is a residue |
| N3 | deferred. Trigger: the first contact-force row in `sem_stimuli.md` |

## New findings

**SHOULD-FIX**
- **NS1, `§7.1` strike row and §11.3:** a strike off its region is `not_on_region` today (`applier.py:123`), not
  `not_on_surface`, which is `kindle`'s code. Reach differs too: cells use footprint plus σ, objects use "within
  `contact_tolerance_um`". A strike 5 cm off a 0.40 m block is accepted, and off a 0.39 m block refused, against §2.3
  and D36 (3). Fix (unverified): objects take `_on_region`'s rule and `not_on_region`.
- **NS2, `§10` `tiles`:** to place tile k, the client must recount the tiling from f32 geometry, which
  `client_objects.md` §3.2 forbade for segments (a recount disagreed for 42 of 1,981 lengths); the partial last tile
  is unspecified. Temperatures land on the wrong patch, or the key check refuses the frame. Fix (unverified): a
  per-face tile count, or explicit tile geometry, plus a ragged-edge rule.
- **NS3, `§3.1`, §7.1, §7.2 against §10:** strike and removal apply to every role, so a struck fuel crate reaches
  `state` 3, which the decoder refuses (fuel's state stays 0 or 1). Fix (unverified): restrict them to non-fuel roles
  until 6.2, or widen fuel's range with a protocol bump.
- **NS4, `§13`:** structure exists from S1 but reaches the wire at S6, so for S1–S5 a locker blocks, supports and
  conducts but is invisible. Fix (unverified): land S6's tables with S1, or refuse structure from shipped scenes and
  `imagine` until S6, as a Known gap.
- **NS5, `§4.3`, §7.3 against `bridge.py` and `applier._check_region`:** a mixed region whose cells are struck away
  becomes object-only mid-life. Its `RegionInstrument.read()` then calls a `Frame.reading` that refuses, so an exception
  reaches Maxim's read tool, and `_check_region` refuses `region_gone` for a region §4.3 says isn't gone. Fix
  (unverified): define the reading for that state, revise `_check_region`, and add both to §12.
- **NS6, `§11.2`:** "an unversioned spec reads as v1", but `schema.read_version` refuses a missing version, and
  migrations are keyed by integer versions. S1's red-first test on the spike's unversioned `arms.yaml` gets
  `bad_version`. Fix (unverified): define v0 explicitly (an exception named in `Format`, or `version: 0` added to the
  committed files) and add a §12 row for `schema.py`.
- **NS7, `§12` S0 row and §2.3:** S0 refuses object-only acts with `wrong_target`, an append-only code whose meaning
  today is "named a target that isn't this region", against `refusals.py`'s "never reused". For S1–S3 the refusal
  depends on the representation (D36 (3)), and §2.3 has no rows for this interim or for readings. Fix (unverified):
  refuse on a representation-neutral basis, and add §2.3 rows for readings and for acts during S1–S3.

**NIT**
- **N1, `§2.1`:** q(o+r) and q(o)+q(r) disagree by 1 µm on 25% of 200,000 random float pairs, and on none for whole-µm
  inputs (measured). Fix (verified): require whole-µm inputs, or define world µm as q(origin) + q(relative).
- **N2, `§3.1`:** box-as-slab picks no axes when edges tie, and no handedness for length × width.
- **N3, `§9`:** S3 "makes an object-only region reachable by an NPC act", but §7.3 and §13 keep refusing it through
  S3; name the act.
- **N4, `§8.3`:** `TickReport` has no lab section (sim_core §4); call it a host-side effect, with a §12 row.
- **N5, `§5.1`:**
  - a body reading the touched tile each tick contradicts sem_stimuli's carried sub-mesh, so say "at onset only";
  - map `tile` to `radiant_emitters`' key in a §12 row.
- **N6, `§11.1` and §11.4:** a reversed unique pair isn't a `duplicate_key`; "name order" should be registry order.
- **N7, `§3.1`:** `recipe_id` for structure and inert rows has no sentinel.
- **N8, `§12`:** missing rows for `client_rendering.md` §4.1 and `schema.py`. The index lists D31–D35, which arrive
  with PR #42: a merge-order dependency, not a defect.

**Maxim (`origin/main` b98954f7):**
- the `mechano_proprio` row is at `docs/plans/grounding.md:253`, and Overdrive's M11 at `sem_stimuli.md:475`;
- searched `docs/plans`, `DECISIONS.md` and `src/maxim/embodiment` for `collapse`, `structural integrity`,
  `rigid body`, `statics` and `load-bearing`: nothing relevant, and no new upstream item is needed.
