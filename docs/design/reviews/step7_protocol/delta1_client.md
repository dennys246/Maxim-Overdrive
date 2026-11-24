# Client and rendering lens: delta round 1 (fold 8beb6af..0c7e6e6, plus 88d7787)

Scope: client/addons/engine/net/{wire_json,net_session,net_client,frame_decoder,wire_fields,wire_catalogue}.gd,
client/tests/net_check.gd, client/tests/unit/net/*.gd, tests/test_godot_net.py.

Method: read every file at 88d7787. All Godot runs went through `godot_check.run_godot` with HOME under
`<scratchpad>/delta1/client/home`. Probes ran in a scratch project holding a copy of `net/*.gd`, which I checked is
byte-identical to 88d7787. Mutations ran on a `git archive 88d7787 client` copy, with the real `res://tests/run.gd`
(baseline: `client-tests: PASS 86 tests`). Note: during this review the worktree gained uncommitted edits to
wire_json.gd, net_session.gd, frame_decoder.gd and the manifest. Everything below is about the committed tree, not
those edits.

## Fold table (round-1 findings)

| # | Status | What I checked |
|---|---|---|
| S1 WireJson laxer than strict_json | **fixed** | WireJson is now its own RFC 8259 parser over bytes. I made three mutations, and each turned red: raw control characters accepted (raw_tab, raw_newline, nul_in_string fail), the leading-zero branch removed (leading_zero.json and header_leading_zero.bin fail), and `}` accepted after a comma (trailing_comma_object.json and header_trailing_comma.bin fail). New gaps in the same parser are N-SF1 and N-SF2 below. |
| S2 non-numeric `protocol` raised a SCRIPT ERROR | **fixed** | NetSession reads welcome through `WireFields.version`, `whole(session)`, `choice(role)` and `digest(catalogue_hash)`, and compares the hash with the build's. I reduced `version`'s type check to `value == null` and the test went red (`"protocol":"0"` gave a SCRIPT ERROR and an empty refusal). I removed the hash comparison and it went red too. `shape` and `build` are still not read, which I accept: nothing in the client uses them. |
| S3 refusal was last-wins | **fixed** | `NetSession.end` keeps the first refusal, and `on_text`/`on_frame` return once the session has ended. With `end` set to always assign, the test went red ("nor does the close"). With the `ended()` guard in on_text removed, it went red ("and isn't read"). The client-side close is unguarded: see S4. |
| S4 buffers and state machine unguarded | **open (partly fixed)** | Fixed: NetSession's branches are unit-tested. Removing the frame-before-welcome check turns it red. Still open, with no deferral in checklists.md step 7 or the backlog: (a) no test sends a frame over 64 KiB through a real socket, so setting `INBOUND_BUFFER_BYTES` back to 65,535 still turns nothing red (test_godot_net sends only hello, welcome and error); (b) what Godot does at the 65th queued packet is still unmeasured; (c) `NetClient.poll`'s `elif session.ended() and state == STATE_OPEN: peer.close(...)`, which the fold message claims ("the client closes after it"), runs in no test. net_check stops the moment the session ends, so deleting the close stays green. |
| N1 identity vs non-ASCII | **fixed** | Both sides now allow only printable ASCII (WireName, `WireFields.identity`). I widened the range to 0x10FFFF and the test went red (optional_name_escaped_non_ascii.bin). |
| N2 blanket not_int vs per-field codes | **fixed** | Python now applies the same blanket rule (`strict_json.integers_only` in `grammar.py:124`, after the version), so both readers give `not_int` (tick_float and scale_float fixtures). |
| N3 `WireFrame.index(z,y,x)` vs `CellSnapshot.index(x,y,z)` | **open** | Both files are unchanged. The fold message does not mention it, and it is not deferred. |
| N4 4 MiB text cap; ASCII checked twice | **fixed** | Text now has its own cap, `NetSession.MAX_TEXT_BYTES` = 256 KiB. FrameDecoder's ASCII loop is now the only ASCII check, because WireJson accepts UTF-8, so the duplicate is gone. Setting the cap to 4 MiB stays green, so the constant has no test. Measured cost: see N-N1. |
| N5 `open` didn't reset state | **fixed** | `open` makes a new `WebSocketPeer` and `NetSession` and clears `_hello_sent`. Checked by reading only: no test reconnects. |
| N6 no f16 probe | **open** | `_check_accepted` still decodes only u8 and u16, so `temperature_c` bytes are never compared. |

**Counts: fixed 7 (S1, S2, S3, N1, N2, N4, N5); open 3 (S4 in part, N3, N6); deferred 0; rejected 0.**

## New findings

### N-SF1 (SHOULD-FIX). `WireJson._hex4` accepts a signed `\u` escape, which the server refuses
`client/addons/engine/net/wire_json.gd::_hex4`. `String.is_valid_hex_number()` accepts a leading `+` or `-`
(Godot's ustring). Measured on 4.7.2 with the committed WireJson:

| input | WireJson | `strict_json.decode` |
|---|---|---|
| `["\u+041"]` | ok, value `"�"`, and the engine prints `ERROR: Invalid hexadecimal notation character "+"` from `hex_to_int` | bad_json ("Invalid \uXXXX escape") |
| `["\u-041"]` | ok, `"�"` ("Invalid unicode codepoint (ffffffbf)") | bad_json |
| `{"x\u+041":1}` | ok | bad_json |

How it fails: a header whose unknown optional grid has the name `"\u+041"` is `bad_identity_key` in Godot and
`bad_json` in Python. An unknown key spelled that way is `unknown_field` in Godot and `bad_json` in Python. O63's
contract, that one hostile corpus is "judged alike by both decoders, code for code", is broken on input the corpus
doesn't hold. Every such escape also writes an engine ERROR to the log. Proposed fix: check each of the four bytes
is in `[0-9A-Fa-f]` before calling `hex_to_int`, and add `\u+041` and `\u-041` to the shared json corpus.
(Unverified.)

### N-SF2 (SHOULD-FIX). The values of accepted JSON are never compared, and `\u0000` decodes to U+FFFD
`client/tests/unit/net/test_wire_fixtures.gd::test_every_json_text_reaches_its_manifest_outcome` and
`wire_json.gd::_escape`/`_string`.
- The test compares only accepted or refused. I made two mutations on the committed tree and **both stayed green
  (PASS 86)**: `\/` decoding to `A` instead of `/`, and every multi-byte UTF-8 sequence decoding to `?`. Whatever the
  parser builds for an accepted string is unguarded, even though solidus_escape, raw_utf8, surrogate_pair and
  escaped_nul exist to hold exactly that.
- One case where the value differs already exists. `String.chr(0)` and `get_string_from_utf8` turn NUL into U+FFFD
  (measured: `chr0 utf8 size 3`, plus a "Unexpected NUL character" engine error each time). So
  `{"a\u0000b":1,"a�b":2}` is **bad_json (a repeated key) in Godot and accepted in Python** (both measured).
  escaped_nul.json passes only because its outcome is the only thing compared.

Proposed fix: have the manifest carry the decoded value of each accepted json fixture (as canonical JSON, say),
compare it in both readers, and add the NUL/FFFD key pair. Alternatively refuse `\u0000` on both sides, if the owner
prefers. (Unverified.)

### NITs
- **N-N1 Parser cost (measured).** I timed parse on 4.7.2, best of 3, with Godot's `JSON` as the reference. The real
  1,028-byte header in base.bin takes 0.67 ms (`JSON`: 0.04 ms). A whole `FrameDecoder.decode(base.bin)` takes
  0.98 ms. At the 64 KiB header cap: a 64 KiB string 33 ms, whitespace 14 ms, `{"k":1},` objects 118 ms, `1,`
  integers 172 ms. At the 256 KiB text cap: string 161 ms, objects 332 ms, integers **887 ms** (about 5x the 64 KiB
  time for 4x the bytes, so slightly superlinear). Every caller is bounded: any refusal and any text after welcome
  ends the session, so a hostile message costs one hitch per session. A padded but valid header (whitespace is
  unbounded up to 64 KiB) costs about 14 ms on every frame. The cost that matters in practice: about 0.7 ms of
  client_rendering §8's "decode + upload ≤ 3 ms" now goes to the header alone, and §8's 1.4 to 2.4 ms measurement
  predates it. B5 has no meter yet. Record the number there. The obvious costs are an array allocated on every byte
  in `_space` (`in [0x20, ...]`), one `PackedByteArray` allocated per ASCII character in `_string`, and a Dictionary
  allocated per escape.
- **N-N2 Close with an over-long reason.** `net_client.gd::poll` closes with `session.refusal`, which can be a code
  the server chose (`error.code`, any length). I measured a 200-byte reason: `close()` moves to STATE_CLOSING, no
  close frame reaches the peer (server close code -1), and the client was still CLOSING 400 polls later. A 10-byte
  reason closes in one poll. Cap or replace the reason at 123 bytes. Separately, the client closes with 1000
  (normal) for a refusal, while the host uses 1008 (§4.3).
- **N-N3 The engine-fact test depends on timing.**
  `tests/test_godot_net.py::test_godot_drops_the_error_that_arrives_with_the_close` asserts 0 packets. That holds
  only while the host's `send(error)` and `close` land in one Godot poll. If a poll falls between the two writes
  (for example on a loaded machine), Godot holds the packet and the test reads 1. It was 8 of 8 green here. The docstring says
  a flip would mean an engine change, but it could also be scheduling.
- **N-N4 A stale docstring.** `wire_fields.gd` lines 8 and 9 still say "JSON numbers arrive as floats (§4.1)".
  WireJson now delivers ints, and floats never reach the schema (not_int). The float path in `whole` is dead.

## Checked, no finding
- **Typing under 4.7.2:** load_all and run.gd are clean at 88d7787 with warnings as errors. The Variant reads in
  wire_json (`simple[b]`, the `smallest` table) assign to typed locals with no warning. `match` on an int Variant
  works.
- **Close state machine:** after a refusal, `poll` sends `close` once (state OPEN, then CLOSING, measured), stops
  reading packets, and `end` on the later CLOSED doesn't overwrite. A server close with an empty reason gives
  `closed <code>`.
- **Depth:** `_depth` is decremented on every closing path, and a refusal ends the parse. Top-level-key attribution
  for protocol matches `integers_only` (`{"protocol":[1.0]}` gives bad_version through `version`).
- **Engine whys** are present for NetSession (pure RefCounted) and net_check's raw mode.
