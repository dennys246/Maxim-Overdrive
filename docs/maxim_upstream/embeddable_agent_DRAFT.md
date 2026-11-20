# DRAFT for Maxim: an embeddable agent, which a host drives (v5)

**Status:** v5 (2026-11-19) folds Maxim's delta review of v4 (SOUND WITH CONDITIONS; our record is
`docs/design/reviews/agent_draft_v3/maxim_delta_review.md`) and your owner's decisions in it. v4 folded your review
of v3 (`maxim_review.md`). No Maxim `src/` lands for the contract until you accept it. O-numbers are Overdrive owner
decisions. Everything here is `[engineering]`. Maxim citations are on `origin/main` **95af47d2**, with line hints
that drift. Where this draft and your candidates doc (`docs/plans/overdrive_refactor_candidates.md`) differ, the doc
wins and §7 asks.

**Overdrive paths** are in `dennys246/Maxim-Overdrive` (private; the owner shares access), branch
`phase1/agent-delta`.

**For a reader who hasn't read Overdrive.** Overdrive is a game world server whose NPCs are Maxim agents. It runs on
an integer tick and replays bit for bit from an intent log. Each real agent runs in its own spawned worker process
(pickle-free framed JSON, no keys, the offline latch engaged); the model gateway stays in the host. A *frame* is the world snapshot a step reads. Optional context: `docs/design/npcs_and_sem.md` §6 and
`docs/roadmap.md` Phase 3 (the ids).

**Ids.** This draft covers OD-A10 to OD-A12, OD-A14, OD-A15, OD-A17, OD-A18, OD-I3 and OD-H6. It depends on OD-A2 to
OD-A9 and OD-A16 (an amendment to `tool_failure_credit.md`, #1200); OD-A20 (§4) is declined by your owner and
OD-A21 is argued, not needed.

| Ours | Yours | Venue (yours) |
|---|---|---|
| OD-A12 `AgentHome` | cand. A1 | a plan merged with #984 |
| OD-A7 keyed substreams | cand. A2 | a new release-gate item after 1.4.0 (your owner, 2026-11-19) |
| OD-A2, OD-A3 clock and port; OD-A4 duration; OD-A5, OD-A6, OD-A8 stamps and ids | cand. A3 (A-pre, A-post) | with #1361, M72 |
| OD-A9 `DefaultNetwork.step(now)` | none (our separate draft, with #1263) | — |
| OD-A10, OD-A11, OD-A17 entry point, roster, leak closure | cand. A4 | a section of this plan |
| OD-I3 pickle load | cand. A5, #1685 | issue |
| OD-I1 `x or time.time()` | #1684 | issue |
| OD-A18 dispatch/settle, writes applied at settle | cand. B2 (#1150) with A6 | #1150 |
| OD-A14, OD-A15 the cut and stepped `think` | cand. B1 (with B3) | hybrid §A.1b, after 1.4.0 |
| inner tool loop | cand. C1 | prereg |

## 1. What v5 changes

- **The embedded efference copy (§2):** every frame and receipt event an agent's intent causes carries that
  intent's invocation pid.
- **OD-A20 restated wider (§4):** the calendar can drop an anchor, splits anchors set at different times
  differently, and moves with the replay machine's timezone. v4's "12 h pause → ≈0.70" predated our erratum, and
  the erratum's "sharing only" was too narrow.
- **A second known divergence:** `Hippocampus.sleep` forgets on `time.time()` (§4), staying with #1361 Q5.
- **OD-EA15 names its fixture; OD-EA12 is ours** against S3b (§6). Your §7 answers and owner decisions are folded.

v4's O38 (§A.1b.5 staleness), O39 (`apply` merged into `settle`) and O40 (`make_agent_rng`) stand. A thought is up
to 3 model calls (`runtime/agent_loop.py:3110-3111`).

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

- **The continuation is split by owner, and is not the whole agent.** The **host** keeps a header: thought id and
  kind, the triggering-input id, budget counters, the PFC cycle index and `max_cycles`, a copy of `basis_seq`, each
  segment's landing time, cancel status and the delivered prefix. The **agent** keeps a body: the partial proposal,
  the transcript, enrichment results, and the loop locals that aren't values yet (the same-tool counter,
  `rejection_followups`), saved in its home, opaque to the host, which enforces budgets from its header. A census of
  today's think-path writes is the plan's first step. An unknown body version loads as `thought_failed(reloaded)`.
- **`basis_seq` is the agent's:** its afferent scheduler's high-water seq (`thalamic_relay.md` §5.5,
  `preempted_since`). The host may hold a copy and never computes it. LLM-proposal staleness waits on GL3.B7, unbuilt.
- **Staleness is §A.1b.5's (O38).** A reply is stale only when a non-self-caused event on a tracked right arrives
  after its `basis_seq`; it goes through the typed pre-emption handler (§A.1b.4), never `_drop_stale_proposal`, and
  `think` returns a re-plan `Pending` (counted) or `ThoughtOutput(abandoned)`. **Tracked rights** are the declared
  preemption rights on afferent tracks (§A.1b.5, `thalamic_relay.md` TR6); today only `nociceptive_fast`'s, from
  GL3.B4. Embedded, they reach the agent through `step`'s frame; a non-danger track counts only when a plan rung
  names it (your owner). Per your condition, this stays out of B2.
- **The embedded efference copy.** Embedded, the agent's intents run in the host, so attribution needs the host's
  help. Each intent in `StepOutput` carries its invocation pid (`PhysicalEventId`, GL3.B2's join,
  `thalamic_relay.md` §5.2), minted by the agent at dispatch, never by the host. The host logs it with the intent,
  and every receipt and frame event that intent causes carries it, as `caused_by`. Without it every self-caused
  reafference reads as non-self-caused, and every in-flight reply goes stale.
- **The request** is a value: rendered text, sampling parameters, a model **role** (speech or plan, bound by the
  host), the template version, and `tools is None`. It is produced at the `LLMRouter._complete_text` cut
  (`models/language/router.py:958`), so the router-only invariant holds. The host stamps priority and deadline (your
  B3), outside any cache key. **The host supplies the bound model's `n_ctx` and its tokenizer** (`token_counter`) to
  the `PromptBudgeter` (`agents/prompt_budgeter.py:65`), required at construction: a budgeter that believes another
  `n_ctx`, or counts with another tokenizer, overruns the server silently (`docs/lessons/sim-n-ctx-config-drift.md`).
- **The reply** is a value: `complete(text)`, with reserved `cancelled(prefix)` and `truncated(prefix, reason)`, where
  the prefix is the speech the host delivered and validated. Speech is a top-level field emitted first. Cancel is
  resuming with `cancelled(prefix)`. The robot keeps `_complete_text_abandonable` (`router.py:998`); B1 fixes the
  shape in its plan after 1.4.0. Replay uses recorded replies, logged as a versioned host type.
- **No reply reaches the parse-failure template** (A4's bypass, with B1): an unparseable reply ends the thought as
  `thought_failed(reason=parse)`. After #1691 a fallback books no NAc credit, but `generate_llm_fallback`
  (`agents/llm_fallback.py:267`, called at `agents/llm_worker.py:1301-1318`) still echoes `triggering_input`.
- **Unchanged from v4:** cognition tools go through follow-ups until your C1 decides; `environment.step`
  (`runtime/tool_dispatch.py:1574`) is passed no environment embedded (B2's call); the robot path drives the same
  `think` through a thin driver, gated by OD-EA14 and OD-EA15 (§6).
- **Budgets** per triggering input and per agent per world minute. **Submit cadence (OD-H6):** a host-called
  `think` never consults `llm_submit_interval` (`runtime/loop_controller.py:154`); part of B1.
- **Consolidation is its own bounded host call** (your owner). Today it runs only at session end
  (`integration/session_end.py::end_session`, `:78`): flush and persist; `_consolidate` (`:241`): `Hippocampus.sleep`,
  then semantic promotion, ATL and AG, each skipped by `_fits` on a wall-clock allowance; re-save. Your owner's
  decision: **world time decides when** (the host calls it when the NPC sleeps), **deterministic units bound the
  compute** (steps, item counts), and the wall clock acts only as a logged, typed abort. It needs an entry point that
  doesn't end the session. `save()` never takes `MaximHandle.stop`'s contract (`console/handle.py:741`).

## 3. The embedded-path leak closure (OD-A17; your cand. A4)

Unchanged from v4: A4's list and guards as written, plus no model backend in the embedded agent, so
`AdaptivePlanner(llm=...)` (`runtime/bootstrap.py:623`), the `ToolPainBridge` reflection
(`bridges/tool_pain_bridge.py:806`) and `FearAgent._analyze_with_llm` (`agents/fear_agent.py:317`) fail closed; the
static ban on `utils/audit.py` with `lint_dead_imports`' resolver (blind spot: `importlib` strings, so our worker
checks `sys.modules` after a scripted run); no env reads (A4 waits for A1).

## 4. Clock, randomness and duration: yours, with our conditions

- **The machinery clock and perceived-time port** are A3's (`ExperienceClockDriver`, `runtime/experience_time.py:36`;
  the ban extends M72), with the planted-render test split as A3 has it. Our port carries coarse world time.
- **Keyed substreams (O40)** are `utils/seeding.py::make_agent_rng(base_seed, agent_id)` (`:79`), extended with a
  stream argument as a new release-gate item after 1.4.0. Your owner keeps exactly `sha256(f"{base_seed}:{agent_id}")`
  and forbids `:` in NPC keys and stream names, so today's `agent_id = "npc_key:stream"` gives the same seed as the
  later stream argument; our loaders refuse a `:` in either. `agent_id` is the persisted NPC key, never an ordinal;
  `base_seed` is the log root's.
- **Tool duration (OD-A4):** `execute_and_learn` measures `exec_elapsed` on the wall clock (`tool_dispatch.py:1419`),
  and `_observe_energy_cost` (`:695`) books a NEGATIVE NAc valence above 2.0 s. Embedded, the host supplies it in
  world time: the root fix.
- **Anchor similarity (OD-A20): declined, noted.** Your owner keeps event similarity on the host calendar (#1361
  S3b); events and anchors age on the experience clock. Credit is normalised (`NAc.distribute_reward`,
  `decisions/nac.py:3587`; `TemporalCreditDistributor.distribute`), but the calendar moves more than sharing:
  - (a) an anchor counts only when 0.3 × similarity × activation > 0.01 (`nac.py:3638`), so the calendar can drop a
    node, and a receipt whose only node drops books nothing;
  - (b) anchor-only nodes set at different host times split differently among themselves;
  - (c) `TemporalSignature.from_timestamp` (`time/temporal_signature.py:60`) uses local time, so the replay machine's
    timezone and DST move credit: a local midnight or a DST change inside the interval steps the similarity.

  Point (c) is a cross-machine effect, which your owner's decision of 2026-11-19 may not have weighed; our strict red
  gates will carry the evidence. We record all three as a known divergence and bring it once real NPCs run.
- **Forgetting on the wall clock: a second known divergence.** `Hippocampus.sleep` scores retention on
  `time.time()` against `accessed_at` (`memory/hippocampus_consolidation.py:117`). On the default access-based
  strategy, a memory accessed once and unlinked is removed once more than 3.36 wall days separate its access from
  the pass, so what an NPC forgets depends on wall time, pauses included. It stays with #1361 Q5; we carry a strict
  red gate and no workaround.
- **τ_elig (OD-A21):** against #1361's decided Q1, unchanged from v4 (9.49 passes, 0.32–0.95 s today, against
  4.75 s after S3a; the striatal window is about 0.3–2 s, Yagishita et al. 2014). Your owner's; **not** blocking.

## 5. The build, in your order

Your §Order governs: step 1, A3 A-pre, A5, #1684 and A2's existing parts, with `AgentHome` (A1) beside #984; step 2,
A3 A-post; step 3, the entry point, sealed roster (OD-A10, OD-A11) and leak closure (A4), whose closure owns the
background-worker thread through `build_memory_hub(start_background_workers=False)` (`runtime/bio_stack.py:489`,
the start at `:654`); step 4, dispatch/settle (B2, #1150, with A6), carrying provenance by source actor, D53
`outcome_valence`, OD-A16's keys, `environment.step` and the invocation pid on each dispatched intent; step 5, the
stepped `think` (B1, B3) after the cut. Our condition (OD-I3): no home reachable from saves before #1685. §6's red
gates come first.

**Before 1.4.0 (your M89 reading):** steps 1–4 may land before the cut, provided the A4 entry point exposes no
`think`, `Pending` or continuation before it, and §2's basis and staleness stay out of B2.

**What our first NPC needs (O29):** #1361 S3a, S3b and S4; OD-A2 to OD-A11; the host-driven worker thread (A4's
closure); OD-A14 to OD-A18; #1684 and #1685. OD-A20 would be needed, but is declined, so our replay exit carries
known divergences. Not blocking: #1361 S5 and S6, OD-A21, and OD-A12's store routing.

## 6. Exit tests

Where you have the test, ours is a configuration of it.

| # | Passes when | Yours |
|---|---|---|
| OD-EA1 | a planted `BashTool` in the roster makes construction refuse, naming it | A4 |
| OD-EA2 | two agents in one process never open the same file | A1's filesystem trace |
| OD-EA4 | no store changes until `settle`; then exactly the returned writes, through the agent bus; a memory write planted in the parallel dispatch path is refused | B2/A6 |
| OD-EA5 | the state digest is identical whether each reply returns instantly or after a seeded random delay | B1's gate |
| OD-EA6 | agent A's digest is identical alone, beside B, reversed and concurrent (proven by a planted global `random`) | A2 (partly) |
| OD-EA7 | the thread count is unchanged by building and stepping | `1263.thread-guard`, configured |
| OD-EA8 | `cancelled(prefix)` records the host-delivered prefix as said and the thought as cancelled; no reply, cancelled or unparseable, reaches the parse-failure template | A4/B1 |
| OD-EA9 | stubs that request a follow-up on every reply, ask for 3 PFC cycles forever, or return 100,000 tokens all stop at the host's budget | none found |
| OD-EA10 | §3's closure tests pass, and a planted read in a lazy path fails the static ban | A4 |
| OD-EA11 | a sentinel in the **machinery** clock never appears in a prompt in raw, clock or date form; an origin offset changes no prompt end to end; offset and scale change no render on a frozen store | A3's planted-render test, split |
| OD-EA12 | several traces credited by one receipt share it identically between agents stepped every tick and every *n*th tick | ours, against S3b (your owner: G2b is not widened) |
| OD-EA13 | a stub that calls a model outside `think` fails closed, naming the call | none found |
| OD-EA14 | B1 robot parity: the robot path through the thin driver gives today's state digest, bit for bit, on recorded replies (Exp 49, Exp 60) | B1's gate |
| OD-EA15 | B2 robot parity: the robot path settles immediately after dispatch, with today's digest, bit for bit, on a fixture of recorded replies plus recorded or injected tool durations (Exp 49, Exp 60); the digest covers B2's side-effect list | B2's guard |

OD-EA3 (no pickle) is #1685. **OD-EA15's duration:** today `exec_elapsed` (wall time) feeds
`_observe_energy_cost`, so the digest cannot be bit-identical unless the duration is in the fixture. We prefer that,
since host-supplied duration is OD-A4's root fix; excluding it instead must be named in the digest's definition.

## 7. Questions left

Your delta review answered v4's four; §2, §4 and §6 fold them. One remains:

1. **Who mints the embedded invocation pid?** We assume B2's dispatch mints it at the `Executor._run_started`
   equivalent and puts it on the intent value, so the host only copies it (§2). Is that B2's, or GL3.B2's?

Searched, nothing found: OD-EA9; a `DECISIONS.md` entry for the host-driven mode (ours:
`docs/maxim_upstream/decisions_entry_DRAFT.md`).

## 8. What it argues against

Mode-based containment (`allowed_dirs`) as the security model when the prompt carries strangers' words, and the
process-wide data home. Both are right for one robot and its operator.
