# Concurrency and lanes: delta round 1 of phase1/protocol (8beb6af..0c7e6e6, plus 88d7787)

Scope: the fold's changes to `src/simcore/host/server.py`, `sessions.py`, `tests/test_host.py`,
`tests/test_godot_net.py`, the asyncio scan in `tests/test_determinism.py`, and step 7's deferrals in
`docs/plans/checklists.md`. websockets 17.4, Python 3.12.12, macOS. Nothing in the worktree was modified. The
round-1 repros (updated only for `HostConfig`'s new keyword-only fields) and the mutation copies are under
`<scratchpad>/delta1/concurrency/`: `leak.py`, `predrop.py`, `order.py`, `mut.py` (the mutations, applied to a
copy in `tree/`), `probe_leaktest.py` and `probe_logtest.py` (repetition probes). Mutated runs import the copy
(checked: `simcore.host.server.__file__` resolves to `tree/src`).

Counts: fold table 4 fixed, 1 deferred (accepted with conditions, see D-S1), 2 open (NITs). New: 0 BLOCKER,
1 SHOULD-FIX, 3 NIT.

## Fold table

| Finding | Status | What I checked |
|---|---|---|
| C1 (BLOCKER) session leak between hello and welcome | **fixed** | `handle` now opens the session and enters `try/finally: sessions.close` before the welcome send. `leak.py` against the folded server: table empty after the drop (`SessionView(sessions=())`), and the rejoin with the host token gets `welcome` (session 2). Mutations in the copy: M1 (close only on a normal return) and M2 (the round-1 shape, welcome sent before the `try`) each turn `test_a_client_that_leaves_before_reading_welcome_frees_its_token` red (TimeoutError after `WAIT_S`). Determinism of the new test: 200 of 200 green on the fixed server, and at all 600 checks a session was live when `_until_no_session` was called, so every iteration really drives the window (not a vacuous empty-table pass); under M2, 20 of 20 red. |
| C2 (SHOULD-FIX) ordinary disconnect logged as ERROR | **fixed** | One `except ConnectionClosed` around the whole of `handle`. `predrop.py`: the drop before hello now logs nothing; the raising dispatch still logs `ERROR connection handler failed` with its `RuntimeError` and closes 1011, the session table empty afterwards, so a real fault is now distinguishable from leaving. Mutation M3 (outer handler removed) turns `test_a_client_that_leaves_mid_handshake_is_not_logged_as_a_server_error` red. Its two halves (hello then close; "not json" then close) are each deterministic: 100 of 100 quiet on the fixed server, 100 of 100 logged under M3. |
| C3 (SHOULD-FIX) `Dispatch` is a sync callback on the network loop | **deferred, accepted with conditions** | Listed in step 7's checklist ("Deferred from the round-1 review") with a reason and a trigger (step 5a's first reply that needs the clock), and the module docstring now says dispatch "may answer from what it holds but never touch the world". Deferring the hand-off itself is right: the simulation lane doesn't exist, so a queue now would have no consumer. But the deferral as written does not hold the risk C3 named; see D-S1. |
| N1 (NIT) `max_queue` implicit | **fixed** (the explicit value) | `max_queue=MAX_QUEUE` (16) is passed beside `max_size`. The rest of N1 (state `write_limit` and the keepalive, which is what ends a half-open session after hello, as choices) was not taken up; and the new constant is unguarded and mis-described, see D-N1. |
| N2 (NIT) no bound on concurrent pre-hello connections | **open** | Not addressed, not in the checklist or a backlog row. Unchanged in substance. The fold slightly lengthens a pre-hello connection's life: the deadline refusal now sends `error` and then awaits the closing handshake, so a silent client holds its slot for `open_timeout` + `hello_deadline_s` + `close_timeout` (10 + 5 + 10 s by default). Still low severity (local processes only). |
| N3 (NIT) session numbering relied on wake order | **fixed** | The test now awaits `a`'s welcome before `b` sends its hello, so the order is the test's by construction. `order.py`: 300 of 300. |
| N4 (NIT) token passed through the test process's environment | **open** | Unchanged (`monkeypatch.setenv` in `_with_host`). Answering round 1's question: `scripts/godot_check.py::godot_env` copies all of `os.environ` (`{**os.environ, "HOME": ..., XDG...}`), so every Godot run inherits the whole test environment, the token included while it is set. Correct and restored after the test, but not an explicit environment. |

## New findings

### SHOULD-FIX

#### D-S1. C3's deferral sits where step 5a won't read it, and drops the guard round 1 asked for

- **Location:** `docs/plans/checklists.md`, step 7's "Deferred from the round-1 review" (C3's row); step 5a's
  section (lines 103 to 246) has no matching item.
- **Defect:** the trigger is "step 5a's first reply that needs the clock", but the item is filed under step 7,
  `phase1/protocol`, the branch this review is folding. Step 5a's section, which its later PRs (PR 4 and the
  `intent_result` work) are built from, has no line about the network lane, the bounded per-session queue, `busy`,
  or "dispatch never touches World". Round 1's fix also asked that a deferral come with a checklist item for a
  check that the network-lane module imports nothing that reaches `World`. That item is absent, and the
  `skip-layer` contract (`pyproject.toml`) still forbids `simcore.host` only from cells, laws and the scene build, not
  from `simcore.core.world`, `simulation` or `applier`.
- **Failure scenario:** the step 5a builder adds `intent_result` the way the signature invites: a `dispatch` that
  calls `Simulation`/the applier and returns the result. World then runs on the asyncio loop, against lanes §4.1's
  one hard rule. Every other session's `recv` and every hello deadline stall for the length of a step. Nothing goes
  red, and the deferral row that would have warned them is in another step's list. That is C3's scenario,
  unchanged: the deferral records it but guards nothing.
- **Fix (unverified):** move or cross-reference the row into step 5a's section, and add to it a check that becomes
  red when the network-lane module reaches `World`: an import-linter `forbidden` contract from
  `simcore.host.server` to `simcore.core.world`, `simcore.core.simulation` and `simcore.core.applier`, or a test
  that a dispatch touching `World` is refused. The contract could be added today. `server.py` imports none of these
  now. I have not run import-linter with it.

### NIT

- **D-N1. `server.py::MAX_QUEUE`: the bound is unguarded, and its comment counts the wrong unit.** Mutating it to
  `MAX_QUEUE = None` (websockets: no flow control, unbounded) leaves all 38 tests in `tests/test_host.py` green.
  Measured in the copy. So the "a bound, never websockets' default by accident" claim is held by nothing; a test
  could read the server-side connection's receive-queue high-water mark. The comment says "messages received and not
  yet read", but websockets 17's `max_queue` is the "high-water mark of the buffer where frames are received" (16
  frames, low-water 4, `websockets/asyncio/server.py` line 633). A fragmented message is many frames, so the
  comment's unit is wrong, although the byte bound (about 16 × 64 KiB per connection) holds either way.
- **D-N2. `server.py::_Host.handle`: the one `except ConnectionClosed` spans `dispatch` and records nothing.** It
  correctly makes leaving quiet, but it also covers `self._config.dispatch(...)`. A `ConnectionClosed` raised from
  inside a dispatch (a future fan-out that sends on another session's connection) would end *this* session as if
  its client had left, with no record. No session end is logged at any level, so a "host token in use" report has
  no trace of when the previous session closed. Low today: the lanes design sends replies through slots, never from
  dispatch. An INFO line at session close (id and role, never the token) would answer both, and catching only
  around the awaits on this connection would answer the first.
- **D-N3. `tests/test_host.py::test_a_client_that_leaves_before_reading_welcome_frees_its_token`: red only as a
  10 s timeout.** Under a leak, the test spins `asyncio.sleep(0)` for `WAIT_S` and fails with a bare `TimeoutError`
  (M1, M2: 10.3 s each). It never reads the second client's reply, which would name the defect (`token_in_use`) at
  once. It still fails reliably (above), so this is diagnosability and gate time, not correctness.

## What I checked and found sound

- **The new `handle` lifecycle on every exit path:**
  - a pre-hello drop (`recv` raises), the deadline, a non-hello first, a bad hello and a refused `open`: no
    session exists, and the outer handler ends the connection quietly;
  - a welcome-send failure, a `_serve` exit by close, a binary frame, a second hello, 1009 and a raising dispatch:
    each closes the session in the inner `finally`;
  - task cancellation and `server.close()` (1001) run that same `finally`.
  `open` is still synchronous with no await before the insert, so racing hellos remain serialized.
- **The close-reason refusals:** every handshake-ending path now goes through `_refuse` (`error`, then 1008 with the
  code as its reason). A `ConnectionClosed` from either await in `_refuse` reaches the outer handler, quietly. The
  binary-frame cases change from 1003 to 1008/`bad_shape`, consistent across pre- and post-welcome, and the tests
  assert both the error message and the (code, reason) pair.
- **The bounded waits in `tests/test_host.py`:** `_reply` and `_closed` are wrapped in `asyncio.wait_for(...,
  WAIT_S)`, and the leak test's poll is too. None of them decides an outcome: every assertion is on a message or a
  close code, so `WAIT_S` only turns a hang into a failure. The asyncio scan in `tests/test_determinism.py` covers
  `src/` only, so tests' `wait_for` and `sleep(0)` (a yield, not a wall-clock wait) are allowed by design.
  `server.py`'s one allowance is `wait_for`, the handshake deadline.
- **The logging test's determinism:** `async with _host()` closes the server and awaits `wait_closed`, so both
  handlers have finished, and logged if they were going to, before `caplog` is read. Shown by 100 of 100 in each
  direction above.
- **`Sessions(cap < 1)` and `Decision` invariants:** pure constructors, no concurrency impact.
