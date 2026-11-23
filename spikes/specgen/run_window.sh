#!/usr/bin/env bash
# Run one model's cells of the spec generator spike inside the nightly window (owner, 2026-11-22: 22:00 to 08:00 on
# the Mac mini), then stop. Throwaway spike code, run on the mini from its own worktree. Safe to rerun: generate.py
# resumes (and repairs a torn last line), so the next night picks up where this one stopped. Launched outside the
# window, it waits for the window to open.
#
#   spikes/specgen/run_window.sh <S|R> <runs-dir> [start-hour] [stop-hour]
#
# llama-server binds to the mini's Tailscale address (arms.yaml's engine block), looked up here and never written to
# any file. The weights' SHA-256 is measured here and checked by generate.py against freeze.sha256. The window's end
# sends SIGTERM to the generator, then the EXIT trap stops the server.
set -euo pipefail

model=$1
runs=$2
start_hour=${3:-22}
stop_hour=${4:-8}
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../.." && pwd)
py="$root/.venv/bin/python"
models="$HOME/overdrive-gate/specgen-spike-models"
case $model in
  S) gguf="$models/s4b/Qwen3.5-4B-Q8_0.gguf" ;;
  R) gguf="$models/r27b/Qwen3.5-27B-Q8_0.gguf" ;;
  *) echo "model must be S or R" >&2; exit 2 ;;
esac
mkdir -p "$runs"

in_window() {  # start_hour inclusive to stop_hour exclusive; it crosses midnight when start_hour > stop_hour
  local h
  h=$((10#$(date +%H)))
  if [ "$start_hour" -gt "$stop_hour" ]; then
    [ "$h" -ge "$start_hour" ] || [ "$h" -lt "$stop_hour" ]
  else
    [ "$h" -ge "$start_hour" ] && [ "$h" -lt "$stop_hour" ]
  fi
}

until in_window; do sleep 60; done
echo "window open: $(date +%Y-%m-%dT%H:%M)"

weights=$(shasum -a 256 "$gguf" | cut -d' ' -f1)
host=$(tailscale ip -4 | head -n 1)
[ -n "$host" ] || { echo "no Tailscale address" >&2; exit 2; }
port=$("$py" -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])')

# The frozen flags (arms.yaml engine.server_flags), with the host filled in here. The server prints its listening
# address and the model's full path, so its log is filtered: the address and the home directory never reach a file.
host_re=$(printf '%s' "$host" | sed 's/[.]/[.]/g')
mask() { sed -u -e "s/${host_re}/<host>/g" -e "s#${HOME}#<home>#g"; }
llama-server -m "$gguf" --host "$host" --port "$port" --jinja -ngl 999 -c 16384 --parallel 1 \
  > >(mask > "$runs/server-$model.log") 2>&1 &
server=$!
trap 'kill "$server" 2>/dev/null || true' EXIT
ready=0
for _ in $(seq 600); do
  if curl -sf "http://$host:$port/health" | grep -q ok; then ready=1; break; fi
  kill -0 "$server" 2>/dev/null || { echo "llama-server exited; see $runs/server-$model.log" >&2; exit 2; }
  sleep 1
done
[ "$ready" = 1 ] || { echo "llama-server never became ready" >&2; exit 2; }

for split in dev heldout; do
  for arm in A0 A1 A2 A3; do
    in_window || { echo "window closed before $model $arm $split"; exit 0; }
    "$py" "$here/generate.py" --endpoint "http://$host:$port" --model "$model" --arm "$arm" --split "$split" \
      --weights-sha256 "$weights" --machine mini --out "$runs/$model-$arm-$split.jsonl" &
    gen=$!
    while kill -0 "$gen" 2>/dev/null; do
      if ! in_window; then
        kill -TERM "$gen"
        wait "$gen" || true
        echo "window closed during $model $arm $split"
        exit 0
      fi
      sleep 30
    done
    wait "$gen" || { rc=$?; echo "generate.py stopped ($rc) in $model $arm $split; nothing later runs" >&2; exit "$rc"; }
  done
done
echo "all cells of $model done: $(date +%Y-%m-%dT%H:%M)"
