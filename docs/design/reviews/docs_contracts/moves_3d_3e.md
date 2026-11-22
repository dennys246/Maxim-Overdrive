# Moves, steps 3d and 3e

Old locations are at `origin/main` 5c054f6, as in `moves.md` (which is near its word budget). No heading moved.
Abbreviations as in the plan's §2.

## Step 3d: packaging and gates

| Row | Contract | Owner section | Copies now links | Added to the owner |
|---|---|---|---|---|
| 39 | Phase 3 rows (OD ids) | `roadmap.md` Phase 3 | `boundaries.md` §9.3 (the table, now one sentence of ids); `npcs_and_sem.md` §8.1 (the "What" and "Path" columns; "Here" kept) | nothing; OD-A16's `wrong_target` stays the roadmap's, and the copies that lacked it are gone |
| 49 | Package layers | `boundaries.md` §2.2 | `tile_and_client.md` §7 (a lead line); `verify_harness.md` §2 ("under `maxim_overdrive` and above `simcore.protocol`"); `inference_gateway.md` §1 ("7a", "7b" removed; the column already cites §2.2); `sem_stimuli.md` §7.1 ("the layer order stays §2.2's") | ruling 49's five layers as `pyproject.toml`; which table rows are built, under which `simcore` package; which are not built; the table kept as O24's map of splits |
| 50 | Write-window owners | `boundaries.md` §4.1 | `boundaries.md` §10 ("`place` opens it too", now "the window's owners are §4.1's") | ruling 50's four owners; §10's "`place` opens it too (marked for 5a; `imagine` has no intent kind)", verbatim |
| 51 | `logging` in the core | `boundaries.md` §3 | `boundaries.md` §10 ("§3's ban covers `logging` too") | `logging` moved from allowed to banned, with `pyproject.toml`'s reason verbatim; the built list is the `sealed-core` contract, equal to `SEALED_CORE_BANNED` |
| 52 | Who imports `maxim` | `boundaries.md` §8.1 | `npcs_and_sem.md` §6.6 (the host's imports); `sem_stimuli.md` §7.3 (a citation on its `maxim-through-adapters` row) | as built, only `simcore.adapters.sem`; the worker module (SS §7.3) and `engine.adapters.inference` (IG §1) join when built; N §6.6's host sentence, verbatim; the pin 2.6 from `constraints/py3.12.txt` beside "verified on 2.15" |
| 53 | Where the gates are | `boundaries.md` §5.3 | `fire_solid.md` §5.1 ("the one input gate"); `architecture.md` "SEM for the environment" (the modulator no longer carries LLM output and client intents) | nothing; §5.3's client-frames row now cites §9.1 for the strict decoder, not §10 |
| 54 | Gate contract | `boundaries.md` §5.4 | `world_model.md` §8 (F14's lead line; material table v1's "versioned, closed keys, repeated keys refused"); `ip_and_licensing.md` §6 item 3 ("as every loader does") | nothing |
| 55 | Experiment harness | `npcs_and_sem.md` §10 | `boundaries.md` §2.1 (rule, package bullet, table row), §8.1 (table row), §8.4 | B §8.4's import bullet and ledger-pins bullet, verbatim apart from the subject ("it" for `maxim_experiments`) |
| 56 | Content and licence | `boundaries.md` §8.2 | `architecture.md` "Licensing"; `roadmap.md` standing rules | architecture's sentence, verbatim (the roadmap's is a subset) |

Also: `inference_placement.md` §4.3's ledger citation moves from B §8.4 to N §10, and B §2.1's "The engine's name is
open (Q1)" now reads `simcore` (O23, as built).

Skipped:
- **Row 57** (golden method): no live copy restates C §6's method. World_v2 §5 is a record; the roadmap's exit and
  the foundations plan's crate are row 59.
- **Row 58** (requirements by step): tile §11 restated checklist items and is now a link. Client §12 is kept: its
  step 2 and 8 items (bricks, picking, HUD, `net_client.gd`, a post-`imagine` frame) are not in `checklists.md`.
- **Row 50, the roadmap's band-aid list** already cites B §4.1 and names the marked files the lint needs; left.
  B §11.1's 2c bullet is a migration record; left.
- **Row 52, `inference_gateway.md` §1's** "`maxim-through-adapters` gains `engine.adapters.inference`": left, as IG
  has no slack and the line places its own module.
- **Row 54, `fire_solid.md` §1.3 and §5.1** state limits and catalogue rules of their own, not the gate contract.
- **Row 55, `boundaries.md` §10's B-7 row** still names `maxim_experiments`; it is enforcement, left for the owner.
- **O8** is not copied: "Only the applier and the physics laws hold the write handle" and "a shipped build doesn't
  copy frames at exit" contradict the built window (four owners; `CellStore.writing` copies in every build).

Word counts (5c054f6 → now): `boundaries.md` 13,982 → 10,598; `npcs_and_sem.md` 23,492 → 16,002;
`tile_and_client.md` 5,909 → 5,356; `verify_harness.md` 1,252 → 1,243; `inference_gateway.md` 2,509 → 2,507;
`inference_placement.md` 4,886 → 4,607; `sem_stimuli.md` 5,996 → 5,862; `fire_solid.md` 5,972 → 5,949;
`architecture.md` 2,792 → 2,742; `roadmap.md` 6,976 → 6,825; `world_model.md` 4,666 → 3,480;
`ip_and_licensing.md` 1,874 → 1,872.
