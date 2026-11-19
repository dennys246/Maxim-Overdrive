# World fields: what the cells will need to carry, and how to make adding them cheap

Research note for Maxim Overdrive, 2026-11-15. Read against `src/maxim_overdrive/world/{grid,heat,world}.py`,
`docs/architecture.md`, `docs/roadmap.md` and `docs/standards_backlog.md` at `bc4e3c7`. No repo files were changed.

## The short answer

The owner's instinct is right, and the timing matters. **The wire protocol (Phase 1 step 2, B3) and save v0 (B4)
have not been written yet.** They are the expensive things to retrofit. The fields themselves are cheap to add later
if the formats and the grid are shaped for them now.

There is a sharper point too. **Oxygen is not a Phase 2 nicety. It belongs to the Phase 1 fuel model.** A 500 kW fire
uses about 0.038 kg/s of O2. That figure comes from the oxygen-consumption rule of about 13.1 MJ per kg of O2 (Huggett
1980, the basis of cone calorimetry). The 3×3×2 m crate scene is a sealed, insulated box holding about 5.0 kg of O2.
Real flames go out at roughly 12–15% O2, so a sealed fire there should starve in about 45 s, or 7–8 turns. Today's
measurements say the crate catches at turn 15. If O2 is added after the crate scenario is gated, the outcome class of
a gated test flips. That is the retrofit cost made concrete: every golden outcome recorded without a field that
belongs in it has to be re-derived later. The fuel model should consume fuel mass and O2 from the start, even if O2
lives in one number per room at first.

## Physics signals sort into five mechanisms, not twenty fields

Group the signals by mechanism, because each mechanism gets one solver, one kind of closed-form test and one way of
staying the same across rigs.

| Mechanism | Signals | Stored? | Rig-independence technique | Closed-form test |
|---|---|---|---|---|
| **A. Conserved, transported** (finite volume, face fluxes) | heat (have), gas species, smoke, liquid volume, airborne contaminants | yes, state | quantities per unit volume; flux through faces, scaled by open-face area measured in metres; sources by volume overlap | Gaussian diffusion (have); a well-mixed room `C(t)=C0·e^(−Qt/V)`; Torricelli draining; O2 depletion with no inflow |
| **B. Attenuated line integrals** (rays) | light/illuminance, line of sight, radiation dose rate, radio/hack range, approximately sound | **no**, derived each turn from sources | Beer–Lambert `exp(−Σ μᵢ ℓᵢ)` using the exact length of the ray in each cell (Amanatides–Woo DDA), never a count of cells crossed; μ per material per channel, in 1/m | a slab of thickness d gives `exp(−μd)` at every rig (d ≥ two coarse cells); inverse-square in open air |
| **C. Connectivity / graphs** | rooms, structural support, flood connectivity, electrical networks, sound portals, pathing | derived on topology change (room id cached) | thin features at least two coarse cells thick; doors, vents and wires are entities with an aperture or resistance, not cells | an island with no path to an anchor falls; two rooms merge when a wall is breached |
| **D. Local cell state** (no transport) | integrity (have), **fuel remaining**, moisture in materials, surface deposits (blood, oil, acid, soot, scent), phase/enthalpy | yes, state | per-unit-volume rates (as `degrade_*` already does) | exponential evaporation; fuel burn-out time = fuel mass ÷ burn rate |
| **E. Body accumulators** (per agent, not per cell) | toxic dose (FED), rads, blood O2 and breath-hold, wetness, charge/shock, hearing damage | per body, in the agent's state | integrate a *reduction* over the cells the body occupies (a mean, like `RegionSensor`), never a single cell | a constant concentration gives a dose that is linear in time |

Two things follow. Only mechanisms A and D add stored per-cell state, so only they cost memory and save-format
bytes. B and C are recomputed, and E lives on bodies. And B unifies light, visibility, radiation, radio and part of
sound: one ray kernel with a per-channel μ column in the material table.

## Inventory

Costs are at **5.12 M cells**: the 16×10×4 m tile at 0.05 m. The same tile is 640 k cells at 0.1 m and 80 k at 0.2 m.
float32 is 20 MB per scalar field and float64 is 40 MB. **Today's state is 14 B/cell, 72 MB.** The heat substep
allocates several float64 temporaries (k, ρc, three face-conductance arrays, the flux sum, `dT`), about 300 MB at
peak, and rebuilds k and the conductances every substep even when no material changed. A field registry should cache
those, or every new field repeats the mistake.

**Explicit transport costs about dx⁻⁵ per turn.** Cells scale as dx⁻³, and stable substeps scale as dx⁻². For gas
mixing at an effective (eddy) diffusivity of 0.01 m²/s, the stability bound needs **10 / 40 / 160 substeps per 6 s
turn** at 0.2 / 0.1 / 0.05 m. Heat gets away with one because molecular diffusivities are tiny (air and steel are
both about 2×10⁻⁵ m²/s). Eight species × 160 substeps × 5 M cells in numpy is minutes per turn. **This one number
decides most per-cell vs per-room questions below.**

| Signal | Gameplay / NPC sense | Simplest rig-safe model | Couplings | Cost at 5 M cells | Granularity |
|---|---|---|---|---|---|
| **O2, N2, CO2** | suffocation, fire starvation, diving tanks, sealed vaults, hypoxia panic as a Maxim drive or pain input | moles per m³ per species (A); total pressure `p = ΣnRT/V` derived | fire consumes O2 (13.1 MJ/kg) and makes CO2 (wood: about 1.3–1.7 kg/kg fuel); bodies consume O2 (about 0.3 L/min at rest); vents and scrubbers | 3×f32 = 60 MB per-cell; 1 MB on a 0.2 m grid; bytes per room | **per room now**; a fixed-resolution gas grid later |
| **CO, toxic gas, chemical spill vapour** | poisoning, assassination, area denial, evacuations NPCs remember | species in the same mix; dose per body (E) by Purser's FED | under-ventilated fire yields far more CO (about 0.004 kg/kg well ventilated, up to about 0.2 kg/kg; SFPE values, approximate); spill liquid evaporates into vapour | +4 B/cell per species | same as O2 |
| **Smoke / soot** | blinds vision (B's μ), coughing, crouch under the smoke layer, stealth cover | aerosol species (kg/m³) plus slow settling onto surfaces (D: soot deposit) | from fire (about 0.015 kg/kg wood); raises μ for light and LOS | 4 B/cell | **two-zone per room** (hot upper layer and its height, as in NIST CFAST) gives the "crouch under smoke" rule with no per-cell field |
| **Pressure / wind** | decompression, blast overpressure, doors slammed, smoke pushed through vents | equalization over the room graph with orifice flow `Q = Cd·A·√(2Δp/ρ)` through openings; a velocity field only if ever needed | drives advection of every species and of heat (this *is* the roadmap's "convection") | per room: nothing. Per cell: 3×f32 + a pressure solve, 60 MB and a Poisson solve per substep | per room / per portal; **defer** the velocity field |
| **Liquids** (water, oil, acid, coolant, blood) | flooding, diving, drowning, spills, slipping, electrified puddles | volume per room → water level (Barotrauma "hulls and gaps"); orifice flow between rooms; puddles as a floor-surface layer (D) | quenches fire (latent heat 2.26 MJ/kg); conducts current; acid lowers integrity; oil is fuel; wets materials | per room: bytes. Per-cell fill fraction f32 + species u8: 25 MB | **per room now**; per-cell fill later only if a tile needs free-surface flow |
| **Moisture / wetness of materials; humidity** | wet wood won't light, wet floors carry shocks, rot, steam scalds | moisture kg/m³ in a cell's material (D); humidity is water vapour in the gas mix | fire must boil it off first (a latent-heat sink: a clean closed form); raises electrical conductivity; evaporation feeds humidity | f32: 20 MB | per cell (it's per material) |
| **Fuel remaining / char** | burn-out, the Phase 1 exit test | combustible kg/m³ per cell (D), consumed at the burn rate; heat release = burn rate × heat of combustion, capped by O2 | O2 in, CO2/CO/smoke out, heat out; integrity is a separate thing (char is weak but present) | f32: 20 MB | **per cell, now** (Phase 1) |
| **Sound** | Maxim audio localization (`world_set_axis`), noise alerts, gunshot heard two rooms away | **event-driven, not a field.** Per sound event, propagate level over the room/portal graph (or a BFS on a coarse grid) with transmission loss per wall material; direction is the last portal on the path. A wave equation at c = 343 m/s would need dt ≈ 0.1 ms at 0.05 m | doors and openings (C), wall materials; loud events can wake NPCs | nothing stored; one graph search per event | per room / per portal |
| **Light / visibility** | what an agent can see, stealth in shadows, the light shaders draw | sources + B. Gameplay light comes from the server and is coarse; visual light on the client is cosmetic | smoke μ, fire and glow are emitters (glow already), broken lamps are entities | LOS: one DDA ray per agent-target pair. An illuminance grid, if kept, as u8 on a coarse grid | rays per agent; illuminance on a coarse grid |
| **Radiation** | Fallout rads, shielding behind concrete, a contaminated zone | sources + B with μ per material (half-value layers); contamination is a gas/particulate species or a surface deposit (D); dose per body (E) | wet or dense materials shield; contamination spreads with gas and liquid | nothing per cell: sample only where bodies are | per source, sampled at bodies |
| **Electricity** (power, cyberware, tasers, hacking) | shock damage, cyberware power, an electrified pool, EMP, hackable devices | **a graph, not a field.** Devices and wires are entities on a network solved per turn (Kirchhoff, or simpler ONI-style power budgets). A taser or arc is an event: the lowest-resistance path through conductive cells. Wires are thinner than two coarse cells, so they can't be cells by the thin-feature rule | material conductivity (add a column), wetness, liquids; hacking is a `target_effect` on a body's SEM sensors (Phase 5), not a cell field | nothing per cell; a `network_id` only if wiring is ever embedded in walls | graph |
| **Radio / network signal** | hacking range, jammers, dead zones in a Faraday basement | same ray kernel as radiation, with a μ column for RF | metal blocks it; jammers are sources | nothing stored | per source |
| **Structural load** | collapse, debris, unsupported floors | connectivity to anchors after any destruction (C: `scipy.ndimage.label`, O(N) per event); optional per-material span limits (as in 7 Days to Die) rather than stress | destruction from heat and strikes; debris need an entity/body list (new state!) | label pass about 0.1 s at 5 M cells, only on turns that destroyed cells | per cell, on event |
| **Phase / melting** | molten metal, ice, plastic that drips, steam | store **enthalpy** per volume instead of temperature; T is derived, latent heat is exact (the Stefan problem is the closed form) | fire, water boiling off, freezing | same 8 B as `temperature` | per cell |
| **Surface deposits** | blood trails, footprints, scent (sniffer cyberware, dogs), chemical residue, scorch: evidence NPCs and players read | u8 per deposit kind on solid surfaces (D), decaying | spills, fire (soot), bodies (blood) | 5 MB per kind | per cell; ship only the kinds the tile uses |
| **Room id** (infrastructure) | the key to every per-room field | label air cells into rooms after any topology change; u16 | breaches merge rooms (and their gas mixes, by conservation); doors split them | 10 MB, derived | per cell, derived |

## What other games did, and where it went wrong

- **Space Station 13 (/tg/ LINDA).** Each turf holds a `gas_mixture`: an associative list of moles per gas type,
  with heat capacity Σ moles × specific heat. Only "active turfs" run, and settled ones sleep. Because tile-by-tile
  sharing spreads too slowly, "excited groups" average whole regions periodically. **What went wrong:** cost scales
  with how many gas types are present (`react()` and `share()` loop over them); a 900-tile excited group cost about
  900 ms; excited groups "nearly totally broke around about 2016" and nobody noticed for about four years; sharing
  that isn't portioned exactly drives moles negative; groups "fill the space given to them, so be careful with open
  plan stations"; turfs flicker between sleeping and waking.
  https://github.com/tgstation/tgstation/blob/master/code/modules/atmospherics/Atmospherics.md
  **Lessons:** a fixed, small species list beats an open dict; conservation needs a test, not care; sleeping
  is an optimization that needs its own determinism and correctness tests.
- **SS13 ZAS (Baystation) vs per-tile.** Zones of tiles share air instantly, which makes dramatic decompression but
  lagged badly ("ten minutes of processing every bomb", per player reports) because zones rebuild constantly when
  walls break. Players also found per-tile systems absurd: one end of a room on fire while the other is open to
  space. https://paradisestation.org/forum/topic/14390-add-the-baystation-atmos ,
  https://paradisestation.org/forum/topic/5207-can-we-speed-up-linda
  **SS14 "Monstermos"** batches connected tiles into one volume and runs a separate breadth-first search for
  explosive depressurization. A recent bug there: firelocks read stale airtightness data until the next atmos tick,
  so gas leaked and players could space a station step by step.
  https://hackmd.io/@ArtisticRoomba/r1gExUNLxl
  **Lesson:** room models are cheap and dramatic, but derived topology (rooms, airtightness) must be recomputed
  inside the same step as the destruction that changed it. Overdrive just fixed the same class of bug for heat (power
  recomputed after a substep that destroys cells).
- **Oxygen Not Included.** One element, one mass and one temperature per cell (the "one element per cell rule").
  Gases layer by molar mass, there is no ideal gas law, and pressure is just mass. **Exploits come straight from the
  representation:** liquid airlocks (a cell of liquid blocks gas), and the overpressure bypass, where buildings check
  only the element in one cell, so a sliver of liquid lets them overfill. That is the basis of whole meta designs.
  https://oxygennotincluded.wiki.gg/wiki/One_element_per_cell_rule ,
  https://kleiforums.com/forums/topic/98333-a-semi-comprehensive-list-of-the-un-physics-of-oni/
  **Lesson:** one element per cell can't represent "air with 2% CO", which is exactly the chemical-spill and smoke
  case. Overdrive needs a *mixture* per gas cell or room. And any rule that reads a single cell (rather than a
  reduction) becomes an exploit and a rig dependence.
- **Dwarf Fortress.** Liquid depth is 7 levels per tile, with falling, spreading and "pressure" that teleports water up
  to the source height. Gameplay thresholds sit on depth (at 4/7 dwarves won't path; 7/7 drowns). Temperature and
  moving fluids are the classic frame-rate killers; `[TEMPERATURE:NO]` is the standard advice, with side effects
  (obsidian never cools).
  https://dwarffortresswiki.org/index.php/DF2014:Depth , https://dwarffortresswiki.org/index.php/v0.34:Temperature ,
  https://dwarffortresswiki.org/index.php/v0.31:Pressure
  **Lesson:** quantized levels are cheap but not conservative, and fluids dominate cost. Thresholds on depth are a
  good gameplay interface; Overdrive's version is thresholds on room water level, in metres.
- **Noita.** Every pixel is a material. The world is split into 64×64 chunks, each with a dirty rect so only changed
  pixels update, and chunks update in a checkerboard so they can run on many threads.
  https://80.lv/articles/noita-a-game-based-on-falling-sand-simulation/ , GDC talk:
  https://gdcvault.com/play/1025695/Exploring-the-Tech-and-Design
  **Lesson:** sparse, dirty-region updates are where the speed comes from. Overdrive's tile is mostly air at ambient
  conditions; a field that sleeps per chunk (as SS13's active turfs do) is the Phase 2 "Scale" lever, and it must
  stay deterministic.
- **Teardown.** The world is voxel volumes. Destruction is synced by sending *commands* replayed in the same order,
  never voxel data. Join-in-progress needed the whole command history, so it had to be capped and then disabled after
  many changes. https://80.lv/articles/teardown-developer-breaks-down-multiplayer-and-voxel-destruction-tech
  **Lesson:** this matches Overdrive's replay-first rule (B2). But replay-only state gets expensive over time, so
  saves need a full field snapshot plus the intent log after it, which means the save format must carry every field.
- **Barotrauma.** Water and oxygen are per *hull* (a room volume), flowing through *gaps* (openings, doors). It is
  cheap, the game is built on it, and players reason about it well.
  https://barotrauma.fandom.com/wiki/Maintenance
  **Lesson:** per-room liquid is enough for flooding and diving gameplay.
- **Engineering literature.** The NIST CFAST two-zone fire model (each room has a hot upper layer and a cool lower
  layer, with flows through vents) is the validated, cheap way to get smoke layers and room heating without CFD.
  https://pages.nist.gov/cfast/ . NIST FDS is the per-cell version (mixture-fraction combustion, LES), and far too
  heavy here. https://pages.nist.gov/fds-smv/ . Stam's "Real-Time Fluid Dynamics for Games" (semi-Lagrangian, stable
  at any dt, but not conservative):
  https://www.dgp.toronto.edu/public_user_data/people/stam/reality/Research/pdf/GDC03.pdf . Amanatides & Woo's voxel
  traversal gives exact per-cell ray lengths: http://www.cse.yorku.ca/~amana/research/grid.pdf . Sparse grids at
  scale: OpenVDB, https://www.openvdb.org/ . *(These five, and the Huggett 13.1 MJ/kg, SFPE yield and Purser FED
  figures, are from memory, not fetched this session. Check them before they go into `docs/`.)*

## Recommendation

### Design now (Phase 1, before the protocol and save v0 freeze)

1. **A field registry, with the grid as a structure of arrays keyed by it.** Each field declares: its name, dtype,
   **SI units, as a per-unit-volume quantity**, mechanism (A–E), conservation law (conserved / sourced / derived),
   **its resolution** (the rig's cell, or a fixed size in metres, or per room), its boundary condition, its saved or
   derived status, and its snapshot channel and quantization. This lives in `data/` YAML and loads under B12.
   `MaterialGrid` gets `fields: dict[str, array]` instead of a named attribute per field. Each solver owns its
   fields and declares what it reads. The cost is about a day now; adding fields one attribute at a time becomes a
   save and protocol migration each time.
2. **Let a field run at a fixed resolution, independent of the rig, and make that the default for gas.** A gas grid
   at 0.2 m (or per room) is identical at every rig *by construction*: the resolution rule holds for free, and the
   dx⁻⁵ cost goes away. The fine geometry enters only through the **open area of each coarse face** and the **open
   volume of each coarse cell**, measured from fine cells. That is volume overlap, the rule the repo already uses for
   sources. Closed doors and vents are entities that set an aperture.
3. **Reserve the gas-mixture representation now, even if only O2 is live.** A fixed species list from `data/`
   (N2, O2, CO2, CO, H2O vapour, smoke, plus two or three generic "agent" slots for toxins and spill vapours). The
   state is moles per m³ per species, float32, and pressure is derived. Never an open dict (the SS13 cost scaling),
   and never one species per cell (the ONI exploits). Start **per room with a portal graph and orifice flow**, which
   is also the cheapest honest convection (CFAST-style two zones later).
4. **Put fuel and O2 into the Phase 1 fuel model.** Fuel kg/m³ per cell, separate from integrity. Heat release is
   the burn rate × the heat of combustion, limited by available O2. It produces CO2, CO and smoke at declared yields.
   It closes the known gap, and it is testable in closed form: a sealed room's O2 should fall linearly at
   P/13.1 MJ/kg until the flame goes out. Without it, the crate's gated outcome will flip later (see the top).
5. **Make the snapshot and save formats channel-generic before the first golden fixture is committed.** Each
   channel in the header carries its name, shape, cell size in metres, origin, dtype, units, quantization
   (scale/offset), compression and byte size; a per-room channel is a table keyed by room id, not a grid. Readers
   refuse unknown *required* channels and ignore unknown *optional* ones (declared per channel), so a new field is
   additive, not a version bump. Today's `snapshot()` returns a single `shape` and fixed keys, which would make every
   new field a protocol break. The save is the same: a list of `(field, dtype, shape, bytes)` records plus the
   registry version.
6. **Rig memory budgets declared per field.** The rig YAML gets a memory budget, and the registry sums declared bytes
   per cell × cells (state + snapshot + solver temporaries) against it at load. Then "add a field" fails loudly on the
   max profile instead of swapping. Wire it into B5.
7. **Bodies integrate doses; sensors read reductions.** Sensors that read a body's air are a mean over the cells or
   room it occupies, like `RegionSensor`. Dose (FED, rads, breath) is body state, and that matters for Phase 4's agent
   homes in save v1.

### Defer (and say so in "Known gaps")

- Per-cell gas, a velocity field and a pressure-projection solver (Stam / FDS style): only if a tile needs gas clouds
  drifting through open spaces that rooms can't model. The outdoor alley is one big zone with a wind term.
- Per-cell liquid with a free surface: rooms with a water level cover flooding and diving; floor puddles are a
  surface layer.
- An illuminance grid: start with per-agent line-of-sight rays.
- Electrical networks, RF and radiation: these are entity graphs and rays, so none needs grid state. Add the material
  columns (`mu_light`, `mu_rad`, `mu_rf`, `resistivity`) as needed. The registry makes columns cheap.
- Enthalpy instead of temperature: worth deciding before save v0, but it can wait until melting is a feature. If
  deferred, record it, because it changes the state variable of an existing saved field.

### Expensive to retrofit, ranked

1. **Snapshot / wire protocol** with a fixed channel set and a single shape: two codebases (Python and GDScript), with
   golden fixtures on both (B3).
2. **Save format** that names fields individually: every later field is a migration (B4).
3. **Gated outcomes recorded without a field that changes them** (fire without O2): the tests themselves must be
   re-derived.
4. **The cell-count memory model**: 14 B/cell today. Per-cell gas on the max rig would add 32 B/cell (160 MB) plus
   solver temporaries. A rig budget catches this; finding out late means a redesign.
5. **Thin geometry that should have been an entity** (wires, pipes, vents, doors as cells): the thin-feature rule
   already forbids it. Holding to it keeps electricity and airflow on graphs.

Cheap to add later, if items 1–6 above exist: any new species, deposit kind, material column, ray channel or body
accumulator.
