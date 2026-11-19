#!/usr/bin/env bash
# The pre-push gate (CLAUDE.md, "Engineering standards"). Only `prepush: PASS <sha>` on a clean tree clears that
# commit for hand-off. It runs every tier (the resolution rule is a cross-tier claim), so expect about a minute.
#
#   scripts/prepush.sh                       # base: main if it exists, else origin/main
#   BASE=origin/main scripts/prepush.sh
#   PYTHON=/path/to/venv/bin/python scripts/prepush.sh   # e.g. from a worktree without its own .venv
#   ALLOW_DIRTY=1 scripts/prepush.sh         # check work in progress; the result does not clear a hand-off
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

die() { printf 'prepush: FAIL: %s\n' "$*" >&2; exit 1; }
step() { printf '\n== %s\n' "$*"; }

# -- preconditions, all checked before a minute of tests ------------------------------------------------------------

# Other agents may be working in this repository right now (CLAUDE.md, "Assume other agents are working"). Work happens
# on a branch in its own worktree under .worktrees/; the main checkout and main itself are the owner's. GitHub Actions
# runs in a fresh clone where no other session exists, so it is exempt, and the PASS line says the check was skipped.
SKIPPED=""
refuse_main_branch() {
  if [ "${GITHUB_ACTIONS:-}" = "true" ]; then
    SKIPPED=" (isolation check skipped: GitHub Actions)"
    return 0
  fi
  local branch git_dir common_dir
  branch="$(git symbolic-ref -q --short HEAD || true)"
  case "$branch" in
    main | master) die "HEAD is on $branch; work on a phaseN/<step> branch in its own worktree (git worktree add .worktrees/<name> -b phaseN/<step>)" ;;
  esac
  git_dir="$(cd "$(git rev-parse --git-dir)" && pwd -P)"
  common_dir="$(cd "$(git rev-parse --git-common-dir)" && pwd -P)"
  if [ "$git_dir" = "$common_dir" ]; then
    die "this is the main checkout, which is the owner's; run the gate from your worktree under .worktrees/"
  fi
}
refuse_main_branch

PY="${PYTHON:-.venv/bin/python}"
command -v "$PY" >/dev/null 2>&1 || die "no Python at '$PY'; create .venv (CLAUDE.md, Commands) or set PYTHON"
if ! "$PY" -c 'import maxim, ruff, mypy, diff_cover, pytest_cov' 2>/dev/null; then
  PYV="$("$PY" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || echo '<major.minor>')"
  # An editable install points the venv at one checkout, so installing into a venv another worktree shares re-points
  # it for every session. Only a venv inside this worktree is this session's to install into.
  case "$(cd "$(dirname "$PY")" && pwd -P)" in
    "$(pwd -P)"/*) die "'$PY' lacks the gate's tools; install with: $PY -m pip install -c constraints/py$PYV.txt -e '.[dev,maxim]'" ;;
    *) die "'$PY' lacks the gate's tools, and it is shared with other worktrees: don't install into it; make this worktree its own venv (python3.12 -m venv .venv && .venv/bin/pip install -c constraints/py3.12.txt -e '.[dev,maxim]')" ;;
  esac
fi

if [ -z "${BASE:-}" ]; then
  if git rev-parse --verify -q main >/dev/null; then BASE=main; else BASE=origin/main; fi
fi
git rev-parse --verify -q "$BASE" >/dev/null || die "base '$BASE' is not a git ref (fetch it, or set BASE)"
MERGE_BASE="$(git merge-base "$BASE" HEAD)" || die "no merge base between $BASE and HEAD"

DIRTY="$(git status --porcelain)"
if [ -n "$DIRTY" ] && [ -z "${ALLOW_DIRTY:-}" ]; then
  printf '%s\n' "$DIRTY" >&2
  die "the tree has uncommitted changes, so a PASS would not describe HEAD (commit them, or ALLOW_DIRTY=1)"
fi

if [ -d client ]; then
  die "client/ exists but its Godot checks are not wired into this gate yet (docs/standards_backlog.md B6)"
fi

# -- the gate -------------------------------------------------------------------------------------------------------

step "dependencies match the lockfile (O32)"
"$PY" scripts/check_lock.py
if [ "${MAXIM_OVERDRIVE_UNLOCKED:-}" = "1" ]; then SKIPPED="$SKIPPED (lock check skipped: the drift job)"; fi
step "ruff lint"
"$PY" -m ruff check src tests scripts
step "ruff format"
"$PY" -m ruff format --check src tests scripts
step "mypy (strict on src and scripts; test bodies checked)"
"$PY" -m mypy
step "standards lint (TEMPORARY markers, pragmas, guard citations, size limits, coverage and size ratchets against $BASE)"
"$PY" scripts/lint_standards.py --base "$BASE"

step "tests, every tier, with branch coverage (floor in pyproject.toml)"
rm -f .coverage coverage.xml
MAXIM_OVERDRIVE_ALL_TIERS=1 "$PY" -m pytest -q -p no:cacheprovider \
  --cov --cov-report=term --cov-report=xml:coverage.xml

step "diff coverage: lines changed since ${MERGE_BASE:0:8} ($BASE) must be >= 95% covered"
"$PY" -m diff_cover.diff_cover_tool coverage.xml --compare-branch="$BASE" --fail-under=95

HEAD_SHA="$(git rev-parse --short=12 HEAD)"
# A step that wrote into the tree (a test leaving files behind) would make the PASS describe a different tree.
if [ "$(git status --porcelain)" != "$DIRTY" ]; then
  git status --porcelain >&2
  die "the gate changed the working tree while it ran; fix the step that writes there"
fi
if [ -n "$DIRTY" ]; then
  printf '\nprepush: PASS on a dirty tree (HEAD %s plus uncommitted changes); this does not clear a hand-off\n' "$HEAD_SHA"
else
  printf '\nprepush: PASS %s%s\n' "$HEAD_SHA" "$SKIPPED"
fi
