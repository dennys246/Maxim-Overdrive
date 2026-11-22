# Docs-contracts, round 1: Executor

Diff: `git diff 5c054f6..HEAD` at `c043920` (phase1/docs-contracts). Lens: Executor (`docs/code_review.md`). Read-only
review; every planted case ran on in-memory dicts or on a copy of the tree in the session scratchpad, never on the
worktree's docs.

## What was checked, and came out clean

- **Tests and linters.** `pytest tests/test_lint_contracts.py tests/test_lint_standards.py tests/test_check_plan.py`:
  232 passed. `ruff check scripts tests`: clean. `ruff format --check` on the four changed Python files: clean. `mypy`
  (strict, from `pyproject.toml`) on `scripts/lint_contracts.py`, `scripts/check_plan.py`,
  `tests/test_lint_contracts.py`: no issues. `scripts/lint_standards.py` (which runs `check_sizes`): PASS, 0 findings.
  `scripts/check_plan.py`: PASS.
- **Coverage of the new lint.** `pytest --cov=scripts --cov-branch` over the three test modules:
  `scripts/lint_contracts.py` 187 statements, 92 branches, 99%; the one miss is `blocks`'s final flush (a text that
  doesn't end in a newline, line 88, plus its partial branch). `check_plan.py` and `lint_standards.py` at 100%. The
  changed lines clear 95%.
- **Prove by deletion: mutation run.** On a copy of the tree, 16 single mutations of `lint_contracts.py` were applied
  one at a time and the two test modules run: the registry excluded from scope, the registry skipped by `structural`,
  the docs-only marker scan, the owner-block exemption, `list_run`, the fence toggle, the signature's space join, the
  section's upper bound, the kind check, the table header skip, the superseded exemption, `min(threshold, n)`, the
  three-member floor, `Ruling` in the decision regex, the list-head `:` split, and the top-level item split in
  `blocks`. **All 16 were killed.** No test I found cannot fail.
- **Every structure the branch removed would go red if restored.** For each of the 12 designs the branch touched, the
  5c054f6 text was swapped in and the lint run: the fold tables (boundaries 2, npcs_and_sem 3, world_model 1) and the
  §0 decision tables (boundaries, npcs_and_sem, tile_and_client, client_rendering, inference_placement) are all
  flagged, and the old restatements show (boundaries 1, npcs_and_sem 3, tile_and_client 4). The exception is the
  decision *lists* (finding S3).
- **check_plan's required ids.** The 5c054f6 `check_plan.py` over the 5c054f6 sources yields 169 ids; the HEAD script
  over HEAD sources yields 168. old − new = {`OD-EA9`}, new − old = ∅, and
  `tests/fixtures/check_plan/required_ids.txt` equals old − {`OD-EA9`} exactly. Emptying each HEAD source in turn,
  `test_the_required_ids_never_shrink` would fail for every source except `decisions/client_rendering.md`, whose ids
  all appear in another source too (no loss, so not a finding).
- **Fold tables are verbatim (step 1).** Line-set comparison of the removed sections against their records:
  boundaries §"Fold table" ×2 vs `reviews/boundaries/fold.md` + `reviews/foundations_v1/fold_boundaries.md`;
  npcs_and_sem ×3 vs the three new files; world_model vs `reviews/world_model/fold.md`. In each direction the only
  differing lines are blank lines and the added "Moved verbatim" comment. `reviews/npcs_v3/foldtable.py`, retargeted
  at `fold.md`, was run on a copy of the tree: it reproduces `fold.md` byte for byte (175 ids).
- **Decision records (step 2).** For every row of the 8 records, the ruling cell (whitespace-normalised) is a
  substring of its 5c054f6 source: 135 rows, 0 misses once world_model's `D20. ` prefixes are moved to the id column.
  The §0 table id sets match one to one (boundaries 20, npcs_and_sem 42, client_rendering 10, inference_placement 11).
- **Word budgets** (`wc -w`, 5c054f6 vs HEAD, and HEAD with marker lines excluded): no design in `docs/design/*.md`
  grows with markers excluded. With markers counted, one does: `client_rendering.md` 3,800 → 3,810 (finding S4).
  `contracts.md` is new, at 369 words.

## Findings

### S1. SHOULD-FIX: `scripts/lint_contracts.py::blocks`, a vocabulary restated as a bulleted list passes, and B36 is marked done for enumerations

**Failure scenario.** A plan writes the `thought_failed` reasons, one per bullet:

```
- `budget`: over budget
- `timeout`: late
- `parse`: unparseable
```

`blocks` splits each top-level list item into its own block, so each block holds one member, which is under every
threshold, and the lint passes. I planted this form for every registered vocabulary in a new `docs/plans/copy.md` on the
real tree. **All 11 vocabularies went green as a list.** The same members as a table, or as the owner block copied
verbatim, went red for all 11. So the lint catches copy-paste but not the form a person most often types when they
restate a closed list. `test_members_in_neighbouring_list_items_are_references` asserts this pass as intended.

**Why it matters.** `docs/standards_backlog.md` B36 now reads "**done** for enumerations" and lists what review
still holds: prose, a partial copy below a row's count, and unregistered contracts. A full list copy is not among
them. CLAUDE.md's guard now cites `check_contracts` for "the registered vocabularies". The claim is false for the
list form, so the rule is kept by luck, not by a check.

**Evidence.** In-memory plant per contract (`resolve` gave each contract's members; I wrote `- \`m\`: x` per member):
`as-list: green` ×11, `as-table: RED` ×11, `verbatim: RED` ×12.

**Proposed fix (verified as far as stated).** Treat a run of top-level list items as one block for restatement, as
`list_run` already does for owners. I disabled the item split in `blocks` on an in-memory copy and ran it on the real
tree: **1 finding**, `docs/plans/checklists.md:222` (step 7's list names `welcome`, `regions`, `tick`,
`intent_result` across neighbouring items), and the 11 list plants turned red. The author has to judge whether that
checklist hit is a real restatement or needs the row's count raised, and has to rewrite the test that asserts the
opposite. Not verified: the effect on the synthetic tests beyond that one.

### S2. SHOULD-FIX: `scripts/lint_contracts.py::in_scope` (`SUPERSEDED`), a partial supersession note exempts a whole live design

**Failure scenario.** `SUPERSEDED` matches `^> \*\*Superseded` anywhere in the file, so a live design that marks only
one section as superseded drops out of scope entirely. The repo already writes notes like this:
`realtime_lanes_coop.md:179` reads `> **Superseded in part (2026-11-16).**`. I appended
`> **Superseded in part: §1.**` and a three-reason copy of `thought_failed` to `tile_and_client.md`: the lint went
**green** for that copy and for every other restatement anywhere in that file.

**Evidence.** Plant H in the scratch run, `GREEN (unseen)`. Without the note, the same copy in a design is red (plants B
and D). `test_a_superseded_design_is_history_and_may_restate` only tests a whole-file banner at the top, so it can't
tell the two cases apart.

**Proposed fix (unverified).** Exempt only a file whose banner is the first blockquote after the title, or exempt the
superseded section's span rather than the file.

### S3. SHOULD-FIX: `scripts/lint_contracts.py::structural`, decision *lists* moved to records can return unseen

**Failure scenario.** `structural` flags a table whose second header cell starts with `Decision` or `Ruling`. Three of
the 8 records came from lists or prose, not tables: world_model §0 (the `**D20. …**` bullets), fire_model §11
("**Ruled (owner, 2026-11-20):**" items 1–3) and sem_stimuli §10 (the "**Ruled 2026-11-20:** **D1** …" paragraphs).
Restoring the 5c054f6 text of each, the lint reports **no** structural finding for world_model's decisions (only its
fold table), and none at all for fire_model or sem_stimuli. A later edit that re-adds rulings to those designs in
their original form passes, so the decision record and the design can drift apart again.

**Evidence.** `revert.py` (each design swapped to 5c054f6 in memory): world_model `structural: 1` (the fold table),
fire_model `structural: 0`, sem_stimuli `structural: 0`.

**Proposed fix (unverified).** Flag a `## N. Decisions` section in a design that holds anything but a pointer to its
record, or flag a ruling-shaped line (`**Ruled`, `**D\d+\.`, `(owner, 20..-..-..)` at a bullet's head) inside a
design.

### S4. SHOULD-FIX: word budget, the marker-line exemption is the author's rule, and `client_rendering.md` grows with it

**Failure scenario.** CLAUDE.md (O22, B24): "an existing design document doesn't grow". `client_rendering.md` was 3,800
words at 5c054f6 and at dc0e1aa (the plan's ceiling); it is 3,810 at HEAD with its marker counted, and exactly 3,800
without it. The exemption ("Marker lines don't count toward a design's word budget") appears only in commit
`c043920`'s message. It is not in `rulings.md`, the plan's budget paragraph or CLAUDE.md. That makes it an
author-set loosening of an owner rule. It is small today, but every new registry row adds about 10 uncounted words
to a design.

**Evidence.** `wc -w` at both revisions, with and without the `^<!-- contract:` lines. All other designs shrink
either way.

**Proposed fix.** Either the owner rules on the exemption and it is recorded, or `client_rendering.md` cuts 10 words.

### N1. NIT: `scripts/lint_contracts.py` module docstring, stale row format and threshold

The docstring gives the row as `| <name> | <path> §<number> | vocabulary or signature |` (three columns) and says a
restatement holds "at least `min(3, n)`" members. `ROW` requires a fifth "restates at" column, and `restatements`
uses `min(c.threshold, n)`. A reader who writes a row from the docstring gets "a row must read …".

### N2. NIT: `scripts/lint_contracts.py::markers`, not fence-aware: a quoted marker anywhere under `docs/` breaks the gate

`markers` scans every `.md` under `docs/`, including `reviews/`, and doesn't skip fenced blocks. A review or plan that
quotes a marker on its own line inside a code fence counts as a second marker, and the lint fails with "needs exactly
one … marker". (Plant J: a fence holding the `ordering.key` marker in `docs/design/reviews/x/r.md` went red.) This
report keeps its marker quotes inline for that reason. `section_span` and `HEADING` are also not fence-aware.

### N3. NIT: `scripts/lint_contracts.py::section_span`, a section number matches as a prefix

`re.match(rf"{number}[. ]", heading)` lets `"2"` match `### 2.6 B` when that heading comes before `## 2. …`:
`section_span("# T\n### 2.6 B\nx\n## 2. A\ny\n", "2")` returns `(1, 3)`, which is §2.6's span. No current row
triggers it.

### N4. NIT: commit `c043920`, the test count

The message says "42 tests in tests/test_lint_contracts.py"; `pytest --collect-only` collects 43.

### N5. NIT: decision records, "Moved verbatim" with small changes of form

The ruling text is verbatim (checked above), but the form changed: npcs_and_sem's `**O6**` id lost its bold,
world_model's `**D20. One simulation truth.**` became id `D20` plus `**One simulation truth.**`, and fire_model's
numbered list became table rows `ruled 1`–`ruled 3`. The header comment explains the added columns but not these
changes, so "verbatim" slightly overstates. Either say "rulings verbatim; ids moved to the Id column" or leave it.

### N6. NIT: `scripts/lint_contracts.py::restatements`, a signature is matched as an exact string

`(apply_tick,kind_rank,apply_us,actor_id,seq)` (no spaces), or the five fields as separate spans, restates
`ordering.key` and passes (plants I2, I3). The registry's "sees code spans" limit partly covers this. Normalising
whitespace inside a signature span would close the first form.

## Counts

BLOCKER 0, SHOULD-FIX 4, NIT 6.
