# Architecture lens: the agent half, v3 (commit 3db82a8)

Reviewer: Architecture lens (Overdrive). Read: `npcs_and_sem.md` v3 (all of it), the `boundaries.md`, roadmap and
`embeddable_agent_DRAFT.md` v2 diffs in 3db82a8, `reviews/maxim_response_1/` (`response.md`, `response_2.md`,
`architecture.md`, `synthesis.md`, the fold table), `world_model.md` §10, `docs/code_review.md` ("Design reviews").
Maxim `origin/main` 7084f561 was read with `git show` to spot-check the citations below.

**Counts: 2 BLOCKER, 10 SHOULD-FIX, 7 NIT.**

The verdict first. Deleting the host service protocol was right: the callback ran the wrong way, and with requests as
values it is gone without a trace in the port. No callback from the adapter to the host is left. But the contract
is only half written. The port lost `apply`. Nobody owns the continuation (the host, the agent and an "opaque blob"
each do, depending on the section). The lifecycle from a thought request to a follow-up is never written end to end.
O13 moved Maxim into a worker process without re-cutting the world half's gate registry and sealed set. Maxim also
has model calls outside the planning path, so there are second doors to a model the design doesn't mention.
§12.1 item 6 is framed toward dilate: it misdescribes abandon and leaves out the option closest to O11.

## Fold faithfulness

I checked every row of the prior Architecture lens (`maxim_response_1/architecture.md` 1.1–4.6 and its §5 list)
against where the fold table says it landed. All but two landed as claimed:
- **Arch 2.3 is marked folded, but only half landed.** The `basis` is in §6.1. The second half of the finding,
  that the receipt's `stale` kind and Maxim's answer-staleness need one vocabulary, appears nowhere, and what resume
  does when the basis is stale is never stated (S1). It should be **partial**.
- **Arch 4.4 landed, but it now conflicts with §4.2** (S5). That is my own earlier finding coming back: an
  agent-supplied deadline is a second source of time.
- The §5 list's targets all landed (§4.2 P1c row, §4.4 invariant, §4.5 table and meters, §4.7, §4.8, §5.2, §6.1,
  §6.2, boundaries §7.1 and §7.4, draft PR 4 withdrawn, roadmap OD-I1–I4, OD-A12 ConceptExtractor, OD-A15 robot
  driver). Spot-checked citations hold on 7084f561 (`agent_loop.py:2172` `ActionFollowup`; `bio_stack.py:654`
  `start_background_workers`).
- Stale text left by the fold is S10 and N5.

## BLOCKER

### B1. `AgentPort` has no `apply`, so generate-vs-apply has no host-called writer (§6.1, §6.2; `boundaries.md` §7.1)

§6.1 says "`apply` and `settle` the only writers", and the draft's §2 table has `apply(agent, writes)`. But the port
that §6.2 builds and `boundaries.md` §7.1 defines is `step` / `think` / `settle`, with no `apply`. Memory writes come
out of `StepOutput` (and presumably `ThoughtOutput`), and the gate table (`boundaries.md` §5.3, "Thought results …
memory writes") calls them a gate-to-be that the host checks. Nothing in the contract says who puts a checked write
back into the agent, or when.

**Failure scenario.** `phase1/agents` implements the double from §6.2. A `ThoughtOutput` carries a memory write.
The port has no way to hand it back, so the adapter applies it inside `think` or `step` "for now". The write never
passes the host gate (TB2-S3's gate can't exist), it lands at a wall-ordered point inside the worker rather than at
a tick in canonical order (§9), and OD-EA4 ("no store changes until `apply`/`settle`") has no host-side twin to test
against. Memory authority (§12.2) then can't close even after Maxim ships OD-A18, because the port has no slot.

**Fix.** Make the port `step` / `think` / `apply` / `settle`, with `apply(writes)` called by the host at a stated
point in the tick (after stage-1 checks, in canonical order). Say whether `ThoughtOutput` carries writes or only
intents, and list `ThoughtOutput` and the continuation type in `boundaries.md` §2's layer 5b.

### B2. The deliberation continuation has no owner, and its budget counters sit in a value the untrusted side produces (§4.4, §6.1, §6.2, O13)

There are three statements, and they can't all be true:
- §6.1 and `boundaries.md` §7.1 give the signature `think(continuation, reply | None) -> (continuation', …)`. That
  makes the **host** the holder: it passes the value in and gets the next one back.
- §4.4 says continuations "live agent-side … saved with the agent home".
- §6.2 calls it "an opaque, versioned blob in the agent home".

Meanwhile the host needs fields from it: the thought id and kind (for the cost model and the cache), the triggering
input id (keying the follow-up-chain budget, §4.7), cancel status, and the outstanding request's deadline. An opaque
blob hides all of those. The continuation also carries "budget counters" (§6.1), while §6.2's thinking lane enforces
"the follow-up-chain budget". That makes two counters, and nothing says which one is authoritative. Under O13 the
worker is the trust boundary, so a counter the worker writes can't enforce a host budget.

**Failure scenario.** A guest's injected line makes every reply request one more action (Arch 1.3's attack). The
counter that would stop it lives in the continuation, which the compromised worker writes and returns. It resets the
counter on every resume, and the chain never ends. If instead the host keeps its own counter, keyed by the
triggering input id inside an opaque blob, the host can't read the key. On save, the host-held continuation (per the
signature) isn't in the agent home (per §4.4), so loading resumes no thought, or a different one.

**Fix.** Decide the owner in one sentence. I recommend: the worker owns the continuation and saves it in the home,
the port's `think` takes `(thought_id, reply)`, and a separate, host-owned **thought record** (id, kind, triggering
input id, modelled landing, budget counters, cancel status) lives in host state and the save. The host's budgets
read only that record. The continuation stays opaque because nothing on the host needs to read it.

## SHOULD-FIX

### S1. The thought lifecycle is never written end to end (§4.2, §6.1, §6.4)

The pieces exist, but there is no sequence that joins them. Missing:
- **The first call.** How a thought request in `StepOutput` becomes the first `think` call, and which side mints
  the continuation.
- **Follow-ups.** In Maxim a follow-up is the loop's own next submit (`ctrl.pending_action_followup`,
  `agent_loop.py:2172`, `:2264`). Here `settle` "returns nothing" (draft §2), so the follow-up has to reappear as a
  thought request in a later `StepOutput`. To key the chain budget, that request must carry its parent's triggering
  input id, and nobody states that lineage.
- **Two output channels.** Intents come out of both `StepOutput` and `ThoughtOutput`, and their order within a tick
  is unstated.
- **A stale basis.** What resume does when the basis is stale (drop the thought, re-plan, or log it) is not stated,
  and Arch 2.3's single `stale` vocabulary is missing (see Fold faithfulness).

**Scenario.** The double and real Maxim each fill the gap differently, the same scripted scene gives different
follow-up counts, and the budget test passes on the double while the chain still runs unbounded on real Maxim.

**Fix.** Add a sequence to §6.1: request, first `think`, Pending and resume, then `ThoughtOutput`, intents, receipts,
`settle`, the follow-up request with its lineage, and the stale-basis outcome as a logged kind shared with receipts.

### S2. There are second doors to a model outside `think` (§6.1, the request/reply cut; OD-A17)

The design treats the planning call as Maxim's only model call ("the only thing `think` waits on is a model call";
§4.7 says the thinking lane is "the only path to a model"). On 7084f561, Maxim has other LLM injection points:
- `AdaptivePlanner` is built with `llm=llm` whenever memory exists (`runtime/bootstrap.py:623-631`), and it calls
  `self._llm.generate_structured` for goal decomposition (`planning/adaptive_planner.py:487`);
- `ToolPainBridge._generate_reflection` calls `self._llm.generate` after a surprising tool failure
  (`bridges/tool_pain_bridge.py:806`). That is on the **settle** path, where it swallows the error at debug level;
- `FearAgent(llm=fear_llm)` (`runtime/agent_factory.py:1147`) analyses actions with `generate_json` when a router is
  given.

Some of these are dormant on the factory path today (`bootstrap.py:507` builds the bridge without `llm`; fear falls
back to patterns "for NPCs"), but none is named in the cut or the leak closure.

**Scenario.** Under O13 the worker has no keys and the latch is on. A wired planner's call fails inside dispatch, or
the reflection fails silently in `settle`, and behaviour differs from the robot path that the parity guard
compares. Alternatively, a host passes a router "to make it work". Then a model call happens in the worker that the
host never costs, caches or stamps, and reruns stop reproducing.

**Fix.** Either every router call site goes through the cut (so `settle` and dispatch could also return a
`Pending`, a much bigger seam), or every non-planning LLM slot is `None` on the embedded path, as a structural rule
in OD-A17, proven by the static import ban and a planted `llm=` that makes construction refuse. Ask Maxim which; the
second is far smaller.

### S3. "Cognition tools resolve inside `think`" is an inner tool loop (§6.1 row 4; draft §2)

A recall the model asks for has a result the model must see. If it "resolves inside `think`" and feeds a second
model call within the same thought, that is the ReAct inner loop Maxim doesn't have and lists as experiment C10
(`response.md` Part 2, item 10). It also escapes the cost model (§4.2 has no row for it) and the follow-up-chain
budget (§4.7 counts follow-ups after receipts, and this has no receipt).

**Scenario.** A prompt-injected guest gets an NPC to call `recall` repeatedly. Each recall feeds another model call
inside one thought, so the thought runs unbounded by the chain cap at no modelled cost, while §4.5's latency table
counts none of it.

**Fix.** Define a cognition tool's result as an **agent-internal follow-up**: no intent, no world log, no receipt,
but a new P1c/Pn segment with its modelled cost, counted in the chain budget. Or say plainly that the row asks for
C10 and is gated as an experiment.

### S4. O13 cuts the adapter across a process boundary, and the world half wasn't re-cut (O13, §6.3; `boundaries.md` §1, §3, §5.4, §7)

With Maxim in a worker, part of `engine.adapters.agents` runs on each side, and so does the membrane. Maxim calls
`StructureModulator.execute` in process, so stage-1 `parse_action` and the bound-actor check (§6.5) run **inside the
untrusted worker**. Not updated:
- `boundaries.md` §5.4's registry rule says in-process objects from Maxim "reach the engine only through those
  methods, so they are covered without an input primitive". That is now false: everything arrives as bytes through
  a pipe decoder, which is an input primitive and needs a gate row with the strictest contract.
- §1's "second sealed set … the tripwire runs on the agent lane's thread" now has to run in the worker.
- Frames are shipped per step per agent (§7.3's pinned frame), but the B5 meters only count the pipe round trip.
- The scrubbed environment doesn't pin `PYTHONHASHSEED`. Each `spawn`ed worker gets a random string-hash seed, so
  any set iteration order in Maxim varies between reruns (BD-14 already lists set order).

**Scenario.** A compromised worker returns a `StepOutput` whose intent was "already parsed" at stage 1 inside the
worker. The host trusts it, because the registry says Maxim objects need no input primitive, and a malformed intent
reaches the applier. Separately, two reruns of one save diverge because the workers drew different hash seeds.

**Fix.** Add a "worker pipe" gate row (strict decoder, budgets, every `StepOutput`, `Pending` and `ThoughtOutput`
re-validated at stage 1 on the host side), amend §5.4's sentence, state which modules run on which side, add frame
encode and transfer to the meters, and pin `PYTHONHASHSEED` in the worker environment.

### S5. The request's priority and deadline are a second source of time (§6.1 request row vs §4.2, §4.4)

§4.2: "Every segment's world time is computed by the host from the cost model, never parsed from model output", and
the kind is frozen before the call. Yet the request value, built by Maxim in the worker, carries "priority class and
deadline". §4.4 dispatches by deadline. Nothing says which deadline the lane uses, or that the host overrides it.

**Scenario.** Maxim's deadline (wall-based today, or a world-time guess) and the host's cost-model landing disagree.
The lane dispatches by Maxim's deadline, so a request due earlier by the cost model queues behind it, and the world
dilates for the wrong NPC. A compromised worker marks every request "danger, due now" and starves every other NPC.

**Fix.** The host computes the deadline from the frozen kind and the cost model. The request's priority class is
advisory, mapped through a host table and clamped per actor. Say so in §6.1 and in OD-A14.

### S6. Nothing keeps the barrier live if a worker hangs or dies (§6.3, §4.4 Liveness)

The barrier waits until every agent has "returned from `step`, `think` or `settle`". The liveness rule covers only a
**model call** past the wall ceiling. A worker can now hang in Maxim's own code (a lock, a long consolidation) or
die (out of memory, a segfault in a native wheel), and the design has no rule for either.

**Scenario.** One NPC's worker is killed by the OS out-of-memory killer during a co-op session. The barrier never
sees it park, and the world freezes for every player. That is DLP-B2's freeze through a door that §4.4's fixes
don't cover.

**Fix.** Add a per-call wall ceiling on `step`, `think` and `settle` too. Past it, or on worker exit, write a logged
`agent_failed` control record and take the NPC out of the barrier set (a statue). Respawn from the home is a logged,
tier-3 event. Add crash injection for workers to `phase1/lanes`, as the lanes row already does for threads.

### S7. The test double never crosses the worker boundary (§6.2, §6.3)

"The test double runs in-process." The pipe codec, the continuation crossing the process boundary, `spawn`, the
scrubbed environment, worker death and frame shipping are therefore first exercised by real Maxim in Phase 4, after
1.4.0. That is too late to find a contract bug. (`boundaries.md` §11.1 brings the worker processes with
`phase1/lanes`, which still uses only the double.)

**Fix.** Add a process-mode variant of the double in `phase1/lanes`, running in a `spawn`ed worker with the real
pipe, gate and scrubbed environment, and run the barrier, replay and crash tests against both modes.

### S8. The submit path is still touched in pieces, with no single design named, and the build order has holes (draft §4; roadmap OD-A14, OD-A15, OD-A18, OD-H6)

Maxim's own caution was that items 5, 6 and 9 "must be designed together with the hybrid line, or the same submit
path gets restructured twice". v3 follows O15a's order, which is fine, but:
- **OD-H6** moves `llm_submit_interval` (the submit clock, `loop_controller.py:157`) onto the machinery clock
  **now**, and §A.1b replaces "one submit clock" with split clocks after 1.4.0. If OD-H6 is more than the clock
  seam's injection (OD-A2/A6), it is a second restructure. If it is no more than that, it should be a line under
  OD-A2, not a hybrid row.
- **OD-A14, the request/reply cut, has no PR** in the draft's §4 table, which goes from the roster through the leak
  closure and dispatch/settle to the stepped `think`.
- **PR 3** (the leak closure) includes "the parser bypass for cancelled replies", but cancelled replies don't exist
  until the cut and the stepped `think` (PR 5).
- Nothing says that PR 4's `settle`, which must produce the follow-up, is designed against PR 5's continuation.

**Scenario.** PR 4 ships `settle` returning nothing and queuing the follow-up in `ctrl` as today. PR 5 then needs
`settle` to emit a lineage-tagged thought request (S1), so `settle`'s shape changes under a parity guard a second
time.

**Fix.** Name one design document covering OD-A14, OD-A15, OD-A18 and OD-H6's trigger, reviewed before PR 4. Put
OD-A14 in PR 5 explicitly, move the parser bypass to PR 5, and fold OD-H6 into OD-A2/A6 or say what else it changes.

### S9. §12.1 item 6 is not framed fairly

The question offers dilate or abandon and proposes dilate. Four problems:
- **It misdescribes abandon.** "Logged statue NPCs" is true under every policy: §4.4 says the NPC is a statue in
  flight until Maxim's reflex layer exists. Abandon's real cost is that a thought later than its modelled time is
  dropped, and in conversation, with D around 200 ms to 1 s against L = 3 s, that is nearly every reply. **Under
  abandon, NPCs mostly never answer.** The question should say so.
- **It omits dilate's cost.** Under dilate, live play falls to about 0.33× while an NPC deliberates and about 0.11×
  through 3 PFC cycles (§4.5), and it slows the world "for other players in co-op". The owner reversed exactly that
  for live play in O11 ("Live play holds the floor; it doesn't dilate"). The proposal re-introduces it without
  quoting either number or saying that it reverses O11 for the interim.
- **It omits the third option, the one closest to O11:** late-land in real time without the filler repertoire. The
  world keeps real time, the late answer arrives as a new turn when it exists, it is logged, tier 3, and counted by
  O11a's lateness meter. That is O11 minus OD-H5's fillers, needs no game-side repertoire (so OA3 holds), and is what
  world_v2 had for live play. It sounds reluctant on slow hardware, but O11a already accepts and meters that.
- **It understates "interim".** OD-H5 is "a paper plan in the 1.5 line"; Phase 4 waits for 1.4.0. The interim may
  be all of Phase 4.

**Fix.** Rewrite item 6 with three options (dilate, late-land, abandon), each with its numbers and who pays (the
co-op partner, the listener, the NPC that never answers), and state that it may last for all of Phase 4. Propose
whichever is preferred once those costs are visible.

### S10. The world half's PR plan still builds the deleted design (`world_model.md` §10 rows 9b and 10; `npcs_and_sem.md` §6.5)

`world_model.md` §10 wasn't in the commit:
- row 9b (`phase1/agents`) still lists "the split `AgentPort` and host service protocol";
- row 10 (`phase1/lanes`) still lists "the LLM gateway" and no worker processes.

`npcs_and_sem.md` §6.5 still says "The membrane factory takes a frame source and the intent sink", while
`boundaries.md` §7.1 now says it "returns intents in `StepOutput`", and §6.2 says `execute` appends to "the stepping
agent's outbox". These are three descriptions of one seam.

**Scenario.** Whoever opens `phase1/agents` from the PR table builds the protocol v3 deleted.

**Fix.** Update rows 9b and 10 and §6.5 in this fold, and pick one wording for the membrane's output.

## NIT

- **N1 (`boundaries.md` §7.1, "Inline later").** "Calling agents inside the tick is no longer blocked by design,
  only by … the worker boundary". Inlining puts Maxim back in the host process, which O13 just made the trust
  boundary. That makes it a design decision against O13, not only a B5 measurement.
- **N2 (`boundaries.md` §7.1).** "v3's host service protocol" is ambiguous, because `boundaries.md` is itself v3 and
  `npcs_and_sem.md` v3 deleted it. Say "boundaries v3 / npcs v2".
- **N3 (signatures).** `step(now_tick, dt_ticks, frame)` in boundaries, `step(world_dt, frame)` in O6 and
  `step(agent, world_dt_us, frame)` in the draft. State which is the port and which is Maxim's, and the conversion.
- **N4 (§6.4 receipt).** One receipt feeds `settle` (which needs `apply_tick` and frame ids for traces) and becomes
  the follow-up's prompt content (which, by §3.1, may carry no time field). Name the two projections and who strips.
- **N5 (stale text).** Roadmap line 64 still says "a gateway the host supplies". The foundations fold tables in both
  files still cite "§6.1 gateway" and "intent sink as a required port" (Arch B3, Wire B2, Wire B3). Annotate them
  "superseded by O6a" so a reader doesn't follow them.
- **N6 (§5.2, §6.1).** No rule says what happens when the per-chunk speech validator refuses a chunk mid-stream.
  Presumably the host cuts and resumes with `truncated(prefix, reason=validation)`. Say so, so the agent's record of
  what was said matches what players heard.
- **N7 (`boundaries.md` §5.3 "Agent homes" row).** The interim relies on `MAXIM_DATA_HOME`, while OD-A17 says the
  embedded entry point reads no environment. Mark it as the interim until OD-A12, with OD-A17's env-read test
  expecting exactly that one variable until then.
