# Checklists the foundations plan points at

For whoever runs the step. Each item names the review finding it comes from (`reviews/fold.md` has the key). The plan
(`foundations_plan.md`) keeps the order and the decisions; this file keeps the items, so the plan stays inside its
word budget. An item is done when its test exists and passes, or its text has landed. This file is exempt from
O22's budget (O42), and each step's section is deleted when that step's PR merges.

## Step 1, the merge: this line's items

- Map act-validation's Phase 3 items 10 (malformed arguments booked as tool failures, against TF2) and 11 (affordance
  direction, against `scene_actor_affordances.md`) onto OD ids, or add new ids. Never resolve them mechanically
  (SEQ-S11).
- Keep design-v2's newer versions of the three documents it shares with PR #3 (SEQ-S11).
- Drop the marker-lint exemption for `docs/plans/reviews/` together with the rest of `MARKER_EXEMPT_DIRS`, once the
  Markdown-aware lint from PR #3 lands. Its seven hits are backticked, so that lint passes them (fidelity pass,
  2026-11-17).
- O32 and O33 on `phase1/standards`: a constraints lockfile per Python version for the gate and CI, pymaxim
  included; a scheduled unpinned CI job running the gate against the newest releases; `requires-python >= 3.12`
  and CI on 3.12 and 3.14; CLAUDE.md's pymaxim rule reworded to O32.
- Merge the four specifications of the intent-log header (realtime §7, boundaries §6.3, world_model §8, tile §3.5)
  into boundaries §6.3, before step 5a writes the first log fixture (`reviews/flexibility/contracts.md`).
- Write the lessons design-v2 owes to `docs/lessons_maxim_in_games.md`: a duplicate ask to Maxim (OD-A19); `-I`
  ignores `PYTHONHASHSEED`; Python falls back to the real home when `HOME` is unset; a pipe that unpickles; O15a
  (ST-S11).
- Flip the design documents' status lines from DRAFT to accepted, citing the owner's merge (CS-S6).
- Amend `realtime_lanes_coop.md` §7's v0 client-message table to `tile_and_client.md` §3.3: `act` and `act_result`
  retired, one message per kind, no client-sent region (DC-B2). Amend boundaries §4.2's `observed_tick` wording for
  the Frame split (DC-S1). Correct `architecture.md:20` (turn-based; real time with pause).
- The merge commit's `prepush: PASS` comes from CI's `prepush` workflow on `main` (it runs on every push and says
  that its isolation check is skipped). Locally: `git worktree add --detach .worktrees/merge-check <sha>` and run
  the gate there; a detached HEAD is neither `main` nor the main checkout (SEQ-S9).

## Terms the plan uses (CS-S4)

- **Tier A / B / C:** Maxim-side work in Phase 3, by what it enables: A, an agent a host can drive (Phase 4 waits on
  it); B, Maxim's 1.4 line; C, SEM additions after A (`docs/roadmap.md` Phase 3).
- **The 1.4.0 cut:** Maxim's next minor release; the stepped `think` comes after it, in the 1.5 hybrid src phase (O15a).
- **The scripted double:** a fake agent with Maxim's interface, scripted per test, run in a real worker process, so
  the agent line is tested before real Maxim can be.
- **B-numbers (B19, B20):** rows in `docs/standards_backlog.md`, rules held by review until a check exists.
- **OD- ids:** Overdrive's proposals to Maxim (`docs/roadmap.md` Phase 3). **O, OA, D:** owner decisions in the
  design docs' §0.
- **Strict red gate:** `pytest.mark.xfail(strict=True)`; it goes red the day the fix lands, so someone removes it.

## Machine assumptions for any session (CS-S8)

Python 3.10 or later; GPG signing configured, with someone present to answer its passphrase prompt; `gh`
authenticated for the private repository; Godot 4.7.2 at `/Applications/Godot.app` from step 2; a per-worktree
`.venv` (step 0a).

## Step 3b, gates

- Scene v1: F13 plus a required `spawns`; scene v0 is refused by version, not migrated (it would migrate to a
  scene `join` refuses); golden v0 and v1 fixtures (WT-S8).
- One schema and one reader per data format; `MaterialTable`'s lookup arrays and every rejection test generated
  from it.
- One small migration mechanism (`read_version` plus a registry keyed by format and version), used only for
  formats other people hold: saves, logs, bug reports, later mods. Repo-only files get a version bump and a
  refusal test instead.
- Digests stored versioned, as `sha256/c14n-1:<hex>`.
- Content stores time in world units (m/s, seconds), never ticks; ticks are derived at load.
- Loader types for body archetypes and items; the refusal-code enum (WT-S1).
- Identity keys contain no `:` (Maxim's owner, 2026-11-19: `make_agent_rng` joins `f"{base_seed}:{agent_id}"`, so a
  `:` would make streams ambiguous). Every loader that reads one (`body_key`, NPC keys, stream names; later save v0)
  refuses it with a typed code, and each has a rejection test (`npcs_and_sem.md` §3.4).
- Fuel-bed fields (φ, σ) on primitives, validated where made.

## Step 4, verify

- The harness drives laws on a state with explicit `dx`, `dt` and a step count, never `World`; it ships
  `converges(...)` and `band_gate(...)`, and `tests/test_cross_tier.py` is ported onto them.

## Step 5a, the simulation core (O34)

- The substep floor (from 3a): `World.advance` still takes `max(heat.min_substeps(dx), stability)` substeps, where
  `min_substeps` is the retired rigs' 4/16/64 as 0.16 m² / dx². On every 6 s turn the floor, not stability, sets the
  count; stability alone changes every determinism digest (measured in 3a), so dropping the floor is a behaviour
  change with new goldens, owed with the fixed physics step.
- A short composition note first: cell state, body state, ledger, clock, intent log; no god object.
- The step as a fixed, ordered tuple of laws, each with `stable_dt(state)` and `step(state, dt, ledger)`;
  topology changes read from `topology_version`. No discovery.
- **The field registry:** one list in code that the grid's storage, the snapshot, the determinism digest, the
  memory budget and the save all read. Step 6's fields join it, and step 7's catalogue is generated from it.
- Each law split into `prepare` and an array-only kernel, with a bit-identity parity test (the numba seam; no
  numba until a profile asks).
- Intent kinds ranked 0/10/20/30, leaving room; a `retired:` list of verbs, and refusal codes append-only, tested.
- Replay goldens keyed by an environment digest; the log header's field list as merged in step 1.

## Step 5b, bodies and movement (`tile_and_client.md` §2, §3, §4.1)

- The actor table, body motion, the walk grid and A*, the "move bodies" stage (AR-B1).
- Body heat exchange as a reduction over a volume in metres, with closed-form and cross-grid tests (BF-B2).
- `move` and `move_to` as ordinary intents (AR-B2).
- The Frame's cells part and per-tick body table, and the dial-invariance test (BF-B1).
- The alley fixture and its B5 meters (EX-S1).
- The pilots table and `path_version`; the Frame publication rule (DC-S2).
- Body radiation (skin view factors, the flame as a point source) with its closed forms: a clamped two-capacity box
  and a fixed point source (DPH-S4).
- `join` records carry `body_key`, the archetype name and the held item's name.
- The efference-copy fields (`tile_and_client.md` §3.1): bodies-part events and pilots rows carry `cause = (actor_id,
  seq)`; the intent record carries an optional, opaque `invocation`. A test: a `move_to`'s `arrived` and a
  `kindle`'s pilot row name their intent.
- `invocation` is reserved and unfilled until Maxim's G17 stage (autonomic plan, post-fence resume) builds
  `PhysicalEventId` (Maxim's review of v5, SHOULD-FIX 1). A test: null is accepted, and a stand-in is refused with a
  typed code: a uuid string, an executor-style `invocation_id` and any other non-null value. The host copies the
  field and never mints or computes one. When the type exists, the refusal narrows to any non-null value that isn't
  a pid, with its own test.
- Action vocabulary v1 with `actions.yaml` v1, refused at v0 by version, not migrated (DC-S5), and an interim sphere-overlap
  `kindle` deposit: a marked band-aid, its file listed under Phase 1 in the roadmap, removed by step 6's skin.

## Step 6, fire (D30, T13; `tile_and_client.md` §5)

- A short design note first, reviewed under the Physics lens, answering the final review (`reviews/tile_v1/
  final_physics.md`): FPH-B1 radiative transfer between slats inside the bed, plus the draught's air-supply loss;
  FPH-B2 the char-surface product (CO or CO₂) from a cited source, never chosen to make glow pass; FPH-B3 ignition
  and flame spread from a reconstructed sub-cell surface, not a cell mean, with the convergence test as its proof.
  The honest expectation: glow may fail (570–840 °C against 625 °C); then it goes to the owner, and nothing is tuned.

- 6a open-air loss, 6b a 1 mm surface skin, 6c the porous fuel bed (m'' = q''_net / L_g), 6d char oxidation
  (D30).
- `tile_and_client.md` §5.1's constants, each with a provenance row, and the no-fitting rule (DPH-B1); the
  pre-registered failure path to the owner.
- The ledger with `sources`, Δ(skins), `plume_convective`, `flame_radiative` and the deposit test (DPH-S2); the
  flame-radiation Known gap with numbers (DPH-S1).
- `kindle` (vocabulary v1) and the torch band measured at three grids (PH-S4, PH-S5).
- The 0.05 m reference run; V_floor at a fixed 900 °C contact, non-circular (DPH-S3); the 1,300 °C and `crate_far`
  deletion proofs (DPH-B3); the red gate's flip.

## Step 7, `phase1/protocol`

- The frame grammar's extension rule restored (world_v2 §8): a `required` flag per channel, `compression: none`,
  `axis_order`; fixtures for an unknown optional channel (ignored) and an unknown required channel (refused).
- `welcome` and the version `error` carry the engine `build`.
- A refusal for exhausted u16 region ids.
- JSON reads floats (`client_rendering.md` §4.1): decoder fixtures with an integer at 2^53 and at 2^53 + 1 (refused);
  stage 1 refuses `5500.0` and `true` where an integer is expected (Python reads a float, and `bool` is an `int`).
- B25's engine/game check, with the second engine file.

- The strict red gate that refuses guest joins while real-Maxim NPCs are live, as the roadmap's Phase 4 assigns
  this PR (TB-B2).
- `intent_result`, `seq`, `observed_tick` and events' `cause`; the catalogue with non-default-scale fixtures and its hash check on
  every frame (WT-B3, WT-S13).
- `region` as u16 `region_id`, the `regions` message and `regions_version` (DC-B1); `surface_glow` and `burning`;
  `tick` as JSON with integer columns (DC-S9); events accumulated with a resync (DC-S4); `tile_and_client.md`
  §3.3's message table; `welcome`'s maps; a `snapshot` on join (WT-S6).
- Decode and stage-1 rejection fixtures; `HostOnly` tested directly with a guest-role view (WT-S9).
- Buffer caps and the 1009-close test (WT-S12); the `Origin` capture test.
- The guest-text gate `engine.text.player_text`. Its Cf rule must let ZWNJ and ZWJ through for Persian, Indic
  spelling and emoji sequences, or say why not, and NFC runs before the length cap. This is an owner decision
  (TB-N5).

## Step 8, the tile (`tile_and_client.md` §6; `client_rendering.md` §4–§6)

- The game package and its `content/` (AR-S6).
- The exit script, run stepped and unpaced; the controls, each proven by deletion (PH-S3); the stage-2 refusal
  scripts.
- The shader, the cut-away test at ≥ 95%, five scenario goldens per tier, staleness digests, `update_goldens.sh`
  (EX-S13).
- CR-B3's open half: a shaded golden that differs at 128 and 256 bits and agrees across Intel and AMD runners (the
  job logs the CPU); a per-object ΔE over the ID mask (S2C-S3); `golden.gd`'s missing-`--out` refusal tested.
- The human playtest.

## Step 9, save v0

- The actor and pilots tables and `body_key` (BF-N3).
- **Names, not positions:** every index column (`archetype`, `held_item`, `material`) carries a name list in the
  header, and loading remaps by name.
- **The load rule:** a save is state, and loading never replays the log; it stores a region table, not the scene
  file; a content change loads with a `content_changed` flag instead of refusing; every grid carries its cell size.
  This supersedes world_model §8 F5's refuse-on-mismatch for saves (F5 and F14 contradict on embedded scenes).
- No zero-valued `energy` or `dose` columns: they arrive in Phase 4 with defaults.
- No agent state: the `EventSequencer`'s high-water seq in each agent home is save v1, Phase 4 (O43).

## The agent line's PR (after steps 5 and 7)

It needs step 7: the host's stage 1 for worker speech calls `engine.text.player_text` (TB-S9).

**Precedence.** For the agent half, a finding in `docs/design/reviews/npcs_v3_1/` overrides the frozen §6.6 text it
contradicts (TB-S5). Before the codec's fixtures freeze, each of these is a test or a fixed codec kind:
- ATR-S1 (worker stdio not inherited);
- ATR-S3 (a refused frame drops the frame, not the NPC);
- ATR-S6 (the `purge(actor, session)` kind, and a host-computed lower bound on provenance; TB-B3);
- ATR-S8 (snapshot save; cancel pending intents);
- ATR-S9 (a frame per perceiver, not the whole world);
- ATR-S10 (budgets for body, home and rlimits);
- ATR-N1;
- ATR-N2 (a `hello` kind).

**Real Maxim stays off the test process (TB-S4).**
- Every real-Maxim red gate builds its agent only inside a spawned worker, with the allowlist and `MAXIM_OFFLINE`.
- Tests 1–3 are green before the first such gate is written.
- A test asserts that `maxim.runtime` and `maxim.agents` are absent from pytest's `sys.modules` after the agent
  suite.

**Platform and latch (MS-S7, SEQ-S7).**
- Off POSIX, the host refuses to spawn a worker with a typed error, and a test covers it.
- A test pins that the pre-opened `socketpair` survives `engage()`. Tell Maxim that this residual is load-bearing.
- Tests that need `maxim._offline` are a strict red gate naming the pymaxim release that ships it. Raise
  `pymaxim>=` when it ships. A pymaxim release that turns `tests/test_sem_compat.py` red gets its own mirror-update
  PR from this line, never a fix inside a feature branch.
- Windows NPCs before Phase 8 need a Phase 3 item; the owner decides whether they are wanted. Until then, a Known
  gap: real NPCs on macOS and Linux only.

**The lane's model (MS-S8, O18).**
- Build the router with `models/download.py::consented_router`, with no cloud or peer tail when guests are present,
  the model provisioned before play, and stdin not a terminal.
- A gate test: a missing local model with guests present refuses (typed, and shown in the client). It never falls
  through to a remote tail.

**Coverage of the worker (ST-S2).** Coverage follows the child: `patch = ["subprocess"]`, or
`COVERAGE_PROCESS_START` with `parallel` and `combine`. Admit coverage's variables through test 2's allowlist, by
name, and test that the worker's main loop is measured.

**Determinism (ST-S3).**
- The hash probe calls the builtin `hash()`, so give its module a package-qualified exemption in
  `tests/test_determinism.py`, with a reason.
- Rewrite CLAUDE.md's rule of one `Generator` owned by `World`: per-NPC streams break it under either derivation.
  If MS-S6 keeps ours, admit Philox in `NUMPY_RANDOM_ALLOWED` in the same commit, for Overdrive's streams only.

**Formats and data (ST-S5).**
- The channel codec: a version that readers refuse when unknown, a round trip, committed golden fixtures, and a
  Hypothesis round-trip property.
- `data/agents/`: a `version`, closed schemas, and tunables in YAML. The continuation blob is versioned.

**Provenance of *to verify* values (TB-S6, option (b)).** Each value in `data/agents/` carries a tag: `verified`,
`to_verify` or `engineering`. A loader test fails on `to_verify` outside a fixture. The calibration ledger the source would have this block on
is out of the plan (S-S8), so this test is the whole mechanism.

**Replies and reloads.** The logged reply record is a versioned host type the adapter maps Maxim's values into
(Maxim's B1 shape isn't settled; O26 makes replies part of the log). A save whose in-flight thought has an
unknown continuation version loads it as a logged `thought_failed(reloaded)`, not a refusal.

**The embedded efference copy (`npcs_and_sem.md` §6.6; Maxim `thalamic_relay.md` §5.2, GL3.B2).** The codec
carries each intent's invocation pid in `step_output`, and `caused_by` on every receipt and frame event it caused.
Test with the double: an NPC's own `kindle` gives a frame event carrying its pid, a planted second actor's event at
the same locus carries none, and an in-flight thought stays fresh across the first and goes stale on the second.
- **The pid's owners (Maxim's Q1 answer).** The double mints its pid inside the worker, at dispatch, from its own
  sequencer, standing in for B2 and Maxim's `EventSequencer`; the host copies it. A test plants a host-side mint
  (the host fills a missing pid) and goes red. Until G17 the real-Maxim path sends null (step 5b's refusal holds).
- **The settle invariant (OD-EA16, Maxim's SHOULD-FIX 2).** A test that every minted pid resolves exactly once: the
  double mints pids for intents the host then applies, refuses at stage 1 or 2, defers past the budget and drops
  (a superseded move, `coalesced`); each pid comes back in exactly one terminal receipt, the last three as a
  typed refusal receipt carrying it; no receipt names an unminted pid; refusal receipts book no physical event.
  Proven by deletion: a planted drop path that sends no receipt turns it red.
- **Crash recovery (O44).** On restore the sequencer's high-water is max(the saved high-water, the highest pid the
  host logged for that agent); a dead worker's in-flight pids each get a typed `agent_failed` refusal receipt. A
  test: save, let the double mint several pids past the save (some settled, some in flight), kill the worker,
  restore from the older save, keep stepping; assert no pid repeats in the log and every pid settles exactly once,
  the in-flight ones as `agent_failed`. Proven by deletion: drop the floor and a duplicate pid turns it red; drop
  the receipts and an unsettled pid does.
- **Replay ids (O43).** `session_id` is derived from the log header (the root id plus the NPC key): a test that two
  runs of one log give equal ids, and that no wall-clock or uuid source feeds it (the determinism scan). The
  sequencer's high-water seq round-trips through the agent home: save mid-run, load, and the next pid's seq
  continues. Maxim's determinism claim covers single-threaded loop paths only, so a worker
  steps one agent on one thread, never a pool: a test that a worker refuses to build a second agent.

**OD-A20's divergence: two strict red gates (`npcs_and_sem.md` §12.2).** Neither exists yet: this PR lands them,
and until it does the divergences are recorded from Maxim's code and our arithmetic, not from a run, and every
document says the gates *will* carry the evidence (Maxim's review of v5, NIT). Each drives a real `NucleusAccumbens` in a
spawned worker: `update_eligibility` with an explicit anchor `TemporalSignature.from_timestamp(time.time() − Δ)`
(an argument, not a faked clock), `decay_eligibility` until that trace is gone (12 passes at activation 0.0336, 44
at 1), any live-trace node set after, then `distribute_reward(1.0)`. Each reason names OD-A20 (declined 2026-11-19).
- **Gate 1, timezone (c).** One anchor-only node, activation 0.0336, Δ = 20 s, run in two workers whose `TZ` (a test
  input in the allowlist) are fixed offsets the host computes from its current instant: one puts a local midnight
  5 s before it (inside the worker's 20 s window for any spawn delay under 15 s), the other puts local noon there.
  Expect equal credit. It cannot pass today: without a date step similarity is about 0.9999 and 0.3 × 0.9999 × 0.0336 = 0.01008 > 0.01, so the node takes the full reward; with one (monthly 1/31,
  annual 1/365.25) it is about 0.982 and 0.3 × 0.982 × 0.0336 = 0.00990 < 0.01, so it books nothing. A DST change is
  the same mechanism (a 1 h circadian step) and needs no separate gate. `TZ` here is a test input; production code
  must never pin `TZ` to hide this.
- **Gate 2, host pacing (a) and (b), `TZ` fixed with local noon at the instant, so no date step.** Δ = 1 s against
  Δ = 290 s (inside the 300 s wall prune, `nac.py:3715`), standing for a live run and a differently paced replay
  (similarity about 0.999994 and 0.998082). Two assertions: a lone anchor-only node at activation 0.03336 gets equal
  credit (today 0.01001 against 0.00999: credited at 1 s, dropped at 290 s); and with a live-trace node beside it (activation 1
  each), the shares are equal (today 0.23077 against 0.23043). The shares assertion stays red if Maxim drops the
  0.01 threshold, which would turn the lone-node one green; and a UTC fix for (c) alone flips gate 1 and leaves
  gate 2 red, so each gate flips for one fix.
- v3.2's "anchor survives a 12 h pause" assertion is dropped from these gates: it tests #1361 S3b's experience-clock
  ageing, a decided fix with its own gates, and would make an OD-A20 gate flip on the wrong fix.
- Each gate is proven to measure the leak, not its setup: a control run with the similarity planted at 1.0 in the
  worker passes every assertion, so the red comes from the calendar alone.

**Wall-clock forgetting, a strict red gate (`npcs_and_sem.md` §12.2; stays with Maxim's #1361 Q5).** Not yet
written, like the two above. Two identical
stores in a spawned worker (default access-based strategy, no SCN wrapper), each with one memory accessed once,
unlinked, not long-term, with low salience and novelty and no user input, so no promotion or keep rule applies; the
second is loaded from a save with every wall stamp shifted back 4 days, which equals sleeping the same store 4 host days later (the score reads only `now −
accessed_at`). One `Hippocampus.sleep` each; expect identical retention. It cannot pass today: the score is 0.5 ×
(1 − 4/7) + 0.04 = 0.254 < 0.3, so the second removes the memory, against 0.54 kept. Its reason names #1361 Q5. No
workaround. Control: with the stamps unshifted both keep it.

**Reopening the frozen agent half (S-S2).** Edits are errata only until one of these fires:
- Maxim's stepped-`think` API lands (cand. B1);
- the LLM spike measures latency;
- Maxim answers a second candidates round (the first, #1688, is answered by errata);
- Maxim's review of `embeddable_agent_DRAFT.md` (O36; fired 2026-11-19, folded in npcs v3.2; its delta review in v3.3,
  its review of v5 in v3.4).
