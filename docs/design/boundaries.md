# Boundaries between engine, game, Maxim and the outside world (design v2, 2026-11-16)

**Status:** DRAFT v2, for a delta design review before any code. v1 (47add00) went to a six-lens review
(`docs/design/reviews/boundaries/`: 18 BLOCKER, 52 SHOULD-FIX, 29 NIT). This version folds every BLOCKER and
SHOULD-FIX, and the owner's decisions of 2026-11-16 (§0). The fold table at the end maps each finding to where it
landed, or says why it was deferred.

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

| # | Decision |
|---|---|
| O1 | One repository, with an enforced engine/game boundary and a written split trigger. |
| O2 | **The action result contract:** (a) now, (b) later. (a): the Maxim adapter's `execute` submits an intent through the one pipeline and waits *in world time* for its receipt and the next published frame, then reports the applied outcome. (b): return `neutral` immediately and settle later, once Maxim can credit late effects (P3). The foundation (propose and settle, receipts, ids) is laid now, so (a) → (b) is an adapter change, not an engine refactor. |
| O3 | **The agent substrate** runs outside the sealed core, behind an engine-defined `AgentPort` in integer ticks: frozen frames in, logged intents out, with real Maxim. It moves inline when Maxim ships an injected clock and deterministic external stepping. |
| O4 | **Three clocks** (world, body, perceived). No time field reaches cognition. Thought cost is modelled in world time and phased; the world slows (reported dilation, by cause) when real thoughts run late. Abandoning late thoughts is an explicit, logged host policy. Thinking couples to the fatigue drive and sleep pressure, not hunger. Details are part 2's (`npcs_and_sem.md`); this design carries only the interfaces and fields. |
| O5 | **Refining Maxim's SEM is in scope and a priority** of the foundations work, through Maxim's own process. Each SEM-touching item here says whether it is additive now or batched into one SEM breaking-change plan (§9.3). |

## 1. Why now, and what the code is today

Each boundary costs a few renames now, and a refactor across the protocol, zones, fuel and the lab later.

Surveyed on `phase1/act-validation` at 2f200b5 (Executor confirmed each item):
- `src/maxim_overdrive/` has `checks.py`, `config.py`, `world/` (grid, scene, heat, damage, world), `imagination/`
  (spec) and `sem_env/` (bridge, `_compat`), plus a root `__init__` that re-exports config, grid, scene and world.
- Only `sem_env/bridge.py` imports `maxim`.
- No module imports `time`, `random`, `datetime`, `uuid`, `os`, `importlib` or `__import__`. **But** the core does
  reach `pathlib` and `yaml` (`config.py`, file IO on every `World.from_scene` without a table) and `scipy`
  (`damage.py`: `ndimage`, `special.ndtr`). Those bear on determinism (D-N1, D-B2).
- The code that writes the world on the shipped path lives outside `world/`: `bridge.StructureModulator._strike`
  (through `damage.strike`), `_ignite` and `apply` (which set and pop `World.sources`), and `imagination.spec.place`
  (D-B1).
- Several "typed, frozen" objects are neither deeply frozen nor validated: `Region.cells` is a writable mask in a
  frozen dataclass; `MaterialTable` is mutable with public arrays; `RigProfile`, `Material` and `Budget` construct
  invalid values (TB-B2).
- `data/` holds rigs, the material table (physical properties mixed with calibrations the file itself labels
  "GAMEPLAY CALIBRATION"), and action limits.

## 2. Packages and layers

### 2.1 The packages (B-1)

- **Rule:** the engine never imports the game or the experiments. The game may import the engine. Experiments
  import only the engine and their own Apache-2.0 fixtures.
- **The engine's name** is open (Q1). Below it is written `engine`, a working name. The reviews recommend a
  Maxim-neutral name, since B-2 says Maxim is swappable and `maxim_*` reads as Maxim's own namespace (Arch N3).
- **The game package `maxim_overdrive`** is created with the first game content (the lab, `phase1/lab`), not before
  (W1, W4). An empty package now would silently collect new modules from rebased branches.
- **The experiments package** `maxim_experiments` is the harness for Maxim's pre-registered experiments (S10). It
  is distinct from the engine's verification harness (`engine.verify`).

| What | Where |
|---|---|
| Cells, geometry, laws, the simulation, intents, formats, the protocol, the SEM membrane and agent adapter, the host, the verification harness | engine |
| Body grammar and receptor models (physiology is mechanism) | engine (BF-15) |
| This game's content and rules: the lab tile, its scenes, story, NPC rosters and body instances, cradle arcs, calibrations, tuning | game |
| Pre-registered Maxim experiments | `maxim_experiments` (§8.4) |
| Godot: the frame decoder and channel bindings | `client/addons/engine/` (S8) |
| Godot: scenes, art, game UI | `client/game/` |

- **Split trigger (S8):** split into two repositories when an outside consumer wants the engine (a second game, an
  outside developer), or when measured: over the last 20 merged PRs, at least 15 touched only engine paths. No date
  trigger. Phase 2 changes engine and game together, and a split then would double every feature's PRs.

### 2.2 Layers inside the engine (B-8)

The rename re-homes modules by layer, so the package cut and the layer cut agree (S5). A layer imports only layers
below it. Siblings on one line are independent of each other.

| Layer | Modules | Notes |
|---|---|---|
| 0 | `engine.checks` | validation primitives, bounded echo (`shown`, moved from the bridge, TB-S3) |
| 1 | `engine.materials` | `Material`, `MaterialTable` types and the truth constants. No IO, no rig. |
| 2 | `engine.geometry` | primitives, CSG and footprints in metres; no cells (S5) |
| 3 | `engine.cells` | the grid, regions, ownership arrays, the write window (§4.1) |
| 4 | `engine.laws` | heat, damage; later zones, gas, fuel |
| 5 | `engine.scene` &#124; `engine.intents` &#124; `engine.imagination` | scene type and build; the action vocabulary, typed intents, `ActionLimits`, stage-1 parsing, the intent record and receipts (S3); imagined-object specs |
| 6 | `engine.sim` | `World`, `Simulation`, the integer clock, the intent applier, the frame publisher, the `AgentPort` protocol |
| 7 | `engine.loaders` &#124; `engine.encoding` &#124; `engine.protocol` &#124; `engine.adapters.sem` &#124; `engine.adapters.agents` &#124; `engine.tiers` | file gates; display quantization (B-6); wire decode and encode; the Maxim membrane; the Maxim agent stepping adapter; `RigProfile` as a rendering tier |
| 8 | `engine.host` &#124; `engine.verify` | pacing loop, lanes, sessions, `TimeAuthority`, dilation measurement, log writer; the verification harness (S12) |

- **Layers 0–6 are the sealed core** (§3).
- **The written order is the order committed,** checked red-first on today's code (X S-2, Arch N1). Today `config`
  imports `checks`, so `checks` sits below `materials`. `imagination.spec` imports `world.scene` for its primitives;
  after the move it takes them from `engine.geometry` (layer 2), so `imagination` and `scene` can be independent
  siblings. If that move isn't clean, `imagination` gets its own layer above `scene`, never the non-independent `:`
  form, which lets upward imports through unreported.
- **Skip-layer rules (S2).** Layers allow skipping, so a further forbidden contract applies: `engine.adapters.*`,
  `engine.protocol` and `engine.host` import only `engine.sim`'s public surface, `engine.intents` and
  `engine.materials` types. Never `engine.cells`, `engine.laws`, `engine.geometry` internals or `engine.scene` build
  functions. `World.sources` becomes private behind an intent.
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
- **Agents are not in the core** (O3, BF-2). The core defines `AgentPort` (§7.1) and never imports `maxim`. Real
  Maxim runs in the agent lane through `engine.adapters.agents`.
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
  - `maxim` (also held by B-2's protected contract).
  - **Explicitly allowed:** `hashlib`, `math`, `dataclasses`, `enum`, `typing`, `numpy`, `scipy`, `logging`
    (output only).
- **What imports can't show** is held by the AST scan, extended (D-S3, X S-1): `__import__`, `exec`, `eval`, `open(`,
  `id(`, `getenv`/`environ`, iteration over a `set`/`frozenset`, `sorted`/`np.sort`/`np.argsort` without
  `kind="stable"` on non-unique keys, `np.seterr`/`errstate`, BLAS calls (`@`, `dot`, `linalg`, `einsum`). **BLAS is
  forbidden in the core** for now. None exists today; the first solver that needs it brings a threads-pinned policy
  (`threadpoolctl`, 1 thread) to review.
- **The tripwire is a test, not a runtime seal (D-S1, D-N3).** It runs over the golden replay corpus, on the
  simulation thread, with an explicit denylist (`time.*` clocks, `datetime.now/utcnow/today`, `date.today`,
  `os.urandom/getrandom/getpid/environ`, `uuid1/4`, `secrets.*`, `SystemRandom`, `threading.get_ident`,
  `Random.seed(a=None)` detected from the frame, `SeedSequence()` with no entropy), each proven by one planted call.
  It guards only what the corpus exercises, and it ships with sim-clock.
- **Dilation is measured in the host** and enters the `Simulation` only as recorded data (Arch N7), so nobody
  exempts the core to measure it.
- **This guards mistakes, not adversaries.** ctypes and buffer tricks stay possible (D-B4).

## 4. Writes and observation

### 4.1 One write window (the guard for both writes and observation)

- **Every array the core owns is read-only at the owner** (`writeable=False` on the owning array, so a view can't
  re-enable it). This includes the grid's channels, region masks and `MaterialTable`'s arrays (always read-only after
  construction; nothing writes them).
- **One write context,** `with cells.writing():`, is entered only by:
  - `Simulation.step` (the laws during advance, and the intent applier);
  - construction (`Scene.build`, the save loader), named as the third writer (S11, S-7).
- `regions` and `sources` are `MappingProxyType`. `sources` changes only through the applier.
- **What this buys:** "every write happens under advance or intent application" stops being a test that sees only
  exercised paths (TB-S7) and becomes "a write anywhere else raises". The golden scenario runs with the window
  closed outside `step`. It replaces v1's view flags, which guarded copies (X-3) and could be switched back on
  (D-B4). Heat's in-place updates run inside the window, so they are unaffected.
- **Proof tests (D-B4):** for every outward surface, each of direct write, `flags.writeable = True` then write, write
  through `.base`, ufunc `out=`, and attribute assignment must raise.

### 4.2 Observation reads published frames (B-10, rewritten)

- **Rule:** percepts and instruments are immutable samples of one published frame. After each step the simulation
  publishes a frozen frame (copies or read-only owners), stamped with its tick. Nothing outside the simulation lane
  holds a reference to `World`, the grid or `MaterialTable` (S6, BF-4, D-S5, X-3).
- **Sensors type against a `Frame`/`Observation` protocol** with no `advance`, `sources` or `grid`, so mypy refuses
  a peek (D-B4). `RegionSensor` stops holding `World`.
- **Every intent records `observed_tick`,** the frame its decision was based on (D-S5).
- **Observation never draws from the World's generator.** Percept noise uses the per-NPC stream (§7.3) (D-S5).
- `world.snapshot()` already copies. Its only change is B-6's move to `engine.encoding` (Arch N6).
- **Tests:** a reading taken at tick T is unchanged after `advance`; a sensor holds no `World` reference; a read from
  a second thread mid-step returns the frame for T−1, never a mix.

### 4.3 Pushing percepts into bodies (BF-5)

- Maxim bodies perceive by push: the world writes measured values into `vital_metrics` through `world_set_axis` with
  `live_world_set_sensors` declaring the world the single writer.
- **This is a sanctioned mutation of agent state,** done by `engine.adapters.agents` in the agent lane, as a pure
  function of a published frame (so it needs no log record).
- **Every body sensor the world simulates is world-owned.** A modeled `self_effect` is allowed only on sensors the
  world doesn't simulate, and each one is listed as an ANALOG divergence. Otherwise an NPC is burned twice, by the
  YAML delta and by physics.
- Per-part sensors (`arms.thermal`) need P4, since `world_set_axis` is root-only today.

### 4.4 B-13 (new): percepts come only through physical channels at the perceiver (BF-7)

- **Rule:** a percept is a reduction of registered physical channels, evaluated at the perceiver's position and
  receptor, with a line-of-sight gate once light exists. The membrane reads the world only through frames and the
  field registry.
- **Today's region sensors are instruments,** relabelled as such (an ANALOG divergence): usable by tests and the
  lab's instruments, not as an NPC's senses.
- **Lands:** the import half in `phase1/boundaries`; the perceiver half with the first NPC body (Phase 4).

## 5. Untrusted input (B-4, rewritten)

### 5.1 Validation lives in constructors; frozen means deep

- **Rule:** a type's constructor validates. A gate is the decoder that turns bytes (or a Maxim call) into
  constructor calls, and holding an instance is proof it is valid (TB-B2, TB-N3). "Past a gate", not "inside" one
  (TB-N1).
- **Frozen means deep:** tuples, `frozenset`, `MappingProxyType`, and numpy arrays read-only at the owner (§4.1).
- **Violations today, and when each is fixed:**

| Type | Problem | Fixed in |
|---|---|---|
| `Region.cells` | writable mask inside a frozen dataclass | `phase1/boundaries` (§4.1) |
| `MaterialTable` | mutable class, public writable arrays, no sign checks | read-only arrays and validation: `phase1/boundaries`; the strict v1 format: material table v1 |
| `Material` | no validation (`density_kg_m3=0` divides by zero) | `phase1/boundaries` |
| `RigProfile` | builds `min_substeps_per_turn=1.5`, `full_res_radius_m=-3` | `phase1/boundaries` (and it leaves physics, §2.2) |
| `Budget` | builds `max_mass_kg=nan`, removing the mass limit | `phase1/boundaries` |

- **`World` and the grid are the sink,** mutable by design inside the write window, not "objects past a gate".
- **Maxim's own types are a named exception:** `ModulatorResult` (`params`, `metadata`) and `SensorReading`
  (`extra`) are frozen dataclasses holding plain dicts. The membrane only builds them outbound; it never trusts one
  inbound. Deep freezing is a candidate for the SEM breaking-change plan (§9.3).

### 5.2 Guard the sources, not the signatures

- **Input primitives are allowlisted by module (TB-B1, B2, X-2).** Only gate modules may call `yaml.*load*`,
  `json.load(s)`, `Path.read_*`, `open`, `np.load`, `os.environ`/`getenv`, `sys.argv`, or a transport receive. Held
  by an import-linter forbidden contract on `yaml` and `json` outside the gate modules, plus the AST lint in
  `scripts/lint_standards.py` for the calls.
- **Banned everywhere:** `pickle`, `marshal`, `yaml.load` without a `SafeLoader` subclass,
  `np.load(allow_pickle=True)`, `eval`, `exec`.
- **A gate registry** in `lint_standards.py`: gate name → kind (authentication, authorization, validation) → its
  rejection-path test module → status (meets the contract, or gate-to-be with its row). Each gate module is measured
  at 100% branch coverage. The lint checks that every public callable reachable from an outside entry point (the
  Maxim calls, the loaders, the protocol) is registered.
- **Proof:** plant a `json.loads` in a non-gate module, and a public entry with no registry row; both go red.
- v1's annotation rule is dropped. It missed `execute(params: dict[str, Any])` and every path-taking loader, and
  flagged four non-gates (X S-4).

### 5.3 The gates (TB-S1)

| Input | Source | Authentication | Authorization | Validation (gate) | Lands |
|---|---|---|---|---|---|
| NPC tool calls | Maxim (`ModulatorAffordanceTool`) | the agent lane's request id | per-kind authority (§6.1) | `engine.adapters.sem.StructureModulator.execute` (X-2), with `engine.intents.parse_action` as stage 1 | today; moves in `phase1/boundaries` |
| `target=<Entity>` and other Maxim objects | Maxim's actor tool | — | — | resolved to a stable id at `execute`, namesake and identity checks before the intent is frozen (TB-S5) | `phase1/boundaries` |
| Imagined objects | LLM via Maxim | request id | the actor's budget | `imagine` intent: spec constructors at stage 1, `place` as stage 2 (TB-S6) | `phase1/boundaries` (kind), sim-clock (log) |
| Thought results: intents and **memory writes** | agent lane | request id | an NPC's own memory only | the stage-1 validators; memory writes validated by Maxim through item 16's apply step, the game checking shape and size (BF-13) | `phase1/lanes` |
| Scene files, saves, intent logs, bug reports | disk, **strangers' machines** | — | — | the strictest gate (world_model F14): no pickle, budget before allocation, all-or-nothing | scene v1, save v0, sim-clock |
| Rigs, materials, limits, vocabulary, presets, rosters, arcs | `data/`, `content/`, later mods | — | — | a loader each under the gate contract (§5.4) | today and as each lands |
| Handshake, per-launch token, `Origin` | network lane | `hmac.compare_digest`, `Origin` refused, loopback bind (lanes §5) | — | the protocol decoder | `phase1/protocol` |
| Joins and leaves | network lane | session token | — | session to actor id allocation (lanes §4.2) | `phase1/protocol` |
| Controls: dial, pause, presets | host session | session token | `TimeAuthority` / `HostOnly` (lanes §5) | the protocol decoder | `phase1/protocol` |
| Client frames (intents) | network lane | session token | per kind | strict JSON decoder (§10), then stage 1 | `phase1/protocol` |
| Snapshot frames, as the client receives them | server | — | — | the client-side decoder (defence in depth; never crashes on a bad frame) | `phase1/protocol` |
| Token delivery | env var or a 0600 file | — | — | a host config reader; never echoed or logged. The host owns `os` and `secrets` | `phase1/protocol` |
| `MAXIM_OVERDRIVE_*` env vars, the rig CLI flag | operator | — | — | a host config reader; the rig name from a closed set | `phase1/boundaries` |

**Two validation stages** (world_v2 §7): stage 1 is typed parsing in `engine.intents` (shape, finiteness, ceilings);
stage 2 is the world check at apply, in the applier (target exists, not stale, budget).

### 5.4 The gate contract (TB-S2, TB-S3, X S-3)

Every registered gate meets all of these, with a rejection test each:
- one strict loader (repeated keys refused, as `_StrictLoader` does);
- a version field, unknown versions refused loudly;
- a closed key set (a typo is an error, not a silent default);
- one exception type (`ValueError` or a subclass), never `KeyError`/`TypeError` escaping;
- bounded echo through `engine.checks.shown`;
- budgets checked **before allocation**: counts (primitives per spec), string lengths (names), nesting depth, total
  allocation (cells × primitives). `place` today stacks one mask per primitive before refusing anything: 1,000
  one-centimetre primitives cost about 5 GB at the max profile.

Only `ActionLimits.load` and `parse_action` meet the bar today, and `place` partly. `RigProfile.load`,
`MaterialTable.load` and `Scene.from_dict` are registered as gates-to-be and hardened in `phase1/boundaries`
(TB-S2, X S-3). `checks.py`'s docstring claim is corrected with them (TB-N2).

## 6. One pipeline for every input (B-9, rewritten)

### 6.1 Three rules (TB-B3)

1. **One pipeline.** Every record from any source goes: decode → stage-1 validation → log → stage-2 validation
   against the world at apply. NPC and player intents share the validators and the log.
2. **Authority per record kind,** from an actor role the host stamps:

| Kind | Who may emit it |
|---|---|
| `intent` (strike, ignite, douse, …) | any actor |
| `imagine` | any actor, within its budget |
| `control` (dial, pause, presets) | host sessions only, through `TimeAuthority`. **NPCs can never emit it.** |
| `memory_write` | an NPC, to its own memory only |
| `join` / `leave` | the network lane |
| host commands: advance (in ticks), rig selection, save, load, admin `set_material` | the host |

3. **Limits are the shared physics-safety ceiling intersected with the actor's capability.** `ActionLimits` stays
   the ceiling (and a refusal, never a clamp); capability comes from the body and, later, energy (Phase 5).

- **Identity is stamped from the channel, never read from the payload:** a client's session token maps to its actor
  id; an NPC's request id is `(tick, actor, n)` from the agent lane. A guest sending `"actor": 0` changes nothing.
- The "fairness" argument is a game-design goal and no longer part of the trust rationale (TB-N4). Asymmetries are
  explicit in the table above.

### 6.2 The log record (D-B3, D-S7, D-S8, D-S9)

- **The log holds every input** to the `Simulation`, not only actor intents: every kind in §6.1, including refused
  intents (a refusal at apply depends on world state) and host commands. `advance` takes ticks, never wall-derived
  seconds.
- **An intent record** is frozen and versioned, with golden fixtures for its format:
  - `schema_version`, `kind`, `actor_id`, `seq` (per actor);
  - `observed_tick`, `issued_tick`, `apply_tick`;
  - `params`: the **typed canonical** form after stage 1, so later gate tightening doesn't change old replays; the
    raw payload is an optional audit field only;
  - `target`: a **stable id** (a region name or persisted entity id), resolved at the door. Nothing identity-based
    crosses into the log.
- **Derived, never input:** receipts, refusal reasons, destroyed volume, `ModulatorResult`s. Replay recomputes them
  and checks them against a per-tick digest.
- **An NPC's thought is never a log input.** Prompts, LLM text and tool-call text stay out. The only thing a thought
  contributes is the intent it produced, and that is logged.
- **Same-tick order is canonical:** `(apply_tick, actor_id, seq)`, never arrival. Float accumulations over named
  collections (today `World._power_field` over `sources`) iterate in sorted-key order. Ordering keys are integers
  (D-N2).
- **Replay calls nothing live:** no model, no Maxim, no clock. Tested by replaying with `maxim` blocked from import.

### 6.3 The log header (D-B2, D-S4)

- Content digests of the scene, the truth constants, the material table, the action limits and the SEM vocabulary;
  the run seed; the host's `latency_policy` (§7.4).
- The environment: Python, numpy and scipy versions, `platform.machine()`, numpy's CPU dispatch features, the BLAS
  thread count.
- **A content mismatch is refused, loudly.** An environment mismatch downgrades the replay to an outcome-class check,
  and says so, like the rig rule.
- **Goldens are regenerated only** on a recorded content or environment change, in a commit that says which; never to
  make a red test green.

### 6.4 Every writer, classified (S11, S-7, N-3)

| Writer | Writes | Class |
|---|---|---|
| `Scene.build`, the save loader | cells, regions | construction (opens the window before the clock starts) |
| the applier: strike | cells, through the strike law | intent application |
| the applier: ignite, douse | `sources` | intent application |
| the applier: `imagine` (today's `place`) | cells, regions | intent application |
| the laws in `advance` | cells | advance |

- `StructureModulator.apply` stops being public. Its world-writing half becomes the applier; its gate half stays in
  the adapter.
- **A scheduled band-aid, marked.** Until sim-clock builds the log and the clock, `execute` calls the applier
  synchronously with no log. It gets a `TEMPORARY(phase1/sim-clock): …` marker in the adapter, and the file is listed
  under Phase 1 in `docs/roadmap.md`, in `phase1/boundaries` (S11).

## 7. Agents, time and the action contract

### 7.1 `AgentPort` (O3, BF-2)

The core defines the port; `engine.adapters.agents` implements it with Maxim; the agent lane runs it.

| Call | Direction | Meaning |
|---|---|---|
| `step(now_tick, dt_ticks, frame) -> intents` | sim → agent | advance the substrate by world time; return proposed intents |
| `settle(receipts)` | sim → agent | the outcomes of earlier intents |
| `request_thought(...)` | agent → host | ask for deliberation (§7.4) |
| `deliver(thought_result)` | host → agent | a thought's result, at its world-time deadline |

- **Option B, now:** the substrate runs at tick boundaries on published frames, and its outputs enter as logged
  intents. Replays are bit-identical because the log is the truth, and a replay never re-runs Maxim.
- **Inline later:** when Maxim ships an injected clock, RNG and ids and an externally stepped live tick (#1361,
  items 11, 12, 15), the same port is called inside the tick. Until then **real Maxim never runs in the sealed
  tick**, where its wall-clock reads would crash it under the tripwire or leak silently without it.
- **The static import contract is not what seals agents;** the tripwire and the log are.
- **Agent state lives outside `Simulation`.** Save v1 persists the world plus each NPC's agent home, separately.
  That decision is flagged to the save design.
- **Lane hand-off is counted inside the modelled latency** (§7.3), so the threading design never decides an NPC's
  biology.

### 7.2 The action contract: propose and settle (O2, BF-1, B1, BF-8)

- **The engine's contract is propose → receipt.** A receipt carries the intent id, the outcome kind (`applied`,
  `refused`, `stale`, `cancelled`), `apply_tick`, the measured effect (`destroyed_volume_m3`, `absorbed_j`, …), and
  the ids of the frames before and after.
- **Mode (a), now.** The Maxim adapter's `execute` submits the intent, then waits **in world time** for the receipt and
  the next published frame. It returns a `ModulatorResult` built from the application: `success` and `error` from
  the receipt, metadata from the measured effect, `measured_drive_transitions` from the before and after frames.
  - This is a body's reafference latency (one tick), not a wait for a thought, so "nobody waits for a thought"
    holds. It is Maxim's own Reachy precedent (`ReachyOrientMotorBackend.execute`).
  - The wait is bounded in world ticks. A paused world holds the call; it never times out on the wall clock.
- **Mode (b), later.** `execute` returns `outcome_valence: "neutral"` immediately and the receipt reaches Maxim
  through settle, once Maxim splits the tool into propose and settle (§9.3). Switching is a change to the adapter only.
- **Stale is context, never credit** (lesson 9 wins over `realtime_lanes_coop.md` §4.3, which is corrected). Maxim
  has no refusal kind for "the world overtook you": every `success=False` books NEGATIVE. Until P2 gains a `stale`
  kind, stale refusals under mode (a) are an **OPEN divergence with a strict red gate**, and the receipt also goes to
  the next thought's context.
- **Per-actor binding (BF-6).** `to_maxim_entity(world, region, actor=...)` gives each NPC its own entity and
  modulator, so its intents are stamped with that actor. `name` and `full_path` stay identical across actors, since
  the cerebellum and NAc key on them (lesson 10).

### 7.3 Three clocks (O4)

| Clock | What | Owner | Exact? |
|---|---|---|---|
| World time | the integer tick | `Simulation` | exact |
| Body time | drive drift, depletion, reflex latency | the agent substrate, fed the true world dt | exact |
| Perceived time | durations, order, time of day as the NPC believes them | modelled senses | coarse, biased, noisy |

Fields and tests laid now:
- **No time field reaches cognition.** The adapter strips `observed_tick`, `issued_tick`, `apply_tick`, receipt
  ticks, deadlines, the dial and dilation from everything agent-facing. A schema test and a prompt test prove it. The
  NPC matches a receipt by an opaque id.
- **The dial is invisible:** an NPC's percepts are bit-identical at 1× and 20×.
- **Δt invariance:** every agent-side process the adapter steps gives the same result at any step size (closed-form
  updates), the agent's version of the resolution rule.
- **A per-NPC seeded stream,** counter-based and keyed by `(run seed, actor, stream, counter)`, spawned from the log
  header's seed and owned by the agent side. Never the World's generator.
- **Timing data in microseconds** in `data/` (for example `data/agents/timing.yaml`); rates are integer divisors of
  the tick with a per-actor phase.
- **The membrane is the clock translator (BF-11).** Today `RegionSensor` stamps world seconds and Maxim's sensors
  stamp epoch seconds. Until item 10 and P5 land, each field's clock is documented, and the mismatch is an OPEN
  divergence with a red gate. `SensorReading.timestamp` never reaches a prompt verbatim.

### 7.4 Thought cost: the interfaces only (O4)

- **A thought request** carries `kind`, `deadline_ticks` (modelled onset), `cancel_on`, and a cache key (SHA-256 of
  the canonical request).
- **A thought result** is streamed: tokens stamped with world-microsecond offsets finer than the tick, interruptible.
- **The host's `latency_policy`** is logged in the header: the default slows the world when a real thought runs late,
  reported as dilation by cause; abandoning late thoughts is an explicit, logged alternative.
- **The tick size** is decided in sim-clock, with sub-tick offsets on the table.
- The phases (substrate reaction, onset, speech), the fatigue and sleep-pressure coupling, and every constant belong
  to part 2.

## 8. Maxim, content and experiments

### 8.1 Maxim through named adapters (B-2, rewritten; BF-3, X N-1)

- **Rule:** Maxim is imported only by named adapters, each declaring the Maxim surface it uses.

| Adapter | Package | Surface |
|---|---|---|
| SEM membrane | `engine.adapters.sem` | bodies, percepts, acts (`Entity`, `Modulator`, `SensorReading`, `ModulatorResult`, `AffordanceSchema`) |
| Agent stepping | `engine.adapters.agents` | stepping, clock and RNG injection, the experience driver, agent-state save |
| NPC authoring | game, when it exists | `AgentFactory`, seed memory, the arc loader |
| Experiment harness | `maxim_experiments` | the experiment and ledger tooling |

- **Enforced** by import-linter's `protected` contract on `maxim` (allowed importers listed; new root packages are
  covered automatically, verified on 2.15 without pymaxim installed), plus a lint comparing each adapter's imported
  symbols against its declared list.
- **Behaviour, not only shape (BF-10).** A behavioural contract test runs a real `ModulatorAffordanceTool` (and the
  actor tool) against the membrane and asserts what Maxim does with the result: the valence booked for applied,
  refused and pending results; what the cerebellum is trained on; which side-effect keys are promoted. The membrane's
  metadata keys are reserved (a key named `success` would overwrite the outcome). Lands with mode (a) in sim-clock.
- **Proposal ids are one id space** in `docs/roadmap.md` Phase 3 (BF-14). This design cites the realtime design's §6
  items and world_v2's P-numbers until that renumbering lands.

### 8.2 Content and licence (B-5; S9, X S-9, TB-S8)

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

### 8.3 Presentation (B-6)

Display quantization (`crack`, `glow`, uint8, float16 temperature) moves to `engine.encoding` in the protocol PR.
The core is forbidden from importing it; `engine.adapters.sem` is too (§2.2).

### 8.4 Experiments (B-7; S10, BF-9)

- `maxim_experiments` imports only the engine and its own Apache-2.0 fixtures (a fixture body, event pool and
  scene). Neither the engine nor the game imports it.
- Experiments that need game content are game runs, which stay off Maxim's ledger.
- **A ledger record pins** the engine SHA, the pymaxim version, the membrane contract version (mode (a) or (b), and
  any interim `neutral` behaviour, which is part of the treatment) and the Phase 3 items present.
- Decided now, because the Exp 64 draft freezes at the Phase 3 exit and will name these paths.

## 9. Protocol, tests and SEM refinement

### 9.1 One protocol schema (B-11; S7, TB-S4)

- **The in-code field registry is primary** (world_model §8). It generates the schema as a committed artifact; a
  golden test regenerates it and compares bytes.
- **The schema is shape plus closed vocabulary,** not validation. Stage 1 stays the only server validator; limits
  reach the client in the handshake for its UI only.
- **A strict JSON decoder** sits in front: `parse_constant` raises (no `NaN`/`Infinity`), `object_pairs_hook`
  refuses repeated keys, `max_size` applies before decoding. Integers are pinned to at most 2⁵³ (Godot parses numbers
  as doubles).
- **Golden rejection frames** (`NaN`, `1e400`, a repeated key, an oversized frame, an unknown field) sit beside the
  valid ones, decoded by both sides.

### 9.2 Tests out of the shipped path (B-12)

The external half only: the engine is forbidden from importing `pytest` and `hypothesis`. `tests` and `scripts`
aren't packages in the import graph, so that half couldn't fail (Arch N5) and is dropped.

### 9.3 SEM refinement items (O5)

| Item | Why | Path |
|---|---|---|
| Injected clock, RNG and ids; `step(world_dt)` for the agent and the Default Network | the agent lane needs them (§7.1) | additive now (the dedicated "world clock" release) |
| The cerebellum observes at settle time, not during the call (valence is not a cerebellum input: it trains on the sensors read in the call, `tool_bridge.py:864-892`; NAc already honours `neutral`, `tool_dispatch.py:356-375`) | mode (b) must not train on unverified state (BF-1) | additive now |
| A `stale` refusal kind in P2 | §7.2 | additive now |
| Implement `EntropicDriveSpec.coupled_to` for the fatigue coupling (`sem.py:244`; parsed, never applied), with a cognitive-reserve sensor (`modulated_by` exists only on homeostatic drives) | thought cost (O4) | additive now |
| Per-part `world_set_axis` (P4) | §4.3 | additive now |
| Reserved membrane metadata keys | BF-10 | additive now |
| Propose and settle at the tool (P3 with item 16) | mode (b) | batched |
| What `SensorReading.timestamp` means; `drift_rate`'s time base | §7.3 | batched |
| Deep-frozen `ModulatorResult`/`SensorReading` | §5.1 | batched |
| A declared direction per affordance (done to / done by) | lesson 8 | batched |
| An acting-entity context on `execute` | BF-6 (only if per-actor binding is measured to be costly) | batched, low priority |

Batched items go into **one SEM breaking-change plan**, drafted in `docs/maxim_upstream/`, through Maxim's process.

## 10. Enforcement

| Boundary | Check | Lands |
|---|---|---|
| B-1 engine/game/experiments | import-linter forbidden contracts | `phase1/boundaries` |
| B-2 Maxim adapters | `protected` contract on `maxim`; declared-surface lint; behavioural contract test | boundaries; the behavioural test with sim-clock |
| B-3 sealed core | forbidden contract (one shared banned list); extended AST scan; writer non-vacuity test; tripwire over the corpus | boundaries; tripwire with sim-clock |
| Rendering never reaches truth | forbidden contract: core ↛ `engine.tiers` | boundaries |
| Skip-layer rule | forbidden contract: adapters, protocol, host ↛ cells, laws, geometry, scene build | boundaries |
| B-4 untrusted input | input-primitive allowlist (import-linter + AST lint); banned unsafe calls; gate registry with per-gate branch coverage | boundaries |
| B-5 content | directory rule; disjoint material key sets; wheel manifest check | material table v1 |
| B-6 presentation | forbidden: core and `adapters.sem` ↛ `encoding` | the protocol PR |
| B-7 experiments | forbidden: engine and game ↛ `maxim_experiments`; harness ↛ game | the first experiment |
| B-8 layers | import-linter layers contract, committed order | boundaries |
| B-9 one pipeline | the write window (§4.1); record golden fixtures; ordering test; replay with `maxim` blocked | boundaries (window); sim-clock (log) |
| B-10 observation | frame tests (§4.2); `Observation` protocol under mypy | boundaries |
| B-11 one schema | regenerate-and-compare; golden valid and rejection frames on both sides | the protocol PR |
| B-12 tests out | forbidden: engine ↛ `pytest`, `hypothesis` | boundaries |
| B-13 physical percepts | import half: `adapters.sem` reads frames and the registry only | boundaries; perceiver half Phase 4 |

**Running import-linter (X-1, W3, W8, X S-6):**
- Pin `import-linter==2.15` and grimp 3.18. 2.16 requires Python ≥ 3.11 and the repo supports 3.10.
- Run it as `PYTHONPATH="$PWD/src" "$PY" -m importlinter.cli` in `prepush.sh`. Without it, a worktree checks the
  main checkout's code through the shared venv's `.pth` (a planted violation reported KEPT).
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
  - Split `StructureModulator`: gate half in `adapters.sem`, write half into `sim` as the applier, with the
    TEMPORARY marker and roadmap row (§6.4).
  - The contracts, the import-linter wiring and the tooling tests (§10).
- **2c `phase1/gates`: behaviour.**
  - The write window and read-only owners (§4.1); published frames, sensors on frames, instruments relabelled (§4.2,
    §4.4).
  - Validating constructors (§5.1); the gate contract and registry (§5.2, §5.4); budgets and bounded echo.

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
  rule) and `docs/architecture.md` are updated by hand. `docs/design/reviews/` and `docs/design/research/` are kept
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

## 12. Open questions for the owner

1. **The engine's package name.** A Maxim-neutral name is recommended (`engine` is a working placeholder).
2. **Two PRs (structure, then behaviour) or one.** Two is recommended: the rename touches about 70 references in 25
   files, and reviewing it apart from new behaviour keeps both reviewable.
3. **Abandoning `phase1/transport` and `foundations/world-server-v0`.**
4. **Imagination budgets:** the mechanism is engine; per-actor budget values are game data, loaded through a gate.

## 13. What this design does not settle

- **Stale refusals under mode (a)** stay an OPEN divergence until Maxim has a `stale` refusal kind (§7.2).
- **Two clocks into Maxim** stay an OPEN divergence until item 10 and P5 (§7.3).
- **BLAS in the core** is forbidden rather than policed; the first solver that needs it reopens this (§3).
- **The perceiver half of B-13** waits for the first NPC body (Phase 4).

## Fold table

Every BLOCKER and SHOULD-FIX, by review. Status is **folded** (with the section), or **deferred** (with the reason).

| Finding | Severity | Status |
|---|---|---|
| Arch B1 execute's result contract | BLOCKER | folded: §7.2 (owner decision O2; detail in part 2) |
| Arch B2 the gate lint can't see the door | BLOCKER | folded: §5.2 |
| Arch S1 rendering tier reaches physics | SHOULD-FIX | folded: §2.2, §10 |
| Arch S2 layers allow skipping | SHOULD-FIX | folded: §2.2 skip-layer rule, §10 |
| Arch S3 the intent gate has no home | SHOULD-FIX | folded: §2.2 `engine.intents` |
| Arch S4 sealed set too narrow; two lists | SHOULD-FIX | folded: §3 |
| Arch S5 no geometry layer | SHOULD-FIX | folded: §2.2 |
| Arch S6 read-only views wrong once there are lanes | SHOULD-FIX | folded: §4.2 |
| Arch S7 schema vs registry | SHOULD-FIX | folded: §9.1 |
| Arch S8 split trigger; client not cut | SHOULD-FIX | folded: §2.1 |
| Arch S9 engine reaches game data by default paths | SHOULD-FIX | folded: §3, §8.2 |
| Arch S10 harness has no package | SHOULD-FIX | folded: §2.1, §8.4 (imports engine only, per BF-9, not engine and game) |
| Arch S11 other doors; unmarked band-aid | SHOULD-FIX | folded: §6.4 |
| Arch S12 order disagrees with world_model §10 | SHOULD-FIX | folded: §11.1, world_model §10 and roadmap updated |
| BF-1 queued intents blind Maxim's credit | BLOCKER | folded: §7.2 mode (a) now, (b) later; §9.3 |
| BF-2 where the substrate runs | BLOCKER | folded: §3, §7.1 (owner decision O3) |
| BF-3 only `sem_env` can't hold | BLOCKER | folded: §8.1 |
| BF-4 percepts are samples, not views | SHOULD-FIX | folded: §4.2 |
| BF-5 the push path | SHOULD-FIX | folded: §4.3 |
| BF-6 no actor on execute | SHOULD-FIX | folded: §7.2 per-actor binding; §9.3 |
| BF-7 the membrane is omniscient | SHOULD-FIX | folded: §4.4 (B-13) |
| BF-8 stale: credit or context | SHOULD-FIX | folded: §7.2 (lesson 9 wins; lanes §4.3 to be corrected) |
| BF-9 harness must depend on the engine only | SHOULD-FIX | folded: §8.4 |
| BF-10 drift check covers shape only | SHOULD-FIX | folded: §8.1 |
| BF-11 two clocks into one agent | SHOULD-FIX | folded: §7.3 |
| D-B1 the writers are outside the core | BLOCKER | folded: §3 |
| D-B2 unrecorded input from disk | BLOCKER | folded: §3, §6.3 |
| D-B3 the log has no record | BLOCKER | folded: §6.2 |
| D-B4 read-only views defeated | BLOCKER | folded: §4.1 |
| D-S1 the tripwire can't see the cited case | SHOULD-FIX | folded: §3 |
| D-S2 the forbidden list vs import-linter | SHOULD-FIX | folded: §3, §10 |
| D-S3 non-import leaks | SHOULD-FIX | folded: §3 |
| D-S4 environment header | SHOULD-FIX | folded: §6.3 |
| D-S5 observation reads live state | SHOULD-FIX | folded: §4.2 |
| D-S6 the AST scan can go vacuous | SHOULD-FIX | folded: §11.2 |
| D-S7 one log for every input | SHOULD-FIX | folded: §6.1, §6.2 |
| D-S8 canonical same-tick order | SHOULD-FIX | folded: §6.2 |
| D-S9 log the typed canonical intent | SHOULD-FIX | folded: §6.2 |
| X-1 lint-imports reads the main checkout | BLOCKER | folded: §10 |
| X-2 `execute` is the gate | BLOCKER | folded: §5.2, §5.3 |
| X-3 B-10 guards copies | BLOCKER | folded: §4.1, §4.2 |
| X S-1 `os.urandom`; scan misses | SHOULD-FIX | folded: §3 |
| X S-2 the layers fail on today's code | SHOULD-FIX | folded: §2.2 |
| X S-3 three gates don't refuse | SHOULD-FIX | folded: §5.4 (gates-to-be, hardened in 2c) |
| X S-4 the lint rule's false positives and misses | SHOULD-FIX | folded: §5.2 (rule dropped) |
| X S-5 migration drops the game package | SHOULD-FIX | folded: §11.2 |
| X S-6 import-linter pin; cache | SHOULD-FIX | folded: §10 |
| X S-7 B-9's check misses `sources`; mechanism | SHOULD-FIX | folded: §4.1, §6.4 |
| X S-8 the core does file IO; `sem_env` runs in the turn | SHOULD-FIX | folded: §3 (the writers move in; the gate half is outside, with no clock or IO) |
| X S-9 packaging and the B-5 split | SHOULD-FIX | folded: §8.2 |
| TB-B1 the lint can't detect a new door | BLOCKER | folded: §5.2 |
| TB-B2 typed frozen is false | BLOCKER | folded: §5.1 |
| TB-B3 no authority or identity | BLOCKER | folded: §6.1 |
| TB-S1 the gate list is incomplete | SHOULD-FIX | folded: §5.3 |
| TB-S2 gates not equally strong | SHOULD-FIX | folded: §5.4 |
| TB-S3 no cost or size budgets | SHOULD-FIX | folded: §5.4 |
| TB-S4 the schema is shape only | SHOULD-FIX | folded: §9.1 |
| TB-S5 the target check is by identity | SHOULD-FIX | folded: §5.3, §6.2 |
| TB-S6 imagination is a second door | SHOULD-FIX | folded: §5.3, §6.4 |
| TB-S7 the B-9 test sees only exercised paths | SHOULD-FIX | folded: §4.1 |
| TB-S8 the wheel's licence; material key sets | SHOULD-FIX | folded: §8.2 |
| W1 rebases land in the game package | BLOCKER | folded: §2.1, §11.3 |
| W2 scope references go engine-only | BLOCKER | folded: §11.2 |
| W3 lint-imports reads the main checkout | BLOCKER | folded: §10 |
| W4 the empty package has no caller | SHOULD-FIX | folded: §2.1 |
| W5 the `_data` mapping is never exercised | SHOULD-FIX | folded: §11.2 |
| W6 the tier variable split across files | SHOULD-FIX | folded: §11.2 |
| W7 docs sed unsafe and incomplete | SHOULD-FIX | folded: §11.2 |
| W8 contracts partly unexpressible; the guard step | SHOULD-FIX | folded: §3, §10 |
| W9 merge order | SHOULD-FIX | folded: §11.3 |

Coverage: 18 of 18 BLOCKERs and 52 of 52 SHOULD-FIXes folded; none deferred. NITs folded where they touched a
section: Arch N1–N8; BF-12 to BF-15; D-N1 to D-N3, D-N5; X N-1 to N-3; TB-N1 to N-4; W10 to W14. D-N4 (drive
determinism tests from the golden log, by kind) is deferred to sim-clock, where the golden log is born.
