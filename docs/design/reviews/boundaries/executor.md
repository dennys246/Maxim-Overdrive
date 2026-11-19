# Design review: Executor (boundaries.md)

Lens: Executor, design-time. Design: `docs/design/boundaries.md` at `47add00` (branch `phase1/design-v2`). Date:
2026-11-16. Questions: is every claim the design makes about the code true, and can every check it proposes fail?

Read against: the code on `.worktrees/act-validation` at `2f200b5`, `pyproject.toml`, `scripts/prepush.sh`,
`tests/test_determinism.py`, `tests/test_tooling_config.py`, `data/`, and the project venv (Python 3.14.6,
pymaxim 1.3.3). Nothing in either worktree was changed. Everything below marked *verified* was run in scratch copies:
- `src/` renamed to `maxim_world` with an empty `maxim_overdrive`, then `lint-imports` with the design's contracts
  written out (import-linter 2.16 / grimp 3.20 on 3.14; import-linter 2.15 / grimp 3.18 on Python 3.10);
- the same copy with violations planted (function-local `import maxim`, `importlib.import_module("time")`,
  `__import__("random")`, `from os import urandom`, a law importing the root package and `sem_env`);
- the whole repo renamed mechanically (sed over `src/`, `tests/`, `scripts/` and `pyproject.toml`) and the full test
  suite with coverage;
- `tests/test_determinism.py::findings` on evasive sources;
- the loaders and `Scene.from_dict` on malformed input;
- the shared venv's editable `.pth` copied into a scratch venv, to see which tree `lint-imports` reads.

Counts: **3 BLOCKER, 9 SHOULD-FIX, 3 NIT.**

## What checks out

- `src/maxim_overdrive/` has exactly the five parts named (plus a root `__init__.py` that re-exports `config`,
  `world.grid`, `world.scene` and `world.world`).
- Only `sem_env/bridge.py` imports `maxim` (lines 34 and 39, one under `TYPE_CHECKING`, one in a `try`). `_compat`
  imports nothing from Maxim.
- No module under `src/` imports `time`, `random`, `datetime`, `uuid` or `os`. No `importlib` or `__import__` either.
- `tests/test_determinism.py`'s AST scan bans the modules `random`, `secrets`, `uuid`, `time`, `datetime`, `timeit`;
  numpy's global RNG; the names `os.urandom`, `date.today`, `*.SystemRandom`; builtin `hash`; unseeded
  `default_rng`/`PCG64`/`SeedSequence`. It scans every file under `src/maxim_overdrive/` except a future `server/`,
  plus `tests/`. It does not ban `os`, `threading`, `asyncio`, `socket`, `websockets`, `importlib` or `__import__`.
  "Checks part of it" is accurate.
- `data/` holds `rigs/{laptop,rig,max}.yaml`, `materials/core.yaml` and `world/actions.yaml`. `core.yaml`'s own
  header calls `fracture_energy_j_m3` and `degrade_*` "GAMEPLAY CALIBRATION, not measured physics". Accurate.
- Every named gate exists under that name: `config.RigProfile.load`, `config.MaterialTable.load`,
  `config.ActionLimits.load`, `world.scene.Scene.from_dict`, `sem_env.bridge.parse_action`,
  `imagination.spec.place`.
- `world.snapshot` does the quantizing B-6 names (`crack`, `glow`, uint8, plus a float16 temperature).
- B-1, B-2, B-3 and B-12 are expressible in import-linter, and B-2 works without pymaxim installed: grimp records
  `sem_env.bridge -> maxim` from the source, not from the installed package (*verified* on both Python versions; a
  function-local `import maxim.embodiment` planted in `world/heat.py` turns B-2 and B-3 red).
- A layers contract catches a law that imports the root package's re-exports: `world.heat -> maxim_world ->
  maxim_world.world.world` is reported as a chain (*verified*).
- After a mechanical rename the suite passes: 509 passed, 4 xfailed, 100% branch coverage (*verified*). The rename
  is mechanical as claimed; what it silently loses is in S-5.

## BLOCKER

### X-1. `lint-imports` in a worktree reads the main checkout, so a planted violation passes

`scripts/prepush.sh::PY`, the design's Enforcement section ("plant a violating import and watch the gate go red").

The shared venv's editable install is `_editable_impl_maxim_overdrive.pth`, which puts
`/Users/.../Maxim-Overdrive/src` (the **main checkout**) on `sys.path`. CLAUDE.md tells worktrees without their own
venv to use it (`PYTHON=<venv>/bin/python scripts/prepush.sh`). pytest is safe because `pythonpath = ["src"]` puts
the worktree first, and mypy reads `files = ["src", ...]` directly. grimp is not: it finds the root package through
the import system.

Failure scenario, *verified*: a scratch copy of act-validation with `import time` planted in `world/heat.py`, a
forbidden contract on `maxim_overdrive.world`, and the shared `.pth` installed. `lint-imports` with no `PYTHONPATH`
prints `sealed KEPT`. It analyzed the main checkout. With `PYTHONPATH=src` it prints `sealed BROKEN`. The "plant it
and watch it go red" proof would itself come out green in a worktree, the normal way of working here. After the
rename lands on main, every other worktree's gate would lint main's code and pass.

Fold: the gate step runs `PYTHONPATH=src lint-imports` (or the import-linter Python API with `sys.path` set
explicitly), and a tooling test asserts that grimp resolved each root package to a path under the repo being
checked.

### X-2. B-4 leaves out the only gate that has a shipped caller, and its lint rule cannot see it

`sem_env/bridge.py::StructureModulator.execute`, the B-4 gate list, the B-4 Enforcement row.

`execute(self, affordance: str, params: dict[str, Any])` is what Maxim calls with an NPC's tool call. Its own
docstring says "This is a trust boundary". `parse_action` is its helper, and the `target` checks (namesake, other
entity) live only in `execute`, not in `parse_action`. Of the six named gates, only `parse_action` has a caller on
the shipped path, and that caller is `execute`. `place` and `from_dict` have no `src/` caller except each other
(`spec._read` calls `Scene.from_dict`), and the loaders are called by tests and `World.from_scene`.

The proposed rule ("every public function taking a `Mapping` or `object` parameter is a listed gate or its private
helper") does not see `execute`: its parameter is `dict[str, Any]`, not `Mapping` or `object` (*verified* by an AST
pass over `src/`, below). Failure scenario: a second modulator lands with `execute(self, affordance: str, params:
dict[str, Any])` that skips `parse_action`. The B-4 lint passes, and "there are no other doors" is certified while
a door stands open. The protocol decoder that B-4 lists for later will also take `bytes` or `str`, which the rule
doesn't match either.

Fold: name `StructureModulator.execute` as the gate and `parse_action` as its helper. Key the rule on where values
come from, not on annotations. The workable form is an explicit registry: gate name to its rejection-path test file.
The lint then checks that every public callable reachable from an outside entry point (the SEM `execute`, the
loaders, later the protocol) is registered.

### X-3. B-10's check guards copies, while the channel it names stays open

`world/world.py::snapshot`, `sem_env/bridge.py::RegionSensor`, `sem_env/bridge.py::StructureModulator`, the B-10
Enforcement row.

Nothing outward is a view today. `snapshot` returns `grid.material.copy()` and freshly computed `crack`, `glow` and
`temperature_c` arrays. `RegionSensor.read` returns a `SensorReading` with a Python `float` and a new `extra` dict.
Setting `writeable=False` on those copies, and testing that writing raises, gives a test that can go red only if
the flag line is deleted. It protects no world state.

The mutation path the design names ("a sensor that nudges a value") is the live object graph. `RegionSensor` holds
`self._world`, and so does `StructureModulator`. `to_maxim_entity` hands both to Maxim inside an `Entity`. Through
them, all of these are writable: `world.grid.temperature` and `integrity`, `world.sources` (a public dict),
`world.limits` (`World` is not frozen), `grid.regions`, and `grid.materials.conductivity` / `fracture` /
`degrade_*`. Those last are `MaterialTable`'s shared arrays, which physics reads every substep. Failure scenario: a
sensor, or anything holding the Entity, writes `sensor._world.grid.materials.conductivity[4] = 0`. Every later turn
changes, and the B-10 test stays green. Marking the grid's own arrays read-only isn't a fix either: `heat.substep`
and `damage` write them in place.

Fold: either make sensors hold a read-only facade (a narrow `WorldView` exposing reads, with the arrays it hands
out as read-only views), or state honestly that B-10 is held by review, and name the facade as the real fix with a
backlog row. Also make the material table's arrays read-only after construction (`MaterialTable.__init__`). Nothing
writes them after `__init__`, so a test that writing raises is a real guard there.

## SHOULD-FIX

### S-1. `os.urandom` cannot be written as an import-linter contract, and the AST scan misses the other ways in

The B-3 forbidden list; `tests/test_determinism.py::_name_findings`, `::BANNED_MODULES`.

*Verified*: putting `os.urandom` in `forbidden_modules` makes the whole run error with "Invalid forbidden module
os.urandom: subpackages of external packages are not valid." That is every contract at once, not only B-3. The
design says the AST scan "stays for calls and names imports can't show". *Verified*: the scan returns no findings
for each of these:
- `from os import urandom; urandom(8)`;
- `import os; os.getrandom(8)`;
- `importlib.import_module("time")`;
- `__import__("random")`;
- `import threading`.

import-linter misses the dynamic two as well (a planted `importlib.import_module("time")` and `__import__("random")`
left B-3 KEPT).

Fold: forbid all of `os` and `importlib` in the core (nothing in the core or below it imports either today, so it
costs nothing). Add `os`, `importlib`, `threading`, `asyncio` and `socket` to the scan's banned modules, and
`__import__` to its banned calls, with `test_the_scan_catches` cases for each.

### S-2. The B-8 layers fail on today's code as listed

The B-8 layer list.

*Verified* with `|` siblings, import-linter's independent form: `maxim_world.config is not allowed to import
maxim_world.checks` (config.py line 12), and `maxim_world.imagination is not allowed to import
maxim_world.world.scene` (spec.py line 22). Layer 1 must be `config` above `checks`. Layer 4 needs scene below
imagination, or the non-independent `world.scene : imagination`. *Verified* KEPT on both 2.15 and 2.16. The `:`
form also allows `scene -> imagination`: a planted upward import there went unreported. Splitting scene below
imagination is the stricter, accurate stack. Write the order as it will be committed, and say that the first run is
red until it is.

### S-3. Three of the six "gates" don't refuse bad input, and the "typed, frozen" claim is false for one

`config.py::RigProfile.load`, `config.py::MaterialTable.load`, `world/scene.py::Scene.from_dict`,
`config.py::MaterialTable`.

*Verified*:
- **`RigProfile.load`** uses `yaml.safe_load`. A file with `name:` twice and a `bogus:` key loads, as
  `name='y'`. A missing key is a bare `KeyError('name')`. There is no version.
- **`MaterialTable.load`** has no version, no duplicate-key check and no unknown-key check. It accepts
  `conductivity_w_mk: -5`, `fracture_energy_j_m3: -1` and `density_kg_m3: 0`, and the last raises
  `ZeroDivisionError` later, in `diffusivity_m2_s`.
- **`Scene.from_dict`** promises "Any malformed shape is a ValueError" in its docstring. It raises `KeyError` for
  `{}` and for a box with no `min_m`, and `TypeError` for `extent_m: 3`. `spec._read` happens to wrap these, but
  `from_dict` called alone is not a gate.

Only `ActionLimits.load` (strict loader, version, exact keys) and `parse_action`/`place` meet the bar PR 1 set.
`MaterialTable` is a mutable class whose arrays are writable, not a typed frozen object. Listing these as gates in
`lint_standards.py` would certify behaviour they lack. Fold: list them as gates-to-be, with the hardening as part of
`phase1/boundaries` or a backlog row (B3/B4), or harden them in that PR, with a rejection-path test each.

### S-4. The B-4 lint rule's false positives and misses, measured on today's code

The B-4 Enforcement row.

An AST pass over `src/` for public functions with a parameter annotated `object` or `Mapping[...]` finds these:
- **Gates (3):** `parse_action`, `place`, `Scene.from_dict`.
- **False positives (4):** `checks.finite_real`, `checks.whole_number`, `checks.finite_vector` (public validation
  primitives, called from everywhere, neither gates nor private helpers), and `MaterialTable.__contains__(name:
  object)`, a dunder.

It misses:
- `StructureModulator.execute` (X-2);
- `MaterialTable.__init__(materials: dict[str, Material])`;
- all three loaders, whose parameter is `str | Path`, so the rule cannot see the gates it lists;
- the dataclass constructors that validate raw values in `__post_init__` (`Box`, `Cylinder`, `Scene`, `HeatSource`,
  `Strike`, `Ignite`, `ActionLimits`, `RigProfile`). CLAUDE.md places validation there ("validated where primitives
  are made").
- `RegionSensor(world, region, quantity: str)`, which refuses unknown quantities.

The rule as worded will need an exemption list on day one, the band-aid shape CLAUDE.md forbids. See X-2's fold.

### S-5. The migration silently drops the game package from coverage and from the determinism scan

The Migration section; `pyproject.toml::[tool.coverage.run].source`, `[tool.hatch.build.targets.wheel]`,
`tests/test_determinism.py::PACKAGE`, `tests/test_tooling_config.py::test_coverage_measures_branches_over_src_and_scripts`.

The migration lists "imports in `src/`, `tests/`, `scripts/` and docs". Package-name strings outside import
statements are:
- `pyproject.toml`: `packages = ["src/maxim_overdrive"]`, `"data" = "maxim_overdrive/_data"` and
  `source = ["maxim_overdrive", "scripts"]`;
- `tests/test_determinism.py`: `PACKAGE = ROOT / "src" / "maxim_overdrive"`;
- `tests/test_tooling_config.py`: the equality assertion on the coverage source;
- `README.md`: the import examples.

*Verified*, after a mechanical sed over all of them: coverage measures 15 files, which is the 14 engine modules
plus `scripts/lint_standards.py`, and **not** `src/maxim_overdrive/__init__.py`. The determinism scan's `PACKAGE`
becomes `src/maxim_world`, so the game package is never scanned. `test_tooling_config` passes, because it pins the
renamed set. Both are silent today, because the game package is empty. They stop being silent the day the lab or
its scenarios land there, which is the point of the package.

Fold: coverage `source` lists both packages, and `test_tooling_config` pins all three. The determinism scan walks
every package under `src/` except the transport. Add a test that fails if a package under `src/` is absent from
either list.

### S-6. Pinning import-linter breaks the supported Python floor; its cache dirties the tree

`pyproject.toml::[project.optional-dependencies].dev`, `scripts/prepush.sh` (the dirty-tree check).

*Verified*: import-linter 2.16 (current) and grimp 3.20 declare `Requires-Python >=3.11`. On Python 3.10, `pip
install import-linter==2.16` fails ("Could not find a version that satisfies the requirement"). The last release
for 3.10 is 2.15 (with grimp 3.18), and it handled every contract here. The repo declares `requires-python =
">=3.10"` and `mypy.python_version = "3.10"`. Pin `import-linter==2.15` (and grimp), or raise the floor knowingly.

*Verified*: `lint-imports` writes `.import_linter_cache/` into the working directory. The directory is not in
`.gitignore`, and `prepush.sh` dies with "the gate changed the working tree while it ran". The failure is loud, but
the design should name the fix: `--no-cache`, or an ignore entry.

### S-7. B-9's check misses half of what actions mutate, and its mechanism is unspecified

`sem_env/bridge.py::StructureModulator.apply`, `::_ignite`, `imagination/spec.py::place`, `world/scene.py::Scene.build`,
the B-9 Enforcement row.

`apply` changes cells only through `damage.strike` (`grid.integrity -=`, `grid.destroy`). `ignite` and `extinguish`
write no cells: they set and pop `World.sources`, which changes every later turn. A test of "every cell write" never
sees them. `imagination.spec.place` writes cells (`grid.paint`, `grid.name_region`) outside both `World.advance`
and intent application, and so does `Scene.build`. B-9 must say whether imagination becomes an intent and whether
construction is exempt. The design also doesn't say how a test observes "every cell write". NumPy writes can't be
intercepted, and toggling `writeable` around `advance` conflicts with the in-place updates in `heat.substep`. Name
the mechanism (for example, state mutated only through one `World._apply(intent)` choke point, with a test that a
state digest changes only across that call and `advance`), or the row is a check in name only.

### S-8. B-3's "the core never imports the outside world" is false today, and its scope is narrower than the scan's

`world/world.py::World.from_scene`, `config.py`.

The core (`maxim_world.world`) imports `config`, which imports `yaml` and `pathlib`. `World.from_scene` calls
`MaterialTable.load()` (disk I/O, from whatever `data_dir()` resolves to) when `materials` is omitted, and every
test and README example omits it. A replay recorded against one installed material table replays against another
with no error. Nothing in B-3 names file I/O. Separately, the B-3 contract seals only `world`, but `sem_env` runs
inside the turn (Maxim calls `execute` mid-session, and it builds `ModulatorResult`s that a log will record). The
existing AST scan covers `sem_env` and the import contract does not. Fold: put `sem_env` (or at least its action
path) in the sealed set, make `materials` and `limits` required inputs of the core (CLAUDE.md, "Push invariants
into types"), and keep loading in the host.

### S-9. Packaging puts all of `data/` in an Apache-2.0 engine, and the B-5 split will need the engine to reach game data

`pyproject.toml::[tool.hatch.build.targets.wheel.force-include]`, `config.py::data_dir`,
`config.py::MaterialTable.load`, `world/world.py::World.from_scene`.

The migration attaches `_data` to the engine: the whole `data/` tree goes into `maxim_world/_data`, in a
distribution whose `license = "Apache-2.0"`. When material table v1 moves the calibrations to `content/`, the
engine's default loaders (`MaterialTable.load()` with no path, and `World.from_scene`'s fallback) can no longer
build a complete `Material`: `fracture_energy_j_m3` and `degrade_*` are required fields. Either the engine reads a
game-owned path, a B-1 violation by data that import-linter cannot see, or the defaults break. `data_dir()` also
assumes the module sits exactly two levels below the repo root (`here.parents[1] / "data"`). `color_rgb` is in
neither of B-5's two halves; it is presentation (B-6). Fold: state now that the engine's loaders take explicit
paths with no default into game data, and say which package `content/` ships in and under which licence.

## NIT

### N-1. Name the import-linter contract type for B-2

The B-2 Enforcement row.

"Only `sem_env` may import `maxim`" is the `protected` contract: `protected_modules = maxim`, `allowed_importers =
maxim_world.sem_env`. *Verified* KEPT on today's code and BROKEN by a planted import, on 2.15 and 2.16, without
pymaxim installed. A `forbidden` contract with `source_modules` must be updated by hand for every new root package
(the game, B-7's harness). `protected` covers them automatically.

### N-2. The rename changes a string Maxim sees, and no test covers it

`sem_env/bridge.py::to_maxim_entity`.

`metadata={"source": "maxim_overdrive.sem_env", ...}` becomes `maxim_world.sem_env` under a mechanical rename.
Entity metadata can reach an agent's context and a cradle's records. No test asserts it. Decide whether it is a
contract, and pin it with a test or drop it.

### N-3. B-9's wording

The B-9 "Lands" line.

"`StructureModulator.apply` writes cells directly" is loose. It writes them through `damage.strike`, and writes
`World.sources` directly (S-7). The distinction matters for what the B-9 test must observe.
