#!/bin/bash
# Rerun 1's fits (preregistration_rerun1.md §4 gate 2): every seed at each material's r* from out_rerun1/gate1.json,
# only for materials that passed gate 1; each a single-threaded process, 4 at a time, writing
# out_rerun1/fit/<name>_s<seed>.json and its log as it goes. Then N8's reruns of the PMMA seed-0 fits into
# out_rerun1/fit_rerun/, compared with the originals (timings excluded).
set -euo pipefail
cd "$(dirname "$0")"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 MKL_NUM_THREADS=1
PY=${PYTHON:-../../../.venv/bin/python}  # the running worktree's own venv
mkdir -p out_rerun1/fit out_rerun1/fit_rerun
export SOLID_FIT_OUT=out_rerun1/fit  # never the first run's out/fit
jobs=$("$PY" -c '
import json
g = json.load(open("out_rerun1/gate1.json"))
for m, names in (("pine", ("pine",)), ("pmma", ("pmma_forward", "pmma_reverse"))):
    if g["pass"][m]:
        for s in range(5):
            for n in names:
                print(n, s, g["r_star"][m])
if g["pass"]["pine"]:
    print("pine_aalto_fzj", 0, g["r_star"]["pine"])
')
echo "$jobs" | xargs -P 4 -L 1 sh -c '"$0" fit.py "$1" "$2" "$3" > "out_rerun1/fit/log_$1_s$2.txt" 2>&1' "$PY"
echo "$jobs" | grep '^pmma_[a-z]* 0 ' | xargs -P 2 -L 1 sh -c \
  'SOLID_FIT_OUT=out_rerun1/fit_rerun "$0" fit.py "$1" "$2" "$3" > "out_rerun1/fit_rerun/log_$1_s$2.txt" 2>&1' "$PY" || true
"$PY" -c '
import json, pathlib
for p in sorted(pathlib.Path("out_rerun1/fit_rerun").glob("*.json")):
    a = json.loads(p.read_text()); b = json.loads((pathlib.Path("out_rerun1/fit") / p.name).read_text())
    a.pop("timing_reported_only"); b.pop("timing_reported_only")
    print(f"N8 fit rerun {p.stem}: identical {a == b}")
' | tee out_rerun1/fit_rerun/compare.txt
