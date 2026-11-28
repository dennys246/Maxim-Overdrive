# Joint plan draft: Architecture lens

**Commit reviewed:** `92fbe74` on `phase3/joint-plan` (diff `origin/main...HEAD`, base `e6d6a7f`):
`docs/maxim_upstream/joint_plan_DRAFT.md` (new, 2,336 words, within a plan's 2,500) and
`docs/maxim_upstream/README.md`.

**Read against:** Overdrive `origin/main` `e6d6a7f` (O10, O77, O79, O81, the step 3, 4 and 5 briefs in
`docs/plans/next_steps/`, `docs/roadmap.md`, `docs/design/records_layout.md`), the unmerged branches
`phase1/slice2-design` `7f21055` and `phase1/regions-design` `ea5b1c7` (git only), and Maxim `github/main`
`a584c4d0` in `<maxim-clone>` (git only): `docs/plans/release_1_3_5.md` D8/D13 and line 3,
`docs/plans/overdrive_refactor_candidates.md`, `src/maxim/salience/novelty.py`.

**Counts:** 3 BLOCKER, 6 SHOULD-FIX, 4 NIT. Every proposed fix is **unverified** (it's a paper fix, and nothing was
run apart from the `git` reads cited).

---

## BLOCKER

### A1. `joint_plan_DRAFT.md::§7`, `§8`: this branch is a third open session that step 4's brief doesn't allow, and §7 tells the owner to start step 4 while it's open

Step 4's brief (`docs/plans/next_steps/4_records_build.md`, lines 3–7) says "no other session may be open while
you migrate". The session has to confirm that with the owner and check `gh pr list --state open` and
`git worktree list` itself. It names exactly two exceptions, `phase1/regions-design` and `phase1/slice2-design`, plus
step 5's slice branch under O81. `phase3/joint-plan` is none of these. §7 says "start step 4" this week, and §3 puts
step 4 at 2026-11-27 to 12-03, which starts tomorrow. §8 restates the freeze but doesn't count this branch against
it.

**Failure scenario.** The owner follows §7 and starts step 4 tomorrow. The step 4 session runs `git worktree list`,
finds `.worktrees/joint-plan`, and has two choices. It can stop and ask, and the first day of the most
time-critical step goes to an ownership question. Or it can proceed, and then this branch's PR, which edits
`docs/maxim_upstream/README.md`, lands during or after the migration without a rule that covers it. The plan then
slips the date it set for step 4, on its first day.

**Fix (unverified).** Pick one and write it into §7: (a) this branch merges or is parked (no PR, no further commits)
before step 4 starts, or (b) the owner amends step 4's brief to name `phase3/joint-plan` as a third late branch, on
the same terms as the other two.

### A2. `joint_plan_DRAFT.md::§1` (J1's entry text), `§4` J10: ledger runs against the world break Overdrive's O10, and Maxim's D8 rests on O10

Overdrive's O10 (`decisions/npcs_and_sem.md`) reads: "No developer mode with real Maxim before tier A, except inside
strict red-gate tests." Maxim's D8 (`release_1_3_5.md`) justifies its harness only through O10: "So a Maxim-owned
harness may drive Overdrive's world server under strict red gates, which needs no change to Overdrive's decisions."

J1 changes what the harness produces. It becomes a run "recorded on the ledger like any other run". A ledger run
yields a result, so it isn't an `xfail(strict=True)` test. J1's parenthesis "line 3's rules: strict red gates" calls
it both at once. J10's timing makes the clash concrete. The flooded-room fields come with Phase 2 (2027-02 to 04),
the E2/E3 preregistrations follow, and tier A sits in Phase 4, "2027 Q3 at the earliest". So the evidence runs J10
sells as the plan's best link fall before tier A and outside a strict red gate, which O10 forbids.

**Failure scenario.** Maxim's owner files J1 as drafted. A year later the E2 prereg cites the game as its venue, and
its four-lens review reads D8. D8 says no Overdrive decision needed to change, but one does now. Either the review
blocks the prereg on an Overdrive rule nobody amended, or the run goes ahead, and Overdrive's O10 is silently
broken by a Maxim harness.

**Fix (unverified).** Add to §7 an Overdrive owner decision that amends O10: real Maxim may drive the world outside
a strict red gate when a Maxim prereg frozen on Maxim's `main` names the run. Record it in Overdrive's decision log
after step 4, under an id the owner names. Remove "strict red gates" from J1's description of the evidence run,
since it describes line 3's 1.3.5 skeleton and not a ledger run. Have J1 cite the O10 amendment so D8's reasoning
gets replaced and not just contradicted.

### A3. `joint_plan_DRAFT.md::§6` steps 2–3: the ablation probe gathers its data before the prereg that would count it, and its mechanisms are Overdrive's reimplementation of Maxim's

Step 2 runs the ablation in Overdrive in 2027-01, "reported to #1810". Step 3 then turns "the probe's design" into
a Maxim prereg in 2027-02, frozen before data. But the data already exist by then: the prereg is written after
its author has seen the ablation's results on the same design. That is exactly the post-hoc path that J1's own text
("frozen on `main` before data") and Maxim's process close. §6 also ends with "steps 1–3 are evidence".

Separately, step 2 implements Maxim mechanisms in Overdrive: "register integration (Maxim's stated form, where
out-of-register inputs depress the response)", online and pretrained norms, and late fusion. That is Overdrive's
reading of Maxim's documents, coded in Overdrive. As input to a Maxim decision, it's a hand-rolled copy of a spec
that Maxim owns. "Keep Maxim untouched" and "Run Maxim when integration needs it" both point the other way: a run
that bears on a rung uses Maxim's code, in Maxim's harness.

**Failure scenario.** Maxim's DESIGN_REVIEW lens reads the 2027-02 prereg, finds that its arms, populations and
conditions match a run reported a month earlier, and rejects it as a confirmation of known results. Or it misses
that, the rung is earned on a post-hoc design, and the ledger carries a result whose venue J1 vouched for.

**Fix (unverified).** Rewrite §6 so that step 2 is exploratory. It informs the prereg's design, it is labelled as
never being evidence for a rung (in the way O56 labels the spec-generator spike), and it reports to #1810 as an
issue input only. Step 3's prereg then gets a fresh run on held-out populations and conditions, using Maxim's code
in Maxim's harness. Change §6's last sentence to match.

---

## SHOULD-FIX

### S1. `joint_plan_DRAFT.md::§2`, `§7`: the date mechanism has no working owner, no trigger it can meet, and no check

§2 gives re-forecasting to "Overdrive's upstream lane (O77)" at every Maxim release and Overdrive tag, and has that
lane "report each slip in both repositories". That assignment fails on four counts:
- The lane runs "from this brief" (`3_upstream_sync.md`, line 70), and the brief's reconciliation is "the issue or PR
  number, the release that holds the fix, where the lock is, and nothing more" (lines 33–38). It has no duty to
  forecast dates, so the next lane session won't do it.
- O79 bars the lane while step 4 is open, so the first trigger (a 1.3.5 release inside 12-07 to 12-23, near step 4's
  window) may be deferred too.
- Overdrive can't write slip reports in Maxim's repository except as issue comments, and the plan names no Maxim-side
  owner of its half. Maxim's dates of record (milestone due dates) are set by the owner, but nothing re-forecasts
  them.
- A "date of record" is "a row date in Overdrive's `docs/roadmap.md`", but the roadmap's line 3 says "Phases are
  ordered by dependency, not by date", and its rows have no date column. The plan adds a new contract to the
  roadmap's row format without changing the roadmap, which is frozen until step 4 anyway.

§7's "set the date for J11's results" therefore has nowhere to live. The roadmap is frozen and undated, and
slice2-design writes no record. No check notices when a range passes: `check_plan.py` checks the foundations plan
only.

**Failure scenario.** 1.3.5 ships on 12-15. Step 4 is still open, so the lane doesn't run. When it does run, its
brief doesn't mention dates. J11's "12-04 to 12-11" passes without anyone noting the slip, and §2's "a slip is
reported, never absorbed" has held once, on paper.

**Fix (unverified).** Make the duty real:
- amend `3_upstream_sync.md` with a re-forecast step that reads the J table;
- decide, as an owner ruling recorded after step 4, whether roadmap rows carry dates, and in which column;
- name Maxim's owner of the Maxim half (for example the 1.3.5 plan's sessions table);
- until then, say in §2 that the dates are unowned and advisory, not "dates of record".

### S2. `README.md` (the changed line), `joint_plan_DRAFT.md::§1`, `§7`: the owner's 2026-11-26 ruling has no Overdrive record, and the README now contradicts CLAUDE.md

The ruling is recorded only in a `_DRAFT` file meant to be filed upstream and edited by Maxim's owner, and in a
README sentence. The README now says game runs never go on the ledger "until Maxim records the owner's ruling".
CLAUDE.md ("Keep Maxim untouched") still says, unconditionally, "Game runs never go on Maxim's results ledger".
§7 offers to amend CLAUDE.md once J1 is filed, but it lists no Overdrive decision row. Owner rulings belong in
`docs/design/decisions/`, and those logs are frozen until step 4.

**Failure scenario.** A session in 2026-12 reads CLAUDE.md, the standing instruction, and refuses a J10 design
step as forbidden. Another session reads the README and goes ahead. Neither can cite a decision id, because none
exists. Then J1 gets filed with Maxim's owner's edits, and the only Overdrive copy of the ruling, the draft's §1,
no longer matches either the ruling or what was filed.

**Fix (unverified).** Add to §7: "record the 2026-11-26 ruling as an Overdrive decision when step 4 merges, under
an id the owner names (O79 (3) reruns), and point the README and the CLAUDE.md amendment at it". Until then the
README line should cite the ruling's date and say its record is pending. It shouldn't word it as a rule that
depends on a Maxim event.

### S3. `joint_plan_DRAFT.md::§4`, `§5`, `§6` step 1: status and results are copied from their owners, so every reconciliation leaves a stale copy

The tables state status that other documents own:
- J2, "fixed by #1773, in no release": the roadmap's OD-I1, OD-I3 and OD-I6 rows hold this, and step 2 owns them
  (O79 (2)).
- J3, "#1782 (closed)", and J4, "#1787 merged; PRs #1827, #1829 in draft": the roadmap's OD-A rows hold these, and
  the lane reconciles them.
- The README's status column holds the same facts again.

§6 step 1 copies the re-ID probe's interim numbers ("AUC within 0.016", "threshold of 0.85 merges everyone",
"7–14×"). Their owner is the probe's results on the unmerged `phase1/slice2-design`, and its stage 3 is still
running ("finishes 2026-11-27"). That puts the facts in three places in Overdrive alone, with only one of them in
the lane's reconciliation list.

**Failure scenario.** The lane's 1.3.5 rerun updates OD-I1's row to "released in 1.3.5". J2 still says "in no
release", and Maxim's owner, reading the plan upstream, chases a done item. Or stage 3's final read changes the
AUC gap, and the joint plan sent to Maxim carries the interim number.

**Fix (unverified).** Make each row cite its owner by id and keep only the link fields, which are the ask, the
vehicle, who needs it and the range. Replace status phrases with "status: roadmap OD-I1". In §6 step 1, link the
probe's results file and state no numbers, or label them "interim, read at `7f21055`".

### S4. `joint_plan_DRAFT.md::§7`, header "Ids": the roadmap rows "at step 4" fall outside step 4's scope and duplicate rows already drafted

§7 puts "add this plan's links to `docs/roadmap.md` Phase 3 at step 4, as rows citing `J1`–`J14`". But step 4's
brief limits its roadmap edits to "step 4's row" (line 36) and says "Don't redesign". O77 gives the roadmap's
Phase 3 to the upstream lane. The new rows would also overlap rows already written on an unmerged branch:
- J8 and J11 are OD-C15 and OD-C16 on `phase1/slice2-design`'s roadmap (lines 345–346 there).
- J13 (the `hash()` in `novelty.py:111-112`, which is real at `a584c4d0`) and J1's pushback against
  D8/D13 and the candidates rule are Maxim proposals. CLAUDE.md ("Push back on Maxim") says each must be "an item
  under Phase 3 in `docs/roadmap.md`". Held only as J-ids, they sit outside `lint_ids`'s families, so no check sees
  them.

**Failure scenario.** Step 4's session either refuses §7's request, or obeys it and breaks its own brief. If rows
citing J8 and J11 are added later and slice2-design then merges OD-C15 and OD-C16, the roadmap holds two rows each
for person value and person re-identification. Neither collides by id, so `check_roadmap_ids` passes.

**Fix (unverified).** Move the item to "the lane's first rerun after step 4 merges (O79 (1): a trigger that fell
runs then), on ids the owner names". It should add `OD-` rows only for links with no row yet (J1, J10, J13 and
J14's new parts) and map J8 and J11 to OD-C15 and OD-C16 after slice2-design merges. Don't keep J-citing rows
in the roadmap: the J table becomes a view that cites `OD-` ids, not the reverse. Keeping J-ids outside the roadmap
until step 4 is sound only as a temporary label with this named exit.

### S5. `joint_plan_DRAFT.md::§5` J10, `§6` step 3: a Maxim harness that bypasses Overdrive's SEM adapter becomes a second owner of the stimulus contract

Line 3 (`release_1_3_5.md` lines 191–203) has the harness drive "the world server directly" and bypass "Overdrive's
SEM adapter". J10 hands that harness `is_in_water` "from the head's liquid fraction" and a world-owned `oxygen`.
§6 step 5 puts person features behind the leak rules in `sem_stimuli.md` and the re-ID draft. Overdrive's stimulus
contract (which reductions, at which sites, on which cadence, with which leak rules) is owned by
`docs/design/sem_stimuli.md`. A harness that reads the world directly has to reimplement that mapping in Maxim. The
plan doesn't say which side owns it for an evidence run.

**Failure scenario.** The E2 run reads liquid fraction at the head cell centre, which is the "decide at the cell
mean" error the resolution rule bans. Or it reads a channel the leak rules hide from NPCs, such as a person's
identity in a J11 successor. The ledger result then holds for the harness's copy of the membrane, not the game's,
and a later fix to `sem_stimuli.md` doesn't reach it.

**Fix (unverified).** State in J10 and in J1's text that an evidence run reads the world only through Overdrive's
published membrane (the SEM adapter or a frame view `sem_stimuli.md` defines). Then the stimulus contract keeps
one owner, and the harness stays Maxim's. If that needs the embeddable contract first, say so, and J10's range
moves accordingly.

### S6. `joint_plan_DRAFT.md::§3`, `§5`, `§6` step 2: the plan schedules Overdrive steps that O79 (5) gives to the planning session, and has no brief of its own

O79 (5) says "the owner starts the next planning session when step 5 merges. It writes step 6's brief and assigns
steps 5b to 9." This plan dates new Overdrive work in that session's territory:
- the ablation probe ("designed after step 4, runs in 2027-01");
- J10's "field-level design in 2027-01";
- Phase 2's start.

It also asks for "a field-level design" ahead of Phase 1's exit. The winddown rule is one step per session, with a
brief that defines done, including the number of review rounds and a stop rule. But
`docs/plans/next_steps/` has no brief for `phase3/joint-plan`. So nothing defines this plan's exit, its number of
rounds, or which session owns it after hand-off.

**Failure scenario.** The planning session after step 5 orders steps 5b to 9 and leaves the ablation out. The joint
plan, already sent to Maxim, promised it for 2027-01. Two documents now schedule Overdrive's next quarter, and
Maxim plans against the one that won't happen.

**Fix (unverified).** Mark §3's and §6's Overdrive rows as "inputs to the planning session after step 5 (O79 (5)),
not schedules". Record in the hand-off which session owns the plan next. That should be the lane, per S1, with the
duty written into its brief.

---

## NIT

### N1. `joint_plan_DRAFT.md` header "Ids", `README.md`: J-ids collide in Maxim

Overdrive's `origin/main` has no `J1` to `J14` in any text file. Maxim's `github/main` uses J1 to J3 for
`deferred/grounded_word_binding.md`'s joins (`:335`, `:356`, `:361`), which touch cross-modal perception, close to
§6's line. It uses J1 to J7 for finding tags in `log_url_redaction_1801_approach.md`. A `DECISIONS.md` entry or an
issue that says "J1" is ambiguous in Maxim. The README row's permanent text "link J1" gets the same ambiguity.
**Fix (unverified):** use a prefix, such as `JP1`, or `OD-J1` once the ids are in the roadmap per S4.

### N2. `joint_plan_DRAFT.md::§1`: two filings share one draft

J1's `DECISIONS.md` text sits inside a dated plan whose tables churn at every reconciliation. The README's
convention is one draft per filing, with its own status: `decisions_entry_DRAFT.md` is the precedent. The README's
new row already carries two vehicles in one status cell. **Fix (unverified):** move J1's text to its own draft, and
have the plan link to it.

### N3. `joint_plan_DRAFT.md::§8` "Overdrive's step 4 freeze": restated, and broader than its owners

"Overdrive opens no PR from its slice and design branches and writes no record file" paraphrases O81 (1) and step
4's brief, and reads wider than O81, which binds the slice branch. Link O79, O81 and `4_records_build.md` and
don't restate them.

### N4. `joint_plan_DRAFT.md::§5` J11, `§6` steps 1 and 5: the cited paths resolve only on an unmerged branch

`docs/design/research/person_reid_probe/` and "the re-ID draft" don't exist on `origin/main`; they exist only on
`phase1/slice2-design`. The header names `7f21055` as read, but the links in §5 and §6 don't say which branch they
point to. A reader on `main`, or Maxim's owner following them, finds nothing there. Qualify them with the branch
and commit until slice2-design merges.

---

## What holds

- **Boundary.** Apart from A3 and S5, no item builds Maxim-owned cognition in Overdrive, and each Maxim item has a
  Maxim vehicle: an issue (J13), a plan with its three-lens review (J6), a prereg with four-lens review (J1, §6 step
  3), or an owner decision (J9).
- **Record freeze, for this branch's files.** It writes no record file, and `records_layout.md` §5 keeps
  `docs/maxim_upstream/` out of `renumber`'s rewrites. The conflicts are A1 and S4 only.
- **No decision or fold table,** and 2,336 words, under the 2,500 limit.
