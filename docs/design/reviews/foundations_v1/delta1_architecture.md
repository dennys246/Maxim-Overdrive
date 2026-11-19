# Design review, delta 1: foundations fold (boundaries v3, part 2 v2, the Maxim drafts), Architecture lens

- **Lens:** Architecture (right cut, right layer and owner, root cause or band-aid, standing rules, honest docs)
- **Commit:** 18623ce (`phase1/design-v2`), the delta since 4f7a754
- **Date:** 2026-11-16
- **Documents:** `docs/design/boundaries.md` v3, `docs/design/npcs_and_sem.md` v2, `realtime_lanes_coop.md` §4 note,
  `world_model.md` §10, `docs/roadmap.md`, `docs/maxim_upstream/*` (focus: `embeddable_agent_DRAFT.md`)
- **Read against:** my round 1 (`architecture.md` in this directory), CLAUDE.md, `docs/code_review.md`
- **Counts:** 2 BLOCKER, 10 SHOULD-FIX, 9 NIT

## Summary

O6 is the right root fix. My round-1 B2 deadlock came from the agent owning its turn, and the
"host steps, agent returns values" contract removes it. The sealed core, the ownership window, frames as copies, the
log record with `apply_us` and the 5a/5b and 7a/7b/7c sub-layers all compose with it. I found no import cycle. Most
round-1 findings really are closed (table at the end).

The fold stopped at the agent's outer surface, though. Overdrive's side of the contract still has v2's shape, and it
doesn't match the draft it sends to Maxim:
- the draft's host-called `think`, `ThoughtOutput` and `apply` are missing from `AgentPort`;
- v2's agent-calls-host `request_thought` and an intent sink survive beside the values, which gives two doors for
  thought requests and intents;
- memory writes have no applier.

The threading model also fails under its own rules. "Parked at the gateway" means an owner thread blocked inside a
Maxim turn, which is mode (a)'s shape again. With one thread serialising `step` and `think`, the body clock's
schedule and the thought can't both hold.

## BLOCKER

### B1. `boundaries.md` §7.1, §6.1; `npcs_and_sem.md` §6.2 vs `embeddable_agent_DRAFT.md` §4.1 :: Overdrive's port isn't the draft's contract: no `think`, no `apply`, two doors left over from v2, memory writes with no owner

- **What the draft offers** (§4.1): `step(world_dt_us, frame) -> StepOutput` (intents, memory writes, thought
  requests); **host-called** `think(request) -> ThoughtOutput` (intents, memory writes, spoken text, tool calls);
  `apply(memory_writes)`, the only path into the stores; `settle(receipts)`; `save()` / `load(home)`. The host reads
  thought requests from `StepOutput` and decides when to call `think`.
- **What Overdrive builds** (boundaries §7.1, part 2 §6.2): `AgentPort` = `step(now_tick, dt_ticks, frame)` and
  `settle(receipts)` only. On top of that, a host service protocol that the adapter calls: `request_thought(request)`,
  the gateway handle, and an intent sink that `execute` appends to.
- **Second door for thought requests.** §6.1 says "Thought requests come from an agent's `StepOutput` only", and that
  rule carries the per-speaker rate limit. `request_thought` on the service protocol is a second route that bypasses
  it. That is v2's "agent → host" arrow, renamed. Under the draft there is nothing for it to do.
- **Second door for intents.** Intents arrive as values (`StepOutput.intents`), and also through a sink that
  `execute` calls in the middle of a turn (boundaries §6.4, part 2 §6.2). There is no `ThoughtOutput`, so the sink is
  the only way a thought's intents reach the host. That is a callback out of a running turn, which O6 was meant to
  remove.
- **Unowned data.** `StepOutput` carries memory writes, but nothing in Overdrive calls `apply`. Boundaries §6.1 says
  they are "recorded in an agent-side audit record ... and saved with the agent home", with no applier named. Under
  generate vs apply an NPC therefore never remembers anything. The memory-write gate-to-be (§5.3) has no point at
  which it could run.
- **Mixed outputs.** `StepOutput` carries `speak` acts (§7.1), while §6.1 says an NPC speaks "only through a
  thought". The step and think outputs have been merged.
- **Failure scenario.** `phase1/agents` freezes `StepOutput`, the service protocol and their golden fixtures in this
  shape. At Phase 4 the real embedded agent arrives:
  - its intents and speech come back from `think` as values, which the port has no call for;
  - its memory writes wait for an `apply` that nothing makes;
  - the adapter bridges the gap by routing `ThoughtOutput` through the sink and `request_thought`, which puts a
    callback shim around Maxim's contract (the band-aid that the push-back rule forbids);
  - or the port and its goldens get a version bump in the first NPC PR.
- **Fix.**
  - Make the port mirror the draft:
    - `step -> StepOutput`: substrate intents, memory writes, thought requests, no speech;
    - `think(request) -> ThoughtOutput`: intents, `speak`, memory writes, cancelled/budget status;
    - `apply(memory_writes)`, called by the host at a stated point, after the memory gate;
    - `settle(receipts)`, `save`, `load`.
  - Delete `request_thought` and the intent sink from the service protocol. What remains there is the gateway handle
    (and see S3 for its type).
  - `execute` inside a thought records the parsed intent in the adapter's per-thought buffer, which becomes part of
    `ThoughtOutput`. It never calls the host.
  - Name the owner of memory-write application (the host, on the agent's owner thread, at the barrier) and of the
    audit record.

### B2. `boundaries.md` §7.1 (barrier, one owner); `npcs_and_sem.md` §4.4 (no-deadlock invariant), §6.3 :: an owner thread "parked at the gateway" is blocked inside a Maxim turn, so the body clock's schedule, the barrier and the invariant can't all hold

- **The premise is false.** Part 2 §4.4's no-deadlock invariant rests on this: "Under O6 agents never block inside a
  turn (`step` returns values)". But the barrier (§7.1, §6.3) counts an agent as parked when it is "waiting at the
  gateway for a held response". That agent is inside `think`, inside Maxim's tool loop, blocking its owner thread on a
  model call. It is a world-time wait inside a turn, which is mode (a)'s shape.
- **Why it matters even with no deadlock.** The owner thread serialises `step`, `settle`, the push and `think`
  (§6.3). While it is blocked in `think`, the agent's `step` can't run, so one of these breaks:
  - **`step` is skipped.** Then `dt_ticks` is no longer "a pure function of the actor's rate divisor and phase"
    (§7.1, DR-S1): the body clock stops, and drives don't drift. That contradicts §4.4's own "drives keep drifting",
    and every Δt-invariance argument in part 2 §2.1. The "statue" divergence is then caused by Overdrive's threading,
    not only by Maxim's missing reflex layer.
  - **`step` runs on a second thread.** That breaks one owner per agent, which is round-1 B1's race again.
- **The deadlock comes back if owner threads are pooled.** The text says "owned by one agent-lane thread at a time",
  which reads as a pool. Take k owner threads and k agents, each parked in `think` on a response held until T+D. A
  (k+1)-th agent is due to step at T and has no thread. The barrier never completes, the host never reaches T+D, and
  the held responses are never released. Round 1's B2 cycle comes back with "owner thread" in place of "worker".
- **The gap upstream.** Draft §9 leaves this open ("tool calls inside `think`: a host callback, or returning the tool
  call and resuming"). Overdrive's design depends on the answer, but doesn't state which answer it needs.
- **Fix.**
  - Require **return-and-resume** from Maxim, and say so in the draft as Overdrive's evidence:
    - `think` returns at every model call, with a pending-call value (the canonical request), and at every tool call;
    - the host resumes it with the response (or the tokens) at the segment's modelled time;
    - an agent between segments is parked by construction, so `step` interleaves on the same owner thread on
      schedule.
  - Restate the invariant in those terms: no owner thread ever blocks on the gateway.
  - Until Maxim answers, state that owner threads are dedicated, one per agent and never pooled. Give it a test: k+1
    agents, k parked in a thought, and the barrier still completes.
  - Part 2 §4.2's Pn ("after a tool result") should say what the tool result is under propose/settle: pending and
    `neutral`. A thought never perceives its own act's effect, only the next thought does.

## SHOULD-FIX

### S1. `boundaries.md` §2.2 skip-layer prose vs the sub-layers and §10 :: the prose forbids the dependencies the sub-layers were created for

- **The prose** says `engine.adapters.*`, `engine.protocol` and `engine.host` "import only `engine.sim`'s public
  surface, `engine.intents`, `engine.materials` types and `engine.checks`". That forbids:
  - protocol → encoding (7c → 7b);
  - agents → `adapters.sem` (7c → 7b);
  - host → loaders, protocol and adapters (8 → 7), and host → `engine.scene` (to call `from_scene`).
- **The §10 contract** forbids only cells, laws, geometry and "scene build".
- **Failure scenario.** `phase1/boundaries` encodes the prose. The protocol PR goes red on `protocol → encoding`,
  which is exactly round-1 S1's scenario, now made by the fix.
- **Fix.** State the rule as the forbidden set, which is what §10 says. Add `engine.encoding` to the restricted
  importers, since it must work on snapshot copies and never on core arrays (§4.2).

### S2. `boundaries.md` §3 "a second sealed set" :: the agent step path is put under a banned list that includes `maxim`, `os`, `pathlib` and `threading`

- **The contradiction.** "The same banned list and AST scan as the core" includes `maxim` (§3's list), but the
  adapter exists to call Maxim. The home check reads `MAXIM_DATA_HOME` (`os`), and homes are paths (`pathlib`). The
  only named exemption is "one host-only module (wall timeouts)".
- **Failure scenario.** The seal lands with `phase1/agents` and goes red on the adapter's first `import maxim`. Or
  the author widens the exemption to "the adapter", and the seal becomes vacuous.
- **Fix.**
  - Define the agent-path list as the core list minus `maxim`. Move env and path resolution to the host (layer 8),
    which passes a resolved home in.
  - State which adapter modules are in the seal, and prove each by a planted call.

### S3. `boundaries.md` §7.1, §8.1, §5.2; layer 5b :: the gateway's types have no layer-legal home

- **"Implemented by the host, injected into Maxim"** (§8.1) means `engine.host` implements Maxim's `LLMBackend`, with
  its `Token` and cancel-token types. But `protected` allows `maxim` only in named adapters. A structural Protocol
  avoids the runtime import, but not mypy's, and not the registry rule's "class implementing a Maxim protocol".
- **Upward reference.** The service protocol is in `engine.intents` (5b). It names a "frame source" for the membrane
  factory (§7.1), whose type is in `engine.sim` (6).
- **Fix.**
  - Three pieces:
    - an engine-owned `ModelGateway` protocol (request, token stream, cancel) at 5b;
    - the host's implementation at 8;
    - an `LLMBackend` shim in `engine.adapters.agents` (7c) that wraps it, and is the registered Maxim-protocol entry
      point.
  - Put the frame-source protocol in `engine.sim`, or move the service protocol up to `engine.sim` beside
    `AgentPort`.

### S4. `boundaries.md` §7.1; `npcs_and_sem.md` §6.3 :: "parked" excludes an in-flight call, which freezes the world on every thought

- **The definition.** Parked is "returned from `step`, or waiting at the gateway for a **held** response". A response
  still being generated isn't held.
- **Read literally,** the host can't step T+1 while any model call is in flight. The world then stops for every LLM
  call's full wall latency, whatever its modelled time is. That contradicts §4.5's formula, in which the world
  advances up to T+D during the call, and the early-hold design.
- **Fix.**
  - Parked = "not runnable before the next tick": returned, or waiting on any gateway call (in flight or held).
  - The dilate wait is the only thing that holds the world, at T+D.
  - Under B2's fix this becomes "returned".

### S5. `boundaries.md` §11.1; `npcs_and_sem.md` §6.2; `world_model.md` §10 #9b :: `phase1/agents` claims what arrives later, has no shipped caller, and freezes goldens before Maxim's review

- **It claims what arrives later.** The test double "runs through the real gateway, barrier and log" (part 2 §6.2).
  But "the barrier's concurrency, the gateway's threads and the meters arrive with `phase1/lanes`" (§11.1, #10).
- **It has no shipped caller.** Phase 1 has no NPCs, and no 9b row names the host code that calls `AgentPort.step`
  on the shipped path. After 9b, `execute` stops applying (the TEMPORARY marker is removed), and nothing drains its
  intents outside tests. The standing rule "a fix ships with a caller" applies.
- **It freezes goldens too early.** 9b freezes `StepOutput`, receipts and thought-request goldens while the draft's
  §9 questions, which decide their shape (B1, B2), are still open in Maxim.
- **Failure scenario.** 9b ships a port matching neither the draft nor Maxim's eventual answer. Lanes rebuilds the
  gateway path around it. Phase 4 then needs a format bump in the first NPC PR.
- **Fix.**
  - Scope 9b to a synchronous single-thread host stepper (named, in `engine.host`), which is the caller, plus the
    double. Say which tests are "through the real gateway" only from lanes.
  - Gate 9b's golden freeze on Maxim's plan review of `embeddable_agent_DRAFT.md`, or mark those types `v0`
    (unfrozen) until then.
  - Say plainly that 9b is foundations capability, measured only against the double.

### S6. `npcs_and_sem.md` §6.2; `boundaries.md` §5.3, §8.1, §10 :: the strict red gate on real Maxim is honest in spirit, but too coarse to flip cleanly

- **It is too coarse.** There is one `xfail(strict=True)` "until tier A ships". Tier A is 9 embeddable PRs plus A-pre,
  A-post and OD-A16, each shipping on its own clock. A gate that passes only when everything has landed can't show
  partial progress. When it finally XPASSes, nobody knows which piece flipped it.
- **It can fail for the wrong reason.** Without `raises=`, a red gate stays "expected failure" for any reason,
  including an `AttributeError` on an entry-point name guessed from a draft whose §9 asks "factory method or own
  module". Maxim can ship the contract under another name, and the gate stays red forever. That is a gate that can't
  turn green, the mirror image of a test that can't fail.
- **The roster row is mis-stated.** Refusing today's real Maxim roster (it holds `BashTool`) is correct behaviour,
  and that test should be green now. What is red is "a real Maxim NPC can be built and stepped".
- **Fix.**
  - One strict gate per piece, mapped to the draft's exit ids (OD-EA1–EA9, OD-WC*). Each gate uses
    `raises=MaximContractMissing`, a typed adapter error that names the piece, from a capability probe, never from a
    guessed attribute.
  - The roster-refusal test is green now.

### S7. `boundaries.md` §7.1 (`StepOutput` "intents (with `apply_us`)"), §6.2 :: the agent supplies an ordering field that every other source has stamped for it

- **The asymmetry.** Client `apply_us` is refused (§5.3), and segment times are "computed by the host from the cost
  model, never parsed from model output" (§7.4). Yet `StepOutput`'s intents carry `apply_us`, seemingly from Maxim.
- **Why it matters.** It sits in the ordering key `(apply_tick, kind_rank, apply_us, actor_id, seq)`. An agent value
  of 0 wins every same-tick tie, and any Maxim timing drift reorders the log.
- **Fix.**
  - The adapter computes `apply_us` (and `apply_tick`) from `observed_tick + L_bio` (part 2 §9) for step intents, and
    the host computes them from the cost model for thought intents.
  - `StepOutput` carries no time field. That also keeps O4's "no time field reaches cognition" symmetric.

### S8. `boundaries.md` §6.1, §6.2 :: `thought_cancelled` and `thought_failed` are world-log "inputs" that the `Simulation` can't apply, which is round-1 S6's class again

- **The contradiction.** The log "holds every input to the `Simulation`". These two kinds end thoughts, and thoughts
  live outside `Simulation` and outside replay.
- **Failure scenario.** Sim-clock's applier meets them and must no-op them by special case. Or `kind_rank` orders
  them against intents for no stated reason.
- **Fix.**
  - Classify them as **rerun inputs** (tier 2 needs a wall-decided timeout) and world-log audit records that the
    applier never reads.
  - Give them a rank, or say that the applier skips them by kind, and why.

### S9. `npcs_and_sem.md` §4.4; `world_model.md` §10 #11; `roadmap.md` Phase 1 :: three documents give three owners for in-flight thought state

- **The three owners.**
  - Part 2 §4.4: early-held results "live in the host's thought gate, agent-side ... saved with the agent home (save
    v1)".
  - world_model #11 (unchanged): "Save v0, after the lanes, so in-flight thoughts are part of the saved `Simulation`
    state".
  - Roadmap Phase 1: save v0 is "the world grid plus the scene spec. Agent homes join in Phase 4".
- **A layer problem.** A host buffer (layer 8) written into a Maxim-owned home format is unowned data.
- **Fix.**
  - The host owns a host-state section of the save: held results, in-flight requests and policy. It is separate from
    both the world checkpoint and the agent homes, which Maxim owns.
  - Correct world_model #11's rationale. Under O6, save v0 no longer needs to wait for the lanes for this reason.

### S10. `boundaries.md` §8.1 ("NPC authoring | game | `AgentFactory`"), §2.1 :: the game builds Maxim agents, so it holds the object that the adapter's checks are meant to guard

- **The bypass.** Under O6 the roster check, the home, the gateway and `AgentTime` must all be injected at
  construction. If the game calls `AgentFactory` itself, it holds a live Maxim agent. It can then call `think` or
  `apply` directly, which is a second door around the adapter's roster, home and memory gates. The engine sees the
  agent only after construction.
- **The contradiction.** That conflicts with §2.1's "game rules reach the tick as data only".
- **Fix.**
  - Construction happens only in `engine.adapters.agents`.
  - The game supplies data (roster, seed memories, arc, body instance).
  - The game drops from `maxim`'s `protected` importers, or keeps only the arc loader with a declared surface.

## NIT

- **N1. `boundaries.md` §6.1, §6.2 :: `seq` is assigned by whom?** This is round-1 N5, not folded. `step` and
  `think` (or the sink) both produce an actor's intents. Say that the adapter assigns `seq` on the owner thread, in
  production order.
- **N2. `boundaries.md` §7.1 vs §4.2 :: "a frame source" for the membrane factory vs "the frame pinned per agent".**
  Name the source as the adapter's pinned-frame holder. Otherwise the publisher's latest frame is a plausible reading,
  and it is dial-dependent.
- **N3. `boundaries.md` §10 skip-layer row :: "scene build" isn't a module,** contrary to §2.2's "every rule names a
  module".
- **N4. `boundaries.md` §4.2 Tests :: "a read from a second thread mid-step returns the frame for T−1".** Under the
  on-change cadence, it is the last published frame, which may be several ticks back.
- **N5. `npcs_and_sem.md` §6.5 cites `boundaries.md` §7.2 for the membrane factory;** it is in §7.1.
- **N6. Two `sys.setprofile` tripwires on one thread.** Overdrive's (§3, on the agent-lane thread) and Maxim's OD-A2
  (on "the thread that steps the embedded agent") would replace each other, silently making one vacuous. Say which
  one chains, or that Overdrive's runs only with Maxim's off.
- **N7. `world_model.md` §10 #2 :: still "Parts 1, 2 and 3 accepted"** before 2b. This is round-1 N8, not folded.
- **N8. Budget names differ** (`budget_exceeded` in the draft, `thought_failed(reason=budget)` here), and the draft's
  "keyword arguments work too" (§4.2) weakens the canonical request that part 2 §4.8 hashes. State the mapping, and
  ask for the frozen request object.
- **N9. Draft §4.1's `step(world_dt_us, frame)`: `frame` has no type Maxim can name** (Maxim can't import the engine).
  Overdrive pushes and pins percepts anyway (§4.3, §7.3). Say that `frame` is a Maxim-side percept protocol, or drop
  it from the draft in favour of the push.

## Round-1 findings: did they close?

| Round 1 | Verdict |
|---|---|
| B1 the agent lane is undefined | **Closed in substance:** one owner, the barrier, lanes §4 marked superseded. The thread model is ambiguous ("at a time") and fails with `think` (B2) |
| B2 mode (a) + dilation deadlock | **Partial.** Mode (a) is gone, but the no-deadlock invariant's premise is false while an owner thread parks in `think`. The cycle returns under a pooled owner (B2) |
| B3 `AgentPort` isn't the thought seam | **Partial.** The split and the gateway are right. The port doesn't match the draft (B1), and the gateway's layer home is undefined (S3) |
| S1 sibling layers | **Closed** by the sub-layers. The skip-layer prose re-forbids them (S1) |
| S2 restricted importers; writers outside core | **Closed** (stage-2 checks, `entity_key` in checks, save split, `ActionLimits.load` in loaders). N3 left |
| S3 `to_maxim_entity(world, …)` | **Closed** (frame source and sink). Naming is open (N2) |
| S4 frames mutate; cadence; thread scope | **Closed.** Test wording is stale (N4) |
| S5 no PR for agent foundations; marker | **Closed** as a row and a marker target. 9b's scope and caller are open (S5) |
| S6 `memory_write` in the world log | **Closed.** The same class recurs for cancel and fail (S8), and memory writes now have no applier (B1) |
| S7 sub-tick key | **Closed** (`apply_us`, one key). Its source for agent intents is open (S7) |
| S8 SEM paths across docs | **Closed** (OD-C6, OD-C7, §9.3 by OD id) |
| S9 [now] tags | **Closed** |
| S10 part 2 fold table; world_v2 §6 | **Closed** |
| S11 game rule seam | **Closed** (data only). NPC authoring contradicts it (S10) |
| S12 calibrations and the resolution gate | **Closed** |
| S13 slow-effect credit; instruments | **Closed** (OPEN with a red gate; declared sensors) |
| S14 tier C; `last_fired` | **Closed** (OD-A16 in tier A gating Phase 4; `last_fired` in OD-A8) |
| S15 registry check | **Closed** (mechanical rule, four plants) |
| N5 `seq` source | **Open** (N1) |
| N8 2b waits on part 3 | **Open** (N7) |
| N9 settle double credit | **Closed** |

## Verdict per cut

| Cut | Composes with O6? | Note |
|---|---|---|
| Sealed core | Yes | Agents never enter it. The second seal is mis-specified (S2) |
| Write window | Yes | Agents never hold core arrays. Frames are copies |
| Published frames | Yes | Pinned-frame naming (N2) |
| Log record | Mostly | Agent-supplied `apply_us` (S7); cancel and fail kinds (S8); `seq` (N1) |
| Layers | Yes, no cycle | Skip-rule prose (S1); gateway types (S3) |
| `AgentPort` vs the draft | **No** | B1 |
| Lane and barrier | **No, as written** | B2, S4 |
| `phase1/agents` | Sensible in intent | Scope, caller, goldens (S5); red-gate granularity (S6) |
