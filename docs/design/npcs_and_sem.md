# NPCs and SEM: time, thought, action and perception (design part 2, v2, 2026-11-16)

**Status:** DRAFT v2, for a delta design review before any code. v1 (4f7a754) went to the seven-lens foundations
review (`docs/design/reviews/foundations_v1/`: 22 BLOCKER, 82 SHOULD-FIX, 51 NIT across this part, `boundaries.md`
and the Maxim drafts). This version folds every BLOCKER and SHOULD-FIX that touches this part, the owner's decision
O6 and the owner's answers OA1–OA5 to v1's five questions (§0). Two fold tables at the end map each finding to where it
landed: one for the foundations review, one for the world_v2 findings that `world_model.md` handed to this part.

Part 2 of three: part 1 is `world_model.md` (the world), part 3 will be `lab_and_core_loop.md`. This part carries the
detail `boundaries.md` defers. Where it changes a boundaries interface, boundaries is changed in the same fold and
this part says so; it never quietly extends one (Arch S7).

**What changed from v1, in short:**
- **Mode (a) is gone (O6).** v1 had Maxim's tool loop block in `execute` for a world-time receipt. Every lens found
  a face of one root cause: the designs assumed the host drives Maxim's agent, and Maxim owns its loop (its LLM
  calls, tool roster, storage and threads). The replacement is a host-driven **embeddable agent contract** (§6).
  Phase 1 has no NPCs, so nothing is lost now; Phase 4's NPCs wait for Maxim to ship it.
- **The cognitive reserve is gone.** It was a depletion-tank model under a borrowed name. Thought cost now feeds a
  **mental-fatigue drive that rises with load** (§2.3, §4.6).
- **Reply timing is modelled as the gap between turns** (about 200 ms), not as production latency, and planning
  starts during the other speaker's turn (§4.2, §5).
- **The latency truth:** while a thought is pending, the world runs no faster than onset ÷ wall latency. v1's
  throughput table was too optimistic, by about 3× for a conversation (§4.5).
- **Thoughts have budgets and authority rules,** and a hung model can no longer freeze the world (§4.7).
- **Tags are honest:** anything that needs Maxim's tier A says so, with a strict red gate against real Maxim now and
  only the stub variant green (Arch S9, X-2).

**Sources:** `research/time/` (neuroscience, the Maxim time audit, the engine mapping, the skeptic);
`research/signals/`; `docs/maxim_upstream/` (the world-clock and SEM drafts); roadmap Phase 3; the foundations,
boundaries, world_v2 and real-time reviews; the lessons doc (`docs/lessons_maxim_in_games.md` on `phase1/standards`);
Maxim's `origin/main` at 7084f561 (fetched 2026-11-16), read with `git show`, never from its stale working tree
(MP-S14).

**Numbers:** each names its source. *Verified* means a reviewer checked it against the primary source; *to verify*
means recalled from memory, to be checked before it enters `data/`.

**Tags, by when a mechanism lands:**
- **[now]:** a foundation built in Overdrive's Phase 1 PRs, tested against the scripted test-double agent (§6.2);
- **[after A]:** needs Maxim's tier A (the world-clock release and the embeddable agent contract); until then, a
  strict red gate against real Maxim where there is code;
- **[earned]:** built only if a pre-registered experiment earns it (§10);
- **[Phase 4]:** lands with the first NPC bodies.

## 0. Decisions this part rests on

| # | Decision (owner, 2026-11-16) | Where |
|---|---|---|
| O3 | The substrate runs outside the sealed core behind `AgentPort` (as refined by O6) | §1, §6 |
| O4 | Three clocks; no time field reaches cognition; thought cost is modelled and phased in world time; late thoughts dilate the world; it couples to fatigue and sleep pressure, not hunger | §1–§5 |
| O5 | Refining SEM is in scope and a priority, through Maxim's process; additive first | §8 |
| **O6** | **Mode (a) is dropped.** Replaced by a host-driven embeddable agent contract: the host calls `agent.step(world_dt, frame)`, and the agent returns intents, memory writes and thought requests as values, never applying anything or running on its own. A host-supplied LLM gateway with streaming and cancellation; a closed NPC tool roster checked at build; a per-agent home under the save, never `~/.maxim`, with no pickle on the load path; no host time in prompts or observations; the cerebellum observes at settle; `outcome_valence` set per D53. Phase 1 has no NPCs; Phase 4's NPCs wait on Maxim shipping this. This supersedes O2's "(a) then (b)": the end state is reached directly. | §6 |
| OA1 | A thought's kind is chosen by the agent's policy, from a closed vocabulary, before the call. A host-only settings table may override its modelled cost (per-kind multipliers, or a pace preset); the table is logged, and experiments always run on fixed defaults. | §4.2 |
| OA2 | The player sees dilation on a three-handed analogue clock (§5.4). | §5.4 |
| OA3 | Overdrive builds no conversational repertoire of its own: interfaces only in Phase 1; the repertoire comes from Maxim's hybrid line. | §5 |
| OA4 | Speech is stamped per syllable. | §5.3 |
| OA5 | One mental-fatigue drive that rises with load, with per-kind load weights; it recovers with rest and sleep, feeds sleep pressure, and is separate from stamina. | §2.3, §4.6 |
| — | The thought-cost unit is as fine as is realistic and useful, so conversation can be dynamic in hybrid mode | §4, §5, §9 |
| — | Lay the foundations now, and test against Maxim as each tier lands | throughout |

## 1. Three clocks, and who owns them

| Clock | What it is | Owner | Exact? | Reaches cognition? |
|---|---|---|---|---|
| **World time** | the integer tick × `tick_us` | `Simulation` | exact | never |
| **Body time** | drive drift, fatigue, sleep pressure, reflex latency | the agent substrate, fed the true world `dt` by `AgentPort.step` | exact | never as a number; only through what the body feels |
| **Perceived time** | durations, order and time of day as the NPC believes them | modelled time senses (§3) | coarse, biased, noisy | yes, as estimates |

Inside the game the universal time is the world tick. The wall clock belongs to the machine running the universe,
and no NPC may sense it, or the dial (skeptic.md §1, engine_mapping.md §1). Body time is exact because physics
doesn't estimate. Only perception is coarse.

**Where wall time remains (host only):**
- the pacing loop that turns the dial into ticks per wall second;
- measuring dilation (§4.5);
- the LLM gateway's wall timeouts. **Under the dilate policy a timeout retries, and past a host ceiling the thought
  ends as a logged `thought_failed`** (§4.4). A timeout never silently "frees a worker" and never fails a thought on
  its own (BF2-8, TB2-B3);
- network timeouts, meters, log flushing.

None of these values crosses `AgentPort` **[now]**. The agent step path (`engine.adapters.agents` minus one named
host-only module for timeouts) is a second sealed set under the core's banned list and AST scan, and the tripwire
runs on the agent lane's thread too (DR-S10, `boundaries.md` §3).

**Today's violation, for the record** (maxim_time_audit.md; counts settled by the Executor on `main`, X-3):
- about 880 host-clock reads in about 215 files; 36 `uuid4` calls, 27 global-`random` calls and 36
  `default_factory=time.time` stamps in 19 files;
- substrate cadences on the wall: `llm_submit_interval` 0.5 s, the Default Network at 30 Hz, the `ReactionBus`
  refractory 0.5 s; and wall-clock staleness that drops thoughts whatever the world says: `LLMWorker(stale_threshold_s
  =5.0)`, `_STALE_PROPOSAL_AGE_S = 35.0`, the orchestrator's 15, 30 and 60 s (world_v2 BF-5.4);
- the prompt carries the exact host date and time (`prompt_builder.py:1104`, and `:159`'s identity section), and
  `context_pool.py:468, :493` stamps every recent observation `[HH:MM:SS]` in host local time, which reaches the
  planning prompt (`agent_loop.py:2979`) (X-2).

The hippocampus de-duplication's builtin `hash()` is **not** a determinism break: the dict is in memory, never
persisted, and read in insertion order. Its 30 s **wall** window is the break (X-4).

Every real-Maxim run is an OPEN divergence until tier A (§12.2).

## 2. The body: substrate in world time

### 2.1 Every process is Δt-invariant **[now for Overdrive's side; after A for Maxim's]**

- **Rule:** every body process advances by closed-form updates in world `dt`: decay is `x *= exp(-k·dt)`, never
  `x -= k·x·dt`; linear drift is `x += r·dt`, clamped. This is the agent's version of the resolution rule
  (neuroscience.md §8.2).
- **Δt invariance keeps the outcome class; fixed schedules keep the bits (DR-S1).** `dt_ticks` passed to
  `AgentPort.step` is a pure function of the actor's rate divisor and phase, never of lag. A host that catches up by
  passing a larger `dt` keeps the outcome class and loses bit identity, so it never does.
- **Threshold crossings are scheduled, not sampled (DR-S1).** At each step the process computes its next crossing in
  closed form and schedules a wake-up at that tick. Anything that changes its rates (an intent, a percept)
  reschedules. The crossing time is floored once to integer microseconds from the step-start state, never carried as
  a float. This is part 1's "reconstruct, decide at the point, integrate" applied to the body.
- **Discrete percept events accumulate** as an event list since the last step, so a coarse-rate process never misses a
  flash that lived one tick (DR-S1).
- **The step-size invariance test:** each process over one world hour at step sizes of 1, 2, 5, 10 and 50 ticks.
  - Continuous state agrees within a **relative 1e-9** (closed form measured 1.25e-12; Euler 6.8e-4; X-11).
  - Discrete events land on the same tick, gated with an outcome margin as CLAUDE.md requires of binary outcomes.
  - The planted Euler update goes in an **exponential** process with `k·dt_max` ≥ 1e-3; in a linear process Euler is
    exact and the plant can't go red (X-11).
  - Maxim's half has no owner in tier A yet: no exit test there varies the world step size. That is a new upstream
    ask (§8.2).
- **Coupled drives** integrate the source's crossing in closed form before the coupled drive's step; a naive
  per-step multiplier fails the test at 50-tick steps (BF2-1).
- **Multi-rate is allowed; thinning is not.** A process may run at an integer divisor of the tick with a per-actor
  phase. When the host can't keep up, the world dilates; it never lowers an NPC's substrate rate to keep pace.

### 2.2 Drives: homeostatic and entropic

Maxim has the split in `embodiment/sem.py`:

| Spec | Behaviour | Examples | Relief |
|---|---|---|---|
| `HomeostaticDriveSpec` | pulled back toward `set_point` at `drift_rate` | temperature, pressure | the body, once the force is removed |
| `EntropicDriveSpec` | drifts away at `drift_rate`; only an action resets it | hunger, thirst, stamina | eating, drinking, resting |

- **`drift_rate` means per world second.** Today it reads host elapsed time with no reset across a pause and no cap
  (`body.py:293-298`), so a paused NPC gets hungry. The additive path is OD-C1 (#1361 S4 already routes drift
  through `Embodiment.advance(dt)`), plus a docstring and test stating the unit. A rename to carry the unit follows
  Maxim's alias-plus-`DeprecationWarning` precedent (MP-B3), not a breaking batch. **[after A]**
- **Overdrive never models a drive twice.** A drive the world simulates (skin temperature from part 1's heat field)
  is world-owned and pushed through `world_set_axis` (§7.2). A Maxim `self_effect` applies only to drives the world
  doesn't simulate, each listed as an ANALOG divergence.

### 2.3 Mental fatigue, stamina and sleep pressure (OA5; BF2-1, BF2-9)

- **Mental fatigue is a drive that rises with deliberation load** (entropic, `drift_direction: up`), recovered by rest
  and sleep. It is `[engineering]`: *consistent with* accumulation accounts of cognitive fatigue (Wiehler et al. 2022,
  *verified*: about 40 people, 6.25 h of work, lateral-PFC glutamate up; opportunity-cost accounts, Kurzban et al.
  2013, *to verify*), not a measured biological variable.
- **Per-kind load weights** live in `data/agents/fatigue.yaml`, tagged `[engineering]`: effortful control (planning,
  holding back, careful recall) weighs more than a familiar reply. Load is world time spent in P1 and Pn (§4.2) ×
  the kind's weight.
- **There is no reserve that drains.** That is the strength (resource) model of self-control, which failed
  replication (Hagger et al. 2016, *verified*: 23 labs, N = 2,141, d = 0.04 [−0.07, 0.15]; Vohs et al. 2021, *to
  verify*). The name "cognitive reserve" is also taken (Stern 2002: a long-term trait), so it is dropped.
- **Stamina stays a separate drive** (`base_humanoid.yaml` declares `stamina`, physical, relieved by `rest`; Maxim has
  no `fatigue` drive today). An optional, marked cross-coupling may join them later (Marcora et al. 2009, *to
  verify*: mental fatigue cut time to exhaustion).
- **Sleep pressure** follows Process S: it rises with time awake (τ ≈ 18.2 h) and clears in sleep (τ ≈ 4.2 h) (Daan,
  Beersma & Borbély 1984, *verified* by the reviewer). Mental fatigue **feeds it through a small, marked
  `[engineering]` load term** (OA5, O4), on use-dependent sleep evidence (Huber et al. 2004; Porkka-Heiskanen et al.
  1997; both *to verify*). This resolves v1's mismatch between O4 and its mechanism (BF2-9).
- **What fatigue does** (both candidates for OD-X2, §10): the NPC **deliberates less often** and picks cheaper,
  more immediate options, handing more to the substrate (the Wiehler effect); and its onsets get **slower and more
  variable** with time on task (vigilance decrement; Boksem et al. 2005, *to verify*).
- **Maxim can't express this additively through `coupled_to`.** `CouplingSpec` is `{sensor, below, multiplier}`, a
  step on drift, and load-driven accumulation is graded. The additive path is a drive advanced by an internal writer
  (the thought gate), as `world_set_axis` is for the world. Graded coupling is a new upstream ask (§8.2). **[after A;
  effects earned by OD-X2]**

### 2.4 Sleep is gating, not a slower substrate (BF2-5)

- A sleeping brain gates sensory input and raises arousal thresholds, while salient stimuli still get through (one's
  own name, a cry; Oswald et al. 1960 and Portas et al. 2000, *to verify*).
- **Model:** per-channel arousal thresholds by sleep stage in `data/`, a salient-stimulus bypass, and the wake path's
  detection at the full rate. Drive drift during sleep may step rarely, since it is closed-form.
- A sleeping NPC doesn't deliberate, so the "sleep" fast-forward preset still scales. That is a **performance
  property, labelled `[engineering]`**, not biology. How fast an NPC wakes in a fire is set by thresholds, never by a
  step rate chosen for speed.

## 3. Perceived time: coarse, by scale

### 3.1 The rule, and its tests

**No time field reaches cognition.** Agent-facing percepts, receipts, memory text and prompts carry no tick, receipt
or deliver time, deadline, dial, dilation, host date, host time zone or wall time. A receipt is matched by an opaque
id, and a delay is felt only by when the receipt arrives.

- **Who enforces it.** The adapter strips what *it* builds **[now]**. Maxim builds the prompt, so the adapter can't
  strip the prompt: that waits for tier A's prompt-time and `context_pool` rows, and for Overdrive declaring **no
  calendar** to Maxim (BF2-7, X-2). **[after A]**
- **`SensorReading.timestamp` is body machinery,** stamped from the injected clock (OD-C2), never rendered into a
  prompt verbatim. It is the schema test's one named exemption (X-12).
- **In-world clocks are percepts, not oracles.** A wall clock, a phone, a newsfeed or the sky is an object in the
  world, perceived through B-13's channels (§7).
- **The tests (X-12, DR-S6):**
  - **Schema test:** no agent-facing field is named as a time (a name rule), with the exemption list in the test; plus
    a **value-level** check on every metadata key the membrane emits, since a free dict can hide `apply_tick`.
  - **Prompt test:** render the same prompt in two processes with `TZ` set 13 h apart (`time.tzset()`), and assert
    byte-identical output; and no host path, file name, user or host name appears (TB2-B1). Regex for clock strings
    misses `%I:%M %p` and `[HH:MM:SS]`.
  - **Dial-invisibility test:** the test double driven through the LLM gateway (§6.1) with a seeded **wall-delay
    schedule** that makes some segments early and some late at each dial, a threaded host as shipped, and an
    injected fake wall clock (no sleeps). Percepts, receipts and kinds must be bit-identical at 1× and 20×.
    - **Negative control:** the same run under `latency_policy: abandon` must differ between dials.
    - **Plant:** `if dial > 10: skip hold` must go red.
  - **Against real Maxim:** the prompt and dial-invisibility tests run as `xfail(strict=True)` red gates until tier A
    ships the prompt-time, `context_pool`, calendar and stepping rows. Only the test-double variants are green
    **[now]**.

### 3.2 The senses, scale by scale

Numbers from neuroscience.md §3 and §8.4; "approx." there is *to verify* here.

| Scale | What the NPC perceives | Mechanism | Lands |
|---|---|---|---|
| under ~10 ms | nothing as time; fine timing arrives as a feature (sound direction) | the world converts it before the percept | [Phase 4], with sound |
| ~10–40 ms | events within ~30 ms are simultaneous, order unknown (central order threshold ~20–40 ms) | an order-threshold window on event percepts | [earned] |
| ~40–100 ms | one perceptual moment: events within ~100 ms bind | the integration window | [earned] |
| 0.1–3 s | a "now"; reaction 150–250 ms simple, 300–600 ms choice | P0 reaction latency (§4.2) | [now] as data; [earned] as state-dependent |
| seconds to minutes | prospective intervals with scalar noise, CV ~0.1–0.2, biased by arousal (sign a tunable) | an interval sense; Maxim's Weber machinery (`math/ips.py`, 0.15) may be reused | [earned], OD-X2 |
| minutes to hours | retrospective duration from the density of salient events, tens of % off and content-biased (Ornstein 1969; Block & Zakay 1997, *to verify*) | counting salient changes, **extrapolated upward** from Roseboom et al. 2019, whose clips were 1–64 s (*verified*, BF2-4) | [earned] |
| time of day | to minutes with light or a clock; without them the SCN drifts ~11 min/day (period 24.18 h, SD 0.15 h; Czeisler 1999) | an SCN oscillator entrained by world light (§3.3) | [earned], OD-X1 |
| days | a count of sleeps; in isolation off by days to weeks (Siffre) | a sleep counter feeding the date belief | [earned] |

**Until the senses are earned, a coarse interim readout, not nothing (BF2-7).** Without it an NPC has no time sense
at all, and an LLM asked "what time is it?" invents a precise answer, which is further from the owner's tenet than a
coarse bin. **[after A, `[engineering]` ANALOG]:**
- time of day in six bins, only when a light or clock percept is present;
- recency in log bins (just now, minutes, hours, days);
- listed in §12.2 and replaced by the earned estimators.

**Calendar oracles to close:** besides the SCN phase, Maxim's oscillator network has weekly, monthly and annual
scales (`docs/time.md`), and `TemporalSignature` takes them from `weekday()`, `day` and `tm_yday`
(`temporal_signature.py:66-76`). Humans have no biological clock behind those; they are social calendars learned from
cues. Overdrive declares them off (no calendar), and closes them later through perceived cues (a newsfeed, a shift
roster), not through the SCN work (BF2-7, X-9).

**Two biases are tunables, not facts:** arousal's effect on felt intervals (contested sign: Soares et al. 2016), and
"fear slows time", which is denser memory, not finer perception (Stetson et al. 2007).

**Not built:** a perceptual frame rate (alpha/theta sampling is contested: Buergers & Noppeney 2022, Brookshire
2022); a waking 90-minute cycle; felt time speeding up with age.

### 3.3 The SCN **[earned, OD-X1; OD-B8]**

- **Today:** a calendar index. Its phase comes from host local time via `datetime.fromtimestamp`, with 86,400 s
  hard-coded (`temporal_signature.py:62`); `zeitgeber_strength` is declared and never set; the oscillator advances
  one hour per observed event (`oscillator.py:193-194`). Maxim records this as "host calendar by design" (#1361 §(g)).
- **Target:** a free-running period a little over 24 h, held in `data/`; entrained by a world light percept
  (half-maximum ~100 lux for a ~6.5 h exposure, Zeitzer 2000; individual sensitivity varies by an order of magnitude,
  Phillips et al. 2019, *to verify*); phase exposed only as an estimate.
- **Windowless doesn't mean drifting (BF2-13).** Room light is near the half-maximum, so NPCs entrain to whatever
  lighting schedule the arcology runs, which may not match the outer day. Bright night-shift lighting shifts people
  partly; only dim light or darkness (forced-desynchrony protocols use under ~15 lux, *to verify*) free-runs. Captives
  in the dark drift, which OD-X1's third arm tests.
- **Two recorded Maxim decisions this argues against, named (MP-S5, MP-B2):**
  - `bio_faithful_roadmap.md`'s row "entrainment inputs | ANALOG | 4 scales is the deliberate scope", where
    "revisiting requires a new argument". The argument is this section plus OD-X1.
  - #1361 §(g)'s "host calendar by design".
- **Path:** feeding the oscillator elapsed time instead of a fixed `dt=1/24` per observation changes its dynamics even
  on the host clock, so it is a bio-mechanism change: **tier B (OD-B8), not tier A** (MP-B2). Tier A only moves the
  phase's
  *source* from the host calendar to the injected clock, still an oracle (exact world phase); OD-B8 adds the entrained
  oscillator and its estimate.

### 3.4 Where the noise comes from **[now]**

- **Never the World's generator,** so a noisy sense never changes a fire's outcome.
- **Keyed by stable identity, not by order (DR-S4, Wire S3):**
  - `SeedSequence(root, spawn_key=(NS_AGENT, npc_key, stream_key))`, never `spawn()`, which numbers children by
    spawn order;
  - `npc_key` is the persisted NPC identity from the roster (stable across saves and roster edits), not the actor
    allocator's integer;
  - `stream_key` from a registry of fixed integers in `data/` (or the first 8 bytes of SHA-256 of the name), never
    `hash()`;
  - the World's generator is `spawn_key=(NS_WORLD,)` from the same root, so the two trees can't overlap.
- **Counter layout survives rejection sampling.** One normal draw consumes a variable number of Philox outputs, so
  `(tick, event)` goes in the high counter words, or a bit generator is built per `(tick, event)` key. Percept noise is
  keyed by `(npc, stream, tick, sensor)`, never by a running counter, so it can't depend on how often Maxim pulls a
  sensor.
- **Who owns the seed path:** the host derives the agent namespace from the log header's root seed and hands each
  stream to `engine.adapters.agents`; the game's NPC-authoring code never touches it. Stream state that must persist
  is saved with the agent home (save v1).
- **Maxim's proposed `Rng` is sequential** (a seeded `random.Random` or `Generator` with named substreams). Maxim's
  internal draws are then reproducible only under the agent barrier's serialisation (§6.3). Keyed substreams are an
  upstream ask (§8.2).
- **Test:** adding an NPC, or a stream, leaves every other NPC's draws bit-identical.
- **CLAUDE.md's rule** ("one seeded `numpy.random.Generator` owned by `World`") and
  `tests/test_determinism.py::NUMPY_RANDOM_ALLOWED` (which admits `PCG64`, not `Philox`) are amended when this lands
  (BF2-15, Wire S3); `boundaries.md` §11.2 lists both.

## 4. Thought cost

### 4.1 The problem, and the decision

LLM latency is the machine's, in wall seconds. If thoughts cost no modelled time, a 3 s thought is 0.75 world
seconds at 0.25× and 60 at 20×, and competence depends on the dial and the GPU: the same class of bug as
rig-dependent physics (lesson 1).

**Decision (O4):** a thought costs **modelled world time, by phase.** An early result is held until its time; a late
one dilates the world in wall time, reported by cause. The NPC lives through exactly the modelled time on its
substrate. This needs the host to own every LLM call, which the gateway gives it (§6.1): **[after A]** with real
Maxim, **[now]** with the test double.

**Two channels the cost model doesn't remove, stated (BF2-8):**
- **Model capability.** The player's VRAM decides the model, its quantisation and context length, so a bigger GPU
  gives cleverer NPCs at every dial. It can't be modelled away. It is the agent analogue of a rig profile: the model
  profile goes in the log header and the rerun manifest, and the Known gaps record that **the outcome class is not
  promised across model profiles.**
- **The kind may depend on the NPC's state and context, never on host load or the dial.** Test: the same scene at
  1× and 20× with the test double at varied wall latencies gives the same kinds.

### 4.2 The phases

A thought is a sequence of segments, each landing at a modelled world time. **Every segment's world time is computed
by the host from the cost model, never parsed from model output** (TB2-S5). Times are integer world microseconds,
applied at tick boundaries in canonical order (§9).

| Phase | Who produces it | World-time cost | Basis |
|---|---|---|---|
| **P0 reaction** | the substrate, no LLM | a reaction latency from `data/`: ~150–250 ms simple, ~300–600 ms choice | reaction-time norms (neuroscience.md §3.1); backchannels, gaze and fillers live here (§5) |
| **P1 gap / onset** | the LLM, modelled | **in conversation:** `D_gap(turn_type)` from the end of the other speaker's turn, mode ~200 ms with a right-skewed tail; **otherwise:** `D_onset(kind)` for a choice or plan, ~0.6–2 s (*to verify*) | Stivers et al. 2009 (*verified*: mode 0–200 ms; language means ~7–470 ms; polar answers); Kendrick & Torreira 2015 (*verified*: gaps ≥ ~700 ms mark dispreferred replies); Torreira, Bögels & Levinson 2015 (*verified*: in-breath answers ~576 ms modal) |
| **P2 speech** | the LLM's stream, timed by the body | each syllable stamped at speech rate (§5.3) | conversational English ~150–190 wpm, ~4–6 syllables/s (*to verify*) |
| **P3 act** | an action the thought chose | the action's own world time, through the pipeline | — |
| **Pn next segment** | the LLM, after a tool result or a percept | another modelled onset | think → act → perceive |

- **Production latency is hidden, not added (BF2-2).** Levinson & Torreira 2015 (*verified*): gaps are ~200 ms while
  producing even one word takes over 600 ms, so responders plan **during** the incoming turn and launch on turn-final
  cues. The LLM's real latency is absorbed by dilation, and by starting the thought early (§4.5). v1 counted 0.6–1.5 s
  from the end of the turn, which would make every NPC sound reluctant.
- **Landing may depend on content, deterministically (BF2-2).** Under the dilate policy the host holds the world at
  the segment's earliest landing (`T + D_min`) until the result exists, reads its content class (a refusal, a hard
  answer), then sets the landing from it (later, with an "um" or an in-breath in the gap). That is still a pure
  function of the run, independent of the dial. Only the abandon policy can't do it.
- **Kinds (OA1, TB2-S5).** The kind comes from the closed vocabulary of `data/agents/timing.yaml`'s keys (for example
  `polar_answer`, `open_reply`, `dispreferred`, `choice`, `plan`), chosen by the agent's policy **before** the call,
  frozen in the request and logged. A result never changes it. A host-only settings table may scale each kind's cost
  (a multiplier, or a "conversation pace" preset: natural, brisk, snappy); it is labelled a game-feel knob, logged as
  a control record (§4.7), and pinned to the defaults in experiments.
- **Speech length is not part of a deadline.** Speaking is an action that takes world time in proportion to its
  length, like walking.
- **Calibration:** the hybrid draft's latency sweep sets `D_onset` for non-conversational kinds. It is calibration,
  so it can't earn anything (MP-S9).

### 4.3 Interruption and barge-in **[interfaces now; behaviour after A and Maxim's interruptibility work]**

- **`cancel_on`** lists the world events that end a thought in flight: pain above a threshold, a salient percept,
  being spoken to, being addressed by name. Cancellation is decided at a tick and logged (kind `thought_cancelled`,
  `boundaries.md` §6.1). Cancellation sources are world events only, rate-limited per source, so a guest can't cancel
  every NPC's thought by talking repeatedly (TB2-S7).
- **Speech is interruptible mid-stream.**
  - The stop is a P0 reaction (overlaps resolve within a syllable or two; Schegloff 2000, *to verify*), not an
    instant drop (BF2-11).
  - **Memory records what was actually said**, the spoken prefix, which the speech receipt carries.
  - **The unsaid remainder is kept as an interrupted intention** in the next thought's context ("as I was saying…"),
    never as speech (BF2-11).
- **A cancelled thought's late result** is dropped and logged as cancelled.
- **Maxim's side** builds on its own plans instead of duplicating them: `sem_interruptibility.md` (HA-O12, which says
  nothing can cancel a running action today), and Maxim's own plans for cancellable deliberation; roadmap Phase 3
  retired its own C9 in their favour.
  Both are under M89 ("no `src/` before the 1.4.0 cut" for the hybrid family).

### 4.4 Late thoughts **[now with the test double; after A with real Maxim]**

The default policy is **dilate**: the host doesn't step past a segment's modelled time until it has arrived. This is
the wall-time hold that two earlier reviews rejected (lanes concurrency BLOCKER 3, world_v2 DLP-B2) when built
without their fixes. It is built with them (Arch B2):
- **The wait is a state of the simulation lane** on its one multiplexed inbox, which carries `stop` and lane-crash
  messages. `stop` ends the wait at once and joins every thread.
- **The model call is always in the thinking lane, behind the gateway.** `Simulation.step` never calls a model.
- **Dispatch is by deadline,** not by priority then age, so the host never waits on a request queued behind
  later-due ones.
- **No-deadlock invariant:** a thought that is waiting for the world never holds the resource an earlier-due thought
  needs. Under O6 agents never block inside a turn (`step` returns values), so a worker is held only by an LLM call in
  flight, and the host's wait set counts only those. Test: one worker, two NPCs, a thought due after a queued one.
- **Liveness:** under every policy, a call past the host's wall ceiling ends as `thought_failed(reason=timeout)`, a
  logged record, so the world always moves again; the run is flagged tier 3 (TB2-B3, DR-S11).
- **Machine-decided failures** (an LLM error, refusal, out-of-memory) are recorded in the cache as first-class
  responses and flag the run tier 3 (DR-S11).
- **Early-held results** live in the host's thought gate, agent-side. They are saved with the agent home (save v1),
  never in the world log, which holds only the intents they produce (world_v2 DLP S-1).
- **A floor:** the loader requires `D(kind) ≥ D_min(kind) > 0`. Zero is allowed only in a named reference arm of a
  pre-registered experiment ("lockstep reference") (world_v2 BF-5.1).
- **`latency_policy: abandon`** is the explicit alternative for runs that value wall pace (a long unattended
  fast-forward). It is a host-only **control record**, logged when it changes, not only a header field (DR-S11,
  TB2-S7). Abandon runs are tier 3.
- **In flight, the NPC is a statue until Maxim's reflex layer exists.** The DN is camera-only, `ReflexRegistry` is
  keyword-on-text, and drives keep drifting. The world doesn't wait, but the NPC effectively does. The meter
  "in-flight ticks with no substrate action" lands with the lanes, and this stays OPEN until the hybrid line's
  substrate exists (world_v2 BF-5.2).
- **No "um" on a stalled model.** Fillers belong to P0 and are chosen from the **modelled** pending gap (Clark & Fox
  Tree 2002, *verified*: *uh* announces a minor delay, *um* a major one; contested by later corpus work), never from a
  stalled stream (BF2-10).

### 4.5 Latency and throughput, honestly (DR-B5)

v1 used `dial ≤ W / (N·m)`, a throughput bound. Under dilate, **latency binds first:** while a thought is pending,
the world can't pass `T + D` until the result arrives, so with wall latency L above `D / dial` it runs at most `D / L`,
however many workers exist. Over a world interval:

`effective dial ≈ 1 / ( f · L/D + (1 − f) / dial_max )`, and never above the throughput bound,

where f is the fraction of world time covered by at least one pending window. Each segment of a multi-call thought
pays L again, and a tool call can't act on a partial stream, so it pays the full latency.

Recomputed with the documents' own numbers (D = 1 s, L = 3 s, dial_max = 20):

| Scene | v1 said | Latency bound |
|---|---|---|
| One NPC talking to the player | — | **about 0.33×, below real time,** while it deliberates |
| Ten idle NPCs, 2 thoughts per world minute each | ~10× | about 6.7× |
| Hosted, 16 parallel, 2 s, 20 NPCs, 2 per world minute | 12× | about 1× |
| Everyone asleep | ~20× | physics-bound, ~20× |

**What this means for players:** any deliberation slower than its modelled onset puts the world below 1×, including
for other players in co-op. The levers, in order of size:
1. **Start the thought during the other speaker's turn,** on streamed speech, as people do. The player's utterance is
   the NPC's lead time. **Typed text arrives all at once and gives no lead;** streamed voice input does.
2. **Small, fast prompts for the first word** of a reply, and a faster model for speech turns than for plans.
3. **Streaming the first token** for P2 speech, so the gap closes on time-to-first-token, not on the whole reply.
4. P0 carries the gap with gaze and backchannels. That changes the feel, not the arithmetic.

**Meters (B5 rows, DR-S9):** wall latency to first token and to the complete tool call, per model; effective dial by
cause.

### 4.6 Coupling to the body: mental fatigue and sleep pressure, not hunger **[after A; effects earned by OD-X2]**

- **Biology:** the brain uses ~20 W at rest, and task-evoked increases are under ~5% of baseline (Raichle & Gusnard
  2002, *to verify*). So thought charged to calories would be unfaithful, and **hunger is not coupled** (small studies
  of mental work and later food intake, Chaput & Tremblay 2007, *to verify*, aren't strong enough to change that).
- **The loop:** load (world time in P1 and Pn × the kind's weight) raises mental fatigue (§2.3). Mental fatigue feeds
  sleep pressure through the marked load term. Rest and sleep recover it. Once OD-X2 earns them, fatigue makes the NPC
  deliberate less often and its onsets slower and more variable.
- **Never from `LLMEnergyTracker`.** It counts tokens and wall latency, the machine's costs: an NPC would tire faster
  on a slower GPU.
- **The Phase 5 energy and homeostasis plan** gets three limits on the same drive machinery: body energy, the heat
  budget (what Overdrive spends) and mental fatigue.

### 4.7 Thought budgets and authority (TB2-B3, TB2-S5, TB2-S7)

- **A thought budget in `data/agents/thought_budget.yaml`,** under the gate contract (`boundaries.md` §5.4): maximum
  segments, tool calls, tokens per segment (passed to the model as its generation limit and enforced again as a stream
  cut-off **before** buffering), held-buffer bytes, memory writes and their bytes, `cancel_on` length, and a ceiling
  on `D` per kind.
- **Exceeding any cap ends the thought** as `thought_failed(reason=budget)`, logged, keeping the spoken prefix as an
  interruption does.
- **Authority:**
  - only the host changes the dial, `latency_policy` and the pace table; dilation is never a lever a guest can
    request;
  - thought requests come from the agent lane only; percepts may trigger them, rate-limited per speaker;
  - cancellation comes from world events only, rate-limited per source.
- **Rejection tests** for each cap, and a liveness test: a model that never returns, under dilate, still lets the world
  advance after the ceiling.

### 4.8 Reproducing runs with real thoughts **[after A, and after the agent barrier]**

v1 tagged this [now]. It can't hold before tier A: every prompt carries the host time, so no key ever repeats; and
before the barrier (§6.3), the agent state that builds the next request depends on thread timing (DR-B3, X-2, Wire
S9). With both:

- **A response cache, per LLM call** (each segment), not per thought.
- **The canonical request** is a frozen, versioned type with golden fixtures: the model id and a weights or
  quantisation digest; sampling parameters (temperature, top-p, top-k, seed, max tokens, stops); the system prompt; the
  tool schemas in a fixed order; the message list; the prompt-template and pymaxim versions. Serialised as canonical
  JSON: sorted keys, no floats or a fixed float format, NFC strings, explicit separators.
- **Occurrences:** keyed by `(content hash, occurrence index)`, so two identical requests at temperature above 0 in
  one run reproduce both answers.
- **An entry holds only the raw model output and the full canonical request.** On read the gate recomputes the hash
  and refuses a mismatch; actor, kind, timing and targets are recomputed from the request and the cost model, never
  read from the entry (TB2-S4).
- **Misses on a rerun are loud errors**, never a live call, so a rerun can't silently become tier 3.
- **The cache is a registered gate** with the strictest contract (versioned, strict decoder, size budgets), is **per
  save**, never global, and is **excluded from bug reports by default**, since it holds players' conversations.
- **Replay never opens the cache.** Tested: a replay with the cache deleted, or poisoned, gives the same digests.

## 5. Conversation in hybrid mode

### 5.1 The split, and whose line it is (OA3)

| Behaviour | Produced by | Why |
|---|---|---|
| Turn-taking: gaze, nods, backchannels, fillers, starting to answer | Maxim's substrate, P0 | gaps of ~200 ms (Stivers 2009, *verified*) are faster than content can be planned, so people plan in overlap and signal with fast routines |
| Content: what to say and do | the LLM, P1 onward | deliberation |
| Speaking it | the body, at speech rate, interruptible | speech is an action |
| Being interrupted | the substrate first (stop, look), then the LLM | barge-in (§4.3) |

- **Overdrive builds no repertoire of its own** (OA3). A game-side repertoire would be a second substrate competing
  with Maxim's, the workaround the push-back rule forbids. Phase 1 lays only the interfaces: segment kinds, the
  `speak` kind, backchannel and filler intents in the vocabulary, and the timing fields.
- **Build on Maxim's hybrid plans, not beside them.** `hybrid_arbitration.md` (Maxim `origin/main`; HA-O1–O16,
  decided 2026-11-11 and -12): a third `aut_mode` ("arbitrated"), the substrate acting by default after a hold *h*
  with asymmetric pre-emption under a safety floor (HA-O2, HA-O16), one shared NAc with credit per chooser (HA-O8).
  Its family (`idle_dmn_coordinator.md`, `learned_hold_window.md`, `foreign_advice_layer.md`,
  `sem_interruptibility.md`) is under **M89: no `src/` before the 1.4.0 cut.** Phase 4's conversation timeline is
  bound to that, and the owner accepted the coupling (OA3).
- **Overdrive supplies:** the body (gaze, nodding, posture as affordances), the test scenes, and measurements for the
  hybrid line's pre-registered experiments.
- **Starting to think before the other speaker finishes** is proposed to the hybrid line as an experiment: it is the
  largest latency lever (§4.5) and it is bio-faithful (Levinson & Torreira 2015).
- **A push-back the plans reveal:** `learned_hold_window.md` uses "the observed LLM latency" in its waiting cost. In
  an embedded world that makes the hold depend on the player's hardware and the dial, the bug §4.1 removes. The ask:
  embedders supply the modelled latency (§8.2).

### 5.2 Speech as a world input (TB2-S1, TB2-S2, DR-S8, Wire S5)

- **A `speak` kind** (`boundaries.md` §6.1): any actor; an NPC only through a thought, a player only through a
  protocol message. It carries the text.
- **Stage-1 validator:** a length cap, Unicode NFC, control and bidi-override characters refused, a per-session rate
  limit; golden rejection frames.
- **It is logged,** as a world input other actors perceive: replay must reproduce who heard what and which thoughts
  it cancelled. That is the one exception to "LLM text stays out of the log", and it carries a privacy cost: a shared
  bug report includes dialogue. Bug reports therefore redact `speak` text by default, keeping lengths and syllable
  stamps (`boundaries.md` §6.2).
- **Its receipt** carries the spoken prefix; another NPC hears it through a B-13 sound channel (Phase 4, with sound).
- **The client renders speech as plain text, BBCode off.** Godot's `RichTextLabel` interprets `[img]` (which loads
  `res://` and `user://` paths) and `[url]`, so an LLM line must never be markup.
- **Speech timing is stamped by the server only;** client-supplied speech timing is a refused field (TB2-S6).

### 5.3 Syllable stamps (OA4; DR-S8)

- **The server stamps syllables from a model, not from audio.** A deterministic syllabifier in the engine splits each
  word; stamps come from a modelled speech rate with stress and pauses, tunable in `data/agents/speech.yaml`. The
  timeline is a pure function of the text and the NPC's state, independent of the dial and the machine.
- **Stamps never depend on stream chunking.** A word is stamped only once the following delimiter arrives (the last
  at stream end), so a provider that splits "hel" | "lo" never stamps "hel". The syllabifier is pinned and its version
  goes in the rerun manifest.
- **The client conforms.** A text-to-speech engine's own timing varies by machine, so the client stretches audio,
  lip sync and subtitles to the server's syllable times, never the reverse. Phonemes and visemes stay client-only.
- **Caveats:** English syllabification is imperfect (hyphenation dictionaries aren't syllable dictionaries), and the
  library's licence must be checked and listed before it is committed (CLAUDE.md, Data and assets). Word stamps are the
  fallback if the library fails that check.
- Syllables are about 200–250 ms (~4–6 per second, *to verify*), about two ticks at 0.1 s, so they need the sub-tick
  stamps of §9.

### 5.4 What the player sees: the three-handed clock (OA2; Wire S7)

- **An analogue clock, no digits.** Hour and minute hands show world time of day. A **smooth-sweep second hand**
  shows the world's actual rate against real time; a faint **ghost second hand** sweeps at the requested rate, so the
  gap between them is the dilation.
- **Colour plus motion, never colour alone** (CLAUDE.md): blue for slowed, red for fast-forward, always paired with the
  sweep speed.
- **Aliasing:** above a tunable threshold (~60×) the second hand fades into a motion-blurred disc and the minute hand's
  sweep carries the rate.
- **The cause is shown diegetically** on the thinking NPC (a visible pause, a glance away), as a purely visual client
  effect.
- **Dilation by cause** reaches the client through a host status channel (a protocol message and a field-registry
  channel), and is log metadata the `Simulation` never reads (`boundaries.md` §6.3).
- The clock is player-facing UI only; it never reaches an NPC. Part 3 owns its layout.

## 6. The action contract, under O6

### 6.1 The embeddable agent contract (O6; Arch B3, DR-B2, Wire B3, TB2-B1, TB2-B2)

What Maxim must offer for Overdrive to run real NPCs, all **[after A]** and drafted upstream as part of tier A:

| Piece | What it is | Why |
|---|---|---|
| **Host-called stepping** | `step(world_dt, frame) -> StepOutput`: intents, memory writes and thought requests as values; the agent never applies anything and never runs on its own thread | the host owns time and order; generate vs apply (OD-A15) |
| **A host-supplied LLM gateway** | Maxim's only path to a model, with streaming (a token iterator) and cancellation | holding, stamping, dilating, cancelling and caching all need the host in the stream. Maxim's `LLMBackend` protocol today returns whole responses (`complete() -> str`, `complete_with_usage(..., stream=)`), with no token iterator and no cancellation; streaming exists only inside one backend (#1370) (`models/language/backend_protocol.py`, `origin/main` 7084f561) |
| **A closed tool roster** | the membrane's affordances plus reviewed cognition tools (memory recall, narrative), nothing that reaches the host's filesystem, processes, network or Maxim's operational mode | a default agent gets `BashTool`, file tools, `HttpFetchTool`, `InternetSearchTool` and a `singularity` mode switch (`runtime/bootstrap.py:132-141`), and player speech is in its prompt |
| **A home per agent** | injected, under the save, never `~/.maxim` | `data_home()` is a cached module global (`utils/paths.py`); every agent in a process shares one memory, by default the owner's real Maxim home |
| **No pickle on the load path** | Maxim's persistence loads without executing code | `similarity/semantic.py:619` loads with `np.load(..., allow_pickle=True)`; a stranger's save would run code |
| **No host time** | none in prompts or observations | `prompt_builder.py:1104`, `:159`; `context_pool.py:468, :493`; a declared "no calendar" |
| **World-time staleness** | every staleness and deadline on the injected clock | the wall thresholds of §1 drop thoughts whatever the world says |
| **Credit at settle** | the cerebellum observes when the receipt settles, from its frames | it trains on the sensors read during the call (`tool_bridge.py:864-892`) |
| **Valence per D53** | the adapter always self-reports: `neutral` when the measured effect is nil or unverifiable, drive deltas through `measured_drive_transitions` | absent a report, mechanical success books POSITIVE (`tool_dispatch.py`, D53 block); a strike that changed nothing would teach "striking steel doors works" (BF2-3) |
| **An embedded-NPC profile** | one declared profile that builds all of the above | so the game doesn't rely on deregistering tools after Maxim built them |

**Front gate: what Maxim already has, which tier A must build on, not beside (MP-B1):** `ExperienceClockDriver` and
its stepped-world declaration (#1361 S2, Q8; #1361 "adds no clock"); `seeding.py::make_agent_rng`; `_StepClock` and
`LockstepTime`, which already patch `time` for lockstep runs; `tool_failure_credit.md` (#1200, TF1–TF3) and the D53
NEUTRAL tier, which propose and settle amend; `ENTITY_FORMAT_VERSION`; `sem_interruptibility.md`. The upstream drafts
own that survey; this part only depends on its outcome.

### 6.2 What Overdrive builds now **[now: the `phase1/agents` PR]**

- **`AgentPort`, split in two (Arch B3):**
  - the port the **host** calls: `step(now_tick, dt_ticks, frame) -> StepOutput`, `settle(receipts)`;
  - a **host service protocol** the adapter receives as a required keyword-only argument: `request_thought(request)`,
    the gateway handle, the intent sink. It is defined in `engine.intents`, below the adapters, so nothing imports
    upward.
- **`StepOutput`, receipts and thought requests** as frozen, versioned types with golden fixtures.
- **`data/agents/` timing, speech, fatigue and thought-budget files,** each loaded through a gate.
- **The scripted test double:** an agent that implements `AgentPort` from a script (fixed intents, fixed thought
  requests, recorded responses) and runs through the real gateway, barrier and log. Every [now] test in this part runs
  against it. It is a test double, never shipped as an NPC, and the tests say so.
- **Real Maxim** behind `engine.adapters.agents` is a **strict red gate** (`xfail(strict=True)`) until tier A ships,
  with the reason naming the missing piece. Nothing is built around Maxim's router, which the push-back rule forbids.
- **The membrane's synchronous path.** Today `StructureModulator.execute` applies the act within the call. After the
  boundaries split it calls the applier synchronously with no log, under a TEMPORARY marker scheduled for
  `phase1/agents` (not
  `phase1/sim-clock`, which can't remove it; Arch S5). `phase1/agents` replaces it: `execute` only parses, checks the
  bound actor and appends the intent to the stepping agent's outbox, returning a pending, `neutral` result.
- **The PR's place:** after `phase1/sim-clock` (it needs the intent record and the tick) and before `phase1/lanes`
  (which brings the threads, the barrier's concurrency and the meters) (`world_model.md` §10).

### 6.3 The agent lane and the barrier (Arch B1, DR-B1)

This replaces `realtime_lanes_coop.md` §4.1's "the simulation lane owns `Simulation` (and through it World and
agents)" and "agents step inside the simulation lane's tick" (§11).

- **One owner per agent.** Each agent is owned by one agent-lane thread at a time: its `step`, its `settle` and any
  push into its body run there, serialised. Only the LLM call itself leaves it, through the gateway. With
  generate vs apply nothing writes agent state from a thinking worker.
- **The barrier.** The host steps tick T+1 only when every agent is **parked**: returned from `step`, or waiting at
  the gateway for a held response. Released work (a response at its time, a receipt) runs to its next park before the
  tick advances, in canonical order (§9).
- **Agent isolation.** Two agents in one process must not share Maxim's module-level state (global `random`, caches,
  the de-duplication window). Until tier A proves it (an exit test: one agent's digest is the same alone, alongside
  another, reversed and concurrent; DR-S5), the adapter runs **at most one real Maxim agent per process** and refuses
  more (TB2-B2).
- **Meters (B5):** park and release per NPC per tick (at 200 ticks per wall second, 50 µs each is 10 ms per second per
  NPC), adapter push and strip, gateway overhead, GIL contention.

### 6.4 Propose, receipt, settle (Wire S12, Arch S13, X-6)

- **The engine's contract:** an intent produces one receipt: intent id, outcome kind (`applied`, `refused`, `stale`,
  `cancelled`), `apply_tick`, the measured effect, and the before and after frame ids.
- **Each receipt is credited exactly once,** through `settle`, and zero times when `stale`. A test asserts it. Under
  O6 there is no second path (`execute`'s return) to double-book.
- **Slow effects.** Ignite's effect arrives over many physics steps. Credit at a single settle frame learns "ignite
  barely changes temperature". Until tool-level settle can carry a horizon (OD-A16), slow-effect credit is an **OPEN
  divergence with a red gate.** The sensors used for credit are restricted to those the affordance declares it
  affects, so an entity dominated by an ongoing process (a crate in a fire) doesn't train the cerebellum on the
  world's drift (BF2-3).
- **The credit path never reads instruments.** Per-actor binding gives each NPC perceiver-relative sensors, so B-13
  and credit agree (Arch S13).
- **Stale is context, never credit** (lesson 9). Maxim books every `success=False` as NEGATIVE. The refusal-kind key
  (OD-A16) must be **promoted** through the bridge, because `tool_bridge.py:580-582` drops `result.metadata` on
  failure and `tool_dispatch.py:370` books NEGATIVE before any valence is read; the same holds for any settle key
  (X-6). Until then, stale refusals are an OPEN divergence behind a strict red gate, and the receipt goes to the next
  thought's context.
- **A malformed call is a cognitive error, not a tool failure** (lesson 7).

### 6.5 Per-actor binding and identity (TB2-S8, MP-S12, Arch S3)

- Each NPC gets its own entity and modulator, bound to its actor; `name` and `full_path` stay identical across actors,
  since the cerebellum and NAc key on them (lesson 10).
- **The adapter refuses a call whose modulator's bound actor isn't the agent it is stepping.** Test: two NPCs and a
  deliberately shared entity go red without the check.
- **The membrane factory takes a frame source and the intent sink, never `World`** (`boundaries.md` §7.2).
- **Maxim-side:** an acting-entity context reaches `execute` only **opt-in**, declared by the modulator (for example a
  class attribute `accepts_actor = False` that the bridge checks). Injecting a new key into every modulator's
  `params` would make strict modulators, Overdrive's included, refuse every call after an upgrade (MP-S12).

## 7. Perception

### 7.1 B-13: percepts through physical channels; instruments are devices (BF2-6)

- **A percept** is a reduction of registered physical channels at the perceiver's position and receptor, with a
  line-of-sight gate once light exists (`boundaries.md` §4.4).
- **An instrument is an in-world object** with a position, its own physical reduction (a probe, a lag) and a display
  that is perceived like any other percept. A thermometer reads its own temperature where it is.
- **Today's omniscient region sensors** (a crate's interior maximum, to anyone, anywhere) are **test and lab
  instruments, never an NPC's input.** Their interior maximum also grows with resolution; it becomes a surface
  temperature over an area in metres (world_v2 NIT-2).
- **Each world sensor declares how it reaches a perceiver** (N9, perceivability: world_v2 BF-2): its receptor, or the
  device it needs.
- **This shrinks our own Maxim ask.** With instruments as world objects, Maxim may need nothing beyond the existing
  `modality:` on a visual percept, and "using one" is a world fact (in hand, in sight). OD-C8 is re-checked
  against that before it is filed.

### 7.2 The push path **[Phase 4; per-part sensors after C8]**

- Maxim bodies perceive by push: the world writes values through `world_set_axis`, with `live_world_set_sensors`
  declaring it the single writer. The adapter does this on the agent's owner thread (§6.3), as a pure function of the
  frame pinned for that agent (§7.3), so it needs no log record.
- Every body sensor the world simulates is world-owned, so an NPC is never burned twice.

### 7.3 Which frame a pull reads (Wire S6)

- **A frame is pinned per agent** by the adapter: the frame observed at the agent's last `step`. Maxim's pulls during
  a step read that frame, never "the latest published", so what a sensor returns can't depend on the dial.
- **Leaks removed:** `extra={"cell_size_m": dx}` on every reading and `metadata["cell_size_m"]` on the entity put the
  rendering tier in front of cognition; both are dropped (an instrument may carry it).

### 7.4 The receptor-first rule **[now, as a review rule]**

- Every sense names its human receptor or drive, or it is an instrument (lesson 5). An NPC feels rising CO₂ as air
  hunger, never "low O₂".
- **"Every hazard has a cue before harm" is a game-design rule, not biology** (BF2-14). Humans have no receptor for
  carbon monoxide, nitrogen asphyxia or ionising radiation. A cueless hazard is allowed only together with an in-world
  instrument (a CO alarm).

## 8. SEM refinement

### 8.1 Items, by roadmap Phase 3's ids

Additive first, in 1.x; appending a defaulted field is non-breaking under Maxim's own reading of CC3
(`AffordanceSchema`'s marker, `sem.py:113-116`; precedents `always_active` #403 and `speech_param` #1261); only
`Modulator.execute`'s signature is a real break, and it can be opt-in (MP-B3, X-5). Ids are roadmap Phase 3's
`OD-` ids (the Phase 3 fold renumbered them; its "Was" column maps the old A, B, C and SEM S-ids).

| Roadmap | What | Here | Path |
|---|---|---|---|
| OD-I1 | `salience_map.py`'s `or` turns world time 0.0 into the wall clock | §1 | an issue now |
| OD-I2 | `ModulatorResult` has no CC3 declaration (path (b), `metadata` as the extension channel) | §6 | an issue now |
| OD-A1–OD-A9 | the world-clock work: #1361 S3–S6, `AgentTime`, prompt and observation time (with `context_pool`), stamps, the de-duplication window, dispatch gates, ids, the stepped Default Network | §1, §3.1 | additive; defaults reproduce today's values |
| OD-A10–OD-A15 | the embeddable agent: the entry point, the closed tool roster, per-agent homes, no pickle, streaming and cancellation on `LLMBackend`, `step` and `think` returning values with isolation between agents | §6.1 | additive |
| OD-A16 | credit for effects measured later: receipts, the cerebellum at settle, exactly-once credit, `stale` and `call_error` kinds, a per-modulator valence default | §6.4 | an amendment to `tool_failure_credit.md` |
| OD-B8 | the oscillator steps by elapsed time; light entrains the circadian scale | §3.3 | tier B, earned by OD-X1 |
| OD-B9, OD-B10 | coarse time for cognition (interim bins, then estimates); an interval sense | §3.2 | tier B, earned by OD-X2 |
| OD-B12 | a mental-fatigue drive that rises with deliberation load; `CouplingSpec` can't carry it | §2.3, §4.6 | tier B, earned by OD-X2 |
| OD-B13 | weekly, monthly and annual oscillator scales cue-driven or off | §3.2 | tier B |
| OD-C1 | drive drift states its time base | §2.2 | additive; optional rename with an alias |
| OD-C2 | `SensorReading.timestamp` is the body clock, never rendered | §3.1 | additive |
| OD-C3 | `acts_on` on `AffordanceSchema`, a trailing defaulted field | §6 | additive |
| OD-C4 | the acting entity reaches `execute`, opt-in through `accepts_actor` | §6.5 | additive |
| OD-C5 | `ModulatorResult.settles`, a trailing defaulted field | §6.4 | additive |
| OD-C6 | reserved membrane metadata keys | §6 | additive |
| OD-C7 | `ModulatorResult` and `SensorReading` are not mutated (freezing deferred) | `boundaries.md` §5.1 | additive |
| OD-C8 | percepts and instruments, shrunk: instruments are in-world objects | §7.1 | additive |
| OD-C9 | a version rule for the SEM vocabulary on `ENTITY_FORMAT_VERSION` | §6 | additive |
| OD-C10 | `world_set_axis` for sub-sensors | §7.2 | additive (unverified) |
| OD-H1–OD-H4 | the hybrid line as a test bed; modelled latency for the hold; the G4 re-key; deliberation during the other speaker's turn | §5.1 | Maxim's hybrid plans |

### 8.2 Upstream asks this fold reveals

Most are now roadmap Phase 3 rows (the Phase 3 fold added them); the rest are for that fold to place.

| Ask | Roadmap |
|---|---|
| The embeddable agent contract: entry point, closed tool roster, per-agent home, no pickle, streaming and cancellation, `step` and `think` returning values, agent isolation | OD-A10–OD-A15 |
| `context_pool.py:468, :493` in the prompt and observation time row, with no host time zone | OD-A3 |
| A world calendar on the injected clock, or "no calendar" (X-9, BF2-7) | OD-A2, OD-B13 |
| A per-modulator valence default instead of D53's silent POSITIVE (BF2-3) | OD-A16 |
| A mental-fatigue drive; `CouplingSpec` can't carry graded load (BF2-1), arguing against the SHAPE-FROZEN rationale about `extra` (fair about `extra`, but the shape fixes coupling as binary) | OD-B12 |
| Embedder-supplied modelled latency for the learned hold window | OD-H2 |
| Deliberation started during the other speaker's turn | OD-H4 |
| **Keyed RNG substreams,** not sequential ones (DR-S4) | not yet placed |
| **A step-size invariance exit test** in tier A (X-11) | not yet placed |
| **World-time staleness thresholds** (`LLMWorker`'s 5 s, `_STALE_PROPOSAL_AGE_S`, the orchestrator's 15, 30 and 60 s; world_v2 BF-5.4) | not yet placed explicitly; nearest OD-A15 |

Each names the decision it argues against when drafted, and follows Maxim's process. The owner's 2026-11-16
decision to refine SEM is recorded in Maxim's `DECISIONS.md` by the plan PR, not only here (MP-S13).

## 9. The tick and sub-tick time (for `phase1/sim-clock`)

- **The question:** at `tick_us` = 100,000 (0.1 s), the fastest response is one tick. A withdrawal from a burn fits:
  the nociceptive withdrawal reflex's RIII component is above ~90 ms and RII 50–90 ms (Thorell et al. 2023,
  *verified*). The reflex below a tick is the **acoustic startle** (~30–50 ms EMG onset, *to verify*), not the
  stretch reflex v1 cited (BF2-4). Turn gaps of ~200 ms are two ticks, and syllables about two.
- **Integer microseconds end to end (DR-S2).** Agent events (percepts, crossings, intents, syllables) carry an
  integer `apply_us` within the tick; ticks are derived only at apply. Timing data stays in microseconds and is never
  converted to ticks at load.
- **The apply rule:** `apply_tick = ceil((observed_tick·tick_us + L_us) / tick_us)`, in integers; a stamp exactly on a
  boundary applies at that tick.
- **One ordering key, stated once in `boundaries.md` §6.2:** `(apply_tick, kind_rank, apply_us, actor_id, seq)`.
  Controls and joins rank before intents. **Player intents are stamped by the host:** `observed_tick` is the last frame
  sent to that session, and `apply_us` is 0. Client-supplied tick, sub-tick and speech-timing fields are refused
  (TB2-S6, DR-S3).
- **If reflexes need to act below a tick,** the substrate steps k times within a tick on the same frame, for reflexes
  only; the alternative is a smaller tick. Under k substeps, the injected clock advances exactly by the stepped dts,
  so drift and stamps read one time (Wire S1).
- **If neither lands,** a reflex latency below one tick is a Known gap, with numbers.
- **Lane hand-off counts inside the modelled latency:** an intent's apply time is `observed_tick + L_bio`, and a
  configuration where `L_bio` is shorter than the lane's minimum is refused.

## 10. Experiments (Maxim cradles, off the game ledger)

Pre-registered in Maxim's process, run as cradles with an engine-only fixture body. Game runs never go on Maxim's
ledger. Ids are Overdrive-scoped, since T1, T2, E1–E3 and B1–B4 already name Maxim's own release thresholds,
experiments and floor chain (MP-S9). Vocabulary is Maxim's: these are `[behavioral]` claims, and rows go to
`behavioral_graduation_candidates.md`.

| Exp | Question | Arms | Kill criterion |
|---|---|---|---|
| **OD-X1** | Does perceived time of day carry behavioural weight? | exact SCN phase; the entrained oscillator with light; the same with light removed for N days; **floor arms `tabular_q` and `random`** (BF2) | if the oscillator arm can't match the exact arm on food anticipation within the margin, the exact phase stays a marked ANALOG and the gap is a Maxim finding |
| **OD-X2** | Does state-dependent timing change what is learned? | fixed latency; latency and deliberation frequency modulated by mental fatigue and circadian phase; a shuffled control with the same latencies but no link to state; floor arms | if the modulated arm doesn't beat the shuffled control by a pre-registered effect size, state dependence is game feel only (`[engineering]`) |
| hybrid latency sweep | At what world-time latency does competence collapse? | stub latency 0, 1, 3, 10, 30 world s | calibration, not a claim: it sets `D_onset` and earns nothing |

Without floor arms, either experiment could reach only `PARTIAL (narrow: floor matched)` under Maxim's BF2 rule
(2026-10-10). The refractory and habituation curves are manipulation checks. Both go to `docs/experiments/` only after
a four-lens design review.

## 11. What this supersedes

### 11.1 In `realtime_lanes_coop.md`

| There | Here |
|---|---|
| §4.1 "the simulation lane owns Simulation (and through it World and agents)"; "agents step inside the simulation lane's tick" | agents are outside `Simulation`, one owner thread each, stepped by the host behind a barrier (§6.3) |
| §4.2 `(tick, host_seq)` assigned on arrival | one canonical key in `boundaries.md` §6.2; arrival never orders (§9) |
| §4.2 request ids "assigned by the simulation lane" | thought request ids come from the host's thought gate, `(tick, actor, n)` |
| §4.3 "applies on the first tick after it arrives" | each segment lands at its modelled time; early results are held (§4.2) |
| §4.3 thinking speed "depends on the dial … measured rather than hidden" | modelled and dial-independent; late thoughts dilate (§4.1, §4.4) |
| §4.3 abandonment by `max_age_ticks` as the default | dilate is the default; abandon is a logged host control (§4.4) |
| §4.3 a stale refusal is "something it can learn from" | context, never credit, OPEN until OD-A16 (§6.4) |
| §4.3 "a thought result is a pure value" | holds under O6's contract, from tier A (§6.1) |
| §4.4 tier 3 "live models aren't reproducible" | reruns reproduce after tier A and the barrier (§4.8); replays were always exact, and reproduce the world only (`boundaries.md` §6.2) |
| §9 Q1 "don't hold the world for a late thought" | held in wall time, never in world time, with DLP-B2's fixes (§4.4) |

Still standing in §4.3: one thought in flight per NPC, the meters, and the fixed-latency stub (now the test double).

### 11.2 In `world_v2.md` §6

| There | Here |
|---|---|
| "thought results and worker failures" are log inputs | a thought is never a world-log input; its intents are, and failures that end a thought are logged `thought_failed` records; results themselves are agent-side (`boundaries.md` §6.2) |
| the `Simulation` decides abandonment and cancellation | abandonment is a host policy; cancellation is decided from world events at a tick (§4.3, §4.4) |
| live results apply at `max(T + d_min, first tick after arrival)`; "the world never waits" | the world dilates under the default policy, with a floor `D ≥ D_min > 0` (§4.4) |
| the world-time latency mode for headless cradles only | generalised as the default for live play, with DLP-B2's fixes |

## 12. Open questions and divergences

### 12.1 For the owner

1. **Guest sessions with real-Maxim NPCs before tier A.** Host data (local time and time zone, workspace paths, the
   owner's own Maxim memories) reaches NPC dialogue until tier A. Proposed: the host refuses guest sessions while
   real-Maxim NPCs are live, until the prompt test passes on the pinned pymaxim (TB2-S9).
2. **Local or remote LLM.** If a remote provider is ever used, it receives players' words; that needs a stated
   disclosure (TB2-S9).
3. **The stale-refusal fix gates Phase 4.** Roadmap Phase 3's exit now requires OD-A16, so the first NPCs never learn
   from stale refusals (Arch S14). Confirm that ordering, since it puts the credit amendment on Phase 4's critical
   path.
4. **Bug reports and dialogue.** `speak` text is redacted from bug reports by default (§5.2). Is that the right
   default, or should the reporter choose?

### 12.2 Known OPEN divergences (each with a red gate when there is code)

- Real Maxim reads the host clock on the live path (about 880 reads); closes with tier A.
- Real Maxim's prompt carries host time, time zone and the workspace manifest; closes with tier A's prompt rows.
- The prompt and dial-invisibility tests against real Maxim; red until tier A.
- Two clocks reach one agent (the membrane stamps world seconds, Maxim's sensors epoch seconds); closes with SEM S2
  and OD-A2.
- Memory writes are ungated LLM output until generate vs apply (OD-A15) gives the game a value to check (TB2-S3).
- Memory authority ("an NPC writes only its own memory") is OPEN until per-agent homes and pickle-free persistence
  land (TB2-B2).
- Stale refusals book NEGATIVE; closes with OD-A16.
- Slow-effect credit; closes with OD-A16's settle horizon.
- The NPC is a statue while a thought is in flight; closes with the hybrid line's substrate.
- The SCN phase is an oracle (host calendar today, exact world phase after tier A); closes with OD-B8 if OD-X1 earns it.
- Weekly, monthly and annual phases are calendar oracles; Overdrive declares them off.
- The coarse interim time readout is an `[engineering]` ANALOG until the senses are earned.
- Region sensors are omniscient; they are test and lab instruments only, until B-13's perceiver half (Phase 4).
- Outcome class is not promised across model profiles (§4.1).

### 12.3 Source inconsistencies

- v1's §12.3 note that `boundaries.md` §9.3 still carried two wrong asks was stale at 4f7a754 and is removed.
- The counts are settled (X-3): on Maxim `main`, 36 `uuid4` calls, 27 global-`random` calls, 36
  `default_factory=time.time` stamps in 19 files. The roadmap's "39 global `random`" had no basis.
- The skeptic's brief drew perceived-time noise from "the world RNG"; the per-NPC streams of §3.4 supersede it.

## Fold table: the foundations review (`reviews/foundations_v1/`)

Every BLOCKER and SHOULD-FIX that touches this part. Status is **folded** (with the section), **partial** (what is
missing), or **elsewhere** (the document that owns it).

| Finding | Severity | Status |
|---|---|---|
| Arch B1 the agent lane is defined nowhere | BLOCKER | folded: §6.3, §11.1 |
| Arch B2 mode (a) + dilation deadlock | BLOCKER | folded: mode (a) dropped (O6); §4.4 DLP-B2 fixes and no-deadlock invariant |
| Arch B3 `AgentPort` isn't Maxim's thought seam | BLOCKER | folded: §6.1 gateway, §6.2 port split |
| Arch S3 `to_maxim_entity` takes `World` | SHOULD-FIX | folded: §6.5; boundaries §7.2 |
| Arch S5 agent foundations have no PR; the marker can't come out | SHOULD-FIX | folded: §6.2 (`phase1/agents`, its TEMPORARY marker); world_model §10 |
| Arch S7 part 2 quietly extends the log record | SHOULD-FIX | folded: §9; the key and `apply_us` are in boundaries §6.2 |
| Arch S8 SEM paths disagree across docs | SHOULD-FIX | folded: §8.1, §12.3; boundaries §9.3 |
| Arch S9 [now] tags need tier A | SHOULD-FIX | folded: tags, §3.1, §4.8 |
| Arch S10 no fold table; world_v2 §6 not superseded | SHOULD-FIX | folded: this table, the world_v2 table, §11.2 |
| Arch S13 mode (a) credits only instant effects | SHOULD-FIX | folded: §6.4 (OPEN with a red gate; perceiver-relative credit) |
| Arch S14 tier C holds independent items | SHOULD-FIX | partial: §12.1 Q3 asks whether C2 gates Phase 4; the tier split is roadmap Phase 3's (other fold) |
| X-2 [now] claims false with real Maxim | BLOCKER | folded: §3.1, §4.8, §1 (`context_pool`) |
| X-3 the counts | SHOULD-FIX | folded: §1, §12.3 |
| X-4 `hash()` is not a determinism break | SHOULD-FIX | folded: §1 |
| X-5 CC3 misquoted | SHOULD-FIX | folded: §8.1 |
| X-6 refusal and settle keys never reach dispatch | SHOULD-FIX | folded: §6.4, §8.1 |
| X-9 `Clock` can't give three phases | SHOULD-FIX | folded: §3.2, §8.2 item 3 |
| X-10 M76 vs G4; M72 | SHOULD-FIX | elsewhere: the world-clock draft and roadmap OD-H3 (other fold); this part cites no M76 |
| X-11 step-size test tolerance and plant | SHOULD-FIX | folded: §2.1 |
| X-12 schema, prompt and protected tests | SHOULD-FIX | folded: §3.1 (schema, prompt); boundaries §10 (protected) |
| X-13 additive disagreement; stale note | SHOULD-FIX | folded: §8.1, §12.3 |
| Wire B2 mode (a) can't reach the pipeline | BLOCKER | folded: mode (a) dropped; §6.2 intent sink as a required port |
| Wire B3 no Maxim thought entry point | BLOCKER | folded: §6.1, §6.2 |
| Wire S1 three time inputs, no invariant | SHOULD-FIX | folded: §9 (the clock advances exactly by stepped dts); the draft's test is elsewhere |
| Wire S3 seed path owner; counter keying | SHOULD-FIX | folded: §3.4 |
| Wire S4 log record lacks fields and kinds | SHOULD-FIX | folded: §4.3, §4.4, §9; boundaries §6.1–§6.2 |
| Wire S5 speech has no wire | SHOULD-FIX | folded: §5.2, §5.3 |
| Wire S6 which frame a pull reads; leaks | SHOULD-FIX | folded: §7.3, §3.1 |
| Wire S7 dilation has no channel | SHOULD-FIX | folded: §5.4; boundaries §6.3 |
| Wire S9 the cache is unregistered; can't hit | SHOULD-FIX | folded: §4.8 |
| Wire S10 stale Phase 3 ids | SHOULD-FIX | folded: §8.1 (ids as at 35b9c3e, updated with any renumbering); §12.2 closes two clocks with S2 and A2 |
| Wire S12 settle double credit | SHOULD-FIX | folded: §6.4 |
| DR-B1 agent code races the tick | BLOCKER | folded: §6.3 |
| DR-B2 the host doesn't own the LLM call | BLOCKER | folded: §6.1 |
| DR-B3 the cache isn't canonical | BLOCKER | folded: §4.8 |
| DR-B5 throughput is the wrong bound | BLOCKER | folded: §4.5 |
| DR-S1 Δt invariance vs bits; crossings | SHOULD-FIX | folded: §2.1 |
| DR-S2 sub-tick units and field | SHOULD-FIX | folded: §9; boundaries §6.2 |
| DR-S3 three ordering keys | SHOULD-FIX | folded: §9, §11.1; boundaries §6.2 |
| DR-S4 Philox stability | SHOULD-FIX | folded: §3.4 |
| DR-S5 agents share module state | SHOULD-FIX | folded: §6.3 (one real agent per process until proven); the exit test is the draft's (other fold) |
| DR-S6 dial-invisibility test can't fail | SHOULD-FIX | folded: §3.1 |
| DR-S7 replay reproduces the world only | SHOULD-FIX | folded in boundaries §6.2–§6.3 (tiers and the rerun manifest) |
| DR-S8 speech is world input; chunking | SHOULD-FIX | folded: §5.2, §5.3 |
| DR-S9 unmeasured budgets | SHOULD-FIX | folded: §4.5, §6.3 meters; boundaries §4.2, §6.2 |
| DR-S10 the agent adapter is unsealed | SHOULD-FIX | folded: §1; boundaries §3 |
| DR-S11 machine-decided failures | SHOULD-FIX | folded: §4.4 |
| TB2-B1 the NPC tool surface | BLOCKER | folded: §6.1 roster, §3.1 prompt test; boundaries §5.3 |
| TB2-B2 one shared home; pickle | BLOCKER | folded: §6.1, §6.3, §12.2 |
| TB2-B3 no thought budget; liveness | BLOCKER | folded: §4.4, §4.7 |
| TB2-S1 speech has no kind or gate | SHOULD-FIX | folded: §5.2 |
| TB2-S2 the log excludes and includes LLM text | SHOULD-FIX | folded: §5.2; boundaries §6.2 (per-kind rule) |
| TB2-S3 the memory-write gate can't exist yet | SHOULD-FIX | folded: §12.2; boundaries §5.3 (gate-to-be) |
| TB2-S4 the cache is an untrusted input | SHOULD-FIX | folded: §4.8 |
| TB2-S5 kind from model output | SHOULD-FIX | folded: §4.2 |
| TB2-S6 who stamps player ticks | SHOULD-FIX | folded: §9, §5.2 |
| TB2-S7 authority misses policy and cancels | SHOULD-FIX | folded: §4.3, §4.4, §4.7 |
| TB2-S8 identity from the object called | SHOULD-FIX | folded: §6.5 |
| TB2-S9 host data before tier A | SHOULD-FIX | partial: §12.1 Q1–Q2 put the guard and disclosure to the owner; closed code vocabulary in boundaries §5.4 |
| BF2-1 the cognitive reserve | BLOCKER | folded: §2.3, §4.6 |
| BF2-2 reply onset vs gap | BLOCKER | folded: §4.2, §5.1 |
| BF2-3 mode (a) emits no D53 valence | SHOULD-FIX | folded: §6.1, §6.4, §8.2 item 5 |
| BF2-4 citation corrections | SHOULD-FIX | folded: §2.3, §3.2, §4.2, §4.6, §9 |
| BF2-5 sleep as gating | SHOULD-FIX | folded: §2.4 |
| BF2-6 two meanings of instrument | SHOULD-FIX | folded: §7.1 |
| BF2-7 no interim time sense; calendar oracles | SHOULD-FIX | folded: §3.2, §3.1, §12.2 |
| BF2-8 hardware still decides competence | SHOULD-FIX | folded: §1, §4.1 |
| BF2-9 O4 vs §4.6 on sleep pressure | SHOULD-FIX | folded: §2.3 (owner answer OA5: fatigue feeds sleep pressure, marked) |
| MP-B1 no front gate | BLOCKER | partial here: §6.1 names the existing pieces; the survey itself is the drafts' (other fold) |
| MP-B2 oscillator breaks "robots unchanged" | BLOCKER | folded: §3.3 (tier B) |
| MP-B3 CC3 misread | BLOCKER | folded: §8.1 |
| MP-S5 decisions argued against unnamed | SHOULD-FIX | folded for this part: §3.3 names the ANALOG row and #1361 §(g); G4, G17 and M72 are the drafts' |
| MP-S9 experiment ids; BF2 floors | SHOULD-FIX | folded: §10 |
| MP-S12 the injected actor key isn't additive | SHOULD-FIX | folded: §6.5 |
| MP-S13 the owner decision recorded only here | SHOULD-FIX | folded: §8.2 (recorded in Maxim's `DECISIONS.md` by the plan PR) |
| MP-S14 stale tree; two trees' lines | SHOULD-FIX | partial: this part reads `origin/main` 7084f561; line numbers carried from the audit (1.3.3) are not all re-checked |

Findings in the foundations review that touch neither this part nor boundaries (the world-clock draft's PR plan,
fence, tripwire mechanism and exit tests; the SEM plan's venue, format and precedents; roadmap tiering): Wire B4,
Wire S2, X-7, X-8, DR-S12, MP-S1 to MP-S4, MP-S6 to MP-S8, MP-S10, MP-S11. They are the upstream drafts' fold. (X-1's
tripwire mechanism is also folded into `boundaries.md` §3.)

## Fold table: world_v2 findings handed to this part (`world_model.md`, "Not in this part")

| Finding | Status |
|---|---|
| DLP-B2 the blocking hold without its fix | folded: §4.4 |
| DLP S-1 the early-result buffer, its log position and floor | folded: §4.4 (held agent-side, saved with the home; `D ≥ D_min > 0`) |
| DLP S-2 the total order's key | folded: §9; boundaries §6.2 |
| DLP S-5 settling per cluster | elsewhere: Phase 2 rubble (part 1's foundations) |
| BF-1 TF2 doesn't exclude stale refusals | folded: §6.4 |
| BF-2 silent hazards as readable numbers | folded: §7.1 (N9 perceivability) |
| BF-3 the lab's cues and relief actions | elsewhere: part 3 |
| BF-4 the hybrid 1.5 draft vs option C | partial: §5.1 builds on Maxim's hybrid plans; the draft's rewrite is the upstream fold |
| BF-5 the latency mode's floor, failure rule, statue, wall staleness, cradle tempo | folded: §4.4 (floor, failure, statue), §1 and §6.1 (wall staleness); cradle tempo partial: live play's `D_min` equals the cradle's `D`, and the measured gap stays OPEN for the hybrid line |
| BF-6 P3 as a prerequisite; the cerebellum's job | folded: §6.1, §6.4 (settle horizon, declared sensors) |
| BF-7 the proposals' shape and clock list | elsewhere: the upstream drafts |
| BF-8 rubble as an NPC object | elsewhere: Phase 2 |
| BF-9, BF-10 the cryo store; the sealed chamber | elsewhere: part 3 |
| BF-11 heat debt | elsewhere: part 3 and Phase 5 |
| BF-12 cause verbs need effectors; requires refusals | folded: §6.4 (malformed calls are cognitive errors); effectors on tool entities are part 3's |
| BF-13 delta 1 items dropped | partial: D1, D2, D7, D8, D11 folded through §4.4, §6.4, §4.1 and §1; D9 (sleep as a world behaviour) folded in §2.4; D3–D6, D10, D12–D15 are the hybrid draft's and part 3's |

NITs folded where they touched a section: BF2-10 to BF2-15; world_v2 NIT-1 ("context for the next thought") and
NIT-2 (surface temperature).
