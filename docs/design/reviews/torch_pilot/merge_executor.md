# The merge round: Executor (2026-11-23)

**Lens:** Executor (`docs/code_review.md`). **Head read:** afdb849 on `phase1/torch-pilot`, against `origin/main`
b578761. **Summary:** 1 BLOCKER, 1 SHOULD-FIX, 2 NITs. Statuses are `open` until a reviewer reads the fold.

## What I checked

- **The diff the branch adds to main** (`git diff origin/main afdb849`): docs only, 31 files. No file under `src/`,
  `scripts/`, `tests/`, `data/` or `client/` differs from main, so no generated artifact (`docs/generated/`), field
  registry or golden can change, and the code half of the gate sees main's tree.
- **The four conflict resolutions** in 88a410a against `fold4.md`'s account: `fire_solid.md` §1.3's contact
  paragraph (main's text, the branch's ending), §2 (main's S0 text with TP1's exception, plus "from 6.1b"), the
  lessons file (main's 37, the branch's 38), and `roadmap.md` (the TP6 sentences beside main's write-window, port and
  `known_gaps.md` text; OD-A16 carries §31, §37 and lesson 38). Each matches the account.
- **The auto-merged files** (`sim_core.md`, `tile_and_client.md`, `fire_model.md`, `client_objects.md`,
  `contracts.md`, `checklists.md`, `standards_backlog.md`): each branch hunk lands on main's current text; I found no
  hunk that reverts a main edit. `fire_model.md` was not touched by main since the old base (aaebc1b and b578761 hold
  the same 5,449 words), so its hunks are the branch's alone.
- **The renumbering:** headings 37 and 38 are unique; `torch_pilot.md` §12 and the OD-A16 row cite 38; main's §37
  citation in OD-A16 still means main's lesson. `torch_pilot.md` §7 and §10 name `docs/known_gaps.md`.
- **Word budgets** (whole-file `wc -w`, main → head; marker lines included on both sides, so the comparison is fair
  for files whose markers didn't change): `fire_solid.md` 5,964 → 5,960, `tile_and_client.md` 5,386 → 5,382,
  `fire_model.md` 5,449 → 5,427, `client_objects.md` 5,173 → 5,158, `sim_core.md` 3,770 → 3,770. No existing design
  document grows. `torch_pilot.md` is new at 4,998 (≤ 6,000; its contract marker counted). `contracts.md` grows
  592 → 647 by one registry row and its reason, which the registry needs for the new vocabulary. `checklists.md` is
  exempt (B24, O42). `fold4.md` is 33 lines.
- **ID lints, read by hand:** decision ids TP1–TP9 occur in one log only (`grep -rln "| TP[0-9]"` finds only
  `decisions/torch_pilot.md`); no `OD-` id is added; `check_plan.py`'s regexes (`O\d+`, `OA\d+`, `OD-…`, `D\d+`,
  `T\d+`) match nothing new in the branch's text in its sources (`TP5`, `TP6`, `A-B1`, `C1`, `W1` match none), so
  `required_ids.txt` and the real-plan test see main's set.
- **The lints and the real-tree tests run:** see "Runs" at the end.
- **Main's newer text against the torch-pilot text:** `subcell_solids.md` (§2.3's acts row, §7.1's `strike` and
  `kindle` rows, §12's row), `known_gaps.md`, `generation_harness.md` U4, `sim_core.md` §5, and the step 5a PR 4a
  note in `checklists.md`.
- **The parked row** against `origin/phase1/records-layout` (read with `git show`), and `fold4.md`'s stop rule.

## BLOCKER

**E-B1. `torch_pilot.md::§3 The target` (and §7's crater bullet): "A cell region with no solid cell left is no
candidate" decides on cells, which main has since ruled out.**
Main, newer than the branch's base, says in `sim_core.md` §5 ("Strikes resolve on their own tick"; owner,
2026-11-22, `reviews/sim_tick/fold.md`): `"gone" is authored geometry only, so a strike on a destroyed region
destroys nothing`. The reason is recorded in `docs/plans/checklists.md` (the step 5a PR 4a note, Exec S2): "no solid
cell left" flips with the grid spacing (strike 29 at 0.2 m, 30 at 0.1 m on a 1.2 m wood cube). `known_gaps.md`
records the same class for a fire refused by its cells ("off the coarse grid that decision depends on the rig").
The torch pilot's §3 still makes "no solid cell left" a candidacy rule (line 102), and §7 restates it (line 219);
both predate the merge (present at 0c3f30b), and the merge brought in the ruling they contradict.
*Failure scenario:* on the 1.2 m wood cube struck 29 times, beside a fuel slab within 50 mm of the point. At 0.1 m
the cube still has a solid cell, is the nearest candidate, and the `kindle` resolves to it (applied, fruitless:
cells take no deposit). At 0.2 m the cube has none, drops out, and the same logged point resolves to the slab, which
lights. One intent log gives two outcome classes across grids: the verification rule's failure (CLAUDE.md), on the
act Phase 1's exit runs. A fresh 6.1b session must pick between §3 and sim_core §5 with no ruling to pick by, and
the receipt's effect value (the derived target) and the digest differ by grid as well.
*Fix (unverified, a contract choice for the author):* make the cell-region candidate rule follow sim_core §5's
authored-geometry "gone", or state the cell rule as a recorded exception with a Known gap and its numbers.

## SHOULD-FIX

**E-S1. `docs/roadmap.md::Phase 1, "Parked: one file per record"`: "found three BLOCKERs" understates the parked
review.** The round-1 reports on `origin/phase1/records-layout` hold eleven BLOCKERs, each under its report's
`## BLOCKER` heading: A-B1–A-B4 (`round1_architecture_bio.md`), C1–C3 (`round1_concurrency.md`) and W1–W4
(`round1_wire_executor.md`). The row names three ids for two defects and calls that the count.
*Failure scenario:* the trigger is the first step after the base tag, run as the only session. That session plans
from the roadmap row, budgets for three folds, and meets A-B2 (immutable lessons contradict CLAUDE.md), A-B3 (no
single decision namespace), C2 (a duplicate on `main` can't be fixed) and W3 (the id grammar fails on day one)
unannounced. The row is the only record on `main` of the parked state, since the branch has no PR.
*Fix (verified by `git show origin/phase1/records-layout:docs/design/reviews/records_layout/<report>.md` and its
`## BLOCKER` / `## SHOULD-FIX` headings):* give the count as eleven, with the three as examples, or link the three
reports by path.

## NIT

**E-N1. `docs/design/reviews/torch_pilot/fold4.md::The stop rule`:** "A NIT goes to a backlog row or a Known gap,
with no change to the text" has no home for a NIT that is neither a rule waiting for a check nor a physics gap
(E-N2 below is one), and a row in either file is itself a text change. The rule is also silent on a BLOCKER found by
the one permitted delta round, after which "no round runs"; the charter's stop procedure ("When the rounds stop")
asks for the owner's acceptance, which `fold4.md` doesn't record. *Scenario:* the delta round finds a BLOCKER in the
fold's text, and the author can neither leave it nor have the fix read. *Fix (unverified):* say what happens then
(fold it unread, or the owner rules).

**E-N2. `fold4.md::What changed`:** "with three conflicts" is followed by four bullets (`fire_solid.md` has two
hunks). Three files, four hunks; a reader counting bullets against the text stumbles. No other claim in the account
is wrong: I checked each against `git show 88a410a --cc` and the tree, including the three places main links to
`torch_pilot.md` §3 (it also links from `subcell_solids.md` §2.3, §7.1 and §12, which the account doesn't need to
list).

## Not findings, checked

- `subcell_solids.md` §7.1's `strike` row uses "`torch_pilot.md` §3's shared ranked query"; §3 has it ("One query,
  two policies"). §12's row ("after S1, a pilot's target follows §3.1's states and §4.3's 'gone'") is consistent with
  `torch_pilot.md` §2, which defines Phase 1's lifecycle only.
- `fire_solid.md` §2's interim rule and `subcell_solids.md` §2.3's row both except `kindle`, linking §3: one owner.
- `tile_and_client.md` §3.2 drops "when its region is gone" from the lifecycle, as `torch_pilot.md` §2 says; the
  `region_gone` refusal code stays in §3.4's registered vocabulary for the other acts.
- `generation_harness.md` U4 ("`kindle` on the object ignites if and only if it is fuel") needs sub-cell objects as
  candidates, which §3 promises when that design lands (TP1).

## Runs

- `scripts/lint_standards.py` at afdb849 (through the box waiter, without `--base`): `PASS (0 finding(s))`. It
  runs `check_ids` (decisions, roadmap ids, lessons), `check_contracts`, `check_paths`, `check_markers`,
  `check_guards`, `check_inputs` and the size checks over the tracked tree. This report was untracked at the time.
- **Not run:** `scripts/check_plan.py` and the real-tree tests (`test_check_plan.py`, `test_lint_ids.py`,
  `test_lint_contracts.py`, `test_lint_paths.py`, `test_lint_standards.py`). They waited over an hour behind other
  sessions' suites on the box and were stopped. Their verdicts here rest on reading the regexes and sources by hand
  (above), not on a run; the author's gate run settles them. The prepush `--base` ratchets (sizes, coverage) see no
  code change on this branch.
- **What only CI would catch:** nothing I found. The branch changes no code, data or generated artifact, so the
  golden, Godot and coverage jobs see main's tree; the docs lints that ran are the ones CI runs.
