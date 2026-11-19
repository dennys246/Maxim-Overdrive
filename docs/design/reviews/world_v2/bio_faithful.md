# Bio-faithful integration: review of `docs/design/world_v2.md` (v2 draft, d596418)

Reader: the Bio-faithful integration lens (`docs/code_review.md`). Overdrive worktree `phase1/design-v2` at
d596418. Maxim read at 4b773ef8 (read only, nothing modified). Every claim about Maxim cites the file it comes from.
Divergences are tagged **EARN**, **ANALOG** or **OPEN** (Maxim's `docs/plans/bio_faithful_roadmap.md` intents).

**Verdict.** v2's core split is right, and it is the most faithful framing so far: the world simulates matter, SEM
exposes it, and Maxim feels and learns. Fractions rather than labels, causes rather than outcomes, and no physics
inside SEM are all correct, and decision 11 (waiting defined in world time) settles delta 1's D1 properly. But four
things are wrong or missing, and each changes what the NPC learns:
- **The stale-refusal rule rests on a claim about Maxim that is false.** No Maxim tool path today keeps a refusal
  the game makes out of NAc.
- **The SEM membrane, as specified, hands NPCs numbers no body can sense.** Maxim generates a `read_<entity>_<sensor>`
  tool for every sensor, so a zone's O₂ or CO fraction becomes something the NPC can simply read.
- **The lab table's warning cues mostly have no producer in the world v2 schedules.** Well-mixed zones with no
  radiant flux give no heat gradient as an NPC approaches a fire, and no smoke layer.
- **The hybrid 1.5 draft hasn't changed since delta 1.** It contradicts the owner's option C, which v2 doesn't
  record anywhere.

Counts: 4 BLOCKER, 9 SHOULD-FIX, 5 NIT.

---

## BLOCKER

### BF-1. "Maxim's TF2 already excludes refusals the game makes before the modulator runs" is false, so a stale refusal books NAc on every Maxim path today

**Location:** `world_v2.md` §6, "A stale refusal is a percept for the next thought, never NAc credit"; §1 bullet 4.

**What Maxim actually does:**
- TF2 (`docs/plans/tool_failure_credit.md`, TF2 and Stage 1) governs only the **ToolPainBridge's** failure booking.
  The same plan says that for a never-run call, "`tool_dispatch` still books its NEGATIVE, as today" (Stage 1, red
  gate arm 2).
- `runtime/tool_dispatch.py::record_outcome` books to NAc unless `refused` is in `GATE_REFUSAL_KINDS`
  (`_learning_nac`). Anything else raises a `ValueError`.
- `GATE_REFUSAL_KINDS` (`tools/base.py`) can be produced only by Maxim's executor.
  `runtime/executor.py::_retag_body_gate_kind` re-types a gate kind returned by a tool body as `EXTERNAL_FAILURE`,
  loudly. The game can't mint one.
- `embodiment/tool_bridge.py::ModulatorAffordanceTool.execute` turns any `ModulatorResult(success=False)` into
  `ToolOutput(success=False)`, with no kind and its metadata dropped.

**So a stale refusal books a NEGATIVE, state-blind causal link on `tool:<entity>_<aff>` (delta 1 D2's exact harm),
whichever way it reaches Maxim:**
- returned from the SEM modulator;
- returned from a requires check (N5);
- returned from a later apply step reported as a tool result.

The rule is achievable only if both of these hold:
1. **The intent is applied outside Maxim's tool dispatch.** That is v1's "generate vs apply" (v1 §6 item 16).
   Neither v2 nor `docs/roadmap.md` Phase 3 lists it now. Today Maxim runs the tool *inside* the LLM turn, against
   whatever the modulator can see. There is no later apply step to be stale at.
2. **Maxim has a booking path for "your applied plan was overtaken" that writes only to the carryover and the
   outcome window.** The precedent exists: `tool_dispatch.py::book_machine_refusal` (#1085, owner re-decision
   #1185: "a refusal that no person made teaches nothing about the action or its situation"). Its scope is the
   planning drain only.

**Fix:**
- Correct §6. Replace the TF2 sentence with what Maxim does, citing `_learning_nac` and `_retag_body_gate_kind`.
- Add a P8: extend `book_machine_refusal`'s scope to intents a world applies later, as machine refusals at apply
  time. It argues against #1085's scope (the planning drain only), and keeps #1185's rule.
- Restore "generate vs apply" as an explicit prerequisite, by name.
- State the interim, as delta 1 asked: until P8 and generate-vs-apply land, a stale refusal is only a log record
  and a meter. It is never returned to a live Maxim agent as a `ToolOutput`.
- Tag the missing stale-plan learning signal **OPEN**.

### BF-2. N1 and N2, run through Maxim's tool generator, hand NPCs the silent hazards as readable numbers

**Location:** §7 N1 (`zone` entities) and N2 ("gas readings"); §9's cryo store ("none from the body") and "Study
participants … instrumented"; research `sem.md` §3a N1 (`gas_<species>_fraction` on zones).

- `embodiment/tool_bridge.py::generate_tools_for_entity` makes `sense_<entity>` (`EntitySenseTool`, every sensor)
  and `read_<entity>_<sensor>` (`SensorReadTool`) for **every** sensor on every entity it is given.
- No proximity, line-of-sight or receptor gate applies. P-E (percepts gated by line of sight) is a Phase 4 proposal.
- So if zones carry `gas_o2_fraction` and `gas_co_fraction`, an NPC in the cryo store calls
  `read_cryo_store_gas_o2_fraction` and knows what no human could feel. That is the caricature
  `maxim_senses.md` §0.5 and §3 warn about, delivered through a sense tool instead of a pain.
- It breaks §9's own premise ("silent hypoxia is invisible, so trust the instrument") and the exact Exp 2 negative
  control in `gameplay.md` §4 (CO with no cue must produce no avoidance).
- **This is already true in shipped code.** `sem_env/bridge.py` exposes `temperature_max` over all of a region's
  cells. That is an interior maximum no hand or eye can read, and a non-linear reduction over cells (see NIT-2).

**Fix:** add **N9, perceivability**. Each world sensor in `data/sem/vocabulary.yaml` declares how it reaches an
NPC, and the bridge registers sensors on entities only accordingly:
- `body`: a human receptor exists, so it is written to the body through `world_set_axis`;
- `percept`: an unaided human perceives it at range, such as visible smoke density, glow, a sheen or frost;
- `instrument`: only a device in the scene reads it, such as an O₂ meter, a CO alarm or a thermometer.

Odourless species fractions exist only on instrument entities that are placed in the scene. Zones expose only
`percept` quantities. A test asserts that no generated tool reads an `instrument` quantity except through an
instrument entity. The general fix is Maxim's: a reach or line-of-sight gate on generated read tools. Add it as P9,
joining P-E, arguing against `generate_tools_for_entity`'s ungated "every sensor is a tool".

### BF-3. The lab's warning cues and relief actions have no producer in the world v2 builds

**Location:** §9 table (columns "Warning cue" and "Relief action"); §2.1 ("An air cell's temperature becomes its
zone's"); §2.2 (zones well mixed, one enthalpy); §11 (no radiation, sound or light PR); `gameplay.md` §2, row
"Radiant and contact heat" (R-1: "without radiation, the cue only arrives on contact").

The charter asks whether each hazard has a cue the NPC can sense before the harm, and a relieving action. Checked
row by row against what v2 schedules up to PR 11:

| Room | Cue v2 names | Producer in v2? |
|---|---|---|
| Vented burn bay | glow | no vision substrate for a non-camera body (`maxim_senses.md` §1: the DN is camera-only); P-E is Phase 4 |
| | heat on skin | **No gradient exists.** Air takes its zone's temperature, and a zone is well mixed, so skin temperature is the same anywhere in the bay until contact. Radiant flux to bodies isn't designed: `architecture.md` research gives a 0.3 radiative share to *nearby solids*, not to a body. |
| | crackle | sound field is Phase 2 |
| | relief "retreat" | relieves nothing inside the zone, since no gradient exists to retreat down |
| | "smoke layer" | needs a two-layer zone (`physics.md` §6: "reserved, not built"). "Crouch under the smoke", gameplay.md's relief, can't exist. |
| Sealed test chamber | CO₂ air hunger | needs the lung model (Phase 4) and an allowlisted drive (P-B) |
| | smoke | needs visibility or irritant (P-C, P-E) |
| Cryo store | fog, hiss | fog is client-visual only, with no NPC percept until P-E. Hiss needs the Phase 2 sound field. |
| Coolant loop | hiss, steam, heat | same as above; a steam scald needs a skin-condensation flux in the body model (Phase 4) |

**Consequence.** In the lab as built in PR 11, the "What an NPC can learn" column is unlearnable. An NPC feels the
fire on contact or not at all. That is the "pain with nothing to do about it" case `maxim_senses.md` §3 calls a
caricature.

**Fix:**
- Add a column to the §9 table: the signal's producer, and the PR or phase that delivers it. Make the "learn" column
  conditional on it.
- Put **radiant flux to a body** in the fuel PR. It can be a view-factor reduction from burning faces, written in
  metres with a closed form for a disc or plane source, so the heat cue arrives before contact. If it can't go into
  the fuel PR, record "no approach gradient within a zone" as a known gap, with numbers.
- Record the two-layer zone as the producer the smoke-layer row needs, or drop "smoke layer" from the table.
- State plainly that before Phase 4 the lab is a physics benchmark with NPCs present, not a place NPCs learn.

### BF-4. The hybrid 1.5 draft contradicts the owner's option C, and v2 records neither the decision nor delta 1's D3 to D6

**Location:** `docs/maxim_upstream/hybrid_1_5_line_DRAFT.md` (unchanged since v1); `world_v2.md` §0 (no decision
recording option C), §6 ("The NPC still lives through T..T + d on its substrate").

Option C is the owner's choice: a reflex layer first, and a habit layer only once data earns it. The draft still
says:
- **The claim:** "Its substrate (reflexes, **NAc's learned action selection**, drives) carries it". That is
  agent-level NAc selection in flight, the habit layer, asserted as part of the hybrid from the start.
- **H1's battery** includes "find food and rest". Under option C those are deliberative jobs, not reflex jobs
  (delta 1 D3).
- **H3** uses `NAc.recommend_action` returning `None` as the trigger to deliberate. That is the "sometimes substrate,
  sometimes LLM" switch that `docs/plans/deferred/hybrid_substrate_reflex_runtime.md` rejects ("Why NOT
  `aut_mode="hybrid"`"). Its `None` mostly reflects `min_confidence` and the exploration setting (delta 1 D4).
- **H1's arms:** "zero latency" and "the world paused for each thought" are the same world-time arm, and the
  reflexes-off × latency control is missing (D5).
- **H4** measures time to a protective action, which cancellation can't change (D6).
- **The cross-references** point at v1 §4.3 and "Phase 3 items 11, 12, 13, 15, 16, 17". `docs/roadmap.md` Phase 3
  holds only items 1 to 9. v2 folds v1's list only by a line in "Supersedes".

**Fix:**
- Record option C as decision 19 in §0.
- Rewrite the draft to match it:
  - Stage 1: the claim covers the DN reflex layer on its own isolated NAc (BL-4, A3) plus the action already
    executing.
  - Name a withdrawal `Behavior` as new mechanism, pre-registered (the DN has none today: `default_network/behaviors/`).
  - Split H1's battery into reflex jobs and deliberative jobs.
  - Fold D4 to D6 into H1, H3 and H4.
  - Stage 2 (habit): a separate pre-registered experiment whose entry criterion is a Stage 1 result. It names "Why
    NOT `aut_mode="hybrid"`" as the decision it would revisit, and the evidence that would earn it (**EARN**).
- Fix the draft's references to v2 and to the roadmap's real numbering.

---

## SHOULD-FIX

### BF-5. §6 world-time latency mode: faithful in world time, but it lacks a floor, a failure rule and an honest account of the in-flight NPC, and Maxim's own wall-clock staleness defeats it

**Location:** §6, "Headless cradles and experiments use the world-time latency mode".

Blocking the host in wall time so that a thought lands at T + d in world time is faithful to decision 11. Inside the
world no tick is skipped, and the ANALOG tag (a declared constant, independent of content) is honest. Five gaps:

1. **d = 0 is waiting under another name.** A thought built on the state at T and applied at T means deliberation
   took no world time, which is exactly the "world waits" arm. Fix: the loader requires `d(kind) >= d_min(kind) > 0`.
   d = 0 is allowed only in a named reference arm of a pre-registered experiment, reported as "lockstep reference".
2. **In flight, the NPC today is a statue.** Until option C's reflex layer exists, the substrate during T..T + d is
   only the action already executing. The DN is camera-only, `ReflexRegistry` is keyword-on-text (delta 1 D3, D11),
   and drives keep drifting. The world doesn't wait, but the NPC effectively does. Fix: say so in §6. Meter
   "in-flight ticks with no substrate action" from PR 10, and tag it **OPEN** until the reflex layer lands. This is
   the evidence decision 7 asks for, so make it visible rather than letting "lives through it on its substrate"
   imply it is already true.
3. **Model failure in this mode.** Delta 1 D1 asked for a typed `thought_failed`, never a wall timeout. v2 is
   silent: the host blocks, then what? Fix: a model failure is a logged input, `thought_failed` at T + d. It is never
   an indefinite block and never a wall timeout.
4. **Maxim's wall-clock staleness drops the thought the host is blocking for.** The defaults:
   - `agents/llm_worker.py::LLMWorker(stale_threshold_s=5.0)`;
   - `runtime/agent_loop.py::_STALE_PROPOSAL_AGE_S = 35.0`;
   - `simulation/orchestrator.py`: 15 s, 30 s and 60 s.
   
   A real Maxim agent in a cradle discards on host seconds, whatever d says. Fix: name these, with v1 item 13 (a
   world-time deadline), as hard prerequisites of the mode with a real agent (delta 1 D8, which v2 drops).
5. **A cradle's d and live play's latency disagree.** An NPC cradled at d = 3 s but played at 1× on a model that
   takes 8 s lives a different deliberation tempo after the cradle. Its stale rate and its NAc temporal windows were
   calibrated on another one. Fix: set `d_min(kind)` in live play equal to the cradle's `d(kind)`, so the cradle's
   tempo is live play's floor. Meter the live distribution above it, and tag the gap **OPEN**, to be measured by
   H6. Pre-register d for Exp 64.

### BF-6. P3 is Maxim's own recorded prerequisite, not a pushback, and it asks the cerebellum to do a job its Bio-mapping doesn't claim

**Location:** §7 table, P3.

- **The diagnosis is right, and verified.** `tool_bridge.py` reads `entity_state` immediately after
  `modulator.execute` and calls `cerebellum.observe_from_action(actual=entity_state)`. With cells changing only in
  `advance`, `ignite` is learned as having no effect.
- **The framing doesn't need to be adversarial.** `docs/plans/deferred/sem_motor_binding.md` (header and the
  "divergence resolved by phasing" paragraph) already says that the Stage-5 "act-now-credit-later pending map
  remains mandatory before any NON-blocking dispatcher ships". Overdrive is that dispatcher. Framed as "the game
  triggers your recorded prerequisite", P3 is much easier for Maxim's process to accept than "the assumption is
  wrong".
- **The time scales.** `embodiment/cerebellum.py`'s Bio-mapping is "single-cue delta rule", and it explicitly
  doesn't implement climbing-fibre timing. Biologically, cerebellar forward models predict sub-second consequences.
  A slab melting minutes after `heat` is an action-outcome contingency, which Maxim's NAc causal links and their
  `temporal_window_seconds = 300` handle (`decisions/nac.py::NACConfig`, on the wall clock until #1361).
  - Routing a minute-scale transition into the cerebellum's "actual after this action" would teach it that a heat
    call has an effect it can't time.
  - Fix: split P3. The short form gives the cerebellum the state after the next physics step ("the flame took").
    The long form reports measured transitions to NAc's delay-tolerant causal path on world time. Tag the long form
    **OPEN**.

### BF-7. The Maxim proposals aren't yet in the shape Maxim's process accepts, and the clock list is incomplete

**Location:** §7 table (P4, P6 and P7 have an empty "Argues against"; P5 names lists, not decisions); CLAUDE.md
"Push back on Maxim" ("Name the decision you're arguing against").

- **The arguments exist, in `sem.md` §3b. v2 dropped them.**
  - P4 argues against `world_set_axis`'s root-only scope (`embodiment/audio_localization.py`, the "root sensors
    only" refusal).
  - P6 argues against the status quo of three additions after 1.0 with no version recorded, and against
    `ModulatorResult` having no CC3 marker.
  - P7 argues against the silent drop of metadata in `ModulatorAffordanceTool.execute`.
  - P5 argues against `body.py::evaluate_failures`' wall-clock `dt` and `FailureMode.last_fired = time.time()`.
- **Missing clocks** (delta 1 D11, dropped):
  - `embodiment/reflex.py::ReflexRegistry(clock=time.monotonic)`: cooldowns, habituation and sensitization;
  - `embodiment/cerebellum.py::prune_stale_models` on `time.time()`;
  - the staleness defaults in BF-5 item 4;
  - `NACConfig.temporal_window_seconds`.
- **Missing proposals:** P8 (BF-1) and P9 (BF-2).

**Fix:** restore the "argues against" text, with file and symbol, for every row. Add the four clocks to P5. Add P8
and P9.

### BF-8. Rubble as loose cells: real matter, but not yet a real object for an NPC, and an entity per cluster would break the resolution rule

**Location:** §4, last bullet ("For Maxim, a chunk is a real thing, an entity an NPC can perceive and use"); §7 N1
(`matter` entities, "rubble clusters; deferred"); §2.4 (`region_id`).

- **§4 and §7 contradict each other.** §4 promises an entity per chunk. N1 defers `matter` entities. As built, rubble
  is a snapshot channel for the client, not an entity, so no NPC can perceive or use it.
- **An entity per `ndimage.label` cluster depends on the rig.** §4 itself says fragment count differs by rig: 0.2 m
  chunks on laptop, 5 cm on max. One entity per cluster would give an NPC 3 things on a laptop and 40 on max, with
  rig-dependent names. NAc and the vocabulary key on names exactly (N7), so what an NPC learns would depend on the
  rig. That is the resolution rule broken at the percept level.
- **The structure entity's sensors don't separate attached from loose matter.** `region_id` keeps a loose cell
  owned by its region, so a crate shattered to rubble could still read as solid. N1 never says which.
- **"Where grounded concepts come from"** is a claim about Maxim's grounding line with no citation. In Maxim,
  grounding comes through perception, and carry, throw and climb need a body that can move objects (Phase 5 or
  later).

**Fix:**
- Rubble reaches Maxim first as rig-independent fractions on its parent structure (`intact_fraction`,
  `loose_fraction`) and on the zone (`rubble_volume_m3`).
- A `matter` entity exists only for a pile above a minimum volume, with its identity defined in metres (for
  example, loose volume merged within a stated radius). Its ids stay stable across settling, and a cross-tier test
  checks that the number of entities agrees across rigs.
- Remove the "grounded concepts" sentence, or cite it.

### BF-9. The cryo store's "trust the instrument" isn't learnable first-person with Maxim's machinery, and its cues don't sit where the danger is

**Location:** §9, row "Cryo store".

- **The receptor test is passed honestly:** no body cue, correctly.
- **No teaching signal reaches Wire-4.** It learns only from pain on `drive:health` or `drive:oxygen`
  (`nac.py::DEFAULT_CLUSTER_FEAR_FAILURE_MODES`).
  - Under silent hypoxia the `oxygen` drive must *not* hurt (`maxim_senses.md`: an O₂ pain is the caricature).
  - The harm is unconsciousness, then death. Unconsciousness doesn't exist as a body state yet (P-F, Phase 4).
  - An unconscious NPC doesn't experience the cluster-to-pain pairing at all.
  - So the first-person lesson is near-zero by physiology. That is faithful, and the table should say it: the real
    routes are social learning (Phase 5, `gameplay.md` Exp 6) and being told.
- **Fog marks the cold gas near the spill, not where O₂ is low.** Cold N₂ is dense and pools at the floor, which is
  the real trap: bending down to help a collapsed colleague. A well-mixed zone can't represent that.
- **The instrument has to be perceivable.** An O₂ meter is an instrument entity (BF-2's N9), and its alarm needs
  sound (Phase 2) or line of sight to its display (P-E).

**Fix:** change the "learn" cell to "silent; learned only socially or by instruction (Phase 5)". Record floor
pooling of dense gas as a known gap, joining the two-layer zone. Make the O₂ meter an instrument entity with an
alarm.

### BF-10. The sealed chamber's relief action "open the door" is the backdraft, and its occupants don't live to learn "fires starve"

**Location:** §9, row "Sealed test chamber".

- **Opening the door is the hazard.** A starved, hot, fuel-vapour-laden room is exactly where opening a door causes
  a backdraft or flashover. `gameplay.md`'s table says so ("a burning room whose door is opened can flash over").
  v2's zone model, with fuel vapour as a species and vent inflow, will produce it. That is faithful physics, but
  then "open the door" is a harm, not a relief, and an NPC learns "that door hurts".
- **The occupant is incapacitated.** By the design's own numbers (about 4 kg of O₂ in 18 m³, extinction ramping from
  15% down to 10% O₂), extinction leaves the room at roughly 6–9% CO₂, plus CO and a hot ceiling. That incapacitates
  in minutes. "Fires starve when sealed" is a lesson for an observer outside, which needs line of sight, not for the
  occupant.

**Fix:** the occupant's relief is "leave". Show "opening the door later" as its own outcome (a hazard to someone
outside). Move the "learn" cell to an observer, conditional on P-E.

### BF-11. §10's heat debt: right in outline, wrong that "cooling works by changing phase", and silent on what the NPC needs to feel it

**Location:** §10; `gameplay.md` §1 row "Cyberware that overheats" and §2.

- **Faithful:** heat storage as a debt is the body's real heat balance (S = M − W − E − C − R − K). Where you are
  setting how long you can push is true, and a burning bay shortening it is true.
- **Wrong:** "cooling works by changing phase".
  - Plunging into water is conduction and convection; water carries heat about 25 times faster than air
    (`maxim_senses.md` §2, "Cold and wet"). It isn't a phase change.
  - At rest, radiation and convection carry most body heat. Evaporation dominates only during exertion, or once the
    surroundings are hotter than the skin.
- **Humidity.** Humid air throttles sweat evaporation: the wet-bulb limit. "In the rain, longer" is true only when
  conduction to cold rain beats the humidity penalty. §3.1's evaporation law (ρ_sat(T_s) − ρ_zone) already gives
  this. Let it be emergent, never an authored constant.
- **Feeling it.** An NPC needs a two-sided need, because no corrective need fires above the set point
  (`autonomic_layer.md` R-2, GL2b). And for `implant_temp` to be feared, its harm must reach `health`, or P-B must
  extend the allowlist. Neither is named as a dependency of §10.
- **The coolant implant is fiction, a designed sensor.** That is justified by the ripperdoc premise, and should be
  kept off cradled bodies that have no implants (`gameplay.md`).
- **The roadmap.** Phase 5 defines Overdrive as "forcing an action through a part below its integrity limit, paid
  for in pain". v2's Supersedes doesn't touch it.

**Fix:**
- Reword to "cooling runs through the body's heat balance: convection, radiation, conduction and evaporation".
- List R-2, GL2b and P-B as §10's Maxim dependencies.
- Tag the implant sensor as designed, not innate.
- Add roadmap Phase 5's Overdrive line to Supersedes.

### BF-12. N3's cause verbs have no effector, and N5's requires refusal books the same state-blind NEGATIVE that BF-1 avoids

**Location:** §7 N3 ("heat, cool, pour, ignite, vent, douse"), N5.

- **Free verbs on every entity are magic.** `heat(power_w)` on a crate lets an NPC heat it with no flame, no tool
  and no cost.
  - Real bodies act through effectors and tools: a torch, an extinguisher, a valve.
  - Maxim's own imagination model puts verbs on the body ("the agent interacts with scene entities using its own
    body's tools", `imagination/trigger.py`).
  - Fix: cause verbs live on tool and fixture entities that exist in the scene (the torch's `apply_flame`, the
    valve's `open`). Their power comes from the tool's data, and the costs to the body join Phase 5 as `self_effect`.
- **N5 is the right gate, but say what it teaches.** A world-backed `requires` refusal goes down the
  `affordance_blocked` path (`tool_bridge.py`) and books a NEGATIVE on the state-blind tool link. `extinguish` with
  no fire teaches "extinguish is bad" everywhere. That is Maxim's intended chain ("can't fly with a broken wing"),
  and state-blind is Maxim's limitation, not the game's. Name it as **OPEN**, and raise it in P2's discussion:
  should a requires block book to the situation cluster rather than the tool?

### BF-13. Delta 1 findings v2 drops or only half folds

**Location:** `world_v2.md` §1 says the delta 1 files are "folded here for the first time".

| Delta 1 | Status in v2 |
|---|---|
| D1 (world-time latency mode) | **Folded,** except: the typed `thought_failed` (BF-5.3); `d` read from `data/` and hashed into world config; the draft's wording |
| D2 (stale refusal) | **Half:** the rule is stated, but on a false premise (BF-1). The Phase 3 item and the interim rule are missing. |
| D3 to D6 (draft claim, H3 trigger, H1 arms, H4 measures) | **Dropped;** the draft is unchanged (BF-4) |
| D7 (an OPEN tag for live thinking speed that depends on the dial and hardware; what the presets do to NPC deliberation) | **Half:** the `d_min` floor is folded. The tag and the presets statement are missing. |
| D8 (pushback names its decision) | **Half:** a column was added, but it is empty for P4, P6 and P7, and v1 items 13, 14 and 17 are gone (BF-7) |
| D9 (NPC sleep as a world behaviour; consolidation off the simulation lane) | **Dropped.** "Sleep" appears only as a preset (decision 8). |
| D10 (divergence tags; drive rates calibrated in world-day terms; a test that the percept builder reads only `World`; food and rest affordances in roadmap Phase 4) | **Dropped.** The only tag is §6's ANALOG. §5's "simulation can't read server config" test is a different guard. §9's day-long study has arrival and sessions but no food or rest affordance, and participants can't spend a day there without them (Bio-11). |
| D11 (`ReflexRegistry` and the staleness clocks) | **Dropped** (BF-7) |
| D12 (`salience/movement_detector.py` normalised per second) | **Dropped** |
| D13 to D15 (draft NITs) | **Dropped** (the draft is unchanged) |

**Fix:** fold each item, or answer it in writing with a reason, as the charter requires.

---

## NIT

- **NIT-1.** §1 and §6 call a stale refusal "a percept". The percept is the world state the NPC perceives at
  T + d (the door is open). "The plan was overtaken" is carryover context. Say "context for the next thought", which
  is also what `book_machine_refusal` books.
- **NIT-2.** `temperature_max` over a region's cells (`sem_env/bridge.py`) is an interior maximum, and the max of
  smaller cells is higher, so the reading grows with resolution. It breaks "every consumer reads a reduction at its
  own scale". Replace it with a surface temperature over an area in metres, classed `percept` (by touch) or
  `instrument` (BF-2).
- **NIT-3.** N6's root-level skin temperature, standing in for P4's per-part sensors, should carry the
  `TEMPORARY(phase3)` marker that `sem.md` N6 asked for. v2 drops the marker.
- **NIT-4.** The coolant room's "What an NPC can learn: where Overdrive's heat debt goes" is the designer's lesson.
  An NPC learns "the hiss predicts a scald" (`gameplay.md` Exp 3).
- **NIT-5.** The wet lab's relief "avoid the room" is future avoidance, not relief at the time of harm. The acting
  relief is to leave or ventilate. Conditioned aversion from malaise binds to taste and odour far more than to
  place (the Garcia effect), so the faithful lesson keys on the smell, with the H₂S trap as a deliberate exception.
  Tag P-D's credit window **OPEN**.

---

## What I checked and found faithful

- **The division of labour** (§7 preamble, decision 13). SEM's drift is linear and on the wall clock, its couplings
  are parsed but never read (`autonomic_layer.md` R-4), and scene entities are never ticked: all verified as stated
  in `sem.md`. Keeping physics out of SEM is right, and so is "deliberately not proposed" (categorical sensors,
  repurposing the couplings, a phase-diagram type).
- **N2's fractions.** They match what Maxim's learning paths read (numeric `reading_schema` only), and they converge
  across rigs.
- **N3's "causes, never outcomes"**, and no `target_effect` on world entities. This matches Maxim's
  phantom-credit principle (`sem_motor_binding.md` decision 3). BF-12 is about the effector, not the rule.
- **N6's `world_set_axis(owner=…)` path** is the earned Minecraft pattern (oxygen, health). N7's versioned
  vocabulary is right: NAc keys on tool names exactly.
- **P3's diagnosis** is verified in `tool_bridge.py` (BF-6 is about framing and routing).
- **P1, P2 and P6** are well argued in `sem.md`. P2 keeps #1315's rule that only the executor makes gate kinds,
  which `executor.py::_retag_body_gate_kind` enforces.
- **Decision 11** (waiting defined in world time) and §6's live `max(T + d_min, arrival)` floor. Slow motion can't
  give an NPC thinking faster than a mind could.
- **The latency mode's purpose.** It removes the host-speed-driven abandonment that delta 1 D1 measured. Its ANALOG
  tag is honest.
- **One world clock for sensors** (§5, DX7), and region reductions cached per physics step.
- **The immersion and drowning path** (lower level): Exp 60's earned design, faithful.
- **"Every hazard gets an authored escape", and invisible hazards only through instruments:** right as principles.
  BF-2, BF-3, BF-9 and BF-10 are about whether the rooms meet them.
- **Bound water leaving as steam** as the first latent transition, and fines going to the zone's
  soot-and-fines species: physically sound and cheap.
- **Study participants as the reason for instruments and a daily rhythm.** This gives the SCN a real zeitgeber
  structure. It needs D10's food and rest affordances to be a day an NPC can live.
