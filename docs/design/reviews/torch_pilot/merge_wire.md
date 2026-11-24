# The merge round, Wire integrity (2026-11-23)

**Lens:** Wire integrity (`docs/code_review.md`). **Head read:** `afdb849` on `phase1/torch-pilot` (merges 88a410a of
main at 7500a85 and 2728425 of main at b578761; afdb849's parked row and `fold4.md`).
**Summary:** 0 BLOCKER, 3 SHOULD-FIX, 2 NIT. Statuses are `open`: this report folds nothing.

**How it was read:** `git diff 7500a85 88a410a`, `git diff b578761 afdb849`, `git diff 88a410a afdb849` and
`git show` of `origin/phase1/records-layout` (35cec7b); greps over the merged tree's `src/`, `tests/`, `data/`,
`docs/generated/`, `client/tests/fixtures/wire/` and `docs/`; a script that resolved every `<doc>.md §N` cited in the
branch's added lines against the headings of the merged tree (85 citations, all resolve); `gh pr list --head
phase1/records-layout` (no PR). Lints, through the box's waiter: `scripts/lint_ids.py` exit 0 with no output. `lint_contracts`, `lint_markers`,
`lint_paths` and `lint_standards` were queued and not run: the waiter's check queue held them for over 30 minutes, and
I stopped them. The markers and `pilot.fields` rows below are read by hand, not linted.

## Contracts the merges touch

| Contract | Owner | Producers / consumers on the merged tree | What each gets, before → after the merge |
|---|---|---|---|
| Pilots table on the wire (tile §2.2) | `tile_and_client.md` §2.2, TP5 | none in code; consumers: step 5b's checklist ("The pilots table"), TP5 ("frozen in step 7") | before: no shipped grammar. After: step 7's v0 grammar shipped with dtypes `u8 u16 u32 f16 f32` only (`protocol/catalogue.py::DTYPES`), "a new one bumps the protocol". See W-S2 |
| Refusal codes | `tile_and_client.md` §3.4; `core/refusals.py` | `ambiguous_point`, `not_on_surface`, `over_item_max`, `pilot_live`, `restrike_wait` all in `RefusalCode` and pinned by `tests/test_refusals.py` | unchanged; holds |
| `LogRecord` key (`actor_id`, `seq`) | `boundaries.md` §6.2 | `core/intents.py::LogRecord` bounds both to u32 | the pilot record's u32 `actor_id`/`seq` and tile §2.2's columns agree; holds |
| Per-tick digest members (sim_core §9) | `sim_core.md` §9 | not built (`simulation.py`'s docstring: "the per-tick digest" is still to come); `core/digest.py` is c14n-1, a different scheme | member 6 is a design addition with no code to disagree with; holds |
| Inputs registry (sim_core §6) | `sim_core.md` §6, `core/fields.py::INPUTS` | `INPUTS` has `sources`, `source_exposure`, `loads`; `docs/generated/fields.md` is generated from code | pilots is declared for 6.1b; the generated file is not affected; holds |
| `pilot.fields` vocabulary | `torch_pilot.md` §2 (contracts registry row) | tile §2.2 shares five names; registry threshold 6 with the reason recorded | holds by reading; not linted (see above) |
| `ignite` red gates (torch §9.4) | `torch_pilot.md` §9.4 | `tests/test_cross_tier.py`, `tests/test_act_validation.py` | three of four names resolve; one was renamed on main. See W-S1 |
| `TEMPORARY` markers | CLAUDE.md, `docs/roadmap.md` Phase 1 | `simulation.py:98`, `imagination.py:159`, `bridge.py:192`, `data/world/actions.yaml:7` | each file is listed under Phase 1; the frame-0 bullet came from #59 intact. See W-N1 for `actions.yaml`'s text |
| Lesson numbers | `docs/lessons_maxim_in_games.md` | lesson 37 (main's port read-back) and 38 (the branch's held act), each once | OD-A16's "§37" means main's 37, correctly; "lesson 38" in OD-A16 and `torch_pilot.md` §12 resolve; holds |
| `OD-` ids | `docs/roadmap.md` | OD-A16, A18, A20, C5, C8 each defined once | holds; OD-C11 is unresolved, pre-existing on main (W-N2) |
| Parked row | `docs/roadmap.md` Phase 1 | `origin/phase1/records-layout` reviews | See W-S3 |

## SHOULD-FIX

### W-S1, `docs/design/torch_pilot.md::§9.4`: a red gate cited under a name main has since renamed

§9.4 lists the four `ignite` red gates that close by deletion at 6.1b. The fourth is cited as
`test_the_crate_is_badly_burned_at_the_same_turn_at_every_rig`. On the merged tree the test is
`tests/test_cross_tier.py::test_the_crate_is_badly_burned_at_the_same_time_at_every_rig` (renamed on main by 336eee8,
which 7500a85 contains and 0c3f30b doesn't); `docs/known_gaps.md:14` cites the new name. `grep -rn same_turn_at_every_rig`
over `docs/`, `src/` and `tests/` finds only `torch_pilot.md:299`.

*Failure scenario:* 6.1b's author closes "each gate and Known gap by that deletion, recorded" from §9.4's list; a
search for the cited name finds nothing, so the crate gate's closure is missed or recorded against a name no test has,
and the gate (whose reason still says the fix is the reconstructed burn rate) is left in an unknown state. The merge's
own question, "did every citation move", is exactly this case: a rename on one side, a citation on the other, no
textual conflict. *Fix (verified by grep):* the new name at `torch_pilot.md:299`; no other occurrence needs it.

### W-S2, `docs/design/tile_and_client.md::§2.2` (and TP5): the pilots row doesn't fit the v0 wire step 7 shipped

The merge brought in step 7's frame grammar (14a4ae3, in 7500a85, not in 0c3f30b). Three of the branch's claims about
that wire no longer hold on the merged tree:
- **The dtype.** tile §2.2 gives `centre_mm` as 3 × i32. `src/simcore/protocol/catalogue.py::DTYPES` is
  `u8, u16, u32, f16, f32`, and its docstring and `client_rendering.md` §4 say a new dtype bumps the protocol;
  `frame_header.py` refuses any other dtype (`Choice(tuple(DTYPES))`), and `docs/generated/protocol.md` shows the same
  closed list. The row as written can't be sent in v0.
- **"Frozen in step 7."** TP5 (`decisions/torch_pilot.md`) says the row's columns are frozen in step 7. Step 7's
  checklist on the merged tree (`docs/plans/checklists.md`, "Step 7") lists what landed and what remains, and the
  pilots table is in neither; it sits under step 5b ("The pilots table and `path_version`").
- **The tick bound.** tile §2.2: "A tick past 2³² − 1 is outside v0; step 7 names the refusal." Step 7's remaining
  list has no such item, and the shipped header's `tick` is `Whole(lo=0, hi=2⁵³−1)`, so nothing on the tree owns the
  refusal for a u32 `end_tick` column.

*Failure scenario:* 5b builds the pilots table to tile §2.2 and either can't encode `centre_mm`, or adds `i32` without
the protocol bump the extension rule requires, which every client fixture's version check then misses; and a long
session's `end_tick` wraps in a u32 column with no refusal anywhere. (The actor table's `pos_mm`, `body_temp_mk`,
`energy` and `dose` are i32 on main too: the same gap, pre-existing, not this branch's.) *Fix (unverified; a contract
question for the owner of tile §2.2, not designed here):* state the row against v0's dtypes or name the bump, and point
the freeze and the tick refusal at the step whose checklist carries them.

### W-S3, `docs/roadmap.md::Phase 1, "Parked: one file per record"`: the BLOCKER count is wrong

The row says round 1 "found three BLOCKERs, none folded", naming A-B1, C1 and W1. The three reports on
`origin/phase1/records-layout` (35cec7b) list eleven: A-B1–A-B4 (`round1_architecture_bio.md`), C1–C3
(`round1_concurrency.md`) and W1–W4 (`round1_wire_executor.md`). C1 and W1 are the same defect, so ten distinct. The rest
of the row checks out: the branch is pushed with no PR, the design's scope matches its §0 ("each record its own file,
generates every index, detects id collisions mechanically"), none is folded (each report says "statuses are unset"),
and A-B1 and C1/W1 are described accurately. The owner's ruling has no record in this tree beyond the row itself.

*Failure scenario:* the session the trigger names reads "three BLOCKERs" as the size of the remaining work and plans
a short fold, missing that immutable lessons contradict CLAUDE.md (A-B2), decisions have no single id namespace
(A-B3, W4), a duplicate on main can't be fixed under the design's own rule (C2), `renumber` silently moves another
branch's citation (C3, W2) and the id grammar fails on the current tree (W3). Those set whether the design survives,
not just its fold. *Fix (verified against the three reports):* "eleven BLOCKERs (ten distinct), none folded", with the
two named as the central ones, or a pointer to the reports instead of a count.

## NIT

- **W-N1, `data/world/actions.yaml:7` against `docs/roadmap.md` Phase 1:** the marker says the ceilings' real fix is
  "the Phase 1 fuel model … the ceilings are then set from that model", and cites "docs/architecture.md, Known gaps",
  which moved to `docs/known_gaps.md`. The roadmap now says 6.1b removes the band-aid and `torch_pilot.md` §10 replaces
  the ceilings with §6's. The marker's reason is main's text, not the merge's, and the lint only checks phase and file;
  6.1b rewrites the file anyway. Scenario: a reader of the marker looks for the fix in the wrong place until 6.1b.
- **W-N2, `docs/design/tile_and_client.md::§2.3, §3.1, §8, §10`:** `OD-C11` is cited four times and defined nowhere in
  `docs/roadmap.md`. Pre-existing on main (7500a85 has the same four citations and no row); not caused by the merges.
  Recorded because the lens asked whether every id resolves.

## Checked and holding

- The conflict resolutions in `fire_solid.md` §1.3 and §2 read as one text: main's S0 wording with the branch's
  "from 6.1b" and "6.1b's `kindle` uses geometry"; `fuel_only_region` appears only in `subcell_solids.md`'s applied
  rows, as dropped.
- Auto-merged `sim_core.md` §6 and §9, `fire_model.md` §5.4 and §10.2, `client_objects.md` §5.4 and §7.3,
  `contracts.md`, `checklists.md` (5b, 6, 8, 9) and B30: each sentence the branch added resolves on the merged tree,
  and none contradicts code. The claims about unbuilt things (the solid resolver, digest member 6, the pilots save) are
  stated as 6.1b's or step 9's.
- `tile_and_client.md` §3.4's refusal contract still lists `region_gone`; the branch dropped only the lifecycle's
  "when its region is gone", which is a pilot-ending rule, not the code.
- `torch_pilot.md` §10's table resolves (`tests/test_act_validation.py::test_every_verification_grid_is_at_least_as_fine_as_the_smallest_action`,
  `tests/test_deposit.py`, `test_exposure.py`, every `§N` it names). `fold4.md`'s claim that main links `torch_pilot.md` §3
  from `fire_solid.md` §2, `generation_harness.md` and `reviews/subcell_solids/fold2.md` holds at b578761 (`subcell_solids.md`
  lines 72 and 236 link it too).
