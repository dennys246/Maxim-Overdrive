# Records layout: one file per record, generated indexes (design, 2026-11-22)

**Scope.** The layout of the repository's shared, append-only records: lessons, decisions, Known gaps and standards
backlog rows. Today each family is one file that every branch appends to, so parallel sessions collide. This design
gives each record its own file, generates every index from the records, and detects id collisions mechanically. It
is contract only (CLAUDE.md, "A design document holds the contract"). Its mechanisms are build steps (§9).

**Status: design, not yet reviewed.** No record moves until it is reviewed and its owner questions (§10) are ruled.

## 1. The problem, measured

On 2026-11-22 alone, parallel branches lost time to collisions in shared records four ways:
- **Lessons.** Two branches each added lessons 32 and 33 to `docs/lessons_maxim_in_games.md`. At the merge one
  branch's pair became 35 and 36, and every citation in its files was renumbered by hand.
- **Decisions.** Two branches appended rows after the same row of `docs/design/decisions/world_model.md`, one D31–D35
  and the other D36–D37, giving a merge conflict resolved by hand.
- **The decision index.** `docs/plans/foundations_plan.md` lists every decision id, sits at its 2,500-word budget,
  and `scripts/check_plan.py` requires every id there. About five times in one day a branch had to cut someone
  else's wording to fit its own ids, and two branches then collided on the same index line.
- **Known gaps** are one bullet list in one file, the same pattern on a smaller scale.

The cause is shared: several writers append to one list, at the same place, with numbers that only mean something
in one sequence. Each record family in §2 has that shape.

## 2. Families in scope

| Family | Ids today | Where today | Citations |
|---|---|---|---|
| Lessons | `lesson 1`–`lesson 36`, as headings `### N.` | `docs/lessons_maxim_in_games.md` | about 70 files cite "lesson N" |
| Decisions | `O1`…, `OA1`…, `D1`…, `T1`…, `TP1`…, and each design's own family | `docs/design/decisions/<design>.md`, one table per design | every design, plan, roadmap and many tests |
| Known gaps | none (bold bullets) | `docs/known_gaps.md` (PR #52) | red-gate `reason=` strings cite the file |
| Standards backlog | `B1`–`B44` | `docs/standards_backlog.md`, one table | CLAUDE.md's `Guard:` lines, the guard lint |

Out of scope for now:
- **Phase 3 rows** (`OD-…` in `docs/roadmap.md`) collide the same way, but the roadmap is exempt from the budget
  (O41) and edited less often. They may join as a later family under the same contract.
- **Review records** are already one file per report.

## 3. Layout

Each record is one Markdown file, in a directory per family:
- lessons: `docs/lessons/<id>-<slug>.md`;
- decisions: `docs/design/decisions/<design>/<id>-<slug>.md`, where `<design>` is the design whose decision log holds
  it today;
- Known gaps: `docs/known_gaps/<slug>.md`;
- backlog rows: `docs/standards_backlog/<id>-<slug>.md`.

A slug is lowercase ASCII words joined by hyphens, at most 60 characters. The id and slug in a file's name must equal
its front matter (§4). Every record directory sits below a path `scripts/lint_contracts.py` already treats as out
of scope, or is added to its out-of-scope list, so records are never checked as designs.

Two branches adding records now add different files. Git merges them without a conflict, unless two branches choose
the same id, which §5 handles.

## 4. The record format

A record file is YAML front matter, then a Markdown body. Front matter is read by one loader with the repository's
strict YAML gate (`simcore.adapters.loaders`'s strict reader, or the scripts' equivalent: duplicate keys refused,
unknown keys refused, a `version` that the reader knows).

Common keys:
- **`version`:** 1. A reader refuses any other.
- **`id`:** the family's id (§5). Known gaps use their slug as their id.
- **`title`:** one line. It becomes the index's line for the record.
- **`date`:** the ISO date the record was made.

Per family:
- **Lessons:** `section`, one of the lessons file's section headings today ("World and physics", "Perception and the
  body" and so on, a closed list held by the generator). The body holds the lesson's text, with its *Evidence* and
  *Consequence* as today.
- **Decisions:**
  - `who` (for example "owner") and `owner_section` (the design section that states its contract);
  - optional `supersedes` and `amends`, lists of ids.

  The body is the ruling's text. A decision's status (live, superseded, amended) is **derived**, never stored, from
  later records' `supersedes` and `amends`. So no existing decision file is edited when a new ruling changes its
  status. That keeps today's rule that a ruling is never edited and a new ruling is a new record.
- **Known gaps:**
  - `status`: `open` or `closed`;
  - `gate`: the strict red gate's test id, or `none` with a reason;
  - `closes_at`: the named step that fixes it;
  - when closed, `closed_by`: a commit or PR.

  The body holds its numbers. A Known gap is the one family whose files change after creation, and only in `status`,
  `closed_by` and the body's numbers.
- **Backlog rows:** `rule` (the CLAUDE.md rule it holds), `check` (the body) and `lands_with`, plus `status` (`open`,
  `done in part` or `done`, with the commit). Like a gap, a row may change its status.

**Immutability.** Comparing a branch with its base, a record file that exists on the base may change only in its
family's mutable fields. Any other edit to an existing lesson or decision file is refused. A wording fix to a merged
lesson is a new lesson, or an erratum that cites it.

## 5. Ids: kept short, collisions detected and fixed

**Every existing id is kept,** and new records continue each family's numbering. "lesson 36", "D34", "O57" and "TP1"
keep resolving, and so do frozen files that cite ids, such as the spec generator spike's pre-registration, which can
never change.

**Why not ids that can't collide.** An id unique by construction (a date-slug, or a block reserved per branch) would
end the collisions. But it would make citations long, or need a central allocator, and there is none: sessions never
push `main`, and the owner merges on GitHub. So ids stay short and sequential, and collisions are made cheap to find
and fix:
- **Allocation.** A branch takes the next free number in the family, as seen in its own tree.
- **Detection.** `check_records` (§7) fails on two record files with one id in a family, naming both files. It runs in
  the gate and in CI on the pull request's merge ref, so a duplicate is caught before the owner merges, whichever
  branch lands first.
- **Resolution.** The later branch runs `scripts/records.py renumber <old> <new>`, which renames its record file,
  rewrites the id in its front matter, and rewrites the citations **in the files that branch changed**, never in
  others, because elsewhere the old id belongs to the other branch's record. This is the renumbering done by hand on
  2026-11-22, made one command and checked.

`check_records` also fails on a citation to an id that has no record, which catches a renumber that missed a
citation.

**Citation forms**, which the checker recognises:
- `lesson N`;
- a decision id by its family pattern (the patterns `check_plan.py` and `lint_contracts.py` already use, extended with
  each design's family);
- `B<N>`;
- a Known gap by `docs/known_gaps.md` plus its slug, for example `` `place-loses-geometry` ``.

Red-gate `reason=` strings name the gap's slug, so the test that a reason cites a real gap can be mechanical.

## 6. Generated indexes

`scripts/records.py index` writes each family's index from its records. Each generated file begins with one marker
line saying it is generated and naming the command, and is committed. The check (§7) regenerates it and compares
bytes, as `tests/test_fields.py` does for `docs/generated/fields.md`.

| Generated file | From | Keeps |
|---|---|---|
| `docs/lessons_maxim_in_games.md` | `docs/lessons/` | its path, its sections, the full text of every lesson in id order, and `### N.` headings, so existing links and citations still land |
| `docs/design/decisions/<design>.md` | `docs/design/decisions/<design>/` | its path and its table form, with the derived status column |
| `docs/known_gaps.md` | `docs/known_gaps/` | its path; open gaps first, closed gaps after with their closing commit |
| `docs/standards_backlog.md` | `docs/standards_backlog/` | its path, its table, and its header text, which moves into the generator's template |
| `docs/generated/decisions_index.md` | every decision record | one line per id: id, title, owning design, derived status |

**The foundations plan** keeps its prose and its open questions. Its §4 decision table is replaced by one sentence
that links `docs/generated/decisions_index.md`. That removes the table from the plan's budget. Today the table is
about a quarter of its words, and is the text branches have been cutting.

**Budgets.** O22's word budgets apply to hand-written text, so the rule is restated here only by reference. A generated
file has no budget of its own, because its size follows its records. Each record has one: a lesson at most 600 words,
a decision 300, a Known gap 400, and a backlog row 200. These are the longest existing records rounded up, measured
at R1 before the caps are fixed. The proposed CLAUDE.md wording is in §8.

## 7. Checks and the changes to existing tooling

**A new lint, `scripts/lint_records.py::check_records`,** is registered in `lint_standards.py` beside the others. It
refuses:
- a record whose front matter fails the strict reader, or whose name disagrees with its `id` and slug;
- two records with one id in a family;
- a citation (§5's forms) in any tracked text file to an id with no record. Frozen files are checked too: they must
  resolve, and they can't change;
- an edit to an existing record outside its family's mutable fields, compared with the base branch, as
  `lint_sizes.py`'s ratchet compares;
- a generated file that differs from its regeneration. The message names the record to edit, or the converter to run
  (§8);
- a `supersedes` or `amends` naming an unknown id, and cycles among them.

**`scripts/check_plan.py`** keeps its open-question checks and its budget on the plan's hand-written text. Its
`missing_ids` check (every id in the design documents appears in the plan) is retired. The generated index holds
every id by construction, and `check_records` holds citations to records.

**`scripts/lint_contracts.py`:**
- its scope stays the hand-written design, plan, roadmap and architecture files;
- the record directories are added to its out-of-scope paths;
- the generated `docs/known_gaps.md` stays in scope (PR #52's test), because it is read as a contract-bearing
  document, while its generator, not its records, is what the lint checks;
- the no-decision-table rule in designs is unchanged.

**`scripts/lint_guards.py`**, which holds every CLAUDE.md rule to a check or a backlog row, reads backlog ids from the
records instead of the table.

**The conventions in CLAUDE.md** change where they name a file:
- "Record lessons as they're learned" names `docs/lessons/`, one file per lesson;
- "Record known physics gaps" names `docs/known_gaps/`, one file per gap;
- the backlog rule names `docs/standards_backlog/`.

## 8. Migration, tolerant of branches in flight

**The converter, `scripts/records.py migrate`,** parses today's four formats into records:
- the decision tables, whose columns differ by file: a missing field is recorded as `unknown`, never invented;
- the lessons headings and their bodies;
- the Known-gap bullets;
- the backlog rows.

It is proven by a round trip. Regenerating from the records must reproduce each original file byte for byte, apart
from the marker line and status columns now derived. Any difference is either fixed in the converter or listed in the
migration commit as a named, reviewed change.

**`scripts/records.py migrate-branch`** is for a branch that edited the old files after the migration landed. It reads
the branch's diff to the four old files against its merge base, writes each added row, lesson or gap as a record,
reverts the hand edits, and regenerates. When a late branch merges `main`, its edits to the now-generated files
conflict or fail `check_records`. The lint's message names this command, so the step can't be missed.

**Order.** The migration lands when the fewest branches carry record edits:
1. **Merge first:** PR #51 (decisions D36–D37 and index rows) and PR #52 (the Known-gaps move). They edit the most
   records, and #52 creates the Known-gaps file this design splits.
2. **Then land this branch's migration,** regenerated from that `main`.
3. **Then each remaining branch runs `migrate-branch` at its next merge of `main`:**
   - PR #47 (backlog row B44, foundations rows, roadmap);
   - PR #48 (backlog rows B11 and B37);
   - `phase1/torch-pilot` (its TP decision file, a lesson and backlog edits).
4. **No action:** PR #50, which touches no record. The spec generator spike's frozen files keep their citations.

**The CLAUDE.md edit proposed for the owner.** Replace "Record known physics gaps in `docs/architecture.md` ("Known
gaps")" (or its #52 form) and the lessons and backlog file names with the record directories (§7). Add one sentence
under the budget rule: "Generated files have no budget of their own; each record family has a per-record budget
(`docs/design/records_layout.md` §6)."

## 9. Build steps

- **R1, the format and the checks.** `scripts/records.py` (read, write, index, renumber) and `lint_records.py`, on
  fixtures only. Tests:
  - every refusal in §7, each proven by deleting its check;
  - a renumber that misses a citation goes red;
  - a hand edit to a generated file goes red;
  - a duplicate id across two fixture "branches" goes red.

  Measure the per-record budgets on the real records before fixing them (§6).
- **R2, the converter.** `migrate` and `migrate-branch`, with the round-trip test over a copy of today's four files
  committed as fixtures, and a test that a fixture branch's added row comes out as one record.
- **R3, the migration commit.** Run `migrate` after the §8 order's first step. Commit the records, the generated files
  and the tooling changes (§7), and the CLAUDE.md edit once the owner rules on it.
- **R4, the late branches.** Each runs `migrate-branch` at its merge (§8).

Each step gets a review round with the Executor, Architecture and Wire integrity lenses. These files are formats
other tooling reads.

## 10. Owner questions

1. **Ids: keep short numbers and detect collisions** (recommended), or switch to ids that can't collide (date-slugs),
   which would lengthen every new citation?
2. **The lessons file: generated as full text** (recommended), or an index of titles and links only? Full text keeps
   it one readable document, as CLAUDE.md describes it.
3. **Families: lessons, decisions, Known gaps and backlog now** (recommended), with Phase 3 rows later?
4. **The per-record budgets in §6:** accepted as caps measured at R1?
5. **The CLAUDE.md wording in §8:** accepted?
