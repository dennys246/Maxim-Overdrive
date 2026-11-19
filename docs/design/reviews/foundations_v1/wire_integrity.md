# Design review: foundations v1 (boundaries v2, NPCs and SEM, Maxim drafts), Wire integrity lens

- **Lens:** Wire integrity (every data path the designs promise, traced from source to consumer; anything with no
  caller, no owner or a silently broken path)
- **Under review at commit 4f7a754:** `docs/design/boundaries.md` (v2, mainly §6, §7, §10 and §11),
  `docs/design/npcs_and_sem.md`, `docs/maxim_upstream/world_clock_release_DRAFT.md`,
  `docs/maxim_upstream/sem_breaking_change_plan_DRAFT.md`, `docs/roadmap.md` Phase 3
- **Code surveyed:** `phase1/act-validation` at 2f200b5 (`sem_env/bridge.py`, `world/world.py`, `tests/`,
  `scripts/lint_standards.py`)
- **Date:** 2026-11-16
- **Counts:** 4 BLOCKER, 12 SHOULD-FIX, 9 NIT

The interfaces are well named, but several of the paths they promise have no callee on one side. Two of those are
sequencing gaps: the code that owns a mechanism lands two or more PRs after the mechanism. The others are Maxim-side
gaps the designs don't admit. The thought path assumes the host sits between Maxim and its model, and nothing gives
it that seat. Mode (a) assumes the adapter can reach the pipeline and a second lane, and neither exists when mode (a)
lands. The world-clock draft assumes a required keyword reaches about 40 files of dataclass defaults. Paths traced:

| Path | Verdict |
|---|---|
| NPC intent: Maxim tool call → adapter → stage 1 → log → applier → receipt → settle → Maxim | breaks at adapter → pipeline (B2), at the wait (B2), and at settle (S12) |
| Client intent: protocol → gate → log | sound in boundaries; the receipt back to the client is unbound (N1) |
| Percept: frame → adapter → `SensorReading` → Maxim, time stripped | which frame a pull reads is unowned (S6); `timestamp` and `cell_size_m` leak (S6) |
| Thought: `request_thought` → thinking lane → cache → segments at modelled times → `deliver` | no Maxim entry point or interception point (B3); the cache key can't hit before A6 (S9) |
| Dilation by cause → host meters and client | no record kind, no protocol channel (S7) |
| Log header digests and environment | rig, engine version, the split material files and the digest form are missing (S8) |
| Per-NPC RNG seed from the header | crosses B-1 with no owner; counter keying is wall-dependent before tier A (S3) |
| Injected `Clock`/`Rng`/`IdSource` → every consumer in the draft | can't reach default-factory stamps without a silent default; `HostClock` isn't today's clock (B4, S1, S2) |

## BLOCKER

### B1. The write window and published frames land in 2c, but the code that owns them lands in sim-clock

`boundaries.md` §4.1, §4.2, §6.4, §11.1 (2c `phase1/gates`); `world_model.md` §10 (#2c before #4 `phase1/sim-clock`)

- §4.1: `with cells.writing():` "is entered only by `Simulation.step` … [and] construction". §4.2: "After each step
  the simulation publishes a frozen frame". 2c ships both. `Simulation` and its `step` are born in `phase1/sim-clock`,
  two PRs later (world_model §10 #4).
- On the shipped path after 2c, `execute` calls the applier synchronously, with no log (§6.4's TEMPORARY band-aid).
  The applier writes cells and `sources` outside any `Simulation.step`.
- **Failure scenario.** Either:
  - the window is honoured, and every `execute("strike", …)` raises on the write, so the shipped NPC path breaks; or
  - the applier opens the window itself. Then "a write anywhere else raises" is false, because any importer of the
    applier writes. It is also a second band-aid with no TEMPORARY marker and no roadmap row.
- **The same gap for frames.** `tests/test_sem_bridge.py:25-29` strikes, then reads `integrity < 1.0` and
  `breached == 1.0` with no `advance`. If 2c sensors read frames published "after each step" by `World.advance`, that
  read returns the pre-strike frame: a silent semantic change, or a test edited to pass.
- **Fix.** Name the 2c window owners explicitly: `World.advance` and the applier, with a `TEMPORARY(phase1/sim-clock)`
  marker on each, saying they move to `Simulation.step`. Also state that the applier publishes a frame after each
  application until sim-clock. Or move the window and frames into sim-clock. Either way, write it in §11.1.

### B2. Mode (a)'s execute can't reach the pipeline, and its world-time wait has no second lane to wait across

`boundaries.md` §2.2 (skip-layer rule; layer 7 vs layer 8), §4.2, §7.2; `npcs_and_sem.md` §6.1, §6.4;
`bridge.py::StructureModulator.__init__`, `::to_maxim_entity`, `::_on_region`, `::centroid_m`

- **No route in.** Mode (a) has `execute` "submit an intent through the one pipeline". The pipeline (log writer,
  sessions, lanes) is `engine.host`, layer 8. `engine.adapters.sem` is layer 7 and can't import it. No injected port
  (an intent sink, a frame source) is defined anywhere.
- **It still holds `World`.** §7.2 and npcs §6.4 keep `to_maxim_entity(world, region, actor=...)`. That contradicts
  §4.2 ("Nothing outside the simulation lane holds a reference to `World`").
  - Today `StructureModulator` holds `World`, and reads `World` for `limits`, the reach check (`_on_region`, region
    footprints) and the fire's centroid.
  - The skip-layer contract (adapters ↛ cells, geometry) goes red on the reach check in 2b. Nothing says whether it
    moves to stage 2 in the applier or stays in the gate half.
- **No request context.** Maxim's `Modulator.execute(affordance, params)` carries no request id and no segment time.
  §6.1 needs both: identity `(tick, actor, n)` "from the agent lane" (§6.1) and "the segment's modelled time" (npcs
  §6.1 step 2). They can only arrive ambiently, through modulator state or a context variable set by the thinking
  lane. That mechanism is unspecified, and it is the identity stamp, which is a trust property.
- **No second lane.** §8.1 lands the behavioural test "with mode (a) in sim-clock" (#4). The lane skeleton arrives in
  `phase1/protocol` (#6) and the thinking lane in `phase1/lanes` (#10). With one thread, `execute` blocking "until the
  next published frame" deadlocks. If `execute` advances the world to get unblocked, an NPC's tool call moves time,
  which breaks "only `World.advance` moves time" and the host's ownership of pacing.
- **Fix.**
  - Define the adapter's collaborators as required keyword-only ports: `submit(intent) -> receipt future`, and a
    frame source pinned per agent (S6), with no `World`.
  - Say where the reach and centroid checks go.
  - Define how the request id and segment time reach `execute`.
  - Move mode (a) to the PR that has two lanes, or state the single-threaded stepping rule for sim-clock.

### B3. The thought path has no Maxim entry point and no point where the host can intercept it

`boundaries.md` §7.1 (`request_thought`, `deliver`), §7.4, §8.1 (the agent-stepping surface);
`npcs_and_sem.md` §4.2, §4.4, §4.7, §6.1; `world_clock_release_DRAFT.md` §3

- **Two models.** §7.1 has the agent ask the host for a thought (`request_thought`) and the host `deliver` the
  result. npcs §6.1 has Maxim's own tool loop calling `execute` during an LLM turn that Maxim itself runs. These
  can't both be the path.
  - Today Maxim decides when to think: `llm_submit_interval` is 0.5 s of wall time (`loop_controller.py:157`).
  - Maxim calls the model itself, and consumes the model's output inside its loop.
  - So under mode (a) `deliver` has no Maxim callee, and `request_thought` has no Maxim caller.
- **The host isn't in the stream.** Every [now] mechanism in npcs §4 needs the host to sit between Maxim and the model:
  - stamping segments at modelled times;
  - holding an early result;
  - dilating while a segment is late (the host must know a segment is pending, and when the model has finished);
  - `cancel_on`;
  - the response cache.

  The only way in is to own Maxim's LLM backend. §8.1's agent-stepping surface ("stepping, clock and RNG injection,
  the experience driver, agent-state save") doesn't list it. Tier A and the world-clock draft mention only "a stub LLM
  with recorded responses" (E1). Whether Maxim's full loop accepts an injected backend is unverified anywhere.
- **No stepping callee either.** `AgentPort.step(now_tick, dt_ticks, frame) -> intents` has no Maxim callee before A3
  and A4. The draft puts A4 after Maxim 1.3.6 (§3.3, PR 8). Until then real Maxim runs its own wall-clock threads, so
  the "[now]" claims are unpassable with real Maxim:
  - "the substrate runs at tick boundaries" (§7.1);
  - npcs §3.1's dial-invisibility test;
  - npcs §6.1's "[now; tested against real Maxim]".
- **Fix.**
  - Pick one thought model for mode (a), and name the Maxim seam it needs: an injected LLM backend, verified against
    Maxim's code.
  - Add that seam to tier A, or to §8.1's surface with a roadmap id.
  - Say what `step` does before A3 and A4. Either a stub agent implements `AgentPort` and real Maxim is a strict red
    gate, or real Maxim runs free as a recorded OPEN divergence.

### B4. The world-clock draft's `AgentTime` reaches the entry point, not the consumers, and `HostClock` isn't today's clock

`world_clock_release_DRAFT.md` §3.1, §3.2 (the 36 `default_factory=time.time` stamps, PR 3), §6 E5

- **No route to the stamps.** §3.1 makes `AgentTime` "a required keyword on a new embedded entry point, so forgetting
  one is a `TypeError` rather than a silent wall-clock fallback". PR 3 moves the 36 `default_factory=time.time`
  fields, "mechanical, about 40 files", onto `Clock`.
  - A dataclass `default_factory` has no parameter that can carry the injected clock. It can reach one only through
    an ambient: a module global or a context variable.
  - An ambient whose default is `HostClock` is exactly the silent fallback §3.1 forbids.
  - With many NPCs in one process, and thoughts running on worker threads, a process global also can't tell agents
    apart.
- **Robots don't keep today's behaviour.** `Clock.now_us()` is "monotonic, in the host's microseconds", an int.
  Today's stamps are `time.time()`: epoch float seconds, persisted in agent homes (`saved_at`, NAc anchors,
  hippocampus records).
  - If `HostClock.now_us` is monotonic, a robot's stamps after the release compare against a clock that resets at
    reboot.
  - Either way their unit changes, and the homes saved before the release need a migration the draft doesn't
    mention.
  - E5 ("the existing suite, green") passes unless the suite loads a pre-release home. So the release's main
    promise, that it stays out of the breaking-change question, is unguarded.
- **Fix.**
  - Specify the injection mechanism for deep consumers: a context variable bound per stepped agent, with no default
    in embedded mode, so it raises if unset.
  - Make `HostClock` reproduce today's values exactly (epoch seconds), or add a persisted-stamp migration and a
    fixture test that loads a pre-release home.

## SHOULD-FIX

### S1. Three time inputs into one agent, with no invariant tying them

`world_clock_release_DRAFT.md` §3.1, §3.3; `boundaries.md` §7.1

- The agent receives `Clock.now_us()`, `DefaultNetwork.step(now_us)` (absolute) and
  `AgentLiveTick.step(world_dt_us)` (delta). Overdrive's port speaks ticks (`step(now_tick, dt_ticks)`).
- Nothing states that, under an embedder, `Clock.now_us` advances exactly by the stepped dts.
- **Scenario:** the adapter steps the live tick by `dt` but sets the clock at tick boundaries while running k reflex
  substeps (npcs §9 item 3). Drift integrates one time, and stamps and refractories read another. That is BF-11's two
  clocks, recreated inside Maxim.
- **Fix:** add one invariant and a test to the draft: under an embedder, `now_us` is set only by `step`, and the sum of
  the dts equals the change in `now_us`.

### S2. The draft's tripwire misses the sites the draft itself names, and its `Rng` default isn't today's behaviour

`world_clock_release_DRAFT.md` §3.1 (tripwire, `Rng` default), §2, §6 E4, E5

- **The tripwire misses.** It patches `time.time`, `monotonic`, `perf_counter`, `datetime.now` and the global
  `random`. It misses:
  - `time.time_ns` and `monotonic_ns`;
  - `time.strftime`, `localtime` and `ctime` with no argument. §2 names session ids from `time.strftime` (G17);
  - `datetime.utcnow`, `datetime.today` and `date.today`;
  - `uuid1` and `uuid4`. §2 names the 38 `uuid4` calls;
  - `os.urandom`;
  - numpy's global `np.random`. The audit counts only the stdlib `random`.

  So E4 can pass with every id site still on the wall. Overdrive's own denylist (`boundaries.md` §3) is wider; reuse
  it.
- **The default isn't today's.** The `Rng` default is "seeded from OS entropy, today's behaviour". Today's behaviour
  is the global `random` module, which tests can seed. Moving those sites to a per-agent generator seeded from entropy
  changes any test that relies on `random.seed`, and E5 could walk.
- **Fix:** make the default the global module. Enumerate the numpy-random sites too.

### S3. The per-NPC seed path from the log header has no owner across B-1, and counter keying is wall-dependent

`boundaries.md` §6.3, §7.3, §8.1; `npcs_and_sem.md` §3.4; `world_clock_release_DRAFT.md` §3.1; CLAUDE.md
(Determinism); `tests/test_determinism.py::NUMPY_RANDOM_ALLOWED`

- **Owner.** `AgentTime` (with `Rng`) is passed at the agent factory (draft §3.1). §8.1 puts `AgentFactory` in the
  game's NPC-authoring adapter, and "clock and RNG injection" in `engine.adapters.agents`. The engine can't import the
  game.
  - So it's unsaid who derives the stream from the header seed and hands it to the factory.
  - It's also unsaid whether actor ids are stable across save and load, which the keys `(run seed, actor, …)` need.
  - Stream counters must persist in the agent home (save v1), and that isn't listed.
- **Keying.** "Counter" keying means a draw depends on how many draws came before. Percept noise is drawn when Maxim
  pulls a sensor, which before tier A happens on Maxim's wall cadence. So the noise depends on the dial, which breaks
  the dial-invisibility test. Key percept noise by `(actor, stream, tick, sensor)`, not by a running counter.
- **Type mismatch.** Maxim's `Rng` is a stateful `random.Random` or `Generator` with named substreams (the type is
  open, §8). Overdrive wants a counter-based Philox. The draft should carry Overdrive's requirement.
- **Rule drift.**
  - CLAUDE.md still says randomness comes from "one seeded `numpy.random.Generator` owned by `World`", and
    `NUMPY_RANDOM_ALLOWED` admits `PCG64` but not `Philox`. Neither is in §11.2's doc list.
  - `engine.adapters` is exempt from the determinism scan (§3), so agent-side Overdrive code, which §4.7's reruns and
    E1 depend on, has no determinism guard at all.

### S4. The log record and kinds don't carry what part 2 sends through them

`boundaries.md` §6.1 (kinds table), §6.2 (record, ordering); `npcs_and_sem.md` §4.3, §4.4, §9

- **No sub-tick field.** npcs §9 orders intents by "tick, then sub-tick time, then actor, then sequence". The §6.2
  record has no sub-tick field, and §6.2 still says `(apply_tick, actor_id, seq)`. Two same-tick intents from one actor
  replay in `seq` order even when their modelled times say otherwise; that holds only if `seq` follows sub-tick order.
  Add the field and the order.
- **Missing kinds.** npcs logs cancellation ("decided at a tick … and logged", §4.3) and `thought_failed` under
  `abandon` (§4.4). Neither is a kind in §6.1.
- **`memory_write` has no consumer.** It is listed as an input "to the `Simulation`", but agent state lives outside
  `Simulation` (§7.1) and replay never runs Maxim. Either it is agent-home data, or say what replays it.
- **Two id shapes.** The request id `(tick, actor, n)` (§6.1) and the record's per-actor `seq` (§6.2) are two id
  shapes for one intent. Say which is the intent id that receipts carry.

### S5. Speech has no wire

`npcs_and_sem.md` §4.2 (P2), §4.3, §5; `boundaries.md` §6.1, §6.2, §9.1

- Speech is "an action that takes world time" and is interruptible. "Receipts for speech acts carry the spoken
  prefix", and the client "shows or voices each token at its time".
- But there is no `speak` kind in §6.1, no channel in the field registry (§9.1), and §6.2 keeps "LLM text and
  tool-call text" out of the log, while receipts are "derived … replay recomputes them". A receipt carrying the spoken
  prefix can't be recomputed from a log that holds no speech.
- Another NPC hearing the speech has no B-13 channel to perceive it through.
- Conversation is the core of Phase 4. Define the speech intent, its record (it must be logged, as text or as a
  digest plus a side file), its frame channel and its receipt.

### S6. Percepts: which frame a pull reads is unowned, and two leaks reach Maxim

`boundaries.md` §4.2, §7.3; `npcs_and_sem.md` §3.1, §6.1 step 5; `bridge.py::RegionSensor.read`,
`::to_maxim_entity`

- **Which frame?** Region entities are pulled: Maxim calls `RegionSensor.read()` when it likes. "Sensors type against
  a `Frame`" doesn't say which frame. In mode (a) the cerebellum reads sensors "during the call", after the wait.
  - With "latest published", at 20× several frames pass between the wait ending and Maxim's read. The cerebellum
    then trains on the effect plus N ticks of physics, which depends on the dial.
  - Define a frame pinned per agent: the observed frame normally, and the receipt's after-frame for the rest of a
    mode (a) call. The adapter owns the pin.
- **`timestamp` leak.** The schema test "no agent-facing type has a time field" fails on `SensorReading.timestamp`, a
  required field. Today the bridge fills it with `grid.time_s`, world seconds. Name the exemption, and say what value
  it carries before tier A, so the test isn't written to pass.
- **`cell_size_m` leak.** `extra={"cell_size_m": dx}` on every reading, and `metadata["cell_size_m"]` on the entity,
  put the rendering tier in front of cognition. Percepts then differ by rig. §11.2 decides the `source` string (W10)
  but not this; drop both or move them to an instrument.

### S7. Dilation by cause has no record kind and no channel to the client

`boundaries.md` §3 ("enters the `Simulation` only as recorded data"), §7.4; `npcs_and_sem.md` §4.1, §4.5, §12.1 Q2

- "Reported as dilation by cause" (deliberation, physics, substrate) has a producer (the host) and no defined
  consumer path:
  - no protocol message or registry channel for the client (the banner question needs a channel whatever its answer);
  - no meter name;
  - no record kind.
- The `Simulation` should never read it. A wall-derived number that the core consumes would make outcomes depend on
  the wall. Say it is log metadata the core never reads.

### S8. The log header is missing inputs a replay or a rerun depends on

`boundaries.md` §6.3; `world_model.md` F15; `npcs_and_sem.md` §4.7

- **No rig.** CLAUDE.md says "the intent log plus the scene and rig reproduce any session", and the header has no rig.
  If the rig still sets the grid until the truth constants absorb it (§2.2), a replay at another rig gives different
  bits and no mismatch is refused.
- **No version.** There is no engine SHA or `derivation_version` (F15), and no `tick_us` unless it is one of the truth
  constants (say so).
- **The split material table.** After the split it is two files (§8.2), the engine's and the content's. "The material
  table digest" must name both, plus the imagination budgets (game data, Q4).
- **No digest form.** Raw bytes refuse on a YAML comment change; a canonical form needs one canonicalizer. Say which.
- **Reruns (§4.7).** The pymaxim version, the response cache's digest and `data/agents/timing.yaml` decide a rerun,
  and none is recorded.

### S9. The response cache is an unregistered input, and its key can't hit before A5 and A6

`npcs_and_sem.md` §4.7; `boundaries.md` §5.3, §7.4

- **Unregistered.** The cache is read from disk, and its contents become thoughts and then intents. It isn't in the
  §5.3 gate table, so it gets no gate contract (versioned, strict, bounded).
- **Can't hit.** The key is "SHA-256 of the canonical request". Until A6, Maxim's prompt carries the host date and time
  (`prompt_builder.py:1104`), and until A5 its ids are `uuid4`. So every key differs between runs, and "[now]: a
  session with real LLM thoughts reproduces at any dial" reproduces nothing.
- **Fix.** Register the gate, and say what the canonical request excludes. Tag §4.7 [after A], or give it a strict
  red gate.

### S10. Phase 3 ids: stale numbers across the docs, two of them mapped to the wrong item

`docs/roadmap.md` Phase 3 (tier-prefixed since 35b9c3e) against:

- `boundaries.md`:
  - O2: "(P3)" → C1;
  - §4.3: "P4" → C8;
  - §5.3: "item 16's apply step" → C1;
  - §7.1: "#1361, items 11, 12, 15" → A1, A3, A4, A2/A5;
  - §7.2: "Until P2 gains a `stale` kind" → C2;
  - §9.3: "P2", "P4", "P3 with item 16";
  - §8.1 still says the design cites the old numbers "until that renumbering lands", but it has landed.
- `npcs_and_sem.md`:
  - §4.3: "items 7 and 13" → C9;
  - §6.2: "item 16" → C1;
  - §7.2: "P4" → C8.
- `world_clock_release_DRAFT.md` §3.3 and §5 PR 8: "Overdrive Phase 3 item 11", "item 12" → A3, A4. These drafts go to
  Maxim, where Overdrive's old numbers mean nothing.
- `sem_breaking_change_plan_DRAFT.md`:
  - S3: "P3 and item 16";
  - S4: "P2 … P7";
  - S5: "P1 (PR 1's item 11)";
  - S9: "P6";
  - S10: "P4", "P5".

  None of the plan's S-items cites its roadmap id.
- `hybrid_1_5_line_DRAFT.md`, lines 25 and 28: "item 11", "(12)", "(13)", "item 17".
- **Two wrong mappings:**
  - **Two clocks.** `boundaries.md` §7.3 and §13 close the two-clocks divergence with "item 10 and P5". Item 10 is
    the SCN phase (A7/B8) and P5 is `FailureMode.last_fired` (C8). npcs §12.2 closes the same divergence with "A2 and
    S2". The red gate would be flipped by whichever item someone reads first.
  - **S2.** npcs §8 maps S2 (`SensorReading.timestamp`) to "A2, C8". C8 is `world_set_axis` per part. S2 has no
    roadmap row of its own.

### S11. `boundaries.md` §9.3's paths disagree with the SEM plan, and two of its items have no home

`boundaries.md` §5.1, §9.3; `sem_breaking_change_plan_DRAFT.md` §2, §3; `npcs_and_sem.md` §8, §12.3

- **Four disagreements.** §9.3 marks four items "batched" that the SEM plan ships additively:
  - propose and settle (S3, `ModulatorReceipt`);
  - the `timestamp` meaning (S2);
  - affordance direction (S5, additive first);
  - the acting entity (S6, an injected key).
- **Two items with no home.** §9.3's "Reserved membrane metadata keys (BF-10), additive now" and "Deep-frozen
  `ModulatorResult`/`SensorReading`, batched" (§5.1 calls it "a candidate for the SEM breaking-change plan") appear in
  neither the SEM plan (its §3 lists four other changes) nor roadmap tier C.
  - BF-10's reserved keys matter on the shipped path. A metadata key named `success` overwrites the outcome (§8.1),
    and this is the only place that says so.
- **A stale claim.** npcs §12.3 says boundaries §9.3 still carries the two wrong asks. This commit already corrected
  them (lines 514 and 516).
- **Fix.** Make §9.3 cite the SEM plan's S-ids and the roadmap ids rather than restating paths. Add the two missing
  items to the plan and the roadmap. Drop §12.3's first bullet.

### S12. `settle` has no Maxim consumer under mode (a), and double credit is possible

`boundaries.md` §7.1 (`settle(receipts)`), §7.2; `npcs_and_sem.md` §6.1, §6.2

- **Double credit.** Under mode (a) the receipt reaches Maxim through the `execute` return. If the host also calls
  `settle` for the same intent, NAc books it twice. Nothing says `settle` is context-only or a no-op in mode (a).
- **Receipts nobody reads.** Intents returned from `step` (the substrate's own proposals) get receipts with no Maxim
  consumer until C1. Their outcomes are silently dropped, and it is an unrecorded divergence.
- **Fix.** Define `settle`'s behaviour per mode, with a test that each receipt is credited exactly once (zero times for
  stale).

## NIT

- **N1. The receipt back to the client is unbound** (`boundaries.md` §5.3, §7.2; `world_model.md` §10 #6
  `act_result`). Say that a client intent's receipt is the `act_result`. Also say when a stage-2 refusal at a later
  tick is sent, and to which session.
- **N2. The "opaque id" an NPC matches a receipt by** (§7.3) must not encode `(tick, actor, n)`, or the tick reaches
  cognition. The strip test must cover ids.
- **N3. `TEMPORARY(phase1/sim-clock)`** (§6.4).
  - `lint_standards.py::check_markers` checks the phase number, not the step, so the marker survives sim-clock
    unnoticed until Phase 1 closes. sim-clock's exit should assert that no `phase1/sim-clock` marker remains.
  - After sim-clock, the applier must be off the adapters' allowed surface (a contract), or the bypass outlives its
    marker.
  - Roadmap Phase 1 has no file list for the lint yet; 2b must add the adapter's new path.
- **N4. "ModulatorResults … replay recomputes them"** (§6.2). Replay never runs the adapter, so only receipts can be
  recomputed. The "per-tick digest" they are checked against isn't in the record or the header.
- **N5. W1's evidence was for a whole-package rename.** v2 splits `world/` across `cells`, `laws`, `scene` and `sim`
  (§11.1). There, git's directory-rename inference either sends a new file to the majority destination (possibly the
  wrong layer) or stops with a split conflict. Re-run the scratch experiment for the split. Extend §11.3's check to list
  every file git relocated by inference, for review.
- **N6. The lanes doc isn't corrected.**
  - §7.2 says `realtime_lanes_coop.md` §4.3 "is corrected". It isn't: its banner points at `world_v2.md`, and §4.3
    still makes `max_age_ticks` abandonment the default (line 239), which `phase1/lanes` will implement from.
  - §11.3 merges `phase1/realtime-design` after `phase1/design-v2`, which already carries that doc (the diff is the
    3-line banner). Say it merges as a no-op, or drop it from the order.
- **N7. "P" ids collide.** npcs' thought phases (P0–P3, Pn), world_v2's Maxim proposals (P1–P7) and world_model's
  physics findings (P1–P5) all use P. npcs §7.2's "P4, roadmap C8" sits beside the phases. Rename the phases (for
  example Φ0 to Φ3, or R/O/S/A).
- **N8. The time-strip tests have no landing PR.** The schema, prompt, dial-invisibility and Δt-invariance tests
  (§7.3, npcs §2.1, §3.1) have no row in §10's enforcement table.
- **N9. `data_dir()` has one root,** but v2 has two (`data/` for the engine, `content/` for the game, §8.2). W5's test
  covers only one. The content loader's root needs the same refuse-loudly test.

## The v1 wire findings (W1–W14) in v2

| v1 | v2 fix | Concrete? |
|---|---|---|
| W1 rebases into the game package | no game package until `phase1/lab`; post-rebase `--name-status` check (§2.1, §11.3) | yes; re-check for the split re-home (N5) |
| W2 scopes go engine-only | `source = ["src", "scripts"]`, test derived from `src/`, scan over every package with a floor, planted proof (§11.2) | yes |
| W3 lint-imports reads the main checkout | `PYTHONPATH="$PWD/src"`, grimp resolution test, preflight import (§10) | yes |
| W4 empty package, no caller | dropped (§2.1) | yes |
| W5 `_data` never exercised | target-equals-loader-package test, refuse when absent (§11.2) | yes for `data/`; `content/` not (N9) |
| W6 tier variable split | name kept, export-equals-read test (§11.2) | yes |
| W7 docs sed | by hand, reviews and research excluded (§11.2) | yes |
| W8 contracts unexpressible; guard step | `os` wholesale, planted imports incl. stdlib and unborn modules, B-12's tests half dropped, guard names the gate step (§3, §10) | yes |
| W9 merge order | named order, stale branches proposed abandoned (§11.3) | yes; the realtime-design entry is a no-op (N6) |
| W10 metadata `source` | fixed vocabulary value, pinned (§11.2) | yes; `cell_size_m` beside it is not decided (S6) |
| W11 Layout paths | listed for a hand update (§11.2) | yes |
| W12 stale bytecode | `git clean -fdX src/` (§11.2) | yes |
| W13 identity strings | `__version__` to the engine, distribution name kept (§11.2) | yes |
| W14 path-keyed exemption | package-qualified list (§11.2) | yes |

All 14 are folded concretely. The new gaps are in the paths v2 adds (B1 to B3), not in the migration.

## What I checked and found clean

- **The client intent path:** decode with the strict JSON decoder, stage 1, the log, stage 2. Identity comes from the
  session token and authority per kind (§6.1, §9.1). No gap in the server half.
- **Default-path removal** (`materials=` and `limits=` required) reaches the one caller that has a default today
  (`World.from_scene`'s `MaterialTable.load()`).
- **Tier ids within `roadmap.md`** are unique, and the Tier A rows match the draft's §3.2 subsystems.
- **`npcs_and_sem.md` §8's S-to-roadmap map** is correct for S3 to S10. S1 and S2 are covered in S10 above.
