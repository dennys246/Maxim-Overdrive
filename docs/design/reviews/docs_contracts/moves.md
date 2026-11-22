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

## Word counts (ceiling: 5c054f6)

| Document | 5c054f6 | Now |
|---|---|---|
| `boundaries.md` | 13,982 | 11,617 |
| `npcs_and_sem.md` | 23,492 | 18,816 |
| `world_model.md` | 4,666 | 4,180 |
