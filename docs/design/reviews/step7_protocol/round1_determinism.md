# Determinism and replay: phase1/protocol (origin/main aaebc1b .. HEAD 8beb6af)

Counts: BLOCKER 0, SHOULD-FIX 1, NIT 3.

## Findings

### SHOULD-FIX D1: `tests/test_determinism.py::NOT_SIMULATION`: the comment and commit 791aa12 promise more than the scan checks

The new comment says "the rest of the host stays scanned, since its pacing loop will feed the world", and commit 791aa12
says the same. That is literally true: only `simcore/host/tokens.py` is exempt. But the static scan
(`findings`, `_name_findings`) bans only the module names `time`, `datetime`, `secrets`, `uuid`, `random` and `timeit`.
It cannot see asyncio's clock, and asyncio's clock is what a pacing loop in this host would use. I checked by calling
`tests.test_determinism.findings` on these snippets:

- `asyncio.get_running_loop().time()` gives `[]`
- `await asyncio.sleep(0.05)` gives `[]`
- `asyncio.wait_for(x, 5.0)` gives `[]` (the real call in `server.py::_Host._hello` passes too)
- for comparison, `from time import monotonic` is flagged

Failure scenario: step 5a writes the pacing loop in `simcore/host` as
`now = loop.time(); world.advance(now - last)`, or it feeds a wall-clock-measured `apply_us` into the ordering key.
The scan stays green, and a replay of the intent log diverges because the log never recorded the wall duration.
The design's real guards are B14's data-flow test ("no wall-clock duration reaches `World.advance`") and the runtime
`sys.setprofile` tripwire (boundaries §3, which "ships with sim-clock"). Neither is in this branch. So the comment
presents the static scan as the guard for the pacing loop, and it is not one.

Fix, unverified. Either reword the comment and the B14 row to say what the static scan reaches and name the tripwire
and the B14 test as the pacing loop's guard, or extend `_name_findings` to flag `asyncio.sleep`, `asyncio.wait_for`,
`asyncio.timeout*` and `.time()` on a loop in modules that import from `simcore.core`. The second option needs an allowance
for the handshake deadline in `server.py`, which shows that a per-file exemption is too coarse a unit here.

### NIT D2: `docs/standards_backlog.md` B14 row is stale

The row still says "since `server/` is exempt from the determinism scan". After this branch the host is scanned except
for `tokens.py`. The row's trigger is "Phase 1 step 7 (`phase1/protocol`)". This branch delivers the Origin, token and
loopback tests, but not "nothing from the transport but validated intent values reaches `World`": no World is wired,
and `dispatch` belongs to the caller. Failure scenario: a reader of the backlog believes the whole host is exempt, or
believes the data-flow test landed with step 7. The row should keep the data-flow test and move its trigger to step 5a.

### NIT D3: `src/simcore/host/sessions.py::Session.session_id` and `replies.welcome` share a name with the replay id

The host's `session_id` is a connection counter in arrival order ("numbered in the order they open"). Two clients
racing their `hello` get different ids on different runs. The checklist's "Replay ids (O43, O45)" names a
different `session_id`, derived from the log header and required to be equal across runs of one log. Both ids are
correct today: per boundaries §6, actor ids come from the simulation lane's allocator when a logged `join` is
applied, and the ordering key `(apply_tick, kind_rank, apply_us, actor_id, seq)` holds no arrival order. Failure
scenario: in 5a, someone wires the host's `Session.session_id`, which `Dispatch` already receives, into a log record,
a pid or an actor id because the names match. A replay then depends on connection order. A one-line note on
`Session` ("transport-only; never logged, never an actor id"), or a rename such as `connection_no`, would close this.

### NIT D4: `.gitattributes` doesn't pin `client/tests/fixtures/wire/**`

`stale()` compares bytes, and `docs/generated/*` is already pinned with `eol=lf` for the same reason. The `.bin` frames all
contain NUL bytes in their length prefixes, so git treats them as binary, which is safe. But `manifest.json` is multi-line LF
text, and the `json/` and `client/` fixtures are text. On a checkout with `core.autocrlf=true`, `manifest.json` gets CRLF line
endings and `test_the_committed_fixtures_are_what_the_script_makes` fails. CI has no Windows runner, so the impact is
low. Also, any stray file in the directory (a macOS `.DS_Store`) is reported as "left over". That failure is loud and
safe, but it is spurious. Fix, unverified: `client/tests/fixtures/wire/** -text`.

## What I checked and found sound

**Frame encoder (`grammar.encode_cells`, `pack`)**

- Every dtype is explicitly little-endian (`DTYPES` maps to `<u1 <u2 <u4 <f2 <f4`).
- A mismatched dtype raises before encoding, so a native big-endian array fails loudly and is never byteswapped silently.
- `np.ascontiguousarray(..., dtype)` gives C order (z, y, x, with x fastest) even for a Fortran-ordered input.
- Shape and sizes are Python ints from `.shape` and `len`.
- The header goes through `strict_json.encode`: `sort_keys`, compact separators, `ensure_ascii`, integers only.
  `_check_numbers` refuses floats. A numpy scalar falls through to `json.dumps`, which raises TypeError, so it fails
  loudly. No float formatting reaches the server's JSON.

**Catalogue hash (`catalogue_hash`)**

- It uses `digest`'s c14n-1 over lists of str, int and bool, with exact types, keys sorted by code point, and no floats.
- It depends on channel order by design, and every caller passes the order it was given.

**Fixture generator (`scripts/wire_fixtures.py`)**

- It has no set iteration and no clock.
- Dicts are ordered by insertion, and the manifest uses `sort_keys`.
- `_repack` writes `0.0` through `json.dumps`, which uses `repr` and is stable.
- `_announced` is pure.

**Byte-identity, measured.** I hashed every output of `files()` (script:
`/private/tmp/claude-501/-Users-dennyschaedig-Scripts-Maxim-Overdrive/e1266556-cb5d-4cec-a4ba-7648bc3e3cd9/scratchpad/review1/determinism/check.py`).

| Run | Result |
|---|---|
| Python 3.12.12 / numpy 2.5.5, `PYTHONHASHSEED` = 0, 3, 4 and random | `stale(OUT) == []`, sha256 `6f18e1eb…288b12` on every run |
| Python 3.14 / numpy 2.5.5 (another worktree's venv, this worktree's `src` first on the path) | the same hash |

**f16 conversion.** `np.linspace(-40, 1200, n).astype("<f2")` gives the same bits as going through f32 first
(`astype("<f4").astype("<f2")`) for both fixture shapes, n = 8 and n = 24. So a hardware f16 path that rounds twice
can't change these fixtures. Across machines the live server promises only the outcome class (CLAUDE.md), so f16 frames
don't need to be byte-identical between machines. Only the committed fixtures must be, and they are. The drift job
runs numpy unpinned, so a numpy that changes `linspace` or the f16 cast shows up there as stale fixtures, which is the
right signal.

**Staleness check (`stale`, `test_the_committed_fixtures_are_what_the_script_makes`)**

- It compares byte for byte and catches missing and left-over files.
- `test_the_generator_reports_a_changed_a_missing_and_a_left_over_file` proves all three by mutation.
- It is sound for determinism. It is not a guard that old fixtures survive an encoder change, because regenerating
  resolves the change. That is Wire integrity's lens.

**`NOT_SIMULATION` exemption**

- `_simulated` matches the exact path or a directory prefix, so `"simcore/host/tokens.py"` exempts that one file.
  `server.py` and `sessions.py` are still scanned and pass. The exemption is narrow.
- It is justified because no secret flows onward. The token strings stay inside `Tokens`, and `match` returns an
  index. `Session` carries `session_id` (a counter), `role` and `token_index`, and holds no entropy. The import
  layers (core lowest) stop `World` from importing the host.
- A stale entry after a rename would scan more, not less, so it is harmless.

**`asyncio.wait_for` in `_hello`**

- The monotonic deadline decides only whether a connection is admitted. Per boundaries §6, joins become logged `join`
  records that the simulation lane applies. So wall time decides who joined, and the log records it, which a replay can
  reproduce. That is correct.

**Arrival order**

- `Sessions.view()` sorts by id, and `_live` is a dict.
- Today nothing in the host is ordered by arrival when it reaches the simulation. The ordering key in boundaries §6
  replaces the arrival-order `host_seq`.

**Tests run:** `tests/test_wire.py` and the determinism static scan, `218 passed, 1 skipped`.
