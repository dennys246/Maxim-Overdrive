# Wire integrity review: phase1/protocol (origin/main aaebc1b...HEAD 8beb6af)

Lens: Wire integrity (docs/code_review.md). I read `src/simcore/protocol/*.py`, `src/simcore/core/{converters,schema,refusals,digest}.py`, `src/simcore/host/*.py`, `scripts/wire_fixtures.py`, `client/addons/engine/net/*.gd`, both fixture tests, the manifest, and the design owners (client_rendering §4.1–§4.3, world_v2 §8, boundaries §5.3/§9.1, tile §3.3/§3.4, O59–O62).

**How I checked:** I built probe frames and texts from `wire_fixtures` helpers in my scratch directory and decoded each with `grammar.decode_frame` / `strict_json.decode`. I then decoded the same bytes with `FrameDecoder.decode` / `WireJson.parse` in Godot 4.7.2, in a copy of `client/` under my scratch dir, run through `godot_check.run_godot` with HOME in scratch. I did not modify the worktree. 28 probes in all; the disagreements are below. 17 edge probes agreed on both sides: 9 grids (over_budget), a 65-char/colon/tab name (bad_identity_key), tick −1, extent 65536 (out_of_range), negative denominator, grids `{}`, grid `7`, kind `[]`, unknown+missing key ordering, nested-vs-top missing, missing-then-bad-kind, a known channel marked optional, cell_size 0, and a 65,537-byte header.

## Contract table

| Contract | Producers (before → after) | Consumers (before → after) | What each consumer gets, before → after | Owner |
|---|---|---|---|---|
| Cell frame `[u32 LE len][ASCII JSON header][arrays]` | none → `grammar.encode_cells`, `pack`; `wire_fixtures` (malformed) | none → `grammar.decode_frame` (tests only), `FrameDecoder.decode` (NetClient) | nothing → typed header, read-only `(nz,ny,nx)` arrays / `WireFrame` with byte slices; matching outcome on all 46 frame fixtures | client_rendering §4.1 |
| Header keys `protocol kind tick shape regions_version catalogue compression grids tables arrays` | → `frame_header.HEADER` | → both decoders (closed keys) | §4.1 lists the substance; `catalogue` (key name), `tables`, `grids[].name/required`, `arrays[].of` and the per-array full channel are code-only | §4.1 (partial; see S7) |
| Grid `cell_size_um`, `origin_um` **[x,y,z]**, `shape` **[nz,ny,nx]** | → `encode_cells` | → `DecodedFrame`, `WireFrame.origin_um` | µm integers; origin order differs from shape order inside one object; neither is in the owner | none (S7) |
| Channel `name unit dtype encoding required scale[num,den] offset[num,den]` | → `catalogue.Channel.description` | → both decoders; equality = identity | rationals as integer pairs (DC-N5) ✓; raw ⇒ 1/1, 0/1; den > 0 | §4.1 / §4.2 |
| dtypes `u8 u16 u32 f16 f32`, LE | → `catalogue.DTYPES` | → `WireCatalogue.DTYPE_BYTES` | sizes agree; LE for u16 not exercised by any fixture (B1) | §4.1 (LE) |
| Catalogue hash `sha256/c14n-1` over the carried channels in order | → `catalogue_hash`, `replies.welcome.catalogue_hash` | → both decoders (string compare), `WireCatalogue.catalogue_hash` (test only) | equal for V0 (test) ✓; scope (carried channels vs whole catalogue, table columns) not in owner | §4.1 + boundaries §6.3 |
| Extension rule | → grammar `_extension` | → FrameDecoder `_extension` | agree on all fixtures and probes | §4.1, world_v2 §8 |
| Strict JSON (pin < 2⁵³, no NaN/Inf, repeated key, depth 32, size cap) | → `strict_json.decode/encode` | → `WireJson.parse` | outcomes differ on floats ≥ 2⁵³, raw UTF-8, NUL tails (S1, S3) | boundaries §9.1, O59, O60, O62 |
| Client messages `hello move move_to kindle time snapshot` | Godot `NetClient` (hello only) | → `messages.read_message` | `time` takes key `op` (not in owner) | tile §3.3 |
| `welcome {type protocol session role build shape catalogue catalogue_hash}` | → `replies.welcome` | → `NetClient._on_text` (checks `protocol`; reads `catalogue_hash`) | no schema in the registry; client ignores `catalogue`, `build` | §4.1 (N2) |
| `error {type code field?}` + close 1008 reason=code | → `replies.error`, `server._refuse` | → `NetClient` (code or close reason) | code string | tile §3.4 |
| Refusal codes on the wire | → adds `bad_text bad_token token_in_use host_only`; also puts `missing_field bad_version bad_identity_key over_budget` on the wire | → client stores as `refusal` | codes outside the owner vocabulary (S6) | tile §3.4 |
| Gates: 4 MiB inbound, 64 queued, 64 KiB server max_size, 1009 | → server, NetClient | — | match §4.3 ✓ | §4.3 |
| Limits MAX_GRIDS 8 / TABLES 16 / ARRAYS 64 / EXTENT 65535 / HEADER 64 KiB / identity 64 | → frame_header, grammar | → frame_decoder.gd copies | agree today; no fixture or test ties them (S8) | none |
| Manifest `format/version/frame_cap/catalogue`, sets with readers | → `wire_fixtures.files` | → `tests/test_wire.py`, `test_wire_fixtures.gd` | frames + json read by both; client set python only | world_v2 §8 |

## BLOCKER

**B1. `scripts/wire_fixtures.py::_arrays`: the region probe cannot detect byte order.** The comment says "region: both bytes differ, so RG8's byte order shows". In fact `np.arange(n)*257` yields 0x0000, 0x0101, …, 0x0707, values whose two bytes are equal. The only u16 probes are `base` region@[1,1,1] = 7·257 (Python `frame.channels[...]`, Godot `decode_u16`) and `asymmetric`, which reuses the same values. Verified: `(np.arange(8,'<u2')*257).tobytes() == (…).astype('>u2').tobytes()` is True. Failure scenario: the server's u16 is switched to big-endian, or a Godot reader assembles `r<<8|g` (as `cell_snapshot.gd:81` will once the decoder fills CellSnapshot). Every fixture still passes, the fixture bytes regenerate identically, and `--check` stays green. §4.1's "little-endian" therefore has no cross-language guard for u16, and a test that cannot fail is a BLOCKER under the charter. Fix (unverified; arithmetic only): use values whose bytes differ, e.g. `*257 + 1` (7 → 0x0708), and probe at least one region cell in `asymmetric`.

## SHOULD-FIX

**S1. `frame_decoder.gd::_header` / `net_client.gd::_on_text`: a NUL truncates the text, so Godot accepts what Python refuses.** `get_string_from_ascii()` (frames) and `get_string_from_utf8()` (text) stop at the first NUL. Probes:
- the base header followed by `\x00pad`, inside the declared header length: Python `bad_json`, Godot **accepted**;
- the text `{"a":1}\x00xx`: Python `bad_json`, Godot accepted.

So the twin decoder accepts bytes its server twin refuses, and no fixture has a NUL. Fix: before converting, refuse any 0x00 in the header bytes (the ASCII loop already walks them). Add `header_nul` and `json/nul_tail` fixtures.

**S2. `wire_fields.gd::identity`: an identity key is limited to 0x20–0x7E, but the Python rule is `str.isprintable()` over decoded text.** The comment "A header is ASCII, so printable is 0x20 to 0x7E" is wrong. The header bytes are ASCII, but `ö` decodes to ö, and the server's own encoder (`ensure_ascii=True`) writes exactly that escape. Probe: an optional grid named `zönes`. Python **accepted** it (ignored as `grid:zönes`); Godot refused it, `bad_identity_key`. Failure scenario: a registry bump adds an optional channel, unit, grid or table with a non-ASCII name. Old clients refuse every frame instead of ignoring it, which breaks the extension rule the six goldens exist to hold. Fix: either restrict `identity_key` to ASCII on the wire (a contract change, recorded in §4.1), or make Godot's printable test match Python's. Add a fixture either way.

**S3. `strict_json.decode` vs `WireJson.parse`: the "json" set claims "texts both JSON readers judge alike", but the readers implement different contracts.** Probes (Python / Godot):
- `{"a":1e20}`: accepted / bad_json;
- `{"a":9007199254740992.0}`: accepted / bad_json;
- `{"a":"é"}` as raw UTF-8: accepted / bad_json;
- `{"a":1}\x00xx`: bad_json / accepted.

Python reads client text, where floats and UTF-8 are legal. Godot reads server text, which is ASCII and integers only. Both may be right, but nothing states the split, and the 14 json fixtures sit only where the two coincide. Fix: name each reader's contract in §9.1, or in the manifest with per-reader outcomes, and add these four as fixtures.

**S4. Frame refusal codes diverge beyond the fixtures, which contradicts the docstrings.** `frame_decoder.gd` says its checks run "in the same order and [with] its refusal codes", and `wire_fields.gd` says "a header the server would refuse for a field, the client refuses for that field with the same code". Probes (Python / Godot):
- `required: 1.0` → bad_shape / not_int; `kind: 1.5` → unknown_kind / not_int; an unknown key `zz: 2.5` → unknown_field / not_int. Godot's blanket float scan runs before the schema. O62 assigns `not_int` to the client, so either O62 or the docstring must give.
- `tick: 1e20` → not_int / **bad_json**. This one contradicts O62 itself, which says a float literal is `not_int`; `WireJson` applies the 2⁵³ magnitude check before the literal scan.
- Two faults (array 0 raw with scale 2/1, array 1 dtype u64) → unknown_kind / bad_shape. Python runs `Channel.__post_init__` after the whole schema read; Godot runs it per array.
- `catalogue` ending in `"\n"` → bad_shape / bad_version. Godot's `RegEx` `$` matches before a final newline; Python uses `fullmatch`.
- Welcome `protocol: 1.0` gives the client `not_int`, while O62 says protocol floats give `bad_version`.

Impact is low today, since a code is only logged client-side. Still, the claim is false, and the manifest's "one outcome each" holds only because each fixture breaks one rule. Fix: correct the claims, or align the order (post-checks after the schema walk, `\A…\z` in the regex, the literal scan before the magnitude check).

**S5. `server._hello` / `messages.CLIENT_MESSAGES["hello"]`: a newer client is refused for its fields, not its version.** `_VERSION`'s comment says "any version is read as a number first, so a newer one gets bad_version". In fact the whole hello schema runs first. Verified: `{"type":"hello","protocol":1,"token":"abc","caps":[]}` gives `unknown_field`, and protocol 1 with an 80-char token gives `bad_shape`. Only a v1 hello with v0's exact shape gets `bad_version` (the `hello_newer` fixture). Failure scenario: protocol v1 adds a hello field, and the v0 host tells the user "unknown_field" when it should say "version mismatch". That breaks "Readers refuse versions they don't know, loudly", by name, and it is unlike the frame path, which reads `protocol` first. Fix (unverified): read `protocol` with `read_version` before the hello schema, and add a fixture for a newer hello carrying an extra field.

**S6. `refusals.RefusalCode`: wire codes outside the owner vocabulary.** Tile §3.4's `refusal.codes` marker is the owner. This branch adds `bad_text`, `bad_token`, `token_in_use` and `host_only`, and sends `bad_token`/`token_in_use`/`busy` as `error` replies and close reasons. It also sends `missing_field`, `bad_version`, `bad_identity_key` and `over_budget` in frame refusals and `error` replies. None of these is in §3.4, whose "time refused (role)" row names no code. `refusals.py`'s own docstring says "the protocol (step 7) … add producers, not codes", and this branch breaks that. The lint can't catch it, because `lint_contracts` ties markers to docs only. Fix: add the codes to §3.4's table and marker, with stage, reply and logged columns, or rule otherwise.

**S7. The frame header's contract values live only in code.** §4.1 lists "grids (each with shape, cell size and origin)". It does not say that:
- `origin_um` is **[x, y, z]** while `shape` is **[nz, ny, nx]**, in the same grid object (`frame_header.GRID`, `WireFrame.origin_um`);
- units are µm;
- the key is `catalogue`;
- `compression` is `"none"`;
- tables are `{name, required, rows}`, with no integer key column, although §4.1 says "an integer key column";
- each array carries a full channel and an `of`;
- the hash covers the carried channels in order, so a server that later sends a subset, or table columns, must announce a different welcome hash.

`docs/generated/protocol.md` gives names and converters but no axis order or units. Failure scenario: the next consumer (`IsoCamera.to_godot`, or step 5a's encoder) reads `origin_um[0]` as z, following the shape's order. Fix: put the axis order and units in §4.1, or name the generated artifact as the owner of these fields.

**S8. The mirrored limits have no shared fixture.** MAX_GRIDS 8, MAX_TABLES 16, MAX_ARRAYS 64, MAX_EXTENT 65535, MAX_HEADER_BYTES 64 KiB and the identity limit of 64 chars are copied into `frame_decoder.gd`/`wire_fields.gd` by hand. The catalogue copy has a hash test; these copies have none. The frames manifest has no `over_budget`, `bad_identity_key` or `out_of_range` fixture: its codes are bad_shape 14, bad_json 9, accepted 5, unknown_field 4, bad_version 4, unknown_kind 4, not_int 3, missing_field 3. My probes show the two sides agree today, but nothing keeps them agreeing. Fix: add edge fixtures (8 vs 9 grids, extent 65535 vs 65536, a 64- vs 65-char name, negative tick).

## NIT

- **N1** `messages.CLIENT_MESSAGES["time"]`: the key `op` and its words `pause/resume/set_scale` are code-only. Tile §3.3 writes `pause | resume | set_scale` with no key name, and `scale` is an unbounded `Real` (ceilings deferred, which is fine).
- **N2** `replies.welcome` and `replies.error` are hand-built dicts, outside the in-code registry that boundaries §9.1 makes primary, and absent from `docs/generated/protocol.md`. `protocol`, `catalogue_hash` and role words `host`/`guest` are not in §4.1. The client never checks `welcome.catalogue` against its own V0 or against `catalogue_hash`, and has no welcome fixture; only the live Godot test covers it.
- **N3** §4.1 says each channel's `unit` comes "from the closed vocabulary". The code holds a unit to the vocabulary only by equality for known channels, and lets any identity through on unknown optional ones (`SMOKE`'s `kg_per_m3`). The reasoning is sound (frame_header docstring), but the owner should say so.
- **N4** `WireCatalogue.catalogue_hash` is a second canonicaliser (`JSON.stringify`). It matches c14n-1 only for ASCII strings, ints and bools, and §4.1 says "one canonicaliser". It is test-only today; mark it as such, or check its domain.
- **N5** No reader probes `temperature_c` (f16) values. Python only round-trips its own bytes, so the f16 layout across languages (later `FORMAT_RH`) has no golden yet.
- **N6** O60 and O62 name §9.1 as owner section, but only O59's line changed there. §9.1 still doesn't say the server's JSON is integers-only or how the client codes a float literal.
- **N7** `frame_decoder.gd::_header`: `non_integer_keys.has("protocol")` matches a float under any nested key named `protocol`, which gives `bad_version` where Python would give `unknown_field`.

## Checked, no finding

- Axis order [nz,ny,nx] with x fastest: both sides use index x + nx(y + ny·z); the asymmetric fixture's corner probes and the x=3, z=1 offsets are checked on both.
- The u32 header length is LE on both sides.
- dtype byte sizes agree.
- `[num,den]` rationals agree, as do the raw⇒1/1,0/1 rule and den > 0.
- The extension rule's order (grids, then tables, then arrays; ignored names in header order) agrees.
- The duplicate-name, no-`cells`, grid-shape-differs and layout tiling checks agree.
- O59 pin: 2⁵³−1 accepted; 2⁵³ and 2⁵³+1 refused, on both sides and in both fixture sets.
- Stage 1 refuses `5500.0`, `1e3` and `true` as `not_int`.
- Lone lead and trail surrogates: Godot's parser refuses them ("unpaired trail surrogate", measured).
- Depth 32 and 5,000 agree.
- The buffer caps match §4.3.
- Hello is sent with integer `protocol`.
- The manifest's client set is correctly Python-only (Godot never decodes client messages). §9.1's golden-rejection list (NaN, 1e400, repeated key, oversized, unknown field) is covered for both readers by frames and json together.
- The commit claims "every frame and JSON fixture reaches the same outcome and code in both decoders" are true for the fixtures as committed. The overreach is in the docstrings (S4) and in the json set's claim (S3).
