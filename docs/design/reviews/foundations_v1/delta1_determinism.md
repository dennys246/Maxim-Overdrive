# Determinism and replay lens (with performance and lane concurrency): foundations, delta round 1

Lens: Determinism and replay, also covering Performance and Concurrency and lanes. Commit: 18623ce
(`phase1/design-v2`), reviewed as `git diff 4f7a754 18623ce -- docs/`. Date: 2026-11-16. Counts: **2 BLOCKER,
10 SHOULD-FIX, 7 NIT.**

Read: `boundaries.md` v3 (§3, §4, §6, §7, §10, the fold table), `npcs_and_sem.md` v2 (§2.1, §3, §4, §5.2–§5.3, §6,
§7.3, §9, the fold table), `maxim_upstream/world_clock_release_DRAFT.md`, `maxim_upstream/embeddable_agent_DRAFT.md`,
the lanes supersession note, `standards_backlog.md` B5, and round 1 (`determinism.md`). Probes were run in the main
`.venv` (numpy 2.5.4, CPython 3.14.6, Apple silicon). Each one is quoted where it is used.

## Correction to my round-1 review (first, because v2 copied it)

Round 1's DR-B5 table had a row "Ten idle NPCs, 2 thoughts per world minute | ~10× | about 6.7×". That mixed up two of
v1's rows. v1 said **1×** for ten NPCs thinking twice a world minute each, and **~10×** for idle NPCs thinking once in
five world minutes. My 6.7× is the latency bound for the *idle* row: λ = 10/300 per s, f = 1 − e^(−1/30) ≈ 0.033,
1/(0.033·3 + 0.967/20) ≈ 6.8×. v2's §4.5 now prints "Ten idle NPCs, 2 thoughts per world minute **each** | ~10× |
about 6.7×", which is wrong on both columns. With that load, f ≈ 0.28, and the latency bound is about 1.1× even with
unlimited workers. With v1's single local model it is at most 1×, and below 1× once the queue forms. DD-S6 has the
corrected table.

## Summary

Three folds hold: the single ordering key, the rerun manifest and tier table, and the strict, never-on-replay cache.
Two of the headline folds don't.

- **The write window still leaks (DD-B1).** Measured: a view taken of the window's fresh writable array inside the
  window writes the world after the window has swapped that array in as the read-only owner. The proof test as worded
  ("a view unlocked inside a window") exercises a different escape, one that already raises. So it passes on the
  leaking design, which is exactly round 1's DR-B4 failure again.
- **The barrier can work, but the agent execution model it sits on contradicts itself (DD-B2).** Three things are
  said at once: one owner thread per agent, where "only the LLM call leaves it"; a `think` that runs a whole
  deliberation through a blocking `LLMBackend`; and drives and P0 that keep running while the thought is pending.
  All three can't hold together. Either the substrate freezes for every thought, or `think` runs on a second thread
  whose exclusion with `step` isn't specified. In the second case DR-B1's race returns inside one agent.

Tier 1 is still exact under every option. Tier 2 can hold at any dial once DD-B2's baton rule is written down and
tier A lands. Its guard can't see a missing barrier as specified (DD-S1).

On performance, the fixes stack copies. With DD-B1 done right, each window costs one or two full-grid copies, and
each frame publish costs another. At 20× with active NPCs, frames are published about every tick, and three 80 MB
copies (5.7 ms each, measured) don't fit a 5 ms tick. Two more problems: the tripwire can't see numpy's random
functions at all (measured), and the B5 rows the documents cite exist only in prose.

---

## BLOCKER

### DD-B1. The ownership window still lets a view escape, and its proof test can't see it

`boundaries.md` §4.1 ("yields fresh writable arrays … swaps them in as the new read-only owners at exit. No handle
outlives the window"; the proof test "a view unlocked inside a window, written after the window closes")

Measured (numpy 2.5.4):

```python
owner = np.zeros(8); owner.flags.writeable = False
w = owner.copy()              # enter: a fresh writable array
cached = w[2:5]               # a law caches a view inside the window
w[0] = 1
w.flags.writeable = False     # exit: w becomes the read-only owner
owner = w
cached[0] = 99                # succeeds: owner == [1, 0, 99, 0, ...]
```

Setting the base's flag doesn't reach views that already exist. So "no handle outlives the window" is an assertion,
not a mechanism. A view taken of `w` is born writable and needs no unlock. The specified proof test unlocks a view of
the *old* owner, whose base is read-only, and that already raises (measured: "cannot set WRITEABLE flag to True of
this array"). The test is green on the leaking design.

Failure scenario: heat caches `self._t_interior = w.temperature[1:-1, 1:-1]` on its first step "to avoid
re-slicing". A later refactor calls `heat.relax()` from an instrument helper outside `step`. It writes through the
cached view into the live owner. Nothing raises, and the world changes outside the pipeline.

Fix:
- **The owner a window leaves behind must be a buffer that was never exposed writable.** At exit, copy the window's
  arrays into new owners. Writes through escaped views then land in a dead buffer, which is harmless to the world, and
  a physics test sees them as a no-op.
- **Better:** make the window copy-on-write per chunk (or per channel). It hands out writable copies only of the
  chunks a law or the applier asks for, and commits each by copying it into a fresh owner chunk. That bounds the cost
  (DD-S8).
- **Re-word the proof test:** take a view *of the window's handle* inside the window, close the window, write through
  the view, and assert that the world digest is unchanged. Prove the test by deleting the exit copy and watching it
  go red.

### DD-B2. The agent execution model contradicts itself, so the barrier's correctness is undefined

`boundaries.md` §7.1 ("One owner per agent … Only the LLM call leaves it"; parked = "returned from `step`, or waiting
at the gateway for a held response"); `npcs_and_sem.md` §6.3, §4.4 ("Under O6 agents never block inside a turn";
"drives keep drifting"), §4.5 lever 4 ("P0 carries the gap"); `embeddable_agent_DRAFT.md` §4.1 (`think(request)`
"runs one deliberation through the host's `llm`"), §4.2 (the gateway *is* an `LLMBackend`, `complete()` blocks), §9
("How tool calls inside `think` are answered … open")

Here is what the documents say a thought does:
- `think` is a synchronous call that makes several blocking `LLMBackend` calls, with tool calls answered by the host;
- its Python runs on the agent's owner thread ("only the LLM call leaves it").

Then, while a thought is pending, that thread is blocked in the gateway for many ticks, so `step` can't run. Drives
don't drift, P0 can't backchannel through a P1 gap, and the reflex substrate is frozen. That contradicts §4.4, §4.5
and §5.1.

The only alternative is for `think` to run on a second thread. Then the documents never say three things:
- that `step` and `think`'s code are mutually exclusive;
- in what order a release and the agent's `step` run within a tick;
- which park states exist. A tool call waiting for its receipt, and a stream's `next()` waiting for a token, are
  missing from the list.

`think` reads drives, context and recall, which `step` mutates every tick, even under generate vs apply, since `step`
"advances drives, the experience clock and the substrate". If `step(T+1)` overlaps the post-release segment, the next
prompt sees tick T or tick T+1 state depending on the OS scheduler. That is DR-B1's race inside one agent.

§4.4's no-deadlock argument also changes. It assumed "agents never block inside a turn". A blocking `think`
on a bounded pool of think threads has early-held thoughts holding threads until their modelled time. With more
pending thoughts than threads, the earlier-due thought can't start, and the world dilates forever. That is Arch B2
again.

Failure scenario: an implementer reads §7.1 literally and runs `think` on the owner thread. Every NPC is a statue for
3 s of wall time per thought (the "statue" of §4.4, now in every thought rather than only until the reflex layer
exists). The fix they reach for is a second thread with no exclusion. Tier-2 reruns then differ in the prompt of
segment two, depending on whether `step(T+1)` ran first.

Fix (Overdrive's side, buildable against a blocking backend):
- **A per-agent baton.** An agent's `step`, `settle`, push and the running part of `think` hold one baton. `think` may
  run on its own thread, one per agent with a thought in flight, never a bounded pool. It releases the baton only
  inside host primitives: a gateway call, a stream `next()`, a tool-answer wait.
- **Park states, complete:** idle; returned from `step`; parked in the gateway, a stream read or a tool answer. The
  host advances only when no agent holds the baton outside a park.
- **The order within a tick:** releases due at T (in the §6.2 key order), each run to its next park, then `step(T)`
  for each agent in `actor_id` order. Or the reverse, but one order, stated in §6.2 as part of the canonical order.
- **Liveness:** a `think` that blocks anywhere other than a host primitive (a Maxim lock, a pool, a socket) is caught
  by the wall ceiling as `thought_failed(timeout)` and named in a test-mode assertion.
- **Upstream:** answer `embeddable_agent_DRAFT.md` §9's open question in this direction. Tool calls return and resume,
  or go through a host callback that parks. State in §4.1 that `step` and `think` never run concurrently on one agent,
  and add an exit test (DD-S1's latch, against the stub host).

---

## SHOULD-FIX

### DD-S1. The barrier's guard can't fail as specified

`boundaries.md` §10 ("a slow agent at 20× must not see a later frame than at 1×"); `npcs_and_sem.md` §3.1 (the
dial-invisibility test: seeded wall delays through the gateway, a threaded host, a fake wall clock);
`embeddable_agent_DRAFT.md` OD-EA5

The seeded wall delays sit inside the gateway, which is the *parked* region. They test the hold and dilation, and the
`if dial > 10: skip hold` plant does go red there. But the race the barrier prevents is in the *unparked* region:
`think`'s Python after a release, racing `step(T+1)`. With a fake wall clock, the host's loop isn't paced at either
dial, so thread interleaving depends on the OS, not the dial. Remove the barrier, and the 1×/20× pair can still agree:
the think thread wins the GIL quickly and consistently, so no tick slips in. "A slow agent" is undefined. OD-EA5's
stub host is presumably synchronous, so its delays change nothing.

Fix: a deterministic latch test. After a release, the test double blocks on a test latch, which is *not* a host
primitive. The host exposes an instrumentation event "barrier wait entered". The test releases the latch only after
that event. Without the barrier the host never enters the wait. It steps T+1 while the latch is held, a step counter
sees it, and the test goes red with no sleep. Prove it by deleting the barrier wait. Keep the dial test for the hold.
Its abandon negative control needs a delay schedule with at least one delay between D/20 and D/1, stated, or abandon
can also agree across dials.

### DD-S2. The profile-hook tripwire can't see numpy's random functions, and its thread scope contradicts the upstream draft

`boundaries.md` §3 (the tripwire); `world_clock_release_DRAFT.md` §3.3

Measured with `sys.setprofile` on CPython 3.14.6 and numpy 2.5.4:
- `np.random.random()`, `np.random.rand()`, `np.random.normal()` and `Generator.normal()` emit **no** profile event.
  They are Cython functions, not `builtin_function_or_method`, so the hook can't see them. The denylist's "numpy's
  global `np.random`" entry can't be proven by a planted call; its plant stays green. (`SeedSequence()` and
  `default_rng()` with no entropy *are* caught, through their `urandom` call.)
- `datetime.datetime.now is datetime.datetime.now` is `False`: each access gives a new bound method. "Matching the
  function objects themselves" by identity misses it. It matches by `==` (measured `True`).
- Calls made from C to C (`functools.partial(time.time)()`, `map(time.time, …)`) emit the event for the outer C
  callable only.
- The hook slows Python-heavy code about **8.6×** (measured). Over the corpus, that is a slow-tier test.
- Thread scope: boundaries says `sys.setprofile` plus `threading.setprofile_all_threads` on ≥ 3.12. The upstream
  draft says the hook is per-thread and `setprofile_all_threads` "is not used". The repo's floor is Python 3.10.
  An all-threads hook also lands on the network lane, the thinking workers and pytest's own threads, which turns
  "a timeout on another thread must not trip" into a frame-allowlist problem.

Failure scenario: Maxim's prompt sampler calls `np.random.choice` from the global state. The tripwire is green, and
tier-2 reruns differ.

Fix:
- Install `sys.setprofile` at the entry of the simulation-lane and agent-lane thread functions in test mode. Drop
  `setprofile_all_threads`. Align both documents.
- Match by equality, or by `(__self__, __name__)`.
- For numpy's global state, add a **state-diff check**: digest `np.random.get_state()` before and after the corpus
  run (and Maxim's turn), and fail on any change. Prove it with a planted `np.random.random()`.
- Name C-to-C calls as a known blind spot, held by the AST scan.
- Mark the corpus run `slow`.

### DD-S3. The cache's occurrence index has no defined order, and a rerun's model key comes from the wrong machine

`npcs_and_sem.md` §4.8; `boundaries.md` §5.3, §6.3

- **Occurrences.** "Keyed by `(content hash, occurrence index)`", but the index is counted in an order nobody states.
  Two NPCs at one tick sending identical requests get index 0 and 1 in the order their think threads reach the
  gateway, which is a race. Adding an unrelated NPC that sends the same request earlier shifts every later index.
  Fix: key by the thought request id `(tick, actor, n)` plus the segment index. Keep the content hash as a
  verification field the gate recomputes, not as the key. Then there is no counting at all.
- **Model profile on rerun.** The canonical request includes the model id and weights digest. If the rerunning
  machine's gateway fills these in from *its* model, every lookup misses on a developer's machine (loudly, which is
  the right failure, but tier 2 is then unusable for bug reports). Fix: in rerun mode the gateway builds requests with
  the model profile from the rerun manifest, never from local weights. The manifest check refuses on a mismatched
  pymaxim or config, not on a mismatched local model.
- Temperature, strict misses and never-on-replay are right as written.

### DD-S4. The keyed per-NPC RNG costs about 6–10 µs per draw as specified, and `SeedSequence` keys collide across word widths

`npcs_and_sem.md` §3.4; `boundaries.md` §7.3

- **Stable under adding NPCs and under rejection sampling:** yes, as now specified (explicit `spawn_key`, a
  persisted `npc_key`, a fresh generator per `(npc, stream, tick, sensor)`).
- **Cost (measured):** building `Generator(Philox(SeedSequence(...)))` per draw is 9.7 µs. `Philox(key=, counter=)`
  is 6.0 µs. Resetting the counter on one reused bit generator is 2.2 µs, and gives identical values. At 20 NPCs × 10
  sensors × 200 ticks/s (20× at 0.1 s ticks), that is 40,000 draws per second, or about 0.24–0.39 s of CPU per wall
  second. Fix: derive `key` once per `(npc, stream)`. Per `(npc, stream, tick)`, set the counter and draw
  `random_raw(2·n_sensors)` once. Map each sensor's fixed slot (from the registry) through a fixed-consumption
  transform (Box–Muller on two raw words), so a vector draw has no rejection coupling between slots, and adding a
  sensor at a new slot changes no other. Add the cost as a B5 row.
- **Collision (measured):** `SeedSequence` splits each `spawn_key` integer into 32-bit words with no length marker.
  `spawn_key=(2**32,)` and `(0, 1)` give the same state, and so do `(1, 5, 7 + 9·2³²)` and `(1, 5 + 7·2³², 9)`. With
  "the first 8 bytes of SHA-256" stream keys next to small roster ints, an accidental collision is unlikely, but the
  scheme isn't sound. Fix: encode every key component as exactly two 32-bit words (or reduce every key to 32 bits),
  and test the encoding.

### DD-S5. The single ordering key is incomplete

`boundaries.md` §6.2; `npcs_and_sem.md` §9

- **`kind_rank`** is given only as "controls and joins before intents". There are no ranks for `speak`, `imagine`,
  `thought_cancelled`, `thought_failed`, `leave` or host commands. A player's `speak` at `apply_us` 0 that cancels a
  thought, and that thought's intent in the same tick: which applies first? Give the full rank table in §6.2, with a
  golden fixture.
- **The `apply_us` domain** isn't defined under the ceil rule. A time inside (k−1, k]·tick_us applies at tick k. Is
  `apply_us` its offset from (k−1)·tick_us, or from k·tick_us? Say "the offset within (apply_tick − 1, apply_tick]",
  and what an exact boundary stamp gets.
- **Players at `apply_us = 0`** precede every NPC event of the same tick. That is a deliberate asymmetry. State it in
  §6.1's asymmetry table.
- **Releases versus steps** within a tick (DD-B2) belong in this key's description.

### DD-S6. The latency table's numbers are wrong in two rows, and conversation uses the wrong D

`npcs_and_sem.md` §4.5

- Row 2, from my round-1 error (the correction above). For "2 per world minute each": f ≈ 0.28, latency bound about
  1.1×, throughput bound with v1's single 3 s model 1×, so **≤ 1×**. For "once per 5 world minutes each": about 6.8×.
- **Conversation.** The row "one NPC talking to the player, about 0.33×" uses D = 1 s, which is `D_onset` for
  choices and plans. A conversational reply's P1 is `D_gap`, mode about 200 ms (§4.2). The honest measure is a stall
  per reply, not a dial:
  - with typed input, `stall ≈ L_TTFT − D_gap`: about 2.8 s of frozen world per reply at L = 3 s, or 0.3–1.3 s at a
    TTFT of 0.5–1.5 s;
  - with planning during the other's turn, `stall ≈ max(0, L_TTFT − lead − D_gap)`.
- **The requested dial during conversation** is effectively 1×, because the player speaks in wall time. Say what the
  host requests (a forced 1×, or a cap) and whether a 20× request during conversation is refused.
- **Row 3** (hosted, 1×) and the formula are right.

### DD-S7. The streamed-speech bound was dropped, and lever 1 conflicts with `cancel_on`

`npcs_and_sem.md` §4.5, §4.3, §5.3

- v1's row "one NPC speaking at 20× needs about 70 tokens/s" is gone. Under dilate it binds harder than before. A word
  is stamped only once its following delimiter arrives (§5.3), so the host can't know whether the next word is due at
  tick T until it has it. The world waits on the stream word by word, and **dial ≤ model tokens/s ÷ (~3.3 tokens per
  world second per speaker)**. Restore it, with a B5 row for sustained tokens per second.
- **Lever 1** ("start the thought during the other speaker's turn") collides with `cancel_on: being spoken to`, which
  cancels exactly the thought lever 1 starts. Specify what the early thought reads: a prefix of the player's speech
  as of a world tick. Then define what continued speech does (cancel, or extend and re-request) and its rate limit.
- **Streamed player speech has no record form.** `speak` is one record with its text and `apply_us = 0`. Streamed
  voice needs per-chunk `speak` records, stamped at host arrival ticks, so the prefix an early thought read is in the
  log and the rerun is deterministic.

### DD-S8. Frames: copies per tick at 20×, stacked with the window copies, and a plain copy fails the `.base` proof test

`boundaries.md` §4.1 (the proof tests include "write through `.base`"), §4.2 (frames are copies published "after each
physics step and after each tick that applied an intent")

- **Cadence.** With active NPCs at 20×, nearly every tick applies an intent, so frames are published per tick, which
  is the case §4.2 itself prices at 13–16 GB/s. Measured: an 80 MB copy takes 5.7 ms (about 14 GB/s). With DD-B1's
  exit copy, each intent tick costs a window copy, an exit copy and a frame copy. That is about 17 ms against a 5 ms
  tick. Fix:
  - chunked copy-on-write for both windows and frames (a frame shares unchanged chunks with the previous one);
  - a frame for agents that is only the reductions the step already computes;
  - full-grid client snapshots at the client's wall cadence, not per world tick.
- **Seal.** A frame that is a `.copy()` with `writeable = False` can be re-enabled through `.base` (measured: re-enabled
  and wrote). Frames are shared by every agent and the encoder, so one consumer's write reaches the others. Back
  published chunks with immutable bytes (`np.frombuffer(buf.tobytes())`). Measured: neither the array nor its `.base`
  can be made writable, at the cost of 4.1 ms per 80 MB, which chunking also bounds.
- **Thread scope:** say which lanes may hold a frame. Retiring a frame is reference-counted, never "after N ticks".

### DD-S9. A thread per agent costs more than it buys under the GIL

`boundaries.md` §7.1; `npcs_and_sem.md` §6.3 (the 50 µs estimate)

Measured: an uncontended park-and-release round trip is 8.4 µs, so the 50 µs estimate is conservative. But that is
the *uncontended* case. When the simulation lane holds the GIL in Python, a woken agent thread waits up to
`sys.getswitchinterval()`, which is 5 ms. One contended hand-off per tick spends the whole 5 ms tick at 20×. Under the
GIL, agent threads give no parallelism, and the barrier serialises them anyway. Fix:
- step agents on the host thread, in canonical order (deterministic by construction);
- give a thread, or a coroutine, only to an in-flight `think` (DD-B2's baton);
- make the B5 row measure the contended hand-off, with the simulation lane busy.

Revisit this when free-threaded CPython and Maxim's thread safety are both on the table.

### DD-S10. The B5 rows the designs cite don't exist

`standards_backlog.md` B5 (unchanged: turn time, snapshot encode time and bytes); `boundaries.md` §4.2, §10;
`npcs_and_sem.md` §4.5, §6.3

The documents say "B5 row" about a dozen times, but B5 is unchanged. By CLAUDE.md's own rule, a document is not a
check. Add the rows to B5 (or as B5 sub-rows), each with its meter and the PR that owns it:
- window copy;
- frame publish and seal;
- the per-tick digest;
- the synchronous log write;
- the contended barrier hand-off;
- gateway overhead;
- the keyed RNG cost;
- the substrate step cost `c`;
- adapter push and strip;
- TTFT and complete-tool-call latency per model profile;
- sustained tokens per second;
- effective dial and stall per reply, by cause;
- the tripwire run time.

---

## NIT

- **DD-N1.** The per-tick digest's scope still isn't stated (DR-S9, partial). Measured, SHA-256 over 80 MB takes
  32 ms. Say: derived values per tick, full state per physics step or per N ticks (`boundaries.md` §6.2).
- **DD-N2.** `npc_key` is "from the roster". An NPC created at run time (born, summoned, a guest's companion) needs a
  deterministic key, such as `(parent key, creation seq)`, never the allocator (§3.4).
- **DD-N3.** "`dt_ticks` is a pure function of the actor's rate divisor and phase" conflicts with §2.1's scheduled
  crossing wake-ups, which add state-dependent steps. Say "a pure function of the schedule and the agent's own
  scheduled wake-ups, never of lag" (`boundaries.md` §7.1; `npcs_and_sem.md` §2.1).
- **DD-N4.** The upstream half of DR-S4 and DR-S12 is unplaced. §8.2 lists keyed substreams as "not yet placed", and
  neither draft has an exit test that adding an agent leaves another agent's draws identical. `make_agent_rng(seed,
  agent_id)` needs `agent_id` to be the stable key, which the draft should say.
- **DD-N5.** A cancelled stream's cache entry must hold every token the live run *read*. Because of word lookahead,
  that is one word past the last one released. A rerun then never misses at the cut. Also state round 1's DR-N4
  order (cancellation, then lookup) (§4.8).
- **DD-N6.** Round 1's DR-N2 (the µs bound beside the 2⁵³ pin), DR-N3 (`L_bio` measured from the sub-tick stamp or
  from the frame tick), and DR-N7 (NEP 19 as the reason for the numpy header) aren't folded or recorded as declined.
- **DD-N7.** §10's barrier row names the meters, but its test is DD-S1's. Point it at the latch test.

---

## Round-1 findings: did they close?

| Round 1 | Verdict |
|---|---|
| DR-B1 agent code races the tick | **partial.** The barrier is stated; the execution model beneath it contradicts itself (DD-B2), and its guard can't fail (DD-S1) |
| DR-B2 the host doesn't own the LLM call | **folded** (the gateway in §7.1, upstream §4.2). The blocking-`think` consequence is DD-B2 |
| DR-B3 the cache | **mostly folded.** Strict misses, never on replay, the canonical request, failures as responses. The occurrence order and the rerun model key remain (DD-S3) |
| DR-B4 the window leaks | **not closed.** The ownership window leaks a view of its own handle, and the proof test misses it (DD-B1) |
| DR-B5 the throughput bound | **folded in form.** Two rows wrong (one from my error), conversation uses the wrong D, the speech bound dropped (DD-S6, DD-S7) |
| DR-S1 Δt invariance; crossings | **folded** (scheduled crossings, µs floor, event lists, fixed `dt`); wording NIT DD-N3 |
| DR-S2 µs and the field | **folded** (`apply_us` int64, the ceil rule); domain ambiguity in DD-S5 |
| DR-S3 one key | **folded,** lanes §4.2 superseded; rank table incomplete (DD-S5) |
| DR-S4 Philox stability | **folded** for stability; cost and the collision are new (DD-S4) |
| DR-S5 module state | **folded** Overdrive-side (one real agent per process), with OD-EA6 upstream |
| DR-S6 dial test | **folded** for the hold; the barrier half is DD-S1 |
| DR-S7 tiers and the manifest | **folded** |
| DR-S8 speech in the log; chunking | **folded**; streamed player speech has no record (DD-S7) |
| DR-S9 budgets | **not closed:** no B5 rows exist (DD-S10); frame cost made worse by the window fix (DD-S8) |
| DR-S10 the agent path unsealed | **folded**, subject to DD-S2's thread-scope and numpy gaps |
| DR-S11 machine failures; policy as control | **folded** |
| DR-S12 upstream exit tests | **mostly folded** (fake wall clock in WC2/WC3, non-vacuity in WC1, wall-delay in EA5, isolation in EA6); EA5's synchronous stub can't fail (DD-S1); stream stability unplaced (DD-N4) |

## Direct answers

- **Does the barrier give tier 1/2 bit-identity at any dial?** Tier 1: yes, always. Tier 2: yes, *if* the per-agent
  baton, the complete park set and the within-tick order of releases versus steps are specified (DD-B2), and after
  tier A. Never under abandon. As written, the model either freezes the substrate during every thought or leaves the
  race open.
- **Can its test fail?** The dial test can fail for the hold (the plant works). It can't fail for the barrier: the
  seeded delays are in the parked region, and a fake clock removes the dial's effect on interleaving. Add the latch
  test (DD-S1).
- **The ownership window?** It doesn't prevent the escape (measured, DD-B1). It needs an exit copy or chunked
  copy-on-write, and a proof test that takes the view from the window's own handle.
- **`apply_us` and the key?** Integer µs and one key are right. The rank table, the `apply_us` domain and the
  release/step order are missing (DD-S5).
- **Keyed RNG?** Stable under adding NPCs and under rejection sampling as specified. About 6–10 µs per draw, and
  `SeedSequence` word-width collisions are real (DD-S4).
- **Cache?** Never read on replay: right. Strict misses: right. Temperature: handled. The occurrence index must
  become the request id, and a rerun's model key must come from the manifest (DD-S3).
- **D/L numbers?** Row 2 is wrong (my round-1 error, copied). Conversation should use `D_gap`, which means about
  2.8 s of frozen world per typed reply at L = 3 s. The honest dial in conversation is ≤ 1× by construction, with a
  stall per reply of `max(0, TTFT − lead − D_gap)`. Lead exists only with streamed voice, and only once its record
  form and the `cancel_on` conflict are settled (DD-S6, DD-S7).
- **Frames at 0.1 m?** 64–80 MB per tile is right. One copy is 5.7 ms. "On change" is about every tick at 20× with
  active NPCs, and the window fix adds copies. Chunked copy-on-write and bytes-backed chunks are needed (DD-S8).
- **Tripwire?** Per-thread `setprofile` is the right shape. It is blind to numpy's Cython random functions, misses
  `datetime.now` by identity, contradicts the upstream draft on thread scope, and costs about 8.6× (DD-S2).
- **B5 rows?** Cited, not present (DD-S10).
