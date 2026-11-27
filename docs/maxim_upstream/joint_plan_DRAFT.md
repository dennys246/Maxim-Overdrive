# DRAFT for Maxim and Overdrive: one plan, with dates, both ways

**Status:** drafted in Maxim Overdrive on 2026-11-26, on the owner's ruling of that day (§1). Nothing here is
committed in either repository. Every date below is a **proposed range**, derived from measured pace by the method in
§2; a range becomes a date of record only when the owner commits it in the repository that delivers it.

**Read against:** Maxim `github/main` `a584c4d0` (2026-11-26) and its tags; Overdrive `origin/main` `e6d6a7f`
(2026-11-25) and the unmerged `phase1/slice2-design` at `7f21055`. Both repositories warn that plan text drifts:
re-check every number against a fresh fetch before acting on it.

**Ids.** Links between the repositories are `J1`, `J2`, … in this draft only. Items already on Overdrive's roadmap
keep their `OD-` ids; Maxim may renumber anything it accepts.

## 1. The ruling, and what it changes

**Owner, 2026-11-26:** game evidence may count for Maxim rungs, **through Maxim's own process**: a pre-registration
frozen on Maxim's `main` before data, the four-lens design review, and the ledger as Maxim keeps it. Goal set the
same day: one plan across both repositories, with versions and dates on what each needs from the other.

Maxim's `main` says the opposite in three places, so the ruling needs a Maxim record before any link below can name
a game-sourced rung:
- `docs/plans/overdrive_refactor_candidates.md`, the opening rule: "game runs never go on Maxim's ledger";
- `docs/plans/release_1_3_5.md` D8 and D13: "Overdrive is engineering in 1.3.5, not evidence", which repeats the rule
  and leaves "the transfer-check venue for tier C" an open owner question;
- the same candidates document, §Cautions and §Not decided here, which name that venue as undecided.

**J1, the `DECISIONS.md` entry (text for Maxim's owner to edit and file):**

> **2026-11-26 — Overdrive evidence can earn rungs, through this repository's process.** An Overdrive world can be
> the venue for a rung's evidence when the rung's pre-registration names it, is frozen on `main` before data, and
> passes the four-lens design review; the run is driven by a Maxim-owned harness (line 3's rules: strict red gates,
> the interpreter asserted, the Overdrive commit stamped) and recorded on the ledger like any other run. The
> transfer-check rule stands for claims that generalise beyond the venue: a result earned in the game moves a claim
> about the robot or Minecraft only with its own transfer check. This answers the tier C venue question
> (`overdrive_refactor_candidates.md` §Not decided here) and amends D8/D13 from 1.3.6 on; 1.3.5 stays engineering.

The last clause is a proposal, not part of the ruling: it keeps 1.3.5's scope, which is already 68 of 87 issues open,
from moving.

## 2. How dates work in this plan

- **Proposed ranges come from measured pace,** with the method stated in each row. Maxim's 1.3.x releases came 8, 19,
  7 and 30 days apart (median 13.5); merged PRs ran about 70 a week in October and 22–43 a week in November.
  Overdrive is twelve days old: 76 merged PRs, one tag (`v0.1.0`, 2026-11-23), and narrow steps that take 0.5–3 days
  of the owner's attention each. Overdrive's ranges are therefore ±2× at least.
- **A date of record** is a range the owner has committed in the delivering repository: a milestone due date on
  Maxim's GitHub, or a row date in Overdrive's `docs/roadmap.md`. This draft only proposes.
- **Re-forecast** at every Maxim release and every Overdrive tag, which are already the triggers of Overdrive's
  upstream lane (O77). The lane updates the table in §4 and §5 and reports each slip in both repositories.
- **A slip is reported, never absorbed.** When a link misses its range, the delivering repository says so in the
  issue or row that tracks it, with the new range and the cause, and every link that depends on it moves in the same
  update.

## 3. Milestones on both sides

| Milestone | Scope | Gate | Proposed range | Method |
|---|---|---|---|---|
| Maxim 1.3.5 | `release_1_3_5.md`: gates, Overdrive's asks, the orchestrator line, fix groups | its §Exit: line 1 merged, the AvServ hardline, line 2's S items, the world-clock plan's first PR, line 6 items 1/2/7 | 2026-12-07 to 12-23 | plan start (11-22) plus the median interval, widened toward 1.3.4's 29 days for the design-gated items |
| Overdrive step 4 | records layout and migration | its brief's exit test | 2026-11-27 to 12-03 | its brief; not started |
| Overdrive slice verdict | slice week 4 | the verdict note | due 2026-12-18 | a date already of record |
| Maxim 1.3.6 | loop phase 2: #1150 and the loop stack, #1361 S3–S6, B0b | T0, the decomposition gate: 1 of 33 items evidenced | 2027-01-15 to 03-31, low confidence | 2–4 gate items a week from 1.3.6's start |
| Overdrive Phase 1 exit | torch a slab, the same at laptop and rig | `roadmap.md` Phase 1 exit | 2027-01-15 to 03-31 | step pace; the fire ladder (6.1b) has no code yet |
| Overdrive Phase 2 start | sound, light and visibility, gas, liquids | each field's closed-form and cross-grid tests | 2027-02 to 04 | after Phase 1's exit |
| Maxim 1.4.0 | T0–T4, T4a, T7, T8; E2, E3, GL5 only if recorded in time | `roadmap_1_4.md` §Release thresholds | 2027-03 to 07, very low confidence | 1.3.6 plus B2 → B3 → B4 and E1, at an assumed 3–6 weeks a rung |
| Overdrive Phase 4 | NPC bodies with real Maxim | the Exp 64a verdict | 2027 Q3 at the earliest, no upper bound | tier A's subset, and OD-A15 (stepped `think`) in Maxim's 1.5 line |

Two facts set the shape of everything below. **Maxim's T0 gate is the long pole for both repositories:** most of
what Overdrive needs (tier A's A-post, GL3.B1, the forward model's S4) waits for the fence it lifts. And **Overdrive's
Phase 4 has no date until Maxim's 1.5 line has one**, because the stepped `think` (OD-A15) is in it.

## 4. What Overdrive needs from Maxim

| Link | Ask | Maxim vehicle | Delivering release | Needed by | Proposed range |
|---|---|---|---|---|---|
| J1 | the venue ruling recorded (§1) | `DECISIONS.md` | none (a record) | J8, J10, J11 | 2026-12 |
| J2 | OD-I1, OD-I3, OD-I6 released (fixed by #1773, in no release) | 1.3.5 | 1.3.5 | Phase 4's subset; Overdrive's lock moves (O78) | with 1.3.5 |
| J3 | OD-I10, OD-I11, OD-I13: `NO_PROXY`, the blocked `base_url` advisory, seeds on backends | #1782 (closed), GHSA advisory, #1305 | 1.3.5, or the advisory's own release | Phase 4's inference path | with 1.3.5 |
| J4 | tier A's A-pre: OD-A2, A3, A5, A6 | `world_clock_a_pre.md` (#1787 merged; PRs #1827, #1829 in draft) | 1.3.5 for PR 1a/1b; A6 in 1.3.6 | Phase 4's subset | 1.3.5 to 1.3.6 |
| J5 | tier A's A-post and #1361: OD-A1, A4, A8, A9, OD-I8 | A-post with 1.3.6 | 1.3.6 | Phase 4's subset | with 1.3.6 |
| J6 | the embeddable agent: OD-A10–A12, A14, A17, A18, and the settle amendment (OD-A16) | a plan from `embeddable_agent_DRAFT.md` (rated sound by Maxim's review) and #1150 | 1.4.x | Phase 4 | not dateable until the plan is filed; proposed filing 2026-12 |
| J7 | the stepped `think` (OD-A15) and keyed RNG (OD-A7) | the 1.5 line; after the 1.4.0 cut | 1.5 | Phase 4 | not dateable; Overdrive asks Maxim for a range at 1.4.0's cut |
| J8 | person value and person re-identification: #1807 (GL2c) and #1810 (fabric §B) answered | `autonomic_layer.md` §3.4/3.5; `deferred/cross_modal_perception_fabric.md` | answers need no release; mechanisms 1.4.x | slice 2's R6; Phase 4's vendor | answers 2027-01; see §6 |
| J9 | #1802 (onset latch), #1803 (process-wide `_human_is_driving`), #1788 (tool energy never reaches NAc) | 1.3.5 line 5; an owner decision; A-post | 1.3.5, open, 1.3.6 | slice 2's server and Phase 4 | #1803: an owner decision by 2026-12 |

## 5. What Maxim needs from Overdrive

| Link | Offer | Overdrive vehicle | Needed by (Maxim) | Proposed range |
|---|---|---|---|---|
| J10 | **a flooded-room world for the oxygen rungs.** Line 3's first scenario (`is_in_water` from the head's liquid fraction, world-owned `oxygen`) maps onto E2's air pocket and E3's strategic breathing, and E1 needs "a contingency a reasonable no-bio floor can lose" | Overdrive's Phase 2 liquid and gas fields, served to line 3's Maxim-owned harness (its owner is unassigned today) | E2's and E3's pre-registrations | a field-level design in 2027-01; fields with Phase 2, 2027-02 to 04. **This is the link most likely to move a Maxim rung, and its harness has no owner** |
| J11 | person-recognition evidence: the re-ID probe's results, then a second probe (the ablation, §6) | `docs/design/research/person_reid_probe/` and its successor | #1810; modality resolution's "graded consumer" trigger; the set-point plan's revival trigger | results to #1810 2026-12-04 to 12-11; ablation 2027-01 |
| J12 | the drift job read before every cut (M97) and strict red gates that flip on an upstream fix (O75) | `.github/workflows/drift.yml`, `tests/test_maxim_fixes_pending.py` | every cut | exists; the 1.3.5 flip is expected and intended |
| J13 | defects found from the game: the builtin `hash()` in `salience/novelty.py::update_with_entity`, salted per process under a comment that says "deterministic" | a Maxim issue | any patch release | file once the owner agrees, 2026-11 |
| J14 | a seeded, replayable host for the hybrid line and time sense (OD-H1–H6, OD-B8–B13) | `hybrid_1_5_line_DRAFT.md`, `time_sense_DRAFT.md` | the 1.5 hybrid line | not dateable until filed |

## 6. The person-perception line, end to end

This line started the plan. Its critical path crosses both repositories four times.

1. **Overdrive: the re-ID probe closes.** Stage 3 finishes 2026-11-27; the post-run fold, the final read, the results
   and their review take about a week. Results go to #1810 2026-12-04 to 12-11 (J11). What they show so far:
   - Maxim's sensor encoder ranks people correctly offline, AUC within 0.016 of the raw features;
   - it packs them near cosine 1, so its default sensor threshold of 0.85 merges everyone;
   - mixing a person's features with place sensors in one world vector breaks recognition when the place changes.
   A centring test on Maxim's own `_sensor_embed` widens the usable threshold window 7–14× without changing the
   ranking.
2. **Overdrive: the ablation probe.** It has its own frozen protocol and runs offline on abstract descriptors:
   - modality subsets: body, voice, gait, clothing;
   - fusion: one mixed vector, additive late fusion, and register integration (Maxim's stated form, where
     out-of-register inputs depress the response);
   - representation rungs: raw, then an online norm, then a pretrained norm, then a pretrained discriminative one;
   - conditions: disguise, voice change, a mismatched face and voice, a missing modality, near-average people, a
     drifting norm, and exposure widening;
   - populations: P from 20 to 500.
   It answers Maxim's tombstones on its own terms: the adaptive set-point's "rest embeds to zero" and "strands frozen
   prototypes", and the fabric's ban on familiarity touching thresholds. It is designed after step 4, runs in
   2027-01, and is reported to #1810 and to the modality-resolution plan.
3. **Maxim: a pre-registration that uses it.** With J1 recorded, the probe's design can become a Maxim
   pre-registration whose venue is the game. It goes through Maxim's four-lens review, is frozen before data, and is
   run by a Maxim-owned harness. It names person recognition as the graded consumer that
   `deferred/modality_resolution_and_alignment.md` §4 waits for, and as the "small, same-side move of one graded
   sensor" that `deferred/setpoint_aware_neutral.md` revives on. Proposed: pre-registration 2027-02, after 1.3.6's
   start.
4. **Maxim: the mechanisms.** A centred person modality beside `_sensor_embed`, never an edit to it (G2); the
   item-to-node map of `latent_forward_model.md` §4.2 item 5; fabric §B's identity. All wait for the fence and
   GL3.B1: 1.4.x, no earlier than 2027-04.
5. **Overdrive: the world side.** Perceivable body features as stimulus rows at the eyes and ears, attenuated by
   distance, light and smoke, with identity never named to Maxim (`sem_stimuli.md`, the re-ID draft's §4). This needs
   Phase 2's light and sound and Phase 4's bodies: 2027 Q3 at the earliest.

Steps 4 and 5 meet at Phase 4. Neither repository waits idle for the other before then: steps 1–3 are evidence and
need no new mechanism on either side.

## 7. What can be committed now

These need only a decision, not a release, so the owner can make them dates of record this week:
- **Maxim:** file J1; give the 1.3.5 milestone a due date in its range; name an owner for line 3's harness (J10);
  decide #1803's ownership question (J9).
- **Overdrive:** start step 4 (everything on the slice and design branches waits for it); set the date for J11's
  results; approve filing J13; add this plan's links to `docs/roadmap.md` Phase 3 at step 4, as rows citing
  `J1`–`J14`; and amend `CLAUDE.md`'s "Game runs never go on Maxim's results ledger" to name the ruling, once J1
  is filed (an owner edit: that file is the owner's instructions).

## 8. Risks, and what this plan does not decide

- **T0 is unmeasured scope.** It has 32 open items, and no orchestrator slice has landed since 2026-10-30. 1.3.6 and
  1.4.0 have no defensible date until its rate is measured over a month. A 1.3.7 is possible (D14).
- **One rig, shared** by Minecraft, experiments and robot runs (D12; #1708 blocked). Game runs need no rig, which is
  part of J10's value.
- **The owner is the bottleneck in both repositories:** merges, signing, rulings and playtests. Every range here
  assumes the owner's present availability.
- **Overdrive's step 4 freeze.** Until step 4 merges, Overdrive opens no PR from its slice and design branches and
  writes no record file. Every Overdrive date in this plan moves with step 4.
- **Not decided here:** how a game result transfers to a robot claim (J1 keeps Maxim's transfer-check rule); the
  person mechanisms' design, which is Maxim's; Overdrive's Phase 4 date.
