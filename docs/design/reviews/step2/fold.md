# Step 2 fold: author's record

**This is the author's record, not a fold-status table.** Under O25 a reviewer sets each finding's status from the
tree; nothing here is a status. It lists, per finding, what the author changed and the deletion proof that shows the
change is guarded. Reviews: `executor.md`, `architecture.md`, `wire_trust.md`, `client_rendering.md` (round one, at
aa5fcfa) and `delta.md` (at 9911998).

**How each proof ran:** the named mechanism was broken in the real file, the named tests run (against Godot 4.7.2
for client and fixture tests, with HOME and XDG inside tmp_path), and the file restored byte for byte. "Red" means the
named tests failed and nothing else did, unless the line says otherwise.

## Deletion proofs

| Id | Broken | Red |
|---|---|---|
| D1 | `run.gd` no longer awaits each test or suite (the result kept, so it still parses) | `test_a_test_that_fails_after_an_await_fails_the_run` only; the clean client still passes |
| D2 | `TestContext.finish` no longer fails a test with no check | `test_a_test_that_makes_no_check_fails_the_run` |
| D3 | `run.gd` no longer recurses into `unit/` subdirectories | `test_a_suite_in_a_subdirectory_runs` |
| D4 | `golden.gd`'s headless refusal removed | `test_the_golden_scene_refuses_a_headless_run_instead_of_hanging` (as a timeout) |
| D5 | the isolation scan's round-one `env=` rule removed | its three catch cases (superseded by D15–D19) |
| D6 | `golden_run.draw` without `error_findings` | the error-line case and the hang test |
| D7 | `golden_run.draw` without `exit_findings` | the exit-2 case |
| D8 | `golden_run.golden_job` without `import_step` | `test_a_failed_import_draws_nothing` |
| D9 | `golden_key` without the LLVM version and Ubuntu revision | 5 `test_golden_compare.py` tests, the key test among them |
| D10 | `golden_run.main` without resolving `--out` | `test_a_relative_out_directory_reaches_godot_as_an_absolute_path` |
| D11 | `install_godot.sh` maps any Linux machine to `linux-x86_64` | the aarch64 refusal case |
| D12 | `godot_check.sentinel_findings` ignores the exit code after PASS | `test_a_runner_that_exits_non_zero_after_pass_fails` and 2 unit cases |
| D13 | `golden_run.draw` draws in the unimported `CLIENT` instead of the imported copy | 5 `test_golden_run.py` tests (the stand-in Godot fails a draw in a project it never imported) |
| D14 | `run.gd` no longer fails a suite with no `test_` methods | `test_a_suite_with_no_test_methods_fails` only |
| D15 | the spawn allowlist removed (no spawn outside it is flagged) | all 19 spawn forms in `SPAWN_FORMS` |
| D16 | `from … import …` aliases no longer resolved | the 4 `from`-import forms |
| D17 | `os.exec*` and `os.spawn*` no longer counted as spawns | the 4 exec and spawn forms |
| D18 | Godot's site no longer required to pass `godot_env(home)` | 5 of 6 `test_godot_must_be_given_a_moved_home` cases (the sixth has no `env=` and D19's rule catches it) |
| D19 | an allowed site no longer required to write `env=` | `test_an_allowed_site_must_still_say_which_environment_it_gets` |

Two first attempts proved the wrong thing, and were redone: D1's first version made `run.gd` fail to parse (every
Godot test went red, so it proved nothing), and its second went green because the no-check rule caught the test first;
the await fixture now makes one passing check before its `await`. D14's first version used `if false:`, which the
warnings-as-errors settings refuse to parse; it now uses a condition that is never true.

## Per finding

| Id | What the author changed | Proof |
|---|---|---|
| S2C-B1 | `run.gd` awaits each test and suite; `TestContext.finish` fails a test with no check | D1, D2 |
| S2E-N1 | a fixture where the runner prints PASS then exits 3; the runner's docstring calls its own quit code belt and braces | D12 |
| S2E-S1, S2C-N4 | `scripts/golden_run.py` imports a fresh copy before drawing | D8, D13 |
| S2A-S1 | `golden_run.py` reuses `godot_check.run_godot`, `error_findings`, `exit_findings`; `run.sh` has no scan | D6, D7 |
| S2E-S2 | a slow fixture runs `golden.tscn` headless and expects the refusal; the missing-`--out` case is deferred to step 8 (B7, checklist) | D4 |
| S2E-S3 | CR-B3's open half in B7 and the step 8 checklist | none: a record |
| S2A-S2 | `install_godot.sh` detects the platform; each workflow step is one line | D11 |
| S2A-S3 | the JSON probe is a client unit test; the windowed probes are a separate project in `tools/godot_probes/`; B26 | none: the unit test is held by the gate |
| S2A-S4 | B25 and a step 7 checklist item | none: a record |
| S2A-S5 | `MAXIM_OVERDRIVE_GODOT=1` for the fixtures; the gate sets both switches | `test_client_project.py` asserts the gate sets both |
| S2A-S6 | the errata block folded into §3, §4.1, §6.1, §6.5, §7.2–§7.4, §8 and §9; 3,800 words against 3,801 at freeze | none: a document |
| S2C-S1 | the key carries the Mesa package version and the LLVM version; `libllvm20` pinned | D9 |
| S2C-S2 | §8 and `godot_probes.md` give the 173–294 µs spread over eight runs | none: a measurement |
| S2C-S3, S2C-N1 | the camera centred on the crate, the floor fills the view; the blind spot in `golden_compare`'s docstring, B7 and step 8 | none: framing; the per-object ΔE is step 8 |
| S2W-S1 | §3, §4.1 and §12; step 7 checklist items for 2^53 and the server's refusals | none: a record |
| S2W-S2 | B2, B3, B5, B12 and B14 retargeted to the current plan; B9 left stale (the plan does not schedule it) | none: a record |
| S2W-S3, S2D-S1 | process spawning in `tests/` and `scripts/` only at `ALLOWED_SPAWNS`, any spelling, each with an explicit env; Godot only with `godot_env(home)` | D15–D19 |
| S2W-S4 | B27 | none: a record |
| S2D-S2 | the stand-in Godot's import marks the copy, and its draw fails in a project it never imported | D13 |
| S2D-N1 | a `test_*.gd` with no `test_` method fails | D14 |
| S2D-N2 | `golden.gd` reads the crate's position from the scene; the golden image is byte-identical | none: the golden job passes unchanged |
| S2D-N3 | `install_godot.sh` runs `--version` with HOME and XDG inside `<dest>` | `test_client_project.py` asserts it; ran once on macOS |
| S2D-N4 | this record | none |
| S2D-N5 | B26 says `tools/godot_probes/` is outside the gate on purpose and is rerun on an upgrade | none: a record |
| NITs, round one | S2A-N2/S2E-N4 (B6 pending CI), S2A-N3/S2E-N2 (`main.gd` dropped), S2A-N4, S2A-N5 (base in the PASS line), S2A-N6, S2C-N2, S2C-N3 (D3), S2E-N3, S2E-N5, S2W-N1, S2W-N3–N6 | as listed |
| Not folded | S2A-N1 (the clean gate runs twice: the prepush step fails fast, the test proves `main`); S2W-N2 (SHA-pinned actions: a repo-wide change) | none |

The fold also fixed one bug of its own making, found by running the Mac advisory draw: `golden_run.py` passed a
relative `--out` to Godot, which reads it against the project (D10).
