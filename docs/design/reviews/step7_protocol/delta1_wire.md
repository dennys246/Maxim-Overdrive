# Wire integrity, delta round 1: phase1/protocol (fold 8beb6af..0c7e6e6, plus 88d7787)

Lens: Wire integrity. I read the fold's diff for `src/simcore/protocol/*`, `core/{converters,schema}.py`,
`client/addons/engine/net/*` (the new `wire_json.gd` and `net_session.gd` in full), `scripts/wire_{fixtures,texts}.py`,
the manifest, both fixture tests, `test_net_session.gd`, the owner sections the fold edited, and O63 to O66.

**How I checked.** I reviewed the committed tree. `git archive HEAD` (88d7787) went to `<scratchpad>/delta1/wire/head`.
The worktree had uncommitted edits by another session to `converters.py`, `schema.py`, `server.py` and some tests, so
I read none of my results from it. I wrote 81 probes (`<scratchpad>/delta1/wire/gen.py`): 40 JSON texts and 41 frames.
Python judged each one with `strict_json.decode` or `grammar.decode_frame`. Godot 4.7.2 judged the same bytes with
`WireJson.parse` or `FrameDecoder.decode` (`<scratchpad>/delta1/wire/client/probe.gd`), run through
`godot_check.run_godot` with HOME in scratch. **18 of the 81 disagree.** I made each mutation in a scratch copy, ran
the targeted tests, then restored the copy.

## Contract table (what changed)

| Contract | Producers (before → after) | Consumers (before → after) | What each consumer gets, before → after | Owner |
|---|---|---|---|---|
| The client's JSON parser (O63) | — | `JSON` + text scans → `WireJson.parse` (FrameDecoder) / `parse_server` (NetSession) | Godot's lenient parser → a parser over bytes. All 56 json and 59 frame fixtures agree. **18 probes still part** (SF1–SF3, S4) | boundaries §9.1 |
| Server JSON is integers only, judged after the version (O62) | `strict_json.encode` (now also refuses non-JSON types) | `integers_only` after `read_version` / `WireFields.version` then `non_integer_keys` | Before, Python and Godot gave different codes. After, `not_int` on both sides, or `bad_version` for a top-level `protocol`. 12 float and protocol probes agree, and the nested `protocol` case (N7) agrees | client_rendering §4.1 |
| Wire names are printable ASCII (O63) | — | `WireName` / `WireFields.identity` (decoded text) | Python accepted `zönes` and Godot refused it → both refuse, `bad_identity_key` (fixture) | §4.1 |
| A frame's hash is welcome's full catalogue (O64) | `encode_cells(catalogue=…)` hashed the carried channels → hashes the whole catalogue | both decoders, and NetSession (welcome's hash against the build's) | a subset frame changed the hash → it doesn't (fixture `optional_channel_omitted`) | §4.1 |
| Welcome as the client reads it | `replies.welcome` (unchanged; hand-built) | NetClient read `protocol` only → NetSession reads `protocol`, `session ≥ 1`, `role ∈ {host, guest}` and the digest, then compares it with the build's | the first refusal ends the session | §4.1 (partly; N2) |
| Hello reads `protocol` first | `messages._check_protocol` before the schema; `_VERSION = Whole(0,0)` | server | an extra field or a long token in a newer hello gave `unknown_field`/`bad_shape` → now `bad_version` | boundaries §5.3 |
| Close reason = refusal code; `hello_first` | `server._refuse` | NetClient reads the close reason | §4.3, tile §3.4 marker | §4.3 / tile §3.4 |
| Region probe values `i·257 + 1` | `wire_fixtures._arrays` | both fixture tests, asymmetric corners | the u16 byte order is now observable | — |

## Fold table (my round-1 findings; status set from the tree)

| # | Status | What I checked |
|---|---|---|
| B1 | **fixed** | `_arrays` writes `·257 + 1`, and the asymmetric golden probes regions at 8 corners (manifest). Mutation: a u16 encoder writing big-endian (`grammar.encode_cells`) turns `test_the_committed_fixtures_are_what_the_script_makes` and `test_a_frame_round_trips_every_channel_bit_for_bit` red. Round 1's `·257` would have left the first one green. |
| S1 | **fixed** for raw NUL | Fixtures `nul_after_value`, `nul_in_string` and `header_nul_padding`. My `header_nul_tail` probe agrees: `bad_json` on both sides. An *escaped* NUL still parts (SF1). |
| S2 | **fixed** | Both sides apply the ASCII rule. Fixture `optional_name_escaped_non_ascii`. Mutations: Python's `WireName` without its ASCII test → that fixture red in `test_wire.py`; Godot's `identity` bound raised to 0xFFFF → red in `test_wire_fixtures.gd`. |
| S3 | **fixed** as stated | My four probes (`1e20`, `9007199254740992.0`, raw UTF-8, NUL tail) are now fixtures, and both sides agree on them. The json set still holds texts on which the readers part (SF1–SF3). |
| S4 | **open** | The float cases now agree (`required:1.0`, `kind:1.5`, `zz:2.5` and `tick:1e20` → `not_int` on both sides), as do the `catalogue` with a trailing `\n` (`bad_shape`) and welcome `protocol:1.0` (`bad_version`). The cross-array order still parts. Python runs `Channel.__post_init__` after the whole `HEADER.read`; Godot runs it per array. Three probes: array 0 raw with scale `[2,1]` plus array 1 dtype `u64` → `unknown_kind` / `bad_shape`; plus array 1 name `a:b` → `bad_identity_key` / `bad_shape`; plus array 2 `of: "a:b"` → `bad_identity_key` / `bad_shape`. The docstrings of `frame_decoder.gd` and `wire_fields.gd` still claim the same order and codes, and the fold neither changed them nor deferred the finding. |
| S5 | **fixed** | `_check_protocol` runs before the schema. Mutation (call removed) → 12 tests red, including `test_host.py`'s `compat` field and 99-char token cases. |
| S6 | **fixed** | tile §3.4's marker and row now list `host_only bad_version missing_field bad_identity_key over_budget bad_text bad_token token_in_use hello_first`. |
| S7 | **fixed** | client_rendering §4.1's frame row names every key, `cell_size_um`/`origin_um` as world x, y, z, `compression: none`, ASCII names and O64's hash scope. |
| S8 | **open** (partly fixed) | Fixtures `too_many_tables`, `extent_past_u16` and `name_with_colon` were added. Godot mutations MAX_TABLES 17 and MAX_EXTENT 65536 → red. The other mirrored limits stayed **green** under mutation: MAX_GRIDS 9, MAX_ARRAYS 65, MAX_HEADER_BYTES 65 KiB and an identity length of 65, all four in one run, "PASS 86 tests". Nothing ties those four copies to the server's values. |
| N1 | **rejected** (I withdraw it) | `docs/generated/protocol.md`, the artifact of the registry §9.1 makes primary, names `op` and its words. |
| N2 | **open** (partly fixed) | The client now checks welcome's hash against its build's, unit-tested. `welcome`/`error` are still hand-built dicts outside the registry, and no golden welcome bytes from `replies.welcome` reach the Godot reader except in the live test. |
| N3 | **open** | §4.1 still says each `unit` comes "from the closed vocabulary"; the code still lets an unknown optional channel's unit through. |
| N4 | **fixed** | `WireCatalogue.catalogue_hash` is now on the shipped path (NetSession), but its docstring states its domain, wire names are ASCII, and the V0 hash test holds it. |
| N5 | **open** | The probes still read only `material` and `region`; there is no f16 `temperature_c` golden. |
| N6 | **fixed** | §9.1 now states O62 and O63. |
| N7 | **fixed** | `non_integer_keys` takes the key only at depth 1. Probe: `"zz":{"protocol":1.0}` → `not_int` on both sides. |

Counts: 10 fixed, 5 open, 1 rejected, 0 deferred. None of my findings is in the step 7 checklist. The four deferrals
listed there (C3, A8, A6, A7) belong to other lenses.

## New findings in the fold

### SHOULD-FIX

**SF1. `wire_json.gd::_string` builds each string with `PackedByteArray.get_string_from_utf8()`, and Godot's UTF-8
reader strips a leading U+FEFF and turns U+0000 into U+FFFD. So Godot accepts frames Python refuses, and keys
collide.** I measured both behaviours in Godot 4.7.2: raw `EF BB BF 61` reads as a 1-character `"a"`, and an escaped NUL
prints "Unicode parsing error … Unexpected NUL character" and reads as U+FFFD. Probes, Python / Godot:
- frame, a header key `"﻿tick":5` in place of `tick`: `unknown_field` / **accepted**, read as `tick`;
- frame, `"catalogue":"﻿<welcome's hash>"`: `bad_shape` / **accepted**;
- frame, `"kind":"﻿full"`: `unknown_kind` / **accepted**;
- frame, grid name `"﻿cells"`: `bad_identity_key` / **accepted**;
- json `{"﻿a":1,"a":2}` (escaped or raw): accepted / `bad_json` (repeated key);
- json `{"a\u0000b":1,"a�b":2}`: accepted / `bad_json`.

The committed fixture `escaped_nul` is "accepted" on both sides, but the two values differ (`"x\x00"` in Python,
`"x�"` in Godot), so the corpus counts as agreement a case where the readers part. This is round 1's S1 again,
now entering through escapes. It breaks O63's "judged alike, code for code" and the twin decoder's defence in depth.
The server's encoder never writes these bytes, so nothing breaks today. Failure scenario: a header string the client
reads differently from the server, such as a hash or a key, is accepted as something else. Fix (unverified as a
whole; I measured its primitives): build the string from code points. `String.chr(0xFEFF)` appended to a String keeps
it (length 2 for U+FEFF + "a"), and `String.chr(0)` has length 1. If Godot can't carry NUL through every path, refuse
`\u0000` on both sides (a contract line in §9.1). Add frame fixtures for a BOM'd key and hash, and json fixtures for
both key collisions.

**SF2. `wire_json.gd::_hex4` accepts a sign: `String.is_valid_hex_number()` allows a leading `+` or `-`.** `["\u-041"]`
and `["\u+041"]` → Python `bad_json` / Godot **accepted**, with the value U+FFFD. `"\u+041"` also makes the engine print
`ERROR: Invalid hexadecimal notation character "+"`, a line `godot_check.ERROR_LINE` matches, so a fixture of it would
fail the gate's error scan rather than its outcome check. Separately, after a failed `_hex4`, `_escape` still calls
`String.chr(-1)`. That prints a "Unicode parsing error" on the committed `short_unicode_escape` fixture; the outcome is
still right. Fix (unverified): check each of the four bytes against `[0-9A-Fa-f]`, and return from `_escape` on -1.

**SF3. `wire_json.gd::_real` decides finiteness with `String.to_float()`, whose exponent wraps or clamps; Python uses
`float()`.** Python / Godot:
- `[1e4294967296]`: `bad_json` / accepted as 1.0;
- `[1e2147483648]`: `bad_json` / accepted as 0.0;
- `[1e4294967297]`: `bad_json` / accepted as 10.0;
- `[0e99999999999999999999]`: accepted / `bad_json`;
- `[0.` + 400 zeros + `1e400]` (≈ 0.1): accepted / `bad_json`.

Godot also prints "WARNING: Exponent too high". On the server-JSON paths every float is refused anyway, so only the
code parts: frame `"tick":1e4294967296` gives `bad_json` / `not_int`. The `json` set promises one outcome for both
readers, and these five break it. Fix (unverified): the parser already holds the digits, so bound the exponent and
mantissa before converting. Alternatively, make the contract say that floats on the server's JSON are `not_int`
without being evaluated, on both sides.

### NIT

- **NT1** `frame_decoder.gd` and `wire_fields.gd` docstrings: "with its checks in the same order and its refusal codes"
  and "the client refuses for that field with the same code" are still false for multi-fault headers (S4). Either
  align the order or narrow the claim.
- **NT2** The fold message says "A corpus of 41 grammar edges and 12 frame edges … is judged alike … code for code".
  That holds for the corpus as committed. SF1 to SF3 show inputs outside it that part, which the message already
  concedes about round 1's corpus.

## Checked, no finding

- The protocol-first order on both sides: `true`, `"0"`, `-1`, `0.0`, `[1.0]`, a missing protocol with a float
  elsewhere, and the key `"protocol\u0000"` all give `bad_version` on both.
- Agreement on: depth 32 and 33 for objects, `-0`, `-0.0`, `1E+2`, a 16-digit integer, the subnormal and maximum
  doubles and the first value past the maximum, a form feed or NBSP as whitespace, `￿` escaped and raw, two high
  surrogates, `\U0041`, and every NUL-in-name, NUL-in-choice and NUL-in-key frame probe.
- The new `WireJson` contracts (UTF-8 lead and continuation checks, overlong forms, surrogates, past U+10FFFF, depth,
  repeated keys, the 2⁵³ pin) agree with Python on every committed fixture and on my probes, except SF1 to SF3.
- NetSession: a float anywhere gives `not_int`, a float `protocol` gives `bad_version`, welcome comes once, a frame
  before welcome is `bad_shape`, and the first refusal wins (unit tests read).
