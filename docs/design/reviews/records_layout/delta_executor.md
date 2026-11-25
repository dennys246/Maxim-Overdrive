# Records layout design, delta round: Executor (2026-11-24)

Read: the fold's diff `239f267..9d1e747` (design, rulings RL1–RL10, `fold.md`, two roadmap rows), checked against round
1's reports and the tree. Ran read-only git and `.venv/bin/python` one-liners: `lint_ids._decision_rows` over the
decision logs at `1ed9caa` and `9d1e747`, heading, bullet and row counts with `grep` and `git show`, whitespace word
counts per record, and a census of every decision log's first and status cells. Nothing was edited but this report.

## Round-1 statuses

| Finding | Status | Evidence |
|---|---|---|
| A-B1 | fixed | §1 withdraws the "stop conflicting" claim (RL9). §5 and §6 make the committed, id-ordered index the detector, and R1 tests it. Two insertions at one point always conflict in git's three-way merge, so the detector holds whenever both branches committed a regenerated index, and §7's regeneration check refuses one that didn't. |
| A-B2 | fixed | RL10: lesson bodies are mutable, with an `amended` trail (§4). S1 (the trail wasn't enforced) is fixed at `01cbb25`. |
| A-B3 | fixed | §5 defines a family as an id prefix across every log, which is what `lint_ids` holds. Cross-listed rows become one record with `also_in`, and restating and id-less rows get slug ids. S3 (the slug-id file name) is fixed at `01cbb25`. |
| A-B4 | fixed | Updated after the RL13 fold (`01cbb25`). At `9d1e747` the four fields couldn't carry "confirmed by O69" (twice), "confirmed by O74", "corrected by O73", or seven `restates` cells whose target isn't an id ("world_model §0" four times, "boundaries §0" twice, "CLAUDE.md", "realtime decisions 1–4", "`client_rendering.md`"). §4 now has `confirms`, `corrects` and `amended_by_external` (a path plus the ruling's first cell, which exists: `rulings.md` has a row whose first cell is 41), and `restates` takes a path with a section. Every status cell's meaning is now derivable, and R2 tests the four kinds. Reproducing the cells' exact wording is a separate problem: see "New BLOCKER in the fold". |
| C1 | fixed | The same defect as W1. §1 withdraws the PR-CI claim, RL8 keeps "require up to date" off, and §5's detector stops the second merge with a conflict, which GitHub refuses whether or not the branch is protected. R1 tests it (A-B1, C1, W1). |
| C2 | fixed | §4's exception and §5's "A duplicate on `main`" allow the rename only while `main` holds two records, and R1 tests that case. S5 (the rename's citations, and who opens the fix branch) is fixed at `01cbb25`. |
| C3 | fixed | §5: `renumber` rewrites only lines the branch added or changed against the merge base, and lists `main`'s lines. R1's shared-file test goes red under a whole-file rewrite. S6 (running mid-merge) is fixed at `01cbb25` by RL12. |
| W1 | fixed | As C1. |
| W2 | fixed | As C3. The R1 test asserts both errors: the branch's citation moves, and `main`'s doesn't. |
| W3 | fixed | §5 takes `lint_ids::check_lessons`'s spellings and scope (`docs/**/*.md`, `tests/*.py` `reason=`, frozen files skipped). I read `scripts/lint_ids.py`: it covers "Lesson N", "lessons N and N", ranges, `§N` and the file-name form, so "Lessons 32 and 33" is read. Decision citations are no longer resolved, so the false passes and the red marks on Maxim's ids are gone. |
| W4 | fixed | As A-B3. The ten cross-listed ids I measured (O3–O7, O7a, O31, T1, T2, D20) each become one record. |

**Numbers checked.**
- §2 lessons: 40 `### N.` headings, numbered 1 to 40 with no gap. True.
- §2 backlog: 48 distinct row ids, B1 to B48. True.
- §2 decisions: 174 rows with a single id, 164 distinct ids, ten logs. True at `9d1e747`, not at `1ed9caa` as stated. At `1ed9caa` there are nine logs, 164 rows and 154 ids; the extra ten are this branch's RL1–RL10 (NIT N1).
- §2 Known gaps: "13 bold bullets" is false. The file has 18 top-level gaps, 13 bold and 5 plain ones under "Known gaps (tracked, not gated yet)" (S4).
- RL4 and §6 budgets, measured as whitespace words per record:
  - lesson: longest is 474 (lessons 31 and 36), so 500;
  - decision: longest is O79's row, 361 (its ruling cell is 350), so 400;
  - Known gap: longest is 344 ("Fires diverge across rigs"), so 400;
  - backlog: longest is B5's row, 540, so 600.
  All four match.
- Word counts: the design is 2,988 words, a new document under 6,000 (it isn't on `main`). The rulings file is 691 words and `fold.md` 674.

## New findings

### BLOCKER

- **X-B1, §8 against §6: the byte-for-byte round trip can't pass on the tree, and the fold made it stricter.**
  - At `239f267`, any difference could be "listed in the migration commit as a named, reviewed change". The fold
    narrows the exceptions to the marker line, the lessons index and the derived status column.
  - In the same diff, §6 makes generated forms the originals don't have:
    - `docs/known_gaps.md` is "grouped by `kind`, each with its slug shown". Today's file has no kind groups and no
      slugs, and it has a plain "tracked, not gated yet" list followed by bold gaps in authoring order.
    - Lesson headings get "the date generated from `date`". Lesson 11's heading reads "(2026-11-15, reworded
      2026-11-20)", and §6 puts the `amended` trail under the lesson, not in its heading.
    - Each `<design>.md` log is regenerated, but no field keeps today's row order, which isn't id order:
      `boundaries.md` runs O41, O42, O25, O8, O57, and `npcs_and_sem.md` has O7a after O45. §6 doesn't say the order.
    - Restating and id-less rows become slug-id records. §6 doesn't say whether the regenerated first cell shows
      `D26–D28` or the slug.
  - Failure: step 4's R2 round-trip test (`tests/test_records.py`, the brief's exit test) fails on `known_gaps.md` by
    construction, and on the logs and lesson 11 unless the converter invents an order field or a heading tail §4
    doesn't define. The brief says "Don't redesign", so the session stops at R2.
  - This is contract: it decides what the generated files look like and what the migration may change. Under the stop
    rule it goes to the owner.
  - The decision the owner faces (unverified): either list each form change in §8 as a named exception (kind grouping,
    slugs, the dated heading, row order), or keep today's forms at R2/R3 and regroup in a later commit.

### SHOULD-FIX

- **S1, §4 "What may change" and §7: RL10's trail is unenforced.** §4 lets a lesson change "its body, its `title`
  and its `amended` list, which only grows". It never refuses a body change with no new `amended` entry, so
  `lint_records` passes one, and R1's "every refusal in §4" never tests it. §8's CLAUDE.md wording for "Record lessons"
  doesn't mention `amended` either. Failure: a session rewrites lesson 23's Consequence (as #49 did) with no entry.
  The gate is green and the correction is invisible, which is the lesson 29 problem A-B2 raised. Mechanism: an R1
  test, plus a §4 rule that a body or title change grows `amended` by exactly one entry.
- **S2, §5 `renumber`'s upstream refusal refuses the one case it meets.** It refuses "an old id cited anywhere under
  `docs/maxim_upstream/`", and "a lesson is cited upstream only after it is on `main`". So the only
  citation of number `41` that can exist upstream is of `main`'s lesson number `41`, which is the record that keeps its id.
  Failure: A merges lesson number `41`, and a later PR cites it as a lesson in an upstream draft. B, holding its own 41, merges
  `main`, runs `renumber 41=42`, and is refused. There is no other permitted resolution, so B either edits by hand
  (§6 forbids that for generated files) or is stuck. R1's test ("refuses an id cited under `docs/maxim_upstream/`")
  passes and proves the deadlock. The refusal should name a branch-added upstream line citing the branch's record,
  or be dropped (unverified).
- **S3, §3 and §5: a slug-id decision record has no defined file name, and the example names the wrong log.** The
  layout is `<design>/<id>-<slug>.md`, and §3 requires the id and slug to equal the front matter. The id
  `world_model/d26-to-d28` contains a `/`, so the rule gives a nested path (`world_model/world_model/d26-to-d28-…`) or
  nothing. Also, the `D26–D28` restating row is in `tile_and_client.md`, not `world_model.md`, where D26, D27 and
  D28 are separate rows. Failure: R1 has to pick a file-name rule for about 22 slug-id rows (the census lists
  `ruled 1–3`, `the split`, `the rounds stop`, `CLAUDE.md`, the four `—` rows and the five list and range rows), and
  `lint_records`' name check can't be written from §3.
- **S4, §2 and §4: Known gaps are miscounted, and their fields can't be migrated.**
  - There are 18 gaps, not 13; the five plain ones have no bold lead, and §4 doesn't say where their `title` comes
    from (decisions get "by hand in the migration commit"; gaps get nothing).
  - §8 says a missing field is `unknown`, but `kind`'s values are `physics`, `performance` or `trust boundary`, and
    `gate` and `closes_at` take a value "or `none`/`unscheduled` and a reason". None admits `unknown`, and no source
    gap has a `kind`.
  - Failure: R2's converter either writes `unknown`, which R1's schema refuses, or invents a kind, which §8 forbids.
    Mechanism to settle (unverified): state that the migration commit sets `kind` and titles by hand, as it does for
    decision titles.
- **S5, §5 "A duplicate on `main`": the fix moves no citation, and no one owns it.** On the fix branch every
  citation of the renamed record came from `main`, so `renumber` lists them all and rewrites none. The rename then
  leaves every citation of the second record resolving silently to the first, which is the C3 failure. The design
  also doesn't name who opens the fix branch, the second half of C2. Mechanism: an R1 test that the fix path
  rewrites the citations the second record's merge added (they can be found from its merge commit), and a sentence
  naming the owner.
- **S6, §5 `renumber` mid-merge: "against its merge base" depends on whether the merge of `main` is committed.** §5's
  sequence is merge `main`, regenerate, see the lint fail, then renumber. If `renumber` runs before the merge commit,
  HEAD is still the branch's old tip, so a working-tree diff against the old merge base includes `main`'s incoming
  lines. Those are then treated as the branch's own and rewritten, which is C3 again. R1's shared-file test doesn't
  say which state it runs in, so it can pass in one state and miss the other. Mechanism: an R1 test that runs
  `renumber` during an uncommitted merge and asserts a refusal, or the same result as after the commit.

### NIT

- **N1, §2:** "Counts are at `1ed9caa`" is wrong for decisions. The figures (174, 164, ten logs) include this
  branch's RL1–RL10. At `1ed9caa`: nine logs, 164 rows, 154 ids. Trigger: R1's recount.
- **N2, §5 and §6: "id order" is undefined for suffixed and slug ids.** `O7a`; `RL10` against `RL2` sorts
  differently by text and by number, and so would `B10`. The order changes the backlog's round-trip bytes. Trigger:
  R1, the determinism test.
- **N3, §3: there are no out-of-scope paths to add to.** `lint_contracts.py` has no such list; its `SCOPE` regex
  (`^docs/(design|plans)/[^/]+\.md$|…`) already excludes subdirectories. The `_header.md` files sit in
  subdirectories, so keeping them in scope means widening `SCOPE`. Trigger: R1.
- **N4, §8: CLAUDE.md's "A record id names one record" goes stale.** It still says a decision filed in two logs "says
  `also in` in both rows", and §8's wording list leaves it out. Trigger: R3.
- **N5, §5: the same id with the same slug.** Two branches give an add/add conflict on one path, leaving one file
  with conflict markers. `renumber` can't separate the two records there, and R1 tests only "one id with two
  slugs". Trigger: R1.

## Status check after the RL13 fold (2026-11-24)

Read: `git diff 14c2e5d 01cbb25` (the design, RL11–RL13, and `fold.md`'s "After the delta round"), checked against the
tree. I re-ran the first-cell and status-cell census over every decision log, grepped for the paths a `restates`
entry would have to name, and counted the design's words: 3,989, a new document under 6,000.

| Finding | Status | Evidence |
|---|---|---|
| X-B1 | open | RL11's two-stage proof and `legacy` fix three of its four cases: row position, lesson 11's heading tail, and the gap groups and bullet form. The fourth isn't on §8's closed list ("and only those"): the first cell of a slug-id row. That cell can't be derived from the slug: four rows read `—`, one reads `CLAUDE.md`, and others read `D26–D28` and `RT1–4`. This is part of the new BLOCKER below. |
| S1 | fixed | §4 requires one `amended` entry for every body, `title` or `section` change, §7 refuses a change without one, and R1 tests it. |
| S2 | fixed | §5: `renumber` never rewrites under `docs/maxim_upstream/` and doesn't refuse to run. `check_records` refuses a new upstream citation of a lesson that isn't on the base. R1 tests that the branch's record is still renumbered while `main`'s record of that number is cited upstream. |
| S3 | fixed | §3: a slug-id decision is `<slug>.md`, unique in its log's directory, and the front matter has a `slug` key. The example now names `tile_and_client/`. R1 tests that a slug id makes a valid file name. |
| S4 | fixed | §2 now says 18 bullets, 13 with a bold lead, which is true; the decision counts are true at `1ed9caa`. §4 makes hand titles legal and `unknown` legal at the migration. One residue: see SF-A below. |
| S5 | fixed | §5: `lint_ids` names the PR that brought the second record, the owner starts the fix session, and `renumber --merged <PR>` rewrites the lines that PR's merge commit added against its first parent. R1 tests it. Merges on this repository are merge commits (`1ed9caa` "Merge pull request #72"), so a first parent exists. |
| S6 | fixed | RL12: the base is a fetched `origin/main`, and `renumber` and the change check refuse during an uncommitted merge. R1 tests a stale local `main` and the refusal. |
| N1 | fixed | §2's decision figures are now 1ed9caa's (164 rows, 154 ids, nine logs, plus this branch's log), which matches my count. |
| N2 | fixed | §5 defines id order: prefix, then number, then suffix, with slug ids after their log's numbered ids. |
| N3 | fixed | §3 and §7 now speak of `lint_contracts`' scope regex, widened to the `_header.md` files. |
| N4 | deferred | The author left it for the owner, because RL5 limits step 4's CLAUDE.md edits. Trigger: step 4, R3. |
| N5 | rejected | The author's reason holds: the same path on both branches is a git add/add conflict on the record file, which git itself reports and the session resolves; it never passes silently. |

### New BLOCKER in the fold

**§8 stage 1 (RL11): the closed `legacy` list can't reproduce today's decision cells byte for byte.**
- The fold dropped "the derived status column" from the round trip's exceptions, so the status cells must regenerate
  exactly. §8 says "A cell the fields can't derive is a converter bug, never a listed exception", and limits `legacy`
  to five listed facts, "and only those".
- Three kinds of cell on the tree are neither derivable from §4's fields nor on that list:
  - **First-cell qualifiers.** `D12, provisional` and `PH2-S2, re-ruled`. The id is `D12`, and no field holds
    "provisional". Stage 2 then drops it as "presentation only", although it is the ruling's standing.
  - **First cells of slug-id rows.** These are the `—` rows, `CLAUDE.md`, `D26–D28` and `RT1–4` (X-B1's residue).
  - **Status-cell wording.** The same field kind renders in four styles: "restates world_model §0" (stem and section),
    "restates `client_rendering.md`" (a backticked file name), "restates CLAUDE.md" (bare), and "restates realtime
    decisions 1–4". The last names no file: the nearest is `docs/design/realtime_lanes_coop.md`. Likewise "amended by
    docs-contracts ruling 41" has to come from `{path: …/docs_contracts/rulings.md, ruling: "41"}`.
- Failure: R2's byte-for-byte test fails on `client_rendering.md`, `sem_stimuli.md` and `tile_and_client.md`. Step 4
  then either writes per-row special cases into the renderer (a band-aid) or puts unlisted text into `legacy`, which
  §8 forbids. The brief says "Don't redesign", so the session stops at R2.
- A fix for the owner to weigh (unverified): add the original id and status cells to `legacy`'s list, and add a field
  for a ruling's qualifier, so that "provisional" survives stage 2.

**SF-A (SHOULD-FIX, mechanism, for step 4's R1 and R3 tests): "the migration commit" has no definition the lint can
read.**
- §4 and §7 make `unknown` and `legacy` legal "only in a record that exists at the migration commit", and refuse
  either one "written after it".
- `check_records` compares with the base, a fetched `origin/main`. In the migration PR itself every record is new
  against that base, and nothing names the commit.
- Failure: R3's first commit fails its own gate on every `unknown` and `legacy` field. Or, if the lint skips the check
  while the base has no records, the check is never tested before it matters.
- Deferred to R1 and R3 as a test: the migration PR passes, and a later record holding `unknown` is refused. Trigger:
  step 4, R1.
