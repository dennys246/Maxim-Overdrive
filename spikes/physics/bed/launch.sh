#!/bin/bash
# Run every line of queue.txt as `run.py <line>`, 6 at a time, single-threaded BLAS.
cd "$(dirname "$0")"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 MKL_NUM_THREADS=1
xargs -P 6 -L 1 sh -c '../../../.venv/bin/python run.py "$@" > results/log_$1.txt 2>&1' _ < "${1:-queue.txt}"
