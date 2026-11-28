# Delta round: all lenses

<!-- Kept verbatim. One reader covered the four lenses in turn, over the fold's diff only (the author's choice for a
diff-only round; the charter asks for parallel readers, so this is recorded as a deviation). The report's escaped
line-break characters are written as   and  . -->

Lenses: Executor, Architecture, Wire integrity, Concurrency and lanes. Scope: `fold1.diff` (round-1 tree to fold 1) and, by the coordinator's addendum, `fold2.diff` (fold 1 to the current tree). I read only those diffs and the code they touch. I ran:
- the three record test modules on the current tree: 187 passed;
- `scripts/lint_standards.py --base origin/main`: PASS, 0 findings;
- probes `p1`–`p10` in `<scratchpad>/delta/`, in throwaway repositories built with the tests' helpers;
- 25 scripted mutations of fold 1's mechanisms against a copy of the fold-1 tree (`mut.py`), and 3 mutations of fold 2's (`m2/`).

Nothing in the worktree was edited.

Counts: 1 BLOCKER, 4 SHOULD-FIX, 6 NIT. Under the stop rule, D1 goes to the owner.

## 1. Fold status of round 1's findings (reviewer-set, read from the tree)

| Finding | Status | What I checked |
|---|---|---|
| C B-1, E1 | **open, in part** | Added and changed lines are now caught: `test_index_refuses_an_edit_inside_an_existing_entry` passes, and the HEAD-allowance and base-allowance mutations go red. Deleted and moved lines are still discarded with exit 0, and the lint calls the file "stale" (D2). The fold also brought a regression (D1). |
| W1, C B-2 | **fixed** (pre-merge path) | I ran the shipped entry point, `scripts/records.py migrate-branch phase1/late --into ../work --hand ../hand.yaml`, from a separate main checkout (`p10`). It wrote the four records into the branch's worktree and left the checkout it ran in clean. The `cwd toplevel` mutation goes red. W1's second half (the hand file's home, and the after-merge path on a §6-form `main`) is **deferred**: reason, R3 builds §6's form; trigger, R3, plus owner question 3. One residual with `--into` is D4. |
| A1 | **open** (owner) | Contract question 1. It blocks R3. |
| A2, W2, E3 | **fixed** | `records.stated_status` is the one reader of the prose. `p2` ran the old and the new parser over the fixture backlog: the only difference is B36, which is now `done in part`. `closes_at` is held: the `closes_at prose` mutation goes red. fold.md says 28 `unknown` statuses; the fixture gives **26** (26 unknown, 17 open, 3 done, 2 done in part). The count is overstated. |
| A3, C SF-2 | **open, in part** | A line the base's records generate now reads as stale (`test_a_line_the_base_generated_is_stale_not_a_hand_edit`). A committed change to a record the branch itself added, made without running `index`, is still refused as "a hand edit" and points at `migrate-branch`, from both `index` and the lint (`p1` case c). See D1. |
| A4 | **open, in part** | First half fixed: an amended record the worktree holds is kept (`test_migrate_branch_keeps_a_record_the_branch_already_holds`; the `keep worktree records` mutation goes red). Second half not fixed: on the pre-merge path, main's records are still written as adds (D3). |
| W4, C SF-1 | **fixed** | The dirty refusal and the head refusal each have a test, and the `dirty check` and `changed heads` mutations go red. |
| W5 | **fixed** | `problems` is printed (read in `migrate_branch`). |
| A5 | **open** (owner) | Question 3. |
| W3 | **open** (owner) | Question 2. |
| W6 | **fixed** | The alias now ends `§Decisions`. `test_the_migrated_tree_passes_every_record_check` passes with the relation check on. The aliases, and the kinds and `closes_at` of gaps, are listed (read). |
| C SF-3 | **deferred** | Reason: the lessons index head is §6's form, which isn't built. Trigger: R3's presentation commit, whose delta adds the branches test. |
| C SF-4 | **fixed** | The test passes. A residual is accepted: byte-identical rows merge cleanly, and `lint_guards` catches the duplicate. |
| C SF-5, E8 | **deferred** | Reason and trigger as SF-3 (R3). |
| C SF-6 | **fixed** | `test_renumber_merged_lists_a_hand_resolved_line_holding_both_citations` passes, and the `unsafe_texts` mutation goes red. |
| C SF-7 | **fixed** | The message names `--merged` and the `git log` command, and the test runs that command and gets PR #2. |
| E2 | **fixed** | The test passes, and the `raced check` mutation goes red. |
| E4 | **fixed** | The `amended_by_external` mutation goes red. |
| E5 | **fixed** | Each of the seven has a test. I re-mutated the HEAD allowance (red) and the closely related checks above. I did not re-mutate `_same_but_legacy`, the slug drop or the family check, but their named tests pass. |
| E6 | **fixed** for the cases it reproduced | Non-ASCII names, a space and `diff.noprefix` are handled; the `fixed prefixes`, `quotePath` and `tab suffix` mutations each go red. Names holding `"`, `\`, a tab or a newline are still C-quoted (N1). |
| E7 | **fixed** | The `untracked in renumber`, `binary skip` and `git failure caught` mutations each go red. |
| E (RL14) qualifier | **fixed** (closed vocabulary; the `qualifier choice` mutation goes red). Whether a stored "provisional" is right at all stays **open** (owner question 4). |
| W7 | fixed | `\x85`, ` `, ` ` and `\|` are refused, with a test. |
| W8 | fixed | The docstring (read). |
| N-1 | fixed | Two ids to one, and a path collision, are each refused; both mutations go red. An id that isn't free but has a different slug is still left to the lint. |
| N-2 | **open, in part** | Git failures fixed. "`renumber` writes, then `index` refuses, then 'nothing was written'" is still there, and fold 1 made it more reachable (D1, second scenario). |
| A6 | fixed | The markers are in place, roadmap row 4 lists both files, and `lint_standards` passes. |
| A8 | fixed in part (author's NIT call) | The marker and the table head each have one owner. The family-root literals remain, with no trigger stated. |
| A10 | fixed | As the qualifier row. |
| E10 | fixed | Byte comparison, plus the new-log check. |
| E12 | fixed | The test now reads with `encoding="utf-8"`. |
| Left by the author (A7, A9, A11, A12, A13, E11, N-3, W9–W13, N-4, N-5, E9) | NITs, the author's call | Recorded with fold.md's triggers. I check none of them against those triggers here. E11's file-wide text match is separate from the fetch question it is grouped with, and stands as written. |

## 2. Defects in fold 1

### D1 BLOCKER: `records_index.py::stray_lines` with `records_cli.py::index` (and `known_generations`) refuse the ordinary authoring loop and `renumber` on an uncommitted record

The line-set rule accepts only lines that the working tree's records, HEAD's, the base's or MERGE_HEAD's generate. The generation `index` itself wrote a minute earlier, from records not yet committed, is none of these.

- **Scenario 1, the authoring loop** (`p8`). A session writes lesson 50 ("Draft text."), runs `index` (rc 0), revises the record to "Better text.", and runs `index` again. Result: rc 1, "holds 'Draft text.', which no record generates: a hand edit … `migrate-branch` …". Nothing was hand-edited. The same tree on the round-1 copy gives rc 0, so fold 1 introduced the regression.
- **Scenario 2, `renumber`** (`p7`). An uncommitted O5 record, indexed, then `renumber O5=O6`:
  - the rename is written;
  - `index` refuses, calling the old `| O5 |` row a hand edit, and prints "nothing was written" after `renumber` has written;
  - the generated log still names O5.

  The round-1 copy gives rc 0 with the index updated. The new generated-file skip in `rewrite_citations` is what exposes this.
- **Scenario 3, committed without `index`** (`p1` case c). A branch adds lesson 50 and indexes it, then commits a retitle without re-running `index`. `index` and the lint both report a hand edit.

None of these loses data: every refusal fails safe. But the shipped command is wrong for §5/§6's normal "edit the records, then run `index`" loop, and the remedy it names is wrong. The only way out, undocumented, is to delete the generated file (`p1`: rc 0 afterwards), which is exactly what the rule exists to prevent. That is "wrong on the shipped path". It goes live at R3, which is why it is a BLOCKER now.

Fix (unverified): the rule needs the generation the file was last written from. One option: `index` writes a hash of the file's body into the marker line. A file whose body matches its own hash is untouched since the last `index` and is regenerated freely; only a mismatched file is checked line by line. That covers B-1's committed hand edit, a merge, and all three scenarios. The marker line is §6's contract, so this needs the owner's ruling.

### D2 SHOULD-FIX: `records_index.py::stray_lines` lets a deleted or moved line through, and `lint_records.py::generated` calls it stale

A line that "only went missing" is not stray, and the allowed set is the whole file's lines.
- `p1` case a: a committed hand deletion of a lesson paragraph. The lint says "it is stale: run `scripts/records.py index`"; `index` gives rc 0 and restores the paragraph.
- `p1` case b: a paragraph moved from lesson 1 to lesson 2. rc 0, and the move is reverted.
- `p1b` case d: a decision row deleted by hand. The lint says "stale"; `index` restores the row.

Scenario: a late branch deletes a paragraph of a lesson, or a decision row, in the old file, then merges `main` cleanly. The gate tells it to run `index`, and the deletion vanishes with exit 0. `migrate-branch` would have refused a deleted row by name. This is the residual of B-1 ("regeneration never discards text"), at a narrower trigger. Fix (unverified): the hash in D1 also catches this, because any edit breaks the hash.

### D3 SHOULD-FIX: `records_branch.py::_writes` still writes main's records into a pre-merge branch as adds, so the later merge conflicts, and can revert main's edits

`p5`: `migrate-branch` before the merge, commit (13 files added), then `git merge origin/main`.
- With `main` unchanged since the run, the merge conflicts on `decisions_index.md`, `lessons/1-one.md` and `B1-a-rule.md`. These are add/add conflicts, because the merge base holds no records.
- If `main` amends lesson 2 after the run, `lessons/2-two.md` conflicts too, though the branch never touched it. Resolving with "ours" quietly reverts main's amendment.

This is A4's second half, unfixed. No test merges after the pre-merge path. Fix (unverified): write only the branch's own records before a merge, and let the merge bring main's (then `index`). Alternatively, say in §8 and in the command's output that the session must merge `main` immediately and resolve each conflict on a record the branch didn't change as "theirs".

### D4 SHOULD-FIX: `records_cli.py::main` resolves `--into` without `--show-toplevel`, so a subdirectory succeeds silently

`p4`: `--into <late worktree>/docs`, with an uncommitted edit present. The `git status` pathspecs and `ls-tree` paths are read relative to `docs/`, so the dirty check is vacuous, nothing is parsed, nothing is written, and the command exits **0** with "review the records … then commit them". `cwd` gets `rev-parse --show-toplevel` and `--into` doesn't. Fix (unverified): resolve `--into` the same way, and refuse a path that isn't a worktree's top level.

### D5 SHOULD-FIX (Performance): `records_git.py::Git.files_at` runs one `git show` per file, and `index` now reads two or three generations

`p6`, on the migrated fixture (326 files): one `files_at` takes 3.8 s, and `index` takes 8.0 s outside a merge. During a merge it reads a third generation. The cost grows with every record, and `index` is the command run after each record edit. Fix (unverified): one `git cat-file --batch` per revision. Optimize from this measurement, per the rule.

### N1 NIT: `records_git.py::Git.hunks` still mis-keys C-quoted names

`p3`: names holding `"`, `\`, a tab or a newline key as `/docs/a\"q.md"`, because `core.quotePath=false` doesn't stop that quoting. `renumber` then lists instead of rewriting, which fails safe. `--merged` refuses with "git show … failed" for any PR touching such a file. No tracked file has such a name today. Fix (unverified): `diff -z`, or unquote.

### N2 NIT: `records_cli.py::main` and `::known_generations` raise a traceback

`cwd` outside a repository raises `CalledProcessError` uncaught (`p4` case f). The same happens when `origin/main` shares no merge base with HEAD.

### N3 NIT: `lint_records.py::prose_agrees` checks less than before

It now skips any record whose prose states nothing (`unknown`). A post-migration backlog record with `status: done` whose prose doesn't state it now passes; before the fold, that read as `open` and was a finding. Separately, the "**done** for" rule would read a complete "**done** for every family" as done in part. B36 is the only such row today.

### N4 NIT: the MERGE_HEAD allowance in `records_cli.py::known_generations` has no test

`MERGE_HEAD` reaches git through the shared `git.merging()` code, but removing the generation it adds (the `index MERGE_HEAD allowance` mutation) kept 218 tests green. That is a test that cannot fail for that line.

## 3. Fold 2 (`fold2.diff`)

**`files_at`, blobs only and `.md` only: correct for every caller today.**
- `lint_records`' `BASE_PATHS`: four record roots, `docs/maxim_upstream/` and `lessons_maxim_in_games.md`. `_base_lessons`, `upstream_citations` (which filter `.md` themselves), `changes` and `generated` read nothing else.
- `records_cli.known_generations` and `renumber`'s `base_paths` read `ROOTS`, which are records and headers only.
- `records_branch` reads `origin/main` over `ROOTS`, and the base and branch over `TODAY` plus the decision logs, all `.md`.
- `lint_standards.record_problems` reads `BASE_PATHS` too.
- No tracked file under those prefixes is non-`.md`, no symlink is tracked anywhere, and the only `freeze.sha256` is under `spikes/`.

Two notes:
- A symlinked `.md` would be read as its target's path, because a symlink is a blob of mode 120000. That case is latent.
- `show` now runs with `check=True`, so a listed blob that fails becomes a traceback rather than a skipped file. That is better than skipping silently.

Proven: dropping `.md` turns `test_files_at_reads_markdown_blobs_only` red. Dropping the blob filter is not tested, because no test has a submodule. NIT.

**`lint_records.report`:** a pure extraction with a test. Fine.

**`test_generation_reads_no_clock_locale_or_environment`:** proven by adding `import time` to `records_index.py`, which turns it red. But `from os import environ` passes the scan: I added it, and the test stayed green. NIT: forbid `environ`, or scan imports through the AST rather than substrings.

**The locale test without time zones:** consistent with `test_determinism`'s scan, which passes, and it restores the locale. Dropping the TZ loop is justified only by the structural scan, which has the gap above.

**The new branch tests** (the converter refusals, the merge refusal, no `origin/main`, deleted and binary files, a PR with no merge commit): read, and all pass. None of them changes D1–D5.

## 4. For the owner

- **D1 (BLOCKER):** the fix touches §6's marker contract, so it needs your ruling.
- **Folds needed:** D2–D5 (SHOULD-FIX).
- **Still open, and blocking R3:** questions A1, W3, A5 and RL14.
- **fold.md overstates two things:** the "28 unknown" count (it is 26), and B-1 and SF-2 as wholly folded.
