# Step 5a PR 2 (`phase1/sim-laws`): round 1 and delta 1 folds

**Correction first (delta 1, D2):** this fold first said a read-only view "can't be unlocked". That was false: its
memoryview's `.base.obj` was the writable array, and a planted `grid.material.base.obj[0, 0, 0] = 0` wrote the world.
The bullet below now says what the code does.

Round 1 ran four lenses on 3b4c493 (`round1_exec_physics.md`, `round1_architecture.md`, `round1_wire_det.md`,
`round1_performance.md`): 0 BLOCKER, 13 SHOULD-FIX, 19 NIT. This table is the author's account of the fold. **Every
status is "open (for the reviewer)"** until a reviewer reads it from the tree (O25). Rows marked **proposed amendment,
for the owner** are places where the fold judged the code right and the design wrong. The draft wording is in
`docs/design/sim_core.md`, marked "(proposed, `reviews/sim_laws/fold.md`)", and the owner rules on each one.

## How the main fix works

- **Writers are tokens.** `writers.claim(name)` grants each writer's `WriterToken` once, at its owner's import:
  Topology's in `topology.py`, construction's in `scene.py`, and every law's in `physics.py`. A second claim raises, so
  anyone else who claims a writer makes its owner's import fail. A string, a token made by hand, or one `claim` didn't
  grant is refused. The core imports no `sys`, so `claim` can't check its caller. A source scan
  (`tests/test_ownership.py::test_only_each_writers_owner_narrows_claims_or_names_its_token`) holds `as_writer`,
  `claim`, `constructing` and the three token names to their owners' modules.
- **Laws never narrow themselves.** `physics.run_law` narrows to the law's token and its `reads` around `step`, then
  has Topology apply the law's requests. Inside a block, a read outside `reads` raises `UndeclaredRead`, and narrowings
  don't nest, so a law holding another writer's token still can't use it. Construction's token only opens a window
  (`scene.constructing`), never narrows one, and it opens none once an orchestrator's window has run.
- **Handles and views.** `material` and `original_material` are never handed out writable, so they change only
  through Topology's edits, which only Topology's block may make. A read-only view is a frozen copy whose chain ends in
  immutable bytes, cached per field and dropped on each change to it (delta 1, D2). A narrowed block's writable arrays are revoked when it ends: the store keeps a copy and drops the
  array it handed out.
- **Plants** (scratch copy, `plants.py` in the fold's scratchpad; each test went red when its mechanism was deleted,
  baseline green): `require_read`, `_EDITED_ONLY`, `require_editor`, the read-only buffer, revocation, the bump on a
  raising batch, the clock-in-block refusal, nesting, claim-once, the token check, construction never narrowing,
  construction after a run, `check_laws` equality, and the destroyed-count check. The reviewers' own plants on the new
  code, G3 (thermal writes `material` itself, or applies Topology itself), G4 (heat narrows "as construction"), the
  architecture plant (`as_writer(construction)` in the world's window) and SF2's kept handle, all now fail. The
  `laws-independent` contract went red on `from simcore.core.damage.loads import LOADS` and on `from simcore.core
  import damage` planted in `damage/thermal.py`.
- **Bit-identity.** On the determinism scenario (fire, strike, 30 turns), the digest at 0.2 m and 0.1 m is the same on
  f72817a, on 3b4c493 and on the fold. `test_laws`' old-path comparison passes. PR 1's bit-identity tests pass.

## Findings

| Finding | What the fold did | Status |
|---|---|---|
| Arch S1, writers.py split at count | `writers.py` is writer identity (tokens, `claim`) and the access rule (`Gate`, composed by the store, not a base class). The window's lifecycle (one owner, commit or roll back, close listeners) is `window.py::WindowOwner`. Batch counting is Topology's block in the store, reset per block | open (for the reviewer) |
| Arch S2, Exec SF1, self-asserted identity | tokens; `run_law`; the token scan; plants above | open (for the reviewer) |
| Arch S3, Exec SF2, handles outlive narrowing; subscript writes to `material` | topology channels never writable; per-block revocation; read-only buffers; tests `test_a_handle_kept_past_its_block_writes_nowhere_the_world_reads`, `test_a_law_reads_and_writes_only_what_it_declares` | open (for the reviewer) |
| Arch S4 (reads unchecked) | reads are checked in a law's block | open (for the reviewer) |
| Arch S4 (§5 typed views and handles; "as_writer at runtime") | **proposed amendment, for the owner** (§5): runtime narrowing to a token, with reads, writes and revocation checked at runtime. The law still receives the grid, not typed views, so an undeclared access is a runtime error, not a static type error | open (for the reviewer) |
| Arch S4 (§5.1 damage package) | code changed: `damage/` has `loads.py` and `thermal.py` (one law each) and `strike.py` (the strike resolver), with `loads.RESOLVERS` as the declared tuple | open (for the reviewer) |
| Arch S4 (§6 sources resolved by heat) | code stays until PR 3: `World._power_field` carries a `TEMPORARY(phase1/sim-clock)` marker naming PR 3, and `simulation.py` lists it | open (for the reviewer) |
| Arch S4 (§2 `Changes` with the cells) | **proposed amendment, for the owner** (§2): `Changes` carries load effects, so it lives with the laws | open (for the reviewer) |
| Arch S5, laws-independent blind to two laws in a module | the damage package; the contract lists `damage.loads`, `damage.thermal` and `heat`; region reductions moved to `reductions.py` | open (for the reviewer) |
| Arch S6, roadmap:51 stale | the roadmap names PR 4 for both windows, and the checklist's item moved to PR 4 | open (for the reviewer) |
| Arch S7, writes checked in one direction | `check_laws` requires `writes` to equal the registry's declaration | open (for the reviewer) |
| Wire S1, version bumps only on a changing batch | **proposed amendment, for the owner** (§5.1, §7 points at it): once per changing batch. The false quote in `writers.py` is gone, the checklist item is reworded, and `test_a_strike_that_breaks_nothing_leaves_the_version_where_it_was` pins the strike path | open (for the reviewer) |
| Wire S2, request key undefined; overlapping paints | **proposed amendment, for the owner** (§5.1): an unkeyed request's key is its emission index, and where paints overlap the later one wins. `topology.py`'s false sentence is gone, and `test_overlapping_paints_apply_in_emission_order` shows the order is load-bearing | open (for the reviewer) |
| Wire S3, departures only in the commit | `simulation.py`'s departures list gains `_power_field`, `bound_reads`/`prepare` (PR 3), the strike `Load` and the header's tuple (PR 4); the roadmap is fixed | open (for the reviewer) |
| Perf P1, construction and imagine hold every mask | `Scene.build` feeds Topology a generator (`apply` takes an `Iterable`); `_voxelize` checks inside the window and rolls back. Peak memory (tracemalloc), 3b4c493 → fold, 1.54×10⁶ cells: 400 unnamed boxes 647.6 → 61.6 MB, 400 named 1819.9 → 1233.8 MB (the named floor is the region table's own masks), a 32-primitive `imagine` 93.8 → 46.9 MB | open (for the reviewer) |
| Arch N1, destroyed count has two owners | `resolve_loads` raises when a law's effects disagree with Topology's count; tested | open (for the reviewer) |
| Arch N2, paint checks only the `material` writer | paint requires every field it writes, `regions` included | open (for the reviewer) |
| Arch N3, Wire N2, two time movers; float-time PR | `heat.step` is gone, and heat alone runs as the one-law tuple through `run_physics`. The clock can't move inside a writer's block. CLAUDE.md says PR 3 for `time_s` and PR 4 for `World.advance` | open (for the reviewer) |
| Arch N4, applier drives resolution | deferred to PR 4: the applier's marker now names the strike `Load`, and `simulation.py` lists it. `OUTCOME_MODULES` can't add `physics` until then. The scan matches subpackages | open (for the reviewer) |
| Arch N5, LAW_NAMES mirror | noted as the tuple's mirror | open (for the reviewer) |
| Arch N6, free-string writer | `apply` takes no writer: Topology applies every batch, construction's included | open (for the reviewer) |
| Exec NIT 3, Wire N3, `_edited` leaks | reset per block; a batch that edits and then raises still bumps once; tested | open (for the reviewer) |
| Exec NIT 4, contract test collapses | asserts one module per law | open (for the reviewer) |
| Exec NIT 5, replan trigger and batch boundary | §5's "today" sentence now names the editing-substep guard. The per-record batch boundary is deferred to PR 4, where `imagine` as stage 2 makes it matter (as in Wire N6) | open (for the reviewer) |
| Exec NIT 6, the reference shares code under test | `test_laws`' docstring says what the reference shares | open (for the reviewer) |
| Wire N1, stale names | `code_review.md`, `architecture.md` and `fire_solid.md` fixed | open (for the reviewer) |
| Wire N4, CLAUDE.md wrap | the three lines rewrapped; older overlong lines (commands, guards) left | open (for the reviewer) |
| Wire N5, LF unguarded | `.gitattributes` pins `docs/generated/*` to LF | open (for the reviewer) |
| Wire N6, topology docstring restates §5.1 | it links to §5.1 | open (for the reviewer) |
| Perf P2, per-load work | `slated` is made only from the second load on. The other two passes stay; the count is now checked against Topology's | open (for the reviewer) |
| Perf P3, gate overhead | **corrected in delta 1 (D3):** the round-1 numbers here (14–30 µs per law, 1.24 → 1.38 ms turns) weren't reproduced. The cost is about 2 µs per block plus one copy of each written field per block, O(cells): about 2% of a substep at 4×10⁶ cells (Perf's delta). Delta 1's view cache adds one frozen copy of each field a law reads after it changed; best-of-5 substep times, round-1 fold → delta, are 1.02–1.05 → 1.05–1.19 ms at 4.8×10⁴ cells and 6.26–7.22 → 6.18–6.44 ms at 3×10⁵ (noise at the larger size). The B5 lever is reusing a block's lease, or skipping revocation for the orchestrator's own laws | open (for the reviewer) |
| Perf P4, `check_laws` every call | `DEFAULT_LAWS` is checked once, at import; any other tuple on each call | open (for the reviewer) |

## Delta 1

Two readers on the staged fold (`delta1_exec_phys_perf.md`, `delta1_arch_wire_det.md`): 0 BLOCKER, 4 SHOULD-FIX,
8 NIT. Each plant below was run: the test goes red with its mechanism deleted.

| Finding | Fold | Status |
|---|---|---|
| D1, SF-1, token by `law.name` | `run_law` grants a token only to the registered law object itself (`_REGISTERED.get(law.name) is law`); tests run plants through `physics._run_as`, which the token scan holds to `physics.py`. `test_a_law_named_like_a_registered_one_gets_no_token` (plant P2: the name lookup restored, it writes); a law with `reads=None` is refused | open (for the reviewer) |
| D2, `.base.obj` unlock | a reader's view is `readonly.frozen` of the field, cached in `CellStore._views`, dropped at revocation, in `_set_cells` (paint's and destroy's edits) and at open and close. `test_a_read_only_view_reaches_no_writable_memory` walks `.base`/`.obj` for all four fields (plant P1: the memoryview view restored, all four red); `test_a_read_only_view_follows_every_change_to_its_field` (each `_views.pop` deleted: red, and the revocation one also breaks bit-identity) | open (for the reviewer) |
| SF-2, "changing batch" two ways | one definition: a batch that changed a cell's value or the region table. Paint compares values (`_set_cells`) and reports whether it took cells from a region (`_take_cells`); destroy already counted only hits; a new name always changes the table. `test_a_batch_moves_the_version_only_if_it_changes_a_value` pins empty, same-material and region-taking paints (plant: the unconditional bump, red). §5.1's draft states the definition | open (for the reviewer) |
| D3, Perf P3 row | restated above | open (for the reviewer) |
| D4, private reach | ruff `SLF001` selected; tests exempt. `test_code_outside_the_tests_reaches_no_private_name` (plant: rule dropped, red) | open (for the reviewer) |
| N1, `_claimed` unscanned | in the token scan's `TOKENS` | open (for the reviewer) |
| N2, CLAUDE.md:69 | rewrapped | open (for the reviewer) |
| N3, `on_close` ungated | refused while the window is open or held; `test_a_law_leaves_no_close_listener_behind` (plant: refusal deleted, red) | open (for the reviewer) |
| N4, stale names | `boundaries.md` keeps the audit's `damage.py` and names today's files; `architecture.md` names `damage/thermal.py` | open (for the reviewer) |
| N5, one gate for 5b | deferred (author's): trigger 5b, when `body_points` or `radiant_emitters` need a window; they join this store's gate and window, not a second `WindowOwner`. Recorded with amendment 2 below | open (for the reviewer) |
| N6, amendment wording | §5 says `prepare(views)` comes later and `step` gets the grid until then; §7 says "§5.1 says when it moves" | open (for the reviewer) |

## What needs the owner

- The four proposed amendments: §2, §5 (with N5: 5b's body fields share this gate and window), §5.1's key, and the
  changing-batch bump, now defined as a changed value or region table (SF-2; the alternative is "a non-empty edit").
- The token's limit. Python can't stop code that reaches into private names (`topology._TOPOLOGY`). The runtime
  refuses nesting and every token it didn't grant, the scan holds the token names, and ruff's `SLF001` refuses private
  reach in `src/` and `scripts/` (D4). A `getattr` with a string is the residual, and it is named.
- Perf P3's cost, against B5's budget.
