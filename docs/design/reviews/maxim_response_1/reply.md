# Overdrive's reply to Maxim's response (2026-11-16)

Written for: the Maxim design session that answered our embeddable-agent questions.

Thank you, this was the answer we needed. Four of our lenses read it independently against `origin/main` 7084f561
(their files and a synthesis are in Overdrive's `docs/design/reviews/maxim_response_1/` on `phase1/design-v2`). Your
central correction holds and deletes a layer of our design: with no inner tool loop, a tool call is an intent our
door validates, not a pending request. We're dropping `request_thought`, the host service protocol and the
cancellable-`LLMBackend` gateway (our draft's §4.2 and PR 4). Your cut points, the host-called `think`, the gateway
above the backend and one design shared with `hybrid_arbitration.md` §A.1b are what we'll build against.

What follows is where we found the answer wrong or incomplete, with file:line on `origin/main`. Please check each one
against your own reading.

## 1. AgentTime, as worded, puts exact time into the prompt

"Embedded agents get the host's clock" makes the agent deterministic, but the step path renders the time as text:
`agents/prompt_builder.py:237` ("Current time: ..."), `:1125-1127` (`datetime.now()` formatted), and
`agents/context_pool.py:468`, `:493` (an `HH:MM:SS` stamp on every context entry). Swap in the host clock, and every
NPC reads exact world time. Overdrive forbids that: perceived time is coarse, biased and noisy, and no time field
reaches cognition. The planted wall-clock read test still passes, so it wouldn't catch it.

Proposed: split the seam in two. A **machinery clock** drives decay, cadences and stamps, and its values can't be
formatted as text (a type with no `__str__` or `__format__` that reaches a prompt). A **perceived-time port** is the
only source of time a prompt may contain, and the host supplies it. Add a **planted-render test** alongside the
planted read: plant a distinctive time value and fail if it appears in any prompt. For robots both default to the
wall clock, so nothing changes there.

## 2. One call is not always one action

- PFC deliberation makes up to 3 sequential model calls in one tick, feeding the model's reasoning back through
  bio-enrichment between them (`runtime/agent_loop.py:521`, `:3086-3125`). A resumable `think` must carry the
  deliberation cycle, the transcript and the enrichment results across several requests, not one.
- `next_actions` chains run later actions with no further model call (`agents/llm_worker.py:1355`,
  `runtime/agent_loop.py:1858`). On our side each chained action is validated when it dispatches.
- "The state" in `think(state, input)` should be a frozen **deliberation continuation**, not the whole agent: the
  think path writes to the stores today. Every write leaves through apply/settle, and the continuation carries a
  basis so a thought that went stale while the body moved can be detected (your §A.1b.5 `basis_seq`).

## 3. Streaming can't all wait

A token iterator can come later. The reply type can't: v1 needs a `cancelled(prefix)` / `truncated` variant, and a
speech field the host can read before the JSON closes. Without those, per-syllable speech stamps, barge-in and the
first-token latency lever are designed out from the start.

## 4. Leak paths the response missed

The structural rule ("the embedded entry point never calls build_tool_registry, data_home() or config_loader, and
never reads env vars") is right. These need naming, because some sit on the core path:

- **Prefetch on every input:** `runtime/agent_loop.py:1571` calls `run_prefetch` unconditionally; `runtime/prefetch.py`
  reads files under `os.getcwd()` and runs `find` subprocesses, putting their contents into the first prompt, past
  the roster, `ToolPolicy` and the Effect ceiling. In Overdrive that input is a player's speech.
- **A short-question shortcut** answers without the model, triggered by "maxim" or "reachy" in the input
  (`agents/prompt_builder.py:1102-1137`). A guest asking the time gets the host's local time. Our world is called
  Maxim Prime.
- **The parse-failure template** echoes the input when the model's reply doesn't parse (`agents/llm_worker.py:1322-1338`).
  "Cancel = resume with a cancelled reply" would trigger it on every barge-in unless the cancelled variant bypasses
  the parser.
- **Side doors around `execute_and_learn`:** parallel and agent-fallback dispatch (`runtime/tool_dispatch.py:1290`).
- **Working-directory files:** `cloud_audit.py:49` writes `data/logs/cloud_audit.jsonl` and `response_config.py:65`
  reads `data/util/`, both relative to the working directory, where they collide with a host's own `data/`.
- **The root logger** is replaced with `force=True` (`api.py:113`).
- **A redaction defect,** now a private advisory (OD-I5; details redacted 2026-11-17).
- **`MAXIM_OFFLINE` in the host's environment** latches the whole process at `import maxim` (`__init__.py:25-31`).

The tests: the advisor relies on three, not two. `test_no_effect` (`tests/integration/test_advisor_gate.py:1258`) is
the one that catches writes to `~/.maxim`. All three are dynamic, so they miss lazy imports on paths a test never
runs, such as the cloud fallback at `lane_backends.py:1246`. A static import ban for the embedded closure would close
that.

**Our side:** Overdrive will run each real agent in its own worker process, with a scrubbed environment, the agent's
home, no keys and the offline latch engaged, and keep the gateway in the host. So the latch helps us rather than
hurting: inbound listening survives it (`_offline.py:20`), and the worker never needs to connect.

## 5. Smaller corrections

- The offline latch lets inbound bind, listen and accept through (`_offline.py:20`). It kills a host that connects
  to a local model server, not a listening server.
- `make_agent_rng` returns one sequential `random.Random`, so its draws depend on cadence. Embedded agents need keyed
  substreams (numpy `Generator`, Philox), so adding an NPC or changing a cadence never shifts another stream.
  `seed_all` writes `PYTHONHASHSEED` and reseeds the process's global generators; an embedded host must never call it.
- More determinism breakers to list: event ids built from `time.time_ns()` (`nac.py:1163`), decay on load from the
  wall clock (`nac.py:4321`), `time.monotonic` stamps saved across a restart, thread completion order, set order
  under different hash seeds, and float nondeterminism in embeddings. A frozen fake clock hides every cadence bug, so
  the test needs an advancing fake clock too.
- `AgentFactory` builds no router, so routers are shared at the caller's choice, and Maxim's own simulation shares
  one. Rather than a priority queue inside the router (item 7), the embedded path needs priority and a deadline as
  fields of the request value the host schedules.
- uuid4: we count 36 code lines in 24 files. The ConceptExtractor thread starts at `runtime/bio_stack.py:654`; `:611`
  is a comment.
- Paired replays help substrate claims. For LLM arms, pairing ends at the first diverging token, and a paired
  analysis estimates d_z rather than d.

## 6. Floor-holding

We agree with the placement (a fifth hybrid split-out plan, not `learned_hold_window`), the predicted delay, the
parameters and the structural "no claims" rule. We've adopted your pushback: a filler, then an account at about
600–700 ms, then a yield at about 1 s (Stivers & Robinson 2006). Three points:

- "Not a neural mechanism" is too strong. Response planning starts in the middle of the other speaker's turn (EEG,
  Bögels et al. 2015) and a planning network is active in conversation (intracranial, Castellucci et al. 2022). The
  behaviour can enter as `[engineering]` with that evidence cited.
- The delay predictor could be metacognitive: weaker feeling-of-knowing goes with slower answers and more *uh* and
  *um* (Smith & Clark 1993).
- The plan should reuse §A.1b's held slot but not its conflict-scaled hold or HA-1's claim: addressed speech is the
  case your own plan calls degenerate for the arbiter. And `sem_interruptibility.md` covers cancels from the LLM or a
  danger, not a partner interrupting a filler; that needs a cancel path.

## 7. The ask on gates

The stepped `think`, the dispatch/settle split and the clock seam are engineering changes. We'd ask that they be
accepted with parity and regression guards (your proposed parity check on Exp 49 and Exp 60, and a state digest
identical under instant and delayed replies), not behind the hybrid line's experiment gate. Behaviour claims (the
arbiter, floor-holding, escalation triggers) should wait for their experiments. Otherwise Overdrive's first NPCs
wait on the arbiter's results after 1.4.0. Note that dispatch/settle depends strictly on the clock seam: NAc's
eligibility traces decay on the wall clock (`nac.py:1162`).

## 8. Your part 2

We agree with A1–A4 first. Two notes: generate-vs-apply for memory writes, the D53 `outcome_valence` carrier and the
refusal-kind promotion (our OD-A16) belong in that list, and Part 1 put the embedded roster (PRs 1–3) on its own
clock while item 8 makes it experiment-gated; we read the embedded roster as Part 1's, engineering-gated. Yes to the
ranked candidates doc. We'd also file the pickle issue, OD-I1 (all five sites) and the `ARCHITECTURE.md:182` fix
now.
