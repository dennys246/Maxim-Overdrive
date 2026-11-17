# Architecture lens: Maxim's response to the embeddable-agent questions

Reviewer: Architecture lens (Overdrive). Read: `response.md` (this folder); Overdrive `docs/design/boundaries.md`,
`docs/design/npcs_and_sem.md`, `docs/maxim_upstream/embeddable_agent_DRAFT.md`, `docs/maxim_upstream/README.md`,
`docs/roadmap.md` Phase 3; Maxim `origin/main` 7084f561, read-only, spot-checking the citations that carry the design.

Tags: **AGREE**, **PUSH BACK** (Maxim's answer is wrong or incomplete, with the reason), **MISSING** (neither side
has it), **CHANGE-OURS** (an Overdrive document or decision must change).

Short version: the correction is right and it makes Overdrive's agent half simpler, mostly by deleting things
(the host-service callback, the cancellable backend, parked threads, tool schemas in the cache key). But the answer's
central signature, `think(state, input) -> (state', Pending | ThoughtOutput)`, hides three things the merged design
must settle before it is a contract: what "state" is, how a thought in flight composes with `step`, and where the
injection budget went now that there is no inner loop. Part 2's ranking demotes the embedded tool roster from "now"
to "earn it by experiment", which contradicts Part 1. Its replay claim is also overstated.

---

## 1. "No inner tool loop" and "Maxim's action is your validated intent"

**AGREE (1.1). The correction is verified.** `agent_loop.py:2172` queues the batched-exploration result as
`ctrl.pending_action_followup` and `continue`s. `:2256-2264` takes `execute_and_learn`'s `_outcome.followup` into the
same slot for the next submit. The model never sees a tool result inside a call. Our draft's §4.2 / §4.6 / §9 assumed
otherwise (`embeddable_agent_DRAFT.md:92`, `:141`, `:210`), and so does `npcs_and_sem.md` §4.7's "tool calls" cap
(`npcs_and_sem.md:447-449`).

**What it simplifies (AGREE, and CHANGE-OURS where noted):**
- **The host service protocol loses its reason to exist.** `boundaries.md:497` and `npcs_and_sem.md:585-586` hand
  the adapter `request_thought(request)` and "the LLM gateway handle" as a required keyword. If `think` *returns* the
  request, the adapter never calls the host. The callback runs the wrong way (inversion of control), and it was the
  thing that made "no upward import" (`boundaries.md:499-501`) need a special protocol layer. Delete it. `AgentPort`
  becomes `step`, `think` (resume) and `settle`, all called by the host. CHANGE-OURS.
- **The barrier's "parked at the gateway" state goes away** (`boundaries.md:512-514`, `npcs_and_sem.md:611-613`).
  An agent with an outstanding request is just a value with a `Pending` in it; no thread is parked. The
  no-deadlock invariant in `npcs_and_sem.md:379-381` becomes true by construction rather than by a dispatch rule.
  CHANGE-OURS: rewrite the park definition as "returned from `step`/`think`/`settle`".
- **Tool-call latency (§4.5).** "A tool call can't act on a partial stream, so it pays the full latency"
  (`npcs_and_sem.md:409-410`) stays true. What changes is the *count*: a thought's segments are now (a) PFC
  deliberation cycles and (b) follow-up thoughts after receipts, not tool calls inside one call. See 1.3.
- **The cache key (§4.8).** "the tool schemas in a fixed order" (`npcs_and_sem.md:470`) is moot: planning sends no
  native `tools=`; tools are rendered into prompt text. The canonical request is rendered system/user text, sampling
  parameters, model profile and template version. Keep a field asserting `tools is None`, so a later move to native
  tools changes the key loudly. CHANGE-OURS.
- **O6's step signature survives** (`boundaries.md:47`, `npcs_and_sem.md:51`). It gains a sibling, `think`, and loses
  "a host-supplied LLM gateway with streaming and cancellation" as a *Maxim* deliverable. CHANGE-OURS (see §5).

**PUSH BACK (1.2). "Maxim's action is your validated intent" is true for world actions only.** Our roster row
(`npcs_and_sem.md:566`) includes "reviewed cognition tools (memory recall, narrative)". A memory recall isn't a world
intent. Sending it through the engine's one intent door would log it, give it a receipt at a tick, and charge it a
follow-up model call (a full L, §4.5) just to read the agent's own store. The merged design needs a typed split:
- **effectful world tools** go out as intents and come back as receipts → follow-up;
- **internal, read-only cognition tools** (recall, narrative lookup) resolve inside `think` against the agent's own
  stores, which only `apply`/`settle` ever write.

Without that split, either cognition tools go through the world log (wrong layer, and a privacy leak into bug
reports), or "the only pending request is a model call" quietly stops being true. MISSING on both sides.

**PUSH BACK (1.3). The injection budget didn't go away; it moved.** The draft's §4.6 threat (an injected prompt holding
an agent in a long tool loop, TB2-B3; `embeddable_agent_DRAFT.md:145-147`) has a direct analogue: an injected prompt
that makes every reply request one more action, so each receipt triggers another follow-up thought, tick after tick.
Under a live-play hold (O11) that's an NPC monopolised by a guest. Under dilate it's a world crawling at L per step.
The budget has to be keyed **per triggering input across its follow-up chain**, plus `parallel_actions` per reply
(grammar `maxItems`, the advisor pattern the response cites, `_session.py:288`) and PFC cycles per thought. Maxim
already has a per-turn counter shape in `LoopController.rejection_followups` (`loop_controller.py`, beside
`llm_submit_interval` at `:157`). The response says §4.6 is "Mostly [covered], but on the advisor only" and doesn't
address the chain at all. MISSING; CHANGE-OURS: `npcs_and_sem.md:447-452` and `embeddable_agent_DRAFT.md:138-148`, and
OD-EA9 (`embeddable_agent_DRAFT.md:181`), whose "a stub model that calls a tool forever" becomes "a stub whose every
reply requests a follow-up".

**PUSH BACK (1.4). One call per thought is not quite true either: PFC deliberation makes 2–3.**
`agent_loop.py:3085-3125` runs `_run_deliberation_cycles` when the first proposal says `ready_to_act=False`, with
`max_cycles` 3 when a percept source exists, else 2 (`:3089-3093`). That's inside one tick today, blocking on
`_wait_for_proposal`. Under the resumable think these become successive `Pending`s of one thought. For Overdrive:
- **Cost model.** Each cycle is a P1-like segment with no speech. Our §4.2 table (`npcs_and_sem.md:319-331`) has no
  row for it. Under O9 ("content may only make it land later", `npcs_and_sem.md:56`) a model-chosen extra cycle
  is a content-dependent delay, so it must be capped in `thought_budget.yaml` and counted against the dilation
  budget.
- **Latency.** The worst case for "one NPC talking to the player" is 3·L before speech, not L. At L = 3 s that's a
  roughly 9 s hold, past any floor ceiling. §4.5's table (`npcs_and_sem.md:414-419`) understates it. CHANGE-OURS.

**Is multi-step tool use lost? No, it moves.** Multi-step is a chain of thoughts linked by follow-ups, which is
exactly our "think → act → perceive" Pn row (`npcs_and_sem.md:331`). That's more bio-faithful, since each step sees
the world's actual response. The cost is one full L per step, and that's an argument *for* item C10 (an inner loop as
a tested alternative), not a loss to patch here.

## 2. The contract: `think(state, input) -> (state', Pending | ThoughtOutput)`

**AGREE (2.1). A host-called function, a frozen value, the gateway above the backend, cancel as a reply.**
- It is the right shape for a deterministic host. Every source of nondeterminism collapses into one logged input,
  the reply. Its landing tick is assigned by the host's cost model, so wall latency can't leak in.
- The `_inference_lock` argument is verified. `router.py:1080` takes one lock per router around
  `_complete_text_locked`, so N NPCs on one router think one at a time. Our draft's `LLMBackend` capabilities
  (`embeddable_agent_DRAFT.md:57`, `:101-111`) would have inherited it and the blocking thread. Withdraw PR 4
  (`:161`).
- "Generators can't be saved" is the right reason to refuse a coroutine.

**PUSH BACK (2.2). "state" is undefined, and the obvious reading is wrong.** If `state` means the whole agent
(hippocampus, NAc, ATL, cerebellum…), copying a frozen snapshot per call is unaffordable and still isn't pure: the
think path writes today. The hybrid plan itself records that `propose_via_substrate` "writes EC, re-keys clusters,
fires a situation cue, ticks drift and pain, and bumps visit counts" (`hybrid_arbitration.md:395-396`), and prompt
build reads and updates the context pool and working memory. The contract that can actually hold is:
- `think(agent, continuation, input) -> (continuation', Pending | ThoughtOutput)`, where `agent` is read-only on this
  path and **only the continuation is the frozen value**;
- every store write leaves as a value through `apply`/`settle` (our OD-A15 generate-vs-apply, which Part 2 doesn't
  list; see 4.2);
- a census of writes on the think path is the plan's first step, and OD-EA4 (`embeddable_agent_DRAFT.md:176`) is
  its gate.

**MISSING (2.3). A thought in flight against an agent that keeps stepping.** Between `Pending` and resume, the host
keeps calling `step` (drives drift, percepts arrive, receipts settle). A frozen `state` captured at request time and
resumed later would either overwrite those changes or fork the agent. The continuation must carry a `basis` (the
agent's step sequence and frame id at request time), and resume must decide staleness against the *current* agent.
That is exactly §A.1b.5's `basis_seq` staleness (`hybrid_arbitration.md` §A.1b item 5), which is one more reason the
merge in §3 is right. It also means our receipt `stale` kind and their answer-staleness need one vocabulary.

**What the continuation must contain for save, load and replay (MISSING, propose to Maxim):**
- a format version; the thought id `(actor, seq)`; the `kind` (OA1, frozen before the call);
- the cycle index and `max_cycles`; the first or partial proposal carried between PFC cycles;
- the outstanding canonical request (the cache key, `npcs_and_sem.md:468-471`), or none;
- the `basis` (step seq, frame id) and the triggering input id, which keys the follow-up-chain budget (1.3);
- budget counters spent (cycles, follow-ups, tokens, writes and bytes);
- cancel status, with the delivered prefix if cancelled;
- the loop locals the response lists as not yet values (the same-tool counter, `rejection_followups`);
- the RNG stream position and the id-source cursor, if prompt build draws from them (Part 2 item 2/3).

It must be serialised without pickle, under the same rule as OD-A13. Our side: §4.4 already says early-held results
are saved with the agent home (`npcs_and_sem.md:386-387`); the continuation joins them there, never the world log.

**AGREE with a condition (2.4). Where PFC blocking and the worker pool go.** PFC cycles become successive `Pending`s
(1.4). The worker thread and queue leave the embedded path entirely; the host's thinking lane executes request
values and schedules by deadline (`npcs_and_sem.md:377-378`). **The condition:** the robot loop must drive the *same*
`think` through a thin worker driver, not keep its own deliberation. Otherwise Maxim has two deliberation paths,
one of them tested only by a game, and the embedded one rots. Part 2's parity check (item 5, Exp 49 and Exp 60)
only means something if it is checking one function under two drivers. Say this in the plan.

**PUSH BACK (2.5). The request must not carry Maxim's provider choice.** The response puts "provider choice" before
the cut (`router.py:944`'s prelude). On the embedded path the model is the host's model profile (`npcs_and_sem.md`
§4.1, the rig analogue). The lane/cloud default (`lane_backends.py:1269`) is one of the confirmed leak paths. The
request names a model *role* (speech vs plan, our §4.5 lever 2); the host binds it.

**PUSH BACK (2.6). "Streaming later" is acceptable for the token iterator, not for the reply type or the output
format.** Under the request/reply cut, streaming is mostly a *host* capability. The host owns the HTTP stream, stamps
syllables server-side (`npcs_and_sem.md:527-532`) and cuts on barge-in (§4.3). Maxim doesn't need to consume tokens
incrementally. But two things must be in v1 of the contract, or OA4, barge-in and §4.5's lever 3
(`npcs_and_sem.md:426`) are designed out:
- **A partial reply variant:** `Reply.cancelled(prefix)` / `Reply.truncated(prefix, reason=budget)`. The parse path
  must accept it, and the agent must record the prefix as said and the rest as an interrupted intention (§4.3,
  `npcs_and_sem.md:357-361`). "Cancel = resume with a cancelled reply" is half of this; the prefix is the other half.
- **A streamable speech field.** Maxim's reply is one JSON action. To speak before the JSON closes, the speech text
  must be a top-level field the host can extract incrementally, and it must be emitted *before* the action fields.
  That's a prompt/grammar decision Maxim owns. Without it, the time to first syllable is the whole reply, and with
  PFC cycles (1.4) it's 3·L.
- **Trust.** Streamed speech reaches players before the full reply validates, so the stage-1 speech validator
  (`npcs_and_sem.md:513-515`) must run per chunk and must not depend on the rest of the JSON. CHANGE-OURS: §5.2 says
  so.

## 3. Merging the embeddable think with hybrid §A.1b

**AGREE (3.1). One design.** The facts support it. §A.1b's net-new item 2 is "one proposal slot, one submit clock"
restructured into a held slot with a deadline (`hybrid_arbitration.md:74-80`, `:216-222`). The resumable think
restructures the same submit path. Designed apart, the slot is rebuilt twice. The merge also gives Overdrive the
semantics it wanted for late thoughts. §A.1b.1's hold is "a deadline on the held slot … never a blocking wait", on
"one named clock per world: the experience clock where the world has one" (`:217-226`). With the host assigning
reply landing ticks, "did the LLM land inside *h*" becomes a function of the modelled cost, which is OD-H2's ask
satisfied structurally rather than by a parameter.

**PUSH BACK (3.2). Merge the design, not the gate.** The hybrid family's build is gated on experiments: "The
four-lens review of the portfolio prereg runs BEFORE any harness is built … The build, after 1.4.0"
(`hybrid_arbitration.md:397-398`). Part 2 then files the seam as item 5, "adopt only if an experiment earns it". The
seam is engineering. Its acceptance is a regression gate (state digest identical under seeded wall delays, OD-EA5;
behavioural parity with today's worker), not a ledger claim. If it rides the hybrid's experimental gate, Overdrive's
Phase 4 waits on the arbiter's *results*, not only its *structure*. Ask for: one design document; the seam and the
dispatch/settle split shipped as `[engineering]` on the 1.3.6 loop builder with parity guards; the arbiter, *h* and
pre-emption built on top after 1.4.0 as the hybrid plan says. Part 2 item 6 mixes both too: the *split* is
engineering, while *moving robot credit from dispatch to measurement* is behavioural and needs evidence. Separate
them.

**Timeline cost (state it plainly).** Nothing in `src/` before 1.3.6 for the seam, and nothing hybrid before 1.4.0
(M89, `hybrid_arbitration.md:24-25`). Phase 4 already starts only on tier A (`roadmap.md:173-175`), so the merge adds
no new gate if 3.2 is accepted. If it isn't, Phase 4's real-NPC start moves from "after 1.3.6 plus A-post" to "after
1.4.0 plus the hybrid design review", and that's the coupling the owner should decide on knowingly.

**What Overdrive can build now against the test double (AGREE with our §6.2, reshaped):**
- `AgentPort` as `step` / `think` (resume) / `settle`; `Pending`, `Reply` (including `cancelled(prefix)` and
  `truncated`) and `ThoughtOutput` as frozen, versioned types with goldens;
- the continuation as an opaque, versioned blob in the agent home, with a save/load round trip;
- the host thinking lane that executes request values, by deadline, with the response cache, cancel-as-reply, the
  wall ceiling → `thought_failed`, and the follow-up-chain budget;
- the host-side stream: chunked speech validation and syllable stamping from a scripted stream;
- receipts → `settle` → the follow-up as the next `think` input;
- the scripted double implemented as a real state machine (PFC-style multi-cycle, follow-ups, partial replies), so
  the barrier and replay tests exercise the hard cases;
- the hold itself (*h*, floor-holding) is **not** buildable now: OA3 forbids a game-side repertoire. The double may
  script fillers as fixed outputs for interface tests only, and the tests must say so.

## 4. Part 2's list and order

**AGREE (4.1). A1–A4 first.** Per-agent home, RNG, clock and pickle-free load are cheap, robot-safe, guardable by
deletion, and everything after depends on them.
- On A2: `make_agent_rng` (`utils/seeding.py:79`) derives a `random.Random` from `(base_seed, agent_id)` by SHA-256.
  That is fine as the robot default, but the embedded path must accept an injected stream so the host can key it as
  `SeedSequence(root, spawn_key=(NS_AGENT, npc_key, stream_key))` (`boundaries.md:563-565`). Ask that `AgentTime`'s
  RNG be injectable with `make_agent_rng` as its default, not that the host conform to `make_agent_rng`.

**PUSH BACK (4.2). Part 2 contradicts Part 1 on the tool roster, and drops generate-vs-apply.**
- Part 1 puts the roster, home and pickle PRs "on their own clock, before 1.3.6" (`response.md:106`). Part 2 lists
  only home (A1) and pickle (A4) in group A, and moves the roster to B8, "make capability rosters the default for all
  agents … adopt only if an experiment earns it" (`response.md:217`). For *embedded* agents the closed roster is a
  security property guaranteed by construction (their own words), and without it there is no Phase 4 at all
  (TB2-B1). Keep the embedded roster, with its import-closure and env-read-set tests (`response.md:104`), in group
  A. Only B8's "for all agents" extension needs the red-team experiment.
- Generate vs apply (memory writes as values, OD-A15; `embeddable_agent_DRAFT.md:97-99`) appears nowhere in Part 2.
  Item 6 splits *tool* dispatch from settle, but the think path's own writes (2.2) aren't covered. Add it to item 5's
  scope explicitly.

**MISSING (4.3). Items Overdrive needs that Part 2 omits.**
- **D53 valence self-report and refusal-kind promotion (OD-A16).** `outcome_valence` on receipts, and the bridge
  dropping `result.metadata` on failure so stale books NEGATIVE (`npcs_and_sem.md:359-362`), must be part of item 6's
  settle half, or the split ships with the "striking steel doors works" bug intact. Item 6 should name OD-A16 as its
  amendment.
- **The second dispatch seam.** `execute_and_learn`'s own docstring names tracked exceptions that still dispatch on
  their own: `execute_parallel_actions` and the agent-fallback path #1147 (`tool_dispatch.py:1293-1295`). "The single
  place they belong" (`response.md:28`) is true only after those fold in. Batched exploration (`agent_loop.py:2149-
  2183`) is exactly the parallel path. Item 6 must include them, or parallel actions keep crediting at dispatch.
- **The ConceptExtractor thread** (OD-EA7). The response confirms it fails today (`response.md:75`), but no Part 2
  item fixes it. Put it under A1, since it's the home's worker.
- **The follow-up-chain and cycle budget** (1.3, 1.4).
- **The submit trigger on the embedded path.** Item 9 (escalation instead of the 0.5 s wall interval,
  `loop_controller.py:157`) is filed as an experiment. For embedded agents the wall interval is a determinism bug
  regardless. The seam must at least run it on the injected clock now, with escalation triggering as the later,
  earned change.
- **The write window.** Our O8 window is engine-side, but the same rule applies to agent stores: written only at the
  host's `apply`/`settle` point on the agent's owning lane. The plan should say who may hold a writable store handle
  outside it, which today is the ConceptExtractor thread and the DN thread (OD-A9).
- **Guest-driven holds.** Live play (O11) lets any speaker trigger thoughts and holds. Per-speaker rate limits exist
  on our side (`npcs_and_sem.md:456`), but the substrate's floor-holding plan (Part 1 §3) should take "who triggered
  the hold" as an input, so one guest can't keep an NPC permanently mid-hold.

**PUSH BACK (4.4). Item 7 (router priority queue) isn't on the embedded path, and shouldn't be.** With the gateway
above the backend, the host schedules requests (by deadline, `npcs_and_sem.md:377-378`). A Maxim-side "danger before
dialogue" queue in the router helps robots and `AgentPool`. For embedders, what's needed is the *priority class and
deadline as fields of the request value*, so the host can schedule by them. Otherwise the policy is decided twice,
in two places that can disagree.

**PUSH BACK (4.5). The replay claim is overstated.** "Overdrive can replay the same run bit for bit with one variable
changed. Paired replays shrink the confidence intervals" (`response.md:210`). A bit-identical replay needs the
response cache (`npcs_and_sem.md:461-480`). Once the changed variable alters any prompt, every later request misses,
and §4.8 makes misses loud errors, never live calls (`:477`). So pairing holds only:
- for substrate-only arms;
- for variables downstream of every model call;
- for the prefix before the first divergence.

It's still valuable (it's how we'd test Exp 49-style substrate questions), but the plan should state the limit, or
BF2 power calculations will assume variance reduction that LLM arms won't deliver.

**AGREE, with an addition (4.6). The overfitting caution.** A transfer check in a Maxim-owned harness before a claim
moves is the right rule (OD-HX5, generalised). Two additions:
- It cuts both ways. Overdrive must not let Maxim's robot defaults become game constants. Floor thresholds, *h* and
  filler timing are per-world parameters on the listener's clock, which the response itself asks for
  (`response.md:121`).
- C10–C12 are framed as the game "testing Maxim's choices". Each needs its outcome measured on a Maxim-owned task
  too, or it's game evidence only, which Maxim's ledger rule excludes.

**Order, from Overdrive's view.** A1–A4 plus the embedded roster (4.2) → one merged seam design (item 5 + item 6 +
generate-vs-apply + OD-A16's settle keys) → seam and split built on 1.3.6 with parity guards → hybrid arbiter and
floor-holding after 1.4.0 → items 7–9 and C10–C12 as experiments.

## 5. What Overdrive must change

**CHANGE-OURS, by section:**
- **`boundaries.md:47` (O6) and `npcs_and_sem.md:51` (O6).** Replace "a host-supplied LLM gateway with streaming and
  cancellation" with: the agent's deliberation is a host-called, resumable `think` that returns model requests as
  values; the host executes them; cancel is a `cancelled(prefix)` reply; a streamable speech field. Keep the rest.
- **`boundaries.md:48` (O7).** The condition, "until Maxim answers", is met. Unpark the agent half for one revision
  and a review round (with Bio-faithful as a lens). Note that the answer comes from Maxim's design session, not from
  its process: nothing is filed, so citations stay "proposed".
- **`boundaries.md` §7.1 (`:489-526`).** Remove the host service protocol row and `request_thought`. Make
  `AgentPort` `step` / `think` / `settle`. Redefine the barrier's park. Revisit the "Inline later" bullet (`:519-522`):
  with requests as values, the only nondeterministic input is the reply, so calling agents on the simulation lane is
  no longer blocked by design, only by Maxim's step cost. Decide it by a B5 measurement, not now.
- **`boundaries.md` §7.4 (`:576-587`).** "A thought result is streamed through the gateway" becomes "the host streams
  the model call; the agent sees `Reply` values".
- **`npcs_and_sem.md` §4.2 table (`:319-331`).** Add a PFC cycle row (no speech, modelled cost, capped). Reword Pn as
  "after a receipt (follow-up) or a percept".
- **`npcs_and_sem.md` §4.4 (`:377-381`).** Simplify the no-deadlock invariant: no worker is ever held by an agent.
- **`npcs_and_sem.md` §4.5 (`:405-426`).** Recompute "one NPC talking" with up to 3 PFC cycles. Add a meter for
  cycles per thought and follow-ups per triggering input.
- **`npcs_and_sem.md` §4.7 (`:447-452`).** Replace "tool calls" with parallel actions per reply, PFC cycles per
  thought, and follow-up chain length per triggering input.
- **`npcs_and_sem.md` §4.8 (`:468-471`).** Drop "tool schemas in a fixed order" and assert `tools is None`. Add the
  continuation to the save, never the log.
- **`npcs_and_sem.md` §5.2 (`:513-515`).** Run the speech validator per streamed chunk.
- **`npcs_and_sem.md` §6.1 (`:565-566`).** Rewrite the gateway row as above. Add a continuation row and a cognition
  vs world tool split. Add `runtime/bootstrap.py:261-276`'s internet tools and the global stores to the evidence
  column.
- **`npcs_and_sem.md` §6.2 (`:583-593`).** Reshape per §3 above (what we build now). The host service protocol goes.
- **`embeddable_agent_DRAFT.md`.**
  - §3 row 1 (`:57`): the gateway is not an `LLMBackend`.
  - §4.1 (`:85`): `home` → the existing `persistence_dir` plus the global-store census.
  - §4.2 (`:101-116`): rewrite as request/reply.
  - §4.6 (`:138-148`) and OD-EA9 (`:181`): the follow-up-chain budget.
  - §5 PR 4 (`:161`): withdraw.
  - OD-EA8 (`:180`): cancel as a resumed `cancelled(prefix)` reply.
  - §9 (`:206-211`): record the answers.
  - Line 69's "unverified" DM claim is now confirmed (`ARCHITECTURE.md:182` is stale).
- **`roadmap.md` Phase 3.**
  - OD-I1 (`:79`): five sites.
  - OD-I2 (`:80`): downgrade to a docstring nit.
  - OD-A13 (`:105`): becomes an issue now, with the three corrections.
  - OD-A14 (`:106`) and OD-A15 (`:107`): rewrite as above.
  - New items: the robot path drives the same `think` (2.4), the ConceptExtractor thread, the import-closure and
    env-read tests, and the `ARCHITECTURE.md:182` docs fix.

**Decisions to revisit:**
- **O6: yes**, as above. The intent holds; the mechanism named in it was wrong.
- **O7: yes**, unpark it (above).
- **OA3: holds**, but its timeline is now explicit. The repertoire is a fifth hybrid split-out plan, on paper in the
  1.5 line, with a pre-registration for any claim. Phase 4's live conversation therefore has no floor-holding for a
  long time. The owner needs to choose the Phase 4 interim: dilate in live play, or abandon with logged statue NPCs
  (`npcs_and_sem.md:393`).
- **O11: yes, amend it.** Add the response's own pushback: past about 1 s, people often give an account ("let me
  think") before yielding. Yielding is one option among several. An account is speech, but it must stay
  claim-free and uncredited, like fillers. Also state that every threshold is a per-world parameter on world time,
  and that O11 depends on OA3's timeline above.
