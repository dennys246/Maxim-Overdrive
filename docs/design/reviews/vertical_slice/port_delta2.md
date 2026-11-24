# The slice's port onto Simulation: delta round 2

Reviewer: delta-2 reader, read-only, on `04d2386` (fold `14bfbfc..04d2386`). Mutations ran in a scratch copy with
the worktree's venv. Neither the full suite nor `prepush.sh` was run.

At HEAD, `spikes/slice/tests`, `tests/test_isolation.py` and `tests/test_tooling_config.py` pass 282 of 282 (30 s).

**Summary:** 5 rows fixed, 2 open, 1 deferred. No BLOCKER. Three SHOULD-FIX findings. The worst is that delta 1's
exact fixed-port plant still passes.

## Delta 1 fold table

| Finding | Status (reviewer) | Evidence |
| --- | --- | --- |
| Isolation half (R1 Exec S2 / Arch S5 / Det S1, D1 S1) | **open** | The spawn part is fixed: setting `SPAWN_ROOTS` back to tests/scripts turned the new test red. Plants of `subprocess.run` and `os.system` in `slice_server/server.py`, and a spawn plus a bare git call in a slice test, were all named. The port part is not fixed. Delta 1's plant, `socket.create_server(("127.0.0.1", 8080))`, still passes in a slice test, and also in `tests/` (new finding 1). The fold's test plants `s.bind(...)` instead, which the rule does catch. Its git case can't fail on its own: with the git rule's root put back to `"tests/"`, all 3 cases pass, because the spawn rule catches the git call first. |
| D1 S2: damaged log crashes `metrics` | fixed | Narrowing the handler to `ZeroDivisionError` turned `test_a_damaged_log_is_refused_by_name` red (`ValueError: could not convert string to float: 'x'`). The replay itself (`observe`, `replay`) runs after `read_log` returns, outside the `try`, so a `Sim` bug can't read as a refusal. |
| D1 S3: ruff paths unguarded | fixed | Each of these went red: dropping `spikes/slice` from prepush's format line, adding a second command to the check line, and adding `extend-exclude = ["spikes/slice/slice_server/npc.py"]` (the last one via `test_ruff_lints_every_tracked_python_file`). |
| D1 NIT 7: data in the log | **open** | The code is right on all three paths, but only one of them is guarded. Making `session_metrics` read today's files turned the new test red. Making `check_replay` (the `replay` command) use `config.load()` passed 172 of 172. Making `serve` run `config.load()` instead of the data it logged also passed 172 of 172. See new findings 2 and 3, and NIT 1. |
| D1 NIT 5: `wall_tick_s` | fixed | `test_a_pacing_of_zero_is_refused`. `not x > 0` refuses NaN too. |
| D1 NIT 4: spliced comment | fixed | `pyproject.toml`: each line now has its own reason. |
| D1 NIT 6: empty testpath unnamed | fixed | The assertion now lists `empty`. |
| R1 Det S2 remainder: wall-clock tests | deferred (reviewer) | Reason: I added `wall_tick_s=0.001` to the vendor-line test. It passed 6 of 6 runs at about 0.8 s. But a 30-tick run then lasts 30 ms and races the client's connect and hello, so the change swaps a 2.95 s test for a test that can fail under load. That backs the author's reason. Both tests are under the few-seconds bar. Trigger: either test over 3 s or flaking, or the loop gaining a start-after-authentication hook. |

## New findings

**SHOULD-FIX 1: `tests/test_isolation.py::SERVER_CALLS_PORT_AT` / `::_fixed_port`: `socket.create_server((host, 8080))`
is never flagged, in `tests/` or in the slice.**
- The table puts `create_server`'s port at positional index 2, which is asyncio's `start_server(cb, host, port)`
  layout. `socket.create_server` takes one address tuple at index 0.
- Ran: `findings(...)` on `socket.create_server(("127.0.0.1", 8080))` returns `[]` at `tests/test_a.py` and at
  `spikes/slice/tests/test_a.py`. `s.bind(...)`, `port=8080` and a URL with a port are each caught.
- **Failure scenario:** the slice opens its own listener with exactly this call (`server.py`). A slice test that
  copies it with a fixed port collides with another session's run, and the gate stays green. This is the scenario
  delta 1 ran.
- The gap predates the fold, but the fold row claims the scenario is closed, and its test avoids the spelling.
- Fix: add a check for the address tuple at index 0, and a `test_the_scan_catches` case for it. Unverified.

**SHOULD-FIX 2: `spikes/slice/slice_server/__main__.py::check_replay` and `::serve`: the "runs on the logged data"
claim is guarded only for `metrics`.**
- Table row 4's two mutations leave the suite green.
- **Failure scenario:** a refactor brings back `config.load()` in `check_replay`. After a retune, `slice_server
  replay` reports MISMATCH on every earlier playtest log, which is the exact failure this fold set out to remove, and
  no test notices.
- Likewise, `serve` could log one reading of the files and run another.
- Fix: the replay test does what the metrics test already does (`config.load` monkeypatched to raise). A `serve` test
  retunes the data in `tmp_path` or `config.raw` between the two reads and checks that the session still replays.
  Unverified.

**SHOULD-FIX 3: `spikes/slice/slice_server/__init__.py::LOG_VERSION`: the meta's layout changed without a version
bump, and the old fixture was overwritten.**
- The meta now requires `data`, but the version is still `slice-log-1`.
- Ran: the pre-fold committed fixture (`git show 14bfbfc:.../session_slice-log-1.jsonl`), a valid `slice-log-1`
  log, now gives `can't be replayed: ValueError: the slice's data is the files [...], got None`, exit 2.
- **Failure scenario:** any playtest log recorded on this branch since `793e112` is refused with a reason that
  points at its data, not at its version.
- `slice-log-1` never reached `origin/main`, so the impact is small. But CLAUDE.md asks for a version bump or a
  migration, and for old fixtures to stay committed.
- Fix: bump to `slice-log-2`, and either keep the `-1` fixture as a refused-by-version case or delete it with a
  reason. Unverified.

**NIT 1: `__main__.py::serve`: `serve` parses the YAML objects, while replay parses their JSON round trip, and the
two can differ.**
- Numbers survive: floats by repr, ints stay ints, and `.inf`/NaN round-trip (and `_positive` refuses them).
- Keys and types don't always survive. Ran: I added a YAML 1.1 bool key `yes: 0.5` under `objects`.
  `parse(raw) != parse(json.loads(json.dumps(raw)))` (`'True'` against `'true'`). A `materials` key that is an int
  stays an int in `serve` and becomes a str on replay.
- A date value (SafeLoader builds `datetime.date`) makes `json.dumps` raise `TypeError` in `serve`, after the log
  file is created, leaving it empty.
- None of this is reachable with today's files.
- Fix: `serve` parses `json.loads` of the meta line it wrote. Unverified.

**NIT 2: `metrics.py::read_log`: `except (ValueError, KeyError, TypeError)` also wraps the slice's own parsers and
`_parts`.**
- A code bug there (a `KeyError` or `TypeError`) reports as "can't be replayed" with exit 2, not as a traceback.
- It is named by type, not silent, and the committed-fixture test would go red on it, so the gate still sees it.
- Fix (optional): wrap the record fields' reads, not the parsers.

**NIT 3: `tests/test_isolation.py::test_a_spike_test_the_gate_runs_is_held_to_the_tests_rules`.**
- `(root,) = ...` raises a bare unpacking error when a second spike joins `testpaths`.
- Its git case is masked by the spawn rule (table row 1). Use `env={}` and assert on the git message.
- `test_voice.py`'s URL exemption borrows the `shared-path-ok` marker, which exempts every node rule on that line.

**Wrong flags and exemptions in `slice_server`:** none. No shipped code is flagged, since the 72 isolation tests pass
at HEAD. `slice_server` is held to the spawn rule but not to the port and git rules, by design: its port is a
parameter, defaulting to 0.
