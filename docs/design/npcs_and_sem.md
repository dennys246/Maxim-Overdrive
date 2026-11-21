# NPCs and SEM: time, thought, action and perception (design part 2, v3.4, 2026-11-19)

**Status:** DRAFT v3.4 (2026-11-19). §6 is reopened under O36 to fold Maxim's plan review of the agent draft
(`reviews/agent_draft_v3/maxim_review.md`: O38 staleness, O39 three host calls, O40 `make_agent_rng`, OD-A20
declined, OD-EA14 and OD-EA15), its delta review (`maxim_delta_review.md`: the embedded efference copy, OD-A20
widened, wall-clock forgetting, `:` barred from keys) and its review of v5 (`maxim_review_v5.md`: the pid's owners
and its unbuilt stage, the settle invariant, O43) and its review of v6 (O45). A reviewer sets fold statuses (O25).

**History.** v1 (4f7a754) went to the seven-lens foundations review (`reviews/foundations_v1/`); v2 folded it with
O6 (mode (a) dropped for a host-driven contract; the cognitive reserve replaced by a mental-fatigue drive) and the
answers OA1–OA5. v3 folded Maxim's two answers and our review of them (`reviews/maxim_response_1/`; O11a, O13–O15a).
v3.1 folded the five-lens npcs_v3 review into §6.6, with the correction that NAc's traces decay per loop tick (`reviews/maxim_response_1/correction_1.md`, `erratum_1.md`). The
fold tables at the end map each round's findings.

Part 2 of three: part 1 is `world_model.md` (the world), part 3 will be `lab_and_core_loop.md`. This part carries the
detail `boundaries.md` defers. Where it changes a boundaries interface, boundaries is changed in the same fold and
this part says so; it never quietly extends one (Arch S7).

**Sources:** `research/time/` (neuroscience, the Maxim time audit, the engine mapping, the skeptic);
`research/signals/`; `docs/maxim_upstream/` (the world-clock and SEM drafts); roadmap Phase 3; the foundations,
boundaries, world_v2 and real-time reviews; the lessons doc (`docs/lessons_maxim_in_games.md` on `phase1/standards`);
Maxim's `origin/main` at 7084f561 (§6 re-checked on f0b1cea4, then 95af47d2), read with `git show`, never its working tree (MP-S14).

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
| O3 | The substrate runs outside the sealed core behind `AgentPort` (as refined by O6 and O6a) | §1, §6 |
| O4 | Three clocks; no time field reaches cognition; thought cost is modelled and phased in world time; late thoughts dilate the world; it couples to fatigue and sleep pressure, not hunger | §1–§5 |
| O5 | Refining SEM is in scope and a priority, through Maxim's process; additive first | §8 |
| **O6** | **Mode (a) is dropped.** Replaced by a host-driven embeddable agent contract: the host calls `agent.step(world_dt, frame)`, and the agent returns intents, memory writes and thought requests as values, never applying anything or running on its own. A host-supplied LLM gateway with streaming and cancellation; a closed NPC tool roster checked at build; a per-agent home under the save, never `~/.maxim`, with no pickle on the load path; no host time in prompts or observations; the cerebellum observes at settle; `outcome_valence` set per D53. Phase 1 has no NPCs; Phase 4's NPCs wait on Maxim shipping this. This supersedes O2's "(a) then (b)": the end state is reached directly. *Its mechanism is corrected by O6a.* | §6 |
| O6a | **O6's mechanism, corrected after Maxim's answers (2026-11-17, O7a).** Maxim has no inner tool loop, so the gateway is not a backend Maxim calls: `think` is a host-called, resumable function that returns each model request as a value, the host executes it, and cancel is resuming with a `cancelled(prefix)` reply. The intent of O6 holds; "a host-supplied LLM gateway with streaming and cancellation" is replaced by this request/reply cut. | §6 |
| OA1 | A thought's kind is chosen by the agent's policy, from a closed vocabulary, before the call. A host-only settings table may override its modelled cost (per-kind multipliers, or a pace preset); the table is logged, and experiments always run on fixed defaults. | §4.2 |
| OA2 | The player sees dilation on a three-handed analogue clock (§5.4). | §5.4 |
| OA3 | Overdrive builds no conversational repertoire of its own: interfaces only in Phase 1. **Revised 2026-11-16:** v1 said the repertoire comes from Maxim's hybrid line, but none of the hybrid plans has one (foundations delta, Bio-faithful). It is proposed upstream as **OD-H5** (a turn-taking substrate), and its absence is an OPEN divergence (§12.2) until it lands. | §5 |
| O7 | The agent half of this part (§4.4, §6) is parked as a reviewed draft until Maxim answers the embeddable-agent questions; the world half proceeds (`boundaries.md` O7). *Its condition is met: see O7a.* | §4.4, §6 |
| O9 | **A reply's content may only make it land later, never earlier.** The substrate schedules the earliest onset from what the body knows, and logs it. Content (a dispreferred answer, a long one) may add delay, capped in `thought_budget.yaml` and counted against the session's dilation budget; it may never pull the onset earlier, since that would rewrite a logged time. Resolves BF2-2 against TB2-S5. | §4.2, §4.7 |
| O10 | No developer mode with real Maxim before tier A, except inside strict red-gate tests. | §4.8, §12.1 |
| O11 | **Live play holds the floor; it doesn't dilate (2026-11-16).** While a thought is late, the substrate covers the wait with content-free fillers and gaze aversion; past a floor ceiling the NPC yields, and the late answer arrives as a new turn, logged and never booked as a cognitive failure (resolves BF2-8 against TB2-B3). The world keeps real time. Guards: a yield never feeds fatigue, credit or learning; dilate stays for experiments and the lockstep reference; a B5 meter counts yields per turn by hardware. Needs OD-H5 first. This reverses BF2-10 for live play, on purpose. | §4.4, §5 |
| O12 | **Processing speed is a per-NPC trait, in world time (2026-11-16).** People differ in speed, but that variation belongs to the person: stable, and independent of whose machine hosts the world. Hardware lateness is not that (one host's GPU slows every NPC at once, and most in busy scenes). Each NPC draws an onset multiplier at creation, saved with the agent, from the NPC's keyed stream (§3.4); it scales the modelled onset under either latency policy and never reads the hardware. Its distribution lives in `data/agents/`, validated at load: a lognormal, median 1 at a stated reference age, sigma 0.15 within an age (plausible 0.10–0.25; choice-RT CVs of 0.13–0.15 in age-matched cohorts, `research/speed/individual_differences.md`, *verified* there). Fatigue (§2.3) and per-response noise still vary speed within a person, and per trial that noise is larger than the gap between people. The refinements the review proposes (age, domains, turn gaps) are §12.1 item 5, for the owner. | §4.2 |
| O11a | **O11 amended after Maxim's response (2026-11-16, `reviews/maxim_response_1/`).** Floor-holding runs in three steps: a content-free filler, then an account ("let me think") at about 600–700 ms, then a yield at about 1 s. The order rests on the preference for progressivity: a non-answer such as an account is preferred over silence (Stivers & Robinson 2006, *verified* there; it gives no timings). The timings come from elsewhere: gaps past about 700 ms read as dispreferred (Kendrick & Torreira 2015, *verified*) and about 1 s is the "standard maximum" silence (Jefferson 1989, *to verify*). Every threshold is a per-world parameter in world time. The first filler is chosen from the **modelled** predicted delay; what follows may track real lateness, logged, tier 3, and counted by a meter of lateness-caused gaps per machine, because listeners hear long gaps as reluctance (BD-4: Kendrick & Torreira 2015, Roberts et al. 2006). Floor-holding is proposed to Maxim as a fifth hybrid split-out plan, not inside `learned_hold_window`. | §4.4, §5 |
| O13 | **Each real Maxim agent runs in its own worker process; the process boundary is the trust boundary (TBR-3).** The worker gets a scrubbed environment, its home set to the agent's home under the save, no API keys and the offline latch engaged; it talks to the host over a pipe opened before the latch. Workers start with `spawn`, since the latch refuses `fork` and `forkserver`. The worker's working directory is its empty agent home and prefetch is off structurally: the latch stops prefetch's `find` but not its file reads under the working directory (Maxim's second response). The LLM gateway stays in the host. Pipe latency and memory per worker are measured (B5) before Phase 4 commits to them; Windows needs an OS sandbox. | §6 |
| O14 | *(Text edited 2026-11-17 to match Maxim's answer on redaction; §12.1 item 1.)* **Guest sessions with real-Maxim NPCs wait for five gates** (replaces §12.1 item 1's single prompt test): the worker process (O13); a no-effect test (no file reads or writes, sockets or spawns outside the agent home); a dialogue-level bypass test (prefetch, the short-question shortcut as a regression target since Maxim deleted it, #1689, the parse-failure template, phrase commands); line separators refused in `speak` (U+2028 and U+2029 may forge prompt headers; a related Maxim issue is a private advisory, OD-I5); and memory provenance by speaker with a purge path. | §5.2, §12.1 |
| O15 | **Engineering seams are accepted on engineering grounds.** The stepped `think`, the dispatch/settle split and the clock seam are asked of Maxim with parity and regression guards, not behind the hybrid line's experiment gate; only behaviour claims wait for experiments. Otherwise Phase 4 waits on the arbiter's results after 1.4.0. | §6, §8 |
| O15a | **Maxim's answer on O15 (second response):** the clock seam and dispatch/settle enter as engineering refactors behind a bit-identical state-digest parity guard on recorded replays, with the robot path settling right after dispatch. The stepped `think` is engineering-gated too, but it is §A.1b's seam in `agent_loop.py`, so it lands **after the 1.4.0 cut**, sequenced with the agent-loop decomposition slices (M89, touch-it-shrink-it). So Phase 4's first real NPCs wait for 1.4.0 plus that slice; until then Overdrive builds against the scripted test double. | §6, roadmap Phase 4 |
| O16 | **Phase 4's interim live-play policy (owner, 2026-11-17; §12.1 item 6).** Until OD-H5's floor-holding substrate exists: **dilate in single-player**, shown on the three-handed clock, since only that player pays for the slower world; **silent late landing in co-op**, where dilation's cost would fall on other players. Late replies there land as a new turn, logged and tier 3, with lateness metered per machine. | §4.4, §12.1 |
| O17 | **Guests' speech held agent-side is purged on request and never shipped in a bug report (owner, 2026-11-17; §12.1 item 7).** | §5.2, §12.1 |
| O18 | **A sixth guest gate (owner, 2026-11-17): guest sessions use a local model only, by default.** A remote model needs a disclosure the guest sees and accepts before their words leave the machine. | O14, §12.1 |
| O19 | **The agent half is frozen at v3.1; its remaining findings become tests (owner, 2026-11-17).** Three rounds found blockers of new kinds at ever finer implementation grain (the pipe unpickles, `-I` ignores `PYTHONHASHSEED`, an unset `HOME` falls back to the real home, a resume test that can't fail): divergence, which paper can describe and only code can prove. No more design rounds on the agent half. The delta findings (`reviews/npcs_v3_1/`) are its known-issues list, and each open BLOCKER becomes a red-first test in the `phase1/agents` PR against the scripted double behind the real worker channel: a hash probe in the worker's first frame, the worker's home and `XDG_*` set with no read of the host's home, the codec refusing pickles, an agent-state digest so the resume test can fail. The world half proceeds to `phase1/boundaries` and `phase1/gates`. | §6, §12 |
| O20 | **An LLM measurement spike is allowed (owner, 2026-11-17).** A throwaway script outside `src/` makes raw model calls, with no Maxim, to measure latency to the first token and to the full reply, tokens per reply, cost or local throughput, and how many NPCs one local model can serve. It makes no claim and never enters the replayable core. It doesn't amend O10, which is about real Maxim. | §4.5 |
| O26 | **A guest's purge leaves redaction records (owner, 2026-11-17; TB-B3).** O17's reach is the agent stores, continuation bodies, the response cache's requests, saves and the intent log. Each purged span becomes a record (actor, tick, length) in the log. Replay never re-runs a model on purged text: it replays the recorded model replies. A reply that quoted the purged words is redacted too, and replay is bit-identical only up to the first redacted reply, which the log marks as a replay boundary. The `purge(actor, session)` kind and a host-computed provenance lower bound are in the agent line's codec. The mechanism is designed in the agent PR. | §5.2, §6.6 |
| O27 | **Co-op listeners perceive lateness (owner, 2026-11-17; DB-S5 (a)).** Under O16's silent late landing, listeners hear the whole silence, the modelled part plus the lateness, and that is recorded as a Known gap, not hidden by an oracle. | §6.6 |
| O28 | **Co-op is Phase 5 or later (owner, 2026-11-17; skeptic S-S5).** No more review rounds on co-op or guest sessions until single-player NPCs exist. The recorded decisions (O14, O16–O18, O26, O27) stand. | §0 |
| O29 | **Bound the Maxim dependency (owner, 2026-11-17; skeptic S-S6, MS-S9).** Name the minimal tier-A subset Phase 4's first NPC needs, from the exit tests; the rest of Phase 3 is non-blocking. Ask Maxim for a date range for 1.4.0. The Phase 3 items Maxim's candidates doc doesn't cover go to a second candidates round after tier A. | §12 |
| O30 | **§12.1's remaining items answered as recommended (owner, 2026-11-17).** OD-A16 gates Phase 4. `speak` text stays out of bug reports by default. The speed trait takes the age shift, the general-plus-domain factor and the weak gap loading. Deferred by name: the OS sandbox for guest workers (before guest sessions), the speed trait's slow tail and filler propensity (after the LLM spike). | §12.1 |
| O35 | **Refresh the embeddable-agent draft and send it for Maxim's review now (owner, 2026-11-19).** Maxim accepted the world-seam front gate (`reviews/maxim_response_1/response_4.md`) and reviews the plan before any Maxim `src/` lands. `docs/maxim_upstream/embeddable_agent_DRAFT.md` folds what changed since v3.1 (Maxim's A3 clock and A2 substreams, OD-A4's tool duration, OD-A20, OD-A21, O26, O29's subset) and goes within weeks, so the review runs alongside Phase 1, not at 1.4.0. | §6 |
| O36 | **Maxim's review of that draft is a reopen trigger for the frozen agent half (owner, 2026-11-19).** It joins O19's list: its findings may change the port, and folding them is what a reopen is for. | §0 |
| O37 | **A bridge prototype NPC is the LLM spike's second half (owner, 2026-11-19).** After the tile renders, one unreplayed Maxim NPC through the 1.1.4 seam measures latency, cost and whether a conversation feels alive. It lives outside the replayable core and makes no claim (O20). | §4.5 |
| O38 | **Staleness is Maxim's hybrid §A.1b.5 (owner, 2026-11-19, Maxim's plan review).** A reply is stale only when a non-self-caused event on a tracked right arrives after its `basis_seq`, with the efference-copy exclusion (Maxim `docs/plans/hybrid_arbitration.md` §A.1b.5). Our `superseded` verdict and the step-sequence/frame-id basis are dropped. Staleness goes through Maxim's typed pre-emption handler, never `_drop_stale_proposal` (§A.1b.4). | §6.6 |
| O39 | **`apply` merges into `settle` (owner, 2026-11-19, Maxim's plan review).** Maxim's cand. A6 applies proposed writes at settle under B2's digest, so `AgentPort` is three host calls: `step`, `think`, `settle`. | §6 |
| O40 | **One randomness derivation (owner, 2026-11-19, Maxim's plan review):** Maxim's `utils/seeding.py::make_agent_rng(base_seed, agent_id)`, keyed by the persisted NPC key and extended with a stream argument, proposed to Maxim as part of a new per-agent release-gate item (after 1.4.0, per Maxim's owner). Until it exists, `agent_id` may carry `"npc_key:stream"`. The `stable_hash_64_signed` formula is dropped. | §3.4, §6.6 |
| O43 | **Replay ids (owner, 2026-11-19, Maxim's review of v5).** `session_id` is derived from the intent log's header (the log's root id plus the NPC key), never the wall clock or a uuid; the sequencer's high-water seq is saved in the NPC's agent home, so a loaded save continues the sequence. Amended by O45. | §6.6 |
| O44 | **Crash recovery and event ids (owner, 2026-11-19).** On restore the sequencer's high-water is max(the saved one, the highest pid the host logged for the agent), so an older save never re-mints a logged id; a dead worker's in-flight pids each get a typed `agent_failed` refusal receipt, so each settles once (OD-EA16). Amended by O45. | §6.4, §6.6 |
| O45 | **A log segment per restore (owner, 2026-11-19, Maxim's review of v6).** Each restore opens a new log segment, and the segment number is part of `session_id`, recorded in the log header so replay reproduces it; ids from different segments can't collide whatever the seq. O44's floor is no longer a requirement: it stays only as a host-side test that no new pid equals a logged one. Amends O43 and O44. | §6.4, §6.6 |
| O7a | **O7's condition is met:** Maxim answered (`reviews/maxim_response_1/`). The agent half is unparked for one revision, folding the response and its review, then one review round. | §4, §6 |
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
- the thinking lane's wall timeouts on the model calls it executes. **A failed call retries (`inference_placement.md` §2.6), and past a host ceiling the thought
  ends as a logged `thought_failed`** (§4.4). A timeout never silently "frees a worker" and never fails a thought on
  its own (BF2-8, TB2-B3);
- network timeouts, meters, log flushing.

None of these values crosses `AgentPort` **[now]**. The agent step path (`engine.adapters.agents` minus one named
host-only module for timeouts) is a second sealed set under the core's banned list and AST scan, and the tripwire
runs on the agent lane's thread too (DR-S10, `boundaries.md` §3).

**Today's violation, for the record** (maxim_time_audit.md; counts settled by the Executor on `main`, X-3):
- about 880 host-clock reads in about 215 files on the older `main` the time audit read (on 7084f561: 608
  `time.time()`, 145 `time.monotonic()`, 20 `datetime.now`; §12.2); 36 `uuid4` calls, 27 global-`random` calls and 36
  `default_factory=time.time` stamps in 19 files;
- substrate cadences on the wall: `llm_submit_interval` 0.5 s, the Default Network at 30 Hz, the `ReactionBus`
  refractory 0.5 s; and wall-clock staleness that drops thoughts whatever the world says: `LLMWorker(stale_threshold_s
  =5.0)`, `_STALE_PROPOSAL_AGE_S = 35.0`, the orchestrator's 15, 30 and 60 s (world_v2 BF-5.4);
- the prompt carries the exact host date and time (`agents/prompt_builder.py:229`, `:1122-1124`, and `:159`'s
  identity section), and
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
  - **Dial-invisibility test:** the test double driven through the host's thinking lane (§6.1) with a seeded **wall-delay
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
    spawn order (Overdrive's own streams; Maxim's derive by O40);
  - `npc_key` is the persisted NPC identity from the roster (stable across saves and roster edits), not the actor
    allocator's integer; it and every stream name contain no `:` (Maxim's owner: `make_agent_rng`'s
    `f"{base_seed}:{agent_id}"` join stays, so a `:` would make it ambiguous), refused at load;
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
- **Two kinds of stream, and one accepted cost (DET-S8, BD-13).** Overdrive's own streams (percept noise, the speed
  trait) stay keyed Philox counters as above. Maxim's internal streams are a `random.Random`
  per stream from `make_agent_rng`, keyed by `npc_key` and stream, `base_seed` from this tree's root (O40, §6.6). That fixes
  isolation across NPCs and streams, but **within** a stream Maxim's draws stay sequential, so a change in how often
  Maxim draws (a cadence change) shifts that stream's later draws. Accepted: §2.1's Δt test keeps bit identity only
  under fixed schedules for Maxim's streams, and paired substrate arms (§4.8) lose correlation within a stream from
  the first change in draw count. `NUMPY_RANDOM_ALLOWED` is amended for Philox for Overdrive's streams only.
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
substrate. This needs the host to own every LLM call, which the request/reply cut gives it: `think` returns each model request
as a value and the host executes it (§6.1). **[after A]** with real Maxim, **[now]** with the test double.

**Two channels the cost model doesn't remove, stated (BF2-8):**
- **Model capability.** The placement table decides each function's model (`inference_placement.md`), so a bigger GPU
  or a cloud model gives cleverer NPCs at every dial. It can't be modelled away. It is the agent analogue of a rig
  profile: each reply records its placement, and the Known gaps record that **the outcome class is not promised
  across model profiles.**
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
| **P1c deliberation cycle** | the LLM, when the first proposal isn't ready to act (PFC) | a modelled cycle cost per cycle, no speech; at most `max_cycles` (Maxim: 2, or 3 with a percept source) and capped in `thought_budget.yaml` | `agent_loop.py:521`, `:3086-3125` on Maxim `origin/main` 7084f561; `[engineering]` cost |
| **P3 act** | an action the thought chose | the action's own world time, through the pipeline | — |
| **Pn next thought** | the LLM, after a receipt (the follow-up) or a percept | another modelled onset | think → act → perceive; each step sees the world's actual response |

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
- **Deliberation cycles are content-dependent delay (O9).** Whether the model asks for another cycle depends on its
  output, so each cycle may only make speech land later, is capped, and counts against the session's dilation budget.
- **`next_actions` chains** (one reply committing later actions with no further model call, `llm_worker.py:1355`)
  are validated step by step, each when it dispatches, never once at proposal time.
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

**Policy by context (O11, O11a):** live play **holds the floor** and keeps real time; experiments, the lockstep
reference and unattended runs **dilate**. Floor-holding needs Maxim's turn-taking substrate (OD-H5), so until it lands
the Phase 4 interim policy is an owner question (§12.1). Under **dilate** the host doesn't step past a segment's
modelled time until it has arrived. This is the wall-time hold that two earlier reviews rejected (lanes concurrency BLOCKER 3, world_v2 DLP-B2) when built
without their fixes. It is built with them (Arch B2):
- **The wait is a state of the simulation lane** on its one multiplexed inbox, which carries `stop` and lane-crash
  messages. `stop` ends the wait at once and joins every thread.
- **The host's thinking lane executes request values.** `think` returns a `Pending(request)`; the lane runs it and
  the host resumes `think` with the reply. `Simulation.step` never calls a model.
- **Dispatch is by deadline,** not by priority then age, so the host never waits on a request queued behind
  later-due ones.
- **No-deadlock invariant, by construction:** no worker is ever held by an agent. An agent with an outstanding
  request is a value holding a `Pending`; a worker is held only by a model call in flight, and the host's wait set
  counts only those. Test: one worker, two NPCs, a thought due after a queued one.
- **Liveness:** under every policy, a thought past its liveness ceiling, counted from enqueue (`inference_placement.md` §2.5), ends as `thought_failed(reason=timeout)`, a
  logged record, so the world always moves again; the run is flagged tier 3 (TB2-B3, DR-S11).
- **Machine-decided failures** (an LLM error, refusal, out-of-memory) are recorded in the cache as first-class
  responses and flag the run tier 3, judged on a thought's final outcome (DR-S11).
- **Early replies are held by the host,** text included and saved with its header (`inference_placement.md` §4.2), and `think` resumes only at the segment's modelled landing tick (§6.6). The
  continuation's host-owned header lives in the host and its agent-owned body agent-side, saved with the agent home
  (save v1), never in the world log, which holds only the intents they produce and the host records (world_v2 DLP S-1).
- **A floor:** the loader requires `D(kind) ≥ D_min(kind) > 0`. Zero is allowed only in a named reference arm of a
  pre-registered experiment ("lockstep reference") (world_v2 BF-5.1).
- **`latency_policy: abandon`** is the explicit alternative for runs that value wall pace (a long unattended
  fast-forward). It is a host-only **control record**, logged when it changes, not only a header field (DR-S11,
  TB2-S7). Abandon runs are tier 3.
- **In flight, the NPC is a statue until Maxim's reflex layer exists.** The DN is camera-only, `ReflexRegistry` is
  keyword-on-text, and drives keep drifting. The world doesn't wait, but the NPC effectively does. The meter
  "in-flight ticks with no substrate action" lands with the lanes, and this stays OPEN until the hybrid line's
  substrate exists (world_v2 BF-5.2).
- **Floor-holding in live play (O11a) [after OD-H5]:** a content-free filler, then an account ("let me think") at
  about 600–700 ms, then a yield at about 1 s, each threshold a per-world parameter in world time. The **first** filler
  is chosen from the modelled predicted delay (Clark & Fox Tree 2002, *verified*: *uh* announces a minor delay, *um* a
  major one), ideally from a metacognitive feeling-of-knowing signal (Smith & Clark 1993, *verified* in BD-3), never
  from hardware. What follows may track real lateness: logged, tier 3, and counted by a **lateness meter** (gaps
  caused by lateness, per machine), because listeners hear long gaps as reluctance (BD-4; Roberts et al. 2006). A
  yield never feeds fatigue, credit or learning. Under dilate, BF2-10 still holds: no filler from a stalled stream.

### 4.5 Latency and throughput, honestly (DR-B5)

v1 used `dial ≤ W / (N·m)`, a throughput bound. Under dilate, **latency binds first:** while a thought is pending,
the world can't pass `T + D` until the result arrives, so with wall latency L above `D / dial` it runs at most `D / L`,
however many workers exist. Over a world interval:

`effective dial ≈ 1 / ( f · L/D + (1 − f) / dial_max )`, and never above the throughput bound,

where f is the fraction of world time covered by at least one pending window. Each model call pays L again: up to
`max_cycles` PFC cycles before the first speech, and one more L for every follow-up after a receipt. An action can't
act on a partial stream, so it pays the full latency.

Recomputed with the documents' own numbers (D = 1 s, L = 3 s, dial_max = 20):

| Scene | v1 said | Latency bound |
|---|---|---|
| One NPC talking to the player | — | **about 0.33×, below real time,** while it deliberates |
| The same, through 3 PFC cycles before speaking (the default maximum; the ratio leaves out P1c's modelled cycle cost, which §4.2 adds to D, so it is a lower bound on the wait) | — | **about 0.11× under dilate;** under floor-holding a ~9 s wall wait, past any yield ceiling, so the NPC yields and answers as a new turn |
| Ten idle NPCs, 2 thoughts per world minute each | ~10× | about 6.7× |
| Hosted, 16 parallel, 2 s, 20 NPCs, 2 per world minute | 12× | about 1× |
| Everyone asleep | ~20× | physics-bound, ~20× |

**What this means for players:** any deliberation slower than its modelled onset puts the world below 1×, including
for other players in co-op. The levers, in order of size:
1. **Start the thought during the other speaker's turn,** on streamed speech, as people do. The player's utterance is
   the NPC's lead time. **Typed text arrives all at once and gives no lead;** streamed voice input does.
2. **Small, fast prompts for the first word** of a reply, and a faster model for speech turns than for plans.
3. **Streaming the first token** (unavailable until OD-A25; O50) for P2 speech, so the gap closes on time-to-first-token, not on the whole reply.
4. P0 carries the gap with gaze and backchannels. That changes the feel, not the arithmetic.

**Meters (B5 rows, DR-S9):** wall latency to first token and to the complete reply, per placement and function; PFC cycles per
thought; follow-ups per triggering input; effective dial by cause; under floor-holding, the lateness meter (§4.4).

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

- **A thought budget in `data/agents/thought_budget.yaml`,** under the gate contract (`boundaries.md` §5.4): PFC
  cycles per thought; `parallel_actions` per reply (also as a grammar `maxItems`, the advisor's pattern); `next_actions`
  chain length; **follow-up chain length per triggering input**, keyed by the input's id, so an injected prompt that
  makes every reply request one more action can't monopolise an NPC tick after tick; tokens per model call (passed as
  the generation limit and enforced again as a stream cut-off **before** buffering); held-buffer bytes; memory writes
  and their bytes; `cancel_on` length; and a ceiling on `D` per kind. Under floor-holding, holds are rate-limited per
  triggering speaker, so one guest can't keep an NPC permanently mid-hold.
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

The response cache (canonical request, occurrences, entries, the three modes, pairing, saves and branches) and the
rerun manifest's inference items are owned by `inference_placement.md` §4.2–§4.3.

## 5. Conversation in hybrid mode

### 5.1 The split, and whose line it is (OA3)

| Behaviour | Produced by | Why |
|---|---|---|
| Turn-taking: gaze, nods, backchannels, fillers, accounts, yielding the floor, starting to answer | Maxim's substrate, P0 (OD-H5) | gaps of ~200 ms (Stivers 2009, *verified*) are faster than content can be planned, so people plan in overlap and signal with fast routines |
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
- **Floor-holding is proposed to Maxim as a fifth hybrid split-out plan (OD-H5),** not inside
  `learned_hold_window` (Maxim's answer; BD-1). It reuses §A.1b's held slot, but not its conflict-scaled hold or
  HA-1's claim, because addressed speech is the case Maxim's own plan calls degenerate for the arbiter (BD-2). It
  enters as `[engineering]` with its evidence cited: response planning starts in the middle of the other speaker's
  turn (EEG, Bögels et al. 2015) and a planning network is active in conversation (intracranial, Castellucci et al.
  2022), so "not a neural mechanism" is too strong (BD-9). Any claim needs a pre-registration on a measurable outcome
  (gap distribution, overlap rate, repair rate). It is a paper plan in the 1.5 line, so Phase 4 lives without it for a
  long time.
- **No claims, structurally (BD-6).** Fillers and accounts come from a closed vocabulary with an empty proposition
  field; the speaker never stores them as utterances and never credits them. A listener stores the hesitation as a
  feature of the speech percept (a duration, a filler-present flag), not as words.
- **The speed trait (O12) scales the modelled onset, never the yield threshold** (BD-5). A filler-propensity trait is
  a candidate (Bortfeld et al. 2001, *to verify*).
- **A late answer after a yield returns to the earlier sequence** ("about what you asked…"), a new turn, not a
  conversation-analytic misplacement (BD-8).
- **Partner barge-in needs a social cancel source.** `sem_interruptibility.md` covers cancels from the LLM or a
  danger; a partner interrupting a filler has no cancel path today (BD-10). Part of OD-H5.
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
- **Stage-1 validator:** a length cap, Unicode NFC, control and bidi-override characters refused, **every line
  separator `str.splitlines` splits on refused** (U+2028, U+2029, U+0085, `\v`, `\f`, U+001C–U+001E), since a guest
  line could otherwise forge a section header in Maxim's prompt (TBR-11; O14), and a per-session rate
  limit; golden rejection frames.
- **NPC speech is validated per chunk** (over the held reply until OD-A25), before it reaches any player, independent of the rest of the reply
  (Arch 2.6).
- **Memory provenance (TBR-8; O14):** every memory an NPC forms from speech records the speaker, so a prompt-injected
  memory can be traced to a guest and purged without touching what other players said.
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
| **Host-called `step`, `think` and `settle`** (O39) | Overdrive's port, in ticks: `step(now_tick, dt_ticks, frame)`, `think(handle, reply \| None)`, `settle(receipts, writes)`; Maxim's function `step(agent, world_dt_us, frame)`; `settle` the only writer, applying the host-gated writes (Maxim's cand. A6) and the credit through the agent bus; the continuation split into a host-owned header and an opaque agent-owned body (§6.6); nothing runs on its own thread | the host owns time and order; generate vs apply (OD-A15, OD-A18). Maxim has no inner tool loop (`agent_loop.py:2172`, `:2264`), so the only thing `think` waits on is a model call, but PFC deliberation makes up to 3 by default (`:3110-3111` on f0b1cea4; `llm.deliberation_max_cycles` overrides it, so the host's cap governs) |
| **The request/reply cut** (replaces v2's "host-supplied gateway") | the request is a value (rendered text, sampling, the **function**, template version, `tools is None`; the host stamps priority and deadline from the kind, outside the cache key); produced at the `LLMRouter._complete_text` cut (`router.py:958`), the function's envelope (`inference_placement.md` §2.1) feeding the `PromptBudgeter` (Maxim's `docs/lessons/sim-n-ctx-config-drift.md`); the reply is `complete(text)`, with reserved `cancelled(prefix)` and `truncated(prefix, reason)` variants that bypass the parse-failure template; speech is a top-level field emitted first | the lane sits above the backends, and no router is built (`inference_placement.md`), and the host holds, stamps, cancels and caches (Maxim's answer; Arch 2.1, 2.5, 2.6) |
| **The deliberation continuation** | a frozen, versioned, pickle-free value, not the whole agent, split by owner (§6.6) | `step` keeps running while a thought is out, so resume must decide staleness against the current agent (Arch 2.2, 2.3) |
| **World tools vs cognition tools** *(proposed; not adopted)* | resolving cognition tools inside `think` would be an inner tool loop, Maxim's C10 question; until an experiment decides it, cognition tools go through follow-ups like world tools (§6.6) | a recall through a follow-up costs a full L (Arch 1.2, Arch S3) |
| **A closed tool roster** | the membrane's affordances plus reviewed cognition tools, sealed with the advisor's patterns (`ToolPolicy`, the `Effect` ceiling); engineering, on its own clock | the default registry holds file tools (`runtime/bootstrap.py:132-135`) and `BashTool` (`:27`), and the CLI and embodied runtime add internet tools (`:255-276`); player speech is in the prompt |
| **`AgentHome`** | one per-agent object routing every store, over `AgentFactory`'s existing `persistence_dir` | the core stores are already per agent (`agents/agent_factory.py:1168-1172`); ten families are still global (embeddings, fear and escalation bridges, DN thresholds, focus and bounds learners, energy, cost, provenance, lane decisions), and the ConceptExtractor thread starts at construction (`runtime/bio_stack.py:654`) |
| **No pickle on the load path** (issue OD-I3) | Maxim's persistence loads without executing code | `MemoryHub._restore_on_open` → `EmbeddingStore.load` → `np.load(allow_pickle=True)` (`integration/memory_hub.py:719-727`, `similarity/semantic.py:662`): dormant unless `enable_semantic`, on a global file; must land before `AgentHome` makes it reachable from saves (TBR-10) |
| **The clock seam, split in two** | a **machinery clock** for decay, cadences and stamps, and a **perceived-time port**, the only time a prompt may contain, which the host supplies. Guarded by a planted-render test with its sentinel in the **machinery** clock plus an offset-and-scale test (§6.6) and a lint banning `datetime.now`, `strftime` and `localtime` in prompt-reaching modules (Maxim's answer: a no-`__str__` type can't be the guard) | the prompt renders the time (`prompt_builder.py:229`, `:1122-1124`; `context_pool.py:468`, `:493`); swapping in the host clock alone would hand cognition exact world time (BD-12) |
| **Keyed substreams** (O40) | one derivation, Maxim's `make_agent_rng` (§6.6); `seed_all` never called on the embedded path | `seed_all` reseeds the process (BD-13); a host-side derivation beside Maxim's would be a second one (Maxim's plan review) |
| **The leak closure** (OD-A17) | prefetch off and the working directory at the empty agent home; the short-question shortcut deleted in Maxim for everyone (#1689, PR #1694); the parse-failure template never reached; no model backend in the worker, so second model doors fail closed; no `force=True` logging; paths under the home; side doors folded into dispatch; a static import ban plus the advisor's three closure tests | prefetch reads files under the working directory on every input (`agent_loop.py:1571`), past every tool rule (Executor N2; TBR-3, TBR-7) |
| **World-time staleness** | every staleness and deadline on the machinery clock | the wall thresholds of §1 drop thoughts whatever the world says |
| **Credit at settle** | dispatch tags, settle credits, through NAc's existing eligibility traces, one credit path; robots settle right after dispatch | the cerebellum trains on the sensors read during the call (`agents/tool_bridge.py:864-892`); dopamine's window after an action is 0.3–2 s (Yagishita et al. 2014, *verified* in BD-19); NAc's traces decay ×0.9 **per loop tick** (`decisions/nac.py:3707`), so this depends on step-size-invariant decay (OD-A19, §6.6), not on the clock seam alone |
| **Valence per D53** | the adapter always self-reports: `neutral` when the measured effect is nil or unverifiable, drive deltas through `measured_drive_transitions` | absent a report, mechanical success books POSITIVE (`runtime/tool_dispatch.py`, D53 block); a strike that changed nothing would teach "striking steel doors works" (BF2-3) |
| **The robot path drives the same `think`** | a thin driver over the same function; the robot keeps `_complete_text_abandonable` | one deliberation path (Arch 2.4), gated by the robot-parity exit tests OD-EA14 and OD-EA15 (roadmap Phase 3) |
| **Consolidation, its own bounded host call** (Maxim's owner, 2026-11-19) | world time decides when (the NPC's sleep, §2.4); deterministic units (steps, item counts) bound the compute; the wall clock only as a logged, typed abort; an entry point that doesn't end the session; `save()` stays separate | today consolidation runs only at session end (`integration/session_end.py::end_session`; `_consolidate`'s stages are skipped by `_fits` on a wall allowance) and `MaximHandle.stop` blocks on it (`console/handle.py:741`) |

**Front gate: what Maxim already has, which tier A must build on, not beside (MP-B1):** `AgentFactory` and its
`persistence_dir`; the advisor's patterns, not the advisor itself (it is a quarantine with one hard-coded tool, no
injected backend and a process-wide offline latch); `ExperienceClockDriver` and
its stepped-world declaration (#1361 S2, Q8; #1361 "adds no clock"); `seeding.py::make_agent_rng`; `_StepClock` and
`LockstepTime`, which already patch `time` for lockstep runs; `tool_failure_credit.md` (#1200, TF1–TF3) and the D53
NEUTRAL tier, which propose and settle amend; `ENTITY_FORMAT_VERSION`; `sem_interruptibility.md`. The upstream drafts
own that survey; this part only depends on its outcome.

### 6.2 What Overdrive builds now **[now: the `phase1/agents` PR]**

- **`AgentPort`: `step`, `think` and `settle`, all called by the host (O39)** (v2's host service protocol and
  `request_thought` are deleted: a callback from the adapter to the host ran the wrong way, and with requests as
  values nothing needs it).
- **`StepOutput`, `Pending`, `Reply` (with `cancelled(prefix)` and `truncated`), `ThoughtOutput`, receipts and thought
  requests** as frozen, versioned types with golden fixtures; the continuation as an opaque, versioned blob in the
  agent home, with a save/load round trip.
- **The host thinking lane** that executes request values by deadline, with the response cache, cancel as a reply,
  the wall ceiling ending a thought as `thought_failed`, and the follow-up-chain budget.
- **Speech validation and syllable stamping** over the held reply at its landing tick (streamed after OD-A25).
- **`data/agents/` timing, speech, fatigue and thought-budget files,** each loaded through a gate.
- **The scripted test double:** an agent that implements `AgentPort` from a script and runs through the real
  thinking lane, barrier and log. It is a real state machine, so the hard cases are exercised: multi-cycle PFC
  deliberation, follow-ups after receipts, `next_actions` chains, partial and cancelled replies, and stale thoughts.
  It may script fillers as fixed outputs for interface tests only, and the tests say so (OA3). Every [now] test in this part runs
  against it. It is a test double, never shipped as an NPC, and the tests say so.
- **Real Maxim** behind `engine.adapters.agents` is a **strict red gate** (`xfail(strict=True)`) until tier A ships,
  with the reason naming the missing piece. The lane never uses Maxim's router; its backends are the transports (O46, `inference_placement.md`).
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

- **One worker process per real agent (O13).** Each real Maxim agent runs in its own process, started with
  `spawn` (the offline latch refuses `fork` and `forkserver`), with a scrubbed environment, no API keys, its working
  directory and home at its agent home under the save, prefetch off, and the latch engaged after the host pipe is
  open. Model calls stay host-side, in inference gateways (O47). The process boundary contains the leak paths Maxim hasn't closed yet:
  they reach an empty directory and a refused socket, not the host (TBR-5). **The channel, the environment
  allowlist, the codec, failure handling and the test double's place behind the channel are §6.6;** v3's "test double
  in-process" and "scrubbed environment" are superseded there.
- **One owner per agent.** Its `step`, `think`, `settle`, `consolidate` and any push into its body run serialised in its worker.
  With generate vs apply nothing writes agent state from anywhere else.
- **The barrier.** The host steps tick T+1 only when every agent is **parked**: returned from `step`, `think` or
  `settle` (an agent with an outstanding request is parked, holding a `Pending`). Released work (a reply at its time,
  a receipt) runs to its next park before the tick advances, in canonical order (§9).
- **Agent isolation.** The worker process gives it by construction for real agents. Tier A still proves it inside
  one process (OD-EA6: one agent's digest is the same alone, alongside another, reversed and concurrent; DR-S5),
  because Maxim's own simulation hosts several agents in one process.
- **Meters (B5):** park and release per NPC per tick, now a channel round trip (§6.6 gives its cost, budget and levers), **pipe round trip per park** and **memory per worker** (both measured before Phase 4 commits to O13), adapter
  push and strip, thinking-lane overhead.

### 6.4 Propose, receipt, settle (Wire S12, Arch S13, X-6)

- **The engine's contract:** an intent produces one receipt: intent id, outcome kind (`applied`, `refused`, `stale`,
  `cancelled`), `apply_tick`, the measured effect, and the before and after frame ids.
- **Each receipt is credited exactly once,** through `settle`, and zero times when `stale`. A test asserts it. Under
  O6 there is no second path (`execute`'s return) to double-book, once Maxim folds its parallel and agent-fallback
  dispatch into the same split (`tool_dispatch.py:1290-1291`; TBR-6).
- **Every minted pid settles exactly once (Maxim's review of v5; OD-EA16).** Each invocation pid an agent mints
  comes back in exactly one terminal receipt, executed or a typed refusal; no receipt arrives without a minted pid;
  a refusal receipt is the pid's outcome, not a physical event, and a refusal's pid never appears in a GL3.B2 row
  (Maxim's review of v6). The host's refusals, deferrals past a budget and
  drops all end in a typed refusal receipt carrying the pid, so none is orphaned; a dead worker's in-flight pids get
  `agent_failed` refusals (O44).
- **Settle feeds NAc's existing eligibility traces,** not a second credit path. Dispatch/settle is an engineering
  refactor behind a bit-identical state-digest parity guard, with robots settling right after dispatch; delayed settle
  happens only when a host chooses it (O15a). A delay sweep that measures credit accuracy must include intervening
  actions, or the measurement is trivial (BD-19).
- **Slow effects.** Ignite's effect arrives over many physics steps. Credit at a single settle frame learns "ignite
  barely changes temperature". Until tool-level settle can carry a horizon (OD-A16), slow-effect credit is an **OPEN
  divergence; a red gate will hold it once the agent PR lands one.** The sensors used for credit are restricted to those the affordance declares it
  affects, so an entity dominated by an ongoing process (a crate in a fire) doesn't train the cerebellum on the
  world's drift (BF2-3).
- **The credit path never reads instruments.** Per-actor binding gives each NPC perceiver-relative sensors, so B-13
  and credit agree (Arch S13).
- **Stale is context, never credit** (lesson 9). Maxim books every `success=False` as NEGATIVE. The refusal-kind key
  (OD-A16) must be **promoted** through the bridge, because `agents/tool_bridge.py:580-582` drops `result.metadata` on
  failure and `runtime/tool_dispatch.py:370` books NEGATIVE before any valence is read; the same holds for any settle key
  (X-6). Until then, stale refusals are an OPEN divergence, to be held by a strict red gate once the agent PR lands it,
  and the receipt goes to the next thought's context.
- **A malformed call is a cognitive error, not a tool failure** (lesson 7).

### 6.5 Per-actor binding and identity (TB2-S8, MP-S12, Arch S3)

- Each NPC gets its own entity and modulator, bound to its actor; `name` and `full_path` stay identical across actors,
  since the cerebellum and NAc key on them (lesson 10).
- **The adapter refuses a call whose modulator's bound actor isn't the agent it is stepping.** Test: two NPCs and a
  deliberately shared entity go red without the check.
- **The membrane factory takes a frame source and returns intents in `StepOutput`, never `World`** (`boundaries.md`
  §7.1; the v2 intent sink is deleted, O6a).
- **Maxim-side:** an acting-entity context reaches `execute` only **opt-in**, declared by the modulator (for example a
  class attribute `accepts_actor = False` that the bridge checks). Injecting a new key into every modulator's
  `params` would make strict modulators, Overdrive's included, refuse every call after an upgrade (MP-S12).

### 6.6 The contract's edges (v3.1; the npcs_v3 review)

v3 named the mechanisms; the five-lens review of it (`reviews/npcs_v3/`) found where their edges weren't pinned. This
section pins them. Where it and an earlier section differ, this section wins, and the earlier text points here.

**The worker channel is a registered gate (Exec B1, TB3-B1, Arch S4, S7; `boundaries.md` §5.3, §5.4)** **[now]**
- **The process:** `subprocess.Popen([sys.executable, "-I", "-m", <worker entry>], env=<allowlist>,
  cwd=<agent home>, close_fds=True, pass_fds=(<child end>,))` over a `socket.socketpair()`. Never `multiprocessing`:
  its `Connection.recv()` unpickles, so a compromised worker could run code in the world server. The determinism and
  isolation scans ban `multiprocessing`, `pickle`, `marshal` and `shelve` in `engine.host` and `engine.adapters`.
- **The environment is an allowlist, not a scrub:** nothing from the host's environment passes except the variables
  the worker needs, each named: `PYTHONHASHSEED` (pinned per run and recorded in the log header), `OMP_NUM_THREADS`,
  `OPENBLAS_NUM_THREADS` and `MKL_NUM_THREADS` = 1 (recorded), and a minimal `PATH`. No keys, no `HOME`, no `MAXIM_*`:
  v3.1's interim `MAXIM_DATA_HOME` is dropped, since Maxim's A4 waits for A1 (`AgentHome`) (Maxim's plan review). The offline latch engages after the channel opens.
- **The codec:** length-prefixed frames, each a versioned, closed-schema JSON object through the strict decoder
  (`boundaries.md` §10), with size budgets checked before allocation. Message kinds are closed per direction: host to
  worker `step`, `resume`, `settle`, `consolidate`, `save`, `load` (every spawn begins with it, carrying the function envelopes), `shutdown`; worker to host `step_output`, `pending`,
  `thought_output`, `ack`, `error(code)`. Each intent in `step_output` carries its invocation pid (opaque to the host; null until Maxim's
  G17 stage builds `PhysicalEventId`, then any non-null value that isn't a pid is refused);
  each receipt in `settle` and each event in `step`'s frame that an intent caused carries it as `caused_by`. An unknown kind, field or version ends the agent (below).
- **One actor per channel,** bound at spawn: every frame's actor id must equal it.
- **Everything from the worker is untrusted input.** Stage 1 (`engine.intents.parse_action`, the guest-text gate, the
  memory-write gate) runs **in the host** on decoded values. `boundaries.md` §5.4's assumption that Maxim objects need
  no input primitive no longer holds across the process: an `Entity` target arrives as a stable id and is re-checked
  in the host. The agent-owned continuation body (below) is bytes the host stores and returns, never decodes.
- **Tests [now]:** golden rejection frames for every refusal; a planted pickle frame refused without being
  unpickled; a frame from the wrong actor refused. **The test double runs behind this channel in a spawned worker,**
  so every [now] determinism test exercises the shipped path: spawned workers, the codec and the barrier's merge
  (DET-S3).
- **A hung or dead worker never freezes the world (Arch S6, TB3-S10, DET-S4).** A worker that doesn't park within the
  host's per-park wall ceiling (`data/agents/thought_budget.yaml`), exits, or sends a refused frame is killed. The
  host logs `agent_failed(npc, reason = hung | crashed | protocol)` as a record, treats the NPC as parked and inert
  (its body processes go on; it takes no actions), and flags the run tier 3. Restarting it from its last saved home is
  an explicit host control record that opens a new log segment (O45; its in-flight pids: §6.4, O44).
- **The worker is a container, not a sandbox (TB3-S6).** It runs as the user and can read what the user can. It
  contains the paths Maxim's code takes by default (working directory, home, environment, keys, outbound network); a
  hostile process needs an OS sandbox (macOS `sandbox-exec`, Linux seccomp and namespaces, Windows AppContainer).
  Proposed for the owner (§12.1 item 1): with guests present, real NPCs need the OS sandbox too, and on a platform
  without one (Windows today) guest sessions with real NPCs are refused.
- **The host never latches itself (TBR-4, TB3-S7).** The host refuses to start with `MAXIM_OFFLINE` set in its own
  environment (a start-up check, **[now]**), since `import maxim` would latch the world server. Once the adapter is
  split, the host imports Maxim's types only through `simcore/adapters/sem/_compat.py`, and `maxim` itself only in workers and inference gateways.
- **Its cost (Exec S4):** every park is a round trip. 20 NPCs × 200 ticks per wall second × 50–200 µs per round trip
  is 0.2–0.8 wall seconds per second spent on the barrier alone, enough to make 20× unreachable. B5 gets a budget for
  it, and the levers are: only agents due this tick (by rate divisor, §2.1) get a round trip; frames go as deltas;
  idle agents step at a coarser divisor. Inlining agents back into the host would undo O13, so it is a design decision
  against O13, not a measurement (Arch N1).

**Who writes, and who owns the continuation (Arch B1, B2, S1)**
- **The port, in one signature (Exec N7, Arch N3, DET-N1).** Overdrive's `AgentPort`, in integer ticks:
  `step(now_tick, dt_ticks, frame) -> StepOutput`; `think(handle, reply | None) -> Pending(request) | ThoughtOutput`;
  `settle(receipts, writes) -> ack` (O39). Maxim's embedded function is `step(agent, world_dt_us, frame)`;
  the adapter converts ticks to microseconds through the fixed schedule (§9).
- **`settle` is the only writer, host-called (O39).** Memory writes, retrieval strengthening (below) and any other
  store change leave `step` and `think` as values. The host gates them (own memory only, provenance stamped, budget),
  orders them canonically (§9), and passes them to `settle` with the receipts; `settle` applies writes and credit by
  publishing through Maxim's agent bus, never into the stores directly (Maxim's cand. A6, under B2's digest).
- **The continuation is split by owner.** The **host-owned header** is a frozen value the host keeps and never sends
  out to be returned: thought id and kind, the triggering input id, the budget counters, the PFC cycle index and
  `max_cycles`, `basis_seq` (O38), each segment's modelled landing tick, cancel status and the
  delivered prefix, and any `held_reply` (text and provenance, `inference_placement.md` §4.2). The **agent-owned body** (the partial proposal, the transcript, enrichment results, the loop
  locals that aren't values yet) stays in the worker, saved in the agent home, and reaches the host only as opaque
  bytes for saving. The host enforces budgets from its header, so a guest-injected follow-up chain can't reset them;
  a worker reply that contradicts the header is a protocol error.
- **The lifecycle, end to end:** a thought request (from `StepOutput` or a follow-up) is stamped by the host with its
  kind's deadline, priority and landing ticks (outside the cache key; DET-N2, Arch S5) → the model call runs in the
  host's thinking lane → the host holds the reply → at the segment's landing tick the host resumes `think` → either
  another `Pending` (the next PFC cycle, counted) or a `ThoughtOutput` → its intents, speech and writes pass their
  gates → intents apply in the world → receipts → `settle` with receipts and gated writes → any follow-up is a new request
  under the same triggering input's budget.
- **Staleness is Maxim's hybrid §A.1b.5 (O38).** A reply is stale only when a non-self-caused event on a tracked
  right arrives after `basis_seq`, the agent's afferent-scheduler high-water seq (Maxim `thalamic_relay.md` §5.5,
  `preempted_since`): the header holds a copy, never computes it, and LLM-proposal staleness waits on GL3.B7.
  Tracked rights are declared preemption rights (TR6; today only `nociceptive_fast`'s); a non-danger track counts
  only when a plan rung names it (Maxim's owner). **The embedded efference copy:** attribution (GL3.B2's pid join,
  `thalamic_relay.md` §5.2) works only if every receipt and frame event an intent causes carries its pid (the codec
  above; `tile_and_client.md` §3.1). B2's dispatch, the `_run_started` equivalent, draws it from the agent's own
  `EventSequencer` inside the worker: the sequencer owns the mint, GL3.B2 the contract, and the host only copies it.
  The executor's `invocation_id` (`uuid4`, `executor.py:512`) is never the pid or a join key. On a stale reply the agent returns a re-plan `Pending` (counted) or `ThoughtOutput(abandoned)`. Tracked-right
  events reach the agent through `step`'s frame; Maxim keeps this out of B2.

**Determinism at the edges (DET-B1 to B3, S1, S2, S5 to S7)**
- **`think` resumes only at the segment's modelled landing tick,** never when the reply arrives. A reply that arrives
  early is held by the host. One that arrives late, under dilate, lands at the tick the world waited at; under
  floor-holding, the tick it lands at is logged as `reply_landed(thought, tick)`, a host record a rerun consumes.
  Test: a plant that resumes on arrival makes a rerun with instant cached replies diverge, and goes red.
- **`cancelled(prefix)` and `truncated(prefix)` carry the delivered speech** (reasons: `inference_placement.md` §2.6)**:** the host-validated syllables already
  emitted to the world by the cancel tick (§5.3), in world time. Tokens streamed beyond them are discarded and never
  reach cognition (TB3-S5). A chunk the guest-text gate refuses mid-stream ends the reply as
  `truncated(prefix, reason=validation)` (Arch N6).
- **The planted-render guard plants in the machinery clock** (an instant with unusual seconds, TZ pinned, checked in
  raw, clock, date and duration forms), and adds an **offset test end to end, offset and scale only at render level on a frozen store**
  (erratum 2026-11-19: a scaled machinery clock legitimately changes decay end to end): runs whose machinery clocks
  differ, with identical perceived-time bins, must render byte-identical prompts. That catches a
  rendered duration (`f"{now - t:.0f}s ago"`) and a rendered order, which a sentinel instant can't (BF3-7).
- **Floor-holding events are host records:** `floor_event(npc, filler | account | yield, tick, cause = modelled |
  lateness)`. A run with any lateness-caused event is tier 3 for reruns; tier-1 replay reads the records (DET-S1).
- **Cache repeats are numbered in canonical order** (by thought request id), not execution order, so two NPCs with
  byte-identical requests can't swap answers on a rerun (DET-S2).
- **Resume equivalence:** saving and loading an agent mid-thought, then continuing, gives the same digest as a
  continuous run; tested with the double [now] (DET-S5).
- **No lateness reaches cognition as time.** A listener's percept carries hesitation as a coarse perceived category
  from the perceived-time port, and only for the **modelled** part of a gap; lateness-caused extension is never
  written into another NPC's memory (DET-S6, BF3-4). Fatigue load counts modelled phase durations, never real or late
  time (DET-S7).
- **One derivation for Maxim's agent randomness (Exec S3, DET-N4; O40):** `make_agent_rng` with a stream argument
  (until it exists, `agent_id` is `"npc_key:stream"`), keyed by the persisted NPC key, never Maxim's ordinal, with
  `base_seed` from the log header's root. Each stream's state is saved pickle-free in the agent home. Overdrive's own
  streams stay §3.4's tree.
- **Replay ids and the step thread (O43, O45).** `session_id` comes from the log header (root id, NPC key and
  segment number; each restore opens a segment); the sequencer's
  high-water seq is saved in the agent home (save v1, Phase 4). Maxim
  scopes determinism to single-threaded loop paths (`thalamic_relay.md` §5.5): one worker per agent, stepped by one
  thread, is inside it, so never a pool of agents per worker thread.
- **The machinery clock's zero (DET-N5):** world µs map onto Maxim's seconds with a fixed nonzero offset until
  OD-I1 lands, since 0.0 makes five `x or time.time()` sites swap in the wall clock.

**The model has more doors than `think` (Arch S2)**
- `AdaptivePlanner(llm=...)` (`runtime/bootstrap.py:623`, calling `adaptive_planner.py:487`), the `ToolPainBridge`
  reflection on the settle path (`tool_pain_bridge.py:806`, its error swallowed) and `FearAgent(fear_llm)` (`_analyze_with_llm`,
  `fear_agent.py:317`) call a model outside `think`. **The worker holds no model backend at all,** so each such call fails closed, and a test asserts the
  refusal; each becomes a request through the cut, or is off on the embedded path. OD-A17 names them.
- **Cognition tools inside `think` would be an inner tool loop** (Maxim's cand. C1 question; Arch S3; erratum 2026-11-19: was "C10"). Until Maxim decides
  it by experiment, cognition tools go through follow-ups like world tools. If adopted, each resolution is a counted
  cycle with a modelled cost.

**Parse failures and guest text (TB3-S1, S3, S4, N4)**
- **Any parse failure ends the thought as `thought_failed(reason=parse)`.** The parse-failure template does echo the
  guest's words (`'{question}'` from `triggering_input`, `agents/llm_fallback.py::generate_llm_fallback`, `:267`, templates
  `:296-304` on f0b1cea4; after #1691 a fallback books no NAc credit, but still echoes), so the embedded path never reaches it, for any reply, not only cancelled ones. OD-A17 says so.
- **One gate for guest text, `engine.text.player_text`,** used by `speak` and by every guest-supplied string that can
  reach a prompt (display names, imagined-object labels, written text in the world). It checks the **decoded** text
  (after JSON unescaping, so an escaped U+2028 is caught), per chunk and whole, and refuses controls, bidi overrides,
  every line separator `str.splitlines` splits on, and every format (Cf) character, including zero-width characters
  and the tag characters U+E0000–U+E007F.

**Memory provenance (O14 gate 5; TB3-S2)**
- Every memory write carries the set of actors whose words it derives from, each with its session id and the host's
  index (TBR-8), so a purge can target one guest in one session. A derived write (concept extraction, a
  summary, another NPC repeating it) carries the union of its sources' sets. Purging an actor removes every record
  whose set contains it. Exit test: a guest's line, relayed by a second NPC and extracted into a concept, leaves no
  trace after a purge. OD-A18's generate vs apply carries the field; the purge is an Overdrive gate, its types in
  `phase1/agents` and its behaviour in Phase 4.

**Receipts have two projections (Arch N4).** `settle` gets the full receipt (`apply_tick`, the before and after
frame ids, the measured effect) for credit and traces. The follow-up prompt gets a projection the host builds with
every time field stripped (§3.1): outcome kind and measured effect only.

**Budgets (TB3-S9)**
- The chain budget is per triggering input **and** per NPC per world minute, so thoughts without a speech trigger
  (percepts, idle) are budgeted too, and a new message doesn't reset the window. Holds are rate-limited per speaker.

**Biology at the edges (BF3-1 to BF3-6, BF3-8)**
- **Credit's real dependency (BF3-1).** NAc's eligibility traces decay by ×0.9 **per loop tick**
  (`decisions/nac.py:3707` `decay_eligibility`, run from `_loop_bio_tick_maintenance`, `runtime/agent_loop.py:800-840`,
  with five sibling decays), not on the wall clock; `nac.py:1162` is the 300 s causal-link buffer. So credit depends
  on how often an agent ticks. NAc normalises credit, so a lone trace is credited fully at any step rate (the "13×"
  figure an earlier draft gave was wrong); the real step-rate effects are how credit is shared among traces and when a
  trace expires into the temporal-anchor fallback, which reads the host clock (`nac.py:3625-3640`, `:3715`).
  Dispatch/settle (OD-A18) depends on Maxim's own experience-time decay (#1361 S3a and S3b, our OD-A1), with the
  anchor similarity's calendar read as OD-A20, declined (§12.2); OD-A19 was a duplicate. Its exit test credits several
  traces at two divisors and checks their shares match. Our earlier claim to Maxim was corrected in
  `reviews/maxim_response_1/correction_1.md`.
- **The settle horizon (BF3-2):** dopamine's 0.3–2 s window (Yagishita et al. 2014, *verified* in BD-19) supports
  immediate credit only. A horizon of seconds to minutes for slow effects (OD-A16) is `[engineering]`; its route is
  NAc's 300 s causal-link buffer, named, not the traces.
- **Yield timing (BF3-3):** Jefferson's ~1 s (1989, *to verify*) is about **unfilled** silence. The yield fires after
  about 1 s of silence following the last filler or account, not 1 s from the turn's end; the account's onset is a
  parameter in 600–1000 ms (`[engineering]`: our 600–700 ms, Maxim's ~1 s).
- **At the design's own latency, live replies yield (BF3-4).** With L = 3 s every live reply passes the yield, so
  O11a's yield is the common path, not the exception. **Known gap:** players hear lateness as reluctance (Roberts et
  al. 2006, *verified* in BD-4) and no NPC-side rule can hide it; the fix is latency (the first-token and overlap
  levers of §4.5). The listener-side rule above keeps it out of other NPCs' memories.
- **P1c counts (BF3-5):** a deliberation cycle's modelled duration × its kind's weight enters mental-fatigue load
  (§2.3, §4.6), and the speed trait (O12) scales P1c's modelled cost as it scales onsets.
- **Retrieval strengthening survives a host-called `think` (BF3-6):** a recall inside `think` returns a `retrieval`
  write (the trace ids reactivated) stamped at the cycle's modelled time, applied at `settle`, so the testing effect
  holds without `think` writing.
- **Planning during the other's turn (BF3-8):** Bögels et al. 2015 and Castellucci et al. 2022 (*verified* in BD-9)
  support starting to plan in overlap (OD-H4, folded into OD-H5), not the filler repertoire itself; §5.1 is read so.

**Fairness and naming (BF3-9 to BF3-13)**
- Clark & Fox Tree 2002's *uh*/*um* signalling is contested on acoustics (O'Connell & Kowal 2005), and it is what
  picks the first filler, so the choice is a parameter with that caveat. Kendrick & Torreira 2015 is a production
  statistic; the perception claim is Roberts et al. 2006. Bortfeld et al. 2001 is *verified* (abstract, BD-5); a
  per-NPC filler-propensity trait joins §12.1 item 5. "PFC deliberation" is Maxim's ANALOG label, not a prefrontal
  claim of ours.
- Tests written now with the double: a filler-only turn adds zero utterance records and zero credit events while the
  listener's percept carries the hesitation category (BD-6); the settle path stamps the chooser and excludes yields
  (BD-19).

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
| OD-I1 | `x or time.time()` turns world time 0.0 into the wall clock, at five sites | §1 | an issue now |
| OD-I2 | `ModulatorResult` has no CC3 declaration; downgraded to a docstring nit (it is an in-process value) | §6 | a nit |
| OD-I3 | the pickle-capable embeddings load, dormant by default, on a global file | §6.1 | an issue now |
| OD-A1–OD-A9 | the world-clock work: #1361 S3–S6, `AgentTime`, prompt and observation time (with `context_pool`), stamps, the de-duplication window, dispatch gates, ids, the stepped Default Network | §1, §3.1 | additive; defaults reproduce today's values |
| OD-A10–OD-A12, OD-A14, OD-A15, OD-A17, OD-A18 (OD-A13 moved to OD-I3; OD-A19 withdrawn) | the embeddable agent: the entry point, the closed tool roster, `AgentHome`, the request/reply cut, the stepped `think` and its continuation, the leak closure, the dispatch/settle split | §6.1 | additive; the stepped `think` after 1.4.0 (O15a) |
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
| OD-H1–OD-H3, OD-H5 | the hybrid line as a test bed; modelled latency for the hold; the G4 re-key; the turn-taking substrate, which folds in OD-H4 (deliberation during the other speaker's turn) | §5.1 | Maxim's hybrid plans |

### 8.2 Upstream asks this fold reveals

Most are now roadmap Phase 3 rows (the Phase 3 fold added them); the rest are for that fold to place.

| Ask | Roadmap |
|---|---|
| The embeddable agent contract: entry point, closed tool roster, `AgentHome`, the request/reply cut, the stepped `think`, the leak closure, dispatch/settle | OD-A10–OD-A12, OD-A14, OD-A15, OD-A17, OD-A18 |
| `context_pool.py:468, :493` in the prompt and observation time row, with no host time zone | OD-A3 |
| A world calendar on the injected clock, or "no calendar" (X-9, BF2-7) | OD-A2, OD-B13 |
| A per-modulator valence default instead of D53's silent POSITIVE (BF2-3) | OD-A16 |
| A mental-fatigue drive; `CouplingSpec` can't carry graded load (BF2-1), arguing against the SHAPE-FROZEN rationale about `extra` (fair about `extra`, but the shape fixes coupling as binary) | OD-B12 |
| Embedder-supplied modelled latency for the learned hold window | OD-H2 |
| Deliberation started during the other speaker's turn | OD-H5 (folds in OD-H4) |
| **Keyed RNG substreams,** not sequential ones (DR-S4, BD-13) | OD-A7 |
| **Step-size-invariant decay,** with its exit test (X-11; BF3-1 makes it load-bearing, since NAc's traces decay per loop tick) | OD-A1 (#1361 S3a, S3b; OD-A19 withdrawn as a duplicate), the anchor similarity OD-A20 (declined by Maxim's owner, §12.2); exit test OD-EA12 |
| **Retrieval strengthening as a returned write** on a host-called `think` (BF3-6), arguing against the draft's read-only think as Maxim accepted it | OD-A15 |
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

**Paired replays (DET-N3, BD-16):** a paired analysis estimates d_z, not d, and the seed stays the unit; the estimand
(a paired JZS on d_z) is pre-registered, and each pair reports its divergence tick, the first tick at which the two
arms' states differ, so a reader can see how much of the run the pairing actually covered.

Without floor arms, either experiment could reach only `PARTIAL (narrow: floor matched)` under Maxim's BF2 rule
(2026-10-10). The refractory and habituation curves are manipulation checks. Both go to `docs/experiments/` only after
a four-lens design review.

**When a game-earned result can move a Maxim claim (BD-17, Arch 4.6).** Only through a Maxim-owned harness, under a
pre-registration frozen before data, with engineering invariants (bit-identical replays, parity digests) kept apart
from behavioural claims, which stay PARTIAL until a transfer check passes on a Maxim-owned task or the robot, and with
every world-only affordance declared. The caution cuts both ways: Maxim's robot defaults never become game constants;
floor thresholds, *h* and filler timing are per-world parameters on the listener's clock.

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

### 11.3 In v2 of this part (after Maxim's answers)

v3 replaced v2's split `AgentPort`, host service protocol and `request_thought` with three host calls (§6.2, O39),
its cancellable backend with the request/reply cut (§6.1), tool-call caps with PFC cycles and follow-up chains
(§4.7), one injected clock with two (§6.1), and in-process agents with a worker per agent (§6.3).

## 12. Open questions and divergences

### 12.1 For the owner (items 1, 3, 4 and 5 answered or deferred by name in O30, 2026-11-17)

1. **Guest sessions with real-Maxim NPCs: decided (O14).** They wait for five gates: the worker process (O13); a
   no-effect test; a dialogue-level bypass test (prefetch, the deleted shortcut as a regression target, the parse-failure template, phrase commands,
   which trigger on "maxim", the name of our world); line separators refused in `speak`; and memory provenance by
   speaker with a purge path. Provenance and lane-decision JSONL currently write guests' words into the owner's
   `~/.maxim` (TBR-13), which `AgentHome` and the worker's environment allowlist close. Maxim deleted the shortcut
   (#1689). **Each gate now has a home**
   (§6.6; roadmap Phase 4): a strict red gate refuses guest joins while real-Maxim NPCs are live until all five tests
   pass, owned by `phase1/protocol`. The sixth gate, remote model egress, is O18; the OS sandbox is deferred by name
   (O30).
2. **Local or remote LLM: decided (O18;** TB2-S9).
3. **The stale-refusal fix gates Phase 4.** Roadmap Phase 3's exit now requires OD-A16, so the first NPCs never learn
   from stale refusals (Arch S14). Confirm that ordering, since it puts the credit amendment on Phase 4's critical
   path.
4. **Bug reports and dialogue.** `speak` text is redacted from bug reports by default (§5.2). Is that the right
   default, or should the reporter choose?
5. **The speed trait's structure (O12), from `research/speed/individual_differences.md`.** Proposed:
   - **Age shifts the median, not the spread.** Decision onset slows about 0.5–0.8% per adult year, simple responses
     about half that; spread within an age doesn't shrink (*verified*: Der & Deary 2017, Woods et al. 2015).
   - **One general factor plus a residual per domain** (decision onset, speech onset):
     `m = exp(σ·(λ·z_g + √(1−λ²)·z_d))`, λ ≈ 0.75 (simple and choice RT correlate 0.59, about 0.75 corrected for
     reliability; *verified*, the λ form `[engineering]`).
   - **Turn gaps come mostly from the dialogue and the pair, not the speaker.** In the Fisher corpus the pair explains
     41.5% of a speaker's gap variance and the speaker 12.8% (*verified*: Cavalcanti & Skantze 2025). The trait gets a
     weak loading on gaps at most; no study links lab speed to conversational gaps.
   - **Filler propensity** (`[engineering]`, BD-5, BF3-11): a per-NPC trait for how often an NPC fills a pause, from
     the same keyed draw, since filler rates differ between speakers (Bortfeld et al. 2001, *verified* abstract).
   - **Optional slow tail** (`[engineering]`): real populations have a heavier slow tail than a lognormal; a small
     slow group (about 5% of NPCs, twice the sigma) would give it.
6. **Phase 4's interim live-play policy: decided (O16);** its numbers are §4.5's.
7. **Retention of guest speech agent-side (TBR-13): decided (O17, O26).**

### 12.2 Known OPEN divergences (each with a red gate when there is code)

- **Inference placement's divergences** are owned by `inference_placement.md` §6.2.
- **Co-op lateness is heard (O27):** until OD-H5 and latency close it, a co-op listener hears a late NPC's whole
  silence, modelled part and host lateness together, so the host's speed reaches other NPCs' memories. Accepted as
  a known gap; the alternative was an oracle.

- Real Maxim reads the host clock on the live path (608 `time.time()`, 145 `time.monotonic()`, 20 `datetime.now`
  on 7084f561); determinism closes with tier A's machinery clock on the ~30 step-path files.
- Real Maxim's prompt carries host time, time zone and the workspace manifest. **This closes only with the
  perceived-time port and the planted-render test, not with the machinery clock** (BD-15), so landing tier A's clock
  doesn't retire the O4 gate.
- The prompt and dial-invisibility tests against real Maxim; red until tier A.
- Two clocks reach one agent (the membrane stamps world seconds, Maxim's sensors epoch seconds); closes with SEM S2
  and OD-A2.
- Memory writes are ungated LLM output until generate vs apply (OD-A18) gives the game a value to check, through the
  host's `settle` (§6.6; TB2-S3).
- Memory authority ("an NPC writes only its own memory") is OPEN until per-agent homes and pickle-free persistence
  land (TB2-B2).
- Stale refusals book NEGATIVE; closes with OD-A16.
- Slow-effect credit; closes with OD-A16's settle horizon.
- The NPC is a statue while a thought is in flight; closes with the hybrid line's substrate.
- Real NPCs wait for the stepped `think` (O15a); until then every agent test runs on the test double.
- LLM-bypassing replies on the core path (prefetch, and the parse-failure template, which does echo the guest's
  words; Maxim deleted the short-question shortcut, #1689); closes with OD-A17, whose parser bypass covers every reply, not only cancelled ones
  (TB3-S1), and the worker process contains them meanwhile.
- Credit depends on the tick rate, because NAc's traces decay per loop tick; closes with OD-A1 (#1361 S3a), the
  anchor fallback's age and expiry with S3b; its similarity's calendar read stays (next item).
- **Delayed credit follows the host's calendar and timezone (OD-A20, declined by Maxim's owner 2026-11-19).** NAc's
  anchor path credits a node whose trace has expired (below 0.01: 44 passes at ×0.9, 1.5–4.4 s at 10–30 Hz today,
  about 22 s of experience time after #1361 S3a) by `0.3 × similarity × activation`, counted only above 0.01
  (`decisions/nac.py:3622-3640`); the similarity compares host-calendar signatures (circadian, weekly, monthly
  `(day−1)/31`, annual). Credit is normalised, but the calendar moves more than sharing (v3.2's erratum was too
  narrow; Maxim's delta review): (a) it can drop a node below 0.01, so a receipt whose only node drops books nothing;
  (b) anchor-only nodes set at different host times split differently; (c) `TemporalSignature.from_timestamp` uses
  local time (`time/temporal_signature.py:60`), so a local midnight (similarity about 0.018 lower) or a DST change
  moves credit, and **a replay in another timezone differs** (OD-WC1). The 300 s window is wall time today
  (`nac.py:3715`), so a pause past it prunes the anchor until #1361 S3b. Anchors are session-scoped (`nac.py:875`).
  No workaround (no faked time or pinned `TZ` in production). Recorded from Maxim's code and our arithmetic, not a
  run: two strict red gates will carry the evidence to re-raise OD-A20 once the agent PR lands them
  (`checklists.md`). Phase 4's replay exit carries this divergence.
- **What an NPC forgets follows the wall clock** (Maxim's delta review; stays with #1361 Q5, which keeps it as a
  stated inconsistency). `Hippocampus.sleep` scores retention on `time.time()` against `accessed_at`
  (`memory/hippocampus_consolidation.py:117`). On the default access-based strategy (score `0.5 × (1 − age/7 d) +
  0.2 × min(1, accesses/5) + 0.3 × min(1, edges/20)`, removed below 0.3), a memory accessed once with no edges is
  removed once its access is more than 3.36 wall days before the pass; with 20 edges it is never removed. So a
  paused week erases such memories, and a replay paced unlike the live run forgets differently. No workaround.
  Recorded from the code and arithmetic, not a run; a strict red gate will carry it once the agent PR lands it.
- Model calls outside `think` (`AdaptivePlanner`, the `ToolPainBridge` reflection, `FearAgent`); they fail closed in
  the worker, which holds no backend, and close with OD-A17.
- Maxim has no turn-taking substrate (gaze, backchannels, fillers, floor-holding); closes with OD-H5 if Maxim takes it
  (OA3, revised).
- The SCN phase is an oracle (host calendar today, exact world phase after tier A); closes with OD-B8 if OD-X1 earns it.
- Weekly, monthly and annual phases are calendar oracles; Overdrive declares them off.
- The coarse interim time readout is an `[engineering]` ANALOG until the senses are earned.
- Region sensors are omniscient; they are test and lab instruments only, until B-13's perceiver half (Phase 4).
- Outcome class is not promised across model profiles (§4.1).

### 12.3 Source inconsistencies

- v1's §12.3 note that `boundaries.md` §9.3 still carried two wrong asks was stale at 4f7a754 and is removed.
- The counts are settled (X-3), and both sides now agree: on Maxim `main`, 36 `uuid4` code lines in 24 files, 27
  global-`random` calls, 36 `default_factory=time.time` stamps in 19 files (plus one `time.monotonic` at
  `tools/registry.py:146`). The roadmap's "39 global `random`" had no basis. The count of `MAXIM_*` names read depends
  on the search pattern (122–213); "far more than 50" is what holds.
- The skeptic's brief drew perceived-time noise from "the world RNG"; the per-NPC streams of §3.4 supersede it.

## Fold table: the foundations review (`reviews/foundations_v1/`)

Every BLOCKER and SHOULD-FIX that touches this part. Status is **folded** (with the section), **partial** (what is
missing), or **elsewhere** (the document that owns it).

| Finding | Severity | Status |
|---|---|---|
| Arch B1 the agent lane is defined nowhere | BLOCKER | folded: §6.3, §11.1 |
| Arch B2 mode (a) + dilation deadlock | BLOCKER | folded: mode (a) dropped (O6); §4.4 DLP-B2 fixes and no-deadlock invariant |
| Arch B3 `AgentPort` isn't Maxim's thought seam | BLOCKER | folded: §6.1 gateway, §6.2 port split *(superseded by `npcs_and_sem.md` O6a and v3.1 §6.6: one host-called port; intents return in `StepOutput`; the gateway is the host's thinking lane)* |
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
| Wire B2 mode (a) can't reach the pipeline | BLOCKER | folded: mode (a) dropped; §6.2 intent sink as a required port *(superseded by `npcs_and_sem.md` O6a and v3.1 §6.6: one host-called port; intents return in `StepOutput`; the gateway is the host's thinking lane)* |
| Wire B3 no Maxim thought entry point | BLOCKER | folded: §6.1, §6.2 *(superseded by `npcs_and_sem.md` O6a and v3.1 §6.6: one host-called port; intents return in `StepOutput`; the gateway is the host's thinking lane)* |
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

## Fold table: the last two review rounds (`reviews/maxim_response_1/`, `reviews/npcs_v3/`)

Generated by `reviews/npcs_v3/foldtable.py` from the ids in both rounds' lens files. It refuses an id without
a row, a row without an id, and a folded or partial row that names no section or roadmap row. The round-1
statuses were re-checked against the npcs_v3 review, which found v3's table overstated (it claimed 87
folded; the lenses put it at about 80): those rows say what v3 lacked.

| Lens | Id | Status | Where, or why not |
|---|---|---|---|
| maxim_response_1/bio_determinism | BD-1 | partial | §5.1, roadmap OD-H5: its own plan, not `learned_hold_window`; the fixed-in-v1 yield deadline (learned only with a social cost) is left to the OD-H5 plan |
| maxim_response_1/bio_determinism | BD-2 | folded | §5.1 |
| maxim_response_1/bio_determinism | BD-3 | folded | §4.4, §6.6 (the acoustics caveat) |
| maxim_response_1/bio_determinism | BD-4 | folded | §0 (O11a), §4.4 (the lateness meter), §6.6 (the listener side and the Known gap; v3 had only the speaker side) |
| maxim_response_1/bio_determinism | BD-5 | folded | §5.1, §12.1 item 5 (filler propensity) |
| maxim_response_1/bio_determinism | BD-6 | folded | §5.1, §6.6 (the structural rule's test, written now; v3 lacked it) |
| maxim_response_1/bio_determinism | BD-7 | folded | §0 (O11a), §4.4; its citation corrected after Maxim's second answer (Stivers & Robinson supports the order only) |
| maxim_response_1/bio_determinism | BD-8 | folded | §5.1 |
| maxim_response_1/bio_determinism | BD-9 | folded | §5.1, §6.6 |
| maxim_response_1/bio_determinism | BD-10 | folded | §5.1, roadmap OD-H5 |
| maxim_response_1/bio_determinism | BD-11 | folded | §6.1 (the clock seam), roadmap OD-A2 |
| maxim_response_1/bio_determinism | BD-12 | folded | §6.1, §6.6 (the sentinel in the machinery clock, the offset-and-scale test), roadmap OD-A2, OD-A3 |
| maxim_response_1/bio_determinism | BD-13 | partial | §3.4, §6.6: isolation across NPCs and streams holds; within a Maxim stream draws stay sequential, so a cadence change shifts them, an accepted cost recorded in §3.4 (v3 marked this folded) |
| maxim_response_1/bio_determinism | BD-14 | partial | roadmap OD-A2 (an advancing fake clock, a static ban on `time.*` and `datetime.now`, a long-horizon run), OD-A7 (`time_ns` ids); decay on load, `monotonic` stamps across saves, thread and set order, embedding floats and LLMs at T = 0 are in no design row, and `reply.md` §5 doesn't list the last two |
| maxim_response_1/bio_determinism | BD-15 | folded | §12.2 |
| maxim_response_1/bio_determinism | BD-16 | folded | §4.8, §10 (d_z pre-registered, divergence tick per pair) |
| maxim_response_1/bio_determinism | BD-17 | folded | §10 |
| maxim_response_1/bio_determinism | BD-18 | partial | roadmap OD-H6 (the wall interval on the machinery clock now; escalation later); the idle-DMN second trigger and a world-time refractory are not yet written |
| maxim_response_1/bio_determinism | BD-19 | folded | §6.1, §6.4, §6.6 (the chooser stamp and yield-exclusion test; credit's real dependency), roadmap OD-A18, OD-A19 |
| maxim_response_1/trust_boundary | TBR-1 | folded | §6.1 (the leak closure), roadmap OD-A17 |
| maxim_response_1/trust_boundary | TBR-2 | folded | §6.1, `embeddable_agent_DRAFT.md` §3 (three tests plus a static ban, with named packages) |
| maxim_response_1/trust_boundary | TBR-3 | folded | §6.1, roadmap OD-A17; the worker process contains what isn't closed yet (§6.3, §6.6) |
| maxim_response_1/trust_boundary | TBR-4 | folded | §6.3, §6.6 (`spawn`; the host never latches itself, a start-up check; v3 missed the host side) |
| maxim_response_1/trust_boundary | TBR-5 | folded | §6.6 (the channel as a gate, the test double behind it), `boundaries.md` §5.3 (v3 had neither) |
| maxim_response_1/trust_boundary | TBR-6 | folded | §6.4, roadmap OD-A18, `embeddable_agent_DRAFT.md` OD-EA4 (the planted parallel-dispatch write) |
| maxim_response_1/trust_boundary | TBR-7 | folded | §6.1, §6.6, roadmap OD-A17 (the static ban names `maxim.embodied_runtime`; no reply reaches the template) |
| maxim_response_1/trust_boundary | TBR-8 | folded | §5.2, §6.6 (provenance with session id and host index) |
| maxim_response_1/trust_boundary | TBR-9 | folded | §6.1: the request/reply cut makes the model path the host's |
| maxim_response_1/trust_boundary | TBR-10 | folded | §6.1, roadmap OD-I3 |
| maxim_response_1/trust_boundary | TBR-11 | partial | §5.2, §6.6 (the guest-text gate, every Cf character restored); cloud egress refused with guests is a proposed sixth gate for the owner, §12.1 item 1 |
| maxim_response_1/trust_boundary | TBR-12 | folded | §6.6 (an environment allowlist, not a scrub; the host start-up check) |
| maxim_response_1/trust_boundary | TBR-13 | folded | §12.1 items 1 and 7 (retention of guest speech agent-side) |
| maxim_response_1/trust_boundary | TBR-14 | folded | §0 (O14), §12.1 item 1, roadmap Phase 4 |
| maxim_response_1/architecture | 1.1 | folded | §6.2, §11.3, §4.8 |
| maxim_response_1/architecture | 1.2 | partial | §6.1, §6.6: cognition tools inside `think` are proposed, not adopted, pending Maxim's C10 experiment |
| maxim_response_1/architecture | 1.3 | folded | §4.7, §6.6, `embeddable_agent_DRAFT.md` OD-EA9 |
| maxim_response_1/architecture | 1.4 | folded | §4.2 (P1c), §4.5 |
| maxim_response_1/architecture | 2.1 | folded | §6.1 |
| maxim_response_1/architecture | 2.2 | folded | §6.1, §6.6 (the continuation split by owner), `embeddable_agent_DRAFT.md` §2 |
| maxim_response_1/architecture | 2.3 | folded | §6.1 (the basis), §6.6 (one staleness vocabulary and what resume does; v3 had only the basis) |
| maxim_response_1/architecture | 2.4 | folded | §6.1, roadmap OD-A15 |
| maxim_response_1/architecture | 2.5 | folded | §6.1 (a model role) |
| maxim_response_1/architecture | 2.6 | folded | §6.1, §5.2, §6.6 (per-chunk validation on decoded text) |
| maxim_response_1/architecture | 3.1 | folded | §0 (O15a), roadmap OD-A15 |
| maxim_response_1/architecture | 3.2 | folded | §0 (O15, O15a; the stepped `think` after 1.4.0) |
| maxim_response_1/architecture | 4.1 | folded | §6.1, §6.6 (one derivation) |
| maxim_response_1/architecture | 4.2 | folded | roadmap OD-A11, OD-A18 (Maxim: no contradiction) |
| maxim_response_1/architecture | 4.3 | partial | roadmap OD-A16, OD-A18 (D53, settle keys, side doors), OD-A12 (ConceptExtractor), §4.7 and §6.6 (chains, guest holds), roadmap OD-H6 (the submit trigger); the write window for agent stores is not written |
| maxim_response_1/architecture | 4.4 | folded | §6.1, §6.6 (the host stamps priority and deadline from the kind; v3's agent-supplied deadline was a second source of time) |
| maxim_response_1/architecture | 4.5 | folded | §4.8 |
| maxim_response_1/architecture | 4.6 | folded | §10 |
| maxim_response_1/architecture | §5 | folded | v3 and v3.1: §0 (O6a, O7a), §4.2, §4.4, §4.5, §4.7, §4.8, §5.2, §6.1, §6.2, §6.6; `boundaries.md` §7.1, §7.4; the embeddable draft; roadmap Phase 3; OA3's interim is §12.1 item 6 |
| maxim_response_1/executor | 1a | folded | §4.2 (`next_actions`) |
| maxim_response_1/executor | 1b | folded | §6.1 |
| maxim_response_1/executor | 1c | folded | §4.2 (P1c), §6.1 |
| maxim_response_1/executor | 1d | folded | §6.1 (no inner tool loop) |
| maxim_response_1/executor | 2a | folded | §6.1 |
| maxim_response_1/executor | 2b | folded | §12.2 (never share a router) |
| maxim_response_1/executor | 3a | folded | §6.1 front gate |
| maxim_response_1/executor | 3b | folded | §6.1 front gate |
| maxim_response_1/executor | 3c | folded | §4.7 (`maxItems`) |
| maxim_response_1/executor | 3d | folded | §6.3, §6.6 |
| maxim_response_1/executor | 4a | folded | §6.1 (`AgentHome`) |
| maxim_response_1/executor | 4b | folded | §6.1 (`AgentHome`) |
| maxim_response_1/executor | 4c | folded | §6.1 (`bio_stack.py:654`) |
| maxim_response_1/executor | 4d | folded | §6.1, §6.6 (keyed substreams) |
| maxim_response_1/executor | 5a | folded | §12.3 |
| maxim_response_1/executor | 5b | folded | §12.3 |
| maxim_response_1/executor | 5c | not folded | the 3 legacy `np.random` calls change no design row; OD-A7's scope (randomness outside the fence) covers them |
| maxim_response_1/executor | 5d | folded | §12.3 |
| maxim_response_1/executor | 5e | folded | §12.2 |
| maxim_response_1/executor | 5f | folded | §12.3 |
| maxim_response_1/executor | 5g | folded | roadmap Phase 3 (OD-I1, five sites) |
| maxim_response_1/executor | 6a | folded | roadmap Phase 3 (OD-I3) |
| maxim_response_1/executor | 6b | folded | §6.1, roadmap OD-I3 |
| maxim_response_1/executor | 6c | folded | roadmap Phase 3 (OD-I3) |
| maxim_response_1/executor | 6d | folded | roadmap Phase 3 (OD-I3) |
| maxim_response_1/executor | 7a | folded | §6.1 (roster row) |
| maxim_response_1/executor | 7b | folded | roadmap OD-H6 |
| maxim_response_1/executor | 7c | folded | roadmap Phase 3 (OD-I4) |
| maxim_response_1/executor | 7d | folded | roadmap Phase 3 (OD-I4) |
| maxim_response_1/executor | 7e | folded | §6.1, §6.3 (no keys, the gateway in the host) |
| maxim_response_1/executor | 8a | folded | §5.1, roadmap OD-H5 |
| maxim_response_1/executor | 8b | folded | §0 (O15a) |
| maxim_response_1/executor | — Citations for the resumable-think cut po | folded | §6.1, `embeddable_agent_DRAFT.md` §1 |
| maxim_response_1/executor | — Advisor POSIX-only | folded | §6.6 (an OS sandbox per platform; Windows refused for guest sessions, proposed) |
| maxim_response_1/executor | N1 | folded | §4.2, §6.1 |
| maxim_response_1/executor | N2 | folded | §6.1, roadmap OD-A17 |
| maxim_response_1/executor | N3 | folded | §12.2 |
| maxim_response_1/executor | N4 | folded | §6.3, §6.6 |
| maxim_response_1/executor | N5 | folded | §3.4, §6.6 (one derivation; CLAUDE.md's numpy rule governs `World`; v3 left the conflict open) |
| maxim_response_1/executor | N6 | folded | §12.3 |
| maxim_response_1/executor | N7 | folded | §1, §6.1, §6.4 (directories added; §1's time citation is `:1125-1127`; v3 had neither) |
| npcs_v3/architecture | B1 | folded | §6.6 (`apply` and `settle` the only writers, both host-called), `boundaries.md` §7.1 |
| npcs_v3/architecture | B2 | folded | §6.6 (a host-owned header with the budgets, an opaque agent-owned body) |
| npcs_v3/architecture | S1 | folded | §6.6 (the lifecycle, end to end) |
| npcs_v3/architecture | S2 | folded | §6.6 (no backend in the worker; the doors fail closed), roadmap OD-A17, `embeddable_agent_DRAFT.md` §3 |
| npcs_v3/architecture | S3 | folded | §6.1, §6.6 (cognition tools not adopted; C10) |
| npcs_v3/architecture | S4 | folded | §6.6 (stage 1 in the host; `PYTHONHASHSEED` pinned), `boundaries.md` §5.3, §5.4 |
| npcs_v3/architecture | S5 | folded | §6.1, §6.6 (the host stamps priority and deadline) |
| npcs_v3/architecture | S6 | folded | §6.6 (`agent_failed`) |
| npcs_v3/architecture | S7 | folded | §6.6 (the test double behind the channel) |
| npcs_v3/architecture | S8 | folded | `embeddable_agent_DRAFT.md` §4 (PR 5 is the one submit-path design; PR 4a), roadmap OD-A15 |
| npcs_v3/architecture | S9 | folded | §12.1 item 6 (reframed with dilate's numbers, co-op cost, abandon's real cost) |
| npcs_v3/architecture | S10 | folded | `world_model.md` §10 rows 9b and 10, §6.5 |
| npcs_v3/architecture | N1 | folded | §6.6, `boundaries.md` §7.1 (inlining is a decision against O13) |
| npcs_v3/architecture | N2 | folded | `boundaries.md` §7.1 (the host service protocol of boundaries v2 and npcs v2) |
| npcs_v3/architecture | N3 | folded | §6.6 (one signature), `boundaries.md` §7.1 |
| npcs_v3/architecture | N4 | folded | §6.6 (receipts have two projections) |
| npcs_v3/architecture | N5 | folded | roadmap Phase 3 note; the foundations fold rows annotated (§6.6), `boundaries.md` fold table |
| npcs_v3/architecture | N6 | folded | §6.6 (`truncated(prefix, reason=validation)`) |
| npcs_v3/architecture | N7 | folded | `boundaries.md` §5.3 (Agent homes: `MAXIM_DATA_HOME` the one allowed read until OD-A12) |
| npcs_v3/bio_faithful | BF3-1 | folded | §6.1, §6.6 (credit's real dependency), roadmap OD-A19, `correction_1.md` |
| npcs_v3/bio_faithful | BF3-2 | folded | §6.6 (the settle horizon is `[engineering]`; its route is the 300 s buffer) |
| npcs_v3/bio_faithful | BF3-3 | folded | §6.6 (the yield after ~1 s of unfilled silence; the account's onset a parameter) |
| npcs_v3/bio_faithful | BF3-4 | folded | §6.6 (the Known gap; the listener-side rule) |
| npcs_v3/bio_faithful | BF3-5 | folded | §6.6 (P1c in fatigue load and the speed trait) |
| npcs_v3/bio_faithful | BF3-6 | folded | §6.6, §8.2, roadmap OD-A15 (retrieval writes returned) |
| npcs_v3/bio_faithful | BF3-7 | folded | §6.6 (the offset-and-scale test) |
| npcs_v3/bio_faithful | BF3-8 | folded | §6.6 (planning in overlap, not the repertoire) |
| npcs_v3/bio_faithful | BF3-9 | folded | §6.6 (the O'Connell & Kowal caveat) |
| npcs_v3/bio_faithful | BF3-10 | folded | §6.6 (production vs perception) |
| npcs_v3/bio_faithful | BF3-11 | folded | §6.6, §12.1 item 5 (filler propensity) |
| npcs_v3/bio_faithful | BF3-12 | folded | §6.6 (Maxim's ANALOG label) |
| npcs_v3/bio_faithful | BF3-13 | folded | §6.6 (the BD-6 and BD-19 tests); this table re-marks BD-6 and BD-19 |
| npcs_v3/determinism | DET-B1 | folded | §4.4, §6.6 (resume at the landing tick; `reply_landed`) |
| npcs_v3/determinism | DET-B2 | folded | §6.6 (the prefix is delivered speech in world time) |
| npcs_v3/determinism | DET-B3 | folded | §6.1, §6.6, `embeddable_agent_DRAFT.md` OD-EA11 |
| npcs_v3/determinism | DET-S1 | folded | §6.6 (`floor_event` host records) |
| npcs_v3/determinism | DET-S2 | folded | §6.6 (canonical repeat numbering) |
| npcs_v3/determinism | DET-S3 | folded | §6.6 (the double in a spawned worker) |
| npcs_v3/determinism | DET-S4 | folded | §6.6 (`agent_failed`, logged) |
| npcs_v3/determinism | DET-S5 | folded | §6.6 (resume equivalence) |
| npcs_v3/determinism | DET-S6 | folded | §6.6 (a coarse category, modelled part only) |
| npcs_v3/determinism | DET-S7 | folded | §6.6 (fatigue counts modelled durations) |
| npcs_v3/determinism | DET-S8 | folded | §3.4 (the accepted cost); this table re-marks BD-13 and BD-14 |
| npcs_v3/determinism | DET-N1 | folded | §6.6 (one signature) |
| npcs_v3/determinism | DET-N2 | folded | §6.6 (host-stamped, outside the cache key) |
| npcs_v3/determinism | DET-N3 | folded | §10 (d_z pre-registered, divergence tick per pair) |
| npcs_v3/determinism | DET-N4 | folded | §6.6 (`npc_key`; state saved pickle-free) |
| npcs_v3/determinism | DET-N5 | folded | §6.6 (the machinery clock's zero) |
| npcs_v3/executor | B1 | folded | §6.6, `boundaries.md` §5.3 (the worker channel gate) |
| npcs_v3/executor | S1 | folded | this fold table, after §12.3 (TBR-4, Exec N5 and N7 re-marked and folded) |
| npcs_v3/executor | S2 | folded | roadmap Phase 4 (entry: OD-A1 to OD-A19, 1.4.0 and the slice), roadmap Phase 3 exit (OD-EA10 to OD-EA12) |
| npcs_v3/executor | S3 | folded | §3.4, §6.6 (one derivation; the real hash names) |
| npcs_v3/executor | S4 | folded | §6.3, §6.6 (the round-trip estimate, budget and levers) |
| npcs_v3/executor | S5 | folded | §6.5; the foundations fold rows annotated in both files |
| npcs_v3/executor | S6 | folded | §12.1 item 1, roadmap Phase 4 (the red gate and the five tests) |
| npcs_v3/executor | N1 | folded | §1 (each count names its `main`) |
| npcs_v3/executor | N2 | folded | §6.1, §6.4, `embeddable_agent_DRAFT.md` §3 |
| npcs_v3/executor | N3 | folded | §6.1 (ten families) |
| npcs_v3/executor | N4 | folded | §6.1 (the roster row) |
| npcs_v3/executor | N5 | folded | the header, §4.5, §6.1, `embeddable_agent_DRAFT.md` §1 ("by default"; the 0.11× row is a lower bound) |
| npcs_v3/executor | N6 | folded | §8.1, §8.2, roadmap OD-H4 (folded into OD-H5) |
| npcs_v3/executor | N7 | folded | §6.6 (one signature) |
| npcs_v3/executor | N8 | partial | this generator, which writes the fold table after §12.3 (root-relative, per-file counts printed, refuses folded rows without a place); nothing in the gate reruns it yet, and the 40-character keys of two round-1 rows are kept so their ids stay stable |
| npcs_v3/executor | N9 | folded | §0 (O14's dated note) |
| npcs_v3/executor | N10 | folded | §6.1, §12.1 item 1 (which trigger uses the wake word) |
| npcs_v3/trust_boundary | TB3-B1 | folded | §6.6, `boundaries.md` §5.3 |
| npcs_v3/trust_boundary | TB3-S1 | folded | §6.6, §12.2, `embeddable_agent_DRAFT.md` §2 (no reply reaches the template) |
| npcs_v3/trust_boundary | TB3-S2 | folded | §6.6 (provenance through derivation and relay; the purge's exit test) |
| npcs_v3/trust_boundary | TB3-S3 | folded | `boundaries.md` §5.3, §6.6 (every Cf character) |
| npcs_v3/trust_boundary | TB3-S4 | folded | §6.6 (decoded text, per chunk and whole) |
| npcs_v3/trust_boundary | TB3-S5 | folded | §6.6 (the host-delivered prefix) |
| npcs_v3/trust_boundary | TB3-S6 | folded | §6.6 (a container, not a sandbox; an OS sandbox proposed for guest sessions) |
| npcs_v3/trust_boundary | TB3-S7 | folded | §6.6 (the host never latches itself) |
| npcs_v3/trust_boundary | TB3-S8 | partial | §12.1 item 1: remote egress with guests is proposed as a sixth gate; the owner decides |
| npcs_v3/trust_boundary | TB3-S9 | folded | §6.6 (budgets per input and per NPC per world minute) |
| npcs_v3/trust_boundary | TB3-S10 | folded | §6.6 (`agent_failed`) |
| npcs_v3/trust_boundary | TB3-S11 | folded | §12.1 item 1, roadmap Phase 4 (the strict red gate on guest joins) |
| npcs_v3/trust_boundary | TB3-S12 | folded | this fold table, after §12.3 (TBR-5, 7, 8, 11, 12, 13 and 4 re-checked; TBR-11 stays partial) |
| npcs_v3/trust_boundary | TB3-N1 | folded | §12.2, `boundaries.md` §5.3 (OD-A18) |
| npcs_v3/trust_boundary | TB3-N2 | folded | `embeddable_agent_DRAFT.md` §3, roadmap OD-A17 (the ban's packages named) |
| npcs_v3/trust_boundary | TB3-N3 | folded | `embeddable_agent_DRAFT.md` §5 (OD-EA4's planted write) |
| npcs_v3/trust_boundary | TB3-N4 | folded | §6.6, `boundaries.md` §5.3 (one guest-text gate for every string) |

**Counts:** 175 ids; 165 folded, 9 partial, 1 not folded.
