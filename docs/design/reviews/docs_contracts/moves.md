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
