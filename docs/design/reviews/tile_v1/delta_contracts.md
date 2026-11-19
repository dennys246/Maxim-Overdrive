# Tile spec v2, delta: Wire integrity, Trust boundary, Architecture

Target: the working tree of `phase1/tile-spec` (uncommitted fold of f6afd66): `docs/design/tile_and_client.md` §2–§4,
§7, and `docs/design/client_rendering.md` §3–§4, §5.6, §7.5. Read against `boundaries.md` §0 (O23, O24), §2, §4.2,
§6.1–§6.3, §7.2; `world_model.md` §5, §8; `origin/phase1/realtime-design:docs/design/realtime_lanes_coop.md` §2.1,
§4, §7; `origin/phase1/act-validation`'s `bridge.py` and `data/world/actions.yaml`; round one's `wire_trust.md` and
`architecture.md`. Scope: the new contracts only.

Counts: 2 BLOCKER, 9 SHOULD-FIX, 10 NIT.

## BLOCKER

### DC-B1. The `region` channel and the static welcome map break on regions that `imagine` creates
`tile_and_client.md::§4.2` (channel table, `welcome`), `§2.3` (Replanning)

- world_model §5: `region_id` is u16, ids are never reused, and a `regions_version` bumps on every new region, "the
  protocol carries the change" (F10). `imagine` creates a region on the shipped path (`imagination.spec.place` adds
  `grid.regions[name]`), and §2.3's replan test uses `imagine`.
- The tile sends a u8 *index into `welcome`'s map*, caps regions at 255 "refused at load", and has no message that
  updates the map after `welcome`. A load-time cap doesn't bound runtime creation, and never-reused ids grow
  monotonically.
- Failure: the replan test imagines a box at tick N. The next cell frame carries a region the client's map lacks. The
  decoder either refuses the frame (session closes) or the ID pass, cut-away and pick outline treat it as region 0;
  if the map is part of the hashed catalogue, every later frame fails the hash. A long `imagine` session passes 255
  and the encoder has no defined behaviour. u8 vs u16 is a real mismatch: the u8 index needs a world-id → index remap
  that nothing specifies.
- **Fix.** Send `region` as u16 carrying `region_id` itself (no remap; +230,400 B, 1.61 → 1.84 MB, under the
  3.5 MiB cap, derived). Put `regions_version` in every cell frame's header; add a `regions` message (new entries
  only) sent before the first frame that uses them; the decoder refuses a frame whose `regions_version` is ahead of
  its map. Keep the region map out of the catalogue hash, or the hash churns. Fixture: a frame after an `imagine`.

### DC-B2. The client message set contradicts protocol v0 and plan step 7, with no amendment written
`tile_and_client.md::§3.1` (kind table), `§3.3`, `§3.4` (`unknown_kind`, `unknown_field`); `client_rendering.md::§3`

- realtime §7's v0 table has one intent message, `act {region, action, params}`, answered by `act_result`.
  `foundations_plan.md` step 7 still says "`act_result`". The tile has per-kind messages (`move`, `move_to`,
  `kindle`), an `intent_result` reply, and "the client sends no `region`". Neither document says which table step 7
  freezes, nor how `strike`, `douse`, `imagine` arrive ("as today" means `act` with a client-sent `region`, which
  the tile's own rule forbids for `kindle`).
- Failure: step 7 is built from realtime §7 (the protocol's owning doc). A client sends `act {region: "crate",
  action: "kindle", ...}`; either the server accepts a client-chosen region the tile says the server derives, or the
  tile's `unknown_field` refuses a message realtime §7 defines. The golden wire fixtures freeze whichever reached
  code first.
- **Fix.** Write the v0 client-message table once (tile §3.3, with an amendment line in realtime §7 when that branch
  merges): retire `act`/`act_result`; one message per kind; per kind, whether `region` is sent or derived (`strike`
  needs a decision: its point-or-centroid targeting differs from `kindle`'s point-only); update the plan's step-7
  row.

## SHOULD-FIX

### DC-S1. `observed_tick` is stamped from the wrong stream
`tile_and_client.md::§3.1`
boundaries §4.2 stamps "the last frame sent to that session". The tile stamps "the last tick delivered". After the
Frame split the client's cells lag its latest `tick` by up to 1/`snapshot_hz` (0.5 s at 2 Hz), more under the
one-frame-in-flight drain rule (`client_rendering.md` §4). A `kindle` picked on cells at tick T_c is recorded as
observed at T_t > T_c, so any `stale` rule judges it against a world the player never saw. **Fix:** stamp the tick of
the last cell frame sent (optionally also the last bodies tick), and amend boundaries §4.2's wording with the split.

### DC-S2. The Frame cadence narrows O23 and loses a receipt's after-frame
`tile_and_client.md::§4.1`
boundaries §4.2 and O23 publish "after each tick that applied an intent, so a receipt's after-frame exists on its
apply tick". The tile publishes cells only on cell writes and bodies only when an actor changed. An applied `kindle`
adds a source (no cell write, no actor column change); a refused intent changes nothing. Failure: the receipt's
`after` frame id names a Frame that was never published. **Fix:** publish a Frame (bodies part plus the shared cell
reference, cheap) on every tick that applied any intent, and state that frame ids are ticks.

### DC-S3. Body occupancy has no home in the Frame split
`tile_and_client.md::§2.1` (occupancy), `§4.1`
"Body occupancy is a registered derived field." If it lives in the cell part, the cell version bumps every walking
tick and the 64–80 MB copy runs per tick, the O23 cost. **Fix:** say occupancy is derived from the bodies part at
reduction time, never stored in the cell part.

### DC-S4. Events ride a lossy, throttled stream; pilots have no state
`tile_and_client.md::§4.1`, `§4.2`; `client_rendering.md::§3` (pilot marker)
`tick` is throttled to 30 Hz and latest-wins per session. At 20× one delivery spans about 6.7 ticks, so `arrived`,
`path_blocked` or `pilot_ended` in a skipped tick is gone. `path_state` recovers paths; nothing recovers pilots (no
pilot column or table), so the client's live-pilot marker never clears, and a reconnecting client can't learn a pilot
exists. A successful replan changes the waypoints, and no message carries them. **Fix:** a per-tick pilots table
(`actor_id`, `region_id`, `end_tick`) in the bodies part; events accumulate per session until delivered, bounded,
with overflow forcing a resync; a replan event carries the new `path_mm`.

### DC-S5. `kindle` has no physics-safety ceiling, and `actions.yaml` v0 is orphaned
`tile_and_client.md::§3.2`
boundaries §6.1 rule 3: limits are the `ActionLimits` ceiling *intersected with* capability. The tile gives `kindle`
only the item's capability. `data/world/actions.yaml` v0 has an `ignite` block, and
`tests/fixtures/formats/v0/actions.yaml` is a committed golden fixture. Retiring `ignite` changes that file's schema
with no version or migration named. **Fix:** `actions.yaml` v1 with a `kindle` ceiling (`max_power_w`,
`max_duration_ticks`, `min_radius_m`) and a v0 → v1 migration (or a refusal test) that keeps the v0 fixture loading.
*On refusing v0 intent logs:* acceptable. No committed intent-log fixture exists on `main`, `phase1/act-validation`,
`phase1/realtime-design`, `phase1/standards` or this branch, and the log writer hasn't shipped. The refusal test needs
a hand-built v0 log committed in step 6. Better still, if `kindle` lands before the log writer ships, no v0 log can
ever exist and the test is moot. Say which order the plan takes.

### DC-S6. An item-dependent check sits in world-free stage 1
`tile_and_client.md::§3.4` (`out_of_range` row)
"`duration_ticks` over the item's max" is listed as stage 1, but the held item is actor state at apply, and stage 1 reads
nothing from the world (`parse_action`'s docstring; boundaries §6.1). **Fix:** stage 1 checks the ceiling (DC-S5);
the item max is a logged stage-2 code (`over_item_max`).

### DC-S7. `kindle` doesn't fit the region-bound SEM door
`tile_and_client.md::§3.2`, `§3.1` (NPC sentence); `bridge.py::StructureModulator`
The modulator is per region, and an NPC calls `crate.ignite`. `kindle` derives the region from the point. An NPC
calling `crate.kindle` at a point on the wall has two region sources and no rule. boundaries §6.2 logs `target`
"resolved at the door", but the region is derived at stage 2, after the log. `duration_ticks` in an
`AffordanceSchema` puts a tick count in front of an agent (npcs §3, O4). **Fix:** make `kindle` a body affordance
(per-actor binding, boundaries §7.2), not a region one. Log `target: null` and put the derived region in the receipt
(derived, replayed). The agent-facing parameter is in body terms, and the adapter converts it to ticks.

### DC-S8. `dir` is sound arithmetic but neither canonical nor decided
`tile_and_client.md::§2.3`, `§3.1`
Checked: (1000, 0) gives 140 mm and (707, 707) gives 98 mm per axis, as stated. But magnitude leaks into the step:
(1, 1) gives n = 1414 and 99 mm per axis, while (1000, 1000) gives 98, so one direction yields two logged params and
two trajectories. "Typed canonical params" aren't canonical. Separately, §3.1 argues that an allocentric compass is
wrong for a body (OD-C11) while adopting an allocentric `dir`, and T2 never decided the vector. It is a vocabulary
step 7 freezes. **Fix:** canonicalise at stage 1 (require max(|dx|, |dy|) = 1000, or normalise with a stated rounding
rule) and log the canonical form. Add §9 Q7: "integer allocentric `dir` on the wire, egocentric reduction in the
Phase 4 adapter?" The design is sound once canonical. Recommend yes.

### DC-S9. The actor table's encoding on `tick` is unspecified
`tile_and_client.md::§2.2`, `§4.2`
`tick` is a JSON text message (realtime §7). The table is column-major with `f32` `body_temp_c` and `i16` `facing`, yet
no encoding, catalogue entry, hash coverage or fixture is named. JSON floats for `f32` aren't bit-stable across
encoders. **Fix:** either a small binary table (catalogue-described, hash-checked) or JSON with integer columns only
(`body_temp_mK` as i32); either goes in step 7's fixtures.

## NIT

- **DC-N1** `§3.1` kind table: "any actor holding an igniter" and "with a body" are capability (stage-2
  `no_igniter`, `no_body`), not authority. boundaries §6.1's column is the emitter's role: "any actor".
- **DC-N2** `§2.2`: `energy`, `dose` are "absent until Phase 4/5, declared now", yet they're counted in the 36 B.
  F5 has no optional fields: say they're present as zero, with a `derivation_version`.
- **DC-N3** `§3.1` table: `douse` isn't "as today". act-validation ships `extinguish`, and `douse` is F7's.
- **DC-N4** `§1.3`: `cutaway` is a presentation flag inside scene v1, so it's in the scene digest, and flipping a
  cut-away refuses every replay. Put it in client data keyed by region name.
- **DC-N5** `§4.2`: name the catalogue hash's canonicaliser (boundaries §6.3, one in `engine.checks`). `975/255`
  doesn't terminate in binary, so the number format must be fixed.
- **DC-N6** `§3.2` Deposit: state the pilot's interval, [apply_tick, apply_tick + D) in tick time, against the
  physics interval (t − 5, t]. A pilot applied on physics tick 70 is otherwise off by one step between builds.
- **DC-N7** `§7`: "file gates" and "host" aren't among O24's four layers (core, adapters, game, client protocol).
  Name the O24 layer for each. The stage-1 enum holds host-produced `coalesced`/`rate_limited`: say the enum lives in
  core and the host produces them.
- **DC-N8** No caller on the shipped path: receptor volumes, `energy`/`dose`, the `stale` and `cancelled` outcomes,
  and `observed_tick` (no `stale` rule in Phase 1). Say so, or state the Phase 1 stale rule.
- **DC-N9** `§2.1` reach "from the body axis" is horizontal, so a point 4 m up a wall is in reach. State 3-D
  distance or a height band.
- **DC-N10** `§2.2` `held_item` u8 "0 none" is an index into `welcome`'s list. Say the list is 1-based, or 0
  collides with the first item.

Verdict: not ready to freeze. The movement-as-intent pipeline is now right; DC-B1 (region identity under `imagine`)
and DC-B2 (two v0 message tables) are cheap to settle and must be before step 7's fixtures.
