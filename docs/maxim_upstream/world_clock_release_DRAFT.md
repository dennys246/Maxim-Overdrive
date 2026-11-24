# DRAFT for Maxim: a world clock for embedded agents, in two plans (A-pre and A-post)

**Status:** drafted in Maxim Overdrive on 2026-11-16 after a seven-lens review (`docs/design/reviews/foundations_v1/`),
brought in line with the roadmap's tier A table on 2026-11-24 (step 3, `phase3/upstream-sync`). Nothing is built, run
or claimed. Everything is `[engineering]`.

- **Maxim tree:** read at Maxim `origin/main` `5bcc2cf0` (2026-11-24). Citations are `file::symbol`; a line number is a hint only.
- **What rules.** The roadmap's Phase 3 tier A table and `docs/design/reviews/maxim_response_2/response.md`. Where
  this draft and a row differ, the row wins. Sections marked *Superseded* keep only a pointer.
- **Maxim's A-pre plan is merged.** Maxim's D9 session wrote it as `docs/plans/world_clock_a_pre.md` and its guard
  note, merged as #1787. It read this draft as background only. Its owner rulings (D-WC1 to D-WC7, Maxim's owner,
  2026-11-24) are cited from it; where it and this draft differ, the plan rules on Maxim's side.
- **Overdrive ids:** OD-A1 to OD-A8, plus OD-I8 and Maxim's #1769. The stepped Default Network (OD-A9) has its own
  draft, `default_network_stepped_DRAFT.md`.
- **The two plans:**
  - **A-pre**, touching no fenced or hot file. Maxim put it in 1.3.5, line 2 (`release_1_3_5.md` D9), not on its own
    patch number.
  - **A-post**, with 1.3.6 (Session A), after the decomposition slices land: `runtime/agent_loop.py`,
    `simulation/orchestrator.py`, NAc's selection path and `runtime/tool_dispatch.py`.
- **Out of both, tier B** (`time_sense_DRAFT.md`): the oscillator's elapsed-time step, entrainment and any world
  calendar.

## 1. The claim, and what "done" means

**An embedded Maxim agent reads time from two collaborators its host injects: a machinery clock for decay,
cadences, windows and stamps, and a perceived-time port, the only time a prompt may contain (OD-A2). Two runs of the
same host script leave it in bit-identical state however fast or slow the host's wall clock runs. Robots, the console
and pulse keep today's behaviour exactly.**

"Robots unchanged" is meant literally: the host defaults return exactly what today's code reads, including the units
of persisted stamps, and the characterization golden still sees time through `_StepClock`. Randomness and ids are
OD-A7, after the 1.4.0 cut (§3.6).

## 2. Front gate: what this rides on

| Existing | What it does | How this plan uses it |
|---|---|---|
| `runtime/experience_time.py::ExperienceClockDriver` | advances an agent's experience clock from its world's time | For robots it is the machinery clock for decay and cadences (OD-A2, cand. A3). The A-pre plan diverges for its windows on purpose: the driver quantises turns and excludes pauses, so moving a wall window onto it would change robot behaviour. Under embedding the entry point (OD-A10, A-post) must feed both from one host source; nothing in A-pre makes them agree. |
| `experience_clock_decay.md` (#1361) | the one-clock policy for memory | Respected: no second experience clock. OD-A1 (#1361 S3 to S6) is a dependency, not built here. |
| `tests/unit/_loop_harness.py::_StepClock`, `scripts/survival_world/scripted_water.py::LockstepTime` (#951) | patch the global `time` to run the loop lockstep | A process-wide patch can't serve several agents in one process, hence injected collaborators. Host defaults read `time.time` through the module attribute at call time, with a test that `_StepClock` still reaches them. |
| `DECISIONS.md` G17 | defers the session-id source to the post-fence resume stage | **Stands** (D-WC1). No `IdSource` in A-pre. |
| `DECISIONS.md` G3: tracks on the loop/tick clock | | Agreed and built on. |

## 3. The design

### 3.1 The split clock (OD-A2)

| Collaborator | Host default (robots, console, pulse) | Embedded |
|---|---|---|
| **machinery clock**: epoch seconds as today, and microseconds | `time.time()` / `time.monotonic()`, read at call time; for decay and cadences, `ExperienceClockDriver` | the host's world seconds |
| **perceived-time port**: the only time a prompt may contain | `datetime.now()` and the host calendar, as today | what the embedder declares; Overdrive declares none, so nothing renders |

- **One bundle on the embedded entry point** (OD-A10), every collaborator required there. The A-pre plan (D-WC7) keeps
  a default on every other constructor until A-post.
- **Tests (OD-A2):** a planted wall-clock read under an advancing fake clock, and a planted-render test: a sentinel in
  the machinery clock, `TZ` pinned, checked in raw, clock and date forms; an origin offset end to end; offset and scale
  only at render level on a frozen store, since a scaled clock legitimately changes decay.
- **The port's modes in A-pre** (D-WC2 revised): host default or none. A world calendar is tier B. This meets
  Overdrive's contract that no time field reaches cognition (`npcs_and_sem.md` §3.1) except for `exec_agent.py`'s SCN
  phase dict, which renders until A-post (a hot file). It does not give `npcs_and_sem.md` §3.2's coarse readout
  (OD-B9), so Phase 4's first NPC has none (roadmap tier A, open question (c)).

### 3.2 Live-path stamps and the tool's duration (OD-A4)

- **Stamps: explicit pass, defaults kept.** Each construction site on the embedded live path passes its stamp from
  the machinery clock, and the `default_factory=time.time` stays for robots and off-path sites. No `ContextVar` or
  module global: `proprioception/pain_bus.py`'s docstring rejects that back channel, and an ambient read that falls
  back to the wall is a silent fallback. Off-path stamps (`mesh/*`, `utils/web_cache.py`, `runtime/worker_pool.py`)
  are out of scope.
- **A stamp moves with every reader that subtracts from it.** The A-pre plan (D-WC6, I4) moves the stamp half (Hippocampus capture
  and access stamps, `SpecSensor.read`'s `SensorReading` stamp) with `AgentHome` (OD-A12) in A-post, each as a whole
  reader set with a clock-domain marker in the home, and reports this back against our A-pre label.
- **A tool's duration from the host, in world time**, not `runtime/tool_dispatch.py::execute_and_learn`'s wall
  `exec_start`/`exec_elapsed` (about `:1515`), which `_observe_energy_cost` books as NEGATIVE NAc valence above 2.0 s.
  Maxim agrees it is the root fix. `tool_dispatch.py` is fenced, so it lands in A-post, with B2 (#1150), as a field of
  the settle receipt (the plan's §Placements; its gate lands red in PR 0).
- **#1769** (open): `CostTracker` seeds its month from `time.time()` but records on the caller's clock. Maxim routed it
  to this plan. The A-pre plan (D-WC5) puts the whole tracker on the wall: spend is real money. Overdrive needs no world
  time there.

### 3.3 *Superseded:* the profile-hook tripwire

Superseded by OD-A2's **static AST ban** on `time.*` and `datetime.now` in Maxim's step-path set, which **extends
M72** rather than adding a second lint, plus a long-horizon scripted run (BD-14.2): dynamic plants miss
consolidation, sleep and decay paths. The first draft's `sys.setprofile` hook is dropped. The A-pre plan takes the
same (D-WC4: one AST lint with a machinery scope and a prompt scope; the long-horizon run as a strict red gate).

### 3.4 Prompt and observation time (OD-A3)

Only through the perceived-time port, or omitted, with a lint banning `datetime.now`, `strftime` and `localtime` in
prompt-reaching modules. Examples on `5bcc2cf0` (the plan's census is authoritative):
- `agents/prompt_builder.py::build_datetime_section` and the datetime it gets (about `:1202-1204`, `datetime.now()`),
  and `_build_engage_prompt`'s own `datetime.now()` (about `:2389-2391`); `build_identity_section`'s `date_str`/`time_str`;
- two tool results that hand the model a raw epoch: `tools/introspection.py::_format_episodic_memory` and
  `SceneSummaryTool.execute`;
- `agents/context_pool.py`'s `[HH:MM:SS]` observation stamps (`time.localtime(entry.timestamp)`, about `:468`,
  `:493`), which reach the live planning prompt;
- SCN-derived text that reaches the model (`[TEMPORAL]`, `temporal_patterns`, `current_phase`), which the plan omits
  under no calendar.

`llm_fallback`'s canned time and date answers are gone, removed with the short-question shortcut (#1689). What the
agent *believes* the time is stays tier B.

### 3.5 Windows, salience and the phase source (OD-A5); dispatch gates (OD-A6)

- **OD-A5:** the Hippocampus's 30 s wall de-duplication window, attention and salience stamps, and
  `TemporalSignature`'s phase source. The plan takes the window and the SCN-derived renders, moves capture and access
  stamps to the stamp half (D-WC6) and salience and gaze to OD-A9, and keeps SCN registration on the host calendar
  (D-WC2 revised), so the phase source does not move. That reaches past OD-A20's decline, which named NAc's anchor
  similarity: SCN registration and the persisted EC `temporal_hash` (`similarity/signature.py`,
  `datetime.fromtimestamp`) bin on host-local time, so what an agent recalls depends on the host's time zone. The plan
  moves both with the stamp half; which calendar they bin on then is asked on #1787.
- **OD-A6:** reaction and pain dispatch gates (`reactions/bus.py::ReactionBus`, `proprioception/pain_bus.py`'s
  per-`(entity, failure_mode)` refractory) count the injected clock under embedding; motor and IO limits stay on the
  wall, with a check that no motor-dispatch path reads the injected clock. Lands after #1200. The plan (D-WC3) puts it
  in 1.3.6. `pain_bus.py` maps the bus as FUNCTIONAL, sharing the nociceptive pathway's role "with refractory gating";
  a body's refractory counts body time, which for an embedded agent is world time. At 20× a 0.5 s wall window is 10
  world seconds and drops distinct world events.

### 3.6 Randomness and ids (OD-A7)

Keyed substreams by `utils/seeding.py::make_agent_rng(base_seed, agent_id)` with a stream argument
(`npcs_and_sem.md` §3.4, O40); `similarity/semantic.py`'s `or 42` made an explicit seed; `seed_all` never called on
the embedded path; `decisions/nac.py`'s `time.time_ns()` event ids. **A new release-gate item after the 1.4.0 cut,
not a widened `1305.owned-rng`** (Maxim's owner, 2026-11-19). #1305 (open) keeps the global `random` / `np.random`
half.

### 3.7 The live path: which sites move, and where

| Subsystem | Overdrive id | Plan (tier A) | Placement in the A-pre plan |
|---|---|---|---|
| The split clock and the static ban | OD-A2 | A-pre | taken |
| Prompt and observation time | OD-A3 | A-pre | taken |
| Live-path stamps; `SensorReading` stamping; tool duration | OD-A4 | A-post | stamps with OD-A12, duration with B2 (fenced file) |
| Hippocampus window; salience stamps; phase source | OD-A5 | A-pre (window), A-post (the rest) | window and SCN renders taken; stamps A-post; salience with OD-A9; phase source stays host |
| Reaction and pain gates | OD-A6 | A-pre | 1.3.6, after #1200 |
| Randomness and ids | OD-A7 | after the 1.4.0 cut | after the 1.4.0 cut |
| Fenced ids and stamps (`agent_loop`, `orchestrator`, `tool_dispatch`), NAc stamps and anchors, `FailureMode.last_fired` (with #1361 S4) | OD-A8 | A-post | A-post |
| `Embodiment.evaluate_failures`'s `time.time()` drive drift (`embodiment/body.py`, about `:293`) | OD-I8 | a question to #1361 | #1361 S4 (Q4: drift only through `Embodiment.advance(dt)`) |
| The agent live tick (`llm_submit_interval`, `target_hz`) | — | the embeddable agent plan's `step` | — |

PR 0's census, not a grep in a plan, fixes the counts.

## 4. Maxim decisions this argues against, named and quoted

| Decision (verbatim) | Where | Status of the argument |
|---|---|---|
| "SCN phases, `TemporalSignature` similarity \| host calendar by design" | `experience_clock_decay.md` §(g) | *Superseded:* **OD-A20 declined** by Maxim's owner (2026-11-19). Event similarity stays on the host calendar; a known divergence, held by two strict red gates once the agent PR lands them (`npcs_and_sem.md` §12.2). The calendar is recast as perceived time: the port, not the SCN, is what a prompt reads. |
| "PainBus refractory, reflex cooldowns \| motor/IO rate limits; hardware safety" | same table | Argued: a dedup window counts world time under embedding (§3.5, OD-A6). Accepted (D-WC3). |
| M72's allowlist: "heartbeat, timeouts, scheduling, refractories, SCN phases, the driver's stall cap" | `outstanding.md` M72 | Argued: extend M72 to the embedded step path (OD-A2). Accepted: the A-pre plan amends M72 (D-WC4). |
| "`idle_sleep_s`, `target_period`, `llm_submit_interval`, the 120 s `_submitted_recently` window \| loop scheduling" | same table | *Superseded:* **OD-H6 withdraws** the loop-interval argument. Under a host-called `think` the submit cadence is the host's, so it needs no change for embedders; it lands inside cand. B1 (OD-A15). |
| G17: the session-id source "waits for the stage that needs it" | `DECISIONS.md` | *Superseded:* not argued now. G17 stands; ids are OD-A7's, after 1.4.0. |

**Corrected evidence (kept).** Hippocampus de-duplication on builtin `hash()` does not break determinism:
`_recent_observations` is in memory, never persisted, read in insertion order. The real breaks on that path are the
30 s wall window (OD-A5) and the `uuid4` memory id `observe` returns (OD-A7).

## 5. Order and the fence

- **The fence** (`roadmap_1_3_x.md`): "Nothing under `runtime/agent_loop.py`, `decisions/nac.py`'s selection path or
  `simulation/orchestrator.py` until the decomposition slices touching it have landed." This plan also treats
  `runtime/tool_dispatch.py` as fenced (#1150's 1.3.6 slice), which is why OD-A4's tool duration is A-post.
- **Overlaps:** #1361 S3 to S6 (1.3.6; A-post depends on them); `Embodiment.evaluate_failures` is S4's target
  (`last_fired`, OD-I8); the PainBus is rewired by #1200 first; #1263's remainder is the Default Network draft's.
- **CI cost (M83):** PRs are scoped to the census, not swept.

## 6. *Superseded:* the build

The PR list is Maxim's now: the A-pre plan's PR 0 to PR 5 for A-pre (PR 5 in 1.3.6), each red gate
`xfail(strict=True, raises=AssertionError)`. A-post's PRs follow the fence. This draft no longer carries an estimate.

## 7. Exit tests

| # | Test | Passes when |
|---|---|---|
| OD-WC1 | **Two runs, bit-identical.** One scripted host session (stub model with recorded responses), injected collaborators, twice in separate processes with different `PYTHONHASHSEED` | a canonical digest of the agent's persisted state is byte-identical, and every digested component changed during the script, proven by planting one wall stamp per component |
| OD-WC2 | **Wall pace doesn't matter.** The same session at 1× and 20× fake wall pace, with jitter | OD-WC1's digest is identical |
| OD-WC3 | **Pause.** The fake wall advances 30 s with no world steps | no drift, decay, habituation recovery or gate release; no real sleep |
| OD-WC4 | **No wall reads on the path.** The static ban at zero outside the allowlist on the step-path set, plus the long-horizon run | green, and each planted read goes red |
| OD-WC5 | **Robots unchanged.** The suite on host defaults; the golden under `_StepClock`; a pre-release robot home loaded and saved | green; the home round-trips byte-identically |
| OD-WC6 | **No host time in prompts.** The same embedded prompt in two processes with `TZ` 13 h apart | byte-identical |
| OD-WC7 | **Step size doesn't matter.** One world span stepped at 1, 2, 5, 10 and 50 ticks | continuous state agrees within a pinned relative 1e-9, on an exponential plant with `k·dt_max ≥ 1e-3` (Euler is exact on a linear one, so it can't go red) |

The A-pre plan takes OD-WC5, OD-WC6, OD-WC2 (A-pre scope) and OD-WC4 (static form, with the long-horizon run's A-pre
half) and leaves OD-WC1, OD-WC3 and OD-WC7 to A-post. OD-WC1 digests ids, which are OD-A7's, so it can't pass
before the 1.4.0 cut.

## 8. Owner questions: answered

1. Is embedding a supported use? **Yes** (owner, 2026-11-19; `decisions_entry_DRAFT.md`).
2. Should A-pre take its own patch number? **No:** D9 puts it in 1.3.5.
3. Should G17's `IdSource` be scoped to embedding now? **No:** G17 stands (D-WC1).
4. Should M72's allowlist be amended for the embedded scope? **Yes** (D-WC4).
