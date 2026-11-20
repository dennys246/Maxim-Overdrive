# Step 2 pre-push review: Executor

**Diff:** `git diff origin/main...HEAD` at aa5fcfa (`phase1/godot-skeleton`). **Lens:** Executor (`docs/code_review.md`).
**Counts:** 0 BLOCKER, 3 SHOULD-FIX, 5 NIT.

## What I ran

All runs used a scratch copy of the tree under `build/s2e/` (deleted afterwards), with Godot's HOME and XDG_* inside it.
No tracked file was edited.

- **Baseline:** `MAXIM_OVERDRIVE_ALL_TIERS=1 .venv/bin/pytest` on `test_godot_gate_fixtures.py`, `test_godot_check.py`,
  `test_golden_compare.py` and `test_client_project.py`. Result: 68 passed in 51 s.
- **Deletions** (each on the scratch copy, then restored):
  - **D1:** `godot_check.py::error_findings` with the error-line scan removed. 6 fixture tests go red: the 4 compile cases,
    the runtime error in a test, and the error before quit.
  - **D2:** `load_all.gd`'s check reduced to `script == null`. The 4 does-not-compile cases go red.
  - **D3:** `godot_check.py::import_step` without `import_changes`. `test_a_script_committed_without_its_uid…` goes red.
  - **D4:** `run.gd`'s `quit(0 if t.passed() else 1)` changed to `quit(0)`. **All 37 tests pass** (NIT S2E-N1).
  - **D5:** `run_godot` with the `timeout=` removed. `-k hang` hangs indefinitely. That is the intended failure, though as a
    hang rather than a red test. I killed it.
  - **D6 (golden):** I deleted the `Crate` node from a scratch `golden.tscn` and ran `ci/godot-golden/run.sh` in the
    local `overdrive-golden` image. Result: `golden_compare: FAIL … a 3220 px blob with ΔE > 10.0`. I also painted the
    crate out of the committed PNG and compared it in numpy: it fails the same way. A whole-frame shift of 1 px gives a
    113 px blob and fails.
- **CI paths, in the image** (x86-64 under Docker emulation, so not a GitHub runner):
  - `godot_check.main` with the Linux 4.7.2 build, headless: `godot_check: PASS`. This is the ubuntu-latest gate step.
  - `run.sh` unmodified: `golden_compare: PASS rig/boxes.png`.
- **Headless golden on the Mac:** `golden.tscn` under `--headless` exits 1 with the refusal message, so the guard works.
  No test exercises it (S2E-S2).
- **class_name without an import:** I added an `EnginePin` reference to a scratch `golden.gd` and ran the scene on a copy
  with no `.godot/`, the way `run.sh` does. Result: `Parse Error: Identifier "EnginePin" not declared` (S2E-S1).

## Checklist "Step 2"

| Item | Delivered? |
|---|---|
| `addons/engine` and `game` layout; Compatibility; every warning at Error; a test reads it | yes (`test_client_project.py`, plus the live check in `unit/test_project_settings.gd`); `directory_rules={}` is held by both |
| `godot_check.py`: timeout, error scan, load check, sentinel, fixtures by deletion | yes; D1–D3 and D5 confirm it; the exit-code half of the runner is unproven (N1) |
| Linux golden job: base by digest, Mesa by version, Godot by SHA-256, vector width fixed, goldens keyed by Mesa, one golden | yes, and it catches a deleted object (D6); it has never run on GitHub; "required" is the owner's setting (B7 says so) |
| §9 probes on 4.7.2, including RG8 with `texelFetch` | yes, except "two runner CPU types", which needs CI; its deferral is not tracked (S2E-S3) |

## SHOULD-FIX

### S2E-S1: the golden run never imports, so it breaks as soon as a golden script uses a `class_name`

**Location:** `ci/godot-golden/run.sh` (the `cp -R client …; rm -rf "$work/client/.godot"` and the `xvfb-run godot …` line).

**Failure scenario:** `run.sh` deletes the import cache and runs `res://tests/golden.tscn` directly. The gate imports
first, and `godot_probes.md` ("`class_name` on a fresh checkout") shows why: without `.godot/`, global classes do not
resolve. I reproduced it on the scene path. A `golden.gd` that names `EnginePin` fails with `Parse Error: Identifier
"EnginePin" not declared` and `Failed to load script "res://tests/golden.gd"`. Today's `golden.gd` uses no `class_name`,
so step 2 passes by luck. Step 8's goldens instantiate `CellVolume`, the frame decoder and other engine classes, and the
job will go red on the first such commit. The cause will look like a renderer fault.

**Fix:** in `run.sh`, run `godot --headless --import --path "$work/client"` under `timeout`, scan its output with the same
grep, and only then call `xvfb-run`. Add the assertion to
`test_client_project.py::test_the_golden_job_renders_under_xvfb_and_keeps_its_frames`.

### S2E-S2: `golden.gd`'s refusal paths, including the headless guard from the errata, have no test

**Location:** `client/tests/golden.gd::_ready` (the headless refusal, the missing `--out=` refusal, the size check).

**Failure scenario:** no test runs `golden.tscn`. A grep of `tests/` and `scripts/` finds only an existence check. Delete
the `DisplayServer.get_name() == "headless"` guard and every test stays green: the gate only loads the script, and CI
renders under Xvfb, where the guard never fires. The guard exists because the errata (§6.1) measured a hang. A
regression shows up only when someone runs the scene headless, as a hang. This is a mechanism the branch claims (errata
§6.1, `godot_probes.md`) with no test that fails without it. Coverage cannot see it because coverage measures only Python.

**Fix:** add a `slow` fixture test that runs `--headless --path <project> res://tests/golden.tscn` through
`gc.run_godot` with `HANG_TIMEOUT_S`. It asserts `golden: --headless draws nothing` and exit 1, not a timeout. Deleting
the guard then turns it red as a timeout. A second case can cover the missing `--out=`. That needs a display, so it can
wait for step 8, but it should be named there.

### S2E-S3: CR-B3's open half is tracked only in the design errata

**Location:** `docs/design/client_rendering.md` (the errata line "CR-B3 stays open until then"); `docs/plans/checklists.md`
step 8; `docs/standards_backlog.md` B7.

**Failure scenario:** two things are open: the "llvmpipe on two runner CPU types" probe, and a golden that can tell the
vector widths apart. The committed golden is flat with 4 colours. The Mac's Metal frame passes against it at mean ΔE
0.009, and its 128-bit and 256-bit frames are byte-identical, so the pin is unproven. The step 8 checklist does not
mention CR-B3, and B7's "Missing" list does not either. The charter (§4) says a finding with no code to mark is deferred
as a backlog row. As things stand, step 8 can land shaded goldens without anyone running the two-CPU comparison, and
CR-B3 would read as closed by default.

**Fix:** add "CR-B3: a shaded golden rendered at 128 vs 256 bits must differ, and agree across Intel and AMD runners
(from `run.sh`'s CPU line in the job history)" to step 8 in `checklists.md` and to B7's Missing list.

## NIT

- **S2E-N1** `client/tests/run.gd::_initialize`: the `quit(0 if t.passed() else 1)` that §7.3 requires is proven by no
  fixture. In D4, `quit(0)` left all 37 green, because the FAIL summary line already fails the sentinel. Either say in the
  docstring that the exit code is belt and braces, or add a fixture that prints a PASS line and then fails, which shows
  the `returncode` branch of `sentinel_findings` against real Godot.
- **S2E-N2** `client/game/main.gd::_ready`: the pin check's `push_error` never runs under a test. `test_main_scene`
  instantiates the scene without adding it to the tree, so `_ready` never fires. Either add it to a SceneTree in the
  runner, or drop the check, since `test_engine_pin.gd` already holds the pin.
- **S2E-N3** `ci/godot-golden/run.sh` (`--name rig/boxes.png`): the step-2 scene has no tier, but its golden sits under
  `rig/`. §6.5's `<tier>/` path implies a tier that this frame does not have. Use `renderer/boxes.png`, or say why it is `rig`.
- **S2E-N4** `docs/standards_backlog.md` B6, "done (step 2; first CI run pending)": the Linux headless gate step passed
  only in the image under emulation (my run). The fixture tests have never run on Linux, because the image has no pytest
  and I did not install one. "Done" before CI has run contradicts CLAUDE.md's "done and verified". Mark it "done pending
  CI" until the first green run.
- **S2E-N5** `ci/godot-golden/run.sh`: the image logs `libxkbcommon.so.0` and `libdbus-1.so.3` as missing. Neither
  matches the error grep today. If a future Godot reports either as `ERROR:`, the job turns red for a reason that has
  nothing to do with rendering. Install both, pinned, or note in the Dockerfile that they are expected.
