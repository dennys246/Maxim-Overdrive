# Wire integrity review: phase1/ci-cost (f5e9619)

Reviewer: Wire integrity lens, independent. Diff `origin/main...f5e9619`: test.yml and golden.yml triggers narrowed to
`pull_request` and `push: branches: [main]`; test.yml **and drift.yml** (the brief named only test.yml) map
`macos` to self-hosted label `overdrive-mini`; two tests in `tests/test_check_lock.py`.

**Counts: 0 BLOCKER, 4 SHOULD-FIX, 5 NIT.**

## SHOULD-FIX

**WI-S1 `.github/workflows/test.yml::prepush`, `drift.yml::drift` (runs-on `overdrive-mini`): no runner exists yet.**
`gh api repos/.../actions/runners --jq .total_count` returns `0` (verified, today). The commit message says the macOS
jobs "wait in the queue"; GitHub fails a job that waits 24 h for a runner. Failure scenarios: (a) every PR from this
merge on shows two macOS checks pending, then red, so red checks become something to ignore; (b) the Monday drift
run's macOS legs fail without starting, so `Open an issue when the gate fails unpinned` (`if: failure()`, a step in the
same job) never runs, and macOS drift goes unreported. Nothing on the shipped path has shown the runner path works:
`setup-python` on a self-hosted Mac, the `GITHUB_ACTIONS` exemption, `install_godot.sh` there. Fix: register the
runner and get one green PR run of all four test.yml legs before merge, then state the run in the hand-off. Unverified
(owner action).

**WI-S2 `docs/standards_backlog.md::B11`: says test.yml runs the gate "on every push and PR".** Now false for branch
pushes. Failure: a reader trusts a pushed branch with no PR to have a CI result; it has none. Fix: "on pull requests
and pushes to main". Verified the text; no other doc makes the every-push claim about CI (`godot_probes.md:11`, "the
gate holds it on every push", reads as the local gate and stays true).

**WI-S3 The CI exemption's stated reason is now false: `CLAUDE.md` ("only GitHub Actions, whose clone is fresh"),
`scripts/prepush.sh::refuse_main_branch` comment ("runs in a fresh clone"),
`tests/test_prepush.py::test_github_actions_is_exempt_because_its_clone_is_fresh`.** On a self-hosted runner the
workspace persists between jobs. The behaviour is still sound: the exemption needs a checkout that no session shares,
and a runner's `_work` clone is one; `actions/checkout@v4` (default `clean: true`) resets and `git clean -ffdx`s it,
removing `.venv` and `client/.godot`; `RUNNER_TEMP` (Godot and its HOME) is emptied per job. But the runner user's
home (pip cache, setup-python's tool cache, `~/.gitconfig`) persists, and nothing stops the runner's work folder being
put under an existing checkout on the mini, where the owner's sessions also run gates. Failure: someone reasons from
"fresh" (no residue, no neighbours), for example to skip a cleanliness check under `GITHUB_ACTIONS`. Fix: one owner
for the reason (CLAUDE.md's rule; prepush.sh and the test name cite it), reworded to "a checkout dedicated to the
runner, reset by actions/checkout", and a note that the runner's work folder lies outside every checkout. Unverified
where the work folder will live (no runner yet).

**WI-S4 The "remove the self-hosted runner before the repository goes public" obligation has no owner.** It is
stated three times (comments in test.yml and drift.yml, a comment in the new test) and tracked nowhere: no
`docs/standards_backlog.md` row, no roadmap item. CLAUDE.md: a finding with no code to mark becomes a backlog row,
and a contract stated in two places moves to one owner. Failure: the repository is made public (for the Steam page
or open-sourcing the engine half); a fork PR runs arbitrary code on the owner's Mac mini, which sits on the owner's
Tailscale network and, for drift, holds a token with `issues: write`. A YAML comment is not seen when visibility
changes. Fix: one backlog row as the owner, with the trigger "before the repository's visibility changes"; the
workflows cite the row. Unverified. A check is hard offline; the row at least makes the gap visible.

## NIT

- **WI-N1 `drift.yml::drift`, step "Open an issue…":** uses `gh`, which GitHub's images ship and a self-hosted Mac
  may not have on the runner's PATH. Failure: a real drift failure turns red but opens no issue. Unverified; check the
  mini.
- **WI-N2 Stale `macos-latest`:** `ci/install_godot.sh` header ("macos-universal (macos-latest, either CPU)") and
  `docs/design/research/godot_probes.md:158` ("Godot on `ubuntu-latest` and `macos-latest`"). The installer works
  (`Darwin/*` maps to macos-universal); only the text is stale.
- **WI-N3 `tests/test_check_lock.py`:** the trigger and runner tests aren't about the lock; the workflow-shape tests
  are already split between this file and `tests/test_client_project.py`. A third concern in a lock module grows that
  scatter. Not a correctness issue.
- **WI-N4 CI's only PASS line is now a merge commit's.** With push runs gone, CI's prepush runs only on `pull_request`,
  where checkout builds `refs/pull/N/merge`, so its `prepush: PASS <sha>` names the merge commit, never the branch
  head. Nothing relies on CI's sha (the hand-off PASS is local, per CLAUDE.md), but a backlog row flipped "with the
  run's link" (B6) cites a sha that is in no branch. Likewise golden, whose result "counts only on CI (T12)", now runs
  only once a PR exists. That fits the draft-PR practice, but nothing says so.
- **WI-N5 Contention on the mini:** the owner's sessions run gates there, and the runner now does too. The Godot step's
  outer timeouts (B6) were sized on idle machines, so a timeout under load would read as a hang. Unverified.

## What I checked

| Contract | Where | Result |
|---|---|---|
| CI-on-every-push claims | B11, CLAUDE.md, roadmap, prepush.sh, code_review.md, `grep` over md/py/sh/yml | B11 stale (S2); others fine |
| Gate's `GITHUB_ACTIONS` exemption | `prepush.sh::refuse_main_branch`, CLAUDE.md, `test_prepush.py` | sound behaviour, false reason in 3 places (S3) |
| Lock skip events | `check_lock.py::SKIP_EVENTS` = {schedule, workflow_dispatch}; drift.yml triggers unchanged; test.yml events push/pull_request outside the set and test.yml sets no `UNLOCKED` | match |
| Existing workflow tests | `test_check_lock.py` (lockfile per matrix Python, drift skip), `test_client_project.py` (Godot install step, permissions, golden `runs-on: ubuntu-latest`) | still satisfied by the YAML as read |
| Push-only reliance | PR description, hand-off PASS, branch protection | no PR open for this branch; protection unavailable on this private free repository (403), so no required checks to break; merge-sha PASS (N4) |
| Runner existence | `gh api …/actions/runners` | 0 registered (S1) |
| Self-hosted residue | checkout `clean`, `RUNNER_TEMP`, install_godot.sh HOME | reset per job; home-dir caches persist (S3) |
| One owner | runner rationale and removal rule; exemption reason | 3 copies each, no owner (S3, S4) |
| Godot installer on the mini | `ci/install_godot.sh::detect` | Darwin maps to universal; comment stale (N2) |
| Repo visibility | `gh api` | private, which the removal rule depends on (S4) |
