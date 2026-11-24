# The merge round's delta: Architecture, Wire integrity and Executor (2026-11-23)

**Lenses:** Architecture, Wire integrity and Executor together (`docs/code_review.md`). **Diff read:**
`git diff afdb849 8710f4c` (4a9e5e8 and 8710f4c) only. **Head read:** aa49c52 on `phase1/torch-pilot`, against
`origin/main` b578761 (fetched; unchanged).
**Count:** of the 15 prior findings, 9 fixed, 4 deferred, 2 rejected, 0 open. New: 0 BLOCKER, 0 SHOULD-FIX, 4 NIT.

## Statuses

| Id | Status | Evidence |
|---|---|---|
| A-B1 | fixed | `torch_pilot.md` §3 now reads "a candidate until authored geometry (a later paint) has taken every cell, as the applier's 'gone' is (TP10). Destruction never removes one". That is TP10's text, and it is what `src/simcore/core/applier.py::_check_region` does: it refuses `region_gone` on `not regions[region].cells.any()`, and a region's mask loses cells only to `MaterialGrid._take_cells` (a later paint), never to `MaterialGrid.destroy`, which sets `material` and `integrity` and leaves the masks alone. §7's gap is restated to match. The 29/30-strike cube is now a candidate at both grids, so the finding's scenario resolves the same way at every spacing. `grep "solid cell left"` over `docs/` (reviews excluded), `src/` and `tests/` finds only the step-5a note in `checklists.md` that records why the old predicate was dropped. |
| E-B1 | fixed | The same defect and the same text as A-B1. |
| A-S1 | fixed | §9.4 cites `test_the_crate_is_badly_burned_at_the_same_time_at_every_rig`, which is `tests/test_cross_tier.py:113`. `same_turn_at` no longer appears outside review reports. `core/deposit.py::Deposit` exists (line 63), and its docstring describes the fallback into air that §9.4 names. `grep _power_field` finds no live design text beyond `sim_core.md` §2's "minus `_power_field`" and records (TP6's row, research notes, the PR 4a checklist note). See D-N1 for one consequence of the rename. |
| W-S1 | fixed | Same as A-S1's test rename. |
| A-S2 | fixed | The parked row in `docs/roadmap.md` says eleven, and names A-B1–A-B4, C1–C3 and W1–W4. I read `origin/phase1/records-layout` at 35cec7b: the three reports' `## BLOCKER` sections hold exactly A-B1–A-B4, C1–C3 and W1–W4. The row's "C1 and W1 are one defect" matches the Wire report's own note. |
| W-S3 | fixed | Same as A-S2. |
| E-S1 | fixed | Same as A-S2. |
| A-S3 | deferred | The defect stands in main's text: `generation_harness.md`'s U4 row still says "`kindle` on the object ignites if and only if it is fuel" and cites `torch_pilot.md` §3. The fold put the pointer A-S3 asked for into step 6's tests to write in `checklists.md`: "U4 … judges ignition with §5's pilot condition, so a hold short of the band or a burnt-out target is no engine defect". **Reason:** the U4 row belongs to `generation_harness.md`, which this branch doesn't edit. **Trigger:** U4 leaves `not_run` at 6.1b. At that point its row's predicate and its citation (§5 as well as §3) are edited by U4's owner. The checklist bullet doesn't say that the row itself must change, so 6.1b has to read the bullet as an instruction to edit the row. |
| W-S2 | fixed | Tile §2.2 now says "5b ships it with an `i32` dtype, a protocol bump and a refusal for ticks past 2³² − 1 (TP11)". The 5b checklist says the same ("The pilots table brings the wire's `i32` dtype, a protocol bump and the refusal of a tick past 2³² − 1"). Both match TP11. `src/simcore/protocol/catalogue.py::DTYPES` is still `u8 u16 u32 f16 f32`, which agrees with TP11's "step 7's shipped catalogue has no `i32`", and the addition is placed where the extension rule requires a bump. The step-7 claim is gone from tile §2.2. TP5's row still says it, which is D-N2. |
| A-N1 | deferred | Recorded in `fold4.md` with a trigger: the planning session after the tag, which restates the roadmap. The trigger relies on the same undefined "tag" that the NIT names. That is acceptable for a NIT, but whoever runs that session has to define the tag first. |
| A-N2 | rejected | Author's reason, which I accept: "three conflicts" counts files (`fire_solid.md`, the lessons file, `roadmap.md`), and the four bullets are hunks. `fold4.md` says so. |
| E-N2 | rejected | Same as A-N2. |
| W-N1 | deferred | Recorded in `fold4.md`. The marker at `data/world/actions.yaml:7` is main's text, and **trigger:** 6.1b removes it (`torch_pilot.md` §10's `actions.yaml` row). |
| W-N2 | deferred | Recorded in `fold4.md`. `OD-C11` is main's text and still undefined, with the planning session as **trigger**. |
| E-N1 | fixed | `fold4.md` (at aa49c52, outside the diff) now says that a BLOCKER found by this round goes to the owner. On the NIT half, it records the NITs in `fold4.md` itself, and says openly that neither a backlog row nor a Known gap fits them. That departs from its own stop rule as written, but it is stated, not hidden. The owner's acceptance of the stop rule is the author's account. No tree record of it exists, and I can't check it. |

## New findings

None is a BLOCKER, so none goes to the owner under the stop rule.

**D-N1 (NIT). `docs/design/fire_solid.md::§2` (the consumer table's `Deposit` row) and `::§3.1` ("The guard")
against `torch_pilot.md::§9.4`.**
After the rename, §9.4 says 6.1b deletes `Deposit`. `fire_solid.md` §2's table gives `Deposit` as "unchanged;
guarded (§3.1)" for 6.0–6.1, and §3.1's air-power guard exempts "`Deposit`'s fallback" by name. `torch_pilot.md` §10
lists no edit to either line. The meaning isn't new: `_power_field` was the same mechanism before it moved to
`deposit.py`. The rename makes the disagreement visible.
*Scenario:* 6.1b deletes `Deposit` and its gate as §9.4 says. `fire_solid.md` §3.1 then still names an exception
for a class that doesn't exist, and §2's table says the class survives 6.1. A 6.1b author who reads `fire_solid.md`
first keeps a deposit path that §9.4 deletes. Harm is low, because the deletion only makes the guard stricter.
*Trigger:* 6.1b. *Fix (unverified):* §10's `fire_solid` row names those two lines.

**D-N2 (NIT). `docs/design/decisions/torch_pilot.md::TP5`.**
TP5 still reads "frozen in step 7", with status `live`. TP11 moves the table to 5b and keeps TP5's layout. The log
has a convention for amending a row (`decisions/boundaries.md` O2: "superseded by O6"), and TP5 doesn't use it. Tile
§2.2 cites both TP5 and TP11.
*Scenario:* a reader who follows tile §2.2's "(TP5)" to the log reads "frozen in step 7". If TP11 isn't read, the
pilots table gets planned into step 7's remaining list, and that list doesn't carry the `i32` bump.
*Trigger:* the next edit to the log. Whether a partly superseded row says so is the log owner's call.

**D-N3 (NIT). `docs/design/tile_and_client.md::§2.2` and `docs/plans/checklists.md::Step 5b`: "the refusal of a
tick past 2³² − 1" doesn't say what is refused, or with which code.**
Possible readings: `Simulation.step` refusing to advance, the encoder refusing a frame, or a `kindle` whose
`end_tick` would overflow being refused. The refusal codes are a registered vocabulary (tile §3.4's
`<!-- contract: refusal.codes` marker), and none was added.
*Scenario:* 5b picks one reading, and a later step assumes another. One ships a refusal code outside the registered
list, or a frame with a wrapped `end_tick`. In practice this can't happen: at `tick_us = 100_000`
(`simulation.py:46`), 2³² ticks is about 13.6 years of world time.
*Trigger:* 5b, as a test to write. This is a mechanism; the owner ruled the contract (TP11).

**D-N4 (NIT). `docs/design/torch_pilot.md::§3`: "as the applier's 'gone' is" points at a definition that main
plans to change.**
`subcell_solids.md` §4.3 (main's text) says "A region is gone when it has no live cell and no object in state `live`
or `failed`. `applier._check_region` follows this rule (§12)". `fire_solid.md` §2's table carries that change into
6.0–6.1.
*Scenario:* if "live cell" is read as a surviving solid cell, the applier's "gone" becomes destruction-based again
at that step. §3's two clauses then disagree: a later paint taking every cell versus whatever the applier does. On
the struck cube the grid-dependence returns. TP10's "destruction never removes one" and `sim_core.md` §5.1's ruling
settle the reading, so a reader has a ruling to choose by. The Architecture report's "Outside this round's scope"
note already named the inconsistency in main's text.
*Trigger:* the step that makes `_check_region` follow `subcell_solids.md` §4.3. Its author reads "live" as
authored, per TP10.

## Checked and holding

- **Word budgets against `origin/main`** (whole-file `wc -w`, with `<!-- contract:` lines dropped on both sides):
  - `tile_and_client.md`: 5,304 on main, 5,299 at afdb849, 5,304 at 8710f4c. It is level with main, so it doesn't
    grow, but it has no room left: one more word in a later fold breaks the budget.
  - `torch_pilot.md` is new: 4,995 (≤ 6,000).
  - `decisions/torch_pilot.md` is new: 524.
  - `roadmap.md` grows by 11 in the fold. It isn't a design document.
  - `checklists.md` is exempt (B24).
- **TP10 and TP11** are the last two rows of the log, dated 2026-11-23, status `live`. Each owner section they name
  (`torch_pilot.md` §3 and `tile_and_client.md` §2.2) carries the ruling and links it.
- **No contract is stated twice.** The pilots table's dtype and bump are stated in tile §2.2 and listed in 5b's
  checklist as work, which is allowed. §7's gap links TP10 and doesn't restate §3's rule.
- **The fold's other edits:** §0's "TP1–TP11"; "rounded half to even from metres" (the unrounded `centre_m` of §2
  stands); and the 6.1b checklist bullet "a cell region destroyed to its last cell stays a candidate at every grid
  (TP10)", which is a test that can fail (put back the old predicate and the 0.2 m run refuses).

## What I ran

- `git diff afdb849 8710f4c` and `git show` at aa49c52 of the touched files.
- `git show origin/phase1/records-layout:docs/design/reviews/records_layout/<report>.md` for each of the three reports.
- Greps over `docs/`, `src/` and `tests/` for "solid cell left", `same_turn_at`, `_power_field`, `Deposit`, "gone"
  and "step 7".
- Read `applier.py::_check_region`, `grid.py::destroy`, `_take_cells`, `scene.py::_check_no_solid_overlaps`,
  `catalogue.py::DTYPES` and `deposit.py`.
- `wc -w` at three revisions.
- `.venv/bin/python scripts/lint_standards.py`: exit 0, `PASS (0 finding(s))`.
- `.venv/bin/python scripts/check_plan.py`: exit 0, `PASS (0 finding(s))`.
- Both lints ran with this report untracked.

I edited nothing except this file. No test suite or prepush ran.
