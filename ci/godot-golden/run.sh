#!/usr/bin/env bash
# Render the renderer goldens on llvmpipe under Xvfb and compare them with the committed ones (client_rendering.md
# §6.5). It runs inside the golden image, with the repository mounted read-only at /repo:
#
#   docker build --platform linux/amd64 -f ci/godot-golden/Dockerfile -t overdrive-golden .
#   docker run --rm --platform linux/amd64 -v "$PWD:/repo:ro" -v "$out:/out" overdrive-golden ci/godot-golden/run.sh /out
#
# Godot's exit status is not trusted on its own: the log is scanned for errors, and the compare reads the renderer's
# name from the log to pick the golden directory and to refuse anything but 256-bit llvmpipe.
set -euo pipefail

out="${1:?usage: $0 <out dir>}"
work="$(mktemp -d)"
cp -R client "$work/client"
rm -rf "$work/client/.godot"

grep -m1 "model name" /proc/cpuinfo || true  # which CPU drew it: GitHub's pool mixes Intel and AMD (CR-B3)
status=0
# Xvfb is an X server that draws into memory: Godot's Linux build has no surfaceless GL mode, so it needs a display.
timeout 120 xvfb-run -a -s "-screen 0 1280x720x24" \
  godot --audio-driver Dummy --rendering-driver opengl3 --rendering-method gl_compatibility --fixed-fps 60 --resolution 1280x720 \
  --path "$work/client" res://tests/golden.tscn -- --out="$out/boxes.png" >"$out/golden.log" 2>&1 || status=$?
cat "$out/golden.log"
[ "$status" -eq 0 ] || { echo "golden: Godot exited $status" >&2; exit 1; }
if grep -E "SCRIPT ERROR|Parse Error|ERROR:" "$out/golden.log" >&2; then
  echo "golden: Godot printed an error" >&2
  exit 1
fi
python3 scripts/golden_compare.py --log "$out/golden.log" --actual "$out/boxes.png" \
  --goldens client/tests/goldens --name rig/boxes.png --diff "$out/boxes.diff.png"
