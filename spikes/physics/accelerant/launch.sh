#!/bin/bash
# Run every line of a queue file as `acc_run.py <line>`, 4 at a time, single-threaded BLAS, bed/ on the path.
cd "$(dirname "$0")"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONPATH=../bed
xargs -P 4 -L 1 sh -c '../../../.venv/bin/python acc_run.py "$@" > results/log_$1.txt 2>&1' _ < "${1:-queue.txt}"
