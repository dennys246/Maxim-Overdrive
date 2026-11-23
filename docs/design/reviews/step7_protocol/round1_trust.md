# Trust boundary review: phase1/protocol (origin/main aaebc1b ... HEAD 8beb6af)

Lens: Trust boundary. Covers the server side (`src/simcore/host/`, `strict_json.py`, `messages.py`, `converters.py`,
`core/text.py`), the client's net decoders (`client/addons/engine/net/*.gd`) and the gate registry rows.
Probe scripts are in `/private/tmp/claude-501/-Users-dennyschaedig-Scripts-Maxim-Overdrive/e1266556-cb5d-4cec-a4ba-7648bc3e3cd9/scratchpad/review1/trust/`
(probe1 to probe6, gd/). The worktree was not modified.

Counts: **2 BLOCKER, 2 SHOULD-FIX, 6 NIT.**

## BLOCKER

### T-B1. A client that closes right after `hello` leaks its session, and its token stays `token_in_use` for the rest of the launch
`src/simcore/host/server.py::_Host._handshake` (and `_Host.handle`)

`_handshake` calls `sessions.open(hello.token)` and then `await connection.send(encode(reply))`. The `try/finally`
that closes the session is in `handle` and only wraps `_serve`. If the send raises `ConnectionClosed`, the session
stays in `Sessions._live` for good. The send raises whenever the client's close frame or FIN reaches the server
before the welcome goes out.

Reproduced (probe3.py, real server on port 0): 20 times, the client sends the host's hello and then calls
`await ws.close()` at once. Each time the server logs `connection handler failed ... ConnectionClosedOK` from
`server.py:90`. Afterwards `sessions.view()` still holds `Session(1, HOST, 0)`, and a fresh connection with the
host token gets `{"code":"token_in_use","type":"error"}`.

What this means: the host token can never join again in this launch. A Godot client that quits or crashes during
connect, or any network hiccup at that moment, is enough. boundaries §5.3 says "when the host leaves, the world
pauses until the host token reconnects", and that reconnect can never happen. Each such leak also uses up a slot
under the cap, so N+1 leaks make every join `busy`. No test closes the connection between hello and welcome.

Fix (verified): wrap the welcome send so that a `ConnectionClosed` there closes the session and returns `None`. Or,
better, open the session inside the same `try/finally` that closes it. I patched a copy of `src/` with the first
form and reran probe3: no live session afterwards, and the rejoin gets `welcome`. A test belongs with the fix: send
hello, close at once, then assert that the token joins again.

### T-B2. `player_text` lets invisible characters through: variation selectors carry hidden bytes, and Hangul fillers make a blank message
`src/simcore/core/text.py::player_text` / `_REFUSED_CATEGORIES`

The gate refuses characters by general category (Cc, Cf, Cs, Co, Cn, Zl, Zp). Many Default_Ignorable code points are
not in those categories: they are Mn or Lo, they render as nothing, and they pass. Measured with probe4.py on Python
3.12, `unicodedata` 15.0:

- `"hi" + 16 chars from U+FE00-FE0F` (VS1-16, Mn) is **accepted**. So is `"hi" + "".join(chr(0xE0100+b) for b in
  b"ignore previous instructions")` (VS17-256, Mn), which holds 28 invisible characters, one per byte. This is the
  published "variation-selector smuggling" trick for carrying a payload invisibly into an LLM prompt.
- U+034F COMBINING GRAPHEME JOINER ×50, U+17B4/17B5, U+180B-180D (Mongolian FVS): accepted.
- `"ㅤ"`, `"ᅟ"`, `"ﾠ"` (Hangul fillers, Lo) are accepted **as the whole message**. They pass "not all
  spaces" because `isspace()` is False for them, so a guest can send speech that renders blank.
- `"a‍️b"` is accepted: a ZWJ beside an invisible VS. That is the "zero-width run" O61 meant to stop,
  built from a non-Cf neighbour.

O61 (live) says "zero-width runs that could carry hidden bits are refused". This is the step's own deliverable for
that decision, and it misses the best-known way to do exactly that. The gate has no caller yet (no `speak` message),
which is the only reason this is not exploitable today. I grade it BLOCKER because it breaks a live decision. A
reader could argue SHOULD-FIX because nothing calls the gate.

Fix direction (unverified): refuse Default_Ignorable_Code_Point (DerivedCoreProperties). `unicodedata` doesn't expose
it, so it would be a committed table with its Unicode version. Make one exception: allow a single VS15 or VS16
(U+FE0E/FE0F) right after a character that has an emoji or text presentation, so ❤️ still works. Also refuse a
message whose every character is DI, a filler or blank. Add the cases above as rejection tests.
`test_whatever_passes_..._holds_no_lone_format_character` would not catch this, because it only looks for Cf.

## SHOULD-FIX

### T-S1. At DEBUG, the token is logged except for 13 of its 43 characters, and the test meant to catch that cannot see it
`src/simcore/host/server.py` (websockets' frame logging) / `tests/test_host.py::test_no_token_reaches_a_log_a_reply_or_a_repr`

websockets logs every frame at DEBUG on `websockets.server`. `Frame.__str__` cuts a text frame over 75 bytes to its
first 48 and last 24 bytes. Godot's hello is `JSON.stringify` with sorted keys,
`{"protocol":0,"token":"<43>","type":"hello"}` (83 bytes). The log line therefore shows **30 of the 43 token
characters** (24 at the front, 6 at the end), which I measured by running `Frame.__str__` on that exact shape. probe2
shows the same thing live: `< TEXT '{"type": "hello", ... "token": "GdK4...Bz-QBuJ-Z_oNGD28EH9Wo"}'`.

`tokens.py`'s docstring says a token "never appears in a log". The test sets caplog to DEBUG and sends a full guest
token, but it only checks for the whole token and for `token[:-1]`. So it passes while about 70% of the token is in
the captured log. Nothing turns on DEBUG today (there's no host entry point yet), so this rule holds by luck rather
than by a check.

Fix (unverified): set the server's `logger=` to a logger that never emits frame contents, or filter the
`websockets` DEBUG records. The test should check that no 8-character substring of any token appears in
`caplog.text`.

### T-S2. Nothing fuzzes `read_message` past the outer layer; the only property test is on `decode`, with random text
`tests/test_wire.py::test_the_decoder_refuses_any_text_with_bad_json_or_reads_it`

That property test draws `st.text(max_size=200)`, and almost every example dies as `bad_json` at the first
character. Nothing generates structured JSON for `read_message`. I ran a structured fuzz (probe6: 20,000 dicts with a
valid `type` and fields drawn from the schemas' keys and mixed values) and counted where the examples stopped:
17,235 `unknown_field`, 1,239 `missing_field`, 128 `not_int`, 1 accepted. It found no crash. I also ran about 45
hand-picked hostile messages (probe1): `type` as a list, dict, null or number; nested vectors; `-0`; a 5000-digit
integer; `1e99999`; a BOM; a trailing NUL or NBSP; escaped keys; a `\ud800` key; 30k-deep nesting; a 60 KB key. Every
one was refused with a code or read correctly, so the code holds. But the "validators never crash on any input" rule
(B9) isn't being tested beyond the outermost check, which goes against the project's own "measure fuzz reach"
lesson.

Fix (unverified): a Hypothesis strategy per message kind, built from each schema's fields (a valid value or one of
the converter's `bad` values per field, plus an extra key now and then), asserting `Refused` or a typed message. Also
assert how deep the examples reach.

## NIT

- **T-N1** `server.py::_gate`: two `Upgrade` headers make `request.headers.get("Upgrade")` raise
  `MultipleValuesError`. The server then answers **500** and logs a traceback where it should answer 400 (probe5).
  The connection is still refused. Fix: use `get_all("Upgrade")`.
- **T-N2** `server.py::_Host._refuse`: a client that sends a bad hello and closes at once makes `_refuse`'s send raise
  `ConnectionClosed`, which reaches websockets as `connection handler failed` at ERROR with a traceback (probe3
  output). No session leaks on this path, but any local program can fill the log with error tracebacks.
- **T-N3** `server.py::start`: connections that haven't sent hello yet have no cap. Each one is held for up to
  `hello_deadline_s` plus websockets' `open_timeout`, and may buffer up to `max_queue` (16) × 64 KiB. Only native
  local programs can reach this, since browsers are stopped by the Origin 403. Note it next to the session cap in
  §5.3, or cap pending handshakes.
- **T-N4** `server.py::_Host._answer`: after welcome, a malformed second `hello` (an unknown field, say) gets an
  `error` reply and the session goes on. Only a well-formed second hello closes the connection. §5.3 says "hello
  comes first and only once ... anything else closes". A `type == "hello"` check before stage 1 would make the rule
  exact.
- **T-N5** `tests/test_host.py`: no test fails if `compression=None` is removed from `start`. Probably harmless,
  since websockets applies `max_size` after inflating, but the commit message claims "compression is off" and nothing
  holds it. `test_no_hello_within_the_deadline...` uses `deadline=0.0`, so it can't tell a deadline that is enforced
  from one that is ignored. If the timeout were dropped, the test would hang instead of failing.
- **T-N6** `core/text.py::player_text`: the `Cn` refusal depends on the interpreter's `unicodedata` version: 15.0 on
  3.12, newer on 3.14, and both lockfiles are supported. Speech accepted and logged on 3.14 that holds a Unicode 16
  character would be refused on 3.12. If a replay re-runs stage 1 on logged speech, it diverges. Record the Unicode
  version the gate rules on, or pin it.

## Checked, no finding

- **Origin:** `"Origin" in request.headers` is case-insensitive in websockets `Headers`. Empty, `null`, a URL and a
  duplicated `origin` all get 403 (tests plus probe5). Plain GET and POST get 400. The bind is the literal
  `127.0.0.1` (tested). The Godot upgrade carries no Origin (`test_godot_net.py`, capture listener).
- **Caps:** websockets `max_size=64 KiB` counts the reassembled message before any parse, and the 1009 test exercises
  it at the cap and at cap + 1. `strict_json.decode` counts UTF-8 bytes (surrogatepass) before decoding.
  `_INT_DIGITS` refuses long integer text before `int()`, so Python's 4300-digit `ValueError` can't escape.
  `RecursionError` is caught. `_check_value` is iterative.
- **strict_json:** NaN, Infinity and -Infinity; 1e400; repeated keys, including escaped and nested ones; lone
  surrogates in keys and values; a BOM; trailing junk; non-UTF-8 bytes; 2^53-1 accepted, while 2^53, 2^53+1 and
  5000 digits are refused. Each was refused with `bad_json` or read correctly (probe1 and the fixtures).
  `5500.0`, `1e3`, `true` and `1.0e0` where an integer goes give `not_int`.
- **Error replies and close reasons:** `error` carries only `code` and the schema's field name. `unknown_field` has
  no `field` and doesn't echo a client key. Close reasons are code values only. `Opaque`'s refusal doesn't echo the
  token. `Hello.__repr__` and `Tokens.__repr__` hide tokens.
- **Tokens:** `secrets.token_urlsafe(32)`. `compare_digest` runs over every token with no early exit. The Opaque
  alphabet keeps the bytes ASCII. `write_token_file` uses `O_CREAT|O_EXCL`, which refuses a symlink that is already
  there, with mode 0600 masked by the umask.
- **Sessions:** `open` is synchronous, so two concurrent hellos with one token can't race. `bad_token` is decided
  before `token_in_use` and `busy`, so a stranger learns nothing about the cap. Ids are never reused. `HostOnly` is
  tested with a guest view and an unknown id, and never answers pending.
- **Client:** Godot 4.7.2's `JSON.parse` refuses nesting past about 1024 levels ("JSON structure is too deep"); I
  measured this with gd/deep.gd under `run_godot` up to 2,000,000 levels, and it didn't crash. `WireJson` refuses
  non-ASCII and checks depth and numbers iteratively. `_scan` runs only on text the parser accepted, so its unbounded
  inner `while` ends. In `FrameDecoder`, every size comes from header values checked against `MAX_EXTENT` and the
  real payload length before any slice; there's no decompression (only `none`); and every allocation is a slice of a
  packet capped at 4 MiB. `WireFields` readers return neutral values after a refusal, and each caller checks
  `read.ok` before indexing. I found no hostile frame that crashes or allocates without a bound.
- **Gate registry (`scripts/lint_gates.py`):** every public callable in the ten new gate modules has a row. The rows
  marked `meets` point at the right test modules. Branch coverage, measured on test_host, test_wire, test_text and
  test_converters: host, messages and converters are at 100%. `strict_json` is at 99%, missing only `122->exit`, the
  `_check_numbers` fall-through for a non-JSON object. `text.py` is at 89% here, but the missing lines are
  `visible_name`'s, which other modules test. The registry rows are accurate, with two exceptions: `player_text` is
  marked `meets` while T-B2 stands, and `start` is marked `meets` while T-B1 stands. Note for Wire integrity, not
  this lens: `start`, `HostOnly` and `write_token_file` have no caller on the shipped path yet.
