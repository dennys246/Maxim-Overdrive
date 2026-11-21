**Verdict: one BLOCKER, six SHOULD-FIX, three NITs.** Tier-1 replay is safe as designed. Tier-2 rerun has one contract hole: a failover after speech has started streaming. It also has several unstated rules that the model-less cache key now depends on.

# Determinism and replay: `docs/design/inference_placement.md` (diff 814dea9..04ab810)

## What I read
- The design itself, all sections.
- The diff to `npcs_and_sem.md` (§4.1, §4.8, §6.1 table, §6.2 note) and to `boundaries.md` (§5.3 cache row, §6.3 manifest, §7.1), and the `checklists.md` lane block.
- For context: `npcs_and_sem.md` §1, §4.1, §4.4, §4.8, §5.3, §6.6 (worker spawn, determinism at the edges, resume equivalence) and §10 (paired replays); `boundaries.md` §6.1–§6.3 (record kinds, log record, header, manifest, tiers) and §7.3–§7.4.
- Maxim `origin/main` 043eab8f: `src/maxim/models/language/token_counter.py` and the `get_token_counter` call sites.

## Findings

### BLOCKER 1: `inference_placement.md::§2.6 Outcomes, failure and health` (with §3, "A hung or dead gateway"): a failover after part of the reply has streamed can't be reproduced by tier-2 rerun, and the run isn't flagged tier 3

**Defect.** Speech is streamed into the world before the reply completes:
- `boundaries.md` §7.4: "the host streams the model call itself, reads the speech field first, validates it per chunk, and stamps syllables".
- `npcs_and_sem.md` §6.6: `cancelled(prefix)` carries "the host-validated syllables already emitted to the world".

§2.6 says that, under dilate, a failed attempt "is dispatched again, and selection may choose the next eligible placement". §3 ends every in-flight attempt as `transport_down` when the gateway is killed. The closed outcome list has no "failed after a delivered prefix" case. The cache keeps one reply per request, and §4.1's `attempt count` implies that reply is the final attempt's text. Nothing says what the retry does with syllables the world has already heard, and nothing says such a run is tier 3.

**Failure scenario.**
1. Under dilate, NPC 7's planning call on placement `local-a` streams "Get down, the" and the host stamps and emits those syllables.
2. The gateway hangs and is killed. The attempt ends `transport_down`.
3. The retry on `lan-b` returns "Run! The roof is going." The cache entry holds that text with `attempt count = 2`.
4. The world log holds both utterances: the dead prefix and the full retry.
5. A tier-2 rerun reads the cache, streams only "Run! The roof…", and emits no "Get down, the". Its world now differs from the recorded log at that tick.
6. The manifest flags tier 3 only for "any machine-decided thought failure, or under `abandon`". A retried `transport_down` whose final outcome is `ok` falls in neither, so the run was labelled tier 2 and the rerun breaks the promise.

Before this design the same hole existed for a timeout retry on one model (§4.4). Placement makes it routine, because one gateway death fails every stream at once. The outcome vocabulary and the cache entry shape are both tagged [now], so this is contract.

**Proposed directions (unverified).** Any one of:
- Once any syllable has been emitted, a failed attempt ends the reply as `truncated(prefix, reason=transport)` and is never retried.
- The cache entry records the delivered prefix of each failed attempt.
- Any retried attempt flags the run tier 3.

### SHOULD-FIX 2: `inference_placement.md::§2.6` and `npcs_and_sem.md::§4.8`: one cache entry per request occurrence, and the tier of a retried-then-`ok` run, are implied but never stated

**Defect.** §2.6 says both "only the final outcome becomes the thought's reply" and "machine-decided failures stay first-class responses in the cache". A builder can read the second as "write each failed attempt as an entry".

**Failure scenario.**
1. Attempt 1 times out on A and is cached as `(h, 0, timeout)`.
2. Attempt 2 succeeds on B and is cached as `(h, 1, ok)`.
3. On the rerun, the request takes occurrence 0 and replays a timeout. Its byte-identical successor later takes occurrence 1 and receives the first request's answer.
4. The rerun's agent state diverges with no miss, so nothing is loud.

**What is missing.** The design should state:
- the occurrence index is per request, never per attempt;
- attempts and placements live only in provenance;
- whether a failed attempt that a later attempt recovered makes the run tier 3 (BLOCKER 1 depends on this answer).

The checklist's tests don't include "a failover writes exactly one entry at the request's occurrence".

### SHOULD-FIX 3: `inference_placement.md::§4.2` (the parenthetical) and `npcs_and_sem.md::§4.8`: "live play never reads the cache" carries the weight of the model-less key, but it is hedged, not in the contract text, and untested

**Defect.** §4.2 justifies dropping the model id because "Live play writes the cache and never reads it", then asks the Executor to confirm it. The §4.8 diff does not add the sentence; it adds only the key change. The rule therefore lives in a hedge in a new document, and no test in `checklists.md` holds it. §4.8 tests "replay never opens the cache", but no test checks that live play never reads it.

**Failure scenario.**
1. A later change lets live play reuse cached answers on load, to make a continued session "resume smoothly".
2. Before this design, the model id in the key made a session with a changed `placement.local.yaml` miss.
3. Now the key carries only the role, so the continued session silently serves answers the old model wrote under a new table.
4. Provenance would show this, but nothing refuses it and the run's tier label says nothing.

**Fix direction (unverified).** State the rule in §4.8 and add a test: a live session with a poisoned cache entry for its first request dispatches anyway and produces the double's answer.

### SHOULD-FIX 4: `inference_placement.md::§4.2` against `npcs_and_sem.md::§4.8` "What pairing buys" and §10 "Paired replays": with no model in the key, a paired experiment whose arms differ in placement silently reuses one arm's answers

**Defect.** §4.8 says two paired runs "stay paired only until the first prompt differs; after that every request misses". Reruns treat a miss as a loud error. For pairing to cover only "the prefix before divergence", paired arms must use a third mode: read on a hit, dispatch on a miss. The design names only two modes, live (write-only) and rerun (read-only, never dispatches). In the third mode the model-less key is wrong whenever the arm variable is the placement or the model, because the prompt never changes on account of the model.

**Failure scenario.**
1. An experiment compares role `planner` on an 8B loopback model (arm A) against Claude (arm B), paired on seed.
2. Arm B's first request has the same canonical request as arm A's, because the model isn't in the key, so it hits arm A's answer.
3. Arm B's agent state matches arm A's, so its next prompt matches too, and every later request also hits.
4. Arm B is arm A, the divergence tick reported per pair never arrives, and the analysis finds "no effect of model".

The manifest's "reported, never refused" table difference is the only trace of the confound.

**What is missing.** The design should state which cache modes exist. If read-through exists, it must refuse, or key by placement, when the table digest differs (unverified).

### SHOULD-FIX 5: `inference_placement.md::§4.3`, `§2.2` and `boundaries.md::§6.3`: the manifest both refuses and reports the same file, and doesn't say where a rerun's envelopes come from

**Defect 1: the manifest contradicts itself.** `boundaries.md` §6.3 keeps "the digests of `data/agents/` … with the same refuse-on-mismatch rule". §2.2 puts `placement.yaml` under `data/agents/`, and it holds the roles, envelopes, policies and the default placement. The same diff then says the merged table's digest and the role envelopes are "reported, never refused".

**Failure scenario 1.** A rerun on a machine whose shipped `placement.yaml` changes only the default loopback placement's model id:
- under one rule it is refused (the `data/agents/` digest differs);
- under the other it is reported;
- an implementer can satisfy either sentence and be wrong by the other.

**Defect 2: where a rerun's envelopes come from is unspecified.** Envelopes are not like placements on a rerun. They are handed to workers at spawn (§2.1) and they determine the rendered prompt, so they determine the key. The design doesn't say whether a rerun spawns its workers with the manifest's recorded envelopes or with the rerun machine's loaded table.

**Failure scenario 2.** If the rerun loads the local table:
1. A rerun machine has no `placement.local.yaml`, or one that its own loader refuses (a placement smaller than an envelope).
2. The rerun can't start at all, although the table is "never refused".
3. Or a changed envelope makes the first request miss deep into a long run, not at start-up.

**What is missing.** The design should state:
- envelopes are refuse-on-mismatch;
- a rerun takes envelopes from the manifest and never loads or merges local placements;
- `placement.yaml`'s placement entries are carved out of the `data/agents/` refuse rule, or moved out of that directory.

### SHOULD-FIX 6: `inference_placement.md::§2.1` "a named `token_counter`": the role's counter isn't required to be a pure function of the text, and Maxim's counters aren't

**Defect.** The render, and so the key, depends on the counter. At 043eab8f:
- `token_counter.py::_LazyTokenCounter` returns `CharEstimateCounter` until a background thread has loaded the model, then upgrades to `LlamaCppTokenCounter`.
- `LlamaCppTokenCounter.count_tokens` silently falls back to `len(text)//3` on any exception.
- `router.get_token_counter()` (the old path, used at `api.py:827` and `console/handle.py:457`) returns the lazy one.

The design moves the counter from "the bound model" to "the role", which is the right move. But it doesn't say the counter must be computable inside the worker with no model loaded and no network, and it doesn't say what identifies its version.

**Failure scenario.**
1. A role names a llama.cpp tokenizer as its counter.
2. In live play the worker renders prompt P1 while the tokenizer isn't ready (character estimate), and P2 after it loads.
3. The rerun, on a machine where the tokenizer loads before the first request, renders P2 for the first request. That is a miss: loud, but the tier-2 rerun is impossible.
4. Worse, if two live runs on one machine race differently, live competence depends on load timing, which §4.1 forbids.

**Fix direction (unverified).** Make the counter vocabulary closed and every counter pure and in-worker, with its implementation version in the envelope's identity. The manifest then refuses a counter mismatch at start-up rather than as a miss mid-run.

### SHOULD-FIX 7: `inference_placement.md::§6.2` (and the `checklists.md` test): the widened dial-invisibility test can't fail on the leak it exists to guard

**Defect.** §2.1 promises "the agent never learns which placement serves it". §6.2's test runs the double "with different placement mixes" and expects the same kinds, receipts, percepts and, under `pinned`, transcript, "since the double answers by request". The double ignores everything but the request, so it would also ignore any placement field that leaked into what it receives.

**Failure scenario.** A builder adds `provenance.placement_id` to the reply value handed to `think`, or to a percept's metadata. The double ignores it, every digest matches, and the test passes. The transcript claim is a property of the double, not of the lane.

Two further gaps:
- The test varies only wall latencies. It has no scripted failures, failovers, cooldown expiry or spend-cap crossing, which are what make the selected placement change mid-run.
- It has no negative control. `boundaries.md` §7.3 requires one for the dial (`abandon` must differ), and this test should equally show it can see a placement difference.

**Fix direction (unverified).**
- A value-level schema test: nothing crossing `AgentPort` or the worker codec carries provenance fields.
- A double variant that echoes its whole input into its output.
- A failure schedule in the mix.
- A negative control: a plant that passes the placement id to the agent must turn the test red.

### SHOULD-FIX 8: `inference_placement.md::§2.6`, `§3`, `§8` [now]: the tests to write need wall delays, cooldowns and a gateway kill ceiling, but no injected host clock is named, so they must either sleep or race

**Defect.** The [now] tests use a scripted transport with "canned replies, delays and failures", cooldowns that are "a wall-time constant per outcome class", a gateway "wall ceiling", "a cancelled call holding its slot until its scripted return", and "`pinned` against `spill` with a full slot". CLAUDE.md bans sleeps and wall-clock reads in tests (`test_the_simulation_and_tests_have_no_hidden_sources_of_nondeterminism`). The delays run inside a separate process (the gateway), so a fake clock has to cross the channel.

**Failure scenario.** Under spill, whether request 2 lands on A or B depends on whether A's scripted 50 ms delay has elapsed when its slot is granted. On a loaded CI runner the test flips. Or the test sleeps and the determinism scan goes red.

**What is missing.** The contract should name one injected host wall clock for the lane, the cooldowns and the gateway (the scripted transport advanced by the test through a host-to-gateway message, or the whole thing in-process for unit tests). It should also say this clock is inside "one named host-only module for timeouts" (§1 there), not a second clock source.

### SHOULD-FIX 9: `inference_placement.md::§4.2` and `npcs_and_sem.md::§6.6` "Resume equivalence" / "Cache repeats": writes to a per-save cache across save, load and branches are unspecified, and the model-less key widens the collisions

**Defect.** The cache is "per save". The design doesn't say:
- when an entry is written: on arrival, while the reply is still held, or at the landing tick;
- whether held, unlanded replies are saved with the host header;
- what happens when two live branches from one save write the same `(hash, occurrence)`.

Before this design, branches that used different models wrote distinct keys. Now every branch collides.

**Failure scenario.**
1. A reply arrives at tick 100 and is cached at `(h, 3)`. It is held for landing at tick 140.
2. The player saves at tick 120. Held replies aren't in the save.
3. The player loads, and the request is re-dispatched live to a different placement.
4. The new answer either overwrites `(h, 3)`, so the pre-save tier-2 rerun now reads the wrong text, or takes `(h, 4)`, so the post-load rerun is off by one occurrence for every later identical request.

The resume-equivalence test with the double can't see either case, because the double gives the same answer twice. This is pre-existing in kind, but the gateway restart and the per-load `open(table)` make it routine.

**What is missing.** The design should state:
- the write point;
- that held replies are part of the saved host state;
- the branch rule: one cache per segment or lineage (O45), never shared by branches.

## NITs

**NIT 10: `inference_placement.md::§2.6`.** `thought_failed(reason=unavailable)` is a new reason. `boundaries.md` §6.1 lists only "budget, timeout, model error", and the log record is versioned with golden fixtures. Because it never dispatched, it has no cache entry, so a rerun meets it as a miss unless it consumes the log record. The design says the run is tier 3, which is consistent, but it should name the reason in §6.1 and say the rerun reads the record.

**NIT 11: `inference_placement.md::§4.2` "its envelope's version".** If the version is a hand-bumped integer, it promises nothing. If it is the digest of the canonical envelope value, the same canonicalizer as `boundaries.md` §6.3, it can't drift from the content. Say which.

**NIT 12: `inference_placement.md::§4.3`.**
- "The set of provenance records … summarised per placement" needs a canonical order to be digest-stable.
- It is derivable from the cache, whose digest is already in the manifest.
- One table digest per manifest doesn't fit a session whose table changed across a load (each load opens a segment, O45). Record it per segment.

## Checked, no finding
- **Provenance holds no wall time** (§4.1). Latency and spend are meters. The attempt count depends on wall time but is a recorded value in the entry, under the cache digest. Nothing on the rerun path recomputes it.
- **Spend and health making the answering model depend on wall time.** Classed correctly: it affects only live dispatch, which is tier 3 by `boundaries.md` §6.3's table. A rerun never dispatches, so neither is consulted. Spend never reaches cognition (§5.3). The client status message is not a world input. Guest join and leave, which change consent, are already log records.
- **Placement decisions and failovers as non-records, tier 1.** Safe. Replay never runs agents and reads only intents, `speak`, `thought_failed`, `thought_cancelled`, `reply_landed` and `floor_event`. Placement reaches the world only through those, plus lateness under floor-holding, which is already a logged `reply_landed` and tier 3.
- **The same, tier 2.** Safe only once BLOCKER 1 and SHOULD-FIX 2 are closed.
- **Landing tick and kind.** §6.1 keeps "resumes at the modelled landing tick whichever model answered". The kind is chosen before the call (`boundaries.md` §7.4). Under dilate, a slower placement changes only dilation.
- **Stream chunking.** Stamps are chunk-independent (`npcs_and_sem.md` §5.3), so the gateway's `chunk` granularity per transport can't move a syllable.
- **Gateway restart and held replies.** Held replies and the continuation header live in the host, not the gateway, so a restart loses none. In-flight attempts are covered by BLOCKER 1.
- **Pinned as the default.** It removes load-dependence of the model from live play, except on failure. That is good for outcome-class stability but irrelevant to tier 1 and tier 2.
- **Gateway environment** (§3). No `PYTHONHASHSEED` is needed, because nothing the gateway computes reaches the world except relayed text, which is recorded.
