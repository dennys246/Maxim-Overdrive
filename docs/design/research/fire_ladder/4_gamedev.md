# Ladder research 4: what game development knows about fire and materials

Research note, 2026-11-20. Lens: shipped games, engine tech and systemic design, and what transfers to a
physics-authoritative server feeding learning agents. Read in the repo: `docs/design/world_model.md` §0, §1, §9 and
`hot_surface_spike/results.md` §0 and §5. No repo files were edited.

**Tags.** **V**: I read it in a primary source (the developer's own words, docs, API or paper page). **S**: secondhand,
an article quoting or summarising the developer. **M**: from memory, still to verify. Most game-fire internals are
behind the GDC Vault paywall or were never published, so much of this is S. I say where.

## 0. The answer in ten lines

1. **No shipped game I could check derives fire spread from flames heating fuel.** Every one uses a discrete *fire
   object* (an entity, a per-cell flag, a pixel state) that ignites neighbours by a rule, a probability or a
   threshold. Some, like Teardown, layer that on a heat accumulator.
2. **The games that do simulate heat physically (Oxygen Not Included, Dwarf Fortress, Powder Toy) simulate
   *conduction*.** None that I found spreads flame through a flame volume. That missing piece is exactly what the
   hot-surface spike found missing (§5: "flames as volumes that heat neighbouring fuel").
3. **BotW's structure points the same way.** "Materials can not influence each other's states"; only elements (fire,
   wind) carry change between them (S). The carrier between fuels is a separate thing. In physics it's the flame and
   plume, a volume, not a cell flag.
4. **Every system bounds cost by locality** (player radius, dirty rects, active lists, fire counts). D21 allows the
   exact version. Fiedler's step clamp *is* world dilation (V).
5. **Fixed timestep with an honest slowdown is standard practice.**
6. **Design lesson one (Far Cry 2, S):** fire "doesn't propagate indefinitely because it's just not fun". Balancing
   realism against playability was the hardest part.
7. **Design lesson two (Hocking, S):** messy systems like fire collapse the player's intent, and that can be good,
   *if* the player stays confident about what fire will do.
8. **Fidelity helps when it matches intuition, and hurts when it contradicts it.** Dohta: puzzles that "reference
   the way the real world works" are solved "instinctively" (S). A crate that won't spread contradicts intuition,
   so to a player it reads as a bug, whatever the physics.
9. **The honest hybrid:** a cited sub-grid flame correlation on the server, with client flourish from its fields.
10. **For the exit:** make "build a fire" the verb (fire starter, kindling, crate).

## 1. Shipped fire and material systems

### Breath of the Wild / Tears of the Kingdom
- Dohta (GDC 2017) called the chemistry engine a "rule-based state calculator", the counterpart to a physics engine
  as a "rule-based movement calculator". **S** (Thumbsticks, GamesBeat, both reporting the talk; I couldn't see the
  Vault recording).
- Its three rules: elements change materials' states; elements change each other's states; "materials can not
  influence each other's states". **S** (GamesBeat and Thumbsticks agree; Tom's Guide's wording conflicts).
- Elements are things "without a constant state" (fire, water, ice, electricity, wind); materials are trees, rocks
  and the player. **S**.
- Dohta: "Little of it would scientifically work in the real world." **S** (GamesBeat). Grass fires make updrafts
  (S, Zelda Wiki). Grid representation, cost and LOD: nothing primary found (M).

### Far Cry 2 (Jean-François Lévesque, Ubisoft Montréal)
All **S**, from a Game Developer interview:
- Fire started as patches "no bigger than 10 meters by 10 meters"; management then asked for the whole savanna.
- He spent about 18 months on it, adapting CG research papers "by simplifying their math and physics".
- What drives spread: vegetation type, humidity, recent rain (the world must dry first), wind direction, and heat
  making fire run faster uphill. Water puts out only the submerged part.
- "The fire doesn't propagate indefinitely because it's just not fun."
- Particle fidelity was cut for framerate.
- AI treats fire as "an area-of-effect fear spell". Players get trapped by their own fire when upwind or uphill.

The data structures are unpublished. I found no primary source; a GDC talk may exist (unverified).

### Noita (Nolla Games, GDC 2019)
All **S**, from an 80.lv interview credited to Nolla, not quoting Purho directly:
- The world is split into 64×64 chunks, each with a dirty rect.
- Updates run bottom-up, multithreaded in a checkerboard of 4 passes. Pixels may move 32 px beyond their own chunk,
  which avoids locks.
- Fire: "look in a random direction to see if it can ignite that pixel". Fire that meets water makes steam. Wood
  burns for a set time, then is destroyed.
- The real rules are "more complicated". There's no temperature system in the article.

So Noita is a pure state machine. The Vault talk is paywalled.

### Teardown (Tuxedo Labs)
**V** (the official modding API):
- `AddHeat`: "As soon as the heat of the voxel reaches a critical value, it destroys and can ignite the surrounding
  voxels."
- Fires are countable discrete objects: `GetFireCount`, `QueryClosestFire`, `QueryAabbFireCount` and the
  server-only `SpawnFire` and `RemoveAabbFires`.
- So Teardown is a hybrid: a scalar heat accumulator per voxel, plus fire entities that ignite neighbours.
- A user-facing cap on the fire count exists. **M**.

### Minecraft
**V** (Minecraft Wiki, which documents decompiled behaviour; treat it as near-primary):
- Fire is a block with an age of 0 to 15, rescheduled every 30–40 game ticks in Java.
- Spread chance comes from per-block ignite and burn odds (planks 5/20, leaves 30/60, grass 60/100), difficulty and
  age.
- Rain blocks spread.
- **Fire updates only within a radius of a player** (`fire_spread_radius_around_player`). That is interest
  management applied to physics.

### Dwarf Fortress
**S** (DF Wiki):
- Each item exposed to a hotter or colder environment moves toward it by the temperature difference divided by its
  specific heat, every tick.
- Temperatures are u16 in an offset Fahrenheit scale.
- Item count is "the only major performance issue items cause", and temperature can be switched off
  (`[TEMPERATURE:YES]`).
- A container bug held a 1° offset forever, so the game recalculated constantly. That's a lesson in sleep criteria:
  a "nearly settled" region must count as settled, or it never sleeps.

### Oxygen Not Included
**S** (wiki and community reverse-engineering):
- Real-ish conduction per cell: a mass, a specific heat and a conductivity, with exchange every 0.2 s tick.
- The lower conductivity of a pair governs (with exceptions). Transfers are clamped per tick.
- Below a minimum delta, heat doesn't transfer at all. That's a deliberate dead band, cheap and stable, and it
  violates conservation at the margin.
- It has (nearly) no fire. **M**.

### Powder Toy
- Per-particle temperature with a per-element `HeatConduct` value (**S**, from the source snippet), plus an optional
  ambient air-heat grid carried on air currents (**S**, wiki).
- Fire is a particle type. **M**.

### Others (thin evidence)
- DOS2: discrete typed surfaces and clouds with authored combinations (fire on water makes steam). **S** (guides).
- Red Faction Guerrilla: pre-fractured meshes with a stress-based collapse model. **S** (Red Faction Wiki).
- Control and Spelunky: authored fracture and short-lived fire entities, no thermal model. **M**.

## 2. Research and engine tech

- **Nguyen, Fedkiw and Jensen 2002 (V, abstract).** Incompressible Navier-Stokes "to independently model both
  vaporized fuel and hot gaseous products". The paper models expansion at the reaction front and at the solid's
  vaporisation, draws blackbody rendering, and lets "flammable objects … catch on fire". The flame front is a level
  set moving at a curvature-dependent speed, D = a − bκ (S). It's offline, and no cost is stated.
  - This is the cleanest statement of what our model lacks: the flame is its own region with its own gas, and
    ignition of nearby objects follows from that gas reaching them.
- **Melek and Keyser (SPM 2005).** Couple heat, fuel and shape in burning objects (S, abstract via listings); unread.
- **Stam, "Stable Fluids" 1999.** Semi-Lagrangian advection plus implicit viscosity, "unconditionally stable" at any
  dt (S). Fedkiw, Stam and Jensen 2001 added vorticity confinement against its numerical dissipation (S).
  - Semi-Lagrangian advection isn't conservative (M), a poor fit for a ledger closing to 10⁻¹³.
- **Unreal Niagara Fluids (V, Epic docs).** Grid gas sims on the GPU. 3D costs more memory and GPU than 2D, and the
  docs steer 3D toward hero effects and cinematics.
- **EmberGen and Houdini Pyro.** GPU real-time and offline volumetric sims, mostly baked to flipbooks for games. **M**.
- **Lesson.** Real-time engine fire is visual. Its gameplay twin, where one exists, is a separate cheap system.
- **Simulation LOD.** Brockington's Neverwinter Nights AI used 5 LODs of behaviour complexity (S, via citing
  papers). Factorio removes idle entities from an intrusive active list, so switching one on or off costs O(1) (S,
  forum, dev reply). FFF #421 (V): idle roboports "turn back on" when needed, robots are "updated once every 20 ticks"
  with motion faked between, and "the game needs to remain fully deterministic or a desync would happen", so coupled
  networks stay on one thread.
- **Fixed timestep (V, Fiedler, "Fix Your Timestep").** "The renderer produces time and the simulation consumes it
  in discrete dt sized steps". Interpolate the render between the last two states. Under load, clamp the steps so the
  simulation "will appear to slow down".
- **Interest management.** Simulate everywhere at bounded cost per tick; send each client only its area. **M**.

## 3. Systemic design lessons

1. **Bound the spread, or it isn't fun** (FC2, S). The bound came from design, not physics. In Minecraft it came
   from age and rain (V).
2. **Intentionality versus chaos** (Hocking, GDC 2009, S via blog notes).
   - "Richly connected systems produce emergent gameplay"; fire, crowds and physics "tend to collapse the player's
     intentionality".
   - The fix wasn't less chaos but improvisation. The player still needs "continuity of intent" and "confidence";
     change that's too drastic makes players reload.
3. **Legibility comes from real-world reference** (Dohta, S). BotW's fire is legible because it does what people
   believe fire does: grass burns, rain stops it, heat rises. It isn't physically accurate. Players don't check
   physics; they check expectations.
4. **The failure modes, and who got them:**
   - runaway spread (FC2's motivation for the bound);
   - performance spikes (FC2 cut particles; Teardown exposes fire counts);
   - self-trapping (FC2, S), which players enjoyed as a story;
   - exploitation, burning a camp to win (FC2 used level design and AI "so you can't burn a camp and expect every NPC
     to die", S).
5. **AI and fire.**
   - FC2: enemies switch from attacking to self-protection, "AoE fear" (S).
   - BotW enemies react to fire (M). The Last of Us and Hitman: nothing found, no claim.
   - All of these are scripted responses to a fire *flag*. None learns.

**Does fidelity help?** Only where it changes outcomes in ways players can predict: wet won't light, wind and slope
speed it, oil spreads it, a closed door starves it. Fidelity in hidden variables, like char-layer insulation, is
invisible to players unless it produces a surprise. And a surprise that contradicts intuition ("the crate won't burn")
reads as a bug. **M/judgement**, consistent with Dohta and Hocking above.

## 4. Transfer

| Lesson | Verdict | Why |
|---|---|---|
| Rule-based spread on labels (Minecraft, Noita, BotW, DOS2) | **Doesn't apply** | It's the stance the project rejected, rightly for learning agents: NPCs would learn the designers' table. But note it: every shipped fire is of this kind. |
| A separate carrier between fuels (BotW's elements, Teardown's fire entities) | **Applies with changes** | The structural insight holds: spread needs a thing that isn't the fuel. Physically that's the flame and plume volume. Make it a gas-phase region with a heat release rate, a cited height and a cited flux onto nearby surfaces, not an entity with an ignition radius. |
| Heat accumulates to a threshold (Teardown, DF) | **Applies** | Already the model (ignition by surface temperature or flux). |
| Bound cost by locality (Noita dirty rects, Factorio active list, Minecraft radius) | **Applies, exact version only** | D21 permits sleep that is bit-identical. Dirty-rect bounding boxes for the fire's update, and an active-chunk list, fit that exactly. Minecraft's player radius *changes outcomes*, so it's forbidden here, and rightly, because NPCs live off-camera. |
| DF's 1° bug | **Applies** | The sleep test needs a stated "uniform" criterion. A residue that never settles keeps a chunk awake forever. If a dead band is used, put it on the ledger (ONI's silently isn't). |
| Fixed tick, clamp, dilate (Fiedler) | **Applies; already the design** | At 0.7 s per 0.5 s the tile is in Fiedler's "appears to slow down" regime. Report it, as D21 says. |
| Determinism by threading discipline (Noita checkerboard, Factorio) | **Applies** | Fixed-partition parallel passes are deterministic by construction. A future optimisation, not Phase 1. |
| Stable Fluids / Niagara for gas | **Server: no. Client: yes.** | Non-conservative advection breaks the ledger; per-cell Navier-Stokes is out of budget. Client flourish only. |
| "Bound the spread or it's not fun" | **Applies with changes** | The bound must come from physics: fuel, O₂, moisture, gaps. A designer can only author the *scene* (fuel spacing, a wet alley, a concrete floor), which is honest level design. |
| Legibility via intuition | **Applies strongly** | It holds for players *and* NPCs: real fire's regularities are what the agents should learn. A physics model that misses them fails both. |
| Scripted AI fear of fire | **Doesn't apply** | Agents must learn from sensed heat, light and pain. But FC2 shows the payoff to aim for: fire as a lever on enemy behaviour. |

**The honest hybrid.**
- The server holds the truth: heat, fuel, heat release rate per cell or region, and a sub-grid flame model.
- The client may draw flame tongues, flicker, sparks, embers and smoke curls from snapshot fields: heat release rate,
  surface temperature, soot. A flame mesh can be sized by the same cited flame-height correlation the server uses.
  Then the picture and the truth agree without any feedback.
- What is *not* honest: client flames bigger than the server's flame volume, because a player would then reasonably
  expect ignition there.

**Where the stance costs more than it buys (candid).**
- The project wants *fire spread derived from first principles at 0.1 m*. No game, and few real-time research
  systems, do that. Fire engineering itself doesn't resolve flames at 0.1 m outside CFD like FDS, which wants finer
  cells and runs far slower than real time (**M**, FDS practice).
- Two spikes have now shown the cell-local model can't carry spread. Insisting on resolving flames would make Phase 1
  a CFD project.
- The stance doesn't require that. A *cited empirical correlation* (flame height from heat release rate; incident
  flux versus distance; crib burning rate) is a law about fire measured in labs, not a designer's rule on labels. It
  is "reconstruct, decide at the point" with the reconstruction taken from fire science.
- That is the line I'd draw. Labels and probabilities are out. Measured correlations with stated validity ranges and
  ledger closure are in.

## 5. Recommendations for the ladder and the Phase 1 exit

1. **Change the exit verb from "light a crate" to "build a fire against a crate".**
   - A real crate isn't lit with a torch-sized source either. People use a fire starter, kindling, then fuel.
   - It's physically faithful, so the ladder rung "wax fire starter lights a stick" *becomes* the exit's first beat.
   - It's legible: every player knows the sequence.
   - It gives NPCs a real lesson later (small fires grow only with fuel arranged for them).
   - Exit scene: the player lights a fire starter under a few sticks leaned on a crate that's packed with cardboard.
     It catches, grows, and the crate cracks, glows and burns down.
   - This is option 3 ("change the exit") done as design rather than retreat.
2. **Order the ladder by what the exit needs, not by material breadth:**
   - (a) one PMMA slab ignites and burns at the cone-calorimeter rate (the cleanest data, no char);
   - (b) one softwood slab: charring, burning out;
   - (c) the wax starter lights a stick, the first *transfer* rung, which needs the flame-volume correlation;
   - (d) spread on one vertical surface, which tests the correlation's flux-versus-distance;
   - (e) a crib against NIST data;
   - then the crate scene.
   - Cardboard is mostly the exit's kindling, so it matters at (c) to (e). PMMA is a validation material only; it
     needn't be in the alley.
3. **Make the flame-volume correlation its own rung with its own pre-registration** before (c). It's the piece both
   spikes lacked and what every game substitutes a rule for.
4. **The material table:** per-material combustion columns (ignition temperature or critical flux, heat of
   combustion, heat of gasification, char yield, density, k, c, moisture) are *not* labels. Minecraft's flammability
   table is per-block too. The difference is that ours feed equations whose outputs are checked against
   measurements. Keep every value cited with its test method, since cone data vary with heat flux.
5. **Add a legibility check to each rung,** beside the physics gate: a 10-second clip judged against "does this look
   like what fire does?" A physically passing rung that looks wrong is a finding, not a pass.
6. **Performance for the exit:**
   - Exact sleep plus a fire bounding box (Noita's dirty rect) should cut the quiet 1.9×10⁶ cells to the few
     thousand near the fire. An **estimate**, not measured; measure it.
   - Accept dilation honestly until then.
   - Don't buy speed with the player radius.
7. **Run D28's heat-debt prototype against the real fire early.** FC2's hardest problem wasn't propagation but
   fun. Whether a slow, physical crate fire is a good game moment is untested.

## What I could not verify

- No GDC Vault talk was watched (BotW, Noita, DOS2, Hocking); all such claims are S.
- FC2's data structures, Teardown's fire cap, BotW's grid, Control, Spelunky, ONI and Powder Toy fire are M.
- Nguyen 2002 read at abstract level; DF Wiki returned HTTP 429 (search excerpts only).
