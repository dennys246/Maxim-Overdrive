# DRAFT for Maxim: the world-clock release, an agent a deterministic host can step

**Status:** a proposal drafted in Maxim Overdrive on 2026-11-16, for Maxim's own process: an issue, this plan, a
three-lens plan review (Executor, Architecture, Wire integrity) and a three-lens code review per PR. Nothing here is
built, run or claimed. It moves to Maxim's `docs/plans/` if Maxim accepts it. Game runs stay off Maxim's results
ledger.

- **Release shape:** on its own clock, like the atonia gate (`roadmap_1_3_x.md`, "The atonia gate (own clock; it
  takes the next free patch number when it ships)"). It ships when it is done and takes the next free number then.
- **Tier:** this is tier A of Overdrive's Phase 3 (`docs/roadmap.md`): **embeddability only**. It adds no mechanism
  and claims no behaviour. Everything in it is `[engineering]` under Maxim's two-tier rule.
- **Maxim tree read:** `main` at `4b773ef8` (2026-11-16). Line numbers below are from that tree unless marked
  "1.3.3" (the installed wheel the Overdrive audit read).

## 1. The claim, and what "done" means

**A Maxim agent can be stepped by a host that owns time, randomness and ids, and two runs of the same host script
leave it in bit-identical state, however fast or slow the host's wall clock runs.**

"Done" is the exit test in §6, on the shipped path: an embedded agent with a stub LLM, stepped by a scripted host.
Robots and the console keep today's behaviour exactly, because the default clock is the host clock (§3.1).

## 2. What was measured (Overdrive's evidence)

The audit is `docs/design/research/time/maxim_time_audit.md` in Overdrive (grep-based, so the counts are approximate).

- **About 880 clock sites in about 215 files** (`time.time()` about 570 of them, in 173 files of 1.3.3). Thirty-six
  dataclass fields default to `time.time` (`grep default_factory=time.time` on `main`). Thirty-eight `uuid4()` calls
  and about 39 uses of the global `random` module (`main`).
- **The substrate's cadence is set by the wall clock.** `LoopController.llm_submit_interval = 0.5`
  (`runtime/loop_controller.py:157`), checked against the wall in `runtime/loop_state.py::_substrate_tick_due`
  (`:240`); `run_agentic_loop(target_hz=30.0)` (`runtime/agent_loop.py:970`); the Default Network's own thread at
  `update_hz = 30.0` (`default_network/config.py:219`); `EmbodimentConfig.poll_hz = 1.0` (`embodiment/body.py:88`).
  **Consequence in a world with a time dial:** at 20x, an agent gets one twentieth of its substrate updates per world
  second, so its reflexes slow as the world speeds up (Overdrive `engine_mapping.md` §1.4).
- **Pause leaks.** `Embodiment.evaluate_failures` drifts by `now - self._last_poll` on the wall
  (`embodiment/body.py:294-295`), never reset across a pause and uncapped. #1361 records this ("the pause leak").
- **The prompt carries the exact host date and time.** `agents/prompt_builder.py:1104` (`now = datetime.now()`),
  `:232-236` (`build_datetime_section`, "=== CURRENT DATE/TIME (IMPORTANT) ===", "Today is {date_str}"), `:2379`
  (search synthesis). `agents/llm_fallback.py:330, :334, :338` answer "what time is it" from the host clock before
  the LLM runs. In a game, an NPC asked the time answers with the player's real local time, and in co-op a guest
  learns the host's time zone.
- **The SCN phase is the host calendar.** `time/temporal_signature.py:62` (`datetime.fromtimestamp(ts)`, host local
  time, daylight saving included). The oscillator advances by a fixed step per observation, not by elapsed time
  (`time/oscillator.py:193-194`), so ten events in a minute move it hours and a silent day moves it zero.
- **Determinism breaks that ride with time.** Hippocampus de-duplication keys on builtin `hash()`
  (`memory/hippocampus.py:1055`), which Maxim's own CLAUDE.md forbids for values that persist and which varies across
  processes. `attention/salience_map.py:227` reads `now = current_time or time.time()`, so a world time of exactly
  `0.0` silently becomes the wall clock. Session and run ids come from `time.strftime` (`DECISIONS.md` G17 records
  "No deterministic session id exists").
- **Under a deterministic host, real Maxim cannot run inside the sealed tick at all.** Overdrive's boundaries review
  (`docs/design/reviews/boundaries/bio_faithful.md`, BF-2) found that a host tripwire on clock reads would raise in
  the first agent step (`embodiment/cerebellum.py:155` reads `time.time()`). Without the tripwire the host silently
  reads the wall clock. Either way Maxim cannot be embedded in a deterministic host today.

Overdrive lessons this rests on (`docs/lessons_maxim_in_games.md`): 11 (agents need world time, injected), 12 (nobody
waits for a thought, in world time) and 6 (an action's effect may arrive after the call).

## 3. The design

### 3.1 Three injected collaborators, defaulting to today's behaviour

A new `utils/clock.py` (name open) with three small protocols:

| Protocol | Surface | Default |
|---|---|---|
| `Clock` | `now_us() -> int` (monotonic, in the host's microseconds); `epoch_s` and `day_length_s` for calendar phase | `HostClock`: wall time, host calendar, today's behaviour |
| `Rng` | a seeded `random.Random` (or `numpy.random.Generator`) per agent, with named substreams | seeded from OS entropy, today's behaviour |
| `IdSource` | `next_id(kind) -> str`, built from (agent, session, sequence) | `uuid4`, today's behaviour |

- **Robots, the console and pulse change nothing**, because they get the defaults. This is what keeps the release
  out of a breaking-change question.
- **Embedders pass all three** through one `AgentTime` bundle on the agent factory (`create_full_agent`,
  `AgentFactory`), as a required keyword on a new embedded entry point, so forgetting one is a `TypeError` rather than
  a silent wall-clock fallback (Maxim's "[engineering] Push silent-no-op invariants into types").
- **A tripwire for embedders:** with an injected clock, a test-mode guard patches `time.time`, `time.monotonic`,
  `time.perf_counter`, `datetime.now` and the global `random` to raise inside a stepped turn. Maxim's M72 lint
  (`outstanding.md:123`, backlog with no check yet) becomes its static half, scoped to the live path below.

### 3.2 The live path: which sites move (not all 880)

Only sites an embedded agent reaches in a stepped turn move to the injected collaborators. Hardware edges, backend
timeouts, heartbeats and robot motor sleeps stay on the wall, as #1361 §(g) already says for "watch the process and
backend".

| Subsystem | Sites (from the audit; `main` lines where checked) | Moves to |
|---|---|---|
| Drives and body | `embodiment/body.py:294-295` (drift dt); stamps at 1.3.3 `body.py:128, :502, :599`; `embodiment/spec.py:837` (`SensorReading.timestamp=_time.time()`) | `Embodiment.advance(dt)` from #1361 S4; stamps from `Clock` |
| NAc credit | `decisions/nac.py:439` (`temporal_window_seconds = 300.0`), `:1167` (stale cut); anchors and `saved_at` (1.3.3 `:3661, :4188`); `causal_link.py`, `significance.py`, `valence_signal.py` stamps | #1361 S3b moves windows to experience time; stamps from `Clock` |
| Hippocampus | dedup `memory/hippocampus.py:1055` (builtin `hash`, 30 s wall window `:290`); capture and access stamps; `memory/types.py` defaults; consolidation `now = time.time()` (1.3.3 `hippocampus_consolidation.py:113, :283, :453, :581`) | `stable_hash_64_signed`; window and stamps on `Clock` |
| Cerebellum | `embodiment/cerebellum.py:155, :453` | `Clock` |
| Reaction and pain buses | `reactions/bus.py:35, :81` (`DEFAULT_REFRACTORY_S = 0.5`); `proprioception/pain_bus.py`, `pain.py` cooldowns | `Clock` (see §4, the refractory split) |
| Attention and salience | `attention/salience_map.py:227` (the `or` bug); `salience/salience_network.py`, `movement_detector.py`, inhibition of return | `Clock`; `is None`, never `or` |
| SCN and temporal signature | `time/temporal_signature.py:62`; `time/scn.py` stamps; the 19 signature producers listed in the audit §1.3 | phase from `Clock` (`epoch_s`, `day_length_s`), no host local time |
| Oscillator | `time/oscillator.py:193-194` | `step(dt)` with the elapsed `Clock` time since the last observation |
| Default Network | its thread (1.3.3 `default_network/network.py:891-906`), cooldowns, inhibition, arbiter, gaze `random.uniform` | `DefaultNetwork.step(now_us)` and the injected `Rng` (§3.3) |
| Live loop cadence | `loop_state.py:240` (`_substrate_tick_due`), `loop_controller.py:157`, `agent_loop.py:970`, `loop_substrate.py` (1.3.3 `:56`), `substrate_proposal.py` (1.3.3 `:871`, a request id from the wall) | the agent live tick (§3.3); ids from `IdSource` |
| Prompt time | `prompt_builder.py:1104, :2379`; `llm_fallback.py:330-338` | the calendar of the injected `Clock`, or omitted (§3.4) |
| Ids and randomness on the path | `uuid4` and global `random` sites the stepped turn reaches | `IdSource`, `Rng` |

The PR that lands each row enumerates its exact sites with a grep in its description, and the tripwire (§3.1) is the
check that none was missed on the path the exit test runs.

### 3.3 Externally stepped: the agent live tick and the Default Network

- **`DefaultNetwork.step(now_us)`** (Overdrive Phase 3 item 11). Every DN timer reads the injected `Clock`. The
  existing thread stays as the robot mode: it calls `step` on its own cadence. An embedder never starts the thread.
- **`AgentLiveTick.step(world_dt_us)`** (item 12): one call drives the experience driver
  (`runtime/experience_time.py:36`, `ExperienceClockDriver`), `Embodiment.advance` (#1361 S4) and the proposer, and
  proposes on action completion, not on every call. It is not `AgentPool`, which has no body, drives or DN
  (Overdrive X4).
- **Sequencing with the fence.** Both touch code inside Maxim's fence ("Nothing under `runtime/agent_loop.py`,
  `decisions/nac.py`'s selection path or `simulation/orchestrator.py` until the decomposition slices touching it
  have landed", `roadmap_1_3_x.md:358`), and #1361 S3–S6 are already scheduled with 1.3.6's loop work
  (`roadmap_1_3_x.md:1245`). So the live tick lands **after 1.3.6**, built on `loop_stack_builder.md`'s one builder,
  and this plan does not duplicate S3–S6: it depends on them. The rows outside the fence (§5, PRs 0–5) can ship
  first.

### 3.4 Prompt time

With an injected clock, the date and time sections and the canned answers come from the injected clock's calendar
(the world's), or are omitted when the embedder declares no calendar. With `HostClock` nothing changes. **What the
agent believes the time is** (an estimate from an entrained oscillator) is tier B, not this release.

## 4. Maxim decisions this argues against, with the evidence

| Decision (verbatim) | Where | The argument |
|---|---|---|
| "SCN phases, `TemporalSignature` similarity \| host calendar by design" | `experience_clock_decay.md` §(g) | Keep it as the **default**, but the calendar must be the injected clock's. In an embedded world the host calendar is another universe's: NPCs live on the player's local time zone and daylight saving, and two machines give one world moment different phases (Overdrive `realtime_lanes_coop.md` §3.2). This changes the source, not the four frozen fields of `TemporalSignature`. |
| "PainBus refractory, reflex cooldowns \| motor/IO rate limits; hardware safety (embodiment brief §1)" | same table | Correct for a robot's motors, wrong for an agent's perception. Split them: **physical-edge rate limits** (motor commands, IO) stay on the wall; **perceptual refractoriness and cooldowns** (ReactionBus, PainBus, DN cooldowns) read the injected clock. Under `HostClock` both read the wall, so the robot is unchanged. At 20x today, a 0.5 s pain refractory is 10 world seconds. |
| "`idle_sleep_s`, `target_period`, `llm_submit_interval`, the 120 s `_submitted_recently` window \| loop scheduling; no longer pace decay" | same table | True once S3a lands, but they still pace the **substrate's proposals**, which sets reflex latency in world time. The live tick (§3.3) replaces them for embedders; the robot keeps them. |
| "No deterministic session id exists … Every session id today is wall-clock `time.strftime`" | `DECISIONS.md` G17 | `IdSource` closes it, and G3's own rule already asks for it: the `AfferentEvent` id is "(agent, session id, seq): no uuid, no wall time". |
| M76: the hybrid plan revives on "a second robot body" | `outstanding.md:127` | Not needed for this release. Overdrive asks separately (Phase 3 tier C) to re-key it to include a simulated body. |

Decisions this release **agrees with and builds on:** the one-clock policy ("the experience clock governs everything
that strengthens or forgets a memory trace; wall time only at named sites where downtime is meant to count",
`memory_strength_and_forgetting.md`), #1361's owner decisions 1 and 2 and answers Q4 ("No wall-clock fallback") and
Q6, and G3 ("Tracks are logical channels scheduled on the loop/tick clock: deterministic, lockstep-testable").

## 5. The build, in order

Sizes: **S** under about 150 changed lines, **M** about 150–600, **L** over 600 or touching the loop. Each PR lands
red gates first (`xfail(strict=True)`, flipped in place), and gets Maxim's three-lens code review.

| PR | What | Size | Fenced? |
|---|---|---|---|
| 0 | Red gates for §6's exit tests (E1–E6) against a stub embedded host; the M72 lint in report mode over the live path | S | no |
| 1 | `utils/clock.py`: `Clock`, `Rng`, `IdSource`, `AgentTime`, the host defaults, the test-mode tripwire | S | no |
| 2 | Small fixes outside the fence: `salience_map.py:227` `is None`; hippocampus dedup on `stable_hash_64_signed`; prompt and fallback time from `Clock` (§3.4) | S | no |
| 3 | The 36 `default_factory=time.time` stamps and `SensorReading` stamping (`spec.py:837`) from `Clock`; mechanical, about 40 files | M | no |
| 4 | Stamps and dt in hippocampus, cerebellum, attention, salience, and the reaction and pain buses (with the §4 refractory split) | L, split 4a/4b | no (NAc rows wait for the fence) |
| 5 | `uuid4` and global `random` on the live path to `IdSource` and `Rng`; `TemporalSignature` and the oscillator from `Clock` | M | no |
| 6 | `DefaultNetwork.step(now_us)`; the thread becomes a caller of `step` | L | no |
| 7 | NAc stamps and anchors on `Clock` (after #1361 S3b) | M | yes, after 1.3.6 |
| 8 | `AgentLiveTick.step(world_dt_us)` on the 1.3.6 loop builder (item 12) | L | yes, after 1.3.6 |
| 9 | Flip E1–E6 on the shipped embedded path; docs, changelog fragment, the M72 lint enforcing | M | no |

**Estimate: 10 PRs (3 S, 4 M, 3 L), plus the dependency on 1.3.6's #1361 S3–S6.** PRs 0–6 can ship before 1.3.6;
7–9 cannot. The honest uncertainty is PR 4 and PR 8: the audit is a grep, not a call-graph walk, so the live path may
reach sites it missed. The tripwire turns any miss into a red test rather than a silent leak.

## 6. Exit tests (the determinism test is E1)

| # | Test | Passes when |
|---|---|---|
| **E1** | **Two runs, bit-identical.** One scripted host script (500 world ticks, percepts, actions, a stub LLM with recorded responses), an injected `Clock`, `Rng` (fixed seed) and `IdSource`, run twice in separate processes with different `PYTHONHASHSEED` | a canonical digest of the agent's persisted state (NAc maps and links, hippocampus records and ids, drive values, DN state, SCN bins, cerebellum models) is byte-identical |
| E2 | **Dial invariance.** The same script, with the host pacing at 1x and at 20x wall speed (and with injected wall-time jitter) | the E1 digest is identical across both |
| E3 | **Pause.** 30 wall seconds with no world ticks, mid-script | zero drift, decay, habituation recovery or refractory release during the pause |
| E4 | **No wall reads on the path.** The tripwire armed for a whole stepped turn | no raise |
| E5 | **Robots unchanged.** The existing suite with `HostClock` defaults | green, and no ledger row walks (if one would, the plan review lists it) |
| E6 | **No host time in prompts.** An embedded prompt and the fallback answers | contain no host date, time or time zone |

Prove each gate by deleting what it guards (for E1: reintroduce one `time.time()` stamp and watch the digest differ).

## 7. What stays out

- **Tier B (the 1.4 line, earned by experiment):** an SCN oscillator entrained by a world light percept with a
  free-running period; the prompt's time from the agent's own time sense; interval estimates with scalar noise;
  state-dependent latency. Each enters `[engineering]` and graduates only through a pre-registered experiment
  (Overdrive's skeptic brief, `docs/design/research/time/skeptic.md` §5, T1 and T2).
- **Tier C (the 1.5 hybrid line):** propose and settle credit for effects that arrive after the call, a stale refusal
  kind, generate vs apply, cancellable deliberation, and the batched SEM changes
  (`sem_breaking_change_plan_DRAFT.md`).

## 8. Open for Maxim's review

- The module name and whether `Rng` is `random.Random` or a NumPy `Generator` (Maxim uses both).
- Whether PR 8 is a new entry point or a mode of the 1.3.6 builder.
- Whether the tripwire belongs in Maxim's test utilities or only in embedders' tests.
- Whether this is one release or two (PRs 0–6 before 1.3.6, PRs 7–9 after).
