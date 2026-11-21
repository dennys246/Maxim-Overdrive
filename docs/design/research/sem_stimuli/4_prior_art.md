# SEM stimulus research 4: prior art in games, robotics simulators and embodied-AI environments

Research only; no repository edited. Context read in the `sem-stimulus` worktree: `CLAUDE.md`, `docs/design/npcs_and_sem.md`
§3.4 and §7, `research/fire_ladder/4_gamedev.md` and `6_biofaithful_sem.md`, and lesson 24.

Tags: **V** means I read it in a primary source (vendor docs, source, a paper, a developer's own talk text). **S**
means secondhand (an analysis, a talk summary, a search digest). **M** means from memory, not checked. **Most game-AI
internals here are secondhand.** Thief and F.E.A.R. are developer papers (V). Splinter Cell Blacklist and Alien:
Isolation come through Tommy Thompson's write-ups of developer talks (S). The Last of Us, Hitman and Dishonored are
thin (S/M).

## 0. The answer in brief

1. **Nobody ships what Overdrive wants.**
   - Game AI delivers *percepts*: designer-filtered awareness states, tuned for the player, with sanctioned cheats.
   - Robotics simulators deliver *instrument readings*: physical, noisy and clocked, but their thermal cameras render
     *authored* temperatures.
   - Embodied-AI suites deliver pixels plus privileged extras.

   World-computes-the-stimulus, Maxim-transduces has no exact precedent. MuJoCo and TDW's Clatter come closest.
2. **MuJoCo puts the boundary where lesson 24 does.** Touch is a sum of physical normal forces. Its `noise`
   attribute "does not affect the simulation", so the consumer applies noise. Period and delay are declared per
   sensor and are deterministic.
3. **Privileged channels creep in by convenience.** Examples: UE's Team and Prediction senses, ML-Agents' ray tags,
   Malmo's `ObservationFromNearbyEntities`, AI2-THOR's `Hot/Cold/RoomTemp`. Suites that cared fenced them by
   namespace (DMLab `DEBUG.`), declared group (Isaac Lab) or removal (Habitat 2020).
4. **Removing an oracle makes agents look worse, and that is the honest number.** Habitat's PointNav winner fell to
   SPL 0.21 without GPS+Compass (S).
5. **Interest management must be deterministic and observer-blind.** Games budget perception by wall time (UE sight,
   5 ms per tick, S) and by distance to the player. Both break Overdrive's rules.
6. **The prior art's leak test is ablation.** Overdrive can do better with an invariance test: change a
   privileged-only quantity and require bit-identical NPC inputs.

## 1. Game AI perception

**Unreal Engine AI Perception (V, Epic docs).**
- Actors register as stimulus sources for chosen senses.
- The senses are Sight (radius, lose-sight radius, peripheral angle), Hearing (from `Report Noise Event` within a
  range), Damage, Team ("a teammate is nearby"), Touch and Prediction (a target's location N seconds ahead).
- A stimulus carries Age, Expiration Age, Strength, Stimulus and Receiver Location, Tag and Successfully Sensed. Max
  Age 0 means "never forgotten".
- Sight is time-sliced: `MaxTimeSlicePerTick` 5 ms in the 4.24 source quoted on the forums, plus `MaxTracesPerTick`.
  Users report "several seconds" of sight lag with many AIs (S).
- *It exposes percepts about actors, not physical quantities.* Hearing is a designer event (lesson 4's
  anti-pattern). Team and Prediction are oracles.

**Unity ML-Agents (V, Learning-Environment-Design-Agents).**
- Observe "what you would expect a human to be able to use", with "ideally no extraneous information".
- Normalize to [0, 1] or [−1, 1]. Positions go "in relative coordinates wherever possible".
- Ray and grid sensors return one-hot *tags*. Stacking gives "limited memory".
- Nothing on privileged information.

**Thief: The Dark Project (V, Leonard, GDC 2003, via Gamasutra).**
- Each object has an "intrinsic visibility" in 0..1 from lighting, movement and exposure. Vision uses ordered
  viewcones, including a backward motion-only "spidey-sense" cone.
- Sound propagates "through the world's 3D geometry" with "attenuated awareness values".
- Awareness is discrete states, "the only representation of the internals … exposed to the designer". Rises pass a
  time filter. Falls decay through a "capacitor".
- "Sense links" are "the primary memory of the AI" and spread by verbalization, "with controls … to constrain
  knowledge cascades".
- "Free knowledge" infers a target's movement "without overtly demonstrating cheating".
- Sensing costs "a non-trivial amount of the AI's CPU budget". It is ordered cheapest-first, with rate scaled by game
  state.

**F.E.A.R. (V, Orkin, GDC 2006 paper).**
- Each AI's sensors keep "an up to date list of potentially valid cover positions".
- A squad coordinator sees "from a bird's eye view … everyone at once".
- Dialogue made the coordination legible. Sometimes it replaced behaviour: "I need reinforcements" had no mechanism
  behind it.

**Splinter Cell Blacklist (S, Thompson on Walsh, GDC 2014).**
- A "coffin"-shaped vision cone, with raycasts to eight bones.
- Sound distance is summed through chokepoints: 10 m through a door can count as 50 m.
- Hearing is *weaker when the camera isn't looking at the NPC*, and cones shrink on low difficulty.
- Barks report what a guard perceived.

**Alien: Isolation (S, Thompson citing Bray, nucl.ai 2016).**
- The director "always knows" where the player is but doesn't tell the alien: "the alien has to figure it out for
  itself".
- The director does send *hints* (jobs near the player), and a menace gauge withdraws the alien when tension peaks.
- The alien's senses are footsteps, gunshots, the motion tracker at about 1.5 m, and rear raycasts.

**Thin evidence.**
- TLOU's human AI is FSM-based. TLOU2 added a middle awareness state (S).
- Enemies ignoring Ellie in stealth is widely reported (M).
- Hitman's disguise "enforcers" are M. Dishonored: nothing primary found.

**Known failure modes.**
- *Omniscient AI:* directors, coordinators, free knowledge, Team and Prediction, all deliberate.
- *Unreadable AI:* the reason for barks and awareness meters. Every studio above spent real effort on legibility.
- *Load-dependent perception:* UE sight lags under many agents (S).

## 2. Robotics simulators

**Gazebo (V, classic sensor-noise tutorial; S, gz-sensors thermal docs).**
- Gaussian noise per ray beam, per camera pixel (GPU shader, then 8-bit) and per IMU component.
- IMU bias is "sampled once at simulation start", then fixed. Orientation is not noised.
- The thermal camera reads a temperature *assigned* to a model (`<temperature>` in K, or a heat-signature texture
  between `min_temp` and `max_temp`). The older hector plugin marks hot objects by colour.
- **There is no heat transfer behind the image.**

**MuJoCo (V, `doc/` on `main`, fetched 2026-11-20).**
- Touch: contacts inside a site's volume, re-projected along the normal so soft contacts don't escape. The output
  is "a non-negative scalar … adding up the (scalar) normal forces".
- `noise` "does not affect the simulation; it serves as a convenient location for storing standard deviation".
- `cutoff` clamps the output. `delay` reads a history buffer at `time − delay`. `interval = "period phase"` sets a
  recompute period that need not be a multiple of the timestep, with the phase fixed at reset.
- The pipeline is "entirely deterministic and reproducible", but only "within a single version, on the same
  architecture".
- The "unsorted" contact reduction is "potentially non-deterministic".

**Isaac Sim / Isaac Lab (S, docs via search).**
- Physics sensors are contact, IMU and effort, with `sensor_period`. A sensor's rate "cannot go beyond the physics
  frequency".
- Isaac Lab sorts observations into named groups. `enable_corruption` applies a group's noise; by convention a noisy
  `policy` group sits beside a clean, privileged `critic` group, for asymmetric actor-critic and student-teacher
  training.
- No native thermal camera found (M).

## 3. Embodied-AI environments

**Habitat (S).**
- PointNav's noise-free GPS+Compass was removed in 2020, because "high-precision localization in indoor
  environments can not be assumed".
- 2020 added actuation noise benchmarked on a real LoCoBot, plus RGB and Redwood depth noise.
- The winner fell to SPL 0.21. Visual odometry later recovered most of the loss.

**ThreeDWorld (V, `Documentation/lessons`).**
- Clatter synthesizes sound "from physics-driven events": the collision, both masses, "audio materials" and
  relative velocity (Traer, Cusimano & McDermott, DAFx 2019).
- **Audio "isn't directly returned by the build"**, so agents can't react to it at runtime. The Multimodal
  Challenge pre-rendered .wav files.
- The semantic-states page states lesson 24 in its own words: an oven door "isn't actually ever 'open' or 'closed';
  rather, it is at an angle".
- Output data is opt-in (`once`/`always`/`never`) and covers all objects by default. Staying non-privileged is the
  experimenter's discipline.

**AI2-THOR (V, object-types docs).**
- "All objects have an abstracted Temperature value that can be either Hot, Cold, or Room Temperature."
- Booleans include `isCooked`, `isDirty` and `isBroken`.
- **The label oracle lesson 24 rejects, in a major benchmark.** That every object is returned at every step is M.

**Malmo and MineRL (V, Malmo schema 0.30; S/M, MineRL).**
- Malmo missions declare observation handlers in a versioned XSD. Many are oracles:
  - `ObservationFromNearbyEntities` lists "the positions of all entities" in range, seen or not;
  - `ObservationFromGrid` includes hidden blocks;
  - `ObservationFromDistance` gives the distance to named points;
  - `ObservationFromRay` gives F3-debug properties.
- MineRL agents got 64×64 pixels plus inventory (M).
- **Maxim's Minecraft integration is unread here.** Check which channels it uses before citing it.

**DeepMind Lab (V, `docs/users/observations.md`).**
- Player observations are `RGB_INTERLEAVED`, `VEL.TRANS`, `VEL.ROT` and `INSTR`.
- Privileged data sits under `DEBUG.`, split into "Player only" (`DEBUG.POS.TRANS`) and "Server only" (every
  player's health and eye position, the maze layout).

**Animal-AI (S).**
- 84×84 pixels. Velocity, health and later global position and raycasts are optional.
- Hidden tests were built only from the training objects.

## 4. Transfer

The target: a physics-authoritative server that feeds bio-inspired learning agents receptor-level stimuli. The two
tests are lesson 24's: could an instrument measure it here, and is it transduction?

| Lesson | Verdict | How |
|---|---|---|
| UE stimulus sources | **Applies with changes** | Register *emitters of physical fields* (a flame radiates, a collision emits sound), never "things to perceive". |
| UE Age and forgetting | **Doesn't** | Memory is Maxim's. The world delivers only the current value at the receptor. |
| UE Team, Prediction, Tag; ML-Agents tags; Malmo entities and grid; AI2-THOR temperature | **Doesn't** | Identities and futures no receptor senses. |
| UE `Report Noise Event` | **Doesn't** | A designer event (lesson 4). Sound comes from physics, as in Clatter. |
| Thief's visibility from lighting | **Applies with changes** | Luminance at the target is world physics, but Overdrive needs radiance at each eye with line of sight. Cones, rise filters and capacitor decay are transduction, so they are Maxim's. |
| Thief's sense links spread by speech | **Applies** | Knowledge spreads only through speech as a world input (§5.2). Range and time bound the cascades. |
| Free knowledge, Alien's hints, F.E.A.R.'s coordinator | **Doesn't** | A director may *act* through the world (make a noise) but never write to an agent's inputs. Keep Alien's split, an omniscient world and an agent that "has to figure it out", and drop the hints. |
| Barks for legibility | **Applies, on the client** | Legibility belongs to the client and to NPC speech grounded in the NPC's own state, never to extra NPC knowledge. |
| Chokepoint sound paths | **Applies with changes** | A portal-graph path length is a fair cheap propagation estimate if it converges (lesson 2). Camera-dependent hearing and difficulty-scaled cones **don't**: they leak the observer. |
| ML-Agents normalization | **Doesn't** | Deliver SI units (W/m², K, cd/m², Pa, mol/m³). Gain and compression are the receptor's. |
| ML-Agents relative coordinates; "what a human would use" | **Applies** | Stimuli are in the body frame, per body site. The human test is lesson 24's first test. |
| Gazebo noise, bias fixed at start | **Applies with changes** | Instrument noise is the device's (world). Receptor noise is Maxim's. A fixed bias fits keyed streams (§3.4). |
| Gazebo thermal from authored heat | **Doesn't** | Overdrive's physics-computed temperatures are a strength. Don't regress for convenience. |
| MuJoCo touch | **Applies** | A template for contact pressure per body region, with a fixed reduction order. |
| MuJoCo `noise` stored, not applied; `interval` and `delay` | **Applies with changes** | The world delivers clean values. Receptor latency and noise are Maxim's, but the world's sampling cadence per channel must still be declared. |
| MuJoCo per-version determinism | **Applies** | Pin the version in the log header. Cross-platform bit identity is a separate claim. |
| Isaac rate ceiling | **Applies** | Stimuli can't be sampled faster than world time. A crackle onset (~10 ms) needs sub-tick events (§9) or an honest band limit. |
| Isaac Lab groups | **Applies with changes** | Make "NPC" and "instrument/lab" declared groups behind a type and import boundary. A privileged path is for evaluation only and never feeds learning. |
| Habitat's GPS removal | **Applies** | Expect and report the drop. Calibrate noise from physiology, as Habitat used LoCoBot data. |
| TDW Clatter | **Applies** | The precedent for crackle and impact as physics-derived stimuli. |
| TDW audio not returned | **Applies as a warning** | Don't route hearing through an audio renderer. Define the stimulus at each ear as data (band levels, onset times) in the world, logged and deterministic. |
| TDW "door never open" | **Applies** | It agrees with lesson 24. AI2-THOR is the counterexample. |
| Malmo XSD manifest | **Applies (form only)** | Use a declared, versioned manifest per scenario. Most of Malmo's channels fail the receptor test. |
| DMLab `DEBUG.` namespace | **Applies with changes** | A naming convention isn't enforcement. Use a type plus the existing import-linter. |

## 5. Interest management: which NPCs get stimuli computed, and when

**Prior art.**
- UE's Replication Graph puts actors in spatial grid nodes, so they don't "evaluate each connected client
  individually" (V; Fortnite: 100 players, about 50,000 actors).
- Thief scales rate by game state. Half-Life skips sensing far from the player (V, per Leonard).
- UE sight slices by wall clock (S). Alien's director runs jobs front stage and backstage (S).

**For Overdrive:**
1. **Fidelity never depends on the player or the camera.** Half-Life's and Blacklist's rules give an NPC different
   stimuli depending on who watches, which breaks lesson 1 and determinism. Interest management may decide *when an
   agent steps*, never *what a stimulus is worth*.
2. **Budget by count, not wall time.** A wall-clock slice makes perception depend on machine load, the kind of
   determinism leak lesson 17 turns into a red gate. Limits are fixed numbers with a deterministic order.
3. **Cull with physical cutoffs.** For each channel, drop sources whose contribution at the body is below a declared
   SI floor, for example well under the 1 kW/m² warmth level for radiant flux. This is MuJoCo's `cutoff` turned
   into a culling rule. Test convergence: halving the floor changes the delivered value within tolerance.
4. **Separate harm from stimulus.** Burn dose and toxic uptake integrate in the world every tick for every body,
   because tissue is world physics. Stimulus *delivery* happens when the agent steps, as a pure function of its
   pinned frame (§7.2–7.3). A non-stepping NPC still burns.
5. **Open: stimuli that should wake an agent.** A slow-stepping agent must still get a strong onset, and smoke
   arousal is Maxim's gate. A world-side physical onset (dF/dt above a floor) that forces a step risks becoming a
   designer event. Decide with Maxim, and test it.
6. **Spatial hashing of emitters** only bounds the search (M, standard).

## 6. Sensor schemas and versioning

**Prior art.** SDF and Malmo XSD are versioned. ML-Agents fixes vector sizes. DMLab fixes names, types and shapes.
MuJoCo's determinism holds per version (all V).

**For Overdrive:** each channel declares:
- name;
- SI unit;
- body site and reduction, in metres;
- world cadence;
- receptor class (§7.1 N9);
- group (NPC or instrument);
- version.

Hash the manifest into the log header and the agent home.

**A schema change is a body change.** A learning agent has fitted the old units and reductions, and a new reduction
radius silently changes what it feels. So migrate the home, or mark it trained on vN. Extend the
`test_sem_compat.py` and drift-job idea to the manifest.

## 7. Testing that an agent can't read privileged state

**Prior art.**
- Habitat ablates: remove the channel, measure the drop.
- DMLab namespaces. Isaac Lab groups. Animal-AI holds out tests.
- I found no suite with an automated non-leak test (M, absence of evidence).

**Proposed, strongest first:**
1. **Invariance test.** Vary what should be invisible while holding physics fixed:
   - entity ids and allocation order;
   - material-table fields no receptor reads (flammability, heat of combustion);
   - grid resolution;
   - render tier;
   - another NPC's internal state.

   The delivered stimulus vector must be bit-identical, or within tolerance for dx. This is lesson 24's first test,
   made executable.
2. **Structural fence.** Instruments live where the NPC delivery path can't import them. A red gate asserts no
   `RegionInstrument` reaches `world_set_axis`.
3. **Provenance.** A delivered channel without a named receptor or in-world device fails (§7.4).
4. **Probes in experiments, not the gate.** If a linear probe decodes a privileged variable from logged NPC inputs
   beyond what physics explains, something leaks (M as practice).
5. **Measure reach.** Count how many channels, materials and body sites the invariance fuzz actually varies.

**Exploit risk.** Learning agents exploit simulator errors; OpenAI's hide-and-seek agents "box-surfed" on physics
bugs (S, details M). Conservation (lesson 3) is the defence, and stimulus channels inherit it.

## What I could not verify

- Current UE sight budgets (only a 4.24 quote).
- SDF `update_rate` wording.
- Whether Isaac Sim has a thermal camera.
- Whether AI2-THOR returns every object at every step.
- MineRL observation details.
- Hitman, Dishonored and TLOU internals.
- Maxim's Minecraft channels.

**Sources:**
- dev.epicgames.com: AI Perception and Replication Graph.
- UE forums (S).
- unity-technologies.github.io/ml-agents.
- gamedeveloper.com: Leonard 2003; Thompson on Alien: Isolation and on Blacklist (S).
- gamedevs.org: Orkin 2006.
- classic.gazebosim.org: `sensor_noise`.
- gazebosim.org/api/sensors (S).
- github.com/google-deepmind/mujoco `doc/`.
- Isaac Sim and Isaac Lab docs (S).
- aihabitat.org/challenge/2020 and arXiv 2210.06849 (S).
- github.com/threedworld-mit/tdw `Documentation/lessons`.
- arXiv 2007.04954 (TDW).
- ai2thor.allenai.org: object types.
- microsoft.github.io/malmo 0.30.
- arXiv 1907.13440 (MineRL).
- github.com/google-deepmind/lab `docs/users/observations.md`.
- arXiv 1909.07483 and the Animal-AI repos (S).
