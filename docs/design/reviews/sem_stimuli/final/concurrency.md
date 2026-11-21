# Final round: `sem_stimuli.md` v4, Concurrency and lanes

**Reader:** Concurrency and lanes (the delta-1 and delta-2 reader of this lens). **Read:** `git diff 0918685..aa6bd1b`
(v4 §4, §5, §6.2–§6.3, §8, §10, §11; `docs/plans/checklists.md`'s new 5a, 5b, agents and laws items; `delta2/fold.md`),
against my `delta2/concurrency.md`. Maxim by `git show`/`git grep` at `origin/main` `043eab8f`, not fetched. Scratch:
`_durable/sem_review_final/scratch_concurrency/` (`thread_names.py`, `coalesce_divisor.py`).

**A correction of my own delta-2 advice comes first.** My C2 fix (a baseline at `agent_ready`, compared by name
multiset) is what v4 adopted. I checked it against Maxim's session lifecycle only, not against the LLM call path. At
`origin/main`, `llm_worker.py:665` builds a `ThreadPoolExecutor(max_workers=1, thread_name_prefix="LLMCall")` at
start, and the executor creates its thread lazily, on the first submit, which happens inside the first cognition
step. So on real pymaxim, every NPC's name multiset gains `LLMCall_0` at its first LLM call. With v4's rule, that NPC
then fails as `agent_failed(protocol)` at its next park. v4 states that the real-Maxim test is strict red. It doesn't
state the consequence on the shipped path. That is new finding R1.

## Status

| Id | Status | Reason (read from the tree at `aa6bd1b`) |
|---|---|---|
| S9 | deferred | Unchanged and still honoured. The checklist's agents item carries the condition: the B5 row "counted per tick, with the pump's cost and GIL share". **Reason:** there is no channel and no M4 answer to measure. **Trigger:** `phase1/agents`' B5 row |
| F1 | fixed | §4.1: the gate is live, with stub replies released at host hooks (the checklist names three: before step 6, a test-only hook inside it, after the join) in two fixed orders, overlap on and off, then replay with `maxim` blocked. The stub stream includes a cell-writing intent, and the replay leg must go red on the planted early merge. The hook inside step 6 is what puts the arrival inside physics, which my "straddling delays" asked for without wall timing. This is better than what I proposed |
| F2 | fixed | §4.6: T16a "flips only once the barrier's B5 row exists (concurrency F2)". The checklist adds 1× and the dial's maximum, counted per tick, with the pump's cost. The body step is inside a park, so a per-tick park count prices it |
| F3–F6, N-a–N-c | fixed (held) | Fixed in delta 2; the cut kept their text (§4.1–§4.5, §8). F6's thread rule was replaced by C2's, see R1 |
| C1 | fixed | §4.2: `BodyFrame.events` holds "first available at this tick only", and `BoundFrame.events` concatenates the events since the last delivery. §5 adds an events lane per NPC over `BodyFrame.events`. §4.5 drops the previous life's events from the first delivery after a restart, not from the `BodyFrame`, so the digest is free of delivery history. T9 compares `BodyFrame`s byte for byte. One part of my fix was dropped ("before coalescing"); that is R2, a new defect in the diff, not a reopening |
| C2 | fixed, as asked | §4.4: baseline at `agent_ready` after the session opens, name multiset, session close and open outside a park, `agent_failed(protocol)`, OD-EA7 named as unmet and its test strict red; Q7 records the session-open assumption. The rule as I specified it has a defect on the LLM path (R1). Re-baselining isn't logged (R4) |
| C3 | fixed | §4.1 sets `L_us ≥ 1` and refuses 0, planted (checklist: X5, C3). The false citation of §9 is gone |
| C4 | fixed | §4.3: inbound `step_output` merges only when whole, and a partial one at expiry is discarded with the `hung` record. The checklist plants a half-sent `step_output` that must match replay |
| C5 | fixed | §4.1: the pump is a thread that hands off only through a queue step 7 drains; its cost and GIL share go in the B5 row (checklist) |
| C6 | fixed | §8's "2,000 parks" sentence is gone. The checklist cost table says that under D14 the barrier's parks divide by the cognition divisor |

**Deferrals proposed this round for my lens:** none. S9 stays deferred.

**Counts:** 9 fixed (F1, F2, C1–C6, with F3–F6 and N-a–N-c held), 1 deferred (S9), 0 open, 0 rejected.

## New findings in the diff

### SHOULD-FIX

#### R1. The thread check kills every real-pymaxim NPC at its first LLM step, and v4 doesn't say so
**`sem_stimuli.md::§4.4` ("Threads: the baseline is taken at `agent_ready` … at every park the multiset of thread
names must equal it … OD-EA7 is unmet on today's pymaxim, so the real-Maxim test is strict red until it lands");
checklist, agents: "the thread baseline at `agent_ready` by name multiset … planted with a new thread at the third
park".**

**Scenario.**
1. A real NPC reaches `agent_ready`, and its baseline holds no `LLMCall_*` thread.
2. Its first cognition step calls the LLM through `LLMWorker._call_llm_with_timeout`, and the executor spawns
   `LLMCall_0`.
3. At the next park the multisets differ, and the host records `agent_failed(protocol)`.
4. Every real NPC is inert after one thought.

On a timeout, `llm_worker.py:820-824` replaces the executor while the wedged orphan keeps its name, so the multiset
holds two `LLMCall_0`. That one is a real leak, and the check is right to catch it.

**Verified** with `thread_names.py`, a model of the executor pattern:
- equal after the first call: `False`, new `{'LLMCall_0': 1}`;
- after a timeout replacement: `{'LLMCall_0': 2}`.

**Not verified:** that the embedded build's step goes through `LLMWorker` (`agent_loop.py:956` takes one; OD-A10's
build doesn't exist yet).

**Why this is a defect and not just "strict red":** v4 presents OD-EA7 as a test-status fact. On the shipped path, it
means `phase1/agents` can't run one real Maxim NPC past its first LLM call until Maxim lands `1263.thread-guard`. The
only alternative is to weaken the check, and that would be a band-aid. The roadmap and §11.3 don't list it as a risk
or a dependency. The stub plant can't see it, because a stub makes no LLM call.

**Fix (unverified, design):**
- §11.3 states that real NPCs can't run until OD-EA7 lands.
- The roadmap lists OD-EA7 as a prerequisite of the agent line's first real-Maxim scene.
- The checklist adds a real-pymaxim test that makes one LLM step and then parks, `xfail(strict=True)` on OD-EA7, so
  the day Maxim fixes this the gate flips.

The checklist doesn't hold this today.

**Checked, no finding:** `router.py:1026-1027` starts a transient per-call daemon thread that signals `done` in
`finally` and then exits. I suspected the park could see it still alive. In 2,000 trials it was never listed after
`done.wait()` returned (0/2000). That doesn't prove the race can't happen, but I have no evidence for one.

#### R2. Coalescing depends on the divisor, so T9's `BoundFrame` multiset goes red on correct behaviour, and "nothing is lost" is false
**`sem_stimuli.md::§4.2` ("a `BoundFrame` is assembled at delivery, concatenating the undelivered ticks' events and
receipts under the byte budget, so nothing is lost at any divisor"), `§4.3` ("capped per delivered frame … overflow
coalesces by `(kind, site)` into count and peak"), `§6.3 T9` ("`BoundFrame` event and receipt content equal as a
multiset over a common window").**

The budget applies per delivered frame. A frame at divisor d carries d ticks of events. So whether a burst coalesces
depends on d: the same event stream is delivered verbatim at divisor 1 and as one count-and-peak record at divisor 50.

**Scenario.** Sound lands, and an NPC near a steady noise source gets one event per tick.
- At divisor 10 the frame fits the budget; at divisor 11 it overflows and coalesces.
- T9's multiset comparison goes red though nothing is wrong. Or someone narrows T9 to "where nothing coalesced",
  which is the loosened-test path.
- The contract sentence "nothing is lost at any divisor" is false: individual events and their `(tick, offset_us)`
  stamps are lost to coalescing, and they are lost more often at higher divisors.

**Verified** with `coalesce_divisor.py` (one 24-byte event per tick, a 256-byte budget): the multisets are equal to
divisor 1's at d = 5 and d = 10, and differ at d = 11 and d = 50.

v1 has no event producer, and a gate holds `events` empty, so nothing is red today. But the sentence is contract, and
T9 is frozen against it.

A related ambiguity: §4.2 puts *receipts* under the byte budget, but §4.3 defines coalescing only by `(kind, site)`,
which receipts don't have. If receipts count toward the budget, an overflow at a high divisor has no defined fate for
a `(pid, kind)`.

**Fix (unverified, design):**
- §4.2 says that event fidelity under the budget depends on the cognition divisor, and drops "nothing is lost".
- T9 compares `BoundFrame` content before coalescing (as delta-2 C1 asked), or compares the coalesced
  `(kind, site, count, peak)` per common window.
- Receipts sit outside the event budget, with their own bound (at most one per logged intent).

The checklist doesn't hold this.

### NIT

- **R3. `§4.4`, the body step under D14.** "On other ticks the host steps it" describes D5 (c). Under D14 (§4.6),
  push and body step run at the cognition rate, so there are no other-tick body steps. Someone who implements §4.4 as
  written under D14 parks every worker every tick, which undoes the saving C6's division describes. The fix is to say
  "under (c)" in §4.4. The checklist's "one `evaluate_failures` per agent step on a cognition tick" agrees with D14,
  so only the design text is ambiguous.
- **R4. `§4.4`, re-baselining at session boundaries is silent.** A session open that leaks one thread per cycle is
  absorbed into each new baseline, and nothing records it. My C2 fix asked for "each re-baselining and logging the
  delta"; v4 dropped the logging. The fix is a host-side record of the multiset delta at each re-baseline, plus a
  bound: the delta must be empty, or the threads Maxim's session lifecycle restarts by name. The checklist doesn't
  hold this.

## Checked, no finding

- **The tick order.** Frames are built in step 4 in the simulation lane, before any send. The merge is step 7, after
  the join. The pump stamps but doesn't decide, and `hung` and `crashed` are logged records, so membership replays
  exactly (§4.1, §4.3, §4.5).
- **History independence of events (C1's intent).** `BodyFrame` and its events lane are per tick. The previous life's
  receipts and events are dropped only at delivery after a restart. Inert and failed NPCs accumulate nothing (§4.3),
  so back-pressure stays bounded.
- **The overlap gate's live leg can fail.** A cell-writing stub intent, released at the hook inside step 6 and
  applied on arrival by the plant, changes cells that the physics step and step 8 read, while replay applies it at
  step 1 of T+1. This is red by construction, as my delta-2 toy showed. Every cognition divisor eventually lands on a
  physics tick (at the least common multiple), so the gate needs no extra condition on the divisor.
- **T16a (verification) and its flip condition** are stated in both §4.6 and the checklist.
- **D5 (c) at the cognition rate:** §6.1 supersedes §6.6's barrier levers by name ("D14's interim restores 'due
  agents only'").

**Counts:** status 9 fixed, 1 deferred, 0 open, 0 rejected. New: 0 BLOCKER, 2 SHOULD-FIX (R1, R2), 2 NIT (R3, R4).
R1 comes from my own delta-2 fix.
