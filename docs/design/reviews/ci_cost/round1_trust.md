# Trust boundary review: phase1/ci-cost (f5e9619)

Reviewer: Trust boundary lens, independent, read-only. Diff: `git diff origin/main...f5e9619` (test.yml, drift.yml,
golden.yml, tests/test_check_lock.py).

**Evidence labels.** "Measured" means I ran it in this session. "Docs (recalled)" means GitHub's documented behaviour
as I know it. I did not fetch the docs this session, so the owner should confirm those items on the pages named.
"Unverified" means it is my reasoning or depends on the mini's actual setup, which I did not inspect: I made no SSH
connection.

## Summary

The change itself is small and correct: a matrix `include` maps `macos` to the label `overdrive-mini`. The risk is in
what it leaves unsaid. The branch sends arbitrary repository code, plus the newest unpinned PyPI releases every week,
to a persistent machine the owner uses for other work. It says nothing about which account the runner runs as, how it
is isolated, or how the workspace is cleaned. Its only "before public" safeguard is a YAML comment.

Findings: **2 BLOCKER, 4 SHOULD-FIX, 3 NIT.**

## Who can run code on the mini

- **Any writer, through any workflow, on any branch.** The label is open to every workflow file in the repository.
  The `pull_request` event runs the workflow file from the PR's merge commit, so a PR can change `runs-on`, add
  steps, or delete any guard written in the YAML (Docs, recalled: "Events that trigger workflows", pull_request,
  GITHUB_SHA is the merge commit). `workflow_dispatch` on drift.yml also lets any writer run any branch's version of
  that file on the mini, with `issues: write`. The comment's phrase "any PR's code" understates this: a plain branch
  push with an `on: push` workflow is enough.
- **Today the writers are the owner and the owner's agent sessions.** The sessions already run gates on the mini over
  SSH, so they are not a new exposure. Collaborators added later, a GitHub App, and Dependabot (not configured today:
  `.github/` holds only `workflows/`) would be.
- **Forks of a private repo.** Fork PR workflows on private repos are off by default and governed by the "Fork pull
  request workflows in private repositories" setting (Docs, recalled: "Managing GitHub Actions settings for a
  repository"). Unverified: whether a personal-account repo shows that setting. The owner should check Settings >
  Actions > General.
- **Once public**, any GitHub user can fork and open a PR. Only a first-time contributor's run waits for approval
  (Docs, recalled). GitHub's own advice is to use self-hosted runners only with private repositories (Docs, recalled:
  "Security hardening for GitHub Actions", self-hosted runners).

## What a job can reach

The runner app runs jobs as the account that started it, with no sandbox (Docs, recalled). If that account is
`dennys`, every job can reach the following:

- the owner's whole home: `~/.ssh`, `~/overdrive-gate` (other branches' worktrees, the Godot binary), and the Ollama
  models and data;
- credentials that macOS releases without a prompt, because the job calls the tool the keychain item belongs to.
  For example, `git credential fill` goes through `osxkeychain`, and `gh auth token` reads the CLI's token. Either
  yields the owner's personal GitHub credential, which reaches every repo, Maxim included. Unverified: whether such
  items exist on the mini;
- persistence: a LaunchAgent in `~/Library/LaunchAgents`, or edits to shell rc files;
- the tailnet: every device of the owner's that Tailscale ACLs allow. If the mini holds a key the main Mac accepts,
  that includes the main Mac, which holds the signing key. Unverified: the memory notes mention SSH in both
  directions.

## Findings

### BLOCKER 1: `drift.yml::drift`, unpinned releases on the owner's machine

`pip install --upgrade -e '.[dev,maxim]'` installs the newest release of every transitive dependency, then imports
and runs it under the gate. On `macos-latest` a compromised release ran in a throwaway VM. On the mini it runs as the
runner account on a machine that persists.

Failure scenario: a maintainer account is compromised. This class of attack is real: ultralytics 8.3.41 on PyPI,
December 2024, shipped a miner. A dependency of numpy, pytest or hypothesis publishes a release that drops a
LaunchAgent and reads `~/.ssh` and the gh token. It runs within a week, unattended, at 06:17 UTC on a Monday.

Mitigation, choose one:
- (a) Keep drift's macOS leg on `macos-latest`. It is a weekly job with two legs, so its cost is bounded.
- (b) Run it on the mini only under a dedicated non-admin account with an ephemeral runner (SHOULD-FIX 1 and 2).

Under the owner's own account, (a) is the only safe option.

### BLOCKER 2: `test.yml` / `drift.yml` header comment, "remove before public" is only a comment

CLAUDE.md says "A document is not a check": a rule held only by attention needs a backlog row. This rule has neither
a check nor a backlog row, and `docs/roadmap.md` doesn't mention it (`grep public` finds only an unrelated line). The
failure is catastrophic and depends on memory. The repo goes public months from now, a fork PR edits `test.yml` to
run anything, and it runs on the mini.

A guard inside the workflow, such as `if: github.event.repository.private`, does not fix this. The PR controls the
workflow file and can delete the guard. Mitigations, in order of strength:

1. **A runner-side pre-job hook (the real control).** Set `ACTIONS_RUNNER_HOOK_JOB_STARTED=/path/check.sh` in the
   runner's `.env` (Docs, recalled: "Running scripts before or after a job"). The script lives on the mini, outside
   any PR's reach. It reads `$GITHUB_EVENT_PATH` and exits non-zero unless `.repository.private == true` and, for
   `pull_request`, `.pull_request.head.repo.full_name == .repository.full_name`. Unverified: whether the `schedule`
   payload carries `repository`. If it doesn't, allow `schedule` explicitly, since schedules run only the default
   branch's file.
2. **A workflow step that catches the owner's own forgetting.** Make it the first step, before checkout, so no PR
   code has run yet:
   `[ "$(gh api repos/$GITHUB_REPOSITORY --jq .private)" = true ] || exit 1`, with `GH_TOKEN` set. Reading repo
   metadata needs only `contents: read`. Unverified: that this holds for every event. Calling the API avoids
   depending on the event payload. A test can pin that the step is present, like the existing matrix test.
3. **A roadmap item and a backlog row:** "deregister the runner (Settings > Actions > Runners) before visibility
   changes". The hook and the step only fail jobs; deregistering the runner is the actual removal.

### SHOULD-FIX 1: persistent workspace, toolcache and caches (registration, not yet in the repo)

`actions/checkout` with `clean: true` runs `git clean -ffdx && git reset --hard` on the existing repo (Docs,
recalled). That leaves `.git/config` and `.git/hooks` alone. Failure scenario: a PR writes `core.fsmonitor =
<payload>` into the workspace's `.git/config`. The next push-to-main job runs it during checkout, so main's macOS PASS
is forged, or a later job's token is stolen. The reasoning is mine (unverified), but the mechanism is the documented
behaviour of fsmonitor and hooks.

The same kind of persistence lives in:
- `_work/_tool`: setup-python's Python can be replaced for every later run;
- `~/Library/Caches/pip`: the wheel cache, shared with the owner's own gates if the account is the same.

The lockfiles carry no hashes (measured: `grep -c -- --hash constraints/*.txt` gives 0), so a poisoned cached wheel
is accepted. `RUNNER_TEMP`, where Godot is installed, is emptied for each job (Docs, recalled), so Godot is fine.

Mitigation: register with `./config.sh --ephemeral` (one job, then the runner deregisters), or use JIT configs
(`POST /repos/{owner}/{repo}/actions/runners/generate-jitconfig`) (Docs, recalled). Re-registering after each job
needs a wrapper loop and a token with admin rights on the repo, kept on the mini. That token is a secret worth
scoping: a fine-grained PAT, this repo only, Administration: write. If ephemeral is rejected, the pre-job hook from
BLOCKER 2 should instead `rm -rf` the `_work/<repo>` directory and point `PIP_CACHE_DIR` at `$RUNNER_TEMP`.

### SHOULD-FIX 2: run as a dedicated standard account (registration)

Create a non-admin user such as `runner`, with no sudo and no keychain items, and keep the owner's GitHub, SSH and
Tailscale credentials out of it. A second account is not automatically walled off. On this Mac, `ls -led ~` gives
`drwxr-x---+ <owner> staff` and `~/Scripts` is `drwxr-xr-x` (measured). Every standard user is in `staff`, so a
runner account could traverse the owner's home and read anything created with umask 022, such as `~/overdrive-gate`.
On the mini, run `chmod 700 ~` for the owner, then check (unverified there).

`./svc.sh install` on macOS installs a LaunchAgent for the configuring user, which runs only while that user is
logged in (Docs, recalled). A dedicated account therefore needs auto-login, or a LaunchDaemon with a `UserName` key.
Unverified: that Godot runs headless without a GUI session. Finally, set a Tailscale ACL so the mini cannot reach the
main Mac on port 22.

### SHOULD-FIX 3: `drift.yml::drift.permissions` and `actions/checkout`, the token sits on the runner

The whole job holds `issues: write`, and checkout keeps the token in `.git/config` for the length of the job
(`persist-credentials` defaults to true; Docs, recalled). Code from an unpinned package can read it and open, edit or
close issues as `github-actions`.

Mitigations:
- Move the issue step into a separate `ubuntu-latest` job with `needs: drift` and `if: failure()`, and give the mini
  job `contents: read` only.
- Set `persist-credentials: false` in both workflows. The gate never fetches (measured: `scripts/prepush.sh` line 100
  says so), and `fetch-depth: 0` already brings in `origin/main`.

### SHOULD-FIX 4: `scripts/prepush.sh::refuse_main_branch`, the exemption's premise is now false

The comment (lines 19–20) and CLAUDE.md both say "GitHub Actions runs in a fresh clone where no other session exists,
so it is exempt." On the mini's runner, neither half holds: the clone persists, and the owner's own gates and
playtests share the machine. The skip still works in practice, because the runner's `_work` directory is not a
session's worktree. Two changes fix the premise:
- Reword the comment and CLAUDE.md to describe the real condition: a runner workspace that no session uses.
- Require that the runner's work directory sits outside `~/overdrive-gate`.

`RUNNER_ENVIRONMENT` (`github-hosted` or `self-hosted`; Docs, recalled) could put the distinction in the PASS line.

### NIT 1: `test.yml::prepush.runs-on`, a lone custom label

Prefer `[self-hosted, macOS, ARM64, overdrive-mini]`. The first three are the runner's default labels (Docs,
recalled). With them in the list, the intent is explicit, and only a self-hosted Mac can ever match.

### NIT 2: `tests/test_check_lock.py::test_macos_runs_on_the_owners_self_hosted_runner_and_linux_on_githubs`

This test locks in the risky mapping. When the repo goes public, the test has to be inverted, not just deleted, so
that it asserts no self-hosted label. Name that in the roadmap item from BLOCKER 2.

### NIT 3: `setup-python` on self-hosted macOS (functional)

Unverified, recalled from setup-python's advanced-usage doc: the prebuilt macOS Pythons expect the toolcache at
`/Users/runner/hostedtoolcache`, so set `AGENT_TOOLSDIRECTORY` to it. Naming the dedicated account `runner` makes that
the natural path.

## Owner checklist for registering the runner

1. Create a dedicated standard user, not an admin, and run `chmod 700` on the owner's home.
2. Register at repo scope with `--ephemeral` (or JIT) and the label `overdrive-mini`. Put the work directory in the
   runner user's home.
3. Install the job-started hook (BLOCKER 2.1).
4. Start the runner as a LaunchDaemon with `UserName=runner`, or use auto-login plus `svc.sh`.
5. Confirm in Settings > Actions > General that fork PR workflows are off.
6. Restrict the mini in Tailscale ACLs.
7. Deregister the runner before any change to the repo's visibility.
