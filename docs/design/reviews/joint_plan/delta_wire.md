# Joint plan draft: Wire integrity lens, delta round

**Tree:** `a48cc3903883a28336397e1c779a5b890d8be13a` (the staged fold on `phase3/joint-plan`, parent `92fbe74`, not
committed). Read against Overdrive `origin/main` `e6d6a7f` and `phase1/slice2-design` `7f21055`, Maxim `github/main`
`a584c4d0` (`<maxim-clone>`, git only), and issues via `gh`, 2026-11-26/27.

**Stop rule.** This is the last round. New findings in fold text go to the owner, not to another round.

**Counts.** Round 1: 7 fixed, 2 deferred, 3 open, 0 rejected. New: 0 BLOCKER, 8 SHOULD-FIX, 3 NIT. Each proposed fix
says whether I verified it.

## 1. Round-1 statuses (the reviewer's, read from the tree)

| Id | Status | Evidence |
|---|---|---|
| B1 | **fixed** | J10 is now JP17, "a candidate, not a link", not dateable. It names the missing producers (liquids in no phase, head and lung in Phase 4), says a harness must go through the membrane, and records that E2 is mechanism-gated and built on Minecraft. |
| B2 | **open** (narrowed) | Fixed: the entry cites `npcs_and_sem.md` §10 and keeps PARTIAL, leaves the transfer venue explicitly open, strikes the candidates document's opening rule by name, and asserts `simcore` rather than stamping it. Still open: the Maxim text doesn't carry §10's pins, and Overdrive's side makes §10 a superset of it. Two owners still state different record contents (D1). |
| B3 | **fixed** | §6 step 2 is "never evidence". Step 3 is Maxim-only until step 5. Step 4 says "No Maxim trigger fires", and each trigger is now quoted as written. I re-read `archive/world_channel_weighting.md:223` and fabric §C, and both match. |
| S1 | **deferred** (author's proposal) | §2 says the re-forecast has no owner and proposes two amendments: the lane brief, written by the planning session, and Maxim's cut checklist, which is a Maxim process item. Ranges live only in this file. Trigger: Overdrive's planning session. JP13's range still falls inside step 4 with no re-forecaster, and §2 says so ("a snapshot"). |
| S2 | **fixed** | The §3 1.3.5 row says lines 3–5 don't gate the cut. JP3 reads "if in before the cut", and JP4 "only if green before the cut". JP9's #1802 now reads "open" (milestone 1.3.5, line 5). I checked JP4's "PR 0 already meets" claim: `world_clock_a_pre.md:48` says "1.3.5 needs only this plan reviewed and PR 0 merged", and #1798 merged 2026-11-25. |
| S3 | **open** | Added: JP10 (tier B, Exp 64a), JP11 (the SEM plan) and JP15. Still missing: two of line 6's four Overdrive-side asks, and the line 6 deliveries to OD-A23, OD-A24 and OD-I9. The README's claim is still false (D6). |
| S4 | **fixed** | The poster is named ("that branch's session after the results review"), and §6 cites `7f21055`. Residual NIT: JP13's vehicle cell is still a branch path, and that branch migrates after step 4. |
| S5 | **deferred** | Recording is set for step 4 (§7; the entry's "Overdrive's side"), where step 4's freeze allows it. The list of copies is now six, but it misses a seventh (D8). |
| S6 | **fixed** | §3 no longer has an Overdrive Phase 2 row. JP17 says liquids are "in no Overdrive phase". |
| N1 | **fixed** | JP9 cites #1788's thread. Maxim's own plan also places it: `world_clock_a_pre.md:297` "A-post → A-post (#1788)". |
| N2 | **fixed** | JP16 now has an asking end: Overdrive's replay rule once real Maxim runs in the NPC loop. I re-verified `salience/novelty.py:110-112`. The named test would be the `test_runs_in_processes_with_different_hash_seeds_agree` pattern. |
| N3 | **open**, and now load-bearing | §3 now says 1.3.6's "exit is T0's gate items" and dates Phase 4 from that (D7). |

## 2. Links traced end to end

Each link is traced from producer to consumer to delivering release.
- **Connect:** JP2–JP9 and JP14.
- **Undatable by design, stated:** JP6, JP7 and JP10–JP12.
- **Connects, NIT residual:** JP13 (S4).
- **Connects, with a weak asking end:** JP16 (N2).
- **No live consumer before step 5:** JP1 (D9).
- **Wrong producer:** JP15 (D5).
- **A candidate, consistent with its own text, but contradicted by the entry's condition 3:** JP17 (D3).

Figures I re-checked:
- The release intervals, 8, 19, 7 and 30 days (tags v1.3.0–v1.3.4), and 1.3.5's range.
- 1 of 33 items evidenced (`release_gates.json` gates `1.4.0`, the evidenced item `1263.dn-stop`; last changed 10-24).
- The milestones: #1827, #1829, #1803, #1788, #1807 and #1810 have none; #1802 and #1305 are on 1.3.5; #1782 is
  closed and is line 6 item 6 (OD-I10).

I didn't verify the probe's "18 of 22 conditions". It is attributed to the encoding check at `7f21055`, whose
attribution the plan says is not committed.

## 3. New findings

### SHOULD-FIX

**D1. `decisions_entry_game_evidence_DRAFT.md::The entry` condition 2, against `npcs_and_sem.md` §10: the Maxim text pins less than Overdrive's owner of the same contract.**

§10 on main says "A ledger record pins the engine SHA, the pymaxim version, the membrane and agent contract versions
(including any interim `neutral` behaviour, which is part of the treatment), the placement digests
(`inference_placement.md` §4.3), and the Phase 3 items present". It also requires that "every world-only affordance
[be] declared" and that "engineering invariants … [be] kept apart from behavioural claims".

The entry's condition 2 pins the two commits, the scene digest and the grid spacing. The two commits imply the
membrane and the agent code. They don't imply:
- the placement digests, that is, which model served the agent's LLM calls;
- the interim `neutral` behaviour, when it is configuration rather than code;
- the world-only affordances.

Overdrive's side then has §10 "gain the pins of condition 2", so Overdrive's record becomes a strict superset of
Maxim's, and nothing makes Maxim's entry require it.

*Failure scenario.* A pre-registration satisfies conditions 1–4. The model behind the placement changes between
seeds, which is legal because no digest is pinned. Maxim's ledger counts the run. Under Overdrive's §10 the record is
invalid. One row has two verdicts, and neither text is stale by its own rules. That is round 1's B2, narrowed.

*Fix (unverified).* Condition 2 adds "and every pin `npcs_and_sem.md` §10 names at the pinned Overdrive commit",
including the affordance declaration. Alternatively, it lists them inline and §10 cites the entry.

**D2. `decisions_entry_game_evidence_DRAFT.md::The entry`, "an Overdrive world": it doesn't say whether game content may enter, and two Overdrive rules turn on exactly that.**

- **The definition.** `boundaries.md` §8.4 defines the term: "Experiments that need game content are game runs".
- **The harness rule.** §10 has the harness import "only the engine and its own Apache-2.0 fixtures (a fixture body,
  event pool and scene)".
- **The repository licence.** `CLAUDE.md` § Licensing reserves story, characters, lore, art and audio.
- **What the entry does.** It amends the "game runs" ban, so it reads as admitting game content. Yet its Overdrive
  side changes neither the import rule nor the licence question.

*Failure scenario, both readings:*
- **Game content allowed.** A pre-registration pins a scene authored in the game. Either §10's import rule refuses
  the harness, or Maxim's public ledger reproduction depends on content that isn't Apache-licensed.
- **Engine fixtures only.** In that case the old rule never barred the run, since §10 already sends cradles with
  fixture bodies through Maxim's process. The entry then amends a rule it doesn't need to.

*Fix (unverified).* State which reading is meant. If game content is allowed, amend §10's import rule and §8.4 by
name, and say how a reserved asset is reproduced.

**D3. `decisions_entry_game_evidence_DRAFT.md` condition 3's alternative clause reopens round 1's B1 seam and contradicts JP17.**

Condition 3 says values reach the agent through the membrane, "or the pre-registration lists each value with the
source it was sensed from". That second branch lets harness code build a percept outside the world, which is the
bypass of Maxim's line 3 brief (`release_1_3_5.md` lines 183–215, "bypasses Overdrive's SEM adapter"). Two Overdrive
texts forbid it:
- `boundaries.md` §4.3: "Every body sensor the world simulates is world-owned".
- §4.4 B-13: "a percept is a reduction of registered physical channels, evaluated at the perceiver's position".

JP17 itself says "a harness would have to go through the membrane". By the entry's "Whose words", this clause is the
author's wording, not the owner's.

*Failure scenario.* A flooded-room pre-registration lists `is_in_water ← head liquid fraction, computed in the
harness`. It satisfies condition 3's second branch. Overdrive's B-13 is violated, yet the run counts.

*Fix (unverified).* Drop the alternative. Or narrow it to values that Overdrive's stimulus contract
(`sem_stimuli.md`) defines and the world emits, and name B-13 as the rule.

**D4. The entry's harness sentence, "stamping alone does not satisfy `lint_harness_provenance.py`": no Maxim mechanism asserts a second package's commit.**

`scripts/_provenance.py` and `lint_harness_provenance.py` on `a584c4d0` establish only Maxim's own code under test.
`executed_code_provenance` takes `maxim.__file__`, and `working_tree_dirty` and `code_tree_sha256` read Maxim's
`src`/`scripts`. The lint checks that a harness calls those guards. Nothing in it can see `simcore`. The parenthetical
reads as if the existing lint enforced condition 2 for Overdrive's tree. It doesn't, so "asserts the `simcore` it
imports" has no producer.

*Failure scenario.* A harness stamps `simcore.__version__` and calls Maxim's preflight. The lint passes, the
`simcore` tree is dirty or comes from a different checkout, and the run counts. This is the Exp 42b failure on the
other repository.

*Fix (verified against the two files).* Name the needed mechanism as a Maxim process item: a second declared code
tree in `executed_code_provenance`, refused when dirty or not at the pin. Reword the sentence to "the rule
`lint_harness_provenance.py` enforces for Maxim's own tree".

**D5. `joint_plan_DRAFT.md::§5 JP15`: the named producer can't reach the proxy, the real vehicle exists on main, and half the asks are missing.**

- **The named producer can't reach the proxy.** "Today the slice vendor; inferred": the slice vendor's only LLM
  call is `spikes/slice/slice_server/voice.py::ollama`. It refuses any host not starting with `http://127.0.0.1:`,
  so it can't call the mini's proxy at `<mini>:8099`.
- **The real vehicle exists on main.** `inference_placement.md` §2.2 owns `max_in_flight` (1 to 16, at most 10 on
  `maxim_peer`). It has `failed(overloaded)` in its outcome table, `owner_lan` and its HTTPS note (IG §7), and the
  loopback fake-server tests in its build list. It is a design with no code in `src/` yet.
- **Half the asks are missing.** JP15 lists two of line 6's four "Overdrive's side" asks (`release_1_3_5.md`
  §Line 6). Classifying a 429 as overloaded, the `owner_lan` HTTPS check and the Phase 4 fake-server tests are
  absent.
- **The hold-mark refusal has no outcome yet.** D12's refusal names the holder, and I found no outcome for it in
  the placement table. That is unverified beyond a search for "hold", "429" and "overloaded".
- **"Needed by: line 6 item 3" has no date.** 1.3.5's exit needs only item 3's approach note, so "with that item"
  has no delivering release.

*Failure scenario.* Maxim's owner reads JP15 as satisfied by a slice component that can't call the mini. The gateway
build then ships without the 429 classification or the hold refusal, and nobody owes it.

*Fix (verified by reading `voice.py` and `inference_placement.md` on main).*
- Make the vehicle `inference_placement.md` (§2.2, the outcome table, IG §7, the build checklist).
- List all four asks plus the hold refusal.
- Write "not dateable: item 3 has no release".

**D6. `README.md` row for `joint_plan_DRAFT.md`: the coverage claim is still false.**

- **OD-C13 to OD-C16 don't exist.** The README says "links JP1–JP17: every draft above, plus OD-C13–C16 and Maxim's
  asks of Overdrive". The highest tier C id on main is OD-C12, I found no OD-C13 to OD-C16 on any local or remote
  branch, and JP11 itself says "OD-C1–C12".
- **"Maxim's asks of Overdrive" is half covered (D5).**
- **Several open roadmap rows have no link.** OD-A21, OD-A22, OD-A23, OD-A24, OD-A25, OD-I9 and OD-I12 are in no
  JP row. That includes three line 6 deliveries to Overdrive (item 1 to OD-A23, item 5 to OD-A24 and OD-A14, item 8
  to OD-I9) and OD-A25's "after 1.4.0" answer.
- **"Every draft above" misses one.** `decisions_entry_DRAFT.md` is linked by no JP row (D8).

*Failure scenario.* A reader takes the README as the index, looks for OD-C13 and finds nothing, or takes the line 6
answers as tracked when they aren't. That is round 1's S3, still open.

*Fix (verified by searching for the ids).* Drop "OD-C13–C16". Either add a JP row for line 6's deliveries and
OD-A21, A22, A25 and I12, or narrow the claim to "the drafts above, except `decisions_entry_DRAFT.md`".

**D7. `joint_plan_DRAFT.md::§3` 1.3.6 row and "What this means for Overdrive": the "measured" range rests on a misread gate and a rate the cited file doesn't show.**

- **The gate.** Maxim's `roadmap_1_3_x.md` lists 1.3.6's own exit (the loop decomposition, #1361 S3–S6, B2's
  prerequisites) and calls 1.3.6 "the point at which T0 can pass". The 33 items are `release_gates.json`'s
  `gates["1.4.0"].items`, which is the 1.4.0 gate.
- **The rate.** The file hasn't changed since 2026-10-24, so the rate it shows over November is zero. The 0.5–0.75 a
  week comes from "three issues closed since November, unverified against their items".
- **What it feeds.** "Measured" then carries "At T0's measured rate, Phase 4 is 2028".

*Failure scenario.* Overdrive's planning session schedules Phase 4 for 2028 on a figure the plan calls measured.
Maxim's owner reads Overdrive as waiting on T0 rather than on A-post's ship with 1.3.6.

*Fix (verified by reading both files).* Gate 1.3.6 on its own exit list. Call the range "estimated from an
unverified issue count" until §7's December measurement exists.

**D8. A seventh copy of the old rule: `docs/maxim_upstream/decisions_entry_DRAFT.md` item 4, "Game runs never go on the results ledger".**

This is a live upstream draft, not a dated research file. Its question was answered yes by Maxim's owner on
2026-11-19, and it isn't filed: Maxim's `DECISIONS.md` on `a584c4d0` has no Overdrive entry. The new entry's "six
statements" list and its "What it amends" both miss it.

*Failure scenario.* Maxim files the 2026-11-19 entry verbatim after JP1. Maxim's `DECISIONS.md` then holds two
entries that disagree about the same rule.

*Fix (unverified).* Add it to the list, and amend item 4 in the draft before it's filed. Dated research copies
(`fire_ladder/6b_maxim_perception.md:130`, `time/skeptic.md:224`, `states_of_matter/gameplay.md:230`,
`specgen_spike/sources.md:23`) can stay as history.

### NIT

**D9. `§4 JP1` "Needed by" and `§6` step 3, "under JP1".** JP13's results are never evidence (§6 step 2 and JP13's
qualifiers), and step 3 is "a Maxim-only experiment" until step 5. A Maxim-only experiment needs no ruling about
Overdrive worlds. So JP1's only consumer is JP17, which is a candidate. *Scenario:* Maxim holds step 3's
pre-registration until JP1 is filed. *Fix:* "Needed by: a game-venue pre-registration (JP17; §6 step 3 after step 5)".

**D10. `§4 JP10` vehicle.** OD-B1–B7's vehicle is candidates §Tier B B1–B7 (roadmap "Was" column), not
`time_sense_DRAFT.md`, which covers OD-B8–B13.

**D11. The entry's "What does not change".** It says the venue "stays the owner's open question", while candidates
§Cautions gives it to "the hybrid line owner". Quote that.

## 4. Top items for the owner

1. **The evidence contract (D1–D4):**
   - The Maxim entry pins less than §10 (D1).
   - It doesn't say whether game content may enter (D2).
   - Condition 3's author-worded alternative readmits harness-built percepts (D3).
   - Its provenance assertion has no Maxim mechanism (D4).

   All four sit in the text the owner is about to hand Maxim's owner, and each is a sentence-level fix.
2. **JP15's producer (D5):** the named producer can't call the mini, and the real owner, `inference_placement.md`,
   carries all four line 6 asks.
3. **The README's coverage claim (D6):** it cites ids that don't exist.
4. **The 2028 Phase 4 headline (D7):** it rests on a 1.4.0 gate's rate labelled "measured".
