**Verdict: round 1's Performance findings are mostly fixed, but the fold adds four contract defects.** The v2 text contradicts itself on how `pinned` behaves under load, and O50 quietly removes the peer cancel that §2.5 still claims. Of round 1's ten findings, 8 are `fixed` and 2 are `open`: S-3 in part and S-5's prompt-layout half. Among the new findings, none is a BLOCKER: 5 are SHOULD-FIX (4 contract, 1 mechanism) and 3 are NIT.

# Delta review, Performance: `docs/design/inference_placement.md` v2 (274f297..caca211)

**What I read:**
- the full fold diff;
- v2 in full (5,988 words, 12 under the cap);
- `npcs_and_sem.md` §4.4 and §4.5 at caca211;
- `research/llm_spike.md`;
- the B5 row in `standards_backlog.md`;
- the Known gaps in `architecture.md`;
- the roadmap rows.

**Maxim, at origin/main 043eab8f, with `git show`:**
- `maxim_peer_backend.py:555-570`, `:930-940` and `:1085-1096`, which are the three cancellation checkpoints;
- `utils/http.py:60-70` (`DEFAULT_POOL_PER_ENDPOINT = 10`);
- the `models/language/__init__.py` and `router.py` import lists.

I ran nothing else.

## 1. Statuses of round-1 findings (read from the tree at caca211)

| Finding | Status | Evidence |
|---|---|---|
| **B-1** no chunk producer | **fixed** | O50 records a decision against streaming. OD-A25 is the ask (`roadmap.md`), the `chunk` kind is reserved (IP §3.3), and §6.3 states the cost with the spike's numbers. That is one of the two fixes I proposed. There is residue in `npcs_and_sem.md` §4.5; see D-1. |
| **S-1** cancel per transport; wasted decode | **fixed** in text | IP §2.5 states cancel per transport, and B5 now meters abandoned tokens per placement. But O50's `stream=False` removes the peer mechanism that §2.5 relies on; see D-2, a new defect. |
| **S-2** `timeout_s` is not a whole-call bound; `pinned` stuck on a full placement | **fixed** | IP §2.5 adds `call_ceiling_s` with a kill, the liveness ceiling now runs from enqueue, and kills free slots. Retries are zeroed where they can be (F4). The "minutes of `thought_failed`" scenario comes back in a new form through cooldown and restart; see D-3. |
| **S-3** server concurrency; context per slot | **open** (part) | Context per slot is fixed: IP §2.2 `context_per_slot`, checked against `total_budget` in §2.1. Two parts are not: `max_in_flight` ≤ the server's real parallelism is declared and never measured, and no B5 probe for real concurrency was added (the B5 row has none). So round 1's Defect 1, a server-side first-come queue behind declared slots, still holds whenever the declaration is wrong. The `server` group is new, and its meaning is undefined; see D-4. |
| **S-4** cost of `pinned` | **fixed** | IP §2.4 states the number (1.03× against 1.34×), cites it as a reviewer's model, and B5 has "wait while another eligible placement was free". §4.5's table was not recomputed for `pinned`. That was my suggested fix, not the defect, so I do not hold it open. |
| **S-5** prompt layout; spend undercount | **open** (layout half) | Spend is fixed: four counts times four rates (IP §4.1, §5.5), F8 is stated as a Known gap with OD-I9, and B5 has cache hit ratio and prefill per call. The layout rule (stable text in `system`, volatile text in `user`) is not in IP, the roadmap, OD-A14 or `embeddable_agent_DRAFT.md`; I grepped for "stable", "volatile" and "layout". The fold table says it "goes with B1", but no Phase 3 row or draft carries it, so as the tree stands it is dropped, not deferred. To defer it properly, a clause should go into OD-A14 or the B1 draft, triggered by OD-A14's cut. |
| **S-6** model on the same machine as the world | **fixed** | The B5 row has turn time and time to first token with a loopback model under physics load at the max profile, against one memory budget for weights, KV cache and pinned frames. |
| **S-7** per-chunk cost; rows missing from B5 | **fixed** | The rows are now in B5 (`standards_backlog.md` B5, "Owed rows (inference placement…)"). Per-chunk cost is moot under O50, and gateway start time, restarts and memory are listed. The unmeasured claim "microseconds to a millisecond" is gone. There is a residual trigger-column gap; see D-7. |
| **N-1** barrier parks serial or parallel | **fixed** | IP §7 now gives both figures: about 4 s per second serial, about 0.2 s per second in parallel, with the LAN round trip marked *to measure*. |
| **N-2** "measured" | **fixed** | IP §7 now says "derived". |

## 2. New findings in the fold

### D-1. SHOULD-FIX, contract. `npcs_and_sem.md::§4.5` (lever 3) and `research/llm_spike.md`: O50's cost is stated in IP §6.3 but not where the levers are ranked

**Defect:**
- IP §6.3 says "§4.5's lever 3 is unavailable until OD-A25". But §4.5 itself is not in IP §10's edit list and was not touched. It still ranks "3. Streaming the first token for P2 speech" as a lever, with no note that it is unavailable.
- The spike's conclusion "Speech is … streamed, so the NPC speaks while the rest decodes" also stands unannotated.
- §4.5's table is not numerically wrong. It already assumes L = 3 s, which is a full-reply latency. So the table survives, and the stale part is the ranked list of levers, which is what a reader acts on.

**Failure scenario.** At `phase1/agents` or Phase 4, someone plans the speech path from §4.5, the design that owns latency. They budget P2 speech on time to first token (0.32 s), not full reply (1.29 s), and size O11a's filler and account timing on a lever the design has switched off.

**How bad.** Under floor-holding, even one NPC alone at 1 in flight now passes the yield (1.29 s > about 1 s). Every reply to the player becomes a yield and a new turn, and the account path is never the normal path. That is a change in what O11a means in practice, and §4.4 and §4.5 say nothing of it.

**Fix (unverified).** Add one line in §4.5's lever 3 pointing to O50 and OD-A25, and one line in the spike's conclusion.

### D-2. SHOULD-FIX, contract. `inference_placement.md::§2.5` (cancel on `maxim_peer`) and `§1.3` (F5): under O50's `stream=False`, peer cancel no longer frees anything early

**Defect.** F5 lists three checkpoints. I confirmed them at 043eab8f:
- `:566`, before the call;
- `:937`, "after peer call returned";
- `:1093`, between SSE chunks, inside the streaming loop.

With `stream=False`, which IP §3.3 and O50 mandate, the between-chunks check never runs. A non-streamed call has only a check before the call and one after it returns. §2.5 still says that on `maxim_peer` "the call ends at its next check". The next check is now after the whole reply has been generated and received. Peer cancel is therefore identical to the cloud transports: the slot is held, and the leader keeps decoding, until the call returns or `call_ceiling_s` kills the gateway.

**Failure scenario:**
1. The player interrupts while four NPCs' replies are in flight on a `maxim_peer` leader with `max_in_flight: 4`.
2. The host counts on §2.5's early release when it plans capacity.
3. In fact all four slots stay held for the full decode (about 1.3–2.2 s each on the spike's numbers). The leader's batch keeps the abandoned decodes, which slows the live calls (round 1, S-1: time to first token rises from 0.32 s to 0.54 s to 1.40 s as in-flight goes from 1 to 4).
4. The "abandoned tokens" meter shows it, but the contract told the scheduler otherwise.

**Fix (unverified).** §2.5 says that, under O50, no transport frees a slot on cancel. Peer's early release returns with OD-A25.

### D-3. SHOULD-FIX, contract. `inference_placement.md::§2.3`, `§2.4`, `§2.6` (pinned), `§2.7`, `§3.4`: under load, `pinned` either fails over or stalls, depending on which paragraph you read, and in neither case is the cost stated

**Defect: three rules that cannot all hold.**
- §2.4: under `pinned`, "a request may use only the **first eligible** placement".
- §2.3: a placement is ineligible while it is cooling down or its gateway is not up.
- §2.6: under `pinned`, `overloaded` and `call_timeout` "don't [move]: the request waits for the same placement". Yet §2.7 says those outcomes, which are attributed to the placement, *start its cooldown*.

So one 429 makes placement A ineligible, and by §2.4 the first eligible placement is now B. The request moves, which is exactly what §2.6 forbids. Either the waiting rule can't be implemented as written, or cooldown has to be exempt from eligibility under `pinned`. The design doesn't say which.

**The same gap appears for kills:**
- A call past `call_ceiling_s` is a symptom of load (a slow server).
- The kill makes the gateway "not up" while it restarts with exponential backoff (§3.4), so by §2.4 pinned traffic moves to B.
- The resulting `failed(unreachable)` is attributed to the host, and §2.6's rule on what moves a pinned request covers only failures attributed to the placement. So what a host-attributed failure does under `pinned` is undefined.

**Load can mark a placement down for the whole session.** After `max_restarts` kills in a window, "the placement is down for the session" (§3.4, §2.7). Under sustained load the reply-time tail keeps crossing `call_ceiling_s`, so the kills repeat and a healthy but busy local model is removed until restart. That is capability following load, permanently, which is the thing O48 and the owner's §11 default exist to prevent.

**Failure scenario, the waiting reading.** A pinned cloud placement takes one `overloaded`:
1. Its cooldown is a value in `functions.yaml` that nothing sets yet.
2. Then probe-first applies: one call, of about one full-reply latency, before "full traffic resumes".
3. All the function's requests wait for cooldown plus one probe round trip.
4. If that exceeds the liveness ceiling, every thought in the function ends `thought_failed(timeout)` for the cooldown, and the run falls to tier 3.

This is round 1's S-2 outcome, now arrived at through cooldown instead of through held slots. The probe also cuts throughput from `max_in_flight` (up to 16) to 1 for a round trip after every cooldown.

**Fix (unverified):**
- State which rule wins under `pinned`, for cooling, restarting and host-attributed outcomes.
- Require cooldown plus one probe to fit inside the liveness ceiling, or state the timeout fallout.
- Exclude load-caused kills from the `max_restarts` count.

### D-4. SHOULD-FIX, contract. `inference_placement.md::§2.2` (`server`, `max_in_flight`) and `§2.4`: a shared server's slot count and dispatch order are undefined

**Defect.** "Placements sharing a `server` share its `max_in_flight`", but `max_in_flight` is a field on each placement, and a group has no field of its own. If two placements in one group declare 2 and 4, the cap could be 2, 4 or 6, and the loader has no rule for it.

§2.4 also gives each placement its own deadline queue. When a slot frees in a group, which queue gets it? If nothing says, the slot can go to placement A's head (due later) over placement B's head (due sooner). That reintroduces, across queues, the same deadline inversion that round 1's S-3 found inside the server.

**Failure scenario.** A 3B speech model and a 7B planning model on one Ollama are grouped as `server: box1`. A planning request with a late deadline takes the freed slot while a speech request due in 200 ms waits. Speech goes past the yield, and the "slot wait" meter blames the speech placement.

**Fix (unverified):**
- `max_in_flight` belongs to the group when `server` is set, and a placement in a group may not declare its own.
- A freed group slot goes to the earliest-due head across the group's queues.

### D-5. SHOULD-FIX, mechanism; deferred to `phase1/agents`, or Phase 4's fake-server test. `inference_placement.md::§2.5` and `§3.4`: what one kill costs the other calls on the placement is not metered, and `call_ceiling_s` has no rule tying it to the reply-time tail

**Defect.** Under O53 a kill ends *every* attempt on that placement. With `max_in_flight` up to 16, one slow call takes down up to 15 healthy ones. Each of them:
- is retried as a fresh attempt (`failed(unreachable)` is retried, per §2.6), after the gateway's start time plus backoff;
- is charged at the worst case, its dispatched input plus `response_reserve` (§5.5). That inflates spend, so the soft cap is reached early on `third_party`.

The probability that some call in flight crosses the ceiling grows with the number in flight. So the busier the placement, the more often it kills and the more collateral each kill costs: throughput falls with load in a way §4.5's formula has no term for.

B5 lists restarts but not collateral attempts per kill. Nothing says how to choose `call_ceiling_s` relative to the full-reply distribution, for example above a measured high percentile at `max_in_flight`.

**Failure scenario:**
1. A cloud placement runs 12 in flight, and one provider tail call reaches 30 s against a ceiling of 25 s.
2. Eleven completed-in-a-moment replies are lost, re-dispatched after a restart (cost unmeasured), and charged 11 × the worst case.
3. Five such tails in the window, and the placement is down for the session (see D-3).

**Fix (unverified):**
- A B5 meter: collateral attempts per kill, with their spend at the worst case.
- A checklist test of throughput against kill rate on the scripted transport.
- The rule for setting the ceiling relative to the tail, recorded once the Phase 4 measurement exists.

### D-6. NIT, contract. `inference_placement.md::§2.2` (no transport timeout field), `§2.5` and `§3.3` (`open`): under `stream=False`, the per-read timeout becomes a bound on the whole response, and nothing ties it to the ceiling

**Defect.** F4 says timeouts bound each socket read. With `stream=False`, no byte arrives until the reply is complete. So the transport's read timeout is now, in effect, a limit on the whole generation time, applied once per retry.

v2 dropped `timeout_s` from the placement fields, and `open` carries "transport settings only" without listing them, so the value and its constraints aren't contract. Two cases go wrong:
- **Timeout too short.** If it is below the full decode time at `response_reserve`, which is possible with `thinking` on or with long plan replies, every such call ends `call_timeout` after burning a full decode, and is retried. §2.6's `pinned` rule then waits on the same placement forever.
- **Timeout too long.** If (1 + retries) × the timeout is above `call_ceiling_s`, the host's kill always pre-empts the transport. That turns a placement-attributed `call_timeout` into a host-attributed kill, and moves traffic, as D-3 describes.

**Fix (unverified).** Name the transport timeout as a field of `open`, with its relation to `response_reserve` at the decode rate and to `call_ceiling_s` checked at load.

### D-7. NIT, mechanism. `standards_backlog.md::B5` (trigger column), and `inference_placement.md::§8` (instance model against O53)

**B5's trigger column.** The inference rows were appended to the row's text, but the trigger column still reads "Phase 1 step 5a …; frames pinned per agent with `phase1/agents`". Most of the new rows need real transports: time to first token, cache hit ratio, prefill, memory under load. They have no step that owes them, so they can sit in the backlog unowned. The fix is to name `phase1/agents` (gateway start time, restarts, channel round trip, host CPU per reply, on the scripted transport) and Phase 4 (the rest).

**§8's instance model.** §8 lets Phase 4's test choose "one call per process where a transport can't take concurrent calls". That contradicts O53's "one gateway per placement", and it changes what the gateway-memory and start-time rows count: per placement or per slot. It also changes what a kill takes down: one call, or every call on the placement. The B5 row and §3.4 assume per placement.

Gateway memory is the import set behind `maxim.models.language/__init__.py` → `router.py`, which pulls in `cost_tracker`, `cloud_redaction`, `cloud_audit`, `llama_backend` (its optional dependencies load lazily) and `cloud_dispatch`, multiplied by the number of processes. That cost is unmeasured either way. It is correctly marked "to measure", but nothing caps it.

### D-8. NIT, contract. `inference_placement.md::§0` (O50) and `§6.3`: "a Known gap with its number" is not recorded as one, and the number is for one reply length

**Not where the Known gaps are.** O50 says the cost "is a Known gap with its number (§6.3)". `architecture.md`'s "Known gaps" has no inference entry, and §6.3 is a design section, not a list of gaps. The proxy and cleartext gaps in §5.2 and §5.4 say "a Known gap" with no location either. The place a reader looks for gaps doesn't list them.

**One reply length.** The 1.29 s and 1.46 s figures are the spike's medians for a 60-token cap through Ollama's native streaming API. Full-reply time grows by about 42 ms per output token at 23.8 tok/s. It was measured with a streaming client, while the gateway path is `openai_compatible` with `stream=False`, which is unmeasured (IP §2.2 concedes this). So say "at a 60-token cap", and mark the non-streamed figure to measure at §8.

## 3. Numbers in the fold

| Number | Status |
|---|---|
| §6.3: 1.29 s, 0.32 s, 1.46 s | cited (spike, near-quiet cells) |
| §2.4: 1.03× against 1.34× | cited as a reviewer's model (round 1, S-4) |
| §2.2: pool of 10 | verified (`utils/http.py:67`, `DEFAULT_POOL_PER_ENDPOINT = 10`) |
| §7: about 1 ms LAN round trip | marked *to measure* |
| §7: 2.5–2.9 s | derived and cited |
| §2.2: max_in_flight range 1 to 16 | a bound, not a measurement |
| F4: "about 90 s" of capacity retries | cited but not re-verified by me |
| `call_ceiling_s`, `ping_ceiling_s`, cooldowns, `max_restarts`, restart backoff cap | no value and no "measured at step N" |

The unset values in the last row are acceptable as mechanism only if D-3 and D-5's constraints, which are relations between them, are written as contract.

## 4. What I checked and found sound

- Per-placement queues (§2.4) remove the head-of-line blocking that existed across placements.
- The liveness ceiling now counts from enqueue (§2.5), so slot wait is bounded.
- Each attempt gets one reply, and attempt ids are scoped by generation (§3.3), so no late reply is miscounted after a kill.
- The channel has bounded outboxes and reader threads (§3.3). Under O50 the frame rate is one reply per call, so round 1's S-7 concern about chunk rate and the GIL does not arise.
- Spend for abandoned and killed calls counts the worst case (§5.5). That is conservative, and correct for a cap.
- §7's arithmetic is unchanged and correct.

**Summary for the author.** D-1, D-2, D-3 and D-4 are contract, and should fold or go to the owner. D-5 and the B5 trigger in D-7 are mechanism, deferred to `phase1/agents` and Phase 4, with the trigger named in each. D-6 and D-8 are small text fixes. S-5's layout half needs a Phase 3 home to count as deferred.
