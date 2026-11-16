# Bio-faithful integration: delta review 1 of `docs/design/realtime_lanes_coop.md` (v1, 2026-11-15)

Reader: Bio-faithful integration lens (`docs/code_review.md`). Overdrive at 02338ef; Maxim read at 4b773ef8
(read only). Scope: whether v1 folded round 1 (`bio_faithful.md`) correctly, plus §3.4, §4.3, §6 items 10 to 18
and `docs/maxim_upstream/hybrid_1_5_line_DRAFT.md`. Every claim about Maxim cites the file it comes from.

**Verdict.** Decision 7 is faithful to Maxim in its core. Maxim's own `agents/llm_worker.py::LLMWorker` states
"Main loop NEVER waits on LLM", and DN runs on its own thread under the loop. But v1 words "waiting" without saying
in which clock. That makes the headless cradles and the 1.5 line's own H2 sweep undefined or forbidden, and it
quietly drops round 1's case for a world-time deliberation latency that doesn't depend on the host. The stale
refusal "it can learn from" would, through Maxim's real failure path, write a state-blind negative causal link
whose rate rises with the dial: the wrong lesson, through the strongest learning channel. The 1.5 draft's claim and
H3 bring back the "sometimes substrate, sometimes LLM" mode switch that Maxim's hybrid plan rejected, without naming
that decision. Several pushback items don't name the decision they argue against, which the new CLAUDE.md rule
requires.

Counts: 3 BLOCKER, 8 SHOULD-FIX, 4 NIT.

---

## BLOCKER

### D1. "Nothing waits" doesn't say which clock, so cradles and H2 are undefined or forbidden

**Location:** decision 7; §4.3 ("Nothing waits for a thought", "applies on the first tick after it arrives", "With
live models, thinking speed in world time depends on the dial"); §3.4 ("headless cradles, unpaced"); §3.1
("Unpaced is a host mode"); draft H2 ("stub deliberation latency swept over world time"); round-1 finding 5(d).

- **What decision 7 protects is world time.** The NPC doesn't freeze and the world doesn't stop in the NPC's
  lived time. A wall-clock lockstep doesn't break that. The host stops calling `step` until a thought is in, and
  the thought then applies at a declared world tick `T + d`, with the NPC's substrate running through `T..T+d`.
  Inside the world, no tick is missing and nobody waited. In the live game, a wall hold shows as a stutter, and
  the owner has ruled it out there. Headless has no one watching.
- **Cradles, as v1 has them.** They run unpaced, with arrival-driven application and world-time abandonment.
  Take a laptop tile stepping unpaced at about 300× (§2.3). A 3 s wall-clock thought is then about 900 world
  seconds, which is past any sensible `max_age_ticks`. A cradled NPC's deliberation is abandoned or applied
  minutes late, and how often depends on the host's GPU and load. Cradles are where NPCs' lives are made, and
  Exp 64's arms are cradle runs. Arm differences would then include host-speed-driven abandonment, which is the
  G0 outage abort (v1 §6) firing on a fast machine.
- **H2 needs exactly the lockstep.** "Latency swept over world time" with a live model means: hold in wall time
  until the result is in, then apply at `T + d`. v1's §4.3 has no such mode, and the draft's wording ("nothing
  ever waits") reads as forbidding it. Round-1 finding 5(d) asked for this mode ("headless never times out"), and
  the fold lost it.

**Fix:** in §4.3, define waiting in world time. Then add a **world-time latency mode** for headless runs (cradles
and experiments). Each request kind has a declared `d` in ticks, from `data/`. The thought applies at `T + d`. The
host blocks in wall time until the result is in. If the model fails, it's a typed `thought_failed` and never a wall
timeout. Live interactive play keeps arrival-driven application. Say in decision 7 and in the draft that the
lockstep is not "waiting", because the NPC lives through `d`. Name the per-kind `d` as an **ANALOG** (a thinking
latency that doesn't depend on what is being thought about).

### D2. The stale refusal, fed back "as an outcome it can learn from", teaches a latency-caused, state-blind lesson

**Location:** §4.3 ("An action the world has overtaken is refused as stale, and the refusal goes back to the NPC
as an outcome, which is something it can learn from"); draft H2 measures; Maxim
`docs/plans/tool_failure_credit.md` (finding 3, TF2); `docs/wiring/substrate-learning-channels.md`.

- **Where a refusal lands in Maxim today.** A failed tool books two NEGATIVE links:
  `runtime/tool_dispatch.py::record_outcome` (`nac.observe`, keyed on the error text and goal) and
  `PlanHistoryBridge.record_plan_outcome` (`tool_failure_credit.md`, "What the dive found" 3). The `nac.observe`
  link is the **causal link** of `substrate-learning-channels.md`. That link is keyed `tool:X`, it's
  **state-blind**, and it is the channel that saturates selection.
- **What it would teach.** The cause of a stale refusal is that the plan was built on the world at `T` and the
  world changed before `T + d`. Nothing in it says the tool is bad. Credited as a tool failure, it writes "ignite
  is a bad action" with no state attached, and that's the wrong causal link. If it's credited instead to the
  cluster at `T + d`, it penalizes the tool in a state the NPC never chose it in.
- **It brings the dial in.** With live models, `d` in world time scales with the dial (§4.3), so the stale rate
  does too. At the "wait" preset (§3.4), NPCs would pile up negative causal links in proportion to how fast the
  player fast-forwards. §3.1 keeps the dial out of percepts, but this path writes it straight into learned state.
  That's Bio-11's rule, broken through credit instead of through a percept.
- **Maxim's recorded decision already rules it out.** TF2 gives failure credit "only when the invocation reached
  `tool.run`". A refusal by the game's validator, before the SEM modulator runs, is not a tool failure under TF2.

**Fix:** in §4.3, a stale refusal is a percept to the **deliberative** layer. It goes into the next thought's
context ("the plan failed: the door is already open") and is logged. It never reaches NAc credit through the
tool-failure path. Whether a stale plan should carry a learning signal at all, and where it would go, is a Maxim
question. One candidate is a deliberation-side prediction error, not a tool value. Add it as a Phase 3 item that
cites TF2 and the causal-link entry. Until Maxim answers, PR 4's stub refusal is an outcome reply and a meter, and
nothing that later wiring would read as reward. Replace the phrase "something it can learn from" with what the
NPC actually gets.

### D3. The 1.5 draft's claim and H3 are the mode switch the hybrid plan rejected, and the decision isn't named

**Location:** draft "The claim" ("Its substrate (reflexes, NAc's learned action selection, drives) carries it
through the world while an LLM thought is in flight"); H1's battery ("keep away from fire, find food and rest");
H3; §4.3 ("its reflexes, habits and the action it's already doing"); Maxim
`docs/plans/deferred/hybrid_substrate_reflex_runtime.md` ("Why NOT `aut_mode="hybrid"`").

- **The decision.** The hybrid plan says: "Hybrid is not 'sometimes substrate, sometimes LLM cognition'; it's 'a
  reflex runs *underneath* continuous LLM cognition.'" The reflex is a DN `Behavior` on an **isolated** reflex NAc
  (A3, BL-4). `recommend_action` as the agent-level selector is substrate-primary mode, and that mode *replaces*
  LLM selection: `runtime/agent_loop.py` calls the substrate tick "Mutually exclusive with the LLM submit branch".
- **What the draft proposes instead.** Agent-level NAc selection fills the gaps between thoughts, and H3 starts a
  thought when `recommend_action` returns `None`. That is "sometimes substrate, sometimes LLM", with the LLM as
  the fallback when the substrate is unsure. It may be a better design. It's still a reversal of a recorded Maxim
  decision, and the draft doesn't name it. Under CLAUDE.md's new rule and Maxim's process, it gets refused, or
  worse, built without the argument.
- **The battery tests jobs the hybrid's reflex layer doesn't have.** Finding food and rest is agent-level
  selection: substrate-primary NAc or the LLM. It is no DN reflex's job. H1's "substrate floor" on food would
  measure substrate-primary competence and attribute it to the hybrid.
- **"Keep away from fire" has no Maxim mechanism to run in flight.** DN's behaviours are orienting, startle,
  social, idle, motion and `turn_around` (`default_network/behaviors/`), all fed by visual detections
  (`_process_tick` returns early without them; round-1 finding 3). `embodiment/reflex.py::ReflexRegistry` is
  innate, keyword-on-percept-text, and dispatches `damage_component` or `set_entity_sensor`, which are body
  effects, not locomotion. A withdrawal reflex is new mechanism. Testing "the substrate" on it tests whatever the
  game builds.
- **"Habits"** in §4.3 has no referent in Maxim's LLM-primary or hybrid mode.

**Fix:** choose, and say which.
- **(a) Faithful to the hybrid plan.** In-flight substrate means the DN reflex layer on its own isolated NAc
  (protective and orienting) plus the action already executing. H1's battery splits into reflex jobs (respond to a
  strike, withdraw from heat: name a withdrawal `Behavior` as new mechanism, pre-registered) and deliberative jobs
  (food and rest), measured separately.
- **(b) Argue against the decision.** Keep NAc agent-level selection in flight and H3's trigger. The draft then
  names "Why NOT `aut_mode="hybrid"`" as the decision it revisits, gives the evidence, and says how the two
  selectors share one NAc without the leak that A3 and BL-4 exist to prevent.

Delete "habits" from §4.3, or define it as (b).

---

## SHOULD-FIX

### D4. H3's trigger, "`NAc.recommend_action` returns `None`", is grounded in code but doesn't mean "no opinion"

**Location:** draft H3; Maxim `decisions/nac.py::recommend_action` (lines 2186 to 2640);
`runtime/substrate_proposal.py::propose_via_substrate`; `default_network/gate.py::ThalamicGate`.

- `None` is returned when the best score is below `min_confidence`, a tunable defaulting to 0.3, or when
  `available_tools` is empty. `propose_via_substrate` also returns `None` for missing plumbing: no NAc, no
  executor, no registry.
- **With exploration on** (`substrate_explore_bonus_weight > 0`), the explore-first hard gate forces a proposal
  for any untried tool. `None` then never fires while the NPC knows least, which is when deliberating matters
  most.
- **With exploration off** (the default, 0.0), a new NPC returns `None` almost every time unless a drive above 0.5
  matches the substring heuristic. It would then deliberate constantly early on.
- So H3 as written is mostly a sweep of `min_confidence` and of the exploration setting.
- In substrate-primary, `None` means IDLE ("treats this as IDLE for that tick"). Using it as the cue to deliberate
  changes its meaning.
- **Maxim already has a bottom-up trigger to deliberate:** `ThalamicGate`'s escalation (novelty and salience,
  goal relevance, speech, anomaly, rapid approach, attention lock), plus `llm_submit_interval`.

**Fix:** H3 compares against Maxim's real triggers: gate escalation, the fixed interval, and a confidence-margin
or uncertainty measure from the score table (the provenance components are already emitted). Fix `min_confidence`
and the exploration setting per arm, and report them. Classify every `None` by cause (below threshold, no tools,
plumbing) so a plumbing `None` never counts as "no opinion".

### D5. H1's control arms duplicate each other and leave out the control the claim needs; the kill criterion tests the wrong job

**Location:** draft H1 arms; "Kill criterion"; "Open for Maxim's review" (how the "world waits" arm is reported).

- **Two arms are the same arm.** In world time, "on with zero latency" and "world paused for each thought" are
  both `d = 0`, since a live model can only reach zero latency through a pause. They differ only if one uses a
  stub and the other a live model, and then the comparison mixes deliberation quality with latency.
- **The paused arm isn't a caricature, but calling it "the world waits" invites the misreading** the draft worries
  about. Under D1 it is "lockstep, `d = 0`". It's a reference point, not a mechanism.
- **The missing control: reflexes off, latency on.** The hybrid claim is that the substrate makes up for the
  deliberation latency. That needs a 2×2 of reflex layer on or off against `d` at 0 and above 0. Without the
  reflexes-off arm under latency, a flat H2 curve could come from a world too gentle to punish latency, and a
  steep curve from a deliberator that's slow at everything.
- **The kill criterion is a conjunction of two things that miss.** "H1 floor near zero on every task" is expected
  under the hybrid plan for deliberative tasks (D3). And "H2 collapses at small latencies" passes with reflexes
  that do nothing, if the world is gentle.

**Fix:**
- Arms: (no deliberation) × (reflexes on, off) × `d` ∈ {0, swept}, with one deliberator held constant across arms.
  Use a scripted oracle for the primary analysis and a live model as the replication.
- Kill: on reflex-job tasks, the reflexes-on arm doesn't reduce the latency penalty against reflexes-off at
  matched `d`.
- Report `d = 0` as "lockstep reference".

### D6. H4 measures what the reflex does, not what cancellation is for

**Location:** draft H4 (measures: "time to a protective action"); §4.3 ("one outstanding thought per NPC"; "Pain
or salience can cancel a thought in flight"); hybrid plan "Motor arbitration".

- Under the hybrid plan's one-way rule, voluntary action suppresses the reflex only while it is *executing*. A
  thought in flight suppresses nothing. So time to a protective action is set by the reflex, whether cancellation
  is on or off. H4's primary measure can't tell the arms apart, and the result would be a false null.
- Cancellation has two real jobs in this design:
  - it stops a plan the hazard has overtaken from applying (the stale rate);
  - it frees the single outstanding thought slot (§4.3), so the NPC can re-deliberate with the hazard in context.

**Fix:** H4 measures time to the first **deliberate** response that takes account of the hazard, and how often
an overtaken plan applies, cancellation on against off. Keep time to a protective action as a check that
cancellation doesn't slow the reflex.

### D7. §9 Q1 misstates round-1 finding 5, and v1 drops its core without naming the divergence

**Location:** §9 Q1 ("The bio-faithful reviewer's case for holding was that deliberation is lived time. Under
decision 7 that stays true"); §4.3 (dial-dependent thinking speed); §3.4 presets.

- **Finding 5's case.** It was that apply-on-arrival makes "an NPC's world-time reaction speed a property of the
  host's GPU, its load and the dial. That is the caricature." It cited Maxim's own principle twice
  (`runtime/experience_time.py`: "a slow model must not make the agent forget faster"; `experience_clock_decay.md`:
  decay not "bound to thinking speed").
- **What v1 does.** v1 accepts that thinking speed depends on the host and the dial, as "a real property of a mind
  in a faster or slower world". The second half of that is true. The host-hardware half isn't: no mind thinks
  faster because the player bought a GPU.
- **The presets make it worse.** The "wait" and "sleep" presets fast-forward on purpose (§3.4), so during exactly
  those stretches every NPC gets less deliberation per world second and more abandonment. This is a predictable
  shift in NPC behaviour that the player triggers, and §3.4 doesn't state it.

**Fix:**
- Correct §9 Q1 to say decision 7 overrides finding 5's hardware-independence for live play, and keeps it for
  headless runs (D1).
- Tag live play's dial- and hardware-dependent thinking speed as a named divergence. It's **OPEN**, to be measured
  by H6.
- In §3.4, state what the presets do to NPC deliberation.
- Optional, and it doesn't wait: never apply before `T + d_min(kind)`. Slow motion then can't hand NPCs thinking
  faster than any mind could.

### D8. Several pushback items don't name the decision they argue against

**Location:** §6 items 13, 14 and 17; the draft. CLAUDE.md "Push back on Maxim": "Name the decision you're arguing
against".

- **Item 17** argues against Maxim's **G4** (`docs/plans/grounding.md`, 2026-10-07, quoted in the hybrid plan's
  banner: "this trigger is NOT re-keyed… Whether to re-read the 'second robot body' gate is a question at GL3's
  start"). Name G4 and that venue. The best argument is G4's own precedent: it re-keyed the perception plans from
  body count to capability triggers because "Minecraft satisfies the PERCEPTION abstraction". The game asks for
  the same treatment for the reflex half. Note too that the Microduck arriving meets the physical trigger with no
  re-keying. The re-keying's case therefore has to rest on what only the game offers (exact, replayable latency
  control), not on getting there first.
- **Item 14** asks for sleep forgetting on experience time, which reverses **#1361 Q5** ("don't extend 'no offline
  forgetting' to Hippocampus/ATL now"; `experience_clock_decay.md`, "Stated inconsistency (kept by Q5)"). Round 1
  named it, and v1 dropped the name.
- **Item 13** (a world-time deadline) argues against Maxim's wall-clock staleness defaults:
  `runtime/agent_loop.py::_STALE_PROPOSAL_AGE_S` = 35 s (#1048's cutoff) and `LLMWorker(stale_threshold_s=5.0)`.
  Under the dial, a live Maxim agent drops thoughts by host seconds. Name both, and D13 (a dropped stale proposal
  is rescheduled, never idled), which the game's `thought_failed` should match.
- **Item 18 and the draft:** see D3.

**Fix:** add the decision and its file to each row. This is the shape Maxim's process can accept: the decision,
the evidence and the venue.

### D9. Round-1 finding 4's world half (when NPCs sleep, and where consolidation runs) was dropped

**Location:** §6 item 14 (covers only the Maxim entry point); §3.4 ("sleep" preset); README ("Bio-4 sleep and
consolidation → §6 item 14").

- Round 1 asked for three things: sleep as a world behaviour (a fatigue drive, SCN phase and a rest affordance),
  consolidation off the simulation lane as a thinking-lane job applied at wake, and the Maxim entry point.
- v1 keeps only the entry point. Maxim's sleep can block for seconds (`on_session_end_lightweight`). Run in the
  simulation lane, it stalls every NPC's world, and nothing in v1 rules that out.
- The "sleep" preset is the *player's* fast-forward, and v1 doesn't say whether NPCs sleep during it. A reader can
  take it for NPC sleep.

**Fix:** in §4.3, consolidation is a thinking-lane job with the same apply-at-tick semantics. NPC sleep is a world
behaviour with a Phase 4 rest affordance, and stays **OPEN** in Maxim (two-process S+C coupling;
`CircadianContext.phase` has no producer). Rename the preset, or say it is unrelated to NPC sleep.

### D10. v1 drops every divergence tag, and two round-1 fixes; the README says they were folded

**Location:** whole design (no EARN, ANALOG or OPEN anywhere); README rows for Bio-8 and Bio-11.

- **The tags are gone.** The charter asks for every divergence to be named, "ideally as Maxim's EARN, ANALOG or
  OPEN". Round 1 tagged them: the calendar as zeitgeber (ANALOG), perfect entrainment (ANALOG), the oscillator's
  elapsed time (EARN), the movement/speech split (OPEN), `drift_rate: 0` for world-owned drives (ANALOG),
  consolidation (EARN), and Phase 2 visibility (OPEN). v1 carries none of them. §3.4 states perfect entrainment in
  prose without the tag.
- **Bio-8's fix is missing.** "Calibrate drive rates in world-day terms in `data/`" appears nowhere. §3.4 restates
  the problem and gives no fix.
- **Bio-11's guard is missing.** "A test row that the percept builder reads only `World` state" appears nowhere.
  §3.1 states the rule with no guard, and the README cites §3.1.
- The food and rest affordances are recorded only in the README and the draft, not in `docs/roadmap.md` Phase 4.

**Fix:** tag each divergence where v1 states it. Add the drive-calibration rule to §3.4. Add the percept-source
test to PR 3's or PR 4's test list (a B14 row). Put the relief affordances into roadmap Phase 4.

### D11. The clock inventory still misses Maxim's percept reflexes, and the thought staleness clocks

**Location:** §1 ("drives, DN timers, NAc decay, sleep forgetting, hippocampus de-duplication, percept
timestamps"); §6 items 12 and 15. Round 1 missed this too.

- `embodiment/reflex.py::ReflexRegistry` is Maxim's innate percept-reflex layer. It's wired in
  `simulation/orchestrator.py` for archetype bodies, with `clock=time.monotonic` by default, and its cooldowns,
  habituation decay and sensitization run on that clock. Under the dial, a reflex's cooldown and habituation pass
  in host seconds. It is also the only reflex that reaches NAc, through its pain-only learning path. That makes it
  likely the first "substrate" an NPC on the tile actually has.
- The `LLMWorker` and `agent_loop` staleness clocks (D8) belong in the inventory too.

**Fix:** add both to item 15 (an injected clock), and name `ReflexRegistry` in item 12's live tick as a substrate
component the tick drives. Its clock is injectable already (`ReflexRegistry(clock=...)`), so the Maxim change is
small: the default comes from the live tick.

---

## NIT

### D12. The README says every Bio NIT was taken; two aren't in v1

"SEM sensors sample cells every tick" (round-1 finding 13) is nowhere in v1. Neither is
`salience/movement_detector.py`'s per-frame velocity, which needs per-second normalization at 10 Hz (finding 13).
That belongs in item 11. Add both, or correct the README.

### D13. H7 compares curves from different tasks

H2 runs on fire, food and strikes. H7 runs on the orient task (Reachy, the Microduck). "The same curve, game
against robot" needs one task on both. That means a sound-orienting task in the game, which needs Phase 2's sound
field, or the transfer claim is limited to the curve's shape. State it.

### D14. H5 and H6 are scoped oddly

- **H5** (dialogue with reflexes) runs on a path that has no body today: NPC replies go through
  `AgentPool._generate_llm_response`, which has no DN and no drives (round 1, finding 3). H5 depends on item 12.
  Say so.
- **H6** measures a game artifact, the dial. The Maxim-side question is world-time latency, and H2 covers it. H6
  is better as an Overdrive measurement (B5 or the meters), kept off Maxim's ledger.

### D15. Item 10 and the week of a non-24-hour day

- Item 10 doesn't yet name the brief invariant it touches (`docs/agents/bio-memory.md`, SCN temporal credit) or
  its lint (#1361's M72 allowlist).
- Round 1's "define the week and year of a non-24 h world in world config" (finding 7) is unfolded. That's
  harmless while the day is held at 24 hours.

---

## What I checked and found sound

- **Decision 7's core matches Maxim.** `LLMWorker`'s first design principle is "Main loop NEVER waits on LLM".
  DN runs under the loop on its own thread. The loop allows one pending proposal (`ctrl.pending_proposal`, "LLM
  gate BLOCKED"), the same as §4.3's one outstanding thought per NPC. While a thought is in flight, Maxim's
  LLM-primary agent keeps its DN and the tool it's executing, and nothing else. That matches "the NPC doesn't
  freeze" once "habits" goes (D3).
- **World-time abandonment is better than Maxim's wall-clock staleness,** and correctly routed to Maxim as item 13
  (D8 asks only that it name the defaults).
- **Applying at a tick boundary and logging the tick it applied at** keeps tier 1 replays bit-identical under
  arrival-driven application. Validating against the world at that tick is round-1 5(c), folded correctly. The
  NAc routing is D2's issue, not the validation.
- **Item 10** now names #1361 §(g) as the decision it revisits, covers every `TemporalSignature` producer, drops
  local time, and includes the oscillator's elapsed-time fix (Bio-2, Bio-6). Folded correctly.
- **Items 11 and 12** are retargeted as round 1 asked: DN with BL-2, A3, A4, SF-1, SF-2, an injected clock and RNG;
  a live tick rather than `AgentPool`; proposing on action completion. The per-tick substrate step is gone from
  §2.1.
- **#1361 as a hard prerequisite,** and the experience clock declared in turns with `tick_us` (Bio-1, Bio-9).
  Folded correctly.
- **§3.1's rule that the dial, dilation and deadlines never reach a percept** is right as a rule (D10 asks for its
  guard, D2 for the credit path).
- **§3.4's free dial within caps, presets as host requests capped by the rig, and dilation reported** are faithful.
  Headless cradles are the right way to give NPCs whole days, once D1 defines their thought latency.
- **§3.4's perfect-entrainment statement** is accurate to Maxim's SCN (no intrinsic period). Only the tag is
  missing.
- **The §4.3 meters** (latency in ticks, stale rate, substrate-only fraction, reflex conflicts, abandonment, calls
  per NPC-hour) are the right signals, and they map onto H2's measures.
- **The Exp 64 update paragraph** in §6 carries all five of round-1 finding 12's points.
- **The draft's process framing** is right: an issue, a plan, four-lens review, a pre-registration per
  experiment, game runs off the ledger, and a kill criterion that allows an honest null. Only D3 to D6 need to
  change before it goes to Maxim.
