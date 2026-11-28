# NPC inspector design v2: delta review, Determinism and replay (with Concurrency and lanes)

**Lens:** Determinism and replay, and Concurrency and lanes (`docs/code_review.md`). **Read:** `npc_inspector.md` v2 (working-tree blob `20b6cbb1`), the fold diff against v1 (`bd0137d`), my round-1 report (`reviews/npc_inspector/determinism.md`), and the author's claims (`fold.md`, blob `5791d71e`). I took the claims as claims, not as facts. I checked v2 against `boundaries.md` §6.1–§6.3, `npcs_and_sem.md` §2.1, §6.3, §6.6 and §9, `realtime_lanes_coop.md` §4, `sem_stimuli.md` §4.1–§4.5 and §5, and `inference_placement.md` §4.2. This was a paper review: I ran no code, so every fix proposed below is *unverified*. Section references are to `npc_inspector.md` unless another file is named.

**Summary:** All 12 round-1 findings are `fixed` in the text. No finding is deferred, rejected or open. The tier split, the gap vocabulary, per-segment records and the frozen-entry bounded queue are real fixes, and they hold up against the owner sections. The fold added text that has 6 new SHOULD-FIX and 4 new NIT. **There is no new BLOCKER, either in the text the fold added or elsewhere.** Two of the new SHOULD-FIX are contract and should fold now:
- D2-S1: the "On replay" column overclaims. Receipts from stage-1 refusals cannot be re-derived, and the delivery cadence is not a tier-1 input.
- D2-S3: a save cannot take an asynchronous record truncated at its barrier without a rule for doing so.

The rest are mechanism. I'd defer them to `phase1/agents`' checklist, each with that step as its trigger, as the stop rule for second paper rounds allows (B33).

## Status of round-1 findings

| Finding | Status | Evidence from v2 |
|---|---|---|
| B1 timing channel; tier-3 claim false | fixed | §1 "What the invariant promises, by tier" holds tiers 1–2 to bit-identical digests and tier 3 to a cost: no record IO on the simulation lane, plus a copy budget. §9 adds a stalled-writer test. The test's form has its own problems (D2-N1), and the tier-3 claim still overstates (D2-S2). |
| B2 value plant may stay green; home digest has no owner | fixed | §9 "On/off with an echo double": the double folds every input it receives into its home, and the home digest is c14n-1, "owned by this design for the double". The guard is proved by breaking what it guards. Residual: D2-N2. |
| B3 no lane owns the IO; slow or failed writes | fixed | §3 "The lane": frozen entries, a bounded queue, the simulation lane never blocks and does no IO, and a record lane drains the queue. §3 "Failure never stops the world": `dropped` and `stopped` gaps, a typed status and a meter. Stopping the run instead is §10 item 4. Residuals: D2-S2, D2-S4. |
| S1 no kind marks the record incomplete | fixed | §2 adds a `gap` kind with closed reasons `dropped stopped torn rewound off`, plus `tick_end`. Both are in the registered `mind_record.kinds` line. |
| S2 cannot span segments | fixed | §3 "One record per agent per log segment": the header carries its own segment and its parent's, a save truncates the record, a load opens a child record, and the rule links `inference_placement.md` §4.2. Restarts do open segments (`npcs_and_sem.md` §6.6, O45). The truncation rule is not implementable as written against the asynchronous lane (D2-S3). |
| S3 torn line; drift against the log | fixed | §3 "Crashes": the writer writes whole ticks, the reader trims a torn final tick into a `torn` gap and refuses all other corruption, and a view reads both files only up to the last tick complete in both. Residual: D2-S4 (per-entry queueing can tear a tick before it reaches disk). |
| S4 a restart rewinds the agent | fixed | §2: a `rewound` gap names the home's snapshot tick, views mark the write pointers in that span as lost, and "anything decoded from a refused frame" is excluded by name. |
| S5 the replay split does not match the log | fixed | §2's table has an "On replay" column per kind, and log facts are read from the log rather than copied. §9: replay never writes a record and compares deliveries byte for byte. The `stimulus` row's "re-derived" claim is only partly true (D2-S1). |
| S6 a stamp that admits arrival order | fixed | §1 "Its clock": entries are stamped by the world-time event, "never with when the host saw it", and an arrival tick is never a stamp. The stamp for thought entries is ambiguous (D2-S5), and the §9 test cannot see an arrival stamp (D2-S6). |
| N1 no within-tick order key; no reproducibility test | fixed | §3: kind in the table's order, then actor id, then sequence. §9 "Reproducibility" runs under different hash seeds. Residual: D2-N3. |
| N2 unbounded growth | fixed | §3 "Size": the rotation unit is the segment, a save carries truncated records, and the reader's budgets are contract. The queue's capacity is mechanism and is rightly left to the build step. |
| N3 a purge rewrites the file; the rerun must stop at O26 | fixed | §2: the record holds no free text. No purge touches it, and tier-1 delivery comparison is unaffected by `speak` redaction because deliveries carry no text. |

## New findings in text the fold added

### D2-S1 (SHOULD-FIX, contract): "re-derived on replay" is false for stage-1 receipts and for delivery grouping

**Where:** `npc_inspector.md::§2` (the table, `stimulus` row, "re-derived, and compared with the recorded copy"); `§9` "Replay against the record".

Two parts of a recorded delivery cannot be rebuilt from tier 1's inputs (scene, header and log; `boundaries.md` §6.3's tier table):

- **Receipts from stage-1 refusals.** `receipt.kinds` v1 is `malformed limit accepted`, and `malformed` and `limit` are "decided by stage 1 alone" (`sem_stimuli.md` §6.2). The pipeline is decode → stage 1 → log (`boundaries.md` §6.1 rule 1), and the log's "refused intents" are refusals at apply (§6.2). So an NPC intent refused at stage 1 never reaches the log. v2 says so itself: the `refusal` row reads "recorded only (the log holds stage-1-accepted intents)". Replay therefore cannot recompute the `malformed` or `limit` receipt that a later delivery carried.
- **Delivery grouping.** A `BoundFrame` concatenates "the undelivered ticks' events and receipts" (`sem_stimuli.md` §4.2). Under D14, delivery runs at the cognition rate (§4.6), which is an integer divisor with a per-actor phase (`boundaries.md` §7.3; `npcs_and_sem.md` §2.1). Idle agents may step at a coarser divisor (§6.6). Agent timing lives in `data/agents/`, which is in the rerun manifest, not in the header (`boundaries.md` §6.3). Nothing places the per-actor divisor and phase in the log or the header. `join` carries bodies and bindings only.

What `sem_stimuli.md` §5 does guarantee is narrower: the bound values and the receipts are digested *per tick, independent of delivery*. Per-tick values are re-derivable. Per-delivery bytes are re-derivable only if the cadence is a tier-1 input and every receipt kind is derived from logged facts.

**Failure scenario.** A scripted double emits one out-of-range `strike`, which is refused `limit` at stage 1. The next delivery carries the `limit` receipt and is recorded. In replay, no intent exists for it, so the recomputed delivery lacks the receipt. The byte comparison goes red on a correct writer. Faced with that, an implementer will either drop receipts from the comparison, so a drifting receipt copy goes unseen, or rebuild them from the record's own `refusal` entries, so the record becomes an input to its own check. A double whose cadence comes from `data/agents/` goes red, or is skipped, the same way.

**Fix (*unverified*).**
- State the replay comparison per tick, against `sem_stimuli.md` §5's bound lane (values, plus receipts derived from logged intents).
- Check `malformed` and `limit` receipts only for consistency with the same tick's `refusal` entries, and label that check as such.
- Either name the per-actor divisor and phase as a tier-1 input (a `join` field, or a header slot owned by `boundaries.md` §6.3), or compare only per tick.

**Upstream.** The same stage-1 hole appears to affect `sem_stimuli.md` §5's bound lane, which digests "the receipts produced that tick" and is compared on replay. That section's owner should check it. It is not this design's to fix.

### D2-S2 (SHOULD-FIX): the record lane's identity is unnamed, and "within the copy budget" ignores the shared disk

**Where:** `§3` "The lane" ("the pattern of `realtime_lanes_coop.md` §4.1's record lane"); `§1` "Tier 3".

- **The citation is wrong.** Lanes §4.1's record lane drains no queue. There, the simulation lane writes the world log synchronously, and the record lane "only flushes and rotates". v2 is a different pattern, an asynchronous drain.
- **The lane is unnamed.** v2 does not say whether the mind record shares that thread or has its own.
- **The disk is shared either way.** The simulation lane still does synchronous world-log IO every tick. Mind-record writes compete for the same file system and buffer cache.

**Failure scenario.** On a slow disk in co-op under floor-holding, the record lane writes 20 agents' stimulus entries every tick. The world log's synchronous writes on the simulation lane slow down. So does its flush, if the two records share the flushing thread. The barrier lengthens, and a `reply_landed` tick moves. Meanwhile the "stalled writer" test stays green, because a stalled writer does no IO at all. The tier-3 sentence promises "per-barrier time ... within the copy budget", which is false under this load.

**Fix (*unverified*).**
- Name the record lane as its own thread, owned by the host, separate from the world log's flush.
- Restate tier 3 as my round-1 fix said: the record is host load. It has no IO on the simulation lane and its own B5 row, and it carries no promise about barrier time under contention.
- Add a B5 meter that measures the world log's write time with the record on and off.

### D2-S3 (SHOULD-FIX, contract): a save cannot truncate an asynchronous record at its barrier

**Where:** `§3` "A save carries each record truncated at the save's barrier"; `§8` (Save v1).

A save is a host command, applied in log order on the simulation lane (`boundaries.md` §6.2, rank 40). At that moment the record lane may lag the barrier by up to the queue's depth. To carry the record "truncated at its barrier", the save has three options, and the design names none:

1. Wait for the drain. That is the simulation lane blocking on IO pace, which §3 forbids. Under a stalled writer the save never finishes, which brings back B1's channel in tier 3.
2. Copy the queued in-memory entries.
3. Let the record lane finish the save asynchronously, which means the save is not complete at its barrier.

**Failure scenario.** A save is taken during a disk stall. Under option 1 the world freezes. Under the obvious implementation of copying the file as it stands, the save holds the record up to tick T−40, with no gap marking ticks T−39 to T. After a load, the child record's parent appears to end early, and a view reads it as a quiet NPC. That is the false causal chain round-1 S1 was about.

**Fix (*unverified*).** Pick one rule and state it as save contract:
- **Either** the save copies the file plus the queued entries up to the barrier, and writes a `dropped` gap for anything already lost;
- **or** the save's record is closed asynchronously, and the save's header records the tick to which its record is complete.

### D2-S4 (SHOULD-FIX): per-entry queueing can tear a tick, and a `dropped` gap is wall-dependent

**Where:** `§3` "The lane" ("builds each entry ... puts it on a bounded queue"; "writes whole ticks"); `§3` "Failure"; `§9` "Reproducibility".

Entries are queued one at a time, but the file is written in whole ticks.
- **Torn ticks.** If the queue fills partway through tick T's entries, some of T is queued and the rest is lost. The record lane then either writes a partial tick with a `tick_end` (a lie) or must invent a rule. And the lane cannot know the dropped span unless the simulation lane tells it, but v2 says the lane writes the gap "when it catches up".
- **Wall dependence.** Overflow depends on how fast the lane drains in wall time. So whether a `dropped` gap appears, and where, is wall data. That makes §9's "two record-on runs give byte-identical records" a flaky test whenever the queue ever fills.

**Failure scenario.** A CI host under load drains slower in one run than in the other. One record holds `gap(dropped, 4000–4012)` and the other does not, and the reproducibility test fails intermittently. That breaks "Tests are deterministic".

**Fix (*unverified*).**
- The simulation lane enqueues one frozen batch per tick, so a tick is queued or dropped whole.
- It counts the first and last dropped tick itself and hands that span to the next batch it enqueues.
- §1 says record bytes are reproducible only for gap-free records, and the reproducibility test sizes the queue so that it cannot overflow.

### D2-S5 (SHOULD-FIX, contract): a thought entry's stamp is either a future tick or unknown when it is written

**Where:** `§1` "Its clock" ("a thought's modelled landing tick, or the tick its `reply_landed` record names"); `§2` `thought_state` ("each segment's modelled landing tick"); `§3` (whole ticks).

A `thought_state` entry holds the landing tick of every segment, and those ticks lie in the future at request time. Under floor-holding, the landing tick is unknown until `reply_landed` (`npcs_and_sem.md` §6.6). If the stamp is the landing tick, an entry built at barrier T is filed under a later tick L. Either ticks then stop being monotonic in the file, which breaks the torn-tick trim and "last tick complete in both", or the simulation lane must hold the entry until L. A tier-3 rerun would also file the same entry under different ticks.

**Failure scenario.** Two implementations differ. One files the entry under T and carries L as a field. The other holds it until L. Both pass the stamp assertion, and their records differ byte for byte.

**Fix (*unverified*).**
- The stamp is the tick of the barrier at which the host-owned header changed (a request at step, a resume at its landing tick, a cancel): a world-time event, known when the entry is built.
- Landing ticks are fields, not stamps.
- `gap` entries are stamped by the tick at which they are written, and carry their span as fields.

### D2-S6 (SHOULD-FIX, mechanism, defer to `phase1/agents`): the stamp test can't see an arrival stamp

**Where:** `§9` "Stamps" ("the writer asserts that each stamp equals the world-time event it names"); `§9` "Reproducibility".

- **The assertion is circular.** It compares the stamp with the value it was computed from. A writer that takes its stamp from arrival also asserts against arrival, and stays green.
- **The reproducibility test can't vary arrival.** It runs the double at a fixed latency in ticks (`realtime_lanes_coop.md` §4.3), so arrival timing never varies, and an arrival-derived stamp yields identical records in both runs.
- **The round-1 guard is gone.** Round-1 S6's second plant relied on a tier-2 rerun byte comparison, and v2 moved the rerun comparison to [Phase 4].

**Failure scenario.** A writer stamps `thought_state` with `now_tick` at the moment the pump hands the reply over. Every [agents] test is green.

**Fix (*unverified*).** Give the reproducibility test the release-order legs of `sem_stimuli.md` §4.1's overlap gate: stub replies released at host hooks in two fixed orders. Plant an arrival stamp and watch the test go red. **Deferred by this reviewer to `phase1/agents`' checklist; trigger: that step's test list.** The contract part, the stamp itself, is D2-S5.

### D2-N1 (NIT, mechanism, defer to `phase1/agents`): the stalled-writer test measures wall time

**Where:** `§9` "A stalled writer" ("leaves the simulation lane's per-barrier time within the copy budget").

As worded, this test reads the wall clock and asserts a timing threshold. "Tests are deterministic" forbids the wall clock in tests, and lanes §4.1 asks for best-of-N runs or operation counts. Make it a structural test, *unverified*:
- a writer blocked forever on an event;
- the simulation lane completes N ticks;
- a `dropped` gap and the typed status appear;
- the world digest is unchanged.

The time budget belongs in the B5 meter.

### D2-N2 (NIT, mechanism, defer to `phase1/agents`): the echo plant can be a no-op; gated writes aren't folded

**Where:** `§9` "On/off with an echo double".

- **A no-op plant.** The plant feeds "a recorded value into a delivery". But a `stimulus` entry *is* a copy of a delivery. In a static scene, feeding back tick T−1's value leaves tick T's delivery unchanged, so the test stays green. The plant must inject a value that differs from the true delivery, for example a recorded count or a perturbed copy, *unverified*.
- **A missing input.** The fold list ("deliveries, receipts, resumes") drops round-1's "gated writes" passed to `settle`. A plant on that channel is invisible to the echo home.

### D2-N3 (NIT, contract): `readout` sorts after `tick_end`; "sequence" is undefined

**Where:** `§3` "The order within a tick is ... kind in the table's order, then actor id, then the entry's sequence".

- **`readout` comes too late.** The table's order puts `readout` after `tick_end`, so in its [later] form `readout` entries would land after the tick's end marker.
- **Actor id adds nothing.** The actor id is constant within a per-agent record.
- **"Sequence" is undefined.** If it is append order on the simulation lane, it is deterministic only if the merge order of step 7 is. It should cite `npcs_and_sem.md` §9's canonical order, or the intent's `seq` for refusals.

Fix, *unverified*: `tick_end` is always last, and each kind names its sequence source.

### D2-N4 (NIT): the on/off flag is in the header, but switching off is a gap

**Where:** `§3` ("Whether the record was on is a field of the log header"); `§2` gap reason `off`.

A header field is fixed per segment, while the `off` gap implies the record can be switched mid-segment. Switching it *on* mid-segment has no marker at all: the record simply starts at tick T. A view then cannot tell "on from T" from "lost before T". Say whether the switch is per segment only (then drop `off`, or keep it only for a stop), or give switching on its own entry. *Unverified.*

## What holds

- In tiers 1 and 2, no path leads from the record into `Simulation` or an agent. The import rule (§4) and the writing scan cover the value channel, and the echo double makes the guard able to fail, once D2-N2's plant is real.
- The simulation lane does no record IO and never blocks on the record, and entries are frozen when they cross lanes. That answers the Concurrency lens's freeze question, provided a stimulus entry references `BoundFrame`'s deep-frozen arrays (`sem_stimuli.md` §4.2) rather than copying them into writable ones.
- A failure becomes a reported gap, a status and a meter, never an exception at the barrier and never a swallow.
- Moving every log fact out of the record (§2) removed most of round 1's drift risk. There is now one owner per fact.

**New BLOCKERs in text the fold added: none.**
