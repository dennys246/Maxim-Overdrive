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

- From boundaries §10 and §11.1's "lands: boundaries" rows that step 3a (structure only, O23) did not build. All
  done in 3b part (a), with §11.1's 2c items (the window, frames, validating constructors, the registry, budgets and
  bounded echo):
  - done: the StructureModulator split: its gate half stays in `simcore.adapters.sem`, its write half (`apply`,
    `_strike`, `_ignite`, douse) moves into the core as the applier, with the reach and centroid checks as stage-2
    checks; `parse_action`, the typed actions and the refusal type move below the membrane (§2.2 `intents`)
    (`simcore/core/applier.py`, `simcore/core/intents.py`);
  - done: then the skip-layer forbidden contract (adapters, protocol ↛ grid, laws, geometry, scene build)
    (`pyproject.toml` `skip-layer`, proven by a planted import in `tests/test_tooling_config.py`);
  - done: §3's writer non-vacuity test: every function assigning into a cell array, `regions` or `sources` is in the
    core (`tests/test_ownership.py`);
  - done: B-4's input-primitive allowlist and banned unsafe calls (`tests/test_input_allowlist.py`,
    `scripts/lint_inputs.py`); B-10's `Observation` protocol and frame tests (`simcore/core/frames.py`,
    `tests/test_frames.py`); B-13's import half (`membrane-reads-frames`; the field registry joins its allowed list in
    step 5a).
- Part (b), on `phase1/formats`:
  - done, no shipped caller until step 5b (spawns) and step 8 (the shipped scene, with a scene file loader in
    `loaders.py`): scene v1, F13 plus a required `spawns`; scene v0 is refused by version, not migrated (scenes are
    repo-only); golden v0 and v1 fixtures (WT-S8); zones, vents and gaps refused by path; every extent a whole number of
    0.2 m cells, judged in whole micrometres, so a scene builds at every verification grid or none (world_model WT-5,
    WT-11); spawn names unique under Maxim's name rule, never a region's name nor one of Maxim's target aliases (`self`,
    `aut`, `player`) (`simcore/core/scene.py`, `grid.py`; `tests/fixtures/formats/v0/scene.yaml`, `v1/scene.yaml`,
    `tests/fixtures/scenes/alley_box.yaml`; `tests/test_scene_v1.py`).
  - done: one schema and one reader per data format; `MaterialTable`'s lookup arrays and every rejection test
    generated from it (`simcore/core/schema.py`; `tests/test_formats.py` finds every `Format`, fail closed, walks
    every tagged kind, and pins each schema in `tests/fixtures/formats/schemas.txt`). Not built: units and provenance
    on `Field` (flexibility review row 7), which land with 6.0a's material table v1 (tile §5.1's provenance rows);
    stage-1 intent parsing (`intents.py`) stays its own idiom until step 7 moves the wire format onto the schema.
  - done: one small migration mechanism (`read_version` plus `Format.migrations`, keyed by format and version),
    refused for a repo-only format at declaration; no shipped format is held by others yet, so none migrates.
  - done, no shipped caller until step 5a's log header: digests stored versioned, as `sha256/c14n-1:<hex>`
    (`simcore/core/digest.py`).
  - done: content stores time in world units, never ticks: a schema field named for ticks is refused where it is
    declared. Ticks derived at load arrive with the tick (step 5a).
  - done: the refusal-code enum (WT-S1, `simcore/core/refusals.py`), append-only and pinned; every gate's refusal
    carries a code, and the SEM membrane answers an agent with the code alone.
  - done: identity keys contain no `:` (Maxim's owner, 2026-11-19: `make_agent_rng` joins `f"{base_seed}:{agent_id}"`,
    so a `:` would make streams ambiguous), refused as `bad_identity_key` (`checks.identity_key`). Today's one loader
    of them, the scene's spawns (name, archetype, held item), has a rejection test per key; NPC keys and stream
    names get theirs with their loaders (`phase1/agents`), save v0's `body_key` at step 9 (`npcs_and_sem.md` §3.4).
  - done: B29 (`loaders.DataPath`; `scripts/lint_inputs.py`'s routes through a value; the four corpus rows).
  - not built: loader types for body archetypes (the body contract is being redesigned, `sem_stimuli.md` v4 on
    `phase1/sem-stimulus`; owner, 2026-11-21) and for items, which travel with them (owner, 2026-11-21: skipped for
    now).
  - superseded: fuel-bed fields (φ, σ) on primitives. `fire_solid.md` (accepted 2026-11-20) makes a fuel an object,
    never a cell field, and dropped `bed:` from tile §1.3.

## Step 4, verify

- The harness drives laws on a state with explicit `dx`, `dt` and a step count, never `World`; it ships
  `converges(...)` and `band_gate(...)`, and `tests/test_cross_tier.py` is ported onto them.

## Step 5a, the simulation core (O34)

- Step 4's harness, the three items it left here (`docs/design/verify_harness.md` §7):
  - the scenario agreement studies (`tests/test_cross_tier.py`, the cross-grid tests in `tests/test_act_validation.py`)
    move from `World` to `Simulation` at its fixed physics step, so they refine space alone; until then they refine
    space and time together;
  - the reversed-order half of the splitting test, `same_class_under_refinement` over the law list in both orders
    (`research/physics_spike/splitting.md` §6.4);
  - the exact work counters (`world_v2.md` row 2) from `Simulation`, with B5's budgets as their reader.

- Retire `imagination.place`'s write window (its `TEMPORARY(phase1/sim-clock)` marker): owner confirmed 2026-11-20.
- From step 3b part (b)'s review: the scene format becomes held by others once the log header records a scene (bug
  reports carry it), so `SCENE` is declared `held_by_others` then and an old version migrates (Architecture A3); the
  refusal codes produced today get their stage, reply and logging class beside tile §3.4's (Wire N6).

- The substep floor (from 3a, marked `TEMPORARY(phase1/sim-clock)` in `src/simcore/core/heat.py`): `World.advance`
  takes `max(heat.min_substeps(dx), stability)` substeps per call, the retired rigs' 4/16/64 as 0.16 m² / dx²,
  whatever the call's length. On every 6 s turn the floor, not stability, sets the count; stability alone changes
  every determinism digest (measured in 3a). Replace it with an accuracy floor per step length, with new goldens
  and `tests/test_determinism.py::TURN_SUBSTEPS` updated, and rework its other callers:
  `tests/test_heat.py::_error` and `::test_insulated_world_conserves_heat` pass it to 3,600 s calls, where it means
  nothing, and `::test_the_substep_floor_follows_the_grid_spacing_as_the_rig_profiles_did` pins it.
- A short composition note first: cell state, body state, ledger, clock, intent log; no god object.
- The step as a fixed, ordered tuple of laws, each with `stable_dt(state)` and `step(state, dt, ledger)`;
  topology changes read from `topology_version`. No discovery.
- **The field registry:** one list in code that the grid's storage, the snapshot, the determinism digest, the
  memory budget and the save all read. Step 6's fields join it, and step 7's catalogue is generated from it.
- Each law split into `prepare` and an array-only kernel, with a bit-identity parity test (the numba seam; no
  numba until a profile asks).
- Intent kinds ranked as `boundaries.md` §6.2 says; a `retired:` list of verbs, and refusal codes append-only, tested.
- Replay goldens keyed by an environment digest; the log header's field list as merged in step 1.
- The u16 region-id array (world_model §10 row 4), which `fire_solid.md` §0 leans on.
- **6.0a rides this line** (`fire_solid.md` §0, §5): the split material data, its loaders and versions, and the
  fuel tables' registry entries, before the log writer records the first golden.
- **The SEM stimulus contract's 5a half** (`sem_stimuli.md` v5 §5, §7.1, §11.1; the composition note cites §11.1,
  A-S10): reserve lane chains (row lanes keyed `(name, derivation_version, producers)` with producers the transitive
  closure over every law's declared reads and writes, an events lane and a per-tick bound lane per NPC; A3-S5, W11,
  DP3-N2, S-F3, N3), header slots (schema, `BoundFrame` and receipt versions, each law's version, truth constants
  including the per-tick event budget, the largest cognition divisor and the maximum emitter count; DP3-N3, DP-F-S3) and
  the `join`, `leave`, `agent_ready`, `agent_failed` records; the per-tick law slot, the two-rate contact exchange,
  the `body_points` container (A3-S4) and `radiant_emitters` keyed `(writer law, source object id, primitive id)`
  (DP-F-N1); every `forbidden` list from `_core_modules()` with `as_packages = false`, asserted by its equality test
  (N-S3, verified on a toy).
- **Digest plants 5a can build, on a toy row** (§5; Y7, S-F4): a toy law change moving a digested value by at least
  one rounding quantum, requiring a first differing tick named by the per-tick lanes (the tissue numbers, 10⁻¹²
  relative at tick 0 and one ulp at tick 120–152, were measured before rounding, N-F5); a toy producer two hops
  upstream bumped alone changes the row's key (A3-S5); an unbound row added stays green.

## Step 5b, bodies and movement (`tile_and_client.md` §2, §3, §4.1)

- From step 3b part (b)'s review (Determinism N7): a spawn maps to a cell in integers (`at_mm * 1000 // dx_um`), with
  a stated side for a point on a cell face; the alley's spawn sits on the floor's top face at every grid.

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

- **The SEM stimulus contract's 5b half** (`sem_stimuli.md` v5 §3.1, §4.5, §7.1, §7.3): `body-protected` with
  layer 6's modules (`Simulation`, the applier, the frame publisher) as allowed importers, `body-layers` in the order
  `contact`, `tissue | irradiance`, `store`, `spec | sites`, `geometry` (verified on a toy: every needed import kept,
  `spec → store` broken; split `spec | sites` if `sites` imports `spec`), and `CORE_PUBLIC_SURFACE` gaining
  `body.spec` with `MEMBRANE_SURFACE` subtracting it (A3-S2, A3-S6, A3-N1); the store's writer allowlist and its
  ownership scan (A3-S6); `store.py` implementing `body_points` with no copy, and a save–load plant of a carried field
  marked `derived` (A3-S4).
- **The core node** (§3.1; N-F2): the 245 kJ/K store with its metabolic source and fixed effector settings; closed
  form: the two-node steady state (core and skin) for a fixed ambient; plant: drop the source, and the `bodies`
  ledger's residual goes red.
- **Posture, gaze, breath and the thermoregulatory effectors** (W12, §3.1): stage-1 finite and unit-vector checks,
  ranges in `ActionLimits` from `data/`, a gate-registry row each, every rejection path tested, a Hypothesis "never
  crashes" property; plant: a NaN gaze is a `malformed` receipt and the world advances (W-N4). The effector kind is
  refused `malformed` until a body declares agent regulation, the body-instance field reserved here.

## Step 6, fire (D30, T13; `tile_and_client.md` §5)

**Superseded (owner, 2026-11-20).** Step 6 is the ladder of `fire_model.md` v2, built from `fire_solid.md` (6.0b,
6.1) and the later rung designs. The list below is kept as the record of what the tile spec asked; each item is
answered, replaced or carried by those documents (their §10 and §7 tables).

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

- The frame grammar's extension rule (`client_rendering.md` §4.1); fixtures for an unknown optional channel
  (ignored) and an unknown required channel (refused).
- The engine `build` in `welcome` (`client_rendering.md` §4.1) and the version `error`.
- A refusal for exhausted u16 region ids.
- JSON reads floats (`client_rendering.md` §4.1; the pin is `boundaries.md` §9.1's): decoder fixtures with an integer
  at 2^53 and at 2^53 + 1 (refused); stage 1 refuses `5500.0` and `true` where an integer is expected (Python reads a
  float, and `bool` is an `int`).
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

- Decide frame retention per agent before agents land: a frame pins a full grid (~100 MB at 5e6 cells); owner,
  2026-11-20.

It needs step 7: the host's stage 1 for worker speech calls `engine.text.player_text` (TB-S9).

**The SEM stimulus contract's agent half** (`sem_stimuli.md` v5 §3.2, §4, §6.2, §7.3):
- `stimuli/wire.py` (importing only `checks`, `readonly` and numpy), and `schema.py`'s rows, site sets and binding
  validation, land here, before the codec (Y3, S-F2); `CORE_PUBLIC_SURFACE` gains both and `MEMBRANE_SURFACE`
  subtracts them (N-N1); `agents-reads-body-frames` with `allow_indirect_imports = false` and a grimp closure test over
  `AGENTS_SURFACE` (`stimuli.wire`, `checks`, `readonly`) and each member's parent packages, planted with a surface
  module importing `body.spec` and with a re-export in `core/stimuli/__init__.py` (W9, Y4, A3-S1, N-N2, W-N5). The
  worker sends intents as wire data; stage 1 parses them host-side (N-S2).
- Versions and gate rows: binding table, `BoundFrame`, receipt, `welcome`, `step_output` (W13); replay refuses an
  unknown format version by name, planted by bumping the receipt version (W11).
- Receipts: `pid` per NPC (W14); kinds per D15, decided by stage 1, every stage-2 result `accepted`; one `Receipt` in
  `stimuli.wire`, mapped from `intents`' refusal codes by layer 6 (N-S1); delivery concatenates undelivered ticks,
  planted at divisor 10 by delivering only the current tick's (W10, C1); T11 sweeps every target-dependent refusal the
  applier returns (no such region, air, gone, off the footprint, nothing burning), once per affordance, each planted by
  mapping that path's `Outcome.applied` to the kind (W2, W-N2).
- Coalescing per tick (§4.3; R2, W-N1, DP-F-S2, S-F6, verified on a toy): a burst at divisors 1 and 10 with T9 comparing
  event content, red on per-delivery coalescing; receipts never coalesced, bounded by `ActionLimits`' per-step cap; the
  delivery bound refused at start against the socket buffer. `offset_us` is named as a strip exemption beside
  `SensorReading.timestamp` (`boundaries.md:572`) in the strip-list schema test (S3, W-N6).
- `L_us ≥ 1` refused at 0, planted (X5, C3).
- The overlap gate (§4.1; F1, Y6, DP3-N1): stub replies held and released at host hooks (before step 6, a test-only
  hook inside it, after the join) in two fixed orders; a cell-writing stub intent; every leg's lanes and record stream
  equal (DP-F-N4); the plant applies a `step_output` on arrival and the replay leg must go red (toy-verified: an `ignite`
  plant goes red on both legs, a posture plant only on replay).
- The worker's checks (§4.4): the value check before each push against the recorded clamped value, a bite counted,
  planted with a stub modulator writing during cognition (X1, Y2); `world_owned_sensors` equals the bound set, and an
  anonymous `world_set_axis` on a bound sensor returns `False`, planted with an empty tuple (Y8); the thread baseline
  at `agent_ready` by name multiset, planted with a new thread at the third park (C2); each re-baseline logs its
  delta, planted with a session open that leaks one thread (R4); a real-pymaxim test that makes one LLM step and parks,
  `xfail(strict=True, raises=AssertionError)` on OD-EA7 (`LLMCall_0`, `llm_worker.py:665`; R1); one
  `evaluate_failures` per agent step on a cognition tick, planted with a host step on a cognition tick so the count
  reads 2 (D2-S2, B-F-N4); the worker refuses `MAXIM_ENABLE_BODY_STATE_PROMPT` (D2-S3); the bindings-digest refusal
  planted by editing only the worker's copy (W4).
- Bounds (§4.3): a burst keeps the agent alive; a failed NPC's buffer stays empty for 10,000 ticks; a worker reading
  one byte at a time lives; one that never reads lets the world advance; one sending half a `step_output` is `hung`,
  nothing merged, matching replay (C4); NaN, ±Infinity, `1e400` and `bool` refused, each planted; each lifecycle row
  gets a crash-injection test.
- D14's Known gap (§4.6), entered with this line's code; the barrier's B5 row at 1× and the dial's maximum, counted
  per tick, with the pump's cost and GIL share, which T16a's flip waits on (F2, S9, C5, C6).
- Every strict red gate this line adds states `raises=` with the narrowest expected type (S-F5); a tooling test that
  fails on an `xfail` without `raises=` is a standards-backlog proposal for `phase1/standards-bars`.

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

**The lane's model (MS-S8, O18; `docs/design/inference_placement.md` and `inference_gateway.md`, O46–O54).**
- The lane dispatches through one inference gateway per placement on a scripted transport; Maxim's router is never
  built on this path. A missing local model with guests present refuses the session at start (typed, shown in the
  client); it never falls through to a remote placement.
- Tests (IP §2–§6, IG §1–§9): every rejection of the three files (an uncovered function, an unfitting envelope, a
  tier a no-degrade function forbids, an uncovered tokenizer family, `call_ceiling_s` not below the liveness ceiling,
  a `server` member declaring `max_in_flight`, mismatched endpoint ids); per-placement and per-group queues; `single`,
  `pinned` and `spill`; a load delay never moving a pinned function; cooldown, probe re-issue and down-for-session on
  failed starts only; the ceiling kill's trigger and collateral; each classification row (IG §5) and each outcome
  row (IP §2.6), with no reason or outcome crossing `AgentPort`; one `reply` per attempt and late replies after a
  cancel; one cache entry per occurrence; a poisoned entry ignored live; a rerun that never looks up a request
  cancelled before landing; a branch cache cut at the save point; a held reply across save and load; taint from
  every guest-string channel and its clearing by `purge`; `NO_PROXY=*` in the gateway's environment; provenance
  bounds; the transitive import set and the no-effect allowed set; the gateway log as the only place an endpoint may
  appear, and no credential anywhere; the dial-invisibility test of IP §6.4.
- **Deferred from the delta round (mechanism; trigger: writing that test in this step, unless Phase 4 is named):**
  probe outcomes that are neither success nor fault (delta concurrency D8); a start ceiling (D9); outbox overflow per
  kind (D11); the gateway's own sleeps on the injected clock (D12, Phase 4); disconnect behaviour of a non-streamed
  call (D6, Phase 4); collateral cost per kill and a ceiling rule from the reply tail (performance D-5); the instance
  model under concurrency (C7, Phase 4); per-transport stop reasons, refusal values and `allow_local_endpoints`
  (wire S-4, executor E-N6, Phase 4); the HTTPS `owner_lan` address check (executor D-S6b, Phase 4); the proxy re-read
  at each client build (trust D-S3); the no-effect allowed set (trust D-S5); call-time import capture (E-S9); slot
  reservation per function (C12, on the slot-wait meter); a dial-test failure schedule that stays recoverable and
  waits per reply (determinism N1); a probe of each server's real parallelism against its declared `max_in_flight`
  (performance S-3, Phase 4).

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
  typed refusal receipt carrying it; no receipt names an unminted pid; refusal receipts book no physical event, and
  no refusal's pid appears in a GL3.B2 row (Maxim's review of v6).
  Proven by deletion: a planted drop path that sends no receipt turns it red.
- **Crash recovery (O44, O45).** Each restore opens a new log segment, and its number is part of `session_id`; a
  dead worker's in-flight pids each get a typed `agent_failed` refusal receipt. A test: save, let the double mint
  several pids past the save (some settled, some in flight), kill the worker, restore from the older save (opening
  segment k+1), keep stepping; assert no new pid equals any logged pid (O44's floor, now this collision check) and
  every pid settles exactly once, the in-flight ones as `agent_failed`. Proven by deletion: keep the old segment
  number on restore and a duplicate pid turns it red; drop the receipts and an unsettled pid does.
- **Replay ids (O43, O45).** `session_id` is derived from the log header (the root id, the NPC key and the segment
  number): a test that two runs of one log, restores included, give equal ids, and that no wall-clock or uuid source feeds it (the determinism scan). The
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

## The SEM stimulus laws (with `tissue_temperature`, before Phase 4; `sem_stimuli.md` v5 §2.3, §3.1, §8)

Moved out of the design by the owner's split (2026-11-21). Each item is a test to write; numbers marked **D** were
measured in the research (L3) or the reviews, **M** are from memory and must be cited before `data/`.
- **Tissue:** a 3-layer Pennes column per point (0.1 / 2 / 10 mm, a node at each declared depth; Torvi & Dale, S);
  partial contact and clothing as sub-columns and layers. Closed form: the steady profile. The join and restart
  solve it directly (started uniform at the core it needs 1,060 s to settle within 0.1 K, **D**), with a test that a
  joined NPC's tissue doesn't move in its first second at ambient (PH2-N3).
- **The core and thermoregulation** (PH2-S2 re-ruled (c), owner, 2026-11-21; Physics S1, B-F-S3): a free core node,
  every watt booked signed in `bodies`. The plant (**M**, cite before `data/`): basal metabolism about 80 W (about
  45 W/m² over 1.8 m²); skin blood flow from strong vasoconstriction (tens of mL/min) to full vasodilation (about
  6–8 L/min, Rowell); sweat up to about 1–2 L/h, 1 L/h evaporated being about 675 W at 2.43 MJ/kg; shivering up to
  about 3–5× basal. The **ANALOG stand-in controller** follows Gagge's two-node model (Gagge, Stolwijk & Nishi 1971,
  **M**): set points, proportional effector commands within those ranges, marked to move into Maxim (M20).
  Verification: with effectors fixed, the two-node steady state in closed form; with the stand-in on, the idle
  steady state where production plus regulation balances losses, and the `bodies` ledger closing to its tolerance
  over one world hour; plant: drop the metabolic source and both go red. A cross-tier test of the plant at three
  grids. Validation against published two-node data is a Known gap if it misses. The unregulated drift was
  3.5–4.7 K/h (**D**, delta 2).
- **Sinks** (PH2-S1; tile §2.1's exchange-volume convection superseded by `sem_stimuli.md` §3.1): each point's
  convective sink read through `gas.at`/`gas.over` over a volume in metres (a fixed reservoir in Phase 1's still air,
  booked in `bodies`; rest 32.4 °C; with the tile's exchange volume as sink it rests at 34.7, **D**, reviewers'
  figures); the radiative sink named (v1: the fixed ambient) with the exact secant coefficient (a coefficient fixed at
  rest is low by 28% at 100 °C, 2.2× at 200 °C, **D**). Test: a two-region body, one region in a hot gas region of a
  fixture gas field, burns only that region; on the shipped path it waits for zones (P-N3).
- **Immersion and plume** (PH2-S3): a continuous gas-temperature field per flame (flame, intermittent and plume
  regions from a cited correlation), h(d)·(T_gas − T_s) per point; a cross-tier test with an outcome margin for a
  hand at the flame edge; until then "plume gas doesn't heat" is a Known gap with a number.
- **Contact** (PH2-B1): the object-side sub-mesh, refined to the substep's penetration depth, persists for the whole
  contact, read by the solid law through a conservative remap and remapped once at release. Outcome gate, with a
  horizon and a margin (P-S2): wood at 90 °C stays painless for 10 s with at least 1.9 K to threshold at the basal
  layer (the persistent reference hurts at 54.2 s, 100 °C at 12.5 s, 80 °C not in 60 s, **D**, `wood_horizon.py`);
  wood at 120 °C hurts at 0.76 s within the reference's own mesh-convergence spread; the per-tick rebuild is the
  planted red case (painless 90 °C wood hurts at 2.35 s rebuilt, 0.40 s from stale state, **D**). Two components on
  one solid cell solve in canonical order, held by a save–load test that reloads bit-identical (DP-F-S1).
  Convergence: rebuild interval × object nodes; the two-way coupling with a solid stepping at 0.5 s is unmeasured.
  Contact onset and release interpolate between poses (holding a pose quantises onset to ±0.1 s, 40–50% of steel's
  time to pain, **D**). Components share sub-mesh nodes, never just an object (DP3-S3); `contact.py` composes
  tissue's operator on one grid per component (A3-S3).
- **Accuracy:** error-controlled substeps per point, memoryless, against the header's kelvin tolerance; a fixed
  0.1 s step makes 70 °C steel pain 20% late and radiant error 1.25 K at 80 kW/m² (**D**). Ω's sensitivity is 5.1–5.5%
  per 0.1 K under L3's ΔE/R = 55,000 K, and 7.0–7.8% per 0.1 K if Henriques is P ≈ 3.1×10⁹⁸, ΔE/R ≈ 75,500 K (**M**):
  fix it after the constant trace (Y9, PH2-N1, P-N2). Convergence to 80 kW/m², for immersion and for contact.
- **Flux and occlusion:** quadrature view factors; intact authored geometry occludes as primitives in metres, altered
  cells by transmittance defined per path length (fraction/λ along the chord) or sub-cell reconstruction, with a
  grazing ray in the wall-edge test (PH2-N2); B28 first; a grid-only march is the planted red case. Cross-tier tests
  per coupling (occlusion, face emission, face contact, zone gas, immersion) at offsets 0, dx/3, 2dx/3, band gates
  and a wall edge; a half-shaded body's burned area matches per-point rays. Face couplings strict red in v1 (S4).
- **Damage:** Ω ≥ 1 at the basal layer is a burned point. A region half at 15 kW/m² and half at 5 burns first at
  6.2 s; one column at the mean, at 11.8 s (**D**).
- **Refresh schedule** (§8; DP3-B1, DP3-S1, DP3-S2): a cap of k pairs per body per emitter per tick, ranked within a
  body and an emitter by (last refresh tick, point id) (DP-F-N2), the literal "moved first" rule having starved
  stationary pairs for 100 of 100 ticks (**D**). At k = 12, ten running NPCs see at most 5 ticks of staleness, as a
  shared K = 116 did, and a shared cap changed A's refresh ticks when others ran (**D**, rerun 2026-11-21). k = 12 is
  the stationary floor (58 / 5 = 11.6), so a runner gains over v2's once-per-physics-step only at k > 12 (DP-F-N3). The header records the maximum emitter count; D12's measurement runs on one body at that
  count: time to pain and burned area against every-tick refresh, stepping from behind a wall into 20 kW/m² (pain at
  1.1 s). Emitters are summed in stable-key order (DP3-N5). Clustering's bound: the angular spread's maximum over the
  emitter's quadrature points (a 0.68 m flame at 1 m subtends about 38°, **D**).
- **Cost table** (basis: 58 points, the 0.1 m tier, light heat load ~1.4 s per world second, one emitter; 10 NPCs, per
  world second, **D**): skin at one substep per tick plus quadrature flux ~21–32 ms; visibility once per physics step
  ~73–90 ms (c ≈ 63–78 µs per pair); delivery ~15–30 ms; stationary ~110–150 ms against ~140; visibility every tick
  for ten runners ~365–450 ms; substeps near a fire ~11–14 ms on this basis (DP3-N4); contact and the Maxim body step
  unmeasured. 100 NPCs stationary: ~2.5–2.9 wall seconds per world second. Under D14 the barrier's parks divide by the
  cognition divisor (C6).
- **The first body** (§3.3): the region-to-modulator map, tagged ANALOG, with the planted-burn test (SF-2, trigger
  this PR); the A4 gain weighs `(|v−0.5|·2)³` (`encoder.py:596`), so centred at 33 °C over [−4, 70] °C, 45 °C weighs
  0.034 and 60 °C 0.39 (**D**); an apparatus check of the measured rest per depth and ambient in the shipped scenes
  against the declared rest (28.5–35.1 °C from 5 to 30 °C ambient, **D**; D2-N1).
- **Before `data/`:** trace Henriques' constants; grade Ω = 1 against two published second-degree times; record
  Jasiński's miss; cite the contact conductance (it moves steel pain 4.5×) and ambient h; anchor on ISO 13732-1
  Table A.1 (S); verify receptor depths, anthropometry, ear spacing and tidal volume; reconcile L3's buttocks share
  with `geom.py` (Q1).
- **T16a–c** (§4.6; B-F-B1): T16a strict red under D14; T16b green (the world half, per-tick bound value across the
  fixture drive's band edge between cognition steps); T16c strict red naming M4 and OD-A22, under D5 (c), asserting
  the between-pass publish joins its crossing tick. **The pain-path test** (§4.6; B-F-S2, B-F-N1): fingertip on 70 °C
  steel at the dial's maximum divisor over every cognition phase, a PainBus publish seen by a subscriber, a lead over
  Ω = 1 of at least a cited withdrawal latency (**M**) plus one cognition interval, the lead recorded in ticks.
- **T17** (§6.3), the thermoregulation future bar, strict red naming M20 and OD-C12; its world half is the core
  item's closed forms.
- **Plants for §6.3's gates** (S-F1): T1 a world module writing a drive or a PainBus publish; T4 a march that ignores
  the wall; T5 a model reading the combustion constant; T6 a model leaking a constant into a pre-event frame, which
  the probe must decode; T7 fire text in a receipt; T8 a sensor range computed from the scene; T10 a row added
  without its pin; T14 a row in `QUANTITIES` and a row with no receptors; T15 a model that delays the cue past the
  damage onset. T11's plants (moved from the design): batched `@`, a global sparse solve, batch-minimum dt, a
  cross-body cluster; a shared refresh budget, red only with a crowd or a cap below demand (one B at the floor stays
  green, **D**); emitters summed in append order, with at least three emitters of nonzero flux at A (two can't go
  red, **D**); B on the same floor object, with B's patch raising the merged component's substep count. Each first
  asserts that its permutation changes the planted computation's output (DP-F-S4).
- **The tissue row's digest plants** (moved from 5a, S-F4): a surface-conductance change moving a digested value by
  one rounding quantum; an order reversal in `reduce.py`, `join` unchanged, on one-sided exposure, asserting first
  that the permuted values differ; a bound home refused when a producer two hops upstream changes (A3-S5); events get
  a plant with their first producer.
