## Contracts in the logging, replay, determinism and persistence domain that are stated in more than one place (worktree docs-contracts, read-only)

The worst problems come first. D = DEFINES, R = REFERENCES.

### Contradictions

1. **Scene v0 to v1 migration.** These copies DIFFER.
   - D `tile_and_client.md:79-80` §1.3: "v0 migrates by the literal `spawns: []` (F12)".
   - D `checklists.md:67-68` Step 3b: "scene v0 is refused by version, not migrated".
   - Owner: tile §1.3, since the tile owns the scene format. Delete the checklist's rule or move it there.

2. **Zones in scene v1.** These copies DIFFER.
   - D `world_model.md:232` §8 F13: "Scene format v1 is a strict loader (F13): zones, vents and gaps refused by path".
   - D `world_v2.md:84` §2.2: "Zones are authored in metres … in scene format v1".
   - D `tile_and_client.md:79` §1.3: "zones become v2 in Phase 2".
   - Owner: tile §1.3. world_model's F13 wording is ambiguous ("refused by path") and should link to tile §1.3.

3. **What save v0 holds, and how it loads.** Six versions, which DIFFER.
   - D `roadmap.md:23`: "the world grid plus the scene spec".
   - D `foundations_plan.md:35` row 9: "grid, scene, actor and pilots tables".
   - D `checklists.md:229-232` Step 9: "loading never replays the log; it stores a region table, not the scene file; a content change loads with a `content_changed` flag instead of refusing". This line says it "supersedes world_model §8 F5", so a plan is overriding a design.
   - D `world_model.md:213-215` §8 F5: "Embedded copies of the registry, scene and specs are compared … A save from a newer build is refused".
   - D `world_v2.md:366-369` §8: the save "embeds … the scene with its zones".
   - D `boundaries.md:435` §6.2: "a save is a checkpoint plus the log for the world".
   - D `realtime_lanes_coop.md:85-87` §2.1: "a `Simulation` checkpoint plus the log header … the thoughts in flight".
   - D `world_model.md:278` §10 row 11 and `world_v2.md:430`: save v0 "after the lanes, so in-flight thoughts are part of the saved `Simulation` state". This contradicts boundaries §6.2/§7 ("Agent state lives outside `Simulation`", :532) and the checklist's "No agent state".
   - R `tile_and_client.md:495`.
   - Owner: none fits today. Give the save format one design section, for example in world_model §8. The checklist should hold tests only.

4. **Fuel state in the save.** These copies DIFFER.
   - D `fire_model.md:419-426` §9.2: "Save and digest carry everything that is state: … inventories, front positions and latches".
   - D `fire_solid.md:73` §1.1: "An inventory is a `bincount` over nodes in key order, never stored". `fire_solid.md:406-417` §5.5 also lists the save tables.
   - Owner: fire_solid §5.5. It says it "follows fire_model.md v2 wherever it doesn't say otherwise", and fire_model is "the direction, not the build spec". fire_model §9.2 should point to it.

5. **Determinism tiers.** Three numberings, which DIFFER.
   - D `boundaries.md:463-468` §6.3: "1. Replay | the world, bit for bit … 2. Rerun | the world and the agents … 3. Live | the outcome class".
   - D `realtime_lanes_coop.md:266-271` §4.4: "2. Scripted runs are bit-identical at any dial and any pacing, with stub agents".
   - D `world_v2.md:259-264` §5: "2. Scripted runs whose inputs carry their ticks are bit-identical at any dial".
   - `npcs_and_sem.md` §11.1 supersedes only realtime §4.4's tier 3, so tier 2's old meaning survives in two docs, and world_v2's copy was never superseded.
   - R `npcs_and_sem.md` §4.4 (:414, :424), §6.6 (:825) and `sem_stimuli.md:289`. These use boundaries' meaning.
   - Owner: boundaries §6.3.

6. **The intent record's fields.** These copies DIFFER.
   - D `boundaries.md:407-412` §6.2 lists `schema_version, kind, actor_id, seq, observed_tick, issued_tick, apply_tick, apply_us, params, target`, with no `invocation`.
   - D `tile_and_client.md:194-200` §3.1 restates that list and adds: "An agent's intent logs Maxim's invocation pid as opaque `invocation`".
   - D `checklists.md:144-149`: "the intent record carries an optional, opaque `invocation`", with the null/stand-in refusal rules. The same rules are restated in `roadmap.md:149` and OD-A18 (:197).
   - D `realtime_lanes_coop.md:352-356` (v0 records `tick`, `host_seq`, …). Superseded.
   - Owner: boundaries §6.2. It needs `invocation` added, and the others should link to it.

7. **Ordering key.**
   - D `boundaries.md:427-430` §6.2: "stated here and nowhere else".
   - Restated but agreeing: `tile_and_client.md:196` and `npcs_and_sem.md` §9 (:1022).
   - DIFFER: `world_v2.md:291` §6: "sorts them by one total key, then assigns `host_seq`". It has no supersession note; npcs §11.1 and boundaries supersede only realtime §4.2 (`realtime_lanes_coop.md:219`, "`(tick, host_seq)` when the simulation lane takes it off its inbox").
   - The `kind_rank` values appear only in `checklists.md` 5a: "Intent kinds ranked 0/10/20/30". That is a contract held in a plan.
   - Owner: boundaries §6.2.

8. **The log header.** Its field list is split across at least six places, and the copies DIFFER.
   - D `boundaries.md:438-461` §6.3: content digests, the run seed, the engine SHA, `derivation_version` (singular), and "Python, numpy and scipy versions, `platform.machine()`, numpy's CPU dispatch features, the BLAS thread count".
   - D `world_model.md:240-244` §8: "every version: vocabulary, scene format, action limits, protocol, registry, materials; numpy, scipy and BLAS versions, the platform, and a dirty flag". The protocol and registry versions, BLAS *versions* and the dirty flag are missing from boundaries §6.3.
   - D `tile_and_client.md:278-281` §3.5: "gain the body archetypes, items, spawns, the vocabulary and `actions.yaml` versions, and the navigation constants".
   - D `sem_stimuli.md:282-285` §5: `STIMULUS_SCHEMA_VERSION`, lanes, id maps, truth constants. `checklists.md:121` restates the header slots.
   - D `npcs_and_sem.md` O45 (:74) and §6.6 (:838), plus `roadmap.md:197` and `:304-306`: the segment number and "the log's root id" are "recorded in the log header". boundaries §6.3 has neither; it names only "the run seed".
   - D `realtime_lanes_coop.md:350-352` (v0 header). Superseded.
   - D digest form: boundaries §6.3 ("SHA-256 over a canonical serialisation … sorted keys, fixed number format"), `world_model.md:244` (agrees), and `checklists.md:75` adds "`sha256/c14n-1:<hex>`".
   - Owner: boundaries §6.3, with the others as links or pointers to registered slots.

9. **Rerun manifest.** The earlier contradiction is mostly fixed. boundaries §6.3 (:455-460) now delegates "the inference items of `inference_placement.md` §4.3". One tension remains:
   - boundaries: "with the same refuse-on-mismatch rule".
   - `inference_placement.md:321-322` §4.3: "Recorded, reported and never refused, one entry per log segment: the placement table's digest and each segment cache's digest".
   - Agreeing R: `npcs_and_sem.md` §4.8 (:505) and §5.3 (:580, the syllabifier version).
   - Owner: boundaries §6.3 for the manifest, inference §4.3 for its items. boundaries should say its refuse rule has exceptions.

10. **Keyed randomness.** These copies DIFFER in scope.
    - D `boundaries.md:580-582` §7.3: "Per-NPC seeded streams … `SeedSequence(root, spawn_key=(NS_AGENT, npc_key, stream_key))`". This is unqualified.
    - D `npcs_and_sem.md:293-316` §3.4: that tree is "Overdrive's own streams; Maxim's derive by O40"; Maxim's streams are "a `random.Random` per stream from `make_agent_rng`".
    - D `npcs_and_sem.md` §6.6 (:834-837), §6.1 table (:620), O40 (:71).
    - D `roadmap.md:186` OD-A7: the `sha256(f"{base_seed}:{agent_id}")` formula, the ban on `:`, and `"npc_key:stream"`.
    - D `checklists.md:77-79`: the ban on `:`.
    - Owner: npcs §3.4. boundaries §7.3 omits the O40 split.

11. **Data timing at load.** These copies DIFFER.
    - D `checklists.md:74`: "Content stores time in world units (m/s, seconds), never ticks; ticks are derived at load".
    - D `npcs_and_sem.md:1020-1021` §9: "Timing data stays in microseconds and is never converted to ticks at load".
    - D `boundaries.md:583`: "Integer microseconds in `data/agents/`".
    - Owner: npcs §9.

12. **World config.** These copies DIFFER.
    - D `realtime_lanes_coop.md:89-99` §2.2: `tick_us`, `physics_every_ticks`, `day_length_ticks`, `epoch_us`, in `data/world/`.
    - D `world_v2.md:257` §5: "Everything `Simulation.step` reads is hashed world config: action limits, `max_age_ticks`, the stub's parameters …".
    - boundaries §6.3 says "truth constants" instead.
    - R `tile_and_client.md:467` ("realtime §2.2's `epoch_us`"). This treats the superseded doc as the live owner.
    - R `client_rendering.md:94` (`welcome` carries "the world config", undefined).
    - The `tick_us` value of 100,000 agrees across tile §6.1 (:381, owner T3), npcs §9 and realtime.

### Duplicates that agree, or add without conflict

13. **Record-kind vocabulary.**
    - D `boundaries.md:372-383` §6.1.
    - Kinds stated only elsewhere: `agent_ready`, `agent_failed`, `join` and `leave` reserved in `sem_stimuli.md:293-294`; `floor_event` and `reply_landed` host records in `npcs_and_sem.md:813, :824`; redaction records in O26 (:61). `world_v2.md:279-283` §6 is superseded by npcs §11.2.
    - Owner: boundaries §6.1. It is missing these kinds.

14. **`session_id` and pid rules (O43–O45).**
    - D `npcs_and_sem.md:838-840` §6.6, O43–O45 (:72-74), `roadmap.md:197` OD-A18, `roadmap.md:268-272` and `:304-306`, `checklists.md:372-379`. These agree once O45's amendment is applied.
    - The executor's `invocation_id` "is never the pid" is stated in npcs :807, roadmap :197 and checklists :148.
    - Owner: npcs §6.6.

15. **Response cache occurrence order.** `npcs_and_sem.md:826` ("numbered in canonical order (by thought request id)") and `inference_placement.md:292` agree. The cache "moved" to inference §4.2, so the npcs bullet is a leftover copy. Owner: inference §4.2.

16. **Thought request id `(tick, actor, n)`.**
    - Current: `boundaries.md:388` §6.1, "from the host's thought gate".
    - Superseded: realtime §4.2, "assigned by the simulation lane".
    - Not superseded: `world_v2.md:280`.
    - Owner: boundaries §6.1.

17. **Client timing fields refused, and `observed_tick` stamping.** Stated in `boundaries.md:340` §5.3 and `:250` §4.2, `tile_and_client.md:201-202` §3.1, and `npcs_and_sem.md:1023-1025` §9. They agree: "last cell frame" / "last frame sent", and `apply_us` 0. Owner: boundaries §4.2. `checklists.md:27` still asks to amend that wording.

18. **Tick order.**
    - `realtime_lanes_coop.md:82-85` §2.1 (superseded) has 4 steps.
    - `tile_and_client.md:169` §2.3 has 5, "(realtime §2.1)".
    - `sem_stimuli.md:143-145` §4.1 has 8, "amended by insertion".
    - These are compatible but triplicated. Owner: sem_stimuli §4.1, the newest.

19. **Runtime tripwire scope.** Three lists that don't cite each other:
    - `realtime_lanes_coop.md:273`: time, uuid, random.
    - `world_v2.md:265-267`: urandom, secrets, datetime, monotonic, numpy globals. No uuid.
    - `world_model.md:184-186` §6: a setprofile hook catching uuid4 and datetime.
    - The static banned list is boundaries §3 (:175-180), its owner.

20. **Version rules F1 and F15.**
    - D `world_model.md` §8 (:203-208, :239).
    - Restated in `sem_stimuli.md:291-296` §5 ("a new meaning gets a new name … bumps `derivation_version`").
    - Bump rules (registry vs protocol) exist only in `world_v2.md:357-358` §8, which world_model says "stands".
    - Owner: world_model §8. It should absorb world_v2 §8.

21. **Version fields.**
    - `topology_version`: D `world_v2.md:91` §2.2 ("`set_material`, which bumps"); R world_model §7 ("v2 §2.2"). `fire_solid.md:159` says `grid.destroy` bumps it, which is compatible.
    - `regions_version`: D `world_model.md:169` §5 (F10) and D `client_rendering.md:94-104` §4.1 for the wire. They agree.
    - `path_version`: tile §2.2/§2.3 only; client_rendering R.

### Superseded docs that still define things

- **`realtime_lanes_coop.md`** has a superseded banner (:3). It still defines world config (§2.2), tick order and the save (§2.1), tiers (§4.4), and the log v0 header and records (§7, :350). tile cites §2.1 and §2.2 as live, and `checklists.md:26` plans to amend its §7. npcs §11.1 supersedes only parts of §4.
- **`world_v2.md`** has **no superseded banner**; its status still reads "DRAFT, for a design review". world_model says it replaces it, yet says "v2 §8 stands" and cites v2 §2.2. Still live and unsuperseded: tiers (§5), world config (§5), `host_seq` ordering and request ids (§6), the save grammar and bump rules (§8), `topology_version` (§2.2), and save v0 ordering (row 9). npcs §11.2 supersedes only four §6 items.
- **Decision tables inside design docs**: npcs §0 O-table (O40, O43–O45), boundaries and world_model fold tables. These duplicate the contracts above, and B36 says such tables belong in reviews or indexes.

### Proposed owners

| Contract | Owner |
|---|---|
| Record fields, ordering key, record kinds | boundaries §6.1–§6.2 |
| Log header, tiers, rerun manifest | boundaries §6.3 |
| Manifest inference items, response cache | inference_placement §4.2–§4.3 |
| Streams | npcs §3.4 |
| `session_id` and pids | npcs §6.6 |
| Sub-tick and timing units | npcs §9 |
| Tick order | sem_stimuli §4.1 |
| Scene format | tile §1.3 |
| Fuel save tables | fire_solid §5.5 |
| Format and version rules | world_model §8, absorbing world_v2 §8 |
| Save v0 | no design owner today; needs one |
| World config | no live owner (superseded realtime §2.2); needs one |