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

## Delta round 1 folds

Statuses of round 1's findings are in `delta1.md` (its sample URL written `<page>`). The statuses it set are copied here
by the author for the record; the report is the source. Round 1: F1 fixed (see D6); F2, AW-S4, F4, F5, F7, AW-N1,
AW-S1, AW-S5, AW-N3 fixed; F6, AW-N2 fixed, with the fold's URL claim false (D1 below makes it true again); F3 fixed
but non-UTF-8 deferred to B45, whose trigger read only "open"; AW-S2, AW-S3, AW-S6 deferred to the other PRs (#47 has
merged, so AW-S6 goes to whoever owns the go-public items); AW-N4 rejected (the rule belongs under Working); AW-N5 open
(main moved again).

| Finding | Author's fold | Status |
|---|---|---|
| D1: anchoring hid every home after a prefix (`/c/Users`, `/Volumes/<disk>/Users`, `file://localhost`, `../Users`) | Homes are told by spelling, not position: `Users` and `home` as the systems spell them count after any separator; other cases only where a path starts (`docs/users/` stays a directory). WSL's special case is gone. Eight prefixed spellings tested. The dash form keeps its anchor (prose), and a dash-encoded home after an encoded prefix is recorded in B45 | |
| D2: names starting with, or holding, a non-ASCII letter | Names are Unicode `\w`; `test_a_name_in_any_script_is_a_name_and_is_masked_whole`. The test found that a dash-encoded name's end can't be told (`-Users-<first>-<last>-`), so a dash form is masked to its path component's end | |
| D3: overlapping matches leak letters through the mask | Spans merge; `test_overlapping_names_are_masked_as_one` | |
| D4: the lookbehind's `._-` untested | `./users/x`, `../users/x`, `a_/users/x`, `a-/users/x` in the pass cases | |
| D5: a symlink's target is never scanned | B45 | |
| D6: the mini's login is the commit email's local part | B45: redacting it keeps the tree consistent, not secret | |
| (author) line findings printed the file's path unmasked | `check_paths` prints the masked path on every finding; `test_a_line_finding_prints_its_files_path_masked` | |
| B45's trigger read "open" | "No step yet: review holds it; a leak found in review gets a pattern here if one can see it" | |
| AW-N5: behind main | Merged with the delta fold | |

## Delta round 2 folds

Statuses of delta round 1's findings are in `delta2.md`: D1, D3, D4, D6, the unmasked-line row, B45's trigger and
AW-N5 fixed; D2 open in part (E1); D5 deferred to B45. Its new findings:

| Finding | Author's fold | Status |
|---|---|---|
| E1: combining marks, a space in a Windows profile and a URL-encoded name leak through the mask or escape detection | The third patch to the name's boundary was due, so the approach changed: `masked` cuts a path where its first private name starts and prints `<name>…`, whatever follows, so where a name ends no longer matters to what prints. A name may start with `%` (URL-encoded) in both forms; the test found the dash form missed it and printed the path unmasked. `_account` reads only the account a name begins with, for `PUBLIC_ACCOUNTS`. Eight names tested, none of whose parts reaches a finding | |
| E2: JSON's `\/` and `%5C` separators pass | `_SEP`: slashes or backslashes in any run, `%2F` or `%5C` | |
| E3: any directory spelled exactly `home` or `Users` is refused, a `res://…/home/` one too | `NOT_A_DISK`: Godot's `res://` and `user://` and web URLs are on no one's disk and are skipped; `ssh://` and `file://` homes still count (tested). Any other exact `Users` or `home` directory is refused, and the docstring says so and what to do | |
| E4: the test module cites B44 | B45 | |
| AW-N5: main moved | Merged (4b09fbb) | |

## Delta round 3 folds

Statuses of delta round 2's findings are in `delta3.md`: E1, E2, E4 fixed; E3 fixed in part (a `client/game/home/`
file was still refused); AW-N5 fixed for 06c2774 (main moved again). Its new findings:

| Finding | Author's fold | Status |
|---|---|---|
| D3-S1: the URL exemption skipped the rest of any token, hiding homes in JSON lines, dev-server links and queries | Web URLs aren't exempt: nothing in the tree or the open PRs needed it. `NOT_A_DISK` is Godot's `res://`, `user://` and `client/` tokens, ending at a quote, comma, bracket or space, and inside them only the exact-spelling form is skipped, never the dash form. Four D3-S1 cases tested | |
| E3 (rest): a `client/game/home/` file refused | A path under `client/` is Godot's `res://`, as file path or in text (`test_a_godot_projects_own_home_directory_is_not_a_home`); a scratchpad copied there is still refused | |
| D3-N1: a file path holding a home the check can't see prints unmasked on its lines' findings | B45 (it follows from B45's blind spots) | |
| D3-N2: names starting with `.`, `@`, `+` or an emoji | B45 | |
| D3-N3: 947d90e's message says masking only the matched name turns the combining-mark cases red | Author's correction: it doesn't; those cases are held by the cut and by `_NAME`'s Unicode class together, so either alone keeps them green. The spaced and overlap cases are the cut's | |
| D3-N4: `ssh://host/home/` listed twice | The second copy removed | |
| (author) the `client/` file-path flag in `masked` | Removed: its deletion left every test green, because the `client/` token already covers a file path | |
