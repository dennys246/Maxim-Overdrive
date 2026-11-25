# Records layout design, round 1: Wire integrity and Executor (2026-11-22)

The reader's hand-back, condensed and saved by the author. Statuses are unset until a reviewer sets them after the
fold. All probes were read-only greps and awk over the worktree, `origin/main` and the open PR branches, plus `gh api`.
The reader ran one `git fetch`, which updated only remote-tracking refs.

**Counts:**
- 36 lessons, all with regular headings;
- 139 decision rows in 8 files;
- 43 backlog rows;
- 18 gaps on #52;
- lesson citations in 10 spellings, about 205 occurrences in about 85 files.

## Formats

| Format | Writer | Reader | Version | Owner |
|---|---|---|---|---|
| Record front matter (four schemas) | humans, `records.py` | `lint_records`, `records.py index`; the reader is unnamed | one shared `version: 1` | §4 |
| Record file name `<id>-<slug>.md` | same | `lint_records` | none | §3 |
| Generated lessons, decision logs, decisions index, `known_gaps.md`, backlog | `records.py index` | humans; `check_plan`'s `ID_SOURCES`; `lint_contracts`; `lint_guards`; `lint_standards` | a marker line only | §6 |
| Citation grammar | humans | `check_records`, `renumber` | none | §5 |

## BLOCKER

- **W1, §5 and §1: a duplicate id still reaches `main`.** CI doesn't rerun when `main` moves, and `main` is
  unprotected, with no rulesets. Two PRs adding lesson 37 in different sections merge cleanly, and only the push run
  on `main` goes red. "Different files, no conflict" is half true: the committed index conflicts when records sort
  together, which is then the only detector. *Fix (unverified):* require up-to-date branches or another rerun
  policy, and say whether the generated files' shared hunks are a feature or a cost.
- **W2, §5 and R1: the renumber test can't fail on its real case.** A missed citation still resolves to the other
  branch's record, and a whole-file rewrite moves `main`'s legitimate citation. Fix: rewrite only lines added against
  the merge base, and test both errors with a shared file.
- **W3, §5 and §7: the id grammar fails on day one and gives false passes.**
  - Tokens with no record: `O2a O2b O2c O99`, `D12` ("D12, provisional"), `D16–D19` (review findings), `D53` and
    `D65` (Maxim's own decision ids), `D2395` (in a frozen pre-registration, so a permanent red), `T0` (a temperature),
    `T16a–c`, `B0`, `B018`, `B905` (a ruff rule), `B99` (a test fixture).
  - False passes: `T1-S1` and `D5-N1` in docstrings resolve as decisions.
  - The lesson grammar misses "Lesson N", "lessons N and N", "lessons N–N", "lessons §N" and the file-name form.
    "Lessons 32 and 33", the exact case §1 renumbered by hand, wouldn't be rewritten.

  *Fix (unverified):* scope the grammar to `docs/` and `reason=` strings, qualify Maxim ids, enumerate lesson
  spellings, and run R1's test over the real tree.
- **W4, §3–§5: "family" and the id grammar are undefined.**
  - Ten ids appear in two logs (O3–O7, O7a, O31, T1, T2, D20).
  - O spans four designs, and D is shared by `sem_stimuli` and `world_model`.
  - Per-directory uniqueness allows two O59s, while per-prefix uniqueness fails the migration.
  - Fourteen of 139 rows have no single id: "ruled 1–3", S4, "PH2-S2, re-ruled", "the split", "the rounds stop",
    "CLAUDE.md", "RT1–4", "D20, D25", "D26–D28", "D29, D30", "O23, O24, O31".

## SHOULD-FIX

- **W5, §8:** the round trip exempts the one column that carries information. 36 of 139 status cells aren't plain
  `live` ("also in", "restates", "amended by docs-contracts ruling …"), and none is derivable. Decisions have no title
  source, so 139 index lines would read `unknown`, and two date cells aren't ISO.
- **W6, §8 and R2:** backlog status lives inside prose (`**done**`), B23 and B24 have three cells, few gaps carry
  "Red gate:" or a closing step, and one gap is half closed, which `open`/`closed` can't express. `status`, `gate` and
  `closes_at` would duplicate the body. "Closed gaps" also contradicts #52's rule that a fixed gap is removed.
- **W7, §6:** the backlog cap (200) is below six rows (B5 about 447). The other maxima: lesson 31 about 458, O57 187, a
  gap 339. §4 of the plan is about 1,083 of its 2,500 words, not "a quarter".
- **W8, §4:** lessons are amended in place today, and #49 rewrites lesson 23; this is an owner question. The
  comparison must be against the merge base, and deletions need a rule.
- **W9, §8:** #49 is omitted (it adds lesson 37, edits lessons 23 and 33, and edits gaps). #48 edits B11 and B37.
  `migrate-branch` converts only added rows, and a late branch must merge `main` to get the tool, a merge that
  conflicts in the generated files. Fix: run the tool from a `main` checkout against the branch.
- **W10, §7:** retiring `missing_ids` drops coverage of the OD ids (81 in the roadmap, 84 in the plan).
- **W11, §4:** `read_yaml` reads whole files, not front matter; unknown-key and version refusal live in `core.schema`.
  Name the module, the delimiter grammar (a body containing `---`), the gate row, and versions per family.

## NIT

- **N1:** a lesson heading's date tail doesn't fit `date: ISO`.
- **N2:** `owner_section` takes values like "cites §8".
- **N3:** gap-slug `reason=` rewrites aren't in R3's commit list.
- **N4:** a one-at-a-time renumber can collide when shifting a range.
