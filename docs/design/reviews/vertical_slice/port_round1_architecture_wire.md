# Architecture and Wire integrity: phase1/slice-tuning @ 793e112

Read-only; every claim is read from the tree at 793e112. What I ran: `spikes/slice/tests` alone (160 passed, 19.1 s), `pytest --collect-only` over both testpaths (3811 collected, no basename clash), the tooling test's glob by hand, the isolation and determinism scanners run over `spikes/slice/**`, and a cadence probe (`scratchpad/review/cadence.py`). I did not run the full suite or prepush.

No BLOCKERs.

## The questions asked

**Holding the World beside the Simulation.** No text in sim_core.md forbids it. §2/§4 define `Simulation(world, *, config)` as adopting a built world, so the caller necessarily holds the reference. Only the membrane is barred from holding the simulation (§13). `World.sources` is a `MappingProxyType` and stays read-only at rest. `World.writing()` is still public, though, and nothing ties its caller to `Simulation`: `grid.writing(writer=None)`, and `adopt()` refuses only a second simulation. The ownership scans walk `SRC.rglob` only. So the slice *could* open a window outside `step`, and only review stops it. This is strictly narrower than before the port, when the slice built its own `Applier`, and the slice never calls `writing()` (grep). Verdict: not a leak today. NIT-1 below.

**physics_every=1.** I measured it. I monkeypatched `slice_server.sim.SimConfig` to `physics_every=5` and ran the commit's own script (kindle the crate, stand 0.6 m away, 400 s, no vendor charges). The pallet ignites at 134.2 s, the body trips at 226.2 s and the crate burns out at 273.2 s, **identical to physics_every=1**. With the vendor's default charges, both cadences douse at 0.5 s and go idle at 0.6 s. Digests differ, as expected. CPU per tick is 0.38 ms at 5 against 0.85 ms at 1. So on the shipped path the outcome class doesn't change, and the code comment's justification ("the slice's fire and heat were tuned on a 0.1 s step") is not supported by any measured difference. See SHOULD-FIX-1.

**The README restating a contract.** Partly. See NIT-2 and SHOULD-FIX-4.

**The log version.** It is versioned and refused loudly, but the version isn't bound to what it claims to track, and there's no fixture. See SHOULD-FIX-2 and SHOULD-FIX-3.

**testpaths interactions.**
- Coverage measures only `src`/`scripts`, so slice code isn't measured and diff-cover ignores it, which the plan's §2 relaxes anyway.
- Collection is clean: `tests/` is a package and the slice's `test_wire.py` is rootless.
- The isolation and determinism scans don't cover the new path. See SHOULD-FIX-5.
- Godot and golden jobs: untouched, since neither invokes pytest over testpaths.

**The tooling glob.** 0.08 s. Here it finds `client/tests`, `spikes/slice/tests` and `tests`. `.worktrees`, which holds other sessions' trees and venvs, is skipped, so the main checkout is safe. CI's fresh clone puts its venv at `.venv` (`test.yml:33`), which is skipped, and so is the remote gate's. See NIT-3 for the edges.

## SHOULD-FIX

**SHOULD-FIX-1: `spikes/slice/slice_server/sim.py::Sim.__init__`, physics_every=1 is an unmeasured departure from the truth constants.** sim_core.md §3 makes `tick_us`/`physics_every` T3's truth constants (tile_and_client.md §6.1: every 5 ticks). The slice overrides physics_every on a stated reason that the measurement above contradicts.
- Failure scenario: the slice's verdict (VS5, foundations step 10) feeds Phase 2's crate and the 6.x rungs. Its playtest numbers would then be on record as "tuned on a cadence the engine doesn't ship", which invites someone to change T3, or to argue for it, on no evidence. Meanwhile it doubles tick CPU and the budget numbers the verdict reports (plan §7 Q4).
- `tests/test_sim.py::test_physics_runs_on_every_tick_not_the_engines_default_fifth` guards a mechanism (the crate's hottest cell rising by tick 2) that no outcome depends on.
- Either run at `T3` and delete that test, or, if the owner wants the 10 Hz visual cadence for feel, say that this is the reason (not the tuning) and record the outcome-class equivalence measured at both cadences. Verified: the cadence probe above. The fix itself is unverified.

**SHOULD-FIX-2: `spikes/slice/slice_server/__init__.py::LOG_VERSION`, "the version moves with the engine" has no mechanism.** The comment says a log replays only on the engine it was recorded on, so the version tracks the engine. Nothing ties `slice-log-1` to the engine, though. The meta records neither `SimConfig`, nor the law tuple, nor an engine revision, although sim_core.md §14 puts both `SimConfig` and the law tuple in the real header.
- Failure scenario: the next main merge that changes heat's summation order (this port already moved temperatures by 6e-12) makes every recorded `slice-log-1` playtest log report "does NOT match", with the version check passing. That is exactly the misleading failure this version was added to prevent.
- Changing `physics_every` would do the same.
- Fix: record `SimConfig` (and the law names and versions, or the engine commit) in the meta and refuse a mismatch by name. Unverified.

**SHOULD-FIX-3: `spikes/slice/tests/test_metrics.py`, no committed log fixture.** The formats standard says "Old fixtures stay committed, and a format change that breaks one needs a migration or a version bump." The only replay round trip (`test_a_real_session_log_replays_and_a_tampered_one_is_flagged`) records a fresh log every run, so it can never see the format, or the engine under it, change. The commit message says "Main's gate runs the slice's tests, so a change to the engine can't break it quietly", but a bit-moving engine change keeps this suite green while it breaks every recorded log.
- Fix: commit a short `slice-log-1` fixture with its end digest. If the owner doesn't want the slice to gate engine PRs on bits, the README claim should narrow instead. Unverified.

**SHOULD-FIX-4: `spikes/slice/README.md` ("The port moved no number the slice was tuned on"), the claim is scoped wider than the measurement.** The measured script has no strikes. The port changed strike semantics: a strike now applies at the tick's end, after the fire, the vendor and the body's `blocked` have read the pre-strike frame, where before it applied on arrival. That is the change the old README warned about.
- Failure scenario: week-3 Overdrive-strike playtest numbers are compared across the port as if equal.
- Fix: state the script measured, or measure a strike run on both. Separately, vertical_slice.md §3.1 still says `world.advance(0.1)` and §5 still says "no applier call". The plan owns the lane's loop, so the owner text is now stale beside the README. Unverified.

**SHOULD-FIX-5: `tests/test_isolation.py::SCANNED`, `tests/test_determinism.py` (line 307), the new testpath runs in the gate but escapes both scans.** `SCANNED = ("src", "scripts", "tests")`, and the determinism file list ends at `(ROOT / "tests").rglob`. I ran both scanners over `spikes/slice/**`:
- Isolation finds nothing today.
- Determinism flags `spikes/slice/tests/test_voice.py:19-20` (`time.monotonic` deadlines), plus the server's wall clock, which is legitimately host-side.

Failure scenario: a later slice test spawns a process, binds a fixed port or writes outside `tmp_path`, and collides with another session's gate, with every guard green. Also, `test_server.py::test_the_server_runs_past_its_stats_report` takes 5.4 s of real-time pacing and isn't marked `slow` ("over a few seconds … mark it slow").
- Fix: derive the scanned roots from testpaths, or exempt the slice explicitly with a reason. Unverified.

**SHOULD-FIX-6: `spikes/slice/slice_server/__main__.py::main`, `except ValueError` is wider than "a log this slice can't read".**
- `Simulation.step` raises `ValueError` for a bad batch (an out-of-order key, a wrong tick), and so does `Sim.__init__` for a bad tick.
- A slice bug hit during replay, such as `_pending` falling out of key order if boundaries.md §6.2 ever gives `strike` and `ignite` different ranks, is then reported as a log problem with exit 2 and no traceback.
- A non-dict first line raises `AttributeError` and a missing `dx_m` raises `KeyError`. Both escape as tracebacks, so the refusal also isn't total.

Fix: a dedicated `LogRefused(ValueError)` raised by `read_log` for every malformed-log path and caught by name. Unverified.

## NIT

**NIT-1: `sim.py::Sim.world`, a public attribute that holds the write window.** It is kept only to read `sources` (the digest and the tests). Making it `_world`, or holding `world.sources` behind a read-only accessor, keeps `writing()` out of easy reach. The slice's `limits` read could use `Simulation.limits`. Unverified.

**NIT-2: README and `sim.py` comments restate contracts owned elsewhere (B36 prose).**
- The README restates "the engine's default is every fifth" (T3, tile_and_client.md §6.1).
- The `PLAYER, FIRE` comment restates the key order (boundaries.md §6.2).

Link them instead. The `_pending` order relies on `KIND_RANK` being 30 for all three kinds today (`intents.py:156`). Sorting `records` by `LogRecord.key` before `step` would make that robust. Unverified.

**NIT-3: `tests/test_tooling_config.py::test_the_gate_runs_every_tests_directory_in_the_tree`, the glob walks the filesystem, not the tracked tree.**
- An untracked venv not named `.venv` (say `.venv-3.14`, or `venv/`) holds `site-packages/*/tests/test_*.py` and turns this red spuriously.
- A tests directory named otherwise (`test/`), or `test_*.py` outside any `tests/`, escapes.
- The `client/tests` subtraction is dead today: it holds no `test_*.py`, which I checked.
- Fix: walk `git ls-files` through `tests/_gitutil.py`. Unverified.

**NIT-4: coverage coupling.** The slice tests now count toward the `fail_under = 100` floor on `src/`. If any `src/` branch is reached only through the slice, deleting the slice (plan: "every piece is either deleted or rebuilt") drops coverage below the floor. Not measured, since it needs two full-coverage runs. Measure it once, or keep the slice out of the coverage run.

Clean: `Voice.ready()` and the clock injection, `_destroyed_m3` reading `Outcome.effects` (sim_core.md §4), and construction, which takes `Simulation.from_scene`'s path.
