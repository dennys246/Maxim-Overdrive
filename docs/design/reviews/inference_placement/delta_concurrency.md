**Verdict: liveness holds, and there is no new BLOCKER.** Every wait the simulation lane makes is now on a request whose ceiling starts at enqueue on the injected host clock, so the world always moves again. Four contract SHOULD-FIXes are short text changes, and they must still fold: kill attribution, the cooldown-versus-pinned contradiction, what "finished" means, and the bound on `call_ceiling_s`. A fifth contract SHOULD-FIX (D7, the branch cache) belongs mainly to the Determinism lens. The mechanism findings go to the `phase1/agents` or Phase 4 checklist.

Lens: Concurrency and lanes, delta round. I read `inference_placement.md` v2 at caca211 (§0–§8), the diff `274f297..caca211` in `npcs_and_sem.md` and `checklists.md`, the fold table, and my round-1 report. `npcs_and_sem.md` §1 and §4.4 are as edited.

---

## 1. Statuses of round-1 findings (read from the tree at caca211)

| Finding | Status | Evidence |
|---|---|---|
| C1 no whole-call bound | **fixed** | IP §2.5 adds `call_ceiling_s`, enforced by killing the placement's gateway (O53), and retry counts are set to zero where they can be. Unswitchable retries run inside the ceiling. §1.3 F4 now states that timeouts bound reads, not calls. Residuals: D1 (attribution) and D4 (no bound on the ceiling itself). |
| C2 pinned full; ceiling start | **fixed** (liveness) | IP §2.5: "The liveness ceiling starts when the request is enqueued", and kills free slots. The health half (giving abandoned-full an outcome health can act on) moves to D1. |
| C3 hang criterion; blast radius | **fixed** | IP §3.4 defines two criteria (a call past `call_ceiling_s`; no `pong` within `ping_ceiling_s` while an attempt is in flight), and a kill reaches only that placement's gateway (O53, §3.2). |
| C4 head-of-line blocking | **fixed** | IP §2.4: a queue per placement, a slot granted to the earliest-due request that may use it, and "A full placement therefore never blocks…". |
| C5 lifecycle races | **fixed** in parts 1, 3 and 4; part 2 is weakened by D3 | IP §3.3 rules: generation-scoped `attempt_id`, exactly one `reply`, cancel of a finished attempt is a no-op, and the old channel closes before attempts are declared (§3.4). Part 3 (a retry beside the original) can't happen any more: retries follow only attempt replies or kills. Part 2 (whether the host cancels on its own liveness timeout) is unstated, and "finished" is undefined (D3). |
| C6 no chunk producer | **fixed** (by owner decision O50, author-set via the owner) | IP §0 O50, §3.3 (`chunk` reserved), §6.3 (cost with numbers), §9 OD-A25. |
| C7 concurrent backend safety | **deferred** | Reason: [now] runs a scripted transport, and O53 removes the cross-placement `_EndpointRegistry` collision because each placement has its own process. Trigger: Phase 4's concurrency test (IP §8, "N concurrent calls with an injected auth failure"). Condition: the deferral's fallback, "one call per process where a transport can't take concurrent calls" (IP §8), means several processes per placement, which contradicts O53 and §2.5's kill unit. If the test picks that branch, the owner must rule on it, and it must not be built silently. |
| C8 health feedback on load | **fixed** | IP §2.7: request-attributed outcomes don't cool, and a probe goes first after a cooldown. IP §2.6: under pinned, `overloaded` and `call_timeout` wait instead of moving. Under `spill`, cooling on `call_timeout` can still shift load (a swappable law, opt-in). D2 and D8 are new defects in this text. |
| C9 server capacity, killed spend, pool | **open** (bullet 1 only) | Bullet 2 is fixed (IP §5.5, worst-case count for killed calls). Bullet 3 is fixed (IP §2.2, at most 10 for `maxim_peer`). Bullet 1 is not addressed: a kill frees every host slot while the server may still be generating the orphaned calls, and kills are now *the* bounding mechanism, so it matters more than in v1. See D6. |
| C10 I/O model | **fixed** | IP §3.3: a reader thread per side that never blocks on a write, bounded outboxes, and the largest frame bounded by the envelope. The overflow rule is missing (D11, mechanism). |
| C11 shutdown and orphans | **fixed** | IP §3.4: shutdown is a bounded wait then a kill, the gateway exits with `os._exit` on EOF, and restarts back off up to a cap with `max_restarts` in a window. The wait values are unnamed (D10). |
| C12 shared slots across functions | **deferred** | Reason: a capacity reservation is a swappable law, only the real latency distribution can size it, and liveness is bounded by `call_ceiling_s` and the liveness ceiling. Trigger: the B5 slot-wait meter (IP §8) shows speech waiting past O11a's yield budget (about 1 s) behind another function's calls at Phase 4. |
| N1 `max_in_flight` bound | **fixed** | IP §2.2 sets it to 1 to 16. |
| N2 chunks after cancel | **deferred** | Moot while no chunk is sent (O50). Trigger: OD-A25 lifts O50. The guarantee must then be the host's (drop chunks for a cancelled attempt), not the gateway's. |

---

## 2. New findings in the fold

### D1. SHOULD-FIX (contract): `inference_placement.md::§2.5` and `§2.6` (`failed(unreachable)` attribution) and `§2.7`/`§3.4`: a kill is attributed to the host, so health never sees a hung placement, and "down for the session" means two different things

**What the text says.**
- §2.5: when any call passes `call_ceiling_s`, "Every attempt on it then ends `failed(unreachable, host-killed)`".
- §2.6's table attributes `unreachable` to "host after a kill or crash".
- §2.7: host-attributed outcomes start no cooldown.
- So the outcome C1 and C2 were about (a placement that is alive but too slow, the trickling server) never reaches the health law. The call that crossed the ceiling is the placement's failure. The other calls killed with it are collateral. The table doesn't tell them apart.

**What bounds it instead.** Only restarts do, and the two sections disagree on what counts:
- §2.7: "A gateway that keeps **failing to start** marks its placement down for the session".
- §3.4: "After `max_restarts` in a window, the placement is down".

**Failure scenario under each reading.** A loopback llama.cpp server under memory pressure, guests present, every function pinned to it.
- **Kills don't count** (§2.7's reading). Each cycle runs: dispatch, the ceiling passes, a kill, a restart (the gateway starts fine), full traffic again with no probe, because no cooldown was started. Every cycle costs a whole `call_ceiling_s` of dilation, and it never stops.
- **Kills count** (§3.4's reading). A transient slowdown (a few long `plan` calls) kills the gateway `max_restarts` times. The only eligible placement is then down for the whole session, and every thought ends as `unavailable` until restart.
- Collateral: each kill also discards up to 15 healthy calls on the placement, whose spend is counted at the worst case (§5.5).

**Why it's contract.** The cooldown law, `inference_status` (§5.6) and the B5 restart meter all depend on which outcome a kill produces and what "down" counts. *Fix direction (unverified):* attribute the crossing call to the placement (a `call_timeout`-class outcome, so the probe law engages) and the collateral to the host, and say whether kills count toward `max_restarts`.

### D2. SHOULD-FIX (contract): `inference_placement.md::§2.3` and `§2.4` contradict `§2.6` ("Under `pinned`… `overloaded` and `call_timeout` don't [move]") and `§6.2`

**What the text says.**
- §2.6 says a pinned request hit by `overloaded` or `call_timeout` "waits for the same placement until the liveness ceiling".
- §2.7: those outcomes are placement-attributed, so they start the placement's cooldown.
- §2.3 item 2: a cooling placement is not eligible, and neither is one whose gateway is not up.
- §2.4: under `pinned` a request "may use only the **first eligible** placement in its function's list".
- So while the first placement is cooling down (or restarting after a kill, D1), the first *eligible* placement is the second one. Both the waiting retry and every new request of that function go there.

**Failure scenario.** A 529 storm on the Anthropic `plan` placement starts its cooldown. For the length of the cooldown, every NPC's `plan` requests are served by the second placement, which runs a different model. Load moves a pinned function. That contradicts O48, §6.2 ("load alone never moves a pinned function") and BF-3's fold. The per-NPC placement-change meter counts it as normal.

The reading in which the request waits for the first placement is not written anywhere. Under that reading the pinned rule needs "first placement eligible on consent and budget", with health as a wait condition rather than an eligibility condition.

**Why it's contract.** It decides which model answers, which is an owner decision. Liveness is unaffected either way, because the enqueue ceiling bounds the wait.

### D3. SHOULD-FIX (contract): `inference_placement.md::§3.3` rules: "finished" is undefined, and one reading kills the gateway on every cancel

**What the rules say.**
- "`cancel` of an attempt that is already finished is a no-op." Here "finished" is from the gateway's side.
- "A `reply` for an unknown, **finished** or foreign attempt … is a protocol error: that gateway is killed." Here "finished" is from the host's side.
- §2.5 says on a cancel the host "stops waiting at once" and the outcome is `cancelled`.

**Failure scenario.** A builder takes "finished" to mean "the host has decided the attempt's outcome". That is a natural reading, since the host decides `cancelled` at once. Then:
1. A world event cancels a thought, and the host records `cancelled`.
2. The gateway obeys "exactly one reply" and sends `reply(cancelled)` when the cloud call returns.
3. That is a reply for a finished attempt, so the gateway is killed.

Every cancel then kills every other call on that placement (up to 15). The same happens when the liveness ceiling ends a request whose attempt is still in flight.

C5's point 2 also stays unstated: whether the host sends `cancel` when its own liveness ceiling fires. On `maxim_peer` that would let the call stop at its next check instead of running to `call_ceiling_s`.

*Fix direction (unverified):* an attempt is finished only by its one `reply` or by its gateway's death. The request's outcome (cancelled, timeout) is separate, and the host sends `cancel` on the liveness ceiling too. This matches §2.5's "a slot is held … until its gateway replies".

### D4. SHOULD-FIX (contract): `inference_placement.md::§2.2` `call_ceiling_s`: no bound, and no relation to the liveness ceiling

`call_ceiling_s` lives in `placements.yaml`, which the player edits (§2.2 "Who may change what"). No range is stated. The design has no rule like "call_ceiling_s ≤ liveness ceiling". Two failures follow:
- **A ceiling of 10⁶ s.** C1 is back: no whole-call bound exists. Under pinned, a hung placement's slots stay held indefinitely. Every request of that function waits the full liveness ceiling and ends `timeout`. No kill, cooldown or failover ever happens.
- **A ceiling above the liveness ceiling.** Calls routinely outlive their requests, and abandoned calls hold slots past the requests they served. That reproduces C2's "every later thought waits the full ceiling" in a bounded but recurring form.

The loader is a registered gate (§3.5), and its accepted range is contract. *Unverified:* refuse a value above the function's liveness ceiling. That needs the liveness ceiling's source named too: it is "the host's wall ceiling" in `npcs_and_sem.md` §4.4, and no file is given.

### D5. NIT (contract): `inference_placement.md::§2.2` `server`: whose `max_in_flight` does a group share?

Each placement carries its own `max_in_flight` (1 to 16), and "Placements sharing a `server` share its `max_in_flight`". Suppose two placements in group `s` declare 4 and 8. The group's cap is undefined: 4, 8 or 12 are all plausible builds, and 12 overruns a 4-slot llama-server, which is exactly the case C9 and S-3 were about. Needed: a loader rule, either refusing a mismatch or giving the group its own field. The case also belongs in the gate's golden rejection files.

### D6. SHOULD-FIX (mechanism): `inference_placement.md::§2.5` ("its slots free") with `§2.2` `server`: a kill frees host slots while the server is still busy (C9 bullet 1, made worse by the fold)

Under O50 every call is `stream=False`. Whether llama.cpp's server, Ollama or a provider aborts a non-streamed generation when the client's connection drops is *unverified*; I did not test it.

**Failure scenario, if the server doesn't abort.**
1. A kill of placement A frees A's slots, and with them the `server` group's slots.
2. The group grants them at once, to A's restarted gateway or to sibling placement B.
3. The server is still decoding A's orphaned calls, so the new calls run slow and cross `call_ceiling_s`.
4. That kills them too.

It can cascade across every placement on the server, and with D1's first reading it loops.

This can be checked only by running, so it is a mechanism. *Deferred to:* Phase 4's loopback fake-server and real-server test (IP §8), which must measure disconnect behaviour under `stream=False`. Trigger: that test. If servers don't abort, the slot-release rule after a kill (contract) must be revisited.

### D7. SHOULD-FIX (contract): `inference_placement.md::§4.2` "Branches": the cache copy has no as-of point

This mainly belongs to the Determinism lens, and I found it while checking held replies across saves.

"A load opens a new segment whose cache starts as a copy of its parent's." Read literally, the copy is taken at load time.

**Failure scenario.**
1. The player saves at tick T and keeps playing in the same segment. Its cache gains entries for occurrences after T.
2. Later the player loads the save at T. The new segment's cache now holds the parent's *future* entries.
3. The branch dispatches the same occurrences live and writes its own entries. That gives two entries for one occurrence in one segment's cache, against "One entry per request occurrence", and a rerun of the branch can read the parent's entry instead of its own.

The same race exists at the save point. If a reply arrives (and is written to the cache, §4.2's write point) after the save has taken its headers, it is in the cache but not held in the save. The branch then re-dispatches it, and two entries result. *Unverified:* define the copy as the parent's cache as of the save point, with entries written after the header snapshot excluded.

### D8. SHOULD-FIX (mechanism): `inference_placement.md::§2.7`, "one probe dispatch goes first": a probe that ends neither good nor bad wedges a pinned placement

"Full traffic resumes only when the probe succeeds." The probe is a real request, so it can end as:
- `cancelled` (a world event);
- `truncated(length)` or `failed(context_overflow)` or `refused` (request-attributed);
- `unreachable` attributed to the host (killed with others, D1);
- or its request can hit the liveness ceiling first.

None of these is a success or a placement failure. If the builder sends no new probe, the placement stays in probe state with no probe in flight. Every pinned request then waits the full liveness ceiling and ends `timeout`, each one dilating the world by the ceiling, for the rest of the session. The world moves, but the function is dead with no signal.

This is a swappable law. *Deferred to:* the `phase1/agents` checklist, as a test that every non-success, non-placement-failure probe outcome triggers the next probe.

### D9. SHOULD-FIX (mechanism): `inference_placement.md::§3.3`/`§3.4` `open` → `ready`: no start ceiling

The two hang criteria (§3.4) cover a call in flight and an unanswered ping while an attempt is in flight. Neither covers a gateway that never answers `open`.

**Failure scenario.** Phase 4 picks the OS keychain (§3.5). On macOS, a keychain access prompt blocks credential resolution until the player answers it, which may be never. Nothing happens next:
- `ready` never comes;
- §2.7's "keeps failing to start" never counts it, because nothing says a start has failed;
- the placement is never eligible ("gateway is up").

Under pinned, every request of that function ends as `timeout` at the ceiling. With guests present, the start-time refusal ("a missing local model … refuses the session at start", §5.6) never fires, because it waits on a start that never ends. *Deferred to:* the build step, as a start ceiling on the injected clock, counted as a failed start, with a test.

### D10. NIT (contract): `inference_placement.md::§3.4`: unnamed tunables

`ping_ceiling_s`, the ping cadence, the backoff base and cap, `max_restarts` and its window, and the shutdown wait are named but given no file, no range, and no rule relating them. Two relations matter:
- `ping_ceiling_s` should exceed a ping interval;
- the backoff cap relative to the liveness ceiling decides whether a restarting pinned placement ever serves a waiting request.

Each file is a registered gate (§3.5), so its keys are contract. Name the file (presumably `functions.yaml` or a host-only table) and the ranges.

### D11. NIT (mechanism): `inference_placement.md::§3.3` "writes through a bounded outbox": overflow is unstated

The text doesn't say what a full outbox does: block, drop, or treat it as hung.
- **Host side.** Dropping a `dispatch` leaves a slot held until `call_ceiling_s` kills the gateway. Dropping a `ping` kills it after `ping_ceiling_s`.
- **Gateway side.** A call thread blocked on a full reply outbox holds a finished call's reply.

Every choice is liveness-safe, because the kill bounds it. But a dropped `cancel` silently loses the peer early stop. *Deferred to:* the `phase1/agents` channel tests, with each kind's overflow behaviour stated and tested.

### D12. NIT (mechanism): `inference_placement.md::§6.4`, "one injected host wall clock": the gateway's own sleeps aren't on it

The host's ceilings, cooldowns and supervision are injected, but inside a Phase 4 gateway the retries "it can't switch off" (`_OpenAIBackend`'s gateway retries, §2.5) and the SDKs' backoff sleep in real time. The [now] scripted transport is unaffected. The Phase 4 fake-server tests (IP §8) would then sleep in real time, against the "no sleeps" test rule, or need the ceiling scripted around real sleeps. *Deferred to:* Phase 4's backend tests. It also strengthens OD-I9's ask for configurable retry budgets.

---

## 3. Checked, no finding

- **The world always moves again.** Every simulation-lane wait under dilate is on a request. Its liveness ceiling starts at enqueue (§2.5) on the injected clock (§6.4). Retries, pinned waits, cooldowns, probes, restarts and full slots all sit inside that ceiling. `stop` ends the wait (`npcs_and_sem.md` §4.4). I found no wait outside a request.
- **Retries under every policy.** They are bounded by the liveness ceiling and are new attempts (§2.6), never running beside the original. Request-attributed outcomes are never retried. After a kill, retries go only to a gateway that has sent `ready` (eligibility). There is no retry storm under pinned, because load failures wait.
- **Generation-scoped ids, and the channel closed before attempts are declared** (§3.3, §3.4). A buffered frame from a dead generation can't match a new attempt.
- **Exactly one reply.** It holds if D3 defines "finished", and a slot is released exactly once (§2.5).
- **Ping and pong.** The reader thread answers, so pong shows only that the process is alive. The call ceiling covers stuck calls, so the two criteria together close C3 under both of round 1's readings.
- **Shutdown and orphans.** A bounded wait then a kill, and `os._exit` on EOF, mean non-daemon call threads can't keep an orphan alive (§3.4). The host's reader threads are joinable once the kill closes the channel.
- **The no-deadlock invariant is unchanged.** No agent holds a slot, and a `Pending` is a value.
- **The spend cap's softness** is bounded by `max_in_flight` per placement, and killed calls are counted at the worst case (§5.5).
- **Held replies across a save.** The text is held in the header and saved, and a load never re-dispatches it (§4.2). The as-of race is D7.
