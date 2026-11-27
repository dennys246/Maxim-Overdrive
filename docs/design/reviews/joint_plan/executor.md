# Joint plan draft: Executor review

**Reviewed:** `phase3/joint-plan` at `92fbe74` (`docs/maxim_upstream/joint_plan_DRAFT.md`, new; `docs/maxim_upstream/README.md`).
**Sources:** Maxim `<maxim-clone>` at `github/main` `a584c4d0` and its tags, read only through `git show`, `git grep`,
`git log` and `git for-each-ref`; `gh` read-only on `dennys246/Maxim` (milestones, issues, PRs, releases, advisories)
and `dennys246/Maxim-Overdrive`; Overdrive `origin/main` `e6d6a7f` and `phase1/slice2-design` `7f21055`. `gh` was
read 2026-11-27 about 06:40 UTC, a few minutes after the draft's commit (06:35 UTC).

**Lens:** does every factual claim hold against its source, and is every proposed range derivable from the method
the draft states?

**Counts:** 3 BLOCKER, 6 SHOULD-FIX, 8 NIT. Every finding is `open`.

## BLOCKER

### E1. `joint_plan_DRAFT.md::§3 Overdrive Phase 2 start` and `::§5 J10`: liquids and oxygen are not in Overdrive's Phase 2

The draft gives Phase 2's scope as "sound, light and visibility, gas, liquids", and J10's vehicle as "Overdrive's
Phase 2 liquid and gas fields", with "fields with Phase 2, 2027-02 to 04". On `origin/main`, `docs/roadmap.md`
§Phase 2 lists sound, light and visibility, gas and radiation, convection, structural support, load and moving bodies,
scale, the known gap, and the rungs moved from Phase 1 (6.2–6.4, zones and vents, phase change other than fusion, CSG
footprints). `git show origin/main:docs/roadmap.md | grep -i -E "liquid|water|oxygen|flood|drown"` finds no liquid,
water, oxygen or flooding anywhere in the roadmap. The flooded room (`is_in_water` from the head's liquid fraction,
world-owned `oxygen`) exists only in research: `docs/design/research/states_of_matter/gameplay.md:99` and `:235`,
`.../sem.md:253-257`, `.../signals/maxim_senses.md:76`. That is also the "Overdrive `gameplay.md` §5 item 1" that
Maxim's `release_1_3_5.md` line 3 cites.

The range is also the wrong quantity: "2027-02 to 04" is the draft's Phase 2 *start*, so it can't also be the date
the fields are delivered.

**Failure scenario:** the draft calls J10 "the link most likely to move a Maxim rung". Maxim's owner reads it,
schedules E2's and E3's pre-registrations to use an Overdrive venue in 2027-Q1/Q2, and perhaps assigns line 3's
harness owner on that basis. No Overdrive phase schedules the liquid field or the oxygen drive, so the date has no
delivering row, and nothing reports a slip, because no row exists to slip.

**Fix (unverified):** either cite the research and say no phase holds liquids yet, with J10 "not dateable", or
make adding liquids and oxygen to a roadmap phase an Overdrive decision this plan proposes (§7), and give J10 a
delivery range derived from that phase.

### E2. `::§3 Maxim 1.3.6` and `::§3 Maxim 1.4.0`: the ranges come from an assumed rate, not a measured one, and the arithmetic doesn't reproduce them

§2 says "proposed ranges come from measured pace". 1.3.6's method is "2–4 gate items a week from 1.3.6's start".
Nothing measures that rate, and §8 says T0's rate is unmeasured. What can be measured:
- `scripts/release_gates.json` at `a584c4d0`: 33 items under `1.4.0`, one with evidence (`1263.dn-stop`). The file
  was last changed 2026-10-24 (`484e12ca`). The draft's "1 of 33" and "32 open" are right.
- The issues behind three more items have closed without their evidence being recorded: #1259 (2026-11-01), #1264
  (2026-11-18), #1267 (2026-11-21). Whether each item's scope is met is unverified. Even counting them, the pace is
  about 3 to 4 items in six weeks, roughly 0.5–0.75 a week, which is a third to a sixth of the rate the draft assumes.
  At 0.75 a week, 32 items take about 43 weeks.
- Several T0 items belong to the orchestrator line, not to loop phase 2: `1323.functions-1000` (it covers
  `start_simulation_mode`, still 1,818 lines at `a584c4d0` against a 1,000 bound), `1123.*` ×3, `932.resume-sim`,
  `1288.orch-stall-nudge` and `863.orch.*` ×3. `release_1_3_5.md` says "the planned mainline has nobody on it". A
  1.3.6 range keyed to loop-phase-2 pace doesn't cover them.

Even at the draft's own rate the dates don't follow. 1.3.6 starts after 1.3.5 (2026-12-07 to 12-23 by §3).
32 items ÷ 4 a week = 8 weeks, which gives 2027-02-01 at the earliest. 32 ÷ 2 = 16 weeks, which gives 2027-04-14 at the
latest. The draft has 2027-01-15 to 03-31. Starting the slices early (D5) from today gives 2027-01-21 at the earliest,
still not 01-15.

For 1.4.0, "1.3.6 plus B2 → B3 → B4 and E1, at an assumed 3–6 weeks a rung" is four rungs written in series:
12–24 weeks after 1.3.6, which gives 2027-04-09 to 2027-09-15. Three serial rungs (if E1 runs beside B4) give 9–18
weeks, 2027-03-19 to 2027-08-04. The draft has "2027-03 to 07". It also leaves out T2 (Exp 62), T7 and T8, which
`roadmap_1_4.md` §Release thresholds also requires.

**Failure scenario:** Overdrive dates Phase 4 ("2027 Q3 at the earliest") on 1.4.0 arriving in 2027-03 to 07, and
the owner weighs Overdrive's fan-out against it. The measured rate puts T0 alone near the end of 2027. The plan's
own rule ("a slip is reported, never absorbed") then fires at the first re-forecast, against dates that were never
derived.

**Fix (unverified):** state the measured T0 rate (items with evidence, plus closed issues listed as unverified) and
derive both ranges from it with the arithmetic written in the row. List the orchestrator items apart from loop
phase 2, or mark 1.3.6 and 1.4.0 "not dateable until a month's rate is measured", as §8 already argues.

### E3. `::§6 step 1`: "a centring test … widens the usable threshold window 7–14× without changing the ranking" has no committed source

This number is §6's evidence for step 4's mechanism ("a centred person modality beside `_sensor_embed`"), and its
results go to #1810 (J11). I found no source for it:
- `phase1/slice2-design` at `7f21055`: `results.md` (2,458 words) covers Step 0 and Stage 1 and has no centring.
  The commit message of `7f21055` reports the A-world encoding check, not centring.
- `git grep -E "7–14|centring test|centering test|mean-centr"` over every local branch and remote ref matches only
  this draft, plus an unrelated kinematics review line.
- `git log --all -i --grep=centr` finds commits about cell centres and arms' centres, not embedding centring.
- No match in the slice2-design worktree's untracked files or in the shared `_durable` folder.

**Failure scenario:** the owner, or Maxim's #1810 thread, takes "7–14×" as a measured property of `_sensor_embed`
and plans the centred modality from it. Nobody can rerun it, and if it came from a scratch run in a conversation,
it is gone.

**Fix (unverified):** commit the centring test and its output on the probe's branch (protocol status: a labelled
diagnostic, like the encoding check) and cite the commit, or remove the sentence until it exists.

## SHOULD-FIX

### E4. `::§4 J4`: PR 1a/1b are not committed to 1.3.5, and the world-clock exit condition has already been met

J4 says "1.3.5 for PR 1a/1b". `world_clock_a_pre.md` at `a584c4d0` says the opposite: "1.3.5 needs only this plan
reviewed and PR 0 merged (§Exit). The other PRs merge when green". Its §Exit adds "PRs 1–4 ride 1.3.5 if green before
the cut; otherwise they follow. PR 5 is 1.3.6." PR 0 is #1798, merged 2026-11-25, and J4's vehicle column omits it.
So §3's 1.3.5 gate "the world-clock plan's first PR" is already met, and #1827 and #1829 are still drafts.
Also, J4 lists OD-A5 under A-pre as a whole. The roadmap row and the A-pre plan put only its window (and the
SCN-render part) in A-pre; the rest of it is A-post.

**Failure scenario:** Overdrive's upstream lane plans OD-A2's and OD-A3's red gates and the lock move to flip at
1.3.5. PR 1a misses the cut, which the plan allows, and the miss reads as a slip when nothing was ever promised.
**Fix (unverified):** "1.3.5 if green before the cut, else the next release". Cite #1798 as merged, and split OD-A5.

### E5. `::§3 Maxim 1.3.6` scope: B0b moved to 1.3.5

`roadmap_1_3_x.md` §1.3.6 still has a B0b bullet, but its own note says that #1227 and #1228 (with #1225) moved to
1.3.5 line 5 on 2026-11-22. `gh`: #1227 is open in milestone 1.3.5, and #1228 and #1225 are closed in milestone 1.3.5.
Listing B0b under 1.3.6 counts work twice in a plan that sets dates from scope.
**Fix (verified against the sources above):** drop B0b from 1.3.6, or write "the `arm_effective` stamp, if not done in 1.3.5".

### E6. `::§6 step 1`: the probe findings are stated more firmly than the record supports

- "Mixing … breaks recognition when the place changes." `7f21055`'s message: of 82 Stage 2 cells, 18 read row 3
  and all fail offline on all three layers, and "the committed attribution waits for the full join". `check.json`'s
  notes say the environment is the probe's own (four places, each sensor uniform per place), "not a measured scene".
- "Its default sensor threshold of 0.85 merges everyone." `results.md`: non-twin merge at P = 20 is 1.00 "in every
  cell checked". False-match at 0.85 is 0.32–0.81. "Everyone" is the merge statistic in the cells checked, not every
  condition.
- The AUC claim ("within 0.016") is verified (`results.md` lines 105 and 190).

**Failure scenario:** the bullets go to #1810 as results before the full join, and Maxim's fabric owner treats a
synthetic-environment result as a property of Maxim's world vector.
**Fix (unverified):** add the qualifiers: preliminary, Stage 2's 82 cells only, the probe's own environment, and
attribution pending.

### E7. `::§5 J13`: the `hash()` fact holds, but no defect or provenance is shown

Verified: `src/maxim/salience/novelty.py:110-112` at `a584c4d0` reads `# Stable hash → pseudo IDs (positive ints,
deterministic)` and then `hash(entity_name) & 0x7FFFFFFF`. `str` hashes are salted per process. But:
- No Overdrive tree records the finding. `git grep` for `update_with_entity` and for novelty `hash()` on `origin/main`
  and `7f21055` finds nothing, so "defects found from the game" has no committed source.
- No outcome is shown to change. `novelty.py` has no save or load path, and its callers are
  `default_network/network.py:650` and `:657`. Within one process the ids are consistent. Across processes they
  differ, but nothing is shown to persist or order by them. Maxim closed a similar case as #1789 (persisted id
  indexes following `PYTHONHASHSEED`), and that one changed saved bytes.

**Failure scenario:** Maxim's owner gets an issue with no failure scenario. It is triaged as a comment fix, or it
costs a review round to find out it changes nothing, which weakens the game's standing as a source of defects.
**Fix (unverified):** find a consumer whose result depends on the id across processes (the class-modulation lookup
in `inference/segment_vision.py::NoveltyTracker`, any ordering or eviction by id). File it with that consumer, or
file it as a misleading comment.

### E8. `::§6 step 3` and `::§5 J11`: "the graded consumer that modality resolution waits for" is not that plan's trigger

`deferred/modality_resolution_and_alignment.md` line 4: "Revive trigger RE-KEYED 2026-10-07 … revives when the
grounding line's GL3 registry+provenance stage ships". §4's "only when a graded consumer exists" (line 181) is the
condition for promoting F-B, the scalar `_place_code`, measured by a pre-registered graded-orient ablation. It does
not revive the plan.
**Failure scenario:** the person probe's pre-registration claims to fire a Maxim trigger it can't fire, and the
four-lens review spends a round on it.
**Fix (verified against the text):** say "§4's condition for F-B" and name the actual revive trigger (GL3 shipping).

### E9. `::§2` and `::§3`: several ranges have no stated derivation

- Overdrive Phase 1 exit, 2027-01-15 to 03-31: the method is "step pace", with no number. It is the same range as
  Maxim 1.3.6.
- Phase 2 start, 2027-02 to 04, "after Phase 1's exit": the exit's range starts 01-15, so the two-week offset is
  unexplained.
- J8, "answers 2027-01": no method.
- Step 4, "11-27 to 12-03, its brief": `docs/plans/next_steps/4_records_build.md` gives no duration. It allows R3 to
  move to a second session.
- "Steps that take 0.5–3 days", "±2× at least", and "Stage 3 finishes 2026-11-27": no source is cited, and `7f21055`
  says only that Stage 3's runs are "still on the mini".

**Failure scenario:** §7 asks the owner to commit dates this week, so a range with no method can become a date of
record. At the first re-forecast, nobody can tell a slip from a bad estimate.
**Fix (unverified):** write each row's arithmetic, or mark the row "estimate, no measured basis".

## NIT

- **E10 `::§3 Maxim 1.3.5`**: from the stated method, 11-22 + 13.5 days = 12-05/06 (the draft has 12-07), and
  11-22 + 29 or 30 days = 12-21/22 (the draft has 12-23). §2 gives 1.3.4's interval as 30 days and §3 as 29: tag dates
  (10-23 to 11-22) give 30, and GitHub release dates in UTC (10-24 to 11-22) give 29. Pick one basis. The interval
  list 8, 19, 7, 30 and the median 13.5 are verified on tag dates.
- **E11 `::§2`**: "about 70 [merged PRs] a week in October" holds for the weeks of 09-28, 10-05 and 10-12 (68, 76, 74,
  Monday weeks, UTC−7). The weeks of 10-19 and 10-26 were 35 and 46, and October's average was about 58 a week (259
  PRs). November's weeks were 22, 29, 36 and 29 (the last one partial). "22–43" fits only Sunday-start or UTC
  bucketing. So the slowdown began in mid-October, not in November.
- **E12 `README.md` new row**: "links J1–J14 over every row above" is false. No J link covers
  `sem_breaking_change_plan_DRAFT.md` (OD-C1 to OD-C10), OD-I2 in `issues_now_DRAFT.md`, or Exp 64's OD-B1 to OD-B7.
- **E13 `::§1`**: `release_1_3_5.md` also says it in its line 3 summary ("Game runs stay off Maxim's ledger, and the
  harness runs under O10's strict red gates (D8, D13)"), a fourth place that J1 doesn't name. And §Not decided here
  calls the venue undecided, which isn't "the opposite".
- **E14 `::§8`**: "Game runs need no rig" is in tension with D12, which exists because game and playtest traffic
  share the mini's proxy. The claim holds only for runs without LLM inference on the mini.
- **E15 `::§4 J7`**: the roadmap's OD-A7 row places keyed RNG as "a new release-gate item after the 1.4.0 cut", not
  in the 1.5 line. Only the stepped `think` is placed in "the 1.5 hybrid line's `src`" (roadmap line 248).
- **E16 `::§5 J10`**: "a contingency a reasonable no-bio floor can lose" is set as a quote but combines
  `baseline_floors.md:29` ("a contingency a reasonable floor can lose") and `e1_conflict_prereg.md:16`/`:70` ("a
  reasonable no-bio floor can lose"). Quote one of them, or paraphrase.
- **E17 `::§4 J2`**: "needed by Phase 4's subset" covers OD-I1 and OD-I3 (roadmap §Phase 4), not OD-I6. OD-I6 is
  needed for the import-linter upgrade and the lock move.

## Verified as written

- Maxim `github/main` = `a584c4d0` (2026-11-26). Overdrive `origin/main` = `e6d6a7f` (2026-11-25).
- 1.3.x tag dates: 1.3.0 09-19, 1.3.1 09-27, 1.3.2 10-16, 1.3.3 10-23, 1.3.4 11-22. The intervals and their median
  hold (E10 has the 29/30 basis).
- Milestone 1.3.5: 87 issues. 68 open is consistent with a read at 06:29–06:32 UTC. At review time it was 67 open
  (#1761, #1764 and #1765 closed 06:29–06:32 UTC), and the milestone has no due date.
- Overdrive: first commit 2026-11-14 (twelve days), 76 merged PRs, `v0.1.0` 2026-11-23 on `41036dc`. The slice
  verdict is due 2026-12-18 (roadmap step 10).
- D8/D13's heading quote, and its "open owner question" on the tier C venue. The candidates document's header rule,
  "game runs never go on Maxim's ledger", and its §Cautions and §Not decided here, which call the venue undecided.
- Issue and PR states:
  - #1782 closed 11-26, fixed by PR #1822 (merged on `main`, in no release).
  - #1787 merged 11-24.
  - #1827 and #1829 open as drafts.
  - #1773 merged 11-23 and not in v1.3.4.
  - #1788 open (A-post with B2, per the owner's comment).
  - #1802 open in milestone 1.3.5, "line 5" (owner, 11-25).
  - #1803 open, "owner-decision, after 1.3.5".
  - #1807 and #1810 open.
  - #1305 open in milestone 1.3.5.
  - #1361 and #1150 open.
  - #1708 open.
- GHSA-rjg9-f5r9-7x7p (the blocked `base_url` advisory) is in draft.
- OD- ids: every one the draft cites exists on `origin/main`'s roadmap with the tier the draft gives (A-pre: A2, A3;
  A-post: A4, A8, A9; embeddable: A10–A12, A14, A15, A17, A18; amendment: A16; OD-I8 in #1361 S4), apart from E4
  (A5) and E15 (A7). OD-A15 is placed after the 1.4.0 cut, in the 1.5 hybrid line. OD-C15 and OD-C16 exist only on
  `7f21055`.
- Maxim 1.4.0's thresholds: T0–T4, T4a, T7, T8, with E2 and E3 conditional (T5, T6) and GL5 conditional (T9).
- Citations: `autonomic_layer.md` §3.4/§3.5 and §5.4 (GL2c); fabric §B; `latent_forward_model.md` §4.2 item 5 (the
  per-item → node map); `setpoint_aware_neutral.md`'s trigger phrase, its zero vector and its frozen prototypes.
- Planning PR #71 merged, so step 4 may start. Its brief lets the slice2-design branch stay in flight.
- `drift.yml` and `tests/test_maxim_fixes_pending.py` exist. O75, O77 and O78 say what the draft says they do.
- Draft size: 2,336 words, within the 2,500-word plan budget.
