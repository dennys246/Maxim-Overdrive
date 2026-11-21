# Boundaries between engine, game, Maxim and the outside world (design v3, 2026-11-16)

**Status:** DRAFT v3, for a delta design review before any code. v1 (47add00) went to a six-lens review
(`docs/design/reviews/boundaries/`: 18 BLOCKER, 52 SHOULD-FIX, 29 NIT), folded in v2. v2 (4f7a754) went to the
seven-lens foundations review with part 2 and the Maxim drafts (`docs/design/reviews/foundations_v1/`). This version
folds every foundations BLOCKER and SHOULD-FIX that touches it, and the owner's decision O6 (§0). Its agent sections
(§7.1, §7.4, §8.1, §9.3) were revised on 2026-11-17 to match `npcs_and_sem.md` v3 (O6a, O7a, O13). Two fold tables at
the end map each finding to where it landed.

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

| # | Decision |
|---|---|
| O1 | One repository, with an enforced engine/game boundary and a written split trigger. |
| O2 | *Superseded by O6.* It was: the action result contract (a) now (a world-time wait in `execute`), (b) later (`neutral` plus late credit). The foundations review showed (a) deadlocks with dilation, races the tick, and credits only instant effects, and that "(a) → (b) is an adapter change" was overstated (foundations Arch B2). |
| O3 | **The agent substrate** runs outside the sealed core, behind an engine-defined `AgentPort` in integer ticks: frozen frames in, logged intents out. Refined by O6: the host steps it. |
| O4 | **Three clocks** (world, body, perceived). No time field reaches cognition. Thought cost is modelled in world time and phased; the world slows (reported dilation, by cause) when real thoughts run late. Abandoning late thoughts is an explicit, logged host policy. Thinking couples to the fatigue drive and sleep pressure, not hunger. Details are part 2's (`npcs_and_sem.md`); this design carries only the interfaces and fields. |
| O5 | **Refining Maxim's SEM is in scope and a priority** of the foundations work, through Maxim's own process. Each SEM-touching item here cites its roadmap `OD-` id and path (§9.3): additive first in 1.x. |
| O6 | **Mode (a) is dropped; agents follow a host-driven embeddable contract.** The host calls `agent.step(world_dt, frame)`; the agent returns intents, memory writes and thought requests as values and never applies anything or runs on its own. Maxim must offer a host-supplied LLM gateway with streaming and cancellation, a closed NPC tool roster checked at build, a per-agent home under the save (never `~/.maxim`) with no pickle on the load path, no host time in prompts or observations, the cerebellum observing at settle, and `outcome_valence` per D53. Phase 1 has no NPCs; Phase 4's NPCs wait on Maxim shipping it. Detail: `npcs_and_sem.md` §6. *Its mechanism is corrected by `npcs_and_sem.md` O6a: no inner tool loop in Maxim, so `think` is host-called and resumable, returns model requests as values, and cancel is a `cancelled(prefix)` reply; the host service protocol is gone (§7.1).* |
| O7 | **The world half proceeds; the agent half is parked (2026-11-16, after the foundations delta round).** The world half (packages and layers, the sealed core, gates by source, the log record and canonical order, replay tiers, keyed randomness, the response-cache rules) folds this round's world findings and goes to `phase1/boundaries` and `phase1/gates` after PR 1 is rebased. The agent half (`AgentPort` under O6, `npcs_and_sem.md` §4.4 and §6) stays a reviewed draft: no further review rounds until Maxim answers the embeddable-agent questions (a resumable `think`, how far `maxim.advisor` and `AgentFactory` reach). It goes to Maxim as a conversation, not as a polished draft. |
| O7a | O7's condition is met: Maxim answered (`reviews/maxim_response_1/`), so the agent half is unparked for one revision and one review round. Each real agent runs in its own worker process, the process boundary being the trust boundary (`npcs_and_sem.md` O13). |
| O21 | **Merge, never rebase (owner, 2026-11-17).** Pushed branches are merged forward (`phase1/standards` into each, and the merge line in `docs/merge_notes.md` on `phase1/realtime-design`), never rebased, so no branch needs a force-push. PR #1 targets `main`. This replaces §11.3's rebase order. |
| O22 | **A word budget for documents (owner, 2026-11-17; a standards change still to make).** No existing design document grows; a new design document is at most 6,000 words, the plan at most 2,500, a review report at most 3,000. |
| O23 | **§12's questions answered as recommended (owner, 2026-11-17, after the plan's fold).** The engine package is `simcore`. Two PRs, structure then behaviour. `phase1/transport` and `foundations/world-server-v0` are abandoned (`phase1/standards` contains both). Imagination budgets are engine mechanism with per-actor values in game data. Frames publish on change, not per tick. |
| O24 | **Three or four layers, not twelve (owner, 2026-11-17; skeptic S-S4).** `phase1/boundaries` builds the engine core, the adapters, the game and the client protocol as layers, with import contracts; a layer splits when a module passes the 500-line tripwire. This amends §11.1's twelve-layer list, which becomes the map of where splits are expected to fall. |
| O31 | **The word cap is per document; a split along a real seam is allowed (owner, 2026-11-18).** The tile spec split into `tile_and_client.md` (world) and `client_rendering.md` (Godot), about 9,970 words together, each under 6,000. A split must follow a seam the work has (different lenses, different plan steps), not cut one subject in two to dodge the cap. |
| O32 | **Lock every dependency; surface drift on a schedule (owner, 2026-11-18, after the flexibility review).** A constraints lockfile per supported Python version pins the gate and CI, pymaxim included. A scheduled unpinned CI job runs the gate, the SEM drift test among it, against the newest releases, and its failure opens the mirror-update work. CLAUDE.md's "update the mirror rather than pinning it away" keeps its intent (drift is never hidden) and changes its mechanism. |
| O33 | **Python 3.12 or later (owner, 2026-11-18).** `requires-python >= 3.12`; CI on 3.12 and 3.14. 3.10 is past end of life and resolved a different numpy and scipy line than 3.14. |
| O34 | **Plan step 5 splits (owner, 2026-11-18).** 5a the simulation core: clock, `Simulation`'s composition (a short note first), the ordered law list, the field registry, region ids, caches. 5b bodies and movement. |
| O41 | **The roadmap is exempt from O22's word budget (owner, 2026-11-19).** It is the living index of phases and Phase 3 ids, so it grows with decisions. O22 covers design documents, plans and review reports. |
| O42 | **`docs/plans/checklists.md` is exempt from O22's word budget (owner, 2026-11-19).** It is a living list of each step's items, like the roadmap (O41). Each step's section is deleted when that step's PR merges, so it shrinks as work lands. |
| O25 | **Reviewers, not authors, set fold status (owner, 2026-11-17).** A finding's status (`fixed`, `deferred`, `rejected`, `open`) in a fold table is set by a reviewer reading the tree, as in `docs/plans/reviews/fold.md`; an author's own status is marked as such. A standards change still to make, with O22's budget. |
| O8 | **The write window is a dev and test-build check; correctness rests on structure.** Only the applier and the physics laws hold the write handle. The window's ownership check, and a reference-count check at window exit that finds any surviving view, run in dev and test builds, as engine job-safety checks do. A shipped build doesn't copy frames at exit: measured at about 5.7 ms against a 5 ms tick. |

## 1. Why now, and what the code is today

Each boundary costs a few renames now, and a refactor across the protocol, zones, fuel and the lab later.

Surveyed on `phase1/act-validation` at 2f200b5 (Executor confirmed each item):
- `src/maxim_overdrive/` has `checks.py`, `config.py`, `world/` (grid, scene, heat, damage, world), `imagination/`
  (spec) and `sem_env/` (bridge, `_compat`), plus a root `__init__` that re-exports config, grid, scene and world.
- Only `sem_env/bridge.py` imports `maxim`.
- No module imports `time`, `random`, `os` or `importlib`, but the core reached `pathlib` and `yaml` (`config.py`)
  and `scipy` (`damage.py`), which bear on determinism (D-N1, D-B2; the IO left the core in 3a).
- The world's writers lived outside `world/`, in the bridge and `place` (D-B1); objects called frozen were neither
  deeply frozen nor validated (TB-B2). Both fixed in 3b.
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
| 7a | `engine.loaders` &#124; `engine.tiers` | file gates (including `ActionLimits.load` and the save's decoding half); `RigProfile` as a rendering tier |
| 7b | `engine.encoding` &#124; `engine.adapters.sem` | display quantization (B-6, uses tiers); the Maxim membrane |
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
  - `maxim` (also held by B-2's protected contract).
  - **Explicitly allowed:** `hashlib`, `math`, `dataclasses`, `enum`, `typing`, `numpy`, `scipy`, `logging`
    (output only).
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
  trip. It guards only what the corpus exercises, and it ships with sim-clock.
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
- **Before `Simulation` exists (2c; foundations Wire B1).** In `phase1/gates` the window's owners are `World.advance`
  and the intent applier, each under a TEMPORARY marker scheduled for `phase1/sim-clock`, saying it moves to
  `Simulation.step`, with
  the files listed under Phase 1 in `docs/roadmap.md`. Until sim-clock, the applier publishes a frame after each
  application, so `tests/test_sem_bridge.py`'s strike-then-read keeps its meaning without an edit.

### 4.2 Observation reads published frames (B-10, rewritten)

- **Rule:** percepts and instruments are immutable samples of one published frame, stamped with its tick. Nothing
  outside the simulation lane holds a reference to `World`, the grid or `MaterialTable` (S6, BF-4, D-S5, X-3).
- **Frames are copies, published on change (foundations Arch S4, DR-S9).** Never the owner, which the next window
  replaces. Cells change at physics steps and at intent apply, so a frame is published then, not per tick. Agents get
  reductions (per-region and per-NPC scalars from the bincount pass), not grids: a full-grid copy is 64–80 MB per tile
  at 0.1 m, about 13–16 GB/s of copying if published per tick at 20×. The copy and the publish are B5 rows.
- **Cadence:** a frame is published after each physics step (0.5 s) and after each tick that applied an intent, so a
  receipt's after-frame exists on its apply tick. The design never promises "one tick" of reafference for effects that
  only show at the next physics step.
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

- Maxim bodies perceive by push: the world writes measured values into `vital_metrics` through `world_set_axis` with
  `live_world_set_sensors` declaring the world the single writer.
- **This is a sanctioned mutation of agent state,** done by `engine.adapters.agents` on the agent's owner thread
  (§7.1), as a pure function of the agent's pinned frame (so it needs no log record).
- **Every body sensor the world simulates is world-owned.** A modeled `self_effect` is allowed only on sensors the
  world doesn't simulate, and each one is listed as an ANALOG divergence. Otherwise an NPC is burned twice, by the
  YAML delta and by physics.
- Per-part sensors (`arms.thermal`) need OD-C10, since `world_set_axis` is root-only today.

### 4.4 B-13 (new): percepts come only through physical channels at the perceiver (BF-7)

- **Rule:** a percept is a reduction of registered physical channels, evaluated at the perceiver's position and
  receptor, with a line-of-sight gate once light exists. The membrane reads the world only through frames and the
  field registry.
- **Today's region sensors are test and lab instruments,** relabelled as such (an ANALOG divergence), never an NPC's
  input. **An instrument an NPC uses is an in-world device** with a position, its own physical reduction and a
  display perceived like any other percept (foundations BF2-6; `npcs_and_sem.md` §7.1).
- **The membrane drops `cell_size_m`** from readings and entity metadata, which put the rendering tier in front of
  cognition (foundations Wire S6).
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
| **Agent homes** (foundations TB2-B2) | Maxim's `data_home()`; saves | — | one home per agent, under the save; never `~/.maxim` | until `AgentHome` routes every store, each real agent runs in its own worker process, its working directory at its agent home, with an allowlisted environment and no `MAXIM_*` (Maxim's A4 waits for A1, so OD-A17's env-read test allows no read; `npcs_and_sem.md` §6.6); a test asserts two NPCs resolve different homes. Agent homes from outside this machine are a **gate-to-be**: a foreign save loads the world only and re-seeds agents from the roster; a home loads only from a save this machine wrote, checked by a per-install HMAC, until Maxim's persistence is pickle-free | `phase1/agents`; save v1 |
| `target=<Entity>` and other Maxim objects | Maxim's actor tool | — | — | resolved to a stable id at `execute`, namesake and identity checks before the intent is frozen (TB-S5) | `phase1/boundaries` |
| Imagined objects | LLM via Maxim | the bound actor | the actor's budget | `imagine` intent: spec constructors at stage 1, `place` as stage 2 (TB-S6) | `phase1/boundaries` (kind), sim-clock (log) |
| **The worker channel** (`npcs_and_sem.md` §6.6; Exec B1, TB3-B1) | a real agent's worker process | one actor per channel, bound at spawn | — | the strictest contract: length-prefixed, versioned, closed-schema JSON through the strict decoder, closed message kinds per direction, size budgets before allocation, pickle-free (`multiprocessing`, `pickle`, `marshal`, `shelve` banned in `engine.host` and `engine.adapters`); golden rejection frames and a planted pickle frame; a refused frame, a hang past the per-park ceiling or a crash ends the agent as a logged `agent_failed` | `phase1/agents` (with the test double behind it) |
| Thought results: intents, speech and **memory writes** | the agent's `StepOutput` and `ThoughtOutput`, decoded from the worker channel | the bound actor | an NPC's own memory only, with provenance by source actor (§6.6) | everything re-validated **in the host**: intents and speech through stage 1, memory writes through the host's gate before the host passes them to `settle` (canonical order; O39); a **gate-to-be** until generate vs apply (OD-A18) gives the game a value to check, an OPEN divergence with a strict red gate (foundations TB2-S3) | `phase1/agents` (types); OD-A18 (memory) |
| **Thought budgets** (foundations TB2-B3) | the host's thinking lane | — | — | PFC cycles, `parallel_actions`, `next_actions` and follow-up chains per triggering input, tokens per call (a generation limit and a stream cut-off before buffering), held-buffer bytes, memory writes, `cancel_on` length, `D` ceilings, from `data/agents/thought_budget.yaml` | `phase1/agents` |
| **Player speech and all guest text** (foundations TB2-S1; TB3-S3, TB3-S4, TB3-N4) | network lane | session token | per-session rate limit | one gate, `engine.text.player_text`, for `speak` and every guest string that can reach a prompt: length cap, NFC, then on the **decoded** text, per chunk and whole, refuse controls, bidi overrides, every line separator `str.splitlines` splits on (U+2028, U+2029, U+0085, `\v`, `\f`, U+001C–U+001E) and every format (Cf) character, zero-width and tag characters included | `phase1/protocol` |
| **The response cache** (foundations DR-B3, TB2-S4, Wire S9) | disk, per save | — | — | the strictest contract: versioned, strict decoder, size budgets; an entry holds only raw output, the canonical request and its provenance, and the gate recomputes the hash and refuses a mismatch; never read by replay | after tier A |
| Scene files, saves, intent logs, bug reports | disk, **strangers' machines** | — | — | the strictest gate (world_model F14): no pickle, budget before allocation, all-or-nothing | scene v1, save v0, sim-clock |
| Rigs, materials, limits, vocabulary, presets, rosters, arcs | `data/`, `content/`, later mods | — | — | a loader each under the gate contract (§5.4) | today and as each lands |
| Handshake, per-launch token, `Origin` | network lane | `hmac.compare_digest`, `Origin` refused, loopback bind (lanes §5) | — | the protocol decoder | `phase1/protocol` |
| Joins and leaves | network lane | session token | — | session to actor id allocation (lanes §4.2) | `phase1/protocol` |
| Controls: dial, pause, presets | host session | session token | `TimeAuthority` / `HostOnly` (lanes §5) | the protocol decoder | `phase1/protocol` |
| Client frames (intents) | network lane | session token | per kind | strict JSON decoder (§10), then stage 1; client-supplied `observed_tick`, `issued_tick`, `apply_tick`, `apply_us` and speech timing are refused, with golden rejection frames (foundations TB2-S6) | `phase1/protocol` |
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

| Kind | Who may emit it |
|---|---|
| `intent` (strike, ignite, douse, …) | any actor |
| `imagine` | any actor, within its budget |
| `speak` | any actor: an NPC only through a thought, a player only through a protocol message (foundations TB2-S1) |
| `control` (dial, pause, presets, `latency_policy`, the thought-pace table) | host sessions only, through `TimeAuthority`. **NPCs can never emit it, and dilation is never a lever a guest can request** (foundations TB2-S7, DR-S11) |
| `thought_cancelled` | the host, from world events in `cancel_on` only, rate-limited per source; a guest can't cancel thoughts by talking repeatedly (foundations TB2-S7) |
| `thought_failed` (reason: budget, timeout, model error) | the host's thought gate (foundations TB2-B3, Wire S4) |
| `join` / `leave` | the network lane |
| host commands: advance (in ticks), rig selection, save, load, admin `set_material` | the host |

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
- **An intent record** is frozen and versioned, with golden fixtures for its format:
  - `schema_version`, `kind`, `actor_id`, `seq` (per actor);
  - `observed_tick`, `issued_tick`, `apply_tick`, and **`apply_us`** (int64, the integer world-microsecond offset
    within the tick; foundations Arch S7, DR-S2, Wire S4). Never a float;
  - `params`: the **typed canonical** form after stage 1, so later gate tightening doesn't change old replays; the
    raw payload is an optional audit field only;
  - `target`: a **stable id** (a region name or persisted entity id), resolved at the door. Nothing identity-based
    crosses into the log.
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
- **One ordering key, stated here and nowhere else (foundations DR-S3, Wire S4; supersedes `realtime_lanes_coop.md`
  §4.2's arrival-order `host_seq`):** `(apply_tick, kind_rank, apply_us, actor_id, seq)`. Controls and joins rank
  before intents. The log is written in that order, so a replay never sorts. Float accumulations over named
  collections (today `World._power_field` over `sources`) iterate in sorted-key order. Ordering keys are integers
  (D-N2).
- **Replay calls nothing live:** no model, no Maxim, no clock, and **never the response cache**. Tested by replaying
  with `maxim` blocked from import, and with the cache deleted or poisoned (foundations TB2-S4).
- **Replay reproduces the world, never the agents (foundations DR-S7).** Under O3 and O6 replay never runs Maxim, so
  it reproduces `World` bit for bit and no agent state. Why an NPC chose something needs a tier-2 **rerun**, against
  the rerun manifest (§6.3). So a save is a checkpoint plus the log for the world, and agent homes are saved as state.
  CLAUDE.md's replay sentence is scoped to the world when this lands (§11.2).

### 6.3 The log header (D-B2, D-S4)

- Content digests of the scene, the truth constants (including `tick_us`), both material files after the split (the
  engine's and the content's), the action limits, the imagination budgets and the SEM vocabulary; the run seed; the
  host's initial `latency_policy` and thought-pace table (later changes are control records, §6.2).
- **The rig** (while it still feeds anything until the truth constants absorb it), the **engine SHA** and the
  `derivation_version` (world_model F15) (foundations Wire S8).
- **One digest form:** SHA-256 over a canonical serialisation of the loaded, typed value (sorted keys, fixed number
  format), so a YAML comment change doesn't refuse a replay. One canonicalizer, in `engine.checks`.
- **Dilation by cause** is log metadata the `Simulation` never reads (foundations Wire S7); it reaches the client
  through a host status message (`npcs_and_sem.md` §5.4).
- The environment: Python, numpy and scipy versions, `platform.machine()`, numpy's CPU dispatch features, the BLAS
  thread count.
- **A content mismatch is refused, loudly.** An environment mismatch downgrades the replay to an outcome-class check,
  and says so, like the rig rule.
- **Goldens are regenerated only** on a recorded content or environment change, in a commit that says which; never to
  make a red test green.
- **A rerun manifest beside the header (foundations DR-S7, Wire S8),** with the same refuse-on-mismatch rule, for
  tier-2 reruns that re-run agents: the digests of `data/agents/` (timing, speech, fatigue, thought budget), the
  roster and each agent home's initial state; the pymaxim version and config digest; the placement table's digest
  and role envelopes (reported, never refused: `inference_placement.md` §4.3); the response cache's digest;
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
| `Simulation.from_scene`, the save's construction half | cells, regions | construction (opens the window before the clock starts) |
| the applier: strike | cells, through the strike law | intent application |
| the applier: ignite, douse | `sources` | intent application |
| the applier: `imagine` (today's `place`) | cells, regions | intent application |
| the laws in `advance` | cells | advance |

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
| `AgentPort` | `engine.sim` | the host | `step(now_tick, dt_ticks, frame) -> StepOutput`; `think(handle, reply \| None) -> Pending \| ThoughtOutput`; `settle(receipts, writes)` (O39). Maxim's embedded function is `step(agent, world_dt_us, frame)`; the adapter converts ticks through the fixed schedule |

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
- **The host's thinking lane** in `engine.host` executes request values, by deadline, with the response cache and
  cancel as a reply. It is the only path to a model and owns placement; a host-owned gateway makes the calls through
  Maxim's backends, never its router (`inference_placement.md`).

**The agent lane (supersedes `realtime_lanes_coop.md` §4.1's "the simulation lane owns … agents" and "agents step
inside the simulation lane's tick"):**
- **One owner per agent.** Each real agent runs in its own worker process (`npcs_and_sem.md` O13): `spawn`, a
  scrubbed environment, its home and working directory at its agent home, the offline latch engaged after the pipe
  opens. Its `step`, `think`, `settle` and any push into its body run there, serialised. The channel to it is
  a registered gate (§5.3), the environment an allowlist, and a hung or dead worker ends as a logged `agent_failed`,
  never a frozen barrier (`npcs_and_sem.md` §6.6). The worker contains Maxim's default leak paths; it is not an OS
  sandbox.
- **The barrier (foundations DR-B1).** The host steps tick T+1 only when every agent is parked: returned from `step`,
  `think` or `settle`, an outstanding request being a `Pending` value, not a parked thread. Released work runs to its next park before the tick advances, in the
  canonical order (§6.2). Lockstep on intents alone isn't enough: agent code would race the tick, and what the
  cerebellum trains on would depend on the dial.
- **Agent isolation** comes from the worker process for real agents; tier A still proves it inside one process
  (OD-EA6), since Maxim's module-level state (global `random`, caches, the de-duplication window) is shared there
  (foundations DR-S5, TB2-B2).
- **`dt_ticks` is a pure function of the actor's rate divisor and phase,** never of lag (foundations DR-S1).
- **Agent state lives outside `Simulation`.** Save v1 persists the world plus each NPC's agent home, separately.
- **Lane hand-off is counted inside the modelled latency** (§7.3), so the threading design never decides an NPC's
  biology.
- **Inline later:** with requests as values the only nondeterministic input is the reply, so calling agents inside
  the tick is no longer blocked by determinism. But inlining puts Maxim back in the host process, which O13 made the
  trust boundary, so it is a design decision against O13, not only a B5 measurement (Arch N1).
- **Until tier A,** real Maxim behind the adapter is a strict red gate; every [now] agent test runs against the
  scripted test double, in a spawned worker behind the same channel (`npcs_and_sem.md` §6.2, §6.6).

### 7.2 The action contract: propose, receipt, settle (O6; BF-1, foundations BF2-3, Wire S12, Arch S13)

- **The engine's contract is propose → receipt → settle.** An intent produces one receipt: the intent id
  `(actor_id, seq)`, the outcome kind (`applied`, `refused`, `stale`, `cancelled`), `apply_tick`, the measured effect
  (`destroyed_volume_m3`, `absorbed_j`, …), and the before and after frame ids.
- **There is no blocking wait.** v2's mode (a) blocked Maxim's tool loop in `execute` until a world-time receipt. It
  deadlocked with the dilate policy on one worker (foundations Arch B2), raced the tick (DR-B1), had no route into the
  pipeline and no second lane to wait across (Wire B2), and credited only instant effects (Arch S13). Under O6 the
  agent returns intents as values and receives receipts through `settle`.
- **Each receipt is credited exactly once,** through `settle`, and zero times when `stale`; a test asserts it.
- **Valence per D53:** the adapter always self-reports. `neutral` when the measured effect is nil or unverifiable,
  drive deltas through `measured_drive_transitions`; absent a report, Maxim books mechanical success as POSITIVE.
- **Credit reads declared sensors only,** the ones the affordance declares it affects, and never instruments.
  Slow-effect credit (ignite) is an OPEN divergence with a red gate until settle can carry a horizon (OD-A16).
- **Stale is context, never credit** (lesson 9). Until Maxim promotes a refusal-kind key through the bridge's failure
  path (OD-A16), stale refusals are an OPEN divergence with a strict red gate, and the receipt goes to
  the next thought's context.
- **Per-actor binding (BF-6; foundations TB2-S8):** each NPC gets its own entity and modulator, bound to its actor.
  `name` and `full_path` stay identical across actors (lesson 10). The adapter refuses a call whose bound actor isn't
  the agent it is stepping.

### 7.3 Three clocks (O4)

| Clock | What | Owner | Exact? |
|---|---|---|---|
| World time | the integer tick | `Simulation` | exact |
| Body time | drive drift, mental fatigue, sleep pressure, reflex latency | the agent substrate, fed the true world dt | exact |
| Perceived time | durations, order, time of day as the NPC believes them | modelled senses | coarse, biased, noisy |

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
- **Per-NPC seeded streams,** keyed by stable identity: `SeedSequence(root, spawn_key=(NS_AGENT, npc_key,
  stream_key))`, never `spawn()`; the World's generator under `(NS_WORLD,)`. The host derives them from the log
  header's root seed (foundations DR-S4, Wire S3).
- **Integer microseconds** in `data/agents/`; rates are integer divisors of the tick with a per-actor phase.
- **The membrane is the clock translator (BF-11).** Today `RegionSensor` stamps world seconds and Maxim's sensors
  stamp epoch seconds. Until OD-C2 and OD-A2 land, each field's clock is documented, and the mismatch is an
  OPEN divergence with a red gate (foundations Wire S10: v2 named the wrong items). Under k reflex substeps, the
  injected clock advances exactly by the stepped dts (foundations Wire S1).

### 7.4 Thought cost: the interfaces only (O4)

- **A thought request** carries `kind` (from the closed vocabulary of `data/agents/timing.yaml`, chosen before the
  call and never changed by a result), the modelled times, `cancel_on`, and its budget.
- **A thought result** arrives as `Reply` values: the host streams the model call itself, reads the speech field
  first, validates it per chunk, and stamps syllables in integer world microseconds below the tick, interruptible. Segment times are computed by the host from the cost model, never parsed from model output
  (foundations TB2-S5).
- **The host's `latency_policy`** is a host-only control: live play holds the floor once Maxim's turn-taking
  substrate exists (`npcs_and_sem.md` O11, O11a); until then, O16: it dilates in single-player and lands late and
  silently in co-op, with DLP-B2's fixes (the wait is a
  state on the simulation lane's inbox, dispatch by deadline, a wall ceiling that ends a thought as a logged
  `thought_failed`); `abandon` is the logged alternative (foundations Arch B2, TB2-B3).
- **The tick size** is decided in sim-clock, with `apply_us` already in the record.
- Phases, budgets, the cache, fatigue and every constant belong to part 2.

## 8. Maxim, content and experiments

### 8.1 Maxim through named adapters (B-2, rewritten; BF-3, X N-1)

- **Rule:** Maxim is imported only by named adapters, each declaring the Maxim surface it uses.

| Adapter | Package | Surface |
|---|---|---|
| SEM membrane | `engine.adapters.sem` | bodies, percepts, acts (`Entity`, `Modulator`, `SensorReading`, `ModulatorResult`, `AffordanceSchema`) |
| Agent stepping | `engine.adapters.agents` | host-called `step`, `think` and `settle`, the request/reply values (model calls run by the host, never injected into Maxim), the worker process, the tool-roster check, the per-agent home, clock and RNG injection, the experience driver, agent-state save (foundations Arch B3, DR-B2) |
| NPC authoring | game, when it exists | `AgentFactory`, seed memory, the arc loader |
| Experiment harness | `maxim_experiments` | the experiment and ledger tooling |

- **Enforced** by import-linter's `protected` contract on `maxim` (allowed importers listed; verified on 2.15 without
  pymaxim installed), plus a lint comparing each adapter's imported symbols against its declared list.
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

Display quantization (`crack`, `glow`, uint8, float16 temperature) moves to `engine.encoding` in the protocol PR.
The core is forbidden from importing it; `engine.adapters.sem` is too (§2.2).

### 8.4 Experiments (B-7; S10, BF-9)

- `maxim_experiments` imports only the engine and its own Apache-2.0 fixtures (a fixture body, event pool and
  scene). Neither the engine nor the game imports it.
- Experiments that need game content are game runs, which stay off Maxim's ledger.
- **A ledger record pins** the engine SHA, the pymaxim version, the membrane and agent contract versions (including
  any interim `neutral` behaviour, which is part of the treatment), the model profile, and the Phase 3 items present.
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

### 9.3 SEM refinement items (O5; foundations Arch S8, Wire S10, Wire S11, X-5, X-13, MP-B3)

Ids are roadmap Phase 3's `OD-` ids (its "Was" column maps the old A, B, C and SEM-plan S-ids). **Additive first, in
1.x:** under Maxim's own reading of CC3 (`AffordanceSchema`'s marker, `sem.py:113-116`), appending a field with a
default is non-breaking (precedents: `always_active` #403, `speech_param` #1261), and a rename follows the
alias-plus-deprecation precedent. Only `Modulator.execute`'s signature is a real break, and it can be opt-in. No
major version is proposed.

| Item | Roadmap | Path |
|---|---|---|
| The world clock: a machinery clock and a perceived-time port (planted-render test, prompt-module lint), keyed substreams, stamps, the de-duplication window, dispatch gates, ids, the stepped Default Network | OD-A1–OD-A9 | additive; robots default to the wall clock |
| The embeddable agent: entry point, closed tool roster, `AgentHome`, the request/reply cut, the stepped `think` and its continuation, the leak closure, the dispatch/settle split | OD-A10–OD-A15, OD-A17, OD-A18 | additive; the stepped `think` after 1.4.0 |
| Credit for effects measured later: receipts, the cerebellum at settle, exactly-once credit, `stale` and `call_error` kinds promoted through the bridge, a per-modulator valence default | OD-A16 | an amendment to `tool_failure_credit.md` |
| Drive drift states its time base | OD-C1 | additive; optional rename with an alias |
| `SensorReading.timestamp` is the body clock | OD-C2 | additive |
| A declared direction per affordance (`acts_on`, trailing, defaulted) | OD-C3 | additive |
| The acting entity reaches `execute`, opt-in (`accepts_actor`) | OD-C4 | additive only because opt-in (MP-S12) |
| `ModulatorResult.settles`, trailing, defaulted | OD-C5 | additive |
| Reserved membrane metadata keys (BF-10): metadata can't overwrite `success` | OD-C6 | additive |
| `ModulatorResult` and `SensorReading` are not mutated (§5.1; freezing deferred) | OD-C7 | additive |
| Percepts and instruments, shrunk: instruments are in-world objects | OD-C8 | additive |
| A version rule for the SEM vocabulary on `ENTITY_FORMAT_VERSION` | OD-C9 | additive |
| `world_set_axis` for sub-sensors | OD-C10 | additive (unverified) |
| A mental-fatigue drive that rises with load; `CouplingSpec` can't carry it | OD-B12 | tier B, earned by OD-X2 |
| The `x or time.time()` bug at five sites; the pickle-capable load; the stale `ARCHITECTURE.md:182`; the redaction question (a private advisory; its own security issue) | OD-I1, OD-I3, OD-I4, OD-I5 | issues now; OD-I2 (a missing CC3 note on `ModulatorResult`) is a docstring nit |

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
  exists from 3a, holding only `data.py`, against §2.1; §3's ban covers `logging` too.
- **As built in 3b(a) (2026-11-20):** a frame holds the read-only owners, which no window writes in place, so it
  needs no copy, but it pins a whole grid (about 100 MB at 5×10⁶ cells; one pinned per agent is a B5
  row). Stamped by sequence and `time_s` until the tick. A cell window copies all four channels
  twice in every build, even unchanged (O8's switch can't reach the core); a sources-only window
  copies none but still publishes. `place` opens it too (marked for 5a; `imagine` has no intent kind). The
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
  streams from one root seed", `tests/test_determinism.py::NUMPY_RANDOM_ALLOWED` admits `Philox`, and the replay
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
- **Stale refusals** stay an OPEN divergence until Maxim promotes a `stale` refusal kind (OD-A16)
  (§7.2). Roadmap Phase 3's exit now requires OD-A16 before Phase 4 (`npcs_and_sem.md` §12.1 asks the owner to confirm).
- **Slow-effect credit** stays OPEN until settle carries a horizon (OD-A16).
- **Memory writes** are ungated until generate vs apply (OD-A18) and the host's `settle`; memory authority is OPEN until per-agent homes and
  pickle-free persistence land.
- **Two clocks into Maxim** stay an OPEN divergence until OD-C2 and OD-A2 (§7.3).
- **The game's rule seam is data only** (§2.1); a game that needs a new mechanism brings it to the engine.
- **BLAS in the core** is forbidden rather than policed; the first solver that needs it reopens this (§3).
- **The perceiver half of B-13** waits for the first NPC body (Phase 4).

## Fold table: the v1 review (`reviews/boundaries/`)

Every v1 BLOCKER and SHOULD-FIX, as folded in v2. **Three v2 folds were revised in v3** after the foundations review
found them not achieved or overtaken: D-B4 (v2's flag-toggling window failed; v3's ownership window, §4.1), D-S8 (v2
left lanes §4.2's arrival order standing; v3 states one key, §6.2), and Arch B1 / BF-1 (v2's mode (a); superseded by O6,
§7.2).

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

v1 coverage: 18 of 18 BLOCKERs and 52 of 52 SHOULD-FIXes folded in v2, three of them revised in v3 (above), and the
gate-registry fold (Arch B2, TB-B1, X-2) made mechanical in v3 (foundations Arch S15). NITs folded where they touched a
section: Arch N1–N8; BF-12 to BF-15; D-N1 to D-N3, D-N5; X N-1 to N-3; TB-N1 to N-4; W10 to W14. D-N4 (drive
determinism tests from the golden log, by kind) is deferred to sim-clock, where the golden log is born.

## Fold table: the foundations review (`reviews/foundations_v1/`)

Every foundations BLOCKER and SHOULD-FIX that touches this design. Status is **folded** (with the section),
**partial** (what is missing), or **elsewhere** (the document that owns it). Findings that touch only part 2 are in
`npcs_and_sem.md`'s fold table; those that touch only the Maxim drafts or roadmap Phase 3 are the drafts' fold.

| Finding | Severity | Status |
|---|---|---|
| Arch B1 the agent lane is defined nowhere | BLOCKER | folded: §7.1 (one owner per agent, the barrier); lanes §4.1 superseded in part 2 §11.1 |
| Arch B2 mode (a) + dilation deadlock | BLOCKER | folded: O6 drops mode (a); §7.2, §7.4 (DLP-B2's fixes) |
| Arch B3 `AgentPort` isn't the thought seam | BLOCKER | folded: §7.1 (port split, gateway) *(superseded by `npcs_and_sem.md` O6a and v3.1 §6.6: one host-called port; intents return in `StepOutput`; the gateway is the host's thinking lane)* |
| Arch S1 sibling layers aren't independent | SHOULD-FIX | folded: §2.2 sub-layers 5a/5b, 7a/7b/7c |
| Arch S2 restricted importers need what's forbidden; writers outside the core | SHOULD-FIX | folded: §2.2 skip-layer rule (stage-2 checks, `entity_key` in checks, save split, `ActionLimits.load` in loaders) |
| Arch S3 `to_maxim_entity` takes `World` | SHOULD-FIX | folded: §7.1 |
| Arch S4 frames can mutate; thread scope; cadence | SHOULD-FIX | folded: §4.1 (thread scope), §4.2 (copies, cadence) |
| Arch S5 agent foundations have no PR; the marker can't come out | SHOULD-FIX | folded: §6.4, §11.1 (`phase1/agents`); world_model §10 |
| Arch S6 `memory_write` in the world log | SHOULD-FIX | folded: §6.1 |
| Arch S7 the log record lacks the sub-tick key | SHOULD-FIX | folded: §6.2 (`apply_us`, one key) |
| Arch S8 SEM paths disagree; two items have no home | SHOULD-FIX | folded: §9.3, §5.1 (OD-C6, OD-C7) |
| Arch S11 no seam for game rules | SHOULD-FIX | folded: §2.1 (data only) |
| Arch S12 calibrations leave the resolution gate | SHOULD-FIX | folded: §8.2 |
| Arch S13 credit for slow effects; instruments | SHOULD-FIX | folded: §7.2 (OPEN with a red gate; declared sensors) |
| Arch S15 the registry check overstated | SHOULD-FIX | folded: §5.2 (mechanical rule, four plants) |
| X-1 the tripwire can't see what it claims | BLOCKER | folded here: §3 (profile hook); the world-clock draft's tripwire is the drafts' fold |
| X-2 [now] claims false with real Maxim | BLOCKER | folded: §7.3 (strict red gates until tier A) |
| X-5 CC3 misquoted | SHOULD-FIX | folded: §9.3 |
| X-12 schema, prompt, protected tests | SHOULD-FIX | folded: §7.3, §8.1, §10 |
| X-13 additive disagreement | SHOULD-FIX | folded: §9.3 |
| Wire B1 the window and frames before `Simulation` | BLOCKER | folded: §4.1, §11.1 |
| Wire B2 mode (a) can't reach the pipeline | BLOCKER | folded: O6; §7.1 (intent sink as a required port) *(superseded by `npcs_and_sem.md` O6a and v3.1 §6.6: one host-called port; intents return in `StepOutput`; the gateway is the host's thinking lane)* |
| Wire B3 no Maxim thought entry point | BLOCKER | folded: §7.1, §8.1 (the gateway) *(superseded by `npcs_and_sem.md` O6a and v3.1 §6.6: one host-called port; intents return in `StepOutput`; the gateway is the host's thinking lane)* |
| Wire S1 three time inputs, no invariant | SHOULD-FIX | folded: §7.3 |
| Wire S3 the seed path; CLAUDE.md drift | SHOULD-FIX | folded: §7.3, §11.2 |
| Wire S4 record fields and kinds | SHOULD-FIX | folded: §6.1, §6.2 |
| Wire S5 speech has no wire | SHOULD-FIX | folded: §6.1, §6.2 (`speak`); detail in part 2 §5.2 |
| Wire S6 which frame; leaks | SHOULD-FIX | folded: §4.2, §4.4 |
| Wire S7 dilation has no channel | SHOULD-FIX | folded: §6.3 |
| Wire S8 the header misses inputs | SHOULD-FIX | folded: §6.3 |
| Wire S9 the cache is unregistered | SHOULD-FIX | folded: §5.3 |
| Wire S10 stale Phase 3 ids | SHOULD-FIX | folded: OD- ids throughout (§4.3, §5.3, §7, §8.1, §9.3, §13) |
| Wire S11 §9.3 vs the SEM plan | SHOULD-FIX | folded: §9.3 |
| Wire S12 settle double credit | SHOULD-FIX | folded: §7.2 |
| DR-B1 agent code races the tick | BLOCKER | folded: §7.1 (barrier) |
| DR-B2 the host doesn't own the LLM call | BLOCKER | folded: §7.1, §8.1 |
| DR-B3 the cache isn't canonical | BLOCKER | folded: §5.3 (gate); the key in part 2 §4.8 |
| DR-B4 the v1 D-B4 fold doesn't hold | BLOCKER | folded: §4.1 (ownership window, the unlock-then-close proof) |
| DR-B5 throughput is the wrong bound | BLOCKER | elsewhere: part 2 §4.5 (boundaries carries no throughput claim) |
| DR-S1 Δt invariance vs bits | SHOULD-FIX | folded: §7.1 (`dt_ticks` from the schedule); detail in part 2 §2.1 |
| DR-S2 sub-tick units and field | SHOULD-FIX | folded: §6.2 |
| DR-S3 three ordering keys | SHOULD-FIX | folded: §6.2 |
| DR-S4 Philox stability | SHOULD-FIX | folded: §7.3 |
| DR-S5 agents share module state | SHOULD-FIX | folded: §7.1 (one real agent per process); the exit test is the drafts' |
| DR-S6 the dial test can't fail | SHOULD-FIX | folded: §7.3 |
| DR-S7 replay reproduces the world only | SHOULD-FIX | folded: §6.2, §6.3 (tiers, rerun manifest) |
| DR-S8 speech is world input | SHOULD-FIX | folded: §6.2 |
| DR-S9 unmeasured budgets | SHOULD-FIX | folded: §4.2 (frame copies, on change), §10 (barrier meters); remaining rows in part 2 |
| DR-S10 the agent adapter is unsealed | SHOULD-FIX | folded: §3 |
| DR-S11 machine-decided failures; policy changes | SHOULD-FIX | folded: §6.1, §6.2, §6.3 |
| TB2-B1 the NPC tool surface | BLOCKER | folded: §5.3 (roster gate) |
| TB2-B2 one shared home; pickle | BLOCKER | folded: §5.3 (homes gate-to-be), §7.1 |
| TB2-B3 thought budgets; liveness | BLOCKER | folded: §5.3, §6.1, §7.4 |
| TB2-S1 speech kind and gate | SHOULD-FIX | folded: §5.3, §6.1 |
| TB2-S2 the log excludes and includes LLM text | SHOULD-FIX | folded: §6.2 (per kind) |
| TB2-S3 the memory-write gate can't exist yet | SHOULD-FIX | folded: §5.3 (gate-to-be), §13 |
| TB2-S4 the cache is untrusted | SHOULD-FIX | folded: §5.3, §6.2 (replay never opens it) |
| TB2-S5 kind from model output | SHOULD-FIX | folded: §7.4 |
| TB2-S6 who stamps player ticks | SHOULD-FIX | folded: §4.2, §5.3 |
| TB2-S7 authority misses policy, requests, cancels | SHOULD-FIX | folded: §6.1 |
| TB2-S8 identity from the object called | SHOULD-FIX | folded: §5.3, §7.2 |
| TB2-S9 host data before tier A | SHOULD-FIX | partial: §5.4 (closed code vocabulary); the guest-session guard and LLM locality are owner questions in part 2 §12.1 |
| TB2-S10 in-process inputs from Maxim | SHOULD-FIX | folded: §5.2 |
| BF2-6 two meanings of instrument | SHOULD-FIX | folded: §4.4 |
| MP-B3 CC3 misread | BLOCKER | folded: §9.3 |
| MP-S12 the injected actor key isn't additive | SHOULD-FIX | folded: §9.3 |

NITs folded where they touched a section: Arch N1 (inline later is a future decision, §7.1); BF2-15 (§11.2).
