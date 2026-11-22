# Docs-contracts, delta round 1: Executor and Architecture

Diff: `git diff c043920 c989b12` (the round-1 fold, 7cfea02, and the owner's rulings, c989b12), plus the conflict
resolution of the merge b1237ac in `docs/plans/foundations_plan.md`. Lenses: Executor and Architecture
(`docs/code_review.md`). I only read. Every planted case ran on in-memory dicts (through `check_contracts`) or on a
`git archive HEAD` copy in the session scratchpad, never on the worktree's files. The only file this review wrote is
this one, and it quotes markers inline only.

## What was run

- `pytest tests/test_lint_contracts.py tests/test_lint_standards.py tests/test_check_plan.py --cov=scripts
  --cov-branch`: **234 passed**. `scripts/lint_contracts.py`: 196 statements, 84 branches, **99%**. The one miss is
  line 84, `blocks`'s final flush for a text that doesn't end in a newline, which is the same miss as in round 1.
- `ruff check` and `ruff format --check` on the lint and its tests: clean. `mypy` (strict): no issues.
  `scripts/lint_standards.py`: PASS, 0 findings (20 rules checked, 27 review-held). `scripts/check_plan.py`: PASS.
- **Mutation run, 28 single mutations of `lint_contracts.py`** against `tests/test_lint_contracts.py` (45 tests,
  the real-tree test included), on the archive copy. **24 were killed**: the fence toggle in `blocks`, splitting list
  items again, a banner anywhere, banners ignored, markers not fence-aware, a section number matched as a prefix,
  `unnamed` off, exclusions ignored, every table column as a member position, items without backticks, RULING off,
  RULING without `**Ruled`, FOLD off, the decision-table check off, the blanket owner exemption restored, the row's
  count ignored (`min(3, n)`), `first_item` off, the `absent` branch off, the signature joined without spaces, the
  three-member floor off, a signature needing 2, orphan markers off, the marker-in-section check weakened, and plans
  dropped from scope. **4 survived**: see NEW-6.
- **Prior structures restored.** Each of 8 designs was swapped back to its 5c054f6 text in memory and run through
  `structural`. world_model gave 12 findings (the fold table plus 11 `- **D…` rulings), fire_model 1 (`**Ruled`),
  sem_stimuli 2, boundaries 3, npcs_and_sem 4, and tile, client and inference 1 each. All go red.
- **The derived counts, recomputed on the merged tree (b1237ac).** For each vocabulary I took the largest number of
  its members in one in-scope block outside its own owner lines, using the lint's own `blocks`, `in_scope` and
  `resolve`:

| Contract | Largest reference | max(3, ref + 1) | Row |
|---|---|---|---|
| `thought_failed.reasons` | 1 | 3 | 3 |
| `truncated.reasons` | 1 | 3 | 3 |
| `receipt.kinds` | 1 | 3 | 3 |
| `intent_result.outcomes` | 1 | 3 | 3 |
| `intent.kinds` | 4 (`boundaries.md`:451, `kind_rank`) | 5 | 5 |
| `refusal.codes` | 5 (`tile_and_client.md`:384, §6.3's exit script) | 6 | 6 |
| `record.kinds` | 4 (`sem_stimuli.md`:237; `boundaries.md`:424) | 5 | 5 |
| `intent_record.fields` | 4 (`boundaries.md`:317 and :605) | 5 | 5 |
| `codec.kinds` | 3 (`npcs_and_sem.md`:630) | 4 | 4 |
| `server.messages` | 4 (`checklists.md`:223; `tile_and_client.md`:223) | 5 | 5 |
| `client.messages` | 3 (`vertical_slice.md`:47, `checklists.md`:155, tile :175, :193) | 4 | 4 |

  **Every row matches ruling 1.** The references contracts.md lists are the blocks I found at three or more members.
- **The merge's conflict.** The resolution takes main's step 6 row ("red-first (6.1)", from #34) and this branch's
  step 7 row (links to C §4.1, T §3.3 and B §5.3). That is the right union. check_plan passes on it.
- **Word budgets** (`wc -w`, marker lines excluded under ruling 2, 5c054f6 → HEAD): no design grows except
  `world_v2.md`, 5,429 → 5,454. That is the +25 of its banner, which ruling 6 allows. `client_rendering.md` is 3,774.

## Fold status of round 1

Every status here is read from the tree. "Owner" means the status rests on a recorded ruling in rulings.md, "Round 1
rulings".

| Finding | Status | Evidence in the tree |
|---|---|---|
| Exec S1 / Arch A1 (list copy invisible) | **fixed** | `blocks` no longer splits list items. `test_a_copy_one_member_per_bullet_fails` exists, and the mutant that re-splits items is killed by it. |
| Exec S2 / Arch A5 (partial banner exempts file) | **fixed** | `in_scope` checks `header(text)` only. `test_a_superseded_note_inside_a_section_does_not_exempt_the_design` kills both banner mutants. Edge cases remain in NEW-4. |
| Exec S3 (decision lists return unseen) | **fixed** | `RULING` added, and the three 5c054f6 forms go red (above). Variants that evade it are in NEW-3. |
| Exec S4 / Arch A12 (marker words vs budget) | **fixed** (owner, ruling 2) | Recorded in rulings.md and contracts.md. |
| Exec N1 (stale docstring) | **fixed** | The docstring gives the five-column row and the row's count. |
| Exec N2 / Arch A14 (marker scan) | N2 **fixed**; A14 **open** (NIT) | `markers` is fence-aware for backtick fences. It still scans every `docs/**/*.md`, so a review that quotes a marker on its own line, unfenced or in a `~~~` fence, fails the tree (probes 4a and 4b). No reason is recorded for keeping that scope. |
| Exec N3 (§ prefix match) | **fixed** | `\.?\s` after the number. The prefix mutant is killed. |
| Exec N4 (test count) | **fixed** | 7cfea02 says 45 tests, and 45 are collected. |
| Exec N5 ("verbatim" with form changes) | **open** (NIT) | The decision records' header comment is unchanged on this point. |
| Exec N6 (signature without spaces) | **open** (NIT) | `` `(apply_tick,kind_rank,seq)` `` in a plan passes (probe 8). |
| Arch A2 (marker one-way, inference wrong) | **fixed** | `members` is deleted. `unnamed` and `member_positions` tie the block to the marker both ways, with exclusions after `not:`. The mutants `unnamed off`, `exclusions ignored` and `absent off` are killed. Residual gaps are in NEW-5. |
| Arch A3 (thresholds tuned after the run) | **fixed** (owner, ruling 1) | The counts are derived and match the recomputation above. The docstring states the row's count. |
| Arch A4 (blanket owner exemption) | **fixed** | Only `c`'s own owner lines are exempt. `test_another_contracts_owner_block_is_still_checked` kills the restored-union mutant. |
| Arch A6 (world_v2 still owns live contracts) | **open**, in part | Fixed: the banner, WM's "v2 §N stands" pointers, and IL §4's link (now B §5.3). Open: `world_v2.md` §2.6, the ledger, is still the only statement of "every process is one transfer, limited by what the donor holds, applied antisymmetrically, never clamped afterwards; cells plus zones plus pools close per substep". WM §4 amends only its tolerance (line 118), and `sem_stimuli.md` §5 (line 390) still links to "`world_v2.md` §2.6" for it. The banner this fold added took that owner out of scope, which is the A6 failure scenario on a section the fold didn't list. |
| Arch A7 (record statuses; duplicates; empty owners; CLAUDE.md location) | **open**, in part | Fixed: O24, O8 and O11a read "live; amended by docs-contracts ruling 49/50/41", and the header comment names the rulings as a status source. Open, with no reason recorded: the duplicate rows (O3 and O4 read "also in" in two records), the mostly empty Owner section column, and CLAUDE.md ("kept in `docs/design/reviews/` and indexes") against `docs/design/decisions/`. |
| Arch A8 (`imagine` in two vocabularies) | **deferred** (owner, ruling 5; trigger: step 5a) | The trigger exists only in rulings.md (NEW-1). |
| Arch A9 (push log-record claim dropped) | **open** | Ruling 3 keeps the claim dropped and names "an open finding for `sem_stimuli.md` §4.4". That finding has no trigger and no home a build step reads: SS §4.4, the checklists and the backlog say nothing (NEW-1). |
| Arch A10 (row 79 contradicts itself) | **fixed** | Row 79 now reads "Ruled; applying it waits with row 10 (Not decided, below)". |
| Arch A11 (CLAUDE.md thin-feature rule) | **fixed** (owner, ruling 4) | CLAUDE.md now carries "(fuel objects excepted, `docs/design/world_model.md` §1.1)". |
| Arch A13 (fold and decision detection keys on exact headings) | **open** (NIT) | `## Review fold` over a `| Finding | Status |` table still passes (probe 10). |
| Arch A15 (moves.md says "uncommitted") | **open** (NIT) | `moves.md` lines 85 and 133 still say it. |

## New findings

### NEW-1. SHOULD-FIX: `reviews/docs_contracts/rulings.md` "Round 1 rulings" 3 and 5: two deferrals live only in a review record, so their triggers can't fire

**Failure scenario.** The step 5a builder works from `docs/plans/checklists.md` and `boundaries.md` §6.1. Neither
says that §6.1's separate `imagine` record kind folds into `intent` when `imagine` becomes an intent kind
(ruling 5), so 5a ships two record kinds for one action. That is A8's contradiction, now permanent. In the same way,
the `BoundFrame` log writer, built from SS §4.4 and the checklists, never sees the open question of whether a push
needs a log record (ruling 3).

**Evidence.** I searched `docs/` outside `reviews/` for "log record", "push needs" and "imagine" folding: none in
SS §4.4, none in the checklists (`grep imagine docs/plans/checklists.md` returns nothing), and no backlog row. A
status of deferred needs a trigger someone will reach (CLAUDE.md, O25). A record nobody at the trigger reads
doesn't meet that.

**Fix (unverified).** Add one checklist item each: step 5a for ruling 5, and the step that builds the `BoundFrame`
log for ruling 3. Or add a backlog row with the trigger.

### NEW-2. NIT: `docs/design/contracts.md`, intro paragraph: stale rule and marker syntax

The intro still says the lint fails when a block "holds three or more of those members". The next sentence says
each row's count governs. The marker form it gives, `<!-- contract: <name>: <members> -->`, leaves out the
`| not: <spans>` exclusions, which 7 of the 12 live markers use. Someone writing a marker from the registry's own
text gets an "its block holds …, which its marker neither names nor excludes" failure with no explanation of how to
fix it.

### NEW-3. NIT: `scripts/lint_contracts.py::RULING`, a heuristic with gaps in both directions

These forms pass inside a design (probes 7):
- `1. **D20. One truth.**` (a numbered list);
- `- **Ruled (owner, 2026-11-20):**` (a bullet);
- `**D20. One truth.**` (no bullet);
- `- **OD-A1.**`.

`- **D1** deliverable: the tile` fails, though it is not a ruling. The three historical forms are caught, which is
what S3 asked, but the docstring ("a list of rulings") reads as the general rule. B36 doesn't name the gap.

### NEW-4. NIT: `scripts/lint_contracts.py::header`, the edges of the header-only banner

- A design with no `## ` heading is all header, so `> **Superseded in part …` anywhere in it exempts the whole file
  (probe 2).
- A partial banner placed in the header also exempts the whole file (probe 3: `> **Superseded in part (§4) by
  `y.md`.**`).

Neither case is on the tree today. `header` isn't fence-aware either.

### NEW-5. NIT: `scripts/lint_contracts.py::parse_marker` / `unnamed`, exclusions are never checked

- A stale exclusion (a span no longer in the block) passes (probe 5b).
- A name both named and excluded passes (probe 5c).
- Any keyword after `|` is accepted: `| except: a b` excludes `except:`, `a` and `b` (probe 6). The surviving
  `removeprefix` mutant shows that `not:` is decorative.

So `not:` can only grow. An exclusion that later becomes a real member (say `ignite` returning to `intent.kinds`)
stays hidden from the two-way check, which A2's fold exists to prevent. Probe 5 (a new member added to the text and
to `not:` at once) passes by design, since the docstring says exclusions are "said aloud". The cases above aren't
said aloud.

### NEW-6. NIT: `tests/test_lint_contracts.py`, three mutants survive, plus one dead guard

1. Header skip. With `[1:]` removed in `member_positions`, every test still passes: no fixture table has a code span
   in its header, so that line is untested.
2. Registry scope. With `rel != REGISTRY` removed from `in_scope`, every test passes, the real-tree test included.
   Nothing proves the registry is out of scope. It matters once contracts.md's reference list names four members of
   a row.
3. `removeprefix("not:")`. Equivalent in behaviour (NEW-5).
4. `if kept and …` in `restatements` is dead code. `need >= 1` always holds, so an empty `kept` can't reach it. It is
   an equivalent mutant.

The first two are cheap single-assert tests.

### NEW-7. NIT: `scripts/lint_contracts.py::first_item`, an owner can no longer be a bulleted list, and the fold didn't say so

The round-1 lint merged an owner's list run (`list_run`, `test_a_marked_list_defines_as_a_whole`). The fold deleted
both, so an owner written one member per bullet now fails with "its marker names [timeout, parse, …], which its
block doesn't hold" (probe 1). That message points at the marker, not at the form. The other bullets of the same list
are a restatement of the owner under the S1 fix. The module docstring says "one list item". Neither 7cfea02's message,
contracts.md nor B36 records the change. It fails loudly, so it's a NIT: a vocabulary in that form simply stays
unregistered.

### NEW-8. NIT: `docs/design/world_v2.md`, the header contradicts itself

The new banner, "Superseded 2026-11-16 by `world_model.md` …", sits directly above "**Status:** DRAFT, for a design
review before any code". Ruling 6 allows the banner's words, but the status line now says the opposite. (A6's open
remainder is the substantive part.)

## What holds

- The two-way marker check found real drift on the tree (`busy`, the core record fields, and `intent`, `control`,
  `join` and `leave` in `record.kinds`). The live markers now account for every member-position span.
- Owner exemption is per contract. `boundaries.md`:424's four `record.kinds` inside the `intent_record.fields` owner
  are counted, and they sit under the row's 5.
- Section matching is whole-number, and backticked marker items hold spaces
  (`test_a_backticked_exclusion_may_hold_spaces`).
- Module fit is unchanged: one job, the size limits clear (lint_standards PASS), and the `check_contracts(files)`
  signature matches its siblings.

## Counts

Round 1 fold: 16 fixed (Executor S1–S4, N1–N4; Architecture A1–A5, A10–A12),
1 deferred (A8), and open: A6 and A7 in part, A9, plus NITs N5, N6, A13, A14, A15.

New findings: **BLOCKER 0, SHOULD-FIX 1 (NEW-1), NIT 7 (NEW-2 to NEW-8).** A6's open remainder (`world_v2.md` §2.6,
the ledger, ownerless in scope) is a SHOULD-FIX carried under A6, not counted again.
