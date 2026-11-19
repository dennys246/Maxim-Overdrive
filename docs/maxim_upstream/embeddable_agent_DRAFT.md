# DRAFT for Maxim: an embeddable agent, which a host drives (v4)

**Status:** v4 (2026-11-19) folds Maxim's plan review of v3 (SOUND WITH CONDITIONS; our record is
`docs/design/reviews/agent_draft_v3/maxim_review.md`) and your owner's decisions on Q2, Q9 and Q10 of the same day.
It is our answer to that review; no Maxim `src/` lands for the contract until you accept it. O-numbers are Overdrive
owner decisions. Everything here is `[engineering]`. Maxim citations are on `origin/main` **f0b1cea4**, with line
hints that drift. Where this draft and your candidates doc (`docs/plans/overdrive_refactor_candidates.md`) differ,
the doc wins and §7 asks.

**Overdrive paths** are in `dennys246/Maxim-Overdrive` (private; the owner shares access), branch
`phase1/agent-review`.

**For a reader who hasn't read Overdrive.** Overdrive is a game world server whose NPCs are Maxim agents. It runs on
an integer tick and replays bit for bit from an intent log. Each real agent runs in its own spawned worker process
(pickle-free framed JSON, an allowlisted environment, no keys, the offline latch engaged); the model gateway stays in
the host. A *frame* is the world snapshot a step reads. Optional context: `docs/design/npcs_and_sem.md` §6 (the port, reopened by
your review under O36) and `docs/roadmap.md` Phase 3 (the ids).

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

## 1. What v4 changes

- **Staleness is your §A.1b.5 (O38);** "superseded" and our frame-id basis are dropped (a frame id changes every
  step, so every reply went stale).
- **`apply` is merged into `settle` (O39):** three host calls. We had no front-gate reason for a second write door.
- **One randomness derivation (O40):** your `make_agent_rng`, with a stream argument.
- **Gone:** the shortcut section (you deleted it, #1689, PR #1694) and the `MAXIM_DATA_HOME` exception.
- **Robot-parity exit tests** for B1 and B2 (OD-EA14, OD-EA15), your DO-NOT-BUILD.
- **OD-A20 is noted, not adopted;** we carry it as a known divergence (§4).

Still true from v1: a thought can be up to 3 model calls with a percept source, 2 without
(`runtime/agent_loop.py:3110-3111`; `llm.deliberation_max_cycles` overrides it).

## 2. The contract

Construction goes through `AgentFactory` (OD-A10), a separate constructor beside `MaximHandle`
(`console/handle.py:176`); deliberation is its own module.

| Call | Does | Returns |
|---|---|---|
| `step(agent, world_dt_us, frame)` (the host's port is in ticks; its adapter converts) | advances drives, the experience clock and the substrate; reads percepts | a `StepOutput` value: intents, proposed writes, thought requests |
| `think(agent, handle, reply \| None)` | runs deliberation to its next model call; may read, never write | `Pending(request) \| ThoughtOutput`, with proposed writes (retrieval strengthening included) as values |
| `settle(agent, receipts, writes)` | the only write door: credit from receipts, and the host-gated writes (your A6), published through the agent bus, never into the stores directly | an ack |

Outside the port, as lifecycle calls: `save()` / `load(home)` (under the home only, pickle-free; an ack or a typed
refusal) and `consolidate(agent, budget)` (below).

- **The continuation is split by owner, and is not the whole agent.** The **host** keeps a header: thought id and
  kind, the triggering-input id, budget counters, the PFC cycle index and `max_cycles`, `basis_seq` (§A.1b.5), each
  segment's landing time, cancel status and the delivered prefix. The **agent** keeps a body: the partial proposal,
  the transcript, enrichment results, and the loop locals that aren't values yet (the same-tool counter,
  `rejection_followups`), saved in its home, opaque to the host, which enforces budgets from its header. A census of today's think-path writes is the plan's first step.
- **The body is versioned:** an unknown body version loads as a logged `thought_failed(reloaded)`, never a refused
  save.
- **Staleness is §A.1b.5's (O38).** A reply is stale only when a non-self-caused event on a tracked right arrives
  after its `basis_seq`; the agent's own dispatched actions are excluded by attribution (efference copy, the
  invocation-pid join or TR23's writer kind). A stale reply goes through the typed pre-emption handler (§A.1b.4),
  never `_drop_stale_proposal`'s planning-failure path, which counts toward `planning_failed`; `think` then returns a
  re-plan `Pending` (counted) or `ThoughtOutput(abandoned)`. Embedded, tracked-right events reach the agent through
  `step`'s frame. Per your condition, this stays out of B2.
- **The request** is a value: rendered text, sampling parameters, a model **role** (speech or plan, bound by the
  host), the template version, and `tools is None`. It is produced at the `LLMRouter._complete_text` cut
  (`models/language/router.py:958`), so the router-only invariant holds. The host stamps priority and deadline (your
  B3), outside any cache key. **The host supplies the bound model's context size** to the `PromptBudgeter`, a required
  collaborator at construction: a budgeter that believes another `n_ctx` overruns the server silently
  (`docs/lessons/sim-n-ctx-config-drift.md`).
- **The reply** is a value: `complete(text)`, with reserved `cancelled(prefix)` and `truncated(prefix, reason)`, where
  the prefix is the speech the host delivered and validated. Speech is a top-level field emitted first. Cancel is
  resuming with `cancelled(prefix)`. The robot keeps `_complete_text_abandonable` (`router.py:998`); B1 reserves the
  two variants and the speech field, and fixes the shape in its plan after 1.4.0.
- **Replies are recorded, and the record is the host's:** replay uses recorded replies, never a model, and the log
  stores a versioned host type the adapter maps your reply values into, so B1's shape can change freely.
- **No reply reaches the parse-failure template** (A4's bypass, with B1): an unparseable reply ends the thought as
  `thought_failed(reason=parse)`. After #1691 a fallback reply books no NAc credit, but `generate_llm_fallback`
  (`agents/llm_fallback.py:267`, templates `:296-304`, called at `agents/llm_worker.py:1301-1318`) still echoes
  `triggering_input`.
- **Cognition tools go through follow-ups** until your C1 decides otherwise.
- **`environment.step`** (`runtime/tool_dispatch.py:1574`): our position for B2 is yours, that the embedded roster
  passes no environment and the follow-up arrives in receipts.
- **The robot path drives the same `think`** through a thin driver, gated by OD-EA14 and OD-EA15 (§6).
- **Budgets per triggering input and per agent per world minute** across follow-up chains: PFC cycles,
  `parallel_actions` (a grammar `maxItems`), `next_actions` length, tokens, memory writes and bytes.
- **Submit cadence (OD-H6):** a host-called `think` never consults `llm_submit_interval`
  (`runtime/loop_controller.py:154`); part of B1, not your C3.
- **Consolidation is its own bounded host call** (your owner, 2026-11-19). The host calls it in world time, when the
  world says the NPC consolidates (during its sleep, say), with a budget; `save()` stays separate and never takes
  `MaximHandle.stop`'s contract (`:741`), since `stop` runs blocking consolidation.

## 3. The embedded-path leak closure (OD-A17; your cand. A4)

We take A4's list and guards as written. Ours adds or differs only here:
- **No model backend in the embedded agent at all,** so the model calls outside `think` fail closed, each named:
  `AdaptivePlanner(llm=...)` (`runtime/bootstrap.py:623` → `planning/adaptive_planner.py:487`), the
  `ToolPainBridge` reflection on the settle path (`bridges/tool_pain_bridge.py:806`, its error dropped) and
  `FearAgent._analyze_with_llm` (`agents/fear_agent.py:303`, the call at `:317`). Each becomes a request, or is off.
- **The static ban rides on `utils/audit.py`** (the CI-gated AST import scan) with `lint_dead_imports`' any-depth
  resolver. It names at least `maxim.embodied_runtime` (the phrase commands,
  `embodied_runtime/input_handlers.py::_handle_phrase_text`, `:171`), the internet tools, `build_tool_registry`'s
  module, `runtime.prefetch` and `time.sleep`. Its blind spot is `importlib` strings; our worker adds a run-time
  `sys.modules` check after a scripted run.
- **No env reads, no exception:** A4 waits for A1. Our workers also start in the empty agent home: defence in depth,
  not the guard.

## 4. Clock, randomness and duration: yours, with our conditions

- **The machinery clock and perceived-time port** are A3's (`ExperienceClockDriver`, `runtime/experience_time.py:36`;
  the ban extends M72), with the planted-render test split as A3 now has it. Our port carries coarse world time.
- **Keyed substreams (O40)** are `utils/seeding.py::make_agent_rng(base_seed, agent_id)` (`:79`), extended with a
  stream argument as a new release-gate item after the 1.4.0 cut (your owner, 2026-11-19); `1305.owned-rng`'s scope,
  tied to `seed_all`/`get_global_seed`, which the embedded path never calls, is unchanged. Until it exists,
  `agent_id` carries `"npc_key:stream"`. Two conditions: `agent_id` is the host's persisted NPC key, never an ordinal
  (streams survive saves and roster edits), and `base_seed` comes from the host's log root. We drop our
  `stable_hash_64_signed` formula.
- **Tool duration (OD-A4):** `execute_and_learn` measures `exec_elapsed` on the wall clock (`tool_dispatch.py:1419`),
  and `_observe_energy_cost` (`:695`) books a NEGATIVE NAc valence above 2.0 s. Embedded, the host supplies it in
  world time: the root fix, as you say.
- **Anchor similarity (OD-A20): declined, noted.** Your owner keeps event similarity on the host calendar, as #1361
  S3b has it; events and anchors age on the experience clock. Our v3 lean was wrong: SCN hour and day features reach
  the model through `temporal_patterns` and `[TEMPORAL]` (A3), so the read is on the perceived-time side. For us,
  credit through the anchor path (a receipt settled after its trace expires) depends on host time. A world paused 12 h inside the 300 s window gives a similarity of about 0.70 instead
  of about 1, and a crossed midnight steps the monthly phase by 1/31. We record that as a known divergence with a
  strict red gate, and will bring its evidence once real NPCs run.
- **τ_elig (OD-A21):** an argument against #1361's decided Q1. NAc's eligibility traces decay ×0.9 per pass
  (`decisions/nac.py::decay_eligibility`), τ_eff = −1/ln 0.9 = 9.49 passes: 0.32–0.95 s at 10–30 Hz today, against
  4.75 s after S3a, so 5–15× longer. The striatal window is about 0.3–2 s (Yagishita et al. 2014). This is not
  `experience_clock_decay.md` §Motivation's 50-pass τ (1.7–5 s), whose ratio happens to match. Reopening Q1 is your
  owner's, with its own experiment; **not** blocking for us.

## 5. The build, in your order

Your §Order governs: step 1, A3 A-pre, A5, #1684 and A2's existing parts, with `AgentHome` (A1) beside #984; step 2,
A3 A-post; step 3, the entry point, sealed roster (OD-A10, OD-A11) and leak closure (A4), whose closure owns the
background-worker thread, through `build_memory_hub(start_background_workers=False)` (`runtime/bio_stack.py:489`,
the start at `:654`); step 4, dispatch/settle (B2, #1150, with A6), carrying provenance by source actor, D53
`outcome_valence`, OD-A16's keys and `environment.step`; step 5, the stepped `think` (B1, B3) after the cut. A2's
per-agent key is a new gate item after the cut. Our condition (OD-I3), not your order: no home reachable from saves
before #1685. §6's red gates come first.

**Before 1.4.0 (your M89 reading):** steps 1–4 may land before the cut, provided the A4 entry point exposes no
`think`, `Pending` or continuation before it, and §2's basis and staleness stay out of B2.

**Timing, as you gave it:** 1.4.0 planned March to May 2027; B1 follows with no range, so our first real NPC is after
mid-2027. Meanwhile one unreplayed bridge NPC measures latency, cost and feel, claiming nothing.

**What our first NPC needs (O29):** #1361 S3a, S3b and S4; OD-A2 to OD-A11; OD-A12's host-driven thread; OD-A14 to
OD-A18; #1684 and #1685. OD-A20 would be needed, but is declined, so our replay exit carries a known divergence. Not
blocking: #1361 S5 and S6, OD-A21, and OD-A12's store routing.

## 6. Exit tests

Where you have the test, ours is a configuration of it.

| # | Passes when | Yours |
|---|---|---|
| OD-EA1 | a planted `BashTool` in the roster makes construction refuse, naming it | A4 |
| OD-EA2 | two embedded agents in one process never open the same file | A1's filesystem trace |
| OD-EA4 | no store changes until `settle`; then exactly the returned writes, through the agent bus; a memory write planted in the parallel dispatch path is refused | B2/A6 |
| OD-EA5 | the state digest is identical whether each reply returns instantly or after a seeded random delay | B1's gate |
| OD-EA6 | agent A's digest is identical alone, beside B, reversed and concurrent (proven by a planted global `random`) | A2 (partly) |
| OD-EA7 | the thread count is unchanged by building and stepping | `1263.thread-guard`, configured |
| OD-EA8 | `cancelled(prefix)` records the host-delivered prefix as said and the thought as cancelled; no reply, cancelled or unparseable, reaches the parse-failure template | A4/B1 |
| OD-EA9 | stubs that request a follow-up on every reply, ask for 3 PFC cycles forever, or return 100,000 tokens all stop at the host's budget | none found |
| OD-EA10 | §3's closure tests pass, and a planted read in a lazy path fails the static ban | A4 |
| OD-EA11 | a sentinel in the **machinery** clock never appears in a prompt in raw, clock or date form; an origin offset changes no prompt end to end; offset and scale change no render on a frozen store | A3's planted-render test, split |
| OD-EA12 | several traces credited by one receipt share it identically between agents stepped every tick and every *n*th tick | G2b's fixture widened, a #1361 slice decision (Q2) |
| OD-EA13 | a stub that calls a model outside `think` fails closed, naming the call | none found |
| OD-EA14 | B1 robot parity: the robot path through the thin driver gives today's state digest, bit for bit, on recorded replies (Exp 49, Exp 60) | B1's gate |
| OD-EA15 | B2 robot parity: the robot path settles immediately after dispatch, with today's digest | B2's guard |

OD-EA3 (no pickle) is #1685.

## 7. Questions left

Your review answered v3's ten; §1–§5 fold them.

1. **B1's tracked rights, embedded:** which world events count as tracked rights for a host-driven agent? We propose
   §A.1b.5's default, danger tracks only, delivered through `step`.
2. **OD-EA12:** will #1361 widen G2b's fixture to several traces sharing one receipt? If not, OD-EA12 is ours, in
   Phase 3, against S3b.
3. **A2's stream argument:** will the gate item derive from `f"{base_seed}:{agent_id}:{stream}"`, so streams made
   with `agent_id = "npc_key:stream"` survive the change?
4. **`consolidate`:** is its budget in world time, and which stages does a bounded call run?

Searched, nothing found: the model calls outside `think` in active plans; OD-EA9; a `DECISIONS.md` entry for the
host-driven mode (ours is proposed in `docs/maxim_upstream/decisions_entry_DRAFT.md`).

## 8. What it argues against

Mode-based containment (`allowed_dirs`) as the security model when the prompt carries strangers' words, and the
process-wide data home. Both are right for one robot and its operator.
