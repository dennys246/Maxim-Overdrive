# Delta round 2: `sem_stimuli.md` v3, Concurrency and lanes

**Reader:** Concurrency and lanes (the delta-1 reader of this lens). **Read at:** Overdrive `77e24bb`: v3 whole, my
delta-1 report, `delta1/fold.md`, `delta1/determinism_performance.md`, `npcs_and_sem.md` §9, `src/simcore/core/intents.py`.
Maxim by `git show` / `git grep` at local `origin/main` `043eab8f`, not fetched. Scratch:
`_durable/sem_review_delta2/scratch_concurrency/` (`overlap_gate_toy.py`, `overlap_gate_toy2.py`, `thread_check_cost.py`).

**Two corrections of my own delta-1 advice come first.**
1. **F3's fix put "since this NPC's last delivered frame" on the wrong frame.** I didn't say which frame; v3 put it on
   `BodyFrame`, which is built and digested every tick and never delivered. That makes a per-tick, host-only frame
   depend on delivery history, which contradicts T9. New finding C1.
2. **F6's fix asked for "the thread set at every park equals the post-build set" without a baseline or a comparison
   rule.** At Maxim `origin/main` the ConceptExtractor worker starts at session open and is replaced, as a new
   `Thread` object, at each later session. v3 copied my wording, so the check as written kills healthy NPCs on
   Maxim's normal lifecycle. New finding C2.

## Status

| Id | Status | Reason (read from v3) |
|---|---|---|
| S9 | deferred | §4.1 now says which thread does what (step 4 in the simulation lane; a host pump encodes, sends, receives, stamps), scatter-gather, and that push plus body step sit inside the ceiling. The per-tick critical path and the push's share of the ceiling can't be numbers until the channel exists and M4 prices the body step. **Reason:** nothing to measure yet. **Trigger:** `phase1/agents`' B5 row. **Condition:** that row is per tick, not per world second: steps 1–4, then max(physics, slowest park) on physics ticks, then merge, with the push's share of the ceiling stated |
| F1 | open | §4.1's gate now runs live with stub workers, two delay schedules, overlap on and off, then replay, with a planted merge during step 6. That gate **can** fail, but only if the stub stream contains an intent kind that step 6 reads, or the world digest covers state the plant writes after step 6. v3 names neither, and the intents §4.5 names (posture, gaze, breathing) don't qualify. Missing: one sentence (below, "The lane-overlap dispute") |
| F2 | deferred | Accepted with an amended trigger. Scatter-gather is stated (§4.1); §6.6's levers are superseded by name (§6.1); §8 promises the B5 row at 1× and the dial's maximum, the highest dial sustainable, and hung kills per 1,000 parks. **Reason:** the body step is unmeasured. **Trigger:** the stub round trip at 1× and 20× is measurable without Maxim, so it lands with `phase1/agents`' channel; the body step lands with M4's answer. **Condition:** T16 may not flip (delivery moving to every tick, §4.6) until the row exists with both parts, because D14 is what keeps (c)'s barrier cost off the table today. v3 doesn't state that condition; add it to §4.6 |
| F3 | fixed | §4.2 uses "since this NPC's last delivered frame", valid at any divisor; §11.3 names (d) as the fallback and says T9 and T16 decide. The full step per tick can't be priced before M4, which §11.3 says. My fix placed the rule on an unnamed frame, and v3 put it on `BodyFrame`; that is C1, not a reopening |
| F4 | fixed | §4.2: `(tick, offset_us)` stamps, delivered in the first frame built after the event, sort key `(tick, offset_us, kind rank, local_id)`, latency "zero for intent-made, up to six ticks for physics-made". Six is right: physics at T covers (T−5, T] and the event is first built into T+1's frame |
| F5 | fixed | §4.3: partial send is normal (the 8,192-of-20,000 measurement), per-channel outbox pumped inside the ceiling, only ceiling expiry is `hung`, only `BrokenPipeError`, `ConnectionResetError` or EOF is `crashed`, the event budget sits below the socket buffer, and both tests (one byte at a time lives; never reads lets the world advance). The receive direction is not stated: C4 |
| F6 | fixed | §4.4 checks the thread set at every park against post-build, cites OD-EA7, and plants a thread at the third step, as I asked. My ask was wrong in a way that matters: C2 |
| N-a | fixed | §4.1: merge is step 7, after the join; the ceiling is judged on the pump's stamps during physics |
| N-b | fixed | §8: "a counter gate reads parks from the log" |
| N-c | fixed | §4.5: a restart's first frame carries no events; the dropped count is logged |

Deferrals from delta 1 still honoured: S6 (d) is named in §11.3; N5 (pause) still waits for `phase1/agents`' design.

**Counts:** 7 fixed, 2 deferred, 1 open, 0 rejected.

## The lane-overlap dispute, settled

**The question.** In delta 1, I said the overlap gate couldn't fail (F1), and the Determinism and performance reader
wrote "the on/off replay gate can fail: a leak changes world state and the T+1 frames"
(`delta1/determinism_performance.md:235`).

**For v2, F1 stands.** v2's gate replayed a log, and replay runs no agents (§5, `boundaries.md` §6.2). Step 5 is
empty in replay, so overlap on and off run the same code, and a leak from step 5 has no source. DP's note describes
what a leak would do, not a gate that could see one.

**For v3, the gate can fail, under one condition v3 doesn't state.** I built a toy of §4.1's tick
(`overlap_gate_toy.py`, deterministic; physics is a diffusion sweep over 64 cells on every fifth tick). A stub
emits one intent every seventh tick, and the merge logs it for T+1. The plant applies the intent's effect during
step 6: at a schedule-drawn sweep index with overlap on, at index 0 with it off. Replay applies the logged record at
step 1 of T+1. I ran two intent kinds against two digest points:

| Stub intent | Digest point | Plant: on/off and schedules agree | Plant: live equals replay | Verdict |
|---|---|---|---|---|
| `ignite` (writes a cell) | frames only | no | no | **red** |
| `ignite` | end of tick | no | no | **red** |
| posture (body store only) | frames only | yes | **yes** | **green: the gate can't fail** |
| posture | end of tick | yes | no | red, via replay only |

All four clean runs are green. Two things follow.
- **The replay leg is what does the work, and it fails only on state that something reads,** or a digest takes,
  between the plant's write in step 6 and step 1 of T+1. Physics doesn't read posture, so a posture intent applied
  early is invisible at the next frame.
- **The on/off leg catches only a kind that physics reads,** and then only when the delay schedules put the arrival
  inside the physics step. If every stub answers before physics reads the affected cells, "on" behaves like "off"
  and the leg is green.

**What v3 must add to §4.1 (F1's remainder).** The stub stream includes at least one cell-writing action
(`Ignite`, `Strike` or `Extinguish`, which exist in `core/intents.py` today) aimed at cells the physics step reads.
The two delay schedules are drawn so arrivals land before, during and after the physics step's wall span. The gate
is shown red on the planted merge with that kind. A posture-only or breath-only stub stream doesn't count as the
plant. **Verified** in the toy only. It models the order of operations, not the threads, the pump or the real heat
law.

## New findings in v3

### SHOULD-FIX

#### C1. `BodyFrame.events` depends on delivery history, which breaks T9 and the per-tick digest
**`sem_stimuli.md::§4.2` (`BodyFrame.events: … since this NPC's last delivered frame, capped`; "never leaves the
host"), `§4.6` (delivery at the cognition rate; "tissue and frames still run every tick"), `§6.3 T9` ("divisors
1–50: frames byte-identical"), `§5` (lanes digest the frames).**

`BodyFrame` is built and digested every tick for every body, whether or not anything is delivered (§4.5's table:
inert and failed bodies are "built and digested, not sent"). Its `events` field is defined by when the last
`BoundFrame` went out, and under D14 that is the cognition divisor. So at divisor 10 the field holds up to ten ticks
of events, and at divisor 1 it holds one. When it is coalesced under the cap, even its counts and peaks differ.
- **T9 goes red** the day the first event producer lands, though nothing is wrong. Or someone narrows T9 to
  `value`, which is the loosened-test path CLAUDE.md forbids.
- **The stimulus digest stops being a function of world state alone.** It becomes a function of world state plus
  cadence. Replay still reproduces it, because the divisor and `agent_ready` are logged. But §0's claim that the
  frames are what the world computes, whatever the agent's cadence (§7.1), stops being true for events.
- **Restart (N-c) and failure** both change the delivery history, so they change the digest of a host-only frame.

v1 has no producer, and a gate holds `events` empty (§4.2), so nothing is red today. But `BodyFrame` is frozen now.

**Fix:** split the two meanings across the two frames.
- `BodyFrame.events` holds the events first available at this tick: stamped `(tick, offset_us)`, divisor-independent,
  and digested in an events lane.
- `BoundFrame.events` holds the concatenation of the `BodyFrame` events since this NPC's last delivered
  `BoundFrame`, capped and coalesced at delivery. The coalescing counters stay in the save, as §5 says.
- T9 then compares `BodyFrame`s byte for byte across divisors, and `BoundFrame` event content as a multiset over a
  common window before coalescing.

**Verified** by reading only; there is no code to run.

#### C2. The per-park thread check has no baseline point, and Maxim's session lifecycle changes the thread set
**`sem_stimuli.md::§4.4` ("At every park the thread set must equal the post-build set … as OD-EA7 requires; planted
red at the third step").**

At `origin/main`:
- `MemoryHub._restore_on_open` calls `start_background_workers()` at session open (`memory_hub.py:707-716`).
  That method is documented as "constructor-deferred workers after transactional assembly" (`:907-911`).
- `on_session_end` shuts the worker down, and the next session revives it as a **new `threading.Thread`** with the
  same name (`concept_extractor.py:542-560`).
- `agent_factory.py:535` opens the session.

v3 doesn't say whether "post-build" is before or after the session opens, how the sets compare, or what the failure
reason is.
- **If the baseline precedes session open,** the first park sees `concept-extractor-worker` and fails every NPC.
- **If an NPC lives across two Maxim sessions** (a save-and-resume, or any session boundary the embedded build
  runs), the identity set differs at the next park, and a healthy NPC dies. `thread_check_cost.py` shows a
  same-name restart breaks equality by identity (`False`) but keeps it by name (`True`).
- **OD-EA7 fails today by Maxim's own account** (`maxim_response_1/response.md:75`), and v3 doesn't mention it. So
  the check is red on real pymaxim until Maxim lands that item, yet nothing marks it as a strict-red gate.

The check is cheap: 1.3 µs per park with 12 threads, measured. Cost isn't the problem.

**Fix:**
- Take the baseline at `agent_ready`, after the Maxim session opens.
- Compare the multiset of thread **names**, so a Maxim-style same-name restart passes and a new thread doesn't.
- Run session close and open only as worker lifecycle steps outside a park, each re-baselining and logging the
  delta.
- Name the failure `agent_failed(protocol)`.
- State that OD-EA7 is unmet on today's pymaxim. The real-Maxim build test is `xfail(strict=True)` until it lands,
  and the stub-worker test carries the plant.

The value check stays the real one-writer guard: a background thread that writes a bound sensor is caught by value
whatever its name. **Verified:** the Maxim lines (by `git show` at `origin/main`) and the identity-versus-name
behaviour (script). **Not verified:** whether the embedded host-driven build opens a session inside build or at
first step. That depends on OD-A10's build, which doesn't exist yet. Say which assumption v3 makes.

### NIT

- **C3. `§4.1`, the overlap premise cites a number §9 doesn't state.** "`npcs_and_sem.md` §9's lane minimum
  refuses equality". §9 says only that `L_bio` "shorter than the lane's minimum is refused" (`npcs_and_sem.md:1053`),
  with no value. Under §9's apply rule, `apply_tick = ceil((observed_tick·tick_us + L_us)/tick_us)`,
  `apply_tick > observed_tick` holds if and only if `L_us ≥ 1` (arithmetic, checked). Say the minimum is at least
  1 µs, or, more honestly, one tick of hand-off, and plant a configuration with `L_us = 0` refused. Executor X5
  overlaps this; the number is what's missing.
- **C4. `§4.3`, partial messages in the other direction.** The outbox and the tests cover host to worker. Say also
  that the pump merges a `step_output` only when it arrives whole, and that a partial one at ceiling expiry is
  discarded with the `hung` record. Plant a worker that sends half a `step_output` and stalls: the agent is `hung`,
  nothing is merged, and the record stream matches replay.
- **C5. `§4.1`, the pump's lane.** If the pump is a thread in the host process, it shares the GIL with the
  simulation lane. Its Python work slows physics, and its stamps can lag by up to the switch interval (0.005 s
  measured, the default). Neither changes values, since stamps only decide `hung`, which is logged. But the B5 row
  should carry the pump's cost, and §4.1 should say whether the pump is a thread or a process. Also say the pump
  hands off only through a queue that step 7 drains, so the ownership scan can hold it to touching no world state.
- **C6. `§8`, the barrier paragraph.** "10 NPCs make 2,000 parks per wall second" at 20× is the D5 (c) figure.
  Under D14's interim it is 2,000 divided by the cognition divisor. Say that, so a reader doesn't price today's
  build at (c)'s cost, and doesn't miss that the cost arrives when T16 flips (F2's condition).

## Checked, no finding

- **Back-pressure under D14.** A ready agent at divisor 50 accumulates up to 50 ticks of events. The per-frame cap
  and the `(kind, site)` coalescing bound the bytes. Inert and failed agents accumulate nothing (§4.3). That's
  bounded.
- **Hung and crash decisions.** They are wall-time decisions recorded as logged `agent_failed` records in step 7,
  so replay reproduces membership exactly (§4.5, §5).
- **Step 4 before step 5.** The frames are built in the simulation lane before any send, so a worker can't observe
  a half-built frame. `BodyFrame` is deep-frozen with a base chain ending in `bytes` (§4.2).

## Counts

Status: 7 fixed, 2 deferred (S9; F2 with an amended trigger and condition), 1 open (F1: name a cell-writing stub
intent and straddling delays), 0 rejected. New: 0 BLOCKER, 2 SHOULD-FIX (C1, C2), 4 NIT (C3–C6). C1 and C2 both
come from my own delta-1 fixes, as v3 adopted them.
