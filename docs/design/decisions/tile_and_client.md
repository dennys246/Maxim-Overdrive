# Decisions of `tile_and_client.md`

<!-- Moved verbatim from `tile_and_client.md` §0 at 5c054f6 by phase1/docs-contracts (CLAUDE.md, "One owner
per contract"). A record: rulings are never edited; a new ruling is a new row. Who, date and Owner section come
from the source table where it had those columns; otherwise the date is the ruling's own or its heading's, and
"cites" lists the sections the ruling's text names, which are not necessarily its owner.
Status comes only from supersessions and amendments the rulings state. -->

T8–T12 are client decisions (`client_rendering.md` §0).

| Id | Ruling | Who, date | Owner section | Status |
|---|---|---|---|---|
| T1 | Camera: isometric 3/4, fixed elevation, 90° steps, bounded zoom, a cut-away rule | owner, 2026-11-18 | — | restates `client_rendering.md`; also in `decisions/client_rendering.md` |
| T2 | Movement: click-to-move and WASD, both validated intents through the one door, logged; the client never moves the player | owner, 2026-11-18 | §2, §3 | live; also in `decisions/client_rendering.md` |
| T3 | Tick 0.1 s, physics every 0.5 s; the 6 s turn is retired | owner, 2026-11-18 | §6.1 | live |
| T4 | `kindle`, with power from a held item; `ignite` retired | owner, 2026-11-18 | §3.2 | live |
| T5 | A body heat state from Phase 1 | owner, 2026-11-18 | §2.1 | live |
| T6 | File OD-C11 (egocentric locomotion) with Maxim | owner, 2026-11-18 | §3.1 | live |
| T7 | The walk direction is an integer vector, canonicalised at stage 1 | owner, 2026-11-18 | §2.3 | live |
| T13 | Frozen at v3; no more paper rounds on the fire physics. Step 6's PR carries a short design note under the Physics lens, the final review's FPH-B1 to B3 are its requirements, and its convergence tests and pre-registered failure path decide | owner, 2026-11-18 | §5 | live |
| T14 | The flame radiates into bodies by a point source in Phase 1; into walls in Phase 2 | owner, 2026-11-19 | §9 | live |
| T15 | The crate: 20 mm slats at φ = 0.25 | owner, 2026-11-19 | §9 | live |
| T16 | Protocol v0 freezes only the kinds a Phase 1 client sends | owner, 2026-11-19 | §3.3, §9 | live |
| T17 | An accelerant lights the crate, not the pilot alone; step 6 researches char oxidation first (`physics_spike.md`) | owner, 2026-11-20 | §5, §6.3 | live |
| T18 | The accelerant is a pore-loading field the SEM bridge reads, never an SEM rule (`physics_spike.md`) | owner, 2026-11-20 | §5, §9 | live |
| RT1–4 | Real time with pause on a fixed tick; a dial; pause a state; host-only time control | owner, 2026-11-15 | — | restates realtime decisions 1–4 |
| D20, D25 | One truth at 0.1 m, rigs are rendering tiers; reconstruct, decide at the point, integrate | owner, 2026-11-16 | — | restates world_model §0 |
| D26–D28 | Tile first, exit as written; clinic after; heat-debt prototype after the tile | owner, 2026-11-17 | — | restates world_model §0 |
| D29, D30 | Step 6 = 6a open-air loss, 6b surface skin, 6c porous fuel bed, 6d char oxidation; solid sub-cell recession moves to Phase 2 | owner, 2026-11-18 | — | restates world_model §0 |
| O23, O24, O31 | Frames publish on change; `simcore` in four layers (core, adapters, game, client protocol); this split | owner, 2026-11-17/18 | — | restates boundaries §0 |
