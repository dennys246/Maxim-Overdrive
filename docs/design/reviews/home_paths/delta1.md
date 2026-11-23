# Review: phase1/home-paths, delta round 1 (Executor, Trust boundary, Architecture, Wire integrity)

Tree: `git diff 09e3449 a0ca10f`, with the round-1 records excluded, plus the records and the a0ca10f commit message.
Read-only: nothing in the worktree was edited, committed or stashed, and the gate was not run.

What I ran:

- `git archive a0ca10f` into `<scratchpad>/review_home/copy` (its own git repo), with the worktree's venv.
  - `tests/test_lint_paths.py` there: 34 passed.
  - Probes of `check_paths` against about 80 spellings, on a0ca10f's `lint_paths.py` and on 09e3449's (`git show`).
  - `tracked_text_files` on a scratch repo holding names with a newline, a tab, a space and CRLF, a deleted tracked
    file, a dangling symlink and an untracked file.
- `scripts/lint_standards.py` in the worktree at a0ca10f: PASS, 0 findings (22 rules held by a check, 27 by review).
- `check_paths` over the files each unmerged `origin/*` branch adds or changes. Only `origin/phase1/sim-replay` is
  flagged, in its one known file.
- Privacy: `git grep -a -i` across the tree at a0ca10f for the local account name and the mini's login; the same
  search across `git log origin/main..a0ca10f`; and a search of the a0ca10f diff and the 041dd72 merge for hostnames,
  tailnet names, private IPv4 and home roots. The merge adds no home path. Its one hit is `$HOME/overdrive-gate/…` in
  `spikes/specgen/run_window.sh`, which is a variable, not a path. The test ids show only the roots, never the
  sample name.

## Deletion proofs re-run (on the copy)

| Mechanism deleted | Result | Matches the commit message |
|---|---|---|
| `-z` (back to `splitlines`) | `test_files_with_non_ascii_names_are_read` red, 1 failed | yes |
| `_ROOT`'s lookbehind | the `docs/users/` pass case and `test_the_repository_holds_no_home_directory` red | yes |
| path-form name back to stopping at `-` | `test_a_public_accounts_name_with_more_after_it_is_someone_else[/Users/]` and `[/home/]` red | yes |
| `DASH_HOME`'s lookbehind (not in the message) | the prose pass case and the whole-repository test red | (extra) |
| `._-` dropped from `_ROOT`'s lookbehind | **34 passed**: nothing guards that part (D4) | n/a |

## Status of round-1 findings (read from the tree)

| Finding | Status | Basis |
|---|---|---|
| F1 BLOCKER | **fixed** | `ci_cost/round1_trust.md:42` now reads `<owner>`. A whole-word search for the login over the tree at a0ca10f finds nothing. See D6 on what the redaction does and doesn't hide. |
| F2, AW-S4 | **fixed** | All 11 new spellings are refused, each in its own parametrized case. The docstring now lists spellings instead of claiming "every", and CLAUDE.md and B45 no longer say "any spelling". D1 is a regression this fold introduced in neighbouring spellings, so it is a new finding, not a reopening. |
| F3 | **fixed** (path names, non-ASCII names); **deferred** (non-UTF-8 text) | The file-path scan has a test, and its masking has a proof. `-z` has a test and a proof. Non-UTF-8 text is named in B45 as review-held, which is its record, though B45's trigger column reads only "open". |
| F4 | **fixed** | B45 names history, merged-PR refs, forks, and commit and PR text, and says GitHub Support is the route, unverified. |
| F5 | **fixed** | `/Users/runner-<name>` is refused for the path form (proof above), and `//Users//` is in SPELLINGS. The dash form's pass is stated and tested. |
| F6, AW-N2 | **fixed**, but the fold's account of it is false | `docs/users/` and hyphenated prose pass, each with a test. The fold table says "URL routes like `/home/<route>` after a host still match". Measured: `https://example.com/home/<page>` now passes, where at 09e3449 it was refused. The same cause is D1. |
| F7, AW-N1 | **fixed** | B45: "21 paths in 16 review files", which matches round 1's count. |
| AW-S1 | **fixed** | The row is B45. No unmerged `origin/*` branch adds a B45. #47 has since merged its B44 (see AW-N5). |
| AW-S2 | **deferred**, the right disposition | Which branch renumbers depends on merge order, and this branch can't know it. Trigger: the second of #55 and this branch to merge renumbers to check 9, in the docstring, `main` and the commit text. The hand-off must carry it. |
| AW-S3 | **deferred**, the right disposition | Re-measured with the new patterns: `origin/phase1/sim-replay` still has exactly one flagged file, `docs/design/reviews/sim_tick/round1_det_bio.md`, and no other unmerged branch does. Going red on #49 is the check working. Trigger: #49's next merge of main. The fix is that branch's. |
| AW-S5 | **fixed** | CLAUDE.md says "a local account name" and exempts the public account and the authorship name. |
| AW-S6 | **deferred**, the right disposition | #47 owns that roadmap text (one owner per contract). #47 has merged since, so the hand-off now goes to whichever session owns the go-public items on main. |
| AW-N3 | **fixed** | The prepush step label names home paths. |
| AW-N4 | **rejected** (reviewer's status) | The leak comes from what sessions and review agents write into records, which is the concern of the Working rules beside it (worktree isolation, signing). "Data and assets" is about tunables and licensed files. Either place is defensible, and moving it gains nothing. |
| AW-N5 | **open again** | `origin/main` moved to d7b6233 (#47 and #51 merged) after 041dd72. `git merge-tree` reports a content conflict in `docs/standards_backlog.md`, where #47's B44 and this branch's B45 both append after B43. Keeping both rows resolves it. The new files add no home path. |

## New findings

### D1 SHOULD-FIX: `scripts/lint_paths.py::_ROOT` and `DASH_HOME`: the anchors hide homes behind a mount or host prefix

The fold added the lookbehinds to stop `docs/users/` matching once the patterns became case-insensitive. A real home
path often comes after a prefix that ends in a letter, though. Each case below passes at a0ca10f and was refused at
09e3449 (both measured):

| Input (placeholder form) | Where it occurs |
|---|---|
| `/c/Users/<name>/x` | Git Bash (MSYS2) on Windows, the most common Windows git shell |
| `/cygdrive/c/Users/<name>` | Cygwin |
| `/System/Volumes/Data/Users/<name>/x` | macOS's firmlinked data volume, printed by `df`, `mount`, fs_usage and some crash reports |
| `/Volumes/<disk>/Users/<name>/x` | a second disk, or a Time Machine backup |
| `-System-Volumes-Data-Users-<name>-…` | Claude Code's dash encoding of the path above |
| `file://localhost/Users/<name>/x` | NSURL and plist output |
| `ssh://host/home/<name>/repo.git`, `vscode-remote://ssh-remote+host/home/<name>/x` | remote URLs in logs and editor settings |
| `../../Users/<name>/x` | a relative path out of a repository (also D4) |

The author fixed one member of this class, WSL's `/mnt/c/Users`, by naming it. The class itself is "a home under any
prefix ending in a letter or digit", and naming members one by one won't close it.

Failure scenario: a review record quotes a Git Bash traceback (`/c/Users/<name>/repo/...`) or a `df` line from the
mini. The gate passes, CI passes, and the name is published. The docstring's "Each counts only where a path can
start" is literally true, but CLAUDE.md says "No file holds a path under a home directory (`/Users/<name>`…)", and a
reader takes `/System/Volumes/Data/Users/<name>` to be that.

Extra cases, which also failed at 09e3449: the UNC and WSL shares `\\localhost\c$\Users\<name>` and
`\\wsl$\<distro>\home\<name>`, and a fully URL-encoded file URL (`file%3A%2F%2F%2FUsers%2F<name>`), because only
`/+` repeats and `%2f` doesn't.

There is a trade-off for the author, not designed here: the false positive is real. The tree holds
`docs/users/observations.md` (in `research/sem_stimuli/4_prior_art.md`), which is why the unanchored pattern failed
there.

### D2 SHOULD-FIX: `scripts/lint_paths.py::PATH_HOME`: a name that starts with a non-ASCII letter passes

The name class is ASCII (`[a-z0-9_]…`), so `C:\Users\<name starting with É>\x` passes, and so does a CJK profile
name (measured). Windows creates profile folders from display names, so non-ASCII profile names are common there. A
name with a non-ASCII letter in the middle is caught only up to that letter, and a masked file path then prints the
tail (`<name>é…`).

This is not a regression: 09e3449 missed it too. But this fold is the one that made non-ASCII file names visible
(F3), and neither the docstring nor B45 records the gap. Failure scenario: a Windows contributor's path in a pasted
log passes the gate.

### D3 NIT: `scripts/lint_paths.py::masked`: overlapping matches print part of a name

`masked` replaces from the right using offsets taken before any replacement. When a `DASH_HOME` match sits inside a
longer `PATH_HOME` name and is shorter than `<name>`, the inner replacement shifts the text, and the outer
replacement then stops short of the end of the original name.

Measured: a file path of the form `docs/C:/Users/<a>_-home-<bb>-<cdefgh>/r.md` (with real letters in place of the
placeholders) printed `docs/C:/Users/<name>efgh/r.md`. The last four letters of the name reached the log.

It is contrived: it needs `_-home-` inside an account name, in a file path. Failure scenario: such a path appears and
CI's public log shows a fragment of the name.

### D4 NIT: `scripts/lint_paths.py::_ROOT`: the `._-` part of the lookbehind has no test, and it opens `../Users/<name>`

Deleting `._-` from `(?<![a-z0-9._-])` leaves all 34 tests green (measured), so no test can fail for that part.

What it does in practice is let `./Users/<name>`, `../Users/<name>` and `_/Users/<name>` pass. A relative path out of
a checkout still names the account. Failure scenario: a record says "ran `../../Users/<name>/tool`" and passes.

Either drop the characters, or keep them with a pass case that needs them. Which one is the author's call.

### D5 NIT: `scripts/lint_repo.py::tracked_text_files`: a symlink's target is never scanned

This predates the fold, but the fold widened the claim to "file contents and file paths". A tracked symlink's blob is
its target path. `p.is_file()` follows the link, so a dangling target is skipped (measured), and a live one has the
target file read instead of the link text. A committed link to `/Users/<name>/…` therefore publishes the name and
passes the check. Failure scenario: a session commits a convenience symlink into a scratch or model directory.

Not in B45.

### D6 NIT: `docs/standards_backlog.md::B45`, the F1 records: the redacted login is public in every commit's metadata

The login F1 redacted equals the local part of the commit-author email on this branch's commits (checked). It is
therefore public in every commit's header, whatever the tree says. Round 1's report notes that it is "the local part
of the commit-author email", but B45 and the fold present it as a name that review found and removed.

The fold's records also point at the exact history line: "`ci_cost/round1_trust.md:42` … the Mac mini's login", and
"half of an SSH target". Failure scenario: the owner reads B45, believes the login is private again, and keeps
relying on that.

The honest statement is one clause in B45: "also public as the commit-author email's local part".

### Checked and found sound

- **`-z`.** Names with a newline, a tab, a space or non-ASCII characters are all read. CRLF content reads as `\n`
  (universal newlines, as before). A deleted tracked file and a dangling symlink are skipped, as before. Untracked
  files are listed. `filter(None, …)` drops the trailing empty field.
  - A name that isn't valid UTF-8 would now make the decode raise, so the lint fails loudly rather than silently. APFS
    refuses to create such a name (measured, errno 92), so only a Linux checkout could hit it.
  - Every other standards check now reads files it used to skip. `lint_standards` still reports 0 findings.
- **The trailing-dash rule.** `/Users/<x>-/` is still refused, because the regex backtracks to the name.
  `/Users/runner-<name>` passes and `/Users/runner-<x>`, with a real suffix, is refused (proof above).
- **Case-sensitive `PUBLIC_ACCOUNTS`.** `/Users/` followed by `shared` in lower case is refused. That is a false positive in the safe
  direction, and not a finding.
- **Privacy.** Apart from D6, nothing in the tree at a0ca10f, the branch's commit messages or the test ids holds a
  local account name, a home path, a hostname or a private address. The round-1 reports and fold.md pass the branch's
  own check.
