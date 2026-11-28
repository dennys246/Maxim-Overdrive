# Fold of round 1 (author's account)

What the author did for each round-1 finding. The **Status** column is the delta round's to set (O25), and it set
them in `delta.md` §1, which is the record: there, B-1/E1, A3/SF-2, A4 and N-2 are **open, in part**, so this note's
account of them overstated the fold: a reviewer
writes `fixed`, `deferred` (with its reason and trigger), `rejected` (with a reason) or `open`, read from the tree.
Every fold below ships with a test, and each mechanism the folds added was proven by deleting it: 43 scripted
mutations, every one red (the commit lists them).

Prefixes: A Architecture, W Wire integrity, C Concurrency and lanes (the report's B-n and SF-n), E Executor.

## BLOCKERs

| Finding | The author's fold | Status |
|---|---|---|
| C B-1, E1 | `records_index.stray_lines` is the one rule for a hand edit: a generated file's line that no known generation produces. Line by line, so an edit inside an entry counts. `index` refuses with it, writing nothing. `lint_records.generated` uses it too, and names the right remedy for each case. Tests: an in-entry edit is refused and survives; a stale file says run `index`. | |
| W1, C B-2 | `migrate-branch <branch> --into <worktree> --hand <file>` runs from an `origin/main` checkout and writes into the late branch's worktree, as §8 says. Every command acts on the repository it is run in (`cwd`'s top level), never the script's. Test: the CLI run from a main checkout into the branch, which leaves the main checkout clean. The after-merge path on a §6-form `main` is deferred to R3 (W1's second half, C SF-5, E8). The hand file's home is an owner question (below). | |

## SHOULD-FIX

| Finding | The author's fold | Status |
|---|---|---|
| A1 | Not changed: §3 places a cross-listed decision in "the first of its logs by name", so D20 goes under `client_rendering/` as the design says. That contradicts §6's "owning design". This is a contract question for the owner, below. | |
| A2, W2, E3 | `records.stated_status` is the one reading of a backlog row's prose: the converter takes the field from it, and the lint holds the field to it. A bold **done** limited to a scope ("for enumerations") reads as done in part, so B36 migrates as done in part. `closes_at` is now held to the body like `gate`. The 26 `unknown` statuses (corrected from 28 by the delta round) are R3's to resolve, by hand and listed. | |
| A3, C SF-2 | Folded with B-1. The lint's message says "stale: run index" when every line comes from the tree's or the base's generation. `index` also allows HEAD's, the base's and MERGE_HEAD's generations, so a committed record change that wasn't regenerated passes. | |
| A4, W4, W5, C SF-1 | `migrate-branch` refuses a dirty worktree, and refuses by name a file whose head the branch changed. It never overwrites a record the worktree holds; it writes main's missing records with main's bytes. It prints every generation problem. | |
| A5 | Owner question (below): the hand file is a contract between the migration and every late-branch run. | |
| W3 | Owner question (below): cross-listed decisions' per-log owner sections. | |
| W6 | The alias is now `docs/design/realtime_lanes_coop.md §Decisions`, which the relation check resolves. Hand aliases, kinds and `closes_at` are listed with the titles. | |
| C SF-3 | Deferred to R3: the lessons index head (RL9's lessons detector) arrives with §6's form. R3's delta adds the branches test. | |
| C SF-4 | Test added: two branches adding B2 conflict in the backlog table, and the duplicate is caught. Residual: two rows with byte-identical text merge cleanly, because the backlog table has no slug column; `lint_guards` still catches the duplicate at the gate. | |
| C SF-5, E8 | Deferred to R3, as above. | |
| C SF-6 | `--merged` lists, and doesn't rewrite, a line its merge's hunk changed from one already citing the old id. Test added. | |
| C SF-7 | `lint_ids`' message names `renumber --merged <PR>` for main, and the `git log` command that names the PR. The test runs that command. | |
| E2 | `migrate-branch` refuses, by name, an edit to a field main also changed since the branch's base. | |
| E4 | `lint_records` refuses `amended_by_external` in a decision added after the migration. | |
| E5 | Each of the seven surviving mutations now has a test that fails: existing-record legacy, "the branch leaves one", the HEAD allowance (distinct bodies), a row inserted mid-log, the retitle keeping its slug, the family check in `rename_records` (a decision shaped `B5` is not renamed by `B5=B6`), and the upstream base allowance. | |
| E6 | `Git.hunks` runs with fixed prefixes and `core.quotePath=false`, drops git's tab suffix, and skips untracked binaries. Test: a non-ASCII name with a space, under `diff.noprefix`. | |
| E7 | `renumber` reads untracked files too, and a failed git call is a refusal, not a traceback. Tests added. | |
| E (RL14) qualifier | `qualifier` is a closed vocabulary (`provisional`, `re-ruled`), A10's fix. Whether a stored "provisional" is right at all is an owner question, below. | |

## NITs

Fixed: W7 (`Line` refuses YAML's other line breaks, and `|`); W8 (the docstring); N-1 (two ids to one, and a
rename onto a record's path, are refused); N-2 (git failures); A6 (`TODAYS_FORM` and the `legacy` fields carry
`TEMPORARY(phase1/records-build)` markers, listed in roadmap step 4's row); A8 (one owner for the marker line and the
table head); E10 (the fixtures are compared byte for byte, and a new log is caught); E12 (UTF-8 reads). Also a bug
the folds' tests found: `renumber` rewrote citations inside generated files; it now skips them, since `index`
rebuilds them.

Also folded, though no reviewer found it: the full WIP gate showed the locale test left the process in the C
locale, which broke 76 later tests under `LANG=en_US.UTF-8`. It now restores the locale it found, and was shown
red first under that `LANG`.

Left, each with its trigger: A7 (`lint_guards` globs disk; trigger R3, when its table reader goes); A9 (renumber's
lesson scope in `tests/`; the next renumber change); A11 (`records.py` loads twice as `__main__`; an identity check
across modules); A12 (named in the PR); A13, E11 and C N-3 (the gate compares with the last fetch; a stale base
failing loudly is the signal); W9 (§8's legacy list omits `three_cells` and an empty owner-section cell; the next
design edit); W10 (removing `legacy` is allowed at any time; R3, where it ends); W11 (blank lines in a gap's body
under today's form; R3's §6 form); W12 (record paths as citations; R3's brief edits); W13 (D12's title carries its
qualifier; R3's presentation commit); C N-4 and N-5 (caught by the merge or by review); E9 (legacy as a catch-all;
latent, counted within §8's list).

## Questions for the owner (contract; none blocks R1–R2, all block R3)

1. **A1:** where does a cross-listed decision's file live? §3 says the first log by name, which puts D20 (world_model's
   ruling) under `client_rendering/`, and §6's index then names client_rendering as its owning design. The
   alternative is the log whose row isn't a restatement.
2. **W3:** cross-listed decisions' per-log owner sections (O3–O7a, T1, T2, D20) are kept only in `legacy`, and R3
   removes `legacy`. Should they be a per-log field, or be dropped by name at R3?
3. **A5, W1:** where does the migration's hand file live after R3? Every `migrate-branch` run needs it.
4. **E (RL14):** `qualifier: provisional` stays in D12's immutable record after a later ruling confirms it. Is a
   qualifier a historical label only?

## The owner's rulings on the delta round (2026-11-27)

The delta round (`delta.md`) found one BLOCKER, D1, which the stop rule sends to the owner. The owner ruled in session:

- **D1: a seal in the marker line.** `index` writes the SHA-256 of each generated file's body into its marker line
  (`records_index.seal`). A file whose body still matches its seal is untouched since `index` wrote it, so it
  regenerates freely: the authoring loop, `renumber` on an uncommitted record, and a committed record change
  without `index`, delta D1's three scenarios. Outside a merge, any other body is an edit and is refused by name, a
  removed or moved line included, which also folds **D2**. During a merge, only a line no side's generation produces
  is an edit (`records_index.edit_found`, the one rule `index` and the lint share). §6's marker contract gains the
  seal. The design is not edited here (the brief: don't redesign), so R3 records this ruling where §6 can cite it.
- **D3, D4 and D5 are deferred to R3**, the trigger, where R3's own rounds read their folds.

The D1 fold landed after the delta round, so no review round has read it: the stop rule allows none. It ships with
tests for each scenario, and 5 new mutations of the seal, plus 4 of `index`'s merge allowances, all go red. Delta N4 is
folded with them: a merge whose conflict is resolved to either side, and under diff3, now has a test, and dropping
the HEAD, MERGE_HEAD or base generation turns it red. The lint's base generation is removed, since outside a merge it
only chose a message. N1 to N3 are left, with trigger R3.
