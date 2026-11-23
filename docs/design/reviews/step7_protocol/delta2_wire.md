# Wire integrity, delta round 2: phase1/protocol (fold 88d7787..cde7634)

Lens: Wire integrity. I read the fold's diff for `client/addons/engine/net/*`, `strict_json.py`, `messages.py`,
`frame_header.py`/`grammar.py` (order), `scripts/wire_{fixtures,frames,texts}.py`, the manifest, `test_wire_fixtures.gd`,
`test_net_session.gd`, boundaries §9.1 and O63 to O66.

**How I checked.** I reviewed the committed tree: `git archive cde7634` went to `<scratchpad>/delta2/wire/head`, and
Python ran with `PYTHONPATH` on that copy (I confirmed `simcore.__file__` resolves there). I wrote 1,817 probes
(`<scratchpad>/delta2/wire/gen.py`): delta-1's 81, re-run, plus new ones. They cover BOM and NUL placement, C1, U+2028,
integer edges, 59 hard float literals and their negatives, 800 random doubles (shortest repr and 17 digits), 300 random
long decimals, 400 near-halfway decimals, exponent saturation, and 102 two-fault frames (3 channel-rule faults × 17
other faults, in both array orders). Python judged each one with `strict_json.decode` or `grammar.decode_frame` and
recorded `wire_texts.value_tree`. Godot 4.7.2 judged the same bytes with `WireJson.parse` or `FrameDecoder.decode`
(`<scratchpad>/delta2/wire/client/probe.gd`, which uses the same `_tree` as `test_wire_fixtures.gd`). Godot ran only through
`godot_check.run_godot`, with HOME in scratch. I made each mutation in `<scratchpad>/delta2/wire/mut` and ran
`res://tests/run.gd`. The baseline was `client-tests: PASS 89 tests`.

**Result:** every frame probe agrees, outcome and code, and so does every text, BOM, NUL, escape and integer probe.
**799 probes part, all on floats.** 798 of them are a value difference, and 1 is an outcome difference (NT-1).

## Fold table (my delta-1 findings still open, and the ones it raised; status read from the tree)

| # | Status | What I checked |
|---|---|---|
| S4 | **fixed** | `_read_header` runs `_channel_rules` after every array is read, which matches `read_header`, where `HEADER.read` runs before each `Channel` is built. All 102 two-fault frames agree on the code. I mutated the decoder back to per-array rules, and `raw_scale_and_{unknown_dtype,bad_name,bad_of}.bin` went red (3 failures). |
| S8 | **fixed** | The manifest's `limits` come from the server's constants (`wire_fixtures.LIMITS`), and `test_the_client_s_limits_are_the_server_s` compares all eight. I mutated MAX_GRIDS to 9: `too_many_grids.bin` and `max_grids` went red. |
| N2 | **fixed** (welcome) | `server/welcome.json` comes from `encode(welcome(...))`, and `test_net_session.gd` reads it through NetSession. `error` still has no golden. I accept that, since it carries only a code that NetSession checks for shape. |
| N3 | **fixed** | client_rendering §4.1 now reads "a known channel's from the closed vocabulary", which matches the code. |
| N5 | **fixed** | `TEMPERATURE_BITS` probes temperature_c's f16 bits at two cells, and Godot reads them as u16 bits. I did not mutate this one. |
| SF1 | **fixed** | The BOM is built point by point, and U+0000 is refused on both sides (§9.1). All 26 BOM and NUL probes agree on outcome and on value (mid-string BOM, a double BOM, a BOM then an astral character, a BOM key against the empty key, NUL alone, NUL in a key, NUL as `protocol`). Mutations: BOM branch off → 6 red (`kind_with_escaped_bom`, `grid_name_with_escaped_bom`, `raw_bom_in_key`, ...). NUL allowed → `escaped_nul.json` red. |
| SF2 | **fixed** | `_hex4` checks each digit. `\u+041`, `\u-041`, `\u0x41` and `\u 041` all agree. With the `is_valid_hex_number` mutation, `signed_unicode_escape_minus.json` went red. |
| SF3 | **fixed** for outcome, under the shipped caps | `_double` works out the magnitude from the digits, and the 10^308 halfway is exact. Every exponent probe from delta-1 agrees, and so do 1e999999, 1e-999999 and 0.0e1000000. Mutations: `to_float` alone → 7 red; halfway rule off → 2 red. The residue is new: SF-1 (values) and NT-1 (past roughly 1 MB). |
| NT1 | **fixed** | `frame_decoder.gd` now points to grammar.py's order, and with S4 fixed that order holds. |
| NT2 | **withdrawn** | It was about a commit message, and a commit message isn't amended. The new message limits its claims to the holes the round measured. |

Counts: 9 fixed, 1 withdrawn, 0 open, 0 deferred.

## New findings in the fold

### SHOULD-FIX

**SF-1. `wire_json.gd::_double` hands its digits to `String.to_float`, which is not correctly rounded and drops
everything below about 1e-292 to zero. So the two readers decode about half of all float literals to different
doubles. That breaks §9.1's new "judged alike, code and value" and `_double`'s docstring ("as Python's float()
reads it").** The fold's value test passes only because the float fixtures it compares happen to avoid such values.

Measured, Python's `float()` against Godot's `WireJson.parse`:
- `[970034019735371.5]` → …371.5 / **…371.6**;
- `[-27862564.327137534]` → …534 / **…537**;
- `[9007199254740993.0]` → 9007199254740992 / **9007199254740994** (the halfway rounds away from even);
- `[1.00000000000000011102230246251565404236316680908203124]` → 1.0 / **1.0000000000000002**;
- `[2.2250738585072014e-308]` (DBL_MIN, a normal double) → DBL_MIN / **0.0**;
- `[4.4501477170144023e-308]` → / **0.0**;
- `[1.16e-292]` → / **0.0**, and every subnormal reads as 0.0.

Counts:
- random doubles: 190 of 400 differ in their shortest repr, and 190 of 400 at 17 digits;
- near-halfway decimals: 118 of 200;
- random long decimals: 142 of 300;
- in the range 1e-30 to 1e30, about 1 in 5 differ by 1 ulp;
- above 1e30, up to 3 ulps;
- below 1e-292, the value is flushed to zero.

I ran a second probe (`probe2.gd`) that calls raw `to_float` on the same literals. It gives the same bits as
`WireJson` on 1,560 of 1,588, so the root cause is Godot's `built_in_strtod`, not the fold's reconstruction.

Impact on the shipped path today: none. O62 refuses every float on the server's JSON (`not_int`), and both readers
still agree on finite versus overflow, so no code parts within the 64 KiB caps. The defect is a written contract
that doesn't hold, plus a docstring and a test that both claim it does. `WireFields.whole()` "still takes one for
the client's own data", so the first client path that keeps a float's value inherits the error silently.

Fix (unverified; it is a contract call for the owner):
- either narrow the contract to "a float is classified, not valued": both readers agree on `bad_json` (overflow)
  versus `not_int`. Then drop float bits from `value_tree`'s parity, or keep only exactly representable short
  literals, and say so in §9.1 and in `_double`'s docstring;
- or give GDScript a correctly rounded decimal-to-double conversion (big-integer arithmetic). That is a large piece
  of work, for values nothing reads.

Whichever is chosen, add fixtures `[970034019735371.5]`, `[9007199254740993.0]` and `[2.2250738585072014e-308]`, so
the claim is held either way.

### NIT

- **NT-1. `wire_json.gd::_double` caps an exponent of 7 or more digits at ±100000, but Python reads the exponent
  exactly. The outcome parts once a text carries about a million digits.**
  - `[1` + 999,990 zeros + `e-1000000]` (1e-10): Python accepts it, Godot gives **bad_json**;
  - `[0.` + 999,999 zeros + `1e1000000]` (1.0): Python reads 1.0, Godot **0.0**.

  Both texts fit under the 1 MiB cap the json fixture tests use. Neither can reach the shipped path, since the frame
  header and NetSession texts are capped at 64 KiB and the cap stays exact while a text holds fewer than about 99,700
  digits. But `parse` takes any `max_bytes`, so either state that bound in the docstring or count the exponent's true
  value saturating only past `max_bytes + 400`.
- **NT-2.** For `1e999999`-class literals, `to_float` still prints `WARNING: Exponent too high` (5 of my probes).
  `godot_check.ERROR_LINE` doesn't match WARNING lines, so the gate is unaffected, but hostile input can still write
  to the engine log.

## Checked, no finding

- **Frames:** delta-1's 41 frame probes and 24 new ones agree, outcome and code. That includes `protocol` written as
  `1e400` (`bad_json`) or as `"\u0000"`, a BOM before the `protocol` key, `tick` at 2⁵³−1 and past it, names of 64
  and 65 characters, a name that is empty or a space, leading and trailing spaces, an upper-case or short catalogue
  hash, and another digest scheme.
- **Text:** C1 controls, U+2028, U+FFFE leading, lone or unpaired surrogates, and a BOM before the value all agree,
  in outcome and in value.
- **Integers:** ±(2⁵³−1) accepted and ±2⁵³ refused on both sides. `-0`, `01`, `-01`, `+1` and a 17-digit negative
  agree.
- **NetClient and NetSession:** the `CODE` regex `^[a-z][a-z_]{0,31}\z` accepts all 43 `RefusalCode` values (the
  longest is 16 characters).
- **The encoder:** `strict_json.encode` now refuses NUL and lone surrogates in keys and values alike. No reply the
  server builds can hold one, because decoded input already refuses both.
