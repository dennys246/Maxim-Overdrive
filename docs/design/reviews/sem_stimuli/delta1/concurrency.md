# Delta round 1: `sem_stimuli.md` v2, Concurrency and lanes

**Reader:** Concurrency and lanes (round 1's reader of this lens). **Read at:** Overdrive `3e97ac9`: v2 whole, my
round-1 report, `fold.md`, `npcs_and_sem.md` §6.6, `realtime_lanes_coop.md` §2.1 and §4.1, `tile_and_client.md`
§2.3, the DP review's delivery table, and `embeddable_agent_DRAFT.md` §5–§7. Maxim by `git show` / `git grep` at
local `origin/main` `043eab8f`, not fetched.

**Two corrections of my own round-1 folds come first.**
1. **B1's test can't fail as I proposed it.** I asked for "the same log with overlap on and off gives the same world
   digest and stimulus digest". v2 §4.1 adopted it word for word. But replay runs no agents (v2 §5,
   `boundaries.md` §6.2), so in a replay step 5 is empty, and "overlap on" overlaps physics with nothing. The race
   the gate exists to catch can't occur in it. New finding F1.
2. **S2's fold mapped "a short write" to `agent_failed(crashed)`.** On a non-blocking socket, which the same fold
   requires, a send that takes fewer bytes than offered is the normal "buffer full" result, not a crash. v2 §4.3
   copied my wording. New finding F5.

## Status of round-1 findings

| Id | Status | Reason (read from v2) |
|---|---|---|
| B1 | fixed | §4.1 states the order as an insertion into D10 (records, move bodies, tissue, frames, agents, physics, outputs), matching `realtime_lanes_coop.md` §2.1 and tile §2.3; overlap of steps 5 and 6 is allowed and justified by `observed_tick + L`. The gate is wrong: F1 |
| B2 | fixed | §4.3: per-tick cap within a body-derived byte budget, coalescing by `(kind, site)` into count and peak, the host's pre-send check, nothing accumulates for inert, absent or failed NPCs, and both gates. Physics events don't fit "this tick only": F3 |
| S1 | fixed | §3.2: reduction in the core, only bound values cross; §8 counts bytes and frames as work counters with a delivery B5 row; the "few hundred bytes" claim is gone |
| S2 | fixed | §4.3: non-blocking, multiplexed, inside the per-park ceiling; `BrokenPipeError`, `ConnectionResetError` → `agent_failed(crashed)`; both gates. Except the short-write mapping: F5 |
| S3 | fixed | §4.4: a post-build check of `threading.enumerate()` and bound sensors' owners, planted red, as asked. Checking once is too weak against Maxim's real threads: F6 |
| S4 | fixed | §8 allowed item (3): fork-join inside `Simulation.step`, published read-only arrays only, joined before any window opens, a task's exception is a simulation-lane exception, serial until T11's batch plant |
| S5 | fixed | §4.2: `__post_init__` refuses writable or non-owning arrays, as `CellFrame` does, plus a constructor-site scan. The planted scratch-buffer view isn't named as a test; name it when `frame.py` lands |
| S6 | deferred | Owner ruled D5 (c), so (a) and (b) are moot. I accept (d), the wake predicate, as **deferred, not rejected**: the author's own trigger ("M16 fails and (c) is unaffordable") is a deferral's trigger. Condition: §11.3's M16 risk names (d) as the fallback candidate, or the deferral is invisible where it fires (F3). The cost of (c) at §6.6's operating point is still missing; carried to F2 |
| S7 | fixed | §4.5's lifecycle table: join, not ready / build refused (`agent_failed(build)`), failed, restart, leave, each with world side, frames and record; readiness is a logged `agent_ready`; membership from records; inert bodies built and digested, not sent, so delivery never changes the digest; crash injection per row |
| S8 | fixed | §4.5: breathing is a logged intent through `StepOutput` applied next tick; the default schedule for inert agents; replay with `maxim` blocked reproduces the dose |
| S9 | open | §8 adds work counters (parks, frames, bytes per tick) and B5 rows for delivery, the worker push and event-buffer depth; §2.1 has the worker count clamps. Still missing: **which thread encodes, digests and pumps the sockets** (it matters once step 6 overlaps step 5, F4); the **per-tick critical path** (§8's table is per world second, but physics ticks are lumpy and the barrier is a max, not a sum); and the **worker push's share of the per-park ceiling** |
| N1 | fixed | §8: refresh "from world state, never by NPC index"; staggering by index is gone |
| N2 | fixed | moot: the reuse cache was dropped (DP-N1) |
| N3 | fixed | §5: deltas ruled out for these frames; the digest covers canonical values, not codec bytes |
| N4 | fixed | §4.2: the worker checks `npc_key` against its channel's actor and that `tick` rises |
| N5 | deferred | Accepted. Reason: pause belongs to the barrier and the per-park ceiling, both `phase1/agents`' design. Trigger: that design, which must say that a pause stops ticks, tissue and frames, and stops the per-park ceiling from killing a parked worker |

**Counts:** 13 fixed, 2 deferred, 1 open, 0 rejected.

## New findings in v2

### BLOCKER

#### F1. The overlap gate replays a log, and replay runs no agents, so it can't fail
**`sem_stimuli.md::§4.1` ("A gate replays one log with that overlap on and off and requires identical digests");
`§5` ("Replay reproduces the world, never the agents").**

What the overlap risks is live-only: the host decoding a `step_output` mid-physics and applying something into
state that step 6 reads; the per-park ceiling firing at a different point; a `settle` or breath record landing at T
instead of T+1. In replay, no worker exists, step 5 does nothing, and overlap on and off run the same code. The
gate is green by construction. The charter makes that a BLOCKER ("a test that cannot fail"). The flaw was in my
round-1 fold.

**Scenario:** a later commit lets the merge of tick T's `step_output` run as replies arrive, so a posture intent
reaches the body store during step 6 at T instead of at step 1 of T+1. Physics at T then debits the flame's share
from a pose that replay, which applies the logged posture at T+1, never sees. Live and replay diverge, and the
gate stays green.

**Fix:** run the gate **live** with spawned stub workers behind the real channel (as `npcs_and_sem.md` §6.6 already
requires of [now] tests): deterministic stub agents that emit intents and breath records, two seeded wall-delay
schedules, overlap on and off. Require the identical world digest, stimulus digest and logged record stream, then
replay that log with `maxim` blocked and require the same digests again. Show it red with a planted merge that
applies a `step_output` during step 6.

### SHOULD-FIX

#### F2. D5 (c) puts every NPC on the barrier every tick, and its cost is stated only at 1× near a fire
**`sem_stimuli.md::§8` (the delivery row, "~15–30 ms" per world second at 10 NPCs), `§10 D5`; against
`npcs_and_sem.md::§6.6` ("Its cost").**

§6.6 prices the barrier at 20 NPCs × 200 ticks per wall second × 50–200 µs per round trip as 0.2–0.8 s per wall
second, "enough to make 20× unreachable". It named three levers: only due agents get a round trip, frames go as
deltas, idle agents step coarser. v2 removes all three for bodies: (c) makes every body due every tick, §5 rules
out deltas, and a coarse idle divisor now slows only cognition. The DP review derived §8's delivery row from a
6 KB full frame, summed host-serially, per world second at 1×. It omits:
- **the Maxim body step in the worker,** which is what each park actually waits on and is unmeasured, since M16
  doesn't exist yet;
- **the dial:** away from a fire, physics is cheap and the dial matters. 10 NPCs at 20× is 2,000 parks per wall
  second, 0.1–0.4 s of round trip alone by §6.6's figure, before any body step;
- **the shape of the wait:** whether the host scatters all frames and then gathers (the barrier costs the slowest
  worker) or sends and waits in turn (it costs the sum). §8's sum implies the second, and v2 doesn't say which;
- **the exposure to kills:** each park is a chance at the wall-time `hung` kill. Under (c) a divisor-10 agent
  parks ten times as often, so on a starved host, kills rise and tier-3 runs come sooner.

**Scenario:** the owner sets 20× in a quiet street with 10 NPCs. The world can't keep the dial, which the design
never predicted, and a loaded laptop kills an NPC as `hung` on an ordinary tick.

**Fix:** state scatter-gather. Add the B5 row per wall second at 1× and at the dial's maximum, with the worker body
step measured once M16 has an answer, and state the highest dial (c) sustains at 10 NPCs. Count hung kills per
1,000 parks as a meter. This is the cost S6 asked to sit beside (c).

#### F3. The frozen frame assumes M16, and the fallback is undesigned on the delivery side
**`sem_stimuli.md::§4.2` (`events: … this tick only`), `§0` (frozen: "the `BodyFrame` and the wire's `BoundFrame`;
the tick placement"), `§11.3` ("D5 (c) needs M16"); `embeddable_agent_DRAFT.md::§7` (M16: "If not, every tick is a
full step, or contacts between steps go unfelt").**

M16 is an open question to Maxim. v2 freezes now a wire form that is right only if the answer is yes. If it is no:
- **"Every tick is a full step"** is the whole embedded step for every NPC on every tick. That deletes the "only
  cognition is slow" premise, and its barrier cost is unpriced (F2 at full-step cost).
- **"Contacts between steps go unfelt"** means the agent steps at its divisor. Then the ticks between its steps
  either send nothing, and their `this tick only` events are lost (a gunshot between steps is never heard), or
  frames queue, and B2's accumulation comes back. The frozen form has no "since the last delivered frame" meaning,
  so either way it changes, which is a `STIMULUS_SCHEMA_VERSION` bump on a form frozen for Phase 4.

The risk line names the symptom, not the delivery rule, and never names the cheap fallback, S6 (d).

**Fix:** freeze the form so it is valid under both answers. Events cover "since this NPC's last delivered frame",
capped per frame with B2's coalescing, and offsets run from that frame's first tick. Under (c) that is one tick, so
nothing changes today. Name the fallback in §11.3: (d), a logged wake predicate, with the cost of a full step per
tick beside it. Say what T9's strict red gate measures in each case.

#### F4. Physics-made events don't fit a frame built before physics
**`sem_stimuli.md::§4.1` (frames built at step 4, physics at step 6), `§4.2` (events "this tick only"; "One frame
covers one tick, so offsets order correctly"), `§5` (the save holds "pending events").**

Physics runs at step 6 every fifth tick, over the interval (T−5, T], after tick T's frames are built and sent. An
event it produces (an impact, a collapse, any sound or impact the solid or fire law emits) is stamped somewhere in
the last five ticks. Those frames have already gone. It can reach only T+1's frame, where its "offset within the
tick" is negative or up to five ticks old, and the sort key's claim that one frame covers one tick is false for
it. The save's "pending events" shows a buffer already exists between ticks. v1 has no producer (§4.2), so nothing
breaks today, but the form is frozen now.

**Fix:** stamp events with the tick they belong to and their offset within that tick, deliver them in the first
frame after they are made, and sort by `(tick, offset_us, kind rank, local_id)`. State the latency: up to five
ticks plus one for physics-made events, and zero for intent-made ones applied at step 1. F3's "since last
delivered" rule covers both.

#### F5. A short write on a non-blocking socket is ordinary, so killing on it kills healthy NPCs
**`sem_stimuli.md::§4.3` ("`BrokenPipeError`, `ConnectionResetError` and a short write become
`agent_failed(crashed)`").**

A non-blocking `send` returns the bytes it took, which is fewer than offered whenever the socket buffer is full,
and `BlockingIOError` when it takes none. macOS gives a Unix stream socket 8,192 bytes each way (round 1, **D**). A
tick that queues a `settle` (receipts plus gated writes) and a `step` to a worker that hasn't drained the previous
message gets a partial send. Under §4.3 that ends a live NPC as `crashed`, flags the run tier 3, and the cause is
wall-time scheduling. My round-1 fold wrote this.

**Fix:** a partial send keeps its remainder in a per-channel outbox, pumped by the same multiplexer inside the
per-park ceiling. Only a ceiling expiry is `hung`; only `BrokenPipeError`, `ConnectionResetError` or EOF is
`crashed`. Set §4.3's byte budget below the socket buffer and say so. Test it with a planted worker that reads one
byte at a time: the frame arrives whole, and the agent lives.

#### F6. The one-writer check runs once, and Maxim starts and restarts threads after build
**`sem_stimuli.md::§4.4` ("after Maxim builds, the worker checks that `threading.enumerate()` holds only its step
thread"); `embeddable_agent_DRAFT.md::§6` OD-EA7 ("the thread count is unchanged by building **and stepping**").**

At `origin/main` (`git grep`): `ConceptExtractor.restart_worker` starts a new worker thread after construction
(`memory/concept_extractor.py:542-560`), and its docstring says "the hippocampus capture worker restarts per
session". `BackgroundTaskManager.start` (`default_network/background_tasks.py:135-148`) starts on call, and
`agentic_runtime.py:255` starts the `doa-feed` thread. A check made once, after build, passes, and a thread started
at step N then runs unseen. v2's check also differs from the exit test the embeddable draft already gives Maxim
(OD-EA7, which includes stepping), so the two documents disagree on the guarantee.

**Fix:** make §4.4's check OD-EA7's: compare the thread set at every park against the post-build set. It costs
microseconds per park. Cite OD-EA7 as the Maxim side and keep the owner check per bound sensor. Plant a thread
started at the third step and show it red.

### NIT

- **N-a. `§4.1`, `§4.3`: the merge has no step.** §4.3 ends an agent "in tick T's merge", but §4.1's seven steps
  don't place the merge. Put it after the join of steps 5 and 6 and before step 7, and say that step 5 writes
  nothing step 6 reads (F1's plant tests exactly this). Say also how the per-park ceiling is judged while the
  simulation lane is inside physics: either a pump thread stamps arrivals, or the ceiling is checked at the first
  poll after the join, which moves a `hung` decision by up to one physics step of wall time.
- **N-b. `§8`, the work counter "parks per tick."** Under (c) it equals the number of ready NPCs. That number
  depends on `agent_ready`, a wall-time fact. It replays exactly because the record is logged, but a counter gate
  compared across live runs will differ, so the gate must read it from the log, not from a rerun.
- **N-c. `§4.5`, restart "sent from that tick."** Restart opens a new log segment (O45). Say whether the restarted
  agent's first frame carries F3's "since last delivered" events from before the failure (I'd say no, empty, with
  a logged count of what was dropped).

## Counts

Round 1: 13 fixed, 2 deferred (S6 (d), N5), 1 open (S9), 0 rejected. New: 1 BLOCKER (F1), 5 SHOULD-FIX (F2–F6), 3
NIT. Two of the new findings (F1, F5) are errors in my own round-1 folds that v2 adopted as written.
