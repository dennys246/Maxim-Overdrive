#!/usr/bin/env bash
# The golden job inside the golden image (client_rendering.md §6.5), with the repository mounted read-only at /repo:
#
#   docker build --platform linux/amd64 -f ci/godot-golden/Dockerfile -t overdrive-golden .
#   docker run --rm --platform linux/amd64 -v "$PWD:/repo:ro" -v "$out:/out" overdrive-golden ci/godot-golden/run.sh /out
#
# scripts/golden_run.py does the work: a fresh import, each golden scene under Xvfb, and the judgement, with the gate's
# own timeout and output scans (scripts/godot_check.py). This wrapper only names the CPU and the output directory.
set -euo pipefail

out="${1:?usage: $0 <out dir>}"
grep -m1 "model name" /proc/cpuinfo || true  # which CPU drew it: GitHub's pool mixes Intel and AMD (CR-B3)
exec python3 scripts/golden_run.py --godot godot --out "$out"
