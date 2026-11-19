# Maxim Overdrive

A cyberpunk RPG set in **Maxim Prime**, where every NPC is a [Maxim](https://github.com/dennys246/Maxim) agent with a
life it actually lived.

**Status: foundations.** This repository currently holds the world server: the world as material cells, heat and
damage physics that aim to give the same outcomes at every resolution (with the known exceptions recorded in
`docs/architecture.md`, "Known gaps"), and an SEM bridge that lets Maxim agents perceive and
act on the environment. There is no game client yet.

## What is here

- `world/`: the material grid, scenes authored in metres, heat conduction, damage, the turn loop, render snapshots
- `sem_env/`: walls, doors and objects as Maxim SEM Entities (sensors read cells; modulators change them)
- `imagination/`: imagined objects as validated specs that become ordinary, destructible cells
- `data/`: rig profiles (laptop, rig, max), the material table, and world config (`data/world/`: action limits)
- `docs/architecture.md`: the design and its rules; `docs/book_to_world.md`: the plan for bringing a book to life

## Quick start

```bash
pip install -c constraints/py3.12.txt -e '.[dev,maxim]'   # Python 3.12 or 3.14; match the lockfile
pytest                                   # laptop and rig profiles
MAXIM_OVERDRIVE_ALL_TIERS=1 pytest       # adds the 0.05 m 'max' profile (slow)
```

```python
from maxim_overdrive import Box, RigProfile, Scene, World
from maxim_overdrive.config import ActionLimits
from maxim_overdrive.sem_env.bridge import to_maxim_entity

scene = Scene((3.0, 3.0, 2.0), (Box((1.2, 1.2, 0), (1.8, 1.8, 0.6), "wood", "crate"),))
world = World.from_scene(scene, RigProfile.load("rig"), limits=ActionLimits.load())
crate = to_maxim_entity(world, "crate")            # a real maxim Entity
crate.modulators["structure"].execute("ignite", {"power_w": 60_000})
for _ in range(100):
    world.advance()                                  # one 6-second turn
print(crate.read_all_sensors()["integrity"].value)
```

## License

- **Code:** Apache-2.0 (`LICENSE`).
- **Story, characters, lore, art and audio:** all rights reserved (`ASSETS_LICENSE.md`).
