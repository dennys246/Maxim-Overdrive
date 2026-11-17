# DRAFT for Maxim: an embeddable agent, which a host drives (v2)

**Status:** a proposal drafted in Maxim Overdrive, for Maxim's process as a **plan** (a three-lens plan review and a
three-lens code review per PR). v2 (2026-11-17) is re-based on Maxim's design session's answers
(`docs/design/reviews/maxim_response_1/response.md` and `response_2.md` in Overdrive) and Overdrive's four-lens
review of them. Everything here is `[engineering]`; it claims no behaviour. Citations are to `origin/main` 7084f561;
Maxim's ranked candidates doc, when written, re-checks them on a fresh tree and supersedes this draft's ordering.

- **Overdrive ids:** OD-A10 to OD-A12, OD-A14, OD-A15, OD-A17, OD-A18 (tier A), and the issue OD-I3 (pickle).
- **Depends on:** the world clock plans (OD-A2 to OD-A8: the machinery clock, the perceived-time port, keyed
  substreams, ids); the propose/settle amendment (OD-A16), which joins the dispatch/settle split (OD-A18).

## 1. What v1 got wrong about Maxim

- **There is no inner tool loop.** One planning call returns one JSON action, plus optional `parallel_actions` and a
  `next_actions` chain; the result comes back as `ctrl.pending_action_followup` on the next tick
  (`runtime/agent_loop.py:2172`, `:2264`; `agents/llm_worker.py:1355`). A tool call is an intent the host validates,
  not a request `think` waits on. v1's "tool calls inside `think`" and its tool-loop budget don't exist.
- **But one thought can be several model calls.** PFC deliberation runs up to 3 sequential calls in one tick, feeding
  the model's reasoning back through bio-enrichment between them (`agent_loop.py:521`, `:3086-3125`).
- **The gateway is not an `LLMBackend`.** v1's PR 4 (token-stream and cancel capabilities on the backend) would have
  re-imported the blocking worker and the router's per-router `_inference_lock` (`models/language/router.py:185`,
  `:1080`). Withdrawn.
- **The home parameter exists:** `AgentFactory` already scopes the core stores under `base_data_dir/<agent_id>`
  (`runtime/agent_factory.py:1168-1172`). The gap is about nine families of still-global stores.
- **The advisor is not the base.** It is a quarantine for an untrusted observer (one hard-coded tool, no injected
  backend, a process-wide offline latch). Its *patterns* are what to reuse: the sealed registry, the `Effect` ceiling,
  the `ToolPolicy` pin, typed refusals, budgets in the grammar (`maxItems`), and its three closure tests.

## 2. The contract

Construction goes through `AgentFactory` (the single construction point); deliberation is its own module.

| Call | Does | Returns |
|---|---|---|
| `step(agent, world_dt_us, frame)` | advances drives, the experience clock and the substrate; reads percepts | a `StepOutput` value: intents, memory writes, thought requests |
| `think(agent, continuation, reply \| None)` | runs deliberation up to its next model call | `(continuation', Pending(request) \| ThoughtOutput)` |
| `apply(agent, writes)` / `settle(agent, receipts)` | the only paths by which writes and credit reach the stores | nothing |
| `save()` / `load(home)` | persist and restore under the home only, pickle-free | nothing |

- **The continuation is a frozen, versioned value, not the whole agent.** It carries the thought id and kind, the PFC
  cycle index and `max_cycles`, the partial proposal between cycles, the outstanding canonical request, a `basis`
  (step sequence and frame id at request time, §A.1b.5's `basis_seq`) and the triggering-input id, budget counters,
  cancel status with the delivered prefix, and the loop locals that aren't values yet (the same-tool counter,
  `rejection_followups`). The agent is read-only on the think path; every write leaves through `apply`/`settle`. A
  census of today's think-path writes is the plan's first step.
- **The request** is a value: rendered system and user text, sampling parameters, a model **role** (speech or plan,
  which the host binds to its model profile; never Maxim's provider choice), priority class and deadline fields, the
  template version, and an assertion that `tools is None`.
- **The reply** is a value: `complete(text)`, with reserved `cancelled(prefix)` and `truncated(prefix, reason)`
  variants, which bypass the parse-failure template (`llm_worker.py:1322-1338`). Speech is a top-level field emitted
  first, so the host can stream it before the JSON closes. A token iterator can come later.
- **Cancel** is resuming with a `cancelled(prefix)` reply. No contextvar, no cancel token on a backend.
- **Internal cognition tools** (memory recall, narrative lookup) resolve inside `think` against the agent's own
  stores; only effectful world tools leave as intents. Proposed; Maxim's answer didn't cover the split.
- **The robot path drives the same `think`** through a thin worker driver, so there is one deliberation path and the
  parity check compares one function under two drivers.
- **Budgets per triggering input** across its follow-up chain: PFC cycles per thought, `parallel_actions` per reply
  (a grammar `maxItems`), `next_actions` chain length, tokens per call, memory writes and bytes.

## 3. The embedded-path leak closure (one tier-A item, OD-A17)

Close structurally, don't enumerate. The embedded entry point never calls `build_tool_registry`, `data_home()` or
`config_loader`, and never reads the environment. Named because some sit on the core path:
- prefetch off (`runtime/agent_loop.py:1571`, `runtime/prefetch.py`), and the working directory set to the empty
  agent home, since the offline latch stops prefetch's `find` but not its file reads;
- the short-question shortcut bypassed (`agents/prompt_builder.py:1102-1137`, `agents/llm_fallback.py:290-330`: it
  fires on any triggering input);
- no `force=True` root-logger takeover (`api.py:113`);
- every path under the agent home, never the working directory (`cloud_audit.py:49`, `response_config.py:65`);
- the parallel and agent-fallback side doors folded into dispatch (`runtime/tool_dispatch.py:1290-1291`);
- the parser bypass for cancelled replies.

Proven by the advisor's three tests (import closure, env-read set, `test_no_effect` at
`tests/integration/test_advisor_gate.py:1261`) plus a static import ban, because dynamic tests miss lazy paths they
never run (the cloud fallback at `lane_backends.py:1246`).

## 4. The build, in order (proposed; Maxim's candidates doc decides)

| PR | What | When |
|---|---|---|
| 0 | Red gates for §5, against a stub embedded host | own clock |
| 1 | The embedded roster: sealed, `Effect`-ceilinged, refused at construction | own clock (engineering; robot defaults stay experiment-gated) |
| 2 | `AgentHome`: the remaining global stores routed through one per-agent object; the ConceptExtractor thread made host-driven (`runtime/bio_stack.py:654`) | own clock |
| 3 | The leak closure (§3) and its four tests | own clock |
| 4 | Dispatch/settle split of `execute_and_learn`, with generate-vs-apply, D53 `outcome_valence` and OD-A16's keys; robots settle right after dispatch | after the clock seam (OD-A2), behind a bit-identical state-digest parity guard |
| 5 | The stepped `think` and the continuation, on §A.1b's seam | after the 1.4.0 cut, with the agent-loop decomposition slices |
| 6 | Flip §5's gates; docs | last |

The pickle-free load is the issue OD-I3, filed now; it must land before PR 2 makes homes reachable from shared saves.

## 5. Exit tests

| # | Passes when |
|---|---|
| OD-EA1 | a planted `BashTool` in the roster makes construction refuse, naming it |
| OD-EA2 | two embedded agents in one process never open the same file |
| OD-EA4 | no store changes until `apply`/`settle`; then exactly the returned writes |
| OD-EA5 | the state digest is identical whether each reply returns instantly or after a seeded random delay |
| OD-EA6 | agent A's digest is identical alone, beside B, reversed and concurrent (proven by a planted global `random`) |
| OD-EA7 | the thread count is unchanged by building and stepping |
| OD-EA8 | a `cancelled(prefix)` reply records the prefix as said and the thought as cancelled, and never reaches the parse-failure template |
| OD-EA9 | a stub whose every reply requests a follow-up, one that asks for 3 PFC cycles forever, and one that returns 100,000 tokens all stop at the host's budget |
| OD-EA10 | the four closure tests of §3 pass, and a planted read in a lazy path fails the static ban |
| OD-EA11 | a planted perceived-time sentinel never appears in a rendered prompt (with the world clock plans) |

OD-EA3 (no pickle) moves to the issue OD-I3.

## 6. What it argues against

Mode-based containment (`allowed_dirs`) as the security model when the prompt carries strangers' words, and the
process-wide data home. Both are right for one robot and its operator.
