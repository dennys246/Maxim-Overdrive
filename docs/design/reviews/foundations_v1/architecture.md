# Design review: foundations v1 (boundaries v2, part 2, the two Maxim drafts, roadmap Phase 3), Architecture lens

- **Lens:** Architecture (right cut, right layer and owner, root cause or band-aid, standing rules, honest docs)
- **Commit:** 4f7a754 (`phase1/design-v2`)
- **Date:** 2026-11-16
- **Documents:** `docs/design/boundaries.md` (v2, delta round), `docs/design/npcs_and_sem.md` (part 2, new),
  `docs/maxim_upstream/world_clock_release_DRAFT.md`, `docs/maxim_upstream/sem_breaking_change_plan_DRAFT.md`,
  `docs/roadmap.md` Phase 3
- **Read against:** CLAUDE.md, `docs/code_review.md`, `world_model.md` (§10, and the hand-off list at its end),
  `world_v2.md` §6, `realtime_lanes_coop.md` §4, `research/time/`, the v1 reviews in `reviews/boundaries/`, and the
  code at `.worktrees/act-validation` (2f200b5). Maxim surfaces checked in the installed pymaxim 1.3.3.
- **Counts:** 3 BLOCKER, 15 SHOULD-FIX, 9 NIT

## Summary

Boundaries v2 is a large improvement on v1. The package, core and gate cuts are mostly right now: deny-by-default
core, writers moved inside it, ownership-based write window, source-keyed input guard, typed canonical log record.
Most v1 findings really are folded (spot-check below).

The new material doesn't compose yet. It's the agent half: `AgentPort`, mode (a), the "agent lane", and part 2's
thought cost.
- No document defines the lane that runs the agents. The accepted lanes design still says the simulation lane owns
  the agents.
- Mode (a)'s world-time wait, combined with part 2's "dilate by default" host policy and a finite worker pool,
  deadlocks.
- The interfaces that part 2's thought-cost design depends on (held early results, streamed and interruptible
  tokens, a response cache keyed on the request) need the host to own the LLM call. `AgentPort` doesn't model that
  ownership, and Maxim's `LLMBackend` seam doesn't offer it.

The four documents also disagree on how each SEM item ships (boundaries §9.3 against the SEM plan, on five rows).
Part 2 extends the log record without listing the change, and has no fold table for the world_v2 findings that
world_model handed to it.

## BLOCKER

### B1. `boundaries.md` §3, §4.3, §5.3, §6.1, §7.1; `npcs_and_sem.md` §7.2 :: the "agent lane" exists in no lanes design, and the accepted one contradicts it

- **What v2 says.** Real Maxim "runs in the agent lane through `engine.adapters.agents`" (§3). The agent lane runs
  `AgentPort` (§7.1), does the push path (§4.3), and issues request ids `(tick, actor, n)` (§5.3, §6.1). Part 2 §7.2
  repeats this.
- **What the accepted lanes design says** (`realtime_lanes_coop.md` §4.1, §4.2, §4.3):
  - there are four lanes: simulation, network, thinking (a worker pool) and record;
  - the simulation lane "owns Simulation (and through it World and agents)", and "agents step inside the simulation
    lane's tick";
  - request ids are "assigned by the simulation lane";
  - a thought's result is "a pure value", and "the model never touches World or agent state from the thinking lane".
- **What is superseded.** Part 2 §11 supersedes five §4.3 sentences. Nothing supersedes §4.1 or §4.2, so `phase1/lanes`
  (world_model §10 #10, "part 2 specifies the thinking rules") is built from two designs that disagree on who owns
  the agents.
- **The concurrency hole this hides.** Under mode (a), which is the only mode now, Maxim's tool loop runs during an
  LLM turn (part 2 §6.1 step 1). Today that loop writes the hippocampus and NAc inside the call. Part 2 §6.2 concedes
  that the "pure value" holds only after C1. So a Maxim agent is mutated by two contexts: the turn, in a thinking
  worker, and `AgentPort.step` plus the `world_set_axis` push, in the "agent lane".
- **Failure scenario.** In `phase1/lanes`, NPC A's turn runs in worker 1 and writes NAc links. Meanwhile the agent
  lane steps A's `Embodiment.advance` and pushes `vital_metrics`.
  - Maxim's agent state is not thread-safe for this, and nothing in either design says it must be.
  - The cerebellum's in-call sensor read (`tool_bridge.py:580-590`) races the push.
  - The rerun reproducibility part 2 §4.7 claims then depends on thread scheduling.
- **Fix.**
  - Write the lane topology once. Is the agent lane a new lane, or the thinking lane? Which thread may touch a given
    Maxim agent? (Recommendation: one owner per agent. The turn and the substrate step for one NPC are serialized on
    that NPC's owner, and only the LLM call itself leaves it.)
  - Supersede lanes §4.1 and §4.2 explicitly, in part 2 §11, or in a lanes delta that world_model §10 #10 cites.

### B2. `boundaries.md` §7.2 (mode (a)) + `npcs_and_sem.md` §4.4 (dilation is the default) :: the two compose into a deadlock, and part 2 reinstates a twice-rejected blocking hold without its fixes

- **Mode (a).** `execute` blocks the calling Maxim turn "in world time" until the intent's receipt and the next
  published frame exist (§7.2; part 2 §6.1 step 3).
- **Part 2 §4.4.** "The host does not step past a segment's modelled time until that segment has arrived." That is the
  default for live play, not only for headless cradles.
- **Failure scenario.** Use part 2's own §4.5 setting: one local model, so one thinking worker.
  - NPC A's turn emits a tool call whose modelled time is tick 115, and blocks in `execute` waiting for tick 115. It
    still holds the worker, because Maxim's turn isn't finished.
  - NPC B has a thought queued, due at tick 110. It can't start, because the worker is held.
  - The host stops at tick 110 waiting for B. A waits for the host to reach 115. B waits for A's worker.
  - Nothing advances, and part 2 has no rule that breaks the cycle. The cycle exists whenever workers are fewer than
    turns blocked in `execute` plus thoughts due earlier than their apply ticks.
- **Prior record.** This is the wall-time hold that `reviews/realtime_lanes_coop/concurrency_performance.md` BLOCKER 3
  rejected. `reviews/world_v2/determinism_lanes_performance.md` B-2 rejected it again when world_v2 reintroduced it for
  cradles. Its fix had five parts:
  - the wait is a state of the simulation lane on one multiplexed inbox, with `stop` and crash messages;
  - a timeout becomes a logged worker failure;
  - dispatch is by deadline;
  - the mode is refused while a network session can attach;
  - tests with a stub that never answers.

  Part 2 makes the hold the live default and cites neither review. world_model's hand-off list gives DLP-B2 to part 2
  ("Not in this part (part 2 or 3): DLP-B2, S-1, S-2 and S-5"). Part 2's early-result hold also lacks DLP S-1's rules:
  where held results live, whether that buffer is saved state, and what the log records.
- **Also overstated: "(a) → (b) is an adapter change, not an engine refactor"** (O2, §7.2, part 2 §6.2). Mode (a)
  is the reason a worker blocks inside a Maxim turn. Mode (b) removes that. So the thinking lane's scheduling, and its
  deadlock-avoidance rule once written, differ between the modes. That is a host change.
- **Fix.**
  - Fold DLP B-2 and S-1 into part 2 §4.4, by id.
  - State the no-deadlock invariant: a turn blocked in `execute` never holds the resource that an earlier-due thought
    needs. Either separate Maxim turn threads from LLM slots, or dispatch by deadline and let the host's wait set
    count only thoughts that hold a worker.
  - Test it with one worker, two NPCs, and the tool call due after the queued thought.
  - Correct the "adapter change only" claim.

### B3. `boundaries.md` §7.1, §7.4; `npcs_and_sem.md` §4.2–§4.7 :: `AgentPort` is not the seam that real Maxim's thoughts pass through, so part 2's thought-cost design has no interface to stand on

- **What part 2 needs.** Part 2 §4 depends on the host controlling the LLM call:
  - an early result is held until its modelled time;
  - a segment boundary falls at each tool call, and "the tool call's world time comes from the model, not from when
    the GPU emitted it";
  - tokens are streamed, stamped with world-microsecond offsets, and interruptible;
  - responses are cached by a SHA-256 of the canonical request (§4.7).
- **What the documents give it.** `AgentPort`'s `request_thought` / `deliver(thought_result)` (§7.1) model the host
  making the call and delivering a result. Under mode (a), though, the call is made by Maxim's own LLM router inside
  Maxim's tool loop. The host never sees a "thought result". It sees an `execute` callback in the middle of the turn.
- **The only seam that could carry part 2's rules** is Maxim's `LLMBackend` protocol
  (`maxim/models/language/backend_protocol.py`). The host would implement a backend that blocks `complete()` until
  the modelled onset. But that protocol is synchronous and returns the whole response (`complete() -> str`,
  `complete_with_usage(..., stream: bool) -> LLMResponse`). It has no token iterator and no cancellation.
- **Missing upstream.** Three needs aren't in Phase 3:
  - streamed speech with world-time stamps;
  - an interrupted reply whose memory "records what it actually said" (part 2 §4.3). Maxim writes the reply it
    generated;
  - an injected backend on the embedded factory.

  C9 (cancellable deliberation) covers none of them.
- **Layer problem.** `request_thought` is drawn as "agent → host". `engine.adapters.agents` is layer 7 and the host is
  layer 8, so implementing it as drawn is an upward import. The service protocol it would need below layer 7 isn't
  defined.
- **Direction problem.** `step` is drawn as "sim → agent". If `Simulation` calls it, real Maxim runs in the sealed
  tick, which §7.1 forbids. If the host calls it, the label is wrong, and the "dependency inversion" justification for
  putting the port in the core doesn't apply.
- **Failure scenario.** `phase1/lanes` implements `request_thought`/`deliver` with the test stub (fine). The first
  real-Maxim run then finds:
  - Maxim's router calls its own backend;
  - nothing holds an early tool call, so the tool call's apply tick becomes wall-dependent (lesson 1's class of bug);
  - the cache never hits, because the prompt carries the host date (A6);
  - speech can't be cut mid-stream.

  The fix would then be a band-aid around Maxim's router, which the push-back rule forbids.
- **Fix.**
  - Name the seam. The adapter injects a host-owned `LLMBackend` and makes it the thought gate. Add it to
    `engine.adapters.agents`' declared surface (§8.1).
  - Split `AgentPort` into the port the host calls (`step`, `settle`) and a host service protocol, defined in
    `engine.sim` or `engine.intents`, that the adapter receives as a required keyword argument (`request_thought`,
    the wait).
  - Add Phase 3 items for the streaming, cancellation and spoken-prefix memory that part 2 §4.3 needs. Otherwise mark
    those mechanisms [after C-x], not [now as interfaces].

## SHOULD-FIX

### S1. `boundaries.md` §2.2, layers 5 and 7 :: "siblings on one line are independent" is false as designed, which is v1's N1 / X S-2 again

- **Layer 5** (`scene | intents | imagination`). The `imagine` intent's stage 1 is "spec constructors" (§5.3), and
  the intent record carries a spec. So `engine.intents` imports `engine.imagination`, or the reverse, if
  `parse_action` dispatches to it.
- **Layer 7** (`loaders | encoding | protocol | adapters.sem | adapters.agents | tiers`):
  - the protocol encodes frames whose `crack`, `glow` and float16 temperature come from `engine.encoding` (§8.3);
  - `color_rgb` is "`engine.tiers`/`encoding`" (§8.2);
  - `adapters.agents` builds each NPC's entities and pushes percepts through the membrane's types, so it almost
    certainly imports `adapters.sem`.
- **Failure scenario.** `phase1/boundaries` commits the contract in the written order (§2.2 "checked red-first on
  today's code"). It's green on day one only because these modules don't exist yet. `phase1/protocol` then goes red
  on protocol → encoding, and someone switches the line to `:`, which v2 itself forbids.
- **Fix.**
  - Layer 7: say which of these import which, and give each dependent its own sub-layer, for example
    `tiers < encoding < protocol` and `adapters.sem < adapters.agents`. Or say that the host composes them, so the
    siblings stay independent.
  - Layer 5: put the `imagine` intent type where the import points.

### S2. `boundaries.md` §2.2 skip-layer rule, §4.1, §11.1 :: the restricted importers need what the rule forbids, and two writers sit outside the core

- **The gate half needs geometry and cells.** The half of `StructureModulator` that stays in `adapters.sem`
  (§6.4) needs:
  - region footprints in metres (`_on_region`, `bridge.py:281-300`), which is `engine.geometry`;
  - the name rule `entity_key` (`bridge.py:29, :341`, today in `world.grid`), which is `engine.cells`;
  - `engine.checks.shown`, which the gate contract mandates (§5.4).

  The prose allows only `engine.sim`'s public surface, `engine.intents` and `engine.materials` types. The forbidden
  contract in §10 then forbids geometry and cells.
- **Two parts of the rule can't be expressed.** "Geometry internals" and "scene build functions" aren't modules, and
  import-linter can't forbid a function (v1 W8 again).
- **Two writers sit outside the core.**
  - **The save loader.** It is named as a writer that enters the window (§4.1, §6.4). But loaders are layer 7, outside
    the core, so §3's non-vacuity test ("every function assigning into a cell array ... is defined in a core module")
    goes red, or it gets an exemption.
  - **`ActionLimits.load`.** It moves "into `engine.intents`" (§11.1), a core layer that bans `yaml` and `pathlib`.
- **Failure scenario.** `phase1/boundaries` moves `_on_region` into `adapters.sem` and the contract goes red. The
  author exempts `engine.geometry` "for types". The rule then has a hole a debug command can use, which is the v1 S2
  scenario.
- **Fix.**
  - Make the point-to-region decision a stage-2 world check in the applier, which is where a world-state check
    belongs. Alternatively, publish footprints and the name rule on the frame or in `engine.intents`.
  - Allow `engine.checks` explicitly.
  - Make scene build its own module, or route construction through `Simulation.from_scene`.
  - Split the save loader into decoding (layer 7) and construction (core).
  - Leave `ActionLimits.load` in `engine.loaders`.

### S3. `boundaries.md` §7.2; `npcs_and_sem.md` §6.4 :: `to_maxim_entity(world, region, actor=...)` hands `World` to the agent side

- **The contradiction.** §4.2 says "nothing outside the simulation lane holds a reference to `World`". Both documents
  then keep a signature whose first argument is `World` and whose products (the sensors and the modulator) live on
  the agent side.
- **Failure scenario.** The per-actor factory closes over `World`. The first sensor built in it reads
  `world.grid.temperature` live, and the `Observation` protocol can't catch it, because the factory is typed against
  `World`.
- **Fix.** The membrane factory takes a frame source and a submit handle, never `World`, and the per-actor binding is
  written against that signature.

### S4. `boundaries.md` §4.1, §4.2 :: "copies or read-only owners" plus a window that flips the owner's flag means a frame can change under its reader; frame cadence is unstated

- **The frame can mutate.** The window makes the owner writeable during `step`. A frame that holds the owner itself
  (the cheap reading of "read-only owners") is mutated mid-step. The §4.2 thread test catches that only when it wins
  the race.
- **The guard is single-threaded.** `flags.writeable` is per array, not per thread. While the simulation lane is
  inside the window, any thread holding a reference can write. "A write anywhere else raises" (§4.1) is a
  single-thread guarantee. Across lanes the guard is §4.2's "no references", which should be said.
- **Frame cadence is unstated.** `world_model.md` §9 and world_v2 publish region reductions "once per physics step"
  (0.5 s). The tick is 0.1 s (part 2 §9). So "the next published frame" in mode (a) is up to five ticks away, not the
  "one tick" reafference that §7.2 and part 2 §6.1 claim.
- **Fix.**
  - Frames are copies, or double-buffered owners that are never re-flagged. Budget the copy per profile (B5).
  - State the window's thread scope.
  - Say whether a frame is per tick or per physics step, and correct the latency claim to match.

### S5. `boundaries.md` §6.4, §8.1, §11.1; `world_model.md` §10; part 2's [now] tags :: the agent foundations have no PR, and the marked band-aid can't come out when its marker says

- **2c ships things whose dependencies don't exist yet.** `phase1/gates` (2c) ships published frames "stamped with
  its tick", `observed_tick` on every intent, and the "read from a second thread mid-step" test (§4.2, §11.1). The
  integer tick, `Simulation` and the intent record are born in sim-clock (#4), and threads in lanes (#10). So 2c
  either builds placeholders with no caller, or tests that can't be written yet.
- **Nothing in world_model §10 builds the agent foundations.** No PR builds `AgentPort`, `engine.adapters.agents`,
  receipts and settle, the thought request and result types, the response cache, `data/agents/timing.yaml` and its
  loader, or the per-NPC stream. Part 2 tags all of them [now], defined as "built in Overdrive's Phase 1 PRs", without
  saying which PR.
- **The TEMPORARY marker can't be removed at sim-clock.** The marker is `TEMPORARY(phase1/sim-clock)` (§6.4), and the
  behavioural contract test "lands with mode (a) in sim-clock" (§8.1). But mode (a) needs a host that advances the
  world while a Maxim turn is blocked in `execute`. That is a second thread, or a re-entrant `step` called from inside
  an agent call, and the lanes PR (#10) is the first to provide it.
- **Failure scenario.** At sim-clock the marker's phase step finishes. The lint fails, so the marker is renamed
  rather than removed. Or `execute` is made to advance the world itself, which is a second clock door.
- **Fix.**
  - Give the agent foundations a row in world_model §10. They probably belong with or just before lanes.
  - Re-target the marker and the behavioural test to the PR that actually ends the synchronous path.
  - Scope 2c to what has a caller then: the window, read-only owners, constructors, gates. Leave frame threading and
    `observed_tick` to sim-clock and lanes.

### S6. `boundaries.md` §5.3, §6.1, §6.2 :: `memory_write` is a `Simulation` log input that the `Simulation` can't apply and replay never reads

- **The contradiction.** §6.1 lists `memory_write` as a record kind, and §6.2 says the log holds "every kind in §6.1"
  and passes each through "stage-2 validation against the world at apply". But:
  - agent state lives outside `Simulation` (§7.1);
  - the applier is in the core, which can't import `maxim`;
  - replay "never re-runs Maxim".

  A logged memory write is therefore never applied on replay. It is audit, not input.
- **It doesn't exist yet.** It exists only after C1 (generate vs apply). Under mode (a), Maxim writes its own memory
  inside the turn, and no record is produced at all.
- **Failure scenario.** Sim-clock implements the applier from §6.1's table, meets a kind it can't apply without a
  callback into the agents, and special-cases it.
- **Fix.** Take `memory_write` out of the `Simulation` log. If it is kept, keep it as an agent-side audit record, and
  date it [after C1].

### S7. `npcs_and_sem.md` §6.1 step 2, §9 item 2 :: part 2 quietly extends boundaries' log record and its order key

- **What part 2 adds.** Intents are stamped with "the segment's modelled time" in world microseconds, and same-tick
  order becomes `(tick, sub-tick time, actor, seq)`. That "extends `boundaries.md` §6's ordering".
- **What boundaries has.** §6.2's record has no sub-tick field, and its key is `(apply_tick, actor_id, seq)`. This is
  a change to a versioned format with golden fixtures, made in a document that says it "does not reopen" boundaries.
  §12.3 (where part 2 promises to list such changes) doesn't list it.
- **Failure scenario.** Sim-clock builds the record from boundaries §6.2, and its goldens freeze. Lanes then needs the
  sub-tick key. That means a format bump, or a second ordering rule in the applier.
- **Fix.** Add the field and key to boundaries §6.2 now (or as a §12.3 fold row), decided in sim-clock as part 2 §9
  proposes. Write the key once, as DLP S-2 asked.

### S8. `boundaries.md` §5.1, §9.3 vs `sem_breaking_change_plan_DRAFT.md` §2–§3 vs `npcs_and_sem.md` §8, §12.3 :: the SEM items' paths disagree across the docs, and two items exist nowhere upstream

- **Boundaries §9.3 marks five items "batched".** The SEM plan makes four of them additive:
  - propose and settle: additive through `ModulatorReceipt` (only `pending` is batched);
  - the timestamp and `drift_rate` time base: S1 and S2, additive;
  - affordance direction: S5, additive first;
  - acting entity: S6, additive first.
- **The fifth is missing.** "Deep-frozen `ModulatorResult`/`SensorReading`", which boundaries §5.1 calls "a candidate
  for the SEM breaking-change plan", isn't in the plan, its §3 batch or the roadmap.
- **Reserved membrane metadata keys** ("additive now", BF-10) are likewise absent from the SEM plan and Phase 3.
- **Part 2 §12.3 is stale.** It says boundaries §9.3 still asks for "the cerebellum honours neutral" and
  "`modulated_by`". At 4f7a754 boundaries already has the corrected rows. So the commit fixed two rows and left five
  out of step, and part 2's note is now wrong.
- **Failure scenario.** Maxim's plan review reads boundaries (cited by both drafts) and the SEM plan side by side. It
  sees Overdrive asking for a 2.0 in one and saying "no break needed" in the other, and the deep-freeze ask is lost.
- **Fix.**
  - Make boundaries §9.3 cite SEM plan ids and paths verbatim.
  - Add deep-freeze and reserved keys to the plan (as S11 and S12, or under S3 and S9), with their additive or batched
    path.
  - Delete or update part 2 §12.3's first bullet.

### S9. `npcs_and_sem.md` §3.1, §4.7 :: [now] tags claim results that need tier A

- **Prompts.** The prompt test ("no tick, no clock string and no date from the host") and the dial-invisibility test
  ("bit-identical percepts **and prompts**") are tagged [now]. Maxim builds the prompt, and today it carries
  `datetime.now()` (`prompt_builder.py:1104`), so with real Maxim both tests are red until A6.
- **The response cache.** §4.7 [now] claims "a session with real LLM thoughts reproduces at any dial". The cache key
  hashes a request that contains the host date (A6), and Maxim's ids and global `random` (A5) vary per run. So keys
  never repeat, and the agent state that builds the next request diverges.
- **Failure scenario.** The [now] tests are built against the stub, so they pass while testing nothing about Maxim.
  Or they're built against Maxim and are permanently red without a strict marker.
- **Fix.** Tag them [after A], and give each a `xfail(strict=True)` red gate against real Maxim [now], with only the
  stub variant green.

### S10. `npcs_and_sem.md` (whole) vs `world_model.md`'s hand-off list :: part 2 has no fold table, and it doesn't supersede world_v2 §6

- **The unfolded hand-off.** world_model's closing list hands to part 2 or 3: world_v2's DLP-B2, S-1, S-2 and S-5
  (the thinking lane and its latency mode), and world_v2 BF-1 to BF-13. Part 2 cites none of them, and has no fold
  table.
- **What world_v2 §6 still says.** Part 2 §11 supersedes the lanes design, but not world_v2 §6, which states:
  - thought results and worker failures are log inputs (boundaries §6.2 says a thought is never a log input);
  - the `Simulation` itself decides abandonment and cancellation (part 2 makes abandonment a host policy);
  - the live source applies at `max(T + d_min, first tick after arrival)`, so the world never waits (part 2: the
    world dilates).
- **Failure scenario.** The lanes implementer reads world_v2 §6 (world_model calls it a record, but parts of it
  "stand" by default) and builds world_v2's log.
- **Fix.** Add a fold table to part 2, covering the findings world_model handed it, and add world_v2 §6 rows to §11.

### S11. `boundaries.md` §2.1 :: the cut says the game holds "rules" but defines no way for game code to reach the tick

- **The gap.** The game package holds "this game's content and rules". The engine never imports the game. So a game
  rule that acts in the world (a game-specific affordance, intent kind or law) can enter only by registration or
  injection at runtime, and the design defines neither.
- **Failure scenario.** `phase1/lab` (#12) needs a lab-specific rule. Either:
  - it lands in the engine, and the cut erodes on its first use; or
  - it is passed in as a callable that runs inside `Simulation.step`. The callable sits outside the import-linter
    banned-list contract, which covers the engine's layers 0–6 only. Only the AST scan sees it, if the game package is
    on its walk list.
- **Fix.** Define the extension seam now. Either:
  - game rules are data only (vocabulary, calibrations, rosters), and new mechanisms are engine code; or
  - there is a registry that the core calls, and the banned-list contract extends to the modules that register.

  The first is simpler, and it matches "physiology is mechanism" (BF-15).

### S12. `boundaries.md` §8.2 :: putting calibrations in game content takes the physics values the game ships out of the engine's resolution gate

- **The cut.** `fracture_energy_*`, `degrade_*` and combustion tuning go to rights-reserved game content. Engine tests
  use Apache fixture tables. These values decide outcome classes: breach, ignition and burn-out.
- **The consequence.** The cross-tier and closed-form tests (the resolution rule) then prove invariance for fixture
  values only. Nothing in the engine gate runs the shipped values. Yet the fuel PRs' acceptance scenario (world_model
  §10, the vented crate burning away against the 0.05 m reference) is defined on the crate's real material.
- **Failure scenario.** A game retune puts wood's breach energy inside the band where the laptop and max profiles
  disagree. The engine gate stays green, and Phase 1's exit test ("the same apart from detail at the laptop and rig
  profiles") fails in the lab, or never runs.
- **Fix.** The game's gate runs `engine.verify`'s cross-tier suite over its content tables, as a required check that
  is born with the content file in material table v1 (#5). Alternatively, reclassify values that decide outcome
  classes as engine physics with game overrides refused (the closed key sets already support that).

### S13. `boundaries.md` §4.4, §7.2; `npcs_and_sem.md` §6.1, §7.1 :: mode (a) helps only instant effects, and its credit path reads the omniscient instruments that B-13 removes

- **Slow effects aren't covered.** Mode (a) waits one frame, so strike, which lands at once, is credited correctly.
  Ignite adds a source, and its effect (heat, then burn) arrives over many physics steps. Maxim's cerebellum reads
  sensors once, after the wait, and so learns "ignite barely changes temperature". That is BF-1's failure, kept for
  every slow effect. Neither doc records it as a divergence.
- **The credit path depends on instruments.** Maxim's tool bridge trains on "every sensor of the acted-on entity",
  and today those are region instruments, readable from anywhere. When B-13's perceiver half lands (Phase 4), either
  the credit path keeps reading instruments (B-13 broken where it matters most), or it reads nothing.
- **Fix.**
  - Record slow-effect credit as an OPEN divergence until C1, with a red gate.
  - Use per-actor binding (already [now]) to give each NPC's entity perceiver-relative sensors, so B-13 and the
    credit path agree.

### S14. `docs/roadmap.md` Phase 3 tiers :: tier C puts independent additive SEM items behind the hybrid line, and one clock item changes tier between documents

- **Independent items wait on the hybrid line.** Tier C is "the 1.5 hybrid line, and the SEM refinement plan". C2
  (stale kind), C4 (actor key) and C7 (versioning) are small, additive and independent of the hybrid runtime. The SEM
  plan's own §5 orders S1, S2 and S9 right after tier A, then S3, S4 and S6.
- **The stale divergence outlives Phase 3.** Phase 3's exit needs only tier A and B1–B7. So the stale-books-NEGATIVE
  divergence (C2) is still OPEN when Phase 4's first NPCs live and learn.
- **`FailureMode.last_fired` changes tier.** The SEM plan's S10 says it "joins tier A". The roadmap puts it in C8. The
  tier A draft's live-path table doesn't list `maxim/embodiment/sem.py:1560` (`self.last_fired = time.time()`, cited
  in v1 D-B1). Yet tier A's E1 claims a bit-identical agent.
- **Fix.**
  - Split tier C into "SEM additive, after A" (C1–C9) and "hybrid line" (C10, C11).
  - Decide whether C2 gates Phase 4.
  - Put `last_fired` in tier A's §3.2 table.

### S15. Fold table, Arch B2 / TB-B1 / X-2 :: "folded" overstates the gate-registry check

- **What §5.2 rests on.** "The lint checks that every public callable reachable from an outside entry point ... is
  registered." That depends on a static reachability analysis over Python call graphs, which §5.2 never specifies.
  The entry-point list is itself manual.
- **What the proof covers.** The planted proof covers a `json.loads` in a non-gate module, and a public entry with no
  row. v1 B2's exact scenario is different: a new `handle(raw: bytes)` added inside the protocol module, which is a
  gate module and may decode. Neither half of the proof catches it.
- **Fix.** Specify the registry check mechanically (for example, every public callable defined in a gate module must
  have a row), and mark the fold "partial" until it is.

## NIT

- **N1. `boundaries.md` §3, §7.1 :: "moves inline later" changes the core's definition and replay.** If the port is
  called inside the tick, "the core is the code that runs on the simulation lane" becomes false, because
  `engine.adapters.agents` is unscanned. Replay must then either call Maxim or skip the port. Say which, and that the
  logged intents stay the input.
- **N2. `boundaries.md` §10 "Lands" :: several rows say "boundaries" for work §11.1 puts in `phase1/gates`.** These
  are the window, frames, the registry and the constructors. Use the PR names.
- **N3. `boundaries.md` §7.1, §8.1, §9.3 :: old proposal ids.** The text still uses #1361, items 11, 12, 15 and 16, and
  P3, P4 and P5. §8.1 says it will do so "until that renumbering lands", but the roadmap renumbered on this same
  branch. Switch to A, B and C ids.
- **N4. `npcs_and_sem.md` §8 :: S2 maps to "A2, C8".** C8 is per-part `world_set_axis` and `last_fired`. S2 belongs to
  A2 (tier A PR 3, `spec.py:837`).
- **N5. `boundaries.md` §6.1, §6.2 :: one `seq` per actor, two producers.** `execute` (the turn) and `AgentPort.step`
  (the substrate) both emit an actor's intents. Say who assigns `seq` and how ties at equal sub-tick times break, or
  reruns depend on which thread incremented first.
- **N6. `npcs_and_sem.md` §4.3, §4.4 :: `cancelled` and `thought_failed` are "logged" but not classified** as input or
  derived in boundaries §6.1 and §6.2. world_v2 DD2 had classified them as derived.
- **N7. `boundaries.md` §11.2 :: the distribution `maxim-overdrive` will ship the engine** while the game package is
  `maxim_overdrive`. `pip install maxim-overdrive` then doesn't install `maxim_overdrive`. Decide with Q1.
- **N8. `world_model.md` §10 #2 :: "Parts 1, 2 and 3 accepted" gates 2b on a part 3 that isn't written.** 2b doesn't
  depend on it. Say whether 2b waits for it.
- **N9. `boundaries.md` §7.1, §7.2 :: in mode (a), `settle(receipts)` delivers receipts that `execute` already
  turned into credit.** State that settle carries context only in mode (a), or the adapter credits twice.

## Fold table spot-check (v2's claims against its text)

| Finding | Claim | Verdict |
|---|---|---|
| Arch B1 execute's contract | §7.2, O2 | Folded, by a decision rather than a deferral. Composition broken (B2, B3) |
| Arch B2 gate lint | §5.2 | **Partial** (S15) |
| Arch S2 skip layers | §2.2, §10 | Folded in intent. The rule as written forbids what the gate half needs (S2) |
| Arch S3 intents home | §2.2 | Folded. Its layer-5 sibling independence is wrong (S1) |
| Arch S5 geometry layer | §2.2 | Folded |
| Arch S9 data defaults | §3, §8.2 | Folded. `ActionLimits.load`'s destination is not stated (S2) |
| Arch S11 doors and marker | §6.4 | Folded. The marker's phase is wrong (S5) |
| Arch S12 order | §11.1, world_model §10 | Folded |
| BF-2 substrate home | §3, §7.1 | Folded in the core. The lane it runs in is undefined (B1) |
| BF-5 push path | §4.3 | Folded |
| BF-13 thought results gate | §5.3 | Folded. `memory_write` is misplaced in the `Simulation` log (S6) |
| D-B2 disk input | §3, §6.3 | Folded |
| D-B3 log record | §6.2 | Folded. Part 2 extends it unlisted (S7) |
| D-B4 / X-3 views | §4.1 | Folded. Frame aliasing and thread scope are open (S4) |
| D-S5 observation | §4.2 | Folded |
| D-S8 canonical order | §6.2 | Folded. The `seq` source is open (N5) |
| TB-B3 authority | §6.1 | Folded. Request-id ownership conflicts with lanes §4.2 (B1) |
| TB-S6 imagination | §5.3, §6.4 | Folded |
| W1 rebases | §2.1, §11.3 | Folded (git's default `merge.directoryRenames=conflict` makes the claim plausible) |

Of 19 rows checked: 18 are genuinely folded, often with a new defect introduced by the fold. One is partial. The
count line ("18 of 18 BLOCKERs and 52 of 52 SHOULD-FIXes folded") is accurate as a count of rows. It is not a
statement that the folds compose, and the agent-side folds don't yet.

## Verdict per cut

| Cut | Right? | Note |
|---|---|---|
| Packages (engine / game / experiments) | Yes | the game extension seam is missing (S11); calibrations leave the gate (S12) |
| Layers | Right shape | layers 5 and 7 aren't independent (S1); skip-layer rule (S2) |
| Sealed core | Yes | |
| Write window | Yes, single-thread | frames must copy (S4) |
| Published frames | Yes | `to_maxim_entity(world, …)` (S3); cadence (S4) |
| `AgentPort` | Wrong seam | B3; lane undefined (B1) |
| Propose/settle and mode (a) | Right intent | deadlock (B2); slow effects (S13) |
| Log record | Yes | `memory_write` (S6); sub-tick (S7) |
| SEM items across the docs | Inconsistent | S8, S14 |
