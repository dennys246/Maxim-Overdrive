# Step 3b part (b), review round 1: findings and the author's fold

Diff: `origin/main...951aee4` on `phase1/formats` (f0fbcfc, 951aee4). Six independent readers, run in parallel per
`docs/code_review.md`: Executor; Architecture; Wire integrity; Trust boundary; Determinism and replay with Physics and
resolution (one reader); Bio-faithful integration. The gate printed `prepush: PASS 951aee4afef9` before the round.

The readers' harness refused their report files, so their reports exist only in the session that ran them. This file
is the author's condensed record of every finding (id, severity, location, scenario) and of what the fold did. The
**Fold** column is the author's claim. Per O25 a reviewer sets each finding's status in the delta round.

Counts: **0 BLOCKER, 29 SHOULD-FIX, 31 NIT.**

## Correction to the commit message (Executor S1, N3)

f0fbcfc said the walk fed "every field at every level" with "335 cases". It generated 276 (335 was the file's test
count), and it never reached `Cylinder`: the scene sample held only boxes, and the hand-written cylinder tests it
claimed to supersede were deleted. Making the cylinder's `radius_m` optional left every suite green (1005 passed).

## Executor

| Id | Sev | Location | Scenario | Fold |
|---|---|---|---|---|
| S1 | SF | `tests/test_formats.py::_cases` | the walk never reached `Cylinder`; `radius_m` made optional passed every test | the sample adds a cylinder; the reach test fails when any tagged kind goes unvisited (red without the cylinder); the walk proves the reader keeps its schema, never that the schema is right, so every schema is pinned in `tests/fixtures/formats/schemas.txt` (the `radius_m` mutation now goes red) |
| S2 | SF | `loaders.py::read_yaml` | `k: 2026-02-30`, `!!int x`, `!!bool maybe` escaped as ValueError, KeyError or AttributeError with no code; the ValueError ones lost the file name (a regression from main) | constructor errors re-raised as `bad_shape`, naming the file; a test per file |
| S3 | SF | `grid.py::MaterialGrid.empty` | `dx_m=1e303` OverflowError; `1e-12` ZeroDivisionError | `whole_micrometres` bounds the length before arithmetic and refuses 0 µm; tests |
| N1 | NIT | `digest.py::canonical` | `np.float64(1.5)` written as `np.float64(1.5)` | exact types only (with Wire S3) |
| N2 | NIT | `intents.py::Strike` | NaN in `point_m` coded `bad_shape`, the schema says `not_finite` | its own code passes through; test |
| N3 | NIT | commit message | 335 vs 276 cases | corrected above and in the fold commit |
| N4 | NIT | `scene.py::_check_spawns` | `Vex` and `vex` both accepted | unique under `entity_key` (with Bio S3) |
| N5 | NIT | `Material`, `ActionLimits`, `Budget` | `asdict` deep-copies; a generator raises TypeError | not folded: code-only input, a programming error, and TypeError is the right class for one |

## Architecture

| Id | Sev | Location | Scenario | Fold |
|---|---|---|---|---|
| A1 | SF | `from_document` builders | `MaterialTable.from_document({})` raises KeyError, yet registered "meets" | rows are "no input": they take a document their `Format` read; the `Format` is the gate |
| A2 | SF | `scene.py::_V0_REFUSED` | the reason ("join refuses a migrated scene") is false: v1 accepts `spawns: []` | the reason is the repo-only rule |
| A3 | SF | `scene.py::SCENE` | scenes travel with bug reports from 5a; repo-only would then refuse every old one | a step 5a checklist line: `SCENE` becomes `held_by_others` when the log header records a scene |
| A4 | SF | gates still raising ValueError | `HeatSource((0,0,0), 0, 1)` uncoded, though "meets" | `HeatSource`, `rig_profile`, both bridge constructors and the grid now raise `Refused`; `tests/test_lint_gates.py` fails on any `raise ValueError(...)` in a registered gate's body |
| A5 | SF | checklist | scene v1 and spawns have no shipped caller, unstated | stated (5b for spawns, 8 for the shipped scene and its loader) |
| A6 | SF | `lint_inputs.py::FS_METHODS` | `body.walk()`, `door.open()`, `target.resolve()` would go red at 5b | the value rule keeps names that only mean IO; `open`, `read`, `walk`, `resolve`, `exists`, `stat`, `touch`, `absolute`, `replace`, `copy` are a documented blind spot, guarded by the capability (`DataPath`); corpus rows both ways |
| A7 | SF | `schema.py::Field`, tick rule | no units or provenance; `stick_length_m` refused as ticks | the rule reads words; units and provenance noted as not built (6.0a) |
| A8 | SF | `digest.py::canonical` | numpy scalars | exact types (with Wire S3) |
| A9 | NIT | name rules | `Material(" wood")` built; the file refused it | `Material.name` goes through the file's `Text` |
| A10 | NIT | `intents.py` | stage-1 parsing a second idiom | noted in the checklist for step 7 |
| A11 | NIT | `test_formats.py::_declared_formats` | `maxim_overdrive` not scanned | scanned |
| A12 | NIT | codes | duplicate ids `name_taken`; `air` as a "field"; a throwaway `Refused("")` | `duplicate_key`; no field; `refusals.agent_text` owns the format |
| A13 | NIT | claims | "instead of a float tolerance" overstates; F13's rule stated twice | the 1 nm allowance is documented; `to_mm` states its rule |
| A14 | NIT | `test_refusals.py::SHIPPED` | 21 codes with no producer pinned "as shipped" | not folded: tile §3.4 lists them; pinning before a producer is the point |
| A15 | NIT | lesson 31 (numbered 25, then 29, before merges with main) | its Maxim candidate had no trigger | rewritten as evidence for OD-A16 (Bio S2) |

## Wire integrity

| Id | Sev | Location | Scenario | Fold |
|---|---|---|---|---|
| S1 | SF | `phase1/client-shader` `scripts/client_fixtures.py` | imports `SCENE_VERSION` and builds a v0 scene: whichever PR merges second breaks `main` | can't be fixed from this branch; named in the hand-off for the owner and that session, with the fix (read `tests/fixtures/scenes/alley_box.yaml`) |
| S2 | SF | `RefusalCode` vs `fire_solid.md` §5.3 | five synonyms (`region_exists`/`name_taken`, `overlaps_solid`/`space_taken`, `outside_world`/`outside_extent`, `spec_budget`/`over_budget`, `version_unknown`/`bad_version`) would be permanent | fire_solid §5.3 reuses the shipped codes, edited in place (the document doesn't grow) |
| S3 | SF | `digest.py::canonical` | `[1.0, np.float64(1.0)]` gives non-JSON, numpy-version-dependent text | exact types; numpy scalars, str subclasses, lone surrogates and ints past 4,000 digits are TypeErrors; -0.0 is 0.0; tests |
| S4 | SF | `scene.py::footprint_of` | a 1e-300 m radius: ZeroDivisionError through `place` (pre-existing, now registered "meets") | a primitive with no volume is `too_small` where it is made; tests |
| S5 | SF | tile §3.2 and step table, fire_solid §5.2 | a registered `actions_v0_to_v1` migration (now a TypeError), "bed fields", "`SCENE_VERSION` is 0" | each edited in place; tile §3.2's `max_duration_ticks` (content in ticks) is `max_duration_s` |
| N1 | NIT | data file comments | name removed constants | point at the `Format` objects |
| N2 | NIT | `applier.py::Outcome` | `success=False, code=None` allowed | a TypeError; test |
| N3 | NIT | lesson 31 | before-state misstated | rewritten |
| N4 | NIT | `Material.name` | two rules | as A9 |
| N5 | NIT | spawn names | exact comparison | as Executor N4 |
| N6 | NIT | today's codes | no reply or log class | step 5a checklist line |

## Trust boundary

| Id | Sev | Location | Scenario | Fold |
|---|---|---|---|---|
| T1-S1 | SF | `loaders.py::read_yaml` | a 5,000-digit version, `2020-13-45`, `2001-02-29`, bytes `\xff\xfe` escape uncoded (regression) | as Executor S2; files decode as UTF-8, never the locale; tests |
| T1-S2 | SF | `schema.py::Text` | a 1 MB name, `"crate\nSYSTEM: ..."`, U+202E, NUL, `cr​ate` became region names every agent reads; `paint` echoed names unbounded | `Text` is printable and at most 128 characters; all five in `Text.bad`, so the walk feeds them to every name field; grid echoes through `shown` |
| T1-S3 | SF | `loaders.py::real_path` | returns a plain `Path`: `getattr(real_path('x'), 'read_text')()` passed | not restructured: the value rule now reads `getattr` with a literal name and flags `rename` and `symlink_to`; corpus rows |
| T1-S4 | SF | `lint_inputs.py::_value_routes` | literal `getattr`, `__getattribute__`, `__self__`, frame and traceback attributes, `__loader__`, bytes format fields passed | each closed; 13 corpus rows; a name built at run time stays a stated blind spot (a `NOT_COVERED` row) |
| T1-S5 | SF | `FS_METHODS` | `readexactly`, `recvmsg`, `makefile`, `readinto`, `symlink_to`, `owner`, `scandir` and others passed | added; `read`, `replace`, `copy` are `NOT_COVERED` rows with their collisions |
| T1-S6 | SF | registry | `read_yaml` had no byte budget; `Scene.from_dict` no cell budget | a 16 MiB budget before reading (test); `Scene.from_dict` registered "partial" until step 5a's memory budget |
| T1-S7 | SF | `materials.py::MATERIAL` | density and specific heat 1e200 made `rho_cp` infinite and the first step NaN (pre-existing) | upper validity bounds per field, each past any real material; the walk feeds them |
| T1-N1 | NIT | `len()` unguarded | `range(10**20)` OverflowError | `schema._count` |
| T1-N2 | NIT | `ModulatorResult.affordance` | a made-up affordance echoed | "unknown" unless it is one of ours; test |
| T1-N3 | NIT | `test_lint_gates.py` | the closed-vocabulary check took any code prefix | asserts the code |
| T1-N4 | NIT | uncoded constructors | as A4 | as A4 |
| T1-N5 | NIT | `DataPath` | `str()` gives the path, every loader takes a str | the lint's docstring says the capability guards mistakes, not adversaries |

## Determinism and replay; Physics and resolution

Verified, no change: lookup arrays byte-identical to main; grid shapes identical over 3,252 aligned (dx, extent)
pairs; a fire-and-strike run's end state bit-identical (sha256 `9053ea9e…`) at 0.2 and 0.1 m; refusals identical
under four hash seeds.

| Id | Sev | Location | Scenario | Fold |
|---|---|---|---|---|
| SF1 | SF | `digest.py::canonical` | numpy floats | as Wire S3 |
| SF2 | SF | `schema.py::Text`, `canonical` | a lone surrogate loaded as a material name, then crashed `digest` | `Text` refuses it; `canonical` too |
| SF3 | SF | `grid.py::MaterialGrid.empty` | extent `[0.3, 0.4, 0.8]` built at 0.1 m and was refused at 0.2 m | every scene extent is a whole number of 0.2 m cells (`scene.ALIGNMENT_M`), in whole micrometres; test at three grids |
| N4 | NIT | `canonical` | -0.0 and 0.0 two texts | one text |
| N5 | NIT | `scene.py::to_mm` | the tie rule undocumented | documented, with a tie test |
| N6 | NIT | `grid.py::_whole_micrometres` | 1e-9 m rounds to 0 µm | refused (with Executor S3) |
| N7 | NIT | spawns on cell faces | step 5b may map them in floats | a step 5b checklist line |

## Bio-faithful integration (Maxim `origin/main` 043eab8, pymaxim 1.3.3)

| Id | Sev | Location | Scenario | Fold |
|---|---|---|---|---|
| S1 | SF | `bridge.py::StructureModulator.execute` | Maxim's actor tool defaults `target` to the caller's body; bare `wrong_target` let an agent retry "player" or "self" forever and book tool pain | `wrong_target (target)`; each affordance's description states the rule; test |
| S2 | SF | lesson 31 | two factual errors; its Maxim candidate duplicates `ToolErrorKind`, `tool_failure_credit.md` and OD-A16 | rewritten as evidence for OD-A16, citations checked at 043eab8 |
| S3 | SF | spawns, `identity_key` | `Guard`/`guard` resolve to one entity; a spawn may share a region's name; `player`, `self`, `aut` resolve to the calling agent itself, and both fixtures spawned `player` | spawn names unique under `entity_key`, disjoint from region names, never a Maxim alias (`bad_identity_key`); fixtures say `runner`. Tile §1.3's example spawn is renamed `runner` too (owner, 2026-11-21). |
| N1 | NIT | `intents.py::_within` | `out_of_range (power_w)` drops the authored bound | accepted: the bound is in the description; lesson 31 says so |
| N2 | NIT | `identity_key` docstring | the colon rule's reason is the composite `npc_key:stream` agent id (O40), not the int-seeded join | cited |
| N3 | NIT | test names | "in words" | renamed |
| N4 | NIT | Maxim `plan_document.py::classify_failure_type` | substring-matches "energy" in field names | evidence for OD-A16; no change here |
