# Docs-contracts delta 2: Executor (with Architecture's eye on the lint)

Scope: commit 858cac2 against b1237ac, `scripts/lint_contracts.py`, `tests/test_lint_contracts.py` and the intro of
`docs/design/contracts.md`, which fold delta 1's NEW-3 to NEW-7 (`delta1_executor_architecture.md`). Read-only. I
planted every probe and mutant in memory, with the module exec'd from mutated source and patched into the test
module. The probe and mutant drivers sit in the session scratchpad and are not committed.

## What I ran

- `pytest tests/test_lint_contracts.py`: 52 passed, `test_the_real_tree_passes` among them, so `check_contracts`
  over `docs/**/*.md` returns `[]`.
- Branch coverage of `scripts/lint_contracts.py`: 99%. Lines 88 (a trailing block with no final newline) and 170
  (a non-docs key in `markers`) are missed. Neither line is in this diff, so every changed line runs.
- `ruff check` and `ruff format --check` are clean on both files, `mypy` (strict) is clean, and
  `scripts/lint_standards.py` passes, size limits included (`marker_problem` is about 15 code lines).
- Twelve mutants against the full test file:

| Mutant | Result | Killed by |
|---|---|---|
| keyword check off | killed | `test_an_exclusion_is_checked_too[but:…]` |
| both-named-and-excluded check off | killed | `…[…budget]` |
| stale-exclusion check off | killed | `…[…ghost]` |
| stale check against all spans, not member positions | **survived** | none |
| `RULING` without `\d+\.` | killed | `test_a_numbered_list_of_rulings_inside_a_design_fails` |
| `header` with no sections returns the whole text | killed | `test_a_design_without_sections_is_exempt_only_by_a_banner_in_its_lead` |
| `header` lead `[:3]` changed to `[:2]` or to `[:4]` | **both survived** | none |
| `member_positions` without `[1:]` (header-row skip) | killed | `test_a_tables_header_row_is_not_a_member_position` |
| `rel != REGISTRY` removed from `in_scope` | killed | `test_the_registry_is_out_of_scope` |
| `keyword` hard-wired to `"not:"` | killed | `…[but:…]` |
| `removeprefix("not:")` removed | killed (28 tests) | most of the file |

NEW-6's two survivors are now killed, and the `removeprefix` mutant, which was equivalent in round 1, is now
observable. The new tests can fail.

## Findings

### D2-1. NIT: `scripts/lint_contracts.py::header`, NEW-4's second case is unfixed, and nobody recorded it

**Failure scenario.** A design adds `> **Superseded in part (§4) by `y.md`.**` above its first section. That
partial banner exempts the whole document, so a restatement of any vocabulary in §1 to §3 passes unseen. This is
the S2/A5 failure the round-1 fold closed for banners placed inside a section.

**Evidence.** I probed two documents, each with that banner in its lead and three `outcomes.reasons` members below.
One had sections and one had none. `check_contracts` returned `[]` for both. `SUPERSEDED` (`^> \*\*Superseded`)
matches "Superseded in part". NEW-4 listed two cases, and the fold fixed only the first (no sections). The second is
missing from `moves_3d_3e.md`'s "Left, with reasons", and that table says only "a design without sections is exempt
only by a banner in its lead paragraphs". Nothing on the tree triggers it today: the one partial banner,
`realtime_lanes_coop.md`:179, sits inside §4.

### D2-2. NIT: `scripts/lint_contracts.py::RULING`, NEW-3 is fixed for one of its five forms, and the rest are unrecorded

**Failure scenario.** A design gains `- **Ruled (owner, 2026-11-20):** …` or a bare `**D20. One truth.**`, and the
lint passes it. The docstring and contracts.md's new intro ("a list of rulings") still read as the general rule.

**Evidence.** These probes inside a design section passed: `- **Ruled (owner, 2026-11-20):** x`,
`**D20. One truth.** x` and `- **OD-A1.** x`. `1. **D20.**` and `10. **O3:**` now fail, which is correct. The false
positive `- **D1** deliverable: the tile` still fails: `[.:*]` matches the closing `**`. `moves_3d_3e.md` records
NEW-3 as "numbered lists of rulings are caught", with no remainder under "Left". It stays a heuristic. The defect is
the unstated gap, not the heuristic itself.

### D2-3. NIT: `tests/test_lint_contracts.py::test_a_design_without_sections_is_exempt_only_by_a_banner_in_its_lead`, the boundary of the lead is unpinned

**Failure scenario.** The lead's size, three paragraphs, is a contract that the docstring states only as "its lead
paragraphs". Changing it to 2 or 4 leaves every test green, so a later edit can widen the exemption silently.

**Evidence.** The `[:3]`→`[:2]` and `[:3]`→`[:4]` mutants both survive. The `late` fixture puts its banner in
paragraph 5, and the `early` fixture puts it in paragraph 2. A banner in paragraph 3 (exempt) and one in paragraph 4
(not exempt) would pin it. The docstring's Scope paragraph also still says "the text before its first section", with
no word about documents that have none.

### D2-4. NIT: `tests/test_lint_contracts.py::test_an_exclusion_is_checked_too`, the stale check's table case is untested

**Failure scenario.** `marker_problem` tests a stale exclusion against `member_positions`, not against every span.
So in a table owner, excluding a span from a later column is called stale, although the block holds it. The
"against all spans" mutant survives, so a refactor could flip between these meanings without a red test. The stricter
reading is defensible, since a later column is not a member position. It is unpinned, though, and the message ("which
its block doesn't hold") is false in that case: the block does hold it.

### D2-5. NIT: `scripts/lint_contracts.py::parse_marker`, a bare trailing bar gives a confusing message

`<!-- contract: x: a b c | -->` gives "its marker reads '|' after '|'". When `rest` is empty, `keyword` falls back to
`bar`. It fails loudly, so this is wording only. Separately, `| not: a | not: x` reports
"excludes ['|', 'not:', 'x']": it is loud too, with odd wording.

### D2-6. NIT: `scripts/lint_contracts.py::restatements` with `registry`, the removed guard and a count of 0

Removing `if kept and` is correct under the module's invariants: a vocabulary has at least 3 members, and a signature
needs 1. But `ROW` accepts `| 0 |`. With a count of 0, `need` is 0, and every block on the tree is reported as
restating, now including the owner's own block, with an empty member list ("restates outcomes.reasons ()"). I probed
this. `registry` doesn't refuse a count below 3, which ruling 1 sets as the floor. This hole predates the diff, and
the diff makes its output slightly worse.

### D2-7. NIT: commit 858cac2's message, the mutation proof isn't stated

CLAUDE.md, "Prove a guard by deleting what it guards", asks the commit message to say that the guards were broken and
went red. The message gives counts and coverage but no mutants. My table above supplies the evidence, and the tests
do fail. The record does not say so.

No BLOCKER and no SHOULD-FIX. The real tree passes, every changed line is covered, and lint, types and sizes are
clean.

## Fold status (reviewer-set, read from the tree at 858cac2)

| Finding | Status | Reason |
|---|---|---|
| NEW-3 | **open**, in part | Numbered lists are caught and tested. The bullet `**Ruled`, the bare `**D20.`, `OD-A1` and the `- **D1**` false positive remain, with no record (D2-2). |
| NEW-4 | **open**, in part | A design with no sections is now limited to its lead, and the mutant is killed. A partial banner in the lead still exempts the whole file, with no record (D2-1). The lead's size is unpinned (D2-3). |
| NEW-5 | **fixed** | Stale, both-named-and-excluded and keyword checks, each killed by its own parametrized case. Residuals are D2-4 and D2-5, both NITs. |
| NEW-6 | **fixed** | The header-row and registry-scope mutants are now killed, the `removeprefix` mutant is observable, and the dead `kept` guard is removed (but see D2-6). |
| NEW-7 | **fixed**, in part | The docstring now says that a list owner is its first item. The error message still points at the marker rather than at the form, which NEW-7 named, and is unchanged. |

Counts: 0 BLOCKER, 0 SHOULD-FIX, 7 NIT.
