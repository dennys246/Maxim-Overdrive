# Review: phase1/home-paths, delta round 2 (Executor, Trust boundary, Architecture, Wire integrity)

Tree: `git diff a0ca10f bb4c075`, the merge de4e45d (`docs/standards_backlog.md` resolution, `git diff
origin/main...de4e45d --stat`), `fold.md` ("Delta round 1 folds") and bb4c075's commit message. Read-only: nothing in
the worktree was edited, committed or stashed, and the gate was not run.

What I ran:

- `git archive bb4c075` into `<scratchpad>/review_home/copy2` (its own git repo), with the worktree's venv.
  `tests/test_lint_paths.py` there: 48 passed. Five deletion proofs (table below), each run with
  `tests/test_lint_paths.py tests/test_lint_standards.py`, and each restored with `git checkout` before the next.
- About 35 probe strings through `check_paths` and `masked`, on bb4c075's `lint_paths.py` and on a0ca10f's
  (`git show`), so I could tell regressions from gaps that were already there.
- `scripts/lint_standards.py` in the worktree at de4e45d: PASS, 0 findings (22 rules held by a check, 28 by review).
- `check_paths` over the whole tree of `git merge-tree de4e45d origin/main` (main has moved to 06c2774, #54). The merge
  is clean, with no conflict and 0 findings.
- `gh pr diff` for the open PRs #49, #52, #53 and #55, with `_private` run over every added line. The one hit is #49's
  known `docs/design/reviews/sim_tick/round1_det_bio.md` (AW-S3). No false positive.
- Privacy: `git grep -a -i` at de4e45d for the local account name, the mini's login (as a whole word, which leaves out
  the public GitHub account), `ts.net`, and private IPv4 ranges (10/8, 192.168/16, 100.64/10). The same search ran over
  `git log origin/main..de4e45d`, and over the collected test ids of `tests/test_lint_paths.py`. The tree hits are
  only prose about tailnets in review records, with no name in them. The log and the test ids are clean.

## Deletion proofs re-run (on the copy)

| Mechanism deleted | Red | Matches the message |
|---|---|---|
| `_EXACT` dropped from `PATH_HOME` | 8 spellings: `/mnt/c`, `/c`, `/cygdrive/c`, `/System/Volumes/Data`, `/Volumes/Backup`, `file://localhost`, `ssh://host/home`, `../Users` | yes ("the eight prefixed spellings"). `](/Users/` stays green, because `_AT_START` catches it. That is fine, but it is not an exact-case guard. |
| `_AT_START` lookbehind reduced to `\w` | the `./users` pass case, `test_the_repository_holds_no_home_directory`, `test_the_repository_itself_passes` | yes |
| span merge disabled (`if False:`) | `test_overlapping_names_are_masked_as_one` | yes |
| line findings back to `{rel}` | `test_a_line_finding_prints_its_files_path_masked` and the 3 Unicode cases | yes |
| dash span back to the name's end | the file-path test, `ana-élise` and the overlap test | yes |

## Status of delta-1 findings (read from the tree)

| Finding | Status | Basis |
|---|---|---|
| D1 SHOULD-FIX | **fixed** | All of D1's prefixed spellings are now refused, and so are its extras: UNC `\\localhost\c$\Users\<name>`, `\\wsl$\<distro>\home\<name>`, `file%3A%2F%2F%2FUsers%2F<name>` and `vscode-remote://…/home/<name>`. The dash form after an encoded prefix is **deferred** to B45, which names it. Its trigger is review. The trade is new false positives for any directory spelled exactly `home` or `Users` (E3). |
| D2 SHOULD-FIX | **open, in part** | Fixed for letters Python's `\w` counts: precomposed Latin and CJK names are found and masked whole. Still open for D2's second half, "a name … caught only up to that letter, and a masked file path then prints the tail": a letter that `\w` doesn't count still stops the name (E1). |
| D3 NIT | **fixed** | Spans merge. D3's own case (`docs/C:/Users/<a>_-home-<b>-<c>/r.md`) now masks to `docs/C:/Users/<name>/r.md`. Proof 3 is red. |
| D4 NIT | **fixed** | The pass case needs `.` and `-` in the lookbehind (`_` now comes from `\w`). Proof 2 is red. |
| D5 NIT | **deferred** (B45) | B45 now names "a symlink's target". Its trigger is a leak found in review. I accept that, with one note: unlike the others in B45, this one a check could see cheaply (`git ls-files -s` mode `120000`). |
| D6 NIT | **fixed** | B45 says the login is also the commit author address's local part, so the redaction "keeps the tree consistent rather than secret". The commit message says it too. |
| (author) line findings printed the path unmasked | **fixed** | `check_paths` prints `shown` on every finding. Proof 4 is red. |
| B45's trigger read "open" | **fixed** | It now reads "No step yet: review holds it; a leak found in review gets a pattern here if one can see it". That is an event, which counts as a trigger. |
| AW-N5 | **fixed** for d7b6233 | The merge is correct (see below). `origin/main` has since moved to 06c2774 (#54). `merge-tree` is clean and the merged tree has 0 findings, but the branch must merge main again before hand-off. |

**Merge resolution.** In de4e45d, `docs/standards_backlog.md` holds B44 (#47's, unchanged from main) and then B45
(this branch's, unchanged from bb4c075), in id order, with no duplicate id (`uniq -d` is empty). `lint_standards.py`
passes at de4e45d.

## New findings

### E1 SHOULD-FIX: `scripts/lint_paths.py::_NAME` and `masked`: a name `\w` cuts short leaks its tail, and a percent-encoded name isn't found

The fold's claim is "masks that leak nothing", and the D2 test names any script. Python's `\w` counts letters and
digits, though, not combining marks. Three cases, each measured on bb4c075:

1. **Combining marks.** Devanagari, Bengali, Thai and similar scripts write almost every name with a vowel sign or a
   virama, which are marks (Mn or Mc), not letters. A decomposed (NFD) Latin name, as macOS tools often emit, has the
   same problem. Each one is found, but the name stops at the first mark. A file path such as
   `docs/Users/<a Hindi name>/x` therefore prints `docs/Users/<name>` followed by every letter after the first mark of
   the real name. The NFD form of a name like `élodie` prints `<name>` plus a combining accent and `lodie`.
   `test_a_name_in_any_script_is_a_name_and_is_masked_whole` covers only precomposed Latin and CJK, so it can't see
   this.
2. **Spaces.** Windows creates profile folders from display names, which can hold a space. A file path under
   `C:\Users\<first> <last>\` prints `<name> <last>`, so the surname reaches the CI log.
3. **Percent-encoding.** A `file:` URL that NSURL or VS Code builds for a non-ASCII account percent-encodes the name,
   as in `file:///Users/<percent-encoded-name>/x`. The name then starts with `%`, which `\w` doesn't match, so the home is **not
   found at all**: the check passes it. This is the URL form of D2's original miss.

Case 3 was already a gap at a0ca10f, and cases 1 and 2 leak only through a file path's mask, never through a line
finding's text. All three contradict the fold's stated property, though, and nothing in the docstring or B45 records
them.

Failure scenario: a contributor with a Hindi account name copies a scratchpad folder into `docs/`. The gate refuses
it, correctly, but CI's public log prints most of the name.

### E2 NIT: `scripts/lint_paths.py::_SEP`: JSON-escaped and percent-encoded backslash separators pass

The docstring says separators may be "escaped". A JSON-escaped slash is not covered:

- `"\/Users\/<name>\/x"` passes. `\\+` takes the backslash, then the next character must be `Users` or the name, but
  it is `/`. PHP's `json_encode` and some JavaScript loggers escape slashes this way.
- `C:%5CUsers%5C<name>` (a percent-encoded backslash) passes too.

Both were gaps at a0ca10f as well. Failure scenario: a pasted JSON log from a tool that escapes slashes carries a home
directory past the gate.

### E3 NIT: `scripts/lint_paths.py::_EXACT`: any directory spelled `home` or `Users` is refused, with no way to pass it

This is the cost of D1's design. Measured, each of these is refused at bb4c075 and passed at a0ca10f:

- a URL route, `https://example.com/home/<page>`;
- a Godot resource path, `res://game/home/<scene>.tscn`;
- a source directory, `src/Users/<x>.py`;
- a path in a home-named folder under `~`, `~/home/<x>`.

The tree and every open PR's added lines carry none of these today (measured), so the cost is zero now. But this is an
RPG, and a `home/` directory for a player's base under `client/game/` or `data/world/` is a plausible name. When one
arrives, the whole directory fails the gate, and the only remedy is renaming the directory. The `ADVICE` text ("write
<home>, <scratchpad> or a path relative to the repository") doesn't fit that case, and the docstring doesn't say that
routes and repository directories with these exact names are refused.

The same class already existed for the dash form at a0ca10f: a CLI flag or CSS class that starts `--home-` or
`--users-` followed by a word is refused.

Failure scenario: a later step adds `client/game/home/` and the gate goes red, with a message that tells the author to
use a placeholder.

### E4 NIT: `tests/test_lint_paths.py` module docstring: cites B44, which is now #47's row

The docstring reads `(CLAUDE.md, "No personal details in the tree"; B44)`. AW-S1 renumbered the row to B45, but this
citation was missed. Since the merge, B44 is "Run Maxim when integration needs it", so the citation points at the wrong
rule. Failure scenario: a reader or a future id lint (#55's `lint_ids`) follows B44 to an unrelated row.

### Checked and found sound

- **`_COMPONENT_REST`.** It masks a dash form to the end of its component, which is at the next `/`, `\`, whitespace,
  backtick or quote. That is never too little, because an encoded name can't cross a slash. It can be too much (it
  hides the repository part of `-Users-<name>-<repo>`), but only in a file path's finding, and that costs readability,
  not privacy.
- **Line findings.** Their text is never printed, only the masked path and the line number, so E1 reaches only file
  paths.
- **`shown != rel`** is equivalent to `_private(rel)` being non-empty. A public-account match leaves the text
  unchanged, and a private match always changes it.
- **Privacy.** Nothing in the tree at de4e45d, in `git log origin/main..de4e45d` or in the test ids holds a local
  account name, a home path, a hostname or a private address. This report passes `check_paths` (checked before
  hand-off).
