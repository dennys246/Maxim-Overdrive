#!/usr/bin/env bash
# The pre-push gate (CLAUDE.md, "Engineering standards"). Only `prepush: PASS` clears a branch for push.
# It runs every tier (the resolution rule is a cross-tier claim), so expect about a minute.
#
#   scripts/prepush.sh              # against main
#   BASE=origin/main scripts/prepush.sh
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
BASE="${BASE:-main}"
PY="${PYTHON:-.venv/bin/python}"
[ -x "$PY" ] || PY="python3"

step() { printf '\n== %s\n' "$*"; }

step "ruff lint"
"$PY" -m ruff check src tests scripts
step "ruff format"
"$PY" -m ruff format --check src tests scripts
step "mypy (strict on src)"
"$PY" -m mypy
step "standards lint (TEMPORARY markers, guard citations)"
"$PY" scripts/lint_standards.py

step "tests, every tier, with branch coverage (floor in pyproject.toml)"
rm -f .coverage coverage.xml
MAXIM_OVERDRIVE_ALL_TIERS=1 "$PY" -m pytest -q -p no:cacheprovider \
  --cov --cov-report=term --cov-report=xml:coverage.xml

step "diff coverage: lines changed since $(git merge-base "$BASE" HEAD | cut -c1-8) ($BASE) must be >= 95% covered"
"$PY" -m diff_cover.diff_cover_tool coverage.xml --compare-branch="$BASE" --fail-under=95

if [ -d client ]; then
  step "Godot client checks"
  echo "client/ exists but its checks are not wired yet (docs/standards_backlog.md B6)" >&2
  exit 1
fi

printf '\nprepush: PASS\n'
