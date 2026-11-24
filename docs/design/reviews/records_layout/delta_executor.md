# Records layout design, delta round: Executor (2026-11-24)

Read: the fold's diff `239f267..9d1e747` (design, rulings RL1–RL10, `fold.md`, two roadmap rows), checked against round
1's reports and the tree. Ran read-only git and `.venv/bin/python` one-liners: `lint_ids._decision_rows` over the
decision logs at `1ed9caa` and `9d1e747`, heading, bullet and row counts with `grep` and `git show`, whitespace word
counts per record, and a census of every decision log's first and status cells. Nothing was edited but this report.

## Round-1 statuses

| Finding | Status | Evidence |
|---|---|---|
| A-B1 | fixed | §1 withdraws the "stop conflicting" claim (RL9). §5 and §6 make the committed, id-ordered index the detector, and R1 tests it. Two insertions at one point always conflict in git's three-way merge, so the detector holds whenever both branches committed a regenerated index, and §7's regeneration check refuses one that didn't. |
| A-B2 | fixed | RL10: lesson bodies are mutable, with an `amended` trail (§4). The trail isn't enforced, though: see SHOULD-FIX S1. |
| A-B3 | fixed | §5 defines a family as an id prefix across every log, which is what `lint_ids` holds. Cross-listed rows become one record with `also_in`, and restating and id-less rows get slug ids. The slug-id file name is undefined: see S3. |
| A-B4 | open | External rulings are covered now (`amends` takes a path and an anchor), but the four fields still can't carry every status cell on the tree. The census at `9d1e747` finds "confirmed by O69" (twice), "confirmed by O74", "corrected by O73", and seven `restates` cells whose target isn't an id ("restates world_model §0" four times, "restates boundaries §0" twice, "restates CLAUDE.md", "restates realtime decisions 1–4", "restates `client_rendering.md`"). §4 makes `restates` a list of ids and has no confirm or correct relation. R2's test "every non-`live` status cell derives back to its meaning" would go red on these, and §8 forbids dropping them ("none loses information"), so step 4 can't build what the design says. This is a contract gap. |
| C1 | fixed | The same defect as W1. §1 withdraws the PR-CI claim, RL8 keeps "require up to date" off, and §5's detector stops the second merge with a conflict, which GitHub refuses whether or not the branch is protected. R1 tests it (A-B1, C1, W1). |
| C2 | fixed | §4's exception and §5's "A duplicate on `main`" allow the rename only while `main` holds two records, and R1 tests that case. The rename's citations and who opens the fix branch are left: see S5. |
| C3 | fixed | §5: `renumber` rewrites only lines the branch added or changed against the merge base, and lists `main`'s lines. R1's shared-file test goes red under a whole-file rewrite. One ordering case is left (S6). |
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
