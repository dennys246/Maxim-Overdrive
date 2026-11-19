# DRAFT for Maxim: a coarse, bodily sense of time (tier B, earned by experiment)

**Status:** a proposal drafted in Maxim Overdrive on 2026-11-16, for Maxim's process: a plan for the mechanisms, each
entering `[engineering]`, plus two experiment drafts. Each experiment needs a four-lens design review and a frozen
pre-registration before any data. Nothing is built, run or claimed. Read against `origin/main` `7084f561`.

- **Overdrive ids:** OD-B8 to OD-B13 (tier B); experiments OD-X1 and OD-X2.
- **Depends on:** the world clock plans (tier A).
- **Evidence base:** Overdrive's time research (`docs/design/research/time/`: neuroscience, the Maxim time audit, the
  engine mapping and a skeptic's brief) and its bio-faithful review (`docs/design/reviews/foundations_v1/bio_faithful.md`).
  Citations marked *from memory* there are re-checked before any value enters a config.

## 1. The idea

People don't perceive time at its true resolution. They have coarse, biased estimates at each scale: about 30 ms
order thresholds, about 100 ms moments, interval error of 10–20% growing with the interval, a circadian clock
entrained by light that drifts without it, and days counted in sleeps. An agent in a world should know time the same
way: from its body and its percepts, never from a clock reading handed to cognition.

## 2. Front gate

| Need | Existing | Relation |
|---|---|---|
| Circadian phase | `time/oscillator.py::OscillatorNetwork`, four scales (circadian, weekly, monthly, annual); `time/scn.py` | **Rides on it.** |
| The oscillator's step | `OscillatorConfig.dt = 1/24`, `integration_steps = 1`, advanced once per **observation** | **Changes it** (§3.1). This is why it is tier B, not A. |
| The bio-roadmap's gate | `bio_faithful_roadmap.md` SCN row: "5 of 6 event types have NO producer … Gate: front-gate question first: does per-event-type phase learning earn its keep"; and "~20k oscillators / entrainment inputs \| ANALOG \| 4 scales is the deliberate scope" | **Argued against, by name** (§4). The ANALOG row is about the oscillators' count and scope; adding a light input revisits it, so a new argument is owed. |
| Number sense | `math/ips.py` Weber machinery (fraction 0.15) | **Candidate reuse** for interval noise. |
| Recency | the hippocampus's access stamps | **Stays machinery.** What cognition sees is a coarse bin (§3.3). |

## 3. The mechanisms (each `[engineering]` until earned)

### 3.1 OD-B8. The oscillator steps by elapsed time, and light entrains it

- `step(dt)` with the elapsed world time since the last update, not a fixed step per observation. Today ten events in
  a minute advance it hours, and a silent day advances it zero.
- A light percept (a world light level at the agent) is the circadian scale's entrainment input, with a free-running
  period a little over 24 h. Without light it drifts.
- Under the host clock this changes robot SCN dynamics too, so it is opt-in per agent until earned. The robot default
  stays the fixed step.

### 3.2 OD-B13. The weekly, monthly and annual scales are cue-driven for embedders

Humans have no biological weekly or monthly clock. Those rhythms are social, learned from cues (a shift roster, a
newsfeed). After tier A they are exact calendar oracles. For embedded agents they are either off (no calendar
declared) or entrained by declared calendar percepts. They are never read from the clock.

### 3.3 OD-B9. Cognition gets coarse time, never a reading

- **An interim readout, now**, for embedders that declare no calendar. Without it, an LLM asked "what time is it?"
  invents a precise answer, which is further from the tenet than a coarse truth:
  - time of day in four to six bins, present only when a light or clock percept is;
  - recency in log bins: just now, minutes, hours, days.
- **Later**, the bins come from the oscillator's estimate (OD-B8) and the interval sense (OD-B10), not from the clock.

### 3.4 OD-B10. An interval sense

Durations estimated with scalar noise (Weber fraction 10–20%; the arousal bias kept as a tunable sign, because the
dopamine evidence points both ways: Soares 2016 against the classic drug studies). Retrospective duration counts
salient events (Roseboom 2019, clips of 1–64 s; extrapolating to hours is a hypothesis, not a finding).

### 3.5 OD-B12. A mental-fatigue drive

- An entropic drive that **rises** in proportion to deliberation load: world time spent deliberating, weighted per kind
  of thought by a control-demand weight from config. Rest and sleep recover it.
- **Not a depleting "reserve".** That is the resource model that failed replication (Hagger 2016: 23 labs,
  N = 2,141, d = 0.04 [−0.07, 0.15]). And "cognitive reserve" is Stern's long-term trait, a different construct.
- **Its effects, both candidates for OD-X2:**
  - a raised cost of starting a thought, so a tired agent deliberates less and leans on the substrate (Wiehler 2022,
    *Curr Biol* 32:3564: high-demand participants shifted to immediate, low-effort choices);
  - a slower, more variable onset with time on task.
- **Separate from physical `stamina`** (`base_humanoid.yaml`), with an optional, marked cross-coupling.
- **The Maxim ask (pushback):** `CouplingSpec` is `{sensor, below, multiplier}`, a threshold step on drift. It can't
  express load-proportional build-up. The additive path is a drive that the thought gate advances by load (an internal
  writer), not `coupled_to`. A naively stepped threshold coupling also breaks step-size invariance unless the source's
  crossing is reconstructed first.

## 4. Decisions this argues against

| Decision | Where | The argument |
|---|---|---|
| "Gate: front-gate question first: does per-event-type phase learning earn its keep (B2 never behaviorally graduated)" | `bio_faithful_roadmap.md`, SCN row | Agreed: this plan doesn't argue for event-type phase learning. It argues that the oscillator's **step** is wrong (one hour per observation), which no experiment needs to show, and that light is the circadian scale's real input. |
| "~20k oscillators / entrainment inputs \| ANALOG \| 4 scales is the deliberate scope" | same file | The four scales stay. Adding one entrainment input (light) to one scale needs "a new argument", and this is it: an agent in a world with a day can't be faithful to the SCN without the SCN's input. |
| "SCN phases … host calendar by design" | `experience_clock_decay.md` §(g) | Tier A swaps the calendar's source; this plan replaces the calendar, for embedded agents, with an entrained estimate. |

## 5. Experiments (drafts; ids are Overdrive's and Maxim may reassign them)

Both run as **Maxim cradles**, never as game runs, and both carry the BF2 floor: "a NEW substrate-path claim earns
only if it beats `tabular_q` and `random`" (`behavioral_graduation_candidates.md`). Without floor arms they could
reach only PARTIAL. Tier names follow Maxim's: `[engineering]` until a row earns `[behavioral]` through
`behavioral_graduation_candidates.md`.

### OD-X1. Does an entrained clock carry the behaviour an exact one does?

- **Arms:**
  - the exact circadian phase (the tier A stand-in);
  - the oscillator stepped by elapsed time and entrained by world light;
  - the same oscillator with the light removed;
  - the floors: `tabular_q` and `random`.
- **Task:** food that appears at a fixed time of day.
- **Prediction:** the entrained arm anticipates as well as the exact arm and beats both floors. In the dark it drifts
  by about (period − 24 h) per day, and it re-entrains when light returns.
- **Kill criterion:** if the entrained arm can't match the exact arm within a pre-registered margin, the exact phase
  stays, marked as a stand-in.

### OD-X2. Does state-dependent timing change what is learned?

- **Arms:**
  - fixed latency;
  - latency and thought cost modulated by mental fatigue, arousal and circadian phase;
  - a shuffled control with the same latencies unlinked from state;
  - the floors.
- **Task:** a timed hazard with rest available.
- **Prediction:** only the state-modulated arm learns to rest before hazards and to act on them when alert.
- **Kill criterion:** if it doesn't beat the shuffled control by a pre-registered effect size, state dependence is
  game feel only.
- **Manipulation checks** (true by construction, so they earn nothing): the latency distributions differ by state,
  and the gate's refractory curve holds.

## 6. What stays out

Sleep as raised arousal thresholds (Overdrive's bio-faithful review BF2-5) is a mechanism of its own, for a later
plan. Speech timing is Overdrive's, and the conversational repertoire is the hybrid line's.
