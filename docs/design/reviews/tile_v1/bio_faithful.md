# Bio-faithful integration review: `docs/design/tile_and_client.md` (f6afd66)

Reader: Bio-faithful integration lens (`docs/code_review.md`). Maxim claims are read from `origin/main` at `6fee7377`
(2026-11-17), via `git show`. Checked: the tile spec in full; `sem_env/bridge.py`; `npcs_and_sem.md` §0, §2, §3 and
§7–§8; `boundaries.md` §4.2–§4.4 and §7.2; `research/signals/maxim_senses.md`; `world_model.md` D28;
`world_v2.md` §10; `foundations_plan.md` §2; Maxim's `embodiment/sem.py` (`Entity`, the three frozen dataclasses),
`_data/components/bodies/base_humanoid.yaml`, `minecraft_player.yaml`, `minecraft_bench57.yaml`,
`embodiment/audio_localization.py::world_set_axis`, `similarity/place_code.py`.

What holds, stated only so the reader knows it was checked: no host or wall time is put into the world state the
spec defines (integer mm, integer tick, headings as integers, the sky keyed to world time, not the client's clock);
shader lighting is declared render-only and never sensed; the spec does not add fields to Maxim's frozen types.

Counts: 2 BLOCKER, 6 SHOULD-FIX, 4 NIT.

---

## BLOCKER

### BF-B1. The actor table perceivers will read rides the wall-throttled wire frame

`tile_and_client.md::§5.3 Cadence and size` (with §11, second bullet).

§5.3 says actors go "in the `tick` message, throttled to ≤ 30 Hz" and "are also a table in the published frame, so a
Phase 4 perceiver reads bodies and cells from one frame". The frame described in the same list is the *wire*
snapshot: "at most `snapshot_hz` (2 Hz during fire), latest-wins" (realtime §7: "at most `snapshot_hz` per session").
Both throttles are in wall time. Step 7 builds "the actor table in frames" (§13), so this is what gets built.

Failure scenario: Phase 4, the owner sets the dial to 10×. Ticks now run at 100 per wall second, physics steps at 20
per wall second, and the wire frame is capped at 2 per wall second, latest-wins. Which ticks' actor poses and cells a
perceiver gets now depends on the dial and on host load. An NPC watching the player cross the alley sees it at 0.5 s
world spacing at 1× and at 5 s world spacing at 10×. Its reaction (npcs §3.2's P0 latency, 150–250 ms) is then set by
the throttle, not by its body. That is the dial reaching cognition, which `npcs_and_sem.md` §7.3 forbids ("what a
sensor returns can't depend on the dial") and its §3.1 dial-invisibility test is written to catch. It also breaks
replay of percepts, since latest-wins drops are not logged.

There is a second, deterministic defect under it. Even the simulation's own published `Frame` (boundaries §4.2:
after each physics step and each tick that applied an intent) misses bodies under a held heading. A `move {heading}`
held for 32 ticks (§7.2, ticks 10–42) applies one intent, then moves the body every tick with no further intent, so
frames between physics steps don't exist. A perceiver sees the body jump 0.7 m every 0.5 s.

Fix: state two separate things in §5.3. (1) The simulation's published `Frame` carries the actor table **every tick
on which any actor's state changed** (O23 "on change": a moving body is a change every tick); cells keep their
physics-step and intent-tick cadence; actors are tens of bytes each, so this is cheap. (2) The `tick` throttle and
`snapshot_hz` are wire encodings for the client only. No perceiver ever reads the wire. Add a test: the actor table
an adapter pins at tick T is the same at dial 1× and 20× and under an injected wire stall.

### BF-B2. The body takes no heat until Phase 4/5, but D28's heat-debt prototype is step 10, two steps after the tile

`tile_and_client.md::§2.1 The body`, `§11`, `§13` ("Later in Phase 1: … the heat-debt prototype (D28)").

§2.1: "Not painted into cells: the body doesn't block heat, burn or take damage. Standing in the fire is harmless, a
Known gap until bodies have physics (Phase 4/5)." But `foundations_plan.md` §2 step 10 is the grey-box heat-debt
prototype (D28), right after the tile (step 8) and save v0 (step 9, "save v0 with the actor table", §13). D28 tests
`world_v2.md` §10's claim that "where you are sets how long you can Overdrive: in the rain, longer; in a burning bay,
shorter". That claim needs the body to exchange heat with the cells around it.

Failure scenario, either way it goes:
- Step 10 honours this spec. The heat budget can't depend on the cells, so the prototype becomes a location-blind
  stamina bar. Its playtest verdict can't speak to D28's question, and the owner is told the loop is or isn't fun on
  evidence that doesn't test it.
- Step 10 needs exposure, so it bolts on a player-only heat store: a `heat_j` field on the actor, coefficients in
  `data/world/player.yaml`, a sampled cell temperature at `pos_mm`. That is a second body model. Phase 4's NPCs get
  Maxim's `core_temperature` and `thermal` homeostatic drives (`base_humanoid.yaml`, infant variant; `maxim_senses.md`
  §1). Then the player's heat physics and the NPC's are different code, violating npcs §2.2 ("Overdrive never models
  a drive twice … world-owned and pushed through `world_set_axis`"). Save v0, frozen at step 9 with an actor table
  that has no body state, needs a format bump in the very next step. And sampling the cell at a point is the
  centre-in-cell read CLAUDE.md forbids.

Fix, in the spec now and not in code beyond the schema:
1. State that the actor table is **the one body model for every actor**, player and NPC. Body physical state (heat
   store, later energy store and dose) is world-owned, per actor, in the `Simulation`. Maxim's `Entity` holds only
   what is felt (drives, set points, pain), fed by `world_set_axis` per `boundaries.md` §4.3.
2. Define the body's exchange as a **reduction over a body volume in metres** (the cylinder, or named part volumes;
   see BF-S6), never a cell read, with a closed-form test and a cross-tier test like any physics.
3. Reserve the body-state fields in the actor schema that save v0 carries (version them even if Phase 1 sets the
   exchange coefficient to zero). Then move "the body takes no heat" from "Phase 4/5" to "until step 10", and say what
   D28 reads.
4. Rename `data/world/player.yaml` to a body-type file (for example `data/world/bodies/human.yaml`), with the
   player's *capability* limits (ignite power, rates) kept separate, so an NPC body loads the same file.

---

## SHOULD-FIX

### BF-S1. §11 says an NPC perceives the ignite event "from the same frame and log"

`tile_and_client.md::§11`, second bullet.

The intent log is not a perceptual channel. It is the record of every input, including refused ones (boundaries
§6.2). B-13 (`boundaries.md` §4.4) says a percept is a reduction of registered physical channels at the perceiver's
position and receptor.

Failure scenario: Phase 4 implements this bullet as written. An NPC behind the end wall, facing away, "perceives" the
player's `act ignite` from the log the tick it applies, before any flame, heat or light exists. That is an oracle of
intent, the exact "number it could never sense" the lens asks about.

Fix: replace the bullet: "An NPC perceives the body through the actor table in the published frame, and the fire
through its physical channels (Phase 2 light and sound, heat at the perceiver), never through the log."

### BF-S2. Facing is render-only: the client derives it from interpolated velocity

`tile_and_client.md::§2.1` (actor table), `§4.4` ("Animate walk and turn from interpolated velocity").

The actor table holds `pos_mm`, `held` heading (−1 when stopped) and `path`. It holds no body yaw. The only
orientation that exists is the one the client draws.

Failure scenario: Phase 4. An NPC needs to know whether the player is facing it, which is a social cue and later a
line-of-sight gate (`maxim_senses.md` §2, light row; P-E). Maxim's `azimuth` is head-relative (`base_humanoid.yaml`:
"head-relative azimuth of the current sound", −1 left to +1 right), so computing it for an NPC listener needs that
NPC's yaw in the world. Neither exists server-side. The obvious patch, inferring yaw from the last displacement,
disagrees with what the player sees whenever the client's smoothing differs. An NPC then reacts to "the player turned
away" that the player never saw on screen.

Fix: add `yaw` to the actor table (integer, for example the 8 heading values now, or millidegrees), set by the server
from movement and by a later `turn` intent, kept when stopped. The client draws it and never computes it. Minecraft's
avatar already exposes `turn {degrees}` (`minecraft_player.yaml`, `avatar.turn`).

### BF-S3. Locomotion is two protocol message kinds, not a body affordance NPCs will share; and it disagrees with Maxim's `legs.move`

`tile_and_client.md::§2.2`, `§4.1`, `§4.2`, `§13` (step 7: `move`, `move_to`, `move_result` as message kinds).

`ignite` goes through the one SEM door (`act {region, action, params}` into `engine.intents.parse_action`). Walking
does not: `move` and `move_to` are bespoke protocol kinds with integer-mm targets. Maxim's humanoid body declares
locomotion as an affordance: `legs.move {direction: str, speed: str}`, "north/south/east/west … walk/run/sneak",
`requires: {integrity: 0.1}` (`base_humanoid.yaml`). Minecraft's is `avatar.move_to {x: float, z: float}`
(`minecraft_player.yaml`).

Failure scenario: Phase 4's NPC calls `legs.move {direction: "north", speed: "run"}` through Maxim's
`ModulatorAffordanceTool`. Nothing in the tile's design maps it. The 4 compass words don't match the 8 headings,
"run" and "sneak" don't exist, and `requires` (leg integrity) has no counterpart in the actor's movement. So the NPC
needs a second locomotion path into the `Simulation`, with a second validation and a second log kind. And
`move_result` carries `tick_applied`, which an agent-facing receipt must not carry (npcs §3.1).

There is also a Maxim-side problem the game exposes. `legs.move`'s `direction` is allocentric compass words, and
Minecraft's `move_to {x, z}` takes world coordinates (and bench57 feeds signed world offsets as sensors). Humans have
no compass or GPS sense: they turn and walk relative to the body, or walk toward something they perceive. A player
gets world headings from a camera-relative UI, but an NPC handed world coordinates is reading an oracle.

Fix: (1) Define one body intent, `locomotion` (held direction or target), as the stage-1 kind that both the client's
`move`/`move_to` and an NPC's body modulator reduce to, bound to the actor (boundaries §7.2), with movement gated by
the body's own state (leg integrity once bodies take damage). The wire-only fields (`tick_applied`, `path_mm` for
drawing) live on the client reply, not the receipt. (2) Raise the egocentric-locomotion question with Maxim as a new
Phase 3 item: `legs.move`'s cardinal `direction` and `move_to {x, z}` as allocentric oracles; propose egocentric
`move {forward, turn}` and target-by-percept-id. No OD id covers this today (closest: OD-C8, percepts and instruments);
assign one (for example OD-C11) under roadmap Phase 3 rather than designing around it here.

### BF-S4. `ignite {power_w, duration_s}` lets the actor choose watts

`tile_and_client.md::§2.3` ("the player supplies `ignite {point_m, power_w, duration_s}`"), `§4.3`.

A body chooses where to hold the flame and for how long. It doesn't choose the flame's power: that belongs to the
lighter, torch or cyberware it holds.

Failure scenario: Phase 4. The `ignite` affordance reaches an NPC through `AffordanceSchema.params` with `power_w:
float`. The LLM picks `power_w: 50000` because a big number sounds decisive, clipped only by `player.yaml`'s limit.
That limit is the player's, so which limit applies to an NPC is undefined. Fire becomes a free parameter of
deliberation, not a fact about what the NPC carries.

Fix: put `power_w` (and the pilot's radius or area) on a held igniter item's data. The intent carries `point_m` and
`duration_s` (capped by the item), and stage 2 refuses `no_igniter` when the actor holds none. For the tile, the
player spawns holding one lighter. This also makes D28 and the clinic's "tools as items" consistent.

### BF-S5. The pilot `ignite` is the first slow-effect affordance, and the spec doesn't name the credit divergence

`tile_and_client.md::§2.3`, `§7.2` (tick 70: "success").

`ignite`'s receipt reports success when the pilot is placed. Whether the crate catches is decided by step 6's law,
seconds to minutes later.

Failure scenario: Phase 4. Maxim books the `act_result` success at dispatch. `boundaries.md` §7.2 records D53's
default as a silent POSITIVE valence (BF2-3), so an NPC is credited for a pilot that failed to ignite (one below the
band, held too short). It learns that holding a lighter to a crate for 0.2 s works. This is the tile's own scenario,
and the game's first concrete evidence for OD-A16 (slow-effect credit) and OD-C5 (`ModulatorResult.settles`).

Fix: in §2.3, state that `act_result.success` means "accepted and applied", not "ignited"; name the divergence as
OPEN with OD-A16 and OD-C5; and record the tile's numbers (pilot duration against time to sustained burning, once
step 6 has them) as evidence in the OD-A16 draft. Correct `StructureModulator.affordances["ignite"].description`
("burns until extinguished") in the same PR as the params change.

### BF-S6. One cylinder can't carry the receptor volumes Phase 4 needs, and a head-sized volume is under two coarse cells

`tile_and_client.md::§2.1` (collision volume), `§2.2` ("a reduction over the body's volume in metres").

`maxim_senses.md` §4 step 3 sets the rule for every body sense: "a volume average over a body-part sphere at least
two coarse cells across", per part (head, torso, arms: `arms.thermal`, `head.thermal`). The spec has one collision
cylinder, 0.5 m across. A human head is about 0.2 m across (*from memory, to verify*), which is one cell on the 0.2 m
verification grid. The tile's own verification grid would then fail the outcome-class agreement for any head-level
reading near the fire front.

Failure scenario: D28 or Phase 4 adds `head.thermal` as a 0.2 m sphere. At 0.2 m it reads one cell's mean; at 0.1 m,
eight. The burn integral's outcome class (burned or not) flips between grids near the threshold. Either the
cross-tier test is loosened (forbidden) or the sphere is inflated to 0.4 m (no longer a head).

Fix: name receptor volumes as part of the body type (BF-B2 item 4), separate from the collision cylinder, with each
volume's size in metres. Record now, as a Known gap, that head- and hand-scale receptors fall under the two-coarse-cell
rule and will need the reconstruct-then-integrate path (CLAUDE.md: sub-cell profile from neighbours, then integrate)
rather than a plain cell average. The physics lens should own the method; this lens needs it named before the body
schema freezes in save v0.

---

## NIT

### BF-N1. The sky follows a "time of day" nothing defines, and it contradicts a fixed night ambient

`tile_and_client.md::§1.2`, `§11` ("a later SCN entrained by world light shares the player's day").

No protocol field or scene key defines the world's day (an epoch hour, a day length). §1.2 also fixes ambient as
"low (night)". If a `time_of_day` field is added to `tick` for the sky, it is one step from a percept that hands NPCs
the exact phase (npcs §3.1, §3.3; "no calendar"). Fix: in Phase 1, either a fixed night sky, or the world's day defined
once in `data/world/` as the future light field's source. Reword §11: the SCN entrains on the Phase 2 light field at
the perceiver, never on this number or the client's sky.

### BF-N2. Per-session rate limits are wall-time flood guards, not body limits

`tile_and_client.md::§2.3` ("≤ 1 ignite per second per session"), `§4.1` ("≤ 30 per second per session").

Say they are transport-layer guards on wall time, outside the world. What a body can do (one live pilot per actor, a
re-strike time on the igniter) is in world time on the actor, so a 20× dial doesn't let the player strike 20 times
faster per world second, and NPCs, which have no session, get the same body limits.

### BF-N3. `actor_id` is an allocator integer; say it is not identity

`tile_and_client.md::§2.1`.

npcs §3.4 keys NPC randomness and persistence by `npc_key` from the roster, "not the actor allocator's integer".
State that `actor_id` is session-scoped and that save v0 maps a body to a persistent key, so the actor table isn't
mistaken for the identity Phase 4 seeds streams from.

### BF-N4. `extra={"cell_size_m"}` and `metadata["cell_size_m"]` are still on the bridge this tile edits

`src/maxim_overdrive/sem_env/bridge.py::RegionSensor.read`, `to_maxim_entity`.

§2.3 changes the bridge's `ignite`. Boundaries §4.4 and npcs §7.3 drop `cell_size_m` from readings and entity
metadata. Under D20 it is constant (0.1 m), so it is no longer a tier leak, but it is still resolution in front of
cognition. Drop it in the same PR, or list it in §13 with the boundaries PR that does.

---

Verdict: not ready to build; fold BF-B1 (perceivers must read a deterministic, per-change actor table, never the
throttled wire) and BF-B2 (one world-owned body model with heat state, before save v0 and D28) first.
