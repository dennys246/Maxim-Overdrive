# Time in the engine: world time, body time, perceived time (research, 2026-11-16)

**Status:** research input for the boundaries design and part 2 (`npcs_and_sem.md`). Nothing here is decided; the
recommendations are for the owner. It reads `realtime_lanes_coop.md` (§2 to §4), `boundaries.md`,
`world_model.md` §1, §6 and §9, `reviews/boundaries/bio_faithful.md` (BF-1, BF-2, BF-8, BF-11) and
`determinism.md` (D-B3, D-S5, D-S7, D-S8), `research/signals/`, `lessons_maxim_in_games.md` (standards worktree),
`docs/maxim_upstream/hybrid_1_5_line_DRAFT.md`, and the installed pymaxim 1.3.3 (read only).

**Numbers.** Each is marked *measured* (with its source), *derived* (with the arithmetic), *from memory* (to verify
before it reaches `data/`), or *unmeasured* (an assumption that needs a B5 row).

## 0. The answer in eight lines

1. **One correction to the framing.** The universal time in this engine is **world time** (the integer tick), not
   the wall clock. The wall clock belongs to the machine running the world. An NPC lives in world time and must never
   be able to tell what the wall clock says, or how fast the dial is (Bio-11).
2. **The world tick is the fine reality. An NPC perceives time only coarsely and noisily** (the owner's refined
   framing). This splits time inside an NPC into two kinds that the engine must keep apart:
   - **time as a parameter of dynamics:** drives drift, transmitters deplete and recover, and reflexes take their
     latency, all in exact world time, because the body is physics;
   - **time as information:** what the NPC can know or say about durations, order and the time of day. It comes
     only through a modelled sense (an interval timer with Weber noise, an entrained SCN, an order threshold, or an
     in-world clock it can see), never as a tick number.
3. **Every rate is in world time, and every schedule is fixed by the model, never by the machine.** The dial changes
   only how often the host calls `step`. Any machine shortfall (physics, the substrate lane, a late LLM) is absorbed
   by **dilation in wall time**, reported, never by changing a world-time schedule. This is D21's rule, applied to
   agents.
4. **The brain's intrinsic rate limits belong in the engine at behaviour scale,** not spike scale: reaction
   latency, maximum action rate, refractory and depletion pools with recovery time constants, habituation. They are
   game cooldowns and stamina pools with biological constants, counted in ticks.
5. **LLM latency is a property of the machine.** Recommendation: give deliberation a **modelled world-time cost**
   from biology (a deadline fixed when the thought is requested), hold early results until the deadline, and dilate
   the world for late ones. Add per-NPC thought slots (one in flight, a refractory interval) so LLM demand is
   bounded per world second, and let the substrate carry behaviour in between.
6. **This changes what "nobody waits" means, and it needs an owner decision.** In world time nobody waits: the NPC
   lives through exactly the modelled time, acting on its substrate. In wall time the world may slow, as physics
   already makes it. That reverses `realtime_lanes_coop.md` §9 Q1 ("hold the world for a late thought? No") for
   wall time, while keeping it for world time.
7. **Determinism improves.** With modelled deadlines, *when* a thought lands is a pure function of world state.
   With a recorded model (a response cache), runs with real LLM thoughts become reproducible at any dial, which today
   is impossible (tier 3).
8. **Foundations to lay now:** integer-tick fields on intents, receipts and thought requests (engine and log only,
   stripped before cognition); `AgentPort.step(world_dt_ticks, frame)` with a separate perceived-time channel; rates
   in microseconds in `data/`; a per-NPC counter-based RNG stream outside the core; a host latency policy logged in
   the header; and a rule plus a test that no agent-facing schema carries a tick, a wall time or the dial.

---

## 1. Three clocks, and who owns each

### 1.1 What each clock is

| Clock | What it is | Units | Owner | Must it be world time? |
|---|---|---|---|---|
| **World time** | The simulation's truth: `tick × tick_us`. The only clock that moves anything in the world. | integer ticks | `Simulation` (sealed core) | It *is* world time. |
| **Body time** | The NPC's physical processes: drive drift, reflex latency, refractory and depletion pools, fatigue, sleep pressure, the SCN oscillator's own dynamics. They advance by exact world `dt`. | world seconds, held as integer ticks or microseconds | the agent (Maxim's substrate), stepped by the engine through `AgentPort` | **Yes.** These processes change what the NPC does, and so what the world becomes. Driven by anything other than world time, they make behaviour depend on the machine. |
| **Perceived time** | What the NPC believes about time: how long something lasted, what came first, the time of day, how long ago a memory happened. | the NPC's own internal estimates, never ticks | the agent (Maxim), computed from body-time signals | **No, it is internal state.** It must be *derived from* world time only through modelled senses, with deterministic noise. It may be wrong, and should be, in the ways people are. |
| **Wall time** | The host machine's clock. | wall seconds | the host and its lanes, never the core or an agent | **It must never reach the other three.** |

A comparison from games: in almost every engine, *game time* and *real time* are already different clocks. A
paused game still runs its menus on real time, and a bullet-time effect slows game time while the UI runs at full
speed. This design adds a third: the time a character *believes* has passed.

### 1.2 Body time is exact; perception of it is not

The owner's point, refined: people can't perceive time at its true resolution. We get a coarse, noisy estimate,
and the SCN gives a time of day that is only as good as its entrainment. The engine should copy that split:

- **The neurons integrate true time without knowing it.** A transmitter pool refills with a time constant in real
  seconds whether or not the animal attends to it. So the substrate's dynamics take the exact `world_dt`. This is
  physics, not information.
- **The animal knows only what a mechanism computes.** Interval timing (a pacemaker and accumulator, or a population
  of striatal "time cells"; the models are contested, *from memory*) gives durations with roughly constant
  *relative* error, Weber's law. The SCN gives a phase entrained by light. Temporal order needs a minimum
  separation. Memory dates events by context, not by a stamp.

So the rule for the engine is: **time may enter an NPC as a parameter of its dynamics; it may enter as information
only through a modelled sense.** A tick number is never information an NPC receives.

### 1.3 Where wall time legitimately remains

Wall time is real and needed, in the host only:

- **The pacing loop.** The host turns the dial into wall pacing: call `Simulation.step` every
  `tick_us / time_scale` wall microseconds, using an accumulator (§2.1). This is the one place the dial and the wall
  clock meet.
- **Dilation measurement.** The effective scale is world time advanced per wall second, measured by the host and
  reported in the tick status. It goes to the client and the meters, never into a frame an NPC reads.
- **The LLM call's own timeout,** which only frees a worker (CP-4), and the network lane's deadlines (the `hello`
  deadline, socket timeouts).
- **Meters:** p99 tick time, LLM wall latency, queue depths.
- **The log's flush cadence,** which is I/O, not simulation.

None of these is an input to the `Simulation` except through a logged record (D-S7): a pause, a dial change, a
thought result, a thought failure. That is how wall-time events become world-time facts.

### 1.4 Maxim reads the wall clock where the substrate's cadence is set (pushback evidence)

Lesson 11 covers drives and decay. The cadences are on the wall clock too (pymaxim 1.3.3, read only):
- `runtime/loop_controller.py:157`: `llm_submit_interval = 0.5`, in wall seconds;
- `runtime/loop_state.py::_substrate_tick_due` (line 259): `time.time() - ctrl.last_llm_submit_time`;
- `default_network/background_tasks.py::OperationThrottler.should_run` (line 89): `time.time()`;
- `default_network/config.py:219` and `network.py:86`: `update_hz = 30.0`, paced in wall time;
- `embodiment/percepts.py:57,109`: `poll_hz = 1.0`, on `time.time()`;
- `runtime/agent_loop.py:1020`: the loop's `target_hz = 30.0`.

**Consequence.** Under a dial, every one of these runs at a fixed wall rate, so at 20× a Maxim NPC gets one
twentieth of the substrate updates per world second, and at 0.25× it gets four times as many. Its reflexes get
slower in world time as the dial goes up. That is exactly the dial-dependent intelligence lesson 12 forbids, in the
substrate rather than the LLM. It strengthens the case for Phase 3 items 12 and 15 (an externally stepped live tick
and an injected clock): **every Maxim cadence should be a world-time rate under an injected clock.** Add these
sites to those items' evidence.

---

## 2. Multi-rate simulation

### 2.1 How games do it

- **The fixed timestep with an accumulator** (Glenn Fiedler's "Fix Your Timestep" is the standard reference). The
  render loop runs as fast as the screen allows. Each frame it adds the elapsed real time, times the time scale, to
  an accumulator, then runs whole simulation steps of a fixed size while the accumulator holds at least one step,
  carrying the remainder. The simulation always sees the same step size, so its results don't depend on frame rate.
  The renderer draws between the last two states by interpolation, so motion looks smooth at any frame rate. This
  is what the host's pacing loop does, and what the Godot client does with snapshots.
- **Physics substeps.** A step too large for a stiff law is split into smaller substeps inside one simulation step.
  `substeps_per_physics_step` is this.
- **Multi-rate subsystems.** Not everything runs every step. Physics might run every step, AI "think" every few,
  pathfinding on request, and ambient systems every second. In a deterministic engine the rate is always an
  **integer divisor** of the base tick: "every k ticks". `physics_every_ticks = 5` is the first.
- **Time-slicing (staggering).** With 100 NPCs thinking every 10 ticks, the engine runs 10 of them each tick rather
  than 100 on one tick and none on the others. The slice an NPC is in is its **phase**: `(tick + phase) % k == 0`.
  This flattens the cost spikes (CP-9's lumpy ticks are the same problem for physics).
- **AI level of detail (LOD).** Many games update distant or off-screen NPCs less often. **Here that is allowed only
  if it is decided from world state, identically on every machine and at every dial** (the same rule as D21 for
  resolution). "Off-screen" is a property of the client, so it can't decide anything. "Asleep" can: a sleeping
  animal really does respond more slowly, so a sleeping NPC's lower rate is biology, not a budget trick.
- **Cooldowns and resource pools.** The game form of a refractory period: an ability can't be used again until tick
  `last_use + cooldown`, and stamina drains with use and refills over time. Section 2.3 uses exactly these, with
  biological constants.
- **Lockstep and time dilation, in shipped games.** Factorio and most RTS games run a deterministic fixed-rate
  simulation in lockstep, so a slow machine slows everyone rather than changing the result. EVE Online's "time
  dilation" slows a busy server's game time to as little as 10% of real time, rather than dropping or reordering
  events. Paradox's grand strategy games keep a fixed in-game tick and simply run fewer ticks per second on a slow
  machine (*from memory*, all three). This design's dilation is the same idea.

### 2.2 The rule that makes behaviour identical under any dial

1. **Every rate and duration in the world or an agent is expressed in world time** and converted to ticks once at
   load, never in wall seconds.
2. **Every schedule is a pure function of world state:** "every k ticks at phase p", or "at tick T + L". Nothing is
   scheduled as "when the worker finishes".
3. **The host calls `step` at whatever wall rate it can, up to the dial.** If any part of the step (physics, the
   substrate lane, a due thought) is late in wall time, the host waits, in wall time, and reports dilation.

Under these three rules, the dial is invisible to the world and to every NPC, by construction.

### 2.3 Mapping the brain's intrinsic rate limits onto ticks

The owner's examples (refractory periods, vesicle recycling, SNARE reloading) are real, but they act at
millisecond scales the engine can't and shouldn't simulate per NPC (a neuron's absolute refractory period is about
1 ms; *from memory*). What they produce at the scale of behaviour is what an NPC needs. The mapping:

| Neural mechanism (*from memory*) | What it produces in behaviour | Engine form | Typical constant (*from memory*) |
|---|---|---|---|
| Conduction and synaptic delays along a pathway | **Reaction latency:** a stimulus can't change action before L | a delay: a percept from the frame of tick T may affect an intent applied no earlier than T + L | spinal stretch reflex 25–50 ms; simple visual reaction 180–250 ms; choice reaction 350–600 ms, rising with the number of choices (Hick's law) |
| Absolute and relative refractory periods; motor-unit firing limits | **Maximum action rate** | a cooldown per action class: next allowed tick | finger tapping about 5–7 Hz; saccades about 3–4 per second |
| Central bottleneck between response selections | **The psychological refractory period:** a second decision right after a first is delayed | a cooldown on the decision stage, separate from the motor one | about 100–300 ms of added delay |
| Vesicle pool depletion and recycling (readily releasable pool refills in seconds; full recycling in tens of seconds) | **Short-term depression: habituation and sensory adaptation** to a repeated stimulus, recovering with rest | a depletion pool per receptor channel: each response draws it down, it refills with a time constant | recovery τ of seconds to tens of seconds |
| SNARE priming and vesicle docking | **Readiness:** a primed, expected response is faster | a reduced latency when the action was prepared (a cue earlier than T) | foreperiod effects of tens to about 100 ms |
| Metabolic depletion, adenosine | **Fatigue and sleep pressure** | homeostatic and entropic drives, already in Maxim, stepped by world `dt` | hours |

All of these are integer ticks or per-tick decay factors computed from world `dt`. None depends on the dial. They
should live in `data/agents/timing.yaml` (a name proposed here), in microseconds, versioned, strict-loaded, and
converted to ticks at load, with a check that rounding stays within a stated tolerance. Storing them in
microseconds means a later change to `tick_us` is a reload, not a refactor.

**The tick is coarse for reflexes.** At `tick_us = 100,000` (0.1 s), the fastest possible response is one tick, two
to four times a spinal reflex. Choice reactions (350 ms and up) are representable, at about ±50 ms of quantization.
Two ways out, both cheap now and costly later:
- a smaller `tick_us` (50 ms doubles the agent and host overhead per world second but not physics, which keeps its
  0.5 s period);
- or an **agent sub-tick**: the substrate steps k times inside a tick on the same frame, for reflex arcs only.

Recommend deciding the tick size in `phase1/sim-clock`, before anything is counted in ticks, and recording reflex
latency below one tick as a Known gap if 0.1 s stays.

**Option B's hand-off latency must be counted inside the modelled latency, not on top of it.** If the substrate runs
in its own lane at tick boundaries (BF-2 option b), an intent built from the frame of tick T can apply no earlier
than T + 1. If the engine then adds a modelled reaction latency of L ticks on top, the lane architecture has
changed the NPC's biology. Instead, the engine schedules every intent at `observed_tick + L_bio` exactly (and
refuses a configuration where `L_bio` is shorter than the lane's minimum). Then moving the substrate inside the core
later (BF-2 option a) changes nothing an NPC experiences.

### 2.4 Compute: what the dial does, and what is affordable

**The dial multiplies wall compute for everything rated in world time.** At dial s, one wall second must run s world
seconds of physics and s world seconds of every NPC's substrate. It does not multiply LLM compute directly: that is
per thought (§3), and how many thoughts arise per world second is a design choice.

**Physics at 20×** (derived from `world_model.md` §9, measured costs on the 16×10×4 m tile at 0.1 m): a cached heat
substep costs 3.9 ms, and the explicit stability limit at 0.1 m allows far more than 0.5 s for solids (dt ≤ dx²/6α;
for steel, α ≈ 1.2e-5 m²/s, about 140 s; *from memory* for α), so one substep per 0.5 s physics step: 7.8 ms per
world second. Region reductions are about 3 ms per physics step at 0.1 m (23 ms at 0.05 m, divided by 8; derived),
another 6 ms per world second. A quiet tile is about 15 ms per world second; a fire with zones, fuel and relabels
perhaps 30 to 40 (*unmeasured*). **At 20×, physics takes 0.3 to 0.8 of one core.** That agrees with the lanes
design's "rig, 0.1 m, about 20× with caching".

**The substrate.** Per-NPC wall CPU per wall second = `c × r × s`, where c is the cost of one substrate step, r its
rate in world Hz, and s the dial. **Maxim's substrate step cost in a game loop is unmeasured;** it needs a B5 row
before anything here is relied on. The table spans the plausible range:

| c, cost per step | NPCs per core at 1×, r = 10 Hz | at 5× | at 20× |
|---|---|---|---|
| 0.05 ms | 2,000 | 400 | 100 |
| 0.2 ms | 500 | 100 | 25 |
| 1 ms | 100 | 20 | 5 |
| 5 ms | 20 | 4 | 1 |

(Derived: NPCs per core = 1 / (c × r × s).) Three things change the picture:

- **The GIL.** In-process (option B as a thread), the substrate shares one interpreter lock with the simulation lane.
  At 20× physics leaves about half a core, so halve the 20× column. As separate processes, each core is free, but
  each tick pays a hand-off: send a compact percept frame (scalars per NPC, not grids) and receive intents. At 200
  ticks per wall second (20× of 10 Hz), even 0.2 ms per hand-off is 40 ms a second. Batch all NPCs per process per
  tick.
- **Multi-rate substrate.** Not every process needs 10 Hz. Reflex arcs and the cerebellum's forward model run at the
  tick; the DN's salience at 5–10 Hz; drive drift, NAc decay and percept polling at 1 Hz; consolidation only in
  sleep. If 20% of the cost needs 10 Hz and the rest 1 Hz, the effective rate is about 2.8 Hz, and the table above
  improves about 3.5×.
- **Sleep is cheap by biology.** A sleeping NPC runs at low rates and doesn't deliberate, which is why the "sleep"
  fast-forward preset is the one that can reach 20× with many NPCs.

**When the budget runs out, the world dilates, as for physics.** The host must never thin an NPC's substrate rate
to keep up, because that changes its reflexes (§1.4 is the warning).

---

## 3. The LLM latency problem, honestly

### 3.1 The problem

Deliberation latency today is a property of the machine: the model, its hardware, its load, and the network. Under
"nobody waits" with no modelled cost, a 3 s wall thought lands after:

| Dial | World seconds for a 3 s wall thought |
|---|---|
| 0.25× | 0.75 |
| 1× | 3 |
| 5× | 15 |
| 20× | 60 |

A minute of world time is a long time to think about a fire. So with free latency, **how competent an NPC is
depends on the dial and the hardware**. A player on a fast GPU in slow motion has cleverer neighbours than a player
on a laptop at fast-forward. `realtime_lanes_coop.md` §4.3 accepted this as "a real property of a mind in a faster
or slower world". The honest objection is that it isn't a property of any mind: no brain's deliberation time
depends on how fast someone else's machine runs. It is the one place where the machine decides an outcome, which
D21 forbids for physics.

There is no biological number for "an LLM thought". What biology offers is the time a person takes for the
behaviour the thought produces: a deliberate choice among a few options takes about 0.5 to 2 s; forming a short
spoken reply begins after about 0.6 to 1.5 s and then runs at about 2 to 3 words a second; deciding a plan takes
seconds to minutes (*from memory*). Those are what a modelled cost would copy.

### 3.2 The options

**O1. Free latency (today's design).** The thought applies on the first tick after it arrives.
- No-wait: holds in world and wall time.
- Bio-faithful: no; deliberation time is the machine's.
- Determinism: the thought's tick depends on wall timing. Replays are exact from the log; no rerun is reproducible
  (tier 3).

**O2. Modelled deliberation cost: a deadline in world time, fixed at request.** When the NPC starts a thought at
tick T, the agent's policy assigns it a modelled latency `D(kind, context)` in ticks from `data/` (a simple choice,
a reply, a plan). The thought applies at exactly `T + D`. An early result is held until then (the substrate keeps
acting meanwhile; nothing waits). A late one leaves three choices at the deadline:
- **O2a, dilate:** the host doesn't step past `T + D` until the result arrives. In world time nobody waits; in wall
  time the world slows, reported as dilation with its cause.
- **O2b, abandon:** the thought fails at `T + D`, logged as `thought_failed`. The machine then decides whether a
  thought succeeds.
- **O2c, extend:** the deadline slips to arrival. That is O1 with a floor, and inherits O1's problem.

**O3. Thought slots, rate-limited.** One thought in flight per NPC (already decided, CP-4), plus a refractory
interval in world time before the next, and a per-NPC "deliberation budget" that the substrate's state (sleep,
pain, arousal) modulates. This bounds LLM demand per world second, and so per wall second at any dial. It is
biologically fair as a rate limit (attention is limited), but the specific depletion model is ANALOG: "ego
depletion" is contested in the literature (*from memory*), so the budget shouldn't claim to be a mechanism.

**O4. The substrate carries behaviour.** Reflexes, habits, NAc's learned action selection, the cerebellum's
predictions and the DN carry the NPC between thoughts, and deliberation is reserved for what the substrate can't
handle (novelty, dialogue, plans). This is the hybrid line's claim (H1, H3). It doesn't solve the latency problem;
it shrinks how much it matters. **It is required under every option.**

**O5. Dial caps during deliberation.** The host caps the dial while a thought is in flight (or while a player-facing
one is). This is O2a done crudely: it slows the world even when the thought would have arrived in time, and it
doesn't make the landing tick deterministic.

### 3.3 Against "nobody waits" and determinism

| Option | Waits in world time? | Waits in wall time? | Landing tick is a pure function of state? | Dial-independent behaviour? |
|---|---|---|---|---|
| O1 free | no | no | no | no |
| O2a modelled, dilate | no | yes, only when late | **yes** | **yes** |
| O2b modelled, abandon | no | no | yes when on time; machine decides failures | no, the failure rate depends on dial and hardware |
| O2c modelled, extend | no | no | no | no |
| O3 slots | (with any of the above) | | rate only | bounds demand |
| O4 substrate | (with any of the above) | | | reduces sensitivity |
| O5 dial cap | no | yes, always while thinking | no | partly |

O2a is the only option where an NPC's intelligence is independent of the dial and the hardware. Its price is wall
time, so the question is whether that price is affordable at the dials that matter.

### 3.4 Can O2a keep fast-forward? The throughput budget

Sustainable dial ≈ `W / (N × m)`, where W is LLM throughput in thoughts per wall second (workers ÷ wall latency),
N the number of awake, deliberating NPCs, and m the thoughts each starts per world second (derived; it ignores
burstiness, so treat it as an upper bound).

| Setup | W | N | m (per NPC) | Sustainable dial |
|---|---|---|---|---|
| one local model, 3 s, serial | 0.33/s | 10 | 2 per world minute | 1× |
| same | 0.33/s | 10 | 1 per 5 world minutes | 10× |
| same, everyone asleep | 0.33/s | 0 awake | 0 | physics-bound (about 20×) |
| two local workers, 3 s | 0.67/s | 3 (the player's companions) | 2 per world minute | 6.7× |
| hosted model, 16 parallel, 2 s | 8/s | 20 | 2 per world minute | 12× |

So fast-forward survives where it is used for its stated purposes, "wait" and "sleep" (§3.4 of the lanes design):
NPCs that are asleep or idle deliberate rarely, by biology, and the substrate carries them. It does not survive "20×
while ten NPCs argue", and that is the honest answer: in that scene, either the world slows, or the NPCs get
stupider. O2a chooses the first and says so.

### 3.5 Recommendation

1. **O4 always.** It is the hybrid claim, and the H1 and H3 experiments measure it.
2. **O2 with a deadline from `data/`**, assigned by the agent's policy at request time from the thought's kind, and
   logged with the request. Early results are held; this is buffering, not waiting.
3. **O2a as the default host policy:** late thoughts dilate the world, with dilation attributed to "deliberation"
   in the tick status and the meters, beside "physics" and "substrate".
4. **O2b as an explicit, logged host policy** (`latency_policy: abandon`) for runs that value wall pace over
   faithfulness, such as a long unattended fast-forward. Its machine-dependent failure rate is a meter, and its runs
   are tier 3.
5. **O3:** one thought in flight per NPC, a refractory interval and a budget, all in world time.
6. **Keep the speech duration out of the deadline.** A reply's length is known only when it arrives, so a deadline
   that depended on it would depend on arrival. Instead, the thought's deadline is the decision latency, and
   speaking is then an action that takes world time in proportion to its length, like walking.
7. **Cancellation is decided in world time,** by pain or salience at a tick (item 13). A cancelled thought's late
   result is dropped and logged.
8. **Use H2 to choose D.** The hybrid draft's H2 sweeps stub latency over world time (0, 1, 3, 10, 30 s). With O2,
   that sweep becomes the calibration: it shows where competence collapses, and the shipped D sits where people
   actually take that long. Propose this to Maxim as an addition to the 1.5 line: the shipped mechanism is a
   modelled world-time deadline, not measured machine latency.

**This needs an owner decision,** because it changes decision 7's reading. Decision 7 says neither the world nor the
NPC waits for a thought, and it defines waiting in world time. O2a keeps that: the NPC experiences exactly D and
acts throughout. But `realtime_lanes_coop.md` §9 Q1 answered "hold the world for a late thought?" with "no", and O2a
holds it in wall time. The argument for the change: physics already dilates the world in wall time when the
machine can't keep up (D21), and no one calls that waiting; a thought is the same case. It differs from the H1
control arm ("the world paused for each thought"), which gives deliberation zero world time; O2a gives it a
biological amount.

---

## 4. Determinism and replay, per option

| | O1 free | O2a dilate | O2b abandon | O3 slots | O5 cap |
|---|---|---|---|---|---|
| Replay from the log (tier 1) | exact | exact | exact | exact | exact |
| Scripted run with stubs (tier 2) | exact (stub latency in ticks) | exact | exact | exact | exact |
| Rerun with a **recorded** real model (a response cache keyed by the request's canonical hash) | no: landing ticks move with wall timing | **exact at any dial and machine**, because the landing tick is `T + D` and the content is the cache's | exact only if every thought was on time; otherwise failures move | follows the base option | no |
| What the log must hold | thought result with apply tick | request (tick, kind, D) and result | request, result or `thought_failed` | slot state is derived, not logged | the cap decisions, as time records |
| Wall data in the log | none as input | none as input | none as input | none | the cap as a host record |

Notes:
- **The response cache is the big gain.** It turns "real Maxim with a real LLM" into a reproducible test, once
  Maxim's deterministic-agent items (12, 15, 16) land. The cache is an untrusted input (a loader with a gate, B-4)
  and keyed by a SHA-256 of the canonical request, never by builtin `hash()`.
- **Dilation never enters the log as an input.** The log records what was applied at which tick. Dilation is a
  meter.
- **Thoughts due on one tick apply in request-id order** `(tick, actor, n)` (§4.2 of the lanes design), and
  same-tick intents in `(tick, actor id, per-actor seq)` order (D-S8), never arrival order.
- **Under option B,** the substrate lane is in lockstep with the simulation lane: tick T + 1 doesn't run until every
  intent due then has been produced. A slow substrate lane dilates the world; it never makes an intent miss its
  tick. That keeps tier 2 exact with the substrate outside the core.

---

## 5. Perceived time: coarse, noisy and deterministic (the owner's refined framing)

### 5.1 What an NPC can know about time, and through what

| What | Mechanism to model | Engine side | Agent side |
|---|---|---|---|
| **How long something lasted** | an interval timer with scalar variability: the estimate's error grows in proportion to the duration (Weber fraction about 0.1–0.2 for seconds to minutes; *from memory*). Arousal and dopamine change the clock's speed; danger is remembered as longer (*from memory*; the "time slows down" effect is reported as retrospective, not perceptual) | supplies exact `world_dt` to the body's dynamics | the timer is agent state; its readout is noisy, from the NPC's own stream (§5.2) |
| **What came first** | a temporal order threshold: two events closer than about 20–60 ms are reported in the wrong order or as simultaneous (*from memory*) | events within one tick are simultaneous to every percept (their engine order is canonical, not perceptual); with 0.1 s ticks, events a tick or more apart are above the threshold | the agent sees order only between percepts it received at different ticks |
| **The time of day** | the SCN: an oscillator with a free-running period slightly off 24 h (about 24.2 h in people; *from memory*), entrained by light (and weakly by meals and activity), so its phase is an estimate that drifts without light | supplies light as a physical field (a percept), never the time of day | the SCN integrates body time and is entrained by sensed light; the NPC's "time of day" is its phase estimate |
| **How long ago a memory happened** | episodic memory dates events by context (what else was going on, how many events since), not by a timestamp | none | Maxim's memory may keep an exact world time internally as machinery (an ANALOG divergence, §5.4), but cognition reads only the subjective estimate |
| **What the clock says** | reading a clock | **a clock in the world is an object**, with a display the NPC can see when it looks | an exact time is legitimate only as a percept of an in-world device, which can be wrong, stopped or out of sight |

This gives the game something interesting for free: an NPC kept in a windowless room drifts out of phase; an NPC who
owns a watch knows the time; a frightened NPC overstates how long the fire burned.

### 5.2 Where the noise comes from

- **Never the World's `Generator`.** An agent's perceptual noise drawing on the world's stream would make physics
  depend on how often an NPC looked (D-S5). It would also make the world's random draws depend on how many NPCs exist.
- **A per-NPC, counter-based stream, keyed and stateless:** each draw is a pure function of
  `(run seed, actor id, stream name, counter)`, for example numpy's `Philox` with the key set from those values
  through `SeedSequence`. The counter is the tick plus a per-tick draw index, or the event's id. A draw doesn't
  depend on any other NPC, on lane scheduling, or on how many draws came before in another stream.
- **It lives with the agent, outside the core under option B,** and moves inside with the agent under option A.
  Either way its seed comes from the log header (one root seed, spawned per actor and stream), so the stream is
  reproducible and needs no log entries.
- **Under option B a replay doesn't even need it:** the NPC's outputs are logged intents. Tier 2 reruns (stubs, or a
  recorded model) do need it, and get it from the seed.
- **The stream's state at a save** is just the counter, so save v1's agent state stays small.

### 5.3 What a frame or percept may contain about time

**Agent-facing (cognition, prompts, Maxim's `SensorReading` values):**
- **may contain:** the percepts of the moment (light, heat, sound and what the NPC's senses compute from them), the
  outcomes of its own actions as they are sensed, a clock's display if it sees one, and its own internal estimates
  (duration, phase), which the agent computes, not the engine;
- **must not contain:** the tick number, the world time in microseconds, the time of day, `observed_tick` or any
  intent or receipt tick, the dial, dilation, the effective scale, wall times, thought deadlines or queue state.

**Engine-facing (the `AgentPort` call, the log, the meters):** exact ticks everywhere. `AgentPort.step` receives
`world_dt` because the body needs it as a dynamics parameter (§1.2); the adapter passes it to the substrate's
integrators and never into a percept or a prompt.

**One frozen Maxim field gets in the way.** `SensorReading.timestamp` is a field of Maxim's frozen type, and Maxim's
machinery uses it for ordering and age gating (BF-11). Today the membrane fills it with `grid.time_s`. Proposal:
fill it with the body clock (exact world time on the one declared clock, BF-11's fix), and treat it as machinery.
The rule, and the pushback to Maxim, is that **a reading's timestamp never reaches an LLM prompt verbatim**; prompt
builders render time from the subjective estimate ("a minute or two ago", "this evening"). Until Maxim agrees, it is
an OPEN divergence with a strict red gate on a prompt containing a raw timestamp.

### 5.4 What this means for intents and receipts

- **`observed_tick`, `issued_tick`, `apply_tick`, `receipt_tick` are engine and log fields.** They exist so that
  the log is complete (D-B3), staleness can be judged (BF-8), and latency can be metered. The adapter strips them
  before anything reaches cognition.
- **The NPC matches a receipt to its action by an opaque id**, not by a tick. Maxim's `settle` (BF-1's proposed
  `propose`/`settle` split) receives the outcome and the sensed after-state; the delay it experienced is known to it
  only by the receipt's *arrival*, at a tick the engine scheduled (the sensing latency), and by its own interval
  timer.
- **A stale refusal carries no "the world changed at tick X".** It says "overtaken", as context (lesson 9, BF-8).
- **Memory timestamps inside Maxim** (hippocampus de-duplication, decay windows) can run on the exact body clock,
  which is a faithful *substrate* (decay happens in real time) but an ANALOG *memory* (people don't stamp episodes).
  The divergence is that an exact stamp exists at all; the rule is that cognition can't read it.

### 5.5 Guards for this, once there is code

- a schema test: no agent-facing type or percept channel has a field in the time vocabulary (`tick`, `*_us`,
  `time_of_day`, `scale`, `dilation`, `deadline`, `wall`);
- a red gate on any rendered prompt containing a world tick or a raw timestamp;
- the noise stream: a test that an NPC's draws are unchanged when another NPC is added, and when the World's
  `Generator` is advanced;
- the dial: a scripted run at 0.25×, 1× and 20× with stub agents gives bit-identical NPC percepts, not only world
  state.

---

## 6. Foundations to lay now, in the boundaries design

Each costs a field or a rule today and a refactor later.

1. **`AgentPort` takes integer ticks and a frame, and splits dynamics from information.**
   ```
   AgentPort
     step(now: TickView, world_dt_ticks: int, frame: PerceptFrame) -> list[IntentProposal]
     settle(receipts: list[Receipt]) -> None
     request_thought() -> ThoughtRequest | None      (or returned by step)
     deliver(result: ThoughtResult) -> None          (called at the apply tick)
   ```
   `TickView` carries the tick for the adapter's bookkeeping and the injected body clock; the adapter's contract
   forbids passing it into percepts. `PerceptFrame` is an immutable sample of one published frame (BF-4) with no time
   fields beyond what §5.3 allows.
2. **The intent record** (extends D-B3's): `actor`, `actor_seq`, `source` (reflex, substrate, deliberation,
   player), `thought_id` when from a thought, **`observed_tick`** (the frame the decision used), **`issued_tick`**,
   **`apply_tick`** (`observed_tick + L` for substrate intents, the deadline for thought intents), typed params and a
   stable target id. All ticks are integers.
3. **The receipt:** `intent_id`, `apply_tick`, outcome kind (`applied`, `refused`, `stale`, `cancelled`), the
   application's metadata, `before_frame_tick` and `after_frame_tick`, and **`deliver_tick`** (the sensing latency,
   in ticks, from `data/`). The agent sees the outcome and the sensed after-state, not the ticks.
4. **The thought request:** `request_id = (tick, actor, n)`, `requested_tick`, `context_frame_tick`, `kind`,
   **`deadline_ticks`** (the modelled D), `cancel_on` (the pain and salience conditions), and the canonical hash for
   a response cache.
5. **A host latency policy** (`free`, `modelled_dilate`, `modelled_abandon`), in server config, hashed into the log
   header, with the determinism tier it gives. Phase 1's stub keeps its fixed latency in ticks, which is
   `modelled_dilate` with a stub that is never late.
6. **Timing data in microseconds:** `data/agents/timing.yaml` for reaction latencies, cooldowns, refractory
   intervals, pool time constants, deliberation deadlines by kind, the sensing latency and the thought refractory
   interval; strict loader, converted to ticks at load with a rounding check.
7. **Rates are integer divisors with a phase from the actor id** (`(tick + phase(actor)) % k == 0`), so staggering
   is deterministic and agent LOD can only be decided from world state.
8. **A per-NPC counter-based RNG stream,** spawned from the log header's seed, owned by the agent side, never the
   World's `Generator`.
9. **Dilation with a cause:** the tick status and meters split effective scale by cause (physics, substrate,
   deliberation). None of it reaches a frame an NPC reads.
10. **Decide `tick_us` in `phase1/sim-clock`** with reflex latency in view (§2.3), or record the gap.
11. **Lockstep for the substrate lane under option B:** intents due at tick T must exist before T runs; a late lane
    dilates, never skips.
12. **Phase 3 additions:** the cadence sites of §1.4 as evidence for items 12 and 15; a two-clock injected
    interface (a body clock for dynamics, perceived time for cognition); `SensorReading.timestamp` as machinery,
    never in prompts; and the modelled-deadline proposal for the 1.5 line's H2.

## 7. Open questions for the owner

1. **O2a, dilating the world in wall time for a late thought,** given that nobody waits in world time? This revises
   `realtime_lanes_coop.md` §9 Q1.
2. **The tick size:** 0.1 s with reflexes quantized to one tick (a Known gap), 50 ms, or an agent sub-tick?
3. **How much subjective-time modelling, and when:** the order and "no ticks in percepts" rules now (they cost
   nothing), the interval timer and entrained SCN with Maxim's item 10, or later?
