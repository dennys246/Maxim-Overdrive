# Maxim Overdrive

A cyberpunk RPG set in **Maxim Prime**, where every NPC is a [Maxim](https://github.com/dennys246/Maxim) agent with a
life it actually lived.

**Status: foundations.** This repository currently holds the world server: the world as material cells, heat and
damage physics that aim to give the same outcomes at every resolution (with the known exceptions recorded in
`docs/architecture.md`, "Known gaps"), and an SEM bridge that lets Maxim agents perceive and
act on the environment. There is no game client yet.

## What is here

- `src/simcore/`, the engine: `core/` (the material grid, scenes authored in metres, heat conduction, damage, the
  turn loop, imagined objects as validated specs that become ordinary, destructible cells), `adapters/` (file
  loaders; `sem/`: walls, doors and objects as Maxim SEM Entities) and `protocol/` (rendering tiers, snapshots)
- `src/maxim_overdrive/`, the game: where its data lives
- `data/`: rendering tiers (laptop, rig, max), the material table, and world config (`data/world/`: action limits)
- `docs/architecture.md`: the design and its rules; `docs/book_to_world.md`: the plan for bringing a book to life

## Quick start

```bash
pip install -c constraints/py3.12.txt -e '.[dev,maxim]'   # Python 3.12 or 3.14; match the lockfile
pytest                                   # the 0.2 m and 0.1 m grids
MAXIM_OVERDRIVE_ALL_TIERS=1 pytest       # adds the 0.05 m verification grid (slow)
```

```python
from maxim_overdrive import data
from simcore.adapters.sem.bridge import RegionInstrument
from simcore.core.intents import Ignite, LogRecord
from simcore.core.scene import Box, Scene
from simcore.core.simulation import T3, Simulation

scene = Scene((3.0, 3.0, 2.0), (Box((1.2, 1.2, 0), (1.8, 1.8, 0.6), "wood", "crate"),))
sim = Simulation.from_scene(scene, data.materials(), dx_m=0.1, config=T3, limits=data.action_limits())
fire = Ignite(power_w=60_000.0, radius_m=0.3)
sim.step([LogRecord(apply_tick=1, apply_us=0, actor_id=1, seq=0, kind="ignite", target="crate", params=fire)])
for _ in range(6000):
    sim.step(())                                     # one 0.1 s tick; physics every fifth
print(RegionInstrument(sim.frames, "crate", "integrity").value())  # read from the latest published frame
```

## License

- **Code:** Apache-2.0 (`LICENSE`).
- **Story, characters, lore, art and audio:** all rights reserved (`ASSETS_LICENSE.md`).
