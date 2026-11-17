# DRAFT for Maxim: an embeddable agent, which a host drives (v2)

**Status:** a proposal drafted in Maxim Overdrive, for Maxim's process as a **plan** (a three-lens plan review and a
three-lens code review per PR). v2 (2026-11-17) is re-based on Maxim's design session's answers
(`docs/design/reviews/maxim_response_1/response.md` and `response_2.md` in Overdrive) and Overdrive's four-lens
review of them; v2.1 folds Overdrive's five-lens review of its own design (`docs/design/reviews/npcs_v3/`) and a
correction we owe Maxim (`correction_1.md`: NAc's traces decay per loop tick). Everything here is `[engineering]`; it claims no behaviour. Citations are to `origin/main` 7084f561;
Maxim's ranked candidates doc, when written, re-checks them on a fresh tree and supersedes this draft's ordering.

- **Overdrive ids:** OD-A10 to OD-A12, OD-A14, OD-A15, OD-A17 to OD-A19 (tier A), and the issue OD-I3 (pickle).
- **Depends on:** the world clock plans (OD-A2 to OD-A8: the machinery clock, the perceived-time port, keyed
  substreams, ids); the propose/settle amendment (OD-A16), which joins the dispatch/settle split (OD-A18).

## 1. What v1 got wrong about Maxim

- **There is no inner tool loop.** One planning call returns one JSON action, plus optional `parallel_actions` and a
  `next_actions` chain; the result comes back as `ctrl.pending_action_followup` on the next tick
  (`runtime/agent_loop.py:2172`, `:2264`; `agents/llm_worker.py:1355`). A tool call is an intent the host validates,
  not a request `think` waits on. v1's "tool calls inside `think`" and its tool-loop budget don't exist.
- **But one thought can be several model calls.** PFC deliberation runs up to 3 sequential calls by default
  (`llm.deliberation_max_cycles` overrides it, `runtime/config_loader.py:139`, `:551`) in one tick, feeding
  the model's reasoning back through bio-enrichment between them (`agent_loop.py:521`, `:3086-3125`).
- **The gateway is not an `LLMBackend`.** v1's PR 4 (token-stream and cancel capabilities on the backend) would have
  re-imported the blocking worker and the router's per-router `_inference_lock` (`models/language/router.py:185`,
  `:1080`). Withdrawn.
- **The home parameter exists:** `AgentFactory` already scopes the core stores under `base_data_dir/<agent_id>`
  (`agents/agent_factory.py:1168-1172`). The gap is ten families of still-global stores.
- **The advisor is not the base.** It is a quarantine for an untrusted observer (one hard-coded tool, no injected
  backend, a process-wide offline latch). Its *patterns* are what to reuse: the sealed registry, the `Effect` ceiling,
  the `ToolPolicy` pin, typed refusals, budgets in the grammar (`maxItems`), and its three closure tests.

## 2. The contract

Construction goes through `AgentFactory` (the single construction point); deliberation is its own module.

| Call | Does | Returns |
|---|---|---|
| `step(agent, world_dt_us, frame)` (the host's port is in ticks; the adapter converts) | advances drives, the experience clock and the substrate; reads percepts | a `StepOutput` value: intents, memory writes, thought requests |
| `think(agent, handle, reply \| None)` | runs deliberation up to its next model call; may read, never write | `Pending(request) \| ThoughtOutput`, with any writes (including retrieval strengthening) as values |
| `apply(agent, writes)` / `settle(agent, receipts)` | the only paths by which writes and credit reach the stores, both called by the host after its own gate | nothing |
| `save()` / `load(home)` | persist and restore under the home only, pickle-free | nothing |

- **The continuation is split by owner, and is not the whole agent.** The **host** keeps a header: thought id and
  kind, the triggering-input id, budget counters, the PFC cycle index and `max_cycles`, the `basis` (step sequence and
  frame id, §A.1b.5's `basis_seq`), each segment's landing time, cancel status and the delivered prefix. The **agent**
  keeps a body: the partial proposal between cycles, the transcript, enrichment results, and the loop locals that
  aren't values yet (the same-tool counter, `rejection_followups`), saved in its home and opaque to the host. Budgets
  live in the host's header, so the agent can't reset them. The agent writes nothing on the think path: recalls that
  strengthen a trace (the testing effect) return a `retrieval` write, applied by `apply`. A census of today's
  think-path writes is the plan's first step.
- **Staleness has one vocabulary,** `fresh`, `stale`, `superseded`: on a stale basis `think` returns a new request (a
  re-plan) or `ThoughtOutput(abandoned)`.
- **The request** is a value: rendered system and user text, sampling parameters, a model **role** (speech or plan,
  which the host binds to its model profile; never Maxim's provider choice), the template version, and an assertion
  that `tools is None`. Priority and deadline are the host's, stamped from the thought's kind.
- **The reply** is a value: `complete(text)`, with reserved `cancelled(prefix)` and `truncated(prefix, reason)`
  variants. The prefix is the speech the host has already delivered, validated, not whatever tokens streamed. **No
  reply ever reaches the parse-failure template** on the embedded path: a complete reply that doesn't parse ends the
  thought as a failure (`thought_failed(reason=parse)`), because the template echoes the triggering input
  (`agents/llm_worker.py:1322-1338`, `agents/llm_fallback.py` near `:395-400`). Speech is a top-level field emitted
  first, so the host can stream it before the JSON closes. A token iterator can come later.
- **Cancel** is resuming with a `cancelled(prefix)` reply. No contextvar, no cancel token on a backend.
- **Cognition tools inside `think` are not proposed now.** Resolving memory recall inside `think` would be an inner
  tool loop, your C10 question; until an experiment decides it, cognition tools go through follow-ups like world
  tools.
- **The robot path drives the same `think`** through a thin worker driver, so there is one deliberation path and the
  parity check compares one function under two drivers.
- **Budgets per triggering input and per agent per world minute** across follow-up chains (so thoughts with no
  speech trigger are budgeted too): PFC cycles per thought, `parallel_actions` per reply
  (a grammar `maxItems`), `next_actions` chain length, tokens per call, memory writes and bytes.

## 3. The embedded-path leak closure (one tier-A item, OD-A17)

Close structurally, don't enumerate. The embedded entry point never calls `build_tool_registry`, `data_home()` or
`config_loader`, and never reads the environment. Named because some sit on the core path:
- prefetch off (`runtime/agent_loop.py:1571`, `runtime/prefetch.py`), and the working directory set to the empty
  agent home, since the offline latch stops prefetch's `find` but not its file reads;
- the short-question shortcut bypassed (`agents/prompt_builder.py:1102-1137`, `agents/llm_fallback.py:290-330`: it
  fires on any triggering input);
- no `force=True` root-logger takeover (`api.py:113`);
- every path under the agent home, never the working directory (`utils/cloud_audit.py:49`, `utils/response_config.py:65`);
- the parallel and agent-fallback side doors folded into dispatch (`runtime/tool_dispatch.py:1290-1291`);
- no reply reaches the parse-failure template (above);
- **no model backend in the embedded agent at all,** so model calls outside `think` fail closed: `AdaptivePlanner(llm=...)`
  (`runtime/bootstrap.py:623`, `adaptive_planner.py:487`), the `ToolPainBridge` reflection on the settle path
  (`tool_pain_bridge.py:806`, its error swallowed) and `FearAgent(fear_llm)`; each becomes a request through the cut
  or is off on the embedded path.

Proven by the advisor's three tests (import closure, env-read set, `test_no_effect` at
`tests/integration/test_advisor_gate.py:1261`) plus a static import ban, because dynamic tests miss lazy paths they
never run (the cloud fallback at `runtime/lane_backends.py:1246`). The ban names at least `maxim.embodied_runtime` (the
phrase commands, `input_handlers.py:202`, `:274-312`), the internet tools, `build_tool_registry`'s module and
`runtime.prefetch`. Until `AgentHome` lands, the env-read test expects exactly one read, `MAXIM_DATA_HOME`.

## 4. The build, in order (proposed; Maxim's candidates doc decides)

| PR | What | When |
|---|---|---|
| 0 | Red gates for §5, against a stub embedded host | own clock |
| 1 | The embedded roster: sealed, `Effect`-ceilinged, refused at construction | own clock (engineering; robot defaults stay experiment-gated) |
| 2 | `AgentHome`: the remaining global stores routed through one per-agent object; the ConceptExtractor thread made host-driven (`runtime/bio_stack.py:654`) | own clock |
| 3 | The leak closure (§3) and its four tests | own clock |
| 4a | Step-size-invariant decay (OD-A19): NAc's eligibility traces and their five siblings in `_loop_bio_tick_maintenance` decay as `exp(−Δt/τ)` on the machinery clock, not ×0.9 per loop tick | after the clock seam (OD-A2) |
| 4 | Dispatch/settle split of `execute_and_learn`, with generate-vs-apply (with provenance by source actor), D53 `outcome_valence` and OD-A16's keys; robots settle right after dispatch | after PR 4a, behind a bit-identical state-digest parity guard |
| 5 | The stepped `think`, the continuation and the reply variants, on §A.1b's seam: one design for the submit path, so OD-H6's submit clock, the request/reply cut (OD-A14) and the cancelled-reply parser bypass land as parts of it, not before | after the 1.4.0 cut, with the agent-loop decomposition slices |
| 6 | Flip §5's gates; docs | last |

The pickle-free load is the issue OD-I3, filed now; it must land before PR 2 makes homes reachable from shared saves.

## 5. Exit tests

| # | Passes when |
|---|---|
| OD-EA1 | a planted `BashTool` in the roster makes construction refuse, naming it |
| OD-EA2 | two embedded agents in one process never open the same file |
| OD-EA4 | no store changes until `apply`/`settle`; then exactly the returned writes; a memory write planted in the parallel dispatch path is refused (TBR-6) |
| OD-EA5 | the state digest is identical whether each reply returns instantly or after a seeded random delay |
| OD-EA6 | agent A's digest is identical alone, beside B, reversed and concurrent (proven by a planted global `random`) |
| OD-EA7 | the thread count is unchanged by building and stepping |
| OD-EA8 | a `cancelled(prefix)` reply records the host-delivered prefix as said and the thought as cancelled; no reply, cancelled or unparseable, reaches the parse-failure template |
| OD-EA9 | a stub whose every reply requests a follow-up, one that asks for 3 PFC cycles forever, and one that returns 100,000 tokens all stop at the host's budget |
| OD-EA10 | the four closure tests of §3 pass, and a planted read in a lazy path fails the static ban |
| OD-EA11 | a sentinel planted in the **machinery** clock never appears in a rendered prompt in raw, clock, date or duration form, and two runs whose machinery clocks differ by an offset and a scale, with equal perceived-time bins, render byte-identical prompts (with the world clock plans) |
| OD-EA12 | one receipt delayed by the same world time is credited equally by agents stepping at two rate divisors (OD-A19) |
| OD-EA13 | a stub that calls a model outside `think` fails closed, naming the call |

OD-EA3 (no pickle) moves to the issue OD-I3.

## 6. What it argues against

Mode-based containment (`allowed_dirs`) as the security model when the prompt carries strangers' words, and the
process-wide data home. Both are right for one robot and its operator.
