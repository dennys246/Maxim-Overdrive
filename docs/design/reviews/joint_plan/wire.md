# Joint plan draft: Wire integrity lens

**Reviewed:** `phase3/joint-plan` at `92fbe74`, against Overdrive `origin/main` `e6d6a7f`, `phase1/slice2-design`
`7f21055` and Maxim `github/main` `a584c4d0` (`<maxim-clone>`, git only); issues via `gh`, 2026-11-26.

**Counts:** 3 BLOCKER, 6 SHOULD-FIX, 3 NIT. Each proposed fix says whether I verified it.

## Contracts the diff touches

| Contract | Producer (delivering side) | Consumer (asking side) | What the consumer gets |
|---|---|---|---|
| J1, the venue ruling | Maxim `DECISIONS.md` (not filed) | J8, J10, J11; §6 step 3 | a text that conflicts with Overdrive's own owner of the same contract (B2) |
| J2 | #1773 on Maxim main, carried into 1.3.5 | the lock move (O78); O75's red gates | connects |
| J3 | #1782 (closed, 1.3.5); GHSA advisory; a comment on #1305 | Phase 4's inference path | partly connects (S2) |
| J4 | `world_clock_a_pre.md`; draft PRs #1827, #1829 | Phase 4's subset | connects; exit needs only PR 1 (S2) |
| J5 | A-post with #1361 in 1.3.6 | Phase 4's subset | connects (candidates §Not decided here) |
| J6, J7 | an unfiled plan; the 1.5 line | Phase 4 | no producer yet, stated |
| J8 | #1807 and #1810, both open, no milestone | slice 2's R6 | connects. J1 is not needed (B2) |
| J9 | #1802 (1.3.5, line 5); #1803 (no milestone); #1788 (no milestone, no plan text) | slice 2's server; Phase 4 | the delivering release is overstated (S2, N1) |
| J10 | Overdrive Phase 2 "liquid and gas fields"; a line 3 harness with no owner | E2's and E3's preregistrations | **does not connect** (B1) |
| J11 | `docs/design/research/person_reid_probe/`, on a branch only | #1810; two deferred Maxim plans | partly connects (S4, B3) |
| J12 | `drift.yml`, `tests/test_maxim_fixes_pending.py` (both on main) | M97; every cut | connects |
| J13 | a Maxim issue (`salience/novelty.py:111-112` uses the builtin `hash()`, confirmed) | not named on Overdrive's side | N2 |
| J14 | two unfiled drafts | the 1.5 hybrid line | no producer yet, stated |
| §2, the re-forecast | the upstream lane (O77) | both repositories | **no trigger runs it** (S1) |
| The ledger rule | six Overdrive copies (S5) | every Overdrive experiment design | only the README changes (S5) |

## BLOCKER

### B1. `joint_plan_DRAFT.md::§5 J10`: no planned producer exists for what the flooded room needs, and the consumer it names isn't waiting on a world

These are the two ends of J10.

**The producer side (Overdrive).** J10's vehicle is "Overdrive's Phase 2 liquid and gas fields", dated 2027-02 to 04.
§3's milestone row lists "gas, liquids" for Phase 2. But:
- `roadmap.md` §Phase 2 on `origin/main` has no liquids item. It lists sound, light, gas and radiation, convection,
  structure, load, scale, and the D26 moves (zones, vents, combustion per zone). Flooding appears only in
  `research/states_of_matter/gameplay.md` §4's Phase 2 list ("per-room liquid with portals (flooding)"), and that
  file is research, not a plan of record. `world_model.md` §2 says that liquid in zones "has a level but no position
  yet".
- The flooded room's other two inputs aren't fields at all. One is `is_in_water` "from the head's liquid fraction",
  which needs a body with a head box. The other is `oxygen` "owned by the world", the lung store of Exp 60's pattern.
  The same research file puts both in Phase 4: "Body models: … immersion and the lung store (the Exp 60 pattern)".
  `boundaries.md` §13 also says "the perceiver half of B-13 waits for the first NPC body (Phase 4)". The draft itself
  dates Phase 4 "2027 Q3 at the earliest, no upper bound". So J10's 2027-02 to 04 range is earlier than its own
  producer's phase.
- E2 needs an air pocket, which `roadmap_1_4.md` §Phase 0 defines as "a 1-tall air cell under a solid ceiling". A
  per-zone pool with one level and no position can't hold air under a lower ceiling in the same zone. The
  field-level design would have to answer that before J10's offer holds.

**The seam.** Line 3 (`release_1_3_5.md` lines 183–215) says the harness "drives the world server directly and
bypasses Overdrive's SEM adapter". If the adapter is bypassed, something else must turn the world's liquid level
into `is_in_water` and the body's state into `oxygen`, and that would be Maxim-side harness code. Two of Overdrive's
contracts forbid that. `boundaries.md` §4.3 says "every body sensor the world simulates is world-owned", and §4.4
(B-13) says "a percept is a reduction of registered physical channels, evaluated at the perceiver's position". On
top of that, `npcs_and_sem.md` §10 makes a ledger record pin "the membrane and agent contract versions", and a run
that bypasses the membrane has none to pin. The draft names none of this. It also leaves four other things unnamed:
- the interface the harness calls (`simcore` exposes no versioned API for an outside caller, only
  `simcore.__version__`);
- whether runs go through the intent log, which is the backbone of replay;
- whose lock the run uses (Overdrive's goldens and cross-tier results are recorded on its own numerical stack;
  `CLAUDE.md`, "Dependencies are locked");
- who maintains the harness when Overdrive's internals change. The harness has no owner, and the draft concedes
  that.

**The consumer side (Maxim).** "Needed by: E2's and E3's pre-registrations" is wrong in two ways:
- `roadmap_1_4.md` §Phase 3 says E2 is "MECHANISM-GATED", and that it "does not freeze until the store exists", the
  store being a Phase 5 cluster-keyed relief store. A world doesn't unblock E2. E3 depends on E2's pocket.
- The E ladder's instrument is built for Minecraft (`scripted_water.py`, `ScriptedWaterBridge`): "Composition is
  proven only through `run_minecraft_aut`". Moving E2 or E3 to Overdrive is a new design that needs all four lenses
  (line 3's own last paragraph). It isn't a precondition those preregistrations are waiting on.

**Failure scenario.** Maxim's owner names a line 3 harness owner on the strength of §7. That owner finds no
Overdrive step, brief or roadmap row producing liquids, a head box or a lung store before Phase 4. The bypass rule
then forces percepts to be built in Maxim, against B-13. E2 stays unfrozen on its relief store whatever Overdrive
ships. And the plan's headline link, "the link most likely to move a Maxim rung", moves nothing in its range.

**Fix (unverified).** Restate J10's producer as three Overdrive deliverables, each with its own phase:
1. a positioned liquid, or a pocket-capable zone;
2. a body with a head box;
3. a world-owned lung store.

Each needs a roadmap row. Name which contract the harness reads through: the membrane, or a new versioned harness
API. Re-key "needed by" to E2's design (after the relief store), not to its preregistration.

### B2. `joint_plan_DRAFT.md::§1 J1`: the DECISIONS text duplicates and contradicts the contract Overdrive already owns, and two readers would read its transfer clause in opposite ways

- **There is already an owner.** `npcs_and_sem.md` §10, "When a game-earned result can move a Maxim claim (BD-17,
  Arch 4.6)", owns this contract on Overdrive's side. It says behavioural claims "stay PARTIAL until a transfer check
  passes on a Maxim-owned task or the robot". It also requires the ledger record to pin the engine SHA, the pymaxim
  version, the membrane and agent contract versions, the placement digests and the Phase 3 items present. J1 instead
  says a run is "recorded on the ledger like any other run", with only "the Overdrive commit stamped". J1 neither
  cites §10 nor amends it. That is a second owner of one contract (B36).
- **The transfer clause is ambiguous.** J1 keeps the transfer check only "for claims that generalise beyond the
  venue … a claim about the robot or Minecraft". Candidates §Tier C requires "a transfer check in a Maxim-owned
  harness or on the robot before it moves a Maxim claim". J1's harness is itself Maxim-owned, so one reader takes
  the Overdrive run as its own transfer check. Another reader takes J1 to mean that a rung (a claim about Maxim, not
  about the robot) needs no transfer check at all. Either way, `npcs_and_sem.md` §10's PARTIAL rule is silently
  dropped.
- **It doesn't name every rule it overrides.** J1 says it "answers" candidates §Not decided here and amends D8 and
  D13. It doesn't strike the candidates document's opening sentence ("game runs never go on Maxim's ledger"). It
  also skips §Cautions, which gives the venue decision to "the hybrid line owner". Maxim's line 3 brief still lists
  "What would make an Overdrive result count as evidence?" as open.
- **Its provenance is weaker than Maxim's own rule.** The harness-provenance rule is "a result whose code-under-test
  cannot be established is not a validation". A *stamped* Overdrive commit is the `git_hash`-shaped answer that rule
  calls the wrong question, unless the harness *asserts* that the imported `simcore` is that commit, with a clean
  tree. Maxim `CLAUDE.md` adds that weak evidence "cannot be the sole evidence for a status change".
- **"Needed by" is wrong.** J8 asks for answers to questions, which needs no ruling. J11's step 1 posts results to an
  issue, which needs none. Step 2 runs offline (B3). The links that actually need J1 are J10 and §6 step 3.

**Failure scenario.** The owner files J1 verbatim. Then an E2 run in Overdrive moves T-thresholds without a transfer
check (reader one), while Overdrive's `npcs_and_sem.md` §10 still says PARTIAL. The two repositories disagree about
the same row's status, and neither text is stale by its own rules.

**Fix (unverified).** Make `npcs_and_sem.md` §10 the single statement of the contract and have J1 cite it, or have J1
supersede it by name. State whether the Overdrive harness counts as a transfer venue. Pin the membrane and agent
versions, or say why a membrane bypass is exempt. Assert the imported `simcore` rather than stamping it. Strike the
candidates document's opening rule by name. Cut "needed by" to J10 and §6 step 3.

### B3. `joint_plan_DRAFT.md::§6` steps 2–4: the chain's outputs don't feed the next step, and none of the Maxim triggers it names can fire on what it produces

- **Step 2 to step 3: the venue is wrong.** Step 2 "runs offline on abstract descriptors". The stage 1–3 probe
  (`person_reid_probe/protocol.md` on the slice 2 branch) is likewise synthetic features through Maxim's
  `_sensor_embed`, with no world. Step 3 then makes it "a Maxim pre-registration whose venue is the game", but the
  game can't produce a perceivable person until step 5, which is 2027 Q3 at the earliest. An offline encoder probe
  is an ordinary Maxim offline script, like `scripts/orient_substrate/*`, and needs no J1. So step 3 depends on step
  5, not on step 2. The proposed 2027-02 preregistration is either mislabelled (not a game venue) or dated a phase
  too early.
- **Step 3, modality resolution §4: misquoted.** The plan is DEFERRED, and its revive trigger was re-keyed on
  2026-10-07 to "the grounding line's GL3 registry+provenance stage ships". "Only when a graded consumer exists" is
  §4's condition for *promoting F-B*, population coding for **scalar/angular sensors**. It names its own test, "the
  pre-registered two-arm ablation" of `6_graded_orient_curve.py`. Person identity over many features isn't a graded
  scalar consumer, and naming it can't revive a plan that waits on GL3.
- **Step 3, set-point-aware neutral: wrong trigger.** The governing banner (2026-09-19) reads "Revive when: a 1.4 rung
  names the gap it fills". The quoted 2026-09-16 phrase is "a roadmap want that STRUCTURALLY needs a small, same-side
  move of **one** graded sensor … and then only as the adaptive (salience-layer) design". A person probe is neither
  a 1.4 rung nor one graded sensor. The tombstone itself puts habituation "DOWNSTREAM of a stationary encoding".
- **Step 4, the forward model: not an identity mechanism.** `latent_forward_model.md` §4.2 item 5's map is "a
  per-item → consequence-node membership map" for affordance items in S5's acquired-equivalence test. "Only the S5
  harness calls it … it has no production caller", and T4a/Dormant applies if S5 doesn't earn. It doesn't recognise
  a person.
- **Step 4, fabric §B: the trigger doesn't fit.** Its revive trigger is "GL3 … ships AND a 1.4 rung needs
  cross-modal binding". `person_reid_DRAFT.md` Q2 already notes that Overdrive's need is *single-modality*. The plan
  presents that open question as a delivery.

**Failure scenario.** Maxim's owner accepts step 3 on the draft's word. The preregistration cites §4 and the set-point
trigger. Maxim's Bio-faithful lens reads both deferred headers and rejects the citations. And the "game venue"
can't run until Phase 4's bodies exist, so step 3's 2027-02 date slips by at least two quarters with no slip
reported (S1).

**Fix (unverified).** Re-sequence the chain:
1. step 2 is an offline Maxim-side probe, with no J1;
2. a game-venue preregistration comes after step 5.

Replace each trigger citation with the trigger as written, and say plainly that none fires today. Drop the §4.2
item 5 citation unless a person-to-node map is actually proposed.

## SHOULD-FIX

### S1. `joint_plan_DRAFT.md::§2` "Re-forecast": no trigger runs it in either repository

- **Overdrive.** The lane's brief (`next_steps/3_upstream_sync.md`) scopes each rerun to restating statuses "in
  O76's form … and nothing more". It holds no tables of dates, it runs "never while step 4 is open", and it runs
  only at a tag or a release. No Overdrive tag is scheduled, and 1.3.5 is 2–4 weeks out. Meanwhile §6's
  2026-11-27 and 12-04 dates fall inside step 4.
- **Maxim.** There is no trigger at all. Its dates of record are milestone due dates, set only by Maxim's owner.
- **One owner.** §7 then copies "this plan's links" into `roadmap.md` as rows. The draft's tables and the roadmap
  rows become two copies of each range, and the J ids are "in this draft only", with "Maxim may renumber".

**Failure scenario.** Step 4 slips a week. No lane runs, and J11's range passes with no slip reported, against §2's
own rule.

**Fix (unverified).** Name a brief, or amend O77's, that owns re-forecasting. Put the ranges in exactly one place, the
roadmap rows, and make the draft point there. Name the Maxim-side trigger, for example the release checklist that
M97 already uses.

### S2. `§4 J3, J4, J9`: the "delivering release" column assumes lines that don't gate 1.3.5's cut

`release_1_3_5.md` §Exit says: "Lines 3, 4 and 5 do not gate the cut. Whatever has merged ships." It also requires
only the A-pre plan's *first* PR.
- **#1802 (J9)** is in line 5, so the release that carries it isn't fixed.
- **PR 1b (J4)** is a draft, and the exit doesn't wait for it.
- **OD-I13 (J3)** rides #1305 only as a comment. Line 2's #1305 row covers the global `random`/`np.random`, and
  nothing in Maxim's plan commits the backend half to 1.3.5 (cite the comment, not the issue).

**Failure scenario.** Overdrive moves its lock to 1.3.5 (O78), expecting the onset latch. The latch didn't merge,
and the slice 2 server's sustained heat floods the PainBus.

**Fix (verified against §Exit).** Write "1.3.5 if merged by the cut (line 5 doesn't gate it)". Keep each red gate until
a release is read.

### S3. `§4/§5`, and the README row's "links J1–J14 over every row above": the link list has gaps

Missing links, all on Maxim's `main` or Overdrive's:
- **Line 6, "the peer mesh, for Overdrive".** That is items 1–9, with OD-A14, A23, A24, I9 and I10 from
  `inference_placement.md`. The §3 gate cites line 6, but no J link says what Overdrive consumes from it.
- **Maxim's asks of Overdrive in line 6.** These are "Overdrive's side, not Maxim's": `max_in_flight` from the
  advertised capacity, 429 classified as overloaded, the `owner_lan` HTTPS check, the fake-server tests. D12 adds "a
  client-side check is an ask to Overdrive". None of them is in §5.
- **What Phase 4 waits on.** OD-B1 to OD-B7, the Exp 64a prereg (`exp64_cradle_conduct_prereg_DRAFT.md`) and the SEM
  additive plan (`sem_breaking_change_plan_DRAFT.md`) are in no J link.

**Fix (unverified).** Add the links, or narrow the README claim to the rows actually linked.

### S4. `§5 J11`: the vehicle is a path on an unmerged branch, and nobody owns the posting

`docs/design/research/person_reid_probe/` exists only on `phase1/slice2-design`. Step 4's migration may move it, since
that branch "migrates after it". The draft names no session to post the results to #1810. The lane can't do it
during step 4.

**Fix (unverified).** Name the slice 2 design session as the poster, and cite a commit SHA rather than a branch path.

### S5. `README.md` diff, and `§7`: one copy of the ledger rule changes and five don't, and the ruling has no record

The rule "game runs never go on Maxim's ledger" also stands in:
- `roadmap.md:489` (a standing rule);
- `boundaries.md` §8.4 ("stay off Maxim's ledger");
- `npcs_and_sem.md` §10 (its title, and line 1008);
- `hybrid_1_5_line_DRAFT.md:38`;
- `CLAUDE.md`.

§7 names only `CLAUDE.md`. The owner's 2026-11-26 ruling also has no entry in `docs/design/decisions/`. Its only home
is §1 of a DRAFT, and step 4's freeze bars new record files.

**Fix (unverified).** Record the ruling when step 4 allows, with its id, and list every copy that it amends.

### S6. `§3`, the row for Overdrive's Phase 2 start: the gate and scope cells cite plan content that doesn't exist

"Gas, liquids", and "each field's closed-form and cross-grid tests" for liquids, come from a research file, not from
the roadmap (B1). This feeds J10's range directly.

**Fix (verified by reading `roadmap.md` §Phase 2).** Cite the roadmap's list, or add liquids to it by an owner
decision.

## NIT

- **N1. `§4 J9`.** "#1788 … A-post, 1.3.6" rests only on Overdrive's OD-A4 row. Maxim has no milestone for it and no
  plan text placing it. Say "proposed by Overdrive".
- **N2. `§5 J13`.** No Overdrive consumer is named. Name the Phase 4 replay or determinism test that would turn red
  on the salted `hash()`, so the link has an asking end.
- **N3. `§3`, Maxim 1.3.6's gate.** "T0, the decomposition gate" is a 1.4.0 threshold. `roadmap_1_3_x.md` §1.3.6
  calls 1.3.6 "the point at which T0 can pass". That makes it a precondition, not 1.3.6's own gate.
