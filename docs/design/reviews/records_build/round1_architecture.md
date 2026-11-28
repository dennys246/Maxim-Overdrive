# Round 1: Architecture

Reviewer: Architecture lens. Scope: the staged diff on `phase1/records-build` against `a5cf4bd` (R1 and R2), the brief `docs/plans/next_steps/4_records_build.md`, `docs/design/records_layout.md`, and RL1 to RL14.

What I ran:
- a probe at `<scratchpad>/review/arch_probe.py`, which runs `records_migrate.migrate` over `tests/fixtures/records/today/` with `tests/fixtures/records/hand.yaml`, then regenerates and lints;
- `scripts/lint_records.py`: PASS, 0 findings;
- `scripts/lint_standards.py --base origin/main`: PASS, 0 findings.

I did not run the suite or the gate.

## Summary

The format has one owner (`records.py::read_record`, with `record_text` as its one writer). The loaders' change is the minimal text-level entry point that §4 and §7 ask for. There are no import cycles: `lint_ids` → `records` → `simcore`, and `lint_records` / `records_renumber` → `lint_ids`. The TEMPORARY dual reading is a legitimate scheduled band-aid (judged below).

The real problems:
- One code choice becomes permanent at R3: where a cross-listed decision's file lives.
- One part of the "one owner per fact" proof is missing (`closes_at`).
- One check names the wrong remedy.
- `migrate-branch` can silently overwrite a branch's own record.
- The hand file is an interface between steps that the design never names.

Counts: 0 BLOCKER, 5 SHOULD-FIX, 8 NIT.

## Findings

### A1 SHOULD-FIX: a cross-listed decision lives in one log's directory but takes its fields from another's

`scripts/records_decisions_build.py::build` and `::_raw`, with `scripts/records_decisions.py::primary`.

Two different rules pick a cross-listed decision's "own" log:
- `primary()` takes the fields from the first log *that does not restate*.
- `build` puts the file in `sorted(r.log for r in group)[0]`, the first log by name, and `also_in` is everything else.

For D20 these disagree. The probe printed:

```
docs/design/decisions/client_rendering/D20-one-simulation-truth.md cites §1 ('world_model',) ()
| D20 | one-simulation-truth | One simulation truth. | `client_rendering.md` | live; also in `decisions/world_model.md` |
```

The failures:
1. `docs/generated/decisions_index.md` names `client_rendering.md` as D20's design (§6: "owning design"). D20 is world_model's ruling.
2. `owner_section: cites §1` was world_model's cell. Read from a record under `client_rendering/`, it now points at client_rendering §1.
3. `Record.log` is derived from the directory, so `status()` treats client_rendering as D20's home.

After R3, a decision file "never changes and is never deleted" (§4), and `lint_records::changes` refuses a rename. So R3 freezes this placement for good. Today, D20 is the only id where the two rules disagree; O3 to O7a, O31, T1 and T2 agree.

The design doesn't say which directory a cross-listed record lives in. The code chose one that contradicts §6's "owning design". This needs settling (folded, or taken to the owner) before R3 runs.

Proposed fix (unverified): put the file in `primary(group).log` and make `also_in` the other logs.

### A2 SHOULD-FIX: "one owner per fact" is held for `gate` only, not `closes_at`, and the backlog status prose has two parsers

`scripts/lint_records.py::prose_agrees` and `scripts/records_migrate.py::gaps` / `::_status`.

§4 says: "A gap's `gate` and `closes_at`, and a backlog row's `status` … `check_records` refuses a field that disagrees with it [the prose]." `prose_agrees` checks `gate` and backlog `status`. It never checks `closes_at`, which comes only from the hand file (`hand.closes_at.get(slug, UNKNOWN)`). That is the author's deviation (5).

Failure scenario: R3's hand file gives gap X `closes_at: phase2/step-3` while X's prose names step 5a. Nothing refuses the mismatch. R3's presentation commit then deletes the prose (§4, §8 stage 2), and the hand value becomes the sole owner with no proof behind it.

`kind` isn't in the prose, so taking it from the hand file is in line with RL6. `closes_at` is in the prose.

Separately, the rule for reading a backlog row's prose status is written twice:
- `_status` uses `_DONE.match`, anchored at the start of a cell, and treats only a leading `open` as open; anything else is `unknown`.
- `prose_agrees` searches for `**done**` anywhere in body plus `lands_with`, and calls everything else `open`.

Today's fixture agrees: the probe found 0 `prose_agrees` findings on the migrated records. But a row whose `**done**` sits mid-cell would migrate as `unknown`/`open` while the lint reads `done`. Once the migration has landed, a new record can't hold `unknown`, so the session would then be told its record disagrees with its own prose.

Proposed fix (unverified): one function owns "what the prose says" for each fact, and both the converter and the check call it.

### A3 SHOULD-FIX: `lint_records::generated` and `records_cli::index` disagree on what a hand edit is, and the lint names the wrong remedy

`scripts/lint_records.py::generated` vs `scripts/records_cli.py::stray_entries`.

- `index` allows an entry that HEAD's records generate, so a record deleted since HEAD isn't treated as a hand edit.
- The lint has no such allowance. Any entry the regeneration lacks is called a hand edit, and the message names `migrate-branch`.

Verified with the probe:
1. Migrate the fixture.
2. Delete one gap record, which §4 allows.
3. Don't run `index`.

The lint reports: "docs/known_gaps.md … holds '- NPC inference …', which no record holds: a branch edited it by hand; run `scripts/records.py migrate-branch <branch>`".

That advice is wrong. The branch never edited the old file, so `migrate-branch` maps nothing, and the remedy is `index`. These are two owners of one rule (§6's "an entry that no record holds"), and they have already diverged.

Proposed fix (unverified): one function owns stray detection, and both call it.

### A4 SHOULD-FIX: `migrate-branch` rewrites every `origin/main` record into the branch's worktree and regenerates without the branch's own records

`scripts/records_branch.py::migrate_branch`.

`records` is `main`'s records with the mapped changes. The write is `{**headers, **{r.path: record_text(r) for r in records}, …, **out}`, and `out` is `generate(records, …)`.

Scenario (read from the code, not run):
1. A late branch merges `main` cleanly.
2. It amends lesson 12 the new way (a record edit with an `amended` entry), and also edits an old file.
3. `migrate-branch` overwrites `docs/lessons/12-….md` with `origin/main`'s text. The branch's amendment is gone, and nothing reports it.
4. The branch's own new records are left on disk but missing from the regenerated files. The next `index` repairs that part; it doesn't recover step 3.

Before a merge, rewriting every main record through `record_text` also adds or alters many record files on the branch. Any main record whose bytes differ from `record_text`'s output (say, a hand-written `date: "…"` against safe_dump's `'…'`) then turns the later merge into an add/add conflict per file.

§6 says "regeneration never discards text", and §8 says the command leaves the worktree "with the records". It should write the changes, not overwrite records that already exist.

### A5 SHOULD-FIX (a design finding for the owner): the hand file is an interface between steps that the design doesn't name, and its only copy is a test fixture

Files: `scripts/records_migrate.py::HAND` / `::read_hand`, `scripts/records_decisions_build.py::Hand`, `tests/fixtures/records/hand.yaml`. This is the author's deviation (4).

`migrate-branch` re-parses both sides of a late branch's old logs through `build()`. `build()` raises a `MigrationError` for every row without a bold lead that has no hand title. So after R3, every late-branch session (R4, regions-design, slice2-design) needs the migration's hand file, with exactly the keys for every lead-less row and every restated-name alias.

By CLAUDE.md's test ("if another module depends on a value, it is contract"), that file is contract. But:
- §4 and §8 mention only titles "given by hand in the migration commit, listed there";
- its committed home after R3 is undecided;
- the only copy lives under `tests/`, is keyed to the fixture logs, and holds no kinds or steps.

The format is also split across two modules: `Hand` sits in `records_decisions_build`, while `HAND` and `read_hand` sit in `records_migrate`.

Asking for the owner's ruling on where the R3 hand file lives, recorded where §8 can cite it. I'm not designing that here.

There is a related gap in the same command's "after a clean merge" path (§8). After R3's presentation commit, `main`'s generated files are in §6's forms. `records_migrate`'s parsers read only today's forms, and `TODAYS_FORM` is the only form built. The path that works is "before the branch merges `main`", which is the one the late branches need. The "after a merge" path is proven only against today's forms. Trigger: R3's presentation commit.

### A6 NIT: the today's-form machinery isn't marked, so nothing pins its removal to R3

`scripts/records_index.py::TODAYS_FORM` and the `legacy` schema fields in `scripts/records.py`.

`TODAYS_FORM = True` has no `False` branch in the generator; it only switches `prose_agrees` off. The today's-form renderers, the `legacy` fields in all four schemas and the switch itself are all removed at R3 (RL11). Yet only `lint_ids` and `lint_guards` carry `TEMPORARY(phase1/records-build)` markers, and the roadmap's step 4 row names only those files.

Marking these too would let `lint_markers` show the whole R3 removal list. Also note that dropping the `legacy` key from the schemas is a format change, which needs either a version bump or an argument that no record holds `legacy`.

### Judgment: the TEMPORARY dual reading (`lint_ids::check_decisions`, `::check_lessons`, `lint_guards::backlog_numbers`) is legitimate

- The brief's scope stop puts R3 in a later session, and the real tree has no records until then.
- The table path keeps the live checks running.
- The record path turns on automatically when a family holds records.
- Both are marked, and the roadmap row names both files.
- The selector is per family, so a partial tree doesn't switch the wrong lint.
- It hides no symptom. It is §7's change landing ahead of the data, and R3 removes it.

### A7 NIT: `lint_guards::backlog_numbers` reads a different source from every other check

`lint_guards::backlog_numbers` reads records by globbing disk (`root / docs/standards_backlog`). Every other check, `lint_ids` included, reads the tracked `files` mapping. So an untracked stray record counts toward B-id duplicates here and nowhere else.

### A8 NIT: constants that already have an owner are restated

- `records_decisions.TABLE_HEAD` restates `records_index.DECISION_HEAD`.
- The family roots are hard-coded in several places: `records_migrate.DECISION_LOGS`, the `"docs/lessons/"`, `"docs/known_gaps/"` and `"docs/standards_backlog/"` literals, the `_header.md` paths in `migrate()`, `records_decisions_build.ROOT`, and `lint_records.BASE_PATHS`. `records.FAMILIES` and `records_tree.ROOTS` already own them.
- `lint_standards::record_problems` repeats the base-building in `lint_records::main`.
- `records_cli::git_tracked` repeats `lint_repo.tracked_text_files`.
- Moving a family's root would leave stale copies behind.

### A9 NIT: `records_renumber::rewrite_line` re-implements the lesson-citation scope, wider

§5 makes `lint_ids::check_lessons`'s files the owner: `docs/**/*.md` and `tests/*.py` `reason=` strings. `rewrite_line` rewrites any lesson citation in any line of `tests/**.py`, comments and code included. That rewrites outside the spans `lint_ids` resolves, so a rewrite there can't be checked.

### A10 NIT (on RL14's unreviewed line): `qualifier` is free text holding a ruling's standing

`scripts/records.py::DECISION`, field `qualifier` (`_LINE`).

A status is "derived, never stored" (§4), but `qualifier` is a stored standing with no vocabulary. `qualifier: superseded` would read back without complaint and render beside the id. Today's values are `provisional` (D12) and `re-ruled` (PH2-S2), so a closed `Choice` would hold the line.

Also, since a decision never changes, D12 shows "provisional" forever, even after a later ruling `confirms` it. The derived status then reads "confirmed by …" beside an id cell that still says provisional.

### A11 NIT: `records.py`'s `__main__` loads the module twice

`records.py` runs as `__main__`, then `records_cli` imports `records`, which loads it a second time. The comment says it loads once. Nothing breaks today: the CLI uses only the second copy. But a future `isinstance` or identity check across the two copies would fail.

### A12 NIT: the scope and the split need naming in the PR

The files touched match the brief's list, except `tests/test_isolation.py` (the new `ALLOWED_SPAWNS` row for `records_git::_git`). That edit is a necessary consequence of the isolation rule, not a scope breach, but the PR should name it.

On the ten modules (deviation 1): the brief allows "the names the fold chose", and the 500-line tripwire forces a split. The split mostly follows responsibilities (format, generator, git, renumber, CLI, tree IO, log parsing, decision building, migration, branch mapping, lint). Two exceptions:
- the hand format straddles two modules (A5);
- `records_cli::renumber` holds the `--merged` base-path decision, so the CLI decides as well as dispatches.

### A13 NIT: the change check's base is whatever was last fetched, not a fresh fetch

`lint_records::main` and `lint_standards::record_problems`.

The gate never fetches by design (`prepush.sh`, which prints the base it used), so RL12's "freshly fetched" holds only for `renumber` and `migrate-branch`.

Failure scenario: a local `origin/main` last fetched before R3 merged, and a branch that has since merged main. `migrated = bool(base)` is then false, so the unknown and legacy checks for new records are off entirely, and a new record holding `unknown` passes locally. CI's fresh clone catches it, so this is a NIT. The docstring should say which comparisons fetch.

## The author's deviations, judged

1. **Ten modules instead of two:** accepted (A12).
2. **Git objects instead of a detached worktree (§8):** equivalent for reading, and better under the isolation rule because it creates no worktree. Not a defect in itself. The defect is in what the command writes (A4). Record it in the PR as a deviation from §8's wording.
3. **Cross-listed decisions:** A1, SHOULD-FIX, irreversible at R3.
4. **The hand file under `tests/fixtures/`:** fine for R2's fixtures, but the real file is an unnamed contract (A5).
5. **`gate` and `closes_at` sources:** `gate` from the parsed red-gate span is held against the prose. `closes_at` from the hand file alone breaks §4's one-owner proof (A2). `kind` from the hand file alone is consistent with RL6.

## The lines RL14 folded unreviewed

- **§4 `qualifier`:** holds structurally (optional, and R2 builds and renders it). It should be a closed vocabulary (A10).
- **§4's second one-time exception (R3's presentation commit):** consistent with the build. `lint_records::_fields` excludes `legacy`, so removing `legacy` is allowed, and gap and backlog bodies are mutable, so removing the duplicated prose passes. Removing `legacy` is in fact allowed at any time, not only at R3. That is harmless, because only the migration writes `legacy` and no record holds it after R3. "Presentation only" is not checked mechanically for gaps and backlog rows, whose fields may change anyway, so review holds it there, as §8 says.
- **§8's widened `legacy` list (id and status cells):** sound for the round trip. One cost: while a legacy `status` cell exists it is rendered in place of the derived status, so a new ruling wouldn't show on that row. R3's two commits in one PR close that window, so §9's "one PR" is load-bearing and correct.
- **§8's corrected stage 2:** consistent with `_with_legacy` (the second wording is kept per log in `legacy.rows[].ruling`, then dropped at stage 2). It still holds after A1's fix, as long as "dropped by name" names the non-primary log's row.
