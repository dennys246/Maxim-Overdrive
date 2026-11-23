# phase1/home-paths: round 1 folds

Round 1 (2026-11-22): Executor and Trust boundary (`round1_executor_trust.md`), Architecture and Wire integrity
(`round1_arch_wire.md`), on 09e3449. The "Author's fold" column is the author's claim; "Status" is set by a delta
reviewer from the tree (O25). The reports' sample paths are written `<name>`, so the check this branch adds passes them.

| Finding | Author's fold | Status |
|---|---|---|
| F1 BLOCKER: `ci_cost/round1_trust.md:42` still held a local account name (the Mac mini's login) | `<owner>`; a sweep for the login found no other bare use; B45 names both hand-found names | |
| F2, AW-S4: "every spelling" false (case, escaped and forward separators, URL encoding) | `lint_paths.py`: both patterns case-insensitive; separators `\`+, `/`+ or `%2f`; `C:/Users`, `/mnt/c/Users` (WSL); 11 new spellings in `test_every_spelling_of_a_home_directory_is_refused`. The docstring lists the spellings rather than claiming all | |
| F3: file paths, non-ASCII names and non-UTF-8 text are unscanned | File paths checked, printed with the name masked (`masked`); `lint_repo.tracked_text_files` lists with `-z`, so every standards check now reads non-ASCII names; non-UTF-8 text recorded in B45 | |
| F4: the history claim omits PR refs and forks | B45: history, merged PRs' refs, forks and commit and PR text keep what was published; a rewrite of `main` doesn't reach the refs or forks (GitHub Support, per GitHub's documentation; not verified here) | |
| F5: `/Users/runner-<name>` passed as `runner`; `/Users//<name>` passed | The path form's name runs to the next separator; separators may repeat. `test_a_public_accounts_name_with_more_after_it_is_someone_else`. The dash form can't tell `runner-x` from `runner`'s project, so it passes there (tested) | |
| F6, AW-N2: hyphenated prose and in-repo `users/` dirs refused | Both forms count only where a path can start (not after a letter, digit or path character); the anchoring made `docs/users/` in the tree pass and would have hidden WSL's `/mnt/c/Users`, which is now named; URL routes like `/home/<route>` after a host still match (the safe direction) | |
| F7, AW-N1: "17 review files" | B45: 21 paths in 16 files | |
| AW-S1: PR #47 adds a different B44 | Renumbered to B45 here | |
| AW-S2: PR #55 adds a "check 8" in the same hunks | Not foldable here: whichever merges second renumbers. Named in the hand-off | |
| AW-S3: PR #49 adds a home path, so it goes red once this merges | Intended; named in the hand-off with the fix (`<scratchpad>`) | |
| AW-S5: the rule says "a username", false for the public handle | CLAUDE.md: "a local account name"; the public GitHub account and the authorship name are not private | |
| AW-S6: roadmap go-public item 4 is stale and #47 owns that text | Not edited here (one owner); named in the hand-off for #47 | |
| AW-N3: the prepush step label | Names home paths | |
| AW-N4: the rule may belong under "Data and assets" | Author's view: kept under Working, beside the other rules about what a session writes; the reviewer's call | |
| AW-N5: behind origin/main | Merged (041dd72) | |
