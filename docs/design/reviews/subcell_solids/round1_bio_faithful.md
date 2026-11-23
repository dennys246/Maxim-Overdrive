# Sub-cell solids design, round 1: Bio-faithful integration (2026-11-22)

The reader's report as handed back, saved by the author. Statuses are unset: a reviewer sets them after the fold.

**Read:** `subcell_solids.md` at `1c701aa`, and against it `sem_stimuli.md` v5, `fire_solid.md` §2 and §7,
`boundaries.md` §4.3–§4.4, `docs/plans/checklists.md` (the contact and pain-path items),
`src/simcore/adapters/sem/bridge.py`, `reviews/fire_solid/bio_faithful.md` (B1), and from `phase6/specgen-spike`
the survey (§5, item 8) and D31–D35. **Maxim:** `origin/main` at `b98954f7` (2026-11-22 10:29, release 1.3.4). It is
current, so nothing is left unverified for staleness.

**Verdict.** §9's principles are right. NPC sensors reduce over metric volumes, no sensor names a cell or an object,
mass never reaches an NPC as a number, and no Entity field is added. But other sections reopen paths §9 says stay
shut. §7.1 and §7.3 extend the omniscient region instruments and the affordance targets to objects, which is the
fire_solid Bio B1 finding again. New target-dependent refusals bypass D15's receipt rule. And the senses §9 assigns
to an owner (weight, contact force) have no owner. One BLOCKER, four SHOULD-FIX, three NITs. Nothing in the design
needs a Maxim change now, and I found nothing that contradicts a Maxim plan or decision.

---

## BLOCKER

### B1. §7.1 and §7.3 widen `QUANTITIES` and the structure modulator to objects, which reopens fire_solid Bio B1 and contradicts §9's own bridge bullet

**Location:** `subcell_solids.md::§7.3` (`QUANTITIES` "defined on a region's matter, both cells and objects"),
`::§7.1` ("`fuel_only_region` is never built. Every act above is defined on every role"), `::§9` (fourth bullet: "The
bridge's surface … changes only through the NPC fire note's ruling … This design adds no affordance"), `::§12` (the
`fire_solid.md` §2 row), `::§14` item 1. Against: `fire_solid.md::§2` ("An object quantity, when needed, gets a new
name (F1) as a lab instrument under `tests/`, never in `QUANTITIES` or on an NPC builder (`boundaries.md` §4.4)"),
`fire_solid.md::§7` ("6.0–6.1 doesn't block on [the NPC fire note] because the bridge, `QUANTITIES` and the
affordances stay untouched"), `reviews/fire_solid/bio_faithful.md` B1, and
`src/simcore/adapters/sem/bridge.py::region_parts` and `::to_maxim_entity`.

**What the tree does today:** `region_parts` builds a `RegionInstrument` for every `QUANTITIES` entry on every
region. `to_maxim_entity` (in `src/`) puts those instruments on a real Maxim `Entity`, and Maxim's generated
read-all-sensors tool hands them to any agent that holds it. `sem_stimuli.md` §6.1's D10 split moves the
instruments to a lab builder, but only in `phase1/agents`. Today only convention separates lab from NPC (delta1 NS3,
still open). fire_solid kept 6.0–6.1 independent of the NPC fire note by keeping `QUANTITIES` and the affordances on
cells. This design removes that premise in two ways:
- It withdraws `fuel_only_region`, so `region_parts` now builds instruments and a `structure` modulator for
  object-only regions.
- It redefines `integrity`, `temperature_max` (now over every object *node*, interior ones included) and `breached`
  over objects, keeping the same names.

§9 says the bridge's surface doesn't change. Through `region_parts`, it does. §14 item 1 frames the change only as an
F1 naming question. That is the smaller of its two problems.

**Failure scenario:** S3 lands before `phase1/agents` (§13 orders S3 only "after 6.0b", not after D10). A harness
hands `to_maxim_entity("aquarium")` to a Maxim agent. Through the generated read tool, the agent sees `breached`
flip when the 6 mm pane cracks, and `temperature_max` rise from the steel stand's interior node, before any
receptor at its position could register either. No sound, vision or contact row exists yet. Fear and credit then
condition on an oracle, and the LLM prior hides the leak (`fire_model.md` §7). Separately, replays and goldens taken
on either side of S3 report `integrity` under one name with two meanings, which F1 forbids.

**Fix (unverified).** Pick one of these:
- (a) Keep `QUANTITIES` on cells, pinned. Give object readings new names on a lab surface (a lab builder or
  `tests/`), never in `QUANTITIES`, as `fire_solid.md` §2 requires.
- (b) Make S3 depend on D10's lab-builder split having landed, with a test that no builder an NPC can reach holds a
  `RegionInstrument`. Also move the NPC fire note's trigger ahead of S3, since fire_solid §7's reason for not
  blocking on that note no longer holds.

Under either option, rewrite §9's fourth bullet so it is true, and restate §14 item 1 with the leak named as well as
F1. If the specgen stage-2 scoring needs `breached` or `integrity` for objects, that is a lab consumer and belongs on
the lab surface.

---

## SHOULD-FIX

### S1. The new refusal codes that depend on the target aren't routed through D15's receipts or T11's sweep

**Location:** `subcell_solids.md::§11.3`, `::§7.1` (`ignite` "refused otherwise … under a new code
`not_flammable`"; `not_on_object`), `::§8.4` (`unsupported`), `::§4.1` and §4.2 (`overlaps_object`). Against:
`sem_stimuli.md::§6.2` (v1 receipt kinds are target-independent; every stage-2 result is `accepted`; T11 sweeps
"every target-dependent refusal the applier returns (existence, air, gone, footprint, burning state)") and `::§6.3`
T5. Also `boundaries.md` §6's table: an `imagine` comes from "LLM via Maxim", from any actor, so NPCs issue them.

Four of the new codes are decided by world state the NPC may not perceive:
- `not_flammable` depends on the target's material, which is a combustion fact;
- `not_on_object` depends on its footprint;
- `overlaps_object` depends on whether something exists, possibly out of sight;
- `unsupported` depends on the support graph, which includes hidden members.

T11's sweep has no category for material or support. Today's bridge returns `outcome.agent_text` synchronously
(`StructureModulator._from`).

**Failure scenario 1 (ignite):** An NPC calls `ignite` on a steel locker, gets `not_flammable`, and has learned that
steel doesn't burn without any thermal event. T5 forbids exactly this: a material that differs only in a combustion
constant must give identical streams.

**Failure scenario 2 (imagine):** An NPC imagines a box into a dark cupboard and gets `overlaps_object`, which tells
it something is in there. If it gets `unsupported` instead, it learns the shelf under the spot has lost its bearing
path.

**Fix (unverified).** In §11.3, split the codes into two groups:
- Stage-1, spec-only codes may surface as `malformed`: `part_too_thin`, `parts_overlap`, `unknown_role`,
  `bad_version`.
- Stage-2, target-dependent codes map to `accepted`: the four above.

Then add material and support to T11's sweep categories, and make the steps that first produce the stage-2 codes
(S1 for `overlaps_object`, S3 and S4 for the rest) wait for `phase1/agents`' `pending` result, or state what holds
the leak until then.

### S2. §9 cites an owner for weight and contact force that doesn't define them

**Location:** `subcell_solids.md::§9` (third bullet: "owned by `sem_stimuli.md` §3's body: a contact force at its
receptors when it pushes or lifts"). Against: `sem_stimuli.md::§2.2` (the v1 rows are only `tissue_temperature` and
`core_temperature`; "contact and vibration, joints and vestibular (ANALOG)" are later rows that "freeze with their
field's design") and `::§3` (no force, pressure or weight anywhere; grep confirms). `subcell_solids.md::§7.1` and
`npcs_and_sem.md` have no push or lift act. On Maxim's side, `sem_stimuli.md::§9` M11 (touch: a Question to GL3).

**The gap:** the survey's item 8 ("what an NPC senses of weight, contact and motion") is answered by pointing at a
section that defers it, with no trigger. So weight, contact force and motion have no owner and no trigger.

**Failure scenario:** S4 registers `load` and a contact force as fields (§9, second bullet). Phase 4 wants NPCs to
feel a table give way. With no row design and no trigger, the path of least resistance is to mark the member-load
field perceivable and bind it. That hands the NPC the solver's member load, not a force at its skin.

**Fix (unverified).** State three things in §9:
- Contact force and weight are a future `sem_stimuli.md` row, at receptor sites, frozen with the body-support or
  D32 design.
- That row's trigger is the first act or state that puts a body's weight on an object, or lets it push or lift one.
- Until then NPCs sense none of weight, contact force or motion, recorded as a named perception gap.

Cite the Maxim side as M11 and the GL3 track below.

### S3. Verdicts and table-derived values are left as candidates to be marked perceivable, and `support_lost` goes to an undefined "tick report"

**Location:** `subcell_solids.md::§9` (second bullet: "a load, a contact force, a support state … perceivable only
when … marks them, which is false by default") and `::§8.3` ("an event `support_lost` in the tick report"). Against:
`sem_stimuli.md::§2.1` (a row's `name` is "a physical quantity, never a verdict") and `::§7.4` ("material ids and
table constants never are" perceivable).

**The problem:** `support` is a graph verdict ("anchored", "bearing", "loose"). Capacity, `role` and `material_id`
come from table constants. `integrity` is a law's summary. "False by default" leaves each of them one reviewed data
change away from an NPC. "Tick report" appears in no other design (grep), so where `support_lost` goes has no owner.

**Failure scenario:** a later branch marks `support` perceivable "for the fall cue", with a planted test. A row model
reads it, and an NPC knows a table is loose before anything moves. Or `support_lost` is put on `BodyFrame.events`,
or into text an LLM sees, and becomes a fall oracle that T7's denylist doesn't name.

**Fix (unverified).** Name `support`, `role`, `material_id`, capacity, `integrity`, `members` and the load solve's
outputs as never perceivable, in the same class as material ids. Only a force or a temperature at a receptor's site
may be. Then say `support_lost` is a log and lab record, never a `StimulusEvent` or text an NPC can see.

### S4. The coupling between NPC bodies and objects isn't bound, and the 0.4 m threshold changes what an NPC can feel

**Location:** `subcell_solids.md::§5.1` (couples object to cell and object to object only), `::§3.3` (the profile
chosen by a convective `h_ref`), `::§2.2` (the cross-threshold test under "one fire and one load"). Against:
`sem_stimuli.md::§7.1` (`contact.py` writes "the object through an exchange field … against its own carried
sub-mesh"), `::§2.3` ("Cell faces exchange nothing with bodies in v1"; strict red gates), `::§4.6` and the checklist
(the pain-path test, "fingertip contact on 70 °C steel"; the sub-mesh "read by the solid law through a conservative
remap").

**Why it matters:** under `fire_solid.md` §1.3, steel is cells, and bodies can't touch cell faces in v1. So this
design is what makes Phase 4's pain-path fixture representable from a shipped scene. That is real value, but the
design never says that body contact and irradiance apply to `structure` and `inert` objects. It doesn't say what
`contact.py` reads (which nodes and faces) or how its remap lands in a lumped or 1-D profile. That profile was chosen
for convection, but contact conductance moves steel's time to pain 4.5× (checklist). Nor does it say whether object
faces write `radiant_emitters`.

**Failure scenario 1 (contact):** S2 ships box objects with lumped profiles, and `contact.py` is written against
fuel `slab` and `rod` kinds. At release, the fingertip's sub-mesh is either unsupported on a `box` or remapped into
the one node. The pain-path gate then can't be built on structural steel, or the result depends on a profile
decision made for a different h.

**Failure scenario 2 (threshold):** §2.2's 0.38/0.40/0.42 m test passes on fire and load. Yet a hand on a hot 0.39 m
concrete block hurts (object contact), while the same hand on a 0.40 m block feels nothing (cell face, red in v1).
What an NPC learns, "hot concrete burns", changes outcome class at an authoring threshold.

**Fix (unverified):**
- Add body to object as a §5.1 coupling, with `sem_stimuli.md` §7.1 as its owner. State the interface: the node and
  face fields it reads, the exchange field it writes, and that §3.3's profile choice never sets the skin's contact
  temperature.
- Say whether object faces are emitters.
- Add a contact case to §2.2's threshold test, with its cell side under sem_stimuli's strict face-contact gate.

---

## NIT

- **N1. `subcell_solids.md::§5.2`.** The Phase 1 ambient rule means a steel door in a burning room stays cool to the
  touch. That is a false regularity an NPC would learn. Phase 2 precedes Phase 4 in `docs/roadmap.md`, but the Known
  gap should say it must close (S5) before any NPC contact row reads an object, or carry a gate that says so.
- **N2. `subcell_solids.md::§8.3`, `::§8.4`.** While objects can't fall, the red gate also stands for a learnable
  falsehood ("charred legs hold"). The Known gap should say that NPC perception and learning of structural failure
  wait on D32. D33's `unsupported` refusal is a world rule, not physics (a real loose part falls), so tag it
  **ANALOG** with D32 as the step that earns it.
- **N3. For when the contact row lands, not now.** Maxim's GL3 maps SEM `self_effect` deltas on touch sensors to
  `mechano_proprio`. Once the world simulates contact force, `boundaries.md` §4.3 makes those sensors world-owned, so
  a YAML touch delta would double-count. Raise it then as a question to GL3 (`thalamic_relay.md` §5.4), not as a new
  item.

---

## Maxim: what origin/main has (`b98954f7`)

- **A touch and proprioception channel exists as a plan:** `docs/plans/grounding.md` (the GL3 track table, line 253)
  defines `mechano_proprio` ("touch, proprioception (not temperature, not pain)"). Its Minecraft membership is mapped
  in `docs/plans/thalamic_relay.md` §5.4, enforced by GL3.B3's track-membership test. A future contact-force row binds
  there, through Overdrive's existing M11, a Question to GL3. That needs no new item and no Maxim change from this
  design.
- **Declared weight or fragility on items:** searched for `mass`, `weight`, `heavy`, `heft`, `load_cell`,
  `contact_force`, `mechanorecep`, `fragile`, `breakab` and `shatter` in `src/maxim/_data/components/items/`,
  `src/maxim/embodiment/sem.py` and the live `docs/plans/` and `DECISIONS.md`. Nothing found that declares an object's
  weight or breakability to an agent. So there is no M14-style declared property (like `heat_output`) for this design
  to push back on. The only nearby hits are unrelated (`sanity_break`, a lockpick's "may break picks" text).
- **Frozen types:** the design adds no field to `SensorReading`, `ModulatorResult`, `AffordanceSchema` or `Entity`,
  and leaves `_compat.py` alone. That holds.
- **Contradictions:** none found with a Maxim plan or decision. The pushback this design's evidence would support
  (that world-produced breakage and fall cues should reach Maxim as sound, vision and contact, not as state) is
  already Overdrive's position in M11 and M14. It needs no new draft.
