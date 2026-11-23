# lint_ids, fold 1 (2026-11-22)

Author's claims; a reviewer sets the statuses. Executor findings are E1–E6, Architecture and Wire findings S1–S4 and
N1–N3. Mutations: 14, one per fix below, each run against `tests/test_lint_ids.py` and `tests/test_lint_standards.py`
with the source restored after; all 14 went red.

| Finding | Change | Mutation that now fails |
|---|---|---|
| E1, S2 | `tests/test_lint_standards.py::test_main_runs_the_id_check`: a duplicate lesson makes `main()` return 1 | `check_ids` call replaced by `pass` |
| E2, N1 (file-name forms) | `_CITE`'s file-name alternative takes `§N`, `N`, `::N` and a `§N, §N` list, the Executor's regex; four spellings added to the parametrized test. The real tree stays clean, with 225 citations (was 221) | the old `§`-only form; the list dropped |
| E3, S1 (decorated, hyphenated) | Read as records rather than refused: backticks and bold are stripped, a `(qualifier)` is accepted, and `PH2-S2` is its own family. The real tree stays clean, with 118 decision ids (PH2-S2 added) | each of the three widenings reverted |
| S1 (Phase 3 items) | `check_roadmap_ids`: an `OD-<letters><n>` first cell in `docs/roadmap.md` is defined once; the 67 on `main` are unique. Wired through `check_ids` | not wired; `> 2`; decoration not stripped |
| S4 (silent fallback) | Without the lessons file, any citation is a finding naming the first one; a tree with no citation (a fixture) has nothing to hold. The cementing test is replaced by both cases. This replaces "gate it in `lint_standards`" with a condition that can't hide a rename in the real tree, which has 225 citations | the missing-file finding returns `[]` |
| S4 (owner) | CLAUDE.md "Record lessons" now cites `scripts/lint_ids.py::check_lessons`, so `lint_guards` holds the wiring. Enforced rules go from 21 to 22. No CLAUDE.md rule governs decision ids, so `check_decisions` gets no Guard citation | — |
| S3 | Moot: the bypass was on the deleted ruleset 27865593; `main-protection` has none | — |
| E4 | The spelling test asserts `docs/x.md:1:`; a new test pins a citation on line 3 | `line = 1` |
| E5 | A four-digit number after a separator ends the list: `lesson 24, 2026-11-20` cites 24 only | lookahead dropped |
| E6 | Tests for "also in" read from the status cell only, and for three cross-listed definitions | `status = line`; `len(defs) != 2` dropped |
| N2, N3 | Docstring: citations of decisions and items aren't resolved, and why; a green check doesn't mean the renumber is complete | — |

Not folded: N1's code comments and spike files stay out of scope; citations are read in `docs/**/*.md` and test
`reason=` strings only, as the docstring says.

Checks run: ruff check and format, mypy strict on the four touched files, `lint_standards` (PASS, 0 findings; this
includes the size limits), and `tests/test_lint_ids.py`, `tests/test_lint_standards.py` and
`tests/test_tooling_config.py` (250 passed). No full gate on the laptop; that runs on the mini.
