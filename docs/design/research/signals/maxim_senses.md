# What a Maxim NPC can sense and feel, and what it needs from the world

Maxim at `4b773ef8` (read-only). Paths are relative to the Maxim repo root unless they start
with `src/maxim_overdrive`.

## 0. The answer in five lines

1. Maxim has **one proven way** for a world quantity to become something an NPC feels, and Overdrive can use it
   today with no Maxim change. The game computes a body quantity and writes it into a **world-owned root sensor**
   through `world_set_axis(owner=...)`. The body YAML gives that sensor `modality: world` and a drive with
   `drift_rate: 0`. Maxim then turns how far the value sits from its set point into drive pain. Minecraft's
   `oxygen`, `health` and `food` work this way (`_data/components/bodies/minecraft_player.yaml:82-130`,
   `embodiment/backends/minecraft.py:1-35`, `embodiment/audio_localization.py:692`).
2. **The world must model the body's exchange with the cells**: uptake, dose, heat flux into the skin and tissue
   damage. Maxim cannot do it, because a drive's drift is a fixed rate (`sem.py::drift_step`, `body.py:634`) and
   the hooks that would let something outside the drive move it (`CouplingSpec`, `ModulationSpec`) are parsed but
   never read (`autonomic_layer.md` §1.3 R-4). Maxim owns what the NPC feels: the set point, the comfort band, the
   pain and the learning.
3. **NPCs learn to avoid a hazard through the situation, not through its cause.** Wire-2 valence is keyed on the
   body that was hurt, not on the thing that hurt it (`autonomic_layer.md` R-3). What actually works is Wire-4
   situation-fear: a cluster of world sensors gets tied to a later pain from `drive:health` or `drive:oxygen`. That
   is the allowlist `decisions/nac.py:425`. Exp 60 earned this, though it only matched a tabular Q-learner (ledger
   T1-13 PARTIAL). So every hazard needs **a cue the agent can sense, distinct from the harm, before the harm
   lands** (the `is_in_water` lesson in `minecraft_player.yaml:162-177`), and **a pain on one of those two
   allowlisted drives**.
4. Two pieces of body machinery are missing, and most hazards need them. First, **burns as pain**: today heat on
   the skin is mild drive discomfort, at most 0.2, which no PainBus learner hears. The planned `NociceptorSpec`
   (GL2b) is not started. Second, **heat as a need**: no corrective need fires above the set point. See
   `autonomic_layer.md` R-1, R-2, §3.2 and §3.3.
5. **Where human bodies have no receptor, the faithful choice is no sensor.** Radiation, carbon monoxide and inert
   gases are deadly to people because nothing feels them. If the game added an "O2 pain" for CO, or a "rads pain",
   it would be a caricature.

## 1. Inventory of Maxim's sensing and body machinery

| Piece | Where | Status | Bio-mapping |
|---|---|---|---|
| `SensorReading`, `ModulatorResult`, `AffordanceSchema` (frozen 1.0), `Sensor` / `Modulator` protocols, `Entity` | `src/maxim/embodiment/sem.py:38-145, 746-830` | Real. The Overdrive bridge mirrors them. | none |
| Drive specs: `HomeostaticDriveSpec` (set_point, drift_rate, comfort_band, pain_scale, linear pain model only) and `EntropicDriveSpec` (drift_direction, deprivation and satisfaction thresholds) | `sem.py:182-245`; helpers `drive_pain_for_value`, `corrective_need_intensity`, `drift_step` at `sem.py:251-460` | Real, wired, tested. Shape-frozen: new fields mean a major bump. `CouplingSpec` and `ModulationSpec` are reserved, never read. | none |
| Drift tick | `embodiment/body.py::tick_vital_drift:634` | Real. There is also a legacy name-keyed drift for `fatigue`, `strain` and `exhaustion` (`body.py:668`). | none |
| Failure modes: `FailureTrigger`, `FailureMode` (threshold, any/all, persistent, recovery condition) | `sem.py:1463-1510`; `body.py::evaluate_failures:258` | Real. A failure publishes on the PainBus; drive breaches latch on entering a band. Tests: `tests/unit/test_transition_drive_pain.py`. | none |
| Body YAMLs | `src/maxim/_data/components/bodies/`. The base is `base_humanoid.yaml`: stamina, hunger, visibility, azimuth, and head, torso, arms and legs with integrity and `damage_affinities` (slash, blunt, fire). The infant variant (`infant_humanoid.yaml`) adds `hunger` and `thirst` (entropic), `core_temperature` (homeostatic), and `arms`/`head` `thermal`, `pressure` and `texture`. | Real. The cradle experiments use them (Exp 37, Exp 42). | none |
| World-owned sensors: `world_set_axis(owner=)`, `world_owned_sensors`, `live_world_set_sensors` | `embodiment/audio_localization.py:692`; `embodiment/backends/minecraft.py`; `runtime/bootstrap.py:560` | Real. **It writes root sensors only** (`audio_localization.py:727-733`), so it cannot set `arms.thermal`. | none |
| Drives present today | hunger, thirst, food (entropic); core_temperature, thermal, pressure, health, oxygen, azimuth-centeredness (homeostatic); stamina has no drive, only a failure mode (`exhaustion`) | Real. **There is no fear drive or curiosity drive.** Fear is Wire-4 cluster-fear plus `PainType.ANTICIPATED` from NAc. `agents/fear_agent.py` is a code and action safety reviewer, not an emotion. Curiosity is a deferred plan (`docs/plans/deferred/intrinsic_motivation_1_3.md`). | none |
| Corrective needs | `runtime/substrate_proposal.py:60`: matches substrings `temp`/`thermal` to "cold", `food` to "hunger", `health` to "threat". `oxygen` is deliberately left out, so surfacing must be learned. | Real. It only fires one way (R-2), and the substring match misfires on other drive names. | none |
| Pain taxonomy | `proprioception/pain.py`. `PainType` has motor types, tool types, `RESOURCE_EXHAUSTION`, `EXTERNAL_SIGNAL`, `SAFETY_VIOLATION` and `ANTICIPATED`. `PainKind` is NOCICEPTIVE, DRIVE, ANTICIPATORY, FRUSTRATION or EXHAUSTION. `classify_pain` treats `drive:<x>` as DRIVE, except `drive:health`, which is NOCICEPTIVE (`TISSUE_DAMAGE_DRIVES`). | Real. | none |
| PainBus with severity latch and subscribers (memory 0.4, Wire-2 0.3, NAc 0.3, Wire-4 0.3 plus the allowlist) | `proprioception/pain_bus.py` | Real | **FUNCTIONAL**. Sensitization kinetics and fiber classes or gate control are ANALOG (`bio_faithful_roadmap.md`, PainBus row). |
| `NociceptorSpec` (heat, cold, mechanical or chemical; above or below a threshold; a second receptor on the same sensor; `drive:<s>:noxious` is NOCICEPTIVE) | `docs/plans/autonomic_layer.md` §3.2 | **Planned** (GL2b). Not started, waits for the decomposition fence. | will be tagged at birth |
| Burn too weak to learn from (R-1); no heat need (R-2); valence keyed on the body hurt (R-3) | `autonomic_layer.md` §1.3 | Known defects; the GL2b fixes are planned. | none |
| `InteroceptiveOutcome` (signed record of what happened to the body; nociception, drive pain, relief, harm) | `sem.py:517-571` | GL2a is built but only records; nothing reads it yet. | none |
| `SensorEncoder` (a dict of sensors becomes an EC node; delta gate; P1 ranges; A4 gain on `world` only) | `similarity/encoder.py:708-860` | Real | EC: **FUNCTIONAL**. Attractor completion is ANALOG; theta coding is OPEN. |
| EC modalities: text, vision, `interoception`, `audio`, `world`. The last three are frozen-centroid (`ec.py:463`). | `similarity/ec.py` | Real. "audio" is in use for azimuth, not reserved. | FUNCTIONAL |
| `SensoryModality` enum: SIGHT, SOUND, TOUCH, **SMELL**, INTEROCEPTION | `agents/modality.py:109-131` | SMELL, TOUCH and SOUND map to **text**. There is no smell substrate. | none |
| Audio localization: azimuth by DoA, `place_code`, `listen` and `turn_left`/`turn_right` with a centeredness drive | `embodiment/audio_localization.py`; `similarity/place_code.py`; `base_humanoid.yaml` azimuth | Real (Reachy hardware and sim). An elevation axis is meant to need only one YAML sensor plus one call. | place_code **FUNCTIONAL** |
| Default Network: YOLO detections, behaviours, arbiter, thalamic gate filtering percepts | `default_network/network.py`, `default_network/gate.py` | Real, but only for **camera** detections. There is no non-camera vision input. | **NAME-ONLY** (a salience network; the DMN reorganisation is EARN, Stage B) |
| Thalamic relay (`Receptor` registry, `AfferentTrack`; a thermal dual-track as the first slice) | `docs/plans/thalamic_relay.md` | **Planned.** GL3.B0 has only a census and red gates. | none |
| Proximity sensing: a fire's `heat_output` reaching a body without touch | `docs/plans/deferred/sem_environmental_proximity_sensing.md` | **Deferred**, zero code. It revives when a drive must be relieved by the ambient environment the agent senses. | none |
| Reflexes: innate, keyword-matched on percept text, fire `damage_component` | `embodiment/reflex.py` | Real, but **text-triggered**, not sensor-triggered. | none |
| Damage routing: `damage_affinities` keyed by type name (slash, blunt, fire, cold, shock...) | `embodiment/spec.py:531`; YAMLs in `creatures/` | Real, open vocabulary. | none |
| Breathing, O2 and drowning | `minecraft_player.yaml` `oxygen` plus `is_in_water`; Exp 60 (`docs/experiments/exp60_drowning_avoidance_prereg.md`; B1 floor) | Real on Minecraft only: the **game** simulates the air store. Maxim has no model of breathing. | none |
| Toxins and chemical sensing | `items/poison_vial.yaml`: the `poisoned` failure mode is on the **vial's** own `toxicity` sensor, not on the drinker | No body machinery. Chemical sensing exists only as the `chemical` value reserved in `NociceptorSpec`. | none |
| Thermoregulation | `core_temperature` and `thermal` homeostatic drives | Real, cold side only (R-2). Sweating, shivering and drift that depends on exposure do not exist. | none |

## 2. Each world signal against Maxim

The pattern for every row below follows from the resolution rule. The game computes a **body-part reduction**: a
volume average over a sphere or box around the body part, at least two coarse cells across, so it reads the same
at every rig. A dose is a **time integral inside `World.advance`**. Each body model ships with a closed-form test
and a cross-tier test. The value reaches Maxim through `world_set_axis(owner="overdrive_world")`, on a sensor the
body declares. Declared ranges should follow the A4 range rule, so that a resting value sits at the midpoint
(`minecraft_player.yaml:84-98`). "Maxim change" items are proposals for Overdrive Phase 3, and each goes through
Maxim's own process.

| World signal | What consumes it in Maxim | How the world produces it from cells | Maxim change needed |
|---|---|---|---|
| **Immersion (water, liquids)** | `is_in_water` (a world cue) and `oxygen` (a homeostatic drive owned by the world); the Exp 60 pattern | Liquid fraction by volume overlap of the head and torso boxes with liquid cells. Head submerged when the head-box liquid fraction is at least 0.5. Needs only a static liquid material; no flow. | **None.** Wire-4 already includes `drive:oxygen`. |
| **Breath and air composition (O2, CO2)** | Air hunger: reuse `oxygen` or add a new drive | Game side, a lung store per body. Each turn it exchanges with the volume-averaged gas fractions at the mouth sphere, and metabolic use draws it down: an exact ODE with a closed form. **Faithful split:** felt air hunger follows CO2 or breath-holding, which humans feel strongly. Low O2 at normal CO2 is barely felt and shows up as falling `head.awareness` and `stamina`, then an `unconscious` failure mode. | A new drive name such as `air_hunger` would **not** be in the Wire-4 allowlist, so nothing would learn to fear it. Proposal: add it to the allowlist as an explicit set, reviewed (`nac.py:425`, where the hivemind ingest refuses names outside it). Proposal: a failure mode or reflex that lets unconsciousness block affordances. Today `requires` thresholds can do part of this. |
| **CO and inert gases** | Nothing, which is the faithful answer: no human receptor | A dose integrated in the body store (COHb uptake); silent damage to `awareness` and `health`. | None. The cue has to be indirect: smoke that comes with it, the smell of a co-pollutant, or **seeing another NPC collapse** (Phase 5 rumour). Proposal, later: learning from others' harm (`docs/plans/social_referencing.md`). |
| **Smoke and irritant gas** | Airway irritation, which is chemical nociception, plus reduced visibility | Irritant concentration at the mouth sphere becomes `airway_irritation`. The same field cuts visibility along the line of sight. **Smoke needs buoyancy (convection)**: by diffusion alone it pools instead of rising (a known gap in `docs/architecture.md`). | Proposal: `NociceptorSpec` with `modality: chemical` once GL2b lands. Until then, irritant damage goes through `health`. Odour as a `world` sensor with no drive works today as a fear cue. A real smell substrate is a separate proposal (SMELL maps to text today). |
| **Systemic toxins (spill, poison)** | Nothing today. The faithful target is a **nausea or malaise** drive that supports conditioned taste aversion. | Body burden from inhaled or ingested dose (first-order toxicokinetics, closed form), then delayed nausea and `health`. | Proposal: a malaise or nausea drive and a cue-to-outcome credit window that tolerates delay (CTA works over hours; Maxim's eligibility windows are short). Fix the poison model, which has the vial get poisoned instead of the drinker (`items/poison_vial.yaml`). |
| **Heat and radiant heat** | `core_temperature`, `arms.thermal`, `head.thermal` (homeostatic), plus `health` for burns | Skin temperature or flux from a volume average of the cells around each body part. A burn as a tissue-damage integral (Henriques/Arrhenius, closed form) written into `health`. **Radiant heat does not exist in the world yet**, so a fire is felt only by conduction through air, which is far too slow (known gap). | (a) `world_set_axis` for sub-sensors (`arms.thermal`), or declare per-part sensors at the root. (b) GL2b `NociceptorSpec` (heat) so a burn is pain and not 0.04 of discomfort. (c) A two-sided corrective need (R-2). Until then, burn to `health` carries the learning (NOCICEPTIVE, on the allowlist). |
| **Cold and wet** | `core_temperature` (the cold side works today) | Heat loss from conduction to air or water, with water about 25 times faster than air. | None beyond the same root-sensor limit. |
| **Sound** | `azimuth` with `listen` and `turn_*` (audio EC modality, place_code); speech as text percepts | Phase 2 propagation field, then head-relative direction of arrival from the source and path, and loudness at the head sphere. Loudness above the pain threshold goes to `health` (ear damage). | Elevation: one YAML sensor (designed for). Loudness as a world sensor: none needed. |
| **Light and visibility** | No vision substrate for a non-camera body. `visibility` is a sensor on the body itself, and Minecraft's `light_level` has no drive and no resting value. | Illuminance and line of sight should **decide which entities an NPC's percepts and sense tools may return**, not exist as a scalar to feel. | Proposal: gating percepts by the world's line of sight, at the sense-tool or auto-sense seam (`docs/plans/deferred/passive_sense_discovery.md`). A scalar `light_level` sensor is fine as context, but it gives no drive anything to do. |
| **Electric shock** | `health` and a damage affinity (`shock`), plus a lockout through `requires` | Current through the body from cell conductivity along a contact path (needs a circuit solver: expensive). | None for the damage. `NociceptorSpec` has no electrical modality; mechanical or heat is close enough, or route it to `health`. |
| **Radiation** | **No sense, faithfully** | A dose integrated per body, then delayed malaise and `health`. A Geiger counter item (a device entity whose clicks are sounds) is the game-native cue. | The malaise drive above. Never a rads pain sensor. |
| **Pressure and blast** | `health` through `damage_affinities.blunt`, loudness, knockback | Peak overpressure at the body's sphere from a blast source (Friedlander and scaled distance, closed form). Ambient pressure only matters for diving (barotrauma). | None. Mechanical `NociceptorSpec` later. |
| **Structural vibration** | `pressure` (infant arms only); legs have no sensor | Cell acceleration under the feet. Useless until structural collapse exists (Phase 2), because a cue that predicts nothing teaches nothing. | Proposal: a mechanoreceptor on the legs or feet (YAML only). |

## 3. The faithful order: my view

**First, real work for almost no world machinery:**
1. **Heat on the body, with burns written to `health`.** The heat field exists, and the drives and the pain path
   exist. The game only needs a skin reduction and a burn-damage integral with a closed form. A burn lands on a
   NOCICEPTIVE drive that is on the allowlist, so Wire-4 can learn "near hot metal or fire, then pain". The
   honest caveats: without radiation the cue arrives only at contact, and without GL2b the thermal channel alone
   is too weak to learn from. Health is what carries the learning.
2. **Immersion and breath.** This is a material flag plus a lung ODE. It reuses Exp 60's earned design
   (`is_in_water` as the cue, `oxygen` as the drive, a learned `escape` affordance) with no Maxim change. It is
   the highest-confidence item, because Maxim has already measured it.
3. **Cold.** It falls out of item 1 and gives `core_temperature` a two-sided world: shelter, fire, water.

**Second, real work but needs Phase 2 fields:**
4. **Sound direction,** once propagation exists. Maxim's orient loop is already built for it.
5. **Smoke and gas, with CO2 air hunger and silent hypoxia.** This needs convection first, or smoke behaves
   wrongly, and it needs the allowlist proposal for any new drive name.

**Caricatures if added without the matching body machinery:**
- **An O2 field with an "oxygen pain".** This is the owner's example. It teaches the NPC that carbon monoxide
  hurts, which is false. Model the body store, feel CO2 and breath-holding, and let hypoxia steal capacity
  silently.
- **A radiation sensor or rads pain.** People have no such receptor.
- **Toxins as immediate pain.** The real signal is delayed malaise, which needs a nausea drive and delayed credit.
- **Smell as a scalar mapped into text,** or **light as a felt scalar.** Neither gives a drive anything to do;
  each is a cue at best.
- **Vibration before collapse physics.** The cue would predict nothing.
- **Any hazard with no relieving affordance.** That is pain with nothing to do about it; the agent learns
  helplessness, not avoidance. Each signal needs its act: surface, step back, leave the room, open a vent.

## 4. A standard way to explore a new signal

Each step names the check that guards it.

1. **Receptor test.** Name the human receptor or drive: nociceptor, thermoreceptor, chemoreceptor for CO2, the
   nausea centre, or none. If there is none, the world gets an instrument entity, not a body sensor.
2. **Split physics from feeling.** The game owns exchange, dose and damage as a body model, with a closed-form
   test and a cross-tier test. Maxim owns the set point, the band, the pain kind and the learning.
3. **Reduction.** A volume average over a body-part sphere at least two coarse cells across. A dose is integrated
   in `World.advance`. It must never depend on whether a cell centre is inside the body.
4. **Pain kind and fear.** Decide DRIVE, NOCICEPTIVE or silent. Check membership in the Wire-4 allowlist and the
   0.3 and 0.4 learner thresholds.
5. **A cue before the harm.** Name the world sensor that separates the hazard cluster before the pain lands.
   Exp 60's Gate (ii) separability probe is the template.
6. **Relief.** Name the affordance that fixes it, and check the corrective-need table.
7. **Ranges.** A resting value sits at the midpoint. Use `modality: world`, `drift_rate: 0` and
   `world_owned_sensors`.
8. **D1 environment lens and routing.** Run the D1 environment lens. Any Maxim change goes to Overdrive's roadmap
   under Phase 3, with an issue and a plan in Maxim.

## 5. Proposals for Maxim (Overdrive Phase 3)

- P-A: `world_set_axis` for modulator sub-sensors (`arms.thermal`), so a world can own heat per body part.
- P-B: the Wire-4 allowlist reviewed as an explicit set for new body hazards (`air_hunger`, `malaise`).
- P-C: GL2b as planned. `NociceptorSpec` (heat and chemical first) and the two-sided corrective need, which
  Overdrive needs for faithful burns and irritants.
- P-D: a malaise or nausea drive with delay-tolerant credit (conditioned taste aversion), for toxins and
  radiation.
- P-E: percepts gated by the world's line of sight, at the sense-tool or auto-sense seam, for light and
  visibility.
- P-F, low: unconsciousness as a body state that blocks affordances; today `requires` and `failure_modes`
  only approximate it.
