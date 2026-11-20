# Step 2 (Godot skeleton): Architecture lens

Diff: `git diff origin/main...HEAD` at `aa5fcfa`. Read: `docs/code_review.md`, CLAUDE.md, `client_rendering.md` §6–§9
and its errata, `boundaries.md` §2.1 and O24, `research/godot_probes.md`, every file in the diff. Measured here:
`scripts/godot_check.py` alone 13.3 s; `tests/test_godot_gate_fixtures.py` 55.2 s (15 tests; the slowest are the
`.uid` import 17.8 s, the clean whole gate 12.3 s, the shared import 8.6 s, the two hangs 5.0 s each).

Counts: 0 BLOCKER, 6 SHOULD-FIX, 6 NIT.

## SHOULD-FIX

**S2A-S1. The golden job reimplements the gate's "Godot's output is the truth" logic in bash, untested.**
`ci/godot-golden/run.sh` (the `timeout 120`, the `grep -E "SCRIPT ERROR|Parse Error|ERROR:"`, the exit-status
check) duplicates `scripts/godot_check.py::run_godot`, `::ERROR_LINE` and `::error_findings`, which have unit tests
and fixtures. Failure: step 8 widens the error pattern (say, `USER ERROR:` or a 4.8 message format) in
`godot_check.py`; the golden job keeps the old grep and passes a run that printed the new error, while the gate
catches it. Two copies of one rule with one guard. Fix: give `godot_check.py` (or a small shared module it and
`golden_compare.py` import) a `run_and_scan` entry the golden job calls, so `run.sh` is only the Xvfb wrapper and
the invocation; or have `golden_compare.py --log` apply `godot_check.error_findings` to the log it already reads.

**S2A-S2. The platform-to-build mapping is copied into two workflows instead of living in the installer.**
`.github/workflows/test.yml` and `.github/workflows/drift.yml` "Install Godot" each carry the same `case
"$RUNNER_OS"` block. `ci/godot.env` is the single source for version and digests, but which build a machine gets is
decided in three places (two YAML copies, plus the Dockerfile's literal `linux-x86_64`). Failure: an arm64 Linux
runner or a Windows leg is added to one matrix; one copy is updated, the other job installs the wrong build or
exits "no pinned Godot build". `test_every_job_that_runs_the_gate_installs_the_pinned_godot_first` pins the
duplication rather than removing it. Fix: `ci/install_godot.sh <dest>` detects the platform itself (`uname -s`/`-m`)
with the explicit argument as an override; each workflow step becomes one line.

**S2A-S3. The probes sit in the shipped project, assert nothing, and nothing reruns them.**
`client/tests/probes/*.gd`. `godot_probes.md` says "the Godot upgrade branch reruns them", but no script, test,
checklist or roadmap row makes that happen; the gate only parses them. They print observations, so a rerun on
4.8 that changed behaviour (e.g. `JSON.stringify` writing `5500.0` for an int) passes silently: they are notes with
a typing obligation, not guards, and they live in `res://` where a future export picks them up and where every
warning promoted by an engine upgrade must be fixed in them too. Failure: the upgrade branch trusts §9's verdicts
because "the probes still load". Fix: (a) turn the two headless, assertable probes into client unit tests now
(`probe_json_ints.gd` into `tests/unit/test_json_ints.gd` with `check_eq`; the Origin probe becomes step 7's
listener test, as the doc already says); (b) move the windowed ones to a separate Godot project (e.g.
`tools/godot_probes/` with its own `project.godot`), and add the rerun to the upgrade procedure in `docs/roadmap.md`
or a backlog row, so the promise has an owner.

**S2A-S4. The engine/game split is a directory name with no check, and GDScript's global `class_name` makes an
upward dependency free.** `client/addons/engine/` vs `client/game/` (boundaries §2.1). Any `class_name` declared in
`game/` is visible to `addons/engine/` with no `preload` or path, so the first step-7 decoder that reaches a game
type crosses the licence and layer boundary (Apache-2.0 engine half depending on rights-reserved game code) with
nothing to notice. B19 (1) covers Python layers only; B19 (3) lists only GDScript size limits. Fix: a backlog row
now (B19 (5) or a new row) naming the rule and a cheap check: no `res://game/` path and no `class_name` declared
under `game/` referenced from `addons/engine/`, run by `godot_check.py` or `test_client_project.py`; land the check
with step 7, when the second engine file arrives.

**S2A-S5. `MAXIM_OVERDRIVE_ALL_TIERS` now means two unrelated things.** `tests/test_godot_gate_fixtures.py::pytestmark`
reuses the physics rig-tier switch (`tests/conftest.py::ALL_TIERS`, the 0.05 m max profile) to mean "run Godot".
Failure: client work needs the 55 s fixture run and must also pay the max-profile physics minute; physics work on a
machine without Godot (a Linux dev box) gets 15 hard failures from a variable it set for rig tiers. Two reasons to
change one switch. Fix: a separate `MAXIM_OVERDRIVE_GODOT=1` (the gate and CI set both), or a `godot` marker
selected by the gate; CLAUDE.md's command block names the Godot one.

**S2A-S6. `client_rendering.md` grew, and now carries text its own errata contradict.**
`docs/design/client_rendering.md` (+17 lines of errata ahead of §0). O22: an existing design document doesn't grow.
The errata block also leaves the wrong sentences in place: §7.3 still says fixtures live in
`client/tests/gate_fixtures/` and "fails on a null `load()`"; §6.5 still gives the path without the Godot version
and says "Mesa pinned by package version"; §6.1 still says "asserts `get_image() != null`"; §8's table still says
160–230 µs and 1.7 ms. A reader of §7.3 builds the wrong gate; "these override the text below where they differ"
is a band-aid on a document. Fix: edit each section in place (each correction replaces a sentence, so the word
count holds or falls), leave the evidence in `godot_probes.md`, drop the block.

## NIT

**S2A-N1. The clean-client gate runs twice per push.** `scripts/prepush.sh` runs `godot_check.py` (13 s), then
`test_the_clean_client_passes_the_whole_gate` runs `godot_check.main` on the same tree (12 s). The test is the
end-to-end proof of `main`, so keep it; drop the separate prepush step instead and let the pytest step be the Godot
gate, or keep the step and make the test use a fixture project. One is redundant on the push path.

**S2A-N2. B6 is marked done before it has run where it is required.** `docs/standards_backlog.md` B6: "**done**
(step 2; first CI run pending)". `ci/install_godot.sh` has never run on a GitHub runner, and the macOS leg's
`Godot.app/Contents/MacOS/Godot` from an unzip (quarantine, signing) is unproven. CLAUDE.md: "done" means verified.
Mark it "done locally; CI pending" and flip it with the green run's link.

**S2A-N3. The pin is restated in `client/addons/engine/engine_pin.gd`, and checked three times.** MAJOR/MINOR/PATCH/
STATUS duplicate `ci/godot.env` (held by `test_the_engine_pin_agrees_everywhere`), and the version is then checked by
`godot_check.py::version_findings`, `tests/unit/test_engine_pin.gd` and `game/main.gd::_ready`. The `_ready` check has
no effect on the shipped path: an exported game embeds the engine it was exported with, and `push_error` doesn't
stop it. It also isn't the engine half's job per boundaries §2.1 (decoder, channel bindings). Either drop
`EnginePin` and `main.gd`'s check (the gate's version step is the guard) or say in its header why a runtime check
earns its place.

**S2A-N4. `LP_NATIVE_VECTOR_WIDTH` is pinned in two files.** `ci/godot-golden/Dockerfile` sets 256;
`scripts/golden_compare.py::VECTOR_BITS` refuses anything else. Changing one fails CI rather than drifting, so it is
safe, but say in each which is the source (or pass `--vector-bits` from `run.sh` reading the image's env).

**S2A-N5. The prepush base can be a stale `origin/main` without saying so.** `scripts/prepush.sh` (BASE selection).
Preferring `origin/main` is right (local `main` lags; the owner merges on GitHub), but the gate never fetches and
never prints which commit it compared against. A worktree whose last fetch predates a merge diffs and ratchets
against an old base; the PASS line looks the same. Print `$BASE` with `git rev-parse --short` and its commit date in
the PASS line; the gate need not fetch.

**S2A-N6. The warning count 49 is a literal in three places.** `tests/unit/test_project_settings.gd` (`seen >= 49`),
`tests/test_client_project.py`, and B6's text. The upgrade branch must find all three. Name it once (e.g. a constant
in the Python test that the GDScript test receives, or one comment both cite).

## Checked, no finding

- `scripts/godot_check.py` (198 lines): each function decides or does; `check` is a four-step list; complexity is low.
  `scripts/golden_compare.py` (152 lines): metric, key derivation and CLI are separate functions; one job each.
- Single source for version and digests: `ci/godot.env` feeds `install_godot.sh`, the Dockerfile (via the installer)
  and `godot_check.py::pinned_version`; the release URL repeats `4.7.2` but in the same file.
- No `TEMPORARY`, `noqa`, `pragma` or loosened tolerance in the diff; §6.2's ΔE thresholds are applied verbatim.
- Engine whys: present in `engine_pin.gd`, `main.gd`, `run.gd`, `golden.gd` and the Dockerfile/run.sh (Xvfb,
  llvmpipe); `project.godot`'s `directory_rules = {}` is explained in the errata and `test_project_settings.gd`.
- Gate fixtures are in `tmp_path`, never in `client/`; Godot's HOME and XDG dirs are inside the work directory;
  `build/` is ignored, and the gate run here left the tree clean.
- `.dockerignore` keeps the image's inputs to the three pinned files.
