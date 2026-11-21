# Final round: `sem_stimuli.md` v4, Architecture lens

At **aa6bd1b**, the diff `0918685..aa6bd1b` only. Statuses are mine (O25), read from the tree, not from `fold.md`.
I edited nothing. Scratch scripts: `scratch_architecture/` (import-linter 2.6). I made no Maxim claim.

**Statuses: 8 fixed, 2 open, 0 deferred, 0 rejected.** **New findings: 0 BLOCKER, 3 SHOULD-FIX, 3 NIT.**

## Status table

| Id | Status | Reason (read from the tree) |
|---|---|---|
| A-S10 | fixed | The checklist's 5a item cites `sem_stimuli.md` v4 §5, §7.1 and §11.1 and says "the composition note cites §11.1". `foundations_plan.md:6` says "`checklists.md` holds the steps' items", so a 5a author reaches the pointer from the plan. The plan row was left unchanged, which is acceptable now that the checklist carries the pointer |
| A3-S1 | fixed (ruling below) | §7.1 adds a `wire.py` leaf that imports only `checks` and numpy. §7.3 sets `AGENTS_SURFACE` = `stimuli.wire`, `intents`, `limits`, `checks` and adds a grimp closure test. I read the imports at this tree: `intents` imports `checks` and `limits`, `limits` imports `checks`, and `checks` imports only the stdlib and numpy. The surface is closed today. Two residues are new findings: N-S2 (the surface stops being closed at 5a) and N-S3 (package entries in the forbidden list) |
| A3-S2 | **open** | v4 adds `body-layers` and `stimuli-layers`, and it restates stimuli as 5c. But both contracts, as written, break on imports the design itself prescribes. **`stimuli-layers`:** the order is models above `registry \| run \| reduce \| events`, but §7.2's own `registry.py` imports `models.tissue_temperature`, and `run.py` ("order and handout") has to import `registry` and `reduce`, which `\|` declares independent. **`body-layers`:** `spec \| geometry \| sites` forbids `spec` and `sites` from importing `geometry`. Yet a body instance holds its site sets, and `sites` places geometry's body-metre sets in world metres. Verified: `v4_layers.sh` puts §7.3's two contracts verbatim on a toy. Each implied import is **BROKEN**: `registry → models`, `run → registry`, `run → reduce`, `spec → geometry`, `sites → geometry`. Missing: an order that §7.2's code satisfies. One such order is in the fix below |
| A3-S3 | fixed | In §7.1, `tissue.py` exports the column operator and steps only untouched sub-columns. `contact.py` steps each touched component on one grid it owns, first in step 3. §7.2 is restated: "a touched one's [substeps depend] on its component, which is world state". The checklist's contact item repeats the split |
| A3-S4 | fixed | §3.1 says "Tissue has one home": `store.py` implements `body_points`, the `FieldReader` views it with no copy, and save status comes from the registry entry. §5's save cites "the registry and §7.1". The checklist's 5b item plants a carried field marked `derived` |
| A3-S5 | **open** | §5 keys row lanes by `(name, derivation_version, producers)`, where producers are "the laws stepping the fields in its `reads`". §7.4 makes "every law that steps a read field" declare a version. The bound lane key adds the bindings digest, the reduce version and the bound row keys, which covers pooling through the bindings digest. **But producers are one hop deep.** `tissue_temperature` reads the tissue field, which `tissue.py` and `contact.py` step. `irradiance.py` computes the flux that `tissue.py` consumes, but it steps no field the model reads. So A3-S5's own scenario (an occluder fix in `irradiance.py`, no golden covering it) still loads an agent home silently under D13. The 5a plant ("a producer's version bumped alone") bumps a direct producer, so it passes while missing this case. Missing: producers as the transitive closure over every law's declared reads and writes, and a plant that bumps a law two hops upstream. Unverified as built |
| A3-S6 | fixed | `body-protected` lands in 5b with `store.py`. Its allowed importers are layer 6's modules (`Simulation`, the applier, the frame publisher), held by the exists test. The store's writers form an allowlist in `boundaries.md` §6.4's table with an ownership scan: load, motion, the applier, `tissue.py`, `irradiance.py`, `contact.py` |
| A3-N1 | fixed | `MEMBRANE_SURFACE` subtracts all three new surface modules (§7.3). The timing residue is N-N1 |
| A3-N2 | fixed | `core/stimuli/events.py` owns the pending-event and coalescing state, and layer 6 owns and saves it. The residue is N-N3 |
| A3-N3 | fixed | §4.2 defines `site_id` as the "index within the row's site set for this body", and §5's lane bytes say "site index" |

**Proposed deferrals:** none in this lens.

**Ruling on A3-S1 (the author chose Wire's `wire.py` leaf over my `true` + `PLAIN_DATA`): accepted.** A leaf that is
closed by construction is the stronger design. Nobody has to curate a plain-data list. The `false` setting and the
closure test say the same thing, so neither can drift from the other. And schema and frame, whose imports were the
chains I worried about, are no longer on the surface. The ruling has one condition: the closure must stay true for
the surface's *other* members, and at 5a it won't (N-S2).

**Fix for A3-S2 (verified, `v4_layers_fixed.sh`).** I ran these orders on the same toy:
- body: `["contact", "tissue | irradiance", "store", "spec | sites", "geometry"]`
- stimuli: `["run", "registry | reduce | events", "models", "frame | schema", "wire"]`

Every implied import is **KEPT** under them, including `reduce` importing `frame`, `schema` and `wire`, and models
importing `schema`. The planted `spec → store` and `models → run` both go **BROKEN**. Whether `sites` imports `spec`
is a design choice I didn't settle. If it does, `spec | sites` needs to become two layers.

## New findings

### SHOULD-FIX

#### N-S1. `Receipt` gets a second home, and the reason v4 gives for putting stimuli at 5c no longer holds

`sem_stimuli.md::§7.1` (the `wire.py` row: "`BoundFrame`, `StimulusEvent`, `Receipt` and kinds … imports only
`checks` and numpy"; the line after it: "`core/stimuli` above intents, since `BoundFrame` carries `Receipt` (5c)").
`boundaries.md::§2.2` layer 5b: `engine.intents` holds "stage-1 parsing, the intent record, **receipts**,
`StepOutput`". `boundaries.md::§7.1`: `settle(receipts, writes)`.

- **The contradiction.** v3 placed `Receipt` nowhere. v4 now puts it in `stimuli.wire`, and it also justifies
  stimuli sitting above intents by the claim that `BoundFrame` carries `Receipt`. If `Receipt` lives in `wire`,
  nothing in stimuli imports intents, so 5c has no dependency behind it and no contract checks it. If `Receipt`
  stays in intents, as `boundaries.md` §2.2 says (and v4 supersedes that map without naming receipts), then `wire`
  has to import intents, which its "only `checks` and numpy" rule forbids.
- **Who makes a receipt.** The `malformed` and `limit` kinds are stage-1 outcomes in `intents`. `intents` sits at
  5b, below stimuli, and `stimuli-protected` only allows layer 6 and adapters to import stimuli. So `intents` can't
  import `wire.Receipt`. It has to keep its own refusal kinds, which layer 6 then maps.
- **Failure scenario.** 5b lands before `phase1/agents`. It follows `boundaries.md` and puts receipts and their
  kinds in `intents` for `settle`. Then `phase1/agents` lands `wire.Receipt` with D15's kinds. Two receipt types
  and two kind vocabularies now exist. Only one of them has the receipt version and gate row (§5), and T7's
  denylist and T11's receipt-byte sweep run over only one of them. Nothing goes red.
- **Fix (unverified).** Name one home, and supersede the other by name. Either keep `Receipt` in `intents` and let
  `wire` import surface members only (the closure test still holds), which makes 5c real. Or keep it in `wire`,
  supersede `boundaries.md` §2.2's "receipts" and `settle`'s type, and drop the 5c sentence.

#### N-S2. `AGENTS_SURFACE` stops being closed when 5a makes `imagine` an intent kind

`sem_stimuli.md::§7.3` (`agents-reads-body-frames`: `allow_indirect_imports = false`; "a grimp test requires the
surface to be closed under imports"). `fold.md` A3-S1 ("the leaf makes the surface closed by construction").
`boundaries.md::§2.2` 5b ("the `imagine` intent carries a spec, so intents sit above imagination").
`roadmap.md:49-51` (step 5a makes `place` the applier's stage 2 of the `imagine` kind). `imagination.py:21-22`
imports `grid` and `scene`, and `scene.py:19-20` imports `grid` and `materials`.

- **Only `wire` is a leaf.** The closure argument holds for `wire` alone. `intents` is also on the surface, and
  after 5a, which comes before `phase1/agents`, `intents` imports `imagination`, so the chain runs
  `intents → imagination → grid, scene → materials`.
- **What breaks at landing.** The contract breaks on the worker's first `from simcore.core.intents import …`, and
  the closure test goes red. That is A3-S1's failure scenario again, with `intents` in the place `schema` held. The
  easy ways out are the same band-aids as before: widen `AGENTS_SURFACE` to include `imagination`, `scene`, `grid`
  and `materials`, which gives the worker direct access to the cells module, or flip the setting to `true`.
- **Verification.** The imports are verified in this tree; the contract mechanism was verified in delta 2, not
  rerun for this chain.
- **Fix (unverified).** Choose before 5a lands what the worker takes from intents. One option is a closed
  intent-wire module, like `wire.py`, that holds the typed intents and stage-1 parsing without the `imagine`
  spec's construction. Record the choice in the 5a and agents checklist items.

#### N-S3. A recursive `_core_modules()` that lists packages forbids the surface's submodules

`sem_stimuli.md::§11.1` 5a ("recursive `_core_modules` with every module and `__init__` classified"), `§7.3`
(forbidden lists equal to `_core_modules() − AGENTS_SURFACE`, and to `_core_modules() − CORE_PUBLIC_SURFACE` for
skip-layer). The surface gains `stimuli.wire`, `stimuli.schema` and `body.spec`.

- **The mechanism.** If the recursive list includes the package names `simcore.core.stimuli` and
  `simcore.core.body`, they land in the forbidden lists. import-linter's `forbidden` contract treats a forbidden
  module as a package by default (`as_packages`), so forbidding `simcore.core.stimuli` also forbids
  `simcore.core.stimuli.wire`.
- **Verified** (`package_forbid.sh`): a worker importing only `stimuli.wire`, with `u.core.stimuli` in the
  forbidden list, is **BROKEN**. With `as_packages = false`, or with packages left out of the list, it is **KEPT**.
  I tested the agents contract. Skip-layer uses the same mechanism over `body.spec` and the stimuli modules, and I
  didn't run it.
- **Failure scenario.** 5a lists packages, as §11.1 says; skip-layer breaks on the first loader importing
  `body.spec`, and the obvious repair, dropping the package by hand, reopens the hole A2-S4 closed.
- **Fix (verified on the toy for the agents contract).** Set `as_packages = false` on every forbidden contract
  whose list comes from `_core_modules()`, and have the equality tests assert that setting. Alternatively, classify
  packages separately and never list them.

### NIT

- **N-N1** `§7.3` (the adapters' reach row: "gains only `body.spec`, `stimuli.wire`, `stimuli.schema` … Lands: 5b")
  and `tests/test_tooling_config.py:277` (`_core_modules() >= CORE_PUBLIC_SURFACE`). Under that assertion, adding
  `wire` and `schema` in 5b fails, because neither exists until `phase1/agents` and the tissue row. The 5b checklist
  item correctly adds only `body.spec`. But the agents item never adds `stimuli.wire` to `CORE_PUBLIC_SURFACE` or
  subtracts it from `MEMBRANE_SURFACE`, and the worker needs both. Give each module its landing step.
- **N-N2** `§4.2` ("Deep frozen: `__post_init__` refuses writable arrays and arrays whose base chain doesn't end in
  immutable `bytes`") and `§7.1` (`wire.py` imports only `checks` and numpy). The checklist's closure plant is
  "a surface module importing `readonly`". So the one import the leaf most naturally needs is the planted red case,
  and `BoundFrame` gets a third inline copy of the base-chain check (`frames.py:52` holds one, and `frame.py` will
  hold another). `readonly.py` imports only numpy, so it is closed. Either move the predicate into `checks` or put
  `readonly` on the surface. Then choose a different plant, such as `body.spec`.
- **N-N3** `§7.1` (`events.py`: "the pending-event and coalescing state, owned and saved by layer 6"). This is
  carried, saved state, like the store's, but it has no write window, no writer allowlist and no row in §6.4.
  Today's writer scan passes it trivially because it sits in the core. Name its writers the way §7.1 names the
  store's.

## Is any of this law-level?

No. All six are module seams and import contracts, frozen contract by §0, so they belong in the design. Neither
checklist item yet holds A3-S2's corrected order, N-S2's 5a choice or N-S3's `as_packages` setting.

## What I checked

The whole diff; my delta-2 report; `fold.md`; `boundaries.md` §2.2; `foundations_plan.md:6`; `roadmap.md:46-54`;
`tests/test_tooling_config.py:253-288`; the imports of six core modules; three toy runs.

What remains is mechanical, but each item goes red on its first landing, which is when band-aids get chosen.
