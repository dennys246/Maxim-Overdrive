# Lessons: applying Maxim to games

What building Maxim Overdrive teaches about putting Maxim agents into a simulated world. Each lesson is written when
it is learned (CLAUDE.md, "Record lessons as they're learned"), with its evidence and what it means for Maxim and for
anyone building a game with Maxim. This file is the seed of an engine's documentation and the evidence base for
pushbacks to Maxim (roadmap Phase 3).

Format: **the lesson**, then *Evidence* (where it was found, with numbers) and *Consequence* (for the world, for
Maxim, or both), and the Phase 3 item or design section that acts on it.

## World and physics

### 1. One simulation truth beats resolution tiers (2026-11-16)

**Letting different machines simulate the world at different resolutions makes them play different games.**
*Evidence:* PR 1's eight review rounds kept finding outcomes that depended on the cell size: a fire's crate integrity
0.70 / 0.57 / 0.51 at turn 22 across 0.2 / 0.1 / 0.05 m; a strike accepted at one rig and refused at another; a
breach flipping. *Consequence:* simulate one truth resolution everywhere and scale only rendering
(`docs/design/world_model.md`, D20). A machine's time budget may only sleep provably quiet regions or slow time; it
may never change what is simulated (D21).

### 2. Never threshold a cell's mean: reconstruct, decide at the point, integrate (2026-11-16)

**Averaging then applying a threshold is not applying a threshold then averaging, and the error grows with the
cell size.** *Evidence:* burning as a threshold on cell-mean temperature converged slowly and left the coarse grid far
off (the degradation driver 1.3–1.5× larger at one grid than another while mean temperature agreed within 1 °C);
cell-mean ignition took 1,350 s at 0.2 m against a closed form of 5.2 s; wall heat exchange gave 104 MJ/m² against a
converged 48. *Consequence:* a CLAUDE.md physics standard; every law reconstructs the sub-cell profile, evaluates the
law on it, and integrates.

### 3. Conserve everything an agent might learn from (2026-11-16)

**Games usually delete debris; a learning agent needs mass and energy accounted for.** *Evidence:* destroyed cells
took their heat with them; a fire kept heating air after its fuel was gone (2.67 million °C by turn 200); sending all
destroyed mass into the room's air would have filled a room with 1.3 kg/m³ of particulate. *Consequence:* a ledger
test, mass to a debris pool per room, and a fuel model that burns what exists.

## Perception and the body

### 4. Perception must come from world physics, not designer events (2026-11-16)

**Most games send NPCs designer-placed stimuli (noise events, sight cones). A learning agent can only learn cues
the world actually produces.** *Evidence:* in Phase 1's well-mixed rooms with no radiant heat, nothing changes as an
NPC approaches a fire until it touches it, so the lab's lessons are unlearnable there. *Consequence:* each phase of
the roadmap adds the physical sources of cues (sound, light, smoke layers, radiant heat); the Phase 1 lab is a
physics benchmark first.

### 5. Feel only what a body can sense; instrument the rest (2026-11-16)

**An "oxygen pain" sensor is a caricature: people feel rising CO₂ (air hunger), not low O₂.** *Evidence:* the senses
research (`docs/design/research/signals/maxim_senses.md`). *Consequence:* the receptor-first rule. Name the human
receptor or drive, or give the world an instrument instead. Every hazard needs a cue before harm and an action that
relieves it, or the agent learns helplessness instead of avoidance.

### 6. An action's effect may arrive after the call returns (2026-11-16)

**Maxim's cerebellum judges an action by sensor values read in the same call; a world that changes only when time
advances teaches it that every action did nothing.** *Evidence:* `tool_bridge.py` reads sensors in the call; the world
changes cells only in `World.advance`. *Consequence:* Phase 3 proposal P3, credit for effects that arrive later.

## Acting, refusals and learning

### 7. A malformed argument is a cognitive error, not a tool failure (2026-11-15)

**Maxim books a refused tool call as a surprising NEGATIVE on the tool, whatever the state.** *Evidence:* PR 1's 33
probes; a JSON typo would teach an NPC to avoid striking the crate altogether. *Consequence:* OD-A16's `call_error`
kind, produced by validation in Maxim's executor before the tool runs (argues against TF2).

### 8. "Done to" and "done by" are different affordances (2026-11-16)

**Maxim's actor tool reads every scene affordance as something the entity does to a target; a world's structure
affordances are things done to it.** *Evidence:* `actor(entity="crate", affordance="ignite")` is refused by default
(target "player"); a call aimed at the wall through the crate's tool would be booked against `crate_strike`.
*Consequence:* OD-C3, a declared direction per affordance, and OD-A16's `wrong_target` kind.

### 9. A late thought is context, never credit (2026-11-16)

**If deliberation latency makes an action stale, refusing it teaches the agent that the tool is bad, scaled by the
game's speed.** *Evidence:* the bio-faithful reviews of the real-time design. *Consequence:* stale refusals go to the
next thought's context; a Maxim change is needed for the failure path to respect that. *Update (2026-11-22):* v1's
receipt never says `stale`, and the host withholds a stale intent's credit (`sem_stimuli.md` §6.2), so nothing reaches
Maxim's failure path; the Maxim change waits for `stale` to return as a receipt kind.

### 10. Names are identities, so match Maxim's own name rule (2026-11-16)

**NPC memories key on tool and sensor names exactly; renaming orphans what an NPC learned, and two names Maxim
resolves alike can send an action to the wrong object.** *Evidence:* "crate" and "Crate" let a call aimed at one burn
the other; `" crate"` answered to `"crate"`. *Consequence:* region names unique under Maxim's normalisation, a
versioned SEM vocabulary, and the format rule that a name's meaning never changes.

## Time

### 11. Agents' machinery needs world time, injected; cognition gets no clock (2026-11-15, reworded 2026-11-20)

**Maxim's substrate reads the wall clock widely, so paused NPCs get hungry and replays diverge.** *Evidence:*
`time.time()` in 178 pymaxim files; the SCN on the host calendar with local time zones; hippocampus de-duplication on
wall time. *Consequence:* Phase 3 items for an injected world clock, a deterministic agent contract and
experience-clock decay. *Reworded (SEM stimulus design D4, OD-A2):* the injected clock is machinery (drift, stamps,
windows); cognition receives no time field, as time research §8.4 requires.

### 12. Nobody waits for a thought, in world time (2026-11-16)

**If the world waits for an LLM, fast-forward and slow motion change how smart NPCs are; if the NPC waits, the hybrid
mode isn't working.** *Evidence:* the real-time design's review. *Consequence:* waiting is defined in world time; the
substrate carries the NPC while it deliberates; the hybrid line in Maxim tunes this by experiment.

## Working with Maxim

### 13. Search Maxim before proposing to it (2026-11-17)

**A game that drives Maxim hard will keep rediscovering what Maxim has already built or planned, so search Maxim's
plans and code before asking it for anything.** *Evidence:* three of Overdrive's upstream asks duplicated Maxim's own
work: a new world clock (Maxim already had several clock mechanisms), a sealed tool roster and effect ceiling (the
shipped `maxim.advisor`), and step-size-invariant trace decay (`docs/plans/experience_clock_decay.md`, #1361 S3a,
which Overdrive's roadmap already tracked as OD-A1). Each was caught by a review, the last one only after a
correction note had been written (`docs/design/reviews/npcs_v3_1/determinism_bio.md` on `phase1/design-v2`).
*Consequence:* every ask cites what Maxim's `origin/main` has on the topic, and a duplicate becomes a question to the
existing plan (CLAUDE.md, "Search Maxim before proposing to it"; backlog B22).

### 14. A staleness basis tied to frame ids goes stale every tick (2026-11-19)

**In a stepped world every tick makes a new frame, so a thought marked stale "when the frame moved on" is always
stale; staleness has to mean that something the agent didn't cause happened on a channel it tracks.** *Evidence:*
the embeddable-agent draft v3 based staleness on the step sequence and frame id, with `fresh`, `stale` and
`superseded` verdicts; Maxim's plan review found that this basis goes stale every step, and that "superseded" has no
Maxim definition (`docs/design/reviews/agent_draft_v3/maxim_review.md`). Maxim's hybrid §A.1b.5 already had the fix:
stale only when a non-self-caused event on a tracked right arrives after `basis_seq`, with the agent's own actions
excluded by attribution (efference copy), since otherwise every in-flight answer is stale. *Consequence:* O38 adopts
§A.1b.5 and routes staleness through Maxim's typed pre-emption handler (`npcs_and_sem.md` §6.6). For any game: key
staleness to typed, attributed events, never to the clock or the frame counter.

### 15. Read the partner's existing utilities before proposing a mechanism (2026-11-19)

**Lesson 13 again, at a finer grain: the duplicates are now helpers and recent fixes, not whole plans.** *Evidence:*
in one review Maxim pointed to three: `utils/seeding.py::make_agent_rng` already derived per-agent seeds with
SHA-256, so our `stable_hash_64_signed` formula would have been a second derivation; the short-question shortcut we
argued about had already been deleted for everyone (#1689, PR #1694; candidates A4, decided 2026-11-17); and `MaximHandle` already embeds an
agent, so our entry point is a separate constructor beside it, and its `stop()` runs blocking consolidation, which a
`save()` must not inherit. Our "machinery side" lean for OD-A20 was wrong for the same reason: SCN features already
reach the model through `temporal_patterns` and `[TEMPORAL]`. *Consequence:* before a draft goes out, grep the
partner's `origin/main` for each mechanism it names (seeding, the shortcut's symbols, the handle, every reader of a
clock it classifies), and re-read the issue tracker for the past week (O40; the draft v4).

### 16. A second write door needs its own reason (2026-11-19)

**Each path by which state can change is a door to guard, test and keep in the parity digest, so one more door is
a cost, not a free refinement.** *Evidence:* the draft v3's port had `apply` (memory writes) beside `settle`
(credit), both host-called; Maxim's candidate A6 already applies proposed writes at settle under B2's digest, and its
review asked for a front-gate reason for the second door or a merge. We had none. *Consequence:* O39 merges `apply`
into `settle`, so `AgentPort` is three calls and the write gate has one place (`npcs_and_sem.md` §6.6). In a game
engine the same rule keeps one intent door into the world.

### 17. A partner's "no" on a determinism leak becomes a red gate, not a workaround (2026-11-19)

**When the partner declines a fix the game needs, record the divergence with numbers and a strict red gate, so the
evidence builds until it can be argued again.** *Evidence:* Maxim's owner kept NAc's anchor similarity on the host
calendar (OD-A20, 2026-11-19). A receipt settled after its trace expires is credited through `0.3 × similarity ×
activation`, counted only above 0.01; a crossed local midnight lowers the similarity by about 0.018, so replay and
learning follow the host's calendar and timezone (lesson 18 has the full reach). *Consequence:* a known divergence
(`npcs_and_sem.md` §12.2), recorded from Maxim's code and our arithmetic, not a run, and two red gates that will
carry the evidence once the agent PR lands them (`checklists.md`; lesson 20); no faked time or pinned `TZ` in the worker, which
CLAUDE.md's push-back rule forbids. The same holds for the second divergence Maxim keeps with #1361 Q5:
`Hippocampus.sleep` forgets on `time.time()`, so a memory accessed once is gone after 3.36 wall days; its red gate
lands with the same PR. Three first
designs of the OD-A20 gate could not fail (an hour shift moves both timestamps; a lone node takes the full share; a
pause tests a different fix): a red gate against a partner's system needs the same can-it-fail proof as any test.

### 18. Overcorrecting a correction is its own failure (2026-11-19)

**A correction states exactly what the code does, no narrower and no wider than the original error.** *Evidence:*
the agent draft framed OD-A20 as a similarity of about 0.70 after a 12 h pause; our fold review found that
normalisation cancels the similarity for a lone node, and the erratum (npcs §12.2, lesson 17, the roadmap) then said
the calendar moves *only* how credit is shared between live-trace and anchor-only nodes. Maxim's delta review (`docs/design/reviews/agent_draft_v3/
maxim_delta_review.md`) found that too narrow: the 0.01 threshold lets the calendar drop a node outright (a receipt
whose only node drops books nothing), anchors set at different host times split differently, and
`TemporalSignature.from_timestamp` reads local time, so the replay machine's timezone moves credit. The fold review saw
the threshold but checked it only at activation 1 (0.3 × 0.70 = 0.21 clears it), not at the small activations an
encoder's match similarity gives. *Consequence:* the
draft v5, npcs §12.2 and the roadmap row restate it, and the red gate is respecified on the threshold, so that it
will fail today once the agent PR writes it. For any correction: re-read the whole function, every branch and constant, before writing "only".

### 19. An efference copy across a process boundary needs an invocation id on every effect (2026-11-19)

**When an agent's actions run in the host, the agent can tell its own consequences from the world's only if every
effect the host reports names the action that caused it.** *Evidence:* Maxim's staleness (hybrid §A.1b.5) excludes
self-caused events by attribution, through GL3.B2's invocation-pid join (`thalamic_relay.md` §5.2): in a robot the
pid is minted at `Executor._run_started` and travels with the tool's own transduction. Embedded, the intent leaves
the agent and its effects arrive later as frame and receipt events from the host; Maxim's delta review noted that
without the dispatching pid on them every self-caused reafference reads as non-self-caused, and every in-flight
reply goes stale. Our intents already had an id, `(actor_id, seq)`, and receipts carried it; frame events did not.
*Consequence:* bodies-part events and pilots rows gain `cause`, the intent record an opaque `invocation`, and the
codec carries the pid (`tile_and_client.md` §3.1, `npcs_and_sem.md` §6.6; plan steps 5b and 7). The agent's own
sequencer mints it and the host only copies it (lesson 20). In any game engine,
an effect record names its causing command from the start, since adding it after the wire freezes is a version bump.

### 20. Evidence is claimed when the test exists, and an id the host can refuse must still come back (2026-11-19)

**Two failures of the same kind: claiming what isn't there yet.** First, a design must not say a red gate "carries
the evidence" before the gate exists; until it lands and runs, the evidence is the partner's code read and our
arithmetic, and the text says so in the future tense. Second, when an agent mints an id for an action the host may
then refuse, defer or drop, every minted id must still come back exactly once, or it is an orphan the partner's
gates count as a broken join. *Evidence:* Maxim's review of the draft v5 (`docs/design/reviews/agent_draft_v3/
maxim_review_v5.md`). Our cover note said the strict red gates for OD-A20 and wall-clock forgetting "carry the
evidence", but PR #8 was docs only and `tests/` had no such file. And on the loop path `Executor._run_started`
mints the invocation pid and can still refuse before `tool.run`; embedded, the agent mints at `step` and our host
can refuse, defer past a budget or drop the intent afterwards, while GL3.B2's gate requires every pid to resolve to
exactly one event. The same review caught a third claim-ahead: step 4 listed the pid, but `PhysicalEventId` and
`EventSequencer` come with Maxim's autonomic G17 stage, unbuilt at 95af47d2. *Consequence:* the documents use
"will carry, once the agent PR lands them"; a settle invariant (one terminal receipt per minted pid, refusals as a
typed receipt, never a physical event) with exit test OD-EA16; and the `invocation` field reserved as null until
G17, refusing any stand-in such as a uuid (`npcs_and_sem.md` §6.4, §6.6; `checklists.md` steps 5b and the agent
PR). For any engine: a command id is a promise of exactly one outcome record, refusals included, and a field filled
with a look-alike before its type exists is worse than an empty one, because replay will trust it.

### 21. A snapshot remembers an older id counter than the log; the authority sets the floor on restore (2026-11-19)

**When an agent's id counter is saved in snapshots and its ids are written to a log, a restore from an older snapshot
re-mints ids the log already holds.** *Evidence:* O43 saves the sequencer's high-water seq in the NPC's agent home;
if a worker dies after minting past its last save, a restart from that save would reissue pids already in the
intent log, breaking replay joins and OD-EA16's one-receipt-per-pid invariant. Found while folding Maxim's review of
v5, not by Maxim. *Consequence:* O44: on restore the high-water is the larger of the saved value and the highest pid
the host logged for that agent, and a dead worker's in-flight pids each get a typed `agent_failed` refusal receipt;
a question to Maxim whether its sequencer accepts a host-supplied floor; a crash-recovery test in the agent PR.
Maxim's review of v6 offered a simpler fix, which O45 takes: each restore opens a new log segment whose number is
part of `session_id`, so restored ids can't collide with logged ones whatever the seq, and the floor survives only
as a host-side collision test. For any engine: whoever saw every issued id (the server, the host) sets the
counter's floor after a restart, never the snapshot alone; and a fresh id namespace per restore removes the need
for a floor at all.

### 22. An agent's semantic layer reads the world; it never runs it (2026-11-20)

**SEM is where an agent perceives and acts, so it is tempting to let it carry world rules too.** *Evidence:* the
accelerant design (T18) began as SEM labels (porous, flammable, an accelerant with speed and intensity modifiers)
and a spread mechanism keyed on those labels. Our bridge already defines an Entity as sensors that reduce over
cells and modulators that act on them (`simcore/adapters/sem/bridge.py`), so a spread rule there would have made the
agent interface decide outcomes the authoritative server should, thresholded a whole entity's mean (D25), and taught
Maxim our rule table instead of fire's regularities. *Consequence:* T18: the accelerant is a per-cell pore-loading
field in the physics; SEM sensors derive porous, flammable and soaked from fields, and a `soak` modulator (Phase 2)
writes the field through the physics. For any engine embedding agents: tags an agent perceives are read-outs of
simulated state, so they can't disagree with the world, and interactions come from one set of laws rather than a
growing table of tag pairs. New sensors and modulators need no Maxim change; a new SEM concept would.

### 23. Maxim's sensors pull, so a frame must be published when an action applies, not only when time moves (2026-11-20)

**Maxim's `Sensor.read()` is a pull with no tick argument, and its modulator tool reads every sensor on the entity right
after `execute` returns, as the action's "cascade effects" (`ModulatorAffordanceTool`, pymaxim 1.3.3). A world that
publishes frames only at physics steps would show the agent the world from before its own act.** *Evidence:* step 3b
part (a) moved the SEM instruments onto published frames (`simcore/core/frames.py`). With publication removed from the
window's close (a planted mutation of `World.__init__`),
`tests/test_sem_bridge.py::test_strike_moves_the_integrity_sensor` went red: the strike landed and the integrity reading
did not move. *Consequence:* every write window that closes publishes, so an application's effect is in the next read
(since step 5a's PR 4a, one frame per tick that applied a record or ran physics, held by
`tests/test_ownership.py::test_the_shipped_path_publishes_one_frame_per_tick_with_a_record_or_physics`). For any engine:
an agent that perceives by pulling needs its own act reflected in the next pull, or its efference copy has nothing to
match; publish on change, and make the action's commit a change. *Amended 2026-11-20 (`sem_stimuli.md` §6.2):* NPC
stimuli are pushed each tick, so the post-`execute` cascade read sees the pre-act frame. Push and pull now hold at
different layers; the cascade read is logging, never credit, and the act's effect reaches the actor in the next tick's
frame.

### 24. A sensor must be something a receptor could sense; read-outs that are true can still be oracles (2026-11-20)

**Lesson 22 was half right.** *Evidence:* the fire redesign's bio-faithful research (`docs/design/fire_model.md`
§5, `research/fire_ladder/6_biofaithful_sem.md` §1.3) found that two of T18's derived labels, flammable and porous,
can't disagree with the world but still give every NPC knowledge no receptor delivers: they are material constants,
so an agent reading them learns our table, not fire. The other labels (soaked, burning) were yes/no, which thresholds
a whole entity's mean, the D25 hazard lesson 22 itself cites; `states_of_matter/sem.md` N2 ("fractions, never
labels") had already said so. *Consequence (pending the owner's ruling on fire_model §11 item 7):* the world computes the
physical stimulus at the receptor (tissue temperature at receptor depth, with incident flux internal; concentrations at the
nose; luminous flame in view), Maxim's receptors transduce it, and state reaches an NPC only as continuous fractions through a
percept. Two leak tests decide where a quantity lives: could an instrument at that spot measure it without a
nervous system (the world's), and is it transduction, meaning a threshold, gain, adaptation or latency (the
receptor's). Tissue is world physics even when its constants come from physiology papers: skin conduction and burn
damage belong to the world, or the body gets a second heat path (design review, `reviews/fire_model/bio_faithful.md`
S4). For any engine embedding agents: "computed from the world" is necessary for a sensor, not sufficient; it must
also be sensible.

### 25. An agent's tool bridge shows the LLM each sensor's unit and value, so a faithful stimulus is still a label to the LLM (2026-11-20)

**Delivering physics instead of labels doesn't keep a language model from reading the physics as a label.**
*Evidence:* Maxim generates a read tool per sensor ("Returns value in {sensor.unit}", returning `value` and `unit`)
and a sense tool naming every sensor (`embodiment/tool_bridge.py:295-321`, `:1002-1020` at `origin/main`
`043eab8f`), found by the SEM stimulus design review (`reviews/sem_stimuli/bio_faithful.md` S2). A skin sensor reads
"celsius … 47.3", and 47 °C means "burning" to the LLM. The same review round found two smaller traps: Maxim clamps
NaN to the top of a sensor's range (`max(lo, min(hi, nan))` is `hi`), and a single digest over the whole stimulus
registry would freeze every law it was meant to keep replaceable (`architecture.md` A-B2). *Consequence:* no
learning claim rests on an LLM-primary NPC alone (substrate-side measures, a counter-prior or dose–response
instead); a question to Maxim on withholding world-channel read tools (`sem_stimuli.md` M19); NaN refused at three
layers; and versions recorded per bound row. For any engine: audit what the agent's *language* channel sees, not
only what its sensors carry.

### 26. A reviewer's suggested fix is a claim like any other: check it before folding it (2026-11-21)

**Advice from a design review is unverified until it is measured or traced.** *Evidence:* in the SEM stimulus
design's delta round 1 (`docs/design/reviews/sem_stimuli/delta1/`), five readers retracted round-1 fixes that v2 had
folded word for word. A lane-overlap gate run on replay can't fail, because replay runs no agents (concurrency F1, a
BLOCKER). A short write on a non-blocking socket is normal, so killing the worker on it kills healthy NPCs (F5;
measured here: 8,192 of 20,000 bytes taken, then `BlockingIOError`). A one-ulp plant on surface conductance doesn't
move L3's column until tick 120–152, and never at zero flux, while a 10⁻¹² relative change shows at tick 0 (executor
B1, re-measured here). A digest chain stored every N ticks finds the first bad window, not the first bad tick (DP2-N1).
Thermal adaptation's "salience-layer route" names no plan at Maxim's `origin/main` (bio N-2). Two other gaps came from
the fold itself: a delivery and digest that turned every new row into a replay break (architecture A-B2), and a budget
ruled on stationary bodies only (DP2-B1). *Consequence:* the v3 fold measured or traced each checkable fix before
writing it, and recorded "unverified" where it couldn't. For any project folding reviews: a reviewer's fix gets the
same check as a source's number, because a test that can't fail, adopted on a reviewer's word, guards nothing.
*Again at step 8's fuel pass (2026-11-22, `docs/design/reviews/client_fuel/`):* the rendering lens's unverified fix
for crossing sticks, an opaque core alpha-tested at coverage 0.5, did fix the occlusion, and it put a hard step in the
edge's ramp that broke the stick-stability bar on the laptop tier (2.55–2.62× the ideal line against 2.0×). A depth-only
core kept both. The fold's own new tests needed the same check: the headless renderer returns an identity transform and
an empty box for any MultiMesh, which satisfied "a slab's local y is up" and "the culling box holds the rods", and
three more mechanisms survived deleting them until their tests were rewritten.

### 27. A host that steps a Maxim body must not step it inside the agent's own tick (2026-11-21)

**Maxim's substrate tick steps the body in a fixed order, and pain is keyed to the situation noted just before.**
*Evidence:* at `origin/main` 043eab8f the substrate-primary proposal runs `note_active_clusters` and then
`evaluate_failures`, so a pain publish is "keyed to the clusters noted above" (`substrate_proposal.py:808-839`; the
W-4 order, `grounding.md:451`), and `loop_gates.py` warns that a second call doubles the tick. The v3 design pushed
stimuli and then stepped the body from the host before the agent's tick (bio D2-S2): drive pain latches on band entry,
so the host's call would publish the onset against the previous step's clusters and the agent's own call would find
the latch set and publish nothing, keying a burn's fear to where the NPC stood up to a cognition step earlier.
*Consequence:* v4 pushes on a cognition tick and leaves the body step to the agent's tick; the host steps the body
only between cognition steps, and how such a publish is keyed is asked of Maxim (M4, a question to `autonomic_layer.md` §3.1.4's out-of-band producer, G9, and #1176).
For any game hosting Maxim: deliver stimuli from outside, but let the agent's own loop own the order in which its
body is stepped and its pain is credited.

### 28. A world that holds a regulated variable fixed does the agent's homeostasis for it (2026-11-21)

**The world should be the body's plant; the agent should be its controller.** *Evidence:* v4's core law (a) held the
core node at 37 °C, which closed the energy books by booking whatever power that took. The final round showed what
that costs (Physics S1, Bio-faithful F-S3): a body 3 m from the tile's fire absorbs about 1.0 kW, so a free core would
rise about 5 K in 20 world minutes, while the held core reads 37.0 °C and sinks the heat unbooked. A bound
`core_temperature` would then be a constant, and Maxim's own two-sided thermoregulation need (`autonomic_layer.md`
R-2, §3.3) could never be exercised or learned. *Consequence:* the owner re-ruled PH2-S2 to (c): a free core, an
energy-conserving plant (metabolism, skin blood flow, sweat, shivering), and effector commands reserved in the
contract, set by a marked ANALOG stand-in until Maxim drives them (M20). For any game hosting Maxim: model the
physiology the controller acts on, and leave the set point and the effector choice to the agent; a world that
regulates on the agent's behalf hides the very signal the agent is supposed to learn from.

### 29. A host that schedules many agents must own placement, and that argues with a recorded Maxim rule (2026-11-21)

**Maxim's distributed infrastructure moves inference, not agents, and its router is a scheduler of its own.**
*Evidence:* at `origin/main` 043eab8f the networked mesh was deleted as dead code (`mesh/__init__.py`), and the peer
system sends a machine's model calls to a leader. Maxim already splits capability (a function's tier) from placement,
and records that placement "rides on `LLMRouter`'s existing … failover — NOT a new resolver" (`docs/agents/llm-routing.md`).
The router fails over inside one call: it records who served (`last_used_*`, `router.py:285-316`), but the caller didn't choose. It reads
process state (`router.py:77`, `:201`). Underneath, no backend streams to its caller, the cloud backends turn most
failures into an empty reply, retries run inside the call, and no timeout bounds a whole call. A host that books
deadlines, slots, consent and spend per placement, and must kill a stuck call, can't let a second scheduler run inside
its dispatch. *Consequence:* O46–O53 (`docs/design/inference_placement.md`): a request names a function, the lane
picks the placement, one gateway process per placement makes one backend call per dispatch, and the cache key never
names the model. The rule we argue against is OD-A24, with this evidence; the backend gaps are OD-I9, OD-I10 and
OD-A25. A first draft missed Maxim's placement rule because its search never used the word "placement": search for
the design's own nouns first. For any game hosting Maxim: let the agent ask for a kind of model, let the host decide
which one answers and record that it did, and take the disagreement to Maxim rather than around it.

### 30. A local model's latency is the machine's, not the model's: measure it under the load the game will share (2026-11-21)

**The LLM spike measured a quiet machine; the game never runs on one.** *Evidence:* the spike (`spikes/llm/results/`)
timed qwen2.5:3b at about 0.3 s to the first token and 1–2 s for a short reply, at a load average near 7. The
vertical slice's vendor asked the same model for its lines while the world, the client and other sessions shared
the machine (load average 125–142): every line timed out at 2.5 s and fell back to a canned one, and direct calls
took 48 s cold and 8 s warm. On the owner's quiet Mac mini (load average about 2.5), the same voice code took
1.37 s cold and 0.23 s warm (median; p95 0.27 s), with 0 fallbacks in 20. The vendor still walked to the fire and put it out on time, because a behaviour tree
decided and the model only spoke (`spikes/slice/slice_server/npc.py`, `voice.py`). `npcs_and_sem.md` §4.5 bounds the
world at `D / L` while a thought is pending, with L = 3 s. The game alone on the mini gave L = 0.23 s, well inside
that; other processes loading the machine pushed it to 8 s, where the bound would be 1/8 of real time. L is set by
what shares the machine, not by the model or the game. *Consequence:* for any game hosting Maxim in its LLM-harness mode, latency is set by everything
else the machine is doing, so (a) keep a decision path that acts within a tick without the model (a reflex, a
substrate policy, a behaviour tree), and let the model add to it rather than gate it; and (b) set L from a
measurement under the game's expected load, then recompute §4.5's dial with it before the NPC line commits to it.

### 31. An agent's refusal vocabulary must be closed, and it still has to steer (2026-11-21)

**What the world tells an agent when it refuses is an input to the agent's next thought, so it is a protocol, not a
message.** *Evidence:* step 3b part (b) replaced the SEM membrane's free-text errors with the refusal-code enum
(`simcore/core/refusals.py`, WT-S1; boundaries §5.4). The old words echoed the caller's own values ("got 1e+12", bounded
by `checks.shown`, never scrubbed) and repeated a made-up parameter's name into the next prompt. In Maxim (`origin/main`
043eab8) that text reaches the deliberation prompt (`exec_agent.py`, "tool: FAILED: <error>"), the episode's recall
tokens and its dedup key (`memory/types.py`), so every refused value was a distinct episode; a code makes repeated
refusals of one kind one recognisable episode. The cost was real too, and two pieces had to come back: a field name from
the reader's own schema (`out_of_range (power_w)`, a name we wrote), and the fix for the commonest refusal on Maxim's
orchestrator path, where `OrchestratorActorTool` defaults `target` to the agent under test's body: there `wrong_target`
is the likeliest answer, and bare, it let a caller retry "player" or "self" forever, so it is `wrong_target (target)`
with the rule stated in each affordance's description (round 1 review, Bio-faithful S1). On an NPC's own per-entity tool
`target` has no default, so the refusal arises only when the model adds one. The namesake case kept its own code, as it
had its own words before: "name the crate" would loop it. Authored bounds left the error text; they stay in the
description an agent reads. *Consequence:* codes are append-only from their first shipment (the intent log and the wire
carry them), a refusal names at most a name we wrote (a schema field or a call key), and a code is split when two causes
need different next actions. For Maxim: it already has a closed vocabulary, `ToolErrorKind` and `GATE_REFUSAL_KINDS`
(`tools/base.py`), threaded through credit by `docs/plans/tool_failure_credit.md`, but `ModulatorResult` has no kind, so
`tool_bridge.py`'s `ToolOutput(success=False, error=result.error)` books every SEM refusal as an external failure, which
pain reads as tool failure. That is evidence for OD-A16 (its `call_error` and `wrong_target` kinds, and
`docs/maxim_upstream/propose_settle_amendment_DRAFT.md`), not a new item: the ask is a kind on `ModulatorResult` that
`RefusalCode` maps onto. Maxim's own refusals still answer in prose that echoes its caller (`simulation/tools.py`), so
an agent's prompt mixes both conventions until then. A SEM refusal reaches two readers with no kind at all (`error_kind`
is `None`, `tools/base.py`): the pain detector books it as an external failure (`executor.py:789`), and the replan path
renders it as "Failure type: None" in the replan prompt (`loop_state.py:248`, `plan_document.py:281`). Neither
classifies by the text, though the replan prompt carries it verbatim as "Failure reason:" (`plan_document.py:280`);
Maxim's one text classifier, `classify_failure_type`, runs only from a planner its own docstring calls dormant (delta
rounds 2 and 3, SF-1, R3-5).

### 32. A writer's identity must be a capability its owner holds, not a name it gives (2026-11-22)

**When many laws share one world, "who is writing" has to be unforgeable, or the field registry describes intentions,
not the world.** *Evidence:* step 5a's PR 2 let each law narrow the write window to its own name (`as_writer(name)`).
Two reviewer plants passed every guard (`reviews/sim_laws/round1_exec_physics.md`, SF1): thermal damage writing
`material` "as topology", and heat writing "as construction", which gave it `material`, `integrity` and `regions`. A
handle taken in one law's block stayed writable for the rest of the window, and a read-only view could be unlocked in
one line (SF2). The fold makes each writer a token claimed once, at its owner's import (Topology, construction, and
the orchestrator for every law); the orchestrator runs each law narrowed to its token and its declared `reads`, and a
block's writable arrays are revoked when it ends, at about one array copy per law per substep. The plants now fail at
runtime and in a source scan. *Consequence:* any field a future law (fire's solid and contact laws, the body laws) or
an NPC-facing path writes is held to the registry by the same tokens. Python can't make a token unforgeable against
code that reaches into private names, so a scan holds the tokens to their owners' modules; that is the residual, and
it is named. For Maxim: none yet; this is the engine's half of the SEM contract (`sem_stimuli.md` §7.1), where a body
law's writes must be as checkable as a physics law's.

### 33. An event shorter than the physics step must still reach the physics, or the NPC never feels it (2026-11-22)

**A world that reads its sources only at the physics tick loses every event that starts and ends between two
ticks.** *Evidence:* before step 5a's PR 3, physics read the heat sources standing at the physics tick, so a fire lit
at tick 2 and doused at tick 4 (at T3, ticks of 0.1 s and a physics step every 5) put no energy into the world, and
fires lit at ticks 66 and 69 gave bit-identical states. `source_exposure` (sim_core.md §3) records which value stood
at the end of each tick and deposits each its integer ticks' share; `tests/test_exposure.py` holds it to
`k · tick_us · power` for k = 1 to 5, a douse, a re-ignite at a new power and a replacement. *Consequence:* the
stimulus an NPC can sense (a brief flare's heat) exists in the world at all; the per-tick digest and the save must
carry the exposure too (PR 4b), or a replay from a mid-step save would lose it again. For Maxim: none yet; it is the
engine's precondition for any stimulus shorter than a physics step reaching the SEM sensors.

### 34. When the world models something below its grid, the renderer and the NPCs' senses both have to follow it, and they become two producers of what the fire looks like (2026-11-21)

**A sub-grid representation (fuel as objects in metres, not cells) breaks every consumer built on cells, and the
renderer and the stimulus path each have to be rebuilt on it separately.** *Evidence:* the shader branch (#31) drew
glow and flames from per-cell channels (`surface_glow`, `burning`) after the fire build spec had moved fuel into
sub-grid objects (B42). The cell raymarch walks straight through fuel sitting in air cells, and a 20 mm stick is
0.6–2.4 px across the zoom range, so the client needs a second pass of instanced meshes and a pixel floor
(`docs/design/client_objects.md` §2, §4). Once rebuilt, the presentation path shows the player three cues no stimulus
row carries: burning brightness from the solid model's ignition latch, char darkening, and a client-drawn Phase 1
flame. An NPC's sight row reads radiance from surface temperatures only (`sem_stimuli.md` §2.2), so a just-ignited
stick looks to an NPC like unburnt wood at the same temperature. *Consequence:* for the world, each divergence is
named where the presentation is built (`client_objects.md` §5.4), so that a perception bar that misses is traced to
the game's split, not to Maxim. For Maxim there is nothing to ask yet. Whether sight needs an albedo or flame
channel is the NPC fire note's question, against OD-C8.

### 35. A name in a docstring is not a plan: Maxim's imagination designs behaviour, not bodies (2026-11-22)

**A game that assigns work to a named Maxim component must check that the component is built, or planned, to do it.**
*Evidence:* since Phase 0, `simcore/core/imagination.py` said "Maxim's ImaginationDesigner, later" would propose
imagined objects as primitives made of materials. At `origin/main` 688c4b02, `ImaginationDesigner.imagine`
(`src/maxim/imagination/designer.py`) calls `EntityDesigner.design()` (`simulation/entity_designer.py`), which asks an
LLM for a SEM entity: sensors, modulators, affordances and failure modes. It has no geometry, dimensions or materials,
and no Maxim plan adds them. We searched geometry, primitive, mesh, voxel, metres, cylinder, text-to-3d and object
spec, and found nothing. Maxim's claim is learning without fine-tuning (`README.md:28`), so a model trained to write
geometry can't live inside the agent. *Consequence:* Phase 6 had no spec author.
- The author is now a generator on the world's side (O57), never the agent's imagination.
- Once an imagined object exists, what it does to an NPC is an ordinary world event. A first draft of O57 borrowed
  Maxim's provenance words (`apparatus` for the generator, `imagined` for its objects). In Maxim those label
  body-consequence records (`sem.py`, `OUTCOME_PROVENANCE`), and `apparatus` is never learned from, so using them
  would have hidden from NPCs that an imagined table burns (round 1, Architecture B1).
- Whether Maxim should know that an entity was generated is a question for Phase 6's design.
- The spec generator spike (`docs/design/research/specgen_spike/plan.md`) measures the first step.

### 36. A reasoning model's default thinking can spend the whole reply budget: switch it off in the chat template, and prove the switch with a control (2026-11-22)

**A generator that thinks before it answers can run out of tokens before it writes a single field.** *Evidence:* on
the owner's Mac mini, before the spec generator spike's freeze (`docs/design/reviews/specgen_spike/freeze_delta2.md`):
- **Without the switch,** llama-server (build 10621) with the model's own template, Qwen3.5 4B (Q8_0) put all 4,096
  reply tokens into reasoning (11,926 characters) and returned an empty answer, so the scorer would class every
  reply `truncated`. The JSON-schema grammar didn't prevent it: with the grammar on, the reasoning still took all
  4,096 tokens (12,136 characters). The grammar constrains the answer, and the answer never started.
- **With the switch,** `chat_template_kwargs: {enable_thinking: false}`, all 19 probe replies (12 under A2, 6 under A0
  and one same-seed repeat) had no reasoning, and every grammar-constrained reply parsed, at about 40 tokens/s (about
  5 s per spec).
- **Gemma 4 31B** also thought by default, but within the budget: 3,170 and 3,655 tokens of reasoning, four to five
  minutes a call at 12 tokens/s, before it answered. With the switch it didn't reason at all.
- **Qwen3.5 27B,** the reference model, matched S: without the switch it spent all 4,096 tokens reasoning (11,093
  and 11,601 characters) for about 520 s per call and answered nothing; with it, all 19 replies parsed at about
  8 tokens/s.

A silent "no thinking" proves nothing until the same call without the switch shows thinking.

*Consequence:* any game call to a local model (imagination, an NPC's voice) pins the template's thinking switch in
its frozen settings, and verifies it once per model and engine build with a control call. A default flip costs the
whole reply budget: the reference model took about 8.6 minutes a call, against lesson 30's
latency bound of seconds. The spike records the switch in `spikes/specgen/arms.yaml` and its engine build there too.

**Maxim has the same gap (run on pymaxim 1.3.4, 2026-11-22).** Pointed at the same llama-server serving S, Maxim's
`_OpenAIBackend` returned empty content after 12.5 s: 512 of 512 tokens, stop reason `length`. Nothing in the backend
can switch a template's thinking off, so a reasoning model behind a Maxim lane answers nothing (OD-I12, a question to
its deferred self-hosted-servers plan). The first attempt found a second defect: without `allow_local_endpoints`, the
backend blocks the loopback URL, and because its refusal checks the provider's name rather than its type, a provider
keyed `local` of type `openai` falls back to the OpenAI client's default endpoint. The test prompt went to
api.openai.com (refused 401). A blocked local endpoint can fail open to the cloud (OD-I11). For a local-first game (O58),
any gateway built on Maxim's backends must refuse there, not fall back. Running Maxim found both; reading its plans
found neither.

### 37. A stepped world's interim port hands an action's read-back whatever physics ran on that call, and Maxim learns from it (2026-11-22)

**Through a submit-and-step port, Maxim's "read right after execute" shows an instant effect (a strike's crater) in the
action's own read-back, but a slow one (a fire's heat) on whichever later call happens to run a physics tick, and Maxim
learns from that read-back.** *Evidence:* since step 5a's PR 4a a frame is published once per tick (sim_core.md §4), so
the bridge writes through a `Port` its test or host owns (§13): each call that reaches stage 2 is one record and one
tick (`tests/test_sem_bridge.py::test_the_membrane_steps_only_through_its_port_one_tick_per_call_that_reaches_stage_2`).
The PR's Bio-faithful review drove pymaxim 1.3.3's `ModulatorAffordanceTool` through that port, alternating `ignite` and
`extinguish` on the crate: `temperature_max` read back 20.0 for calls 1 to 4, 21.29 on call 5 (a physics tick) and 22.15
on call 10, an extinguish. In 1.3.3 that read-back is more than logging, though it is not reward credit:
`maxim/embodiment/tool_bridge.py` reads every sensor after `execute` (line 584), passes the readings to
`Cerebellum.observe_from_action(actual=...)` (line 885) whenever a cerebellum is attached (line 860), and puts them in
the tool's output as `entity_state` (line 908), which reaches the LLM. The cerebellum is a forward model "for sensory
prediction instead of reward" (`cerebellum.py`'s docstring), so the douse's predictor learns to expect heating, and the
model reads that it heated; NAc's credit comes from the interoceptive drives, not from this read. Lesson 23's amendment
("the cascade read is logging, never credit") holds for reward, not for prediction or the prompt (PR 4a delta 2, D2-N2).
*Consequence:* no outcome bar is measured through the port (§13), and `phase1/agents` replaces it with a pending result
and the effect in a later frame. For Maxim: this is lesson 6's point, already Phase 3's OD-A16 (effects measured later;
the cerebellum observing at settle), and this is new evidence for it, not a new item.

### 38. A held act's effect lands after Maxim has retired the call, so call-window credit pays the wrong act (2026-11-22)

**A `kindle` is applied at once, but what it does is decided by physics many steps later.** *Evidence:* in Phase 1
the torch's pilot is a prescribed flux on fuel strips, and a strip flashes only once its own profile reaches
m''_flash (`docs/design/torch_pilot.md` §5). That takes physics steps of 0.5 s each, while the pilot is still live. On
Maxim's side, read at `origin/main` b98954f7:
- R4's credit is anchored to the executor call window, and "relief landing after a call returns credits the NEXT call"
  (`docs/plans/roadmap_1_4.md`, R4);
- `docs/plans/tool_failure_credit.md` (lines 76–80) retires a tool event at invocation end, removing the 300 s pending
  window, and warns that "R4 delayed credit must not assume the window";
- what reaches past a call is weak or on the wrong clock: the `tool:kindle` eligibility trace (0.3, ×0.9 per loop
  iteration, onto a `_reward_bias` capped at 0.20; `docs/plans/lookback_primitive.md`), and the anchor tier's 300 s
  window, read on `time.time()` (`nac.py`; OD-A20).

So a Phase 4 NPC that kindles a slab and walks away would credit whatever the flash causes to its walk, not its
`kindle`. Our own amendment draft (`docs/maxim_upstream/propose_settle_amendment_DRAFT.md`) assumes the opposite:
"consequences that take seconds stay with NAc's temporal window". In Phase 1, too, the flash reaches no stimulus row,
because no row carries flame (`client_objects.md` §5.4).

*Consequence:* the evidence for OD-A16 is two delays, measured separately at 6.1b: from the act to the physical
outcome (`t_flash`), and from the receipt to the first change in a declared stimulus row. The second one, not the
first, sizes any credit window. The amendment draft's slow-effects paragraph has to be revisited before it goes
upstream.
