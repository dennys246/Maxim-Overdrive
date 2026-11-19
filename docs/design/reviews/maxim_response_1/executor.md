# Executor lens (fact-check): Maxim's response 1

Read only Maxim `origin/main` 7084f561 (`git show` / `git grep`). Paths are under `src/maxim/` unless shown
otherwise. Nothing in the Maxim repo was checked out, fetched or written.

## Claims

| # | Claim | Verdict | Evidence (origin/main) |
|---|---|---|---|
| 1a | One model call returns one JSON action plus `parallel_actions` | PARTLY | `agents/llm_worker.py:1355-1365` also parses `next_actions`, a sequential chain the loop runs one per tick with no model call between them (`runtime/agent_loop.py:1794-1796`, `:1858-1860`; `runtime/loop_controller.py:145`). The response leaves out `next_actions`. |
| 1b | A tool result becomes `ctrl.pending_action_followup` and the next tick submits it | CONFIRMED | `runtime/agent_loop.py:2172` (batched exploration), `:2264` (`_execute_and_learn` outcome), consumed at `:2700-2733` |
| 1c | The model never sees a tool result within one call; there is no inner tool loop | CONFIRMED, with two caveats | No ReAct-style loop exists. The planning call passes no `tools=` (`agents/llm_worker.py:1236-1252`). The only `tools=` caller is `agents/exec_agent.py:1520/1529`, which is documented dormant (`exec_agent.py:1486-1494`). Caveat (i): PFC deliberation makes up to 3 sequential, blocking model calls in one tick (`runtime/agent_loop.py:3086-3125`, `_run_deliberation_cycles` at `:521`, `max_cycles` 2 or 3 at `:3090-3094`). Between calls it feeds the model's own reasoning back through bio-enrichment (memories, predictions, concepts). That is not a tool result, but one "think" can mean several model calls with state carried between them. Caveat (ii): the prefetcher reads files and runs `find` before the first call (see Notes). |
| 1d | `LLMResponse.tool_calls` has no reader outside the backends | CONFIRMED | The only hits for `.tool_calls`/`tool_calls=` are `models/language/anthropic_backend.py:468`, `:569` (writers) |
| 2a | `_inference_lock` (router.py:1080) serializes every inference per router | CONFIRMED | Lock created at `models/language/router.py:185`, "Serializes inference calls (llama-cpp not thread-safe)". `_complete_text` (`:944`) holds it for the whole dispatch, cloud calls included (`:1080-1100`). When the acquire times out (600 s default, `MAXIM_INFERENCE_LOCK_TIMEOUT_S`) the call returns `("", None)` |
| 2b | Agents share a router by default | PARTLY (the response doesn't state this) | `AgentFactory` builds no router; the caller supplies one. The simulation builds one shared router for the narrator, the AUT and the fear gate (`simulation/orchestrator.py:1012-1014`, "single model, alternating inference"; `_build_aut_router` defaults to it at `:643`). Each `LLMWorker` also has a single-worker pool (`agents/llm_worker.py:657`). So "ten NPCs on one router think one at a time" is accurate whenever a host shares the router, which is Maxim's own pattern. |
| 3a | Advisor: one hard-coded `ProposeActionTool` | CONFIRMED | `advisor/_session.py:88-122`; pinned policy at `:240-242` |
| 3b | Advisor refuses injected backends; the only seam is a private test hook | CONFIRMED | `advisor/_session.py:247-251` (`_backend_factory`, "tests replace this name; no env var selects it") |
| 3c | `maxItems: max_calls` sits in the grammar | CONFIRMED | `advisor/_session.py:288` area (`completion_schema`) |
| 3d | Offline latch is one-way and process-wide, refusing connect, DNS, spawn and fork, so it "would kill a co-op server's own networking" | PARTLY | One-way and process-wide: CONFIRMED (`_offline.py:3`; `engage` at `advisor/_session.py:784`). It refuses every `connect`/`connect_ex` including loopback, all name lookups, every spawn and every fork (`_offline.py:6-18`, `:62-65`). But inbound `bind`/`listen`/`accept` pass (`_offline.py:20`), so a server that only accepts loopback connections still works. What dies: every outbound connection, including a local model server over HTTP and any peer or relay connection; launching the Godot client or any subprocess; and multiprocessing with fork or forkserver. It also writes five env vars, `HF_HUB_OFFLINE` among them, for the whole process (`_offline.py:53-59`). |
| 4a | Per-agent stores live under `base_data_dir/<agent_id>` | CONFIRMED | `runtime/agent_factory.py:1168-1172` (the response cites it without the `runtime/` directory); default base is `data_home()/...` (`:737`) |
| 4b | Global stores remain | CONFIRMED (spot-checked) | Each of these calls `resolve_user_state` (meaning `~/.maxim/`, `utils/paths.py:347-360`): energy (`agents/llm_context.py:25`), escalation (`bridges/escalation_bridge.py:129`), fear (`bridges/fear_bridge.py:144`), DN thresholds (`default_network/gate.py:77`), cost (`models/language/cost_tracker.py:108`), focus (`proprioception/focus_learner.py:86`), bounds (`spatial/bounds_learner.py:103`), embeddings (`integration/memory_hub.py:246`) |
| 4c | ConceptExtractor thread starts at construction (agent_factory.py:611) | CONFIRMED; the citation is weak | `agent_factory.py:611` is only a comment on shutdown. The actual start is `runtime/bio_stack.py:654` (`memory_hub.start_background_workers()` at the end of `build_bio_stack`); the hub is built with it deferred (`bio_stack.py:489`) |
| 4d | `make_agent_rng` has no caller | CONFIRMED | Defined at `utils/seeding.py:79`; it is referenced only in its own docstring and in `tests/unit/test_seeding.py`. Note: it returns `random.Random`, not a numpy `Generator` |
| 5a | uuid4: 35 calls in 24 files | PARTLY | I count 36 code lines in 24 files (38 hits, less a comment at `hivemind/cli.py:655` and a docstring at `time/temporal_event.py:28`). The draft's 36 looks right, and Maxim's "your extra one is a comment" is unsupported. |
| 5b | Global random: 27 (26 draws in 9 files plus `random.seed`) | CONFIRMED | 9 files; `decisions/significance.py:190`; Anthropic jitter at `models/language/anthropic_backend.py:198`; `utils/seeding.py:51` |
| 5c | Legacy `np.random`: 3 calls, one at `salience_map.py:437` | CONFIRMED | Plus `hardware/simulation/streams.py:87`, `:158` (`np.random.seed` at `seeding.py:57` aside) |
| 5d | `default_factory=time.time`: 36 in 19 files, plus 1 monotonic at `tools/registry.py:146` | CONFIRMED | |
| 5e | 608 `time.time()` in 178 files; 145 monotonic; 20 `datetime.now` | CONFIRMED | 608 lines in 178 files; 145; 20 counting `now`/`utcnow`/`today` (15 for `datetime.now(` alone) |
| 5f | 128 distinct `MAXIM_*` names are read | PARTLY, unverifiable as stated | 122 distinct names appear on lines with `environ`/`getenv`; 198 appear as quoted literals (many go through helpers); 213 are mentioned anywhere. "Far more than 50" holds; the exact 128 depends on the regex |
| 5g | `x or time.time()`: five sites | CONFIRMED | `attention/salience_map.py:227`, `salience/salience_network.py:222`, `models/language/cost_tracker.py:376`, `:469`, `:480` |
| 6a | Pickle load dormant unless `enable_semantic` (default False) | CONFIRMED | `similarity/ec.py:413`; the `EmbeddingStore` is created only in `__init__` when the flag is set (`ec.py:588-598`). Nothing in src passes True. A persisted `ec.json` can carry `enable_semantic: true` (`ec.py:1759`), but loading it does not create the store, so the load at `memory_hub.py:724-726` stays gated |
| 6b | Path `_restore_on_open` → `EmbeddingStore.load` → `np.load(allow_pickle=True)` | CONFIRMED | `integration/memory_hub.py:700-727`; `similarity/semantic.py:662` |
| 6c | The file is global `~/.maxim/util/semantic_embeddings.npz` | CONFIRMED | `integration/memory_hub.py:243-246` via `resolve_user_state`. Side effect: it runs `mkdir` on `~/.maxim/util` when the hub is built |
| 6d | Only pickle-capable load in src | CONFIRMED | No `pickle.load(s)`, `joblib`, `torch.load`, `shelve` (only in a sandbox blocklist, `utils/sandbox_executor.py:181`), `dill` or `read_pickle`. The other `np.load` (`embodiment/component_index.py:443`) uses the default `allow_pickle=False`. `transformers_backend.py:281` uses safetensors |
| 7a | Default roster includes the internet tools (bootstrap.py:261-276) | PARTLY | Registered only when `internet_launch_enabled` is True (`runtime/bootstrap.py:255-276`; `utils/internet_access.py:648`). It is a required keyword. On by default in the CLI (`cli.py:2481-2483`) and the embodied runtime (`embodied_runtime/agentic_runtime.py:548`, default True). Off in the simulation (`simulation/orchestrator.py:1141`, `simulation/tools.py:1541`), the API (`api.py:837`) and the console (`console/handle.py:209`). It is a real leak path for any entry point that copies the CLI, but not "the default roster" everywhere |
| 7b | `llm_submit_interval` is 0.5 wall seconds | CONFIRMED | `runtime/loop_controller.py:157`; compared against `last_llm_submit_time` (`:156`), which is stamped with `time.time()` |
| 7c | `create_npc_agent` has no caller in src | CONFIRMED | Defined at `runtime/agent_factory.py:936`; there are no callers in `src/`, and `simulation/dm_runtime.py` never mentions `AgentFactory` |
| 7d | ARCHITECTURE.md :38 / :103 / :182 | CONFIRMED | :38 says agents/ must not execute tools or mutate state; :103 says runtime/ owns orchestration; :182 says the DM runtime's "NPC agents have real memory ... via AgentFactory", which is stale per 7c |
| 7e | Other leak paths cited (register_tool, MAXIM_ALLOW_BASH, lane anthropic default) | CONFIRMED (spot-checked) | `simulation/orchestrator.py:313-329` (`os.environ.setdefault("MAXIM_ALLOW_BASH","1")`, "outlives the sim"); `runtime/lane_backends.py:1269` (the response omits the `runtime/` directory) |
| 8a | `hybrid_arbitration.md` §A.1b: held slot with a deadline, submit gate, split clocks, one replace site | CONFIRMED | `docs/plans/hybrid_arbitration.md:74-85` (the four build pieces) and `:214-220` (*h* is a deadline on the held slot, checked once per pass, never a blocking wait). "Split clocks" there means split cadence stamps (`last_llm_submit_time` drives three things). A different line, `:225-226`, states *h* in "one named clock per world (experience clock, else wall clock)" |
| 8b | M89 bars src/ before 1.4.0 | CONFIRMED, wording nuance | `hybrid_arbitration.md:24-25`: "No `src/` change for this line before the 1.4.0 cut ... mechanization backlog M89." M89 is the backlog row for mechanizing that rule, not the bar itself. The same id is reused at `:303` for the protective-action rule |
| — | Citations for the resumable-think cut points | CONFIRMED | `router.py:944` `_complete_text`; `llm_worker.py:1356-1380` parse; `runtime/tool_dispatch.py:1257` `execute_and_learn`; `runtime/experience_time.py:36` `ExperienceClockDriver(..., monotonic=time.monotonic)` |
| — | Advisor POSIX-only | PARTLY (I checked only the latch) | `_offline.py:29`: the audit hook is POSIX-only in what it names (Windows `CreateProcess` is not listed) |

## Notes: what they got wrong or missed that matters to Overdrive

1. **A think is not one model call.** The headline "one model call returns one action" is wrong for any agent where
   the PFC gate passes. `_run_deliberation_cycles` runs up to 3 model calls back to back, inside the tick, blocking
   on `_wait_for_proposal`, with bio-enrichment between calls. So a resumable `think(state, input)` must carry the
   deliberation cycle, the accumulating transcript and the enrichment results across several pending model requests,
   not just one. The response does list "PFC deliberation blocks inside the tick" under "not yet a value". But its
   central claim, that the only pending request is ever a single model call, understates the state the cut has to
   hold. Separately, `next_actions` lets one call commit a multi-tick action chain without consulting the model
   again. Overdrive's intent door needs a rule for those (validate each step at dispatch time, not once at proposal
   time).
2. **Missed leak path: speculative prefetch.** On every user input, `LoopController.run_prefetch`
   (`runtime/loop_controller.py:611-614`, called unconditionally at `runtime/agent_loop.py:1571`) scans the text for
   file references. It reads files under `os.getcwd()` (`runtime/prefetch.py:422`, `:472`, `:624`) and runs `find`
   subprocesses (`prefetch.py:575-586`), then puts the contents in the first prompt (`agent_loop.py:2993`). None of
   this goes through the tool roster, `ToolPolicy` or the `Effect` ceiling. In Overdrive, player speech to an NPC is
   exactly that input: a player who names a file can pull server-side files into an NPC's prompt. It is also a
   spawn, which the offline latch would refuse loudly. The embedded entry point must not construct the prefetcher,
   and the import-closure test should name `runtime.prefetch`.
3. **The router lock is real and default-shared in Maxim's own multi-agent pattern.** Maxim's simulation shares one
   router across the narrator, the AUT and the fear gate. The lock is held through cloud calls too, so the
   "ten NPCs think one at a time" conclusion stands for any shared router, local or cloud.
4. **The offline latch is narrower than "kills a co-op server's networking."** A server that only listens survives.
   But an outbound connection to a local model server, a peer, or a client-process spawn dies. Either way the
   advisor is unusable as the NPC base, so the conclusion stands while the stated reason is overstated.
5. **`make_agent_rng` returns `random.Random`.** That conflicts with Overdrive's rule that randomness comes from one
   seeded `numpy.random.Generator` owned by `World`, so wiring it as-is would not satisfy Overdrive. Also,
   `seed_all` writes `PYTHONHASHSEED` and reseeds the global `random`, numpy and torch generators process-wide
   (`utils/seeding.py:40-70`), a hidden global effect an embedded host must never trigger.
6. **Counting nits:** the draft's 36 for uuid4 is the better count, and 128 env names is a regex-dependent figure.
   Neither changes a decision.
7. **Smaller issues:** two citations omit their `runtime/` directory (`agent_factory.py`, `lane_backends.py`), and
   one cites a comment instead of the code (`agent_factory.py:611` instead of `bio_stack.py:654`). The facts behind
   them hold.
