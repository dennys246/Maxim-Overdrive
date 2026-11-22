# Step 5a PR 2 (phase1/sim-laws @ 3b4c493): Architecture and modularity review

Reviewer: independent, Architecture lens. Read: the diff `origin/main...3b4c493`, CLAUDE.md, sim_core.md §2, §5, §5.1,
§6, §13, boundaries.md §4.1 and §6.4, `docs/plans/checklists.md`'s 5a §5/§5.1/§6 items, `docs/roadmap.md` Phase 1.
Ran: `lint-imports` (10 kept, 0 broken), an AST count of public methods, and one probe script (below).

**Counts: 0 BLOCKER, 7 SHOULD-FIX, 6 NIT.**

The shape is right: the law tuple, the registry as the one owner of writers, Topology requests built before the window
opens (scene, imagination), damage no longer a callback, and a substep loop shared rather than copied. The findings are
about the guard being weaker than CLAUDE.md now says it is, and a split that was cut at the count.

## Probe (verified, run on this tree)

```python
with g.writing(writer=None):
    with g.as_writer("heat"):
        t = g.temperature
    t[0, 0, 0] = 999.0            # after heat's block, window writer None
    with g.as_writer("construction"):
        g.material[0, 0, 0] = 0   # any core code, as construction, bypassing Topology
# -> escaped write landed: True; material bypass landed: True; topology_version unchanged (1)
```

## SHOULD-FIX

**S1. `src/simcore/core/writers.py::WriterGate`: split at the count, not along a responsibility.**
`CellStore` had 11 public methods; adding `writer`, `topology_version` and `as_writer` makes 14 (limit 12). They moved
to a base class, `class CellStore(WriterGate)`, so `lint_sizes` (it counts a class's own body) passes while the public
surface of `CellStore`/`MaterialGrid` is unchanged (MaterialGrid exposes 28 public names across its bases). The two
classes aren't separate concerns. They share protected state: `CellStore` sets `WriterGate._open`, `_channel` calls
`_may_write`, `writing()` calls `_begin`/`_end`. `WriterGate` also holds a second job, counting topology batches, which
sim_core.md §2 gives to the cell state with Topology as the requester. CLAUDE.md forbids exactly this.
*Failure scenario:* 5b's `body_points` container and `sem_stimuli.md` §7.1's `radiant_emitters` keyed rows need the
same writer gate. As a mixin welded to `CellStore._open`, that means a second `WriterGate` instance with its own
`_writer` and its own `topology_version`, so the one-owner property is lost the moment a second container appears.
*Fix (unverified):* use composition. One gate object, owned by the store and consulted by every container (cells,
regions, bodies, keyed tables), and batch counting moved into `topology.apply`, the one place a batch is defined.

**S2. `writers.py::WriterGate.as_writer`: a writer's identity is self-asserted (verified, probe).**
Each law narrows itself (`heat.py:115`, `damage.py:72`, `:120`), and any code in an open window may call
`as_writer(<any registered name>)`, `"construction"` included. The only scan restricting `as_writer` covers
`applier.py` (`tests/test_ownership.py::OUTCOME_CALLS`). `test_only_topology_edits_the_world` looks only for
`paint`/`destroy`/`name_region` calls, so `grid.material[m] = 0` under `as_writer("construction")` in a law passes
every guard. CLAUDE.md's flow rule now cites these tests as enforcing "every write to a field is declared" and the
checklist's "Topology is the only path to `material`". At runtime they enforce that only for writers that honestly
name themselves. *Failure scenario:* the 6.1 solid law, needing a char write fast, narrows as `damage.thermal` or
`construction`. No test goes red, and integrity gets a writer the registry says doesn't exist.
*Fix (unverified):* laws never narrow. `physics` wraps each `law.step` in `grid.as_writer(law.name)` and Topology
narrows in `apply`. A scan allows `as_writer(` only in `physics.py` and `topology.py`, and `writing(writer=CONSTRUCTION)`
only in `Scene.build`. The tests that use `as_writer("construction")` inside `World.writing`
(`test_ownership.py:145`, `:191`, `test_laws.py:64`, `:90`) move to a construction window.

**S3. `grid.py::CellStore._channel`: handles outlive their narrowing, and a direct write to a topology field skips the
version (both verified, probe).**
(a) `_channel` hands back the window's array itself, so a handle taken inside `as_writer("heat")` stays writable for
the rest of the window, under any writer. sim_core.md §5's `prepare` and its "preallocated outputs" (PR 3) is where
laws start holding arrays across calls. (b) `material`/`original_material` are writable through plain subscripting
for Topology and construction, but only `paint`/`destroy`/`name_region` call `_mark_edited`.
*Failure scenario (b):* PR 3 keys face conductances and `stable_dt` on `topology_version` (§7). One subscript write to
`material` (construction in a test helper, or S2's impersonation) leaves conductances stale with no error, and that is
a physics result, not a crash.
*Fix (unverified):* never hand out the topology channels writable. They change only through the edit methods that
bump the version. Then record in the design that a narrowed handle is valid only inside its block, and have the
orchestrator (S2) hand laws their arrays per call.

**S4. Departures from sim_core.md recorded only in the commit message.**
`grep` over `docs/` finds no mention of `as_writer`, "typed handles" or "emission order". sim_core.md is unchanged and
still states, as contract, things the tree contradicts:
- §5: "read-only views of its `reads` and write handles for its `writes` only, so an undeclared read or write is a
  type error". Reads are not checked at all. `reads` is decoration, yet §5's `bound_reads` cache keys and §6's
  producer closure (sem_stimuli §5) are computed from it. The checklist's first §5 item ("a planted law touching an
  undeclared field raises") is neither met for reads nor deferred.
- §5.1: "the damage package, whose resolvers (one module per kind, a declared tuple)". As built, it is one module with
  an `if load.kind != "strike"` chain.
- §6: `sources` "resolved by heat". `World._power_field` resolves the deposit and heat only consumes `power_w`, so
  `fields.INPUTS` states a falsehood that `test_every_input_kind_has_one_resolver_and_it_is_a_law` passes on.
- §2 places `Changes` with the cells. It is in `law.py`.
A commit message is not a tracker. Under "one owner per contract" and the marker rule, each departure is either an
amendment to sim_core.md (written as the contract, not as a fold table) or a deferral row in `checklists.md` naming
its PR. Typed views and handles may still be the right answer. Choosing runtime narrowing instead is an architecture
change, and CLAUDE.md wants it reviewed on the design first.
On soundness: emission-order keys are sound while a batch is one requester's one invocation. `_power_field` staying
until PR 3 is sound if the registry says "World (interim, PR 3)". Runtime narrowing is unsound as it stands (S2, S3,
no reads). The single damage module is acceptable only with S5's caveat.

**S5. `pyproject.toml` `laws-independent`: blind to two laws in one module.**
`damage.LOADS` and `damage.THERMAL` share `damage.py`, and an independence contract works at module level, so
"no law imports or calls another" is unguarded between them. The test asserts that the contract covers
`{type(law).__module__}`, which collapses the two into one entry and so cannot notice the gap.
*Failure scenario:* `ThermalLaw.step` reuses `_strike_loss`, or calls `LOADS.step` to apply a "thermal load". It stays
green, and integrity gains a hidden coupling outside the fields.
*Fix (unverified):* make `simcore/core/damage/` with `loads.py` and `thermal.py` listed in the contract, shared math
(`_axis_fraction`) in a non-law module, and `region_integrity` (an observer's reduction that `frames.py` imports) out
of the law modules. The test should also assert that no two tuple members share a module.

**S6. `docs/roadmap.md` (Phase 1, line 51) is stale, and a slip went unstated.**
The `World.advance` marker was rewritten from "PR 2 moves it into the step's law list" to "PR 4 moves the window
there". The roadmap still says "step 5a's PR 2 moves the laws' window into the step". `checklists.md:223` implies PR 3
("once the write window moves into the step"). Three places, three PRs. The marker lint passes because it checks only
the file listing. This is the brutal-honesty rule's case: a scheduled band-aid's removal moved and nothing says so.
*Fix:* name the PR once, in the roadmap, and match the checklist to it.

**S7. `law.py::Law.writes` and `fields.FieldSpec.writers`: two owners of one fact, checked in one direction.**
The gate enforces the registry. `check_laws` and `test_every_law_writes_only_fields_that_declare_it` check only that
`law.writes ⊆ registry`. If the registry adds `heat` to `integrity`, heat can write integrity while declaring
`writes=("temperature",)`, and §6's producer closure, computed from `writes`, is wrong. *Fix (unverified):* assert
equality, `{f for f in FIELDS if law.name in f.writers} == set(law.writes)`, in `check_laws`.

## NIT

- **N1. `physics.py::resolve_loads`** discards `topology.apply`'s destroyed count. `LoadEffect.destroyed_cells` is the
  law's prediction ("Topology destroys exactly these"), so two owners report the destruction. Assert they agree, or
  take the count from Topology.
- **N2. `grid.py::MaterialGrid.paint`** names a region and narrows region masks (`_take_cells`) after checking only the
  `material` writer, never `regions`. The two have the same writers today, so it bites only once they diverge.
- **N3. `heat.py::step` and `physics.py::run_physics`** both run `grid.time_s += seconds`, and `time_s`'s setter checks
  the window but no writer. That makes two time movers until PR 3 removes `time_s`. Say so in heat's docstring or
  route heat-alone studies through `run_physics` with a one-law tuple.
- **N4. `applier.py::Applier._strike`** calls the orchestrator (`physics.strike`) itself, so the applier still drives
  resolution instead of appending a `Load` (§5.1's "Inputs declare"). `OUTCOME_MODULES` doesn't list
  `simcore.core.physics`. This is interim until PR 4, but it sits under no marker of its own, and `physics.strike`
  makes the orchestrator name an input kind.
- **N5. `fields.py::LAW_NAMES`** duplicates `physics.DEFAULT_LAWS`'s order, held by a test. That is acceptable given
  the layering. Note it in the registry's docstring as the tuple's mirror, not its owner.
- **N6. `topology.py::apply(writer=...)`** takes a free string checked against two values. A `Literal` type, or a
  separate `construct()` entry point, would push the invariant into the type, per CLAUDE.md's rule.

## Future fit (asked)

- **Fire 6.0b/6.1 (solid, contact at `per_physics_step`):** `_RUN` refuses those cadences loudly, which is correct
  until PR 3. The registry can express `contact_exchange` (contact writes it, solid reads and resets it). S2 must land
  first, or nothing holds those laws to their names.
- **5b bodies:** `Law.step(grid: MaterialGrid, ...)` hands every law the whole grid, including `paint`, `destroy`,
  `writing` and the `time_s` setter. A body container has no parameter in this signature and no gate (S1). Expect to
  change the protocol, which argues for doing the views-and-handles decision (S4) before 5b, not after.
- **`radiant_emitters`:** per-row `(writer, ...)` keys need the gate's current writer at the container, which a
  composed gate (S1) gives for free and the mixin does not.

## Layering

`lint-imports`: 10 contracts kept. The new modules are classified in both forbidden lists, and `fields` is correctly on
the public surface. The internal direction is clean: `fields` ← `writers` ← `grid` ← `topology` ← `law` ← laws ←
`physics` ← `world`/`applier`. No band-aid markers were added. The existing marker was edited, and that edit is S6.
