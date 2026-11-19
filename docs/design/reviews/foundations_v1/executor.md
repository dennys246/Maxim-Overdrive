# Design review: Executor (foundations v1)

Lens: Executor, design-time. Commit: `4f7a754` (branch `phase1/design-v2`). Date: 2026-11-16. The questions: is
every factual claim true, and can every proposed check fail?

Documents: `docs/design/boundaries.md` (v2), `docs/design/npcs_and_sem.md`,
`docs/maxim_upstream/world_clock_release_DRAFT.md`, `docs/maxim_upstream/sem_breaking_change_plan_DRAFT.md`,
`docs/roadmap.md` Phase 3.

What I read them against:
- Maxim `main` at `4b773ef8`, read-only;
- the installed pymaxim 1.3.3 in the project venv;
- Overdrive `.worktrees/act-validation` at `2f200b5`.

Nothing in any worktree or in Maxim was changed. Anything marked *verified* was run in scratch copies under the
session scratchpad:
- import-linter 2.15 with grimp 3.18, on Python 3.10, against a copy of `act-validation/src`;
- two tripwire probes, one patching module attributes and one using a profile hook;
- an Euler-versus-closed-form step-size probe;
- greps over both Maxim trees.

Counts: **2 BLOCKER, 12 SHOULD-FIX, 5 NIT.**

## Verified true (sampled: 60+ citations)

Each of these says what the documents say it says, at the line given (`main` unless marked 1.3.3).

**Clock and cadence**
- `loop_controller.py:157` (`llm_submit_interval = 0.5`).
- `loop_state.py:240` (`_substrate_tick_due`, which compares against the wall at `:258`).
- `agent_loop.py:970` (`run_agentic_loop`, `target_hz=30.0`).
- `default_network/config.py:219` (`update_hz = 30.0`).
- `body.py:88` (`poll_hz = 1.0`) and `body.py:294-295` (`drift_dt = now - self._last_poll`).

**Prompts**
- `prompt_builder.py:1104` and `:2379` (`datetime.now()`), and `:232-236` (the date/time section).
- `llm_fallback.py:330, :334, :338`.

**SCN and oscillator**
- `temporal_signature.py:62` (`datetime.fromtimestamp`; 86400 is hard-coded at `:66`).
- `oscillator.py:193-194`: `integration_steps=1` and `dt=1/24`, so each observation moves the oscillator one hour.
- `zeitgeber_strength` is declared (`models/bio_context.py:199`) and never set.

**Determinism and stamps**
- `hippocampus.py:1055` (builtin `hash`) and `:290` (`dedup_window_s = 30.0`).
- `salience_map.py:227` (`current_time or time.time()`).
- `cerebellum.py:155, :453`; `spec.py:837`.
- `nac.py:439, :1167`; `reactions/bus.py:35, :81`; `experience_time.py:36`.

**SEM types** (`embodiment/sem.py`)
- `SensorReading` `:39-65` (`extra`, `timestamp` at `:64`); `ModulatorResult` `:69-78` (a one-line docstring and
  `metadata`).
- The SHAPE-FROZEN markers at `:107`, `:152`, `:173`, `:197`, `:233`.
- `drift_rate` "per second" at `:205` and `:240`; `modulated_by` only on the homeostatic spec (`:209`); `coupled_to`
  at `:244`.
- The `Modulator` protocol at `:785-811`, with `execute` at `:809`.
- `spec.py:278-313` parses `modulated_by` and `coupled_to`, and nothing outside `sem.py` and `spec.py` reads them
  (grep). "Never applied" is true.

**The tool path**
- `ModulatorAffordanceTool` is at `tool_bridge.py:394`.
- The cerebellum trains at `:864-892`, from `entity_state` read at `:585-590`, after `execute` at `:580`. Mode (a)'s
  premise holds: the reads come after the call's wait.
- In `tool_dispatch.py:356-375`, a neutral link "falls into NEITHER", and `not success` gives NEGATIVE.

**Maxim docs**
- `roadmap_1_3_x.md:358` (the fence, verbatim), `:1245` (#1361 S3–S6 with the 1.3.6 loop work), `:851-852` ("Breaking
  in places, a patch release by owner decision (2026-10-23)") and `:1176` (the atonia gate's own clock).
- `outstanding.md:123` (M72, a backlog lint) and `:130` (M79: pulse pins `pymaxim>=1.3.3,<2.0`).
- `DECISIONS.md:525-527` (G17, "No deterministic session id exists … wall-clock `time.strftime`"), and `:616, :621`
  (G3: "no uuid, no wall time"; "lockstep-testable").
- In `experience_clock_decay.md`: the §(g) rows `:286-288` verbatim; Q4 `:93-95` ("ONLY through
  `Embodiment.advance(dt)`", "No wall-clock fallback"); Q6 `:98`; the pause leak `:231`.
- `memory_strength_and_forgetting.md:787-788` (the one-clock policy).

**1.3.3 lines**
- `body.py:128, :502, :599`; `nac.py:3661, :4188`.
- `hippocampus_consolidation.py:113, :283, :453, :581`.
- `default_network/network.py:891-906`; `loop_substrate.py:56`; `substrate_proposal.py:871`; `hippocampus.py:1022`.

**Other claims**
- `stable_hash_64_signed` exists (`utils/seeding.py:121`).
- `SEM_PROTOCOL_VERSION` is absent.
- `ReachyOrientMotorBackend.execute` waits on the wall (`hardware/reachy/motor_backend.py:244-253`).
- `math/ips.py:41` sets `weber_fraction = 0.15`.
- `LLMEnergyTracker` counts tokens and latency.
- `tests/unit/test_cc3_forward_compat.py` does not cover `ModulatorResult`, so the CC3 gap is real.
- About 880 clock sites in about 215 files on 1.3.3: a broad grep gives 881 lines in 216 files.

**import-linter 2.15 (verified)**
- On Python 3.10 it installs grimp 3.18, and pip offers nothing newer on 3.10. That is consistent with 2.16 needing
  Python 3.11 or later.
- The `protected` contract type exists.
- A `protected` contract on `maxim` is KEPT on today's code and BROKEN by a planted `import maxim.embodiment.sem` in
  `world/heat.py`.
- A `forbidden` contract with stdlib targets (`time`, `datetime`, `pathlib`, `yaml`, with
  `include_external_packages`) fails on planted imports. It also reports today's indirect
  `world.scene -> config -> yaml/pathlib`, as boundaries §1 says.

## BLOCKER

### X-1. The tier-A tripwire cannot see most of what it claims to catch

`world_clock_release_DRAFT.md` §3.1 (the tripwire), E4 and §5 ("The tripwire turns any miss into a red test").

The design patches `time.time`, `time.monotonic`, `time.perf_counter`, `datetime.now` and the global `random` to
raise. *Verified* in a probe (`tripwire_probe.py`) that this cannot work as specified:

**Patching misses whole classes of sites**
- **`datetime.now` cannot be patched.** `datetime.datetime.now = …` raises `TypeError: cannot set 'now' attribute
  of immutable type`.
- **`field(default_factory=time.time)` holds the original builtin.** It was bound when the class was defined, so
  patching `time.time` afterwards does not reach it. A `Rec()` built after the patch still reads the wall. These are
  the 36 stamps of PR 3, the largest single class.
- **From-imports keep the original object.** There are 6 `from uuid import uuid4` and 12 `from datetime import
  datetime` imports on `main`.
- **Calendar conversions are not clock reads.** `time.localtime(ts)`, `time.strftime(fmt, …)` and
  `datetime.fromtimestamp(ts)` are not on the list. They are exactly how host local time leaks: the SCN (A7), and
  `context_pool.py`, see X-2.

**Patching also trips sites that are meant to stay on the wall**
- The patch is process-global. §3.2 keeps backend timeouts and heartbeats on the wall, so with any worker thread
  alive during a stepped turn, E4 goes red on correct code.

**The failure scenario:** PR 3 is half done, and E4 passes. Embedded agents still stamp every `memory/types.py` record
with the wall. The release's stated mitigation for an incomplete grep is the thing that misses.

**The fix:**
- Use a profile hook (`sys.setprofile` / `threading.setprofile_all_threads`, which is Python 3.12+) on `c_call`
  events. Match the function object itself (`time.time`, `time.localtime`, `datetime.now`, `os.urandom`, …), with a
  frame-based allowlist for the named wall sites.
- *Verified:* such a hook catches the `default_factory`, `datetime.now` and `localtime` calls the patch missed
  (`tripwire_profile.py`).
- Each class needs a planted call (a `default_factory` stamp, a from-import, a `fromtimestamp`, a timeout on another
  thread that must not trip) so that the check is proven able to fail.

Overdrive's own tripwire (boundaries §3) is safe for now, because the core bans those imports. It should still name
the profile mechanism, for the same reasons.

### X-2. `[now]` claims that real Maxim makes false: time in prompts, dial invisibility, reproducible reruns

`npcs_and_sem.md` §3.1, §4.7 and §6.1; `boundaries.md` §7.3.

**What the documents claim**
- §3.1 says, **[now]**: "The adapter strips every one [time field] before anything reaches an agent's … prompt".
- It adds a prompt test and a dial-invisibility test: "bit-identical percepts and prompts" at 1× and 20×.
- §4.7, **[now]**: with the recorded response cache, "a session with real LLM thoughts reproduces at any dial".
- Mode (a) is "tested against real Maxim".

**Why that cannot hold before tier A**
- **The adapter never builds Maxim's prompt.** Maxim builds it, and the adapter has nothing to strip.
- **Maxim writes the host date and time into the prompt:** `prompt_builder.py:1104` (`datetime.now()`), and the
  identity section takes `date_str`/`time_str` too (`:159`).
- **It also stamps each recent observation** `[HH:MM:SS]` in host local time (`agents/context_pool.py:468, :493`).
  That text goes into the live planning prompt (`runtime/agent_loop.py:2979`).
- **So the documented tests are red from day one.** The prompt test and the dial-invisibility test are red on real
  Maxim before tier A.
- **The cache never hits.** It is keyed by SHA-256 of the canonical request, and that request contains a clock that
  changes every second, so a rerun misses every entry.

**Tier A misses a site too.** `context_pool.py` is in none of these:
- the world-clock draft's §3.2 "Prompt time" row;
- PR 2;
- roadmap A6.

Once stamps come from an injected world clock, `time.localtime(world_ts)` still renders them in the **host time
zone**. That is the very co-op leak §2 of the draft describes.

**The failure scenario:** sim-clock lands the dial-invisibility test as specified against the mode (a) adapter, and
it fails, or it is quietly pointed at a stub where it cannot fail.

**The fix:**
- Tag these tests as strict red gates against real Maxim until A6, plus the new `context_pool` row, ship. List them in
  §12.2.
- Run the green half against a stub, with a planted leak: put the dial into a percept, and it must go red.
- Add `context_pool.py:468, :493` to the draft's §3.2, PR 2 and A6.
- Say that the §4.7 cache reproduces runs only after tier A, or key it on a request with time removed. That is a
  divergence, and it should be logged as one.

## SHOULD-FIX

### X-3. The counts: the true numbers, and how they were counted

Roadmap A5, `world_clock_release_DRAFT.md` §2 and `npcs_and_sem.md` §12.3.

All counts are `grep -rn --include=*.py` over `src/maxim` (`main`) and site-packages `maxim` (1.3.3):

| Pattern | `main` raw lines | `main` real calls | 1.3.3 raw | 1.3.3 real | Roadmap/draft | Audit |
|---|---|---|---|---|---|---|
| `uuid4(` | 38 | **36** (2 are a comment and a docstring: `hivemind/cli.py:655`, `time/temporal_event.py:28`) | 36 | 34 | 38 | 36 |
| global `random.{random,uniform,choice,gauss,seed,…}(` | 28 | **27** (`utils/seeding.py:37` is a docstring) | 28 | 27 | **39** | 28 |
| `default_factory=time.time` | **36** (in 19 files) | 36 | **36** | 36 | 36 | 35 |

**What the comparison shows**
- **"About 39 uses of the global `random`" has no basis.** The nearest count is 37: every `random.X` reference,
  which includes 9 seeded `random.Random(seed)` constructors. Those are local generators, not global state.
- **The audit's 35 is off by one** on both trees.
- **The roadmap and the audit don't really disagree on `uuid4`.** Each is a raw count of a different tree.
- **"Boundaries' summary of it repeats the audit" (§12.3) is false.** `boundaries.md` gives none of these numbers.

**The fix:** state 36 `uuid4` calls, 27 global-`random` calls and 36 stamps (19 files), each with the tree and the
pattern.

### X-4. The hippocampus `hash()` is not a determinism break, and Maxim's reviewers will say so

`world_clock_release_DRAFT.md` §2: "keys on builtin `hash()` … which Maxim's own CLAUDE.md forbids for values that
persist and which varies across processes". The same claim is in roadmap A5.

**Why the claim fails**
- `_recent_observations` is an in-memory dict (`hippocampus.py:499`). It is never persisted, and it is read in
  insertion order.
- The same text hashes equal within any one process. So the dedup outcome is identical under any `PYTHONHASHSEED`,
  except on a 2⁻⁶⁴ collision.
- Maxim's rule (`CLAUDE.md:109`) covers values "that cross a persistence boundary", and this one does not.
- The real determinism break at that site is the 30 s **wall** window (`:290`, `:1058`).

**The failure scenario:** the plan review strikes the claim, and the release loses credibility on a load-bearing
argument.

**The fix:** reframe it as hygiene (Overdrive's own rule is "no builtin `hash()` in the simulation"), and lead with the
window.

### X-5. CC3 is misquoted for `AffordanceSchema`, and "declare `metadata` the escape hatch" is not CC3 path (a)

`sem_breaking_change_plan_DRAFT.md` §1 and §3 (S5's `acts_on`).

**What the plan claims:** that on the marked types, "Adding any new field post-1.0 is a major-version-bump change".
That holds for `CouplingSpec` (`sem.py:155-156`).

**What `AffordanceSchema`'s own marker says** (`sem.py:113-116`): "All fields have defaults, so additive fields
appended at the end stay non-breaking. Adding a *required* field post-1.0 is a major-version-bump change." It also
quotes "Do NOT add fields … without a breaking-change plan."

So `acts_on` with a default may be a non-major change that needs a plan, not an entry in the breaking batch.

**The escape-hatch claim.** CC3 path (a) (`CLAUDE.md:105`) is "defaults on all fields + `extra: dict =
field(default_factory=dict, hash=False, compare=False)`". `ModulatorResult` falls short in three ways:
- it has five required fields;
- its free dict is named `metadata`;
- that dict has no `hash=False, compare=False`.

**The failure scenario:** the plan review rejects the first PR as "not path (a)", or `acts_on` sits in the breaking
batch that Maxim's own docstring says it needn't join.

**The fix:**
- Quote the `AffordanceSchema` text, and ask Maxim which rule governs.
- For `ModulatorResult`, choose path (b), a SHAPE-FROZEN marker with `metadata` documented as the extension channel.
  Otherwise propose amending CC3's path (a).

### X-6. S4's refusal key, and S3's `settles` key, never reach `tool_dispatch`

`sem_breaking_change_plan_DRAFT.md` S3 and S4. The roadmap's C1 and C2.

**What the plan says:** S4 is "a refusal-kind key in `ModulatorResult.metadata` … read by `tool_dispatch`". The code
can't deliver it that way:
- On failure, `tool_bridge.py:580-582` returns `ToolOutput(success=False, error=result.error)` and drops
  `result.metadata` entirely.
- `tool_dispatch` reads `side_effects`, never `metadata` (the bridge's own comment, `:962-966`).
- `tool_dispatch.py:370` books NEGATIVE on `not success` before any valence is read.

On success, metadata keys reach `tool_dispatch` only by explicit promotion, as `outcome_valence` is promoted
(`:967-970`). So S3's `settles` key must be promoted too, or the bridge cannot skip its in-call cerebellum observation
(`:864`) by a key it never reads.

**The failure scenario:** PR "S4" adds the key and a unit test on `tool_dispatch`'s input, and on the shipped path the
key is discarded. Stale refusals still book NEGATIVE.

**The fix:** name the bridge's failure return and the promotion step as part of S3 and S4. Each is still additive. Add
a test through `ModulatorAffordanceTool.execute`, not only `tool_dispatch`.

### X-7. PR 3 is neither mechanical nor about 40 files, and a `default_factory` can't take an injected clock

`world_clock_release_DRAFT.md` §5, PR 3.

**The sites:** there are 36 stamps in **19 files** (`agents/bus.py` has 8; `agents/autonomy.py` 4; `runtime/preemption.py`
3; `agents/context_pool.py` 3; …). Several are off the live path (`utils/web_cache.py`, `utils/output_watcher.py`,
`mesh/*`), against §3.2's "only sites an embedded agent reaches".

**The clock can't reach them.** A `default_factory` takes no arguments, so a per-agent `Clock` can reach it only
through ambient state, such as a contextvar or a module global. That state falls back to `HostClock` when unset, which
is exactly the "silent wall-clock fallback" that §3.1 promises to make a `TypeError`.

**The failure scenario:** one record type is built outside the scope where the clock is set, and it silently stamps
the wall. Only X-1's fixed tripwire would see it.

**The fix:** decide the mechanism in the plan. One option is an ambient clock that **raises** when unset in embedded
mode. The other is removing the defaults from live-path types and passing the stamp explicitly. Then re-size PR 3.

### X-8. The "Fenced?" column and the plumbing are wrong for PRs 2 and 5

`world_clock_release_DRAFT.md` §4 (the G17 row) and §5.

**Fenced sites the plan counts as unfenced**
- On the live path, run and session ids are minted in fenced files:
  - `agent_loop.py:149` (`run_id = time.strftime(…)`);
  - `agent_loop.py:661, :1462` (`uuid.uuid4()` thought refs);
  - `simulation/orchestrator.py:955` (`session_id`).
- So PR 5 is partly fenced.
- "`IdSource` closes" G17 depends on post-1.3.6 code.

**Plumbing no PR owns**
- No PR row carries the `AgentTime` plumbing: from `AgentFactory.create_full_agent` (`runtime/agent_factory.py:969`)
  to `LLMWorker`, which builds `PromptBuilder` (`agents/llm_worker.py:435`), and on to each subsystem.
- PR 1 is `utils/clock.py` only.
- PR 2 is sized S, yet it must thread a clock into `PromptBuilder` and `llm_fallback`'s callers. It must also carry the
  `context_pool` site (X-2).

**The fix:**
- Add a PR for the factory and entry-point wiring.
- Mark PR 5's fenced sites, or move them to PR 8.
- Re-size PR 2 as M.

### X-9. `Clock` can't produce three of `TemporalSignature`'s four phases

`world_clock_release_DRAFT.md` §3.1 (`epoch_s`, `day_length_s`), §3.2 and §4 (row 1).

`TemporalSignature.from_timestamp` takes the weekly, monthly and annual phases from `dt.weekday()`, `dt.day` and
`tm_yday` (`temporal_signature.py:66-76`). `epoch_s` plus `day_length_s` gives a circadian phase only.

**The failure scenario:** PR 5 gets there and has to choose silently. One choice keeps the host calendar for three
phases, which is the leak. The other sets them to a constant, which collapses Maxim's weekly, monthly and annual bins
and changes retrieval.

**The fix:** add a world calendar to the protocol (week, month and year lengths, or a `calendar(now_us)` function), or
state the decision for the other three phases.

### X-10. M76 is the wrong citation, and the decision to argue against is G4. M72's allowlist is a decision too

`world_clock_release_DRAFT.md` §4 (the last row); roadmap C10.

**M76**
- `outstanding.md:127`'s M76 is about `second_body_staging.md` and `microduck_intent_layer.md`, not the hybrid plan.
- The hybrid plan's trigger is at `deferred/hybrid_substrate_reflex_runtime.md:4`.
- Directly below it (`:5-7`) is owner decision G4 (2026-10-07): "this trigger is NOT re-keyed".
- Overdrive's rule is to "name the decision you're arguing against", so this has to be G4.

**M72**
- Its allowlist names "refractories, SCN phases" as staying on the wall (`outstanding.md:123`).
- A7 and A8 move exactly those off the wall. Reusing M72 as the tripwire's "static half" means amending that
  allowlist, and §4 doesn't list it.

**The fix:** add both to §4's table, with these citations.

### X-11. The step-size invariance test: name its tolerance and where the Euler update goes, or the plant can't fail

`npcs_and_sem.md` §2.1; `boundaries.md` §7.3.

*Verified* (one-hour τ, 0.1 s tick, one world hour, step sizes 1, 2, 5, 10 and 50 ticks):

| Update | Maximum relative spread across step sizes |
|---|---|
| Closed form `x *= exp(-k·dt)` | 1.25e-12 |
| Euler `x -= k·x·dt` | 6.8e-4 |
| Linear drift, clamped | 5e-13 |

**Why both choices matter**
- **The tolerance.** A "closed-form tolerance" left undefined, or set at 1e-3, passes the planted Euler update.
- **Where the plant goes.** In a linear process, Euler *is* exact, so a plant there can never go red.

**A gap in the tagging.** §2.1 tags Maxim's side **[after A]**, but no tier-A item or exit test covers step-size
invariance. E2 varies wall pace, not world step size.

**The fix:**
- Pin the tolerance (for example a relative 1e-9 on continuous state).
- Require the plant in an exponential process with `k·dt_max` of at least 1e-3.
- Add a tier-A exit test, or retag Maxim's half as unowned.

### X-12. The schema test, the prompt test and the protected contract, as written

**The schema test** (`npcs_and_sem.md` §3.1): "no agent-facing type has a time field".
- `SensorReading.timestamp` is a time field on an agent-facing type, and §3.1 itself exempts it. So the test is either
  red forever or relies on an allowlist the document doesn't name.
- `ModulatorResult.metadata` is a free dict, and a schema test can't see `apply_tick` inside it.
- **The fix:** a name rule plus an explicit exemption list, and a value-level test on the metadata keys the membrane
  actually emits.

**The prompt test.** "No clock string" by regex misses formats such as `%I:%M %p` and `[HH:MM:SS]`. A failable
alternative: render the same prompt twice, in processes with `TZ` set 13 h apart (`time.tzset()`), and assert the two
are byte-identical. Any rendering in host local time differs, because 13 mod 24 ≠ 0.

**The protected contract** (`boundaries.md` §8.1): the claim is that new root packages are "covered automatically".
That is false.
- *Verified:* a new root package `game` with `import maxim.embodiment.sem`, not listed in `root_packages`, gives
  **KEPT**. Listed, it gives **BROKEN**. grimp never builds a graph for an unlisted root.
- What `protected` does save is updating the importer list. It does not save updating `root_packages`.
- §10's tooling test, that grimp resolves each listed root, is the converse check.
- **The fix:** add a test that `root_packages` equals the set of top-level packages under `src/`.

### X-13. The documents disagree on what is additive, and npcs §12.3 is stale

**Boundaries §9.3 marks these "batched":**
- propose and settle at the tool;
- what `SensorReading.timestamp` means, and `drift_rate`'s time base;
- a declared direction per affordance;
- an acting-entity context.

The SEM plan (S1, S2, S3, S5, S6) and `npcs_and_sem.md` §8 make each of them additive first.

**One item is in neither place.** Boundaries batches "Deep-frozen `ModulatorResult`/`SensorReading`", and the SEM
plan's §3 breaking batch doesn't include it.

**npcs §12.3 is stale.** It says boundaries §9.3 still carries "the cerebellum honours `neutral`" and "finish
`modulated_by`", but `4f7a754` already corrected both (`boundaries.md:514, :516`).

**The failure scenario:** the owner, or Maxim, reads boundaries as the interface of record and plans a 2.0 for items
the SEM plan ships in 1.x.

**The fix:** align §9.3's Path column with the SEM plan, add or drop the deep-freeze item, and delete the stale bullet
in §12.3.

## NIT

- **N-1. Roadmap A1 says "#1361 S2–S6 (scheduled in Maxim's 1.3.6)".** Only S3–S6 are homed in 1.3.6. S2
  "coordinates with Session V's `simulation/` files" (`roadmap_1_3_x.md:366`). S0 and S1 have shipped.
- **N-2. Roadmap B2 cites `prompt_builder.py:159` for "You are Maxim".** The string is at `:167` on `main` (`:166`
  on 1.3.3). `:159` is `build_identity_section`'s signature. That signature does take `date_str` and `time_str`, so
  A6 should list it.
- **N-3. SEM plan S6: "the way it already injects `target`".** Only `OrchestratorActorTool` passes a resolved
  `target=<Entity>`. `ModulatorAffordanceTool` only fills declared YAML defaults (`tool_bridge.py:507-515`).
- **N-4. E3 and E2 in the world-clock draft.**
  - E3 sleeps 30 real wall seconds. That is slow, and it duplicates #1361's G4. Advance a fake wall instead.
  - E2 follows from E1 plus a working E4. Say what E2 catches that E4 doesn't, such as wall reads on threads the
    tripwire doesn't watch.
- **N-5. PR 1 is sized "S" (under 150 lines).** Three protocols, the defaults, `AgentTime`, a profile-hook tripwire
  with an allowlist (X-1) and a planted call for each class won't fit in 150 lines. Call it M.
