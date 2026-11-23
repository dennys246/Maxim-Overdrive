# Trust boundary, delta round 1: phase1/protocol (8beb6af ... 0c7e6e6, plus 88d7787)

Lens: Trust boundary. I reran the round-1 probes against the folded server and attacked what the fold added: the
GDScript parser, the close-reason path, the quiet logger and hello's version-first read. Probes are in
`<scratchpad>/delta1/trust/`: `srv.py` and `srv2.py` (server), `probe4.py` and `text2.py` (guest text), `probe5.py`
(headers), `pyjson.py`, `client/probe.gd` (WireJson), `longreason.py` with `client/longreason.gd` (close reason) and
`mutate.py` (mutations in a scratch copy of the tree). The worktree was not modified. Godot ran only through
`run_godot`/`godot_env`, with HOME inside the scratch directory and a copy of `client/`.

Counts: fold table **7 fixed, 3 open, 0 deferred, 0 rejected**. New: **1 BLOCKER, 2 SHOULD-FIX, 6 NIT.**

## Fold table (status read from the tree)

| Id | Status | What I checked |
|---|---|---|
| T-B1 session leak | **fixed** | `_Host.handle` opens the session and closes it in one `try/finally`, with the welcome send inside. Live run: 20 hello-then-close and 20 hello-then-abort clients left `SessionView(sessions=())`, and the rejoin got `welcome`. Mutation (close moved out of the `finally`): `test_a_client_that_leaves_before_reading_welcome_frees_its_token` went **red**. |
| T-B2 invisible characters | **fixed** (for every case in round 1; see the new BLOCKER D-B1) | Rerunning probe4, every case from round 1 is now refused: VS1-16 and VS17-256 payloads, CGJ, the Hangul fillers, Khmer, the Mongolian FVS, ZWJ then VS, and braille-blank-only text. I checked the `DEFAULT_IGNORABLE` table against Unicode 16's DI list range by range and found no gap. Mutations that dropped the DI check, the blank check or the EMOJI base check each turned `tests/test_text.py` **red**. |
| T-S1 token at DEBUG | **fixed** | `_QuietLogger` passed as `logger=`. Live, with the root logger at DEBUG and the test's client records filtered out, the server wrote 149 INFO lines and **0** 8-character token substrings. Removing `logger=` turned the test **red**, and so did making `isEnabledFor` pass DEBUG through. |
| T-S2 structured fuzz | **fixed** | `test_stage_1_never_crashes_on_a_real_message_with_one_field_changed` changes one field of a real message. The reach (10 of 400 stop at `bad_json`) appears only in the commit message, and no test asserts it (NIT D-N5). |
| T-N1 duplicate `Upgrade` → 500 | **open** | `_gate` still calls `request.headers.get("Upgrade", "")`. probe5: `HTTP/1.1 500` plus a `MultipleValuesError` traceback. It is not deferred anywhere. |
| T-N2 refusal send raises on a gone client | **fixed** | `handle` catches `ConnectionClosed` around the whole life. Live: bad hello then close (×5) and bad hello then abort (×5) logged nothing above INFO. New test `test_a_client_that_leaves_mid_handshake_is_not_logged_as_a_server_error`. |
| T-N3 no cap on pending handshakes | **open** | Neither a cap nor a note in boundaries §5.3, and no checklist or backlog row. |
| T-N4 malformed second hello | **open** | A well-formed second hello now ends with `hello_first`. A malformed one does not: live, after `welcome`, `{"type":"hello","protocol":0,"token":"zz","extra":1}` got `{"code":"unknown_field"}` and the connection stayed open (my receive timed out with no close). A second hello with `protocol: 1` does the same. That breaks the text the fold just wrote into boundaries §5.3: "`hello` comes first and only once ... anything else ends it (`hello_first`)". Fix (unverified): in `_answer`, check `type == "hello"` on the decoded mapping before stage 1. |
| T-N5 compression / deadline untested | **fixed** | `test_the_server_negotiates_no_compression` checks that a deflate offer gets no extension. Every wait is bounded by `WAIT_S`, so a deadline that was ignored now fails instead of hanging. |
| T-N6 `Cn` depends on the Unicode version | **fixed** (documented) | `player_text`'s docstring records 15.0 on 3.12 and 16.0 on 3.14, and that replay reads back the kept text and never re-checks it. Only review holds "never re-checked". I accept this. |

## New findings

### D-B1 (BLOCKER). An invisible Mn character outside DI carries a hidden run, and a message made only of it passes "draws something"
`src/simcore/core/text.py::_visible` / `player_text`

U+16FE4 KHITAN SMALL SCRIPT FILLER is Mn and zero-width, and it is not Default_Ignorable, so `_visible` counts it as
drawn. Measured on 3.12:
- `"\U00016FE4"` alone is **accepted**. O65 says "a message that draws nothing ... is refused".
- `"hi" + "".join(K + (ZWNJ if bit else ZWJ) for each bit of b"ignore all previous rules") + K + "!"` (401
  invisible characters, 25 bytes hidden) is **accepted** at `max_chars=500`. Each joiner sits between two
  "visible" fillers, so O61's joiner rule passes it. At the real cap of 200 that is still about 12 hidden bytes in a
  run that renders as nothing. O61 (live) says "zero-width runs that could carry hidden bits are refused".
- The same sweep found other characters that draw nothing and count as drawn: U+13441 and U+13442 (EGYPTIAN
  HIEROGLYPH FULL and HALF BLANK, which `visible_name` already refuses by name) and U+1D159 MUSICAL SYMBOL NULL
  NOTEHEAD.

The grade follows round 1's T-B2: it breaks a live ruling, and no caller is the only reason it can't be exploited
today. A reader could argue SHOULD-FIX.

Fix direction (unverified): reuse the name rule `visible_name` already has (`_BLANK_WORDS`). Refuse U+16FE4, or any
Mn/Lo whose name says FILLER. Treat BLANK-named characters as drawing nothing, as `_BLANK` treats U+2800. Add the
cases above as rejection tests.

### D-S1 (SHOULD-FIX). WireJson accepts `\u` escapes with a sign, and a negative one skips the surrogate check (O63 broken)
`client/addons/engine/net/wire_json.gd::_hex4`

Godot's `String.is_valid_hex_number()` accepts a leading `+` or `-`. Measured on 4.7.2:
- `{"a":"\u+041"}`, `{"a":"\u-041"}` and `{"a":"\u-800"}` are all **accepted** by `parse_server`, each with an engine
  `ERROR`/"Unicode parsing error" and a value of U+FFFD. Python's `strict_json.decode` gives `bad_json` for all three.
- `\u-800` gives `cp = -0x800`, which passes both surrogate range tests.

O63's contract is that one hostile corpus is "judged alike by both decoders, code for code", and the corpus has no
escape with a sign. Fix (**verified**): check that each of the four bytes is `[0-9A-Fa-f]` before `hex_to_int`. In a
copy of `client/`, all four cases (with `\u0x41`) became `bad_json`, and `res://tests/run.gd` printed
`client-tests: PASS 86 tests`. Add `\u+041` and `\u-800` to `client/tests/fixtures/wire/json/` so the corpus holds them.

### D-S2 (SHOULD-FIX). The peer's error code and close reason become the refusal verbatim, and one over 123 bytes leaves the client stuck in CLOSING
`client/addons/engine/net/net_session.gd::on_text` ("error"), `net_client.gd::poll`

`on_text` takes any non-empty string in `error.code` as `refusal`, and `poll` takes `get_close_reason()` as it comes.
After that, `poll` calls `peer.close(1000, session.refusal)`. A WebSocket close reason is at most 123 bytes. Measured
against a listener that answers hello with `{"type":"error","code":"A"*N}`:
- N = 9 or 123: CLOSED after 21 polls, and the server sees 1000.
- N = **124**: the client stays in state 2 (CLOSING) for all 300 polls (about 3 s). It never sends a close frame,
  and the server sees 1006 only when Godot exits.

Any local program that holds the port first (the client connects to `127.0.0.1:<port>`) can put arbitrary text up to
256 KiB into the client's refusal, which the UI will show, and can leave its socket stuck half closed. The fold added
both paths (C-S2 to C-S4, A2). Fix (unverified): read `error.code` and the close reason as one of the known refusal
codes (a list the manifest can share with `RefusalCode`), anything else as `bad_shape`, and close only with a known
code.

### NITs
- **D-N1** `wire_json.gd::_string`: `\u0000` decodes to U+FFFD with an engine error, while Python keeps NUL. So
  `{"a\u0000":1,"a�":2}` is a repeated key in Godot (`bad_json`) and two keys in Python. The `escaped_nul`
  fixture compares only the outcome, never the value. Refusing `\u0000` on both sides, or comparing decoded values,
  would close it.
- **D-N2** `wire_json.gd::_real`: `1.7976931348623158e308` is finite in Python (then `not_int`) and `bad_json` in
  Godot (`to_float` rounds it to inf). Both refuse, with different codes, so O63's code-for-code claim misses this
  boundary. Add it to the corpus.
- **D-N3** `net_session.gd::MAX_TEXT_BYTES`: WireJson takes **1.2-1.4 s** on a 256 KiB `[0,0,...]` text message
  (0.1-0.9 s on the other shapes I tried) on the client's main thread. Each such message from a hostile peer freezes
  the frame loop. The server's real text messages are under 2 KiB. A cap near 16 KiB would bound the stall at about
  80 ms.
- **D-N4** `core/text_tables.py::EMOJI`: this is Unicode's `Emoji` property, not `emoji-variation-sequences.txt`.
  O65 says "a character with text and emoji forms", yet U+1F600, the regional indicators and the skin-tone modifiers
  each take a VS16. Under O61 and O65 as ruled, VS15, VS16 or nothing after each digit, and ZWNJ, ZWJ or nothing
  between any two Latin letters, both pass (measured), so about 1.6 bits per visible character travel unseen. The
  rulings sanction this, so it is the owner's call. I flag it because it falls short of O65's stated aim.
- **D-N5** `tests/test_wire.py::test_stage_1_never_crashes_...`: the reach (how many examples get past `decode`)
  appears only in the commit message. No test asserts it, so a strategy change that collapses the reach stays green.
- **D-N6** `messages.py::_check_protocol`: `bad_version` carries `field="protocol"` for a whole-number version but no
  field for a float, a missing or a non-number one. Live: `protocol:1` gives `{"code":"bad_version","field":"protocol"}`,
  and `protocol:0.0` gives `{"code":"bad_version"}`. Harmless, but the error shape is inconsistent.

## Checked, no finding
- **Version-first read:** none of 15 hostile hellos (protocol `1`+new field, `0.0`, missing, `"0"`, `-1`, `true`,
  `null`, `[0]`, 23 digits, `1.79e308`, a repeated `protocol`, and a type of `"Hello"` or `["hello"]`) crashed. Each
  got an error and a 1008 close whose reason equals the code. A long token with `protocol:1` gets `bad_version`.
  Removing `_check_protocol`'s call turned `test_host.py` **red**.
- **Close reason (server):** every refusal I triggered (deadline, binary first, non-hello first, bad JSON, `[]`)
  closes with 1008 and reason = code. Dropping the reason turned the test **red**. Every server code fits 123 bytes.
- **Quiet logger:** websockets routes every frame log through the adapter's `isEnabledFor`, and the only output was
  INFO open and close lines. One asyncio DEBUG line came from the event loop and holds no content.
- **WireJson:** depth 32 is accepted and 33 refused, with recursion bounded by `MAX_DEPTH`. Overlong, surrogate and
  past-U+10FFFF UTF-8 are refused. Truncated sequences are length-checked before indexing. The 4-byte UTF-8, escape,
  surrogate-pair, space, many-keys and long-fraction or long-exponent inputs at the 256 KiB cap all finished in
  0.1-0.9 s, with no crash and no unbounded allocation (the input cap bounds everything). Frame headers go through
  `parse` capped at 64 KiB, after the ASCII check.
- **Sessions:** the welcome send and `_serve` share the `finally`, and cancellation (`server.close()`) runs it.
  `Decision` and `Sessions(cap<1)` refuse what can't be.
