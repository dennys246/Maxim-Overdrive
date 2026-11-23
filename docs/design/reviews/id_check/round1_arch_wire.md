# lint_ids, round 1: Architecture and Wire integrity (2026-11-22)

The reader's hand-back, condensed and saved by the author. Statuses are unset until a reviewer sets them after the
fold. The reader ran `lint_standards` (0 findings, 21 enforced, 27 backlog) and `tests/test_lint_ids.py` (30 passed),
and edited nothing.

**Shipped path, traced:** `scripts/prepush.sh:86` runs `lint_standards.py`, which runs `check_ids(files)` over
`git ls-files -co`. CI runs `prepush.sh` on the PR's merge ref, so it sees `main`'s ids and the branch's together.

**Open PRs:** `check_ids` on each open branch (#47, #49, #51, #52, #53, #54) gives 0 findings. Only #49 adds a lesson
(37) and only #51 adds decision rows (D36, D37), so no merge order turns red today. #54 adds Phase 3 ids (OD-I13 and
on), which the lint doesn't read (S1).

**Architecture: clean.** One job, placed with the other `lint_*.py` modules, following the registry pattern, 163
lines with every function well under 40 code lines. It doesn't duplicate `check_plan.ID_SOURCES` (which checks
presence in the plan, not uniqueness), `lint_contracts` (decision tables live in `decisions/`) or `lint_guards`
(B-id uniqueness).

## SHOULD-FIX

- **S1, `scripts/lint_ids.py::_ID_CELL`: Phase 3 ids and hyphenated ids aren't covered, and the docstring doesn't
  say so.** Branches number `| OD-I13 |` rows in parallel exactly as they do decisions: #54 adds OD-I13, and a second
  branch taking it merges green. `PH2-S2, re-ruled` fails `^([A-Z]+)(\d+)` and is skipped. Fix (unverified): read
  `OD-<L><n>` roadmap rows as a family and accept hyphenated ids, or name both exclusions with a backlog row.
- **S2, `lint_standards.py::main`: the wiring has no test.** Deleting the call leaves every test green. Failure: a
  refactor drops the line and duplicates reach `main` with a green gate.
- **S3, the ruleset's `bypass_actors`:** admin, `bypass_mode: always`, so GitHub offers to merge a branch that is
  behind `main`, skipping the rerun the lint depends on. *Author's note:* this was ruleset 27865593 ("main: up to
  date and green"), which the owner had the author delete on 2026-11-22. The remaining `main-protection` (27865484)
  has `bypass_actors: []` and `current_user_can_bypass: "never"`, checked with `gh api` after the deletion. Moot.
- **S4, `check_lessons`: a silent fallback, and formats with no owner.** `if LESSONS not in files: return []` turns
  the lesson checks off with no message when the file is moved or renamed, and
  `test_without_the_lessons_file_there_is_nothing_to_check` cements it: a handler that quietly returns a fallback.
  The four formats writers depend on (the decision-row shape, the `also in` spelling, `### N.` headings, the citation
  grammar) live only in the module docstring, and no CLAUDE.md rule names `lint_ids` as its Guard, so the guard lint
  doesn't hold the wiring. Fix (unverified): report a missing file, and cite `lint_ids` in the "Record lessons" Guard.

## NIT

- **N1, `_CITE` misses real spellings:** `` `lessons_maxim_in_games.md` 30 `` (no §) at
  `docs/design/inference_placement.md:351` and `reviews/sem_stimuli/bio_faithful.md:232`; code comments such as
  `tests/test_ownership.py:234` ("lesson 23"); `spikes/slice/slice_server/npc.py:16`.
- **N2, scope asymmetry:** lesson citations are resolved and decision citations are not. A sound choice given
  Maxim's D53/D65 and the frozen D2395, but the docstring should say so.
- **N3, `check_decisions`' message:** if the renumbering author misses a citation, it still resolves to the other
  branch's record and both lints pass. Worth one docstring line, so green isn't read as "renumber complete".
