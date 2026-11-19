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
probes; a JSON typo would teach an NPC to avoid striking the crate altogether. *Consequence:* Phase 3 item 10,
validation in Maxim's executor before the tool runs (argues against TF2).

### 8. "Done to" and "done by" are different affordances (2026-11-16)

**Maxim's actor tool reads every scene affordance as something the entity does to a target; a world's structure
affordances are things done to it.** *Evidence:* `actor(entity="crate", affordance="ignite")` is refused by default
(target "player"); a call aimed at the wall through the crate's tool would be booked against `crate_strike`.
*Consequence:* Phase 3 item 11, a declared direction per affordance.

### 9. A late thought is context, never credit (2026-11-16)

**If deliberation latency makes an action stale, refusing it teaches the agent that the tool is bad, scaled by the
game's speed.** *Evidence:* the bio-faithful reviews of the real-time design. *Consequence:* stale refusals go to the
next thought's context; a Maxim change is needed for the failure path to respect that.

### 10. Names are identities, so match Maxim's own name rule (2026-11-16)

**NPC memories key on tool and sensor names exactly; renaming orphans what an NPC learned, and two names Maxim
resolves alike can send an action to the wrong object.** *Evidence:* "crate" and "Crate" let a call aimed at one burn
the other; `" crate"` answered to `"crate"`. *Consequence:* region names unique under Maxim's normalisation, a
versioned SEM vocabulary, and the format rule that a name's meaning never changes.

## Time

### 11. Agents need world time, injected (2026-11-15)

**Maxim's substrate reads the wall clock widely, so paused NPCs get hungry and replays diverge.** *Evidence:*
`time.time()` in 178 pymaxim files; the SCN on the host calendar with local time zones; hippocampus de-duplication on
wall time. *Consequence:* Phase 3 items for an injected world clock, a deterministic agent contract and
experience-clock decay.

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
calendar (OD-A20, 2026-11-19). A receipt settled after its trace expires is credited by `0.3 × similarity ×
activation`; a crossed midnight moves the similarity by about 0.017, and a 12 h pause inside the 300 s window drops it
from about 1 to about 0.70, so replay and learning follow the host's clock. Because credit is normalised, the
calendar only moves how a receipt is shared between live-trace and anchor-only nodes, a narrower crack than first
written. *Consequence:* a known divergence (`npcs_and_sem.md` §12.2) and a red gate on a shared receipt across
midnight (`checklists.md`); no faked time in the worker, which CLAUDE.md's push-back rule forbids. Two first designs
of that gate could not fail (an hour shift moves both timestamps; a lone node takes the full share): a red gate
against a partner's system needs the same can-it-fail proof as any other test.
