# DRAFT for Maxim: an embeddable agent, which a host drives (v7)

**Status:** v7 (2026-11-19) folds Maxim's review of v6; verdict SOUND (our record is
`docs/design/reviews/agent_draft_v3/maxim_review_v6.md`), with our owner's answer to its Q1 (O45). No Maxim
`src/` lands for the contract until you accept it. O-numbers are Overdrive owner decisions. Everything here is
`[engineering]`. Maxim citations are on `origin/main` **95af47d2** (the pid facts re-checked on c28b2681), with line
hints that drift. Where this draft and your candidates doc (`docs/plans/overdrive_refactor_candidates.md`) differ, the doc wins.

**Overdrive paths** are in `dennys246/Maxim-Overdrive` (private; the owner shares access), branch
`phase1/agent-v7`.

**For a new reader:** Overdrive is a game world server whose NPCs are Maxim agents, each in a spawned worker
(pickle-free framed JSON, no keys, the offline latch engaged), with the model gateway in the host. It runs on an
integer tick and replays bit for bit from an intent log; a *frame* is the snapshot a step reads. Context:
`docs/design/npcs_and_sem.md` §6.

**Ids.** Covered: OD-A10 to OD-A12, OD-A14, OD-A15, OD-A17, OD-A18, OD-I3, OD-H6. Depended on: OD-A2 to OD-A9,
OD-A16 (#1200). OD-A20 is declined by your owner; OD-A21 is argued, not needed.

| Ours | Yours | Venue (yours) |
|---|---|---|
| OD-A12 `AgentHome` | cand. A1 | a plan merged with #984 |
| OD-A7 keyed substreams | cand. A2 | a new release-gate item after 1.4.0 (your owner, 2026-11-19) |
| OD-A2, OD-A3 clock and port; OD-A4 duration; OD-A5, OD-A6, OD-A8 stamps and ids | cand. A3 (A-pre, A-post) | with #1361, M72 |
| OD-A9 `DefaultNetwork.step(now)` | none (our draft, with #1263) | — |
| OD-A10, OD-A11, OD-A17 entry point, roster, leak closure | cand. A4 | a section of this plan |
| OD-I3 pickle load | cand. A5, #1685 | issue |
| OD-I1 `x or time.time()` | #1684 | issue |
| OD-A18 dispatch/settle, writes applied at settle | cand. B2 (#1150) with A6 | #1150 |
| OD-A14, OD-A15 the cut and stepped `think` | cand. B1 (with B3) | hybrid §A.1b, after 1.4.0 |
| inner tool loop | cand. C1 | prereg |

## 1. What v7 changes

- **A log segment per restore (O45, §2),** your Q1 alternative: the segment number is part of `session_id`, so
  O44's floor is no longer a requirement, and nothing goes on your resume stage's question list.
- **OD-EA16 (§6) takes your Q2 request:** a refusal's pid never appears in a GL3.B2 row.

v6's folds (the pid's owners, G17, the settle invariant, O43, tense) and v4's O38 to O40 stand.

## 2. The contract

Construction goes through `AgentFactory` (OD-A10), a separate constructor beside `MaximHandle`
(`console/handle.py:176`); deliberation is its own module.

| Call | Does | Returns |
|---|---|---|
| `step(agent, world_dt_us, frame)` (the host's port is in ticks; its adapter converts) | advances drives, the experience clock and the substrate; reads percepts | a `StepOutput` value: intents (each with its invocation pid), proposed writes, thought requests |
| `think(agent, handle, reply \| None)` | runs deliberation to its next model call; may read, never write | `Pending(request) \| ThoughtOutput`, with proposed writes (retrieval strengthening included) as values |
| `settle(agent, receipts, writes)` | the only write door: credit from receipts, and the host-gated writes (your A6), published through the agent bus, never into the stores directly | an ack |

Outside the port, as lifecycle calls: `save()` / `load(home)` (under the home only, pickle-free; an ack or a typed
refusal) and `consolidate(agent, budget)` (below).

- **The continuation is split by owner.** The **host** keeps a header: thought id and
  kind, the triggering-input id, budget counters, the PFC cycle index and `max_cycles`, a copy of `basis_seq`, each
  segment's landing time, cancel status and the delivered prefix. The **agent** keeps a body: the partial proposal,
  the transcript, enrichment results, and the loop locals that aren't values yet, saved in its home, opaque to the host, which enforces budgets from its header. A census of
  think-path writes comes first. An unknown body version loads as `thought_failed(reloaded)`.
- **`basis_seq` is the agent's:** its afferent scheduler's high-water seq (`thalamic_relay.md` §5.5,
  `preempted_since`). The host may hold a copy and never computes it. LLM-proposal staleness waits on GL3.B7, unbuilt.
- **Staleness is §A.1b.5's (O38).** A reply is stale only when a non-self-caused event on a tracked right arrives
  after its `basis_seq`; it goes through the typed pre-emption handler (§A.1b.4), never `_drop_stale_proposal`, and
  `think` returns a re-plan `Pending` (counted) or `ThoughtOutput(abandoned)`. **Tracked rights** are TR6's declared
  preemption rights, today only `nociceptive_fast`'s (GL3.B4). Embedded, they reach the agent through `step`'s frame; a non-danger track counts only when a plan rung
  names it (your owner). Per your condition, this stays out of B2.
- **The embedded efference copy, and who owns the pid (your Q1 answer).** The agent's intents run in the host.
  B2's dispatch is the `Executor._run_started` equivalent: inside the worker it draws one `PhysicalEventId` per intent from the agent's own `EventSequencer`, under its lock, and puts it
  on the intent value. The sequencer is the mint's authority, GL3.B2 the contract (`thalamic_relay.md` §5.2, §6),
  never B2 or the host. The host logs the pid with the intent and copies it, as `caused_by`, onto every receipt and
  frame event the intent causes; it never mints or computes one. The executor's `invocation_id`
  (`str(uuid.uuid4())`, `executor.py:512`) is never the embedded pid or a replay join key. Without it every self-caused
  reafference reads as non-self-caused.
- **The settle invariant.** Every minted pid comes back in exactly one terminal receipt, executed or a typed
  refusal, and no receipt arrives without a minted pid. A refusal receipt is the pid's outcome, not a physical
  event. The host's refusals, deferrals past a budget and drops all end in a typed refusal receipt carrying the pid
  (OD-EA16); when a worker dies, the host writes a typed `agent_failed` refusal receipt for each in-flight pid (O44).
- **Replay ids (O43, O45).** `session_id` is derived from the intent log's header (the log's root id, the NPC key
  and the segment number), never the wall clock or a uuid. Each restore opens a new log segment, its number recorded
  in the header so replay reproduces it; ids from different segments can't collide whatever the seq. The sequencer's
  high-water seq is saved in the NPC's agent home, so a loaded save continues the sequence. O44's floor stays only as
  a host-side test that no new pid equals a logged one. Your §5.5 scopes determinism to single-threaded loop paths: our one worker per
  agent, stepped by one thread, is inside it, and we never pool agents on a worker thread.
- **Unchanged from v5:** the request is a value (rendered text, sampling, a model **role**,
  the template version, `tools is None`) produced at the `LLMRouter._complete_text` cut
  (`models/language/router.py:958`), the host stamping priority and deadline (B3) outside any cache key and supplying
  the bound model's `n_ctx` and tokenizer (`token_counter`) to the `PromptBudgeter`
  (`agents/prompt_budgeter.py:65`), required at construction; the reply is `complete(text)`, with reserved
  `cancelled(prefix)` and `truncated(prefix, reason)` carrying the host-delivered speech, a top-level field emitted
  first; the robot keeps `_complete_text_abandonable` (`router.py:998`), and B1 fixes the shape after 1.4.0; replay
  uses recorded replies, a versioned host type. No reply reaches the parse-failure template, which still echoes
  `triggering_input` (`agents/llm_fallback.py:267`): an unparseable reply ends as `thought_failed(reason=parse)`.
  Cognition tools go through follow-ups until your C1 decides; `environment.step` (`runtime/tool_dispatch.py:1574`)
  gets no environment embedded (B2's call); the robot path drives the same `think` through a thin driver (OD-EA14,
  OD-EA15). Budgets are per triggering input and per agent per world minute; a host-called `think` never consults
  `llm_submit_interval` (OD-H6, `runtime/loop_controller.py:154`; part of B1).
- **Consolidation is its own bounded host call** (your owner): today only at session end
  (`integration/session_end.py:78`, its stages skipped by `_fits` on wall time). World time decides when (the NPC's sleep), deterministic units bound the compute, the wall clock is only a logged,
  typed abort, through an entry point that doesn't end the session; `save()` never takes `MaximHandle.stop`'s
  contract (`console/handle.py:741`).

## 3. The embedded-path leak closure (OD-A17; your cand. A4)

Unchanged from v4: A4's list and guards, plus no model backend in the embedded agent, so the second model doors
(`runtime/bootstrap.py:623`, `bridges/tool_pain_bridge.py:806`, `agents/fear_agent.py:317`) fail closed; the static
ban on `utils/audit.py` (blind spot: `importlib` strings, so our worker checks `sys.modules`); no env reads (A4 waits
for A1).

## 4. Clock, randomness and duration: yours, with our conditions

- **The machinery clock and perceived-time port** are A3's (`ExperienceClockDriver`, `runtime/experience_time.py:36`;
  the ban extends M72), with the planted-render test split as A3 has it. Our port carries coarse world time.
- **Keyed substreams (O40)** are `utils/seeding.py::make_agent_rng(base_seed, agent_id)` (`:79`), extended with a
  stream argument as a new release-gate item after 1.4.0. Your owner keeps exactly `sha256(f"{base_seed}:{agent_id}")`
  and forbids `:` in NPC keys and stream names; our loaders refuse a `:` in either. `agent_id` is the persisted NPC
  key; `base_seed` is the log root's.
- **Tool duration (OD-A4):** `exec_elapsed` is wall time (`tool_dispatch.py:1419`), and `_observe_energy_cost`
  (`:695`) books NEGATIVE above 2.0 s; embedded, the host supplies it in world time, the root fix.
- **Anchor similarity (OD-A20): declined, noted, as you verified it.** Your owner keeps event similarity on the
  host calendar (#1361 S3b). So (a) the 0.01 threshold (`nac.py:3638`) can drop a node, and a receipt whose only node
  drops books nothing; (b) anchor-only nodes set at different host times split differently; (c)
  `TemporalSignature.from_timestamp` (`time/temporal_signature.py:60`) reads local time, so timezone and DST move
  credit. A known divergence, from your code and our arithmetic, not a run: two strict red gates will carry the
  evidence once our agent PR lands them.
- **Forgetting on the wall clock, a second known divergence.** `Hippocampus.sleep` scores retention on
  `time.time()` (`memory/hippocampus_consolidation.py:117`): a memory accessed once and unlinked goes after 3.36 wall
  days, pauses included. It stays with #1361 Q5; a strict red gate will carry it once our agent PR lands it.
- **τ_elig (OD-A21):** against #1361's decided Q1, unchanged from v4; your owner's, **not** blocking.

## 5. The build, in your order

Your §Order governs: step 1, A3 A-pre, A5, #1684 and A2's existing parts, with `AgentHome` (A1) beside #984; step 2,
A3 A-post; step 3, the entry point, sealed roster (OD-A10, OD-A11) and leak closure (A4), whose closure owns the
background-worker thread through `build_memory_hub(start_background_workers=False)` (`runtime/bio_stack.py:489`,
the start at `:654`); step 4, dispatch/settle (B2, #1150, with A6), carrying provenance by source actor, D53
`outcome_valence`, OD-A16's keys, `environment.step`, the settle invariant and the invocation pid on each
dispatched intent; step 5, the stepped `think` (B1, B3) after the cut. Our condition (OD-I3): no home reachable
from saves before #1685. §6's red gates come first.

**Step 4's pid depends on an unbuilt stage.** `PhysicalEventId` and the per-agent `EventSequencer` come with your
autonomic plan's post-fence resume stage (G17); neither is in `src` at 95af47d2 or c28b2681. B2 may wait on that
stage, or land with the field reserved and unfilled (null), never a stand-in (no uuid, no executor `invocation_id`).
Our host accepts null there until the type exists, then refuses any non-null value that isn't a pid.

**Before 1.4.0 (your M89 reading):** steps 1–4 may land if A4's entry point exposes no `think`, `Pending` or
continuation, and §2's basis and staleness stay out of B2.

**What our first NPC needs (O29):** #1361 S3a, S3b and S4; OD-A2 to OD-A11; the host-driven worker thread (A4's
closure); OD-A14 to OD-A18; #1684 and #1685; G17's pid. OD-A20 is needed but declined, so our replay exit carries
known divergences. Not blocking: #1361 S5 and S6, OD-A21, and OD-A12's store routing.

## 6. Exit tests

Where you have the test, ours is a configuration of it.

| # | Passes when | Yours |
|---|---|---|
| OD-EA1 | a planted `BashTool` in the roster makes construction refuse, naming it | A4 |
| OD-EA2 | two agents in one process never open the same file | A1's filesystem trace |
| OD-EA4 | no store changes until `settle`, then exactly the returned writes, through the agent bus; a write planted in the parallel dispatch path is refused | B2/A6 |
| OD-EA5 | the state digest is identical whether each reply returns instantly or after a seeded random delay | B1's gate |
| OD-EA6 | agent A's digest is identical alone, beside B, reversed and concurrent (proven by a planted global `random`) | A2 (partly) |
| OD-EA7 | the thread count is unchanged by building and stepping | `1263.thread-guard`, configured |
| OD-EA8 | `cancelled(prefix)` records the delivered prefix as said and the thought as cancelled; no reply reaches the parse-failure template | A4/B1 |
| OD-EA9 | stubs that request a follow-up on every reply, ask for 3 PFC cycles forever, or return 100,000 tokens all stop at the host's budget | none found |
| OD-EA10 | §3's closure tests pass, and a planted read in a lazy path fails the static ban | A4 |
| OD-EA11 | a **machinery**-clock sentinel never reaches a prompt in any form; an origin offset changes no prompt; offset and scale change no render on a frozen store | A3's planted-render test, split |
| OD-EA12 | several traces credited by one receipt share it identically between agents stepped every tick and every *n*th tick | ours, against S3b (your owner: G2b is not widened) |
| OD-EA13 | a stub that calls a model outside `think` fails closed, naming the call | none found |
| OD-EA14 | B1 robot parity: the robot path through the thin driver gives today's state digest, bit for bit, on recorded replies (Exp 49, Exp 60) | B1's gate |
| OD-EA15 | B2 robot parity: the robot settles right after dispatch, with today's digest, bit for bit, on recorded replies plus recorded or injected tool durations (Exp 49, Exp 60), the digest covering B2's side-effect list | B2's guard |
| OD-EA16 | every minted pid resolves in exactly one terminal receipt, for refused, deferred, dropped and `agent_failed` intents too; no receipt carries an unminted pid; refusals book no physical event, and a refusal's pid never appears in a GL3.B2 row | ours, beside GL3.B2's gate |

OD-EA3 (no pickle) is #1685. OD-EA15's tool duration is in the fixture (OD-A4's root fix), or its exclusion is
named in the digest's definition.

## 7. Questions left

**M16 (new, 2026-11-21): can an embedded body step every tick without cognition?** Our stimulus design steps every
body each tick and runs cognition slower (`sem_stimuli.md` D5). Your G1–G4 audit calls the `SensorEncoder` body
world the only path that acts without the LLM (`DECISIONS.md`), and `agentic_runtime` already degrades to it
(`bounded_stop.md`). If not, every tick is a full step, or contacts between steps go unfelt.

v6's two are answered: **a host-supplied floor** (we take your segment alternative, O45, §2), and **GL3.B2's gate**
(unchanged; OD-EA16 adds that a refusal's pid never appears in a GL3.B2 row, §6).

Searched, nothing found: OD-EA9; a `DECISIONS.md` entry for the host-driven mode (ours:
`docs/maxim_upstream/decisions_entry_DRAFT.md`).

## 8. What it argues against

Mode-based containment (`allowed_dirs`) as the security model when the prompt carries strangers' words, and the
process-wide data home. Both are right for one robot and its operator.
