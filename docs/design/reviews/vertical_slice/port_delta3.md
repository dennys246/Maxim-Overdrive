# The slice's port onto Simulation: delta round 3 (final)

Reviewer: delta-3 reader, read-only, on `d1c7b2c` (fold `04d2386..d1c7b2c`). Mutations ran in a scratch copy
(`git archive HEAD`) with the worktree's venv, one at a time, each file restored from the worktree afterwards.
Neither the full suite nor `prepush.sh` was run.

At HEAD, `spikes/slice/tests` and `tests/test_isolation.py` pass 249 of 249 (19 s).

**Summary:** all three SHOULD-FIX rows are fixed, and the two NIT rows are accepted as left. No BLOCKER and no
SHOULD-FIX. Three NITs go to the backlog.

## Delta 2 fold table

| Finding | Status (reviewer) | Evidence |
| --- | --- | --- |
| Delta 2 S1 (and the open isolation row): `socket.create_server((host, 8080))` | fixed | With `ADDRESS_CALLS = {"bind"}`, 3 tests went red: both new fixed-port cases and the spike case. With the git rule's root back to `"tests/"`, the git case went red (1 of 3). Before the fold, all 3 cases passed under that mutation. Nothing shipped is flagged wrongly; see the note below. |
| Delta 2 S2 (and the open data row): replay and serve unguarded | fixed | Each of these turned exactly one test red, with 174 others passing. `serve` using `cfg = config.load()` turned `test_a_session_runs_on_the_data_it_logged` red. `serve` using `config.parse(config.raw())` (reading the files twice) turned the same test red. `check_replay` replaying on `config.load()` turned `test_the_replay_command_runs_on_the_logged_data` red. |
| Delta 2 S3: layout changed without a version bump | fixed | `LOG_VERSION = "slice-log-2"`. The restored `-1` fixture is byte-identical to `14bfbfc`'s. The `-2` fixture is `04d2386`'s log with only the version string changed, and it has the same digest. With the version check disabled (`if False:`), `test_an_older_committed_log_is_refused_by_its_version` went red. |
| Delta 2 NIT 2: the broad handler | rejected (reviewer, as a fold item) | The handler is named by type, and the committed-log replay sees a parser bug. NITs aren't folded in this round, per the owner's ruling. |
| Delta 2 NIT 3: borrowed `shared-path-ok` marker | rejected (reviewer, as a fold item) | Same reason: a NIT, not folded in this round. It stays a backlog candidate. |

**Wrong flags from `ADDRESS_CALLS`:** none on shipped or tested code.

- asyncio's `loop.create_server(factory, host, port)` and `loop.create_connection(factory, host, port)` take a
  protocol factory first. That is never an `ast.Tuple`, so the new branch can't fire on them. I ran
  `loop.create_server(f, "127.0.0.1", 0)` and it returned `[]`.
- The slice's own calls aren't flagged either. `server.py:93` uses `create_server(("127.0.0.1", port))` with `port`
  as a parameter, outside the tests-only rule. The 7 calls in `test_server.py` use
  `create_connection(("127.0.0.1", server.port))`, where the port is an attribute, so `_Module.value` returns
  `None` and nothing is flagged.

**`serve`'s round trip:** this is correct.

- `serve` parses `json.loads(meta)["meta"]["data"]` from the exact string it writes, so the session and a replay
  parse the same values. This closes delta 2 NIT 1.
- Reverting to `parse(data)` on the YAML objects isn't guarded by a test. That is acceptable: the fold row claims it
  only as a side effect, and the case it covers isn't reachable with today's files.

## New findings

**NIT 1: `tests/test_isolation.py::SERVER_CALLS_PORT_AT` / `::_fixed_port`: `socket.create_server`'s positional
backlog reads as a port.**
- `create_server: 2` follows asyncio's `start_server(cb, host, port)` layout. In
  `socket.create_server(address, family, backlog, ...)`, index 2 is the backlog.
- Ran: `socket.create_server(("127.0.0.1", 0), socket.AF_INET, 5)` in `tests/` was flagged with "a test server on
  a fixed port". That is a false positive on port 0.
- The mapping predates the fold, and no code in the tree uses this spelling, so there's no failure on any path
  today. The fold's docstring now names `socket.create_server`, which makes the two layouts collide visibly.

**NIT 2: `tests/test_isolation.py::_fixed_port`: an address held in a variable, or asyncio's `create_connection`,
isn't seen.**
- Ran: `ADDR = ("127.0.0.1", 8080); socket.create_server(ADDR)` returns `[]`.
- Ran: `loop.create_connection(f, "127.0.0.1", 8080)` returns `[]`, because `create_connection` has no
  positional-port entry.
- No code in the tree uses either spelling. Both are the scan's known limits (it reads literals only), not
  regressions.

**NIT 3: `tests/test_isolation.py::test_a_spike_test_the_gate_runs_is_held_to_the_tests_rules`: the new loop passes
vacuously when no spike is in `testpaths`.**
- This replaced delta 2 NIT 3's unpacking error. It is harmless, because a spike outside `testpaths` isn't run by
  the gate, so its rules don't matter.
- A one-line `assert` that the loop ran would make the test's reach explicit.

Also seen, and not a finding: `spikes/slice/README.md` line 14 is now 139 characters, where the file's prose
otherwise wraps at 120. No lint checks this.
