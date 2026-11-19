# Maxim response 1: Bio-faithful integration and Determinism/replay lens

**Reviewed:** `response.md` (this folder), against Overdrive's `npcs_and_sem.md` (§0 O4, O11, O12; §1; §3; §4; §5;
§12), `research/speed/individual_differences.md`, `research/time/`, `boundaries.md` §6–§7, and the drafts in
`docs/maxim_upstream/`. Maxim read-only at `origin/main` 7084f561 via `git show`.

**Tags:**
- **AGREE:** the response is right, and I say why.
- **PUSH BACK:** the response is wrong or overstated, and Maxim should hear it.
- **MISSING:** something neither side listed.
- **CHANGE-OURS:** Overdrive's design should change.

**Source marks:**
- *verified*: I checked the abstract or a primary index this session.
- *verified (secondary)*: I checked it only through a secondary summary that cites the work.
- *unverified*: from memory, or not checked.

Maxim code citations were all checked at 7084f561.

## Summary

The response is right about the engineering and about where things live, and better informed about Maxim than
our drafts were. It has three weak spots:

- It frames floor-holding as behavioural with no neural story, when there is one: response planning during the
  other's turn, and the metacognitive feeling-of-knowing signal that drives *uh*, *um* and latency.
- Its AgentTime seam, as worded, would hand cognition the exact world clock, which O4 forbids. Its planted-read
  test proves determinism, not time-blindness.
- Its "paired replays shrink the CIs" claim is true for substrate-only runs and much weaker once an LLM is in the
  loop.

Overdrive has one real problem of its own. Under O11, hardware lateness becomes a pragmatic signal of reluctance
that other agents hear. O12 doesn't cover that, and nothing in our design names it.

---

## 1. Floor-holding (response §3)

### BD-1 AGREE: placement outside `learned_hold_window`, but the two plans must state their seam

`learned_hold_window.md` learns *how long* the action hold lasts. Its waiting cost is "the world's hazard and
reward rate, the backend's action duration, and the observed LLM latency" (line 19). It has no repertoire, so
floor-holding needs a home of its own. Agreed.

But the yield deadline *is* a hold. If a later version learns it through that plan's waiting cost, the waiting cost
needs a social term: the listener's inference of reluctance (BD-4). Without one, a learned hold would happily wait
3 s in conversation, because nothing in hazard or reward charges for it.

**Ask:** the fifth plan says explicitly that the yield deadline is a fixed, pre-registered parameter in v1. It
names `learned_hold_window` v2 as the only place where it may become learned, and only with a social-cost term.

### BD-2 PUSH BACK: §A.1b is the right mechanism but the wrong claim to bind to

The plan rides on §A.1b's net-new machinery: the held slot with a deadline, the submit gate and one replace site
(`hybrid_arbitration.md` lines 74–83). That reuse is correct.

But `hybrid_arbitration.md` itself says the hybrid "only means something in sensor-driven worlds", because in text
sims every turn escalates (§A.1, "Where the hybrid is not degenerate"). Addressed speech is exactly that case:
"Pending addressed text" always escalates. In conversation the arbiter is degenerate, and the margin-scaled *h*
(conflict, 1 − margin, the STN analogy) has nothing to scale.

So the floor-holding plan should:
- reuse the slot mechanics;
- *not* inherit *h*'s conflict scaling or HA-1's arbitration claim;
- have its own prereg on its own outcome (BD-6).

Otherwise a null on floor-holding gets read as evidence about arbitration, or the reverse.

### BD-3 AGREE, with a refinement: choose the filler from the predicted delay, and make the predictor metacognitive

**Clark & Fox Tree 2002** (*verified*; *Cognition* 84:73–111): speakers use *uh* and *um* "to announce that they
are initiating what they expect to be a minor (uh), or major (um), delay". They are words, planned and formulated
like other words. The finding is contested on acoustics: O'Connell & Kowal 2005, "Uh and Um Revisited", *J
Psycholinguist Res* (*verified* only that it exists). Overdrive §4.4 already says so.

**Smith & Clark 1993** (*verified*; *J Mem Lang* 32:25–38) is the stronger anchor, and the response omits it. The
weaker the speaker's feeling of knowing (FOK):
- the slower the answer;
- the *faster* an "I don't know";
- the more *uh* and *um*, hedges and self-talk.

**Brennan & Williams 1995** (*verified (secondary)*, through the Smith & Clark search results) showed that
listeners read FOK from these cues.

So the "latency predictor" is not only a cost-model lookup. In people it is the speaker's metacognitive estimate of
retrieval success.

**Refinement for the plan:**
- Predicted delay = f(kind, a content-class or FOK signal the agent already has), evaluated in modelled world time.
  Recall confidence from the hippocampus, or the NAc margin, are examples of such a signal.
- It must never be the hardware.

That is OD-H2 (agreed by Maxim) plus a bio-faithful input. It also fits our §4.2, where landing may depend on
content class.

### BD-4 MISSING (Overdrive-side BLOCKER-level for O11): under live play, hardware lateness becomes a social signal

The literature says gaps and fillers *carry meaning*:
- **Kendrick & Torreira 2015** (*verified*; *Discourse Processes* 52:255–289): dispreferred responses outnumber
  preferred ones only at transitions of about 700 ms or more.
- **Roberts, Francis & Morgan 2006** (*verified*; *Speech Commun* 48:1079–1093): listeners rate willingness to
  comply lower as silence grows across 0, 600 and 1200 ms.
- **Kohtz & Niebuhr 2017** (*verified (secondary)*, Interspeech): a tolerance threshold near 600 ms.

Under O11 the world keeps real time, and a late thought is covered by fillers and then a yield. A slow GPU therefore
makes every NPC *sound reluctant*, to the player and to listening NPCs, whose models may learn from it.

That is exactly what O12 forbids for speed: "variation belongs to the person … independent of whose machine hosts
the world". O11's guards stop the *speaker* from booking the yield as fatigue, credit or learning. Nothing protects
the *listener* from the speaker's apparent reluctance.

**CHANGE-OURS:**
- O11 gains a named Known gap with a meter: per hardware, the share of turn transitions over 700 ms that came from
  lateness rather than from the modelled gap.
- The filler policy splits:
  - the **first** filler is chosen from the modelled predicted delay: deterministic, trait-scaled (O12),
    hardware-independent;
  - **continuation**, account and yield follow elapsed world time. That part is hardware-dependent in live play,
    logged, and tier 3.
- NPC listeners perceive lateness-caused fillers like any other. They can't tell the difference, and pretending
  they can would be an oracle. So the gap stays a gap, and the levers that close it are §4.5's: start early, a fast
  first word, streaming.
- State in O11 that the honest fix is latency, not a flag.

### BD-5 AGREE: thresholds are parameters, on the listener's clock

- **Stivers et al. 2009** (*verified* in `individual_differences.md`): language means span about 7–469 ms.
- **Jefferson 1989** (*verified* that the chapter exists and what it proposes: "a 'standard maximum' silence of
  approximately one second", in Roger & Bull, eds., pp. 166–196). The metric's details are *unverified*: I could not
  reach the text.

"~1 s" is a reasonable *yield* default. The ~600–700 ms evidence (BD-4) suggests a second, earlier threshold: the
point where the gap starts to read as dispreference. That is where the account (BD-7) belongs.

In Overdrive the listener's clock is world time. For a player at 1× in live play, that equals wall time.

**O12 fit:**
- The **speaker's** trait scales the modelled onset, and so the predicted delay and the first filler.
- It must **not** scale the yield threshold, which is the listener's norm.

`individual_differences.md` already says gaps are mostly dialogue and pair (Cavalcanti & Skantze 2025: pair 41.5%,
speaker 12.8%), so the pair-accommodation term belongs on the threshold, not on the trait.

**MISSING:** disfluency *rate* is its own individual difference.
- **Bortfeld et al. 2001** (*verified* abstract; *Lang Speech* 44:123–147): it rises with planning difficulty (the
  director role, abstract topics), barely with age; men produce more fillers (*verified (secondary)*).
- Proposed for §12.1 item 5: a per-NPC filler-propensity trait from the keyed stream, `[engineering]`, independent
  of the speed trait. The research doc should get a row for it.

### BD-6 AGREE: "no claims" enforced structurally, but the analogy and the listener side need care

- Speaker-side: floor-holding acts carry no proposition, are never stored as utterances, and are never credited.
  Right, and it matches O11's guards.
- **The Exp 63b analogy is fair but not "exactly"** (Maxim `exp63c_scripted_recall_prereg.md`:18;
  `exp63b_carried_recall_prereg.md`:57–60). There the stall template was the *narrator's* filler line, used as a
  recall cue, so template words crowded the cue path. Same mechanism (content-free text competing with content in
  memory), different side of the conversation.
- **PUSH BACK on "never stored" for the listener.** Hesitation is information to the hearer. Smith & Clark, Brennan
  & Williams and Kendrick & Torreira (BD-3, BD-4) all show listeners use it. A listener NPC should store *that the
  speaker hesitated*, as a feature of the speech percept: a duration, a filler-present flag. It should not store the
  filler as an utterance with words.
- **Structural form:** a filler is a `speak`-family act with a closed token set and an empty proposition field, so
  the memory writer can't treat it as content. A test: a turn whose only output is fillers adds zero utterance
  records and zero credit events, and a listener's percept carries the hesitation feature.

### BD-7 AGREE, strongly: give an account before yielding

**Stivers & Robinson 2006** (*verified*; *Lang Soc* 35:367–392): a preference for progressivity. Answers are
preferred over non-answers, and non-answers ("I don't know", "let me think") are themselves preferred over no
response from the selected speaker. Accounts are often offered for non-answers.

Smith & Clark 1993 found fast "I don't know"s under low FOK. So the order is:

1. a filler chosen from the predicted delay;
2. past about 600–700 ms, an account or a word-search display;
3. past about 1 s, a yield.

A **word-search display** is gaze aversion and a "thinking face": **Goodwin & Goodwin 1986**, *Semiotica* 62:51–75
(*verified* the paper; the "thinking face" and gaze specifics are *unverified*).

The account ("let me think", "hang on") is still content-free in the propositional sense, so it fits BD-6's
structural rule. It is a closed-vocabulary act, not LLM text.

**O11 should say "account, then yield", not only "yield".**

### BD-8 PUSH BACK: misplacement marker is the right family, but the example is a different device

**Schegloff & Sacks 1973** (*verified* the paper and its attribution of misplacement markers; *Semiotica* 8:289–327)
describe markers like "by the way". These mark an item *as out of its proper place*. A late answer to a question the
NPC yielded on is better described as a **return to a prior sequence**: "about what you asked", "so, to answer
your question".

The CA literature treats returns as their own practice. One example is the "re-exiting a sequence" practice whose
paper turned up in my search, on conversationanalysis.org (*unverified*). Schegloff 2007, *Sequence Organization*,
is the standard reference (*unverified*).

This is a NIT for the plan's citations. The behaviour (the late answer opens a new turn, marked) is right and
matches O11.

### BD-9 PUSH BACK: "behavioural, not a neural mechanism" dismisses a real neural story

The response says floor-holding "is behavioural (conversation analysis), not a neural mechanism". The *repertoire*
is behavioural, but the *timing architecture* it rides on has direct neural evidence:

- **Bögels, Magyari & Levinson 2015** (*verified*; *Sci Rep* 5:12881): EEG shows production planning starting
  within about 0.5 s of the answer becoming retrievable, up to seconds before the question ends. Areas tied to late
  planning stages light up early, with an attention switch from comprehension to production.
  - Replicated in part: Bögels, Casillas & Levinson 2018 (*verified (secondary)*), and in the wild in Bögels 2020,
    *Cognition* (*verified (secondary)*; the ERP replicated, the alpha decrease less reliably).
- **Castellucci et al. 2022** (*verified*; *Nature* 602:117–122): ECoG finds a speech-planning network, caudal
  inferior frontal (Broca's region) and caudal middle frontal gyrus. It is more active for preparing speech than
  non-speech actions, and the same network appears in unscripted conversation before the participant speaks.
- **Levinson & Torreira 2015** (*verified* in our research doc) and **Indefrey & Levelt 2004** (*unverified* here;
  cited via L&T) give the production-latency arithmetic.

Implications:
- OD-H4 (deliberation that starts during the other's turn) is not just a latency lever. It is the bio-faithful
  default, with a neural mapping: an ANALOG to a frontal planning network gated by predicted retrievability. Maxim
  agreed to fold OD-H4 in, which is good. The plan should carry this table, not "no neural mechanism".
- The FOK signal (BD-3) has its own neural literature: prefrontal metamemory. That is *unverified*, and I cite
  nothing specific.
- The tier: still `[engineering]`, innate prior, earned by a prereg. The bio-mapping column should read ANALOG with
  these citations rather than "none".
- Overdrive's `individual_differences.md` notes that *fast responders show reduced anticipatory processing*
  (Bögels 2018). That is a speed-trait-relevant finding for O12's optional speech-onset domain.

### BD-10 MISSING: barge-in on a filler is outside `sem_interruptibility`'s contract

The response cites `sem_interruptibility.md` "for the rule that fillers can be cut off at any time". That plan:
- defines `interruptible: none | between_steps | anytime`, declared in code on the backend (lines 31–43);
- **scopes itself to "the cancels that come from arbitration, by the LLM or the danger interrupt"** (line 55);
- rules out `anytime` on Reachy "until an MP decision allows it" (line 69).

A partner barging in is neither the LLM nor a danger. Its cancel source is a *social percept*.

**Ask:** the fifth plan defines a third cancel source (a partner's speech onset) for speech-family affordances. The
embedded backend declares filler and account acts `anytime`. Robot speech gets its own MP decision. Our §4.3
(`cancel_on`, rate-limited per source) is the game side of that and is consistent.

---

## 2. Determinism scope (response §4, Part 2 items 1–3)

### BD-11 AGREE: scope to embedded agents, proved by a test, not a count

The recount matches ours within one uuid4 hit, and the ~30 step-path files claim is plausible. "Prove the scope
with a test" is exactly our standard ("prove a guard by deleting what it guards").

Building on `ExperienceClockDriver(clock, monotonic=...)` (`runtime/experience_time.py:36`) is right.

### BD-12 PUSH BACK (BLOCKER for O4): AgentTime as worded hands cognition the exact clock

"Embedded agents get the host's clock" fixes *determinism*, and O4 is violated by construction. The step path
includes the prompt and observation builders:
- `prompt_builder.py:1104` and `:159` render the date and time;
- `context_pool.py:468, :493` stamps observations `[HH:MM:SS]`;
- `temporal_signature.py:66–76` reads `weekday()` and `tm_yday`.

All are cited in our §1. Swap their source from the wall to the world clock and every NPC prompt carries the exact
world time. That is bit-reproducible and exactly what "no time field reaches cognition" forbids. The planted
wall-clock read test passes on that design.

**Ask:** AgentTime is split by type into:
- a **machinery clock**: stamps, decay, cadences and the experience driver, never rendered;
- a **perceived-time port**: the coarse readout, and later OD-B9 and OD-B10, which is the only thing prompt and
  memory-text builders may call.

Make it a type error to format the machinery clock into text: a `MachineInstant` with no `__str__` or `__format__`
that yields digits. The guard set needs, besides the planted read:
- our TZ-13 h prompt test;
- a **planted render**: a prompt builder that formats `agent_time.now()` must go red.

### BD-13 PUSH BACK: `make_agent_rng` is the wrong primitive for Overdrive's keyed streams

`utils/seeding.py:79` returns one sequential `random.Random`, seeded from SHA-256 of `f"{base_seed}:{agent_id}"`.
That has three problems:

- **Sequential.** Every draw depends on how many draws came before. Maxim's DN runs at 30 Hz wall and its cadences
  are wall-gated (our §1), so the count of draws depends on cadence, and percept noise depends on how often Maxim
  pulled a sensor. Our §3.4 keys noise by `(npc, stream, tick, sensor)` exactly to avoid this.
- **One stream per agent.** Adding a draw in attention shifts every later draw in spatial. Our test ("adding a
  stream leaves the others bit-identical") fails.
- **`agent_id` is free text.** The docstring's example is `"agent_0"`, an ordinal. It must be the persisted NPC key.

Also, `seed_all` (the same file, lines 27–64) mutates process-global `random`, `np.random` and `torch`, and sets
`PYTHONHASHSEED` in the environment. An embedded agent must never call it: the host owns the process. The
import-closure test should ban it on the embedded entry point.

**Ask:**
- the item-2 PR adds named substreams (a fixed registry, never `hash()`);
- a keyed draw API `draw(stream, key_tuple)` on a counter-based generator (Philox), which our §8.2 already asks
  for.

`make_agent_rng` can be the robot default.

### BD-14 MISSING: replay breakers the response didn't list

Each item names where it bites.

1. **Wall-gated cadences under a *frozen* fake clock.** "Step the agent under a frozen fake clock" hides every
   cadence bug: `llm_submit_interval` 0.5 s (`loop_controller.py:157`), DN 30 Hz, `ReactionBus` 0.5 s, and the
   stale thresholds of 5, 35, 15, 30 and 60 s. Under a frozen clock nothing elapses, so they never fire or always
   fire. The test needs an *advancing* fake clock scripted by world dt, plus a plant at a cadence site.
2. **Horizons.** The planted read is caught only on paths the test runs. Consolidation, sleep, decay and
   `TemporalCreditDistributor`'s 300 s anchors fire only after long world intervals. So:
   - a long-horizon scripted run (hours of world time, sleep included);
   - **plus a static AST ban** on `time.*` and `datetime.now` in the step-path set, as our sealed set does (§1).
   A dynamic plant alone can't prove absence.
3. **Ids that encode time.** `nac.py:1163` builds event ids from `time.time_ns()`. So the id seam is not only
   uuid4: it also covers `time_ns` ids and anything ULID- or uuid1-like. Ids also must not reach prompts in a form
   that encodes order or time.
4. **Offline decay on load.** `nac.py:4321–4333` applies `apply_wall_clock_decay(time.time() - saved_at)` at file
   load (opt-in). For an embedded agent, world time stops while the game is closed. Loading a save a week later must
   not prune learning. The embedded home must force it off, with a test: same save, load at two fake wall times,
   identical state.
5. **`time.monotonic` across a save.** 145 monotonic reads. Monotonic time restarts per process, so any persisted
   monotonic stamp is meaningless after load. AgentTime must be one clock, persisted with the agent home.
6. **Threads and pools.** The response names the ConceptExtractor thread, the worker pool and the router lock as
   isolation problems, but not as *ordering* problems. Any completion-order-dependent write breaks bit-identity:
   memory appends, NAc updates and JSONL provenance. The planted-read test is single-threaded and proves nothing
   here. It needs either no threads on the step path (OD-EA7) or our agent barrier (§6.3), with a test: the same
   run under two seeded completion-order schedules gives the same digest.
7. **Set and dict order.** `set[str]` iteration order varies with `PYTHONHASHSEED`. Maxim has `stable_hash_*`
   for persisted hashes (`seeding.py:105–130`), but iteration order over string sets is a separate leak. It needs
   our two-process, different-hash-seed test, run on the agent step.
8. **Float nondeterminism in embeddings.** The semantic path (dormant by default, `enable_semantic=False`) and any
   embedding model:
   - torch on MPS or CUDA is nondeterministic unless forced, and BLAS results depend on thread count;
   - near-ties in similarity ranking then flip recall.
   Our replay header already records the BLAS thread count (`boundaries.md` §6.3). Embedding calls should go
   through the response cache like LLM calls, or carry a deterministic-mode guard and a tie-break rule (a stable
   secondary key).
9. **LLM nondeterminism even at temperature 0.** Batch size, thread count and the reduction order flip tokens. One
   llama.cpp report (#22956, *verified (secondary)*) needed `OMP_NUM_THREADS=1`. This is why our tier 2 rides on the
   response cache, not on seeds. Maxim's "same seed per paired trial" (`baseline_floors.md`:139) is not enough for
   bit-identity.
10. **Filesystem order.** `os.listdir` and glob order on load from the agent home. Sort at every read.

### BD-15 CHANGE-OURS: say plainly that the AgentTime seam is tier A and does not satisfy O4 alone

Our §12.2 says "Real Maxim reads the host clock on the live path; closes with tier A". With BD-12, tier A closes
*determinism*. O4 closes only with the perceived-time port and the prompt rows. Split that divergence row in two,
so tier A's landing doesn't silently retire the O4 gate.

---

## 3. Paired replays and admissibility (Part 2, "why these matter"; "two cautions")

### BD-16 AGREE in principle, PUSH BACK on scope: pairing helps substrate claims; with an LLM it decays fast

Common random numbers are a standard variance-reduction technique: same seed, one variable changed. They reduce the
variance of the *difference* when the arms' outcomes are positively correlated.

Maxim already *requires* "the same model, seeds and state keys" for floor comparisons
(`behavioral_graduation_candidates.md`, BF2). `baseline_floors.md`:139 already says "same temperature, top_p, and
seed per paired trial". It also records that Exp 37's harness never passed the seed to the sim. Today's pairing is
nominal, and determinism would make it real. That is the strongest version of their argument, and they didn't use
it.

The limits:
- **Divergence.** Change one variable in an LLM arm and the prompts change. Cache misses force live samples, and
  the trajectories decorrelate from the first differing token: agent loops are effectively chaotic. The gain is
  large for substrate-path claims (BF2's `tabular_q` and `random` floors) and small for LLM-path claims (`bare_llm`
  floors) beyond the first divergence. A prereg should report the **divergence tick** per pair.
- **The estimand changes.** A paired analysis reports d_z, which is d / √(2(1 − r)). An effect-size pass rule
  written for a between-arms d can't be re-read as d_z without inflating it. Every prereg that uses pairing must
  state the estimand and the correlation, and pre-register the paired test. The same goes for a Bayes factor: a
  paired JZS, not an independent-groups one.
- **Pseudoreplication.** Several replays of one seed are not independent units. The unit stays the seed, and n is
  the number of seeds.
- **"BF2 floors" is a floor rule, not a CI.** BF2 (owner decision 2026-10-10) says what to beat, not how to infer
  it. Pairing tightens the comparison against the floor; it doesn't change the rule. The phrase "the confidence
  intervals that BF2 floors depend on" conflates the two.

### BD-17 AGREE: the overfitting caution; MISSING: what makes a game-earned result admissible

Transfer checks before a claim moves are right. That is our OD-HX5, and "game runs never go on Maxim's ledger".

Proposed admissibility conditions, for the candidates doc:
1. **The harness is Maxim's.** A Maxim-owned harness, either a scripted world or an Overdrive world through a Maxim
   simulation bridge (`hybrid_1_5_line_DRAFT.md` open question). The world's build is pinned by hash in the run
   manifest, like the GGUF SHA in Exp 63c.
2. **Pre-registered and frozen on Maxim `main` before data,** with the four-lens review, floor arms, the estimand
   (BD-16), and calibration seeds disjoint from evaluation seeds. HA already requires that, and OD-HX2 is calibration
   only (MP-S9).
3. **Tiered outcome.**
   - *Engineering invariants* earned in the game can enter Maxim as tests against a Maxim-owned scripted fixture.
     Examples: state digest identical under any reply delay (item 5's bar); credit invariant to the dial. They need
     no transfer, because they are properties of the code.
   - *Behavioural claims* earned in the world reach at most PARTIAL (for example "earned in an embedded world; robot
     transfer owed") until the robot or a second Maxim world reproduces them.
4. **Declared world-specific affordances.** Exact time, perfect replay and omniscient instruments are absent on a
   robot. A claim whose mechanism needs one of them is world-only by construction, and says so.
5. **No Overdrive game-feel knobs in the arms.** The pace table and the `abandon` policy stay pinned (our OA1).

---

## 4. Items 9 and 6

### BD-18 AGREE: deliberation by escalation, not a 0.5 s wall interval; three conditions

The biology supports event-triggered deliberative control, not a fixed rate:
- uncertainty or reliability-based arbitration (Daw, Niv & Dayan 2005, *unverified* here; already HA's anchor);
- **Lee, Shimojo & O'Doherty 2014** (*verified*; *Neuron* 81:687–699): control is allocated by the relative
  reliability of the model-based and model-free predictions, encoded in inferior lateral PFC and frontopolar cortex;
- conflict monitoring (Botvinick et al. 2001, *unverified*);
- the expected value of control (Shenhav, Botvinick & Cohen 2013, *unverified*);
- vicarious trial and error at choice points (Redish 2016, *unverified*).

No literature I know posits a fixed-rate deliberation clock. `llm_submit_interval` 0.5 s (`loop_controller.py:157`)
is engineering, and its wall basis is our §1 violation.

**Conditions:**
1. **Not only escalation.** Spontaneous thought arises at rest without a trigger. That is
   `idle_dmn_coordinator.md`'s job, and item 9 must not delete the only path that lets an idle NPC think. Name the
   two triggers (escalation, idle DMN) together.
2. **The rate limit survives, in world time.** The 0.5 s interval also limits cost. Replace it with a world-time
   refractory plus the mental-fatigue cost (our §4.6, OD-B12), which is Shenhav's EVC in Maxim terms.
3. **Item 9 is HA's claim.** §A.1 *is* escalation (margin, novelty, RPE, text). Item 9 is either "arbitrated
   becomes the default" (a claim needing HA-1's evidence) or "llm-primary's cadence moves off the wall" (an
   engineering fix needing none). Split them. OD-HX2 is calibration only and can't earn the claim. OD-H4's "during
   the other's turn" is a candidate escalation reason (`text` fired on streamed input).

### BD-19 AGREE: the dispatch and settle split is bio-faithful, with three conditions

`execute_and_learn` (`tool_dispatch.py:1257`) fuses execution with credit, which matches the response.

In biology, the eligibility trace is laid at action time and the neuromodulator arrives later:
- **Yagishita et al. 2014** (*verified*; *Science* 345:1616): dopamine enlarges striatal spines only 0.3–2 s
  *after* glutamatergic input, gated by cAMP and PKA in distal dendrites.
- Longer delays need other machinery (all *unverified*): synaptic tagging and capture over hours (Frey & Morris
  1997), reverse hippocampal replay at reward (Foster & Wilson 2006), behavioural-timescale plasticity over seconds
  (Bittner et al. 2017), and taste aversion over hours, which is selective by belongingness.

So "dispatch lays the tag; settle applies credit when the outcome is measured" is the right shape.

**Conditions:**
1. **One credit path, not two.** NAc already has eligibility-trace proportional distribution (`nac.py` docstring;
   `TemporalCreditDistributor`, 300 s anchors, `tool_pain_bridge.py:202–230`). HA names these as paths that ignore
   the chooser. Settle must feed the existing distributor, carrying the chooser stamp, not add a parallel credit
   path.
2. **The trace decays on the agent clock.** `nac.py:1162` takes `now = time.time()` for pending events and prunes
   at 2 × `temporal_window_seconds` on the wall. Under dilate, an outcome N ticks later is credited by wall elapsed
   time: hardware-dependent credit. Item 6 therefore depends on item 3, and the suggested order (1–4, then 5 and 6)
   must hold strictly.
3. **The sweep needs interference.** "Sweep N and measure credit accuracy" is trivial with no intervening actions.
   Bio predicts graded decay with delay, plus misattribution to intervening actions, so the sweep must cross N with
   the number of distractor actions. Our O11 guard (a yield never feeds credit) is one of the settle path's
   exclusions and should be a named test there.

This item also matches our OD-A16 (stale refusals and the settle horizon).

---

## Findings index

| Id | Tag | One line |
|---|---|---|
| BD-1 | AGREE | own plan, not `learned_hold_window`; the yield deadline is fixed in v1, learned only with a social cost |
| BD-2 | PUSH BACK | reuse §A.1b's slot, not *h*'s conflict scaling or HA-1's claim; conversation is the degenerate case |
| BD-3 | AGREE + refine | predicted delay from kind plus FOK (Smith & Clark 1993), modelled, never hardware |
| BD-4 | MISSING / CHANGE-OURS | O11 makes slow hardware sound like reluctance to listeners; first filler modelled, continuation tier 3, a meter |
| BD-5 | AGREE + MISSING | trait scales onset, never the yield threshold; add filler-propensity trait (Bortfeld 2001) |
| BD-6 | AGREE / PUSH BACK | no claims speaker-side; listeners store the hesitation as a feature |
| BD-7 | AGREE | filler, then account (around 600–700 ms), then yield (around 1 s); Stivers & Robinson 2006 |
| BD-8 | PUSH BACK (NIT) | a late answer is a return to a prior sequence, not a "by the way" misplacement |
| BD-9 | PUSH BACK | there is a neural story: Bögels 2015, Castellucci 2022; map it as ANALOG |
| BD-10 | MISSING | partner barge-in is not an arbitration cancel; `sem_interruptibility` needs a social cancel source |
| BD-11 | AGREE | embedded scope, a test not a count |
| BD-12 | PUSH BACK (BLOCKER for O4) | AgentTime must split machinery clock from perceived port; planted-render test |
| BD-13 | PUSH BACK | `make_agent_rng` is sequential and single-stream; keyed Philox substreams; ban `seed_all` |
| BD-14 | MISSING | frozen clock hides cadences; horizons; `time_ns` ids; offline decay on load; monotonic across saves; thread order; set order; embedding floats; LLM at T = 0; fs order |
| BD-15 | CHANGE-OURS | split §12.2's host-clock row into determinism (tier A) and O4 (perceived port) |
| BD-16 | AGREE / PUSH BACK | pairing is real for substrate claims; decays after LLM divergence; d_z, seeds as units; BF2 is a floor |
| BD-17 | AGREE + MISSING | admissibility: Maxim harness, frozen prereg, invariants vs behaviour tiers, declared world-only affordances |
| BD-18 | AGREE | escalation (Lee 2014) plus idle DMN plus a world-time refractory; split the claim from the fix |
| BD-19 | AGREE | dispatch tags, settle credits (Yagishita 2014); one credit path; trace on agent clock; interference sweep |

## Sources checked this session

- Clark, H. H., & Fox Tree, J. E. (2002). Using *uh* and *um* in spontaneous speaking. *Cognition*, 84, 73–111.
  *verified* (abstract via full-text mirror).
- Smith, V. L., & Clark, H. H. (1993). On the course of answering questions. *J Mem Lang*, 32, 25–38. *verified*
  (abstract).
- Kendrick, K. H., & Torreira, F. (2015). The timing and construction of preference. *Discourse Processes*, 52,
  255–289. *verified* (abstract).
- Roberts, F., Francis, A. L., & Morgan, M. (2006). *Speech Communication*, 48, 1079–1093. *verified* (abstract).
- Jefferson, G. (1989). Preliminary notes on a possible metric which provides for a 'standard maximum' silence of
  approximately one second in conversation. In Roger & Bull (eds.), 166–196. *verified* (citation and claim; text
  unread).
- Schegloff, E. A., & Sacks, H. (1973). Opening up closings. *Semiotica*, 8, 289–327. *verified* (citation and
  misplacement-marker attribution, secondary).
- Stivers, T., & Robinson, J. D. (2006). A preference for progressivity in interaction. *Lang Soc*, 35, 367–392.
  *verified* (abstract).
- Bögels, S., Magyari, L., & Levinson, S. C. (2015). *Sci Rep*, 5, 12881. *verified* (abstract).
- Castellucci, G. A., et al. (2022). A speech planning network for interactive language use. *Nature*, 602,
  117–122. *verified* (abstract and index).
- Bortfeld, H., et al. (2001). Disfluency rates in conversation. *Lang Speech*, 44, 123–147. *verified* (abstract).
- Goodwin, M. H., & Goodwin, C. (1986). *Semiotica*, 62, 51–75. *verified* (citation only).
- Lee, S. W., Shimojo, S., & O'Doherty, J. P. (2014). *Neuron*, 81, 687–699. *verified* (abstract).
- Yagishita, S., et al. (2014). A critical time window for dopamine actions on the structural plasticity of
  dendritic spines. *Science*, 345, 1616–1620. *verified* (abstract).
- Everything else above is marked *unverified* where it is cited.
