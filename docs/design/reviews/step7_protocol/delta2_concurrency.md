# Concurrency and lanes: delta round 2 of phase1/protocol (88d7787..cde7634)

Scope: the fold's changes to `src/simcore/host/server.py`, `src/simcore/protocol/messages.py` (`HelloRefused`),
the `network-lane-off-the-world` contract in `pyproject.toml` and its test in `tests/test_tooling_config.py`,
`tests/test_host.py` (the `MAX_QUEUE` and repeated-Upgrade tests, the malformed second hello), the two new socket
tests in `tests/test_godot_net.py`, and step 7's deferrals in `docs/plans/checklists.md`. I reviewed the committed
tree (`git archive cde7634` into `<scratchpad>/delta2/concurrency/tree/`); mutations are copies beside it
(`m_A` to `m_H3`), and each mutated run imports its copy (checked: `simcore.host.server.__file__` resolves into
the copy). Nothing in the worktree was modified. Godot 4.7.2 ran through the tests' own `run_godot`, with
`--basetemp` and so HOME inside the scratch directory.

Counts: fold table 2 fixed, 2 deferred (both accepted), 1 rejected (accepted), 2 open (NITs). New: 0 BLOCKER,
0 SHOULD-FIX, 3 NIT.

## Fold table

| Finding | Status | What I checked |
|---|---|---|
| D-S1 (SHOULD-FIX) C3's deferral unguarded and filed away from its trigger | **fixed** | The contract `network-lane-off-the-world` (forbidden: `simcore.host.server` to `simcore.core.world`, `.simulation`, `.applier`) is in `pyproject.toml`; all three modules exist, and `lint-imports` on the tree is 11 kept, 0 broken. Mutation M-A (`server.py` imports `simcore.core.world`) and M-B (`sessions.py`, which the server imports, imports `simcore.core.applier`) each break it, so indirect reach is caught as well as direct. The C3 row's trigger is now "this step's `intent_result`", which is listed in the same step-7 list (with "after step 5a's integer clock"), so whoever builds that reply reads the row. My delta-1 fix was the contract, and the author took it as written. Its limit is mine: see D2-N1. |
| C3 (SHOULD-FIX) `Dispatch` is a sync callback on the network loop | **deferred, accepted** | Reason and trigger in step 7's checklist; the module docstring states the rule. There is no simulation lane yet for a queue to feed, so building the hand-off now would leave it with no consumer. |
| D-N1 (NIT) `MAX_QUEUE` unguarded, comment's unit wrong | **fixed** | The comment now says "frames". `test_the_server_bounds_each_connection_s_queue_and_its_messages` replaces `serve` and asserts the kwargs. M-D (`MAX_QUEUE = None`) and M-E (the `max_queue=` argument deleted) each turn it red: it fails on the assert and on a `KeyError` respectively, while the other 40 tests stay green. It asserts the literal 16, not the constant, so changing the constant can't keep it green by accident. |
| N2 (NIT) no cap on pre-hello connections | **deferred, accepted** | Listed with a reason (only local programs reach the port) and a trigger (guests from beyond localhost, Phase 5). The trigger points at the wrong place, though; see D2-N2. |
| N4 (NIT) token passed through the test process's environment | **rejected, accepted** | The author's reason holds: delivering the token by environment variable is the design (boundaries §5.3), so the test exercises the shipped delivery. `godot_env` copying all of `os.environ` is the cost, but only in tests, and `monkeypatch` undoes it. The new `_against` helper uses the same pattern. |
| D-N2 (NIT) one `except ConnectionClosed` spans `dispatch`; no session-end record | **open** | `handle` is unchanged, and the finding is in no checklist or backlog row. Its severity is unchanged too: dispatch sends nothing today. |
| D-N3 (NIT) the leak test is red only as a 10 s timeout | **open** | That test is unchanged. The fold's new Godot tests repeat the pattern at 60 s (D2-N3). |

## New findings

### NIT

- **D2-N1. `docs/plans/checklists.md` (C3's row) and `pyproject.toml::network-lane-off-the-world`: the contract
  sees the server's import graph, not the `dispatch` it is handed.** The row says the contract "holds the server
  to" never touching the world on the network loop. That is true of `server.py`'s imports. It is not true of the
  injected `Dispatch`, which is where my own delta-1 failure scenario put the risk. A game-side
  `dispatch` that calls `Simulation` lives in `maxim_overdrive`, imports `simcore.core.world` legitimately, and is
  passed in as `HostConfig.dispatch`. The contract stays KEPT, and World runs on the asyncio loop. My proposed fix
  ("an import-linter contract ... or a test that a dispatch touching `World` is refused") was the weaker of the two
  options, and I did not say that it can't see a callback. The real guard is structural and comes with the trigger:
  when `intent_result` lands, the network lane should hand messages to a queue type rather than call a function
  that returns a reply. So this is a NIT on wording: the row should say the contract guards the server module only,
  and that the hand-off's shape (a queue, never a call) is the guard `intent_result` must add. Separately, the
  `pyproject.toml` comment still says "step 5a hands messages to the simulation lane", while the row now names this
  step's `intent_result`. They should name one trigger.
- **D2-N2. N2's trigger, "guests joining from beyond localhost (Phase 5)", names a phase whose list doesn't carry
  it.** Roadmap Phase 5 is "The player's body and the Overdrive mechanic". Guest sessions are gated in the
  roadmap's "Guest sessions with real NPCs (Phase 5 or later, O28)" list (`docs/roadmap.md` around line 304), which
  has no line about a pre-hello connection cap. This is the same structural gap as D-S1: whoever opens the port
  beyond localhost works from that list, not from step 7's deferrals. Fix (unverified): add one line to that
  guest-session gate list that cross-references the step-7 row.
- **D2-N3. `tests/test_godot_net.py::_against`: a client that never completes the exchange is red only after 60 s,
  as a bare `TimeoutError`, and the lines Godot printed are lost.** `closed` is appended only after `handle` gets
  past `recv` and every `send`. Whenever Godot doesn't connect or send hello, `handle` never runs or raises, and
  `_until` spins `asyncio.sleep(0)` (one core busy) until `wait_for` fires after `TIMEOUT_S`. The lines, which
  would name the cause, are returned only after the wait. Measured with mutation M-H3 (`net_check.gd` treats
  `open` as failing with `ERR_CANT_CONNECT`): each of the two new tests failed after about 60 s with
  `TimeoutError`. The printed line `net-check: open failed Can't connect` was visible only in the old `_with_host`
  test's assert. The gate stays correct, since the failure is still red; the cost is the time to diagnose a
  failure and the gate's wall time. Fix (unverified): record the close in a `finally` inside `handle`, and set an
  `asyncio.Event` there instead of spinning. Then, after `_net_check` returns, wait a short bound on the event and
  `assert closed, lines`.

## Checked and found sound

- **The `HelloRefused` close path.**
  - Before welcome, `_hello`'s `except Refused` still catches it (it is a subclass), so a malformed first hello
    keeps its own code (`bad_version`, `bad_token`, ...).
  - After welcome, `_answer` catches it before the generic `Refused`: it sends `error` with `hello_first`, then
    close 1008 with the same reason, and returns False. `_serve` then returns, and the inner `finally` closes the
    session.
  - Mutation M-F (the `except HelloRefused` arm removed) turns only the new parametrized case
    `{"type":"hello","protocol":0}` red.
  - A `ConnectionClosed` from either await in `_refuse` reaches the outer handler, quietly, as before.
  - One unchanged property, not a finding: after any refusal, `connection.close` awaits the closing handshake (up
    to websockets' `close_timeout`, 10 s) before the `finally` frees the session. A host client that ignores the
    close holds its token for that long.
- **The new socket tests: server lifecycle and flakiness.**
  - `_against` serves on `BIND` port 0 inside `async with serve(...)`, which closes the listener and its
    connections on every exit path. The port reaches Godot by environment variable, and Godot runs in
    `asyncio.to_thread`, so the loop keeps serving.
  - The close code the second test asserts is read after `wait_closed`. That code is the one in the frame Godot
    sent: `NetClient.poll` calls `peer.close(1000, refusal)` before `_finish`'s `quit`.
  - Stability: 15 repetitions of each new test, plus the module's six tests, 36 of 36 green (24 s in total).
  - They can fail: M-H1 (the client closes with an empty reason) gives `(1000, '')`, and M-H2 (no client close at
    all) gives `(1006, '')`. Each is red in about 5 s.
- **The repeated-Upgrade test.** Its one read is bounded by `wait_for(..., WAIT_S)`, and its writer is closed and
  awaited. `get_all` cannot raise, so the 400 is an answer, not a 500 from a handler that failed.
