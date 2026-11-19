# Future flexibility: code and architecture (2026-11-18)

Reviewer: code and architecture lens, one of three. Read: this worktree's `src/`, `tests/`, `data/`, `scripts/`;
`origin/phase1/act-validation`'s `config.py`, `checks.py`, `scene.py`, `world.py`, `sem_env/bridge.py` and tests (the
code the merge line brings in); `phase1/standards:CLAUDE.md`; `boundaries.md`, `world_model.md`, `world_v2.md` (as
the record v3 points back to), `tile_and_client.md` §4, §5, §7, §11; `foundations_plan.md` §2; `checklists.md`.

The question: what makes later change expensive, and what is the cheapest thing to do now or in the first code steps.

## Ranked table

| # | Risk | Future cost if left | Likelihood | Action now | Owning step | Action cost |
|---|---|---|---|---|---|---|
| 1 | **The solver loop belongs to heat.** `heat.py::step` owns substep scheduling, the stability bound, source refresh and the topology-change rule. Every other law joins it as a callback (`world.py::World.advance` passes `on_substep=damage.thermal_degrade`, whose `int` return means "topology changed") | Step 6 adds four laws (6a–6d) plus skins and a ledger. Each one either becomes another callback in `heat.step` or forces the loop to be rewritten in the middle of step 6. Phase 2 (zones, gas, sound, light, phase change) repeats the cost per law | Certain: step 6 has four laws, and the roadmap has at least five more | Step 5's `Simulation` owns the physics step. It holds a **static, ordered tuple** of laws under one small protocol: `stable_dt(state)`, `step(state, dt, ledger)`. The step uses the minimum stable dt. Topology change comes from `topology_version`, not from return values. No discovery and no plugins | 5 (sim-clock) | About 150 lines and half a day, while `heat.step` is being rewritten for ticks anyway |
| 2 | **The field registry has no owner.** v2 put "the registry for today's fields driving the digest" in sim-clock (`world_v2.md` §11 row 3). v3 dropped it from that row (`world_model.md` §10 row 4), and neither plan step 5 nor `checklists.md` names it. Yet `world_model.md` §7 and §8 (reserved channels, the face table), `boundaries.md` §9.1 ("the in-code field registry is primary"), `client_rendering.md` §4's catalogue and `npcs_and_sem.md` :656 all assume it exists. Today every consumer lists the fields by hand: the attributes of `grid.py::MaterialGrid`, `world.py::snapshot`, `tests/test_determinism.py::digest` | Step 6 adds skin temperatures, fuel fraction and char. A field missing from `digest` is invisible to the determinism gate, so the gate can't fail for it. Step 7 then freezes a wire grammar against a hand-written channel list, and step 9's save does the same again | High. It is the same failure as the caches v2 dropped and v3 had to restore (`world_model.md` §9) | Add to step 5's checklist: an in-code `FIELDS` declaration (name, location cell/face/zone, dtype, units, saved or derived, channel and quantization, required). `MaterialGrid` storage, `digest`, `snapshot` and the memory budget iterate it. Settle that it lives in code, not in v2's `data/world/fields.yaml` | 5, before 6 and 7 | About a day |
| 3 | **The rig still decides physics.** `grid.py::MaterialGrid.empty(rig)` takes `rig.cell_size_m`. `scene.py::Scene.build(rig, …)`, `World.rig`, and `World.advance` takes `rig.min_substeps_per_turn`. The physics tests run through the `rig`/`rigs` fixtures in `tests/conftest.py` (173 references in `src/` and `tests/` here). Act-validation commits `tests/fixtures/formats/v0/rig.yaml` with physics fields | D20 turns rigs into rendering tiers. If step 3a reads "no behaviour change" as "keep the `rig` parameter", steps 4 and 5 each re-plumb resolution through every builder and test | High. The core ↛ `tiers` contract (`boundaries.md` §2.2, S1) can't pass otherwise, so 3a must do it, but the plan doesn't say so | In 3a, replace the `rig` argument with a truth parameter, `dx_m` (keyword-only), with substeps derived from stability and the physics step. Tests parametrize over grid spacings (0.2, 0.1, 0.05), not over rig names. `RigProfile` moves to `tiers` with no physics fields. **Retire** rig format v0 with a loud version refusal; don't write a migration | 3a | Mechanical; the same diff 3a already owes |
| 4 | **The verification harness is planned against a clock that step 5 replaces.** Step 4 comes before step 5. Today's entry point is `World.advance(seconds)` with `turn_seconds=6.0` and float `elapsed` accumulation (`heat.py::step`). Step 5 brings integer ticks and a 0.5 s physics step (T3) | A harness built on `World` is rewritten in step 5, and every law's convergence test with it | Medium-high. The plan's first action for step 4 is "the harness", with no stated API | The harness drives **laws on a state**, never `World`, with explicit `dx`, `dt` and step count, because space and time are refined separately, which is step 4's own requirement. It ships two helpers, `converges(scenario, grids, tol)` and `band_gate(scenario, inputs)`. `tests/test_cross_tier.py` is ported onto them. Each new law then needs a scenario, a closed form and one call | 4 | Small if written into the step's checklist now |
| 5 | **No kernel seam for performance work.** `heat.py::substep` and `stable_dt` rebuild `_face_conductances` (`np.take` copies) on every substep and read `grid.materials` lookups inside the hot path. Transients peak at 412 MB at 0.05 m (`world_model.md` §9). `world.py::sphere_overlap` samples 64× the whole grid per source | A numba or C backend later means rewriting the callers, because kernels take a `MaterialGrid` rather than arrays | Medium. Caching is already planned for step 5; numba isn't planned at all | Use step 5's caching to split each law into `prepare(state)` (re-run on `topology_version`) and a **pure-array kernel** with `out=` buffers and no object access. Add one bit-identity parity test template per kernel. **Don't add numba now**: it would need the banned list and AST scan extended, a fastmath and threads policy (as BLAS needs, `boundaries.md` §3), and a profile showing it is needed | 5 | Folded into caching work already planned |
| 6 | **`Simulation` heading for a god object.** `World` is small today (`world.py::World`: grid, rig, sources, turn, `_power_field`, `advance`). Tile §7 puts actor and pilots tables, motion, the walk grid, A\*, body heat, the bed, the laws, intents, receipts and `Frame` in the core. `boundaries.md` §2.2 layer 6 adds the clock, the applier, construction, the frame publisher and `AgentPort` | The 12-public-method and 40-line tripwires (`phase1/standards:CLAUDE.md`) force ad hoc splits mid-step, cut by line count rather than by concern | High: the step 5 checklist alone lists about ten responsibilities | Step 5 opens with a half-page composition note. `Simulation` composes `CellState`, `BodyState`, `Ledger`, `Clock` and `IntentLog`. `step()` is a short list of named stages. The applier and the laws are module functions over that state | 5 | An hour of design |
| 7 | **Loaders are uniform in checks but hand-rolled per format.** Act-validation's `config.py::MaterialTable.load` names each property four times: the `Material` field, `MATERIAL_REQUIRED`/`OPTIONAL`, the load body and the `__init__` lookup arrays. Its comment says a test holds the four together. `scene.py::Scene.from_dict` dispatches on `kind` by if-chain | Tile §5.1 adds about ten constants with provenance. Scene v1, archetypes, items, `actions.yaml` v1 and `data/agents/` each need a reader plus "every rejection path tested" (3b's done-when). That is about half a day of boilerplate and a bespoke rejection-test file per format | Certain: 3b and 6 add five or more formats | In 3b, one declarative schema per format (field → converter from `checks`, units, required, provenance tag) and one reader that applies it. `MaterialTable`'s per-id arrays are generated from the schema. One parametrized test feeds every schema field missing, unknown, NaN, bool and wrong-type values | 3b | About a day; repaid by the second format |
| 8 | **Sensors are if-chains per quantity.** `sem_env/bridge.py::RegionSensor`'s `_UNITS`, `reading_schema` and `value` | Each Phase 2 perceivable (sound level, light, gas) edits three branches in the membrane. The planned move to a `bincount` reduction published per frame (`world_model.md` §9) rewrites them anyway | Medium | When 3a splits the bridge, quantities become a table (quantity → field, reducer, unit, range), later derived from #2's registry | 3a, then 5 | A couple of hours |
| 9 | **The write window is built on `World.advance` in 3b, then moved to `Simulation.step` in 5** (`boundaries.md` §4.1, TEMPORARY markers) | Known, marked rework | Certain, already accepted | Keep 3b's window a thin wrapper, so step 5's move is a re-parenting. Nothing more | 3b | None extra |

## Why #1 and #2 lead

**#1.** Read today's `heat.py::step`. Its docstring has to explain damage's needs: destroyed cells change both the
stability bound and where sources deposit. That is the heat module knowing another law's consequences. D25 laws
couple through exactly this. The skin needs the heat field. The bed's pyrolysis needs skin flux. Char oxidation feeds
heat. The ledger needs every law's terms. If the loop stays in heat, each coupling becomes another keyword argument.

The fix is small and needs no framework. The physics step is a fixed sequence of operator-split laws. Each law
reports its ledger terms, its stability bound and nothing else. The order lives in one tuple that review can read.
This is also what lets a future law be added by appending to that tuple, while engine-code review still applies
(`boundaries.md` §2.1: a new law is engine code, never game data).

**#2.** It is a plan gap, not a design gap. Every v3 document assumes the registry, and no step builds it. Step 7 is
the protocol freeze ("generic grammar from the first fixture"). Without a registry in place by step 5, step 7 either
builds it under deadline or freezes a hand-listed channel set into golden fixtures. Unpicking golden fixtures later
costs a migration or a version bump per change (CLAUDE.md, "Every format is versioned").

## Plan order: where it forces rework

- **3a then 4 then 5:** both risks are covered by #3 and #4 above. The short version: make resolution and time
  explicit parameters at 3a, and the step-4 harness never sees `World`.
- **Step 5 is overloaded.** It carries `Simulation`, the integer tick, the 0.1 m truth, the intent log, bodies,
  motion, A\*, body heat with radiation, vocabulary v1, the Frame rule, caches, `set_material`, `region_id`, and (per
  #1, #2, #5, #6) the law seam, the registry and the kernels. Recommend splitting it at a real seam: **5a** the
  simulation spine (clock, `Simulation` composition, law tuple, registry, `region_id`, caches, kernels), and **5b**
  bodies and movement (actor and pilots tables, walk grid, A\*, body heat, `move`/`move_to`, vocabulary v1). 5b sits
  entirely on top of 5a, and each half is reviewable on its own.
- **Act-validation's code isn't in this worktree.** This branch's `config.py` has no `known_keys` and no format
  versions. Any flexibility work done here before the merge line lands (step 1) is built on the wrong base. None
  should be.

## Over-engineering the plan would be better without

- **`boundaries.md` §2.2's twelve-row layer table and its skip-layer contracts, as written.** O24 decided three or
  four layers and keeps the table only as a map of expected splits. §10 still asks for contracts "proven by a planted
  import, including modules that don't exist yet". For 3a: ship O24's layers (core, adapters, game, client protocol),
  the core banned list, core ↛ `tiers`, and `maxim` only in the adapters. Add each finer contract when its module is
  born. This follows O24, and it narrows §10's text, which predates O24.
- **A migration for rig format v0.** Under D20 it is a dead format. Refuse it by version.
- **v2's `data/world/fields.yaml`.** A YAML registry would put the state layout under data control, adding another
  gate with no user. In code, as `boundaries.md` §9.1 already says.
- **A law registry with discovery** (entry points, decorators, registration by import). A static tuple is enough.
  Import-time registration would also defeat the "order committed and reviewed" property.
- **`memory_budget_mb` per rig** (v2 §2.5). Rigs no longer hold state, so the budget belongs to the tile at the truth
  resolution plus the verification grids.
- **numba or C now** (#5): not until a profile says so. The seam costs almost nothing; the backend does.

## Conflicts with owner decisions

- The 5a/5b split doesn't conflict with any decision. It changes plan step 5's row, which is the owner's call.
- The over-engineering note on §2.2 and §10 follows O24. It conflicts only with §10's pre-O24 wording.
- #3 is consistent with D20 and the plan's "no behaviour change" for 3a, provided the tests pass today's spacings
  explicitly, so that results stay bit-identical.

## Not risks

- Material ids as `uint8` with air at id 0: a fixed, stated limit; the loader refuses over 255.
- `imagination/spec.py::place` going through `Scene.from_dict`: one door, already the pattern step 5's `imagine`
  intent needs.
- `scipy` in the core (`damage.py`): explicitly allowed by `boundaries.md` §3.
