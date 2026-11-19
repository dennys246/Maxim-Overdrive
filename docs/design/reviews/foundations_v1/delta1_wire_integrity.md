# Design review: foundations delta 1 (boundaries v3, NPCs and SEM v2, Maxim drafts), Wire integrity lens

- **Lens:** Wire integrity (every promised data path traced from source to consumer under O6; anything with no
  caller, no owner, a mechanism landing before its owner, or ids and names that disagree across documents)
- **Under review at commit 18623ce:** `git diff 4f7a754 18623ce -- docs/`: `docs/design/boundaries.md` (v3),
  `docs/design/npcs_and_sem.md` (v2), `docs/design/world_model.md` §10, `docs/design/realtime_lanes_coop.md` (banner),
  `docs/roadmap.md` Phase 3, every draft in `docs/maxim_upstream/`
- **Previous round:** `wire_integrity.md` in this directory (4 BLOCKER, 12 SHOULD-FIX, 9 NIT at 4f7a754)
- **Code surveyed:** `phase1/act-validation` at 2f200b5 (`tests/`, `sem_env/bridge.py`, `world/`)
- **Maxim read:** `origin/main` 7084f561 with `git show` (`utils/seeding.py`, `models/language/backend_protocol.py`,
  `runtime/tool_dispatch.py`)
- **Date:** 2026-11-16
- **Counts:** 2 BLOCKER, 12 SHOULD-FIX, 17 NIT (10 new, 7 carried from round 1 unaddressed)

O6 fixed the round-1 blockers at their root: no blocking `execute`, an intent sink as a required port, a host-owned
gateway, frames pinned per agent, a keyed seed path with an owner. The world half of the pipeline (client intent,
gate, log, applier, frame) now traces cleanly. The agent half still has two breaks. The first: **the call that runs a
thought is not on Overdrive's side of the contract.** `AgentPort` has `step` and `settle`. Maxim's draft has `think`.
Nothing says who calls `think`, on which thread, or how its tool calls, segments and receipts interleave with the
tick. The second: **the D53 valence has no carrier at settle.** Paths traced:

| Path | Verdict |
|---|---|
| NPC action: host `step` → `StepOutput` intents → stage 1 → log → applier → receipt → `settle` → cerebellum and NAc with D53 valence | sound to the receipt. Breaks at `settle`: `ModulatorReceipt` carries no valence (B2); receipt kinds and fields don't map (S2). Intents from inside a thought have no segment time (B1) |
| Player action: protocol → strict decoder → stage 1 → log | sound; the `act_result` binding is still unsaid (carried N-C1) |
| Percept: frame copy → adapter (pinned per agent) → `SensorReading` → Maxim, time stripped | sound on Overdrive's side; what Maxim's `step(world_dt_us, frame)` takes as `frame` is undefined (S2); `context_pool` waits on OD-A3, tagged correctly |
| Thought: request → host thought gate → gateway (stream, cancel) → budgets → segments at modelled times → cache → result | no call site for `think`; two request paths and two intent paths; a blocking `think` on the owner thread starves steps and settles (B1) |
| Speech: `speak` record → client as plain text with syllable stamps | streaming text can't be written to an apply-ordered log as one record; stamps aren't in the record; no client message (S4) |
| Dilation by cause → host meter and client clock | a producer and a UI, but no PR, no record format and no guard test (S5) |
| Time of day → SCN phase and the client's hour hand | no world epoch or calendar anywhere in Overdrive; "no calendar" contradicts "exact world phase after tier A" (S6) |
| Log header and rerun manifest | folded (rig, engine SHA, `derivation_version`, both material files, budgets, canonical digest); fields owned by later PRs (N6) |
| Per-NPC keyed RNG seed path | folded on Overdrive's side; the hand-off to Maxim's `make_agent_rng(base_seed: int, agent_id: str)` is unspecified (N9) |

## BLOCKER

### B1. The thought path has no call site: `think` is in Maxim's contract and nowhere in Overdrive's

`boundaries.md` §7.1 (the port table, the barrier, the host service protocol), §6.4; `npcs_and_sem.md` §4.2 (Pn),
§4.4 (no-deadlock invariant, "drives keep drifting"), §6.2, §6.3; `embeddable_agent_DRAFT.md` §4.1, §9

- **Overdrive's port** (`boundaries.md` §7.1) has two calls, `step(now_tick, dt_ticks, frame) -> StepOutput` and
  `settle(receipts)`. **Maxim's draft** (§4.1) has five: `step`, `think(request) -> ThoughtOutput`, `apply`, `settle`,
  `save`/`load`. No Overdrive document says who calls `think`, on which thread, or where `ThoughtOutput` goes. The
  draft leaves the hard part open (§9: "How tool calls inside `think` are answered: by a host callback, or by
  returning the tool call and resuming"), and Overdrive's design has picked the callback answer without saying so
  (`execute` appends to "the stepping agent's outbox", §6.4).
- **Two paths for each value, no rule between them:**
  - thought requests arrive as values in `StepOutput` *and* through `request_thought(request)` on the host service
    protocol the adapter calls (§7.1 table);
  - intents arrive as values in `StepOutput` *and* through the intent sink from `execute` during a thought.
- **No segment time for intents made during a thought.** `StepOutput` intents carry `apply_us`. An intent that
  `execute` puts in the outbox during `think` has none. Its time is the segment's landing time, which only the
  gateway knows (npcs §4.2: "computed by the host from the cost model"). The adapter has no defined way to read it.
  Round-1 B2's "no request context" survives here, for time if not for identity.
- **If `think` blocks on the agent's owner thread** (the barrier counts "waiting at the gateway for a held response"
  as parked, §7.1), three promised mechanisms break:
  - **Body time stops.** One owner thread serialises `step`, `settle` and pushes (§7.1). While it sits inside
    `think`, no scheduled `step` runs, so "drives keep drifting" (npcs §4.4) is false. Catching up afterwards with a
    larger `dt` is exactly what npcs §2.1 forbids ("`dt_ticks` is a pure function of the actor's rate divisor and
    phase, never of lag").
  - **Pn can't perceive its own act.** npcs §4.2's "think → act → perceive" needs the act's receipt settled and the
    frame re-pinned before the next segment. Neither can happen while `think` holds the thread. `execute` returns a
    pending, `neutral` result, so the next segment always reasons from the pre-act frame. A thought that strikes a
    door and then decides whether to strike again never learns the first strike worked.
  - **Pool starvation.** "One owner per agent … one agent-lane thread at a time" doesn't say one thread per agent.
    With a pool smaller than the NPC count, agents parked inside `think` hold every thread. A held response waits for
    world time, the world waits for every agent to park, and an unparked agent can't get a thread to step. That is
    foundations Arch B2's deadlock, moved from the thinking lane to the agent lane. npcs §4.4's invariant ("a worker
    is held only by an LLM call in flight") counts thinking workers, not agent-lane threads, so its test (one worker,
    two NPCs) can't see it.
- **Failure scenario.** `phase1/lanes` builds a four-thread agent lane. Five test-double NPCs each request a thought
  whose segment lands two ticks later. Four park inside `think`. The fifth's `step` at T+1 never gets a thread, the
  barrier never releases, and the world hangs under `dilate` with nothing past the wall ceiling to end it, because
  the ceiling counts LLM calls and none is in flight.
- **Fix.** Put thought execution on the port, resumably:
  - Add a host-called `think` to `AgentPort` (or a `ThoughtSession` with `advance(segment) -> SegmentOutput`), and
    take the draft's "return the tool call and resume" answer. Each segment returns to the host. The host applies the
    intents, settles their receipts, re-pins the frame and steps the body on schedule. Then it resumes the thought.
  - Make one path per value: thought requests only in `StepOutput` (drop `request_thought` from the service
    protocol, or say it is the adapter's internal plumbing for the same value), and intents only as returned values,
    each stamped by the host with its segment's `apply_us`.
  - State the agent-lane thread rule (one thread per agent, or "no agent ever parks holding a pool thread"), and
    extend npcs §4.4's deadlock test to the agent lane.
  - Carry the choice upstream as a decision for the embeddable draft's §9, with this scenario as the evidence.

### B2. D53 valence has no carrier at settle

`boundaries.md` §7.2 ("Valence per D53: the adapter always self-reports"); `npcs_and_sem.md` §6.1 (valence row),
§6.4; `propose_settle_amendment_DRAFT.md` §3.1, §3.2; Maxim `runtime/tool_dispatch.py` (D53 block, verified on
7084f561: `outcome_valence` is read from `side_effects`, and absent a report, `learn_valence = _V.POSITIVE`)

- The adapter's self-report is promised at settle, because under O6 the effect is measured only then. But the
  amendment's `ModulatorReceipt` carries the receipt id, an outcome kind, sensor deltas and
  `measured_drive_transitions`, and **no `outcome_valence`**. The propose-time result is `neutral` by design.
- The amendment says NAc credits a receipt "through the same D53 and measured-transition path as a synchronous tool".
  That path reads `outcome_valence` from `side_effects`, and a receipt fills no such slot. So NAc gets one of two
  valences:
  - **the D53 default, POSITIVE:** a strike on a steel door that destroyed nothing is booked as success, which is
    BF2-3's exact failure;
  - **the per-modulator default** (§3.2: "World modulators … declare it [`neutral`]"): every applied world action is
    neutral, including a strike that breached the wall. NAc then learns from world acts only through drive
    transitions, and a strike changes no drive.
- **Failure scenario.** At Phase 4 an NPC strikes a weak partition and breaks through. With the per-modulator
  default, NAc books neutral for the breach, the cluster gets no credit, and "strike weak walls to escape" is never
  learned. Without the default, it books POSITIVE for every strike on steel as well, so the NPC learns that striking
  works whatever it hits.
- **Fix.** Add `outcome_valence` (D53's vocabulary) to `ModulatorReceipt`, set by the modulator's settle-side
  measurement. Say how the adapter computes it from the receipt's before and after frames over the declared sensors.
  Make the amendment's PR 0 red gate assert both halves: a nil effect books neutral, and a real effect books what the
  modulator reports, not the default.

## SHOULD-FIX

### S1. The gateway lives in `engine.host`, but must be a Maxim `LLMBackend`, so the host would import `maxim`

`boundaries.md` §2.2 (layer 8: "the thought gate and LLM gateway"), §3 (agent step path "minus one named host-only
module (wall timeouts)"), §7.1, §8.1; `npcs_and_sem.md` §1 ("the LLM gateway's wall timeouts");
`embeddable_agent_DRAFT.md` §3 ("The host's gateway is an `LLMBackend`")

- Maxim calls the gateway as an `LLMBackend`, whose methods return Maxim types (`complete_with_usage -> LLMResponse`,
  and the new `Token` stream). B-2's `protected` contract lets only the named adapters import `maxim`. If the gateway
  is written in `engine.host`, the contract goes red the day `phase1/lanes` writes it. If the host is added to the
  allowed importers, B-2 has quietly widened.
- The wall timeouts are placed twice: in the agent adapter's host-only module (§3) and in the gateway in
  `engine.host` (§7.1, npcs §1).
- **Fix.** Split it in two. The host's gateway is engine-typed (requests and segments as `engine.intents` values).
  The Maxim-facing `LLMBackend` shim lives in `engine.adapters.agents`, built from the gateway handle the service
  protocol passes in. That shim is the gate-registry entry §5.2 names. Place the timeouts in one of the two.

### S2. Overdrive's values and Maxim's drafted values don't map

`boundaries.md` §7.1, §7.2, §5.3 (thought budgets); `npcs_and_sem.md` §4.7, §6.1, §6.4;
`embeddable_agent_DRAFT.md` §4.1, §4.6; `propose_settle_amendment_DRAFT.md` §3.1, §3.3; roadmap OD-A15

| Thing | Overdrive | Maxim draft |
|---|---|---|
| step | `step(world_dt, frame)` (O6, npcs §6.1, roadmap OD-A15); `step(now_tick, dt_ticks, frame)` (port) | `step(world_dt_us, frame)` |
| `frame` | an engine `Frame` of reductions | undefined: Maxim has sensors that are pulled and `world_set_axis` that is pushed, and no frame type |
| receipt kinds | `applied`, `refused`, `stale`, `cancelled` | `applied`, `refused_by_world`, `stale`, `cancelled`, plus `call_error` on the failure path |
| credit counts | once each, zero for `stale` | once for `applied`, zero for `stale` **and `cancelled`** |
| receipt body | measured effect (`destroyed_volume_m3`, `absorbed_j`), before and after frame ids | sensor deltas over declared sensors, `measured_drive_transitions` |
| over budget | `thought_failed(reason=budget)`, logged, the thought ends | the turn "returns what it has, marked `budget_exceeded`" |

- **Failure scenario.** The adapter forwards `refused` and Maxim's kind check doesn't match it. Or a cancelled intent
  is credited once on Overdrive's rule, and Maxim's exactly-once test fails on it. Or Maxim returns two intents with
  `budget_exceeded` and Overdrive logs `thought_failed`. Do those intents apply? Neither document says.
- **Fix.** One mapping table in npcs §6.1, with names taken from the drafts or changed in them: Overdrive's kind →
  Maxim's kind; who computes the sensor deltas (the adapter, from the two frame ids over the affordance's declared
  sensors); `stage-1 refusal` → `call_error`; `budget_exceeded` → `thought_failed`, with a rule for the intents
  already returned. Name the step argument's unit the same way everywhere. Define `frame` in the draft, or say that
  `step` takes no frame and percepts arrive only through pushes and pinned pulls.

### S3. Memory writes have no `apply` call, so after OD-A15 an NPC remembers nothing

`boundaries.md` §6.1 (memory writes "agent-side values in `StepOutput`"), §7.1; `npcs_and_sem.md` §6.2;
`embeddable_agent_DRAFT.md` §4.1 (`apply(memory_writes)`: "the only path by which writes reach the agent's stores")

- Generate vs apply means a write reaches Maxim's stores only when the host calls `apply`. `AgentPort` has no `apply`,
  and no document names who calls it, when relative to the barrier, or in what order across agents.
- **Fix.** Add `apply(memory_writes)` to the port, or state that the adapter calls it inside `settle`, at a stated
  point in the tick. Put the gate-to-be (§5.3) on that call.

### S4. Speech: a streamed `speak` can't be one record in an apply-ordered log, and the client has no message

`boundaries.md` §6.1, §6.2 (record fields; "the log is written in that order, so a replay never sorts"; bug reports
keep "lengths and syllable stamps"), §9.1; `npcs_and_sem.md` §5.2, §5.3; world_model §10 #6

- **Write order.** NPC speech streams, and other actors hear it and cancel on it syllable by syllable. A `speak`
  record that holds the full text exists only at the end of the stream. By then the log already holds records for
  later ticks, so the record can't go in at its `apply_tick` without a sort, which §6.2 rules out.
- **Stamps aren't in the record.** Stamps are "a pure function of the text and the NPC's state" (npcs §5.3), but
  replay never runs agents, so it can't recompute them. And the bug-report rule keeps stamps that §6.2's record
  doesn't have.
- **No wire to the client.** No document names the server-to-client speech message or registry channel that carries
  text and stamps. The protocol PR (#6) has `welcome`, `act_result` and `error`. Round-1 S5's "its frame channel"
  is still open.
- **Fix.**
  - Log speech per word, or per syllable group (a `speak_segment` kind with its stamps and an utterance id), in apply
    order.
  - Make the stamps logged input, not derived.
  - Name the client message and the PR that owns it.

### S5. Dilation by cause: no PR, no format, no guard

`boundaries.md` §3, §6.3; `npcs_and_sem.md` §5.4; world_model §10 #6, #10, #12

- It is measured in the host (lanes, #10) and drawn on the clock (part 3, #12). But no PR owns the "host status
  message" or its registry channel: #6 doesn't list it. It is filed under the log header (§6.3), though it's a time
  series. §6.2 says the log holds inputs, and this isn't one, so it has no record kind or side file.
- "Never read by the `Simulation`" has no test. A wall-derived number in the log, with no test that the core never
  reads it, is how outcomes end up depending on the wall.
- **Fix.** Pick a home: a side stream beside the log, or a non-input record kind that replay skips. Give the status
  message to #6 or #10. Add an import or AST check that the core never reads it.

### S6. Time of day has no world epoch, and "no calendar" contradicts "exact world phase after tier A"

`npcs_and_sem.md` §3.1 ("Overdrive declaring no calendar"), §3.3 ("Tier A only moves the phase's source to the
injected clock … exact world phase"), §5.4 (hour and minute hands show world time of day); `boundaries.md` §6.3;
`world_clock_release_DRAFT.md` §3.1 (`Clock.now()` is "world epoch seconds (the host persists its world epoch)";
`calendar(now) -> Calendar | None`)

- Overdrive's world time is `tick × tick_us` from zero. Nothing in the scene, the header or the save holds the world
  epoch or day length that the hour hand, the SCN phase and Maxim's `Clock.now()` all need.
- The draft's `None` calendar turns off weekly, monthly and annual phases, but whether the daily phase survives is
  unsaid. The `Calendar` type bundles day, week, month and year lengths. Overdrive wants a day and nothing else, and
  says both "no calendar" and "exact world phase".
- **Fix.**
  - Put a world epoch and day length in the scene or save, with a digest in the header.
  - Have the draft allow a day-only calendar, so that `None` means no phase at all.
  - Make npcs §3.1 say "no week, month or year" rather than "no calendar".

### S7. The draft still has no invariant tying `Clock` to the stepped dts (round-1 S1, half closed)

`boundaries.md` §7.3, `npcs_and_sem.md` §9 (folded Overdrive-side); `world_clock_release_DRAFT.md` §3.1, §7

- Overdrive now states that the injected clock advances exactly by the stepped dts. The draft, where the clock lives,
  doesn't say who advances an embedded `Clock` (the host, separately, or `step(world_dt_us)`), and no OD-WC test
  checks that the sum of the dts equals the change in `now_us`. npcs' fold table says "the draft's test is
  elsewhere", and it isn't anywhere.
- **Fix.** Add the invariant to the draft's §3.1, and an exit test OD-WC8 with k substeps.

### S8. `phase1/agents` (9b) relies on the gateway and barrier from `phase1/lanes` (#10)

`npcs_and_sem.md` §6.2 (the test double "runs through the real gateway, barrier and log"), §3.1 (dial-invisibility:
"a threaded host as shipped"); `boundaries.md` §5.3 (thought budgets, "the LLM gateway", lands `phase1/agents`),
§3, §10 (agent step path seal, "tripwire on the agent lane", lands `phase1/agents`), §11.1 ("the gateway's threads …
arrive with `phase1/lanes`"); world_model §10 #9b, #10

- 9b ships tests and gates whose mechanisms are born in #10:
  - the gateway and barrier the test double runs through;
  - the stream cut-off the budgets enforce;
  - the agent-lane thread the tripwire watches.

  Either 9b builds them early, so lanes doesn't own them, or the [now] tests can't run in 9b.
- **Fix.** Split by owner and say so in §11.1. 9b gets the types and a single-threaded synchronous gateway stub. #10
  gets the real gateway, the cut-off, the threads, the dial-invisibility test and the tripwire on the agent lane.
  Give the time-strip tests their rows in §10 (carried N-C6).

### S9. OD-A16 needs OD-C5, which is tier C, "after tier A"

roadmap Phase 3 (tier C heading; exit "OD-A16 has closed the stale-refusal divergence before Phase 4"); Phase 4
("Starts on tier A … OD-A1 to OD-A16"); `propose_settle_amendment_DRAFT.md` §3.1 (`settles`, "OD-C5, after OD-I2");
`sem_breaking_change_plan_DRAFT.md` §3 item 3 (OD-C5 "landing with the propose/settle amendment")

- The two drafts agree that OD-C5 lands with the amendment. The roadmap tiers it after tier A, and Phase 4's gate
  lists only OD-A1 to OD-A16. OD-C6 (reserved keys) has the same dependency: it goes with the amendment's extraction.
  So someone reading the roadmap would schedule OD-C5 and OD-C6 after the item that needs them.
- **Fix.** Move OD-C5 and OD-C6, with OD-I2, into tier A as OD-A16's prerequisites, or list them in Phase 4's gate.

### S10. The 2c write window has no sanctioned writer for construction or for test initial conditions

`boundaries.md` §4.1 ("Before `Simulation` exists": owners `World.advance` and the applier); act-validation 2f200b5:
`tests/test_heat.py:17, :42, :51`, `tests/test_snapshot.py:46, :71, :79, :83`, `tests/test_validation.py:126, :214,
:440, :489`, `tests/test_act_validation.py:239`; `world/grid.py:133, :160`

- In 2c "a write anywhere else raises". But construction in 2c is `World.from_scene` → `Scene.build` → `grid.paint`
  (`grid.py:133`), which the 2c paragraph doesn't name. And 13 test sites write grid arrays or region masks directly,
  including the closed-form heat test's Gaussian initial condition, which is the physics gate CLAUDE.md requires.
- **Failure scenario.** 2c lands, and `test_heat`'s closed-form test raises on `g.temperature[:] = …`. Someone opens
  `cells.writing()` in the test, which gives the window a fourth, unlisted owner. Or they edit the test to pass.
- **Fix.** Name construction (`World.from_scene` in 2c) as an owner. Give tests one sanctioned writer, an
  initial-condition parameter on construction (a temperature field, region overrides), so that closed-form setups
  build through it. Say what happens to `test_validation.py:214`'s "a later paint took every cell" refusal, a state
  that a direct mask write is the only way to reach.

### S11. Save v0's reason contradicts O6

world_model §10 #11 ("Save v0, after the lanes, so in-flight thoughts are part of the saved `Simulation` state");
`boundaries.md` §7.1 ("Agent state lives outside `Simulation`"); `npcs_and_sem.md` §4.4 ("Early-held results live in
the host's thought gate, agent-side. They are saved with the agent home (save v1)")

- Two owners are written down for one piece of state: in-flight thoughts are in the `Simulation` save (#11), and they
  are agent-side, saved with the home (v1). The #11 row was not updated with the O6 fold.
- **Fix.** Restate #11: v0 holds the world and the log position, plus the host's `thought_cancelled` and
  `thought_failed` records. In-flight thoughts are agent-side, and save v1 owns them. Then re-check whether v0 still
  needs to come after the lanes.

### S12. The interim time bins are tagged [after A], but they are OD-B9, tier B

`npcs_and_sem.md` §3.2 ("Until the senses are earned, a coarse interim readout … [after A, `[engineering]` ANALOG]");
roadmap OD-B9 (tier B); Phase 4 ("Starts on tier A")

- Phase 4 waits only on tier A. So Phase 4's first NPCs get no interim time sense, which BF2-7 calls worse than a
  coarse one: an LLM asked the time invents a precise answer.
- **Fix.** Move the interim bins (OD-B9's first half) into tier A, or tag them [tier B] and record in §12.2 that the
  first NPCs have no time sense.

## NIT

New:
- **N1. Stale ids remain.**
  - npcs §7.2 heading "per-part sensors after C8": now OD-C10.
  - npcs §12.2 "closes with SEM S2 and OD-A2": now OD-C2.
  - npcs fold table: Arch S14 "asks whether C2 gates Phase 4" (now OD-A16), and Wire S10's description ("§12.2
    closes two clocks with S2 and A2").
  - The drafts that go to Maxim still say "Overdrive's earlier item 16", "item 5", "item 11" and "P4"
    (`embeddable_agent_DRAFT.md` §3 and §4, `default_network_stepped_DRAFT.md`, `sem_breaking_change_plan_DRAFT.md`
    OD-C10). "item 16" is not in the roadmap's Was column.
- **N2. `SensorReading` stamping** is OD-A4 in the roadmap. `boundaries.md` §7.3 and §13 close the two-clocks
  divergence with "OD-C2 and OD-A2". OD-C2 is only the docstring, and it's tier C. Cite OD-A4.
- **N3. `hybrid_1_5_line_DRAFT.md` OD-H2** says the gateway "reports" modelled latency "(OD-A14)". OD-A14 is streaming,
  cancel and an inspectable request, with no latency report. Name where the modelled latency enters.
- **N4. npcs §10's "hybrid latency sweep"** is the hybrid draft's OD-HX2. Use the id.
- **N5. The header holds fields whose owners come later.** `latency_policy` and the pace table come from the host and
  the agents (#9b, #10), but the header is born with the log in sim-clock (#4). State the format version that adds
  them. The rerun manifest's "response cache digest", written beside the header at start, digests a file that grows
  during the run: digest it at close, or per entry.
- **N6. The thought request id `(tick, actor, n)` encodes the tick.** If it is passed into `think(request)` and Maxim
  stores it (a thought ref in memory), the tick reaches agent state. Give Maxim an opaque id, as receipts get one
  (§3.1).
- **N7. The world-clock draft's tripwire denylist (§3.3) is narrower than `boundaries.md` §3's.** It is missing
  `Random.seed(a=None)` and `random.Random()` with no seed, `SeedSequence()` with no entropy, `secrets.*`,
  `SystemRandom` and `threading.get_ident`. Round 1 asked to reuse Overdrive's list.
- **N8. The seed hand-off to Maxim.** `make_agent_rng(base_seed: int, agent_id: str)` hashes
  `f"{base_seed}:{agent_id}"` (verified). Say which int the host passes (one drawn from the `NS_AGENT` tree, or the
  root), and that `agent_id` is the roster's `npc_key`. `IdSource`'s `session` needs the same: who mints it for an
  embedded agent, and is it stable across saves?
- **N9. 9b changes `test_sem_bridge.py` again.** 2c keeps its strike-then-read without an edit. 9b makes `execute`
  only enqueue, so `integrity < 1.0` right after `execute` fails. Say that the test moves to host step, log, apply and
  frame. Say also that `execute` with no stepping agent is refused, not appended to an outbox nobody drains.
- **N10. What is logged at the edges.** Is a stage-1 refusal inside `execute` (a `call_error`) logged? §6.2 logs
  refused intents for their world dependence, and a stage-1 refusal has none. And does an intent already returned by
  a thought that later ends as `thought_failed` still apply?

Carried from round 1, not addressed (neither fold table lists Wire NITs):
- **N-C1 (was N1).** A client intent's receipt is the `act_result`; say so, and say when a stage-2 refusal at a later
  tick is sent, and to which session.
- **N-C2 (was N3).** `check_markers` checks the phase number, not the step. Markers now name `phase1/agents` and
  `phase1/sim-clock`, so each of those PRs should assert at its exit that none of its markers remains.
- **N-C3 (was N4).** "Replay recomputes them and checks them against a per-tick digest" (§6.2): the digest is in
  neither the record nor the header.
- **N-C4 (was N5).** W1's rebase evidence was for a whole-package rename. Re-run it for the split across layers, and
  have §11.3's check list every file git relocated by inference.
- **N-C5 (was N7).** "P" ids still collide: the thought phases P0–P3 and Pn, and the roadmap's Was column (P2, P3,
  P4, P6, P7).
- **N-C6 (was N8).** The schema, prompt, dial-invisibility and Δt tests have no row in §10's table.
- **N-C7 (was N9).** `data_dir()`'s refuse-loudly test covers `data/` only. `content/` needs the same.

## Did round 1 close?

| Round 1 | Status at 18623ce |
|---|---|
| B1 window and frames before `Simulation` | **closed** (§4.1, §11.1: named owners, TEMPORARY(sim-clock), the applier publishes). New gap: construction and tests (S10) |
| B2 mode (a) can't reach the pipeline | **closed** by O6 (intent sink port, the factory takes no `World`, reach and centroid checks in the applier). Segment time for intents made during a thought is still missing (B1) |
| B3 no thought entry point | **partly closed**: the gateway exists, and `step` before tier A is the test double with real Maxim red. But `think` has no call site (B1), and the gateway's layer is wrong (S1) |
| B4 `AgentTime` can't reach the stamps; `HostClock` | **closed** in the draft (explicit pass, defaults kept, tripwire; `now()` in epoch seconds read at call time; OD-WC5 loads a pre-release home) |
| S1 three time inputs, no invariant | **half**: Overdrive side folded; the draft has neither the invariant nor a test (S7) |
| S2 tripwire misses; `Rng` default | **closed** (profile hook, wider denylist, global `random` default); a residue in N7 |
| S3 seed path owner; counter keying | **closed** (host owns it; keyed by `(npc, stream, tick, sensor)`; Philox and CLAUDE.md drift listed); the Maxim hand-off is N8 |
| S4 record fields and kinds | **closed** (`apply_us`, one key, `thought_cancelled` and `thought_failed`, `memory_write` out, intent id `(actor_id, seq)`) |
| S5 speech has no wire | **partly closed**: the kind, the gate and logging. The streaming write order, the stamps in the record and the client message are open (S4) |
| S6 which frame; leaks | **closed** (pinned per agent; the `timestamp` exemption; `cell_size_m` dropped) |
| S7 dilation channel | **partly closed**: "the core never reads it" and the client message are stated. No PR, format or guard (S5) |
| S8 header inputs | **closed**; the world epoch is missing (S6), and timing and the cache digest are N5 |
| S9 response cache | **closed** (registered gate, [after A], never read by replay) |
| S10 stale Phase 3 ids | **mostly closed**; stragglers in N1 and N2 |
| S11 §9.3 vs the SEM plan | **closed** (OD ids, OD-C6 and OD-C7 added, the stale note removed) |
| S12 settle double credit | **closed** (one path); but the valence at settle has no field (B2) |
| N1–N9 | N2 closed (opaque receipt id); N6 closed (lanes banner); N1, N3, N4, N5, N7, N8 and N9 carried (N-C1 to N-C7) |

## What I checked and found clean

- **Client intent path:** strict decoder, host-stamped `observed_tick` and `apply_us = 0`, refused client time
  fields, stage 1, log in canonical key order, stage 2 (`boundaries.md` §4.2, §5.3, §6.2; npcs §9).
- **The world half of the NPC path:** the gate half in `adapters.sem` with no geometry, the reach and centroid
  checks as stage-2 checks, per-actor binding and the refusal of a mismatched actor, one receipt per intent with
  before and after frame ids, the frame cadence that guarantees an after-frame on the apply tick.
- **Percepts on Overdrive's side:** frames as copies published on change, the pin per agent, noise from per-NPC
  streams, the push as a pure function of the pinned frame, `cell_size_m` dropped.
- **Ids across documents:** OD-I1, OD-I2, OD-A1 to OD-A16, OD-B1 to OD-B13, OD-C1 to OD-C10, OD-H1 to OD-H4,
  OD-X1 and OD-X2, OD-HX1 to OD-HX5, OD-WC1 to OD-WC7, OD-EA1 to OD-EA9 and OD-DN1 to OD-DN3 are unique and consistent
  between the roadmap, the README index and the drafts. OA1 to OA5 are defined once (npcs §0) and cited consistently.
  The Phase 3 exit's OD-WC1 and OD-EA5 exist.
- **Maxim citations spot-checked on 7084f561:** `make_agent_rng`'s signature and its SHA-256 derivation;
  `LLMBackend`'s three `supports_*` flags; D53's silent POSITIVE in `tool_dispatch.py`.
- **PR order on the world side:** 2b → 2c → verify → sim-clock → agents → lanes. Each world mechanism (the window,
  frames, the log, `observed_tick`, the tick, the tripwire) lands in or after the PR that owns it. The exceptions
  are on the agent side (S8) and in save v0 (S11).
