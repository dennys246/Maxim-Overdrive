# Moves: where each moved text went

Old locations are at `origin/main` 5c054f6 (`git show 5c054f6:<path>` recovers the text a record cites). No section is
renumbered. A section whose text moved keeps its heading and gains a pointer.

## Step 1: fold tables (verbatim, checked line for line against the deletions; a rerun of `foldtable.py` reproduces its table byte for byte)

| Old location | New home |
|---|---|
| `boundaries.md`, "Fold table: the v1 review" | `reviews/boundaries/fold.md` |
| `boundaries.md`, "Fold table: the foundations review" | `reviews/foundations_v1/fold_boundaries.md` |
| `npcs_and_sem.md`, "Fold table: the foundations review" | `reviews/foundations_v1/fold_npcs_and_sem.md` |
| `npcs_and_sem.md`, "Fold table: world_v2 findings handed to this part" | `reviews/world_v2/fold_npcs_and_sem.md` |
| `npcs_and_sem.md`, "Fold table: the last two review rounds" | `reviews/npcs_v3/fold.md` (`foldtable.py` retargeted) |
| `world_model.md`, "Fold table" | `reviews/world_model/fold.md` |

## Step 2: decision tables

Each document's rulings move verbatim to `docs/design/decisions/<doc>.md`. Each record is one table: `| Id | Ruling | Who, date | Owner section | Status |`. The design keeps its heading and gains a pointer. The check: every word of each removed section is in its record or its pointer, apart from column headers, list numbers, the period after an id, and item separators.

| Old location | New home | Rulings |
|---|---|---|
| `boundaries.md` §0 | `decisions/boundaries.md` | 20 |
| `npcs_and_sem.md` §0 | `decisions/npcs_and_sem.md` | 42 |
| `world_model.md` §0 | `decisions/world_model.md` (with its two lead paragraphs) | 11 |
| `tile_and_client.md` §0 | `decisions/tile_and_client.md` | 18 |
| `client_rendering.md` §0 | `decisions/client_rendering.md` | 10 |
| `inference_placement.md` §0 | `decisions/inference_placement.md` | 11 |
| `sem_stimuli.md` §10 | `decisions/sem_stimuli.md` | 20 |
| `fire_model.md` §11, items 1–3 (items 4–10 and the asks table stay) | `decisions/fire_model.md` | 3 |

Not moved: `ip_and_licensing.md` §1, which holds proposals, not rulings.

`check_plan.py` reads the five records of its six documents. Its required set at 5c054f6 is 169 ids, and now 168:
only OD-EA9 dropped (`tests/fixtures/check_plan/required_ids.txt` records why).

## Word counts (ceiling: 5c054f6)

| Document | 5c054f6 | Now |
|---|---|---|
| `boundaries.md` | 13,982 | 10,527 |
| `npcs_and_sem.md` | 23,492 | 16,191 |
| `world_model.md` | 4,666 | 3,557 |
| `tile_and_client.md` | 5,909 | 5,468 |
| `inference_placement.md` | 4,886 | 4,564 |
| `client_rendering.md` | 3,800 | 3,613 |
| `sem_stimuli.md` | 5,996 | 5,910 |
| `fire_model.md` | 5,991 | 5,834 |

## Step 3a: wire

Old locations are at 5c054f6. Abbreviations as in the plan's §2.

| Row | Contract | Owner section | Copies replaced by links (file §) | Added to the owner (what) |
|---|---|---|---|---|
| 1 | Intent kinds, vocabulary v1 | `tile_and_client.md` §3.2 | `boundaries.md` §6.1 (authority table, "strike, ignite, douse, …"); `world_model.md` §8 (F7's `douse` description) | the v1 kind list (`move`, `move_to`, `kindle`, `strike`, `douse`, `imagine`, from T §3.1 and §3.3) and F7's "water as a heat and O₂ sink, with caps" |
| 2 | `kind_rank` values | `boundaries.md` §6.2 | `tile_and_client.md` §3.1 (0/1/2/3, deleted); `checklists.md` 5a (0/10/20/30) | the ranks as ruled: join/leave 0, `time` 10, moves 20, `kindle`/`strike`/`douse`/`imagine` 30, "leaving room" (CL) |
| 3 | Ordering key | `boundaries.md` §6.2 | `tile_and_client.md` §3.1; `npcs_and_sem.md` §9 (the tuple and "Controls and joins rank before intents") | nothing |
| 9 | Refusal codes, check order | `tile_and_client.md` §3.4 | `fire_solid.md` §5.3's dangling "5a's list" now names tile §3.4's enum (`simcore/core/refusals.py`) | nothing |
| 11 | Frame header, catalogue, bump rules | `client_rendering.md` §4.1 | `world_model.md` §8 ("Frame rules" F2–F4, F6; "v2 §8 stands" now names the owner); `architecture.md` "Transport" (compression field); `checklists.md` step 7 (`required`, `compression`, `axis_order`) | grids (shape, cell size, origin), `compression` (off in v0), uncompressed size (WV2 §8, AR); `required` and encoding per channel, typed column-major tables (WV2 §8, WM F4); the refuse/ignore and bump rules, `kind: delta` reserved (WV2 §8, RL §7 W-F6, WM F2–F3); axis order (RL §7 W-F4) |
| 12 | `welcome` fields | `client_rendering.md` §4.1 | `sem_stimuli.md` §3.2 (`bindings_digest`); `ip_and_licensing.md` §6 item 4 (spec ids); `checklists.md` step 7 (`build`) | own `actor` id, material table v1 (RL §7, WV2 §8); zone list (WV2 §8); recipe name↔id map (FS §5.6); each region's spec id (IL §6); `bindings_digest` (SS §3.2); engine `build` (CL) |
| 13 | Messages per step | `client_rendering.md` §4.1; `tile_and_client.md` §3.3 | `world_model.md` §10 row 6 (`act_result`); `foundations_plan.md` row 7; `tile_and_client.md` §3.3's server-to-client list | nothing |
| 14 | Frame bytes per cell | `client_rendering.md` §4.2 | `architecture.md` "Transport" (5 B per cell and the sizes derived from it) | nothing |
| 15 | Buffer caps | `client_rendering.md` §4.3 | `architecture.md` "Transport" ("both ends must raise", and head-of-line "harmless for a turn-based game") | nothing |
| 16 | Handshake | `boundaries.md` §5.3 | `client_rendering.md` §7.5 (token, `Origin`, order); `architecture.md` "Transport"; B §5.3's table row now points below | RL §5's token and handshake bullets, verbatim |
| 17 | Strict JSON, 2⁵³ | `boundaries.md` §9.1 | `client_rendering.md` §4.1 (JSON bullet); `checklists.md` step 7 | nothing |
| 18 | Two-stage validation | `boundaries.md` §5.3 | its own citation "(world_v2 §7)" corrected to lanes §7 | caps from `data/world/` (ruling 18); both refusals are replies with a listed code, the world unchanged; one gate for NPCs, LLM results and clients (RL §7) |
| 19 | Frame publication, snapshot cadence | `tile_and_client.md` §4; `client_rendering.md` §4.1 | `boundaries.md` §4.2 ("Cadence") | T §4: cells change at physics steps (0.5 s) and at intent apply (B §4.2); C §4.1: 2 Hz during any fire, served from the last frame, coalesced, rate-limited, encoded once and shared, read-only (RL §7) |

Skipped:
- **Rows 6 and 7** (receipts): OD-A16's credit kinds (`stale`, `call_error`, `wrong_target`, roadmap Phase 3) don't fit the split. `stale` is an agent-facing receipt kind in OD-A16 and in B §7.2 ("zero times when `stale`"), but in the split only the wire `intent_result` has it, and SS §6.2's agent kinds are `malformed`, `limit`, `accepted`. Left for the owner.
- **Rows 10 and 79:** open. #31's shader reads `surface_glow` and `burning` as live channels, and #31's session has
  taken the conflict with `fire_solid.md` §5.6 to the owner (2026-11-21). Row 79's tile §5.5 edit was reverted on
  review: it pointed at §4.2's bed meaning, which still stands, so the two wait together.
- **Row 16, T §3.3's `hello` row:** left; it is the message's fields, not the handshake rules.
- **Row 12, FS §5.6's "`welcome` carries the recipe name↔id map":** left as a one-member reference; FS is at its word ceiling.

Word counts (ceiling 5c054f6 → after this step): `boundaries.md` 13,982 → 10,680; `client_rendering.md` 3,800 →
3,800; `tile_and_client.md` 5,909 → 5,478; `world_model.md` 4,666 → 3,514; `npcs_and_sem.md` 23,492 → 16,178;
`sem_stimuli.md` 5,996 → 5,912; `fire_solid.md` 5,972 → 5,972; `ip_and_licensing.md` 1,874 → 1,874;
`architecture.md` 2,792 → 2,752; `checklists.md` 7,354 → 7,353; `foundations_plan.md` 2,500 → 2,499.

## Step 3b: log, replay and formats

Old locations are at 5c054f6, uncommitted on this branch until the owner commits. Abbreviations as in the plan's §2.

| Row | Contract | Owner section | Copies now links (file §) | Added to the owner |
|---|---|---|---|---|
| 4 | Intent record fields | `boundaries.md` §6.2 | `tile_and_client.md` §3.1 (field list; `invocation` rules); `checklists.md` 5b (two items, the tests kept); `roadmap.md` Phase 3 lead-in (OD-A18's pid) | `invocation`: optional, opaque, null for players, host copies and never mints, null not a stand-in until G17, the refusal before and after the type (T §3.1, CL 5b, RM) |
| 5 | Record kinds | `boundaries.md` §6.1 | `sem_stimuli.md` §5 (sim-clock's reserved records); `checklists.md` 5a (same) | a host-records row: `agent_ready`, `agent_failed`, `floor_event`, `reply_landed`, redaction records; O26's redaction record sentences (ruling-only text) |
| 20 | Log header | `boundaries.md` §6.3 | `world_model.md` §8 (header bullet); `tile_and_client.md` §3.5; `sem_stimuli.md` §5 (header slots); `fire_solid.md` §5.1; `checklists.md` 3b (digest form), 5a (header slots) | T §3.5's digests and "rate limits stay out"; FS §5.1's per-file name, version and recipe-set digest; WM F16's versions, BLAS versions and dirty flag; O43/O45's root id and segment number; SS §5's stimulus slots, verbatim; N §6.6's `PYTHONHASHSEED`; the `sha256/c14n-1:<hex>` form and refuse-by-prefix (`digest.py`); the canonicalizer's home corrected to `simcore/core/digest.py` (tiebreaker 1) |
| 21 | Determinism tiers | `boundaries.md` §6.3 | none: no live document cites RL §4.4's or WV2 §5's tiers | nothing |
| 22 | Rerun manifest | `boundaries.md` §6.3 | none needed | the exception: IP §4.3's recorded items are never refused (ruling 22) |
| 23 | Keyed streams | `npcs_and_sem.md` §3.4 | `boundaries.md` §7.3; `npcs_and_sem.md` §6.6 (randomness bullet), §6.1 table's pointer; `roadmap.md` OD-A7; `checklists.md` 3b (`:` rule) | `sha256(...)` join (RM OD-A7); stream argument, `"npc_key:stream"`, never Maxim's ordinal, state saved pickle-free (N §6.6) |
| 24 | Timing units | `npcs_and_sem.md` §9 | `boundaries.md` §7.3; `checklists.md` 3b ("ticks derived at load") | nothing |
| 25 | World config | `npcs_and_sem.md` §9 | `tile_and_client.md` §8 (world's day) | RL §2.2's table, time-of-day rule and `data/world/` line, verbatim; its server-config sentence left out (below) |
| 26 | Save v0 | `world_model.md` §8 (F5) | `world_model.md` §10 row 11; `checklists.md` step 9 (load rule) | a content change refused; no in-flight thoughts (ruling 26) |
| 27 | Fuel save tables | `fire_solid.md` §5.5 | `fire_model.md` §9.2 (save bullet) | nothing (FS at ceiling); FM keeps the items FS is silent on |
| 28 | Scene format | `tile_and_client.md` §1.3 | `world_model.md` §8 (F13), §2 (zones' version), §10 row 7; `checklists.md` 3b | F13's loader rules; CL's extent and spawn-name rules; "never migrated, since scenes are repo-only" (code) |
| 29 | Version rules F1, F15 | `world_model.md` §8 | `sem_stimuli.md` §5 | SS §5's "a better estimate bumps … in a commit saying so" |
| 30 | `session_id`, pids | `npcs_and_sem.md` §6.6 | `roadmap.md` OD-A18 (two clauses), Phase 4 save v1 | O43's "never the wall clock or a uuid"; O45's no-collision; O44's floor as a test; "a loaded save continues the sequence" |
| 31 | Thought request id | `boundaries.md` §6.1 | `npcs_and_sem.md` §11.1 | nothing |
| 32 | Tick order | `sem_stimuli.md` §4.1 | `tile_and_client.md` §2.3 | nothing |
| 33 | Tripwire scope | `boundaries.md` §3 | `world_model.md` §6 | WM §6's pymaxim binding fact and the RNG-state comparison |

Left, and why:
- Row 25: RL §2.2's "Server config … in `data/server/`" is not copied; ruling 18 puts stage-1 caps in `data/world/`,
  and `data/server/` is open in `rulings.md`. `client_rendering.md` §4.1's "the world config" stays unlinked (C at
  ceiling). WV2 §5's hashed world config list is a record.
- Row 26: B §6.2's "a save is a checkpoint plus the log" is left; F5 is silent on it.
- Row 28: FS §5.2 puts fuel in "the scene version after the one on `main`"; T §1.3 and `scene.py` reserve v2 for
  zones. FM §7's "Scene v2 carries fuel objects" also conflicts. Not edited.
- Row 30: CL's crash-recovery and replay-id items are tests to write that agree; kept. RM's Phase 3 exit line kept.
- `checklists.md` step 1's "Merge the four specifications of the intent-log header" left for the owner to mark.

Word counts (5c054f6 → after step 3a → now): `boundaries.md` 13,982 → 10,680 → 11,016; `npcs_and_sem.md`
23,492 → 16,178 → 16,311; `tile_and_client.md` 5,909 → 5,478 → 5,491; `world_model.md` 4,666 → 3,514 → 3,474;
`sem_stimuli.md` 5,996 → 5,912 → 5,847; `fire_model.md` 5,991 → 5,834 → 5,805; `fire_solid.md` 5,972 → 5,972 → 5,951;
`checklists.md` 7,354 → 7,353 → 7,212; `roadmap.md` 6,976 → 6,976 → 6,820.

## Rows 6 and 7 (receipts), after the owner's re-ruling

| Row | Contract | Owner section | Copies now links | Added to the owner |
|---|---|---|---|---|
| 6 | Agent-facing receipt | `sem_stimuli.md` §6.2 | `boundaries.md` §7.2, `npcs_and_sem.md` §6.4, `inference_placement.md` §2.6's pointer | nothing |
| 7 | Wire `intent_result` | `tile_and_client.md` §3.3 | `boundaries.md` §7.2, `npcs_and_sem.md` §6.4 | the shape, from its own "one receipt shape" bullet (was cited to boundaries §7.2) |

Fixed on review of step 3b: `checklists.md` step 9 keeps "loading never replays the log", which F5 and F14 don't say
and ruling 26 doesn't contradict.
