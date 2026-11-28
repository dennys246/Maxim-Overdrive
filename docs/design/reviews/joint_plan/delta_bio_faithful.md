# Joint plan draft, delta round: Bio-faithful integration lens

**Tree reviewed:** staged index, tree `a48cc3903883a28336397e1c779a5b890d8be13a`, on `phase3/joint-plan` (the fold of
round 1, not yet committed), diffed against `92fbe74`. Files read: `docs/maxim_upstream/joint_plan_DRAFT.md`,
`docs/maxim_upstream/decisions_entry_game_evidence_DRAFT.md` (new) and `docs/maxim_upstream/README.md`, all from the
index. **Maxim read:** `github/main` `a584c4d0` in `<maxim-clone>`, by `git show` and `git grep` only. **Overdrive
read:** the index's `docs/design/npcs_and_sem.md` §10, `docs/design/boundaries.md` §13 and
`docs/design/decisions/npcs_and_sem.md` (O10), and the re-ID probe at `7f21055`.

**Stop rule:** this is the last round. New findings in fold text go to the owner, not to another round.

**Counts.** Round 1's 13 findings: 11 `fixed`, 2 `open` (BF-B1 on one clause, BF-N2). New: 0 BLOCKER, 4 SHOULD-FIX,
4 NIT. Every proposed fix below is unverified unless marked.

## A correction to my round-1 report

BF-S1 said J1 answered "a different question" from the tier C venue, namely `release_1_3_5.md` line 3 item 3's. That
was half wrong. Line 3 item 3 reads: "What would make an Overdrive result count as evidence? That is the tier C venue,
which is the owner's call." Maxim's own text treats the two questions as one. `overdrive_refactor_candidates.md`
§Not decided here ("The transfer-check venue for tier C") and D8 ("The transfer-check venue for tier C stays an open
owner question") name the transfer check. The fold's split is right: the entry answers the evidence question and
leaves the transfer-check venue open. But Maxim's line 3 item 3 now reads as answered and unanswered at once. D-S2
covers that.

## Round-1 findings: status from the tree

| Finding | Status | Evidence in tree `a48cc39` |
|---|---|---|
| BF-B1 | **open** (one clause) | Safeguards (b), (c) and (d) are folded as the entry's conditions 2, 4 and 1. Condition 2 pins both commits, the scene digest and the grid spacing before data, and refuses dirty trees. A scene tuned after the freeze changes the digest, so (d)'s "does not tune it after the freeze" holds through condition 2. Condition 1 puts the scenario under the confounding lens. Condition 4 cites verification status and Known gaps. Safeguard (a) is folded without its checker: the owner-approved text had "the Bio-faithful lens signs off on the list", and condition 3 drops it. See D-S1. |
| BF-B2 | fixed | §6 opens "Evidence and questions only. The mechanisms and their dates are Maxim's to design, through #1810's answers." The old step 4 (centred modality, item-to-node map, 1.4.x date) is gone. JP8 is now "#1807 and #1810 answered", release "none (answers)". The map appears only in step 4's trigger search, described correctly. |
| BF-S1 | fixed | The entry: "Every adoption still needs a transfer check before it moves a claim … this entry does not answer it. A game-earned result stays PARTIAL until its transfer check passes". JP1 in §1: "keeps Maxim's transfer-check rule whole". The narrowing to "claims that generalise" is gone. The round-1 report's third bullet (say which decider: Cautions' "hybrid line owner" or D8's "owner") isn't addressed; it is carried as D-N4. |
| BF-S2 | fixed | The entry drops "strict red gates" for evidence runs. Its Overdrive side says "A ledger run is not a red gate, so evidence runs need their own exception" and proposes O10's amendment, recorded at step 4 with the owner's wording. §7 lists it. |
| BF-S3 | fixed | Step 2 names both decisions. It quotes `archive/world_channel_weighting.md` §Closed verbatim, with all three reasons, including "2% jitter separates 20/20" (checked against `github/main`). It names "fabric §C's ban on familiarity touching recognition thresholds" (an accurate paraphrase of §C and §Deliberately NOT doing), and it "measures each one's stated failure". |
| BF-S4 | fixed | Centring is now "an uncommitted illustration … It is not evidence, and step 2 measures it." The 7–14× number is gone. The 18-of-22 claim cites the encoding check at `7f21055` and says "its attribution is not committed yet". See D-N3 on the qualifiers. |
| BF-S5 | fixed | The set-point trigger claim is gone. Step 4 now lists that trigger as not firing. Step 2 adds "Maxim's place-code population coding as an arm". F-A's knife-edge warning no longer applies, because the threshold readings left the plan. |
| BF-S6 | fixed | Step 2 is "never evidence". Step 3's pre-registration is "designed in Maxim and run fresh on Maxim's code, in a Maxim-owned harness, on a new population generator and seeds, under JP1". A new generator does more than the held-out conditions I asked for. |
| BF-S7 | fixed | "It tests register integration only with a spatial register, as fabric §B defines it." If the offline probe can't supply a spatial register, the arm drops out instead of becoming a caricature. |
| BF-S8 | fixed (ownership) | "Which person an NPC attends to is Maxim's attention, never the membrane's." The failure scenario (the membrane picks the nearest body) is now forbidden. How the choice reaches the world is not stated. See D-S4. |
| BF-N1 | fixed | §5 no longer lists the set-point trigger as a Maxim need. |
| BF-N2 | **open** | Neither draft names grounding's provenance kinds (`apparatus`, `narrated`) for game runs. There is no fold and no reason recorded. |
| BF-N3 | fixed (substance) | Condition 1 requires the four-lens design review. Line 3 item 3 is still not cited; it is folded into D-S2. |

## Answers to the brief's questions

- **Do the decisions draft's safeguards close BF-B1?** Three of the four do. "Sensed, not handed" does not, for two
  reasons. First, its main route, through Overdrive's membrane, is closed until the embeddable contract ships (D-S1).
  Second, its fallback route, a list of values in the pre-registration, has no named checker. In practice, every
  evidence run before 1.4.x takes the weaker route, and nobody is charged with checking it. The harness-pin clause
  also claims an enforcement that doesn't exist (D-S3).
- **Does §6 still design Maxim's cognition?** No, apart from one framing in step 5 (D-S4). Steps 2 and 3 are an
  Overdrive exploratory probe that is labelled never-evidence, plus a pre-registration designed in Maxim. The
  ablation's arms do name candidate mechanisms, but they are explicitly argued against named Maxim decisions, and
  they cannot earn anything.
- **Does it name the decisions it argues against, and quote them right?** Yes. The `world_channel_weighting.md`
  quote is verbatim. The fabric §C paraphrase is accurate. Step 4's description of `latent_forward_model.md` §4.2
  item 5 is accurate: a per-item → consequence-node membership map with a harness-only freeze trigger.
- **Is "no Maxim trigger fires on this line today" accurate?** Yes, on `github/main` `a584c4d0`:
  - The fabric revives when "GL3's registry+provenance stage ships AND a 1.4 rung needs cross-modal binding". Modality
    resolution revives when "GL3's registry+provenance stage ships". `thalamic_relay.md`'s status (2026-10-24) and
    `docs/plans/README.md` say "GL3.B1 onward is not built", so neither has fired.
  - The set-point plan revives when "a 1.4 rung names the gap it fills". `roadmap_1_4.md` has no person,
    re-identification or face rung (searched: person, re-ident, face, cross-modal, binding, set-point).
  - Step 4 quotes all four triggers correctly.
- **Is attention moved correctly?** Partly: the ownership is right and the channel is missing (D-S4).

## New findings

### SHOULD-FIX

#### D-S1. "Sensed, not handed" falls back to its weaker route until 1.4.x, and that route has no checker

**Where:** `decisions_entry_game_evidence_DRAFT.md::The entry` condition 3, against Overdrive's
`docs/design/boundaries.md::§13` ("Until it ships, real Maxim behind the adapter is a strict red gate").

Condition 3 offers two routes. Either every value reaches the agent "through Overdrive's membrane (its SEM adapter
and stimulus contract)", or the pre-registration lists each value with its sensed source. Boundaries §13 keeps real
Maxim behind the adapter a strict red gate until the embeddable contract ships (JP6, 1.4.x). An evidence run is not
a red gate (the entry says so). So until 1.4.x, the membrane route is closed to evidence runs. The proposed O10
amendment doesn't open it: O10 is about developer mode, and §13 is a separate statement that isn't in the entry's
list of six. That leaves only the list route. The owner-approved text of safeguard (a) had the Bio-faithful lens sign
off on the list, and condition 3 dropped that clause.

**Failure scenario.** In 2027, the E-ladder pre-registration lists `oxygen` as "sensed from the head's liquid
fraction", and the harness reads it straight from the world server. The four-lens review reads the pre-registration,
but no lens is charged with checking that list against what the harness actually reads. The harness passes the
ground-truth value on, the rung's gates pass, and the row is earned on an oracle. That is BF-B1's first scenario,
reopened through the fallback route.

**Fix (unverified).** Restore the dropped clause in condition 3: "Maxim's Bio-faithful and Environment lenses sign
off on the list". The Environment lens's charter is already D1, "no synthetic sensor/reward", per
`docs/experiments/DESIGN_REVIEW.md`. Then do one of two things, as the owner chooses:
- add `boundaries.md` §13 to the Overdrive-side amendments beside O10; or
- state that before the embeddable contract, only the list route exists.

#### D-S2. "What it amends" omits the line 3 text that the conditions contradict

**Where:** `decisions_entry_game_evidence_DRAFT.md::The entry` ("What it amends"), against `release_1_3_5.md`
§Line 3 items 2 and 3 and its rules line ("Game runs stay off Maxim's ledger, and the harness runs under O10's strict
red gates (D8, D13)").

Line 3 item 2 specifies the Maxim-owned harness: it "drives the world server directly and bypasses Overdrive's SEM
adapter", and it "stamps the Overdrive commit". Conditions 2 and 3 forbid both for evidence runs. Line 3 item 3 says
the evidence question "is the tier C venue". The entry answers that question while saying it doesn't answer the tier
C venue. "What it amends" lists only the candidates doc's opening rule and D8/D13.

**Failure scenario.** The 1.3.5 harness skeleton is built to line 3 item 2, and it is the natural starting point for
the first evidence harness. Nothing in Maxim's text says the bypass and the stamp end at the engineering boundary, so
both carry over into an evidence run. Separately, a Maxim reader sees line 3 item 3 marked as the owner's open call
while the entry treats it as answered.

**Fix (unverified).** Add line 3 items 2 and 3 and the rules line to "What it amends". Say that the 1.3.5 skeleton's
bypass and stamp are engineering-only and don't satisfy conditions 2 and 3. Say that the entry answers line 3 item
3's evidence question and separates it from the transfer-check venue, which stays open.

#### D-S3. The harness-pin clause credits a lint with a check it doesn't make

**Where:** `decisions_entry_game_evidence_DRAFT.md::The entry`: "a Maxim-owned harness that asserts the `simcore` it
imports is the pinned commit (stamping alone does not satisfy `lint_harness_provenance.py`)".

`release_1_3_5.md` line 3 item 2 says the stamp exists "since the harness-provenance rule covers only the `maxim`
import". `git grep -i 'simcore\|overdrive'` over `scripts/lint_harness_provenance.py` and `scripts/_provenance.py`
on `github/main` finds nothing. The lint's "stamping is detection, refusing is enforcement" rule applies to Maxim's
own code under test, not to `simcore`.

**Failure scenario.** A harness that only stamps the `simcore` commit passes the lint. The entry reads as if the lint
would refuse it, so no reviewer looks for the assertion, and condition 2's "refuse to run against anything else"
holds by attention only.

**Fix (unverified).** Reword the clause: the harness must assert the `simcore` commit, and the lint does not check
that today. Extending the lint to the Overdrive import is a Maxim process item, and until then the four-lens review
(the Wiring lens) checks it.

#### D-S4. Step 5 states who owns attention, but not how the choice reaches the world, and it leaves per-person rows open

**Where:** `joint_plan_DRAFT.md::§6` step 5 ("Perceivable body features become stimulus rows at the eyes and ears …
and never name a person. Which person an NPC attends to is Maxim's attention, never the membrane's.").

Fabric §B solves correspondence with the body. After the observer orients, "what is at center" is the percept:
"Fixed-cardinality encoding. One canonical region, not N detections." Two things don't fit that:
- "Which person an NPC attends to" presupposes that the world has already split the scene into persons for attention
  to choose among.
- "Stimulus rows" with no cardinality rule allows a row set per visible body. A set of rows per body is the world
  solving individuation and correspondence: these features belong together, as one body. That is the
  variable-cardinality fork §B removes.

Attention can only reach the world as an effector act (gaze or orient), and step 5 doesn't say that.

**Failure scenario.** The step-5 design emits one feature-row set per visible body, and Maxim's attention picks an
index. No person is named, so condition 3's letter holds. But every recognition result is conditioned on a
segmentation the world performed, and Maxim's correspondence-by-orienting is never exercised.

**Fix (unverified).** Replace the sentence with one that says three things:
- the membrane renders what lies in the observer's foveal region (and, for sound, its bearing) after the observer's
  own orient or gaze command;
- the region has a fixed cardinality, with no per-body row sets;
- which body ends up at the fovea follows from Maxim's orienting policy acting through the body.

This is contract text, because it says what the membrane emits, so I'd fold it now. If the owner prefers to defer
it, the trigger is the step-5 world-side design (the stimulus contract's person rows), and that design's review
carries this finding.

### NIT

- **D-N1.** Condition 3's "a field's exact value" is ambiguous. Every receptor reads a field, and an ideal receptor's
  output is a field's exact value. Say instead "any value not produced by a declared receptor model at a body site",
  which is Overdrive's own row contract in `sem_stimuli.md`.
- **D-N2.** The entry leaves out one condition from Overdrive's own §10 rule ("When a game-earned result can move a
  Maxim claim"): "every world-only affordance declared". Add it to condition 1 or condition 3.
- **D-N3.** Step 1 drops two sets of qualifiers:
  - "The sensor default of 0.85 merges every person" holds, in `results.md` at `7f21055`, for the cells without
    stress or twins, name set a, σ_w 0.1 and 0.4, where per-person merge at P = 20 is 1.00. Name those cells, or keep
    "in the cells checked" next to that bullet.
  - "18 of 22 conditions" can't be derived from committed text: `check.json` has no summary, and the per-cell
    verdicts need the uncommitted attribution. Label it "unreviewed", as the centring note is labelled.
- **D-N4.** Round 1's BF-S1 third bullet is still unaddressed. Cautions names "the hybrid line owner" as the decider
  of the tier C venue. D8 and the entry say "the owner". Say which.

## What I checked and found sound

- The README's new rows and its JP1 pointer match the drafts.
- The entry's "Whose words" line keeps the author's "from 1.3.6" scope separate from the owner's ruling.
- §8 still leaves the person mechanisms with Maxim.
- JP17 now says that a harness "would have to go through the membrane", consistent with condition 3.
- §10 of `npcs_and_sem.md` does say that behavioural claims "stay PARTIAL until a transfer check passes on a
  Maxim-owned task or the robot", as the entry cites.

## Top items for the owner

1. **D-S1.** Restore the sign-off on the read list (Bio-faithful and Environment lenses). Decide whether
   `boundaries.md` §13 joins O10 in Overdrive's amendments. Without one or the other, "sensed, not handed" is
   unchecked for every evidence run before 1.4.x.
2. **D-S2.** Add line 3 items 2 and 3 and the rules line to "What it amends", so the 1.3.5 harness skeleton's bypass
   and stamp can't carry into an evidence run.
3. **D-S4.** One sentence in step 5: the membrane renders the foveal region after the observer's own orient command,
   with fixed cardinality and no per-body rows.
4. **D-S3.** Correct the `lint_harness_provenance.py` parenthetical. The lint doesn't cover `simcore`.
