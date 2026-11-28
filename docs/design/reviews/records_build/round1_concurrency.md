# Round 1: Concurrency and lanes

<!-- Kept verbatim, except that the scratchpad path is written <scratchpad> (the public tree holds no home path, B45) and the late branch's lesson is written "lesson number `44`", which lint_ids does not read as a citation of a lesson not on main. -->

Reviewer: Concurrency and lanes. Tree: `phase1/records-build`, staged diff against `a5cf4bd`. I wrote probes only under the review scratchpad. They used the tests' own helpers (`tests/_records.py`, `tests/_gitutil.py`), in throwaway repositories made in the scratchpad with `isolated_env()`. I ran no suite and no gate.

## What holds

- **The decisions index conflicts as designed.** When two branches add the same new id, both insert their index line after the same anchor line in the base, so git conflicts on the second merge. This holds for one id taken in two different logs (one prefix, one family) and for a branch that adds several ids. Same id with same slug is an add/add conflict on the record file, unless the files are byte-identical, in which case it is one record. The backlog table is generated in id order and appends at the end, so it conflicts the same way. No probe was needed for the backlog; only decisions are tested (see SF-4).
- **`renumber` takes its base correctly.** Its base is the merge base with a freshly fetched `origin/main` (`records_git.py::Git.fetch_base`). It refuses during an uncommitted merge. It lists lines from `main`, and lists a hand-resolved line whose hunk removed a line citing the old id (`own_lines`' `unsafe`). It skips frozen files and `docs/maxim_upstream/`, and skips decision and `B` tokens under `docs/design/reviews/`. It applies a range mapping in one pass. The stale-local-`main` test is the right shape: the merge base with `origin/main` is the `main` commit the branch actually merged.
- **`lint_records` gets the gate's base.** `lint_standards.py::record_problems` passes the gate's `--base` (`prepush.sh` passes `origin/main`) and refuses the change check during a merge. On CI's `pull_request` merge ref, the base is `origin/main` itself, which is correct. On a push to `main` the change check compares main with itself. That is fine, because `lint_ids` carries the duplicate check there.
- **`lint_ids` covers a mixed tree.** Once records exist it reads only records. A cleanly merged hand row (D38 in a generated log) is then invisible to `lint_ids`, but `lint_records::generated` flags it as a stray entry and names `migrate-branch`. So the gate still sees it.
- **Isolation is consistent.** Tests pass `isolated_env()`. The CLI passes `os.environ` on purpose, the same as `lint_repo`. `ALLOWED_SPAWNS` names `records_git.py::_git`. I found no fixed temp path and no write to the home directory.

## Findings

### B-1 (BLOCKER): `records_cli.py::stray_entries` / `records_index.py::entries`: `index` silently discards hand-edited text inside an existing entry

**What is wrong.** `entries()` keys each generated file on one thing per entry: a lesson's `### ` heading, a gap's first bullet line, or a table row's id cell. `stray_entries` refuses only when a key is unknown. Any edit inside an existing entry keeps a known key, so `index` regenerates over it and exits 0. That covers:
- a lesson body;
- a gap's continuation lines;
- a decision row's ruling, who/date or owner cells;
- any header prose above the entries.

`lint_records::generated` makes this worse. For the same state, it finds no stray key, so it tells the session to "edit the records or the _header.md it is made from, then run `scripts/records.py index`", which is the command that destroys the edit.

**Failure scenario.** `phase1/slice2-design` also amends an existing lesson's body in the old file. After R3, its merge of `main` goes through cleanly. Its gate says to run `index`. It runs `index`, and the amendment is gone with exit 0. A decision-row edit (which `migrate-branch` would refuse by name) disappears the same way. This breaks §6's "regeneration never discards text".

**Verified.** Probe `probe1.py` case 1: a lesson whose body was hand-edited in the generated file and committed. `cli.index` returned 0 and the edit was gone. Case 3: `lint_records.generated` printed the "run `scripts/records.py index`" message.

**Fix (unverified).** Refuse whenever the current file differs from both the new regeneration and HEAD's regeneration anywhere outside a conflict region, not only on unknown keys.

### B-2 (BLOCKER): `scripts/records.py` `__main__` (`root = Path(__file__).parents[1]`), `records_branch.py::migrate_branch`: the before-merge path of `migrate-branch` can't be run by the two late branches

**What is wrong.** A late branch forked before this change has no `scripts/records.py` in its tree. Its editable venv also lacks `simcore.adapters.loaders.read_yaml_text`, which `records.py` imports and which this change adds. So the session can only run another checkout's script, with another checkout's venv. But `root` comes from that script's own location. Every git call and every write then targets the other checkout, never the branch's worktree:
- `migrate-branch` refuses there, because that checkout's HEAD isn't the branch.
- `index` and `renumber` have no HEAD check, so run that way they write into the other checkout. That is the owner's main checkout or another session's worktree.

§8 says the tool "writes its result into the branch's worktree" and "works before the branch merges `main`". The tests call `branch.migrate_branch(work, …)` with `root` passed in directly, which hides this. On the shipped entry point, only the after-merge path is reachable. B-3 below argues that path will usually not be a clean merge once R3 lands, which would leave `phase1/regions-design` (D38) and `phase1/slice2-design` (lesson number `44`) with no working route.

**Verified by reading.** `records.py` lines 457–461 and line 35, and the `loaders.py` diff (`+def read_yaml_text`). I did not run it against another worktree, which this review may not touch.

### SF-1 (SHOULD-FIX): `records_branch.py::_parsed` / `migrate_branch`: `migrate-branch` drops header edits and overwrites uncommitted edits, with exit 0

**What is wrong.**
- `_parsed` keeps only `[1]` (the entries) from `lessons()`, `gaps()`, `backlog()` and `build()`. A branch's edit to a file's head prose is therefore never mapped and never refused. `migrate_branch` then writes `main`'s `_header.md` and the regenerated files over it.
- It reads only the committed tip (`files_at(branch, …)`), yet overwrites the working-tree old files. Uncommitted edits to the four files are lost silently.

§8 says each edit is mapped "or refused by name".

**Verified.** Probe `probe4.py`, on the test's `_migrated_main` fixture:
- an uncommitted lesson 45 appended to the lessons file was gone afterwards;
- an edit to the backlog's head ("The head, edited by the late branch.") was gone;
- `migrate_branch` returned 0.

**Fix (unverified).** Refuse when the old files or record directories are dirty. Map or refuse a head diff by name.

### SF-2 (SHOULD-FIX): `records_cli.py::stray_entries`: `index` wrongly refuses after a committed record change that wasn't regenerated, and points at the wrong tool

**What is wrong.** The allowed set is "now" plus HEAD's regeneration. If a session commits a record change and only then runs `index`, the generated file's old entry is in neither set. Two cases:
- a committed gap deletion (deleting a gap is allowed);
- a committed lesson retitle.

`index` then refuses with "a hand edit … `migrate-branch`". `migrate-branch` is the wrong tool here. The only way out is a hand edit of the generated file, which the rule forbids. The same refusal happens when the record change arrives in a commit the session merged from `main` before regenerating, if `main` itself skipped regeneration.

**Verified.** Probe `probe2.py`. A committed deletion of `a-gap.md` made `index` return 1 (`holds '- **A gap.** One.'`). A committed `title: One` → `Uno` also returned 1.

**Related (NIT, unverified).** With `merge.conflictStyle=diff3`/`zdiff3`, a conflict region's base section can hold a lesson heading or gap first line that is in neither side. `index` would then refuse during a merge it should resolve.

### SF-3 (SHOULD-FIX, trigger R3): the lessons family has no pre-merge detector in today's form

**What is wrong.** In today's form, lessons are placed by section and then by id. Two branches adding lesson number `44` in different sections insert at different points. git merges cleanly, and GitHub would merge the second PR. Only `lint_ids` then sees the duplicate: on `main` after the fact, or at the next gate of a branch that merges `main`. RL9's id-ordered lessons head is not built in this branch. `TODAYS_FORM = True`, and the §6 form arrives only in R3's presentation commit.

**How big the window is.** On `main` the window is zero only if R3 really lands both commits in one PR (§9 says it does). The R3 delta must add a branches test that two lessons in different sections conflict in the generated file. Today `test_two_branches_adding_to_one_family_conflict_in_its_index` covers decisions only. §9 R1 asks for "records to one family" and lists A-B1, which concerned every id-bearing family.

**Verified.** Probe `probe1.py` case 2: lesson number `44`-a ("World and physics") and `44`-b ("Time") on two branches. `git merge` returned 0, and `lint_ids` then reported `lessons id 44 is held by 2 records`.

### SF-4 (SHOULD-FIX): `tests/test_records_branches.py::test_two_branches_adding_to_one_family_conflict_in_its_index` covers only decisions

**What is wrong.** The backlog table is a detector named in §6, and `lint_guards` carries its duplicate check. No test shows two branches adding `B48` conflict in `docs/standards_backlog.md`, or that after `index` the duplicate check fires. A regression in `backlog_file`'s order or form would remove the detector with nothing going red.

**Verified by reading** the test's parametrization.

### SF-5 (SHOULD-FIX, trigger R3): `records_branch.py::migrate_branch` after a merge is tested only against a `main` in today's form, a state `main` will never be in

**What is wrong.** `test_migrate_branch_after_a_clean_merge_of_main` relies on "the marker line is the only line main changed near them". That holds only while the generator writes today's form. R3 lands the presentation commit in the same PR, so every late branch meets a `main` in §6 form. That changes two things:
- Its merge is unlikely to be clean. The decision logs re-sort by id, and the lessons file gains an index head.
- After a merge, `before`/`after` are parsed with today's-form parsers (`records_migrate.lessons`, `gaps`, `build`).

If the merge conflicts, `migrate-branch` refuses ("no merge in progress"), and its message doesn't tell the session to `git merge --abort` and run it before merging. Per B-2, the before-merge path isn't reachable either. R3's delta must rerun both paths against a `main` in §6 form.

**Unverified.** R3 isn't built.

### SF-6 (SHOULD-FIX): `records_renumber.py::merged_own`: `--merged` rewrites a hand-resolved line holding both citations

**What is wrong.** `merged_own` returns `Own({}, texts, {})` with `unsafe` empty. The PR's merge diff against its first parent includes any line its session resolved by hand when it merged `main`. A line holding both branches' citations matches by text and is rewritten whole, so the other PR's citation moves too. §9 R1 requires this to be "listed, not rewritten" (delta Concurrency N2). That requirement is met for the ordinary path only.

Matching by text also rewrites any identical line elsewhere in the same file that cites the old id. That case is rarer, but the same kind of error.

**Unverified by run, verified by reading** `merged_own` and `Own.holds`.

**Fix (unverified).** Mark as unsafe the added lines of hunks in `merge^1..merge` whose removed lines cite an old id.

### SF-7 (SHOULD-FIX): `lint_ids.py::duplicate_records` doesn't name the PR that brought the second record

**What is wrong.** §5 says `lint_ids` fails on `main` "naming both records and the PR whose merge brought the second". The message names both paths, then says to run `renumber <id>=<next free id>`. It names no PR and doesn't mention `--merged`. On `main`, the session doesn't know which PR to pass to `--merged`. It could also follow the message literally and run the ordinary `renumber`. On a fresh branch from `main`, both records are in the base, so that renames neither ("no record of this branch has it").

**Verified by reading** the message text.

### N-1 (NIT): `records_renumber.py::plan` / `parse_mapping`: no check that the new id is free

The docstring says "no old id as another's new", but the code doesn't check it. That case is harmless, because range shifts need it. What the code also misses:
- `O5=O7 O6=O7` is accepted. Verified: `parse_mapping` returned `{'O5':'O7','O6':'O7'}`.
- A rename onto a path `main` already holds silently replaces `main`'s record in the worktree. Verified: `plan` with `O5=O6`, where `main` holds `O6-x.md` and the branch's slug is also `x`, overwrote main's "Keep me." body.

`lint_ids` or `lint_records` catches both at the gate, but `renumber` exits 0 having done it.

### N-2 (NIT): `records_cli.py::renumber`: partial writes, uncaught failures, untracked files

- `renumber` writes its renames, then calls `index`. If `index` refuses (B-1/SF-2 states), it prints "nothing was written" after `renumber` has already written.
- `fetch_base`'s `git fetch` failing (offline) raises `CalledProcessError` uncaught, and so does `hunks()` on an untracked binary file. Both show as a traceback, not a refusal.
- Untracked files outside the record roots appear in `hunks` but not in `files`, so a citation there is neither rewritten nor listed.

### N-3 (NIT): `records_renumber.py::merged_commit` reads `origin/main` without fetching

RL12 asks for a freshly fetched base. If `origin/main` is stale, it refuses loudly ("0 merge commits"), so the failure isn't silent.

### N-4 (NIT): `records_branch.py::map_changes`: an added entry whose path `main` already holds replaces `main`'s record

If an added lesson or row's computed path (same id, same slug) is one `main` already holds, it replaces `main`'s record in the write set. Before the branch merges, nothing in the gate compares them, because the base holds no records. The later merge's add/add conflict catches it.

### N-5 (NIT): `lint_records.py::_duplicate_fix` can't tell which record a duplicate fix renamed

It allows renaming either of two same-id base records. It can't tell whether the fix renamed the second PR's record or the first's. `--merged` picks correctly; a hand rename isn't held.

## Answers to the brief's questions

- **Do two branches adding to one family conflict?** Decisions and backlog: yes. Lessons: no, not before R3's §6 form (SF-3).
- **`renumber`:**
  - its base: correct;
  - refusal during a merge: yes;
  - stale local `main`: correct;
  - hand-resolved line: listed on the ordinary path, rewritten under `--merged` (SF-6);
  - range mapping: correct;
  - frozen, upstream and review files: correct;
  - `--merged`: it finds the right merge commit by its message, and matching lines by text survives `main` moving.
- **`index`:** it refuses a new hand entry after a clean merge. It silently drops edits inside existing entries (B-1) and wrongly refuses after a committed record change (SF-2).
- **`migrate-branch`:**
  - after a clean merge, on a today's-form `main`: works for lesson number `44` and D38;
  - before a merge: only through the test's `root`, not the shipped entry point (B-2);
  - against a §6-form `main`: untested (SF-5);
  - by name, it refuses decision edits, deleted lessons and deleted rows;
  - head edits and uncommitted edits are lost silently (SF-1).
- **`lint_records`:** it uses the gate's base and refuses during a merge. Correct.
- **Can a duplicate still merge unseen?** Yes: lessons in different sections until §6 (SF-3). After that, `lint_ids` still catches it on `main`, but its message doesn't lead to `--merged` (SF-7).
- **Writes outside the worktree or an environment-named repository:** `index` and `renumber` run from another checkout's script write into that checkout (B-2). Otherwise the environment handling matches `lint_repo`.

Probes (scratchpad): `<scratchpad>/review/probe1.py`, `probe2.py`, `probe3.py`, `probe4.py`. `probe3.py` is superseded: its own `git add -A` committed the "uncommitted" edit, so it proves nothing. `probe4.py` is the corrected run.
