# Decisions of `client_rendering.md`

<!-- Moved verbatim from `client_rendering.md` §0 at 5c054f6 by phase1/docs-contracts (CLAUDE.md, "One owner
per contract"). A record: rulings are never edited; a new ruling is a new row. Who, date and Owner section come
from the source table where it had those columns; otherwise the date is the ruling's own or its heading's, and
"cites" lists the sections the ruling's text names, which are not necessarily its owner.
Status comes from supersessions and amendments the rulings state, and from the docs-contracts rulings (`reviews/docs_contracts/rulings.md`). -->

T3–T7 are world decisions (world §0).

| Id | Ruling | Who, date | Owner section | Status |
|---|---|---|---|---|
| T1 | Camera: isometric 3/4, fixed elevation, 90° steps, bounded zoom, a cut-away rule | owner, 2026-11-18 | §1, §2 | live; also in `decisions/tile_and_client.md` |
| T2 | Click-to-move and WASD, both validated intents; the client never moves the player | owner, 2026-11-18 | §3; world §3 | live; also in `decisions/tile_and_client.md` |
| T8 | The Compatibility renderer for Phase 1 | owner, 2026-11-18 | §7.4 | live |
| T9 | No client-side prediction in Phase 1 | owner, 2026-11-18 | §3.1 | live |
| T10 | Camera elevation 40° | owner, 2026-11-18 | §1 | live |
| T11 | Walls-down by region, with stumps | owner, 2026-11-18 | §2 | live |
| T12 | Goldens gated in Linux CI only; the owner's Mac is advisory | owner, 2026-11-18 | §6.5 | live |
| D20 | Rigs are rendering tiers only; every tier receives the same 0.1 m channels | owner, 2026-11-16 | — | restates world_model §0; also in `decisions/world_model.md` |
| O31 | The tile spec's split into this document and `tile_and_client.md` | owner, 2026-11-18 | — | restates boundaries §0; also in `decisions/boundaries.md` |
| CLAUDE.md | Godot 4.7.2 pinned; typed GDScript, warnings as errors; visuals from channels; never colour alone; nothing fed back | standing | — | restates CLAUDE.md |
