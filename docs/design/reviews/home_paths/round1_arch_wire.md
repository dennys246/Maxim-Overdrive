# Review: phase1/home-paths, Architecture and Wire integrity

Reader: Architecture and Wire integrity lenses. Tree: `git diff 53cd42c..09e3449` and the commit message. Read-only: I
edited nothing in the worktree and did not run the gate.

What I ran:
- `.venv/bin/python scripts/lint_standards.py`: PASS, 0 findings, 22 rules enforced by a check, 27 held by review.
- `.venv/bin/pytest -q -p no:cacheprovider tests/test_lint_paths.py`: 16 passed.
- `check_paths` over every text blob of `53cd42c`'s tree, read through `git show`: 18 findings in 16 files. Counting
  `-Users-<name>` occurrences in the 17 changed review files at base gives 21 paths on 18 lines in 16 files. The
  commit message's counts hold.
- `check_paths` on hand-made edge cases (results under AW-S4 and AW-N2).
- `git grep` and `git diff 53cd42c...origin/<branch>` for the seven open PRs (`gh pr list`). Every local
  `origin/<branch>` matched its PR's head SHA.
- `git merge-tree --write-tree HEAD origin/main`: merges clean. `origin/main` has moved to c6d4f10 (#50) and adds no
  home paths.

## Verdict on the questions asked

- **Root fix or band-aid.** The commit 2c1d8d8 scrub was a one-off grep. The real cause is that sessions and review
  agents write absolute scratchpad paths into records, and that will keep happening (see AW-S3). A gate check that
  every branch must pass is the right place: it is enforced once, not at each call site. `check_paths(files)` has one
  job, takes the same `files` map from `lint_repo.tracked_text_files` as `check_inputs`, and `lint_standards.main`
  wires it in one line. This is consistent with the sibling modules. No finding.
- **Exemption mechanism.** A two-name public-account allowlist in code (`runner`, `Shared`) is the better choice. A
  per-line marker would let a real path be waived by whoever writes the line, and the waived line would still publish
  the name. Tests that need a sample build it at run time, which works. No finding.
- **Shipped path.** `scripts/prepush.sh:86` runs `scripts/lint_standards.py --base "$BASE"`.
  `.github/workflows/test.yml:41` and `drift.yml:44` run `scripts/prepush.sh`, so a planted path fails both the local
  gate and CI. `tests/test_lint_standards.py::test_main_refuses_a_home_directory_in_an_untracked_file` covers the
  wiring. The commit says deleting the call turns that test red; I did not re-run that deletion.
- **Scrubbed records.** I read all 19 replaced lines. No sentence is mangled. `$D = <scratchpad>/review_perf/` still
  reads as an assignment. Paths at the end of a sentence keep their full stop, and the backtick spans are intact. One
  loss: records from four different sessions now share one `<scratchpad>`, so a record no longer says which session
  did the work. Scratchpads aren't durable anyway, so this needs no finding.

## Findings

### AW-S1 SHOULD-FIX: `docs/standards_backlog.md::B44`, the same id as PR #47's B44

PR #47 (`phase1/maxim-run-standard`) appends `| B44 | Run Maxim when integration needs it | … |` after B43, and its
new CLAUDE.md rule cites `Guard: B44`. This branch appends a different B44 at the same place.

Failure: whichever PR merges second gets a textual conflict at the end of the backlog. If it is resolved by keeping
both rows, `lint_guards.check_guards` reports "backlog row B44 is defined 2 times", and the gate goes red on main's
next merge. If it is resolved by keeping one row, one of the two CLAUDE.md rules cites the wrong row, and the lint
can't see that.

Fix (unverified): the second PR to merge renumbers to B45 and updates its CLAUDE.md citation and its test text. The
hand-off should name the collision so the owner picks the order.

### AW-S2 SHOULD-FIX: `scripts/lint_standards.py` module docstring and `main`, check 8 claimed twice

PR #55 (`phase1/id-check`) adds `8. Record ids no two branches may share … lint_ids.py`, `from lint_ids import
check_ids` and `problems += check_ids(files)` at the same three hunks this branch uses for `lint_paths`. It also adds a
`_load` line next to this branch's in `tests/test_lint_standards.py`.

Failure: the second merge conflicts in all four places. A careless resolution leaves two checks both numbered 8, or
drops one of the `problems +=` lines. Only the dropped-line case is caught, by each branch's wiring test.

Fix (unverified): whichever lands second renumbers to 9. The commit message's "standards check 8" and the docstring
of `lint_paths.py` ("Standards check 8") move with it. Say this in the hand-off.

### AW-S3 SHOULD-FIX: hand-off, open PR #49 goes red once this merges

`origin/phase1/sim-replay` (PR #49) adds `docs/design/reviews/sim_tick/round1_det_bio.md:5`, which holds a
dash-encoded scratchpad path with the owner's username. None of the other six open PRs add one. #53 and #55 still
carry the 16 old files, but only because their merge base is older; merging main fixes those.

Failure: after this merges, #49's next merge of main fails `check_paths` at the gate and on CI. That is the intended
behaviour and acceptable, but the owner of #49 learns about it only from a red run. Every session's review agents
will keep producing such lines until their briefs say to write `<scratchpad>`, as this round's brief did.

Fix (unverified): the hand-off names #49 and its file, and tells other sessions to have reviewers write
`<scratchpad>`.

### AW-S4 SHOULD-FIX: `scripts/lint_paths.py::HOME` does not catch "every spelling"

These measured cases pass the check:
- `c:\users\<name>\x`: lowercase Windows root.
- `C:\\Users\\<name>\\x`: escaped backslashes, which is how a Windows path appears in JSON, a log dump or a Python
  string literal.
- `/USERS/<name>`: macOS's default APFS is case-insensitive, so this path is valid there.
- `%2FUsers%2F<name>`: URL-encoded.

`C:/Users/<name>` and `file:///Users/<name>` are caught. The claim "in every spelling" appears in the commit subject,
the CLAUDE.md rule, the module docstring and B44.

Failure: a Windows contributor's traceback pasted into a review record as JSON, or an escaped path in a `.py` literal,
passes the gate and publishes the name. The docs say this is impossible.

Fix (unverified): either make the match case-insensitive and accept one or more backslashes, with a test for each
case, or narrow the wording to the spellings that are actually checked.

### AW-S5 SHOULD-FIX: `CLAUDE.md::"No personal details in the tree"`, the rule is false on the tree as worded

The rule says no file holds "a username". The owner's public GitHub account appears in `CLAUDE.md` line 3, `README.md`
and five more documents, and the owner's surname appears in `pyproject.toml` and `ASSETS_LICENSE.md` as authorship. The
title "No personal details" makes the same overclaim.

Failure: a reviewer applying the rule and B44 literally flags the licence and the package metadata, or the rule
silently means less than it says. Either way, review is no longer holding a precise rule.

`lint_guards` counts the rule as check-enforced (22, up from 21) while most of its clauses (usernames, hostnames,
addresses) are review-only. That follows the existing mixed-guard convention (B1 plus a check), and the parenthetical
on B44 is honest, so this is not a separate finding.

Fix (unverified): name what is meant, for example a local account name, a machine's hostname or tailnet name, and a
private address. Say that authorship and the public account are allowed.

### AW-S6 SHOULD-FIX: `docs/roadmap.md` "Before the repository goes public" item 4, stale, and owned by #47

On main, item 4 still reads "absolute paths under the owner's home in seven files (three spike scripts and four
documents, found 2026-11-21) become relative or are removed". #48 removed those paths and this branch removes 21 more,
so the count understates the scope and the item reads as not done. PR #47 rewrites that section's preamble to say
"Items 2, 4 and 5 are still open".

Failure: once both merge, the roadmap says item 4 is open, which is untrue. The section also never records that the
first scrub missed the dash-encoded form, the lesson this branch exists for.

This branch is right not to edit the section, because #47 owns that text. Fix (unverified): the hand-off asks #47 to
mark item 4 done, citing this branch and B44 (history not rewritten).

### AW-N1 NIT: `docs/standards_backlog.md::B44`, "17 review files" contradicts the commit's 16

Measured: 16 files held the dash-encoded paths. The 17th changed file, `ci_cost/round1_trust.md`, held only the
`ls -l` owner column, which B44 mentions separately. As written, B44 attributes all 17 files to the paths.

### AW-N2 NIT: `scripts/lint_paths.py::HOME`, false positives on ordinary hyphenated prose

Measured: `a work-from-home-office` and `the Power-Users-guide` are both refused. The failure is loud, not silent, but
the message tells the author to write `<home>`, which doesn't apply to prose, and rewording is the only way out.

Fix (unverified): anchor the dash form to what Claude Code emits, a `-Users-<name>-` that directly follows a `/`.

### AW-N3 NIT: `scripts/prepush.sh:85`, the step label doesn't name the new check

The label lists "TEMPORARY markers, pragmas, guard citations, size limits, coverage and size ratchets". Someone
reading a red gate log won't learn from it that home paths are checked here.

### AW-N4 NIT: rule placement

The rule sits under Working, between "Record lessons" and "Engine choices". It governs what may be committed, like the
`.env`, SDK and licensed-asset rule under "Data and assets", so it may belong there. This is a judgement call, and the
current placement is defensible.

### AW-N5 NIT: the branch is behind main

`origin/main` is at c6d4f10 (#50). The merge is clean and adds no home paths. Merge main and rerun the gate before
handing over, so the PASS line is for the merged tree.

Counts: 0 BLOCKER, 6 SHOULD-FIX, 5 NIT.
