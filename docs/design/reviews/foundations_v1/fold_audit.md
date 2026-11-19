# Fold audit: the foundations review, as folded at 18623ce

- **Auditor:** independent fold auditor (adversarial; read-only apart from this file). The upstream-draft items were
  graded by a delegated reader against `docs/maxim_upstream/*` and Maxim `origin/main` 7084f561. The auditor did not
  re-verify that reader's citations, apart from where they bear on the design docs (marked below).
- **Commit:** 18623ce (`phase1/design-v2`)
- **Date:** 2026-11-16
- **Read:** the seven reviews in this directory (Architecture, Executor, Wire integrity, Determinism, Trust boundary,
  Bio-faithful, Maxim process); `boundaries.md` v3 and `npcs_and_sem.md` v2, both in full along with their fold tables;
  `docs/roadmap.md` Phase 1 and Phase 3; `docs/maxim_upstream/README.md`, plus the drafts that the delegated reader
  went through; and the 18623ce diffs to `world_model.md` and `realtime_lanes_coop.md`.
- **Not read:** the `delta1_*.md` files. They appeared untracked in this directory while the audit was running, so
  this audit is independent of them.
- **Grades:** FOLDED means the text resolves the failure scenario. PARTIAL means the text addresses it, but the
  scenario still occurs. OVERCLAIMED means a table says folded and the text doesn't back it. WRONG-FIX means the fold
  introduces a new defect.

## Summary

Every BLOCKER and every SHOULD-FIX was graded: 22 BLOCKERs and 81 SHOULD-FIXes. The SHOULD-FIX count is 81, not 82.
See "Counts" below.

| Review | BLOCKER F / P / O / W | SHOULD-FIX F / P / O / W |
|---|---|---|
| Architecture | 1 / 2 / 0 / 0 | 13 / 2 / 0 / 0 |
| Bio-faithful | 2 / 0 / 0 / 0 | 6 / 1 / 0 / 0 |
| Determinism | 4 / 1 / 0 / 0 | 9 / 2 / 1 / 0 |
| Executor | 1 / 1 / 0 / 0 | 9 / 2 / 0 / 0 |
| Maxim process | 3 / 0 / 0 / 0 | 9 / 5 / 0 / 0 |
| Trust boundary | 3 / 0 / 0 / 0 | 8 / 2 / 0 / 0 |
| Wire integrity | 3 / 1 / 0 / 0 | 8 / 3 / 1 / 0 |
| **Total** | **17 / 5 / 0 / 0** | **62 / 17 / 2 / 0** |

No item is a strict WRONG-FIX. Three folds do introduce new defects, recorded under the items they came from:
- **Arch B2:** the agent-lane thread is a new held resource, and nothing bounds it.
- **TB2-S5:** content-dependent landing conflicts with the rule it was folded next to.
- **DR-S5:** the wrong "de-duplication window" evidence was copied into both design docs.

**Verdict.** This fold is much better than the earlier three. Most rows are true, and the agent contract is coherent at
the level of its pieces. The gaps sit where two findings met in one section and were resolved without a word: BF2-8
against TB2-B3, BF2-2 against TB2-S5, and the barrier against the no-deadlock invariant. The other gaps are where a
table points at a fold that has no table.

## Ids claimed nowhere

Every id appears in at least one design fold table, except these 14:

> DR-S12, X-7, X-8, MP-S1, MP-S2, MP-S3, MP-S4, MP-S6, MP-S7, MP-S8, MP-S10, MP-S11, Wire B4, Wire S2

`npcs_and_sem.md` sends them to "the upstream drafts' fold" in a prose line under its table. That fold has no table.
`docs/maxim_upstream/README.md` names none of these ids, and the drafts cite only TB2-B1 to B3, Arch B1 and B3, DR-B1,
DR-B2, DR-S5, Wire B3, Wire S12, X-6, X-9, BF2-3, BF2-5, BF2-8, DR-B5, MP-S9 and MP-S13. So for these 14, nothing
claims a fold in a place a reviewer can check. They were graded from the draft text (see below), and nine of them are
FOLDED. Five other rows are part-delegated the same way: X-1 (the draft half), X-10, Arch S14, DR-S5 (the exit test)
and MP-B1 (the survey).

**Fix:** give `docs/maxim_upstream/README.md` a fold table, or put a row for each of these ids in `npcs_and_sem.md`'s
table.

## Counts

- **Neither table has summary counts.** Each has only rows: boundaries has 66 (17 BLOCKER, 49 SHOULD-FIX) and npcs has
  76 (18 BLOCKER, 58 SHOULD-FIX). So no total can be wrong, but none can be checked either.
- **The npcs header says "22 BLOCKER, 82 SHOULD-FIX, 51 NIT".** The 22 and the 51 match the reviews. 82 matches the
  reviews' headers, but `executor.md` claims "12 SHOULD-FIX" and lists 11 (X-3 to X-13). The true SHOULD-FIX count
  is **81**.
- **A row label in boundaries drifts from its finding.** "Arch S7 the log record lacks the sub-tick key" is a fair
  paraphrase of the finding "part 2 quietly extends boundaries' log record".

## BLOCKERs not FOLDED

### Arch B2: mode (a) and dilation deadlock (PARTIAL; new defect)

Mode (a) is gone, and DLP-B2's five fixes are all present (npcs §4.4). But the no-deadlock invariant is stated against
the wrong resource, on a premise the same fold contradicts:
- **npcs §4.4:** "Under O6 agents never block inside a turn (`step` returns values), so a worker is held only by an
  LLM call in flight, and the host's wait set counts only those."
- **npcs §6.3 and boundaries §7.1:** the barrier counts an agent as parked when it is "returned from `step`, **or
  waiting at the gateway for a held response**. Released work … runs to its next park before the tick advances." So
  agent code does block mid-execution at the gateway, holding its agent-lane thread.
- **"One owner per agent"** says "Each agent is owned by one agent-lane thread at a time". That allows a pool, and the
  pool size is never stated.

**Surviving scenario.** With K agent-lane threads and more than K agents, K agents are parked at the gateway on early
results held until T+D. Agent B is due to step at T+1, but no thread is free, so B never returns from `step`. The
barrier never closes and the world never reaches T+D. That is Arch B2's cycle on a different resource. The one-worker
test (one worker, two NPCs) watches LLM workers only, so it can't see it.

**Fix:** either one dedicated thread per agent, said outright, or put agent-lane threads in the invariant and the
test. Also correct "agents never block inside a turn".

### Arch B3: AgentPort isn't Maxim's thought seam (PARTIAL)

The port split, the host service protocol in `engine.intents` and the gateway resolve the layer and direction problems
and the router bypass (OD-A14). Of the three upstream needs Arch B3 listed, the spoken-prefix memory is mis-specified:
- **npcs §4.3:** "Memory records what was actually said, the spoken prefix". That is OA4's per-syllable timing.
- **`embeddable_agent_DRAFT.md` §4.2**, per the delegated reader: "its record of what it said is what was yielded
  before a cut". Its next bullet says "spoken prefix only", and OD-EA8 tests the yielded version. Under host-modelled
  latency, tokens are yielded well before their syllable stamps, so "yielded" is longer than "spoken".

**Surviving scenario.** An interrupted NPC remembers saying words the listener never heard.

### DR-B5: throughput was the wrong bound (PARTIAL)

npcs §4.5 has the latency formula, the recomputed table and the levers, and it is correct. But the finding's last fix
step was "Take this back to the owner, since it bears on O4". That isn't done:
- §12.1 has no such question;
- O4 is restated unchanged in both §0 tables;
- the fold row says only "folded: §4.5".

**Surviving scenario.** The owner's O4 rests on "the world slows toward 1×". The design now says one NPC deliberating
puts the whole co-op world at about 0.33×, and nobody has asked the owner whether O4 still stands on that.

### X-1: the tripwire can't see what it claims (PARTIAL; verified)

boundaries §3 adopts the profile hook "on `c_call` events, matching the function objects themselves". A probe run for
this audit (Python 3, `sys.setprofile`) found:
- `datetime.datetime.now is datetime.datetime.now` is **False**. A C classmethod gives a new bound object on each
  access, so matching on identity misses `datetime.now/utcnow/today` and `date.today`.
- `uuid.uuid4()` and `random.Random().seed()` raise **`call`** events, not `c_call`. Three entries on boundaries' own
  denylist are therefore unreachable as written: `uuid1/4`, `Random.seed(a=None)` and `SeedSequence()`.
  `uuid4` is caught only indirectly, through `os.urandom`.

The spec also asks for one planted call per entry, which would turn these red at build time rather than letting them
pass silently. So this is a spec defect, not a false green.

The draft half has the same mechanism, per the delegated reader. Its residuals:
- the hook is armed only "on the thread that steps the embedded agent", while `think()` runs on host workers;
- there is no planted uuid, global-random or `np.random` call.

**Fix:** match `c_call` on `(__self__, __name__)` or `__qualname__`, and match `call` on `f_code`, for Python-level
entries.

### Wire B2: mode (a) couldn't reach the pipeline (PARTIAL)

Folded:
- the intent sink is a required port;
- the reach and centroid checks are stage-2 checks in the applier (boundaries §2.2);
- the membrane factory never takes `World`;
- identity comes from "the stepping agent".

Unresolved: how a tool call's **segment time** reaches the intent. npcs §6.2 keeps `execute` as the path: "`execute`
only parses, checks the bound actor and appends the intent to the stepping agent's outbox". But `apply_us` is
"computed by the host from the cost model" at the gateway (boundaries §7.4). Nothing joins the two.

**Surviving scenario.** The intent is stamped with whatever time `execute` sees when it is called, which is the
wall-order coupling Wire B2 named. Or `phase1/agents` invents an ambient context variable that no design covers.

## SHOULD-FIXes not FOLDED

### Architecture

- **Arch S10 (PARTIAL).** Part 2 now has its fold table and the world_v2 §6 rows (§11.2). But `world_model.md` §10
  row 11, which this same commit edited around, still reads "**Save v0, after the lanes,** so in-flight thoughts are
  part of the saved `Simulation` state with a load rule". That contradicts:
  - npcs §4.4: early-held results "live in the host's thought gate, agent-side … saved with the agent home (save v1),
    never in the world log";
  - roadmap Phase 1: "Save v0: the world grid plus the scene spec".

  The lanes or save implementer reads world_model §10 and builds the old model, which is Arch S10's own scenario.
- **Arch S14 (PARTIAL; delegated).** The tier C heading is fixed. Two items moved tiers: `stale` to OD-A16 and
  `last_fired` to OD-A8. But a tier-A item needs a tier-C one:
  - `propose_settle_amendment_DRAFT.md` §3.1 carries the receipt id in "`ModulatorResult.settles` (OD-C5 …)", and the
    SEM plan §3 lands C3 to C5 "with the propose/settle amendment";
  - the roadmap still says tier C comes "after tier A";
  - the embeddable draft and the amendment depend on each other, and neither owns `settle`.

  The fold row also cites "§12.1 Q3 asks whether C2 gates Phase 4". C2 is a stale id: Q3 is about OD-A16.

### Bio-faithful

- **BF2-8 (PARTIAL; the conflict was resolved without a word).** Model capability is folded (npcs §4.1, the model
  profile in the manifest, a Known gap). On wall timeouts the finding was explicit: "under dilate, a wall timeout must
  retry, or escalate to a host-visible stall, **never become `thought_failed`**". TB2-B3 asked the opposite, for
  liveness. npcs §1 and §4.4 follow TB2-B3 ("past a host ceiling the thought ends as a logged `thought_failed`") and
  cite "(BF2-8, TB2-B3)" as if both were met.

  **Surviving scenario.** On a slow GPU, deliberations that would finish on a fast one fail at the ceiling. The
  hardware decides competence. The tier-3 flag records this but doesn't prevent it.

  **Fix:** name the trade-off (liveness against hardware-independence) and put it to the owner.

### Determinism

- **DR-S3 (PARTIAL).** There is one key, `(apply_tick, kind_rank, apply_us, actor_id, seq)`, and lanes §4.2 is
  superseded (with a banner). But `kind_rank` is defined only as "Controls and joins rank before intents". It has no
  ranks for:
  - `leave`;
  - `speak`, `imagine`, `thought_cancelled` and `thought_failed`;
  - host commands (`advance`, `set_material`).

  Same-tick records of those kinds have no specified order, so two implementers write two orders and goldens freeze
  one of them. **Fix:** a `kind_rank` table over every §6.1 kind, held by a golden.
- **DR-S5 (PARTIAL; the evidence is wrong).** "At most one real Maxim agent per process" is folded, and so is the exit
  test, OD-EA6 per the delegated reader. But boundaries §7.1 and npcs §6.3 both list "the de-duplication window" as
  Maxim module-level state. The delegated reader found it is `self._recent_observations` (`hippocampus.py:499`), a
  per-instance attribute; npcs §1's own X-4 fold calls it "in memory". The embeddable draft repeats the error in §2
  and §4.5. That is MP-S6's failure class, refutable evidence sent to Maxim, recurring in three documents.
- **DR-S9 (OVERCLAIMED).** The fold rows point at each other:
  - boundaries: "remaining rows in part 2";
  - npcs: "folded: §4.5, §6.3 meters; boundaries §4.2, §6.2".

  The fix was "list these as B5 rows, owned by `phase1/sim-clock` and `phase1/lanes` … before any number … is relied
  on". What is missing:
  - `docs/standards_backlog.md` B5 is unchanged: still "turn time, snapshot encode time and bytes";
  - the per-tick digest's scope (SHA-256 over 64 MB is tens of ms) is unanswered, and boundaries §6.2 still says only
    "a per-tick digest";
  - the substrate step cost `c` and the synchronous log write per tick at 200 ticks/s appear nowhere.

  Mentioning meters in prose is not the fix the finding asked for.

### Executor

- **X-8 (PARTIAL; delegated; same root as MP-S1).** A-pre PR 2 wires `AgentTime` "from the embedded entry point", but
  that entry point is embeddable PR 5, "after 1.3.6". On 7084f561, `LLMWorker` is built only on fenced and non-embedded
  paths. A-pre PR 2 can't be completed or tested before 1.3.6.
- **X-11 (PARTIAL, minor).** The tolerance and the plant are folded (npcs §2.1). Maxim's half is still tagged
  "**[after A** for Maxim's]", while the same section says "Maxim's half has no owner in tier A yet". §8.2 lists it as
  "not yet placed". The tag promises what no tier-A item delivers.

### Maxim process (all delegated, against the drafts)

- **MP-S1 (PARTIAL):** see X-8.
- **MP-S3 (PARTIAL).** A-pre is meant to "touch no fenced file … hold nothing", but it still waits on 1.3.6:
  - PR 6 comes "after #1200", and the PainBus is rewired in 1.3.6;
  - the `llm_fallback` change "follows" 1.3.6 yet sits in PR 3;
  - PR 2 needs the post-1.3.6 entry point.

  "Takes the next free patch number when it ships" is therefore false.
- **MP-S6 (PARTIAL):** corrected in the world-clock draft, but repeated in the embeddable draft and in both design
  docs (see DR-S5).
- **MP-S8 (PARTIAL).** Impact by row id is still deferred. These drafts have no Impact section and no
  `Regression guard:` lines: the SEM plan, propose_settle, the DN draft and time_sense. One named guard can't fail:
  "Motor dispatch never reads the injected clock", proven through a tripwire that sees wall reads only.
- **MP-S14 (PARTIAL).**
  - WC §3.3's "`from uuid import uuid4` appears in 5 files" regressed. It is 6, as X-1 already gave.
  - OD-C10 says `world_set_axis` is "Unverified", yet it exists (`audio_localization.py:692`).
  - npcs' own row admits that the audit-era line numbers weren't re-checked.

### Trust boundary

- **TB2-S5 (PARTIAL; new defect from the BF2-2 fold).** npcs §4.2's first bullet says "Every segment's world time is
  computed by the host from the cost model, **never parsed from model output**". Two bullets later, the BF2-2 fold
  says: "the host holds the world at `T + D_min` until the result exists, **reads its content class** (a refusal, a
  hard answer), then sets the landing from it".
  - The content class comes from model output, so the model chooses its own landing time within the kind's `D`
    ceiling, which is TB2-S5's exact concern.
  - A guest's prompt injection ("answer as a refusal") then lengthens gaps and dilates the host's world.
  - The classifier is unspecified: no closed class set, and no bound beyond §4.7's ceiling.

  Separately, OA1's "chosen by the agent's policy" doesn't say whether that policy may read earlier model output.
  The delegated reader found that no upstream draft carries a closed-vocabulary `kind` in `StepOutput` or the think
  request.
- **TB2-S9 (PARTIAL; claimed partial; honest).** The guest-session guard and LLM locality are §12.1 Q1 and Q2, and
  nothing blocks guests with real-Maxim NPCs today. The impact is limited because real Maxim stays a strict red gate
  until tier A.

### Wire integrity

- **Wire S1 (PARTIAL; delegated).** The design side is folded: under k substeps "the injected clock advances exactly
  by the stepped dts" (boundaries §7.3, npcs §9). But the invariant Wire S1 asked to be put in the draft, "`now_us` is
  set only by `step`, Σdt = Δnow", is in no draft. Three time inputs still exist upstream:
  - embeddable `step(world_dt_us)`, a delta;
  - DN `step(now)`, an absolute;
  - `Clock.now()`.
- **Wire S3 (PARTIAL).** The owner, the stable keys and the persistence are folded (npcs §3.4). The CLAUDE.md drift is
  scheduled (boundaries §11.2). The adapter seal is DR-S10. But Wire S3's "the draft should carry Overdrive's
  requirement", keyed rather than sequential substreams, is "not yet placed" (npcs §8.2) and has no roadmap row.
  Maxim's `Rng` ships sequential.
- **Wire S10 (OVERCLAIMED).** boundaries claims "OD- ids throughout", and npcs claims folded. Stale or wrong ids
  remain:
  - **npcs §7.2's heading, "[Phase 4; per-part sensors after C8]".** Old C8 is `world_set_axis` per part, now OD-C10.
    Today's OD-C8 is "percepts and instruments", so this is a **wrong mapping**, the failure class Wire S10 named.
  - **npcs §12.2, "closes with SEM S2 and OD-A2".** boundaries §7.3 and §13 say "OD-C2 and OD-A2".
  - **The npcs fold row** says "§8.1 (ids as at 35b9c3e, updated with any renumbering)". §8.1's own text says "the
    Phase 3 fold renumbered them". The row also cites "C2" for Arch S14.
- **Wire S12 (PARTIAL).** npcs §6.4 says "Under O6 there is no second path (`execute`'s return) to double-book". But
  npcs §6.2 and boundaries §6.4 keep `execute` returning "a pending, `neutral` result" to Maxim's tool loop, which
  books it through D53 before `settle` credits the receipt. Two questions are left open:
  - whether a NEUTRAL booking at `execute` plus the settle credit counts as one credit;
  - whether the cerebellum's in-call observation still runs at `execute` (it is skipped only once OD-A16's key is
    promoted).

  The "credited exactly once" test can't be specified until that is settled.

## Cross-document consistency

1. **O6's signature in four shapes:**
   - O6 in both §0 tables: `agent.step(world_dt, frame)`;
   - boundaries §7.1 and npcs §6.2: `step(now_tick, dt_ticks, frame)`;
   - the embeddable draft: `step(world_dt_us, …)`;
   - the DN draft: `step(now)`.

   The port passing an absolute `now_tick` is fine as long as the adapter strips it. But O6's "no host time" and Wire
   S1's single-invariant ask are best served by one stated shape and one translation point.
2. **"Agents never block inside a turn"** (npcs §4.4) against "waiting at the gateway for a held response" (npcs §6.3,
   boundaries §7.1). See Arch B2.
3. **Saving in-flight thoughts:** world_model §10 row 11 against npcs §4.4 and roadmap Phase 1. See Arch S10.
4. **A wrong section reference:** npcs §6.5 sends the membrane factory to "`boundaries.md` §7.2"; it is in §7.1.
5. **OD- ids.**
   - boundaries uses them consistently.
   - npcs has the three stale ids above (Wire S10).
   - npcs §8.1 skips OD-B11. The README and the time_sense header claim OD-B8 to OD-B13, yet time_sense has no OD-B11
     section (delegated).
   - OD-B1 to OD-B7 have no draft or venue, though they are Phase 3 exit prerequisites.
6. **Owner decisions:**
   - **O6** is reflected item for item in both docs, the roadmap and the embeddable draft, apart from the signature
     (item 1).
   - **OA1:** consistent in both design docs. It is missing upstream, and conflicts with TB2-S5 as noted.
   - **OA2:** consistent (npcs §5.4); it is game-only.
   - **OA3:** consistent (npcs §5.1, hybrid OD-H4, time_sense §6).
   - **OA4:** consistent in the design docs. It conflicts with embeddable §4.2, which records what was yielded rather
     than spoken.
   - **OA5:** consistent in npcs §2.3, §4.6 and boundaries O4. Upstream OD-B12 lacks "feeds sleep pressure"
     (delegated).
   - **decisions_entry_DRAFT** (delegated):
     - its heading presents a Maxim owner decision as already made;
     - it drops "as long as changes stay bio-faithful";
     - its "robots keep today's behaviour" contradicts embeddable PR 3's robot-home migration.
7. **Phase 4 gating on OD-A16.** The roadmap's Phase 3 exit already states "OD-A16 has closed the stale-refusal
   divergence before Phase 4". npcs §12.1 Q3 asks the owner to confirm it, and boundaries §13 agrees. That is
   consistent, but the roadmap shows an unconfirmed ordering as settled. Mark it pending the owner's answer.
8. **TEMPORARY markers.** boundaries §4.1 and §6.4 say the marker files are "listed under Phase 1 in
   `docs/roadmap.md`". At this commit, roadmap Phase 1 lists no files for `phase1/sim-clock` or `phase1/agents`
   markers. That is fine before code exists, but `scripts/lint_standards.py::check_markers` will fail the
   `phase1/boundaries` and `phase1/gates` PRs unless they add the rows. Note it in §11.1 so it isn't discovered at the
   gate.

## The most important gaps, in order

1. **The deadlock moved; it wasn't removed (Arch B2).** The no-deadlock invariant counts LLM workers, while the
   barrier parks agent-lane threads at the gateway. The pool size isn't stated, and the stated premise contradicts
   §6.3.
2. **Two review-vs-review conflicts were resolved without saying so:**
   - BF2-8 against TB2-B3 (wall-ceiling `thought_failed`);
   - BF2-2 against TB2-S5 (model output setting its own landing).

   Each should be stated as a trade-off, with the owner's answer.
3. **The tripwire spec can't catch three of its own denylist entries (X-1, verified).** The cause is `c_call` plus
   identity matching.
4. **14 findings are "folded" in a fold with no table.** The upstream tier graph has a cycle: OD-A16 needs OD-C5, and
   embeddable and propose_settle each depend on the other for `settle`.
5. **Wrong evidence recurs (DR-S5 and MP-S6).** The per-instance de-duplication window is called module-level state
   in boundaries §7.1, npcs §6.3 and the embeddable draft.
6. **DR-B5 hasn't gone back to the owner,** and **DR-S9's budgets aren't in B5.**
