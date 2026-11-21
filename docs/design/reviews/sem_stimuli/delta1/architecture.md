# Delta round 1: `sem_stimuli.md` v2, Architecture lens

At `phase1/sem-stimulus` **3e97ac9**. Reviewer-set statuses (O25), read from the tree. No repository edited.

**Statuses: 14 fixed, 6 open, 0 deferred, 0 rejected.** **New: 0 BLOCKER, 4 SHOULD-FIX, 4 NIT.** A-B2 stays open
at BLOCKER weight: its replay half is still broken (below).

## What I checked

- v2 in full; my round-1 report; `fold.md`'s Architecture rows.
- `pyproject.toml` `skip-layer`, `membrane-reads-frames`, `maxim-through-adapters`; `tests/test_tooling_config.py`
  lines 250–288 (`_core_modules`, `CORE_PUBLIC_SURFACE`, `MEMBRANE_SURFACE`, both surface tests).
- `boundaries.md` §2.2 (layer map) and §6.4 (every writer, classified); `world_v2.md` §2.5–§2.6;
  `foundations_plan.md` rows 5a, 5b, 6; `long_term_features.md`'s SEM stimulus rows (on this branch).
- **import-linter 2.6 source** (`importlinter/contracts/protected.py`, `domain/helpers.py`, in the `fire-research`
  venv): an allowed importer may import **every** descendant of a protected package, since the check subtracts
  `allowed_modules` per protected descendant with no per-submodule scoping; an unborn, non-wildcard allowed importer
  resolves to nothing, with no error.

## Status table

| Id | Status | Reason |
|---|---|---|
| A-B1 | fixed | §7.3 makes both packages `protected` (fail closed); a models import allowlist; `_core_modules` recursive in 5a with `__init__` classified; `PLANTED` rows. Combined with the recursive skip-layer test, adapters are confined to the classified surface. Residues are N1 and N4 below |
| A-B2 | **open** | The agent-home half is fixed (rule 5, D13). The replay half is not: §5's digest covers every body's full `BodyFrame` with ids from sorted names, so adding any row or swapping an unbound row's law changes every log's digest chain. "Replay refuses only on a changed row some NPC in the log bound" is false as specified. See below |
| A-S1 | fixed | §2.1: `receptors`, `pooling`, `tag` are non-identity; closing a tag bumps `derivation_version`; T14 requires receptors |
| A-S2 | fixed | `core/body/irradiance.py` named, flux internal, costed in §8, kernel B5 rows via §7.2. Its contact half is carried under A-S3 |
| A-S3 | **open** | Items 1 and 3 handed to 5a (§7.1). Item 2, the tissue–solid contact coupling, has two homes and no order or writer class. See below |
| A-S4 | fixed | §4.2: `BodyFrameFeed` beside `Frame`, keyed by `npc_key`, `FrameView` never reaches it; §4.2's cadence stands |
| A-S5 | fixed | §3.2, §5: the core reduces and digests; only bound values cross. The binding checks are now on the wrong side of that move: N3 |
| A-S6 | fixed | D1 ruled option (a): one route |
| A-S7 | fixed | §7.1: runner keeps order and handout; no due-set under D5 (c); cutoffs per row; refresh in irradiance; cache dropped; assembly in `frame.py` |
| A-S8 | **open** | The contract exists, but it is a hand-written denylist with no surface test. Round 1's fix asked for classification against the surface sets, as `test_the_membrane_contract_leaves_it_frames_the_applier_and_the_intents_only` does for the membrane. Without it, a module later added to `CORE_PUBLIC_SURFACE` (5a's field registry, say) reaches the agents adapter silently. Missing: an `AGENTS_SURFACE` set and a test that the forbidden list equals `_core_modules() - AGENTS_SURFACE` plus the named adapters |
| A-S9 | fixed | §6.1 splits `region_parts`; modulators stay; the lab builder's location is `phase1/agents`' call (§11.1) |
| A-S10 | **open** | Proposed deferral accepted **for each format's detail**, trigger: the PR of the step §11.1 names. Rejected for what §11.1 leaves unassigned: the §7.4 lints (completeness, no central switch, BLAS ban, constructor-site scan, models allowlist test) have no step; the Maxim-format body YAML's digest and worker check have none; the save format's new tissue, visibility and pending-event state has none; the binding format's version, gate row and fixtures are not stated (only "format and loader"). `foundations_plan.md` rows 5a and 5b don't mention the work v2 gives them |
| A-S11 | fixed | §4.5: posture, gaze and breathing are logged intents; default breathing for inert NPCs |
| A-S12 | **open** | Items 1, 2, 5, 6 named (§3.3, §3.1, §6.1, §7.1). Item 3: the tracker still says "in what units **and ranges**" (`long_term_features.md`, SEM stimulus **Contract** row), against §2.1. Item 4: `boundaries.md` §2.2's layer map is not amended or named: `core/stimuli` sits between layers 4 and 6, and `core/body` spans 2 (geometry), 3 (store, its own write window) and 4 (tissue, irradiance) |
| A-N1 | fixed | §7.2: digests and ids sort by name |
| A-N2 | fixed | §4.2: constructor-site scan (its step: A-S10) |
| A-N3 | fixed | §4.2: the core owns `tick`; the worker checks it rises and drops it |
| A-N4 | **open** | §7.4 lists exemptions, but exempts all of `adapters/agents`, the module most likely to grow `if sensor == "tissue_temperature"`. The worker maps bindings by order (§4.2), so it needs no row names. The lint's blind spots (receptor and unit literals, `spec.name` against a variable) are still unstated. Narrow the exemption to the binding loader and say what the lint can't see |
| A-N5 | fixed | §7.1: the protocol lives in `schema.py` |
| A-N6 | fixed | §4.3 rules it: a world bug stops the server loudly, with tick and NPC |

## A-B2, the open half: the digest makes every row a breaking change for replay

`sem_stimuli.md::§5` ("The digest", "The header", rules 2, 3, 5), `§4.2` (`BodyFrame.stimulus_id`, "Ids come from
sorted names").

- **What v2 records.** The per-tick digest is over "every body's canonical `BodyFrame` and `BoundFrame` values",
  chained, and stored in the log. A `BodyFrame` holds every row's value at every site in its site set (§0: the core
  builds the frame, *then* reduces it by bindings). Ids are dense indices from sorted names.
- **What that does to the rules.**
  - Rule 3 (adding a row is non-breaking): `sound_event` adds values to every `BodyFrame` and renumbers every row
    that sorts after it. Every recorded chain mismatches at tick 0.
  - Rule 2 on an unbound row: bumping `contact_pressure`'s law changes every `BodyFrame` digest, though no NPC binds
    it.
  - §5's save rule ("frames are recomputed on load and must match the digest") fails the same way.
- **Failure scenario.** Phase 2 lands `sound_event`. Every committed replay golden from Phase 1, which is the
  regression suite and the save format's backbone (CLAUDE.md "Replays are first-class"), goes red. The usual
  response is to regenerate them, which deletes the evidence the goldens exist to hold. The law/contract split is
  again enforced in the wrong place, the round-1 BLOCKER's exact shape, moved from the header to the digest.
- **Fix.** Digest per row, in lanes keyed by `(name, derivation_version)`, never by dense id: each lane chains its
  own canonical `(npc_key, site, value)` values; `BoundFrame` values form one more lane per NPC. The header records
  the lanes. Replay compares the lanes whose key is unchanged between the log and the current registry, refuses only
  if a changed lane is one some NPC in the log bound, and reports the skipped lanes. Dense ids stay a wire and
  in-memory matter. Plant: add an unbound row and require the replay to stay green; bump a bound row and require red.

## A-S3, the open item: contact has two homes, no order and no writer class

`§2.4` (contact: "one implicit system over the object's surface nodes and the skin at the tissue substep, its heat
booked out of the object's inventory"), `§7.1` (irradiance owns "contact coupling"; tissue owns "columns,
sub-columns, substeps"), against `boundaries.md::§6.4`.

- **Two homes.** One implicit system spans the skin nodes, which `tissue.py` steps, and the object's surface nodes,
  which the solid law (6.1, `fire_solid.md` §3.2) owns. §7.1 puts it in `irradiance.py`, a radiative module, while
  §2.4 runs it "at the tissue substep". Whichever module holds it, that module solves part of another law's state.
- **A writer `boundaries.md` §6.4 doesn't have.** The table lists four writer classes: construction, intent
  application, "the laws in `advance`" and the strike. The contact solve writes the object's nodes every 0.1 s tick
  at step 3, between physics steps and outside them. That is a fifth class, and it means the world's write window
  opens every tick, not only at physics steps.
- **Failure scenario.** At implementation, `tissue.py` imports the solid store to write its nodes, and the solid law
  integrates the same nodes at 0.5 s. The two rates double-count or drop the exchange. The writer scan is green,
  because both writers are in the core.
- **Fix.** Name one owner: a `core/body/contact.py` coupling law. It owns the joint solve, writes the skin through
  the body store's window and the object's surface through the solid law's own exchange API, and books one
  antisymmetric `bodies` ↔ object ledger entry per substep. Name its place in the tick: step 3, after the solid's
  last published state is held. Add it to `boundaries.md` §6.4 as a per-tick law writer. Keep `irradiance.py`
  radiative.

## New findings

### SHOULD-FIX

#### A2-S1. `body-protected` refuses the 5b body-instance loader and the save decoder

`sem_stimuli.md::§7.3` (`body-protected`: "the composition and `core.stimuli`"), `§11.1` (5b: "the body-instance
format (strict loader …)"), `§5` ("The save: tissue, visibility and pending events"); `boundaries.md::§2.2` (layer
7a: loaders hold "the save's decoding half").

- The strict loader is a file gate in `simcore.adapters.loaders` (CLAUDE.md: "Only the file gates read input"). It
  must build or hand over a body instance whose type lives in `core/body/geometry.py`. The save's decoding half,
  also a loader, must hand tissue and visibility state to the store's construction half.
- Neither the loaders nor the protocol are allowed importers of `simcore.core.body`. So as written, step 5b's own
  loader breaks the contract on its first import.
- Making `simcore.adapters.loaders` an allowed importer opens all of `core.body`, store and tissue included. I
  verified that `protected` has no per-submodule scope.
- **Fix.** Put the body instance and the saved-state record in one plain-data module (`core/body/spec.py`: frozen,
  validated where made, no state). Allow `simcore.adapters` as an importer of `core.body`, and add `spec` to
  `CORE_PUBLIC_SURFACE`. The recursive skip-layer test then forbids every other `core.body` module to adapters.
  State that the protection *inside* the core comes from `body-protected` and the protection from adapters comes
  from skip-layer classification. `stimuli-protected` has the same shape (A2-N4).

#### A2-S2. The models allowlist gates imports, not fields: a model may still declare `reads: material`

`§7.3` (models allowlist), `§7.4` ("Honest reads"), `§6.3` T5; `world_v2.md::§2.5` (the field registry declares
every field `MaterialGrid` holds).

- Round 1's point 3 was that the leak-relevant state must be unreachable. v2 closes the import route: models import
  only `schema`, the field-reader type, `body.geometry`, `body.sites`, `checks`. But the `FieldReader` opens
  registered fields, and honest reads only proves a model opened *exactly what it declared*.
- **Failure scenario.** A smoke-irritant model declares `reads = ("material", "temperature")` to pick an irritant
  per material id. Completeness, honest reads and the allowlist are all green. T5 catches it only if its canonical
  scene happens to contain that material pair before any thermal event.
- **Fix.** Fail closed at the field level: each field registry entry gets a `perceivable` flag, default false. The
  completeness check refuses any `reads` naming a non-perceivable field. Material ids and table constants are never
  perceivable, and making a field perceivable is a reviewed data change with a planted test.

#### A2-S3. The core reduces bindings that only the worker checks, and the binding type has no core home

`§3.2` ("The core reduces … in fixed order"; "Build checks"), `§7.1` ("Binding check, push | `adapters/agents/`
(worker)"), `§5` ("binding tables ride their `join` records"), `§11.1` (`phase1/agents`: "the binding format and
loader").

- Since A-S5's fold, the core consumes the binding table every tick. But §7.1 still runs all build checks in the
  worker: row exists, sites in the set, `single` has one site, no mean across depths, pooling by class. So the core
  can reduce, and digest, an invalid binding for ticks before the worker refuses it at `agent_ready`.
  - §4.5 says a refused NPC is "built and digested, not sent", so the digest chain carries reductions over a
    binding the system declared invalid.
- **Layering.** The core can't import a binding type defined in `adapters/agents`.
- **The checks split into two kinds.**
  - World-side: row, site membership, `single`, depths, pooling by receptor class. These need only the registry and
    the body.
  - Maxim-side: unit string against the Maxim sensor's unit, and a mean bound to a pain path. These need Maxim's
    body YAML.
- **Fix.** A frozen `Binding` spec in `core/stimuli/schema.py`, validated where made, at `join`. The core refuses an
  invalid binding before the first reduction, and `join` logs the refusal. The worker keeps only the Maxim-side
  checks. Say which check runs where.

#### A2-S4. Step 5a lands `stimuli/schema.py` and `frame.py` with no caller until "before Phase 4"

`§11.1` (5a: "`stimuli/schema.py`, `frame.py`"; "before Phase 4": the first model and law); CLAUDE.md "A fix ships
with a caller"; `foundations_plan.md` row 5a (no stimulus work listed).

- With no model, `STIMULI` is empty. The feed publishes empty frames each tick, and the frozen `BodyFrame` layout
  ships about a year before its only consumer, Phase 4 (after mid-2027). The tests can only check an empty tuple.
- Any change the tissue law's PR needs is then a schema version bump against fixtures that guarded nothing.
- **Fix.** 5a reserves only what a log or a composition needs: the log slots, the per-tick law slot, the two
  containers, the recursive `_core_modules`. `schema.py`, `frame.py`, the contracts and the §7.4 lints land with
  `tissue_temperature`, their first caller. Record the 5a and 5b additions in `foundations_plan.md`, which §11.1
  says owns order.

### NIT

- **A2-N1** `§7.1`, the Frames row ("both frames, reduction, canonical values"): three jobs. Reduction carries the
  pooling law that §3.2 says moves to Maxim (EARN on GL3.B1). Give it its own `core/stimuli/reduce.py`, so that
  move doesn't touch the frame types.
- **A2-N2** `§7.1` says models "read tissue". The allowlist (§7.3) excludes `body.store` and `body.tissue`. Say that
  tissue state reaches models only through the `FieldReader`, over 5a's per-body point container, and that this
  container is a registered field (`perceivable`, per A2-S2).
- **A2-N3** `§6.3`: the gate table has two header rows (`| # | Gate | Catches |`, then `| # | Gate |`) and renders
  broken.
- **A2-N4** `§7.3`, `stimuli-protected` ("only the simulation composition, and adapters' `schema`/`frame`
  imports"): a `protected` contract can't express "only these submodules" (import-linter 2.6 `protected.py`). The
  implementer must allow `simcore.adapters` wholesale, and the narrowing comes from skip-layer's recursive
  classification. Say so, or the contract will be read as doing what it can't. Also name the composition module:
  an unborn allowed importer is silently empty, so a misspelling fails every legitimate importer, not the contract
  author.

## What holds up

- Fail-closed contracts, checked against the pinned tool's semantics.
- The `BodyFrameFeed` kept beside `Frame`.
- Reduction in the core.
- Bound-row agent homes.
- A runner stripped to order and handout.

The remaining architecture risk sits in two places: the digest (A-B2) and the cross-law contact writer (A-S3).
