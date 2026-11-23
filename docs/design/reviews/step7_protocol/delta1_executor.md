# Executor delta review: step 7 fold (8beb6af..0c7e6e6, plus 88d7787)

Lens: Executor. I read the fold's diff and checked it against the committed tree at 88d7787. My scratch copy is a
`git archive HEAD` at `<scratchpad>/delta1/executor/py`, and Python runs there with PYTHONPATH pointed at it. Godot runs
on copies of that copy's `client/` through `godot_check.run_godot`, with HOME inside the scratch directory. I wrote
nothing to the worktree.

**Caution:** during this round the worktree picked up uncommitted edits to `wire_json.gd`, `frame_decoder.gd`,
`net_session.gd`, the manifest, server.py, and an untracked `newer_protocol_with_float.bin`. That is the author's next
fold. I did not review those edits. Everything below is measured on the committed tree. I reran my two Godot probes
on HEAD's client, and both runs gave the same results.

Baseline: the Python modules I touched (test_host, text, wire, converters, formats) pass 1208 with 1 skipped. The
client suite passes 86 tests. test_godot_net passes 4.

## 1. Fold table (round-1 Executor findings)

| ID | Status | What I checked |
|---|---|---|
| E-B1 session leak | **fixed** | `server.py::_Host.handle` now opens the session and closes it in one `finally`, which also covers the welcome send. I moved the welcome send back out of the `try`, and `test_a_client_that_leaves_before_reading_welcome_frees_its_token` went red 5 times out of 5, after its 10 s `WAIT_S` bound. Restored, it is green in 12 of 12 reruns. The quiet-leave test is not vacuous either: changing `except ConnectionClosed` to another type turned it red 4 times out of 4. |
| E-S1 Godot JSON not strict | **fixed** for the measured rows | My six round-1 rows now agree. NUL padding, trailing comma and leading zero are fixtures, and each check is red when broken. `tick:1e300` gives not_int on both sides (probe). A raw control byte gives bad_json on both, and the raw-control mutation goes red (3 fixtures). `tables:[{protocol:1.0}]` gives not_int on both. The new parser still parts from Python on other leaves: see X-S1. |
| E-S2 non-ASCII names | **fixed** | `converters.WireName` and `wire_fields.gd::identity` both now hold names to printable ASCII. Breaking it goes red on both sides: Python's WireName ASCII mutation, and Godot's `optional_name_escaped_non_ascii.bin`. |
| E-S3 tests that hang | **fixed** | All five round-1 mutations are now red in about 11 s, none hangs: max_size, the second-hello close, the binary-after-welcome close, the hello protocol check (now `messages._check_protocol`), and `wait_for` on the hello deadline. |
| E-S4 invisible characters | **fixed** | Every round-1 case is now refused: 40 VS16, 40 supplementary selectors, the ZWJ/VS16 run, CGJ, the Hangul filler alone, the braille blank alone. Each of these mutations goes red: the ignorable refusal, the emoji-base condition, the presentation rule, the blank set, the draws-nothing check, and `_drawn_at` for a joiner after a VS. Residual scope: X-N2. |
| E-N1 integer length guard | **fixed** | Deleting the guard in `strict_json._integer` turns the 10,000-digit test red. |
| E-N2 compression | **fixed** | `test_the_server_negotiates_no_compression` goes red when `compression=None` is deleted. |
| E-N3 masked checks | **open** | The fold did not address it. I deleted the shape check in Python `grammar._containers` and all 276 tests stayed green. In Godot, `_containers`' cells-shape check and `_channel`'s raw-scale check also survive deletion (86 tests green). The fixtures `grid_shape_differs` and `raw_with_scale` are unchanged. The WireJson ASCII-loop part is moot: the loop is gone, and `frame_decoder.gd`'s byte loop is red when broken. |
| E-N3b token compare early exit | **open** | The code is unchanged, with no test and no backlog row. It is review-held only. I'd accept a row in B14 that names it. |
| E-N4 digest `$` | **fixed** | Reverting `\z` to `$` turns `digest_trailing_newline.bin` red. |
| E-N5 8009004's mutation count | **open** | The fold's "Correction" paragraph addresses fixture coverage, not the 2-versus-1 count. NIT only. |
| E-N6 welcome read loosely | **fixed** | `NetSession._on_welcome` now reads protocol, session, role and digest, and compares the catalogue hash with this build's. Each of these mutations goes red: dropping the catalogue compare, and widening the session range. A welcome with no hash gets bad_shape (tested). |

Counts: **9 fixed, 3 open, 0 deferred, 0 rejected.**

### The commit's "proven by breaking" claims

Every one holds; I broke each in a scratch copy and watched it go red.

- **Godot:**
  - welcome catalogue check: red, 1 test;
  - first refusal wins: red, 1 test;
  - overlong UTF-8, in the author's form (`cp < smallest - 0x10000000`): red on the 3- and 4-byte fixtures;
  - depth: red, `nesting_past_limit`;
  - repeated keys: red, 5 fixtures;
  - raw control characters: red, 3 fixtures;
  - digest anchor: red;
  - an Origin header added to `NetClient.open`: 3 of the 4 test_godot_net tests red;
  - close-reason read: all 4 red, though the run took 188 s, because the net check waits out its own timeout.
- **Python:**
  - session leak: red;
  - quiet logger removed: `test_no_token_reaches_a_log...` red;
  - asyncio scan: red for a planted `asyncio.sleep` and for a planted `get_running_loop().time()` in server.py.
- **The two removed checks:** the claim that trailing-comma and leading-zero refusal now falls out of the grammar is true. `_separated` and `_number` refuse both, and both fixtures are refused.

## 2. New findings in the fold

### SHOULD-FIX

**X-S1. `client/addons/engine/net/wire_json.gd::_hex4`, `::_real`, `::_escape`: the "strict RFC 8259 parser" hands
its leaves to Godot's lenient helpers, so it still parts from `strict_json` on inputs outside the corpus. O63's premise
and the commit's "judged alike by both decoders, code for code" are false there.**

Measured on HEAD, with the same bytes fed to `strict_json.decode` / `decode_frame` and to `WireJson.parse` /
`FrameDecoder.decode` (`<scratchpad>/delta1/executor/mkprobe.py`, `probe.gd`):

| input | Python | Godot |
|---|---|---|
| `{"a":"\u-041"}` | bad_json | **accepted** (a = U+FFFD) |
| `{"a":"\u+041"}` | bad_json | **accepted** (a = U+FFFD), and the engine prints `ERROR: Invalid hexadecimal notation character "+"` from `hex_to_int` |
| `[1e999…9]` (400 exponent digits) | bad_json (overflow) | **accepted as 0.1** |
| `{"a":"x\u0000y"}` | accepted, `x\x00y` | accepted, `x�y` (a different value; Godot logs "Unexpected NUL character") |
| frame, a channel name `\u+06daterial` | bad_json | bad_identity_key |
| frame, a unit `\u-069d` | bad_json | bad_identity_key |
| frame, `"tick":1e<400 nines>` | bad_json | not_int |

The causes:
- `is_valid_hex_number()` allows a leading sign.
- `String.to_float()` misreads a long exponent instead of overflowing.
- `String.chr(0).to_utf8_buffer()` followed by `get_string_from_utf8()` replaces NUL with U+FFFD.

At the frame level every case is still refused, so nothing hostile gets in. But the code differs, and at the JSON
layer that NetSession reads text with, the outcome differs. Round 1's lesson was that this class of gap is only found
by inputs outside the fixtures. The corpus has no signed escape, no long exponent, and no value check on
`escaped_nul`, which compares outcomes only.

Fix (unverified):
- `_hex4` checks each of the four bytes against `[0-9A-Fa-f]` itself.
- `_real` decides overflow from the literal: count exponent digits, or compare against the largest double's text, as
  Python's `float()` does.
- `\u0000` either keeps U+0000 or is refused on both sides.
- Add each row above as a `json/` or `frames/` fixture, and for `escaped_nul` compare the decoded value, not only
  the outcome.

**X-S2. `src/simcore/protocol/grammar.py::_header` (the `integers_only` call) and
`client/addons/engine/net/wire_json.gd::parse_server`: the two halves of O62's "one helper on each side" can each be
deleted with every test green.**

- Python: I deleted `integers_only(raw, "frame header")`, and test_wire stays green (276 passed). The schema's `Whole`
  converters refuse every float that the fixtures place, so the call decides nothing any test checks. Its unit test
  covers the function, not this call site.
  Failure scenario: a header float where the schema reports another code first. With the call removed,
  `"tables":[{"protocol":1.0,…}]` or an unknown key holding `1.5` reads as unknown_field in Python and not_int in
  Godot. That is exactly the divergence the call exists to prevent.
- Godot: I replaced `parse_server`'s protocol check with `false`, and the client suite stays green (86). No test sends
  a welcome or error whose `protocol` is a float, so the bad_version-for-a-float-protocol rule on text messages is
  unguarded. With the check gone, NetSession ends with not_int instead.

Fix (unverified): add a frame fixture with a float inside a nested unknown or optional place (want not_int, on both
sides), and a `test_net_session` case `{"protocol": 0.0}` written as text (want bad_version).

### NIT

- **X-N1 `src/simcore/core/text.py::_visible`:** the `not _within(DEFAULT_IGNORABLE, ch)` clause survives deletion
  (333 green). It is redundant: `_refused_at` refuses every ignorable code point itself, and FE0E and FE0F go through
  `_presentation_at`. Drop the clause or test it.
- **X-N2 `src/simcore/core/text_tables.py::EMOJI`:** the table is Unicode's `Emoji` property, not the set O65 names
  ("a character with text and emoji forms", that is, emoji-variation-sequences). So these pass:
  - `"😀️😀😀︎😀️"`: U+1F600 has no text form;
  - `"1️2︎3️4"`: digits without a keycap.

  Each base therefore carries about 1.6 hidden bits in a selector that draws nothing different. That is bounded by the
  visible characters, but it is not what the comment, "the only bases a variation selector may follow", or O65 say.
  It is the owner's call whether to narrow the table or the wording.
- **X-N3 `client/addons/engine/net/net_client.gd::poll` / `::open`:** two of the commit's stated behaviours survive
  deletion with test_godot_net green (4 passed): "the client closes after it" (`peer.close(1000, session.refusal)`) and
  "a reconnect starts a fresh session" (`session = NetSession.new()` in `open`). Both are true by reading only.
- **X-N4 `wire_json.gd::_integer`:** the `digits > _INT_DIGITS` guard survives widening (86 green). It is probably
  redundant, because `to_int` saturates on overflow (I did not verify why), so the comment's claim that it matters
  isn't held by a test.
- **X-N5, the commit message's numbers:**
  - It says tile_and_client is 5380 of 5408 words. `wc -w` at 0c7e6e6 gives 5389, still within budget.
  - It says "41 grammar edges and 12 frame edges". The manifest grew from 14 to 56 json fixtures (+42) and from 46 to
    59 frame fixtures (+13, counting `optional_channel_omitted`).

  The other three word counts match `wc -w` (client_rendering 3739, boundaries 10736, world_v2 5404).

Scripts and logs: `<scratchpad>/delta1/executor/{pymut.py,gdmut.py,mkprobe.py,probe.gd,txt.py,rungd.py}`.
