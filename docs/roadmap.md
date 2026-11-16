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

These go to the Maxim repo, each with its own issue, plan and review (pre-registration, four-lens review, ledger).
None is patched here. **Owner decision (2026-11-16):** Overdrive is a vehicle for refining Maxim's SEM, including
types Maxim marks shape-frozen, as long as changes stay bio-faithful and go through Maxim's process. SEM refinement is
a priority of Overdrive's foundations work, which runs in parallel with Maxim: Overdrive lays its side (the agent
port, propose and settle, world time) now and tests against each Maxim change as it lands.

Ids are tier-prefixed, because the earlier lists collided (PR 1's items 10 and 11, `realtime_lanes_coop.md` §6 items
10–18, `world_v2.md` P1–P7). "Was" gives the old number.

### Tier A: the world-clock release (an agent a deterministic host can step)

Its own release, on its own clock like Maxim's atonia gate. Draft: `docs/maxim_upstream/world_clock_release_DRAFT.md`
(10 PRs; the loop half lands after Maxim's 1.3.6). Nothing NPC-related in Overdrive is real until it lands.

| Id | Item | Was |
|---|---|---|
| A1 | #1361, experience-clock decay, S2–S6 (scheduled in Maxim's 1.3.6; a dependency, not duplicated) | prerequisite |
| A2 | An injected clock, RNG and id source on the agent's live path, defaulting to the host clock so robots are unchanged | 15 (part) |
| A3 | An externally stepped Default Network, `step(world_now)` | 11 |
| A4 | An externally stepped agent live tick, `step(world_dt)` | 12 |
| A5 | Deterministic agents: builtin `hash()` in hippocampus de-duplication, about 38 `uuid4` calls, about 39 uses of the global `random`, 36 `default_factory=time.time` stamps, wall-clock ids | 15 |
| A6 | Prompt time from the injected clock, or omitted: no host date, time or time zone in prompts or canned answers (`prompt_builder.py:1104`, `llm_fallback.py:330-338`) | new |
| A7 | `TemporalSignature` phase from the world clock and day length, no host local time; the oscillator integrates elapsed time, not a fixed step per event. Argues against #1361 §(g), "host calendar by design" | 10 (first half) |
| A8 | Split refractories by kind: motor and IO rate limits stay on the wall; perceptual refractoriness and cooldowns read the injected clock. Argues against #1361 §(g), "hardware safety" | new |
| A9 | The `salience_map.py:227` bug: `current_time or time.time()` turns a world time of 0.0 into the wall clock | new |
| A10 | The DM runtime builds NPCs through `AgentFactory` (`ARCHITECTURE.md` says it does, but it doesn't); the injected clock rides on the factory | 5 |

### Tier B: the 1.4 line (NPCs that remember, and bio-faithful time, earned by experiment)

Each mechanism enters Maxim as `[engineering]` and graduates only through a pre-registered experiment (the skeptic's
T1 and T2, `docs/design/research/time/skeptic.md` §5). These are also Exp 64's prerequisites.

| Id | Item | Was |
|---|---|---|
| B1 | NPC replies recall memory (`runtime/agent_pool.py::_generate_llm_response` never reads the hippocampus) | 1 |
| B2 | A persona hook in the full loop (`agents/prompt_builder.py:159` hard-codes "You are Maxim") | 2 |
| B3 | A seed-memory API: backdated `experience_us`, salience taken from the event (its wall-clock de-duplication half lands in A5) | 3 |
| B4 | Bus messages reach the receiver's memory (`AgentPool._handle_message` only logs them) | 4 |
| B5 | Save affordance effects (#1159: `to_dict` drops `params`, `requires`, `self_effect` and `target_effect`) | 6 |
| B6 | The arc YAML loader keeps `act`, `world_entities` and `mother_scaffold` | 8 |
| B7 | An install-augment API: attach a modulator and regenerate its tools in one call | 9 |
| B8 | An SCN oscillator with a free-running period, entrained by a world light percept, its phase exposed as an estimate (experiment T1) | 10 (second half) |
| B9 | The prompt's time of day from the agent's own time sense, not the clock | new |
| B10 | A modelled time sense: interval estimates with scalar noise, state-dependent latency (experiment T2) | new |
| B11 | Consolidation without ending the session, on experience time, with idle replay | 14 |

### Tier C: the 1.5 hybrid line, and the SEM refinement plan

Drafts: `docs/maxim_upstream/hybrid_1_5_line_DRAFT.md` and `docs/maxim_upstream/sem_breaking_change_plan_DRAFT.md`
(additive first; at most one breaking batch, opened only on evidence from Overdrive's use).

| Id | Item | Was |
|---|---|---|
| C1 | Propose and settle: credit for effects that arrive after the call (`ModulatorReceipt`, a deferred cerebellum observation); generate vs apply | P3, 16 |
| C2 | Validation in the executor, with a call-error kind, and a stale refusal kind that is context, never credit | PR 1's 10, P2, P7 |
| C3 | A declared direction per affordance (done to vs done by) | PR 1's 11, P1 |
| C4 | The acting entity reaches `Modulator.execute` | new (BF-6) |
| C5 | Deliberation couples to fatigue through `EntropicDriveSpec.coupled_to`, parsed today but never applied | new |
| C6 | Percepts and instruments as declared channels | new (BF-7) |
| C7 | A `SEM_PROTOCOL_VERSION` with a written minor and major rule; a CC3 declaration on `ModulatorResult` | P6 |
| C8 | `world_set_axis` for sub-sensors such as `arms.thermal`; `FailureMode.last_fired` on world time | P4, P5 |
| C9 | Cancellable SEM actions and cancellable deliberation with a world-time deadline | 7, 13 |
| C10 | Re-key the hybrid plan's revive trigger (M76) to include a simulated body | 17 |
| C11 | A Maxim 1.5 line: build the hybrid runtime and tune it by experiment | 18 |

- **Exit:** tier A has shipped and Overdrive's agent port runs a real Maxim agent bit-identically under the world
  clock; Exp 64a's prerequisites (tier B, items B1–B7) are met and its pre-registration is frozen. The Exp 64 draft is
  in `docs/maxim_upstream/` and moves to Maxim's `docs/experiments/`.

## Phase 4: Cradles and the first NPCs (later)

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
