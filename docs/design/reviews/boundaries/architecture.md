# Design review: boundaries, Architecture lens

- **Lens:** Architecture (root cause or band-aid, right layer and owner, standing rules, honest docs)
- **Design under review:** `docs/design/boundaries.md` at 47add00
- **Code tested against:** `.worktrees/act-validation/src/maxim_overdrive/` at 2f200b5
- **Date:** 2026-11-16
- **Counts:** 2 BLOCKER, 12 SHOULD-FIX, 8 NIT

## What was checked

The import graph of every module in `src/` at 2f200b5, set against the B-8 stack:

| Module | Imports (in-package) | B-8 layer | Consistent? |
|---|---|---|---|
| `checks` | none | 1 | yes |
| `config` | `checks` | 1 | only if `checks` and `config` are *not* independent siblings (N1) |
| `world.grid` | `config` (`AIR_ID`, `MaterialTable`, **`RigProfile`**) | 2 | by the stack yes; by D20 no (S1) |
| `world.heat` | `world.grid` | 3 | yes |
| `world.damage` | `checks`, `config`, `world.grid` | 3 | yes |
| `world.scene` | `checks`, `config`, `world.grid` | 4 | yes. **scene does not import heat or damage** |
| `imagination.spec` | `checks`, `world.grid`, **`world.scene`** | 4 | breaks the stated rule "a layer imports only layers below it" (N1) |
| `world.world` | `checks`, `config`, `world.heat`, `world.damage`, `world.grid`, `world.scene` | 5 | yes. **world does not import sem_env** |
| `sem_env.bridge` | `checks`, `config`, **`world.damage`**, `world.grid`, `world.world`, `maxim` (try/`TYPE_CHECKING`) | 6 | allowed by layers; it is the second door B-9 forbids (S2) |
| `maxim_overdrive/__init__` | `config`, `world.grid`, `world.scene`, `world.world` | root | outside the layers |

So today's code fits the stack, with two exceptions in how the rule is written (N1), and one dependency the stack
blesses that the world model removes (S1). Future modules were checked against the stack in S3, S5 and S6. Also read:
`StructureModulator.execute`/`apply`, `RegionSensor.value`, `imagination.spec.place`, `World.advance`/`from_scene`,
`snapshot`, `config.data_dir`, the AST scan in `tests/test_determinism.py`, `pyproject.toml`'s wheel mapping, and
`docs/maxim_upstream/exp64_*`.

## BLOCKER

### B1. `boundaries.md` §B-9 :: "execute becomes a producer of intents" breaks `StructureModulator.execute`'s result contract, and the design doesn't say what replaces it

- **Today:** `sem_env.bridge::StructureModulator.execute` returns a `ModulatorResult` synchronously, and that result
  carries the outcome:
  - `success` reports what happened in the world: `extinguish` fails with "nothing is burning", and a strike fails
    with "the crate is gone";
  - the metadata carries `destroyed_volume_m3` and `absorbed_j`, measured by `damage.strike` as it runs.
- **Under B-9:** the intent is logged and applied at a tick boundary by the simulation lane, after `execute` has
  already returned. So `execute` can return only one of two things:
  - **"queued".** Then `ModulatorResult.success` changes meaning, from "it happened" to "it was accepted". That is
    Maxim's frozen type (CLAUDE.md: "Don't add fields Maxim doesn't have"), and Maxim's orchestrator reads the result
    as the outcome of the act.
  - **The real outcome.** Then the thinking lane blocks on the simulation lane until the intent's tick runs. That
    couples the lanes and puts wall-clock latency into when an NPC learns what it did.
- **Failure scenario:** sim-clock implements B-9 as written. An NPC calls `extinguish` on a crate whose fire went out
  in the same tick. `execute` returns `success=True` ("queued"), the intent is then refused at apply time, and the
  NPC's memory records a successful extinguish that never happened. Or, the other way, `execute` blocks, and a replay
  of the thinking lane depends on scheduling.
- **Why it's a BLOCKER:**
  - B-9 is presented as a boundary, but it is really a change to an external contract.
  - Choosing between the two options either needs a Maxim change (a Phase 3 item, with its pushback), or it is a
    lanes decision that part 2 (`npcs_and_sem.md`) owns.
  - Landing B-9 in sim-clock without that decision means the boundary gets built first and the contract chosen by
    accident later.
- **Fix:** keep B-9's rule ("one log, one validator, both actors"). Drop "execute becomes a producer of intents" from
  this document, and defer how `execute` and its result behave to part 2, as a named open question. If the answer
  changes what `ModulatorResult` means, list it under Phase 3 as a Maxim proposal.

### B2. `boundaries.md` §Enforcement, row B-4 :: the gate lint can't see the real door that exists today

- **The check:** "every public function taking a `Mapping` or `object` parameter is a listed gate or its private
  helper".
- **The real entry point for untrusted NPC and LLM input today** is `sem_env.bridge::StructureModulator.execute(self,
  affordance: str, params: dict[str, Any])`:
  - its annotations are `str` and `dict[str, Any]`, neither `Mapping` nor `object`;
  - it isn't in B-4's list (only `parse_action` is).
- **The loaders take a path, not a mapping:** `RigProfile.load(name_or_path: str | Path)`, `MaterialTable.load(path:
  str | Path | None)` and `ActionLimits.load`. So every future file gate the design names (save, scene-v1, intent
  log) is invisible to the lint as well.
- **Failure scenario:** `phase1/protocol` adds `def handle(self, raw: bytes)` or `def on_intent(self, msg: dict[str,
  Any])`. The lint passes, and the design's claim that "listing the gates makes 'there are no other doors'
  checkable" is false on day one. A check that can't fail on the case it exists for is a BLOCKER under the charter.
- **Fix:** key the check on where data comes from, not on parameter annotations. Two options:
  - an allowlist of the modules that may call `yaml.*`, `json.*`, `Path.read_*`/`open`, or receive transport bytes
    (an import-linter forbidden contract on `yaml` and `json` outside the gate modules does most of this);
  - or annotate gates explicitly (a decorator or a `GATES` registry), with a test that every public callable
    reachable from the protocol, the bridge and the loaders is registered.

## SHOULD-FIX

### S1. `boundaries.md` §B-8 and §Further candidates :: the boundary D20 is about is missing, and B-8 blesses the dependency D20 removes

- **The design leaves out:** the rendering tier never reaches the truth.
- **What the world model says:** `world_model.md` D20 and §1.1 say rigs become rendering tiers only.
- **What the code does today:** the rig decides physics in the core:
  - `world.grid::MaterialGrid.empty` takes `rig.cell_size_m`;
  - `world.world::World.advance` takes `self.rig.min_substeps_per_turn`;
  - `world.scene::Scene.build(rig, …)` voxelizes per rig.
- **B-8 makes it permanent:** it puts `config` (which holds `RigProfile`) at layer 1, under everything. The layers
  contract would then pass with grid → `RigProfile` forever.
- **Why this one boundary matters:** every resolution finding in PR 1's eight rounds traces to it (world_model §1.1,
  "why this is the root fix").
- **Failure scenario:** sim-clock introduces the 0.1 m truth constant but leaves `World.rig` in place for "min
  substeps". A laptop and a max client then step with different substep counts, and nothing in the gate notices.
- **Fix:**
  - split `config` into physical configuration (the truth resolution, materials) and presentation (`RigProfile`, as a
    rendering tier);
  - add a forbidden contract: the core may not import the rendering tier;
  - land it in `phase1/boundaries`, so sim-clock is born inside it.

### S2. `boundaries.md` §B-8 / §B-9 :: layers allow skipping layers, so the SEM membrane may call the laws directly, and does today

- **What the bridge does today:**
  - `sem_env.bridge::StructureModulator._strike` calls `damage.strike(self._world.grid, …)`;
  - `_ignite` and `apply` mutate `self._world.sources`, a public dict.
- **What B-8 allows:** `sem_env` (layer 6) may import any lower layer, including the laws (3) and the grid (2). So the
  contract blesses exactly the "second way in" that B-9 forbids.
- **B-9 is checked only at runtime:** "a test that every cell write … happens under `World.advance` or intent
  application". A runtime test sees only the paths the tests drive.
- **Failure scenario:** a protocol handler imports `world.damage` for a debug "smash" command. The layers contract
  passes, and the runtime test passes because no test drives that command.
- **Fix:** add a forbidden contract alongside the layers. `sem_env`, the protocol and the host may import only the
  `Simulation`'s public surface (intents in, published observations out), never `world.grid`, `world.heat`,
  `world.damage` or `world.scene` directly. Make `World.sources` private behind an intent.

### S3. `boundaries.md` §B-4 / §B-9 :: the one intent gate has no home that both producers can reach

- **The conflict:**
  - B-9 wants players and NPCs validated by the same gate;
  - B-4 lists that gate as `sem_env.bridge::parse_action`;
  - B-8 puts `sem_env` and the protocol side by side in layer 6.
- **Failure scenario:** `phase1/protocol` needs `parse_action`. Either it imports `sem_env`, so the player server
  depends on the Maxim membrane and its optional `maxim` import, and the siblings are coupled; or it copies the
  validator, which gives two gates that drift.
- **Fix:** move the action vocabulary, `parse_action`, the typed actions and `ActionLimits` into an `intents` module
  at layer 5, or lower, beside the `Simulation` that applies them. Both `sem_env` and the protocol then call down to
  it. Say this in the design, and land the move in `phase1/boundaries`, since it is a rename-sized move.

### S4. `boundaries.md` §B-3 :: the sealed set is an allowlist ("the core is `maxim_world.world`"), which is narrower than today's check, and the two banned lists will drift

- **Today's check is wider.** `tests/test_determinism.py::BANNED_MODULES` scans the whole package except `server/`
  (`NOT_SIMULATION = {"server"}`): deny by default.
- **B-3 is narrower.** It seals only `world`. That leaves out `sem_env` (which mutates `World.sources` and calls
  `damage.strike`) and `imagination` (`spec.place` paints cells). Both write simulation state, and both would be
  allowed `time` and `uuid` under B-3.
- **The two lists already differ.** The scan bans `timeit`, and B-3 doesn't. B-3 bans `threading`, `asyncio`,
  `socket` and `websockets`, and the scan doesn't.
- **Failure scenario:** someone adds `metadata={"at": time.monotonic()}` to a bridge result. Today's scan catches it.
  If the scan is reduced to "what imports can't show" (B-3's wording), and B-3 covers only `world`, nothing does. The
  value then reaches a `ModulatorResult` that the intent log records.
- **Fix:**
  - define the sealed set as everything except an explicit list of non-simulation packages (host, transport,
    thinking lane), which is the scan's existing shape;
  - keep one banned-module list, read by both the import-linter config and the AST scan, or have a test assert that
    they are equal;
  - rename `NOT_SIMULATION`'s `server` to the `host` name together with B-8.

### S5. `boundaries.md` §B-8 :: geometry in metres has no layer, and the fuel laws will need it from above

- **What the world model requires:** the laws in layer 3 decide from geometry in metres:
  - world_model §3: ignition from "the pilot's footprint in metres", breach by "remaining thickness in metres";
  - §5: region CSG answers "does this fire touch the region".
- **Where that geometry lives today:** split between `world.grid` (`Footprint`, `Bounds`, `Point`) and `world.scene`
  (`Box`, `Cylinder`, `footprint_of`, `boxes_overlap`), which is layer 4.
- **Failure scenario:** `phase1/fuel-surface` needs `footprint_of` and the CSG in `fuel.py` (layer 3). It must import
  `world.scene` (layer 4), so the layers contract goes red. The author then either moves `fuel` up a layer, so a law
  sits above the authoring layer, or copies the geometry.
- **Why the rename PR is the time to fix it:** the `world` package currently spans layers 2, 3, 4 and 5. That is a
  sign the package cut and the layer cut disagree, and `phase1/boundaries` touches every import anyway.
- **Fix:** add a `geometry` layer (primitives, CSG and footprints in metres; no cells) at layer 2, beside or below
  `grid`. Re-home the modules by layer (for example `cells/`, `geometry/`, `laws/`, `sim/`) in the same rename.

### S6. `boundaries.md` §B-10 :: read-only views are the wrong mechanism once there are lanes, and they miss today's actual leak

- **Read-only views still change underneath the reader.** A `writeable=False` view of a live array changes whenever
  the world advances. Under the lanes (world_model §10, PR 10), a thinking-lane reader holding such a view sees a torn
  state mid-step.
- **They aren't a lock either.** A view of an array whose base is writeable can have `writeable=True` set back.
- **The world model already chose a better mechanism:** region reductions are "published once per physics step as a
  frozen object" (§9).
- **Today's leak isn't the snapshot.** `world.world::snapshot` already returns fresh arrays (`.copy()` and
  `astype`). The live reads are `sem_env.bridge::RegionSensor.value` (`self._world.grid.temperature[mask]`, every
  call) and the public mutable surface: `World.grid`, `World.sources`, `MaterialGrid.paint` and `name_region`.
- **Failure scenario:** in the lanes PR, a sensor reads `grid.temperature` while the simulation lane is mid-substep.
  The read-only flag doesn't help, and the reading is from no tick.
- **Fix:** restate B-10 as "observation reads only published, immutable per-step snapshots; nothing outside the
  simulation lane holds a reference to `World` or `MaterialGrid`". Enforce it with S2's import contract plus a test
  that sensors read from the published object. Drop the `writeable=False` work on the snapshot, which already copies.

### S7. `boundaries.md` §B-11 :: "defined once, as a versioned schema file" conflicts with world_model §8 "the code's registry and loaders are authoritative"

- **Two sources of truth.** World_model §8 makes the in-code field registry authoritative: embedded copies are
  compared against it, never executed. B-11 makes a schema file authoritative.
- **Failure scenario:** a channel is added to the registry and not to the schema file, or the reverse. Which one does
  the catalogue hash in `welcome` cover? The decoder refuses frames whose hash differs (§8), so one of the two silently
  becomes decorative.
- **Fix:** say which one is primary. The natural choice is that the registry generates the schema as an exported,
  committed artifact, with a golden test that regenerating it gives the same bytes. The GDScript parser is then
  tested against that artifact and the golden frames.

### S8. `boundaries.md` §B-1 :: the split trigger mixes a need with a date, and `client/` isn't cut at all

- **The trigger.** "A second game or an outside developer wants the engine, or at the Phase 1 exit, whichever comes
  first."
  - "Phase 1 exit" is not a reason to split. Phase 2 (rubble, collapse, adaptive refinement, per D21 and D22) changes
    the engine and the game together, so a split there turns every feature into two coordinated PRs across repos,
    with protocol and version pinning between them.
  - The trigger should be a need: an outside consumer, or a measured pattern (for example, most engine PRs touching
    no game files over a stated period).
- **The client.** B-1 assigns "the Godot game client's content" to the game. But the frame decoder and the parser
  from B-11 are engine, and the design doesn't cut `client/` into an engine addon and game content.
- **Failure scenario:** at a split, the GDScript decoder, which is engine wire code, is in the game repo. The engine
  repo then has no second reader for its own grammar, which is the reason PR 6 builds one.
- **Fix:** drop the date from the trigger, or justify it. Add `client/` to B-1's table (for example
  `client/addons/<engine>/` for the decoder and channel bindings, and `client/game/` for content).

### S9. `boundaries.md` §B-1 / §B-5 :: the engine reaches game data through default file paths, which import-linter cannot see

- **Defaults today:**
  - `config::data_dir()` and `MaterialTable.load(path=None)` default to `_data/materials/core.yaml`;
  - `World.from_scene(materials=None)` calls `MaterialTable.load()` inside the core.
- **After B-5:** the calibrations (`degrade_*`, fracture energy) become content under `content/`. So either the
  engine's defaults point into game content (an engine → game dependency carried by a string), or the engine loses
  data its own tests need.
- **Other game tuning B-5 doesn't place:** `data/world/actions.yaml` (ActionLimits values), the action vocabulary
  (`strike`, `ignite`, `extinguish`), and the LLM-facing affordance descriptions in `StructureModulator.affordances`.
- **Failure scenario:** at the repo split, the engine's `test_damage` loads fracture energy from rights-reserved
  content it no longer has. Or, the other way, the Apache engine wheel ships the game's calibrations, because
  `force-include "data" = "maxim_overdrive/_data"` is attached to the engine wholesale (§Migration, Packaging).
- **Fix:**
  - remove the data defaults from the core: `materials` becomes a required keyword-only parameter (CLAUDE.md, "push
    invariants into types");
  - engine tests use Apache-licensed fixture tables under `tests/`;
  - state for each `data/` file whether it is engine or content;
  - say what the engine's own `_data` holds after the split.

### S10. `boundaries.md` §B-7 :: the harness has no package, and the contract doesn't say who may import whom

- **The gap.** B-7 forbids `maxim_overdrive` from importing "the harness", but doesn't say where the harness lives.
  `docs/maxim_upstream/exp64_cradle_conduct_prereg_DRAFT.md` needs "a probe harness that offers the same SEM
  affordances on every turn", and cradle runs use game scenes and NPC authoring.
  - In the engine, it can't import game content (B-1).
  - In the game, it is the game.
  - As a third package, it needs its own row in B-1 and B-8.
- **Failure scenario:** the first experiment needs the lab tile. It is put in `maxim_overdrive.experiments` "for
  now", where B-7's contract can't apply, because a package may import its own children.
- **Fix:** name a third top-level package (say `maxim_experiments`) that may import engine and game, and that neither
  may import. Note also that B-1 lists "the verification harness" as engine. Distinguish the two harnesses by name.

### S11. `boundaries.md` §B-9 "Lands" :: other doors, and an unmarked band-aid

- **The test would fail on legitimate writes.** "Every cell write … under `World.advance` or intent application"
  would fail on several writes the design doesn't list:
  - `imagination.spec::place` (paints cells; the CLAUDE.md-mandated entry for imagined objects, and an NPC's imagined
    object is an NPC path);
  - `world.scene::Scene.build`;
  - the save loader;
  - `StructureModulator.apply`, public and callable with a typed action, which skips `execute`'s target checks.
- **Imagination needs a decision.** The design must say whether imagination becomes an intent. It should, since it
  is NPC output.
- **The band-aid is unmarked.** "Today `StructureModulator.apply` writes cells directly, which is acceptable only
  until the log exists" is a scheduled band-aid. CLAUDE.md requires a `TEMPORARY(phase1/sim-clock): …` marker in the
  code and a roadmap row, and this design provides neither.
- **Failure scenario:** sim-clock writes the cell-write test, finds three writers that aren't intents, and exempts
  them one at a time, which is exactly the "special case" band-aid the standards forbid.
- **Fix:**
  - list every cell writer and classify each one: construction (`build`, load), intent application, or `advance`;
  - make imagination an intent kind;
  - make `apply` private to intent application;
  - add the marker and the roadmap row now, in `phase1/boundaries`.

### S12. `boundaries.md` §Migration :: the order disagrees with world_model §10, and the roadmap

- **The claim.** "Lands after PR 1 and before `phase1/sim-clock`, so sim-clock's new modules are born inside the
  boundaries."
- **The conflict.** World_model §10 puts `phase1/verify`, a new harness package, between PR 1 and sim-clock, and
  doesn't list `phase1/boundaries` at all. Neither does `docs/roadmap.md`.
- **Failure scenario:** verify is built first, under `maxim_overdrive/verify/`. The rename then moves it, and its
  layer placement is decided after it exists, which is the exact cost the "Why now" section argues against.
- **Fix:** put `phase1/boundaries` as PR 2.5 (before verify) in world_model §10 and in the roadmap, and place the
  verification harness in the B-8 stack (it sits above `Simulation`, beside the host).

## NIT

- **N1. `boundaries.md` §B-8 :: the stack as written is red on day one.**
  - `config` imports `checks` (both layer 1), and `imagination.spec` imports `world.scene` (both layer 4), which
    breaks "a layer imports only layers below it".
  - In import-linter syntax, `a | b` siblings are independent by default.
  - Fix: either make `checks` and `scene` their own lower layers, or declare the siblings non-independent (`:`) and
    reword the rule.
- **N2. `boundaries.md` §B-3 :: two parts of the list don't belong in an import contract.**
  - `maxim` repeats B-2, since B-2 already forbids it everywhere but `sem_env`.
  - `os.urandom` isn't a module, so import-linter can't express it. Today it is held only by the AST scan's
    `os.urandom` rule, and the enforcement table should say so.
- **N3. Q1 :: the engine name `maxim_world` names the engine after the one dependency B-2 says is swappable.**
  - It also reads as part of Maxim's namespace, next to `maxim`/pymaxim.
  - Recommendation: a Maxim-neutral engine name.
- **N4. `boundaries.md` §Migration, "mechanically" :: the rename isn't purely mechanical.** These strings are seen
  outside the code:
  - `to_maxim_entity`'s `metadata={"source": "maxim_overdrive.sem_env"}` is a string Maxim sees;
  - the `pip install 'maxim-overdrive[maxim]'` message;
  - the `MAXIM_OVERDRIVE_*` environment variables;
  - the `_data` path.
  
  Each is a vocabulary or operator-surface contract. List them, and decide whether each follows the engine's or the
  game's name.
- **N5. `boundaries.md` §B-12 :: half of the contract can't fail.** `tests` and `scripts` aren't packages in the
  import graph, so "src never imports tests/scripts" can't go red the way the design says it will be proven. Keep the
  external `pytest`/`hypothesis` half, which can fail.
- **N6. `boundaries.md` §B-6 / §B-10 :: both move or flag `snapshot`, in different PRs.** Do one. With S6, the
  snapshot already copies, and B-6's move to the encoding layer is the only change it needs.
- **N7. `boundaries.md` §B-3 :: the design doesn't say where dilation is measured.** World_model §1.2's "the tick
  status reports the effective time scale" needs a wall clock. Say that it is measured in the host and enters the
  `Simulation` only as recorded data, so that nobody "fixes" it later by exempting `Simulation` from B-3.
- **N8. `boundaries.md` §B-4 :: "inside a gate, code takes typed, frozen objects" doesn't hold today.**
  `MaterialGrid`, `World` and `MaterialTable` are mutable and cross the gates. Scope the claim to values crossing a
  gate (actions, specs, profiles), or say which mutable types are exempt and why.

## Verdict on each boundary

| Boundary | Right cut? | Note |
|---|---|---|
| B-1 engine/game | Yes, but under-specified | data defaults (S9), client (S8), trigger (S8) |
| B-2 Maxim membrane | Yes, holds today | cheapest and most valuable contract here |
| B-3 sealed sim | Right idea, wrong set | deny by default, one list (S4) |
| B-4 named gates | Right idea, check is wrong | BLOCKER B2; the gate's home (S3) |
| B-5 content | Right, materials only | action limits and vocabulary unplaced (S9) |
| B-6 presentation | Right, timing fine | N6 |
| B-7 experiments | Right, no home yet | S10 |
| B-8 layers | Right shape, missing layers | rendering tier (S1), geometry (S5), skip-layers (S2), N1 |
| B-9 one door | Right rule, wrong mechanism stated | BLOCKER B1; doors and marker (S11) |
| B-10 read-only | Wrong mechanism | published snapshots (S6) |
| B-11 one schema | Right, conflicts with §8 | S7 |
| B-12 tests out | Half vacuous | N5 |

**Boundaries this design should add:**
- the rendering tier never reaches the truth (S1);
- the `Simulation`'s public surface is the only way in for the bridge, protocol and host (S2);
- a shared `intents` layer below both producers (S3);
- a `geometry`-in-metres layer below the laws (S5);
- the engine never reads game data by a default path (S9);
- a named experiments package (S10).
