# Delta round: Trust boundary and Performance, step 3b(a) fold

Scope: `git diff 3a0d482`, the uncommitted fold in the working tree, including its new files. I re-probed on an rsync
copy (`scratchpad/3b/review/dcopy`) using the worktree's venv, against `origin/main` extracted with `git archive`. The
worktree is untouched. Timings are CPU time (`process_time`), minimum of 3 to 5 runs, measured at a load average of
about 14. `tests/test_extremes.py` and `tests/test_lint_gates.py` pass on the copy (148 tests).

**Correction to my round-1 S6 number.** I measured 1.45 s for `advance(0.5)` under heavy load. This round, at a load
average of 14, it came out at 1.16 s on the fold and 1.26 s on main. The builder's 0.68 to 0.74 s on a lightly loaded
machine is plausible. My figure was a loaded upper bound, not the machine's speed.

## Status of my round-1 findings (set from the tree)

| id | status | evidence |
|---|---|---|
| B1 Cylinder overflow through `place` | **fixed** | `scene.py::_coordinates` bounds every coordinate and radius to 1 km before any arithmetic, and `mask` squares as `r*r`. A radius of 1e200, 1.4e154 or 1e300, a centre of 1e200, an origin of 1e308, and an origin of 999 with a 2 m box are all refused as `SpecRejected`. `Scene.build` with a 1e200 radius refuses with `ValueError`. |
| S1 lint_inputs evasions | **open** | Every literal spelling I listed is now caught except `importlib.import_module("pickle").loads(b)` and `__import__("pickle").loads(b)`. Those slip through because of a new chain-skip defect, which also blinds checks that worked before (D-B1 below). |
| S2 registry gaps and inheritance | **fixed** | Rows exist for `Applier.apply`, `primitives_from_data`, `Box`, `Cylinder`, `Material`, `MaterialTable`, `ActionLimits` and `HeatSource`. Planted modules: a direct subclass, an attribute base (`bridge.StructureModulator`), a two-level subclass and a sensor subclass are all flagged. The `import ... as SM` alias base and `self.name` set in `__init__` are not, and the docstring says so. A tuple assignment is not flagged and is not documented (D-N3). `check_gates` is clean on the tree. |
| S3 "meets" without closed codes | **fixed** (the registry is now honest); the codes themselves are **deferred** | Every agent-facing row now reads `partial: free-text refusals until the refusal-code enum (plan step 3b part b, WT-S1)`. The trigger is real: `docs/design/tile_and_client.md` §3.4 and its step table put "the refusal-code enum" in 3b. |
| S4 budgets after allocation | **fixed** | `_within_world_rules` checks extent, ownership and mass before any mask is computed. A spec refused for extent now costs 0.66 ms (main: 58.7 ms). An "occupied" refusal raised inside the window rolls back: material and regions are unchanged, the arrays are read-only, no frame is published and the window is closed. |
| S5 paint rebuilt every region | **fixed** | `_take_cells` copies only the regions a paint takes cells from, and reads only the box the mask covers. Under load on the alley (1.92e6 cells, 40 regions): build 220 ms (main 272), `place` with 32 primitives 121 ms (main 340), and one paint over 38 regions inside a window 9 ms. Each mask is computed once. |
| S6 physics slower than real time | **deferred** (B5 row, step 5a), honest with one wording NIT | The Known gap reads: 0.7 s lightly loaded at 1.92e6 cells, 1.45 s under heavy load, 3.9 s at 5e6 (loaded), "1.4–7.7× real time", with min-of-N, `process_time` and the date. The numbers are stated with their conditions. The range's ends, though, come from different load conditions (D-N4). |
| N1 unhashable quantity | **fixed** | `RegionInstrument` raises `ValueError` and `Frame.reading` raises `ValueError` for a list. |
| N2 uncached `Frame.reading` | **rejected** (author's NIT call) | The reason given, lab-only and no optimization without a profile, is acceptable. Revisit when an NPC percept reads frames. |
| N3 a full window for ignite and extinguish | **fixed** | `World.writing(cells=False)`: ignite copies no cells, publishes no frame, and commits the sources. |
| N4 freeze failure half-commits | **fixed** | A `MemoryError` planted in the third `frozen()` call: the temperature is rolled back, the arrays stay read-only, the sources are unchanged, no frame is published and the window is closed. |
| N5 `.2f` echo | **fixed**, with a new wording NIT (D-N2) | |
| N6 raw region echo | **fixed** | An unknown region is now echoed through `shown`. A 1e6-character region gives a 66-character message. The other two messages echo only a name already in the table. |
| N7 substring test-name check | **fixed** | `_identifiers` reads names from the syntax tree. |
| N8 `range(10**20)` | **fixed** | Refused as `ActionRefused ... got <a range>`. |

## New findings

### BLOCKER

**D-B1. `scripts/lint_inputs.py::unsafe_findings` and `::input_findings`: the "judge a chain once, at its end" skip hides every call whose result is used through an attribute. That blinds both rules to the commonest spellings, and HEAD caught them.**

Both functions build `inner = {id(n.value) for n in ast.walk(tree) if isinstance(n, ast.Attribute)}` and skip those
nodes. The skip is meant to stop `yaml.unsafe_load` being judged twice, once at `yaml` and once at the full name. But
the value of an `Attribute` can be a `Call`, and that skips the call itself.

Probes, HEAD (3a0d482) versus the fold:

| Source | HEAD | fold |
|---|---|---|
| `open(p).read()` in `src/simcore/core/` (input rule) | caught | **missed** |
| `Path(p).open().read()` in `src/simcore/core/` | caught | **missed** |
| `np.load(p).copy()` in `src/simcore/core/` | caught | **missed** |
| `json.loads(s).get("a")` in `src/simcore/core/` | caught | **missed** |
| `np.load(p, allow_pickle=True).item()` in `tests/` or `scripts/` (unsafe rule) | caught | **missed** |
| `importlib.import_module("pickle").loads(b)` | missed | **missed** |
| `__import__("pickle").loads(b)` | missed | **missed** |

What still catches some of these:
- `json` imports in `src/` are still refused by the import-linter contract.
- In `src/simcore/`, the `importlib` import is still flagged.
- Nothing catches `open(...).read()` or `np.load(...).copy()` anywhere in `src/`.
- Nothing catches `np.load(..., allow_pickle=True).item()` outside `src/`. That is the standard idiom for loading a
  pickled object from an `.npy` file, and it unpickles.

`tests/test_lint_gates.py` has no chained case, and its 24 evasion tests use the unchained form
(`m = importlib.import_module('pickle')`), so the suite passes. The guard for CLAUDE.md's rule ("Only the file gates
read input, and nothing unpickles", `Guard: scripts/lint_inputs.py::check_inputs`) is now weaker than it was before
the fold, on its most likely inputs. The fold reports S1 as fixed with "reverted (HEAD's module: 23 red)", which
proves the new cases, not the old ones.

Fix:
- Skip only an `Attribute` or `Name` that is the `.value` of an `Attribute` (`isinstance(n.value, ast.Attribute | ast.Name)`), never a `Call`.
- Add the chained rows above as permanent tests.
- Rerun HEAD's own cases against the new module as the red-first check.

### SHOULD-FIX

None.

### NIT

- **D-N1.** `scripts/lint_inputs.py::_unsafe_call` still misses spellings that its "named in any way" wording invites.
  The docstring's "guards mistakes, not adversaries" covers them, but its eval and exec sentence overstates. The
  misses:
  - a positional `allow_pickle`: `np.load(p, None, True)`;
  - a `SafeLoader` subclass that registers yaml's Python constructors (`L.add_multi_constructor("tag:yaml.org,2002:python/", yaml.constructor.UnsafeConstructor.construct_python_object)`), which counts as safe because of its base;
  - `__builtins__["eval"]`, `vars(builtins)["eval"]` and `builtins.__dict__["exec"]`;
  - a `yaml.CUnsafeLoader` or `yaml.CFullLoader` attribute named on its own. Each is still caught when passed as
    `Loader=`, so this one is cosmetic.

  The fix: count positional argument 3 of `numpy.load`; flag `add_constructor` and `add_multi_constructor` whose
  argument names `yaml.constructor`; flag `__builtins__` and `builtins.__dict__`; add the C loaders to `UNSAFE_YAML`.
  Pandas, joblib and torch are not in the lockfiles, so their unpicklers don't matter today.
- **D-N2.** `src/simcore/core/imagination.py::_within_world_rules`: `:.3g` turns 1,999.8 m into "too large: 2e+03 m
  across" and 650 kg into "6.5e+02 kg". The echo is bounded, but it reads worse than before. Use `:.4g`, or `:,.0f`
  after clamping to `MAX_EXTENT_M`, which now holds.
- **D-N3.** `scripts/lint_gates.py::_members`: `name, affordances = "d", {}` (a tuple target) still hides a Modulator,
  and the new docstring lists only `__init__` members and aliased bases as unseen. Either handle `ast.Tuple` targets
  or name the case.
- **D-N4.** `docs/architecture.md` (Known gaps, physics) and `docs/standards_backlog.md::B5`: "1.4–7.7× real time"
  pairs a lightly loaded alley figure (0.7 s) with a loaded 5e6-cell figure (3.9 s). A like-for-like statement would
  be: lightly loaded, 1.4× at 1.92e6 cells and about 3.6× at 5e6 by linear scaling; loaded, about 2.3 to 2.9× and
  7.7×. The text does give each number's conditions, so this is wording, not a false claim.
- **D-N5.** `src/simcore/core/checks.py::_BoundedRepr._sorted_set` sorts and reprs every element before truncating to
  `maxset`. `shown(set(range(10**6)))` takes 777 ms for a 33-character answer (a 1e6-key dict takes 15 ms). JSON
  can't make a set, but YAML's `!!set` can, and so can any Python caller (`execute` with `{"energy_j": set(...)}` took
  the same path in a probe). The fix: sort only when `len(x) <= some bound`; past it, print `<a set of n>`.
- **D-N6.** `src/simcore/core/frames.py::Frame._region` still raises `KeyError` for an unknown region, now through
  `shown`. No row covers `Frame.reading`, and the registered caller `RegionInstrument` pre-checks, so it is
  unreachable from untrusted input today. A `ValueError` would match §5.4 if an observer ever passes a name straight
  through.

### Performance of the fold's own changes

- `_bounding_box` costs three full-grid `any` reductions per paint, and `_take_cells` costs O(R · box) per paint. Both
  are well inside the measured 9 ms for a paint over 38 regions.
- Inside a window that has painted, `grid.regions` rebuilds a frozen `Region` for each touched mask on every access
  (`_region_table`). No reader does that today: `paint` and `name_region` use `_region_names`, and strike and advance
  don't paint. It is a trap for a future law that reads regions inside a painting window. It is not a finding yet.
- The sources-only window removes the about 54 MB copy per ignite or extinguish on the alley. The cell window is
  unchanged: two copies, 2 to 5 ms at tile scale. B5 now records it as fitting.

## Counts

Round-1 findings (B1, S1 to S6, N1 to N8):
- fixed: 12 (B1, S2, S3, S4, S5, N1, N3, N4, N5, N6, N7, N8)
- deferred: 1 (S6, B5 at step 5a; the S3 codes are also deferred, to 3b part b)
- rejected: 1 (N2, the author's NIT call)
- open: 1 (S1, through D-B1)

New: **1 BLOCKER** (D-B1), **0 SHOULD-FIX**, **6 NIT**.
