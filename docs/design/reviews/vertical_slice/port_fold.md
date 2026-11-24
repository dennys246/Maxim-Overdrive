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
own docstring) had one failing test on `7500a85`, `test_m5_burns_an_accepted_spec_at_turns_of_6_s`; #59 ported its M5,
and on the merge with `b578761` all 73 pass. It stays outside testpaths, as its own docstring says.

## Delta 1 fold

Delta 1 (`port_delta1.md`, on `14bfbfc`) set the round-1 statuses above in its own table: 11 fixed, Exec S2 / Arch S5
/ Det S1, Det S2 and Arch N4 open, Det N4 deferred. Its new findings, and the author's account of the fold after
`14bfbfc`, for delta 2 to read from the tree:

| Finding | What the author did | Status (reviewer) |
| --- | --- | --- |
| Round 1 Exec S2 / Arch S5 / Det S1 (isolation half) and Delta 1 S1: the tests-only isolation rules fire only under `tests/` and `scripts/` | `TEST_ROOTS` from testpaths and `SPAWN_ROOTS` (with the spike roots) drive the spawn, git and fixed-port rules; `test_a_spike_test_the_gate_runs_is_held_to_the_tests_rules` plants a spawn, a fixed port and a bare git call in a slice test (red with the old roots). The scan then caught `test_voice.py`'s refused `example.com:11434`, exempted with its reason | |
| Delta 1 S2: a truncated or malformed log crashes `metrics` | `read_log` refuses every line that isn't a JSON record, and wraps the parse of data, grid and intents in `LogRefused`; `test_a_damaged_log_is_refused_by_name` (truncated, bad `dx_m`, bad data, unknown intent, a non-record line) | |
| Delta 1 S3: nothing holds the gate's ruff paths | `test_the_gate_lints_and_formats_every_path_it_tests` reads both ruff lines in `prepush.sh` against `RUFF_PATHS` (red with the slice dropped from the format line); the tracked-files ruff test uses the same paths | |
| Delta 1 NIT: no digest of the data in the log, so a retune makes every earlier log mismatch | Taken as a SHOULD-FIX for week 4's tuning: the meta keeps the data files as read (`config.raw`), `serve` runs on exactly that data, and replay and metrics parse it from the log (`test_a_replay_runs_on_the_data_the_session_was_played_on`, red when metrics reads today's files) | |
| Delta 1 NIT: `wall_tick_s` unvalidated | Refused unless positive; tested | |
| Delta 1 NIT: the spliced per-file-ignore comment | Each line has its own reason | |
| Delta 1 NIT: the tooling test doesn't name an empty testpath | It names it | |
| Round 1 Det S2 (remainder): the vendor-line test (2.95 s) and the hello deadline (0.9 s) still run on the wall clock | Not changed. Both drive the real socket and the clocked hello deadline end to end; a fast run needs the client authenticated before the first tick, which the loop doesn't offer. Each is under the few-seconds bar. Author's proposal: deferred, trigger a slice test over 3 s or a flake of either | |

## Delta 2 fold

Delta 2 (`port_delta2.md`, on `04d2386`) set the delta-1 rows in its own table: 5 fixed, the isolation half and the
data-in-log row open, the wall-clock remainder deferred (reviewer: trigger either test over 3 s or flaking, or a
start-after-authentication hook). The author's account of the fold after `04d2386`:

| Finding | What the author did | Status (reviewer) |
| --- | --- | --- |
| Delta 2 S1 (and the open isolation row): `socket.create_server((host, 8080))` never flagged | `ADDRESS_CALLS` (`bind`, `create_server`, `create_connection`) reads the port from the address tuple; cases in the fixed-port test and in the spike test (red with only `bind`); the spike test's git case passes `env=` and asserts the git rule's own message (red with the git rule's root back to `tests/`) | |
| Delta 2 S2 (and the open data row): replay and serve unguarded | `serve` parses the JSON round trip of the meta it wrote (which also ends Delta 2 NIT 1); `test_the_replay_command_runs_on_the_logged_data` and `test_a_session_runs_on_the_data_it_logged` (red when serve reads `config.load`, when it reads the files twice, and when replay reads `config.load`) | |
| Delta 2 S3: layout changed without a version bump | `LOG_VERSION` is `slice-log-2`; the `slice-log-1` log from `14bfbfc` is committed again and refused by its version (`test_an_older_committed_log_is_refused_by_its_version`) | |
| Delta 2 NIT 2: the broad handler wraps the parsers | Not changed: named by type, and the committed-log test goes red on a parser bug | |
| Delta 2 NIT 3: the borrowed `shared-path-ok` marker on `test_voice.py`'s URL | Not changed | |

## Delta 3, the last round

The owner's stop rule (2026-11-23): delta 3 is the last round; only BLOCKER and SHOULD-FIX fold, NITs go to the
backlog with no code. Delta 3 (`port_delta3.md`, on `d1c7b2c`) set the delta-2 rows: the three SHOULD-FIX fixed, the
two NITs rejected as fold items. It found no BLOCKER or SHOULD-FIX. Its NITs 1 and 2 (the fixed-port rule's limits)
are in backlog row B20; NIT 3 (the spike test's loop is vacuous with no spike in testpaths) is harmless, since the
gate runs no spike that isn't in testpaths. Still open or deferred, with their triggers: Arch N4 (whether src coverage
leans on the slice's tests; measure before the slice is deleted at step 10's close), Det N4 and the wall-clock server
tests (deferred by delta 1 and 2's reviewers, triggers in their rows).
