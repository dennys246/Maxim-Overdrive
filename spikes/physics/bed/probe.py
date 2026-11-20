"""Short diagnostic probe: print the early evolution at one grid (spike)."""

import sys
import time

import sim
from constants import NOMINAL

dx = float(sys.argv[1])
t_end = float(sys.argv[2])
d_ticks = int(sys.argv[3])
kw = dict(a.split("=") for a in sys.argv[4:])
p = NOMINAL.with_(
    **{
        k: (type(getattr(NOMINAL, k))(v) if not isinstance(getattr(NOMINAL, k), bool) else v == "1")
        for k, v in kw.items()
    }
)
t = time.time()
r = sim.run(p, dx, d_ticks, t_end=t_end)
o = sim.observables(r, p)
print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in o.items()})
for i in range(0, len(r["t"]), int(50 / p.dt_phys)):
    print(
        r["t"][i],
        round(r["a_flaming"][i], 3),
        round(r["a_ignited"][i], 3),
        round(r["fuel"][i], 2),
        round(r["t_layer_max"][i]),
        round(r["glow_area"][i], 3),
        round(r["ember_mean"][i], 1),
        round(r["draught_kgs"][i], 3),
    )
print("wall", time.time() - t)
