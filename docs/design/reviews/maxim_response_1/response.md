# Maxim's response to the embeddable-agent questions (2026-11-16)

Kept verbatim as received from the Maxim design session (read at Maxim `origin/main` 7084f561), in two parts: the
answers, then a ranked list of proposed Maxim changes written after the owner said yes. The Overdrive review of it is
in this folder, one file per lens, plus `synthesis.md`.

---

## Part 1: the answers

Written for: the Overdrive design session, which asked the questions, and you as owner of both lines.

I read everything from Maxim's origin/main at 7084f561. That's the same tree the drafts cite, so I didn't need to fetch. Three read-only agents covered the code, and I spot-checked the citations that carry weight. The Overdrive files came from phase1/design-v2, cloned read-only into my scratchpad.

### The big correction first

The drafts assume Maxim runs an inner tool loop inside each think, and it doesn't. One model call returns one JSON action, plus optional parallel_actions. The loop executes it, and the result becomes ctrl.pending_action_followup, which the next tick submits (runtime/agent_loop.py:2172, :2264). The model never sees a tool result inside a call. LLMResponse.tool_calls has no reader outside the backends.

That makes your problem smaller than you think. In a resumable think, the only pending request is ever a model call. Tool calls aren't pending requests; they're intents the host's door validates. Their results come back as the next percept or follow-up. Maxim's action is your validated intent.

### 1. A resumable think

It fits. The loop is already a hand-rolled state machine. It sits on LoopController fields (pending_proposal, pending_action_followup) and re-enters once per tick.

Where the natural cut is:

- The model side is around LLMRouter._complete_text (models/language/router.py:944). Everything before it produces a request value: prompt build, redaction, provider choice. Everything after it consumes a reply: the parse into LLMProposal (agents/llm_worker.py:1356-1380).
- The tool side is a split of tool_dispatch.execute_and_learn (runtime/tool_dispatch.py:1257) into a dispatch half and a settle half. Today that one function fuses execution with NAc credit and memory writes. That split is your generate-vs-apply rule and your propose/settle amendment, in the single place they belong.

What isn't yet a value:

- PFC deliberation blocks inside the tick (agent_loop.py:3089-3125).
- The worker thread and its queue.
- Contextvar cancel events.
- Loop locals like the same-tool counter.

Use an explicit frozen state object, not a generator. The codebase has no send()-style generators (only @contextmanager helpers), and a generator can't be saved, loaded or replayed.

Factory method or own module? Construction goes in AgentFactory, as the single construction point (docs/agents/runtime-tools.md:32). The deliberation goes in its own module: think(state, input) -> (state', Pending | ThoughtOutput).

Agent method or host-called function? A function the host calls, with a thin method that delegates at most. ARCHITECTURE.md:38 says agents/ must not execute tools or mutate state, and :103 says runtime/ owns orchestration. A function that returns requests satisfies both by construction.

Cancellation doesn't conflict. DECISIONS.md has no cancellation entry. What exists is a per-call contextvar event (utils/cancellation.py) and a process-wide shutdown event (models/language/cancellation.py). Both serve the robot path, and both stay.

Your draft's §4.2 is at the wrong level. It makes the host gateway an LLMBackend that takes a cancel token. That re-imports the blocking thread. It also re-imports the router's _inference_lock (router.py:1080), which serializes every inference on a router, so ten NPCs sharing one router would think one at a time. Put the gateway above the backend: think returns the request, and a host cancel just means resuming with a cancelled reply. Token streaming is only needed for stamping speech and barge-in, so make it a later, separate capability.

Hybrid overlap, flagged for you as owner: this is the same seam as hybrid_arbitration.md §A.1b's loop restructure. That's the held slot with a deadline, a submit gate keyed on attempt state, split clocks, and one replace site. If they're designed separately, the submit path gets restructured twice. They should be one design.

Venue and version: a plan, coordinated with the hybrid line. The src/ work comes after 1.3.6, the loop builder; the hybrid family's M89 already bars src/ before 1.4.0.

### 2. How far the advisor stretches

Not as the NPC base. The advisor was built as the opposite of an embeddable agent: a quarantine for an untrusted observer, made for AvServ (docs/plans/advisor_mode.md). For an NPC:

- It holds exactly one tool, ProposeActionTool, hard-coded (advisor/_session.py:90-122, :132-210).
- Tests pin its import closure and the env vars it reads, so memory and the SEM can't be wired in (tests/integration/test_advisor_gate.py:839, :854).
- It refuses injected backends. It loads a local GGUF file through closed_local, and the only seam is a private test hook (_session.py:244-250).
- It engages a one-way, process-wide offline latch at open (_session.py:784, _offline.py:1-21). That refuses every connect, DNS lookup, spawn and fork for the whole host process, which would kill a co-op server's own networking.
- It's probably POSIX-only (O_DIRECTORY, dir_fd, pread).

What to reuse is its patterns:

- the sealed registry;
- the Effect ceiling (tools/base.py:113-145);
- the unforgeable ToolPolicy pin;
- typed refusals at open;
- budgets enforced in the grammar itself (maxItems: max_calls, _session.py:288);
- the import-closure and env-read-set tests.

How much AgentFactory already covers (your second question):

- Per agent already: Hippocampus, NAc, ATL, SCN, EC, AngularGyrus and the cerebellum, under base_data_dir/<agent_id> (agent_factory.py:1168-1172, bio_stack.py).
- Still global: semantic embeddings, the escalation and fear bridges, DN thresholds, the focus and bounds learners, energy, the cost tracker, lane decisions, provenance, sim reports, config and the nickname registry (store census in the agent report).
- So OD-A12 is half built. The constructor parameter exists; the leftover global stores don't use it.
- Also: the ConceptExtractor thread starts at construction (agent_factory.py:611), so OD-EA7 ("no threads of its own") fails today.

Coverage of your draft's items:

| Item | Covered? |
|---|---|
| A10 entry point | Partly (the advisor's shape, with no memory) |
| A11 tool roster | Partly, and ahead of the draft (sealed registry, ToolEffectRefused, api.py:2107-2112) |
| A12 home | Partly |
| A13 pickle-free load | No |
| A14 gateway | No (the advisor is the inverse) |
| A15 step, think, generate vs apply | No |
| §4.6 budgets | Mostly, but on the advisor only |

Your leak paths are all confirmed:

- register_tool (api.py:2119-2160).
- MAXIM_ALLOW_BASH=1: set process-wide, and it "outlives the sim" (simulation/orchestrator.py:313-329).
- A cloud route through config lanes and the anthropic default (lane_backends.py:1269).
- Phrase commands: input_handlers.py:171-235 and agents/llm_fallback.py:300-350.
- The pickle load (see question 5).
- Env vars: 128 distinct MAXIM_* names are read, not about 50.

Leak paths you missed:

- the default roster's InternetSearchTool, HttpFetchTool and InternetAccessTool (runtime/bootstrap.py:261-276);
- the global stores above;
- provenance and lane-decision JSONL written to ~/.maxim.

Don't enumerate leaks; close them structurally. The embedded entry point must never call build_tool_registry, data_home() or config_loader, and must never read env vars. Prove that with an import-closure test and an env-read-set test, as the advisor does.

Venue: part of the embeddable-agent plan. PRs 1–3 (roster, home, pickle) can run on their own clock, before 1.3.6.

### 3. A turn-taking substrate (OD-H5)

It belongs in the 1.5 hybrid line, but not in learned_hold_window. That plan learns how long the action hold lasts. Floor-holding is what the body does during the hold in the speech channel, plus a rule for when to yield. It maps directly onto §A.1b:

- During the hold h on the speech component, the substrate's default act is a content-free floor-holding act.
- When the hold passes about 1 s, the substrate yields the floor.
- When the late answer arrives, that's the LLM pre-empting after the yield, so it opens a new turn with a misplacement marker. That's the conversation-analysis term for "About what you asked..." (Schegloff & Sacks 1973).

Home: a fifth split-out plan under hybrid_arbitration.md. It would cite §A.1b, and sem_interruptibility.md for the rule that fillers can be cut off at any time. Fold OD-H4 (deliberation that starts during the other person's turn) into it.

What it needs to pass Maxim's process:

- Choose the filler from the predicted delay, not the elapsed one. Clark & Fox Tree's "uh" versus "um" signals the speaker's expected delay. So the plan needs a latency predictor, and in an embedded world that's modelled world time, which is your OD-H2. I agree with OD-H2.
- Make thresholds parameters, not constants. Stivers et al. 2009 found means differing across languages by up to about 460 ms. Measure them on the listener's clock, which in a game is world time.
- Enforce "no claims" structurally. Floor-holding acts carry no proposition, are never stored as utterances and are never credited. Exp 63b's null came from exactly this kind of contamination: its recall cues were the stall template, and template words crowded out real content (docs/experiments/exp63c_scripted_recall_prereg.md:18).
- Gaze aversion on Reachy is motion. It goes through goto_target and has to compose with DN tracking, so the robot half sits behind the hardware-safety brief. In a game it's free.
- Be honest about the framing. This is behavioural (conversation analysis), not a neural mechanism. It enters as [engineering] with the innate-prior tier, and earns its place only through a pre-registered experiment on a measurable outcome: gap distribution, overlap rate or repair rate.
- Pushback: after about 1 s, people usually give an account ("let me think") before they give up the floor. Yielding is one option, not the only one.

Venue: a plan now; any claim needs a pre-registration. Version: the 1.5 hybrid line, on paper only.

### 4. Determinism hooks

The recount, reproducible with git grep -nE over src/maxim:

| Count | Your number | Maxim's | Notes |
|---|---|---|---|
| uuid4 calls | 36 | 35, in 24 files | Your extra one is probably a comment or docstring hit |
| Global random | 27 | 27 | 26 draws in 9 files plus random.seed, at utils/seeding.py:51 |
| default_factory clock fields | 36 in 19 files | 36 in 19 files, plus 1 | The extra is time.monotonic, at tools/registry.py:146 |

There are also 3 legacy global np.random calls; one is attention/salience_map.py:437.

The factory fields are the tip. There are 608 time.time() calls in 178 files, plus 145 time.monotonic() and 20 datetime.now.

Scope it to embedded agents: yes. About 30 of the 51 affected files are on the per-step path. All the global random draws but one (an Anthropic backoff jitter) sit in attention, default_network, spatial and decisions/significance.py:190. Prove the scope with a test, not a count: step the agent under a frozen fake clock and seeded RNG, and plant a wall-clock read that must fail.

What already exists to build on:

- make_agent_rng (utils/seeding.py:79) exists but has no caller.
- ExperienceClockDriver(clock, monotonic=...) is injectable (runtime/experience_time.py:36).
- 13 functions already take a now/current_time/timestamp parameter.

Venue: your world-clock plans, A-pre on its own clock and A-post with 1.3.6. Robots keep wall-clock defaults.

### 5. The pickle load

File it now, as a 1.3.x issue, with three corrections to the draft:

- It's dormant by default. It only runs when enable_semantic is on, which defaults to False (similarity/ec.py:413, :588) and which nothing in src sets.
- It is at session start: MemoryHub._restore_on_open → EmbeddingStore.load → np.load(..., allow_pickle=True) (integration/memory_hub.py:719-727, similarity/semantic.py:662).
- The file is the global ~/.maxim/util/semantic_embeddings.npz, not per agent (memory_hub.py:243-246).

It's the only pickle-capable load in src, and no existing issue covers it.

Your other two issues:

- OD-I1 is right, but it's five sites, not one: salience_map.py:227, salience/salience_network.py:222, and models/language/cost_tracker.py:376, :469 and :480.
- OD-I2 is weaker than written. ModulatorResult is an in-process return value; it's never persisted and never crosses a wire. So CC3's scope arguably doesn't cover it. The honest fix is a docstring that says so, not the SHAPE-FROZEN marker. It's a nit-level issue at most.

### Where your drafts are wrong about Maxim

- The inner tool loop: §4.6's "tool calls in the turn" and §9's "tool calls inside think" don't exist (see above).
- "Tool schemas in a fixed order": planning sends no native tools=. Tools are described in the prompt text.
- The gateway as a cancellable LLMBackend: it's at the wrong level (question 1).
- A new home parameter: the factory already has persistence_dir. The gap is the leftover global stores.
- "One thread per agent": that understates it. There's the ConceptExtractor thread, the worker pool and the shared router lock.
- "The DM doesn't build NPCs through AgentFactory": your draft is right, and Maxim's ARCHITECTURE.md:182 is stale. create_npc_agent has no caller in src. That's a small docs issue for Maxim.

### Summary

| Question | Answer | Venue | Version line |
|---|---|---|---|
| Resumable think | Fits: one state object, cut at the router and at execute_and_learn; share the design with HA §A.1b | Plan | After 1.3.6; hybrid parts after 1.4.0 |
| Advisor as the NPC base | No; reuse its patterns. Factory covers the core stores | Inside the embeddable plan; PRs 1–3 on their own clock | 1.4 era |
| Floor-holding substrate | Fifth hybrid split-out plan, not learned_hold_window | Plan now, prereg for any claim | 1.5 hybrid line |
| Determinism | Scope to embedded agents; prove it with a planted-read test | World-clock plans | A-pre on its own clock; A-post with 1.3.6 |
| Pickle load | Its own issue now, with the three corrections | Issue | 1.3.x patch |

Decisions this leaves for you:

- whether the hybrid's loop restructure and the embeddable think become one design;
- whether the floor-holding plan gets drafted now as a fifth hybrid split-out;
- whether to file the pickle issue, OD-I1 (five sites) and the ARCHITECTURE.md:182 fix on Maxim now.

I haven't filed or edited anything in either repo.

---

## Part 2: proposed Maxim changes (after the owner said yes)

Several things I found are worth changing, and they fall into three groups. Some are worth doing on engineering grounds alone. Some should only be adopted if an experiment earns them. And for some, the game's real value is testing a design choice Maxim made without evidence.

### A. Worth doing anyway: correctness and isolation, guarded by tests

These need no experiment. Each makes Maxim more correct for robots too, and each can be proven by deleting what it guards.

1. One AgentHome object, owned per agent. The factory already scopes the core memory stores. About nine families are still process-global: semantic embeddings; the fear and escalation bridges; DN thresholds; the focus and bounds learners; energy; the cost tracker; provenance; lane decisions; the nickname registry. Route them all through one object, and an agent's home can never half-resolve to ~/.maxim. Test isolation improves for free. Guard: two agents in one process never open the same file.
2. Per-agent randomness, through the existing make_agent_rng. utils/seeding.py:79 already has make_agent_rng, but nothing calls it. The 26 global random draws sit almost entirely in attention, default_network and spatial. Today, adding an NPC changes another NPC's idle behaviour. This is small and mechanical.
3. One clock and id seam on the step path (call it AgentTime). Robots default to the wall clock, and embedded agents get the host's clock. It's scoped to the roughly 30 step-path files, not all 178 files that read time.time(). Prove it with a planted wall-clock read that must fail.
4. Pickle-free embeddings, and the five x or time.time() sites. Both are already issue-sized.

Why these matter for research, not only for Overdrive: once an agent's state, clock, RNG and ids belong to it, Overdrive can replay the same run bit for bit with one variable changed. Paired replays shrink the confidence intervals that BF2 floors and effect-size pass rules depend on. That's the most valuable thing the game can give Maxim's research integrity, and it rests entirely on items 1–3.

### B. Worth building, but adopt only if an experiment earns it

5. The stepped deliberation seam: a state object with a request/reply cut. It is the same seam as the hybrid's §A.1b loop restructure, so build it once. Engineering bar: the agent's state digest is identical whether a reply returns instantly or after a seeded random delay. Behavioural question: does a robot on the new seam behave the same as one on today's blocking worker? Run a parity check on the Exp 49 and Exp 60 tasks before it replaces anything.
6. Split execute_and_learn into dispatch and settle (runtime/tool_dispatch.py:1257). This is what most directly attacks a known gap. Memory says R4, delayed credit, is where Maxim's ladder is weakest. Once credit is applied when the outcome is measured, rather than when the action is dispatched, Overdrive can deliver outcomes N ticks later on purpose. Then sweep N and measure credit accuracy.
7. Replace the router's one inference lock with a prioritized per-agent request queue. The _inference_lock (router.py:1080) makes ten NPCs think one at a time. The experiment: competence and response latency as the NPC count grows, with a danger-before-dialogue priority against first-in-first-out.
8. Make capability-based tool rosters the default for all agents, not only the advisor. Today, mode-based containment (allowed_dirs) is the security model, and a robot that hears a stranger has the same injection surface as an NPC. The experiment is an adversarial-prompt red-team suite. What has to be measured is task competence lost under the smaller roster; the security gain is guaranteed by construction.
9. Trigger deliberation by escalation rather than the wall clock. llm_submit_interval is 0.5 wall seconds (loop_controller.py:157). Escalation is the hybrid's core claim, and Overdrive's latency sweep (OD-HX2) is the ideal calibration for it.

### C. Design choices Overdrive can finally test, not refactor

10. One action per call, versus an inner tool loop. Maxim never shows the model a tool result inside one call. That was a default; nothing recorded justifies it. A game can compare loop-carried follow-ups against a ReAct-style inner loop on the same tasks. It also pairs naturally with the B2–B4 baselines (Reflexion first).
11. Modelled latency versus observed latency in the hold (your OD-H2). Overdrive can show directly whether a hold that learns from observed latency picks up a dependence on the hardware.
12. Floor-holding (the fifth hybrid split-out plan). It's only measurable in a world where gaps and overlaps are timed exactly.

### Two cautions

- Overfitting Maxim to the game. A change Overdrive earns is earned in a game. Maxim's ledger never takes game runs. Every adoption needs a transfer check in a Maxim-owned harness or on the robot before it moves a claim. That's your OD-HX5 pattern, applied generally.
- Scope pressure. Items 1–4 ride on existing infrastructure, so they pass the front gate cleanly. Items 5–9 each need their reason written down, and 5, 6 and 9 must be designed together with the hybrid line, or the same submit path gets restructured twice.

Suggested order: 1–4 first, because they unlock replay, and replay makes every later experiment cheaper and more trustworthy. Then 5 and 6 together, after 1.3.6. The rest waits for those.

They offered to turn this into a ranked candidates doc in Maxim's plan format, with each item's front-gate reason, venue and the experiment that would earn it.
