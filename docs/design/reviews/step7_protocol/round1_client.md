# Client and rendering lens: phase1/protocol (origin/main aaebc1b .. HEAD 8beb6af)

Scope: client/addons/engine/net/*.gd, client/tests/net_check.gd, client/tests/unit/net/test_wire_fixtures.gd,
client/tests/unit/test_json_ints.gd, tests/test_godot_net.py. Read against client_rendering §3.1, §4.1–§4.3, §7.1,
§7.5, the step 7 checklist, and src/simcore/protocol/grammar.py and strict_json.py (the Python twins).

Method: I read every file, then ran Godot 4.7.2 probes in my own scratch project
(scratchpad/review1/client/proj, HOME in scratchpad/review1/client/home, through `godot_check.run_godot`). The project
holds a **copy** of client/addons/engine/net/*.gd and calls the real WireJson and NetClient. Nothing in the worktree
was modified.

Counts: **BLOCKER 0, SHOULD-FIX 4, NIT 6.**

---

## SHOULD-FIX

### S1. WireJson accepts JSON the server's strict decoder refuses (trailing commas, leading zeros, raw control characters)
`client/addons/engine/net/wire_json.gd::parse` (and so `FrameDecoder._header` and `NetClient._on_text`).

Defect: the header docstring says WireJson is "the defence-in-depth twin of the server's strict decoder". It adds
checks for repeated keys, number size, depth and ASCII on top of Godot's `JSON.parse`. But Godot's parser is laxer than
RFC 8259 in ways nothing else catches. I measured this on 4.7.2 against the real `WireJson.parse`:

| input | WireJson | `simcore.protocol.strict_json.decode` |
|---|---|---|
| `{"tick":007}` | ok, `{"tick": 7.0}` | bad_json ("Extra data") |
| `{"a":1,}` | ok | bad_json |
| `[1,2,]` | ok | (bad_json, same rule) |
| `{"a":"x<TAB>y"}` (raw tab) | ok | bad_json ("Invalid control character") |

Failure scenario: a frame whose header ends `..."arrays":[...],}`, or holds `"tick":007`, is **accepted** by
FrameDecoder and **refused** (bad_json) by `grammar.decode_frame`. That breaks the twin contract the manifest is meant
to hold, and the commit message's claim that the two decoders reach one outcome holds only for the committed fixtures.
`_scan` already walks every character, so it can refuse a `,` directly before `}`/`]`, a `0` followed by a digit at the
start of a number, and a byte below 0x20 inside a string. Add the three as `json` set fixtures that both readers read.
(Fix unverified.)

### S2. NetClient's version check raises a SCRIPT ERROR on a non-numeric `protocol` and leaves the client stalled
`client/addons/engine/net/net_client.gd::_on_text`, line 84: `if message.get("protocol") != float(PROTOCOL):`.

Defect: in Godot 4.7.2, `!=` between a bool or String Variant and a float is a runtime error, not `true`. I measured it:
`Invalid operands 'bool' and 'float' in operator '!='` and `'String' and 'float'`. Only `null != 0.0` evaluates (to
true). The error aborts `_on_text`, so neither `refusal` nor `welcome` is set.

Failure scenario (run on the real NetClient):
`_on_text('{"type":"welcome","protocol":true}')` prints the SCRIPT ERROR, then `refusal == ""` and `welcome == {}`.
The owner polls forever with nothing to show. net_check would sit until the test's 60 s outer timeout. This is the
version check: it exists to handle a server that isn't this build, and it fails silently on exactly that input.

Related: welcome passes through with no schema at all. `{"type":"welcome","protocol":0}` is accepted as a complete
welcome (measured). `catalogue_hash` is then read through `str()`, so a missing hash turns into `"<null>"` and every
frame is refused bad_version. The frame header gets a closed schema through WireFields; welcome gets none. Read
`protocol` with `WireFields.whole`-style type checks before comparing it, and give welcome the keys the client
depends on (`catalogue_hash` through `WireFields.digest`, `role`, `shape`, `build`). (Fix unverified.)

### S3. NetClient's `refusal` is last-wins, so the cause is overwritten by its consequences
`client/addons/engine/net/net_client.gd::_on_text`, `::_on_frame`.

Defect: WireRead's docstring says the first refusal wins, which is the right rule. NetClient does the opposite: every
branch assigns `refusal = ...`. NetClient also never closes the socket after it refuses something, so traffic keeps
arriving and keeps overwriting the cause.

Failure scenario (run on the real NetClient): a welcome with `protocol: 1` sets `refusal = "bad_version"`. The next
binary frame arrives while `welcome` is still empty and sets `refusal = "bad_shape"`. The version error, the one
§7.5 says to show ("refused loudly, with the reason shown"), is lost. The same happens to a server `error` followed by
anything else.

net_check stops at the first refusal, so no test can see this. Either keep the first refusal, or make a refusal
terminal (close the peer with a code). (Fix unverified.)

### S4. The §4.3 buffer settings and most of NetClient's state machine are guarded by nothing
`client/addons/engine/net/net_client.gd::INBOUND_BUFFER_BYTES`, `::MAX_QUEUED_PACKETS`, `::_on_text`, `::_on_frame`.

Defect:
- **Buffers.** No test reaches the reason the buffers are set. The commit says 4 MiB is needed "because the default
  of 65,535 bytes is smaller than a cell frame". No test sends a frame over 64 KiB through NetClient, so setting
  `INBOUND_BUFFER_BYTES` back to 65535 turns nothing red. Searched: no test references either constant, `_on_frame`, or
  a binary packet over a real socket.
- **Falling behind.** "64 queued packets, so it notices when it falls behind" has no code behind it. Nothing in
  NetClient reads, reports or tests an overflow. What Godot does at the 65th packet (drop it, or close and with which
  code) is unmeasured.
- **The state machine.** The only Godot tests are three end-to-end runs: an Origin capture, a welcome, and a close
  reason. None of these branches has a test: `error` text read as text, frame before welcome, `unknown_kind`, a
  welcome with the wrong version, `not_int` in a text message, a frame refusal, and a frame accepted into
  `last_frame`. Python diff coverage does not see GDScript.

All of these can be unit-tested by calling `_on_text`/`_on_frame` directly. I did exactly that in a probe. The buffer
case needs one host-side test that sends a v0 frame of about 1.4 MB and checks `last_frame`. Under "prove a guard by
deleting it", the buffer constants are currently unguarded. (Fix unverified.)

---

## NIT

- **N1** `wire_fields.gd::identity`. The comment says "A header is ASCII, so printable is 0x20 to 0x7E". That is not
  true: the header's *bytes* are ASCII, but a `é` escape decodes to é. Measured: WireJson returns `"é"`,
  `strict_json` returns `'é'`, and `checks.identity_key("é")` accepts it, while `WireFields.identity` refuses it
  (bad_identity_key). Python's `str.strip()` and `isprintable()` also differ from `strip_edges()` outside ASCII. The
  server writes ASCII names today, so the only effect is a divergence on an optional channel or grid a newer server
  might add. Either refuse non-ASCII in decoded strings in both readers, or match Python's rule here.
- **N2** `frame_decoder.gd::_header`. Any non-integer literal anywhere in the header is refused `not_int` before the
  closed schema is read. Python reads the float and refuses per field: `"kind": 1.5` gives unknown_kind,
  `"grids": 1.0` gives bad_shape, and an unknown key `"x": 1.5` gives unknown_field, while Godot gives not_int for all
  three. The outcome (refused) matches but the code differs, against the docstring's "its refusal codes". Only
  `tick_float`/`tick_1e3` (an int field) are fixtures.
- **N3** `wire_frame.gd::index(z, y, x)` against `render/cell_snapshot.gd::index(x, y, z)`. The two classes use the
  same formula with opposite argument orders. The checklist defers filling CellSnapshot from WireFrame (and v0 lacks
  CellSnapshot's required `surface_glow`/`burning`, so that fill is not possible yet). When it lands, swapped
  arguments are silently wrong on every non-cubic grid. Pick one order now.
- **N4** `net_client.gd::_on_text` passes `INBOUND_BUFFER_BYTES` (4 MiB) as the text cap. WireJson walks text
  character by character in GDScript twice (the ASCII loop and `_scan`), on the main thread inside `_process`. A
  multi-MB text message would hitch frames. Server text messages are small, so give text its own cap matching the
  server's outbound bound. `FrameDecoder._header` also checks ASCII twice (its own loop, then WireJson's).
- **N5** `net_client.gd::open` resets none of `_hello_sent`, `welcome`, `refusal`, `last_frame`. Calling `open` again
  to reconnect (WT-S6, "a snapshot after a reconnect") would never send hello, and the host's deadline would close
  it. Not on the shipped path yet.
- **N6** `test_wire_fixtures.gd::_check_accepted` probes only u8 and u16 values. The f16 `temperature_c` bytes are
  never compared, so a slice offset bug confined to the last array would show only through the size check. Add one
  f16 probe (`decode_half`).

---

## Checked, no finding

- **Typing:** every var, parameter and return is typed, `for x: T in` is used throughout, and typed arrays and
  dictionaries are used where the shape is known. Header internals are untyped `Dictionary` of Variants, which is
  acceptable for a parse tree. I confirmed `Array[int] == [1, 1]` is true on 4.7.2, so `_channel`'s raw check and
  `_same_channel` compare by content. `match` on a non-String Variant against String patterns falls through without
  error (measured). FrameDecoder's other comparisons only run on values WireFields has already typed.
- **Floats from JSON:** `whole()` refuses bool first and accepts float or int. WireJson refuses magnitudes ≥ 2^53 and
  lists point and exponent literals, so `int(f)` is exact. `-0` reads as 0 in both readers. `protocol` is checked
  before the blanket not_int, so 1.0 and 1e0 get bad_version, and true is not a float.
- **PackedByteArray bounds:** `decode_u32(0)` runs only after `size() >= 4`. The header slice is bounded by
  `length <= size - 4`. `_layout` proves the arrays tile the payload exactly before `_frame` slices it. Products stay
  far below 2^63 (65535³ × 4; 64 arrays × 2^55). Duplicate grid and table names and a duplicate taken channel are
  refused.
- **Check order** against grammar.py: checks 1 to 6 have the same order and codes, ignored containers are recorded in
  the same order, and arrays of ignored containers are skipped before the channel rules, as in Python.
- **No feedback into the world:** NetClient sends only hello (protocol int, token). No clock, position or
  derived value goes out. The token comes from env or a file, never argv (§7.5). `handshake_headers` is never set, and
  the raw-listener test asserts an `upgrade` header was captured, so its "no origin" assertion can fail.
- **Close handling:** `poll` returns on STATE_CLOSED and reads the close reason only when nothing earlier set
  `refusal`. I did not re-measure the commit's claim that a text packet in the same poll as the close is unavailable.
  The code does not depend on it, because it reads the reason. STATE_CONNECTING and STATE_CLOSING need no handling
  beyond polling. A failed `send_text` is retried and reported.
- **§4.1 and §7 delivery:** the decoder hands over raw per-channel `PackedByteArray`s in [nz, ny, nx] x-fastest order
  (the asymmetric fixture checks it), which matches "one Image per z-slice". The step 7 checklist explicitly defers
  filling `CellSnapshot`, the `regions_version` check against the region map, and a scene owning NetClient.
  The tree location (`net/` rather than §7.1's `protocol/`) is named in CLAUDE.md's layout.
- **Engine whys:** present for NetClient (RefCounted polled per `_process`, WebSocketPeer), WireJson (RefCounted
  statics) and net_check (a SceneTree as its own main loop).
- **Tests:** test_godot_net binds port 0, takes Godot through `run_godot` with HOME in tmp, puts the token in env,
  and checks error_findings. test_json_ints changes only its comment.
