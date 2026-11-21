**Verdict: two new BLOCKERs (both contract, both in the cache text the fold added), one new SHOULD-FIX (contract) and three NITs.** Of round 1's twelve findings, ten are `fixed` and one is `open` (S5, through a stale line in `boundaries.md`). BLOCKER 1 is `fixed` as contract for when OD-A25 lands, and is moot under O50 until then.

# Delta review, Determinism and replay: `docs/design/inference_placement.md` v2 (diff 274f297..caca211)

## What I read
- The full diff, all twelve files.
- IP v2, all of it.
- `npcs_and_sem.md` §1, §4.3, §4.4, §4.8 and §6.6 ("Determinism at the edges", cache repeats, resume equivalence).
- `boundaries.md` §6.1, §6.3 (as it stands at caca211, not only the hunks that changed), §7.3 and §7.4.
- The `checklists.md` lane block, and `fold_round1.md`. I used its claim column only to find where to look.

## Part 1: statuses for round-1 findings (reviewer-set, read from the tree at caca211)

| # | Status | Evidence |
|---|---|---|
| BLOCKER 1, failover after delivered speech | **fixed** | `IP::§2.6` says: "Once speech has reached the world, a failure is never retried. It ends the reply as `truncated(prefix, reason=transport)`". It is moot under O50 (`IP::§0`, `§3.3`, since `chunk` is reserved). Residual: `transport` is not in the outcome table's `truncated` reasons (`length`, `stream_broken`), so it needs a row when OD-A25 lands. That is not a blocker now. |
| S2, one entry per occurrence | **fixed** | `IP::§4.2`: "One entry per request occurrence, and only for the final outcome … Attempts and placements live only in provenance." The checklist has "one cache entry per occurrence after a failover". The tier question is answered by implication only, see NIT N3. |
| S3, live never reads | **fixed** | `IP::§4.2` gives the rule and the poisoned-entry test. `npcs_and_sem.md::§4.8` now says "Live play writes, never reads". The checklist carries the test. |
| S4, no read-through mode | **fixed** as stated, but the fold left a contradiction behind, see new S3 | `IP::§4.2`: "Three modes, and no fourth … no read-through mode". |
| S5, manifest refuses and reports; envelope source | **open** | `IP::§2.2` (the file split) and `IP::§4.3` (envelopes refuse, and a rerun spawns workers with the recorded envelopes) fix it in IP. But `boundaries.md::§6.3` line 457 still reads "the placement table's digest and role envelopes (reported, never refused: `inference_placement.md` §4.3)". That flatly contradicts IP §4.3, which it cites, and it still records a single table digest, not one per segment. The fold diff never touched that line, although `IP::§10` lists `boundaries.md` §6.3 as changed. It needs a one-line fold. |
| S6, pure token counters | **fixed** | `IP::§2.1`: a closed vocabulary; each counter is pure, runs in the worker with no model or network, and its version is in the envelope's identity. `_LazyTokenCounter` is excluded by name. |
| S7, dial test can't fail | **fixed** | `IP::§6.4`: an echo double, a failure schedule, the schema test across `AgentPort` and the codec, and a negative control. A residual mechanism note is NIT N1. |
| S8, injected host clock | **fixed** | `IP::§6.4`: one injected host wall clock, the named timeout module, drives the lane, cooldowns, ceilings and supervision. The scripted transport is advanced by test messages. The checklist says "on one injected host clock". |
| S9, write point, held replies, branches | **fixed** as asked. The new rule has its own defect, see new B2 | `IP::§4.2`: the write point is arrival, held text is saved with the header, and each segment has its own cache. `npcs_and_sem.md::§4.4` is edited to match. |
| NIT 10, `unavailable` | **fixed** | `IP::§2.6` has a closed list. `boundaries.md::§6.1` points to it. |
| NIT 11, envelope version | **fixed** | `IP::§2.1`: "the digest of its canonical value (`boundaries.md` §6.3's canonicalizer), never a number bumped by hand". |
| NIT 12, manifest summary and per-segment digest | **fixed** in IP (§4.3, per segment; the per-placement summary is gone). The `boundaries.md` §6.3 half is covered by S5's open status. |

## Part 2: new findings in the fold

### BLOCKER B1: `IP::§4.2` ("`cancelled` writes nothing", "the write point is when the reply arrives") with `npcs_and_sem.md::§6.6` ("a rerun with instant cached replies"): the cache has no entry for a thought cancelled while its call was in flight, and nothing tells a tier-2 rerun not to look one up, so every rerun of a run with such a cancel fails on a miss. **Contract.**

**Defect.** Three rules interact.
1. Cancellation is decided at a world tick from `cancel_on` events and logged (`npcs_and_sem.md` §4.3). Whether the reply had arrived by that tick depends on wall time.
2. The cache is written when the reply arrives (§4.2). An in-flight cancel's gateway outcome is `cancelled` and writes nothing (§2.6's table). The cancelled request therefore has an entry if its reply beat the cancel tick, and none if it didn't.
3. A rerun "reads and never dispatches, and a miss is a loud error". `npcs_and_sem.md` §6.6 has the rerun serve "instant cached replies", which means it looks up at dispatch.

Nothing says *when* a rerun reads an occurrence's entry. Nothing says a request whose thought is later cancelled is exempt from the lookup.

**Failure scenario.**
1. A live run under dilate. At tick 500, NPC 3 asks a planning call, occurrence `(h, 0)`, which lands at tick 560.
2. The player speaks to NPC 3 at tick 530. `cancel_on` fires, and `thought_cancelled` is logged.
3. The reply hadn't arrived; the gateway ends the attempt as `cancelled`, and no entry is written.
4. The tier-2 rerun reaches the same request at tick 500. It looks up `(h, 0)` at dispatch, misses, and stops with a loud error at tick 500, before the world reaches the cancel it would have reproduced.

Barge-in is the commonest interactive event (`npcs_and_sem.md` §4.3), so nearly every interactive run becomes un-rerunnable. The manifest still labels it tier 2, because a cancel is neither a machine-decided failure nor `abandon` (`boundaries.md` §6.3).

The variant is worse. A builder who meets the miss and makes "miss means cancelled" the rule has made a miss silent. That defeats the reason §4.8 made misses loud.

**Missing contract.**
- The read point: at the landing tick, or "a miss is an error only if the thought reaches its landing tick uncancelled".
- That a cancelled request still consumes its occurrence index in canonical order, so `npcs_and_sem.md` §6.6's "numbered in canonical order (by thought request id)" stays aligned between live and rerun whether or not an entry exists.

**A direction, unverified:** state both in §4.2, and add a checklist test: a live run with an in-flight cancel, then a rerun from its cache, gives identical digests.

### BLOCKER B2: `IP::§4.2` "A load opens a new segment whose cache starts as a copy of its parent's": the copy includes the parent's entries from after the save point, and the child's first requests collide with them on every reload. **Contract.**

**Defect.** The parent segment usually keeps playing after a save and keeps writing entries. A load opens a child segment from the save. The child starts from the same agent state, so its first requests after the load are byte-identical to the parent's first requests after the save. Their occurrence indices also match, because both continue the canonical request-id sequence from the save. Live play never reads, so the child dispatches and writes the same `(hash, occurrence)` key the copy already holds. §4.2 doesn't say whether that write replaces the inherited entry, is refused, or is a gate error.

**Failure scenario.**
1. The parent saves at tick 120.
2. The parent plays on. At tick 130 request `h` (occurrence 4) is answered "Take the stairs." and cached.
3. The player reloads the tick-120 save. The child copies the whole cache, `(h, 4)` included.
4. At tick 130 the child issues the identical request and dispatches live, at temperature above 0. It gets "Take the lift." and writes `(h, 4)`.
5. The outcome depends on the write rule:
   - **First writer wins, or the existing key is refused:** the child's tier-2 rerun silently serves "Take the stairs.", and the rerun's world diverges from the child's log with no miss.
   - **The write errors:** live play breaks on every reload.
   - **Replace:** correct, but only if stated.

The same collision happens for a request in flight at the save, which `IP::§4.2` re-dispatches on load (only *arrived* replies are held), while the parent may have written its own answer after the save. Reloading is routine, so this is routine. The resume-equivalence test with the double can't see it, because the double answers both identically (round-1 S9's point, still unaddressed for this path).

**Missing contract.** What the copy holds (only entries whose requests precede the segment's start, by canonical request id), or that a child's write replaces an inherited entry. Plus a checklist test using a double that answers differently per segment.

### SHOULD-FIX S3: `IP::§4.2` ("Three modes, and no fourth … pair only on substrate-only arms") against `npcs_and_sem.md::§4.8` "What pairing buys": the fold removed the mode that pairing needs but kept the claim. **Contract.**

**Defect.** §4.8 still says paired runs "stay paired only until the first prompt differs; after that every request misses. So paired reruns help substrate-only arms and the prefix before divergence". With only the three modes, a rerun that meets the first differing prompt hits a loud miss and stops. That holds for a substrate-only arm too: any substrate variable that changes what an NPC perceives changes its next prompt. Running "past the divergence" means dispatching on a miss, and that is the fourth mode §4.2 forbids.

**Failure scenario.**
1. An experiment pairs arm B (drive decay ×1.2) on arm A's cache, by seed.
2. At tick 4,000 arm B's first prompt differs, and the rerun aborts with a miss.
3. The harness author, following §4.8's sentence, adds "dispatch on a miss" to finish the arm. That re-creates round-1 S4's confound for any later arm that differs by placement or model, because the model is not in the key.

**Missing contract.** Either:
- pairing through the cache covers only the shared prefix, and the arm ends (or is tier 3 from the first miss) at divergence. §4.8 then says so, and §4.2's "pair only on substrate-only arms" is corrected; or
- a fourth mode is named, refuses a placement-digest difference, and flags tier 3 from the first miss.

The owner picks; I'm not proposing which.

### NIT N1: `IP::§6.4`, the dial-invisibility test. **Mechanism; defer to `phase1/agents`' checklist.**
- **The failure schedule can make the arms legitimately differ.** A scripted failure, cooldown or spend-cap crossing that pushes a request past the liveness ceiling, or leaves no eligible placement, ends it as `thought_failed(timeout | unavailable)`, a different world.
  - Failure scenario: the test goes red on a correct lane, and someone "fixes" the schedule ad hoc.
  - Needed: the schedule keeps every request recoverable within the ceiling, with an eligible placement always left. A separate case shows the ceiling outcome does differ.
- **The echo double's reply needs a fixed parse.** "Echoes a digest of its whole input" must still produce a reply the agent parses, or every thought ends `parse`, and the test compares failure records instead of behaviour.
- **The assertion is only "canonical requests byte-identical".** A placement leak into agent state that isn't rendered (memory metadata), or into a receipt, wouldn't show. It should also assert the world-log digest, kinds and receipts, as `boundaries.md::§7.3` does.
- **The test must wait for each reply before the next clock advance.** With two gateway processes, arrival order at the host's reader threads (`IP::§3.3`) is up to the OS scheduler, even on the injected clock.

### NIT N2: `IP::§5.1`, per-speaker taint. **Mechanism, with one contract sentence.**
- Taint ("an NPC that hears an NPC holding such words holds them too", lasting until O17's purge) is host state that outlives the session. The design doesn't say whether it is:
  - saved as a versioned field of the save; or
  - recomputed from the lineage's logged `speak` records, plus a logged purge record.
- Replay and rerun are unaffected: a rerun never dispatches, so eligibility is never consulted, and its only world effect, `thought_failed(unavailable)`, is a logged record.
- After a load it decides eligibility, so a lost taint set silently lets a tainted NPC go to `third_party`.
  - Failure scenario: a taint set held only in memory is empty after a load, and NPC 9 is eligible for Claude again with a guest's words still in its memory.
- Name its home, so the save format and the gate registry (`IP::§3.5`) can carry it.

### NIT N3: residual stale text that the fold's own decisions contradict
- **`npcs_and_sem.md::§4.4`** still says "Machine-decided failures … are recorded in the cache as first-class responses and flag the run tier 3".
  - After `IP::§4.2`'s "only for the final outcome", a failed attempt that a later attempt recovered is not cached. But the tier rule doesn't say it is not a "machine-decided failure".
  - One clause ("a thought's final outcome; recovered attempts flag nothing") closes it.
- **`boundaries.md::§7.4`** still says "the host streams the model call itself … validates it per chunk", against O50.
  - It is harmless for determinism, because stamps are chunk-independent.
  - But it is contract text a builder of the reply path will read.
- **`boundaries.md::§5.3`'s thought-budget row** has the same problem: "a stream cut-off before buffering".

## Checked, no finding
- **Cache key (function + envelope identity).** Every field that moves the rendered prompt is in the key or refused at start:
  - the envelope digest covers `total_budget`, `response_reserve`, `token_counter` with its version, and `thinking`;
  - `max_tokens` = min(reserve, thought budget) is in the sampling parameters;
  - `thought_budget.yaml` and `functions.yaml` sit under `data/agents/` and refuse.
  
  Dropping the model is safe given live-never-reads (S3, fixed) and no read-through (S4), apart from new S3's pressure to add one. Server-side chat templates differ by placement but sit below the cached raw output, and a rerun never dispatches.
- **Envelopes from the manifest on a rerun.** These are consistent with refusal: a recorded envelope that differs from the loaded one is refused anyway. A rerun never reads `placements.yaml` or `endpoints.yaml`, so it can start on a machine without them (round-1 S5's failure scenario 2 is gone).
- **The outcome table's cache encodings, other than `cancelled`.**
  - `truncated(*)` caches its text and reason, so a rerun reproduces it.
  - Every `failed(*)` that reaches `think` caches "failure", and the run is tier 3 by `boundaries.md` §6.3.
  - Liveness `timeout` and `unavailable` have no gateway row and no entry, but are logged records in tier-3 runs, where a rerun promises nothing.
  - `failed(empty)` and `ok`-with-silence are separated by `stop_reason`, both deterministic functions of the transport result.
- **Retries and failover with no delivered prefix (under O50)** reach the world only as one final reply at the modelled landing tick (`IP::§6.1`), so a recovered retry is tier-2-safe.
- **The `pinned` wait on `overloaded`/`call_timeout` past the ceiling** ends as `thought_failed(timeout)`, logged and tier 3. Correct.
- **A gateway kill and generation-scoped attempt ids.** The old channel closes before the attempts are declared failed, so no late frame can land a reply into a wrong attempt or a wrong cache occurrence (`IP::§3.3`, `§3.4`).
- **Held replies saved with the header.** These fix round-1 S9's re-dispatch for *arrived* replies, and resume equivalence holds for them. Replies in flight at the save are B2's case.
- **Provenance and spend.** Still no wall time in provenance (§4.1). Spend, health and consent act only on live dispatch, which is tier 3, and never reach cognition.
- **Pure counters** remove the load-timing dependence of the render. With the version inside the envelope identity, a counter change refuses at start, not as a miss mid-run.
- **The injected clock.** One named host module drives the lane, cooldowns, ceilings and backoff, and the scripted transport is advanced by messages, so the determinism scan's no-sleep rule is held (apart from N1's arrival-order note).

## Routing (last paper round)
- **B1, B2 and S3 are contract.** Each is a sentence or two in `IP::§4.2` and `npcs_and_sem.md::§4.8`, with a checklist test, so they fold or the owner overrules them.
- **S5 (open)** is a one-line fold to `boundaries.md::§6.3`.
- **N1** is deferred by me to `phase1/agents`' checklist (trigger: writing the §6.4 test).
- **N2** is deferred to `phase1/agents` (trigger: the consent and taint build), with the one sentence on taint's home folded now if the owner wants the save format settled.
- **N3** is a text cleanup, foldable now.
