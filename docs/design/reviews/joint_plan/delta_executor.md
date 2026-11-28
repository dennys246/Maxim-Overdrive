# Joint plan draft: Executor delta review

**Reviewed:** the staged fold on `phase3/joint-plan`, tree `a48cc3903883a28336397e1c779a5b890d8be13a` (not yet
committed; signing waits on the owner), against round 1's base `92fbe74`. The files are
`docs/maxim_upstream/joint_plan_DRAFT.md`, `decisions_entry_game_evidence_DRAFT.md` (new) and `README.md`.

**Sources:** Maxim `<maxim-clone>` at `github/main` `a584c4d0`, read only through `git show`, `git grep` and
`git log`. Overdrive `origin/main` `e6d6a7f` and `phase1/slice2-design` `7f21055`, read with `git show`. `gh` was
used read-only on `dennys246/Maxim` on 2026-11-26.

**Stop rule:** this is the last round. New findings in fold text go to the owner, not to another round.

**Counts:** of the 17 round-1 findings, 15 are `fixed` and 2 are `open`. The fold added 2 new SHOULD-FIX and
6 new NITs. It added no BLOCKER.

## Correction to my round-1 report, first

My E2 gave the measured T0 rate as "about 3 to 4 items in six weeks, roughly 0.5–0.75 a week". That was wrong in
two ways, and the fold copied it into §3:
- 4 ÷ 6 is 0.67, not 0.75.
- The one evidenced item, `1263.dn-stop`, was satisfied in `12523fd0` ("satisfy 1263.dn-stop"). That is the same
  day, 2026-10-15, as the commit that created the gate (`e0fc59e3`). So it was not progress made inside the window.
  Since the gate was created, no item has had evidence recorded. All five arms were recorded on 10-24 (`484e12ca`),
  but arms are not items. The three closed issues (#1259, #1264, #1267) are the only possible progress, and none
  has been checked against its item.

N1 below gives the arithmetic that follows from this.

## Round-1 findings: status from the staged tree

| Id | Status | Evidence in the staged tree |
|---|---|---|
| E1 | fixed | JP17 calls the flooded room "a candidate, not a link". It says liquids and oxygen are in no Overdrive phase (only `states_of_matter` research), that it is "not dateable", and that the planning session decides. The Phase 2 dates are gone. |
| E2 | fixed (N1 is new) | §3 now gives a "measured" range and an "assumed" range for 1.3.6 and 1.4.0, each with its rate. The arithmetic and the label carry new defects; see N1. |
| E3 | fixed | "7–14×" is gone. §6 item 1 calls the centring result "an uncommitted illustration … not evidence", and says step 2 measures it. |
| E4 | fixed | JP4 cites PR 0 (#1798) as already meeting 1.3.5's world-clock condition (merged 2026-11-25T06:06Z, checked). It says "PR 1a/1b in 1.3.5 only if green before the cut" and "A5 (in part)". "A6 in 1.3.6" matches `world_clock_a_pre.md` line 52 and PR 5. |
| E5 | fixed | The 1.3.6 row no longer lists scope, and B0b is gone. |
| E6 | fixed (N2 is new) | §6 item 1 now has "in the cells checked, with synthetic people and places" and "its attribution is not committed yet". The new count it adds is wrong; see N2. |
| E7 | open | JP16 drops the claim that the defect was "found from the game", and adds "no outcome effect shown (the tracker isn't persisted)". The same cell then says "it breaks Overdrive's replay rule once real Maxim runs in the NPC loop", with no consumer shown. I checked: the pseudo ids are dict keys only, and eviction sorts by time (`inference/segment_vision.py:350`), not by id. The only seed-dependent outcome I can find is a 31-bit collision, between two names or between a name and a real track id, and that is improbable. The row contradicts itself. Filing still waits on the owner's go-ahead, which limits the harm. |
| E8 | fixed | §6 item 4: "modality resolution (revives on GL3; its 'graded consumer' promotes population coding)". This matches `modality_resolution_and_alignment.md` lines 4–5 and 180 (F-B is population coding). |
| E9 | open (residual) | Fixed: the Overdrive Phase 1 and Phase 2 dates, J8's date, step 4's date, "0.5–3 days" and "±2×" are all removed, and §2 says the plan proposes no Overdrive step dates. Still open: JP13's "2026-12-04 to 12-11" gives no duration for "the fold, read and review". Its "Stage 3 ends about 2026-11-27 (measured per-cell times)" can't be reproduced from the tree: `protocol.md` records only "Stage 3's first 68 cells ran at 0.48 of the estimate", with no remaining hours and no slot count. §6 item 2's new "run in 2027-01" is N4. |
| E10 | fixed | 1.3.5 is now 12-06 to 12-22: 11-22 plus 13.5 days is 12-05.5, which rounds to 12-06, and 11-22 plus 30 days is 12-22. §2 now uses 30 days only. |
| E11 | fixed | "64–70 a week in October's first three weeks and 22–43 a week since" reproduces with 7-day windows from 10-01 UTC: 64, 70, 68, then 42, 40, 22, 22, 43. The basis isn't stated; see N8. |
| E12 | fixed (N3 is new) | JP10 now covers the Exp 64 pre-registration and OD-B1–B13. JP11 covers OD-C1–C12 and OD-I2. |
| E13 | fixed | §1 no longer lists places or says "the opposite". The decisions draft names what it amends. |
| E14 | fixed | "Game runs need no rig" is gone. JP15 carries D12's hold mark instead. |
| E15 | fixed | JP7: OD-A7 is "after the 1.4.0 cut", in 1.4.x, and OD-A15 is in the 1.5 line. |
| E16 | fixed | The quote is gone. The decisions entry paraphrases and cites `baseline_floors.md`. |
| E17 | fixed | JP2: "OD-I1, OD-I3 (and OD-I6, tooling)", needed by "Phase 4's subset; Overdrive's lock move (O78)". |

## New findings

### SHOULD-FIX

#### N1. `joint_plan_DRAFT.md::§3 Maxim 1.3.6` and `::§3 Maxim 1.4.0`: the "measured" range rests on an unmeasured rate, and its arithmetic uses unstated, mixed bases

What the tree shows (see the correction above):
- 33 items, 1 evidenced, 32 open. I re-counted `scripts/release_gates.json` at every revision from `e0fc59e3` to
  `github/main`. The three `retired` entries are functions, not items, so they don't reduce the count.
- Since the gate was created on 10-15 (six weeks), no evidence has been recorded on any item.
- Three item issues have closed, each unverified against its item: #1259 (2026-11-01T03:33Z), #1264 (11-18) and
  #1267 (11-21).

The rate the tree supports is therefore 0 to 0.5 items a week (0 to 3 in six weeks), not 0.5 to 0.75.

The draft's range reproduces only from a mix of bases:
- **Measured, 2027-09 to 2028-02.** 32 ÷ 0.75 = 42.7 weeks and 32 ÷ 0.5 = 64 weeks. Counted from **today**
  (11-26), that gives 2027-09-22 to 2028-02-17.
- **Assumed, 2027-02-01 to 04-14.** This is counted from **the old 1.3.5 range** (12-07 and 12-23, plus 8 and 16
  weeks). The fold moved 1.3.5 to 12-06 to 12-22, so the same method now gives 01-31 to 04-13.
- **Internal inconsistency.** The rate counts the three closed issues as done, but the remaining count is still 32.
  If they are done, 29 remain.

On the tree's own rate, 0.5 a week gives 64 weeks: 2028-02-17 from today, or 2028-03 after 1.3.5. A rate of 0 gives
no latest date. The honest measured row is "2028-02 at the earliest, and no latest date, since no evidence has been
recorded since 10-15". That is "not dateable", which is what §7 already proposes to fix by measuring over December.

The 1.4.0 "measured" row (2027-12 to 2028-08) adds four rungs at an unmeasured 3–6 weeks each. Its arithmetic
follows from the 1.3.6 row (12 and 24 weeks after 2027-09-22 and 2028-02-17 give 2027-12-15 and 2028-08-03). But the
word "measured" covers only the 1.3.6 part.

**Failure scenario:** Maxim's owner reads the bolded "measured: 2027-09" as T0's demonstrated pace, and sets the
1.3.6 milestone or weighs the orchestrator line's staffing from it. The earliest date the tree supports is about
five months later. The first re-forecast then reports a slip that the data never allowed. §3's conclusion, "Phase 4
is 2028", survives the correction; it gets stronger.

**Fix (unverified):**
- State the window (10-15 to 11-26) and say that no evidence was recorded in it.
- Give the measured row as "≥ 2028-02, no upper bound (0–0.5 items a week)", or as "not dateable".
- Start both rows from one basis, and recompute the assumed row from the current 1.3.5 range.
- Label 1.4.0's rung durations as assumed.

#### N2. `::§6 item 1`: "fail offline in 18 of 22 conditions" misreads its source

`7f21055`'s commit message reports the Stage 2 join as "22 conditions; 18 read row 3 and all of them fail offline,
on all three layers; 4 have no row 3". The 4 were not tested by the check. They did not pass. "18 of 22" tells a
reader that 4 of 22 passed. The bullet also drops "Stage 2 only": the join covered 82 of the 274 cells, and Stage 3's
cells wait on the full join. This bullet is the one that goes to #1810.

**Failure scenario:** Maxim's fabric owner reads a 4-in-22 pass rate and looks for the conditions under which a
summed world vector keeps identity. No such condition was observed.

**Fix (verified against the commit message):** "in all 18 of Stage 2's 22 conditions that read row 3, it fails
offline on all three layers; the other 4 have no row 3".

### NIT

- **N3 `README.md::joint_plan row`.** "plus OD-C13–C16" names ids that `joint_plan_DRAFT.md` never mentions (0
  matches). They exist only on `phase1/slice2-design` (`7f21055:docs/roadmap.md:343-346`), not on `origin/main`.
  This branch merges first, so main's README would cite rows that main doesn't have. Either name the JP links that
  carry them (OD-C14 is #1803, in JP9; C15 and C16 are #1807 and #1810, in JP8), or drop the clause.
- **N4 `::§6 item 2`.** "Designed after step 4, run in 2027-01" is an Overdrive date with no method. It contradicts
  §2's "this plan proposes no Overdrive step dates", and O79 (5) gives step order to the planning session.
- **N5 `::Ids`.** "Maxim already uses `J1`–`J7` in two documents" is wrong. At least five Maxim documents use J ids:
  - `log_url_redaction_1801_approach.md` (J1–J3, J5–J7);
  - `deferred/grounded_word_binding.md` (J1–J3);
  - `coding_world.md` (J2, J3);
  - `social_referencing.md` (J2);
  - `experiments/rationale/e1-conflict/wiring.md` (J0–J2).

  The rename to `JP` is still right; only the count is wrong.
- **N6 `decisions_entry_game_evidence_DRAFT.md::Overdrive's side`.** "Six statements of the old rule" undercounts.
  - On `origin/main`, two more live documents state the rule:
    - `docs/design/research/fire_ladder/6b_maxim_perception.md:130`, which draws a consequence from it ("so every
      experiment below runs in a Maxim-owned harness");
    - `docs/design/research/time/skeptic.md:224`.
  - On Maxim's side, the entry amends `release_1_3_5.md` D8/D13 (line 79). It doesn't name §Answers to Overdrive
    (line 330), which restates the rule.
- **N7 `decisions_entry_game_evidence_DRAFT.md::Whose words`.** It says "the ruling and its conditions 1–4 are the
  owner's". The owner's safeguards were: pre-registered with a confounding-lens review of the scenario; pinned
  before data, including the scene digest and spacing; sensed, not handed; and verified world. Some of the text is
  the author's elaboration:
  - condition 2's "reachable from its repository's public `main` or a release tag" and its clean-tree clause, which
    read "valid commits";
  - condition 3's alternative, "or the pre-registration lists each value with the source it was sensed from". This
    one allows values that don't come through the membrane, which is broader than "sensed, not handed".

  Mark these as the author's, as the draft already does for "from 1.3.6".
- **N8 `::§2`.** The PR-rate basis isn't stated. Monday weeks give 68–76 for the first three October weeks, not
  64–70. Say "7-day windows from 10-01, UTC".

## Verified as written in the fold

- **Plan size.** `joint_plan_DRAFT.md` is 1,761 words, within the 2,500-word plan budget.
- **The 1.3.5 row.** §Exit, and "Lines 3, 4 and 5 do not gate the cut" (`release_1_3_5.md` line 392). The
  milestone has no due date (66 open, 21 closed at review time).
- **Rows and plans cited by the fold.**
  - `release_1_3_5.md`:
    - JP15: D12 (line 101), line 6 item 3 (line 301), and `max_in_flight` "about 1" (lines 310 and 331).
    - JP14: M97 (lines 114 and 386).
  - `roadmap_1_3_x.md`:
    - 1.3.6's exit: release gates clear, plus B2's three prerequisites (lines 1317–1319).
    - B2 → B3 → B4 is serial and runs after the fence (lines 1309–1315 and 1390).
  - `archive/world_channel_weighting.md:223`: the set-point quote, verbatim, at the path the fold now gives.
  - Fabric: revives on GL3 (line 7); §B's register (line 250); §C's ban on familiarity lowering thresholds (lines
    276–283).
- **Overdrive ids and decisions.**
  - OD-A1 is in 1.3.6 via #1361 S3–S6 (roadmap line 273). OD-I10 cites #1782 (line 204).
  - These ranges exist on `origin/main`: OD-B1–B13, OD-C1–C12, OD-H1–H6, OD-I1–I13.
  - O79 (5) gives step order to the planning session. O10's text is quoted exactly
    (`decisions/npcs_and_sem.md:21`).
- **Overdrive's own documents.** `npcs_and_sem.md` §10 (line 1036) says behavioural claims "stay PARTIAL until a
  transfer check passes". The six statements the entry lists all exist (`CLAUDE.md:379`, `roadmap.md:489`,
  `boundaries.md:696` (§8.4), `npcs_and_sem.md:1008`, `hybrid_1_5_line_DRAFT.md:38`, README).
- **The harness clause.** `lint_harness_provenance.py`'s docstring says "stamping is detection, refusing is
  enforcement", which supports "stamping alone does not satisfy".
- **JP17.** `roadmap_1_4.md` gates E2 on a relief store (lines 100 and 378).
- **Arithmetic.** The 1.4.0 rows reproduce from their 1.3.6 rows (N1 covers what the 1.3.6 rows rest on).
  "Twelve days old" is correct (11-14 to 11-26).
