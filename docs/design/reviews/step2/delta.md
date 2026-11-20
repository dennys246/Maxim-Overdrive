# Step 2 delta review (fold a840630..9911998)

**Counts:** 0 BLOCKER, 2 SHOULD-FIX, 5 NIT.

## What I ran

Everything ran on a copy (`git archive 9911998`) under `scratchpad/s2d/`, with HOME and XDG_* inside it. I used the worktree's `.venv/bin/python` read-only and Godot 4.7.2. I wrote nothing to the worktree, and `git status` was clean afterwards. The copy is deleted.

- **Runner (S2C-B1).** I imported the copy, then added `tests/unit/async/` with three tests:
  - awaits 2 frames, then `check(false)`: **FAIL**, reported as "late failure";
  - no check: **FAIL**, reported as "made no checks";
  - adds a node, awaits 5 frames plus a 0.1 s timer, then checks: **PASS**. Alone, the sentinel read `client-tests: PASS 9 tests`, exit 0.
  - A `SCRIPT ERROR` after an await still prints the PASS sentinel. The gate's error scan catches it, which is the design. No finding.
- **Runner mutations.** Removing `await` before `suite.call` turned both new fixtures red. Replacing `t.finish()` with `pass` turned the no-check fixture red.
- **Fixtures.** `MAXIM_OVERDRIVE_GODOT=1 pytest tests/test_godot_gate_fixtures.py tests/test_godot_check.py tests/test_client_project.py tests/test_golden_compare.py`: 83 passed.
- **golden_run mutations.** Each was applied alone, then `tests/test_golden_run.py` was run:
  - drop `exit_findings`: red (case1);
  - drop the missing-frame check: red (case2);
  - drop `error_findings`: red (case0 and the hang test);
  - drop `import_step`: red (failed-import test);
  - drop `judge`: red (differs test);
  - draw with `--path CLIENT` instead of the imported copy: **all 11 pass** (S2D-S2).
- **Isolation scan.** I ran `tests/test_isolation.py::findings` on 9 probe forms (S2D-S1). I also grepped every `subprocess`/`os.exec`/`os.system` call in `scripts/` and `tests/`.

## Checks (1)–(5)

1. **S2C-B1: fixed and verified.** `run.gd::_initialize` awaits `_run_suite`, which awaits each `suite.call`. `test_context.gd::finish` fails a test with zero checks. Legitimate async tests still pass.
2. **`golden_run.py` does reuse `godot_check`.** It calls `run_godot`, `error_findings`, `exit_findings`, `copy_project` and `import_step`, and `run.sh` has no grep left. Each check I deleted turned a test red, except the S2E-S1 property itself (S2D-S2).
3. **The isolation rule is weaker than CLAUDE.md claims (S2D-S1).** No current `env=` call leaks the real HOME into Godot:
   - `test_determinism` runs Python;
   - `test_tooling_config` runs ruff with `dict(os.environ)`;
   - `test_prepush` uses `isolated_env()`, but the gate dies on its missing PYTHON before reaching Godot;
   - `_detected` sets PATH only and runs `--platform`.

   The only Godot call is `godot_check.run_godot`.
4. **Round-one SHOULD-FIXes (16).** Folded from the tree: S2A-S1 to S2A-S6, S2C-S1 (key plus `libllvm20` pinned), S2C-S2 (173–294 µs spread), S2E-S1, S2W-S1 (§4.1 bullet and step 7 checklist), S2W-S2 (B3, B14, B2, B5, B12 retargeted). Deferred with a named row and trigger:
   - S2C-S3: framing fixed; the per-object ΔE is in B7 and the step 8 checklist;
   - S2E-S2: headless fixture landed; the `--out` refusal is deferred to step 8;
   - S2E-S3: step 8 checklist and B7;
   - S2W-S4: B27.

   **Only partly folded:** S2W-S3 (S2D-S1) and S2E-S1's test half (S2D-S2).
5. **New problems:** see the NITs. I found nothing broken.

## SHOULD-FIX

### S2D-S1: the isolation rule checks that `env=` is written, not that HOME is moved, and misses most spawn forms

`tests/test_isolation.py::_subprocess_without_env`. The rule fires only on `subprocess.<run|call|check_call|check_output|Popen>` with no `env` keyword. Measured:

- **Missed, in both `tests/` and `scripts/`:**
  - `from subprocess import run; run([...])`
  - `import subprocess as sp; sp.run(...)`
  - `os.system`, `os.execv`
  - `asyncio.create_subprocess_exec`
  - `subprocess.getoutput`
- **Accepted:** `env=None` and `env=os.environ`. Both hand Godot the real HOME.

S2W-S3 asked for "pass `env=` *or not reach Godot*". CLAUDE.md's Working rule now says "Godot only through `godot_check.run_godot`" and cites this test as its guard, but nothing checks that half.

**Scenario.** A step-8 tile-golden test copies the existing `_ruff` pattern: `subprocess.run([godot, "--path", p], env=dict(os.environ))`. The scan passes it. Two sessions' gates then share `~/Library/Application Support/Godot/` (shader cache, `godot.log` rotation) and race on it. This is exactly round one's scenario, with one keyword added.

**Fix:**
- Allow subprocess calls in `tests/` and `scripts/` only in an allowlist of modules (`godot_check.py`, `_gitutil.py`, `lint_standards.py`, and the four current test helpers), each with a one-line reason. Any new site then needs review.
- Alternatively, flag `env=` values that are `None`, `os.environ` or `dict(os.environ)` without a marker.
- Resolve `from subprocess import …` and module aliases through `_Module`, and add `os.system/exec*/spawn*/popen` and `asyncio.create_subprocess_*`.
- Seed each form as a fixture string.

### S2D-S2: no test proves the golden scene is drawn in the imported copy (S2E-S1's actual property)

`scripts/golden_run.py::draw` / `tests/test_golden_run.py::FAKE_GODOT`. The fake Godot exits 0 on `--import` and draws for any `--path`. Changing `draw` to `"--path", str(CLIENT)` (the read-only, unimported checkout) left all 11 tests green. `test_a_failed_import_draws_nothing` proves only that a failed import stops the draw.

**Scenario.** A refactor passes `CLIENT` (or a second, unimported `copy_project`) to `draw`. The unit tests stay green. On the image, the first step-8 golden that uses a `class_name` fails with `Identifier "EnginePin" not declared`: the very failure S2E-S1 described, and one that looks like a renderer fault.

**Fix.** Make the fake's `--import` write `<path>/.godot/imported.mark`. Make the fake's draw print `Parse Error: Identifier not declared` when its `--path` has no such mark, the way the real Godot fails. Then deleting or misdirecting the import step turns a test red.

## NIT

- **S2D-N1** `client/tests/run.gd::_run_suite`. A `test_*.gd` with no `test_*` method (a typo such as `tset_`, or every method renamed) adds zero tests and no failure. Fail a suite that loads but yields no test methods.
- **S2D-N2** `client/tests/golden.gd::CRATE`. It hard-codes the Crate node's position from `golden.tscn`. Moving the crate in the scene silently aims the camera elsewhere. Read `$Crate.position` instead.
- **S2D-N3** `ci/install_godot.sh` (`"$dest/$bin" --headless --version`). CLAUDE.md suggests running the installer locally, and this runs Godot with the real HOME. The isolation scan covers Python only. Run it with `HOME="$dest/home"`, plus the XDG variables.
- **S2D-N4** The commit cites "D1 to D12 in the fold report", but no fold report or fold-status table is in the tree. Under O25 the reviewer sets statuses, so the statuses in (4) above are mine, read from the tree. Commit the D-list, or a status table, beside the reviews.
- **S2D-N5** `tools/godot_probes/` is now outside every gate. No step loads it, so warnings-as-errors and parse rot show up only at the next upgrade. B26 accepts this. A one-line `--headless --import` of that project in `godot_check` would keep it parseable cheaply.
