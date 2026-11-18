# Fold of the seven-lens plan review (2026-11-17)

This table maps every BLOCKER and SHOULD-FIX in the seven reviews of `foundations_plan.md` (5eded2d / 72bf36c) to
where the working tree on top of 21a2ab6 handles it. A reviewer set each status from what the files say, not from
the author's account.

**Status:**
- `fixed`: the tree addresses it.
- `deferred`: the tree defers it by name, with a reason and a trigger.
- `rejected`: the tree rejects it, with a reason.
- `open`: not handled. A vague mention counts as `open`.

**Id key:**
- `CS-B`/`CS-S`: cold-start reader lens, `cold_start.md`.
- `TB-B`/`TB-S`: trust boundary and bio-faithful lens, `trust_bio.md`.
- `SEQ-B`/`SEQ-S`: sequencing lens, `sequencing.md`.
- `S-B`/`S-S`: skeptic lens, `skeptic.md`.
- `MS-B`/`MS-S`: Maxim-side lens, `maxim_side.md`, whose own ids are bare `B1`, `S1`.
- `ST-B`/`ST-S`: standards lens, `standards.md` (bare `B-1`, `S1`).
- `F-B`/`F-S`: fidelity lens, `fidelity.md` (bare `B1`, `S1`).

The other prefixes cited are:
- backlog rows: `B` plus a number, in `docs/standards_backlog.md`;
- owner decisions: `O`, `OA` and `D`;
- Maxim items: `OD-`, from roadmap Phase 3;
- delta-round finding ids from `docs/design/reviews/npcs_v3_1/`: `DB-` (determinism and bio), `ATR-` (trust).

## cold_start.md (6 BLOCKER, 10 SHOULD-FIX)

| Finding | Gist | Status | Where |
|---|---|---|---|
| CS-B1 | Plan order contradicts world_model §10, boundaries §11.1, roadmap | fixed | `world_model.md` D26 (§10 replaced for Phase 1 by plan §2), row 10; `boundaries.md` §11.1 (:778) |
| CS-B2 | Step 5 had no base branch; its code lived on another session's branch | fixed | plan §2 step 3a blocked by step 1 (all four branches on `main`) |
| CS-B3 | World-half decisions and owner questions missing | fixed | plan §4 (D20–D26), §5 (boundaries §12, world_model §12); `scripts/check_plan.py` reads `world_model.md` |
| CS-B4 | No "next step", no owners | fixed | plan §1 ("this line" defined), §2 Owner and Done-when columns, step 0a |
| CS-B5 | Nothing visible or playable, or when | fixed | plan §2 (D26, tile first): step 2 golden frame, step 8 exit. The glossary is still missing (see CS-S4) |
| CS-B6 | Stale SHAs and "still" claims | fixed | plan §1 table matches origin and `gh pr list`. The "update the plan in the same commit" rule was not added |
| CS-S1 | design-v2's CLAUDE.md contradicts the plan | fixed | plan §2 step 1: "Until it lands, `phase1/standards:CLAUDE.md` governs" |
| CS-S2 | The venv step had no command and blocked step 5 | fixed | plan §2 step 0a (command, `pip show pymaxim`); step 1 depends on 0a |
| CS-S3 | Sending the correction is unrunnable: no destination | fixed | plan step 0c ("to the Maxim design session … paste it there") |
| CS-S4 | Undefined ids and terms (tier A, B19, the 1.4.0 cut, the scripted double…) | fixed | `checklists.md` "Terms the plan uses"; this file's key for review ids |
| CS-S5 | Review ids collide with backlog ids | fixed | plan cites review findings by prefix only (TB-B3, DB-S5, S-S1) |
| CS-S6 | Design status lines say DRAFT; nothing records acceptance | deferred | `checklists.md` step 1 (flip to accepted at the owner's merge); the lines still say DRAFT |
| CS-S7 | PR #3 had no next step | fixed | plan §2 step 1 (the merge line) |
| CS-S8 | Machine assumptions unstated | fixed | `checklists.md` "Machine assumptions" |
| CS-S9 | "The linked document wins" can't settle doc-vs-doc conflicts | fixed | `world_model.md` D26 makes plan §2 own Phase 1's order |
| CS-S10 | `check_plan.py` was run by nothing | fixed | `tests/test_check_plan.py::test_the_real_plan_passes` |

NITs (7, unnumbered): not audited one by one; open.

## fidelity.md (4 BLOCKER, 12 SHOULD-FIX)

| Finding | Gist | Status | Where |
|---|---|---|---|
| F-B1 | Maxim side a round stale; would duplicate filings | fixed | plan §3 (issue numbers, candidates doc). Maxim's "Not decided here" questions are still not listed in §5 |
| F-B2 | Agent step blocked by the wrong thing | fixed | plan §2 agent line "after step 5" |
| F-B3 | Gating owner questions missing | fixed | plan §5, all four sources |
| F-B4 | Steps reverse the design's order (part 3, acceptance) | fixed | `world_model.md` D26; plan step 0d, step 1 (acceptance) |
| F-S1 | O11 misstated | fixed | plan §4 O11, O16 |
| F-S2 | "Plus the decomposition slice" dropped | fixed | plan §4 O15a ("after 1.4.0 and the decomposition slice"); §2 "Real NPCs" cites O15a |
| F-S3 | O13 shown as current despite §6.6 | fixed | plan §4 O13 |
| F-S4 | O19 cited the wrong step | fixed | plan §4 O19 ("§2") |
| F-S5 | Two false claims about sources | fixed | removed from plan |
| F-S6 | Questions marked decided that aren't; decisions only in the plan | fixed | plan §5 npcs item 1 (sandbox open), item 5 (five proposals, as recommendations) |
| F-S7 | Branch and PR facts wrong | fixed | plan §1; `boundaries.md` O21 |
| F-S8 | "Every owner decision" left out D20–D25 | fixed | plan §4; `check_plan.py` |
| F-S9 | "Exit tests" heading mislabels EA4/EA6/EA9 (conditional) | open | plan §3 line unchanged. By the finding's own terms it's a NIT unless the owner uses that line as the Phase 3 exit checklist; nothing in the tree says either way |
| F-S10 | Stale source text unflagged | fixed | All listed items fixed, `apply` in `boundaries.md` :617, :776 and `npcs_and_sem.md` §6.2. The last spot, `npcs_and_sem.md` :37, was fixed by the author after the reviewer's final pass (status set by the author, not re-verified) |
| F-S11 | The candidates doc adopted our wrong `nac.py:1162` claim; the correction didn't name it | fixed | `reviews/maxim_response_1/response_3.md` §7 (Maxim: "We'll correct it there") |
| F-S12 | Red-first test 4 dropped the double's fold | fixed | plan §2 agent line, test 4 |

NITs (N1–N16): not audited one by one; open.

## maxim_side.md (3 BLOCKER, 11 SHOULD-FIX)

| Finding | Gist | Status | Where |
|---|---|---|---|
| MS-B1 | `correction_1.md`: duplicate anchor question, wrong 10 Hz figure | fixed | `erratum_1.md` §2, §3; `npcs_and_sem.md` §12.2; roadmap OD-A20, OD-A21. The erratum gives the right numbers but no explicit retraction of "10 Hz" |
| MS-B2 | OD-I5's mechanism was public | deferred | Files swept: a re-sweep of `docs/`, `src/`, `scripts/` and `tests/` finds only the advisory's name and Overdrive's own speak-gate rule. Roadmap OD-I5 redacted; `erratum_1.md` §5 discloses the exposure. History: plan §1 Security gate, before going public |
| MS-B3 | Maxim's front gate (why not the 1.1.4 seam) unanswered | fixed | `erratum_1.md` §6 |
| MS-S1 | Phase 4 later than stated (cand. B1, 1.5 hybrid) | fixed | plan §2 "Real NPCs"; §4 O15a |
| MS-S2 | Plan's Maxim-side state stale | fixed | plan §3. The roadmap Phase 3 pin is still `7084f561` (:59) |
| MS-S3 | OD-A19 still referenced | fixed | `npcs_and_sem.md` :1007; `embeddable_agent_DRAFT.md` :10, PR 4a removed, OD-EA12 restated. Fold-history rows at npcs :1466 and :1497 still cite it, as records |
| MS-S4 | Machinery clock disagrees with cand. A3 | fixed | roadmap OD-A2; `erratum_1.md` §4 |
| MS-S5 | Tool duration on the wall clock; `environment.step` in dispatch | fixed | roadmap OD-A4, OD-A18; plan agent line test 6 |
| MS-S6 | Two keyed-substream derivations | fixed | roadmap OD-A7 (conditional on cand. A2, settled in #1305); `erratum_1.md` §4 |
| MS-S7 | #1687 makes real NPCs POSIX-only | deferred | plan §3 (the gap); `checklists.md` agent PR "Platform and latch" (Windows as an owner decision and a Known gap) |
| MS-S8 | #1396 changes what O18 must guard | deferred | `checklists.md` agent PR "The lane's model" |
| MS-S9 | Large parts of Phase 3 have no Maxim answer | fixed (owner) | O29 (`npcs_and_sem.md` §0): a second candidates round after tier A; plan §4. Status set by the author from the owner's decision |
| MS-S10 | OD-H6 against #1361 §(g) | fixed | roadmap OD-H6 (lands inside cand. B1) |
| MS-S11 | Smaller mismatches (parse bypass tier, the shortcut, T1-16 STALE) | fixed | roadmap OD-A17 (shortcut fixed at its root in Maxim, TBR-13; parse-failure bypass with cand. B1); `exp64_cradle_conduct_prereg_DRAFT.md:13` |

NITs (N1–N6): not audited one by one; open.

## sequencing.md (6 BLOCKER, 11 SHOULD-FIX)

| Finding | Gist | Status | Where |
|---|---|---|---|
| SEQ-B1 | The plan stopped before the tile | fixed | plan §2 steps 0a–9; Phase 2 deferrals; roadmap Phase 2 "Moved from Phase 1 by D26" |
| SEQ-B2 | Agents ordered before the clock | fixed | plan §2 agent line "after step 5" |
| SEQ-B3 | PR #1 landed into a branch to be abandoned | fixed | plan §1 (base `main`); §5 boundaries Q3 |
| SEQ-B4 | Owner decisions blocking step 5 missing | fixed | plan §2 step 0b, step 3a (Q1, Q2); §5 |
| SEQ-B5 | PR #3 missing; three merge orders | fixed | plan §2 step 1 (the order, as `merge_notes.md`); `boundaries.md` O21 replaces §11.3 |
| SEQ-B6 | Exit test untestable; tile and locomotion unowned | fixed | `world_model.md` D26; plan step 0d (player movement, golden-screenshot method), step 8 |
| SEQ-S1 | Venvs are step 0 | fixed | plan step 0a. Grimp and import-linter on Python 3.14 are not checked |
| SEQ-S2 | Part 3 blocked the wrong way | fixed | plan step 0d (no code dependency); D26 |
| SEQ-S3 | No Godot step | fixed | plan step 2 |
| SEQ-S4 | Boundaries needs PR #2 merged | fixed | plan step 3a blocked by step 1 |
| SEQ-S5 | `phase1/agents` too big; thinking lane and workers double-owned | fixed | plan agent line (three parts; owns the thinking lane); `boundaries.md` :778; `world_model.md` row 10 |
| SEQ-S6 | Red-first test 5 can't fail | fixed | plan agent line test 5 (strict red gate against pymaxim) |
| SEQ-S7 | The latch exists only in an unreleased pymaxim; mirror-update owner | deferred | `checklists.md` agent PR "Platform and latch" (mirror-update owner: this line) |
| SEQ-S8 | Ledger untestable and misplaced; `lint_standards.py` split | fixed | ledger dropped (see S-S8); plan step 6 "material table v1 with provenance"; step 3a splits the lint first |
| SEQ-S9 | How a merge commit gets its PASS | fixed | plan step 1 Done-when; `checklists.md` step 1 (CI, or a detached worktree; checked against `phase1/standards:scripts/prepush.sh::refuse_main_branch`) |
| SEQ-S10 | Timing budget method under load | fixed | plan §6 (CPU time, minimum of N runs, never wall time) |
| SEQ-S11 | Rebase conflicts are design work | fixed | `checklists.md` step 1 (items 10 and 11; keep design-v2's versions of the shared docs) |

NITs (SEQ-N1–SEQ-N8): not audited one by one; open.

## skeptic.md (4 BLOCKER, 8 SHOULD-FIX)

| Finding | Gist | Status | Where |
|---|---|---|---|
| S-B1 | The plan never mentions the exit | fixed | plan §2 opening, step 8 |
| S-B2 | Godot client last of about 16 PRs | fixed | plan step 2, step 8 |
| S-B3 | Exit unsettled; lab pulls Phase 2 in | fixed | `world_model.md` D26; roadmap Phase 2 |
| S-B4 | Premise unmeasured; cheapest measurement forbidden | fixed | `npcs_and_sem.md` O20; plan §2 LLM spike |
| S-S1 | Build the agent line later | rejected | plan §2 agent line: "It stays in Phase 1 against S-S1: O19 chose tests over paper" |
| S-S2 | Freeze is against rounds, not change; name reopen triggers | fixed | `checklists.md` "Reopening the frozen agent half"; plan §6 "errata only" |
| S-S3 | Owner bandwidth is the critical path | fixed | plan step 1 before code; `boundaries.md` O22 word budget |
| S-S4 | Boundaries refactor oversized (12 layers) | fixed (owner) | O24 (`boundaries.md` §0); plan step 3a. Status set by the author from the owner's decision |
| S-S5 | Co-op and guest privacy designed before single-player | fixed (owner) | O28 (`npcs_and_sem.md` §0); roadmap Phase 4 guest line. Status set by the author from the owner's decision |
| S-S6 | Maxim dependency unbounded | fixed (owner) | O29: the subset is still to be named from the exit tests, and the date asked in `erratum_1.md`. Status set by the author |
| S-S7 | Core loop and fun underweighted | fixed (owner) | D28 (`world_model.md` §0); plan step 10. Status set by the author from the owner's decision |
| S-S8 | Calibration ledger has no caller | fixed | absent from the plan |

NITs (S-N1–S-N4): not audited one by one; open.

## standards.md (4 BLOCKER, 14 SHOULD-FIX)

| Finding | Gist | Status | Where |
|---|---|---|---|
| ST-B1 | Rebases would need a force-push | fixed | `boundaries.md` O21 |
| ST-B2 | Agent step's position; test 4 had no caller | fixed | plan agent line (after step 5, owns the thinking lane) |
| ST-B3 | Step 5's preconditions incomplete, cycle with part 3 | fixed | plan §2 (3a blocked by 1 and 0b; 0d independent) |
| ST-B4 | Six owner decisions left out; checker blind | fixed | plan §4 D20–D26; `check_plan.py` |
| ST-S1 | `check_plan.py` seen by no gate | fixed | moved to `scripts/`; `tests/test_check_plan.py::test_the_real_plan_passes` |
| ST-S2 | Worker coverage mechanism | deferred | `checklists.md` agent PR "Coverage of the worker" |
| ST-S3 | Determinism edits: hash probe against the `hash()` scan, Philox allowlist, CLAUDE.md RNG rule | deferred | `checklists.md` agent PR "Determinism" (the Philox and rule edits are conditional on MS-S6) |
| ST-S4 | Test 5 can't fail; real-Maxim gate needs fencing | fixed | plan test 5 (strict red gate). Fencing: see TB-S4, open |
| ST-S5 | Formats and data standards for the agent line | deferred | `checklists.md` agent PR "Formats and data" |
| ST-S6 | No step names lenses | fixed | plan §2 Lenses column |
| ST-S7 | Backlog "Lands with" pointers stale | fixed | plan §2 Closes column (B2–B7, B14, B19, B20). B9 and B12 are unmapped |
| ST-S8 | B19 (4) applies | fixed | plan step 3a first action |
| ST-S9 | Venvs a precondition | fixed | plan step 0a |
| ST-S10 | design-v2's older CLAUDE.md | fixed | plan step 1 ("`phase1/standards:CLAUDE.md` governs") |
| ST-S11 | Lessons owed for design-v2's work | fixed | `checklists.md` step 1 (the five lessons, assigned to this line at the merge) |
| ST-S12 | PR #3's Markdown lint against design-v2's records | fixed | `merge_notes.md` design-v2 items; `checklists.md` step 1 (drop the `docs/plans/reviews/` exemption) |
| ST-S13 | §1 status table wrong | fixed | plan §1 |
| ST-S14 | Two dangling dependencies (merge order, OD-A18 "After OD-A19") | fixed | plan step 1; roadmap OD-A18 |

NITs (N1–N5): not audited one by one; open.

## trust_bio.md (3 BLOCKER, 9 SHOULD-FIX)

| Finding | Gist | Status | Where |
|---|---|---|---|
| TB-B1 | Tests 2 and 4 pass whatever the code does | fixed | plan agent line tests 2 (probe, planted real-home read) and 4 (digest folds steps and staleness) |
| TB-B2 | Guest gates have no step | fixed | plan step 7 (guest-join red gate); `checklists.md` step 7; roadmap Phase 4 gate list (O18 added); plan §5 npcs item 1 (sandbox) |
| TB-B3 | O17's purge versus replay needs an owner choice | fixed (owner) | O26 (`npcs_and_sem.md` §0: redaction records, replay boundary, the `purge` kind); `checklists.md` agent PR. Status set by the author |
| TB-S1 | Correction carried a new error and an answered question | fixed | `erratum_1.md` §1 (split test), §2, §3 (names #1361 Q1) |
| TB-S2 | Push-backs had no Phase 3 rows | fixed | roadmap OD-A20, OD-A21; `npcs_and_sem.md` §12.2 |
| TB-S3 | Test 5 is a strict red gate, not red-first | fixed | plan agent line test 5 |
| TB-S4 | Real-Maxim red gates only inside the worker, after test 2 | deferred | `checklists.md` agent PR "Real Maxim stays off the test process" |
| TB-S5 | `npcs_v3_1` findings override frozen §6.6; list of trust findings | deferred | `checklists.md` agent PR "Precedence" (ATR-S1, S3, S6, S8, S9, S10, N1, N2) |
| TB-S6 | *To verify* numbers enter `data/agents/` | deferred | `checklists.md` agent PR "Provenance" (option (b)) |
| TB-S7 | O16 gives up O4 and O12 in co-op | fixed | plan §4 O16; O27 and its known gap in `npcs_and_sem.md` §12.2. Status set by the author |
| TB-S8 | O12 at full strength in conversation while the evidence is open | deferred | plan §5 npcs item 5: slow tail and filler propensity after the LLM spike |
| TB-S9 | Agent step skips the PRs its trust rests on | fixed | plan agent line "after steps 5 and 7", owns the thinking lane; `checklists.md` agent PR; `world_model.md` row 10 |

NITs (TB-N1–TB-N6): folded where cheap: TB-N1 (plan O11a), TB-N2 (`[engineering]` on O4, OA5), TB-N5 (`checklists.md` step 7), TB-N6 (line removed), TB-N4 (roadmap Phase 4, npcs O14: "file reads or writes"). TB-N3 open.
