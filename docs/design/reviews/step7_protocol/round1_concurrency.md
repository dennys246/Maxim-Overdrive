# Concurrency and lanes: review of phase1/protocol (origin/main aaebc1b..8beb6af)

Scope: `src/simcore/host/server.py`, `sessions.py`, `tokens.py`, `tests/test_host.py`, `tests/test_godot_net.py`,
against `docs/design/realtime_lanes_coop.md` §4.1 and §5, and `docs/design/boundaries.md` §5.3. websockets 17.4,
Python 3.12.12. Nothing in the worktree was modified; the repros are scripts under
`/private/tmp/claude-501/-Users-dennyschaedig-Scripts-Maxim-Overdrive/e1266556-cb5d-4cec-a4ba-7648bc3e3cd9/scratchpad/review1/concurrency/`.

Counts: 1 BLOCKER, 2 SHOULD-FIX, 4 NIT.

## BLOCKER

### C1. A client that drops between hello and welcome leaves its session in the table for the rest of the launch

- **Location:** `src/simcore/host/server.py::_Host._handshake` and `_Host.handle`
- **Defect:** `_handshake` calls `self._config.sessions.open(hello.token)` and then `await connection.send(encode(reply))`,
  and `handle` only enters `try: ... finally: sessions.close(session)` after `_handshake` returns. If the welcome send
  raises, `sessions.close` never runs. A send raises when the peer has closed: websockets' `send_context` raises the
  stored `ConnectionClosedOK/Error`. The same leak happens when `server.close()` runs during that send.
- **Failure scenario (reproduced, `leak.py`):** the client sends a valid host hello and closes straight away, as a
  Godot client quitting or crashing during the join would. The server's `recv` returns the hello, `open` adds session 1,
  and the welcome send raises `ConnectionClosedOK: received 1000 (OK); then sent 1000 (OK)` (logged as "connection
  handler failed"). Afterwards `sessions.view()` is still `SessionView(sessions=(Session(session_id=1, role=HOST, ...),))`,
  and a fresh connection with the host token gets `{"code":"token_in_use","type":"error"}`. **The host is locked out
  until the process restarts.** A guest token gets locked out the same way, and every leaked session also counts
  toward the cap, so after `cap` such drops every hello gets `busy`. Under the design ("when the host leaves, the
  world pauses until the host token reconnects", lanes §5) this is a permanent pause.
- **Why the tests miss it:** every test in `tests/test_host.py` that gets a welcome also reads it before it
  disconnects.
- **Fix (unverified):** make "the session is open" and "the session will be closed" a single step. One way: have
  `handle` own the whole lifetime (`session = sessions.open(...)`, then `try:` send the welcome and serve, `finally:`
  close), for example with `Sessions` exposing a context manager. A regression test can drive it deterministically in
  one event loop: the client calls `send(hello)` then `close()` with no await in between, which is what `leak.py`
  does. It reproduced on every run.

## SHOULD-FIX

### C2. An ordinary disconnect during the handshake is logged as an ERROR "connection handler failed" with a traceback

- **Location:** `src/simcore/host/server.py::_Host._hello`, `_Host._refuse`, `_Host._handshake`
- **Defect:** `_serve` catches `ConnectionClosed`, but the handshake phase does not. If `connection.recv()` in
  `_hello` (peer gone before hello), the send in `_refuse` (peer gone before its error), or the welcome send (C1) raises
  `ConnectionClosed`, the exception escapes `handle`. websockets' `conn_handler` then logs it at ERROR with
  `exc_info=True` (`websockets/asyncio/server.py`, around line 764).
- **Failure scenario (reproduced, `predrop.py`):** connect, then close before sending hello. The server logs
  `ERROR connection handler failed` with a `ConnectionClosedOK` traceback. Any client that leaves early, any port probe
  that completes the upgrade, and any Godot client the player closes on the join screen produces a handler-failure
  traceback. A real handler failure (a raising dispatch, below) then looks exactly like routine noise. This is the same
  missing exit path as C1, so one fix covers both. It also contradicts lanes §4.1's split between a crash, which is
  loud, and "a network task's failure ends only its session".
- **Fix (unverified):** handle `ConnectionClosed` once, around the whole of `handle`, as the end of the connection,
  not just around `_serve`.

### C3. `Dispatch` is a synchronous request-to-reply callback on the network loop, the wrong shape for the lanes contract

- **Location:** `src/simcore/host/server.py::Dispatch`, `_Host._answer`
- **Defect:** `Dispatch = Callable[[Session, ClientMessage], Mapping[str, object]]` runs on the asyncio loop thread
  (the network lane), and its return value is sent straight back. Lanes §4.1 says the network lane "decodes and
  schema-checks, never touches World". Its inbound path is `put_nowait` onto a bounded per-session queue, where a full
  queue is answered `busy`. Replies come back through latest-wins per-session slots, with `call_soon_threadsafe`.
  Neither the queue nor the busy reply exists, and the signature has no room for them.
- **Failure scenario:** at step 5a, the replies that need the clock (`intent_result`, `time_decision`) join
  `dispatch`, as the module docstring says. The path this signature invites is a dispatch that calls into `Simulation`
  or the applier and returns `intent_result`. That runs World on the network lane, against §4.1's one hard rule. It
  also blocks every other session's recv and every hello deadline while a step runs, because dispatch is sync on the
  one loop. Nothing would catch it: the `[tool.importlinter]` skip-layer contract (pyproject line 146) forbids
  `simcore.host` only from core internals such as the grid, not from `simcore.core.world`, `simulation` or `applier`.
  It applies to the package as a whole, so it can't tell the network lane's module from the simulation lane's. No test
  says "the network lane never touches World".
- **Today:** dispatch is test-only (`_echo`, `_reply`), so no lane touches World yet. This finding is about the
  contract the next step builds on, not a live race.
- **Fix (unverified):** either give `server.py` the design's hand-off now (a bounded inbox, `busy` on full, replies
  through slots), or narrow `Dispatch`'s docstring to "stage-1 acceptance only, never the simulation". In the second
  case, add a step-5a/lanes checklist item for a check that the network-lane module imports nothing that reaches
  `World`, so the deferral is visible.

## NIT

- **N1. `server.py::start`: `max_queue` is websockets' default, not set.** The design asks for "a bounded `max_queue`"
  (§4.1). The default (16 frames, low-water 4) is bounded: at most 16 × 64 KiB = 1 MiB buffered per connection,
  including pre-hello connections. But the bound is implicit, and a websockets default change would move it silently.
  Pass it explicitly beside `max_size`. `write_limit` (32 KiB) and the keepalive (`ping_interval=20`,
  `ping_timeout=20`) are the defaults too. Keepalive is what ends a half-open session after hello, since there's no
  idle deadline. Worth stating as a choice.
- **N2. `server.py::_Host`: no bound on concurrent unauthenticated connections.** The session cap counts only sessions.
  Any local process can hold open many upgraded, pre-hello connections, each for up to `hello_deadline_s` (5 s) after
  an `open_timeout` (10 s) upgrade, each buffering up to 1 MiB. Only local programs can do this (Origin refusal stops
  web pages before the handler runs), and they could hurt the player in other ways, so it's low severity.
- **N3. `tests/test_host.py::test_a_guest_token_is_a_guest_and_sessions_are_numbered_in_order`: ordering not enforced.**
  Both hellos are sent before either reply is awaited, so the session numbers depend on the order in which the
  server's loop wakes the two handler tasks, which follows the selector's readiness order. It passed 300 of 300 runs
  here (`order.py`, macOS kqueue), so it isn't shown flaky, but it relies on an ordering no API promises.
  Deterministic form: await `a`'s welcome before `b` sends its hello, as `test_the_session_cap_refuses_one_more_with_busy`
  already does.
- **N4. `tests/test_godot_net.py`: environment set from the test.** `monkeypatch.setenv` writes the token and port into
  the test process's `os.environ`, and `run_godot` reads them from there. It's correct and restored, and `to_thread`
  plus `TIMEOUT_S` bounds the worker thread. But it means the token travels through the whole test process's
  environment, not only an explicit env passed to the one spawn. That matches "never argv", but goes against the
  "each with an explicit environment" spirit. Check that `godot_env(home)` copies only what's needed.

## What I checked and found sound

- **Session table under concurrent connections:** one asyncio loop, and `Sessions.open` is synchronous with no
  `await` between the token-in-use and cap checks and the insert. Two racing hellos with the same token are therefore
  serialized: one gets a welcome, the other `token_in_use`. The cap can't be overshot. `Sessions` isn't thread-safe
  (`view()` iterates a live dict), which is fine while only the loop touches it. If the simulation lane ever calls
  `view()` from its own thread, it has to go through the loop. Flag this at lanes.
- **Dispatch that raises** (`predrop.py`, a dispatch that raises `RuntimeError`): the exception leaves `_serve`,
  `handle`'s `finally` closes the session (table empty afterwards), and websockets closes with 1011. Only that session
  ends, as §4.1 asks, apart from the logging confusion in C2.
- **Dispatch that blocks:** it blocks the whole loop (C3). There's no timeout or meter, which is expected before the
  lanes step.
- **Hello deadline:** `asyncio.wait_for(recv(), deadline)` covers only the first message, after the upgrade.
  websockets' `recv` can be cancelled safely, including mid-fragment. `TimeoutError` is the right type on 3.11 and
  later. With `deadline=0.0` the test is deterministic (no data is ever sent).
- **Second hello, binary frame after welcome, 1009:** each closes, the `async for` ends on `ConnectionClosedOK/Error`,
  and the session is closed in `finally`.
- **Server shutdown:** `server.close()` closes connections (1001) and `wait_closed` waits for the handler tasks, so the
  `finally` blocks run. The exception is the C1 window.
- **Slow readers:** each reply is one awaited `send`, so a client that doesn't read pushes back on its own handler
  through `write_limit`. No growth without a bound.
- **Tests leaking servers, ports or threads:** every server is closed in a `finally` (`_host`, the bind test,
  `_with_host`) or by `async with server` (the capture test). Clients use `async with`, the raw HTTP writer is closed
  and waited on, every bind is port 0 on 127.0.0.1, and Godot runs in a `to_thread` bounded by `TIMEOUT_S`.
  `tests/test_host.py` passes (32 in 0.62 s), also with `-W error::ResourceWarning`. Nothing sleeps, and the token
  free-again test passes reliably because the second upgrade takes several loop round trips after the first handler's
  `finally` is ready to run.
- **Tokens:** pure, with no shared mutable state. `match` compares against every token.
