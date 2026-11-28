# DRAFT for Maxim and Overdrive: one plan, with dates, both ways

**Status:** drafted in Maxim Overdrive on 2026-11-26 on the owner's ruling of that day, folded after one review round
and its delta (`docs/design/reviews/joint_plan/`); no third round (stop rule). No date or commitment here is of record
in either repository: every date is a **proposed range** with its method, or says it can't be dated. This branch
merges before Overdrive's step 4 starts (owner, 2026-11-26).

**Read against:** Maxim `github/main` `a584c4d0` (2026-11-26) and its tags; Overdrive `origin/main` `e6d6a7f`. Status
and scope belong to the rows and plans each link cites; this plan says what a link connects and when. Re-check
against a fresh fetch before acting.

**Ids.** `JP1`, `JP2`, … are this plan's links (several Maxim documents use `J` ids). Overdrive's `OD-` ids keep their
roadmap rows; Maxim may renumber anything it accepts.

## 1. The ruling

**Owner, 2026-11-26 and 11-27:** game evidence may count for Maxim rungs, through Maxim's own process, and only when
the data is pinned to valid commits of both repositories. **JP1** is that ruling as a Maxim `DECISIONS.md` entry
plus Overdrive's matching records: [decisions_entry_game_evidence_DRAFT.md](decisions_entry_game_evidence_DRAFT.md).
Its five conditions are pre-registered, pinned before data, sensed not handed (the membrane, or a listed-values
route signed off by Maxim's Bio-faithful and Environment lenses), a verified world, and licensed content: Apache-2.0
fixtures by default, with the owner's content as a later ablation arm. It keeps Maxim's transfer-check rule whole
and leaves open where the transfer check runs.

## 2. How dates work, and what is missing

- **A proposed range** states its method. Maxim's 1.3.x releases came 8, 19, 7 and 30 days apart (median 13.5).
  Merged PRs ran 64–70 a week in October's first three weeks and 22–43 a week since (7-day windows from 10-01, UTC).
  Overdrive is twelve days old, with one tag (`v0.1.0`, 2026-11-23). Its step order belongs to its next planning
  session (O79 (5)), so this plan gives no Overdrive step dates.
- **A date of record** is a range the owner commits where the link is delivered: a milestone due date on Maxim's
  GitHub, or a row in Overdrive's roadmap.
- **The re-forecast has no owner yet.** Overdrive's upstream lane may only restate statuses, and never during step 4.
  Maxim has no such trigger. Until both exist, the ranges below are a snapshot of 2026-11-26. Two amendments would
  give them owners (§7): the lane's brief gains a re-forecast duty, and Maxim's cut checklist re-reads this plan's
  links. Until then ranges live only in this file, and roadmap rows cite a `JP` id, never a copied date.
- **A slip is reported, never absorbed:** in the issue or row that tracks the link, with the new range and its cause.

## 3. Maxim's milestones

| Release | Gate | Proposed range | Method |
|---|---|---|---|
| 1.3.5 | `release_1_3_5.md` §Exit; lines 3–5 don't gate the cut | 2026-12-06 to 12-22 | plan start (11-22) plus the median interval, up to 1.3.4's 30 days |
| 1.3.6 | its own exit (loop phase 2: #1150, #1361 S3–S6); it is "the point at which T0 can pass" | **not dateable** | no measured rate for its scope |
| 1.4.0 | T0, the 1.4.0 decomposition gate (`scripts/release_gates.json`: 33 items, one evidenced on the day the gate was made, 2026-10-15; the file unchanged since 10-24), then B2 → B3 → B4 and E1 | **not dateable.** At the rate the tree supports (0 to 0.5 items a week, counting three closed issues not checked against their items): 2028-02 at the earliest, no latest. At an assumed 2–4 a week from the 1.3.5 cut, plus four rungs at an assumed 3–6 weeks: 2027-04-25 to 09-28 | the tree's rate, and an assumed one, each labelled |

**What this means for Overdrive.** Phase 4 (NPC bodies with real Maxim) needs most of tier A's subset after 1.3.6,
the embeddable contract (1.4.x) and the stepped `think` (OD-A15, Maxim's 1.5 line). It can't be dated, and on the
tree's rate it is 2028 or later. A real date needs T0's rate measured (§7); the scope that sets it is Maxim's.

## 4. What Overdrive needs from Maxim

| Link | Ask (rows) | Maxim vehicle | Delivering release | Needed by |
|---|---|---|---|---|
| JP1 | the ruling recorded, and a harness check that asserts the imported `simcore` | `DECISIONS.md`; a harness item | none; before the first evidence run | any game-venue pre-registration; JP17 |
| JP2 | released fixes: OD-I1, OD-I3 (and OD-I6, tooling) | #1773 | 1.3.5 | Phase 4's subset; Overdrive's lock move (O78) |
| JP3 | OD-I10, OD-I11, OD-I13 | line 6 item 6, the GHSA advisory, #1305 | 1.3.5 if in before the cut, else the next | Phase 4's inference path |
| JP4 | A-pre: OD-A2, A3, A5 (in part), A6 | `world_clock_a_pre.md`; PR 0 (#1798) meets 1.3.5's world-clock condition; PRs #1827, #1829 | PR 1a/1b in 1.3.5 only if green before the cut; A6 in 1.3.6 | Phase 4's subset |
| JP5 | A-post and #1361: OD-A1, A4, A8, A9, OD-I8 | A-post with 1.3.6 | 1.3.6 | Phase 4's subset |
| JP6 | the embeddable agent (OD-A10–A12, A14, A17, A18) and the settle amendment (OD-A16) | a plan from `embeddable_agent_DRAFT.md`; #1150 | 1.4.x | Phase 4 |
| JP7 | OD-A15 (stepped `think`), OD-A25 (streaming); OD-A7 (keyed RNG) | the 1.5 line; after the 1.4.0 cut | 1.5; 1.4.x | Phase 4 |
| JP8 | #1807 and #1810 answered | `autonomic_layer.md` §3.4/3.5; fabric §B | none (answers) | slice 2's R6 |
| JP9 | #1802; #1803's ownership decision; #1788 | 1.3.5 line 5 (not gating); an owner decision; A-post ("planned for A-post with B2", the issue's thread) | open; none; 1.3.6 | slice 2's server; Phase 4 |
| JP10 | tier B: OD-B1–B7 (the candidates document's tier B), OD-B8–B13, Exp 64a's pre-registration | `time_sense_DRAFT.md` (B8–B13), `exp64_cradle_conduct_prereg_DRAFT.md`; none filed | 1.4.x | Phase 4's exit |
| JP11 | the SEM refinements (OD-C1–C12; OD-I2 is a docstring nit) | `sem_breaking_change_plan_DRAFT.md`, not filed | after tier A | Phase 4 on |
| JP12 | the hybrid line (OD-H1–H6) | `hybrid_1_5_line_DRAFT.md` | 1.5 | Phase 5 on |
| JP18 | line 6's answers: OD-A23 (item 1's measurement), OD-A24 and OD-A14 (item 5's design pass), OD-I9 (item 8), OD-I10 (item 6); and the questions OD-A21, A22, OD-I12 | `release_1_3_5.md` line 6; the `maxim_response_2` batch | 1.3.5 where line 6 gates; else open | Phase 4's inference path; non-blocking questions |

JP6, JP7 and JP10–JP12 aren't dateable until their plans are filed. Filing them is Overdrive's next upstream-lane
work, after step 4.

## 5. What Maxim needs from Overdrive

| Link | Offer | Overdrive vehicle | Needed by | Proposed range |
|---|---|---|---|---|
| JP13 | the re-ID probe's results, with their qualifiers (§6) | `docs/design/research/person_reid_probe/` on `phase1/slice2-design`, posted to #1810 by that branch's session after its results review | #1810 | 2026-12-04 to 12-11. Stage 3's last cells end about 11-27 (the mini's run logs: 66 cells left at 11-26 22:43, 690–9,760 s each over four shards; not in the tree). The write-up and its review are an assumed 3–7 days |
| JP14 | the drift job read before every cut (M97); strict red gates that flip on a fix (O75) | `.github/workflows/drift.yml`; `tests/test_maxim_fixes_pending.py` | every cut | exists; the 1.3.5 flip is intended |
| JP15 | line 6's Overdrive-side asks: `max_in_flight` on `maxim_peer` from advertised capacity (about 1 today), a 429 classified as overloaded, the `owner_lan` HTTPS check, the Phase 4 fake-server tests | `docs/design/inference_placement.md` §2.2 (its Phase 4 transports) | line 6 item 3 (advertised capacity) | Phase 4's transports; not dateable before them |
| JP16 | a defect: builtin `hash()` in `salience/novelty.py::update_with_entity` under a comment that says "deterministic". The ids are dict keys and eviction sorts by time, so the only cross-process effect found is an improbable 31-bit collision | a low-priority Maxim issue | any patch | file on the owner's go-ahead |
| JP17 | **a candidate, not a link:** a world venue for Maxim's E-ladder (line 3's flooded room) | none yet. Liquids and oxygen are in no Overdrive phase (only `states_of_matter` research), and the head and lung models are Phase 4 body work | E2 is mechanism-gated on a relief store and built on Minecraft (`roadmap_1_4.md`) | not dateable. Next: Overdrive's planning session decides whether liquids enter the roadmap; Maxim decides whether a game venue serves the E-ladder |

## 6. The person-perception line

Evidence and questions only. The mechanisms and their dates are Maxim's to design, through #1810's answers.

1. **The probe closes (JP13).** What it shows so far, with synthetic people and places, unreviewed:
   - Maxim's sensor encoder ranks people correctly offline, AUC within 0.016 of the raw features (Stage 1);
   - it packs them near cosine 1, so the sensor default of 0.85 merged every person in the cells checked;
   - person features summed with drawn-place sensors in one world vector: in Stage 2's 82 of 274 cells, all 18
     conditions that read row 3 also fail offline on all three layers, and the other 4 conditions read no row 3
     (encoding check, `7f21055`; its attribution is not committed yet).

   An uncommitted illustration on `_sensor_embed` suggested that centring on a population mean widens the threshold
   window without changing the ranking. It is not evidence; step 2 measures it.
2. **An exploratory ablation in Overdrive, never evidence.** It runs offline on abstract descriptors and reimplements
   fusion, so nothing it finds can earn a rung. It names the two Maxim decisions it argues against and measures each
   one's stated failure:
   - the adaptive set-point, closed: "2% jitter separates 20/20; rest embeds to the zero vector; strands frozen
     prototypes" (`archive/world_channel_weighting.md`);
   - fabric §C's ban on familiarity touching recognition thresholds.

   It includes Maxim's place-code population coding as an arm, and tests register integration only with a spatial
   register, as fabric §B defines it. It is designed after step 4, in the order the planning session sets.
3. **A Maxim pre-registration, if the ablation motivates a claim.** It is designed in Maxim and run fresh on Maxim's
   code, in a Maxim-owned harness, on a new population generator and seeds. Until the world side (step 5) exists,
   it is a Maxim-only experiment, and needs no JP1.
4. **No Maxim trigger fires on this line today.** Searched: fabric (needs cross-modal binding and GL3), modality
   resolution (revives on GL3; its "graded consumer" promotes population coding), the set-point plan (a 1.4 rung
   names the gap), and `latent_forward_model.md` §4.2 item 5 (an item-to-consequence map, not identity). The path
   is #1810's Q1–Q7.
5. **Overdrive's world side.**
   - Perceivable body features become stimulus rows at the eyes and ears (`sem_stimuli.md`), attenuated by distance,
     light and smoke, and never name a person.
   - Which person an NPC attends to is Maxim's attention. The choice reaches the world only as the NPC's own orient
     or gaze command, and the world renders what that body's sites receive: one canonical region, not a row set per
     visible body (fabric §B).
   - This needs Phase 2's light and sound and Phase 4's bodies.

## 7. What can be committed now

These need a decision, not a release:
- **Maxim:**
  - file JP1;
  - give the 1.3.5 milestone a due date in its range;
  - decide #1803;
  - add JP1's harness check to the line 3 work;
  - have its owner read `release_gates.json` at the end of December, so T0 has a measured rate and 1.4.0 a range;
  - add this plan's links to the cut checklist.
- **Overdrive:**
  - merge this branch, then start step 4;
  - approve filing JP16;
  - in the first session after step 4, record the ruling with its O10 and §13 exceptions (JP1's Overdrive side);
  - in the planning session, give the upstream lane its re-forecast duty, and decide JP17's liquids question;
  - the owner authors content for the content-ablation arm when ready; nothing waits on it.

## 8. Not decided here

- Where a game result's transfer check runs, and who decides it.
- The person mechanisms, which are Maxim's.
- Overdrive's step order and phase dates, which belong to its planning session.
- Any date this plan calls assumed.
