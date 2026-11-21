# SEM stimulus design review: Wire integrity and Trust boundary

**Reviewed:** `docs/design/sem_stimuli.md` at `3357439` (`phase1/sem-stimulus`), with `research/sem_stimuli/`. I read
the charter, CLAUDE.md, `boundaries.md` §4, §6, §7, §9, `world_model.md` §6 and §8, `realtime_lanes_coop.md` §2,
`npcs_and_sem.md` §6.4–§7.4, `tile_and_client.md` §2.1, §3.1 and §4, `pyproject.toml`'s import contracts,
`tests/test_tooling_config.py`'s surfaces, and `frames.py`, `applier.py`, `adapters/sem/`, `protocol/`. I read Maxim
with `git show origin/main` at `043eab8f` and did not fetch it.

**Counts:** 3 BLOCKER, 12 SHOULD-FIX, 8 NIT.

**Claims checked and true:** at Maxim `043eab8f`, `world_set_axis` is root-only, NaN becomes `hi` and is written raw
with no range, and `owner=` is not an ACL. Also true: `bootstrap.py:552-561`, `spec.py:290`, `:556` and `:820-823`,
the materials-hole statement, and `bridge.py:48`.

## 1. Contract table

| Contract (type) | Producers, before → after | Consumers, before → after | What each consumer gets, before → after |
|---|---|---|---|
| Stimulus row schema (vocabulary, persisted via header) | none → `core/stimuli/schema.py`, `models/*` | none → runner, header canonicaliser, handshake name maps, D2's generated artifact, the worker's binding check, the agent-home registry digest, T10, T14, the §7.4 lints | nothing → name, unit, validity, receptor, site set, cadence, tag, reads, `derivation_version`. Validity is defined only for temperature (S8). |
| Unit vocabulary (vocabulary) | Maxim free text; `frames.QUANTITIES` units → a closed list "shared with the field registry", which doesn't exist yet (5a) | the worker's binding check, which compares strings exactly with Maxim's YAML `unit` | Maxim's thermal drives use `celsius_norm` on [-1, 1] (`infant_humanoid.yaml:43-46`), which no `celsius` row can bind to (S9) |
| `BodyFrame` (payload, then wire) | none → `stimuli.run` (core), encoded by the host | none → the worker adapter, the stimulus digest, the save's recompute check | id/value columns, `npc_key`, `tick`, `basis_sequence`, `events`. `StimulusEvent` is undefined, and carries no `caused_by` (S2) and no time base (S3). |
| `AgentPort.step`'s `frame` (call, O19, D1) | `boundaries.md` §7.1 / npcs §6.6: a pinned frame plus events carrying `caused_by`; tile §4: the bodies part with the actor table → a `BodyFrame` | Maxim's embedded `step(agent, world_dt_us, frame)`; the staleness rule, which needs tracked-right events | before: a frame source and the pinned actor table. After: neither, and the design doesn't say so (S1). Tracked-right events have no row. |
| Site frame and body grammar (persisted, game data) | tile §2.1's 5b body (cylinder, a lumped 245 kJ/K store, `body_key`) → `core/body/geometry.py`, `sites.py`, `store.py`, `tissue.py` | tissue law, stimulus models, the header's site tables, the save | two body models with no owner named between them (B3) |
| Binding (persisted, gate) | none → per-NPC data, checked at worker build | the worker's push; the rerun manifest | stimulus, sites, reduction, sensor. The checks are incomplete (S9), and the loader has no gate row (S11). |
| Push to Maxim (call) | the DoA feed and the Minecraft backend → the Overdrive worker adapter via `world_set_axis(owner=)` | `vital_metrics`, then drives, pain and the substrate | `True` even when the value is clamped. `False` ends the agent (§4.3); the writes before it have already landed (N8). |
| `live_world_set_sensors` (gate) | `build_executor`'s modulator-backend loop → an Overdrive modulator backend that is "shipped" but never specified | `world_set_axis` refuses anonymous writes; `tool_bridge` filters `self_effect` and withholds credit | this depends on a build path the embedded agent may not take (S10) |
| Stimulus digest and header (persisted) | none → per-tick `stimulus_digest`, plus the registry, site tables and tissue constants in the header | replay, rerun refusal, the save-load check | defined as both "canonical(BodyFrame)" and "the bytes sent" (S7) |
| Registry, `STIMULI` (vocabulary) | none → `core/stimuli/registry.py` | header, handshake, agent home | row-add rule 3 and agent-home rule 5 contradict each other (S6) |
| NPC builder (call, capability) | npcs §6.5: per-actor entity and modulator from a frame source → `(npc_key, body-frame source, outbox)` | Maxim tool generation, discovery and prompt formatting | the environment's entities have no construction path (S1, S5) |
| Lab builder (call) | `region_parts`, `to_maxim_entity`, `RegionInstrument`, `StructureModulator` in `adapters/sem/bridge.py` → moved under `tests/` (D10) | 9 test modules; `to_maxim_entity` (shipped) calls `region_parts` | `tests-out` forbids shipped code importing `tests` (S5) |
| Receipts and refusals into the NPC (payload) | `Applier` `Outcome` → `StructureModulator._from` → npcs §6.6's two projections, unchanged | `settle` credit; the follow-up prompt ("outcome kind and measured effect") | `absorbed_j`, `destroyed_volume_m3`, and stage-2 refusal text. No stimulus test covers them (B1). |
| Import contracts (gate) | `skip-layer`, `membrane-reads-frames` → plus §7.3's six | the gate's `lint_imports`; `test_tooling_config` surfaces | `adapters.agents` may still import `world`, `applier`, `frames` and `bridge` (S4) |
| Tick order (lifecycle) | D10: records → agents → physics → outputs → "stimuli after every law at T", with the tissue law every tick | `Simulation.step`, the barrier | contradicts D10 (B2) |

## 2. BLOCKERs

**B1. `sem_stimuli.md::§6 Trust` claims one channel, and the receipt channel carries privileged state that none of
the 14 tests exercises.**
The design states that "the NPC builder gets one NPC's frame source and nothing else, and fourteen tests ... hold
it." But the outbox's return path reaches the NPC through `settle` and through the follow-up prompt. The prompt
projection is "outcome kind and measured effect only" (npcs §6.6, "Receipts have two projections"). Today that path
carries:
- `Applier._strike`'s `absorbed_j` and `destroyed_volume_m3`. These are instrument values, and they depend on material
  strength and density. This is exactly what T5 forbids, and it arrives *before any thermal event*.
- `Applier._extinguish`'s "nothing is burning on the {region}". This is a fire-state oracle for a region the NPC may not
  see. T4 forbids exactly this for stimuli.
- `_check_region`'s "there is no {x} in this world" and "the {region} is gone". These are existence oracles keyed by
  name.
- `_strike`'s "point_m is not on the {region}". A bisection over `point_m` recovers the footprint bounds in metres,
  which is occluded geometry.

T7 is a word denylist, so it cannot see a fact. The scenarios of T4, T11 and T12 issue no intents, so their byte
scans never contain a receipt.

*Failure:* NPC A strikes a crate behind a wall and learns its absorbed energy (a material constant). A asks to
extinguish the vault fire and learns whether a fire it cannot see is burning. All 14 tests stay green.

*Fix:* bring receipts into §6. The NPC projection should be a closed refusal-kind vocabulary, with the measured effect
limited to what the NPC's own receptors register. Then run T4, T5 and T11 over receipt bytes with intents issued, and
give T12 a sentinel in `absorbed_j`. Alternatively, record each of these as a named ANALOG with a red gate.

**B2. `sem_stimuli.md::§4.1 step 1` and `§2.4` contradict the frozen tick order.**
- D10 (`realtime_lanes_coop.md` §2.1) and `tile_and_client.md` give the tick as "records, move bodies, **agents,
  physics**, outputs".
- The design builds frames "after every law at tick T" and steps agents at T "with the frame computed at that tick".
- On a physics tick, either the agent steps before its frame exists, or the agent sees the previous physics state.
  The design says neither. Silently reordering the tick would reverse D10.
- The tissue law "integrates every tick", which adds a per-tick law step that D10's order doesn't have.

*Failure:* the `phase1/agents` implementer picks one of the two readings. A frame stamped `tick = T` then holds
fields from T−5. The dial can't expose this, but replay digests encode whichever choice was made.

*Fix:* state where the tissue law and `stimuli.run` sit in the tick, and which tick's frame an agent stepping at T
receives. Amend D10 by name if the order changes.

**B3. `sem_stimuli.md::§3, §7.1` (body store, tissue law) duplicate `tile_and_client.md` §2.1's world-owned body,
with no owner ruled between them.**
Step 5b already designs one body model:
- a lumped 245 kJ/K heat store;
- flame radiation by a point source onto 0.5 m², debiting the unreceived-flame ledger line;
- convection over an exchange volume, with a `bodies` ledger line;
- a persistent `body_key` that "can serve as an NPC's key".

This design adds Pennes columns per skin point that absorb "flux onto skin", plus a `core_temperature` "from a body
heat balance". It never cites `tile_and_client.md`, and it names `npc_key` in place of `body_key`.

*Failure:* the flame's radiant energy is debited once by the lumped body and again by the skin columns, or by neither.
The energy ledger breaks. Two "body temperatures" exist, and `core_temperature` has two producers, which breaks
"one owner" (`fire_model.md` §5.1, as the design itself cites).

*Fix:* add a supersedes row against `tile_and_client.md` §2.1. Name one producer for body heat, and one ledger line
debited by the skin columns. Rule that `npc_key` is `body_key`.

## 3. SHOULD-FIX

**S1. `§6.1 Capabilities` silently supersedes four standing contracts.**
- `boundaries.md` §7.1 and npcs §6.5: "the membrane factory takes a frame source".
- `boundaries.md` §4.2 and npcs §7.3: a frame "pinned per agent", which Maxim's pulls read.
- npcs §6.5: "each NPC gets its own entity and modulator". `StructureModulator.__init__` needs a `FrameSource`.
- `tile_and_client.md` §4: "an adapter's pinned actor table", with every actor's position, as an ANALOG direct view.

The last is privileged state reaching the adapter, which §6.1 says can't happen. *Failure:* `phase1/agents` follows
npcs §6.5 and hands the factory a frame source, or the pinned actor table. Every T-test still passes, because each
tests only the `BodyFrame`. *Fix:* a supersedes list. Either rule the actor table out of the NPC path, or list it as
an ANALOG with T8 and T11 covering it.

**S2. `§4.1 BodyFrame.events` has no cause field, and the npcs codec's rule would leak another actor's identity.**
npcs §6.6 says each event "that an intent caused carries it as `caused_by`". `tile_and_client.md` §3.1 calls the same
thing `cause = (actor_id, seq)`. In A's frame, an event that B's intent caused would then name B's actor id and how
many intents B has sent. The efference copy and the "non-self-caused" staleness test need only A's own pids. *Fix:*
carry the cause only when the event was self-caused, and send null otherwise. Add a T11 variation in which B acts in
A's view. Settle one name: `cause` or `caused_by`.

**S3. `§4.1 events ... by (apply_us, id)`, and §2.3's integer-µs arrival times.**
- `apply_us` is the offset *within* a tick (`boundaries.md` §6.2). Events gathered since a step two or more ticks back
  therefore sort tick T−2's 90,000 µs after tick T−1's 10,000 µs: the wrong order whenever the rate divisor is above 1.
- `apply_us` is also on `boundaries.md` §7.3's strip list, and that section's schema test exempts only
  `SensorReading.timestamp`. So either the test goes red, or arrival times are stripped and interaural timing is lost.

*Fix:* stamp each event as an int64 offset from the step's start, sort by `(offset, per-NPC local id)`, and name it as
the second exemption. Define `id` as local to the NPC. A global event counter would reveal activity elsewhere in the
world.

**S4. `§7.3 Import contracts` dropped L5's ban.**
L5 §5 forbade the NPC builder importing `Frame` and the bridge's lab classes. The design keeps only
`agents-no-materials` and a stimuli-scoped `membrane-reads-stimulus-frames`. `skip-layer` still lets
`simcore.adapters.agents` import `world`, `applier`, `frames` (with `QUANTITIES`) and `simcore.adapters.sem.bridge`. The
existing contracts set `allow_indirect_imports = true`. If the new one copies that, it bans direct imports only:
`stimuli.schema`, which shares its units with the field registry, could pull in `materials`. *Fix:* add an
`agents-reads-body-frames` contract that forbids `world`, `applier`, `frames` and `adapters.sem.bridge`, held by
`test_tooling_config` the way `MEMBRANE_SURFACE` is. Until D10 is ruled, nothing keeps the builder off `region_parts`.

**S5. `§10 D10` is scoped wrong.** Moving `region_parts` under `tests/` drags `to_maxim_entity` with it, because that
shipped function calls `region_parts` and `tests-out` forbids shipped imports of `tests`. It also leaves
`StructureModulator` and `ENTITY_SOURCE` with no shipped caller. And the NPC's way to act on a wall becomes undesigned.
npcs §6.6 says targets arrive at the host "as a stable id", but nothing builds the worker-side entity they name. That
entity's names, affordance descriptions (which carry `ActionLimits`) and refusals are the identity and text leak
surface. *Fix:* design the worker-side environment entity: what it carries, built from what. Put T8 and T13 over it.

**S6. `§5 Version rules 3 and 5` conflict.** Rule 3 says adding a row is non-breaking. Rule 5 says an agent home
records "the registry digest it trained on" and is refused under another one. Adding any row changes that digest, so
every saved NPC is refused after an unrelated sense ships. *Fix:* digest only what the agent consumes: its bindings'
rows, units, site sets and `derivation_version`s.

**S7. `§5 Digested every tick`** says both "canonical(BodyFrame)" and "over the bytes sent". The worker codec's named
cost lever is "frames go as deltas" (npcs §6.6). Under that, the bytes sent are not the frame, and a codec change
moves the digest with no stimulus change. *Fix:* digest the canonical value through `checks`' one canonicaliser, and
keep the transport out of it.

**S8. `§2.1 valid` and `§4.3 NaN can't cross` handle malformed values incompletely.**
- "The core raises" has no scope. Raised inside `Simulation.step`, it takes the whole world down because of one NPC.
  The codebase already returns NaN from an empty reduction (`frames.py::Frame.reading`, `temps.size == 0`), and a pose
  that overlaps a solid, or a skin patch with no air, is the same shape.
- Validity is given for temperature only. For the ratio rows, [0, 1] plus float rounding (an area sum of 1 + ε)
  either raises or passes. Neither is stated.
- "Each proven by a planted NaN" doesn't reach `1e400`. `json.loads` turns it into `inf` without `parse_constant`.
  `boundaries.md` §9.1 lists it, but this design's proofs don't.
- The worker's re-check must refuse `bool`, because `float(True)` is 1.0 and `world_set_axis` calls `float(value)`.

*Fix:* give each row an empty-reduction rule and a validity range with a rounding policy. Name the raise's failure
class (a world bug, loud, with the tick logged). Plant NaN, ±inf, `1e400`, `true` and an empty patch.

**S9. `§4.2 Build-time checks` don't cover the Binding's own invariants.** Nothing checks that:
- `stimulus` names a registry row;
- `sites` lie inside both that row's site set and the body;
- `single` has exactly one site;
- an `area_mean` doesn't average across depths, since `tissue_temperature` is points × depths.

The grammar also has no unit transform. Maxim's thermal drives are `celsius_norm` on [-1, 1] with set point 0
(`infant_humanoid.yaml:43-49`), so a `celsius` row can bind to no existing Maxim thermal drive. That is M2's neutral
point again, now at the binding level. The binding file is a new loader and needs a gate-registry row.

**S10. `§4.2 live_world_set_sensors`:** "Overdrive ships one" modulator backend.
- That backend receives every `execute` of the body modulators it is attached to (`attach_backends`), so it *is* the
  outbox path. It is a call contract with no specification.
- It registers only through `build_executor(modulator_factory=...)` (`bootstrap.py:538-561`). Whether Maxim's embedded
  entry (OD-A10) runs that path is unknown, so it belongs on the M-table as a question.
- §2.1's "the world meters how often the clamp bites" has no owner. The core never sees the YAML range, and
  `world_set_axis` returns `True` when it clamps. Assign the metering to the worker adapter.

**S11. `§4.1 step 2–3`: the wire contract lacks its required checks.** CLAUDE.md requires wire formats to have a round
trip plus golden fixtures, and trust boundaries to cover every rejection path with a gate row. The design lists
neither for the `step` message's `BodyFrame`. Also missing:
- the worker checking `npc_key` against its bound actor (the channel binds actor ids, and the frame carries only
  `npc_key`);
- a catalogue or registry hash on the frame, by `world_model.md` §8's rule that "a frame whose catalogue hash differs
  from `welcome`'s is refused". As it stands, a stale handshake name map decodes silently to the wrong rows.

**S12. `§6.2 T9, T11 and T12` have gaps in scope and in their plants.**
- T12's plant, "bind B's site to A", can't be expressed. A Binding names sites inside A's own body, and two NPCs of
  one archetype share site ids. The plants must be a core misroute (A's frame built from B's store) and a host channel
  misroute.
- T11 compares A's `BodyFrame`, not A's agent state. A remote fire raises host load. Maxim's wall-clock machinery
  (M5–M8: drift, the refractory, stamps) then gives A different dynamics, so remote world activity leaks into A.
  T9 varies LLM latency only, so name host load as a known leak until D3 lands.

## 4. NITs

- **N1.** §6.2's "T1, T2" (ownership) reuses §1's T1 and T2 (instrument, transduction). Renumber one set.
- **N2.** `basis_sequence` (a Frame sequence) sits next to npcs' `basis_seq` (Maxim's afferent high-water), which
  means something else. `tile_and_client.md` §4 also makes frame ids ticks, so `tick` and `basis_sequence` may be
  redundant.
- **N3.** `tick` is called a "host-owned header, stripped before Maxim", yet it crosses the channel. Say that the
  worker checks it is monotonic and then drops it.
- **N4.** `events` has no v1 producer and no Maxim push path, since `world_set_axis` is scalar. It is a field with
  no caller.
- **N5.** "No API takes two `npc_key`s" is false for `stimuli.run` and for the digest. Scope it to the NPC-facing API.
- **N6.** Classify `simcore.core.stimuli`'s `__init__` in `CORE_PUBLIC_SURFACE`.
- **N7.** Maxim's loader passes unknown YAML keys into entity metadata (`spec.py:429`). Say whether the site tables
  live in the "Maxim-format" body file, which would put them in metadata, or in a separate Overdrive file with its
  own strict loader.
- **N8.** When a `False` arrives mid-push, the earlier bindings are already in `vital_metrics`. Require that no save
  follows before the agent is ended, or validate everything before any write.

## 5. Does each leak shape have a test that catches it?

| Leak shape | Caught by | Gap |
|---|---|---|
| Region instrument on the NPC | T13, T14, T8 (if the scan includes environment entities) | the builder ban was dropped (S4); D10 is unruled (S5) |
| Material constant | T5, T6, T12 (verbatim copies only) | receipts' `absorbed_j` (B1) |
| Another NPC's stimuli | T11, T12 | T12's plant can't be expressed (S12); `cause` (S2) |
| Entity identity | T11 (ids, allocation order) | `cause` (S2); event ids (S3); the actor table (S1) |
| Outcome text | T7 (word denylist) | factual refusals (B1) |
| Time | T9, and `boundaries.md` §7.3's strip test | event µs (S3); host load (S12) |
| Malformed values | planted NaN at three layers | inf, `1e400`, `bool`, empty patch; raise scope (S8) |
