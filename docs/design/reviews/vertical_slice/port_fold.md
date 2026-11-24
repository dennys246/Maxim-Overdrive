# The slice's port onto Simulation: round 1 fold

Round 1 ran three readers on `793e112` (`port_round1_executor.md`, `port_round1_architecture_wire.md`,
`port_round1_determinism_concurrency.md`). No BLOCKER. The fold is the commit after `793e112`. The "what the author
did" column is the author's account; the status column is the delta reviewer's, read from the tree.

| Finding | What the author did | Status (reviewer) |
| --- | --- | --- |
| Exec S1: record order holds only while every rank is 30 | `_run_engine_tick` sorts by `LogRecord.key`; `test_a_ticks_records_reach_the_engine_in_the_logs_key_order` patches strike to rank 40 and runs a kindle and a strike in one tick (red without the sort) | |
| Exec S2, Arch S5, Det S1: slice tests in the gate without its scans | `tests/_testroots.py` reads testpaths; the isolation scan covers each spike root, the determinism scan its non-host modules (`SPIKE_HOST` exempts server, `__main__`, voice) with `MUST_SCAN_SPIKES`; `test_voice._wait` waits on the futures, not the wall clock; ruff and its format check cover `spikes/slice`, with the tests' per-file ignores | |
| Det S2, Arch S5: server tests paced to the wall clock, one 5.4 s | `Server(wall_tick_s=...)` paces ticks; the stats test runs at 1 ms; `test_the_wall_pacing_never_changes_the_world` | |
| Arch S1: `physics_every=1` justified by a claim the measurement contradicts | Kept, with the reason the digest needs it (Det N3): at one tick per step no exposure state outlives a tick. `ENGINE` in `sim.py` says so; the README points there | |
| Arch S2: the log version isn't tied to the engine | The meta carries the engine's `tick_us` and `physics_every`, refused when they differ; the version's comment no longer claims it moves with the engine's arithmetic | |
| Arch S3: no committed log fixture | `tests/fixtures/session_slice-log-1.jsonl` and `test_the_committed_session_log_still_replays` (red on one intent moved one tick, and on a 1e-6 change to heat's source term; green on a 1e-12 change to every temperature step, which moves no stored bit in this session) | |
| Arch S4: README claim wider than the measurement; plan §3.1 and §5 stale | README names both runs and their scope (the strike run included); the plan's two lines updated | |
| Arch S6: `except ValueError` too broad | `LogRefused(ValueError)`, raised by `read_log`, caught by name | |
| Arch N1: `Sim.world` public | `_world`, with a read-only `sources` property | |
| Arch N2: comments restating the key and T3 | The `PLAYER, FIRE` comment no longer restates the key; README defers to `ENGINE` | |
| Arch N3, Exec N2: tooling test walks the filesystem | `git ls-files` through `tests/_gitutil.py`; fails naming any tracked tests directory no testpath runs | |
| Arch N4: slice tests count toward src coverage | Not measured; open | |
| Exec N1: the refusal `RuntimeError` untested | `test_a_refused_record_is_a_bug_and_says_so` | |
| Exec N3: the cadence test passes at `physics_every=2` | It now asserts the burning crate warms on each of five consecutive ticks (red at 2 and at 5) | |
| Det N4: `ready()` after `close()`, and lines undrained at close | Not changed: latent, never on the shipped path; open | |

Found outside the review while folding: `spikes/specgen/test_spike.py` (another session's spike, run by hand by its
own docstring) has one failing test on today's main, `test_m5_burns_an_accepted_spec_at_turns_of_6_s`. Reported to the
owner, not changed here.
