# Executor review: phase1/protocol (origin/main aaebc1b ... HEAD 8beb6af)

Lens: Executor. I read the diff's code (strict_json, messages, converters, catalogue, frame_header, grammar, replies,
text, host/server, sessions, tokens, and the GDScript net/ decoders, NetClient and net_check.gd) and the four commit
messages. I tested everything in scratch copies: `executor/py` (a git archive of HEAD, run with PYTHONPATH pointing at
it) and `executor/client` (a copy of client/, imported and run through `godot_check.run_godot` with HOME inside the
scratch directory). I did not modify the worktree; I checked afterwards that it is still clean and that the copy's
`src/` matches it again.

Counts: **1 BLOCKER, 4 SHOULD-FIX, 6 NIT.**

## BLOCKER

**E-B1. `src/simcore/host/server.py::_Host._handshake` / `handle`: a session leaks when the client closes before
`welcome` is sent, and its token is locked out for the rest of the launch.**
`_handshake` calls `sessions.open(...)` and then `await connection.send(encode(reply))`. The `try/finally` that calls
`sessions.close` lives in `handle`, and execution enters it only after `_handshake` returns. If the client sends `hello`
and then closes cleanly, `send(welcome)` raises `ConnectionClosedOK`. The exception passes through `handle` without
closing the session.
Reproduced (`executor/leak.py`, against the real `start()`): five times, connect, `send(hello)`, `await ws.close()`.
After the first attempt `sessions.view()` holds 1 live session, and it stays there. A fresh connection with the same
token then gets `{"code":"token_in_use","type":"error"}`. Each attempt also logs an ERROR traceback, "connection
handler failed", from websockets. With the host's own token, the player can't rejoin their own game until relaunch.
A Godot client that quits or crashes during the handshake triggers this. The same unguarded `send` in `_refuse`
produces the traceback noise. That path leaks no session, because `open` refused, but it is still a handler crash for
an ordinary disconnect.
Fix (unverified): open the session and enter the `try/finally` before sending `welcome`, or catch `ConnectionClosed`
around the welcome send and close the session there. Add a test that does hello then close and then rejoins with the
same token.

## SHOULD-FIX

**E-S1. `client/addons/engine/net/wire_json.gd::parse`: it is not a strict JSON reader, so the client accepts frame
headers the server's decoder refuses. The claims "WireJson (strict JSON over Godot's JSON class)" and "applies the
same rules" (grammar.py's docstring) are false outside the fixtures.**
Measured on Godot 4.7.2 (`executor/probe*`, results recorded below). Godot's `JSON.parse` accepts trailing commas
(`[1,2,]`, `{"a":1,}`), leading zeros (`01`) and raw control characters inside strings, and WireJson adds no check
for any of them. `PackedByteArray.get_string_from_ascii()` (frame_decoder.gd::_header) also stops at a NUL byte.
I built frames from the base fixture and read each with both decoders:

| header change | Python `decode_frame` | Godot `FrameDecoder.decode` |
|---|---|---|
| valid JSON + `\x00junk` inside the header length | refused bad_json | **accepted** |
| trailing comma before `}` | refused bad_json | **accepted** |
| `"tick":05` | refused bad_json | **accepted** |
| `"tick":1e300` | refused not_int | refused bad_json |
| raw `\x01` inside a channel name | refused bad_json | refused bad_identity_key |
| `"tables":[{"protocol":1.0}]` | refused unknown_field | refused bad_version (`non_integer_keys` is per key name, not per path) |

The last three are code divergences. The first three are outcome divergences. The server never writes such text, so
this is defence in depth, not an exploit. But the branch's stated contract is one outcome per input for both readers,
and the fixtures don't sample this class of input.
Fix (unverified): in WireJson, refuse a NUL or any control byte in the header, and have `_scan` refuse a trailing comma
and a leading zero, since it already walks every token. Refuse a float of magnitude 2^53 or more as Python does, or
have Python refuse it with bad_json; either way, add the rows above as fixtures in `json/` and `frames/`.

**E-S2. `client/addons/engine/net/wire_fields.gd::identity`: the client refuses an unknown optional channel whose name
or unit has a non-ASCII escape, which breaks the extension rule.**
The comment says "A header is ASCII, so printable is 0x20 to 0x7E". That holds for the bytes, not for the decoded
strings, because JSON escapes such as `é` decode to non-ASCII. Python's `identity_key` uses `str.isprintable()`.
Measured: an optional channel `Channel("café", "ratio", "f32", "raw", required=False)` appended to the base frame.
Python ignores it (`accepted`, ignored `channel:café`); Godot refuses the whole frame with `bad_identity_key`. The same
happens with an optional channel whose unit is `"°c"`. catalogue.py's docstring promises exactly this case works: "an
optional channel with a unit this build has never heard of is ignored". A future server that adds such a channel
breaks every v0 client.
Fix (unverified): either restrict names and units to ASCII in the server's schema, which is a registry rule needing a
test on both sides, or make the client's check match `isprintable`. Add the fixture.

**E-S3. `tests/test_host.py` (`_reply`, `_closed`, `_drain`): five server guards are held by tests that hang instead of
failing.** These mutations each made the run time out (60 s, after an earlier 300 s run) instead of going red:
- `max_size` ×4;
- the second-hello close removed;
- the binary-after-welcome close removed;
- the `protocol != PROTOCOL` check removed;
- `wait_for` removed from the hello deadline.

The cause: `ws.recv()` has no timeout, and pytest has no `timeout` setting (none in pyproject or the lock). In the gate,
such a regression would hang prepush with no failure line naming the guard. Fix (unverified): wrap the test client's
waits in `asyncio.timeout(...)`. That is not a wall-clock dependency in the simulation, only a bound on a socket read.

**E-S4. `src/simcore/core/text.py::player_text`: invisible characters outside `Cf` pass, so the claims "none of the
characters that render as nothing" and "zero-width runs that could carry hidden bits are refused" are false.**
Each of these was accepted (measured, `executor/txt.py`):
- `"a" + "️"*40`: variation selectors are category Mn;
- `"a" + "\U000E0100"*40`: 240 supplementary variation selectors, a known way to hide one byte per character in
  invisible text;
- `"a‍️‍️b"`: a run of joiners, legal because a Mn neighbour counts as "visible";
- `"hi͏͏"`: COMBINING GRAPHEME JOINER;
- `"ㅤ"` alone, and `"⠀"` alone: HANGUL FILLER and BRAILLE BLANK pass the "not all spaces" check. The name
  rule already refuses BLANK and FILLER.

O61 as written names format characters only, so this may be the owner's scope. But the module's own docstring and O61's
rationale claim more than the code does.
Fix (unverified): refuse Default_Ignorable_Code_Point, keeping the joiners in their contexts, plus the BLANK/FILLER
names; or narrow the docstring and O61's rationale and record the gap.

## NIT

- **E-N1 `strict_json.py::_integer`**: the `len(text) > _INT_DIGITS` guard survives deletion: all 322 tests stay green.
  It matters, because without it `int("9"*5000)` raises a plain `ValueError` (the 4300-digit limit), which is not
  `Refused`. The server catches `Refused` only, so the handler would crash. Add a 5000-digit fixture.
- **E-N2 `server.py::start` `compression=None`**: deleting it keeps every test green. The test clients all pass
  `compression=None`, so no test offers permessage-deflate and checks that the server declines it.
- **E-N3 `grammar.py::_containers`** (the cells-grid shape check), and its twin in frame_decoder.gd: deleting it keeps
  both suites green. `grid_shape_differs` is refused `bad_shape` by `_layout` anyway, so the fixture doesn't isolate the
  check. Likewise, deleting the raw-scale check in Godot's `_channel` keeps the client suite green: `raw_with_scale`
  fails the known-channel identity check first. Use an unknown optional raw channel with scale [2,1] to isolate it.
  The same holds for WireJson's own ASCII loop, which frame_decoder's loop masks (survived deletion).
- **E-N3b `tokens.py::Tokens.match`**: an early return on a match survives deletion. Timing isn't testable here; the
  docstring claim is held by review only.
- **E-N4 `wire_fields.gd::digest`**: `^...$` in Godot's PCRE matches before a trailing `\n`, where Python uses
  `fullmatch`. A catalogue of `"<hash>\n"` gets Python bad_shape and Godot bad_version (measured).
- **E-N5 commit 8009004's mutation counts**: I reproduced repeated-key 5, pin 2 and unknown-required-channel 1. My
  version of the known-channel identity mutation (skipping `_same_channel`) gave 1 failure, not the 2 claimed. The
  claim may rest on a different mutation; worth stating which.
- **E-N6 `net_client.gd::_on_text`**: `welcome` is stored without checking any field but `protocol`. A welcome with no
  `catalogue_hash` makes every frame `bad_version` against the string "<null>". That fails safe, but the refusal names
  the frame, not the welcome.

## Claims checked and found true

- **Godot drops the error packet that arrives with the close** (commit 791aa12). I patched the copy's `NetClient.poll`
  to print the state and packet count each poll, and to drain packets before handling CLOSED. With a wrong token, the
  state went from OPEN straight to `state=3 avail=0`: the packet was never available. With the close-reason read
  removed, the outcome became "closed 1008". The claim and the mutation proof hold.
- **Both decoders reach the same outcome on every fixture.** The unmodified client suite passes 81 tests; the Python
  modules pass 322 with 1 skipped. Godot mutations that go red:
  - the repeated-key check (5);
  - the pin (2);
  - unknown required channel, grid and table (1 each);
  - the layout payload check, a duplicate channel, protocol;
  - depth;
  - the hash compare (a compile failure, so it doesn't count as a proof);
  - the non-integer scan (also a compile failure).
- **Python mutations that go red:**
  - strict_json: repeated key, the pin, surrogates, depth, the cap counted before parsing, the encoder refusing floats;
  - grammar: unknown required channel and container, identity, the ASCII header, the catalogue check, a duplicate
    channel, a duplicate container;
  - catalogue: the raw scale check;
  - messages: the time scale rule;
  - player_text: both joiner rules, NFC before the cap, isspace;
  - the server and its replies: Origin, 400, the bind literal, the close reason, the error field, welcome's build;
  - sessions: token_in_use, the cap, HostOnly, the frozen view;
  - tokens: the token role, O_EXCL, mode 0600.
- **The 2^53 pins in both readers** (`tick_below/at/past_2p53`); stage 1 refusing 5500.0 and true (not_int), in
  test_host and the fixtures; the Godot upgrade request carrying no Origin (test_godot_net captures it).
- **The checklist's "shipped path" item** is honest: no game code calls `start`, `encode_cells` or `NetClient` yet.
