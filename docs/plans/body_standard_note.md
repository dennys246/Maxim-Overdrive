# The body standard: an input for the next planning session

**What this is.** This is an input for the planning session the owner starts when step 5 of the next steps merges
(`docs/roadmap.md`, "The next steps after `v0.1.0`"). It proposes; the owner's rulings on its questions are §5. It is not a design either:
step 5b owns the body's contract (`docs/plans/checklists.md`, "Step 5b, bodies and movement"), and anything this note
recommends reaches that contract only through step 5b's design review. It was written on 2026-11-27, at the owner's
ask.

**The owner's idea (2026-11-27, paraphrased).** Make an articulated stick figure, with joints and limbs, the
standard first NPC body: the base other bodies extend from, and the way to show how Maxim is embodied as a
character. Small variations would follow, such as colour changes and basic scars. A moving capsule doesn't convince
players they're in a world, and even a roughly human shape would do better. Joints might be the hard part.

**How this was checked.** Four independent readers each took one question:
- what Overdrive already plans for bodies;
- what Maxim provides for embodiment;
- the engineering cost in the server and the Godot client;
- the strongest case against.

The author then checked each citation below at the ref named, and the reports themselves are not kept. The refs
are:
- Overdrive `origin/main` at `e6d6a7f`, and `phase1/slice2-design` at `7f21055`;
- Maxim's `origin/main` at `b90800e`, fetched on 2026-11-27.

## 1. What exists today

**Nothing about bodies has shipped.**
- `src/` has no body module; bodies arrive with step 5b. The roadmap's next-steps table lists 5b as "open, not
  started", with planning assigning it after 5a PR 4b merges.
- The shipped client draws no actors: `client/game/main.tscn` holds one `Main` node.
- The "blob" is a Godot `CapsuleMesh` in two places: the slice spike (`spikes/slice/godot/scripts/main.gd`) and the
  rendered checks' stage (`client/tests/support/render_stage.gd`).

**The body is designed, though, and the design already answers much of the idea.**
- **One body model, owned by the world.** The design gives the body a collision cylinder, and says "Overdrive never
  models a body twice" (`docs/design/tile_and_client.md` §2.1). Body occupancy comes from the bodies part of the
  `Frame` and is never stored in cells (§2.1). So limbs are not cells, and the thin-feature rule
  (`docs/design/world_model.md` §1.1) binds them only where they meet the grid.
- **The actor table has no pose or joint columns** (§2.2).
- **The client may animate already.** It may "interpolate poses; animate from `facing` and motion", and may not
  "move the drawn body by its own collision" (`docs/design/client_rendering.md` §3.1).
- **What the body feels is designed as fixed points.** The skin's site set is 17 regions with fixed points in
  body-local metres, beside `joints` and `head` site sets (`docs/design/sem_stimuli.md` §3.1).
  - The research already describes the body as "capsules in metres with quadrature points fixed on them"
    (`docs/design/research/sem_stimuli/3_world_side.md`, item 2).
  - Joint and vestibular rows are later, ANALOG rows (`sem_stimuli.md` §2.2).
- **Posture, gaze and breath are already planned as intent kinds** (`sem_stimuli.md` §4.5, and step 5b's checklist).
- **Appearance already has an owner.** The person re-identification draft commits that each body has "physical,
  perceivable features (height, build, clothing colour, voice pitch, gait)" (`docs/maxim_upstream/person_reid_DRAFT.md`
  §4, on `phase1/slice2-design`). Scars are not among them.
- **Searched on every branch, nothing found:** stick figure, skeleton, ragdoll, limb, articulated, a rig, an
  animation plan for NPCs. The idea fills a real gap.

**What Maxim gives a body (at `b90800e`).**
- **An agent acts by choosing a named affordance.**
  - `tool_bridge.py` turns each affordance into a tool, `src/maxim/decisions/nac.py::recommend_action` chooses among
    discrete names, and the Minecraft body records that "substrate-primary recommend_action emits empty params"
    (`src/maxim/_data/components/bodies/minecraft_player.yaml`).
  - The Cerebellum keeps a forward model per affordance and parameter bucket, not per trajectory
    (`src/maxim/embodiment/cerebellum.py`).
- **Maxim's shipped humanoid is a part tree with no joints.** `base_humanoid.yaml` has head, torso, arms and legs,
  with part sensors such as `arm_mobility` and `leg_mobility`, and damage affinities that map onto parts.
- **Joint control lives below Maxim on every body it drives.**
  - On Reachy, the robot's daemon does the inverse kinematics; Maxim sends one clamped target
    (`src/maxim/hardware/reachy/motor_backend.py`).
  - In Minecraft, a pathfinding library walks; Maxim says `move_to`.
- **Maxim's own plan for a legged robot draws the line plainly.** That plan is `docs/plans/microduck_intent_layer.md`,
  a rev 2 draft, deferred until a second robot body exists. It says:
  - "Arbitration granularity is the policy, not the joint."
  - "Nothing in the substrate goes inside the control loop."
  - "48 raw dims is the dilution failure at 48×": design "a reduced proprioceptive summary (gait phase, CoM offset,
    per-limb load bands)", not raw joints.
- **Searched in `src/`, nothing found:** body schema, efference copy, central pattern generator.

## 2. Recommendation

**R1. The base is the part-level body, and a skeleton is one way to draw it.**
- The standard worth fixing is what Maxim senses and acts through:
  - the parts and the site sets on them (`sem_stimuli.md` §3.1);
  - the affordances (`walk_to`, `reach`, `look_at`, `flee`, `block`);
  - a few summary sensors per part with declared ranges.
- This lines up with Maxim's `base_humanoid.yaml` part tree, so damage, pain, `requires` gates and forward models
  attach to limbs as they already do.
- A stick figure, a skinned mesh, cyberware or a non-human body are then views of the same spec. That is also what
  Phase 5 promises: the player's body is an SEM entity "with the same body grammar as the NPCs" (`docs/roadmap.md`,
  Phase 5).
- A bone hierarchy as the base would lock in the view and leave the grammar implicit.

**R2. Joints live in a controller beneath the agent, never in Maxim.**
- The agent picks an affordance. A game-side controller turns it into motion, playing the spinal and brainstem
  role that Reachy's daemon and Minecraft's pathfinder play.
- The body reports summaries back, not joint vectors.
- Asking the language model or the action selector for joint angles would be a caricature: neither can carry a
  trajectory, and Maxim's own plan names raw joints as the dilution failure.
- **Said plainly:** a jointed body adds nothing to Maxim's mechanisms beyond the part-level body. Its value is
  legibility and presence, which is real, but a showcase should not claim the skeleton is deeper embodiment.

**R3. The server owns a pose only where the world reads it.**
- **Where the world reads it:** fire exposure and pain are evaluated at the body's fixed points (`sem_stimuli.md`
  §2.3, §3.2), and reach is measured from the body (`tile_and_client.md` §2.1).
  - So a limb the client swings toward a fire is not the limb the server burns.
  - The engineering reader estimated a walk cycle swinging a hand 0.3 m toward a fire 1 m away at about twice the
    point-source flux at peak. That is an unmeasured estimate from 1/r².
- **The proposal for step 5b's design:**
  - The server carries a small posture vocabulary (stand, walk, crouch, reach, fallen, the set to be decided). Each
    posture has its own site positions in body-local metres, with a cross-tier test per posture.
  - The gait cycle stays visual.
  - The difference between the drawn and the felt limb is recorded as a Known gap with its measured number, in the
    commit that draws the gait.
- **No ragdoll:** Godot's physics is not deterministic across machines, and where a fallen body lies feeds its
  exposure. "Fallen" is a server posture.

**R4. Gaze comes first.**
- Players read life from intention more than from limb count: a head turning toward a noise, a pause, then the act.
- Gaze is already a planned intent (§4.5). Drawn from the server's gaze target, it shows real agent state.
- Once Maxim's attention is read out (`docs/design/npc_inspector.md` on `phase3/npc-inspector`, unmerged), it would
  show Maxim's own state, not the behaviour tree's.
- This is the single cheapest change that makes an NPC read as alive.

**R5. Appearance is world state NPCs can perceive, never client decoration.**
- If colour or build exist only in the client, players see differences NPCs can't sense. So appearance is
  body-instance data the server owns, and the client draws what it is sent.
- **Colour:** colour as identity is fine, but colour as state also changes shape or shading (CLAUDE.md, client
  standards).
- **Scars come only from damage the body took,** in play or in the past its cradle generates (`docs/roadmap.md`,
  Phase 4). Decorative scars contradict "a life it actually lived".
- **Skin tone** is drawn per NPC from the setting's population (BS5).

**R6. Timing: not in slice 1.**
- The slice 1 vendor is the comparison baseline. "The vendor felt alive enough" is the verdict the NPC line has to
  beat (`docs/plans/vertical_slice.md` §3.5). Changing its body before the 2026-12-18 verdict confounds the
  playtests.
- Slice 2's AI is not humanoid: it acts through a rack, a fan, a sprinkler, a door and a camera
  (`docs/plans/slice2.md` §3.5, on `phase1/slice2-design`).
- **The natural homes:**
  - the body grammar, postures and gaze in step 5b's design, with Bio-faithful integration among its lenses;
  - the drawn figure in step 8's client, which replaces the `Actor_<id>` capsules (`client_rendering.md`, the scene
    tree).
- **The client half is small, per the engineering reader's estimate (unmeasured):**
  - drawn as one `MultiMeshInstance3D` of about 11 capsules per NPC;
  - a stride locked to distance travelled, so feet don't slide;
  - an idle breath and a lean that follows acceleration;
  - a few hundred lines of typed GDScript, plus a golden with the gait phase frozen.
- **The wire needs no pose.** It needs a posture byte per tick and an appearance id sent once.

## 3. Unchecked, to measure at the build step

- Whether Godot 4.7.2's Compatibility renderer supports `Decal`, and which IK modifiers 4.7.2 has. Each needs a
  probe under `tools/godot_probes/` (B26) before a design relies on it.
- The byte and draw-call figures in R6, measured against B5's budgets.
- The flux-error estimate in R3, measured on a plant.
- Stiffness: procedural cycles read as robotic without secondary motion. A stylised figure avoids the uncanny
  valley, and a half-realistic one falls into it. Only a playtest settles this.

## 4. What it may need from Maxim

None of this is needed for R1 to R6. Each item is a candidate Phase 3 row, after step 4, under the search rule.
- **A proprioceptive channel.** The substrate has interoception, audio and world, and none is proprioceptive.
  Maxim's own plan scopes adding one as a selection-dynamics re-baseline (`microduck_intent_layer.md`; roadmap row
  1.1.4 there).
- **A body schema and an efference copy:** searched in `src/`, nothing found.
- **Parameters on substrate-chosen actions,** which are empty today.
- **Per-part sensors,** already OD-C10.

## 5. The owner's rulings (2026-11-27)

The owner answered each question through a multiple-choice prompt. These rulings are inputs to the planning session
and step 5b's design, and each is filed as an `O` decision after step 4 merges, while the decision files are frozen.

| # | Question | Ruling |
|---|---|---|
| BS1 | What the base is | The part-level body spec, with the skeleton as one view of it (R1) |
| BS2 | Timing | Step 5b's design and step 8's client; slice 1's vendor is left as it is (R6) |
| BS3 | Appearance | World state that NPCs can perceive, owned by the server (R5) |
| BS4 | Scars | Only from damage the body lived through, in play or in its cradle's past (R5) |
| BS5 | Skin tone | A body-instance feature, drawn per NPC from a distribution that fits Maxim Prime's population, set by the owner or the writers |
| BS6 | Gaze | First among the drawn behaviours (R4) |
