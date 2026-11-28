# Joint plan draft: Architecture lens, delta round

**Tree reviewed:** `a48cc3903883a28336397e1c779a5b890d8be13a`, the staged fold on `phase3/joint-plan` over `92fbe74`
(`git diff --cached 92fbe74`). It covers `docs/maxim_upstream/joint_plan_DRAFT.md` (1,761 words, within a plan's
2,500), the new `docs/maxim_upstream/decisions_entry_game_evidence_DRAFT.md` (546 words) and
`docs/maxim_upstream/README.md`.

**Read against:** Overdrive `origin/main` `e6d6a7f`: `CLAUDE.md`, `docs/design/decisions/npcs_and_sem.md` (O10),
`docs/design/npcs_and_sem.md` §10, `docs/design/boundaries.md` §8.4, `docs/roadmap.md`,
`docs/plans/next_steps/4_records_build.md`, `docs/maxim_upstream/decisions_entry_DRAFT.md`. Also
`phase1/slice2-design` `7f21055`, and Maxim `github/main` `a584c4d0` in `<maxim-clone>`: `scripts/release_gates.json`,
`scripts/lint_harness_provenance.py`, `docs/plans/overdrive_refactor_candidates.md`, `docs/plans/release_1_3_5.md`
and `docs/plans/baseline_floors.md`. All of it was read through git only.

**Owner rulings since round 1** (the owner's, not findings): this branch merges before step 4; game data counts
only when it is pinned to valid commits of both repositories; JP1 carries four safeguards.

**Stop rule** (written before this round): this is the last round. New findings in fold text go to the owner, not to
a third round.

**Counts.** Round 1: 8 fixed, 5 open, 0 deferred, 0 rejected. (S1's Overdrive half is deferred, but the finding
stays open on its Maxim half.) New in this round: 0 BLOCKER, 4 SHOULD-FIX, 5 NIT. Every proposed fix is
**unverified**. They're paper fixes, and nothing was run apart from the `git` reads cited.

---

## 1. Round-1 findings, status read from the tree

| Id | Status | Evidence at `a48cc39` |
|---|---|---|
| A1 | **fixed** | The header says "This branch merges before Overdrive's step 4 starts (owner, 2026-11-26)". §7 says "merge this branch, then start step 4". The owner chose option (a). |
| A2 | **fixed** (in text) | The draft no longer calls the evidence run a "strict red gate". The entry amends D8/D13 and the candidates rule "except as this entry allows". The new draft's "Overdrive's side" drafts O10's amendment and names the ledger-run-versus-red-gate clash. *The vehicle for recording it is new finding D1.* |
| A3 | **fixed** | §6 step 2 reads "An exploratory ablation in Overdrive, never evidence … nothing it finds can earn a rung". Step 3 reads "designed in Maxim and run fresh on Maxim's code, in a Maxim-owned harness, on a new population generator and seeds". |
| S1 | **open** (Maxim half); Overdrive half **deferred** | Fixed in part: §2 now says "The re-forecast has no owner yet … the ranges below are a snapshot of 2026-11-26". Ranges replace dates of record, and §7 gives the Overdrive amendment to the planning session (trigger: that session, O79 (5)). Still open: §2's second amendment ("Maxim's cut checklist re-reads this plan's links (a Maxim process item)") has no item in §7's Maxim list, so half of the admitted gap has no action. |
| S2 | **open** | The Overdrive record now waits for "at step 4", which step 4's brief doesn't allow (D1). Until then `CLAUDE.md` line 379 still says "Game runs never go on Maxim's results ledger", unconditionally, with no pending note. The README still words the rule as one that depends on a Maxim event ("until Maxim records the owner's ruling"), and it drops the ruling's pinning condition. |
| S3 | **open** | The header now disclaims status ("Status and scope belong to the rows and plans each link cites"), but the table still carries it: JP2 "#1773, merged", JP3 "#1782 (closed)", JP4 "PR 0 (#1798) already meets 1.3.5's world-clock condition". §6 step 1 still states the probe's numbers (0.016, 0.85, "18 of 22"). Only one of them is pinned (`7f21055`), and "18 of 22" appears in no prose file under `person_reid_probe/` at `7f21055` (only cell JSON matches 0.016). |
| S4 | **open** (narrow) | §7's "add rows at step 4" is gone (fixed). But §2 now says "roadmap rows cite `JP` ids rather than copying dates", which is the opposite of the fix: the J table should cite `OD-` ids, and JP ids stay outside `lint_ids`' families. JP8, JP9 and JP13 still don't name OD-C13 to OD-C16 (zero matches in the plan), although the README row claims they do (D5). JP16 (`hash()`) and JP17 are still not Phase 3 items, which CLAUDE.md's "Push back on Maxim" requires. |
| S5 | **open** | JP17 now says "a harness would have to go through the membrane", and the entry's condition 3 names the membrane. But condition 3's alternative reopens the bypass (D3). |
| S6 | **fixed** | §2 reads "this plan proposes no Overdrive step dates", and §8 reads "Overdrive's step order and Phase dates … belong to its planning session". J10's 2027-01 design date and the Phase 2 dates are gone. The residue is D9. |
| N1 | **fixed** | The ids are now `JP1`–`JP17`. `git grep -w 'JP[0-9]+'` finds no match in Maxim `a584c4d0` or Overdrive `e6d6a7f`. |
| N2 | **fixed** | The ruling has its own draft, `decisions_entry_game_evidence_DRAFT.md`, with its own README row. |
| N3 | **fixed** | §8 no longer restates the step 4 freeze. |
| N4 | **fixed** | JP13 names `phase1/slice2-design`, §6 step 1 pins `7f21055`, and `sem_stimuli.md` resolves on `main`. |

---

## 2. New findings in the fold

### SHOULD-FIX

#### D1. `joint_plan_DRAFT.md::§7` and `decisions_entry_game_evidence_DRAFT.md::"Overdrive's side"`: "at step 4, record the ruling and O10's amendment" falls outside step 4's brief

The fold moved S2's record to step 4, which brings back S4's defect class. Step 4's brief (`4_records_build.md`) says
"Don't redesign". Its "Files you may touch" list covers migration files, and `CLAUDE.md` gets "two changes … and no
other". An owner ruling that amends O10, `npcs_and_sem.md` §10 and `CLAUDE.md`'s ledger sentence is new content,
not migration. The entry draft goes further and spreads six edits across "each in its owner's step", which names no
step and no trigger.

**Failure scenario.** The step 4 session reads §7, checks its brief, and refuses. Or it complies, and the
migration commit then carries a decision that no review of step 4 covered. Either way, O10 and `CLAUDE.md` still
forbid what the plan and Maxim's entry allow. The cross-repository contradiction that A2 named persists for as long
as it takes someone to pick the item up.

**Fix (unverified).** Choose one and write it into §7: (a) the owner amends step 4's brief to add the O10 row,
`npcs_and_sem.md` §10's pins and `CLAUDE.md`'s ledger sentence; or (b) the first session after step 4 merges records
them, with a named owner. In both cases, list the six edits with the session that makes them.

#### D2. `decisions_entry_game_evidence_DRAFT.md::condition 2`: two owners of what an evidence run pins, with lists that differ

Overdrive's `npcs_and_sem.md` §10 already owns the ledger record's pins: "the engine SHA, the pymaxim version, the
membrane and agent contract versions …, the placement digests …, and the Phase 3 items present". Condition 2 states
a different list: the Maxim commit, the Overdrive commit, the scene digest and the grid spacing. The Overdrive side
then says §10 "gains the pins of condition 2". So the pin list would live in a Maxim `DECISIONS.md` entry and an
Overdrive design section at once, and neither cites the other as its owner.

**Failure scenario.** A prereg meets condition 2 exactly, and Maxim's DESIGN_REVIEW accepts it. It doesn't pin the
membrane contract version or the placement digests, which §10 requires and which change the treatment ("any interim
`neutral` behaviour … is part of the treatment"). The run counts in Maxim. In Overdrive it is unreproducible
against the contract the game says it ran under. When §10 later adds a pin, Maxim's entry, an append-only record,
can't follow.

**Fix (unverified).** Condition 2 keeps the principle: both commits must be reachable from a public `main` or a tag,
with clean trees. It delegates the rest of the list to the world's published pin contract (§10). Alternatively,
the owner rules that Maxim's entry owns the list and §10 cites it. Either way, one owner.

#### D3. `decisions_entry_game_evidence_DRAFT.md::condition 3`: the "or the pre-registration lists each value" clause reopens S5's bypass

Condition 3 reads: "through Overdrive's membrane …, **or** the pre-registration lists each value with the source it
was sensed from". The second branch lets a Maxim harness read world fields directly, with line 3's bypass of the SEM
adapter, provided the prereg lists them. That is the second owner of the stimulus mapping S5 named. It also
contradicts JP17 ("a harness would have to go through the membrane"). "The source it was sensed from" is undefined
outside the membrane, because the membrane is where Overdrive defines sensing: reductions over volumes in metres,
sites, cadence and leak rules (`sem_stimuli.md`).

**Failure scenario.** An E2 prereg lists "`is_in_water`: the head cell's liquid fraction". The four-lens review
accepts it, because the condition allows a list. The reading is a cell-centre threshold on a mean, which
CLAUDE.md's resolution rule bans and `sem_stimuli.md` would not emit. A ledger result rests on it.

**Fix (unverified).** Drop the alternative. If a value has no membrane channel yet, the run waits for one, or the
channel is added to `sem_stimuli.md` through Overdrive's process first.

#### D4. `decisions_entry_game_evidence_DRAFT.md::"What it amends"` and "Six statements": the amendment list misses a Maxim-bound statement of the old rule

`docs/maxim_upstream/decisions_entry_DRAFT.md` decision 4 reads "Game runs never go on the results ledger". It is a
`DECISIONS.md` entry for Maxim that its README marks "its question answered yes (Maxim's owner, 2026-11-19)". Neither
the new entry's "What it amends" nor Overdrive's "six statements" names it. Maxim's `release_1_3_5.md:330` restates
the rule with O10 too. Both are covered only indirectly, through D8/D13.

**Failure scenario.** Both entries get filed. Maxim's `DECISIONS.md` then holds a 2026-11-16 entry that says game
runs never go on the ledger and a 2026-11-26 entry that says they may. The later entry amends neither by name, so a
reviewer can't tell which one binds.

**Fix (unverified).** Add the 2026-11-16 entry's decision 4 (once it's filed, by its Maxim heading) to "What it
amends", and add `decisions_entry_DRAFT.md` to Overdrive's list, making seven statements. Count again with `git grep`
before filing.

### NIT

- **D5. `README.md` (the joint plan's row):** it says "links JP1–JP17: every draft above, plus OD-C13–C16". The plan
  contains no `OD-C13` to `OD-C16`. Either map JP8, JP9 and JP13 to those ids (S4's fix) or drop the claim.
- **D6. `joint_plan_DRAFT.md::§7`:** "measure T0's rate over December" names no owner and no place for the result,
  so no one can verify that it happened. Also, §2's Maxim cut-checklist amendment is missing from §7 (S1). Give each
  Maxim item its vehicle, such as an issue or the 1.3.5 plan's sessions table.
- **D7. `joint_plan_DRAFT.md` header:** "Nothing here is committed in either repository" becomes false once §7's
  first Overdrive item merges the file into Overdrive. Say "nothing here is a commitment of either repository".
- **D8. `decisions_entry_game_evidence_DRAFT.md`:** "(stamping alone does not satisfy `lint_harness_provenance.py`)"
  implies that the lint covers the imported `simcore`. At `a584c4d0` it checks `assert_repo_interpreter` and Maxim's
  own checkout, and nothing in it names an embedded engine. State that the simcore assertion is a new harness
  requirement, not one an existing lint enforces.
- **D9. `joint_plan_DRAFT.md::§6` step 2:** "Designed after step 4, run in 2027-01" is an Overdrive step date, against
  §2's "this plan proposes no Overdrive step dates". Mark it as an input to the planning session.

---

## 3. The asked checks

- **Ownership.** The fold fixed one duplication (N2) and introduced two: the pin list (D2) and the stimulus contract
  (D3). Status copies remain (S3). The entry correctly defers the transfer-check venue to the candidates plan's
  §Not decided here, which matches `overdrive_refactor_candidates.md:401,453`. Its PARTIAL clause matches
  `npcs_and_sem.md` §10's last paragraph. Neither restates a rule; both cite it.
- **Record freeze.** No record file is touched (the diff covers only `docs/maxim_upstream/` and the review reports),
  and the branch merges before step 4. The freeze holds for this branch. D1 is the one place the plan hands a record
  to step 4 that step 4 can't take.
- **Repo boundary.** It holds. Every Maxim item has a Maxim vehicle, and the ablation is labelled exploratory and
  Overdrive's. The new draft sensibly splits Maxim's entry from "Overdrive's side", and it is written for Maxim's
  owner to edit, with the author's proposal ("from 1.3.6") marked as such. Verified citations: `baseline_floors.md`,
  `lint_harness_provenance.py`, `release_gates.json` (33 items, 1 with evidence, 3 retired, file last changed
  2026-10-24), and the candidates plan's opening rule at line 8. The gate key in `release_gates.json` is `1.4.0`.
  §3's reading that 1.3.6's exit is T0's items relies on `roadmap_1_4.md:13` ("the point at which T0 can pass"), and
  it stands.
- **§2's admitted gap.** It is handled honestly. The plan says in plain words that the re-forecast has no owner,
  downgrades every date to a dated snapshot, and names the two amendments that would close the gap. Only the Overdrive
  amendment has an action item (S1, D6), and nothing marks the snapshot stale when a range passes. The remaining
  dishonesty risk is a reader treating "2026-12-06 to 12-22" as live after 12-22. A one-line "re-read before acting
  after <date>" would close it. That's optional.
- **§7's verifiability.** Of nine items, six can be checked against a tree or GitHub: file JP1, the milestone due date,
  #1803, the merge, approval to file JP16, and the planning session's two items. One can't be done as written:
  "at step 4, record …" (D1). One has no owner or output: T0's rate (D6). The Overdrive half of the six-statement
  rollout has no item at all (D1, D4).

## 4. Top items for the owner

1. **D1:** decide where the ruling's Overdrive record and O10's amendment are made: an amendment to step 4's brief,
   or the first session after it. Until then, `CLAUDE.md` contradicts the ruling.
2. **D2 and D3:** before JP1 is filed, make condition 2 defer to one pin contract and strike condition 3's
   alternative. Once filed, a Maxim `DECISIONS.md` entry is hard to change.
3. **D4:** add the 2026-11-16 entry's decision 4 to what JP1 amends, so Maxim's log doesn't hold two contradicting
   entries.
4. **S3 and S4:** these remain open from round 1. Status copies in JP2–JP4 and §6, and §2's "roadmap rows cite JP
   ids", are cheap to fold, or the owner can accept them as a snapshot.
