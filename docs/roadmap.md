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
- Fires that go out when their fuel is gone, so a burnt-out crate's fire stops instead of heating air to millions of
  degrees (`docs/architecture.md`, Known gaps; the red gate is
  `tests/test_cross_tier.py::test_a_fire_that_has_burned_its_fuel_stops_heating`). Needed before the tile's crate
  scenario is gated.
- **Exit:** walk into the alley, set a crate on fire, and watch it crack, glow and burn away. It must look the same,
  apart from detail, at the laptop and rig profiles.

## Phase 2: Physics breadth (later; in parallel with Phase 3)

Each new field ships with a closed-form test and a cross-tier test, under the resolution rule.

- **Sound:** a propagation field feeding Maxim's audio localization (`world_set_axis`).
- **Light and visibility:** what an agent can see, and the light the shaders draw.
- **Gas and radiation:** smoke, toxins and Fallout-style rads, as diffusion plus sources.
- **Convection:** an approximation so rooms heat realistically and fires don't have to sit on a material.
- **Structural support:** cells left unsupported fall as debris.
- **Scale:** run cells beyond `full_res_radius_m` coarser, then move the hot loops to numba or C if profiling says so.
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
all read against Maxim `origin/main` `7084f561` (2026-11-16).

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
| OD-I1 | `x or time.time()` turns a world time of 0.0 into the wall clock, at five sites: `attention/salience_map.py:227`, `salience/salience_network.py:222`, `models/language/cost_tracker.py:376`, `:469`, `:480` | A9 |
| OD-I2 | `embodiment/sem.py::ModulatorResult` has no CC3 declaration. Downgraded to a docstring nit: it is an in-process return value, never persisted or sent (Maxim's answer) | C7 (half), P6 |
| OD-I3 | The only pickle-capable load in `src`: `MemoryHub._restore_on_open` → `EmbeddingStore.load` → `np.load(allow_pickle=True)` on the global `~/.maxim/util/semantic_embeddings.npz`; dormant unless `enable_semantic`, and must land before `AgentHome` (OD-A12) makes it reachable from saves | OD-A13 |
| OD-I4 | `ARCHITECTURE.md:182` is stale: the DM runtime doesn't build NPCs through `AgentFactory` (`create_npc_agent` has no caller) | new (Maxim's answer) |
| OD-I5 | A security issue in cloud redaction, held by Maxim as a private advisory; details in private notes, not here | new (TBR-11) |

### Tier A: an agent a host drives (Phase 4 waits on a named subset)

**The subset Phase 4's first NPC needs (O29):** OD-A1 (only #1361 S3a, S3b and S4), OD-A2 to OD-A11, OD-A12's
host-driven ConceptExtractor thread, OD-A14 to OD-A18 and OD-A20, with the issues OD-I1 and OD-I3. Each is needed for
host stepping, world time only, bit-identical replay, one intent door or the single-player worker boundary, through
OD-WC1, OD-EA4, OD-EA5, OD-EA10 to OD-EA12 and the draft's thread-count test, or by O30 (OD-A16). Exp 64a also
needs OD-B1 to OD-B7. Not blocking: #1361 S5 and S6, and OD-A21. OD-A12's store routing waits for two agents in one
process. So the subset is most of tier A, and its long pole, OD-A15, stays.

**Timing, from Maxim (2026-11-19, `reviews/maxim_response_1/response_4.md`; a planning range, not a commitment):**
1.4.0 earliest February 2027, planned March to May 2027, after 1.3.4 to 1.3.6 and 1.4.0's release gates (#1305's
owned RNG, where cand. A2 lives). The stepped `think` (cand. B1) comes after 1.4.0, in the 1.5 hybrid line's `src`
phase, with no range yet, so Phase 4's first real NPC is after mid-2027 at the earliest. Maxim accepted the world-seam
front gate (the case for a host-driven runtime mode); `embeddable_agent_DRAFT.md` gets Maxim's review round before
any Maxim `src/` lands for it.

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
| OD-A3 | Prompt and observation time only through the perceived-time port, or omitted, with a lint banning `datetime.now`, `strftime` and `localtime` in prompt-reaching modules. Covers `prompt_builder`'s datetime and identity sections (`:237`, `:1125-1127`), `llm_fallback`'s canned answers and `context_pool`'s `[HH:MM:SS]` stamps (`:468`, `:493`). | A-pre | A6 |
| OD-A4 | Live-path stamps outside the fence, passed explicitly with defaults kept; `SensorReading` stamping; a tool's duration supplied by the host in world time, not `runtime/tool_dispatch.py:1343`'s wall clock (which sets NAc valence above 2.0 s) | A-pre | A5 (part) |
| OD-A5 | The hippocampus's 30 s wall window, attention and salience stamps, and `TemporalSignature`'s phase source | A-pre | A5 (part), A7 (source half) |
| OD-A6 | Reaction and pain dispatch gates on the injected clock under embedding. Motor and IO limits stay on the wall. Lands after #1200. | A-pre | A8 |
| OD-A7 | Randomness and ids outside the fence: keyed substreams, `random.Random(stable_hash_64_signed(f"{base_seed}:{agent_id}:{stream}"))` (Maxim's cand. A2) if `agent_id` is the persisted NPC key and `base_seed` the host's log root, else our `SeedSequence` handout (npcs §3.4); settled inside #1305; `semantic.py:205`'s `or 42` made an explicit seed; `seed_all` never called on the embedded path; `time.time_ns()` event ids (`decisions/nac.py:1163`) | A-pre | A5 (part) |
| OD-A8 | Fenced ids and stamps (`agent_loop`, `orchestrator`, `tool_dispatch`), NAc stamps and anchors, and `FailureMode.last_fired` (with S4) | A-post | A5 (rest), C8 (half) |
| OD-A9 | `DefaultNetwork.step(now)`, with the thread a caller of it, coordinated with #1263's remainder | A-post | A3 |
| OD-A10 | The embedded entry point on `AgentFactory`, every collaborator required; the DM runtime builds NPCs through it | embeddable | A10 |
| OD-A11 | A closed tool roster for embedded agents, sealed with the advisor's patterns, refused at construction, with no workspace manifest. Engineering, on its own clock; making capability rosters the robot default stays experiment-gated | embeddable | new (TB2-B1) |
| OD-A12 | `AgentHome`: one per-agent object over `AgentFactory`'s `persistence_dir`, routing the ten still-global store families; the ConceptExtractor thread made host-driven | embeddable | new (TB2-B2) |
| OD-A13 | *Moved to OD-I3*, an issue now | — | new (TB2-B2) |
| OD-A14 | The request/reply cut: the request as a value (rendered text, sampling, model role, priority and deadline fields, `tools is None`); the reply with reserved `cancelled(prefix)` and `truncated` variants that bypass the parse-failure template, and speech as a field emitted first. Not an `LLMBackend` capability | embeddable | new (DR-B2, Arch B3); was "streaming and cancellation on `LLMBackend`" |
| OD-A15 | The stepped `think` on §A.1b's seam, one design for the submit path (OD-A14, OD-H6 and the cancelled-reply bypass land as parts of it): a continuation split into a host-owned header and an agent-owned body, with `basis_seq`; writes only as returned values, retrieval strengthening included; multi-call PFC cycles, `next_actions`; the robot path drives the same `think`; isolation between agents in one process. Lands after the 1.4.0 cut with the agent-loop decomposition slices | embeddable | A4 |
| OD-A16 | Credit for effects measured later: receipts, the cerebellum observing at settle, exactly-once credit, `stale` and `call_error` kinds, a per-modulator valence default. Rides on OD-A18 | amendment | C1, C2, P2, P3, P7 |
| OD-A17 | The embedded-path leak closure: prefetch off and the working directory at the agent home; the short-question shortcut fixed at its root in Maxim, since it fires on any input (TBR-13), not bypassed for embedders; no `force=True` logging; paths under the agent home; a static import ban (naming `maxim.embodied_runtime`, the internet tools, `build_tool_registry`'s module and `runtime.prefetch`) plus the advisor's three closure tests; no reply reaches the parse-failure template (it echoes the input; its bypass lands with cand. B1, as OD-A15's cancelled-reply bypass); no model backend in the embedded agent, so the model calls outside `think` (`AdaptivePlanner`, the `ToolPainBridge` reflection, `FearAgent`) fail closed | embeddable | new (Maxim's second answer; TBR-3, TBR-7) |
| OD-A18 | Split `execute_and_learn` into dispatch and settle, folding in the parallel and agent-fallback side doors; generate vs apply for memory writes, D53 `outcome_valence` and OD-A16's keys; settle feeds NAc's existing traces; memory writes carry provenance by source actor; robots settle right after dispatch; `environment.step` (`tool_dispatch.py:1516`) leaves dispatch for the host. After #1361 S3a and S3b and cand. A3 A-post, behind a bit-identical state-digest parity guard | embeddable | C1 (generate vs apply) |
| OD-A19 | *Withdrawn 2026-11-17:* it duplicated Maxim's own `docs/plans/experience_clock_decay.md` (#1361 S3a), which we already track as OD-A1; the temporal-anchor fallback's age and expiry move in #1361 S3b, and its similarity's host-calendar read (`nac.py:3629`) is OD-A20. Was: Step-size-invariant decay: NAc's eligibility traces decay ×0.9 per loop tick today (`decisions/nac.py:3707`, from `_loop_bio_tick_maintenance`, `runtime/agent_loop.py:800-840`, with five sibling decays), so credit depends on the tick rate; decay as `exp(−Δt/τ)` on the machinery clock, with an exit test crediting one delayed receipt equally at two rate divisors (OD-EA12). Argues against the per-tick decay contract; corrects Overdrive's earlier claim that the traces decay on the wall clock (`correction_1.md`) | A-post | new (npcs_v3 BF3-1) |
| OD-A20 | Anchor similarity off the host calendar for embedders: after #1361 S3b, `TemporalSignature.now()` (`nac.py:3629`) still scores anchor similarity on host time of day ("host calendar by design", #1361 §(c), §(g)), so a replay at another hour credits differently and an NPC's learning depends on the player's clock. Read it from the perceived-time port. Maxim raises it as a #1361 question; we bring this evidence (`erratum_1.md`) | A-post | #1361 question |
| OD-A21 | τ_elig from the striatal window, against #1361 Q1 (taus anchored on Exp 30's 2 Hz fixture, 4.75 s at any rate after S3a): NAc's dopamine eligibility window is about 0.3–2 s (Yagishita et al. 2014); longer delays belong to the anchor path, which is why OD-A20 matters. An owner decision with its own experiment in Maxim, not a doc edit; S3a records the rationale first | A-post | #1361 Q1 |

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
| OD-H6 | Under a host-called `think` the submit cadence is the host's, so the 0.5 s wall `llm_submit_interval` (`loop_controller.py:157`) needs no change for embedders; it lands inside cand. B1 (OD-A15), not as its own ask, since #1361 §(g) keeps it on the wall for robots on purpose. Triggering deliberation by escalation is the later, experiment-earned change | new (Arch 4.3, BD-18) |

**Retired:** C9 (cancellable SEM actions and deliberation). Mid-action cancel is Maxim's own `sem_interruptibility.md`,
and cancelling a model call is a `cancelled(prefix)` reply under OD-A14.

- **Exit:**
  - Tier A's subset (O29) has shipped, and Overdrive's agent port drives a real Maxim agent bit-identically under the world clock
    (exit tests OD-WC1, OD-EA5, OD-EA10, OD-EA11 and OD-EA12).
  - OD-A16 has closed the stale-refusal divergence before Phase 4.
  - Exp 64a's prerequisites (OD-B1 to OD-B7) are met, and its pre-registration is frozen.
  - The Exp 64 draft is in `docs/maxim_upstream/` and moves to Maxim's `docs/experiments/`.

## Phase 4: Cradles and the first NPCs (later)

- **Starts on tier A's subset** (owner decisions O6, O15a and O29): no real Maxim NPC runs before the subset under
  Phase 3's tier A heading ships (OD-A1's #1361 S3a, S3b and S4; OD-A2 to OD-A11; OD-A12's thread; OD-A14 to OD-A18;
  OD-A20; the issues OD-I1 and OD-I3), and before Maxim's 1.4.0 cut with the agent-loop decomposition slice that
  carries the stepped `think` (OD-A15). OD-A21, #1361 S5 and S6, and OD-A12's store routing don't block it.
- **Guest sessions with real NPCs (Phase 5 or later, O28) wait for O14's gates,** held by a strict red gate that refuses guest joins while
  real-Maxim NPCs are live (owned by `phase1/protocol`), and flipped only when each passes:
  - the worker process and its channel gate (`npcs_and_sem.md` §6.6);
  - a no-effect test (no file reads or writes, sockets or spawns outside the agent home);
  - a dialogue-level bypass test driving guest speech through a real worker (prefetch, the shortcut, the
    parse-failure template, phrase commands);
  - the guest-text gate refusing line separators and format characters on decoded text;
  - memory provenance with a purge that survives relay and extraction.
  - O18's local model by default, remote only with the guest's informed consent (decided).
  Deferred by name (O30): an OS sandbox for workers in guest sessions, decided before guest sessions open.
- The cradle writer: a fixed event pool from an arc plus handcrafted inflection points, assembled per NPC in code.
- Three NPCs on the first tile (the ripperdoc, a fixer and a street kid), each cradled from an authored life.
- A dialogue screen and turn order. Movement runs in substrate-primary mode (no LLM); speech goes to the LLM.
- Save format v1: the world plus each NPC's agent home.
- **Exit:** Exp 64a runs and its verdict is published, pass or an honest null. If it passes, 64b (the gradient) and
  64c (ordering) follow.

## Phase 5: The player's body and the Overdrive mechanic (later)

- The player's body is an SEM entity with the same body grammar as the NPCs.
- Cyberware is installed and removed at the ripperdoc. Hacking is a `target_effect` on another body's sensors.
- **Overdrive:** forcing an action through a part below its integrity limit, paid for in pain.
- Rumour: fear and reputation spread between NPCs through hivemind merges of learned state, never of episodes.
- **Exit:** an NPC who never met the player avoids them because another NPC got hurt.

## Phase 6: Imagination as a generative engine (later)

- In-game imagination, bound to the materials table and a power budget. The world validates every spec before the
  object exists.
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
