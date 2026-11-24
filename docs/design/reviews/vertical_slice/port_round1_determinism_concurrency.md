# Determinism and replay, Concurrency and lanes: phase1/slice-tuning at 793e112

Lenses: Determinism and replay; Concurrency and lanes. Diff: `git diff origin/main...HEAD`. Read-only. I ran the
probes from `<scratchpad>/review/` (`replay_probe.py`, `serve_probe.py`, `voice_probe.py`, `scan_spikes.py`) with
the worktree's `.venv/bin/python`.

**Summary: no BLOCKER.** Replay is bit-identical in process, across processes and across hash seeds. The digest still
covers everything later ticks depend on, but only because physics runs every tick (NIT 3). The `ready()` fix is
correct and its test goes red under the old code. The two SHOULD-FIXes are about the slice's tests joining main's
run without joining main's scans.

## What ran, and what came out

1. **Replay is bit-identical.**
   - `replay_probe.py` scripts 150 ticks: a kindle, 12 strikes, an Overdrive run, then a stop. The probe checked that
     those ticks really produce the `kindle`, `strike`, `npc` and `doused` events. Under `PYTHONHASHSEED` 0, 1 and
     12345, every process gave the same final digest `a30c37db…072c` for the run in the `Sim`, and the same
     `replay()` digest `a28c5b77…50b0`. Each was also equal when rerun inside its process.
   - `serve_probe.py` ran `serve(0.2, 0, llm=False, root=<scratch>, ticks=20)`, then `check_replay` on the log in
     three new processes (seeds 0, 7 and 99). All three printed MATCH (`eb41774b…213f`). The log's meta carries
     `"log": "slice-log-1"`.
   - A limit: the served session had no client, so it logged no intents. The probe in the `Sim` is the one that
     exercised intents.
2. **What the digest covers after the port.** I read `Simulation`, `SourceExposure`, `Physics`, `HeatState`,
   `MaterialGrid` and `Fire`.
   - `Simulation._clock` is always `Sim.tick + 1`, and the digest hashes `Sim.tick` and `f.time_s`.
   - The law states (`HeatState`) and the bounds cache are caches, rebuilt by `warm` from the grid and the sources.
   - `original_material` and the regions change only by painting, and the slice doesn't paint.
   - `_seq` only sets the order of records within one actor, which is already the order they were submitted in.
   - The point of a source (`Applier._centroid_m`) comes from cells the digest already hashes.
   - `Fire._requests` and `Sim._pending` are empty between ticks.
   - `SourceExposure` holds `since` and the closed segments, which the digest doesn't hash. With `physics_every=1`
     each step has a single tick, so every share is one tick and no closed segment outlives its tick. The digest is
     therefore complete today; see NIT 3.
   - Key order: every record has `kind_rank` 30 and `apply_us` 0. `_take` submits the player's strikes before any
     record from the fire, so the strictly increasing check in `_check_batch` always holds.
3. **Voice.**
   - The 3 ordering, never-drop and latency tests passed in 60 separate pytest runs out of 60.
   - **Proving the guard:** with the old partitioning `ready()` patched in, the new ordering test goes red ("a later
     line waits for every earlier one").
   - **Stress test:** on a real `ThreadPoolExecutor`, 200 trials of 30 requests each, with `ready()` polled at
     random times. Every line came out in order, none lost and none duplicated.
   - **The injected clock is read from the worker thread.** `time.monotonic` is thread-safe. In the latency test the
     main thread writes `now[0] = 5.0` before `release.set()`, so the `Event` orders that write before the worker's
     reads that the test asserts on. The first request's `queued_s` can read 0 or 5, but the test doesn't assert it.
     The test is free of races.
4. **Isolation.**
   - `tests/test_isolation.py` and `tests/test_determinism.py` passed (176 tests, 7.6 s).
   - The slice suite passed: 160 tests in 18.5 s.
   - Running both scans over `spikes/slice` by hand: the isolation scan is clean. The determinism scan's findings
     are under SHOULD-FIX 1.

## SHOULD-FIX

**1. `tests/test_determinism.py::scanned_files`, `tests/test_isolation.py::SCANNED`: the slice's tests now run in main's suite, but neither scan reads them.**
- `test_the_gate_runs_every_tests_directory_in_the_tree` makes every tests directory run. The scans that enforce the
  rules for tests still cover only `src`, `scripts` and `tests`: `scanned_files()` globs `ROOT / "tests"`, and
  `SCANNED = ("src", "scripts", "tests")`.
- **Failure scenario:** a slice test that uses `time.sleep`, binds a fixed port, writes to `/tmp` or spawns a process
  passes main's gate unseen. The CLAUDE.md rules on isolation and determinism are then unguarded for the tests this
  branch just brought in.
- **This already happens:** `scan_spikes.py` reports `spikes/slice/tests/test_voice.py:19-20` (`_wait`, a deadline
  on `time.monotonic`). The same scan fails that pattern under `tests/`.
- The scan also reports the host-side `server.py`, `__main__.py` (`secrets`, `strftime`) and `voice.py`. Those
  aren't simulation code. They would need an exemption like `NOT_SIMULATION`.
- The simulation modules of the slice (`sim.py`, `fire.py`, `body.py` and the rest) are clean.
- **Proposed fix (unverified):**
  - Add `spikes/slice/tests` to both scans.
  - Add the slice's simulation modules to the determinism scan, with `server.py`, `__main__.py` and `voice.py`
    exempt as host code.
  - Bound `_wait` with `concurrent.futures.wait(voice._pending, timeout=10)` instead of the wall clock.
  - Better still, the existing test could derive these lists from `testpaths`, so the next spike can't slip past.

**2. `spikes/slice/tests/test_server.py`: the tests are paced by the wall clock, and one is long, now inside main's gate.**
- `Server.run` paces ticks with `time.monotonic`, so the server tests run in real time:
  - `test_the_server_runs_past_its_stats_report`: 5.42 s, and not marked `slow`.
  - `test_a_change_of_the_vendors_state_sends_a_line_and_logs_it`: 2.96 s.
  - `test_a_silent_connection_is_dropped_after_the_hello_deadline`: 0.92 s, timed by a real deadline.
- **Failure scenario:** on a loaded machine (the box_quiet two-suite cap exists because of load), a test that waits
  on the hello deadline or on tick pacing can flake. Every gate run also pays more than 10 s of wall time.
- This goes against "Tests are deterministic and fast … mark anything over a few seconds `slow`".
- The tests existed before this branch, but this branch puts them in the gate.
- **Proposed fix (unverified):** give `Server` an injectable clock, as `Voice` now has, or mark the long test `slow`.

## NIT

**3. `spikes/slice/slice_server/sim.py::Sim.digest`: whether the digest is complete depends on `physics_every=1`, and nothing says so.**
- **Failure scenario:** if `Sim.__init__` ever uses the engine's default `physics_every=5`, the exposure's closed
  segments and `since` ticks become state that lasts across ticks. Example: a douse followed by a re-ignite inside
  one physics step. That state shapes the next step's deposit, and the digest doesn't hash it. Two runs that
  diverged would then share a digest until the next physics tick.
- Two things hold the cadence at 1 today: the hard-coded `SimConfig` and
  `test_physics_runs_on_every_tick_not_the_engines_default_fifth`.
- **Proposed fix (unverified):** state the dependence in the digest's docstring, or hash `self._engine`'s exposure.
  Hashing the exposure would need an accessor on `Simulation`. PR 4b's per-tick engine digest makes this moot, so
  this could be deferred, with that PR as the trigger.

**4. `spikes/slice/slice_server/voice.py::Voice.ready` and `close`: futures that raise inside the finished prefix.**
- `ready()` takes the prefix off `_pending` before it calls `result()`. So if any `result()` raises, the lines after
  it in that prefix are lost. Two ways that can happen:
  - an exception from `ask` other than `VoiceFailed`, or a `KeyError` in `_fallback`;
  - calling `ready()` after `close()`, once the running head finishes. The queued futures were cancelled, so their
    `result()` raises `CancelledError`. `voice_probe.py` showed that after `close()` the head is still running and
    the 2 queued futures are cancelled.
- The shipped path never calls `ready()` after `close()`, and `ollama` turns its failures into `VoiceFailed`, so this
  is latent.
- Separately, `Server.close` doesn't drain `ready()` before `voice.close()`. Lines that finished but weren't
  delivered are left out of the session log, which slightly undercounts the voice metrics.
- This isn't new in the diff. The prefix rule doesn't make it worse.

## Checked and fine

- `ready()` can no longer reorder lines, and still never loses or duplicates one: shown by the mutation, the stress
  test and the flip-future test.
- The prefix rule adds no head-of-line blocking that the single worker didn't already have.
- Matching `destroyed_m3` to events: strike records and `ok` strike events are both in `_take` order, and both `zip`
  calls are strict.
- A refused log returns 2 from both `replay` and `metrics`, and the tests cover both.
- The slice tests write only under `tmp_path`. `serve` always gets `root=tmp_path`, and the servers bind port 0.
