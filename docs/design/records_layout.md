# Records layout: one file per record, generated indexes (design, 2026-11-22)

**Scope.** The layout of the repository's shared records: lessons, decisions, Known gaps and standards backlog rows.
Today each family is one file that every branch appends to, so parallel sessions collide. This design gives each
record its own file, generates every index from the records, and makes a collision cheap to find and fix. It is
contract only (CLAUDE.md, "A design document holds the contract"). Its mechanisms are build steps (§9).

**Status: round 1 and its delta folded at step 1a (2026-11-24).** The owner's rulings are RL1–RL13
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
| Decisions | 164 rows with a single id (154 ids, the rest cross-listed) in nine logs, plus restating and id-less rows; this branch adds the tenth log, RL1–RL13 | `docs/design/decisions/<design>.md` |
| Known gaps | none: 18 bullets, 13 with a bold lead | `docs/known_gaps.md` (#52) |
| Standards backlog | `B1` to `B48` | `docs/standards_backlog.md` |

Out of scope:
- **Phase 3 rows** (`OD-…` in `docs/roadmap.md`). `lint_ids::check_roadmap_ids` holds each unique, and the roadmap
  is the upstream lane's (O77). They may join later under this contract.
- **Review records** are already one file per report.

## 3. Layout

Each record is one Markdown file, in a directory per family:
- lessons: `docs/lessons/<n>-<slug>.md`;
- decisions: `docs/design/decisions/<design>/<id>-<slug>.md`, where `<design>` is the log that holds it today, or, for
  a cross-listed decision, the first of its logs by name; a decision whose id is a slug (§5) is `<slug>.md`;
- Known gaps: `docs/known_gaps/<slug>.md`;
- backlog rows: `docs/standards_backlog/<id>-<slug>.md`.

A slug is lowercase ASCII words joined by hyphens, at most 60 characters. A file's id and slug must equal its front
matter's `id` and `slug`. Each family directory also holds `_header.md`, the hand-written text that heads its
generated file (§6). Record directories stay outside `scripts/lint_contracts.py`'s scope; its scope is widened to the
`_header.md` files.

## 4. The record format

**One reader** owns the format: `scripts/records.py::read_record`. A record file begins with a line that is exactly
`---`, and its front matter ends at the next such line; everything after it is the body, which may contain `---`
lines. `read_record` splits the two itself. The front matter text is parsed by the strict YAML grammar that
`simcore.adapters.loaders` owns (`_StrictLoader`: duplicate keys and unbuildable values refused), through a
text-level entry point the loaders gain at R1, since `read_yaml` reads only a whole single-document file. It is held to
its family's schema with `simcore.core.schema` (unknown keys refused, unknown versions refused). Each family has its
own schema and its own `version`, 1 at R1. The reader is a file gate, with a row in the gate registry
(`scripts/lint_gates.py`). A date is a quoted string `"YYYY-MM-DD"`. An unquoted date loads as a date object and is
refused.

Common keys:
- **`version`**, per family.
- **`id`**: the family's id (§5). A Known gap's id is its slug.
- **`slug`**: as in the file name.
- **`title`**: one line, the record's line in its index.
- **`date`**: the date the record was made.
- **`legacy`**: presentation facts no other field holds, kept for the two-stage proof (RL11, §8), and removed at R3.
  Only the migration writes it.

**`unknown`.** The migration writes `unknown` where a source lacks a required value, and lists each one in its
commit. It is legal in every required field except `version`, `id`, `slug` and `title`, but only in a record that
exists at the migration commit. A record added later never holds it.

**Lessons:**
- `section`: one of a closed list, held by the generator: the lessons file's section headings today, plus "Game and
  general engineering" for lessons beyond Maxim (RL7).
- `amended`: a list of `{date, why}`, empty at creation (RL10).

The body holds the lesson's text, with its *Evidence* and *Consequence*. The body may change. Each change appends one
`amended` entry with a one-line why, and the generated file shows the trail under the lesson. A correction like
lesson 29's stays visible where the lesson is read.

**Decisions:**
- `who` and `owner_section`, as the log's columns today.
- `supersedes`, `amends`, `confirms`, `corrects`: lists of decision ids, held by the later ruling.
- `amended_by_external`: rulings outside the decision records that amended this one (today's "amended by
  docs-contracts ruling 41"). Each is a repository path and the ruling's first cell in that file's table
  (`{path: docs/design/reviews/docs_contracts/rulings.md, ruling: "41"}`), which must exist. Only the migration
  writes it. A ruling made after it is a decision record.
- `also_in`: the other logs that list it (a cross-listed decision, today's "also in").
- `restates`: for a row that restates others (today's `D26–D28`, `RT1–4`), what it restates. Each entry is a decision
  id, or a repository path with an optional section (`docs/design/world_model.md §0`, `CLAUDE.md`).

The body is the ruling's text. The title is the ruling's bold lead sentence; a row without one is given a title by
hand in the migration commit, listed there. A decision's status (live, superseded, amended, confirmed, corrected,
restates) is **derived** from these fields across every record, never stored. So a new ruling changes an old one's
status without editing it.

**Known gaps:**
- `kind`: `physics`, `performance` or `trust boundary` (RL6).
- `gate`: the strict red gate's test id, or `none` and a reason.
- `closes_at`: the named step that fixes it, or `unscheduled` and a reason.

The body holds its numbers, and the whole body is mutable. A gap whose fix lands is removed: its record is deleted in
the commit that flips its gate (#52's rule). A partly closed gap keeps one record, for its open part. A gap without a
bold lead is given a title by hand in the migration commit, listed there.

**Backlog rows:**
- `rule`: the CLAUDE.md rule it holds.
- `lands_with`: as the table's column.
- `status`: `open`, `done in part` or `done`; and `done_in`, when not open, a commit, a PR or a named step, as the
  source states it.

The body is the check's text.

**One owner per fact.** A gap's `gate` and `closes_at`, and a backlog row's `status`, are also stated in prose today.
Until R3's presentation commit, the body keeps that prose verbatim for the byte-for-byte proof, and `check_records`
refuses a field that disagrees with it. From that commit, the field is the one owner: the prose is removed and the
generated file renders the field.

**What may change.** Compared with the base (§5, RL12):
- a decision file never changes and is never deleted;
- a lesson may change only its body, `title` and `section`, and every such change adds one `amended` entry; the list
  only grows, and a lesson is never deleted;
- a Known gap may change anything but its slug, and may be deleted;
- a backlog row may change its body, `lands_with`, `status` and `done_in`; it is never deleted;
- the one exception for every family is §5's duplicate fix.

## 5. Ids: kept short, collisions detected and fixed

**Every existing id is kept,** and new records continue each family's numbering (RL1). "lesson 36", "D34", "O57" and
"TP1" keep resolving, and so do frozen files that cite ids.

**A family** is what CLAUDE.md's "A record id names one record" and `lint_ids` define: for decisions, an id prefix
across every log (`D` is one family over `sem_stimuli` and `world_model`); lesson numbers; `OD-` ids, which stay in the
roadmap (RL3). `B` numbers are a family too, but their duplicate check stays `lint_guards`' (§7). So:
- a cross-listed decision is one record, with `also_in`;
- a restating row (a range or list of ids) is a record whose id is a slug, unique in its log's directory (`d26-to-d28`
  in `docs/design/decisions/tile_and_client/`), and which carries `restates`;
- a row with no id (`ruled 1`, `the split`) is a record whose id is a slug, unique in its log's directory. Nothing cites
  either by number.

**Id order**, used by every index: by prefix, then number, then letter suffix (`O7`, `O7a`, `O8`); slug ids follow
their log's numbered ids, by slug.

**Allocation.** A step takes the ids its brief reserves (O79, O81). Otherwise it takes the next free number in its
own tree.

**Detection, before the second merge** (RL9, RL8). Each id-bearing family has one generated, committed index in id
order, one line per record: id, slug, title (§6). Two branches adding to one family both insert lines after the same
last record, so git reports a conflict and GitHub refuses the second PR's merge. Its session merges `main` locally,
runs `scripts/records.py index`, and the duplicate check fails if the ids collide. Two branches adding one id with one
slug would write the same file name, an add/add conflict. GitHub's "require up to date" rule stays off (RL8).

**The duplicate check** is `lint_ids`, retargeted at the record files: two records with one id in a family fail,
naming both. It runs in the gate and in CI.

**The base** of every comparison in this design (`renumber`'s lines, §4's changes, `migrate-branch`'s diff) is the
merge base with a freshly fetched `origin/main`, never local `main`, which may be days behind (RL12). `renumber` and
the change check refuse to run during an uncommitted merge, when the working tree holds `main`'s incoming lines as
if they were the branch's.

**Resolution.** CLAUDE.md names who renumbers: the branch merged second, its own records and citations. It runs
`scripts/records.py renumber <old>=<new> …`, which applies one mapping at once, so shifting a range can't collide
with itself. It renames the branch's record files and rewrites their front matter. It rewrites citations **only in
lines the branch added or changed against the base**, and lists, without rewriting, every citation of an old id in
lines that came from `main`, because those name the other branch's record. A decision or `B` id is rewritten only as
a whole token, and never in `docs/design/reviews/`, whose finding ids share the shapes (`S1`, `T1-S1`). It never
rewrites:
- a file listed in any `freeze.sha256`;
- a file under `docs/maxim_upstream/`. A lesson is cited there only once it is on `main`, so every citation there
  names `main`'s record, never the one being renumbered. `check_records` refuses a citation added under
  `docs/maxim_upstream/` of a lesson that isn't on the base.

A citation the branch made somewhere it didn't edit (a stacked branch, say) still resolves silently to the other
record. Short citations accept that residual risk (RL1), and the listing above narrows it.

**A duplicate on `main`** (both merged anyway). `lint_ids` fails on `main` naming both records and the PR whose merge
brought the second. The owner starts a session to fix it on a fresh branch. It runs `renumber --merged <PR>`, which
renames that PR's record and rewrites citations in the lines that PR's merge commit added against its first parent,
and lists the rest for the author. That rename of an existing record is allowed only while the base holds two records
with the old id and the branch leaves one.

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
regenerating it, never by hand, and regeneration never discards text. If a generated file holds an entry that no
record holds (a late branch's hand edit merged cleanly), `index` refuses, names the entry and names `migrate-branch`
(§8).

The forms below are §6's forms, the ones R3's presentation commit switches to. Until that commit, the generator writes
today's form, from the records and their `legacy` fields (RL11, §8).

| Generated file | From | Keeps |
|---|---|---|
| `docs/lessons_maxim_in_games.md` | `docs/lessons/` | its path; the header; first, the id-ordered index of every lesson; then the full text by section, in id order within a section, under `### N.` headings with the date generated from `date`, and each `amended` trail (RL2) |
| `docs/design/decisions/<design>.md` | `docs/design/decisions/<design>/` and cross-listed records | its path and table form, in id order, with the derived status column |
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
  - a record that `read_record` refuses, or whose file name disagrees with its `id` and `slug`;
  - a change §4 doesn't allow, compared with the base (§5), as `lint_sizes.py`'s ratchet compares, including a
    lesson change without a new `amended` entry;
  - an `unknown` in a record added after the migration commit, a `legacy` field written after it, and a field that
    disagrees with the prose it duplicates (§4);
  - a citation added under `docs/maxim_upstream/` of a lesson not on the base (§5);
  - a generated file that differs from its regeneration, naming the record or `_header.md` to edit, or `migrate-branch`
    when the generated file was edited by hand (§8);
  - a `supersedes`, `amends`, `confirms`, `corrects`, `restates` or `amended_by_external` entry naming an unknown id,
    path, section or external ruling, and cycles among them;
  - a record over its family's budget.

**`scripts/check_plan.py`** keeps its open-question checks, its budget, and the half of `missing_ids` that requires
every `OD-` id in the plan. The decision half is retired: the generated index holds every decision id by
construction.

**`scripts/lint_contracts.py`:** its scope regex stays the hand-written designs, plans, roadmap, architecture and
`docs/known_gaps.md` (as #52 made it), widened to the `_header.md` files. Record directories are subdirectories and
stay outside it. A finding in `docs/known_gaps.md` names the record to edit, and the generated sections keep stable
headings so findings stay stable.

**`simcore.adapters.loaders`** gains the text-level entry point to its strict YAML grammar (§4). It is the one engine
change this design needs.

**CLAUDE.md** changes only by the wording of §8.

## 8. Migration

**The proof has two stages** (RL11).
1. **Nothing is lost.** `scripts/records.py migrate` parses today's four formats into records. Regenerating them in
   today's form reproduces each original file byte for byte, apart from the marker line. Every presentation fact no
   other field holds goes into `legacy`, and only those: a row's position in its log; for a cross-listed decision, each
   log's own row cells where they differ from the record; a lesson heading's tail (lesson 11's "reworded 2026-11-20");
   a date cell's original text when it isn't ISO; a gap's group and bullet form in today's file. A field the source
   lacks is `unknown` (§4). Every derived status must equal the original cell's meaning. A cell the fields can't
   derive is a converter bug, never a listed exception.
2. **The new forms.** A separate commit switches the generator to §6's forms, removes every `legacy` field and the
   duplicated prose (§4), and lists each removal. It is reviewed as presentation only: its diff changes no record's
   `id`, `slug`, `title`, body text or relation fields. A cross-listed decision's second wording, a restatement, is
   dropped there by name, as "One owner per contract" asks.

**`scripts/records.py migrate-branch <branch>`** is for a branch that edited the old files after the migration
landed. It runs in a detached worktree of a freshly fetched `origin/main` and writes its result into the branch's
worktree. It reads the branch's own commits' diff to the four old files against the base (§5). So it works before the
branch merges `main`, and after a merge that went through cleanly. It:
- writes each added row, lesson or gap as a new record;
- maps each edit of an existing entry onto a change §4 allows (a lesson body with an `amended` entry, a backlog status,
  a gap's body), or refuses it by name;
- leaves the branch's worktree with the records and regenerated files, for its session to commit.

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

- **R1, the format and the checks,** on fixtures: the loaders' text-level entry point, `read_record`, `records.py
  index` and `renumber`, `lint_records`, and `lint_ids` and `lint_guards` reading records. Tests:
  - every refusal in §4 and §7, each proven by deleting its check;
  - two fixture branches adding records to one family conflict in the generated index, adding one id with two slugs
    included, and after regeneration the duplicate check fails (A-B1, C1, W1);
  - on a file both branches share, `renumber` rewrites the branch's own added citation and lists, without rewriting,
    `main`'s citation of the same id (C3, W2, A-S1). It does the same with a stale local `main` behind `origin/main`,
    and refuses during an uncommitted merge (RL12; delta Concurrency B1, Executor S6). A hand-resolved line holding both
    branches' citations is listed, not rewritten (delta Concurrency N2);
  - `renumber` never rewrites a frozen file or a file under `docs/maxim_upstream/`, and still renumbers the branch's
    record when `main`'s record of that number is cited upstream (S4, A-S10; delta Architecture N-S1, Concurrency SF3,
    Executor S2); a range mapping applies at once (W-N4); a review finding id shaped like a decision id is never
    rewritten (delta Wire S5);
  - the duplicate-on-`main` rename is allowed only in its case, and `--merged` rewrites the second PR's own citations
    (C2; delta Concurrency SF2, Executor S5);
  - a body containing `---` reads back whole, an unquoted date and an unknown version are refused, and a slug id makes
    a valid file name (W11; delta Wire W11, S3, Architecture N-S2, Executor S3);
  - a lesson body changed without an `amended` entry is refused (delta Executor S1);
  - `index` refuses a generated file holding an entry no record holds (delta Concurrency SF1);
  - lesson citations in every spelling `lint_ids` reads resolve against fixture records (W3, A-S2);
  - a regeneration twice in different locales and time zones is byte-identical (C-N1).

  Measure each family's longest record and fix the budgets (RL4).
- **R2, the converter,** stage 1 of §8. `migrate` and `migrate-branch`, with the byte-for-byte round trip over a copy
  of today's four files committed as fixtures. Tests:
  - every non-`live` status cell derives back to its meaning, the "confirmed by", "corrected by", external and
    section-restating cells included (A-B4, W5);
  - cross-listed, restating and id-less rows each come out as one record, and each cross-listed id's per-log cells
    survive in `legacy` (A-B3, W4, S1; delta Wire B1, S4);
  - the decision logs' row order, lesson 11's heading tail and the non-ISO date cells survive in `legacy` (delta
    Executor X-B1, Wire B1, W-N1);
  - the backlog's prose `**done**`, its three-cell rows, the five gaps without a bold lead and the gaps without a
    gate or step come out as listed `unknown` fields or hand titles, never invented values (W6);
  - a fixture branch's added row becomes one record, its edit of an existing lesson becomes an `amended` entry, and
    an edit §4 refuses is refused by name (S2, W9);
  - `migrate-branch` before the branch merges `main`, and after a clean merge (S3, W9; delta Concurrency SF1).
- **R3, the migration,** stage 2 of §8, in two commits. First: run `migrate` on `origin/main` and commit the records,
  today's-form generated files, the tooling changes (§7) and the CLAUDE.md wording (§8). Then: the presentation commit,
  plus the red-gate `reason=` rewrite to gap slugs (A-S7) and the two O73 channels as `trust boundary` gaps, with
  `checklists.md`'s step 7 pointing at them (RL6).
- **R4, a late branch,** if any is open, runs `migrate-branch` (§8).

Each step gets a review round with the Executor, Architecture and Wire integrity lenses, plus Concurrency and lanes,
because these are formats other tooling reads and ids that concurrent branches allocate.

## 10. Owner questions

Ruled at step 1a, 2026-11-24, as RL1–RL5 (`docs/design/decisions/records_layout.md`). The two added questions, three
contract choices from round 1 and three from the delta round are RL6–RL13. None is open.
