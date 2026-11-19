# How Maxim represents time: an audit for world-time NPCs (2026-11-16)

Read-only audit of **installed pymaxim 1.3.3**
(`.venv/lib/python3.14/site-packages/maxim/`, 539 `.py` files) and the Maxim repo's plans and decisions
(`/Users/dennyschaedig/Scripts/Maxim`, branch `main`, clean tree, **32 commits behind `origin/main`**. The
newer commits touch bounded-stop, routing, motion and coverage, not time. Version 1.3.3 in `pyproject.toml`).
Every path below is relative to the package root unless it starts with `docs/` (the Maxim repo) or names
Overdrive.

The question: can Maxim NPCs live entirely in world time (pause, a dial up to about 20x), and how far is
Maxim's sense of time from a bio-faithful one? The owner's framing, as refined: neurons are not a literal
clock tick. **A person never perceives time at its true resolution.** What they get is coarse and noisy:
SCN phase, interval timing, the order and recency of events. That is coarser than physical time. So
this audit also asks where Maxim components see **exact** time that a bio-faithful agent would only
**estimate**.

---

## 0. Headlines

1. **Wall clock everywhere.** A grep finds about **880 clock sites in about 215 files** (`time.time()` alone
   is in **173 files**, which matches the boundaries review's correction of lesson 11). That splits into
   about 570 `time.time()`, 108 `monotonic`/`perf_counter`, 98 `sleep`/`wait(timeout)`, 53 calendar reads
   (`datetime.now`, `strftime`), and about 50 that are only docstrings or comments. Another **35
   dataclass fields default to `time.time`** (`field(default_factory=time.time)`), so every record built
   without an explicit stamp reads the host clock.
2. **One world-time seam already exists, and it is the right shape.** `runtime/experience_time.py::ExperienceClockDriver`
   advances `memory/experience_clock.py::ExperienceClock` (integer µs) once per live loop pass. In a
   turn-based world it advances by turns times a quantum, from a percept source's `experience_turns()`
   and `experience_us_per_turn`. Today **only `StrengthStrategy` reads it, and that strategy is not the
   default** (`memory/hippocampus.py:220`: `memory_strategy: str = "access_based"`). Everything else that
   learns, forgets, drifts or habituates runs on wall seconds or on loop-pass counts.
3. **#1361 (`docs/plans/experience_clock_decay.md`) is mostly unbuilt.** Only **S1** has landed: no
   offline NAc decay, which is opt-in and Dormant (`decisions/nac.py:447-468`). S2 to S6 are still strict
   red gates in `tests/unit/test_experience_clock_decay.py` (lines 432, 458, 503, 542, 628, 678 and 715).
   These cover the step-clocked fixtures, NAc `advance_experience(dt_us)`, eligibility and anchors on
   one clock, `Embodiment.advance`, and `decay_all` on time. `Embodiment.advance` does not exist in 1.3.3
   or in the repo's `src/`.
4. **The SCN is a calendar index, not a clock.** It has no intrinsic period, no light input and no
   entrainment. Phase is computed from host local time: `time/temporal_signature.py:62`,
   `datetime.fromtimestamp(ts)`, with daylight saving and 86,400 s hard-coded. Its Kuramoto oscillator
   advances **one hour per observed event**, whatever time actually passed (`time/oscillator.py:193-194`,
   `dt = 1/24` day). It is then pulled back toward the calendar phase. Maxim records this as deliberate:
   "SCN phases, `TemporalSignature` similarity | host calendar by design" (`experience_clock_decay.md`
   §(g)).
5. **The LLM is told the exact host date and time on every tool-aware prompt.** That covers weekday,
   date, and time to the minute, as an `IMPORTANT` section (`agents/prompt_builder.py:231-240`, `:1075-1077`,
   `:1624-1626`, `:2279-2296`). A canned fast path also answers "what time is it" with the exact host
   time (`agents/llm_fallback.py:306-330`). An NPC in Maxim Prime asked the time would give the
   player's real local time.
6. **Nothing models perceived duration with error.** There is no interval-timing model, no scalar
   (Weber) noise on durations, no dopamine or arousal effect on clock speed, and no subjective time.
   The one Weber-Fechner system (`math/ips.py`, `weber_fraction = 0.15`) is the number sense, and it is
   never applied to durations. Every consumer gets exact float seconds or exact µs.
7. **There are bio-flavoured rate limits, but in wall seconds.** Examples: refractory periods (ReactionBus
   0.5 s, PainBus 0.5 s, pain cooldown 0.5 s, reflex cooldowns), habituation (social gaze dwell, reflex
   exposure counts), inhibition of return, energy recharge "per second", and movement-salience decay.
   Each one is tuned in host seconds, and most read `time.time()` directly. Only the ThoughtGate's
   refractory counts loop passes (`refractory_ticks = 2`).

---

## 1. Every way Maxim represents or consumes time

### 1.1 Method and totals

- Pattern: `time.time|monotonic|perf_counter|sleep|time_ns|monotonic_ns|localtime|gmtime|strftime`, with
  the aliases `_time`, `time_mod` and `time_module`. Also `datetime.now|utcnow|today`, `date.today`,
  `asyncio.sleep` and `.wait(timeout`. The scan covers all 539 files.
- Result: **883 lines in 215 files.** The kind split is a heuristic, because lines inside multi-line
  docstrings are counted as code:

| Kind | Count | What it is |
|---|---|---|
| `time.time()` / `time_ns()` | ~572 | absolute epoch stamps (mostly), and wall dt by subtraction |
| `monotonic` / `perf_counter` | ~108 | durations and deadlines (process-relative) |
| `sleep` / `wait(timeout=)` | ~98 | scheduling: loop pacing, polling, motor waits |
| calendar (`datetime.now`, `strftime`, `localtime`) | ~53 | run ids, log stamps, **prompt date/time**, temporal parsing |
| comment/docstring only | ~52 | |

- Not caught by the pattern: 35 `field(default_factory=time.time)` defaults, two injectable `clock=`
  defaults (`embodiment/reflex.py:185, :525`) and one `monotonic=` default (`runtime/experience_time.py:45`).
- Also not caught: 9 `datetime.fromtimestamp` calls, which convert to host local time. The one that
  matters is `time/temporal_signature.py:62`; the rest are log rendering, plus `similarity/signature.py:126`.

### 1.2 Per directory (grep counts)

| Directory | Files | Sites | time.time | mono/perf | sleep/wait | calendar |
|---|---|---|---|---|---|---|
| runtime | 31 | 138 | 90 | 10 | 20 | 4 |
| simulation | 25 | 102 | 67 | 6 | 14 | 10 |
| agents | 15 | 80 | 57 | 7 | 2 | 9 |
| models (LLM backends) | 9 | 59 | 31 | 21 | 4 | 1 |
| embodied_runtime (robot) | 8 | 55 | 24 | 0 | 23 | 3 |
| utils | 13 | 47 | 16 | 22 | 2 | 6 |
| memory | 13 | 45 | 26 | 13 | 2 | 3 |
| default_network | 10 | 32 | 28 | 2 | 2 | 0 |
| hardware | 5 | 27 | 12 | 3 | 12 | 0 |
| attention | 5 | 23 | 23 | 0 | 0 | 0 |
| planning | 4 | 23 | 19 | 0 | 1 | 3 |
| peer | 4 | 21 | 10 | 1 | 9 | 1 |
| bridges | 6 | 20 | 18 | 0 | 0 | 0 |
| tools | 8 | 20 | 15 | 2 | 0 | 0 |
| console | 3 | 19 | 12 | 3 | 0 | 2 |
| embodiment | 9 | 18 | 14 | 2 | 1 | 0 |
| proprioception | 5 | 17 | 16 | 1 | 0 | 0 |
| interactive | 2 | 17 | 14 | 3 | 0 | 0 |
| decisions (NAc) | 5 | 14 | 12 | 0 | 0 | 1 |
| inference | 2 | 14 | 9 | 0 | 2 | 0 |
| everything else (bench, doctor, spatial, energy, comms, hivemind, provenance, salience, integration, math, retrieval, tunnel, mesh, harm, time, reactions, similarity, top level) | 39 | 87 | | | | |

### 1.3 Per subsystem, by meaning

Legend: **dt** = a duration (subtraction, or a monotonic deadline). **abs** = an absolute epoch stamp
that is stored or compared. **cal** = calendar or time of day. **pace** = a sleep or poll that
schedules work.

#### SCN and circadian (`time/`): 2 direct reads, but 19 producers of host-calendar phase

- `time/temporal_signature.py:62` (**cal**): `datetime.fromtimestamp(ts)` gives circadian (seconds of
  day / 86,400), weekly (Monday 00:00 = 0), monthly (`(day-1)/31`) and annual (`(yday-1)/365.25`)
  phase in **host local time**.
- `TemporalSignature.now()` (`:90-94`) reads `time.time()`.
- `time/scn.py:63` (**abs**): `BinEntry.registered_at = _time.time()`.
- 19 call sites build a signature from the wall clock or a wall timestamp. They feed SCN binning, NAc
  temporal anchors and temporal-credit similarity:
  - `decisions/temporal_credit.py:165, :240`
  - `decisions/nac.py:3575`
  - `similarity/encoder.py:312, :402, :1046`
  - `bridges/tool_pain_bridge.py:213, :247`
  - `bridges/escalation_bridge.py:342, :487`
  - `embodiment/body.py:559`
  - `agents/exec_agent.py:780`
  - `agents/statistician_agent.py:405`
  - `integration/memory_hub.py:1266` (falls back to `time.time()` at `:1264`)
  - `memory/concept_extractor.py:307`
  - `retrieval/temporal_signal.py:140`
  - `simulation/introspection.py:216`
- `time/oscillator.py` reads no clock. It has a `dt` parameter (`step(dt)`, `:106`), but `observe()`
  always calls `step()` with the default one hour (`:193-194`). See §3.

#### Drives and homeostasis (`embodiment/`, `energy/`): 18 + 8 sites

- `embodiment/body.py:293-298` (**dt, wall**): `evaluate_failures()` computes
  `drift_dt = time.time() - self._last_poll`, then calls `tick_vital_drift(drift_dt)`.
  - The arithmetic, `embodiment/sem.py:435-451::drift_step(spec, value, dt)`, is pure in `dt`, so it is
    already a clean seam.
  - `_last_poll` is never reset across a pause, and the dt has no cap. The first evaluation after a
    pause drifts through the whole pause. The plan itself records this ("the pause leak").
- The legacy drift for `fatigue`, `strain` and `exhaustion` is `rate * dt` in wall seconds
  (`body.py:670-682`). `EmbodimentConfig.poll_hz = 1.0` and `vital_drift_rate = 0.001`.
- Stamps (**abs**): `body.py:128` (`FailureEvent.timestamp` default), `:502` and `:599` (pain signals),
  and `embodiment/spec.py:825-830`, where `SpecSensor.read` stamps `SensorReading.timestamp=_time.time()`.
- `runtime/loop_gates.py:255-` (`tick_embodiment_drift`) calls `evaluate_failures()` once per live pass
  on llm-primary. On substrate-primary, `propose_via_substrate` ticks the body instead.
- `energy/signal.py:91-113` (**dt, wall**): `EnergyBudget.recharge_rate = 1.0` "energy recovered per
  second", with `last_update` defaulting to `time.time`.
- `energy/tracker.py:114, :129`: rate windows on the wall clock.

#### NAc, dopamine-like credit, DN timers

NAc (`decisions/`, 14 sites):
- `decisions/nac.py:1153-1154, :1307, :1318` (**abs, then dt, wall**). Pending events and outcomes
  match within `temporal_window_seconds = 300.0` wall seconds (`:440`). Stale events are cut at twice
  the window (`:1158`).
- `:3661`: anchor pruning against the same wall window.
- `:4188` and `:4270` (**abs**): `saved_at`, plus offline decay `time.time() - saved_at`. Since S1 this
  is opt-in and Dormant (`offline_wall_decay=False`, `:467`).
- In-session decay is per **pass**, not per time: `reward_bias_decay_tau = 50.0` "ticks" (`:474`), and
  eligibility `x0.9` per pass (`docs/decisions.md:319`). The plan's audit shows why that fails: "Decay ∝
  wall time ∝ LLM latency + host load".
- `:362`: a log "tick" is `int(time.time() - sim_logger._sim_start)`, wall seconds since sim start.
  `runtime/agent_loop.py:2844, :3035` use the same convention.
- `decisions/causal_link.py:229, :347, :447`: `last_observed` (**abs**).
- `decisions/significance.py:239, :245` and `decisions/valence_signal.py:69` (**abs**).
- There is **no dopamine module.** "Dopamine" appears 4 times, all in prose
  (`decisions/nac.py:12`, `integration/memory_hub.py:611`, `inference/segment_vision.py:123`). Nothing
  models tonic or phasic DA, and nothing modulates timing with DA.

Default Network (`default_network/`, 32 sites, all wall):
- `network.py:891-906`: its own ~30 Hz thread (`config.py:219`, `update_hz = 30.0`), paced by
  `perf_counter` and `time.sleep`.
- Idle time: `network.py:279, :552` (`_last_interesting_time`).
- Behaviour cooldowns: `behaviors/base.py:136, :143, :156` (`cooldown_seconds`).
- Inhibition auto-release: `inhibition.py:40-60` (`_inhibit_until = time.time() + duration`).
- Arbiter switching: `arbiter.py:76, :134`.
- Exploration scheduling with global `random.uniform` delays: `gaze_manager.py:214, :227-231`.
- Social habituation, dwell seconds and recovery "per second": `behaviors/social.py:83, :113-118, :333`.
- Idle fixation: `behaviors/idle.py:76-292`. Startle: `behaviors/startle.py:71`.
- The ThoughtGate refractory is **pass-counted** (`runtime/thought_gate.py:43`, `refractory_ticks = 2`),
  and is reset after each deliberation cycle (`agent_loop.py:723, 743, 761, 1392, 3278`).

#### Hippocampus: de-duplication, consolidation, forgetting (`memory/`, 45 sites)

- **De-duplication** (`memory/hippocampus.py:1018-1030`): `obs_hash = hash(text...)` uses builtin
  `hash()`, which is not stable across processes. It is checked against `time.time()` within
  `dedup_window_s = 30.0` wall seconds (`:282`).
- **Capture and access stamps** (**abs**):
  - `hippocampus.py:885, :950, :1219, :1281, :1311, :2456`
  - `memory/types.py:563-564, :592` (`created_at`, `accessed_at` default to `time.time`)
  - `memory/base.py:31` (`datetime.utcnow()`)
- **Experience time** (**dt, world-capable**): `hippocampus.py:857, :1222` stamp `experience_us` from
  `self.experience_clock.now_us()`. `StrengthStrategy` uses `R = exp(-dt/S)` with dt in experience µs
  (`memory/strategies.py:600-645`, `memory/encoding.py:176-185`).
- **Consolidation and forgetting** (**dt, wall**) on the **default** path:
  - `hippocampus_consolidation.py:113, :283, :453, :581` take `now = time.time()`.
  - `AccessBasedStrategy` scores on `now - record.accessed_at` against a 7-day `max_age_without_access`
    (`strategies.py:171-206`). `strategies.py:282` has a 30-day `max_age`.
  - The experience-clock plan records this: "Hippocampus `sleep()` and ATL consolidation on the
    **default** path still forget by `time.time()` against `accessed_at`, so downtime counts there"
    (§(f), kept by owner answer Q5).
- **Sleep is the session end.** `MemoryHub.on_session_end` calls `hippocampus.sleep()`
  (`integration/memory_hub.py:904`). Sim mode skips it (`runtime/bio_integration.py:288`). No
  circadian or sleep-pressure trigger exists.
- `memory_hub.py:678, :1045, :1171`: session duration in wall seconds.
  `percept_trace_buffer.py:35, :68`: monotonic stamps.
- ATL: `memory/atl.py:470, :582, :617, :755` (**abs and dt**).

#### Cerebellum forward model (`embodiment/cerebellum.py`, 2 sites)

- `:155`: `ForwardModel.update` sets `last_observed = time.time()`.
- `:453`: prunes models older than `prune_age_s = 7 days` of wall time (`:213`).
- The model predicts **magnitude only**. It has no timing component ("NOT implemented: … cerebellar
  microcircuitry (Purkinje/climbing-fiber timing)", `:14-18`), and it judges an action by sensors read
  in the same call (Overdrive lesson 6).

#### Sensors, `SensorReading.timestamp`, attention and salience

- `embodiment/sem.py:39-65`: `SensorReading.timestamp: float` is required and unitless by contract.
  In practice it is wall epoch (`spec.py:830`).
- `agents/percept_context.py:101`: percept `timestamp`, "monotonic intra-session, wall cross-session".
- `reactions/types.py:166-167`: a Reaction timestamp, plus a `scn_tag: CircadianContext` that nothing
  produces (only `from_dict`).
- Attention and salience, all **dt, wall**:
  - `attention/attention_network.py:170-431` (focus duration, reachability decay `exp(-t/τ)`, `:244`)
  - `attention/salience_map.py:225-227`, which takes `now = current_time or time.time()`. Note the
    falsy check: a world clock at 0.0 falls through to wall.
  - inhibition-of-return recovery `1 - exp(-t/decay)` (`:350`)
  - `attention/gaze_*` and `scene_context.py`
  - `salience/salience_network.py:222-372`: recency `exp(-t / recency_decay_seconds = 5.0)`
  - `salience/movement_detector.py:101-178`: `exp(-dt/decay_seconds)`

#### Embodied runtime and hardware (robot): 55 + 27 sites

These are mostly **pace**: worker loops `time.sleep(0.005-0.1)` (`embodied_runtime/workers.py:257-320`),
the vision stream (`vision_stream.py:79-186`) and motor waits. This is the legitimate wall-clock edge for
a physical body. It does not apply to game NPCs, except where the same classes are reused.

#### The live loop, substrate and hybrid (`runtime/`, 138 sites)

- `runtime/agent_loop.py:1101, :1119, :3313-3316` (**pace**): `run_agentic_loop(target_hz=30.0)`
  sleeps `target_period - elapsed` each pass.
- `runtime/loop_state.py:256-260` (**dt, wall**): `_substrate_tick_due` proposes when
  `time.time() - ctrl.last_llm_submit_time > llm_submit_interval`, where
  `LoopController.llm_submit_interval = 0.5` (`loop_controller.py:157`).
- `runtime/loop_gates.py:197-201`: `_submitted_recently` keeps the loop awake for 120 wall seconds after
  any LLM submit. `:122, :247` sleep `idle_sleep_s`.
- `runtime/loop_substrate.py:56`: substrate tick `now = time.time()`.
- `runtime/substrate_proposal.py:871`: `request_id=f"substrate-{int(time.time()*1000)}"`, an id from the
  wall clock.
- `runtime/experience_time.py` (**dt, injectable**): see §4.
- `runtime/tick_tracker.py:75-110`, `runtime/gating.py:179-398` (adaptation windows),
  `runtime/preemption.py:194-294` (signal cooldowns) and `runtime/rate_limiter.py`: all wall.
- What Maxim calls the "hybrid runtime" (`docs/plans/deferred/hybrid_substrate_reflex_runtime.md`) is
  the DN's ~30 Hz wall thread running a reflex `Behavior` beside the slow agent loop. It is deferred, and
  its revive trigger is a second **physical** robot body. That trigger is Overdrive's `outstanding.md`
  M76 reference.

#### LLM deliberation (`agents/`, `models/`): 80 + 59 sites

- **Wall timeouts and deadlines**:
  - `agent_loop.py:404-413` (proposal wait)
  - `:1813` (`llm_response_timeout`, 30 s)
  - router and backends, about 21 monotonic sites in `models/language/`
  - `llm_call_registry.py`, which tracks the age of in-flight calls
- **Prompt calendar** (**cal**): see §5.1.
- `agents/autonomy.py:800-809`: "one hour ago" windows on the wall clock.

#### Schedulers and workers

Background and worker scheduling is all wall or monotonic:
- `default_network/background_tasks.py:89-174` (`wait(timeout=5.0)`)
- `runtime/worker_pool.py:392-487` (deadlines, job GC at 300 s)
- `memory/concept_extractor.py:513-574`, `memory/concept_grounder.py:108-200` (TTL cache, review
  cooldown)
- `utils/web_cache.py`

Job ids embed `monotonic_ns()` (`concept_grounder.py:164, :200`, `concept_extractor.py:239`). Session
and run ids come from `time.strftime` (`loop_controller.py:125`, `loop_setup.py:531`,
`agent_loop.py:176`). Maxim's DECISIONS.md G17 records that no deterministic session id exists.

### 1.4 Durations vs timestamps vs calendar, in summary

| Meaning | Where it dominates | World-time impact |
|---|---|---|
| **Wall dt** (subtract two `time.time()` or monotonic reads) | drive drift, NAc windows, dedup, forgetting (default), DN cooldowns and habituation, salience decay, refractories, energy recharge | pause leaks through; the dial does nothing; replays diverge |
| **Pass counts** | NAc decay taus and eligibility, ThoughtGate refractory, the oscillator's one hour per event | rate follows loop polling and LLM latency, not world time |
| **Experience µs** | Hippocampus `experience_us`, `StrengthStrategy` (non-default) | correct, if the world declares turns |
| **Absolute epoch stamps** | about 35 dataclass defaults, every `created_at`/`timestamp`, `saved_at`, ids | non-deterministic; a world epoch would need injecting at construction |
| **Calendar / time of day** | `TemporalSignature` (SCN, anchors, credit similarity), prompt date/time, `retrieval/temporal_signal.py` ("yesterday" parsed against `datetime.now()`, `:101, :199, :233, :298`) | NPCs live on the player's local calendar and time zone |

---

## 2. Internal ticks, rate limits, refractoriness, depletion, adaptation, oscillations, interval timing

| Notion | Present? | Where | How faithful |
|---|---|---|---|
| **Intrinsic tick / pacemaker** | No | The loops are paced by `time.sleep` (`agent_loop` 30 Hz, DN 30 Hz, body 1 Hz poll). The only "tick" is a loop pass. | No neural basis. A pass is a polling artefact, which the plan itself shows: "Polling decides whether a pass happens, not anything the agent lives through". |
| **Refractory periods** | Yes, as rate limits | `reactions/bus.py:35, :81-89` (`DEFAULT_REFRACTORY_S = 0.5` per kind:source, monotonic); `proprioception/pain_bus.py:109-` (per `(entity, failure_mode)`); `proprioception/pain.py:82, :563, :670` (`pain_cooldown_seconds = 0.5`); `embodiment/reflex.py` cooldowns (injectable clock); `runtime/thought_gate.py:43` (2 passes); DN `cooldown_seconds`. | Functional analogue only, a spam guard. The plan's §(g) keeps these on the wall clock on purpose: "motor/IO rate limits; hardware safety". Bio refractoriness is milliseconds and per neuron. These are 0.5 s per signal class. |
| **Depletion / fatigue** | Partly | Entropic drives (`fatigue`, `strain`, `exhaustion` rise at `rate*dt`, `body.py:670-682`; `EntropicDriveSpec`, `sem.py:447-450`); `energy/signal.py::EnergyBudget` (spend and recharge per wall second); the ThoughtGate energy check is an **LLM token budget** (`thought_gate.py:42-44`). | Linear drift with a set point. No vesicle-pool or resource-recovery kinetics. Nothing makes repeated firing slower. Token budget as "energy" is an engineering analogue. |
| **Adaptation / habituation** | Yes, scattered | Social gaze habituation (dwell seconds, recovery per second, `behaviors/social.py:40-118`); reflex habituation by exposure count (`reflex.py:194-195`); inhibition of return (`salience_map.py:350`); salience recency `exp(-t/5 s)`; movement decay; `memory_hub.py:608-612` ("resisting habituation"); `runtime/gating.py` threshold adaptation. | Plausible shapes (exponential recovery, count-based habituation), but each has its own wall-second constant and none shares a clock. Count-based reflex habituation is the only clock-free one. |
| **Oscillations** | One | `time/oscillator.py`: 4 Kuramoto oscillators (circadian, weekly, monthly, annual) with Hebbian coupling. Maxim tags it MECHANISM. No theta, gamma or ultradian rhythms. `bio_faithful_roadmap.md` lists theta coding as "OPEN". | The equations are real, but it is driven per event, not per elapsed time (§3). There are no sub-second rhythms. |
| **Interval timing** | No | `grep` for pacemaker, interval timing or scalar timing: none. NAc's temporal window is a hard 300 s cut, not a timing distribution. | Absent. |
| **Dopamine-modulated clock speed** | No | No DA state, no clock-speed parameter. | Absent. |
| **Subjective / perceived time** | No | `grep` for subjective, perceived duration or time estimate: none. The DN's `duration_jitter` (`config.py:118`) is motor randomness, not perception. | Absent. |
| **Weber scaling** | Yes, for numbers only | `math/ips.py:41` (`weber_fraction = 0.15`), `math/types.py:26` (log magnitude bins). | A ready analogue for scalar timing, but nothing applies it to durations. |

**Perceived duration with error: nothing in Maxim models it.** Every duration a component consumes is the
exact difference of two clock reads. Every phase is the exact calendar value.

---

## 3. How the SCN works

- **What it is.** `time/scn.py` is a set of **binned indices**:
  - 24 hourly, 7 daily, 4 weeks of the month and 12 monthly `BoundedBin`s of memory ids (`:173-198`,
    each capped at 200, evicting by significance).
  - Queries: `query_hour`, `query_day`, `query_intersection`, `query_similar_time`.
  - `get_threshold_adjustment` (`:473-500`) raises thresholds for sparsely populated hours.
  - `get_all_clusters` feeds `Hippocampus.sleep_with_clustering` (`docs/time.md:328`).
  - Bio-mapping, by its own docstring: "FUNCTIONAL… The core is binned temporal indexing for fast
    queries".
- **What it entrains to.** It entrains to **nothing.** The phase comes from `datetime.fromtimestamp` on
  the wall epoch (`temporal_signature.py:57-86`):
  - There is no light sensor and no zeitgeber input. `models/bio_context.py:183-207::TemporalContext`
    declares `zeitgeber_strength`, `oscillator_phase` and `energy`, "A richer backend would use these".
    The SCN accepts it as a parameter (`scn.py:235, :476`), but **no caller ever sets it**.
  - `docs/time.md:402` maps "Zeitgebers (time cues)" to `TemporalSignature`, which means the host
    calendar.
- **Period and phase.**
  - Circadian period is a hard 86,400 s (`:66`). Weekly is 7 days. Monthly is approximated as
    `(day-1)/31`, so it jumps at month ends. Annual is `/365.25`.
  - The oscillator's natural frequencies are fixed at 1, 1/7, 1/30 and 1/365.25 cycles per day
    (`oscillator.py:36-41`). There is no free-running period near 24.2 h and no phase-response curve.
  - `observe(signature)` (`:131-198`) computes the error against the calendar phase, then soft-resets
    toward it with `blend = max(0.1, 1/(1+0.01·count))`. That is a learning-rate pull to the calendar,
    not entrainment by a cue.
  - It then applies the Hebbian coupling update and **one Euler step of `dt = 1/24` day per observation**.
  - Consequence: ten events in one minute advance the oscillator ten hours. A silent day advances it
    zero. Its "prediction" is only meaningful because the next observation snaps it back.
  - It is enabled in `runtime/bio_stack.py:413` ("B2: close SCN→NAc feedback loop"). Per the roadmap,
    5 of its 6 event types have no producer (`docs/plans/deferred/scn_event_producer_gap.md`).
- **Time zones.** It uses host local time implicitly, daylight saving included. There is no tz
  parameter and no UTC.
  - Two machines give one world moment different phases. Overdrive's `realtime_lanes_coop.md` §3.2
    records the same defect.
  - A peer clock-skew path (`register_external`, `:262-297`) is "Dormant since 2026-05-26", and its
    estimator has been deleted.
- **CircadianContext** (`time/circadian.py`) has fields for `phase` ("wake", "rest", "sleep_slow",
  "sleep_rem"), `tick` and `wall_time`, but **no producer constructs one**. It only round-trips through
  `from_dict` on percepts and reactions. There is no sleep/wake state machine. Sleep is the session end.
- **Recorded rationale (it constrains any change):**
  - `experience_clock_decay.md` §"Front-gate": "SCN is rejected (owner decision 1): it bins by host time
    of day and never sees world time."
  - §(g), "What stays wall-clock on purpose": "SCN phases, `TemporalSignature` similarity | host calendar
    by design".
  - `memory_strength_and_forgetting.md` Open question 1: "The SCN bins by time of day, the wrong clock
    for this".
  - `DECISIONS.md` 2026-10-10: the SCN temporal-coupling stub is demoted to `[engineering]`. #1180 is
    parked because the behavioural test "cannot succeed by construction".

---

## 4. Clock-injection seams today, and how hard a full injected clock would be

### 4.1 Seams that exist

| Seam | Where | Injects | Notes |
|---|---|---|---|
| `ExperienceClockDriver(clock, *, percept_source, paused_seconds, monotonic=time.monotonic)` | `runtime/experience_time.py:36-94` | a monotonic callable, **or** a turn-based world via duck-typed `experience_turns() -> int` and `experience_us_per_turn: int` | The model seam. It subtracts pause and caps a pass at 300 s. It is built only inside `run_agentic_loop` (`loop_setup.py:180-196`), not under `AgentPool.run_turn` (Overdrive X4). |
| `ExperienceClock.advance(dt_us)` | `memory/experience_clock.py:52-58` | world µs directly | Reads no clock. Persisted with the Hippocampus. Refuses negative values. Its stall assert is `ExperienceClockStalled`. |
| `drift_step(spec, value, dt)` and `tick_vital_drift(dt)` | `embodiment/sem.py:435`, `body.py:634` | dt | Pure. Only the `evaluate_failures` wrapper reads the wall. |
| `OscillatorNetwork.step(dt)` | `time/oscillator.py:106` | dt in days | Exists, but `observe()` ignores it. |
| `ReflexRegistry(clock=...)`, `build_reflex_registry(clock=...)` | `embodiment/reflex.py:185, :525` | a callable | "provides deterministic clock injection for tests". |
| `current_time=` / `timestamp=` optional parameters | `attention/salience_map.py:216`, `salience/salience_network.py:159, :207`, `reactions/types.py:166` | a float | Falls back to `time.time()`. `salience_map` uses `or`, so 0.0 falls through. |
| `NAc.apply_wall_clock_decay(elapsed_s)` | `decisions/nac.py:4067` | elapsed seconds | Dormant. |

There is no `Clock` protocol, no `World.now()`-style object, and no `step(dt)` on the agent, the DN or the
body. `Embodiment.advance(dt)` and `NAc.advance_experience(dt_us)` are designed in #1361 but not built.

### 4.2 How hard

- **Easy, and planned already (#1361 S2 to S5).** These run on dt that one driver produces: NAc decay
  and windows, body drift, `decay_all`. The designs exist, red gates exist, and the owner has decided
  them. The game declares itself turn-based (`experience_turns()` = tick, `experience_us_per_turn` =
  `tick_us`, `realtime_lanes_coop.md` §3.3), and #1361 delivers the rest. **Caveat:** the driver only
  exists inside `run_agentic_loop`.
- **Moderate (a few hundred sites, mechanical).** About 35 dataclass `default_factory=time.time` fields
  and the many `time.time()` stamps in `memory/`, `decisions/`, `bridges/`, `attention/` and
  `salience/`. The fix is one injected clock object, passed by a required keyword (Overdrive's
  "push invariants into types").
  - Maxim's own **M72** lint is the enforcement it plans: "a lint over `decisions/`, `memory/`,
    `embodiment/body.py`, `agents/memory_agent.py::_apply_decay` and
    `proprioception/focus_learner.py::_apply_decay` that refuses a `time.time`/`time.monotonic` read
    outside an allowlist". This is backlog in `outstanding.md:123`, with no check yet.
- **Hard (architectural).**
  - The DN's own 30 Hz thread (`network.py:891-906`), which needs an externally stepped DN (Overdrive
    upstream item 11).
  - `run_agentic_loop`'s `time.sleep` pacing and the 120 s or 0.5 s wake windows (`loop_gates.py:197-201`,
    `loop_state.py:256-260`), which need an externally stepped live tick (item 12).
  - LLM turns that write state during the call (item 16).
  - Changing `TemporalSignature`'s contract (item 10) fights a recorded "by design" decision and a
    SHAPE-FROZEN dataclass (`temporal_signature.py:41-48`). The four fields can stay, but their
    **source** must change: world time and the world's day length, not `datetime.fromtimestamp`.
- **Out of scope for NPCs.** Backend timeouts, heartbeats, robot motor sleeps. #1361 §(g) correctly
  keeps "watch the process and backend" on the wall clock.

### 4.3 What Maxim's own decisions say (verbatim where binding)

- **One clock policy** (`memory_strength_and_forgetting.md`, Open question 1, resolved 2026-09-21): "the
  experience clock governs everything that strengthens or forgets a memory trace; wall time only at
  named sites where downtime is meant to count".
- **#1361 owner decisions (2026-10-17)**, `experience_clock_decay.md`:
  1. "Anchor in-session NAc decay (and body drift) to the ExperienceClockDriver, not to gate passes or SCN."
  2. "OFFLINE: NO forgetting while the agent is switched off — experience time, not wall clock".
- **#1361 owner answers to its open questions:**
  - Q2: "idle time COUNTS toward decay."
  - Q4: "body drift happens ONLY through `Embodiment.advance(dt)` on the experience clock; `evaluate_failures()` stops drifting, so out-of-loop callers must call `advance()` themselves … No wall-clock fallback."
  - Q6: "the survival world uses world seconds (the ExperienceClockDriver's real-time mode)"
  - Q8: "a fixture 'turn' is step-clocked (1/target_hz)."
- **The recorded audit of what a tick is** (`experience_clock_decay.md` §Motivation): "NAc decay is
  called 'TICK-anchored' in `NACConfig`, but a tick is any `pre_tick_gate` pass that is not idle and
  reaches §8.5. Polling decides whether a pass happens, not anything the agent lives through". And:
  "**Two clocks in one credit computation.**"
- **Tracks on the loop clock** (`DECISIONS.md`, owner decision G3; `thalamic_relay.md`; `outstanding.md`
  M40): "Tracks are **logical channels scheduled on the loop/tick clock**: deterministic,
  lockstep-testable, never OS threads. Real concurrency exists only at hardware edges, which post into
  an inbox the loop drains." The `AfferentEvent` id is "(agent, session id, seq): no uuid, no wall time".
- **Determinism gap, recorded** (`DECISIONS.md` G17): "No deterministic session id exists … Every
  session id today is wall-clock `time.strftime`".
- **Four clocks, recorded** (`thalamic_relay.md` §3.1): "Four clocks are in use. **Wall time** drives the
  loop period, the substrate cadence …, drive drift …, and the PainBus … and ReactionBus refractories.
  **Experience time** … is read only by memory strength today. **Pass count** is the clock of NAc decay
  … **Sequence numbers**". Item 6 of the same document adds: "On turn-based worlds the eligibility anchor
  and the capture time are in different units. **UNVERIFIED** whether this mis-credits anything today."
- **M76** (`outstanding.md:127`): a tripwire for "a second robot body revives the second-body plans",
  which gates the hybrid plan. Overdrive item 17 asks to re-key it to include a simulated body.
- **The superseded SCN anchoring plan** (`deferred/scn_decay_anchoring.md`) wanted NAc decay on an SCN
  clock surface. It was superseded on 2026-10-17 in favour of the experience clock. So Maxim has
  already said no to making the SCN the master clock for decay.

---

## 5. Where Maxim gives a component exact time that a bio-faithful agent would only estimate

### 5.1 The LLM prompt contains the exact host date and time: confirmed

- `agents/prompt_builder.py:1075-1077`: `now = datetime.now()`, `date_str = "%A, %B %d, %Y"`,
  `time_str = "%I:%M %p"`.
- `:231-240::build_datetime_section`: "=== CURRENT DATE/TIME (IMPORTANT) ===", "Today is {date_str}",
  "Current time: {time_str}".
- `:1624-1626`: added to every tool-aware prompt at `SectionPriority.IMPORTANT`. The `LLMWorker` path
  builds its prompts here (`agents/llm_worker.py:408, :1391-1392`).
- `:2279-2296`: the search-synthesis prompt adds "CURRENT DATE: {date_str} at {time_str}".
- `:158`: `build_identity_section` also takes `date_str` and `time_str`.
- `agents/llm_fallback.py:306-330`: the canned answers "The current time is {time_str}." and "Today is
  {date_str}." run **before** the LLM for "what time" or "what day" questions.
- `tools/reachy.py:1005-1010`: the tool text tells the model "The last sound faded {age_s:.0f}s ago".
  That is an exact age, to the second.

The prompt also carries exact sensor values in body state (`embodiment/body.py:788-806`,
`"- {entity}.{sensor}: {val}{unit}"`). That isn't time, but it is the same exactness problem.

### 5.2 Exact timestamps and durations elsewhere

| Consumer | What it gets | A bio-faithful agent would have |
|---|---|---|
| `SensorReading.timestamp` (`sem.py:64`; stamped `spec.py:830`) | exact epoch float on every reading | no timestamp. Perception is "now", plus ordering and a coarse sense of recency |
| Drives (`body.py:295-297`) | exact wall dt | Drives integrate real elapsed world time, which is physics and correct to be exact. The agent's **perception** of how long it has been hungry would be coarse. Maxim doesn't separate the two. |
| NAc credit window (`nac.py:1318`) | exact `delta <= 300.0` s cut | a graded, scalar-noisy eligibility over interval, wider for longer delays |
| Hippocampus dedup (`hippocampus.py:1025-1027`) | exact `< 30.0` s | familiarity that fades. Fine as an engineering guard, but on wall time |
| Hippocampus stamps (`created_at`, `accessed_at`, `experience_us`) | exact floats or µs, and **forgetting uses exact dt** | Exact storage is fine as the substrate's physics. Recall of *when* should be ordinal and log-compressed. Nothing surfaces "when" to the agent coarsely. |
| SCN / `TemporalSignature` | exact calendar phase to the second, from the host | a phase **estimate**: an internal oscillator with a free-running period, entrained by light and routine, with drift and jet lag |
| Temporal parsing (`retrieval/temporal_signal.py:101-298`) | "yesterday" resolved against exact `datetime.now()` | relative to the agent's own day estimate |
| LLM prompt | exact weekday, date and minute (§5.1) | "it's evening, I think", from SCN phase, light, routine and hunger |

**Nothing in Maxim models perceived duration with error** (§2). The closest pieces:
- the Weber number sense in `math/ips.py`;
- the SCN's own `get_threshold_adjustment` (`scn.py:473`), which makes judgements less confident at
  sparsely populated hours, a confidence on time-of-day familiarity, not a time estimate;
- the oscillator's `prediction_error_ema` (`oscillator.py:160-161`), which measures error but never
  feeds it back as uncertainty.

---

## 6. Where the design contradicts a bio-faithful time model

1. **Components read a universal clock directly.** About 880 sites. A brain has no access to physical
   time. Every timing signal is generated internally and is noisy. In Maxim the substrate reads the
   ground truth, and so does the LLM (§5.1).
2. **The SCN is keyed to the host calendar, not to zeitgebers.**
   - It has no free-running period, no light input, no phase response and no jet lag. It can't be
     wrong about the time of day, which a real SCN often is.
   - `TemporalContext.zeitgeber_strength` exists and is never fed.
   - Maxim records "host calendar by design" (#1361 §(g)). That is the decision Overdrive item 10 argues
     against.
   - Bio-faithful replacement: an oscillator with an intrinsic period. It integrates **elapsed world
     time**. It is entrained by a world light percept (and later by routine, food and social cues).
     Its phase is the agent's *estimate* of the time of day.
   - Maxim Prime's day length then becomes a property of the light, not a config the SCN is told. A
     real day-length experiment still needs Maxim's pre-registration (`realtime_lanes_coop.md` §3.4,
     Bio-7).
3. **The oscillator integrates per event, not per elapsed time.** `observe()` always steps one hour
   (`oscillator.py:193-194`). So its free run means nothing, and its "prediction" is reset every
   observation.
4. **Timers are in wall seconds.** This covers refractories, cooldowns, habituation recovery,
   inhibition of return, salience recency, energy recharge, the NAc window, dedup and default forgetting.
   - Under a world dial they don't scale. At 20x, a 0.5 s pain refractory is 10 world seconds.
   - Under pause they keep running: a paused NPC's habituation recovers and its body drifts on resume.
   - Bio timers scale with the organism's own time, which is world time here.
   - #1361 §(g) keeps refractories and cooldowns on the wall clock as "hardware safety". That is right
     for a robot's motors and wrong for an NPC's perception. The game needs those split: physical-edge
     rate limits on the wall, perceptual refractoriness on world time.
5. **Pass counts stand in for time.** NAc taus are in "ticks", which are loop passes, paced by polling and
   LLM latency. A slow model makes the agent forget faster (G2's red gate, line 458).
6. **No interval-timing system and no subjective time.** There's no scalar-noise duration estimate, so
   nothing can make a frightened NPC feel time stretch, or a bored one feel it drag. There's no
   dopamine state, so the "DA speeds the clock" family of effects can't exist. The NAc temporal window
   is a step function, not a timing distribution.
7. **Sleep is a session end, not a circadian state.** Consolidation happens when the operator ends a
   session (`memory_hub.py:904`). There is no sleep pressure (adenosine-like) and no SCN gate on sleep.
   `CircadianContext.phase` is never produced. Overdrive item 14 is the matching ask: consolidation
   without ending the session, with idle replay.
8. **Exact time leaks to cognition.** The prompt states the exact host date and time as IMPORTANT, and
   the fallback answers "what time is it" exactly (§5.1). For a bio-faithful NPC, the time of day in a
   prompt should be the SCN's coarse **estimate**, in world terms ("late evening, I think"), or nothing.
   That needs a Maxim change, because the section is hard-wired into `PromptBuilder`. It should be an
   item next to item 10.
9. **Three or four clocks mix in one computation.** Eligibility is per pass, anchors and windows are on
   wall seconds, and captures are in experience µs (`thalamic_relay.md` item 6, "UNVERIFIED" mis-credit).
   A brain has one body clock with many noisy readouts. Maxim has several exact clocks that disagree.
10. **Non-determinism comes bundled with time.**
    - Builtin `hash()` in hippocampus dedup (`hippocampus.py:1022`) is a direct break of Maxim's own
      CLAUDE.md rule on persisted hashes. It isn't persisted here, but it does vary across processes.
    - 36 `uuid4()` calls and 28 calls on the global `random` module (including `gaze_manager.py:227,
      :296-297`).
    - Ids built from `time.time()` and `monotonic_ns()`.
    - An injected clock is necessary for Overdrive item 15 but not sufficient. The RNG and id source
      have to be injected with it.

### What is *not* a contradiction

- Exact time **inside the substrate's physics** is fine. Drive drift, experience µs and memory strength
  can integrate exact world dt, the same way the body really does metabolise in real time.
- The bio-faithful requirement applies to what the agent **perceives and reports**: percept timestamps,
  the SCN phase, durations it judges, and the prompt.
- That points to a clean split. One injected, exact world clock drives the substrate. A separate,
  modelled **time sense** gives cognition coarse, noisy estimates: SCN phase from entrained light,
  scalar-noise interval estimates, and ordinal recency.

---

## 7. Implications for Overdrive's upstream list (`realtime_lanes_coop.md` §6)

- **#1361 stays the prerequisite** and is about one sixth built (S1 of S0 to S6). S3a, S3b and S4 are
  what stop paused NPCs getting hungry and forgetting.
- **Item 10** should name both halves:
  - world-time phase (no host local time, the world's day length);
  - an oscillator that **integrates elapsed world time** and is **entrained by a light percept**, with
    its phase exposed as an estimate.
  - Against: #1361 §(g) ("host calendar by design") and the SHAPE-FROZEN `TemporalSignature`. The
    evidence comes from §3 above: one hour per event, no zeitgeber input, a never-fed `TemporalContext`.
- **A new candidate item: the prompt's time of day comes from the agent's time sense, not
  `datetime.now()`** (§5.1). It is small in code (`prompt_builder.py:1075-1077, :2279-2281`,
  `llm_fallback.py:306-330`) and large in faithfulness.
- **A new candidate item: a modelled time sense**, meaning interval estimates with scalar noise and
  arousal or reward modulation. It would be `[engineering]` until a pre-registered experiment earns it,
  and it reuses `math/ips.py`'s Weber machinery. This is a 1.5-line research question, not a
  prerequisite.
- **Item 11 (stepped DN) and item 12 (stepped live tick)** are where the wall-second refractories,
  cooldowns and habituation move to world time. The split in §6.4 (hardware rate limits vs perceptual
  refractoriness) should go in that proposal, because #1361 §(g) currently lumps them together.
- **Item 15 (deterministic agents):** add `hippocampus.py:1022` builtin `hash()`, the 35 `default_factory`
  stamps, and `salience_map.py:227`'s `current_time or time.time()` falsy fallback, which turns world
  time 0.0 into wall time.
