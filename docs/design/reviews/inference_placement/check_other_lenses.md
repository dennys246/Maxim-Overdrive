**Verdict: not ready to hand off. One open BLOCKER-class status (B2/D7: the branch cache for requests in flight at the save), one new contract BLOCKER (taint's transitive leg covers only hearing), two new contract SHOULD-FIXes, and three NITs.** Statuses for 61 findings: **42 fixed, 10 deferred, 9 open, 0 rejected.**

Lenses: Concurrency and lanes, Determinism and replay, Trust boundary, Performance, Bio-faithful integration (one reader, short delta check). Read at ed55c2f: IP v3 and IG v1 in full, the diff `92f6c5f..ed55c2f` (all 14 files), the five delta reports and `fold_delta.md`. The claim column was used only to find where to look. Maxim was read at `origin/main` 043eab8f only.

Verified myself:
- IG §5's stop-reason lines `openai_backend.py:542`, `anthropic_backend.py:467` and `maxim_peer_backend.py:958` match their description.
- `env -i NO_PROXY=* no_proxy=* python3 -I` → `urllib.request.getproxies()` returns `{'no': '*'}`.

I did not rerun the httpx half.

---

## 1. Statuses

### Concurrency (`delta_concurrency.md`)

| Finding | Status | Evidence |
|---|---|---|
| C7 instance model | **deferred** (stands) | IP §8 Phase 4 sends "more than one process per placement" to the owner. It is in checklist "Deferred from the delta round" (C7, Phase 4). |
| C9 bullet 1 orphaned server work | **deferred** | Same as D6: IP §8 Phase 4 disconnect test, and the checklist (D6, Phase 4). |
| C12 slot reservation | **deferred** (stands) | Checklist "slot reservation per function (C12, on the slot-wait meter)". |
| N2 chunks after cancel | **deferred** (stands) | Moot under O50. Trigger: OD-A25. |
| D1 kill attribution; two "down" rules | **fixed** | IP §2.5: the crossing call is `call_timeout` (load) and the others are host collateral. IP §2.7 and IG §4: down only from failed starts, and kills never count. A crash residue is new finding N-S1. |
| D2 cooldown vs pinned | **fixed** | IP §2.3 ("A placement under a load delay stays eligible") and §2.7. Cooldown applies only to fault outcomes. |
| D3 "finished" | **fixed** | IG §3: finished only by one `reply` or gateway death. The host sends `cancel` on cancel and at the ceiling (IP §2.5). The protocol-error list no longer names "finished". |
| D4 `call_ceiling_s` bound | **fixed** | IP §2.2: refused unless below the smallest liveness ceiling. The ceiling's source is named (`thought_budget.yaml`, per kind). |
| D5 group `max_in_flight` | **fixed** | IP §2.2 `servers` owns it, and members declare none. The checklist has the rejection. |
| D6 disconnect under `stream=False` | **deferred** | IP §8 Phase 4 bullet 2 and the checklist (D6, Phase 4). |
| D7 branch cache as-of point | **open** | See B2. The cut is by request id, not by when the entry was written. |
| D8 probe wedge | **fixed** (contract) | IP §2.7: "re-issued until one ends in `ok` or in a fault". The test is in the checklist (D8). |
| D9 start ceiling | **fixed** | IG §4 `start_ceiling_s`, counted as a failed start. Residue: new finding N-S2. |
| D10 tunables | **fixed** | IG §4: the `health` block, with three relations. |
| D11 outbox overflow | **fixed** (contract) | IG §3: a full outbox counts as hung, and IG §4 kills. The per-kind test is in the checklist. |
| D12 gateway sleeps | **deferred** | Checklist (D12, Phase 4). |

### Determinism (`delta_determinism.md`)

| Finding | Status | Evidence |
|---|---|---|
| S5 (round 1) `boundaries.md` §6.3 | **fixed** | `boundaries.md` §6.3 now points to IP §4.3's inference items. The stale "reported, never refused" text is gone. |
| B1 in-flight cancel, rerun misses | **fixed** | IP §4.2:<br>- the read is at the landing tick;<br>- a request whose thought ended (a logged cancel or `thought_failed`) before landing is never looked up;<br>- the index is assigned at creation "whether or not an entry is ever written".<br>The checklist has the test. |
| B2 branch copy collides | **open** (BLOCKER severity stands, in part) | IP §4.2 "Saves and branches": the copy holds "entries whose requests were created at or before the saved high-water request id". That excludes requests made after the save. It does not exclude a request **in flight at the save**: its id is ≤ the high-water mark, the parent writes its entry after the save, and the copy picks it up. Only *arrived* replies are held (`held_reply`), so the child re-dispatches that request live and writes the same `(hash, index)` key.<br>Scenario: B2's own last paragraph and D7's second paragraph, both still uncovered. The parent saves with request 41 in flight; its reply "Take the stairs." arrives after the save and is cached as `(h, 4)`. The player loads, the copy includes `(h, 4)`, the child re-dispatches and gets "Take the lift.", and its write collides. The child's tier-2 rerun then reads either text.<br>The rule needs the cut at what the save reflects (entries written at or before the save's header snapshot), or a stated child-wins write rule. |
| S3 pairing / fourth mode | **fixed** | IP §4.2 "Pairing": shared prefix only, and an arm ends at its first miss (owner ruling). npcs §4.8's pairing text is removed and points to IP. |
| N1 dial-test schedule | **deferred** | IP §6.4 folds the world digests and the per-reply wait. The recoverable schedule is in the checklist (determinism N1). Trigger: writing the test. |
| N2 taint home | **fixed** | IG §6 "Where taint lives": saved, versioned, and consent and purges logged. IG §9 has the gate row. |
| N3 stale text | **fixed** | npcs §4.4 "judged on a thought's final outcome". `boundaries.md` §7.4 and the §5.3 thought-budget row are reworded. |

### Performance (`delta_performance.md`)

| Finding | Status | Evidence |
|---|---|---|
| S-3 (round 1, part) declared vs real server parallelism | **open** | Nothing measures `max_in_flight` against a server's real parallelism. A grep for "parallelism" and "real concurrency" over IP, IG, B5 and the checklist finds nothing. IP §8's "N concurrent calls" runs against a fake server. The fold claims "the real-concurrency probe at Phase 4", but no such probe is in the tree. |
| S-5 (round 1) prompt layout | **open** | It is the author's own claim. The layout is in neither OD-A14 nor any draft. |
| D-1 lever 3 | **fixed** | npcs §4.5 lever 3 says "unavailable until OD-A25; O50". `llm_spike.md` is annotated. |
| D-2 peer cancel | **fixed** | IP F5 and §2.5: "no transport frees the slot early". |
| D-3 pinned under load | **fixed** (contract) | IP §2.7 load delay. Kills don't count (IG §4). A residue through start timeouts is N-S2. |
| D-4 group cap and order | **fixed** | IP §2.2 `servers`. §2.4 has one queue per group, and a freed slot goes to the earliest-due request. |
| D-5 cost per kill | **deferred** | B5 row "collateral attempts per kill" ([now]). The checklist has "collateral cost per kill and a ceiling rule from the reply tail". |
| D-6 transport timeout | **open** | IG §3 `open` now carries "the transport timeout" (the field is fixed). The fold says its relation to `call_ceiling_s` and `response_reserve` "is mechanism (checklist)", but the checklist's deferred list has no such item, and IG §4's three relations don't include it. The deferral is claimed, not recorded. |
| D-7 B5 owners; instance model | **fixed** | The B5 row is split between `phase1/agents` and Phase 4. IP §8 sends more than one process per placement to the owner. |
| D-8 Known-gap location; numbers | **open** (part) | The location is fixed (an `architecture.md` pointer to IP §6.3). But §6.3's O50 gap now holds **no numbers**. It defers to "the vertical slice's lesson … on `phase1/vertical-slice` at 7eed0bc", and I checked that 7eed0bc is **not an ancestor of ed55c2f**, so the cited numbers aren't in this tree. That lesson is also numbered 29 there, which collides with this branch's lesson 29. "On every loaded figure there, a reply passes … the yield" cannot be checked from the branch. CLAUDE.md requires Known gaps "with numbers". |

### Trust boundary (`delta_trust_boundary.md`)

| Finding | Status | Evidence |
|---|---|---|
| D-B1 taint only through speech | **open** | IG §6 now covers every guest-supplied string the NPC perceives directly. The transitive leg is still only "everything it **heard** from NPCs that held them": speech again. See new finding N-B1. |
| D-S1 clearing taint | **open** (part) | The clearing event is defined (IG §6: `purge(S)` completes on that NPC), O54 is implemented and "spreads and persists" is OPEN. But the fold took reading 2 of D-S1: host taint clears when the *agent's* purge completes, and that purge reaches only the records whose provenance sets name S (npcs §6.6, which O26 calls a "lower bound"). A paraphrase or summary missing from those sets survives, and the NPC becomes eligible for `third_party`. That cost is not named as an OPEN or a Known gap. |
| D-S2 `owner_lan` overclaim | **fixed** | IG §7: honest first-hop text, Tailscale stated, the HTTPS lookup-only limit stated. IP §6.3 Known gap. The HTTPS check is in the checklist (Phase 4). |
| D-S3 proxy re-read | **deferred** | IG §7 and the checklist ("the proxy re-read at each client build"). |
| D-S4 gateway log | **fixed** | IG §2 "Its log": size-bounded, under the session directory, outside saves and bug reports, purged, the only place an endpoint may appear. The checklist is consistent. |
| D-S5 no-effect allowed set | **deferred** | The allowed set is stated in IG §2 and spawns are forbidden. The test is in the checklist. |
| D-S6 out-of-bounds; spend floor | **fixed** | IG §3: the value becomes null and is metered. IG §8: the host's floor when a count is null or zero. |
| D-S7 cache row strictness | **fixed** | IP §4.2 "Format": versioned, strict decoder, budgets before allocation. |
| D-S8 oversized frame | **fixed** | IG §3: the gateway cuts the reply and classifies it `failed(oversized)`, a placement fault. |
| D-N1 to D-N7 | **fixed** (7) | IG §3 `open` fields; IG §8 ids; IG §2 header wording; IG §7 single-player proxy; IP §6.3 and `architecture.md`; IG §7 first hop; OD-I10 cites `strict_address_check`. |

### Bio-faithful (`delta_bio_faithful.md`)

| Finding | Status | Evidence |
|---|---|---|
| BF-3 (round 1) | **fixed** | Via B-1. |
| B-1 pinned under load | **fixed** (contract) | IP §2.7: load delay, eligibility kept, `empty` on `openai_compatible` and `anthropic` counted as load, kills not counted. IP §6.3 Known gap for F2. One route remains: N-S2. |
| S-1 to S-6 | **fixed** (6) | IP §2.1 and OD-A14 (new field); IP §2.1 tiers checked at load; IP §2.6 (only `Reply` variants, `stream_broken` removed) and §6.4 schema test; OD-A25 now a question to B1; IG §2 `NO_PROXY=*` and OD-I10 as a question; IG §6 taint as O26's lower bound, purge clearing, O54, and §6.2 OPEN. |
| N-1, N-2, N-4 | **fixed** | IP §1.2 `last_used_*` at `router.py:285-316`; OD-I9 cites `:771`; IP §6.1 cites O27. |
| N-3 OPEN registered; meter | **open** (meter half) | The npcs §12.2 pointer is fixed. IP §6.2's "per-NPC meter counts changes of placement" is in neither the B5 row nor the checklist tests (grep finds nothing). |

---

## 2. The specific checks

1. **Pinned, load delay and cooldown (IP §2.3, §2.4, §2.7).** These are consistent for call outcomes:
   - load outcomes leave the placement eligible, and `pinned` and `single` wait (§2.7);
   - fault outcomes cool it, and failover moves only on faults (§6.2 says so);
   - the ceiling kill is a load outcome for the crossing call and host collateral for the rest.

   Two routes still let load or non-faults bend the rule:
   - start timeouts under machine load reach "down for the session" (N-S2);
   - crash loops never cool (N-S1, the opposite direction).

   There is also one wording conflict for `single` (N-N1).
2. **Liveness.** It holds. The ceiling counts from enqueue on the injected clock (IP §2.5, §6.4). `call_ceiling_s` is below it, so slots are bounded by the kill. IG §4 keeps the start ceiling and the backoff cap below the ceiling. "Down" and "no eligible placement" end requests at once as `unavailable`. Waiting on a cooling-only candidate or a restarting gateway is bounded by the ceiling. I found no wait outside a request.
3. **Rerun reproducibility.** With an in-flight cancel it is reproducible from IP §4.2: read at landing, no lookup after a logged end, index at creation. With a reload it is **not** reproducible for requests in flight at the save (B2 open, above).
4. **Taint.** It is host-computable, its clearing event is defined (`purge(S)`), its home is defined (saved, versioned, logged, IG §9 gate), and O54 is implemented word for word: "Either person may delete … Only S may release". It does **not** cover every channel transitively (N-B1). Its clearing rests on the agent's provenance without that being said (D-S1 open).
5. **No placement fact reaches the agent.** It holds for values: IP §2.6 "What the agent sees" and the §6.4 schema test with its negative control. The outcomes still reach the agent as an event rate (N-N2).
6. **Registration.**
   - `architecture.md` Known gaps has the IP §6.3 pointer, but the O50 gap lacks numbers in-tree (D-8).
   - npcs §12.2 points to IP §6.2.
   - IG §6's OPEN (taint spreads) is listed in IP §6.2.
   - IG §7's gaps are listed in IP §6.3.

---

## 3. New findings (contract only)

### N-B1. BLOCKER (Trust boundary, Bio-faithful): `inference_gateway.md::§6` "Taint", second bullet

The transitive leg is "everything it **heard** from NPCs that held them". An NPC that holds a guest's words can also put them into world text: imagined-object labels (an LLM-built `imagine` spec) and written text in the world. Another NPC can then perceive that text without hearing anyone. Those strings are NPC-supplied, so they are outside the first bullet's "guest-supplied" list, and they are not "heard". So D-B1's defect returns one hop later.

**Failure scenario.**
1. In co-op, guest G (who declined `third_party`) tells NPC A a personal detail. A is loopback-only by taint.
2. A imagines a notice board reading "G says …".
3. G leaves. Single-player, Claude is opted in.
4. NPC B, who never heard A or G, reads the board. B's taint is empty, so B's prompt, which holds G's words, goes to Anthropic without G's consent.

This is against O51's ruling ("every guest-supplied string, by any channel"). The host can compute the fix: it knows the authoring NPC's taint when the intent applies. Fixing it is a contract sentence: a string an NPC authors into the world carries its author's taint, and perceiving it transfers that taint.

### N-S1. SHOULD-FIX (Concurrency, Trust boundary): `inference_placement.md::§2.6` (`failed(unreachable)` row: "host when collateral of a kill **or a crash**") with `§2.7`

A gateway crash makes every attempt on it host-attributed: retried, with no cooldown. A gateway that starts cleanly but dies on each call is never cooled, never probed and never failed over, and its restarts are not failed starts (IG §4). Causes include:
- a native crash in an SDK;
- an out-of-memory error from buffering a hostile, oversized body, since IG §3 cuts the text only after building the reply.

**Failure scenario.** `agent_inference` is pinned to `[A, B]`, and A's server returns a huge body on every call. A's gateway is killed for out-of-memory on each attempt. Every thought retries on A until the liveness ceiling and ends `thought_failed(timeout)`, for the rest of the session. B is never used, although this is a fault, which §6.2 says moves the function.

Contract: which outcome a crash during an attempt produces, and whether it counts toward health.

### N-S2. SHOULD-FIX (Bio-faithful, Performance, Concurrency): `inference_gateway.md::§4` "Starting" with `inference_placement.md::§2.7` and O48

A start that sends neither `ready` nor `error` within `start_ceiling_s` counts as a failed start, and `max_failed_starts` in the window marks the placement down for the session. A gateway start spawns Python and imports `maxim.models.language`'s set, so on a loaded machine it is slow. Restarts follow each load-caused ceiling kill.

**Failure scenario.**
1. 20 NPCs at 20× share the machine with a loopback 14B model.
2. Load-slowed calls cross `call_ceiling_s`, which kills the gateway; the crossing call counts as load, which is correct.
3. Each restart, run under the same load, exceeds `start_ceiling_s`.
4. After `max_failed_starts`, the placement is down for the session, and the pinned function moves to its 3B fallback for good.

Load then moves a pinned function permanently, against the owner's ruling ("load never moves a pinned function"). A start timeout and an `error(...)` reply need distinct treatment in the contract, or the gap must be named.

### N-N1. NIT (Determinism and replay): `inference_placement.md::§2.4`

For `single`, the text says "If it isn't eligible, the request ends at once as `unavailable`". Under the same section, "One whose only candidate is cooling down waits". A cooling placement is ineligible (§2.3), so for `single` the two sentences disagree. Experiments use `single` (§4.3).

**Scenario.** A transient fault during an experiment arm. One build ends the arm's thoughts at once; the other recovers after the cooldown with an `ok` reply, which is tier-2-safe. The same schedule then gives different worlds depending on which sentence the builder followed.

### N-N2. NIT (Bio-faithful): `inference_placement.md::§2.6` "What the agent sees" and `§6.2`

Failed thoughts resume the agent as `cancelled(prefix)`, an interruption with no world cause. How often an NPC is "interrupted" then depends on its placement's health, and refusals come only from some providers. No value crosses `AgentPort`, but an event rate does.

**Scenario.** NPCs on a flaky or refusing placement experience many more phantom interruptions than identical NPCs on a local model.

It is unregistered in §6.2's OPEN list.

### N-N3. NIT (Trust boundary): `inference_gateway.md::§6` "Who may purge (O54)"

A speaker is an actor and its session, and purges target "one guest in one session" (npcs §6.6). "S while connected" then means a guest can never purge, or release, an earlier session's words after rejoining, because that session's speaker can't connect again. Only the owner can erase them.

Separately, O26's purge reach doesn't include guest-authored world text. While a guest's sign stands, perceiving it re-taints NPCs, so the owner's "unlock by erasing" doesn't fully work.

**Scenario.** G declines on Monday and returns on Tuesday wanting to purge or release Monday's words. Neither is possible under the text.

---

**Outside my lenses (for the Architecture check, one line).** The worktree's CLAUDE.md now carries B36 "One owner per contract", which says decision tables live in `docs/design/reviews/` and indexes, not in design documents. IP §0 is a decision table (O46–O54).

**Must fold before hand-off, or go to the owner:** B2/D7 (in-flight at save) and N-B1. N-S1 and N-S2 are contract SHOULD-FIXes. D-6's claimed checklist deferral and D-8's in-tree numbers are small text folds. S-3 and S-5 (round 1) still need a home that actually exists.
