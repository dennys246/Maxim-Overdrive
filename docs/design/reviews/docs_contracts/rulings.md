# Rulings for the docs-contracts line (owner, 2026-11-21)

The owner agreed to the author's recommendations as a whole ("agreed with your recommendations overall",
2026-11-21). The rows cite the plan's inventory (`docs/plans/docs_contracts.md` §2). The author wrote down each ruling
as recommended, and the owner's agreement is the only authority for it.

## Tiebreakers, approved once

1. Where a contract is built, the text that matches the code is live.
2. Otherwise the owner's newest dated ruling wins over older restatements.
3. Otherwise the build spec wins over the direction. `fire_solid.md` beats `fire_model.md`, and `fire_model.md`
   counts as superseding only where `fire_solid.md` is silent.
4. Otherwise the stricter reading wins. No bar loosens.

Where a later design supersedes by name, its text becomes the owner text, and the old copy becomes a link.

## The open decisions

- **Orphans.** World config's owner is `npcs_and_sem.md` §9 (row 25), and save v0's is `world_model.md` §8 (row 26).
- **Decision tables.** They move verbatim to `docs/design/decisions/<doc>.md`. Plans keep their own lists.
- **`reviews/npcs_v3/foldtable.py`.** It is retargeted to the moved fold table.

## The ✗ rows

| Row | Ruling | Ground |
|---|---|---|
| 2 | `kind_rank` 0/10/20/30, in the tile's order | owner's call; nothing reads the values yet |
| 6, 7 | Split: `sem_stimuli.md` §6.2 owns the agent receipt `(pid, kind)`; tile §3.3 owns the wire `intent_result` outcomes `applied`, `refused`, `stale`, `cancelled`. OD-A16's credit kinds are rechecked against the split before the move | owner's call |
| 8 | `kindle` derivation: tile §3.2 stays live until the flames design | 3 (flames are designed after R0–R1) |
| 18 | Stage-1 caps live in `data/world/` | 1 (no `data/server/`) |
| 22 | Refuse on mismatch for world inputs (boundaries §6.3); inference items recorded, never refused (inference_placement §4.3); boundaries states the exception | 2 |
| 24 | Timing stays in integer microseconds; ticks derived only at apply (npcs §9) | owner's call |
| 26 | Save v0 keeps F5: a newer build and a content change are refused; no in-flight thoughts, since agent state lives outside `Simulation` | owner's call |
| 28 | Scene v0 is refused by version, never migrated, as built (`src/simcore/core/scene.py`, `_V0_REFUSED`, merged in #32 as 5c054f6); tile §1.3's migration text is stale | 1 |
| 37 | The worker's `HOME`, `XDG_*` and `TMPDIR` are set under the agent home; npcs §6.6 reads "the host's `HOME` never passes through" | owner's call |
| 41 | O16 is the live interim policy; npcs §6.6's floor thresholds fold into §4.4; O11a stays a record | 2 |
| 43 | Model requests carry a deadline, not a priority. OD-A14's upstream ask is amended to match | 2 |
| 45 | The roadmap's Phase 4 wording owns the guest gates; npcs §6.6 owns the character list | 2, 4 |
| 49 | Five layers, as `pyproject.toml`: core < adapters < protocol < verify < game | 1 |
| 50 | The window's owners as built: `World.advance`, the applier, scene construction, `imagination.place` | 1 |
| 51 | `logging` is banned in the core (`pyproject.toml:116`) | 1 |
| 55 | The experiment harness is Maxim-owned (npcs §10) | owner's call |
| 59 | The Phase 1 exit is the torch-lit slab (roadmap, 2026-11-20) | 2 |
| 60 | Both rules: the band's width is gated (world_model §3), and the operating point clears the band by a margin (tile §6.3); "replaces" is dropped | 4 |
| 61 | No allowance, as `simcore/verify/agreement.py::agrees`; the tile's tol/4 is dropped | 1, 4 |
| 63, 66, 71 | `fire_solid.md` where it speaks; otherwise the text stays, marked for the flames design | 3 |
| 68 | Emission is `fire_model.md` §4.4's; the body side is `sem_stimuli.md` §2.3's; the tile's face-to-body exchange is stale | 3 |
| 72 | The thin-feature rule holds for cell geometry; fuel objects are exempt | 3 |
| 79 | `crack` keeps one meaning; the bed's second meaning is dropped. Ruled; applying it waits with row 10 (Not decided, below) | F1 |

## Rows 6 and 7, re-ruled (owner, 2026-11-21: "great!", in reply to the recommendation)

OD-A16 asks Maxim for a vocabulary; `sem_stimuli.md` §6.2 is Overdrive's v1 choice to emit only the
target-independent subset until a row defines "perceived". So the split stands: §6.2 owns the agent receipt, tile
§3.3 owns the wire `intent_result`, boundaries §7.2 and npcs §6.4 link, and OD-A16 is unchanged.

## Not decided

- **The `stale` credit rules.** boundaries §7.2 ("zero times when `stale`", "Stale is context, never credit") and
  npcs §6.4 assume the agent sees `stale`, which `sem_stimuli.md` §6.2's v1 receipt withholds. Not a receipt-shape
  copy, so left; a finding for the owner.
- **Rows 10 and 79 (channel names, `crack`'s bed meaning).** #31 merged reading `surface_glow` and `burning` live,
  recorded as provisional (`client/tests/fixtures/snapshots/FIELDS.md`), and tracked as backlog B42: the client design
  pass before step 8 (D-B2, `fire_solid.md` §5.6) decides them, and `client_rendering.md` §4.2's rows follow it.
- **The `data/server/` client cap** in `client_rendering.md` §4.3 names a directory that doesn't exist. Ruling 18
  covers only stage-1 caps.

- **CLAUDE.md's handshake line.** The author offered to make it a link only if the owner says so explicitly; that
  has not happened, so CLAUDE.md is untouched.

## Round 1 rulings (owner, 2026-11-21: "agreed overall with your recommendations")

1. **Counts:** each registry row's "restates at" is three, or one more than the largest reference outside its owner,
   with the judged references listed in `docs/design/contracts.md`.
2. **Marker lines don't count** toward a design's word budget.
3. **"A push needs no log record"** stays dropped with the pinned frame. It is an open finding for `sem_stimuli.md`
   §4.4: whether a `BoundFrame` push needs a log record.
4. **CLAUDE.md's thin-feature rule** gains its exemption: "(fuel objects excepted, `docs/design/world_model.md`
   §1.1)". Of the two options offered, the author applied this one; the alternative was making the rule a link.
5. **`imagine`:** `boundaries.md` §6.1's separate `imagine` record kind folds into `intent` when step 5a makes
   `imagine` an intent kind. This is recorded here; §6.1 changes with 5a.
6. **Superseded banners** may add their words to a record: `world_v2.md`'s 25.

## Follow-up rulings (owner, 2026-11-21: "agreed with all six")

These answer the six questions left under "Not decided", on `phase1/b36-followup`:
1. **Stale credit** is host-side. The host withholds credit from a stale intent, which its log names, so v1 receipts
   need no `stale` kind, and the "goes to the next thought's context" clauses in `boundaries.md` §7.2 and
   `npcs_and_sem.md` §6.4 are dropped. Owner: `sem_stimuli.md` §6.2.
2. **The root id and the run seed are two fields:** identity and randomness. `npcs_and_sem.md` §3.4's "root seed"
   now reads "run seed".
3. **O26 is about the tier-2 rerun:** a rerun reads the recorded replies and never re-runs a model on purged text.
   Owner: `inference_placement.md` §4.2. Tier-1 replay calls nothing.
4. **Scene versions go to whichever change lands first.** Fuel entries take the version after main's with 6.0b
   (`fire_solid.md` §5.2), and zones a later one in Phase 2. `fire_model.md` §7's fuel list, which `fire_solid.md`
   overrides, is now a link to it.
5. **A `BoundFrame` push needs no log record:** frames are derived per tick and digested (`sem_stimuli.md` Q8). The
   test that proves it is in `checklists.md`'s agent-line PR.
6. **CLAUDE.md's restated rules name their owners:** "Reconstruct, decide at the point" names `world_model.md` §3,
   and the handshake line names `boundaries.md` §5.3.
