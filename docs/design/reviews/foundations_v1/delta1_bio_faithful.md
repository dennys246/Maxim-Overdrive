# Bio-faithful integration, delta round 1: `npcs_and_sem.md` v2, `boundaries.md` v3 §4.3–§4.4 and §7, the Maxim drafts (18623ce)

- **Lens:** Bio-faithful integration (`docs/code_review.md`), always on for design reviews; it also asks whether the
  game's push-backs to Maxim are fair to Maxim's recorded rationale.
- **Design commit:** 18623ce (`phase1/design-v2`), diffed against 4f7a754.
- **Date:** 2026-11-16.
- **Counts:** 1 BLOCKER, 10 SHOULD-FIX, 7 NIT.
- **Read:** `npcs_and_sem.md` v2 (all), `boundaries.md` v3 §4.3, §4.4, §7; `maxim_upstream/` `hybrid_1_5_line_DRAFT.md`,
  `time_sense_DRAFT.md`, `propose_settle_amendment_DRAFT.md`, the embeddable agent draft (credit and settle rows), the
  world-clock draft (PainBus row); round 1, `reviews/foundations_v1/bio_faithful.md`.
- **Maxim, read-only, `origin/main` 7084f561** (via `git show`): `docs/plans/hybrid_arbitration.md`,
  `learned_hold_window.md`, `sem_interruptibility.md`, `idle_dmn_coordinator.md`, `foreign_advice_layer.md`;
  `src/maxim/runtime/tool_dispatch.py` (the D53 block). Nothing in Maxim was modified.
- **Web checks this round:** Wiehler et al. 2022 (press and HAL record), Giraud & Poeppel 2012, Heldner & Edlund 2010,
  Tassi & Muzet 2000, English speech-rate sources. Each is marked below as verified or from memory.

## Verdict

Round 1 closed well. Every BLOCKER and SHOULD-FIX of mine has a real fold, not a relabel: the reserve is now a
rising fatigue drive tagged `[engineering]`, the conversational timing is a gap with planning during the other's turn,
sleep is gating, instruments are devices, the interim time readout exists, model capability is named, the PainBus
label is fixed, and every push-back I raised is in a draft. The new D53 text is right, and the `CouplingSpec`
push-back in `time_sense_DRAFT.md` §3.5 is stated fairly.

One premise is false, and an owner decision rests on it. **OA3 says the conversational repertoire comes from Maxim's
hybrid line. That line contains no turn-taking repertoire, plans none, and its own text calls addressed-text worlds
its degenerate case** (BLOCKER D1-1). The rest are real but local. Speech timing still lets the dial and the input
device into what NPCs hear. The fatigue load is defined over the wrong window, and the host's pace knob scales it.
The fatigue effect has no home in Maxim's arbiter. Credit ignores HA-O8's per-chooser rule. And my own round-1 fix
for exafference (restrict to declared sensors) doesn't do what I said it would; I correct it in D1-9.

---

## BLOCKER

### D1-1. OA3 rests on a hybrid line that has no conversational repertoire and plans none

**Location:** `npcs_and_sem.md` §0 OA3, §4.2 P0 row ("backchannels, gaze and fillers live here"), §4.4 ("No 'um' on a
stalled model": fillers chosen by P0), §5.1 split table ("Turn-taking … Maxim's substrate, P0"), §5.1 "Overdrive
builds no repertoire of its own"; `hybrid_1_5_line_DRAFT.md` OD-H4.

**What Maxim's plans say (origin/main 7084f561):**
- `hybrid_arbitration.md`, `learned_hold_window.md`, `sem_interruptibility.md`, `idle_dmn_coordinator.md` and
  `foreign_advice_layer.md` don't mention backchannels, turn-taking, conversation, fillers, gaze or nods (a grep of all
  five finds none).
- `hybrid_arbitration.md` §A.1 escalates on "pending addressed text" and says: "In text-percept sims every turn
  escalates, so the hybrid only means something in sensor-driven worlds." A player talking to an NPC is exactly that
  case. The substrate's part in a conversation turn is a NAc tool proposal that dispatches when *h* expires, and no
  proposal in Maxim's vocabulary is a backchannel.
- OD-H4 asks the line only to *start deliberation during the other's turn*. It doesn't ask for the fast repertoire.

**Failure scenario:** Phase 4 lands with the hybrid line shipped as planned. Each NPC turn escalates, the substrate
proposes no conversational act, and in the gap and during the player's turn the NPC does nothing: no gaze shift, no
nod, no *uh* before a long answer (§4.4's filler rule has no producer). §4.4 already records the statue for thoughts in
flight. In conversation the statue becomes the steady state, and the "dynamic conversation in hybrid mode" tenet fails
in its fast half. The owner accepted the M89 coupling (OA3) believing the line would deliver this.

**Fix:**
- Correct §5.1 and OA3's premise in plain words to the owner: the hybrid line provides arbitration, holds and
  interruption, not a turn-taking repertoire. The owner decides again, knowing this. The options are (a) a new
  upstream ask, OD-H5 "a turn-taking substrate" (backchannels and fillers chosen from the modelled gap, gaze to the
  speaker, a turn-end projection cue), proposed to the hybrid line as a candidate with its own pre-registration, or
  (b) a Maxim-side plan outside the line. Building it game-side remains forbidden by the push-back rule, and the doc
  is right to say so.
- Bio basis to bring: Stivers 2009 (answers with a visual component such as a nod come faster), Levinson & Torreira
  2015's two-stage model (early planning, late launch on turn-final cues), and Clark & Fox Tree 2002 for fillers.
- Until it exists, list "no conversational repertoire" under §12.2 as an OPEN divergence beside the statue.

---

## SHOULD-FIX

### D1-2. Player speech: "typed text gives no lead" contradicts server stamping, and live voice would make the dial audible

**Location:** §4.5 lever 1 ("Typed text arrives all at once and gives no lead; streamed voice input does"), §5.2
("speech timing is stamped by the server only"), §5.3.

- If the server stamps a player's `speak` per syllable (§5.2 says client timing is refused, so the server must), a
  typed 15-syllable line lasts about 3 world seconds as the avatar speaks it. Other NPCs hear it over those 3 s, and
  the NPC's LLM, which has the whole text at send, gets those 3 s (÷ dial in wall time) as lead. So typed text does
  give lead. The alternative, a line that lands with zero duration, is unfaithful: a whole utterance heard in one tick.
- **Live voice streamed in wall time is the real hazard.** At 20×, a 3-second spoken sentence spans 60 world seconds,
  so NPCs hear the player speak at about 0.25 syllables per second. At 0.25× it is compressed. That is a percept that
  depends on the dial, which the dial-invisibility test (§3.1) exists to forbid, and §4.5 recommends it as the largest
  lever.
- **Faithfulness constraint either way:** the NPC's thought may *start* with the whole text, but anything it does
  before the utterance ends in world time (a backchannel, a barge-in, a cancel) may depend only on the syllables heard
  so far.

**Fix:** state one rule: every player utterance, typed or voiced, is restamped by the server at the modelled speech
rate in world time (voice through transcription, its own prosody only as a bounded rate hint). Its lead is its world
duration. Pre-end NPC behaviour reads only the heard prefix. Add player speech to the dial-invisibility test's inputs.

### D1-3. The faithful gap is in world time, but the player hears wall time

**Location:** §4.2 P1 row, §4.5 table ("One NPC talking to the player: about 0.33×"), §5.4.

Under dilate an NPC answers 200 ms after the turn in world time, and every NPC conversant hears that. The player is
the other conversant, and hears wall time. With L = 3 s and a typed line, the player waits about 3 s wall, well past
Kendrick & Torreira's ~700 ms, where gaps read as dispreferred (verified in round 1). So the player still hears every
NPC as reluctant, the failure BF2-2 was about, now through the wall. The clock (§5.4) shows the dilation, but it
doesn't change what a pause means to a listener.

**Fix:** say this in §4.5. Add a meter: the wall-time gap distribution on player-facing turns, per model profile, with a
target (for example, a median under ~700 ms wall at 1×) that the levers are measured against. State that the in-world
gap guarantees faithfulness among NPCs and a time course the player can read, not a natural feel for the player.

### D1-4. A floor `D ≥ D_min > 0` on the gap forbids the overlaps real conversation has

**Location:** §4.2 P1 ("from the end of the other speaker's turn, mode ~200 ms with a right-skewed tail"), §4.4 ("the
loader requires `D(kind) ≥ D_min(kind) > 0`").

Transition times are a distribution around zero, not a positive gap. Stivers' mode is 0–200 ms, and Heldner & Edlund
2010 (*J Phonetics* 38:555, verified to exist and to conclude that "turn-taking is generally less precise than is often
claimed"; their overlap share is from memory, a substantial fraction of speaker changes) find many transitions are
overlaps. People launch on a *projected* turn end. A positive floor measured from the turn end cuts the left tail and
makes NPCs uniformly polite and never eager.

**Fix:** keep world_v2 BF-5.1's floor where it belongs, on the thought's duration from its **start** (no zero-latency
thinking), and let the landing relative to the turn end be drawn from a distribution that can go slightly negative,
gated by the projection cue (D1-1). Under the heard-prefix rule (D1-2), an early start can use only what has been
heard.

### D1-5. The fatigue load misses the planning done in overlap, and the host's pace knob scales it

**Location:** §2.3 ("Load is world time spent in P1 and Pn … × the kind's weight"), §4.2 OA1 pace table, §4.6.

- In conversation the work happens **during the other's turn** (§4.2, Levinson & Torreira). P1 is the ~200 ms gap.
  Counting load only over P1 makes conversation nearly free and plans expensive. Worse, a thought that starts early
  (streamed or restamped speech) and one that starts at the end would carry different load for the same work, so the
  input modality would set how tired an NPC gets.
- **The pace table changes biology.** OA1's multipliers scale D, and load is world time × weight, so a player who picks
  "snappy" gets NPCs that tire more slowly, accrue less sleep pressure (the OA5 load term) and, once
  `learned_hold_window` exists, learn a different hold. That is a host setting deciding NPC state, the class of channel
  BF2-8 named. OA1 calls the table a game-feel knob, and it isn't one if it reaches the body.

**Fix:** define load over the thought's whole world-time window, from its start (in overlap or not) to its last
segment, × the kind's weight. Compute it from the **default** cost model, never the scaled one, so the pace table
changes only when segments land. Either that, or record in the log header and the Known gaps that the outcome class is
not promised across pace presets. The first is better.

### D1-6. As specified, the fatigue drive would rise with time awake, not with load, and its recovery has no shape

**Location:** §2.3 ("entropic, `drift_direction: up`, recovered by rest and sleep"), `time_sense_DRAFT.md` §3.5.

An `EntropicDriveSpec` drifts at `drift_rate` per world second and is reset by an action (§2.2's own table). Read
literally, mental fatigue then rises with time awake, which duplicates Process S, and an action resets it, when
recovery is passive and graded. The draft says the thought gate writes it, but it doesn't say `drift_rate` is zero, or
how recovery runs.

**Fix:** state it: `drift_rate = 0` (or a marked baseline); load enters only through the internal writer; recovery is
a closed-form exponential decay toward baseline whose time constant depends on state (awake and resting vs asleep),
from `data/`, tagged `[engineering]`. Then say whether that fits `EntropicDriveSpec` or is part of the OD-B12 ask. It is
Δt-invariant as written, so §2.1's test applies unchanged.

### D1-7. The Wiehler effect ("deliberates less often") has no home in Maxim, and the hybrid line is its natural home

**Location:** §2.3 "What fatigue does", §4.6, `time_sense_DRAFT.md` §3.5 and OD-X2, `hybrid_1_5_line_DRAFT.md`.

Under `aut_mode: arbitrated`, whether a decision goes to the LLM is the arbiter's call (`hybrid_arbitration.md` §A.1:
margin *m*, novelty *n*, surprise *r*, frozen in the prereg as an innate prior). OA1 says the agent's policy picks the
thought's kind. Neither document says who makes a tired NPC deliberate less. If Overdrive's thought gate did it, that
would be the game-side workaround the push-back rule forbids. And `learned_hold_window.md`'s own rule (Keramati et al.
2011: deliberate when the value of information beats the time cost × the reward rate) is where an opportunity-cost
account of fatigue (Kurzban et al. 2013, from memory; and Wiehler's "control becomes more costly") enters naturally:
fatigue raises the cost of deliberating.

**Fix:** add an OD-H item: "fatigue as a modulator of the arbiter's escalation cost", proposed to the hybrid line,
argued against the frozen-innate-prior status of *m*, *n* and *r* only for embedders that declare a fatigue drive, and
tested in OD-X2. Label the mapping from Wiehler's choice task to "fewer escalations" as an ANALOG, since Wiehler
measured economic choices (more immediate, low-effort options; 39 participants; reduced pupil dilation; verified via
the paper's record and press), not deliberation frequency.

### D1-8. Credit at settle ignores HA-O8's per-chooser rule

**Location:** `npcs_and_sem.md` §6.1 ("Credit at settle", "Valence per D53"), §6.4; `boundaries.md` §7.2;
`propose_settle_amendment_DRAFT.md` §3.1.

`hybrid_arbitration.md` HA-O8 (decided): credit is per chooser. `substrate` gets substrate-primary's rule, including the
tool-success floor. `llm` and `substrate_advised` get drive relief only, "without it, advice would reach the
substrate's own values through dispatch credit" (the echo path). An Overdrive receipt carries intent id, kind, effect
and frames, but no chooser. Under the hybrid mode, `settle` would credit an LLM-chosen strike through the same D53 path
as a substrate habit. Overdrive's NPCs would then be the first embedded agents to reopen the echo path HA-O8 closed.

**Fix:** the intent carries the chooser stamp (`substrate | llm | substrate_advised`, Maxim's closed key, M1
provenance), the receipt echoes it, and the amendment says settle credits by the chooser rule. Add a test: an
LLM-chosen applied intent with a positive effect books drive relief only. Say in the amendment that the stamp is
HA-O8's, not a new key.

### D1-9. Correction to my round-1 fix: declared sensors don't separate the action's effect from the world's drift

**Location:** `npcs_and_sem.md` §6.4 ("The sensors used for credit are restricted to those the affordance declares it
affects, so an entity dominated by an ongoing process (a crate in a fire) doesn't train the cerebellum on the world's
drift"), `boundaries.md` §7.2, `propose_settle_amendment_DRAFT.md` §3.1 "Slow effects".

This was my BF2-3 suggestion, and it is wrong as stated. Restriction removes drift on *other* sensors. It does nothing
when the world changes the declared sensor itself: `ignite` declares temperature, and a crate already burning heats up
whether or not the NPC ignites it. The cerebellum then learns "ignite raises temperature by X" where X is mostly the
fire. Biologically a forward model is trained on the prediction error of reafference, and exafference on the same
channel is what efference-copy comparison has to discount.

**Fix:** the receipt's measured effect is the declared sensors' change **minus the change the world would have made
anyway over the same frames**, estimated from the pre-action trend (rate over the frames before the intent ×
dt), with the estimator named in the amendment and tagged `[engineering]`. A counterfactual step of the world without
the intent is exact but costly; offer it as the lab option. Test: igniting a crate that is already burning credits about
zero, while igniting a cold one credits the rise.

### D1-10. OD-H2 asks for more than Maxim needs: the hybrid line already names the clock

**Location:** `hybrid_1_5_line_DRAFT.md` OD-H2; `npcs_and_sem.md` §5.1 "A push-back the plans reveal".

The push-back is right in substance: an embedded agent's hold must not learn from wall latency. But it is unfair by
omission, and it proposes a second mechanism:
- `hybrid_arbitration.md` §A.1b.1 already rules that *h* is "stated in **one named clock per world**: the experience
  clock where the world has one, otherwise the wall clock". The learned hold is *h*'s v2, so its "observed LLM
  latency" naturally falls under the same rule. Citing only `foreign_advice_layer.md` misses Maxim's closest
  precedent.
- Under the dilate policy, latency **observed on the injected experience clock** *is* the modelled latency: the world
  is held until the segment's modelled time, so the experience clock reads D, whatever the wall did. So the fix needs
  no new gateway declaration, only "measured on the world's named clock, never the wall". Under `abandon` it would be
  dial-dependent, and abandon runs are already tier 3.

**Fix:** reframe OD-H2 as "apply §A.1b.1's named-clock rule to the learned hold's latency input", cite §A.1b.1 first,
and offer the gateway's modelled-latency report only as a fallback if Maxim wants the cost before the call (a
prediction rather than a measurement). Say that on a robot nothing changes. Asking for less is the honest version.

### D1-11. Waking has no sleep inertia, so a sleeper in a fire acts at full competence at once

**Location:** §2.4.

Round 1's dorm-fire scenario is now half fixed: *when* an NPC wakes is set by thresholds, not a step rate. But on
waking it has full competence. Sleep inertia is a transitional state of lowered arousal with a performance decrement,
usually under ~30 min without prior sleep loss, worse after waking from slow-wave sleep (Tassi & Muzet 2000, *Sleep
Med Rev*, verified from the abstract; the range runs from 1 min to 4 h). For an NPC woken by an alarm, the first
minutes are exactly when its choices matter.

**Fix:** a sleep-inertia term in `data/`, by the stage woken from: slower and more variable onsets, and deliberation
less likely, decaying in closed form. It uses the same channels as fatigue's effects (D1-7), so OD-X2 can include an
arm. Tag `[engineering]` until earned.

---

## NIT

### D1-12. `dispreferred` can't be a kind chosen before the call

§4.2 lists `dispreferred` among the kinds frozen in the request before the call, and also lets landing depend on the
content class read after it. Whether a reply is a refusal is known only from its content. Drop `dispreferred` from the
kind vocabulary and keep it as a content class that moves the landing (the mechanism §4.2 already has).

### D1-13. Speech-rate numbers disagree, and the syllable's neural basis isn't cited

§4.2 P2 says ~4–6 syllables/s, and §5.3 says syllables are 200–250 ms, which is 4–5/s. Rates also vary by about
2 syllables/s across English dialects (Tanner et al., LabPhon 19, seen in search), so take the rate per NPC from `data/`
with a dialect or speaker term. OA4's choice of the syllable is well founded, and the doc should say why: the speech
envelope's modulation peaks at about 4–7 Hz, and auditory cortex theta tracks it (Giraud & Poeppel 2012, *Nat
Neurosci* 15:511, verified). The syllable is the unit listeners segment, not only a convenient stamp. The rate itself
stays *to verify*.

### D1-14. The interim readout's bins are coarser than a visible clock allows

§3.2's interim readout gives six time-of-day bins "only when a light or clock percept is present". §3.2's own table
says people know the time "to minutes with light or a clock", and §3.1 makes clocks in-world devices. With a clock in
view the NPC should read it (minutes, through B-13), and with light only, bins. Also say that bins taken from exact
world time have sharp edges, which no human sense has. That's acceptable for an ANALOG, but list it.

### D1-15. Model choice per kind, and timeout failures, are hardware channels to fix per profile

§4.5 lever 2 ("a faster model for speech turns than for plans"): state that the model per kind is part of the model
profile, fixed per run, never switched on observed latency or load. §4.4's wall ceiling turns slow hardware into more
`thought_failed`: meter the rate per model profile, and record it in the Known gaps beside "outcome class not promised
across model profiles".

### D1-16. Fatigue and inertia acting on onset need body state in the thought request

The host computes D from the cost model (TB2-S5), but fatigue lives in Maxim's body. For OD-X2's arm (onsets slower and
more variable when tired), the request needs a typed, bounded field of state modulators (fatigue, arousal, circadian
phase) that the host reads and clamps, never free model output. Add it to the request type's reserved fields now, so
the golden fixtures don't need a version bump later.

### D1-17. Sleep is where Maxim's idle-DMN slices belong; offer it

`idle_dmn_coordinator.md` constraint 5 says that idle is rare and the plan must "add rest phases to the world". An
embedded world with real sleep is that rest phase, and replay in slow-wave sleep is the most faithful place for slice
(a). Offer Overdrive's sleep as the venue (an OD-H item). Note that §2.4's 20× sleep preset assumes no compute during
sleep. Budgeted substrate replay is cheap, but it should be metered, and an LLM in that lane (HA-O4, not in the first
build) would change the arithmetic.

### D1-18. The slow-effect fallback rides on a window that is still on pass counts

`propose_settle_amendment_DRAFT.md` §3.1: "Consequences that take seconds stay with NAc's temporal window." That window
today is an exact `delta <= 300.0` s cut with per-pass eligibility (Overdrive's own `maxim_time_audit.md`), on the wall
clock until #1361 lands. Add "after tier A" to the sentence, or the fallback is a wall-clock credit window in an
embedded world.

---

## Round-1 findings: did they close?

| Round 1 | Status at 18623ce |
|---|---|
| BF2-1 cognitive reserve | **Closed** in shape, name and label (§2.3, OD-B12); new issues on the load window, the drive spec and the effect's home (D1-5, D1-6, D1-7) |
| BF2-2 onset vs gap | **Closed** (§4.2, §4.5, OD-H4); new issues on overlaps, player speech and wall gaps (D1-2, D1-3, D1-4) |
| BF2-3 D53 valence | **Closed** (§6.1, boundaries §7.2, amendment §3.2); my exafference fix was wrong (D1-9); the chooser is missing (D1-8) |
| BF2-4 citations | **Closed**, except the speech-rate inconsistency (D1-13) |
| BF2-5 sleep as gating | **Closed**; inertia is missing (D1-11) |
| BF2-6 instruments | **Closed** (§7.1, boundaries §4.4, OD-C8 to be re-checked) |
| BF2-7 interim time sense, calendar oracles | **Closed** (§3.2, OD-B9, OD-B13); bins vs clock (D1-14). Tagged [after A] rather than [now]: honest, since Maxim builds the prompt |
| BF2-8 hardware and competence | **Mostly closed** (model profile named, kind rule and test). Open through the pace table (D1-5) and per-kind models and timeouts (D1-15) |
| BF2-9 O4 vs sleep pressure | **Closed** (OA5, marked load term) |
| BF2-10 to BF2-15 | **Closed** (fillers from the modelled gap, the unsaid remainder as intention, PainBus relabelled in the world-clock draft row 143, windowless entrainment, cue rule as design, the determinism rule amendment listed) |
| Push-backs 1 to 4 | **All drafted**: `CouplingSpec` (time_sense §3.5), the per-modulator valence default (amendment §3.2), calendar scales (OD-B13), the C8 shrink (§7.1) |

## Checked and found faithful

- **D53 as Maxim implements it** (`tool_dispatch.py`): NEUTRAL maps to reward 0.5, the Rescorla-Wagner prior midpoint,
  so a verified nil outcome moves a link's prediction back toward the prior. That is extinction-like, not a skip, so
  `neutral` for "struck the door, nothing happened" is a faithful choice. I had worried it blocked extinction; it
  doesn't.
- **The dilate policy composes with HA's hold.** Under dilate a thought lands exactly at its modelled time, so
  "did the LLM land inside *h*" is a function of D(kind) and *h* on the world clock, the same at every dial. That is
  HA §A.1b.1's named-clock rule, satisfied.
- **Interruption builds on `sem_interruptibility.md`**, not beside it. Declaring speech's interruptibility on the
  backend class in code (never in a spec) and the protective class both fit §4.3. `cancel_on` cancels thoughts, not
  protective actions, which keeps it outside the LLM-can't-cancel-protective rule.
- **The `CouplingSpec` push-back** names the decision, keeps it fair about `extra`, and brings the step-size evidence.
- **The OD-H2 substance** (D1-10 is about framing only), **OD-H3's correction of M76 to G4**, and the experiments' BF2
  floor arms.
- **Fatigue tagged `[engineering]`** with the bio basis written as "consistent with", the reserve and its name gone,
  and Hagger 2016's numbers correct (verified in round 1).
- **Hunger stays uncoupled** (Raichle & Gusnard 2002, from memory, still right).
- **Sleep gating's salient bypass**: Oswald, Taylor & Treisman 1960 (*Brain*, one's own name evokes more K-complexes
  and awakenings) and Portas et al. 2000 (*Neuron*, one's own name processed in sleep) match my memory. I didn't verify
  them on the web this round, so they stay *to verify*.

## Push-backs to Maxim this round reveals

1. **A turn-taking substrate** (D1-1), a new OD-H item. Argued against nothing recorded, since the hybrid line never
   decided it, but against the line's own scoping sentence about text-percept worlds.
2. **Fatigue as the arbiter's escalation cost** (D1-7), argued against *m*, *n* and *r* being frozen innate priors, for
   embedders only.
3. **Sleep as the idle DMN's rest phase** (D1-17): an offer, not a push-back.
4. **OD-H2 narrowed** (D1-10): asking for less, which the push-back rule also requires.

Sources (web, this round): [Wiehler et al. 2022, HAL record](https://hal.sorbonne-universite.fr/hal-04534917);
[ScienceDaily summary](https://sciencedaily.com/releases/2022/08/220811135344.htm);
[Giraud & Poeppel 2012, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC3364513);
[Heldner & Edlund 2010](https://staff.fnwi.uva.nl/r.fernandezrovira/teaching/cosp/cosp2016/docs/HeldnerEdlund2010.pdf);
[Tassi & Muzet 2000](https://www.em-consulte.com/article/588100/sleep-inertia);
[Tanner et al., LabPhon 19](https://labphon.org/sites/default/files/labphon19/Papers/LabPhon19_paper_140.pdf).
