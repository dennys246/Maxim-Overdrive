# Round 1: Executor

<!-- Kept verbatim, except that the late branch's lesson is written "lesson number `44`", which lint_ids does not read as a citation of a lesson not on main. -->

Reviewer: Executor lens. Scope: the staged change on `phase1/records-build` against `a5cf4bd` (R1 and R2), plus the lines RL14 folded without review. I read the brief, `records_layout.md` §3–§9, RL1–RL14 and the charter. I ran `tests/test_records.py`, `tests/test_records_branches.py` and `tests/test_records_migrate.py`: 138 passed in 13 s. For the mutations I copied the staged tree into the scratchpad (checked byte-equal to the index for every staged path) and broke 20 mechanisms one at a time against the three record test modules plus `tests/test_lint_ids.py`. Two tests can't run without a `.git`, so I deselected them: `test_lint_records_runs_alone_on_this_repository` and `test_the_real_tree_has_no_collision_and_no_dangling_citation`. I wrote nothing in the worktree.

While I was reviewing, unstaged edits appeared in `scripts/records_index.py`, `scripts/records.py` and `tests/test_records.py`. One of them is a `stray_lines` function that looks aimed at finding 1. I did not review those edits. Every finding below is against the staged tree.

## Findings

### 1. BLOCKER: `scripts/records_cli.py::index` (with `records_index.py::entries`): regeneration silently discards a hand edit inside an existing entry

§6 says "regeneration never discards text", and that `index` refuses and names `migrate-branch` when a generated file holds something no record holds. `stray_entries` compares only entry keys: a lesson's `### ` line, a gap's first `- ` line, a table row's first cell. An edit inside an entry keeps its key, so `index` overwrites it and exits 0.

Scenario, reproduced (scratchpad probe `p1.py`): a committed tree has lesson 1 and decision O1. In the generated files, change lesson 1's body to "Text, plus a late branch's hand edit." and O1's ruling cell to "Its text, hand-edited.", then run `cli.index`. Result: `rc 0`, and both edits are gone. This is the path §5 and §6 prescribe for resolving a conflict ("runs `scripts/records.py index`"). It is also the case `migrate-branch` exists for: a late branch's edit of an existing lesson that merged cleanly into the generated file. `lint_records::generated` would flag the file as differing, but only before the session runs `index`. After `index` there is nothing left to flag.

No test covers this. `test_index_refuses_a_generated_file_holding_an_entry_no_record_holds` adds a new key only.

### 2. SHOULD-FIX: `scripts/records_branch.py::_edited`: migrate-branch overwrites main's own amendment of the same lesson

`body = new.body` takes the branch's version of the text, which was written against the pre-migration base. It applies that over `mine`, main's current record, and never checks whether main changed the body since the base.

Scenario, reproduced (`p5.py`): main amends lesson 1 to "The first, as main corrected it." with an `amended` entry. A late branch (not yet merged) edits lesson 1 in the old file. `map_changes` writes the branch's body and appends its own amended entry. Main's text is lost with no refusal, but main's trail entry survives, so the trail now describes an edit that is no longer in the body.

This is low risk for the two named late branches, which only add records. It is real once sessions fan out after R3. The test `_assert_migrated` uses a `main` that never edited the lesson. Proposed fix (unverified): refuse by name when `mine.body != old.body`, or when any moved field differs between `mine` and `old`.

### 3. SHOULD-FIX: `scripts/records_lint.py` → `scripts/lint_records.py::prose_agrees`: the `closes_at` half of "One owner per fact" is not checked

§4 says: "A gap's `gate` and `closes_at`, and a backlog row's `status`, are also stated in prose today … `check_records` refuses a field that disagrees with it." §7 repeats this. The code checks `gate` (as a substring of the body) and backlog `status`, but not `closes_at`. The module docstring narrows the claim to `gate` only, so the docstring is honest, but the design's refusal is missing. §9 R1 requires "every refusal in §4 and §7". Scenario: a gap whose body says "closes at step 7" with `closes_at: step 9` passes the lint.

### 4. SHOULD-FIX: no code or test for §4's "`amended_by_external` … Only the migration writes it"

`lint_records::changes` refuses `unknown` and `legacy` in a record added after the migration, but not `amended_by_external`. Scenario: a new post-migration decision with `amended_by_external: [{path: docs/design/reviews/docs_contracts/rulings.md, ruling: "41"}]` passes, as long as the ruling row exists. §7's bullet list omits this rule too, so the design states it in one place and checks it nowhere.

### 5. SHOULD-FIX: refusals and choices with no deletion proof (each mutation stayed green)

13 of my 20 mutations went red. These 7 survived:

| Mutation | What it shows is untested |
|---|---|
| `lint_records.py::changes`: drop the `legacy` changed-on-an-existing-record check | §7's "a `legacy` field written after it" is proven only for new records (`test_unknown_and_legacy_are_the_migrations_alone`), never for an existing record whose legacy is rewritten. |
| `lint_records.py::_duplicate_fix`: drop `and count(branch) == 1` | "and the branch leaves one" (§5) is untested. A branch that deletes both duplicates passes. |
| `records_cli.py::stray_entries`: drop HEAD's generation from `allowed` | `test_index_regenerates_after_a_gap_is_deleted` cannot fail when this is deleted: both fixture gaps share the default body, so the deleted gap's key is still generated by the other. With distinct bodies the mutated code refuses with rc 1 (`p4.py`); the real code passes with rc 0. This is a test that cannot fail for the mechanism it relies on. |
| `records_branch.py::map_changes`: drop `_same_but_legacy` | No test inserts a decision row or a gap mid-file (a position shift) on a late branch. Without the guard, every later row in that log would be refused as "edited". |
| `records_branch.py::_edited`: always drop `slug` from `moved` | The title-changed condition is untested. |
| `records_renumber.py::rename_records`: drop `family_of_id(record.id) == record.family` | Untested. A decision whose id is shaped `B5` would be renamed by `B5=B6`. |
| `lint_records.py::upstream_citations`: drop the `n not in before` allowance | Untested. |

For reference, these went red: the trail-only-grows check, the `gate` prose check, the `\x00` refusal in `Line`, the calendar-date check, the gap id-is-slug check, the external-ruling and section existence checks, the REVIEWS exclusion, the `diff --git` reset in `hunks`, the `unsafe` (hand-resolved) rule, the `restates_ok` meaning bypass, and the slug-id exclusion in `lint_ids::duplicate_records`.

### 6. SHOULD-FIX: `scripts/records_git.py::Git.hunks`: path parsing breaks on quoted names, names with spaces, and `diff.noprefix`

`current = line[6:]` assumes `+++ b/<path>` exactly. Reproduced (`p2.py`):
- `docs/café.md` keys as `/docs/caf\303\251.md"`;
- `docs/a b.md` keys as `docs/a b.md\t` (git appends a tab);
- with `diff.noprefix=true` in the repository or user config, every path loses two characters (`cs/notes.md`). The CLI runs git with the user's own environment and config.

Effect on `renumber`: the branch's own lines are never matched, so its citations are listed instead of rewritten. That fails safe, but it is wrong. Effect on `--merged`: `merged_own` runs `git show <merge>:<bad path>` with `check=True`, which crashes with `CalledProcessError`.

`scripts/lint_repo.py::tracked_text_files` documents exactly this lesson ("home_paths review F3": use `-z`, or a quoted name skips silently). Proposed fix (unverified): `--src-prefix=a/ --dst-prefix=b/`, plus `-c core.quotePath=false`, or `-z` parsing.

### 7. SHOULD-FIX: `scripts/records_cli.py::renumber`: an untracked file's citations are neither rewritten nor listed

`files = {**git_tracked(git), **tree_files(root)}`. `tree_files` defaults to the record directories only. `Git.hunks` deliberately counts untracked files as all-added, but their text never enters `files`. Scenario, read from the code: a session writes a new, uncommitted `docs/plans/x.md` citing O5, then runs `renumber O5=O6`. The citation stays O5 and appears in no listing. That breaks §5's "lists … every citation of an old id".

Related: `hunks` reads every untracked non-ignored file with `read_text(encoding="utf-8")`. An untracked binary (a new golden PNG, say) raises `UnicodeDecodeError`. `renumber` doesn't catch it, so the user gets a traceback.

### 8. SHOULD-FIX: `migrate-branch`'s "after a clean merge" path is proven only on today's form, which main never carries after R3

`test_migrate_branch_after_a_clean_merge_of_main` merges a main whose generated files are in today's form, where only the marker line changed. RL14's §4 and §9 put R3's presentation commit in the same PR as the migration, so once R3 merges, origin/main's generated files are in §6's forms. `records_branch.old_files` and `_parsed` then feed §6 text (the lessons index, `amended` trails, id-ordered rows, kind groups) into today's parsers: `lessons`, `gaps`, `backlog` and `split_log`.

Two outcomes are possible: a `MigrationError`, or worse, a body that absorbs the rendered trail, which `_edited` then writes into the record. The before-merge path (base still pre-migration) is unaffected, and it is the one the two late branches will use if they run it before merging. The after-merge claim in §8 and in the module docstring is therefore unproven on the shipped path. R3 must either teach the parsers §6's forms or refuse the after-merge case.

### 9. NIT: `scripts/records_decisions_build.py::_with_legacy`: legacy is a catch-all for any differing cell

`legacy |= {c: o … if o != r}` stores any of the five cells whenever rendering differs. Only `status` is held to "means the same" (`_same_meaning`). §8 lists which facts belong in `legacy` and says "only those … a cell the fields can't derive is a converter bug, never a listed exception". If the converter had a parse bug in `who`, `owner_section` or `ruling` on a single-log row, the bad cell would be stashed in `legacy`. The byte-for-byte proof would still pass, and R3 would drop the cell.

I counted what the fixture actually stores (`p3.py`). Everything is within §8's list: 15 slug-id `id_cell`s, 1 non-ISO `who_date`, 9 + 9 cross-listed `owner_section` and `ruling` cells, 14 `status` cells, and 1 empty `owner_section` (which is also `unknown`). So this is latent, not live.

### 10. NIT: `tests/test_records.py::test_the_fixtures_are_todays_files` checks existence, not content

The test's name claims the fixtures are today's files, but it only asserts that each fixture path exists in the tree. Main can move, or add a new decision log, without the test noticing. I checked by hand: the fixtures equal both the worktree and `origin/main` (`a5cf4bd`) today.

### 11. NIT: `scripts/records_renumber.py::merged_own`: `--merged` matches "own" lines by text, file-wide, and doesn't fetch

If both PRs added an identical line to one file (a `- O5` list item, say), both copies are rewritten. The `--merged` path also never calls `fetch_base`, so a stale `origin/main` gives "0 merge commits". That is loud, but it departs from RL12. Similarly, `lint_records.main` and the gate compare against the last-fetched `origin/main`, not a freshly fetched one.

### 12. NIT: `tests/test_records.py::test_the_migrated_tree_passes_every_record_check` reads with `read_text()` and no encoding

In one of my subprocess runs it failed with `UnicodeDecodeError: 'ascii' codec`, after `test_generation_is_byte_identical_in_other_locales_and_time_zones` had cycled locales in the same process. I could not reproduce it from my shell, so it is environment-dependent. Passing `encoding="utf-8"` removes the dependence.

## The round trip

The round trip goes through record files for every family. `test_the_migration_round_trips_todays_four_files_byte_for_byte` runs `record_text` on every migrated record and then `load_records` (that is, `read_record`). It asserts the reread records equal the originals and that no record was refused, generates from the reread records, and compares each of the 14 originals (11 logs plus 3 files) exactly with `rest == original` after stripping only the marker line. Indexing into `out[path]` means any missing generated file raises. The comparison is exact. Its only blind spot is finding 9: legacy can absorb differences.

## The §9 test lists

Every R1 and R2 item has a test with a matching name, and I read each one. The gaps are:
- findings 3 and 4 (refusals with no code);
- finding 5 (no deletion proof for the existing-record `legacy` refusal or for "the branch leaves one");
- the brief's "added lesson" for `migrate-branch`, which is present (lesson number `44` in `LATE_EDITS`).

The locale and time-zone test passes, but generation reads no locale anyway.

## The lines RL14 folded

- **§4 `qualifier`.** It is built consistently: `_ID_CELL` accepts both `, q` and ` (q)`, and D12 and PH2-S2 render without legacy. One design defect: "provisional" is a ruling's standing stored in an immutable file. §4 says status is "derived … never stored". Once a later ruling confirms D12, its id cell still reads "D12, provisional" and the file may never change. "re-ruled" is a historical fact and is fine. SHOULD-FIX, for the owner: either `qualifier` is a historical label only, or "provisional" becomes a derived standing.
- **§4's second one-time exception (R3's presentation commit).** The code allows removing `legacy` at any time, not once. That is equivalent in practice, since `legacy` exists only between R3's two commits. But during R3, origin/main holds no records, so `changes()` sees `migrated=False` and checks nothing: §8 stage 2's "changes no record's `id`, `slug`, `title` or relation fields" has no check and is held by review alone. A possible check (unverified): R3 runs `lint_records.py --base <R3's first commit>`. That would hold decisions and lessons unchanged, though not gap or backlog bodies, which are mutable anyway.
- **§8's widened `legacy` list and corrected stage 2.** Consistent with the build in what is actually stored (finding 9), apart from the catch-all mechanism.
- **§9 R3's one PR.** Consistent. Note that R3's presentation commit is code as well as presentation. It needs:
  - the §6 generators (`TODAYS_FORM=False` has no renderer yet);
  - the lessons index, which is RL9's detector for lessons;
  - the parser work from finding 8.

  So "reviewed as presentation only" cannot cover that diff, and the delta round should be told so.

## What I ran

- Scratchpad probes `p1.py` to `p5.py`: findings 1, 6, 5 (the HEAD-allowance row), 9 and 2, in that order.
- `mut.py` and `mut2.py`: the mutation runs.
- `scripts/lint_records.py` and `records.py index` on the real worktree: not run, because the permission classifier refused it. From reading the code, `index` is vacuous on today's tree (no `_header.md`, so it writes nothing).
