# Decisions of `world_model.md`

<!-- Moved verbatim from `world_model.md` §0 at 5c054f6 by phase1/docs-contracts (CLAUDE.md, "One owner
per contract"). A record: rulings are never edited; a new ruling is a new row. Who, date and Owner section come
from the source table where it had those columns; otherwise the date is the ruling's own or its heading's, and
"cites" lists the sections the ruling's text names, which are not necessarily its owner.
Status comes only from supersessions and amendments the rulings state. -->

From v1 and v2 (records in those files): real time on a fixed tick; the time dial; host-only time control; waiting
defined in world time; states of matter as the organising principle; the world simulates and SEM exposes;
temperature plus phase-change progress as the stored heat state.
**Owner, 2026-11-16, after v2's review:**

| Id | Ruling | Who, date | Owner section | Status |
|---|---|---|---|---|
| D20 | **One simulation truth.** Every machine simulates the same world at the same resolution. The truth is 0.1 m base cells (§1). Rigs become rendering tiers only. | owner, 2026-11-16 | cites §1 | live; also in `decisions/client_rendering.md` |
| D21 | **Resolution follows the world, not the machine.** Refinement, if added, is decided from world state, the same on every machine. A machine's time budget may coarsen or sleep only regions where the outcome is provably unchanged; otherwise the world dilates and says so (§1.2). | owner, 2026-11-16 | cites §1.2 | live |
| D22 | **Rubble and collapse move to Phase 2,** with their foundations laid now so that adding them is no major refactor (§7). | owner, 2026-11-16 | cites §7 | live |
| D23 | **The Phase 1 lab is a physics benchmark tile.** NPCs arrive later, starting with the lessons Phase 1 can actually teach (part 2). | owner, 2026-11-16 | — | amended by D26 |
| D24 | **The design is split into three documents, each reviewed separately.** | owner, 2026-11-16 | — | live |
| D25 | **Physics standard:** reconstruct, decide at the point, integrate upward (CLAUDE.md). This part applies it to every law, not one (P-verdict). | owner, 2026-11-16 | — | live |
| D26 | **Tile first (owner, 2026-11-17, after the plan review).** Phase 1's exit is the roadmap's original one: walk into the alley, set a crate on fire, watch it crack, glow and burn away. The crate burns out by a fuel-mass law in open air. The lab's sealed and vented fires (O₂, zones, combustion per zone, products) move to Phase 2, and so do fuel recession and pyrolysis, phase change and the CSG footprints. This amends D23: the lab is Phase 2's benchmark tile, not Phase 1's. §10's order is replaced for Phase 1 by `docs/plans/foundations_plan.md` §2. | owner, 2026-11-17 | cites §10, §2 | amended by D29 |
| D27 | **The clinic follows the exit (owner, 2026-11-17).** Phase 1 builds the alley; the ripperdoc clinic is authored after the exit passes and before Phase 4, whose first NPCs live there. §12's three questions are answered as recommended: truth at 0.1 m, the band gate for binary outcomes, CSG footprints in Phase 2. | owner, 2026-11-17 | cites §12 | live |
| D28 | **A grey-box heat-debt prototype precedes the tile (owner, 2026-11-17, S-S7; VS5).** As the vertical slice, a rough playable test of "Overdrive as heat debt" (`world_v2.md` §10) comes before more physics breadth, to find out whether pushing past limits in a burning space is fun. | owner, 2026-11-17 | cites §10 | live |
| D29 | **Step 6 carries three laws D26 deferred (owner, 2026-11-18, after the tile spec's review).** D26's claim that an open-air crate fire needs no Phase 2 physics was wrong (`reviews/tile_v1/physics.md` PH-B1 to PH-B3): the crate's ~1.6 GJ had no sink, a cell mean hides a glowing surface, and burn-away time doesn't converge without recession. So step 6 becomes 6a open-air heat loss on exposed faces, metered on the energy ledger; 6b the per-face surface skin (§3, §8's face table), which drives glow, crack and ignition by area; 6c sub-cell fuel recession. Zones, combustion products, phase change, CSG and the lab stay in Phase 2. This amends D26. | owner, 2026-11-18 | cites §3, §8 | amended by D30 |
| D30 | **The crate is a porous fuel bed, and its embers glow (owner, 2026-11-18, after the delta review).** A lone solid 0.6 m block goes out in open air: its faces lose ~63 kW at 600 °C against a ~58 kW mean release, and glow needs char oxidation (`reviews/tile_v1/delta_physics.md` DPH-B1, DPH-B2). A real crate is slats around air. So step 6 models it as fire engineers model fuel beds: each cell holds a fuel volume fraction and a surface area per volume, its burn driven by heat reaching that surface; and char oxidation makes the embers glow. Step 6 becomes 6a open-air loss, 6b the surface skin, 6c the porous fuel bed, 6d char oxidation. Sub-cell recession of solid fuel moves to Phase 2. This amends D29. | owner, 2026-11-18 | — | live |
