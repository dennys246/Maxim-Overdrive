# Docs-contracts, round 1: Wire integrity

Reviewer: Wire integrity lens, independent reader. Range `5c054f6..c043920` (`phase1/docs-contracts`). Read-only;
this file is the only write. Charter: `docs/code_review.md`; rule: CLAUDE.md "One owner per contract".

## What was run

1. **A reference resolver, in memory, at both revisions.** It reads every file from `git show <rev>:<path>`. It
   covers the live docs (`docs/design/*.md`, `docs/design/decisions/*.md`, `docs/plans/*.md`, `docs/roadmap.md`,
   `docs/architecture.md`, `docs/code_review.md`, `docs/standards_backlog.md`, `docs/lessons_maxim_in_games.md`,
   CLAUDE.md) and every `.py/.gd/.sh/.md/.txt/.yaml/.toml/.tscn` under `scripts/`, `tests/`, `src/` and `client/`.
   It matches `<doc>[.md] §N`, the plan's §2 abbreviations (`B`, `N`, `T`, `C`, `WM`, `SS`, `FM`, `FS`, `IP`, `IG`,
   `VH`, `IL`, `RL`, `V2`, `AR`, `RM`, `CL`, `FP`, `LT`), the short forms (`tile`, `client`, `world`, `npcs`, `lanes`,
   `v2`, `realtime`), and bare `§N`. A bare `§N` goes to the last doc named earlier on its line, otherwise to its own
   document; in a `decisions/<doc>.md` record it goes to `<doc>`. Each reference is checked against the numbered
   headings of the target at that revision.
2. `git diff --stat` and `--diff-filter=M` on `docs/design/reviews/`.
3. The heading lists of every design doc, plan, the roadmap and architecture, compared between 5c054f6 and HEAD.
4. Row-by-row reads of `moves.md` and `moves_3d_3e.md` against the tree: 52 rows read (listed in the table below).
5. A hunt for missed copies: 10-word shingles shared between live documents, with superseded files and the plan
   excluded, plus targeted greps for the moved members.
6. `lint_contracts.check_contracts` run in memory on the tracked docs. It returns `[]`.

### Resolver output

| | 5c054f6 | HEAD |
|---|---|---|
| References found | 1,879 | 1,542 |
| named / carried / bare / bare in a decision record | 515 / 81 / 1,283 / — | 750 / 104 / 550 / 138 |
| Unresolved | 103 | 94 |
| Resolved at base, heading gone at HEAD | — | **0** |
| Unresolved at HEAD, line also present at base | — | 83 |
| Unresolved at HEAD, line new | — | 11 |

All 138 bare `§N` in the decision records resolve against their source design. I read each of the 11 new
unresolved lines. None is a real break:
- 4 are line-wrap attributions: `boundaries.md` lines 552 and 645 (`npcs_and_sem.md` … `§6.6`),
  `decisions/inference_placement.md` lines 15 and 21 (a bare §N after an `IG §7` citation; each means IP's own
  section, which exists), and `decisions/world_model.md` D26 (`§10`, `§2`).
- 1 is an external doc: `npcs_and_sem.md:805`, Maxim's `thalamic_relay.md` §5.5.
- 3 are plan prose about other documents: `docs_contracts.md` lines 14, 16 and 19.
- 1 is a bare `§6.6` after an IP link: `npcs_and_sem.md:455`, NIT N5.

The 83 that were already unresolved at base are, as far as I could tell, resolver false positives too:
- external Maxim or research docs: `char_oxidation.md`, `autonomic_layer.md`, `splitting.md`,
  `results_rerun1.md`, `neuroscience.md`;
- the `sem_stimuli.md v5 §N` form, whose version word stops attribution;
- `checklists.md` bare §N that cite another doc named earlier in the item;
- `client_rendering.md`'s "world §N", which C defines as `tile_and_client.md` (all of those resolve against
  tile).

I found no genuine pre-existing break. **No reference regressed.**

### Review records

The only file under `docs/design/reviews/` with a modification (`M`) is `reviews/npcs_v3/foldtable.py`, 2 lines,
and rulings.md rules it ("retargeted to the moved fold table"). Every other change under `reviews/` is a new file.
The records are verbatim.

### Headings

Every numbered heading is unchanged, with one exception:

```
docs/design/fire_model.md:  - ## 12. Open questions and risks        (removed in 88f0be1, step 2)
```

The other heading changes are unnumbered and planned: the fold-table headings in `boundaries.md`,
`npcs_and_sem.md` and `world_model.md` became `## Review records`. No live document, script or test cites a removed
fold-table heading by name.

## Findings

### BLOCKER

**B1. `docs/design/fire_model.md` §12 "Open questions and risks" was deleted, not moved.**
- *Evidence:* `git show 88f0be1 -- docs/design/fire_model.md` deletes the whole section. That commit is step 2,
  "decision tables". Its message says only "Not moved: … fire_model.md §11's open items and Maxim asks". The section
  is not in `moves.md` (step 2 lists only "§11, items 1–3"). It is not in `decisions/fire_model.md`, and its text is
  nowhere else live (greps for "flame merging", "named asymmetry", "held flame's lifecycle": no live hit).
- *What was lost:*
  - flame merging, per-flame extinction and autoignition are uncited (refused until cited);
  - the R2a/R2b datasets, TN 2102's stick layout and its O₂ regime are not in hand;
  - cost per flame count is unmeasured;
  - x86 SIMD subset independence is untested (the CI offset test at 1 and N threads);
  - the client's flourish (flicker, smoke) is a named NPC asymmetry;
  - the "Not yet designed" list: per-layer placement, `strike` and breach on fuel objects, a held flame's
    lifecycle, flipping the two fire red gates and retiring `actions.yaml`'s ceilings.
- *Failure scenario:* the records now point at a section that doesn't exist at HEAD:
  - `reviews/fire_model/delta1_bio_faithful.md` row N4 is "fixed: §12, as a named asymmetry";
  - `delta1_executor.md` S3 has "flagged in §12", and NS8 cites "`§12` last bullet";
  - `delta1_determinism_performance.md` DP-N2 has "§12 names it".

  A reader checking those fixes against the tree finds no §12. The open gaps (SIMD subset independence, the
  unmeasured flame-count cost) drop out of every live document, which is what CLAUDE.md's "Record known physics
  gaps … instead of hiding them" forbids. It also breaks plan §5's "No renumbering. A moved section keeps its heading
  and gains a pointer".
- *Fix (unverified):* restore §12 verbatim. It holds open questions, not rulings, so step 2's scope never covered it.

### SHOULD-FIX

**S1. The `seq` range has no live owner.** It is in `realtime_lanes_coop.md` §7 alone, line 325: "`seq` is an integer
in `[0, 2^31)` and must increase within a session (W-F5)".
- *Evidence:* grep for `2^31`, `2³¹` and `[0, 2` over the live docs finds nothing. Plan §1 item 3 names "the `seq`
  range" as a live contract held only by a superseded design, and `inventory_wire.md:107` lists it. No row in the plan
  or in either moves file carries it.
- *Failure scenario:* `tile_and_client.md` §3.3's client messages and `boundaries.md` §6.2's record use `seq`. Step
  7's decoder author reads the live owners, finds no range and no monotonicity rule, and builds a decoder that
  accepts `seq = 2^53` or a repeat. The ordering key `(…, actor_id, seq)` then sees duplicates.

**S2. `world_v2.md` never got its superseded banner, and live text still cites it as an owner.**
- *Evidence:* plan §5 says "`world_v2.md` gains the banner", but `world_v2.md` isn't in the diff. Its status line
  still reads "DRAFT, for a design review before any code". These live lines still hand contracts to superseded
  records:
  - `world_model.md:166`: "v2 §8 stands (self-describing frames, whose grammar is now `client_rendering.md` §4.1's
    …)". Row 11 moved the grammar to C §4.1, yet v2 §8 is still said to stand.
  - `world_model.md:67`: "v2 §2.1 stands" (solids in cells, gas in zones).
  - `world_model.md:123`: "(v2 §2.4)", region ownership.
  - `world_model.md:157`: `topology_version` "(v2 §2.2)". `inventory_log_replay.md:136` flagged this one.
  - `sem_stimuli.md:390`: "the two-rate contact exchange, ledgered antisymmetrically (`world_v2.md` §2.6)".
  - `ip_and_licensing.md:56` (§4): "(`docs/design/realtime_lanes_coop.md` §5: loopback bind, host and guest tokens)".
    Row 16's owner is `boundaries.md` §5.3, and this copy is not in row 16's list.
  - `boundaries.md` §5.3's gate table: "session to actor id allocation (lanes §4.2)", "`TimeAuthority` /
    `HostOnly` (lanes §5)".
- *Failure scenario:* a reader follows `world_model.md` §8 to v2 §8. Nothing marks v2 as superseded, so they take
  its frame rules (pre-row-11, without `kind: delta` reserved or the per-channel `required` flag) as live. An edit to
  the region-ownership or `topology_version` rule has two live-looking homes. Plan §5's step was skipped without a
  record.

**S3. CLAUDE.md contradicts the new owner of the thin-feature rule, and the record names only the handshake line.**
- *Evidence:* `CLAUDE.md:105` reads "Thin features must be at least two cells of the coarsest verification grid
  (0.2 m) thick", with no exemption. Row 72 made `world_model.md` §1.1 the owner and added "fuel objects are exempt
  only as `rod`, `slab` or `bed` recipes" (ruling 72). CLAUDE.md's "Reconstruct, decide at the point, integrate
  upward" paragraph also restates row 78's owner (WM §3) in full. Plan §6 and rulings.md record CLAUDE.md as out of
  scope only for "its handshake line".
- *Failure scenario:* an agent that reads CLAUDE.md first (as every session does) refuses a `rod` fuel object
  thinner than 0.4 m, or flags it in review as a rule breach. The two texts already disagree, and nothing records
  that they do.
- *Fix:* the owner decides. Either a link, or the out-of-scope record lists these two duplications too.

**S4. The "additive first" SEM policy is stated in two designs and the roadmap.**
- *Evidence:*
  - `boundaries.md` §9.3, lines 715–719: "under Maxim's own reading of CC3 (`AffordanceSchema`'s marker,
    `sem.py:113-116`) … precedents `always_active` #403, `speech_param` #1261 … Only `Modulator.execute`'s signature
    is a real break, and it can be opt-in. No major version is proposed";
  - `npcs_and_sem.md` §8.1, lines 921–924: the same, reworded;
  - `roadmap.md:106`: "CC3 text, a trailing defaulted field is additive, so no major version is proposed".

  Row 39 moved both tables to the roadmap and left both lead paragraphs.
- *Failure scenario:* Maxim's CC3 marker moves (a line shift, or a new precedent). One copy is updated and the
  other cites stale line numbers and precedents. This is the stale-copy case the rule exists to stop.

**S5. `npcs_and_sem.md` §6.1's tier-A table still restates roadmap Phase 3 rows.**
- *Evidence:* 53 ten-word shingles are shared between `npcs_and_sem.md` and `roadmap.md`, nearly all of them §6.1's
  table (lines 570–590) against Phase 3's rows:
  - "The clock seam, split in two": a **machinery clock** for decay, cadences and stamps, and a **perceived-time
    port**, the only time a prompt may contain; the planted-render test with its sentinel in the machinery clock; the
    lint banning `datetime.now`, `strftime` and `localtime`. All of this is in OD-A2 and OD-A3.
  - "Keyed substreams", "The leak closure (OD-A17)" and "Credit at settle" overlap OD-A7, OD-A17 and OD-A18 in the
    same way.

  Row 39 names the roadmap Phase 3 rows as the owner and replaced only N §8.1's "What" and "Path" columns. Row 43
  fixed only §6.1's request-contents cell.
- *Failure scenario:* an upstream ask is amended in the roadmap, as ruling 43 amended OD-A14 (deadline, not
  priority), and §6.1 keeps the old wording. A tier-A builder reading the design builds to the stale ask.

### NIT

- **N1.** `fire_model.md` §10.1's "Revised | How" table, line 422, still states the thin-feature exemption verbatim
  ("the rule holds for resolved cells; fuel objects are exempt only as `rod`, `slab` or `bed` recipes …"). WM §1.1
  now owns it (row 72). The 17 shared shingles come from here.
- **N2.** Plan §5 says `moves.md` maps old locations "at dc0e1aa" and that `git show dc0e1aa:<path>` recovers the
  text. `moves.md` and `moves_3d_3e.md` use 5c054f6. Between the two, 11 docs differ (+413/−32 lines, including
  `checklists.md` and `roadmap.md`), so a line cited at one revision may not be at the other.
- **N3.** `moves.md`'s step 3b and 3c headers still say "uncommitted on this branch until the owner commits". The
  file is committed and new on this branch, so it can still be corrected.
- **N4.** `docs/design/contracts.md` makes `tile_and_client.md` §3.2, headed "`kindle` (T4; …)", the owner of the
  whole intent-kind vocabulary. The no-rename rule keeps the heading, so a reader looking for "intent kinds" won't
  find the section by its title. A pointer line in §3's lead would cost a dozen words.
- **N5.** `npcs_and_sem.md:455`: "liveness ceiling per kind (`inference_placement.md` §2.5); and the host's per-park
  wall ceiling (§6.6)". The bare `§6.6` reads as IP's, which has no §6.6; it means N's own.
- **N6.** `boundaries.md` §7.1, line 560, and `npcs_and_sem.md` §2.1, line 87, both state "`dt_ticks` is a pure
  function of the actor's rate divisor and phase, never of lag". This was a duplication before the branch. One
  sentence, below the lint's threshold.

## Rows read against the tree

✓ means the owner states the contract and every named copy now links to it without contradicting what it replaced.

| Row | Contract | Owner states it | Copies link | Note |
|---|---|---|---|---|
| 1 | intent kinds | ✓ T §3.2 | ✓ B §6.1, WM §8 F7 | N4 |
| 2 | `kind_rank` | ✓ B §6.2 (0/10/20/30, ruling 2) | ✓ T §3.1, CL 5a | |
| 3 | ordering key | ✓ B §6.2 | ✓ T §3.1, N §9 | |
| 4 | intent record fields, `invocation` | ✓ B §6.2 | ✓ T §3.1, CL 5b, RM OD-A18 | |
| 5 | record kinds | ✓ B §6.1 | ✓ SS §5, CL 5a | |
| 6, 7 | receipts | ✓ SS §6.2; T §3.3 | ✓ B §7.2, N §6.4 | the `stale` credit rules are open (rulings.md) |
| 9 | refusal codes | ✓ T §3.4 | ✓ FS §5.3 | |
| 11 | frame grammar | ✓ C §4.1 | ✓ AR, CL 7 | WM §8 "v2 §8 stands" (S2) |
| 12 | `welcome` | ✓ C §4.1 | ✓ SS §3.2, IL §6.4, CL 7 | |
| 13 | messages | ✓ C §4.1, T §3.3 | ✓ (no `act_result` left live) | |
| 14, 15 | bytes per cell, buffer caps | ✓ C §4.2, §4.3 | ✓ AR "Transport" | |
| 16 | handshake | ✓ B §5.3 | ✓ C §7.5, AR | IL §4 missed (S2) |
| 17 | strict JSON, 2⁵³ | ✓ B §9.1 | ✓ C §4.1, CL 7 | |
| 18 | two stages | ✓ B §5.3 | — | |
| 19 | cadence | ✓ T §4, C §4.1 | ✓ B §4.2 | |
| 20 | log header | ✓ B §6.3 (every addition present) | ✓ WM §8, T §3.5, SS §5, FS §5.1, CL | |
| 23 | keyed streams | ✓ N §3.4 | ✓ B §7.3, RM OD-A7, CL 3b | |
| 24 | timing units | ✓ N §9 | ✓ B §7.3, CL 3b | |
| 26 | save v0 | ✓ WM §8 F5 (ruling 26) | ✓ CL 9 | |
| 28 | scene format | ✓ T §1.3 (v0 refused, never migrated) | ✓ CL 3b | |
| 29 | F1, F15 | ✓ WM §8 | ✓ SS §5 | |
| 30 | `session_id` | ✓ N §6.6 | ✓ RM | |
| 31 | thought request id | ✓ B §6.1 | ✓ N §11.1 | |
| 33 | tripwire | ✓ B §3 | ✓ WM §6 | |
| 35, 40 | agent lane; three clocks | ✓ N §6.3, N §1 | ✓ B §7.1, §7.3 | |
| 37 | worker env | ✓ N §6.6 (`HF_HOME` included) | ✓ CL, FP | |
| 39 | Phase 3 rows | ✓ RM | partly: B §9.3, N §8.1 tables ✓ | S4, S5 |
| 41 | latency policy | ✓ N §4.4 | ✓ B §7.4 | |
| 43 | model request | ✓ IP §2.1 | ✓ RM OD-A14 (priority dropped) | |
| 49 | layers | ✓ B §2.2 | ✓ IG §1, VH §2, SS §7.1 | |
| 53, 54 | gates; gate contract | ✓ B §5.3, §5.4 | ✓ FS §5.1, AR, IL §6.3 | |
| 56 | licence | ✓ B §8.2 | ✓ AR, RM | |
| 59 | Phase 1 exit | ✓ RM Phase 1 "Exit" | ✓ T §6, FM §7, CL 8 | |
| 60 | band gate | ✓ WM §3 | ✓ T §6.3 item 7, SS, N, VH | |
| 62 | material files | ✓ FS §5.1 (FM additions present) | ✓ FM §9.1 | |
| 63, 64, 65 | ledger, coupling, rate law | ✓ FS §5.4, §1.1/§3.1, §4.2 | ✓ FM §9.2, §2.1–2.2, §3.1 | |
| 67 | R0, R1 | ✓ FS §4.5–4.6 | ✓ FM §6.2 | S-kind: FS's "heater removed: not graded" supersedes FM's graded line, as plan X10 rules |
| 69, 70, 74, 75 | body; push; B-13; split | ✓ SS §3.1, §4.4; B §4.4; SS §1 | ✓ FM §5.1, B §4.3, N §7.2 | |
| 72 | thin features | ✓ WM §1.1 | ✓ AR, T §1.1 | CLAUDE.md (S3), FM §10.1 (N1) |
| 77, 78 | tick; reconstruct rule | ✓ T §6.1; WM §3 | ✓ SS §2.2, RM, AR | CLAUDE.md (S3) |

The registry in `contracts.md` was checked against the markers. All 12 markers sit under the sections the
registry names, and the lint returns no problem on the tree.

## Counts

BLOCKER 1, SHOULD-FIX 5, NIT 6.
