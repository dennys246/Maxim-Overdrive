# Long-term features: where each stands (tracker, started 2026-11-20)

**What this is.** A tracker for features that run longer than one step or phase. Each runs as research, then design,
then rungs, with owner decisions between them. It holds **status and pointers**, never the design itself: each
entry names its documents, its gates, what's decided, what's open and its next step. The foundations plan
(`foundations_plan.md`) still owns step order, and the roadmap (`../roadmap.md`) still owns phase scope. A tracker
entry that disagrees with either is wrong, and gets fixed in the same commit that notices it.

**Rule for entries (owner, 2026-11-20).** A long-term feature has two halves, with different rules:
- **A contract,** decided early and reviewed deeply because it is expensive to change: its formats, its interface to
  the rest of the engine, and what an NPC can sense of it.
- **Its laws,** honest but allowed to be simple, behind that contract, and refined on a calendar budget because they
  can be swapped without a refactor.

Each entry says which half each piece of work is.

## Fire

| | |
|---|---|
| **Goal** | Fire that spreads and burns only by heat transfer, which an NPC can learn from what it senses |
| **Documents** | `../design/fire_model.md` v2 (the direction); `../design/fire_solid.md` (the 6.0–6.1 build spec, accepted 2026-11-20); research in `../design/research/fire_ladder/`, `physics_spike/`, `accelerant_spike/`, `hot_surface_spike/`, `solid_spike/`; reviews in `../design/reviews/fire_model/`, `fire_solid/` |
| **Contract** | fuel objects, segments and coupling (`fire_solid.md` §1–§3); the material data split (§5.1); occupancy (§2); what NPCs sense of fire (the SEM stimulus interface, below) |
| **Laws** | the 1D solid (6.1); flames (6.2); two bodies (6.3); crib and exit (6.4) |
| **Decided** | the ladder (rulings of 2026-11-20); tile §6.3's cross-grid tolerances kept; fits only within cited ranges, graded on held-out data; FDS 6.11.1 as the verification oracle; "light a built fire" as the exit |
| **Status** | **Solid spike:** the solid matches FDS; rerun 1 (numerics only) converges, and validation still misses with every fit at a bound (R5, R6). **The owner took the fallback (2026-11-20):** Phase 1's exit is the lone-surface solid, lit, charring and flaming out, verified but not validated; the crate and 6.2–6.4 move to Phase 2; rerun 2 is banked (`solid_spike/results_rerun1.md` §7). Production code waits for step 5a (6.0a) and step 5b (6.0b) |
| **Open** | why the solid ignites PMMA late at 25 kW/m² (parameter transfer from N₂ gasification, or the ignition criterion); the flame design (6.2), written from the spike's results; the separate NPC fire note (the Maxim asks MP-1, MP-2) |
| **Horizon** | **Long term** (owner, 2026-11-20). The exit's fallback, the highest rung that passes honestly, stays available whenever the owner calls it |
| **Next** | 6.1's production solid, with its validation misses as Known gaps; rerun 2 once the pre-ignition question has a cited answer |

## Plasma

| | |
|---|---|
| **Goal** | Plasma as a state of matter, built slowly, for what NPCs can sense of it: an arc is a flash in the light field, a crackle in the sound field and ozone in the gas field, and its EMI touches cyberware sensors (owner, 2026-11-19) |
| **Documents** | `../roadmap.md` Phase 2 (the three steps below); no design document yet |
| **Contract** | each step is a law in step 5a's list and a field in the registry; the light, sound and gas fields it writes into |
| **Laws** | (1) plasma effects: cutters, welders and weapons as very hot, bright sources (needs the light field); (2) electric fields and arcs: a local potential field, conductivity per material, breakdown as a band-gated binary outcome on the reconstructed field, stochastic channels from the world's seeded RNG; (3) ionised gas: a Saha ionisation fraction, conductivity and radiative cooling, coupled to gas and zones |
| **Decided** | first-principles plasma physics (MHD, particle-in-cell) is out of scope for good: its scales are about 10⁵ finer and 10⁸ faster than the grid, and no player could perceive it |
| **Status** | not started; Phase 2 |
| **Prerequisites** | the light field (Phase 2) and, for step 3, gas zones (Phase 2); the SEM stimulus interface for luminance and sound |
| **Next** | Nothing until the light field is designed |

## The SEM stimulus interface

| | |
|---|---|
| **Goal** | The contract by which the world delivers physical stimuli at receptor locations to NPCs that are Maxim agents, so that what they learn is the world's regularities, never our rules |
| **Documents** | `../design/sem_stimuli.md`; research in `../design/research/sem_stimuli/`; reviews in `../design/reviews/sem_stimuli/` |
| **Contract** | all of it: which quantities, in what units and ranges, sampled where on the body, at what cadence, how they reach Maxim through its frozen SEM types, what is recorded for replay, and the tests that prove no privileged state leaks |
| **Laws** | the world-side models behind each stimulus (skin heat, radiation onto body regions, luminance after line of sight), each replaceable behind the contract |
| **Decided** | the world computes the stimulus at the receptor and Maxim transduces it (`fire_model.md` §5.1); fractions, never booleans; no flammability, flash point or φ as a sensor; tissue physics is the world's (lesson 24) |
| **Status** | design v1 reviewed by seven lenses (15 BLOCKER, 66 SHOULD-FIX, 49 NIT); the owner ruled D1–D12 as recommended (2026-11-20: D5 (c), every body steps each tick; D11 (a), per-site occlusion; D12, a budget of 10 NPCs near a fire with a work-counter gate); v2 folded (`reviews/sem_stimuli/fold.md`), statuses open for the reviewers; D11–D12 reconfirmed at v2's corrected costs and D13 ruled (2026-11-21) |
| **Next** | A delta round on v2, whose reviewers set the fold statuses; M16 to Maxim with the embeddable draft |

## States of matter: liquids, gases and zones

| | |
|---|---|
| **Goal** | Phase is the container a quantity lives in: solids in cells, gases in zones joined by gaps, liquids in pools |
| **Documents** | `../design/world_model.md` §2; `../design/research/states_of_matter/` |
| **Contract** | containers by phase; transfers between them that conserve mass and energy; fire's inventories (`fire_solid.md` §1) already follow it |
| **Laws** | zones and vents, combustion per zone, phase change, positioned puddles (Phase 2, by D26) |
| **Status** | the container model is decided; the Phase 2 laws aren't designed |
| **Open** | dripping, deferred by the fire design until pools have positions; per-species zone state |
| **Next** | Phase 2 |

## Light and sound fields

| | |
|---|---|
| **Goal** | What an agent can see and hear, and what the client draws |
| **Documents** | `../roadmap.md` Phase 2 |
| **Contract** | shared with the SEM stimulus interface: luminance, angular size and flicker in view after line of sight; sound pressure and onsets at the ear |
| **Status** | Phase 2; fire, plasma and NPC vision all wait on the light field |
| **Next** | The SEM stimulus interface fixes what these fields must deliver before they are designed |

## Performance

| | |
|---|---|
| **Goal** | Real time at the tile, measured, with budgets |
| **Documents** | `../architecture.md` Known gaps; `../standards_backlog.md` B5; `../design/research/fire_ladder/5_numerics.md` |
| **Status** | `advance(0.5)` costs about 0.7 s of CPU at 1.92 × 10⁶ cells, before fire, NPCs or radiation exist. Fire's costs are measured in its reviews (flame radiation dominates) |
| **Next** | A fire budget before 6.2's radiation; deterministic work counters as the primary gate |

## How this file is kept

- **An entry changes in the same commit** as the work or ruling that changes it.
- **An entry is retired** when its feature ships or the owner drops it, with one line saying which.
- **New entries** are added for any feature the owner names as long term.
