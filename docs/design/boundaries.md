# Boundaries between engine, game, Maxim and the outside world (design, 2026-11-16)

**Status:** DRAFT, for a design review before any code. The owner decided on 2026-11-16 to keep one repository and
design the engine and game split now, with a trigger for splitting into two repositories later. This document
proposes the boundaries the codebase enforces from here, how each is checked, and when each lands.

## Why now

Each boundary costs a line of configuration and a few renames today. The same boundary after the protocol, zones,
fuel and the lab exist costs a refactor across all of them. The state on `phase1/act-validation` at 2f200b5, surveyed
for this document:

- `src/maxim_overdrive/` has five parts: `checks.py`, `config.py`, `world/` (grid, scene, heat, damage, world),
  `imagination/` (spec) and `sem_env/` (bridge, `_compat`).
- **Only `sem_env/` imports `maxim`.** Boundary 2 already holds; it only needs locking in.
- **No module under `src/` imports `time`, `random`, `datetime`, `uuid` or `os`.** Boundary 3 holds today by
  attention; `tests/test_determinism.py`'s AST scan checks part of it.
- **No game content exists yet.** Every module is engine-like. `data/` holds rigs, the material table (physical
  properties mixed with gameplay calibrations such as `degrade_*`), and action limits.

## The boundaries

### B-1. Engine and game

- **Rule:** the engine never imports the game. The game may import the engine.
- **Packages:**
  - The engine is a new top-level package, proposed name `maxim_world` (open question Q1), holding everything in
    `src/maxim_overdrive/` today.
  - `maxim_overdrive` becomes the game package, empty at first, and later the home of the lab, its scenarios, NPC
    authoring and the game's server entry point.
- **What belongs where:**
  - **Engine:** cells and fields, physics, scenes as a format and its loader, imagination's validated specs,
    actions and their limits as a mechanism, the SEM membrane, the protocol, formats, the simulation and host, the
    verification harness.
  - **Game:** this game's content and rules: the lab tile, its scenes and rooms, story, NPC rosters and cradle
    arcs, gameplay tuning, the Godot game client's content.
- **Revisit trigger:** split into two repositories when a second game or an outside developer wants the engine, or
  at the Phase 1 exit, whichever comes first.

### B-2. Maxim only through the SEM membrane

- **Rule:** only `maxim_world.sem_env` imports `maxim`. Everything else reaches Maxim through it.
- **Why:**
  - Maxim's releases, its frozen types and the Phase 3 proposals land in one place.
  - The `_compat` mirror and its drift test already assume this.
  - A future agent framework, or a newer Maxim, is a swap of one package.

### B-3. The simulation is sealed

- **Rule:** the deterministic core never imports the outside world. The core is `maxim_world.world` today, and later
  the `Simulation`, physics, zones and the field registry. The forbidden modules:
  - the host, transport and thinking lane;
  - `time`, `datetime`, `random`, `secrets`, `uuid`, `os.urandom`;
  - `threading`, `asyncio`, `socket`, `websockets`;
  - `maxim` itself.
- **Why:** determinism, replays and the one-truth decision rest on it. A stray import should fail the lint, not a
  replay weeks later. The forbidden-imports contract is checked statically. The per-thread `sys.setprofile`
  tripwire (`world_model.md` §6) remains for what imports can't show, such as an unseeded `random.Random` built
  inside Maxim.

### B-4. Untrusted input crosses at named gates

- **Rule:** values from outside enter only through named gates. Inside a gate, code takes typed, frozen objects,
  never raw mappings.
- **The gates:**
  - Today: `sem_env.bridge.parse_action`, `imagination.spec.place`, and the loaders (`RigProfile.load`,
    `MaterialTable.load`, `ActionLimits.load`, `Scene.from_dict`).
  - Later: the protocol decoder, and the save, scene-v1 and intent-log loaders.
- **Why:** PR 1 built the first gate and found its edge cases one by one. Listing the gates makes "there are no other
  doors" checkable.

### B-5. Content and licence

- **Rule:** rights-reserved content lives under `content/`. Engine code and engine data live elsewhere and are
  Apache-2.0.
- **The material table** is split when material table v1 is written:
  - physical properties (density, heat capacity, conductivity, transition points, latent heats) are engine data;
  - gameplay calibrations (fracture energy, degradation, combustion tuning) are content.
- **The asset manifest** (backlog B8) lists what is under `content/`.

### B-6. Presentation stays out of physics (when the protocol lands)

- **Rule:** physics computes nothing only the renderer needs. Quantizing for display (`world.snapshot`'s `crack`,
  `glow` and uint8 scaling) moves to an encoding layer beside the protocol.

### B-7. Experiments stay out of the game (when the first experiment is built)

- **Rule:** Maxim's pre-registered experiments run in a harness package that the game never imports. Game runs stay
  off Maxim's results ledger unless pre-registered (an existing rule).

## Enforcement

| Boundary | Check | Lands |
|---|---|---|
| B-1 engine and game | `import-linter` contract: `maxim_world` is forbidden from importing `maxim_overdrive` | `phase1/boundaries` |
| B-2 Maxim membrane | `import-linter` contract: only `maxim_world.sem_env` may import `maxim` | `phase1/boundaries` |
| B-3 sealed simulation | `import-linter` forbidden contract on the core (the list above); the AST scan stays for calls and names imports can't show | `phase1/boundaries` |
| B-4 named gates | a list of gates in `lint_standards.py`, plus a rule that every public function taking a `Mapping` or `object` parameter is a listed gate or its private helper | `phase1/boundaries` |
| B-5 content | the directory rule, plus B8's manifest check over `content/` | material table v1 |
| B-6 presentation | `import-linter`: the core is forbidden from importing the encoding layer, and the encoding layer is the only producer of frames | the protocol PR |
| B-7 experiments | `import-linter`: `maxim_overdrive` is forbidden from importing the harness | the first experiment |

**`import-linter`** is a maintained tool for declaring import rules ("contracts") in `pyproject.toml`. It is added to
the gate and pinned. Each contract is proven the way every guard is: plant a violating import and watch the gate go
red.

## Migration

- **`phase1/boundaries`** lands after PR 1 and before `phase1/sim-clock`, so sim-clock's new modules are born inside
  the boundaries. It:
  - renames `src/maxim_overdrive/` to `src/maxim_world/`, mechanically;
  - creates an empty `src/maxim_overdrive/` game package;
  - updates imports in `src/`, `tests/`, `scripts/` and docs;
  - adds the contracts for B-1 to B-4 to the gate, and a CLAUDE.md rule with its guards.
- **Packaging:** `pyproject.toml` builds both packages from the one distribution for now, with the bundled `_data`
  mapping attached to the engine.
- **Docs that change:** CLAUDE.md (Layout, the SEM rule's paths, the boundary rule), `docs/architecture.md`, and
  `docs/code_review.md` (the Architecture lens checks boundaries).

## Open questions for the owner

1. **The engine's package name.** `maxim_world` is proposed. Others: `maxim_engine`, a name of its own.
2. **Timing:** a dedicated `phase1/boundaries` PR before sim-clock (proposed), or folded into sim-clock.
3. **Whether `imagination` belongs in the engine.** Validated specs that become cells are a mechanism (engine); the
   budget an imagined object gets is game policy, and could move to content.
