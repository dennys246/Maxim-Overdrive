# Architecture lens, delta round 1: phase1/protocol (8beb6af ... 0c7e6e6, plus 88d7787)

Reader: Architecture. Read: CLAUDE.md, docs/code_review.md, round1_architecture.md, O59–O66, the fold's diff of
docs/design/{boundaries,client_rendering,tile_and_client,world_v2}.md, docs/plans/{checklists,foundations_plan}.md,
docs/standards_backlog.md, src/simcore/{core/schema.py,core/converters.py,core/refusals.py,protocol/*,host/*},
client/addons/engine/net/{net_client,net_session,wire_json,frame_decoder}.gd, tests/test_formats.py,
tests/test_determinism.py.
Ran: `scripts/lint_standards.py --base origin/main` (PASS, 0 findings); `wc -w` on the four designs at origin/main,
8beb6af and HEAD; three mutations in a scratch copy (<scratchpad>/delta1/architecture/tree), each restored; one
in-process probe of `Format`. No Godot run.

Counts: fold table: fixed 9, deferred (accepted) 2, open 4 (one is a deferral not accepted). New: BLOCKER 0,
SHOULD-FIX 4, NIT 7.

## Fold table

| # | Status | What I checked |
|---|---|---|
| A1 | fixed | boundaries §2.2 names `simcore.host` \| `simcore.verify` as siblings, lists `engine.host` and `engine.protocol` as built, drops them from "Not built"; matches pyproject's `layers` contract and CLAUDE.md. Prose; no test applies. |
| A2 | fixed | Every server close in server.py goes through `_refuse` with a `RefusalCode` (`hello_first` for the deadline, a non-hello first and a second hello; `bad_shape` for binary). Rule in client_rendering §4.3. **Mutation:** `_refuse` closing with reason `"x"` turns `test_host.py::test_anything_but_a_hello_first_gets_an_error_and_a_close_with_its_code` red. Godot's drop is gated by `test_godot_net.py` on every gate run. An upgrade branch runs the gate, so that covers what a §9 probe would. I did not run it. What is left of the "codes mixed with prose" half is N-6 below. |
| A3 | fixed, with a new defect | O61/O65's text rule is in the §5.3 gate table, and O62/O63 are in §9.1 and client_rendering §4.1. The fold wrote O62's rule into two owners (SF-3). |
| A4 | fixed | O64: `encode_cells` takes the catalogue and hashes it whole; `_announced` no longer rehashes per frame; `optional_channel_omitted` is in the manifest; NetSession compares welcome's hash with its build's. **Mutation:** going back to the per-frame subset hash turns `test_wire.py::test_the_committed_fixtures_are_what_the_script_makes` red. Only the regeneration check goes red, but a regenerated manifest would then mis-expect the omitted-channel fixture, so this holds. |
| A5 | fixed, with a regression | `Schema.wire` is gone and the rule moved to `Format.__post_init__` through `_tick_fields`. **Mutation:** disabling the check turns `test_formats.py::test_content_stores_time_in_seconds_never_ticks` and `::test_the_tick_rule_reads_words_not_letters` red. But the walker skips `MapOf` (SF-1). |
| A6 (a) | **open** | The commit says "one helper on each side". In fact `WireJson.parse_server` turns only a float `protocol` into `bad_version`. `NetSession.on_text` applies `not_int` itself, and `FrameDecoder._header` calls `WireJson.parse` and reimplements both checks. That is still three call sites, two of them diverging, and it already breaks the version-first rule (SF-2). |
| A6 (b) | **open (deferral not accepted)** | Listed with the trigger "step 5a's `time_decision`". Neither step 5a's checklist nor step 7's "Remaining" list builds a `time_decision` (grep: the word appears in checklists.md only in this deferral). A trigger no step owns never fires (SF-4). |
| A7 | deferred, accepted | The reason (sim-replay edits scene.py and the loaders) and the trigger (that branch's merge) are real; `phase1/sim-replay` exists. The fold added `WireName` to converters.py, which widens the split by one, but it is consistent with the deferral's target (everything into converters.py). |
| A8 | deferred, accepted | Step 5b's checklist has "`move` and `move_to` as ordinary intents (AR-B2)", so the trigger is owned. The rename half of my fix ("stage 1" → "decode") was neither done nor deferred: CLAUDE.md still reads "decode and stage 1 of client messages". The fold into `core.intents` will settle the name, so I accept it with the deferral. |
| N1 | open | `NetClient.TOKEN_ENV` / `TOKEN_FILE_ENV` still name `MAXIM_OVERDRIVE_*` inside `addons/engine/`. The fold neither fixed nor deferred it. The checklist's B25 line is generic. |
| N2 | fixed | `async_clock_findings` scans `src/` for asyncio's clock, with `server.py`'s `wait_for` as the one allowance. Unit tests cover alias, `from` and attribute forms. Checked by reading (the author reports a planted `asyncio.sleep` went red). |
| N3 | fixed | `HostConfig` is `kw_only=True` (it was not at 8beb6af); `Decision.__post_init__` refuses a granted decision with a reason; `Sessions(cap<1)` raises. |
| N4 | open | Both check-order comments remain, and they have already drifted: frame_decoder.gd's check 3 lists `not_int`, while grammar.py's list doesn't mention `integers_only` (applied between checks 2 and 3). This is the failure N4 predicted. |
| N5 | open | `hello_deadline_s = 5.0` and the caps still have no `data/` home, and the shipped-path checklist item doesn't mention them. |
| C3 (asked) | deferred, accepted | The trigger reads "step 5a's first reply that needs the clock", but no 5a item produces a reply. The real first reply is step 7's own `intent_result` (Remaining: "after step 5a's integer clock"). Accept, with N-7. |

## Requested checks

**One owner for the added contract text.** client_rendering §4.1 holds the header keys, O64 and the integers-only
codes. world_v2 §8 now links to it instead of restating, which is a clean fix. tile §3.4 adds the new codes to the
registered `refusal.codes` vocabulary, and lint_contracts passes. boundaries §2.2 owns the host layer, and tile §7
now links to it. Two rules ended up in more than one place (SF-3).

**Budgets (O22/O66), `wc -w`:**

| Document | origin/main | 8beb6af | HEAD |
|---|---|---|---|
| boundaries.md | 10748 | 10746 | 10736 |
| client_rendering.md | 3740 | 3740 | 3739 |
| tile_and_client.md | 5408 | 5408 | 5389 |
| world_v2.md | 5452 | 5452 | 5404 |

All four are at or under main. The commit claims tile is at 5380, but 0c7e6e6 and HEAD both measure 5389 (N-1).

**Were the cuts contract?**
- boundaries §1's survey was history, so that cut is fine.
- tile §9's decided questions: the crate values survive at tile line 43 and in the §6 table (σ_min 4.2/7.0), so that cut is fine.
- world_v2 §8's extension and bump rules: all present in client_rendering §4.1's "Extension and bumps", so that cut is fine.
- client_rendering §4.2's fixture list and the §10 row: scales and the asymmetric fixture are covered, but "a frame
  after an `imagine` (a new region)" is no longer named anywhere on step 7's checklist. It is a test to write, not
  contract, but it has dropped out (N-4).
- client_rendering §4.3's head-of-line note: the concept stays in docs/architecture.md, but its "*to measure*" item
  went without a checklist line (N-4).

**NetSession/NetClient split.** It is a sound responsibility split: NetClient owns the socket, buffers, hello and
close, and NetSession owns the meaning, is pure, and is unit-tested branch by branch. First refusal wins, and
`open()` makes a fresh session. Residues: `refusal` can hold `"closed <n>"`, which is prose and not a code (N-6);
`PROTOCOL` is declared in both NetSession and FrameDecoder (N-5); the integers-only rule is still split across
NetSession and FrameDecoder (SF-2).

**The tick rule's move from Schema to Format.** It is the right owner: wire schemas aren't Formats, so the flag could
go, and nothing in the core names the wire any more. The new walker is a second schema walker beside
test_formats.py's `_walk_fields`, and the two already disagree on `MapOf` (SF-1).

**The four deferrals.** A7, A8 and C3 are accepted. A6(b) is not (SF-4).

## New findings

### SF-1. `Format`'s tick rule doesn't descend into `MapOf`, so the material table is no longer checked
**Location:** src/simcore/core/schema.py::_tick_fields (it handles `ListOf`, `Nested` and `Tagged`, but not `MapOf`);
src/simcore/core/materials.py (`MapOf(MATERIAL_NAME, Nested(MATERIAL), ...)`).
**Defect:** before the fold, every `Schema` constructor checked its own fields, so `MATERIAL` was covered. Now only
`Format` checks, through a walker that stops at `MapOf`. The docstring says "at any depth", and that is false.
**Verified:** `Format('doc', 1, Schema((Field('m', MapOf(Identity(), Nested(Schema((Field('hold_ticks', Whole(0,10)),))), 4)),)))`
is accepted at HEAD. The same nesting through `ListOf(Tagged(...))` is refused.
**Failure scenario:** step 6's material table gains `ignition_delay_ticks`. Declaration passes, and content authors
ticks, the case tile §3.2 forbids. `test_no_shipped_format_has_a_field_counted_in_ticks` catches it only for formats
in `SAMPLES`, because its own walker does handle `MapOf`.
**Fix (unverified):** one structural walker in schema.py, used by both `Format` and the tests, so a new container
type gets both checks or neither.

### SF-2. Client integers-only is still applied per call site, and NetSession applies it before welcome's version
**Location:** client/addons/engine/net/wire_json.gd::parse_server, net_session.gd::on_text, frame_decoder.gd::_header.
**Defect:**
- `parse_server`'s comment says it applies O62 "as the server's readers apply it ... any other `not_int`", but the
  code refuses only a float `protocol`.
- `on_text` adds `not_int` for any float right after parsing, before `_on_welcome` reads `protocol`.
- `FrameDecoder` doesn't use `parse_server` at all.

client_rendering §4.1 says the check is "judged after the version".
**Failure scenario:**
- A welcome `{"type":"welcome","protocol":1,...,"x":1.5}` ends the session with `not_int`. §4.1 (and the frame path)
  gives `bad_version`, so a newer server is misreported to the player.
- Step 7's `tick` reader, following `parse_server`'s comment, calls it alone and draws `"tick": 5.0`.

No shared fixture covers server text messages, so neither decoder's tests see it. This is from reading the code; I
did not run it.
**Fix (unverified):** `parse_server` takes the version check as a parameter (or reads `protocol` itself) and then
applies `not_int`. All three callers use it.

### SF-3. The fold restated two of the contracts it wrote down
**Location:**
- the close-with-code rule: boundaries §5.3 ("A refusal is an `error`, then close 1008 with the code as its
  reason"), client_rendering §4.3 (the owner the §5.3 link names) and tile §3.4's new row ("then close 1008 with the
  code as reason");
- integers-only: boundaries §9.1 ("The server's JSON holds integers only (O62) ... strict parser of its own (O63)")
  and client_rendering §4.1 (the same rule, plus its codes and precedence). O62's owner column says §9.1, but the
  operative text is in §4.1.

**Defect:** CLAUDE.md, "One owner per contract": every other document links and never restates. B36 says only
review can see prose restatements.
**Failure scenario:** step 9's save reader or a protocol-1 change edits §4.1's precedence (say, `not_int` before the
version) and leaves §9.1 and the O62 row pointing at the stale copy. The next author reads the owner the decision
names and implements the old rule.
**Fix (unverified):** keep each rule in one section (§4.3; and §4.1 or §9.1, whichever O62's row names), and reduce
the others to a link. That is also a word cut.

### SF-4. A6(b)'s deferral trigger names a step item that doesn't exist
**Location:** docs/plans/checklists.md, step 7, "Deferred from the round-1 review": "trigger: step 5a's
`time_decision`".
**Defect:** `time_decision` appears in no step's build list, neither 5a nor step 7's "Remaining". tile §3.4 assigns
it to step 7.
**Failure scenario:** `time` replies land with `intent_result` in step 7's remaining work. Nobody reads a 5a trigger
there, `scale` stays `Real`, and `tick`'s "scales" either rounds silently or `encode` raises mid-session.
**Fix (unverified):** retarget the deferral to step 7's own remaining item (`time_decision` beside `intent_result`
and `tick`), and add that item to the list.

## NIT

- **N-1.** The commit message's word counts are wrong for tile (it says 5380, but it is 5389). The budget still holds.
- **N-2.** docs/plans/foundations_plan.md line 220 still lists "the guest-text gate's ZWNJ and ZWJ rule (step 7)" as
  open, though O61 and O65 decided it. The fold edited the same file.
- **N-3.** N4 carried over: the two check-order comments have drifted (see the fold table).
- **N-4.** Two tests to write were dropped from client_rendering without a checklist line: the post-`imagine` frame
  fixture, and the head-of-line measurement.
- **N-5.** `PROTOCOL` is declared in both net_session.gd and frame_decoder.gd. Make one constant, cited by both.
- **N-6.** `NetSession.refusal` takes any close reason verbatim, and `"closed <n>"` when there is none, so it still
  mixes codes with prose. It also accepts any `error.code` string unchecked. Keep a code, and hold the close code
  separately.
- **N-7.** C3's trigger should name step 7's `intent_result` dispatch, not "step 5a's first reply".
