# Boundaries between engine, game, Maxim and the outside world (design v3, 2026-11-16)

**Status:** DRAFT v3, for a delta design review before any code. v1 (47add00) went to a six-lens review
(`docs/design/reviews/boundaries/`: 18 BLOCKER, 52 SHOULD-FIX, 29 NIT), folded in v2. v2 (4f7a754) went to the
seven-lens foundations review with part 2 and the Maxim drafts (`docs/design/reviews/foundations_v1/`). This version
folds every foundations BLOCKER and SHOULD-FIX that touches it, and the owner's decision O6 (§0). Its agent sections
(§7.1, §7.4, §8.1, §9.3) were revised on 2026-11-17 to match `npcs_and_sem.md` v3 (O6a, O7a, O13). Two fold tables
(Review records, at the end) map each finding to where it landed.

**What changed from v2, in short:**
- **Mode (a) is dropped (O6).** Agents follow a host-driven embeddable contract: the host steps them, they return
  values, and the host owns every LLM call (§7; since 2026-11-17 by executing the requests `think` returns, O6a). This removes the agent lane's data race, the
  deadlock and the missing thought seam the review found.
- **The write window is ownership, not a flag**, because a view unlocked in one window stayed writable after it
  (§4.1). Frames are copies, published on change, with a stated cadence and thread scope (§4.2).
- **The layers are fixed** where the review showed contracts that would fail the day their modules exist (§2.2).
- **The log record gains `apply_us`, one ordering key, and kinds for speech, cancellation and failure;** `memory_write`
  leaves the world log (§6).
- **NPCs get a closed tool roster and a per-agent home,** and thoughts get budgets (§5.3, §5.4).
- **`phase1/gates` ships only what has a caller then,** and the agent foundations get their own PR (§11.1).

**What changed from v1, in short:**
- The sealed core is defined by what runs on the simulation lane, deny by default, and it now includes the code that
  writes the world (the bridge's write half and `place`). v1 sealed a package that didn't write anything.
- Writes are guarded by ownership: the world's arrays are read-only except inside one write window. Observation reads
  immutable per-tick frames. v1's read-only views guarded copies and could be undone in one line.
- Untrusted input is guarded at its sources (which modules may read files, JSON, YAML, sockets or the environment)
  plus an explicit gate registry. v1's lint keyed on parameter annotations and couldn't see the real door.
- One pipeline for every input, with authority per record kind and identity stamped from the channel. v1's "one
  door, same limits" had no authority model.
- The intent log record is defined. v1 promised one log without saying what was in it.
- The agent substrate has a home: an engine-defined `AgentPort`, run outside the sealed core. v1's seal contradicted
  the lanes design.
- Maxim is reached through named adapters with declared surfaces, not "only `sem_env`".
- New boundaries: the rendering tier never reaches physics; no file IO in the core; a shared intents layer; a
  geometry layer; percepts only through physical channels (B-13).
- The migration is not mechanical. It creates no empty game package, measures coverage by directory, and pins a
  merge order.

## 0. Decisions this design rests on (owner, 2026-11-16)

This document's decisions (20 rulings) are kept as records, with their dates, owner sections and status, in `decisions/boundaries.md`.

## 1. Why now, and what the code is today

Each boundary costs a few renames now, and a refactor across the protocol, zones, fuel and the lab later.

The survey behind it (`phase1/act-validation` at 2f200b5) found the game and engine in one package, IO in the core
and writers outside the world; §2 to §4 are what replaced them, and the review records keep the survey.

## 2. Packages and layers

### 2.1 The packages (B-1)

- **Rule:** the engine never imports the game or the experiments. The game may import the engine. What experiments
  import is `npcs_and_sem.md` §10's.
- **The engine's name** is `simcore` (O23; Q1). Below it is written `engine`, a working name. The reviews recommend a
  Maxim-neutral name, since B-2 says Maxim is swappable and `maxim_*` reads as Maxim's own namespace (Arch N3).
- **The game package `maxim_overdrive`** is created with the first game content (the lab, `phase1/lab`), not before
  (W1, W4). An empty package now would silently collect new modules from rebased branches.
- **The experiment harness** for Maxim's pre-registered experiments is Maxim-owned (`npcs_and_sem.md` §10; S10). It
  is distinct from the engine's verification harness (`engine.verify`).

| What | Where |
|---|---|
| Cells, geometry, laws, the simulation, intents, formats, the protocol, the SEM membrane and agent adapter, the host, the verification harness | engine |
| Body grammar and receptor models (physiology is mechanism) | engine (BF-15) |
| This game's content and rules: the lab tile, its scenes, story, NPC rosters and body instances, cradle arcs, calibrations, tuning | game |
| Pre-registered Maxim experiments | a Maxim-owned harness (`npcs_and_sem.md` §10) |
| Godot: the frame decoder and channel bindings | `client/addons/engine/` (S8) |
| Godot: scenes, art, game UI | `client/game/` |

- **How game rules reach the tick (foundations Arch S11): as data only.** The game supplies vocabulary,
  calibrations, rosters, scenes and limits through the engine's gates. A new mechanism (a law, an intent kind, an
  affordance with new physics) is engine code, reviewed as engine code; no game callable ever runs inside
  `Simulation.step`. This matches "physiology is mechanism" (BF-15) and keeps the banned-list contract sufficient.
- **Split trigger (S8):** split into two repositories when an outside consumer wants the engine (a second game, an
  outside developer), or when measured: over the last 20 merged PRs, at least 15 touched only engine paths. No date
  trigger. Phase 2 changes engine and game together, and a split then would double every feature's PRs.

### 2.2 Layers inside the engine (B-8)

The rename re-homes modules by layer, so the package cut and the layer cut agree (S5). A layer imports only layers
below it. Siblings on one line are independent of each other.

**The layers, as built** (docs-contracts ruling 49; `pyproject.toml` `[tool.importlinter]`, contract `layers`): five,
bottom to top `simcore.core` < `simcore.adapters` < `simcore.protocol` < `simcore.host` &#124; `simcore.verify`
(independent siblings) < `maxim_overdrive` (the game). This order is the contract; O24 is its record. The table below is the map of where splits are expected to fall
(O24): its `engine.*` names are working names, and its numbered layers are not import contracts. Built today:
- layers 0–6 are `simcore.core`: `checks`, `materials`, `grid` (`engine.cells`), `heat` and `damage`
  (`engine.laws`), `imagination`, `scene`, `intents` and `limits`, and `world`, `applier`, `frames` and `simulation`
  (`engine.sim`), with `readonly`, `refusals`, `schema` and `digest` beside them;
- `engine.loaders` and `engine.adapters.sem` are `simcore.adapters`;
- `engine.tiers`, `engine.encoding` and `engine.protocol` are `simcore.protocol`;
- `engine.host`'s sessions, `TimeAuthority` and WebSocket server are `simcore.host`;
- `engine.verify` is `simcore.verify`, which imports nothing from the engine (`verify_harness.md` §2).

Not built: `engine.geometry` (primitives and footprints are in `scene`), `engine.inference_wire`,
`engine.adapters.inference` and `engine.adapters.agents`. Where a
module sits inside the core (`core/body`, `core/stimuli`) is `sem_stimuli.md` §7.1's.

| Layer | Modules | Notes |
|---|---|---|
| 0 | `engine.checks` | validation primitives, bounded echo (`shown`, moved from the bridge, TB-S3) |
| 1 | `engine.materials` | `Material`, `MaterialTable` types and the truth constants. No IO, no rig. |
| 2 | `engine.geometry` | primitives, CSG and footprints in metres; no cells (S5) |
| 3 | `engine.cells` | the grid, regions, ownership arrays, the write window (§4.1) |
| 4 | `engine.laws` | heat, damage; later zones, gas, fuel |
| 5a | `engine.imagination` &#124; `engine.scene` | imagined-object specs; the scene type. Both take primitives from `engine.geometry` |
| 5b | `engine.intents` | the action vocabulary, typed intents (the `imagine` intent carries a spec, so intents sit above imagination), `ActionLimits` (the type only), stage-1 parsing, the intent record, receipts, `StepOutput`, `Pending`, `Reply` and thought requests (S3; foundations Arch B3, S1; the v3 host service protocol is deleted, `npcs_and_sem.md` O6a) |
| 6 | `engine.sim` | `World`, `Simulation`, the integer clock, the intent applier, construction (`Simulation.from_scene`, which builds scenes and loads saves from decoded data), the frame publisher, the `AgentPort` protocol |
| 7a | `engine.loaders` &#124; `engine.tiers` &#124; `engine.inference_wire` | file gates (including `ActionLimits.load` and the save's decoding half); `RigProfile` as a rendering tier |
| 7b | `engine.encoding` &#124; `engine.adapters.sem` &#124; `engine.adapters.inference` | display quantization (B-6, uses tiers); the Maxim membrane; inference gateways (`inference_gateway.md` §1) |
| 7c | `engine.protocol` &#124; `engine.adapters.agents` | wire decode and encode (uses encoding); the agent adapter (uses the membrane's types) |
| 8 | `engine.host` &#124; `engine.verify` | pacing loop, lanes, sessions, `TimeAuthority`, the thought gate and the thinking lane that executes model requests, dilation measurement, log writer; the verification harness (S12) |

- **Layers 0–6 are the sealed core** (§3).
- **The written order is the order committed,** checked red-first on today's code (X S-2, Arch N1). Today `config`
  imports `checks`, so `checks` sits below `materials`. `imagination.spec` imports `world.scene` for its primitives;
  after the move it takes them from `engine.geometry` (layer 2), so `imagination` and `scene` are independent
  siblings. **Every dependency the review found is now a sub-layer** (foundations Arch S1): intents above imagination
  (the `imagine` intent), encoding above tiers, protocol above encoding, the agent adapter above the membrane. The
  non-independent `:` form is never used.
- **Skip-layer rules (S2; foundations Arch S2).** Layers allow skipping, so a further forbidden contract applies:
  `engine.adapters.*`, `engine.protocol` and `engine.host` import only `engine.sim`'s public surface,
  `engine.intents`, `engine.materials` types and `engine.checks`. Never `engine.cells`, `engine.laws` or
  `engine.geometry`. Every rule names a module, since import-linter can't forbid a function:
  - **the reach and centroid checks** (today's `_on_region`, `centroid_m`) are stage-2 world checks in the applier,
    where world-state checks belong; the membrane's gate half needs no geometry;
  - **the name rule** (`entity_key`) moves to `engine.checks`, which the gate half may import;
  - **scene build** happens only through `Simulation.from_scene`, so adapters never see a build function;
  - **the save loader** splits: decoding in `engine.loaders` (layer 7a), construction in `engine.sim`, so the only
    cell writer outside `step` is in the core;
  - `World.sources` becomes private behind an intent.
- **Rendering never reaches the truth (S1, new boundary).** The core (layers 0–6) is forbidden from importing
  `engine.tiers`. Today the rig decides physics (`MaterialGrid.empty` takes `rig.cell_size_m`; `World.advance` takes
  `rig.min_substeps_per_turn`; `Scene.build(rig, …)`). The rename splits `config` into `engine.materials` (truth) and
  `engine.tiers` (rendering), and those parameters move to the truth constants. This is where world_model D20 becomes
  enforced.
- **The membrane never reads display channels (BF-12).** `engine.adapters.sem` is forbidden from importing
  `engine.encoding`.
- **Layers are import direction, not write permission (D-N5).** Writes are guarded by §4.1, not by B-8.

## 3. The sealed core (B-3)

- **Rule:** the core is the code that runs on the simulation lane: layers 0–6 (§2.2). It is defined by exclusion,
  matching today's scan: every engine module except an explicit non-simulation list (`engine.loaders`,
  `engine.encoding`, `engine.protocol`, `engine.adapters`, `engine.tiers`, `engine.host`, `engine.verify`) (S4, D-B1).
- **The writers are inside it.** The bridge's write half (`apply`, `_strike`, `_ignite`, douse) moves into
  `engine.sim` as the intent applier. `place` becomes the stage-2 apply of an `imagine` intent (§5.3). A non-vacuity
  test asserts that every function assigning into a cell array, `regions` or `sources` is defined in a core module
  (D-B1).
- **Agents are not in the core** (O3, O6, BF-2). The core defines `AgentPort` (§7.1) and never imports `maxim`.
  Agents run on the agent lane (§7.1) through `engine.adapters.agents`.
- **A second sealed set: the agent step path (foundations DR-S10).** `engine.adapters.agents` minus one named
  host-only module (wall timeouts) is under the same banned list and AST scan as the core, and the tripwire also runs
  on the agent lane's thread. It owns the strip, the push, per-NPC noise and step scheduling, which decide dial
  invisibility and tier-2 reruns, so a `time.monotonic()` there must go red. Each entry is proven by a planted call.
- **No file IO in the core (D-B2, S-8, S9).** Loaders are gates in layer 7. The core receives frozen, loaded tables
  as required keyword-only parameters (`materials=`, `limits=`, no defaults). `MaterialTable.load()` with no path
  disappears.
- **One banned list,** read by both the import-linter contract and the AST scan, or a test asserting they are equal
  (S4). The list (D-S2):
  - time and randomness: `time`, `timeit`, `datetime`, `random`, `secrets`, `uuid`;
  - the OS and dynamic import: `os` (wholesale, which covers `os.urandom` and `os.getrandom`; X S-1), `importlib`,
    `sys`, `platform`, `locale`, `signal`, `gc`, `weakref`;
  - IO: `pathlib`, `io`, `yaml`, `json`;
  - concurrency and network: `threading`, `asyncio`, `concurrent`, `multiprocessing`, `subprocess`, `socket`,
    `websockets`;
  - `maxim` (also held by B-2's protected contract);
  - `logging` (docs-contracts ruling 51): a record carries a wall-clock stamp and a handler can write a file, and the
    core logs nothing today.
  - **Explicitly allowed:** `hashlib`, `math`, `dataclasses`, `enum`, `typing`, `numpy`, `scipy`.
  - **As built,** the list is `pyproject.toml`'s `sealed-core` contract, equal to
    `tests/test_determinism.py::SEALED_CORE_BANNED`, which bans more than the groups above.
- **What imports can't show** is held by the AST scan, extended (D-S3, X S-1): `__import__`, `exec`, `eval`, `open(`,
  `id(`, `getenv`/`environ`, iteration over a `set`/`frozenset`, `sorted`/`np.sort`/`np.argsort` without
  `kind="stable"` on non-unique keys, `np.seterr`/`errstate`, BLAS calls (`@`, `dot`, `linalg`, `einsum`). **BLAS is
  forbidden in the core** for now. None exists today; the first solver that needs it brings a threads-pinned policy
  (`threadpoolctl`, 1 thread) to review.
- **The tripwire is a test, not a runtime seal (D-S1, D-N3).** It is a **profile hook**
  (`sys.setprofile`, and `threading.setprofile_all_threads` on Python ≥ 3.12) on `c_call` events, matching the
  function objects themselves, with a frame-based allowlist. Patching module attributes can't work: `datetime.now`
  can't be patched, `default_factory=time.time` and from-imports keep the original function, and a process-global
  patch trips the wall reads meant to stay (foundations X-1, verified in a probe). It runs over the golden replay
  corpus, on the simulation and agent-lane threads, with an explicit denylist (`time.*` clocks,
  `datetime.now/utcnow/today`, `date.today`,
  `os.urandom/getrandom/getpid/environ`, `uuid1/4`, `secrets.*`, `SystemRandom`, `threading.get_ident`,
  `Random.seed(a=None)` detected from the frame, `SeedSequence()` with no entropy, `time.localtime`, `time.strftime`
  and `datetime.fromtimestamp` with host-zone rendering, `time_ns`, numpy's global `np.random`), each proven by one
  planted call, including a `default_factory` stamp, a from-import, and a timeout on another thread that must not
  trip. 18 pymaxim modules bind `uuid4` or `datetime` at import, and numpy and stdlib RNG states are compared before
  and after each step (world_model DLP S-8). It guards only what the corpus exercises, and it ships with sim-clock.
- **Dilation is measured in the host** and enters the `Simulation` only as recorded data (Arch N7), so nobody
  exempts the core to measure it.
- **This guards mistakes, not adversaries.** ctypes and buffer tricks stay possible (D-B4).

## 4. Writes and observation

### 4.1 One write window (the guard for both writes and observation)

- **Every array the core owns is read-only at rest.** This includes the grid's channels, region masks and
  `MaterialTable`'s arrays (always read-only after construction; nothing writes them).
- **The write window is ownership, not a flag (foundations DR-B4).** v2 flipped the owner's flag for the window.
  Measured on numpy 2.5.4: a view that re-enables itself while the window is open stays writable after it closes, so
  the guard failed while its proof tests (all run with the window closed) passed. Instead, `with cells.writing() as w:`
  yields fresh writable arrays (the only writable handles), and swaps them in as the new read-only owners at exit. No
  handle outlives the window.
- **The window is entered only by:**
  - `Simulation.step` (the laws during advance, and the intent applier);
  - construction (`Simulation.from_scene`, and the save's construction half), the third writer (S11, S-7).
- `regions` and `sources` are `MappingProxyType`. `sources` changes only through the applier.
- **Thread scope.** The window is a single-thread guarantee. Across lanes the guard is §4.2's rule that nothing
  outside the simulation lane holds a reference to a core array; "a write anywhere else raises" holds on the
  simulation thread only, and the design says so (foundations Arch S4).
- **What this buys:** "every write happens under advance or intent application" becomes "a write anywhere else
  raises" on that thread, instead of a test that sees only exercised paths (TB-S7). Heat's in-place updates run inside
  the window, on the window's arrays.
- **Proof tests:** for every outward surface, each of direct write, `flags.writeable = True` then write, write
  through `.base`, ufunc `out=`, and attribute assignment must raise; and **a view unlocked inside a window, written
  after the window closes,** must not change the world (DR-B4).
- **As built since step 5a's PR 4a.** The window's owners are `Simulation.step` (one window per tick: its records,
  then physics), scene construction (`Scene.build`) and `imagination.place`, marked for PR 4b because `imagine` has no
  intent kind yet. The applier runs inside the step's window; a frame is published once per tick (`sim_core.md`
  §4).

### 4.2 Observation reads published frames (B-10, rewritten)

- **Rule:** percepts and instruments are immutable samples of one published frame, stamped with its tick. Nothing
  outside the simulation lane holds a reference to `World`, the grid or `MaterialTable` (S6, BF-4, D-S5, X-3).
- **Frames are copies, published on change (foundations Arch S4, DR-S9).** Never the owner, which the next window
  replaces. Cells change at physics steps and at intent apply, so a frame is published then, not per tick. Agents get
  reductions (per-region and per-NPC scalars from the bincount pass), not grids: a full-grid copy is 64–80 MB per tile
  at 0.1 m, about 13–16 GB/s of copying if published per tick at 20×. The copy and the publish are B5 rows.
- **Cadence** is `tile_and_client.md` §4's, so a receipt's after-frame exists on its apply tick. The design never
  promises "one tick" of reafference for effects that only show at the next physics step.
- **Sensors type against a `Frame`/`Observation` protocol** with no `advance`, `sources` or `grid`, so mypy refuses
  a peek (D-B4). `RegionSensor` stops holding `World`.
- **Every intent records `observed_tick`,** the frame its decision used (D-S5). For a client intent the host
  stamps the last cell frame's tick, not the last `tick` message's (DC-S1); a client-supplied value is refused (TB2-S6).
- **Which frame an agent reads:** one pinned per agent by the adapter, the frame observed at its last `step`
  (`npcs_and_sem.md` §7.3).
- **Observation never draws from the World's generator.** Percept noise uses the per-NPC stream (§7.3) (D-S5).
- `world.snapshot()` already copies. Its only change is B-6's move to `engine.encoding` (Arch N6).
- **Tests:** a reading taken at tick T is unchanged after `advance`; a sensor holds no `World` reference; a read from
  a second thread mid-step returns the frame for T−1, never a mix.

### 4.3 Pushing percepts into bodies (BF-5)

- Maxim bodies perceive by push. The push path and `world_set_axis` are `sem_stimuli.md` §4.4's.
- **This is a sanctioned mutation of agent state.**
- **Every body sensor the world simulates is world-owned.** A modeled `self_effect` is allowed only on sensors the
  world doesn't simulate, and each one is listed as an ANALOG divergence. Otherwise an NPC is burned twice, by the
  YAML delta and by physics.

### 4.4 B-13 (new): percepts come only through physical channels at the perceiver (BF-7)

- **Rule:** a percept is a reduction of registered physical channels, evaluated at the perceiver's position and
  receptor, with a line-of-sight gate once light exists. The membrane reads the world only through frames and the
  field registry.
- **Today's region sensors are test and lab instruments,** relabelled as such (an ANALOG divergence), never an NPC's
  input. **An instrument an NPC uses is an in-world device** with a position, its own physical reduction (a probe, a
  lag) and a display perceived like any other percept (foundations BF2-6; `npcs_and_sem.md` §7.1).
- **The membrane drops `cell_size_m`** from readings and entity metadata (an instrument may carry it), which put the
  rendering tier in front of cognition (foundations Wire S6).
- **Lands:** the import half in `phase1/boundaries`; the perceiver half with the first NPC body (Phase 4).

## 5. Untrusted input (B-4, rewritten)

### 5.1 Validation lives in constructors; frozen means deep

- **Rule:** a type's constructor validates. A gate is the decoder that turns bytes (or a Maxim call) into
  constructor calls, and holding an instance is proof it is valid (TB-B2, TB-N3). "Past a gate", not "inside" one
  (TB-N1).
- **Frozen means deep:** tuples, `frozenset`, `MappingProxyType`, and numpy arrays read-only at the owner (§4.1).
- **The violations v2 listed** (`Region.cells`, `MaterialTable`, `Material`, `RigProfile`, `Budget`) are fixed in
  3b; the strict material table v1 format is still its own step.

- **`World` and the grid are the sink,** mutable by design inside the write window, not "objects past a gate".
- **Maxim's own types are a named exception:** `ModulatorResult` (`params`, `metadata`) and `SensorReading`
  (`extra`) are frozen dataclasses holding plain dicts. The membrane only builds them outbound; it never trusts one
  inbound. Not mutating them is OD-C7 (freezing deferred); it had no home in v2 (foundations Arch S8, Wire S11).

### 5.2 Guard the sources, not the signatures

- **Input primitives are allowlisted by module (TB-B1, B2, X-2).** Only gate modules may call `yaml.*load*`,
  `json.load(s)`, `Path.read_*`, `open`, `np.load`, `os.environ`/`getenv`, `sys.argv`, or a transport receive. Held
  by an import-linter forbidden contract on `yaml` and `json` outside the gate modules, plus the AST lint in
  `scripts/lint_standards.py` for the calls.
- **Banned everywhere:** `pickle`, `marshal`, `yaml.load` without a `SafeLoader` subclass,
  `np.load(allow_pickle=True)`, `eval`, `exec`.
- **A gate registry** in `lint_standards.py`: gate name → kind (authentication, authorization, validation) → its
  rejection-path test module → status (meets the contract, or gate-to-be with its row). Each gate module is measured
  at 100% branch coverage.
- **The registry check is mechanical, not a reachability analysis (foundations Arch S15, TB2-S10):**
  - **every public callable defined in a gate module** has a row;
  - **every method of a class implementing a Maxim protocol** (`Modulator`, a sensor) **or
    `AgentPort`** is an entry point and has a row. In-process objects from Maxim (tool
    params, `Entity` targets, thought results, streamed tokens) reach the engine only through those methods, so they
    are covered without an input primitive.
- **Proof:** plant a `json.loads` in a non-gate module; a public entry with no row; a new `handle(raw: bytes)` inside a
  gate module (v1 B2's exact scenario); and a new `Modulator` subclass whose `execute` has no row. All four go red.
- v1's annotation rule is dropped. It missed `execute(params: dict[str, Any])` and every path-taking loader, and
  flagged four non-gates (X S-4).

### 5.3 The gates (TB-S1)

| Input | Source | Authentication | Authorization | Validation (gate) | Lands |
|---|---|---|---|---|---|
| NPC tool calls | Maxim (`ModulatorAffordanceTool`) | the stepping agent's bound actor; a call whose modulator is bound to another actor is refused (foundations TB2-S8) | per-kind authority (§6.1) | `engine.adapters.sem.StructureModulator.execute` (X-2), with `engine.intents.parse_action` as stage 1 | today; moves in `phase1/boundaries` |
| **The NPC tool roster** (foundations TB2-B1) | Maxim's tool registry | — | **a closed allowlist**: the membrane's affordances plus reviewed cognition tools; nothing that reaches the host's files, processes, network or Maxim's operational mode | the agent adapter refuses to step an agent whose registry holds any other tool, or an `operational_mode` with filesystem reach; proven by a planted `BashTool` | `phase1/agents` (red gate against real Maxim until tier A) |
| **Agent homes** (foundations TB2-B2) | Maxim's `data_home()`; saves | — | one home per agent, under the save; never `~/.maxim` | until `AgentHome` routes every store, each real agent runs in its own worker process, its working directory and environment as `npcs_and_sem.md` §6.6 sets them; a test asserts two NPCs resolve different homes. Agent homes from outside this machine are a **gate-to-be**: a foreign save loads the world only and re-seeds agents from the roster; a home loads only from a save this machine wrote, checked by a per-install HMAC, until Maxim's persistence is pickle-free | `phase1/agents`; save v1 |
| `target=<Entity>` and other Maxim objects | Maxim's actor tool | — | — | resolved to a stable id at `execute`, namesake and identity checks before the intent is frozen (TB-S5) | `phase1/boundaries` |
| Imagined objects | world-side generator (O57) | the bound actor | the actor's budget | `imagine` intent: spec constructors at stage 1, `place` as stage 2 (TB-S6) | `phase1/boundaries` (kind), sim-clock (log) |
| **The worker channel** (`npcs_and_sem.md` §6.6; Exec B1, TB3-B1) | a real agent's worker process | one actor per channel, bound at spawn | — | the strictest contract: `npcs_and_sem.md` §6.6's codec, its tests and its `agent_failed` rule | `phase1/agents` (with the test double behind it) |
| Thought results: intents, speech and **memory writes** | the agent's `StepOutput` and `ThoughtOutput`, decoded from the worker channel | the bound actor | an NPC's own memory only, with provenance by source actor (§6.6) | everything re-validated **in the host**: intents and speech through stage 1, memory writes through the host's gate before the host passes them to `settle` (canonical order; O39); a **gate-to-be** until generate vs apply (OD-A18) gives the game a value to check, an OPEN divergence with a strict red gate (foundations TB2-S3) | `phase1/agents` (types); OD-A18 (memory) |
| **Thought budgets** (foundations TB2-B3) | the host's thinking lane | — | — | `npcs_and_sem.md` §4.7's caps, from `data/agents/thought_budget.yaml` | `phase1/agents` |
| **Player speech and all guest text** (foundations TB2-S1; TB3-S3, TB3-S4, TB3-N4) | network lane | session token | per-session rate limit | one gate, `engine.text.player_text`, for `speak` and every guest string that can reach a prompt (`npcs_and_sem.md` §6.6): NFC before the cap, some ink, never three inkless in a row nor five marks on one character, format and default-ignorable characters refused but joiners between visible ones and one selector after an emoji base (O61, O65, O70, O71) | `phase1/protocol` |
| **The response cache** (foundations DR-B3, TB2-S4, Wire S9) | disk, per save | — | — | `inference_placement.md` §4.2 | after tier A |
| **The inference gates** | `inference_gateway.md` §9 | — | — | listed there | `phase1/agents` |
| Scene files, saves, intent logs, bug reports | disk, **strangers' machines** | — | — | the strictest gate (world_model F14): no pickle, budget before allocation, all-or-nothing | scene v1, save v0, sim-clock |
| Rigs, materials, limits, vocabulary, presets, rosters, arcs | `data/`, `content/`, later mods | — | — | a loader each under the gate contract (§5.4) | today and as each lands |
| Handshake, per-launch token, `Origin` | network lane | the handshake below | — | the protocol decoder | `phase1/protocol` |
| Joins and leaves | network lane | session token | — | session to actor id allocation (below) | `phase1/protocol` |
| Controls: dial, pause, presets | host session | session token | `TimeAuthority` / `HostOnly` (below) | the protocol decoder | `phase1/protocol` |
| Client frames (intents) | network lane | session token | per kind | strict JSON decoder (§9.1), then stage 1; client-supplied `observed_tick`, `issued_tick`, `apply_tick`, `apply_us` and speech timing are refused, with golden rejection frames (foundations TB2-S6) | `phase1/protocol` |
| Snapshot frames, as the client receives them | server | — | — | the client-side decoder (defence in depth; never crashes on a bad frame) | `phase1/protocol` |
| Token delivery | env var or a 0600 file | — | — | a host config reader; never echoed or logged. The host owns `os` and `secrets` | `phase1/protocol` |
| `MAXIM_OVERDRIVE_*` env vars, the rig CLI flag | operator | — | — | a host config reader; the rig name from a closed set | `phase1/boundaries` |

**The handshake** (copied from `realtime_lanes_coop.md` §5, TB-4 to TB-6):
- **Two kinds of token, fresh each launch:** one host token and up to N guest tokens. The role is bound to the
  token, compared with `hmac.compare_digest`. One live session per token, and no promotion. Tokens reach the client
  by environment variable or a 0600 file, never argv, and never appear in a log or an error echo.
- **The handshake:** `hello` comes first and only once, within a deadline, its protocol read first; anything else
  ends it (`hello_first`), as client_rendering §4.3 ends a refused connection. There's a session cap. Client binary frames are refused. Any request carrying an `Origin` header is refused, including an
  empty one or `null`. Plain HTTP to the port gets a 400. The server binds the literal `127.0.0.1`.

**Actor ids and time authority** (copied from `realtime_lanes_coop.md` §4.2 and §5):
- **Actor ids are integers from the simulation lane's allocator**, issued when a join is applied, never reused,
  for players and NPCs alike. NPCs are allocated in roster order at load.
- **Joins and leaves are records** at a tick, in the log. When a guest leaves, its intents that already have a tick
  apply and the rest are discarded. **When the host leaves, the world pauses** (a logged time decision) until the
  host token reconnects.
- **`TimeAuthority`** sees a frozen view of the sessions. `HostOnly` grants the host and refuses guests, with a
  reason; it never returns `pending`. A `vote` message is refused in v0 (TB-17). A future vote needs a timeout and
  a quorum rule, and the "pending" reply is reserved for it.

**Two validation stages** (lanes §7, TB-13): stage 1 is typed parsing in `engine.intents` (shape, finiteness,
ceilings, with caps from `data/world/`); stage 2 is the world check at apply, in the applier (target exists, not
stale, budget). Both refusals are `error` or `intent_result` replies with a code from a listed vocabulary
(`tile_and_client.md` §3.4), and the world is unchanged. NPCs, LLM results and clients pass one gate.

### 5.4 The gate contract (TB-S2, TB-S3, X S-3)

Every registered gate meets all of these, with a rejection test each:
- one strict loader (repeated keys refused, as `_StrictLoader` does);
- a version field, unknown versions refused loudly;
- a closed key set (a typo is an error, not a silent default);
- one exception type (`ValueError` or a subclass), never `KeyError`/`TypeError` escaping;
- bounded echo through `engine.checks.shown`; anything agent-facing (errors, receipts) uses a **closed code
  vocabulary**, never exception text or paths, since `shown` bounds length and doesn't scrub (foundations TB2-S9);
- budgets checked **before allocation**: counts (primitives per spec), string lengths (names), nesting depth, total
  allocation (cells × primitives). `place` today stacks one mask per primitive before refusing anything: 1,000
  one-centimetre primitives cost about 5 GB at the max profile.

**Across the worker channel** (`npcs_and_sem.md` §6.6), stage 1 runs in the host on decoded values: an `Entity` target
arrives as a stable id and is re-checked, so nothing produced in a worker is trusted for having been a Maxim object.

Which gates meet this bar is the registry's to say (`scripts/lint_gates.py`; TB-S2, X S-3, TB-N2).

## 6. One pipeline for every input (B-9, rewritten)

### 6.1 Three rules (TB-B3)

1. **One pipeline.** Every record from any source goes: decode → stage-1 validation → log → stage-2 validation
   against the world at apply. NPC and player intents share the validators and the log.
2. **Authority per record kind,** from an actor role the host stamps:

<!-- contract: record.kinds: intent imagine speak control thought_cancelled thought_failed join leave agent_ready agent_failed floor_event reply_landed | not: tile_and_client.md latency_policy inference_placement.md set_material npcs_and_sem.md -->
| Kind | Who may emit it |
|---|---|
| `intent` (the kinds of `tile_and_client.md` §3.2) | any actor |
| `imagine` | any actor, within its budget |
| `speak` | any actor: an NPC only through a thought, a player only through a protocol message (foundations TB2-S1) |
| `control` (dial, pause, presets, `latency_policy`, the thought-pace table) | host sessions only, through `TimeAuthority`. **NPCs can never emit it, and dilation is never a lever a guest can request** (foundations TB2-S7, DR-S11) |
| `thought_cancelled` | the host, from world events in `cancel_on` only, rate-limited per source; a guest can't cancel thoughts by talking repeatedly (foundations TB2-S7) |
| `thought_failed` (reasons: `inference_placement.md` §2.6) | the host's thought gate (foundations TB2-B3, Wire S4) |
| `join` / `leave` | the network lane |
| host commands: advance (in ticks), rig selection, save, load, admin `set_material` | the host |
| host records: `agent_ready`, `agent_failed` (`npcs_and_sem.md` §6.6), `floor_event`, `reply_landed` (`npcs_and_sem.md` §6.6), redaction records (below) | the host |

- **Redaction records** (`npcs_and_sem.md` O26). Each purged span becomes a record (actor, tick, length) in the
  log. A reply that quoted the purged words is redacted too. A rerun reads recorded replies, never a model on purged
  text, and matches only up to the first redacted reply, which the log marks as a replay boundary.
- **Thought requests** come from an agent's `StepOutput` only; percepts may trigger them, rate-limited per speaker.
- **`memory_write` is not a world-log kind** (foundations Arch S6, Wire S4). Agent state lives outside `Simulation`,
  the core can't apply it, and replay never runs Maxim. Memory writes are agent-side values in `StepOutput`, recorded
  in an agent-side audit record after OD-A15, and saved with the agent home.

3. **Limits are the shared physics-safety ceiling intersected with the actor's capability.** `ActionLimits` stays
   the ceiling (and a refusal, never a clamp); capability comes from the body and, later, energy (Phase 5).

- **Identity is stamped from the channel, never read from the payload:** a client's session token maps to its actor
  id; an NPC's intents carry the actor the host is stepping (§7.1), and a thought request id is `(tick, actor, n)`
  from the host's thought gate. A guest sending `"actor": 0` changes nothing.
- **The intent id receipts carry is `(actor_id, seq)`** (foundations Wire S4); the thought request id is a separate
  id space for thoughts.
- The "fairness" argument is a game-design goal and no longer part of the trust rationale (TB-N4). Asymmetries are
  explicit in the table above.

### 6.2 The log record (D-B3, D-S7, D-S8, D-S9)

- **The log holds every input** to the `Simulation`, not only actor intents: every kind in §6.1, including refused
  intents (a refusal at apply depends on world state), controls (a `latency_policy` change included) and host
  commands. `advance` takes ticks, never wall-derived seconds.
<!-- contract: intent_record.fields: schema_version kind actor_id seq observed_tick issued_tick apply_tick apply_us params target invocation | not: invocation_id PhysicalEventId -->
- **An intent record** is frozen and versioned, with golden fixtures for its format:
  - `schema_version`, `kind`, `actor_id`, `seq` (per actor);
  - `observed_tick`, `issued_tick`, `apply_tick`, and **`apply_us`** (int64, the integer world-microsecond offset
    within the tick; foundations Arch S7, DR-S2, Wire S4). Never a float;
  - `params`: the **typed canonical** form after stage 1, so later gate tightening doesn't change old replays; the
    raw payload is an optional audit field only;
  - `target`: a **stable id** (a region name or persisted entity id), resolved at the door. Nothing identity-based
    crosses into the log;
  - `invocation`: optional and opaque, an agent's Maxim invocation pid (null for players). The host copies it and
    never mints or computes one. It is null, never a stand-in (no uuid, no executor `invocation_id`), until Maxim's
    G17 stage builds `PhysicalEventId`; until then any non-null value is refused with a typed code, and once the type
    exists any non-null value that isn't a pid.
- **The record's `seq`** is the client message's (`tile_and_client.md` §3.3).
- **Derived, never input:** receipts, refusal reasons, destroyed volume, `ModulatorResult`s. Replay recomputes them
  and checks them against a per-tick digest.
- **What is logged, kind by kind (foundations TB2-S2, DR-S8):**
  - **an NPC's thought is never a log input:** prompts, raw LLM text and tool-call text stay out; what a thought
    contributes is the intents and speech it produced, and those are logged;
  - **`speak` is logged with its text,** since other actors perceive it and it can cancel thoughts. That is the one
    place LLM-derived text enters the log. Bug reports redact `speak` text by default, keeping lengths and syllable
    stamps;
  - **`imagine`** logs its typed spec, whose names are bounded and validated at stage 1;
  - **`thought_cancelled` and `thought_failed`** are logged as records, so the world never waits on a thought the log
    can't explain;
  - memory writes are not world-log records (§6.1).
<!-- contract: ordering.key: (apply_tick, kind_rank, apply_us, actor_id, seq) -->
- **One ordering key, stated here and nowhere else (foundations DR-S3, Wire S4; supersedes `realtime_lanes_coop.md`
  §4.2's arrival-order `host_seq`):** `(apply_tick, kind_rank, apply_us, actor_id, seq)`. Controls and joins rank
  before intents: `kind_rank` `[engineering]` is join/leave 0, `time` 10, moves 20, `kindle`, `strike`, `douse`,
  `imagine` 30, and `ignite` (vocabulary v0 only) 30, host commands (§6.1's: advance, rig selection, save, load,
  admin `set_material`) 40, so a tick's world actions apply before the host's own operations (owner, 2026-11-21, via
  phase1/sim-clock), leaving room. The log is written in that order, so a replay never sorts. Float accumulations over
  named collections (today the deposit over `sources`) iterate in sorted-key order. Ordering keys are
  integers (D-N2).
- **Replay calls nothing live:** no model, no Maxim, no clock, and **never the response cache**
  (`inference_placement.md` §4.2). Tested by replaying with `maxim` blocked from import (foundations TB2-S4).
- **Replay reproduces the world, never the agents (foundations DR-S7).** Under O3 and O6 replay never runs Maxim, so
  it reproduces `World` bit for bit and no agent state. Why an NPC chose something needs a tier-2 **rerun**, against
  the rerun manifest (§6.3). So a save is a checkpoint plus the log for the world, and agent homes are saved as state.
  CLAUDE.md's replay sentence is scoped to the world when this lands (§11.2).

### 6.3 The log header (D-B2, D-S4)

- Content digests of the scene, the registry (from `world_v2.md` §8), the truth constants (including `tick_us`), both material files after the split (the
  engine's and the content's), the action limits, the imagination budgets and the SEM vocabulary, and of the body
  archetypes, items, spawns and the navigation constants (tile WT-S3); the run seed; the host's initial
  `latency_policy` and thought-pace table (later changes are control records, §6.2). Rate limits are pre-log and
  stay out.
- **Each material data file** (`fire_solid.md` §5.1) by logical name (no path), its version and its digest, plus
  one digest over the sorted recipe set (Wire S7).
- **Every version:** vocabulary, scene format, action limits (`actions.yaml`), protocol, registry, materials
  (world_model F16).
- **The log's root id and the segment number** (each restore opens a segment), recorded so replay reproduces
  `session_id` (O43, O45; `npcs_and_sem.md` §6.6).
- **The SEM stimulus slots** (`sem_stimuli.md` §5): `STIMULUS_SCHEMA_VERSION`, the `BoundFrame` and receipt
  versions, rows by sorted name with unit, site set and version, each law's version, the lanes, id maps, truth
  constants (K tolerance and its Ω error, the event byte budget, the largest cognition divisor, the maximum emitter
  count, refresh and clustering parameters, cutoff floors). Bodies and bindings ride `join` records.
- **The rig** (while it still feeds anything until the truth constants absorb it), the **engine SHA** and the
  `derivation_version` (world_model F15) (foundations Wire S8).
- **One digest form:** SHA-256 over a canonical serialisation of the loaded, typed value (sorted keys, fixed number
  format), so a YAML comment change doesn't refuse a replay. It is stored versioned, as `sha256/c14n-1:<hex>`, so a
  change of hash or serialisation is a new prefix a reader refuses by name. One canonicalizer, in
  `simcore/core/digest.py` (as built).
- **Dilation by cause** is log metadata the `Simulation` never reads (foundations Wire S7); it reaches the client
  through a host status message (`npcs_and_sem.md` §5.4).
- The environment: Python, numpy, scipy and BLAS versions, `platform.machine()`, numpy's CPU dispatch features, the
  BLAS thread count, the worker's `PYTHONHASHSEED` (pinned per run, `npcs_and_sem.md` §6.6), and a dirty flag
  (world_model F16, DLP S-7).
- **A content mismatch is refused, loudly.** An environment mismatch downgrades the replay to an outcome-class check,
  and says so, like the rig rule.
- **Goldens are regenerated only** on a recorded content or environment change, in a commit that says which; never to
  make a red test green.
- **A rerun manifest beside the header (foundations DR-S7, Wire S8),** with the same refuse-on-mismatch rule
  (except the items `inference_placement.md` §4.3 records, reports and never refuses), for
  tier-2 reruns that re-run agents: the digests of `data/agents/` (timing, speech, fatigue, thought budget), the
  roster and each agent home's initial state; the pymaxim version and config digest; the inference items
  of `inference_placement.md` §4.3;
  the agent seed namespace; the syllabifier version. A run with any machine-decided thought failure, or under
  `abandon`, is flagged tier 3 in it.

**The three tiers, by what each reproduces:**

| Tier | Reproduces | From |
|---|---|---|
| 1. Replay | the world, bit for bit | scene, header, log |
| 2. Rerun | the world and the agents, bit for bit | the above plus the rerun manifest and the response cache, after tier A and the barrier |
| 3. Live | the outcome class | anything with live models, abandon, or machine-decided failures |

### 6.4 Every writer, classified (S11, S-7, N-3)

| Writer | Writes | Class |
|---|---|---|
| `Simulation.from_scene`, the save's construction half | cells, regions, through `Topology` | construction (opens the window before the clock starts) |
| the applier: strike | a damage `Load` (`sim_core.md` §5.1) | intent application |
| the applier: ignite, douse | `sources` | intent application |
| the applier: `imagine` (today's `place`) | topology requests | intent application |
| `Topology` | cells, regions: every world edit, per batch | world edit (`sim_core.md` §5.1) |
| the laws in `Simulation.step` | their declared fields | physics |

- `StructureModulator.apply` stops being public. Its world-writing half becomes the applier; its gate half stays in
  the adapter.
- **A scheduled band-aid, marked.** After `phase1/boundaries`, `execute` calls the applier synchronously with no log.
  It gets a `TEMPORARY(phase1/agents): …` marker in the adapter, listed under Phase 1 in `docs/roadmap.md` (S11). v2
  targeted `phase1/sim-clock`, which can't remove it: the synchronous path ends only when `execute` stops applying,
  which is the agent foundations PR (foundations Arch S5). There, `execute` only parses, checks the bound actor and
  appends the intent to the stepping agent's outbox, returning a pending, `neutral` result
  (`npcs_and_sem.md` §6.2).

## 7. Agents, time and the action contract

### 7.1 `AgentPort` and the agent lane (O3, O6; foundations Arch B1, B3, DR-B1, Wire B2, B3)

The core defines the port; `engine.adapters.agents` implements it; the **host** calls it. Detail of the embeddable
contract Maxim must offer is in `npcs_and_sem.md` §6.1.

**One port, called by the host (`npcs_and_sem.md` O6a, superseding the v2 split of foundations Arch B3):**

| Interface | Defined in | Called by | Calls |
|---|---|---|---|
| `AgentPort` | `engine.sim` | the host | `npcs_and_sem.md` §6.6's one signature (O39) |

- **`StepOutput`** is a frozen value: intents (with `apply_us`), `speak` acts, thought requests, and memory writes.
  The agent never applies anything and never runs on its own thread (O6): `settle` is the only writer, host-called,
  and the continuation's host-owned header (budgets, `basis_seq`, landing ticks) stays in the host
  (`npcs_and_sem.md` §6.6).
- **Requests are values, so nothing calls upward.** The host service protocol of boundaries v2 and npcs v2 (`request_thought`, a gateway handle
  and an intent sink handed to the adapter) is deleted: with `think` returning `Pending(request)`, the adapter (layer
  7c) never calls the host (layer 8). Maxim has no inner tool loop (`runtime/agent_loop.py:2172`, `:2264` on
  7084f561); a tool call is an intent, and its result comes back as the next tick's follow-up.
- **The membrane factory** takes a frame source and returns intents in `StepOutput`, never `World` (foundations Arch
  S3, Wire B2).
- **The host's thinking lane** in `engine.host` executes request values, by deadline, writing the response cache, with
  cancel as a reply. It is the only path to a model and owns placement; host-owned gateways make the calls through
  Maxim's backends, never its router (`inference_placement.md`, `inference_gateway.md`).

**The agent lane (supersedes `realtime_lanes_coop.md` §4.1's "the simulation lane owns … agents" and "agents step
inside the simulation lane's tick"):**
- **One owner per agent,** in its own worker process (`npcs_and_sem.md` §6.3; its process and environment are
  §6.6's). The channel to it is a registered gate (§5.3), and a hung or dead worker ends as a logged `agent_failed`,
  never a frozen barrier (`npcs_and_sem.md` §6.6). The worker contains Maxim's default leak paths; it is not an OS
  sandbox.
- **The barrier (foundations DR-B1)** is `npcs_and_sem.md` §6.3's. Lockstep on intents alone isn't enough: agent
  code would race the tick, and what the cerebellum trains on would depend on the dial.
- **Agent isolation** comes from the worker process for real agents; tier A still proves it inside one process
  (OD-EA6), since Maxim's module-level state (global `random`, caches, the de-duplication window) is shared there
  (foundations DR-S5, TB2-B2).
- **`dt_ticks`** is as `npcs_and_sem.md` §2.1 states it (foundations DR-S1).
- **Agent state lives outside `Simulation`.** Save v1 persists the world plus each NPC's agent home, separately.
- **Lane hand-off is counted inside the modelled latency** (§7.3), so the threading design never decides an NPC's
  biology.
- **Inline later:** with requests as values the only nondeterministic input is the reply, so calling agents inside
  the tick is no longer blocked by determinism. But inlining puts Maxim back in the host process, which O13 made the
  trust boundary, so it is a design decision against O13, not only a B5 measurement (Arch N1).
- **Until tier A,** real Maxim behind the adapter is a strict red gate; every [now] agent test runs against the
  scripted test double, in a spawned worker behind the same channel (`npcs_and_sem.md` §6.2, §6.6).

### 7.2 The action contract: propose, receipt, settle (O6; BF-1, foundations BF2-3, Wire S12, Arch S13)

- **The engine's contract is propose → receipt → settle.** An intent produces one receipt. The agent-facing receipt
  is `sem_stimuli.md` §6.2's; the wire `intent_result` and its outcome kinds are `tile_and_client.md` §3.3's.
- **There is no blocking wait.** v2's mode (a) blocked Maxim's tool loop in `execute` until a world-time receipt. It
  deadlocked with the dilate policy on one worker (foundations Arch B2), raced the tick (DR-B1), had no route into the
  pipeline and no second lane to wait across (Wire B2), and credited only instant effects (Arch S13). Under O6 the
  agent returns intents as values and receives receipts through `settle`.
- **Each receipt is credited exactly once,** through `settle` (stale: `sem_stimuli.md` §6.2); a test asserts it.
- **Valence per D53:** the adapter always self-reports. `neutral` when the measured effect is nil or unverifiable,
  drive deltas through `measured_drive_transitions`; absent a report, Maxim books mechanical success as POSITIVE.
- **Credit reads declared sensors only,** the ones the affordance declares it affects, and never instruments.
  Slow-effect credit (ignite) is an OPEN divergence with a red gate until settle can carry a horizon (OD-A16).
- **Stale is context, never credit** (lesson 9). v1 neither refuses nor credits a stale intent
  (`sem_stimuli.md` §6.2), so stale's divergence is closed for v1; OD-A16 reopens it if `stale` becomes a kind.
- **Per-actor binding (BF-6; foundations TB2-S8):** each NPC gets its own entity and modulator, bound to its actor.
  `name` and `full_path` stay identical across actors (lesson 10). The adapter refuses a call whose bound actor isn't
  the agent it is stepping.

### 7.3 Three clocks (O4)

The three clocks are `npcs_and_sem.md` §1's.

Fields and tests laid now (detail and test designs in `npcs_and_sem.md` §2–§3):
- **No time field reaches cognition.** The adapter strips `observed_tick`, `issued_tick`, `apply_tick`, `apply_us`,
  receipt ticks, deadlines, the dial and dilation from everything it builds. A schema test (with
  `SensorReading.timestamp` as its named exemption, plus a value-level metadata check) and a prompt test (rendered in
  two time zones 13 h apart) prove it; against real Maxim both are strict red gates until tier A, since Maxim builds
  the prompt (foundations X-2, X-12).
- **The dial is invisible:** with a seeded wall-delay schedule on the thinking lane's replies, percepts, receipts and kinds are
  bit-identical at 1× and 20×, and a negative control under `abandon` must differ (foundations DR-S6).
- **Δt invariance,** with a relative 1e-9 tolerance and the planted Euler update in an exponential process
  (foundations X-11).
- **Per-NPC seeded streams,** keyed by stable identity, as `npcs_and_sem.md` §3.4 derives them (foundations DR-S4,
  Wire S3).
- **Timing units** are `npcs_and_sem.md` §9's; rates are integer divisors of the tick with a per-actor phase.
- **The membrane is the clock translator (BF-11).** Today `RegionSensor` stamps world seconds and Maxim's sensors
  stamp epoch seconds. Until OD-C2 and OD-A2 land, each field's clock is documented, and the mismatch is an
  OPEN divergence with a red gate (foundations Wire S10: v2 named the wrong items). Under k reflex substeps, the
  injected clock advances exactly by the stepped dts (foundations Wire S1).

### 7.4 Thought cost: the interfaces only (O4)

- **A thought request** carries `kind` (from the closed vocabulary of `data/agents/timing.yaml`, chosen before the
  call and never changed by a result), the modelled times, `cancel_on`, and its budget.
- **A thought result** arrives as `Reply` values: the host reads the reply's speech field
  first, validates it (per chunk once streaming lands, OD-A25), and stamps syllables in integer world microseconds below the tick, interruptible. Segment times are computed by the host from the cost model, never parsed from model output
  (foundations TB2-S5).
- **The host's `latency_policy`** is a host-only control; its policies, with DLP-B2's fixes, are `npcs_and_sem.md`
  §4.4's (foundations Arch B2, TB2-B3).
- **The tick size** is decided in sim-clock, with `apply_us` already in the record.
- Phases, budgets, the cache, fatigue and every constant belong to part 2.

## 8. Maxim, content and experiments

### 8.1 Maxim through named adapters (B-2, rewritten; BF-3, X N-1)

- **Rule:** Maxim is imported only by named adapters, each declaring the Maxim surface it uses.

| Adapter | Package | Surface |
|---|---|---|
| SEM membrane | `engine.adapters.sem` | bodies, percepts, acts (`Entity`, `Modulator`, `SensorReading`, `ModulatorResult`, `AffordanceSchema`) |
| Agent stepping | `engine.adapters.agents` | host-called `step`, `think` and `settle`, the request/reply values (model calls run by the host, never injected into Maxim), the worker process, the tool-roster check, the per-agent home, clock and RNG injection, the experience driver, agent-state save (foundations Arch B3, DR-B2) |
| Inference gateways | `engine.adapters.inference` | backends and types of `maxim.models.language`, never calling `LLMRouter` (`inference_gateway.md` §1) |
| NPC authoring | game, when it exists | `AgentFactory`, seed memory, the arc loader |
| Experiment harness | Maxim-owned (`npcs_and_sem.md` §10) | the experiment and ledger tooling |

- **Enforced** by import-linter's `protected` contract on `maxim` (allowed importers listed; verified on 2.15 without
  pymaxim installed; the gate pins 2.6, `constraints/py3.12.txt`), plus a lint comparing each adapter's imported
  symbols against its declared list.
- **As built,** `maxim-through-adapters` allows `simcore.adapters.sem` alone. Each adapter joins `allowed_importers`
  by name, with its test, when it is built: the worker module (`sem_stimuli.md` §7.3) and `engine.adapters.inference`
  (`inference_gateway.md` §1). Once the adapter is split, the host imports Maxim's types only through
  `simcore/adapters/sem/_compat.py`, and `maxim` itself only in workers and inference gateways (`npcs_and_sem.md`
  §6.6).
- **New root packages are not covered automatically** (foundations X-12, verified): grimp builds no graph for a root
  not listed in `root_packages`, so an unlisted `game` importing `maxim` passed. A test asserts `root_packages` equals
  the set of top-level packages under `src/`.
- **Behaviour, not only shape (BF-10).** A behavioural contract test runs a real `ModulatorAffordanceTool` (and the
  actor tool) against the membrane and asserts what Maxim does with the result: the valence booked for applied,
  refused and pending results; what the cerebellum is trained on; which side-effect keys are promoted. The membrane's
  metadata keys are reserved (OD-C6: `tool_bridge` merges `**result.metadata` after `"success": True`, so a key named
  `success` overwrites the outcome).
  It runs against real Maxim as a strict red gate from `phase1/agents`, and turns green with tier A.
- **Proposal ids are roadmap Phase 3's `OD-` ids,** Overdrive-scoped so they can't collide with Maxim's own; its
  "Was" column maps the old A, B, C, P and SEM-plan numbers. v2's old ids are replaced throughout (foundations Wire
  S10, MP-S9).

### 8.2 Content and licence (B-5; S9, X S-9, TB-S8)

Code: Apache-2.0 (`LICENSE`). Story, characters, lore, art and audio: all rights reserved (`ASSETS_LICENSE.md`).

| `data/` file | Owner | Licence |
|---|---|---|
| `rigs/*.yaml` | engine (`engine.tiers`, rendering) | Apache-2.0 |
| material physical columns | engine | Apache-2.0 |
| material calibrations (`fracture_energy_*`, `degrade_*`, combustion tuning) | game, under `content/` | rights reserved |
| `color_rgb` | presentation (`engine.tiers`/`encoding`) | Apache-2.0 |
| `world/actions.yaml` (physics-safety ceilings) | engine | Apache-2.0 |
| the SEM vocabulary and default affordance descriptions | engine | Apache-2.0 |

- **No default path into data from the core** (§3). Engine tests use Apache fixture tables under `tests/fixtures/`.
- **The wheel:** the engine distribution excludes `content/`. Game content ships in a second distribution with its
  own licence when it exists. A check lists each wheel's files against B8's manifest.
- **The material split** gives the engine file and the content file disjoint, closed key sets, and the merge refuses
  an override, so content (later, mods) can never set a physical property.
- **The shipped values stay under the resolution gate (foundations Arch S12).** Calibrations decide outcome classes
  (breach, ignition, burn-out), so moving them to content must not take them out of the cross-tier and closed-form
  tests. The game's gate runs `engine.verify`'s cross-tier suite over its own content tables, as a required check born
  with the content file in material table v1. A retune that puts a value inside a band where profiles disagree goes
  red in the game's gate, not in the lab.

### 8.3 Presentation (B-6)

Display quantization (`client_rendering.md` §4.2, `client_objects.md` §3) moves to `engine.encoding` in the
protocol PR.
The core is forbidden from importing it; `engine.adapters.sem` is too (§2.2).

### 8.4 Experiments (B-7; S10, BF-9)

- The experiment harness is Maxim-owned; what it imports and what a ledger record pins are `npcs_and_sem.md` §10's.
- Experiments that need game content are game runs, which stay off Maxim's ledger.
- Decided now, because the Exp 64 draft freezes at the Phase 3 exit and will name these paths.

## 9. Protocol, tests and SEM refinement

### 9.1 One protocol schema (B-11; S7, TB-S4)

- **The in-code field registry is primary** (world_model §8). It generates the schema as a committed artifact; a
  golden test regenerates it and compares bytes.
- **The schema is shape plus closed vocabulary,** not validation. Stage 1 stays the only server validator; limits
  reach the client in the handshake for its UI only.
- **A strict JSON decoder** sits in front: `parse_constant` raises (no `NaN`/`Infinity`), `object_pairs_hook`
  refuses repeated keys, `max_size` applies before decoding. Integers are pinned below 2⁵³ (O59). The server's JSON
  holds integers only (O62): a reader judges a message's version first, a float there being `bad_version`, then any
  other float, anywhere, `not_int`. The client reads it with its own strict parser; wire text never holds
  U+0000 (O67).
- **Golden rejection frames** and grammar edges are judged alike, code and value
  (floats by class, O68).

### 9.2 Tests out of the shipped path (B-12)

The external half only: the engine is forbidden from importing `pytest` and `hypothesis`. `tests` and `scripts`
aren't packages in the import graph, so that half couldn't fail (Arch N5) and is dropped.

### 9.3 SEM refinement items (O5; foundations Arch S8, Wire S10, Wire S11, X-5, X-13, MP-B3)

Ids are roadmap Phase 3's `OD-` ids (its "Was" column maps the old A, B, C and SEM-plan S-ids). The additive-first
policy under CC3 is roadmap Phase 3's ("Ids").

The items are roadmap Phase 3's rows OD-A1–OD-A12, OD-A14–OD-A18 (OD-A13 moved to OD-I3), OD-B12, OD-C1–OD-C10 and
OD-I1–OD-I5; each row's content and path are the roadmap's.

## 10. Enforcement

| Boundary | Check | Lands |
|---|---|---|
| B-1 engine/game/experiments | import-linter forbidden contracts | `phase1/boundaries` |
| B-2 Maxim adapters | `protected` contract on `maxim`; a test that `root_packages` equals the packages under `src/`; declared-surface lint; behavioural contract test | boundaries; the behavioural test (a strict red gate against real Maxim) with `phase1/agents` |
| B-3 sealed core | forbidden contract (one shared banned list); extended AST scan; writer non-vacuity test; profile-hook tripwire over the corpus | boundaries; tripwire with sim-clock |
| B-3 agent step path | the same banned list and scan over `engine.adapters.agents` minus its host-only module; tripwire on the agent lane | `phase1/agents` |
| NPC tool roster and homes | roster allowlist check with a planted `BashTool`; per-NPC home test; one real agent per process | `phase1/agents` |
| Agent barrier | a test where a slow agent at 20× must not see a later frame than at 1×; park and release meters | `phase1/lanes` |
| Rendering never reaches truth | forbidden contract: core ↛ `engine.tiers` | boundaries |
| Skip-layer rule | forbidden contract: adapters, protocol, host ↛ cells, laws, geometry, scene build | boundaries |
| B-4 untrusted input | input-primitive allowlist (import-linter + AST lint); banned unsafe calls; gate registry with per-gate branch coverage | boundaries |
| B-5 content | directory rule; disjoint material key sets; wheel manifest check | material table v1 |
| B-6 presentation | forbidden: core and `adapters.sem` ↛ `encoding` | the protocol PR |
| B-7 experiments | forbidden: engine and game ↛ `maxim_experiments`; harness ↛ game | the first experiment |
| B-8 layers | import-linter layers contract, committed order | boundaries |
| B-9 one pipeline | the ownership window (§4.1, with the unlock-then-close proof); record golden fixtures; ordering test; replay with `maxim` blocked and the cache deleted | gates (window); sim-clock (log) |
| B-10 observation | frame tests (§4.2); `Observation` protocol under mypy | boundaries |
| B-11 one schema | regenerate-and-compare; golden valid and rejection frames on both sides | the protocol PR |
| B-12 tests out | forbidden: engine ↛ `pytest`, `hypothesis` | boundaries |
| B-13 physical percepts | import half: `adapters.sem` reads frames and the registry only | boundaries; perceiver half Phase 4 |

**Running import-linter (X-1, W3, W8, X S-6):**
- **As built in 3a (2026-11-19):** import-linter 2.6 and grimp 3.13 (pymaxim caps `rich<14`), called as
  `lint_imports_command()` with `PYTHONPATH="$PWD/src"` (`-m importlinter.cli` checks nothing). The game package
  exists from 3a, holding only `data.py`, against §2.1; the core's banned list is §3's.
- **As built in 3b(a) (2026-11-20):** a frame holds the read-only owners, which no window writes in place, so it
  needs no copy, but it pins a whole grid (about 100 MB at 5×10⁶ cells; one pinned per agent is a B5
  row). Stamped by sequence and `time_s` until the tick. A cell window copies all four channels
  twice in every build, even unchanged (O8's switch can't reach the core); a sources-only window
  copies none but still publishes. The window's owners are §4.1's. The
  membrane gets an applier and a frame view, never the world: that is the guard; the peek and re-export scans are
  tripwires. Skip-layer covers `encoding`. The registry adds
  `no input` and `partial`. `Budget` values are engine defaults (O23).
- A tooling test asserts grimp resolves each root package under this repo's `src/`.
- `.import_linter_cache/` goes in `.gitignore` (or `--no-cache`), so the gate doesn't dirty the tree.
- `importlinter` joins the preflight import line in `prepush.sh`.
- Each contract entry is proven by a planted import, including stdlib targets (`include_external_packages`) and
  modules that don't exist yet, whose entry is proven when the module is born.
- The CLAUDE.md rule's guard names the gate step (`scripts/prepush.sh::lint-imports`) and a config test, not
  `pyproject.toml`, where a word match would survive every contract being deleted.

## 11. Migration

### 11.1 Two PRs, before `phase1/verify` (S12)

In world_model §10's order, after #2 (designs accepted) and before #3 (`phase1/verify`), so the verification
harness is born in `engine.verify`:

- **2b `phase1/boundaries`: structure.**
  - Rename and re-home by layer (§2.2), not by sed: `checks`, `materials`, `geometry`, `cells`, `laws`, `scene`,
    `intents`, `imagination`, `sim`, `loaders`, `tiers`, `adapters.sem`.
  - Split `config` (truth vs `tiers` vs loaders); remove data defaults (`materials=`, `limits=` required).
  - Move `parse_action`, the typed actions and `ActionLimits` into `engine.intents`.
  - Split `StructureModulator`: gate half in `adapters.sem`, write half into `sim` as the applier (with the reach and
    centroid checks as stage-2 checks), with its TEMPORARY marker scheduled for `phase1/agents` and its roadmap row
    (§6.4).
  - The contracts, the import-linter wiring and the tooling tests (§10).
- **2c `phase1/gates`: behaviour, limited to what has a caller then (foundations Arch S5, Wire B1).**
  - The ownership write window, owned by `World.advance` and the applier under TEMPORARY markers scheduled for
    `phase1/sim-clock`
    (§4.1); frames published after each application and each advance, as copies; sensors on frames; instruments
    relabelled; `cell_size_m` dropped (§4.2, §4.4).
  - Validating constructors (§5.1); the gate contract and registry (§5.2, §5.4); budgets and bounded echo.
  - **Not in 2c:** `observed_tick` on intents and the integer tick (sim-clock); the cross-thread frame test (lanes).
- **The agent foundations, `phase1/agents`** (a new row in world_model §10, after sim-clock and before lanes): the
  `AgentPort` (`step`, `think`, `settle`), `StepOutput`, `Pending`, `Reply`, the continuation blob, receipts and settle, thought request types, the
  `data/agents/` files and their gates, the per-NPC streams, the tool-roster and home checks, the agent-step-path
  seal, the scripted test double, and real Maxim as a strict red gate. It removes the TEMPORARY marker
  scheduled for it. The barrier's concurrency and the meters arrive with `phase1/lanes`; the thinking lane and the worker processes with `phase1/agents` (npcs §6.2).

### 11.2 What the rename must get right (W2, W5–W7, W10–W14)

- **Coverage measures by directory:** `source = ["src", "scripts"]`. The tooling test derives its expectation from
  `src/`, and a test fails if any package under `src/` is unmeasured. Planted proof: an untested module goes red
  (W2, X S-5).
- **The determinism scan walks every package under `src/`** minus an explicit, package-qualified non-simulation
  list (W14), with a non-vacuity floor: the files defining `Simulation.step` and the applier must be among those
  scanned, and the count must be at least a stated floor (D-S6).
- **The `_data` mapping** is tested: the `force-include` target equals the package holding the loaders, and
  `data_dir()` refuses loudly when neither location exists (W5).
- **`MAXIM_OVERDRIVE_ALL_TIERS` keeps its name,** with a test that `prepush.sh` exports the name `conftest.py` reads
  (W6).
- **Docs:** README's quick start, `docs/code_review.md`, CLAUDE.md (Layout, Commands, the SEM rule's paths, the new
  rule) and `docs/architecture.md` are updated by hand. When the agent foundations land, CLAUDE.md's determinism
  rule ("one seeded `numpy.random.Generator` owned by `World`") becomes "the World's generator plus keyed per-NPC
  streams from one run seed", `tests/test_determinism.py::NUMPY_RANDOM_ALLOWED` admits `Philox`, and the replay
  sentence is scoped to the world (§6.2) (foundations Wire S3, DR-S7, BF2-15). `docs/design/reviews/` and
  `docs/design/research/` are kept
  verbatim and excluded (W7, W11).
- **Wire-visible strings are decided, not sed'd:** the entity metadata `source` becomes a fixed vocabulary value
  (`"overdrive_world"`), pinned by a test (W10, X N-2). `__version__` moves to the engine; the distribution name
  stays `maxim-overdrive`; its description is updated (W13).
- `git clean -fdX src/` after the move, so stale `__pycache__` doesn't make old paths importable (W12).

### 11.3 Merge order (W9, W1)

- `main` is still the initial commit. Proposed order: PR 1 (`phase1/act-validation`) → `phase1/standards` →
  `phase1/design-v2` → `phase1/realtime-design` (docs, superseded in parts) → `phase1/boundaries` →
  `phase1/gates`.
- `phase1/transport` and `foundations/world-server-v0` are proposed abandoned; their useful parts are redone in the
  protocol and lanes PRs (Q3).
- Any branch that survives the rename checks after rebasing that `git diff --name-status` against its pre-rebase tip
  shows no file added under the old path. With no game package, git stops with a conflict instead (W1).

## 12. Open questions for the owner (all answered as recommended: O23, 2026-11-17)

1. **The engine's package name.** A Maxim-neutral name is recommended (`engine` is a working placeholder).
2. **Two PRs (structure, then behaviour) or one.** Two is recommended: the rename touches about 70 references in 25
   files, and reviewing it apart from new behaviour keeps both reviewable.
3. **Abandoning `phase1/transport` and `foundations/world-server-v0`.**
4. **Imagination budgets:** the mechanism is engine; per-actor budget values are game data, loaded through a gate.
5. **Frame cadence:** frames publish on change (after each physics step and each tick that applied an intent), not per
   tick (§4.2). Accept that, or pay the per-tick copy cost for finer percepts?

## 13. What this design does not settle

- **Real NPCs wait for Maxim's embeddable agent contract** (O6). Until it ships, real Maxim behind the adapter is a
  strict red gate, and every agent test runs on the scripted test double.
- **Stale refusals** are closed for v1 (§7.2); OD-A16 still carries `call_error` and `wrong_target`. Roadmap Phase 3's exit now requires OD-A16 before Phase 4 (`npcs_and_sem.md` §12.1 asks the owner to confirm).
- **Slow-effect credit** stays OPEN until settle carries a horizon (OD-A16).
- **Memory writes** are ungated until generate vs apply (OD-A18) and the host's `settle`; memory authority is OPEN until per-agent homes and
  pickle-free persistence land.
- **Two clocks into Maxim** stay an OPEN divergence until OD-C2 and OD-A2 (§7.3).
- **The game's rule seam is data only** (§2.1); a game that needs a new mechanism brings it to the engine.
- **BLAS in the core** is forbidden rather than policed; the first solver that needs it reopens this (§3).
- **The perceiver half of B-13** waits for the first NPC body (Phase 4).

## Review records

This document's fold tables are kept with their reviews: `reviews/boundaries/fold.md`, `reviews/foundations_v1/fold_boundaries.md`.
