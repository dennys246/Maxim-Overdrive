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
  frame. It returns intents, memory writes and thought requests as values, calls a model only through a gateway the
  host supplies, uses only declared tools, and keeps state only in a home the host names.
  - Overdrive builds no interim mode in which Maxim's agent runs its own loop beside the world.
  - **Phase 4's NPCs wait for tier A.**

Both decisions are recorded in Overdrive. The Maxim-side record is proposed in
`docs/maxim_upstream/decisions_entry_DRAFT.md`.

**Ids** carry an `OD-` prefix, because Maxim already uses `A1`/`A2`, `B1`–`B4`, `T1`/`T2`, `E1`–`E3` and `S0`–`S6`.
"Was" gives the id in this roadmap at 35b9c3e, or the older number where that is what documents cite.

### Issues now

| Id | Item | Was |
|---|---|---|
| OD-I1 | `attention/salience_map.py`: `current_time or time.time()` turns a world time of 0.0 into the wall clock | A9 |
| OD-I2 | `embodiment/sem.py::ModulatorResult` has no CC3 declaration; path (b), with `metadata` documented as the extension channel | C7 (half), P6 |

### Tier A: an agent a host drives (Phase 4 waits on all of it)

Drafts:
- `world_clock_release_DRAFT.md`: two plans. **A-pre** goes on its own clock, touching no fenced file. **A-post**
  lands with Maxim's 1.3.6, Session A.
- `default_network_stepped_DRAFT.md`.
- `embeddable_agent_DRAFT.md`.
- `propose_settle_amendment_DRAFT.md`, an amendment to Maxim's `tool_failure_credit.md`.

| Id | Item | Plan | Was |
|---|---|---|---|
| OD-A1 | #1361's S3–S6: a dependency, not duplicated. S3–S6 are in 1.3.6; S2 coordinates with Session V; S0 and S1 shipped. | — | A1 |
| OD-A2 | `AgentTime`. `Clock` gives epoch seconds as stamps are today, microseconds and a calendar; `Rng`'s default is the global `random`; plus `IdSource`. Host defaults read at call time, so `_StepClock` still works. A `sys.setprofile` tripwire on the stepping thread. Wiring from the embedded entry point. | A-pre | A2 |
| OD-A3 | Prompt and observation time from the injected calendar, or omitted. Covers `prompt_builder`'s datetime and identity sections, `llm_fallback`'s canned answers and `context_pool`'s `[HH:MM:SS]` stamps. | A-pre | A6 |
| OD-A4 | Live-path stamps outside the fence, passed explicitly with defaults kept; `SensorReading` stamping | A-pre | A5 (part) |
| OD-A5 | The hippocampus's 30 s wall window, attention and salience stamps, and `TemporalSignature`'s phase source | A-pre | A5 (part), A7 (source half) |
| OD-A6 | Reaction and pain dispatch gates on the injected clock under embedding. Motor and IO limits stay on the wall. Lands after #1200. | A-pre | A8 |
| OD-A7 | Randomness and ids outside the fence | A-pre | A5 (part) |
| OD-A8 | Fenced ids and stamps (`agent_loop`, `orchestrator`, `tool_dispatch`), NAc stamps and anchors, and `FailureMode.last_fired` (with S4) | A-post | A5 (rest), C8 (half) |
| OD-A9 | `DefaultNetwork.step(now)`, with the thread a caller of it, coordinated with #1263's remainder | A-post | A3 |
| OD-A10 | The embedded entry point on `AgentFactory`, every collaborator required; the DM runtime builds NPCs through it | embeddable | A10 |
| OD-A11 | A closed tool roster for embedded agents, refused at construction, with no workspace manifest | embeddable | new (TB2-B1) |
| OD-A12 | A per-agent home, not the process-wide `data_home()` | embeddable | new (TB2-B2) |
| OD-A13 | No pickle on load paths (`similarity/semantic.py`'s embeddings) | embeddable | new (TB2-B2) |
| OD-A14 | Token streaming and cancellation as optional `LLMBackend` capabilities, and an inspectable request | embeddable | new (DR-B2, Arch B3) |
| OD-A15 | `step(world_dt, frame)` and `think(request)` returning values (generate vs apply), `apply`, and isolation between agents in one process | embeddable | A4, C1 (generate vs apply) |
| OD-A16 | Credit for effects measured later: receipts, the cerebellum observing at settle, exactly-once credit, `stale` and `call_error` kinds, a per-modulator valence default | amendment | C1, C2, P2, P3, P7 |

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
| OD-H4 | Deliberation triggered during the other speaker's turn | new (BF2-2) |
| OD-H5 | A turn-taking substrate: gaze, backchannels, content-free fillers and floor-holding while deliberation is pending, and yielding the floor past a ceiling. None of the hybrid plans has one (owner decision OA3, revised 2026-11-16) | new (foundations delta, Bio-faithful) |

**Retired:** C9 (cancellable SEM actions and deliberation). Mid-action cancel is Maxim's own `sem_interruptibility.md`,
and cancelling a model call is OD-A14.

- **Exit:**
  - Tier A has shipped, and Overdrive's agent port drives a real Maxim agent bit-identically under the world clock
    (exit tests OD-WC1 and OD-EA5).
  - OD-A16 has closed the stale-refusal divergence before Phase 4.
  - Exp 64a's prerequisites (OD-B1 to OD-B7) are met, and its pre-registration is frozen.
  - The Exp 64 draft is in `docs/maxim_upstream/` and moves to Maxim's `docs/experiments/`.

## Phase 4: Cradles and the first NPCs (later)

- **Starts on tier A** (owner decision O6, 2026-11-16): no real Maxim NPC runs before the embeddable agent plan and
  its dependencies ship (Phase 3, OD-A1 to OD-A16).
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
