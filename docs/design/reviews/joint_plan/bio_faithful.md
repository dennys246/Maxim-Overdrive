# Joint plan draft: Bio-faithful integration lens

**Commit reviewed:** `92fbe74` on `phase3/joint-plan` (`docs/maxim_upstream/joint_plan_DRAFT.md`, new;
`docs/maxim_upstream/README.md`). **Maxim read:** `github/main` `a584c4d0` in `<maxim-clone>`, by `git show` and
`git grep` only. **Overdrive read:** `origin/main` and `phase1/slice2-design` at `7f21055` (the re-ID probe and
`person_reid_DRAFT.md`). Maxim issues #1807 and #1810 were checked on GitHub: both open, #1810 with no comments.

**Counts:** 2 BLOCKER, 8 SHOULD-FIX, 3 NIT. All proposed fixes are unverified unless marked.

## What the draft gets right

- §8 leaves the person mechanisms' design with Maxim and keeps Maxim's transfer-check rule. §6 step 5 never names
  identity to Maxim. The re-ID draft it builds on searched Maxim and asks #1810 questions rather than proposing a
  plan.
- J1 keeps Maxim's process intact: the pre-registration frozen on `main`, the four-lens review, a Maxim-owned harness
  and the ledger as Maxim keeps it.
- The §1 citations are correct. `overdrive_refactor_candidates.md`'s banner says "game runs never go on Maxim's
  ledger", and `release_1_3_5.md` D8/D13 says "Overdrive is engineering in 1.3.5, not evidence".

The findings below are about the places where the draft goes beyond that.

## BLOCKER

### BF-B1. J1 applies line 3's engineering harness rules to evidence runs, and that admits an oracle and an unfrozen venue

**Where:** `joint_plan_DRAFT.md::§1` (J1's text: "driven by a Maxim-owned harness (line 3's rules: strict red gates,
the interpreter asserted, the Overdrive commit stamped)").

Line 3's rules (`release_1_3_5.md` §Line 3, item 2) were written for engineering tests. Two of them are wrong for
evidence:
- **The harness "drives the world server directly and bypasses Overdrive's SEM adapter."** The adapter is where
  Overdrive keeps its standing rule that an NPC gets only what it could sense: percepts come from cells, and no
  world-assigned name or id is passed on. A harness that skips the adapter can read anything the world server holds.
- **The Overdrive commit is "stamped" at run time, not pinned before data.** A stamp records which world ran. It
  doesn't stop the world from changing between the freeze and the run. Phase 2's liquid and gas fields, which J10
  depends on, will still be changing during 2027-02 to 04.

**Failure scenarios.**
1. E2's harness reads `oxygen`, or for J11 a person's feature row or slot, straight from the server. The NPC is
   handed a number it could never sense, the rung's gates pass, and the row reads EARNED on an oracle. No lens sees
   it, because J1 doesn't ask what the harness reads.
2. Between E2's freeze and its run, Overdrive changes how the head's liquid fraction is integrated (say a 6.1b-style
   reconstruction fix). The stamp records the new commit. The pre-registration still reads as frozen, but the
   contingency it was reviewed against is no longer the one that ran.
3. The venue's author is also the party that benefits from a Maxim win. `baseline_floors.md` warns that a
   contingency built so the floor loses is "a strawman in our favour and is for the confounding lens to refuse".
   J10 advertises exactly that ("E1 needs a contingency a reasonable no-bio floor can lose"). J1 has no rule that
   puts the world's contingency under Maxim's control.

This is the core of the safeguard question: as written, J1 doesn't protect Maxim's claims from the venue.

**Fix (unverified).** Add four rules to J1:
- (a) Every percept in an evidence run reaches Maxim through Overdrive's membrane, under its leak rules. Failing
  that, the pre-registration lists every value the harness reads, with its sensed source, and the Bio-faithful lens
  signs off on the list.
- (b) The pre-registration pins the Overdrive tag or commit, the scene digest and the grid spacing before data. The
  harness refuses to run against anything else.
- (c) The pre-registration cites the verification status of each world field the rung uses, and Overdrive's Known
  gaps for those fields.
- (d) The world's contingency is written into the pre-registration and reviewed by Maxim's confounding lens.
  Overdrive implements it and does not tune it after the freeze.

### BF-B2. §6 step 4 prescribes Maxim's person mechanisms and dates them, which contradicts §8 and pre-answers #1810

**Where:** `joint_plan_DRAFT.md::§6` step 4 ("A centred person modality beside `_sensor_embed` … the item-to-node map
of `latent_forward_model.md` §4.2 item 5; fabric §B's identity … 1.4.x, no earlier than 2027-04"), and the "mechanisms
1.4.x" entry in §4 J8.

§8 says "the person mechanisms' design, which is Maxim's". Step 4 names that design anyway, three times, and each
choice is a cognition decision that #1810 (still unanswered) or Maxim's records leave open or refuse:
1. **The route.** `person_reid_DRAFT.md` Q3 asks Maxim to choose between the Receptor registry channel and §B's own
   encoder. Fabric §B and its target-state table route identity through content encoders (a foveal image encoder, a
   cochlear filterbank) straight into the EC. `world_channel_weighting.md` D3 notes that content embeddings "never
   reach `_sensor_embed`". "A person modality beside `_sensor_embed`" picks the scalar-sensor branch of Q3 without
   saying so.
2. **The item-to-node map.** In `latent_forward_model.md` §4.2 item 5, this map is a per-item membership map frozen
   by "a harness-only trigger", tiered "as an experimenter control … it has no production caller" (grounding G13
   repeats this). Its key is the item, which the harness knows. Applied to people, the key would be who the person
   is: the oracle that the re-ID draft §4 promises never to supply ("Overdrive won't keep a person table and feed
   Maxim its ids"). That is the opposite of §B's "Identity is never declared".
3. **Centring.** An online or population norm in the encoder path is the adaptive set-point that
   `world_channel_weighting.md` closed (see BF-S3).

**Failure scenario.** Maxim's owner reads a dated plan spanning both repositories. Step 4 names three mechanisms with
a release line and a date, and J8 reads "mechanisms 1.4.x". The mechanisms enter 1.4.x scope as Overdrive's request,
before §B's design owner has answered Q1–Q7, and one of them keys recognition on an identity the world supplies.

**Fix (verified by reading only).** Rewrite step 4 as "the mechanism Maxim's answer to #1810 names". Leave it undated
until the answer exists, and gate it on the fabric's own revive trigger (G4, which the re-ID draft's Q2 asks about).
Drop the reference to the `latent_forward_model.md` map, or move it into #1810 as an explicit question ("is a
membership map ever keyed on a person?"). I verified that #1810 has no answer yet (0 comments) and that §4.2 item
5(b) reads as quoted above.

## SHOULD-FIX

### BF-S1. J1 says it answers the tier C venue question, but it answers a different one and narrows the transfer rule

**Where:** `joint_plan_DRAFT.md::§1` (J1's "This answers the tier C venue question") against §8 ("Not decided here:
how a game result transfers to a robot claim").

The open item in `overdrive_refactor_candidates.md` §Not decided here is "**the transfer-check venue** for tier C", and
D8 repeats it. J1 answers a different question: whether the game can be the venue for the evidence itself. That is
`release_1_3_5.md` line 3 item 3's question ("What would make an Overdrive result count as evidence?"), which J1
doesn't cite. J1 says nothing about where the transfer check runs, and §8 says that is undecided. The two sections
contradict each other.

J1 also narrows the Cautions rule. Cautions says "Before it moves a claim, **every** adoption needs a transfer check."
J1 requires one only for "claims that generalise beyond the venue".

**Failure scenario.** E2 is EARNED in Overdrive. Under J1 the rung counts toward the 1.4.0 release thresholds with no
transfer check, because the rung's claim is "about Maxim", not "about the robot". But a Maxim rung is a
generalising claim by nature: it says a mechanism does its job in a body. Reading J1 that way is the overfitting the
Cautions section names.

**Fix (unverified).**
- Say that J1 answers line 3 item 3 and leaves the transfer-check venue open.
- State what a game-venue row supports: the ledger row names its venue, and any release threshold or roadmap claim
  built on that row needs its transfer check unless Maxim's owner rules otherwise.
- Cautions names "the hybrid line owner" as the decider and D8 names "the owner's call". Say which applies.

### BF-S2. J1's "strict red gates" can't record a pass, and Overdrive's O10 forbids the runs J10 needs

**Where:** `joint_plan_DRAFT.md::§1` (J1) and §7 (the Overdrive amendments).

A rung is EARNED when "every frozen gate of that rung's prereg PASS[es]" (`roadmap_1_4.md` §Release thresholds). A
strict `xfail` that passes fails the suite, so an evidence run can't be a strict red gate.

Overdrive's O10 (`docs/design/decisions/npcs_and_sem.md`) reads: "No developer mode with real Maxim before tier A,
except inside strict red-gate tests." J10's runs (2027-02 to 04) come before tier A.

**Failure scenario.** The E2 harness is built to J1's text, under strict red gates. The first passing run turns the
suite red, so either the gate is loosened (Overdrive's rules forbid that) or the run is never recorded. On the
Overdrive side, O10 blocks the run outright.

**Fix (unverified).** Name the form an evidence run takes, separate from the red gates. Add an O10 amendment to §7's
Overdrive list, recorded in `decisions/npcs_and_sem.md`, beside the CLAUDE.md edit.

### BF-S3. The ablation argues against two recorded "do not re-propose" decisions without saying so

**Where:** `joint_plan_DRAFT.md::§6` step 2 ("It answers Maxim's tombstones on its own terms").

Pushing back is right when the game's evidence warrants it. But the draft has to name the decision it argues
against, and say what reopening it takes. It doesn't:
- **The adaptive set-point.** `world_channel_weighting.md` §Closed — do not re-propose lists "adaptive set-point
  (habituation in the encoder)" with three reasons: "2% jitter separates 20/20; rest embeds to the zero vector;
  strands frozen prototypes". The draft quotes the last two and leaves out the first, which is the one a
  per-person online norm is most exposed to (frame jitter dominating once the population mean is subtracted). The
  ablation's "online norm" and "drifting norm" rungs are this mechanism.
- **Familiarity and thresholds.** Fabric §C and §Deliberately NOT doing: "Salience/novelty on the recognition
  threshold … Recorded so it is not re-proposed." The ablation's "exposure widening" condition is familiarity
  widening the recognition radius, which is exactly the positive-feedback loop §C describes.

**Failure scenario.** The ablation reports in 2027-01 that exposure widening helps. Maxim's readers see a closed item
reopened by a game probe, with no argument for why the closure's measurements don't apply.

**Fix (unverified).**
- Name both decisions, and say that reopening them is Maxim's owner's call, through a Maxim plan or experiment.
- Give the argument. A person modality has no rest reading, so "rest embeds to zero" may not transfer. Familiar-face
  tolerance (Burton et al. 2005, already cited in the re-ID draft) is the biology against §C's "ACh/NE gate learning
  rate, not thresholds".
- Make the ablation measure the banned failure: centroid collapse under long exposure at P = 500.

### BF-S4. The centring evidence in §6 step 1 has no committed source

**Where:** `joint_plan_DRAFT.md::§6` step 1 ("A centring test on Maxim's own `_sensor_embed` widens the usable
threshold window 7–14×"; and "mixing a person's features with place sensors … breaks recognition").

I searched `phase1/slice2-design` (`git grep` for "7–14", "centring" and "centred" under the probe directory and
`spikes/`) and the slice2-design worktree's files. `results.md` has no centring section and no A-world reading.
`encoding_check/` holds only `check.json` and `run.log`, with no summary.

**Failure scenario.** The number reaches #1810 or Maxim's owner as the evidence behind a centred person modality,
which is a pushback against a tombstone (BF-S3). Nobody can check it. If a later reading corrects it, the plan has
already carried it across both repositories.

**Fix (unverified).** Cite the file and section once it is committed and reviewed. Until then, mark both claims
"unreviewed, not yet in `results.md`".

### BF-S5. Step 3 misreads two revive triggers and leaves Maxim's own lever out of the ablation

**Where:** `joint_plan_DRAFT.md::§6` step 3, and the representation rungs in step 2.

- **The set-point trigger.** `setpoint_aware_neutral.md` revives on "a roadmap want that STRUCTURALLY needs a small,
  same-side move of **one graded sensor** … and then only as the adaptive (salience-layer) design". Its later banner
  narrows that to "a 1.4 rung names the gap it fills". Person re-identification is a direction problem across 4–10
  features: Stage 1 says the encoding "preserves the ranking and compresses it toward cos 1". That isn't one graded
  sensor. And `world_channel_weighting.md` later found that the salience layer "does not exist for sensor channels"
  ("a new build in a place that only looks occupied").
- **The graded-consumer trigger.** `modality_resolution_and_alignment.md` §4's trigger promotes **F-B, population
  coding** (`similarity/place_code.py`, already shipped), and names its test: "a pre-registered two-arm ablation (raw
  scalar vs `_place_code`)". The ablation's rungs (raw, online norm, pretrained norm, pretrained discriminative) have
  no place-code arm. §4 also warns that F-A per-modality thresholds near 0.99 are "knife-edge", and the probe's
  selected thresholds sit at 0.99–0.999.

**Failure scenario.** Maxim's owner checks the claimed triggers against the plans. The set-point trigger doesn't fit,
and the trigger that does fit names a test the ablation left out. The pre-registration then has to be redesigned
around Maxim's own lever.

**Fix (unverified).** Drop the set-point trigger claim, or argue for it explicitly. Add a place-code arm. Cite F-A's
warning beside the threshold readings.

### BF-S6. The pre-registration would be designed from the ablation's own data

**Where:** `joint_plan_DRAFT.md::§6` steps 2–3 ("the probe's design can become a Maxim pre-registration").

The ablation runs in 2027-01 on Overdrive's population generator. The pre-registration follows in 2027-02, built
from the same design.

**Failure scenario.** The hypotheses and thresholds are chosen after the ablation has measured those exact conditions
on the same generator. The pre-registration is "frozen before data" in letter only, and the safeguard J1 relies on is
empty for this line.

**Fix (unverified).** Report the ablation to #1810 labelled exploratory. Have the pre-registration use fresh seeds and
a held-out set of conditions, and list every ablation result its hypotheses were drawn from.

### BF-S7. "Register integration" on abstract descriptors would be a caricature of §B

**Where:** `joint_plan_DRAFT.md::§6` step 2 (fusion: "register integration (Maxim's stated form, where out-of-register
inputs depress the response)").

Fabric §B's register is spatial: superior-colliculus receptive fields lining up, a sound's bearing against what is at
centre. An offline probe on abstract descriptors has no space, so "register" can only be defined there as feature
agreement.

**Failure scenario.** "Register integration" loses to late fusion, and the result is read as evidence against
Maxim's stated form, when the probe never implemented that form.

**Fix (unverified).** Define the arm on perceived position (the voice's bearing against the body's position, which is
the probe's "mismatched face and voice" condition). If that can't be done offline, say so and move the arm to step 5's
world.

### BF-S8. Step 5 doesn't say who chooses which person is read

**Where:** `joint_plan_DRAFT.md::§6` step 5, which inherits the re-ID draft §4's "the one its own attention selects".

**Failure scenario.** The membrane picks the nearest or most salient body and emits that person's rows. Attention,
which is cognition, has moved into Overdrive, and every recognition result is conditioned on the world's choice.

**Fix (unverified).** State that the world renders whatever the observer's own orienting act puts at its fovea
(§B's convention: the body solves correspondence), and that the choice of target is Maxim's.

## NIT

- **BF-N1.** `§5` J11 lists "the set-point plan's revival trigger" as something Maxim needs. Maxim records no such
  need. It is Overdrive's pushback, so it belongs in §4 or its own row, not in §5.
- **BF-N2.** `§1` J1 should name grounding's provenance kinds for game runs. Harness writes (resets, scripted floods)
  are `apparatus` (G16), which is never credited. World events the narrator writes are `narrated` (G6).
- **BF-N3.** `§1` J1 says nothing about line 3 item 3's own condition: a claim from the brief gets all four lenses
  "because a new world, a new bridge and a new harness make a new design". J1 should cite it. Under Overdrive's rule
  "Search Maxim before proposing to it", the ask should show it has found what Maxim already says.

## Answers to the brief's questions

- **Citations and duplication.** The J8 and J11 asks are questions to existing plans (#1810 to the fabric, #1807 to
  GL2c), not duplicates. Step 4 is the exception: it designs inside #1810's open scope (BF-B2). J1 cites the
  documents it amends but not line 3 item 3, which already frames the question (BF-S1, BF-N3).
- **Faithful to Maxim's stance.** Partly. §B's emergent identity is kept in step 5. But step 4's scalar route and
  item map lean away from it (BF-B2), the register arm risks a caricature (BF-S7), and two closures are argued
  against without being named as closures (BF-S3), with evidence that isn't committed yet (BF-S4).
- **J1 and the bio-faithful claims.** The safeguard isn't adequate as written. It lacks a membrane or read-list rule,
  a venue pinned before data, and Maxim control of the contingency (BF-B1). It narrows the Cautions transfer rule
  (BF-S1). Its harness form can't record a pass (BF-S2).
- **Cognition moving into Overdrive.** Not in the plan's own Overdrive steps, with two exceptions. BF-B2's item map
  would key recognition on a world-supplied identity. BF-S8's attention selection is unassigned and would fall to
  the membrane by default.
