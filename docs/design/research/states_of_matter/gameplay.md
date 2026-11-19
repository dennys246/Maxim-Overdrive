# States of matter as a central mechanic: what it buys the game and its NPCs

Research note, 2026-11-15. Sources: the game repo at `phase1/act-validation` (`56eed51`): CLAUDE.md,
`docs/architecture.md`, `docs/roadmap.md`, `data/materials/core.yaml`, `data/world/actions.yaml` and
`sem_env/bridge.py`. Also the earlier notes `signals/maxim_senses.md` (abbreviated **MS** below) and
`signals/world_fields.md` (**WF**). I made no repo changes. Maxim claims are cited from MS, which read Maxim at
`4b773ef8`.

## 0. The answer in eight lines

1. **Phase is the game's verb amplifier.** Most interesting actions in this game turn matter from one state into
   another, or move it between places: burn (solid to gas), douse (liquid takes heat by boiling), flood, freeze, melt,
   vent and seal. Two basic moves, "change a phase" and "move a phase", already give rise to most cyberpunk set
   pieces.
2. **Each phase gets the representation it can afford, and transitions move mass and energy between them, with
   both conserved.** Solids are cells (as today). Liquids are a per-room level plus a floor film. Gases are a per-room
   mixture with portals between rooms (WF's recommendation). A transition is a conserved transfer between those
   stores: a melting steel cell adds kg to a molten pool, and boiling water adds moles of H2O to the room's gas. Each
   transfer gets a closed-form test (Stefan melting, latent heat of boiling, sealed-room O2 depletion) and a
   cross-tier test.
3. **The material table gains phase columns:** melting and boiling points, latent heats, liquid and vapour
   densities, a combustion block (heat of combustion, yields, O2 demand) and conductivity. That makes phase data, not
   code, and it makes imagined objects (Phase 6) phase-aware for free.
4. **Decide the state variable before save v0.** Enthalpy per m³ gives exact latent heat at every rig. Temperature is
   then derived from it. Melting, freezing and boiling are hard to retrofit once golden fixtures hold temperature
   (WF item "Phase / melting").
5. **The central loop for this game is heat.** Fire makes heat. Water, coolant and cryo remove it by changing phase.
   Bodies and cyberware must shed it. **Overdrive is heat debt**: pushing a body past its limits overruns the
   cyberware's cooling, and the coolant (and the sweat) boils off. That ties states of matter directly to the
   game's signature mechanic and to Phase 5's homeostasis item.
6. **For NPCs, every phase hazard must pass the receptor test** (MS §4). Several of the best set pieces are
   faithfully *silent* to the body: nitrogen boil-off from cryo, CO from a smouldering fire, electrified water and
   low O2. That is good design, not a defect, so long as the world offers an indirect cue (fog, a hiss, a meter, a
   collapsed NPC) and an action that relieves the hazard.
7. **Phase 1 needs only one phase change:** solid fuel becomes gas and heat, and it consumes O2 (the fuel model the
   roadmap already requires). Add per-room smoke as a drawn and saved quantity, and make `extinguish` physical
   (water as a latent-heat sink) rather than deleting the heat source.
8. **Drop per-cell fluid dynamics.** That means free-surface flow, gas velocity fields and lava rheology. Rooms and
   portals give 90% of the play at a cost of a few bytes per room.

## 1. Gameplay: mechanics a phase-centric world enables

Columns: **Verbs** (player), **NPC** (what a Maxim agent experiences), **Emergent because** (what makes it more than a
script), **ID**, which marks a mechanic central to this game's identity: **C** (clinic), **A** (alley), **O**
(Overdrive) or **I** (imagination).

| Mechanic | Verbs | NPC experience | Emergent because | ID |
|---|---|---|---|---|
| **Fire, fuel and smoke** (solid to gas, O2 in, CO2, CO and soot out) | ignite, feed (oil, paper), starve (shut the door), vent, crouch under the smoke layer | burn pain on contact (`health`), smoke as a visible and irritating cue, air hunger as CO2 rises | the outcome comes from fuel mass, O2 in the room and the doors that are open, so a shut door is a tactic, and a burning room whose door is opened can flash over | A (the crate), C |
| **Extinguishing**: water, foam, CO2 extinguisher | douse, smother, flood the floor, use a CO2 extinguisher in a closet | relief: the heat cue falls. With a CO2 extinguisher in a small room, air hunger rises (faithfully felt) | water's 2.26 MJ/kg latent heat is the mechanism. Foam excludes O2. CO2 suffocates the user in a sealed room: the same physics that saves the room can kill the person using it | A, C |
| **Sealed rooms and air** (O2 and CO2 per room) | seal, vent, cut the scrubber, bring a rebreather | air hunger from CO2 (felt), falling stamina and awareness from low O2 (silent) | every sealed volume becomes a resource clock. A fire, a crowd and a dewar all draw on the same O2 | C (the clinic's back room), I |
| **Flooding and diving** (liquid per room, flow through portals) | open a valve, breach a tank, dive, hold your breath, drain | the immersion cue, the `oxygen` drive, surfacing (the Exp 60 pattern, already earned) | water level per room plus flow through openings means a breached pipe two rooms away changes this room. Water also conducts current and douses fire | A (storm drain), later tiles |
| **Steam vents and scalding** (liquid to gas, condensing on skin) | time a vent, block it, redirect it, weaponize a burst pipe | an audible hiss (audio azimuth), then a scald to `health` | the vent runs on its own cycle from heat and pressure in a pipe network. Steam is invisible at the nozzle, so sound and the plume farther out are the real cues | A (street grate) |
| **Coolant and cryo** (LN2 dewar, freon loops) | shatter a dewar, freeze a lock brittle, quench a fire, store organs | a cold burn (cold nociception), and silent N2 asphyxia in a closed room (no receptor) | LN2 expands about 700 times as it boils. A spilled dewar in the clinic's sealed cryo store fills it with N2 that pushes the O2 out, and nobody inside feels it. Brittleness below a transition temperature lets a frozen lock shatter where it would only dent | **C** (organ storage, the iconic ripperdoc prop) |
| **Ice** (freezing and melting) | freeze a puddle, spray a floor, melt a seal, make ice armour or a plug | a slip and fall (`health`), cold | ice changes friction, and the floor film's state decides footing. Imagined ice melts on a timer set by latent heat | A, I |
| **Molten metal and slag** (solid to liquid) | cut a door with a thermal lance, pour, cast, make a molten trap | glow is visible from afar, radiant heat warns, contact is a severe burn | an enthalpy store lets a steel door actually melt through after a known energy, not by a scripted hitpoint. The pool keeps its heat, so it re-ignites wood nearby | A (a gang cutting a shutter), I |
| **Wetting and drying** (moisture in materials) | soak a crate so it won't light, dry a fuse, hose down a wall | wet clothes, so cold sooner. Humans have no wetness receptor: they feel cold plus touch | moisture is a latent-heat sink inside the material, so wet wood has to boil off its water before it can ignite. Rain makes the alley fire-resistant, and a dry night does not | A (rain is the cyberpunk default) |
| **Chemical spills and toxic vapour** (liquid to vapour at a declared rate) | spill, ventilate, use a gas mask, neutralize, plant a vapour trap | depends on the agent: irritants (ammonia, chlorine) are felt at once; systemic toxins are delayed malaise; some are silent | evaporation rate from the liquid's temperature and area, carried on the room's air, so a heated spill is far worse and a draught carries it next door | C (solvents, anaesthetic gas) |
| **Electricity in water** | wet a floor, drop a live cable, short a puddle | no receptor for a field, so the cue is sparks, hum or a collapsed body. Contact is instant `health` damage | the conductive path comes from where the water actually is, so flooding changes who a live cable can kill | A |
| **Cyberware that overheats** (an internal heat budget, coolant boiling off) | Overdrive, cool down in water, pour coolant, stand in the rain | implant heat as a designed (not innate) interoceptive sensor, plus core temperature | the heat drains into the surroundings by the same physics as everything else: a cold, wet alley cools you, and a burning room doesn't | **O** |
| **Pressure and decompression** (gas leaving through a breach) | blow a seal, vent a lab, slam a door with the pressure difference | ear pain (baroreceptors), knockback | orifice flow between rooms from the pressure difference (WF) | later tiles |

### The three identity anchors, concretely

- **The ripperdoc clinic is a phase lab.** It has an LN2 dewar for organs, a coolant loop on the cyberware bench, an
  autoclave (steam), an O2 cylinder (which feeds a fire), anaesthetic vapour, alcohol (flammable vapour) and blood (a
  liquid that leaves evidence on surfaces). Every prop is a phase hazard with a human reason to be there. The
  clinic's set piece: a fire in the back room meets the O2 cylinder (it accelerates), or a dewar cracks in the closed
  cryo store (silent asphyxia). Each comes from the room's air, its doors and its props, never from a script.
- **The alley is weather and waste.** Rain puddles (wetting, conduction), a steam grate (scalding, sound cue), a
  dumpster fire (fuel, smoke) and the crate. The Phase 1 exit test (the crate cracks, glows and burns away) is the
  first instance of "solid becomes gas plus heat".
- **Overdrive is a thermal debt.** A body's actions make heat; Phase 5's metabolic store pays for the work, and the
  heat is the waste. Cooling runs through phase changes: sweat evaporates (2.4 MJ/kg), coolant boils, or you plunge
  into water. Overdrive spends past the cooling budget. The pain comes from heat before integrity gives, so the
  world itself sets how long you can Overdrive, and the player learns to Overdrive in the rain, not in the burning
  clinic. This is the strongest single argument for phase as a core system: it makes the signature mechanic
  depend on the place.
- **Imagination becomes phase-aware for free.** An imagined object names materials from the table, so it inherits
  the melting point, latent heat and combustion block of each. An imagined ice plug melts, an imagined wax key
  softens in the heat, and an imagined wooden bridge burns. Phase 6's power budget can be priced in enthalpy: making
  ice in a hot room costs the heat it must remove. **Rule:** imagination makes solids and sealed containers only, so
  a validated spec never puts free liquid or gas into the world directly. A container that breaks releases its
  contents through the same transfer paths as a cracked dewar. That keeps `imagination.spec.place` the only door
  in.

## 2. NPC perception and learning, bio-faithfully

Method from MS §4: name the receptor (or none); the world owns exchange, dose and damage; Maxim owns the feeling;
there must be a cue before the harm; there must be an action that relieves it; and the drive used must be on the
Wire-4 allowlist (`health` and `oxygen` today, `nac.py:425`) for situation-fear learning to happen.

| Phase signal | Human receptor or drive | Warning cue before harm | Relieving action | Maxim drive or pain kind (MS) | Flag |
|---|---|---|---|---|---|
| Radiant and contact heat (fire, molten metal) | thermoreceptors, TRPV1 heat nociceptors | glow seen, radiant warmth felt at a distance (needs radiant heat, a known gap) | step back, douse | `thermal` / `core_temperature` (weak, R-1), burns to `health` (NOCICEPTIVE, allowlisted) | **R-1:** without GL2b the thermal channel alone is too weak; `health` carries the learning. Without radiation, the cue only arrives on contact |
| Steam scald | the same heat nociceptors (condensing steam deposits latent heat on the skin) | the hiss (audio azimuth), a visible plume beyond the nozzle | time the vent, go round, close the valve | `health` (NOCICEPTIVE) | good: an audio cue already works (MS row "Sound") |
| Cold, cryo contact | TRPM8 thermoreceptors, cold nociceptors | fog, frost, felt cold | withdraw, warm up | `core_temperature` (the cold side works today), cold burn to `health` | none |
| Wetness | **none.** People feel wet as cold plus touch | n/a | dry off, shelter | felt as `core_temperature` through faster heat loss (water conducts about 25 times faster than air) | a "wetness" sensor would be a **caricature**. Model wetness as heat loss |
| Immersion | the urge to breathe from breath-holding (CO2 chemoreceptors) | the `is_in_water` cue (head liquid fraction) | surface, escape | `oxygen` (allowlisted); the Exp 60 pattern, no Maxim change | none: the highest-confidence item |
| CO2 rise in a sealed or smoky room | central chemoreceptors, so air hunger is strongly felt | dyspnoea starts at about 3-5% CO2, before harm | leave, open a vent, shut off the CO2 source | ideally a new `air_hunger` drive (needs the allowlist proposal **P-B**). Fallback: the world owns `oxygen` as a lung store whose felt value follows CO2 | none, if felt from CO2 |
| Low O2 at normal CO2 (N2 from cryo, inert gas) | **none felt.** Peripheral chemoreceptors barely notice; judgment fades | none from the body. Indirect: LN2 fog, a hiss, an O2 monitor's alarm, a collapsed NPC | leave, ventilate, wear a mask | silent: `stamina` and awareness drop, then an `unconscious` failure mode (P-F) | **an O2 pain would be a caricature.** The faithful design is a silent killer with world-side cues |
| CO (smouldering, an under-ventilated fire) | **none** | indirect only: the smoke that comes with it, a CO alarm entity, others collapsing | leave the room | silent dose to awareness and `health` | caricature if felt. A good social-learning case (Phase 5 rumour) |
| Smoke (soot, irritants) | airway chemical nociceptors (TRPA1), so coughing; also loss of sight | visible density, smell, cough at low doses | crouch under the layer, leave, cover the mouth | airway irritation via GL2b `NociceptorSpec` (chemical, **P-C**). Until then the irritant dose goes to `health`. Visibility through line of sight (**P-E**) | a smell scalar mapped into text would be a caricature (MS). Use the odour as a `world` cue sensor with no drive |
| Irritant vapour (ammonia, chlorine) | TRPA1, so the warning is immediate and strong | smell and sting at concentrations below harm | leave, ventilate | as for smoke | none |
| Systemic toxic vapour or a spill (solvents, anaesthetic) | the nausea centre (area postrema) for delayed malaise; anaesthetic sends you to sleep | odour if it has one, else none | leave, ventilate, avoid that place next time | needs a malaise drive with delay-tolerant credit (**P-D**) | immediate pain from a toxin would be a caricature. Hydrogen sulphide is a real trap: at high concentration it deadens the sense of smell, so the cue disappears as the danger rises. Faithful, and a good design |
| Ice and slippery films | **none** for friction ahead of time. The vestibular sense only reports the slip | a visible sheen or frost; learned through the fall | walk round it, salt it, melt it | the fall to `health`. The cue is a visual or `world` surface sensor | fine, so long as a visual cue exists |
| Electricity in water | **none** for a field. Contact gives an instant shock | sparks, hum (audio), a live cable you can see, someone else collapsing | step out, cut the power, avoid wet floors near cables | `health` (NOCICEPTIVE) | **caricature risk:** first contact is often lethal, so there is nothing to learn from. Either add sub-lethal tingles (real: low-current contact is felt) or rely on social learning (Phase 5) |
| Cyberware heat | **none innate.** An implant has no native afferent | the implant's own sensor (a cyberpunk premise: installed hardware reports to its owner) | stop Overdrive, cool off (water, shade, coolant) | a designed `implant_temp` world-owned sensor with a homeostatic drive. To be *feared*, it needs its harm routed to `health` or the allowlist extended (P-B) | a sense humans lack, **but justified by the fiction**: it is installed at the ripperdoc, not innate. Keep it off cradled bodies that have no implants |
| Pressure changes | ear baroreceptors (felt), plus blast to `health` | ear pain, wind through the breach | equalize, leave, hold onto something | `health` via `blunt`; ear pain via mechanical `NociceptorSpec` later | none |

Hazards with **no relieving action** become helplessness, not avoidance (MS §3). Check each tile for them. Two are
built into this list: a sealed room with no exit and no vent (always author an escape act: a vent, a door, a mask
locker), and a flooded room with no surface (always leave an air pocket or a drain valve).

## 3. Player and client

### Show phase without colour alone (CLAUDE.md client standard)

| State | Redundant non-colour cues | Snapshot source |
|---|---|---|
| Solid, damaged | crack geometry and shading (already in the plan) | `crack` |
| Hot or glowing solid | brightness and emissive bloom, heat shimmer distorting what's behind it | `glow`, `temperature_c` |
| Molten | a flat horizontal surface where there were faces, a flowing normal-map animation, drips, plus brightness | a phase channel (or one derived from material plus enthalpy) |
| Liquid (water, coolant, spill) | a flat, reflective, refractive surface at the room's level; ripples; a wet roughness shift on submerged surfaces | per-room `liquid_level_m` and species |
| Wet surface | lower roughness (specular sheen) and a darker value (brightness, not hue) | surface film u8 |
| Ice and frost | a frost texture pattern (crystalline normals), changed specular, a crunch sound | surface film state, or the material id `ice` |
| Smoke | volumetric opacity (a luminance and contrast loss), a visible layer edge at the room's smoke-layer height | per-room `smoke_optical_density` and `smoke_layer_height_m` |
| Steam | white billowing particles with fast fading, a hiss, condensation droplets on nearby surfaces | the vent entity's state plus room H2O |
| Toxic vapour | particle shape and motion (low, creeping, heavier than air), a HUD hazard glyph with a distinct shape, a sound | room species |
| Invisible hazards (N2, CO, live water) | **nothing on screen, by design,** unless the player has an instrument: an O2 or CO meter, a cyber-eye overlay. Then they show as glyphs and patterns | room species; the electrical graph |

The rule for invisible hazards should be stated openly. The player sees what their body or gear can sense, as NPCs
do. Showing CO on screen with no instrument would hand the player a sense the NPCs are faithfully denied, and the
asymmetry would make NPCs look stupid.

### What the Godot 4 client needs per phase (engine notes)

- **Cells (solid, molten):** the planned `ImageTexture3D` uploads of the snapshot channels, and a shader that reads
  them. Molten cells reuse the glow path with a liquid normal animation.
- **Liquid:** one `MeshInstance3D` plane per room at `liquid_level_m`, clipped to the room's footprint, with a water
  shader (screen-texture refraction, Fresnel, scrolling normals). An underwater `Environment` change (fog,
  low-pass audio bus) when the camera is below the level. Why a plane per room: the server's liquid *is* per room, so
  a plane per room is an exact picture of it, not an approximation.
- **Smoke, steam, toxic gas:** `FogVolume` nodes with a fog shader, one per room, with density from the snapshot,
  or sampled from a coarse 3-D density texture once gas goes per cell. **Caveat:** volumetric fog and `FogVolume`
  need the Forward+ renderer, not Mobile or Compatibility. If a low-end client tier is planned, it needs a fallback
  (billboard particle sheets). Decide the minimum renderer when you pin the client, because it is part of the
  client's version contract.
- **Heat shimmer:** a screen-space shader (a `hint_screen_texture` sampler) offset by noise scaled by temperature
  near the camera ray. It is purely visual.
- **Particles:** `GPUParticles3D` for sparks, steam puffs, drips, splashes and embers. All visual.
- **Sound:** synthesized from material and phase events (Phase 6 already plans sound from material properties):
  sizzling when water hits hot cells, hissing, cracking ice.

### Authoritative versus purely visual

- **Authoritative (server, in the snapshot, in the save):** enthalpy and temperature, phase per cell, fuel remaining,
  each room's liquid level and species, each room's gas mixture and smoke density and layer height, the surface film
  (wet, ice, oil, blood), moisture in materials, and the electrical graph. Anything that changes damage, sight,
  footing, a sensor or a dose.
- **Purely visual (client only, never fed back):** ripples, splashes, sub-room smoke swirl, flame flicker, steam
  wisps, heat shimmer, drips, interpolation of the level between turns, decals that only dress cells.
- **One fairness rule worth writing down:** the client's smoke opacity should come from the *same* optical
  density the server uses for NPC line of sight (P-E). Then the player and NPCs are blinded by the same smoke. The
  client can add swirl, but not clear patches.

## 4. Priority

### Phase 1 (exit test and first tile): only what the crate needs, plus what the save v0 freeze forces

1. **Combustion as solid to gas.** Fuel kg/m³ per cell, a burn rate, heat of combustion, O2 consumed at about
   13.1 MJ/kg, CO2 and soot produced at declared yields. This *is* the roadmap's fuel model. It flips
   `test_a_fire_that_has_burned_its_fuel_stops_heating` and removes the `TEMPORARY(phase1)` envelope in
   `data/world/actions.yaml`. O2 can live as one number per room (WF: otherwise a sealed crate scene starves in about
   7-8 turns, and the gated outcome flips later).
2. **The phase columns in the material table and the state-variable decision** (enthalpy versus temperature)
   before save v0 and the first golden fixture. Only the columns combustion needs are live; the rest are reserved.
3. **Per-room smoke** as a sourced scalar (with soot settling), carried in the channel-generic snapshot so the
   client draws a `FogVolume`. Nothing senses it yet.
4. **`extinguish` made physical.** Today it removes a fire by fiat (`bridge.py::Extinguish`). A water or foam
   action that removes heat through latent heat and cuts off the O2 is a better exit test, and it is a closed form.
   This is optional for the exit test; it is the first tile's second verb. It needs a parameter (litres), so it is a
   protocol and limits change. Do it before the protocol freeze or not at all in Phase 1.
5. **Wet wood** (moisture as a latent-heat sink), only if the alley is raining. Cheap: a per-cell f32 and a closed
   form.

### Phase 2 (physics breadth)

- Per-room gas mixtures with a portal graph and orifice flow (this is the roadmap's convection), CO and CO2, room
  merging on a breach.
- Per-room liquid with portals (flooding), floor films (wet, ice, oil).
- Enthalpy-based melting and freezing (molten metal, ice), steam and evaporation.
- Radiant heat (a ray kernel), so heat cues reach the body before contact. Without it every heat lesson arrives on
  contact.

### Phase 3 (Maxim upstream)

- P-B (air hunger on the allowlist), P-C (GL2b heat and chemical nociceptors), P-A (per-part world sensors), and
  later P-D (malaise) and P-F (unconsciousness). File each through Maxim's process, citing the phase hazard that
  needs it.

### Phase 4 (cradles and NPCs)

- Body models: skin heat and burn integral, immersion and the lung store (the Exp 60 pattern), CO2 air hunger,
  silent hypoxia and the CO dose. Cradles should include phase lessons (a hot stove, holding your breath in a bath)
  so NPCs arrive with priors.

### Phase 5 (body and Overdrive)

- The cyberware heat budget, cooling by phase change, and Overdrive as heat debt.
- Electricity in water (the graph, plus wetness raising conductivity) and social learning about silent killers.

### Phase 6 (imagination)

- Phase-aware specs; containers with contents; the power budget priced in enthalpy.

### Drop as scope creep

- Per-cell free-surface liquids (FLIP, SPH, Noita-style falling sand at 3-D scale), and per-cell gas velocity fields
  and pressure projection (Stam, FDS). Rooms and portals cover the play (WF).
- Viscous flow of lava or slag. A molten pool that spreads to its level instantly is enough.
- Pressure-dependent boiling points, supercooling, sublimation chemistry beyond a fixed table entry (dry ice can be
  one table row if a tile needs it), and general reaction networks. Use a fixed table of reactions instead: burn,
  neutralize, corrode.
- Buoyancy of rigid bodies (floating crates). It needs a body and debris system that doesn't exist yet.
- Humidity and weather as simulation. Rain is an authored source of water on surfaces.

## 5. Experiments worth pre-registering

All of these stay off Maxim's results ledger unless they are pre-registered through Maxim's process (roadmap
standing rule). Each uses the earned Wire-4 pattern (a cue before the harm, pain on an allowlisted drive) and needs
a **negative control** that would catch a caricature.

1. **Exp 60 transfer: drowning avoidance in Overdrive physics** (cheapest and first). A flooded room on the tile,
   `is_in_water` from the head's liquid fraction, `oxygen` owned by the world. Prediction: surfacing is learned at
   least as fast as in Minecraft. It tests whether an earned result survives a new world, with **no Maxim change**.
2. **Smoke-room avoidance from a felt cue before harm.** Two rooms, one smoke-filled at random per episode. Cues:
   smoke density (`world` sensor) and CO2 air hunger. Harm: irritant or burn to `health`. **Negative control:** a
   room filled with odourless CO that carries the same harm but no cue. The prediction is *no* learned avoidance
   there before harm, a null that shows the NPC is not given a sense it shouldn't have. It needs P-B (or the
   `oxygen` fallback) and Phase 2 gas.
3. **The steam-vent timing** (an audio cue predicts a scald). Does the hiss's azimuth and timing become a fear cue,
   and does the NPC learn to cross between bursts? It uses audio localization, which already exists. It needs sound
   propagation (Phase 2).
4. **Approach distance to hot metal** (glow and radiant heat, then a burn). Prediction: approach distance increases
   with experience. Negative control: hot metal that doesn't glow (below the Draper point), where the learning
   should be slower or need contact. It needs radiant heat, and ideally GL2b.
5. **Homeostasis under heat debt** (the roadmap's Phase 5 question). Do NPCs with cyberware regulate implant heat
   (rest, seek water) or run themselves into the ground? The manipulation is ambient: rain versus a hot room.
   Prediction: Overdrive episodes are shorter in hot rooms with no instruction to that effect.
6. **Social learning of a silent killer** (Phase 5 rumour). An NPC that saw another collapse in a cryo store (N2)
   or in a live puddle avoids the place, when it has never been hurt there. It ties to the Phase 5 exit, and it
   needs `docs/plans/social_referencing.md` or hivemind merges.
7. **Later, with P-D:** conditioned aversion to a spill room through delayed malaise, testing a credit window that
   tolerates delay.

## Open questions for the owner

- Enthalpy as the saved state variable from save v0: yes or no? (Recommended: yes, because temperature can always be
  derived from it.)
- Is a physical `extinguish` (with a water amount) in Phase 1's protocol freeze, or deferred along with a
  version bump?
- The client's minimum renderer: Forward+ only (volumetric fog), or a Compatibility fallback tier?
- Does the player get instruments (O2 or CO meters, a cyber-eye) as cyberware, which makes invisible hazards a
  reason to visit the ripperdoc?
