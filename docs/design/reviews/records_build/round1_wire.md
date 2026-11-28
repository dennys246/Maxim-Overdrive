# Round 1: Wire integrity

<!-- Kept verbatim, except that the scratchpad path is written <scratchpad> (the public tree holds no home path, B45) and the late branch's lesson is written "lesson number `44`", which lint_ids does not read as a citation of a lesson not on main. -->

Scope: the staged diff on `phase1/records-build` against `a5cf4bd` (R1 and R2), read against `records_layout.md` §4, §6, §8 and §9, RL1–RL14, and the brief. I ran targeted probes and no suite or gate. The probe scripts are in `<scratchpad>/review/` (`probe1.py`, `probe2.py` before another reviewer overwrote it, `wire_probe4.py`, `wire_probe5.py`). Other reviewers write to the same directory.

## What holds (measured)

- **Round trip over the 14 fixture files.** The 14 fixtures under `tests/fixtures/records/today/` are byte-identical to `a5cf4bd`'s files (`cmp`). `migrate` followed by `generate` reproduces all 14, the marker line aside, and adds `docs/generated/decisions_index.md`. That makes 301 records, and every one survives `read_record(record_text(r))` with equal `meta` and `body`. I checked this independently in `probe1.py`.
- **Versions.** `version: 2`, `0`, `"1"`, `1.0` and `true` are each refused with `bad_version`. An unquoted date is refused.
- **The `---` split.** Bodies of `""`, `"\n"`, `"---\n"`, `"x\n---\n"`, `"\r\n"`, a body with no final newline, and bodies holding `\x85`, ` `, BOM or control characters all read back whole.
- **YAML quoting.** A lesson id is written as an int. The external ruling `"41"`, `yes`, `null`, `~`, `1e3`, `0x1F`, `12:30`, `2026-11-24`, `---`, `- x`, `#x`, `&a`, `*a`, unicode and emoji all round-trip. An empty legacy cell (`owner_section: ''`) round-trips too.
- **Status meanings.** Every status cell in the 11 logs parses through `records_decisions.meaning`, which raises on anything it can't read. I printed each original non-`live` cell beside its derived status. Every primary row matches its meaning, with `live;` prefixes added (O6, O11, D23, D26, D29, the restating slug rows).
- **A migrated tree is clean.** It passes `check_records` with no base and with today's base, `lint_ids.check_decisions` and `check_lessons`, relations (the external rulings 41, 45, 49, 50, 59 and 61 exist, and so do the `§0` sections), the budgets, and `prose_agrees`. It also passes a simulated R3 presentation commit that drops every `legacy` field.
- **The two real late branches.** `map_changes` on their actual diffs, against the migrated fixture records: `phase1/regions-design` gives one new D38 record and `phase1/slice2-design` one new lesson number `44`, with no refusal and no `unknown`.
- **On the shipped path.** The gate runs `lint_records` through `lint_standards.record_problems`. `lint_ids` and `lint_guards` read records once records exist.

## Findings

### W1 BLOCKER: `scripts/records_branch.py::migrate_branch` and `scripts/records.py::__main__` (the shipped `migrate-branch` command can't run for the two late branches)

§8 says `migrate-branch` "runs in a detached worktree of a freshly fetched `origin/main` and writes its result into the branch's worktree". The code does something else. `records.py`'s entry point takes `root = Path(__file__).resolve().parents[1]`, so the root is the checkout the script lives in. `migrate_branch` then refuses unless that root's `HEAD` is the branch (`symbolic-ref ... != branch`). Taken together:

- **Run from the late branch's worktree** (`phase1/slice2-design` or `phase1/regions-design`): `scripts/records.py` doesn't exist there until the branch merges `main`, so there is nothing to run.
- **Run from an `origin/main` worktree**, as §8 says: its HEAD is detached, so it is refused with "run it in <branch>'s worktree".
- **Run after merging `main`:**
  - The merge itself conflicts if `main` replaced the old files.
  - Even after a clean merge, `before` is `main`'s generated files. Because R3's two commits land in one PR (§9, RL14), `main` never holds today's form: it goes straight to §6's forms.
  - The converter only parses today's form. One concrete break: decision hand titles are keyed `<log>:<id cell>` (`records_decisions_build.py::row_keys`). Once §6's form renders a slug-id row's id cell as the slug (`d26-to-d28` instead of `D26–D28`), `_title` raises "no bold lead and no hand title" for each of the 43 hand-titled rows.

`tests/test_records_branches.py` passes only because it calls `branch.migrate_branch(work, ...)` with the root injected, on a `main` still in today's form. That is not the shipped path.

`--hand` is also `required=True` in `records_cli.main`. Every message that sends a user there drops it, so argparse exits 2: `lint_records.generated`, `records_cli.index` and the design's `scripts/records.py migrate-branch <branch>` all omit `--hand`. The only hand file in the tree is the test fixture `tests/fixtures/records/hand.yaml`. A real run needs R3's hand file, since `_parsed` rebuilds the whole logs on both sides and so needs every hand title and alias. Nothing names where that file lives.

Failure scenario: after R3 merges, slice2-design's session follows the brief ("runs `migrate-branch` at its next merge of `main`"). It either has no script to run or gets a refusal or a MigrationError. With no working tool, lesson number `44` gets moved by hand.

Proposed fix (unverified): take the branch worktree as an argument or `--into <path>`, run from an `origin/main` checkout as §8 says, and give the hand file a fixed committed path or make its default that path. Add a test that runs the CLI through `records.py` from a separate checkout. Either decide explicitly that the after-merge case works only before R3's presentation commit, or make the parser read §6's forms.

### W2 SHOULD-FIX: `scripts/records_migrate.py::_status` (B36 migrates as `done`, but its prose says done in part)

B36's check cell starts `**done** for enumerations (phase1/docs-contracts): … Still review's: a rule restated in prose …`, and CLAUDE.md still cites "B36 (prose restatements)" as an open review guard. `_DONE` matches the leading `**done**`, so the record holds `status: done, done_in: phase1/docs-contracts`. `lint_records.prose_agrees` agrees, because it also just looks for `**done**`, so nothing catches the mismatch.

From R3's presentation commit the field is the one owner (§4, "One owner per fact"), so the backlog will show B36 as done while a live guard cites it as open. Verified with `probe1.py` (`BK B36 done 'phase1/docs-contracts'`).

Related (NIT): 28 of 48 rows migrate as `status: unknown`. These include rows whose Lands-with cell only names a future step (B2 "Phase 1 step 5a", B12, B43…), which reads as open, and B19 "(1) done; (2), (3) open", which reads as done in part. `changes()` lets a migrated record keep `unknown` forever, so §6's form will render "unknown" for most of the backlog unless R3 resolves them.

### W3 SHOULD-FIX: `scripts/records.py::DECISION` and `owner_section` (cross-listed decisions' owner sections become wrong citations at R3)

A cross-listed decision has one `owner_section`, taken from the primary log. Each log's own cell is relative to that log's design and is kept only in `legacy`:

| Decision | Primary log's cell | Other log's cell |
|---|---|---|
| O5 | boundaries: `cites §9.3` | npcs_and_sem: `§8` |
| O3 | boundaries: `—` | npcs_and_sem: `§1, §6` |
| O4 | boundaries: `—` | npcs_and_sem: `§1–§5` |
| O7a | boundaries: `—` | npcs_and_sem: `§4, §6` |
| T2 | client_rendering: `§3; world §3` | tile_and_client: `§2, §3` |
| T1 | client_rendering: `§1, §2` | tile_and_client: `—` |
| D20 | world_model: `cites §1` | client_rendering: `—` |

O6 and O7 differ in the same way.

§8 stage 2 removes every `legacy` field, and drops by name only "a cross-listed decision's second wording, a restatement". An owner section is not a restatement. So after the presentation commit, `npcs_and_sem.md`'s O5 row reads `cites §9.3`, which a reader resolves against `npcs_and_sem.md` when it means `boundaries.md`. The fact is lost and replaced by a false one. Verified with `probe1.py` (the `OS-LEGACY` lines).

This is a contract gap. §4's format has no per-log field for it, so it needs the owner's ruling rather than a code fold: a per-log owner section, or listing these cells among R3's named drops.

### W4 SHOULD-FIX: `scripts/records_branch.py::migrate_branch` (drops head edits silently and exits 0)

`map_changes` compares entries only. `migrate_branch` then writes `main`'s `_header.md` files over the worktree, so a late branch's committed edit to a file's head (the text before the table or the first section) is thrown away with exit 0. I ran this: the `_migrated_main` fixture plus a committed edit of the backlog head "The head." gave rc 0, and the edit did not survive.

§8 says every edit is either mapped or "refuses it by name". Fix (unverified): diff each head and refuse, or write the branch's head into `_header.md`.

### W5 SHOULD-FIX: `scripts/records_branch.py::migrate_branch` (generation problems decide the exit code but are never printed)

`out, problems = generate(...)` is followed by `write(...)` and `return 1 if problems else 0`, and `problems` is never shown. Example: a late branch adds a row to a decision log `main` doesn't have. The records are written, the "wrote …" lines are printed, and the command exits 1 with no reason. Verified by reading only.

### W6 SHOULD-FIX: `tests/fixtures/records/hand.yaml` aliases, and `records_decisions_build.py::_raw` and `_same_meaning` (a lossy alias, and a meaning check that can't fail on it)

`realtime decisions 1–4` is aliased to `docs/design/realtime_lanes_coop.md`, the whole document. `meaning()` applies the same alias to the original cell and the derived cell, so for restating rows the "every derived status means what its cell meant" proof holds by construction. Only the alias text decides the result.

After R3, `rt1-to-4` reads "restates docs/design/realtime_lanes_coop.md" and the "decisions 1–4" scope is gone. That document has a `## Decisions` section, and `_SECTION_OF` and `_section_exists` would accept `… §Decisions`, though I didn't run that.

Hand aliases, kinds and `closes_at` are also never put in `Migration.listed`. Only hand titles and `unknown` fields are, although the `Hand` docstring says "each listed in its commit". Verified: `Counter(listed)` holds only `unknown` (144) and `hand title` (43).

### W7 NIT: `scripts/records.py::Line` (`record_text` is not `read_record`'s inverse for YAML line breaks)

`Line` refuses only `\n\r\x00`, but YAML also treats `\x85`, ` ` and ` ` as line breaks. Verified: a title `"a\x85b"` is emitted as `'a\x85  b'` and reads back as `'a b'`. A Hypothesis run over decision fields found 30 such differences in 4,000 examples, all involving `\x85`. Fix (unverified): refuse those three characters in `Line`, or dump strings double-quoted.

### W8 NIT: `scripts/lint_ids.py::duplicate_records` (slug-id decisions aren't held to "defined once")

The docstring says "a decision's slug id is unique by its file's path already". That is false: decisions are per log, so `decisions/a/claude-md.md` and `decisions/b/claude-md.md` are two records with one id, and `Relations.of`, which is keyed by id, would merge them. No such pair exists today. By reading.

### W9 NIT: the `legacy` contents go beyond §8's enumerated list

§8 says "and only those", then lists them. The build also writes the backlog's `three_cells` and a non-cross-listed row's `owner_section` (the `inference_placement` `—` row: `''`, with the field holding `unknown`). Both are real presentation facts. Either widen the list or say in the design that it is illustrative.

### W10 NIT: `scripts/lint_records.py::changes` (both one-time exceptions are always open)

`_fields` drops `legacy`, so removing it is allowed in any commit, not only R3's presentation commit. Gap and backlog body edits are always allowed too, so §4's "one-time" exception isn't checked as one-time. It is harmless once `legacy` is gone. Before R3, a commit that removed some `legacy` and regenerated would pass, and it would quietly break the byte-for-byte state that R3's first commit relies on.

A related hole: an existing migrated record may later change a field to `unknown` (a backlog `status`), and nothing refuses it. §4 allows `unknown` only "in a record that exists at the migration commit", meaning at that commit's values.

### W11 NIT: `scripts/records_index.py::_bullet` and `records_migrate.py::_bullets` (today's form can't hold a gap body with a blank line)

`_bullet` renders a blank body line as `"  "`, and `_bullets` raises on a whitespace-only line ("not a bullet or a group"). A gap record written after the migration with a paragraph break produces a `known_gaps.md` that `migrate-branch`'s parse of `main` refuses. A lesson body line starting with `## ` or `### ` has the same problem: the parser reads it as a section or a heading. By reading.

### W12 NIT: record paths are not a citation spelling (`lint_ids.CITATION`, `records_renumber.rewrite_line`)

`renumber 44=45` renames `docs/lessons/44-<slug>.md` to `45-<slug>.md`. A link to the old path is neither rewritten nor checked by `lint_ids` or `lint_records`, so it dangles quietly. Briefs 2, 3 and 5 are to gain record paths at R3 (brief, "Files you may touch").

### W13 NIT: titles and the index table

- A title containing `|` breaks `decisions_index`'s table, because `Line` allows `|`.
- `D12` is titled "D12, provisional" and `PH2-S2` "PH2-S2, re-ruled". The qualifier sits in the title as well as in `qualifier`, so the index reads `| D12 | d12-provisional | D12, provisional |`.
- The hand title "The action result contract, superseded by O6" puts a derived status into an immutable field.

## RL14's lines, against the build

- **§4 `qualifier`**: built as an optional free `Line`. `D12` → `provisional` and `PH2-S2` → `re-ruled` are both migrated. It is rendered as `<id>, <qualifier>`; the `id (qualifier)` spelling the parser accepts falls back to the legacy `id_cell`, and none exists today. Matches, apart from W13.
- **§4's second one-time exception, and R3's two commits in one PR**: the check allows the removal but doesn't limit it to that commit (W10). Holding both commits in one PR is what breaks `migrate-branch`'s after-merge case (W1).
- **§8's widened `legacy` list**: the build holds every listed fact (positions, per-log cells, heading tail, non-ISO date cells, gap group and position, original id and status cells), plus two the list leaves out (W9). Not everything kept in `legacy` is safe to drop at R3: per-log owner sections (W3).
- **§8's corrected stage 2**: decisions, whose bodies never change, and relation fields are held, and lessons can't change their bodies without an `amended` entry, so the "no body text but the prose" clause holds for those families. For gaps and backlog rows the check permits any body change.

## Callers on the shipped path

| Command | Caller | Status |
|---|---|---|
| `lint_records` | The gate, through `lint_standards` | Called |
| `index` | The brief's exit test, `renumber`, and the lint messages | Called |
| `renumber` | Named in the `lint_ids` and `lint_guards` messages | Callable as named |
| `migrate` | R3 | Not in this branch, as planned |
| `migrate-branch` | Named for both late branches | Not runnable as documented (W1) |

On today's tree, which holds no records, `lint_records` checks nothing yet. That is expected before R3.
