# Docs-contracts, delta round 1: Wire integrity

Reviewer: Wire integrity lens, independent reader. Diff under review: `git diff c043920 c989b12` (7cfea02, the round-1
fold, and c989b12, the owner's round-1 rulings), plus the conflict resolution in `git show b1237ac`
(`docs/plans/foundations_plan.md`). Read-only; this file is the only write. Charter: `docs/code_review.md` (a delta
round on a design reviews the fold's diff, and Wire integrity also reads every section that uses a contract the diff
changes; fold status is the reviewer's, read from the tree).

## What was run

1. **A reference resolver, in memory, at HEAD (b1237ac) and at `origin/main` (34c20ee).** It reads every file with
   `git show <rev>:<path>`. Scope: `docs/design/*.md`, `docs/design/decisions/*.md`, `docs/plans/*.md`,
   `docs/roadmap.md`, `docs/architecture.md`, `docs/code_review.md`, `docs/standards_backlog.md`,
   `docs/lessons_maxim_in_games.md`, CLAUDE.md, and every `.py/.gd/.sh/.md/.txt/.yaml/.toml/.tscn` under `scripts/`,
   `tests/`, `src/` and `client/`. It matches `<doc>[.md] §N`, the plan's §2 abbreviations and the short forms
   (`tile`, `client`, `world`, `npcs`, `lanes`, `v2`, `realtime`), and bare `§N` (attributed to the last doc named
   earlier on the line, else the file's own doc; a decision record's to its design). Each is checked against the
   target's numbered headings at that revision.
2. Heading lists of every design doc, decision record, plan, the roadmap and `architecture.md`, HEAD against
   `origin/main`.
3. Row-by-row reads of `moves_3d_3e.md`'s "Round 1 fold" table against `world_v2.md` and `realtime_lanes_coop.md`
   at HEAD (both are records; neither changed except `world_v2.md`'s banner), and greps of every live document for
   citations of either record.
4. `lint_contracts.check_contracts` in memory on the tracked docs: returns `[]`.
5. 10-word shingles between `npcs_and_sem.md`, `boundaries.md` and `roadmap.md` (S4, S5 recheck).
6. `foundations_plan.md` rows 6 and 7 at `origin/main`, c989b12 and HEAD.

### Resolver output

| | origin/main | HEAD |
|---|---|---|
| References found | 1,901 | 1,589 |
| Unresolved | 70 | 88 |
| Unresolved at HEAD, line not unresolved at main | — | 26 |

I read all 26. **None is a real break; no reference regressed.**
- 15 are in `docs/plans/docs_contracts.md` (new on this branch, so absent from main): list continuations after a plan
  abbreviation (`IP §2.1, §4.2`; `FS §4.5–§4.6`; `C §6.2, §6.5, §7.3 and §12`; `C §2, §5.3–§5.5, §6.5 and §8–§10`;
  `T §1.3, §3 and §11`). Every target heading exists at HEAD.
- 3 in `contracts.md` (new lines from c989b12): `tile §2.3, §3.1 and §3.3`, `tile §3.1–§3.2`. Tile has all four.
- 2 in `boundaries.md` (lines 563, 656) and 1 in `world_model.md` (line 68, `§2.1), with these changes.`): line-wrap
  attributions to `npcs_and_sem.md` §6.6 and `world_v2.md` §2.1, both present.
- 2 in decision records: `decisions/fire_model.md` "ruled 2" (`cites §6.3` is tile's, present) and
  `decisions/world_model.md` D26 (`§10`, `§2`: WM §10 and FP §2, present). Both lines changed only by the status
  amendment (A7).
- 1 external: `npcs_and_sem.md`, Maxim's `thalamic_relay.md` §5.5.
- 1 is round 1's N5 (`npcs_and_sem.md:455`), unchanged.

No reference in `scripts/`, `tests/`, `src/` or `client/` is among the 26.

### Headings

Against `origin/main`, no numbered heading in any design doc, decision record, plan, the roadmap or `architecture.md`
is renumbered, removed or renamed. The differences are the planned ones: the unnumbered fold-table headings in
`boundaries.md`, `npcs_and_sem.md` and `world_model.md` became `## Review records`, and the new files
(`contracts.md`, `decisions/*.md`, `plans/docs_contracts.md`) add their own. Only two lint test fixtures name
`## Fold table:`, as synthetic input. `fire_model.md` §12 is back: its text at HEAD is identical to 5c054f6's and to
`origin/main`'s.

### The merge resolution

`foundations_plan.md` at HEAD: the step 6 row is byte-identical to `origin/main`'s (red-first in 6.1, from #34), and
the step 7 row is byte-identical to c989b12's (the links to C §4.1, T §3.3 and B §5.3). The other two differences from
main (line 16's exit link, item 2's worker environment link) are this branch's earlier steps, unchanged by the merge.
**The resolution is correct.**

## The copies out of superseded records

Each row of `moves_3d_3e.md` "Round 1 fold", read against the source at HEAD:

| Copy | Verbatim? | Owner right? | Note |
|---|---|---|---|
| v2 §2.1 sentence → WM §2 | rewritten as WM's own sentence, members unchanged | ✓ | the record's table and bullets left (D20 conflict), for the owner |
| v2 §2.4 "A `Region` keeps its authored footprint …" → WM §5 | ✓ word for word | ✓ | |
| v2 §2.2 choke-point sentences → WM §7 | ✓ the first two sentences; the third omitted | ✓ | the omitted "same substep" sentence conflicts with WM §6, for the owner |
| WM §8 "v2 §8 stands" → own sentence | rewritten, members unchanged | ✓ | |
| lanes §4.2 actor ids, lanes §5 `TimeAuthority` → B §5.3 | ✓ word for word | ✓ | the gate table's "(below)" now resolves for both rows, but see D-S1 |
| IL §4 handshake citation → B §5.3 | ✓ | ✓ | |
| `world_v2.md` banner | the only edit; 25 words (ruling 6) | — | see D-N3 |
| lanes §7 `seq` range → B §6.2 | ✓ word for word, "(W-F5; copied from …)" | partly | see D-S2 |
| B §9.3 CC3 paragraph → RM Phase 3 "Ids" | ✓ less "No major version is proposed", which RM's owner bullet already says | ✓ | both design copies now link |
| N §6.1 tier-A cells → OD ids | — (replaced by ids) | ✓ | |

The three `world_v2.md` §8 items homed in 7cfea02 (c989b12's parent):
- **Registry hash → B §6.3:** "Content digests of the scene, the registry (from `world_v2.md` §8), …". v2's sentence is
  "The intent log header hashes the registry and the material table"; the material files were already in B §6.3.
  Not verbatim but complete; the right owner (row 20).
- **Save grammar and digest → WM §8 F5:** "The save uses the same grammar, losslessly. It embeds the registry, the
  material table, the scene with its zones, and the placed imagined specs. Derived fields are recomputed on load and
  checked against a stored digest (from `world_v2.md` §8, less its retired 'tied to one rig's cell size', D20)."
  Verbatim less the retired clause, which is named. Right owner (row 26). See D-N1 for where it was inserted.
- **Heavy-mode test → `checklists.md` step 9, six fixtures → step 7:** the heavy-mode sentence is verbatim; the
  fixtures item names three of the six (as v2 does; v2 never named the other three). Both are tests to write, so a
  checklist is the right home under CLAUDE.md's contract rule. C §4.1 owns the refuse/ignore rule they test.

The rest of `world_v2.md` §8 is held live: self-describing headers and grids with cell size and origin (C §4.1, cell
frame row), the bump rules and `kind: delta` reserved (C §4.1, lines 91–92), `welcome`'s catalogue, zone list and
material table (C §4.1), `extinguish` retired (T §3.2). Lanes §7's rules are held too: the axis order and shared
encoding (C §4.1), two stages (B §5.3), one final reply per message (T §3.3's "Final reply" column), strict decoding
(B §9.1).

**What remains, live documents citing a superseded record:**
- `sem_stimuli.md:390` cites `world_v2.md` §2.6 for the antisymmetric ledger, whose owner is `fire_solid.md` §5.4 (row
  63). The author excluded it as another session's file; `origin/phase1/sim-clock` does change `sem_stimuli.md`.
- `verify_harness.md:5`, `:36` and `checklists.md:111` cite "`world_v2.md` row 2" (v2 §11's order-of-work row 2,
  "exact performance counters"): provenance for a to-do, not a contract. Acceptable.
- `checklists.md:213` and `:253` cite `world_v2.md` §8 as the source of the fixtures and the heavy-mode test:
  provenance. Acceptable.
- `checklists.md:26` still asks to "Amend `realtime_lanes_coop.md` §7's v0 client-message table", which §7 already
  records as done ("amended at the merge, DC-B2"). The same on `origin/main`; not this diff's.
- **Not held by any live document:** `realtime_lanes_coop.md` §5's joins-and-leaves bullet (D-S1). The two v2
  conflicts the author left "for the owner" (§2.1's table, §2.2's third sentence) are records that WM supersedes;
  they need no owner, but they are listed only in `moves_3d_3e.md`, not in rulings.md's "Not decided" (D-S3).

## Fold status of round 1's findings

**B1 — fixed.** `fire_model.md` §12 is restored, identical to 5c054f6 and to `origin/main`. The four review rows that
cite §12 resolve again. (One stale line inside it is D-N2, inherited from main.)

**S1 — fixed.** The `seq` range has a live home, verbatim, in `boundaries.md` §6.2 (line 436). Its scope is D-S2.

**S2 — fixed, one sub-item deferred.** Read from the tree: WM §2, §5, §7 and §8 no longer say "v2 … stands" or cite v2
as an owner (each is "from `world_v2.md` §N", provenance, with the text now WM's); `ip_and_licensing.md` §4 cites B
§5.3; B §5.3's table cells point to the copied bullets; `world_v2.md` has its banner. **Deferred:** `sem_stimuli.md`
§7.1's `world_v2.md` §2.6. Reason: the file is under change in `phase1/sim-clock`. Trigger: this branch's next merge of
`origin/main` after sim-clock merges, when the citation is repointed to `fire_solid.md` §5.4.

**S3 — open in part.** The thin-feature half is fixed: CLAUDE.md's thin-feature line now reads "(fuel objects excepted,
`docs/design/world_model.md` §1.1)" (ruling 4), which agrees with WM §1.1. The other half is untouched: CLAUDE.md's
"Reconstruct, decide at the point, integrate upward" paragraph still restates WM §3 (row 78) in full, and neither
rulings.md nor any record says it is out of scope. Round 1's fix asked for one or the other.

**S4 — fixed.** Roadmap Phase 3 "Ids" holds the paragraph; B §9.3 and N §8.1 link to it. Shingles B↔RM: 0.

**S5 — fixed.** The §6.1 residue is gone. Of 48 shingles N↔RM left, none is in §6.1: they are N §6.x's pid-receipt
text against OD-A18 and the offset test against OD-A2, present at c043920 and at `origin/main`, outside S5's scope.

**N1 — open.** `fire_model.md:422` still states the thin-feature exemption in full.
**N2 — open.** `docs_contracts.md` lines 4, 5, 157, 158 and 209 still say dc0e1aa; the moves files use 5c054f6.
**N3 — open.** `moves.md` lines 85 and 133 still say "uncommitted … until the owner commits".
**N4 — open.** No pointer to "intent kinds" in tile §3's lead.
**N5 — open.** `npcs_and_sem.md:455`'s bare `§6.6`.
**N6 — open.** `boundaries.md:571` and `npcs_and_sem.md:87` still both state the `dt_ticks` rule.

None of the NITs is recorded as rejected or deferred in a commit message or record, so open is what the tree says.

## New findings

### SHOULD-FIX

**D-S1. Joins and leaves have no live owner, and the fold's "(below)" says they do.**
- *Evidence:* `realtime_lanes_coop.md` §5, third bullet: "**Joins and leaves are records** at a tick, in the log.
  When a guest leaves, its intents that already have a tick apply and the rest are discarded. **When the host leaves,
  the world pauses** (a logged time decision) until the host token reconnects." No live document holds it (greps for
  "host leaves", "guest leaves", "world pauses", "reconnects" find only the records). The fold copied §5's handshake
  and `TimeAuthority` bullets and rewrote B §5.3's gate row to "Joins and leaves | … | session to actor id
  allocation (below)"; below holds actor-id allocation only. B §6.1 has the `join`/`leave` record kinds and B §6.2
  ranks them 0, but neither says what a leave does to queued intents or to time.
- *Failure scenario:* step 7 (`phase1/protocol`) builds disconnects from the live owners. A guest's leave drops
  every intent it sent, including ones already stamped with an `apply_tick`; a scripted log recorded under the
  lanes rule replays a different world. Or the host's socket drops and the world keeps running with no host able to
  pause it, and nothing logs a time decision.
- *Note:* orphaned since v2 superseded lanes, before this branch; round 1 missed it. The fold made the gap look
  closed.

**D-S2. The `seq` rule moved to the intent record, but it governs the wire message.**
- *Evidence:* the source sentence sits in lanes §7's "Client to server" paragraph: it governs the `seq` every client
  message carries. T §3.3 (owner of `client.messages`) gives `seq` to `move`, `move_to`, `kindle`, `time` and
  `snapshot`; `time` makes a control record and `snapshot` makes none. The copy is now B §6.2's "**The record's
  `seq`**", beside a record whose `seq` is "(per actor)" (B §6.2, line 60), and it keeps "within a session", which an
  NPC's records don't have. T §3.3 has no link to it (T §3.1 sends only "the record, its fields" to B §6.2).
- *Failure scenario:* the step 7 decoder author reads T §3.3 and C §4.1, finds no range, and checks none for
  `snapshot` or `time`: a client sends `seq = 2^40` or repeats a snapshot `seq`, and `in_reply_to` matching breaks.
  Or the NPC adapter's author reads "within a session" and can't tell when an NPC's counter may restart, so two
  records share `(actor_id, seq)` in the ordering key after a restore.

**D-S3. `moves_3d_3e.md`'s round 1 record says three homed items were not copied.**
- *Evidence:* its "Skipped" list says of `world_v2.md` §8's save bullet (digest, heavy-mode test), the six fixtures and
  "the intent log header hashes the registry": "Not copied; for the owner". 7cfea02, the same commit, copied all three
  (B §6.3, WM §8 F5, `checklists.md` steps 7 and 9), and its message says so. The table has no rows for them, so
  nothing records the dropped "tied to one rig's cell size" clause either. The two genuine "for the owner" items (v2
  §2.1's table, §2.2's third sentence) are only here, not in rulings.md's "Not decided".
- *Failure scenario:* the owner, reading the moves file as the map (plan §5), rules on the save digest and the
  fixtures as unowned, and a second copy lands in C §4.2 or WM §8. A later reader of WM §8 F5 can't find where its
  digest sentence came from or what was cut. The file is new on this branch, so it can still be corrected.

### NIT

- **D-N1.** WM §8 F5: the save sentences were inserted between ruling 26's two refusals, so "A content change is
  refused too" now follows the digest sentence, not "A save from a newer build is refused". The same bullet's lead
  says the save embeds "the registry, scene and specs"; the inserted sentence adds the material table. Both are true;
  they read as two lists.
- **D-N2.** `fire_model.md` §12, restored verbatim: "flipping the two fire red gates … (proposed: in 6.4)". Since #34,
  FP's step 6 row flips the burnout gate "red-first (6.1)". The same on `origin/main`, so not this branch's
  regression; a stale proposal inside the open-questions list.
- **D-N3.** The `world_v2.md` banner says it is superseded by "`world_model.md`, `npcs_and_sem.md` and the tile
  documents … (`world_model.md`, status)". WM's status names a part 3, `lab_and_core_loop.md`, which doesn't exist;
  it never names the tile documents. The banner is right; its citation doesn't support it.

## Fold-status table

| Finding | Severity | Status (reviewer) | Where read |
|---|---|---|---|
| B1 | BLOCKER | fixed | `fire_model.md` §12 = 5c054f6 = `origin/main` |
| S1 | SHOULD-FIX | fixed (scope: D-S2) | `boundaries.md:436` |
| S2 | SHOULD-FIX | fixed; `sem_stimuli.md:390` deferred (sim-clock owns the file; trigger: next main merge after it lands) | WM §2, §5, §7, §8; IL §4; B §5.3; v2 banner |
| S3 | SHOULD-FIX | open in part: thin-feature fixed (ruling 4); the reconstruct paragraph unrecorded | CLAUDE.md, "Rules that matter here" |
| S4 | SHOULD-FIX | fixed | RM "Ids"; B §9.3; N §8.1 |
| S5 | SHOULD-FIX | fixed | N §6.1 |
| N1 | NIT | open | `fire_model.md:422` |
| N2 | NIT | open | `docs_contracts.md` §1, §5, §7 |
| N3 | NIT | open | `moves.md:85`, `:133` |
| N4 | NIT | open | tile §3 |
| N5 | NIT | open | `npcs_and_sem.md:455` |
| N6 | NIT | open | `boundaries.md:571`, `npcs_and_sem.md:87` |

Reference regressions against `origin/main`: 0. Headings renumbered, removed or renamed: 0. Merge resolution:
correct.

## Counts (new findings)

BLOCKER 0, SHOULD-FIX 3 (D-S1, D-S2, D-S3), NIT 3 (D-N1, D-N2, D-N3).
