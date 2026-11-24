# Records layout: one file per record, generated indexes (design, 2026-11-22)

**Scope.** The layout of the repository's shared records: lessons, decisions, Known gaps and standards backlog rows.
Today each family is one file that every branch appends to, so parallel sessions collide. This design gives each
record its own file, generates every index from the records, and makes a collision cheap to find and fix. It is
contract only (CLAUDE.md, "A design document holds the contract"). Its mechanisms are build steps (§9).

**Status: round 1 folded at step 1a (2026-11-24).** The owner's rulings are RL1–RL10
(`docs/design/decisions/records_layout.md`); the fold's record is `docs/design/reviews/records_layout/fold.md`.
Step 4 builds it.

## 1. The problem, measured

On 2026-11-22 alone, parallel branches lost time to collisions in shared records four ways:
- **Lessons.** Two branches each added lessons 32 and 33. At the merge one branch's pair became 35 and 36, and every
  citation in its files was renumbered by hand.
- **Decisions.** Two branches appended rows after the same row of `docs/design/decisions/world_model.md`, one D31–D35
  and the other D36–D37, giving a merge conflict resolved by hand.
- **The decision index.** `docs/plans/foundations_plan.md` lists every decision id, sits at its 2,500-word budget,
  and `scripts/check_plan.py` requires every id there. Its §4 table is about 1,083 of those words. About five times in
  one day a branch cut someone else's wording to fit its own ids.
- **Known gaps** are one bullet list in one file, the same pattern on a smaller scale.

Since then, `scripts/lint_ids.py` (#55) detects a duplicated decision, lesson or `OD-` id on the first gate that
sees both, and steps take reserved id blocks (O79, O81). That catches a duplicate, but not before both PRs merge:
`main` is unprotected and a PR's checks don't rerun when `main` moves (round 1, C1).

**What this design fixes, and what it doesn't** (RL9). Records stop sharing a file, so editing two records never
conflicts. Additions to one family still conflict, in that family's generated index, and that is deliberate: the
conflict is the detector that stops a duplicate before the second merge (§5). Resolving one is a command, not a hand
edit.

## 2. Families in scope

Four families move (RL3). Counts are at `1ed9caa`, recounted at R1.

| Family | Ids today | Where today |
|---|---|---|
| Lessons | `### 1.` to `### 40.` | `docs/lessons_maxim_in_games.md` |
| Decisions | 174 rows with a single id (164 ids, the rest cross-listed) in ten logs, plus restating and id-less rows | `docs/design/decisions/<design>.md` |
| Known gaps | none: 13 bold bullets | `docs/known_gaps.md` (#52) |
| Standards backlog | `B1` to `B48` | `docs/standards_backlog.md` |

Out of scope:
- **Phase 3 rows** (`OD-…` in `docs/roadmap.md`). `lint_ids::check_roadmap_ids` holds each unique, and the roadmap
  is the upstream lane's (O77). They may join later under this contract.
- **Review records** are already one file per report.

## 3. Layout

Each record is one Markdown file, in a directory per family:
- lessons: `docs/lessons/<n>-<slug>.md`;
- decisions: `docs/design/decisions/<design>/<id>-<slug>.md`, where `<design>` is the design whose log holds it today,
  or, for a cross-listed decision, the design its owner section names first;
- Known gaps: `docs/known_gaps/<slug>.md`;
- backlog rows: `docs/standards_backlog/<id>-<slug>.md`.

A slug is lowercase ASCII words joined by hyphens, at most 60 characters. A file's id and slug must equal its front
matter. Each family directory also holds `_header.md`, the hand-written text that heads its generated file (§6).
Record directories are added to `scripts/lint_contracts.py`'s out-of-scope paths; the header files are not.

## 4. The record format

**One reader** owns the format: `scripts/records.py::read_record`. A record file begins with a line that is exactly
`---`, and its front matter ends at the next such line; everything after it is the body, which may contain `---`
lines. The front matter is parsed by `simcore.adapters.loaders`' strict YAML reader (duplicate keys refused), and held
to its family's schema with `simcore.core.schema` (unknown keys refused, unknown versions refused). Each family has
its own schema and its own `version`, 1 at R1. The reader is a file gate, with a row in the gate registry
(`scripts/lint_gates.py`).

Common keys:
- **`version`**, per family.
- **`id`**: the family's id (§5). A Known gap's id is its slug.
- **`title`**: one line, the record's line in its index.
- **`date`**: the ISO date the record was made.

**Lessons:**
- `section`: one of a closed list, held by the generator: the lessons file's section headings today, plus "Game and
  general engineering" for lessons beyond Maxim (RL7).
- `amended`: a list of `{date, why}`, empty at creation (RL10).

The body holds the lesson's text, with its *Evidence* and *Consequence*. The body may change. Each change appends one
`amended` entry with a one-line why, and the generated file shows the trail under the lesson. A correction like
lesson 29's stays visible where the lesson is read.

**Decisions:**
- `who` and `owner_section`, as the log's columns today.
- `supersedes`, `amends`: lists of decision ids, or of external rulings, each given as a repository path and an anchor
  (`docs/design/reviews/docs_contracts/rulings.md#41`) that must exist.
- `also_in`: the other logs that list it (a cross-listed decision, today's "also in").
- `restates`: for a row that restates other rows (today's `D26–D28`, `RT1–4`), the ids it restates.

The body is the ruling's text. The title is the ruling's bold lead sentence; a row without one is given a title by
hand in the migration commit, listed there. A decision's status (live, superseded, amended, restates) is **derived**
from these fields across every record, never stored. So a new ruling changes an old one's status without editing it.

**Known gaps:**
- `kind`: `physics`, `performance` or `trust boundary` (RL6).
- `gate`: the strict red gate's test id, or `none` and a reason.
- `closes_at`: the named step that fixes it, or `unscheduled` and a reason.

The body holds its numbers, and the whole body is mutable. A gap whose fix lands is removed: its record is deleted in
the commit that flips its gate (#52's rule). A partly closed gap keeps one record, for its open part.

**Backlog rows:**
- `rule`: the CLAUDE.md rule it holds.
- `lands_with`: as the table's column.
- `status`: `open`, `done in part` or `done`, and `done_in`, the commit, when not open.

The body is the check's text.

**What may change.** Compared with the merge base of the branch and `main`:
- a decision file never changes and is never deleted;
- a lesson may change only its body, its `title` and its `amended` list, which only grows; it is never deleted;
- a Known gap may change anything but its slug, and may be deleted;
- a backlog row may change its body, `lands_with`, `status` and `done_in`; it is never deleted;
- the one exception for every family is §5's duplicate fix.

## 5. Ids: kept short, collisions detected and fixed

**Every existing id is kept,** and new records continue each family's numbering (RL1). "lesson 36", "D34", "O57" and
"TP1" keep resolving, and so do frozen files that cite ids.

**A family** is what CLAUDE.md's "A record id names one record" and `lint_ids` define: for decisions, an id prefix
across every log (`D` is one family over `sem_stimuli` and `world_model`); lesson numbers; `B` numbers; `OD-` ids. So:
- a cross-listed decision is one record, with `also_in`;
- a restating row (a range or list of ids) is a record whose id is the log-qualified slug (`world_model/d26-to-d28`)
  and which carries `restates`;
- a row with no id (`ruled 1`, `the split`) is a record whose id is its log-qualified slug. Nothing cites it by number.

**Allocation.** A step takes the ids its brief reserves (O79, O81). Otherwise it takes the next free number in its
own tree.

**Detection, before the second merge** (RL9, RL8). Each id-bearing family has one generated, committed index in id
order, one line per record: id, slug, title (§6). Two branches adding to one family both insert lines after the same
last record, so git reports a conflict and GitHub refuses the second PR's merge. Its session merges `main` locally,
runs `scripts/records.py index`, and the duplicate check fails if the ids collide. Two branches adding one id with one
slug would write the same file name, an add/add conflict. GitHub's "require up to date" rule stays off (RL8).

**The duplicate check** is `lint_ids`, retargeted at the record files: two records with one id in a family fail,
naming both. It runs in the gate and in CI.

**Resolution.** CLAUDE.md names who renumbers: the branch merged second, its own records and citations. It runs
`scripts/records.py renumber <old>=<new> …`, which applies one mapping at once, so shifting a range can't collide
with itself. It renames the branch's record files and rewrites their front matter. It rewrites citations **only in
lines the branch added or changed against its merge base with `main`**, and lists, without rewriting, every citation
of an old id in lines that came from `main`, because those name the other branch's record. It refuses:
- a file listed in any `freeze.sha256`;
- an old id cited anywhere under `docs/maxim_upstream/`. A lesson is cited upstream only after it is on `main`.

A citation the branch made somewhere it didn't edit (a stacked branch, say) still resolves silently to the other
record. Short citations accept that residual risk (RL1), and the listing above narrows it.

**A duplicate on `main`** (both merged anyway). The fix branch renames the record that reached `main` second (by
`git log`), with `renumber`. That rename of an existing record is allowed only while `main` holds two records with
the old id and the branch leaves one.

**Citation forms.** Lesson citations are resolved, in the spellings and files `lint_ids::check_lessons` reads today
(`docs/**/*.md` and `tests/*.py` `reason=` strings; frozen files skipped). Decision citations are not resolved,
because Maxim's decision ids and frozen pre-registrations share their shapes. Backlog citations in CLAUDE.md's
`Guard:` lines stay `lint_guards`'. A Known gap is cited by `docs/known_gaps.md` and its slug. At R3, red-gate
`reason=` strings name their gap's slug, and a test checks each names a real gap.

## 6. Generated indexes

`scripts/records.py index` writes every generated file from the records and the family's `_header.md`. Each begins
with one marker line saying it is generated and naming the command, and is committed. Generation is deterministic:
fixed order, no dates, SHAs, clock or locale beyond the records' own fields. The check (§7) regenerates and compares
bytes, as `tests/test_fields.py` does for `docs/generated/fields.md`. A conflict in a generated file is resolved by
regenerating it, never by hand.

| Generated file | From | Keeps |
|---|---|---|
| `docs/lessons_maxim_in_games.md` | `docs/lessons/` | its path; the header; first, the id-ordered index of every lesson; then the full text by section, in id order within a section, under `### N.` headings with the date generated from `date`, and each `amended` trail (RL2) |
| `docs/design/decisions/<design>.md` | `docs/design/decisions/<design>/` and cross-listed records | its path and table form, with the derived status column |
| `docs/known_gaps.md` | `docs/known_gaps/` | its path and header; gaps grouped by `kind`, each with its slug shown |
| `docs/standards_backlog.md` | `docs/standards_backlog/` | its path, header and table, in id order |
| `docs/generated/decisions_index.md` | every decision record | one line per id, in id order: id, slug, title, owning design, derived status |

The id-ordered indexes (the lessons file's head, the decisions index, the backlog table) are the detector of §5.

**The foundations plan** keeps its prose and open questions. Its §4 table is replaced by one sentence linking
`docs/generated/decisions_index.md`.

**Budgets.** O22's budgets apply to hand-written text, including each `_header.md`. A generated file has no budget of
its own. Each record has one: its family's longest record at R1 rounded up to the next 100 words, then only tightened
(RL4). At the fold that is 500 words for a lesson, 400 for a decision, 400 for a Known gap and 600 for a backlog row.

## 7. Checks and the changes to existing tooling

**One owner per check:**
- **`scripts/lint_ids.py`** keeps id uniqueness and lesson-citation resolution, read from the record files instead of
  the tables and headings.
- **`scripts/lint_guards.py`** keeps backlog-id duplicates and `Guard:` references, read from the records.
- **A new lint, `scripts/lint_records.py::check_records`,** registered in `lint_standards.py`, refuses:
  - a record that `read_record` refuses, or whose file name disagrees with its `id` and slug;
  - a change §4 doesn't allow, compared with the merge base, as `lint_sizes.py`'s ratchet compares;
  - a generated file that differs from its regeneration, naming the record or `_header.md` to edit, or `migrate-branch`
    when the generated file was edited by hand (§8);
  - a `supersedes`, `amends` or `restates` naming an unknown id or a missing external anchor, and cycles among them;
  - a record over its family's budget.

**`scripts/check_plan.py`** keeps its open-question checks, its budget, and the half of `missing_ids` that requires
every `OD-` id in the plan. The decision half is retired: the generated index holds every decision id by
construction.

**`scripts/lint_contracts.py`:** its scope stays the hand-written designs, plans, roadmap and architecture, plus the
`_header.md` files. The record directories are out of scope. `docs/known_gaps.md` stays in scope as #52 made it; a
finding there names the record to edit, and the generated sections keep stable headings so findings stay stable.

**CLAUDE.md** changes only by the wording of §8.

## 8. Migration

**The converter, `scripts/records.py migrate`,** parses today's four formats into records. A field the source lacks is
`unknown`, never invented, and is listed in the migration commit. It is proven by a round trip: regenerating from the
records reproduces each original file byte for byte, apart from the marker line, the lessons index and the derived
status column. Every derived status must equal the original cell's meaning; a difference is fixed in the converter or
listed in the commit as a named change, and none loses information (A-B4).

**`scripts/records.py migrate-branch <branch>`** is for a branch that edited the old files after the migration
landed. It runs from a checkout of `main`, before that branch merges `main`. It reads the branch's diff to the four
old files against its merge base, and:
- writes each added row, lesson or gap as a new record;
- maps each edit of an existing entry onto a change §4 allows (a lesson body with an `amended` entry, a backlog status,
  a gap's body), or refuses it by name;
- commits the result on the branch, which then merges `main` and regenerates.

**When.** O79 runs step 4 alone, and O81 keeps the slice branch free of record edits until step 4 merges, so at the
migration no open branch should need `migrate-branch`. Steps 2 and 3 merge before step 4 starts. A branch that is
open anyway runs `migrate-branch` at its next merge of `main`. R3 reruns `migrate` from scratch if `main` moves
before it merges.

**The CLAUDE.md wording** (RL5), applied by step 4 and nothing else:
- in "Rules that matter here": "Record known gaps (physics, performance or trust boundary) in `docs/known_gaps/`, one
  file per gap and its one owner, with numbers, instead of hiding them; `docs/known_gaps.md` is generated from them."
- in the guard paragraph: "… or a row in `docs/standards_backlog/` (one file per row; `docs/standards_backlog.md` is
  generated) …"
- in "Record lessons as they're learned": "… add or update an entry in `docs/lessons/`, one file per lesson
  (`docs/lessons_maxim_in_games.md` is generated from them) …"
- under "Documents have a word budget": "Generated files have no budget of their own; each record family has a
  per-record budget (`docs/design/records_layout.md` §6)."

## 9. Build steps

- **R1, the format and the checks,** on fixtures: `read_record`, `records.py index` and `renumber`, `lint_records`,
  and `lint_ids` and `lint_guards` reading records. Tests:
  - every refusal in §4 and §7, each proven by deleting its check;
  - two fixture branches adding records to one family conflict in the generated index, adding one id with two slugs
    included, and after regeneration the duplicate check fails (A-B1, C1, W1);
  - on a file both branches share, `renumber` rewrites the branch's own added citation and lists, without rewriting,
    `main`'s citation of the same id (C3, W2, A-S1);
  - `renumber` refuses a frozen file and an id cited under `docs/maxim_upstream/` (S4, A-S10), and a mapping that shifts
    a range applies at once (W-N4);
  - the duplicate-on-`main` rename is allowed only in its case (C2);
  - a body containing `---` reads back whole, and each family refuses an unknown version (W11);
  - lesson citations in every spelling `lint_ids` reads resolve against fixture records (W3, A-S2);
  - a regeneration twice in different locales and time zones is byte-identical (C-N1).

  Measure each family's longest record and fix the budgets (RL4).
- **R2, the converter.** `migrate` and `migrate-branch`, with the round trip over a copy of today's four files
  committed as fixtures. Tests:
  - every non-`live` status cell at R2 derives back to its meaning, external rulings included (A-B4, W5);
  - cross-listed, restating and id-less rows each come out as one record (A-B3, W4, S1);
  - the backlog's prose `**done**`, its three-cell rows and the gaps without a gate or step come out as listed
    `unknown` fields, never invented ones (W6);
  - a fixture branch's added row becomes one record, its edit of an existing lesson becomes an `amended` entry, and
    an edit §4 refuses is refused by name (S2, W9);
  - `migrate-branch` from a `main` checkout, before the branch merges `main` (S3, W9).
- **R3, the migration commit.** Run `migrate` on `main`. Commit the records, the generated files, the tooling changes
  (§7), the CLAUDE.md wording (§8), the red-gate `reason=` rewrite to gap slugs (A-S7), and the two O73 channels as
  `trust boundary` gaps, with `checklists.md`'s step 7 pointing at them (RL6).
- **R4, a late branch,** if any is open, runs `migrate-branch` (§8).

Each step gets a review round with the Executor, Architecture and Wire integrity lenses, plus Concurrency and lanes,
because these are formats other tooling reads and ids that concurrent branches allocate.

## 10. Owner questions

Ruled at step 1a, 2026-11-24, as RL1–RL5 (`docs/design/decisions/records_layout.md`). The two added questions and three
contract choices from round 1 are RL6–RL10. None is open.
