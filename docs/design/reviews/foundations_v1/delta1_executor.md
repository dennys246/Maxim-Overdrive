# Design review, delta round 1: Executor (foundations v1)

Lens: Executor, design-time, delta round. Commit: `18623ce` (branch `phase1/design-v2`). Date: 2026-11-16. The
questions: are the claims true, and can the checks fail?

Under review: `git diff 4f7a754 18623ce -- docs/`, meaning `boundaries.md` v3, `npcs_and_sem.md` v2, every draft in
`docs/maxim_upstream/` this pass touched, and `roadmap.md` Phase 3.

Read against:
- Maxim `origin/main` at `7084f561`, through `git show` and `git grep` only;
- the installed pymaxim 1.3.3. It has neither `runtime/tool_policy.py` nor `maxim/advisor/`; both shipped on `main`
  after 1.3.3.

Nothing in any worktree or in Maxim was changed. Anything marked *verified* was run under the session scratchpad
(`d1/`), on Python 3.10.19 and 3.14.6, with numpy 2.2.6 and 2.5.4.

Counts: **2 BLOCKER, 7 SHOULD-FIX, 14 NIT.**

## Did round 1 close?

| Round 1 | Status at `18623ce` |
|---|---|
| X-1 the tripwire can't see what it claims | **Mostly closed.** The profile hook replaces patching. What's left is S-1: numpy can't be seen, the match must be by equality, and logging trips it. |
| X-2 `[now]` tests red against real Maxim | Closed. They are strict red gates until tier A, and `context_pool` is in OD-A3. |
| X-3 counts | Closed. On `7084f561` I count 37 `uuid4(` and 26 global-`random` calls, the same on `4b773ef8`. That is within method noise of the 36 and 27 the documents use. |
| X-4 `hash()` | Closed. Reframed as hygiene ("Corrected evidence"). |
| X-5 CC3 misquote | Closed (SEM plan §1). The precedents check out: #403 (`92eae365`, 2026-07-19) and #1261 (`d47936e2`, 2026-10-14), both after v1.0.0 (2026-06-17). |
| X-6 keys never reach dispatch | Closed in substance. The amendment names the failure return. S-7 is a new sibling. |
| X-7 how stamps get the clock | Closed. The decision is an explicit pass, with defaults kept and the tripwire as backstop. |
| X-8 fence column and plumbing | The fence part is closed: `tool_dispatch.py` counts as fenced, and the A-pre/A-post split is in. The plumbing part has a new hole (S-3). |
| X-9 calendar | Closed (`Calendar`, with `None` meaning no weekly, monthly or annual phase). |
| X-10 M76, G4, M72 | Closed. All three are quoted correctly. |
| X-11 Δt tolerance and plant | Closed. 1e-9, with the plant in an exponential process. N-8 is residue. |
| X-12 schema, prompt, `root_packages` | Closed. N-7 and N-10 are residue. |
| X-13 additive vs batched | Closed. §9.3 matches the SEM plan, deep-freeze is OD-C7, and the stale §12.3 note is gone. |
| N-1 to N-5 | Closed (S3–S6; no line number for "You are Maxim"; OD-C4's `target` note; WC3 uses a fake wall; PR 1 is sized M). |

## Verified true on `7084f561` (45 sampled)

- **Clock and stepping**
  - `runtime/experience_time.py::ExperienceClockDriver`, duck-typed `experience_turns()` and
    `experience_us_per_turn` (:17-19, :50-58).
  - `experience_clock_decay.md`:
    - "adds no clock, no bus and no SCN surface" (:77);
    - Q8, "a fixture 'turn' is step-clocked (1/target_hz)" (:102);
    - Q4 "ONLY through `Embodiment.advance(dt)`" (:93), and Q7 for `apply_decay=` (:100);
    - the §(g) table rows, verbatim (:284-289).
  - `utils/seeding.py::make_agent_rng(base_seed, agent_id) -> random.Random`, derived through SHA-256, and
    `seed_all`.
  - `tests/unit/_loop_harness.py::_StepClock`, which patches the global `time` module's attributes (:167-212), and
    `scripts/survival_world/scripted_water.py::StepClock` / `LockstepTime` (#951).
  - `runtime/agent_loop.py`: 14 `time.time()` calls, `run_id = time.strftime(...)` (:149), and two
    `thought:{uuid4}` refs. `tool_dispatch.py`: 5 `time.time()` calls.
  - `DefaultNetwork.update_hz = 30.0`, and `time.time()` at :561, :836, :931 and :1390.
  - `run_agentic_loop(target_hz=30.0)`.
  - Hippocampus `dedup_window_s = 30.0`, `uuid4` at :917, `hash(...)` at :1055.
  - The 36 `default_factory=time.time` stamps in 19 files.
- **Decisions, plans, backlog**
  - G17 "the type waits for the stage that needs it" (`DECISIONS.md`:599), and G3's "lockstep-testable" (:690).
  - DECISIONS 2026-11-11, the hybrid 1.5 candidate line.
  - TF1–TF3 (`tool_failure_credit.md`:56-62; `DECISIONS.md`:451-458), with `book_refusal` and `book_machine_refusal`
    (:135).
  - D53 in `docs/bugs/README.md` and `docs/agents/embodiment.md`.
  - `hybrid_arbitration.md`:
    - HA-O1 to HA-O16, all present;
    - "motivation, not evidence" (:50);
    - "escalates if ANY" (:167);
    - §A.1b;
    - HA-O4, HA-O12 and HA-O14.
  - The waiting-cost quote in `learned_hold_window.md` (:19).
  - The quote in `foreign_advice_layer.md` (:34-35).
  - G4's text in `deferred/hybrid_substrate_reflex_runtime.md` (:5-7).
  - M72, M76, M83 and M89 in `docs/plans/outstanding.md`, worded as quoted.
  - The fence, verbatim (`roadmap_1_3_x.md`:358-360), and its 1.3.6 exit item on `_llm_unavailable` (:1256).
- **Pins and SEM**
  - The function-length pins in `utils/function_length_baseline.json`:
    - `ModulatorAffordanceTool.execute` 502 (measured 502);
    - `record_outcome` 392 (measured 392);
    - `execute_and_learn` 357 (measured 357);
    - `Embodiment.evaluate_failures` 224.
  - `FailureMode.evaluate` sets `last_fired = time.time()` (`sem.py`:1560).
  - `ENTITY_FORMAT_VERSION: str = "1.1"`.
  - The marker text in `AffordanceSchema` and `CouplingSpec`, and the path (b) wording in `persistence-config.md`
    (:83).
  - `ModulatorResult`: five required fields, a bare `metadata` dict and no CC3 text.
  - The OD-C6 merge: `**result.metadata` comes after `"success": True` (`tool_bridge.py`:907-921).
  - The failure return drops `metadata` (`tool_bridge.py`:581-582), and `tool_dispatch.py`:370 books NEGATIVE first.
  - D53's "the historical behaviour: mechanical success means POSITIVE" (`tool_dispatch.py`:105-106).
  - Pulse pins `pymaxim[console,reachy,tts]>=1.3.3,<2.0`, in the `robot` extra (`apps/reachy/pyproject.toml`:50).
- **Prompt time**
  - `prompt_builder.py`: `datetime.now()` at :1125 and :2400, `build_identity_section(..., date_str, time_str)` at
    :159, and "You are Maxim, a robot assistant." at :167.
  - The canned answers in `llm_fallback.py` (:290-313).
  - `context_pool.py` renders `[HH:MM:SS]` through `time.localtime` (:468, :493).
- **Other**
  - The `OD-I1` line (`salience_map.py`:227). The same pattern is in `cost_tracker.py`:376 and
    `salience_network.py`:222, and the issue's grep would list both.
  - `semantic.py`:662 calls `np.load(path, allow_pickle=True)` on a file saved with `dtype=object` arrays.
  - `data_home()` is cached in a module global, with `_reset_caches`.
  - `build_tool_registry`:
    - registers `Read/Write/Edit/ExecuteFile`, `Bash` and `GitCommit` (:132-141);
    - registers `ModeSwitchTool` (:231);
    - registers the internet tools only under the launch cap (:259-276).
  - The `LLMBackend` protocol is as described.
  - `_MaximPeerBackend._stream_chunk` exists, with the #1370 docstring.
  - The `OperationalMode` values are passive, active and singularity.
  - The pain-bus docstring quotes: the ContextVar note, the per-`(entity, failure_mode)` gate, and "Bio-mapping:
    FUNCTIONAL … sensitization kinetics".
  - `ReactionBus.DEFAULT_REFRACTORY_S = 0.5`.
  - `OscillatorNetwork` has four scales, and `math/ips.py` has `weber_fraction = 0.15`.
  - The SCN and ANALOG rows of `bio_faithful_roadmap.md` (:35-36), and the climbing-fiber row (:55).
  - OD-B1: `AgentPool._generate_llm_response` never mentions the hippocampus. OD-B4: `_handle_message` only logs.
  - Session V's `1305.owned-rng` and `1263.thread-guard` (`roadmap_1_3_x.md`:673-674).
  - The `TemporalSignature` phase sources.
- **Counts:** the embeddable plan's 9 PRs (3 S, 4 M, 2 L); the world clock's 11 PRs (A-pre: 8, 2 S and 6 M; A-post:
  3 M). Both add up.

## BLOCKER

### D-1. The embeddable agent's front gate misses shipped infrastructure: the atonia composition, and AgentFactory's per-agent homes and empty registry

`embeddable_agent_DRAFT.md`:
- the §2 bullets on TB2-B1 and TB2-B2;
- §3's rows "Closed tool roster", "Per-agent home" and "Host-supplied model";
- §4.3 and §4.4;
- §7, "No recorded decision says an agent must own its loop or its model calls";
- PR 1 and PR 2.

Also `decisions_entry_DRAFT.md` (Reason), `npcs_and_sem.md`:561, and the NPC tool-roster row in `boundaries.md` §5.

None of the Overdrive documents cites `advisor_mode.md` or `atonia_gate_approach_notes.md`. Maxim's own front-gate
question is exactly the one this draft fails.

**The atonia composition (#1315, Session V) has shipped on `main`.** It is not yet in a release.
- `tools/base.py::Effect`: seven flags, among them `WRITE_LOCAL` ("a tool that spawns a process … declares `ALL`"),
  `NETWORK` and `GOVERN` ("mode, autonomy level, internet switch, allowed directories, the tool set"). There is also
  `exceeds(effect, ceiling)`, and `Tool.effect: ClassVar[Effect]`.
- `runtime/tool_policy.py::ToolPolicy` holds a name gate, an **effect ceiling** and **pins** (the exact tool objects
  it authorises). It is "required and keyword-only" on every `Executor` (owner decision V3: `None` is a `TypeError`).
- `advisor/_session.py::SealedToolRegistry` raises on every write after construction, and dispatch requires
  identity with the pinned instance.
- `advisor/_session.py::AdvisorSession.ingest` is **one bounded turn per call**: "No loop, no autonomy controller, no
  prefetch, no data home, and no router is built". That is owner decision V1. V4 adds that its model runs "through a
  closed backend rather than `LLMRouter`".
- `_offline.py` holds an audit-hook latch (V8). That is prior art Maxim will raise against any new Python-level
  enforcement mechanism, the tripwire included.

**AgentFactory already isolates an agent's stores and doesn't build the default roster.**
- `AgentFactory.__init__(base_data_dir=...)` takes a home.
- `create_agent` gives "each agent … Hippocampus (separate persistence path), NAc …, ToolRegistry (empty)". It
  resolves a per-agent `persistence_dir` (:770, :1036-1042), which defaults to `<data_home>/agents/<agent_id>`.
- `create_full_agent` takes a caller-built `tool_registry`.
- #1337 keeps a census of every agent-home writer: `utils/paths.py::AGENT_HOME_PATTERNS`, guarded by
  `tests/unit/test_clear_memory_1337.py`.
- `api.py` takes `home_dir`, and `console/handle.py` takes `home=`.

**So three claims are false on the path Overdrive uses** (`AgentFactory`, as in `boundaries.md`'s adapter table):
- "Ten NPCs share one hippocampus". Agents built by the factory don't.
- "A default agent gets `BashTool` …". The factory's registry is empty, and `build_tool_registry` runs only for the
  CLI, `maxim.run`, the console, the embodied runtime and the sim AUT.
- "A process global can't serve several agents" ("Rides on it? No"). The factory already serves several.

**The failure scenario:** the plan goes to Maxim's three-lens review.
- The Architecture lens answers the front gate with `ToolPolicy.pinned` plus `SealedToolRegistry` plus an effect
  ceiling for OD-A11, and `AgentFactory(base_data_dir=)` plus `persistence_dir` for OD-A12.
- Its §7 argues against "mode-based containment", which Maxim has already superseded.
- Its V1 precedent, Maxim's own loopless bounded-turn entry point, goes uncited. That precedent is the best evidence
  for OD-A15.

The plan is returned, and Overdrive's credibility on the other drafts suffers with it. Two of its nine PRs, and its
PR 2 census, re-do shipped or planned work, and they touch files Session V owns (S-4).

**The fix:**
- Re-run the front gate against `advisor/`, `tool_policy.py`, `tools/base.py::Effect` and `agent_factory.py`.
- Restate OD-A11 as "an embedded agent is built with a pinned `ToolPolicy` whose ceiling excludes `WRITE_LOCAL`,
  `NETWORK`, `COMMS` and `GOVERN`, behind a sealed registry". The new part shrinks to the embedded builder's refusal.
- Restate OD-A12 as "every store reachable from an embedded step resolves under the factory's `persistence_dir`; list
  the ones that don't". That is a census against #1337's patterns, not a new home mechanism.
- Cite V1 and V4 as precedents for `step`/`think` and the host gateway.
- Correct TB2-B1 and TB2-B2 in `decisions_entry_DRAFT.md`, `npcs_and_sem.md` §6.1 and the boundaries roster row: the
  roster risk is real for `maxim.run`-style builds, not for factory-built agents.

### D-2. The ownership write window, as specified, lets a handle outlive the window, and its proof test can't see it

`boundaries.md` §4.1: "`with cells.writing() as w:` yields fresh writable arrays …, and swaps them in as the new
read-only owners at exit. No handle outlives the window." The proof: "a view unlocked inside a window, written after
the window closes, must not change the world".

*Verified* (`d1/win.py`, numpy 2.5.4):
- **Swap at exit** (the yielded array becomes the owner, and `writeable=False` is set on it): a view `v = w[:]` taken
  inside the window stays writable after it. `v[1] = 99` **changes the world**. Clearing the base's flag doesn't
  reach views that already exist.
- **The specified proof can't catch it.** "Unlocking" a view of the read-only owner raises `ValueError: cannot set
  WRITEABLE flag to True` whichever exit is used. So the test is green on the leaking implementation. That is the
  same shape as DR-B4, the defect this fold was meant to close: the guard fails while its proof passes.
- **Copy at exit** (a fresh copy becomes the owner) is safe, and costs one array copy per window.
- **A refcount check at exit** detects any outstanding view: views hold references to their root base. After
  `v = w[1:]; vv = v[:1]`, `sys.getrefcount(w)` is +2, and `vv.base is w`.

**The failure scenario:** heat keeps a scratch view across steps for speed (`self._buf = w.temp[...]`), which is
ordinary numerical code. From the next tick on it writes the world outside any window, on any thread. Every proof
test is green.

**The fix:**
- Specify the exit: either copy (the published frame copy, which §4.2 already makes on change, can become the new
  owner), or assert that the yielded arrays' refcounts are back to baseline and raise if a handle escaped.
- Replace the proof with the attack that matters: take a view of the **yielded** array inside the window, write it
  after exit, and assert that the world is unchanged or that exit raised. Keep the unlock case as a second test.

## SHOULD-FIX

### S-1. Tripwire residue: numpy's global RNG is invisible, the match must be by equality, and logging trips it

`boundaries.md` §3 ("matching the function objects themselves"; the denylist includes "numpy's global `np.random`";
`logging` is explicitly allowed in the core). `world_clock_release_DRAFT.md` §3.3 ("matches the called function
**object**"; the denylist includes "numpy's global `np.random` functions").

*Verified* (`d1/tw.py`, `d1/np2.py`, `d1/lg.py`, on 3.10 and 3.14):

| Call | Identity match | Equality match |
|---|---|---|
| `time.time()`, `os.urandom` (behind `uuid4`), `random.random()` | caught | caught |
| `datetime.now()`, `datetime.fromtimestamp()` | **missed** (a new bound method on each access) | caught |
| `random.choice`, `randint`, `uniform` (Python methods; caught only through inner `getrandbits`/`random`) | **missed** | caught |
| `np.random.choice()`, `np.random.rand()` (Cython `method` objects) | **missed** | **missed**: no `c_call` event is emitted at all |

- **The numpy planted call is red forever.** "Each proven by one planted call" can't be met for numpy with this
  mechanism. Maxim has a live site on the embedded path: `attention/salience_map.py`:437 `np.random.choice(...)`, in
  A-pre PR 5. `Rng` is a `random.Random`, so the plan also gives that site nowhere to move.
- **`logger.warning` trips the hook.** A `LogRecord` calls `time.time_ns()` (`time.time()` on 3.10),
  `threading.get_ident()` and `os.getpid()`, all of them on the denylist. `logger.info` below the level doesn't.
  So a correct core that logs a warning goes red, unless `logging/__init__.py` frames are on the allowlist.
- **The documents disagree.** Boundaries uses `threading.setprofile_all_threads` on Python 3.12 and later; the draft
  says it "is not used". With all-threads profiling, the planted "timeout on another thread must stay green" holds
  only if the hook filters by thread, and that isn't specified.

**The fix:**
- Match by `==` on the bound callable, or on `__self__` plus `__name__`.
- For numpy's global functions, use a second mechanism: swap `np.random.mtrand._rand` for a raising `RandomState`
  under the test, or rely on the AST scan.
- Allowlist the `logging` frames by name.
- Pick one threading rule and state the thread filter.
- In the draft, give `salience_map`'s draw a home: `Rng` gains a numpy `Generator`, or the site moves to
  `random.Random.choices`.

### S-2. The planted `BashTool` can't tell an allowlist from a denylist, and a construction-time check misses later registration

`boundaries.md` §5 roster row and §10; `embeddable_agent_DRAFT.md` OD-EA1 and §4.3.

The rule is an allowlist ("refuses … any other tool"). A check written as `if "bash" in registry` turns the planted
`BashTool` red and passes every other tool: `HttpFetchTool`, a user-injected tool, or `generate_entity_tools` output.
The check also runs only at construction (draft §4.3), while Maxim's registries accept tools through `register`,
`register_scene_tools`, `generate_entity_tools` and user-tool injection after construction. Maxim's advisor plan
names that as the reason for a *sealed* registry.

**The failure scenario:** a scene load calls `generate_entity_tools` after the adapter's check. A
`set_entity_sensor`-class tool, or a mode tool, reaches the NPC, and OD-EA1 stays green.

**The fix:**
- Plant a novel tool too, one no denylist names (for example `class Notes(BashTool): name = "notes"`, or any tool
  whose `effect` exceeds the ceiling).
- Plant a registration after construction, and a same-name replacement. Each must refuse.
- On Maxim's side, use `SealedToolRegistry` (D-1).

### S-3. A-pre PR 2 wires `AgentTime` "from the embedded entry point", which doesn't exist until after 1.3.6

`world_clock_release_DRAFT.md` §6, PR 2; `embeddable_agent_DRAFT.md` §5, PR 5 ("L, yes, after 1.3.6").

A-pre is sold as shippable on its own clock. Its plumbing starts at an entry point that lands only with the
embeddable plan's fenced PR 5. Of the `LLMWorker`'s eight construction sites, one is in the fenced
`simulation/orchestrator.py` (:1556, :1708), and no unfenced one is "embedded".

So A-pre's PRs 2–7 ship collaborators with no caller on any shipped path. That fails Overdrive's "a fix ships with a
caller" and Maxim's own Wire-integrity lens. A-pre's exit tests (OD-WC1 to OD-WC4) need a shipped embedded path,
and only PR 10 (A-post) flips them.

**The fix:** either name a pre-fence carrier, such as the `AdvisorSession`-style bounded turn (D-1) or a test-only
embedded harness, and say what A-pre's exit proves on it; or admit that A-pre's runtime effect starts at A-post, and
size the risk of two plans waiting on one PR.

### S-4. "Fence: no" isn't "free". Session V owns most of the files the embeddable plan and A-pre touch

`roadmap_1_3_x.md`:997, Session V's row, owns:
- `runtime/bootstrap.py`, `runtime/agent_factory.py`, `runtime/tool_dispatch.py`;
- `embodiment/tool_bridge.py`;
- `api.py`, `create.py`, `modes/`;
- `agents/autonomy.py` (4 of the 36 stamps);
- `similarity/{encoder,semantic}.py` (item 10's offline refusal).

The embeddable plan's PRs 1–3 and the world-clock A-pre PRs 4 and 7 land in those files, and the drafts never name
the owning session. The draft also attributes the "touches no decomposition-fenced file … holds nothing" precedent to
the atonia gate (N-1).

**The failure scenario:** OD-A13's pickle-free embeddings PR conflicts with Session V's item 10 edit to `semantic.py`,
and the plan review asks who grants the hunk.

**The fix:** add an ownership column next to "Fence" in both plans' build tables, and sequence or co-own with
Session V.

### S-5. OD-I2's premise: `ModulatorResult` neither persists nor crosses a wire, and OD-C5 doesn't need it

`issues_now_DRAFT.md` OD-I2; `sem_breaking_change_plan_DRAFT.md` "Depends on: OD-I2", OD-C5.

CC3 (`CLAUDE.md`:105) binds a frozen dataclass "that persists or crosses a wire". `ModulatorResult` is an in-process
return value. Nothing serialises it in `src/`: no `to_dict`, no `from_dict`, no `asdict`. "Crosses the tool boundary"
is not a wire. The "done when" has no check: "the CC3 lint (if it covers `sem.py`)". `tests/unit/test_cc3_forward_compat.py`
covers `SensorReading` and `Episode`, not `ModulatorResult`, so nothing can fail.

And a type with no marker is *less* constrained, so OD-C5's trailing defaulted field doesn't depend on OD-I2.

**The failure scenario:** Maxim closes OD-I2 as not-a-defect, and OD-C5 is blocked on a closed issue.

**The fix:**
- Reframe OD-I2 as "declare `ModulatorResult`'s stability as part of the `Modulator` protocol's public surface",
  with a test such as a `test_cc3_forward_compat` case or a marker assertion that fails without the docstring.
- Drop it as a prerequisite of OD-C5, or say why it is one.

### S-6. The model-gateway front gate: three backends stream, and a recorded rationale against cancel tokens goes unnamed

`embeddable_agent_DRAFT.md` §2 ("Streaming exists inside one backend … nothing can cancel a call"), §3's
"Host-supplied model" row, §4.2 (`supports_cancel` takes a cancel token), and §7 ("No recorded decision says …").

- **Three backends stream, not one.** `anthropic_backend.py`:138 (`_stream_response`, :473) and `openai_backend.py`:149
  set `supports_streaming = True`, as `maxim_peer_backend.py`:384 does. All three collapse the stream to one
  `LLMResponse`. So the core claim stands: no caller reads tokens as they arrive.
- **A fourth capability flag exists.** `router.py`:1731 checks `supports_request_context`, so "the existing three"
  undercounts (N-14).
- **Cancellation exists and was decided.** `models/language/cancellation.py` is a process-wide `threading.Event`
  that the anthropic, openai and peer backends consult. Its docstring records the rationale: "threading a
  cancellation token through every signature would be invasive and brittle. A single well-documented global is
  cleaner". `supports_cancel` argues against exactly that, and the plan must name it under Maxim's own "push back by
  name" norm.
- **V4 is a precedent.** The advisor's model runs through a closed backend, not `LLMRouter`.

**The failure scenario:** the reviewer points to `cancellation.py`. The plan's "nothing can cancel a call" reads as
unresearched, and the per-call token loses to the recorded global.

**The fix:**
- Correct the streaming sentence.
- Cite `cancellation.py` and argue against it: a process-global event cancels every NPC's call at once, which is the
  isolation failure §4.5 forbids.
- Cite V4.

### S-7. `measured_drive_transitions` isn't promoted to dispatch. It is consumed inside the bridge call, so settle can't reuse "the same path" as is

`propose_settle_amendment_DRAFT.md` §1 ("as `outcome_valence` and `measured_drive_transitions` are"), §2's
"Measured drive changes reach credit" row ("promoted by the bridge"), §3.1 ("NAc credits through the same D53 and
measured-transition path"). Also `issues_now_DRAFT.md` OD-I2 ("the bridge promotes `outcome_valence` and
`measured_drive_transitions`").

`tool_bridge.py`:678-679 reads `result.metadata["measured_drive_transitions"]` and turns it into
`drive_progress_by_drive`, `drive_potential_diff` and `drive_relief_channel` (:933-952), inside the 502-line
`execute`. Only `outcome_valence` is promoted as a key (:967-970). A receipt delivered at `settle` has no bridge call
frame around it. Crediting its transitions "through the same path" means extracting the measured-credit block out of
`execute` first.

**The failure scenario:** PR 2 promotes the receipt's transitions as a `side_effects` key, assuming dispatch reads
them. Dispatch doesn't, and settle-time drive credit is silently zero. The exactly-once test still passes, because it
counts bookings, not their value.

**The fix:**
- Say "consumed by the bridge's measured-credit block", and name that extraction in PR 2's sizing.
- Have the exactly-once test assert the booked value as well as the count.

## NIT

- **N-1.** The A-pre precedent quote is the embodied-device plan's, not the atonia gate's: "holds nothing, and it
  touches no decomposition-fenced file" (`roadmap_1_3_x.md`:1193-1194). The draft also reverses its order.
- **N-2.** `from uuid import uuid4` is in **6** files, not 5. One is a local import:
  `bridges/tool_pain_bridge.py`:237.
- **N-3.** The "5 `strftime` session ids" in `orchestrator.py` are 4 calls and 1 comment (:999). Two of the calls are
  ids (:186, :1005) and two are file names (:2099, :2289).
- **N-4.** Two "unverified" items can be verified.
  - `world_set_axis` exists (`embodiment/audio_localization.py`:692) and writes "any declared **root** sensor", so
    OD-C10's ask for sub-sensors is real.
  - `simulation/dm_runtime.py` has no `AgentFactory` reference, so the earlier item 5 holds.
- **N-5.** `npcs_and_sem.md`:561 cites `bootstrap.py:132-141` for `HttpFetchTool`, `InternetSearchTool` and the mode
  switch. Those are at :231 and :259-276, and the internet tools are gated by the launch cap.
- **N-6.** `npcs_and_sem.md` §2.1 says "Maxim's half has no owner in tier A yet: no exit test there varies the world
  step size". OD-WC7 now does. That line is stale.
- **N-7.** The two-time-zone prompt test catches host-local rendering only. A wall date rendered in UTC
  (`%A, %B %d, %Y`) is identical in two processes seconds apart. OD-WC6's "passes when" is scoped correctly, but
  `boundaries.md` §7.3 says the schema and prompt tests "prove" that no time reaches cognition. Say the wall half is
  the tripwire's.
- **N-8.** Δt residue:
  - OD-WC7's "same world span" is unpinned. At Maxim's 30 Hz, a world week is about 18M steps, and accumulated
    rounding approaches 1e-9 on correct code. Pin the span (one world hour, as `npcs_and_sem.md` does).
  - Add an absolute floor for states near zero.
  - Apply inputs only on the coarsest step's boundaries, or discrete gates differ by a step.
- **N-9.** Barrier and dial tests:
  - The barrier test ("a slow agent at 20× must not see a later frame than at 1×") passes on a broken barrier if the
    agent's delay is shorter than one 20× tick. Pin the delay above a 1× tick, and drive it with the fake wall.
  - OD-EA5 uses "a seeded random wall delay", which means real sleeps. Overdrive's own version uses a fake wall.
    Align them.
- **N-10.** The `root_packages` test should list every entry under `src/`: namespace directories without
  `__init__.py`, and top-level modules. An `__init__`-only listing lets an unlisted `src/game/` namespace package
  through.
- **N-11.** World clock §3.2 carries "36 stamps in 19 files", and §3.5 says "plans don't carry volatile counts".
- **N-12.** The SEM plan quotes `AffordanceSchema`'s "additive fields … stay non-breaking" and omits the next
  sentence: "Per CLAUDE.md: 'Do NOT add fields to these frozen dataclasses post-1.0 without a breaking-change plan.'"
  Quote it and answer it with the #403 and #1261 precedents, or a reviewer will.
- **N-13.** The receipt exactly-once test names `applied`, `stale` and `cancelled`, but not `refused_by_world`.
- **N-14.** "Checked through `supports_*` flags like the existing three": there are four
  (`supports_request_context`, `router.py`:1731).
