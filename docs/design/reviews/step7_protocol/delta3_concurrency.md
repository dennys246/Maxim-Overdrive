# Concurrency and lanes: delta round 3 of phase1/protocol (e97727d..a532695, merged as 87ff10e)

Scope: the fold's `tests/test_godot_net.py::_against` and its new prose-close test, `src/simcore/host/server.py`
(`text` on every send), `src/simcore/protocol/replies.py::text`, the C3 row in `docs/plans/checklists.md`, the
`network-lane-off-the-world` comment in `pyproject.toml`, and `docs/roadmap.md` for N2's trigger. I reviewed the
committed tree (`git archive 87ff10e` into `<scratchpad>/delta3/concurrency/tree/`). Mutations ran in copies beside
it, and each run imported its copy (checked: `simcore.host.server.__file__` resolves into the copy). Godot 4.7.2 ran
through the tests' own `run_godot`, with `--basetemp`, and so HOME, inside the scratch directory. Nothing in the
worktree was modified.

The merge 87ff10e changes nothing of this branch's. `git diff a532695 87ff10e` equals main's own diff since the merge
base, apart from index hashes and hunk offsets.

Counts: fold table 2 fixed, 2 deferred (still accepted), 3 open (NITs). New: 0 BLOCKER, 0 SHOULD-FIX, 2 NIT.

## Fold table

| Finding | Status | What I checked |
|---|---|---|
| D2-N3 (NIT) `_against` red only after 60 s, as a bare `TimeoutError`, with Godot's lines lost | **fixed** | `handle` records the close in a `finally` and sets an `asyncio.Event`. `go` waits on the event for at most 5 s, and `assert closed, lines` runs after `asyncio.run`. The spin loop `_until` is gone, and no import is left unused. Mutation M1 (`net_check.gd`'s `open` replaced by `ERR_CANT_CONNECT`): the three `_against` tests failed in 20 s in total, against about 60 s each before. Each failed at `assert closed, lines` with `["net-check: open failed Can't connect"]` in the message. On the unmutated tree, the module ran 7 of 7 green in five runs (7 to 10 s each), and `test_host.py` ran 42 of 42 green. |
| D2-N1 (NIT) the C3 row overstated what the contract fences, and two places named different triggers | **fixed** (the row); see D3-N1 for the commit's claim | The row now says the contract "fences only the server's imports, never the injected `dispatch`". The `pyproject.toml` comment and `server.py`'s docstring both name "this step's `intent_result`", so all three name one trigger. The row keeps "through a bounded per-session queue", which is the queue-shaped guard that `intent_result` must add. |
| D2-N2 (NIT) N2's trigger names Phase 5, whose list doesn't carry it | **open** | The roadmap's "Guest sessions with real NPCs (Phase 5 or later, O28)" gate list (`docs/roadmap.md` around line 308) has no line about a pre-hello connection cap or the step-7 row, and the N2 row in the checklist is unchanged. The commit message doesn't mention it. |
| D-N2 (NIT) one `except ConnectionClosed` spans `dispatch`; no session-end record | **open** | `handle` is unchanged apart from `text`. The finding is in no checklist or backlog row. |
| D-N3 (NIT) the leak test is red only as a 10 s timeout | **open** | The test is unchanged. |
| C3 (SHOULD-FIX) sync `Dispatch` on the network loop | **deferred, accepted** | Unchanged from delta 2. The row's wording is now accurate (D2-N1). |
| N2 (NIT) no cap on pre-hello connections | **deferred, accepted** | The reason holds. The trigger's pointer is D2-N2, which is still open. |

## New findings

### NIT

- **D3-N1. Commit a532695's message overstates the fold and leaves out open items.**
  - It says "the C3 row, pyproject and server.py say the import contract fences only the server's imports, never
    the injected dispatch". Only the checklist row says so. The `pyproject.toml` comment and the `server.py`
    docstring changed only their trigger wording.
  - The `pyproject.toml` comment also lost "never a call". That phrase was the one place outside the row that said
    the hand-off's shape is the guard. The row still carries the shape, so this costs nothing in behaviour.
  - The message's "Open (NITs)" list leaves out this lens's D-N2, D-N3 and D2-N2, all three still open.
  - This is the overstated fold table that O25 is about, though small. Fix: correct the hand-off note; adding the
    sentence to the comment is optional.
- **D3-N2. `server.py::_Host._answer`: nothing tests what a reply past `MAX_TEXT_BYTES` does on the shipped path.**
  - `test_the_server_writes_no_reply_past_the_client_s_text_cap` exercises `text` alone.
  - I measured the shipped path with a script, `<scratchpad>/delta3/concurrency/exp/big_reply.py`, using a
    `dispatch` that returns a 65,565-byte reply. The `ValueError` escapes `handle`. websockets logs it at ERROR with
    a traceback and closes 1011 with an empty reason, so the client can report only `closed`. `handle`'s `finally`
    frees the session: the same token rejoined and got `welcome`.
  - That outcome is sound for the network lane: one connection ends, the loop and the other sessions go on, and the
    failure is loud. Nothing pins it, though. When the hand-off becomes a queue (C3's trigger), the check could move
    off the path that frees the token without any test noticing.
  - The cap's arithmetic is right: `encode` uses `ensure_ascii=True`, so characters equal bytes, and the server's
    `>` matches `WireJson.parse`'s `>`.
  - Fix (unverified as a test; the behaviour is measured above): a `test_host` case with an oversized `dispatch`
    that asserts close 1011 and that the token rejoins.

## Checked and found sound

- **`_against`'s exit paths.**
  - The client never connects: `handle` never runs, so the event wait times out after 5 s and the assert reports
    Godot's lines (measured, M1).
  - The client connects but never sends `hello`: Godot's exit drops TCP, and `recv` raises `ConnectionClosed`. The
    `finally` records the close and sets the event before the exception leaves `handle`.
  - The exchange hangs past 5 s: leaving `serve` closes the connection, and the `finally` appends then. So the
    test fails on the code and reason rather than on `assert closed`. It is still red, and it is bounded.
  - `asyncio.Event()` is created before `asyncio.run`. It binds its loop lazily (Python 3.10 and later), so this is
    safe on 3.12 and 3.14.
  - `wait_for` raises the builtin `TimeoutError` (Python 3.11 and later), which the `suppress` names.
- **`text` on the loop:** every send in `server.py` goes through it, and each is a bounded `json.dumps` of at most
  64 KiB on the network loop. Binary frames don't pass through it.
