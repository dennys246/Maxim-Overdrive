# DRAFT for Maxim: a world clock for embedded agents, in two plans (A-pre and A-post)

**Status:** a proposal drafted in Maxim Overdrive on 2026-11-16, revised the same day after a seven-lens review
(Overdrive `docs/design/reviews/foundations_v1/`, especially the Maxim process, Executor and Wire integrity lenses).
It is for Maxim's process as **two plans**, each with a three-lens plan review, a one-page adversarial approach note
for its tripwire, and a three-lens code review per PR. Nothing is built, run or claimed. Everything is
`[engineering]`.

- **Read against:** `origin/main` `7084f561` (2026-11-16). Citations are `file::symbol`; a line number is a hint only.
- **Overdrive ids:** OD-A1 to OD-A8 (tier A). The stepped Default Network (OD-A9) has its own draft,
  `default_network_stepped_DRAFT.md`.
- **The two plans:**
  - **A-pre, on its own clock** (the atonia-gate precedent: "touches no decomposition-fenced file … holds nothing"):
    PRs that touch no fenced file. It takes the next free patch number when it ships.
  - **A-post, with 1.3.6** (owner: Session A): PRs that touch `runtime/agent_loop.py`, `simulation/orchestrator.py`,
    NAc's selection path or `runtime/tool_dispatch.py`, after the decomposition slices land.
- **Out of this release, now tier B** (`time_sense_DRAFT.md`): the oscillator's elapsed-time step and any entrainment.
  That change alters SCN dynamics under the host clock (§1), so it can't be in a release that promises robots are
  unchanged.

## 1. The claim, and what "done" means

**An embedded Maxim agent reads time, randomness and ids only from collaborators its host injects. Two runs of the
same host script leave it in bit-identical state however fast or slow the host's wall clock runs. Robots, the console
and pulse keep today's behaviour exactly.**

"Robots unchanged" is meant literally: the default collaborators return exactly what today's code reads, including
the units of persisted stamps, and the existing characterization golden still sees time through `_StepClock`.

## 2. Front gate: what this rides on, and why a new collaborator is still needed

| Existing | What it does | Why it isn't enough alone |
|---|---|---|
| `runtime/experience_time.py::ExperienceClockDriver` | advances an agent's experience clock from its **world's** time; a world declares itself by duck-typed members (`experience_turns()`, `experience_us_per_turn`) | It feeds memory strength and decay. It doesn't stamp records, pace the Default Network, render prompt time, mint ids or draw random numbers. **This plan builds on it:** an embedded world declares itself to the driver exactly as #1361 S2 declares a fixture (Q8, "a fixture 'turn' is step-clocked"), and the new clock reads the same world time. |
| `experience_clock_decay.md` (#1361), "adds no clock, no bus and no SCN surface" | the one-clock policy for memory | Respected. This plan adds no second experience clock. Its `Clock` is the host's world time for the sites #1361 leaves on the wall on purpose (§(g)), and only under embedding. |
| `utils/seeding.py::make_agent_rng(base_seed, agent_id) -> random.Random`, `seed_all` | per-agent RNG derivation | **Used as is** for embedded agents. The default stays the global `random` module, so `seed_all` keeps working and no test changes. |
| `tests/unit/_loop_harness.py::_StepClock`, `scripts/survival_world/scripted_water.py::StepClock`, `LockstepTime` (#951) | patch the global `time` to run the loop lockstep | A process-wide patch can't serve several agents, a Default Network thread or a host's own threads in one process. That's the reason for an injected collaborator. The new default must keep `_StepClock` working: `HostClock` reads `time.time` through the module attribute **at call time**, never binds it at import, with a test that `_StepClock.install()` still reaches it. |
| `DECISIONS.md` G17: "choosing the [session-id] source is a decision of its own, so the type waits for the stage that needs it" | defers deterministic ids to the post-fence resume stage | **Argued:** embedding is a stage that needs it (§5). The `IdSource` here mints ids for embedded agents only, and is offered to the resume stage to adopt or replace. |
| `DECISIONS.md` G3: tracks are "logical channels scheduled on the loop/tick clock: deterministic, lockstep-testable" | | Agreed and built on. |

## 3. The design

### 3.1 `AgentTime`: three collaborators, defaulting to today

| Collaborator | Surface | Host default (robots, console, pulse) | Embedded |
|---|---|---|---|
| `Clock` | `now() -> float` (epoch seconds, as every persisted stamp is today); `now_us() -> int` (monotonic microseconds, for durations); `calendar(now) -> Calendar \| None` | `time.time()` read at call time; `time.monotonic_ns() // 1000`; the host calendar | world epoch seconds (the host persists its world epoch); world µs; the world's calendar, or `None` when the embedder declares none |
| `Rng` | a `random.Random` | the global `random` module (today's behaviour) | `make_agent_rng(seed, agent_id)` |
| `IdSource` | `next_id(kind) -> str` | `uuid4().hex`, as today | `(agent, session, kind, sequence)`, no wall time |

- **One bundle on the embedded entry point** (the embeddable agent plan), as a required keyword.
- **The calendar** answers the Executor's X-9. `TemporalSignature.from_timestamp` takes weekly, monthly and annual
  phases from `dt.weekday()`, `dt.day` and `tm_yday`, so a clock with only `epoch_s` and a day length can't give them.
  - A `Calendar` carries day, week, month and year lengths and the components of a moment.
  - With `None`, an embedded agent computes no weekly, monthly or annual phase. That changes retrieval for embedded
    agents only, and the plan says so.
- **Persisted stamps keep their meaning.** Stamps stay epoch-second floats. Under embedding they are world epoch
  seconds, and the embedded home records that its clock is a world clock (its own format field). So no robot home
  changes, and the "hippocampus persistence schema change" trigger doesn't fire for robots.

### 3.2 How time reaches the 36 stamps

There are 36 `field(default_factory=time.time)` stamps in 19 files on `7084f561`. A `default_factory` takes no
argument, so an injected clock could reach it only through ambient state, a module global or a `ContextVar`. Maxim has
rejected a `ContextVar` back channel once already (`proprioception/pain_bus.py` module docstring: "re-entrancy …
invisible coupling"), and an ambient that falls back to the wall when unset is the silent fallback this plan forbids.

**Decision proposed: explicit pass, defaults kept.**
- Every construction site **on the embedded live path** passes its stamp from the agent's `Clock`.
- The `default_factory` stays, so robots and every off-path site are unchanged.
- The tripwire (§3.3) is what guarantees that no embedded construction falls back to the default. A missed site
  raises in a test, with the site named.
- Off-path stamps are out of scope (`mesh/*`, `utils/web_cache.py`, `utils/output_watcher.py`,
  `runtime/worker_pool.py`). A world-time stamp on a mesh message sent to another machine would be a wire bug.

### 3.3 The tripwire: a profile hook, not a patch

Patching module attributes can't work (verified by Overdrive's Executor lens in a probe):
- `datetime.datetime.now` is an attribute of an immutable type and can't be patched;
- a `default_factory=time.time` holds the original builtin, bound when the class was defined;
- from-imports keep the original objects: `from uuid import uuid4` appears in 5 files, and
  `from datetime import datetime` in more;
- calendar conversions (`localtime`, `strftime`, `fromtimestamp`) aren't clock reads, but they leak the host time
  zone;
- a process-global patch trips the wall reads that are meant to stay, such as backend timeouts on other threads.

**Proposed:** `sys.setprofile` on the thread that steps the embedded agent. It is thread-scoped by construction, and
Python ≥ 3.10 has it (`threading.setprofile_all_threads` is 3.12+ and is not used). On `c_call` events it matches the
called function **object** against a denylist:
- `time.time`, `time.time_ns`, `monotonic(_ns)`, `perf_counter(_ns)`, `localtime`, `gmtime`, `strftime`, `ctime`;
- `datetime.now`, `utcnow`, `today`, `date.today`, `fromtimestamp`;
- `uuid.uuid1`, `uuid.uuid4`, `os.urandom`;
- the global `random` module's functions, and numpy's global `np.random` functions.

It raises with the calling frame, except for a frame-based allowlist of the named wall sites (backend timeouts,
heartbeats, motor dispatch).

Each class gets a planted call that must go red: a `default_factory` stamp, a from-import, a `fromtimestamp`, a
`strftime`. And one planted negative: a timeout on another thread, which must stay green. The tripwire is a test-mode
guard. Its static half is M72's lint, amended (§4).

### 3.4 Prompt and observation time

These sites render host time into what the model reads:
- `agents/prompt_builder.py`: the datetime section and its `datetime.now()`, the identity section's
  `date_str`/`time_str`, and the search-synthesis `datetime.now()`;
- `agents/llm_fallback.py`: the canned "what time is it" and "today's date" answers;
- **`agents/context_pool.py`**: each recent observation is stamped `[HH:MM:SS]` with
  `time.strftime(..., time.localtime(entry.timestamp))`, and that text reaches the live planning prompt. This site was
  missing from the first draft.

Under an injected clock, each renders from the injected calendar, or is omitted when the embedder declares none. With
the host default, nothing changes. Rendering through `time.localtime` of a world stamp would still leak the host time
zone, so the embedded path never calls `localtime`.

**What the agent *believes* the time is** (an estimate from an entrained oscillator, coarse recency) is tier B
(`time_sense_DRAFT.md`), not this release. In Maxim's own robot use, host time in the prompt is intended. This plan
changes it for embedders only.

### 3.5 The live path: which sites move

| Subsystem | Sites (on `7084f561`) | Moves to | Plan |
|---|---|---|---|
| Prompt and observation time | `prompt_builder.py` datetime and identity sections; `llm_fallback.py` canned answers; `context_pool.py` observation stamps | injected calendar, or omitted | A-pre |
| Live-path stamps outside the fence | the subset of the 36 stamps an embedded turn constructs, listed by PR 0's census; `embodiment/spec.py` `SensorReading` stamping | explicit pass from `Clock` | A-pre |
| Hippocampus | the 30 s wall de-duplication window; capture and access stamps | `Clock` | A-pre |
| Reaction and pain gates | `reactions/bus.py::ReactionBus.DEFAULT_REFRACTORY_S`; `proprioception/pain_bus.py`'s per-`(entity, failure_mode)` refractory | `Clock` under embedding, with motor dispatch on the wall (§4) | A-pre, sequenced after #1200's PainBus rewiring |
| Attention and salience | `attention/salience_map.py` (and OD-I1's fix); salience stamps; inhibition of return | `Clock` | A-pre |
| `TemporalSignature` phase source | `time/temporal_signature.py::from_timestamp` (`datetime.fromtimestamp`) | the injected calendar (identical under the host default) | A-pre |
| Randomness and ids outside the fence | the global `random` and `uuid4` sites an embedded turn reaches, by census | `Rng`, `IdSource` | A-pre |
| Fenced ids and stamps | `agent_loop.py` (`run_id` from `time.strftime`, `uuid4` thought refs, 14 `time.time()` reads); `orchestrator.py` (5 `strftime` session ids); `tool_dispatch.py` (5 `time.time()` reads) | `Clock`, `IdSource` | **A-post** |
| NAc stamps and anchors | after #1361 S3b moves its windows to experience time | `Clock` | **A-post** |
| `FailureMode.last_fired` | `embodiment/sem.py::FailureMode` (`self.last_fired = time.time()`), in `Embodiment.evaluate_failures`, which is pinned at 224 lines and is #1361 S4's target | `Clock`, with S4 | **A-post** |
| The agent live tick | `loop_state.py::_substrate_tick_due`, `loop_controller.py` `llm_submit_interval`, `run_agentic_loop(target_hz=30.0)` | the embeddable agent plan's `step` | **A-post** |

PR 0 prints the census; plans don't carry volatile counts.

## 4. Maxim decisions this argues against, named and quoted

| Decision (verbatim) | Where | The argument |
|---|---|---|
| "SCN phases, `TemporalSignature` similarity \| host calendar by design" | `experience_clock_decay.md` §(g) | Keep it as the **default**. Under embedding, the calendar must be the injected one: the host calendar is another universe's, so NPCs would live on the player's time zone and daylight saving. This changes the source, not `TemporalSignature`'s fields. |
| "PainBus refractory, reflex cooldowns \| motor/IO rate limits; hardware safety (embodiment brief §1)" | same table | **Fairer framing than the first draft's.** The PainBus gate is, in Maxim's own words, a per-`(entity, failure_mode)` dispatch gate that "prevents two distinct embodiment failures … from collapsing into one dispatch" (`pain_bus.py` docstring; "Bio-mapping: FUNCTIONAL … does NOT implement … sensitization kinetics"). It is an `[engineering]` de-duplication gate, not perceptual refractoriness, and this plan claims no perceptual basis for it. The argument is only about **which clock** a dedup window counts. Under embedding it counts world time, because at 20× a 0.5 s wall window is 10 world seconds and drops real, distinct world events. Motor and IO rate limits stay on the wall, guarded by a check that no motor-dispatch path reads the injected clock. |
| M72's allowlist: "heartbeat, timeouts, scheduling, refractories, SCN phases, the driver's stall cap" | `outstanding.md` M72 (owned by `experience_clock_decay.md` §Enforcement) | Amend it: under embedding, refractories and SCN phase sources read the injected clock. The lint gains an "embedded path" scope. This is an amendment for the owning plan to accept, not a silent re-scope. |
| "`idle_sleep_s`, `target_period`, `llm_submit_interval`, the 120 s `_submitted_recently` window \| loop scheduling; no longer pace decay" | same table | True once S3a lands, but they still pace the substrate's proposals, which sets reflex latency in world time. The embedded `step` replaces them for embedders; robots keep them. |
| G17: the session-id source "waits for the stage that needs it" | `DECISIONS.md` | Embedding needs it now. `IdSource` is scoped to embedded agents and offered to the resume stage. |

**Corrected evidence.** The first draft said hippocampus de-duplication on builtin `hash()` breaks determinism. It
doesn't. `_recent_observations` is an in-memory dict, never persisted, read in insertion order, and consistent within
a process. The real breaks on that path are the 30 s **wall** window and the `uuid4` memory id that `observe` returns.
A `stable_hash` swap is offered as hygiene only.

## 5. Order and the fence

- **The fence** (`roadmap_1_3_x.md`, verbatim): "Nothing under `runtime/agent_loop.py`, `decisions/nac.py`'s selection
  path or `simulation/orchestrator.py` until the decomposition slices touching it have landed." It lifts when 1.3.6's
  slices land. This plan also treats `runtime/tool_dispatch.py` as fenced, since it's #1150's 1.3.6 slice target.
- **Overlaps, and who owns them:**
  - **#1361 S3–S6** are scheduled with 1.3.6. A-post depends on them and doesn't duplicate them. S2 coordinates with
    Session V's `simulation/` files.
  - **`Embodiment.evaluate_failures`** is pinned at 224 lines and is S4's target. `last_fired` moves with S4, under
    "touch it, shrink it".
  - **The PainBus** is rewired by `tool_failure_credit.md` (#1200) in 1.3.6. The refractory clock change lands after it.
  - **`llm_fallback`** overlaps 1.3.6's exit item "the `_llm_unavailable` fallback leaves `run_agentic_loop`". The
    canned-answer change follows it.
  - **#1263's remainder**, for the Default Network: see `default_network_stepped_DRAFT.md`.
  - **CI cost (M83):** a sweep across many files restarts every parallel PR's CI. PRs are scoped to the census, not
    swept.

## 6. The build

Sizes: **S** under about 150 changed lines, **M** about 150–600, **L** over 600 or touching the loop. Each PR lands
red gates first (`xfail(strict=True)`, flipped in place).

Overdrive ids:
- **OD-A1:** #1361 S3–S6, a dependency, not built here.
- **A-pre:**
  - OD-A2: PRs 1–2;
  - OD-A3: PR 3;
  - OD-A4: PR 4;
  - OD-A5: PR 5;
  - OD-A6: PR 6;
  - OD-A7: PR 7.
- **A-post:** OD-A8, PRs 8–10.

### A-pre (own clock)

| PR | What | Size |
|---|---|---|
| 0 | Red gates for §7; the census of embedded-path sites (stamps, ids, randomness, calendar conversions) printed by a script | S |
| 1 | `AgentTime`: `Clock`, `Rng`, `IdSource`, `Calendar`, the host defaults (call-time reads; `_StepClock` test), the profile-hook tripwire with its allowlist and planted calls | M |
| 2 | Wiring: `AgentTime` from the embedded entry point to `LLMWorker`, `PromptBuilder` and each subsystem on the path | M |
| 3 | Prompt and observation time (§3.4), including `context_pool` | M |
| 4 | Live-path stamps outside the fence, by explicit pass (§3.2); `SensorReading` stamping | M (re-sized after the census) |
| 5 | Hippocampus window and stamps; attention and salience; `TemporalSignature`'s phase source | M |
| 6 | Reaction and pain gates on `Clock` under embedding, with the motor-dispatch guard (after #1200) | M |
| 7 | Randomness and ids outside the fence | S |

### A-post (with 1.3.6, Session A)

| PR | What | Size |
|---|---|---|
| 8 | Fenced ids and stamps: `agent_loop.py`, `orchestrator.py`, `tool_dispatch.py` | M |
| 9 | NAc stamps and anchors (after #1361 S3b); `FailureMode.last_fired` (with S4) | M |
| 10 | Flip §7 on the shipped embedded path; docs; changelog fragment; M72 amended and enforcing | M |

The stepped agent tick is the embeddable agent plan's `step`. The stepped Default Network is its own draft.

**Estimate: 11 PRs.** A-pre has 8 (2 S, 6 M); A-post has 3 (3 M). The honest uncertainty is PR 4. The census, not a
grep in a plan, fixes its size, and the tripwire catches what the census misses.

## 7. Exit tests

| # | Test | Passes when |
|---|---|---|
| OD-WC1 | **Two runs, bit-identical.** One scripted host session (percepts, actions, a stub model with recorded responses), injected `AgentTime`, run twice in separate processes with different `PYTHONHASHSEED` | a canonical digest of the agent's persisted state is byte-identical, **and every digested component changed during the script** (non-vacuity), proven by planting one wall stamp per component |
| OD-WC2 | **Wall pace doesn't matter.** The same session with a fake wall clock advancing at 1× and 20× of world time, with jitter | OD-WC1's digest is identical. This catches wall reads on threads the tripwire doesn't watch. |
| OD-WC3 | **Pause.** The fake wall advances 30 s with no world steps, mid-script | no drift, decay, habituation recovery or gate release during the pause. No real sleep. |
| OD-WC4 | **No wall reads on the path.** The tripwire armed for a whole embedded turn | no raise, and every planted call goes red |
| OD-WC5 | **Robots unchanged.** The existing suite on host defaults; the characterization golden under `_StepClock`; a pre-release robot home loaded and saved | green; the golden still sees time; the home round-trips unchanged; no ledger row walks (the plan review lists any that would) |
| OD-WC6 | **No host time in prompts.** The same embedded prompt rendered in two processes with `TZ` set 13 h apart | byte-identical, so nothing renders in host local time |
| OD-WC7 | **Step size doesn't matter.** The same world span stepped at 1, 2, 5, 10 and 50 world ticks | every continuous state the step touches (drives, decays, gate windows) agrees within a pinned relative 1e-9. The plant is an Euler update in an **exponential** process with `k·dt_max ≥ 1e-3`; in a linear drift Euler is exact, so a plant there can't go red. |

## 8. Impact, enforcement and owner questions

- **Impact (ledger rows):** PR 0's census lists any ledger row whose evidence reads a site this plan moves under the
  host default. None should, because the host default reproduces today's values. The plan review checks this by row
  id.
- **Regression guards**, one per new `[engineering]` invariant:
  - "Embedded agents get no wall-clock fallback": OD-WC4.
  - "Motor dispatch never reads the injected clock": a planted motor call under the tripwire's negative list.
  - "`HostClock` reads at call time": the `_StepClock` test.
- **Owner questions, asked together at the start:**
  1. Is embedding a supported use (`decisions_entry_DRAFT.md`)?
  2. Should A-pre take the next free patch number on its own clock?
  3. Should G17's `IdSource` be scoped to embedding now, or wait for the resume stage?
  4. Should M72's allowlist be amended for the embedded scope?
