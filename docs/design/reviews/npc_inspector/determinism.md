# NPC inspector design v1: Determinism and replay (with Concurrency and lanes)

**Lens:** Determinism and replay, and Concurrency and lanes (`docs/code_review.md`, the rows of those names). **Read:** `docs/design/npc_inspector.md` and its `contracts.md` row, as staged on `phase3/npc-inspector` (tree `00b97665`, base `origin/main` `e6d6a7f`). Against: `CLAUDE.md`; `boundaries.md` §4, §6.1–§6.4; `npcs_and_sem.md` §4.4, §4.8, §6.3, §6.6 and §9; `realtime_lanes_coop.md` §4; `inference_placement.md` §4.1–§4.3; `decisions/npcs_and_sem.md` O26; `plans/checklists.md` (the scripted double); `tests/test_determinism.py`. This was a paper review. I ran no code, so every proposed fix below is *unverified*. Section references are to `npc_inspector.md` unless another file is named.

**Summary:** 3 BLOCKER, 6 SHOULD-FIX, 3 NIT. The core idea is sound for tiers 1 and 2: the record is an output, copied from values that already crossed the membrane, and never read back. Three things are wrong:
- The isolation guard as written cannot see the channel most likely to leak, which is timing. It may not see the value channel either.
- The record's format has no notion of log segments.
- The design never says which lane does the IO, or what happens when that IO is slow or fails.

---

## B1 (BLOCKER): the on/off guard cannot see the timing channel, and the claim is false in tier 3

**Where:** `npc_inspector.md::§1` ("Writing it must not change any world or agent digest. Test: …"), §4 "Determinism".

The design treats isolation as a value property: nothing reads the record. But writing the record also costs simulation-lane wall time, and several things are decided in wall time:
- the floor-holding lateness (`npcs_and_sem.md` §4.4);
- `reply_landed(thought, tick)` under floor-holding, and silent late landing in co-op (§4.4, §6.6);
- the per-park wall ceiling that produces `agent_failed(hung)` (§6.6);
- under `abandon`, the wall pace of the run.

**Failure scenario.** A live co-op run uses floor-holding, with the record on and a slow disk. Each barrier spends an extra 2 ms in `write`, so the world advances fewer ticks per wall second. A model reply that arrives 3.1 wall seconds after its request now lands at a different tick than it would have with the record off. The consequences:
- `reply_landed` carries a different tick;
- the NPC's `speak` applies at a different `apply_tick`;
- a listener's percept and the world digest differ;
- a `floor_event(cause=lateness)` may appear or vanish.

In other words, turning the inspector on changed what reached other agents. Tier 3 is allowed to be irreproducible, but the design states the invariant unconditionally ("must not change any world or agent digest"), and that statement is false in tier 3.

**Why the test cannot catch it.** The proposed test runs the scripted double, which has a fixed latency in ticks (`realtime_lanes_coop.md` §4.3, last bullet) under dilate, so no wall time ever reaches the world. The test is green whatever the writer's cost. This is "a test that cannot fail" for the channel that matters.

**Fix (*unverified*).** Split the invariant in two in §1:
- **Tiers 1 and 2:** bit-identical world and agent digests with the record on and off. This is the existing test.
- **Tier 3:** the record is host load, like any other. It takes no simulation-lane IO (B3), it has its own B5 budget per barrier, and a meter counts the simulation-lane time spent copying entries. Add a test that injects a writer stalled for N wall seconds and asserts that the per-barrier time on the simulation lane is unchanged within the copy budget. That test can fail.

## B2 (BLOCKER): the value-channel plant may stay green, and "agent-home digest" has no owner

**Where:** `npc_inspector.md::§1` ("A plant that feeds one record value back into a frame goes red").

The double is "scripted per test" (`plans/checklists.md`). A scripted agent's outputs, and usually its home state, do not depend on the frame it receives.

**Failure scenario.** The plant writes a recorded percept value into the next tick's frame. The world digest is computed over `Simulation` state, not over the frames sent to agents, so it does not move. The double ignores the frame, so its home is unchanged. Both digests stay identical and the plant passes. The guard "goes red" only if the double's home state is a function of everything it received.

Separately, no design defines an agent-home digest. A grep of `docs/design/` and `docs/plans/` finds only `sim_core.md` §9's per-tick world digest, and the Maxim-side state digest OD-EA5 and OD-EA6, which is for real Maxim and not for the double. Without an owner for that digest, the test's second half has no defined meaning.

**Fix (*unverified*).**
- Name an owner for the agent-home digest: the double's home, hashed with the `sha256/c14n-1` canonicalizer.
- Require the double used by this test to fold every input it receives (frames, receipts, gated writes, resumes) into its home, as an "echo" script.
- State in the design that the guard is proved by deleting what it guards: plant a feedback, watch the test go red.

## B3 (BLOCKER): no lane owns the record's IO, and nothing says what a slow disk or a failed write does

**Where:** `npc_inspector.md::§3` ("The host writes it, at the barrier"), §4 "Cost".

"The host writes it at the barrier" puts file IO on the simulation lane. The design never names the lane or a channel. `realtime_lanes_coop.md` §4.1 sets the world log's pattern: the simulation lane writes the log synchronously, and a record lane "only flushes and rotates".

If the mind record follows that pattern:
- A full or slow disk blocks the simulation lane. Under dilate and floor-holding this is B1's channel, and it stalls every session in co-op.
- A failed write raises on the simulation lane. Per lanes §4.1, "an exception in the simulation lane is a bug, and the host fails loudly". A diagnostic output can then kill the authoritative world. The only alternative is a swallowed `OSError`, which breaks the no-silent-swallow rule.

If the record does not follow that pattern, the design gives no bounded channel, no rule for a full queue, and no freeze rule for messages crossing lanes. The Concurrency lens asks "is every message crossing a lane frozen?" Here the record copies decoded `StepOutput` values; if the writer canonicalises or redacts in place (sorting a list, blanking speech for a bug-report copy), it mutates what goes to `settle`.

**Fix (*unverified*).** State as contract:
- The simulation lane only builds frozen entry values and puts them on a bounded queue to a record lane, never blocking.
- On overflow or a write error, the record lane stops writing and appends one terminal entry saying where and why the record ended. That entry is reported and metered, never swallowed, and never stops the world.
- Whether a record failure should instead stop the run is the owner's call, but it must be decided in the design.

This needs a kind the closed vocabulary lacks (see S1).

---

## S1 (SHOULD-FIX): the closed kind list has no way to mark that the record is incomplete

**Where:** `npc_inspector.md::§2` (`mind_record.kinds`).

The record refuses any kind outside `percept intent thought write receipt lifecycle state`. That leaves no way to say:
- entries were dropped (B3's overflow);
- the writer stopped after an error;
- the file ends at a crash (S3);
- a span was redacted (S5, O26);
- the agent's state rewound on a restart (S4).

**Failure scenario.** A record that lost ticks 4,000 to 4,200 to a full queue reads exactly like one in which the NPC did nothing for 200 ticks. The explorer's "cause behind every line" then draws a false causal chain across the gap.

Because the vocabulary is a registered contract, adding a kind later is a contract change. It should be decided now, in this round.

## S2 (SHOULD-FIX): one record per agent per run, with one header, cannot span log segments

**Where:** `npc_inspector.md::§2` ("One record per agent per run", "a header with the run's log root id and segment").

Several things open a new log segment:
- each restore (`boundaries.md` §6.3);
- each worker restart after `agent_failed` (`npcs_and_sem.md` §6.6, O45).

A load also branches. The response cache solved the same problem: one cache per segment, and a child inherits the parent "as it stood at the save's header snapshot" (`inference_placement.md` §4.2).

**Failure scenario.** A player saves at tick 500, plays to tick 800, then loads the save. The child segment replays ticks 500 to 800 differently. With one record per run, the file now holds two different `(actor, tick=600)` percepts and no way to tell which branch each belongs to. A record with a single header also misstates the segment for everything after the first restore. Saves are affected too: "a save carries the record" leaves open whether the save at tick 500 carries entries written after 500.

**Fix (*unverified*).** Make it one record per (agent, segment), with the parent segment in the header. A save carries each record truncated at the save's barrier, and a load opens a child record. This follows the response cache's rule.

## S3 (SHOULD-FIX): crash mid-write; a torn last line, and drift against the world log

**Where:** `npc_inspector.md::§2` "The format", §3.

The format is strict JSON lines, and the reader refuses what it doesn't know. When the host crashes, lanes §4.1 flushes the world log, including the record that caused the crash. The design says nothing about the mind record on a crash.

**Failure scenario.** A crash at tick 9,102 leaves half of a `percept` line on disk. The strict gate refuses the whole file, so the record of the session most worth inspecting cannot be opened. If the gate instead tolerates the torn line, the record and the world log can disagree about which ticks are complete:
- the record may hold entries for a barrier whose log records were never flushed;
- the log may hold records for a tick the record never reached.

The explorer then joins mismatched ticks.

**Fix (*unverified*).**
- The record lane writes whole ticks, with a tick-end marker (S1).
- The gate refuses any corruption except a torn final tick, which it trims and reports.
- A view reads both files only up to the last tick complete in both.

## S4 (SHOULD-FIX): a worker restart rewinds the agent while the record runs on

**Where:** `npc_inspector.md::§2` "lifecycle", §4 "Replay".

A restart reloads the agent from its last saved home (`npcs_and_sem.md` §6.6). Memory writes applied at `settle` after that save are gone from the agent but stay in the record. The refused frame that caused `agent_failed(protocol)` is untrusted input, and the design does not say whether any of its decoded content enters the record.

**Failure scenario.** The explorer shows a memory write from tick 3,000 as part of an NPC that, after a restart at tick 3,050 from a home saved at tick 2,900, no longer holds it. The "cause behind every line" then explains later behaviour from a memory the agent does not have.

**Fix (*unverified*).**
- The restart's `lifecycle` entry names the home snapshot's tick.
- Views mark every `write` entry after that tick and before the restart as lost.
- Nothing decoded from a refused frame enters the record.

## S5 (SHOULD-FIX): §4's replay split does not match the log

**Where:** `npc_inspector.md::§4` "Replay".

§4 says replay rebuilds "intents, speech and receipts" from the log, and takes thought lifecycles only from the saved record. Checked against `boundaries.md` §6.1–§6.2, the split is wrong both ways:
- **Intents.** The log holds intents after stage 1 (decode → stage-1 → log), including those refused at apply. The record's `intent` entry holds "its stage-1 result", so intents refused at stage 1 are not in the log and cannot be re-derived. The invocation pid can be.
- **Receipts.** These are "derived, never input": replay recomputes them, which is right. But the `receipt` entry's adapter valence also depends on the adapter's version (O-note `ModulatorResult`). The design should say that it is recomputed and checked, or recorded.
- **Thought lifecycles.** The log carries `thought_cancelled`, `thought_failed`, `reply_landed` and `floor_event`. These are partly re-derivable, not record-only.
- **`lifecycle` entries.** `agent_ready` and `agent_failed` are host log records, so they are re-derivable too.

The design also never says whether a replay writes a mind record. If replay runs with the record on, the host has no agents, so it would write a different, thinner record over or beside the saved one.

**Fix (*unverified*).**
- Make a table of entry kinds marked *log-derived* or *recorded only*.
- Replay never writes a record file. It produces the log-derived entries in memory and compares them with the saved record's, byte for byte. That gives a test that can fail, and it catches a record writer that drifted from the log.

## S6 (SHOULD-FIX): the stamp "the tick at which the host saw it" admits arrival order

**Where:** `npc_inspector.md::§1` ("stamped with the integer tick at which the host saw it"), §2 "thought".

The tick at which the host *sees* a model reply is its arrival tick, which is wall-time data. `think` resumes only at the modelled landing tick, and early replies are held (`npcs_and_sem.md` §6.6). Schema closure cannot catch this: an arrival tick is a legal integer in a legal field.

**Failure scenario.** Two tier-2 reruns from the same cache produce records that differ only in `thought` entries stamped at arrival, because cached replies arrive "instantly". §4's rerun comparison then reports a divergence that is not one. Under floor-holding the same thing happens live.

**Fix (*unverified*).** Every entry is stamped with the world-time event it reports:
- the barrier tick for `step` and `settle` values;
- the landing or `reply_landed` tick for a thought;
- `apply_tick` and `apply_us` for an intent.

Never an arrival tick. "A planted wall-time field is refused" also needs a second plant: a wall-derived value in a legal tick field, caught by the tier-2 rerun's byte comparison.

---

## N1 (NIT): no within-tick order key for the record, and no test that the record reproduces itself

**Where:** `npc_inspector.md::§3` ("in canonical order (`npcs_and_sem.md` §6.3, §9)"), §4.

The ordering key `boundaries.md` §6.2 defines, `(apply_tick, kind_rank, apply_us, actor_id, seq)`, ranks only log kinds. `percept`, `write`, `receipt` and `lifecycle` have no rank, so two implementations can byte-order a tick differently. The design should:
- state the record's own key, or extend `kind_rank` in its owner section;
- add a test that two record-on runs, including runs under different `PYTHONHASHSEED`s (the pattern of `test_runs_in_processes_with_different_hash_seeds_agree`), give byte-identical records.

Without that test, §4's rerun diagnostic has no baseline.

## N2 (NIT): the size meter is per world minute, but the growth is unbounded

**Where:** `npc_inspector.md::§2` "Its size".

The codec's size budgets bound each frame, not totals. A run of 864,000 ticks a day for 20 NPCs grows the record, and every save that carries it, linearly with no cap. A per-world-minute rate is correct and independent of the dial. Still, the contract should name:
- the rotation unit, which could be the segment (S2);
- what a save carries;
- the bound that triggers B3's overflow path.

## N3 (NIT): a purge rewrites an append-only file, and the rerun comparison must stop at O26's boundary

**Where:** `npc_inspector.md::§3` "Guest text", §4 "Rerun".

Redaction makes the record mutable after the fact, across every segment copy and every save holding one (S2). A crash mid-redaction needs the same torn-write rule as S3. §4's rerun comparison must stop at the first redaction boundary the log marks (O26), or it reports the redaction itself as a divergence in agent behaviour. Whether the record joins O26's reach is the owner's ruling; these are the consequences either way.

---

## What holds

- §1's value rule matches `boundaries.md` §6.2: the record is never a log input, replay calls nothing live, and nothing in the engine imports the reader.
- The import contract and ownership scan proposed in §3 are the right mechanical guard for the value channel.
- Copying only decoded barrier values adds no channel round trip, so `npcs_and_sem.md` §6.6's barrier cost budget is untouched apart from the copy itself.
- No wall-clock source is named as a record input, and §5's exclusion of `ts`, `energy_status` and `memory_recall` epochs is right.

I found no path by which the record reaches `World` or an agent in tiers 1 and 2, once B2's guard can actually fail.
