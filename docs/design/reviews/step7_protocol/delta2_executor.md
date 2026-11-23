# Executor delta-2 review: step 7 fold (88d7787..cde7634)

Lens: Executor. I reviewed the committed tree at cde7634, from `git archive cde7634` copies at
`<scratchpad>/delta2/executor/py` (used for Godot) and `.../py2` (used for Python). Python runs with PYTHONPATH set to
the copy. Godot runs through `godot_check.run_godot`, with HOME inside the scratch directory. I wrote nothing to the
worktree.

Baseline:
- The Python modules I touched (wire, text, host, formats, determinism) pass 1307, with 1 skipped.
- The client suite passes 89.
- `test_godot_net` passes 6.

I did not rerun the commit's gate numbers for 88d7787 (3406 passed, 5 failed).

## 1. Fold table (the findings delta 1 left open or raised)

| ID | Status | What I checked |
|---|---|---|
| X-S1 Godot leaves part from strict_json | **fixed** (measured rows) | Every row I measured now agrees. `\u+041` and `\u-041` are fixtures, and the hex mutation goes red. A long exponent goes through `_double`; the saturation mutation goes red on `exponent_past_u32`. U+0000 is refused on both sides: `escaped_nul` is red in Godot, and the decode and encode checks are red in Python. A new hole is in the same code (S1 below). |
| X-S2 O62's two halves deletable | **fixed** | Python: deleting `integers_only(raw, "frame header")` goes red (`float_where_the_schema_answers_first`). Godot: putting the not_int check before the version goes red in 3 tests, and `versioned` forced false goes red in 7. Residual: N2. |
| X-N1 `_visible` ignorable clause | **open** | Deleting it still leaves 60 green. The fold added a second clause of the same kind (N3). |
| X-N2 EMOJI wider than O65 | **fixed** | The table now holds 219 code points (I counted them). `😀︎`/`😀️` is refused. `1️2︎3️4` still passes, because the digits, `#` and `*` are keycap bases with FE0F in emoji-test.txt. That matches O65's "text and emoji forms", so I accept it. |
| X-N3 NetClient behaviours by reading only | **open** (half) | The close after a refusal is now held: removing it makes test_godot_net go red. The reconnect's `session = NetSession.new()` can still be deleted with 6 green. |
| X-N4 `_INT_DIGITS` guard | **open** | Widening it by 1000 leaves 89 green. The code is unchanged and no test was added. |
| X-N5 commit numbers | **fixed** | The message now says 5389 words and +42/+13. That matches what I measured in delta 1. |
| E-N3 masked checks | **fixed** | Each check now goes red when deleted. Python's cells-shape check is red on `grid_shape_same_count`. In Godot, the cells-shape check is red on that fixture too, and the raw-scale check is red on `optional_raw_with_scale`. |
| E-N3b token compare early exit | **open** | `tokens.py` is unchanged, and it has no B14 row. The commit doesn't mention it. |
| E-N5 8009004's count | **fixed** | The commit message now gives 1 failure, not 2. |

Counts: **6 fixed, 4 open, 0 deferred, 0 rejected.**

### The commit's "proven by breaking" claims

All of them hold. I broke each one in a copy and watched it go red.

- **Godot:**
  - BOM kept: 6 failures.
  - Hex digits only.
  - Rounding down to the largest double: 2 failures.
  - No U+0000.
  - Channel rules: dropping the rules goes red, and so does moving them back into `_channel`, the old order (3 failures, on the `raw_scale_and_*` fixtures).
  - Version first: 3 failures.
  - The error code's shape.
  - Exponent saturation.
  - The 4 MiB buffer and the close after a refusal: each one test_godot_net test red.
- **Python:**
  - `integers_only` in the header.
  - A malformed second hello, and the `HelloRefused` re-raise.
  - A repeated Upgrade.
  - Blank and filler in `_refused_at`. The copy in `_visible` survives (N3).
  - U+0000 decoded and encoded, and the encoder walking keys.
  - MapOf in the walk.
  - MAX_QUEUE.
  - The network-lane contract: with a planted `import simcore.core.applier` in server.py, `lint-imports` reports BROKEN.
- **The asyncio scan:** a planted `connection.loop.time()`, a second `wait_for`, `getattr(asyncio, ...)`, `call_later`, `get_event_loop()` and `asyncio.tasks.*` each go red. See N5 for one it misses.

Other factual claims:
- U+1D159 still passes `player_text`, as the residual note says.
- The allowlist diff matches the message: `logging` is added and `UNSUPPORTED_DATA` is dropped.
- The text cap equals `MAX_MESSAGE_BYTES` (64 KiB). This one is true only by reading (N4).

## 2. New findings in the fold

### SHOULD-FIX

**S1. `client/addons/engine/net/wire_json.gd::_double`, the `elif magnitude == 308 and _past_largest(significant)`
branch (round up to inf): it decides an outcome, and no test holds it.**

Replacing it with `elif false:` leaves 89 green. It is not dead code: `String.to_float` rounds literals at or past the
halfway point 2^1024 − 2^970 *down* to the largest double. With the branch gone, Godot accepts 8 of my 11
near-halfway literals as 0x7fefffffffffffff, where Python gives bad_json. Among them:
- `1.79769313486231581e308`;
- `1.797693134862315808e308`;
- the exact halfway, as an integer-like literal and in e308 form;
- halfway + 1.

The corpus's `rounds_up_past_the_largest_double` (`…159e308`) doesn't tell the two apart, because `to_float` already
gives inf there. That is the same "removed as code no test can tell apart" situation the commit applied to the two
caps.

Fix (verified by probe): add `[1.79769313486231581e308]` (refused, bad_json) to `_number_and_structure_edges`. On the
unmutated tree, Python and Godot both refuse it. With the branch removed, Godot accepts it.

**S2. `client/addons/engine/net/net_client.gd::poll`, the close reason "only in a refusal code's shape": untested.**

Replacing `NetSession.CODE.search(reason) != null` with `not reason.is_empty()` leaves test_godot_net green (6). The
commit lists this behaviour among the Wire/Client SHOULD-FIX folds, but not among its proven guards.

Failure scenario: the regex is loosened or lost in a refactor. A server, or anything on the port, that closes with
prose (or a 123-byte reason) then sets `session.refusal`, and the client both shows that text and echoes it.

Fix (unverified): a test_godot_net case where the server closes 1008 with the reason `"Not a code!"`, wanting
`closed 1008`.

**S3. `docs/design/boundaries.md` grew from 10,736 to 10,747 words (`wc -w`, 88d7787 to cde7634), against O22 and
O66.**

O66 says each addition is paid for by an equal cut in the same document, or the author stops and asks. client_rendering
(3739 to 3727) and tile_and_client (5389 to 5386) shrank, but those cuts can't pay for boundaries.

Fix: cut 11 or more words from boundaries.md.

### NIT

- **N1. `wire_json.gd::_double`'s doc comment says `to_float` "reads [the literal] as Python's float() does". That is
  false.**
  - What I measured: 10 of 37 probe literals read to different IEEE bits.
    - Every value below about 4.5e-308 reads as 0, including the smallest normal (`2.2250738585072014e-308`),
      `4.4501477170144023e-308` and `5e-324`.
    - The ties `9007199254740993.0` and 1 + 2^-53 round up, not to even.
    - `8.98846567431158e307` is off by one ulp.
  - Godot also logs `WARNING: Exponent too high` for some literals.
  - No shipped outcome depends on this, because every float in the server's JSON is not_int. But the comment and
    `test_every_accepted_json_text_reads_to_the_server_s_value` read as a general guarantee. Correct the comment, or
    name what the value test covers.
- **N2. `wire_fields.gd::version`, the parameter `was_float`:** it is redundant. A float literal parses as a `float`,
  and `not value is int` already refuses it. Passing `false` leaves 89 green.
- **N3. `text.py::_visible`, the clause `and not _blank(ch)`:** it survives deletion (60 green). `_refused_at` already
  refuses every blank, so it is redundant. Like X-N1, drop it or test it.
- **N4. `net_session.gd::MAX_TEXT_BYTES`:** it isn't in the manifest's `limits`. Changing it from 64 to 256 KiB leaves
  89 green, so "the manifest carries the limits, and Godot holds its constants to them" doesn't cover it.
- **N5. `tests/test_determinism.py`, the asyncio scan:** `_a = asyncio; _a.sleep(0)` planted in server.py stays green
  (104 passed). The commit claims "any value" for the loop's handles, not module aliases, so this is a limit and not
  a false claim. Worth a line in the scan's docstring.
- **N6. `text.py::_blank` in `_refused_at`:** U+2800 is now refused anywhere, not only in a message that draws nothing.
  - That goes past O65's wording, "a message that draws nothing (… U+2800) is refused".
  - It also refuses ordinary braille text, which uses U+2800 as its word space (`⠓⠑⠇⠇⠕⠀⠺⠕⠗⠇⠙`).
  - Owner's call: record the wider rule in O65 and §5.3, or narrow `_blank` back to the draws-nothing check for
    U+2800.

Scripts and logs: `<scratchpad>/delta2/executor/{gdmut.py,gdmut2.py,gdmut3.py,pymut.py,pymut2.py,mkfloat.py,probe*.gd,gdmut_out.txt}`.
