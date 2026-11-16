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

PY="${PYTHON:-.venv/bin/python}"
command -v "$PY" >/dev/null 2>&1 || die "no Python at '$PY'; create .venv (CLAUDE.md, Commands) or set PYTHON"
"$PY" -c 'import maxim, ruff, mypy, diff_cover, pytest_cov' 2>/dev/null \
  || die "'$PY' lacks the gate's tools; install with: $PY -m pip install -e '.[dev,maxim]'"

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

step "ruff lint"
"$PY" -m ruff check src tests scripts
step "ruff format"
"$PY" -m ruff format --check src tests scripts
step "mypy (strict on src and scripts; test bodies checked)"
"$PY" -m mypy
step "standards lint (TEMPORARY markers, pragmas, guard citations, coverage ratchet against $BASE)"
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
  printf '\nprepush: PASS %s\n' "$HEAD_SHA"
fi
