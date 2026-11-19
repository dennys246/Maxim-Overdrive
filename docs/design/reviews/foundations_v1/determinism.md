# Determinism and replay lens (with performance and lane concurrency): foundations v1

Lens: Determinism and replay, also covering Performance and Concurrency and lanes. Commit: 4f7a754
(`phase1/design-v2`). Date: 2026-11-16. Counts: **5 BLOCKER, 12 SHOULD-FIX, 7 NIT.**

Documents read: `docs/design/boundaries.md` v2 (§3, §4, §6, §7 in depth), `docs/design/npcs_and_sem.md` (all),
`docs/maxim_upstream/world_clock_release_DRAFT.md` (§3, §6), the v1 lens review
`docs/design/reviews/boundaries/determinism.md`, `world_model.md` §6 and §9, `research/time/engine_mapping.md` §2–§5,
`realtime_lanes_coop.md` §2–§4, `docs/code_review.md`. Probes run in the main `.venv` (numpy 2.5.4).

**Summary.** Tier 1 (replay of the *world* from the log) holds under every option the designs name, because the log
is the truth and replay calls nothing live. Everything beyond that is weaker than written. The two headline claims
of part 2 are that real-LLM sessions "reproduce at any dial" through modelled deadlines and the response cache
(§4.7, tagged [now]), and that an NPC's percepts are bit-identical at 1× and 20× (§3.1). Neither has a mechanism
yet. The host doesn't own the LLM calls. Agent code runs concurrently with the tick, with no barrier. The cache key
isn't defined. The dial test as specified can't fail. Separately, the throughput table that O4 rests on leaves out
the bound that actually binds (per-thought latency), and overstates fast-forward by up to about 10×. The v1 D-B4
fold doesn't hold either: measured, a view unlocked during one write window stays writable after the window closes.

---

## BLOCKER

### DR-B1. Agent code races the tick: option B lockstep plus mode (a) has no quiescence barrier

`npcs_and_sem.md` §4.2 (segments), §6.1 (mode (a)), §4.7; `boundaries.md` §7.1 ("the substrate runs at tick
boundaries"); `engine_mapping.md` §4 ("tick T + 1 doesn't run until every intent due then has been produced")

Lockstep as written waits for *intents*. It doesn't wait for *agent code*. Under mode (a), one Maxim agent runs on
two paths at once:
- the LLM turn, which runs Maxim's tool loop, writes the hippocampus and NAc during the turn (`realtime_lanes_coop.md`
  §4.3), and blocks in `execute` until a receipt arrives;
- `AgentPort.step`, which advances the same agent's substrate at each tick boundary, and the push path, which writes
  `vital_metrics` from each frame (§4.3).

Nothing says which thread runs either path, or how they are ordered.

Failure scenario: NPC 7's tool call lands at tick 40, and `execute` returns. Its tool loop resumes on a worker
thread, reads sensors for the cerebellum (§6.1 step 5) and writes a hippocampus record. Meanwhile the host, whose
lockstep condition only waits on due intents, steps ticks 41 and 42, and the agent lane pushes their frames into the
same body. At 1× the cerebellum reads tick-40 sensors. At 20× the host is faster than the worker, so it reads tick-42
sensors. The forward model trains on different data, the next substrate intent differs, and from then on the world
differs. Tier 1 replay is still exact, since the intents were logged. But §4.7's "reproduces at any dial" and §3.1's
dial-invisibility test are both false. Maxim's tier A doesn't fix this: an injected clock doesn't serialise two
threads.

Fix: define the agent execution model in the design.
- Each agent is owned by one thread, or is single-entry under a lock with a defined order.
- **The host steps tick T+1 only when every agent is parked** at a known gate: returned from `step`, blocked in
  `execute` awaiting a receipt, or blocked in the LLM gateway awaiting a held response (DR-B2).
- Released work (a response at its deadline, a receipt) runs to its next park before the tick advances, in canonical
  `(tick, sub-tick, actor, seq)` order.

This is the lockstep barrier Factorio-style engines use, applied to the agent's code and not only its outputs. Add a
B5 row for its cost per tick. At 200 ticks per wall second, even 50 µs per park and release per NPC is 10 ms per
second per NPC.

### DR-B2. The host doesn't own the LLM call, so deadlines, early hold, cancellation and the cache can't be built against real Maxim

`npcs_and_sem.md` §4.2, §4.3, §4.4, §4.7; `boundaries.md` §7.1 (`request_thought` is agent → host), §8.1 (adapter
surfaces), §9.3; `world_clock_release_DRAFT.md` §3.1, §6

Every mechanism in part 2 §4 assumes the host sits between Maxim and the model: it holds an early segment, refuses to
step past a late one, cancels, records and replays responses, and stamps tokens. Today Maxim decides by itself when
to call the LLM (`llm_submit_interval`) and calls it through its own backend, inside its tool loop. A thought is
several LLM calls (§4.2, Pn), not one request. The world-clock release injects `Clock`, `Rng` and `IdSource`, but no
LLM gateway. E1 uses "a stub LLM with recorded responses" without naming the injection point. `boundaries.md` §8.1
and §9.3 don't list one either.

Failure scenario: tier A ships exactly as drafted, E1–E6 green. Overdrive embeds real Maxim. Maxim's tool loop calls
its backend directly. The response arrives 0.4 s wall after the request, at 20× that is 8 world seconds, and Maxim
acts on it at once. No host code ever saw the response, so it can't hold it to its modelled onset, cache it, or
cancel it. O4's "modelled thought cost" then holds for stubs only, and with real Maxim every run is the free-latency
option O1 (`engine_mapping.md` §3.2), which is what O4 rejected.

Fix: add an injected `LlmGateway` (name open) to the world-clock release §3.1, as a fourth collaborator: Maxim's only
path to a model. The embedder's implementation parks the calling agent (DR-B1), releases the response at its
modelled time, records it, and serves cache hits. Add an exit test: E1's script run against a gateway that returns
each response after a seeded random *wall* delay, some early and some late, gives the same digest as a synchronous
gateway. List the gateway in `boundaries.md` §8.1's agent-adapter surface and in §9.3 as additive.

### DR-B3. The response cache is not canonical, collides across occurrences, and its miss policy is undefined

`npcs_and_sem.md` §4.7 ([now]); `boundaries.md` §7.4 ("SHA-256 of the canonical request");
`engine_mapping.md` §4

"The canonical request" is never defined. These all bear on the key:
- **What goes in it:** the model id *and* a weights or quantisation digest (a local model swapped for a re-quantised
  build serves different answers under the same name); the sampling parameters (temperature, top-p, top-k, seed,
  max tokens, stop sequences); the system prompt; the tool schemas *in a fixed order*; the message list.
- **How it is serialised:** canonical JSON (sorted keys, a fixed float format or no floats, NFC-normalised strings,
  explicit separators), or the "same" request hashes differently between runs.
- **Occurrences:** at temperature above 0, two identical requests in one run (two NPCs with the same context, or one
  NPC asked the same thing twice) get different answers live. A cache keyed by content alone stores one of them, so
  the rerun differs from the recorded run on the second occurrence. Key by `(content hash, occurrence index)`, or
  store a list per key, consumed in canonical order.
- **Misses on rerun:** if a miss falls through to a live call, a rerun silently becomes tier 3. A rerun must run in
  strict mode, where a miss is a loud error naming the request, never a live call.
- **Granularity:** per LLM call (each segment), not per thought (DR-B2).
- **[now] is wrong:** until tier A, Maxim's prompt carries the exact host date and time (§1, A9), so every request is
  unique and the cache never hits on a rerun. Until generate vs apply (C1), the prompt is built from agent state that
  DR-B1 makes timing-dependent. Tag §4.7 [after A, and DR-B1 resolved].

Failure scenario: a bug report ships its cache. The developer's rerun differs at the first prompt, by one second of
host time, misses, calls their local model, and "reproduces" a different conversation without saying so. The cache
is treated as reproduction, and it reproduced nothing.

Fix: define the canonical request (fields, serialisation, version) as a frozen, versioned type with golden fixtures.
Add occurrence keying, a strict miss policy for reruns, and a cache header carrying the model and weights digests. The
cache is a file read from strangers' machines, so it is a gate with the strictest contract (§5.3 doesn't list it).

### DR-B4. The v1 D-B4 fold doesn't hold: a view unlocked during one write window stays writable after it closes

`boundaries.md` §4.1 ("a write anywhere else raises"; proof tests); v1 D-B4

Measured (numpy 2.5.4):

```python
a = np.zeros(4); a.flags.writeable = False
v = a[:]                                       # a view taken while the window is closed
a.flags.writeable = True; v.flags.writeable = True   # the window opens for one step
a.flags.writeable = False                      # the window closes
v[1] = 5                                       # succeeds: owner False, view True, a == [0, 5, 0, 0]
```

The flag is checked only when it is *set*, against the base's flag at that moment. A view that re-enables itself at
any time inside any window keeps write access forever. With lanes, the window is open most of the time the simulation
lane is busy, so a thread holding a view can also unlock it simply by timing. The proposed proof tests (direct write,
re-enable then write, `.base`, `out=`, attribute assignment) all run with the window closed, so they pass while the
guard fails. That is v1's "a test that can't fail on the line that breaks it" again.

Failure scenario: a law caches a view of `temperature` across steps ("avoid re-slicing") and re-enables it inside
`step` to update in place. In the next scenario, an instrument helper holds that same view and writes through it
outside any window. Nothing raises, and the world changed outside the pipeline.

Fix: don't toggle flags on the owner.
- The write window is **ownership**, not a flag: `cells.writing()` yields fresh writable arrays (or the only writable
  handle) and swaps them in at exit, so no handle outlives the window.
- Anything outward is a copy.
- Add a proof test that unlocks a view inside a window and writes after the window closes.

The real guard is then §4.2's "nothing outside the simulation lane holds a reference", and §4.1 should say so, not
claim that a write anywhere else raises.

### DR-B5. The throughput formula is the wrong bound, and O4's fast-forward conclusion rests on it

`npcs_and_sem.md` §4.5; `engine_mapping.md` §3.4

`dial ≤ W / (N·m)` is dimensionally right and its rows check out arithmetically. But it is a throughput bound, and
under the dilate policy the binding constraint is **latency**. A thought requested at world time T with onset `D`
can't pass `T + D` until its result arrives. If the wall latency L (queue wait, plus prompt build, plus the model)
exceeds `D / dial`, the world runs at most `D / L` for that window, however many workers there are. Over a world
interval:

`effective dial ≈ 1 / ( f · L/D + (1 − f) / dial_max )`

Here f is the fraction of world time covered by at least one pending window. The model has to finish (or, for
streamed speech, produce its first token) within `D/dial`.

Recomputed with the documents' own numbers (D = 1 s, L = 3 s, dial_max = 20):

| Scene | §4.5 / engine_mapping | Latency bound |
|---|---|---|
| One NPC talking to the player, any number of workers | (not listed) | **about 0.33×, slower than real time**, while it deliberates |
| Ten idle NPCs, 2 thoughts per world minute | ~10× | about 6.7× (2 × 3 s + 58 s/20 ≈ 8.9 s wall per world minute) |
| Hosted, 16 parallel, 2 s, 20 NPCs, 2 per world minute (engine_mapping) | 12× | **about 1×** (f ≈ 1 − e^(−40/60) ≈ 0.49: 29 world s at 0.5×, 31 at 20×) |

Each segment of a multi-call thought (Pn, tool calls under mode (a)) pays L again, and a tool call can't be acted on
from a partial stream, so it pays the full latency, not the time to first token.

Failure scenario: the owner accepts O4 on the strength of "the world slows toward 1× during conversation". In
playtest, every conversation with a 3 s local model runs the whole arcology at a third of real time, including
other players in co-op. That isn't "toward 1×".

Fix: replace §4.5's formula with `min(throughput bound, latency bound)` and recompute both tables. State the
user-facing consequence: any deliberation slower than its modelled onset puts the world below 1×. Give the levers
(smaller onset-critical prompts, streaming the first word for P1 speech, P0 carrying the gap). Add a B5 row for wall
latency to first token and to the complete tool call, per model. Take this back to the owner, since it bears on O4.

---

## SHOULD-FIX

### DR-S1. Δt invariance isn't the determinism mechanism, and its discrete-event half fails as specified

`npcs_and_sem.md` §2.1 (step-size test), §3.4; `boundaries.md` §7.3

- **Delivery is quantised to the step.** A crossing "is stamped at sub-tick resolution, and delivered at the next
  tick" after the step that computed it. A drive stepped at 1 Hz (every 10 ticks) that crosses at tick T+3 is
  computed at T+10, so its pain reaches the agent at T+10 or T+11. Stepped every tick, it arrives at T+4. The test's
  "discrete events land on the same tick" goes red by construction at step sizes 5, 10 and 50. Fix: **predictive
  scheduling**. At each step, compute the next crossing in closed form and schedule a wake-up at its tick. An input
  that changes the rates (an intent, a percept) reschedules. Or say that discrete effects are delivered at step
  granularity and are part of the outcome class only at that granularity.
- **Floats near a boundary.** `x *= exp(−k·dt)` ten times and once with `10·dt` differ in the last bits, so a
  crossing computed with `t = ln(x0/θ)/k` can fall on different sides of an integer µs or a tick boundary. Specify
  floor to integer µs from the step-start state, and gate the discrete assertion with an outcome margin, as
  CLAUDE.md requires for binary physics outcomes.
- **Percepts sampled at a coarse rate miss events.** A flash at tick 3 is gone from the frame by tick 10. Discrete
  percept events must accumulate as an event list since the last step, not be sampled from the latest frame.
- **Bit identity comes from fixed schedules, not from Δt invariance.** State that `dt_ticks` passed to
  `AgentPort.step` is a pure function of the actor's rate divisor and phase, never of lag. A host that catches up by
  passing a larger dt keeps the outcome class (by Δt invariance) and loses bit identity.

### DR-S2. Sub-tick time: microseconds or ticks, and the record has no field for it

`npcs_and_sem.md` §9 (items 2 and the last bullet); `boundaries.md` §6.2, §7.3

- §9 stamps agent events "in world microseconds below the tick". The same section says timing data is "converted to
  ticks at load, with a check that rounding stays within tolerance". These contradict each other. Pick integer µs end
  to end, and derive ticks only at apply.
- Give the rounding rule: `apply_tick = ceil((observed_tick·tick_us + L_us) / tick_us)`, in integers, and say
  whether a stamp exactly on a boundary applies at that tick or the next.
- The intent record (§6.2) has `observed_tick`, `issued_tick` and `apply_tick`, but no sub-tick field, while §9's
  ordering key uses one. Add `apply_us` (an int64) to the record and its golden fixtures, or the canonical order
  can't be rebuilt from the log.
- Never a float. The crossing solver's float result is converted once, by the floor rule, at the source (DR-S1).

### DR-S3. Three ordering keys across the documents, one of them arrival order

`boundaries.md` §6.2 `(apply_tick, actor_id, seq)`; `npcs_and_sem.md` §9 `(tick, sub-tick, actor, seq)`;
`realtime_lanes_coop.md` §4.2 `(tick, host_seq)` assigned "when the simulation lane takes it off its inbox", plus
request-id order `(tick, actor, n)`; lanes §2.1's kind order (joins, leaves, time decisions, intents, thought results)

Lanes §4.2 isn't in part 2's supersedes table (§11), so arrival-order `host_seq` still stands on paper. Failure
scenario: an implementer follows lanes §4.2. Two NPC intents due at tick 40 are logged in arrival order. Replay is
exact, but tier 2 reruns differ with thread scheduling, which is v1 D-S8 again. Player intents have no modelled
sub-tick time either: is it 0, or an arrival-derived value?

Fix: one key, stated once (in `boundaries.md` §6.2), carried in the record:
`(apply_tick, kind_rank, apply_us, actor_id, seq)`. Controls and joins rank before intents. Player intents take
`apply_us = 0`, or a logged arrival value. The log is written in that order. Mark lanes §4.2's `host_seq` superseded.
The fold table's "D-S8 folded" is only true once this lands (DR-N6).

### DR-S4. The per-NPC Philox stream isn't stable under adding NPCs or streams, as specified

`npcs_and_sem.md` §3.4; `boundaries.md` §7.3; `engine_mapping.md` §5.2; `world_clock_release_DRAFT.md` §3.1 (`Rng`)

- **`SeedSequence.spawn()` is order-dependent.** Children are numbered by spawn order, so spawning per actor in
  creation order shifts every later stream when one is added. Use `SeedSequence(root, spawn_key=(NS_AGENT,
  actor_key, stream_key))` explicitly, never `spawn()`.
- **The actor id isn't a stable key.** Actor ids come from the allocator "in roster order at load" and on join.
  Insert one NPC early in the roster, and every later NPC's noise changes. Key on a persisted NPC identity (an
  integer from the roster file or its stable id), not the allocator's integer.
- **Stream names need fixed integers.** Use a registry in `data/`, or the first 8 bytes of SHA-256 of the name.
  Never `hash()`.
- **The counter layout collides under rejection sampling.** Measured: `Generator(Philox).standard_normal(1000)`
  advanced the counter by 256, and a draw consumes a variable number of raw outputs (ziggurat rejection, Philox's
  buffer of 4). "Counter = tick plus a per-tick draw index" with consecutive values makes draw i's rejections consume
  draw i+1's counters, giving identical or correlated values. Put `(tick, draw_index)` in the high counter words and
  leave the low word for consumption, or build the bit generator per `(tick, event)` key.
- **The World's generator needs its own namespace:** `spawn_key=(NS_WORLD,)` from the same root. Say it, so
  `default_rng(seed)` and the agent tree can't overlap by accident.
- **Mismatch with the upstream draft.** The world-clock release's `Rng` is "a seeded `random.Random` (or `Generator`)
  per agent, with named substreams": sequential, so a draw depends on how many draws came before in Maxim's own
  code. Overdrive's per-NPC streams are counter-based. Raise this in §8's open questions: ask for keyed substreams,
  or accept that Maxim-internal draws are sequential and are reproducible only under DR-B1's serialisation.

Add a test: adding an NPC (and, separately, a stream) leaves every other NPC's draws bit-identical.

### DR-S5. Agents sharing one process couple through Maxim's module-level state

`world_clock_release_DRAFT.md` §3.2 (only live-path sites move), §6; `engine_mapping.md` §2.4 (in-process option B)

About 39 uses of global `random`, module-level caches, and the hippocampus de-duplication window are process
globals. Tier A moves only the sites a stepped turn reaches. Two agents in one process, stepped in either order or
on two threads, can then consume each other's draws or share cache state. Adding an NPC then changes another NPC's
behaviour, and step order becomes an input.

Fix: an exit test, E7 (agent isolation). The E1 script for agent A, run alone, with agent B alongside, and with A and
B stepped in reversed order and concurrently, gives A the same digest in all four. Prove it by planting a
global-`random` call in a shared helper.

### DR-S6. The dial-invisibility test can't fail as specified

`npcs_and_sem.md` §3.1; `boundaries.md` §7.3

"A scripted run at 1× and at 20× gives bit-identical percepts and prompts." With an instant stub agent, nothing is
ever early or late, no worker is ever behind, and the dial changes only how often `step` is called. The early hold,
the dilation hold, the parking barrier (DR-B1) and the gateway (DR-B2) are never exercised, so the test passes on a
host that has none of them.

Fix:
- Drive the stub through the gateway with a seeded wall-delay schedule, independent of the world, that makes some
  segments early and some late at each dial.
- Run the host threaded, as shipped.
- Use an injected fake wall clock rather than real pacing (no sleeps in tests).
- Add a **negative control:** the same run under `latency_policy: abandon` must differ between dials. That proves the
  test can see a dial leak.
- Plant `if dial > 10: skip hold` and watch it go red.

### DR-S7. The determinism tiers need rescoping: replay reproduces the world, never the agents

`boundaries.md` §6.2 ("Replay calls nothing live"), §6.3 (header), §7.1 ("agent state lives outside
`Simulation`"); CLAUDE.md ("replays are … the bug report, the regression test and the save format's backbone")

Under option B, replay never runs Maxim, so a replay reproduces `World` bit for bit and reproduces no agent state at
all. That is correct, but it changes what the log can be:
- A bug about why an NPC chose something can't be reproduced from the log. It needs a tier 2 rerun.
- Agent state at tick T can't be rebuilt from scene plus log, so a save can't be "a checkpoint plus the log"
  for agents.

The header (§6.3) covers only world inputs. A tier 2 rerun also needs:
- `data/agents/timing.yaml`'s digest, the roster and each agent home's initial digest;
- the pymaxim version and its config digest;
- the model ids and weights digests;
- the response cache's digest, the root seed's agent namespace, and `latency_policy`.

Fix: state the three tiers with what each reproduces (world, or world and agents). Add a rerun manifest beside the
log header, with the same refuse-on-mismatch rule. Correct CLAUDE.md's replay sentence, or scope it to the world.

### DR-S8. Speech is world input, so "LLM text stays out of the log" needs an exception, and stamps must not depend on stream chunking

`boundaries.md` §6.2 ("Prompts, LLM text and tool-call text stay out"); `npcs_and_sem.md` §4.2 (P2), §4.3, §5

Speech is heard by players and other NPCs ("being spoken to" is a `cancel_on` event), so it is an intent whose
params carry the text, and it must be logged. Otherwise replay can't reproduce who heard what, or which thoughts were
cancelled by it. And word stamps "at speech rate, with durations by syllables" must be a pure function of the
*complete word*:
- a provider stream that splits "hel" | "lo" must not stamp "hel";
- a word is stamped only once a following delimiter arrives, and the last word at stream end;
- the syllable counter (or tokenizer) is pinned and its version goes in the rerun manifest.

Otherwise stamps change with the provider's chunking, which is wall-dependent.

### DR-S9. The performance budgets the designs depend on are unmeasured or absent

`boundaries.md` §4.2 (a frozen frame after each step, "copies or read-only owners"), §6.2 ("a per-tick digest");
`npcs_and_sem.md` §2.1, §4.5; `engine_mapping.md` §2.4; `standards_backlog.md` B5 (turn time and snapshot only)

- **Frames.** A full-grid copy per publish is 64–80 MB per tile at 0.1 m and about 0.5–0.64 GB at 0.05 m
  (world_model §9's 100–125 B/cell). Publishing per tick at 20× is about 13–16 GB/s of memcpy at 0.1 m. Publish on
  change only (cells change at physics steps and at intent apply), and give agents reductions (the bincount pass,
  scalars per NPC), not grids. "Read-only owners" can't be a frame, since the owner is written again next step
  (DR-B4).
- **The per-tick digest.** SHA-256 over 64 MB is tens of ms. Say what is digested: receipts and derived scalars per
  tick, and the full state per physics step or per N.
- **Rows B5 doesn't have:** substrate step cost `c` (engine_mapping's own "needs a B5 row"); park and release per NPC
  per tick (DR-B1); adapter push and strip per NPC; gateway overhead; the synchronous log write per tick at 200
  ticks/s; the frame publish; wall latency to first token and to the complete tool call (DR-B5); GIL contention
  between LLM-turn Python and the simulation lane.

Fix: list these as B5 rows, owned by `phase1/sim-clock` and `phase1/lanes`, each with its meter, before any number in
§4.5 or engine_mapping §2.4 is relied on.

### DR-S10. The agent-side adapter decides tier 2 determinism but sits outside every seal

`boundaries.md` §3 (the non-simulation list includes `engine.adapters`), §4.3, §7.3

`engine.adapters.agents` owns the strip (no time field reaches cognition), the push (a pure function of the frame),
the per-NPC noise, step scheduling and the gateway. Dial invisibility and tier 2 reruns depend on all of it being
wall-free. But adapters are excluded from the banned-import contract and the AST scan, and the tripwire runs only on
the simulation thread. A `time.monotonic()` used to "debounce" a percept push in the adapter is caught by nothing.

Fix: a second sealed set, the agent step path (`engine.adapters.agents` minus a named host-only module for
timeouts), under the same banned list and scan. Extend the tripwire to the agent lane's thread. Prove each with a
planted call.

### DR-S11. Under the dilate policy, machine-decided failures still reach agents unrecorded

`npcs_and_sem.md` §4.4; `boundaries.md` §6.3 (`latency_policy` in the header)

Dilation removes lateness as a machine decision, but not failure. An LLM error, a provider timeout, a refused
request or an out-of-memory error arrives as a failed thought (lanes §4.3), decided by the machine. Under option B it
doesn't touch the world log (only the intents that didn't happen do), but it changes the agent, and a cache rerun
can't reproduce it unless the cache records failures as responses. Also, `latency_policy` lives only in the header,
yet a host could switch it mid-session ("abandon" for an unattended fast-forward).

Fix: the cache records failures as first-class responses. A run with any machine-decided failure is flagged tier 3
in its manifest, as abandon runs are. `latency_policy` changes are control records, not header fields.

### DR-S12. The world-clock release's exit tests miss the paths that break

`world_clock_release_DRAFT.md` §6

- **E1** runs a scripted host with a stub LLM, presumably synchronous and single-threaded, so it never exercises
  DR-B1's race or DR-B2's hold. Add the wall-delay gateway variant (DR-B2).
- **E1's digest needs non-vacuity.** Five hundred ticks may never reach consolidation (sleep only) or move an SCN bin.
  Equal digests over subsystems that never ran prove nothing. Assert that each digested component changed during
  the script, and prove the digest by planting a `time.time()` stamp (§6 already says this for one stamp; do it per
  component).
- **E3** pauses for "30 wall seconds", and **E2** paces at wall speed. Both need an injected fake wall clock, or they
  are 30-second sleeps in a test suite.
- Missing: agent isolation (DR-S5) and stream stability under an added agent (DR-S4).

---

## NIT

- **DR-N1.** The World's generator is sequential, so one extra random draw anywhere shifts every later draw. That is
  deterministic, but it makes goldens brittle under unrelated additions. Consider keyed draws for laws, `(tick,
  region or cell id, law)`, as for agents (CLAUDE.md "Determinism"; `realtime_lanes_coop.md` §2.1).
- **DR-N2.** State the bound for world µs: int64 throughout, and on the wire at most 2⁵³ µs (about 285 years), which
  is enough; say so beside §9.1's 2⁵³ pin.
- **DR-N3.** Is reaction latency `L_bio` measured from a percept's sub-tick stamp or from its frame's tick? A
  sub-tick stamp delivered at the next tick gives a systematic bias of up to one tick. Say which (§9, §2.1).
- **DR-N4.** A thought cancelled before its deadline may never have been recorded, so on rerun the gateway must
  return "cancelled" to Maxim, not raise a strict-mode miss (DR-B3). State the order: cancellation first, then the
  cache lookup.
- **DR-N5.** The response cache and the rerun manifest are loaders and belong in `boundaries.md` §5.3's gate table
  under the strangers'-machines contract.
- **DR-N6.** The fold table says D-S8 is folded and none deferred, but lanes §4.2's arrival-order `host_seq` is not
  superseded (DR-S3). Mark it partial until then.
- **DR-N7.** NumPy doesn't promise `Generator` distribution streams across versions (NEP 19). The §6.3 environment
  header covers it, but name it as the reason, and add pymaxim's version for agent-side draws.

---

## v1 determinism findings: did v2 fold them?

| v1 | v2 says | Verdict |
|---|---|---|
| D-B1 writers outside the core | §3 writers move into `engine.sim`; non-vacuity test | **folded** |
| D-B2 unrecorded disk input | §3 no IO in core; §6.3 digests and refusal | **folded** for the world; agents need the rerun manifest (DR-S7) |
| D-B3 log record undefined | §6.2 record, typed canonical params, stable target | **folded**, but missing the sub-tick field (DR-S2) |
| D-B4 read-only views defeated | §4.1 owner flags plus a write window | **not achieved**: a view unlocked inside a window stays writable (DR-B4, measured) |
| D-S1 tripwire can't see the case | §3 denylist, planted per entry, over the corpus | **folded** for the simulation lane; the agent lane is uncovered (DR-S10) |
| D-S2 list vs import-linter | §3 one list, `os` wholesale, allowed list | **folded** |
| D-S3 non-import leaks | §3 AST additions, BLAS forbidden | **folded** |
| D-S4 environment header | §6.3 | **folded** |
| D-S5 observation reads live state | §4.2 frames, `observed_tick`, no World RNG | **folded**; the frame cost is unbudgeted (DR-S9) |
| D-S6 scan vacuity | §11.2 floor | **folded** |
| D-S7 one log for every input | §6.1, §6.2 | **folded** |
| D-S8 canonical same-tick order | §6.2 | **partial**: three keys across the documents, one of them arrival order (DR-S3) |
| D-S9 log the typed intent | §6.2 | **folded** |
| D-N1–N3, N5 | §1, §6.2, §3, §2.2 | folded |
| D-N4 golden-log-driven tests | deferred to sim-clock | acceptable deferral |

## Direct answers to the ask

- **Bit-identical tier 1 and tier 2 under every option?** Tier 1, world replay: yes, under every option, including
  abandon, because the log is the truth. Tier 2 with stubs: yes only if stubs are synchronous. With threaded lanes and
  mode (a), not until DR-B1. Tier 2 with real thoughts through the cache: no mechanism yet (DR-B2, DR-B3), and not
  before tier A in any case.
- **Is the cache key canonical?** It is undefined. Model and weights, sampling parameters, tool-schema order,
  serialisation, occurrences and miss policy are all open (DR-B3). Model nondeterminism is fine *if* the cache is
  strict on rerun, and silently fatal if a miss calls live. Streaming boundaries matter for word stamps (DR-S8).
- **Sub-tick and crossings?** Integer µs isn't decided (DR-S2). Float crossings need a floor rule and an outcome
  margin. Delivery is quantised to the step unless crossings are scheduled predictively (DR-S1). Ties fall to actor
  and sequence once one key is fixed (DR-S3).
- **The Philox separation?** Right in intent, wrong in two details: `spawn()` order and allocator-order actor ids
  make it unstable under adding NPCs, and the counter layout collides under rejection sampling (DR-S4).
- **Does the dial-invisibility test hold?** Not as written; it can't fail (DR-S6). It holds only after DR-B1 and
  DR-B2, and never under abandon.
- **Is the throughput formula right?** It's a correct throughput bound, but not the binding one. The latency bound
  puts conversation below 1× (DR-B5). The substrate step cost and five other costs have no B5 rows (DR-S9).
- **Did v2 fold v1?** Eleven of thirteen BLOCKERs and SHOULD-FIXes fully. D-B4 is not achieved, and D-S8 is partial.
