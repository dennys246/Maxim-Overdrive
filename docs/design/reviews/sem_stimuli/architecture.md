# Design review: `sem_stimuli.md` v1, Architecture lens (focus: modularity)

At `phase1/sem-stimulus` **3357439**. No repository edited.

**Counts: 2 BLOCKER, 12 SHOULD-FIX, 6 NIT.**

## What I checked

- The design in full; `research/sem_stimuli/7_modularity.md` in full, and `3_world_side.md` §0 and §1.3.
- `pyproject.toml` `[tool.importlinter]`, all of it. `tests/test_tooling_config.py` lines 200–300 (`PLANTED`,
  `_core_modules`, `CORE_PUBLIC_SURFACE`, `MEMBRANE_SURFACE`, the two surface tests).
- `src/simcore/core/frames.py` lines 1–80, `world.py`'s symbol list, and `adapters/sem/bridge.py` lines 48–80 and
  205–231.
- `boundaries.md` §2.1–§2.2, §4.2–§4.4, §7.1, §8.1, §9.1, §10 and BF-15; `npcs_and_sem.md` O13, O19, O36, §2.1,
  §6.1, §7; `world_model.md` §8; `world_v2.md` §2.5; `fire_model.md` §5.1; `foundations_plan.md` §2; the tracker.
- **Experiments on import-linter 2.6 / grimp 3.13** (the pinned versions, from the `fire-research` venv), each on a
  throwaway package in my scratchpad:
  - (a) `independence` over `pk.models.*` **does** match a `_contract` module: `a → _contract` is a broken
    contract. L7's claim that the "_" module is outside the wildcard is false.
  - (b) The wildcard works on a **one-child** package (KEPT; red once a second child imports it), settling §7.3's
    unverified point.
  - (c) An unborn **source** in a `forbidden` contract is a hard error (`Module 'pk.notyet' does not exist.`);
    (d) an unborn **target** is KEPT in silence.
  - (e) A `protected` contract on an internal package (`pk.stim`, `allowed_importers = ["pk.world"]`) lets the
    package's own children import each other, and fails a **new, unlisted** module (`pk.newlaw → pk.stim.schema`).
- **Confirmed:**
  - `RegionInstrument` is at `bridge.py:48`.
  - `reading_schema`'s name test is at `:72-75`, so a fifth quantity would get the temperature range.
  - `membrane-reads-frames` forbids `simcore.core.materials` to `adapters.sem` (§6.1's "smaller hole").
  - `region_parts` builds `StructureModulator` too (`:208-217`), and the shipped `to_maxim_entity` calls it (`:224`).

## BLOCKERS

### A-B1. As specified, the §7.3 contracts and §7.4 checks don't fail on the drift most likely to happen

`sem_stimuli.md::§7.3`, `§7.4`; `tests/test_tooling_config.py::_core_modules`.

1. **The surface classification can't see subpackages.** `_core_modules()` is a flat glob,
   `(ROOT/"src"/"simcore"/"core").glob("*.py")`, so it never sees `core/stimuli/**` or `core/body/**`. That causes
   two problems:
   - **Adding the entries breaks the test.** §7.3 says `CORE_PUBLIC_SURFACE` gains `stimuli.schema` and
     `stimuli.frame`. The moment it does, `assert _core_modules() >= CORE_PUBLIC_SURFACE` fails.
   - **Nothing forces classification.** The new modules are invisible to the rule that "a new core module joins this
     set or the contract's forbidden list". So an adapter can import `simcore.core.body.tissue` or
     `simcore.core.stimuli.models.flux`, and no contract or test notices.
2. **`stimuli-read-only` and `laws-blind-to-senses` are denylists, and denylists fail open.**
   - Failure scenario: fire 6.2 lands as `core/solid.py` or `core/laws/flame.py` (D9 is open), and nobody adds it to
     the list. The new law imports `stimuli.schema` to "know who senses it", and the gate is green.
   - The repo has already learned this lesson: `pyproject.toml`'s comment before `maxim-through-adapters` explains
     why input primitives moved to an allowlist ("a denylist of modules can't be completed").
   - Listing unborn laws as **sources** isn't a way out: by (c), that is a gate error. Listing them as **targets**
     is silent until they are born, and silent forever if they are born under another name (d).
   - §7.4's "the contracts' module lists equal the packages that exist" can't be written for "laws": no package or
     naming rule identifies a law until D9 rules.
3. **`stimuli-read-only` leaves the leak-relevant modules open.** It doesn't forbid `simcore.core.grid` (raw
   `material` ids), `simcore.core.materials` (combustion constants) or `simcore.core.frames` (`CellFrame.material`).
   T5's leak, a model keying on a material constant, passes the import check. Only "honest reads" can catch it, and
   that check runs on one canonical scene and only sees reads made through the `FieldReader`. A direct
   `grid.material` access never goes through the reader, so it never sees one.

**Fix.**
- Make `_core_modules()` recurse.
- Invert both stimulus contracts into fail-closed forms:
  - `protected_modules = ["simcore.core.stimuli"]`, with `allowed_importers` set to the simulation composition (and
    `frames`, if it keeps a `stimuli` part). By (e), any new law, store or adapter that imports it goes red.
  - For the models, a grimp allowlist test in the style of `test_input_allowlist.py`: models may import only
    `stimuli.schema`, the field-reader type, `body.geometry`, `body.sites` and `checks`.
- Add one `PLANTED` row per new contract.

### A-B2. The version rules make every "replaceable" law and every "non-breaking" row a refusal for saves and agents

`sem_stimuli.md::§5` (the header, rerun manifest and rules 2, 3 and 5) against `§0` ("Replaceable, the laws") and
`long_term_features.md` ("laws … can be swapped without a refactor").

- **What the design records.** The header carries the whole registry; "a registry mismatch refuses a tier-1
  replay"; rule 5 refuses an agent home under another registry digest without a migration.
- **What that does to the other rules.**
  - Rule 3 says adding a row is non-breaking, but a new row changes the whole-registry digest. So it breaks every
    replay log and every agent home.
  - Rule 2 calls a better estimate the routine way to swap a law. It also changes the digest, so every law swap
    needs a written migration for every trained NPC.
- **Failure scenario.** Phase 2 adds `sound_event`; every Phase 4 NPC refuses to load, though none binds hearing.
- **The consequence.** The contract/law line is drawn in the right words but enforced in the wrong place. The law is
  frozen in practice, which is exactly the refactor the tracker's rule exists to avoid.

**Fix.**
- Digest per **bound** row. An agent home records `(row name, derivation_version)` for the rows its bindings use.
- Refuse only on a change to one of those. Make even that a named, logged body change ("the skin law changed under
  this NPC"), not a hard refusal, and leave the owner to rule which.
- Replay refuses on a changed row that some NPC in the log bound, not on the whole registry.

## SHOULD-FIX

### A-S1. `receptor` and `tag` are frozen into row identity, but both belong to Maxim or to our progress

`§2.1` ("All but the last row are frozen"; tag "closing it is a new row").

- **`receptor` is a property of the consumer.** Which receptor a stimulus feeds is transduction knowledge, the T2
  side of the design's own split.
  - One row already feeds two receptors: `tissue_temperature` "skin points × depths" feeds warm and cool fibres at
    one depth and C-fibre nociceptors at another, yet the field holds one value.
  - When GL2b (M9) defines its nociceptor classes, the frozen value is wrong, and the version rules then force a
    rename.
  - The binding already names the consumer. Make `receptor` a non-identity annotation (a set), checked by T14 for
    being non-empty.
- **Renaming a row when its tag closes contradicts rule 2.** `burned_area_fraction`'s EARN closing on OD-C10 is a
  better estimate of the same meaning. Keep the tag as versioned metadata; rename only on a new meaning.

### A-S2. The flux-onto-skin and occlusion law has no module, owner or step, and it is the whole budget

`§2.4` (the "flux onto skin" row), `§7.1`, `§8`.

- §2.4 lists the law as replaceable: view factors, occlusion per (emitter, region group) on a schedule, held results
  saved. But §7.1 places only `tissue.py` ("skin column, Henriques, contact").
- Occlusion casts rays through solid cells. That makes it a grid reader, a law, a cost driver (820 ms per 100 NPCs
  unstaggered) and a source of saved state (the held occlusion and each NPC's schedule phase).
- **Failure scenario.** It lands in `tissue.py`, which then imports `grid`, the emitter table and the schedule: the
  sensing god module L7 §5 warns about. Or it lands in a stimulus model that writes held state.
- **Fix.** Name a `core/body/irradiance.py` law (or put it under the light field, Phase 2), its owner step (6.2
  writes `radiant_emitters`, so it is probably 6.2 or 6.3), its field (incident flux per point, internal) and its
  B5 row.

### A-S3. The tissue law opens three unplanned seams in step 5a's law list and field registry

`§2.4` ("integrates every tick, for every body"; contact "by a coupled column"), `§7.1`, `§7.2` (`reads`).

1. **Two rates.** O34's law list runs at the physics step. Tissue runs every 0.1 s tick on held fields. The
   `Simulation.step` that 5a's composition note designs must have a per-tick law slot, and the note doesn't know
   that yet.
2. **Two-way coupling.** A "coupled column … one implicit system" with fire_solid §3.2's Robin contact
   (`3_world_side.md` §1.3) means the skin and the object's surface layer exchange energy. That exchange has to be
   written to both sides and ledgered antisymmetrically (`world_v2.md` §2.6), across two laws stepping at two rates.
   Otherwise the body is an unledgered sink.
3. **Body state isn't a field the registry can name.** `reads` must "name a registered field", but `world_v2.md`
   §2.5's containers are cell, fixed-metre grid, zone and face table. Per-body, per-point state (node temperatures,
   Ω) and a multi-writer contributor table (`radiant_emitters`) are new containers.

**Fix.** Hand all three to 5a now, as the design already does for the log reservations, and name the tissue–solid
coupling's owner and order.

### A-S4. `Frame` gaining a `stimuli` part contradicts the publish cadence and the capability narrowing

`§7.1` ("one `stimuli` part of `Frame`"), `§4.1`, against `boundaries.md::§4.2` and `§6.1`.

- **The cadence.** Boundaries §4.2 says frames are published after a physics step and after an intent tick, "not
  per tick". A `BodyFrame` is built at each NPC's step tick against held fields at its current pose, which is mostly
  between publications. So either `Frame` starts publishing on every tick an NPC is due (a silent revision of §4.2),
  or `BodyFrame` isn't part of `Frame`.
- **The capability.** Every `FrameView` holder (the SEM membrane, the client snapshot) would reach every NPC's
  tissue, so §6.1's narrowing rests on host discipline.
- **Fix.** A separate per-NPC `BodyFrameFeed` keyed by `npc_key`, published by the simulation beside `FrameFeed`.
  The `FrameView` never reaches it, and the host hands out per-key views.

### A-S5. The binding's reduction runs in the worker, outside the digest, and needs data the frame lacks

`§3` ("a binding reduces"), `§4.1` steps 3–4, `§5` ("over the bytes sent"; "is then tier 1").

- **It is outside the digest.** The `area_mean` or `max` is computed in `adapters/agents`, after the digested bytes.
  A change to the reduction code changes what every NPC feels, yet the `stimulus_digest` stays green. The rerun
  manifest records the binding *data*, not the code. So "what did the NPC sense at tick T" is not tier 1; only its
  inputs are.
- **It needs data the frame lacks.** `area_mean` needs each point's area, which isn't in `BodyFrame`. The worker
  would need `core.body.geometry` or a new handshake table, which is a hidden dependency.
- **Fix.** Give the core each NPC's binding table as data (sites and reduction, no Maxim) and have it emit the
  reduced values as part of the frame, so they are digested. The worker maps a value to a sensor name and calls
  `world_set_axis`. The per-site rows stay the frozen contract.

### A-S6. D1 merges two different `frame`s and creates two delivery routes

`§10::D1`, `§4.1` steps 3–4, against `npcs_and_sem.md::§6.1` (`step(now_tick, dt_ticks, frame)` is Overdrive's
port; Maxim's function is `step(agent, world_dt_us, frame)`).

- The adapter pushes the frame's values with `world_set_axis` and then calls Maxim's `step(…, frame)`. If that
  `frame` is the `BodyFrame` too, Maxim receives the same stimulus twice by two routes. That is the "two truths" the
  design rejects for pulled sensors in §4.1.
- **D1 should say one of two things:**
  - (a) the `BodyFrame` is the port's `frame`, the adapter consumes it, and Maxim's `frame` argument is something
    else or empty; or
  - (b) Maxim's `step` consumes the frame and does the pushes, which is an upstream ask in the embeddable draft
    under O36.
- (a) keeps Maxim untouched; (b) is cleaner and slower.

### A-S7. `stimuli.run` is set up to become the scheduling singleton L7 §5 warns against

`§4.1` step 1, `§7.1` ("Registry, runner"), `§8` items 1–5.

- Beyond scoped readers and frame building, §8 hands it the due-set, cache reuse, SI-floor cutoffs, parallel
  evaluation and fixed-order assembly, none with its own module; the size tripwires only see the result.
- **Fix.**
  - **Due-set:** the simulation's schedule (`npcs_and_sem.md` §2.1 already owns rate divisors).
  - **Caching:** one wrapper per model, with its cached-equals-fresh test.
  - **Cutoffs:** per-row law parameters.
  - **Assembly and canonical bytes:** `stimuli/frame.py`.
  - **Stagger:** goes with the irradiance law (A-S2).
  - The runner keeps only the order and the capability handout, as L7 §5 says.

### A-S8. `simcore.adapters.agents` gets one narrow contract, where it needs the membrane's

`§7.3` (`agents-no-materials`), `§6.1`.

- Under `skip-layer`, adapters may import `simcore.core.world`, `applier` and `frames`. `adapters.sem` gives up
  `world` (`membrane-reads-frames`), but the agents adapter would keep it. So "never a `FrameSource`, an `Applier` or
  the world" (§6.1) has no import half for the one adapter that runs NPCs.
- **Failure scenario.** A convenience `from simcore.core.world import World` in the agents adapter's host side.
- **Fix.** An `agents-reads-body-frames` contract mirroring `membrane-reads-frames`: no `world`, `materials`,
  `frames` or `applier`. Classify it against the surface sets, and plant one import.

### A-S9. D10, as worded, would move part of the shipped act path into `tests/`

`§10::D10`, `§6.1`; `bridge.py::region_parts` (`:208-217`) and `to_maxim_entity` (`:220-231`).

- `region_parts` builds the `StructureModulator`s as well as the instruments, and `to_maxim_entity` (shipped) calls
  it.
- Moving "`region_parts`, `RegionInstrument`" under `tests/` either breaks the shipped entity builder or makes a
  shipped module import `tests`, which `tests-out` forbids.
- **Fix.** Split `region_parts`: modulators stay in the membrane, and the instrument builder goes to a lab builder.
  Put the lab builder under `tests/` only if the Phase 2 lab, which is game content, never needs it.

### A-S10. Three new data formats and the step placement are left unassigned

`§3`, `§4.2`, `§5`, `§7.1`; CLAUDE.md "Every format is versioned", "Trust boundaries … every loader".

- **The formats, none with a loader, gate row, version or fixture.**
  - The Overdrive body instance: site sets in metres, with depths.
  - The binding table: row, sites and reduction mapped to a sensor.
  - The Maxim-format body YAML, which the host must digest and the worker must check.
  - The per-tick `BodyFrame` codec schema, beside `npcs_and_sem.md` §6.6's codec.
- **No step names the work.**
  - `core/stimuli/*` and `core/body/{geometry,tissue,sites}`.
  - The checks in §7.4, of which four are new `lint_*.py` modules.
  - The 5a log reservations.
  - D10's move "before step 5 ships vocabulary v1".
- **The order.** Only `body/store.py` says "(5b)", yet the "frozen now" v1 rows need 5b, 6.0b (face skins) and 6.2
  (`radiant_emitters`), and their one consumer is Phase 4, after mid-2027.
- **Fix.** A step table, and the tracker's "Next" entry pointing to it, so `foundations_plan.md` stays the owner
  of order.

### A-S11. Agent motor state feeds stimuli but isn't a logged input

`§1` (breathing: "the agent reports its breathing state"), `§2.2` (`eyes`, `head`, `breath` cadence), `§5` ("a pure
function of logged inputs").

- Breathing, gaze and head orientation come from the agent, and they decide the inhaled dose and the radiance at the
  eye. Unless each is an intent in the log, replay with `maxim` blocked can't reproduce the `BodyFrame`.
- A report outside the log is a second input path (boundaries §6.1).
- **Fix.** State that posture, gaze and breathing are intent kinds (5b's vocabulary, or later), and that the frozen
  grammar depends on them.

### A-S12. Decisions the design revises without saying so

Each should be named in the design, its table, or a decision row.

1. `fire_model.md::§5.1` calls the root-sensor skin stopgap **ANALOG**. `§3` and `D8` call it **EARN** on OD-C10.
   The tag changes silently.
2. `boundaries.md::§2.1` (BF-15) puts "body grammar **and receptor models**" in the engine. The design puts
   transduction in Maxim and cites BF-15 for the grammar only. The row needs rewording, or the design must say which
   "receptor models" BF-15 meant.
3. `long_term_features.md` lists "units **and ranges**" as part of the contract. The design delivers no saturation
   range (§2.1), which is a scope change to the tracker.
4. `boundaries.md::§2.2`'s layer map gains a stimuli layer between laws (4) and sim (6), "5c" in L7. The `body`
   package spans layers 2–4: geometry, store and a law. "No existing module moves" is true, but the map O24 keeps is
   changed and not recorded.
5. `boundaries.md::§4.2`'s cadence (A-S4), and `§4.3` / `npcs_and_sem.md::§7.2`'s "a pure function of the frame
   pinned for that agent". The design replaces the pinned frame with a per-step `BodyFrame` shipped over the
   channel. That is right, since a worker can't pin a host frame, but it should say so.
6. `world_v2.md::§2.6`'s ledger rule for the skin's energy exchange (A-S3).
7. Acknowledged (no finding): O19 (D1), D2, D6, §11.1's L7 reversals, the `maxim-through-adapters` amendment
   (whose test, `test_only_the_sem_membrane_may_import_maxim`, must change with it).

## NITs

- **A-N1** `§7.2`: "the tuple's order is the run order". The models are independent and write nothing, so their
  order carries no meaning. But it enters the header's registry digest, and maybe the handshake id map, so a harmless
  reorder refuses a replay. Sort by name for the digest and the ids.
- **A-N2** `§6.1`: "only `simcore.core.stimuli` writes a `BodyFrame`" can't be held by imports. Anyone can construct
  a frozen dataclass. It needs a constructor-site scan, like the writer scan, or a private constructor token.
- **A-N3** `§4.1`: `tick` and `basis_sequence` are called "host-owned" but sit in a core type. Either the core owns
  them (it knows both), or they belong in the host's message envelope.
- **A-N4** `§7.4` ("no central switch"): say whether `tests/`, the generated vocabulary artifact and the body and
  binding data are exempt. The lint can't see switches on receptor or unit literals, or on `spec.name` compared with
  a variable.
- **A-N5** `§7.3` / L7 §3: by (a), a `_contract.py` under `models/` would break `stimuli-independent`. Say that the
  `StimulusModel` protocol lives in `stimuli/schema.py`.
- **A-N6** `§2.1`: "outside it the core raises" lets one NPC's bad value abort the world's step. Rule it as a
  decision, against ending that NPC as `agent_failed`.

## What holds up

The core placement (skip-layer leaves no other home), laws blind to senses, N + M coupling through fields, push
over pull, the declaration registry, the stable per-site contract under changing bindings, and cost-only interest
management. The shape prevents god modules on paper; A-B1 and A-S7 are about making the checks able to say so.
