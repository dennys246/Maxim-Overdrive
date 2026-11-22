# Step 5a PR 2 fold, delta 1: Architecture, Wire integrity, Determinism

Reviewer: independent, read-only. Tree: the staged fold on 3b4c493 (index = working tree, checked). Ran: `lint-imports`
(10 kept, 0 broken), `lint_standards.py` (PASS), 10 touched test modules (466 passed, 1 skipped), four probe scripts,
and the determinism digest at 0.2 m and 0.1 m on the fold against a `git archive` of 3b4c493: **identical** (f7429cba…,
e9e57122…), so bit-identity is verified, not taken from the fold table.

**New: 0 BLOCKER, 2 SHOULD-FIX, 6 NIT.**

## Round-1 status (set by this reviewer, from the tree)

| Finding | Status |
|---|---|
| Arch S1, split at the count | **fixed**: `Gate` is composed, identity is tokens, the lifecycle is `window.py`. Residual 5b note under N5 |
| Arch S2, self-asserted identity | **fixed** for narrowing (scan + runtime nesting/token checks). Identity by name survives one level up: new SF-1 |
| Arch S3, handles outlive narrowing; subscript writes to `material` | **fixed** (read the code; `test_a_handle_kept_past_its_block…` and `test_construction_goes_through_topology…` pass) |
| Arch S4, reads unchecked | **fixed** (runtime, `Gate.require_read`) |
| Arch S4, §5 typed views | **open: owner** (amendment 2) |
| Arch S4, damage package | **fixed** |
| Arch S4, §6 sources resolved by heat | **deferred**: marker in `world.py::_power_field`, listed in the roadmap and `simulation.py`; trigger PR 3 |
| Arch S4, §2 `Changes` | **open: owner** (amendment 1) |
| Arch S5, laws-independent | **fixed** (contract lists three modules; test asserts one module per law) |
| Arch S6, roadmap | **fixed** (roadmap, checklist and CLAUDE.md agree: PR 3 `time_s`, PR 4 windows) |
| Arch S7, writes one direction | **fixed** (`check_laws` equality) |
| Arch N1 | **fixed** |
| Arch N2 | **fixed** |
| Arch N3 | **fixed** (`heat.step` gone; one `time_s +=`, in `physics.py`) |
| Arch N4 | **deferred**: applier marker; trigger PR 4 |
| Arch N5, N6 | **fixed** |
| Wire S1, version per changing batch | **open: owner** (amendment 4). Code half fixed (false quote gone, checklist reworded, strike-path test). See SF-2 |
| Wire S2, request key | **open: owner** (amendment 3). Code half fixed (docstring, `test_overlapping_paints…`) |
| Wire S3, departures only in the commit | **fixed** (`simulation.py` list, roadmap) |
| Wire N1, stale names | **fixed** at the three named sites; two more found (N4 below) |
| Wire N2, N3, N5 | **fixed** (`git check-attr` gives `eol: lf`) |
| Wire N4, CLAUDE.md wrap | **open**: the fold wrote a new 200-column line, `CLAUDE.md:69` (the `physics.py`/`intents.py` line) |
| Wire N6 | **fixed**; the per-record batch boundary **deferred**, trigger PR 4 (`imagine` as stage 2) |

## The regroup

- **`writers.py`**: identity (`WriterToken`, `claim`, `_granted`) and the access rule (`Gate`). One concern
  in two parts (the gate is identity's only consumer). Split correctly. `Gate._ran`
  ("construction is over") is a lifecycle fact in the access rule. Tolerable: it refuses
  construction's token late.
- **`window.py::WindowOwner`**: a template-method base (open, prepare commit, roll back, close), with `CellStore` as its
  only subclass. A responsibility split, not a count split: the hooks are a real interface; rollback
  of the topology version lives with the store, which owns what is saved. It is still inheritance, though, and
  `CellStore` reads the base's `_open` directly. CellStore's public surface, own plus inherited, is exactly 12. See N5.
- **Batch counting** sits in `CellStore.as_writer` for every narrowing, not in `topology.apply` as I suggested. Only
  Topology's block can set `_edited`, and the store owns the version's rollback, so I accept the placement.
- **`damage/`**: `loads.py` (a law), `thermal.py` (a law), `strike.py` (a resolver, not a law), `__init__` re-exports.
  One job per module; `reductions.py` takes observer reductions out of the laws.

## The four amendments (recommendations for the owner)

1. **§2, `Changes` with the laws.** Correct: `Changes.effects` holds `LoadEffect`, a law-layer type, so the cells layer
   can't own it. One owner, no restatement. **Accept.**
2. **§5, runtime narrowing to a token.** It describes the code accurately. It is a real weakening: a type error becomes
   a runtime error, and the law receives the whole grid (`on_close` included, N3). The checks are real, though: I read
   them, the tests pass, and the fold's plants went red. **Accept**, with two wording fixes. §5 still says
   `prepare(views)`, naming views that no longer exist. And the 5b trigger should be recorded: a body container needs
   a parameter or the shared gate (N5).
3. **§5.1, an unkeyed key is its emission index.** Correct and deterministic (below). **Accept**, adding the half that
   gives it teeth: requesters emit in their input's order (scene list, spec list, record's loads), and the log keeps
   that order un-normalised. Without that, "emission index" is defined but not reproducible.
4. **§5.1/§7, once per changing batch.** This is the right rule for caches. **Accept only with "changing" defined, and
   the code matched to the definition (SF-2).** §7 now reads "counts topology batches (§5.1)", which literally
   contradicts §5.1's "changing batch". Word it as "Topology's version; §5.1 says when it moves".

## Determinism of the emission-order keys

Deterministic on one machine, and I verified the points it rests on:
- Order sources: `Scene.build` iterates `self.primitives`, the file's list order; `_voxelize` iterates `placed`, the
  spec's order; `LoadsLaw.step` iterates `inputs.loads`, the record's order. Every one comes from input that is or will
  be logged.
- Generators don't change the meaning. `Box.mask` and `Cylinder.mask` read only `grid.mesh()` (geometry), never
  cells, so a lazy mask equals an eager one. The digest is identical to HEAD.
- Destroys in one batch commute; paints don't, and a test pins it.
- `_take_cells` iterates `_meta`, which is in dict insertion order. No set or `hash()` feeds an order.
- Gaps: no order is defined between keyed rows (`fire_solid.md` §1.4) and unkeyed requests in one batch (trigger 6.0a).
  Reproducibility also depends on PR 4's log never reordering an `imagine` spec's primitives (amendment 3).

## New findings

**SF-1. `physics.py::run_law`: a registered law's token goes to any object that carries the law's name, and no scan
holds the callers (verified).**
`run_law` looks up `_TOKENS.get(law.name)` and is public. `tests/test_ownership.py::OWNED_CALLS` restricts
`as_writer`, `claim` and `constructing`, not `run_law`, `resolve_loads` or `run_physics(laws=…)`. Probe:
`token_uses("simcore/core/applier.py", "physics.run_law(g, Fake(), 0.0, LawInputs())")` returns `[]`. The shipped test
helper `tests/_cells.as_law` uses exactly this pattern ("Run body as the law name"), so it is the house idiom.
*Failure scenario:* in PR 4, moving a strike to a `Load`, someone writes integrity from `world.py` or `applier.py` with
a small frozen dataclass named `"damage.loads"` passed to `run_law`. It holds the real token, every scan stays green,
and the per-record cadence and tuple order (§5) are bypassed. That is Arch S2's impersonation, one call higher.
*Fix (unverified):* add `run_law` and `resolve_loads` to `OWNED_CALLS`, allowed in `physics.py` only. Allow
`run_physics` with `laws=` only where the scan says (`world.py` passes the default). Tests stay free, as now.

**SF-2. `grid.py::MaterialGrid.paint`, `name_region` vs `destroy`: "changing batch" means two different things (verified).**
`destroy` sets `_edited` only when it hits a solid cell. `paint` and `name_region` set it unconditionally. Probe, inside
an orchestrator window: an empty-mask `Paint` bumps 1, repainting a cell with its own material bumps 1, an empty
`Destroy` bumps 0. Amendment 4 says "changing batch", and `topology_version`'s docstring says "batches that have changed
the cells or the region table".
*Failure scenario:* `topology_version` is in §9's per-tick digest from PR 4. Take the admin material edit that sets a
region to the material it already has, or a replay checker or save loader that implements §5.1 as written (compare
before and after). Either one disagrees with the server by one version on that tick, and the digests diverge with no
physics difference.
*Fix (unverified):* the owner picks "a batch that made a non-empty edit" or "a batch that changed a value". State it in
§5.1, make `paint` match `destroy` (`if mask.any()`, or compare values), and pin the empty-paint case in a test.

**N1. `writers.py::_claimed`** holds every granted token and is not in the scan's `TOKENS`. `writers._claimed["topology"]`
works from anywhere (probe: it destroyed a cell). In `src`, `as_writer` is scanned anyway, so the remaining reach is
`grid.writing(writer=writers._claimed["construction"])` on a fresh grid, which evades the `constructing` scan. Add
`_claimed` to `TOKENS`.

**N2. `CLAUDE.md:69`** is 200 columns, written by this fold (Wire N4 left open).

**N3. `window.py::WindowOwner.on_close`** is ungated. A law can register a listener from inside its block. Probe: the
listener ran after every later window. *Scenario:* a law registering per step leaks one listener per substep and runs
code outside the tuple after each commit. Refuse `on_close` while the window is open.

**N4. Stale after the package split:** `docs/design/boundaries.md:53` lists the core's scipy user as `damage.py`. That
note bears on determinism, and the users are now `damage/strike.py` and `reductions.py`. `docs/architecture.md:86`
names `damage.thermal_degrade`.

**N5. `grid.py::CellStore._gate`** is private to the store, and the window is inherited. When 5b's `body_points` or
`sem_stimuli` §7.1's `radiant_emitters` arrive, they need this one gate and this one window, not a second
`WindowOwner`. Trigger: 5b. Record it with amendment 2.

**N6. `sim_core.md` §5 amendment wording:** `prepare(views)` versus `step(grid, …)` (amendment 2); §7's "counts
topology batches" (amendment 4).
