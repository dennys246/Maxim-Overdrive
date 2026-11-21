# Architecture (v0, 2026-11-14)

Maxim Overdrive is a cyberpunk RPG set in **Maxim Prime**, where every NPC is a [Maxim](https://github.com/dennys246/Maxim)
agent with a life it actually lived. This file records the foundations and why they were chosen.

## The split: an authoritative world server, a client that only draws

```
Godot client (render, input, UI)  ──intents──▶  World server (Python, authoritative, fixed turn)
                                  ◀─snapshots──    ├── material grid (cells)
                                                   ├── physics fields (heat today)
                                                   ├── damage
                                                   ├── SEM bridge  ──▶  Maxim agents (a worker each)
                                                   └── imagination specs → cells
```

- The world server owns all state and all physics. The client never simulates anything that feeds back into the
  world. It may add purely visual effects (particles, debris, interpolation between frames).
- Cradles and experiments run the same server headless. The physics an NPC grows up in is the game's physics.
- Real time with pause; late thoughts dilate, hold the floor or land late (`npcs_and_sem.md` §4.4).

## The world is material cells

`simcore/core/grid.py` holds the world as a structure of arrays: per cell, a material id (`uint8`), integrity in [0, 1] and
temperature in °C. Scenes are **authored in metres** (`simcore/core/scene.py`) and voxelized at the grid spacing the world
is given (`dx_m`). Nothing is authored in cells.

Materials (`data/materials/core.yaml`) carry textbook thermal properties plus two gameplay calibrations that are
always **per unit volume** (`fracture_energy_j_m3`, `degrade_*`), so they mean the same thing at every resolution.

## The verification rule

The rule is stated in `docs/design/world_model.md` §1.1. Two tests per module, through `simcore.verify`
(`docs/design/verify_harness.md`):

1. **Against a closed form,** space and time refined apart (E2). Heat: a steel bar's Gaussian pulse, second
   order in space (errors 1.29% / 0.34% / 0.085% at 0.2 / 0.1 / 0.05 m) and first in time. Damage: crater volume
   against `analytic_crater_radius_m` (within 5%).
2. **Across grids,** gated on agreement and convergence (`tests/test_cross_tier.py`).

How the rule is kept, so far:
- Energy lands by **exact cell average** (a strike's Gaussian integrated over each cell) or by **volume overlap**
  (a fire's sphere, sub-sampled), never by "is the cell centre inside". Centre-inside made a 0.3 m fire run 35%
  cooler at 0.2 m cells than at 0.05 m, and the crate burned at one rig and not another.
- SEM sensors are **reductions over cells** (mean integrity, mean and max temperature). Means converge with
  resolution; a max doesn't have to (`temperature_max` mid-burn differs across rigs, see Known gaps), so decisions
  are taken on means or integrals, as the "reconstruct, decide, integrate" rule in CLAUDE.md requires.
- Thin features must be at least two of the coarsest rig's cells thick, or one cell becomes the whole feature and a
  scratch becomes a breach.

**Known gaps (tracked, not gated yet):**
- NPC inference (no streaming yet, load versus failure, first hops, spend): `docs/design/inference_placement.md` §6.3.
- Late in a burn the coarsest rig lags (crate integrity 0.55 at 0.2 m vs 0.37–0.38 at 0.1 and 0.05 m after 150
  turns): a coarse cell degrades as one block. Onset agrees to within 5%. It falls below 0.7 at turn 138 at 0.2 m
  against 104 at 0.1 m. Red gate: `tests/test_cross_tier.py::test_the_crate_is_badly_burned_at_the_same_turn_at_every_rig`.
- No convection or radiation: air only conducts, so rooms heat too slowly and fires must sit on a material.
- Destroying a cell removes its heat with it (the cell becomes air at the air's heat capacity).
- **Fires don't consume fuel: once nothing solid is left under a fire, it heats air.** `World._power_field` spreads a
  fire's power over the solid cells its sphere overlaps, and falls back to the air cells when there are none. Air has
  about 1/1000 of wood's ρc, so the runaway is enormous. On the 3×3×2 m crate scene at 500 kW, radius 0.3 m: the
  crate is gone by turn 50 at 0.2 m cells, and the peak is 207,350 °C at turn 50 and 2.67 million °C at turn 200;
  at 0.1 m it is 361,913 °C at turn 50 and 2.67 million °C at turn 200. The snapshot clamps temperature at 6000 °C,
  so the client never sees the overshoot, but the heat is real and conducts onward. The fix is a fire that goes out
  when it has nothing to burn. It blocks the exit test's "burn away", so it lands before the tile's crate scenario
  is gated. Red gate: `tests/test_cross_tier.py::test_a_fire_that_has_burned_its_fuel_stops_heating`
  (`xfail(strict=True)`).
  *Fixed 2026-11-15, the other half:* power went into cells destroyed mid-turn (16,619 °C by turn 30); it is now
  recomputed after any substep that destroys cells (peaks 538 °C at 0.2 m, 613 °C at 0.1 m). Guards: `tests/test_heat.py::test_a_cell_destroyed_mid_turn_gets_no_more_source_power`
  and `tests/test_cross_tier.py::test_a_fierce_fire_never_heats_any_cell_past_the_flame_temperature`.
- **A source smaller than a cell heats one cell.** `World._power_field` puts all of a sub-cell source's power into
  the cell it sits in, so total power is right but its density is P/dx³: 64× higher at 0.05 m cells than at 0.2 m.
  Peak temperature near a spark therefore depends on the rig. *Closed for actions (2026-11-15):* an `ignite` must
  have a radius of at least 0.3 m and a `strike` a width of at least 0.2 m, the coarsest rig's cell
  (`data/world/actions.yaml`, held by `tests/test_act_validation.py`). A `HeatSource` built directly in code can
  still be smaller.
- **Fires diverge across rigs mid-burn, so fire outcomes don't yet keep the verification rule.** Measured at the
  largest fire actions allow (500 kW, 0.3 m radius) on the 3×3×2 m crate scene, recording crate integrity every
  turn: the spread across laptop / rig / max exceeds 0.1 on every turn from 18 to 27 and peaks at 0.19 at turn 22
  (0.70 / 0.57 / 0.51). It narrows near turn 30 only because the curves cross, and from about turn 30 the fuel gap
  takes over (at 40 turns, integrity 0.02 / 0.26 / 0.34 and peaks of 620 / 1.4×10⁵ / 1.4×10⁵ °C). Smaller radii or
  more power diverge sooner: at a 0.2 m radius the onsets are 11 / 8 / 7, and at 1 MW integrity at turn 30 is
  0.00 / 0.26 / 0.34. `temperature_max` diverges too (540 / 614 / 978 °C at turn 27). **The cause is measured:**
  the crate's mean temperature agrees between laptop and rig to within 1 °C through turn 22, so the crate's heat content agrees, but
  the degradation driver (the mean of the excess of each cell's temperature over the limit, in
  `damage.thermal_degrade`) is 1.3–1.5× larger at rig. The law does converge, slowly (integrity at turn 22 is 0.703 /
  0.567 / 0.514, roughly first order), but the coarse rig sits far off, because a threshold is applied to cell means
  (CLAUDE.md, "Reconstruct, decide at the point, integrate upward"). Scaling the rate by cell size would make the gate pass and is a band-aid; the law itself is held by a
  closed-form test at every rig (`tests/test_validation.py::test_thermal_degradation_follows_its_closed_form_at_every_rig`). The fix is the Phase 1 fuel model, with burning as a
  rate driven by heat content. Held by a strict red gate that checks the spread on every turn for 60 turns,
  `tests/test_act_validation.py::test_the_fiercest_allowed_fire_has_the_same_outcome_at_every_rig_on_every_turn`.
  Until then, `ignite`'s ceilings in `data/world/actions.yaml` (at most 500 kW, a radius of at least 0.3 m) keep
  fires at the powers this physics has been measured at; they make no claim about agreement across rigs.
- **Strikes near the fracture threshold, and breaches of thin walls, flip across rigs.** Below the threshold nothing
  is destroyed at any rig, a guarantee of exact cell-average deposition. Craters with a closed-form radius of at least
  0.33 m (about 1.7 coarse cells; 4× the threshold and above at the 0.2 m minimum width on concrete) match the closed
  form within 25% at every rig. Between the two they don't: destroyed volume at laptop / rig / max is 0 / 0 / 0.001 m³ at 1.05× the
  threshold (about 2.5 MJ), 0.008 / 0.032 / 0.026 m³ at 1.5×, and 0.152 / 0.088 / 0.114 m³ at 3× (closed form
  0.109 m³). The crater radius goes to zero continuously at the threshold, so no minimum width removes the band.
  What an NPC acts on flips too: a 0.4 m concrete wall whose faces sit off the 0.2 m grid, struck at 1.5× the
  threshold, is breached at rig and max but not laptop (a strict red gate,
  `tests/test_act_validation.py::test_a_strike_breaches_a_thin_wall_the_same_at_every_rig`). How the resolution
  rule should treat outcomes at a class boundary is an open decision.
- **A destroyed region still claims its space,** for strikes and for imagined objects alike (`spec.place` refuses
  a new object inside a burnt-out crate's old box). A crate burned to nothing still owns its authored box: a strike there
  is "on the crate", and `ignite` puts the fire into air. "Gone" only means a later paint took every cell. Ownership per cell (the region id array planned
  for design v2) removes it.
- **Overlap is judged on bounding boxes, and it has an authoring cost.** Named solids may not overlap a later solid
  (`scene._check_no_solid_overlaps`, and `imagination.place` for imagined objects), and a cylinder's box corners
  count as its own, so two barrels close together can be refused although they don't touch. A solid window, sign or
  vent inside a named wall is refused too, so such a wall must be split into pieces or left unnamed. Per-cell
  ownership (design v2's region id array) removes both.
- **A region carved hollow keeps its authored centroid.** Air may carve into a named solid (a doorway), but the
  solid's footprint and centroid stay those of the authored box. With a doorway through a wall's middle, the
  centroid is in air: `ignite` puts the fire in the doorway, where it heats only air, and an aimless strike lands
  there too. Refusing such a fire by its cells was tried and withdrawn: off the coarse grid that decision
  depends on the rig (a 0.33 m fire was accepted at laptop and rig, refused at max). Held by a strict red gate,
  `tests/test_act_validation.py::test_a_fire_on_a_region_carved_hollow_heats_the_region_not_air`. Per-cell ownership
  with authored geometry (design v2) removes it.
- **Whether an imagined object fits in the world can depend on the rig.** `imagination.place` refuses an object
  "smaller than one cell at this resolution" when it covers no cell centre, which can happen at the coarse rig and
  not at a finer one. Its size and mass budgets are rig-independent; this check
  isn't. The thin-features rule (two coarse cells) as a minimum authored size
  would remove it.
- **A region's temperature reading can leave its declared range.** `RegionInstrument` declares
  `temperature_max` as [-273, 6000] °C, but the fuel gap lets legal fires drive cells far past that (about 4×10⁵ °C
  after 60 turns of a 500 kW fire, once the crate has burned away). The reading isn't clipped, because clipping
  would hide the gap; the fuel model is the fix.
- **Physics runs slower than real time at tile scale.** `advance(0.5)` takes 0.7 s of CPU at 1.92×10⁶ cells (a
  40×8×6 m tile at 0.1 m) lightly loaded, 1.4× real time (about 3.6× at 5×10⁶ by scaling); under heavy load 1.2–1.45 s
  (2.3–2.9×) and 3.9 s at 5×10⁶ (7.7×). Main is the same (`process_time`, min of 2–5 runs; step 3b). 0.05 m is about
  60× slower than 0.1 m. Step 5a owns it (B5); far cells never run coarser (D21).

## SEM for the environment

`simcore/adapters/sem/bridge.py` makes any named region (a wall, a door, an imagined crate) an SEM Entity: instruments `integrity`,
`temperature_max`, `temperature_mean` and `breached`, and a `structure` modulator with `strike`, `ignite` and
`extinguish`. With pymaxim installed, `to_maxim_entity` returns a real `maxim.embodiment.sem.Entity`, so Maxim's tool
generation, affordance gating and prompt formatting work on the environment unchanged. The environment has no drives,
pain or learning: it is SEM without embodiment.

**The modulator is a trust boundary.** An NPC's tool call, an LLM's output and a client's intent all reach the
world through it, so it works in two stages. `parse_action` turns the untrusted `(affordance, params)` into a frozen
`Strike`, `Ignite` or `Extinguish` inside the world's `ActionLimits` (`data/world/actions.yaml`), reading nothing from
the world, so the protocol layer can run it first. The applier re-checks the action against the
limits, then checks what depends on the world now (the region still has cells, a strike's point is on the region, judged
from authored footprints in metres so the answer is the same at every spacing). A region is its cells plus its authored
footprint; named solids can't share space with a later solid, so a footprint never covers another object's cells.
Parameters are a closed set per affordance, plus the keys Maxim adds itself (`target`). Every number is a finite real
number: NaN, infinities, bools and numeric strings are refused, never guessed. A refusal names the parameter in plain
words and changes nothing. The physics checks again underneath: `HeatSource` and `damage.strike` refuse non-finite
and negative values, whoever calls them. The limits are physics-safety ceilings, not what a body can do; an NPC's
capability will come from its body and energy (`docs/roadmap.md`, Phase 5).

Actions change cells; only `World.advance` moves time.

## Fine-scale state drives graphics

`encoding.snapshot` quantizes per-cell state into arrays a client uploads as 3-D textures: `material`, `crack`
(1 − integrity), `glow` (from 525 °C, near the Draper point, to 1500 °C) and `temperature_c`. Shaders read them
directly, so the finest physical state shows up as cracks, scorch and glowing metal without the renderer knowing
any physics. The cell size sets the finest detail physics can drive; the client can add sub-cell detail (noise,
decals) that is purely visual.

## Transport: WebSocket on localhost (decided 2026-11-15)

The client and server talk over one WebSocket. Snapshots go as binary messages (a JSON header plus the per-cell
arrays), and intents go as JSON text messages. The protocol is defined apart from the transport, so swapping the
transport later means replacing one adapter on each side, not the message format or its tests.

**Why not a raw TCP socket.** At 5 bytes per cell, a 16×10×4 m tile is about 0.4 MB at 0.2 m cells, 3.2 MB at
0.1 m and 26 MB at 0.05 m. On localhost either transport moves that in tens of milliseconds, far less than a turn of
physics. WebSocket frames each message for us (raw TCP means hand-written length-prefix reassembly in GDScript),
is inspectable with `websocat`, is built into Godot 4 (`WebSocketPeer`), and alone suits a web export or `wss://`.

**What it costs, and what we do about it:**
- *Any web page can open `ws://localhost`.* Browsers allow cross-origin WebSockets, which a raw socket would not.
  The server binds to `127.0.0.1` only, refuses any handshake that carries an `Origin` header (browsers always send
  one; Godot's native `WebSocketPeer` sends none unless told to, to be confirmed in step 2), and requires a
  per-launch token. Each refusal has a test (`docs/standards_backlog.md` B14). A web export would send its page's
  `Origin`, so supporting one would mean an Origin allow-list, which is a protocol change made deliberately, not a
  relaxed check.
- *Head-of-line blocking.* WebSocket runs over TCP, so a large snapshot delays any small message queued behind it.
  That is harmless for a turn-based game. Continuous streaming would need delta snapshots or chunking.
- *Whole messages are buffered.* Both ends must raise their default caps (Godot's `inbound_buffer_size` is 64 KiB;
  Python `websockets`' `max_size` is 1 MiB). Multi-tile worlds at 0.05 m would need deltas, as any transport would.
- *Not for real-time internet play.* Fast multiplayer would want UDP (Godot's ENet). Out of scope.
- *The faster local option is shared memory, not raw TCP.* Godot needs a GDExtension for it. A Phase 2 "Scale"
  item only if profiling asks for it.

The snapshot header reserves a compression field from v0, plus each array's uncompressed byte size, which Godot's
`PackedByteArray.decompress(buffer_size, FileAccess.COMPRESSION_ZSTD)` needs. Most cells are air, so zstd should
shrink snapshots by 10× or more.

## Imagination: specs, not assets

`simcore/core/imagination.py`: an imagined object is a spec of primitives made of known materials. Before it exists it must
pass the world's rules (known materials, size, mass budget, free space); then it is voxelized like anything authored,
so it burns and breaks like a real object. The plan for every asset type follows the same pattern: generate a
**validated spec**, then derive the asset deterministically.

| Asset | Generated (LLM) | Derived (deterministic) |
|---|---|---|
| Geometry | primitives + materials | cells; client mesh from cells |
| Look | material choice, wear | colour, crack and glow channels from the material table and cell state |
| Sound | material choice | impact and burn sounds synthesized from material properties (planned) |
| Text | names, inscriptions, lore | — |
| NPCs | cradle events | Maxim memory and learned state (the cradle) |

Image-model assets (textures, portraits) can be added later as cached decoration; they never decide physics.

## Licensing

Code: Apache-2.0 (`LICENSE`). Story, characters, lore, art and audio: all rights reserved (`ASSETS_LICENSE.md`).
