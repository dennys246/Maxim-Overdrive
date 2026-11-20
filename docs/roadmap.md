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

- A Godot 4 client that only draws and sends intents. It uploads snapshot arrays as 3-D textures, and a shader
  reads `crack` and `glow`.
- A local transport between client and server: a WebSocket carrying JSON intents and binary snapshots (decided
  2026-11-15; `docs/architecture.md`, "Transport").
- The first tile authored in metres: the ripperdoc clinic and the alley outside it.
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
  `tests/test_cross_tier.py::test_a_fire_that_has_burned_its_fuel_stops_heating`). Needed before the tile's crate
  scenario is gated. **Requirement:** a cell's burn rate must estimate the integral of the point-wise rate over the
  cell, from a reconstructed sub-cell profile, well enough at the coarsest rig to pass the gate (CLAUDE.md,
  "Reconstruct, decide at the point, integrate upward"). Converging is not enough: today's law converges, slowly,
  and the coarse rig still sits far off, because the measured cause is a threshold on a cell's mean temperature
  (the crate's mean temperature agrees across rigs within 1 °C while the degradation driver differs 1.3–1.5×). A
  per-cell ignition or pyrolysis threshold would inherit it. It must flip the strict
  red gate `tests/test_act_validation.py::test_the_fiercest_allowed_fire_has_the_same_outcome_at_every_rig_on_every_turn`,
  and it removes the marked band-aid in `data/world/actions.yaml`, whose ceilings keep fires at the powers the
  current physics has been measured at.
- The substep floor in `src/simcore/core/heat.py`, a marked band-aid kept for bit-identity when resolution left the
  rig: plan step 5a's fixed physics step replaces it with an accuracy floor per step length.
- **Exit:** walk into the alley, set a crate on fire, and watch it crack, glow and burn away. It must look the same,
  apart from detail, at the laptop and rig profiles.

## Phase 2: Physics breadth (later; in parallel with Phase 3)

Each new field ships with a closed-form test and a cross-tier test, under the resolution rule.

- **Sound:** a propagation field feeding Maxim's audio localization (`world_set_axis`).
- **Light and visibility:** what an agent can see, and the light the shaders draw.
- **Gas and radiation:** smoke, toxins and Fallout-style rads, as diffusion plus sources.
- **Convection:** an approximation so rooms heat realistically and fires don't have to sit on a material.
- **Structural support:** cells left unsupported fall as debris.
- **Scale:** move the hot loops to numba or C if profiling says so (never coarser far cells: world_model D21).
- **Close the known gap:** the coarsest rig's late-burn lag (`docs/architecture.md`).
- **Moved from Phase 1 by D26:** zones and vents, combustion per zone and its products, fuel recession and pyrolysis,
  phase change, the CSG footprints, and the lab as Phase 2's benchmark tile.

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
  `think` is host-called and resumable and the gateway is the host's (O6a). The engineering seams are accepted on
  engineering grounds behind parity guards, and the stepped `think` lands **after Maxim's 1.4.0 cut** with the
  agent-loop decomposition slices (O15a), so Phase 4's real NPCs wait for that too. Maxim's design session will write
  a ranked candidates doc that re-checks every citation on a fresh `origin/main`; the rows below are proposals until
  it lands.

Both decisions are recorded in Overdrive. The Maxim-side record is proposed in
`docs/maxim_upstream/decisions_entry_DRAFT.md`.

**Ids** carry an `OD-` prefix, because Maxim already uses `A1`/`A2`, `B1`–`B4`, `T1`/`T2`, `E1`–`E3` and `S0`–`S6`.
"Was" gives the id in this roadmap at 35b9c3e, or the older number where that is what documents cite.

### Issues now

| Id | Item | Was |
|---|---|---|
| OD-I1 | `x or time.time()` turns a world time of 0.0 into the wall clock, at five sites: `attention/salience_map.py:227`, `salience/salience_network.py:222`, `models/language/cost_tracker.py:376`, `:469`, `:480` | A9; filed by Maxim as #1684 |
| OD-I2 | `embodiment/sem.py::ModulatorResult` has no CC3 declaration. Downgraded to a docstring nit: it is an in-process return value, never persisted or sent (Maxim's answer) | C7 (half), P6 |
| OD-I3 | The only pickle-capable load in `src`: `MemoryHub._restore_on_open` → `EmbeddingStore.load` → `np.load(allow_pickle=True)` on the global `~/.maxim/util/semantic_embeddings.npz`; dormant unless `enable_semantic`, and must land before `AgentHome` (OD-A12) makes it reachable from saves | OD-A13; filed by Maxim as #1685 |
| OD-I4 | `ARCHITECTURE.md:182` is stale: the DM runtime doesn't build NPCs through `AgentFactory` (`create_npc_agent` has no caller) | new (Maxim's answer); filed by Maxim as #1686 |
| OD-I5 | A security issue in cloud redaction, held by Maxim as a private advisory; details in private notes, not here | new (TBR-11) |

### Tier A: an agent a host drives (Phase 4 waits on a named subset)

**The subset Phase 4's first NPC needs (O29):** OD-A1 (only #1361 S3a, S3b and S4), OD-A2 to OD-A11, OD-A12's
host-driven ConceptExtractor thread, OD-A14 to OD-A18, and OD-A20 (needed, declined: Phase 4's replay exit carries a
known divergence, `npcs_and_sem.md` §12.2), with the issues OD-I1 and OD-I3. Each is needed for host stepping, world
time only, bit-identical replay, one intent door or the single-player worker boundary, through OD-WC1, OD-EA4,
OD-EA5, OD-EA7 (Maxim's `1263.thread-guard`, configured), OD-EA10 to OD-EA12 and OD-EA14 to OD-EA16, or by O30
(OD-A16). **OD-A18's invocation pid depends on an unbuilt Maxim stage:** `PhysicalEventId` and the per-agent
`EventSequencer` come from Maxim's autonomic plan, post-fence resume stage (G17), not in `src` at 95af47d2 (nor at
c28b2681). Until it lands, our intent record's `invocation` field is reserved and unfilled (null), never a stand-in
(no uuid, no executor `invocation_id`); our host accepts null there until then, and refuses any non-null value that
isn't a pid once the type exists (`tile_and_client.md` §3.1, `checklists.md` step 5b). **OD-EA12 is ours** (Maxim's owner, 2026-11-19: #1361 does not widen G2b, which checks one trace against
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
| OD-A7 | Randomness and ids outside the fence: keyed substreams by Maxim's `utils/seeding.py::make_agent_rng(base_seed, agent_id)` with a stream argument (O40), `agent_id` the persisted NPC key and `base_seed` the host's log root (until the argument exists, `agent_id` is `"npc_key:stream"`; Maxim's owner keeps exactly `sha256(f"{base_seed}:{agent_id}")`, so `:` is forbidden in NPC keys and stream names, refused by our loaders); a new release-gate item after the 1.4.0 cut, not a widened `1305.owned-rng` (Maxim's owner, 2026-11-19); `semantic.py:205`'s `or 42` made an explicit seed; `seed_all` never called on the embedded path; `time.time_ns()` event ids (`decisions/nac.py:1163`) | A-pre | A5 (part) |
| OD-A8 | Fenced ids and stamps (`agent_loop`, `orchestrator`, `tool_dispatch`), NAc stamps and anchors, and `FailureMode.last_fired` (with S4) | A-post | A5 (rest), C8 (half) |
| OD-A9 | `DefaultNetwork.step(now)`, with the thread a caller of it, coordinated with #1263's remainder | A-post | A3 |
| OD-A10 | The embedded entry point on `AgentFactory`, every collaborator required; the DM runtime builds NPCs through it | embeddable | A10 |
| OD-A11 | A closed tool roster for embedded agents, sealed with the advisor's patterns, refused at construction, with no workspace manifest. Engineering, on its own clock; making capability rosters the robot default stays experiment-gated | embeddable | new (TB2-B1) |
| OD-A12 | `AgentHome`: one per-agent object over `AgentFactory`'s `persistence_dir`, routing the ten still-global store families; the ConceptExtractor thread made host-driven, which belongs to cand. A4's closure through `build_memory_hub(start_background_workers=False)` (`runtime/bio_stack.py:489`, `:654`), not A1 | embeddable | new (TB2-B2) |
| OD-A13 | *Moved to OD-I3*, an issue now | — | new (TB2-B2) |
| OD-A14 | The request/reply cut: the request as a value (rendered text, sampling, model role, priority and deadline fields, `tools is None`), produced at `LLMRouter._complete_text`, with the host supplying the model's context size and tokenizer (`token_counter`) to the `PromptBudgeter` (Maxim's `docs/lessons/sim-n-ctx-config-drift.md`); the reply with reserved `cancelled(prefix)` and `truncated` variants that bypass the parse-failure template, and speech as a field emitted first. Not an `LLMBackend` capability | embeddable | new (DR-B2, Arch B3); was "streaming and cancellation on `LLMBackend`" |
| OD-A15 | The stepped `think` on §A.1b's seam, one design for the submit path (OD-A14, OD-H6 and the cancelled-reply bypass land as parts of it): a continuation split into a host-owned header and an agent-owned body, with `basis_seq` (the agent's afferent-scheduler high-water seq, `thalamic_relay.md::preempted_since`; the host holds a copy, never computes it; LLM-proposal staleness waits on GL3.B7) and staleness per hybrid §A.1b.5 (O38); writes only as returned values, retrieval strengthening included; multi-call PFC cycles, `next_actions`; the robot path drives the same `think` (robot parity: OD-EA14); isolation between agents in one process. Lands after the 1.4.0 cut with the agent-loop decomposition slices | embeddable | A4 |
| OD-A16 | Credit for effects measured later: receipts, the cerebellum observing at settle, exactly-once credit, `stale`, `call_error` and `wrong_target` kinds, a per-modulator valence default. Rides on OD-A18 | amendment | C1, C2, P2, P3, P7 |
| OD-A17 | The embedded-path leak closure: prefetch off and the working directory at the agent home; the short-question shortcut is deleted in Maxim for everyone, matcher and fallback (#1689, PR #1694; after #1691 a fallback reply books no NAc credit, but `generate_llm_fallback` still echoes `triggering_input`); no `force=True` logging; paths under the agent home; a static import ban on `utils/audit.py` with `lint_dead_imports`' resolver (blind spot: `importlib` strings), naming `maxim.embodied_runtime`, the internet tools, `build_tool_registry`'s module and `runtime.prefetch`, plus the advisor's three closure tests; no env reads (A4 waits for A1, no `MAXIM_DATA_HOME` exception); no reply reaches the parse-failure template (it echoes the input; its bypass lands with cand. B1, as OD-A15's cancelled-reply bypass); no model backend in the embedded agent, so the model calls outside `think` (`AdaptivePlanner`, the `ToolPainBridge` reflection, `FearAgent`) fail closed | embeddable | new (Maxim's second answer; TBR-3, TBR-7) |
| OD-A18 | Split `execute_and_learn` into dispatch and settle, folding in the parallel and agent-fallback side doors; generate vs apply for memory writes (cand. A6: applied at settle, published through the agent bus; O39), D53 `outcome_valence` and OD-A16's keys; settle feeds NAc's existing traces; memory writes carry provenance by source actor; each dispatched intent carries its invocation pid, and the host stamps it on every receipt and frame event the intent causes (the embedded efference copy, GL3.B2's join). B2 owns the call site (its dispatch is the `Executor._run_started` equivalent, drawing from the agent's own `EventSequencer` inside the worker and putting the pid on the intent value), the sequencer owns the mint, GL3.B2 the contract; the host copies the pid and never mints or computes one, and the executor's `invocation_id` (`str(uuid.uuid4())`, `executor.py:512`) is never the pid or a replay join key. The pid waits on G17 (above). The settle invariant (OD-EA16): each minted pid comes back in exactly one terminal receipt, executed or a typed refusal; no receipt arrives without a minted pid; refusal receipts count as the pid's outcome, not a physical event, and a refusal's pid never appears in a GL3.B2 row (Maxim's review of v6); the host's refusals, deferrals past a budget and drops all end in one; when a worker dies, the host writes a typed `agent_failed` refusal receipt for every in-flight pid (O44). `session_id` comes from the intent log's header and the sequencer's high-water seq is saved in the agent home (O43); each restore opens a new log segment whose number is part of `session_id`, recorded in the header so replay reproduces it, so ids from different segments can't collide whatever the seq (O45; Maxim's Q1 alternative, so nothing is asked of its resume stage); O44's floor stays only as a host-side test that no new pid equals a logged one; GL3.B2's gate holds unchanged (Maxim's Q2 answer); robots settle right after dispatch (OD-EA15); `environment.step` (`tool_dispatch.py:1574`): our position is Maxim's suggestion, that the embedded roster passes no environment and the follow-up arrives in receipts (B2's call). After #1361 S3a and S3b and cand. A3 A-post, behind a bit-identical state-digest parity guard | embeddable | C1 (generate vs apply) |
| OD-A19 | *Withdrawn 2026-11-17:* it duplicated Maxim's own `docs/plans/experience_clock_decay.md` (#1361 S3a), which we already track as OD-A1; the temporal-anchor fallback's age and expiry move in #1361 S3b, and its similarity's host-calendar read (`nac.py:3629`) is OD-A20. Was: Step-size-invariant decay: NAc's eligibility traces decay ×0.9 per loop tick today (`decisions/nac.py:3707`, from `_loop_bio_tick_maintenance`, `runtime/agent_loop.py:800-840`, with five sibling decays), so credit depends on the tick rate; decay as `exp(−Δt/τ)` on the machinery clock, with an exit test crediting one delayed receipt equally at two rate divisors (OD-EA12). Argues against the per-tick decay contract; corrects Overdrive's earlier claim that the traces decay on the wall clock (`correction_1.md`) | A-post | new (npcs_v3 BF3-1) |
| OD-A20 | *Declined by Maxim's owner 2026-11-19 (noted, not adopted):* event similarity stays on the host calendar, and events and anchors age on the experience clock; kept as a known divergence, recorded from Maxim's code and our arithmetic, not from a run; two strict red gates will carry the evidence once the agent PR lands them (`npcs_and_sem.md` §12.2, `checklists.md`). Maxim's delta review widened it, correcting our v4 text, which said the calendar moves only how credit is shared: (a) it can drop an anchor below the 0.01 threshold (`0.3 × similarity × activation`), so a receipt whose only node drops books nothing; (b) anchors set at different host times split differently; (c) `TemporalSignature.from_timestamp` uses local time, so the replay machine's timezone and DST move credit, a cross-machine effect. No pinned `TZ` in production. Our v3 lean put the read on the machinery side; that was wrong, since SCN features reach the model through `temporal_patterns` and `[TEMPORAL]`. Was: Anchor similarity off the host calendar for embedders: after #1361 S3b, `TemporalSignature.now()` (`nac.py:3629`) still scores anchor similarity on host time of day ("host calendar by design", #1361 §(c), §(g)), so a replay at another hour credits differently and an NPC's learning depends on the player's clock. Read it from the perceived-time port. Maxim said it will raise this as a question on #1361 (`response_3.md`); #1361's plan still reads "host calendar by design" in §(g). Our evidence is in `erratum_1.md` | A-post | #1361 question |
| OD-A21 | τ_elig from the striatal window, an argument against #1361's decided Q1 (2026-10-17: "taus in world-seconds, anchored on Exp 30's fixture regime; tune the turn quantum, never per-runtime taus"; 4.75 s at any rate after S3a): NAc's dopamine eligibility window is about 0.3–2 s (Yagishita et al. 2014); longer delays belong to the anchor path, which is why OD-A20 matters. An owner decision with its own experiment in Maxim, not a doc edit; S3a records the rationale first | A-post | #1361 Q1 |

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
  - OD-A16 has closed the stale-refusal divergence before Phase 4.
  - Exp 64a's prerequisites (OD-B1 to OD-B7) are met, and its pre-registration is frozen.
  - The Exp 64 draft is in `docs/maxim_upstream/` and moves to Maxim's `docs/experiments/`.

## Phase 4: Cradles and the first NPCs (later)

- **Starts on tier A's subset** (owner decisions O6, O15a and O29): no real Maxim NPC runs before the subset under
  Phase 3's tier A heading ships (OD-A1's #1361 S3a, S3b and S4; OD-A2 to OD-A11; OD-A12's thread; OD-A14 to OD-A18;
  OD-A20, declined, so the replay exit carries its divergence; the issues OD-I1 and OD-I3), and before Maxim's 1.4.0 cut with the agent-loop decomposition slice that
  carries the stepped `think` (OD-A15). OD-A21, #1361 S5 and S6, and OD-A12's store routing don't block it.
- **Guest sessions with real NPCs (Phase 5 or later, O28) wait for O14's gates,** held by a strict red gate that refuses guest joins while
  real-Maxim NPCs are live (owned by `phase1/protocol`), and flipped only when each passes:
  - the worker process and its channel gate (`npcs_and_sem.md` §6.6);
  - a no-effect test (no file reads or writes, sockets or spawns outside the agent home);
  - a dialogue-level bypass test driving guest speech through a real worker (prefetch, the parse-failure template,
    phrase commands, and the shortcut Maxim deleted, #1689, as a regression);
  - the guest-text gate refusing line separators and format characters on decoded text;
  - memory provenance with a purge that survives relay and extraction.
  - O18's local model by default, remote only with the guest's informed consent (decided).
  Deferred by name (O30): an OS sandbox for workers in guest sessions, decided before guest sessions open.
- The cradle writer: a fixed event pool from an arc plus handcrafted inflection points, assembled per NPC in code.
- Three NPCs on the first tile (the ripperdoc, a fixer and a street kid), each cradled from an authored life.
- A dialogue screen and turn order. Movement runs in substrate-primary mode (no LLM); speech goes to the LLM.
- Save format v1: the world plus each NPC's agent home, including the agent's `EventSequencer` high-water seq, so a
  loaded save continues the sequence; `session_id` comes from the intent log's header (the log's root id, the NPC
  key and the segment number, a new segment per restore), never the wall clock or a uuid (O43, O45).
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
  object exists.
- An IP gate in front of `simcore.core.imagination.place`, shipped with the LLM caller that feeds it, never after it
  (design: `docs/design/ip_and_licensing.md` §3, once reviewed).
- Assets are derived deterministically from specs: meshes from cells, procedural impact and burn sounds from
  material properties. Image-model art is cached decoration only and never decides physics.
- **Exit:** a player imagines an object mid-scene and it burns and breaks like an authored one, at every rig.

## Phase 7: Book to world (later; the pipeline lives in Maxim)

See `docs/book_to_world.md`. Extraction, timeline and the perspective split, then cradles, scene specs and object specs.

- **Exit:** a public-domain book (first candidate: *The Machine Stops*) becomes a tile whose characters remember only
  what they witnessed. Then Denny's novel becomes Maxim Prime.

## Phase 8: Expand and ship (later)

- More tiles and a world map.
- **Steam:** the Steamworks SDK in a private module, a trademark search and filing for the name, and the WashU OTM
  question settled before any store page.
- **A creator marketplace, decided, not assumed.** Once players exist, decide whether to run one, from the costs in
  `docs/design/ip_and_licensing.md` §5 (copyright takedowns and the safe harbour a cut puts at risk, EU seller
  verification, payouts through a merchant of record, Steam's rules on purchases and trading, curation, unit
  economics). Nothing for a marketplace is built before that decision; content identity (Phase 1) and the IP gate
  (Phase 6) are needed with or without one.
- **Exit:** a store page.

## Standing rules

The engineering standards (no band-aids, testing, the pre-push review, determinism, formats, budgets, client
rules) live in `CLAUDE.md`, each with the check that enforces it; unenforced ones are rows in
`docs/standards_backlog.md`. The rules below are the design rules.

- **The resolution rule:** a rig changes precision, never the outcome class.
- Physics parameters are per unit volume. Scenes are authored in metres, never in cells.
- Energy lands by exact cell average or by volume overlap, never by whether the cell centre is inside.
- The world server is authoritative. The client never simulates anything that feeds back into the world.
- Game runs stay off Maxim's results ledger. Only pre-registered experiments go on it.
- Code is Apache-2.0. Story, characters and assets are all rights reserved.

## Open questions

- Turn length: 6 s is a placeholder. What does combat feel like at 3 s or 10 s?
- Does the world server become a pip-installable dependency of Maxim experiments (cradles in real physics), or stay
  game-only?
- Who holds copyright: Denny or RMDig LLC?
