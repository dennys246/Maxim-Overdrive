# Trust boundary, delta round 2: phase1/protocol (88d7787 ... cde7634)

Lens: Trust boundary. I reviewed the committed tree at cde7634. `git diff cde7634 e97727d -- src client tests` is
empty, so the worktree's code is the fold's code. I reran the delta-1 probes and added new ones, all in
`<scratchpad>/delta2/trust/`: `sweep.py` (every code point through `player_text`), `hello2.py` (second hellos),
`reason.py` (a hostile listener against the real Godot client), `runtests.py` (the client tests). Mutations were made
only in `<scratchpad>/delta2/trust/wt` (from `git archive cde7634`) and `.../client`. Godot ran only through
`run_godot`, with HOME inside the scratch directory.

Counts: fold table **9 fixed, 1 deferred (accepted), 2 open, 0 rejected**. New: **0 BLOCKER, 2 SHOULD-FIX, 3 NIT.**

## Fold table (status read from the tree)

| Id | Status | What I checked |
|---|---|---|
| T-N1 repeated `Upgrade` | **fixed** | `_gate` uses `get_all`. probe5 now gets `400` (it was a `500` with a traceback). Mutation (drop `len(upgrades) != 1`): `test_a_request_with_two_upgrade_headers_gets_a_400` went **red**, and so did the plain-HTTP test. |
| T-N3 pre-hello cap | **deferred, accepted** | Listed in checklist step 7 with a reason (only local programs reach the port) and a trigger (guests beyond localhost, Phase 5). |
| T-N4 malformed second hello | **fixed** | Live, after `welcome`: `{"hello",protocol:0,token:"zz",extra:1}`, `protocol:1`, a bare `{"type":"hello"}` and a valid hello each give `hello_first` and close with 1008, and every session is freed. A repeated `type` key gives `bad_json` and the connection stays open, which is right: its kind can't be read. In the first hello, `HelloRefused` still carries its own code (`bad_version`, `unknown_field`). Mutation (drop the `except HelloRefused` branch): `test_after_welcome_..._a_second_hello_ends_the_session_with_its_code` went **red**. |
| D-B1 invisible filler or blank | **fixed** (two residuals: new N-N1 and N-N2) | Each delta-1 attack is now refused: Khitan filler alone, the 401-character filler-and-joiner run at a cap of 500 and at 200, the hieroglyph blanks, and the braille-blank run. Mutation (drop `_blank` from `_refused_at`): `test_characters_that_draw_nothing_are_refused` went **red**. The fold also over-reaches; see N-S1. |
| D-S1 signed `\u` | **fixed** | `_hex4` checks each digit. Fixtures `signed_unicode_escape_{plus,minus}` are in the manifest. Mutation (back to `is_valid_hex_number`): client tests went **red** on the `minus` fixture. |
| D-S2 peer codes and close reasons | **fixed** (behaviour; its test gap is new N-S2) | Live, against a hostile listener: an error code of `"A"*124` or `"a"*124` becomes `bad_shape` and the client closes with 1000 (before the fold it stayed in CLOSING). A close reason of `"Server Exploded Badly"` becomes `closed 1008`. Mutating NetSession's shape check turned `test_the_server_s_other_messages` **red**. |
| D-N1 `\u0000` | **fixed** | `strict_json` refuses U+0000 when decoding and when encoding. `nul_beside_replacement` is now `bad_json` on both sides. |
| D-N2 `1.7976931348623158e308` | **fixed** | The `just_below_overflow` and `rounds_down`/`rounds_up` fixtures are accepted, accepted and `bad_json`, on both readers. |
| D-N3 256 KiB text stall | **fixed** | `MAX_TEXT_BYTES` is 64 KiB, the server's own cap. I did not re-measure the stall: scaling from delta-1's 1.2-1.4 s at 256 KiB gives about 0.3-0.35 s. |
| D-N4 VS bases | **fixed** (the table) | `EMOJI` now lists emoji-test's FE0F bases. VS16 after U+1F600, a regional indicator or a skin tone is refused. VS15 or VS16 after a digit still passes, and so does a joiner between Latin letters. O61 and O65 allow both, so that part is the owner's ruling, not a defect. |
| D-N5 fuzz reach unasserted | **open** | `tests/test_wire.py` still asserts no reach. It is not deferred. |
| D-N6 `bad_version` field | **open** | `_check_protocol` is unchanged, so `protocol:0.0` still gives no `field`. |

## New findings

### N-S1 (SHOULD-FIX). The blank rule refuses BLANK and FILLER characters anywhere in guest text, beyond O65, and breaks braille and visible punctuation
`src/simcore/core/text.py::_refused_at`

O65 treats U+2800 like a space: "a message that draws nothing (spaces, blanks such as U+2800) is refused". The fold
instead refuses every character whose name holds BLANK or FILLER, wherever it sits. I swept every code point (Unicode
15.0, Python 3.12). Characters that draw a glyph, or are a script's word space, are now refused **inside** ordinary
text:
- `"⠓⠊⠀⠞⠓⠑⠗⠑"` (braille "hi there", with U+2800 as braille's word space): **refused**, `So character at 2`. The
  same text with an ASCII space is accepted, so a braille user can't write braille.
- These print visible glyphs and are refused: U+2422 BLANK SYMBOL (`"a ␢ b"` refused), U+A8F9 DEVANAGARI GAP FILLER
  (`"word꣹"` refused), U+10AF6 MANICHAEAN LINE FILLER, U+1144E NEWA GAP FILLER, U+11945 DIVES AKURU GAP FILLER,
  U+11C44 and U+11C45 BHAIKSUKI GAP FILLER, and U+11F48 KAWI SPACE FILLER.

The test that fixes this behaviour (`"⠀a"` refused "as the name rule refuses it") imports the name rule into
free text, where it doesn't belong. Names follow IDNA and refuse Po and So anyway, but guest text "keeps punctuation,
symbols" (the module's docstring).

Fix (**verified** in a scratch copy): in `_refused_at`, refuse a blank only when it is zero-width, `_blank(ch) and
unicodedata.category(ch) == "Mn"`, and keep `_blank` in `_visible`. With that change:
- braille text, `"a ␢ b"` and `"word꣹"` are accepted;
- `"⠀"`, `"\U00016fe4"`, `"\U00013441"`, `"a"+"\U00016fe4"*50+"b"`, `"a\U00016fe4‍\U00016fe4b"`,
  `"a\U00013441‍\U00013441b"` and `"x‍⠀y"` are still refused (the joiner rule needs drawn
  neighbours);
- `tests/test_text.py` had 59 passed and 1 failed, the failure being the case above, which the fix must flip.

A spacing blank then acts like a space. A run of N of them carries a count of N, as a run of N spaces already does.

### N-S2 (SHOULD-FIX). NetClient's close-reason shape check has no test that can fail
`client/addons/engine/net/net_client.gd::poll` (`var coded`)

I mutated the check to `var coded: bool = not reason.is_empty()`, which takes any reason verbatim, the delta-1 defect.
`MAXIM_OVERDRIVE_GODOT=1 pytest tests/test_godot_net.py` on the mutated copy: **6 passed**. The client unit tests
never run `NetClient.poll`. The commit lists "the error code's shape" among its proven guards, but that mutation
targeted `NetSession.on_text`, which is the error-message half. The close-reason half, which the fold added for D-S2,
has no guard: a regression would bring back the 124-byte close reason and arbitrary refusal text. Fix: add a
`test_godot_net.py` case where the listener sends no error, closes with 1008 and a non-code reason such as
`"Server Exploded Badly"`, and the client's refusal must be `closed 1008`. My `reason.py` probe shows that this is
what happens today.

### NITs
- **N-N1** `text.py::_visible`: the `not _blank(ch)` clause is dead. Removing it leaves `tests/test_text.py` at
  **60 passed**, because `_refused_at` refuses every blank before `_visible` is consulted. The fold's own commit
  removes code that no test can tell apart. With N-S1's fix the clause becomes live and the only blank rule.
- **N-N2** `text.py::player_text`: `"\U0001D159"` (MUSICAL SYMBOL NULL NOTEHEAD) alone is still accepted, though it
  draws nothing, against O65's "draws nothing ... refused". It also still carries the filler-and-joiner run (`run null
  notehead 404 True`), though that run adds no bits beyond O61's sanctioned joiner-between-letters channel. Only the
  commit message records this residual: there is no checklist row, Known gap or backlog row, so it will be lost.
  Record it, or refuse U+1D159 by code point.
- **N-N3** `net_session.gd::CODE` against `tests/test_refusals.py`: the client takes a code that is ASCII
  `[a-z][a-z_]{0,31}`. The Python test holds codes only to `isalpha()` after removing underscores, which allows
  non-ASCII letters and any length. A future code longer than 32 characters (or one with a digit, which both reject
  today) would silently become `bad_shape` on the client, and no shared fixture ties the two together. Separately,
  the shape check isn't a vocabulary check: live, a port squatter's code `you_are_banned_visit_evil_site` becomes the
  client's refusal verbatim, and it closes with that reason. This is low impact, since that process already owns the
  connection, but D-S2's suggested fix was the known codes. Sharing `RefusalCode`'s values through the manifest
  would close both.

## Checked, no finding
- **Version-first read:** delta-1's 15 hostile first hellos give the same codes and a 1008 close with reason = code.
  Wrapping the first hello in `HelloRefused` changes nothing on that path.
- **Logging:** with the root logger at DEBUG, 150 lines and 0 token 8-grams.
- **Sessions:** after 20 close and 20 abort clients, then the second-hello cases, `SessionView(sessions=())`.
- **Oversized hello after welcome:** 70 KB closes with 1009, and the session is freed.
- **Client tests on the committed copy:** `client-tests: PASS 89 tests`.
