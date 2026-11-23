# Architecture lens: phase1/protocol (origin/main aaebc1b ... HEAD 8beb6af)

Reader: Architecture. Read: CLAUDE.md, docs/code_review.md, client_rendering §4.1–§4.3, world_v2 §8, boundaries
§2.2, §5.3, §9.1, decisions O59–O62, checklist step 7, and the full diff of src/, scripts/lint_gates.py,
scripts/lint_inputs.py, pyproject.toml, tests/_imports.py, tests/test_determinism.py, client/addons/engine/net/*.gd.
Ran: `lint_sizes.check_sizes` over src/ and scripts/ (clean). No mutations.

Counts: BLOCKER 0, SHOULD-FIX 8, NIT 5.

## SHOULD-FIX

### A1. boundaries §2.2, the owner of the layer contract, is now stale
**Location:** docs/design/boundaries.md §2.2 ("The layers, as built"), against pyproject.toml `[[tool.importlinter.contracts]] layers`.
**Defect:** §2.2 says it owns the order ("five, bottom to top `simcore.core` < `simcore.adapters` < `simcore.protocol` <
`simcore.verify` < `maxim_overdrive` ... This order is the contract"). It also lists "Not built: ... `engine.protocol`'s
wire codec ... and `engine.host`". The branch adds `simcore.host | simcore.verify` to the contract and updates
CLAUDE.md's layout line, but leaves §2.2 alone. The only boundaries.md edit is one phrase in §9.1. So the design that
owns the contract contradicts the code and CLAUDE.md.
**Failure scenario:** a later step reads §2.2 to place a module, learns that host is unbuilt and that verify sits
directly under the game, and puts the pacing loop somewhere else, or "restores" the five-layer contract. The doc
lint can't see it, because B36 covers prose restatements and only review holds those.
**Fix (unverified):** edit §2.2's "as built" paragraph and its "Not built" list in place (net word change about
zero, so O22 holds).

### A2. Handshake refusals ride on the WebSocket close reason, a new wire contract that no design states, and the client's `refusal` mixes codes with prose
**Location:** src/simcore/host/server.py::_Host._refuse, ::_Host._hello and ::_Host._serve;
client/addons/engine/net/net_client.gd::_on_closed.
**Defect:** the fix for Godot dropping the error packet is to repeat the refusal code as the 1008 close reason. That
is a reasonable mechanism: RFC 6455 close reasons are a real channel, and Godot's `get_available_packet_count`
returns 0 once the peer is not OPEN. But it is now a contract between server and client, and it lives only in two
code comments (net_client.gd and test_host.py:177), not in client_rendering §4.1/§4.3 or boundaries §5.3. The
contract is also only partly kept. `_refuse` writes a code (`bad_token`, `bad_version`, ...), but the other closes
write prose: "hello first", "hello only once", "client frames are text" and "hello first, within the deadline".
`_on_closed` copies any non-empty reason into `refusal`, whose comment calls it a code ("an error the server sent,
what this client refused, or closed <code>").
**Failure scenario:** a client whose hello is slow (a stalled main thread past `hello_deadline_s`) ends up with
`refusal == "hello first, within the deadline"`. Whatever later maps `refusal` to UI text through the refusal
vocabulary (tile §3.4) finds no such code. A second client author (or the Godot upgrade branch) reading only the
design never learns that the close reason carries the code.
**Fix (unverified):** state the rule in its owner section: every server-initiated close carries a `RefusalCode` as
its reason, and the error reply is advisory before a close. Make the four prose closes use codes. Record the Godot
behaviour as a §9 probe in tools/godot_probes (B26), so an engine upgrade re-checks it, instead of only
test_godot_net.py.

### A3. O61's and O62's rules are owned by decision rows; the design sections those rows name don't state them
**Location:** docs/design/decisions/boundaries.md O61 (owner column "§5.3") and O62 (owner column "§9.1");
docs/design/boundaries.md §5.3 and §9.1; client_rendering §4.1 ("JSON numbers read back as floats [ran]: integers
... are cast with `int()`").
**Defect:** CLAUDE.md, "One owner per contract": a contract is stated in one design section, and decision tables are
records, not designs. O61's character rule (ZWNJ/ZWJ only between visible characters, everything else in Cf refused,
NFC before the cap) and O62's rule (the server writes integers only, and the client refuses any literal with
`.`/`e`/`E` as `not_int`) appear only in the decision rows, code comments (text.py, strict_json.py, wire_json.gd,
frame_decoder.gd) and the checklist. §9.1 still says only "pinned below 2⁵³". client_rendering §4.1 still describes
float read-back with no integers-only rule. O59 is the only one of the four whose substance reached its owner section.
**Failure scenario:** step 5a adds `tick` with "scales". Its author reads §4.1 ("JSON with integer columns only") and
§9.1, never sees O62's client-side `not_int` rule, and writes a decoder for `tick` that doesn't refuse `2.0` (see A6).
The server and client then disagree on a fixture nobody wrote.
**Fix (unverified):** move each rule's one-sentence substance into its named owner section (replacing text, so the
budget holds), and have the decision rows and comments point there.

### A4. Frame-header contract: two design owners disagree, and the catalogue-hash semantics leave welcome's catalogue unread by the client
**Location:** src/simcore/protocol/grammar.py::encode_cells and ::decode_frame;
src/simcore/protocol/replies.py::welcome; client/addons/engine/net/net_client.gd::_on_frame;
world_v2 §8 vs client_rendering §4.1.
**Defect:** world_v2 §8 says frames are self-describing: each channel carries dtype, units, encoding and `required`.
client_rendering §4.1 says the header carries, per array, "name, dtype, offset, size and uncompressed size" plus the
catalogue hash, and that the catalogue (with `required`) comes in `welcome`. The branch builds both: a full channel
description in every array, and a hash. That leaves the hash's meaning ambiguous:
- `welcome` announces `catalogue_hash(describe(V0))`, the whole catalogue;
- `encode_cells` stamps `catalogue_hash(describe(<channels this frame carries>))`;
- `decode_frame` and `FrameDecoder` require the two to be equal.
NetClient never reads `welcome["catalogue"]`. It checks frames against its hard-coded `WireCatalogue.v0()`, and the
hash only checks two server-produced values against each other. The fixture generator papers over this:
`scripts/wire_fixtures.py::_announced` sets each fixture's "welcome" hash to whatever the frame's header states.
**Failure scenario:** when a frame legitimately omits an optional channel the catalogue declares (an optional
channel only sent while a fire burns, say), its hash is over a subset. It no longer matches welcome's, and both
decoders refuse a valid frame as `bad_version`. Separately, welcome's catalogue is dead weight on the shipped client,
so a second producer of channel identity can drift with no consumer noticing. world_v2's "registry version"
(an optional channel bumps it) has no wire field. The hash is apparently standing in for it, but no design says so.
**Fix (unverified):** decide in one owner section (client_rendering §4.1, citing world_v2 §8) whether the hash
covers the catalogue or the frame's channels, and whether frames carry full descriptions. Then either hash welcome's
catalogue in every frame, or drop the hash check in favour of per-frame identity. Add a fixture for a frame that omits
an optional catalogue channel.

### A5. `Schema(wire=True)`: a flag that routes around a core rule, and the core now knows about "the wire"
**Location:** src/simcore/core/schema.py::Schema.wire and `__post_init__`; src/simcore/protocol/messages.py (kindle);
src/simcore/protocol/frame_header.py:80.
**Defect:** the rule "content stores time in seconds, never ticks" was enforced by `Schema` for every schema. The
branch adds a boolean that turns it off. CLAUDE.md lists "a flag that routes around broken behaviour" as a band-aid.
Here the behaviour isn't broken; the rule is in the wrong owner. It belongs to content formats, not to every schema.
The core's generic reader now carries a transport concept, and nothing stops a content `Format` from passing
`wire=True` (test_wire.py:416 shows it is accepted on any schema).
**Failure scenario:** a step 5a/9 author hits the ticks refusal on a save or scene schema, sees `wire=True` in the
same module, sets it, and a content file authors ticks, the exact thing tile §3.2 forbids. Nothing goes red.
**Fix (unverified):** enforce the no-ticks rule where content formats are declared (`Format`, or the format
registry test_formats.py walks), and drop the flag.

### A6. Integers-only on the client is a per-call-site check, and client→server `scale` is a float that O62's server can't echo
**Location:** client/addons/engine/net/wire_json.gd::parse ("the caller decides"); net_client.gd::_on_text (lines
76–77); frame_decoder.gd (line ~90); src/simcore/protocol/messages.py::CLIENT_MESSAGES["time"] (`scale: Real()`).
**Defect:** (a) `WireJson.parse` only lists `non_integer_keys`, so each caller has to apply O62's refusal itself.
CLAUDE.md's band-aid list includes "a fix that has to be repeated at each call site". Two callers do it today, and
the `tick`, `intent_result` and `regions` readers are scheduled next. (b) O62 makes every number the server writes an
integer, yet stage 1 accepts `time.scale` as `Real`. A client may send `2.5`, and the `tick` message has to report
"scales" (§4.1) as integers.
**Failure scenario:** (a) step 5a adds a `tick` reader that calls `WireJson.parse` and forgets the check, so
`"tick": 5.0` is drawn. Nothing fails, because the fixtures only cover the two existing callers. (b) `set_scale 2.5`
is granted at stage 1. Then the host either rounds it silently in `tick` (the client shows 2 or 3, not 2.5) or
`encode` raises `ValueError` mid-session, depending on who writes the dispatch.
**Fix (unverified):** (a) make the integers-only refusal the parser's default, with the frame header's
protocol-first precedence as an explicit parameter. (b) make `scale` a `Whole` or a `[num, den]` pair now, while
`time_set_scale.json` is the only golden that would change.

### A7. The converters split follows chronology rather than responsibility, and it turned the closed `Converter` union into an open Protocol
**Location:** src/simcore/core/schema.py::Converter; src/simcore/core/converters.py.
**Defect:** schema.py hit its limit and kept ten converters (Real, Whole, Vector, Rgb, Text, Identity, Nested,
Tagged, ListOf, MapOf). The five new ones (Wholes, Choice, Flag, Digest, Opaque) went to converters.py, whose
docstring says "converters beyond schema's". `Vector` and `Wholes`, or `Whole` and `Wholes`, are one concern split
across two files by date. The charter asks of a size-limit split: "split along a responsibility, or ... at the line
count?" This one is the latter. To avoid a circular import, `Converter` went from a closed union (only these
converters exist, which mypy checks) to a structural `Protocol` that any object with `convert`/`bad` satisfies. That
weakens an invariant the type held.
**Failure scenario:** a later author adds an ad-hoc converter class in a protocol module. It satisfies the Protocol,
is never registered in lint_gates (the registry rows are hand-listed per module), and bypasses the gate-registry
coverage the closed union implied. A reader looking for "the whole-number converters" has to check two modules.
**Fix (unverified):** move every converter into `converters.py` (schema.py keeps Field, Schema, Tagged, Format and
read_version), so the union can stay closed in one place.

### A8. The protocol layer defines a second typed action vocabulary outside `engine.intents`, under the name "stage 1"
**Location:** src/simcore/protocol/messages.py::Move, ::MoveTo, ::Kindle, ::Time and the docstring's "stage 1";
boundaries §5.3 ("stage 1 is typed parsing in `engine.intents`"; "NPCs, LLM results and clients pass one gate") and
§2.2 layer 5b.
**Defect:** typed client actions now live in `simcore.protocol` (layer 7c), while the design puts typed intents and
stage-1 parsing in the core's `intents`, one gate for NPCs and clients. The branch calls the wire-shape check
"stage 1" and its fixtures "stage-1 rejection fixtures". It defers the limit checks that §5.3 assigns to stage 1 to
step 5a's `intent_result`. Neither the checklist nor a known gap says that `Kindle`/`Move` must later fold into, or
translate into, `simcore.core.intents`.
**Failure scenario:** at step 5b, `move` gets a core `Action` type. Two typed `move` vocabularies now exist, protocol's
`Move(seq, dir)` and the core's, with two "stage 1"s. A field added to one is missed in the other, which is the
two-owner drift CLAUDE.md forbids, and NPC and player moves no longer pass one gate.
**Fix (unverified):** rename this layer's check to "decode" (shape and types) in messages.py, the fixtures' names and
the checklist. Add a checklist item under 5a/5b: client messages become `simcore.core.intents` actions there, and
protocol keeps no action types.

## NIT

- **N1. The engine half names the game's environment variable.** client/addons/engine/net/net_client.gd::TOKEN_ENV,
  ::TOKEN_FILE_ENV (`MAXIM_OVERDRIVE_TOKEN*`). `addons/engine/` is meant to be game-free (B25, still open on the
  checklist). The token's source belongs in `game/`, which passes it to `open()`.
- **N2. The scan that justifies the narrow entropy exemption is blind to asyncio's clock.**
  tests/test_determinism.py::NOT_SIMULATION, BANNED_MODULES. Exempting only `tokens.py` is the right, narrow root
  choice (the original plan exempted all of `simcore/host`). But the "rest of the host stays scanned" assurance is
  weaker than it reads: `server.py` already reads the monotonic clock through `asyncio.wait_for`, and the scan doesn't
  flag it, because `asyncio` isn't in `BANNED_MODULES` outside the core. The pacing loop's natural clock
  (`loop.time()`, `asyncio.sleep`) will pass the same way. Record it as a B14 row before the pacing loop lands.
- **N3. Collaborator invariants not pushed into types.** src/simcore/host/server.py::HostConfig takes `sessions`,
  `shape` and `dispatch` positionally (no `kw_only=True`). src/simcore/host/sessions.py::Decision allows
  `Decision(True, HOST_ONLY)`; the "None when granted" rule is a comment. `Sessions(cap=...)` accepts 0 or a negative
  number.
- **N4. The decoder check order is restated in two comments.** grammar.py's module docstring and frame_decoder.gd's
  header both list the six checks. The shared fixtures hold their outcomes and codes, but not the prose. Have one cite
  the other, or both cite the generated docs/generated/protocol.md.
- **N5. Tunables in code.** `hello_deadline_s = 5.0`, the 8-guest cap and the session cap (passed in by tests only)
  are engineering values with no `data/` home. client_rendering §4.3 already puts the client cap in `data/server/`.
  Acceptable until the shipped path exists, but say so on the checklist's shipped-path item.

## Checked, no finding

- **Layering.** `simcore.host | simcore.verify` matches boundaries §2.2's table row 8 (siblings, independent). Verify's
  forbidden list gains `simcore.host`. The skip-layer contract now covers host, and host imports only the protocol,
  `core.refusals` and itself. `core.text` and `core.converters` are pure (no IO), and the SEM membrane is forbidden
  from both. strict_json is the only protocol module allowed `json` (tests/_imports.py). The server is registered as
  an input gate (lint_inputs) and its callables are in the gate registry.
- **The text.py split** is along a real responsibility (character rules for names and for guest text), unlike A7.
- **Capability without a caller.** `start`, `encode_cells`, `player_text`, `HostOnly`/`TimeAuthority` and `NetClient`
  run only under tests. The checklist's new last item says so plainly, and no commit claims a shipped-path result.
  Server-side `decode_frame` has no shipped consumer either; it is the reference reader for the fixtures and the
  future save. Disclosed enough. No BLOCKER.
- **Design review before code.** The host, sessions, HostOnly and the handshake were reviewed in boundaries §5.3 and
  §2.2. O59–O62 are owner rulings. The only new contracts without a design are A2 (the close reason) and the
  frame-hash semantics (A4). Both are SHOULD-FIX for one owner; neither is a new subsystem.
- **Godot packet drop.** Unverified by me (no Godot run). It is consistent with Godot 4's WSLPeer returning no packets
  once the peer is not OPEN. Note that `poll()` returns before draining when CLOSED, so the client code alone couldn't
  tell that apart. The commit says it was measured separately.
- **Sizes.** `check_sizes` is clean over src/ and scripts/. wire_fixtures.py is at 475 lines, near the 500 limit.
- **The client's catalogue copy** (`WireCatalogue.v0()`) is a second copy of V0, held by a hash-equality test against
  the server's. That is acceptable for defence in depth.
