#!/bin/bash
# Run every fit (§4) as its own single-threaded process, 4 at a time; each writes out/fit/<name>_s<seed>.json and a
# log in out/fit/ as it goes.
cd "$(dirname "$0")"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 MKL_NUM_THREADS=1
PY=${PYTHON:-../../../.venv/bin/python}  # the running worktree's own venv
mkdir -p out/fit
printf '%s\n' "pine 0" "pine 1" "pine 2" "pine 3" "pine 4" "pmma_forward 0" "pmma_reverse 0" "pmma_forward 1" \
  "pmma_reverse 1" "pmma_forward 2" "pmma_reverse 2" "pmma_forward 3" "pmma_reverse 3" "pmma_forward 4" \
  "pmma_reverse 4" "pine_aalto_fzj 0" |
  xargs -P 4 -L 1 sh -c '"$0" fit.py "$1" "$2" > "out/fit/log_$1_s$2.txt" 2>&1' "$PY"
