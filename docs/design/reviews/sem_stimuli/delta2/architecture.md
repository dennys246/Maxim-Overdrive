# Delta round 2: `sem_stimuli.md` v3, Architecture lens

At `phase1/sem-stimulus` **77e24bb**. I set these statuses myself, as a reviewer (O25), from the tree; the author's
`fold.md` claims were not taken as evidence. I edited no repository. My scratch plants are in
`_durable/sem_review_delta2/scratch_architecture/`.

**Statuses: 14 fixed, 1 open, 0 deferred, 0 rejected.** **New: 0 BLOCKER, 6 SHOULD-FIX, 3 NIT.**

**A correction to my own round first.** v3 copied my A2-N2 fix ("tissue reaches models through 5a's per-body point
container, a registered field") as I wrote it. That fix was underspecified: it gives tissue state a second home
beside `body/store.py`. See A3-S4.

## Status table

| Id | Status | Reason |
|---|---|---|
| A-B2 | fixed | §5: lanes per row keyed by `(name, derivation_version)`, never by dense id. Replay compares lanes whose key is unchanged and refuses only on a changed bound lane. Plants: an unbound add stays green, a bound bump goes red. Adding `sound_event` no longer touches the tissue lane. Residues: A3-S5 (what the key leaves out) and A3-N3 (site ids in the lane bytes) |
| A-S3 | fixed | §7.1: `contact.py` is the one owner. It writes skin through the store's window and the object through the solid law's exchange API, at step 3, against the solid's last published state, with one antisymmetric entry per substep. It is named as a fifth writer class, and 5a's note gets the two-rate seam. The cross-law half is closed. A body-internal residue (contact against tissue) is A3-S3 |
| A-S8 | fixed | §7.3: `AGENTS_SURFACE` is named, and a test asserts the forbidden list equals `_core_modules() − AGENTS_SURFACE` plus `adapters.sem.bridge`. Combined with Wire S4's `allow_indirect_imports = false`, though, the contract breaks on its first legitimate import: A3-S1 |
| A-S10 | **open** | Every format detail now has a step (§5, §11.1): the lints, the YAML digest and worker check, the save's body state, and the binding, `BoundFrame` and receipt versions with their gate rows. **Proposed deferral of the `foundations_plan.md` rows: rejected.** No pointer to §11.1 exists anywhere a 5a or 5b author reads. I grepped `foundations_plan.md`, `roadmap.md` and the tracker: only the D14 line and OD-I7 cite `sem_stimuli.md`. So the trigger ("the PR that opens 5a") depends on that author already knowing. The budget doesn't block the pointer. Row 5a's "a composition note" can become "a composition note (`sem_stimuli.md` §11.1)" by trimming three words elsewhere, or the tracker's **Next** cell can carry it (`long_term_features.md` is at 1,347 words). Missing: that pointer |
| A-S12 | fixed | Tracker: "units (ranges are Maxim's transduction)". §7.1 supersedes `boundaries.md` §2.2's map by name, with a layer per module. Some layer numbers are wrong, and nothing checks them: A3-S2 |
| A-N4 | fixed | §7.4: the exemption is narrowed to the binding loader, and the blind spots (receptor and unit literals, `spec.name` against a variable) are stated as review's |
| A2-S1 | fixed | §3.1, §7.3: instances and saved state go in `core/body/spec.py`. `CORE_PUBLIC_SURFACE` gains only `body.spec`, `stimuli.schema` and `stimuli.frame`. §7.3 says protection inside the core comes from `protected` and protection from adapters comes from skip-layer. Side effect: A3-N1 |
| A2-S2 | fixed | §7.4: `perceivable` defaults to false, completeness refuses a `reads` that names a non-perceivable field, material ids and table constants never are perceivable, and a change is a reviewed data change with a plant |
| A2-S3 | fixed | §3.2: a frozen `Binding` in `schema.py`, validated when `join` applies. An invalid table is a logged `agent_failed(build)` before any reduction, replay reads `join` through the same gate, and the worker keeps only the Maxim-side checks, listed |
| A2-S4 | fixed | §11.1: 5a reserves the log slots, the seams and the recursive module list. `schema.py`, `frame.py`, `reduce.py`, the contracts and the checks land with `tissue_temperature` |
| A2-N1 | fixed | §7.1: `reduce.py` is split out |
| A2-N2 | fixed (as asked) | §7.1 says it as I asked. What I asked was underspecified: A3-S4 |
| A2-N3 | fixed | §6.3 has one header row |
| A2-N4 | fixed | §7.3 states `protected`'s semantics and the narrowing by skip-layer, and a test checks that every allowed importer exists, which closes the misspelling hole |

## New findings

### SHOULD-FIX

#### A3-S1. `agents-reads-body-frames` with `allow_indirect_imports = false` breaks on the agents' own surface

`sem_stimuli.md::§7.3` (`agents-reads-body-frames`; `AGENTS_SURFACE` = `stimuli.schema`, `stimuli.frame`,
`intents`, `limits`, `checks`). `pyproject.toml` skip-layer and `membrane-reads-frames` (both `true`, lines 143,
158). `tests/test_tooling_config.py:279`.

- **The two folds collide.** The contract's forbidden list is every core module outside `AGENTS_SURFACE`, and from
  5a, `_core_modules()` is recursive, so the list holds `core.body.*`, `core.readonly`, the field registry and the
  rest. With indirect imports forbidden, every *chain* from `adapters.agents` into those modules is a violation.
- **The chains are built in.**
  - `stimuli.schema` validates that a binding's "sites lie in its site set and the body" (§3.2), so it needs
    `body.sites` or `body.spec`.
  - It shares "a closed unit vocabulary … with the field registry" (§2.1).
  - Its `StimulusModel` protocol names the field-reader type.
  - `frame.py` "refuses writable arrays, as `CellFrame` does", and the natural helper for that is `core.readonly`.
  - Today `intents`, `limits` and `checks` are closed: I checked their imports. `schema` and `frame` are not.
- **Verified on a toy package** (`scratch_architecture/pkg/`, import-linter 2.6): `agents.worker → stimuli.frame →
  core.readonly` is **BROKEN** with `false` and **KEPT** with `true`. In 2.6 `forbidden` defaults to `false`
  (`forbidden.py:47`), so Wire S4's fold only states the default, and that default is what every existing contract
  in this repo turns off.
- **Failure scenario.** The tissue row's PR lands `schema.py` importing `body.spec`. The contract goes red on the
  worker's first `from simcore.core.stimuli.schema import Binding`. The easy ways out are to add `body.spec`,
  `body.sites`, `readonly` and the registry to `AGENTS_SURFACE`, which opens their direct import to the worker, or
  to flip the setting to `true`. Either is a band-aid chosen under a red gate.
- **Fix.** Keep `allow_indirect_imports = true`, matching the repo's convention for surface contracts. Bound the
  closure with a test instead:
  - `closure = ⋃ graph.find_upstream_modules(m) for m in AGENTS_SURFACE`;
  - assert `closure − AGENTS_SURFACE ⊆ PLAIN_DATA`, where `PLAIN_DATA` is a named set of stateless modules
    (`readonly`, `body.spec`, `body.sites`, the unit vocabulary);
  - assert `PLAIN_DATA` holds no stateful module (`body.store`, `tissue`, `irradiance`, `contact`, `world`, `grid`).
  - Plant: `schema.py` importing `body.store` goes red.
- **Verified:** I ran `grimp` 3.13's `find_upstream_modules` on the toy and it returns the transitive imports
  (`closure.py`). The full test itself is unverified.

#### A3-S2. `core/body` spans layers 2–4, and no contract holds any of v3's intra-core layer numbers

`§7.1` (spec, geometry, sites at 2; store at 3; irradiance, contact, tissue at 4; stimuli at 5); `boundaries.md::§2.2`
(the package and layer cuts agree (S5); "siblings on one line are independent"; 5b `engine.intents` holds
"receipts"); `pyproject.toml` (no contract inside the core: only `layers` over the four top packages).

- **Nothing checks the numbers.** No contract orders modules inside `simcore.core`. So `spec.py` importing
  `store.py` (a `SavedState.from_store` helper, say) passes every contract. Skip-layer is direct-only (`true`), so
  a loader that imports `body.spec` then reaches the store through it unseen. A2-S1's fix rests on `spec` staying
  plain data, and nothing holds `spec` to that.
- **One number is wrong.** `BoundFrame.receipts` carries `Receipt` (§4.2), which lives in intents (layer 5b).
  So `stimuli` must sit above 5b, not at a bare "5" beside 5a and 5b.
- **Another is doubtful.** `store.py`, at 3 beside cells, has "its own write window". If it reuses the cells'
  window machinery, it sits above cells, not beside them.
- **Failure scenario.** In 5b, `spec.py` grows an import of `store`. Every contract stays green. The loader, which
  is allowed `body.spec`, now reaches the store's write window through it.
- **Fix.**
  - Add an import-linter `layers` contract with `containers = ["simcore.core.body"]`, for example
    `layers = ["contact", "tissue | irradiance", "store", "spec | geometry | sites"]`. `contact` sits above
    `tissue` if A3-S3's split holds. Land it with `store.py` in 5b.
  - Add the same contract for `simcore.core.stimuli`: models above `registry | reduce`, above `frame`, above
    `schema`.
  - Restate stimuli as 5c, above intents.
- **Verified** on a toy (`layers_containers.sh`, import-linter 2.6): `spec → store` goes BROKEN, the clean package is
  KEPT, and `tissue → contact`, siblings under `|`, goes BROKEN.

#### A3-S3. Touched skin has two step owners, and §7.2's per-point substep claim contradicts §2.3's joint solve

`§2.3` (contact: "one implicit system per touched object over the skin and an object-side sub-mesh refined to the
substep's penetration depth"; "error-controlled substeps per point, from the point's own state"), `§7.1` (`tissue.py`
owns "columns, … sub-columns, substeps"; `contact.py` owns "the joint skin–object solve"), `§7.2` ("contact solves per
connected component (one object and its skins)"; "a point's substeps depend only on its own state").

- **Two owners for one column.** A touched sub-column's nodes are unknowns in `contact.py`'s implicit system and
  also in `tissue.py`'s column stepper. Nothing says which steps them, or whose substep controller sets the time
  grid. The sub-mesh is "refined to *the substep's* penetration depth", and the design never says whose substep.
- **The time grid can't stay per point.** A joint system over a component (a palm and three fingertips on one rail,
  or two NPCs' hands on it, since a component is "one object and its skins") needs one time grid. So a touched
  point's substeps depend on its component, not only on its own state. §7.2's batch-invariance sentence is false for
  touched points, and T11's "batch-minimum dt" plant would flag the honest implementation.
- **Failure scenario.** The implementer writes `tissue.py`'s per-point controller as specified, and `contact.py`
  solves the joint system on its own grid. Within one tick a fingertip's column is advanced twice, once by each.
  Or it is advanced once, by whichever runs last, and the other's exchange is lost. The `bodies` ledger entry is
  still antisymmetric, because it books what `contact.py` computed. The writer scan stays green.
- **Fix.**
  - `tissue.py` exports the column operator (conduction, perfusion, outer boundary) and a per-point error estimate.
    It steps only untouched sub-columns.
  - `contact.py` composes those operators with the object sub-mesh, steps each touched component on one grid (the
    finest any of its points requests), and owns that grid.
  - Restate §7.2: "an untouched point's substeps depend only on its own state; a touched point's depend on its
    contact component, which is world state, so B's hand reaches A only physically".
  - Order the two inside step 3.
- **Not verified:** this is a design split. I didn't run it.

#### A3-S4. Tissue state has two homes: `body/store.py` and "5a's per-body point container" (my A2-N2 fix)

`§7.1` (`store.py` holds "pose, core node, tissue and visibility state"; "Tissue reaches models only through the
`FieldReader`, over 5a's per-body point container, a perceivable field"); `§5` ("The save holds all carried
`core/body` state: tissue…"); `world_v2.md::§2.5` (each registry field declares its container and "whether it is
saved or derived"; "`MaterialGrid` holds fields from the registry").

- **The registry would hold the state, or a copy of it.** Under `world_v2` §2.5, a registered field's storage is
  held by the registry's owner, and its save status is declared there. v3 also puts tissue in the store, with its
  own window, and saves it as body state.
- **Either way one rule breaks.**
  - Two arrays need a copy step that appears nowhere in the tick (§4.1) and has no writer class.
  - Or the registry's container *is* the store, and nothing says so.
  - The save then has two routes, the registry's saved flag and §5's body-state list. Nothing stops them
    disagreeing.
- **Failure scenario.** 5a builds the point container in `MaterialGrid`, since that is where registry fields live.
  5b's store holds tissue too. `tissue.py` writes the store. A sync line is added in `Simulation.step` after step 3.
  The save stores both, and a load restores one, so the models read stale tissue for the first tick after a load.
  The save–load test plants only "an omitted reference pose", so it misses this.
- **Fix.** One home. `body/store.py` implements the registry's `body_points` container kind: it registers its tissue
  arrays as fields, and the `FieldReader` opens read-only views of the store's arrays, with no copy. Save status
  comes from the registry entry, and §5's list cites it. Plant for the save–load test: a store field marked
  `derived` that is in fact carried. **Not verified.**

#### A3-S5. Lane keys omit the laws that produce a row's inputs, so D13 can load silently past a body-law change

`§5` (lanes keyed by `(name, derivation_version)`; the `BoundFrame` lane "per NPC"; D13 "an agent home records only
its bound rows"), `§2.1` (`pooling` and `receptors` are non-identity), `§7.1` (the body laws in `core/body/`, outside
any row).

- **Where a value comes from.** `tissue_temperature`'s value is a function of its model's version and of
  `tissue.py`, `irradiance.py` and `contact.py`, which carry no version anywhere in the header (§5 lists row
  versions and truth constants). A bound value also depends on `reduce.py` and the class pooling, which §2.1 makes
  non-identity.
- **Failure scenario.** A fix to `irradiance.py`'s occluder test changes flux only behind partial cover. No replay
  golden covers that case, so nobody bumps `tissue_temperature`'s `derivation_version`, and nothing makes them. An
  agent home trained on the old law records `(tissue_temperature, 1)`. It loads under D13 with no refusal, and its
  input distribution has shifted. That is the silent path D13 exists to close. Where a golden does cover the case,
  the lane goes red as an "unchanged-key mismatch", reported as nondeterminism rather than as a law change.
- **Fix.** Derive the key and don't hand-maintain it. The lane key is `(name, derivation_version, producers)`.
  `producers` is the sorted `(law, version)` set of the laws that step the fields in the row's `reads`; the
  registry already declares "the process that steps it", which only needs a version. Give the bound lane the key
  `(npc_key, bindings_digest, reduce_version, pooling per class, bound row keys)`. D13 records those keys. A
  completeness check computes them, so no human has to remember the graph. Plant: bump a producer's version alone,
  and a bound home refuses. **Not verified.**

#### A3-S6. `body-protected` lands too late, its allowed importers miss the applier, and the store's writers are unclassified

`§7.3` ("each contract lands with its first importer"; `body-protected` allowed: "`Simulation`'s module, …"),
`§11.1` (5b lands `store.py`; "the protected contracts" land with `tissue_temperature`), `§4.5` (posture, gaze and
breathing are intent kinds), `§7.1` (only contact is named as a new writer class); `boundaries.md::§2.2` (layer 6 holds
"the intent applier" and "the frame publisher" beside `Simulation`), `§6.4`. Today `core/applier.py` is a separate
module.

- **The contract lands late.** The two sections contradict each other. `core.body`'s first importer is 5b's
  `Simulation`, but §11.1 lands the contract with the tissue row, so the store's write window sits unprotected
  inside the core for the whole gap.
- **The allowed importers are too few.** `move`/`move_to` (tile §3) and v3's posture, gaze and breathing intents are
  applied by the applier. The frame publisher must put poses in `Frame` for the client. Neither is "`Simulation`'s
  module". When the contract lands, the applier's `body.store` import breaks it, or moves get rerouted through
  `Simulation` as a workaround.
- **The store has five writer kinds, and §6.4 knows one.** Construction and load, motion (step 2), the applier
  (posture, gaze, breath), `tissue.py`, `irradiance.py` (visibility refresh) and `contact.py` all write it. §6.4
  gains only contact.
- **Fix.**
  - Land `body-protected` in 5b, with `store.py`.
  - Name its allowed importers as layer 6's modules (`Simulation`, the applier, the frame publisher), checked by
    the exists test.
  - Give the store's window a writer allowlist and a scan like `tests/test_ownership.py`, with every writer above
    as a row in §6.4.

### NIT

- **A3-N1** `§7.3` and `tests/test_tooling_config.py:271`. `MEMBRANE_SURFACE = CORE_PUBLIC_SURFACE − {materials,
  world}`, so adding `body.spec`, `stimuli.schema` and `stimuli.frame` to the public surface silently opens them to
  the SEM membrane, which has no use for `BodyFrame` (D1's one route). Subtract them explicitly, and say so in §7.3.
- **A3-N2** `§4.2`, `§4.3`, `§5`, `§7.1`. The per-NPC pending-event buffer and the coalescing counters are carried
  state, saved as "body state", but no module in §7.1 owns them. The store sits at layer 3 and can't hold
  `StimulusEvent` (layer 5), and `run.py` is stated as order and handout only. Name a home, for example
  `core/stimuli/events.py`, owned and saved by layer 6, and save it as stimulus state.
- **A3-N3** `§5` (lane bytes `(npc_key, site, value)`). Say that `site` is the index within the row's site set for
  that body, never a body-wide dense id. Otherwise a new site set added for a new row renumbers `skin`, and the
  tissue lane changes, which is A-B2's failure again at a smaller scale.

## What I checked

- v3 in full; my delta-1 report; `fold.md`'s Architecture and Wire S4 rows.
- `pyproject.toml`'s contracts.
- `tests/test_tooling_config.py:253-288`.
- `boundaries.md` §2.2, §6.3 and §6.4; `world_v2.md` §2.5; `foundations_plan.md` rows 5a and 5b (2,500 words);
  `long_term_features.md`'s SEM stimulus rows; the roadmap's diff on this branch; tile §3's movement intents.
- The imports of `core/intents.py`, `limits.py`, `checks.py`, `frames.py`, `applier.py` and `world.py`.
- import-linter 2.6 and grimp 3.13 in the `fire-research` venv, with the toy plants above.
- I didn't rerun the author's scratch measurements. None of them bears on this lens.

## What holds up

- The lanes fix the shape of the round-1 BLOCKER.
- `contact.py` gives the cross-law exchange one owner.
- Bindings are validated in the core.
- The frozen types are deferred until they have a caller.
- The `perceivable` flag fails closed.

The remaining risk is in the contracts' mechanics (A3-S1, A3-S2, A3-S6) and in three ownership seams (A3-S3, A3-S4,
A3-N2). In each, the design states the rule, and the means of enforcing it is missing or contradicts the rule.
