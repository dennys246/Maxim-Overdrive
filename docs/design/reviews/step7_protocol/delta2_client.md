# Client and rendering lens: delta round 2 (fold 88d7787..cde7634)

Scope: the fold's changes to client/addons/engine/net/{wire_json,net_session,net_client,frame_decoder,wire_fields}.gd,
client/tests/net_check.gd, client/tests/unit/net/*.gd and tests/test_godot_net.py.

Method: I reviewed the committed tree, using `git archive cde7634` into `<scratchpad>/delta2/client/tree`. Every Godot
run went through `godot_check.run_godot` with HOME under `<scratchpad>/delta2/client/`. The Godot unit baseline on the
copy is `client-tests: PASS 89 tests`, and the socket baseline is `tests/test_godot_net.py` 6 passed
(`MAXIM_OVERDRIVE_GODOT=1`, worktree venv). Each mutation ran on a fresh copy of that tree
(`<scratchpad>/delta2/client/mutate.py`, `sock.sh`).

## Fold table (delta-1 findings)

| # | Status | What I checked |
|---|---|---|
| S4 buffers and close (open from round 1) | **open, part (b) only** | (a) Fixed. `test_a_frame_past_godot_s_default_buffer_reaches_the_client` sends a 393,216-byte frame through the real NetClient. I set `INBOUND_BUFFER_BYTES` to 65,535 and it went red. (c) Fixed. `test_the_client_refuses_a_welcome_of_another_catalogue_and_closes_with_its_code` asserts the server received `(1000, "bad_version")`. I disabled poll's `elif session.ended() ... peer.close` and it went red: net_check's own `_finish` close carries no reason, so the test can tell the two closes apart. (b) Still open. What Godot does at the 65th queued packet is unmeasured, and neither checklists.md step 7 nor a backlog row lists it. |
| N3 `WireFrame.index(z,y,x)` vs `CellSnapshot.index(x,y,z)` | **open** | Both are unchanged at cde7634 (wire_frame.gd:20, cell_snapshot.gd:66). The commit message doesn't mention it, and it isn't deferred. It bites at the step-7 item that has the decoder fill `CellSnapshot`. |
| N6 no f16 probe | **fixed** | base.bin now carries two `temperature_c` probes with nonzero bits (22601, 25776), and the test reads them as u16. I shifted the decoder's `temperature_c` slice by one byte (frame_decoder.gd::_frame), and both probes went red (got 59736 and 0). |
| N-SF1 signed `\u` escape | **fixed** | `_hex4` now checks the digits one by one. Both corpora now hold `signed_unicode_escape_{plus,minus}.json`. I restored `is_valid_hex_number` and it went red (signed_unicode_escape_minus). |
| N-SF2 values never compared; NUL becomes U+FFFD | **fixed** | `test_every_accepted_json_text_reads_to_the_server_s_value` compares each accepted text's code points and IEEE bits with the manifest's values. I reran my delta-1 mutations, and both now turn red: `\/` decoding to `A` (solidus_escape), and UTF-8 decoding to `?` (object, raw_utf8, raw_bom_in_key). U+0000 is refused on both sides. I removed the `cp == 0` refusal and it went red (escaped_nul). The owner should note this is the author's contract call (boundaries §9.1); the commit message says so. |
| N-N1 parser cost | **open** | Nothing is recorded in B5 (I read standards_backlog.md at cde7634). The text cap dropped to 64 KiB, which bounds text at about 170 ms worst case. The new BOM path adds a worse case: see D2-N1. |
| N-N2 over-long close reason; 1000 vs 1008 | **partly fixed; 1000 vs 1008 open** | Fixed: `session.refusal` is always code-shaped now. An error's code is held to `CODE` (I removed the check and "prose as a code" went red), and every other refusal comes from the client's own vocabulary, so `peer.close(1000, refusal)` stays under 123 bytes. Open: the client still closes a refusal with 1000. The new test pins 1000, and client_rendering §4.3 names only the host's 1008. The client's choice should be written down or changed. |
| N-N3 the engine-fact test depends on timing | **open** | It is unchanged and not deferred. |
| N-N4 stale docstring | **fixed** | wire_fields.gd's module docstring now says ints arrive as ints, and why `whole` still takes a float. |

The fold's other client claims, each checked by mutation, all turned red:

- the BOM path off, which reds `{key,kind,grid_name}_with_escaped_bom.bin`;
- `_double` replaced by `to_float`, 7 red (exponent_past_u32, zero_with_a_huge_exponent, long_fraction_and_exponent, ...);
- `_past_largest` forced false, which reds rounds_up_past_the_largest_double;
- not_int moved before the version, which reds newer_protocol_with_float, protocol_float and the session's "newer welcome";
- `_channel_rules` back inline in `_channel`, which reds raw_scale_and_{unknown_dtype,bad_name,bad_of};
- `_channel_rules` disabled, which reds optional_raw_with_scale;
- welcome's `versioned` forced false, which reds the wrong-welcome tests.

**Counts: fixed 4 (N6, N-SF1, N-SF2, N-N4); partly fixed 2 (S4: (a) and (c) fixed, (b) open; N-N2: the reason length
fixed, the close code open); open 3 (N3, N-N1, N-N3); deferred 0; rejected 0.**

## New findings (the fold's diff)

### D2-SF1 (SHOULD-FIX). A server message whose `type` isn't a string raises a SCRIPT ERROR and ends nothing
`client/addons/engine/net/net_session.gd::on_text`. The fold added
`var versioned: bool = fields.get("type") == "welcome"`. In Godot 4.7.2, `==` between a String and an int, bool, Array
or Dictionary is a runtime error, not `false`. Only `null` compares cleanly. I measured it on the committed code:

| text | refusal | engine |
|---|---|---|
| `{"type":5}` | `""` (not ended) | `SCRIPT ERROR: Invalid operands 'int' and 'String' in operator '=='` |
| `{"type":true}` / `[1]` / `{}` | `""` | the same error for bool, Array and Dictionary |
| `{"type":null}` | `unknown_kind` | none |

How it fails: `on_text` aborts before `end`, so the session stays live with no refusal. NetClient keeps reading, and
the next message is handled as if nothing had arrived. This is the same class as round-1 S2, which the fold of round 1
fixed: hostile input causes a script error and the refusal is lost. At 88d7787 the `match` in the same function took
these values without error, so the fold introduced this. No test sends a non-string `type`.

Proposed fix (**verified**): `var kind: Variant = fields.get("type")` and then
`var versioned: bool = kind is String and kind == "welcome"`. On a copy, all four inputs then give `unknown_kind`
with no engine error, welcome and error still behave as before, and the unit suite stays `PASS 89 tests`. The test
to add: `{"type":5}` and `{"type":true}` in `test_the_server_s_other_messages`, each expecting `unknown_kind`.

### D2-SF2 (SHOULD-FIX). NetClient's coded-close-reason rule has no test that can fail
`client/addons/engine/net/net_client.gd::poll`, the line `var coded: bool = NetSession.CODE.search(reason) != null`.
This is a behaviour change: a peer's close reason that isn't code-shaped becomes `closed <code>`. I reverted it to the
old `not reason.is_empty()` and `tests/test_godot_net.py` stayed green (6 passed), so the rule ships unguarded.
How it fails: a later edit drops the rule, and a server or proxy closing with prose ("Going away", a 120-byte message)
puts that prose into `session.refusal` and every UI that shows it, with no test going red. Proposed test: a `_against`
server that closes with code 1008 and reason `"Not a code!"`, where the client should print `refused closed 1008`.
(Unverified.)

### NITs
- **D2-N1 The BOM path costs about 10x on hostile text (measured).** `wire_json.gd::_decoded` builds a BOM-led string
  with `out += String.chr(cp)` for each code point. Best of 3 on 4.7.2, 64 KiB texts: a plain string takes 43 ms, an
  escaped-BOM string 493 ms, a raw-BOM string 433 ms, and NetSession.on_text of the escaped one 417 ms. A frame header
  can be 64 KiB too. Every such input is refused (no wire name holds U+FEFF), so it costs one hitch of about 0.5 s
  per session. That is the new worst case for N-N1, above the 172 ms I measured in delta 1 at 64 KiB. A cheaper form:
  count the k leading BOMs, then prepend k copies of U+FEFF to `utf8.slice(3k).get_string_from_utf8()`. I measured
  that `get_string_from_utf8` drops exactly one leading BOM, and `[BOM, BOM, a]` keeps one. The rest of this form is
  unverified.
- **D2-N2 `MAX_TEXT_BYTES` is a copied server limit with no check.** Its comment says it is "the server's own inbound
  cap". `test_the_client_s_limits_are_the_server_s` doesn't hold it, and the manifest doesn't carry it. I set it to
  256 KiB and the suite stayed green (PASS 89).
- **D2-N3 The socket wait spins.** `tests/test_godot_net.py::_until` loops `await asyncio.sleep(0)` until the handler
  records the close. That spins a core for as long as Godot takes to close, up to `TIMEOUT_S`. An `asyncio.Event` set
  in `handle` would wait without polling.

## Checked, no finding
- **Typing under 4.7.2:** the copy loads with warnings as errors (the suite needs that). Its `static var CODE`
  initialises at class load, and `\z` refuses `"bad_token\n"` (measured).
- **The ordering of `server_rules`:** the version first, then not_int, for frames and for welcome. An error message
  isn't versioned, which matches the server writing `protocol` only in welcome and frames.
- **The new socket tests:** the server binds port 0 on `BIND`. The token reaches Godot by environment variable. The
  frame is built by the server's own `encode_cells`, so the test exercises the real encoder against the real decoder.
- **`_double` with a 64 KiB-digit literal:** 26 ms, with no superlinear term.
