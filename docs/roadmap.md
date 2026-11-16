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
- Fires that go out when their fuel is gone, so a burnt-out crate's fire stops instead of heating air to millions of
  degrees (`docs/architecture.md`, Known gaps; the red gate is
  `tests/test_cross_tier.py::test_a_fire_that_has_burned_its_fuel_stops_heating`). Needed before the tile's crate
  scenario is gated. It removes the marked band-aid in `data/world/actions.yaml`, which holds `ignite` to the
  envelope where fires are verified the same at every rig.
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

## Phase 3: Maxim upstream, the 1.4 line items (later; in Maxim, through its own process)

These go to the Maxim repo, each with its own issue, plan and review (pre-registration, four-lens review, ledger).
They are the prerequisites for Exp 64 and for NPCs that remember.

1. NPC replies recall memory (`runtime/agent_pool.py::_generate_llm_response` never reads the hippocampus).
2. A persona hook in the full loop (`agents/prompt_builder.py:159` hard-codes "You are Maxim").
3. A seed-memory API: backdated `experience_us`, no 30 s wall-clock de-duplication, salience taken from the event.
4. Bus messages reach the receiver's memory (`AgentPool._handle_message` only logs them).
5. The DM runtime builds NPCs through `AgentFactory`; `ARCHITECTURE.md` says it does, but it doesn't.
6. Save affordance effects (#1159: `to_dict` drops `params`, `requires`, `self_effect` and `target_effect`).
7. Cancellable SEM actions (`docs/plans/sem_interruptibility.md`).
8. The arc YAML loader keeps `act`, `world_entities` and `mother_scaffold`.
9. An install-augment API: attach a modulator and regenerate its tools in one call.
10. Validate a tool's arguments before the tool runs, and book a malformed argument as a cognitive error, not a tool
    failure. Today `tools/base.py::Tool._validate_input` checks only that required keys are present, so a NaN or an
    unknown key reaches the modulator, is refused there, and `ToolPainBridge.record_tool_failure` books a surprising
    NEGATIVE on `tool:<region>_<affordance>`: a JSON typo teaches an NPC to avoid striking the crate in every state.
    The proposal validates against the declared `AffordanceSchema` (types, unknown keys, finiteness, ideally declared
    ranges) in the executor, as an executor-made refusal kind, which keeps #1315's rule that a tool body can't exempt
    itself. **Argues against:** TF2 (`docs/plans/tool_failure_credit.md`), which counts any tool that reached
    `tool.run` as having run. Evidence: the 33 probes of Overdrive's PR 1 (`tests/test_act_validation.py`) and its
    Bio-faithful review.

- **Exit:** Exp 64a's prerequisites are met and its pre-registration is frozen. The draft is in
  `docs/maxim_upstream/` and moves to Maxim's `docs/experiments/`.

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
