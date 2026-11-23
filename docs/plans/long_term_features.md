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
| **Next** | 6.1's production solid, with its validation misses as Known gaps, flipping the burnout red gate (owner, 2026-11-21); rerun 2 once the pre-ignition question has a cited answer |

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
| **Contract** | all of it: which quantities, in what units (ranges are Maxim's transduction), sampled where on the body, at what cadence, how they reach Maxim through its frozen SEM types, what is recorded for replay, and the tests that prove no privileged state leaks |
| **Laws** | the world-side models behind each stimulus (skin heat, radiation onto body regions, luminance after line of sight), each replaceable behind the contract |
| **Decided** | the world computes the stimulus at the receptor and Maxim transduces it (`fire_model.md` §5.1); fractions, never booleans; no flammability, flash point or φ as a sensor; tissue physics is the world's (lesson 24) |
| **Status** | **v5, the contract, is final on paper** (owner, 2026-11-21: the rounds stop). Four paper rounds of seven lenses (blockers 15, 2, 4, 1); the final round's findings are folded into v5 or moved to `checklists.md` as tests (`reviews/sem_stimuli/final/fold.md`), statuses set when the code PRs' reviews read the tree. Ruled D1–D15 and S4; D12 provisional; PH2-S2 re-ruled to (c): the world is the body's plant and the NPC its controller, with effector commands reserved and an ANALOG stand-in until Maxim drives them (M20, OD-C12) |
| **Next** | 5a carries the contract's reservations (`sem_stimuli.md` §11.1); 5b, `phase1/agents` and the tissue row build the rest, each reviewed as code, and each step's plan lists the v5 fold rows it settles; T16c and T17 are future bars on Maxim (OD-A22, OD-C12); M4 goes to Maxim when Phase 4's planning starts (owner, 2026-11-21) |

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
| **Documents** | `../known_gaps.md`; `../standards_backlog.md` B5; `../design/research/fire_ladder/5_numerics.md` |
| **Status** | `advance(0.5)` costs about 0.7 s of CPU at 1.92 × 10⁶ cells, before fire, NPCs or radiation exist. Fire's costs are measured in its reviews (flame radiation dominates) |
| **Next** | A fire budget before 6.2's radiation; deterministic work counters as the primary gate |

## Structure and motion: load, moving bodies and sub-cell solids

| | |
|---|---|
| **Goal** | Objects bear load and fail under it, and intact objects move as physical bodies (pushed, toppled, dragged, thrown) on the authoritative server, so that an NPC can learn what holds and what falls (owner, 2026-11-22, D31, D32) |
| **Documents** | `../roadmap.md` Phase 2; `../design/world_v2.md` §3.2 (strength) and §4 (connectivity, loose solids, settling by angle of repose); research in `../design/research/subcell_solids/`; no design document yet |
| **Contract** (to decide) | what a body is against the grid, and how it hands back to cells at rest; the formats a body adds to frames, saves and the intent log; determinism (bit-identical on one machine, the outcome class across machines and grids); what NPCs sense (weight, contact, motion) |
| **Laws** (to choose) | load against capacity (crushing, bending, buckling), rechecked on events and as strength changes; rigid-body dynamics with contacts and friction; each with a closed-form test and a cross-grid test |
| **Decided** | load is in (D31); moving bodies are in if they can be done honestly, and a declined cost is a valid result (D32); imagined objects meet the support rule when placed (D33); sub-cell solids that aren't fuel get a contract, designed and reviewed before code (D34); a metric threshold in data, analytic primitives, one store with fuel objects (D35) |
| **Open** | whether an existing physics library can meet the determinism and cross-grid rules, or the laws are ours; how fire and load couple (a burning leg fails, the table falls); the sub-cell solids contract: thin sheets, panes and structural members thinner than two cells (D31, D34) |
| **Status** | not started; Phase 2 |
| **Next** | The sub-cell solids design (survey done: `../design/research/subcell_solids/survey.md`; answered by D35), then its review; then a pre-registered spike, as for fire: the closed forms first (D31's, a box's tipping angle, a block sliding with friction), then one body crossing two grids |

## Imagined-object generator

| | |
|---|---|
| **Goal** | Text to imagined-object specs that the world accepts and that behave as asked, written by a generator on the world's side (O57); perhaps later a small model trained against the world's own scorer |
| **Documents** | `../design/research/specgen_spike/plan.md` (stage 1) and `sources.md`; `../design/generation_harness.md` (the offline harness and its use battery, built after stage 1); `../architecture.md` "Imagination"; `../roadmap.md` Phase 6 |
| **Contract** | the spec `place` accepts (v0 today; v1 planned in `../design/fire_model.md`), with its refusal codes; provenance and the IP gate (`../design/ip_and_licensing.md` §3, §6) |
| **Decided** | the spike is allowed, local only, P = 0.8 (O56); the generator is world-side, never the agent's imagination (O57); local models first (O58) |
| **Open** | whether stage 2, training, goes ahead (plan §6); physics scoring waits on spec v1 (plan §5); the two Maxim questions O57 defers to Phase 6's design; `owner_lan` as "owner machines", a declared known gap resolved with the peer-mesh refinement between Maxim and Overdrive (owner, 2026-11-22; `../design/generation_harness.md` §2) |
| **Status** | stage 1 pre-registered 2026-11-22 (`spikes/specgen/freeze.sha256`); S and R measured on the mini; not run |
| **Next** | write the generator and the scorer under `spikes/specgen/`; run S, then R in windows the owner sets (about 9 h and 62 h on the mini) |

## How this file is kept

- **An entry changes in the same commit** as the work or ruling that changes it.
- **An entry is retired** when its feature ships or the owner drops it, with one line saying which.
- **New entries** are added for any feature the owner names as long term.
