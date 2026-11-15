# CLAUDE.md

Maxim Overdrive is a cyberpunk RPG set in **Maxim Prime**, where every NPC is a [Maxim](https://github.com/dennys246/Maxim)
agent (`pymaxim`) with a life it actually lived. This repo currently holds the **world server**. There is no game
client yet.

Read these first: `docs/architecture.md` (the design and why), `docs/roadmap.md` (phases, exit tests, standing rules)
and `docs/book_to_world.md` (the book-to-world plan).

## Commands

```bash
pip install -e '.[dev,maxim]'          # Python >= 3.10; the [maxim] extra enables real SEM Entities
pytest                                 # laptop + rig profiles, a few seconds
MAXIM_OVERDRIVE_ALL_TIERS=1 pytest     # adds the 0.05 m max profile (about 90 s)
```

## Layout

- `src/maxim_overdrive/config.py`: rig profiles and the material table (`data/rigs/`, `data/materials/`)
- `src/maxim_overdrive/world/`: `grid.py` (cells), `scene.py` (authoring in metres), `heat.py`, `damage.py`,
  `world.py` (turn loop, heat sources, `snapshot`)
- `src/maxim_overdrive/sem_env/bridge.py`: environment regions as Maxim SEM Entities
- `src/maxim_overdrive/imagination/spec.py`: imagined objects as validated specs that become cells
- `docs/maxim_upstream/`: drafts that belong in the Maxim repo (the Exp 64 pre-registration)

## Rules that matter here

- **The resolution rule:** a rig profile may change precision, never the outcome class. Any new physics ships with a
  closed-form test and a cross-tier test (`tests/test_heat.py` and `tests/test_cross_tier.py` are the patterns). If
  a cross-tier test fails, fix the physics; never loosen the test to pass.
- Author scenes in metres. Keep physics parameters per unit volume. Deposit energy by exact cell average or volume
  overlap, never by whether the cell centre is inside.
- Thin features must be at least two cells of the coarsest rig thick.
- The SEM bridge uses Maxim's frozen types (`SensorReading`, `ModulatorResult`, `AffordanceSchema`, `Entity`);
  `sem_env/_compat.py` mirrors them field for field for runs without pymaxim. Don't add fields Maxim doesn't have.
- Imagined objects enter only through `imagination.spec.place`, which validates them. Never write cells directly
  from LLM output.
- Actions change cells; only `World.advance` moves time.
- Record known physics gaps in `docs/architecture.md` ("Known gaps"), with numbers, instead of hiding them.

## Cross-repo work

Changes to Maxim (the Phase 3 line items in `docs/roadmap.md`) go to the Maxim repo and follow its process there: its
own CLAUDE.md, pre-registration, four-lens design review and ledger. Game runs never go on Maxim's results ledger.

## Never commit

The Steamworks SDK (its license forbids redistribution), licensed third-party assets, or `.env` files. Code is
Apache-2.0; story, characters, lore, art and audio are all rights reserved (`ASSETS_LICENSE.md`).
