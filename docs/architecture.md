# Architecture (v0, 2026-11-14)

Maxim Overdrive is a cyberpunk RPG set in **Maxim Prime**, where every NPC is a [Maxim](https://github.com/dennys246/Maxim)
agent with a life it actually lived. This file records the foundations and why they were chosen.

## The split: an authoritative world server, a client that only draws

```
Godot client (render, input, UI)  ──intents──▶  World server (Python, authoritative, fixed turn)
                                  ◀─snapshots──    ├── material grid (cells)
                                                   ├── physics fields (heat today)
                                                   ├── damage
                                                   ├── SEM bridge  ──▶  Maxim agents (AgentPool)
                                                   └── imagination specs → cells
```

- The world server owns all state and all physics. The client never simulates anything that feeds back into the
  world. It may add purely visual effects (particles, debris, interpolation between turns).
- Cradles and experiments run the same server headless. The physics an NPC grows up in is the game's physics.
- The game is turn-based (classic Fallout), so LLM latency lands in a dialogue screen, not in a combat loop.

## The world is material cells

`world/grid.py` holds the world as a structure of arrays: per cell, a material id (`uint8`), integrity in [0, 1] and
temperature in °C. Scenes are **authored in metres** (`world/scene.py`) and voxelized at whatever cell size the rig
profile chooses (`data/rigs/`). Nothing is authored in cells.

Materials (`data/materials/core.yaml`) carry textbook thermal properties plus two gameplay calibrations that are
always **per unit volume** (`fracture_energy_j_m3`, `degrade_*`), so they mean the same thing at every resolution.

## The resolution rule

> **A rig profile may change precision, never the outcome class.**

The same scene at two profiles must agree on every gameplay outcome: did the wall breach, did the crate burn, did the
room get hot enough. Each physics module ships two kinds of test:

1. **Against a closed form.** Heat: a Gaussian pulse in a steel bar against the 1-D heat equation (error 1% / 0.1% /
   0.01% at 0.2 / 0.1 / 0.05 m cells, second-order convergence). Damage: crater volume against
   `analytic_crater_radius_m` (within 5%).
2. **Across tiers.** The same scenario at every profile, gated on the outcome (`tests/test_cross_tier.py`).

How the rule is kept, so far:
- Energy lands by **exact cell average** (a strike's Gaussian integrated over each cell) or by **volume overlap**
  (a fire's sphere, sub-sampled), never by "is the cell centre inside". Centre-inside made a 0.3 m fire run 35%
  cooler at 0.2 m cells than at 0.05 m, and the crate burned at one rig and not another.
- SEM sensors are **reductions over cells** (mean integrity, max temperature), which converge with resolution.
- Thin features must be at least two of the coarsest rig's cells thick, or one cell becomes the whole feature and a
  scratch becomes a breach.

**Known gaps (tracked, not gated yet):**
- Late in a burn the coarsest rig lags (crate integrity 0.55 at 0.2 m vs 0.37–0.38 at 0.1 and 0.05 m after 150
  turns): a coarse cell degrades as one block. Onset agrees to within 5%.
- No convection or radiation: air only conducts, so rooms heat too slowly and fires must sit on a material.
- Destroying a cell removes its heat with it (the cell becomes air at the air's heat capacity).
- **Fires don't consume fuel, and nothing radiates.** A fire is a constant-power source spread over the solid cells
  it overlaps, so as a crate burns away the same power lands on fewer cells and their temperature runs away. Measured
  on the 3×3×2 m crate scene, 500 kW at radius 0.3 m for 30 turns: peak crate temperature 16,619 °C at 0.2 m cells
  and 29,213 °C at 0.1 m (crate integrity 0.34 and 0.37, 7 and 136 cells destroyed). The snapshot clamps
  temperature at 6000 °C, so the client never sees the overshoot, but heat conducted onward from those cells is
  real. This blocks the Phase 1 exit test's "burn away" and has to be fixed (fuel consumption, and a loss term)
  before the tile's crate scenario is gated.
- **A source smaller than a cell heats one cell.** `World._power_field` puts all of a sub-cell source's power into
  the cell it sits in, so total power is right but its density is P/dx³: 64× higher at 0.05 m cells than at 0.2 m.
  Peak temperature near a spark therefore depends on the rig. A minimum source radius of about one coarse cell
  would remove it.
- Cost: the 0.05 m profile is about 60x slower than 0.1 m on a fire scenario (explicit heat, Python + numpy).
  `full_res_radius_m` is reserved for running far cells coarser.

## SEM for the environment

`sem_env/bridge.py` makes any named region (a wall, a door, an imagined crate) an SEM Entity: sensors `integrity`,
`temperature_max`, `temperature_mean` and `breached`, and a `structure` modulator with `strike`, `ignite` and
`extinguish`. With pymaxim installed, `to_maxim_entity` returns a real `maxim.embodiment.sem.Entity`, so Maxim's tool
generation, affordance gating and prompt formatting work on the environment unchanged. The environment has no drives,
pain or learning: it is SEM without embodiment.

Actions change cells; only `World.advance` moves time.

## Fine-scale state drives graphics

`world.snapshot` quantizes per-cell state into arrays a client uploads as 3-D textures: `material`, `crack`
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
can be inspected with `websocat` or a few lines of Python, is built into Godot 4 (`WebSocketPeer`), and is the only
one of the two that a web export or `wss://` remote play could use.

**What it costs, and what we do about it:**
- *Any web page can open `ws://localhost`.* Browsers allow cross-origin WebSockets, which a raw socket would not.
  The server binds to `127.0.0.1` only, refuses any handshake that carries an `Origin` header (browsers always send
  one; Godot's native `WebSocketPeer` sends none unless told to, to be confirmed in step 2), and requires a
  per-launch token. Each refusal has a test (`docs/standards_backlog.md` B14).
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

`imagination/spec.py`: an imagined object is a spec of primitives made of known materials. Before it exists it must
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
