# Fire and material states through SEM: what NPCs should sense, do and learn (bio-faithful lens)

Research only; nothing edited. Revisions: Overdrive `phase1/fire-research` at
`124ad83`; the SEM membrane in the `gates` worktree at `396ae10`; **Maxim `origin/main` at `437ec7b1`
(2026-11-20 13:49 -0700)**, read through `git show`/`git grep` only. Earlier docs cite Maxim `4b773ef8`; every Maxim claim
below was re-checked at `437ec7b1`.

Tags: **V** means I read it in a primary source or its abstract (named). **S** means secondhand. **M** means
from memory, not checked.

## 0. The answer in brief

1. **Flame volumes and radiation are what make fire learnable.** Today the only cue is contact (lesson 4).
   Radiant flux is the cue before harm: at 2 kW/m², pain comes about 140 s before blistering (§1).
2. **T18's labels are half right.** "Soaked" and "burning" derived from fields can't disagree with the world. But
   **"flammable" and "porous" as NPC sensors are oracles** no receptor senses (`npcs_and_sem.md::7.4`), and boolean
   labels on a whole entity break D25. Use continuous fractions.
3. **`ignite(power_w)` and `extinguish()` are god verbs.** NPC acts should be bodily, with held things. A fruitless
   act **succeeds as an act and fails in the world**; it is never refused with a reason that leaks the rule.
4. **Maxim plans the body side but has built none of it for fire.** The strongest pushback is the autonomic plan's
   "a burn is **not** added to the fear set".
5. **The physics ladder is a prerequisite, not a curriculum order.** Agents meet fire as a heat source first and
   start fires late.

## 1. What NPCs should sense (Q1)

### 1.1 The biology the design should copy

- **Noxious heat has its own receptor.** TRPV1 is "activated by increases in temperature in the noxious range"
  (**V**, Caterina et al. 1997, *Nature* 389:816, abstract), threshold about 43 °C (**S**, NCBI NBK5244). Skin pain
  starts at about 44–46 °C at the basal layer, about 0.1 mm deep (**S**, NIST firedoc; Hardy 1953 via PMC8300848).
  Warmth and burn pain are separate channels at one site (Maxim agrees: `autonomic_layer.md` R-1).
- **Radiant heat warns before it harms.** Time to severe pain vs second-degree burn on bare skin: 1 kW/m², 115 vs
  663 s; 2 kW/m², 45 vs 187 s; 5 kW/m², 13 vs 40 s; 10 kW/m², 5 vs 14 s (**V**, NOAA ALOHA "Thermal Radiation
  Levels of Concern", from FEMA 1988). **Pain leads damage 3–6×**: the window to learn to step back, which exists
  only if the world radiates.
- **Smoke smell is a waking-only alarm.** Odours woke sleepers on 92% of stage-1 trials; peppermint never in stage
  2, 4 or REM; irritant pyridine on 45% of stage-2 trials, none in stage 4; tones on at least 75% (**V**,
  Carskadon & Herz 2004, *Sleep* 27:402, abstract). Smell must be gated by arousal.
- **Animals use other fire cues.** Juvenile reed frogs flee toward cover at the sound of fire; "the rapid rise-time
  of the crackling sound" is the probable cue (**V**, Grafe et al. 2002, *Proc R Soc B* 269:999). Torpid dunnarts
  "arouse immediately" to smoke (**V**, Stawski et al. 2015, *Physiol Behav* 151:617, abstract).
- **Experience turns alarm into prediction.** Fongoli chimpanzees "calmly monitor wildfires and change their
  behavior in anticipation of the fire's movement" (**V**, Pruetz & LaDuke 2010, *AJPA* 141:646, abstract).
- **Flicker and contact are physics.** Pool flames puff at about 1.5 D^−1/2 Hz (**S**, Cetegen & Ahmed 1993 via
  arXiv:1803.10400), so flame volumes give flicker for free. Contact temperature depends on effusivity √kρc (metal
  feels hotter than wood at one temperature, **M**), so contact needs a skin–surface model.

### 1.2 The sensors, by channel

Every row follows the resolution rule. The value is a body-part reduction over a sphere at least two coarse cells
across, or an integral inside `World.advance`. It reaches Maxim through `world_set_axis(owner="overdrive_world")`
(`maxim_senses.md::2`). "Phase" is the fire redesign's.

| Channel | Receptor | World quantity (reduction) | Latency / scale | Needs |
|---|---|---|---|---|
| Radiant warmth | thermoreceptors | incident flux on each body part's surface (W/m²), then skin temperature from a skin model | seconds; metres | radiation from flame volumes (the redesign) |
| Burn pain | TRPV1-class nociceptors | basal-layer temperature from the same skin model; damage as a Henriques integral into `health` | 0.1–10 s | GL2b to feel it as pain; `health` carries it until then |
| Contact heat | thermo- and nociceptors | contact temperature from the skin–surface model (effusivity) | under 1 s | material k, ρ, c (already in the table) |
| Smoke irritation | chemical nociception (airway) | irritant/soot concentration at the mouth sphere | seconds; gated by arousal | buoyant smoke (Phase 2, known gap) |
| Accelerant smell | olfaction | **vapour** concentration at the nose (from evaporation, set by vapour pressure and flash point) | seconds | an evaporation and vapour field (Phase 2 with `soak`) |
| Flame sight | vision | luminous flame volume and flicker in line of sight | ~0.1 s | percept gating by line of sight (`maxim_senses.md` P-E, OD-C8) |
| Crackle | hearing | onset transients from fuel failure | ~10 ms | sound propagation (Phase 2) |
| Visibility loss | vision | soot optical depth along the line of sight | seconds | buoyant smoke |
| Structural weakness | sight of char, sound, proprioception on load | char depth or integrity at the touched or viewed surface | slow | the char layer (T17) |

**No receptor, no sensor:** flash point, heat of combustion and φ reach an NPC only as knowledge (experience, a
can's label, others; `npcs_and_sem.md::7.1`).

### 1.3 Derived labels: what T18 gets right and wrong

- **"Burning", "smouldering", "charred", "melting", "soaked"** are fine as **continuous structure sensors** in
  [0, 1] (burning-area, glowing-area, char-volume, melt and pore-loading fractions). They converge with resolution
  (sem.md N2). An NPC reads them only through a percept channel (sight, smell, touch), never as an omniscient
  `RegionInstrument`, which is "never an NPC's input" (`gates:src/simcore/adapters/sem/bridge.py`).
- **Boolean words are the problem.** "Soaked: yes" thresholds an entity mean: the D25 hazard T18 itself cites.
  Sem.md N2 says labels "never feed learning"; T18 says the bridge "derives labels". **They disagree; N2 is right.**
- **"Flammable" and "porous" fail the receptor test.** They are material constants (lesson 22's own words). As
  sensors they give every NPC unearned fire knowledge and teach Maxim *our* table. Humans perceive appearance ("dry
  wood", "a solvent smell"). Expose material **identity** as a noun through vision; let "wood burns" be learned or
  told. Flammability shown to the *player* belongs to the client.

## 2. Affordances (Q2)

**What exists.** `structure.ignite(power_w, radius_m)` ("it burns until extinguished") and
`structure.extinguish()` (`bridge.py::StructureModulator.affordances`). Lab verbs: no NPC emits a chosen wattage, and
"extinguish" deletes a heat source with no water, lid or oxygen. Fine for tests and a god-mode player, not NPCs.

**What NPCs should have**, each a body act that drives the physics:

| Act | What the world does | Phase |
|---|---|---|
| `light` a held fire starter (lighter, match, wax starter) | the starter's own cited flame, placed as a heat source on contact | redesign (wax starter is a ladder rung) |
| `apply` a held flame to a target | the starter's flame volume touches the target's surface; ignition is the physics' verdict | redesign |
| `carry` / `drop` / `place` | moves an item entity (a burning stick is an item whose flame moves with it) | needs item entities |
| `pour` (water or fuel) | adds liquid loading or pool liquid, absorbs heat, evaporates | Phase 2 (`soak` in T18) |
| `cover` / `smother` | places a solid over the fire, which cuts air supply | needs an O₂ field; until then, honest absence |
| `fan` / `blow` | adds air flow | needs convection |
| `step_back` / `move` | locomotion; flux falls with distance | needs bodies in the world |

**Representing preconditions without leaking rules:**

- **`requires` states only physical possibility at the actor** (holding a starter, in reach, fuel left), through
  `check_affordance_requires` on live frames (sem.md N5; `origin/main:src/maxim/embodiment/tool_bridge.py:521`).
  **It never predicts an outcome**: no "target is flammable".
- **A fruitless act is a success.** A flame applied to steel *happens*; the world shows no ignition. That is the
  `kindle` rule ("`applied` means placed, not ignited", T17). A refusal would leak the rule into error text, and
  under TF2 book a NEGATIVE on the tool, teaching "my lighter is broken" instead of "steel doesn't burn"
  (`origin/main:docs/plans/tool_failure_credit.md`).
- **Descriptions never carry outcomes.** Maxim's own counter-prior hearth keeps harm "discoverable by acting —
  NEVER in the description text… the world, not the words" (`origin/main:src/maxim/_data/components/items/cradle_false_hearth.yaml`).
- **Verbs live on the body or held item**, Maxim's own model for imagined entities (sem.md §1.4). `apply` is the
  starter's modulator with the target as a parameter, which sidesteps done-to/done-by (OD-C3).
- **No `target_effect` or `self_effect` on world fire entities**, or an NPC "is burned twice" (`npcs_and_sem.md::7.2`).

## 3. What Maxim has or plans (Q3), at `origin/main` 437ec7b1

| Topic | Found | Status |
|---|---|---|
| Frozen SEM types | `origin/main:src/maxim/embodiment/sem.py` `AffordanceSchema`: "SHAPE-FROZEN at 1.0 (CC3)… additive fields appended at the end stay non-breaking" | built |
| Maxim's own fire | `origin/main:src/maxim/_data/components/items/cradle_fire_pit.yaml` (`entity_type: hazard`, `heat_output 0.9`, `fuel 0.8`, `touch` writes `arms.thermal +0.6`); `cradle_false_hearth.yaml` (Exp 38 counter-prior) | constants; no physics |
| Burn as pain | `origin/main:docs/plans/autonomic_layer.md` R-1 (a burn is 0.04 of DRIVE discomfort, heard by no PainBus learner), §3.2 `NociceptorSpec`; `git grep NociceptorSpec origin/main -- src` finds nothing | GL2b **not started** (status 2026-10-18) |
| Heat need | autonomic_layer.md R-2 (corrective need is cold-only) | planned GL2b |
| Cause-keyed valence | autonomic_layer.md R-3 (valence keyed on the sufferer, not the fire) | planned |
| Fear set | `origin/main:src/maxim/decisions/nac.py:425` `DEFAULT_CLUSTER_FEAR_FAILURE_MODES = {"drive:health", "drive:oxygen"}`; autonomic_layer.md §1 invariants: "a burn is **not** added to the fear set" | built; a decision |
| Fear relief, extinction | `origin/main:docs/plans/fear_learning.md` | **deferred** 2026-10-17 |
| Proximity heat | `origin/main:docs/plans/deferred/sem_environmental_proximity_sensing.md`: v1 is "binary in-scene = exposed", with a Maxim-side field→drive map | **deferred**, zero code |
| World-owned sensors | `origin/main:src/maxim/embodiment/audio_localization.py:692` `world_set_axis`, "any declared root sensor" | built, root-only |
| Smell | `origin/main:src/maxim/agents/modality.py` `SensoryModality.SMELL` → `"text"` | no substrate |
| Delayed effects | `tool_bridge.py:580–590, 884` reads `entity_state` in the call; `origin/main:docs/plans/latent_forward_model.md` (line ~209) calls this a "live defect for this purpose" | planned (S0a) |

**Searched, nothing found:** `flammab` (0 files in `docs/` or `src/`); a world-physics, combustion or material
plan (`world physics` matches 4 docs, none a plan for it; `material` in `sem.py`/`spec.py`: no hits);
`thermorecept`/`olfact` outside `grounding.md`, `thalamic_relay.md` and `autonomic_layer.md`; any plan for a smoke or
odour sensor (`smoke` in `src/` is "smoke test"). Body YAMLs carry `damage_affinities` with a `fire` key: damage
typing, not sensing. `overdrive_refactor_candidates.md` holds embedding and determinism items, nothing on sensing.

## 4. Pushbacks and proposals to Maxim (Q4)

Each is a Phase 3 item under Maxim's process. Two are questions to existing plans, not new items (lesson 13).

**P-F1. Let a noxious burn reach situation fear.** *Argues against:* autonomic_layer.md §1, "a burn is not added
to the fear set" (the Wire-4 allowlist as a hivemind wire boundary). *Why:* fire fear is the textbook case of a
Pavlovian cue (flame, crackle, warmth) predicting a nociceptive US. Heat pain is a standard US in human fear
conditioning (**M**). With burns excluded, an NPC fears fire only once `drive:health` drops, so it learns the
**injury** and not the **pain** that precedes it by a factor of 3–6 (§1.1). *Evidence:* a scenario where radiant flux gives pain (`drive:<part>.thermal:noxious`) with no health loss on some
trials and health loss on others, showing Wire-4 situation fear forms only on the health trials.

**P-F2. Calibrate `NociceptorSpec` in physical units.** *Argues against:* §3.2 and §8's "threshold: <owner>",
calibrated against the cradle's +0.6 contact delta. *Why:* the onset is known (about 43–46 °C, §1.1). A world that
writes skin temperature in kelvin, with the sensor range declared, can set the threshold from biology instead of
from a scene's normalized deltas. *Evidence:* the game's closed-form skin model, plus a cross-tier test that the
noxious crossing time agrees at every grid. *This is a question to GL2b, not a new plan.*

**P-F3. Re-scope the deferred proximity plan so the host owns exposure.** *Argues against:*
`sem_environmental_proximity_sensing.md` v1 ("binary in-scene = exposed", plus a Maxim-side "field→drive mapping").
*Why:* a world with radiation computes flux at each body part. A Maxim-side map from `heat_output` to a drive delta
is a second, fabricated physics, which is the plan's own phantom-credit concern. Its revive trigger ("a homeostatic
drive must be relieved by *sensed* ambient environment") is exactly what Overdrive's warm-by-the-fire produces. Maxim keeps the hard question: how
tool-less pain attributes to NAc. *Evidence:* a run
where `core_temperature` moves through `world_set_axis` as an NPC approaches a fire, with no affordance call, plus
the attribution trace.

**P-F4 (existing: OD-A16 and latent_forward_model S0a).** Ignition is the clearest delayed effect: tens of
seconds under a given flux (**M**; the ladder's first rung measures it). *Evidence:* the ladder's ignition-delay time series, joined to each act's invocation id. *A question
to the existing plans, not a new item.*

**Not proposed, deliberately:**
- **An SEM label or modifier vocabulary** (the T18 "new SEM concept"). Fractions on the frozen types carry
  everything §1.3 needs. A label type would invite the oracle mistake.
- **A smell substrate:** a `modality: world` odour sensor already works as a cue; no evidence yet that text fails.

## 5. Is the validation ladder also a curriculum? (Q5)

The ladder (as given in the brief; results.md §5 at `124ad83` names flame volumes and a combustion-capable
material table, not the rungs) orders **physics** by complexity: ignite a slab, burn it, spread on one surface, a
wax starter lighting a stick, a crib. **An agent's order differs in one important way.**

- **Conceptualization, then control, then starting.** Pruetz & LaDuke's three stages of fire cognition put
  chimpanzees at the first (**S** framework, via Futurity; **V** "monitor… in anticipation"). Fessler argues children
  in fire-using societies master fire by middle childhood, with at least 19 societies exposing them by age three
  (**S**, Fessler 2006, *J Cogn Cult* 6:429).
- **"Experience removes fascination" did not replicate:** "contrary to the Exposure Hypothesis, more frequent
  exposure to fire in childhood was associated with more positive psychological associations with fire" (**V**,
  Murray, Fessler & Lupfer 2014, *Evol Behav Sci*, manuscript abstract).
- **Social fear learning is selective:** observer monkeys acquired fear of toy snakes and crocodiles, not flowers or
  rabbits (**S**, Cook & Mineka 1989, *J Abnorm Psychol* 98:448). I found no primary evidence of an innate human
  fear of flame. The faithful prior is prepared *learning*: tier 2 at most (`origin/main:docs/plans/deferred/behavior_tiers.md`).

**A curriculum that reuses the ladder's rungs in an agent's order:**
1. **A burning slab as a static heat source** (the ladder's rung 2): approach and avoid along a flux gradient, and
   find a comfort band (warmth vs pain). This is conceptualization.
2. **Hot-surface contact** (the slab after flame-out, or metal near it): the contact burn and the effusivity lesson.
3. **Fire as a process** (burning, then flame-out, then glowing char): delayed effects. This needs OD-A16, or the
   lesson is unlearnable.
4. **Control on one surface** (rung 3, spread on one surface): douse and step back. This needs Phase 2 liquids.
5. **Starting** (rung 4, a wax starter lights a stick): a tool act whose outcome is the world's.
6. **Anticipating spread** (rung 5, a crib): predicting where heat will be. This is the chimpanzees' "anticipation".
7. **Throughout:** observation of other NPCs, which needs Phase 5 social channels.

Rung 1 (piloted ignition) has no agent stage of its own; it lives inside stage 5.

**A confound Maxim already knows.** An LLM-primary NPC already "knows" that fire burns, so its fire behaviour
measures the prior, not learning. Maxim built the counter-prior hearth for exactly this (Exp 38). Any claim that
NPCs *learned* fire must be measured substrate-side, or with a counter-prior material (a harmless-looking fuel, or a
fire-like display that isn't hot), and under D1 game-native pressure only.

## 6. Recommendation (Q6)

**The fire redesign must expose to the SEM bridge:**
1. **Fields a body can sample:** gas temperature, **incident radiant flux at a point and orientation**, soot and
   irritant concentration, and later vapour per species, reduced to body parts in the world (closed-form and
   cross-tier tested).
2. **Surface temperature with k, ρ, c**, so the world computes contact temperature.
3. **Structure fractions in [0, 1]** (burning, glowing, char, melt, loading, integrity): lab instruments now,
   percept sources once senses are gated by position.
4. **Visible flame volumes:** luminous extent and flicker, so line-of-sight percepts have something to see.
5. **Receipts per act** carrying the invocation id, so ignition, flame-out and damage that come later can be
   credited (OD-A16, OD-A18).
6. **Material identity as a noun** (wood, cardboard, wax) for vision and descriptions, kept separate from
   combustion constants.

**It must never:**
- decide an outcome from a label or in the bridge (lesson 22, T18);
- expose flammability, flash point, heat of combustion or φ as an NPC sensor;
- threshold a whole entity's mean into a boolean the agent learns from (D25);
- refuse an act because the physics would make it fruitless, or put the outcome in description or error text;
- write `target_effect`, `self_effect` or `vital_metrics` on a world fire entity, or a second heat path into the
  body;
- feed an omniscient region instrument (`temperature_max` from anywhere) to an NPC;
- read the wall clock, or stamp anything but world time.

**Where the project's stance looks wrong for the agents:** (a) T18's flammable and porous sensors (§1.3);
(b) T18 and sem.md N2 disagree about labels; N2 should win; (c) `ignite(power_w)` and `extinguish()` are
unsuitable as NPC verbs; (d) until radiation exists, every fire lesson is contact-only and the
learn-before-harm window is zero. (d) is the strongest agent-side reason for option 1 (flame volumes, radiation) over option 3 in
`hot_surface_spike/results.md::5`. Option 3 may suit Phase 1's physics, but leaves NPCs nothing to learn from fire.

