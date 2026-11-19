# Tile and client spec, v1: Architecture lens

Target: `docs/design/tile_and_client.md` at f6afd66 (`phase1/tile-spec`). Read against `docs/code_review.md`,
`CLAUDE.md` (and `phase1/standards:CLAUDE.md` for separation of concerns and the size tripwires),
`docs/design/boundaries.md` (O23, O24, §2.1 placement table, §2.2 layers, §4, §6.1, §8), `docs/design/world_model.md`,
`docs/plans/foundations_plan.md`, `origin/phase1/realtime-design:docs/design/realtime_lanes_coop.md` §2.1, and today's
`src/maxim_overdrive/world/{world,heat}.py`, `docs/architecture.md` Known gaps, `data/materials/core.yaml`.

Counts: 3 BLOCKER, 10 SHOULD-FIX, 5 NIT.

## BLOCKER

### AR-B1. The new mechanism has no home, and the spec names a layer map the owner retired
`tile_and_client.md::§2.1, §2.2, §4.2, §5.1, §5.4, §1.3`

The spec adds the first engine mechanism since the boundaries design: an actor table with bodies, a "move bodies"
tick stage, collision and sliding, a walk grid, A\* with snapping and line-of-sight pruning, a heading table, a
`player.yaml` loader, scene spawns, an actor table in the frame. It places none of them in a package or layer. The
only placements it gives are `engine.intents`, `engine.encoding` and `engine.tiers`. Those come from boundaries
§2.2's twelve-layer table, which O24 turned into "the map of where splits are expected to fall". O23 also renamed the
package `simcore`. Step 3a builds `simcore` with 3–4 layers (core, adapters, game, client protocol) before step 8
writes any of this. So the spec's own placements point at modules that won't exist.

Failure scenario: at step 8 the author puts A\* "on the server" in the host layer, next to sessions and
`TimeAuthority`, because the spec says only "pathed on the server". The host is outside the sealed core (§3), so the
banned list and the AST scan don't cover it. A replay drives `Simulation` without a host, so it never replans, and
§4.5's bit-identical replay fails. Or the planner goes in the game package, being "this game's movement". Then a game
callable runs inside `Simulation.step`, which boundaries §2.1 forbids ("game rules reach the tick as data only").
Either way, a review at code time, not here, decides the boundary for the first new mechanism.

Fix: add a placement table to the spec, one row per new thing, with the `simcore` layer it lives in under O24 and
its data owner. Proposed: the actor table, the bodies, collision, sliding, the walk grid and A\* go in the sealed
core next to `Simulation`, since they are mechanism, deterministic, and on the simulation lane. Typed `move`/`move_to`
go with the intents. The heading table and body parameters are data through a loader gate. Frame actor encoding is
protocol. Spawn validation is construction (AR-S9). Replace every `engine.*` name with its `simcore` home.

### AR-B2. Movement bypasses the one pipeline it claims to use
`tile_and_client.md::§0 T2, §2.3 ("One door"), §4.1, §4.2, §13`

T2 says movement goes "through the one intent door". The spec writes the door out only for `ignite`: stage-1
`parse_action`, then the log, then stage 2. `move {heading}` and `move_to {target_mm}` are specified as protocol
message kinds, with validation ("integer in [0, 7] or null", "re-validated") given no layer. §13 defers them to step
7 "as message kinds". None of them is in boundaries §6.1's authority table or in §6.2's `kind_rank`. `move` is also a
new kind of input: held state applied on every later tick, not an instantaneous intent. The log record (§6.2) has
no field for that, and the frame-cadence rule (§5.3, "each tick that applied an intent") doesn't account for it.

Failure scenario, Phase 4: an NPC must walk to the crate. NPCs act only through SEM affordances into `parse_action`
(boundaries §5.3, NPC tool calls), and no affordance moves a body. So locomotion needs a second door, through the
adapter, with its own validator. That breaks rule 1 of §6.1: "NPC and player intents share the validators and the
log". Today, in Phase 1, `move_result` is a second receipt shape next to `act_result`. And §4.2's "topology change
replans once, else the body stops with `path_blocked`" happens after `move_result` was already sent. It has no reply
and no record. Every client message gets exactly one final reply (realtime §1), and this stop is a world event the
client can't learn of.

Fix: define `move` and `move_to` as `simcore` intent kinds with typed canonical params, stage-1 parsing, an
authority row ("any actor") and a `kind_rank`. Make the wire messages thin encodings of those kinds. Choose one
receipt shape for all intents. Make the `path_blocked` stop a derived per-tick output (an actor event in the `tick`
message and the frame), not a second reply. State that NPC locomotion needs a body-level affordance on Maxim's side,
recorded as a Phase 3 item, so Phase 4 doesn't grow a workaround door.

### AR-B3. The burn's energy has no named destination, so the exit's control assertions rest on an unnamed leak
`tile_and_client.md::§1.2, §7.3 (items 5 and 7)`

The spec correctly says that "open air" here means no O₂ limit, not an open heat boundary. Its consequence ("the
tile's air stays hot") doesn't follow. The crate is a solid 0.216 m³ of wood, 130 kg at 600 kg/m³ (`core.yaml`),
which is about 2.2 GJ at about 17 MJ/kg (heat of combustion *from memory, to verify*). Heat leaves an insulated
extent by no route: no convection, no radiation, air conductivity 0.026 W/m·K. World_model §4 holds the ledger to a
relative 1e-12 per substep. A burn law that conserves energy (step 6) must therefore put 2.2 GJ into cells near the
crate, mostly into the floor beneath it.

Today the books balance only through another Known gap the spec never mentions: "Destroying a cell removes its heat
with it". That is a silent sink.

Failure scenario: step 6 writes an honest burn law. The floor under the crate passes 300 °C over a large area, the
floor's integrity falls below 0.95, and the test fails. §7.3 item 7 already hedges this: "measured first, recorded
with the threshold". The threshold gets set to whatever the leak-dependent run produced, which is a loosened gate by
another name. The other way, step 6 tunes a heat-release fraction so that the walls survive. That is a calibration
hiding a missing physics term, a band-aid the spec has invited by leaving the destination to "the burn law".

Fix: decide in this spec, as architecture, where Phase 1 combustion energy goes. The physical split is world_model
§3's: a flame-feedback flux deposited on the fuel surface, with the rest of the heat release carried off by the
plume. Model the remainder as an explicit, metered "plume exhaust" sink term in the energy ledger. Mark it
`TEMPORARY(phase2)` until the zones and convection work removes it, and record it in Known gaps with the tile's
numbers (the energy exhausted versus deposited). Close or quantify "destroying a cell removes its heat": a destroyed
cell's sensible heat goes to its neighbours or to the same metered sink, never nowhere. Set the floor threshold of
§7.3 item 7 from the physics before measuring, not from the first run.

## SHOULD-FIX

### AR-S1. "Player" is a special case where the engine needs a generic body
`tile_and_client.md::§2.1 (Data), §1.3 (spawns), §2.3 (limits), §11`

Body parameters, reach and pilot limits live in `data/world/player.yaml`, and the spawn is `name: player`.
Boundaries §6.1 rule 3 says capability comes "from the body". §2.1 says body grammar is engine and body instances
are game. Phase 4 NPCs are actors through the same applier. With a player-named file, the first NPC needs either a
second file and loader or an `if actor is player` branch at stage 2, where reach and pilot limits are checked.

Fix: the engine defines a body archetype type (radius, height, speed, reach, capability limits) with a strict
loader. The game supplies instances, `player` being one. The actor table holds an archetype id, and a spawn names an
archetype, not a role.

### AR-S2. Actors in the frame break publish-on-change (O23), and the actor table sits outside the write ownership
`tile_and_client.md::§5.3, §2.1, §11`

§5.3 puts the actor table in "the published frame, so a Phase 4 perceiver reads bodies and cells from one frame".
Bodies change every tick while anyone walks. Boundaries §4.2 publishes frames on cell change only, precisely because
a full-grid copy is 64–80 MB, and O23 fixed that. The design can give either a fresh frame every tick while walking,
which is the per-tick copy O23 rejected (13–16 GB/s at 20×), or a frame whose bodies are up to 5 ticks stale while
the `tick` message shows them current. In that second case the player and an NPC see different worlds. Separately,
§5.3's wire trigger "each tick that applied an intent" sends a 1.15 MB cell frame for a `move`, which changes no
cell. Realtime §2.1 has the right trigger: "when cells' version changed". Boundaries §4.1 also covers only core
arrays, so the actor table is new mutable core state with no stated owner or guard.

Fix: split the frame. Keep the cell part as a copy on cells' version, shared by reference between publishes, and add
a small per-tick body table, both stamped with the same tick. Trigger wire cell frames on cells' version alone. Bring
the actor table under the same ownership rule: a frozen per-tick table replaced by `Simulation.step`.

### AR-S3. Bodies are perceivable only through an omniscient table, which B-13 forbids
`tile_and_client.md::§5.3, §11`

B-13 (boundaries §4.4) says a percept is a reduction of registered physical channels at the perceiver. The body "is
not painted into cells" and there's no light field. §11's "an NPC perceives the body ... from the same frame" means
reading positions from a table, the omniscient membrane BF-7 removed.

Fix: register body occupancy (the cylinders) as a physical field in the registry, so that a future percept reduces
it at the perceiver, behind a line-of-sight gate once light exists. Name the interim state as an ANALOG divergence.
Say that the actor table is the host's and the client's view, not a percept source.

### AR-S4. Two definitions of "blocked" will disagree, and the tolerances will hide it
`tile_and_client.md::§2.2 (Blocked), §4.2 (Walk grid)`

Stepping uses a disc–square overlap in integer mm over a z-band. The walk grid uses a "disc convolution of column
occupancy" on a 0.1 m node lattice. These are different predicates with different discretisations. A node can be
free while a 140 mm step from it into the next free node clips a corner the convolution rounded away. The body then
slides or stops mid-path, `arrival within 50 mm` misses, and a replan fires. The 50 mm tolerance and "replan once"
then absorb a predicate mismatch.

Fix: build one blocked predicate and derive the walk grid from it (a node is free if and only if the step test
passes at its centre), and check each path segment with the same test. Add a property test: every step along a
planned path passes the stepping predicate.

### AR-S5. Glow, and the proposed `fire`, are encoded from cell means, which is part of why glow is dim
`tile_and_client.md::§5.1, §6.4, §12 Q4`

`glow` is `clip((T − 525)/975)` on the cell-mean temperature, a threshold on a mean (D25). §6.4 blames the dim glow
(3 and 23 of 255) only on the physics. Part of it is the encoding: a wood cell degrades away from 250 °C while its
surface is far hotter than its mean. Step 6 brings surface state as a per-face table (world_model §8, DLP S-11), and
the exit's "watch it glow" is a surface phenomenon. Encoded from the mean, glow can stay under the §7.3 threshold
when the surface is above it. Then the pressure to rescale returns, and §6.4 rightly forbids rescaling. `fire` as "u8
heat release per volume" per cell repeats the error for a surface process.

Fix: define `glow` and `fire` from the per-face surface state when step 6 provides it, encoded by the protocol layer
per exposed face, or reduced to the cell's exposed area and named as such. Give them new channel names if their
meaning changes (world_model §8, "a name is an identity").

### AR-S6. The engine/game split of data and client is ignored
`tile_and_client.md::§1.3, §2.1, §1.1 (Material), §9.1`

Boundaries §2.1 assigns "this game's content: the tile, its scenes ... calibrations" to the game, and §8's data table
puts calibrations under `content/` (rights reserved). It also says the game package is born with the first content.
D26 made the alley that first content. Yet the spec puts `alley.yaml` in `data/scenes/`, `player.yaml` in
`data/world/` (the engine's directory, next to the Apache-2.0 `actions.yaml`), and the fuel calibrations in
"material table v1", without the material split. Its Godot tree (`client/scenes/`, `protocol/`) ignores boundaries'
`client/addons/engine/` (decoder, channel bindings) and `client/game/` (scenes, UI).

Failure: the wheel check (boundaries §8) ships game content under Apache-2.0, or step 8 creates the game package
silently.

Fix: state that step 8 creates the game package and `content/`; place the alley, the player archetype values and the
fuel calibrations there; split the client tree as boundaries requires.

### AR-S7. Godot-only rendering knobs placed in the Python engine
`tile_and_client.md::§5.4`

`scaling_3d_scale`, crack substeps, bloom, AO taps and particle counts go "to rendering data under `engine.tiers`".
The server uses none of them. Under D20 every tier gets the same 0.1 m channels, so `encoding`'s reason to depend on
tiers is gone too. Putting them in the engine couples a shader retune to an engine release and leaves unsaid how the
client gets them: `welcome`? a file?

Fix: the rendering-tier table lives in `client/` as typed project data. The server keeps no tier knowledge beyond
what the client reports for metering. Drop the `encoding → tiers` dependency.

### AR-S8. The movement vocabulary is shaped by the camera
`tile_and_client.md::§2.2 (Headings), §4.1, §13 (gamepad)`

Eight headings exist because the camera yaws in 45° + k·90° steps, and the spec already foresees that a gamepad
forces "a versioned change". Step 7 freezes this vocabulary with golden fixtures, and NPC locomotion (Phase 4) has no
reason to be 8-way.

Fix: put an integer direction on the wire and in the intent (`dir: [dx, dy]`, normalised in the core with integer
`isqrt` to the speed). Let the client quantise WASD itself. Keep the diagonal-step table as a derived cache, not a
vocabulary.

### AR-S9. Spawn validation "on free floor" is a layer inversion
`tile_and_client.md::§1.3`

The scene format sits below the simulation (boundaries §2.2, 5a). "On free floor" needs the built grid and the body's
cylinder, so `Scene.from_dict` would have to import the body archetype and the collision predicate.

Fix: the scene format validates only extent and syntax. Construction (`Simulation.from_scene`) and `join` apply the
blocked predicate (AR-S4) for the joining archetype and refuse loudly.

### AR-S10. A §7.3 assertion cannot fail
`tile_and_client.md::§7.3 item 5`

"From `t_gone` + 600 ticks the tile's maximum only falls." With the boundary insulated, no sources (asserted in the
same item: `fire` is zero) and a stable explicit scheme, the discrete maximum principle guarantees it. The charter
makes a test that cannot fail a BLOCKER once it is code.

Fix: replace it with an assertion that can fail, such as total energy staying flat to the ledger tolerance after
`t_gone`, plus the metered exhaust of AR-B3 being zero then.

## NIT

### AR-N1. A sentinel in a typed field
`tile_and_client.md::§2.1`

The `held` heading is "int8, −1 none". Push the invariant into the type instead: `heading: Heading | None` in a frozen
record, and an encoded sentinel on the wire only.

### AR-N2. The "one shader" is one shader with seven jobs
`tile_and_client.md::§6`

DDA traversal, Voronoi crack carving, lighting and AO, emission, cut-away, the ID pass and the temperature debug view
all sit in one fragment shader. Split it into `.gdshaderinc` includes, one concern each, so that the goldens'
proof-by-deletion (§8.2) deletes one include.

### AR-N3. Name the modules, so the tripwires are planned for, not hit
`tile_and_client.md::§2.2, §4.2`

Collision and sliding, the walk grid, A\* (with its tie-breaks, snapping, the 10,000-expansion cap and LOS pruning)
and replanning are four responsibilities. Put them in two modules (body motion; navigation), with A\*'s snap and
prune as separate functions. Otherwise the planner reaches ruff's complexity cap of 10 and the 40-line body limit on
the first draft.

### AR-N4. The point check is still the bounding box
`tile_and_client.md::§2.3`

"On the region's authored footprint" is the bounding box until the Phase 2 CSG (world_model §5). That is exact for
the box crate. Say so, and that a non-box fuel prop waits for the CSG.

### AR-N5. Pilot lifecycle
`tile_and_client.md::§2.3`

"One live pilot per actor" needs sources keyed by actor and an end on every exit path: expiry, the actor leaving,
the region being destroyed. Each end should be a derived output, like the AR-B2 stop.

Verdict: not ready to build. Fold AR-B1–B3 (placement, one pipeline for movement, the combustion energy sink) before
step 5 depends on the tick order and step 6 on the burn's energy books.
