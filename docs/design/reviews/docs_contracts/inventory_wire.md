## Wire protocol and client-facing formats: contracts stated in more than one place

I read every scope doc on `phase1/docs-contracts` and re-read every quote below at its line. The contradictions are listed first.

### A. Copies that disagree

1. **Intent receipt / `intent_result` payload.** The single reply to an intent, and what it wraps.
   - DEFINES boundaries.md:543 §7.2: the receipt has the intent id, outcome (`applied`, `refused`, `stale`, `cancelled`), "`apply_tick`", the measured effect, and the before and after frame ids.
   - DEFINES npcs_and_sem.md:688 §6.4: the same list, including "`apply_tick`".
   - DEFINES tile_and_client.md:255-257 §3.3: "`intent_result` wraps it with wire-only `apply_tick` and `path_mm`. Agent-facing receipts carry no tick."
   - DEFINES sem_stimuli.md:313-320 §6.2: "the **receipt is `(pid, kind)`**". The kinds are "`malformed`, `limit`; any stage-2 result is `accepted`". It supersedes "by name" npcs §6.6's "measured effect", boundaries §2.2's "receipts" and `settle`'s receipt type. It does not name boundaries §7.2 or npcs §6.4, and both still define the old shape.
   - **DIFFER:** boundaries and npcs put `apply_tick` in the receipt, while tile says agent-facing receipts have no tick. The outcome vocabulary also differs: `applied/refused/stale/cancelled` against `malformed/limit/accepted`.
   - **Owner:** split it. The agent receipt goes to sem_stimuli §6.2 (newest, and it says it supersedes). The wire `intent_result` goes to tile §3.3, which must then state its own outcome field.

2. **The intent kinds vocabulary (action vocabulary v1).**
   - DEFINES tile_and_client.md:215 §3.2: "adds `kindle` … and retires `ignite`, as F7 retired `extinguish`". :206 §3.1 lists the kinds in `kind_rank`: "`kindle`, `strike`, `douse`, `imagine` 3".
   - DEFINES world_model.md:210 §8: "`extinguish` is retired, and `douse` … is added (F7)".
   - DEFINES world_v2.md:364 §8: "**`extinguish` changes meaning:** water as an energy and O₂ sink … It bumps the action-limits version". **DIFFERS** from world_model, which retires `extinguish`.
   - DEFINES boundaries.md:376 §6.1 authority table: "`intent` (strike, ignite, douse, …)". **DIFFERS**: it lists the retired `ignite`.
   - DEFINES fire_model.md:244-257 §5.4: "`ignite` and `extinguish` leave `parse_action`", and `strike` "becomes a body act with a held thing".
   - DEFINES boundaries.md:383: admin `set_material` is a host command.
   - DEFINES checklists.md:113 (step 5a): "a `retired:` list of verbs".
   - Stale DEFINES architecture.md:137-138 ("`strike`, `ignite` and `extinguish`"), which describes today's code.
   - **Owner:** tile §3.2, which already owns vocabulary v1. Give it a kinds table, have boundaries §6.1 link to it, and correct world_v2.

3. **`kind_rank` values.**
   - DEFINES tile_and_client.md:206 §3.1: "join/leave 0, `time` 1, moves 2, `kindle`, `strike`, `douse`, `imagine` 3".
   - DEFINES checklists.md:113: "Intent kinds ranked 0/10/20/30, leaving room".
   - **DIFFER:** 0/1/2/3 against 0/10/20/30.
   - **Owner:** boundaries §6.2, which owns the ordering key "stated here and nowhere else". The rank values should move there.

4. **The ordering key.**
   - DEFINES boundaries.md:426-427 §6.2: "One ordering key, stated here and nowhere else … `(apply_tick, kind_rank, apply_us, actor_id, seq)`".
   - Restated (DEFINES) at tile_and_client.md:196 §3.1, which agrees.
   - REFERENCES npcs_and_sem.md:1024 §9 and :1069 §11.1.
   - DIFFERING DEFINES in superseded docs: realtime_lanes_coop.md:219 §4.2 and :354 §7 ("`tick`, `host_seq`"), and world_v2.md:291 §6 ("then assigns `host_seq`").
   - **Owner:** boundaries §6.2.

5. **`kindle` target derivation and deposit (stage-2 refusal `ambiguous_point`).**
   - DEFINES tile_and_client.md:226-228 §3.2: "the named solid whose authored box surface lies within 50 mm … no deeper than 50 mm inside; two candidates is `ambiguous_point`". Its deposit is a sphere, then a disc, with "`min_radius_m` = 0.2".
   - DEFINES fire_model.md:246-249 §5.4: "nearest the point within 50 mm, with a tie within 1 mm refused as `ambiguous_point`". Also: "That replaces the sphere deposit and the 0.2 m minimum radius."
   - **DIFFER** on both the refusal rule and the radius floor.
   - fire_model's status says it is "the direction, not the build spec", but its §10.1 says it revises tile T4.
   - **Owner:** tile §3.2 until fire_model's next revision. One of the two must be edited now.

6. **Snapshot channels.**
   - DEFINES client_rendering.md:113-122 §4.2: `material`, `region`, `crack`, `surface_glow`, `burning` ("the burning fraction of the cell's fuel surface"), and `temperature_c` f16.
   - DEFINES fire_solid.md:428-429 §5.6: "`burning` stays reserved", and "These names supersede fire_model §9.2's `segment_glow` and `burning`". **DIFFERS** from client §4.2, where `burning` is a live channel.
   - DEFINES fire_model.md:414-416 §9.2: "`burning`, the ignited area fraction". fire_solid says this is superseded.
   - DEFINES world_model.md:208 §8: "`crack` stays 1 − integrity". client §4.2 gives `crack` a second meaning, "a bed cell's charred-or-burned fraction" (tile:374 §5.5 says the same). That conflicts with F1, "A new meaning gets a new name".
   - DEFINES architecture.md:159-160: "`material`, `crack` …, `glow` (from 525 °C … to 1500 °C) and `temperature_c`". **DIFFERS** in the name (`glow` against `surface_glow`) and the scale (to 1500 °C against offset 525 °C with scale 975/255).
   - DEFINES checklists.md:205 step 7: builds "`surface_glow` and `burning`".
   - fire_solid:425 also adds a clip on `temperature_c`, "clipped to [−273, 6000] like `temperature_c`", that client §4.2 does not state.
   - **Owner:** client_rendering §4.2.

7. **Per-cell frame size.** architecture.md:171 says "At 5 bytes per cell". client_rendering.md:124 §4.2 says "230,400 × 8 B". **DIFFER.** Owner: client §4.2. architecture should link to it.

8. **Buffer caps and `max_size`.**
   - DEFINES client_rendering.md:131-136 §4.3: client "`inbound_buffer_size` = 4 MiB"; the server "keeps inbound `max_size` at 64 KiB".
   - DEFINES realtime_lanes_coop.md:203 §4.1: "a small `max_size` (about 64 KiB…)". It agrees with client §4.3.
   - DEFINES architecture.md:185-186: "Both ends must raise their default caps (… `max_size` is 1 MiB)". **DIFFERS**: client and realtime have the server keep a small cap.
   - realtime §8's Supersedes list (:385) already says architecture's "buffer-cap advice (TB-7: only the client raises its cap)" must change. That edit was never made.
   - architecture:184 also still says head-of-line blocking is "harmless for a turn-based game".
   - **Owner:** client §4.3.

9. **Cell-frame header and catalogue fields.**
   - DEFINES client_rendering.md:97, 100-101 §4.1. The header has `protocol`, `kind`, `tick`, `shape`, `regions_version`, the catalogue hash, and per array name, dtype, offset and size. The catalogue gives `unit`, `dtype`, and `scale_num`/`scale_den` and `offset`.
   - DEFINES world_v2.md:354-360 §8: per-grid "shape, cell size and origin"; channels with "an encoding from a closed list, `required`"; tables; and the bump rules ("A new encoding, dtype, `kind` or compression bumps the protocol").
   - DEFINES realtime_lanes_coop.md:342-349 §7: z, y, x axis order and "Compression is off in v0, with the field reserved".
   - DEFINES architecture.md:190-191: a reserved compression field "plus each array's uncompressed byte size".
   - DEFINES checklists.md:193-194 step 7: "a `required` flag per channel, `compression: none`, `axis_order`".
   - **DIFFER:** client §4.1's header has no `required`, compression, `axis_order` or grids, while the others require them.
   - **Owner:** client §4.1. The grammar and bump rules should move into it from world_v2 §8, which is superseded.

10. **`welcome` contents.**
    - DEFINES client_rendering.md:94 §4.1: `session`, `role`, the world config, `shape`, the catalogue, the region map, the archetype and item lists, `regions_version`, and the time state.
    - Additional fields are defined elsewhere:
      - realtime_lanes_coop.md:339-340 §7: "the session's own `actor` id … and the material table … §4.1's `welcome` row omits both; they stay here until it is amended."
      - world_v2.md:362 §8: "the zone list and material table v1".
      - fire_solid.md:427 §5.6: "the recipe name↔id map".
      - sem_stimuli.md:122 §3.2: "`bindings_digest`".
      - checklists.md:195: "the engine `build`".
      - ip_and_licensing.md:132 §6: "each region's spec id".
    - **DIFFER:** client §4.1 omits all of these.
    - **Owner:** client §4.1, extended with each field. The other docs then link to it.

11. **Phase-1 protocol step's message list.** world_model.md:271 §10 row 6 says "Versioned, extensible `welcome`, `act_result` and `error`". realtime.md:323 §7 says "`act` and `act_result` are retired", and foundations_plan.md:33 row 7 lists "`welcome`, `intent_result`, `regions`". **DIFFER.** Owner: tile §3.3 (client to server) and client §4.1 (server to client).

12. **`Origin` refusal and versioning in the slice.** vertical_slice.md:29 says "HTTP is refused at the first bytes: the slice's form of the `Origin` refusal". :50-52 gives its own message kinds (`say`, `state`, `event`, `npc_line`) and "**Versioning:** none on purpose". Its own §2 also says "CLAUDE.md's rules for … the wire hold here unchanged", and CLAUDE.md requires every format to be versioned. **DIFFERS** within the plan itself. The slice is a deliberate throwaway format (`slice-0`), so it is not a restatement, but the "versioning: none" line conflicts with the rule.

### B. Copies that agree (restated, should become links)

- **Handshake: token, `Origin`, 127.0.0.1, hello first.**
  - DEFINES realtime_lanes_coop.md:280-285 §5: `hmac.compare_digest`; tokens by env var or 0600 file, never argv; `hello` first and only once; `Origin` refused "including an empty one or `null`"; binds "the literal `127.0.0.1`".
  - Restated in client_rendering.md:338-342 §7.5, tile_and_client.md:245 §3.3, boundaries.md:337-339 and :343 §5.3 rows, and architecture.md:178-182. vertical_slice:168 is test-only.
  - AGREE. **Owner:** move it out of superseded realtime §5 into client §4 or tile §3.3. Suggest a new client_rendering §4.0, "Session and handshake".
- **Strict JSON, closed schemas, 2^53.** DEFINES realtime.md:317-319 §7, boundaries.md:677-679 §9.1, client_rendering.md:105-106 §4.1 and checklists.md:196-197. AGREE (2^53 accepted, 2^53+1 refused). **Owner:** boundaries §9.1.
- **Intent record fields and the pipeline.** DEFINES boundaries.md:368-370 §6.1 and :405-412 §6.2. Restated in tile_and_client.md:194-196 §3.1 ("The record is boundaries §6.2's:" followed by the full list). AGREE. **Owner:** boundaries §6.2. Tile should keep the link and drop the list.
- **Two-stage validation.**
  - DEFINES realtime.md:327-330 §7.
  - DEFINES boundaries.md:345-346 §5.3. It cites "(world_v2 §7)", but world_v2 §7 is the SEM membrane section, so the citation looks wrong.
  - DEFINES tile_and_client.md:261-271 §3.4, the check-order table.
  - AGREE. **Owner:** tile §3.4 for codes and order; boundaries §6.1 for the stage definitions.
- **Refusal codes.** tile §3.4 defines the wire codes. fire_solid.md:380-389 §5.3 appends codes "to 5a's list", but no design doc holds a 5a list. checklists:113 only says codes are append-only. That is a dangling owner, not a contradiction. **Owner:** tile §3.4, or a core-codes section that fire_solid links to.
- **`regions_version` and the regions message.** DEFINES world_model.md:169-170 §5 ("bumps on every new region") and client_rendering.md:95, 104 §4.1. AGREE. **Owner:** client §4.1 for the wire; world_model §5 for id rules.
- **The `snapshot` reply and cadence.** DEFINES realtime.md:336-337 §7 (coalesced, rate-limited, "2 Hz … during any fire") and client_rendering.md:110 §4.1 ("at most `snapshot_hz`, plus a `snapshot` reply after `welcome`"). AGREE. **Owner:** client §4.1.
- **Single-owner items, no duplication:** `seq` range (realtime:325 only, in a superseded doc); the actor and pilots tables and `path_version` (tile §2.2, which client links to); `inference_status` (inference_gateway.md:258 §8 only, with client §4.1 to gain it at step 7); `time_decision` (tile §3.3/§3.4).

### C. Superseded docs that still DEFINE live wire contracts

- **realtime_lanes_coop.md.** Its header (:3) says it was superseded by world_v2. npcs §11.1 supersedes its §4.1–4.3 lane and order items. Still live and cited:
  - §5: the handshake, tokens and `TimeAuthority`. client §7.5 and boundaries §5.3 cite "lanes §5".
  - §7: closed schemas; `seq` in `[0, 2^31)`; `welcome`'s `actor` id and material table ("stay here until it is amended"); readers refuse an unknown version, kind, dtype or compression; axis order; compression off; and intent log v0 with `host_seq`, which boundaries §6.2 supersedes.
  - §4.1: `max_size` and `busy`.
- **world_v2.md.** world_model.md:4 says the trio replaces it. Still live: §8's frame grammar, extension and bump rules, and the "`extinguish` changes meaning" line. world_model.md:203 §8 says "v2 §8 stands", world_v2 §8 says "v1 §7 stands", and checklists.md:193 cites "world_v2 §8". So the live grammar rests on a chain of two superseded docs. §6's `host_seq` ordering is superseded only partly (npcs §11.2).
- **fire_model.md.** It is "direction, not build spec". It still DEFINES §5.4 (`kindle` target and deposit, the bridge's tool surface) and §9.2 (snapshot tables and channels). fire_solid.md:429 supersedes §9.2's names.

Two edits are already owed by Supersedes lists in the docs and were not made: architecture.md's buffer-cap and head-of-line text (realtime §8, world_v2 Supersedes) and client §4.1's `welcome` row (realtime §7).

This was a read-only pass: I changed nothing in the worktree.