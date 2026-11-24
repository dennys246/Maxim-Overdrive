# Executor lens: phase1/slice-tuning @ 793e112

**Tree state first.** `git status` was clean when I started. Partway through, the worktree became dirty: changes to sim.py (it now has `records.sort(key=lambda r: r.key)`), test_determinism.py, test_isolation.py and several slice tests, plus new untracked `tests/_testroots.py` and `spikes/slice/tests/fixtures/`. I made none of these. Every mutation ran in a scratch copy, and `diff -r` against `git archive 793e112` shows that copy is identical to HEAD. Someone (presumably the author, folding) is editing the worktree. All findings below are against 793e112. The early scenario runs used live files from before the edits; I reran them on the HEAD copy and got the same results.

## What ran
- `.venv/bin/python -m pytest -q -p no:cacheprovider spikes/slice/tests`: 160 passed (20 s). `tests/test_tooling_config.py`: 37 passed. Whole-suite `--collect-only`: 3811 collected, no basename clash (tests/ is a package; slice tests import bare). Mixed run of tests/test_wire.py, the slice test_wire.py, test_tooling_config.py and the slice test_sim.py: green.
- test_voice.py with test_server.py, six reruns: all green, about 16 s each.
- Mutation runs on the scratch copy (`mut.sh`, each file restored after):
  - physics_every 1 to 5: `test_physics_runs_on_every_tick…` and test_sim_fire's convective-share test fail. 1 to 2: only the test_sim_fire test fails, so the new test alone doesn't pin "every tick". NIT.
  - Old partition `ready()` restored: `test_ready_hands_lines_over_in_the_order_they_were_asked` fails, and so does the latency test.
  - destroyed_m3 not filled in: `test_a_strikes_destroyed_volume_is_what_the_world_lost` fails.
  - LOG_VERSION check disabled: both refuse-by-name cases fail. `serve` writing meta without `log`: the two serve/replay tests fail. `return 2` changed to re-raise: the refuse tests fail.
  - tick_s guard removed: `test_the_slice_runs_only_the_engines_tick` fails.
  - `time.monotonic` back in `_speak`, at either the latency site or the queued site: the latency test fails.
  - Refusal check in `_run_engine_tick` disabled: **all 160 pass**. See the NIT below.
- Scenarios (scen.py, scen2.py) at HEAD:
  - A tick with 2 strikes and a douse gives keys (t,30,0,1,1), (t,30,0,1,2), (t,30,0,2,5), accepted.
  - A relight tick (Kindle plus Strike) gives strike(1,3), then ignite(2,6), accepted. The crate burns again.
  - 80 ticks of 3 Overdrive strikes each (calm config): per-event destroyed_m3 equals the per-outcome effects on every tick (0 mismatches). The total, 0.16 m³, equals solid cells lost × dx³. Failed-reach strikes have no record and are skipped by the `ok` filter, so the positional mapping holds.
- Removed-API grep over slice_server, its tests and the README (`.advance`, `from_scene`, `Applier`, `world.frames`, `_applier`): no live caller. `world.sources` and `world.limits` still exist and are read correctly.

## Findings

**SHOULD-FIX 1: `spikes/slice/slice_server/sim.py::Sim._run_engine_tick`: record order is correct today only because every `KIND_RANK` is 30.** The key is `(tick, kind_rank, apply_us, actor, seq)`. The slice submits in program order: PLAYER strikes, then the FIRE actor's douses, then its ignites and burnt-out extinguishes. That order is strictly increasing only because the three ranks are equal, a constant the engine owns (`simcore/core/intents.py::KIND_RANK`). Failure scenario: an engine PR gives strike rank 40. I patched `KIND_RANK = {"ignite":30,"strike":40,"douse":30}` into the process and the strike-plus-douse scenario at HEAD raised `ValueError: records must be in strictly increasing key order`, a crash in play. Worse, under the same patch **all 160 slice tests still pass**: no slice test has a strike and a fire record in one tick, or a douse plus an ignite of another fuel. So the new "main's gate runs the slice" guarantee doesn't cover the one cross-module invariant this port adds.
- Fix: sort by `r.key` before `step`. The author seems to be adding this in the working tree. It keeps the destroyed_m3 mapping valid, because strikes stay in seq order. Also needed: a test with a strike and a fire record in one tick, which goes red when the sort is removed under a patched rank. Proposed fix unverified at HEAD; I saw the sort only in the uncommitted tree.

**SHOULD-FIX 2: `pyproject.toml::testpaths`, with `tests/test_isolation.py::SCANNED`, `tests/test_determinism.py`, the ruff/mypy steps in `scripts/prepush.sh`: slice tests enter the gate without the gate's test rules.** The isolation scan covers only `("src", "scripts", "tests")`. The determinism scan, `ruff check src tests scripts` and mypy don't cover `spikes/` either. The slice tests now in the gate use the wall clock: test_server paces real ticks, `test_the_server_runs_past_its_stats_report` takes 5.4 s and isn't marked `slow`, and `_wait` polls `time.monotonic`. Nothing holds them to tmp_path, port 0 or no-spawn either. Concrete evidence: `ruff check spikes/slice` reports 15 SLF001 errors, one added by this branch (`test_voice.py:172`, `voice._pending`). The gate can't see any of them. These are flakiness and isolation exposures, not a failure I reproduced (6/6 green unloaded). The working tree's edits to test_isolation.py and test_determinism.py may address this; I didn't review them.

**NIT 1: `sim.py::Sim._run_engine_tick`: the refusal `RuntimeError` is untested.** Disabling it leaves all tests green. It is unreachable in today's alley: strike points are clamped to the footprint, and nothing paints a region away. It also now fires only after the engine has committed the tick, so a refusal leaves the tick applied before it raises. That is the same crash class as before, but the message no longer coincides with an unapplied action.

**NIT 2: `tests/test_tooling_config.py::test_the_gate_runs_every_tests_directory_in_the_tree`.** It only finds `test_*.py` directly inside a directory literally named `tests`, so a `foo/tests/unit/test_x.py` or a `*_test.py` layout escapes it. It walks the filesystem, not `git ls-files`, so an untracked scratch `tests/` dir in the worktree turns it red. `found - {"client/tests"}` subtracts nothing: client/tests holds no `test_*.py`. Cost is fine: 2.8 s for the glob even in the main checkout, which has 8 worktrees.

**NIT 3: `test_sim.py::test_physics_runs_on_every_tick_not_the_engines_default_fifth`.** It passes at `physics_every=2`. Its name claims every tick, and only test_sim_fire catches 2.

**Not verified:** the README's claim that the port matches `bfb12f8` bit for bit on cracks and to 6e-12 on temperatures. It needs a bfb12f8 worktree, which I didn't create.

**Nothing else wrong found:** `_check_batch` uniqueness of `(actor_id, seq)` holds (per-actor counters, never reset); `apply_tick` equals the engine tick; `apply_us` = 0 < tick_us; the Voice clock is injected everywhere it times; `ready()` ordering is correct.

I didn't touch the worktree's files. Its dirty state is another session's edits (above).
