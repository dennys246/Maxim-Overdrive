# Roadmap (rough draft, 2026-11-15)

Long-term plan for Maxim Overdrive and the Maxim work it depends on. Phases are ordered by dependency, not by date.
Each has an exit test, so it is clear when a phase is done. Phases 2 and 3 can run in parallel.

Status key: **done**, **next**, **later**.

## Phase 0: Foundations (done)

The world server v0: material cells authored in metres, heat conduction, damage, a turn loop, the SEM bridge for
environment regions, imagination specs, and render snapshots (`docs/architecture.md`).

- **Exit (met):** 42 tests pass at the laptop, rig and max profiles. Heat converges at second order against the closed
  form, and crater volume is within 5% of its closed form. Breach and fire outcomes agree across rigs.

## Phase 1: The first visible tile (next)

- A Godot 4 client that only draws and sends intents. It uploads snapshot arrays as 3-D textures for a cell shader,
  and draws fuel objects in a second pass (`docs/design/client_objects.md`).
- A local transport between client and server: a WebSocket carrying JSON intents and binary snapshots (decided
  2026-11-15; `docs/architecture.md`, "Transport").
- The first tile authored in metres: the alley. When the ripperdoc clinic is authored is D27's
  (`docs/design/decisions/world_model.md`).
- Save format v0: the world grid plus the scene spec. Agent homes join in Phase 4.
- The engine and game boundaries, before the verification harness: `phase1/boundaries` (structure) and
  `phase1/gates` (behaviour) (`docs/design/boundaries.md` §11).
- The agent foundations, after the clock and before the lanes: `phase1/agents` (`docs/design/boundaries.md` §11.1,
  `docs/design/npcs_and_sem.md` §6.2). Phase 1 has no NPCs; real Maxim stays a strict red gate until it ships the
  embeddable agent contract.
- Review the content-identity proposal (`docs/design/ip_and_licensing.md` §6: content-addressed spec ids, a
  provenance and licence record per placement) before the intent-log header (`docs/design/boundaries.md` §6.3),
  protocol v0 (`docs/design/tile_and_client.md` §3.3) and save v0 freeze. Its design review uses the note's own
  lenses.
- Fires that go out when their fuel is gone, so a burnt-out crate's fire stops instead of heating air to millions of
  degrees (`docs/architecture.md`, Known gaps; the red gate is
  `tests/test_cross_tier.py::test_a_fire_that_has_burned_its_fuel_stops_heating`). Needed before the Phase 1 exit
  (the slab) is gated. **Requirement:** fuel burns as sub-grid objects with geometry in metres, coupled to the cells
  by overlap (`docs/design/fire_model.md` §0, point 3; `docs/design/fire_solid.md` §1), well enough at the coarsest
  rig to pass the gate. Converging is not enough: today's law converges, slowly,
  and the coarse rig still sits far off, because the measured cause is a threshold on a cell's mean temperature
  (the crate's mean temperature agrees across rigs within 1 °C while the degradation driver differs 1.3–1.5×). A
  per-cell ignition or pyrolysis threshold would inherit it. It must flip the strict
  red gate `tests/test_act_validation.py::test_the_fiercest_allowed_fire_has_the_same_outcome_at_every_rig_on_every_turn`,
  and it removes the marked band-aid in `data/world/actions.yaml`, whose ceilings keep fires at the powers the
  current physics has been measured at.
- The write window's two owners until `Simulation.step` owns it, marked band-aids (`docs/design/boundaries.md` §4.1,
  2c): `World.advance` in `src/simcore/core/world.py` and the intent applier in `src/simcore/core/applier.py` open the
  window themselves; step 5a's PR 4 moves both into the step (PR 2 moved the laws into the tuple, not the window), and
  with it a strike becomes a `Load` the applier appends. `World._power_field` in the same `world.py` holds the
  sources' deposit (sorted and cached since PR 3, `src/simcore/core/deposit.py`) until PR 4 hands the sources to
  heat's `prepare` (`docs/design/sim_core.md` §7). The shell's
  interim `Simulation(world)` seam in `src/simcore/core/simulation.py` goes in PR 4, when `Simulation` carries the
  per-tick digest its strangler tests compare. A third, `place` in
  `src/simcore/core/imagination.py`, opens it because the `imagine` intent kind doesn't exist yet; step 5a's intent
  log, where every input joins one pipeline, makes it the applier's stage 2 of that kind.
- The SEM membrane applies synchronously with no log, a marked band-aid in `src/simcore/adapters/sem/bridge.py`
  (`docs/design/boundaries.md` §6.4): `phase1/agents` makes `execute` only parse, check the bound actor and append
  the intent to the stepping agent's outbox.
- **Exit (the fire fallback, owner, 2026-11-20):** walk into the alley, light a slab with the torch, and watch it
  char, burn and flame out. It must look the same, apart from detail, at the laptop and rig profiles. The crate moves
  to Phase 2 (`docs/design/research/solid_spike/results_rerun1.md` §7).

## Phase 2: Physics breadth (later; in parallel with Phase 3)

Each new field ships with a closed-form test and a cross-grid test, under the verification rule.

- **Sound:** a propagation field feeding Maxim's audio localization (`world_set_axis`).
- **Light and visibility:** what an agent can see, and the light the shaders draw.
- **Gas and radiation:** smoke, toxins and Fallout-style rads, as diffusion plus sources.
- **Convection:** an approximation so rooms heat realistically and fires don't have to sit on a material.
- **Structural support:** cells left unsupported fall as debris.
- **Load and moving bodies** (owner, 2026-11-22, D31, D32): objects bear load and fail under it, and intact objects
  move as physical bodies if that can be done honestly. Research first, in the Structure and motion entry of
  `docs/plans/long_term_features.md`. Imagined objects meet the support rule when placed (D33).
- **Scale:** move the hot loops to numba or C if profiling says so (never coarser far cells: world_model D21).
- **Close the known gap:** the coarsest rig's late-burn lag (`docs/architecture.md`).
- **Moved from Phase 1 by the fire fallback (2026-11-20; after VS5):** crate and rungs 6.2–6.4 (flame object,
  two bodies, crib).
- **Moved from Phase 1 by D26:** zones and vents, combustion per zone and its products, phase change other than
  fusion, and the CSG footprints. Pyrolysis, the fuel's regression, fusion and the lab (as the ladder's rigs) came
  back to Phase 1 with the fire ladder (`docs/design/fire_model.md` §10.1; `docs/design/fire_solid.md` §4.2–§4.3).
- **Plasma, slowly, aiming at plasma as a state of matter** (owner, 2026-11-19). The reason is what Maxim's NPCs can
  sense, learn and use from environmental effects:
  - an arc is a flash in the light field, a crackle in the sound field and ozone in the gas field;
  - its electromagnetic interference touches cyberware sensors.

  In order, each step a law in step 5a's list and a field in the registry:
  1. **Plasma effects:** plasma cutters, weapons and welders as very hot, bright sources. This step needs the light
     field.
  2. **Electric fields and arcs:** a potential field solved locally around active charges, conductivity per material,
     and breakdown as a band-gated binary outcome. The breakdown is evaluated on the reconstructed field at sharp
     features, never on a cell mean (D25), with stochastic channels drawn from the world's seeded RNG.
  3. **Ionised gas:** an ionisation fraction (Saha), conductivity and radiative cooling, coupled to gas and zones.
     This step needs both.

  Out of scope for good: first-principles plasma physics (magnetohydrodynamics, particle-in-cell). Its scales are
  about 10⁵ finer and 10⁸ faster than the grid, and no player could perceive it.

## Phase 3: Maxim upstream, in three tiers (later; in Maxim, through its own process)

These go to the Maxim repo, each through Maxim's own process:
- **an issue** for a discrete defect;
- **a plan** for engineering work, with a three-lens plan review and a code review per PR, but no pre-registration
  and no ledger row;
- **for an experiment only:** a four-lens design review, a pre-registration frozen before data, and a ledger row.

None is patched here. The drafts, their index and the split into issues and plans are in `docs/maxim_upstream/README.md`,
first read against Maxim `origin/main` `7084f561` (2026-11-16); tier A and the issues re-checked on `6fee7377` (2026-11-17), the agent rows on `f0b1cea4` (2026-11-19).

**Owner decisions (2026-11-16):**
- **SEM refinement is a priority** of Overdrive's foundations work, which runs in parallel with Maxim. That includes
  types Maxim marks shape-frozen, as long as changes stay bio-faithful and go through Maxim's process. Under Maxim's
  CC3 text, a trailing defaulted field is additive, so no major version is proposed.
- **O6: tier A's core is an embeddable agent, one that a host drives.** The host calls it with world time and a
  frame. It returns intents, memory writes and thought requests as values, never calls a model itself (it returns
  requests, which the host's thinking lane runs; O6a), uses only declared tools, and keeps state only in a home the host names.
  - Overdrive builds no interim mode in which Maxim's agent runs its own loop beside the world.
  - **Phase 4's NPCs wait for tier A's named subset (O29),** plus OD-B1 to OD-B7 for Exp 64a.
- **After Maxim's answers (2026-11-17, `docs/design/reviews/maxim_response_1/`):** Maxim has no inner tool loop, so
  `think` is host-called and resumable and the host executes its model requests (O6a), through gateways
  (`inference_gateway.md` §2). The engineering seams are accepted on engineering grounds behind parity guards, and
  the stepped `think` lands **after Maxim's 1.4.0 cut** with the agent-loop decomposition slices (O15a), so Phase 4's
  real NPCs wait for that too. Maxim's design session will write a ranked candidates doc that re-checks every
  citation on a fresh `origin/main`; the rows below are proposals until it lands.

Both decisions are recorded in Overdrive. The Maxim-side record is proposed in
`docs/maxim_upstream/decisions_entry_DRAFT.md`.

**Ids** carry an `OD-` prefix, because Maxim already uses `A1`/`A2`, `B1`–`B4`, `T1`/`T2`, `E1`–`E3` and `S0`–`S6`.
"Was" gives the id in this roadmap at 35b9c3e, or the older number where that is what documents cite.
**Additive first, in 1.x:** under Maxim's own reading of CC3 (`AffordanceSchema`'s marker, `sem.py:113-116`),
appending a field with a default is non-breaking (precedents: `always_active` #403, `speech_param` #1261), and a
rename follows the alias-plus-deprecation precedent. Only `Modulator.execute`'s signature is a real break, and it can
be opt-in (from `boundaries.md` §9.3).

### Issues now

| Id | Item | Was |
|---|---|---|
| OD-I1 | `x or time.time()` turns a world time of 0.0 into the wall clock, at five sites: `attention/salience_map.py:227`, `salience/salience_network.py:222`, `models/language/cost_tracker.py:376`, `:469`, `:480` | A9; filed by Maxim as #1684 |
| OD-I2 | `embodiment/sem.py::ModulatorResult` has no CC3 declaration. Downgraded to a docstring nit: it is an in-process return value, never persisted or sent (Maxim's answer) | C7 (half), P6 |
| OD-I3 | The only pickle-capable load in `src`: `MemoryHub._restore_on_open` → `EmbeddingStore.load` → `np.load(allow_pickle=True)` on the global `~/.maxim/util/semantic_embeddings.npz`; dormant unless `enable_semantic`, and must land before `AgentHome` (OD-A12) makes it reachable from saves | OD-A13; filed by Maxim as #1685 |
| OD-I4 | `ARCHITECTURE.md:182` is stale: the DM runtime doesn't build NPCs through `AgentFactory` (`create_npc_agent` has no caller) | new (Maxim's answer); filed by Maxim as #1686 |
| OD-I5 | A security issue in cloud redaction, held by Maxim as a private advisory; details in private notes, not here | new (TBR-11) |
| OD-I6 | pymaxim pins `rich>=13.0.0,<14.0` (`pyproject.toml` on Maxim `origin/main` 10888fec), and every embedder inherits it: Overdrive's import contracts can't use import-linter 2.7+ (which needs `rich>=14.2`) and stay on 2.6 / grimp 3.13 (step 3a, 2026-11-19). Ask: lift or widen the cap, or say why it's needed. Searched Maxim's `docs/plans/` for `rich`: nothing found | new (step 3a) |
| OD-I7 | `ModulatorSpec.apply_damage` (`embodiment/spec.py:1034-1036` at `043eab8f`) returns 1.0 and applies nothing on a modulator with no sub-sensors, with no log or error: a flat body's burn changes nothing (`sem_stimuli.md` delta 1, Bio-faithful SF-2) | new; sent to Maxim's session for 1.3.4 triage, 2026-11-21 |
| OD-I8 | `Embodiment.evaluate_failures` takes drive drift from `time.time()` (`embodiment/body.py`, about `:293` at `043eab8f`); `world_clock_release_DRAFT.md` names `last_fired` in the same function, not this read. A question to route to #1361's plans, not a fix | new; sent with OD-I7, 2026-11-21 |
| OD-I9 | **Pushback** against `plans/archive/llm_path_fast_failover.md:43` and `:769` (cloud retries by design) and `docs/architecture/llm_routing.md`'s empty-content legacy path, which breaks Maxim's own rule at `:771` ("Backend failures raise typed exceptions, not return empty content"): the cloud backends turn almost every failure into `LLMResponse(content="")` (`anthropic_backend.py:377`, `:384-409`; `openai_backend.py:358-360`, `:505` at `043eab8f`), retry inside the call (`max_retries`, `capacity_max_retries`, 4 hard-coded gateway retries at `openai_backend.py:391`, and the SDK clients' own, `:450`), and drop cache-write tokens from `LLMResponse` (`anthropic_backend.py:416-422`). Ask: typed `BackendError`s, configurable retry budgets with defaults unchanged, complete usage counts, so a host gets one call, one outcome and can tell load from failure (`inference_placement.md` §1.3, §2.7, §9). Not in O29's subset | new (2026-11-21) |
| OD-I10 | **Question** to Maxim's 2026-09-28 decision that "the proxy wins for operator paths" (`DECISIONS.md:1150-1192`, `utils/http.py:830`): Overdrive's gateways set `NO_PROXY=*`, which stops httpx's environment lookup from mounting any proxy and urllib's from consulting macOS System Settings (verified with httpx 0.28.1; `inference_gateway.md` §2). Ask: keep that honoured on the backends' path, since it rests on httpx's private `get_environment_proxies` (`DECISIONS.md:1188`), and expose `HTTPEndpoint.strict_address_check` (`utils/http.py:228`, `:875-881`) to backend callers. Not in O29's subset | new (2026-11-21) |
| OD-I11 | A blocked `base_url` can fail open to the cloud, because the refusal is keyed on the provider's **name**, not its **type**. `_OpenAIBackend._get_base_url` (`models/language/openai_backend.py:231-243` at `b98954f7`) warns "Blocked base_url … (SSRF protection)" and returns `None`. `_ensure_client` (`:273-275`) refuses only when `self._provider_key` is `openai_compatible` or `openai_compat`, while the router dispatches on the provider's type (`router.py:467-474`). So a provider of type `openai` (or `openai_compatible` under any other key) with a blocked URL builds a client with no base URL, and the OpenAI SDK takes `OPENAI_BASE_URL` or its default, api.openai.com. Run on pymaxim 1.3.4, 2026-11-22: a provider keyed `local`, type `openai`, pointing at a loopback llama-server, sent its prompt to api.openai.com, refused 401 (lesson 36). Searched Maxim's issues ("SSRF base_url fallback", "Blocked base_url"): nothing found. The fix is to refuse on the type, so a local-first game's NPC prompt can't leave the machine on one misconfiguration | new (2026-11-22) |
| OD-I12 | **Question** to the deferred `plans/deferred/vllm_self_hosted_servers.md`, which calls `chat_template_kwargs` a "vLLM-only payload field" justified only by a dedicated backend (`:62`) and treats thinking as a parsing problem: `--reasoning-parser` keeps `<think>` text out of `content` (`:155-156`), but nothing bounds the tokens it spends. llama-server takes the same field. Run on pymaxim 1.3.4, 2026-11-22: `_OpenAIBackend` against llama-server (`--jinja`, build 10621) serving Qwen3.5 4B returned empty content, 512 of 512 tokens, `stop_reason` `length`: the template's thinking went to `reasoning_content` and spent the whole budget. Nothing in the backend can switch it off (`enable_thinking`, or Ollama's `think`). Does a reasoning model on a self-hosted lane need a per-provider thinking switch, and does this meet the plan's revive trigger? Searched issues ("thinking reasoning local qwen"): nothing found | new (2026-11-22) |
| OD-I13 | **Ask:** seeds and samplers on Maxim's backends. `backend_protocol.py::complete_with_usage` (at `origin/main` 16aaf664) takes `temperature`, `stop` and `thinking`, with no seed, top-p, top-k, `min_p`, `repeat_penalty` or response format, which IP §1.3 F6 records and the generation harness needs to run through the gateway (`generation_harness.md` §4). Searched `docs/plans` for "seed" with backend and sampling terms: archived plans only, nothing live. Until it lands, the harness keeps its own marked client | new (2026-11-22) |

### Tier A: an agent a host drives (Phase 4 waits on a named subset)

**The subset Phase 4's first NPC needs (O29):** OD-A1 (only #1361 S3a, S3b and S4), OD-A2 to OD-A11, OD-A12's
host-driven ConceptExtractor thread, OD-A14 to OD-A18, and OD-A20 (needed, declined: Phase 4's replay exit carries a
known divergence, `npcs_and_sem.md` §12.2), with the issues OD-I1 and OD-I3. Each is needed for host stepping, world
time only, bit-identical replay, one intent door or the single-player worker boundary, through OD-WC1, OD-EA4,
OD-EA5, OD-EA7 (Maxim's `1263.thread-guard`, configured), OD-EA10 to OD-EA12 and OD-EA14 to OD-EA16, or by O30
(OD-A16). **OD-A18's invocation pid depends on an unbuilt Maxim stage:** `PhysicalEventId` and the per-agent
`EventSequencer` come from Maxim's autonomic plan, post-fence resume stage (G17), not in `src` at 95af47d2 (nor at
c28b2681). Until it lands, our intent record's `invocation` field is reserved and unfilled, as `boundaries.md` §6.2
says (`checklists.md` step 5b). **OD-EA12 is ours** (Maxim's owner, 2026-11-19: #1361 does not widen G2b, which checks one trace against
its anchor at two poll rates): an Overdrive-side test against S3b, written in this phase once S3b ships and run
again on Phase 4's first real NPC. Exp 64a also
needs OD-B1 to OD-B7. Not blocking: #1361 S5 and S6, and OD-A21. OD-A12's store routing waits for two agents in one
process. So the subset is most of tier A, and its long pole, OD-A15, stays.

**Timing, from Maxim (2026-11-19, `reviews/maxim_response_1/response_4.md`; a planning range, not a commitment):**
1.4.0 earliest February 2027, planned March to May 2027, after 1.3.4 to 1.3.6 and 1.4.0's release gates (#1305's
owned RNG; cand. A2's per-agent key is a new gate item after the cut, Maxim's owner, 2026-11-19). The stepped `think` (cand. B1) comes after 1.4.0, in the 1.5 hybrid line's `src`
phase, with no range yet, so Phase 4's first real NPC is after mid-2027 at the earliest. Maxim accepted the world-seam
front gate (the case for a host-driven runtime mode) and reviewed `embeddable_agent_DRAFT.md` v3 (SOUND WITH
CONDITIONS, `docs/design/reviews/agent_draft_v3/maxim_review.md`); v4 folds it (O38–O40), v5 folds its delta
review of v4 (SOUND WITH CONDITIONS, `maxim_delta_review.md` beside it), v6 its review of v5 (SOUND WITH
CONDITIONS, `maxim_review_v5.md`: the pid's owners and dependency, the settle invariant, O43), and v7 its review of
v6 (SOUND, `maxim_review_v6.md`: a log segment per restore, O45; a refusal's pid in no GL3.B2 row).

**Maxim `src/` before 1.4.0 (Maxim's plan review, under its M89):** the draft's build steps 1–4 may land before the
cut, on two conditions: cand. A4's entry point exposes no `think`, `Pending` or continuation before the cut, and the
draft's basis and staleness stay out of B2. A2's per-agent key before the cut would be a new gate item, Maxim's owner
call; its owner put it after the cut (2026-11-19).

Drafts:
- `world_clock_release_DRAFT.md`: two plans. **A-pre** goes on its own clock, touching no fenced file. **A-post**
  lands with Maxim's 1.3.6, Session A.
- `default_network_stepped_DRAFT.md`.
- `embeddable_agent_DRAFT.md`.
- `propose_settle_amendment_DRAFT.md`, an amendment to Maxim's `tool_failure_credit.md`.

| Id | Item | Plan | Was |
|---|---|---|---|
| OD-A1 | #1361's S3–S6: a dependency, not duplicated. S3–S6 are in 1.3.6; S2 coordinates with Session V; S0 and S1 shipped. | — | A1 |
| OD-A2 | `AgentTime`, split in two (with a **static** AST ban on `time.*` and `datetime.now` in Maxim's step-path set and a long-horizon scripted run, since dynamic plants miss consolidation, sleep and decay paths; BD-14.2): a **machinery clock** (epoch seconds as today, microseconds; decay, cadences and stamps) and a **perceived-time port**, the only time a prompt may contain. For robots the machinery clock is Maxim's `ExperienceClockDriver` (cand. A3), and the static ban extends M72 rather than adding a second lint. Keyed RNG substreams and `IdSource`. Host defaults read at call time, so `_StepClock` still works. Tests: a planted wall-clock read under an advancing fake clock, and a **planted-render test** (a sentinel in the machinery clock, TZ pinned, checked in raw, clock and date forms; an origin offset end to end; offset and scale only at render level on a frozen store, since a scaled clock legitimately changes decay). | A-pre | A2 |
| OD-A3 | Prompt and observation time only through the perceived-time port, or omitted, with a lint banning `datetime.now`, `strftime` and `localtime` in prompt-reaching modules. Covers `prompt_builder`'s datetime and identity sections (`:229`, `:1122-1124`), `llm_fallback`'s canned answers and `context_pool`'s `[HH:MM:SS]` stamps (`:468`, `:493`). | A-pre | A6 |
| OD-A4 | Live-path stamps outside the fence, passed explicitly with defaults kept; `SensorReading` stamping; a tool's duration supplied by the host in world time, not `runtime/tool_dispatch.py:1419`'s wall clock (`_observe_energy_cost`, `:695`, books NEGATIVE NAc valence above 2.0 s); Maxim agrees it is the root fix | A-pre | A5 (part) |
| OD-A5 | The hippocampus's 30 s wall window, attention and salience stamps, and `TemporalSignature`'s phase source | A-pre | A5 (part), A7 (source half) |
| OD-A6 | Reaction and pain dispatch gates on the injected clock under embedding. Motor and IO limits stay on the wall. Lands after #1200. | A-pre | A8 |
| OD-A7 | Randomness and ids outside the fence: keyed substreams by Maxim's `utils/seeding.py::make_agent_rng(base_seed, agent_id)` with a stream argument, derived as `npcs_and_sem.md` §3.4 says (O40); a new release-gate item after the 1.4.0 cut, not a widened `1305.owned-rng` (Maxim's owner, 2026-11-19); `semantic.py:205`'s `or 42` made an explicit seed; `seed_all` never called on the embedded path; `time.time_ns()` event ids (`decisions/nac.py:1163`) | A-pre | A5 (part) |
| OD-A8 | Fenced ids and stamps (`agent_loop`, `orchestrator`, `tool_dispatch`), NAc stamps and anchors, and `FailureMode.last_fired` (with S4) | A-post | A5 (rest), C8 (half) |
| OD-A9 | `DefaultNetwork.step(now)`, with the thread a caller of it, coordinated with #1263's remainder | A-post | A3 |
| OD-A10 | The embedded entry point on `AgentFactory`, every collaborator required; the DM runtime builds NPCs through it | embeddable | A10 |
| OD-A11 | A closed tool roster for embedded agents, sealed with the advisor's patterns, refused at construction, with no workspace manifest. Engineering, on its own clock; making capability rosters the robot default stays experiment-gated | embeddable | new (TB2-B1) |
| OD-A12 | `AgentHome`: one per-agent object over `AgentFactory`'s `persistence_dir`, routing the ten still-global store families; the ConceptExtractor thread made host-driven, which belongs to cand. A4's closure through `build_memory_hub(start_background_workers=False)` (`runtime/bio_stack.py:489`, `:654`), not A1 | embeddable | new (TB2-B2) |
| OD-A13 | *Moved to OD-I3*, an issue now | — | new (TB2-B2) |
| OD-A14 | The request/reply cut: the request as a value (rendered text, sampling, the caller's declared function name, never a hardware-resolved tier: a new field, since no call site declares one today (`submit_function` and `get_backend_for_function` have no callers, `_complete_text` takes no function), so B1 tags each call site it lists; deadline field, `tools is None`), produced at `LLMRouter._complete_text` without building an `LLMRouter` in the embedded agent, with the host supplying the function's envelope (`total_budget`, `response_reserve`, a pure `token_counter`, `thinking`) to the `PromptBudgeter` (`inference_placement.md` §2.1), and asking B1 to render stable text in `system` and volatile text in `user` so prompt caches hit (Maxim's `docs/lessons/sim-n-ctx-config-drift.md`); the reply with reserved `cancelled(prefix)` and `truncated` variants that bypass the parse-failure template, and speech as a field emitted first. Not an `LLMBackend` capability | embeddable | new (DR-B2, Arch B3); was "streaming and cancellation on `LLMBackend`" |
| OD-A15 | The stepped `think` on §A.1b's seam, one design for the submit path (OD-A14, OD-H6 and the cancelled-reply bypass land as parts of it): a continuation split into a host-owned header and an agent-owned body, with `basis_seq` (the agent's afferent-scheduler high-water seq, `thalamic_relay.md::preempted_since`; the host holds a copy, never computes it; LLM-proposal staleness waits on GL3.B7) and staleness per hybrid §A.1b.5 (O38); writes only as returned values, retrieval strengthening included; multi-call PFC cycles, `next_actions`; the robot path drives the same `think` (robot parity: OD-EA14); isolation between agents in one process. Lands after the 1.4.0 cut with the agent-loop decomposition slices | embeddable | A4 |
| OD-A16 | Credit for effects measured later: receipts, the cerebellum observing at settle, exactly-once credit, `stale`, `call_error` and `wrong_target` kinds, a per-modulator valence default. Evidence from step 3b(b): `ModulatorResult` has no kind, so a SEM refusal's `error_kind` is `None`; the pain detector books it as an external failure (`executor.py:789`) and the replan path prompts "Failure type: None" (`loop_state.py:248`) (`docs/lessons_maxim_in_games.md` §31). Rides on OD-A18 | amendment | C1, C2, P2, P3, P7 |
| OD-A17 | The embedded-path leak closure: prefetch off and the working directory at the agent home; the short-question shortcut is deleted in Maxim for everyone, matcher and fallback (#1689, PR #1694; after #1691 a fallback reply books no NAc credit, but `generate_llm_fallback` still echoes `triggering_input`); no `force=True` logging; paths under the agent home; a static import ban on `utils/audit.py` with `lint_dead_imports`' resolver (blind spot: `importlib` strings), naming `maxim.embodied_runtime`, the internet tools, `build_tool_registry`'s module and `runtime.prefetch`, plus the advisor's three closure tests; no env reads (A4 waits for A1, no `MAXIM_DATA_HOME` exception); no reply reaches the parse-failure template (it echoes the input; its bypass lands with cand. B1, as OD-A15's cancelled-reply bypass); no model backend in the embedded agent, so the model calls outside `think` (`AdaptivePlanner`, the `ToolPainBridge` reflection, `FearAgent`) fail closed | embeddable | new (Maxim's second answer; TBR-3, TBR-7) |
| OD-A18 | Split `execute_and_learn` into dispatch and settle, folding in the parallel and agent-fallback side doors; generate vs apply for memory writes (cand. A6: applied at settle, published through the agent bus; O39), D53 `outcome_valence` and OD-A16's keys; settle feeds NAc's existing traces; memory writes carry provenance by source actor; each dispatched intent carries its invocation pid, and the host stamps it on every receipt and frame event the intent causes (the embedded efference copy, GL3.B2's join). B2 owns the call site (its dispatch is the `Executor._run_started` equivalent, drawing from the agent's own `EventSequencer` inside the worker and putting the pid on the intent value), the sequencer owns the mint, GL3.B2 the contract; the host's side of the pid is `npcs_and_sem.md` §6.6's. The pid waits on G17 (above). The settle invariant (OD-EA16): each minted pid comes back in exactly one terminal receipt, executed or a typed refusal; no receipt arrives without a minted pid; refusal receipts count as the pid's outcome, not a physical event, and a refusal's pid never appears in a GL3.B2 row (Maxim's review of v6); the host's refusals, deferrals past a budget and drops all end in one; when a worker dies, the host writes a typed `agent_failed` refusal receipt for every in-flight pid (O44). `session_id`, log segments and the sequencer's high-water seq are `npcs_and_sem.md` §6.6's (O43, O45; Maxim's Q1 alternative, so nothing is asked of its resume stage); GL3.B2's gate holds unchanged (Maxim's Q2 answer); robots settle right after dispatch (OD-EA15); `environment.step` (`tool_dispatch.py:1574`): our position is Maxim's suggestion, that the embedded roster passes no environment and the follow-up arrives in receipts (B2's call). After #1361 S3a and S3b and cand. A3 A-post, behind a bit-identical state-digest parity guard | embeddable | C1 (generate vs apply) |
| OD-A19 | *Withdrawn 2026-11-17:* it duplicated Maxim's own `docs/plans/experience_clock_decay.md` (#1361 S3a), which we already track as OD-A1; the temporal-anchor fallback's age and expiry move in #1361 S3b, and its similarity's host-calendar read (`nac.py:3629`) is OD-A20. Was: Step-size-invariant decay: NAc's eligibility traces decay ×0.9 per loop tick today (`decisions/nac.py:3707`, from `_loop_bio_tick_maintenance`, `runtime/agent_loop.py:800-840`, with five sibling decays), so credit depends on the tick rate; decay as `exp(−Δt/τ)` on the machinery clock, with an exit test crediting one delayed receipt equally at two rate divisors (OD-EA12). Argues against the per-tick decay contract; corrects Overdrive's earlier claim that the traces decay on the wall clock (`correction_1.md`) | A-post | new (npcs_v3 BF3-1) |
| OD-A20 | *Declined by Maxim's owner 2026-11-19 (noted, not adopted):* event similarity stays on the host calendar, and events and anchors age on the experience clock; kept as a known divergence, recorded from Maxim's code and our arithmetic, not from a run; two strict red gates will carry the evidence once the agent PR lands them (`npcs_and_sem.md` §12.2, `checklists.md`). Maxim's delta review widened it, correcting our v4 text, which said the calendar moves only how credit is shared: (a) it can drop an anchor below the 0.01 threshold (`0.3 × similarity × activation`), so a receipt whose only node drops books nothing; (b) anchors set at different host times split differently; (c) `TemporalSignature.from_timestamp` uses local time, so the replay machine's timezone and DST move credit, a cross-machine effect. No pinned `TZ` in production. Our v3 lean put the read on the machinery side; that was wrong, since SCN features reach the model through `temporal_patterns` and `[TEMPORAL]`. Was: Anchor similarity off the host calendar for embedders: after #1361 S3b, `TemporalSignature.now()` (`nac.py:3629`) still scores anchor similarity on host time of day ("host calendar by design", #1361 §(c), §(g)), so a replay at another hour credits differently and an NPC's learning depends on the player's clock. Read it from the perceived-time port. Maxim said it will raise this as a question on #1361 (`response_3.md`); #1361's plan still reads "host calendar by design" in §(g). Our evidence is in `erratum_1.md` | A-post | #1361 question |
| OD-A21 | τ_elig from the striatal window, an argument against #1361's decided Q1 (2026-10-17: "taus in world-seconds, anchored on Exp 30's fixture regime; tune the turn quantum, never per-runtime taus"; 4.75 s at any rate after S3a): NAc's dopamine eligibility window is about 0.3–2 s (Yagishita et al. 2014); longer delays belong to the anchor path, which is why OD-A20 matters. An owner decision with its own experiment in Maxim, not a doc edit; S3a records the rationale first | A-post | #1361 Q1 |
| OD-A22 | How a publish between cognition passes is keyed (`sem_stimuli.md` M4, which absorbs M16): a host's `evaluate_failures()` between passes, on the injected clock, joined to the situation it occurred in, not the last cluster stash. A question to `autonomic_layer.md` §3.1.4's out-of-band producer (G9; `CauseRef.cause_pid`, `drain_outcomes()`) and #1176 for the in-pass half; GL3.B0's census is evidence. **Future bar:** T16c (`xfail(strict=True)`), triggered when G9's producer lands; its world-side test, T16b, passes now | embeddable | M4 (2026-11-21) |
| OD-A23 | A question to cand. B1's cancel clause ("ride on `utils/cancellation` plus `LLMRouter._complete_text_abandonable`"): does the abandonable path free the transport, or only the caller? Not a backend capability (OD-A14). Overdrive bounds a call by killing its placement's gateway meanwhile (`inference_placement.md` §2.5). Not in O29's subset | embeddable | new (2026-11-21) |
| OD-A24 | **Pushback** against `docs/agents/llm-routing.md`'s invariant that placement "rides on `LLMRouter`'s existing `provider_priority`/`_try_provider` failover — NOT a new resolver" (from `plans/archive/lane_capability_placement_split.md`): an embedder that owns deadlines, slots, consent and spend resolves placement outside `LLMRouter` and calls one backend per dispatch, so the multi-call hazard can't arise. Evidence: `inference_placement.md` §1.2, §2.5 (O46, O52). Not in O29's subset | embeddable | new (2026-11-21) |
| OD-A25 | **Question** to cand. B1, whose reply type plans "the token iterator … later" (`overdrive_refactor_candidates.md:268-270`): when, and at which layer? Every backend collects a stream and returns one `LLMResponse` today (`anthropic_backend.py:473-480`, `openai_backend.py:547-559`, `maxim_peer_backend.py:987` at `043eab8f`). A chunk sink on `complete_with_usage` would lift O50 (no first-token streaming for NPC speech; `inference_placement.md` §6.3) | embeddable | new (2026-11-21) |

### Tier B: the 1.4 line (NPCs that remember, and a coarse sense of time, earned by experiment)

Each mechanism enters Maxim as `[engineering]`, and earns `[behavioral]` only through a pre-registered experiment run
as a Maxim cradle, with BF2's `tabular_q` and `random` floors. Draft for the time items: `time_sense_DRAFT.md`.
OD-B1 to OD-B7 are also Exp 64's prerequisites.

| Id | Item | Was |
|---|---|---|
| OD-B1 | NPC replies recall memory: `runtime/agent_pool.py::_generate_llm_response` never reads the hippocampus | B1 (1) |
| OD-B2 | A persona hook in the full loop: `agents/prompt_builder.py` hard-codes "You are Maxim, a robot assistant." | B2 (2) |
| OD-B3 | A seed-memory API: backdated `experience_us`, salience taken from the event | B3 (3) |
| OD-B4 | Bus messages reach the receiver's memory (`AgentPool._handle_message` only logs them) | B4 (4) |
| OD-B5 | Save affordance effects (#1159: `to_dict` drops `params`, `requires`, `self_effect` and `target_effect`) | B5 (6) |
| OD-B6 | The arc YAML loader keeps `act`, `world_entities` and `mother_scaffold` | B6 (8) |
| OD-B7 | An install-augment API: attach a modulator and regenerate its tools in one call | B7 (9) |
| OD-B8 | The oscillator steps by elapsed time, and light entrains the circadian scale. Opt-in until earned (OD-X1). Argued against the bio-roadmap's SCN gate and ANALOG row, by name. | A7 (oscillator half), B8 |
| OD-B9 | Coarse time for cognition: interim bins now for embedders, later the oscillator's and interval sense's estimates | B9 |
| OD-B10 | An interval sense: scalar noise, retrospective duration from salient events (OD-X2) | B10 |
| OD-B11 | Consolidation without ending the session, on experience time, with idle replay | B11 (14) |
| OD-B12 | A mental-fatigue drive that rises with deliberation load (not a depleting reserve), and the ask that `CouplingSpec`'s threshold step can't carry it (OD-X2) | C5 |
| OD-B13 | The weekly, monthly and annual oscillator scales are cue-driven or off for embedders, never read from a calendar | new (BF2-7) |

Experiments (drafts in `time_sense_DRAFT.md`):
- **OD-X1:** does an entrained clock carry what an exact one does?
- **OD-X2:** does state-dependent timing change what is learned?

They were T1 and T2, which collided with Maxim's 1.4.0 release thresholds.

### Tier C: SEM additive after tier A, and the hybrid line

Drafts: `sem_breaking_change_plan_DRAFT.md` (now an additive refinement plan; the file keeps its name) and
`hybrid_1_5_line_DRAFT.md` (now Overdrive's contribution to Maxim's own hybrid arbitration line, `DECISIONS.md`
2026-11-11, whose rule is no `src/` before 1.4.0).

| Id | Item | Was |
|---|---|---|
| OD-C1 | Drive drift states its time base (docstrings and a test; optional rename with an alias) | SEM S1 |
| OD-C2 | `SensorReading.timestamp` is the body's clock, never rendered in a prompt | SEM S2 |
| OD-C3 | `acts_on: str = "by"` on `AffordanceSchema`, a trailing defaulted field | C3, P1 |
| OD-C4 | The acting entity reaches `execute`, opt-in through `accepts_actor` | C4 |
| OD-C5 | `ModulatorResult.settles`, a trailing defaulted field, after OD-I2 | C1 (pending half) |
| OD-C6 | Reserved membrane keys: a metadata key can't overwrite `success` in the tool output | new (BF-10) |
| OD-C7 | `ModulatorResult` and `SensorReading` must not be mutated (documented and tested; freezing deferred) | new (deep-freeze) |
| OD-C8 | Percepts and instruments, shrunk: instruments are in-world objects perceived through an existing `modality:` | C6 |
| OD-C9 | A written version rule for the SEM vocabulary, on the existing `ENTITY_FORMAT_VERSION` | C7 (half) |
| OD-C10 | `world_set_axis` for sub-sensors (unverified) | C8 (half), P4 |
| OD-C12 | Thermoregulation's controller in Maxim: effector outputs (skin blood flow, sweat rate, metabolic rate, as `sem_stimuli.md` §3.1 reserves them) and `autonomic_layer.md` §3.3's two-sided need (R-2: heat yields no corrective need). Searched `docs/plans`, `DECISIONS.md` and `src` at `043eab8f` for thermoreg, shiver, sweat, vasoconstrict, vasomotor, perfusion and core_temp: only the `core_temperature` drive. A question to `autonomic_layer.md` §3.3. **Future bar:** T17 (`xfail(strict=True)`), triggered when Maxim drives the effectors; its world-side test, the plant's closed forms, passes once the plant lands | M20 (2026-11-21) |
| OD-H1 | The game as a test bed for the hybrid's questions (OD-HX1 to OD-HX5; HX2 is calibration only) | C11 |
| OD-H2 | Pushback: in an embedded world, the hold's waiting cost uses modelled world-time latency, not observed latency | new (DR-B5, BF2-8) |
| OD-H3 | Re-key the deferred reflex runtime's trigger, argued against owner decision G4 at GL3's start | C10 (cited M76 in error) |
| OD-H4 | *Folded into OD-H5*: deliberation triggered during the other speaker's turn | new (BF2-2) |
| OD-H5 | A turn-taking substrate, as a fifth split-out plan under `hybrid_arbitration.md`: gaze, backchannels, a filler from the predicted delay, an account, then a yield, thresholds as per-world parameters; no claims, structurally; a social cancel source for partner barge-in in `sem_interruptibility.md`. Folds in OD-H4. A paper plan in the 1.5 line; any claim needs a pre-registration (owner decisions OA3, O11a) | new (foundations delta, Bio-faithful; Maxim's answer) |
| OD-H6 | Under a host-called `think` the submit cadence is the host's, so the 0.5 s wall `llm_submit_interval` (`loop_controller.py:154`) needs no change for embedders; it lands inside cand. B1 (OD-A15), not as its own ask, since #1361 §(g) keeps it on the wall for robots on purpose. Triggering deliberation by escalation is the later, experiment-earned change | new (Arch 4.3, BD-18) |

**Retired:** C9 (cancellable SEM actions and deliberation). Mid-action cancel is Maxim's own `sem_interruptibility.md`,
and cancelling a model call is a `cancelled(prefix)` reply under OD-A14.

- **Exit:**
  - Tier A's subset (O29) has shipped, and Overdrive's agent port drives a real Maxim agent bit-identically under the world clock
    (exit tests OD-WC1, OD-EA5, OD-EA10, OD-EA11 and OD-EA12), except for OD-A20's declined divergence, which a
    strict red gate will hold once the agent PR lands it.
  - Every minted invocation pid resolves exactly once (OD-EA16): each comes back in exactly one terminal receipt,
    executed or a typed refusal, including intents the host refused, deferred past a budget or dropped and those in
    flight when a worker died (`agent_failed`, O44); no receipt arrives without a minted pid; a refusal receipt is the
    pid's outcome, not a physical event, and its pid never appears in a GL3.B2 row. A restore opens a new log
    segment, so no new pid equals a logged one (O45).
  - Robot parity holds before either seam is built: OD-EA14 (B1's bit-identical state digest on recorded replies,
    Exp 49 and Exp 60) and OD-EA15 (B2's robot path settles immediately, bit-identical on a fixture of recorded
    replies plus recorded or injected tool durations from Exp 49 and Exp 60; the duration is in the fixture, or
    excluded and named; the digest covers B2's side-effect list).
  - Wall-clock forgetting is held by a strict red gate once the agent PR lands it (recorded from Maxim's code and
    arithmetic, not a run): `Hippocampus.sleep` scores retention on `time.time()`, so what an
    NPC forgets depends on wall time (`npcs_and_sem.md` §12.2). It stays with #1361 Q5 (Maxim, 2026-11-19); no
    workaround here, and Phase 4's replay exit carries it beside OD-A20.
  - OD-A16 has landed before Phase 4: stale's divergence is closed for v1 (owner, 2026-11-22), and `call_error`
    and `wrong_target` still need it.
  - Exp 64a's prerequisites (OD-B1 to OD-B7) are met, and its pre-registration is frozen.
  - The Exp 64 draft is in `docs/maxim_upstream/` and moves to Maxim's `docs/experiments/`.

## Phase 4: Cradles and the first NPCs (later)

- **Retire the generation harness's own inference client** (`TEMPORARY(phase4/inference)`, `generation_harness.md`
  §4) when the gateway path can carry its protocol: IP §4.2's request fields and §2.3's caller without speakers, IG
  §3's engine proof, and the Phase 3 asks OD-I11, OD-I12 and OD-I13. Its file is listed here once the code exists.
- **Starts on tier A's subset** (owner decisions O6, O15a and O29): no real Maxim NPC runs before the subset under
  Phase 3's tier A heading ships (OD-A1's #1361 S3a, S3b and S4; OD-A2 to OD-A11; OD-A12's thread; OD-A14 to OD-A18;
  OD-A20, declined, so the replay exit carries its divergence; the issues OD-I1 and OD-I3), and before Maxim's 1.4.0 cut with the agent-loop decomposition slice that
  carries the stepped `think` (OD-A15). OD-A21, #1361 S5 and S6, and OD-A12's store routing don't block it.
- **Guest sessions with real NPCs (Phase 5 or later, O28) wait for O14's gates,** held by a strict red gate refusing guest joins while
  real-Maxim NPCs are live (owned by `phase1/protocol`), flipped only when each passes:
  - the worker process and its channel gate (`npcs_and_sem.md` §6.6);
  - a no-effect test (no file reads or writes, sockets or spawns outside the agent home);
  - a dialogue-level bypass test driving guest speech through a real worker (prefetch, the parse-failure template,
    phrase commands, which trigger on "maxim", the name of our world, and the shortcut Maxim deleted, #1689, as a
    regression);
  - the guest-text gate refusing line separators and format characters on decoded text;
  - memory provenance with a purge that survives relay and extraction.
  - O18's local model by default, remote only with the guest's informed consent.
  - a cap on connections that haven't sent `hello` (`docs/plans/checklists.md`, step 7's deferrals);
  Deferred by name (O30): a worker OS sandbox, decided before guest sessions open.
- The cradle writer: an arc's fixed event pool plus handcrafted inflection points, assembled per NPC in code.
- Three NPCs on the first tile (the ripperdoc, a fixer, a street kid), each cradled from an authored life.
- A dialogue screen and turn order; movement is substrate-primary (no LLM), speech is the LLM's; no NPC meets fire
  before its body has a pain path (`docs/design/sem_stimuli.md` §4.6's test).
- Save format v1: the world plus each NPC's agent home, including the agent's `EventSequencer` high-water seq, so a
  loaded save continues the sequence; `session_id` is `npcs_and_sem.md` §6.6's (O43, O45).
- **Exit:** Exp 64a runs and its verdict is published, pass or an honest null. If it passes, 64b (the gradient) and
  64c (ordering) follow.

## Phase 5: The player's body and the Overdrive mechanic (later)

- The player's body is an SEM entity with the same body grammar as the NPCs.
- Cyberware is installed and removed at the ripperdoc. Hacking is a `target_effect` on another body's sensors.
- **Overdrive:** forcing an action through a part below its integrity limit, paid for in pain.
- **Action energy and homeostasis** (owner idea, 2026-11-15): what a body can do comes from its energy, not from a
  fixed cap. A bodily action (a strike, a lift) draws on a metabolic store that feeds Maxim's drives (fatigue,
  hunger), so an NPC's own homeostasis steers it away from exhausting itself; Overdrive is spending past it, paid in
  pain. A fire is not powered by the body: the actor supplies a spark, and the power comes from the fuel (the Phase 1
  fuel model). It replaces "refuse or clamp" for NPC requests beyond their means, and it is tested as homeostasis: do
  NPCs regulate, or run themselves into the ground? Until then, `data/world/actions.yaml` holds physics-safety
  ceilings only, and requests past them are refused for every caller.
- Rumour: fear and reputation spread between NPCs through hivemind merges of learned state, never of episodes.
- **Exit:** an NPC who never met the player avoids them because another NPC got hurt.

## Phase 6: Imagination as a generative engine (later)

- In-game imagination, bound to the materials table and a power budget. The world validates every spec before the
  object exists. A generator on the world's side writes the spec, never the agent's imagination (O57), on local
  models first (O58). The research line is the spec generator spike (`docs/design/research/specgen_spike/plan.md`,
  O56). When this phase's design starts, ask Maxim the two questions O57 defers.
- An IP gate in front of `simcore.core.imagination.place`, shipped with the LLM caller that feeds it, never after it
  (design: `docs/design/ip_and_licensing.md` §3, once reviewed).
- Assets are derived deterministically from specs: meshes from cells, procedural impact and burn sounds from
  material properties. Image-model art is cached decoration only and never decides physics.
- **Exit:** a player imagines an object mid-scene, and it burns, breaks, and stands or falls like an authored one, at
  every rig (D33).

## Phase 7: Book to world (later; the pipeline lives in Maxim)

See `docs/book_to_world.md`. Extraction, timeline and the perspective split, then cradles, scene specs and object specs.

- **Exit:** a public-domain book (first candidate: *The Machine Stops*) becomes a tile whose characters remember only
  what they witnessed. Then Denny's novel becomes Maxim Prime.

## Phase 8: Expand and ship (later)

- More tiles and a world map.
- **Steam:** the Steamworks SDK in a private module, a trademark search and filing for the name, and the WashU OTM
  question settled before any store page.
- **A creator marketplace, decided, not assumed.** Once players exist, decide whether to run one, from the costs in
  `docs/design/ip_marketplace.md` §3 (copyright takedowns and the safe harbour a cut puts at risk, EU seller
  verification, payouts through a merchant of record, Steam's rules on purchases and trading, curation, unit
  economics). Nothing for a marketplace is built before that decision; content identity (Phase 1) and the IP gate
  (Phase 6) are needed with or without one.
- **Exit:** a store page.

## Before the repository goes public

The repository was private until Maxim published its fix for OD-I5 (owner, 2026-11-21). It is public again since
2026-11-22 (owner), after the disclosure and Maxim 1.3.4's release. The plan was one branch, `phaseN/go-public`, doing
all of this before visibility flipped. Items 1 and 3 hold (item 3 read from the repository settings on 2026-11-22:
no runners, approval for first-time contributors, read-only default token). Items 2, 4 and 5 are still open:

1. **Disclosure:** Maxim's advisory for OD-I5 is public and its fix released. Until then, stay private; the history is
   not rewritten (the mentions span 202 commits and GitHub keeps PR refs).
2. **CI restored:** `.github/workflows/test.yml` runs Linux and macOS on every pull request again (public repositories
   get free minutes), reversing option B. The pinning test is rewritten as
   `tests/test_check_lock.py::test_linux_and_macos_run_on_githubs_runners_for_every_pull_request_and_the_weekly_drift`
   (PR #48).
3. **No self-hosted runner** is registered (Settings > Actions > Runners lists none), and the repository settings
   require approval for workflow runs from first-time contributors.
4. **Personal paths:** absolute paths under the owner's home in seven files (three spike scripts and four documents,
   found 2026-11-21) become relative or are removed.
5. **Assets and licences:** `ASSETS_LICENSE.md` and the asset manifest (B8) are current.

## Standing rules

The engineering standards (no band-aids, testing, the pre-push review, determinism, formats, budgets, client
rules) live in `CLAUDE.md`, each with the check that enforces it; unenforced ones are rows in
`docs/standards_backlog.md`. The rules below are the design rules.

- **The verification rule:** stated in `docs/design/world_model.md` §1.1.
- Physics parameters are per unit volume. Scenes are authored in metres, never in cells.
- Energy lands by exact cell average or by volume overlap, never by whether the cell centre is inside.
- The world server is authoritative. The client never simulates anything that feeds back into the world.
- Game runs stay off Maxim's results ledger. Only pre-registered experiments go on it.
- Licences are `docs/design/boundaries.md` §8.2's.

## Open questions

- Turn length: answered by T3 (owner, 2026-11-18): a 0.1 s tick, and the 6 s turn is retired.
- Does the world server become a pip-installable dependency of Maxim experiments (cradles in real physics), or stay
  game-only?
- Who holds copyright: Denny or RMDig LLC?
