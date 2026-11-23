# Architecture lens, delta round 2: phase1/protocol (88d7787 ... cde7634)

Reader: Architecture. Read: CLAUDE.md, docs/code_review.md, delta1_architecture.md, O62–O66, the fold's diff
(`git diff 88d7787 cde7634`) of src/, scripts/wire_{fixtures,frames,texts}.py, pyproject.toml, client/addons/engine/net/*,
the four designs, docs/plans/{checklists,foundations_plan}.md.
Ran, in a copy at <scratchpad>/delta2/architecture/tree (each mutation restored):
- `lint-imports --contract network-lane-off-the-world` on the tree (KEPT), with `import simcore.core.applier` added to
  server.py (BROKEN), and with `import simcore.protocol.encoding` added (KEPT: no indirect path to the world).
- `schemas_within` without its `MapOf` line: `test_formats.py::test_content_stores_time_in_seconds_never_ticks` red.
- `godot_check.check` on the copy's client with `WireJson.server_rules` applying `not_int` before the version:
  `client-tests: FAIL 3 failure(s) in 89 tests`; unmutated: no findings. HOME was inside the scratch work dir.
- `wc -w` of the four designs at origin/main (d6dcbeb), 88d7787 and cde7634.

Counts: fold table: fixed 8, deferred (accepted) 2, open 3. New: BLOCKER 0, SHOULD-FIX 2, NIT 5.

## Fold table

| # | Status | What I checked |
|---|---|---|
| SF-1 | fixed | `schema.py::schemas_within` unwraps `ListOf`, then `MapOf`, then `Nested`/`Tagged`. The types bound the nesting (`Item = Nested \| Tagged`, `MapOf.value: Nested`), so the walk is complete today. `test_formats.py::_walk_fields` now uses it, and a `MapOf` case was added. **Mutation red** (above). |
| SF-2 / A6(a) | fixed | `WireJson.server_rules` is the one client site: `FrameDecoder._header` and `NetSession.on_text` both call it, version first. `parse_server` is gone. **Mutation red in Godot** (3 failures). |
| SF-3 | fixed | The close rule is only in client_rendering §4.3. boundaries §5.3 and tile §3.4 link to it. Integers-only with its codes is only in boundaries §9.1, which O62's row names, and client_rendering §4.1 links to it. grep finds no other restatement. |
| SF-4 / A6(b) | **open** | Retargeted to "this step's `time_decision`", but step 7's Remaining list still builds no `time_decision`. grep: checklists.md has the word only in this deferral line, and src/ only in a server.py docstring. Half my fix (add the item) was not done, so the trigger still names nothing that is built. |
| N1 | deferred, accepted | The B25 item in step 7's Remaining list now names `NetClient`'s `MAXIM_OVERDRIVE_TOKEN` variables. Trigger: the second engine file. |
| N4 / N-3 | **open** | frame_decoder.gd now defers to "grammar.py's (its module docstring lists them), the one statement of them". grammar.py was not touched, and its list still omits `integers_only`, which `_header` applies between checks 2 and 3 (grammar.py:124). So the one statement the client now cites is missing a step. |
| N5 | deferred, accepted | The shipped-path item reads the hello deadline and the caps from `data/server/`. |
| N-1 | fixed | The commit message corrects tile's count to 5389. |
| N-2 | fixed | foundations_plan.md §5 dropped the ZWNJ/ZWJ line. |
| N-4 | fixed | Both cut tests-to-write are restored to step 7's list. |
| N-5 | fixed | `NetSession.PROTOCOL = FrameDecoder.PROTOCOL`. |
| N-6 | **open (partly fixed)** | Error codes and close reasons are now held to `CODE`'s shape, which fixes that half. `refusal` still takes `"closed %d"` prose, and the close code isn't held apart, so a code and prose still share one field. |
| N-7 | fixed, with residue | The checklist retargets C3 to this step's `intent_result`. The new pyproject comment says "step 5a hands messages to the simulation lane", and server.py's docstring says the replies "join with step 5a". See N-a. |

Unchanged and still accepted: A7, A8, C3.

## Requested checks

- **The `network-lane-off-the-world` contract** is a sound import fence. It fails when broken and is pinned by
  `test_tooling_config.py`. It is narrower than the checklist claims (N-a).
- **`schemas_within`** is in the right place: the core owns the walk, and the tick rule and the tests share it.
  Registering it in `lint_gates._SCHEMA_DESCRIPTIONS` is correct.
- **`WireJson.server_rules`:** one owner, and the order matches `grammar._header`. Residues are in N-d.
- **wire_frames.py / wire_texts.py split:** frame builders, text sets and the assembler. It is reasonable, but uneven
  (N-b).
- **U+0000 in boundaries §9.1:** it has one owner (no other design states it), and the budget holds. boundaries has
  10748 words at origin/main and 10747 at HEAD; client_rendering 3740 → 3727, tile 5408 → 5386, world_v2 5452 → 5404.
  The attribution is wrong (SF-A).
- **Deferrals added:** guest text's Unicode-version dependence (trigger: the first logged speech, `phase1/agents`)
  and the pre-hello connection cap (trigger: Phase 5 guests). Both have a reason and an owned trigger, so I accept
  both. The C3 retarget is accepted. A6 is not (SF-4 above).

## New findings

### SF-A. The U+0000 rule is cited to an owner ruling that doesn't contain it
**Location:** docs/design/boundaries.md §9.1 ("wire text never holds U+0000, which a Godot string can't (O63)");
docs/design/decisions/boundaries.md O63; src/simcore/protocol/strict_json.py::_check_value, `_check_text`;
wire_json.gd::_escape.
**Defect:** O63 rules a strict GDScript parser and printable-ASCII names. It says nothing about U+0000. The commit
calls the rule "my contract call, flagged to the owner", but the only flag is the commit message. No decision row
holds it, and no row is marked as the author's or as pending. CLAUDE.md requires a status the author sets to be
marked as the author's, and the one-owner rule keeps contracts in decision records.
**Failure scenario:** the owner reads O63's row, which is the record §9.1 cites, and never sees the rule. Later a
save reader or a guest-speech relay that needs U+0000 (or rejects it differently) is designed against O63's text,
and the wire refuses with `bad_json` for a reason no decision states. If the owner rejects the call, nothing records
that it was ever pending.
**Fix:** add the clause to a decision row marked "author, 2026-11-22, awaiting the owner" (an O63 amendment, or a new
O-row), and cite that row in §9.1. This costs no design words.

### SF-B. The client's cap on server text is a cross-module contract that lives only in GDScript
**Location:** client/addons/engine/net/net_session.gd::MAX_TEXT_BYTES (cut from 256 KiB to 64 KiB, "the server's
own inbound cap"); scripts/wire_fixtures.py::LIMITS (has `max_header_bytes`, but no text cap);
src/simcore/protocol/strict_json.py::encode (no outbound size bound).
**Defect:** the server's encoder depends on this value, since it must never write a text message larger than the
client reads. No design states it, the manifest doesn't carry it, and the server doesn't bound its output. The
justification also mixes up two directions: 64 KiB is the client→server inbound cap (client_rendering §4.3), while
this is the server→client cap. CLAUDE.md: "if another module depends on a value, it is contract".
**Failure scenario:** step 7's Remaining work adds `tick` as JSON with integer columns (DC-S9), `welcome`'s maps and
the `regions` message. A `tick` carrying fuel tables at the world limits, or a large map's `welcome`, passes 64 KiB.
The server sends it without complaint, the client ends the session with a refusal, and no test on either side sees
the mismatch, because the shared manifest doesn't hold the number.
**Fix:**
- state the server→client text cap in client_rendering §4.3 beside the 4 MiB frame buffer;
- add it to `LIMITS` so Godot's constant is held to it, as `max_header_bytes` is;
- have the server's reply encoder refuse past it, so an oversize `tick` fails in a server test, not in the client.

## NIT

- **N-a** The checklist's C3 line says "the import contract `network-lane-off-the-world` holds the server to it",
  and pyproject's comment says the same. The contract sees imports only. `Dispatch` is an injected callable that
  server.py:142 calls synchronously on the loop, so a game-built closure over `World` passes the contract and blocks
  the network lane, which is exactly C3's hazard. Say that the contract fences imports and that the deferred queue is
  the guard. Also align pyproject's and server.py's "step 5a" with the trigger, which is now step 7's
  `intent_result`.
- **N-b** scripts/wire_fixtures.py:
  - it imports the public builders through 14 one-name `from wire_frames import (x as _x)` blocks, private aliases
    that look like an artefact of the move. Import the names as they are;
  - `Fixture`, the type every set shares, lives in wire_texts.py;
  - the docstring says "Three sets", but `SETS` has four (`server`);
  - the assembler is still 474 of 500 lines, because the frame fixture sets (about 300 lines) stayed in it while the
    text sets moved out. The next frame group forces another split; moving the frame sets beside their builders
    would make the split follow one responsibility.
- **N-c** `strict_json._check_numbers` now also refuses U+0000 and lone surrogates in text, so its name no longer
  says what it checks.
- **N-d** `WireJson.server_rules(read, protocol, versioned: bool)`:
  - the boolean parameter changes the rule;
  - the precondition that `read.value` is a Dictionary is enforced only by a typed cast, which a third caller would
    hit as a script error. A refusal would be better.
  - The knowledge of which server messages carry `protocol` sits in NetSession (`type == "welcome"`). Consider a
    table of versioned types next to the helper.
- **N-e** `WireJson._double` and `_past_largest` hand-roll Python's float rounding at 10^308 (a 309-digit constant).
  Under O62 the client never accepts a float from the server, so the client gains only value parity on the shared
  corpus from this. Whether float value parity is a contract need, or the corpus could stop at "a float literal is
  refused or `not_int`", is worth one line from the author. This is the "stop hand-rolling after two rounds" pattern.
