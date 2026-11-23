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
  are taken on means or integrals, as the "reconstruct, decide, integrate" rule (`docs/design/world_model.md` §3)
  requires.
- Thin features: the rule and its fuel-object exemption are `docs/design/world_model.md` §1.1's.

**Known gaps** are kept in `docs/known_gaps.md`, their one owner (moved there on 2026-11-22). Every gap carries its
numbers and the step that closes it.

## SEM for the environment

`simcore/adapters/sem/bridge.py` makes any named region (a wall, a door, an imagined crate) an SEM Entity: instruments `integrity`,
`temperature_max`, `temperature_mean` and `breached`, and a `structure` modulator with `strike`, `ignite` and
`extinguish`. With pymaxim installed, `to_maxim_entity` returns a real `maxim.embodiment.sem.Entity`, so Maxim's tool
generation, affordance gating and prompt formatting work on the environment unchanged. The environment has no drives,
pain or learning: it is SEM without embodiment.

**The modulator is a trust boundary.** An NPC's tool call reaches the world through it; every gate is listed in
`docs/design/boundaries.md` §5.3. It works in two stages. `parse_action` turns the untrusted `(affordance, params)`
into a frozen `Strike`, `Ignite` or `Extinguish` inside the world's `ActionLimits` (`data/world/actions.yaml`),
reading nothing from the world, so the protocol layer can run it first. The applier re-checks the action against the
limits, then checks what depends on the world now (the region still has cells, a strike's point is on the region, judged
from authored footprints in metres so the answer is the same at every spacing). A region is its cells plus its authored
footprint; named solids can't share space with a later solid, so a footprint never covers another object's cells.
Parameters are a closed set per affordance, plus the keys Maxim adds itself (`target`). Every number is a finite real
number: NaN, infinities, bools and numeric strings are refused, never guessed. A refusal names the parameter in plain
words and changes nothing. The physics checks again underneath: `HeatSource` and `law.Load` refuse non-finite
and negative values, whoever calls them. The limits are physics-safety ceilings, not what a body can do; an NPC's
capability will come from its body and energy (`docs/roadmap.md`, Phase 5).

Actions change cells; only `World.advance` moves time.

## Fine-scale state drives graphics

`encoding.snapshot` quantizes per-cell state into arrays a client uploads as 3-D textures, the channels
`client_rendering.md` §4.2 lists; its interim `glow` channel retires at step 7 (`client_objects.md` §5.1). Shaders read them
directly, so the finest physical state shows up as cracks, scorch and glowing metal without the renderer knowing
any physics. The cell size sets the finest detail physics can drive; the client can add sub-cell detail (noise,
decals) that is purely visual.

## Transport: WebSocket on localhost (decided 2026-11-15)

The client and server talk over one WebSocket. Snapshots go as binary messages (a JSON header plus the per-cell
arrays), and intents go as JSON text messages. The protocol is defined apart from the transport, so swapping the
transport later means replacing one adapter on each side, not the message format or its tests.

**Why not a raw TCP socket.** A frame's size is `docs/design/client_rendering.md` §4.2's (bytes per cell × cells).
On localhost either transport moves it in tens of milliseconds, far less than a turn of physics. WebSocket frames
each message for us (raw TCP means hand-written length-prefix reassembly in GDScript), is inspectable with
`websocat`, is built into Godot 4 (`WebSocketPeer`), and alone suits a web export or `wss://`.

**What it costs, and what we do about it:**
- *Any web page can open `ws://localhost`.* Browsers allow cross-origin WebSockets, which a raw socket would not.
  The handshake (`docs/design/boundaries.md` §5.3) refuses what a browser sends: browsers always send an `Origin`
  header, and Godot's native `WebSocketPeer` sends none unless told to (to be confirmed in step 2). Each refusal has
  a test (`docs/standards_backlog.md` B14). A web export would send its page's `Origin`, so supporting one would
  mean an Origin allow-list, which is a protocol change made deliberately, not a relaxed check.
- *Head-of-line blocking.* WebSocket runs over TCP, so a large snapshot delays any small message queued behind it.
  `docs/design/client_rendering.md` §4.3 bounds the wait. Continuous streaming would need delta snapshots or
  chunking.
- *Whole messages are buffered.* Each end's cap is `docs/design/client_rendering.md` §4.3's. Multi-tile worlds at
  0.05 m would need deltas, as any transport would.
- *Not for real-time internet play.* Fast multiplayer would want UDP (Godot's ENet). Out of scope.
- *The faster local option is shared memory, not raw TCP.* Godot needs a GDExtension for it. A Phase 2 "Scale"
  item only if profiling asks for it.

The frame header (`docs/design/client_rendering.md` §4.1) reserves compression and gives each array's uncompressed
size, which Godot's `PackedByteArray.decompress(buffer_size, FileAccess.COMPRESSION_ZSTD)` needs. Most cells are air,
so zstd should shrink snapshots by 10× or more.

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

The licences are `docs/design/boundaries.md` §8.2's.
