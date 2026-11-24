# The slice's port onto Simulation: delta round 1

Reviewer: delta reader, read-only, on `14bfbfc` (fold `70ecf92`, note `14bfbfc`; diffs `793e112..70ecf92` and
`70ecf92..14bfbfc`). Every mutation ran in a scratch copy (`git archive HEAD`, made a throwaway git repo so
`git ls-files` works), at `<scratchpad>/delta/copy`, with the worktree's `.venv/bin/python` and `PYTHONPATH` set to the
copy's `src`, `spikes/slice` and root. Neither the full suite nor `prepush.sh` was run.

**The slice still runs on the merged main:** `spikes/slice/tests` at HEAD passes 165 of 165 (14 s).

**Summary:** 9 rows fixed, 3 open, 1 deferred. No BLOCKER. One new SHOULD-FIX makes Exec S2 open: the isolation scan
now reads `spikes/slice`, but every rule it applies only to tests is skipped there. A second new SHOULD-FIX: the
narrowed `except` turns a truncated log into a traceback.

## Fold table

| Finding | Status (reviewer) | Evidence |
| --- | --- | --- |
| Exec S1: record order holds only while every rank is 30 | fixed | I replaced `records.sort(...)` with `pass`. The new test went red, `ValueError: records must be in strictly increasing key order`, and it was the only failure of 165. `LogRecord.rank` reads `KIND_RANK` at call time (`intents.py:205`), so the monkeypatch reaches the engine. |
| Exec S2, Arch S5, Det S1: the slice's tests are in the gate without its scans | **open** | Determinism part fixed: a `time.sleep` planted in `spikes/slice/tests/test_body.py` and a `random.random()` planted in `slice_server/heat_debt.py` each turned the scan red, naming the file and line. Ruff and the format check over `spikes/slice` are clean (30 of 30 tracked files seen). Isolation part not fixed: a planted `subprocess.run(["true"])` and `socket.create_server(("127.0.0.1", 8080))` in a slice test both passed `tests/test_isolation.py` (69 passed). See new finding 1. The ruff scope is unguarded: see new finding 3. |
| Det S2, Arch S5: server tests paced to the wall clock, one 5.4 s | **open** | The 5.4 s test now runs at `wall_tick_s=0.001`. `--durations` still shows `test_a_change_of_the_vendors_state_sends_a_line_and_logs_it` at 2.95 s, paced to the wall clock, and the hello-deadline test (0.9 s) still runs on a real deadline. Both are named in Det S2's scenario, and the fold gives no reason for leaving them. The fix is one keyword on the first. |
| Arch S1: `physics_every=1` justified by a claim the measurement contradicts | fixed | `sim.py::ENGINE` now gives the digest-completeness reason (Det N3) and records the equal-outcome measurement at both cadences, which is the reviewer's second option. The README points to it. The cadence test goes red at `physics_every=2` (below). |
| Arch S2: the log version isn't tied to the engine | fixed | `log_meta` carries `tick_us` and `physics_every`. `_check_meta` refuses a mismatch by name, and the test's new parameter covers it. The comment no longer over-claims. The meta doesn't carry the law tuple or a commit; the committed fixture stands in for that (below). |
| Arch S3: no committed log fixture | fixed | Red on every perturbation I tried: `power_w * (1 + 1e-6)` in `heat.substep`; the kindle moved from tick 32 to 31; the strike removed; `overdrive_energy_j` 120000 to 119000. Each failed with "the engine moved the slice's replay". At `physics_every=2` it is refused by the cadence check. It stays green when the ordinary `energy_j` changes, because the fixture holds only an Overdrive strike. That is a scope limit, not a defect. |
| Arch S4: README claim wider than the measurement; plan §3.1 and §5 stale | fixed | The README names both runs and the strike run's scope. Plan lines 37 and 167 are updated. |
| Arch S6: `except ValueError` too broad | fixed | `LogRefused(ValueError)` is raised only by `_check_meta` and caught by name in `__main__.main`, and the tests use `pytest.raises(LogRefused)`. The narrowing opens a regression: see new finding 2. |
| Arch N1: `Sim.world` public | fixed | `grep '\.world\b' spikes/slice` finds no use. The world is `_world`, and `sources` is a property over `World.sources`, a `MappingProxyType`. `_check_fits_the_limits` reads `self._engine.limits`. |
| Arch N2: comments restating the key and T3 | fixed | The `PLAYER, FIRE` comment no longer restates the key order. The README defers to `ENGINE`. |
| Arch N3, Exec N2: tooling test walks the filesystem | fixed | It reads `git ls-files` through `tests/_gitutil.py`. A tracked `spikes/x/tests/test_a.py` turned it red, naming `['spikes/x/tests']`. An extra testpath `spikes/nope/tests` turned it red, but with "a testpath with no tests" and no name: NIT 6. |
| Arch N4: slice tests count toward src coverage | **open** | Not measured. The author set nothing beyond "open", and the full-coverage run is out of my scope. It stays open until the two coverage runs (with and without `spikes/slice/tests`) are compared, or the slice is left out of the coverage run. |
| Exec N1: the refusal `RuntimeError` untested | fixed | Turning `raise RuntimeError(` into `print(` at `sim.py:124` made `test_a_refused_record_is_a_bug_and_says_so` fail. |
| Exec N3: the cadence test passes at `physics_every=2` | fixed | With `physics_every=2` in `ENGINE`, `test_physics_runs_on_every_tick_not_the_engines_default_fifth` failed. So did the committed-log test and `test_the_cells_gain_exactly_the_convective_share...`. |
| Det N4: `ready()` after `close()`, lines undrained at close | deferred (reviewer) | Reason: latent, with no caller of `ready()` after `close()` on the shipped path (`server.py` closes the voice last). Trigger: the voice leaving the spike (step 7 or 8's rebuild), or any new caller of `ready()` after `close()`. |

`14bfbfc` only rewords the specgen paragraph of `port_fold.md`. I didn't rerun specgen.

## New findings

**SHOULD-FIX 1: `tests/test_isolation.py::spawn_findings`, `::_node_findings`, `::_process_findings`: the spike root is
scanned, but every rule that applies only to tests skips `spikes/slice/tests`.** `SCANNED` now includes `spikes/slice`.
But `spawn_findings` returns early unless `rel` starts with `tests/` or `scripts/`. The fixed-port URL rule and
`_fixed_port` need `in_tests = rel.startswith("tests/")`, and so does `_git_outside_helper`. Only the shared-path,
HOME and tempdir rules reach the spike. A planted `/tmp/fixed.txt` in `server.py` was caught.
- **Failure scenario:** a slice test that binds port 8080, spawns `ollama` or runs `git` without `_gitutil` passes
  main's gate. I ran the first two: 69 passed. That is the scenario Det S1 named, so the row stays open.
- `test_voice.py` and `test_server.py` already start servers. Today they bind port 0, so nothing is broken yet.
- The fix is to treat `f"{root}/tests/"` for each `spike_roots()` entry as a tests prefix, and to add a
  `test_the_scan_catches_...` case at a spike path. Unverified.

**SHOULD-FIX 2: `spikes/slice/slice_server/metrics.py::read_log`: a malformed or truncated log is now a traceback, not
a refusal.** `json.loads` raises `JSONDecodeError`, and `float(meta["dx_m"])` raises `ValueError`. Neither is
`LogRefused`, so `main` no longer catches them.
- **Failure scenario:** a server killed mid-flush leaves a partial last line. The log format already expects crashes
  (`crashed`). `slice_server metrics` on that log used to exit 2 with "slice_server metrics: <reason>"; now it dies
  with a traceback.
- Ran: the fixture's first 400 bytes as a log gave `json.decoder.JSONDecodeError`, uncaught. A meta with
  `"dx_m": "x"` gave an uncaught `ValueError`.
- The fix is for `read_log` to wrap parsing and raise `LogRefused` from the cause, naming the line. Unverified.

**SHOULD-FIX 3: `tests/test_tooling_config.py::test_ruff_lints_every_tracked_python_file`: the ruff scope over
`spikes/slice` has no guard.** The test still runs `--show-files src tests scripts` against `ls-files src tests scripts`.
Nothing in `tests/test_prepush.py` or `test_tooling_config.py` reads the ruff paths in `prepush.sh`.
- **Failure scenario:** someone drops `spikes/slice` from either ruff line, or adds an exclude that hides slice files,
  and the gate stays green.
- The fix is to extend the test's paths with `spike_roots()`. Holding prepush's two ruff lines to the same list needs
  a test that reads them. Unverified.

**NIT 4: `pyproject.toml` `[tool.ruff.lint.per-file-ignores]`: the comments were spliced.** `"tests/**"` lost its "tests
reach private names" reason. The `spikes/slice/tests/**` line now carries two comments, end to end.

**NIT 5: `spikes/slice/slice_server/server.py::Server.__init__`: `wall_tick_s` isn't validated, and the overrun meter
reads it.**
- At 0 or below, `run` busy-loops and counts every tick as an overrun.
- At 0.001, `meter.overruns` measures 1 ms slots, not the 100 ms budget, so the stats records in a fast test's log are
  meaningless.
- Neither is on the shipped path, since `__main__.serve` never passes it. `test_the_wall_pacing_never_changes_the_world`
  can fail: setting `sim.tick_s = wall_tick_s` turned it red.

**NIT 6: `tests/test_tooling_config.py::test_the_gate_runs_every_tests_directory_in_the_tree`: the second assertion
doesn't name the empty testpath.** The fold row claims it fails "naming" the gap, which is true only of the first
assertion.

**NIT 7: `spikes/slice/tests/test_metrics.py::_build_fixture`: the fixture bypasses `serve` and the session data.**
- It writes only meta, intents and the end record, so `read_log`'s `line`, `stats` and crash parsing never meet a
  committed file.
- The meta carries no digest of `spikes/slice/data`. On this tuning branch, a YAML tweak shows as "does NOT match" on
  every recorded playtest log, the same misleading failure Arch S2 fixed for the engine, now for the data. This
  predates the fold; I'm noting it, not reopening S2.

**NIT 8: `tests/test_determinism.py::MUST_SCAN_SPIKES`, `SPIKE_HOST`: hard-coded slice paths.** When the slice is
deleted or leaves testpaths (the plan deletes every piece), this test goes red until someone edits it. It fails
loudly, so it's acceptable, but the deletion step should know. The host exemptions are sound: `voice.py`'s `time` is
host-side, and `test_no_simulation_code_imports_the_voice` keeps it there.
