# Bio-faithful integration: review of `docs/design/world_model.md` (design v3 part 1, 66310f4)

Reader: the Bio-faithful integration lens (`docs/code_review.md`), scoped to what part 1 decides that NPCs will live
with. Overdrive worktree `phase1/design-v2` at 66310f4. Maxim read at 4b773ef8 (read only, nothing modified).
Divergences are tagged **EARN**, **ANALOG** or **OPEN** (Maxim's `docs/plans/bio_faithful_roadmap.md` intents).
Numbers marked *from memory* need verifying before they reach `data/` or `docs/`, as part 1's own rule requires.

**Verdict.** Part 1 is a better substrate for NPCs than v2. One truth removes a whole class of percept divergence
(what an NPC learns no longer depends on the host), the surface skin is exactly the quantity touch needs, ignited
area fractions in metres give fire a position, and breach by open area in metres is something a body can actually
perceive. But two decisions in part 1 would force a caricature in part 2, and part 1 is the place to fix them,
because both freeze in the gas interface and the zone table before part 2 is written:
- **The gas interface can't express height.** That is the one swap it was built to make cheap.
- **"All destroyed solid mass goes to the zone's fines species"** puts a crater's worth of concrete into the air
  the NPC breathes and sees through.

Part 1 also has no law for the body as a participant in the world (heat, breath, contact) and no ledger term for
it. So part 2 can couple bodies to the world in only one direction unless part 1 makes room.

Counts: 2 BLOCKER, 7 SHOULD-FIX, 5 NIT.

---

## BLOCKER

### BM-1. The gas consumer interface takes a zone or a cell mask, never a position, so the two-layer swap it exists for still needs every consumer rewritten

**Location:** §2, "A gas consumer interface from the start": `gas.at(zone)`, `gas.over(mask)`; §8 (zone
temperature as a zone column; "a name is an identity").

**Failure.**
- **A body samples gas at its mouth and skin, at a height.** "Crouch under the smoke" (`gameplay.md` §2, fire
  row; `gameplay.md` smoke row: "crouch under the layer") is a decision about the height of the airway. Under
  `gas.at(zone)` the consumer passes no height, so when the two-layer zone arrives, every consumer must change
  its call to say where it is sampling. That is the refactor §2 says the interface prevents.
- **`over(mask)` is a mask of 0.1 m cells.** That ties consumers to the truth grid, which Phase 2's adaptive
  refinement (§1.2) changes. A consumer should say what it is sampling in metres.
- **The well-mixed zone isn't only missing a relief action. It gets the harm wrong.** In a compartment fire
  before flashover, the hot layer is typically 400–600 °C and the floor air within tens of degrees of ambient
  (*from memory*; CFAST-class two-zone results). One mixed temperature puts several hundred degrees at floor
  height. A crawling NPC is burned like a standing one, and the lesson it learns is "a burning room is uniformly
  lethal". That is a caricature of the most-taught fire survival behaviour there is.
- **Frozen names make it worse later.** §8 says a meaning is fixed for the life of the format. If the zone table
  freezes `temperature` and species fractions as single-layer columns in `phase1/protocol` (PR 6), a two-layer
  zone needs new names, and every NPC memory keyed on the old sensor names (N7 in v2) is orphaned.

**Fix.**
- The interface takes geometry in metres: `gas.at(point_m)` and `gas.over(shape_m)` (a sphere or box in metres,
  such as the mouth sphere in `maxim_senses.md`'s smoke row). A well-mixed zone answers every point in it with the
  same value. A two-layer zone, or a later gas grid, answers by height, with no consumer changed.
- Every reading carries the model that produced it (`well_mixed` now), so part 2 can tag the percept and a test
  can find every consumer that relies on the well-mixed assumption.
- Name the zone columns for what they are now (`mixed_temperature_c`, or reserve `upper_` and `lower_` columns
  absent until Phase 2), so the two-layer zone adds names rather than changing one.
- Record in Known gaps, with numbers: "no vertical gradient within a zone: floor and ceiling gas share one
  temperature and composition." Tag the missing smoke layer **OPEN**, with the two-layer zone as its producer.

### BM-2. "A strike that destroys solid mass moves it to the zone's fines species" makes rubble airborne, in the air NPCs breathe and see through

**Location:** §2, "Mass is never silently deleted"; §7, "destroyed solid mass goes to fines". This is a change from
v2 §4, which sent only "mass finer than any cell (dust, powder)" to the zone. Part 1 sends all of it, until Phase 2.

**Failure.**
- v2's species list (`world_v2.md` §2.1) has one "soot and fines" species, and research `architecture.md` gives
  soot `aerosol: true, extinction_m2_kg: 8700`.
- A 0.01 m³ concrete crater is about 23 kg (2300 kg/m³, *from memory*). In the 18 m³ sealed scene that is about
  1.3 kg/m³ of "air". With soot's extinction coefficient, K ≈ 11,000 m⁻¹, so visibility (about 3/K) is well under
  a millimetre. Even with a coarse-dust coefficient two orders of magnitude lower, the room is opaque.
- Any part 2 percept built on airborne particulate (visibility under P-E, airway irritation under P-C, smoke as a
  fear cue) then tells the NPC that hitting a wall fills the room with choking smoke. Rubble mostly falls; only a
  small respirable fraction stays airborne.
- **It is a physics error too, not only a percept error.** If fines count toward the zone's mass and heat
  capacity, 23 kg of dust in about 22 kg of air roughly doubles the zone's heat capacity, and the zone responds to a
  fire at half the rate.

**Fix.**
- Split the destination. Destroyed solid mass goes to a **per-zone settled deposit** (a floor inventory in kg, with
  no gas properties), and only a declared **airborne fraction** by material (data, *to be sourced*) enters an
  aerosol species. That aerosol settles at a declared rate, and soot stays its own species with its own optics.
- The ledger stays exact: deposit plus aerosol equals the mass destroyed. Phase 2's rubble then takes its mass from
  the deposit, which is the same foundation D22 asks for.
- Add a closed-form test: a strike in a sealed zone leaves the zone's gas heat capacity and extinction changed only
  by the airborne fraction.

---

## SHOULD-FIX

### BM-3. The body has no place in the world's laws or its ledger, so part 2 can couple bodies to the world in one direction only

**Location:** §3 (the law table), §4 (the ledger: about 1e-12 of the tile's energy per substep), §2 ("mass is
never silently deleted").

**Failure.** `maxim_senses.md` principle 2 says the world must model the body's exchange with the cells: uptake,
dose, heat flux into the skin. Part 1 has no body term at all.
- **Heat.** A resting body releases about 100 W (*from memory*), and a hand on hot steel draws hundreds of watts
  from the surface. The ledger's tolerance is about 0.1 J per substep (1e-12 × 1e11 J). A contact or a body's
  metabolic heat either enters the ledger as a declared flux, or it breaks the ledger, or it is left out, and the
  world never feels the body: a hand never cools the rail, and a crowded sealed room never warms.
- **Breath.** Resting O₂ uptake is about 0.25 L/min and CO₂ output about 0.2 L/min (*from memory*). That is
  negligible over a fire's minutes, but not over §9's day-long study in a poorly vented lab, where CO₂ air hunger
  is a cue `gameplay.md` lists. Without a mass term, "mass is never silently deleted" forbids it, or part 2 adds
  it outside the ledger.
- **Chunk sleeping** (§1.2) wakes on "a source". Unless a body is declared a source, a body in a quiet room sleeps
  the room around it.

**Fix.** Add a **body boundary** to part 1 as a declared exchange, not a body model:
- a per-body flux record (heat W, species mol/s) that the world applies through the ledger and the zone step, each
  physics step;
- contact as a face-table event (which faces, area in m², duration), with the flux from the closed-form contact law
  (BM-4);
- bodies count as sources for chunk sleeping.

The body's internal physiology stays in part 2 and Maxim. Part 1 only promises that whatever the body exchanges is
conserved. Tag the one-way coupling **OPEN** until this lands.

### BM-4. Skins are the right source for touch and burn percepts. Part 1 should publish what contact needs, and part 2 should read only that

**Location:** §3, heat-exchange row ("a surface skin on every exposed face … depth set in metres"); §8, per-face
state in a face table keyed by (cell index, face).

**Assessment.** Yes, part 2 should read skins. A burn on contact is set by the **contact temperature**, which for two
semi-infinite bodies is T_c = (b_s·T_s + b_k·T_k)/(b_s + b_k), with effusivity b = √(kρc). That is why 60 °C steel
burns and 60 °C wood doesn't. It needs the surface temperature (the skin's top node, not the cell mean, which at
0.1 m lags the surface badly under a flux: P1's numbers) and the material's k, ρ and c, which the material table
already holds. A cell mean would be the caricature.

**Three gaps.**
1. **One skin temperature per face, beside an ignited area fraction.** A 0.1 m face with 10% of its area alight
   carries one surface temperature. Burn damage is strongly non-linear in temperature (Henriques: the damage rate
   roughly doubles per degree above about 44 °C, *from memory*), so a touch at the face mean understates a touch on
   the lit part. That is §3's own principle (decide at the point) broken at the body. Fix: the face row carries the
   burning part's surface temperature (or the skin response at the face's flux levels, which P2's ignited fraction
   already computes) alongside the mean.
2. **Node depth versus contact time.** The probe's skin is 16 nodes over 5 cm, about 3 mm per node. Thermal
   penetration in 1 s is about 3.5 mm in steel and about 0.3 mm in wood (*from memory*), so a brief touch on wood
   sits inside the first node. That is fine if part 2 evaluates contact with the closed form from T_s and b, not
   from the node profile. Say so, so that nobody reads the second node as "the temperature under the finger".
3. **Not every exposed face has a skin.** "Every exposed face that exchanges heat" is every face that borders a
   zone, which is right. Faces that border the body are new (BM-3), and the contact draw must debit the skin, or
   the surface stays hot under a hand.

**Fix:** publish `surface_temperature_c`, `burning_surface_temperature_c` and the material id per face row, named
as identities under §8 now. State that body percepts read the face table, never cells.

### BM-5. Most of what a hand touches is thinner than the cells can represent, and part 1 doesn't say where it lives

**Location:** §1.1 (0.2 m and 0.05 m become verification grids); CLAUDE.md and `docs/architecture.md` ("thin
features must be at least two of the coarsest rig's cells thick"). Part 1 doesn't restate the thin-feature rule.

**Failure.**
- If the rule keeps "coarsest grid" and the convergence test runs from 0.2 m, a solid feature must be at least
  0.4 m thick. If it moves to the truth grid, at least 0.2 m.
- Door handles, railings, pipes, valves, tool grips and a lab bench's steel edge are all thinner than either. The
  coolant loop's hot pipe, the most obvious contact-burn hazard in `world_v2.md` §9, can't be cells.
- So the objects bodies touch most have no skin, no temperature and no contact law, or they are authored oversized,
  which changes their heat capacity and burns.

**Fix.** Part 1 restates the thin-feature rule under one truth, and names the container for sub-cell solids: a
lumped thermal element in metres (a pipe, a rod, a plate) with a closed-form exchange with its zone and the cells it
is mounted on, entering the ledger. Its surface temperature is published the way a skin's is (BM-4). If that's
Phase 2, record "no contact heat from features thinner than 0.2 m" as a known gap, and part 2 removes those hazards
from the lab table.

### BM-6. No radiant field to a point, so the only pre-contact heat cue still has no producer (BF-3, carried)

**Location:** §3 (flame feedback is per m² of fuel; zone-to-wall radiation is in P1's probe); `world_v2.md`
review BF-3; `maxim_senses.md` heat row ("Radiant heat does not exist in the world yet … known gap").

**Failure.** With gas well mixed (BM-1), the only spatial heat signal inside a zone is radiation from burning faces
and hot surfaces. Part 1 has the ingredients (ignited area fractions per face in metres, skin surface temperatures,
the face table), but no law that evaluates incident flux at a point. Without it, an NPC feels a fire on contact or
as the whole room's temperature, and retreat relieves nothing (BF-3). Part 2 can't add it without a world law,
because it is energy leaving faces.

**Fix.** Add "incident radiant flux at a point in metres" as a world query, built from the face table (view factor
from each burning or hot rectangle to a point, closed form), with a closed-form test (a disc or a plane source) and
a convergence test. Charge the flame's radiative fraction to the heat release once. Schedule it in
`phase1/fuel-surface`, or record in Known gaps: "no approach gradient within a zone; heat is felt only on contact
or as the zone temperature", with a scene's numbers.

### BM-7. Chunk sleeping's criterion names cells only, and could freeze the skins and face state that percepts read

**Location:** §1.2 ("uniform, has no sources, and whose halo is uniform … Results are bit-identical with sleeping
on or off").

**Failure.**
- **Uniform cell means don't imply a quiet surface.** A chunk whose cell means match can still have a skin
  relaxing toward its interior, or face rows bordering a zone whose temperature is still changing. If the chunk
  sleeps, the skin's surface temperature (BM-4, what touch reads) freezes at its last value.
- **The test as worded checks state, not percepts.** If region reductions or body samplers are later restricted to
  active chunks as an optimization, a sleeping chunk's sensors go stale while the cells are bit-identical.
- **Bodies must wake chunks** (BM-3), or a body in a quiet room exchanges with nothing.

**Fix.** Define quiet over everything the step touches: cells, the halo, every face row in the chunk (skin nodes,
ignited fractions, recession), the zones its faces border (no zone change this step) and any body in or touching
it. Extend the bit-identical test to the published sensor object (§9's `bincount` reductions) and the face table,
not only cells. Exact-zero only, as research `architecture.md` §3.5 says.

### BM-8. Dilation changes how fast an NPC thinks relative to its world, and it runs Maxim's wall clocks against a slow world

**Location:** §1.2, "When nothing safe is left to trade, the world dilates. The tick status reports the effective
time scale."

**Failure.** When the world runs at 0.5×, an LLM thought that takes 4 s of wall time lands 2 s later in world time:
the NPC thinks twice as fast relative to its world. Maxim's wall-clock mechanisms (drive drift and
`FailureMode.last_fired`, `ReflexRegistry(clock=time.monotonic)`, `NACConfig.temporal_window_seconds`, the
`LLMWorker` and `agent_loop` staleness defaults: v2 review BF-5 and BF-7) run at wall rate against a slowed world, so
hunger outruns the day, and causal windows span less world time than they claim. A budget decision becomes a change
in NPC cognition that nobody chose.

**Fix.** Part 1 states that dilation is visible to the lanes as an input, not only in a tick status line, and
names the consumer obligation part 2 must meet: thought latency floors (`d_min`) are in world time, and every Maxim
clock an NPC runs on is driven from world time (v2's P5, with the clocks BF-7 listed). Until P5 lands, tag
"Maxim's clocks run on wall time while the world dilates" **OPEN** and meter the time scale per physics step.

### BM-9. N6's percept recipe ("a volume reduction around a body part at least two coarse cells across") no longer works under this part

**Location:** §1.1 (one truth; coarse grids only for verification); §2 (no gas in cells); §8 ("air cells'
`temperature_c` stays cell temperature, and the zone temperature is a zone column"); research `sem.md` N6;
`maxim_senses.md` heat row ("skin temperature or flux from a volume average of the cells around each body part").

**Failure.**
- **A body part sits in air.** Air cells carry no gas state, so averaging them gives the zone's value, or a stale
  cell temperature (§8 doesn't say what an air cell's `temperature_c` means now; NIT-3).
- **A reduction that includes solid cells** averages a wall's interior into "skin temperature", which no receptor
  feels.
- **"Two coarse cells" now has no referent:** the coarse grid isn't simulated.

**Fix (part 2 decides; part 1 records the consequence).** Body thermal percepts come from exchange, not averages:
convection from the gas at the part's position (BM-1), radiation at the part (BM-6), and contact with skins or
lumped elements (BM-4, BM-5). Part 1 should say in §1.1 that cell-volume reductions are for structures (integrity,
breach), not for bodies.

---

## NIT

- **NIT-1. "CO pooling" isn't physics, so don't design for it.** CO (28 g/mol) has almost the density of air (29),
  so it travels with the hot smoke to the ceiling and doesn't pool. What pools is dense or cold gas: CO₂ (44),
  H₂S (34), propane (44) and cold N₂ from LN₂ boil-off (the cryo store, BF-9). BM-1's height-aware interface covers
  all of them. Don't bake a "CO pools" scenario into part 2 or part 3.
- **NIT-2. Smell is impossible within a zone, and that is fine for now.** Per-zone gas gives an odour step at each
  door and no gradient inside a room, so source-seeking by smell can't exist. Maxim has no smell substrate either:
  `SensoryModality.SMELL` maps to text (`maxim_senses.md` §1). No NPC loses anything today. Part 2 must not build an
  odour sensor and describe it as a gradient. Tag **OPEN**, with the gas grid as its producer.
- **NIT-3. Say what an air cell's `temperature_c` is** under per-zone gas: a copy of its zone's, or not defined and
  refused by readers. A consumer reading a stale air-cell value is exactly what "a name is an identity" (§8) should
  prevent.
- **NIT-4. Rendering tiers must never feed percepts.** §1.1 makes `laptop`, `rig` and `max` decide how much of the
  snapshot the client draws. Part 2's line-of-sight percepts (P-E) must be computed on the server from the truth,
  never from what a tier drew. One sentence in §1.1 closes the door.
- **NIT-5. Retire `temperature_max` in §8's list.** The shipped `sem_env/bridge.py::RegionSensor` still exposes an
  interior cell maximum (v2 review NIT-2, physics S8). Under one truth it no longer varies by rig, but it is still a
  quantity no body senses. §8's "a new meaning gets a new name" is the place to retire it in favour of a skin-based
  surface temperature.

---

## What part 2 must decide because of part 1

1. **Where gas is sampled for each body percept** (mouth sphere and skin, height in metres) through BM-1's
   interface, and which percepts are tagged `well_mixed` until the two-layer zone arrives.
2. **The thermal path to the body:** convection from local gas, radiation at the part (BM-6), and contact from the
   face table and lumped elements by the effusivity closed form (BM-4, BM-5), replacing N6's volume average (BM-9).
3. **Who owns tissue temperature.** Maxim's planned `NociceptorSpec` (`autonomic_layer.md` §3.2) fires on a
   threshold of a body sensor value. A faithful burn is a time-temperature dose at receptor depth. Either the world
   writes a contact temperature and the body integrates it, which needs a body-side state Maxim doesn't have (a
   `world_set_axis` write is a value, not a flux), or the world computes tissue state, which puts physiology in the
   world. This is a candidate Maxim proposal: a body axis driven by an exogenous flux on world time. Tag **OPEN**.
4. **The body boundary's content:** metabolic heat, breath species and contact draw, as BM-3's flux record.
5. **What airborne particulate means to a body** (visibility, irritation), once BM-2 separates soot, dust aerosol and
   deposit.
6. **The lane's response to dilation** (BM-8): world-time `d_min` and the clock list.
7. **What rubble and fines are to an NPC before Phase 2:** a deposit on the floor is a percept (a pile, a dusty
   floor), and not yet an entity (BF-8's identity-in-metres rule still applies when it becomes one).

## What I checked and found faithful

- **One truth at 0.1 m (D20)** removes BF-8's percept-level break of the resolution rule: entity counts, sensor
  values and therefore NAc's keys no longer depend on the machine. Co-op NPCs on two hosts learn from the same
  world. This is a real gain for faithfulness, not only for physics.
- **Region reductions as one `bincount`, published once per physics step as a frozen object** (§9): one world clock
  for sensors, and a percept that can't be read mid-step.
- **CSG footprints in metres for "is this point on the region"** (§5): reach and touch targets are decided at the
  point, independent of the grid, which is what a hand does.
- **Breach by remaining thickness and open area in metres** (§3, §7): "is there a hole I can see or pass through"
  becomes a geometric fact a body could perceive, not a mass fraction.
- **Ignited area fraction per face, from a footprint in metres** (§3): fire has a position and an extent, the
  producer that a future glow or sight percept (P-E) and the radiant query (BM-6) need.
- **"Goes out" defined by the zone's O₂** (§3, S9): extinction is a world fact an NPC can observe the effects of, not
  a scripted event.
- **Mass conservation as a principle** (§2): right. BM-2 is about where the mass goes, not whether it's kept.
- **Chunk sleeping with the exact-zero criterion and a bit-identical test** (§1.2): sound in principle. BM-7 asks
  only that "quiet" cover the faces, the zones and bodies.
- **The tripwire as a per-thread `sys.setprofile` hook** (§6) keeps the simulation lane's determinism without
  touching pymaxim's wall-clock bindings in the agent lanes. That leaves P5 as the honest route for Maxim's clocks.
- **D23 (the lab as a physics benchmark first)** matches v2 review BF-3's last fix: NPCs aren't promised lessons the
  world can't yet produce.
