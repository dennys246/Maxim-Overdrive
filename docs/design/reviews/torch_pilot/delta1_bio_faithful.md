# Bio-faithful integration, round 2 (delta): torch_pilot.md, working tree over fcc6e55

I read everything read-only. In the Overdrive worktree I read `git diff fcc6e55 -- docs/`, the folded §2, §3, §6, §7, §9.2, §10, §11 and §12, lesson 35, the checklist diff, the contracts diff and `docs/roadmap.md:203`. In Maxim I read b98954f7 with `git show`. I did not fetch, so b98954f7 is only as current as the local ref.

**A correction to my own round-1 wording comes first.** In B-S1 I called `roadmap_1_4.md:69-71` "R4's own definition". R4 is actually the fourth gap in that plan's thesis list ("R4 — credit is anchored to the executor CALL window…"). The plan then reuses the label for the build ("Credit routing (R4, first)", line 352). The folded §12 says "`roadmap_1_4.md`, R4: relief after a call returns credits the next call". That is accurate under either reading, so nothing in the fold depends on my mislabel.

**Citations checked against b98954f7:**
- `tool_failure_credit.md:76-80` holds "Retiring at invocation end removes the 300 s pending window … R4 delayed credit must not assume the window". The plan is ACTIVE.
- In `nac.py`, line 439 sets `temporal_window_seconds: float = 300.0`, and lines 3712-3715 read the anchor window with `now = time.time()`.
- The quote from the amendment draft is real. It sits at `propose_settle_amendment_DRAFT.md:55-56` and reads "Consequences that take seconds stay with NAc's temporal window". Lesson 35 lowercases the first word inside the quotation marks, which is trivial.
- Roadmap OD-A16 (`docs/roadmap.md:203`) has the plan type "amendment" and "Rides on OD-A18". §12 now defers to that row.

## Status table

| Id | Status | Evidence |
|---|---|---|
| B-S1 | fixed | §12 says "OD-A16's route is the roadmap's row (Phase 3, OD-A16), not this note's". It cites `tool_failure_credit.md` 76–80, `roadmap_1_4.md` R4 and `nac.py`'s `time.time()` anchor window (OD-A20), and lists the search terms. All three citations check out at b98954f7. The trace description I flagged as incomplete was removed rather than completed (see B2-N1). |
| B-S2 | fixed | §12 names two delays: "from `kindle` to `t_flash`, physics, measured", and "from the receipt to the first change in a declared stimulus row: none in Phase 1 … (`client_objects.md` §5.4, OD-C8)". The isolating membrane test cannot exist in Phase 1, because no row carries flame, and the text says so. The gap left over is that nothing schedules the measurement or delivers it (B2-S1). |
| B-S3 | fixed | §6 has the row "An NPC's holds (`brief`, `steady`, `long`) — Phase 4's body design (tile §3.2) — each must lie outside the flash band (§9.2) by its margin, measured at 6.1b". This is the deferral option I proposed: the values are deferred and the constraint is stated as contract. §3 now says "In Phase 1 the client is the only producer, so the one-call-site test covers that path alone." What the constraint is measured against is under-specified (B2-N2). |
| B-N1 | fixed | §2 says "Not perceivable: the record, the pilots table and `pilot_ended` (`sem_stimuli.md` §7.4)". Q5's added columns are pilots-table columns, so this covers them. |
| B-N2 | fixed in the design; the downstream edit is open under Q9 | §3 says "An agent's receipt is `sem_stimuli.md` §6.2's `accepted` in every case". §10 has the row "`sem_stimuli.md` §6.2's T11 sweep — adds §4.1's and §4.4's `applied`-with-no-deposit cases". `sem_stimuli.md` itself is unchanged in the tree, and Q9 holds every §10 edit until the owner rules. |
| B-N3 | fixed | §7 says "The torch heats no structural cell, and no body … and tissue under Phase 4's body." |
| B-N4 | fixed | Lesson 35 is in the working tree, numbered after 34, the last lesson on origin/main 2586ed7. It cites the Maxim lines and the draft's slow-effects line. |

## Delta findings

**B2-S1. The fold creates a pushback and an evidence handoff, but nothing tracks or schedules either of them.**
- **Locations:** `docs/lessons_maxim_in_games.md` §35 ("Consequence"), `torch_pilot.md::§12` ("The evidence 6.1b hands OD-A16 is two delays"), `docs/roadmap.md` OD-A16 row (line 203), `docs/plans/checklists.md` 6.1b list.
- **Kind:** contract. It is the routing of a Phase 3 item, and OD-A16's evidence column belongs to the roadmap row.
- **What is wrong:**
  - Lesson 35 concludes "The amendment draft's slow-effects paragraph has to be revisited before it goes upstream." Nothing in the diff touches the draft, the OD-A16 row or any Phase 3 item. CLAUDE.md ("Push back on Maxim…") says each proposal is an item under Phase 3. This one lives only in a lesson.
  - §12 says 6.1b "hands" OD-A16 two delays, but the 6.1b test list in the checklist names no measurement of kindle→`t_flash` as a recorded OD-A16 datum. Nor does it record the "none" for the stimulus-row delay.
  - The OD-A16 row's evidence column still cites only step 3b(b).
- **Failure scenario:** OD-A16's draft goes upstream with "Consequences that take seconds stay with NAc's temporal window". The draft is then arguing for a window that `tool_failure_credit.md` (ACTIVE, TF1–TF3) removes for tool events. Maxim's review catches it, or worse, doesn't. Meanwhile 6.1b ships without recording either delay, because no checklist line asks for them.
- **Fix (unverified):**
  - Add to the OD-A16 row's evidence: "lesson 35; 6.1b's two delays (`torch_pilot.md` §12)".
  - Add a note in the row, or a margin note in the draft, saying the "Slow effects" paragraph is contradicted by `tool_failure_credit.md:80`.
  - Add to the 6.1b checklist one line that records kindle→`t_flash` at the exit, with its spread, into the OD-A16 row.
  - It is one roadmap edit and one checklist line, and fits this branch.

**B2-N1. Lesson 35 and §12 now say the anchor tier is the only path for seconds-late credit. That drops the eligibility trace, which is real and is the trace a tool completion seeds.**
- **Location:** lesson 35 ("the only seconds-late path left is the anchor tier") and `torch_pilot.md::§12`. The fold deleted the old "pruned after about 44 loop iterations" text without replacing it.
- **Kind:** contract. It is evidence text the OD-A16 amendment will be sized on.
- **What is wrong:**
  - `nac.py` b98954f7 keeps `_eligibility` (line 870), credits traces above 0.01 (lines 3597-3620), and decays them ×0.9 in `decay_eligibility` (line 3707).
  - `lookback_primitive.md:33-35` says the trace is seeded at 0.3 on completion and lands on `_reward_bias` through `credit_node` (×0.15, clamp [0, 0.20]).
  - That path counts loop iterations, not seconds, and is capped weak. Calling the anchor tier "the only" path is still false, and it hides the one route by which `tool:kindle` could get any credit at all.
- **Failure scenario:** the amendment proposes a new delayed-credit window. Maxim answers that the eligibility trace already reaches back and the plan duplicates it. That would be the duplicate-ask failure that CLAUDE.md's "Search Maxim before proposing" rule exists to prevent.
- **Fix (unverified):** name both paths, as round 1's B-S1 did. One is the `tool:kindle` eligibility trace (0.3, ×0.9 per iteration, pruned below 0.01, onto the 0.20-capped `_reward_bias`). The other is the anchor tier on `time.time()`.

**B2-N2. The NPC-hold constraint is set against "the flash band", but that band exists only for the exit slab under the exit torch.**
- **Location:** `torch_pilot.md::§6`, the row "An NPC's holds", and §9.2 ("Margin").
- **Kind:** contract. The values are deferred, but the item format will carry them.
- **What is wrong:**
  - §9.2 defines the band's edges for one scripted case: one recipe, one q''_t and r_t, three grids and two steps.
  - The hold durations are item data in `torch.yaml`, and they apply to every recipe an NPC might kindle.
  - "Each must lie outside the flash band by its margin" therefore has no defined band for pine at another width, or for any other recipe.
  - `torch.yaml` v0's fields have no slot for the holds, so Phase 4 also needs a version bump there. That is acceptable, but it isn't stated.
- **Failure scenario:**
  - At Phase 4, `long` is set just past the exit-pine band.
  - A denser recipe's band sits higher, so every NPC `long` kindle on it is fruitless by construction.
  - The miss is then booked as a learning failure, which is round 1's B-S3 scenario moved to a second recipe.
- **Mechanism or contract:** the contract part is to say which band. The measurement is mechanism, deferred to Phase 4's body design. It has no Phase 1 build step, because Phase 1 has no NPC producer.
- **Fix (unverified):** reword the row to "outside every shipped recipe's band under this item's flux and radius, measured when the holds are set (Phase 4 body design); `torch.yaml` gains the fields with a version bump then".

**Rechecked with nothing new found:**
- **Leak rules:** the new `face` and unrounded `centre_m` fields are covered by §2's not-perceivable line. The receipt's effect value goes to the client, not to agents (§3).
- **Clock:** the record's ticks are `Simulation.step` ticks. No wall-clock read was added.
- **§12's "Nothing here asks Maxim for anything":** this holds for the design itself. The only pushback is to our own draft (B2-S1).
- **contracts.md** `pilot.fields`, count 5 with `target` added: this is Wire's lens. I checked only that `target` is not exposed to agents, and it is not.

## Counts
- **Statuses:** 6 fixed, plus B-N2, which is fixed in the design while its `sem_stimuli.md` edit stays open under Q9. That is 7 findings: 0 deferred, 0 rejected, 0 open, and 1 with a downstream edit open.
- **New findings:** 0 BLOCKER, 1 SHOULD-FIX and 2 NIT. All three are contract findings. B2-N2's measurement half is mechanism, deferred to Phase 4's body design because no Phase 1 build step has an NPC producer.
